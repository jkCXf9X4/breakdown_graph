# Graph band layout

This document is the reference for how a graph store turns `band` values, an
optional `subpath`, and forward *structural* `links` into directories. It covers the exact algorithm, the tie-breaks,
the diagnostics, the commands that consume the projection, and the tests that
pin it.

[`DESIGN.md`](DESIGN.md) owns the model and [`GRAPH.md`](GRAPH.md) owns the
topology and commands. This document owns one question: **given a graph view,
which folder does each node land in?** Bands are the only layout; `section` and
`group` place nothing.

## 1. Data versus projection

The source of truth is the node files. For layout, only two pieces of authored
data matter:

- `band`: the band name, plus an optional `subpath` such as `structural`;
  `layer: band/subpath` is the older single-string shorthand.
- `links`: forward parent-to-child structural edges carrying full target refs.
  A symmetric link (`symmetric: true`) is a master whose opposite is derived;
  it adds no band edge and orders no band.

Nothing else is stored. There is no layout file, no ordinal field, no state
file, and no cached plan. Band ordinals, inferred nesting, and folders are
recomputed from the store on every command. The projection is disposable:
inserting a band renumbers later folders without touching a node file.

`order` is authored data too, but it orders nodes inside a band; it does not
choose bands or folders. `group` is ordinary metadata and never places a node
(see §5).

## 2. Terms

| Term | Meaning |
| --- | --- |
| band | The node's `band` string, or the `layer` path's first segment. It is the unit of inference. |
| subpath | The optional placement folder below the band folder. |
| layer | The older shorthand `layer: band/subpath`, normalized to band plus subpath. |
| layer path | A parsed band plus optional subpath. |
| band graph | The directed graph whose nodes are bands and whose edges come from structural links crossing bands. |
| top-level band | A band that gets its own `NN-<slug>` root folder. |
| nested band | A band placed below a top-level band folder by inference. |
| effective folder | The full directory a node's file uses. |
| band ordinal | The zero-based position of a node's top-level band; it is the value `--stage` filters on. |
| order | The integer `order` used inside a band and inside a folder. |

A node belongs to exactly one band (its `band`) and exactly one effective
folder (band folder plus optional `subpath`).

## 3. Detection and modes

`relative_store` (`src/bd_tree/graph.py:315`) checks whether **any** node
declares `stage`.

- **Absolute mode**: at least one node has `stage`. Bands are the integer
  stages. `band`/`layer` is only a label source. `group` is inert. See §6.12.
- **Relative mode**: no node declares `stage`. Bands come from `band`/`layer`
  and the band graph. This is the mode described below and used by `examples/`.

The modes are per store, never per node. Do not mix `stage` and relative
inference in one store. Relative mode does not require `stage`, and a store with
no `stage` key is not invalid.

## 4. The algorithm

The implementation is `_relative_plan` (`src/bd_tree/graph.py:598`), with helpers
listed in §8.1. The steps are:

### 4.1 Parse and validate bands

For each node, `layer_path` (`:216`) normalizes either form:

```text
band = "claims"
subpath = "structural/fan-in"
```

```text
layer = "claims/structural/fan-in"   # shorthand: same band and subpath
```

A node declares exactly one form. `band` is a single segment; `subpath` is a
slash-separated relative path. Both are valid when a string whose stripped form
is non-empty, with no backslash and no empty, `.`, `..`, reserved generated
(`INDEX.md`, `AGENTS.md`, `REFS.md`), or `.md` segment. A `subpath` without
`band`, a `band` containing `/`, or a node mixing `layer` with
`band`/`subpath` is `graph-layer-invalid`. A node with neither is
`graph-layer-missing`. Neither creates a band.

### 4.2 Build the band graph

`_band_edges` (`:402`) scans every authored *structural* link. When source and
target are both valid and their bands differ, add `band(source) ->
band(target)`. Links inside one band add no edge, even when they cross subpaths.
A symmetric link contributes no band edge. A link to a missing
node, or one with an invalid band, adds no edge.

Cycles in this graph are reported by `_layer_cycles` (`:484`) as
`graph-layer-cycle`; strong components of size greater than one are sorted.

### 4.3 Choose top-level bands

`_top_level_bands` (`:581`) works per weakly connected component of the band
graph (`_band_components`, `:536`):

1. Compute indegree and outdegree inside the component.
2. If the component has no edge, every band in it is top-level, kind `2`
   ("isolated"), distance `0`.
3. Otherwise, if the component has no root (indegree `0`) or no sink
   (outdegree `0`), every band is top-level, kind `1` ("cycle-only"),
   distance `0`.
4. Otherwise, let `from_roots` be the unweighted multi-source BFS distance from
   all roots (`_distances`, `:563`), and let `to_sinks` be the same distance to
   all sinks over reversed edges.
5. Let `L = min(from_roots[sink])` over sinks: the shortest root-to-sink
   distance in the component.
6. A band is top-level iff `from_roots[band] + to_sinks[band] == L`.
7. Rank top-level bands by `(kind, distance, band)` where kind is `0` for an
   acyclic connected component, `1` for a cycle-only component, and `2` for an
   isolated component; distance is `from_roots`; the final tie-break is the
   band name in lexicographic order. The rank position is the ordinal `NN`.
   `band_order` does not change this ranking; it only breaks ties in the
   topological order (§4.5) and orders flat top-level folders.

This is the **shortest-path rule**. A band that lies only on a longer detour is
not top-level; a band that lies on at least one shortest root-to-sink path is.
The rule is a convention for producing a readable tree. It is not a proof about
the project's semantics, and the graph itself does not distinguish a detour from
a main line.

If no band satisfies the equality (defensive fallback), the roots become
top-level.

**Flat bands.** Set `band_layout: flat` on the store's `ROOT` node to skip the
shortest-path rule. Every band then becomes top-level, ordered by `_layer_order`
(`:446`); explicit `subpath` values still nest below their band folder. A ROOT
`band_order` list composes: the flat top-level folders are ordered by the hint. This is
a per-store projection convention, not a change to link semantics.

### 4.4 Build top-level folders

For each top-level band, in rank order:

```text
folder = f"{ordinal:02d}-{slugify(band) or 'band'}"
```

`slugify` (`src/bd_tree/model.py:26`) lowercases, folds non-ASCII, and collapses
runs outside `[a-z0-9]` into `-`. The ordinal is zero-based and padded to at
least two digits.

### 4.5 Nest the remaining bands

`_layer_order` (`:446`) produces a deterministic topological order, lexicographic
on ready bands unless the ROOT `band_order` hint reranks them; bands left out by
a cycle are appended sorted by name.

Then, in that order, for each band not already placed:

1. Candidates are incoming band-graph parents that are already placed.
2. If none, defer the band to the fallback list.
3. Otherwise choose the candidate with the greatest `from_roots` distance, and
   break a tie by the lexicographically smallest band name.
4. Set `folder = parent_folder + "/" + slugify(band)`, and inherit the parent's
   top-level band as the band ordinal's ancestor.

Deferred bands are appended after all existing top-level bands, sorted by band
name, each with its own `NN-<slug>` folder and ordinal. This keeps an
unattachable band renderable without inventing an edge.

### 4.6 Attach explicit subpaths and node files

Each node's effective folder is its band's folder, plus `/<subpath>` verbatim
when the node declares one (or its `layer` shorthand has more than one
segment). An explicit subpath always nests below its band folder; it never
changes band inference and does not force the band to be nested.

The file stem is unchanged by layout: explicit `name`, else
`<ref>-<title-slug>`, else `<ref>`, with `.md` appended. `layout_paths`
(`:1561`) joins folder and stem and rejects collisions or a file/directory path
conflict.

### 4.7 Ordinals and `--stage`

Every ref maps to the ordinal of its top-level band. A nested band inherits the
ordinal of the top-level band it was placed under. `--stage A:B` filters on that
ordinal, inclusive; the anchor is always included.

### 4.8 Ordering inside a band and folder

`graph_layout` (`:1010`) groups refs by band and sorts by effective folder, then
`(order, id, version)`. Inside one folder the effective sort is
`(order, id, version)`.

A link whose endpoints share one band must satisfy
`order(source) < order(target)`. This applies across different subpaths of the
same band; otherwise the audit reports `graph-order-back-edge`. Band-wide order
is intentional: a band is one unit even when its nodes live in several folders.

### 4.9 Invalid data still renders

If a node's band is missing or invalid, the node cannot enter the band graph.
The plan collects those refs, sorted by `(id, version)`, and places them in one
trailing `NN-unlayered` band (`UNLAYERED`). This is a rendering fallback only:
it is not a band assignment, not an ordering claim, and it is not a substitute
for the audit errors. The audit still reports `graph-layer-missing` or
`graph-layer-invalid`.

## 5. Diagnostics

| Code | Level | Cause | Effect |
| --- | --- | --- | --- |
| `graph-layer-missing` | error | relative store, node has no `band` or `layer` | node goes to `unlayered` for rendering |
| `graph-layer-invalid` | error | invalid `band`, `subpath`, or `layer` (type, empty, bad segment, backslash, `.md`, reserved name), a `subpath` without `band`, or both forms at once | node goes to `unlayered` for rendering |
| `graph-layer-cycle` | error | strong component of the band graph with more than one band | deterministic cycle fallback; audit fails |
| `graph-order-back-edge` | error | same-band link has `order(source) >= order(target)` | audit fails; layout still renders |
| `invalid-band-order` | error | the ROOT `band_order` value is not a YAML list | hint ignored; layout still renders |
| `graph-group-ignored` | warning | graph node declares `group` | none; `group` never places a node |

Absolute mode, for contrast: `graph-stage-missing` and `graph-stage-invalid`
replace the layer errors; `graph-back-edge` replaces the layer-cycle and order
rules (`stage(source) < stage(target)`); `graph-order-invalid` applies in both
modes. `graph-dangling-link` and `graph-cycle` are shared. There is no
`graph-group-invalid`: `group` is not validated because it has no placement
meaning in a graph store.

## 6. Worked examples

Each example names the test in `tests/test_layer_paths.py` that pins it. Band
edges are written `source -> target`.

### 6.1 Single chain: the example store

Bands: `intent`, `breakdown`, `claims`, `verification`, `operation`;
subpaths `structural`, `verification`, `fan-in`, and `fan-in2`.

Band edges: `intent -> breakdown`, `breakdown -> claims`,
`claims -> verification`, `verification -> operation`.

Every band lies on the one root-to-sink path, so all are top-level and kind
`0`:

| Ordinal | Band | Folder |
| --- | --- | --- |
| 0 | intent | `00-intent` |
| 1 | breakdown | `01-breakdown` |
| 2 | claims | `02-claims` |
| 3 | verification | `03-verification` |
| 4 | operation | `04-operation` |

Explicit subpaths produce `02-claims/structural`, `02-claims/verification`,
`03-verification/fan-in`, and `03-verification/fan-in2`; `12-1` declares only
`band: verification` and sits directly in `03-verification`. Example paths:
`02-claims/structural/4-1-two-parents-one-node.md`,
`02-claims/verification/7-1-derived-in-edges.md`,
`03-verification/12-1-verification-core.md`,
`03-verification/fan-in/8-1-verification-fan-in.md`,
`03-verification/fan-in2/11-1-verification-fan-in-2.md`.

Test: `test_single_chain_example_is_all_top_level_with_identical_paths`.

### 6.2 Fork with parallel detours

Layers: `intent` (1-1), `breakdown` (2-1), `sub-a` (3-1), `sub-b` (4-1),
`claims` (5-1). Edges: `1 -> 2`, `2 -> 3`, `2 -> 4`, `2 -> 5`, `3 -> 5`,
`4 -> 5`.

Band edges: `intent -> breakdown`, `breakdown -> sub-a`,
`breakdown -> sub-b`, `breakdown -> claims`, `sub-a -> claims`,
`sub-b -> claims`.

Shortest root-to-sink distance `L = 2` (`intent -> breakdown -> claims`).
Top-level: `intent` (0+2), `breakdown` (1+1), `claims` (2+0). `sub-a` and
`sub-b` are 2+1=3 and not top-level. Nesting chooses `breakdown` as their
placed parent with distance 1.

| Band | Ordinal | Folder |
| --- | --- | --- |
| intent | 0 | `00-intent` |
| breakdown | 1 | `01-breakdown` |
| claims | 2 | `02-claims` |
| sub-a | 1 | `01-breakdown/sub-a` |
| sub-b | 1 | `01-breakdown/sub-b` |

Test: `test_parallel_detours_nest_under_their_shortest_path_parent`.

### 6.3 Nested detour

Same as 6.2, but `sub-a -> sub-sub` and `sub-sub -> claims` instead of
`sub-a -> claims`. Band edges add `sub-a -> sub-sub`,
`sub-sub -> claims`.

`L` is still 2. Top-level is still `intent`, `breakdown`, `claims`. Placement
order visits `sub-a`, then `sub-b`, then `sub-sub`; `sub-sub`'s only placed
parent is `sub-a`, so it stacks:

| Band | Ordinal | Folder |
| --- | --- | --- |
| intent | 0 | `00-intent` |
| breakdown | 1 | `01-breakdown` |
| claims | 2 | `02-claims` |
| sub-a | 1 | `01-breakdown/sub-a` |
| sub-b | 1 | `01-breakdown/sub-b` |
| sub-sub | 1 | `01-breakdown/sub-a/sub-sub` |

Test: `test_nested_detour_stacks_under_the_placed_child`.

### 6.4 Equal-length parallel branches

Layers: `intent` (1-1), `alpha` (2-1), `beta` (3-1), `sink` (4-1). Edges:
`1 -> 2`, `1 -> 3`, `2 -> 4`, `3 -> 4`.

Band edges: `intent -> alpha`, `intent -> beta`, `alpha -> sink`,
`beta -> sink`. `L = 2`. Both branches are shortest, so both are top-level:
`intent` distance 0, `alpha` and `beta` distance 1, `sink` distance 2. Ties by
band name give `alpha` before `beta`.

| Band | Ordinal | Folder |
| --- | --- | --- |
| intent | 0 | `00-intent` |
| alpha | 1 | `01-alpha` |
| beta | 2 | `02-beta` |
| sink | 3 | `03-sink` |

Test: `test_equal_length_parallel_branches_are_both_top_level`.

### 6.5 Explicit path override

Layers: `intent` (1-1), `breakdown/sub-a` (2-1), `claims` (3-1). Edges:
`1 -> 2`, `2 -> 3`.

Band edges: `intent -> breakdown`, `breakdown -> claims`. All three bands are
top-level. Node 2-1 carries an explicit subpath, so its folder becomes:

```text
01-breakdown/sub-a/2-1.md
```

The explicit subpath does not force `breakdown` to nest again. Test:
`test_explicit_layer_path_wins_over_inference`.

### 6.6 Multi-segment explicit subpath

Layers: `intent` (1-1), `claims/structural/fan-in` (2-1). Edge: `1 -> 2`.
Bands: `intent` ordinal 0, `claims` ordinal 1, both top-level. The subpath is
kept verbatim:

```text
01-claims/structural/fan-in/2-1.md
```

Test: `test_multi_segment_explicit_subpath_is_kept_verbatim`.

### 6.7 Band cycle

Layers: `a` (1-1), `b` (2-1). Edges: `1 -> 2`, `2 -> 1`. Band edges:
`a -> b`, `b -> a`. The component has edges but no root and no sink, so it is
cycle-only: all bands are top-level, kind `1`, sorted by name. The plan reports
`graph-layer-cycle`; rendering is deterministic:

| Ordinal | Band | Folder |
| --- | --- | --- |
| 0 | a | `00-a` |
| 1 | b | `01-b` |

Test: `test_band_cycle_is_reported_and_rendering_is_deterministic`.

### 6.8 Missing or invalid band

Nodes 2-1 (`intent`) links to 1-1 (`a//b`, invalid) and 3-1 (no `band`).
Only `intent` is a valid band, so it is top-level ordinal 0. The two bad refs
are sorted and placed in the trailing fallback:

```text
01-unlayered/1-1.md
01-unlayered/3-1.md
```

Audit reports one `graph-layer-invalid` and one `graph-layer-missing`. This is
not a synthetic band assignment. Test:
`test_missing_and_invalid_layers_fall_back_to_one_trailing_band`.

### 6.9 Same-band order back-edge

Layers: `build/x` (1-1, `order: 2`) links to `build/y` (2-1, `order: 1`). The
link stays inside band `build`, so it adds no band edge. `build` is top-level
ordinal 0; effective folders are `00-build/x` and `00-build/y`. The audit
reports `graph-order-back-edge` because `2 >= 1`, including across subpaths.

Test: `test_same_band_order_back_edge_is_reported_across_subpaths`.

### 6.10 Disconnected bands

Nodes: 1-1 `intent -> 2-1 sink`, 3-1 `zebra`, 4-1 `alpha`. Components:
`{intent, sink}` (kind 0), `{alpha}` (kind 2), `{zebra}` (kind 2). Rank:

| Ordinal | Band | Rank key | Folder |
| --- | --- | --- | --- |
| 0 | intent | `(0, 0, intent)` | `00-intent` |
| 1 | sink | `(0, 1, sink)` | `01-sink` |
| 2 | alpha | `(2, 0, alpha)` | `02-alpha` |
| 3 | zebra | `(2, 0, zebra)` | `03-zebra` |

Connected components come before isolated bands; isolated bands sort by name.
Test: `test_disconnected_bands_are_top_level_after_connected_ones`.

### 6.11 `group` is inert

Node 2-1 has `band: claims`, `subpath: structural`, and `group: ignored`. The
effective folder comes only from the band and subpath:
`01-claims/structural/2-1.md`. The audit warns `graph-group-ignored` and
suggests `band` plus `subpath` instead.
Text and DOT rendering never print `group`. The example store has no `group`
key at all. Test:
`test_group_is_ordinary_metadata_and_warns_in_graph_mode`.

### 6.12 Absolute stage mode is unchanged

Nodes 1-1 (`stage: 0`) links to 2-1 (`stage: 1`, `group: structural`) and
3-1 (`stage: 1`, `group: verification`, `order: 1`). Because a `stage` exists,
relative inference is off. Stage 1's label is the dominant non-empty
`band`/`layer` label
in that stage (`claims`), both nodes land in `01-claims`, and `group` changes
nothing:

```text
01-claims/2-1.md
01-claims/3-1.md
```

DOT labels the cluster `stage 1 — claims`. Test:
`test_absolute_stage_mode_is_unchanged_and_ignores_group`.

The link guard and materialization paths are also pinned by
`test_link_refuses_band_cycle_and_same_band_order_and_new_accepts_paths` and
`test_materialization_tree_work_and_exports_use_nested_folders`.

## 7. Command map

Every command that needs a path builds the same plan. None reads a layout file.

| Command | What it consumes |
| --- | --- |
| `bd graph [REF]` | `graph_view` then the band/folder layout; the text renderer. `--depth` bounds link hops, not bands. |
| `bd graph [REF] --stage A:B` | Filters on the top-level ordinal. |
| `bd graph --dot` | One cluster per effective band folder; label `layer N — band[/subpath]`. |
| `bd graph --svg --out PATH` | Same DOT fed to Graphviz `dot`. |
| `bd work REF` | `layout_paths`: symlink tree at `<project>/bd_work/`. |
| `bd work REF --status` | Reads the existing symlink tree; no layout change. |
| `bd current [--path\|--view]` | Reports the area and its view; does not rebuild. |
| `bd edit REF` | Path of the ref in the active view. |
| `bd export graph --view REF --out DIR` | Regular-file copy of `layout_paths`, plus per-folder `INDEX.md`. |
| `bd export dot --view REF --out FILE` | Flat DOT, no band clusters, labels from the same plan. |
| `bd export svg --view REF --out FILE` | Rendered flat DOT. |

## 8. Extension guide

### 8.1 Code map

| Piece | Location |
| --- | --- |
| `LayerPath` | `src/bd_tree/graph.py:105` |
| `parse_layer`, `require_layer`, `layer_path` | `:138`, `:292`, `:216` |
| `relative_store` | `:312` |
| `flat_bands` | `:317` |
| `band_order_hint` | `:382` |
| `BandPlan` | `:364` |
| `_band_edges` | `:402` |
| `layer_reaches` | `:425` |
| `_layer_order` | `:446` |
| `_layer_cycles` | `:484` |
| `_band_components` | `:536` |
| `_distances` | `:563` |
| `_top_level_bands` | `:581` |
| `_relative_plan` | `:652` |
| `_absolute_plan` | `:780` |
| `build_graph` | `:829` |
| `graph_layout` | `:1010` |
| `layout_paths` | `:1561` |
| `audit` | `:1387` |

### 8.2 Invariants to preserve

- One band per node: from `band` (or the `layer` shorthand); no node is counted twice.
- One effective folder per node: band folder plus optional explicit subpath.
- Deterministic output: sort every set before iterating; keep the documented
  tie-breaks.
- Projection only: no node file is rewritten, no state file appears, and
  `bd work` does not become a second source of truth.
- Full-ref edges: band edges are derived from authored full-ref *structural*
  links; no bare id is written to data, and symmetric links add none.
- One bug class per seam: inference in `_relative_plan`, rendering in
  `graph_layout`/`layout_paths`, diagnostics in `audit`.

### 8.3 Adding an inference rule

1. Decide whether it changes bands, nesting, or only display. Put band and
   nesting rules in `_relative_plan`; put file naming in `_node_path`.
2. Compute over the parsed plan, not over raw strings, so invalid nodes stay in
   `unlayered`.
3. Make every tie deterministic. If two bands or parents compare equal, add a
   final name or ref tie-break.
4. Make it a projection: never add a field, never require a new key, never
   mutate a node.
5. Add a temporary-store test with the smallest graph that distinguishes the new
   rule; add a worked example and a test-map row here.
6. Re-run the examples: `bd check`, `bd audit`, `bd work 1-1`, and both exports.

### 8.4 What must not change

- Absolute mode: integer `stage` bands, forward edges, `band`/`layer` only as a label,
  `group` inert.
- Bands are the only layout: `section` and `group` never place a node.
- Full-ref data edges and sorted `links`.
- The reserved generated names in a layer path.

## 9. Known limits

- **Convention, not proof.** The shortest-path rule picks a readable main line.
  It cannot know which detour is semantically optional.
- **Equal-length branches.** Parallel branches of the same length all become
  top-level; the tool does not guess an owner.
- **Mandatory detours.** A band on every root-to-sink path stays top-level even
  if it is conceptually a sub-step.
- **Cycles.** Rendering is deterministic but meaningless as order; fix the
  cycle with `bd unlink`/`bd link`.
- **Disconnected components.** They are ordered by kind and name, not by
  project intent.
- **Renumbering.** Inserting a band before existing top-level bands shifts later
  `NN-` prefixes. Paths churn; node data does not.
- **`unlayered`.** A rendering fallback only; it never repairs validation.
- **Slug collisions.** Different band names can slugify to one folder (for
  example `A B` and `a-b`). `layout_paths` rejects file and directory
  collisions with `ExportError`; rename the band.
- **Explicit subpaths are verbatim.** They can collide with an inferred folder
  or another subpath; the collision is an export error, not a merge.
- **Nesting is not guaranteed.** A band can be unattachable and is then appended
  as an extra top-level band.

## 10. Test map

| Case | Test | What it pins |
| --- | --- | --- |
| Example chain | `test_single_chain_example_is_all_top_level_with_identical_paths` | five top-level bands, identical paths, subpaths |
| Parallel detours | `test_parallel_detours_nest_under_their_shortest_path_parent` | `L` rule, nesting parent, ordinals |
| Nested detour | `test_nested_detour_stacks_under_the_placed_child` | recursive folder stacking, text indentation |
| Equal branches | `test_equal_length_parallel_branches_are_both_top_level` | both branches top-level, name tie-break |
| Explicit path | `test_explicit_layer_path_wins_over_inference` | subpath below the band, no double nesting |
| Multi-segment path | `test_multi_segment_explicit_subpath_is_kept_verbatim` | verbatim subpath |
| Band cycle | `test_band_cycle_is_reported_and_rendering_is_deterministic` | `graph-layer-cycle`, deterministic fallback |
| Invalid layers | `test_missing_and_invalid_layers_fall_back_to_one_trailing_band` | both codes, one trailing `unlayered` |
| Same-band order | `test_same_band_order_back_edge_is_reported_across_subpaths` | band-wide order, subpath crossing |
| Disconnected | `test_disconnected_bands_are_top_level_after_connected_ones` | kind ordering, name ordering |
| `group` | `test_group_is_ordinary_metadata_and_warns_in_graph_mode` | warning, path unaffected, example has none |
| Absolute mode | `test_absolute_stage_mode_is_unchanged_and_ignores_group` | stage labels, inert `group` |
| Link guard | `test_link_refuses_band_cycle_and_same_band_order_and_new_accepts_paths` | cycle and order refusal, `--band`/`--subpath` paths |
| Materialization | `test_materialization_tree_work_and_exports_use_nested_folders` | `bd work`, `bd edit`, exports, DOT/SVG |
