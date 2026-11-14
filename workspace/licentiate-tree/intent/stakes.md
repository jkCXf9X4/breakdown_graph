---
id: INT-004
type: intent
layer: intent
home: intent/stakes.md
title: What is at stake if a credibility judgement is wrong?
summary: A wrong judgement carries an unsupported decision, and repair re-establishes
  definition, intended use and evidence, plus the execution settings recorded with
  the result
date: 2026-11-11
status: current
---

# What is at stake if a credibility judgement is wrong?

A wrong credibility judgement leaves a decision unsupported.

- **Downstream use:** a simulation result is consumed by a decision, and that decision rests on the traceability the artifact carries to its upstream and downstream information.
- **Exposure:** if the judgement is wrong, the decision stands on information that was never carried with the result or that arrived corrupted.
- **Detection:** the error surfaces late, because the missing or corrupted information failed silently at handover.
- **Repair:** repair re-establishes the definition, intended-use and evidence clauses (`ARG-006`).
  - The execution settings are recorded with the result, not as a clause.
- **Trade:** the contract's cost is paid up front, while the cost of a wrong judgement is paid at the decision (`ARG-006`).
- **Status:** the thesis argues this consequence.
  - No paper in the set measures it.

**Owns:**

- The consequence of a wrong credibility judgement and its cost profile: paid at the decision, found late.
- The repair obligations a wrong judgement triggers.

**Excludes:**

- `ARG-006` for what credibility is and what keeping the contract costs.
- `INT-001` for why the thesis exists; `CLM-001` for where credibility resides.
- `MS-015` for the caveat the kappa text must carry that no paper measures the cost.
- `ARG-004` for the claim-to-evidence trace a measured version would need.