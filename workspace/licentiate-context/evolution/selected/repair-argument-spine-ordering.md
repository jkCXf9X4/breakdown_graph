---
id: IMP-032
type: imp
layer: evolution
home: evolution/selected/repair-argument-spine-ordering.md
title: Repair the argument's spine ordering
summary: The contract is used as a table header before it is stated in full, and ch04
  states a contribution but not the claim ch07 introduces
date: 2026-11-04
status: selected
---

# Repair the argument's spine ordering

The contract is named in ch02 with its parts listed (`thesis/chapters/02_introduction.tex:17`).
It is then used as a table header at `thesis/chapters/03_background.tex:57`, before it is stated clause by clause.
It is finally stated at `thesis/chapters/03_background.tex:80`, after the whole of ch02 and part of ch03.
`thesis/chapters/04_research_questions_and_contributions.tex:18-25` lists three gaps and the premise and never states the arithmetic connecting them to three clauses, four appended papers and three chain stages; three enumerations are in play and their relation is asserted nowhere.
`thesis/chapters/04_research_questions_and_contributions.tex:71-80` lists four paper-level contributions and closes by deferring the claim: "The thesis-level claim they support is developed in \Cref{ch:synthesis}". The claim itself is introduced in ch07 rather than stated in ch04.
`manuscript/kappa-structure.md:24` records ch04 as stating "the claim in `CLM-001`'s wording"; that is false as the thesis stands.
**Evidence:**

The thesis's central device arrives as a reference lookup rather than as an argument step: the reader meets it as a column heading and only later is told what it is.
That ordering makes the background chapter's table unreadable at first encounter and makes the contract look like an assumption rather than a result.
The missing arithmetic in ch04 is the same defect one level up: three enumerations of different lengths (the three handovers, the three clauses, the three stages) with no statement of how they map.
A deferred thesis-level claim is the defect an examiner notices first, because the contributions chapter is where the claim is supposed to be.

- `thesis/chapters/02_introduction.tex:17` names the contract and lists its parts.
- `thesis/chapters/03_background.tex:57` uses the contract clauses as table columns.
- `thesis/chapters/03_background.tex:80` states the contract, after 1,404 words of ch02 and 1,760 words of ch03.
- `thesis/chapters/04_research_questions_and_contributions.tex:18-25` lists three gaps and the premise, with no mapping to the three clauses, the four papers or the three chain stages.
- Three enumerations in play: the three gaps at `04:18-25`, three clauses at `03:80`, four appended papers at `04:60-63`, three chain stages in `ARG-001`.
- `thesis/chapters/04_research_questions_and_contributions.tex:80` defers the thesis-level claim to ch07; the claim first appears at `thesis/chapters/07_synthesis_and_discussion.tex:5`.
- `MS-004` requires the thesis-level contributions in ch04.
- `CLM-001` owns the claim's wording and calibrated strength.
- `manuscript/kappa-structure.md:24` records ch04 as already stating the claim in that wording, which the thesis does not.
- Review record `INFO-028`; audit: `.dynamic-harness/261101_082500_e339/review/structure-front.md` S-01, S-02, S-10 and S-13, all BLOCKER.
**Acceptance:**

- The contract is stated before it is used in full, in the chapter that first needs it, and the table at `03_background.tex:57` follows the statement.
- The introduction's summary at `02_introduction.tex:17` points forward to a stated definition and does not replace it.
- ch04 states the mapping from the three gaps and the premise to the three clauses and the four appended papers; `ARG-001` carries the arithmetic across the three chain stages.
- ch04 states the thesis-level claim in one sentence owned by `CLM-001`, and ch07 elaborates rather than introduces it.
- `manuscript/kappa-structure.md:24` records the claim's actual site, or is marked as intended-state.
- A reader who stops after the methods chapter can state what the thesis claims and what it contributes.
- The restructuring is the minimal one that achieves the above; no chapter is renumbered without a stated reason.
**Out of scope:**

- The wording of the contract (`IMP-021`) and its status as an instrument (`IMP-022`).
- The sub-question decomposition (`IMP-024`).
- The triplication of the paper-to-chain mapping (`IMP-033`).
- The terminology authority for the clause names (`IMP-031`).