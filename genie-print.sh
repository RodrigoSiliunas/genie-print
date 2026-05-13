#!/usr/bin/env bash
# Genie Print launcher (Linux / macOS / Git Bash).
# Configura o venv na primeira execucao e em seguida abre o wizard.
# Qualquer argumento passado e repassado pro image_watcher.py
# (ex: ./genie.sh --sync --dry-run).

set -euo pipefail

# Resolve o diretorio do proprio script, mesmo via link simbolico.
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"

VENV_PY=".venv/bin/python"

if [[ ! -x "$VENV_PY" ]]; then
    echo
    echo "=== Configurando ambiente pela primeira vez ==="
    echo
    if command -v uv >/dev/null 2>&1; then
        uv venv --python 3.13 .venv
        uv pip install -r requirements.txt
    elif command -v python3 >/dev/null 2>&1; then
        python3 -m venv .venv
        "$VENV_PY" -m pip install --upgrade pip >/dev/null
        "$VENV_PY" -m pip install -r requirements.txt
    else
        echo "Erro: nem 'uv' nem 'python3' encontrados no PATH." >&2
        echo "Instale o uv (recomendado) ou Python 3.11+ e tente de novo." >&2
        exit 1
    fi
fi

# Aviso opcional em Linux: clipboard precisa de helper externo + display.
if [[ "$(uname -s)" == "Linux" ]]; then
    has_helper=0
    for tool in xclip xsel wl-paste; do
        if command -v "$tool" >/dev/null 2>&1; then has_helper=1; break; fi
    done
    if [[ $has_helper -eq 0 || -z "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
        echo "Aviso: clipboard features ficam inativas (precisa xclip/xsel/wl-clipboard + display)." >&2
    fi
fi

exec "$VENV_PY" image_watcher.py "$@"
