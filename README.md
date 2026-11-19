# info_graph — `bd`

A flat markdown store for layered project information, with a git solution
boundary, typed dependency edges, and custom symlink work folders.

- **Store** — one markdown file per node, keyed by a running integer.
- **Structure** — an ordered `contains` list defines the tree; paths do not.
- **Solutions** — git branches and worktrees.
- **Layout** — `bd work` renders a view as symlinks into the store.
- **Freshness** — typed links record what depends on what and whether it still holds.

The store is the data. Work folders are disposable layouts. Agents read views;
edits go straight to the node files.

## Two axes

These are deliberately separate:

- **Solution boundary: git.** A branch and worktree hold one solution. Git decides
  when it is merged or discarded.
- **Merge unit: the flat `nodes/` store.** One file per node, so a conflict stays
  local to the node that changed.
- **Layout: `bd work`.** A custom symlink view inside one checkout. Several views
  of the same checkout can coexist; none of them is a copy.

Git answers what changed. `contains` and `links` answer what belongs and what
depends. Pins answer whether it still holds.

## Install

Requirements: Python 3.10+, PyYAML, pytest for the test suite, Graphviz `dot` only
for dot export. There is no packaging step.

```sh
git clone https://github.com/jkCXf9X4/info_graph
cd info_graph
python3 -m pytest -q          # 155 tests
export PATH="$PWD/bin:$PATH"
bd --help
```

`bin/bd` runs from any working directory. If you prefer not to change `PATH`, use
`./bin/bd` in every example.

## Five-minute tour

The repository ships a 128-node evaluation corpus. Read it first; do not edit it.

```sh
export BD_ROOT=workspace/licentiate-n

bd check                       # 128 nodes, 0 errors, 1 size warning
bd tree 1 --depth 1            # outline of the root view
bd show 1+1 --max-chars 300    # body plus one level
bd ls 1                        # children as a table
bd find credibility --limit 3
bd path 65                     # ancestor chain to a leaf
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

`bd` finds the store by walking up from the current directory for a `nodes/`
directory.

- If `nodes/` is at your repo root, run `bd` from anywhere inside the repo.
- If the store is nested, set `BD_ROOT=path/to/store` or pass `--root`.
- One store per checkout. A git worktree has its own `nodes/`.

This repository is the nested case: the corpus lives at
`workspace/licentiate-n`, hence `BD_ROOT` in the tour.

## Choose your path

| I want to… | Read |
| --- | --- |
| Set up and use a store for the first time | [`docs/GETTING-STARTED.md`](docs/GETTING-STARTED.md) |
| Look up a command quickly | [`docs/CHEATSHEET.md`](docs/CHEATSHEET.md) |
| Understand the model and decisions | [`docs/DESIGN.md`](docs/DESIGN.md) |
| Change the tool itself | [`docs/DEVELOPING.md`](docs/DEVELOPING.md) |
| Work safely as an agent | [`AGENTS.md`](AGENTS.md) |
| See what is next | [`docs/ROADMAP.md`](docs/ROADMAP.md) |

## Command map

Inspect:

```
bd check | bd tree | bd show | bd ls | bd find | bd grep | bd path
```

Edit and structure:

```
bd init | bd new | bd contain | bd uncontain | bd link | bd unlink
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
bin/bd                     CLI wrapper
breakdown/                 Python package
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
tools/migrate_licentiate.py  one-off typed-id → numeric migration
workspace/licentiate/      legacy typed-id corpus, read-only evaluation source
workspace/licentiate-n/    numeric corpus, 128 nodes, derived containment
docs/                      user, developer, design, roadmap
```

## Status

- 155 tests pass (`python3 -m pytest -q`).
- The 128-node evaluation corpus passes `bd check` with one size warning.
- Migration body gate: 0 mismatches; every node reachable from root `1`.
- No JSON, TOML, lock, or state data files. Derived output is gitignored.
- Structural edits, git-aware work folders, and the `bd solution` wrapper are in
  place.

## Known limits

- Node-local versions do not sync across branches. Use git merges for solutions;
  versions are for alternatives inside one branch.
- No three-way merge between node versions. Promotion is a copy; synthesis is
  manual.
- One worktree per solution. Switching branches inside one worktree can leave a
  layout pointing at paths absent from the new branch; rebuild with
  `bd work REF --clean` and run `--status`.
- Some editors replace symlinks instead of writing through them. Use
  `bd work --status` / `--writeback`.
- Work folders rely on symlinks; Windows needs developer mode or elevated rights.
- No generic importer yet. The licentiate migration is a worked example.
- No CI configuration or packaging metadata yet.
