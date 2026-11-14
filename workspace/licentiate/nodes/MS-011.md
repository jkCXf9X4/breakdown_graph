---
id: MS-011
type: manuscript
layer: manuscript
home: manuscript/appendices.md
title: What do the appendices deliver?
summary: The four appended papers, the paper supplements A and B, the case appendix,
  and the one closing bibliography
date: 2026-11-11
status: current
---

# What do the appendices deliver?

The back matter carries the appended papers and the supplementary material, and closes the book with one bibliography.

- **Purpose:** print the four appended papers after the Conclusions chapter (`MS-008`) and the kappa material that belongs with them, then the one reference list.
- **Papers:** four papers follow the Conclusions chapter (`MS-008`), each printing its own headings under the shared float and listing layout (`OPS-002`); the form each ships in is `MS-012`.
- **Supplements:** material belonging to one paper follows the four papers as book-level appendices before the bibliography: Appendix A is Paper II's SRMD example, Appendix B is Paper III's workflow listings; both are input by `thesis/paper-appendices.tex` (`OPS-001`).
- **Case appendix:** `thesis/appendices/case.tex` prints the case appendix (`app:case`) after the paper supplements: what the in-repo case contains, its artifact set, and its regeneration command, documenting what the Synthesis chapter argues (`MS-007`).
- **Closing:** one bibliography closes the book (`OPS-004`); the appendix page budget is `IMP-008`.
- **Artifact anchors:** `thesis/appendices/case.tex#app:case`, `thesis/paper-appendices.tex`, `thesis/thesis.tex`.