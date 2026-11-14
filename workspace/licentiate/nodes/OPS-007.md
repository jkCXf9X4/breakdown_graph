---
id: OPS-007
type: operation
layer: operation
home: operation/submodule-workflow.md
title: Submodule workflow
summary: How paper content enters and leaves the kappa
date: 2026-11-11
status: current
---

# Submodule workflow

All six paper repositories are submodules. `template/`, `3rd_party/references/`, and `3rd_party/article_common_artifacts/` are submodules too.

**Initialize:**

- Run `git submodule update --init --recursive` after clone, or when a pin moves.
- `--recursive` reaches Paper IV's nested toolchain and case submodules.
- Paper submodules track branch `kappa`.
- `3rd_party/references` and `3rd_party/article_common_artifacts` track `main`.
- `template` tracks `master`.

**Change a paper:**

- Enter the paper repo: `cd papers/<name>`.
- Edit and build inside that repo, using its own `build.py`.
- Commit on `kappa` in the paper repo, then push.
- Stage the new pointer here: `git add papers/<name>`.
- Commit the pointer with a message that says why the pin moves.
- Commit every edit in the paper repo; never leave a dirty submodule as the change.
- Never change a pin without an intentional reason, stated in the commit message.

**Freeze exception:**

- Compilation-only adaptations live on `kappa`, not on the paper's own branch.
- `final-submission` tags mark the frozen paper versions.
- Paper I sits nine commits past `final-submission` for source-only acronym and house-style fixes.
- Papers II–IV sit past the tag at their `kappa` adapter commits, by 22, 26 and 16 commits.
- The two co-simulation repositories also sit past the tag, by 7 and 10 commits, and no longer feed the book (`INT-002`).
- Those commits carry the house-style adapters and compilation-only fixes; they change no paper content.
- Paper IV pin sits at `101c21f`; only its DOI and venue wait on publication (`IMP-012`).

**Owns:**

- The steps that move paper content into the kappa through submodule pins.

**Excludes:**

- Pin layout and per-paper staging (`OPS-005`).
- Which paper plays which role (`ARG-003`).
- Library pin mechanics for references (`OPS-008`).
- What is frozen at release (`OPS-010`).