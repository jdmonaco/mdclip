# mdclip

A command-line tool that clips web pages to Markdown files with YAML frontmatter. Think of it as the [Obsidian Web Clipper](https://obsidian.md/clipper) browser extension, but for the terminal.

## Features

- **Template-based routing**: URLs are matched to templates that control output folder, tags, and frontmatter
- **YAML frontmatter**: Automatic metadata including title, author (if available), source URL, creation date, published date (if available), description, and tags
- **Multiple input formats**: Single URLs, bookmark exports, markdown files with links, or text files with URL lists
- **Clipboard support**: Automatically reads URLs from clipboard when no input is provided (macOS)
- **Obsidian integration**: Auto-opens clipped notes in Obsidian after single-URL clipping
- **Bookmark section selection**: For large bookmark files, interactively select which folder to process
- **Skip existing**: Option to skip URLs that already have a clipped file with the same source
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
usage: mdclip [-h] [-o FOLDER] [-t NAME] [--tags TAG [TAG ...]]
              [--skip-existing] [-n] [-y] [--all-sections] [--no-format]
              [--no-open] [--vault PATH] [--config FILE] [--list-templates]
              [--verbose] [--version]
              [INPUT ...]

Clip web pages to Markdown with YAML frontmatter.

positional arguments:
  INPUT                 URL, bookmarks HTML file, or text file with URLs
                        (reads clipboard if omitted)

options:
  -h, --help            show this help message and exit
  -o, --output FOLDER   Output folder (relative to vault or absolute path)
  -t, --template NAME   Use named template (bypasses URL pattern matching)
  --tags TAG [TAG ...]  Additional tags to include in frontmatter
  --skip-existing       Skip URLs that already have a clipped file
  -n, --dry-run         Show what would be done without writing files
  -y, --yes             Skip confirmation prompts
  --all-sections        Process all bookmark sections without prompting
  --no-format           Skip mdformat post-processing
  --no-open             Don't open note after clipping
  --vault PATH          Override vault path from config
  --config FILE         Use alternate config file
  --list-templates      List configured templates and exit
  --verbose             Show detailed output
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

# Skip URLs that already have a clipped file
mdclip --skip-existing urls.txt

# Clip without opening in Obsidian
mdclip --no-open "https://example.com"
```

## Configuration

Configuration is stored in `~/.mdclip.yml`. The config file is automatically created with sensible defaults on first run.

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

# Skip URLs if a file already exists with the same source URL
skip_existing: false

# Open clipped note after single-URL processing
# Inside vault: opens in Obsidian; outside vault: opens in glow/less
open_in_obsidian: true
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
