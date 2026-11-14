---
id: ARG-004
type: argument
layer: argument
home: argument/claim-evidence-map.md
title: How is each claim mapped to a paper result?
summary: Every contribution, conclusion and handover names the appended-paper result
  that supports it, with a bound cell; the synthesis claim rests on the four-paper
  set
date: 2026-11-11
status: current
---

# How is each claim mapped to a paper result?

This node holds the claim-to-evidence index: which kappa claim is tied to which appended-paper result, and with what bound.

- **Pointer convention:** a pointer is a `\Cref` to a namespaced label in the appendix, `p1:`, `p2:`, `p3:`, or `p6:` as the key stands, never just the paper; it names a section, figure, or table, and where the paper has no label, the section title.
- **Pointer robustness:** because the label is namespaced and resolved by the build, a pointer to a result that disappears fails the build instead of failing silently.
- **Why line:** a pointer adds one line stating why that result supports the claim.
- **Synthesis pointer:** the synthesis claim points to Papers I to IV, not to a single figure; the thesis claim (`CLM-001`) points to the four-paper set and to `tab:contract-applied` on the in-repo case (`RES-005`).
- **Current map:** contributions cite, in order, Paper I survey figures, Paper II OD/DoV and verification evidence, Paper III workflow schema and provenance, Paper IV guarded round-trip and case study; the bounds are reported practice, proof of concept, one framework, and one aerospace case.
- **Conclusions:** the four conclusions each name one element of the chain and its pointer: the three clauses and the premise (`ARG-003`).
- **Handovers:** the three handovers and the premise are paired in `tab:taxonomy`, each handover with an appended paper (`ARG-002`).
- **Consequence status:** locatable is enumerable at the named handovers, demonstrated at three gaps, and the count is its own; repairable and traceable are demonstrated once, on the in-repo case, where all three clauses are recoverable from artifacts; cost is asserted and bounded, with no measured figure (`CLM-002`).

**Owns:**

- The evidence pointer convention.
- The current claim count, per-consequence status, evidence cells and gap cells.

**Excludes:**

- `VER-001` for the traceability acceptance criterion and its limits.
- `ARG-001` and `ARG-002` for the chain stages and handovers; `ARG-003` for the paper roles.
- `RES-001` to `RES-005` for what each paper and the case establish; the results inside each paper are owned by the paper repos.
- `MS-015` for the obligation this map serves; `VER-006` for the mapping table's presence; `VER-005` for the coverage map.