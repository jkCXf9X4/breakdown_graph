# Agent operating rules

This repository is both a tool (`bd_tree`, command `bd`) and a reference example
project. Read [`README.md`](README.md) and [`docs/DESIGN.md`](docs/DESIGN.md)
before changing behaviour. The design document is authoritative for the model;
this file is the short operating protocol.

## First session

1. Locate the store: plain `bd` works from the repo root because the committed
   `.bd_root` pointer names `examples` (the project root; the store is
   `examples/.bd_tree`). Equivalent: `export BD_ROOT=examples`, or pass
   `--root`. Install once from the clone with `pip install -e '.[test]'`, then
   use `bd`. Without installing, run from the repo root with
   `PYTHONPATH=src python3 -m bd_tree`.
2. Confirm the baseline:

   ```sh
   python3 -m pytest -q
   bd check
   ```

3. See the shape: `bd tree 1-1 --depth 1`, `bd find <term>`, `bd path <ref>`.
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
- A filename is identity and version: `<id>-<version>.md`, version >= 1. There
  is no bare `<id>.md`; versions of one id are peers.
- A ref is the full `id-version` (`5-1`, not `5`). `contains`, `links`, and
  `ROOT` hold full refs only; a bare ref in data is a `check` error (`bare-ref`).
  A bare id on the command line is a selector resolved inside the selected view;
  it is never written to data.
- `contains` is an ordered containment list. A view is the closure of one ref.
- `contains` is a tree per view, and one view holds at most one version per
  logical id (`duplicate-id`); the chain selects what is current. `links` is a
  DAG and never adds nodes to a view;
  it does keep an outgoing target reachable, and a link to another containment
  root is not an `external-link`. A scalar link (`links: ['10-1']`) takes its
  type from the target node's `type`.
- Front matter is arbitrary; only the identity/containment/link/freshness keys
  (`id`, `legacy`, `contains`, `links`, `to`, `type`, `propagates`, `pinned`)
  are reserved. `section`, `name`, and `title` are presentation fields: work and
  export paths use `section` to open directories, else `<name>.md`, else
  `<ref>-<title-slug>.md`, else `<ref>.md`. `section: true` names the directory
  by the node's placement name; `section: "<dir>"` names it verbatim.
  Presentation only: it changes no identity or validation, so it adds no schema.
  `folder` is ordinary metadata with no effect on placement, naming, or
  validation. `home` has no meaning; it is ordinary front matter. Add no schema
  unless a project asks for one.
- Git owns the solution boundary: one branch/worktree per solution. The flat store
  is the merge unit; `bd work` is a layout inside one checkout, never a branch
  mechanism.
- Work folders are symlink views: node `.md` files are symlinks, while
  `INDEX.md`, `AGENTS.md`, and `REFS.md` are regular generated files. Never copy
  node content into a work folder and never introduce a sync layer.
- A project has exactly one writable work area, `<project>/bd_work/`. It holds
  one view at a time; `bd work REF` replaces its contents. Read-only `bd export`
  snapshots (tree, context, dot) are not a second work area.
- A view never crosses a branch, and neither does a version. Versions are node
  files inside one checkout; branches are git. Never resolve a ref through a
  branch name, never add a branch or per-node active-version selector, and never
  copy a node across branches — merge first.
- The version current in a view is the one its parent's `contains` names. There
  is no per-node pointer and no extra state file.
- No JSON, TOML, lock, or state data files. Two exceptions, both one line of
  text: a store-level `ROOT` file holding one ref (e.g. `1-1`), and a
  folder-level `.bd_root` pointer holding one store path, naming the store a
  working folder belongs to. Nothing else goes in either file. Derived output is
  disposable and gitignored.
- The default view root is `ROOT` when present, else the lowest available node
  by `(id, version)`; an explicit ref where a command takes one wins over both.
  `bd check --view REF` only narrows reporting. A declared but missing ref is
  `root-ref-missing`; malformed content is `invalid-root`. This default is
  separate from the view held by the work area, which changes only with
  `bd work REF`.

## Where to work

- Solutions: `bd solution new NAME` (thin wrapper over
  `git worktree add ../NAME -b NAME`); one worktree per solution.
- Writable layout: `bd work REF` writes the single `<project>/bd_work/` area;
  a different REF replaces its contents. `bd work REF+N` (or `--depth N`)
  materializes only the first N descendant levels — the view stays the full
  closure, the area holds a prefix of it. `bd current` reports the area and its
  view, including `+N`; `--path` and `--view` narrow the output, and it errors
  if no area exists.
- Agent sessions work in that one area and read exactly one view. Switch with
  `bd work REF` (drop the `+N` to materialize the whole view); never keep
  parallel work folders side by side. `--status` and `--writeback` inspect the
  view actually in the area, not the requested or default view. `bd views` lists
  containment roots and marks the store default.
- Find and edit inside the area: `bd edit REF` prints the absolute path of a ref
  in the active view and errors if it is absent.
- Read-only snapshots: `bd export tree REF --out DIR`, or another `bd export`
  choice; they are disposable exports, never the work area.
- Switching trees: `bd root REF` changes the store default root, `bd work REF`
  changes the work-area view, or repoint one parent with `bd uncontain` /
  `bd contain`, or clone and swap with `bd clone REF` then `bd replace REF NEW`.
  `bd replace` keeps NEW at REF's exact index in its parent's `contains`, or
  repoints `ROOT` when REF is the root, and leaves the old file as a peer. These
  are the only switches; a view uses the version named by its parent's
  `contains`.
- Never hand-edit generated `INDEX.md`, `AGENTS.md`, or `REFS.md` inside a work or
  output directory.

## Common tasks

| Task | Command |
| --- | --- |
| New store | `bd init DIR` |
| Add a node | `bd new --parent REF --field title=... --field layer=...` |
| Move a child | `bd uncontain P C` then `bd contain P C --before REF` |
| Clone and replace a node | `bd clone OLD` then `bd replace OLD NEW` |
| Replace a version in place | `bd replace OLD NEW` |
| Add an edge | `bd link FROM TO --type supports --propagates` |
| Browse a subtree | `bd tree REF --depth 0` |
| Read a node and children | `bd show REF+2 --max-chars 800` |
| Search | `bd find TEXT`, `bd find 'RE' --regex`; add `--view REF` or `--all` |
| Show the work area | `bd current [--path\|--view]` |
| List containment roots | `bd views` |
| Switch/edit the work area | `bd work REF[+N]`, then open `bd edit REF` |
| Repair symlinks | `bd work --status` / `bd work --writeback` |
| Switch tree root | `bd root REF`, `bd root --clear` |
| Show versions | `bd versions ID`, `bd delete REF` |
| Clone a node or subtree | `bd clone REF [--version N] [--subtree]` |
| New solution | `bd solution new NAME` |
| Convert a classic store | `bd migrate [--dry-run]` |
| Validate | `bd check`, `bd stale` |
| Read-only agent pack | `bd export context --view REF --out DIR` |

## Commands

Commands assume `bd` is installed (`pip install -e '.[test]'`); without
installing, prefix each with `PYTHONPATH=src python3 -m bd_tree` instead of `bd`.

```sh
export BD_ROOT=examples
python3 -m pytest -q
bd check
bd tree 1-1 --depth 1
bd show 1-1+1 --max-chars 400
bd uncontain 1-1 5-1
bd contain 1-1 5-1 --before 2-1
bd link 5-1 6-1 --type supports
bd clone 2-1 --subtree    # copy a subtree to new peer versions
bd replace 2-1 2-2        # wire the copy in at 2-1's index (or repoint ROOT)
bd work 1-1               # write the single <project>/bd_work area
bd work 1-1+1             # same area, first two levels only
bd current                # <project>/bd_work (view 1-1+1)
bd current --path         # print that directory; read-only, no build
bd edit 2-1               # path of ref 2-1 in the active view
bd work 1-2               # switch the same area to another view
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
  scrutiny, and history. Run `bd tree --root docs/breakdown`, or `bd work 1-1`
  from that directory.
