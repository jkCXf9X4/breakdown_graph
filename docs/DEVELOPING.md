# Developing

This guide is for changing the tool itself. To use the tool, read
[`GETTING-STARTED.md`](GETTING-STARTED.md) first.

## Quick start

```sh
git clone https://github.com/jkCXf9X4/breakdown-tree
cd breakdown-tree
pip install -e '.[test]'
python3 -m pytest -q
bd check
```

Requirements: Python 3.10+, PyYAML, pytest. Graphviz `dot` only for graph
rendering.
Install once with `pip install -e '.[test]'` from the clone; without installing,
run from the repo root with `PYTHONPATH=src python3 -m bd_tree`.

## The data flow

```
.bd_tree/nodes/*.md
   │
   ├─ loader.load(root) ──────────────► Store   (every file, every edge)
   │                                      │
   │                                      ├─ Store.components() / neighbors()
   │                                      │
   │                                      └─ load_view(store, ref) ─► View
   │                                                                  │
   ├─ checker / navigate / freshness ◄───────────────────────────────┤
   ├─ exporter (pack) ◄──────────────────────────────────────────────┤
   └─ work (flat symlinks) ◄─────────────────────────────────────────┘
```

- `Store` is the full index: ref → node, all files, all edges, all issues.
  There is one topology. `Store.model` remains as a property for internal
  compatibility, but it always returns `"graph"`; do not add a second branch.
- `Store.neighbors(ref)` is the undirected seam: authored tokens in both
  directions, one entry per neighbour ref, each with a `kind` (`child` or
  `parent`) and the representative authored `Link`.
- `Store.components()` returns every weak component, members sorted by
  `(id, version)`. `Store.topology_roots()` returns one representative per
  component: its lowest member. The name is historical; a cycle no longer
  produces "no roots".
- `Store.children(ref)` and `Store.parents(ref)` keep the authored direction.
  `Store.structural_links(ref)` keeps its historical name but returns every
  authored link; there is no `derived_links`.
- `graph.build_graph` builds `out` from authored tokens and `inn` by reversing
  them; the reversed entries are display-only and are never stored.
- `Store.node_edges(ref)` and `View.node_edges(ref)` return authored out-edges;
  `graph.build_graph(...).inn` is the reversed list that `bd in` renders.
- `View` is one component: every member once, plus `distance`, the undirected
  BFS hop count from the view ref. `View.edges` holds authored links whose two
  ends are both in the component; reversed in-edges never enter.
- Every read-only command works on a `View` or the anchored `Graph`; structural
  edits work on `Store` and write node files.
- Link declaration is body-owned: `inline.scan_inline_links` reads
  `(TITLE)[[REF, TYPE]]` tokens, ignoring fenced code, inline code, and `\[[`;
  the title is an optional prefix, and a bare token is valid. The scanner
  reports `inline-title-missing` for a bare token. `inline.append_token` /
  `remove_token` / `repoint_token` maintain the trailing `## Links` section;
  `retitle_tokens` rewrites the cached title. The cache is tool-generated from
  the target's live title; rendering reads the live title, `checker` reports
  `link-title-stale`, and `ops.retitle` drives the store-wide rewrite.

Validation is global; pack and agent context are view-scoped. The default
anchor is `ROOT`, else the lowest member of the first component; an explicit ref
where a command takes one wins, and `check --view` only narrows reporting. Data
refs are full `id-version`; a bare id is a CLI selector resolved inside the
selected view (`current_ref(view, id)`).

A node that still declares `contains` is not parsed as another topology. The
loader/checker surface it as `contains-removed`, and `bd migrate` is the only
conversion path.

## Module map

| Module | Responsibility |
| --- | --- |
| `loader.py` | Filename grammar, store scan, `ROOT`, component view (`_load_graph_view`), `current_ref` |
| `model.py` | `Node`, `Store` (`neighbors`, `components`, `children`, `parents`, `topology_roots`), `View` (with `distance`), `Neighbor`, `Edge`, `Issue`, `Link` |
| `graph.py` | Adjacency, `ring_distances`, `graph_view`, ring rendering, graph checks, flat pack paths |
| `frontmatter.py` | Parse and rewrite front matter; body bytes are never re-serialised |
| `checker.py` | Structural checks, including `contains-removed`, `--require`, size limits |
| `freshness.py` | Pins, stale edges, pin repair |
| `navigate.py` | `show`, `find`, `path` renderers over undirected neighbours |
| `exporter.py` | Pack projections (graph and fresh context), flat paths, path templates |
| `work.py` | Single flat `<project>/bd_work/` area, `current`/`views`/`edit`, switching, `--status`, `--repair`, git context |
| `solutions.py` | Thin `git worktree` lifecycle wrapper |
| `ops.py` | `init`, `new` (seeds empty `title`/`summary`), `link`, `unlink`, `clone`, `replace`, `delete`, `diff`, `migrate`, `retitle` |
| `api.py` | Public Python functions |
| `cli.py` | argparse wiring and output formatting |

Data comes from the store's `nodes/` directory (`.bd_tree/nodes/` in a project
layout); there are no hidden stores, caches, or state files. The one exception
is the store-level `ROOT` file: one ref on one line. The work-area view is read
from the generated `REFS.md`, not from extra state.

## Key types

```python
Node    id, version, ref, meta, links, body, path
Store   root, nodes: dict[ref, Node], issues, declared_root
        model -> "graph"
        neighbors(ref), components(), children(ref), parents(ref),
        structural_links(ref), topology_roots()
Neighbor ref, kind ("child" | "parent"), link
View    store, ref, nodes: dict[ref, Node], edges, issues,
        distance: dict[ref, int]
Link    to, type, pinned, propagates, raw
Edge    source, target, type, pinned, propagates, origin ("authored")
Issue   level, code, message, node, path
```

`Node.version` is always `>= 1`; `Node.ref` is the canonical `id-version` and
`node_path` always emits the suffix. `Link.raw` is the token text that declared
the edge; a node's `pinned`/`propagates` values come from its `freshness:` map.
`bd clone` copies the source file, so the clone keeps its tokens; `bd clone
--subtree` also rewrites cloned token refs, and `bd replace OLD NEW` is the
separate wiring step: it repoints inbound tokens, or repoints `ROOT` when OLD is
the store root, leaving OLD's file as a peer.

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

## Add a ring-aware command

There is one topology and one order: undirected BFS distance from the anchor.

1. Load with `load_view(store, anchor)` when the whole component is enough, or
   `build_graph(store, anchor=...)` when you need `distance`, `components`, or
   `roots`.
2. Read order from `Graph.distance` and the documented tie-break
   `(distance, kind_rank, link type, id, version)`. Do not re-walk neighbours
   independently; a second walk can disagree on a cycle.
3. Put adjacency, rings, checks, and flat pack paths in `graph.py`. In
   `navigate.py`, render through `render_show`, `render_path`, or
   `walk_neighbors`; there is no `bd tree` and no second child relation.
4. If the command materializes files, reuse `graph.layout_paths` and
   `exporter._ring_layout` rather than constructing names; the work area is
   flat and uses store basenames.
5. If it filters, decide explicitly whether the filter stops traversal
   (`--depth`) or only hides output (`--rings`). A display filter keeps
   walking through hidden nodes.
6. Direction is a label. A new renderer may show `→`/`←`, but must not use
   direction to include or exclude a node unless the command is explicitly
   directional (`bd out`, `bd in`).
7. Add a temporary-store test with the smallest graph that distinguishes the new
   rule; include a cycle and a reciprocal pair where relevant.

## Add a pack projection

`bd pack` materializes a view through a function in `exporter.py`: `api.pack`
calls the default graph projection, or the fresh-context projection with
`--fresh`. A new mode is a new function plus a branch in `api.pack` and a CLI
option.

```python
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

- Take a `View`, never a root path. The graph projection also accepts a `Graph`,
  but a `View` is the common seam.
- Return `ExportResult`.
- Preserve arbitrary front matter.
- Paths are flat: each node uses the store file's basename. There are no node
  directories. `graph.layout_paths` handles the collision suffix.
- In a path template, placeholders are `{ref}`, `{id}`, `{version}`,
  `{distance}`, `{slug}`, `{title}`, plus any front-matter key. `{slug}` is the
  title slug, else the ref.
- Be deterministic; sort by `(distance, id, version)` where the view matters,
  and by `(id, version)` otherwise.
- Never write outside `out`.
- Wire the new mode into `bd pack` and add a test.

## Add a structural edit

Structural edits change body tokens and freshness front matter, not prose.

- `parse_document(text)` keeps `opening`, `raw_fm`, `closing`, `body`.
- `inline.append_token` / `remove_token` / `repoint_token` maintain the trailing
  `## Links` section and leave every other body byte alone. `retitle_tokens`
  rewrites the cached title prefix in place; `ops.retitle` is the store-wide
  driver behind `bd retitle`.
- `rewrite_freshness(raw_fm, freshness)` replaces only the `freshness:` map.
- `document.with_raw_fm(new_fm)` reconstructs the file with the body untouched.
- `render_document(meta, body)` is for new files or an intended full front-matter
  rewrite.

Checklist:

1. Load the store and resolve refs before writing; a bare CLI selector resolves
   through `current_ref(view, id)`, and every data write uses the full ref.
2. Refuse duplicate edges and missing targets with `BreakdownError`. A
   self-loop on one ref is refused; back-edges, reciprocal edges, and cycles are
   accepted. Keep a `## Links` section in ascending target-ref order;
   `append_token` appends in call order, so monotone calls preserve it.
3. A graph edit appends or removes token lines in the source node only. There is
   no `contains` list or front-matter `links` list to write; `migrate` is the
   only place that reads them.
4. Preserve every token and title cache byte you are not deliberately touching;
   `append_token` is a no-op for an identical line, `remove_token` deletes the
   section when it becomes empty, and a title change belongs in `bd retitle`
   or `retitle_tokens`, never in hand-written prose.
5. Preserve unrelated front matter and the body outside the edited section.
6. Test that all other body bytes are unchanged.

## Testing

```sh
python3 -m pytest -q
```

- `tests/conftest.py` provides `write_node`, a helper that writes arbitrary front
  matter.
- Use `tmp_path` and real files. Do not mock the loader.
- `test_view.py` covers component membership, `distance`, multi-parent nodes,
  cycles loading once, `neighbors` kinds, and `components`.
- `test_navigate.py` covers `show` rings and arrows, `path` shortest chains,
  `find` scoping, `view_roots`, and the CLI wrappers.
- `test_graph.py` covers `ring_distances`, cycle distance, reciprocal pairs,
  dangling links, `--type`/`--rings`/`--depth`, flat `layout_paths` and
  templates, ring headings, DOT, check warnings, and flat pack output.
- `test_topology.py` covers the graph model, component roots, graph view,
  `show`/`path`/`find`, and that cycles and back-edges check clean.
- `test_work.py` covers flat symlinks, generated `INDEX.md`/`REFS.md`, ring
  grouping, a cycle appearing once, status/repair, and the single area.
- `test_export.py`, `test_dot_render.py`, and `test_visual.py` cover the
  read-only projections and rendering.
- `test_examples.py` runs the example at `examples/` (store under `.bd_tree/`)
  through check, graph traversal, and flat packing, asserting twelve nodes, one
  component, and a clean store.
- `test_refs.py` covers the filename/ref grammar: full refs, selectors, and
  invalid forms.
- `test_inline.py` covers the token grammar, the prefix title, fences/code
  spans/escapes, duplicate and missing-title warnings, stale-title comparison,
  `retitle`, the `## Links` writers, and the hash stripping that keeps token
  edits from invalidating a pin.
- Root tests cover the precedence: explicit ref where a command takes one >
  `ROOT` > the lowest component member. They also cover `root-ref-missing`,
  `invalid-root`, and `check --view` narrowing only the report.
- `contains-removed` tests declare `contains` and assert `bd check` fails with a
  message pointing at `bd migrate`.
- Migration tests convert `contains` and front-matter `links` to sorted body
  tokens, rewrite legacy suffix tokens to the prefix form, fill missing titles,
  move per-link freshness into the `freshness:` map, strip retired placement
  keys, and assert the migrated store checks clean. `retitle` tests cover the
  store and view scopes, unresolved targets, and `--dry-run`.
- Git tests create a temporary repository, set local `user.name`/`user.email`, and
  use `pytest.mark.skipif(shutil.which("git") is None, ...)`.
- Structural tests assert body bytes, not just field values.
- Keep the suite under a few seconds; no network.

Before a commit:

```sh
python3 -m pytest -q
bd check                         # examples: 12 nodes
bd stale                         # stale or untracked propagating edges
bd work 1-1                      # flat work area, 12 symlinks
git diff --check
```

## Debugging

- `PYTHONPATH=src python3 -m bd_tree ...` is identical to `bd`.
- `BD_ROOT`/`--root` choose the store (default: nearest parent with `nodes/`,
  `.bd_tree/nodes/`, or a `.bd_root` pointer; else a unique store below cwd).
- `bd root` shows or switches the default anchor; `bd root --clear` removes
  `ROOT`. It does not rewrite the work area.
- `bd views` lists components and marks the default and the work-area anchor;
  `bd current` reports the work area and the view actually in it.
- `bd check --view REF` narrows reporting to one component; the default anchor is
  `ROOT`, else the lowest component member.
- `bd graph`, `bd show`, `bd path`, `bd out REF`, `bd in REF`, and `bd check`
  quickly show what the loader sees. `bd graph 1-1 --rings A:B` shows one
  ring window while still traversing through the rest.
- `bd show REF+N` caps each body at 4000 characters unless `--max-chars` is
  given; `--max-chars 0` prints full bodies.
- `bd find` defaults to the anchor's component; `--regex` treats the query as a
  pattern, `--view REF` narrows, and `--all` searches the whole store. Output
  stays capped.
- `bd current --status` diagnoses symlink problems without touching the store
  and inspects the view actually in the area; `bd edit REF` resolves a ref
  inside that view.
- `pdb` works normally; the CLI is a thin argparse layer.

Common mistakes:

- Re-serialising the body through YAML. Never do it.
- Adding a `contains` branch. One topology: convert with `migrate`, reject with
  `contains-removed`.
- Re-introducing an authored placement key. Ordering is BFS distance.
- Treating a `child`/`parent` label as membership. Membership is the whole weak
  component.
- Applying a display filter to traversal. `--rings` hides output only.
- Hardcoding layer names or edge types. The tool is schema-agnostic.
- Writing a sidecar index or a state file. Derive it; the work-area view lives
  in `REFS.md`.

## Invariants to protect

1. The store's `nodes/` directory (`.bd_tree/nodes/` in a project layout) is the
   only source of truth.
2. Filename is identity and version: every file is `<id>-<version>.md`, version
   >= 1; a bare `<id>.md` is invalid.
3. A view is the weakly connected component of its anchor over authored links.
   Membership is undirected; a node appears once at its minimum BFS distance.
4. Direction is a label: `child` or `parent`. It orders ring 1 but never
   filters membership.
5. Cycles, back-edges, and reciprocal pairs are legal; a self-loop on one ref is
   refused by `bd link`.
6. Body tokens are typed and kept in target-ref order; in-edges are derived by
   reversing them. Multiple parents are legal, and every node authors its own
   back-reference. No derived opposite exists.
7. Data refs are full `id-version`; a bare id is a CLI selector only.
8. No placement key exists. `group`, `section`, `folder`, and `home` are inert.
9. Arbitrary front matter survives edits and projections.
10. Body bytes survive structural edits, except the token lines in `## Links`.
11. No JSON/TOML/lock/state data files; the only pointers are the store-level
    `ROOT`, one full ref on one line, and the folder-level `.bd_root`, one store
    path on one line. The work-area view is in `REFS.md`. The transient write
    lock lives outside the store.
12. A view never crosses a branch, and neither does a version; solutions are git
    worktrees. An edge pins a full ref.
13. Generated files are disposable and never committed.
14. A project has exactly one writable work area, `<project>/bd_work/`, holding
    one view at a time. It is flat. Its view changes only with `bd work`, not
    with `bd root`. Read-only projections never become a second work area.
15. One topology. `contains` is not data: a node declaring it is an error
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
- `docs/GRAPH.md` — the one topology: typed body tokens, undirected views,
  rings, checks, packing.
- `docs/GRAPH-LAYOUT.md` — component membership, BFS rings, tie-breaks, the flat
  work area, worked examples, diagnostics, command map, and test map.
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
