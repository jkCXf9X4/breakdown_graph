---
id: VER-005
type: verification
layer: verification
home: verification/requirement-coverage.md
title: Requirement coverage
summary: Which check proves which requirement, and which obligations no check proves
date: 2026-11-11
status: current
---

# Requirement coverage

Every `REQ-` obligation is proved by one check, or it is unproven and this leaf says so.

- `OPS-011` format, length, authorship — `VER-002` proves length and assembly; the abstract word count, the Swedish summary, the delimitations and the author contributions have no check (4 unproven).
- `MS-015` what the kappa must state — `VER-001` proves that each contribution names a paper result; the seven statements other than the delimitation have no check (7 unproven).
- `VER-006` integrity — `VER-003` proves backing and `VER-004` proves terminology; no-uncited-claim, quotation, the mapping table's presence and AI disclosure have no check (4 unproven).
- `VER-007` acceptance criteria — unproven (1): no check runs a reader pass, and `INFO-028` records findings rather than a pass.
- Rule: a requirement with no check is a promise nobody can fail; a reviewer finds it before the gate does.
- Unproven obligations: 16 — 4 in `OPS-011`, 7 in `MS-015`, 4 in `VER-006`, 1 in `VER-007`; the delimitation is counted once, under `OPS-011`.
- `IMP-036` carries the decision on each unproven obligation: a check, or review-only by explicit choice.

**Owns:**

- The requirement-to-check map: which leaf proves which `REQ-` obligation.
- The unproven list and its count.
- The rule that an unproven obligation is a promise nobody can fail.

**Excludes:**

- The obligations themselves (`OPS-011` to `VER-007`).
- What each check proves in detail, and its evidence (`VER-002`, `VER-003`, `VER-004`, `VER-001`).
- The review findings that stand in for a missing check (`INFO-028`).
- The plan that would close the gap (`IMP-036`).