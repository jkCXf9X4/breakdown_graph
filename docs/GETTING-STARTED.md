# Getting started

This guide goes from the default graph example to a browsable, editable store
with a work folder, typed links, a containment store, and a second solution in a
git worktree.

You need Python 3.10+ and PyYAML. From a clone, install the package:

```sh
pip install .
bd --help
```

## 1. See the default graph store

The repository ships `examples/` as the default store (`ROOT` `1-1`). It is a
graph: no node declares `contains` and every node declares `links`. No node
declares `stage` either, so it is a **relative-layer** graph: each node names a
`layer` path, and the band order and nesting are derived from cross-band links.

```sh
export BD_ROOT=examples
bd check
```

```
10 nodes, 0 errors, 0 warnings (view 1-1)
```

The store layout is unchanged from a containment store:

```
examples/.bd_tree/nodes/1-1.md
examples/.bd_tree/ROOT          # 1-1
examples/.bd_tree/nodes/4-1.md
```

A node file looks like this:

```markdown
---
id: 1
title: Verify the staged graph
layer: intent
links:
  - to: 2-1
    type: breaks_down
  - to: 3-1
    type: breaks_down
---
# Verify the staged graph
```

The filename is identity and version: logical id `1`, version `1`. The rest of
the front matter is arbitrary. `links` declares parent→child edges as full
`id-version` refs; `layer` is a path, and its first segment is the band. The
edges order the bands `intent` → `breakdown` → `claims` → `verification` →
`operation`; leftover path segments are explicit subfolders such as
`claims/structural`.

A store's topology is detected once, per store:

- **Containment** — any store with a `contains` key, including an empty or
  legacy store. `contains` is the ordered child relation.
- **Graph** — no `contains`, and at least one node has `links`, `stage`, or a
  non-empty `layer`. Bands are relative `layer` paths when no node declares
  `stage`; absolute integer `stage`s otherwise (older stores).

Both topologies read the same flat node files. `docs/breakdown/` is a live
containment store; `examples/` is the relative-layer graph. `bd init` creates a
containment root (`contains: []`); `bd init --graph` creates a relative-band
graph root.

## 2. Browse a graph

```sh
bd tree 1-1
bd graph
bd show 2-1+1 --max-chars 400
bd find closure --limit 3
bd path 4-1
bd out 1-1
bd in 4-1
bd views
```

- `tree` renders the derived band layout; `graph` renders the same closure with
  authored `→ out` edges and derived `← in` edges.
- `show REF+N` prints the node body plus N link hops.
- `find` searches titles, summaries, bodies, and front-matter fields.
- `path` prints the ancestor chain, choosing the first parent when a node has
  several. `4-1` has two parents; the chain is deterministic but one of several
  paths.
- `out` lists authored out-edges; `in` lists derived in-edges.
- `views` lists topology roots (graph roots), marking the default with `*`.

A node reached through several parents appears once in a view. A graph store has no
`multiple-parents`, per-view `duplicate-id`, or `external-link` errors.

Exit codes: `bd check` returns 1 on errors and 0 on clean. Structural commands
return 2 on refusal.

## 3. Audit the graph

```sh
bd audit
bd check
```

```
0 errors, 0 warnings
```

The graph audit checks the rules that make the forward graph meaningful. In
relative mode:

- every node has a non-empty `layer` path;
- the first path segment is the band, and later segments are explicit
  subfolders;
- links that cross bands order those bands; a band cycle is
  `graph-layer-cycle`;
- the shortest-path rule chooses which bands are top-level and nests detours
  under an inferred parent; equal-length branches stay top-level;
- within a band, a link needs `order(parent) < order(child)`, else
  `graph-order-back-edge`, including across different subpaths;
- a non-integer `order` is an error;
- links resolve, do not cycle, and are sorted by ref;
- a non-anchor root warns (`graph-orphan`), and out-degree above 200 warns
  (`graph-wide-fanout`).

Nesting is a layout convention, not a semantic proof. The exact rule, tie-breaks,
and worked examples are in [`GRAPH-LAYOUT.md`](GRAPH-LAYOUT.md).

`bd check` dispatches on the store's topology, so it runs this audit for a graph
store and the containment checks for a containment store. `bd audit` is the
explicit graph command; against a containment store it refuses with "this store
is containment", so use `bd check` there.

Absolute stage mode is the older alternative, not a requirement. If any node
declares `stage`, the bands are integer stages: every node needs an integer
`stage`, and every edge must satisfy `stage(parent) < stage(child)`. The modes
are selected per store; do not mix them. A new graph uses `layer`
(`bd init --graph`).

In a graph store, structure is edited with links:

```sh
bd new --parent 1-1 --type breaks_down --layer claims/structural --order 0
bd link 2-1 8-1 --type supports
bd unlink 2-1 8-1 --type supports
```

`bd new` allocates the next global id at version 1 and adds a typed link to the
parent; `--type` defaults to `breaks_down` in a graph store. In relative mode
`--layer` is required and takes `BAND[/SUB]`; `--stage` is refused. In absolute
mode use `--stage`; both take `--order`. `bd link` refuses a back-edge or a band
cycle and keeps each target list sorted by ref. `bd contain` and
`bd uncontain` are containment commands; in a graph store they fail with "graph
stores use edges: bd link / bd unlink".

## 4. Edit in the work area

`bd work` renders a view as a tree of symlinks in the project's single writable
work area, `<project>/bd_work/`. Editing a link edits the store.

```sh
bd work 1-1
bd current                 # <project>/bd_work (view 1-1)
work_dir=$(bd current --path)
ls "$work_dir"
```

In a graph store the layout is the derived band layout, `<NN>-<slug(band)>`,
plus any inferred nested band folder and explicit layer subpath. In relative
mode the label is the band name and `<NN>` is the derived top-level ordinal:

```
00-intent/1-1-verify-the-staged-graph.md
02-claims/structural/4-1-two-parents-one-node.md
INDEX.md  AGENTS.md  REFS.md
```

Inserting a band before others renumbers the later top-level directory prefixes
on the next build; no node is renumbered. A detour band can nest under a parent
band instead of getting its own prefix. In absolute mode the label is the
dominant `layer` in that stage, and `<NN>` is the stage.

Only the node `.md` files are symlinks; `INDEX.md`, `AGENTS.md`, and `REFS.md`
are regular generated files. `bd edit REF` prints the ref's absolute path
inside the active view and errors if the ref is not there. `bd current` is
read-only; `--path` prints only the path and `--view` only the ref, and it
errors if no area exists.

`--status` reports `ok`, `missing`, `wrong-target`, `detached`, `stray`, or
`stale-ref`. If an editor replaces a symlink with a regular file:

```sh
bd work --status
bd work --writeback
```

`--writeback` writes the detached content to the original node, refuses files
without valid front matter, and re-links them.

There is exactly one writable work area. `bd work REF` switches it to another
view by replacing its contents: stale links are removed, and `INDEX.md`,
`REFS.md`, and `AGENTS.md` are rewritten. Never keep two work folders side by
side.

A work area may also materialize only the first `N` descendant levels of a view:
`bd work REF+N`, or `bd work REF --depth N`, where `0` materializes the root
alone and `--depth` overrides a suffix. In a graph store a level is a link hop.
The view itself is still the full closure of one ref, not a smaller view. The
generated headers carry `REF+N`, so `bd current --view` reports it and `bd edit`
only resolves refs that are materialized. A rebuild with a different depth, or a
plain `bd work REF`, replaces the area.

```sh
bd work 1-1+1      # root plus one link hop
bd current --view  # 1-1+1
bd work 1-1        # restore the full closure
```

Read-only snapshots (`bd export tree`, `bd export graph`, `bd export context`,
`bd export dot`) are separate disposable exports, not a second work area. In a
graph store `bd work` and `bd export tree` materialize the same band layout, and
`bd export graph` is the same projection with per-band indexes.

## 5. A containment store

Containment remains fully supported. The product breakdown store in this
repository is a live example:

```sh
bd --root docs/breakdown check
bd --root docs/breakdown tree 1-1 --depth 1
bd --root docs/breakdown show 1-1+1 --max-chars 400
```

```
57 nodes, 0 errors, 0 warnings (view 1-1)
```

`bd init` creates a containment store with one root:

```sh
mkdir -p ~/stores/my-tree
cd ~/stores/my-tree
bd init
```

```
.bd_tree/nodes/1-1.md
.gitignore          # bd_work/
```

```markdown
---
id: 1
title: Root
contains: []
---
# Root
```

Add two nodes and inspect the tree:

```sh
bd new --parent 1-1 --field title="Why does this exist?" --field layer=intent
bd new --parent 1-1 --field title="What is true?"       --field layer=claims
bd tree 1-1
```

```
1-1 Root
+- 2-1 Why does this exist?
`- 3-1 What is true?
```

`bd new` appends the full new ref to the parent's `contains`. `bd check` now
reports three nodes:

```sh
bd check
```

```
3 nodes, 0 errors, 0 warnings (view 1-1)
```

Reorder or move a child:

```sh
bd uncontain 1-1 3-1
bd contain 1-1 3-1 --before 2-1
bd tree 1-1
```

`contain` refuses cycles and duplicates, accepts a bare id as a selector, and
writes full refs. `contains` is the declared list: nothing is inherited, so
every version that has children lists them itself. A bare id on the command
line is a selector resolved inside the selected view and is never written to
data.

In a containment store, `section` is the only presentation key that opens
directories: `section: true` names the directory by the node's placement name
(explicit `name`, else the `title` slug, else the ref), and its containment
descendants land inside; with `title: Evolution` the node becomes
`evolution/evolution.md`. `section: "<dir>"` names the directory verbatim; a
leading `/` resolves it from the output root instead of under the parent prefix.
Otherwise a node is placed by `name` (`<name>.md`), else `<ref>-<title-slug>.md`,
else `<ref>.md` when there is no usable title. `--path-template` sets another
route for the whole view.

## 6. Typed links and freshness

`links` carries typed edges in both topologies. In a graph store those edges are
the child relation; in a containment store they are extra semantic edges that
never add nodes to a view. In the containment store from section 5, add a
propagating edge and track freshness:

```sh
bd link 2-1 3-1 --type supports --propagates
bd stale
```

Then edit a target through its work area, or open it with `bd edit REF`. A
propagating edge pins the target body hash; `bd stale` reports when the target
moves. `--propagates` is opt-in; a `see_also` edge never goes stale.

Reconcile after reviewing the change:

```sh
bd reconcile REF           # or --all
bd stale
```

Remove an edge:

```sh
bd unlink FROM TO --type supports
```

Pins are body hashes, so they survive a rebase.

## 7. Versions and switching

Two separate moves: change the default view root, or switch the view held by the
work area. You can also repoint one parent in a containment store.

```sh
bd root 1-1                 # write ROOT; commands default here
bd root                     # 1-1  (ROOT)
bd work 1-1                 # switch the work area
bd current                  # <project>/bd_work (view 1-1)
bd root --clear             # back to the topology's lowest root
```

`ROOT` is one full ref on one line at the store top level. An explicit ref where
a command takes one still wins over it; with no `ROOT`, a graph store uses its
lowest graph root and a containment store its lowest `(id, version)`. `bd check
--view REF` only narrows reporting, not the checked root. `bd root` changes the
default root used by commands but does not rewrite the view already in
`<project>/bd_work/`; run `bd work REF` for that. `bd views` lists topology roots
and marks the default with `*`.

Versions are node-local alternatives inside one branch:

```sh
bd versions 1
bd clone 1-1 --version 2
bd replace 1-1 1-2
```

`bd clone REF` copies a ref to the next free version of the same logical id (or
to `--version N`) and keeps the source file's declared `contains`; it wires
nothing into a view. `bd clone REF --subtree` clones every descendant and
rewrites each cloned parent's child relation (`contains`, or `links` in a graph
store) so the copy is self-contained; `--version` cannot be combined with
`--subtree`. `bd replace OLD NEW` is the separate wiring step: it puts NEW at
OLD's index in its parent's `contains` (containment), repoints inbound links
(graph), or repoints `ROOT` when OLD is the store root; OLD's file stays as a
peer.

In a containment store, a parent's `contains` names the version that is current
in that view. To choose a different position, run `bd uncontain P OLD`, then
`bd contain P NEW --before NEXT`; the `duplicate-id` rule forbids both versions
in one view. In a graph store, an edge pins a full ref, several parents are
allowed, and a view warns (`graph-duplicate-version`) when two versions of one
id are reachable.

## 8. A second solution with git

A solution is a git branch in a worktree; the flat store is the merge unit.

```sh
git init -b main
git add -A
git commit -m "init store"

bd solution new sol-a
```

`bd solution new` prints:

```
worktree /home/you/stores/sol-a
branch sol-a
project .
cd /home/you/stores/sol-a
bd work 1-1
```

The project directory is printed relative to the worktree. In a nested project,
`cd` into the printed project path instead, for example
`cd /home/you/stores/sol-a/examples`, then run the printed `bd work` command.

```sh
cd ../sol-a
bd work 1-1
$EDITOR "$(bd edit 1-1)"
bd check
git add -A && git commit -m "sol-a: alternative intent"
```

Compare without switching:

```sh
cd ../my-tree
git diff main..sol-a -- .bd_tree/nodes/
bd solution list
```

Remove the checkout when done; the branch remains:

```sh
bd solution remove sol-a
```

If the project is nested inside the repo, use the printed `cd` line to enter the
project path inside the worktree, for example `cd /home/you/stores/sol-a/examples`.
Store discovery then finds `.bd_tree/` there. From the worktree root it also
finds a single store below the current directory; `BD_ROOT` is only needed when
several stores are below that root.

## 9. Feed an agent

Two modes:

```sh
# writable: the single work area for one view
bd work 1-1
bd current

# read-only snapshot: fresh nodes, plus STALE.md and AGENTS.md
bd export context --view 1-1 --out /tmp/bd-context-1-1
```

`bd work` writes `<project>/bd_work/` and is the only work area; the export
directory is a disposable snapshot, not a second area. Both contain an
`AGENTS.md`; the work area also records the branch, commit, and worktree. Tell
the agent to read exactly one directory and not to read outside it, and to use
`bd edit REF` rather than guessing paths. To change view, switch the same area
with `bd work REF` and confirm with `bd current`.

## 10. Use an existing markdown tree

There is no generic importer yet. The pattern is:

1. One file per node version under the store's `nodes/` (`.bd_tree/nodes/` in a
   project layout), named `<id>-<version>.md` with a running integer id and a
   version starting at `1`.
2. `id` matches the logical id in the filename.
3. Pick one topology per store:
   - **Graph (relative, the default):** no `contains` anywhere; a non-empty
     `layer` path on every node; `links` lists parent→child edges as full refs,
     sorted; the cross-band edges derive the band order and nesting.
     `bd init --graph` writes a root with `layer: root`.
   - **Graph (absolute, older stores):** no `contains` anywhere; integer `stage`
     on every node; `links` sorted and strictly increasing by `stage`.
   - **Containment:** `contains` lists ordered children as full `id-version`
     refs; `section` opens directories and `name` sets the file stem.
4. `links` holds typed edges with full refs in both topologies; prose citations
   are separate.
5. `--path-template` and presentation fields apply to a containment store; a
   graph store uses its derived band plan (path layers with inference, or
   absolute stages).

`examples/` is the default worked project: a graph store under
`examples/.bd_tree/` with one file per node version, declared `links`, a
relative `layer` path per node, no `stage`, no `group`, and no `contains`. For a
live containment tree with ordered `contains` and root-relative `section` keys,
use the product breakdown store: `bd --root docs/breakdown check` and
`bd --root docs/breakdown tree 1-1 --depth 1`.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `bd: unknown ref '1-1'` | No store found, or the ref is absent from the selected view. Run from the project root or store root, or set `BD_ROOT` to the directory containing `nodes/` (or `.bd_tree/nodes/`). |
| `bd check` sees the wrong store | `BD_ROOT` or `--root` points elsewhere. `bd` uses the nearest `nodes/` or `.bd_tree/nodes/` upward. |
| `root-ref-missing` / `invalid-root` | The `ROOT` file names an absent ref or is malformed. Fix it, or run `bd root --clear`. |
| `bare-ref` / `invalid-ref` in data | `contains`, `links`, and `ROOT` need full `id-version` refs. Convert a classic bare-file store once with `bd migrate`. |
| `duplicate-id` | A containment view holds two versions of the same logical id. `bd uncontain` the unwanted one. |
| `graph-layer-missing` / `graph-layer-invalid` | Relative mode: a graph node lacks a valid `layer` path. Add or fix it; later segments are explicit subfolders. |
| `graph-layer-cycle` / `graph-order-back-edge` | Relative mode: cross-band edges loop, or a same-band edge is not forward by `order` (including across subpaths). Repoint the edge or adjust `order`. |
| `graph-stage-missing` / `graph-back-edge` | Absolute mode: a graph node lacks an integer `stage`, or an edge does not move forward. Fix the field or repoint the edge. |
| `graph-group-ignored` | Warning: `group` places nothing. Replace it with `layer: band/sub`. |
| `graph-orphan` | A non-anchor root has no incoming link. Make it the anchor or link it into the graph. |
| `bd contain` says graph stores use edges | The store is a graph. Use `bd link` / `bd unlink`. |
| `bd work` refuses to switch | `bd_work/` has detached or stray files. Run `--status`, then `--writeback` to keep them or `--clean` to discard them. |
| `bd current` errors | No work area exists. Build one with `bd work [REF]`. |
| `bd edit REF` errors | The ref is not in the active view. Switch with `bd work REF` or use a ref that is present. |
| Edit did not reach the node | The editor replaced the symlink. Run `--status`, then `--writeback`. |
| Want two work folders | Not supported. `bd_work/` is the single area; switch with `bd work REF`. |
| `bd_work/` appears in git status | `bd init` adds it to `.gitignore`; add `bd_work/` if the project predates that. |
| Work folder points at missing files | The branch changed under the layout. Rebuild with `bd work REF --clean`. |
| Size warning on a node | Cosmetic by default. Split the node, or pass `--max-lines` / `--max-chars`. |

## Next

- Command reference: [`CHEATSHEET.md`](CHEATSHEET.md)
- Graph topology: [`GRAPH.md`](GRAPH.md)
- Graph layout algorithm: [`GRAPH-LAYOUT.md`](GRAPH-LAYOUT.md)
- Model and decisions: [`DESIGN.md`](DESIGN.md)
- Change the tool: [`DEVELOPING.md`](DEVELOPING.md)
- Agent rules: [`../AGENTS.md`](../AGENTS.md)
