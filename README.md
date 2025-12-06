# mdclip

A command-line tool that clips web pages to Markdown files with YAML frontmatter. Think of it as the [Obsidian Web Clipper](https://obsidian.md/clipper) browser extension, but for the terminal.

## Features

- **Template-based routing**: URLs are matched to templates that control output folder, tags, and frontmatter
- **YAML frontmatter**: Automatic metadata including title, source URL, creation date, and tags
- **Multiple input formats**: Single URLs, bookmark exports, or text files with URL lists
- **Optional formatting**: Post-process output with mdformat for consistent styling
- **Batch processing**: Clip multiple URLs in one command

## Installation

### Prerequisites

**gather-cli** (required) - Extracts readable content from web pages:

```bash
brew tap ttscoff/thelab
brew install gather-cli
```

**mdformat** (optional) - Auto-formats output Markdown:

```bash
brew install mdformat
```

### Install mdclip

```bash
# With pipx (recommended)
pipx install mdclip

# Or with pip
pip install mdclip

# Or from source
git clone https://github.com/jdmonaco/mdclip.git
cd mdclip
pip install -e .
```

## Quick Start

```bash
# Initialize configuration file
mdclip --init-config

# Edit ~/.mdclip.yml to set your vault path
vim ~/.mdclip.yml

# Clip a URL
mdclip "https://github.com/kepano/defuddle"
```

## Usage

```
usage: mdclip [-h] [-o PATH] [-v PATH] [-t NAME] [--tags TAG [TAG ...]]
              [--dry-run] [--config PATH] [--init-config] [--list-templates]
              [--verbose] [--no-format] [--version]
              [INPUT ...]

Clip web pages to Markdown with YAML frontmatter

positional arguments:
  INPUT                 URL(s), path to bookmarks HTML, or text file with URLs

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
  --version             show program's version number and exit
```

## Examples

```bash
# Clip a single URL
mdclip "https://docs.python.org/3/library/pathlib.html"

# Clip multiple URLs
mdclip "https://github.com/..." "https://stackoverflow.com/..."

# Preview without saving
mdclip --dry-run "https://example.com"

# Override output folder
mdclip -o "Projects/Research" "https://arxiv.org/abs/..."

# Add extra tags
mdclip --tags python tutorial "https://realpython.com/..."

# Clip from a bookmarks export
mdclip ~/Downloads/bookmarks.html

# Clip from a text file (one URL per line)
mdclip urls.txt

# Force a specific template
mdclip -t documentation "https://example.com/docs"
```

## Configuration

Configuration is stored in `~/.mdclip.yml`. Run `mdclip --init-config` to create a default config with example templates.

### Key Settings

```yaml
# Path to your notes vault
vault: ~/Documents/Obsidian/Notes

# Date formats
date_format: "%Y-%m-%d %H:%M"        # For frontmatter
filename_date_format: "%Y-%m-%d"      # For filenames

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
created: 2024-01-15 14:30
tags:
  - webclip
  - docs
---

# Page Title

Content extracted from the web page...
```

## License

MIT
