# Developing

This guide is for changing the tool itself. To use the tool, read
[`GETTING-STARTED.md`](GETTING-STARTED.md) first.

## Quick start

```sh
git clone https://github.com/jkCXf9X4/breakdown-tree
cd breakdown-tree
pip install -e '.[test]'
python3 -m pytest -q
BD_ROOT=examples bd check
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
   ├─ exporter.context|dot, view tree ◄──────────────────────────────┤
   └─ work (symlinks) ◄──────────────────────────────────────────────┘
```

- `Store` is the full index: ref → node, all files, all edges, all issues.
- `View` is one containment closure: the nodes reachable from a root ref.
- Every read-only command works on a `View`; structural edits work on `Store`
  and write node files.

Validation is global; export and agent context are view-scoped. The default view
root is `ROOT`, else the lowest main ref; an explicit ref or `--root-ref` wins.
Reachability follows `contains` or a shared id, so main and its versions are one
logical node.

## Module map

| Module | Responsibility |
| --- | --- |
| `loader.py` | Filename grammar, store scan, `ROOT`, view resolution, citation edges |
| `model.py` | `Node`, `Store`, `View`, `Edge`, `Issue`, `Link` |
| `frontmatter.py` | Parse and rewrite front matter; body bytes are never re-serialised |
| `checker.py` | Structural checks, per-view tree checks, `--require`, size limits |
| `freshness.py` | Pins, stale edges, reconcile |
| `navigate.py` | `show`, `tree`, `ls`, `find`, `grep`, `path` renderers |
| `exporter.py` | `context`, `dot` projections, path templates, and `home`/`folder`/`name` resolution; `bd view` renders the tree |
| `work.py` | Single `<project>/bd_work/` area, `current`/`views`/`edit`, switching, `--status`, `--writeback`, git context |
| `solutions.py` | Thin `git worktree` lifecycle wrapper |
| `ops.py` | `init`, `new` (derives `folder`), `contain`, `uncontain`, `link`, `unlink`, versions, `diff` |
| `api.py` | Public Python functions |
| `cli.py` | argparse wiring and output formatting |

Data comes from the store's `nodes/` directory (`.bd_tree/nodes/` in a project
layout); there are no hidden stores, caches, or state files. The one exception
is the store-level `ROOT` file: one ref on one line.

## Key types

```python
Node   id, version, ref, meta, contains, links, body, path
Store  root, nodes: dict[ref, Node], edges, issues, declared_root
View   store, ref, nodes: dict[ref, Node], edges, issues
Edge   source, target, type, pinned, origin ("link" or "reference")
Issue  level, code, message, node, path
```

`Node.meta` is the raw front matter; arbitrary fields live there and survive
export. `contains is None` means "inherit the main version's list"; `[]` means
"no children". `bd fork` materialises the effective list into the version; the
loader inheritance rule is unchanged, so a hand-written version that omits
`contains` still follows main.

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
def count(root, view="1") -> int:
    return len(_load_view(root, view).nodes)

# cli.py
def _cmd_count(args):
    print(f"{api.count(_find_root(args.root), args.view)} nodes")
    return 0

count = sub.add_parser("count", help="count nodes in a view")
_add_root(count)
count.add_argument("--view", default="1")
count.set_defaults(func=_cmd_count)
```

Test through a temporary store, not by mocking the loader.

## Add an exporter

Exporters are registered by decorator and share the CLI `export` group.

```python
@exporter("summary")
def export_summary(view: View, out: Path, **opts) -> ExportResult:
    _prepare_out(out, force=opts.get("force", False), clean=opts.get("clean", False))
    files = []
    for ref, node in sorted(view.nodes.items()):
        path = out / f"{ref}.md"
        path.write_text(render_document(node.meta, node.body), encoding="utf-8")
        files.append(path)
    return ExportResult("summary", out, len(view.nodes), files)
```

Rules:

- Take a `View`, never a root path.
- Return `ExportResult`.
- Preserve arbitrary front matter.
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

1. Load the store and resolve refs before writing.
2. Refuse cycles, duplicates, and missing targets with `BreakdownError`.
3. Materialise inherited `contains` before editing; write `[]` when clearing.
4. Preserve body bytes and unrelated fields.
5. Test that the body is unchanged byte-for-byte.

## Testing

```sh
python3 -m pytest -q
```

- `tests/conftest.py` provides `write_node`, a helper that writes arbitrary front
  matter and derives `home` from `layer`.
- Use `tmp_path` and real files. Do not mock the loader.
- `test_examples.py` runs the project at `examples/` (store under `.bd_tree/`)
  through `bd check` and view loading, asserting both complete trees.
- Root tests cover the precedence: explicit ref or `--root-ref` > `ROOT` >
  lowest main ref, plus `root-ref-missing` and `invalid-root`.
- Reachability tests assert all three paths: through `contains`, through another
  file with the same id, or through a link from a reachable node. A main and its
  versions are alternatives for one logical node, so an alternative branch is not
  `unreachable`; a linked history view is not one either.
- Link tests cover both forms: a mapping with its own `type`, and a bare ref
  whose type is read from the target node.
- Git tests create a temporary repository, set local `user.name`/`user.email`, and
  use `pytest.mark.skipif(shutil.which("git") is None, ...)`.
- Structural tests assert body bytes, not just field values.
- Keep the suite under a few seconds; no network.

Before a commit:

```sh
python3 -m pytest -q
BD_ROOT=examples bd check
git diff --check
```

## Debugging

- `PYTHONPATH=src python3 -m bd_tree ...` is identical to `bd`.
- `BD_ROOT`/`--root` choose the store (default: nearest parent with `nodes/` or
  `.bd_tree/nodes/`).
- `bd root` shows or switches the default view root; `bd root --clear` removes
  `ROOT`. It does not rewrite the work area.
- `bd views` lists containment roots and marks the default; `bd current` reports
  the work area and the view actually in it.
- `bd check --view REF` narrows validation to one closure.
- `bd tree`, `bd show`, `bd path` quickly show what the loader sees.
- `bd show REF+N` caps each body at 4000 characters unless `--max-chars` is
  given; `--max-chars 0` prints full bodies. `bd ls --depth 0` and
  `bd tree --depth 0` are unlimited.
- `bd find`/`bd grep` default to the default view; `--view REF` narrows and
  `--all` searches the whole store. Output stays capped.
- `bd work --status` diagnoses symlink problems without touching the store and
  inspects the view actually in the area; `bd edit REF` resolves a ref inside
  that view.
- `pdb` works normally; the CLI is a thin argparse layer.

Common mistakes:

- Re-serialising the body through YAML. Never do it.
- Assuming `contains` is a set. Order is data.
- Treating `links` as containment. It is a DAG and must not add view members.
- Hardcoding layer names or edge types. The tool is schema-agnostic.
- Writing a sidecar index. Derive it.

## Invariants to protect

1. The store's `nodes/` directory (`.bd_tree/nodes/` in a project layout) is the
   only source of truth.
2. Filename is identity and version.
3. `contains` is an ordered tree per view; `links` is a DAG.
4. Arbitrary front matter survives edits and exports.
5. Body bytes survive structural edits.
6. No JSON/TOML/lock/state data files; the only store-level pointer is `ROOT`,
   one ref on one line.
7. A view never crosses a branch, and neither does a version; solutions are git
   worktrees. `promote` is filesystem-only and never crosses a worktree; it is
   not a way to switch trees.
8. Generated files are disposable and never committed.
9. A project has exactly one writable work area, `<project>/bd_work/`, holding
   one view at a time. Its view changes only with `bd work`, not with `bd root`.
   Read-only exports never become a second work area.

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
- `docs/BRANCHES-AND-VERSIONS.md` — branch/version separation contract.
- `AGENTS.md` — operating rules for agents.

Keep examples executable. Run them before committing.

## Not built yet

- No CI or generic importer. Packaging is `pyproject.toml` plus the `bd`
  console script.
- No three-way node merge; solutions merge with git.
- No locking for concurrent agents.
- No Windows-specific symlink path.
