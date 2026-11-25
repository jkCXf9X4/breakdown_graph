# Agent operating rules

This repository is both a tool (`bd_tree`, command `bd`) and a reference example
project. Read [`README.md`](README.md) and [`docs/DESIGN.md`](docs/DESIGN.md)
before changing behaviour. The design document is authoritative for the model;
this file is the short operating protocol.

## First session

1. Locate the store: plain `bd` works from the repo root because the committed
   `.bd_root` pointer names `examples` (the project root; the store is
   `examples/.bd_tree`, an undirected graph with `ROOT` `1-1`). Equivalent:
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
   `bd in 4-1`, `bd views`. The default example is one component of twelve nodes
   (`1-1`..`12-1`), rings 0 through 4 from `1-1`; run the commands in
   `examples/README.md`.
4. For a solution: `bd solution new NAME`, `cd` into the printed worktree
   project directory, then `bd work` with the printed default-view ref.
5. For edits: prefer `bd edit REF` for the path inside `bd_work/`; direct edits
   to `.bd_tree/nodes/<ref>.md` are an escape hatch only. Change structure with
   `bd link` / `bd unlink`. There is no `contain`/`uncontain`: `contains` is
   retired and `bd migrate` converts an older store.
6. Validate: `bd check` validates the store and its selected view; `bd audit`
   is the explicit graph audit. Run `bd stale` too.

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
- A ref is the full `id-version` (`5-1`, not `5`). Link tokens and `ROOT` hold
  full refs only; a bare ref in data is a `check` error (`bare-ref`). A bare id
  on the command line is a selector resolved inside the selected view; it is
  never written to data.
- There is one topology: typed body tokens `[[TYPE, REF]]`, optionally with a
  cached `(TITLE)`. In-edges are derived by reversing authored tokens; nothing
  else is marked `[derived]`. A back-reference is an authored token in the other
  node, with its own type. `contains` and front-matter `links` are not data: a
  node that still declares either fails `bd check` (`contains-removed`,
  `links-removed`); `bd migrate` converts it.
- **A view is undirected.** It is the weakly connected component of its anchor
  over authored links, walked in both directions. Membership is not directional;
  multiple parents, reciprocal edges, back-edges, and cycles are legal.
- **Distance is the ordering primitive.** It is the undirected BFS hop count
  from the anchor. Ring 0 is the anchor; ring 1 is split into `children` and
  `parents`; deeper rings are numbered. Every emitted list sorts by an explicit
  key; the canonical key is
  `(distance, kind_rank, link type, id, version)` with
  `child: 0, parent: 1`.
- **Direction is a label, not a filter.** `→` child, `←` parent.
  `bd out`/`bd in` stay directional; `bd graph`, `bd show`, `bd work`, and
  `bd find` use the whole component. `bd clone --subtree` copies the
  undirected neighbourhood (optionally rings `0..N` via `--depth`) and rewires
  links among the copies.
- **No placement keys.** There is no authored position, ordinal, or ROOT layout
  hint. `group`, `section`, `folder`, and `home` are ordinary inert front matter.
  Add no schema unless a project asks for one.
- Front matter is otherwise arbitrary; only the identity/freshness keys
  (`id`, `legacy`, `freshness`) are reserved. The link assertion is the body
  token grammar; `(TITLE)` is an advisory cache of the target's live title. Two
  forms are legal: inline in prose, and `- [[TYPE, REF]](TITLE)` lines in a
  trailing `## Links` section. `name` and `title` are presentation metadata;
  `title` supplies the template slug. A node's path in the work area is the
  store file's basename unless `--path-template` overrides it.
- A self-loop on one ref is refused by `bd link`. A back-edge, a reciprocal
  edge, and a longer cycle are legal and produce no error.
- Git owns the solution boundary: one branch/worktree per solution. The flat store
  is the merge unit; `bd work` is a layout inside one checkout, never a branch
  mechanism.
- **The work area is flat.** Node `.md` files are symlinks at their store
  basename in `<project>/bd_work/`; `INDEX.md`, `AGENTS.md`, and `REFS.md` are
  regular generated files. Those three names are reserved in every directory.
  Never copy node content into a work folder and never introduce a sync layer.
- A project has exactly one writable work area, `<project>/bd_work/`. It holds
  one view at a time; `bd work REF` replaces its contents. Read-only `bd export`
  snapshots (graph, context, dot, svg) are not a second work area.
- **The active node is the work area's view ref in `REFS.md`**, in the header
  `# References — view REF[+N]`. `bd current`, `bd edit`, `--status`, and
  `--writeback` read it. There is no extra state file.
- A view never crosses a branch, and neither does a version. Versions are node
  files inside one checkout; branches are git. Never resolve a ref through a
  branch name, never add a branch or per-node active-version selector, and never
  copy a node across branches — merge first.
- Edges pin full refs, and a view warns (`graph-duplicate-version`) when two
  versions of one id are reachable. There is no per-node pointer.
- No JSON, TOML, lock, or state data files. Two exceptions, both one line of
  text: a store-level `ROOT` file holding one ref (e.g. `1-1`), and a
  folder-level `.bd_root` pointer holding one store path, naming the store a
  working folder belongs to. Nothing else goes in either file. Derived output is
  disposable and gitignored. Writers serialize on a transient advisory lock in
  the system temp directory; it never enters the store or git.
- The default anchor is `ROOT` when present, else the lowest member of the first
  component; an explicit ref where a command takes one wins over both.
  `bd check --view REF` only narrows reporting. A declared but missing ref is
  `root-ref-missing`; malformed content is `invalid-root`. This default is
  separate from the view held by the work area, which changes only with
  `bd work REF`.

## Where to work

- Solutions: `bd solution new NAME` (thin wrapper over
  `git worktree add ../NAME -b NAME`); one worktree per solution.
- Writable layout: `bd work REF` writes the single `<project>/bd_work/` area;
  a different REF replaces its contents. `bd work REF+N` (or `--depth N`)
  materializes only rings `0..N` — the view stays the whole component, the area
  holds a ring prefix. `bd current` reports the area and its view, including
  `+N`; `--path` and `--view` narrow the output, and it errors if no area
  exists.
- Agent sessions work in that one area and read exactly one view. Switch with
  `bd work REF` (drop the `+N` to materialize the whole view); never keep
  parallel work folders side by side. `--status` and `--writeback` inspect the
  view actually in the area, not the requested or default view. `bd views` lists
  component representatives and marks the store default and the work-area anchor.
- Find and edit inside the area: `bd edit REF` prints the absolute path of a ref
  in the active view and errors if it is absent.
- Read-only snapshots: `bd export graph --view REF --out DIR`, or another
  `bd export` choice; they are disposable exports, never the work area.
- Switching trees: `bd root REF` changes the store default anchor, `bd work REF`
  changes the work-area view, or clone and swap with `bd clone REF` then
  `bd replace REF NEW`. `bd replace` repoints inbound links, or repoints `ROOT`
  when REF is the root, and leaves the old file as a peer. These are the only
  switches; edges pin full refs.
- Never hand-edit generated `INDEX.md`, `AGENTS.md`, or `REFS.md` inside a work
  or output directory.

## Common tasks

| Task | Command |
| --- | --- |
| New store | `bd init DIR` (graph root, no placement key) |
| Add a node | `bd new [--parent REF] [--type breaks_down] [--field K=V ...]`; no parent starts a new component |
| Clone and replace a node | `bd clone OLD` then `bd replace OLD NEW` |
| Replace a version in place | `bd replace OLD NEW` |
| Add an edge | `bd link FROM TO --type supports [--propagates]`; appends a token to the source, cycles and back-edges legal |
| Add a back-reference | `bd link TO FROM --type supported_by`; author it on the other node, never a derived opposite |
| Remove an edge | `bd unlink FROM TO [--type T]` |
| Browse the graph | `bd graph [REF] [--depth N] [--distance A:B] [--type T]` |
| Read a node and rings | `bd show REF+2 --max-chars 800` (rings 0..2) |
| Shortest chain | `bd path REF` (shortest undirected path from the anchor) |
| Search | `bd find TEXT`, `bd find 'RE' --regex`; add `--view REF` or `--all` |
| Show the work area | `bd current [--path\|--view]` |
| List components | `bd views` |
| Switch/edit the work area | `bd work REF[+N]`, then open `bd edit REF` |
| Repair symlinks | `bd work --status` / `bd work --writeback` |
| Switch the default anchor | `bd root REF`, `bd root --clear` |
| Show versions | `bd versions ID`, `bd delete REF` |
| Clone a node or component | `bd clone REF [--version N] [--subtree] [--depth N]` |
| New solution | `bd solution new NAME` |
| Convert an old store | `bd migrate [--dry-run] [--type T]` (`contains`, front-matter `links`, classic bare files, retired placement keys) |
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
bd graph 1-1                # rings 0..4 from 1-1
bd graph                    # same view from ROOT 1-1
bd graph 1-1 --distance 2:3 # ring 0 plus rings 2 and 3
bd out 1-1                  # authored out-edges, sorted
bd in 4-1                   # derived in-edges
bd path 10-1                # shortest undirected chain from 1-1
bd views                    # component representatives
bd work 1-1                 # single flat <project>/bd_work area
bd current                  # <project>/bd_work (view 1-1)
bd work 1-1+1               # same area, rings 0..1 only
bd export graph --view 1-1 --out /tmp/bd-graph
bd export context --view 1-1 --out /tmp/bd-context

# structural edits (substitute real refs)
bd new --parent 1-1 --type breaks_down --field title="A new claim"
bd link FROM TO --type supports   # legal even as a back-edge or cycle
bd link TO FROM --type supported_by   # back-reference: authored on the other node
bd unlink FROM TO

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
  explicitly rewrites them. Token maintenance may add or remove `## Links`
  lines; `bd replace` and `bd clone --subtree` rewrite token refs in place.

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
- [`docs/GRAPH.md`](docs/GRAPH.md) — the one topology: typed body tokens,
  undirected views, rings, audit, and export.
- [`docs/GRAPH-LAYOUT.md`](docs/GRAPH-LAYOUT.md) — component membership, BFS
  rings, direction labels, tie-breaks, flat work area, worked examples, command
  map, and test map.
- [`docs/breakdown/`](docs/breakdown/) — product breakdown as a second `bd`
  project (store `docs/breakdown/.bd_tree/`). Run `bd graph --root docs/breakdown`,
  or `bd work 1-1` from that directory.
