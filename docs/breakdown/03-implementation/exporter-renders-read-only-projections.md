---
id: INFO-017
type: info
title: Exporter renders read-only projections
summary: Tree, context, and dot outputs are disposable projections of one view.
date: 2026-11-20
status: current
---

# Exporter renders read-only projections

`exporter.py` registers `tree`, `context`, and `dot` functions that take a `View` and write an `ExportResult` under `--out`.

- **Registry:** `@exporter(name)` fills `EXPORTERS`; `api.export_view` looks up the name, loads the view, refuses invalid views, and calls the function.
- **Tree projection:** `bd view REF --out DIR` runs `export_tree`, which writes each node at its templated path plus one `INDEX.md`.
- **Context projection:** `export_context` writes only fresh nodes, with `STALE.md` and `AGENTS.md`; stale source bodies stay absent.
- **Dot projection:** `export_dot` writes Graphviz with colours and shapes chosen by arbitrary front-matter fields.
- **Disposable output:** `_prepare_out` refuses a non-empty directory without `--force` or `--clean`, and nothing is written outside `out`.
- **Path templates:** `resolve_template` uses `{home}` when every node has one, else `{ref}.md`; `path_problem` rejects escapes and non-markdown paths.
