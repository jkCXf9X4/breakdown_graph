# Example project

This folder is a complete `bd` project and the default store (`.bd_tree/`,
`ROOT` `1-1`). The store has twelve nodes and no `contains`: `links` is the one
child relation. Every node declares its outgoing edges as full
refs in `links`, and every node carries a `band` plus an optional `subpath`;
no node declares `stage`, so the store is in relative mode and the band order
is derived from the cross-band edges. Here the bands are `intent`, `breakdown`,
`claims`, `verification`, and `operation`; the subpaths add `structural`,
`verification`, `fan-in`, and `fan-in2` below their bands, so the links order
the bands `intent` → `breakdown` → `claims` → `verification` → `operation`.
Out-edges are authored on the parent, while in-edges are derived by reversing
them, so a node such as `4-1` can have two parents and still appear once. See
[`docs/GRAPH.md`](../docs/GRAPH.md) for the model and
[`docs/GRAPH-LAYOUT.md`](../docs/GRAPH-LAYOUT.md) for the layout algorithm.

Relative mode requires a non-empty `band` on every node (`layer: band/subpath`
is the older shorthand); a missing or invalid one is `graph-layer-missing` /
`graph-layer-invalid`. The `<NN>` folder prefix is the derived top-level band
position, so inserting a band before others renumbers the later folder paths
without renumbering any node.

The example has no `group` key. Subfolders come from `subpath`:
`4-1` has `band: claims` plus `subpath: structural` and lands in
`02-claims/structural/`; `7-1` adds `subpath: verification`; `8-1` adds
`subpath: fan-in`; `11-1` adds `subpath: fan-in2`. `12-1` declares only
`band: verification` and sits in `03-verification/` itself as the core: the
claim sub-bands feed it and it fans out to the two check subfolders. A node
labels itself, so nothing is inherited; `4-1` has two parents and still lives only under
`02-claims/structural/`, which is the point of the example. Within the
verification band, `order` 0, 1, 2 positions the core, `fan-in`, and `fan-in2`
across their different folders. `group` and `section` are ordinary metadata and
never place a node.

```sh
bd audit                                  # 0 errors, 0 warnings
bd graph                                  # text render from 1-1, band headings
bd graph --svg --out /tmp/bd-graph.svg    # rendered SVG (needs Graphviz)
bd out 1-1                                # authored out-edges, sorted
bd in 4-1                                 # derived in-edges for a two-parent node
bd work 1-1                               # single work area, derived band layout
bd edit 4-1                               # path of 4-1 in the active view
bd export graph --view 1-1 --out /tmp/bd-graph
```

The `/tmp` output holds `00-intent/` through `04-operation/`, the subpath
folders `02-claims/structural/`, `02-claims/verification/`,
`03-verification/fan-in/`, and `03-verification/fan-in2/`, one `INDEX.md` per
directory, and a root index; it is a read-only snapshot, never a work area.
`bd_work/` is ignored by `examples/.gitignore`. `bd graph` labels each band
`layer N — <name>`; the band number is the derived ordinal, not data.

The commands assume the package is installed (`pip install -e '.[test]'` from
the clone). From the repository root, `bd` finds this store through the committed
`.bd_root` pointer.
