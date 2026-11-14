---
id: INFO-036
type: info
layer: evolution
home: evolution/investigations/review-2026-11/major-grounding-ch03a.md
title: Kappa review — grounding, ch03 part 1
summary: Background claims on simulation, CPS and credibility scales
date: 2026-11-01
status: current
---

# Kappa review — grounding, ch03 part 1

Part of `INFO-029`. Severity key and crosswalk are in `R-register.md`.
Covers `03_background.tex` up to the framework comparison.

| R-ID | Location | Defect | Fix | Effort | Source |
|---|---|---|---|---|---|
| R-013 | `03_background.tex:20` | "using the definition by Törngren" over-attributes: Törngren declines to define complexity and offers only competing facets; the "(time, money, material, computation)" list is thesis-side synthesis. | Drop the attribution to a definition; say "Törngren lists facets such as…" and mark the resource list as the thesis's own. | 15 min | CIB-F-B07 |
| R-014 | `03_background.tex:20` | "some using prepositions to locate the scale of the product itself" has zero support: `preposition` = 0 hits in all three cited sources and library-wide only in grammar contexts. | Delete the sentence. | 5 min | CIB-F-B08 |
| R-015 | `03_background.tex:84` | "the more rigorous those processes, the greater the credibility" is verbatim Babula but drops both hedges ("as a general rule", "all else being equal"), and Oberkampf explicitly declines the strong form. | Restore the hedges, or split the citation so Babula carries the monotone claim and Oberkampf the caveat. | 15 min | CIB-F-D03 |
| R-016 | `03_background.tex:117` | "routinely sacrificed" and "usually chosen" inflate Sadjina's hedged "often chosen manually by trial-and-error". | Restore "often". | 5 min | CIB-F-E17 |
| R-017 | `03_background.tex:131` | "deterministic schedule" upgrades both sources' word, which is "predictable". | Use "predictable", or state that determinism is the thesis's stronger requirement. | 10 min | CIB-F-E36 |
| R-018 | `03_background.tex:121` | "guarantees convergence at the price of accuracy" is contradicted, not merely unsupported: gomes2018 pairs strong coupling with *best* accuracy and *worst* performance, and braun2022 denies the guarantee. | Reverse the pairing to match the source, or drop the clause. | 15 min | CIB-F-E21 |
| R-019 | `03_background.tex:121` | The "one of three ways" loop taxonomy is the thesis's own construction; no cited document presents a three-way taxonomy, and gomes2018 describes a fourth (semi-implicit) option the trichotomy omits. | Mark the taxonomy as the thesis's synthesis, or add the semi-implicit branch. | 30 min | CIB-F-E20 |
| R-020 | `03_background.tex:124` | "change stability margins" is a control-theory idiom with no library support, and the "weakly coupled systems tolerate it with little effect" half runs against rosenlund2026, which warns of degradation for weakly coupled sub-systems. | Soften to "can change the effective dynamics", and correct the weakly-coupled half. | 20 min | CIB-F-E25 |
| R-021 | `03_background.tex:9` | "What separates CPS simulation from single-domain simulation is not only heterogeneity but how time is represented" — no source makes the CPS-vs-single-domain comparison. | Cite the comparison or reframe as the thesis's observation. | 15 min | CIB-F-A41 |
| R-022 | `03_background.tex:11` | "The trade-off is the same at every level" is not stated by Gallagher; the source says each level has its purpose. | Drop "at every level". | 5 min | CIB-F-A46 |
| R-023 | `03_background.tex:43` | The chapter's first substantive claim about the literature (NASA CAS, M&S Rigor Scale) carries no citation in the sentence that makes it. | Add the citations to `:43`. | 5 min | SF-S-22 |
| R-024 | `03_background.tex:45` | "Building on the CAS, Blattnig et al. introduced the M&S Rigor Scale" inverts the relationship: the Rigor Scale was a competing proposal for the CAS slot. | Rewrite as "a competing proposal for the same slot". | 10 min | CIB-F-C05 |
| R-025 | `03_background.tex:45` | "it notes only briefly that it does not distinguish between development and operations" — the source contains no such distinction at all, not even briefly. | Delete the clause. | 5 min | CIB-F-C09 |
| R-026 | `03_background.tex:76` | The eek2016 characterization is inverted: the source connects a credibility level to a static fidelity measure, which is not "scores one aspect but does not state what else must accompany it". | Rewrite against the source's own wording. | 15 min | CIB-F-C46 |
| R-027 | `03_background.tex:80` | The gomes2019 citation has a referent mismatch: the source's "these are frequently left implicit" refers to simulator implementation and capabilities, not to orchestration, coupling and step size. | Re-point or narrow the sentence to the source's referent. | 15 min | CIB-F-C50 |
| R-028 | `03_background.tex:33` | "standards lower the technical barrier … but make problems more visible" — only the implicit→explicit half is grounded, and only in one Rosenlund source; "single-tool workflow", "lower the technical barrier" and "make problems more visible" appear in neither. | Ground the second half or mark it as the thesis's reading. | 20 min | CIB-F-B17 |
| R-033 | `03_background.tex:4` | "development and training simulators of the kind used in large-scale CPS programmes" — neither source says "CPS programmes". | Drop the CPS clause or cite it. | 10 min | CIB-F-A30 |

## Owns
- The ch03 grounding rows up to the framework comparison.
## Excludes
- `INFO-037` for the co-simulation, orchestration and step-size half; `INFO-038` for ch04–ch07.
- `INFO-029` for the severity key and crosswalk; `INFO-028` for the index; `INFO-043` for the verdict.
- `IMP-020`–`IMP-035` for the repairs, chiefly `IMP-020` and `IMP-034`.
- `OPS-001`, `OPS-003`–`OPS-005`, `VER-001`–`VER-004`, `ARG-004` for the chapter text, library and citation gate under review.
