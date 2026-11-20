---
id: INFO-032
type: info
title: Solution worktrees are created per branch
summary: bd solution new adds a git worktree and prints the project directory and default-view command.
date: 2026-11-20
status: current
---

# Solution worktrees are created per branch

`bd solution new NAME` runs `git worktree add` for branch `NAME` and prints where to go and which view to build.

- **Default path:** without `--path`, the worktree is the sibling `../NAME` of the repository root.
- **Branch:** `new` creates `NAME` from `--from` or `HEAD`, and an existing branch is checked out instead.
- **Output:** the CLI prints `worktree`, `branch`, `project`, `cd <project-dir>`, and `bd work <view>`.
- **Store location:** `_relative_store` and `_project_relative` translate the store path into the new checkout for both flat and hidden layouts.
- **Listing:** `bd solution list` parses `git worktree list --porcelain` and marks the primary worktree and checkouts holding the store.
- **Removal:** `bd solution remove` removes the worktree and keeps the branch; the primary worktree is refused.
