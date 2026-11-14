---
id: IMP-005
type: imp
layer: evolution
home: evolution/selected/papers-append-as-latex.md
title: Guarantee a build input for every appended paper
summary: All four appended papers are LaTeX adapters and the PDF staging step is gone,
  so nothing checks the four includes as a set
date: 2026-11-04
status: selected
---

# Guarantee a build input for every appended paper

The four appended papers are absorbed as LaTeX through `\includearticle` inside the `papers` environment (`thesis/thesis.tex:47-55`).
Paper I is typeset from its own repository like the other three; no paper ships as a facsimile PDF (`MS-012`).
`thesis/appendices/` is therefore empty and stays empty: it existed for staged PDFs, and none is staged now (`OPS-001:23`).
A missing adapter fails the LaTeX run, but nothing checks the four includes as a set before the build starts, so a dropped include is caught only as a compile error.
The include site is the paper block plus `thesis/paper-appendices.tex`, which inputs the two book-level supplements (`OPS-001:18`).
**Evidence:**

An appendix that silently loses a paper produces a deliverable that looks complete.
The appendix is the evidence half of the thesis, so a missing paper is a missing answer, not a missing page.

- `thesis/thesis.tex:47-55` holds four `\includearticle` lines with no guard around them.
- `ls thesis/appendices/` returns nothing.
- `OPS-001:23-24` records the empty folder and names the paper block as the appendix site.
- `VER-002:13` gives 184 pages for the built book; the sum of the four paper page counts is recorded nowhere.
**Acceptance:**

- Each of the four appended papers resolves to an adapter at build time, and `OPS-001` names the adapter and the include block.
- A missing or renamed adapter fails the build with the paper named, rather than a silent omission.
- The include site is one block, and `OPS-001` names it correctly together with `paper-appendices.tex`.
- Appendix page count equals the sum of the four included paper page counts, and the figure is recorded in `VER-002`.
**Out of scope:**

- Which form each paper ships in (`MS-012`).
- The paper build-rule table and its soft-fail column (`IMP-003`).
- Paper pin and metadata (`IMP-004`).

- Paper build rules (`IMP-003`).
- Build gate acceptance (`VER-002`).