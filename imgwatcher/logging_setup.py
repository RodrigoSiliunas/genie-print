"""Logging that does not raise UnicodeEncodeError on cp1252 Windows terminals."""

import logging
import sys


def configure(verbose: bool = False) -> None:
    """Set up root logger and make stderr tolerant of non-encodable chars.

    On cp1252 Windows consoles, printing Portuguese accents would otherwise
    raise UnicodeEncodeError. We switch the stream's error handler to
    'replace' instead of swapping the stream itself, so pytest's capture and
    other wrappers continue to work.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                try:
                    reconfigure(errors="replace")
                except (ValueError, OSError):
                    pass

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
