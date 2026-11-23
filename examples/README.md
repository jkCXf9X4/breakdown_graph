# Example project

This folder is a complete `bd` project and the default store (`.bd_tree/`,
`ROOT` `1-1`). The store has ten nodes and no `contains`: it is a graph example,
not a containment tree. Every node declares its outgoing edges as full refs in
`links`, and every node carries an integer `stage`; an edge must point from a
lower stage to a higher one. Out-edges are authored on the parent, while in-edges
are derived by reversing them, so a node such as `4-1` can have two parents and
still appear once. See [`docs/GRAPH.md`](../docs/GRAPH.md) for the model and
validation rules.

```sh
bd audit                                  # 0 errors, 0 warnings
bd graph                                  # staged text render from 1-1
bd out 1-1                                # authored out-edges, sorted
bd in 4-1                                 # derived in-edges for a two-parent node
bd export graph --view 1-1 --out /tmp/bd-graph
```

The `/tmp` output holds `00-intent/` through `04-operation/`, one `INDEX.md` per
stage, and a root index; it is a read-only snapshot, never a work area.
`bd_work/` is ignored by `examples/.gitignore`.

The commands assume the package is installed (`pip install -e '.[test]'` from
the clone). From the repository root, `bd` finds this store through the committed
`.bd_root` pointer.
