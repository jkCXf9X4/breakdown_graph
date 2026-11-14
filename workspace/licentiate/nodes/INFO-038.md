---
id: INFO-038
type: info
layer: evolution
home: evolution/investigations/review-2026-11/major-grounding-rest.md
title: Kappa review — grounding, ch04-ch07
summary: Research-question, methods and synthesis claims that exceed their source
date: 2026-11-01
status: current
---

# Kappa review — grounding, ch04-ch07

Part of `INFO-029`. Severity key and crosswalk are in `R-register.md`.

| R-ID | Location | Defect | Fix | Effort | Source |
|---|---|---|---|---|---|
| R-053 | `05_methods.tex:20` | Citation-swap: DRM was created by Blessing & Chakrabarti, not Drego, which *applies* it; and the phase names are re-labelled (step 2 is a literature review, step 4 is "descriptive study II"). | Cite Blessing & Chakrabarti directly, or write "as applied by Drego (2024)", and restore the phase names. | 30 min | RM-F-52 |
| R-054 | `05_methods.tex:29` | Citation-swap: "whether or not the models are deterministic" is not in Pedersen (`non-determinis` = 0 hits); the closer warrant is dalle's level L2. | Re-cite to dalle L37. | 10 min | RM-F-63 |
| R-055 | `05_methods.tex:41` | "Triangulation with experience reports … introduces risks of researcher bias" is asserted with no source, and the risk is sharper than stated because the candidate authored the reports. | Argue it, and name the self-authorship. | 20 min | RM-F-66 |
| R-056 | `05_methods.tex:44` | The Paper IV bound is inverted: determinism is not a stated scope limit in the paper — both `determinis` hits describe the *proposed algorithm* as deterministic. | Remove determinism from the bound list. | 10 min | RM-F-68 |
| R-057 | `04_research_questions_and_contributions.tex:9` | "a composition that can drift from its defining architecture" is NOT-FOUND in both cited sources (`drift` = 0 hits in each). | Cite Paper VI, which does support it, or drop the citation. | 10 min | RM-F-03 |
| R-058 | `04_research_questions_and_contributions.tex:9` | "Standardized interfaces lower the cost of integration" is NOT-FOUND in gomes2019 (`cost` = 0, `standardiz` = 0). | Re-cite or soften. | 10 min | RM-F-07 |
| R-059 | `04_research_questions_and_contributions.tex:19` | "The handover from architecture to system definition is typically manual and weakly traceable" is a general practice claim resting on one bounded case. | Cite the survey, or soften "typically". | 10 min | RM-F-11 |
| R-060 | `04_research_questions_and_contributions.tex:22` | "Evidence exists but is not reproducible or auditable at scale" — `provenance` = 0 hits in Paper III and "at scale" is not in its RQ. | Narrow to traceability, which is supported (34 hits). | 10 min | RM-F-14 |
| R-061 | `07_synthesis_and_discussion.tex:127` | "they introduce process overhead and new failure modes when metadata and traceability are insufficient" — `failure mode` = 0 hits in Paper I, which says standards "might also bring their own set of challenges". | Replace with the paper's own wording. | 10 min | CS-F-48 |
| R-062 | `07_synthesis_and_discussion.tex:30`, `:58` | The figure caption says Paper I states standards are "necessary" but insufficient; Paper I says only that standards "seem a means of some mitigation". | Drop "necessary". | 5 min | CS-F-14 |
| R-063 | `07_synthesis_and_discussion.tex:186` | "can alter system dynamics" — the benchmark models "contain only a pure phase shift", so there is no amplitude dynamics to alter. | Soften to "can alter the phase relationship". | 10 min | CS-F-60 |
| R-064 | `07_synthesis_and_discussion.tex:186` | "increasing parallelism" is not evidenced: the paper claims parallel execution is *maintained*, and the repo has no wall-time, speedup or invocation-count measurement. | Change to "maintaining parallelism". | 5 min | CS-F-61 |
| R-065 | `07_synthesis_and_discussion.tex:202` | Three of six boundary conditions are the chapter's construction, not Paper IV's: "tightly coupled through near-instantaneous feedback" (0 hits), "significant algebraic constraints span groups" (only the positive form exists), "delay assumptions cannot be defended" (0 hits). | Hedge the negative list the way the positive list is hedged at `:196`, or delete the three. | 30 min | CS-F-66, CS-F-67, CS-F-68 |
| R-066 | `07_synthesis_and_discussion.tex:71`, `:75`, `:87` | "two FMUs" / "two components" is false: both `.ssp` archives contain six `<ssd:Component>` elements and five connections. | Correct to six components, or describe the two *models* in two FMI versions. | 15 min | CS-F-21, CS-F-23 |
| R-067 | `07_synthesis_and_discussion.tex:215` | "Guidance on when a given orchestration strategy is justified … does not exist in a form a project can apply" is a strong negative existence claim made in a chapter with zero `\cite` commands. | Cite the literature searched, or soften to "is not available in the papers reviewed here". | 20 min | CS-F-74 |
| R-068 | `07_synthesis_and_discussion.tex:98` | The 2/4 result is circular as presented: a benchmark paper necessarily records results and step sizes, so "the two clauses that survive are the two the papers were built to produce" is a tautology about genre presented as a confirmed prediction. | Present it as a genre observation, not a prediction confirmed. | 20 min | CS-F-32 |
| R-069 | `07_synthesis_and_discussion.tex:85` | The execution clause is said to be filled by "the step sizes that appear in the dataset names and the analysis scripts", but the SSP does not record step size (`fmi_CommunicationStepSize` is an unbound connector) and the scripts glob filenames. | State that step size survives only in filenames — which is a sharper version of the chapter's own argument. | 20 min | CS-F-28 |
| R-070 | `07_synthesis_and_discussion.tex:83` | "a documented reproduction recipe" reproduces only one of the three figures the chapter cites. | Narrow the claim to the figure the recipe reproduces. | 10 min | CS-F-27 |
| R-071 | `06_summary_of_papers.tex:22` | Paper IV is said to determine effects on "validity and performance together"; the Result section reports phase shift only and no timing measurement exists anywhere in the manuscript. | "affect validity, and argues for parallelization, rather than performance alone". | 10 min | CP-F403, RM-F-36, RM-F-91 |
| R-072 | `06_summary_of_papers.tex:27`; `04_research_questions_and_contributions.tex:80`; `08_conclusions_and_future_work.tex:12` | Paper V is credited with "comparative benchmarking" and "reproducible" comparisons; the delivered result is a qualitative waveform overlap the paper itself flags as needing further evaluation, and the paper concedes recorded data "may vary slightly between runs". | "a qualitative cross-check against OMSimulator"; drop "reproducible" from ch04 C5 and ch08:12. | 15 min | CP-F503, RM-F-37, RM-F-92, RM-F-69, RM-F-78 |
| R-073 | `04_research_questions_and_contributions.tex:61`, `:62`, `:64` | Three sub-questions recast the papers' own research questions more broadly than the papers state them: Paper II's LSS scope is dropped, Paper III's "verification" becomes "V&V" and gains a scaling clause, and Paper V is said to support digital-twin and HIL *evaluation* when it evaluates neither. | Restate SQ2, SQ3 and SQ5 in the papers' own terms. | 45 min | RM-F-26, RM-F-27, RM-F-29 |
| R-074 | `04_research_questions_and_contributions.tex:57` | "Each is answered by exactly one appended paper" is bookkeeping-true but obscures that two of six sub-questions (SQ1 premise, SQ5 infrastructure) do not decompose the primary question. | State at `:57` that the decomposition is by paper and that SQ1 and SQ5 are premise and instrument. | 20 min | RM-F-24, RM-F-95, SF-S-11 |
| R-075 | `04_research_questions_and_contributions.tex:38` | The primary question is answerable only under the stipulated reading of "improve credibility" as "make checkable"; no paper measures credibility improvement. | Say in ch04 what ch07 says: the RQ is answered for half its own contract and argued for the other half. | 20 min | RM-F-20 |
| R-076 | `05_methods.tex:92` | "where it does not, the row says so" — no row says so; every "What it enables" cell is affirmative. | Add the negative cells, or delete the disclaimer. | 20 min | RM-F-80 |
| R-077 | `05_methods.tex:46` | The `tab:evidence-base` promise ("a claim that would exceed its row is not made") is breached by `08:12`'s "reproducible evaluation", while row V establishes only "comparable". | Fix `08:12` (see R-072); the promise itself is sound. | 5 min | RM-F-69, RM-F-78 |

## Owns
- The ch04–ch07 rows where a research-question, methods or synthesis claim exceeds its source.
## Excludes
- `INFO-031` for ch02 and `INFO-036`/`INFO-037` for ch03: the siblings split by chapter.
- `INFO-029` for the severity key and crosswalk; `INFO-028` for the index; `INFO-043` for the verdict.
- `IMP-020`–`IMP-035` for the repairs, chiefly `IMP-024`, `IMP-027` and `IMP-034`.
- `OPS-001`, `OPS-003`–`OPS-005`, `VER-001`–`VER-004`, `ARG-004` for the chapter text, library and citation gate under review.
