---
title: Implementation
summary: Where and how bd_tree's concrete files, scripts, and configs are built.
---

# Implementation

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with `pb registers`. -->
- **INFO-015** [Loader owns filenames, discovery, and views](loader-owns-filenames-discovery-and-views.md) — Filename grammar, store resolution, ROOT, and containment closures live in one module.
- **INFO-016** [Model and checker separate shape from validation](model-and-checker-separate-shape-from-validation.md) — Dataclasses hold the loaded graph; structural issues are reported by an independent checker.
- **INFO-017** [Exporter renders read-only projections](exporter-renders-read-only-projections.md) — Tree, context, and dot outputs are disposable projections of one view.
- **INFO-018** [Work module owns the single area](work-module-owns-the-single-area.md) — Symlink layout, switching, status, writeback, and the generated navigation files live together.
- **INFO-019** [CLI and API share one command surface](cli-and-api-share-one-command-surface.md) — Argparse handlers delegate to a thin public API so scripts and terminals use the same operations.
- **INFO-020** [Solutions module wraps git worktree](solutions-module-wraps-git-worktree.md) — Solution lifecycle is a state-free translation of git worktree add, list, and remove.
- **INFO-021** [Ops module performs body-preserving structural edits](ops-module-performs-body-preserving-structural-edits.md) — Contain, link, fork, promote, and init rewrite front matter while preserving body bytes.
<!-- pb:index:end -->
