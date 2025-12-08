"""Configuration loading and management for mdclip."""

from pathlib import Path
from typing import Any

import yaml


# Default configuration values
DEFAULT_CONFIG: dict[str, Any] = {
    "vault": "~/Documents/Obsidian/Notes",
    "date_format": "%Y-%m-%d",
    "filename_date_format": "%Y-%m-%d",
    "default_folder": "Inbox/Clips",
    "auto_format": False,
    "skip_existing": False,
    "open_in_obsidian": True,
    "default_properties": ["title", "source", "author", "created", "published", "description"],
    "templates": [
        {
            "name": "default",
            "folder": "Inbox/Clips",
            "tags": ["webclip"],
            "filename": "{{title}}",
        }
    ],
}

# Default config file content with rich template examples
DEFAULT_CONFIG_YAML = """\
# mdclip configuration
# Location: ~/.mdclip.yml

# Path to your Obsidian vault (or any directory for markdown notes)
vault: ~/Documents/Obsidian/Notes

# Date format for frontmatter 'created' field (can be customized, e.g., "%Y-%m-%d %H:%M")
date_format: "%Y-%m-%d"

# Date format for filename templates
filename_date_format: "%Y-%m-%d"

# Default output folder (relative to vault)
default_folder: Inbox/Clips

# Auto-format output with mdformat (if installed)
# Disabled by default - set to true to enable
auto_format: false

# Skip URLs if a file already exists with the same source URL
# When false (default), appends (1), (2), etc. to filename
# Can also be enabled per-run with --skip-existing flag
skip_existing: false

# Open clipped note after single-URL processing
# Inside vault: opens in Obsidian; outside vault: opens in glow/less
# Disable with --no-open flag or set to false here
open_in_obsidian: true

# Default frontmatter properties (always included when available)
# Supported: title, source, author, created, published, description, tags
default_properties:
  - title
  - source
  - author
  - created
  - published
  - description
  - tags

# Templates define how URLs are processed based on pattern matching
# Templates are checked in order; first match wins
# Built-in triggers (@name) provide smart domain+path matching
# The 'default' template is used when no other template matches
templates:
  # Scientific journals and publishers (113 domains)
  - name: papers
    triggers:
      - "@academic"
    folder: Reference/Papers
    tags: [paper, research]

  # Software documentation (35 domains)
  - name: documentation
    triggers:
      - "@docs"
    folder: Reference/Docs
    tags: [docs, reference]

  # Educational content and .edu sites
  - name: education
    triggers:
      - "@edu"
    folder: Reference/Education
    tags: [education, learning]

  # Government sites (.gov/.mil TLDs)
  - name: government
    triggers:
      - "@gov"
    folder: Reference/Government
    tags: [government, official]

  # Magazines and longform journalism (75 domains)
  - name: longform
    triggers:
      - "@longform"
    folder: Reference/Longform
    tags: [longform, magazine]

  # US-focused news sources (50 domains)
  - name: news
    triggers:
      - "@news"
    folder: Reference/News
    tags: [news, current-events]

  # Science and technology publications (35 domains)
  - name: scitech
    triggers:
      - "@scitech"
    folder: Reference/SciTech
    tags: [scitech, reading]

  # Social media and discussion platforms (35 domains)
  - name: social
    triggers:
      - "@social"
    folder: Reference/Social
    tags: [social, discussion]

  # Wikis and encyclopedias (25 domains)
  - name: wiki
    triggers:
      - "@wiki"
    folder: Reference/Wiki
    tags: [wiki, reference]

  # Default template (required - catches unmatched URLs)
  - name: default
    folder: Inbox/Clips
    tags: [webclip]
"""


def get_config_path() -> Path:
    """Return the default config file path (~/.mdclip.yml)."""
    return Path.home() / ".mdclip.yml"


def config_exists(path: Path | None = None) -> bool:
    """Check if config file exists."""
    config_path = path or get_config_path()
    return config_path.exists()


def init_config(path: Path | None = None) -> Path:
    """Initialize default config file. Returns the path to the created file."""
    config_path = path or get_config_path()
    if config_path.exists():
        raise FileExistsError(f"Config file already exists: {config_path}")
    config_path.write_text(DEFAULT_CONFIG_YAML, encoding="utf-8")
    return config_path


def load_config(path: Path | None = None) -> tuple[dict[str, Any], bool]:
    """Load configuration from file, auto-creating if missing.

    Args:
        path: Optional path to config file. Uses ~/.mdclip.yml if not specified.

    Returns:
        Tuple of (config dict, was_created flag). was_created is True if
        config file was auto-created on this call.
    """
    config_path = path or get_config_path()
    was_created = False

    # Start with defaults
    config = DEFAULT_CONFIG.copy()

    if not config_path.exists():
        # Auto-create config file
        config_path.write_text(DEFAULT_CONFIG_YAML, encoding="utf-8")
        was_created = True

    try:
        with open(config_path, encoding="utf-8") as f:
            file_config = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file {config_path}: {e}") from e

    # Merge file config into defaults
    config = _merge_dicts(config, file_config)

    # Expand paths
    if "vault" in config:
        config["vault"] = str(Path(config["vault"]).expanduser())

    return config, was_created


def merge_config(
    file_config: dict[str, Any], cli_overrides: dict[str, Any]
) -> dict[str, Any]:
    """Merge CLI overrides into file configuration.

    CLI overrides take precedence over file config.
    """
    return _merge_dicts(file_config, cli_overrides)


def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries. Override values take precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def get_template_by_name(
    name: str, config: dict[str, Any]
) -> dict[str, Any] | None:
    """Find a template by name in the config."""
    for template in config.get("templates", []):
        if template.get("name") == name:
            return template
    return None
