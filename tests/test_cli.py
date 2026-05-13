"""Tests for CLI: arg parsing + dispatch."""

from __future__ import annotations

from pathlib import Path

import pytest

from imgwatcher import cli


def test_missing_required_args(capsys):
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args([])


def test_sync_dispatches_to_sync_run(tmp_path: Path, mocker):
    sync_run = mocker.patch("imgwatcher.cli.sync.run")
    run_watchdog = mocker.patch("imgwatcher.cli.watcher.run_watchdog")
    run_polling = mocker.patch("imgwatcher.cli.watcher.run_polling")
    cli.main(
        [
            "--host",
            "h",
            "--dest",
            "/d",
            "--watch-dir",
            str(tmp_path),
            "--sync",
            "--dry-run",
        ]
    )
    sync_run.assert_called_once()
    run_watchdog.assert_not_called()
    run_polling.assert_not_called()


def test_watcher_mode_picks_watchdog_when_available(tmp_path: Path, mocker):
    sync_run = mocker.patch("imgwatcher.cli.sync.run")
    run_watchdog = mocker.patch("imgwatcher.cli.watcher.run_watchdog")
    run_polling = mocker.patch("imgwatcher.cli.watcher.run_polling")
    mocker.patch("imgwatcher.cli.watcher.WATCHDOG_AVAILABLE", True)
    cli.main(["--host", "h", "--dest", "/d", "--watch-dir", str(tmp_path), "--dry-run"])
    sync_run.assert_not_called()
    run_watchdog.assert_called_once()
    run_polling.assert_not_called()


def test_watcher_mode_falls_back_to_polling(tmp_path: Path, mocker):
    sync_run = mocker.patch("imgwatcher.cli.sync.run")
    run_watchdog = mocker.patch("imgwatcher.cli.watcher.run_watchdog")
    run_polling = mocker.patch("imgwatcher.cli.watcher.run_polling")
    mocker.patch("imgwatcher.cli.watcher.WATCHDOG_AVAILABLE", False)
    cli.main(["--host", "h", "--dest", "/d", "--watch-dir", str(tmp_path), "--dry-run"])
    run_polling.assert_called_once()
    run_watchdog.assert_not_called()


def test_creates_watch_dir_if_missing(tmp_path: Path, mocker):
    mocker.patch("imgwatcher.cli.sync.run")
    target = tmp_path / "new-images"
    assert not target.exists()
    cli.main(
        ["--host", "h", "--dest", "/d", "--watch-dir", str(target), "--sync", "--dry-run"]
    )
    assert target.exists()
