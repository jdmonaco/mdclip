"""YAML frontmatter generation for mdclip."""

import re
from datetime import datetime
from typing import Any

import yaml


# Common date format patterns to try when parsing
# Order matters - more specific patterns first
DATE_FORMATS = [
    # ISO 8601 formats
    "%Y-%m-%dT%H:%M:%S%z",      # 2024-01-15T14:30:00+00:00
    "%Y-%m-%dT%H:%M:%S.%f%z",   # 2024-01-15T14:30:00.000+00:00
    "%Y-%m-%dT%H:%M:%SZ",       # 2024-01-15T14:30:00Z
    "%Y-%m-%dT%H:%M:%S",        # 2024-01-15T14:30:00
    "%Y-%m-%d %H:%M:%S",        # 2024-01-15 14:30:00
    "%Y-%m-%d %H:%M",           # 2024-01-15 14:30
    "%Y-%m-%d",                 # 2024-01-15
    # US formats with slashes
    "%m/%d/%Y %I:%M%p",         # 01/15/2024 2:30PM
    "%m/%d/%Y, %I:%M%p",        # 01/15/2024, 2:30PM
    "%m/%d/%Y %H:%M",           # 01/15/2024 14:30
    "%m/%d/%Y",                 # 01/15/2024
    "%m/%d/%y",                 # 01/15/24
    # European formats
    "%d/%m/%Y",                 # 15/01/2024
    "%d-%m-%Y",                 # 15-01-2024
    "%d.%m.%Y",                 # 15.01.2024
    # Long formats
    "%B %d, %Y",                # January 15, 2024
    "%b %d, %Y",                # Jan 15, 2024
    "%d %B %Y",                 # 15 January 2024
    "%d %b %Y",                 # 15 Jan 2024
    "%B %d %Y",                 # January 15 2024
    # With weekday
    "%A, %B %d, %Y",            # Monday, January 15, 2024
    "%a, %B %d, %Y",            # Mon, January 15, 2024
    "%a %d %b %Y",              # Mon 15 Jan 2024
    # RFC 2822
    "%a, %d %b %Y %H:%M:%S",    # Mon, 15 Jan 2024 14:30:00
    "%a, %d %b %Y",             # Mon, 15 Jan 2024
]

# Regex to strip weekday prefix like "Weds " or "Wednesday "
WEEKDAY_PREFIX_PATTERN = re.compile(
    r"^(mon|tue|wed|thu|fri|sat|sun)[a-z]*\.?\s+",
    re.IGNORECASE,
)

# Regex to normalize am/pm spacing
AMPM_PATTERN = re.compile(r"(\d+:\d+)\s*(am|pm)", re.IGNORECASE)


def parse_date(date_str: str, output_format: str = "%Y-%m-%d") -> str:
    """Parse a date string and format it consistently.

    Attempts to parse dates in various common formats and returns
    a normalized date string. Falls back to the original string
    if parsing fails.

    Args:
        date_str: The date string to parse (e.g., "Weds 05/08/2025, 2:30pm")
        output_format: strftime format for output (default: "%Y-%m-%d")

    Returns:
        Formatted date string, or original string if parsing fails
    """
    if not date_str or not isinstance(date_str, str):
        return date_str if date_str else ""

    original = date_str
    date_str = date_str.strip()

    # Normalize: strip weekday prefix (e.g., "Weds " -> "")
    date_str = WEEKDAY_PREFIX_PATTERN.sub("", date_str)

    # Normalize: remove space before am/pm (e.g., "2:30 pm" -> "2:30pm")
    date_str = AMPM_PATTERN.sub(r"\1\2", date_str)

    # Normalize: strip timezone abbreviations like "EST", "PST"
    date_str = re.sub(r"\s+[A-Z]{2,4}$", "", date_str)

    # Try each format
    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.strftime(output_format)
        except ValueError:
            continue

    # Try with lowercase am/pm
    date_str_lower = date_str.lower()
    for fmt in DATE_FORMATS:
        if "%p" in fmt:
            try:
                parsed = datetime.strptime(date_str_lower, fmt.lower())
                return parsed.strftime(output_format)
            except ValueError:
                continue

    # Fallback: return original string
    return original


def build_frontmatter(
    metadata: dict[str, Any],
    template: Any,  # Template dataclass
    config: dict[str, Any],
    extra_tags: list[str] | None = None,
) -> str:
    """Build YAML frontmatter from metadata, template, and config.

    Args:
        metadata: Extracted metadata (title, url, author, description, etc.)
        template: The matched Template object
        config: Global configuration
        extra_tags: Additional tags from CLI

    Returns:
        YAML frontmatter string including --- delimiters
    """
    fm: dict[str, Any] = {}

    # Add default properties
    default_props = config.get("default_properties", ["title", "source", "created"])

    for prop in default_props:
        if prop == "title":
            fm["title"] = metadata.get("title", "Untitled")
        elif prop == "source":
            fm["source"] = metadata.get("url", "")
        elif prop == "created":
            date_format = config.get("date_format", "%Y-%m-%d %H:%M")
            fm["created"] = datetime.now().strftime(date_format)
        elif prop == "author":
            # Author may be a string or list from defuddle
            author = metadata.get("author")
            if author:
                fm["author"] = [author] if isinstance(author, str) else author
        elif prop == "description":
            if metadata.get("description"):
                fm["description"] = metadata["description"]
        elif prop == "published":
            if metadata.get("published"):
                date_format = config.get("date_format", "%Y-%m-%d")
                fm["published"] = parse_date(metadata["published"], date_format)

    # Add tags from template and CLI
    tags = list(template.tags) if template.tags else ["webclip"]
    if extra_tags:
        for tag in extra_tags:
            if tag not in tags:
                tags.append(tag)
    fm["tags"] = tags

    # Add template-specific properties
    if template.properties:
        fm.update(template.properties)

    # Generate YAML
    yaml_content = yaml.dump(
        fm,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=1000,  # Prevent line wrapping
    )

    return f"---\n{yaml_content}---\n\n"


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse frontmatter from markdown content.

    Args:
        content: Markdown content potentially starting with frontmatter

    Returns:
        Tuple of (frontmatter dict, remaining content)
    """
    if not content.startswith("---"):
        return {}, content

    # Find the closing ---
    end_idx = content.find("---", 3)
    if end_idx == -1:
        return {}, content

    yaml_content = content[3:end_idx].strip()
    remaining = content[end_idx + 3:].lstrip("\n")

    try:
        fm = yaml.safe_load(yaml_content) or {}
    except yaml.YAMLError:
        return {}, content

    return fm, remaining
