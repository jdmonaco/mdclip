"""Content extraction using defuddle (Node.js)."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


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


def extract_page(url: str, timeout: int = 60) -> dict[str, Any]:
    """Extract content and metadata from a URL using defuddle.

    Args:
        url: The URL to extract content from
        timeout: Timeout in seconds

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
        result = subprocess.run(
            ["node", str(script_path), url],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            # Try to parse error JSON from stderr
            try:
                error_data = json.loads(result.stderr)
                raise DefuddleError(error_data.get("message", "Unknown error"))
            except json.JSONDecodeError:
                raise DefuddleError(result.stderr or "Unknown error")

        # Parse the JSON output
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise DefuddleError(f"Failed to parse output: {e}") from e

        # Ensure we have fallbacks for essential fields
        if not data.get("title"):
            parsed = urlparse(url)
            data["title"] = parsed.netloc or "Untitled"

        return data

    except subprocess.TimeoutExpired:
        raise DefuddleError(f"Timeout extracting content from {url}") from None
    except subprocess.SubprocessError as e:
        raise DefuddleError(f"Failed to run extraction: {e}") from e
