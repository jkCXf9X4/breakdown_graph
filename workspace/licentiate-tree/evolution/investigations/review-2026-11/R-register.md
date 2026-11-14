---
id: INFO-029
type: info
layer: evolution
home: evolution/investigations/review-2026-11/R-register.md
title: Kappa review — R-register
summary: Severity key, crosswalk and re-gradings for the 212 R-IDs; the rows themselves
  are split by severity and chapter
date: 2026-11-01
status: current
---

# Kappa review — R-register

The severity key, crosswalk and re-gradings behind `INFO-028`; the rows are `INFO-030` to
`INFO-042` and this leaf holds what they share. One row per defect, not per finding: where two
audits reported the same defect, the row carries both source IDs and the crosswalk records the
fold. `PM-n` numbers `prematter-check.md`; `LA` cites the 61-row `library-audit.md` as a unit.

## Severity key
- **BLOCKER** — the central claim is unsupported, self-contradictory, or unreadable as written; an examiner stops here.
- **MAJOR** — a claim exceeds its evidence, a structural promise is broken, or a section does not do its job.
- **MINOR** — local inaccuracy, terminology drift, redundancy.
- **NOTE** — verified-good (protect it) or cosmetic.

Counts: 12 BLOCKER, 161 MAJOR, 12 MINOR, 27 NOTE. **Known inconsistency, not hidden:** 58 of
the 161 MAJOR rows were graded MINOR by the audit that found them, 54 of those 20-minute fixes
or shorter; they were grouped by *subject* rather than re-sorted by grade.

## Crosswalk — R-ID to source finding IDs
Each R-ID in the detail leaves carries its source IDs in the last column; this table records
only the folds.

| R-ID | Folded source IDs | Why one defect |
|---|---|---|
| R-001 | SF-S-01, SF-S-02, SB-S-16 | Three witnesses to one failure: the contract is never introduced as an argument step. SF-S-01 is the pointer to a glossary, SF-S-02 the use-before-statement, SB-S-16 the definition living in a glossary. |
| R-002 | CS-F-05, CS-F-31, SF-S-21 | The score contradiction, seen from ch07's own text (F-05, F-31) and from the glossary (S-21). One defect, two witnesses. |
| R-004 | RM-F-35, RM-F-90, RM-F-72, CS-F-37 | One provenance overclaim at four sites. RM-F-35 is ch04 C3, RM-F-90 the ch04-vs-ch07 divergence, RM-F-72 the `tab:evidence-base` row, CS-F-37 the `tab:paper-roles` cell. |
| R-007 | SF-S-10, SF-S-12, RM-F-46 | The enumeration arithmetic and the missing gap column are one defect: the table that should resolve the confusion does not carry the enumerations that need resolving. |
| R-008 | SF-S-13, PM-2, CS-F-34 | The thesis-level contribution is undeclared in ch04, in the abstract, and in ch07's own accounting. |
| R-071 | CP-F403, RM-F-36, RM-F-91 | Paper IV "performance" overstatement at three sites: ch06:22, ch04 C4, and the ch04-vs-ch07 divergence. |
| R-072 | CP-F503, RM-F-37, RM-F-92, RM-F-69, RM-F-78 | Paper V "reproducible"/"benchmarking" at three sites plus the two `tab:evidence-base` promise breaches it causes. |
| R-096 | SB-S-07, SF-S-12 | The paper→chain mapping triplication and the missing gap column are related but distinct: S-07 is redundancy across three chapters, S-12 is a missing column in one table. Both kept. |
| R-005, R-006 | CIB-F-C15, CIB-F-C43 | Kept separate from SF-S-23: the false universals are grounding failures, SF-S-23 is an ordering failure (novelty claim made before the contract is stated). Cross-referenced, not merged. |
| R-078 | SF-S-04, SF-S-23 | The three-jobs-in-one-section defect and the novelty-claim-in-a-survey-subsection defect are the same section; R-078 carries the split, and SF-S-23's retitling is part of it. |

## Severity re-gradings
Three findings were re-graded from the source audits; each is reported, not silently changed.

| Source | Audit severity | This record | Why |
|---|---|---|---|
| RM-F-03 (`04:9` "drift from its defining architecture", NOT-FOUND in both sources) | BLOCKER | MAJOR (R-057) | A framing sentence with a mis-pointed citation. The claim itself is true and Paper VI supports it; an examiner would not stop, but the citation must be fixed. |
| CP-F501 (`papers.bib:1-4` false title comment) | BLOCKER | MAJOR (R-110) | The comment is not printed in the thesis. It actively misleads a future reader, which is serious, but it cannot stop an examiner reading the PDF. |
| SB-S-14 vs RM-F-79 (ch05:90 vs ch07:66-99) | MAJOR (SB) vs SUPPORTED (RM) | MAJOR (R-091 note) | The audits contradict, and this is the only genuine contradiction between them. RM-F-79 is better evidenced: ch07:69 says "No experiment is run and no evidence is created", so ch05:90's substance is consistent. SB-S-14 is right that the *wording* reads as a denial of ch07's central move. Resolution: a wording defect, not a substantive contradiction. |

## Owns
- The severity key, the count line and the re-gradings.
- The crosswalk recording every fold of one defect reported by two or more audits.
## Excludes
- `INFO-030`–`INFO-042` for the finding rows themselves, including every location.
- `INFO-028` for the consolidated index and read order; `INFO-043` for the verdict and top ten.
- `IMP-020`–`IMP-035` for the repairs each row implies.
- `OPS-001`, `OPS-003`–`OPS-005`, `VER-001`–`VER-004`, `ARG-004` for the thesis text and gates under review, not the finding.
