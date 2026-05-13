"""Idempotent upload of AGENTS.md to the remote drop folder.

`AGENTS.md` is a convention picked up by AI coding agents (Claude Code,
Cursor, etc.) for in-folder context. By dropping one in the screenshot
destination on the remote, the agent that the user is talking to over
SSH gets a description of what this folder is for and how images arrive.

The upload is idempotent: if `AGENTS.md` already exists in the remote
directory, we do not touch it. Users who customize the remote copy keep
their version forever.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from . import display
from .transport import SCPTransport

log = logging.getLogger(__name__)

REMOTE_FILENAME = "AGENTS.md"
TEMPLATE_PATH = Path(__file__).parent / "agents_md_template.md"


def load_content() -> str:
    """Read the bundled template. Cached implicitly by the filesystem."""
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def ensure_uploaded(transport: SCPTransport) -> None:
    """Send AGENTS.md to ``transport.dest_dir`` only if absent.

    Never raises. Failures (e.g. cannot list remote, scp errors) are
    logged at DEBUG and swallowed — Genie Print's primary purpose is
    image uploads, and this is best-effort context for the remote agent.
    """
    if transport.dry_run:
        display.info(f"📄 [DRY RUN] checaria/enviaria {REMOTE_FILENAME} pro remoto")
        return

    try:
        remote_files = transport.list_remote()
    except Exception as exc:
        log.debug("list_remote falhou: %s", exc)
        display.info("📄 Nao foi possivel checar o remoto; pulando envio do AGENTS.md.")
        return

    if REMOTE_FILENAME in remote_files:
        display.info(f"📄 {REMOTE_FILENAME} ja presente no remoto, mantendo.")
        return

    try:
        content = load_content()
    except OSError as exc:
        log.debug("template missing: %s", exc)
        return

    with tempfile.TemporaryDirectory() as td:
        staged = Path(td) / REMOTE_FILENAME
        staged.write_text(content, encoding="utf-8")
        if transport.upload(staged):
            display.info(f"📄 {REMOTE_FILENAME} enviado com contexto pro agente remoto.")
        else:
            display.info(f"📄 Falha ao enviar {REMOTE_FILENAME}; segue sem ele.")
