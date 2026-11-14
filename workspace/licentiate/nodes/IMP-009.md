---
id: IMP-009
type: imp
layer: evolution
home: evolution/implemented/import-paper-6-as-latex.md
title: Import Paper VI as LaTeX inside the kappa
summary: Paper VI now imports as LaTeX; a multi-letter column type name caused the
  table abort
date: 2026-11-04
status: implemented
---

# Import Paper VI as LaTeX inside the kappa

Paper VI entered the appendix as a PDF built from its own source, not as imported LaTeX (`MS-012`).
Inside the kappa document, LaTeX aborted at the first table of `sections/04_implementation.tex` with `Missing number, treated as zero`.
On plain `tabular` the same table failed with `Package array Error: Empty preamble: 'l' used`.
Every later tabular in the run failed too.
**Root cause:**

- `array`'s `\newcolumntype` appends `\NC@do#1` to `\NC@list` (`array.sty:249`, `array.sty:260`).
- `\NC@do` takes one undelimited token, so a column-type name longer than one character silently splits.
- `\newcolumntype{pSixA}[1]{...}` defines `\NC@do p` and leaks the letters `SixA`.
- `\NC@find@p` then matches at once with an empty preamble fragment, and `\@mkpream` loops over nothing.
- Inside `tabularx` the same corruption surfaces as `Missing number, treated as zero` at `\end{tabularx}`.
- Reproduced outside the thesis: plain `article`, `\newcolumntype{Zz}[1]{p{#1}}`, then `\begin{tabular}{ll}` gives the empty-preamble error; a one-letter name compiles.
- Rule for the tree: column-type names must be a single character (`OPS-005`).
**Outcome:**

- Paper VI imports as LaTeX and the kappa builds green (186 pages, `VER-002`).
- The adapter is `papers/2026_purpose_driven_modelling/kappa/paper.tex`, submodule commit `2fd41d3` on branch `kappa`.
- It is reached through the shim `thesis/papers/paper6_purpose_driven_modelling.tex`.
- `thesis/thesis.tex` includes it with `\includearticletex{paper6_purpose_driven_modelling}`.
- The adapter is a self-contained snapshot of the paper's `sections/`, with `\begingroup`, `\graphicspath` to the paper root, `pSix*` local macros, headings demoted one level, and labels and refs prefixed `p6:`.
- The paper's own `A` column type is re-declared under that single letter inside the adapter's group.
- The three tables keep their original `tabularx` column specs and verbatim cells.
- The Acknowledgments stay.
- Abstract, title, authors, INCOSE block, keywords, `multicols*`, `\newacronym`, per-paper bibliography, and biographies are dropped.
- `thesis/build.py` no longer builds or stages any Paper 6 PDF.
- Parent commits: `b320f06` imports the paper, `896aad8` updates the README and drops the variant; the variant `kappa/main.tex` went at submodule commit `9252042`, with nothing building it.
- The paper keeps building standalone with its own `python3 build.py`.
- Paper VI occupies 16 appendix pages where the PDF took 14; the book went from 181 to 186 pages.
- The printed bibliography holds 173 entries instead of 145, because Paper VI's citations now run in the LaTeX job.
**Out of scope:**

- Restyling Paper VI content for the thesis type.
- Changing the Paper VI pin or metadata (`IMP-004`).
- The other imported papers, already landed (`IMP-002`).
- The appendix page budget (`IMP-008`).

- Which form each paper ships in (`MS-012`).
- Paper staging and adapter mechanics (`OPS-001`, `OPS-005`).
- Build gate reference count and evidence (`VER-002`).
- The appendix page budget (`IMP-008`).