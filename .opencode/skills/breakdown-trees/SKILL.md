---
name: breakdown-trees
description: >
  Use when working in a `bd` breakdown store — locating the store (`.bd_root`,
  `BD_ROOT`, `--root`), detecting its topology (graph from forward `links` with
  relative `layer` or absolute `stage` bands, or containment from `contains`),
  browsing one view, editing nodes
  through the single `bd_work/` area, restructuring a graph with
  `link`/`unlink` or a containment tree with `contain`/`uncontain`, adding typed
  `links`, versioning with `clone`/`replace`/`delete`, creating solution
  worktrees, or validating with `bd check`, `bd audit`, `bd stale`, and
  `reconcile`. Covers the filesystem model (flat `nodes/` or
  `.bd_tree/nodes/`, filename as identity and version), full-ref data, bare ids
  as selectors, view resolution and `ROOT`, graph `layer` paths with
  shortest-path band inference and `group` inert, the work-area
  symlink contract and `+N`/`--depth` materialization, containment section
  placement (root-relative and nested), issue codes, and the browse → edit →
  validate loop with exact `bd` commands. The layout algorithm lives in
  `docs/GRAPH-LAYOUT.md`.
  Use ONLY as the mechanism for a `bd` store or the `bd_tree` tool; for which
  layer owns a fact use `product-breakdown`, for judging whether a tree is
  right use `pb-alignment`, for article claims use `article-breakdown`.
---

`bd` stores a numeric graph of nodes on disk, with one of two topologies. Node
files under `nodes/` (`.bd_tree/nodes/` in a project layout) are the only source
of truth. Everything else — `bd_work/` and `bd export` output — is derived and
disposable. One store per checkout; a git worktree has its own store.

A store is a **containment store** when any node declares `contains`; otherwise
it is a **graph store** when at least one node declares `links`, `stage`, or a
non-empty `layer` (an empty or legacy store is containment). Detection is per
store, never per node. The default example `examples/` is a relative-layer
graph; `docs/breakdown/` is a containment store.

This skill is the mechanism: how to find the store, detect its topology, read
one view, change structure, and prove the result valid. It never decides what a
node should say.

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
- **Topology is detected per store** — containment when any node declares
  `contains`; otherwise graph when at least one node has `links`, `stage`, or a
  non-empty `layer`. A view is the
  closure of one ref over that store's child relation.
- **A containment store** — `contains` is an ordered list; order is data, and a
  view is the closure of one ref where a node may appear only once. A node
  without `contains` is a leaf; there is no inheritance. It is a tree per view:
  two parents is `multiple-parents`, and two versions of one logical id is
  `duplicate-id`; the chain selects exactly one version per id. `links` is an
  extra typed DAG: an edge never adds a node to a view, an edge leaving the view
  keeps its target out but reachable, a link to another containment root is not
  an `external-link`, and a missing target is `dangling-link`.
- **A graph store** — `links` is the child relation: parent→child full refs,
  typed, with `propagates`/`pinned` preserved. Out-edges are authored, in-edges
  derived. A node with several parents appears once;
  `multiple-parents`, per-view `duplicate-id`, and `external-link` do not apply.
  Bands have two modes. When any node declares `stage` (absolute mode), every
  node needs an integer `stage`, edges must go forward
  (`stage(parent) < stage(child)`), and `order` breaks ties inside a stage.
  Otherwise (relative mode, the default example) every node needs a non-empty
  `layer` path: the first segment is the band, later segments are an explicit
  subpath. The band order and nesting are derived from cross-band edges by the
  shortest-path rule — a top-level band lies on a shortest root→sink path;
  every other band nests under its deepest already-placed parent, ties by name
  — and `order` positions nodes inside a band, where a same-band edge needs
  `order(source) < order(target)`, including across subpaths. Keep `links`
  sorted; `bd link` refuses a back-edge, a band cycle, or
  a same-band order back-edge, and sorts targets. A view warns
  (`graph-duplicate-version`) when two versions of one id are reachable. See
  `docs/GRAPH-LAYOUT.md` for the algorithm and diagnostics.
- **Front matter is arbitrary** — the only built-in keys are structural (`id`,
  `legacy`, `contains`, `links`), graph band/ordering (`layer`, `stage`,
  `order`, `group`), link
  freshness (`to`, `type`, `propagates`, `pinned`), and containment presentation
  (`section`, `name`, `title`). Everything else is yours; add no schema unless
  the project asks for one. In a containment store, `section` is the only key
  that opens directories: `section: true` uses the placement name,
  `section: "<dir>"` is verbatim and may span segments, and a leading `/`
  resolves from the output root instead of the parent prefix. Two nodes may
  share a directory unless both have containment children there. Otherwise
  placement is `name`, else `<ref>-<title-slug>.md`, else `<ref>.md` when the
  title is unusable. A graph store uses the derived band layout instead: the
  layer path's band plus inferred nesting and explicit subpaths. `group` is
  ordinary metadata in every topology and places nothing; the graph audit warns
  `graph-group-ignored`. `folder` is
  inert ordinary front matter; `home` means nothing.
- **Structural edits preserve bytes** — `bd` rewrites only its own block;
  unrelated fields and body text survive.

## One work area

`<project>/bd_work/` is the project's only writable area and holds one view at
a time. `bd work REF` replaces its contents: node `.md` files become symlinks
into the store, while `INDEX.md`, `AGENTS.md`, `REFS.md` are generated regular
files. With no REF, `bd work` uses the default view. In a graph store the
layout is the graph bands `<NN>-<slug(band)>` (relative `layer` paths with
inferred nesting and explicit subpaths, or absolute stages);
in a containment store it is
`section`/`name` placement. `bd work REF+N` (or `--depth N`) materializes only
the first N descendant levels; a graph level is a link hop. The view is still
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
- **A snapshot is not an area** — `bd export tree`, `bd export graph`,
  `bd export context`, and `bd export dot` write disposable output somewhere
  else.

## Versions and branches are disjoint

A version is a node file inside one checkout. A branch is a git worktree and
owns the solution boundary. A view crosses neither, so never resolve a ref
through a branch name.

- In a containment store, the version current in a view is the one its parent's
  `contains` names. In a graph store, an edge pins a full ref; a view warns
  (`graph-duplicate-version`) when two versions of one id are reachable. There
  is no per-node pointer and switching needs no copy step.
- `bd clone REF [--version N] [--subtree]` copies a ref to the next
  free version of the same logical id; `bd clone REF --subtree` copies every
  descendant and rewires each cloned parent to the cloned children (`contains`,
  or `links` in a graph store), leaving the original untouched (`--version`
  cannot be combined with `--subtree`). `bd replace OLD NEW` is the separate
  wiring step: it puts NEW at OLD's index in its parent's `contains`
  (containment), repoints inbound links (graph), or repoints `ROOT` when OLD is
  the store root, leaving the old file as a peer. Clone and swap in one logical
  flow with `bd clone REF --subtree` then `bd replace REF <printed new root
  ref>`. If OLD is outside the default view, `bd replace` errors. Multiple
  parents is a containment error; graph edges may have several.
  `bd delete REF [--force]` deletes a version, refusing `ROOT`, a reachable ref,
  or one referenced by `contains`/`links` unless `--force`; `bd versions ID`
  lists peers; `bd diff LEFT RIGHT` compares two views id by id. In a containment
  store, use the manual `bd uncontain P OLD`, then `bd contain P NEW --before
  NEXT` only to choose a different position (the `duplicate-id` rule forbids both
  versions in one view).
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
2. Detect the topology (`Store.model`, visible in `bd tree`/`bd views` output):
   graph uses forward `links` with relative `layer` or absolute `stage` bands;
   containment uses `contains`.
3. Baseline: `bd check` (topology-aware), `bd audit` in a graph store, and
   `bd stale` — know what was already broken.
4. Shape: `bd tree --depth 1`, `bd views`, `bd path REF`; in a graph store also
   `bd graph`, `bd out REF`, `bd in REF`.
5. Enter: `bd work REF`, then `bd current` to confirm the area and its view.

## The loop

```bash
export BD_ROOT=path/to/project       # or: bd <cmd> --root path/to/project
bd check                             # topology-aware; exit 0 = no errors
bd audit                             # graph store: layer/stage and edge audit
bd tree --depth 1                    # graph: layer/stage bands; containment: outline
bd graph                             # graph: forward render with in/out edges
bd out REF && bd in REF              # graph: authored out / derived in
bd show 5-1+2 --max-chars 800        # node plus 2 descendant levels (graph: hops)
bd find TERM --limit 5               # titles, summaries, bodies, string fields
bd find 'PATTERN' --regex --view REF # regex; --all searches every node
bd path REF                          # ancestry; graph: first parent when ambiguous

bd work REF                          # build/replace bd_work for one view
bd work REF+1                        # same, first two levels only
bd work REF --depth 2                # equivalent explicit form
$EDITOR "$(bd edit REF)"             # edit the store file through the symlink

# graph store: links are the child relation
bd new --parent REF --type breaks_down --layer BAND[/SUB] --order N   # relative mode
bd new --parent REF --type breaks_down --stage N --order N     # absolute mode
bd link FROM TO --type supports      # refuses a back-edge or band cycle, sorts targets
bd unlink FROM TO
# containment store: contains is the child relation
bd contain P C --before REF          # order is structure, not a field edit
bd uncontain P C
bd link FROM TO --type supports --propagates

bd work --status                     # symlinks intact?
bd check && bd stale                 # structure, then freshness
bd reconcile REF                     # or --all, after reviewing a stale edge
```

Validation loop: edit, `bd check` (and `bd audit` in a graph store), fix, re-run,
and only then `bd stale` plus `bd reconcile REF` (or `--all`) when a propagating
edge's pin moved — bare `bd reconcile` is refused. Never report a change as done
with a failing `bd check`.

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
- **`bd check` dispatches on topology, then narrows.** In a containment store
  the store scan and tree shape/duplicate checks cover every node-rooted view; in
  a graph store it runs the graph audit for the anchor. `--view` narrows
  reporting, not the store scan.
- **Warnings do not fail the build.** In a containment store `external-link`,
  `untracked-link`, `stale-link`, `oversize`, `unreachable-node`; in a graph
  store `graph-orphan`, `graph-wide-fanout`, `graph-duplicate-version`,
  `graph-unsorted-links`, `graph-group-ignored`. Only `error` issues exit 1.
- **Containment links cross views.** A link to another containment root (for
  example a history view) is not `external-link`; `bd show REF --links` lists it.
  In a graph store `links` is the child relation, not a side edge.
- **Graph edges go forward.** In absolute mode, repointing an edge to a lower or
  equal stage is a `graph-back-edge`; in relative mode, a link that would create
  a band cycle is `graph-layer-cycle`, and a same-band edge not forward by
  `order` is `graph-order-back-edge`, including across subpaths. Fix with
  `bd unlink` then `bd link`.
  `bd contain` /
  `bd uncontain` fail in a graph store.
- **A declared but missing `ROOT` is surfaced, never replaced.** That is
  `root-ref-missing`; clearing `ROOT` hides a real break.
- **Bare ids are selectors, not data.** `bd show 5` resolves inside the selected
  view, but `contains`, `links`, and `ROOT` must name `5-1`; a bare data ref is
  `bare-ref`.
- **Three different root operations.** `bd root REF` changes the default view,
  `bd work REF` changes the area's view, `bd link`/`bd replace` (graph) or
  `bd contain`/`bd uncontain` (containment) repoints one edge. Do not use one to
  mean another.
- **Writers serialize, editors do not.** `bd` writes under a transient advisory
  lock; edits made outside `bd` race. Git is the conflict detector.
- **Exit codes** — 0 success, 1 check or navigation failure, 2 structural
  refusal (`BreakdownError`) or argparse usage error; malformed ref/depth on
  `show`/`tree` exits 1, on `work` it exits 2.

Style: apply the `caveman` skill in notes and reports.
