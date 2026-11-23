# breakdown tree — `bd`

A flat markdown store for layered project information, with a git solution
boundary, typed dependency edges, and a single custom symlink work area.

- **Store** — one markdown file per node version, keyed by `<id>-<version>`.
- **Structure — topology per store.** A graph store declares parent→child edges in
  `links`; bands are relative `layer` paths, ordered and nested from cross-band
  edges, or absolute integer `stage`s when a node declares one. A containment
  store declares an ordered `contains` list of full refs. Paths do not define
  either. Detection: containment when any node declares `contains`; otherwise
  graph when any node has `links`, `stage`, or a non-empty `layer`.
- **Root** — an optional `ROOT` file names the default view root in one full ref.
- **Solutions** — git branches and worktrees.
- **Layout** — `bd work` renders one view as symlinks into the store, in a
  single `<project>/bd_work/` area: band layout for a graph store (path layers,
  with inferred nesting and explicit subpaths), `section` placement for a
  containment store. `bd current` reports which view is there.
- **Freshness** — typed links record what depends on what and whether it still holds.
- **Graph is the default example** — `examples/` is a ten-node relative-layer
  graph with `ROOT` `1-1`, path layers such as `claims/structural`, and no
  `group`. [Graph topology](docs/GRAPH.md), [layout algorithm](docs/GRAPH-LAYOUT.md).
  Containment remains supported; see [`docs/breakdown/`](docs/breakdown/).

The store is the data; the work area is a disposable layout. An agent session
reads exactly one view and edits the node files through that one area.

## Two axes

These are deliberately separate:

- **Solution boundary: git.** A branch and worktree hold one solution. Git decides
  when it is merged or discarded.
- **Merge unit: the flat `nodes/` store.** One file per node version keeps a
  conflict local to the version that changed.
- **Layout: `bd work`.** One writable symlink area at `<project>/bd_work/`;
  `bd work REF` switches its contents to another view. Read-only `bd export`
  projections (tree, context, dot, graph) may be many and are disposable; none
  is a copy.
- **Versions are not a third axis.** Every node file is `<id>-<version>.md`;
  `5-1` and `5-2` are peer alternatives for logical node `5` inside the
  checked-out branch. Versions give no isolation and never cross a branch; git
  still owns every branch decision.
  [The full separation](docs/BRANCHES-AND-VERSIONS.md).

A store-level `ROOT` file names one default view root (`bd root 1-1`), so
`tree`, `find`, `work`, `check`, `stale`, and `reconcile` follow it without an
argument. An explicit ref wins where a command takes one; with no `ROOT`, a
graph store uses its lowest graph root and a containment store its lowest
`(id, version)`. `bd check --view REF` only narrows reporting.
The default root and the view in the work area are separate: `bd root REF`
changes the default used by commands, while `bd work REF` replaces the contents
of `<project>/bd_work/`; the area keeps its view until you run `bd work` again.

A ref in data is always the full `id-version` (`5-1`, not `5`); `contains`,
`links`, and `ROOT` never hold a bare id. At the command line a bare id is a
selector: `bd show 5` resolves `5` to the version present in the selected view
and never writes the short form into data.

Git answers what changed. `contains` and `links` answer what belongs and what
depends. Pins answer whether it still holds.

## Install

Requirements: Python 3.10+, PyYAML; pytest only for the test suite; Graphviz
`dot` only for dot export. The distribution is `breakdown-tree`, the import
package `bd_tree`, the command `bd`.

```sh
git clone https://github.com/jkCXf9X4/breakdown-tree
cd breakdown-tree
pip install .                 # or: pip install -e '.[test]'
python3 -m pytest -q          # the suite passes
bd --help
```

Without installing, run from the repository root:
`PYTHONPATH=src python3 -m bd_tree --help`.

## Five-minute tour

The repository ships a small graph example at `examples/`, the default store
(`ROOT` `1-1`). Read it first; do not edit it unless you mean to change the
example.

```sh
export BD_ROOT=examples

bd check                       # 10 nodes, 0 errors, 0 warnings
bd audit                       # graph validation: 0 errors, 0 warnings
bd tree 1-1                    # derived band layout
bd graph                       # text render with layer bands from 1-1
bd graph --svg --out /tmp/bd-graph.svg  # rendered SVG (needs Graphviz)
bd graph 1-1 --depth 1         # direct children only
bd out 1-1                     # authored out-edges, sorted
bd in 4-1                      # derived in-edges for a two-parent node
bd find links --limit 3
bd work 1-1                    # single work area, derived band layout
bd export graph --view 1-1 --out /tmp/bd-graph
bd export tree 1-1 --out /tmp/bd-tree
```

The export is a read-only snapshot (band directories, one `INDEX.md` per band,
and a root index), never a work area. In a graph store `bd work` and
`bd export tree` materialize the same band layout; `bd export graph` is the
same projection with per-band indexes.

Containment is still fully supported. To see a live containment tree, point
`bd` at the product breakdown store:

```sh
bd --root docs/breakdown check
bd --root docs/breakdown tree 1-1 --depth 1
bd --root docs/breakdown work 1-1
cd "$(bd --root docs/breakdown current --path)"
```

`bd work` writes the single `<project>/bd_work/` area and replaces its contents;
node `.md` files there are symlinks into the store, while `INDEX.md`, `AGENTS.md`,
and `REFS.md` are generated. Use `bd edit REF` to find a ref in the active view.

## Create a store

```sh
mkdir my-graph && cd my-graph
bd init
bd new --parent 1-1 --field title="What is true?" --field layer=claims
bd new --parent 1-1 --field title="Why does this exist?" --field layer=intent
bd tree 1-1
bd work 1-1
```

`bd init` creates `.bd_tree/nodes/1-1.md` as a containment root (`contains: []`),
writes a `.gitignore` entry for `bd_work/`, and prints the next commands.
`bd init DIR` scaffolds the same layout inside `DIR`. A graph store is the same
flat files with no `contains` anywhere and parent→child `links`; bands are
relative `layer` paths by default, or absolute integer `stage`s when a node
declares one (older stores). `bd init --graph` writes a relative-band root
(`layer: root`, no `stage`). `examples/` is the shipped graph. `bd new` allocates
the next global id at version 1. In a containment store it appends the full ref
to the parent's `contains`; in a graph store it adds a typed link (`--type`,
default `breaks_down`) and takes `--layer BAND[/SUB]` in relative mode
(required) or `--stage` in absolute mode, plus `--order`. It prefills `title`
and `summary` as empty placeholders, and `--field` overrides them. Front matter
is arbitrary: use `status`, `phase`, `audience`, or anything else.

Graph validation has two code sets. Relative mode reports
`graph-layer-missing`, `graph-layer-invalid`, `graph-layer-cycle`, and
`graph-order-back-edge`; absolute mode reports `graph-stage-missing`,
`graph-stage-invalid`, and `graph-back-edge`. Both share `graph-order-invalid`,
`graph-dangling-link`, and `graph-cycle`; graph warnings include
`graph-group-ignored` (`group` is inert) and `graph-unsorted-links`.

A classic store with bare `nodes/<id>.md` files is converted once, in place:

```sh
bd migrate --dry-run           # print the plan
bd migrate                     # rename bare files and rewrite data refs
```

## Where is my store?

`bd` walks up from the current directory looking for a store: `nodes/` or
`.bd_tree/nodes/`. At each directory a store there wins; otherwise a `.bd_root`
pointer there names the store. If neither appears upward, it scans below the
current directory to depth 3 and uses the store when exactly one is found.

- Project layout: `.bd_tree/` at the project root; `bd` accepts the project root
  or the store root.
- Classic layout: `nodes/` at the repo root; the project root is that directory.
- `.bd_root` is a one-line pointer a working folder may hold to name its store;
  a relative path is resolved from the folder holding the file. It is the
  folder-level way to choose among several stores. `ROOT` is a different file:
  the store-level default-view ref.
- An ancestor store or `.bd_root` always wins over a store found below the
  current directory.
- Several stores below the current directory are a refusal: `bd` lists all of
  them and asks for `--root PATH`, `BD_ROOT=PATH`, or a `.bd_root` pointer.
- If the store is nested, set `BD_ROOT=path/to/project` (or its store root),
  pass `--root`, or add a `.bd_root` pointer.
- One store per checkout. A git worktree has its own store.

The example project is at `examples/`, with its graph store at
`examples/.bd_tree/`. Two stores sit below the repo root, so the repo root holds
a committed `.bd_root` naming `examples`; `docs/` holds one naming `breakdown`,
and `docs/breakdown/` finds its own store first. Plain `bd` therefore works from
anywhere in the checkout. `BD_ROOT=examples` and `--root` still override.

## Choose your path

| I want to… | Read |
| --- | --- |
| Set up and use a store for the first time | [`docs/GETTING-STARTED.md`](docs/GETTING-STARTED.md) |
| Look up a command quickly | [`docs/CHEATSHEET.md`](docs/CHEATSHEET.md) |
| Understand the model and decisions | [`docs/DESIGN.md`](docs/DESIGN.md) |
| Work in the graph topology | [`docs/GRAPH.md`](docs/GRAPH.md) |
| Understand graph folder layout | [`docs/GRAPH-LAYOUT.md`](docs/GRAPH-LAYOUT.md) |
| Know what is a branch and what is a version | [`docs/BRANCHES-AND-VERSIONS.md`](docs/BRANCHES-AND-VERSIONS.md) |
| Change the tool itself | [`docs/DEVELOPING.md`](docs/DEVELOPING.md) |
| Work safely as an agent | [`AGENTS.md`](AGENTS.md) |

## Command map

Inspect:

```
bd check | bd tree | bd show | bd find | bd path | bd views
bd graph | bd out | bd in | bd audit          # graph store
```

Edit and structure:

```
bd init | bd new | bd link | bd unlink | bd migrate
bd contain | bd uncontain                     # containment stores only
```

`bd new` seeds empty `title` and `summary`; `--field` overrides them. In a graph
store it adds a typed link and takes `--layer`/`--stage` and `--order`; in a
containment store it appends to the parent's `contains`.

Root:

```
bd root [REF] [--clear]
```

Layout:

```
bd work [REF[+N]] [--depth N] [--path-template T] [--status] [--writeback] [--clean]
bd current [--path|--view]
bd views
bd edit REF
```

`bd work REF` writes the single `<project>/bd_work/` area and replaces its
contents; it does not create a second folder. With no REF it uses the default
view. The view is always the full closure of one ref over the store's child
relation; the work area may materialize only its first `N` descendant levels
with `REF+N` (the same suffix `bd show`/`bd tree` use) or `--depth N`, where `0`
is the root alone and `--depth` overrides a suffix. In a graph store a level is
a link hop and the layout is the graph bands (derived layers or absolute
stages). `REFS.md`, each folder's `INDEX.md`, and `AGENTS.md` carry the
materialized expression (`REF+N`), so `bd current` and `bd edit` recover it. A
rebuild with a different depth replaces the area. `bd current` is read-only and
prints `<project>/bd_work (view <ref>)`; `--path` prints only the path and
`--view` only the ref, and it errors when no area exists. `--status` and
`--writeback` inspect the view actually in the area, not the
requested or default view. `bd views` lists topology roots (containment roots
or graph roots), marking the store default with `*`. `bd edit REF` prints
the absolute path of that ref inside the current work area and errors if the ref
is not in the materialized area.

In a containment store, `section` is the only presentation key that creates
directories. A node with `section: true` opens a directory named by its
placement name (explicit `name`, else the `title` slug, else the ref), and its
containment descendants nest inside it; `section: "<dir>"` names the directory
verbatim, slashes included.
A leading `/` resolves the directory from the output root instead of under the
parent prefix, so a containment chain can keep layers as siblings.
The section node's own file is `<dir>/<placement-name>.md`, and nested sections
stack. Otherwise a node is placed by explicit `name` (`<name>.md`), else
`<ref>-<title-slug>.md`, else `<ref>.md` when there is no usable title; the
title slug is lowercase kebab-case. `--path-template` opts out of section
inheritance and overrides the whole area; `{name}` and `{slug}` in a template
are the explicit `name`, else the title slug, else the ref.

`folder` is ordinary front matter: preserved, never read, and it affects no
placement, naming, validation, or warning.

Every directory in the work area and in `bd export tree` gets a generated
`INDEX.md` listing its direct node files, then its immediate subfolders. It is
derived from placement and `contains` order on every build, so it cannot go
stale. The names `INDEX.md`, `AGENTS.md`, and `REFS.md` are reserved in every
directory.

Solutions:

```
bd solution new | bd solution list | bd solution remove
```

Versions (node-local alternatives inside one branch):

```
bd versions | bd clone | bd replace | bd delete | bd diff
```

`bd clone REF` copies a ref to the next free version of the same logical id
(or to `--version N`) and keeps the source file's declared `contains`; it wires
nothing into the current view. `bd clone REF --subtree` clones every
descendant: in a containment store it rewrites each cloned parent's `contains`,
and in a graph store it copies the forward link closure and rewrites each
cloned parent's `links`. The copy is self-contained and the original stays
untouched; `--version` cannot be combined with `--subtree`.
`bd replace OLD NEW` is the separate wiring step: in a containment store it
puts NEW at OLD's index in its parent's `contains`; in a graph store it repoints
every inbound link. It repoints `ROOT` when OLD is the store root; OLD's file
stays as a peer. To clone and swap in one logical flow, run
`bd clone REF --subtree` then `bd replace REF <printed new root ref>`. If OLD is
not in the default view, `bd replace` errors. Multiple parents is an error in a
containment store; a graph edge may have several parents, and a view warns when
two versions of one id are reachable (`graph-duplicate-version`). A containment
view uses the version its parent's `contains` names; a graph edge pins a full
ref. To choose a different containment position, run `bd uncontain P OLD`, then
`bd contain P NEW --before NEXT`.
Switch the default root with `bd root`, or switch the work-area view with
`bd work`.
`bd delete REF` removes a version and refuses a `ROOT`, a reachable ref, or one
referenced by any `contains`/`links` unless `--force` is given.

Freshness:

```
bd stale | bd reconcile
```

Read-only projections:

```
bd export tree REF --out DIR
bd export context|graph --view REF --out PATH
bd export dot --view REF --out FILE [--render svg|png|pdf ...]
bd export svg --view REF --out FILE
```

`bd export tree REF --out DIR` is the single read-only topology projection: band
layout for a graph store (derived layers or absolute stages),
`section`/`contains` placement for a containment store,
with one generated `INDEX.md` per folder. `export graph` is the same projection
written as a band snapshot; `context` is the other export choice.

```sh
bd export dot --view 1-1 --out graph.dot --render svg   # graph.dot + graph.svg
bd export svg --view 1-1 --out graph.svg                # rendered only
```

`--render` repeats for `svg`, `png`, or `pdf`; each file sits next to the `.dot`
unless `--render-out` names the one rendered path. `bd graph --svg` remains the
band-clustered visual.

Full syntax: [`docs/CHEATSHEET.md`](docs/CHEATSHEET.md) or `bd <command> --help`.

## Repository layout

```
pyproject.toml             packaging metadata and the `bd` console script
src/bd_tree/               Python package
  loader.py                filename grammar, store index, topology view resolution
  model.py                 Node, Store.model, View, Edge, Issue
  checker.py               structural validation; dispatches per topology
  graph.py                 graph adjacency, band/layer layout, audit, graph export
  exporter.py              tree/context/dot projections
  freshness.py             pins, stale edges, reconcile
  navigate.py              show/tree/find/path
  work.py                  single work area, current/views/edit, status, writeback
  solutions.py             git worktree wrapper
  ops.py                   init, new, structural edits, versions, delete, diff, migrate
  cli.py, api.py           command line and public API
tests/                     pytest suite
examples/                 graph example: .bd_tree/ store + ignored bd_work/
docs/                      user, developer, design, branches/versions
docs/breakdown/            product breakdown: bd store (.bd_tree/) + ignored bd_work/
```

## Status

- The suite passes: `python3 -m pytest -q`.
- The committed example project `examples/` is a graph store: `.bd_tree/nodes/`
  holds ten `<id>-<version>.md` files with declared `links` and relative `layer`s,
  `.bd_tree/ROOT` names `1-1`, and `bd_work/` is gitignored; `bd audit` is clean.
- No JSON, TOML, lock, or state data files; the only exceptions are a
  store-level `ROOT` file with one ref line and a folder-level `.bd_root`
  pointer with one store path. Derived output is gitignored.
- Structural edits, the git-aware single work area, and the `bd solution` wrapper
  are in place.

## Known limits

- Node versions do not sync across branches. Use git merges for solutions;
  versions are for alternatives inside one branch.
- No three-way merge between versions. Synthesis is manual.
- One worktree per solution. Switching branches inside one worktree can leave a
  layout pointing at paths absent from the new branch; rebuild with
  `bd work REF --clean` and run `bd work --status`.
- Some editors replace symlinks instead of writing through them. Use
  `bd work --status` / `bd work --writeback`.
- Work folders rely on symlinks; Windows needs developer mode or elevated rights.
- No generic importer or CI configuration yet; `bd migrate` only converts a
  classic bare-file store in place.
