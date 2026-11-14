---
id: IMP-028
type: imp
layer: evolution
home: evolution/selected/restore-the-appendix-chapter-furniture-and-reachability.md
title: Restore the appendix chapter furniture and reachability
summary: The appendix's chapter style, even-page running head and appendix letters
  are lost; the appendix is not reachable from the front matter
date: 2026-11-11
status: selected
---

# Restore the appendix chapter furniture and reachability

The appendix chapter no longer prints with its intended chapter furniture, and it is not reachable from the front-matter lists. The `\chapterstyle{VZ43}` restore and the `\makeevenhead` reset are missing, and the appendix letters do not render.

**Evidence:**

- `evolution/selected/settle-the-appendix-typographic-residuals.md:51` excludes the appendix's chapter furniture, running head and reachability to this IMP.
- Patch-plan batch B11 (`review/patch-plan-batches.md:27`) touches `paper-appendices.tex`, `liuthesis.cls`, `06_summary_of_papers.tex`, `pre/list_of_papers.tex`.
- R-IDs R-009, R-121, R-122, R-173 are owned by this IMP (`patch-plan.md:34`); the R-009 fix goes at `:14`, between `\appendix` at `:11` and the first `\chapter` at `:15` (`patch-plan-batches.md:50`).

**Change:**

- `\chapterstyle{VZ43}` is restored for the appendix and `\makeevenhead` is reset.
- The appendix chapters render lettered (appendix letters) and are reachable from `pre/list_of_papers.tex` and `06_summary_of_papers.tex`.

**Risk:**

- Medium: `liuthesis.cls` is class-level; a wrong edit affects the whole book.
- Blast radius is the appendix build and the class file; the build gate catches regressions.

**Acceptance:**

- The appendix opens with `\chapterstyle{VZ43}` and the even-page running head matches the intended form.
- Appendix chapters print with the letter scheme and appear in the list of papers.
- `python3 thesis/build.py` runs with 0 undefined citations and no undefined references.

**Out of scope:**

- The typographic residuals inside the papers (`IMP-011`).
- The appendix page budget (`IMP-008`).