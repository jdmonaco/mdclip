# CLAUDE.md - mdclip Development Guide

## Project Overview

**mdclip** is a macOS command-line tool that downloads web pages, extracts readable content, converts to Markdown, and saves as notes with YAML frontmatter. It replicates the functionality of the Obsidian Web Clipper browser extension but operates entirely from the command line, enabling batch processing and automation.

## Core Concept

```
URL(s) → Template Matching → Content Extraction → Markdown + Frontmatter → File Output
```

The tool processes URLs through a template system where URL patterns determine:
- Output folder location
- YAML frontmatter properties
- Tags
- Filename format

## Technology Stack

- **Language**: Python 3.10+
- **Content Extraction**: [defuddle](https://github.com/kepano/defuddle) via Node.js
  - Same library used by Obsidian Web Clipper
  - Extracts title, author, description, published date, site name
  - Converts HTML to clean Markdown
- **Dependencies**:
  - `pyyaml` - Configuration and frontmatter
  - `rich` - Colored console output and progress spinners
  - Node.js runtime with defuddle, jsdom (via npm install)

## Architecture

```
mdclip/
├── src/mdclip/
│   ├── __init__.py         # Package version
│   ├── cli.py              # Argument parsing, main entry point
│   ├── config.py           # Configuration loading, defaults, auto-init
│   ├── console.py          # Rich console output helpers
│   ├── extractor.py        # defuddle wrapper, content extraction
│   ├── frontmatter.py      # YAML frontmatter generation
│   ├── inputs.py           # URL/clipboard/bookmark parsing
│   ├── output.py           # File writing, path handling
│   ├── selector.py         # Interactive section selection (gum/fallback)
│   └── templates.py        # Template matching logic
├── scripts/
│   ├── defuddle-extract.js  # Node.js extraction script
│   └── browser-clip-script.sh # macOS browser automation
├── tests/
├── package.json            # Node.js dependencies (defuddle, jsdom)
├── pyproject.toml
├── README.md
└── CLAUDE.md
```

## Configuration File

Location: `~/.mdclip.yml`

Auto-created with defaults on first run.

### Structure

```yaml
# Global settings
vault: ~/Documents/Obsidian/Notes
date_format: "%Y-%m-%d"
filename_date_format: "%Y-%m-%d"
default_folder: Inbox/Clips
auto_format: false       # Enable mdformat post-processing
skip_existing: false     # Skip URLs with existing clipped files
open_in_obsidian: true   # Auto-open notes after clipping

# Default frontmatter properties
default_properties:
  - title
  - source
  - author
  - created
  - published
  - description

# Templates with URL pattern triggers
templates:
  - name: github
    triggers:
      - "https://github.com/"
      - "^https://[\\w-]+\\.github\\.io/"
    folder: Reference/Software
    tags: [webclip, software, github]
    filename: "{{title}}"
    properties:
      type: repository

  - name: default  # Fallback template (required)
    folder: Inbox/Clips
    tags: [webclip]
    filename: "{{title}}"
```

## CLI Interface

```
mdclip [OPTIONS] [INPUT ...]

Arguments:
  INPUT                     URL(s), bookmark HTML, markdown file, or text file.
                            If omitted, reads URLs from clipboard.

Options:
  -o, --output FOLDER       Output folder (relative to vault or absolute)
  -t, --template NAME       Use named template (bypass pattern matching)
  --tags TAG [TAG...]       Additional tags to include in frontmatter
  --skip-existing           Skip URLs that already have a clipped file
  -n, --dry-run             Show what would be done without writing files
  -y, --yes                 Skip confirmation prompts
  --all-sections            Process all bookmark sections without prompting
  --no-format               Skip mdformat post-processing
  --no-open                 Don't open note after clipping
  --vault PATH              Override vault path from config
  --config FILE             Use alternate config file
  --list-templates          List configured templates and exit
  --verbose                 Show detailed output
  --version                 Show version
  -h, --help                Show help
```

## Key Behaviors

### Input Handling
1. No input provided → read URLs from clipboard via `pbpaste`
2. Input starts with `http://` or `https://` → treat as URL
3. Input is `.html` file → parse as bookmarks export
4. Input is `.md` file → extract URLs from markdown links `[text](url)`
5. Input is other file → read as text, one URL per line
6. Multiple inputs can be mixed

### Clipboard Support
- Uses macOS `pbpaste` to read clipboard contents
- Parses clipboard text for both plain URLs and markdown links
- Enables quick workflow: copy URL → run `mdclip` → done

### Bookmark Section Selection
- For bookmark files with >10 URLs, prompts to select a section
- Uses `gum choose` if available, otherwise numbered input fallback
- `--all-sections` bypasses selection and processes everything

### Batch Confirmation
- Prompts before processing >10 URLs
- `-y/--yes` skips the confirmation prompt

### Skip Existing
- `--skip-existing` flag or `skip_existing: true` in config
- Checks if file exists with same source URL in frontmatter
- Skips re-clipping if already present; otherwise appends `(1)`, `(2)`, etc.

### Obsidian Integration
- After clipping a single URL, auto-opens the note in Obsidian
- Uses `obsidian://open` URL scheme with vault name and file path
- Brings Obsidian to foreground via System Events
- For files outside vault, opens in `glow -p` or `less` as fallback
- `--no-open` flag or `open_in_obsidian: false` disables this

### Template Matching
1. Iterate templates in order
2. For each template, check each trigger pattern against URL
3. Patterns starting with `^` or containing regex metacharacters → regex match
4. Plain strings → substring match (case-insensitive)
5. First match wins
6. Fall back to `default` template if no match

### Filename Generation
- Template variables: `{{title}}`, `{{date}}`, `{{slug}}`, `{{domain}}`
- Sanitization: Remove `< > : " / \ | ? *`, collapse whitespace
- Length limit: 100 characters
- Duplicate handling: Append ` (1)`, ` (2)`, etc.

### Frontmatter Generation
```yaml
---
title: Page Title
source: https://example.com/article
author:
  - Author Name
created: 2024-01-15
published: 2024-01-10
description: A brief description of the page content
tags:
  - webclip
  - software
---
```

### Content Extraction via defuddle
The `scripts/defuddle-extract.js` script:
1. Fetches URL with jsdom
2. Runs defuddle extraction
3. Returns JSON with title, author, description, published, content, etc.

Called from Python via `subprocess.run()`.

## Console Output

Uses Rich library for colored output to stderr:
- `info()` - Blue ℹ for informational messages
- `success()` - Green ✓ for success
- `warning()` - Yellow ⚠ for warnings
- `error()` - Red ✗ for errors
- `create_spinner()` - Progress spinner during extraction

## Error Handling

- **Node.js not installed**: Clear error with install instructions
- **defuddle not installed**: Prompts to run `npm install`
- **Network errors**: Log and continue to next URL in batch
- **Empty content**: Warn but still create note with frontmatter only
- **Invalid config YAML**: Exit with parse error details

## Development Commands

```bash
# Install dependencies
uv sync
npm install

# Run tool
uv run mdclip "https://example.com"

# Type checking
uv run mypy src/mdclip/ --ignore-missing-imports

# Linting
uv run ruff check src/mdclip/

# Format check
uv run ruff format --check src/mdclip/
```

## Code Style

- Type hints throughout
- Docstrings for public functions
- f-strings for formatting
- pathlib.Path for all file operations
- subprocess.run with capture_output=True for external commands
- No bare exceptions; catch specific errors
- Rich console for all user-facing output (not print)

## Example Usage Patterns

```bash
# Clip from clipboard (copy URL first)
mdclip

# Single URL (auto-opens in Obsidian)
mdclip "https://github.com/kepano/defuddle"

# Clip without opening in Obsidian
mdclip --no-open "https://example.com"

# Multiple URLs
mdclip "https://github.com/..." "https://docs.python.org/..."

# From bookmarks export (will prompt for section selection)
mdclip ~/Downloads/bookmarks.html

# Process all bookmark sections
mdclip --all-sections bookmarks.html

# From markdown file with links
mdclip links.md

# From URL list file
mdclip urls.txt

# Skip URLs that already have clipped files
mdclip --skip-existing urls.txt

# Override output location
mdclip -o "Projects/Research" "https://example.com/article"

# Add extra tags
mdclip --tags research python "https://docs.python.org/3/library/re.html"

# Dry run for testing
mdclip -n bookmarks.html

# Skip confirmation for large batches
mdclip -y bookmarks.html
```

## Future Enhancements

- JavaScript-rendered page support (via Playwright/Puppeteer)
- Image downloading and local storage
- Template variables from schema.org data
- Watch mode for clipboard URLs
- Cross-platform clipboard support (Linux/Windows)

## Claude Code Configuration

This project uses the global `~/.claude/settings.json` for all permissions and settings.

### Tools Manager: tlmgr

The `tlmgr` command manages all tool repositories from the umbrella ~/tools directory:

```bash
tlmgr --json summary  # Overall status of all 14 repos
tlmgr --json list     # Detailed status with branches
tlmgr changes         # Show uncommitted changes
tlmgr unpushed        # Show unpushed commits
```

Always use `tlmgr` (not relative paths like `./bin/tools-manager.sh`).

### Development Workflow

**Auto-allowed git operations:**
- Read: status, diff, log, show, branch, grep, blame
- Write: add, commit, push, pull, checkout, switch, restore, stash

**Require confirmation:**
- Destructive: merge, rebase, reset, cherry-pick, revert
- Force operations: push --force
- Repository changes: clone, init, submodule

### Available Development Tools

**Python:** pytest, pip, poetry, uv (install, run, sync)  
**Node:** npm (test, run, install), node  
**Build:** make, bash scripts in ./scripts/  
**Utilities:** find, grep, rg, cat, ls, tree, jq, yq, head, tail, wc  
**Documents:** pandoc, md2docx, mdformat

### Configuration

All permissions are centralized in `~/.claude/settings.json`:
- Sandbox is disabled globally
- Full read/write access to ~/tools/** and ~/agents/**
- Standard security protections (no ~/.ssh, .env files, etc.)
- Consistent behavior across all projects

No project-specific `.claude/` folders are needed.