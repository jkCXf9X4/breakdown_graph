---
id: VER-001
type: verification
layer: verification
home: verification/traceability-check.md
title: How do we know every claim names its supporting paper result?
summary: The traceability criterion — every contribution names a paper result by pointer,
  and a pointer to a vanished label fails the build — with its hand-kept limits
date: 2026-11-11
status: current
---

# How do we know every claim names its supporting paper result?

The traceability check proves `MS-015`'s claim-to-result pointing and serves `VER-007`'s opponent criterion (`VER-005`).

- **Claim:** `CLM-001` and the contribution claims (`MS-004`).
- **Falsifier:** a claim presented as a contribution with no pointer to an appended-paper result, or a pointer to a label that no longer exists.
- **Check:** the acceptance criterion below is enforced by reading and by the build, not by a script.
- **Outcome:** passes for the current kappa; the four handovers and the premise are paired in `tab:taxonomy`, and the RQ answer cites the Summary of Papers and Synthesis chapters (`MS-006`, `MS-007`).
- **Residual risk:** the index is hand-kept, so nothing fails the build when a claim loses its pointer; the synthesis claim rests on the set, so it can weaken silently; the application is single-rater and used once, so it demonstrates a measure rather than validating it.

**Acceptance criterion:**

- Every contribution claim in the kappa names a paper result by pointer (`ARG-004`).
- Every gap names the handover where it occurs and the paper that closes it; a handover with no owning paper is a delimitation, not a gap (`ARG-001`).
- A claim with no pointer is not traceable and is not claimed as a contribution.
- A pointer to a label that no longer exists fails the build.
- The RQ answer cites the Summary of Papers and Synthesis chapters (`MS-006`, `MS-007`), never a single paper alone; the Paper IV synthesis claim points to its bounded case study (`RES-004`).

**Owns:**

- The traceability acceptance criterion and its limits.
- That it proves `MS-015`'s pointing obligation and serves `VER-007`'s opponent criterion.

**Excludes:**

- `ARG-004` for the pointer convention and the current map; `CLM-001` for the claim wording.
- `ARG-001` for the derivation rule that names what a handover with no paper is.
- `RES-001` to `RES-005` for the evidence the pointers name; `VER-005` for the requirement-to-check map.