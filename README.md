# mdclip

A command-line tool that clips web pages to Markdown files with YAML frontmatter. Think of it as the [Obsidian Web Clipper](https://obsidian.md/clipper) browser extension, but for the terminal.

## Features

- **Template-based routing**: URLs are matched to templates that control output folder, tags, and frontmatter
- **YAML frontmatter**: Automatic metadata including title, author, source URL, creation date, description, and tags
- **Multiple input formats**: Single URLs, bookmark exports, markdown files with links, or text files with URL lists
- **Clipboard support**: Automatically reads URLs from clipboard when no input is provided (macOS)
- **Bookmark section selection**: For large bookmark files, interactively select which folder to process
- **Optional formatting**: Post-process output with mdformat for consistent styling
- **Batch processing**: Clip multiple URLs in one command with confirmation for large batches
- **Rich console output**: Colored status messages and progress spinners

## Installation

### Prerequisites

**Node.js** (required) - Used for content extraction via [defuddle](https://github.com/kepano/defuddle):

```bash
# macOS with Homebrew
brew install node

# Or download from https://nodejs.org/
```

**mdformat** (optional) - Auto-formats output Markdown:

```bash
brew install mdformat
```

### Install mdclip

```bash
# Clone the repository
git clone https://github.com/jdmonaco/mdclip.git
cd mdclip

# Install Node.js dependencies
npm install

# Install Python package
pip install -e .

# Or with uv
uv pip install -e .
```

## Quick Start

```bash
# Clip a URL (config file is auto-created on first run)
mdclip "https://github.com/kepano/defuddle"

# Edit ~/.mdclip.yml to customize vault path and templates
vim ~/.mdclip.yml
```

## Usage

```
usage: mdclip [-h] [-o PATH] [-v PATH] [-t NAME] [--tags TAG [TAG ...]]
              [--dry-run] [--config PATH] [--init-config] [--list-templates]
              [--verbose] [--no-format] [-y] [--all-sections] [--version]
              [INPUT ...]

Clip web pages to Markdown with YAML frontmatter

positional arguments:
  INPUT                 URL(s), path to bookmarks HTML, markdown file, or text
                        file with URLs. If omitted, reads from clipboard.

options:
  -h, --help            show this help message and exit
  -o, --output PATH     Override output folder (relative to vault or absolute)
  -v, --vault PATH      Override vault path
  -t, --template NAME   Force specific template (bypass pattern matching)
  --tags TAG [TAG ...]  Additional tags to append
  --dry-run             Show what would be done without writing files
  --config PATH         Use alternate config file
  --init-config         Initialize default config file and exit
  --list-templates      List configured templates and exit
  --verbose             Verbose output
  --no-format           Skip mdformat post-processing
  -y, --yes             Skip confirmation prompt for many URLs
  --all-sections        Process all bookmark sections without prompting
  --version             show program's version number and exit
```

## Examples

```bash
# Clip a single URL
mdclip "https://docs.python.org/3/library/pathlib.html"

# Clip from clipboard (copy a URL, then run without arguments)
mdclip

# Clip multiple URLs
mdclip "https://github.com/..." "https://stackoverflow.com/..."

# Preview without saving
mdclip --dry-run "https://example.com"

# Override output folder
mdclip -o "Projects/Research" "https://arxiv.org/abs/..."

# Add extra tags
mdclip --tags python tutorial "https://realpython.com/..."

# Clip from a bookmarks export (prompts to select a section if >10 URLs)
mdclip ~/Downloads/bookmarks.html

# Process all bookmark sections without prompting
mdclip --all-sections ~/Downloads/bookmarks.html

# Skip confirmation for large batches
mdclip -y bookmarks.html

# Clip from a markdown file (extracts URLs from [text](url) links)
mdclip links.md

# Clip from a text file (one URL per line)
mdclip urls.txt

# Force a specific template
mdclip -t documentation "https://example.com/docs"
```

## Configuration

Configuration is stored in `~/.mdclip.yml`. The config file is automatically created with sensible defaults on first run. You can also run `mdclip --init-config` to explicitly create it.

### Key Settings

```yaml
# Path to your notes vault
vault: ~/Documents/Obsidian/Notes

# Date format (for frontmatter 'created' and filenames)
date_format: "%Y-%m-%d"

# Default output folder (relative to vault)
default_folder: Inbox/Clips

# Enable mdformat post-processing
auto_format: false
```

### Templates

Templates match URLs by pattern and control how they're saved:

```yaml
templates:
  - name: github
    triggers:
      - "https://github.com/"
    folder: Reference/Software
    tags:
      - webclip
      - github
    filename: "{{title}}"
    properties:
      type: repository

  - name: default
    folder: Inbox/Clips
    tags:
      - webclip
    filename: "{{title}}"
```

**Filename variables**: `{{title}}`, `{{date}}`, `{{slug}}`, `{{domain}}`

## Output

Each clipped page creates a Markdown file with YAML frontmatter:

```markdown
---
title: "Page Title"
source: https://example.com/article
author:
  - "Author Name"
created: 2024-01-15
published: 2024-01-10
description: "A brief description of the page content"
tags:
  - webclip
  - docs
---

# Page Title

Content extracted from the web page...
```

Metadata is automatically extracted using [defuddle](https://github.com/kepano/defuddle), the same library used by [Obsidian Web Clipper](https://obsidian.md/clipper).

## License

MIT
