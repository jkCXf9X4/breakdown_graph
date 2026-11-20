---
id: INFO-019
type: info
title: CLI and API share one command surface
summary: Argparse handlers delegate to a thin public API so scripts and terminals use the same operations.
date: 2026-11-20
status: current
---

# CLI and API share one command surface

`cli.py` parses arguments and calls `api.py` for mutations and `navigate.py` for read-only renders, so the command surface and the Python surface stay aligned.

- **API layer:** `api.py` re-exports `load`, `load_view`, `check`, `export_view`, `work`, `edit_path`, `solution_*`, and the structural operations.
- **CLI layer:** each `_cmd_*` handler resolves `--root`, `BD_ROOT`, or the nearest store, calls one function, prints, and returns an integer.
- **Read-only renderers:** `tree`, `ls`, `find`, `grep`, `path`, and `views` call `navigate` functions on a loaded store or view.
- **Shared errors:** `NavigationError` yields exit 1 and `BreakdownError` yields exit 2; `main` prints `bd: ...` to stderr.
- **Entry points:** the `bd` console script targets `bd_tree.cli:main`, and `PYTHONPATH=src python3 -m bd_tree` calls the same `main`.
