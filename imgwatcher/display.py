"""Terminal output: ANSI colors, banner, copy-paste-ready upload report.

Direct stderr writes (no logger) so each block lands as one atomic chunk
with consistent spacing. The remote path printed on its own line so a
triple-click selects exactly the path to paste into Claude Code.
"""

from __future__ import annotations

import os
import sys

try:
    import colorama

    colorama.just_fix_windows_console()
except ImportError:
    pass

try:
    import pyperclip

    _PYPERCLIP_OK = True
except ImportError:
    _PYPERCLIP_OK = False

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
RED = "\x1b[31m"
BRIGHT_RED = "\x1b[91m"
BRIGHT_GREEN = "\x1b[92m"
BRIGHT_YELLOW = "\x1b[93m"
CYAN = "\x1b[36m"
BRIGHT_CYAN = "\x1b[96m"
BRIGHT_WHITE = "\x1b[97m"
GRAY = "\x1b[90m"

_BANNER = r"""
  ▄████ ▓█████  ███▄    █  ██▓▓█████
 ██▒ ▀█▒▓█   ▀  ██ ▀█   █ ▓██▒▓█   ▀
▒██░▄▄▄░▒███   ▓██  ▀█ ██▒▒██▒▒███
░▓█  ██▓▒▓█  ▄ ▓██▒  ▐▌██▒░██░▒▓█  ▄
░▒▓███▀▒░▒████▒▒██░   ▓██░░██░░▒████▒
 ░▒   ▒ ░░ ▒░ ░░ ▒░   ▒ ▒ ░▓  ░░ ▒░ ░
  ░   ░  ░ ░  ░░ ░░   ░ ▒░ ▒ ░ ░ ░  ░
░ ░   ░    ░      ░   ░ ░  ▒ ░   ░
 ██▓███   ██▀███   ██▓ ███▄░   █ ▄▄▄█████▓
▓██░  ██▒▓██ ▒ ██▒▓██▒ ██ ▀█   █ ▓  ██▒ ▓▒
▓██░ ██▓▒▓██ ░▄█ ▒▒██▒▓██  ▀█ ██▒▒ ▓██░ ▒░
▒██▄█▓▒ ▒▒██▀▀█▄  ░██░▓██▒  ▐▌██▒░ ▓██▓ ░
▒██▒ ░  ░░██▓ ▒██▒░██░▒██░   ▓██░  ▒██▒ ░
▒▓▒░ ░  ░░ ▒▓ ░▒▓░░▓  ░ ▒░   ▒ ▒   ▒ ░░
░▒ ░       ░▒ ░ ▒░ ▒ ░░ ░░   ░ ▒░    ░
░░         ░░   ░  ▒ ░   ░   ░ ░   ░
            ░      ░           ░
"""

_RULE = "─" * 68

_color_enabled = True
_clipboard_enabled = True


def detect_color() -> bool:
    if os.environ.get("NO_COLOR") is not None:
        return False
    return sys.stderr.isatty()


def set_color(enabled: bool) -> None:
    global _color_enabled
    _color_enabled = enabled


def set_clipboard(enabled: bool) -> None:
    global _clipboard_enabled
    _clipboard_enabled = enabled


def copy_to_clipboard(text: str) -> bool:
    """Best-effort clipboard write. Returns True on success, False otherwise.
    Never raises — clipboard mechanisms can fail on headless systems, in CI,
    or when no clipboard daemon is running."""
    if not _clipboard_enabled or not _PYPERCLIP_OK:
        return False
    try:
        pyperclip.copy(text)
        return True
    except Exception:
        return False


def c(text: str, *codes: str) -> str:
    if not _color_enabled or not codes:
        return text
    return "".join(codes) + text + RESET


def _write(line: str = "") -> None:
    sys.stderr.write(line + "\n")
    sys.stderr.flush()


def banner() -> None:
    _write(c(_BANNER, BOLD, BRIGHT_RED))


def startup(local_dir: str, host: str, dest_dir: str, mode: str, dry_run: bool) -> None:
    badge = c(" DRY RUN ", BOLD, BRIGHT_YELLOW) if dry_run else c(" LIVE ", BOLD, BRIGHT_GREEN)
    _write()
    _write(f"   {c('Pasta local', DIM)}  {c(local_dir, CYAN)}")
    _write(f"   {c('Destino    ', DIM)}  {c(f'{host}:{dest_dir}', CYAN)}")
    _write(f"   {c('Modo       ', DIM)}  {c(mode, BRIGHT_YELLOW)}  {badge}")
    _write()
    _write(c("   " + _RULE, GRAY))


def ready_watching(folder: str) -> None:
    _write()
    _write(
        "   "
        + c("👀  Aguardando novas imagens em ", BOLD)
        + c(folder, CYAN)
    )
    _write("   " + c("(Ctrl+C para parar)", DIM))
    _write()


def clipboard_mode_active() -> None:
    _write("   " + c("📋  Clipboard ativo — Win+Shift+S, snipping tool ou qualquer copia de bitmap entra no fluxo.", BOLD, BRIGHT_CYAN))


def detected(filename: str) -> None:
    _write()
    _write("   " + c("📸  Nova imagem ", BOLD) + c(filename, BRIGHT_CYAN))


def step(emoji: str, msg: str) -> None:
    _write("       " + emoji + "  " + c(msg, GRAY))


def renamed(old_name: str, new_name: str) -> None:
    arrow = c("→", DIM)
    msg = c(old_name, GRAY) + " " + arrow + " " + c(new_name, BRIGHT_CYAN)
    _write("       " + "✏️ " + "  " + msg)


def upload_success(local_name: str, host: str, remote_path: str, dry_run: bool, size_bytes: int | None = None) -> None:
    tag = c("✅  Upload concluído", BOLD, BRIGHT_GREEN)
    if dry_run:
        tag = c("🧪  Dry-run (não enviado de verdade)", BOLD, BRIGHT_YELLOW)
    size_str = ""
    if size_bytes is not None:
        size_str = "  " + c(f"({_fmt_size(size_bytes)})", DIM)
    _write()
    _write("   " + tag)
    _write()
    _write("   " + c("Imagem:  ", DIM) + c(local_name, BRIGHT_CYAN) + size_str)
    _write("   " + c("Host:    ", DIM) + c(host, CYAN))
    paste_value = f"@{remote_path}"
    _write()
    _write("   " + c("📋  Cole no Claude Code dentro do SSH:", BOLD))
    _write()
    _write(c(paste_value, BOLD, BRIGHT_WHITE))
    _write()
    if copy_to_clipboard(paste_value):
        _write("   " + c("✨  Caminho (com @) copiado pro clipboard — só dar Ctrl+V no Claude Code!", BOLD, BRIGHT_GREEN))
        _write()
    _write(c("   " + _RULE, GRAY))


def error(msg: str) -> None:
    _write("       " + c("❌  " + msg, BOLD, BRIGHT_RED))


def warning(msg: str) -> None:
    _write("       " + c("⚠️   " + msg, BRIGHT_YELLOW))


def info(msg: str) -> None:
    _write("   " + c(msg, DIM))


def goodbye() -> None:
    _write()
    _write("   " + c("👋  Monitoramento encerrado. Até a próxima!", BOLD, BRIGHT_CYAN))
    _write()


def sync_start(count: int, host: str, dest: str) -> None:
    _write()
    _write(
        "   "
        + c("📤  Sincronizando ", BOLD)
        + c(str(count), BRIGHT_CYAN)
        + c(" imagem(ns) para ", BOLD)
        + c(f"{host}:{dest}", CYAN)
    )
    _write()


def sync_line(emoji: str, name: str, color: str = CYAN) -> None:
    _write("     " + emoji + "  " + c(name, color))


def sync_summary(uploaded_paths: list[str], skipped: int, host: str, dry_run: bool) -> None:
    _write()
    tag = c("✅  Sincronização concluída", BOLD, BRIGHT_GREEN)
    if dry_run:
        tag = c("🧪  Dry-run concluído", BOLD, BRIGHT_YELLOW)
    _write("   " + tag)
    _write(
        "   "
        + c(f"     {len(uploaded_paths)} enviada(s)", BRIGHT_GREEN)
        + "   "
        + c(f"{skipped} ignorada(s)", DIM)
    )
    if uploaded_paths:
        _write()
        _write("   " + c("📋  Caminhos no remoto (cole o que precisar, já com @):", BOLD))
        _write()
        for path in uploaded_paths:
            _write(c(f"@{path}", BRIGHT_WHITE))
        if copy_to_clipboard(f"@{uploaded_paths[-1]}"):
            _write()
            _write(
                "   "
                + c(
                    f"✨  Último caminho (@{uploaded_paths[-1].rsplit('/', 1)[-1]}) "
                    "copiado pro clipboard.",
                    BOLD,
                    BRIGHT_GREEN,
                )
            )
    _write()
    _write(c("   " + _RULE, GRAY))


def _fmt_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{size} B"
        size /= 1024
    return f"{size} B"
