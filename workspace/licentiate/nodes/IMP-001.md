---
id: IMP-001
type: imp
layer: evolution
home: evolution/implemented/fill-the-remaining-citation-markers.md
title: Fill the remaining citation markers
summary: All 101 markers are gone; 53 library keys and paper pointers replaced them
date: 2026-11-04
status: implemented
---

# Fill the remaining citation markers

The kappa carried `[CN]` markers where a claim ran with no source behind it.
At the start of the 2026-10-30 pass the count was 101 occurrences on 47 lines: 42 in `03_background`, 25 in `06_summary_of_papers`, 11 in `02_introduction`, 8 in `04_research_questions_and_contributions`, 7 in `08_conclusions_and_future_work`, 4 in `05_methods`, and 4 in `pre/abstract.tex`.
The earlier count of 50 lines was stale and understated the work.
The count is now 0.
**How each marker was closed:**

- Paper claims in `06_summary_of_papers` and the contribution list in `04_research_questions_and_contributions` were repointed, not re-cited: each now names the paper result by `\Cref{pN:...}` (`ARG-004`).
- Conclusions in `08_conclusions_and_future_work` were consolidated to five clause-level statements, each carrying its paper pointer; their trailing markers were dropped because the pointer is the support.
- Literature claims in `02_introduction`, `03_background` and `05_methods` were grounded in library documents and cited.
- The abstract was rewritten without citations: an abstract claims, the body supports (`VER-003`).
**Evidence:**

- `grep -o '\[CN\]'` over `thesis/chapters`, `thesis/tables` and `thesis/pre` returns nothing.
- `thesis/references.yml` grew from 8 to 61 keys; `./thesis/references.sh check` reports all 61 listed and the bib up to date.
- Every key resolves to a library document with extracted text (`OPS-004`).
- The build is green at 204 pages with the three tolerated paper-level overfulls (`VER-002`).
**Acceptance:**

- Zero markers, met.
- Every replacement names a key in `thesis/references.yml`, met.
- Every new key resolves to a library record with text, met.
**Out of scope:**

- The citation gate (`VER-003`) and bibliography generation (`OPS-004`).
- Wording of the claims the citations attach to.
- Reference intake mechanics and store pinning (`OPS-008`).
- The textless standards still awaiting a PDF (`IMP-016`).