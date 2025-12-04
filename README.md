# Jellyfin Playback Validator

Python CLI application for validating Jellyfin movies through playback stream tests. The app identifies defective movie files, tags them, and creates a backup list.

## Features

- **Batch Processing**: Tests a maximum of 10 movies per run (configurable)
- **Progress Tracking**: Saves progress between runs
- **Playback Tests**: Uses Jellyfin's PlaybackInfo API
- **Automatic Tagging**: Adds "DEFECTIVE" tag to broken movies
- **Backup File**: Creates TXT file with defective movies and paths
- **Rich CLI**: Beautiful progress display with rich library
- **Sequential Processing**: Protects server through individual requests

## Requirements

- Python 3.10 or higher
- Jellyfin Server with API access
- API Key and User ID from Jellyfin

## Installation

1. Clone or download repository:
```bash
cd jellyfin-playback-validator
```

2. Create virtual environment (recommended):
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create configuration:
```bash
# Copy example configuration
cp config.example.json config.json  # Linux/Mac
copy config.example.json config.json  # Windows

# Edit config.json with your Jellyfin credentials
```

## Configuration

Edit `config.json` with your Jellyfin data:

```json
{
  "jellyfin": {
    "base_url": "https://your-jellyfin-server.com",
    "web_base": "https://your-jellyfin-server.com",
    "api_key": "your-api-key-here",
    "user_id": "your-user-id-here"
  },
  "validation": {
    "max_films_per_run": 10,
    "timeout_seconds": 30,
    "defect_tag": "DEFECTIVE",
    "pause_between_requests": 1.0
  },
  "output": {
    "backup_file": "defective_movies.txt",
    "progress_file": "progress.json"
  }
}
```

### Getting Jellyfin API Key

1. Open Jellyfin Web Interface
2. Go to Dashboard → API Keys
3. Create a new API Key
4. Copy the key into `config.json`

### Finding User ID

1. Open Jellyfin Web Interface
2. Go to Dashboard → Users
3. Click on your user
4. The User ID is in the URL: `/web/index.html#!/users/user.html?userId=YOUR_USER_ID`

## Usage

### Basic Usage

Start validation:

```bash
python -m src.main
```

The script will:
1. Load the next 10 untested movies
2. Test each movie sequentially
3. Tag defective movies
4. Save progress
5. Display summary

### Multiple Runs

Since the script only tests 10 movies per run, simply execute it multiple times:

```bash
# Run 1: Movies 1-10
python -m src.main

# Run 2: Movies 11-20
python -m src.main

# Run 3: Movies 21-30
python -m src.main

# etc...
```

Progress is automatically saved in `progress.json`.

### Example Output

```
═══════════════════════════════════
   Jellyfin Playback Validator
═══════════════════════════════════
Server: https://tv.einsle.com

Progress: 150/2313 movies tested (6.5%)
Status: OK: 145 | DEFECTIVE: 5

Testing Batch 16/232

⠋ Testing: Avatar (2009) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3/10 30%

  ✓ Avatar (2009)
  ✓ Inception (2010)
  ✗ The Lucky One (2012) - DEFECTIVE
  ✓ Interstellar (2014)
  ...

═══ Summary ═══
Tested       10 movies
OK           9 movies
DEFECTIVE    1 movie
Progress     160/2313 (6.9%)

Remaining: 2153 movies
Run the script again to continue.
```

## Output Files

### progress.json

Stores validation progress:

```json
{
  "total_films": 2313,
  "tested_films": ["id1", "id2", ...],
  "defect_films": ["id3", "id5", ...]
}
```

### defective_movies.txt

Backup list of all defective movies:

```
=== Defective Movies ===
Created: 2025-12-04 15:30:45

- The Lucky One German DL 1080p BluRay x264-SONS (2012)
  /volume3/video2/Filme/_nzbs/The Lucky One German DL 1080p BluRay x264-SONS [tmdbid-446847]/The Lucky One German DL 1080p BluRay x264-SONS.mkv

- Another Broken Movie (2020)
  /volume3/video2/Filme/Another Broken Movie.mkv
```

### jellyfin_validator.log

Detailed log of all operations for debugging.

## Resetting Progress

To start from the beginning, simply delete `progress.json`:

```bash
# Windows
del progress.json

# Linux/Mac
rm progress.json
```

## Configuration Options

### validation.max_films_per_run

Number of movies per run (1-100). Default: 10

### validation.timeout_seconds

Timeout for API requests in seconds (5-120). Default: 30

### validation.defect_tag

Tag name for defective movies. Default: "DEFECTIVE"

### validation.pause_between_requests

Pause between requests in seconds (0-10). Default: 1.0
Increase this value if your server gets overloaded.

## Troubleshooting

### "Configuration file not found"

Create `config.json` based on `config.example.json`.

### "Request failed" / Timeout errors

- Check network connection to Jellyfin
- Increase `timeout_seconds` in configuration
- Verify API Key and User ID

### "No media sources found"

The movie file doesn't exist or is corrupt. This is an expected error for defective movies.

### Script interrupted

Progress is saved after each movie. Simply restart the script, it will continue where it left off.

## Technical Details

### Validation Method

The script uses Jellyfin's `/Items/{itemId}/PlaybackInfo` endpoint:

1. Sends POST request with DeviceProfile
2. Checks if MediaSources are present
3. Checks if DirectStream/DirectPlay is supported
4. Checks for error codes in response

### Tag Management

Tags are added via Jellyfin API:
1. Retrieve current tags of the movie
2. Add new tag
3. Update item

## License

This project is open source and free to use.

## Support

For issues or questions, please create an issue in the repository.
