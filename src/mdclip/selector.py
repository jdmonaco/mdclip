"""Interactive selection for mdclip using gum CLI or fallback input."""

import shutil
import subprocess

from .console import console


def check_gum_available() -> bool:
    """Check if gum CLI is installed.

    Returns:
        True if gum is available in PATH
    """
    return shutil.which("gum") is not None


def select_with_gum(options: list[str], prompt: str = "Select:") -> str | None:
    """Use gum choose for interactive selection.

    Args:
        options: List of options to choose from
        prompt: Header prompt to display

    Returns:
        Selected option string, or None if cancelled/failed
    """
    try:
        result = subprocess.run(
            ["gum", "choose", "--header", prompt] + options,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except subprocess.SubprocessError:
        pass
    return None


def select_with_input(options: list[str], prompt: str = "Select:") -> str | None:
    """Fallback numbered input selection.

    Args:
        options: List of options to choose from
        prompt: Header prompt to display

    Returns:
        Selected option string, or None if user chooses "all" or cancels
    """
    console.print(f"\n[bold]{prompt}[/bold]")
    for i, opt in enumerate(options, 1):
        console.print(f"  [cyan]{i}[/cyan]) {opt}")
    console.print("  [cyan]0[/cyan]) Process all URLs")

    try:
        choice = console.input("\nEnter number: ").strip()
        if choice == "0":
            return None  # Process all
        idx = int(choice) - 1
        if 0 <= idx < len(options):
            return options[idx]
    except (ValueError, EOFError, KeyboardInterrupt):
        console.print()
    return None


def select_section(options: list[str], prompt: str = "Select a section:") -> str | None:
    """Select a section using gum or fallback input.

    Args:
        options: List of section names to choose from
        prompt: Header prompt to display

    Returns:
        Selected section name, or None to process all
    """
    if check_gum_available():
        # Add "All sections" option for gum
        gum_options = ["[All sections]"] + options
        result = select_with_gum(gum_options, prompt)
        if result == "[All sections]":
            return None
        return result
    return select_with_input(options, prompt)
