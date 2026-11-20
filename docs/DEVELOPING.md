# Developing

This guide is for changing the tool itself. To use the tool, read
[`GETTING-STARTED.md`](GETTING-STARTED.md) first.

## Quick start

```sh
git clone https://github.com/jkCXf9X4/info_graph
cd info_graph
python3 -m pytest -q
BD_ROOT=workspace/licentiate-n ./bin/bd check
```

Requirements: Python 3.10+, PyYAML, pytest. Graphviz `dot` only for dot export.
There is no packaging step; `bin/bd` inserts the repository root on `sys.path`.

## The data flow

```
nodes/*.md
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
- `View` is one containment closure: the nodes reachable from a root ref.
- Every read-only command works on a `View`; structural edits work on `Store`
  and write node files.

Validation is global; export and agent context are view-scoped.

## Module map

| Module | Responsibility |
| --- | --- |
| `loader.py` | Filename grammar, store scan, branch/view resolution, citation edges |
| `model.py` | `Node`, `Store`, `View`, `Edge`, `Issue`, `Link` |
| `frontmatter.py` | Parse and rewrite front matter; body bytes are never re-serialised |
| `checker.py` | Structural checks, per-view tree checks, `--require`, size limits |
| `freshness.py` | Pins, stale edges, reconcile |
| `navigate.py` | `show`, `tree`, `ls`, `find`, `grep`, `path` renderers |
| `exporter.py` | `tree`, `context`, `dot` projections and path templates |
| `work.py` | Symlink work folders, `--status`, `--writeback`, git context |
| `solutions.py` | Thin `git worktree` lifecycle wrapper |
| `ops.py` | `init`, `new`, `contain`, `uncontain`, `link`, `unlink`, versions, `diff` |
| `api.py` | Public Python functions |
| `cli.py` | argparse wiring and output formatting |

Data comes from `nodes/`; there are no hidden stores, caches, or state files.

## Key types

```python
Node   id, version, ref, meta, contains, links, body, path
Store  root, nodes: dict[ref, Node], edges, issues
View   store, ref, nodes: dict[ref, Node], edges, issues
Edge   source, target, type, pinned, origin ("link" or "reference")
Issue  level, code, message, node, path
```

`Node.meta` is the raw front matter; arbitrary fields live there and survive
export. `contains is None` means "inherit the main version's list"; `[]` means
"no children".

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
- `test_corpus.py` runs the 128-node corpus through `bd check` and view export.
- Git tests create a temporary repository, set local `user.name`/`user.email`, and
  use `pytest.mark.skipif(shutil.which("git") is None, ...)`.
- Structural tests assert body bytes, not just field values.
- Keep the suite under a few seconds; no network.

Before a commit:

```sh
python3 -m pytest -q
BD_ROOT=workspace/licentiate-n ./bin/bd check
git diff --check
```

## Debugging

- `python3 -m breakdown ...` is identical to `bin/bd`.
- `BD_ROOT`/`--root` choose the store (default: nearest parent with `nodes/`).
- `bd check --view REF` narrows validation to one closure.
- `bd tree`, `bd show`, `bd path` quickly show what the loader sees.
- `bd work --status` diagnoses symlink problems without touching the store.
- `pdb` works normally; the CLI is a thin argparse layer.

Common mistakes:

- Re-serialising the body through YAML. Never do it.
- Assuming `contains` is a set. Order is data.
- Treating `links` as containment. It is a DAG and must not add view members.
- Hardcoding layer names or edge types. The tool is schema-agnostic.
- Writing a sidecar index. Derive it.

## Invariants to protect

1. `nodes/` is the only source of truth.
2. Filename is identity and version.
3. `contains` is an ordered tree per view; `links` is a DAG.
4. Arbitrary front matter survives edits and exports.
5. Body bytes survive structural edits.
6. No JSON/TOML/lock/state data files.
7. A view never crosses a branch, and neither does a version; solutions are git
   worktrees. `promote` is filesystem-only and never crosses a worktree.
8. Generated files are disposable and never committed.

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
- `docs/ROADMAP.md` — next work.
- `AGENTS.md` — operating rules for agents.

Keep examples executable. Run them before committing.

## Not built yet

- No `pyproject.toml`, console script, CI, or generic importer.
- No three-way node merge; solutions merge with git.
- No locking for concurrent agents.
- No Windows-specific symlink path.

See [`ROADMAP.md`](ROADMAP.md).
