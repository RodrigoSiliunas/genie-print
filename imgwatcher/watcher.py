"""Folder watchers: watchdog event-based or polling fallback.

Both implementations share an ImageProcessor instance so all numbering,
renaming, and upload logic lives in exactly one place.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from . import display
from .config import POLLING_INTERVAL_S
from .processor import ImageProcessor, is_image

log = logging.getLogger(__name__)

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    FileSystemEventHandler = object


class _Handler(FileSystemEventHandler):
    def __init__(self, processor: ImageProcessor) -> None:
        self.processor = processor

    def on_created(self, event) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if not is_image(path):
            return
        self.processor.process(path)


def run_watchdog(processor: ImageProcessor) -> None:
    if not WATCHDOG_AVAILABLE:
        raise RuntimeError("watchdog nao disponivel")
    handler = _Handler(processor)
    observer = Observer()
    observer.schedule(handler, str(processor.watch_dir), recursive=False)
    observer.start()
    display.ready_watching(str(processor.watch_dir))
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()
        display.goodbye()


def run_polling(processor: ImageProcessor) -> None:
    display.ready_watching(str(processor.watch_dir))
    display.info(f"(modo polling, {POLLING_INTERVAL_S:.0f}s)")
    known: set[str] = {
        str(p) for p in processor.watch_dir.iterdir() if p.is_file() and is_image(p)
    }
    try:
        while True:
            current = {
                str(p)
                for p in processor.watch_dir.iterdir()
                if p.is_file() and is_image(p)
            }
            for new_path in current - known:
                processor.process(Path(new_path))
            known = {
                str(p)
                for p in processor.watch_dir.iterdir()
                if p.is_file() and is_image(p)
            }
            time.sleep(POLLING_INTERVAL_S)
    except KeyboardInterrupt:
        display.goodbye()
