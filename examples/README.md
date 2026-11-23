# Example project

This folder is a complete `bd` project and the default store (`.bd_tree/`,
`ROOT` `1-1`). The store has ten nodes and no `contains`: it is a graph example,
not a containment tree. Every node declares its outgoing edges as full refs in
`links`, and every node carries a `layer` path; no node declares `stage`, so the
store is in relative mode and the band order is derived from the cross-band
edges. Here the layers are `intent`, `breakdown`, `claims/structural`,
`claims/verification`, `verification/fan-in`, and `operation`, so the links
order the bands `intent` → `breakdown` → `claims` → `verification` →
`operation`. The segments after the band are explicit subfolders. Out-edges are
authored on the parent, while in-edges are derived by reversing them, so a node
such as `4-1` can have two parents and still appear once. See
[`docs/GRAPH.md`](../docs/GRAPH.md) for the model and
[`docs/GRAPH-LAYOUT.md`](../docs/GRAPH-LAYOUT.md) for the layout algorithm.

Relative mode requires a non-empty `layer` path on every node; a missing or
invalid one is `graph-layer-missing` / `graph-layer-invalid`. The `<NN>` folder
prefix is the derived top-level band position, so inserting a band before others
renumbers the later folder paths without renumbering any node.

The example has no `group` key. Subfolders come from the layer path itself:
`4-1` has `layer: claims/structural` and lands in `02-claims/structural/`; `7-1`
has `claims/verification`; `8-1` has `verification/fan-in`. A node labels
itself, so nothing is inherited; `4-1` has two parents and still lives only
under `02-claims/structural/`, which is the point of the example. `group` is
ordinary metadata and never places a node in any topology.

```sh
bd audit                                  # 0 errors, 0 warnings
bd tree                                   # derived band layout, subpath headings
bd graph                                  # text render from 1-1, labelled bands
bd graph --svg --out /tmp/bd-graph.svg    # rendered SVG (needs Graphviz)
bd out 1-1                                # authored out-edges, sorted
bd in 4-1                                 # derived in-edges for a two-parent node
bd work 1-1                               # single work area, derived band layout
bd edit 4-1                               # path of 4-1 in the active view
bd export tree 1-1 --out /tmp/bd-tree
bd export graph --view 1-1 --out /tmp/bd-graph
```

The `/tmp` output holds `00-intent/` through `04-operation/`, the subpath
folders `02-claims/structural/`, `02-claims/verification/`, and
`03-verification/fan-in/`, one `INDEX.md` per directory, and a root index; it is
a read-only snapshot, never a work area. `bd_work/` is ignored by
`examples/.gitignore`. `bd tree` labels each band `layer N — <name>`; the band
number is the derived ordinal, not data.

The commands assume the package is installed (`pip install -e '.[test]'` from
the clone). From the repository root, `bd` finds this store through the committed
`.bd_root` pointer.
