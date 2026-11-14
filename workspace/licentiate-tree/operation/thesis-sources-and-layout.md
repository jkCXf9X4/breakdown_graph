---
id: OPS-001
type: operation
layer: operation
home: operation/thesis-sources-and-layout.md
title: Thesis sources and layout
summary: Where each kappa section lives in the LaTeX tree
date: 2026-11-11
status: current
---

# Thesis sources and layout

Kappa sources live under `thesis/`; the document class comes from the `template` submodule.
`thesis/thesis.tex` is the single entry point for the whole document.

- **Entry point:** `thesis/thesis.tex` loads the class, preamble, chapters, bibliography, and appended papers; line 1 sets `\documentclass[lic,lith,english,ccby]{liuthesis}`.
- **Class and styles:** `thesis/liuthesis.cls` is the class file delivered by the `template` submodule; `thesis/hyperpdfx.sty` is the thesis-local style file.
- **Preamble inputs:** `settings.tex` at line 2, `custom/commands.tex` at line 26, `custom/glossary.tex` and `custom/acronyms.tex` at lines 27-28 (`OPS-003`), `custom/papers-import.tex` at line 29.
- **Back matter:** `paper-appendices.tex` is input at line 59, after the paper block and before the bibliography; `\printbibliography` sits at line 63.
- **Chapters:** nine files live in `thesis/chapters/`, `01_terminology` through `09_author_contributions`; the section contract and their order are `MS-001` to `MS-009`.
- **Terminology chapters:** `01_terminology.tex` holds two unnumbered chapters, "Terminology" and "Acronyms"; both enter the table of contents with running heads and consume no chapter number.
- **Supporting trees:** `thesis/tables/` holds `credibility_scales.tex`, input at `chapters/03_background.tex:49`; `thesis/figures/` holds `design_workflow.dot` with its rendered `design_workflow.pdf`, `graphviz (3).svg`, and `improvement.drawio.svg`.
- **Pre-matter:** `thesis/pre/` holds `abstract.tex`, `sammanfattning.tex`, `acknowledgments.tex`, and `list_of_papers.tex`; the class inputs the first three at `liuthesis.cls:154-156` and the papers list at `liuthesis.cls:158`.
- **Appendices:** `thesis/appendices/` is empty; papers append through the `papers` environment instead.
- **Paper block:** `thesis/thesis.tex:47-55` opens `\begin{papers}` and enters the four papers; `thesis/paper-appendices.tex` holds the book-level appendix A/B after them.
- **Bibliographies on disk:** `thesis/references.bib` and `thesis/papers.bib` sit at the top of `thesis/`; their generation and use are `OPS-004`.
- **Shims:** `thesis/papers/` holds four `.tex` shims, one per appended paper, each inputting `kappa/paper.tex` from its submodule; no other paper has a shim (`INT-002`). Paper IV's is `thesis/papers/paper4_purpose_driven_modelling.tex` and its adapter is `OPS-005`.
- **Paper appendices:** they live next to the adapter as `kappa/appendix.tex`; `paper-appendices.tex` inputs the two files directly.
- **Paper III setup:** `kappa/listing-setup.tex` is shared by its adapter and its appendix so the appendix still resolves `pThreeXML`.
- **Adapter body:** an adapter carries no preamble, front matter, acronym definitions, or bibliography command.
- **`\includearticletex`:** defined at `thesis/liuthesis.cls:499`; it prints a title page, steps the article counter before the cover page so no cover marker prints empty, and inputs `papers/<citekey>`.
- **Two-column switch:** it opens one column for the cover page and chapter head, switches to `\twocolumn` at `\small` for the body, and returns to `\onecolumn` for the next cover, the paper appendices, and the book bibliography.
- **Counters:** it sets `secnumdepth` 3 inside a group per paper, redefines `\thesubsection`, `\thesubsubsection`, and `\thealgocf` with the `\thearticle` prefix, and resets figure, table, equation, footnote, `lstlisting`, `listing`, and `algocf` per paper.
- **Macro omissions:** it opens no `refsection` and prints no bibliography.
- **Label prefixes:** adapter headings sit one level down; labels and macros carry a `p1:`, `p2:`, `p3:`, or `p6:` prefix.
- **Appendix label prefix:** the surviving appendix keeps the `p6:` prefix, because its labels come from the paper submodule's adapter and cannot be renamed without re-pinning that submodule.
- **Build output:** `thesis/temp/` receives all build output.

**Owns:**

- The file inventory of the kappa LaTeX tree and the role of each path.
- The paper block, shim, and adapter wiring, and the `\includearticletex` behaviour.

**Excludes:**

- Section contract, chapter titles, and front-matter order: `MS-001` to `MS-011`.
- Paper build, staging, pins, and the Paper IV adapter: `OPS-005`.
- Glossary and acronym sources and generation: `OPS-003`.
- Bibliography rendering and the single printed list: `OPS-004`.
- The paper house style, column types, and numbering format: `OPS-002`.
- What the kappa must state: `MS-015`.