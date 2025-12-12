# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Jellyfin Playback Validator is a Python CLI tool that validates movie playback capabilities on Jellyfin servers. It processes movies in batches, identifies defective files through API testing, and tracks progress across multiple runs.

## Running the Application

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Create configuration from example
cp config.example.json config.json
# Then edit config.json with actual Jellyfin credentials
```

### Execution
```bash
# Run validation (processes next batch of untested movies)
python -m src.main

# Reset progress and start over
rm progress.json  # Windows: del progress.json

# Test API connectivity (if test_api.py exists in project root)
python test_api.py
```

## Architecture

### Core Components

**src/main.py** - CLI orchestration layer
- Entry point that coordinates all components
- Handles Rich UI (progress bars, tables, colored output)
- Manages batch processing loop and user feedback

**src/jellyfin_client.py** - Jellyfin API abstraction
- Wraps all Jellyfin API interactions via requests Session
- Key method: `test_playback()` uses `/Items/{itemId}/PlaybackInfo` endpoint
- Returns `MovieItem` dataclass objects containing id, name, path, year
- All requests use `X-Emby-Token` header for authentication

**src/validator.py** - Validation orchestration
- Coordinates playback testing via JellyfinClient
- Handles defect marking: adds tags via API + writes to backup TXT file
- Implements configurable pause between requests to avoid server overload

**src/progress_tracker.py** - Stateful batch processing
- Persists progress to JSON after each movie (survives crashes/interruptions)
- Tracks: total_films, tested_films (list of IDs), defect_films (list of IDs)
- Provides `get_next_batch()` to fetch untested movies for sequential processing

**src/config.py** - Pydantic-based configuration
- Validates config.json schema at startup
- Three sections: jellyfin (credentials), validation (behavior), output (file paths)
- Use `load_config()` to get validated Config object
- Supports filtering modes: `filter_recent_only` tests only recently added movies (useful for incremental validation)

### Data Flow

1. main.py loads config and initializes all components
2. JellyfinClient fetches movies from server:
   - If `filter_recent_only=true`: fetches N most recently added movies (sorted by DateCreated DESC)
   - If `filter_recent_only=false`: fetches all movies (sorted by SortName ASC)
3. ProgressTracker determines which movies need testing (set difference)
4. Main loop processes max N movies (default: 10):
   - Validator tests each movie via JellyfinClient.test_playback()
   - On failure: written to defective_movies.txt
   - ProgressTracker.mark_as_tested() called after each (saves JSON)
5. Rich UI displays summary and instructs user to re-run for next batch

### Playback Validation Logic

The `test_playback()` method in [jellyfin_client.py](src/jellyfin_client.py#L124) validates movies through multiple checks:
1. POST to `/Items/{itemId}/PlaybackInfo` endpoint
2. Check for ErrorCode field in response (indicates API-level error)
3. Verify MediaSources array exists and is not empty
4. Validate first MediaSource has:
   - Valid Path field (file location exists)
   - Size > 0 (file is not empty)
   - At least one MediaStream with Type='Video' (has video track)

This simulates what a real Jellyfin player does before playback, without downloading content.

## Important Patterns

### Configuration Security
- config.json contains API credentials and is .gitignored
- config.example.json is the template for users
- Never commit actual credentials

### Stateful Resumability
- progress.json enables restart-from-failure
- Each movie marked tested immediately after validation
- Batch size limits prevent overwhelming servers or sessions

### Sequential Processing
- No parallelization by design (configurable pause_between_requests)
- Protects Jellyfin server from rate limiting / overload
- Users run script multiple times until all movies tested
- Two modes: test all movies incrementally OR test only recent additions (see filter_recent_only config)

### Error Handling
- Network/API errors caught per-movie (logged but don't stop batch)
- KeyboardInterrupt gracefully saves progress
- Defective movies are expected (not exceptions)

## File Locations

- **config.json** - User's Jellyfin credentials (gitignored, create from config.example.json)
- **config.example.json** - Template for user configuration (committed to repo)
- **progress.json** - Runtime state tracking tested/defective movies (created on first run)
- **defective_movies.txt** - Human-readable backup of defective movies with paths
- **jellyfin_validator.log** - Detailed logging output (both file and console)

## Configuration Options

### Core Settings

**validation.filter_recent_only** (boolean, default: true)
- When true: only tests the N most recently added movies (set by recent_movies_limit)
- When false: tests all movies in the library
- Use true for ongoing validation of new additions, false for complete library validation

**validation.recent_movies_limit** (int, default: 50)
- Number of recent movies to fetch when filter_recent_only=true
- Range: 1-1000
- Movies sorted by DateCreated (descending) from Jellyfin

**validation.max_films_per_run** (int, default: 10)
- Number of movies to test in each run
- Range: 1-100

**validation.pause_between_requests** (float, default: 1.0)
- Seconds to wait between API requests
- Range: 0-10
- Increase if server shows signs of overload

**validation.timeout_seconds** (int, default: 30)
- Timeout for API requests in seconds
- Range: 5-120
- Increase if server responses are slow

**validation.defect_tag** (string, default: "DEFECTIVE")
- Tag name to add to defective movies in Jellyfin
- Allows custom tag naming for organization

**jellyfin.web_base** (string)
- Base URL for Jellyfin web interface
- Used for generating links to movies in UI (not for API calls)

## Dependencies

- **requests** - HTTP client for Jellyfin API
- **rich** - Terminal UI (progress bars, tables, colors)
- **pydantic** - Configuration validation and type safety
