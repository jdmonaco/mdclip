"""Shell completion script generation and installation."""

import sys
from importlib.resources import files
from pathlib import Path


def get_completion_path() -> Path:
    """Return the user-level bash completion installation path."""
    return Path.home() / ".local/share/bash-completion/completions/mdclip"


def get_bash_completion_script() -> str:
    """Return the bash completion script content."""
    return files("mdclip.data").joinpath("completion.bash").read_text()


def completion_command(args: list[str]) -> int:
    """Handle the completion subcommand.

    Usage:
        mdclip completion bash [--install | --path]
    """
    if not args or args[0] != "bash":
        print("Usage: mdclip completion bash [--install | --path]", file=sys.stderr)
        print("Supported shells: bash", file=sys.stderr)
        return 1

    flags = args[1:] if len(args) > 1 else []

    if "--path" in flags:
        print(get_completion_path())
        return 0

    script = get_bash_completion_script()

    if "--install" in flags:
        path = get_completion_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(script)
        print(f"Installed: {path}", file=sys.stderr)
        print("Restart your shell or run: source ~/.bashrc", file=sys.stderr)
        return 0

    # Default: print to stdout
    print(script)
    return 0
