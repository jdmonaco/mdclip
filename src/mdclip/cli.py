"""Command-line interface for mdclip."""

import argparse
import sys
import traceback
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from rich.table import Table

from . import __version__
from .config import (
    get_config_path,
    get_template_by_name,
    load_config,
    merge_config,
)
from .console import confirm, console, create_spinner, error, info, success, warning
from .cookies import (
    filter_cookies_for_url,
    find_cookies_for_url,
    format_cookie_header,
    load_cookies_from_file,
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
    detect_formatter,
    format_markdown,
    get_unique_filepath,
    open_note,
    resolve_output_path,
    resolve_template_folder,
    write_note,
)
from .ratelimit import DomainRateLimiter
from .selector import select_section
from .templates import Template, match_template, render_filename, sanitize_filename, slugify

def shorten_path(path: str) -> str:
    """Shorten paths for display: $HOME -> ~, OneDrive CloudStorage -> ~/OneDrive."""
    home = str(Path.home())
    onedrive_prefix = f"{home}/Library/CloudStorage/OneDrive-"
    if path.startswith(onedrive_prefix):
        rest = path[len(onedrive_prefix):]
        if "/" in rest:
            _, subpath = rest.split("/", 1)
            return f"~/OneDrive/{subpath}"
        return f"~/OneDrive/{rest}"
    if path.startswith(home + "/"):
        return "~" + path[len(home):]
    elif path == home:
        return "~"
    return path


def preview_clipboard_urls(
    urls: list[str],
    config: dict,
    args: argparse.Namespace,
) -> bool:
    """Preview clipboard URLs with template matching before processing.

    For a single URL, prints a one-line summary. For multiple URLs, displays
    a Rich table with domain, template, and folder columns, then prompts
    for confirmation.

    Returns:
        True to proceed, False to abort.
    """
    vault = Path(config.get("vault", "")).expanduser()
    templates = config.get("templates", [])

    def _resolve_template(url: str) -> Template:
        if args.template:
            tdict = get_template_by_name(args.template, config)
            if tdict:
                return Template.from_dict(tdict)
        return match_template(url, templates)

    def _resolve_folder(template: Template) -> str:
        if args.output:
            return args.output
        if template.folder:
            return shorten_path(str(resolve_template_folder(template.folder, vault)))
        return "."

    def _domain(url: str) -> str:
        host = urlparse(url).netloc
        return host.removeprefix("www.")

    if len(urls) == 1:
        t = _resolve_template(urls[0])
        info(f"Clipboard: {_domain(urls[0])} → {t.name} ({_resolve_folder(t)})")
        return True

    table = Table(title="Clipboard URLs")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Domain")
    table.add_column("Template", style="cyan")
    table.add_column("Folder")

    for i, url in enumerate(urls, 1):
        t = _resolve_template(url)
        table.add_row(str(i), _domain(url), t.name, _resolve_folder(t))

    console.print(table)

    if args.dry_run:
        return True

    return confirm(f"Process {len(urls)} URLs?", default=True)


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
  mdclip --force urls.txt

Shell completion:
  mdclip completion bash            Output completion script
  mdclip completion bash --install  Install to user completions directory
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
        help="Output folder (relative to cwd or absolute path)",
    )

    parser.add_argument(
        "-t", "--template",
        metavar="NAME",
        help="Use named template (bypasses URL pattern matching)",
    )

    parser.add_argument(
        "--tags",
        metavar="TAGS",
        help="Additional tags, comma-separated (e.g., --tags foo,bar,baz)",
    )

    # Behavior
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if file with same source URL exists",
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
        help="Skip auto-formatting post-processing",
    )

    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Don't open note after clipping",
    )

    parser.add_argument(
        "--rate-limit",
        type=float,
        default=None,
        metavar="SECONDS",
        help="Seconds between requests to same domain (default: 3.0, 0 to disable)",
    )

    parser.add_argument(
        "--cookies",
        metavar="FILE",
        help="Load cookies from Netscape cookies.txt file for authenticated requests",
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
        folder = t.get("folder", "Capture")
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
    formatter: str | None = None,
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

    # Load cookies if provided or auto-detect
    cookie_header = None
    if args.cookies:
        cookies_path = Path(args.cookies).expanduser()
        if not cookies_path.exists():
            error(f"Cookies file not found: {cookies_path}")
            return None
        all_cookies = load_cookies_from_file(cookies_path)
        url_cookies = filter_cookies_for_url(all_cookies, url)
        if url_cookies:
            cookie_header = format_cookie_header(url_cookies)
            if args.verbose:
                info(f"Using {len(url_cookies)} cookies for {urlparse(url).netloc}")
    else:
        auto_cookies_cfg = config.get("auto_cookies", {})
        if auto_cookies_cfg.get("enabled", True):
            search_dirs = [
                Path(d).expanduser()
                for d in auto_cookies_cfg.get("search_dirs", ["~/Downloads"])
            ]
            found = find_cookies_for_url(url, search_dirs)
            if found:
                all_cookies = load_cookies_from_file(found)
                url_cookies = filter_cookies_for_url(all_cookies, url)
                if url_cookies:
                    cookie_header = format_cookie_header(url_cookies)
                    if args.verbose:
                        info(f"Auto-detected {len(url_cookies)} cookies from {found.name}")

    # Extract content and metadata with spinner
    with create_spinner() as progress:
        progress.add_task(f"Extracting: {url}", total=None)
        page_data = extract_page(
            url,
            cookies=cookie_header,
            exa_fallback=config.get("exa_fallback", False),
            exa_min_content_length=config.get("exa_min_content_length", 100),
            exa_livecrawl=config.get("exa_livecrawl", "preferred"),
        )

    title = page_data.get("title", "Untitled")
    content = page_data.get("content", "")

    if args.verbose:
        info(f"Title: {title}")

    if not content:
        warning(f"No content extracted from {url}, skipping")
        return None

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
    extra_tags = [t.strip() for t in args.tags.split(",")] if args.tags else None
    frontmatter = build_frontmatter(
        metadata,
        template,
        config,
        extra_tags=extra_tags,
    )

    # Assemble full note with title heading
    full_content = frontmatter + f"# {title}\n\n" + content

    # Determine output path
    vault = Path(config["vault"]).expanduser()
    if args.output:
        # Explicit -o: cwd-relative
        output_folder = resolve_output_path(args.output)
    elif template.folder:
        # Template auto-routing: vault-relative
        output_folder = resolve_template_folder(template.folder, vault)
    else:
        # No -o, no template folder: cwd
        output_folder = Path.cwd()
        output_folder.mkdir(parents=True, exist_ok=True)

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

    # Check for existing file (skip by default unless --force)
    skip_existing = not args.force
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
    if formatter:
        used = format_markdown(filepath, formatter)
        if used and args.verbose:
            info(f"Formatted with {used}")

    success(f"Saved: {shorten_path(str(filepath))}")

    return filepath


def main(args: list[str] | None = None) -> int:
    """Main entry point.

    Args:
        args: Command-line arguments (for testing)

    Returns:
        Exit code (0 for success)
    """
    # Handle completion subcommand before argparse
    if args is None:
        args = sys.argv[1:]
    if args and args[0] == "completion":
        from .completion import completion_command
        return completion_command(args[1:])

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
    from_clipboard = False
    if not parsed_args.input:
        clipboard_urls = read_clipboard_urls()
        if clipboard_urls:
            from_clipboard = True
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

    # Detect formatter once for the session
    formatter = None
    if config.get("auto_format") and not parsed_args.no_format:
        formatter = detect_formatter()
        if formatter and parsed_args.verbose:
            info(f"Formatter: {formatter}")

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

    # Preview clipboard URLs with template matching
    if from_clipboard and not parsed_args.yes:
        if not preview_clipboard_urls(urls, config, parsed_args):
            info("Aborted.")
            return 0

    # Confirm before processing many URLs (non-clipboard input only)
    if not from_clipboard and len(urls) > URL_CONFIRM_THRESHOLD and not parsed_args.yes:
        if not confirm(f"Process {len(urls)} URLs?"):
            info("Aborted.")
            return 0

    # Initialize rate limiter
    rate_limit = parsed_args.rate_limit
    if rate_limit is None:
        rate_limit = config.get("rate_limit_seconds", 3.0)
    rate_limiter = DomainRateLimiter(delay_seconds=rate_limit) if rate_limit > 0 else None

    # Process URLs with rate limiting
    processed_count = 0
    last_filepath: Path | None = None
    pending = list(urls)

    while pending or (rate_limiter and rate_limiter.has_deferred()):
        # Check for ready deferred URLs
        if rate_limiter:
            ready_deferred = rate_limiter.get_ready_deferred()
            if ready_deferred:
                domains = sorted(set(rate_limiter.get_domain(u) for u in ready_deferred))
                info(f"↩ Processing {len(ready_deferred)} deferred ({', '.join(domains)})")
                pending = ready_deferred + pending

        if not pending:
            # All pending processed, but deferred remain - wait for next
            if rate_limiter and rate_limiter.has_deferred():
                url = rate_limiter.pop_deferred_with_wait()
                if url:
                    wait_time = rate_limiter.delay_seconds
                    info(f"⏳ Waiting {wait_time:.1f}s for {rate_limiter.get_domain(url)}...")
                    pending = [url]
            continue

        # Process all currently pending URLs in a batch
        deferred_this_batch: list[str] = []
        processing_queue = pending.copy()
        pending.clear()

        for url in processing_queue:
            # Check rate limit
            if rate_limiter and not rate_limiter.is_allowed(url):
                rate_limiter.defer(url)
                deferred_this_batch.append(url)
                continue

            try:
                result = process_url(url, config, parsed_args, formatter=formatter)
                if rate_limiter:
                    rate_limiter.record_access(url)
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

        # Emit aggregated deferral message for this batch
        if deferred_this_batch and rate_limiter:
            domains = sorted(set(rate_limiter.get_domain(u) for u in deferred_this_batch))
            info(f"Deferred {len(deferred_this_batch)} URL(s) ({', '.join(domains)})")

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
