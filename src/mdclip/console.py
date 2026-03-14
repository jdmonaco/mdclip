"""Rich console output for mdclip."""

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Console instance writing to stderr (stdout reserved for data)
console = Console(stderr=True)

# When True, suppress all Rich output (for --json mode)
_quiet = False


def set_quiet(quiet: bool) -> None:
    """Enable or disable quiet mode (suppresses Rich output for JSON mode)."""
    global _quiet
    _quiet = quiet


def info(msg: str) -> None:
    """Print an informational message."""
    if not _quiet:
        console.print(f"[blue]\u2139[/blue] {msg}")


def success(msg: str) -> None:
    """Print a success message."""
    if not _quiet:
        console.print(f"[green]\u2713[/green] {msg}")


def warning(msg: str) -> None:
    """Print a warning message."""
    if not _quiet:
        console.print(f"[yellow]\u26a0[/yellow] {msg}")


def error(msg: str) -> None:
    """Print an error message."""
    if not _quiet:
        console.print(f"[red]\u2717[/red] {msg}")


def create_spinner(description: str = "Processing...") -> Progress:
    """Create a spinner progress indicator.

    Usage:
        with create_spinner("Extracting...") as progress:
            task = progress.add_task(description, total=None)
            # ... do work ...
    """
    return Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
        disable=_quiet,
    )


def confirm(prompt: str, default: bool = False) -> bool:
    """Prompt user for yes/no confirmation.

    Args:
        prompt: The question to ask
        default: Default value if user just presses Enter

    Returns:
        True if user confirms, False otherwise
    """
    if _quiet:
        return default
    suffix = "(Y/n)" if default else "(y/N)"
    try:
        response = console.input(f"{prompt} {suffix}: ").strip().lower()
        if not response:
            return default
        return response in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        console.print()
        return False
