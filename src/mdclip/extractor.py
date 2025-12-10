"""Content extraction using defuddle (Node.js)."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse


# Pattern to fix dropcap letters separated from their word
# Matches: single capital letter, blank line, then lowercase continuation
# Example: "K\n\nwan's team" -> "Kwan's team"
DROPCAP_PATTERN = re.compile(r"^([A-Z])\n\n([a-z])", re.MULTILINE)

# Pattern to fix markdown links broken across multiple lines
# Matches: [\n\n## Title\n\n](url) -> [Title](url)
# Handles both escaped (\[) and unescaped ([) brackets
# The link text may have optional heading markers (##)
BROKEN_LINK_PATTERN = re.compile(
    r"\\?\[\s*\n+(?:#{1,6}\s+)?([^\n]+?)\s*\n+\\?\]\(([^)]+)\)"
)

# Pattern for complex broken links containing images or multi-paragraph content
# These are links wrapping complex content like images, captions, credits
# Example: \[\nImage\n![alt](url)\nCaption\n\](link) -> Image\n![alt](url)\nCaption
# We keep the inner content and discard the outer link wrapper
COMPLEX_BROKEN_LINK_PATTERN = re.compile(
    r"\\?\[\s*\n+([\s\S]*?!\[[^\]]*\]\([^)]+\)[\s\S]*?)\n*\\?\]\([^)]+\)"
)

# Pattern to match markdown links and images: [text](url) or ![alt](url)
MARKDOWN_LINK_PATTERN = re.compile(r"(!?)\[([^\]]*)\]\(([^)]+)\)")


class DefuddleError(Exception):
    """Error during content extraction with defuddle."""

    pass


class DefuddleNotInstalledError(DefuddleError):
    """defuddle Node.js dependencies are not installed."""

    pass


class NodeNotInstalledError(DefuddleError):
    """Node.js is not installed."""

    pass


def check_node_installed() -> bool:
    """Check if Node.js is installed and accessible."""
    return shutil.which("node") is not None


def check_defuddle_installed() -> bool:
    """Check if defuddle Node.js dependencies are installed.

    Returns True if node_modules/defuddle exists in the package root.
    """
    package_root = Path(__file__).parent.parent.parent
    node_modules = package_root / "node_modules" / "defuddle"
    return node_modules.is_dir()


def get_script_path() -> Path:
    """Get the path to the defuddle extraction script."""
    package_root = Path(__file__).parent.parent.parent
    return package_root / "scripts" / "defuddle-extract.js"


def cleanup_content(content: str, source_url: str | None = None) -> str:
    """Clean up extracted markdown content.

    Fixes common extraction artifacts like:
    - Dropcap letters separated from their word (e.g., "K\\n\\nwan's" -> "Kwan's")
    - Complex broken links wrapping images/captions (unwrap, keep content)
    - Simple broken links across multiple lines (e.g., "\\[\\n## Title\\n\\](url)")
    - Relative URLs converted to absolute URLs based on source

    Args:
        content: Raw markdown content from defuddle
        source_url: The source URL for resolving relative links

    Returns:
        Cleaned markdown content
    """
    if not content:
        return content

    # Fix dropcap letters separated by blank line from rest of word
    content = DROPCAP_PATTERN.sub(r"\1\2", content)

    # Fix complex broken links (containing images) - unwrap and keep inner content
    # Must run before simple broken link fix
    content = COMPLEX_BROKEN_LINK_PATTERN.sub(r"\1", content)

    # Fix simple markdown links broken across multiple lines
    content = BROKEN_LINK_PATTERN.sub(r"[\1](\2)", content)

    # Convert relative URLs to absolute URLs
    if source_url:
        content = _resolve_relative_links(content, source_url)

    return content


def _resolve_relative_links(content: str, source_url: str) -> str:
    """Convert relative URLs in markdown links to absolute URLs.

    Args:
        content: Markdown content with links
        source_url: Base URL for resolving relative paths

    Returns:
        Content with relative URLs converted to absolute
    """

    def replace_link(match: re.Match[str]) -> str:
        prefix = match.group(1)  # "!" for images, "" for links
        text = match.group(2)
        url = match.group(3)

        # Skip if already absolute (http, https, mailto, etc.)
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", url):
            return match.group(0)

        # Skip anchor-only links
        if url.startswith("#"):
            return match.group(0)

        # Resolve relative URL against source (handles //, /, and relative paths)
        absolute_url = urljoin(source_url, url)
        return f"{prefix}[{text}]({absolute_url})"

    return MARKDOWN_LINK_PATTERN.sub(replace_link, content)


def extract_page(
    url: str, timeout: int = 60, cookies: str | None = None
) -> dict[str, Any]:
    """Extract content and metadata from a URL using defuddle.

    Args:
        url: The URL to extract content from
        timeout: Timeout in seconds
        cookies: Optional Cookie header value for authenticated requests

    Returns:
        Dict with keys: title, author, description, published, content,
        site, domain, wordCount

    Raises:
        NodeNotInstalledError: If Node.js is not installed
        DefuddleNotInstalledError: If defuddle dependencies not installed
        DefuddleError: On extraction failure
    """
    if not check_node_installed():
        raise NodeNotInstalledError(
            "Node.js is not installed. "
            "Install from: https://nodejs.org/"
        )

    if not check_defuddle_installed():
        raise DefuddleNotInstalledError(
            "defuddle is not installed. "
            "Run 'npm install' in the mdclip directory."
        )

    script_path = get_script_path()
    if not script_path.exists():
        raise DefuddleError(f"Extraction script not found: {script_path}")

    try:
        # Set up environment, passing cookies if provided
        env = os.environ.copy()
        if cookies:
            env["MDCLIP_COOKIES"] = cookies

        result = subprocess.run(
            ["node", str(script_path), url],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )

        if result.returncode != 0:
            # Try to parse error JSON from stderr
            try:
                error_data = json.loads(result.stderr)
                raise DefuddleError(error_data.get("message", "Unknown error"))
            except json.JSONDecodeError:
                raise DefuddleError(result.stderr or "Unknown error")

        # Parse the JSON output
        # defuddle may output debug messages before JSON, so find the JSON line
        stdout = result.stdout.strip()
        json_str = None
        for line in stdout.split("\n"):
            line = line.strip()
            if line.startswith("{"):
                json_str = line
                break

        if not json_str:
            raise DefuddleError(f"No JSON found in output: {stdout[:200]}")

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise DefuddleError(f"Failed to parse output: {e}") from e

        # Ensure we have fallbacks for essential fields
        if not data.get("title"):
            parsed = urlparse(url)
            data["title"] = parsed.netloc or "Untitled"

        # Clean up content artifacts
        if data.get("content"):
            data["content"] = cleanup_content(data["content"], source_url=url)

        return data

    except subprocess.TimeoutExpired:
        raise DefuddleError(f"Timeout extracting content from {url}") from None
    except subprocess.SubprocessError as e:
        raise DefuddleError(f"Failed to run extraction: {e}") from e
