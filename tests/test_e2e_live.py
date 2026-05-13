"""Opt-in live e2e test: real SCP/SSH to a configured host.

Skipped unless RUN_LIVE_TESTS=1 is set. Host alias comes from the
LIVE_TEST_HOST env var (default: ``myserver`` — set this to a host
present in your ~/.ssh/config). Touches /tmp/genie-e2e-<uuid>/ only;
cleans up after itself.
"""

from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path

import pytest

from imgwatcher import sync
from imgwatcher.processor import ImageProcessor
from imgwatcher.transport import SCPTransport

LIVE_HOST = os.environ.get("LIVE_TEST_HOST", "myserver")

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("RUN_LIVE_TESTS") != "1",
        reason="set RUN_LIVE_TESTS=1 to enable live tests",
    ),
]


def _ssh(*remote_argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["ssh", LIVE_HOST, *remote_argv],
        capture_output=True,
        text=True,
        timeout=20,
    )


@pytest.fixture
def remote_tmp() -> str:
    remote_dir = f"/tmp/genie-e2e-{uuid.uuid4().hex[:8]}"
    mk = _ssh("mkdir", "-p", remote_dir)
    assert mk.returncode == 0, mk.stderr
    try:
        yield remote_dir
    finally:
        _ssh("rm", "-rf", remote_dir)


def _make_png(path: Path, payload: bytes = b"\x89PNG\r\n\x1a\nfakebody") -> None:
    path.write_bytes(payload)


def test_upload_one_file(tmp_path: Path, remote_tmp: str):
    src = tmp_path / "Image #1.png"
    _make_png(src, b"\x89PNG\r\n\x1a\nfakebody-onefile")

    transport = SCPTransport(host=LIVE_HOST, dest_dir=remote_tmp)
    assert transport.upload(src) is True

    listed = transport.list_remote()
    assert "Image #1.png" in listed


def test_sync_with_conflict_overwrite_all(tmp_path: Path, remote_tmp: str):
    files = []
    for n in (1, 2, 3):
        p = tmp_path / f"Image #{n}.png"
        _make_png(p, f"body-{n}".encode())
        files.append(p)

    transport = SCPTransport(host=LIVE_HOST, dest_dir=remote_tmp)
    assert transport.upload(files[0]) is True
    assert "Image #1.png" in transport.list_remote()

    responses = iter(["t"])
    sync.run(tmp_path, transport, reader=lambda _: next(responses))

    listed = transport.list_remote()
    assert {"Image #1.png", "Image #2.png", "Image #3.png"} <= listed


def test_processor_renames_and_uploads_live(tmp_path: Path, remote_tmp: str):
    src = tmp_path / "screenshot.png"
    _make_png(src, b"\x89PNG\r\n\x1a\nfakebody-process")
    transport = SCPTransport(host=LIVE_HOST, dest_dir=remote_tmp)
    proc = ImageProcessor(tmp_path, transport)
    assert proc.process(src) is True
    assert "Image #1.png" in transport.list_remote()
