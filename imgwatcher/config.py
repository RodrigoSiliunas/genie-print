"""Static configuration: extensions, naming pattern, default folder."""

import re

IMAGE_EXTENSIONS = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".svg"}
)

NAME_PATTERN = re.compile(r"Image #(\d+)")
NAME_TEMPLATE = "Image #{n}{ext}"

DEFAULT_WATCH_DIR = "Images"

SCP_TIMEOUT_SECONDS = 30
SSH_TIMEOUT_SECONDS = 10

STABILITY_POLL_INTERVAL_S = 0.25
STABILITY_MAX_WAIT_S = 5.0

POLLING_INTERVAL_S = 2.0
