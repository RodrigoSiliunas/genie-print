"""One-shot bulk uploader with interactive conflict resolution."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Callable, Optional

from . import display
from .config import IMAGE_EXTENSIONS, SCP_TIMEOUT_SECONDS
from .transport import SCPTransport

log = logging.getLogger(__name__)

ACTION_OVERWRITE = "overwrite"
ACTION_SKIP = "skip"
ACTION_OVERWRITE_ALL = "overwrite_all"
ACTION_SKIP_ALL = "skip_all"
ACTION_ABORT = "abort"

_PROMPT = (
    "  {name} ja existe em {dest}. "
    "[S]obrescrever, [I]gnorar, [T]odos, [N]enhum, [A]bortar: "
)


def ask_user_action(
    file_name: str, dest_path: str, reader: Callable[[str], str] = input
) -> str:
    while True:
        response = reader(_PROMPT.format(name=file_name, dest=dest_path)).strip().lower()
        if response in ("s", "sobrescrever"):
            return ACTION_OVERWRITE
        if response in ("i", "ignorar"):
            return ACTION_SKIP
        if response in ("t", "todos"):
            return ACTION_OVERWRITE_ALL
        if response in ("n", "nenhum"):
            return ACTION_SKIP_ALL
        if response in ("a", "abortar"):
            return ACTION_ABORT
        print("  Opcao invalida. Tente novamente.")


def _list_images(watch_dir: Path) -> list[Path]:
    return sorted(
        p
        for p in watch_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )


def run(
    watch_dir: Path,
    transport: SCPTransport,
    reader: Callable[[str], str] = input,
) -> None:
    """Synchronize all images from watch_dir to the remote dest_dir."""
    watch_dir = Path(watch_dir).resolve()
    files = _list_images(watch_dir)
    if not files:
        display.info("Nenhuma imagem encontrada na pasta.")
        return

    display.sync_start(len(files), transport.host, transport.dest_dir)

    remote_names = transport.list_remote() if not transport.dry_run else set()
    dest_label = f"{transport.host}:{transport.dest_dir}"

    global_action: Optional[str] = None
    uploaded_paths: list[str] = []
    skipped = 0

    for path in files:
        action: Optional[str] = None
        if path.name in remote_names:
            if global_action == ACTION_OVERWRITE_ALL:
                action = ACTION_OVERWRITE
            elif global_action == ACTION_SKIP_ALL:
                action = ACTION_SKIP
            else:
                action = ask_user_action(path.name, dest_label, reader)
                if action == ACTION_OVERWRITE_ALL:
                    global_action = ACTION_OVERWRITE_ALL
                    action = ACTION_OVERWRITE
                elif action == ACTION_SKIP_ALL:
                    global_action = ACTION_SKIP_ALL
                    action = ACTION_SKIP

        if action == ACTION_ABORT:
            display.warning("Sincronizacao abortada pelo usuario.")
            break
        if action == ACTION_SKIP:
            skipped += 1
            display.sync_line("⏭️ ", f"{path.name} (ignorado)", color=display.GRAY)
            continue

        if _upload_one(path, transport):
            uploaded_paths.append(f"{transport.dest_dir}/{path.name}")
            display.sync_line("✅", path.name, color=display.BRIGHT_CYAN)
        else:
            display.sync_line("❌", path.name, color=display.BRIGHT_RED)

    display.sync_summary(uploaded_paths, skipped, transport.host, transport.dry_run)


def _upload_one(path: Path, transport: SCPTransport) -> bool:
    """Used by sync.run; calls transport.upload but logs at sync's indent style."""
    if transport.dry_run:
        return True
    try:
        result = subprocess.run(
            ["scp", str(path), f"{transport.host}:{transport.dest_dir}"],
            capture_output=True,
            text=True,
            timeout=SCP_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        log.debug("scp timeout for %s", path.name)
        return False
    except OSError as exc:
        log.debug("scp os error for %s: %s", path.name, exc)
        return False
    if result.returncode == 0:
        return True
    log.debug("scp non-zero for %s: %s", path.name, result.stderr.strip())
    return False
