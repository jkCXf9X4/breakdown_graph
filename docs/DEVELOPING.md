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
   ├─ exporter.graph|context|dot ◄───────────────────────────────────┤
   └─ work (symlinks) ◄──────────────────────────────────────────────┘
```

- `Store` is the full index: ref → node, all files, all edges, all issues.
  There is one topology. `Store.model` may remain as a property for internal
  compatibility, but it always returns `"graph"`; do not add a second branch.
- `Store.children(ref)` and `Store.parents(ref)` are the structural seam:
  authored non-symmetric `links` and their reverse. `Store.structural_links(ref)`
  is the authored subset; `Store.derived_links(ref)` computes opposite edges
  from other nodes' symmetric masters (`origin="derived"`, never stored).
  `Store.topology_roots()` returns graph roots over structural links.
- `Store.node_edges(ref, include_derived=False)` keeps authored behaviour by
  default; `include_derived=True` appends derived opposites.
- `View` is one closure: the nodes reachable from a root ref over
  `Store.children` (structural links only).
- Every read-only command works on a `View`; structural edits work on `Store`
  and write node files.
- Symmetric links are one authored master per pair. The loader validates
  `symmetric` (bool) and `inverse` (non-empty string, requires `symmetric`) and
  the opposite is derived at load. Never write a derived opposite to a file.

Validation is global; export and agent context are view-scoped. The default view
root is `ROOT`, else the lowest graph root; an explicit ref where a command
takes one wins, and `check --view` only narrows reporting. Data refs are full
`id-version`; a bare id is a CLI selector resolved inside the selected view
(`current_ref(view, id)`).

A node that still declares `contains` is not parsed as another topology. The
loader/checker surface it as `contains-removed`, and `bd migrate` is the only
conversion path.

## Module map

| Module | Responsibility |
| --- | --- |
| `loader.py` | Filename grammar, store scan, `ROOT`, view resolution (`_load_graph_view`), `current_ref`, citation edges |
| `model.py` | `Node`, `Store` (`children`, `parents`, `topology_roots`), `View`, `Edge`, `Issue`, `Link` |
| `graph.py` | Adjacency, band layout (`Graph.relative`, `band`, `band_label`), band-order derivation, graph audit and export |
| `frontmatter.py` | Parse and rewrite front matter; body bytes are never re-serialised |
| `checker.py` | Structural checks, including `contains-removed`, `--require`, size limits |
| `freshness.py` | Pins, stale edges, reconcile |
| `navigate.py` | `show`, `find`, `path` renderers |
| `exporter.py` | `graph`, `context`, `dot` projections and path templates |
| `work.py` | Single `<project>/bd_work/` area, `current`/`views`/`edit`, switching, `--status`, `--writeback`, git context |
| `solutions.py` | Thin `git worktree` lifecycle wrapper |
| `ops.py` | `init`, `new` (seeds empty `title`/`summary`), `link`, `unlink`, `clone`, `replace`, `delete`, `diff`, `migrate` |
| `api.py` | Public Python functions |
| `cli.py` | argparse wiring and output formatting |

Data comes from the store's `nodes/` directory (`.bd_tree/nodes/` in a project
layout); there are no hidden stores, caches, or state files. The one exception
is the store-level `ROOT` file: one ref on one line.

## Key types

```python
Node   id, version, ref, meta, links, body, path
Store  root, nodes: dict[ref, Node], edges, issues, declared_root
       model -> "graph"
       children(ref), parents(ref), structural_links(ref), derived_links(ref),
       topology_roots()
View   store, ref, nodes: dict[ref, Node], edges, issues
Link   to, type, pinned, propagates, symmetric, inverse, raw
Edge   source, target, type, pinned, symmetric,
       origin ("link" | "derived" | "reference")
Issue  level, code, message, node, path
```

`Node.version` is always `>= 1`; `Node.ref` is the canonical `id-version` and
`node_path` always emits the suffix. Children are the node's structural `links`
targets; a symmetric master is shown as an out-edge but does not add a child.
`bd clone` copies the source file, so the new peer keeps its declared `links`;
`bd clone --subtree` also rewrites each cloned parent's `links`, and
`bd replace OLD NEW` is the separate wiring step: it repoints inbound links, or
repoints `ROOT` when OLD is the store root, leaving OLD's file as a peer.

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

## Add a band-aware command

There is one topology but two band modes. Read the mode from the plan, never
per node:

1. Load with `load_view`, which resolves forward structural links.
2. Put adjacency, band layout, audit, and graph export in `graph.py`.
3. In `navigate.py`, `bd graph` renders through `graph.build_graph` /
   `graph_layout`; there is no `bd tree` and no second child relation.
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
6. `bd link` must refuse a back-edge, a band cycle, or a same-band order
   back-edge, and keep targets sorted. A `--symmetric` link skips those ordering
   checks, is never structural, and cannot carry `propagates`.
7. Test both band modes: the same temporary store shape, one with `links` and
   relative `band`s, one with `links` and `stage`.

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
- Placement is the band plan: a top-level band is `<NN>-<slug(band)>`; inferred
  nested bands and explicit `subpath`s are appended by `graph.folders`. In
  absolute mode `<NN>` is the stage and the label is the dominant band/layer
  label. `section`, `group`, and `folder` are never read. The file stem is an
  explicit `name`, else `<ref>-<title-slug>.md`, else `<ref>.md`.
- In a path template, `{name}`/`{slug}` is the explicit `name`, else the title
  slug, else the ref.
- Be deterministic; sort by `(id, version)`.
- Never write outside `out`.
- Add the name to the `export` subparser list and add a test.

## Add a structural edit

Structural edits change front matter, never prose.

- `parse_document(text)` keeps `opening`, `raw_fm`, `closing`, `body`.
- `rewrite_links(raw_fm, links)` replaces only that block.
- `document.with_raw_fm(new_fm)` reconstructs the file with the body untouched.
- `render_document(meta, body)` is for new files or an intended full front-matter
  rewrite.

Checklist:

1. Load the store and resolve refs before writing; a bare CLI selector resolves
   through `current_ref(view, id)`, and every data write uses the full ref.
2. Refuse cycles, duplicates, and missing targets with `BreakdownError`. Refuse
   a back-edge (`stage(source) < stage(target)` in absolute mode), a band cycle,
   or a same-band `order` back-edge (relative mode), and keep `links` sorted by
   ref.
3. Graph edits rewrite only the source node's `links`. There is no `contains`
   list to write, and `migrate` is the only place that reads one.
4. Preserve every link key, including `symmetric` and `inverse`; a symmetric
   master is authored once and `unlink` removes it. `rewrite_links` formatting
   must not drop unknown link keys.
5. Preserve body bytes and unrelated fields.
6. Test that the body is unchanged byte-for-byte.

## Testing

```sh
python3 -m pytest -q
```

- `tests/conftest.py` provides `write_node`, a helper that writes arbitrary front
  matter.
- Use `tmp_path` and real files. Do not mock the loader.
- `test_examples.py` runs the example at `examples/` (store under `.bd_tree/`)
  through `bd audit`, graph traversal, and graph export, asserting twelve nodes,
  relative `band`/`subpath` values and no `stage`, and no `contains`/`section`.
- `test_topology.py` covers forward closure, a multi-parent node appearing once,
  band layout, graph audit codes, and graph structural edits. `test_layers.py`
  covers the relative plan: derived band order,
  `graph-layer-missing`/`graph-layer-invalid`, `graph-layer-cycle`,
  `graph-order-back-edge`, and the `unlayered` rendering fallback.
  `test_layer_paths.py` covers the layout seam: band/subpath parsing, the
  shortest-path top-level rule, inferred nesting, explicit subpaths,
  disconnected and cyclic fallbacks, `group` inertness, absolute mode, and
  materialization through `bd work`/`bd edit`/exports. Keep its worked examples
  in step with [`GRAPH-LAYOUT.md`](GRAPH-LAYOUT.md).
- `test_symmetric.py` covers the master/derived model: parsing and extra link
  keys, loader issues, a derived opposite that is shown but never structural,
  the `inverse` fallback to the master type, and `out`/`in` `[derived]` marking.
  `test_check.py` pins the five symmetric checker codes and `invalid-band-order`;
  `test_graph.py` pins `band_order` tie-breaking and that a symmetric link does
  not order bands.
- Root tests cover the precedence: explicit ref where a command takes one >
  `ROOT` > the lowest graph root. They also cover `root-ref-missing`,
  `invalid-root`, and `check --view` narrowing only the report.
- Reachability tests assert every node is reachable from a graph root through
  forward structural links; an unreached root warns `graph-orphan`.
- Filename tests reject a bare `<id>.md`, version `0`, and leading zeros; data
  tests report `bare-ref` for a bare `links`/`ROOT` entry and `invalid-ref` for
  malformed syntax.
- `contains-removed` tests declare `contains` and assert `bd check` fails with a
  message pointing at `bd migrate`.
- Migration tests convert `contains` to ordered `links`, add `order: i` where
  missing, map `section` to `band`/`subpath`, and assert the migrated store
  checks clean.
- Git tests create a temporary repository, set local `user.name`/`user.email`, and
  use `pytest.mark.skipif(shutil.which("git") is None, ...)`.
- Structural tests assert body bytes, not just field values.
- Keep the suite under a few seconds; no network.

Before a commit:

```sh
python3 -m pytest -q
bd check                         # examples: 12 nodes
bd audit                         # explicit graph audit
git diff --check
```

## Debugging

- `PYTHONPATH=src python3 -m bd_tree ...` is identical to `bd`.
- `BD_ROOT`/`--root` choose the store (default: nearest parent with `nodes/`,
  `.bd_tree/nodes/`, or a `.bd_root` pointer; else a unique store below cwd).
- `bd root` shows or switches the default view root; `bd root --clear` removes
  `ROOT`. It does not rewrite the work area.
- `bd views` lists graph roots and marks the default; `bd current` reports the
  work area and the view actually in it.
- `bd check --view REF` narrows reporting to one closure; the default root is
  `ROOT`, else the lowest graph root.
- `bd graph`, `bd show`, `bd path`, `bd out REF`, `bd in REF`, and `bd audit`
  quickly show what the loader sees.
- `bd show REF+N` caps each body at 4000 characters unless `--max-chars` is
  given; `--max-chars 0` prints full bodies.
- `bd find` defaults to the default view; `--regex` treats the query as a
  pattern, `--view REF` narrows, and `--all` searches the whole store. Output
  stays capped.
- `bd work --status` diagnoses symlink problems without touching the store and
  inspects the view actually in the area; `bd edit REF` resolves a ref inside
  that view.
- `pdb` works normally; the CLI is a thin argparse layer.

Common mistakes:

- Re-serialising the body through YAML. Never do it.
- Adding a `contains` branch. One topology: convert with `migrate`, reject with
  `contains-removed`.
- Treating `section` or `group` as placement. Bands are the only layout.
- Hardcoding layer names or edge types. The tool is schema-agnostic.
- Writing a sidecar index. Derive it.
- Detecting band mode per node. It is per store (`Graph.relative`).

## Invariants to protect

1. The store's `nodes/` directory (`.bd_tree/nodes/` in a project layout) is the
   only source of truth.
2. Filename is identity and version: every file is `<id>-<version>.md`, version
   >= 1; a bare `<id>.md` is invalid.
3. Structural `links` are the child relation: ordered by a relative band
   (derived from cross-band structural edges) or an absolute `stage`, sorted by
   ref, with derived in-edges. Multiple parents are legal. A symmetric link is
   associative: one authored master, opposite derived, never structural.
4. Data refs are full `id-version`; a bare id is a CLI selector only.
5. Arbitrary front matter survives edits and exports.
6. Body bytes survive structural edits.
7. No JSON/TOML/lock/state data files; the only pointers are the store-level
   `ROOT`, one full ref on one line, and the folder-level `.bd_root`, one store
   path on one line. The transient write lock lives outside the store.
8. A view never crosses a branch, and neither does a version; solutions are git
   worktrees. An edge pins a full ref.
9. Generated files are disposable and never committed.
10. A project has exactly one writable work area, `<project>/bd_work/`, holding
    one view at a time. Its view changes only with `bd work`, not with `bd root`.
    Read-only exports never become a second work area.
11. One topology. `contains` is not data: a node declaring it is an error
    (`contains-removed`) until `bd migrate` converts it.

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
- `docs/DESIGN.md` — model, decisions, invariants, migration.
- `docs/GRAPH.md` — the one topology: typed structural and symmetric links,
  relative and absolute bands, audit, export.
- `docs/GRAPH-LAYOUT.md` — the band/subpath layout algorithm (including the
  `band_order` hint), tie-breaks, worked examples, diagnostics, command map, and
  test map.
- `docs/BRANCHES-AND-VERSIONS.md` — branch/version separation contract.
- `AGENTS.md` — operating rules for agents.

Keep examples executable. Run them before committing.

## Not built yet

- No CI or generic importer. `bd migrate` converts a classic bare-file store and
  a containment store in place. Packaging is `pyproject.toml` plus the `bd`
  console script.
- No three-way node merge; solutions merge with git.
- Writes to one store serialize on an advisory lock outside the store
  (`src/bd_tree/fsutil.py`); readers take none, because writers publish
  atomically.
- No Windows-specific symlink path.
