---
id: CLM-001
type: claim
layer: claims
home: claims/thesis-claim.md
title: What does the kappa claim?
summary: Credibility for a decision belongs to the chain that produces the result,
  and loss or corruption at a handover is locatable, repairable, traceable, and costly
date: 2026-11-11
status: current
---

# What does the kappa claim?

The credibility of a simulation result in heterogeneous CPS development is a property of the chain that produces it, not of the individual models that enter it.

- **Handovers:** physics-based, software, electrical and data-driven models are combined through standardized interfaces.
  - Every handover either carries the information the next step needs, corrupts it, or loses it.
- **Weakening:** loss or corruption at a handover is not detected downstream by default.
  - The support for the claim stops travelling with the result.
  - The claim can then be neither defended nor rejected.
- **Locatable:** the loss or corruption occurs at named handovers, so it can be pointed at rather than inferred (`INT-001`, `ARG-002`).
- **Repairable:** automated handover information that is dropped or corrupted can be re-established (`ARG-007`).
  - Regeneration repairs the chain rather than restarting it.
- **Traceable:** definition, intended use, and evidence travel with the standard artifacts, which are the contract's clauses (`ARG-006`).
- **Cost:** keeping the contract valid costs process, toolchain, and execution complexity (`ARG-008`).

**Owns:**

- The claim sentence and the weakening printed with it, in the wording the kappa must use verbatim.
- The four consequences the claim names for that loss or corruption: locatable, repairable, traceable, costly.

**Excludes:**

- `ARG-006` for the credibility definition, the three clauses, and the traceability condition the claim rests on.
- `CLM-003` for the claim's strength boundary; `ARG-009` for the strength argument and refutation; `CLM-002` for what the claim refuses to say.
- `ARG-002` for the handover taxonomy and the paper-to-paper handoff sentences; `ARG-001` for the clause-and-premise arithmetic.
- `INT-001` for the premise: standardized interfaces govern the interoperability and leave its semantics unbound.
- `ARG-007` for the definition-layer mechanism and `ARG-008` for the cost terms.
- `ARG-004` for per-consequence evidence status and bounds.
- `MS-015` for the obligation to state the claim in the text; `MS-002` and `MS-004` for where it is printed.