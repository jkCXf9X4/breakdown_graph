---
id: INFO-024
type: info
title: Check validates global and per-view invariants
summary: bd check covers filenames, ids, containment targets, cycles, view trees, homes, links, and size.
date: 2026-11-20
status: current
---

# Check validates global and per-view invariants

`checker.check` loads the whole store, validates global structure, then validates every containment view plus the selected view.

- **Global pass:** `_check_targets_and_cycles` and `_check_reachability` cover missing targets, containment cycles, and refs unreachable through `contains` or a shared id.
- **Per-view pass:** `_check_view_trees` loads every node-rooted view and reports `multiple-parents`, `containment-cycle`, and `missing-target`.
- **Selected view:** `check` validates homes, propagating links, and body size on the resolved view; `--view` narrows that scope.
- **Size limits:** `SIZE_LINES = 120` and `SIZE_CHARS = 8000` by default, overridable with `--max-lines` and `--max-chars`.
- **Schema opt-in:** `--require FIELD` is the only front-matter validation; arbitrary fields, link types, and layers pass untouched.
- **Result:** `CheckResult` counts scanned nodes and exposes `errors`, `warnings`, and `ok`; the CLI returns 1 when `ok` is false.
