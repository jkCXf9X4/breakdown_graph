---
id: IMP-021
type: imp
layer: evolution
home: evolution/selected/decide-whether-the-contract-is-derived-or-stipulated.md
title: Decide whether the three-clause contract is derived or stipulated
summary: The contract carries one citation, supporting only the execution delimitation,
  and ch07 declines to restate a derivation
date: 2026-11-04
status: selected
---

# Decide whether the three-clause contract is derived or stipulated

The contract is stated in full at `thesis/chapters/03_background.tex:80`.
It carries exactly one citation, `gomesSemanticsCosimulationAlgorithms2019`, and that citation supports only the execution delimitation: that orchestration settings are frequently left implicit in black-box integration.
Clauses one, two and three carry no citation at all.
No clause is derived from any of the four appended papers; the two co-simulation papers left the argument and carry no clause (`ARG-003`).
`thesis/chapters/07_synthesis_and_discussion.tex:14` says the definition is the glossary entry and that "neither is restated here", so the synthesis declines to supply the derivation the background does not give.
**Evidence:**

The thesis's central device has no stated warrant, and the text is ambiguous about whether it needs one.
`03_background.tex:80` frames the clauses as "a requirement of the contract, not as an existing standard", and declares execution a boundary of the thesis; that is a stipulation and is honest, but it is stated for the boundary and not for the contract.
But the surrounding prose reads as a finding: the clauses are presented as what the frameworks leave out, which is a claim about the literature and would need derivation.
An examiner cannot tell whether the contract is a definition the thesis adopts or a result the thesis establishes, and the answer changes what ch03 and ch07 must do.
If it is stipulated, the thesis should say so once and stop hedging. If it is derived, the derivation is missing and the contribution is unsupported.

- `thesis/chapters/03_background.tex:80` states the contract's clauses and cites `gomesSemanticsCosimulationAlgorithms2019` once, for the execution delimitation.
- `thesis/chapters/07_synthesis_and_discussion.tex:14` declines to restate a derivation and points at the glossary.
- `thesis/custom/glossary.tex:25-28` holds the authoritative definition, which is a definition and not a derivation.
- `thesis/chapters/04_research_questions_and_contributions.tex:18-25` lists three gaps and the premise, each with a paper pointer, and never connects a gap to a clause.
- `docs/breakdown/argument/chain/overview.md` states the contract as a property of the argument thread, not as a result of the papers.
- Review record `INFO-028`; audit: `.dynamic-harness/261101_082500_e339/review/claims-synthesis.md` F-11, BLOCKER, records that the clauses are restated as a definition and not derived.
- Audit: `.dynamic-harness/261101_082500_e339/review/claims-intro-bg.md` marks `03_background.tex:80` DEFINITIONAL and correctly framed, so the defect is the ambiguity, not a false attribution.
**Acceptance:**

- The thesis states in one place, in one sentence, whether the contract is stipulated or derived.
- If stipulated: `03_background.tex:80` says so without hedging, `07_synthesis_and_discussion.tex:14` stops apologising, and the thesis states the criterion the stipulation meets.
- If derived: the derivation is written and each clause cites the paper or source it comes from.
- The chosen answer is consistent with the three gaps and the premise at `04_research_questions_and_contributions.tex:18-25` and with the chain steps in `ARG-001`.
- No clause keeps a citation that supports only its motivation while the surrounding text implies derivation.
- The glossary entry and the prose statement agree on the contract's status.
- The calibrated strength this decision must not exceed is `CLM-001`; the outcome is recorded in `ARG-006` (contract's status) and `VER-001` (retrospective test), not in `CLM-001`.
**Out of scope:**

- Whether the contract is scored (`IMP-022`).
- Whether the contract discriminates when applied (`IMP-023`).
- The wording of the novelty claim (`IMP-020`).