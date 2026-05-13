"""Remote-host I/O: SCP upload + SSH-based existence and listing.

All shell-bound paths are passed through shlex.quote because ssh evaluates
its remote-command argument in a shell on the remote side.
"""

from __future__ import annotations

import logging
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import SCP_TIMEOUT_SECONDS, SSH_TIMEOUT_SECONDS

log = logging.getLogger(__name__)


@dataclass
class SCPTransport:
    host: str
    dest_dir: str
    dry_run: bool = False

    def _remote_target(self) -> str:
        return f"{self.host}:{self.dest_dir}"

    def upload(self, local_path: Path) -> bool:
        local_path = Path(local_path)
        if not local_path.exists():
            log.debug("upload: source missing: %s", local_path)
            return False

        target = self._remote_target()
        if self.dry_run:
            log.debug("dry-run upload: %s -> %s", local_path, target)
            return True

        try:
            result = subprocess.run(
                ["scp", str(local_path), target],
                capture_output=True,
                text=True,
                timeout=SCP_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            log.debug("scp timeout for %s", local_path.name)
            return False
        except OSError as exc:
            log.debug("scp os error for %s: %s", local_path.name, exc)
            return False

        if result.returncode == 0:
            return True
        log.debug("scp non-zero (%s): %s", local_path.name, result.stderr.strip())
        return False

    def exists(self, file_name: str) -> bool:
        """Return True iff dest_dir/file_name exists on the remote."""
        if self.dry_run:
            return False
        remote_path = f"{self.dest_dir}/{file_name}"
        remote_cmd = f"test -f {shlex.quote(remote_path)} && echo exists || echo missing"
        try:
            result = subprocess.run(
                ["ssh", self.host, remote_cmd],
                capture_output=True,
                text=True,
                timeout=SSH_TIMEOUT_SECONDS,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            log.debug("exists check failed: %s", exc)
            return False
        return "exists" in result.stdout

    def list_remote(self) -> set[str]:
        """List filenames under dest_dir. Empty set on any failure."""
        if self.dry_run:
            return set()
        remote_cmd = f"ls -1 -- {shlex.quote(self.dest_dir)} 2>/dev/null"
        try:
            result = subprocess.run(
                ["ssh", self.host, remote_cmd],
                capture_output=True,
                text=True,
                timeout=SSH_TIMEOUT_SECONDS,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            log.debug("list_remote failed: %s", exc)
            return set()
        if result.returncode != 0:
            return set()
        return {line for line in result.stdout.splitlines() if line}
