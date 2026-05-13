#!/bin/bash
# Script de conveniência para iniciar o watcher

# Carregar configuração se existir
if [ -f "config.sh" ]; then
    source config.sh
fi

# Configurações padrão - edite conforme necessário
DEFAULT_HOST="${WATCHER_HOST:-myserver}"
DEFAULT_DEST="${WATCHER_DEST:-//path//to//remote//screenshots}"
DEFAULT_WATCH_DIR="${WATCHER_LOCAL_DIR:-Images}"

# Parse argumentos
HOST=${1:-$DEFAULT_HOST}
DEST=${2:-$DEFAULT_DEST}
WATCH_DIR=${3:-$DEFAULT_WATCH_DIR}

echo "Iniciando Image Watcher..."
echo "Host: $HOST"
echo "Destino: $DEST"
echo "Pasta local: $WATCH_DIR"
echo ""

python image_watcher.py --host "$HOST" --dest "$DEST" --watch-dir "$WATCH_DIR"