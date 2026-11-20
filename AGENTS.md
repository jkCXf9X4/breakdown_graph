# Agent operating rules

This repository is both a tool (`bd`) and a reference store corpus. Read
[`README.md`](README.md) and [`docs/DESIGN.md`](docs/DESIGN.md) before changing
behaviour. The design document is authoritative for the model; this file is the
short operating protocol.

## First session

1. Locate the store: `export BD_ROOT=workspace/licentiate-n` or pass `--root`.
2. Confirm the baseline:

   ```sh
   python3 -m pytest -q
   bd check
   ```

3. See the shape: `bd tree 1 --depth 1`, `bd find <term>`, `bd path <ref>`.
4. For a solution: `bd solution new NAME`, `cd` into it, `bd work 1`.
5. For edits: edit through a work folder or `nodes/<ref>.md`; change structure
   with `bd contain` / `bd uncontain` / `bd link` / `bd unlink`.
6. Validate: `bd check`, `bd stale`.

## Two jobs

**Working in a store.** The store is data. Browse with `tree`/`show`/`find`; edit
through `bd work`; keep `nodes/` flat; commit node files, never `build/`.

**Changing the tool.** Read [`docs/DEVELOPING.md`](docs/DEVELOPING.md). Work
through the loader, view, checker, and exporter boundaries. Add a test for every
behaviour change and update the docs listed at the bottom.

## Core invariants

- The files under a store's `nodes/` directory are the only source of truth.
- A filename is identity and version: `<id>.md` is main, `<id>-<version>.md` is a
  version.
- `contains` is an ordered containment list. A view is the closure of one ref.
- `contains` is a tree per view. `links` is a DAG and never adds nodes to a view.
- Front matter is arbitrary; only `id`, `legacy`, `contains`, `links`, `home` are
  reserved. Add no schema unless a project asks for one.
- Git owns the solution boundary: one branch/worktree per solution. The flat store
  is the merge unit; `bd work` is a layout inside one checkout, never a branch
  mechanism.
- Work folders are symlink views. Never copy node content into a work folder and
  never introduce a sync layer.
- A view never crosses a branch, and neither does a version. Versions are node
  files inside one checkout; branches are git. Never resolve a ref through a
  branch name, never add a branch or active-version selector, and never promote
  across branches — merge first.
- No JSON, TOML, lock, or state data files. Derived output is disposable and
  gitignored.

## Where to work

- Solutions: `bd solution new NAME` (thin wrapper over
  `git worktree add ../NAME -b NAME`); one worktree per solution.
- Writable layout: `bd work REF` creates `build/work/<ref>`; edit through symlinks.
- Read-only views: `bd view REF --out DIR` or `bd export ...`.
- Never edit `workspace/licentiate/` directly; it is the legacy typed-id source.
  Use `tools/migrate_licentiate.py` to regenerate `workspace/licentiate-n/`.
- Never hand-edit generated `INDEX.md`, `AGENTS.md`, or `REFS.md` inside a work or
  output directory.

## Common tasks

| Task | Command |
| --- | --- |
| New store | `bd init DIR` |
| Add a node | `bd new --parent REF --field title=... --field layer=...` |
| Move a child | `bd uncontain P C` then `bd contain P C --before REF` |
| Add an edge | `bd link FROM TO --type supports --propagates` |
| Browse a subtree | `bd tree REF --depth 0` |
| Read a node and children | `bd show REF+2 --max-chars 800` |
| Search | `bd find TEXT`, `bd grep 'RE'` |
| Edit a view | `bd work REF`, then edit through the symlinks |
| Repair symlinks | `bd work REF --status` / `--writeback` |
| New solution | `bd solution new NAME` |
| Validate | `bd check`, `bd stale` |
| Read-only agent pack | `bd export context --view REF --out DIR` |

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

## Code style

- Python 3.10, standard library plus PyYAML.
- Type hints, dataclasses, small modules.
- CLI uses argparse. No new dependency without a clear reason.
- Structural errors raise `BreakdownError`; check reporting uses `Issue`.
- Preserve arbitrary front-matter fields and body bytes unless the command
  explicitly rewrites them.

## Commit style

Short conventional prefixes, matching history: `feat:`, `fix:`, `chore:`,
`docs:`. One concern per commit. Do not commit caches, `build/`, exported views,
or generated corpora output.

## Docs map

- [`README.md`](README.md) — front door, two axes, command map.
- [`docs/GETTING-STARTED.md`](docs/GETTING-STARTED.md) — user tutorial.
- [`docs/CHEATSHEET.md`](docs/CHEATSHEET.md) — command reference.
- [`docs/DEVELOPING.md`](docs/DEVELOPING.md) — developer guide.
- [`docs/DESIGN.md`](docs/DESIGN.md) — model, decisions, invariants.
- [`docs/BRANCHES-AND-VERSIONS.md`](docs/BRANCHES-AND-VERSIONS.md) — the
  branch/version separation contract.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — next work.
