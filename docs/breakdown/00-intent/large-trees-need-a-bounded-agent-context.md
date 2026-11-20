---
id: INFO-003
type: info
title: Large trees need a bounded agent context
summary: An agent cannot hold a whole tree; one declared view and one work area keep the context usable.
date: 2026-11-20
status: current
---

# Large trees need a bounded agent context

An agent cannot hold a whole tree, so the tool gives it one declared view in a single work area and replaces that area when the view changes.

- **Context limit:** a full tree dumped into a context displaces the conversation, and the oldest parts are dropped first.
- **Declared view:** a view is the containment closure of one ref, and `bd work REF` materialises exactly that closure.
- **One area:** `<project>/bd_work/` holds one view at a time; a different REF replaces its contents instead of adding a second folder.
- **Navigation:** generated `INDEX.md`, `REFS.md`, and `AGENTS.md` make the bounded subset navigable without listing the store.
- **Read-only pack:** `bd export context --view REF` emits fresh nodes plus `STALE.md` for an agent that must not write.
