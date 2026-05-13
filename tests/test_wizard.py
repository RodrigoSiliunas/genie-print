"""Tests for the interactive wizard."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

from imgwatcher import wizard


def _reader_from(answers: list[str]):
    it: Iterator[str] = iter(answers)

    def _read(_prompt: str) -> str:
        return next(it)

    return _read


def test_wizard_all_defaults_returns_watcher_full(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # 4 prompt answers + mode choice + dry-run + confirm = 7 "" → all defaults
    reader = _reader_from(["", "", "", "", "", ""])
    argv = wizard.run_wizard(reader=reader)
    assert argv is not None
    assert "--host" in argv
    assert "--dest" in argv
    assert "--watch-dir" in argv
    assert "--clipboard" in argv  # default mode is "watcher completo"
    assert "--sync" not in argv
    assert "--dry-run" not in argv
    assert "--no-banner" in argv


def test_wizard_sync_mode(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reader = _reader_from(["myhost", "/my/dest", "imgs", "3", "n", "s"])
    argv = wizard.run_wizard(reader=reader)
    assert argv is not None
    assert "--sync" in argv
    assert "--clipboard" not in argv


def test_wizard_folder_only_mode(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reader = _reader_from(["", "", "", "2", "", "s"])
    argv = wizard.run_wizard(reader=reader)
    assert argv is not None
    assert "--sync" not in argv
    assert "--clipboard" not in argv


def test_wizard_dry_run_flag(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reader = _reader_from(["", "", "", "1", "s", "s"])
    argv = wizard.run_wizard(reader=reader)
    assert "--dry-run" in argv


def test_wizard_cancel_at_confirm_returns_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reader = _reader_from(["", "", "", "", "", "n"])
    argv = wizard.run_wizard(reader=reader)
    assert argv is None


def test_wizard_keyboard_interrupt_returns_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def _interrupt(_prompt: str) -> str:
        raise KeyboardInterrupt

    argv = wizard.run_wizard(reader=_interrupt)
    assert argv is None


def test_wizard_persists_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reader = _reader_from(["custom-host", "/custom/dest", "MyDir", "2", "s", "s"])
    argv1 = wizard.run_wizard(reader=reader)
    assert argv1 is not None
    state_file = Path(".imgwatcher-wizard.json")
    assert state_file.exists()

    # Second run: all defaults → should pick up previous answers
    reader2 = _reader_from(["", "", "", "", "", "s"])
    argv2 = wizard.run_wizard(reader=reader2)
    assert argv2 is not None
    assert "custom-host" in argv2
    assert "/custom/dest" in argv2
    assert "MyDir" in argv2
    # Mode 2 → no --clipboard, no --sync
    assert "--clipboard" not in argv2
    assert "--sync" not in argv2
    # Dry-run was True last time → still True
    assert "--dry-run" in argv2


def test_wizard_invalid_choice_reprompts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Invalid choices "abc" and "99", then valid "2"
    reader = _reader_from(["", "", "", "abc", "99", "2", "", "s"])
    argv = wizard.run_wizard(reader=reader)
    assert argv is not None
    assert "--clipboard" not in argv
    assert "--sync" not in argv


def test_cli_empty_argv_invokes_wizard(tmp_path, monkeypatch, mocker):
    monkeypatch.chdir(tmp_path)
    from imgwatcher import cli

    run_wizard = mocker.patch("imgwatcher.cli.wizard.run_wizard")
    run_wizard.return_value = None  # cancel
    rc = cli.main([])
    run_wizard.assert_called_once()
    assert rc == 0


def test_cli_with_argv_skips_wizard(tmp_path, monkeypatch, mocker):
    monkeypatch.chdir(tmp_path)
    from imgwatcher import cli

    run_wizard = mocker.patch("imgwatcher.cli.wizard.run_wizard")
    mocker.patch("imgwatcher.cli.sync.run")
    cli.main(["--host", "h", "--dest", "/d", "--sync", "--dry-run"])
    run_wizard.assert_not_called()


def test_cli_wizard_argv_feeds_back_to_parser(tmp_path, monkeypatch, mocker):
    """Wizard returns argv → cli parses it → dispatches correctly."""
    monkeypatch.chdir(tmp_path)
    from imgwatcher import cli

    sync_run = mocker.patch("imgwatcher.cli.sync.run")
    wizard_run = mocker.patch("imgwatcher.cli.wizard.run_wizard")
    wizard_run.return_value = [
        "--host", "h",
        "--dest", "/d",
        "--watch-dir", str(tmp_path),
        "--sync",
        "--dry-run",
        "--no-banner",
    ]
    rc = cli.main([])
    sync_run.assert_called_once()
    assert rc == 0
