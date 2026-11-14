---
id: MS-003
type: manuscript
layer: manuscript
home: manuscript/sections/background.md
title: What does the Background chapter deliver?
summary: Simulation, CPS, standardized interfaces, the credibility contract, V&V,
  co-simulation, and the framework-coverage tables
date: 2026-11-11
status: current
---

# What does the Background chapter deliver?

The background supplies the external facts and the credibility contract the argument builds on, in two halves with a closing summary.

- **Purpose:** ground the argument in the literature and standards, state the credibility contract as an argument step, and survey the frameworks the thesis positions itself against.
- **First half:** Cyber-Physical Systems and simulation; Standardized interfaces and system composition; Credibility, intended use, and the contract; Structured verification and validation at scale.
- **Second half:** Continuous development and integration; Simulation complexity drivers; Model exploration and interface-level uncertainty; Co-simulation and orchestration; a closing summary.
- **Contract subsection:** "What the frameworks already contain" sits under Credibility, intended use, and the contract; the stance it takes is `MS-015`'s.
- **Co-simulation text:** one paragraph under Co-simulation and orchestration, no subsections: execution settings change the dynamics of a composed system, the composition artifact carries no slot for them, and mechanism detail is cited rather than surveyed.
- **Tables:** the merged credibility-scales table and `tab:framework-coverage`, which reads four frameworks against the three clauses (`MS-014`).
- **Literature:** `LIT-001`, `LIT-002`, `LIT-003`, `LIT-004`, `LIT-005` own the external facts the chapter presents.
- **Claims:** the contract definition (`ARG-006`) and the three-clause partition must be stated before the framework table reads them (`IMP-032`); the framework claims must match the primary texts (`IMP-020`).
- **Artifact anchors:** `thesis/chapters/03_background.tex#ch:background`, `thesis/chapters/03_background.tex#sec:framework-coverage`, `thesis/chapters/03_background.tex#tab:framework-coverage`, `thesis/tables/credibility_scales.tex#tab:credibility_scales`.