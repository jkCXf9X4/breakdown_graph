# Graph views and ring layout

This document is the reference for how a graph store turns one anchor and its
authored tokens into a view, a ring ordering, and a flat work area. It covers
component membership, BFS rings, direction labels, the tie-break rules, the
generated `INDEX.md` and `REFS.md`, a worked example on the committed store,
cycles, and the limits of using distance as layout.

[`DESIGN.md`](DESIGN.md) owns the model and [`GRAPH.md`](GRAPH.md) owns the
topology and commands. This document owns one question: **given an anchor, which
nodes are in the view, and in what order do they appear?**

## 1. Data versus projection

The source of truth is the node files. For a view, only two pieces of authored
data matter:

- the anchor: an explicit ref, else the store `ROOT`, else the lowest member of
  the first component;
- link tokens in the body: typed edges with full target refs. Every token is
  authored on one node; nothing derives an opposite edge at load.

Nothing else is stored for layout. There is no placement field, ordinal,
position key, layout file, or cache. Components, distances, ring sections, and
the work area are recomputed from the store on every command, and the output is
disposable.

Direction survives in the data as parent -> child, but it does not decide
membership, order, or validation. It is a label on a neighbour and a traversal
rule for explicit directional commands.

## 2. Terms

| Term | Meaning |
| --- | --- |
| component | A weakly connected component of the store over authored links. |
| anchor | The ref a view is focused on; it is always ring 0. |
| distance | The undirected BFS hop count from the anchor. |
| ring | All view members with one distance value. |
| neighbour | One ref reachable over one authored edge in either direction. |
| kind | The direction of a neighbour from the queried ref: `child` or `parent`. |
| view | The whole component of the anchor, ordered by distance. |
| materialized depth | The largest ring written into the work area (`REF+N`). |

A node belongs to exactly one component and appears once in a view, at its
minimum distance.

## 3. Membership and the anchor

`Store.neighbors(ref)` returns every authored neighbour in both directions, one
entry per neighbour ref:

- `child`: the queried ref authors a token to the neighbour;
- `parent`: another node authors a token to the queried ref.

Kind precedence is `child > parent`. A reciprocal pair is a `child` from each
side. The representative link is always an authored token; there is no derived
opposite.

`Store.components()` walks those neighbours and returns every weak component.
Members are sorted by `(id, version)`, and components are sorted by their first
member. `Store.topology_roots()` returns one representative per component: its
lowest member by `(id, version)`. The name is historical; a cycle no longer
leaves a component without a representative.

The default anchor is the declared `ROOT` when present, else the first
component's representative. An explicit ref where a command takes one wins over
both. A declared but missing ref is an error (`root-ref-missing`); the view is
not silently re-anchored.

```sh
bd views                    # one line per component: representative, size, title
bd graph 2-1                # the same component, focused on 2-1
bd work 4-1                 # the same component, materialized around 4-1
```

`bd views` marks the store default with `*` and the active work-area anchor with
`anchor REF`.

## 4. Distance and rings

`ring_distances(store, anchor)` is an undirected breadth-first search over
`Store.neighbors`. It maps every reachable ref to its minimum hop count and
returns an empty map when the anchor is missing. Because a ref is enqueued at
most once, cycles need no special handling.

A view is the anchor's whole component, not a depth prefix. `bd work REF+N` and
`bd graph --depth N` materialize or traverse rings `0..N`; the view behind them
is still the full component.

Ring 0 is the anchor. Ring 1 is split by direction. Rings 2 and deeper are not
split: they are numbered sections, each sorted by `(id, version)`.

```text
## 0 — 1-1
## 1 — children
## 1 — parents
## 2
## 3
```

A node reached through several routes stays in its minimum ring. That is why a
cycle that closes back to the anchor can put a nominally distant node in ring 1.

## 5. Ordering and tie-breaks

Every emitted list is sorted by an explicit key. The canonical global key is:

```text
(distance, kind_rank, link type, id, version)
```

where `kind_rank` is `child: 0`, `parent: 1`. The parts apply as
follows:

- components: members by `(id, version)`, components by their first member;
- text rings: ring 1 within each kind by `(link type, id, version)`; deeper rings
  by `(id, version)`;
- `show`: rings by distance, then arrival kind rank, then link type, then
  `(id, version)`;
- `REFS.md`: rows by `(distance, kind_rank, id, version)`;
- `bd graph --dot`: nodes by `(distance, id, version)`.

No ordering depends on file order, filesystem order, or a YAML mapping order.

## 6. Direction labels

Direction is presentation and an explicit traversal choice; it is never a
membership filter.

| Label | Meaning |
| --- | --- |
| `→` | child: the current node authors the edge to the next node |
| `←` | parent: the next node authors the edge back to the current node |

`bd show REF+N` labels each node with the direction of the step that reached it
from the previous ring. `bd show --links` prints one row per undirected
neighbour, deduped, with the arrow on the queried node's side. `bd path REF`
labels every step of the shortest undirected path from the anchor. `bd out` and
`bd in` remain explicitly directional: authored out-edges and derived in-edges.

```sh
bd show 1-1+2 --no-body --links
bd path 10-1
bd out 3-1
bd in 4-1
```

## 7. Filters

`bd graph` accepts three independent controls:

- `--depth N` stops traversal after `N` link hops;
- `--type T` follows only edges with that type (repeatable);
- `--distance A:B` shows only nodes whose ring is in the inclusive range
  `A:B`.

`--distance` is display-only: out-of-range nodes are omitted from the output,
but traversal continues through them, so a later in-range ring remains
reachable. The anchor is always included, even when it is
outside the requested range.

```sh
bd graph 1-1 --depth 1           # rings 0 and 1
bd graph 1-1 --distance 2:3      # ring 0 plus rings 2 and 3
bd graph 1-1 --type supports     # only supports edges are traversed
```

## 8. The flat work area

`bd work REF[+N]` writes the project's single work area, `<project>/bd_work/`.
It is flat: one relative symlink per materialized ref, using the store file's
basename. There are no node directories and no nested folder layout.

```text
bd_work/
├── 1-1.md        -> ../.bd_tree/nodes/1-1.md
├── 2-1.md        -> ../.bd_tree/nodes/2-1.md
├── 3-1.md        -> ../.bd_tree/nodes/3-1.md
├── 4-1.md        -> ../.bd_tree/nodes/4-1.md
├── INDEX.md      generated
├── REFS.md       generated
└── AGENTS.md     generated
```

If two node files share a basename (possible only with `--path-template`), the
ref is appended to the stem. `INDEX.md`, `AGENTS.md`, and `REFS.md` are
reserved names in every directory.

`REF+N` materializes rings `0..N`; `REF` alone materializes the whole component.
The view recorded in the generated headers stays the full component, with the
materialized depth as a suffix.

### 8.1 INDEX.md

`INDEX.md` is one file at the work-area root. It carries a `nodes:` front-matter
path to the store's real `nodes/` directory, a banner, the view label, a link to
the real node folder, and ring sections:

```markdown
# View 1-1

## Active

- [<title>](1-1.md) — [real file](../.bd_tree/nodes/1-1.md)

## Distance 1 — children

- [<title>](2-1.md) — [real file](../.bd_tree/nodes/2-1.md)
- [<title>](3-1.md) — [real file](../.bd_tree/nodes/3-1.md)

## Distance 2

- [<title>](4-1.md) — [real file](../.bd_tree/nodes/4-1.md)
```

Ring 1 is split into `children` and `parents`; deeper rings are
`Distance N` sections. Every node entry also links to its real store file, so a
reader can open, copy, or delete the source instead of the symlink.

### 8.2 REFS.md

`REFS.md` is the navigation table and the active-view marker:

```markdown
# References — view 1-1

| Path | Ref | Kind | Distance | Title |
| --- | --- | --- | --- | --- |
| `1-1.md` | 1-1 | active | 0 | <title> |
| `2-1.md` | 2-1 | child | 1 | <title> |
| `3-1.md` | 3-1 | child | 1 | <title> |
| `4-1.md` | 4-1 | - | 2 | <title> |
```

Rows are sorted by `(distance, kind, ref)`. The header
`# References — view REF[+N]` is the active node of the work area: `bd current`,
`bd edit`, `--status`, and `--writeback` read it. There is no separate state
file and no per-node pointer.

### 8.3 AGENTS.md

`AGENTS.md` explains that every node `.md` is a symlink, that `INDEX.md`,
`REFS.md`, and itself are generated, that this is the only writable area, and
that `--status`/`--writeback` are the repair path. Inside git it also records
the branch, short commit, and worktree. Outside git those lines are omitted and
the layout is unchanged.

## 9. Worked example: the committed store

`examples/` has twelve nodes (`1-1`..`12-1`), one component, and `ROOT` `1-1`.
The authored structural edges produce this distance map from `1-1`:

| Ring | Members |
| --- | --- |
| 0 | `1-1` |
| 1 | `2-1`, `3-1` |
| 2 | `4-1`, `5-1`, `6-1`, `7-1` |
| 3 | `8-1`, `12-1` |
| 4 | `9-1`, `10-1`, `11-1` |

Why `12-1` is ring 3 while `11-1` is ring 4: `12-1` is reached from `4-1`, and
`11-1` is reached from either `8-1` or `12-1`, one hop later. `9-1` and `10-1`
are reached only from `8-1`.

The text render is:

```text
## 0 — 1-1
[1-1] <title>
  → out: 2-1 (breaks_down), 3-1 (breaks_down)

## 1 — children
[2-1] <title>
  ← in: 1-1 (breaks_down)
  → out: 4-1 (breaks_down), 5-1 (breaks_down), 6-1 (breaks_down)
[3-1] <title>
  ← in: 1-1 (breaks_down)
  → out: 4-1 (supports), 7-1 (supports)

## 2
...
## 3
[8-1] ...  [12-1] ...
## 4
[9-1] ...  [10-1] ...  [11-1] ...
```

`4-1` has two parents (`2-1` and `3-1`) and still appears once, in ring 2.
`8-1` has five inbound edges (`4-1`, `5-1`, `6-1`, `7-1`, `12-1`) and still
appears once, in ring 3.

`bd path 10-1` prints the shortest undirected chain from the anchor:

```text
1-1  <title>
→ 2-1  <title>
→ 4-1  <title>
→ 8-1  <title>
→ 10-1  <title>
```

Every step happens to be an authored child edge here, so every arrow is `→`.
With a back-edge in the chain, the corresponding step is `←`.

The work area for `bd work 1-1` is flat:

```text
1-1.md  2-1.md  3-1.md  4-1.md  5-1.md  6-1.md
7-1.md  8-1.md  9-1.md  10-1.md 11-1.md 12-1.md
INDEX.md  REFS.md  AGENTS.md
```

`bd work 1-1+2` writes only `1-1.md`, `2-1.md`, `3-1.md`, `4-1.md`, `5-1.md`,
`6-1.md`, and `7-1.md`; `bd current --view` then prints `1-1+2`.

## 10. Cycles and back-edges

Cycles and back-edges are legal. The edge guards are a self-loop on one ref and
a duplicate edge to the same target with the same type. A reciprocal pair, a
longer cycle, and an edge that points against the authored direction all load
normally.

Take `1-1 -> 2-1 -> 3-1 -> 1-1`. The component is `{1-1, 2-1, 3-1}`. From
`1-1`, the direct edge to `2-1` and the closing edge from `3-1` both matter, so
the distance map is:

```text
1-1  0
2-1  1
3-1  1
```

`3-1` is ring 1 because it links back to the anchor; it is a `parent` of `1-1`.
No cycle error is emitted, no node is visited twice, and the work area writes
each ref once. A cycle with no anchor-side closing edge simply raises distances
along the path until every node is reached.

## 11. Command map

Every command that needs a view rebuilds the same component and distance map.
None reads a layout file.

| Command | What it consumes |
| --- | --- |
| `bd graph [REF]` | The component as ring sections; `--depth`, `--distance`, and `--type` narrow traversal or display. |
| `bd graph --dot` / `--svg` | The same view as a flat Graphviz graph, nodes ordered by distance. |
| `bd show REF[+N]` | BFS rings `0..N`, each node once, with direction arrows. |
| `bd path REF` | Shortest undirected path from the anchor. |
| `bd find QUERY` | The anchor's component by default; `--view` picks another, `--all` searches the store. |
| `bd views` | One representative and size per component. |
| `bd work REF[+N]` | Flat symlinks plus ring-sorted `INDEX.md` and `REFS.md`. |
| `bd work REF --status` | Reads the existing area and its declared view; no rebuild. |
| `bd work REF --writeback` | Re-links detached files after validating their front matter. |
| `bd current [--path\|--view]` | Reports the area and its view; read-only. |
| `bd edit REF` | Path of the ref in the active view. |
| `bd export graph --view REF --out DIR` | Regular-file copy of the flat view plus one ring-section `INDEX.md`. |
| `bd export context --view REF --out DIR` | Fresh nodes only, plus `STALE.md` and `AGENTS.md`. |
| `bd export dot` / `bd export svg` | Flat DOT or rendered SVG; no clusters. |
| `bd clone REF --subtree [--depth N]` | Copies the undirected neighbourhood (rings `0..N`) and rewires cloned edges. |

## 12. Extension guide

### 12.1 Code map

| Piece | Location |
| --- | --- |
| `Store.neighbors`, `Store.components`, `Store.topology_roots` | `src/bd_tree/model.py` |
| `View`, including `distance` | `src/bd_tree/model.py` |
| `ring_distances`, `build_graph` | `src/bd_tree/graph.py` |
| `graph_view` (traversal and filters) | `src/bd_tree/graph.py` |
| `_ring_sections`, `render_graph` | `src/bd_tree/graph.py` |
| `layout_paths`, `export_graph` | `src/bd_tree/graph.py` |
| `_load_graph_view` | `src/bd_tree/loader.py` |
| `walk_neighbors`, `render_show`, `render_path` | `src/bd_tree/navigate.py` |
| `_ring_layout`, `_build`, `_refs_text`, `_agents_text`, `area` | `src/bd_tree/work.py` |
| `_directory_indexes`, `_graph_index_text` | `src/bd_tree/exporter.py` |

### 12.2 Invariants to preserve

- One member once: every component walk uses a seen-set.
- One view per anchor: membership is the whole weak component, not one direction.
- Distance is the only ordering primitive; direction is a label.
- Deterministic output: sort every set by the documented keys before emitting.
- Projection only: no node file is rewritten by browsing, export, or `bd work`.
- Full-ref edges: neighbours come from authored full-ref tokens; in-edges are
  computed by reversing them and never stored.
- One work area: `bd work` replaces the contents of `<project>/bd_work/`.
- The active node is the `REFS.md` header, not an extra file.

### 12.3 Adding a ring-aware command

1. Load with `load_view(store, anchor)` when the whole component is enough, or
   `build_graph(store, anchor=...)` when you need `distance`, `components`, or
   `roots`.
2. Read order from the graph's `distance` map and the documented tie-break. Do
   not re-walk neighbours independently.
3. If the command materializes files, reuse `layout_paths` and `_ring_layout`
   rather than constructing names.
4. Make every tie deterministic; add `(id, version)` as the final key.
5. If it filters, decide explicitly whether the filter stops traversal
   (`--depth`) or only hides output (`--distance`).
6. Add a temporary-store test with the smallest graph that distinguishes the
   behavior, and update this document and `docs/CHEATSHEET.md`.

### 12.4 What must not change

- Membership is undirected; cycles are ordinary edges.
- No authored placement field returns.
- Full-ref data edges and sorted tokens.
- The three generated names stay reserved.
- `bd_work/` stays flat.

## 13. Known limits

- **Distance is not semantic order.** A hop count measures graph nearness, not
  importance, authority, or reading order. A long chain of important nodes can
  sit in ring 9 while a minor aside sits in ring 1.
- **Ring 1 is not always "children".** It is split by direction so the labels
  stay honest, but the graph may author a back-edge; read the arrow, not the
  ring number.
- **Cycles shorten distances.** A closing edge can put a distant node in ring 1.
  The order is still deterministic; it is just not a topological order.
- **Multiple shortest paths.** `bd path` prints one shortest path, chosen by the
  deterministic neighbour order. Other equally short paths exist.
- **Disconnected stores.** Removing the last edge between two groups creates two
  components. `bd views` lists both; the default anchor stays in one.
- **No authored hierarchy.** If a project needs a declared parent/child reading
  order, encode it with typed tokens and direction, not with positional
  fields.
- **Template collisions.** Two nodes can resolve to one path only through
  `--path-template`; the layout appends the ref to keep them distinct.

## 14. Test map

| Case | Test | What it pins |
| --- | --- | --- |
| Component view | `test_view_is_the_whole_connected_component` | membership is undirected |
| Distance map | `test_view_distance_is_undirected_bfs` | BFS hop counts |
| Multi-parent | `test_a_multi_parent_node_appears_once_in_the_view` | one entry per node |
| Cycle loads | `test_graph_cycle_loads_once_and_is_not_an_error` | cycles are legal |
| Neighbour kinds | `test_neighbors_lists_both_directions_with_kind` | child/parent |
| Components | `test_components_are_one_per_weak_component` | component partition |
| Ring map | `test_ring_distances_maps_every_reachable_ref` | minimum rings |
| Cycle distance | `test_a_cycle_loads_and_rings_use_the_minimum_distance` | closing edge shortens |
| Reciprocal pair | `test_a_reciprocal_pair_is_legal_and_not_a_back_edge` | both sides are children |
| Ring headings | `test_render_graph_ring_headings_split_ring_one` | ring 1 split order |
| Text filters | `test_type_and_distance_filters` | `--type`, `--distance`, `--depth` |
| Flat paths | `test_layout_paths_is_flat_and_uses_store_basenames` | basename layout |
| Template fields | `test_layout_paths_template_placeholders_and_front_matter` | `{distance}` and fields |
| Work rings | `test_work_index_uses_ring_sections` | `Active`, `Distance N` |
| Work cycle | `test_work_cycle_appears_once_at_minimum_distance` | one symlink per ref |
| Show rings | `test_show_depth_two_uses_undirected_bfs_rings` | `show REF+N` |
| Path arrows | `test_path_command_prints_shortest_path_with_arrows` | shortest path labels |
| Example store | `test_example_graph_renders_rings_and_audits_clean` | rings 0..4, clean audit |
| Export | `test_graph_export_is_flat_with_ring_sections_and_byte_stable` | one flat index |
| Views CLI | `test_graph_roots_lists_one_representative_per_component` | one line per component |
