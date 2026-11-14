---
id: MS-013
type: manuscript
layer: manuscript
home: manuscript/included-papers.md
title: Included papers
summary: One Included Papers list naming all four papers, before the table of contents
date: 2026-11-11
status: current
---

# Included papers

The book prints one Included Papers list, and the list is part of the deliverable.

- **Contract:** a listed paper that is absent, or an examined paper that is not listed, breaks the deliverable.
- **Entries:** four, numbered I–IV in paper-number order.
- **Case:** the in-repo case is kappa material, not a publication, so it carries no entry here (`RES-005`).
- **Fields:** each entry carries the full author list, title, venue, year, status, and DOI where assigned.
- **Authority:** identity and status come from `RES-001` to `RES-004`; this leaf fixes presence, content, and completeness only.
- **Pointer:** each entry names its paper number, and the appendix prints the papers in that order.
- **Placement:** the list sits before the table of contents (`MS-010`).

**Owns:**

- Presence of the Included Papers list in the shipped book.
- The content contract of one entry: which fields make it complete.
- That every examined paper is listed and every listed paper is examined.

**Excludes:**

- `MS-010` the front-matter order and where each element is printed.
- `RES-001` to `RES-004` paper identity, status, and the values the entries carry.
- `OPS-010` venue, DOI, and publication metadata upkeep.
- `IMP-012` the Paper IV DOI and venue, and `IMP-025` the venue and status provenance, both still open.
- `IMP-008` the appendix page budget.
- `OPS-001` the LaTeX section that prints the list.