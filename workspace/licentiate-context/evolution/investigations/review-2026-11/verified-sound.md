---
id: INFO-035
type: info
layer: evolution
home: evolution/investigations/review-2026-11/verified-sound.md
title: Kappa review — verified sound
summary: What the audits confirmed works, and should be protected
date: 2026-11-01
status: current
---

# Kappa review — verified sound

Part of `INFO-029`. These are findings too: the author needs to know what not to break.
Every row was positively verified, not merely left unrefuted.

| R-ID | Location | What holds | Source |
|---|---|---|---|
| R-186 | `02:15` → `04:38` | The Introduction's compressed research question is word-for-word the full question at `04:38` with "investigates how" → "How can". The one place the front half's forward-reference discipline works exactly as intended. | SF-S-28 |
| R-187 | `03:33` | The only place in the front half where a term is introduced with an explicit pointer to its glossary entry rather than defined in prose — the pattern the contract needed and did not get. | SF-S-30 |
| R-188 | `05:46` | `tab:evidence-base` is a falsifiable promise that every later claim is bounded by a table row, stated in one sentence with no hedging. The book's strongest structural commitment. | SF-S-31 |
| R-189 | `03:129-131` | MS-003's most specific structural requirement about ch03 (standards-and-semantics subsection inside co-simulation) is satisfied exactly. | SF-S-32 |
| R-190 | `07:13-16` | ch07 explicitly refuses to restate ch03's background and honours it. The section is short precisely because the work was done at `03:41-80`. | SB-S-32 |
| R-191 | `07:66-99` | The retrospective application is the only place in the kappa where the contract is *used* rather than described, and the only place producing a finding no paper contains. | SB-S-33 |
| R-192 | `07:173-184` | The four diagnostic questions ("That is not the system we designed" → definition clause) are a usable instrument no paper contains. | SB-S-34 |
| R-193 | `07:4-12` | The thesis's actual thesis statement, explicitly weakened against the weakest-link strawman. Stronger than anything in ch02 or ch04. | SB-S-35 |
| R-194 | `08:4-15` | Five conclusions, one per clause plus the premise, each with a paper pointer, following ch07's chain order. | SB-S-36 |
| R-195 | `09:1-55` | All six author lists match the papers' own front matter exactly (names, order, spelling; candidate first on all six); all six titles match; the claim that no paper divides authorship into percentage shares is true. | SB-S-37 |
| R-196 | `paper-appendices.tex:15-23` | No duplication with the appended papers: the appendix carries the *full* SRMD example and the *full* workflow listings the paper bodies deliberately abbreviate. | SB-S-39 |
| R-197 | `paper-appendices.tex:11`; `thesis.tex:60` | Placement is correct: after `\end{papers}`, before `\printbibliography`, one appendix block, single bibliography. | SB-S-40 |
| R-198 | `03:55-74` | All four `Def. = no` cells of `tab:framework-coverage` hold — the load-bearing half of the gap argument. The CAS cell is under-cited: Babula contains a NESC recommendation stating the gap outright and should be quoted. | CIB-verdict |
| R-199 | `08:1-29` | All twelve `\Cref` targets into the appended papers resolve; no dangling cross-references. | CP-rollup |
| R-200 | `07:124` | Both asserted citation links are real (III→II at `main.tex:95,139,148`; VI→III at `01_introduction.tex:9`), and the claim that Papers I, IV and V do not cite each other holds in all three directions. | CS-F-44, CS-F-45 |
| R-201 | `07:75` | "Nothing records an architecture that this composition realizes" is verified true: `architecture` = 0 hits across the whole Paper IV repo. The chapter's sharpest and best-evidenced observation. | CS-F-25 |
| R-202 | `07:75` | The SSP provenance field is confirmed verbatim: `generationTool="Dymola by Dassault Systemes"`. | CS-F-24 |
| R-203 | `05:29` | The Dalle repeatability definition is exact on both halves. | RM-F-62 |
| R-204 | `05:24` | The Paper VI case-study description is correct on every countable dimension: three EQs, one case, two versions, aircraft ECS. | RM-F-58 |
| R-205 | `05:22` | The survey-reporting rule is grounded near-verbatim in Kasunic (sampling frame, response rate, instrument in appendix). | RM-F-55 |
| R-206 | `05:76-90` | "Threats to the thesis argument" is the most rigorous page in the kappa. | SB-S-19 |
| R-207 | `06:6-31` | ch06 is *more* conservative than the papers' own abstracts for Papers I, II, III and VI; Paper VI's disclaimer is the paper's own sentence, not a kappa hedge. | CP-rollup |
| R-208 | `pre/abstract.tex:5` vs `08:15` | The abstract's headline result matches ch08 exactly and is correctly scoped. | PM-1 |
| R-209 | `pre/list_of_papers.tex:9-24` | Author order matches `papers.bib`, ch09 and the paper sources for all six papers. | PM-7 |
| R-210 | `pre/list_of_papers.tex:5`, `09:3`, `06:4` | The three statements of ordering are mutually consistent and consistent with the build. | PM-6 |
| R-211 | `3rd_party/references/library/` | 60 of 61 cited keys have adequate extracted text; 0 MISSING. The one SUSPECT (`oberkampfVerificationValidationScientific2010`) is front-matter-only, but the one sentence the kappa cites is present in the Preface, so the citation is grounded. **Limitation: no chapter-level claim may be made against this key.** Its `text.md` is 13 pages of front matter against a 725-page table of contents; the body is absent and closed access (CUP) forbids intaking it. The criterion that catches this is `IMP-030`. | LA |
| R-212 | `thesis/` | No OPS-004 metadata-only violation: all 58 citekeys used in ch02–03 have extracted text, none flagged `text_poor` or `ocr_needed`. | CIB-headline |

## The four that matter most

- **The retrospective application is original and true** (R-201): `architecture` returns zero hits across the whole Paper IV repository, and no paper contains this instrument.
- **`tab:evidence-base` is a real falsifiable commitment** (R-188): it is breached exactly once (R-072), which is what makes it a commitment rather than a decoration (R-077).
- **All four `Def. = no` cells hold** (R-198), the load-bearing half of the gap argument; the CAS cell is *under*-cited, and `babulaNASAStandardModels2009` L447-451 states the gap outright.
- **`05:76-90` is the most rigorous page in the book** (R-206) and is cited by nothing.

## Owns
- The positively verified rows R-186 to R-212, with the location that carries each strength.
- The four that a repair must not break.
## Excludes
- `INFO-034` for the MINOR rows and `INFO-030` for the BLOCKERs; both are defects, not strengths.
- `INFO-029` for the severity key and crosswalk (NOTE covers verified-good or cosmetic).
- `IMP-020`–`IMP-035` for the repairs, chief among them `IMP-030` for the R-211 criterion.
- `OPS-001`, `OPS-003`–`OPS-005`, `VER-001`–`VER-004`, `ARG-004` for the thesis text, library and gates whose strength is recorded here.
