"""Progress tracking for movie validation."""

import json
from pathlib import Path
from typing import List, Set, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class Progress:
    """Progress tracking data."""
    total_films: int = 0
    tested_films: List[str] = None
    defect_films: List[str] = None

    def __post_init__(self):
        if self.tested_films is None:
            self.tested_films = []
        if self.defect_films is None:
            self.defect_films = []


class ProgressTracker:
    """Tracks validation progress across multiple runs."""

    def __init__(self, progress_file: Path):
        """
        Initialize progress tracker.

        Args:
            progress_file: Path to progress JSON file
        """
        self.progress_file = progress_file
        self.progress = self._load_progress()

    def _load_progress(self) -> Progress:
        """
        Load progress from file.

        Returns:
            Progress object
        """
        if not self.progress_file.exists():
            logger.info("No existing progress file found, starting fresh")
            return Progress()

        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            progress = Progress(
                total_films=data.get('total_films', 0),
                tested_films=data.get('tested_films', []),
                defect_films=data.get('defect_films', [])
            )

            logger.info(
                f"Loaded progress: {len(progress.tested_films)}/{progress.total_films} "
                f"films tested, {len(progress.defect_films)} defects found"
            )
            return progress

        except Exception as e:
            logger.error(f"Failed to load progress file: {e}")
            logger.warning("Starting with fresh progress")
            return Progress()

    def save_progress(self) -> None:
        """Save current progress to file."""
        try:
            data = asdict(self.progress)

            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug("Progress saved successfully")

        except Exception as e:
            logger.error(f"Failed to save progress: {e}")

    def initialize_with_total(self, total_films: int) -> None:
        """
        Initialize progress with total film count.

        Args:
            total_films: Total number of films to validate
        """
        if self.progress.total_films == 0:
            self.progress.total_films = total_films
            self.save_progress()
            logger.info(f"Initialized progress with {total_films} total films")
        elif self.progress.total_films != total_films:
            logger.warning(
                f"Total films changed from {self.progress.total_films} to {total_films}"
            )
            self.progress.total_films = total_films
            self.save_progress()

    def get_tested_set(self) -> Set[str]:
        """
        Get set of tested film IDs.

        Returns:
            Set of item IDs
        """
        return set(self.progress.tested_films)

    def get_next_batch(self, all_films: List[str], batch_size: int) -> List[str]:
        """
        Get next batch of untested films.

        Args:
            all_films: List of all film IDs
            batch_size: Number of films to return

        Returns:
            List of film IDs to test
        """
        tested_set = self.get_tested_set()
        untested = [film_id for film_id in all_films if film_id not in tested_set]

        batch = untested[:batch_size]
        logger.info(f"Selected {len(batch)} films for next batch")
        return batch

    def mark_as_tested(self, item_id: str, is_defect: bool = False) -> None:
        """
        Mark a film as tested.

        Args:
            item_id: Jellyfin item ID
            is_defect: Whether the film is defective
        """
        if item_id not in self.progress.tested_films:
            self.progress.tested_films.append(item_id)

        if is_defect and item_id not in self.progress.defect_films:
            self.progress.defect_films.append(item_id)

        # Save after each film to prevent data loss
        self.save_progress()

    def is_completed(self) -> bool:
        """
        Check if all films have been tested.

        Returns:
            True if all films tested, False otherwise
        """
        if self.progress.total_films == 0:
            return False

        return len(self.progress.tested_films) >= self.progress.total_films

    def get_completion_percentage(self) -> float:
        """
        Calculate completion percentage.

        Returns:
            Percentage of films tested (0-100)
        """
        if self.progress.total_films == 0:
            return 0.0

        return (len(self.progress.tested_films) / self.progress.total_films) * 100

    def get_stats(self) -> dict:
        """
        Get current statistics.

        Returns:
            Dictionary with statistics
        """
        tested_count = len(self.progress.tested_films)
        defect_count = len(self.progress.defect_films)
        ok_count = tested_count - defect_count

        return {
            'total': self.progress.total_films,
            'tested': tested_count,
            'ok': ok_count,
            'defect': defect_count,
            'percentage': self.get_completion_percentage(),
            'remaining': self.progress.total_films - tested_count
        }

    def is_film_tested(self, item_id: str) -> bool:
        """
        Check if a film has been tested.

        Args:
            item_id: Jellyfin item ID

        Returns:
            True if tested, False otherwise
        """
        return item_id in self.progress.tested_films

    def is_film_defect(self, item_id: str) -> bool:
        """
        Check if a film is marked as defective.

        Args:
            item_id: Jellyfin item ID

        Returns:
            True if defective, False otherwise
        """
        return item_id in self.progress.defect_films
