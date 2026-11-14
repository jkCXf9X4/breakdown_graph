---
id: INFO-040
type: info
layer: evolution
home: evolution/investigations/review-2026-11/major-metadata-papers.md
title: Kappa review — metadata, ch04-ch06
summary: How the kappa accounts for its own six papers, part 1
date: 2026-11-01
status: current
---

# Kappa review — metadata, ch04-ch06

Part of `INFO-029`. Severity key and crosswalk are in `R-register.md`.
No MISSING-CITATION finding exists in this scope: every literature citation checked
resolved to a library text. These rows concern the kappa's account of its own papers.

| R-ID | Location | Defect | Fix | Effort | Source |
|---|---|---|---|---|---|
| R-117 | `06_summary_of_papers.tex:17` | Two lexical drifts from Paper III's own vocabulary: "machine-executable" (source: "machine-readable") and "provenance" (source: "audit trail"/"lineage"). | Align to the paper's words; "provenance" is load-bearing across the kappa, so this is a consistency decision. | 15 min | CP-F306, CP-F312 |
| R-118 | `06_summary_of_papers.tex:12` | "machine-checkable" is a kappa coinage; Paper II's term is "machine-interoperable". | Align. | 10 min | CP-F201 |
| R-119 | `06_summary_of_papers.tex:22` | "compares the approach with a Jacobi baseline" — the decisive comparison is against Gauss–Seidel, and Jacobi cannot serve as the IUM baseline. | Correct to Gauss–Seidel. | 5 min | CP-F405 |
| R-120 | `06_summary_of_papers.tex:32` | SSV is expanded as "parameter values"; the paper's expansion is "System Structure Values". | Align. | 5 min | CP-F608 |
| R-127 | `04_research_questions_and_contributions.tex:45-47` vs `:42` | The chapter says the terms are defined in the Terminology chapter and then defines them. | Change `:42` to "restated here because the question turns on them". | 5 min | SF-S-29 |
| R-129 | `04_research_questions_and_contributions.tex:6-11` | "Problem formulation" re-describes the problem at the same level of abstraction as `02:3-19` rather than narrowing it. | Cut to the two sentences that set up the gap analysis. | 20 min | SF-S-25 |
| R-130 | `05_methods.tex:5` | The candid "the argument was not the plan" paragraph — the strongest defence against the post-hoc-framework objection — is placed before the chapter has said what its methods are. | Move it into "Research approach" next to the structural-bias paragraph at `:26`. | 15 min | SF-S-15 |
| R-131 | `05_methods.tex:28` | The section title "Determinism and reproducibility (operational meaning)" contains its own justification. | Retitle to "Determinism and reproducibility". | 2 min | SF-S-17 |
| R-132 | `05_methods.tex:1-2` | The chapter has no `\label`, so nothing can cross-reference the threats argument. | Add `\label{ch:methods}` and reference it from ch07 and ch08. | 10 min | SF-S-14 |
| R-151 | `04_research_questions_and_contributions.tex:84` | "the contributions cover the chain from definition to evaluation" — ch07 treats Paper I as a frame and Paper V as checking, not as chain steps, yet ch04's table assigns both a chain-step cell. | Reconcile with ch07's treatment. | 15 min | RM-F-39 |
| R-152 | `04_research_questions_and_contributions.tex:99` | Row III "Traceable V&V workflows" overstates: Paper III narrows to verification. | Change to "verification workflows". | 5 min | RM-F-42 |
| R-153 | `04_research_questions_and_contributions.tex:60` | SQ1 fuses Paper I's RQ1 and RQ2 and drops RQ3. | State the fusion, or restore RQ3. | 10 min | RM-F-25 |
| R-154 | `04_research_questions_and_contributions.tex:65` | SQ6 recasts Paper VI's stated *goal* as a question. | Align. | 10 min | RM-F-30 |
| R-155 | `05_methods.tex:20` | "The kappa does not claim a stricter methodological label than the papers support" is contradicted in part by R-073's scope recasting. | Fix R-073; the label claim then holds. | 5 min | RM-F-53 |
| R-156 | `05_methods.tex:20` | "design-research sense" is the thesis's coinage: `design science`, `engineering research` and hyphenated `design-research` are all 0 hits in Drego. | Use the source's term, "design research". | 5 min | RM-F-51 |
| R-157 | `05_methods.tex:22` | "a survey in software engineering frequently cannot establish a representative sampling frame at all" — "at all" overstates Linåker's "frequently hard", and Kasunic says nothing SE-specific about sampling frames. | Drop "at all"; split the citation. | 10 min | RM-F-56 |
| R-158 | `05_methods.tex:22` | "experience reports" is the thesis's term, not Kasunic's or Linåker's (0 hits in both). | Mark as the thesis's term. | 5 min | RM-F-57 |
| R-159 | `05_methods.tex:44` | "strong at isolating cause–effect relationships" overstates Drego's "typically used to find". | Soften. | 5 min | RM-F-67 |
| R-160 | `05_methods.tex:5` | "That is a legitimate way to write a compilation thesis" is the sentence that licenses the whole retrospective construction, asserted without warrant. | Add a warrant or soften to "an accepted way". | 10 min | RM-F-50 |
| R-161 | `05_methods.tex:31-33` | Three operational reproducibility items are the thesis's own operationalization but are presented as if they followed from the two citations above them. | Mark as the thesis's operationalization. | 10 min | RM-F-64 |
| R-162 | `05_methods.tex:114` | Row VI omits the Zenodo DOI the paper gives (10.5281/zenodo.21869288). | Add it. | 5 min | RM-F-87 |
| R-163 | `05_methods.tex:119` | "the repositories have moved since" is asserted without naming where they moved to. | Name the current locations, or drop the clause. | 10 min | RM-F-88 |

## Owns
- The ch04–ch06 rows on how the kappa accounts for its own six papers.
## Excludes
- `INFO-039` for front matter and bibliography; `INFO-041` for the ch07–ch09 half; `INFO-042` for the appendix.
- `INFO-029` for the severity key and crosswalk; `INFO-028` for the index; `INFO-043` for the verdict.
- `IMP-020`–`IMP-035` for the repairs, chiefly `IMP-024` and `IMP-029`.
- `OPS-001`, `OPS-003`–`OPS-005`, `VER-001`–`VER-004`, `ARG-004` for the thesis text under review, not the finding.
