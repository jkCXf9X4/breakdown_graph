# Agent operating rules

This repository is both a tool (`bd_tree`, command `bd`) and a reference example
project. Read [`README.md`](README.md) and [`docs/DESIGN.md`](docs/DESIGN.md)
before changing behaviour. The design document is authoritative for the model;
this file is the short operating protocol.

## First session

1. Locate the store: plain `bd` works from the repo root because the committed
   `.bd_root` pointer names `examples` (the project root; the store is
   `examples/.bd_tree`, a graph example with `ROOT` `1-1`). Equivalent:
   `export BD_ROOT=examples`, or pass `--root`. Install once from the clone with
   `pip install -e '.[test]'`, then use `bd`. Without installing, run from the
   repo root with `PYTHONPATH=src python3 -m bd_tree`.
2. Confirm the baseline:

   ```sh
   python3 -m pytest -q
   bd audit
   bd check                    # 10 nodes, 0 errors, 0 warnings
   ```

3. See the shape: `bd check`, `bd tree 1-1`, `bd graph`, `bd out 1-1`,
   `bd in 4-1`. The default example is a relative-layer graph of ten nodes
   (`1-1`..`10-1`); run the commands in `examples/README.md`.
4. For a solution: `bd solution new NAME`, `cd` into the printed worktree
   project directory, then `bd work` with the printed default-view ref.
5. For edits: prefer `bd edit REF` for the path inside `bd_work/`; direct edits
   to `.bd_tree/nodes/<ref>.md` are an escape hatch only. Change structure with
   `bd link` / `bd unlink` in a graph store; a containment store adds
   `bd contain` / `bd uncontain`.
6. Validate: `bd check` dispatches on the store's topology; `bd audit` adds the
   graph audit. Run `bd stale` in either store.

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
- Topology is detected per store: containment when any node declares
  `contains`; otherwise graph when any node has `links`, `stage`, or a non-empty
  `layer`. A view is the closure of one ref over that store's child relation.
- In a containment store, `contains` is an ordered tree per view, and one view
  holds at most one version per logical id (`duplicate-id`); the chain selects
  what is current. `links` is a DAG and never adds nodes to a view; it keeps an
  outgoing target reachable, and a link to another containment root is not an
  `external-link`. A scalar link (`links: ['10-1']`) takes its type from the
  target node's `type`.
- In a graph store, `links` is the child relation: parent→child full refs,
  typed, with `propagates`/`pinned` preserved. Out-edges are authored, in-edges
  derived. A node with several parents appears once in a view;
  `multiple-parents`, per-view `duplicate-id`, and `external-link` do not apply.
  Bands have two modes. When any node declares `stage` (absolute mode), edges go
  forward (`stage(parent) < stage(child)`); `order` breaks ties inside a stage.
  Otherwise (relative mode, the default example) every node needs a non-empty
  `layer` path: the first segment is the band, later segments are an explicit
  subpath. Band order and nesting come from cross-band edges by the
  shortest-path rule (equal-length branches stay top-level), and `order`
  positions nodes inside a band, where a same-band edge needs
  `order(source) < order(target)`, including across subpaths. See
  [`docs/GRAPH-LAYOUT.md`](docs/GRAPH-LAYOUT.md).
- Front matter is arbitrary; only the identity/containment/link/freshness keys
  (`id`, `legacy`, `contains`, `links`, `to`, `type`, `propagates`, `pinned`)
  and the graph band keys (`layer`, `stage`, `order`, `group`) are reserved. In
  a containment store, `section`, `name`, and `title` are
  presentation fields: work and export paths use `section` to open directories,
  else `<name>.md`, else `<ref>-<title-slug>.md`, else `<ref>.md`.
  `section: true` names the directory by the node's placement name;
  `section: "<dir>"` supplies the base name. Every folder layer is numbered
  zero-based with two digits (`NN-<base>`) in traversal order; an authored
  leading ordinal is stripped, and only the first segment is numbered (inner
  segments are explicit subpaths). A leading `/` numbers from the output root;
  otherwise it numbers under the parent directory. In a graph
  store, the layout is the graph bands instead: relative mode orders them by
  `layer` path (band plus explicit subpath, with inferred nesting) and absolute
  mode by `stage`; `order` positions a node inside its band. `group` is
  ordinary metadata in every topology: it places nothing and the graph audit
  warns `graph-group-ignored`. Presentation only: it changes no identity or
  validation, so it adds no schema. `folder` is ordinary metadata with no effect
  on placement, naming, or validation. `home` has no meaning; it is ordinary
  front matter. Add no schema unless a project asks for one.
- Git owns the solution boundary: one branch/worktree per solution. The flat store
  is the merge unit; `bd work` is a layout inside one checkout, never a branch
  mechanism.
- Work folders are symlink views: node `.md` files are symlinks, while
  `INDEX.md` in every directory, `AGENTS.md`, and `REFS.md` are regular generated
  files. These three names are reserved in every directory. Never copy
  node content into a work folder and never introduce a sync layer.
- A project has exactly one writable work area, `<project>/bd_work/`. It holds
  one view at a time; `bd work REF` replaces its contents. Read-only `bd export`
  snapshots (tree, context, dot, graph) are not a second work area.
- A view never crosses a branch, and neither does a version. Versions are node
  files inside one checkout; branches are git. Never resolve a ref through a
  branch name, never add a branch or per-node active-version selector, and never
  copy a node across branches — merge first.
- In a containment store, the version current in a view is the one its parent's
  `contains` names. In a graph store, edges pin full refs and a view warns
  (`graph-duplicate-version`) when two versions of one id are reachable. There is
  no per-node pointer and no extra state file.
- No JSON, TOML, lock, or state data files. Two exceptions, both one line of
  text: a store-level `ROOT` file holding one ref (e.g. `1-1`), and a
  folder-level `.bd_root` pointer holding one store path, naming the store a
  working folder belongs to. Nothing else goes in either file. Derived output is
  disposable and gitignored. Writers serialize on a transient advisory lock in
  the system temp directory; it never enters the store or git.
- The default view root is `ROOT` when present, else a graph store's lowest
  graph root, else a containment store's lowest node by `(id, version)`; an
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
  closure, the area holds a prefix of it. In a graph store a descendant level is
  a link hop; the layout is the graph bands. `bd current` reports the area and
  its view, including `+N`; `--path` and `--view` narrow the output, and it
  errors if no area exists.
- Agent sessions work in that one area and read exactly one view. Switch with
  `bd work REF` (drop the `+N` to materialize the whole view); never keep
  parallel work folders side by side. `--status` and `--writeback` inspect the
  view actually in the area, not the requested or default view. `bd views` lists
  topology roots (containment roots or graph roots) and marks the store
  default.
- Find and edit inside the area: `bd edit REF` prints the absolute path of a ref
  in the active view and errors if it is absent.
- Read-only snapshots: `bd export tree REF --out DIR`, or another `bd export`
  choice; they are disposable exports, never the work area.
- Switching trees: `bd root REF` changes the store default root, `bd work REF`
  changes the work-area view, or repoint one parent with `bd uncontain` /
  `bd contain` (containment), or clone and swap with `bd clone REF` then
  `bd replace REF NEW`. `bd replace` keeps NEW at REF's index in its parent's
  `contains` (containment), or repoints inbound links (graph), or repoints
  `ROOT` when REF is the root, and leaves the old file as a peer. These are the
  only switches; a containment view uses the version named by its parent's
  `contains`, while graph edges pin full refs.
- Never hand-edit generated `INDEX.md` (one in every directory), `AGENTS.md`, or
  `REFS.md` inside a work or output directory.

## Common tasks

| Task | Command |
| --- | --- |
| New store | `bd init DIR` (containment root; `bd init --graph DIR` writes a relative-band root) |
| Add a node (graph, relative) | `bd new --parent REF --type breaks_down --layer NAME [--order N]` |
| Add a node (graph, absolute) | `bd new --parent REF --type breaks_down --stage N [--order N]` |
| Add a node (containment) | `bd new --parent REF --field title=... --field layer=...` |
| Move a child (containment) | `bd uncontain P C` then `bd contain P C --before REF` |
| Clone and replace a node | `bd clone OLD` then `bd replace OLD NEW` |
| Replace a version in place | `bd replace OLD NEW` |
| Add an edge (graph) | `bd link FROM TO --type supports [--propagates]`; refuses back-edges or a layer cycle, keeps targets sorted |
| Add a semantic edge (containment) | `bd link FROM TO --type supports --propagates` |
| Browse a topology | `bd tree REF` (graph: layer/stage bands; `--depth` bounds containment only) |
| Read a node and children | `bd show REF+2 --max-chars 800` (graph: two link hops) |
| Reverse chain | `bd path REF` (graph: first parent when ambiguous) |
| Search | `bd find TEXT`, `bd find 'RE' --regex`; add `--view REF` or `--all` |
| Show the work area | `bd current [--path\|--view]` |
| List topology roots | `bd views` |
| Switch/edit the work area | `bd work REF[+N]`, then open `bd edit REF` |
| Repair symlinks | `bd work --status` / `bd work --writeback` |
| Switch tree root | `bd root REF`, `bd root --clear` |
| Show versions | `bd versions ID`, `bd delete REF` |
| Clone a node or subtree | `bd clone REF [--version N] [--subtree]` |
| New solution | `bd solution new NAME` |
| Convert a classic store | `bd migrate [--dry-run]` |
| Validate | `bd check`, `bd audit`, `bd stale` |
| Read-only agent pack | `bd export context --view REF --out DIR` |

## Commands

Commands assume `bd` is installed (`pip install -e '.[test]'`); without
installing, prefix each with `PYTHONPATH=src python3 -m bd_tree` instead of `bd`.

```sh
export BD_ROOT=examples
python3 -m pytest -q
bd check                    # 10 nodes, 0 errors, 0 warnings
bd audit                    # graph example: 0 errors, 0 warnings
bd tree 1-1                 # derived band layout
bd graph                    # relative-band graph from ROOT 1-1
bd out 1-1                  # authored out-edges
bd in 4-1                   # derived in-edges
bd path 4-1                 # reverse chain, first parent when ambiguous
bd views                    # topology roots; graph roots
bd work 1-1                 # single <project>/bd_work area, band layout
bd current                  # <project>/bd_work (view 1-1)
bd export tree 1-1 --out /tmp/bd-tree
bd export graph --view 1-1 --out /tmp/bd-graph

# graph structural edits (substitute real refs)
bd new --parent 1-1 --type breaks_down --layer claims --order 0
bd link FROM TO --type supports   # refuses a back-edge or layer cycle, sorts targets
bd unlink FROM TO

# containment support is unchanged; demo it against docs/breakdown
bd --root docs/breakdown check      # 57 nodes
bd --root docs/breakdown tree 1-1 --depth 1
bd --root docs/breakdown show 1-1+1 --max-chars 400
bd contain PARENT CHILD [--before REF]   # containment stores only
bd uncontain PARENT CHILD                # containment stores only

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
- [`docs/DESIGN.md`](docs/DESIGN.md) — model, decisions, invariants.
- [`docs/BRANCHES-AND-VERSIONS.md`](docs/BRANCHES-AND-VERSIONS.md) — the
  branch/version separation contract.
- [`docs/GRAPH.md`](docs/GRAPH.md) — the graph topology: forward links, relative
  layer bands and absolute stages, audit and export, and how graph commands
  dispatch.
- [`docs/GRAPH-LAYOUT.md`](docs/GRAPH-LAYOUT.md) — the layer-path layout
  algorithm: band inference, nesting, tie-breaks, diagnostics, worked examples,
  command map, and test map.
- [`docs/breakdown/`](docs/breakdown/) — product breakdown as a second `bd`
  project (store `docs/breakdown/.bd_tree/`): current state, open work,
  scrutiny, and history. Run `bd tree --root docs/breakdown`, or `bd work 1-1`
  from that directory.
