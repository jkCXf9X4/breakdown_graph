---
id: IMP-029
type: imp
layer: evolution
home: evolution/selected/make-the-provenance-claims-true-or-remove-them.md
title: Make the provenance claims true or remove them
summary: The kappa states a provenance claim at three sites and in the artifact table;
  the word provenance never appears in Papers III/VI
date: 2026-11-11
status: selected
---

# Make the provenance claims true or remove them

The kappa claims provenance for claims and artifacts that the appended papers do not support: the word "provenance" never appears in Papers III/VI, so the claim is false as written.

**Evidence:**

- Patch-plan batch B2 (`review/patch-plan-batches.md:18`, R-004) removes the provenance claim from `04_research_questions_and_contributions.tex`, `05_methods.tex`, `07_synthesis_and_discussion.tex`.
- Patch-plan batch B5 (`review/patch-plan-batches.md:21`) makes the artifact table's provenance claim true in `05_methods.tex`.
- R-IDs R-004, R-010, R-076, R-162, R-163 are owned by this IMP (`patch-plan.md:25`).
- The provenance word appears at `04_research_questions_and_contributions.tex:78`, `05_methods.tex:62`, `07_synthesis_and_discussion.tex:112`, and in the artifact table.

**Change:**

- Each provenance claim is either backed by a paper that uses the word, or removed.
- The artifact table's provenance claim matches what the sources actually state.

**Risk:**

- Medium: removing a claim narrows a contribution; keeping it requires the papers to support it.
- Blast radius is three thesis chapters and the artifact table.

**Acceptance:**

- No provenance claim remains that the appended papers do not support, checked against the paper texts.
- `04_research_questions_and_contributions.tex:78`, `05_methods.tex:62` and `07_synthesis_and_discussion.tex:112` are either removed or cite a paper containing the claim.
- `python3 thesis/build.py` runs with 0 undefined citations.

**Out of scope:**

- Grounding unrelated load-bearing claims (`IMP-034`).