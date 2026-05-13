"""Tests for clipboard watcher: detection, hash dedup, seeding, file drop."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from imgwatcher import clipboard_watcher


class FakeImage:
    """Minimal duck-typed PIL.Image stand-in."""

    def __init__(self, bytes_: bytes) -> None:
        self._bytes = bytes_

    def tobytes(self) -> bytes:
        return self._bytes

    def save(self, path, format: str | None = None) -> None:
        Path(path).write_bytes(self._bytes)


def test_is_image_true_for_pil_like():
    assert clipboard_watcher._is_image(FakeImage(b"x"))


def test_is_image_false_for_list():
    assert not clipboard_watcher._is_image(["/path/a.png"])


def test_is_image_false_for_none():
    assert not clipboard_watcher._is_image(None)


def test_is_image_false_for_string():
    assert not clipboard_watcher._is_image("hello")


def test_hash_changes_with_bytes():
    a = clipboard_watcher._hash_image(FakeImage(b"aaa"))
    b = clipboard_watcher._hash_image(FakeImage(b"bbb"))
    assert a != b


def test_save_image_writes_png(tmp_path):
    img = FakeImage(b"\x89PNG\r\n\x1a\nfake")
    target = clipboard_watcher.save_image(img, tmp_path)
    assert target is not None
    assert target.parent == tmp_path
    assert target.name.startswith("clipboard-")
    assert target.suffix == ".png"
    assert target.read_bytes() == b"\x89PNG\r\n\x1a\nfake"


def _stop_after(stop: threading.Event, n: int):
    state = {"count": 0}

    def _sleep(_secs):
        state["count"] += 1
        if state["count"] >= n:
            stop.set()

    return _sleep


def test_run_seeds_from_initial_clipboard(tmp_path, mocker):
    """If an image is already on the clipboard at startup, do not save it."""
    initial = FakeImage(b"already_there")
    grab = mocker.patch("imgwatcher.clipboard_watcher.grab")
    grab.side_effect = [initial, initial, initial]
    stop = threading.Event()
    mocker.patch("imgwatcher.clipboard_watcher.time.sleep", side_effect=_stop_after(stop, 1))
    mocker.patch("imgwatcher.clipboard_watcher.PIL_AVAILABLE", True)

    clipboard_watcher.run(tmp_path, stop_event=stop)
    assert list(tmp_path.iterdir()) == []


def test_run_detects_new_image_after_seed(tmp_path, mocker):
    grab = mocker.patch("imgwatcher.clipboard_watcher.grab")
    grab.side_effect = [
        FakeImage(b"old"),
        FakeImage(b"new-screenshot-bytes"),
        None,
    ]
    stop = threading.Event()
    mocker.patch("imgwatcher.clipboard_watcher.time.sleep", side_effect=_stop_after(stop, 2))
    mocker.patch("imgwatcher.clipboard_watcher.PIL_AVAILABLE", True)

    clipboard_watcher.run(tmp_path, stop_event=stop)
    files = list(tmp_path.iterdir())
    assert len(files) == 1
    assert files[0].read_bytes() == b"new-screenshot-bytes"


def test_run_dedups_repeated_image(tmp_path, mocker):
    """Same image bytes seen N times → saved once."""
    img = FakeImage(b"same-bytes")
    grab = mocker.patch("imgwatcher.clipboard_watcher.grab")
    grab.side_effect = [None, img, img, img]
    stop = threading.Event()
    mocker.patch("imgwatcher.clipboard_watcher.time.sleep", side_effect=_stop_after(stop, 3))
    mocker.patch("imgwatcher.clipboard_watcher.PIL_AVAILABLE", True)

    clipboard_watcher.run(tmp_path, stop_event=stop)
    assert len(list(tmp_path.iterdir())) == 1


def test_run_ignores_file_lists(tmp_path, mocker):
    """When user copies file paths in Explorer, grabclipboard returns a list."""
    grab = mocker.patch("imgwatcher.clipboard_watcher.grab")
    grab.side_effect = [None, ["/some/file.png", "/another.png"], None]
    stop = threading.Event()
    mocker.patch("imgwatcher.clipboard_watcher.time.sleep", side_effect=_stop_after(stop, 2))
    mocker.patch("imgwatcher.clipboard_watcher.PIL_AVAILABLE", True)

    clipboard_watcher.run(tmp_path, stop_event=stop)
    assert list(tmp_path.iterdir()) == []


def test_run_ignores_none(tmp_path, mocker):
    grab = mocker.patch("imgwatcher.clipboard_watcher.grab")
    grab.side_effect = [None, None, None]
    stop = threading.Event()
    mocker.patch("imgwatcher.clipboard_watcher.time.sleep", side_effect=_stop_after(stop, 2))
    mocker.patch("imgwatcher.clipboard_watcher.PIL_AVAILABLE", True)

    clipboard_watcher.run(tmp_path, stop_event=stop)
    assert list(tmp_path.iterdir()) == []


def test_run_warns_when_pillow_missing(tmp_path, mocker):
    mocker.patch("imgwatcher.clipboard_watcher.PIL_AVAILABLE", False)
    warning = mocker.patch("imgwatcher.clipboard_watcher.display.warning")
    clipboard_watcher.run(tmp_path)
    warning.assert_called_once()


def test_cli_clipboard_flag_starts_thread(tmp_path, mocker):
    from imgwatcher import cli

    mocker.patch("imgwatcher.cli.watcher.WATCHDOG_AVAILABLE", True)
    mocker.patch("imgwatcher.cli.watcher.run_watchdog")
    thread_cls = mocker.patch("imgwatcher.cli.threading.Thread")

    cli.main(
        [
            "--host", "h",
            "--dest", "/d",
            "--watch-dir", str(tmp_path),
            "--dry-run",
            "--clipboard",
        ]
    )
    thread_cls.assert_called_once()
    _, kwargs = thread_cls.call_args
    assert kwargs["target"] is clipboard_watcher.run
    assert kwargs["daemon"] is True


def test_cli_no_clipboard_flag_no_thread(tmp_path, mocker):
    from imgwatcher import cli

    mocker.patch("imgwatcher.cli.watcher.WATCHDOG_AVAILABLE", True)
    mocker.patch("imgwatcher.cli.watcher.run_watchdog")
    thread_cls = mocker.patch("imgwatcher.cli.threading.Thread")

    cli.main(
        ["--host", "h", "--dest", "/d", "--watch-dir", str(tmp_path), "--dry-run"]
    )
    thread_cls.assert_not_called()


def test_cli_clipboard_ignored_in_sync_mode(tmp_path, mocker):
    from imgwatcher import cli

    mocker.patch("imgwatcher.cli.sync.run")
    thread_cls = mocker.patch("imgwatcher.cli.threading.Thread")

    cli.main(
        [
            "--host", "h",
            "--dest", "/d",
            "--watch-dir", str(tmp_path),
            "--sync",
            "--clipboard",
            "--dry-run",
        ]
    )
    thread_cls.assert_not_called()
