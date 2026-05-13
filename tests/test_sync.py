"""Tests for sync.run conflict resolution + dry-run + batched exists."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from imgwatcher import sync
from imgwatcher.transport import SCPTransport


class ScriptedReader:
    def __init__(self, responses):
        self._responses = list(responses)
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self._responses:
            raise AssertionError("ScriptedReader exhausted; got prompt: " + prompt)
        return self._responses.pop(0)


def _ok(stdout: str = "", stderr: str = "", returncode: int = 0) -> SimpleNamespace:
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def test_sync_dry_run_no_subprocess(watch_dir, make_image_factory, mocker):
    make_image_factory("a.png")
    make_image_factory("b.png")
    run = mocker.patch("imgwatcher.sync.subprocess.run")
    list_remote = mocker.patch.object(SCPTransport, "list_remote")
    t = SCPTransport(host="h", dest_dir="/d", dry_run=True)
    sync.run(watch_dir, t)
    run.assert_not_called()
    list_remote.assert_not_called()


def test_sync_no_files(watch_dir, mocker):
    list_remote = mocker.patch.object(SCPTransport, "list_remote", return_value=set())
    t = SCPTransport(host="h", dest_dir="/d")
    sync.run(watch_dir, t)
    list_remote.assert_not_called()


def test_sync_uploads_all_when_no_conflict(watch_dir, make_image_factory, mocker):
    make_image_factory("a.png")
    make_image_factory("b.png")
    mocker.patch.object(SCPTransport, "list_remote", return_value=set())
    run = mocker.patch("imgwatcher.sync.subprocess.run", return_value=_ok())
    t = SCPTransport(host="h", dest_dir="/d")
    sync.run(watch_dir, t)
    assert run.call_count == 2


def test_sync_overwrite_decision_per_file(watch_dir, make_image_factory, mocker):
    make_image_factory("a.png")
    make_image_factory("b.png")
    mocker.patch.object(SCPTransport, "list_remote", return_value={"a.png", "b.png"})
    run = mocker.patch("imgwatcher.sync.subprocess.run", return_value=_ok())
    t = SCPTransport(host="h", dest_dir="/d")
    sync.run(watch_dir, t, reader=ScriptedReader(["s", "i"]))
    assert run.call_count == 1


def test_sync_overwrite_all_only_prompts_once(watch_dir, make_image_factory, mocker):
    make_image_factory("a.png")
    make_image_factory("b.png")
    make_image_factory("c.png")
    mocker.patch.object(
        SCPTransport, "list_remote", return_value={"a.png", "b.png", "c.png"}
    )
    run = mocker.patch("imgwatcher.sync.subprocess.run", return_value=_ok())
    reader = ScriptedReader(["t"])
    t = SCPTransport(host="h", dest_dir="/d")
    sync.run(watch_dir, t, reader=reader)
    assert run.call_count == 3
    assert len(reader.prompts) == 1


def test_sync_skip_all_only_prompts_once(watch_dir, make_image_factory, mocker):
    make_image_factory("a.png")
    make_image_factory("b.png")
    make_image_factory("c.png")
    mocker.patch.object(
        SCPTransport, "list_remote", return_value={"a.png", "b.png", "c.png"}
    )
    run = mocker.patch("imgwatcher.sync.subprocess.run", return_value=_ok())
    reader = ScriptedReader(["n"])
    sync.run(watch_dir, SCPTransport(host="h", dest_dir="/d"), reader=reader)
    run.assert_not_called()
    assert len(reader.prompts) == 1


def test_sync_abort_stops_loop(watch_dir, make_image_factory, mocker):
    make_image_factory("a.png")
    make_image_factory("b.png")
    mocker.patch.object(SCPTransport, "list_remote", return_value={"a.png", "b.png"})
    run = mocker.patch("imgwatcher.sync.subprocess.run", return_value=_ok())
    reader = ScriptedReader(["a"])
    sync.run(watch_dir, SCPTransport(host="h", dest_dir="/d"), reader=reader)
    run.assert_not_called()


def test_sync_batches_exists_check(watch_dir, make_image_factory, mocker):
    make_image_factory("a.png")
    make_image_factory("b.png")
    make_image_factory("c.png")
    list_remote = mocker.patch.object(SCPTransport, "list_remote", return_value=set())
    mocker.patch("imgwatcher.sync.subprocess.run", return_value=_ok())
    sync.run(watch_dir, SCPTransport(host="h", dest_dir="/d"))
    assert list_remote.call_count == 1


def test_ask_user_action_invalid_then_valid(capsys):
    reader = ScriptedReader(["wat", "s"])
    assert sync.ask_user_action("a.png", "h:/d", reader) == sync.ACTION_OVERWRITE
