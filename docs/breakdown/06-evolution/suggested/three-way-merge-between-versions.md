---
id: IMP-002
type: imp
title: Three-way merge between versions
summary: Promotion copies one version onto main and leaves synthesis to manual editing.
date: 2026-11-20
status: suggested
---

# Three-way merge between versions

Promotion replaces main with one version, and no base is recorded to merge a second alternative against it.

- **Current behavior:** `bd promote` copies the chosen version onto main; versions carry no `based_on` lineage and the tool has no merge engine.
- **Cost:** Two alternatives of one node can only be combined by hand, and the losing content is easy to drop.
- **Possible direction:** Offer a diff-and-synthesize path that treats main as the base and writes a new version, while git stays the history owner.
- **Constraint:** The rejected design kept `based_on` lineage out, so any base must be inferred or supplied explicitly.
