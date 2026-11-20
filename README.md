# breakdown tree — `bd`

A flat markdown store for layered project information, with a git solution
boundary, typed dependency edges, and a single custom symlink work area.

- **Store** — one markdown file per node, keyed by a running integer.
- **Structure** — an ordered `contains` list defines the tree; paths do not.
- **Root** — an optional `ROOT` file names the default view root in one ref line.
- **Solutions** — git branches and worktrees.
- **Layout** — `bd work` renders one view as symlinks into the store, in a
  single `<project>/bd_work/` area; `bd current` reports which view is there.
- **Freshness** — typed links record what depends on what and whether it still holds.

The store is the data; the work area is a disposable layout. An agent session
reads exactly one view and edits the node files through that one area.

## Two axes

These are deliberately separate:

- **Solution boundary: git.** A branch and worktree hold one solution. Git decides
  when it is merged or discarded.
- **Merge unit: the flat `nodes/` store.** One file per node keeps a conflict
  local to the node that changed.
- **Layout: `bd work`.** One writable symlink area at `<project>/bd_work/`;
  `bd work REF` switches its contents to another view. Read-only projections
  (`bd view`, `bd export`) may be many and are disposable; none is a copy.
- **Versions are not a third axis.** `5-1` is an alternative file for node `5`
  inside the checked-out branch. Versions give no isolation and never cross a
  branch; git still owns every branch decision.
  [The full separation](docs/BRANCHES-AND-VERSIONS.md).

A store-level `ROOT` file names one default view root (`bd root 1-4`), so
`tree`, `ls`, `find`, `grep`, `work`, `check`, `stale`, and `reconcile` follow it
without an argument. An explicit ref wins; with no `ROOT`, the lowest main ref is
the root. The default root and the view in the work area are separate:
`bd root REF` changes the default used by commands, while `bd work REF` replaces
the contents of `<project>/bd_work/`; the area keeps its view until you run
`bd work` again. `bd promote` only copies one version onto main; it is not a
switch.

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

The repository ships a small example project at `examples/`. Read it first; do
not edit it unless you mean to change the example.

```sh
export BD_ROOT=examples

bd check                       # clean, two complete trees
bd tree 1 --depth 1            # the main tree
bd tree 1-1                    # the alternative tree
bd show 1+1 --max-chars 300    # body plus one level
bd ls 1                        # children as a table
bd find Method --limit 3
bd path 3                      # ancestor chain to a leaf
```

Then open the work area:

```sh
bd work 1                      # write <project>/bd_work for view 1
bd current                     # <project>/bd_work (view 1)
cd "$(bd current --path)"      # print only the path, for cd
# node .md files here are symlinks; editing one edits .bd_tree/nodes/<ref>.md
# INDEX.md, AGENTS.md, and REFS.md are regular generated files

bd edit 2                      # absolute path of ref 2 in the active view
bd work 1-1                    # switch the same area to the alternative tree
```

## Create a store

```sh
mkdir my-graph && cd my-graph
bd init
bd new --parent 1 --field title="What is true?" --field layer=claims
bd new --parent 1 --field title="Why does this exist?" --field layer=intent
bd tree 1
bd work 1
```

`bd init` creates `.bd_tree/nodes/1.md`, writes a `.gitignore` entry for
`bd_work/`, and prints the next commands. `bd init DIR` scaffolds the same
layout inside `DIR`. Front matter is arbitrary: use `layer`, `phase`, `status`,
`audience`, or anything else.

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
Two stores sit below the repo root, so the repo root holds a committed
`.bd_root` naming `examples`; `docs/` holds one naming `breakdown`, and
`docs/breakdown/` finds its own store first. Plain `bd` therefore works from
anywhere in the checkout. `BD_ROOT=examples` and `--root` still override.

## Choose your path

| I want to… | Read |
| --- | --- |
| Set up and use a store for the first time | [`docs/GETTING-STARTED.md`](docs/GETTING-STARTED.md) |
| Look up a command quickly | [`docs/CHEATSHEET.md`](docs/CHEATSHEET.md) |
| Understand the model and decisions | [`docs/DESIGN.md`](docs/DESIGN.md) |
| Know what is a branch and what is a version | [`docs/BRANCHES-AND-VERSIONS.md`](docs/BRANCHES-AND-VERSIONS.md) |
| Change the tool itself | [`docs/DEVELOPING.md`](docs/DEVELOPING.md) |
| Work safely as an agent | [`AGENTS.md`](AGENTS.md) |

## Command map

Inspect:

```
bd check | bd tree | bd show | bd ls | bd find | bd grep | bd path
```

Edit and structure:

```
bd init | bd new | bd contain | bd uncontain | bd link | bd unlink
```

Root:

```
bd root [REF] [--clear]
```

Layout:

```
bd work [REF[+N]] [--depth N] [--path-template T] [--status] [--writeback] [--clean] [--print]
bd current [--path|--view]
bd views
bd edit REF
```

`bd work REF` writes the single `<project>/bd_work/` area and replaces its
contents; it does not create a second folder. With no REF it uses the default
view. The view is always the full containment closure of one ref; the work area
may materialize only its first `N` descendant levels with `REF+N` (the same
suffix `bd show`/`bd tree` use) or `--depth N`, where `0` is the root alone and
`--depth` overrides a suffix. `REFS.md`, `INDEX.md`, and `AGENTS.md` carry the
materialized expression (`REF+N`), so `bd current` and `bd edit` recover it. A
rebuild with a different depth replaces the area. `bd current` is read-only and
prints `<project>/bd_work (view <ref>)`;
`--path` prints only the path and `--view` only the ref. `--print` also prints
only the path, is read-only, does not build, and errors when no area exists.
`--status` and `--writeback` inspect the view actually in the area, not the
requested or default view. `bd views` lists containment roots, marking the store
default with `*`. `bd edit REF` prints the absolute path of that ref inside the
current work area and errors if the ref is not in the materialized area.

Placement follows one rule: `folder`/`name`, else
`<ref>-<title-slug>.md`, else `<ref>.md` when there is no usable title. The
title slug is lowercase kebab-case.
`--path-template` overrides the whole area; `{name}` and `{slug}` in a template
are the explicit `name`, else the title slug, else the ref.

Solutions:

```
bd solution new | bd solution list | bd solution remove
```

Versions (node-local alternatives inside one branch):

```
bd versions | bd fork | bd promote | bd retire-version | bd diff
```

`bd fork` materialises the effective `contains` list into the new version.
`bd promote` copies one version onto main; it does not switch trees — use
`bd root` for the default root, `bd work` for the work-area view, or repoint a
parent with `bd contain`/`bd uncontain`.

Freshness:

```
bd stale | bd reconcile
```

Read-only projections:

```
bd view REF --out DIR
bd export context|dot --view REF --out PATH
```

`bd view REF --out DIR` is the single read-only tree projection; `bd export`
keeps `context` and `dot`.

Full syntax: [`docs/CHEATSHEET.md`](docs/CHEATSHEET.md) or `bd <command> --help`.

## Repository layout

```
pyproject.toml             packaging metadata and the `bd` console script
src/bd_tree/               Python package
  loader.py                filename grammar, store index, view resolution
  model.py                 Node, View, Edge, Issue
  checker.py               structural validation
  exporter.py              context/dot projections; view renders the tree
  freshness.py             pins, stale edges, reconcile
  navigate.py              show/tree/ls/find/grep/path
  work.py                  single work area, current/views/edit, status, writeback
  solutions.py             git worktree wrapper
  ops.py                   init, new, structural edits, versions, diff
  cli.py, api.py           command line and public API
tests/                     pytest suite
examples/                 example project: .bd_tree/ store + ignored bd_work/
docs/                      user, developer, design, branches/versions
docs/breakdown/            product breakdown: bd store (.bd_tree/) + ignored bd_work/
```

## Status

- The suite passes: `python3 -m pytest -q`.
- The committed example project `examples/` has a `.bd_tree/nodes/` tree, a
  `.bd_tree/ROOT` file, and a gitignored `bd_work/`; `bd check` passes for it.
- No JSON, TOML, lock, or state data files; the only exceptions are a
  store-level `ROOT` file with one ref line and a folder-level `.bd_root`
  pointer with one store path. Derived output is gitignored.
- Structural edits, the git-aware single work area, and the `bd solution` wrapper
  are in place.

## Known limits

- Node-local versions do not sync across branches. Use git merges for solutions;
  versions are for alternatives inside one branch.
- No three-way merge between versions. Promotion copies; synthesis is manual.
- One worktree per solution. Switching branches inside one worktree can leave a
  layout pointing at paths absent from the new branch; rebuild with
  `bd work REF --clean` and run `bd work --status`.
- Some editors replace symlinks instead of writing through them. Use
  `bd work --status` / `bd work --writeback`.
- Work folders rely on symlinks; Windows needs developer mode or elevated rights.
- No generic importer or CI configuration yet.
