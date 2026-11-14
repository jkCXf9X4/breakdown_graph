---
id: RQ-001
type: research-question
layer: intent
home: intent/research-question.md
title: Primary research question
summary: The mechanism question the whole thesis answers
date: 2026-11-06
status: current
---

# Primary research question

The primary research question is:

> How can standardized, machine-interoperable M&S metadata make the credibility of a simulation result explicit, auditable and traceable during development of large-scale cyber-physical systems?

- **Orientation:** a mechanism question, because the descriptive variant — how much credibility is lost — is not answerable by this evidence base.
- **Answer:** credibility for a decision belongs to the chain that produces the result, not to the models that enter it (`CLM-001`).
- **M&S metadata:** the machine-interoperable description of what must be known about a model, a composed system, or the evidence for it.
- **Kinds:** model and system definitions (`ARG-007`), plus verification evidence as recorded V&V outcomes and the links stating what each establishes (`ARG-006`).
- **Standardized and machine-interoperable:** fixed by a published, versioned specification outside any single tool, so independent implementations produce and consume it and tooling checks it (`OPS-003`).
- **Explicit, auditable, traceable:** the contract's three clauses carried as artifacts, not raised numerical accuracy (`ARG-006`).
- **Traceable:** two objects, the definition and the evidence, in both directions (`ARG-008`).
- **Setting:** large-scale CPS development, not a single tool and a single model (`INT-002`).

**Owns:**

- Verbatim wording of the primary research question.
- The three metadata kinds the question works with: model definition, system definition, verification evidence.
- Mechanism orientation of the question, and the rejection of a descriptive variant.

**Excludes:**

- The four sub-questions and their paper mapping (`RQ-002`).
- The thesis claim and its calibrated strength (`CLM-001`).
- Problem statement and its three gaps (`INT-001`).
- Credibility stance itself (`ARG-006`).
- Definition layer as an architectural device (`ARG-007`).
- Scope limits of the study (`INT-002`).