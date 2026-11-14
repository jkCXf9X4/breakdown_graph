---
id: INFO-030
type: info
layer: evolution
home: evolution/investigations/review-2026-11/blockers.md
title: Kappa review — blockers
summary: The twelve defects an examiner would stop at
date: 2026-11-01
status: current
---

# Kappa review — blockers

Part of `INFO-029`. Severity key and crosswalk are in `R-register.md`.
Ranked by cost to fix, cheapest first.

| R-ID | Location | Defect | Fix | Effort | Source |
|---|---|---|---|---|---|
| R-009 | `paper-appendices.tex:15`, `:20`; `liuthesis.cls:473-478`, `:458` | Appendices A and B print with no "Appendix" word and no letter (`\chapterstyle{paperstyle}` is set at `\begin{papers}` and never restored), and the even-page running head reads "Paper VI" on every verso of the appendix. | Restore `\chapterstyle{VZ43}` and reset `\makeevenhead` in `paper-appendices.tex` between `:11` and `:15`. | 15 min | SB-S-01, SB-S-02 |
| R-012 | `pre/acknowledgments.tex:5-7` | Two bare headings, "Supervisors" and "Family", print with no text under them. | Fill both sections. | 15 min | PM-13 |
| R-004 | `04_research_questions_and_contributions.tex:78`; `05_methods.tex:62`; `07_synthesis_and_discussion.tex:112` | Provenance is claimed at three sites where the papers never use the word: ch04 C3 "standards-compatible provenance" (`provenance` = 0 hits in Paper III, which *deviated* from the standard metadata format), `05:62` row III "with provenance", `07:112` Paper VI "carries its provenance" (`provenance` = 0 hits in Paper VI). | Delete the provenance claim from all three; ch07's own `tab:contract-applied` already diagnoses Paper IV for exactly the absence ch07 then attributes to Paper VI. | 20 min | RM-F-35, RM-F-90, RM-F-72, CS-F-37 |
| R-002 | `07_synthesis_and_discussion.tex:7`, `:79`, `:98`; `glossary.tex:25-28` | The contract is declared "not a score to be aggregated" (`07:7`), then scored twice (`07:79` "The score is the number of clauses recoverable", `07:98` "a score of two clauses out of four"), while the glossary says it "is satisfied or not satisfied rather than scored". | Pick the register the glossary already fixes: rewrite `07:79` and `07:98` as "two of the four clauses are recoverable from the artifacts alone" and delete the word *score*. | 30 min | CS-F-05, CS-F-31, SF-S-21 |
| R-006 | `03_background.tex:76` | "intended use is assessed by all four" is unsupportable for any of the four and self-contradictory with `03:69`, which marks PCMM `Use = part`; the CAS source says outright that "the NASA scale does not include the adequacy of the M&S in the assessment process". | Replace with the defensible claim: intended use is stated *inside* each assessment rather than carried with the result, and for PCMM it is only partly stated. | 30 min | CIB-F-C43 |
| R-008 | `04_research_questions_and_contributions.tex:73-84`; `pre/abstract.tex:3` | The thesis-level contribution is never declared as a contribution: ch04 lists six paper-level bullets and defers the thesis-level claim to ch07; the abstract is a paper-by-paper inventory; ch07 then claims two thesis-level contributions (the contract as organizing device, the two-number rubric) that ch04 never declared. | Add one paragraph after `04:82` stating the thesis-level contribution in one sentence, and lead the abstract's second paragraph with it. | 30 min | SF-S-13, PM-2, CS-F-34 |
| R-010 | `05_methods.tex:96` | The `tab:artifacts` caption claims "Repository locations are the ones recorded in the papers at the pinned versions", but three of six rows name a "Paper repository" that Papers II, III and IV never name or link; Paper IV's parenthetical matches the on-disk directory layout, not the paper text. | Either locate and cite the three repositories, or change the caption to say the locations are the candidate's record and mark the three rows as not stated in the paper. | 30 min | RM-F-81, RM-F-83, RM-F-84, RM-F-85 |
| R-011 | `pre/list_of_papers.tex:9-24`; `papers.bib:5-63` | The Included Papers list fails its own five-element contract for every entry: Papers I–V carry no status field at all, and Paper VI carries a status but no venue (`@misc`, no `booktitle`/`publisher`). | Add `pubstate`/`note` to the five entries and a `booktitle` to Paper VI, or print an explicit status line per entry. | 30 min | PM-4, PM-5, CP-F603, CP-F606 |
| R-005 | `03_background.tex:53` | "none of them treats execution as more than numerical error" is false for at least two of the four frameworks on their own text (Rigor Scale's Code Verification category is software-quality assurance; roy2011 lists programming mistakes), and it is in tension with the thesis's own `Exec. = no` cell at `03:67`. | Narrow to the claim that survives all four sources: no framework assesses the correspondence between the executed composition and its architecture, and none treats orchestration settings, coupling scheme and step-size policy as assessed objects. | 45 min | CIB-F-C15 |
| R-007 | `04_research_questions_and_contributions.tex:16-25`, `:90-105` | Four enumerations of one structure are in play and never reconciled: 5 chain steps (`04:16`), 6 gap rows (`04:18-25`), 4 clauses (`03:80`), 5 handovers (ARG-002). `tab:mapping` — the one table that could align them — has no gap column and no clause column. | Add one sentence at `04:16` stating the arithmetic (three gaps, one premise and two cited losses, so five handovers map onto four clauses with execution and evaluation sharing one), and add a Gap column to `tab:mapping`. | 1 h | SF-S-10, SF-S-12, RM-F-46 |
| R-001 | `02_introduction.tex:17`; `03_background.tex:80`; `01_terminology.tex:1-27` | The credibility contract is never introduced as an argument step: `02:17` points at a glossary with no prose, `03:53`/`03:57` use a four-way partition the reader has not been given, and the clauses are first stated at `03:80` — 5,200 words in. | State the four clauses in prose at `02:17`; move the `03:80` paragraph to immediately before `\subsection{What the frameworks already contain}` (`03:51`). | 2 h | SF-S-01, SF-S-02, SB-S-16 |
| R-003 | `07_synthesis_and_discussion.tex:14`; `03_background.tex:80` | The four clauses are restated as a definition, not derived: in `03:80` the only citation attached to them supports clause 4's motivation alone, and no clause is derived from any of the six papers. | Add one sentence per clause naming the paper that forced it, or state plainly that the contract is the thesis's own construction and the papers test it rather than generate it. | 3 h | CS-F-11 |

## Why these twelve and not others

Each one either makes the central claim unsupported, makes the book contradict itself,
or makes a page unreadable as printed. R-001, R-002 and R-003 are one cluster: the
credibility contract is never introduced as an argument step, is stated as a definition
rather than derived, and is then scored in a chapter that opens by denying it is a score.
Fix them together or the fix will not hold.

## Owns
- The twelve BLOCKER rows: location, defect, fix, effort and source ID.
- Why these twelve and not others.
## Excludes
- `INFO-031`–`INFO-042` for the MAJOR, MINOR and NOTE rows; `INFO-035` for what already holds.
- `INFO-029` for the severity key, crosswalk and re-gradings; `INFO-028` for the index.
- `IMP-020`–`IMP-035` for the repairs the rows demand; `INFO-044` for their order.
- `OPS-001`, `OPS-003`–`OPS-005`, `VER-001`–`VER-004`, `ARG-004` for the thesis text and gates under review, not the finding.
