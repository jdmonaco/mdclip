"""Command-line interface for mdclip."""

import argparse
import sys
import traceback
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from . import __version__
from .config import (
    get_config_path,
    get_template_by_name,
    load_config,
    merge_config,
)
from .console import confirm, console, create_spinner, error, info, success, warning
from .extractor import (
    DefuddleError,
    DefuddleNotInstalledError,
    NodeNotInstalledError,
    check_defuddle_installed,
    check_node_installed,
    extract_page,
)
from .frontmatter import build_frontmatter
from .inputs import (
    InputType,
    detect_input_type,
    flatten_sections,
    get_urls_from_section,
    parse_bookmark_structure,
    parse_input,
    read_clipboard_urls,
)
from .output import (
    check_existing_file,
    format_markdown,
    get_unique_filepath,
    open_note,
    resolve_output_path,
    write_note,
)
from .selector import select_section
from .templates import Template, match_template, render_filename, sanitize_filename, slugify

# Confirmation threshold for batch processing
URL_CONFIRM_THRESHOLD = 10


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="mdclip",
        description="Clip web pages to Markdown with YAML frontmatter.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  mdclip "https://example.com/article"
  mdclip -o "Reference/Papers" "https://arxiv.org/abs/..."
  mdclip --dry-run bookmarks.html
  mdclip --skip-existing urls.txt
""",
    )

    # Input
    parser.add_argument(
        "input",
        nargs="*",
        metavar="INPUT",
        help="URL, bookmarks HTML file, or text file with URLs (reads clipboard if omitted)",
    )

    # Output control
    parser.add_argument(
        "-o", "--output",
        metavar="FOLDER",
        help="Output folder (relative to vault or absolute path)",
    )

    parser.add_argument(
        "-t", "--template",
        metavar="NAME",
        help="Use named template (bypasses URL pattern matching)",
    )

    parser.add_argument(
        "--tags",
        nargs="+",
        metavar="TAG",
        help="Additional tags to include in frontmatter",
    )

    # Behavior
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip URLs that already have a clipped file",
    )

    parser.add_argument(
        "-n", "--dry-run",
        action="store_true",
        help="Show what would be done without writing files",
    )

    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip confirmation prompts",
    )

    parser.add_argument(
        "--all-sections",
        action="store_true",
        help="Process all bookmark sections without prompting",
    )

    parser.add_argument(
        "--no-format",
        action="store_true",
        help="Skip mdformat post-processing",
    )

    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Don't open note after clipping",
    )

    # Configuration
    parser.add_argument(
        "--vault",
        metavar="PATH",
        help="Override vault path from config",
    )

    parser.add_argument(
        "--config",
        metavar="FILE",
        help="Use alternate config file",
    )

    parser.add_argument(
        "--list-templates",
        action="store_true",
        help="List configured templates and exit",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output",
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
        console.print("No templates configured.")
        return

    console.print("[bold]Configured templates:[/bold]\n")
    for t in templates:
        name = t.get("name", "unnamed")
        folder = t.get("folder", "Inbox/Clips")
        triggers = t.get("triggers", [])
        tags = t.get("tags", [])

        console.print(f"  [cyan]{name}[/cyan]")
        console.print(f"    Folder: {folder}")
        if triggers:
            trigger_str = ", ".join(triggers[:3])
            if len(triggers) > 3:
                trigger_str += f" (+{len(triggers) - 3} more)"
            console.print(f"    Triggers: {trigger_str}")
        if tags:
            console.print(f"    Tags: {', '.join(tags)}")
        console.print()


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
    # Match template
    if args.template:
        template_dict = get_template_by_name(args.template, config)
        if template_dict is None:
            warning(f"Template '{args.template}' not found, using default")
            template = match_template(url, config.get("templates", []))
        else:
            template = Template.from_dict(template_dict)
    else:
        template = match_template(url, config.get("templates", []))

    if args.verbose or args.dry_run:
        info(f"Template: {template.name}")
        info(f"Folder: {template.folder}")

    if args.dry_run:
        info(f"[dry-run] Would process: {url}")
        return None

    # Extract content and metadata with spinner
    with create_spinner() as progress:
        progress.add_task(f"Extracting: {url}", total=None)
        page_data = extract_page(url)

    title = page_data.get("title", "Untitled")
    content = page_data.get("content", "")

    if args.verbose:
        info(f"Title: {title}")

    if not content:
        warning(f"No content extracted from {url}")

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
    base_path = output_folder / filename

    # Check for existing file
    skip_existing = args.skip_existing or config.get("skip_existing", False)
    existing = check_existing_file(base_path, url)

    if existing.exists:
        if existing.same_source:
            if skip_existing:
                # Skip this URL - file already exists with same source
                info(f"Skipped (exists): {filename}")
                return None
            # Same source but not skipping - use unique filename
            filepath = get_unique_filepath(base_path)
        else:
            # Different source URL - always use unique filename
            filepath = get_unique_filepath(base_path)
    else:
        filepath = base_path

    # Write file
    write_note(filepath, full_content)

    # Format if enabled
    if config.get("auto_format") and not args.no_format:
        if format_markdown(filepath):
            if args.verbose:
                info("Formatted with mdformat")

    # Print relative path if within vault
    try:
        rel_path = filepath.relative_to(vault)
        success(f"Saved: {rel_path}")
    except ValueError:
        success(f"Saved: {filepath}")

    return filepath


def main(args: list[str] | None = None) -> int:
    """Main entry point.

    Args:
        args: Command-line arguments (for testing)

    Returns:
        Exit code (0 for success)
    """
    parsed_args = parse_args(args)

    # Load configuration (auto-creates if missing)
    config_path = Path(parsed_args.config) if parsed_args.config else None
    try:
        config, was_created = load_config(config_path)
        if was_created:
            info(f"Created config file: {get_config_path()}")
            info("Edit this file to customize vault path and templates.")
    except Exception as e:
        error(f"Error loading config: {e}")
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

    # Check for inputs - try clipboard if none provided
    if not parsed_args.input:
        clipboard_urls = read_clipboard_urls()
        if clipboard_urls:
            info(f"Reading {len(clipboard_urls)} URL(s) from clipboard")
            parsed_args.input = clipboard_urls
        else:
            error("No input provided and clipboard empty. Use -h for help.")
            return 1

    # Check Node.js and defuddle are installed
    if not check_node_installed():
        error("Node.js is not installed.")
        info("Install from: https://nodejs.org/")
        return 1

    if not check_defuddle_installed():
        error("defuddle is not installed.")
        info("Run 'npm install' in the mdclip directory.")
        return 1

    # Parse inputs to URLs
    urls: list[str] = []
    bookmark_path: Path | None = None

    for input_item in parsed_args.input:
        # Check if this is a bookmark file for section selection
        input_type = detect_input_type(input_item)
        if input_type == InputType.BOOKMARKS_HTML:
            bookmark_path = Path(input_item).expanduser()

        parsed_urls = parse_input(input_item)
        if not parsed_urls and parsed_args.verbose:
            warning(f"No URLs found in '{input_item}'")
        urls.extend(parsed_urls)

    if not urls:
        error("No valid URLs found in input")
        return 1

    # Bookmark section selection for large bookmark files
    if (
        bookmark_path
        and len(urls) > URL_CONFIRM_THRESHOLD
        and not parsed_args.all_sections
        and not parsed_args.yes
    ):
        with create_spinner("Parsing bookmark structure...") as progress:
            progress.add_task("Parsing bookmark structure...", total=None)
            sections = parse_bookmark_structure(bookmark_path)
        if sections:
            flat_sections = flatten_sections(sections)
            if len(flat_sections) > 1:
                section_names = [name for name, _ in flat_sections]
                selected = select_section(
                    section_names,
                    f"Bookmark file has {len(urls)} URLs. Select a section:",
                )
                if selected:
                    # Find the selected section and get its URLs
                    for name, section in flat_sections:
                        if name == selected:
                            urls = get_urls_from_section(section)
                            info(f"Selected '{section.title}' with {len(urls)} URLs")
                            break

    if parsed_args.verbose:
        info(f"Found {len(urls)} URL(s) to process")

    # Confirm before processing many URLs
    if len(urls) > URL_CONFIRM_THRESHOLD and not parsed_args.yes:
        if not confirm(f"Process {len(urls)} URLs?"):
            info("Aborted.")
            return 0

    # Process each URL
    processed_count = 0
    last_filepath: Path | None = None
    for url in urls:
        try:
            result = process_url(url, config, parsed_args)
            if result:
                last_filepath = result
                processed_count += 1
            elif parsed_args.dry_run:
                processed_count += 1
        except (NodeNotInstalledError, DefuddleNotInstalledError) as e:
            error(str(e))
            return 1
        except DefuddleError as e:
            error(f"Processing {url}: {e}")
            if parsed_args.verbose:
                traceback.print_exc()
        except Exception as e:
            error(f"Processing {url}: {e}")
            if parsed_args.verbose:
                traceback.print_exc()

    # Open note after single-URL success
    if len(urls) == 1 and processed_count == 1 and last_filepath:
        should_open = config.get("open_in_obsidian", True) and not parsed_args.no_open
        if should_open:
            vault = Path(config["vault"]).expanduser()
            open_note(last_filepath, vault)

    # Summary
    if len(urls) > 1:
        if processed_count == len(urls):
            success(f"Processed {processed_count}/{len(urls)} URLs")
        else:
            warning(f"Processed {processed_count}/{len(urls)} URLs")

    return 0 if processed_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
