# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Bridges a local→VPS screenshot workflow: watches a local folder, renames new images to `Image #<N>.<ext>` (N = max existing number + 1), and uploads them via SCP to a remote host so they can be read by Claude Code running over SSH.

User-facing strings (README, CLI output, prompts) are in **Portuguese**. Preserve that when editing user-facing text. Internal identifiers, log message ASCII tags (`[OK]`, `[ERRO]`, `[DRY RUN]`), and exception messages are English.

## Layout

```
imgwatcher/         # the actual package
  cli.py            # argparse + dispatch
  config.py         # extensions, regex, timeouts
  logging_setup.py  # cp1252-safe stderr (uses sys.stderr.reconfigure)
  processor.py      # numbering, rename, wait-for-stable, threading.Lock
  transport.py      # SCPTransport: shlex.quoted ssh/scp wrappers
  watcher.py        # WatchdogWatcher + PollingWatcher, share one processor
  sync.py           # bulk uploader with batched exists-check + conflict prompts
image_watcher.py    # 3-line shim into imgwatcher.cli.main (back-compat entry)
tests/              # pytest suite (unit + opt-in live)
start_watcher.sh    # bash wrapper sourcing config.sh, watcher mode
sync_images.sh      # bash wrapper sourcing config.sh, sync mode
config.example.sh   # copy to config.sh and edit
```

## Commands

This machine's system Python at `C:\Python313\` is missing stdlib and pip. Use `uv` (already installed) to manage a project venv:

```powershell
# First-time setup (creates .venv with managed Python 3.13)
uv venv --python 3.13 .venv
uv pip install -r requirements-dev.txt

# Run the watcher (watcher mode)
.\.venv\Scripts\python.exe image_watcher.py --host <ssh-alias> --dest <remote-path>

# One-shot bulk sync
.\.venv\Scripts\python.exe image_watcher.py --host <ssh-alias> --dest <remote-path> --sync

# Dry-run (no SCP/SSH)
.\.venv\Scripts\python.exe image_watcher.py --host <ssh-alias> --dest <remote-path> --dry-run [--sync]

# Tests
.\.venv\Scripts\python.exe -m pytest                       # unit only, ~2 s
$env:RUN_LIVE_TESTS = "1"; .\.venv\Scripts\python.exe -m pytest -m live  # real SCP to myserver, ~8 s
.\.venv\Scripts\python.exe -m pytest tests/test_processor.py::test_next_number_with_gap  # single test
```

`start_watcher.sh` and `sync_images.sh` still work in Git Bash but assume `python` resolves to a working interpreter (which it does not, on this machine, in plain PowerShell — use the venv path explicitly).

## Architecture

- **One processor, two watcher modes.** `ImageProcessor` owns numbering, renaming, the stability wait, and a `threading.Lock` around scan+rename to prevent two concurrent screenshots from getting the same number. Both `run_watchdog` and `run_polling` in `watcher.py` call `processor.process(path)` — there is no longer duplicated rename/upload code.
- **Numbering** is regex-derived (`Image #(\d+)`) — no persistent counter. Deleting `Image #5.png` after others exist will renumber the next file to 5. (Captured as a known follow-up in the plan, not in scope here.)
- **Transport (`SCPTransport`)** is the only place that shells out. `upload` uses `["scp", src, "host:dest"]` (argv form — safe). `exists` and `list_remote` send remote commands through `ssh` and **must** pass any path through `shlex.quote` because ssh evaluates the remote command in a shell. The exists-check is now `test -f <quoted> && echo exists || echo missing`; the list call is `ls -1 -- <quoted>`. Do not interpolate raw paths.
- **`sync.run`** does one batched `list_remote()` upfront and checks membership in-process — was N round-trips, is now 1. Conflict prompt supports `S`/`I`/`T`/`N`/`A` (skip-all is now reachable).
- **Logging.** `logging_setup.configure` calls `sys.stderr.reconfigure(errors="replace")` instead of replacing the stream — necessary because the older approach (wrapping `stderr.buffer` in a fresh `TextIOWrapper`) breaks pytest's capture and the global `print` infrastructure.

## Gotchas

- **MINGW64 / Git Bash path mangling**: Unix-style absolute paths passed to `--dest` get rewritten to Windows paths. Use double slashes (`//root//foo//bar`). README examples and `config.example.sh` already do this.
- **The watch dir is created** (with `mkdir -p`) if missing, by `cli.main` — don't add another `exists()` check upstream.
- **`processed_files` set was removed** (it caused a silent skip on re-screenshots to the same filename). Dedup now comes from `wait_for_stable` + the `Image #\d+` regex skip in `processor.rename`. If you re-add a dedup set, the regression test in `tests/test_processor.py::test_rescreenshot_processed_twice` will catch it.
- **Live tests touch `myserver`.** They are skipped unless `RUN_LIVE_TESTS=1` is set. They use `/tmp/genie-e2e-<uuid>/` and clean up via `ssh myserver rm -rf ...` in a `finally`. If you change the live test, keep the cleanup in a `finally` — leaking dirs on a VPS is rude.
- **No CI yet.** All tests run locally. `pytest --strict-markers` is on, so don't add new markers without registering them in `pyproject.toml`.

## When extending

- Bug fix → write a failing test first under `tests/`, then fix. The suite is fast (~2 s without live).
- New flag → add to `cli.build_parser`; plumb through `cli.main`; cover with `tests/test_cli.py`.
- New transport (e.g. sftp) → add a class in `transport.py` with the same `upload/exists/list_remote` shape; everything above the transport stays unchanged. Out of scope for this iteration.
