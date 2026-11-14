---
id: MTH-003
type: method
layer: evidence
home: evidence/method/determinism.md
title: What does determinism mean operationally here?
summary: Repeated runs under the same inputs, configuration and execution semantics
  yield the same results and artifacts; the repeatability level of reproducibility
date: 2026-11-11
status: current
---

# What does determinism mean operationally here?

Determinism is defined operationally so the kappa's reproducibility claim is checkable rather than aspirational.

- **Definition:** repeated runs under the same inputs, configuration and execution semantics yield the same results and artifacts.
- **Status:** this is the repeatability level of reproducibility, and it is a prerequisite for credible experimentation rather than a guarantee.
- **Content:** a defined time representation and advancement semantics, a defined execution ordering and data selection policy, and captured configuration, inputs and versioned artifacts.
- **Where bounds are recorded:** `VER-001`; where the tables sit is `MS-005`.
- **Claim:** determinism supports the auditable-evidence clause (`ARG-006`).
- **Literature:** `LIT-006` owns the reproducibility definition this operationalizes.
- **Artifact anchor:** `thesis/chapters/05_methods.tex#ch:methods`.

**Owns:**

- The operational determinism definition and its content.

**Excludes:**

- `MTH-001` for the research approach; `MTH-002` for the survey and case rules.
- `VER-001` for where the evidence bounds are recorded; `MS-005` for the tables.
- `ARG-006` for the evidence clause this definition serves.