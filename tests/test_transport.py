"""Tests for SCPTransport: command shape, shell quoting, error paths."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from imgwatcher.transport import SCPTransport


def _ok(stdout: str = "", stderr: str = "", returncode: int = 0) -> SimpleNamespace:
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def test_upload_calls_scp_with_target(tmp_path: Path, mocker):
    src = tmp_path / "Image #1.png"
    src.write_bytes(b"x")
    run = mocker.patch("imgwatcher.transport.subprocess.run", return_value=_ok())
    t = SCPTransport(host="myhost", dest_dir="/tmp/foo")
    assert t.upload(src) is True
    args, _ = run.call_args
    assert args[0] == ["scp", str(src), "myhost:/tmp/foo"]


def test_upload_dry_run_does_not_call_scp(tmp_path: Path, mocker):
    src = tmp_path / "a.png"
    src.write_bytes(b"x")
    run = mocker.patch("imgwatcher.transport.subprocess.run")
    t = SCPTransport(host="h", dest_dir="/d", dry_run=True)
    assert t.upload(src) is True
    run.assert_not_called()


def test_upload_returns_false_on_nonzero(tmp_path, mocker):
    src = tmp_path / "a.png"
    src.write_bytes(b"x")
    mocker.patch(
        "imgwatcher.transport.subprocess.run", return_value=_ok(returncode=1, stderr="boom")
    )
    assert SCPTransport(host="h", dest_dir="/d").upload(src) is False


def test_upload_returns_false_on_timeout(tmp_path, mocker):
    src = tmp_path / "a.png"
    src.write_bytes(b"x")
    mocker.patch(
        "imgwatcher.transport.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="scp", timeout=1),
    )
    assert SCPTransport(host="h", dest_dir="/d").upload(src) is False


def test_upload_missing_local_file_returns_false(tmp_path, mocker):
    run = mocker.patch("imgwatcher.transport.subprocess.run")
    assert SCPTransport(host="h", dest_dir="/d").upload(tmp_path / "ghost.png") is False
    run.assert_not_called()


def test_exists_quotes_special_chars(mocker):
    run = mocker.patch(
        "imgwatcher.transport.subprocess.run", return_value=_ok(stdout="exists\n")
    )
    t = SCPTransport(host="h", dest_dir="/tmp/with space")
    t.exists("file; rm -rf /.png")
    args, _ = run.call_args
    cmd_list = args[0]
    assert cmd_list[0] == "ssh"
    assert cmd_list[1] == "h"
    remote_cmd = cmd_list[2]
    expected_path = "/tmp/with space/file; rm -rf /.png"
    assert shlex.quote(expected_path) in remote_cmd
    assert "; rm -rf /" not in remote_cmd.split(shlex.quote(expected_path))[0]


def test_exists_true_when_remote_prints_exists(mocker):
    mocker.patch(
        "imgwatcher.transport.subprocess.run", return_value=_ok(stdout="exists\n")
    )
    assert SCPTransport(host="h", dest_dir="/d").exists("a.png") is True


def test_exists_false_when_remote_prints_missing(mocker):
    mocker.patch(
        "imgwatcher.transport.subprocess.run", return_value=_ok(stdout="missing\n")
    )
    assert SCPTransport(host="h", dest_dir="/d").exists("a.png") is False


def test_exists_false_on_dry_run(mocker):
    run = mocker.patch("imgwatcher.transport.subprocess.run")
    t = SCPTransport(host="h", dest_dir="/d", dry_run=True)
    assert t.exists("a.png") is False
    run.assert_not_called()


def test_list_remote_parses_ls_output(mocker):
    mocker.patch(
        "imgwatcher.transport.subprocess.run",
        return_value=_ok(stdout="a.png\nb.png\n\nc.jpg\n"),
    )
    t = SCPTransport(host="h", dest_dir="/d")
    assert t.list_remote() == {"a.png", "b.png", "c.jpg"}


def test_list_remote_quotes_dir(mocker):
    run = mocker.patch(
        "imgwatcher.transport.subprocess.run", return_value=_ok(stdout="")
    )
    t = SCPTransport(host="h", dest_dir="/tmp/d; ls /")
    t.list_remote()
    remote_cmd = run.call_args[0][0][2]
    assert shlex.quote("/tmp/d; ls /") in remote_cmd


def test_list_remote_empty_on_failure(mocker):
    mocker.patch(
        "imgwatcher.transport.subprocess.run",
        return_value=_ok(returncode=2),
    )
    assert SCPTransport(host="h", dest_dir="/d").list_remote() == set()


def test_list_remote_empty_on_dry_run(mocker):
    run = mocker.patch("imgwatcher.transport.subprocess.run")
    assert SCPTransport(host="h", dest_dir="/d", dry_run=True).list_remote() == set()
    run.assert_not_called()
