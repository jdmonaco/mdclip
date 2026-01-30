"""File output handling for mdclip."""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import NamedTuple
from urllib.parse import quote

# Pattern to extract source URL from YAML frontmatter
FRONTMATTER_SOURCE_PATTERN = re.compile(
    r"^---\s*\n.*?^source:\s*['\"]?(https?://[^\s'\"]+)['\"]?\s*$.*?^---\s*$",
    re.MULTILINE | re.DOTALL,
)


class FileExistsResult(NamedTuple):
    """Result of checking if a file exists and matches the source URL."""

    exists: bool
    same_source: bool
    path: Path


def extract_source_url(filepath: Path) -> str | None:
    """Extract the source URL from an existing markdown file's frontmatter.

    Args:
        filepath: Path to the markdown file

    Returns:
        The source URL if found, None otherwise
    """
    try:
        content = filepath.read_text(encoding="utf-8")
        match = FRONTMATTER_SOURCE_PATTERN.search(content)
        if match:
            return match.group(1)
    except (OSError, UnicodeDecodeError):
        pass
    return None


def check_existing_file(base_path: Path, source_url: str) -> FileExistsResult:
    """Check if a file exists and whether it has the same source URL.

    Args:
        base_path: The desired file path
        source_url: The URL being processed

    Returns:
        FileExistsResult with exists, same_source, and path
    """
    if not base_path.exists():
        return FileExistsResult(exists=False, same_source=False, path=base_path)

    existing_source = extract_source_url(base_path)
    same_source = existing_source == source_url

    return FileExistsResult(exists=True, same_source=same_source, path=base_path)


def resolve_output_path(folder: str) -> Path:
    """Resolve explicit -o output folder relative to cwd.

    - Absolute paths: used as-is
    - Tilde paths: expanded
    - Relative paths: resolved from cwd

    Args:
        folder: Folder path (relative to cwd or absolute)

    Returns:
        Resolved Path object (directory will be created if needed)
    """
    folder_path = Path(folder).expanduser()
    output_path = folder_path.resolve()

    # Create directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    return output_path


def resolve_template_folder(folder: str, vault: Path) -> Path:
    """Resolve template folder path relative to vault (auto-routing).

    Args:
        folder: Folder path from template config (relative to vault or absolute)
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


def get_vault_name(vault_path: Path) -> str:
    """Extract vault name from vault path (last component)."""
    return vault_path.resolve().name


def open_note(filepath: Path, vault_path: Path) -> bool:
    """Open a note file - in Obsidian if inside vault, otherwise in pager.

    Args:
        filepath: Absolute path to the markdown file
        vault_path: Path to the Obsidian vault

    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if file is inside vault
        rel_path = filepath.relative_to(vault_path)
        return _open_in_obsidian(rel_path, vault_path)
    except ValueError:
        # File is outside vault - open in pager
        return _open_in_pager(filepath)


def _open_in_obsidian(rel_path: Path, vault_path: Path) -> bool:
    """Open file in Obsidian using obsidian:// URL scheme."""
    try:
        # Obsidian expects path without .md extension
        note_path = rel_path.with_suffix("") if rel_path.suffix == ".md" else rel_path
        encoded_path = quote(str(note_path), safe="/")
        vault_name = get_vault_name(vault_path)
        obsidian_url = f"obsidian://open?vault={quote(vault_name)}&file={encoded_path}"
        subprocess.run(["open", obsidian_url], check=True)
        # Bring Obsidian to foreground via System Events
        subprocess.run(
            [
                "osascript", "-e",
                'tell application "System Events" to set frontmost of process "Obsidian" to true',
            ],
            check=False,
        )
        return True
    except subprocess.SubprocessError:
        return False


def _open_in_pager(filepath: Path) -> bool:
    """Open file in glow (if available) or less."""
    try:
        if shutil.which("glow"):
            subprocess.run(["glow", "-p", str(filepath)], check=True)
        else:
            subprocess.run(["less", str(filepath)], check=True)
        return True
    except subprocess.SubprocessError:
        return False
