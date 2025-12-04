"""Validation logic for Jellyfin movies."""

import time
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging

from .jellyfin_client import JellyfinClient, MovieItem

logger = logging.getLogger(__name__)


class MovieValidator:
    """Validates movie playback and tracks defective files."""

    def __init__(
        self,
        client: JellyfinClient,
        backup_file: Path,
        defect_tag: str = "DEFECTIVE",
        pause_between: float = 1.0
    ):
        """
        Initialize movie validator.

        Args:
            client: Jellyfin API client
            backup_file: Path to backup text file for defective movies
            defect_tag: Tag to add to defective movies
            pause_between: Seconds to pause between requests
        """
        self.client = client
        self.backup_file = backup_file
        self.defect_tag = defect_tag
        self.pause_between = pause_between

    def validate_movie(self, movie: MovieItem) -> bool:
        """
        Validate a single movie's playback capability.

        Args:
            movie: MovieItem to validate

        Returns:
            True if movie is playable, False if defective
        """
        logger.info(f"Validating: {movie.name} ({movie.year or 'N/A'})")

        # Test playback
        is_playable = self.client.test_playback(movie.item_id)

        if not is_playable:
            logger.warning(f"DEFECT found: {movie.name}")
            self._handle_defective_movie(movie)
        else:
            logger.debug(f"OK: {movie.name}")

        # Pause to avoid overwhelming the server
        if self.pause_between > 0:
            time.sleep(self.pause_between)

        return is_playable

    def _handle_defective_movie(self, movie: MovieItem) -> None:
        """
        Handle a defective movie: add tag and write to backup file.

        Args:
            movie: Defective MovieItem
        """
        # Add tag to Jellyfin
        tag_added = self.client.add_tag(movie.item_id, self.defect_tag)
        if tag_added:
            logger.info(f"Added tag '{self.defect_tag}' to {movie.name}")
        else:
            logger.error(f"Failed to add tag to {movie.name}")

        # Write to backup file
        self._write_to_backup(movie)

    def _write_to_backup(self, movie: MovieItem) -> None:
        """
        Write defective movie to backup text file.

        Args:
            movie: Defective MovieItem
        """
        try:
            # Create file with header if it doesn't exist
            if not self.backup_file.exists():
                with open(self.backup_file, 'w', encoding='utf-8') as f:
                    f.write("=== Defective Movies ===\n")
                    f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Append defective movie
            with open(self.backup_file, 'a', encoding='utf-8') as f:
                display_name = movie.name
                if movie.year:
                    display_name = f"{movie.name} ({movie.year})"

                f.write(f"- {display_name}\n")
                f.write(f"  {movie.path}\n\n")

            logger.debug(f"Wrote {movie.name} to backup file")

        except Exception as e:
            logger.error(f"Failed to write to backup file: {e}")

    def validate_batch(self, movies: list[MovieItem]) -> dict:
        """
        Validate a batch of movies.

        Args:
            movies: List of MovieItem objects to validate

        Returns:
            Dictionary with validation results
        """
        results = {
            'total': len(movies),
            'ok': 0,
            'defect': 0,
            'defective_movies': []
        }

        for i, movie in enumerate(movies, 1):
            logger.info(f"[{i}/{len(movies)}] Testing: {movie.name}")

            is_ok = self.validate_movie(movie)

            if is_ok:
                results['ok'] += 1
            else:
                results['defect'] += 1
                results['defective_movies'].append(movie)

        return results

    def get_backup_file_path(self) -> Path:
        """
        Get the path to the backup file.

        Returns:
            Path object
        """
        return self.backup_file
