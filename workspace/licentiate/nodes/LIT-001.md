---
id: LIT-001
type: literature
layer: evidence
home: evidence/literature/lit-001-fmi.md
title: What does the FMI standard itself establish?
summary: FMI packages models as FMUs with a defined co-simulation interface; the master
  algorithm drives exchange and synchronization, and the interface hides how an FMU
  advances time internally
date: 2026-11-11
status: current
---

# What does the FMI standard itself establish?

The FMI standard packages models as FMUs and defines the co-simulation interface a composition uses.

- **Packaging:** FMI standardizes model packaging as tool-independent FMUs for model exchange and co-simulation.
- **Interface:** in co-simulation the master algorithm controls data exchange and synchronization between FMUs through the defined interface.
- **Opacity:** the interface shields the integrator from how the FMU advances time internally; the workings behind the interface are not visible.
- **Source:** `fmidevelopmentgroupFunctionalMockupInterface2022`, verified in the pinned library's extracted text; the opacity reading is in `thesis/chapters/03_background.tex`.
- **Serves:** the standardized-interface premise (`INT-001`), the background chapter (`MS-003`), and the grounding work (`IMP-034`).