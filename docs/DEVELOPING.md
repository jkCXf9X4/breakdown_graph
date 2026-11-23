# Developing

This guide is for changing the tool itself. To use the tool, read
[`GETTING-STARTED.md`](GETTING-STARTED.md) first.

## Quick start

```sh
git clone https://github.com/jkCXf9X4/breakdown-tree
cd breakdown-tree
pip install -e '.[test]'
python3 -m pytest -q
bd audit
```

Requirements: Python 3.10+, PyYAML, pytest. Graphviz `dot` only for dot export.
Install once with `pip install -e '.[test]'` from the clone; without installing,
run from the repo root with `PYTHONPATH=src python3 -m bd_tree`.

## The data flow

```
.bd_tree/nodes/*.md
   │
   ├─ loader.load(root) ──────────────► Store   (every file, every edge)
   │                                      │
   │                                      └─ load_view(store, ref) ─► View
   │                                                                  │
   ├─ checker / navigate / freshness ◄───────────────────────────────┤
   ├─ exporter.tree|context|dot ◄────────────────────────────────────┤
   └─ work (symlinks) ◄──────────────────────────────────────────────┘
```

- `Store` is the full index: ref → node, all files, all edges, all issues.
  `Store.model` is `"graph"` or `"containment"`, detected once per store:
  containment when any node declares `contains`; otherwise graph when any node
  has `links`, `stage`, or a non-empty `layer`.
- `Store.children(ref)` and `Store.parents(ref)` are the topology seam:
  `effective_contains` in a containment store, forward `links` in a graph store.
  `Store.topology_roots()` returns containment roots or graph roots.
- `View` is one topology closure: the nodes reachable from a root ref over
  `Store.children`.
- Every read-only command works on a `View`; structural edits work on `Store`
  and write node files.

Validation is global; export and agent context are view-scoped. The default view
root is `ROOT`, else a graph store's lowest graph root, else a containment
store's lowest node by `(id, version)`; an explicit ref where a command takes one
wins, and `check --view` only narrows reporting. Reachability follows the
store's child relation (and, in containment, a shared logical id), so versions
of one id are one logical node. Data refs are full `id-version`; a bare id is a
CLI selector resolved inside the selected view (`current_ref(view, id)`).

## Module map

| Module | Responsibility |
| --- | --- |
| `loader.py` | Filename grammar, store scan, `ROOT`, topology view resolution (`_load_graph_view`), `current_ref`, citation edges |
| `model.py` | `Node`, `Store` (`model`, `children`, `parents`, `topology_roots`), `View`, `Edge`, `Issue`, `Link` |
| `graph.py` | Graph adjacency, band layout (`Graph.relative`, `band`, `band_label`), layer-order derivation, graph audit and export |
| `frontmatter.py` | Parse and rewrite front matter; body bytes are never re-serialised |
| `checker.py` | Structural checks; dispatches to the graph audit or containment checks, `--require`, size limits |
| `freshness.py` | Pins, stale edges, reconcile |
| `navigate.py` | `show`, `tree`, `find`, `path` renderers |
| `exporter.py` | `tree`, `context`, `dot` projections, path templates, and `section`/`name` placement |
| `work.py` | Single `<project>/bd_work/` area, `current`/`views`/`edit`, switching, `--status`, `--writeback`, git context |
| `solutions.py` | Thin `git worktree` lifecycle wrapper |
| `ops.py` | `init`, `new` (seeds empty `title`/`summary`), `contain`, `uncontain`, `link`, `unlink`, `clone`, `replace`, `delete`, `diff`, `migrate` |
| `api.py` | Public Python functions |
| `cli.py` | argparse wiring and output formatting |

Data comes from the store's `nodes/` directory (`.bd_tree/nodes/` in a project
layout); there are no hidden stores, caches, or state files. The one exception
is the store-level `ROOT` file: one ref on one line.

## Key types

```python
Node   id, version, ref, meta, contains, links, body, path
Store  root, nodes: dict[ref, Node], edges, issues, declared_root
       model -> "graph" | "containment"
       children(ref), parents(ref), topology_roots()
View   store, ref, nodes: dict[ref, Node], edges, issues
       model -> inherited from store
Edge   source, target, type, pinned, origin ("link" or "reference")
Issue  level, code, message, node, path
```

`Node.version` is always `>= 1`; `Node.ref` is the canonical `id-version` and
`node_path` always emits the suffix. In a containment store a node without
`contains` has no children; there is no inheritance from another version. In a
graph store children are the node's `links` targets. `bd clone` copies the
source file, so the new peer keeps its declared list; `bd clone --subtree` also
rewrites each cloned parent's child relation (`contains` or `links`), and
`bd replace OLD NEW` is the separate wiring step: it puts NEW at OLD's exact
index in its parent's `contains` (containment), repoints inbound links (graph),
or repoints `ROOT` when OLD is the store root, leaving OLD's file as a peer.

## Add a CLI command

1. Implement the operation in the right module.
   - read-only rendering → `navigate.py`
   - projection → `exporter.py`
   - file mutation → `ops.py` or `work.py`
2. Add a wrapper in `api.py`.
3. Add `_cmd_<name>` and a subparser in `cli.py`; call `set_defaults(func=...)`.
4. Add a test under `tests/`.
5. Update `README.md`, `docs/CHEATSHEET.md`, and `docs/DESIGN.md` if behaviour
   changed.

Skeleton:

```python
# navigate.py
def render_count(view: View) -> str:
    return f"{len(view.nodes)} nodes"

# api.py
def count(root, view="1-1") -> int:
    return len(_load_view(root, view).nodes)

# cli.py
def _cmd_count(args):
    print(f"{api.count(_find_root(args.root), args.view)} nodes")
    return 0

count = sub.add_parser("count", help="count nodes in a view")
_add_root(count)
count.add_argument("--view", default="1-1")
count.set_defaults(func=_cmd_count)
```

Test through a temporary store, not by mocking the loader.

## Add a topology-aware command

Dispatch on `Store.model` / `View.model`, never per node, and keep the child
relation behind `Store.children` / `Store.parents`:

1. Load with `load_view`, which already selects `contains` or forward links.
2. Put graph-only behaviour in `graph.py` (adjacency, band layout, audit,
   export); keep containment-only edits in `ops.py` and `work.py`.
3. In `navigate.py`, `render_tree` and `render_ls` show the pattern: a graph
   store renders through `graph.build_graph` / `graph_layout`; a containment
   store walks the declared tree.
4. A mode-aware command reads `Graph.relative`, `Graph.band`, `Graph.folders`,
   and `Graph.band_label`; build the plan through `build_graph` (which calls
   `_relative_plan` or `_absolute_plan`) instead of re-deriving band order.
   `Graph.band` is a top-level ordinal; nested bands and explicit subpaths are
   already resolved in `Graph.folders`. `band_prefix(graph)` is `layer` in
   relative mode, `stage` in absolute mode.
5. The audit split follows the plan: `audit` in `graph.py` extends
   `graph.issues` (the plan's layer/stage/order findings) and then runs the
   shared edge checks; absolute mode validates `stage`, relative mode skips it.
   Put mode-specific detection in the plan, shared rules in `audit`.
6. `bd contain` / `bd uncontain` must fail in a graph store with "graph stores use
   edges: bd link / bd unlink"; graph `bd link` must refuse a back-edge, a band
   cycle, or a same-band order back-edge, and keep
   targets sorted.
7. Test both topologies and both graph modes: the same temporary store shape,
   one with `contains`, one with `links` and relative `layer`s, one with `links`
   and `stage`.

## Add an exporter

Exporters are registered by decorator and share the CLI `export` group.

```python
@exporter("summary")
def export_summary(view: View, out: Path, **opts) -> ExportResult:
    _prepare_out(out, force=opts.get("force", False), clean=opts.get("clean", False))
    files = []
    for ref, node in sorted(view.nodes.items()):
        path = out / _default_path(node)
        path.write_text(render_document(node.meta, node.body), encoding="utf-8")
        files.append(path)
    return ExportResult("summary", out, len(view.nodes), files)
```

Rules:

- Take a `View`, never a root path. The graph exporter also accepts a `Graph`,
  but a `View` is the common seam.
- Return `ExportResult`.
- Preserve arbitrary front matter.
- Placement follows the topology. In a containment store, `_default_path` uses
  `section`: a `section` node opens a directory at its own placement name and
  its containment descendants inherit that prefix (nested sections stack);
  otherwise explicit `name` (`<name>.md`), then `<ref>-<title-slug>.md`, then
  `<ref>.md` when there is no usable title. `--path-template` opts out of
  section inheritance. In a graph store, place through the plan: a top-level
  band is `<NN>-<slug(band)>`, inferred nested bands and explicit layer
  subpaths are appended by `graph.folders`, and `group` is inert. In absolute
  mode `<NN>` is the stage and the label is the dominant layer. `folder` is not
  read.
- In a path template, `{name}`/`{slug}` is the explicit `name`, else the title
  slug, else the ref.
- Be deterministic; sort by `(id, version)` unless `contains` order is the point.
- Never write outside `out`.
- Add the name to the `export` subparser list and add a test.

## Add a structural edit

Structural edits change front matter, never prose.

- `parse_document(text)` keeps `opening`, `raw_fm`, `closing`, `body`.
- `rewrite_contains(raw_fm, refs)` and `rewrite_links(raw_fm, links)` replace only
  that block.
- `document.with_raw_fm(new_fm)` reconstructs the file with the body untouched.
- `render_document(meta, body)` is for new files or an intended full front-matter
  rewrite.

Checklist:

1. Load the store and resolve refs before writing; a bare CLI selector resolves
   through `current_ref(view, id)`, and every data write uses the full ref.
2. Refuse cycles, duplicates, and missing targets with `BreakdownError`. In a
   graph store, refuse a back-edge (`stage(source) < stage(target)` in absolute
   mode), a band cycle, or a same-band `order` back-edge (relative mode), and
   keep `links` sorted by ref.
3. Write the declared `contains` list directly; write `[]` when clearing. There
   is no inheritance to materialise. Graph edits rewrite only the source node's
   `links`.
4. Preserve body bytes and unrelated fields.
5. Test that the body is unchanged byte-for-byte, in both topologies.

## Testing

```sh
python3 -m pytest -q
```

- `tests/conftest.py` provides `write_node`, a helper that writes arbitrary front
  matter; placement uses the node's `section`/`name`/`title`.
- Use `tmp_path` and real files. Do not mock the loader.
- `test_examples.py` runs the graph example at `examples/` (store under
  `.bd_tree/`) through `bd audit`, graph traversal, and graph export, asserting
  twelve nodes, relative `layer`s and no `stage`, and no `contains`/`section`.
- `test_topology.py` covers detection, `children`/`parents`, forward closure, a
  multi-parent node appearing once, band layout, graph audit codes, and graph
  structural edits. `test_layers.py` covers the relative plan: derived band
  order, `graph-layer-missing`/`graph-layer-invalid`, `graph-layer-cycle`,
  `graph-order-back-edge`, and the `unlayered` rendering fallback.
  `test_layer_paths.py` covers the layout seam: path parsing, the shortest-path
  top-level rule, inferred nesting, explicit subpaths, disconnected and cyclic
  fallbacks, `group` inertness, absolute mode, and materialization through
  `bd work`/`bd edit`/exports. Keep its worked examples in step with
  [`GRAPH-LAYOUT.md`](GRAPH-LAYOUT.md).
- Root tests cover the precedence: explicit ref where a command takes one >
  `ROOT` > the topology's lowest root (graph root or containment
  `(id, version)`). They also cover `root-ref-missing`, `invalid-root`, and
  `check --view` narrowing only the report.
- Reachability tests assert all three containment paths: through `contains`,
  through another file with the same logical id, or through a link from a
  reachable node.
  Versions of one id are alternatives, so a non-selected version is not
  `unreachable`; a linked history view is not one either.
- Filename tests reject a bare `<id>.md`, version `0`, and leading zeros; data
  tests report `bare-ref` for a bare `contains`/`links`/`ROOT` entry,
  `invalid-ref` for malformed syntax, and `duplicate-id` when one view holds
  two versions of the same logical id.
- Link tests cover both forms: a mapping with its own `type`, and a scalar full
  ref whose type is read from the target node.
- Git tests create a temporary repository, set local `user.name`/`user.email`, and
  use `pytest.mark.skipif(shutil.which("git") is None, ...)`.
- Structural tests assert body bytes, not just field values.
- Keep the suite under a few seconds; no network.

Before a commit:

```sh
python3 -m pytest -q
bd check                         # examples: graph, 12 nodes
bd audit                         # graph audit
bd check --root docs/breakdown   # containment: 57 nodes
git diff --check
```

## Debugging

- `PYTHONPATH=src python3 -m bd_tree ...` is identical to `bd`.
- `BD_ROOT`/`--root` choose the store (default: nearest parent with `nodes/`,
  `.bd_tree/nodes/`, or a `.bd_root` pointer; else a unique store below cwd).
- `bd root` shows or switches the default view root; `bd root --clear` removes
  `ROOT`. It does not rewrite the work area.
- `bd views` lists topology roots (containment roots or graph roots) and
  marks the default; `bd current` reports the work area and the view actually in
  it.
- `bd check --view REF` narrows reporting to one closure; the default root is
  `ROOT`, else the topology's lowest root.
- `bd tree`, `bd show`, `bd path` quickly show what the loader sees. In a graph
  store `bd graph`, `bd out REF`, `bd in REF`, and `bd audit` show the forward
  edges and the audit.
- `bd show REF+N` caps each body at 4000 characters unless `--max-chars` is
  given; `--max-chars 0` prints full bodies. `bd tree --depth 0` is unlimited
  for both the outline and the `--columns` table.
- `bd find` defaults to the default view; `--regex` treats the query as a
  pattern, `--view REF` narrows, and `--all` searches the whole store. Output
  stays capped.
- `bd work --status` diagnoses symlink problems without touching the store and
  inspects the view actually in the area; `bd edit REF` resolves a ref inside
  that view.
- `pdb` works normally; the CLI is a thin argparse layer.

Common mistakes:

- Re-serialising the body through YAML. Never do it.
- Assuming `contains` is a set. In a containment store, order is data.
- Treating a containment store's `links` as membership. There it is a DAG and
  must not add view members; in a graph store it is the child relation.
- Hardcoding layer names or edge types. The tool is schema-agnostic.
- Writing a sidecar index. Derive it.
- Detecting topology per node. It is per store (`Store.model`).

## Invariants to protect

1. The store's `nodes/` directory (`.bd_tree/nodes/` in a project layout) is the
   only source of truth.
2. Filename is identity and version: every file is `<id>-<version>.md`, version
   >= 1; a bare `<id>.md` is invalid.
3. In a containment store, `contains` is an ordered tree per view and `links`
   is a DAG. In a graph store, `links` is the child relation: ordered by a
   relative `layer` path band (derived from cross-band edges) or an absolute
   `stage`, sorted, with derived in-edges.
4. Data refs are full `id-version`; a bare id is a CLI selector only.
5. Arbitrary front matter survives edits and exports.
6. Body bytes survive structural edits.
7. No JSON/TOML/lock/state data files; the only pointers are the store-level
   `ROOT`, one full ref on one line, and the folder-level `.bd_root`, one store
   path on one line. The transient write lock lives outside the store.
8. A view never crosses a branch, and neither does a version; solutions are git
   worktrees. In a containment store, a parent's `contains` names the version
   current in that view; in a graph store, an edge pins a full ref.
9. Generated files are disposable and never committed.
10. A project has exactly one writable work area, `<project>/bd_work/`, holding
    one view at a time. Its view changes only with `bd work`, not with `bd root`.
    Read-only exports never become a second work area.
11. Topology is detected per store, never per node: graph when no node declares
    `contains` and at least one declares `links`; containment otherwise.

## Style and commits

- Python 3.10, type hints, dataclasses, small modules.
- Standard library plus PyYAML. No new dependency without a clear reason.
- CLI uses argparse.
- Structural errors raise `BreakdownError`; checks return `Issue`.
- Commit prefixes: `feat:`, `fix:`, `chore:`, `docs:`. One concern per commit.

## Docs

The repo is documentation-driven. When behaviour changes:

- `README.md` — front door and command map.
- `docs/GETTING-STARTED.md` — user tutorial.
- `docs/CHEATSHEET.md` — command reference.
- `docs/DESIGN.md` — model, decisions, invariants.
- `docs/GRAPH.md` — graph topology, relative and absolute bands, audit, export,
  and dispatch.
- `docs/GRAPH-LAYOUT.md` — the layer-path layout algorithm, tie-breaks, worked
  examples, diagnostics, command map, and test map.
- `docs/BRANCHES-AND-VERSIONS.md` — branch/version separation contract.
- `AGENTS.md` — operating rules for agents.

Keep examples executable. Run them before committing.

## Not built yet

- No CI or generic importer. `bd migrate` only converts a classic bare-file
  store in place. Packaging is `pyproject.toml` plus the `bd` console script.
- No three-way node merge; solutions merge with git.
- Writes to one store serialize on an advisory lock outside the store
  (`src/bd_tree/fsutil.py`); readers take none, because writers publish
  atomically.
- No Windows-specific symlink path.
