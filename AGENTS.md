# Agent operating rules

This repository is a generic markdown information graph and its reference corpus.

Read [`README.md`](README.md) and [`docs/DESIGN.md`](docs/DESIGN.md) before changing
behaviour. The design document is authoritative for the model; this file is the
short operating protocol.

## Core invariants

- The files under a store's `nodes/` directory are the only source of truth.
- A filename is identity and version: `<id>.md` is main, `<id>-<version>.md` is a
  version.
- `contains` is an ordered containment list. A view is the closure of one ref.
- `contains` is a tree per view. `links` is a DAG and never adds nodes to a view.
- Front matter is arbitrary. Only `id`, `legacy`, `contains`, `links`, `home` are
  reserved. Do not add a schema unless a project asks for one.
- Git owns the solution boundary: one branch/worktree per solution. The flat store
  is the merge unit. `bd work` is a layout inside one checkout, never a branch
  mechanism.
- Work folders are symlink views. Never copy node content into a work folder and
  never introduce a sync layer.
- A view never crosses a branch. Do not mix versions from different branches in one
  view; merge the branches with git.
- No JSON, TOML, lock, or state data files. Derived output is disposable and
  gitignored.

## Where to work

- Solutions: `bd solution new NAME` (thin wrapper over
  `git worktree add ../NAME -b NAME`); one worktree per solution.
- Writable layout: `bd work REF` creates `build/work/<ref>`; edit through symlinks.
- Read-only views: `bd view REF --out DIR` or `bd export ...`.
- Never edit `workspace/licentiate/` directly. It is the legacy typed-id source for
  the migration. Use `tools/migrate_licentiate.py` to regenerate
  `workspace/licentiate-n/`.
- Never hand-edit generated `INDEX.md`, `AGENTS.md`, or `REFS.md` inside a work or
  output directory.

## Commands

```sh
export BD_ROOT=workspace/licentiate-n
python3 -m pytest -q
./bin/bd check
./bin/bd tree 1 --depth 1
./bin/bd show 1+1 --max-chars 400
./bin/bd contain 1 5 --after 6
./bin/bd link 5 9 --type supports
./bin/bd work 1 --print
./bin/bd solution list
```

When changing behaviour:

1. Update tests first or alongside the change.
2. Run the full pytest suite and the corpus check.
3. If the model or a command changes, update `README.md` and `docs/DESIGN.md`.
4. Keep the CLI help and the generated work-tree `AGENTS.md` consistent.

## Code style

- Python 3.10, standard library plus PyYAML.
- Type hints, dataclasses, small modules.
- CLI uses argparse. No new dependency without a clear reason.
- Structural errors raise `BreakdownError`; check reporting uses `Issue`.
- Preserve arbitrary front-matter fields and body bytes unless the command is
  explicitly rewriting them.

## Commit style

Short conventional prefixes, matching history: `feat:`, `fix:`, `chore:`,
`docs:`. One concern per commit. Do not commit caches, `build/`, exported views, or
generated corpora output.
