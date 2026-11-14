---
id: IMP-017
type: imp
layer: evolution
home: evolution/selected/second-rater-contract-score.md
title: Have the contract score read by a second rater
summary: The contract application to the in-repo case is single-rater and used once
date: 2026-11-05
status: selected
---

# Have the contract score read by a second rater

`sec:contract-applied` applies the three contract clauses to the in-repo case and reports one verdict per clause (`RES-005`, `IMP-039`).
The reading is made by the candidate, in one pass, on one artifact set.
`tab:contract-applied` is therefore a demonstration of a rubric, not a measurement, and the synthesis says so.
**Evidence:**

An examiner can reasonably ask whether the verdicts are a property of the artifacts or of the reader.
A single-rater reading on a single artifact set cannot separate the two, and the thesis-level claim that the contract is a diagnostic rests on that separation.
The three clause readings are also asymmetric in effort: the definition clause requires following the executed composition back to the architecture, the intended-use clause requires reading the case's criterion statement, and neither is mechanical.

- `thesis/chapters/07_synthesis_and_discussion.tex` states the rubric: clauses recoverable from artifacts alone, plus documents needed to recover the rest.
- The artifact set is `thesis/case/`, and each artifact is named in its README (`IMP-039`).
- The intended-use statement is part of the case, so the clause is read from a committed artifact rather than prose outside it.
- The definition clause compares the executed composition against the case's architecture definition.
**Acceptance:**

- A reader who has the repository but not the synthesis fills in `tab:contract-applied` independently.
- Agreement on all three rows, or a recorded disagreement and an amended rubric.
- The verdicts are either confirmed or changed in the kappa, with the second reading named in the text.
**Out of scope:**

- Extending the case to execution and evaluation, which are delimitations outside the objective (`ARG-006`).
- A second result from another paper; that widens the sample but does not test the rater (`IMP-023`).
- What kind of instrument the score is, and whether a total is legitimate at all (`IMP-022`).