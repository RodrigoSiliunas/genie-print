"""CLI entry point: parse args, configure logging, dispatch to watcher or sync."""

from __future__ import annotations

import argparse
import logging
import sys
import threading
from pathlib import Path
from typing import Optional, Sequence

from . import agents_md, clipboard_watcher, display, logging_setup, sync, watcher, wizard
from .config import DEFAULT_WATCH_DIR
from .processor import ImageProcessor
from .transport import SCPTransport

log = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Worker para monitorar e sincronizar imagens via SCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python image_watcher.py --host myserver --dest /remote/path/screenshots
  python image_watcher.py --host myserver --dest /remote/path --sync
  python image_watcher.py --host myserver --dest /remote/path --dry-run
        """,
    )
    parser.add_argument("--host", required=True, help="Host SSH (alias em ~/.ssh/config)")
    parser.add_argument("--dest", required=True, help="Caminho de destino no remoto")
    parser.add_argument(
        "--watch-dir",
        default=DEFAULT_WATCH_DIR,
        help=f"Pasta local (padrao: {DEFAULT_WATCH_DIR})",
    )
    parser.add_argument("--sync", action="store_true", help="Envia tudo e sai")
    parser.add_argument("--dry-run", action="store_true", help="Nao executa SCP/SSH")
    parser.add_argument("--verbose", action="store_true", help="Log em nivel DEBUG")
    parser.add_argument("--no-color", action="store_true", help="Desliga cores ANSI")
    parser.add_argument("--no-banner", action="store_true", help="Nao imprime o banner")
    parser.add_argument(
        "--no-clipboard",
        action="store_true",
        help="Nao copia o caminho remoto pro clipboard ao terminar o upload",
    )
    parser.add_argument(
        "--clipboard",
        action="store_true",
        help="Tambem monitora o clipboard do SO (Win+Shift+S, snipping tool, etc.)",
    )
    parser.add_argument(
        "--no-agents-md",
        action="store_true",
        help="Nao envia o AGENTS.md de contexto pra pasta remota",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    actual_argv = list(sys.argv[1:] if argv is None else argv)
    if not actual_argv:
        wizard_argv = wizard.run_wizard()
        if wizard_argv is None:
            return 0
        actual_argv = wizard_argv

    args = build_parser().parse_args(actual_argv)
    logging_setup.configure(verbose=args.verbose)

    display.set_color(False if args.no_color else display.detect_color())
    display.set_clipboard(not args.no_clipboard)

    watch_dir = Path(args.watch_dir)
    if not watch_dir.exists():
        watch_dir.mkdir(parents=True, exist_ok=True)

    if not args.no_banner:
        display.banner()
    mode_label = "Sync (one-shot)" if args.sync else (
        "Watcher (watchdog)" if watcher.WATCHDOG_AVAILABLE else "Watcher (polling)"
    )
    clipboard_active = args.clipboard and not args.sync
    if clipboard_active:
        mode_label += " + Clipboard"
    display.startup(
        local_dir=str(watch_dir.resolve()),
        host=args.host,
        dest_dir=args.dest,
        mode=mode_label,
        dry_run=args.dry_run,
    )

    transport = SCPTransport(host=args.host, dest_dir=args.dest, dry_run=args.dry_run)

    if not args.no_agents_md:
        agents_md.ensure_uploaded(transport)

    if args.sync:
        sync.run(watch_dir, transport)
        return 0

    processor = ImageProcessor(watch_dir, transport)

    clipboard_stop: Optional[threading.Event] = None
    clipboard_thread: Optional[threading.Thread] = None
    if clipboard_active:
        display.clipboard_mode_active()
        clipboard_stop = threading.Event()
        clipboard_thread = threading.Thread(
            target=clipboard_watcher.run,
            args=(watch_dir, clipboard_stop),
            daemon=True,
        )
        clipboard_thread.start()

    try:
        if watcher.WATCHDOG_AVAILABLE:
            watcher.run_watchdog(processor)
        else:
            display.warning(
                "Biblioteca watchdog ausente; usando polling. Instale com: pip install watchdog"
            )
            watcher.run_polling(processor)
    finally:
        if clipboard_stop is not None:
            clipboard_stop.set()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
