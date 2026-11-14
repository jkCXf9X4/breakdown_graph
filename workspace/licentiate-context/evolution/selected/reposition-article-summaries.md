---
id: IMP-042
type: imp
layer: evolution
home: evolution/selected/reposition-article-summaries.md
title: Reposition papers/article_summaries.md as a paper-local pointer
summary: The quick-reference restates thesis-facing paper facts the breakdown now
  owns; it must shrink to paper-local metadata and route thesis facts to RES-*, ARG-*,
  glossary and IMPs by ID
date: 2026-11-11
status: selected
---

# Reposition papers/article_summaries.md as a paper-local pointer

`papers/article_summaries.md` predates the evidence layer and `task.md`; its thesis-facing fields now duplicate state the breakdown owns, so edits must stay in sync across two homes.

**Evidence:**

- "Core contribution", "Key results" and "How it supports the thesis" restate what `RES-001`–`RES-004` and `ARG-003` own (`docs/breakdown/evidence/results/paper-*.md`).
- "Key terms (normalize these in the kappa)" duplicates the terminology authority `thesis/custom/glossary.tex` and `ARG-008`.
- "Open issues / next steps (use for task.md)" names `task.md`, which no longer exists (AGENTS.md § Repository map); open work lives in `evolution/selected/`.
- The header lists all six paper repos as "included papers"; the kappa appends Papers I–IV only, and `2026_temporal` (`papers/2026_temporal`) + `2026_co_sim` (`papers/2026_co_sim`) left the compilation and are no longer cited in the kappa body.

**Change:**

- Shrink `papers/article_summaries.md` to paper-local metadata: identity, venue, source paths, the paper's own research questions, reproducibility/DOI pointers, and an explicit `id`-route to the owning leaves — no restated thesis facts.
- Mark `2026_temporal` and `2026_co_sim` as excluded from the compilation.
- Drop every reference to `task.md`.

**Risk:**

- Low: the file is a convenience surface, not a gate; agents lose the quick facts, so the file must cite the owning leaves hard rather than summarize them softly.

**Acceptance:**

- Every thesis-facing fact is deleted or replaced by a backticked `id` citation to its owning leaf.
- No field names `task.md`.
- The two non-included papers are marked excluded.
- `pb check --strict` and `pb node-size --strict` pass; `pb registers` lists the IMP in `selected/INDEX.md`.

**Out of scope:**

- Rewriting the paper submodules (`papers/*/kappa/paper.tex`).
- The paper-to-chain mapping triplication (`IMP-033`).
- Repointing archived decision states (`IMP-035`).
