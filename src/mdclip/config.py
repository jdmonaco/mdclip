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
# The 'default' template is used when no other template matches
templates:
  # GitHub repositories and pages
  - name: github
    triggers:
      - "https://github.com/"
      - "^https://[\\\\w-]+\\\\.github\\\\.io/"
    folder: Reference/Software
    tags:
      - webclip
      - software
      - github
    filename: "{{title}}"
    properties:
      type: repository

  # Stack Overflow questions
  - name: stackoverflow
    triggers:
      - "stackoverflow.com/questions"
      - "stackexchange.com/questions"
    folder: Reference/Code
    tags:
      - webclip
      - code
      - stackoverflow
    filename: "{{title}}"

  # Documentation sites
  - name: documentation
    triggers:
      - "docs."
      - "readthedocs.io"
      - "developer."
      - "/docs/"
    folder: Reference/Docs
    tags:
      - webclip
      - docs
    filename: "{{title}}"

  # Wikipedia articles
  - name: wikipedia
    triggers:
      - "wikipedia.org/wiki"
    folder: Reference/Wikipedia
    tags:
      - webclip
      - reference
      - wikipedia
    filename: "{{title}}"

  # arXiv papers
  - name: arxiv
    triggers:
      - "arxiv.org"
    folder: Reference/Papers
    tags:
      - webclip
      - paper
      - arxiv
    filename: "{{title}}"
    properties:
      type: paper

  # Hacker News
  - name: hackernews
    triggers:
      - "news.ycombinator.com"
    folder: Inbox/News
    tags:
      - webclip
      - news
      - hackernews
    filename: "{{title}}"

  # Default template (required - used when no other template matches)
  - name: default
    folder: Inbox/Clips
    tags:
      - webclip
    filename: "{{title}} {{date}}"
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
