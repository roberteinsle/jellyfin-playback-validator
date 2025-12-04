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

    def get_all_movies(self) -> List[MovieItem]:
        """
        Fetch all movies from Jellyfin.

        Returns:
            List of MovieItem objects

        Raises:
            requests.RequestException: On API error
        """
        endpoint = f"/Users/{self.user_id}/Items"
        params = {
            'IncludeItemTypes': 'Movie',
            'Recursive': 'true',
            'Fields': 'Path,ProductionYear',
            'SortBy': 'SortName',
            'SortOrder': 'Ascending'
        }

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
            'UserId': self.user_id,
            'DeviceProfile': {
                'MaxStaticBitrate': 140000000,
                'MusicStreamingTranscodingBitrate': 384000
            }
        }

        try:
            response = self._make_request('POST', endpoint, json=payload)
            data = response.json()

            # Check if media sources are available
            media_sources = data.get('MediaSources', [])
            if not media_sources:
                logger.warning(f"No media sources found for item {item_id}")
                return False

            # Check if direct stream or direct play is supported
            first_source = media_sources[0]
            supports_direct = (
                first_source.get('SupportsDirectStream', False) or
                first_source.get('SupportsDirectPlay', False)
            )

            if not supports_direct:
                logger.warning(f"Item {item_id} doesn't support direct playback")
                return False

            # Check for error codes in response
            if data.get('ErrorCode'):
                logger.warning(f"Item {item_id} has error: {data.get('ErrorCode')}")
                return False

            logger.debug(f"Playback test successful for item {item_id}")
            return True

        except requests.RequestException as e:
            logger.error(f"Playback test failed for item {item_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during playback test for {item_id}: {e}")
            return False

    def add_tag(self, item_id: str, tag: str) -> bool:
        """
        Add a tag to a Jellyfin item.

        Args:
            item_id: Jellyfin item ID
            tag: Tag to add

        Returns:
            True if successful, False otherwise
        """
        # First, get current item details to retrieve existing tags
        try:
            item_endpoint = f"/Users/{self.user_id}/Items/{item_id}"
            response = self._make_request('GET', item_endpoint)
            item_data = response.json()

            # Get existing tags and add new one if not present
            existing_tags = item_data.get('Tags', [])
            if tag in existing_tags:
                logger.info(f"Tag '{tag}' already exists on item {item_id}")
                return True

            existing_tags.append(tag)

            # Update item with new tags
            update_endpoint = f"/Items/{item_id}"
            update_payload = {
                'Tags': existing_tags
            }

            response = self._make_request('POST', update_endpoint, json=update_payload)
            logger.info(f"Added tag '{tag}' to item {item_id}")
            return True

        except requests.RequestException as e:
            logger.error(f"Failed to add tag to item {item_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error adding tag to {item_id}: {e}")
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
