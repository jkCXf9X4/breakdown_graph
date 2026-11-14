---
id: ARG-007
type: argument
layer: argument
home: argument/definition-layer.md
title: Definition layer
summary: Model and system definitions as the machine-interoperable layer
date: 2026-11-11
status: current
---

# Definition layer

The definition layer is the conceptual step that precedes every credibility claim and holds two artifacts: the model definition and the system definition.
The definition gap is the one `INT-001` names: artifacts are hand-derived from the architecture, so manual judgement and manual error both enter them; the claim the mechanism serves is `CLM-001`.

- **Model definition:** the interface-facing description exchanged through a standardized model interface; it states which variables are exchanged, with what causality and units, and what a simulator needs to execute.
- **System definition:** describes how a set of models is composed, connected, and parameterized, and is the executable realization of an architecture, not the architecture itself.
- **Gap consequence:** hand derivation lets experts adapt the artifacts, but also lets an architecture error or a manual edit propagate into every derived artifact; the architecture's own fidelity bounds what the audit proves (Paper IV).
- **Mechanism:** Paper IV narrows the gap with scripted generation and guarded reverse synchronization, which propagates validated downstream edits back and rejects unsafe ones, leaving a bounded manual remainder.
- **Interface scope:** a standardized interface packages models, connects them, and describes structure and configuration tool-independently.
- **FMI:** covers model packaging and the executable model interface.
- **SSP:** covers system structure and parameterization.
- **Generated artifacts:** FMI model descriptions, SSD structure, and SSV parameter values.
- **Representation scope:** FMI and SSP are the machine-interoperable representation scope of the thesis, and related traceability metadata concepts extend it.
- **OD:** operational domain, the set of conditions where a model is valid for its intended use.
- **DoV:** domain of verification, the set of conditions where V&V evidence exists; OD is typically a subset of DoV.
- **Intended use:** OD and DoV are the carriers; the Paper II objective is `RES-002`'s.
- **Effect on credibility:** explicit definitions travel with models and are checked automatically on reuse and composition, so architecture, composition, and execution stay aligned; what that changes is `ARG-006`'s improvement clause and `CLM-002`'s first refusal.

**Owns:**

- The distinction between model definition and system definition.
- The definition gap's hand-derivation framing, its generation-plus-synchronization mechanism, and the bound the manual remainder leaves on what derivation proves.
- The FMI and SSP representation scope.
- OD as a subset of DoV.

**Excludes:**

- `ARG-006` for the credibility definition and its three clauses; `CLM-001` for the claim itself.
- `ARG-008` for reserved-term rules and term ownership.
- `ARG-003` for paper roles and `RES-001` to `RES-004` for evidence bounds.
- `MS-003` for where the background section presents these terms.
- `OPS-003` for the glossary pipeline that carries the entries.