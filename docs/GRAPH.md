# Graph topology

A graph store is one of the two topologies `bd` supports. It reads the same flat
store as a containment store but never consults `contains`: the child relation
is declared `links`, so one node can have any number of parents without changing
the containment model. The default example at `examples/` is a graph.

Containment remains fully supported. A store is a **containment store** when any
node declares a `contains` key. Otherwise it is a **graph store** when at least
one node declares `links`, `stage`, or a non-empty `layer`/`band`; an empty or
legacy store with none of those keys is containment. Detection is per store, never per
node. `docs/breakdown/` is the live containment example.

## Model

An edge is declared on its parent node as `parent -> child` in `links`:

```yaml
links:
  - to: 4-1
    type: breaks_down
```

`links` is already parsed by the loader, and data refs are full
`<id>-<version>` refs. A graph store ignores `contains` completely.

Bands have two modes, selected per store.

**Relative mode (the default example).** When no node declares `stage`, bands
come from each node's non-empty `band` (or the older `layer: band/subpath`
shorthand). An optional `subpath` names an explicit folder below the band
folder. A link that crosses bands adds a band edge, and a topological sort with
a deterministic lexicographic tie-break orders the bands. The shortest-path
rule then decides which bands are top-level and which nest under an inferred
parent folder; equal-length branches stay top-level. This nesting is a
projection convention, not a proof about the graph. Unconnected bands sort
after connected ones. `order` (default `0`) positions nodes inside a band. A
missing or empty `band` is `graph-layer-missing` / `graph-layer-invalid`; an
invalid band, subpath, or `layer` path is also `graph-layer-invalid`; a band
cycle is `graph-layer-cycle`; a same-band edge must satisfy
`order(source) < order(target)`, else `graph-order-back-edge`. The full
algorithm, tie-breaks, and worked examples are in
[`GRAPH-LAYOUT.md`](GRAPH-LAYOUT.md).

**Absolute mode (older stores).** When any node declares `stage`, the bands are
the integer stages. Edges must be strictly forward:
`stage(source) < stage(target)`. Missing or non-integer stages are
`graph-stage-missing` / `graph-stage-invalid`; a non-forward edge is
`graph-back-edge`. `order` (default `0`) is the within-stage tie-break.

Both modes keep `links` sorted by ref so a merge stays local to the edge that
changed, and both report a non-integer `order` as `graph-order-invalid`. In
relative mode the band ordinal is derived; no node is renumbered when a band is
inserted.

`group` is ordinary metadata in a graph store. It changes no band, no folder, no
edge, and no validation. Audit warns `graph-group-ignored` and suggests
`band` plus `subpath` instead. A containment store ignores `group` for
placement too. Use `band` and `subpath` for graph subfolders.

The authored data is the **out-edge list** on each node. **In-edges are always
derived** by reversing those declarations. Audit and rendering label them
`derived`; nothing infers an edge that is not written in a node file.

A node reached through several parents appears once in a view. A graph store has no
`multiple-parents`, per-view `duplicate-id`, or `external-link` errors. A view
warns when two versions of one id are reachable (`graph-duplicate-version`).

A bare id on the command line selects the highest existing version. A full ref
is used verbatim.

## Dispatch

Commands dispatch on `Store.model`:

| Command | Graph store | Containment store |
| --- | --- | --- |
| `bd check` | graph audit plus freshness and size | containment checks |
| `bd audit` | explicit graph audit | not applicable; use `bd check` |
| `bd tree` | band or stage bands | containment outline |
| `bd show REF+N` | N link hops | N containment levels |
| `bd path` | reverse chain, first parent when ambiguous | containment chain |
| `bd find` | view search | view search |
| `bd views` | graph roots | containment roots |
| `bd diff`, `bd stale` | closures and edges | closures and edges |
| `bd work` / `current` / `edit` | band layout | containment layout |
| `bd export tree` | band layout | containment layout |
| `bd export graph` | band snapshot | band snapshot of the graph |
| `bd new --parent` | adds a typed link (`--type` default `breaks_down`; `--band`/`--subpath` or `--layer` in relative mode, `--stage` in absolute mode; `--order`) | appends to `contains` |
| `bd link` | child edge; refuses a back-edge or a band cycle, keeps targets sorted | semantic edge |
| `bd replace` | repoints inbound links | replaces at the parent's index |
| `bd clone --subtree` | rewrites cloned `links` | rewrites cloned `contains` |
| `bd delete` | removes a version | removes a version |
| `bd contain` / `bd uncontain` | fail: "graph stores use edges: bd link / bd unlink" | reorder the tree |

## View as a query

A graph view is the forward closure of one anchor over authored out-edges:

- the anchor is always included;
- a node reached through many parents is included once;
- `--type T` follows only links with that type (repeatable);
- `--stage A:B` keeps bands in the inclusive range (an absolute stage ordinal or
  a derived band ordinal); the anchor is always included;
- `--depth N` bounds traversal to `N` edge hops.

The default anchor is the store `ROOT` when present, else the lowest graph root
(a node with no incoming edge).

```sh
bd graph                    # text render from the default anchor
bd tree 1-1                 # same closure, band layout
bd graph 1-1 --depth 1      # direct children only
bd graph --stage 2:3        # bands 2 and 3, plus the anchor band
bd graph --type supports    # follow one edge kind
bd graph --dot              # Graphviz DOT
bd graph --svg --out graph.svg  # rendered SVG (needs Graphviz)
bd show 4-1+1               # the node plus one link hop
```

`bd graph --svg` pipes the clustered DOT through Graphviz `dot`, so it needs
the `dot` binary on `PATH`; `bd graph --dot` is the dependency-free fallback.
Both accept `--out PATH`; without it they print to stdout.

## Layout

Text rendering, the work area, and export group refs by band (a derived relative
band or an absolute stage), then sort inside an effective folder by
`(order, id, version)`. In relative mode the band label is the band name itself,
so the text header is `layer N — <name>`; an inferred nested band and an
explicit subpath each print as a folder heading. In absolute mode the label is
the most common non-empty `band`/`layer` label in that stage, slugified, with a
lexicographic tie-break; without one it falls back to `stage-NN`, so the
header is `stage N — <label>`. The directory name is `<NN>-<slug(band)>`, with
the band number zero-based and padded to at least two digits.

In relative mode `<NN>` is the derived top-level ordinal. Inserting a band
before others renumbers the later top-level folder paths; no node data changes,
so the churn is output only. A nested band adds its inferred folder below the
parent band folder, and an explicit `subpath` is appended verbatim, so a
node with `band: claims` and `subpath: structural` is
`02-claims/structural/<ref>-<slug>.md`. An explicit subpath never forces its
band to nest: the band's inferred folder (or top-level folder) is the base, and
the subpath is appended to it. `group` adds nothing in any mode.

`bd work` and `bd export tree` materialize this band layout, including inferred
nested folders, explicit subpaths, and an `INDEX.md` in each; `bd export graph`
is the same projection with per-folder indexes. A work area still holds one view
at a time and never becomes a second source of truth.

## Authored out-edges, derived in-edges

```sh
bd out 1-1      # the declared links of 1-1, sorted, no inference
bd in 4-1       # computed parents of 4-1, every line marked derived
```

`bd graph` prints, for each node, `← in:` (derived) and `→ out:` (authored).

## Audit

`bd check` dispatches to the graph audit for a graph store; `bd audit [REF]` is
the explicit form. Both exit non-zero when any error is present. The default
anchor is the same as `bd graph`. `bd audit` is graph-only: against a containment
store it exits 2 with "this store is containment; graph commands need links and
stages", so use `bd check` there.

Relative mode reports `graph-layer-missing`, `graph-layer-invalid`,
`graph-layer-cycle`, and `graph-order-back-edge`. Absolute mode reports
`graph-stage-missing`, `graph-stage-invalid`, and `graph-back-edge`. The
remaining codes are shared.

| Code | Level | Meaning |
| --- | --- | --- |
| `graph-layer-missing` | error | the node has no `band` (or `layer`) in relative mode |
| `graph-layer-invalid` | error | `band`, `subpath`, or `layer` is invalid, missing its `band`, or mixed with the other form (relative mode) |
| `graph-layer-cycle` | error | cross-band edges form a cycle; the bands are reported |
| `graph-order-back-edge` | error | a same-band edge has `order(source) >= order(target)`, including across subpaths |
| `graph-stage-missing` | error | the node has no `stage` (absolute mode) |
| `graph-stage-invalid` | error | `stage` is not an integer (booleans are rejected) |
| `graph-back-edge` | error | `stage(source) >= stage(target)` (absolute mode) |
| `graph-order-invalid` | error | `order` is not an integer |
| `graph-group-ignored` | warning | a graph node declares `group`, which never places a node |
| `graph-dangling-link` | error | a link target does not exist |
| `graph-cycle` | error | DFS finds a cycle; the path is reported |
| `graph-orphan` | warning | a non-anchor node has no incoming edge |
| `graph-wide-fanout` | warning | out-degree above 200; split into an intermediate header |
| `graph-duplicate-version` | warning | one id has several versions reachable from the anchor |
| `graph-unsorted-links` | warning | a node's link targets are not sorted by ref |

Invalid relative data still renders: nodes with a missing or invalid band
share one trailing `unlayered` band. That is a rendering fallback, not an
ordering claim, and the audit still reports the error. A band cycle also
renders with a fallback order after the audit reports `graph-layer-cycle`.

## Export

`bd export graph` writes a read-only snapshot of one graph view:

- node files as regular files at `<NN>-<slug(band)>[/<subpath>]/<ref>-<slug>.md`
  (a node `name` is used for the stem when present; inferred nested bands and
  explicit subpaths add directories, `group` does not);
- one `INDEX.md` per band, per inferred or explicit folder: a directory lists
  its direct nodes with authored `→` out-links and derived `←` in-links, then
  links to its immediate subfolder indexes;
- a root `INDEX.md` listing each top-level band with its node count and a link
  to its index.

`bd work` and `bd export tree` write the same root index for a graph store: one
entry per top-level band, never a link pre-order. Declaring `band_layout: flat`
on the store's `ROOT` node keeps every band top-level (see
[`GRAPH-LAYOUT.md`](GRAPH-LAYOUT.md)).

The output is deterministic and byte-identical across runs. `--force` writes
into a non-empty directory; `--clean` removes the output first.

```sh
bd export graph --view 1-1 --out /tmp/bd-graph
bd export tree 1-1 --out /tmp/bd-tree
```

Three visual paths cover the same store: `bd graph --svg` draws the clustered
band view (relative bands or absolute stage bands); the
`bd export dot --render svg` pair writes the flat DOT graph and renders it (same
DOT text fed to the file and to Graphviz); and `bd export svg` renders that flat
graph without keeping the `.dot` source.

## Scale notes

- Keep every node's `links` sorted by ref. Sorted lists keep a merge local to
  the edge that changed.
- When one node fans out too widely, insert an intermediate header instead of
  adding hundreds of direct edges. Audit warns above 200 out-links.
- Sorting is numeric by `(id, version)`, matching the rest of the store.
- Reachability is a query, not stored placement: adding a parent adds no file
  and no containment edge. In-edges are derived, so no parent array is rewritten.

## Example store

`examples/` is the default graph store, with no `contains`, no `section`, and no
`stage` key: it is a relative-band graph. It proves a claim with two parents,
sorted links, bands with optional `subpath`s (`intent`, `breakdown`, `claims`,
`verification`, `operation`), and no `group` key. Node `12-1` sits at
the band root as the verification core and fans out to the check subfolders.
Every band is on the one shortest root-to-sink path, so all stay top-level and
the folders are `00-intent` through `04-operation`; the subpaths add
`02-claims/structural`, `02-claims/verification`,
`03-verification/fan-in`, and `03-verification/fan-in2`.

```sh
bd check
bd tree 1-1
bd graph
bd graph --svg --out /tmp/bd-graph.svg
bd out 1-1
bd in 4-1
bd audit
bd work 1-1
bd edit 4-1
bd export tree 1-1 --out /tmp/bd-tree
bd export graph --view 1-1 --out /tmp/bd-graph
```

The repository `.bd_root` pointer names `examples`, so plain `bd` finds it from
the repo root. An explicit root works too:

```sh
bd --root examples graph
```
