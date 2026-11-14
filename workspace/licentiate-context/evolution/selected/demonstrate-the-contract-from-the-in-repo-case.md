---
id: IMP-039
type: imp
layer: evolution
home: evolution/selected/demonstrate-the-contract-from-the-in-repo-case.md
title: Demonstrate the contract from the in-repo case
summary: One in-repo case under thesis/case/ carries the three-clause contract from
  artifacts alone
date: 2026-11-05
status: selected
---

# Demonstrate the contract from the in-repo case

The synthesis applies the three clauses once, to the case under `thesis/case/`.
The case ships its own artifact set, so a reader recovers each clause from the repository rather than from a cited paper.
It is kappa material, argued in the synthesis and documented in the appendix, claiming no empirical result (`MS-012`).
**Evidence:**

The earlier application read a paper's artifact set, so no clause could be checked without that paper. With the cited works gone, the thesis has no result to apply the contract to unless a case supplies one.
The case must also carry all three clauses, or the demonstration repeats the one-of-three outcome that made the instrument look uniform.

- The application moved from the cited temporal-decoupling paper to an in-repo case (`RES-005`).
- `IMP-023` tests whether the instrument discriminates, and that test needs a case carrying all three clauses.
- The clauses are `ARG-006`; the definition layer the first clause rests on is `ARG-007`.
**Acceptance:**

- `thesis/case/` holds an architecture definition, a model package and system-structure artifact, an intended-use statement, a verification record, a regeneration command, and a README naming each file.
- Each of the three clauses is recoverable from that set alone, with the artifact and line named for it.
- `tab:contract-applied` reports one verdict per clause, three rows; the target is three of three recoverable, and a lower count is reported rather than adjusted.
- The regeneration command is documented in `thesis/case/README.md` and runs from the repository root.
- `thesis/appendices/case.tex` documents the case and its artifact set in the book (`app:case`).
- `python3 thesis/build.py` is green with no undefined citation; `pb check --strict` and `pb node-size --strict` pass.
- The leaf names what it replaces: the application formerly made on the cited temporal-decoupling paper (`RES-005`).
**Out of scope:**

- The independence of the rater (`IMP-017`).
- Whether the instrument is a score (`IMP-022`).
- Whether the contract discriminates between results (`IMP-023`).
- Printing the case as one of the four appended papers; the appendix documents it (`MS-012`).