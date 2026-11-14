<!-- GENERATED FILE — do not edit. Regenerate with `bd export tree`. -->

# literature

- [What does the FMI standard itself establish?](lit-001-fmi.md) — FMI packages models as FMUs with a defined co-simulation interface; the master algorithm drives exchange and synchronization, and the interface hides how an FMU advances time internally
- [What does the SSP standard itself establish?](lit-002-ssp.md) — SSP describes system structure and parameterization; a parameter can be declared and left unbound, and the standard defines no structured home for execution settings or intended use
- [How do the NASA credibility frameworks treat intended use?](lit-003-nasa-intended-use.md) — NASA-STD-7009 and its CAS require intended use to be stated and assessed but never define it; the one formal bounded-applicability concept is "limits of operation", a parameter-set boundary
- [How do the validation and application domains differ?](lit-004-domains.md) — The validation domain is the parameter-space region where experiments exist; the application domain is larger, and the two are generally not coincident
- [What do the CAS's own authors say about model integration?](lit-005-integration-gap.md) — A NESC recommendation accompanying the CAS says it makes no distinction between individual models and integrated models, and should be refined for integration
- [What does reproducibility mean in the simulation literature?](lit-006-reproducibility.md) — Repeatability is re-executing the same simulation history under the same inputs, configuration and execution semantics; a non-deterministic interface destroys it
- [What does design research establish as method?](lit-007-design-research.md) — Engineering research identifies problems in practice, builds artifacts, and evaluates them against the problem rather than a hypothesis
- [How does the simulation-credibility literature aggregate over process steps?](lit-008-ahmann-min-rule.md) — The credibility literature aggregates over process steps as a minimum — the overall level equals the lowest credibility level of a single step
