---
id: VER-004
type: verification
layer: verification
home: verification/terminology-consistency-checks.md
title: Terminology consistency checks
summary: How term and acronym drift is detected
date: 2026-11-11
status: current
---

# Terminology consistency checks

`thesis/custom/glossary.tex` is the LaTeX authority for term meaning.
The union acronym table regenerates 125 keys from 4 paper roots.
Last measured run on 2026-11-04 exits 2 with 2 form conflicts and 1 option conflict.
It proves `VER-006`'s terminology-use obligation, less term use in prose (`VER-005`).

**Checks:**

- Union regeneration exits 0 only when no conflict is unresolved.
- The 2026-11-04 run exits 2 with form conflicts on `hla` and `liu` and an option conflict on `opscon`; the committed `conflicts.md` predates them.
- A resolved key stays listed in `conflicts.md`; it is not silenced with `--allow-conflicts`.
- A source bug is fixed in the paper repo's `kappa` branch, not patched in the union; a genuine clash of meaning is recorded with reasoning, not merged away.
- Rendered-text grep catches a misspelling the table would otherwise carry: `grep Lnköping` returned 0 matches.
- New terms match `thesis/custom/glossary.tex`, or the glossary is updated on purpose.

**Acceptance criteria:**

- Union regeneration exits 0, with 0 unresolved conflicts and 0 form or option conflicts; the current run does not meet it.
- `conflicts.md` changes only together with a recorded reason.
- 0 matches for each known misspelling in the rendered text.
- Every new technical term has one glossary entry and one spelling.

**Limits:**

- The `liu` key carried `Lnköping` latently, defined but unused, so a clean grep proves absence in text, not absence in the table.
- `se` still means two different things; the clash is recorded, not resolved.
- Nothing checks term usage inside prose; that stays a reading task, and `VER-006` counts it unproven (`VER-005`).

**Owns:**

- The terminology acceptance criteria and the drift-detection evidence.
- The limits of each check, including the latent-defect case.
- That it proves `VER-006`'s terminology-use obligation short of prose use.

**Excludes:**

- What the definition layer and term ownership are (`ARG-007`, `ARG-008`).
- The glossary and acronym pipeline (`OPS-003`).
- Regeneration steps and conflict resolution procedure (`OPS-009`).
- Citation and bibliography checking (`VER-003`).
- Term use inside prose and the rest of the coverage map (`VER-005`, `IMP-036`).