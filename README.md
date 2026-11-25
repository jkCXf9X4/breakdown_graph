# breakdown tree — `bd`

A flat markdown store for layered project information, with typed dependency
edges, a git solution boundary, and a single custom symlink work area.

- **Store** — one markdown file per node version, keyed by `<id>-<version>`.
- **One topology: typed links.** A node declares edges in its body as
  `[[TYPE, REF]]` tokens; `bd link` writes the same token into a trailing
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
- **Work area** — `bd work` renders one view as a flat set of symlinks into the
  store, in a single `<project>/bd_work/` area. `bd current` reports which view
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
- **Layout: `bd work`.** One writable symlink area at `<project>/bd_work/`;
  `bd work REF` switches its contents to another view. Read-only `bd export`
  projections (graph, context, dot, svg) may be many and are disposable; none is
  a copy.
- **Versions are not a third axis.** Every node file is `<id>-<version>.md`;
  `5-1` and `5-2` are peer alternatives for logical node `5` inside the
  checked-out branch. Versions give no isolation and never cross a branch; git
  still owns every branch decision.
  [The full separation](docs/BRANCHES-AND-VERSIONS.md).

A store-level `ROOT` file names one default anchor (`bd root 1-1`), so
`graph`, `find`, `work`, `check`, `stale`, and `reconcile` follow it without an
argument. An explicit ref wins where a command takes one; with no `ROOT`, the
store uses the lowest member of its first component. `bd check --view REF` only
narrows reporting. The default anchor and the view in the work area are
separate: `bd root REF` changes the default used by commands, while `bd work REF`
replaces the contents of `<project>/bd_work/`; the area keeps its view until you
run `bd work` again.

A ref in data is always the full `id-version` (`5-1`, not `5`); link tokens
and `ROOT` never hold a bare id. At the command line a bare id is a selector:
`bd show 5` resolves `5` to the version present in the selected view and never
writes the short form into data.

Links are declared in the node body, not in front matter. A token is
`[[TYPE, REF]]`, optionally followed by `(TITLE)`: authors write it inside a
sentence, and `bd new`, `bd link`, and `bd migrate` maintain a trailing
`## Links` section of `- [[TYPE, REF]](TITLE)` lines. `REF` is a full
`id-version`; `TITLE` is a cached copy of the target's live title and is
advisory — rendering always uses the live title, and only `bd check` compares
the cache (`link-title-stale`). A back-reference is an ordinary authored token
in the other node: if `3-1` writes `[[verifies, 8-1]]`, `8-1` authors its own
token with its own type. In-edges are still derived by reversing authored
tokens and are marked `[derived]` by `bd in`.

Git answers what changed. Typed edges answer what belongs and what depends.
Pins answer whether it still holds. Freshness pins live in one top-level
`freshness:` map keyed by target ref, not on individual links.

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

The repository ships a small example at `examples/`, the default store (`ROOT`
`1-1`). Read it first; do not edit it unless you mean to change the example.

```sh
export BD_ROOT=examples

bd check                       # 12 nodes, 0 errors, 0 warnings
bd audit                       # graph validation: 0 errors, 0 warnings
bd graph                       # rings 0..4 from 1-1
bd graph --svg --out /tmp/bd-graph.svg  # rendered SVG (needs Graphviz)
bd graph 1-1 --depth 1         # rings 0 and 1
bd graph 1-1 --distance 2:3    # ring 0 plus rings 2 and 3
bd out 1-1                     # authored out-edges, sorted
bd in 4-1                      # derived in-edges for a two-parent node
bd path 10-1                   # shortest undirected chain from 1-1
bd views                       # component representatives
bd find links --limit 3
bd work 1-1                    # single flat work area for the component
bd current                     # <project>/bd_work (view 1-1)
bd export graph --view 1-1 --out /tmp/bd-graph
```

`bd graph` is the only view renderer: text rings by default, `--dot` for
Graphviz DOT, `--svg` for a rendered image. `bd export graph` writes the same
flat view as a read-only snapshot (node files plus one ring-section `INDEX.md`),
never a work area. `bd work` materializes the same view with symlinks.

`bd work` writes the single `<project>/bd_work/` area and replaces its contents;
node `.md` files there are symlinks into the store at their store basename, while
`INDEX.md`, `AGENTS.md`, and `REFS.md` are generated. Use `bd edit REF` to find
a ref in the active view.

## Create a store

```sh
mkdir my-graph && cd my-graph
bd init
bd new --parent 1-1 --field title="Why does this exist?"
bd new --parent 1-1 --field title="What is true?"
bd graph 1-1
bd work 1-1
```

`bd init` creates `.bd_tree/nodes/1-1.md` as the graph root, writes a
`.gitignore` entry for `bd_work/`, and prints the next commands. There is no
`--graph` flag; the graph is the only topology. `bd init DIR` scaffolds the same
layout inside `DIR`.

`bd new` allocates the next global id at version 1 and appends a typed token to
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
`link-title-stale`, and `invalid-freshness`. Cycles, back-edges, and reciprocal edges are legal and
produce no error. A node that still declares `contains` fails `bd check` with
`contains-removed`, which tells you to run `bd migrate`.

## Migration

`bd migrate` converts an older store in place. It still renames classic bare
`nodes/<id>.md` files to `<id>-<version>.md`, and also converts a containment
store to the one topology:

1. Every `contains: [c0, c1, ...]` becomes a typed body token
   `[[T, c0]]` in a trailing `## Links` section, preserving order; the key is
   removed. `T` is `--type`, default `breaks_down`.
2. Front-matter `links` moves into the same section as `- [[TYPE, REF]](TITLE)`
   lines, sorted by ref; a stale scalar link gains an explicit type. Per-link
   `pinned`/`propagates` values move to the top-level `freshness:` map.
3. Retired placement keys are stripped from every node (`band`, `subpath`,
   `layer`, `stage`, `order`) and from the ROOT node (`band_layout`,
   `band_order`). `section` stays as inert front matter.

```sh
bd migrate --dry-run           # print the plan, touch nothing
bd migrate                     # apply atomically
bd check                       # the converted store passes
```

`--root` works as on every command. `--type` chooses the edge type for converted
`contains` lists. There is no placement flag: rings are derived from the graph.

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
  the store-level default-anchor ref.
- An ancestor store or `.bd_root` always wins over a store found below the
  current directory.
- Several stores below the current directory are a refusal: `bd` lists all of
  them and asks for `--root PATH`, `BD_ROOT=PATH`, or a `.bd_root` pointer.
- If the store is nested, set `BD_ROOT=path/to/project` (or its store root),
  pass `--root`, or add a `.bd_root` pointer.
- One store per checkout. A git worktree has its own store.

The example project is at `examples/`, with its store at `examples/.bd_tree/`.
Two stores sit below the repo root, so the repo root holds a committed `.bd_root`
naming `examples`; `docs/` holds one naming `breakdown`, and `docs/breakdown/`
finds its own store first. Plain `bd` therefore works from anywhere in the
checkout. `BD_ROOT=examples` and `--root` still override.

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
bd check | bd show | bd find | bd path | bd views
bd graph | bd out | bd in | bd audit
```

Edit and structure:

```
bd init | bd new | bd link | bd unlink | bd migrate
```

`bd new` seeds empty `title` and `summary`; `--field` overrides them. It appends
a typed token to `--parent` and takes no placement flags. Without `--parent` the
node starts its own component.

`bd link FROM TO --type T` appends a `- [[T, TO]](TITLE)` line to FROM's
`## Links` section in call order; existing lines are untouched, so add targets
in ascending order or re-sort the section (`graph-unsorted-links` warns).
Back-edges,
reciprocal edges, and cycles are legal; a self-loop on the same ref is refused.
`--propagates` records the edge in FROM's `freshness:` map and pins the target's
current body hash; the pin is refreshed by `bd reconcile`.

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
anchor. The view is always the whole component of one ref; the work area may
materialize only rings `0..N` with `REF+N` (the same suffix `bd show` uses) or
`--depth N`, where `0` is the anchor alone and `--depth` overrides a suffix.
`REFS.md`, `INDEX.md`, and `AGENTS.md` carry the materialized expression
(`REF+N`), so `bd current` and `bd edit` recover it. A rebuild with a different
depth replaces the area.
`bd current` is read-only and prints `<project>/bd_work (view <ref>)`; `--path`
prints only the path and `--view` only the ref, and it errors when no area
exists. `--status` and `--writeback` inspect the view actually in the area, not
the requested or default view. `bd views` lists component representatives,
marking the store default with `*` and the work-area anchor. `bd edit REF`
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
bd solution new | bd solution list | bd solution remove
```

Versions (node-local alternatives inside one branch):

```
bd versions | bd clone | bd replace | bd delete | bd diff
```

`bd clone REF` copies a ref to the next free version of the same logical id
(or to `--version N`) and keeps the source file's link tokens; it wires
nothing into the current view. `bd clone REF --subtree` clones the whole weakly
connected component and rewrites each cloned node's token refs; `--depth N`
narrows that to rings `0..N` and implies `--subtree`. Edges whose targets were cloned
are rewired to the copies; a depth prefix keeps edges that leave the prefix
pointing at the originals. The original stays untouched; `--version` cannot be
combined with `--subtree` or `--depth`.
`bd replace OLD NEW` is the separate wiring step: it repoints every inbound link.
It repoints `ROOT` when OLD is the store root; OLD's file stays as a peer. To
clone and swap in one logical flow, run `bd clone REF --subtree` then
`bd replace REF <printed new root ref>`. If OLD is not in the default view,
`bd replace` errors. Several parents are legal, and a view warns when two
versions of one id are reachable (`graph-duplicate-version`). Edges pin a full
ref. Switch the default anchor with `bd root`, or switch the work-area view with
`bd work`.
`bd delete REF` removes a version and refuses an effective `ROOT` or a ref that
is an inbound target of any link unless `--force` is given.

Freshness:

```
bd stale | bd reconcile
```

Read-only projections:

```
bd export graph --view REF --out DIR
bd export context --view REF --out DIR
bd export dot --view REF --out FILE [--render svg|png|pdf ...]
bd export svg --view REF --out FILE
```

`bd export graph` is the read-only component projection: flat node files plus
one ring-section `INDEX.md`. `context` is the fresh-node agent pack; `dot` and
`svg` render the flat graph with Graphviz.

```sh
bd export dot --view 1-1 --out graph.dot --render svg   # graph.dot + graph.svg
bd export svg --view 1-1 --out graph.svg                # rendered only
```

`--render` repeats for `svg`, `png`, or `pdf`; each file sits next to the `.dot`
unless `--render-out` names the one rendered path. `bd graph --svg` remains the
ring visual.

Full syntax: [`docs/CHEATSHEET.md`](docs/CHEATSHEET.md) or `bd <command> --help`.

## Repository layout

```
pyproject.toml             packaging metadata and the `bd` console script
src/bd_tree/               Python package
  loader.py                filename grammar, store index, component view
  model.py                 Node, Store, View, Neighbor, Edge, Issue
  checker.py               structural validation, including contains-removed
  graph.py                 components, rings, audit, flat graph export
  exporter.py              graph/context/dot projections
  freshness.py             pins, stale edges, reconcile
  navigate.py              show/find/path renderers
  work.py                  single flat work area, current/views/edit, status, writeback
  solutions.py             git worktree wrapper
  ops.py                   init, new, structural edits, versions, delete, diff, migrate
  cli.py, api.py           command line and public API
tests/                     pytest suite
examples/                  graph example: .bd_tree/ store + ignored bd_work/
docs/                      user, developer, design, branches/versions
docs/breakdown/            product breakdown: bd store (.bd_tree/) + ignored bd_work/
```

## Status

- The committed example project `examples/` is a twelve-node graph:
  `.bd_tree/nodes/` holds `<id>-<version>.md` files whose bodies carry typed
  link tokens, `.bd_tree/ROOT` names `1-1`, and `bd_work/` is gitignored;
  `bd audit` is clean. From `1-1` the rings are `0: 1-1`, `1: 2-1 3-1`,
  `2: 4-1 5-1 6-1 7-1`, `3: 8-1 12-1`, `4: 9-1 10-1 11-1`.
- One topology. `contains` is rejected by `bd check` (`contains-removed`);
  `bd migrate` converts an older store. Front-matter `links` is retired too:
  a node that still declares it is `links-removed`, and `bd migrate` moves it
  into body tokens.
- No JSON, TOML, lock, or state data files; the only exceptions are a
  store-level `ROOT` file with one ref line and a folder-level `.bd_root`
  pointer with one store path. The work-area view is in its generated `REFS.md`.
  Derived output is gitignored.
- Structural edits, the flat ring work area, and the `bd solution` wrapper are
  in place.

## Known limits

- Node versions do not sync across branches. Use git merges for solutions;
  versions are for alternatives inside one branch.
- No three-way merge between versions. Synthesis is manual.
- Distance is graph nearness, not semantic importance or reading order.
- One worktree per solution. Switching branches inside one worktree can leave a
  layout pointing at paths absent from the new branch; rebuild with
  `bd work REF --clean` and run `bd work --status`.
- Some editors replace symlinks instead of writing through them. Use
  `bd work --status` / `bd work --writeback`.
- Work folders rely on symlinks; Windows needs developer mode or elevated rights.
- No generic importer or CI configuration yet; `bd migrate` converts a classic
  bare-file store and a containment store in place.
