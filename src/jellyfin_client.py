"""Jellyfin API Client for movie validation."""

import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class MovieItem:
    """Represents a movie from Jellyfin."""
    item_id: str
    name: str
    path: str
    year: Optional[int] = None


class JellyfinClient:
    """Client for interacting with Jellyfin API."""

    def __init__(self, base_url: str, api_key: str, user_id: str, timeout: int = 30):
        """
        Initialize Jellyfin client.

        Args:
            base_url: Jellyfin server URL
            api_key: API key for authentication
            user_id: User ID for requests
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.user_id = user_id
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'X-Emby-Token': api_key,
            'Content-Type': 'application/json'
        })

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make HTTP request to Jellyfin API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments for requests

        Returns:
            Response object

        Raises:
            requests.RequestException: On request failure
        """
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault('timeout', self.timeout)

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"Request failed for {endpoint}: {e}")
            raise

    def get_all_movies(self, filter_recent: bool = False, limit: Optional[int] = None) -> List[MovieItem]:
        """
        Fetch all movies from Jellyfin.

        Args:
            filter_recent: If True, fetch only recently added movies
            limit: Maximum number of movies to return (only used if filter_recent=True)

        Returns:
            List of MovieItem objects

        Raises:
            requests.RequestException: On API error
        """
        endpoint = f"/Users/{self.user_id}/Items"
        params = {
            'IncludeItemTypes': 'Movie',
            'Recursive': 'true',
            'Fields': 'Path,ProductionYear,DateCreated',
        }

        if filter_recent and limit:
            # Sort by date added (descending) and limit
            params['SortBy'] = 'DateCreated'
            params['SortOrder'] = 'Descending'
            params['Limit'] = str(limit)
        else:
            # Sort by name for all movies
            params['SortBy'] = 'SortName'
            params['SortOrder'] = 'Ascending'

        try:
            response = self._make_request('GET', endpoint, params=params)
            data = response.json()

            movies = []
            for item in data.get('Items', []):
                movie = MovieItem(
                    item_id=item['Id'],
                    name=item.get('Name', 'Unknown'),
                    path=item.get('Path', ''),
                    year=item.get('ProductionYear')
                )
                movies.append(movie)

            if filter_recent and limit:
                logger.info(f"Retrieved {len(movies)} recently added movies from Jellyfin (limit: {limit})")
            else:
                logger.info(f"Retrieved {len(movies)} movies from Jellyfin")
            return movies

        except Exception as e:
            logger.error(f"Failed to retrieve movies: {e}")
            raise

    def test_playback(self, item_id: str) -> bool:
        """
        Test if a movie can be played back.

        Args:
            item_id: Jellyfin item ID

        Returns:
            True if playback is possible, False otherwise
        """
        endpoint = f"/Items/{item_id}/PlaybackInfo"
        payload = {
            'UserId': self.user_id
        }

        try:
            response = self._make_request('POST', endpoint, json=payload)
            data = response.json()

            # Check for error codes in response
            if data.get('ErrorCode'):
                logger.warning(f"Item {item_id} has error: {data.get('ErrorCode')}")
                return False

            # Check if media sources are available
            media_sources = data.get('MediaSources', [])
            if not media_sources:
                logger.warning(f"No media sources found for item {item_id}")
                return False

            # Check if file exists and has valid properties
            first_source = media_sources[0]

            # File must have a valid path
            if not first_source.get('Path'):
                logger.warning(f"Item {item_id} has no file path")
                return False

            # File must have a size > 0
            file_size = first_source.get('Size', 0)
            if file_size == 0:
                logger.warning(f"Item {item_id} has zero file size")
                return False

            # Must have at least one video stream
            media_streams = first_source.get('MediaStreams', [])
            has_video = any(stream.get('Type') == 'Video' for stream in media_streams)
            if not has_video:
                logger.warning(f"Item {item_id} has no video stream")
                return False

            logger.debug(f"Playback test successful for item {item_id}")
            return True

        except requests.RequestException as e:
            logger.error(f"Playback test failed for item {item_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during playback test for {item_id}: {e}")
            return False

    def get_item_details(self, item_id: str) -> Optional[MovieItem]:
        """
        Get detailed information about a specific item.

        Args:
            item_id: Jellyfin item ID

        Returns:
            MovieItem object or None if failed
        """
        endpoint = f"/Users/{self.user_id}/Items/{item_id}"
        params = {
            'Fields': 'Path,ProductionYear'
        }

        try:
            response = self._make_request('GET', endpoint, params=params)
            item = response.json()

            return MovieItem(
                item_id=item['Id'],
                name=item.get('Name', 'Unknown'),
                path=item.get('Path', ''),
                year=item.get('ProductionYear')
            )

        except Exception as e:
            logger.error(f"Failed to get item details for {item_id}: {e}")
            return None
