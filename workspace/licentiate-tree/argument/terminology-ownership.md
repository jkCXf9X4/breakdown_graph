---
id: ARG-008
type: argument
layer: argument
home: argument/terminology-ownership.md
title: Terminology ownership
summary: One owner per term, and the reserved-meaning rules
date: 2026-11-11
status: current
---

# Terminology ownership

Each term has one owner and one meaning across the kappa and the included papers, and one term never rotates synonyms.
Ownership rules live in this tree; the glossary source and the acronym pipeline are `OPS-003`.

- **Owner:** the source that introduces the term and defines it once.
- **Reuse:** other texts reuse the term and do not redefine it.
- **Second sense:** a term that needs a second sense gets its own key.
- **Direction:** a rename in one paper propagates to the kappa, not the reverse.
- **Forms:** plural and compound forms keep the owner's wording.
- **Intended use:** belongs to Paper II and carries no other sense in the kappa.
- **Excluded wording:** "purpose" and "purpose-driven" are not thesis terms.
- **Architecture intent:** Paper IV uses it for the architecture as authoritative source.
- **SE:** Simulation Engine in the kappa and Papers II and III; Paper IV uses it for Systems Engineering, so that sense takes its own key and the shared table's resolution is `OPS-003`.
- **Core homes:** definition terms, OD and DoV in `ARG-007`; credibility and the contract in `ARG-006`; intended use reserved to Paper II; the stage-by-stage chain in `ARG-001`.
- **Execution terms:** orchestration and weakly coupled are defined in the kappa's co-simulation background (`MS-003`); determinism takes its operational definition from `MTH-003`; their glossary entries are `OPS-003`.
- **Cost and lifecycle terms:** complexity covers process, toolchain, and execution cost; traceability covers linking artifacts across the simulation lifecycle.
- **Traceability:** the link between a definition and its evidence, and between a claim and the result that establishes it; it runs both ways, from the result to the definition, workflow, inputs and versions, and from the definition to the results and decisions that depend on it; the evidence clause is `ARG-006` and the pointer convention `ARG-004`.
- **Reserved meanings:** auditable and verification evidence keep `ARG-006`'s meanings, and this leaf only reserves their wording.

**Owns:**

- The one-owner-per-term rule.
- The reserved-meaning list, including the intended-use reservation and the SE disambiguation.
- The core term homes.

**Excludes:**

- `OPS-003` for the glossary source, the acronym union, and the pipeline that generates them.
- `ARG-007` for the content of the definition terms.
- `VER-004` for terminology consistency checks.
- `MS-001` to `MS-011` for section-level content.