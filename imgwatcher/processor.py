"""Single source of truth for: numbering, renaming, stability detection.

A processor instance is shared by every watcher mode so the rename rules,
the file-stability wait, and the cross-thread numbering lock all live in
exactly one place.
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Optional

from . import display
from .config import (
    IMAGE_EXTENSIONS,
    NAME_PATTERN,
    NAME_TEMPLATE,
    STABILITY_MAX_WAIT_S,
    STABILITY_POLL_INTERVAL_S,
)
from .transport import SCPTransport

log = logging.getLogger(__name__)


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTENSIONS


def wait_for_stable(
    path: Path,
    poll_s: float = STABILITY_POLL_INTERVAL_S,
    max_wait_s: float = STABILITY_MAX_WAIT_S,
) -> bool:
    """Wait until two consecutive size reads match. Returns False on timeout
    or if the file disappears mid-wait."""
    deadline = time.monotonic() + max_wait_s
    previous: Optional[int] = None
    while time.monotonic() < deadline:
        try:
            current = path.stat().st_size
        except FileNotFoundError:
            return False
        if previous is not None and current == previous:
            return True
        previous = current
        time.sleep(poll_s)
    return False


class ImageProcessor:
    """Owns the watch directory: numbering, renaming, dispatching to transport."""

    def __init__(self, watch_dir: Path, transport: SCPTransport) -> None:
        self.watch_dir = Path(watch_dir).resolve()
        self.transport = transport
        self._lock = threading.Lock()

    def next_number(self) -> int:
        """Smallest N such that no file in watch_dir matches Image #N."""
        max_n = 0
        for entry in self.watch_dir.iterdir():
            if not entry.is_file():
                continue
            match = NAME_PATTERN.search(entry.stem)
            if match:
                n = int(match.group(1))
                if n > max_n:
                    max_n = n
        return max_n + 1

    def rename(self, src: Path) -> Optional[Path]:
        """Rename src to Image #N.<ext> unless it already matches the pattern.
        Returns the post-rename path (or original if no rename needed), or
        None on error/missing file."""
        src = Path(src)
        with self._lock:
            if not src.exists():
                return None
            if NAME_PATTERN.match(src.stem):
                return src
            n = self.next_number()
            target = self.watch_dir / NAME_TEMPLATE.format(n=n, ext=src.suffix)
            try:
                src.rename(target)
            except OSError as exc:
                log.debug("rename failed: %s -> %s: %s", src, target, exc)
                return None
            return target

    def process(self, src: Path) -> bool:
        """Full pipeline: wait silently for the file to stabilize, then announce
        + rename + upload + spotlight remote path. Transient events (snipping
        tools that briefly create and replace files) produce no output."""
        src = Path(src)
        if not is_image(src):
            return False
        if not src.exists():
            return False

        if not wait_for_stable(src):
            if src.exists():
                display.detected(src.name)
                display.warning("Arquivo nao estabilizou em 5s, pulando.")
            return False

        display.detected(src.name)
        original_name = src.name
        renamed = self.rename(src)
        if renamed is None:
            display.error(f"Falha ao renomear {original_name}")
            return False
        if renamed.name != original_name:
            display.renamed(original_name, renamed.name)

        display.step("⬆️ ", f"Enviando para {self.transport.host}...")
        ok = self.transport.upload(renamed)
        if not ok:
            display.error(f"Upload falhou: {renamed.name}")
            return False

        remote_path = f"{self.transport.dest_dir}/{renamed.name}"
        try:
            size = renamed.stat().st_size
        except OSError:
            size = None
        display.upload_success(
            local_name=renamed.name,
            host=self.transport.host,
            remote_path=remote_path,
            dry_run=self.transport.dry_run,
            size_bytes=size,
        )
        return True
