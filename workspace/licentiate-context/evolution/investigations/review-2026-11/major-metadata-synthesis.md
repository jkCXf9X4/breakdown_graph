---
id: INFO-041
type: info
layer: evolution
home: evolution/investigations/review-2026-11/major-metadata-synthesis.md
title: Kappa review — metadata, ch07-ch09
summary: How the kappa accounts for its own six papers, part 2
date: 2026-11-01
status: current
---

# Kappa review — metadata, ch07-ch09

Part of `INFO-029`. Severity key and crosswalk are in `R-register.md`.

| R-ID | Location | Defect | Fix | Effort | Source |
|---|---|---|---|---|---|
| R-113 | `09_author_contributions.tex:19-21`, `:26-28`, `:34-37`, `:42-45`, `:50-55`, `:10-13` | All sixteen role bullets are unverifiable: no included paper declares author contributions (no CRediT, no equal-contribution statement). | Add one sentence stating the roles are the candidate's own declaration. | 10 min | CP-F212, CP-F213, CP-F214, CP-F215, CP-F115–F118, CP-F320–F322, CP-F409, CP-F508, CP-F617 |
| R-114 | `09_author_contributions.tex:12` | "Aerospace experience report contribution" attributes a specific domain to the candidate; the paper never maps author→domain. | Soften to "experience report from the aerospace domain (Saab)", or confirm against affiliations. | 10 min | SB-S-31, CP-F117 |
| R-134 | `07_synthesis_and_discussion.tex:100-102` | The completeness indicator is introduced and immediately disclaimed as hand-applied, single-rater and used once. | State what a validated version would need and why the single application is still informative, or drop the subsection. | 30 min | SB-S-22 |
| R-135 | `07_synthesis_and_discussion.tex:101` | The two-number rubric is introduced in ch07, used once, and appears in neither ch04's contributions nor ch08. | Declare it in ch04 (see R-008) or drop it. | 20 min | CS-F-34 |
| R-136 | `07_synthesis_and_discussion.tex:112` | `tab:paper-roles` V's locators are a category error: `p5:tab:cps_cosim_tools` is a related-work table of *other* engines, so it evidences the gap, not the contribution. | Re-point at the engine's own result. | 15 min | CS-F-43 |
| R-137 | `07_synthesis_and_discussion.tex:116` | "bounds when delay-aware decoupling preserves causality" — one criterion on one benchmark is a condition, not a bound. | Change "bounds when" to "states the condition under which". | 5 min | CS-F-42 |
| R-138 | `07_synthesis_and_discussion.tex:78` | "the intended use is stated as boundary conditions in the paper … but as a sentence" understates: Paper IV has a labelled `\paragraph*{Scope and Limitations.}`. | Correct the description. | 5 min | CS-F-29 |
| R-139 | `07_synthesis_and_discussion.tex:78`, `:200` | "estimable delays" is presented as a stated condition; estimation is future work in Paper IV. | Remove "estimable" from the condition list. | 5 min | CS-F-30, CS-F-65 |
| R-140 | `07_synthesis_and_discussion.tex:113` | `tab:paper-roles` I flattens a domain-divergent result: Paper I reports that aerospace shows a correlation with *not* experiencing collaboration challenges. | Add the divergence. | 10 min | CS-F-39 |
| R-141 | `07_synthesis_and_discussion.tex:114` | `tab:paper-roles` II drops Paper II's own qualifier that its attributes "should be viewed as initial examples and should be evaluated further in a broader industrial context" — a qualifier ch06 carries. | Restore the qualifier. | 10 min | CS-F-40 |
| R-142 | `07_synthesis_and_discussion.tex:127` | "Paper I shows that standards are strong enablers" outruns the paper's own "seems a means of some mitigation" and "should be interpreted with caution". | Soften "shows" to "reports". | 5 min | CS-F-47 |
| R-143 | `07_synthesis_and_discussion.tex:215` | "the definition link … has not been exercised at the scale and change rate of an industrial development programme" — Paper VI has no limitations section, so the phrasing is ch07's. | Mark as the synthesis's reading. | 10 min | CS-F-73 |
| R-144 | `07_synthesis_and_discussion.tex:16` | "those statements are what make the artifact rejectable" — Paper VI supports rejection of *edits*, not withdrawal of *claims*. | Mark as an analogy. | 10 min | CS-F-13 |
| R-145 | `07_synthesis_and_discussion.tex:64` | "Orchestration choices determine what evidence is needed" — Paper IV never links step size to evidence requirements. | Mark as the chapter's inference. | 10 min | CS-F-18 |
| R-146 | `07_synthesis_and_discussion.tex:171` | "A stale definition is invisible from inside a simulation" — no paper demonstrates a stale definition passing a workflow. | Mark as an inference from `:169`. | 10 min | CS-F-56 |
| R-147 | `07_synthesis_and_discussion.tex:174` | "The six gaps … are the handovers at which credibility is lost" strengthens ch04, which defines the gaps as handovers but never claims credibility is lost at each. | Align with ch04. | 10 min | CS-F-57 |
| R-148 | `07_synthesis_and_discussion.tex:183` | "the four failures call for different work" is an assertion about diagnostic discriminability that nothing tests. | Mark as a proposed use. | 10 min | CS-F-58 |
| R-149 | `07_synthesis_and_discussion.tex:135` | Paper III's portability is asserted, not shown — it is demonstrated inside one in-house framework. | Add the bound. | 10 min | CS-F-50 |
| R-150 | `07_synthesis_and_discussion.tex:140` | "Three vocabularies … are not three classifications; they are one" — the clause names were fixed in ch03 *before* the papers were assigned, so the alignment is not independent evidence. | Say so, and present the mapping as a decision (see R-086). | 20 min | CS-F-51 |
| R-168 | `08_conclusions_and_future_work.tex:5` | "The conclusions follow the argument chain … rather than the publication order" — ch07 fixes chain order as VI, I, II, III, IV, V; ch08 orders I, VI, II+III, IV, V. | Align, or state the deviation. | 10 min | CP-C07 |
| R-169 | `08_conclusions_and_future_work.tex:25` | "Link definition provenance to orchestration experimentation" has no antecedent in ch07, whose nearest basis is about scale, not about linking to the engine. | Re-anchor or drop. | 10 min | CP-W05 |

## Owns
- The ch07–ch09 rows on how the kappa accounts for its own six papers.
## Excludes
- `INFO-040` for the ch04–ch06 half; `INFO-039` for front matter; `INFO-042` for the appendix and glossary.
- `INFO-029` for the severity key and crosswalk; `INFO-028` for the index; `INFO-043` for the verdict.
- `IMP-020`–`IMP-035` for the repairs, chiefly `IMP-022` and `IMP-027`.
- `OPS-001`, `OPS-003`–`OPS-005`, `VER-001`–`VER-004`, `ARG-004` for the thesis text under review, not the finding.
