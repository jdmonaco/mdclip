"""YAML frontmatter generation for mdclip."""

from datetime import datetime
from typing import Any

import yaml


def build_frontmatter(
    metadata: dict[str, Any],
    template: Any,  # Template dataclass
    config: dict[str, Any],
    extra_tags: list[str] | None = None,
) -> str:
    """Build YAML frontmatter from metadata, template, and config.

    Args:
        metadata: Extracted metadata (title, url, author, description, etc.)
        template: The matched Template object
        config: Global configuration
        extra_tags: Additional tags from CLI

    Returns:
        YAML frontmatter string including --- delimiters
    """
    fm: dict[str, Any] = {}

    # Add default properties
    default_props = config.get("default_properties", ["title", "source", "created"])

    for prop in default_props:
        if prop == "title":
            fm["title"] = metadata.get("title", "Untitled")
        elif prop == "source":
            fm["source"] = metadata.get("url", "")
        elif prop == "created":
            date_format = config.get("date_format", "%Y-%m-%d %H:%M")
            fm["created"] = datetime.now().strftime(date_format)
        elif prop == "author":
            # Author may be a string or list from defuddle
            author = metadata.get("author")
            if author:
                fm["author"] = [author] if isinstance(author, str) else author
        elif prop == "description":
            if metadata.get("description"):
                fm["description"] = metadata["description"]
        elif prop == "published":
            if metadata.get("published"):
                fm["published"] = metadata["published"]

    # Add tags from template and CLI
    tags = list(template.tags) if template.tags else ["webclip"]
    if extra_tags:
        for tag in extra_tags:
            if tag not in tags:
                tags.append(tag)
    fm["tags"] = tags

    # Add template-specific properties
    if template.properties:
        fm.update(template.properties)

    # Generate YAML
    yaml_content = yaml.dump(
        fm,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=1000,  # Prevent line wrapping
    )

    return f"---\n{yaml_content}---\n\n"


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse frontmatter from markdown content.

    Args:
        content: Markdown content potentially starting with frontmatter

    Returns:
        Tuple of (frontmatter dict, remaining content)
    """
    if not content.startswith("---"):
        return {}, content

    # Find the closing ---
    end_idx = content.find("---", 3)
    if end_idx == -1:
        return {}, content

    yaml_content = content[3:end_idx].strip()
    remaining = content[end_idx + 3:].lstrip("\n")

    try:
        fm = yaml.safe_load(yaml_content) or {}
    except yaml.YAMLError:
        return {}, content

    return fm, remaining
