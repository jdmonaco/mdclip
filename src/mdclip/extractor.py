"""Content extraction using gather-cli."""

import shutil
import subprocess
from typing import Any
from urllib.parse import urlparse

from .templates import Template


class GatherError(Exception):
    """Error during content extraction with gather-cli."""

    pass


class GatherNotInstalledError(GatherError):
    """gather-cli is not installed."""

    pass


def check_gather_installed() -> bool:
    """Check if gather-cli is installed and accessible."""
    return shutil.which("gather") is not None


def get_gather_version() -> str | None:
    """Get the installed gather-cli version."""
    if not check_gather_installed():
        return None
    try:
        result = subprocess.run(
            ["gather", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() or result.stderr.strip()
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return None


def extract_title(url: str, timeout: int = 30) -> str:
    """Extract the page title from a URL.

    Args:
        url: The URL to extract title from
        timeout: Timeout in seconds

    Returns:
        Page title, or domain name as fallback
    """
    if not check_gather_installed():
        raise GatherNotInstalledError(
            "gather-cli is not installed. "
            "Install with: brew tap ttscoff/thelab && brew install gather-cli"
        )

    try:
        result = subprocess.run(
            ["gather", "--title-only", url],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        title = result.stdout.strip()
        if title:
            return title
    except subprocess.TimeoutExpired:
        pass
    except subprocess.SubprocessError as e:
        raise GatherError(f"Failed to extract title: {e}") from e

    # Fallback to domain name
    parsed = urlparse(url)
    return parsed.netloc or "Untitled"


def extract_content(
    url: str,
    options: list[str] | None = None,
    timeout: int = 60,
) -> str:
    """Extract markdown content from a URL.

    Args:
        url: The URL to extract content from
        options: Additional gather-cli options
        timeout: Timeout in seconds

    Returns:
        Markdown content
    """
    if not check_gather_installed():
        raise GatherNotInstalledError(
            "gather-cli is not installed. "
            "Install with: brew tap ttscoff/thelab && brew install gather-cli"
        )

    cmd = ["gather", "--no-include-source"]
    if options:
        cmd.extend(options)
    cmd.append(url)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise GatherError(f"Timeout extracting content from {url}") from None
    except subprocess.SubprocessError as e:
        raise GatherError(f"Failed to extract content: {e}") from e


def build_gather_options(template: Template, config: dict[str, Any]) -> list[str]:
    """Build gather-cli options from template and config.

    Args:
        template: The matched template
        config: Global configuration

    Returns:
        List of command-line options for gather
    """
    options: list[str] = []

    # Link formatting
    if config.get("inline_links", True):
        options.append("--inline-links")
    else:
        options.append("--no-inline-links")

    if config.get("paragraph_links", False):
        options.append("--paragraph-links")
    else:
        options.append("--no-paragraph-links")

    # Template-specific options
    if template.gather_opts:
        options.extend(template.gather_opts)

    return options
