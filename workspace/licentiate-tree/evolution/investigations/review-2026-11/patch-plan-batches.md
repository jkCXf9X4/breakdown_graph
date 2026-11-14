---
id: INFO-045
type: info
layer: evolution
home: evolution/investigations/review-2026-11/patch-plan-batches.md
title: Kappa review 2026-11 — patch plan batches and verification
summary: The fourteen commit batches with files, gates and messages, and the file:line
  verification of all 12 blockers and 10 top-ten rows
date: 2026-11-01
status: current
---

# Kappa review 2026-11 — patch plan, batches and verification

The detail behind `INFO-044`: one commit per batch, and the verification of the review's file:line claims. `pb` = both gates; `build` = `python3 thesis/build.py` with 0 undefined citations.

## The batches
| # | Closes | Files | Gate | Message |
|---|---|---|---|---|
| B1 | `IMP-021`, `IMP-022` | `03_background.tex`, `07_synthesis_and_discussion.tex`, `custom/glossary.tex` | pb + build | `Settle what the credibility contract is and stop calling it a score` |
| B2 | R-004 (`IMP-029`) | `04_research_questions_and_contributions.tex`, `05_methods.tex`, `07_synthesis_and_discussion.tex` | pb + build | `Remove the provenance claim from all three sites` |
| B3 | R-012 (`IMP-026`) | `pre/acknowledgments.tex` | pb + build | `Fill the two empty acknowledgment sections` |
| B4 | `IMP-020` | `03_background.tex`, `04_research_questions_and_contributions.tex` | pb + build | `Narrow the gap claim to what survives all four frameworks` |
| B5 | `IMP-029` | `05_methods.tex` | pb + build | `Make the artifact table's provenance claim true` |
| B6 | `IMP-025` | `pre/list_of_papers.tex`, `papers.bib`, `09_author_contributions.tex`, `06_summary_of_papers.tex` | pb + build | `Record one authoritative venue and status per paper` |
| B7 | `IMP-034` | `02_introduction.tex`, `03_background.tex`, `07_synthesis_and_discussion.tex` | pb + build | `Ground the uncited load-bearing claims` |
| B8 | `IMP-026` | `pre/sammanfattning.tex` | pb + build | `Rewrite the Swedish abstract as a faithful equivalent` |
| B9 | `IMP-032`, `IMP-033`, `IMP-031`, `IMP-024` | ch02, ch03, ch04, ch06, ch07, `custom/glossary.tex`, `01_terminology.tex` | pb + build | `Reorder the argument spine and cut the triplication` |
| B10 | `IMP-027` | `08_conclusions_and_future_work.tex`, `07_synthesis_and_discussion.tex` | pb + build | `Derive the future work from the synthesis gaps` |
| B11 | `IMP-028` | `paper-appendices.tex`, `liuthesis.cls`, `06_summary_of_papers.tex`, `pre/list_of_papers.tex` | pb + build | `Restore the appendix's chapter furniture and reachability` |
| B12 | `IMP-023` | `07_synthesis_and_discussion.tex` | pb + build | `Apply the contract to a second result` |
| B13 | `IMP-017` (outside the 15) | `07_synthesis_and_discussion.tex` | pb + build | `Record the second reading of the contract` |
| B14 | `IMP-030` | library record, intake/lint criterion | pb | `Require body coverage in the text-adequacy criterion` |

**Why B1 and B9 are single commits.** B1's two IMPs rewrite the same three files and both change
`03:80`, so split the glossary contradicts the chapter it was just edited with; B9 moves text across
five chapters, so any split leaves `\Cref`s dangling. B2–B8 and B14 revert independently.
## Verification of the review's file:line claims
All 12 blocker locations (R-001–R-012, `INFO-030`) and all 10 top-ten locations (`INFO-043`) were read from the
thesis source; every quoted string is present at the claimed line, and T1–T10 act exactly there.
**No file:line mismatch.** Also verified, because the plan depends on them: `03:67`/`03:69` cells,
`03:57` clause columns, `04:27` vs `07:174`, `07:185-203`, `07:215`, `08:17-27` with `08:25`/`08:26`
orphaned, `05:92`, `01_terminology.tex:12`, `sammanfattning.tex:39`, `papers.bib:1-4`,
`list_of_papers.tex:5`.
## Shared R-IDs
Authoritative owner first, other IMPs in brackets. R-001 → `IMP-032` (`IMP-021`, `IMP-031`). R-002 →
`IMP-022` (`IMP-031`). R-003 → `IMP-021` (`IMP-032`). R-126 → `IMP-031` (`IMP-021` decides which
definition survives). R-067, R-143 → `IMP-034` (`IMP-027`). R-093, R-135 → `IMP-022` (`IMP-027`).
R-052, R-128 → `IMP-031` (`IMP-034`). R-109 → `IMP-028` (`IMP-025`). R-196, R-197, R-209 and R-210 are NOTE rows to preserve.

## Discrepancies
1. **R-004 and R-012 were owned by no IMP:** closed, R-004 → `IMP-029` and R-012 → `IMP-026`, with B2 and B3 the commits.
2. **`INFO-030`'s R-009 fix says "between `:11` and `:15`":** `:11` is `\appendix`, `:15` the first `\chapter`, so the instruction is right but the insertion point is `:14`.
3. **`IMP-034` calls `03:91` uncited:** the line carries `\cite{gomesCosimulationFutureOpen2018}` for its first clause and the load-bearing second clause is uncited, so the finding stands and only the wording is imprecise.

## Owns
- The fourteen commit batches: files, gate and message, one commit each.
- The recorded result of checking every blocker and top-ten location against the thesis source.
## Excludes
- `INFO-044` for the dependency order, the R-ID ownership and the author decisions.
- `INFO-030` and `INFO-043` for the rows whose locations are checked here.
- `IMP-020`–`IMP-035` for the work each batch delivers.
- `OPS-001`, `OPS-003`–`OPS-005`, `VER-001`–`VER-004`, `ARG-004` for the thesis sources, build and gates the batches run against.
