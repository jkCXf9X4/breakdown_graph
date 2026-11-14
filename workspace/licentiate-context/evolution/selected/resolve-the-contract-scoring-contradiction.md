---
id: IMP-022
type: imp
layer: evolution
home: evolution/selected/resolve-the-contract-scoring-contradiction.md
title: Resolve the contract's scoring contradiction
summary: Four texts describe the contract as a score and as not-a-score, and the worked
  example depends on which
date: 2026-11-04
status: selected
---

# Resolve the contract's scoring contradiction

The contract is described in two incompatible ways.
`thesis/chapters/07_synthesis_and_discussion.tex:7` says it is "formulated as what must accompany a result rather than as a score to be aggregated".
`thesis/chapters/07_synthesis_and_discussion.tex:79` captions the same table "The score is the number of clauses recoverable from artifacts alone".
`thesis/chapters/07_synthesis_and_discussion.tex:98` reports "a score of two clauses out of four".
`thesis/custom/glossary.tex:25-28` says the contract is "satisfied or not satisfied rather than scored".
The prose defers to the glossary as authoritative, so the authoritative text denies the thing the chapter then does.
**Evidence:**

The worked example at `07_synthesis_and_discussion.tex:66-99` is the thesis's only empirical application of its central device, and it is written as a score.
If the contract is not a score, the example is malformed and must be rewritten as three independent verdicts, with execution and evaluation stated as delimitations outside the objective.
If it is a score, the glossary and the chapter's opening sentence are wrong, and the thesis must say what the number means and what it does not.
An examiner reading the glossary first and the synthesis second sees the thesis contradict itself on the one instrument it asks to be judged by.
The contradiction also propagates: `IMP-017` asks a second rater to reproduce "the score", which presupposes the answer.

- `thesis/chapters/07_synthesis_and_discussion.tex:7` denies aggregation.
- `thesis/chapters/07_synthesis_and_discussion.tex:79` defines the score as a count of recoverable clauses.
- `thesis/chapters/07_synthesis_and_discussion.tex:98` reports a score whose denominator includes execution, which the objective places outside the contract (`ARG-006`).
- `thesis/chapters/07_synthesis_and_discussion.tex:101` says the thesis "uses two numbers for a result", which is a metric, and in the same paragraph calls the rubric "hand-applied, single-rater and used once".
- `thesis/custom/glossary.tex:25-28` says satisfied-or-not rather than scored.
- `CLM-001`'s calibrated strength is silent on "not a score" while `07:7` asserts it, so the intent layer does not license the score reading: resolve for `07:7` or amend `07:7`.
- Review record `INFO-028`; audit: `.dynamic-harness/261101_082500_e339/review/claims-synthesis.md` F-05 and F-31, both BLOCKER.
- Audit: `.dynamic-harness/261101_082500_e339/review/structure-back.md` S-22.
**Acceptance:**

- One sentence in the thesis states what kind of instrument the contract is: checklist, score, or diagnostic.
- The glossary entry, `07_synthesis_and_discussion.tex:7`, the caption at `:79`, and the result sentence at `:98` all use that one description.
- If it is a score: the thesis states the scale, what a higher number means, and why aggregation across clauses is legitimate.
- If it is a checklist: `tab:contract-applied` reports three verdicts and no total, with execution and evaluation stated as delimitations outside the objective, and `:101`'s "two numbers" is removed or re-described.
- If it is a diagnostic: the thesis states what it diagnoses and what a diagnosis is not.
- The answer is the one `IMP-017`'s second rater is asked to reproduce.
- The calibrated strength this decision must not exceed is `CLM-001`; the outcome is recorded in `ARG-006` (contract's status) and `VER-001` (retrospective test), not in `CLM-001`.
**Out of scope:**

- Whether the contract is derived or stipulated (`IMP-021`).
- Whether the instrument discriminates between results (`IMP-023`).
- The independence of the rater (`IMP-017`).