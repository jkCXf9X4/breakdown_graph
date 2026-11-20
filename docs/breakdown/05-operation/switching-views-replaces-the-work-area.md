---
id: INFO-025
type: info
title: Switching views replaces the work area
summary: bd work REF rebuilds the same bd_work path and removes links left by the previous view.
date: 2026-11-20
status: current
---

# Switching views replaces the work area

`bd work REF` rebuilds `<project>/bd_work/` for the new view and leaves no link from the previous view.

- **Same path:** with no `out`, `work()` resolves `view.store.project_root / "bd_work"`; the path does not vary by ref.
- **Stale links:** `_inspect` marks links whose ref is absent from the new view as `stale-ref`; `_build` unlinks them and prunes empty directories.
- **Fresh links:** every ref in the new closure gets a relative symlink at its templated path.
- **Generated files:** `INDEX.md`, `REFS.md`, and `AGENTS.md` are rewritten for the new ref.
- **View header:** `REFS.md` and `INDEX.md` carry the view ref, so `bd current` and `bd work --status` read the area's actual view.
- **Guard:** detached or stray regular files stop the switch until `--writeback` or `--clean`.
