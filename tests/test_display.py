"""Tests for the display module: clipboard side-effect + flags."""

from __future__ import annotations

import pytest

from imgwatcher import display


def test_set_color_disabled_returns_raw():
    display.set_color(False)
    try:
        assert display.c("hello", display.BRIGHT_RED) == "hello"
    finally:
        display.set_color(True)


def test_set_color_enabled_wraps_ansi():
    display.set_color(True)
    out = display.c("hello", display.BRIGHT_RED)
    assert out.startswith(display.BRIGHT_RED)
    assert out.endswith(display.RESET)


def test_copy_to_clipboard_disabled_returns_false(mocker):
    fake = mocker.patch("imgwatcher.display.pyperclip", create=True)
    display.set_clipboard(False)
    try:
        assert display.copy_to_clipboard("hi") is False
        fake.copy.assert_not_called()
    finally:
        display.set_clipboard(True)


def test_copy_to_clipboard_enabled_calls_pyperclip(mocker):
    fake = mocker.patch("imgwatcher.display.pyperclip", create=True)
    mocker.patch("imgwatcher.display._PYPERCLIP_OK", True)
    display.set_clipboard(True)
    assert display.copy_to_clipboard("hi") is True
    fake.copy.assert_called_once_with("hi")


def test_copy_to_clipboard_swallows_exceptions(mocker):
    fake = mocker.patch("imgwatcher.display.pyperclip", create=True)
    fake.copy.side_effect = RuntimeError("no clipboard daemon")
    mocker.patch("imgwatcher.display._PYPERCLIP_OK", True)
    display.set_clipboard(True)
    assert display.copy_to_clipboard("hi") is False


def test_copy_to_clipboard_returns_false_when_pyperclip_missing(mocker):
    mocker.patch("imgwatcher.display._PYPERCLIP_OK", False)
    display.set_clipboard(True)
    assert display.copy_to_clipboard("hi") is False


def test_upload_success_clipboard_gets_at_prefix(mocker):
    fake = mocker.patch("imgwatcher.display.pyperclip", create=True)
    mocker.patch("imgwatcher.display._PYPERCLIP_OK", True)
    display.set_clipboard(True)
    display.upload_success(
        local_name="Image #4.png",
        host="myserver",
        remote_path="/root/foo/Image #4.png",
        dry_run=False,
        size_bytes=1024,
    )
    fake.copy.assert_called_once_with("@/root/foo/Image #4.png")


def test_sync_summary_clipboard_gets_at_prefix(mocker):
    fake = mocker.patch("imgwatcher.display.pyperclip", create=True)
    mocker.patch("imgwatcher.display._PYPERCLIP_OK", True)
    display.set_clipboard(True)
    paths = ["/root/foo/a.png", "/root/foo/b.png"]
    display.sync_summary(paths, skipped=0, host="myserver", dry_run=False)
    fake.copy.assert_called_once_with("@/root/foo/b.png")


def test_cli_no_clipboard_disables_it(tmp_path, mocker):
    from imgwatcher import cli

    set_clipboard = mocker.patch("imgwatcher.cli.display.set_clipboard")
    mocker.patch("imgwatcher.cli.sync.run")
    cli.main(
        [
            "--host", "h",
            "--dest", "/d",
            "--watch-dir", str(tmp_path),
            "--sync", "--dry-run", "--no-clipboard",
        ]
    )
    set_clipboard.assert_called_once_with(False)


def test_cli_default_enables_clipboard(tmp_path, mocker):
    from imgwatcher import cli

    set_clipboard = mocker.patch("imgwatcher.cli.display.set_clipboard")
    mocker.patch("imgwatcher.cli.sync.run")
    cli.main(
        [
            "--host", "h",
            "--dest", "/d",
            "--watch-dir", str(tmp_path),
            "--sync", "--dry-run",
        ]
    )
    set_clipboard.assert_called_once_with(True)
