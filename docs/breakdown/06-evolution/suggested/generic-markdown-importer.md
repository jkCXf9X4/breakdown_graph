---
id: IMP-006
type: imp
title: Generic markdown importer
summary: Existing markdown trees must be converted by hand to the node file pattern.
date: 2026-11-20
status: suggested
---

# Generic markdown importer

An existing markdown tree must be converted by hand into node files with ids, `contains`, and front matter.

- **Current behavior:** There is no importer; each document becomes a node through manual file creation and containment edits.
- **Cost:** Migration is slow and error-prone, and reachability or duplicate ids surface only after the tree is built.
- **Possible direction:** Map folders or headings to containment, assign stable ids, and emit a dry-run report before writing nodes.
- **Constraint:** Import must preserve body bytes and avoid inventing schema beyond the structural keys.
