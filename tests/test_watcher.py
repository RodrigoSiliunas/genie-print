"""Tests for watcher modes."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from imgwatcher import watcher
from imgwatcher.processor import ImageProcessor


def test_polling_detects_new_file(watch_dir, fake_transport, make_image_factory, monkeypatch):
    monkeypatch.setattr(watcher, "POLLING_INTERVAL_S", 0.1)
    proc = ImageProcessor(watch_dir, fake_transport)
    stop_event = threading.Event()

    def stop_after_one_cycle():
        # Drop a file, then wait briefly for the watcher to pick it up.
        time.sleep(0.05)
        make_image_factory("dropped.png", b"abc")
        time.sleep(0.6)
        stop_event.set()

    def patched_run_polling(proc):
        log = watcher.log
        log.info("test polling start")
        known = {str(p) for p in proc.watch_dir.iterdir() if p.is_file()}
        while not stop_event.is_set():
            current = {str(p) for p in proc.watch_dir.iterdir() if p.is_file()}
            for new_path in current - known:
                proc.process(Path(new_path))
            known = {str(p) for p in proc.watch_dir.iterdir() if p.is_file()}
            time.sleep(0.1)

    threading.Thread(target=stop_after_one_cycle, daemon=True).start()
    patched_run_polling(proc)
    assert "Image #1.png" in fake_transport.uploaded


def test_handler_calls_process_for_image(watch_dir, fake_transport, make_image_factory):
    if not watcher.WATCHDOG_AVAILABLE:
        pytest.skip("watchdog not installed")
    proc = ImageProcessor(watch_dir, fake_transport)
    handler = watcher._Handler(proc)
    src = make_image_factory("foo.png", b"abc")

    class FakeEvent:
        def __init__(self, path, is_dir=False):
            self.src_path = str(path)
            self.is_directory = is_dir

    handler.on_created(FakeEvent(src))
    assert fake_transport.uploaded == ["Image #1.png"]


def test_handler_ignores_directories(watch_dir, fake_transport):
    if not watcher.WATCHDOG_AVAILABLE:
        pytest.skip("watchdog not installed")
    proc = ImageProcessor(watch_dir, fake_transport)
    handler = watcher._Handler(proc)

    class FakeEvent:
        src_path = str(watch_dir / "subdir")
        is_directory = True

    handler.on_created(FakeEvent())
    assert fake_transport.uploaded == []


def test_handler_ignores_non_image(watch_dir, fake_transport, make_image_factory):
    if not watcher.WATCHDOG_AVAILABLE:
        pytest.skip("watchdog not installed")
    proc = ImageProcessor(watch_dir, fake_transport)
    handler = watcher._Handler(proc)
    src = make_image_factory("notes.txt", b"hi")

    class FakeEvent:
        def __init__(self, path):
            self.src_path = str(path)
            self.is_directory = False

    handler.on_created(FakeEvent(src))
    assert fake_transport.uploaded == []
