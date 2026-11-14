---
id: IMP-038
type: imp
layer: evolution
home: evolution/selected/give-the-unattributed-architecture-leaves-a-state.md
title: Give the three unattributed architecture leaves a state
summary: No archived record names ARG-007, ARG-008 or MTH-001, so the generated map
  omits them, and an archived record cites a float-inventory path that is gone
date: 2026-11-05
status: selected
---

# Give the three unattributed architecture leaves a state

`traceability-map.md` is generated from each archived record's `state:` field only, so a leaf appears only when a record names that leaf; no record names `ARG-007`, `ARG-008` or `MTH-001`.
An archived record also lists `docs/breakdown/manuscript/figure-and-table-inventory.md`, which does not exist; the inventory it named is `MS-014`.
**Evidence:**

A reader of the map reads the definition layer, term ownership and the research methods as historyless, which is either false or a history nobody wrote.

- The map carries rows for `ARG-001`, `MS-001` and `RES-001` only; the other three leaves exist with `status: current` under `argument/`.
**Acceptance:**

- `traceability-map.md` carries one `State:` row per live leaf under `argument/`, each produced by an archived record's `state:` field.
- No `Artifacts:` path in the map lacks a file at that path, and the float inventory appears as `MS-014`.
**Out of scope:**

Hand-editing the map, the archive, or the leaves; a new record for a choice with no dated event behind it.