---
title: Verification
summary: How each bd_tree claim is checked, and the evidence that it holds.
---

# Verification

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with `pb registers`. -->
- **INFO-022** [Temporary stores drive the test suite](temporary-stores-drive-the-test-suite.md) — Tests build real stores in temporary directories and assert loaded state and file bytes.
- **INFO-024** [Check validates global and per-view invariants](check-validates-global-and-per-view-invariants.md) — bd check covers filenames, ids, containment targets, cycles, view trees, homes, links, and size.
- **INFO-026** [Example project proves two complete trees](example-project-proves-two-complete-trees.md) — The committed example is checked as a clean store with a main and an alternative closure.
- **INFO-028** [Git-dependent tests skip without git](git-dependent-tests-skip-without-git.md) — Worktree and git-context tests detect the executable and skip cleanly when it is absent.
- **INFO-030** [Exit codes separate navigation, structure, and success](exit-codes-separate-navigation-structure-and-success.md) — Zero means success, one a navigation or check failure, two a structural refusal.
- **INFO-035** [Stale and reconcile are view-scoped](stale-and-reconcile-are-view-scoped.md) — bd stale and bd reconcile report and rewrite pins inside one containment view.
<!-- pb:index:end -->
