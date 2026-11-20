---
title: Suggested
summary: Improvement candidates not yet selected for work.
---

# Suggested

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with `pb registers`. -->
- **IMP-001** [Cross-branch version synchronization](cross-branch-version-synchronization.md) — Node versions do not follow a merge, so alternatives can drift between branches.
- **IMP-002** [Three-way merge between versions](three-way-merge-between-versions.md) — Promotion copies one version onto main and leaves synthesis to manual editing.
- **IMP-003** [Branch-switch layout repair](branch-switch-layout-repair.md) — A checkout can leave bd_work pointing at paths that the new branch does not contain.
- **IMP-004** [Recovery for symlink-replacing editors](recovery-for-symlink-replacing-editors.md) — Editors that replace a symlink force a manual status and writeback cycle.
- **IMP-005** [Windows symlink support](windows-symlink-support.md) — The work area needs POSIX symlinks and Windows currently requires developer mode.
- **IMP-006** [Generic markdown importer](generic-markdown-importer.md) — Existing markdown trees must be converted by hand to the node file pattern.
- **IMP-007** [Concurrent editor locking](concurrent-editor-locking.md) — No lock coordinates two writers, so git remains the conflict detector.
- **IMP-008** [Snapshot list and prune](snapshot-list-and-prune.md) — Read-only exports have no lifecycle command to list or clean old outputs.
<!-- pb:index:end -->
