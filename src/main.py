"""Main CLI entry point for Jellyfin Playback Validator."""

import sys
import logging
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.table import Table
from rich import box

from .config import load_config
from .jellyfin_client import JellyfinClient
from .progress_tracker import ProgressTracker
from .validator import MovieValidator


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('jellyfin_validator.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Rich console for pretty output
console = Console()


def print_header(config):
    """Print application header."""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Jellyfin Playback Validator[/bold cyan]",
        border_style="cyan"
    ))
    console.print(f"[dim]Server: {config.jellyfin.base_url}[/dim]")
    console.print()


def print_progress_stats(stats, batch_num, total_batches):
    """Print current progress statistics."""
    console.print(f"[bold]Fortschritt:[/bold] {stats['tested']}/{stats['total']} Filme getestet "
                  f"({stats['percentage']:.1f}%)")
    console.print(f"[bold]Status:[/bold] OK: [green]{stats['ok']}[/green] | "
                  f"DEFEKT: [red]{stats['defect']}[/red]")
    console.print()
    console.print(f"[bold yellow]Teste Batch {batch_num}/{total_batches}[/bold yellow]")
    console.print()


def print_summary(validation_results, stats):
    """Print validation summary."""
    console.print()
    console.print("[bold cyan]═══ Zusammenfassung ===[/bold cyan]")

    # Create summary table
    table = Table(show_header=False, box=box.SIMPLE)
    table.add_column("Label", style="bold")
    table.add_column("Value")

    table.add_row("Getestet", f"{validation_results['total']} Filme")
    table.add_row("OK", f"[green]{validation_results['ok']} Filme[/green]")
    table.add_row("DEFEKT", f"[red]{validation_results['defect']} Filme[/red]")
    table.add_row("Gesamtfortschritt", f"{stats['tested']}/{stats['total']} ({stats['percentage']:.1f}%)")

    console.print(table)
    console.print()

    if stats['remaining'] > 0:
        console.print(f"[bold yellow]Noch zu testen:[/bold yellow] {stats['remaining']} Filme")
        console.print("[dim]Führe das Script erneut aus, um fortzufahren.[/dim]")
    else:
        console.print("[bold green]✓ Alle Filme wurden getestet![/bold green]")

    console.print()


def main():
    """Main application entry point."""
    try:
        # Load configuration
        console.print("[dim]Lade Konfiguration...[/dim]")
        config = load_config()

        print_header(config)

        # Initialize components
        project_root = Path(__file__).parent.parent

        client = JellyfinClient(
            base_url=config.jellyfin.base_url,
            api_key=config.jellyfin.api_key,
            user_id=config.jellyfin.user_id,
            timeout=config.validation.timeout_seconds
        )

        progress_tracker = ProgressTracker(
            progress_file=project_root / config.output.progress_file
        )

        validator = MovieValidator(
            client=client,
            backup_file=project_root / config.output.backup_file,
            defect_tag=config.validation.defect_tag,
            pause_between=config.validation.pause_between_requests
        )

        # Fetch all movies
        console.print("[dim]Lade Filmliste von Jellyfin...[/dim]")
        all_movies = client.get_all_movies()

        if not all_movies:
            console.print("[red]Keine Filme gefunden![/red]")
            return 1

        # Initialize progress with total count
        progress_tracker.initialize_with_total(len(all_movies))

        # Get current stats
        stats = progress_tracker.get_stats()

        # Check if already completed
        if progress_tracker.is_completed():
            console.print("[bold green]✓ Alle Filme wurden bereits getestet![/bold green]")
            console.print()
            print_summary({'total': 0, 'ok': 0, 'defect': 0}, stats)
            return 0

        # Get next batch
        all_movie_ids = [movie.item_id for movie in all_movies]
        batch_ids = progress_tracker.get_next_batch(
            all_movie_ids,
            config.validation.max_films_per_run
        )

        if not batch_ids:
            console.print("[yellow]Keine neuen Filme zu testen.[/yellow]")
            return 0

        # Get movie objects for batch
        batch_movies = [m for m in all_movies if m.item_id in batch_ids]

        # Calculate batch number
        batch_num = (stats['tested'] // config.validation.max_films_per_run) + 1
        total_batches = (stats['total'] + config.validation.max_films_per_run - 1) // config.validation.max_films_per_run

        print_progress_stats(stats, batch_num, total_batches)

        # Validate batch with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:

            task = progress.add_task(
                f"[cyan]Teste Filme {stats['tested']+1}-{stats['tested']+len(batch_movies)}...",
                total=len(batch_movies)
            )

            validation_results = {
                'total': len(batch_movies),
                'ok': 0,
                'defect': 0
            }

            for i, movie in enumerate(batch_movies):
                # Update progress description
                progress.update(
                    task,
                    description=f"[cyan]Teste: {movie.name}",
                    completed=i
                )

                # Validate movie
                is_ok = validator.validate_movie(movie)

                # Track result
                if is_ok:
                    validation_results['ok'] += 1
                    console.print(f"  [green]✓[/green] {movie.name}")
                else:
                    validation_results['defect'] += 1
                    console.print(f"  [red]✗[/red] {movie.name} - DEFEKT")

                # Mark as tested
                progress_tracker.mark_as_tested(movie.item_id, is_defect=not is_ok)

                # Update progress bar
                progress.update(task, completed=i + 1)

        # Get updated stats
        stats = progress_tracker.get_stats()

        # Print summary
        print_summary(validation_results, stats)

        return 0

    except FileNotFoundError as e:
        console.print(f"[red]Fehler:[/red] {e}")
        return 1
    except KeyboardInterrupt:
        console.print("\n[yellow]Abbruch durch Benutzer[/yellow]")
        console.print("[dim]Der Fortschritt wurde gespeichert. Führe das Script erneut aus, um fortzufahren.[/dim]")
        return 130
    except Exception as e:
        console.print(f"[red]Unerwarteter Fehler:[/red] {e}")
        logger.exception("Unexpected error in main()")
        return 1


if __name__ == '__main__':
    sys.exit(main())
