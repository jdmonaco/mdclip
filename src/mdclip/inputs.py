"""Input parsing for mdclip - URLs, bookmarks HTML, and URL files."""

import re
from enum import Enum, auto
from pathlib import Path

from bs4 import BeautifulSoup


class InputType(Enum):
    """Types of input that mdclip can process."""

    URL = auto()
    BOOKMARKS_HTML = auto()
    URL_FILE = auto()


def is_valid_url(url: str) -> bool:
    """Check if a string is a valid HTTP(S) URL.

    Args:
        url: String to check

    Returns:
        True if valid URL
    """
    url = url.strip()
    if not url:
        return False

    # Must start with http:// or https://
    if not re.match(r"^https?://", url, re.IGNORECASE):
        return False

    # Basic format check - has a domain
    if not re.match(r"^https?://[^\s/]+", url, re.IGNORECASE):
        return False

    return True


def detect_input_type(input_str: str) -> InputType:
    """Detect the type of input.

    Args:
        input_str: The input string (URL, file path, etc.)

    Returns:
        InputType enum value
    """
    input_str = input_str.strip()

    # Check if it's a URL
    if input_str.lower().startswith(("http://", "https://")):
        return InputType.URL

    # Check if it's a file path
    path = Path(input_str).expanduser()
    if path.exists():
        # Check for bookmarks HTML
        if path.suffix.lower() == ".html":
            return InputType.BOOKMARKS_HTML
        # Otherwise treat as URL list file
        return InputType.URL_FILE

    # Default to URL (will fail validation later if invalid)
    return InputType.URL


def parse_input(input_str: str) -> list[str]:
    """Parse input and return list of URLs.

    Args:
        input_str: URL, path to bookmarks HTML, or path to URL list file

    Returns:
        List of valid URLs
    """
    input_type = detect_input_type(input_str)

    if input_type == InputType.URL:
        url = input_str.strip()
        if is_valid_url(url):
            return [url]
        return []

    path = Path(input_str).expanduser()

    if input_type == InputType.BOOKMARKS_HTML:
        return parse_bookmarks_html(path)

    if input_type == InputType.URL_FILE:
        return parse_url_file(path)

    return []


def parse_bookmarks_html(path: Path) -> list[str]:
    """Parse URLs from a bookmarks HTML export file.

    Handles exports from Chrome, Firefox, Safari, etc.

    Args:
        path: Path to bookmarks HTML file

    Returns:
        List of valid URLs found in the file
    """
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Try with different encoding
        content = path.read_text(encoding="latin-1")

    soup = BeautifulSoup(content, "html.parser")

    urls: list[str] = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if is_valid_url(href):
            urls.append(href)

    return urls


def parse_url_file(path: Path) -> list[str]:
    """Parse URLs from a text file (one URL per line).

    Args:
        path: Path to text file containing URLs

    Returns:
        List of valid URLs found in the file
    """
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="latin-1")

    urls: list[str] = []
    for line in content.splitlines():
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        if is_valid_url(line):
            urls.append(line)

    return urls
