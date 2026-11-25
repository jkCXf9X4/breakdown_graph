# The graph

`bd` has one topology: a graph of markdown nodes joined by typed `links`. A node
declares edges, in-edges are derived, and a view is the weakly connected
component of one anchor over the authored links. Direction survives as a label,
not as a membership rule. The default example at `examples/` is a twelve-node
graph with `ROOT` `1-1` and rings 0 through 4.

A node that still declares `contains` is not a different topology: `bd check`
reports `contains-removed` and tells you to run `bd migrate` (§ Migration).

## Model

An edge is declared on one node as an out-link:

```yaml
links:
  - to: 4-1
    type: breaks_down
  - to: 12-1
    type: verifies
    symmetric: true
    inverse: verified_by
```

`links` is parsed by the loader, and data refs are full `<id>-<version>` refs.
`to` is required and must be a full ref; `type` is a required non-empty
arbitrary label. Optional `propagates` and `pinned` are preserved, as are extra
edge keys.

The authored data is the **out-edge list** on each node. **In-edges are always
derived** by reversing those declarations. A symmetric master's opposite is
derived at load. Audit and rendering label both `derived`; nothing infers an
edge that is not written in a node file.

A link is **structural** unless it declares `symmetric: true`. Structural links
keep the authored parent -> child direction and supply the labels for `bd out`,
`bd in`, and the `← in` / `→ out` rows of `bd graph`. `bd clone --subtree`
follows the undirected component.

A **symmetric** link is the single authored master of a two-way relation:
exactly one node file writes `X --T--> Y`. Load derives the opposite
`Y --(inverse or T)--> X` without storing it. It is never a second authored
edge, and `bd out` marks the derived side `[derived]`. Optional `inverse` names
the opposite's type and requires `symmetric: true`. `propagates` is invalid on a
symmetric link.

A node reached through several neighbours appears once in a view. Multiple
parents, reciprocal pairs, back-edges, and cycles are legal; a self-loop on one
ref is refused by `bd link`.

A bare id used as a graph anchor resolves to the highest existing version of
that id; commands that resolve a selector inside a view use the version present
there. A full ref is used verbatim.

## View as an undirected component

A view is the weakly connected component of one anchor over authored `links`,
walked in both directions:

- the anchor is always included, at distance 0;
- a node reached through many routes is included once, at its minimum distance;
- `--type T` follows only links with that type (repeatable);
- `--depth N` bounds traversal to `N` link hops;
- `--distance A:B` keeps only nodes whose ring is in the inclusive range; the
  filter is display-only, so traversal continues through hidden nodes and the
  anchor is always included.

Direction is a label on each neighbour: `child` (an authored out-link),
`parent` (another node's out-link targets this one), or `peer` (a symmetric
master in either direction). It orders ring 1 into children, parents, and peers.
Deeper rings are not split.

The default anchor is the store `ROOT` when present, else the lowest member of
the first component. A component always has a representative, even when it
contains a cycle.

```sh
bd graph                    # text render from the default anchor
bd graph 1-1                # the same component, anchored at 1-1
bd graph 1-1 --depth 1      # rings 0 and 1
bd graph 1-1 --distance 2:3 # ring 0 plus rings 2 and 3
bd graph --type supports    # follow one edge kind
bd graph --dot              # Graphviz DOT
bd graph --svg --out graph.svg  # rendered SVG (needs Graphviz)
bd show 4-1+1               # the node plus one link hop
bd views                    # one representative per component
```

`bd graph --svg` pipes the flat DOT through Graphviz `dot`, so it needs the
`dot` binary on `PATH`; `bd graph --dot` is the dependency-free fallback. Both
accept `--out PATH`; without it they print to stdout. `bd graph` is the only
view renderer; there is no separate `bd tree` command.

## Ring layout

Text rendering, the work area, and export order refs by distance from the
anchor. Ring 0 is the anchor. Ring 1 is split into `children`, `parents`, and
`peers`, each sorted by `(link type, id, version)`. Rings 2 and deeper are
numbered sections sorted by `(id, version)`. The canonical global key is
`(distance, kind_rank, link type, id, version)`, where `kind_rank` is
`child: 0`, `parent: 1`, `peer: 2`.

`bd work` materializes this as a **flat** directory: one symlink per
materialized ref, named after the store file, plus a root `INDEX.md` with ring
sections and a `REFS.md` table sorted by `(distance, kind, ref)`. There are no
node directories. `REF+N` materializes rings `0..N`; the view stays the full
component. `bd export graph` writes the same flat view as regular files with one
ring-section `INDEX.md`.

The active node of the work area is the view ref in the `REFS.md` header
(`# References — view REF[+N]`). `bd current`, `bd edit`, `--status`, and
`--writeback` read it; there is no separate state file.

## Authored out-edges, derived in-edges

```sh
bd out 1-1      # the declared links of 1-1, sorted, no inference
bd in 4-1       # computed parents of 4-1, every line marked derived
```

`bd graph` prints, for each node, `← in:` (derived) and `→ out:` (authored).
`bd show --links` prints one undirected neighbour row per edge with an arrow:
`→` child, `←` parent, `↔` peer.

## Audit

`bd check` runs structural validation and the graph checks; `bd audit [REF]` is
the explicit graph form. Both exit non-zero when any error is present. The
default anchor is the same as `bd graph`.

Cycles, back-edges, and reciprocal edges are never errors.
`graph-orphan` now means a node outside the anchor's component, not a node
without an incoming edge.

| Code | Level | Meaning |
| --- | --- | --- |
| `contains-removed` | error | a node still declares `contains`; run `bd migrate` |
| `bare-ref` | error | a data ref is a bare id; use a full `<id>-<version>` ref |
| `invalid-ref` | error | a data ref or CLI selector is malformed |
| `invalid-link` | error | a link is missing `to` or `type`, or is not a mapping |
| `invalid-links` | error | `links` is not a list |
| `invalid-propagates` | error | `propagates` is not a boolean |
| `invalid-symmetric` | error | `symmetric` is not a boolean |
| `inverse-without-symmetric` | error | `inverse` is empty, or present without `symmetric: true` |
| `invalid-pin` | error | `pinned` is not a string |
| `symmetric-self-edge` | error | a symmetric link's `to` equals its source |
| `duplicate-symmetric-edge` | error | both directions are authored symmetric; keep one master |
| `propagates-on-symmetric` | error | a symmetric link declares `propagates` |
| `graph-dangling-link` | error | a link target does not exist |
| `root-ref-missing` | error | the declared `ROOT` ref does not exist |
| `invalid-root` | error | the `ROOT` file is empty, malformed, or holds a bare id |
| `graph-orphan` | warning | a node is not in the default component |
| `graph-wide-fanout` | warning | out-degree above 200; split into an intermediate header |
| `graph-duplicate-version` | warning | one id has several versions reachable from the anchor |
| `graph-unsorted-links` | warning | a node's link targets are not sorted by ref |
| `untracked-link` | warning | a propagating edge has no pinned hash |
| `stale-link` | warning | a propagating edge's pin no longer matches the target body |
| `oversize` | warning | a node body exceeds the size limits |
| `missing-field` | error | a field named by `--require` is absent or empty |
| `duplicate-version` | error | two files claim one ref |
| `invalid-filename` | error | a filename is not `<id>-<version>.md` |
| `invalid-id` | error | front-matter `id` is not an integer |
| `id-filename-mismatch` | error | front-matter `id` differs from the filename |
| `bad-frontmatter` | error | the document cannot be parsed |
| `missing-nodes-dir` | error | neither `nodes/` nor `.bd_tree/nodes/` exists |
| `view-root-missing` | error | the requested view ref does not exist |

## Export

`bd export graph` writes a read-only snapshot of one view:

- node files as regular files at their flat basename, using the store file's
  name;
- one root `INDEX.md` with ring sections and links to each real node file;
- no node directories and no per-folder indexes.

`bd work` writes the same flat structure with symlinks instead of copies. The
output is deterministic and byte-identical across runs. `--force` writes into a
non-empty directory; `--clean` removes the output first.

```sh
bd export graph --view 1-1 --out /tmp/bd-graph
```

Three visual paths cover the same store: `bd graph --svg` draws the ring view;
the `bd export dot --render svg` pair writes the flat DOT graph and renders it
(the same DOT text fed to the file and to Graphviz); and `bd export svg` renders
that flat graph without keeping the `.dot` source.

## Migration

An older store is converted by `bd migrate`:

1. Classic bare `nodes/<id>.md` files become `<id>-<version>.md`.
2. `contains: [c0, c1, ...]` becomes `links` with one typed edge per child, and
   the key is removed. The edge type comes from `--type` (default
   `breaks_down`).
3. Scalar `links` entries gain an explicit type, and every link list is sorted
   by ref.
4. Retired placement keys are stripped from every node (`band`, `subpath`,
   `layer`, `stage`, `order`) and from the ROOT node (`band_layout`,
   `band_order`).

`bd migrate --dry-run` prints the plan without writing; `bd migrate` applies it
atomically; `--root` selects the store. After migration `bd check` passes.

The same command upgrades an already-migrated store, idempotently.
`--symmetric TYPE` (repeatable) marks every link of that type as a master and
drops any `propagates`/`pinned`; `--inverse TYPE=TYPE2` (repeatable) marks it
and names the derived opposite's type. There is no placement flag: placement is
derived from distance.

```sh
bd migrate --root docs/breakdown \
  --symmetric verifies --inverse verifies=verified_by
```

## Scale notes

- Keep every node's `links` sorted by ref. Sorted lists keep a merge local to
  the edge that changed.
- When one node fans out too widely, insert an intermediate header instead of
  adding hundreds of direct edges. Audit warns above 200 out-links.
- Sorting is numeric by `(id, version)`, matching the rest of the store.
- Reachability is a query, not stored placement: adding a parent adds no file
  and no positional field. In-edges are derived, so no parent array is rewritten.

## Example store

`examples/` is the default store: twelve nodes, one component, no `contains`,
and no placement key. Every node declares its outgoing edges as full refs in
`links`. From `1-1` the rings are:

| Ring | Members |
| --- | --- |
| 0 | `1-1` |
| 1 | `2-1`, `3-1` |
| 2 | `4-1`, `5-1`, `6-1`, `7-1` |
| 3 | `8-1`, `12-1` |
| 4 | `9-1`, `10-1`, `11-1` |

The store proves a claim with two parents (`4-1`), sorted links, a five-parent
fan-in (`8-1`), and a verification core (`12-1`) that reaches `11-1` one ring
later. `4-1` and `8-1` each appear once despite their multiple neighbours.

```sh
bd check
bd graph                    # ring sections from 1-1
bd graph --svg --out /tmp/bd-graph.svg
bd out 1-1
bd in 4-1
bd path 10-1
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
