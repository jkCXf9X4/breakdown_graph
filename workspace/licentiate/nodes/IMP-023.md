---
id: IMP-023
type: imp
layer: evolution
home: evolution/selected/test-whether-the-contract-discriminates.md
title: Test whether the contract discriminates between results
summary: One application to the in-repo case, which is built to carry all three clauses,
  so a full verdict shows the instrument is not negative by construction
date: 2026-11-05
status: selected
---

# Test whether the contract discriminates between results

The contract is applied once, to the in-repo case under `thesis/case/` (`RES-005`).
The case is built so all three clauses sit in committed artifacts, and the application reports one verdict per clause.
A full count is the discrimination evidence: the instrument can return a positive result, so its verdict is not entailed by the choice of result.
It is not a measurement of the case.
**Evidence:**

A rubric that returns the same verdict on every input is a description, not a measure.
The thesis-level claim makes the contract a diagnostic at the handovers; a diagnostic must be able to come out differently.
The retired application returned one of three because the artifact set predated the definition clause, so the negative outcome was entailed by construction.
The in-repo case removes that entailment: it is built by the thesis, its artifacts sit in the repository, and a reader can check each verdict.
If the case cannot carry a clause, the instrument claim weakens and the leaf says so.

- The application moved from the cited temporal-decoupling paper to the in-repo case (`RES-005`).
- `IMP-039` builds the case, its artifact set, and its regeneration command.
- The three clauses are `ARG-006`; the outcome is recorded in `VER-001`.
- Review record `INFO-028`; audit: `.dynamic-harness/261101_082500_e339/review/structure-back.md` S-15 records the retired application as guaranteed by construction.
**Acceptance:**

- The contract is applied once, to the in-repo case, and the outcome is reported with one verdict per clause.
- All three clauses are recoverable from the case's artifacts alone, each with the artifact and line named.
- `tab:contract-applied` reports three of three; a lower count is reported rather than adjusted, and the leaf states what recovering the missing clause would take.
- The thesis states what the full count shows: a clause is recoverable when its artifact exists, so the instrument is not negative by construction.
- The thesis claims one application, not two; no second result is implied.
- The leaf states which test it runs: `CLM-001`'s refutation tests the CLAIM; this leaf tests the INSTRUMENT. The outcome is recorded in `VER-001`, not in `CLM-001`.
- The application reports verdicts, not predictive power: `CLM-001` claims no measured effort, defect rate, or productivity.
**Out of scope:**

- The independence of the rater (`IMP-017`).
- What kind of instrument the contract is (`IMP-022`).
- Building the case and its artifacts (`IMP-039`).
- Printing the case as one of the four appended papers; the appendix documents it.