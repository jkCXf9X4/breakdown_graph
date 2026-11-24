# breakdown tree — `bd`

A flat markdown store for layered project information, with typed dependency
edges, a git solution boundary, and a single custom symlink work area.

- **Store** — one markdown file per node version, keyed by `<id>-<version>`.
- **One topology: typed links.** A node declares edges in `links: [{to, type}]`.
  There is no second topology and no `contains` key. A link is *structural* by
  default; a link with `symmetric: true` is one authored master whose opposite
  is derived at load time (see below).
- **Layout — bands.** A node names a `band`, plus an optional `subpath`, and the
  band order and nesting are derived from cross-band structural links; or a node
  declares an absolute integer `stage`. `order` positions nodes inside a band,
  and a ROOT `band_order` list is an optional tie-break hint. Paths do not
  define structure.
- **Root** — an optional `ROOT` file names the default view root in one full ref.
- **View** — the closure of one ref over authored *structural* out-links. A node
  reached by several parents appears once; multiple parents are legal.
- **Solutions** — git branches and worktrees.
- **Work area** — `bd work` renders one view as symlinks into the store, in a
  single `<project>/bd_work/` area. `bd current` reports which view is there.
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

A store-level `ROOT` file names one default view root (`bd root 1-1`), so
`graph`, `find`, `work`, `check`, `stale`, and `reconcile` follow it without an
argument. An explicit ref wins where a command takes one; with no `ROOT`, the
store uses its lowest graph root. `bd check --view REF` only narrows reporting.
The default root and the view in the work area are separate: `bd root REF`
changes the default used by commands, while `bd work REF` replaces the contents
of `<project>/bd_work/`; the area keeps its view until you run `bd work` again.

A ref in data is always the full `id-version` (`5-1`, not `5`); `links` and
`ROOT` never hold a bare id. At the command line a bare id is a selector:
`bd show 5` resolves `5` to the version present in the selected view and never
writes the short form into data.

Structural links define structure; symmetric links are associative and derive
an opposite. A link is structural unless it declares `symmetric: true`, and only
structural links expand a view, define `path` ancestry and `views` roots, order
bands, and feed `bd clone --subtree`. A symmetric master is authored on exactly
one node — `X --T--> Y` — and load derives the opposite `Y --(inverse or T)--> X`
without storing it; `bd out`, `bd in`, and the `show --links` footer mark
derived edges `[derived]`. Because one file
owns the relation, there is nothing to keep in sync and no second copy to merge.

Git answers what changed. `links` answer what belongs and what depends. Pins
answer whether it still holds.

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
bd graph                       # text render with derived band layout from 1-1
bd graph --svg --out /tmp/bd-graph.svg  # rendered SVG (needs Graphviz)
bd graph 1-1 --depth 1         # direct children only
bd out 1-1                     # authored out-edges, sorted
bd in 4-1                      # derived in-edges for a two-parent node
bd find links --limit 3
bd work 1-1                    # single work area, derived band layout
bd export graph --view 1-1 --out /tmp/bd-graph
```

`bd graph` is the only view renderer: text bands by default, `--dot` for
Graphviz DOT, `--svg` for a rendered image. `bd export graph` writes the same
band layout as a read-only snapshot (band directories, one `INDEX.md` per
folder, and a root index), never a work area. `bd work` materializes the same
layout with symlinks.

`bd work` writes the single `<project>/bd_work/` area and replaces its contents;
node `.md` files there are symlinks into the store, while `INDEX.md`, `AGENTS.md`,
and `REFS.md` are generated. Use `bd edit REF` to find a ref in the active view.

## Create a store

```sh
mkdir my-graph && cd my-graph
bd init
bd new --parent 1-1 --field title="Why does this exist?" --band intent
bd new --parent 1-1 --field title="What is true?" --band claims
bd graph 1-1
bd work 1-1
```

`bd init` creates `.bd_tree/nodes/1-1.md` as the graph root (`band: root`),
writes a `.gitignore` entry for `bd_work/`, and prints the next commands. There
is no `--graph` flag; the graph is the only topology. `bd init DIR` scaffolds
the same layout inside `DIR`.

`bd new` allocates the next global id at version 1 and adds a typed link to the
parent (`--type`, default `breaks_down`). In relative mode it takes `--band` with
optional `--subpath` (or the older `--layer BAND[/SUB]`); in absolute mode it
takes `--stage`; both take `--order`. It prefills `title` and `summary` as empty
placeholders, and `--field` overrides them. Front matter is arbitrary: use
`status`, `phase`, `audience`, or anything else.

Graph validation has two code sets. Relative mode reports `graph-layer-missing`,
`graph-layer-invalid`, `graph-layer-cycle`, and `graph-order-back-edge`; absolute
mode reports `graph-stage-missing`, `graph-stage-invalid`, and `graph-back-edge`.
Both share `graph-order-invalid`, `graph-dangling-link`, and `graph-cycle`; graph
warnings include `graph-group-ignored` (`group` is inert) and
`graph-unsorted-links`. Symmetric links add `invalid-symmetric`,
`inverse-without-symmetric`, `symmetric-self-edge`, `duplicate-symmetric-edge`,
and `propagates-on-symmetric`; a non-list ROOT `band_order` is
`invalid-band-order`. A node that still declares `contains` fails `bd check`
with `contains-removed`, which tells you to run `bd migrate`.

## Migration

`bd migrate` converts an older store in place. It still renames classic bare
`nodes/<id>.md` files to `<id>-<version>.md`, and now also converts a
containment store to the one topology:

1. Every `contains: [c0, c1, ...]` becomes `links: [{to: c0, type: T}, ...]`,
   preserving order; the key is removed. `T` is `--type`, default `breaks_down`.
2. Sibling order is preserved by writing `order: i` for converted children that
   have no explicit `order`.
3. A `section` path on a node with no `band` becomes `band` plus `subpath` (a
   leading ordinal such as `00-` is dropped); `section` itself stays as inert
   front matter.

```sh
bd migrate --dry-run           # print the plan, touch nothing
bd migrate                     # apply atomically
bd check                       # the converted store passes
```

`--root` works as on every command. `--type` chooses the edge type for converted
`contains` lists. Three additions also run on an already-migrated store and are
idempotent:

- `--symmetric TYPE` (repeatable) sets `symmetric: true` on every link of that
  type, and drops `propagates`/`pinned` from it.
- `--inverse TYPE=TYPE2` (repeatable) does the same and names the derived
  opposite's type.
- `--band-order` writes the ROOT `band_order` hint (`root` first, then bands
  whose `section` has a leading `NN` ordinal by number, then remaining
  section-derived bands in first-seen order) and sets `band_layout: flat`.

```sh
bd migrate --symmetric verifies --inverse verifies=verified_by --band-order
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
| Understand the band folder layout | [`docs/GRAPH-LAYOUT.md`](docs/GRAPH-LAYOUT.md) |
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

`bd new` seeds empty `title` and `summary`; `--field` overrides them. It adds a
typed link and takes `--band`/`--subpath` (or `--layer`), `--stage`, and
`--order`.

`bd link FROM TO --type T` adds a structural edge and refuses a back-edge or a
band cycle. `--symmetric` instead authors the single master of a two-way
relation, and `--inverse T2` names the derived opposite's type; a symmetric link
skips the band/stage ordering checks and cannot combine with `--propagates`.

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
view. The view is always the full closure of one ref over forward structural
links; the work area may materialize only its first `N` descendant levels with
`REF+N` (the
same suffix `bd show` uses) or `--depth N`, where `0` is the root alone and
`--depth` overrides a suffix. A level is a link hop and the layout is the band
plan (derived bands, or absolute stages). `REFS.md`, each folder's `INDEX.md`,
and `AGENTS.md` carry the materialized expression (`REF+N`), so `bd current` and
`bd edit` recover it. A rebuild with a different depth replaces the area.
`bd current` is read-only and prints `<project>/bd_work (view <ref>)`; `--path`
prints only the path and `--view` only the ref, and it errors when no area
exists. `--status` and `--writeback` inspect the view actually in the area, not
the requested or default view. `bd views` lists graph roots, marking the store
default with `*`. `bd edit REF` prints the absolute path of that ref inside the
current work area and errors if the ref is not in the materialized area.

Bands are the only layout. A node lands in its band's folder, plus an explicit
`subpath`; a top-level band folder is `<NN>-<slug(band)>`. The file stem is an
explicit `name` (`<name>.md`), else `<ref>-<title-slug>.md`, else `<ref>.md` when
there is no usable title; the title slug is lowercase kebab-case. `--path-template`
overrides the whole area; `{name}` and `{slug}` in a template are the explicit
`name`, else the title slug, else the ref. The ROOT node may add
`band_order: [band, ...]` to break ties in the topological band order (and so
order flat top-level folders); it never overrides a real edge constraint, and
unknown or duplicate names are ignored. It composes with `band_layout: flat`:
same top-level folders, ordered by the hint.

`section` is inert front matter: preserved, never read, and it affects no path.
`folder` is likewise ordinary front matter: preserved, never read, and it
affects no placement, naming, validation, or warning.

Every directory in the work area and in `bd export graph` gets a generated
`INDEX.md` listing its direct node files, then its immediate subfolders. It is
derived from the band plan on every build, so it cannot go stale. The names
`INDEX.md`, `AGENTS.md`, and `REFS.md` are reserved in every directory.

Solutions:

```
bd solution new | bd solution list | bd solution remove
```

Versions (node-local alternatives inside one branch):

```
bd versions | bd clone | bd replace | bd delete | bd diff
```

`bd clone REF` copies a ref to the next free version of the same logical id
(or to `--version N`) and keeps the source file's declared `links`; it wires
nothing into the current view. `bd clone REF --subtree` clones every descendant
in the structural forward closure and rewrites each cloned parent's `links`. The
copy is self-contained and the original stays untouched; `--version` cannot be
combined with `--subtree`.
`bd replace OLD NEW` is the separate wiring step: it repoints every inbound link.
It repoints `ROOT` when OLD is the store root; OLD's file stays as a peer. To
clone and swap in one logical flow, run `bd clone REF --subtree` then
`bd replace REF <printed new root ref>`. If OLD is not in the default view,
`bd replace` errors. Several parents are legal, and a view warns when two
versions of one id are reachable (`graph-duplicate-version`). Edges pin a full
ref. Switch the default root with `bd root`, or switch the work-area view with
`bd work`.
`bd delete REF` removes a version and refuses a `ROOT`, a reachable ref, or one
referenced by any link unless `--force` is given.

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

`bd export graph` is the read-only topology projection: the band layout (derived
relative bands, or absolute stages) with one generated `INDEX.md` per folder.
`context` is the fresh-node agent pack; `dot` and `svg` render the flat graph
with Graphviz.

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
  loader.py                filename grammar, store index, view resolution
  model.py                 Node, Store, View, Edge, Issue
  checker.py               structural validation, including contains-removed
  graph.py                 adjacency, band layout, audit, graph export
  exporter.py              graph/context/dot projections
  freshness.py             pins, stale edges, reconcile
  navigate.py              show/find/path renderers
  work.py                  single work area, current/views/edit, status, writeback
  solutions.py             git worktree wrapper
  ops.py                   init, new, structural edits, versions, delete, diff, migrate
  cli.py, api.py           command line and public API
tests/                     pytest suite
examples/                  graph example: .bd_tree/ store + ignored bd_work/
docs/                      user, developer, design, branches/versions
docs/breakdown/            product breakdown: bd store (.bd_tree/) + ignored bd_work/
```

## Status

- The committed example project `examples/` is a relative-band graph:
  `.bd_tree/nodes/` holds twelve `<id>-<version>.md` files with declared `links`
  and relative `band`/`subpath` values, `.bd_tree/ROOT` names `1-1`, and
  `bd_work/` is gitignored; `bd audit` is clean.
- One topology. `contains` is rejected by `bd check` (`contains-removed`);
  `bd migrate` converts an older store. Symmetric links author one master and
  derive the opposite at load; structural links alone define closure and layout.
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
- No generic importer or CI configuration yet; `bd migrate` converts a classic
  bare-file store and a containment store in place.
