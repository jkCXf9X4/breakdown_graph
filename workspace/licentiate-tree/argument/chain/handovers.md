---
id: ARG-002
type: argument
layer: argument
home: argument/chain/handovers.md
title: What can happen to information at a handover, and how do the papers hand off?
summary: A handover carries, corrupts, or loses the information the next step needs;
  the papers hand off to each other in chain order
date: 2026-11-11
status: current
---

# What can happen to information at a handover, and how do the papers hand off?

Each handover names where credibility weakens when models are mixed, and each stage names the appended paper that answers it.

- **Failure modes:** a handover either carries the information the next step needs, corrupts it, or loses it; corruption is carried-but-degraded — composition drift or distorted semantics — distinct from loss, and neither is detected downstream by default.
- **Handoff Paper I:** the premise (`INT-001`) motivates objective intended-use representations.
- **Handoff Paper II:** turns credibility's dependence on intended use into an explicit, machine-interoperable representation.
- **Handoff Paper III:** adds the process-side prerequisite, workflows whose evidence is auditable, repeatable, and comprehensible.
- **Handoff Paper IV:** closes the upstream end, so the executed composition in the in-repo case traces to the architecture (`RES-004`).
- **Handoffs by citation:** Paper III cites Paper II and Paper IV cites Paper III; the premise is argued in the kappa, and the demonstration runs on the in-repo case (`RES-005`).

**Owns:**

- The failure-mode taxonomy at each handover: carries, corrupts, or loses, with corruption as carried-but-degraded and distinct from loss.
- The paper-to-paper handoff sentences.

**Excludes:**

- `ARG-001` for the stage facts, the derivation rule and the arithmetic; `ARG-003` for the per-paper chain roles; `ARG-001` for the full cross-paper narrative.
- `VER-001` for what a handover with no owning paper is.
- `RES-001` to `RES-004` for paper identity, status and metadata, and for what each paper establishes.