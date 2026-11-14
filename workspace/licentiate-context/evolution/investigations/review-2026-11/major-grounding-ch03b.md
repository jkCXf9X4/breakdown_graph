---
id: INFO-037
type: info
layer: evolution
home: evolution/investigations/review-2026-11/major-grounding-ch03b.md
title: Kappa review — grounding, ch03 part 2
summary: Background claims on co-simulation, orchestration and step size
date: 2026-11-01
status: current
---

# Kappa review — grounding, ch03 part 2

Part of `INFO-029`. Severity key and crosswalk are in `R-register.md`.
Covers `03_background.tex` from the co-simulation section to the chapter close.

| R-ID | Location | Defect | Fix | Effort | Source |
|---|---|---|---|---|---|
| R-034 | `03_background.tex:4` | "it is the decision—not the model in isolation—that must be credible" is only partly supported, and eek explicitly disclaims guaranteeing credibility at model or simulator level. | Add the disclaimer, or narrow to the test-worthiness declaration. | 15 min | CIB-F-A33, CIB-F-A34 |
| R-035 | `03_background.tex:7` | "Their heterogeneous nature is reflected in the models used to represent them" — junghanns has zero hits for "heterogen". | Re-point the citation. | 10 min | CIB-F-A36 |
| R-036 | `03_background.tex:9` | "data-driven components advance time differently and operate on different horizons" — "horizon" and "data-driven" are 0 hits in both sources. | Drop or re-cite. | 10 min | CIB-F-A42, CIB-F-A43 |
| R-037 | `03_background.tex:43` | "obscures the contribution of the development work itself and shifts requirements onto the processes surrounding model evaluation" is NOT-FOUND in Babula, which presents the three-category split neutrally. | Delete the evaluative gloss. | 10 min | CIB-F-C04 |
| R-038 | `03_background.tex:47` | "credibility is context dependent: every evaluation is made in light of the model's intended use" is partly contradicted by blattnig2013. | Narrow to the sources that say it. | 10 min | CIB-F-C10 |
| R-039 | `03_background.tex:65`, `:67`, `:69`, `:71` | Four framework-table cells are PARTIAL or NOT-FOUND against their cited sources: CAS `Use = yes`, Rigor `Use = yes`, Rigor "states intended use inside the scale", V&V `Exec. = part`. | Re-source each cell; the PCMM row in particular is cited to a document that never describes the PCMM. | 1 h | CIB-F-C20, CIB-F-C25, CIB-F-C29, CIB-F-C39 |
| R-040 | `03_background.tex:69` | The PCMM row is sourced to `blattnigNASAStandardModels2013`, which explicitly defers PCMM detail to a companion paper and never enumerates PCMM factors; "numerical error" has zero occurrences in the file. | Re-cite to Oberkampf & Roy, which blattnig2013 itself names as the detailed reference. | 30 min | CIB-F-C30, CIB-F-C31, CIB-F-C33, CIB-F-C34, CIB-F-C35 |
| R-041 | `03_background.tex:71` | "assumes the model under assessment is the model that runs" is NOT-FOUND in roy2011, which neither asserts nor denies it. | Mark as the thesis's inference. | 10 min | CIB-F-C41 |
| R-042 | `03_background.tex:76` | "each framework assesses a model or a result against an intended use" fails for blattnig2008 and is absent for PCMM. | Narrow to the two frameworks that support it. | 15 min | CIB-F-C42, CIB-F-C44 |
| R-043 | `03_background.tex:107` | The four exploration examples are attributed to two documents that enumerate none of them; the doc that grounds two of the four is already cited in the same sentence. | Re-point at `rosenlundObjectivelyDefinedIntended2024` L47/L58. | 15 min | CIB-F-D32, CIB-F-D36 |
| R-044 | `03_background.tex:111` | The wall-clock half of "determine both the numerical behaviour … and its wall-clock cost" is NOT-FOUND in hansen2022, whose only "costly" is debugging effort. | Move the cost clause to galtier2015, already cited on the same line. | 10 min | CIB-F-E05 |
| R-045 | `03_background.tex:114` | "Gauss–Seidel typically converges faster for strongly coupled systems" is cited to hafner, which never discusses convergence speed; the claim is true and grounded by lelarasmee1982, whose qualifier is "especially for MOS circuits", not "strongly coupled". | Re-cite to lelarasmee1982 and correct the qualifier. | 10 min | CIB-F-E11 |
| R-046 | `03_background.tex:117` | "Larger steps reduce exchange overhead and can shorten wall time" is NOT-FOUND in both cited documents, which only define H as the exchange interval. | Cite a source that measures it, or drop. | 15 min | CIB-F-E14 |
| R-047 | `03_background.tex:127` | "thread and process allocation, and the distribution of sub-models over machines" is NOT-FOUND repo-wide. | Split the sentence: keep the order→results half (grounded by arnold2010 L101) and mark the allocation half as the thesis's own. | 15 min | CIB-F-E29 |
| R-048 | `03_background.tex:137-138` | The chapter's concluding sentence — the premise the whole thesis rests on — carries zero citations, and "necessary but insufficient" appears in no library document. | Attach the citekeys already used at `:33` and `:39`, and mark the conjunction as the thesis's synthesis. | 20 min | CIB-F-E42, CIB-F-E43 |
| R-049 | `03_background.tex:91` | "a result that was valid for the previous configuration is not automatically valid for the current one" is the hinge from the continuous-development observation to the contract requirement, and carries no citekey. | Add `rosenlundObjectivelyDefinedIntended2024` L260. | 5 min | CIB-F-D21 |
| R-050 | `03_background.tex:124` | The zero-order-hold one-step delay is uncited but precisely groundable. | Add `gomesCosimulationStateArt2017a` L925-926. | 5 min | CIB-F-E23 |

## Owns
- The ch03 grounding rows from the co-simulation section to the chapter close.
## Excludes
- `INFO-036` for the earlier ch03 half; `INFO-038` for ch04–ch07.
- `INFO-029` for the severity key and crosswalk; `INFO-028` for the index; `INFO-043` for the verdict.
- `IMP-020`–`IMP-035` for the repairs, chiefly `IMP-020` and `IMP-034`.
- `OPS-001`, `OPS-003`–`OPS-005`, `VER-001`–`VER-004`, `ARG-004` for the chapter text, library and citation gate under review.
