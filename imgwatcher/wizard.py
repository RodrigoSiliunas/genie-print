"""Interactive setup wizard.

Triggered when `image_watcher.py` is invoked with no CLI args. Asks the user
a small set of questions (with sensible defaults remembered from the
previous run), builds an argv-style list, and hands it to `cli.main` so
every existing flag, log, and path is reused. Persists answers to
`.imgwatcher-wizard.json` in the current directory.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable, Optional

from . import display

STATE_FILE = Path(".imgwatcher-wizard.json")

DEFAULT_HOST = "myserver"
DEFAULT_DEST = "/path/to/remote/screenshots"
DEFAULT_WATCH_DIR = "Images"

MODE_OPTIONS = [
    (
        "Watcher completo",
        "monitora clipboard (Win+Shift+S) + pasta local — recomendado",
        ["--clipboard"],
    ),
    (
        "Watcher só pasta",
        "monitora só a pasta local (Lightshot, prints salvos manualmente)",
        [],
    ),
    (
        "Sync único",
        "envia tudo o que ja esta na pasta e sai",
        ["--sync"],
    ),
]


def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(state: dict) -> None:
    try:
        STATE_FILE.write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass


def _write(line: str = "") -> None:
    sys.stderr.write(line + "\n")
    sys.stderr.flush()


def _ask(reader: Callable[[str], str], question: str, default: str = "") -> str:
    suffix = ""
    if default:
        suffix = " " + display.c(f"[{default}]", display.DIM)
    prompt = (
        "   "
        + display.c(question, display.BOLD)
        + suffix
        + display.c(" › ", display.DIM)
    )
    sys.stderr.write(prompt)
    sys.stderr.flush()
    response = reader("").strip()
    return response if response else default


def _yesno(reader: Callable[[str], str], question: str, default: bool = False) -> bool:
    label = "S/n" if default else "s/N"
    raw = _ask(reader, question, label).strip().lower()
    if raw == label.lower():
        return default
    return raw in ("s", "sim", "y", "yes")


def _choice(
    reader: Callable[[str], str],
    question: str,
    options: list[tuple[str, str, list[str]]],
    default_index: int = 0,
) -> int:
    _write()
    _write("   " + display.c(question, display.BOLD))
    for i, (label, desc, _flags) in enumerate(options, start=1):
        marker = display.c("●", display.BRIGHT_CYAN) if i - 1 == default_index else " "
        _write(
            f"     {marker} "
            + display.c(f"[{i}]", display.BOLD)
            + " "
            + display.c(label, display.CYAN)
            + " — "
            + display.c(desc, display.DIM)
        )
    while True:
        raw = _ask(reader, "Sua escolha", str(default_index + 1)).strip()
        try:
            n = int(raw)
            if 1 <= n <= len(options):
                return n - 1
        except ValueError:
            pass
        _write(
            display.c(
                f"   Escolha um numero entre 1 e {len(options)}.",
                display.BRIGHT_RED,
            )
        )


def run_wizard(reader: Optional[Callable[[str], str]] = None) -> Optional[list[str]]:
    """Returns argv-style list of args, or None if user cancelled."""
    reader = reader or input
    display.set_color(display.detect_color())

    try:
        return _run_wizard_inner(reader)
    except (KeyboardInterrupt, EOFError):
        _write()
        _write(display.c("   Cancelado.", display.BRIGHT_RED))
        return None


def _run_wizard_inner(reader: Callable[[str], str]) -> Optional[list[str]]:
    state = _load_state()

    display.banner()
    _write(
        "   "
        + display.c("Bem-vindo ao Genie Print!", display.BOLD, display.BRIGHT_CYAN)
    )
    _write(display.c("   Vamos configurar em 4 passos.", display.DIM))
    _write()

    host = _ask(reader, "Host SSH (alias em ~/.ssh/config)", state.get("host", DEFAULT_HOST))
    dest = _ask(reader, "Pasta de destino no remoto", state.get("dest", DEFAULT_DEST))
    watch_dir = _ask(
        reader, "Pasta local pra monitorar", state.get("watch_dir", DEFAULT_WATCH_DIR)
    )
    mode_idx = _choice(
        reader, "Como rodar?", MODE_OPTIONS, default_index=state.get("mode", 0)
    )
    dry_run = _yesno(
        reader, "Dry-run? (nao envia de verdade)", default=state.get("dry_run", False)
    )

    argv: list[str] = [
        "--host", host,
        "--dest", dest,
        "--watch-dir", watch_dir,
        "--no-banner",  # banner already shown by the wizard
    ]
    argv.extend(MODE_OPTIONS[mode_idx][2])
    if dry_run:
        argv.append("--dry-run")

    _write()
    _write("   " + display.c("Resumo:", display.BOLD))
    _write(f"     Host       {display.c(host, display.CYAN)}")
    _write(f"     Destino    {display.c(dest, display.CYAN)}")
    _write(f"     Pasta      {display.c(watch_dir, display.CYAN)}")
    _write(
        f"     Modo       {display.c(MODE_OPTIONS[mode_idx][0], display.BRIGHT_YELLOW)}"
    )
    dry_label = "SIM" if dry_run else "NAO"
    dry_color = display.BRIGHT_YELLOW if dry_run else display.GRAY
    _write(f"     Dry-run    {display.c(dry_label, dry_color)}")
    _write()

    if not _yesno(reader, "Confirmar e iniciar?", default=True):
        _write()
        _write(display.c("   Cancelado.", display.BRIGHT_RED))
        return None

    _save_state(
        {
            "host": host,
            "dest": dest,
            "watch_dir": watch_dir,
            "mode": mode_idx,
            "dry_run": dry_run,
        }
    )

    _write()
    return argv
