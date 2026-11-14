---
id: ARG-006
type: argument
layer: argument
home: argument/credibility-contract.md
title: What does credibility mean here?
summary: Credibility is the degree of trustworthiness for a stated decision, made
  explicit by a three-clause contract in standardized artifacts rather than numerically
  better
date: 2026-11-11
status: current
---

# What does credibility mean here?

Credibility is the degree to which a result is trustworthy for a stated decision and its intended use.
- **Basis:** available evidence, stated assumptions.
- **Definition clause:** the executed composition still corresponds to the architecture that defines the system.
- **Intended-use clause:** which decision is supported, under which conditions, and at what rigor.
- **Evidence clause:** which V&V evidence exists, and how it is audited and reproduced.
- **Carrier:** the three clauses travel through standardized artifacts (`ARG-007`).
- **Improvement:** making the contract explicit, auditable and traceable (`INT-001`).
- **No accuracy gain:** the contract changes what can be audited, not the numbers; it claims no numerical-accuracy gain.
- **Redundancy:** the three clauses can be redundant for a given decision, adding nothing to the claim.
- **Scope:** a result can be credible for one decision and not another.
  - Its operating conditions travel with the claim.
- **Cost:** keeping the contract valid costs process, toolchain, and execution complexity (`ARG-008`).
- **Literature:** `LIT-002` and `LIT-003` own the standard and framework facts the contract positions against.

**Owns:**

- The definition of credibility here: trustworthiness for a stated intended use.
- The three clauses the standardized artifacts carry and what each one names.
- That credibility holds per decision, with operating conditions travelling with the claim.
- That the contract claims no numerical-accuracy gain, and that the three clauses can be redundant for a given decision.

**Excludes:**

- `CLM-001` for the claim that credibility for a decision belongs to the chain that produces the result; `ARG-009` for how strong that claim is.
- `ARG-007` for the definition layer and the definition gap the definition clause rests on.
- `ARG-002` for the handover-by-handover chain; `INT-001` for the premise that standardized interfaces leave the semantics unbound.
- `ARG-008` for the term ownership that fixes how these words are used; `MS-015` for stating them in the kappa.