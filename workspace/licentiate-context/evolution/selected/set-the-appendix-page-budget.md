---
id: IMP-008
type: imp
layer: evolution
home: evolution/selected/set-the-appendix-page-budget.md
title: Set the appendix page budget
summary: The appendix runs four papers at 184 pages; no budget or format ceiling has
  been stated for the smaller book
date: 2026-11-04
status: selected
---

# Set the appendix page budget

Papers I-IV enter the appendix as LaTeX bodies set in the thesis type, two columns at `\small` (`OPS-002`, `OPS-001`).
The four-paper build produces 184 pages and 5492446 bytes at the recorded pins (`VER-002:13`).
The earlier measurement described a six-paper book: 56 appendix pages over 40 facsimile pages, closing at 193.
The growth is typography, not content: a narrower measure and larger leading applied to bodies written for two-column or other sizes.
`OPS-011` states format, length, and authorship obligations but no page ceiling, so the budget is a judgement about examiner expectation, not a rule check.
**Evidence:**

An appendix that grows the imported papers competes with the kappa narrative for the examiner's attention.
The page cost was measured once, for a book that no longer exists, so the current book has no recorded budget.

- `VER-002:13` records 184 pages and 5492446 bytes for the four-paper book.
- `OPS-002:16` records the two-column `\small` setting the page count follows from.
- `VER-002:22` records the three tolerated overfull hboxes.
- `OPS-011:14-19` lists the examiner's obligations and names no page bound.
**Acceptance:**

Two options; the smaller-size one is taken, the accept-as-is one stays open.

- Accept the thesis typography as is. Does a 184-page document meet faculty format rules and examiner expectations? Done when the answer is recorded and `VER-002` keeps 184 as its reference page count.
- Set the imported bodies at a smaller size. The papers already run two-column at `\small` (`OPS-002`); reclaiming more pages would need a smaller size still.
- Either way `VER-002` carries the resulting page count, the per-paper split, and the overfull tolerance.
**Out of scope:**

- Converting Paper I to a facsimile: its retypeset body is the shipped form (`MS-012`).
- Redoing the migration for content reasons; the bodies are landed and compile (`IMP-002`).
- Restyling the paper figures beyond the house-style widths already applied (`OPS-002`).

- Which form each paper ships in (`MS-012`).
- Paper block mechanics and adapters (`OPS-001`).
- Build gate reference count and evidence (`VER-002`).
- The shared house style itself (`OPS-002`).