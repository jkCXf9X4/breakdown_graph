# Agent operating rules

This repository is both a tool (`bd_tree`, command `bd`) and a reference example
project. Read [`README.md`](README.md) and [`docs/DESIGN.md`](docs/DESIGN.md)
before changing behaviour. The design document is authoritative for the model;
this file is the short operating protocol.

## First session

1. Locate the store: plain `bd` works from the repo root because the committed
   `.bd_root` pointer names `examples` (the project root; the store is
   `examples/.bd_tree`, a relative-band graph with `ROOT` `1-1`). Equivalent:
   `export BD_ROOT=examples`, or pass `--root`. Install once from the clone with
   `pip install -e '.[test]'`, then use `bd`. Without installing, run from the
   repo root with `PYTHONPATH=src python3 -m bd_tree`.
2. Confirm the baseline:

   ```sh
   python3 -m pytest -q
   bd audit
   bd check                    # 12 nodes, 0 errors, 0 warnings
   ```

3. See the shape: `bd check`, `bd graph 1-1`, `bd graph`, `bd out 1-1`,
   `bd in 4-1`. The default example is a relative-band graph of twelve nodes
   (`1-1`..`12-1`); run the commands in `examples/README.md`.
4. For a solution: `bd solution new NAME`, `cd` into the printed worktree
   project directory, then `bd work` with the printed default-view ref.
5. For edits: prefer `bd edit REF` for the path inside `bd_work/`; direct edits
   to `.bd_tree/nodes/<ref>.md` are an escape hatch only. Change structure with
   `bd link` / `bd unlink`. There is no `contain`/`uncontain`: `contains` is
   retired and `bd migrate` converts an older store.
6. Validate: `bd check` validates the store and its views; `bd audit` is the
   explicit graph audit. Run `bd stale` too.

## Two jobs

**Working in a store.** The store is data. Browse with `graph`/`show`/`find`;
edit through `bd work`; keep the store's `nodes/` flat; commit node files, never
`bd_work/`.

**Changing the tool.** Read [`docs/DEVELOPING.md`](docs/DEVELOPING.md). Work
through the loader, view, checker, and exporter boundaries. Add a test for every
behaviour change and update the docs listed at the bottom.

## Core invariants

- The files under a store's `nodes/` directory (`.bd_tree/nodes/` in a project
  layout) are the only source of truth.
- A filename is identity and version: `<id>-<version>.md`, version >= 1. There
  is no bare `<id>.md`; versions of one id are peers.
- A ref is the full `id-version` (`5-1`, not `5`). `links` and `ROOT` hold full
  refs only; a bare ref in data is a `check` error (`bare-ref`). A bare id on
  the command line is a selector resolved inside the selected view; it is never
  written to data.
- There is one topology: typed `links`. Structural links define structure;
  symmetric links are associative and derive an opposite. `contains` is not
  data. A node that still declares it fails `bd check` with `contains-removed`;
  `bd migrate` converts it. A view is the closure of one ref over forward
  structural links.
- A link is *structural* unless it declares `symmetric: true`. Only structural
  links expand a view, define `path` ancestry and `views` roots, order bands, and
  drive `bd clone --subtree`. A symmetric master (`symmetric: true`, optional
  `inverse: TYPE`) is authored on exactly one node; its opposite is derived at
  load, marked `[derived]`, and never stored or structural.
- Structural `links` are the child relation: parent→child full refs, each with a
  required non-empty `type`, with `propagates`/`pinned` preserved. Out-edges are
  authored, in-edges derived. A node with several parents appears once in a
  view; multiple parents are legal.
- Bands have two modes. When any node declares `stage` (absolute mode), edges go
  forward (`stage(parent) < stage(child)`); `order` breaks ties inside a stage.
  Otherwise (relative mode, the default example) every node needs a non-empty
  `band` (or the older `layer: band/subpath` shorthand), and an optional
  `subpath` names an explicit folder below the band. Band order and nesting
  come from cross-band structural edges by the shortest-path rule (equal-length
  branches stay top-level), unless the ROOT node declares `band_layout: flat`,
  which keeps every band top-level in topological order; a ROOT
  `band_order: [band, ...]` breaks ties among ready bands in the topological
  order and composes with flat; `order` positions nodes inside a band, where a
  same-band edge needs `order(source) < order(target)`, including across
  subpaths. See [`docs/GRAPH-LAYOUT.md`](docs/GRAPH-LAYOUT.md).
- Front matter is arbitrary; only the identity/link/freshness keys (`id`,
  `legacy`, `links`, `to`, `type`, `propagates`, `pinned`, `symmetric`,
  `inverse`) and the band keys (`layer`, `band`, `subpath`, `stage`, `order`,
  `group`, and the ROOT node's `band_layout`/`band_order`) are reserved. Bands
  are the only layout. `section`, `group`,
  `folder`, and `home` are ordinary front matter: `section` and `group` place
  nothing and add no schema. A node's file stem is an explicit `name`
  (`<name>.md`), else `<ref>-<title-slug>.md`, else `<ref>.md`. Add no schema
  unless a project asks for one.
- Git owns the solution boundary: one branch/worktree per solution. The flat store
  is the merge unit; `bd work` is a layout inside one checkout, never a branch
  mechanism.
- Work folders are symlink views: node `.md` files are symlinks, while
  `INDEX.md` in every directory, `AGENTS.md`, and `REFS.md` are regular generated
  files. These three names are reserved in every directory. Never copy
  node content into a work folder and never introduce a sync layer.
- A project has exactly one writable work area, `<project>/bd_work/`. It holds
  one view at a time; `bd work REF` replaces its contents. Read-only `bd export`
  snapshots (graph, context, dot, svg) are not a second work area.
- A view never crosses a branch, and neither does a version. Versions are node
  files inside one checkout; branches are git. Never resolve a ref through a
  branch name, never add a branch or per-node active-version selector, and never
  copy a node across branches — merge first.
- Edges pin full refs, and a view warns (`graph-duplicate-version`) when two
  versions of one id are reachable. There is no per-node pointer and no extra
  state file.
- No JSON, TOML, lock, or state data files. Two exceptions, both one line of
  text: a store-level `ROOT` file holding one ref (e.g. `1-1`), and a
  folder-level `.bd_root` pointer holding one store path, naming the store a
  working folder belongs to. Nothing else goes in either file. Derived output is
  disposable and gitignored. Writers serialize on a transient advisory lock in
  the system temp directory; it never enters the store or git.
- The default view root is `ROOT` when present, else the lowest graph root; an
  explicit ref where a command takes one wins over both.
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
  closure, the area holds a prefix of it. A descendant level is a link hop; the
  layout is the band plan. `bd current` reports the area and its view, including
  `+N`; `--path` and `--view` narrow the output, and it errors if no area
  exists.
- Agent sessions work in that one area and read exactly one view. Switch with
  `bd work REF` (drop the `+N` to materialize the whole view); never keep
  parallel work folders side by side. `--status` and `--writeback` inspect the
  view actually in the area, not the requested or default view. `bd views` lists
  graph roots and marks the store default.
- Find and edit inside the area: `bd edit REF` prints the absolute path of a ref
  in the active view and errors if it is absent.
- Read-only snapshots: `bd export graph --view REF --out DIR`, or another
  `bd export` choice; they are disposable exports, never the work area.
- Switching trees: `bd root REF` changes the store default root, `bd work REF`
  changes the work-area view, or clone and swap with `bd clone REF` then
  `bd replace REF NEW`. `bd replace` repoints inbound links, or repoints `ROOT`
  when REF is the root, and leaves the old file as a peer. These are the only
  switches; edges pin full refs.
- Never hand-edit generated `INDEX.md` (one in every directory), `AGENTS.md`, or
  `REFS.md` inside a work or output directory.

## Common tasks

| Task | Command |
| --- | --- |
| New store | `bd init DIR` (relative-band graph root) |
| Add a node (relative) | `bd new --parent REF --type breaks_down --band NAME [--subpath SUB] [--order N]` |
| Add a node (absolute) | `bd new --parent REF --type breaks_down --stage N [--order N]` |
| Clone and replace a node | `bd clone OLD` then `bd replace OLD NEW` |
| Replace a version in place | `bd replace OLD NEW` |
| Add an edge | `bd link FROM TO --type supports [--propagates]`; refuses back-edges or a band cycle, keeps targets sorted |
| Remove an edge | `bd unlink FROM TO [--type T]` |
| Browse the graph | `bd graph [REF] [--depth N] [--stage A:B] [--type T]` |
| Read a node and children | `bd show REF+2 --max-chars 800` (two link hops) |
| Reverse chain | `bd path REF` (first parent when ambiguous) |
| Search | `bd find TEXT`, `bd find 'RE' --regex`; add `--view REF` or `--all` |
| Show the work area | `bd current [--path\|--view]` |
| List graph roots | `bd views` |
| Switch/edit the work area | `bd work REF[+N]`, then open `bd edit REF` |
| Repair symlinks | `bd work --status` / `bd work --writeback` |
| Switch view root | `bd root REF`, `bd root --clear` |
| Show versions | `bd versions ID`, `bd delete REF` |
| Clone a node or subtree | `bd clone REF [--version N] [--subtree]` |
| New solution | `bd solution new NAME` |
| Convert an old store | `bd migrate [--dry-run] [--type T]` (`contains`, or classic bare files); add `--symmetric TYPE`, `--inverse TYPE=TYPE2`, `--band-order` on an already-migrated store |
| Validate | `bd check`, `bd audit`, `bd stale` |
| Read-only agent pack | `bd export context --view REF --out DIR` |

## Commands

Commands assume `bd` is installed (`pip install -e '.[test]'`); without
installing, prefix each with `PYTHONPATH=src python3 -m bd_tree` instead of `bd`.

```sh
export BD_ROOT=examples
python3 -m pytest -q
bd check                    # 12 nodes, 0 errors, 0 warnings
bd audit                    # graph example: 0 errors, 0 warnings
bd graph 1-1                # derived band layout
bd graph                    # relative-band graph from ROOT 1-1
bd out 1-1                  # master out-edges then [derived] opposites
bd in 4-1                   # derived in-edges
bd path 4-1                 # reverse chain, first parent when ambiguous
bd views                    # graph roots
bd work 1-1                 # single <project>/bd_work area, band layout
bd current                  # <project>/bd_work (view 1-1)
bd export graph --view 1-1 --out /tmp/bd-graph

# structural edits (substitute real refs)
bd new --parent 1-1 --type breaks_down --band claims --order 0
bd link FROM TO --type supports   # refuses a back-edge or band cycle, sorts targets
bd link FROM TO --type verifies --symmetric --inverse verified_by
bd unlink FROM TO

bd work REF+1               # same area, first N descendant levels only
bd current --path           # print that directory; read-only, no build
bd edit REF                 # path of a ref in the active view
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
- [`docs/DESIGN.md`](docs/DESIGN.md) — model, decisions, invariants, migration.
- [`docs/BRANCHES-AND-VERSIONS.md`](docs/BRANCHES-AND-VERSIONS.md) — the
  branch/version separation contract.
- [`docs/GRAPH.md`](docs/GRAPH.md) — the one topology: typed structural and
  symmetric links, relative bands and absolute stages, audit and export.
- [`docs/GRAPH-LAYOUT.md`](docs/GRAPH-LAYOUT.md) — the band/subpath layout
  algorithm: band inference from structural links, the `band_order` hint,
  nesting, tie-breaks, diagnostics, worked examples, command map, and test map.
- [`docs/breakdown/`](docs/breakdown/) — product breakdown as a second `bd`
  project (store `docs/breakdown/.bd_tree/`). Run `bd graph --root docs/breakdown`,
  or `bd work 1-1` from that directory.
