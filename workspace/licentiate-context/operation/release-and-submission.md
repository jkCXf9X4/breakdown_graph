---
id: OPS-010
type: operation
layer: operation
home: operation/release-and-submission.md
title: Release and submission
summary: What goes out, where it lands, and what is frozen
date: 2026-11-11
status: current
---

# Release and submission

This leaf covers the release surface and the frozen state of the deliverable `INT-002` defines.

**Frozen state:**

- Each paper carries a `final-submission` tag.
- Submodule pins select the exact commits the kappa compiles.
- Tags and pins are the freeze; later paper work does not enter silently.
- A source-only fix may put a pin several commits past its tag (`OPS-007`).
- Pin changes are intentional and described in the commit.

**Release surface:**

- `release/` holds two dated snapshots: `release/2026_02_13.pdf` and `release/2026_08_16.pdf`.
- No release script, tag, or checklist defines how a snapshot is produced.
- No release process is recorded beyond those two files.

**Open before submission:**

- Paper IV DOI and published venue are still missing; the paper is in press (`IMP-012`).
- Paper IV pin is confirmed final at `101c21f` (`OPS-005`, `IMP-004`).

**Owns:**

- What the release surface contains and which state is frozen.

**Excludes:**

- Deliverable shape and paper count (`INT-002`).
- Paper set and roles (`INT-002`, `ARG-003`).
- Pin mechanics and the `kappa` branch (`OPS-007`).
- Build commands (`OPS-006`).