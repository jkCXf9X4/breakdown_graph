---
id: MS-010
type: manuscript
layer: manuscript
home: manuscript/front-matter.md
title: What does the front matter deliver?
summary: Sammanfattning, Abstract, Acknowledgments, Included Papers, contents and
  lists, in a fixed order before the numbered chapters
date: 2026-11-11
status: current
---

# What does the front matter deliver?

The front matter opens the book and fixes what the reader meets before the argument starts.

- **Purpose:** carry the abstract, the Swedish popular-science summary, the acknowledgments and the Included Papers list before the chapters.
- **Order:** Sammanfattning, Abstract, Acknowledgments, Included Papers, Contents, List of Figures, List of Tables, Terminology, Acronyms (`MS-013`).
- **Sources:** `thesis/pre/abstract.tex`, `thesis/pre/sammanfattning.tex`, `thesis/pre/acknowledgments.tex`, `thesis/pre/list_of_papers.tex`; the class inputs the first three at `liuthesis.cls:154-156` and the papers list at `liuthesis.cls:158` (`OPS-001`).
- **Included Papers:** the list's content contract is `MS-013`; each entry must carry the full author list, title, venue, year, status and DOI where assigned (`R-011`).
- **Abstract:** 250–300 words, introduces no claim the claims layer does not have (`OPS-011`).
- **Sammanfattning:** a popular-science summary of about one page, a faithful equivalent of the abstract (`OPS-011`, `IMP-026`).
- **Artifact anchors:** `thesis/pre/abstract.tex`, `thesis/pre/sammanfattning.tex`, `thesis/pre/acknowledgments.tex`, `thesis/pre/list_of_papers.tex`.