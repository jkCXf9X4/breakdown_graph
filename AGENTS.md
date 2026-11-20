# Agent operating rules

This repository is both a tool (`bd_tree`, command `bd`) and a reference example
project. Read [`README.md`](README.md) and [`docs/DESIGN.md`](docs/DESIGN.md)
before changing behaviour. The design document is authoritative for the model;
this file is the short operating protocol.

## First session

1. Locate the store: `export BD_ROOT=examples` (the project root; the store is
   `examples/.bd_tree`) or pass `--root`. Install once from the clone with
   `pip install -e '.[test]'`, then use `bd`. Without installing, run from the
   repo root with `PYTHONPATH=src python3 -m bd_tree`.
2. Confirm the baseline:

   ```sh
   python3 -m pytest -q
   bd check
   ```

3. See the shape: `bd tree --depth 1`, `bd find <term>`, `bd path <ref>`.
   For the example layout and two complete trees over one store, run the commands
   in `examples/README.md`.
4. For a solution: `bd solution new NAME`, `cd` into the printed worktree
   project directory, then `bd work` with the printed default-view ref.
5. For edits: prefer `bd edit REF` for the path inside `bd_work/`; direct edits
   to `.bd_tree/nodes/<ref>.md` are an escape hatch only. Change structure with
   `bd contain` / `bd uncontain` / `bd link` / `bd unlink`.
6. Validate: `bd check`, `bd stale`.

## Two jobs

**Working in a store.** The store is data. Browse with `tree`/`show`/`find`; edit
through `bd work`; keep the store's `nodes/` flat; commit node files, never
`bd_work/`.

**Changing the tool.** Read [`docs/DEVELOPING.md`](docs/DEVELOPING.md). Work
through the loader, view, checker, and exporter boundaries. Add a test for every
behaviour change and update the docs listed at the bottom.

## Core invariants

- The files under a store's `nodes/` directory (`.bd_tree/nodes/` in a project
  layout) are the only source of truth.
- A filename is identity and version: `<id>.md` is main, `<id>-<version>.md` is a
  version.
- `contains` is an ordered containment list. A view is the closure of one ref.
- `contains` is a tree per view. `links` is a DAG and never adds nodes to a view.
- Front matter is arbitrary; only the identity/containment/link/freshness keys
  (`id`, `legacy`, `contains`, `links`, `to`, `type`, `propagates`, `pinned`)
  are reserved. `home`, `folder`, `name`, and `title` are presentation fields.
  Add no schema unless a project asks for one.
- Git owns the solution boundary: one branch/worktree per solution. The flat store
  is the merge unit; `bd work` is a layout inside one checkout, never a branch
  mechanism.
- Work folders are symlink views: node `.md` files are symlinks, while
  `INDEX.md`, `AGENTS.md`, and `REFS.md` are regular generated files. Never copy
  node content into a work folder and never introduce a sync layer.
- A project has exactly one writable work area, `<project>/bd_work/`. It holds
  one view at a time; `bd work REF` replaces its contents. Read-only `bd view`
  and `bd export` snapshots are not a second work area.
- A view never crosses a branch, and neither does a version. Versions are node
  files inside one checkout; branches are git. Never resolve a ref through a
  branch name, never add a branch or per-node active-version selector, and never
  promote across branches — merge first.
- No JSON, TOML, lock, or state data files. The one exception is a store-level
  `ROOT` file: one ref on one line (e.g. `1-4`), nothing else. Derived output is
  disposable and gitignored.
- The default view root is `ROOT` when present, else the lowest main ref; an
  explicit ref or `--root-ref` wins over both. A declared but missing ref is
  `root-ref-missing`; malformed content is `invalid-root`. This default is
  separate from the view held by the work area, which changes only with
  `bd work REF`.

## Where to work

- Solutions: `bd solution new NAME` (thin wrapper over
  `git worktree add ../NAME -b NAME`); one worktree per solution.
- Writable layout: `bd work REF` writes the single `<project>/bd_work/` area;
  a different REF replaces its contents. `bd current` reports the area and its
  view; `--path` and `--view` narrow the output, and it errors if no area
  exists.
- Agent sessions work in that one area and read exactly one view. Switch with
  `bd work REF`; never keep parallel work folders side by side. `--status` and
  `--writeback` inspect the view actually in the area, not the requested or
  default view. `bd views` lists containment roots and marks the store default.
- Find and edit inside the area: `bd edit REF` prints the absolute path of a ref
  in the active view and errors if it is absent.
- Read-only snapshots: `bd view REF --out DIR` or `bd export ...`; they are
  disposable exports, never the work area.
- Switching trees: `bd root REF` changes the store default root, `bd work REF`
  changes the work-area view, or repoint one parent with `bd uncontain` /
  `bd contain`. `bd promote` is not a switch; it copies one version onto main.
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
| Search | `bd find TEXT`, `bd grep 'RE'`; add `--view REF` or `--all` |
| Show the work area | `bd current [--path\|--view]` |
| List containment roots | `bd views` |
| Switch/edit the work area | `bd work REF`, then open `bd edit REF` |
| Repair symlinks | `bd work --status` / `bd work --writeback` |
| Switch tree root | `bd root REF`, `bd root --clear` |
| Show versions | `bd versions ID`, `bd fork ID`, `bd promote REF` |
| New solution | `bd solution new NAME` |
| Validate | `bd check`, `bd stale` |
| Read-only agent pack | `bd export context --view REF --out DIR` |

## Commands

Commands assume `bd` is installed (`pip install -e '.[test]'`); without
installing, prefix each with `PYTHONPATH=src python3 -m bd_tree` instead of `bd`.

```sh
export BD_ROOT=examples
python3 -m pytest -q
bd check
bd tree 1 --depth 1
bd show 1+1 --max-chars 400
bd contain 1 5 --after 6
bd link 5 9 --type supports
bd work 1                 # write the single <project>/bd_work area
bd current                # <project>/bd_work (view 1)
bd work 1 --print         # print that directory; read-only, no build
bd edit 2                 # path of ref 2 in the active view
bd work 1-1               # switch the same area to another view
bd solution list
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
`docs:`. One concern per commit. Do not commit caches, `bd_work/`, exported
views, or generated output.

## Docs map

- [`README.md`](README.md) — front door, two axes, command map.
- [`docs/GETTING-STARTED.md`](docs/GETTING-STARTED.md) — user tutorial.
- [`docs/CHEATSHEET.md`](docs/CHEATSHEET.md) — command reference.
- [`docs/DEVELOPING.md`](docs/DEVELOPING.md) — developer guide.
- [`docs/DESIGN.md`](docs/DESIGN.md) — model, decisions, invariants.
- [`docs/BRANCHES-AND-VERSIONS.md`](docs/BRANCHES-AND-VERSIONS.md) — the
  branch/version separation contract.
- [`docs/breakdown/`](docs/breakdown/) — product breakdown as a second `bd`
  project (store `docs/breakdown/.bd_tree/`): current state, open work,
  scrutiny, and history. Run `bd --root docs/breakdown tree`, or `bd work 1`
  from that directory.
