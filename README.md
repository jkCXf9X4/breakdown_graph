# breakdown graph — `bdg`

A flat markdown store for layered project information, with typed dependency
edges, a git solution boundary, and a single custom symlink work area.

- **Store** — one markdown file per node version, keyed by `<id>-<version>`.
- **One topology: typed links.** A node declares edges in its body as
  `[[REF, TYPE]]` tokens; `bdg link` writes the same token into a trailing
  `## Links` section. There is no second topology and no `contains` key.
  In-edges are derived by reversing authored tokens.
- **View — undirected.** The view is the weakly connected component of one
  anchor: every node reachable through authored links in either direction.
  Direction stays in the data and as a label; it does not filter membership.
  Cycles and back-edges are legal.
- **Layout — rings.** Ordering is the undirected BFS hop count from the anchor.
  Ring 0 is the anchor; ring 1 is split into children and parents; deeper rings
  are numbered. Distance is derived on every command.
- **Root** — an optional `ROOT` file names the default anchor in one full ref.
- **Solutions** — git branches and worktrees.
- **Work area** — `bdg work` renders one view as a flat set of symlinks into the
  store, in a single `<project>/bdg_work/` area. `bdg current` reports which view
  is there.
- **Freshness** — typed links record what depends on what and whether it still
  holds.

The store is the data; the work area is a disposable layout. An agent session
reads exactly one view and edits the node files through that one area.

## Two axes

These are deliberately separate:

- **Solution boundary: git.** A branch and worktree hold one solution. Git decides
  when it is merged or discarded.
- **Merge unit: the flat `nodes/` store.** One file per node version keeps a
  conflict local to the version that changed.
- **Layout: `bdg work`.** One writable symlink area at `<project>/bdg_work/`;
  `bdg work REF` switches its contents to another view. Read-only `bdg pack`
  projections and `bdg graph --format` renders may be many and are disposable;
  none is a writable work area.
- **Versions are not a third axis.** Every node file is `<id>-<version>.md`;
  `5-1` and `5-2` are peer alternatives for logical node `5` inside the
  checked-out branch. Versions give no isolation and never cross a branch; git
  still owns every branch decision.
  [The full separation](docs/BRANCHES-AND-VERSIONS.md).

A store-level `ROOT` file names one default anchor (`bdg root 1-1`), so
`graph`, `find`, `work`, `check`, and `stale` follow it without an argument. An
explicit ref wins where a command takes one; with no `ROOT`, the
store uses the lowest member of its first component. `bdg check --view REF` only
narrows reporting. The default anchor and the view in the work area are
separate: `bdg root REF` changes the default used by commands, while `bdg work REF`
replaces the contents of `<project>/bdg_work/`; the area keeps its view until you
run `bdg work` again.

A ref in data is always the full `id-version` (`5-1`, not `5`); link tokens
and `ROOT` never hold a bare id. At the command line a bare id is a selector:
`bdg show 5` resolves `5` to the version present in the selected view and never
writes the short form into data.

Links are declared in the node body, not in front matter. A token is
`(TITLE)[[REF, TYPE]]`: the cached title is a prefix, with optional spaces
between `)` and `[[`, and authors write only the bare `[[REF, TYPE]]`.
`bdg new`, `bdg link`, `bdg replace`, `bdg migrate`, and `bdg retitle` write the
title; `bdg new`, `bdg link`, and `bdg migrate` also maintain a trailing
`## Links` section of `- (TITLE)[[REF, TYPE]]` lines. `REF` is a full
`id-version`; `TITLE` is
tool-generated from the target's live title and is never hand-maintained.
Rendering always uses the live title; `bdg check` compares the cache exactly
(`link-title-stale`) or warns when a token is bare (`inline-title-missing`),
and `bdg retitle` regenerates every cache in scope. A back-reference is an
ordinary authored token in the other node: if `3-1` writes
`[[8-1, verifies]]`, `8-1` authors its own token with its own type. In-edges
are still derived by reversing authored tokens and are marked `[derived]` by
`bdg in`.

Git answers what changed. Typed edges answer what belongs and what depends.
Pins answer whether it still holds. Freshness pins live in one top-level
`freshness:` map keyed by target ref, not on individual links.

## Install

Requirements: Python 3.10+, PyYAML; pytest only for the test suite; Graphviz
`dot` only for graph rendering. The distribution is `breakdown-graph`, the import
package `bdg`, the command `bdg`.

```sh
git clone https://github.com/jkCXf9X4/breakdown_graph
cd breakdown_graph
pip install .                 # or: pip install -e '.[test]'
python3 -m pytest -q          # the suite passes
bdg --help
```

Without installing, run from the repository root:
`PYTHONPATH=src python3 -m bdg --help`.

Prebuilt wheels and sdists are attached to each
[release](https://github.com/jkCXf9X4/breakdown_graph/releases); install one with
`pip install <path-or-url-to-wheel>`.

## Five-minute tour

The repository ships a small example at `examples/`, the default store (`ROOT`
`1-1`). Read it first; do not edit it unless you mean to change the example.

```sh
export BDG_ROOT=examples

bdg check                       # 12 nodes, 0 errors, 0 warnings
bdg stale                       # stale or untracked propagating edges
bdg graph                       # rings 0..4 from 1-1
bdg graph --format svg --out /tmp/bdg-graph.svg  # rendered SVG (needs Graphviz)
bdg graph 1-1 --depth 1         # rings 0 and 1
bdg graph 1-1 --rings 2:3       # ring 0 plus rings 2 and 3
bdg out 1-1                     # authored out-edges, sorted
bdg in 4-1                      # derived in-edges for a two-parent node
bdg path 10-1                   # shortest undirected chain from 1-1
bdg views                       # component representatives
bdg find links --limit 3
bdg work 1-1                    # single flat work area for the component
bdg current                     # <project>/bdg_work (view 1-1)
bdg pack 1-1 --out /tmp/bdg-graph
```

`bdg graph` is the only view renderer: text rings by default, `--format dot` for
Graphviz DOT, `--format svg` for a rendered image. `bdg pack` writes the same
flat view as a disposable copy (node files plus one ring-section `INDEX.md`),
never a work area. `bdg work` materializes the same view with symlinks.

`bdg work` writes the single `<project>/bdg_work/` area and replaces its contents;
node `.md` files there are symlinks into the store at their store basename, while
`INDEX.md`, `AGENTS.md`, and `REFS.md` are generated. Use `bdg edit REF` to find
a ref in the active view.

## Create a store

```sh
mkdir my-graph && cd my-graph
bdg init
bdg new --parent 1-1 --field title="Why does this exist?"
bdg new --parent 1-1 --field title="What is true?"
bdg graph 1-1
bdg work 1-1
```

`bdg init` creates `bdg_graph/nodes/1-1.md` as the graph root, writes a
`.gitignore` entry for `bdg_work/`, and prints the next commands. There is no
`--graph` flag; the graph is the only topology. `bdg init DIR` scaffolds the same
layout inside `DIR`.

`bdg new` allocates the next global id at version 1 and appends a typed token to
the parent (`--type`, default `breaks_down`). It takes no placement flags: the view
and its rings are derived from links and distance. Without `--parent` the node
starts its own component. It prefills `title` and `summary` as empty
placeholders, and `--field` overrides them. Front matter is arbitrary: use
`status`, `phase`, `audience`, or anything else.

Graph validation keeps structural and edge checks. The graph codes are
`graph-dangling-link`, `graph-orphan` (a node outside the default component),
`graph-duplicate-version`, `graph-wide-fanout`, and `graph-unsorted-links`.
The loader and body scanner add `links-removed` (a node still declares
front-matter `links`), `inline-malformed`, `inline-duplicate`,
`inline-title-missing`, `link-title-stale`, and `invalid-freshness`. Cycles,
back-edges, and reciprocal edges are legal and produce no error. A node that
still declares `contains` fails `bdg check` with `contains-removed`, which tells
you to run `bdg migrate`.

## Migration

`bdg migrate` converts an older store in place. It still renames classic bare
`nodes/<id>.md` files to `<id>-<version>.md`, and also converts a containment
store to the one topology:

1. Every `contains: [c0, c1, ...]` becomes a typed body token
   `[[c0, T]]` in a trailing `## Links` section, preserving order; the key is
   removed. `T` is `--type`, default `breaks_down`.
2. Front-matter `links` moves into the same section as
   `- (TITLE)[[REF, TYPE]]` lines, sorted by ref; a stale scalar link gains an
   explicit type. Legacy suffix tokens `[[TYPE, REF]](TITLE)` or
   `[[REF, TYPE]](TITLE)` become the prefix form `(TITLE)[[REF, TYPE]]`, and
   missing titles are filled from the target.
   Per-link `pinned`/`propagates` values move to the top-level `freshness:` map.
3. Retired placement keys are stripped from every node (`band`, `subpath`,
   `layer`, `stage`, `order`) and from the ROOT node (`band_layout`,
   `band_order`). `section` stays as inert front matter.

```sh
bdg migrate --dry-run           # print the plan, touch nothing
bdg migrate                     # apply atomically
bdg retitle                     # refresh every cached title from live titles
bdg check                       # the converted store passes
```

`--root` works as on every command. `--type` chooses the edge type for converted
`contains` lists. There is no placement flag: rings are derived from the graph.

## Where is my store?

`bdg` walks up from the current directory looking for a store: `nodes/` or
`bdg_graph/nodes/`. At each directory a store there wins; otherwise a `.bdg_root`
pointer there names the store. If neither appears upward, it scans below the
current directory to depth 3 and uses the store when exactly one is found.

- Project layout: `bdg_graph/` at the project root; `bdg` accepts the project root
  or the store root.
- Classic layout: `nodes/` at the repo root; the project root is that directory.
- `.bdg_root` is a one-line pointer a working folder may hold to name its store;
  a relative path is resolved from the folder holding the file. It is the
  folder-level way to choose among several stores. `ROOT` is a different file:
  the store-level default-anchor ref.
- An ancestor store or `.bdg_root` always wins over a store found below the
  current directory.
- Several stores below the current directory are a refusal: `bdg` lists all of
  them and asks for `--root PATH`, `BDG_ROOT=PATH`, or a `.bdg_root` pointer.
- If the store is nested, set `BDG_ROOT=path/to/project` (or its store root),
  pass `--root`, or add a `.bdg_root` pointer.
- One store per checkout. A git worktree has its own store.

The example project is at `examples/`, with its store at `examples/bdg_graph/`.
Two stores sit below the repo root, so the repo root holds a committed `.bdg_root`
naming `examples`; `docs/` holds one naming `breakdown`, and `docs/breakdown/`
finds its own store first. Plain `bdg` therefore works from anywhere in the
checkout. `BDG_ROOT=examples` and `--root` still override.

## Choose your path

| I want to… | Read |
| --- | --- |
| Set up and use a store for the first time | [`docs/GETTING-STARTED.md`](docs/GETTING-STARTED.md) |
| Look up a command quickly | [`docs/CHEATSHEET.md`](docs/CHEATSHEET.md) |
| Understand the model and decisions | [`docs/DESIGN.md`](docs/DESIGN.md) |
| Work in the graph topology | [`docs/GRAPH.md`](docs/GRAPH.md) |
| Understand the ring layout and work area | [`docs/GRAPH-LAYOUT.md`](docs/GRAPH-LAYOUT.md) |
| Know what is a branch and what is a version | [`docs/BRANCHES-AND-VERSIONS.md`](docs/BRANCHES-AND-VERSIONS.md) |
| Change the tool itself | [`docs/DEVELOPING.md`](docs/DEVELOPING.md) |
| Work safely as an agent | [`AGENTS.md`](AGENTS.md) |

## Command map

Inspect:

```
bdg check | bdg show | bdg find | bdg path | bdg views
bdg graph | bdg out | bdg in
```

Edit and structure:

```
bdg init | bdg new | bdg link | bdg unlink | bdg migrate | bdg retitle
```

`bdg new` seeds empty `title` and `summary`; `--field` overrides them. It appends
a typed token to `--parent` and takes no placement flags. Without `--parent` the
node starts its own component.

`bdg link FROM TO --type T` appends a `- (TITLE)[[TO, T]]` line to FROM's
`## Links` section in call order, writing the target's live title; existing
lines are untouched, so add targets in ascending order or re-sort the section
(`graph-unsorted-links` warns). Back-edges, reciprocal edges, and cycles are
legal; a self-loop on the same ref is refused. `--propagates` records the edge
in FROM's `freshness:` map and pins the target's current body hash; the pin is
refreshed by `bdg stale --fix`.

`bdg retitle [REF] [--dry-run]` regenerates every cached title in
scope: the whole store by default, or the view of `REF`. Each cache is
set from its target's live title; tokens whose target cannot be resolved are
left untouched. It prints `retitled N tokens in M nodes`, or
`would retitle N tokens in M nodes` with `--dry-run`.

Root:

```
bdg root [REF] [--clear]
```

Layout:

```
bdg work [REF[+N]] [--depth N] [--path-template T] [--clean] [--repair]
bdg current [--path|--view|--status]
bdg views
bdg edit REF
```

`bdg work REF` writes the single `<project>/bdg_work/` area and replaces its
contents; it does not create a second folder. With no REF it uses the default
anchor. The view is always the whole component of one ref; the work area may
materialize only rings `0..N` with `REF+N` (the same suffix `bdg show` uses) or
`--depth N`, where `0` is the anchor alone and `--depth` overrides a suffix.
`REFS.md`, `INDEX.md`, and `AGENTS.md` carry the materialized expression
(`REF+N`), so `bdg current` and `bdg edit` recover it. A rebuild with a different
depth replaces the area.
`bdg current` is read-only and prints `<project>/bdg_work (view <ref>)`; `--path`
prints only the path and `--view` only the ref, and it errors when no area
exists. `bdg current --status` and `bdg work --repair` inspect the view actually
in the area, not the requested or default view. `bdg views` lists component
representatives, marking the store default with `*` and the work-area anchor.
`bdg edit REF`
prints the absolute path of that ref inside the current work area and errors if
the ref is not in the materialized area.

The work area is flat: one symlink per node at its store basename.
`--path-template` overrides the whole area; placeholders are `{ref}`, `{id}`,
`{version}`, `{distance}`, `{slug}`, `{title}`, plus any front-matter key.
`{slug}` is the title slug, else the ref.
`group`, `section`, `folder`, and `home` are inert front matter: preserved,
never read, and they affect no path.

`INDEX.md` is one generated file at the work-area root, with ring sections. Its
`nodes:` front-matter path points at the store's real `nodes/` folder, and every
node entry also links straight to its real file. `REFS.md` is the sorted
path/ref/kind/distance/title table and carries the active view in its header.
`AGENTS.md` records the editing rules and, inside git, the branch, commit, and
worktree. The names `INDEX.md`, `AGENTS.md`, and `REFS.md` are reserved in every
directory.

Solutions:

```
bdg solution new | bdg solution list | bdg solution remove
```

Versions (node-local alternatives inside one branch):

```
bdg versions | bdg clone | bdg replace | bdg delete | bdg diff
```

`bdg clone REF` copies a ref to the next free version of the same logical id
(or to `--version N`) and keeps the source file's link tokens; it wires
nothing into the current view. `bdg clone REF --subtree` clones the whole weakly
connected component and rewrites each cloned node's token refs; `--depth N`
narrows that to rings `0..N` and implies `--subtree`. Edges whose targets were cloned
are rewired to the copies; a depth prefix keeps edges that leave the prefix
pointing at the originals. The original stays untouched; `--version` cannot be
combined with `--subtree` or `--depth`.
`bdg replace OLD NEW` is the separate wiring step: it repoints every inbound
link and sets each rewritten token's cached title to NEW's live title. It
repoints `ROOT` when OLD is the store root; OLD's file stays as a peer. To
clone and swap in one logical flow, run `bdg clone REF --subtree` then
`bdg replace REF <printed new root ref>`. If OLD is not in the default view,
`bdg replace` errors. Several parents are legal, and a view warns when two
versions of one id are reachable (`graph-duplicate-version`). Edges pin a full
ref. Switch the default anchor with `bdg root`, or switch the work-area view with
`bdg work`.
`bdg delete REF` removes a version and refuses an effective `ROOT` or a ref that
is an inbound target of any link unless `--force` is given.

Freshness:

```
bdg stale [--fix]
```

Read-only projections:

```
bdg pack REF --out DIR
bdg pack REF --fresh --out DIR
bdg graph REF --format text|dot|svg [--out PATH]
```

`bdg pack` is the disposable copy: every node as a regular file plus one
ring-section `INDEX.md`. `--fresh` writes only fresh nodes, plus `AGENTS.md` and
`STALE.md`, for an agent that must not write. `bdg graph --format dot|svg`
renders the graph with Graphviz; `text` is the ring view.

```sh
bdg graph 1-1 --format dot --out graph.dot   # Graphviz source
bdg graph 1-1 --format svg --out graph.svg   # rendered image
```

`--format svg` pipes the DOT through Graphviz `dot`, so it needs the `dot`
binary on `PATH`.

Three projections cover the same store: `bdg work` (writable symlinks into the
store), `bdg pack` (a disposable regular-file copy), and `bdg graph --format`
(a string render written to `--out` or stdout). Only `bdg work` is writable;
the other two are never a second work area.

Full syntax: [`docs/CHEATSHEET.md`](docs/CHEATSHEET.md) or `bdg <command> --help`.

## Repository layout

```
pyproject.toml             packaging metadata and the `bdg` console script
src/bdg/                   Python package
  loader.py                filename grammar, store index, component view
  model.py                 Node, Store, View, Neighbor, Edge, Issue
  checker.py               structural validation, including contains-removed
  graph.py                 components, rings, checks, flat graph paths
  exporter.py              pack projections (graph and fresh context)
  freshness.py             pins, stale edges, pin repair
  navigate.py              show/find/path renderers
  work.py                  single flat work area, current/views/edit, status, repair
  solutions.py             git worktree wrapper
  ops.py                   init, new, structural edits, versions, delete, diff, migrate
  cli.py, api.py           command line and public API
tests/                     pytest suite
examples/                  graph example: bdg_graph/ store + ignored bdg_work/
docs/                      user, developer, design, branches/versions
docs/breakdown/            product breakdown: bdg store (bdg_graph/) + ignored bdg_work/
```

## Status

- The committed example project `examples/` is a twelve-node graph:
  `bdg_graph/nodes/` holds `<id>-<version>.md` files whose bodies carry typed
  link tokens, `bdg_graph/ROOT` names `1-1`, and `bdg_work/` is gitignored;
  `bdg check` is clean. From `1-1` the rings are `0: 1-1`, `1: 2-1 3-1`,
  `2: 4-1 5-1 6-1 7-1`, `3: 8-1 12-1`, `4: 9-1 10-1 11-1`.
- One topology. `contains` is rejected by `bdg check` (`contains-removed`);
  `bdg migrate` converts an older store. Front-matter `links` is retired too:
  a node that still declares it is `links-removed`, and `bdg migrate` moves it
  into body tokens.
- No JSON, TOML, lock, or state data files; the only exceptions are a
  store-level `ROOT` file with one ref line and a folder-level `.bdg_root`
  pointer with one store path. The work-area view is in its generated `REFS.md`.
  Derived output is gitignored.
- Structural edits, the flat ring work area, and the `bdg solution` wrapper are
  in place.

## Known limits

- Node versions do not sync across branches. Use git merges for solutions;
  versions are for alternatives inside one branch.
- No three-way merge between versions. Synthesis is manual.
- Distance is graph nearness, not semantic importance or reading order.
- One worktree per solution. Switching branches inside one worktree can leave a
  layout pointing at paths absent from the new branch; rebuild with
  `bdg work REF --clean` and inspect it with `bdg current --status`.
- Some editors replace symlinks instead of writing through them. Use
  `bdg current --status` / `bdg work --repair`.
- Work folders rely on symlinks; Windows needs developer mode or elevated rights.
- No generic importer or CI configuration yet; `bdg migrate` converts a classic
  bare-file store and a containment store in place.
