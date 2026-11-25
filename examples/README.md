# Example project

This folder is a complete `bdg` project and the default store (`bdg_graph/`,
`ROOT` `1-1`). The store has twelve nodes and no `contains`: typed body tokens
are the one edge relation. Each linked node writes its outgoing edges inline in
prose, for example `(Structural claims)[[2-1,breaks_down]]`; tooling writes the
same token as a `- (TITLE)[[REF,TYPE]]` line under `## Links` (no space after
the comma in the canonical form; a legacy single-space `[[REF, TYPE]]` is still
accepted). Authors write
the bare token; the cached title is tool-generated from the target's live title
and refreshed by `bdg retitle`, never hand-edited. In-edges are derived by
reversing authored tokens. There is no placement key: the view is the weakly
connected component of the anchor, and ordering is the undirected BFS hop count
from that anchor.

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
3. Direction is a label: ring 1 is split into children and parents, but
membership is the whole component.

```sh
bdg check                                  # 0 errors, 0 warnings
bdg stale                                  # 0 stale edges
bdg retitle --dry-run                      # would retitle 0 tokens in 0 nodes
bdg graph                                  # ring sections from 1-1
bdg graph 1-1 --depth 1                    # rings 0 and 1
bdg graph 1-1 --rings 2:3                  # ring 0 plus rings 2 and 3
bdg graph --format svg --out /tmp/bdg-graph.svg  # rendered SVG (needs Graphviz)
bdg out 1-1                                # authored out-edges, sorted
bdg in 4-1                                 # derived in-edges for a two-parent node
bdg path 10-1                              # shortest undirected chain from 1-1
bdg views                                  # one line per component
bdg work 1-1                               # single work area (ring folders)
bdg work 1-1 --flat                        # one symlink per node at store basename
bdg edit 4-1                               # path of 4-1 in the active view
bdg pack 1-1 --out /tmp/bdg-graph
```

`bdg work 1-1` writes `examples/bdg_work/` as ring folders by default: each
node is a symlink at `{distance}/{ref}_{title}.md` —
`0/1-1_Verify the undirected graph.md`, `1/2-1_Structural claims.md`,
`2/4-1_Two parents, one node.md`, and so on — plus generated `INDEX.md`,
`REFS.md`, and `AGENTS.md` at
the root and an `INDEX.md` in every ring folder. The layout is recorded in
`REFS.md` as `# Layout — {distance}/{ref}_{title}.md` and reused by a later plain
`bdg work`. A `--path-template` overrides the layout, and `--flat` restores one
symlink per node at its store basename (recorded as `# Layout — flat`, sticking
on later rebuilds). The root `INDEX.md` has `## Active`,
`## Distance 1 — children`, then `## Distance 2` through `## Distance 4`.
`REFS.md` is the path/ref/kind/distance/title table and its header names the
active view.

The `/tmp/bdg-graph` pack holds the same twelve node files plus one root
`INDEX.md` with the same ring sections. Its default layout stays flat basenames
— unlike `bdg work` — and it nests only with `--path-template`. It is a
disposable copy, never a work area. `bdg_work/` is ignored by
`examples/.gitignore`.

The commands assume the package is installed (`pip install -e '.[test]'` from
the clone). From the repository root, `bdg` finds this store through the committed
`.bdg_root` pointer.
