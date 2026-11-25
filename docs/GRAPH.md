# The graph

`bd` has one topology: a graph of markdown nodes joined by typed link tokens in
their bodies. A node declares edges, in-edges are derived, and a view is the
weakly connected component of one anchor over the authored links. Direction
survives as a label, not as a membership rule. The default example at
`examples/` is a twelve-node graph with `ROOT` `1-1` and rings 0 through 4.

A node that still declares `contains` is not a different topology: `bd check`
reports `contains-removed` and tells you to run `bd migrate` (§ Migration).

## Model

A link is a reserved token in the node body:

```markdown
The intent breaks down into [[breaks_down, 2-1]](Structural claims).

## Links
- [[verifies, 12-1]](Verification core)
```

Both forms declare the same thing: one typed out-edge from this node to a full
ref. Authors write tokens inside prose; `bd new --parent`, `bd link`, and
`bd migrate` maintain a trailing `## Links` section of
`- [[TYPE, REF]](TITLE)` lines. `bd unlink` removes token lines, and
`bd replace` / `bd clone --subtree` rewrite token refs in place.

- `TYPE` matches `[A-Za-z][A-Za-z0-9_-]*` and is never empty; `REF` is a full
  `<id>-<version>` ref. A bare ref in a token fails the grammar
  (`inline-malformed`); `bare-ref` is reported for a bare `ROOT` line.
- `(TITLE)` is a cached copy of the target's live title and is advisory.
  Rendering always reads the live title; only `bd check` compares the cache and
  warns `link-title-stale`.
- Tokens inside fenced code blocks, inline code spans, and escaped as `\[[` are
  ignored. Indented code blocks and HTML comments are not shielded: a token
  there is read as a link.
- A malformed token is `inline-malformed`; the same type and target declared
  twice is `inline-duplicate`.
- Front-matter `links` is retired: a node that still declares it fails with
  `links-removed`, and `bd migrate` moves the list into the body.

The authored data is the **out-edge token list** on each node. **In-edges are
always derived** by reversing those tokens. There is no symmetric master and no
derived opposite: a node that should acknowledge an edge authors its own token,
with its own type. `bd in` labels every computed line `[derived]`; nothing else
is marked derived.

Tokens are expected in ascending target-ref order; `graph-unsorted-links`
warns otherwise. `bd clone --subtree` follows the undirected component.

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

Direction is a label on each neighbour: `child` (an authored out-link) or
`parent` (another node's out-link targets this one). It orders ring 1 into
children and parents. Deeper rings are not split.

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
anchor. Ring 0 is the anchor. Ring 1 is split into `children` and `parents`,
each sorted by `(link type, id, version)`. Rings 2 and deeper are numbered
sections sorted by `(id, version)`. The canonical global key is
`(distance, kind_rank, link type, id, version)`, where `kind_rank` is
`child: 0`, `parent: 1`.

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
bd out 1-1      # the declared tokens of 1-1, sorted, no inference
bd in 4-1       # computed parents of 4-1, every line marked derived
```

`bd graph` prints, for each node, `← in:` (derived) and `→ out:` (authored).
`bd show --links` prints one undirected neighbour row per edge with an arrow:
`→` child, `←` parent.

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
| `links-removed` | error | a node still declares front-matter `links`; run `bd migrate` |
| `bare-ref` | error | a data ref is a bare id; use a full `<id>-<version>` ref |
| `invalid-ref` | error | a data ref or CLI selector is malformed |
| `inline-malformed` | error | a `[[...]]` fragment does not match `[[TYPE, REF]]` |
| `inline-duplicate` | warning | one node declares the same type and target twice |
| `invalid-freshness` | error | the `freshness:` map or an entry has the wrong shape |
| `link-title-stale` | warning | a cached token title differs from the target's live title |
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
2. `contains: [c0, c1, ...]` becomes one typed token per child in a trailing
   `## Links` section, and the key is removed. The edge type comes from
   `--type` (default `breaks_down`).
3. Front-matter `links` moves into that section as sorted
   `- [[TYPE, REF]](TITLE)` lines; a retired scalar link gains an explicit type.
   Per-link `pinned`/`propagates` values move to the top-level `freshness:` map,
   and `symmetric`/`inverse` are dropped.
4. Retired placement keys are stripped from every node (`band`, `subpath`,
   `layer`, `stage`, `order`) and from the ROOT node (`band_layout`,
   `band_order`).

`bd migrate --dry-run` prints the plan without writing; `bd migrate` applies it
atomically; `--root` selects the store. After migration `bd check` passes.
There is no placement flag; migration is idempotent, and a token-only store is
left untouched.

```sh
bd migrate --root docs/breakdown --dry-run
bd migrate --root docs/breakdown
```

## Scale notes

- Keep a node's tokens in ascending target-ref order. Sorted declarations keep
  a merge local to the edge that changed.
- When one node fans out too widely, insert an intermediate header instead of
  adding hundreds of direct edges. Audit warns above 200 out-links.
- Sorting is numeric by `(id, version)`, matching the rest of the store.
- Reachability is a query, not stored placement: adding a parent adds no file
  and no positional field. In-edges are derived, so no parent array is rewritten.

## Example store

`examples/` is the default store: twelve nodes, one component, no `contains`,
and no placement key. Its nine linked nodes carry their tokens inline in prose,
each with a cached title. From `1-1` the rings are:

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
