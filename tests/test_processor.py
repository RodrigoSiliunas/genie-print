"""Tests for processor: numbering, renaming, stability, locking."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from imgwatcher.processor import ImageProcessor, is_image, wait_for_stable


def test_next_number_empty(watch_dir, fake_transport):
    proc = ImageProcessor(watch_dir, fake_transport)
    assert proc.next_number() == 1


def test_next_number_with_existing(watch_dir, fake_transport, make_image_factory):
    make_image_factory("Image #5.png")
    make_image_factory("Image #2.jpg")
    make_image_factory("random.png")
    proc = ImageProcessor(watch_dir, fake_transport)
    assert proc.next_number() == 6


def test_next_number_with_gap(watch_dir, fake_transport, make_image_factory):
    make_image_factory("Image #1.png")
    make_image_factory("Image #10.png")
    proc = ImageProcessor(watch_dir, fake_transport)
    assert proc.next_number() == 11


def test_rename_non_matching(watch_dir, fake_transport, make_image_factory):
    src = make_image_factory("screenshot.png")
    proc = ImageProcessor(watch_dir, fake_transport)
    result = proc.rename(src)
    assert result is not None
    assert result.name == "Image #1.png"
    assert result.exists()
    assert not src.exists()


def test_rename_already_matching_is_noop(watch_dir, fake_transport, make_image_factory):
    src = make_image_factory("Image #3.png")
    proc = ImageProcessor(watch_dir, fake_transport)
    result = proc.rename(src)
    assert result == src
    assert src.exists()


def test_rename_missing_file_returns_none(watch_dir, fake_transport):
    proc = ImageProcessor(watch_dir, fake_transport)
    assert proc.rename(watch_dir / "does-not-exist.png") is None


def test_is_image_extensions():
    assert is_image(Path("a.png"))
    assert is_image(Path("a.JPG"))
    assert is_image(Path("a.webp"))
    assert not is_image(Path("a.txt"))
    assert not is_image(Path("a.exe"))


def test_wait_for_stable_steady_file(watch_dir, make_image_factory):
    p = make_image_factory("steady.png", b"abcdef")
    assert wait_for_stable(p, poll_s=0.05, max_wait_s=1.0) is True


def test_wait_for_stable_growing_file(watch_dir, make_image_factory):
    p = make_image_factory("growing.png", b"a")

    def grow():
        for chunk in (b"b", b"c", b"d"):
            time.sleep(0.05)
            with p.open("ab") as fh:
                fh.write(chunk)

    threading.Thread(target=grow, daemon=True).start()
    assert wait_for_stable(p, poll_s=0.05, max_wait_s=2.0) is True


def test_wait_for_stable_missing_returns_false(watch_dir):
    assert wait_for_stable(watch_dir / "ghost.png", poll_s=0.05, max_wait_s=0.2) is False


def test_concurrent_rename_no_collision(watch_dir, fake_transport, make_image_factory):
    src_a = make_image_factory("a.png")
    src_b = make_image_factory("b.png")
    proc = ImageProcessor(watch_dir, fake_transport)
    results: list[Path] = []
    barrier = threading.Barrier(2)

    def go(src: Path):
        barrier.wait()
        r = proc.rename(src)
        if r is not None:
            results.append(r)

    threads = [threading.Thread(target=go, args=(src_a,)), threading.Thread(target=go, args=(src_b,))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(results) == 2
    names = {r.name for r in results}
    assert names == {"Image #1.png", "Image #2.png"}


def test_process_full_pipeline_uploads(watch_dir, fake_transport, make_image_factory):
    proc = ImageProcessor(watch_dir, fake_transport)
    src = make_image_factory("foo.png", b"abcdef")
    assert proc.process(src) is True
    assert fake_transport.uploaded == ["Image #1.png"]


def test_process_rejects_non_image(watch_dir, fake_transport, make_image_factory):
    proc = ImageProcessor(watch_dir, fake_transport)
    src = make_image_factory("notes.txt", b"abc")
    assert proc.process(src) is False
    assert fake_transport.uploaded == []


def test_rescreenshot_processed_twice(watch_dir, fake_transport, make_image_factory):
    """Regression: re-creating a file at the same path must be processed again."""
    proc = ImageProcessor(watch_dir, fake_transport)
    src1 = make_image_factory("shot.png", b"first")
    assert proc.process(src1) is True
    src2 = make_image_factory("shot.png", b"second")
    assert proc.process(src2) is True
    assert fake_transport.uploaded == ["Image #1.png", "Image #2.png"]


def test_process_silent_when_file_missing(watch_dir, fake_transport, mocker):
    """Regression: transient event for a file that's already gone produces no
    warning and no detected message — silently dropped."""
    detected = mocker.patch("imgwatcher.processor.display.detected")
    warning = mocker.patch("imgwatcher.processor.display.warning")
    proc = ImageProcessor(watch_dir, fake_transport)
    assert proc.process(watch_dir / "ghost.png") is False
    detected.assert_not_called()
    warning.assert_not_called()


def test_process_silent_when_file_vanishes_during_wait(
    watch_dir, fake_transport, make_image_factory, mocker
):
    """Regression: snipping-tool pattern — file exists at on_created, then
    disappears mid-wait. Should produce no warning."""
    detected = mocker.patch("imgwatcher.processor.display.detected")
    warning = mocker.patch("imgwatcher.processor.display.warning")
    src = make_image_factory("vanish.png", b"a")
    mocker.patch("imgwatcher.processor.wait_for_stable", return_value=False)
    src.unlink()
    proc = ImageProcessor(watch_dir, fake_transport)
    assert proc.process(src) is False
    detected.assert_not_called()
    warning.assert_not_called()


def test_process_warns_when_file_persists_but_doesnt_stabilize(
    watch_dir, fake_transport, make_image_factory, mocker
):
    """If the file is still there but wait timed out, the user does deserve
    to see a warning."""
    detected = mocker.patch("imgwatcher.processor.display.detected")
    warning = mocker.patch("imgwatcher.processor.display.warning")
    src = make_image_factory("growing.png", b"a")
    mocker.patch("imgwatcher.processor.wait_for_stable", return_value=False)
    proc = ImageProcessor(watch_dir, fake_transport)
    assert proc.process(src) is False
    detected.assert_called_once()
    warning.assert_called_once()
