#!/usr/bin/env python3
"""Compat shim. Real entry point is imgwatcher.cli.main()."""

from imgwatcher.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
