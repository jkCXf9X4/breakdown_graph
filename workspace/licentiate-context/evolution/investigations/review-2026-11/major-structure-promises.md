---
id: INFO-033
type: info
layer: evolution
home: evolution/investigations/review-2026-11/major-structure-promises.md
title: Kappa review — broken promises and redundancy
summary: Promises the book makes and then breaks, and the same content printed more
  than once
date: 2026-11-01
status: current
---

# Kappa review — broken promises and redundancy

Part of `INFO-029`. Severity key and crosswalk are in `R-register.md`.
Each row is a place where the kappa promises and does not deliver, or prints one argument twice.

## Broken promises and redundancy

| R-ID | Location | Defect | Fix | Effort | Source |
|---|---|---|---|---|---|
| R-092 | `07_synthesis_and_discussion.tex:174` vs `04:27` | ch04 promises "The gaps are not enumerated a second time later in the kappa"; ch07:174 enumerates all six, in the same sentence that says "the list is therefore not repeated here". | Delete the six-gap list from `07:174`; refer to `\Cref{sec:gaps}` by name only. | 10 min | SB-S-06 |
| R-093 | `07_synthesis_and_discussion.tex:101` vs `08` | "Validating it requires independent raters … which is stated as future work" — ch08's six future-work items contain no rubric-validation item (`rater`/`rubric`/`completeness` = 0 hits). | Add the item to ch08, or drop the forward reference. | 15 min | CS-F-36, CP-M1 |
| R-094 | `07_synthesis_and_discussion.tex:98` vs `08` | ch07 promises that applying Paper VI's workflow to the Paper IV benchmark is future work; ch08 has no matching item. | Add the item to ch08. | 15 min | CP-M2 |
| R-095 | `07_synthesis_and_discussion.tex:216` vs `08:17-29` | ch07 says "These are the openings that `\Cref{ch:conclusions}` turns into future work", but ch07 names four gaps and ch08 lists six items; two have no antecedent in ch07. | Add the two missing gaps to `07:215`, or drop the two bullets from ch08. | 20 min | SB-S-11 |
| R-096 | `04:97-102`, `06:6-31`, `07:103-125` | The six-row paper→chain-step mapping appears three times. | Keep ch04's table and ch07's; cut ch06's chain-step paragraphs to one clause each. | 45 min | SB-S-07 |
| R-097 | `03:137-141`, `04:20`, `06:8`, `07:5`, `07:110`, `07:127`, `07:152`, `08:8` | The premise "standards are necessary but insufficient" is stated in at least six places across five chapters. | State it once fully at `03:137-141`, then `\Cref` it. | 30 min | SB-S-18 |
| R-098 | `04_research_questions_and_contributions.tex:29-30` vs `03:78` | The same positioning argument (frameworks say *what* to assess; this thesis says *where* it is lost) is made twice in near-identical words. | Delete one and cross-reference the other. | 10 min | SF-S-24 |
| R-099 | `05_methods.tex:40-44` vs `:76-89` | Paper VI's boundedness is stated twice, 39 lines apart, in near-identical wording. | Delete the `:44` sentence and let `:82-83` carry it. | 10 min | SF-S-16 |
| R-100 | `05_methods.tex:3` vs `:20` | "mixed-methods study" and "exploratory survey" are different methodological claims, made without reconciliation. | Use one label. | 10 min | SF-S-26 |
| R-101 | `07_synthesis_and_discussion.tex:140` vs `:169`, `:171`, `:178-180` | The chapter promises "the rest of the thesis uses the clause names" and that the coarser Kind grouping is "not used as a third enumeration in the prose"; both promises are broken within 30 lines. | Pick one name per column and use it in all three tables and the prose. | 45 min | CS-F-52, CS-F-53, SB-S-25 |
| R-102 | `07_synthesis_and_discussion.tex:4-12` vs `02:15-19` | The thesis's actual claim — including the explicit caveat that it is not a weakest-link claim — is stated sharpest at `07:4-9`, ~40 pages after the first, weaker formulation. | Move a compressed version of `07:4-9` into `02:15-19`. | 30 min | SB-S-17, SB-S-35 |
| R-103 | `05_methods.tex:86` vs `07:6-9` | Two chapters use "weakest" for different objects (evidence strength vs credibility aggregation) without distinguishing them. | Add a disambiguating clause in one place. | 10 min | SB-S-24 |
| R-104 | `06_summary_of_papers.tex:1` vs `07:19-21` | ch06's chain-step paragraphs already deliver the argument order, so the reordering ch07 presents as its own move has happened a chapter earlier, unannounced. | Announce the chain order in ch06's introduction, or move the paragraphs to ch07. | 20 min | SB-S-20 |
| R-105 | `08_conclusions_and_future_work.tex:10` | Conclusion 3 merges the scope and evidence clauses, so five items cover six things and the conclusions cannot be read off `tab:taxonomy`. | Split into two, or state at `08:6` why they are concluded together. | 20 min | SB-S-23 |

## Owns
- The MAJOR rows where the kappa promises and does not deliver, or prints one argument twice.
## Excludes
- `INFO-032` for sections that do not do their job, which is a different defect class.
- `INFO-029` for the severity key; `INFO-028` for the index; `INFO-043` for the verdict.
- `IMP-020`–`IMP-035` for the repairs; `OPS-001`, `OPS-003`–`OPS-005`, `VER-001`–`VER-004`, `ARG-004` for the text under review.
