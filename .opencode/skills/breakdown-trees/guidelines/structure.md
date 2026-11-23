# Structure: topology, links, versions

Structure is data in front matter. Change it with `bd` commands so ordering,
cycles, and pins stay consistent; never hand-edit `contains` or `links` unless
the tool cannot express the change.

A store's topology is detected once: **containment** when any node declares
`contains`; otherwise **graph** when at least one node has `links`, `stage`, or
a non-empty `layer`/`band`. The choice is per store, never per node. `examples/`
is the default relative-band graph; `docs/breakdown/` is a containment store.

## Graph stores

In a graph store `links` is the child relation. Each edge is authored on its
parent as `parent -> child` with a full ref and a type. Out-edges are authored;
in-edges are derived and are never rewritten.

```bash
bd new --parent REF --type breaks_down --band BAND [--subpath SUB] [--order N]  # relative
bd new --parent REF --type breaks_down --stage N [--order N]      # absolute mode
bd link FROM TO --type supports
bd unlink FROM TO [--type TYPE]
```

Bands have two modes, selected per store.

- **Relative mode (default).** When no node declares `stage`, every node needs a
  non-empty `band` (or `layer` path); missing/empty is `graph-layer-missing` /
  `graph-layer-invalid`, and a bad `band`/`subpath` is also
  `graph-layer-invalid`.
  The first segment is the band; later segments are explicit subfolders. Band
  order and nesting are derived from cross-band links by the shortest-path rule:
  a top-level band lies on a shortest root→sink path, every other band nests
  under its deepest already-placed parent (ties by name), so a detour may nest
  while equal-length branches stay top-level. `order`
  (default `0`) positions nodes inside a band; a same-band edge needs
  `order(FROM) < order(TO)`, else `graph-order-back-edge`, including across
  subpaths. See `docs/GRAPH-LAYOUT.md`.
- **Absolute mode (older stores).** When any node declares `stage`, every node
  needs an integer `stage` and an edge must go forward:
  `stage(FROM) < stage(TO)`. `order` breaks ties inside a stage; a
  missing/non-integer stage or a non-integer order is an error.
- `bd link` refuses a back-edge (absolute), a link that would create a band
  cycle (relative), or a same-band order back-edge, and keeps each target list
  sorted by ref.
  Repoint an edge with `bd unlink` then `bd link`; do not hand-sort.
- `group` is ordinary metadata in every topology and places nothing; the graph
  audit warns `graph-group-ignored`. Use `band` plus `subpath` instead.
- A node reached through several parents appears once in a view. There is no
  `multiple-parents`, per-view `duplicate-id`, or `external-link` in a graph store.
- `bd contain` and `bd uncontain` fail in a graph store with "graph stores use
  edges: bd link / bd unlink". Do not use them to move a graph node.
- `bd new` adds a typed link (`--type` defaults to `breaks_down`). Relative mode
  requires `--band` (optional `--subpath`; older `--layer BAND[/SUB]`) and
  refuses `--stage`; absolute mode takes
  `--stage`; both take `--order`. It refuses an explicit `id`.
- Fan-out above 200 warns; insert an intermediate header instead of hundreds of
  direct edges.

## Containment stores

`contains` is an ordered list on the parent; a view is the closure of one ref
and must be a tree.

```bash
bd new --parent REF --field title=... --field phase=...   # next global id
bd contain P C --before REF
bd contain P C --after REF
bd uncontain P C
```

- Order is meaningful: `--before`/`--after` place the child relative to an
  existing sibling; passing both is refused.
- Moving a child is two operations: `bd uncontain P C`, then
  `bd contain NEW C --before REF`.
- `contain` refuses self-containment, cycles, duplicates, and unknown
  siblings. A node reachable twice in one view is `multiple-parents`.
- A node without `contains` is a leaf; nothing is inherited. `contains` holds
  full refs only, and `bd new` appends the full `<newid>-1`.
- `contain` and `uncontain` accept a bare id as a selector and resolve it in the
  selected view; they always write full refs.
- `bd new` refuses an explicit `id` and derives no placement fields.

Containment decides what a containment view shows. A fact that belongs to
another branch does not get contained "for now" — it gets its own node in its
own place.

## Links in a containment store

`links` is an extra typed edge graph, kept a DAG by convention: containment
cycles are checked (`containment-cycle`), link cycles are neither refused nor
reported. Every `to` is a full ref. A link never pulls a node into a view, but
it keeps its target reachable and a link to another containment root is not
`external-link`. A scalar link (`links: ['10-1']`) takes its type from the
target node's `type`; the mapping form carries an edge-specific label or
freshness.

```bash
bd link FROM TO --type supports --propagates
bd unlink FROM TO [--type TYPE]
```

- `--type` is required and must be non-empty; duplicate edges are refused.
- `--propagates` marks the edge as tracking the target's body: the edge stores
  a `pinned` hash and `bd stale` reports when it moves. Do not add it by
  reflex — only for an edge whose meaning depends on the target's current
  text.
- `unlink` errors when nothing matched, so a silent no-op cannot mask a typo.

## Versions

A version is a node file in the same checkout, not a branch. Every file is
`<id>-<version>.md`; versions of one id are peers.

```bash
bd versions ID              # peer files of one id, ascending by version
bd clone REF                # copy to the next free version of the same id
bd clone REF --version N    # explicit version slot
bd clone REF --subtree      # copy the node and every descendant
bd replace OLD NEW          # wire NEW in at OLD's index (containment) or inbound links (graph)
bd delete REF               # delete a version (refuses ROOT/reachable/referenced)
bd delete REF --force       # delete anyway
bd diff LEFT RIGHT          # compare two views id by id
```

- In a containment store, the version current in a view is the one its parent's
  `contains` names. In a graph store, an edge pins a full ref; a view warns
  (`graph-duplicate-version`) when two versions of one id are reachable. There
  is no per-node pointer and switching needs no copy step.
- `bd clone` copies the source file, including its declared `contains`, and
  wires nothing into the current view; a containment version that omits
  `contains` is a leaf, not an inheritor.
- `bd clone REF --subtree` clones every descendant and rewrites each cloned
  parent's child relation (`contains`, or `links` in a graph store), producing a
  self-contained copy; the original stays untouched. `--version` cannot be
  combined with `--subtree`.
- `bd replace OLD NEW` is the separate wiring step: it puts NEW at OLD's exact
  index in its parent's `contains` (containment), repoints inbound links
  (graph), or repoints `ROOT` when OLD is the store root; OLD's file stays as a
  peer. Clone and swap in one logical flow with `bd clone REF --subtree` then
  `bd replace REF <printed new root ref>`. If OLD is outside the default view,
  `bd replace` errors. Multiple parents is a containment error; graph edges may
  have several.
- In a containment store, to make another version current, repoint the parent
  with `bd contain` / `bd uncontain`, or use `bd clone REF` then `bd replace REF
  NEW`. To choose a different position, run `bd uncontain P OLD`, then
  `bd contain P NEW --before NEXT` (the `duplicate-id` rule forbids both
  versions in one view).
- Refs inside `contains`/`links` are full and exact (`6-2`, not `6`); a bare
  data ref is `bare-ref`.
- A classic store with bare `nodes/<id>.md` files converts once with
  `bd migrate [--dry-run]`.

## Solutions

```bash
bd solution new NAME                 # git worktree ../NAME on branch NAME
bd solution new NAME --path DIR      # explicit worktree path
bd solution new NAME --from REF      # branch start point (default: HEAD)
bd solution list                     # worktrees and checkouts holding this store
bd solution remove NAME|PATH [--force]
```

Git owns the solution boundary: one worktree per solution, merge in git.
`bd work` is a layout inside one checkout and never a branch mechanism. A
solution never sees another branch's nodes or versions; merge before repointing
to them.

## Switching trees

Three distinct operations, often confused:

| Goal | Command |
|---|---|
| Change the store default view | `bd root REF` / `bd root --clear` |
| Change the view in the work area | `bd work REF` |
| Repoint one edge | graph: `bd unlink FROM TO` then `bd link FROM NEW`; containment: `bd uncontain P OLD` then `bd contain P NEW --before REF`, or `bd replace OLD NEW` |

None of them copies a file over another: the parent's `contains` (containment)
or the inbound edge (graph) is the record of which version a view uses.
