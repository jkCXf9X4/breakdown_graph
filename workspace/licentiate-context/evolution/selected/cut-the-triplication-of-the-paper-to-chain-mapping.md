---
id: IMP-033
type: imp
layer: evolution
home: evolution/selected/cut-the-triplication-of-the-paper-to-chain-mapping.md
title: Cut the triplication of the paper-to-chain mapping
summary: The mapping from papers to chain stages is stated three times across the
  chapters; it belongs in one place
date: 2026-11-11
status: selected
---

# Cut the triplication of the paper-to-chain mapping

The paper-to-chain mapping (which paper answers which chain stage) appears in three chapters, so a reader meets the same mapping three times and edits must stay in sync.

**Evidence:**

- `evolution/selected/repair-argument-spine-ordering.md:53` excludes the triplication of the paper-to-chain mapping to this IMP.
- Patch-plan batch B9 (`review/patch-plan-batches.md:25`) carries this IMP with `IMP-032`, `IMP-031`, `IMP-024` across ch02, ch03, ch04, ch06, ch07, `custom/glossary.tex`, `01_terminology.tex`.
- R-IDs R-085, R-090, R-092, R-096, R-147 are owned by this IMP (`patch-plan.md:31`).
- The mapping appears three times; B9's message is "Reorder the argument spine and cut the triplication".

**Change:**

- The paper-to-chain mapping is stated once, in the place `ARG-003` owns, and the other two sites reference it.

**Risk:**

- Medium: B9 moves text across five chapters, so a split leaves `\Cref`s dangling; it lands as one commit with `IMP-032`, `IMP-031`, `IMP-024`.

**Acceptance:**

- The mapping appears in exactly one chapter and the other two cite it by reference.
- No `\Cref` dangles after the move.
- `python3 thesis/build.py` runs with 0 undefined citations.

**Out of scope:**

- The argument spine ordering (`IMP-032`).
- The sub-question decomposition (`IMP-024`).
- The terminology authority for the clause names (`IMP-031`).