# Graph mode (prototype)

Graph mode is an additive prototype beside containment. It reads the same flat
store, but it never consults `contains`: a view is computed from declared
`links`, so one node can have any number of parents without changing the
containment model.

> **Prototype and additive.** Containment is still supported and unchanged:
> `bd check`, `bd work`, `bd export tree`, `bd export context`, and
> `bd export dot` keep their existing meaning. Use `bd audit` for graph-mode
> validation; `bd check` still validates containment. The default example store
> at `examples/` is a graph.

## Model

An edge is declared on its parent node as `parent -> child` in `links`:

```yaml
links:
  - to: 4-1
    type: breaks_down
```

`links` is already parsed by the loader, and data refs are full
`<id>-<version>` refs. Graph mode ignores `contains` completely.

Every node carries an integer `stage`. Edges must be strictly forward:
`stage(source) < stage(target)`. Inside one stage, `order` (default `0`) is the
tie-break. Missing or non-integer stages are errors; a non-integer `order` is an
error.

The authored data is the **out-edge list** on each node. **In-edges are always
derived** by reversing those declarations. Audit and rendering label them
`derived`; nothing infers an edge that is not written in a node file.

A bare id on the command line selects the highest existing version. A full ref
is used verbatim.

## View as a query

A graph view is the forward closure of one anchor over authored out-edges:

- the anchor is always included;
- a node reached through many parents is included once;
- `--type T` follows only links with that type (repeatable);
- `--stage A:B` keeps nodes whose `stage` is in the inclusive range;
- `--depth N` bounds traversal to `N` edge hops.

The default anchor is the store `ROOT` when present, else the lowest root (a
node with no incoming edge).

```sh
bd graph                    # text render from the default anchor
bd graph 1-1 --depth 1      # direct children only
bd graph --stage 2:3        # two stages
bd graph --type supports    # follow one edge kind
bd graph --dot              # Graphviz DOT
```

## Layout

Text rendering and export group refs by stage, then sort inside a stage by
`(order, id, version)`. A band label is the most common non-empty `layer`
metadata in that stage, slugified, with a lexicographic tie-break; without a
`layer` it falls back to `stage-NN`. The directory name is `<NN>-<label>`, with
the stage number zero-padded to at least two digits.

## Authored out-edges, derived in-edges

```sh
bd out 1-1      # the declared links of 1-1, sorted, no inference
bd in 4-1       # computed parents of 4-1, every line marked derived
```

`bd graph` prints, for each node, `← in:` (derived) and `→ out:` (authored).

## Audit

`bd audit [REF]` collects graph-mode issues and exits non-zero when any error is
present. The default anchor is the same as `bd graph`.

| Code | Level | Meaning |
| --- | --- | --- |
| `graph-stage-missing` | error | the node has no `stage` |
| `graph-stage-invalid` | error | `stage` is not an integer (booleans are rejected) |
| `graph-order-invalid` | error | `order` is not an integer |
| `graph-back-edge` | error | `stage(source) >= stage(target)` |
| `graph-dangling-link` | error | a link target does not exist |
| `graph-cycle` | error | DFS finds a cycle; the path is reported |
| `graph-orphan` | warning | a non-anchor node has no incoming edge |
| `graph-wide-fanout` | warning | out-degree above 200; split into an intermediate header |
| `graph-duplicate-version` | warning | one id has several versions reachable from the anchor |
| `graph-unsorted-links` | warning | a node's link targets are not sorted by ref |

## Export

`bd export graph` writes a read-only snapshot of one graph view:

- node files as regular files at `<NN>-<label>/<ref>-<slug>.md` (a node `name`
  is used for the stem when present);
- one `INDEX.md` per stage with direct nodes, authored `→` out-links and derived
  `←` in-links;
- a root `INDEX.md` listing each stage with its node count and a link to its
  index.

The output is deterministic and byte-identical across runs. `--force` writes
into a non-empty directory; `--clean` removes the output first.

```sh
bd export graph --view 1-1 --out /tmp/bd-graph
```

## Scale notes

- Keep every node's `links` sorted by ref. Sorted lists keep a merge local to
  the edge that changed.
- When one node fans out too widely, insert an intermediate header instead of
  adding hundreds of direct edges. Audit warns above 200 out-links.
- Sorting is numeric by `(id, version)`, matching the rest of the store.
- Reachability is a query, not stored placement: adding a parent adds no file
  and no containment edge.

## Example store

`examples/` is the default graph store, with no `contains` and no `section`. It
proves a claim with two parents, sorted links, and a forward-only stage chain.

```sh
bd graph
bd out 1-1
bd in 4-1
bd audit
bd export graph --view 1-1 --out /tmp/bd-graph
```

The repository `.bd_root` pointer names `examples`, so plain `bd` finds it from
the repo root. An explicit root works too:

```sh
bd --root examples graph
```
