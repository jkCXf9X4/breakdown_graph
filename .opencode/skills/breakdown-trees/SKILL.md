---
name: breakdown-trees
description: >
  Use when working in a `bd` breakdown store — locating the store (`.bd_root`,
  `BD_ROOT`, `--root`), browsing a containment view, editing nodes through the
  single `bd_work/` area, restructuring `contains`, adding typed `links`,
  versioning with `clone`/`replace`/`delete`, creating solution worktrees, or
  validating with `bd check`, `bd stale`, and `reconcile`. Covers the
  filesystem model (flat `nodes/` or `.bd_tree/nodes/`, filename as identity
  and version), full-ref data, bare ids as selectors, view resolution and
  `ROOT`, the work-area symlink contract and `+N`/`--depth` materialization,
  issue codes, and the browse → edit → validate loop with exact `bd` commands.
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
- **Two layouts, one model** — classic: `nodes/` at the store root; project:
  `.bd_tree/nodes/` under a project root. `bd init DIR` creates a store with
  one root node.
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
- **`links` is a typed edge graph** — edges never add nodes to a view; an edge
  leaving the view keeps its target out but keeps it reachable. A link to
  another containment root is intentional and not an `external-link`; an
  existing target outside the view warns, a missing target is the error
  `dangling-link`. Containment cycles are checked (`containment-cycle`); link
  cycles are neither refused nor reported, so keep links a DAG by convention.
- **Front matter is arbitrary** — the only built-in keys are structural (`id`,
  `legacy`, `contains`, `links`), link freshness (`to`, `type`, `propagates`,
  `pinned`), and presentation (`folder`, `name`, `title`). Everything else is
  yours; add no schema unless the project asks for one. Placement is `folder`
  plus `name`, else `<ref>-<title-slug>.md`, else `<ref>.md` when the title is
  unusable. `home` means nothing.
- **Structural edits preserve bytes** — `bd` rewrites only its own block;
  unrelated fields and body text survive.

## One work area

`<project>/bd_work/` is the project's only writable area and holds one view at
a time. `bd work REF` replaces its contents: node `.md` files become symlinks
into the store, while `INDEX.md`, `AGENTS.md`, `REFS.md` are generated regular
files. With no REF, `bd work` uses the default view. `bd work REF+N` (or
`--depth N`) materializes only the first N descendant levels; the view is still
the full closure, the area holds a prefix. `N=0` leaves the root alone. Note
that `bd tree --depth 0` means unlimited, while `show`/`work` `+0` means the
root only. `bd current` reports the area as `REF+N`.

- **Edit through the area** — `bd edit REF` prints the placement path; writing
  it writes the store file, and it exits 2 when REF is outside the materialized
  `REF+N` prefix (not merely outside the full closure).
- **Never keep two work folders** — switch with `bd work REF`, never side by
  side, and never read outside the one area you were given.
- **Never hand-edit generated files** and never copy node content into the
  area: no sync layer exists.
- **Commit node files only** — `bd_work/` is derived and `bd init` ignores it;
  an export directory is not auto-ignored, so keep it out of git yourself.
- **A snapshot is not an area** — `bd export tree`, `bd export context`, and
  `bd export dot` write disposable output somewhere else.

## Versions and branches are disjoint

A version is a node file inside one checkout. A branch is a git worktree and
owns the solution boundary. A view crosses neither, so never resolve a ref
through a branch name.

- The version current in a view is the one its parent's `contains` names; there
  is no per-node pointer and switching needs no copy step.
- `bd clone REF [--version N] [--subtree]` copies a ref to the next
  free version of the same logical id; `bd clone REF --subtree` copies every
  containment descendant and rewires each cloned parent to the cloned children,
  leaving the original tree untouched (`--version` cannot be combined with
  `--subtree`). `bd replace OLD NEW` is the separate wiring step: it finds OLD
  in the default view and puts NEW at OLD's exact index in its parent's
  `contains`, or repoints `ROOT` when OLD is the store root, leaving the old
  file as a peer. Clone and swap in one logical flow with `bd clone REF
  --subtree` then `bd replace REF <printed new root ref>`. If OLD is outside the
  default view, `bd replace` errors and asks for `bd contain`; multiple parents
  is an error.
  `bd delete REF [--force]` deletes a version, refusing `ROOT`, a reachable ref,
  or one referenced by `contains`/`links` unless `--force`; `bd versions ID`
  lists peers; `bd diff LEFT RIGHT` compares two views id by id. Use the manual
  `bd uncontain P OLD`, then `bd contain P NEW --before NEXT` only to choose a
  different position (the `duplicate-id` rule forbids both versions in one view).
- A classic store with bare `nodes/<id>.md` converts once with `bd migrate
  [--dry-run]`.
- `bd solution new NAME [--path PATH] [--from REF]` creates a worktree,
  `bd solution list` shows them, and `bd solution remove NAME|PATH [--force]`
  removes one; `bd work` only changes the layout inside whichever checkout you
  already are in.

## Session start

1. Locate: `bd` resolves `--root`, then `$BD_ROOT`, then the upward walk (at
   each directory a store there first, then a `.bd_root` pointer), then a
   downward scan to depth 3 for a unique store. Several stores below the cwd is
   refused; a `.bd_root` file holds one store path.
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
bd work REF --depth 2                # equivalent explicit form
$EDITOR "$(bd edit REF)"             # edit the store file through the symlink

bd contain P C --before REF          # order is structure, not a field edit
bd uncontain P C
bd link FROM TO --type supports --propagates
bd unlink FROM TO

bd work --status                     # symlinks intact?
bd check && bd stale                 # structure, then freshness
bd reconcile REF                     # or --all, after reviewing a stale edge
```

Validation loop: edit, `bd check`, fix, re-run, and only then `bd stale` plus
`bd reconcile REF` (or `--all`) when a propagating edge's pin moved — bare
`bd reconcile` is refused. Never report a change as done with a failing
`bd check`.

## Route the work

| Ask | Read |
|---|---|
| How do I read `tree` / `show` output, and which view am I in? | [`guidelines/browsing.md`](guidelines/browsing.md) |
| Where do I edit, and why did my edit not reach the store? | [`guidelines/editing.md`](guidelines/editing.md) |
| Move a node, add an edge, clone a subtree, switch trees | [`guidelines/structure.md`](guidelines/structure.md) |
| `bd check` printed a code I do not recognise | [`guidelines/validation.md`](guidelines/validation.md) |
| Which layer should own this fact? | the `product-breakdown` skill |
| Is this tree actually right? | the `pb-alignment` skill |

## Gotchas

- **A direct store edit bypasses the view check.** `.bd_tree/nodes/<id>-<version>.md`
  (or `nodes/<id>-<version>.md` in a classic store) works for a ref outside the
  active view; that is an escape hatch, not the route. Prefer `bd edit REF`.
- **Editors replace symlinks.** If `bd work --status` reports detached files,
  `bd work --writeback` keeps the edits and `--clean` discards them. Switching
  views with detached files is refused.
- **`bd check` spans the store, then narrows.** The store scan and tree
  shape/duplicate checks cover every node-rooted view; reachability, freshness,
  size, and `--require` run for the checked view. `--view` narrows reporting,
  not the store scan.
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
  refusal (`BreakdownError`) or argparse usage error; malformed ref/depth on
  `show`/`tree` exits 1, on `work` it exits 2.

Style: apply the `caveman` skill in notes and reports.
