---
id: LIT-004
type: literature
layer: evidence
home: evidence/literature/lit-004-domains.md
title: How do the validation and application domains differ?
summary: The validation domain is the parameter-space region where experiments exist;
  the application domain is larger, and the two are generally not coincident
date: 2026-11-11
status: current
---

# How do the validation and application domains differ?

Roy and Oberkampf formalize the difference between where evidence exists and where a model is applied, which the kappa's extrapolation rule relies on.

- **Validation domain:** the set of points in the model input parameter space where experiments have been conducted.
- **Application domain:** the operating envelope, larger than the validation domain.
- **Gap:** the validation domain is generally not coincident with the application domain (`royComprehensiveFrameworkVerification2011` L567).
- **Consequence:** applying a model beyond its validation domain is explicit extrapolation of model-form uncertainty, not default validity.
- **Verification:** quotes verified against the pinned library's extracted text in the 2026-11 intended-use audit (`review-2026-11/source-audits/intended_use_domain_cluster.md`).
- **Serves:** the "extrapolation must be stated, not assumed" rule (`ARG-005`, `MTH-001`, `MS-005`).