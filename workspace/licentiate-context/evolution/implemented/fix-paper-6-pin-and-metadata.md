---
id: IMP-004
type: imp
layer: evolution
home: evolution/implemented/fix-paper-6-pin-and-metadata.md
title: Fix Paper 6 pin and metadata
summary: Pin confirmed at the accepted manuscript; DOI waits on publication
date: 2026-11-04
status: implemented
---

# Fix Paper 6 pin and metadata

The Paper 6 submodule sits at `fe4c818` on branch `kappa`, carrying the LaTeX adapter (`IMP-009`); the accepted manuscript is tag `final-submission` at `05e2ae8`.
The pin descends from that tag and is an ancestor-safe superset: body sections and `references.bib` are unchanged, and the only manuscript-source change since the tag is the OpsCons plural fix in `main.tex` (`5e69546`).
That fix lives in the paper's own acronym block, which the kappa does not use; the kappa builds its acronym union from all paper sources.
**Evidence:**

The kappa cited a version nobody had confirmed as the accepted one.
A wrong pin would not fail the build, only the examination, and the stub carried no DOI with no published record yet.

- `git merge-base --is-ancestor final-submission HEAD` succeeds, and `git diff --stat final-submission..HEAD` shows `kappa/paper.tex`, the OpsCons line in `main.tex`, and three removed reference PDFs; `sections/` is untouched.
- `python3 build.py` at `fe4c818` builds 14 letter pages with 0 undefined citations or references.
- Crossref and OpenAlex returned no record for the title on 2026-10-30.
- `thesis/papers.bib` names `paper6_purpose_driven_modelling`.
**Acceptance:**

- The pin points at the accepted version, and the paper card records it as final.
- `paper6_purpose_driven_modelling` in `thesis/papers.bib` carries a DOI.
- The paper board records the citekey and DOI.
- The pinned commit builds the paper.
**Outcome:**

- The pin is `kappa@fe4c818`, 10 commits past `final-submission` `05e2ae8`, and is confirmed final for the kappa; it adds only the adapter, the OpsCons plural fix, and reference-PDF cleanup.
- The pinned commit builds the paper standalone: 14 pages, 0 undefined references.
- The kappa citekey is `paper6_purpose_driven_modelling`; `thesis/papers.bib` carries it with `pubstate = {inpress}`.
- No DOI exists yet: the paper is in press and neither Crossref nor OpenAlex has a record as of 2026-10-30; the DOI and published venue are tracked separately in `IMP-012`.
- The paper card and the board row record the confirmed pin and citekey, with DOI still pending.
**Out of scope:**

- Paper 6 content or layout (`IMP-002`).
- The paper build-rule table (`IMP-003`).
- The guarded appendix include (`IMP-005`).
- Pin mechanics for the other papers (`OPS-007`).

- Paper content and peer review outcome.
- Submodule update mechanics (`OPS-007`).
- Citation gate (`VER-003`).
- The DOI and venue assigned at publication (`IMP-012`).