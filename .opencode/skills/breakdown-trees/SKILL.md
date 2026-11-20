---
name: breakdown-trees
description: >
  Use when working in a `bd` breakdown store — locating the store, browsing a
  containment view, editing nodes through the single `bd_work/` area,
  restructuring `contains`, adding typed `links`, creating or deleting
  versions, creating solution worktrees, or validating with `bd check` and
  `bd stale`. Covers the filesystem model (flat `nodes/`, filename as identity
  and version), full-ref data, bare ids as selectors, view resolution and
  `ROOT`, the work-area symlink contract, issue codes, and the browse → edit →
  validate loop with exact `bd` commands.
  Use ONLY as the mechanism for a `bd` store or the `bd_tree` tool; for which
  layer owns a fact use `product-breakdown`, for judging whether a tree is
  right use `pb-alignment`, for article claims use `article-breakdown`.
---

`bd` stores a numeric containment graph on disk. Node files under `nodes/`
(`.bd_tree/nodes/` in a project layout) are the only source of truth.
Everything else — `bd_work/` and `bd export` output — is derived and
disposable. One store per checkout; a git worktree has its own store.

This skill is the mechanism: how to find the store, read one view, change
structure, and prove the result valid. It never decides what a node should say.

## Source of truth: the store

- **Filename is identity and version** — every file is `<id>-<version>.md`,
  version >= 1; `5-1.md` and `5-2.md` are peer versions of id `5`.
- **Data refs are full `id-version`** — `contains`, `links`, and `ROOT` never
  hold a bare id; a bare data ref is a `bare-ref` check error. A bare id on the
  command line is a selector resolved inside the selected view and is never
  written to data.
- **`contains` is an ordered list** — order is data; a view is the closure of
  one ref, and a node may appear in it only once. A node without `contains` is
  a leaf; there is no inheritance.
- **`contains` is a tree per view** — two parents in one view is
  `multiple-parents`, and two versions of the same logical id in one view is
  `duplicate-id`; the chain selects exactly one version per id.
- **`links` is a DAG** — typed edges that never add nodes to a view; an edge
  leaving the view keeps its target out but keeps it reachable. A link to
  another containment root is intentional and not an `external-link`; other
  outside targets warn.
- **Front matter is arbitrary** — only `id`, `legacy`, `contains`, `links` are
  reserved. Add no schema unless the project asks for one. Placement comes from
  `folder`/`name` or the title (`<ref>-<title-slug>.md`); `home` means nothing.
- **Structural edits preserve bytes** — `bd` rewrites only its own block;
  unrelated fields and body text survive.

## One work area

`<project>/bd_work/` is the project's only writable area and holds one view at
a time. `bd work REF` replaces its contents: node `.md` files become symlinks
into the store, while `INDEX.md`, `AGENTS.md`, `REFS.md` are generated regular
files. `bd work REF+N` (same `+N` suffix as `show`/`tree`) materializes only
the first N descendant levels; the view is still the full closure, the area
holds a prefix. `bd current` reports the area view as `REF+N`.

- **Edit through the area** — `bd edit REF` prints the path; writing it writes
  the store file, and errors when the ref is not in the active view.
- **Never keep two work folders** — switch with `bd work REF`, never side by
  side, and never read outside the one area you were given.
- **Never hand-edit generated files** and never copy node content into the
  area: no sync layer exists.
- **Commit node files only** — `bd_work/` and exports are ignored derived
  output.
- **A snapshot is not an area** — `bd export tree`, `bd export context`, and
  `bd export dot` write disposable output somewhere else.

## Versions and branches are disjoint

A version is a node file inside one checkout. A branch is a git worktree and
owns the solution boundary. A view crosses neither, so never resolve a ref
through a branch name.

- The version current in a view is the one its parent's `contains` names; there
  is no per-node pointer and no copy step.
- `bd version REF [--version N]` copies a ref to the next free version of the
  same logical id; `bd delete REF [--force]` deletes a version, refusing `ROOT`,
  a reachable ref, or one referenced by `contains`/`links` unless `--force`;
  `bd versions ID` lists peers; `bd diff LEFT RIGHT` compares two views id by id.
- `bd solution new NAME` creates a worktree; `bd work` only changes the layout
  inside whichever checkout you already are in.

## Session start

1. Locate: `bd` walks up for `nodes/` or `.bd_tree/nodes/`; set `BD_ROOT` or
   pass `--root` when the store is nested.
2. Baseline: `bd check` and `bd stale` — know what was already broken.
3. Shape: `bd tree --depth 1`, `bd views`, `bd path REF`.
4. Enter: `bd work REF`, then `bd current` to confirm the area and its view.

## The loop

```bash
export BD_ROOT=path/to/project       # or: bd <cmd> --root path/to/project
bd check                             # exit 0 = no errors; do this first
bd tree --depth 1                    # outline; default depth 2, 0 = unlimited
bd show 5-1+2 --max-chars 800        # node plus 2 levels of descendant bodies
bd find TERM --limit 5               # titles, summaries, bodies, string fields
bd find 'PATTERN' --regex --view REF # regex; --all searches every node
bd path REF                          # ancestry, for orientation

bd work REF                          # build/replace bd_work for one view
bd work REF+1                        # same, first two levels only
$EDITOR "$(bd edit REF)"             # edit the store file through the symlink

bd contain P C --before REF          # order is structure, not a field edit
bd uncontain P C
bd link FROM TO --type supports --propagates
bd unlink FROM TO

bd work --status                     # symlinks intact?
bd check && bd stale                 # structure, then freshness
```

Validation loop: edit, `bd check`, fix, re-run, and only then `bd stale` plus
`bd reconcile` when a propagating edge's pin moved. Never report a change as
done with a failing `bd check`.

## Route the work

| Ask | Read |
|---|---|
| How do I read `tree` / `show` output, and which view am I in? | [`guidelines/browsing.md`](guidelines/browsing.md) |
| Where do I edit, and why did my edit not reach the store? | [`guidelines/editing.md`](guidelines/editing.md) |
| Move a node, add an edge, create or delete a version | [`guidelines/structure.md`](guidelines/structure.md) |
| `bd check` printed a code I do not recognise | [`guidelines/validation.md`](guidelines/validation.md) |
| Which layer should own this fact? | the `product-breakdown` skill |
| Is this tree actually right? | the `pb-alignment` skill |

## Gotchas

- **A direct store edit bypasses the view check.** `.bd_tree/nodes/<ref>.md`
  (full `id-version`) works for a ref outside the active view; that is an escape
  hatch, not the route. Prefer `bd edit REF`.
- **Editors replace symlinks.** If `bd work --status` reports detached files,
  `bd work --writeback` keeps the edits and `--clean` discards them. Switching
  views with detached files is refused.
- **`bd check` validates every node-rooted view.** `--view` narrows what is
  reported, not what is checked.
- **Warnings do not fail the build.** `external-link`, `untracked-link`,
  `stale-link`, `oversize`, `unreachable-node` exit 0; only `error` issues exit 1.
- **Links cross views.** A link to another containment root (for example a
  history view) is not `external-link`; `bd show REF --links` lists it.
- **A declared but missing `ROOT` is surfaced, never replaced.** That is
  `root-ref-missing`; clearing `ROOT` hides a real break.
- **Bare ids are selectors, not data.** `bd show 5` resolves inside the selected
  view, but `contains`, `links`, and `ROOT` must name `5-1`; a bare data ref is
  `bare-ref`.
- **Three different root operations.** `bd root REF` changes the default view,
  `bd work REF` changes the area's view, `bd contain`/`bd uncontain` repoints
  one parent. Do not use one to mean another.
- **No locking.** Concurrent edits race; git is the conflict detector.
- **Exit codes** — 0 success, 1 check or navigation failure, 2 structural
  refusal (`BreakdownError`).

Style: apply the `caveman` skill in notes and reports.
