# Getting started

This guide goes from the default example to a browsable, editable store with a
work folder, typed links, and a second solution in a git worktree. `bd` has one
topology: markdown nodes joined by typed `links`. A link is structural by
default; one with `symmetric: true` is an authored master whose opposite is
derived at load.

You need Python 3.10+ and PyYAML. From a clone, install the package:

```sh
pip install .
bd --help
```

## 1. See the default store

The repository ships `examples/` as the default store (`ROOT` `1-1`). Every node
declares `links`. No node declares `stage`, so it is a **relative-band** graph:
each node names a `band` plus an optional `subpath`, and the band order and
nesting are derived from cross-band structural links.

```sh
export BD_ROOT=examples
bd check
```

```
12 nodes, 0 errors, 0 warnings (view 1-1)
```

The store layout:

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
band: intent
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
`id-version` refs; `band` names the rank and an optional `subpath` names a
folder below it (`layer: band/subpath` is the older shorthand). The edges order
the bands `intent` → `breakdown` → `claims` → `verification` → `operation`; a
`subpath` such as `structural` adds an explicit folder below its band. Structural
links define structure; a symmetric link (`symmetric: true`, optional `inverse`)
writes the relation once and the opposite is derived at load, never stored.

There is no second topology and no `contains` key. A node that still declares
`contains` fails `bd check` with `contains-removed`; `bd migrate` converts it
(§10).

## 2. Browse the graph

```sh
bd graph 1-1
bd graph --depth 1
bd show 2-1+1 --max-chars 400
bd find closure --limit 3
bd path 4-1
bd out 1-1
bd in 4-1
bd views
```

- `graph` renders the band layout from an anchor, with authored `→ out` edges
  and derived `← in` edges. `bd graph` is the only view renderer.
- `show REF+N` prints the node body plus N link hops.
- `find` searches titles, summaries, bodies, and front-matter fields.
- `path` prints the ancestor chain, choosing the first parent when a node has
  several. `4-1` has two parents; the chain is deterministic but one of several
  paths.
- `out` lists authored out-edges; `in` lists derived in-edges.
- `views` lists graph roots, marking the default with `*`.

A node reached through several parents appears once in a view. Multiple parents
are legal.

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

- every node has a non-empty `band` (or `layer` shorthand);
- `subpath` adds an explicit folder below that band;
- structural links that cross bands order those bands; a band cycle is
  `graph-layer-cycle`; a ROOT `band_order` list is only a tie-break hint;
- the shortest-path rule chooses which bands are top-level and nests detours
  under an inferred parent; equal-length branches stay top-level;
- within a band, a structural link needs `order(parent) < order(child)`, else
  `graph-order-back-edge`, including across different subpaths;
- a non-integer `order` is an error;
- links resolve, do not cycle, and are sorted by ref; symmetric links are
  skipped by the back-edge/cycle audit but still must resolve;
- a symmetric relation has one master per pair, never a self-edge, no
  `propagates`, and `inverse` only with `symmetric: true`
  (`invalid-symmetric`, `inverse-without-symmetric`, `symmetric-self-edge`,
  `duplicate-symmetric-edge`, `propagates-on-symmetric`);
- a non-list ROOT `band_order` is `invalid-band-order`;
- a non-anchor root warns (`graph-orphan`), and out-degree above 200 warns
  (`graph-wide-fanout`);
- a node declaring `contains` is `contains-removed`.

Nesting is a layout convention, not a semantic proof. The exact rule, tie-breaks,
and worked examples are in [`GRAPH-LAYOUT.md`](GRAPH-LAYOUT.md).

Absolute stage mode is the older alternative, not a requirement. If any node
declares `stage`, the bands are integer stages: every node needs an integer
`stage`, and every edge must satisfy `stage(parent) < stage(child)`. The modes
are selected per store; do not mix them. A new store uses `band`/`subpath`.

Structure is edited with links:

```sh
bd new --parent 1-1 --type breaks_down --band claims --subpath structural --order 0
bd link 2-1 8-1 --type supports
bd link 2-1 8-1 --type verifies --symmetric --inverse verified_by
bd unlink 2-1 8-1 --type supports
```

`bd new` allocates the next global id at version 1 and adds a typed link to the
parent; `--type` defaults to `breaks_down`. In relative mode `--band` is required
and `--subpath` is optional (`--layer BAND[/SUB]` is the older shorthand);
`--stage` is refused. In absolute mode use `--stage`; both take `--order`.
`bd link` refuses a back-edge or a band cycle and keeps each target list sorted
by ref. `--symmetric` instead authors the one master of a two-way relation and
skips those ordering checks; `--inverse TYPE` names the derived opposite's type.

## 4. Edit in the work area

`bd work` renders a view as a tree of symlinks in the project's single writable
work area, `<project>/bd_work/`. Editing a link edits the store.

```sh
bd work 1-1
bd current                 # <project>/bd_work (view 1-1)
work_dir=$(bd current --path)
ls "$work_dir"
```

The layout is the derived band plan, `<NN>-<slug(band)>`, plus any inferred
nested band folder and explicit `subpath`:

```
00-intent/1-1-verify-the-staged-graph.md
02-claims/structural/4-1-two-parents-one-node.md
INDEX.md  AGENTS.md  REFS.md
```

Inserting a band before others renumbers the later top-level directory prefixes
on the next build; no node is renumbered. A detour band can nest under a parent
band instead of getting its own prefix. In absolute mode the label is the
dominant band/layer label in that stage, and `<NN>` is the stage.
`band_layout: flat` on the ROOT keeps every band top-level, and a ROOT
`band_order: [band, ...]` orders those free bands without overriding an edge
constraint.

Only the node `.md` files are symlinks; `INDEX.md`, `AGENTS.md`, and `REFS.md`
are regular generated files. Each `INDEX.md` carries a `nodes:` front-matter
path to the store's real node folder, each node entry links straight to its
real file (`— [real file](…)`), and a `[nodes/](…)` link opens the folder to
copy or delete. `bd edit REF`
prints the ref's absolute path inside the active view and errors if the ref is
not there. `bd current` is read-only; `--path` prints only the path and `--view`
only the ref, and it errors if no area exists.

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
alone and `--depth` overrides a suffix. A level is a link hop. The view itself
is still the full closure of one ref, not a smaller view. The generated headers
carry `REF+N`, so `bd current --view` reports it and `bd edit` only resolves
refs that are materialized. A rebuild with a different depth, or a plain
`bd work REF`, replaces the area.

```sh
bd work 1-1+1      # root plus one link hop
bd current --view  # 1-1+1
bd work 1-1        # restore the full closure
```

Read-only snapshots (`bd export graph`, `bd export context`, `bd export dot`)
are separate disposable exports, not a second work area. `bd work` and
`bd export graph` materialize the same band layout; the export writes regular
files and per-folder indexes.

## 5. Create a store

```sh
mkdir -p ~/stores/my-graph
cd ~/stores/my-graph
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
band: root
---
# Root
```

`bd init` always writes a relative-band graph root; there is no `--graph` flag
because graph is the only topology. Add nodes and check:

```sh
bd new --parent 1-1 --type breaks_down --band intent  --field title="Why does this exist?"
bd new --parent 1-1 --type breaks_down --band claims  --field title="What is true?"
bd check
```

```
3 nodes, 0 errors, 0 warnings (view 1-1)
```

`bd graph 1-1` renders the band layout. `bd new` adds the typed link to the
parent's `links` and requires `--band` in relative mode.

Bands are the only layout. A node's folder comes from its `band` and optional
`subpath`; its file stem from an explicit `name`, else `<ref>-<title-slug>.md`,
else `<ref>.md` when there is no usable title. `section` and `group` are inert
front matter: they place nothing.

To move a node between bands, edit its `band`/`subpath` (through `bd edit REF`)
or repoint the edges that determine band order. There is no separate move
command: position is data on the node, not an ordered child list.

## 6. Typed links and freshness

`links` carries typed edges. Add a propagating edge and track freshness:

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
work area.

```sh
bd root 1-1                 # write ROOT; commands default here
bd root                     # 1-1  (ROOT)
bd work 1-1                 # switch the work area
bd current                  # <project>/bd_work (view 1-1)
bd root --clear             # back to the lowest graph root
```

`ROOT` is one full ref on one line at the store top level. An explicit ref where
a command takes one still wins over it; with no `ROOT`, the store uses its
lowest graph root. `bd check --view REF` only narrows reporting, not the checked
root. `bd root` changes the default root used by commands but does not rewrite
the view already in `<project>/bd_work/`; run `bd work REF` for that. `bd views`
lists graph roots and marks the default with `*`.

Versions are node-local alternatives inside one branch:

```sh
bd versions 1
bd clone 1-1 --version 2
bd replace 1-1 1-2
```

`bd clone REF` copies a ref to the next free version of the same logical id (or
to `--version N`) and keeps the source file's declared `links`; it wires
nothing into a view. `bd clone REF --subtree` clones every descendant in the
structural forward closure and rewrites each cloned parent's `links` so the copy is
self-contained; `--version` cannot be combined with `--subtree`. `bd replace OLD
NEW` is the separate wiring step: it repoints every inbound link, or repoints
`ROOT` when OLD is the store root; OLD's file stays as a peer.

An edge pins a full ref, several parents are allowed, and a view warns
(`graph-duplicate-version`) when two versions of one id are reachable. Repoint
the edge whose peer you want to change.

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
cd ../my-graph
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
3. Pick one band mode:
   - **Relative (the default):** a non-empty `band` on every node with an
     optional `subpath` (`layer: band/subpath` is the older shorthand); `links`
     lists parent→child edges as full refs, sorted; the cross-band structural
     edges derive the band order and nesting. `bd init` writes a root with
     `band: root`.
   - **Absolute (older stores):** integer `stage` on every node; `links` sorted
     and strictly increasing by `stage`.
4. `links` holds typed edges with full refs; prose citations are separate.
5. The layout is the band plan; `--path-template` overrides naming.

An older store that used `contains` is converted in place:

```sh
bd migrate --dry-run     # print the plan
bd migrate               # contains -> links, order -> links order, section -> band
bd check                 # clean
```

`bd migrate` preserves child order by writing `order: i`, uses `--type`
(default `breaks_down`) for the converted edges, and turns a `section` folder
path on a node without `band` into `band` plus `subpath`. `section` may remain
as inert front matter. On an already-migrated store, `--symmetric TYPE` marks
every link of a type as a master, `--inverse TYPE=TYPE2` names its derived
opposite, and `--band-order` writes the ROOT `band_order` hint plus
`band_layout: flat`; all are idempotent.

`examples/` is the default worked project: a relative-band graph under
`examples/.bd_tree/` with one file per node version, declared `links`, a
relative `band` plus optional `subpath` per node, no `stage`, no `group`, and no
`contains`.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `bd: unknown ref '1-1'` | No store found, or the ref is absent from the selected view. Run from the project root or store root, or set `BD_ROOT` to the directory containing `nodes/` (or `.bd_tree/nodes/`). |
| `bd check` sees the wrong store | `BD_ROOT` or `--root` points elsewhere. `bd` uses the nearest `nodes/` or `.bd_tree/nodes/` upward. |
| `root-ref-missing` / `invalid-root` | The `ROOT` file names an absent ref or is malformed. Fix it, or run `bd root --clear`. |
| `contains-removed` | The store still declares `contains`. Run `bd migrate --dry-run`, then `bd migrate`. |
| `invalid-symmetric` / `inverse-without-symmetric` | `symmetric` must be a boolean and `inverse` a non-empty string only with `symmetric: true`. Fix the link, or rerun `bd migrate --symmetric TYPE [--inverse TYPE=TYPE2]`. |
| `symmetric-self-edge` / `duplicate-symmetric-edge` | Author one master per pair, never to itself and never in both directions; remove the extra link with `bd unlink`. |
| `propagates-on-symmetric` | Remove `propagates`/`pinned`; freshness is structural-only. |
| `invalid-band-order` | ROOT `band_order` must be a YAML list of band names. Fix it or remove the key. |
| `bare-ref` / `invalid-ref` in data | `links` and `ROOT` need full `id-version` refs. Convert a classic bare-file store once with `bd migrate`. |
| `graph-layer-missing` / `graph-layer-invalid` | Relative mode: a node lacks a valid `band`/`subpath` (or `layer` path). Add or fix it; `subpath` adds an explicit folder. |
| `graph-layer-cycle` / `graph-order-back-edge` | Relative mode: cross-band structural edges loop, or a same-band edge is not forward by `order` (including across subpaths). Repoint the edge or adjust `order`. |
| `graph-stage-missing` / `graph-back-edge` | Absolute mode: a node lacks an integer `stage`, or an edge does not move forward. Fix the field or repoint the edge. |
| `graph-group-ignored` | Warning: `group` places nothing. Replace it with `band` plus `subpath`. |
| `graph-orphan` | A non-anchor root has no incoming link. Make it the anchor or link it into the graph. |
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
- Band layout algorithm: [`GRAPH-LAYOUT.md`](GRAPH-LAYOUT.md)
- Model and decisions: [`DESIGN.md`](DESIGN.md)
- Change the tool: [`DEVELOPING.md`](DEVELOPING.md)
- Agent rules: [`../AGENTS.md`](../AGENTS.md)
