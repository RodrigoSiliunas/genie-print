"""Shared fixtures."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pytest

from imgwatcher.transport import SCPTransport


@pytest.fixture
def watch_dir(tmp_path: Path) -> Path:
    return tmp_path


def make_file(folder: Path, name: str, content: bytes = b"x") -> Path:
    p = folder / name
    p.write_bytes(content)
    return p


@dataclass
class FakeTransport:
    """In-memory stand-in for SCPTransport."""

    host: str = "fake"
    dest_dir: str = "/tmp/fake"
    dry_run: bool = False
    uploaded: list[str] = field(default_factory=list)
    remote_files: set[str] = field(default_factory=set)
    upload_should_succeed: bool = True

    def upload(self, local_path: Path) -> bool:
        if not self.upload_should_succeed:
            return False
        self.uploaded.append(Path(local_path).name)
        self.remote_files.add(Path(local_path).name)
        return True

    def exists(self, file_name: str) -> bool:
        return file_name in self.remote_files

    def list_remote(self) -> set[str]:
        return set(self.remote_files)


@pytest.fixture
def fake_transport() -> FakeTransport:
    return FakeTransport()


@pytest.fixture
def make_image_factory(watch_dir: Path):
    def _make(name: str, content: bytes = b"x") -> Path:
        return make_file(watch_dir, name, content)

    return _make
