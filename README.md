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

**Trigger types:**
- Substring match: `"https://github.com/"`
- Regex pattern: `"^https://[\\w-]+\\.github\\.io/"`
- Built-in filter: `"@academic"` (see below)

**Filename variables**: `{{title}}`, `{{date}}`, `{{slug}}`, `{{domain}}`

### Built-in Triggers

mdclip includes built-in triggers for common content types using smart URL matching with domain and path scoring.

| Trigger | Description | Domains |
|---------|-------------|---------|
| `@academic` | Scientific journals and publishers | 113 |
| `@docs` | Software documentation and references | 35 |
| `@edu` | Educational content and .edu sites | 15+ |
| `@gov` | Government sites (.gov/.mil) | 45+ |
| `@longform` | Magazines and longform journalism | 75 |
| `@news` | US-focused news sources | 50 |
| `@scitech` | Science & technology publications | 35 |
| `@social` | Social media & discussion platforms | 35 |
| `@wiki` | Wikis and encyclopedias | 25 |

#### `@academic`

Matches academic and scientific journal article URLs from Nature, arXiv, PubMed, IEEE, ACM, Springer, Elsevier, and more. Requires domain + article path for high precision.

```yaml
templates:
  - name: papers
    triggers:
      - "@academic"
    folder: Reference/Papers
    tags: [paper, research]
```

#### `@docs`

Matches software documentation URLs from official language docs (Python, MDN, Rust), documentation platforms (Read the Docs, GitHub Pages), cloud providers, and spec references. Requires domain + path for precision.

```yaml
templates:
  - name: documentation
    triggers:
      - "@docs"
    folder: Reference/Docs
    tags: [docs, reference]
```

#### `@edu`

Matches educational content from online learning platforms (Coursera, Khan Academy, edX) and any .edu domain. The .edu TLD is matched automatically.

```yaml
templates:
  - name: education
    triggers:
      - "@edu"
    folder: Reference/Education
    tags: [education, learning]
```

#### `@gov`

Matches government and official sites via .gov and .mil TLDs plus known agency domains. Works for federal, state, and international government sites.

```yaml
templates:
  - name: government
    triggers:
      - "@gov"
    folder: Reference/Government
    tags: [government, official]
```

#### `@longform`

Matches general interest magazines and longform journalism sites including The Atlantic, New Yorker, Economist, Harper's, literary reviews (NYRB, LRB, Paris Review), and political magazines. Sources curated from [aldaily.com](https://aldaily.com).

```yaml
templates:
  - name: longform
    triggers:
      - "@longform"
    folder: Reference/Longform
    tags: [longform, magazine]
```

#### `@news`

Matches news article URLs from major US newspapers, TV networks, wire services, and digital-native outlets. Trusts domain alone (lower threshold) for known news sources.

```yaml
templates:
  - name: news
    triggers:
      - "@news"
    folder: Reference/News
    tags: [news, current-events]
```

#### `@scitech`

Matches popular science and technology publication URLs from Wired, Ars Technica, The Verge, Scientific American, and more. Trusts domain alone for known sources.

```yaml
templates:
  - name: scitech
    triggers:
      - "@scitech"
    folder: Reference/SciTech
    tags: [scitech, reading]
```

#### `@social`

Matches social media and discussion platform URLs from Twitter/X, Reddit, Hacker News, YouTube, Mastodon, LinkedIn, and more. Trusts domain alone for known platforms.

```yaml
templates:
  - name: social
    triggers:
      - "@social"
    folder: Reference/Social
    tags: [social, discussion]
```

#### `@wiki`

Matches wiki and encyclopedia URLs from Wikipedia, Fandom, Britannica, and software project wikis. Trusts domain alone for known wiki platforms.

```yaml
templates:
  - name: wiki
    triggers:
      - "@wiki"
    folder: Reference/Wiki
    tags: [wiki, reference]
```

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
