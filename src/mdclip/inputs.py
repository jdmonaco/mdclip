"""Input parsing for mdclip - URLs, bookmarks HTML, and URL files."""

import html
import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path


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
    Uses regex for fast parsing of large files.

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

    # Fast regex extraction of URLs from HREF attributes
    href_pattern = re.compile(r'<A\s+HREF="(https?://[^"]+)"', re.IGNORECASE)

    urls: list[str] = []
    for match in href_pattern.finditer(content):
        url = match.group(1)
        if is_valid_url(url):
            urls.append(url)

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

    Uses a fast single-pass regex approach to handle large bookmark files
    efficiently. Tracks nesting depth by counting <DL> and </DL> tags.

    Args:
        path: Path to bookmarks HTML file

    Returns:
        List of top-level BookmarkSection objects
    """
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="latin-1")

    # Single-pass regex parsing - much faster than BeautifulSoup for large files
    # Pattern matches: <DL>, </DL>, <DT><H3>title</H3>, <DT><A HREF="url">
    token_pattern = re.compile(
        r"<DL>|</DL>|<DT><H3[^>]*>([^<]+)</H3>|<DT><A\s+HREF=\"(https?://[^\"]+)\"",
        re.IGNORECASE,
    )

    root_sections: list[BookmarkSection] = []
    section_stack: list[BookmarkSection] = []
    depth = 0

    for match in token_pattern.finditer(content):
        token = match.group(0).upper()

        if token == "<DL>":
            depth += 1
        elif token == "</DL>":
            depth -= 1
            # Pop sections that are now closed
            while section_stack and section_stack[-1].depth >= depth:
                section_stack.pop()
        elif match.group(1):
            # H3 folder title - decode HTML entities like &amp; -> &
            title = html.unescape(match.group(1).strip())
            section = BookmarkSection(title=title, depth=depth)

            if section_stack:
                section_stack[-1].children.append(section)
            else:
                root_sections.append(section)

            section_stack.append(section)
        elif match.group(2):
            # URL
            url = match.group(2)
            if section_stack and is_valid_url(url):
                section_stack[-1].urls.append(url)

    return root_sections


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


def flatten_sections(
    sections: list[BookmarkSection],
    _depth: int = 0,
    _is_last_stack: list[bool] | None = None,
) -> list[tuple[str, BookmarkSection]]:
    """Flatten hierarchical sections into a list with tree-style display names.

    Uses box-drawing characters to show hierarchy:
    ├── for items with siblings below
    └── for last item in a group
    │   for continuation lines

    For sections with both direct URLs and subfolders, adds a "." entry
    to allow selecting only the direct URLs without subfolder contents.

    Args:
        sections: List of BookmarkSection objects
        _depth: Current depth (internal use)
        _is_last_stack: Track which ancestors are last in their group (internal use)

    Returns:
        List of (display_name, section) tuples
    """
    if _is_last_stack is None:
        _is_last_stack = []

    result: list[tuple[str, BookmarkSection]] = []

    for i, section in enumerate(sections):
        is_last = i == len(sections) - 1

        # Build the display prefix with box-drawing characters
        if _depth == 0:
            # Root level - no tree prefix
            display_prefix = ""
        else:
            # Build prefix from ancestor continuation lines
            # Skip first element (root level has no visual representation)
            display_prefix = ""
            for ancestor_is_last in _is_last_stack[1:]:
                display_prefix += "    " if ancestor_is_last else "│   "
            # Add branch for this item
            display_prefix += "└── " if is_last else "├── "

        count_str = f" ({section.total_urls})" if section.total_urls > 0 else ""
        display_name = f"{display_prefix}{section.title}{count_str}"

        if section.total_urls > 0:
            result.append((display_name, section))

        # If section has both direct URLs and children, add a "<bookmarks>" entry
        # to allow selecting only the direct URLs
        if section.urls and section.children:
            # Create synthetic section with only direct URLs
            direct_only = BookmarkSection(
                title="<bookmarks>",
                depth=section.depth + 1,
                urls=list(section.urls),
                children=[],
            )
            # Build prefix for the "<bookmarks>" entry (it's the first child)
            child_prefix = ""
            for ancestor_is_last in _is_last_stack[1:]:
                child_prefix += "    " if ancestor_is_last else "│   "
            if _depth > 0:
                child_prefix += "    " if is_last else "│   "
            child_prefix += "├── "  # Never last since children follow
            direct_display = f"{child_prefix}<bookmarks> ({len(section.urls)})"
            result.append((direct_display, direct_only))

        # Recurse into children
        if section.children:
            child_results = flatten_sections(
                section.children,
                _depth=_depth + 1,
                _is_last_stack=_is_last_stack + [is_last],
            )
            result.extend(child_results)

    return result
