# The graph

`bd` has one topology: a graph of markdown nodes joined by typed `links`. A node
declares edges, and a view is the forward closure of one root over its
*structural* edges. Structural links define structure; symmetric links are
associative and derive an opposite. There is no second child relation. The
default example at `examples/` is a twelve-node relative-band graph.

A node that still declares `contains` is not a different topology: `bd check`
reports `contains-removed` and tells you to run `bd migrate` (§ Migration).

## Model

An edge is declared on its parent node as `parent -> child` in `links`:

```yaml
links:
  - to: 4-1
    type: breaks_down
  - to: 12-1
    type: verifies
    symmetric: true
    inverse: verified_by
```

`links` is already parsed by the loader, and data refs are full
`<id>-<version>` refs. `to` is required and must be a full ref; `type` is a
required non-empty arbitrary label. Optional `propagates` and `pinned` are
preserved, as are extra edge keys.

A link is **structural** unless it declares `symmetric: true`. Only structural
links expand a view, define `path` ancestry and `views` roots, feed band
inference and band order, take part in back-edge/cycle audit, and are followed
by `bd clone --subtree`.

A **symmetric** link is the single authored master of a two-way relation:
exactly one node file writes `X --T--> Y`. Load derives the opposite
`Y --(inverse or T)--> X` without storing it; it is never structural, and
`bd out`, `bd in`, and the `show --links` footer mark it `[derived]`. Optional
`inverse` names the opposite's type and requires `symmetric: true`.
`propagates` is invalid on a symmetric link.

Bands have two modes, selected per store.

**Relative mode (the default example).** When no node declares `stage`, bands
come from each node's non-empty `band` (or the older `layer: band/subpath`
shorthand). An optional `subpath` names an explicit folder below the band
folder. A structural link that crosses bands adds a band edge, and a topological
sort with a deterministic lexicographic tie-break orders the bands; a ROOT
`band_order` list replaces that tie-break, earlier index first, without
overriding a real edge constraint. The shortest-path rule then decides which
bands are top-level and which nest under an inferred parent folder; equal-length
branches stay top-level. This nesting is a
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

`group` is ordinary metadata. It changes no band, no folder, no edge, and no
validation. Audit warns `graph-group-ignored` and suggests `band` plus `subpath`
instead. `section` is also inert: it is ordinary front matter with no effect on
paths, layout, or validation. Bands are the only layout.

The authored data is the **out-edge list** on each node. **In-edges are always
derived** by reversing those declarations, and a symmetric master's opposite is
derived at load. Audit and rendering label both `derived`; nothing infers an
edge that is not written in a node file.

A node reached through several parents appears once in a view. Multiple parents
are legal. A view warns when two versions of one id are reachable
(`graph-duplicate-version`).

A bare id on the command line selects the highest existing version in the
selected view. A full ref is used verbatim.

## View as a query

A view is the forward closure of one anchor over authored structural out-edges:

- the anchor is always included;
- a node reached through many parents is included once;
- `--type T` follows only links with that type (repeatable);
- `--stage A:B` keeps bands in the inclusive range (an absolute stage ordinal or
  a derived band ordinal); the anchor is always included;
- `--depth N` bounds traversal to `N` edge hops.

The default anchor is the store `ROOT` when present, else the lowest graph root
(a node with no incoming structural edge).

```sh
bd graph                    # text render from the default anchor
bd graph 1-1                # same closure, band layout
bd graph 1-1 --depth 1      # direct children only
bd graph --stage 2:3        # bands 2 and 3, plus the anchor band
bd graph --type supports    # follow one edge kind
bd graph --dot              # Graphviz DOT
bd graph --svg --out graph.svg  # rendered SVG (needs Graphviz)
bd show 4-1+1               # the node plus one link hop
```

`bd graph --svg` pipes the clustered DOT through Graphviz `dot`, so it needs
the `dot` binary on `PATH`; `bd graph --dot` is the dependency-free fallback.
Both accept `--out PATH`; without it they print to stdout. `bd graph` is the only
view renderer; there is no separate `bd tree` command.

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
the subpath is appended to it. `group` and `section` add nothing.

`bd work` and `bd export graph` materialize this band layout, including inferred
nested folders, explicit subpaths, and an `INDEX.md` in each folder. A work area
still holds one view at a time and never becomes a second source of truth.

## Authored out-edges, derived in-edges

```sh
bd out 1-1      # the declared links of 1-1, sorted, no inference
bd in 4-1       # computed parents of 4-1, every line marked derived
```

`bd graph` prints, for each node, `← in:` (derived) and `→ out:` (authored).

## Audit

`bd check` runs structural validation and the graph checks; `bd audit [REF]` is
the explicit graph form. Both exit non-zero when any error is present. The
default anchor is the same as `bd graph`.

Relative mode reports `graph-layer-missing`, `graph-layer-invalid`,
`graph-layer-cycle`, and `graph-order-back-edge`. Absolute mode reports
`graph-stage-missing`, `graph-stage-invalid`, and `graph-back-edge`. The
remaining codes are shared. Symmetric edges are skipped by the back-edge and
cycle audit; they still need a resolvable `to` and a non-empty `type`.

| Code | Level | Meaning |
| --- | --- | --- |
| `contains-removed` | error | a node still declares `contains`; run `bd migrate` |
| `invalid-symmetric` | error | a link's `symmetric` value is not a boolean |
| `inverse-without-symmetric` | error | `inverse` is empty, or present on a link without `symmetric: true` |
| `symmetric-self-edge` | error | a symmetric link's `to` equals its source |
| `duplicate-symmetric-edge` | error | both directions are authored symmetric; keep one master |
| `propagates-on-symmetric` | error | a symmetric link declares `propagates` |
| `invalid-band-order` | error | the ROOT `band_order` is not a YAML list |
| `graph-layer-missing` | error | the node has no `band` (or `layer`) in relative mode |
| `graph-layer-invalid` | error | `band`, `subpath`, or `layer` is invalid, missing its `band`, or mixed with the other form (relative mode) |
| `graph-layer-cycle` | error | cross-band structural edges form a cycle; the bands are reported |
| `graph-order-back-edge` | error | a same-band edge has `order(source) >= order(target)`, including across subpaths |
| `graph-stage-missing` | error | the node has no `stage` (absolute mode) |
| `graph-stage-invalid` | error | `stage` is not an integer (booleans are rejected) |
| `graph-back-edge` | error | `stage(source) >= stage(target)` (absolute mode) |
| `graph-order-invalid` | error | `order` is not an integer |
| `graph-group-ignored` | warning | a node declares `group`, which never places a node |
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

`bd export graph` writes a read-only snapshot of one view:

- node files as regular files at `<NN>-<slug(band)>[/<subpath>]/<ref>-<slug>.md`
  (a node `name` is used for the stem when present; inferred nested bands and
  explicit subpaths add directories, `group` and `section` do not);
- one `INDEX.md` per band, per inferred or explicit folder: a directory lists
  its direct nodes with authored `→` out-links and derived `←` in-links, then
  links to its immediate subfolder indexes;
- a root `INDEX.md` listing each top-level band with its node count and a link
  to its index.

`bd work` writes the same structure with symlinks instead of copies. Declaring
`band_layout: flat` on the store's `ROOT` node keeps every band top-level, and
`band_order: [band, ...]` orders those free bands (see
[`GRAPH-LAYOUT.md`](GRAPH-LAYOUT.md)).

The output is deterministic and byte-identical across runs. `--force` writes
into a non-empty directory; `--clean` removes the output first.

```sh
bd export graph --view 1-1 --out /tmp/bd-graph
```

Three visual paths cover the same store: `bd graph --svg` draws the clustered
band view (relative bands or absolute stage bands); the
`bd export dot --render svg` pair writes the flat DOT graph and renders it (same
DOT text fed to the file and to Graphviz); and `bd export svg` renders that flat
graph without keeping the `.dot` source.

## Migration

An older store that used `contains` is converted by `bd migrate`:

1. `contains: [c0, c1, ...]` becomes `links` with one typed edge per child, in
   the same order; the edge type comes from `--type` (default `breaks_down`).
2. A converted child without an explicit `order` gets `order: i` for its list
   position.
3. A `section` path on a node with no `band` becomes `band` plus `subpath`;
   `section` itself stays as inert front matter.

`bd migrate --dry-run` prints the plan without writing; `bd migrate` applies it
atomically; `--root` selects the store. After migration `bd check` passes.

The same command upgrades an already-migrated store, idempotently. `--symmetric
TYPE` (repeatable) marks every link of that type as a master and drops any
`propagates`/`pinned`; `--inverse TYPE=TYPE2` (repeatable) marks it and names
the derived opposite's type; `--band-order` writes the ROOT `band_order` hint
and sets `band_layout: flat`.

```sh
bd migrate --root docs/breakdown \
  --symmetric verifies --inverse verifies=verified_by --band-order
```

## Scale notes

- Keep every node's `links` sorted by ref. Sorted lists keep a merge local to
  the edge that changed.
- When one node fans out too widely, insert an intermediate header instead of
  adding hundreds of direct edges. Audit warns above 200 out-links.
- Sorting is numeric by `(id, version)`, matching the rest of the store.
- Reachability is a query, not stored placement: adding a parent adds no file
  and no structural edge. In-edges are derived, so no parent array is rewritten.

## Example store

`examples/` is the default store, with no `contains`, no `section`, and no
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
bd graph                    # derived band layout
bd graph --svg --out /tmp/bd-graph.svg
bd out 1-1
bd in 4-1
bd audit
bd work 1-1
bd edit 4-1
bd export graph --view 1-1 --out /tmp/bd-graph
```

The repository `.bd_root` pointer names `examples`, so plain `bd` finds it from
the repo root. An explicit root works too:

```sh
bd --root examples graph
```
