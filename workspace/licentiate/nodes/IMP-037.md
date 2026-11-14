---
id: IMP-037
type: imp
layer: evolution
home: evolution/selected/align-the-thesis-to-the-three-clause-model.md
title: Align the thesis to the three-clause model
summary: The thesis still states four clauses and five stages; `ARG-006` makes the
  contract three clauses and execution/evaluation delimitations
date: 2026-11-05
status: selected
---

# Align the thesis to the three-clause model

`ARG-006` fixes the credibility contract at three clauses, definition, intended use and evidence, and makes execution and evaluation delimitations outside the objective.
The thesis still states four clauses and a five-stage chain, and applies a four-clause score.
The two models cannot both stand: an examiner reading the contract section and the synthesis will see the breakdown and the book disagree on the thesis's central device.
**Evidence:**

The execution clause was never supported by an appended paper, so keeping it as a fourth clause promised evidence the thesis does not carry.
The same clause forced a five-stage chain, a five-row taxonomy, a four-clause score, and a fifth conclusion.
Removing it is not a wording fix: it changes the count in the contract, the figure, the tables, the abstract, the glossary and the conclusions.

- `thesis/chapters/03_background.tex:53`, `:57` and `:80` state four clauses and read four frameworks against them.
- `CLM-001` now fixes the claim sentence, the weakening and four named consequences verbatim, so the alignment keeps that wording and changes only the clause, stage and gap counts.
- `thesis/chapters/07_synthesis_and_discussion.tex:9` states five stages and calls execution a clause; `:73`, `:98`, `:106`, `:120`, `:178`, `:189` and `:191` repeat the four-clause model.
- `thesis/chapters/07_synthesis_and_discussion.tex:101` reports a score of two of four, and `:135` titles the taxonomy section "One taxonomy, four clauses".
- `thesis/chapters/05_methods.tex:26`, `thesis/chapters/08_conclusions_and_future_work.tex:15`, `thesis/chapters/02_introduction.tex:17`, `thesis/pre/abstract.tex:5` and `thesis/custom/glossary.tex:25-28` carry the same count.
- `tab:contract-applied`, `tab:taxonomy` and `tab:framework-coverage` carry execution columns or rows.
- `RQ-001` now prints the objective's three-property form, "standardized, machine-interoperable M&S metadata" making credibility "explicit, auditable and traceable", and the kappa carries the same sentence. Done 2026-11-05; the clause-count rows below stay open.
**Acceptance:**

- The contract section states three clauses and one delimitation paragraph for execution and evaluation; no fourth clause remains.
- `tab:contract-applied` has three clause rows and reports three recoverable clauses of three, with execution and evaluation reported as delimitations outside the count.
- `tab:taxonomy` aligns three gaps, three clauses and three chain stages; execution and evaluation are not clause rows.
- `fig:credibility-chain` draws three stages with the Paper I premise as a frame, not five.
- Chapter 7 carries four conclusions: the premise, definition, intended use and evidence; future work states the execution and evaluation delimitations and the doctoral directions that would bring them into the objective.
- The abstract, ch02, ch05, ch08 and the glossary use the same three-clause count.
- The introduction and abstract use the objective's wording: credibility is made explicit, auditable and traceable through standardized artifacts.
- No "four clauses", "execution clause", "two losses" or "five stages" remains in the thesis.
- The kappa build runs with no undefined citation; `pb check --strict` and `pb node-size --strict` pass.

Status 2026-11-05: the research-question wording is done, in `RQ-001` and in the kappa.
The application target moved to the in-repo case (`RES-005`, `IMP-039`), so `tab:contract-applied` and the ch07 application are rewritten to that case and not to the cited benchmark.
Still open: the three-clause count in ch03, ch05, ch07 and ch08, `tab:contract-applied`, `tab:taxonomy`, `tab:framework-coverage`, `fig:credibility-chain`, the abstract, the glossary, and the build gate.
**Out of scope:**

- New empirical work on execution or evaluation.
- Rewriting the appended papers.
- Renegotiating the claim's strength (`CLM-001`, `ARG-009`).