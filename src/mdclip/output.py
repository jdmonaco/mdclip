"""File output handling for mdclip."""

import shutil
import subprocess
import tempfile
from pathlib import Path


def resolve_output_path(folder: str, vault: Path) -> Path:
    """Resolve output folder path relative to vault.

    Args:
        folder: Folder path (relative to vault or absolute)
        vault: Base vault path

    Returns:
        Resolved Path object (directory will be created if needed)
    """
    folder_path = Path(folder).expanduser()

    if folder_path.is_absolute():
        output_path = folder_path
    else:
        output_path = vault / folder_path

    # Create directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    return output_path


def get_unique_filepath(base_path: Path) -> Path:
    """Get a unique filepath, appending numbers if file exists.

    Args:
        base_path: The desired file path

    Returns:
        A unique path (may have (1), (2), etc. appended to stem)
    """
    if not base_path.exists():
        return base_path

    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent

    counter = 1
    while True:
        new_path = parent / f"{stem} ({counter}){suffix}"
        if not new_path.exists():
            return new_path
        counter += 1


def write_note(path: Path, content: str) -> None:
    """Write content to file atomically.

    Uses a temporary file and rename to ensure atomic write.

    Args:
        path: Output file path
        content: Content to write
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file in same directory, then rename
    # This ensures atomic write on most filesystems
    fd, temp_path = tempfile.mkstemp(
        suffix=".md.tmp",
        prefix=".mdclip_",
        dir=path.parent,
    )
    temp_file = Path(temp_path)

    try:
        with open(fd, "w", encoding="utf-8") as f:
            f.write(content)
        temp_file.rename(path)
    except Exception:
        # Clean up temp file on error
        if temp_file.exists():
            temp_file.unlink()
        raise


def check_mdformat_installed() -> bool:
    """Check if mdformat is available."""
    return shutil.which("mdformat") is not None


def format_markdown(path: Path) -> bool:
    """Format markdown file using mdformat.

    Args:
        path: Path to markdown file to format

    Returns:
        True if formatting succeeded, False otherwise.
    """
    if not check_mdformat_installed():
        return False

    try:
        result = subprocess.run(
            ["mdformat", str(path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False
