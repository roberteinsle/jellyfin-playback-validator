"""Test script to analyze Jellyfin PlaybackInfo API response."""

import requests
import json

# Configuration
BASE_URL = "https://tv.einsle.com"
API_KEY = "3e1e7c4998064adda1ffcfafaf1c125a"
USER_ID = "693a254c5e134e95b7a97b2fddfa794b"

# Setup session
session = requests.Session()
session.headers.update({
    'X-Emby-Token': API_KEY,
    'Content-Type': 'application/json'
})

print("=" * 80)
print("JELLYFIN API TEST - Fetching first movie")
print("=" * 80)

# Get first movie
print("\n1. Fetching movie list...")
response = session.get(
    f"{BASE_URL}/Users/{USER_ID}/Items",
    params={
        'IncludeItemTypes': 'Movie',
        'Recursive': 'true',
        'Fields': 'Path,ProductionYear',
        'SortBy': 'SortName',
        'SortOrder': 'Ascending',
        'Limit': 1
    },
    timeout=30
)

movies = response.json()
if not movies.get('Items'):
    print("No movies found!")
    exit(1)

movie = movies['Items'][0]
print(f"   Movie: {movie['Name']} ({movie.get('ProductionYear', 'N/A')})")
print(f"   ID: {movie['Id']}")
print(f"   Path: {movie.get('Path', 'N/A')}")

# Test playback
print("\n2. Testing PlaybackInfo API...")
playback_response = session.post(
    f"{BASE_URL}/Items/{movie['Id']}/PlaybackInfo",
    json={
        'UserId': USER_ID,
        'DeviceProfile': {
            'MaxStaticBitrate': 140000000,
            'MusicStreamingTranscodingBitrate': 384000
        }
    },
    timeout=30
)

print(f"   Status Code: {playback_response.status_code}")

if playback_response.status_code == 200:
    playback_data = playback_response.json()

    print("\n3. Response Analysis:")
    print(f"   MediaSources present: {len(playback_data.get('MediaSources', []))}")

    if playback_data.get('MediaSources'):
        source = playback_data['MediaSources'][0]
        print(f"   SupportsDirectStream: {source.get('SupportsDirectStream')}")
        print(f"   SupportsDirectPlay: {source.get('SupportsDirectPlay')}")
        print(f"   SupportsTranscoding: {source.get('SupportsTranscoding')}")
        print(f"   Container: {source.get('Container')}")

    if playback_data.get('ErrorCode'):
        print(f"   ERROR CODE: {playback_data['ErrorCode']}")

    print("\n4. Full Response (formatted):")
    print(json.dumps(playback_data, indent=2))
else:
    print(f"   ERROR: {playback_response.text}")

print("\n" + "=" * 80)
