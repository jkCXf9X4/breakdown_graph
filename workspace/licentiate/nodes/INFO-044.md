---
id: INFO-044
type: info
layer: evolution
home: evolution/investigations/review-2026-11/patch-plan.md
title: Kappa review 2026-11 — patch plan
summary: Dependency-ordered waves, R-ID ownership and author decisions that sequence
  the 15 review IMPs into commits
date: 2026-11-01
status: current
---

# Kappa review 2026-11 — patch plan

This leaf sequences the review's open work; findings are `INFO-029`, the ranking `INFO-030` and
`INFO-043`, the work `IMP-020`–`IMP-034`. New here is only the order, the R-ID ownership and what
only the author can decide; batches, commit messages and verification are `INFO-045`.

## Order, and the R-IDs each IMP owns

Waves are ordered by what blocks what, not by severity. Where two IMPs touch one R-ID the owner is
the one whose acceptance criteria name the fix; R-IDs come from each IMP's body and `INFO-030`.
WAVE 0 — decisions, no prose edits. `IMP-021` R-003, R-027 (1 BLOCKER, 1 MAJOR, 3 h) gates
everything: if the contract must be derived, ch03 and ch07 need a derivation written and
`IMP-032`'s reordering changes shape. `IMP-022` R-002, R-068, R-135, R-138, R-139 (1 BLOCKER,
4 MAJOR, 1 h) gates `IMP-023` and `IMP-017`, both of which presuppose an instrument.
WAVE 1 — truth repairs, independent of each other and of WAVE 0. `IMP-020` R-005, R-006, R-042,
R-057, R-185 (2 BLOCKER, 3 MAJOR, 1.25 h); `IMP-029` R-004, R-010, R-076, R-162, R-163 (2 BLOCKER,
3 MAJOR, 1.25 h); `IMP-025` R-011, R-110, R-111, R-115 (1 BLOCKER, 3 MAJOR, 2 h); `IMP-034` R-020,
R-047, R-048, R-049, R-050, R-067, R-083, R-143, R-181 (9 MAJOR, 3 h); `IMP-026` R-012, R-106,
R-107 (1 BLOCKER, 2 MAJOR, 1.25 h).
WAVE 2 — structural, after WAVE 0. `IMP-032` R-001, R-007, R-008, R-078, R-151 (3 BLOCKER,
2 MAJOR, 4 h) is the highest-value fix: it makes the author's red line true, since `04:84` defers
the claim and it first appears at `07:5`. Then `IMP-033` R-085, R-090, R-092, R-096, R-147
(5 MAJOR, 1.5 h), `IMP-031` R-101, R-125, R-126, R-128, R-146, R-150 (6 MAJOR, 2 h) and `IMP-024`
R-073, R-074, R-153, R-154 (4 MAJOR, 2 h).
WAVE 3 — consequential. `IMP-027` R-089, R-093, R-105, R-168, R-169 (5 MAJOR, 2 h); `IMP-028`
R-009, R-121, R-122, R-173 (1 BLOCKER, 3 MAJOR, 1.5 h); `IMP-023` R-088, R-094 (2 MAJOR, 2 h).
WAVE 4 — tooling, independent of the thesis. `IMP-030` R-211 (1 NOTE, 1 h).
Any order: `IMP-020`, `IMP-025`, `IMP-026`, `IMP-029`, `IMP-030`, `IMP-034`. Hard-blocked:
`IMP-023`, `IMP-027`, `IMP-031`, `IMP-032`, `IMP-033`. R-004 and R-012 had no owning IMP; they fold
into `IMP-029` and `IMP-026`.

## Decisions only the author can make

- **`IMP-021` derived or stipulated?** **Stipulated.** `03:80` already says "a requirement of the contract, not an existing standard" and the audit graded it DEFINITIONAL; deriving it would make the contract a result of six papers written before it existed.
- **`IMP-022` checklist, score, or diagnostic?** **Diagnostic.** The only option that keeps `07:66-99` (the one original instrument, R-191) and the glossary's "satisfied or not satisfied" both true, and it is what `07:174` already claims.
- **`IMP-023` run the contract on Paper VI, and is 2/4 publishable?** **Run it.** A rubric returning 2/4 on every input is a description, and the examiner will ask; if Paper VI also returns 2/4, that is a finding, not a failure.
- **`IMP-024` are SQ1 and SQ5 premise and instrument rather than parts?** **Reclassify.** The "parts" claim becomes true for four of six and the primary question is untouched; `ARG-001` already calls step 1 the premise that "carries no clause".
- **`IMP-025` the authoritative venue record for Papers I/III/IV/V/VI?** **The DOI landing page where a DOI exists** (I–V all have one in `papers.bib`), and "submitted" for VI, whose `@misc` entry has no venue field.

## Owns

- The dependency order: which IMP blocks which, and which may land in any order.
- Which R-IDs each IMP owns, and the author decisions the order depends on.
## Excludes

- `INFO-045` for the fourteen commit batches, messages and file:line verification.
- `INFO-029` for the rows themselves; `INFO-030` and `INFO-043` for the ranking.
- `IMP-020`–`IMP-035` for the work itself; `CLM-001` and `INFO-035` for the claim and what must not break.
- `OPS-001`, `OPS-003`–`OPS-005`, `VER-001`–`VER-004`, `ARG-004` for the thesis text and gates the batches edit.
