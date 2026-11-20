---
id: INFO-023
type: info
title: Init scaffolds a hidden-store project
summary: bd init writes .bd_tree/nodes/1.md, a bd_work ignore entry, and the next commands.
date: 2026-11-20
status: current
---

# Init scaffolds a hidden-store project

`bd init [DIR]` creates a project whose store is `<DIR>/.bd_tree/nodes/` and whose single root node is `1.md`.

- **Root node:** `init_store` writes `.bd_tree/nodes/1.md` with `id: 1`, `title: Root`, `home: 1.md`, and `contains: []`.
- **Body:** the file body is `# Root` plus one line asking for the graph's intent.
- **Ignore entry:** `_ensure_work_ignored` creates `.gitignore` with `bd_work/` or appends that line without duplicating it.
- **Refusal:** a non-empty `nodes/` or `.bd_tree/nodes/` is left intact and raises `BreakdownError`.
- **Next steps:** the CLI prints `store initialized at ...` and the `bd new`, `bd tree`, and `bd work` commands.
- **Clean baseline:** the new store passes `bd check` with one scanned node.
