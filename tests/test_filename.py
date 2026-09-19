"""Tests for filename template resolution and date variables."""

from datetime import datetime

from mdclip.config import DEFAULT_CONFIG
from mdclip.frontmatter import parse_date, parse_datetime
from mdclip.templates import Template, render_filename


def test_template_filename_defaults_to_none() -> None:
    """A template without a filename key defers to the config default."""
    assert Template.from_dict({"name": "papers"}).filename is None
    assert Template.from_dict({"name": "x", "filename": "{{slug}}"}).filename == "{{slug}}"


def test_default_filename_in_default_config() -> None:
    assert DEFAULT_CONFIG["default_filename"] == "{{title}} {{published}}"


def test_template_filename_overrides_config_default() -> None:
    config = {"default_filename": "{{title}} {{published}}"}
    template = Template.from_dict({"name": "x", "filename": "{{domain}} - {{title}}"})
    chosen = template.filename or config.get("default_filename") or "{{title}}"
    assert chosen == "{{domain}} - {{title}}"

    template = Template.from_dict({"name": "y"})
    chosen = template.filename or config.get("default_filename") or "{{title}}"
    assert chosen == "{{title}} {{published}}"


def test_render_filename_published_variable() -> None:
    rendered = render_filename(
        "{{title}} {{published}}", {"title": "A Title", "published": "20250721"}
    )
    assert rendered == "A Title 20250721"


def test_parse_datetime_iso_and_long_formats() -> None:
    iso = parse_datetime("2025-07-21T14:30:00Z")
    assert iso is not None and iso.strftime("%Y%m%d") == "20250721"
    assert parse_datetime("July 21, 2025") == datetime(2025, 7, 21)
    assert parse_datetime("Mon, 21 Jul 2025") == datetime(2025, 7, 21)


def test_parse_datetime_returns_none_on_failure() -> None:
    assert parse_datetime("") is None
    assert parse_datetime("not a date") is None
    assert parse_datetime(None) is None  # type: ignore[arg-type]


def test_published_falls_back_to_clip_date() -> None:
    """Mirror the cli.py resolution: unparseable published -> clip date."""
    clip_date = datetime(2026, 9, 19)
    for published in (None, "", "garbage"):
        resolved = parse_datetime(published or "") or clip_date
        assert resolved == clip_date
    resolved = parse_datetime("2025-07-21") or clip_date
    assert resolved.strftime("%Y%m%d") == "20250721"


def test_parse_date_still_returns_original_on_failure() -> None:
    assert parse_date("garbage") == "garbage"
    assert parse_date("2025-07-21", "%Y%m%d") == "20250721"
    assert parse_date("") == ""
