"""Input parsing for mdclip - URLs, bookmarks HTML, and URL files."""

import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

from bs4 import BeautifulSoup, Tag


class InputType(Enum):
    """Types of input that mdclip can process."""

    URL = auto()
    BOOKMARKS_HTML = auto()
    URL_FILE = auto()
    MARKDOWN_FILE = auto()


# Pattern to match markdown links: [text](url)
MARKDOWN_LINK_PATTERN = re.compile(r'\[([^\]]*)\]\((https?://[^\s)]+)\)')


@dataclass
class BookmarkSection:
    """A section in a bookmarks file."""

    title: str
    depth: int = 0
    urls: list[str] = field(default_factory=list)
    children: list["BookmarkSection"] = field(default_factory=list)

    @property
    def total_urls(self) -> int:
        """Total URLs including children."""
        count = len(self.urls)
        for child in self.children:
            count += child.total_urls
        return count


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
        suffix = path.suffix.lower()
        # Check for bookmarks HTML
        if suffix == ".html":
            return InputType.BOOKMARKS_HTML
        # Check for markdown file
        if suffix == ".md":
            return InputType.MARKDOWN_FILE
        # Otherwise treat as URL list file
        return InputType.URL_FILE

    # Default to URL (will fail validation later if invalid)
    return InputType.URL


def parse_input(input_str: str) -> list[str]:
    """Parse input and return list of URLs.

    Args:
        input_str: URL, path to bookmarks HTML, markdown file, or URL list file

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

    if input_type == InputType.MARKDOWN_FILE:
        return parse_markdown_file(path)

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
        href = str(link["href"])
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

    return parse_text_for_urls(content)


def parse_markdown_file(path: Path) -> list[str]:
    """Parse URLs from a markdown file.

    Extracts URLs from markdown links [text](url) and plain URLs.

    Args:
        path: Path to markdown file

    Returns:
        List of valid URLs found in the file
    """
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="latin-1")

    return parse_text_for_urls(content)


def extract_markdown_links(text: str) -> list[str]:
    """Extract URLs from markdown links like [text](https://...).

    Args:
        text: Text containing markdown links

    Returns:
        List of URLs extracted from markdown link syntax
    """
    return [match.group(2) for match in MARKDOWN_LINK_PATTERN.finditer(text)]


def parse_text_for_urls(text: str) -> list[str]:
    """Parse text for URLs - both plain URLs and markdown links.

    Args:
        text: Text to parse

    Returns:
        List of valid URLs, deduplicated while preserving order
    """
    urls: list[str] = []

    # Extract markdown links first
    urls.extend(extract_markdown_links(text))

    # Then extract plain URLs (one per line, skip comments)
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if is_valid_url(line):
            urls.append(line)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_urls: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    return unique_urls


def read_clipboard_urls() -> list[str]:
    """Read URLs from clipboard via pbpaste (macOS).

    Returns:
        List of valid URLs from clipboard, or empty list if unavailable
    """
    try:
        result = subprocess.run(
            ["pbpaste"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return parse_text_for_urls(result.stdout)
    except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return []


def parse_bookmark_structure(path: Path) -> list[BookmarkSection]:
    """Parse bookmark HTML into hierarchical sections.

    Args:
        path: Path to bookmarks HTML file

    Returns:
        List of top-level BookmarkSection objects
    """
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="latin-1")

    soup = BeautifulSoup(content, "html.parser")
    sections: list[BookmarkSection] = []

    def parse_dl(dl: Tag, depth: int = 0) -> list[BookmarkSection]:
        """Recursively parse a DL element."""
        result: list[BookmarkSection] = []
        current_section: BookmarkSection | None = None

        for child in dl.children:
            if not isinstance(child, Tag):
                continue

            if child.name == "dt":
                # Check for H3 (section header) or A (bookmark link)
                h3 = child.find("h3")
                if h3:
                    # New section
                    title = h3.get_text(strip=True)
                    current_section = BookmarkSection(title=title, depth=depth)
                    result.append(current_section)

                    # Check for nested DL
                    nested_dl = child.find("dl")
                    if nested_dl and isinstance(nested_dl, Tag):
                        current_section.children = parse_dl(nested_dl, depth + 1)
                else:
                    # Bookmark link
                    link = child.find("a", href=True)
                    if link:
                        href = str(link.get("href", ""))
                        if is_valid_url(href):
                            if current_section:
                                current_section.urls.append(href)
                            elif result:
                                result[-1].urls.append(href)

        return result

    # Find the main DL element
    main_dl = soup.find("dl")
    if main_dl and isinstance(main_dl, Tag):
        sections = parse_dl(main_dl)

    return sections


def get_urls_from_section(section: BookmarkSection) -> list[str]:
    """Recursively collect all URLs from a section and its children.

    Args:
        section: BookmarkSection to collect URLs from

    Returns:
        List of all URLs in the section and its subsections
    """
    urls = list(section.urls)
    for child in section.children:
        urls.extend(get_urls_from_section(child))
    return urls


def flatten_sections(sections: list[BookmarkSection], prefix: str = "") -> list[tuple[str, BookmarkSection]]:
    """Flatten hierarchical sections into a list with display names.

    Args:
        sections: List of BookmarkSection objects
        prefix: Prefix for nested sections

    Returns:
        List of (display_name, section) tuples
    """
    result: list[tuple[str, BookmarkSection]] = []
    for section in sections:
        display_name = f"{prefix}{section.title}" if prefix else section.title
        if section.total_urls > 0:
            count_str = f" ({section.total_urls} URLs)"
            result.append((f"{display_name}{count_str}", section))
        for child in section.children:
            child_results = flatten_sections([child], prefix=f"{display_name} > ")
            result.extend(child_results)
    return result
