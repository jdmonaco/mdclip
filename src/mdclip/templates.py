"""Template matching and filename generation for mdclip."""

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any


# Regex metacharacters that indicate a pattern is a regex
REGEX_METACHARACTERS = r"^$.*+?{}[]()|\\"


@dataclass
class Template:
    """A template for processing URLs."""

    name: str
    folder: str = "Inbox/Clips"
    tags: list[str] = field(default_factory=lambda: ["webclip"])
    filename: str = "{{title}}"
    triggers: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    gather_opts: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Template":
        """Create a Template from a dictionary."""
        return cls(
            name=data.get("name", "default"),
            folder=data.get("folder", "Inbox/Clips"),
            tags=data.get("tags", ["webclip"]),
            filename=data.get("filename", "{{title}}"),
            triggers=data.get("triggers", []),
            properties=data.get("properties", {}),
            gather_opts=data.get("gather_opts", []),
        )


def is_regex_pattern(pattern: str) -> bool:
    """Check if a pattern should be treated as a regex.

    A pattern is considered regex if it:
    - Starts with '^' (anchor)
    - Contains regex metacharacters beyond simple wildcards
    """
    if pattern.startswith("^"):
        return True
    # Check for regex metacharacters (excluding common URL chars)
    for char in REGEX_METACHARACTERS:
        if char in pattern and char not in "/.":
            return True
    return False


def matches_pattern(url: str, pattern: str) -> bool:
    """Check if a URL matches a pattern.

    Args:
        url: The URL to check
        pattern: Either a regex pattern or a substring to match

    Returns:
        True if the URL matches the pattern
    """
    if is_regex_pattern(pattern):
        try:
            return bool(re.search(pattern, url, re.IGNORECASE))
        except re.error:
            # Invalid regex, treat as substring
            return pattern.lower() in url.lower()
    else:
        # Case-insensitive substring match
        return pattern.lower() in url.lower()


def match_template(url: str, templates: list[dict[str, Any]]) -> Template:
    """Find the first matching template for a URL.

    Templates are checked in order. The first template with a matching
    trigger wins. If no template matches, returns the 'default' template.

    Args:
        url: The URL to match
        templates: List of template dictionaries from config

    Returns:
        The matching Template object
    """
    default_template = None

    for template_dict in templates:
        template = Template.from_dict(template_dict)

        # Track the default template
        if template.name == "default":
            default_template = template

        # Check triggers
        triggers = template_dict.get("triggers", [])
        if not triggers:
            # No triggers means this is the default/fallback
            continue

        for trigger in triggers:
            if matches_pattern(url, trigger):
                return template

    # Return default template if found, otherwise create a basic one
    if default_template:
        return default_template

    return Template(name="default")


def render_filename(template: str, variables: dict[str, str]) -> str:
    """Render a filename template with variables.

    Supported variables:
    - {{title}} - Page title
    - {{date}} - Current date (formatted per config)
    - {{slug}} - Slugified title
    - {{domain}} - URL domain

    Args:
        template: Filename template string
        variables: Dictionary of variable values

    Returns:
        Rendered filename (without extension)
    """
    result = template
    for key, value in variables.items():
        placeholder = "{{" + key + "}}"
        result = result.replace(placeholder, value)
    return result


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug.

    - Lowercase
    - Replace spaces and punctuation with hyphens
    - Remove consecutive hyphens
    - Strip leading/trailing hyphens
    """
    # Normalize unicode
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    # Lowercase
    text = text.lower()

    # Replace non-alphanumeric with hyphens
    text = re.sub(r"[^a-z0-9]+", "-", text)

    # Remove consecutive hyphens
    text = re.sub(r"-+", "-", text)

    # Strip leading/trailing hyphens
    text = text.strip("-")

    return text


def sanitize_filename(name: str, max_length: int = 100) -> str:
    """Sanitize a string for use as a filename.

    - Remove invalid characters: < > : " / \\ | ? *
    - Collapse whitespace
    - Limit length
    - Handle edge cases (empty, dots only, etc.)

    Args:
        name: The filename to sanitize
        max_length: Maximum length (default 100)

    Returns:
        Sanitized filename (without extension)
    """
    if not name:
        return "Untitled"

    # Remove invalid filename characters
    invalid_chars = r'[<>:"/\\|?*]'
    name = re.sub(invalid_chars, "", name)

    # Collapse whitespace
    name = re.sub(r"\s+", " ", name)

    # Strip leading/trailing whitespace and dots
    name = name.strip(" .")

    # Handle empty result
    if not name:
        return "Untitled"

    # Truncate to max length, trying to break at word boundary
    if len(name) > max_length:
        # Try to break at last space before limit
        truncated = name[:max_length]
        last_space = truncated.rfind(" ")
        if last_space > max_length // 2:
            name = truncated[:last_space]
        else:
            name = truncated

    # Strip trailing whitespace/dots again after truncation
    name = name.strip(" .")

    return name or "Untitled"
