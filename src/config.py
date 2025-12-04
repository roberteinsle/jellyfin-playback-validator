"""Configuration management for Jellyfin Playback Validator."""

import json
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class JellyfinConfig(BaseModel):
    """Jellyfin server configuration."""
    base_url: str
    web_base: str
    api_key: str
    user_id: str

    @field_validator('base_url', 'web_base')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URLs don't end with trailing slash."""
        return v.rstrip('/')


class ValidationConfig(BaseModel):
    """Validation settings."""
    max_films_per_run: int = Field(default=10, ge=1, le=100)
    timeout_seconds: int = Field(default=30, ge=5, le=120)
    defect_tag: str = Field(default="DEFECTIVE")
    pause_between_requests: float = Field(default=1.0, ge=0, le=10)


class OutputConfig(BaseModel):
    """Output file settings."""
    backup_file: str = Field(default="defective_movies.txt")
    progress_file: str = Field(default="progress.json")


class Config(BaseModel):
    """Main configuration model."""
    jellyfin: JellyfinConfig
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load configuration from JSON file.

    Args:
        config_path: Path to config file. Defaults to config.json in project root.

    Returns:
        Validated Config object

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config.json"

    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            f"Please create config.json based on config.example.json"
        )

    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)

    return Config(**config_data)


def create_example_config(output_path: Optional[Path] = None) -> None:
    """
    Create an example configuration file.

    Args:
        output_path: Where to save the example. Defaults to config.example.json
    """
    if output_path is None:
        output_path = Path(__file__).parent.parent / "config.example.json"

    example_config = {
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

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(example_config, f, indent=2, ensure_ascii=False)
