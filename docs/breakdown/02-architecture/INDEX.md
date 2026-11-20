---
title: Architecture
summary: How bd_tree is organized, covering decomposition, interfaces, data flow, and structural decisions.
---

# Architecture

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with `pb registers`. -->
- **INFO-008** [Node files are the only source of truth](node-files-are-the-only-source-of-truth.md) — A store is a flat directory of markdown node files; every other surface is reproducible.
- **INFO-009** [A filename encodes identity and version](a-filename-encodes-identity-and-version.md) — The ref is the filename: id.md is main and id-version.md is one alternative inside a checkout.
- **INFO-010** [Contains is ordered closure data](contains-is-ordered-closure-data.md) — Containment is an ordered list per node, and a view is the closure rooted at one ref.
- **INFO-011** [Links form a DAG outside view membership](links-form-a-dag-outside-view-membership.md) — Typed links express semantics and never add a node to a view; an outside target is reported as external.
- **INFO-012** [A project root may hide its store in .bd_tree](a-project-root-may-hide-its-store-in-bd-tree.md) — Discovery accepts .bd_tree/nodes or a classic nodes directory, and the project owns bd_work.
- **INFO-013** [The work area is a symlink layout](the-work-area-is-a-symlink-layout.md) — Node entries link back to the store while INDEX, REFS, and AGENTS are regular generated files.
- **INFO-014** [Root precedence selects the default view](root-precedence-selects-the-default-view.md) — An explicit ref wins over ROOT, which wins over the lowest main ref; the work area view is separate.
- **INFO-034** [Freshness is opt-in per edge](freshness-is-opt-in-per-edge.md) — A propagating link pins the target body hash, and stale and reconcile work per edge.
<!-- pb:index:end -->
