---
title: Operation
summary: How bd_tree is installed, released, and run day to day.
---

# Operation

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with `pb registers`. -->
- **INFO-023** [Init scaffolds a hidden-store project](init-scaffolds-a-hidden-store-project.md) — bd init writes .bd_tree/nodes/1.md, a bd_work ignore entry, and the next commands.
- **INFO-025** [Switching views replaces the work area](switching-views-replaces-the-work-area.md) — bd work REF rebuilds the same bd_work path and removes links left by the previous view.
- **INFO-027** [Detached edits block a switch until writeback](detached-edits-block-a-switch-until-writeback.md) — A regular file in the area is preserved by writeback or discarded explicitly with clean.
- **INFO-029** [Snapshots stay outside the work area](snapshots-stay-outside-the-work-area.md) — bd view and bd export write disposable copies and never become a second writable layout.
- **INFO-031** [Generated files stay generated](generated-files-stay-generated.md) — INDEX, REFS, and AGENTS are rewritten by the tool and excluded from hand editing.
- **INFO-032** [Solution worktrees are created per branch](solution-worktrees-are-created-per-branch.md) — bd solution new adds a git worktree and prints the project directory and default-view command.
- **INFO-033** [Discovery walks up to nodes or .bd_tree](discovery-walks-up-to-nodes-or-bd-tree.md) — A command run in the project root or a descendant finds the nearest store.
<!-- pb:index:end -->
