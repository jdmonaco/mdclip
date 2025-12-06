"""Command-line interface for mdclip."""

import argparse
import sys
import traceback
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from . import __version__
from .config import (
    config_exists,
    get_template_by_name,
    init_config,
    load_config,
    merge_config,
)
from .extractor import (
    DefuddleError,
    DefuddleNotInstalledError,
    NodeNotInstalledError,
    check_defuddle_installed,
    check_node_installed,
    extract_page,
)
from .frontmatter import build_frontmatter
from .inputs import parse_input
from .output import format_markdown, get_unique_filepath, resolve_output_path, write_note
from .templates import Template, match_template, render_filename, sanitize_filename, slugify


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="mdclip",
        description="Clip web pages to Markdown with YAML frontmatter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  mdclip --init-config
  mdclip --dry-run bookmarks.html
  mdclip "https://github.com/kepano/defuddle"
  mdclip -o "Projects/Research" "https://example.com/article"
""",
    )

    parser.add_argument(
        "input",
        nargs="*",
        metavar="INPUT",
        help="URL(s), path to bookmarks HTML, or text file with URLs",
    )

    parser.add_argument(
        "-o", "--output",
        metavar="PATH",
        help="Override output folder (relative to vault or absolute)",
    )

    parser.add_argument(
        "-v", "--vault",
        metavar="PATH",
        help="Override vault path",
    )

    parser.add_argument(
        "-t", "--template",
        metavar="NAME",
        help="Force specific template (bypass pattern matching)",
    )

    parser.add_argument(
        "--tags",
        nargs="+",
        metavar="TAG",
        help="Additional tags to append",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without writing files",
    )

    parser.add_argument(
        "--config",
        metavar="PATH",
        help="Use alternate config file",
    )

    parser.add_argument(
        "--init-config",
        action="store_true",
        help="Initialize default config file and exit",
    )

    parser.add_argument(
        "--list-templates",
        action="store_true",
        help="List configured templates and exit",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output",
    )

    parser.add_argument(
        "--no-format",
        action="store_true",
        help="Skip mdformat post-processing",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return parser.parse_args(args)


def list_templates(config: dict) -> None:
    """Print configured templates."""
    templates = config.get("templates", [])
    if not templates:
        print("No templates configured.")
        return

    print("Configured templates:\n")
    for t in templates:
        name = t.get("name", "unnamed")
        folder = t.get("folder", "Inbox/Clips")
        triggers = t.get("triggers", [])
        tags = t.get("tags", [])

        print(f"  {name}")
        print(f"    Folder: {folder}")
        if triggers:
            print(f"    Triggers: {', '.join(triggers[:3])}", end="")
            if len(triggers) > 3:
                print(f" (+{len(triggers) - 3} more)")
            else:
                print()
        if tags:
            print(f"    Tags: {', '.join(tags)}")
        print()


def process_url(
    url: str,
    config: dict,
    args: argparse.Namespace,
) -> Path | None:
    """Process a single URL and create a note.

    Args:
        url: The URL to process
        config: Configuration dictionary
        args: Parsed CLI arguments

    Returns:
        Path to created file, or None if dry-run
    """
    if args.verbose:
        print(f"Processing: {url}")

    # Match template
    if args.template:
        template_dict = get_template_by_name(args.template, config)
        if template_dict is None:
            print(f"  Warning: Template '{args.template}' not found, using default", file=sys.stderr)
            template = match_template(url, config.get("templates", []))
        else:
            template = Template.from_dict(template_dict)
    else:
        template = match_template(url, config.get("templates", []))

    if args.verbose or args.dry_run:
        print(f"  Template: {template.name}")
        print(f"  Folder: {template.folder}")

    if args.dry_run:
        return None

    # Extract content and metadata
    page_data = extract_page(url)
    title = page_data.get("title", "Untitled")
    content = page_data.get("content", "")

    if args.verbose:
        print(f"  Title: {title}")

    if not content:
        print(f"  Warning: No content extracted from {url}", file=sys.stderr)

    # Build metadata from extracted data
    metadata = {
        "title": title,
        "url": url,
        "author": page_data.get("author"),
        "description": page_data.get("description"),
        "published": page_data.get("published"),
        "site": page_data.get("site"),
        "domain": page_data.get("domain"),
    }

    # Generate frontmatter
    frontmatter = build_frontmatter(
        metadata,
        template,
        config,
        extra_tags=args.tags,
    )

    # Assemble full note with title heading
    full_content = frontmatter + f"# {title}\n\n" + content

    # Determine output path
    folder = args.output or template.folder
    vault = Path(config["vault"]).expanduser()
    output_folder = resolve_output_path(folder, vault)

    # Generate filename
    filename_template = template.filename or "{{title}}"
    filename_vars = {
        "title": title,
        "date": datetime.now().strftime(config.get("filename_date_format", "%Y-%m-%d")),
        "slug": slugify(title),
        "domain": urlparse(url).netloc,
    }
    filename = render_filename(filename_template, filename_vars)
    filename = sanitize_filename(filename) + ".md"

    # Write file
    filepath = get_unique_filepath(output_folder / filename)
    write_note(filepath, full_content)

    # Format if enabled
    if config.get("auto_format") and not args.no_format:
        if format_markdown(filepath):
            if args.verbose:
                print("  Formatted with mdformat")

    # Print relative path if within vault
    try:
        rel_path = filepath.relative_to(vault)
        print(f"  Saved: {rel_path}")
    except ValueError:
        print(f"  Saved: {filepath}")

    return filepath


def main(args: list[str] | None = None) -> int:
    """Main entry point.

    Args:
        args: Command-line arguments (for testing)

    Returns:
        Exit code (0 for success)
    """
    parsed_args = parse_args(args)

    # Handle --init-config
    if parsed_args.init_config:
        if config_exists():
            print(f"Config file already exists: {Path.home() / '.mdclip.yml'}", file=sys.stderr)
            return 1
        try:
            path = init_config()
            print(f"Created config file: {path}")
            return 0
        except Exception as e:
            print(f"Error creating config: {e}", file=sys.stderr)
            return 1

    # Load configuration
    config_path = Path(parsed_args.config) if parsed_args.config else None
    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        return 1

    # Apply CLI overrides
    overrides = {}
    if parsed_args.vault:
        overrides["vault"] = parsed_args.vault
    if overrides:
        config = merge_config(config, overrides)

    # Handle --list-templates
    if parsed_args.list_templates:
        list_templates(config)
        return 0

    # Check for inputs
    if not parsed_args.input:
        print("Error: No input provided. Use -h for help.", file=sys.stderr)
        return 1

    # Check Node.js and defuddle are installed
    if not check_node_installed():
        print(
            "Error: Node.js is not installed.\n"
            "Install from: https://nodejs.org/",
            file=sys.stderr,
        )
        return 1

    if not check_defuddle_installed():
        print(
            "Error: defuddle is not installed.\n"
            "Run 'npm install' in the mdclip directory.",
            file=sys.stderr,
        )
        return 1

    # Parse inputs to URLs
    urls: list[str] = []
    for input_item in parsed_args.input:
        parsed_urls = parse_input(input_item)
        if not parsed_urls and parsed_args.verbose:
            print(f"  Warning: No URLs found in '{input_item}'", file=sys.stderr)
        urls.extend(parsed_urls)

    if not urls:
        print("No valid URLs found in input", file=sys.stderr)
        return 1

    if parsed_args.verbose:
        print(f"Found {len(urls)} URL(s) to process\n")

    # Process each URL
    success_count = 0
    for url in urls:
        try:
            result = process_url(url, config, parsed_args)
            if result or parsed_args.dry_run:
                success_count += 1
        except (NodeNotInstalledError, DefuddleNotInstalledError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except DefuddleError as e:
            print(f"Error processing {url}: {e}", file=sys.stderr)
            if parsed_args.verbose:
                traceback.print_exc()
        except Exception as e:
            print(f"Error processing {url}: {e}", file=sys.stderr)
            if parsed_args.verbose:
                traceback.print_exc()

    # Summary
    if len(urls) > 1:
        print(f"\nProcessed {success_count}/{len(urls)} URLs successfully")

    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
