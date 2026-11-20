# breakdown tree — `bd`

A flat markdown store for layered project information, with a git solution
boundary, typed dependency edges, and custom symlink work folders.

- **Store** — one markdown file per node, keyed by a running integer.
- **Structure** — an ordered `contains` list defines the tree; paths do not.
- **Root** — an optional `ROOT` file names the default view root in one ref line.
- **Solutions** — git branches and worktrees.
- **Layout** — `bd work` renders a view as symlinks into the store.
- **Freshness** — typed links record what depends on what and whether it still holds.

The store is the data; work folders are disposable layouts. Agents read views and
edit the node files directly.

## Two axes

These are deliberately separate:

- **Solution boundary: git.** A branch and worktree hold one solution. Git decides
  when it is merged or discarded.
- **Merge unit: the flat `nodes/` store.** One file per node keeps a conflict
  local to the node that changed.
- **Layout: `bd work`.** A custom symlink view inside one checkout. Several views
  can coexist; none is a copy.
- **Versions are not a third axis.** `5-1` is an alternative file for node `5`
  inside the checked-out branch. Versions give no isolation and never cross a
  branch; git still owns every branch decision.
  [The full separation](docs/BRANCHES-AND-VERSIONS.md).

A store-level `ROOT` file names one default view root (`bd root 1-4`), so
`tree`, `ls`, `work`, `check`, `stale`, and `reconcile` follow it without an
argument. An explicit ref wins; with no `ROOT`, the lowest main ref is the root.
Switching trees writes `ROOT` or repoints a parent; `bd promote` only copies one
version onto main.

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

The repository ships a small example store in `examples/switch-trees`. Read it
first; do not edit it.

```sh
export BD_ROOT=examples/switch-trees

bd check                       # clean, two complete trees
bd tree 1 --depth 1            # the main tree
bd tree 1-1                    # the alternative tree
bd show 1+1 --max-chars 300    # body plus one level
bd ls 1                        # children as a table
bd find Method --limit 3
bd path 3                      # ancestor chain to a leaf
```

Then make a work folder:

```sh
bd work 1 --print              # path only, for cd
bd work 1
cd "$(bd work 1 --print)"
# every .md here is a symlink; editing it edits nodes/<ref>.md
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

`bd init` creates `nodes/1.md` and prints the next commands. Front matter is
arbitrary: use `layer`, `phase`, `status`, `audience`, or anything else.

## Where is my store?

`bd` walks up from the current directory until it finds `nodes/`.

- If `nodes/` is at your repo root, run `bd` from anywhere inside the repo.
- If the store is nested, set `BD_ROOT=path/to/store` or pass `--root`.
- One store per checkout. A git worktree has its own `nodes/`.

This repository's example store is at `examples/switch-trees`, hence `BD_ROOT`.

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
bd work [REF] [--name N] [--path-template T] [--status] [--writeback] [--print]
```

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
`bd root` or repoint a parent with `bd contain`/`bd uncontain`.

Freshness:

```
bd stale | bd reconcile
```

Read-only projections:

```
bd view REF --out DIR
bd export tree|context|dot --view REF --out PATH
```

Full syntax: [`docs/CHEATSHEET.md`](docs/CHEATSHEET.md) or `bd <command> --help`.

## Repository layout

```
pyproject.toml             packaging metadata and the `bd` console script
src/bd_tree/               Python package
  loader.py                filename grammar, store index, view resolution
  model.py                 Node, View, Edge, Issue
  checker.py               structural validation
  exporter.py              tree/context/dot projections
  freshness.py             pins, stale edges, reconcile
  navigate.py              show/tree/ls/find/grep/path
  work.py                  symlink work folders, status, writeback
  solutions.py             git worktree wrapper
  ops.py                   init, new, structural edits, versions, diff
  cli.py, api.py           command line and public API
tests/                     pytest suite
examples/switch-trees/     small store with two complete trees and a ROOT file
docs/                      user, developer, design, branches/versions
```

## Status

- The suite passes: `python3 -m pytest -q`.
- The committed example `examples/switch-trees` has two complete trees and a
  `ROOT` file; `bd check` passes for it.
- No JSON, TOML, lock, or state data files; the only exception is a store-level
  `ROOT` file with one ref line. Derived output is gitignored.
- Structural edits, git-aware work folders, and the `bd solution` wrapper are in
  place.

## Known limits

- Node-local versions do not sync across branches. Use git merges for solutions;
  versions are for alternatives inside one branch.
- No three-way merge between versions. Promotion copies; synthesis is manual.
- One worktree per solution. Switching branches inside one worktree can leave a
  layout pointing at paths absent from the new branch; rebuild with
  `bd work REF --clean` and run `--status`.
- Some editors replace symlinks instead of writing through them. Use
  `bd work --status` / `--writeback`.
- Work folders rely on symlinks; Windows needs developer mode or elevated rights.
- No generic importer or CI configuration yet.
