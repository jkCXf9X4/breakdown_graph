# Example project

This folder is a complete `bd` project and the default store (`.bd_tree/`,
`ROOT` `1-1`). The store has twelve nodes and no `contains`: `links` is the one
edge relation. Every node declares its outgoing edges as full refs in `links`,
and in-edges are derived by reversing them. There is no placement key: the view
is the weakly connected component of the anchor, and ordering is the undirected
BFS hop count from that anchor.

The store is one component. From `1-1` the rings are:

| Ring | Members |
| --- | --- |
| 0 | `1-1` |
| 1 | `2-1`, `3-1` |
| 2 | `4-1`, `5-1`, `6-1`, `7-1` |
| 3 | `8-1`, `12-1` |
| 4 | `9-1`, `10-1`, `11-1` |

`4-1` has two parents (`2-1` and `3-1`) and still appears once, in ring 2.
`8-1` has several inbound edges and still appears once, in ring 3. `12-1`
reaches `11-1` one hop later, which is why `11-1` is ring 4 while `12-1` is ring
3. Direction is a label: ring 1 is split into children, parents, and peers, but
membership is the whole component.

```sh
bd audit                                  # 0 errors, 0 warnings
bd graph                                  # ring sections from 1-1
bd graph 1-1 --depth 1                    # rings 0 and 1
bd graph 1-1 --distance 2:3               # ring 0 plus rings 2 and 3
bd graph --svg --out /tmp/bd-graph.svg    # rendered SVG (needs Graphviz)
bd out 1-1                                # authored out-edges, sorted
bd in 4-1                                 # derived in-edges for a two-parent node
bd path 10-1                              # shortest undirected chain from 1-1
bd views                                  # one line per component
bd work 1-1                               # single flat work area
bd edit 4-1                               # path of 4-1 in the active view
bd export graph --view 1-1 --out /tmp/bd-graph
```

`bd work 1-1` writes `examples/bd_work/` as a flat directory: one symlink per
node at its store basename (`1-1.md`, `2-1.md`, …), plus generated `INDEX.md`,
`REFS.md`, and `AGENTS.md`. `INDEX.md` has `## Active`, `## Distance 1 — children`, then `## Distance 2`
through `## Distance 4`. `REFS.md` is the
path/ref/kind/distance/title table and its header names the active view.

The `/tmp/bd-graph` export holds the same twelve node files plus one root
`INDEX.md` with the same ring sections. It is a read-only snapshot, never a work
area. `bd_work/` is ignored by `examples/.gitignore`.

The commands assume the package is installed (`pip install -e '.[test]'` from
the clone). From the repository root, `bd` finds this store through the committed
`.bd_root` pointer.
