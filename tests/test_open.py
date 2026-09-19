"""Tests for Obsidian open routing in mdclip.output."""

import subprocess
from pathlib import Path
from unittest.mock import patch

from mdclip import output
from mdclip.output import _open_in_obsidian, open_note


def test_prefers_obz_when_available(tmp_path):
    vault = tmp_path / "vault"
    (vault / "Sub").mkdir(parents=True)
    with patch.object(output.shutil, "which", return_value="/usr/local/bin/obz"), \
         patch.object(output.subprocess, "run") as run, \
         patch.object(output.time, "sleep") as sleep:
        run.return_value.returncode = 0
        assert _open_in_obsidian(Path("Sub/Note.md"), vault) is True
    run.assert_called_once()
    argv = run.call_args[0][0]
    assert argv[:3] == ["/usr/local/bin/obz", "open", "--path"]
    assert argv[3] == str(vault.resolve() / "Sub" / "Note.md")
    sleep.assert_not_called()


def test_obz_nonzero_exit_reports_failure(tmp_path):
    with patch.object(output.shutil, "which", return_value="obz"), \
         patch.object(output.subprocess, "run") as run:
        run.return_value.returncode = 1
        assert _open_in_obsidian(Path("Note.md"), tmp_path) is False


def test_fallback_waits_then_opens_uri(tmp_path):
    with patch.object(output.shutil, "which", return_value=None), \
         patch.object(output.subprocess, "run") as run, \
         patch.object(output.time, "sleep") as sleep:
        assert _open_in_obsidian(Path("Note.md"), tmp_path) is True
    sleep.assert_called_once_with(output.OBSIDIAN_SETTLE_SECONDS)
    argv = run.call_args[0][0]
    assert argv[0] == "open"
    assert argv[1].startswith("obsidian://open?path=")
    assert "osascript" not in str(run.call_args_list)


def test_fallback_subprocess_error(tmp_path):
    with patch.object(output.shutil, "which", return_value=None), \
         patch.object(output.subprocess, "run", side_effect=subprocess.SubprocessError("x")), \
         patch.object(output.time, "sleep"):
        assert _open_in_obsidian(Path("Note.md"), tmp_path) is False


def test_open_note_outside_vault_uses_pager(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    outside = tmp_path / "elsewhere.md"
    outside.write_text("x")
    with patch.object(output, "_open_in_pager", return_value=True) as pager, \
         patch.object(output, "_open_in_obsidian") as obs:
        assert open_note(outside, vault) is True
    pager.assert_called_once_with(outside)
    obs.assert_not_called()
