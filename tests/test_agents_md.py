"""Tests for the AGENTS.md idempotent uploader."""

from __future__ import annotations

import pytest

from imgwatcher import agents_md


def test_template_loads_and_is_non_empty():
    content = agents_md.load_content()
    assert "Genie Print" in content
    assert "AGENTS.md" in content
    assert len(content) > 200


def test_ensure_uploaded_skips_when_present(fake_transport):
    fake_transport.remote_files = {"AGENTS.md", "Image #1.png"}
    agents_md.ensure_uploaded(fake_transport)
    assert fake_transport.uploaded == []


def test_ensure_uploaded_uploads_when_missing(fake_transport):
    fake_transport.remote_files = {"Image #1.png"}
    agents_md.ensure_uploaded(fake_transport)
    assert fake_transport.uploaded == ["AGENTS.md"]


def test_ensure_uploaded_uploads_when_remote_empty(fake_transport):
    agents_md.ensure_uploaded(fake_transport)
    assert fake_transport.uploaded == ["AGENTS.md"]


def test_ensure_uploaded_skips_in_dry_run(fake_transport, mocker):
    fake_transport.dry_run = True
    list_remote = mocker.spy(fake_transport, "list_remote")
    agents_md.ensure_uploaded(fake_transport)
    assert fake_transport.uploaded == []
    list_remote.assert_not_called()


def test_ensure_uploaded_swallows_list_remote_exception(fake_transport, mocker):
    """If list_remote() raises, we must NOT propagate — best effort."""
    mocker.patch.object(
        fake_transport, "list_remote", side_effect=RuntimeError("network down")
    )
    agents_md.ensure_uploaded(fake_transport)
    assert fake_transport.uploaded == []


def test_ensure_uploaded_handles_upload_failure(fake_transport):
    fake_transport.upload_should_succeed = False
    agents_md.ensure_uploaded(fake_transport)
    # No exception raised even though upload returned False
    assert fake_transport.uploaded == []


def test_cli_default_calls_ensure_uploaded(tmp_path, mocker):
    from imgwatcher import cli

    ensure = mocker.patch("imgwatcher.cli.agents_md.ensure_uploaded")
    mocker.patch("imgwatcher.cli.sync.run")
    cli.main(
        [
            "--host", "h",
            "--dest", "/d",
            "--watch-dir", str(tmp_path),
            "--sync",
            "--dry-run",
        ]
    )
    ensure.assert_called_once()


def test_cli_no_agents_md_skips_upload(tmp_path, mocker):
    from imgwatcher import cli

    ensure = mocker.patch("imgwatcher.cli.agents_md.ensure_uploaded")
    mocker.patch("imgwatcher.cli.sync.run")
    cli.main(
        [
            "--host", "h",
            "--dest", "/d",
            "--watch-dir", str(tmp_path),
            "--sync",
            "--dry-run",
            "--no-agents-md",
        ]
    )
    ensure.assert_not_called()
