"""Poll the OS clipboard for bitmap images and drop them into the watch dir.

The folder watcher then picks them up via its normal on_created path, so the
clipboard mode reuses the full rename + upload + spotlight pipeline without
any duplication. Designed to run in a daemon thread alongside the folder
watcher.

Pillow's ImageGrab.grabclipboard() returns:
  - PIL.Image.Image  → a bitmap was on the clipboard (Win+Shift+S, etc.)
  - list[str]        → file paths were copied in Explorer (we ignore)
  - None             → no image content
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from pathlib import Path
from typing import Any, Optional

from . import display

log = logging.getLogger(__name__)

try:
    from PIL import ImageGrab

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

CLIPBOARD_POLL_INTERVAL_S = 0.5


def _is_image(content: Any) -> bool:
    return hasattr(content, "tobytes") and hasattr(content, "save")


def _hash_image(img: Any) -> str:
    try:
        return hashlib.md5(img.tobytes()).hexdigest()
    except Exception:
        return ""


def grab() -> Optional[Any]:
    """Wrapper around ImageGrab.grabclipboard. Patchable in tests."""
    if not PIL_AVAILABLE:
        return None
    try:
        return ImageGrab.grabclipboard()
    except Exception as exc:
        log.debug("grabclipboard failed: %s", exc)
        return None


def save_image(img: Any, watch_dir: Path) -> Optional[Path]:
    ts = int(time.time() * 1000)
    target = Path(watch_dir) / f"clipboard-{ts}.png"
    try:
        img.save(target, format="PNG")
        return target
    except OSError as exc:
        log.debug("clipboard image save failed: %s", exc)
        return None


def run(watch_dir: Path, stop_event: Optional[threading.Event] = None) -> None:
    """Polling loop. Seeds last_hash with the current clipboard to avoid
    auto-uploading something the user copied before starting the watcher."""
    if not PIL_AVAILABLE:
        display.warning("Pillow nao instalado; --clipboard inativo. pip install Pillow")
        return

    last_hash: Optional[str] = None
    initial = grab()
    if _is_image(initial):
        last_hash = _hash_image(initial)

    while True:
        if stop_event is not None and stop_event.is_set():
            return
        content = grab()
        if _is_image(content):
            h = _hash_image(content)
            if h and h != last_hash:
                last_hash = h
                save_image(content, watch_dir)
        time.sleep(CLIPBOARD_POLL_INTERVAL_S)
