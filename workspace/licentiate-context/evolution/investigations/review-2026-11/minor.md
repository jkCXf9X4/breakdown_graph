---
id: INFO-034
type: info
layer: evolution
home: evolution/investigations/review-2026-11/minor.md
title: Kappa review — minor
summary: Local inaccuracies, terminology drift and redundancy
date: 2026-11-01
status: current
---

# Kappa review — minor

Part of `INFO-029`. Severity key and crosswalk are in `R-register.md`.
Each is a one-line fix. None changes an argument.

| R-ID | Location | Defect | Fix | Effort | Source |
|---|---|---|---|---|---|
| R-174 | `03_background.tex:39` | "repeatable assembly" — the SSP standard's word is *reuse*; "repeatable" and "assembly" appear nowhere. | Align. | 5 min | CIB-F-* |
| R-175 | `03_background.tex:114` | "two canonical schemes" reduces hafner's four-branch taxonomy; "canonical" appears nowhere in the source. | Drop "canonical". | 5 min | CIB-F-E07 |
| R-176 | `03_background.tex:117` | "of the third kind" is not hafner's terminology. | Use the source's term. | 5 min | CIB-F-E22 |
| R-177 | `03_background.tex:111` | galtier2015 never uses "orchestrator" in the relevant sense; it attributes ordering to "the user writing a master code". | Use "master algorithm". | 5 min | CIB-F-E02 |
| R-178 | `03_background.tex:121` | lee2015 is decorative for the conservative/optimistic synchronization definitions; all the specific wording is Banks alone. | Re-cite to Banks. | 10 min | CIB-F-E39, CIB-F-E40 |
| R-179 | `03_background.tex:121` | braun2022 is decorative for the loop framing: "loop" has zero occurrences in its 917 lines. | Re-cite. | 10 min | CIB-F-E20 |
| R-180 | `03_background.tex:107` | `gomesPropertyPreservationCosimulation2019` is a 9,213-line doctoral thesis, not a paper; citing it for a four-item list over-reads it. | Re-point (see R-043). | 5 min | CIB-F-D32 |
| R-181 | `03_background.tex:91` | Rosenlund's accreditation claim is itself second-hand from Balci & Ormsby 2000. | Cite the primary source if the point is load-bearing. | 10 min | CIB-F-D38 |
| R-182 | `03_background.tex:84` | "V&V is rarely a single test" and "rarely follows a single waterfall" — "single test"/"waterfall" are 0 hits in the cited sources. | Drop the frequency claims. | 10 min | CIB-F-D05, CIB-F-D15 |
| R-183 | `03_background.tex:107` | The SRMD gloss describes the SSP Traceability standard, not a statement Rosenlund makes. | Cite the spec, or use Rosenlund's wording. | 10 min | CIB-F-D12 |
| R-184 | `03_background.tex:69` | `blattnigNASAStandardModels2013` calls the CAS and PCMM "similar", which cuts against the table's sharp `no` vs `part` contrast on the Execution axis. | Address the source's own framing. | 15 min | CIB-surprise-1 |
| R-185 | `03_background.tex:67` | The Rigor Scale's Process Control category is a partial execution dimension — the closest thing to a counterexample to `Exec. = no`. | State why it does not overturn the cell. | 15 min | CIB-surprise-3 |

## The drift worth naming

"Provenance" is load-bearing across the kappa but is not Paper III's or Paper VI's word
(R-117, R-004). "Machine-checkable" is a kappa coinage where Paper II says
"machine-interoperable" (R-118). One gap carries three names across three documents
(R-128). Settle the vocabulary once and most of this section disappears.

## Owns
- The MINOR rows: local inaccuracies, terminology drift and redundancy, one-line fixes each.
## Excludes
- `INFO-030` for the twelve blockers; `INFO-031`–`INFO-033` and `INFO-036`–`INFO-042` for the MAJOR rows.
- `INFO-029` for the severity key and crosswalk; `INFO-028` for the index; `INFO-043` for the verdict.
- `IMP-020`–`IMP-035` for the repairs; `IMP-031` for the terminology governance these rows feed.
- `OPS-001`, `OPS-003`–`OPS-005`, `VER-001`–`VER-004`, `ARG-004` for the thesis text and gates under review, not the finding.
