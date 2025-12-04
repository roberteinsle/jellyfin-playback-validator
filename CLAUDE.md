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
# Run validation (processes next 10 untested movies)
python -m src.main

# Reset progress and start over
rm progress.json  # or: del progress.json on Windows
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

### Data Flow

1. main.py loads config and initializes all components
2. JellyfinClient fetches all movies from server (filtered by Type='Movie')
3. ProgressTracker determines which movies need testing (set difference)
4. Main loop processes max N movies (default: 10):
   - Validator tests each movie via JellyfinClient.test_playback()
   - On failure: tag added + written to defective_movies.txt
   - ProgressTracker.mark_as_tested() called after each (saves JSON)
5. Rich UI displays summary and instructs user to re-run for next batch

### Playback Validation Logic

The `test_playback()` method validates movies by:
1. POST to `/Items/{itemId}/PlaybackInfo` with DeviceProfile
2. Checking response for MediaSources array (empty = defective file)
3. Verifying SupportsDirectStream or SupportsDirectPlay (both false = corrupt)
4. Checking for ErrorCode field in response

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

### Error Handling
- Network/API errors caught per-movie (logged but don't stop batch)
- KeyboardInterrupt gracefully saves progress
- Defective movies are expected (not exceptions)

## File Locations

- **config.json** - User's Jellyfin credentials (not in repo)
- **progress.json** - Runtime state (created on first run)
- **defective_movies.txt** - Human-readable backup of defective movies
- **jellyfin_validator.log** - Detailed logging output

## Dependencies

- **requests** - HTTP client for Jellyfin API
- **rich** - Terminal UI (progress bars, tables, colors)
- **pydantic** - Configuration validation and type safety
