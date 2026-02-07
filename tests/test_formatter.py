"""Tests for the formatter cascade (mdfmt > mdformat)."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mdclip.output import detect_formatter, format_markdown


class TestDetectFormatter:
    """Tests for detect_formatter()."""

    @patch("mdclip.output.shutil.which")
    def test_prefers_mdfmt_over_mdformat(self, mock_which):
        """mdfmt should be preferred when both are available."""
        mock_which.side_effect = lambda cmd: f"/usr/local/bin/{cmd}"
        assert detect_formatter() == "mdfmt"
        mock_which.assert_called_once_with("mdfmt")

    @patch("mdclip.output.shutil.which")
    def test_falls_back_to_mdformat(self, mock_which):
        """Falls back to mdformat when mdfmt is not available."""
        mock_which.side_effect = lambda cmd: None if cmd == "mdfmt" else f"/usr/local/bin/{cmd}"
        assert detect_formatter() == "mdformat"

    @patch("mdclip.output.shutil.which")
    def test_returns_none_when_neither_available(self, mock_which):
        """Returns None when no formatter is installed."""
        mock_which.return_value = None
        assert detect_formatter() is None

    @patch("mdclip.output.shutil.which")
    def test_only_mdfmt_available(self, mock_which):
        """Works when only mdfmt is installed."""
        mock_which.side_effect = lambda cmd: "/usr/local/bin/mdfmt" if cmd == "mdfmt" else None
        assert detect_formatter() == "mdfmt"

    @patch("mdclip.output.shutil.which")
    def test_only_mdformat_available(self, mock_which):
        """Works when only mdformat is installed."""
        mock_which.side_effect = lambda cmd: "/usr/local/bin/mdformat" if cmd == "mdformat" else None
        assert detect_formatter() == "mdformat"


class TestFormatMarkdown:
    """Tests for format_markdown()."""

    @patch("mdclip.output.subprocess.run")
    def test_returns_formatter_name_on_success(self, mock_run):
        """Returns the formatter name when formatting succeeds."""
        mock_run.return_value = MagicMock(returncode=0)
        result = format_markdown(Path("/tmp/test.md"), "mdfmt")
        assert result == "mdfmt"

    @patch("mdclip.output.subprocess.run")
    def test_returns_none_on_nonzero_exit(self, mock_run):
        """Returns None when the formatter exits with an error."""
        mock_run.return_value = MagicMock(returncode=1)
        result = format_markdown(Path("/tmp/test.md"), "mdformat")
        assert result is None

    @patch("mdclip.output.subprocess.run")
    def test_passes_correct_command(self, mock_run):
        """Passes the formatter name and file path to subprocess."""
        mock_run.return_value = MagicMock(returncode=0)
        path = Path("/tmp/test.md")
        format_markdown(path, "mdfmt")
        mock_run.assert_called_once_with(
            ["mdfmt", str(path)],
            capture_output=True,
            text=True,
            timeout=30,
        )

    @patch("mdclip.output.subprocess.run")
    def test_handles_timeout(self, mock_run):
        """Returns None on subprocess timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="mdfmt", timeout=30)
        result = format_markdown(Path("/tmp/test.md"), "mdfmt")
        assert result is None

    @patch("mdclip.output.subprocess.run")
    def test_handles_subprocess_error(self, mock_run):
        """Returns None on subprocess errors."""
        mock_run.side_effect = subprocess.SubprocessError("failed")
        result = format_markdown(Path("/tmp/test.md"), "mdformat")
        assert result is None

    @patch("mdclip.output.subprocess.run")
    def test_works_with_mdformat(self, mock_run):
        """Works correctly with mdformat as the formatter."""
        mock_run.return_value = MagicMock(returncode=0)
        result = format_markdown(Path("/tmp/test.md"), "mdformat")
        assert result == "mdformat"
        assert mock_run.call_args[0][0][0] == "mdformat"
