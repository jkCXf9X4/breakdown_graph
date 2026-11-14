---
id: IMP-018
type: imp
layer: evolution
home: evolution/selected/recheck-framework-coverage-cells.md
title: Re-check the framework-coverage cells against primary texts
summary: Two cells in the framework table rest on secondary descriptions, and one
  was already corrected once
date: 2026-11-04
status: selected
---

# Re-check the framework-coverage cells against primary texts

`tab:framework-coverage` reads four credibility frameworks against the three contract clauses.
The cells are readings, not quotations, and two of them rest on secondary description.
The intended-use column was corrected on 2026-10-31 from `part` to `yes` for NASA CAS and the M&S Rigor Scale, because both condition the assessment on an intended use rather than omitting it.
That correction is evidence that the remaining cells deserve the same scrutiny.
**Evidence:**

An examiner who knows NASA-STD-7009 will test the cells that understate a framework, and the thesis has already had one such cell.
The PCMM row rests on Blattnig's description of the model, because `oberkampfPredictiveCapabilityMaturity2007` is metadata-only in the library.
The `Exec = part` cells for PCMM and Oberkampf--Roy assert that execution appears only as numerical error; that is a reading of scope, not a sentence in either source.

- `babulaNASAStandardModels2009` states the CAS assesses credibility "for their broad intended use", which is why the column changed.
- `LIT-003` and `LIT-005` own the verified framework facts the cells read.
- `blattnigNASAStandardModels2013` describes PCMM as narrower in scope, focused on mathematical models, and names it in one sentence.
- `royComprehensiveFrameworkVerification2011` separates validation and application domains but says nothing about orchestration.
- `asmeStandardVerificationValidation2009` is metadata-only, so a fifth row cannot be added until `IMP-016` closes.
**Acceptance:**

- Every cell either cites a sentence from a primary source or is marked in the text as a reading of scope.
- ASME V&V 20 is added as a fifth row, or the omission is stated where the table introduces it.
- No cell contradicts a framework's own text.
**Out of scope:**

- Adding frameworks beyond the four in the table.
- The novelty paragraph that follows the table; it depends on the table but is not a cell (`IMP-020`).