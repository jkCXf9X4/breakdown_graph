---
id: RV-003
type: review
layer: review
home: review/cadence.md
title: When is the kappa reviewed?
summary: Per change on touched nodes, per release as a full sweep before the registers,
  and again when the layer model changes
date: 2026-11-11
status: current
---

# When is the kappa reviewed?

Review is a gate, not an event; it runs at three triggers.

- **Per change:** when nodes are touched, the owning layer's gates rerun, and a reviewer checks the touched subtree against `RV-001`.
- **Per release:** before `pb registers` regenerates the release surfaces, a full-kappa sweep runs against `RV-001` and the requirement map `VER-005`.
- **On layer-model change:** a migration that redefines the layers triggers a full sweep, because every leaf's owning layer can shift.
- **Gate relation:** a full sweep is also the manual pass that `VER-007` has no check for (`VER-005` calls the missing reader pass out).
- **Cadence practice:** the 2026-11 run was a full sweep; its record is `INFO-056`.