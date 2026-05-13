# Configurações do Image Watcher
# Edite este arquivo conforme suas necessidades e depois renomeie para config.sh

# Host SSH (deve estar configurado em ~/.ssh/config)
WATCHER_HOST="myserver"

# Caminho de destino no servidor remoto
# Use barras duplas no MINGW64 para evitar conversão de path
WATCHER_DEST="//path//to//remote//screenshots"

# Pasta local para monitorar
WATCHER_LOCAL_DIR="Images"

# Extensões de imagem suportadas (separadas por espaço)
IMAGE_EXTENSIONS=".png .jpg .jpeg .gif .bmp .webp .tiff .svg"