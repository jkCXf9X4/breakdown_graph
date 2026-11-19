# info_graph — `bd`

A flat markdown store for layered project information, with running numeric refs,
per-node versions, containment views, and writable symlink work trees.

The store is the data. Work folders are disposable layouts over it. Agents read
views; edits go straight to the node files. Git owns the solution boundary; the
flat store is the merge unit; `bd work` is the layout lens.

## Why this exists

Layered breakdown documents (intent → claims → argument → evidence → manuscript →
verification → operation, or any other layering) describe one realization of a
solution. Exploring another realization by editing the tree in place leaves old
lower-layer nodes in the working tree, and an AI agent reading the repository picks
them up as current. Git branches and worktrees isolate a solution, but they do
not make stale lower-layer nodes disappear from the branch. Isolation and
invalidation are different jobs.

`bd` separates four things that file trees usually conflate:

1. **Identity** — a node is a file named by a running integer (`5.md`).
2. **Version** — `5-1.md`, `5-2.md` are alternative realizations of node 5.
3. **Containment** — `contains:` defines the tree for a view.
4. **Projection** — a view is a containment closure; a work folder is that closure
   materialized as symlinks to the same files.

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

## Quick start

Requirements: Python 3.10+, PyYAML, pytest (tests), Graphviz `dot` (optional dot
export). No packaging step; the CLI is `bin/bd` or `python -m breakdown`.

```sh
export BD_ROOT=workspace/licentiate-n
./bin/bd check
./bin/bd tree 1 --depth 1
./bin/bd show 1+1 --max-chars 400
./bin/bd find credibility --limit 3
./bin/bd work 1 --print
./bin/bd work 1
```

`bd work 1` creates `workspace/licentiate-n/build/work/1`, a tree-shaped directory
where every `.md` file is a symlink. Open it and edit normally; the write lands in
`nodes/<ref>.md` and `git status` reports the node, not the layout.

A second solution is a second worktree:

```sh
git worktree add ../info_graph-sol-a -b sol-a
cd ../info_graph-sol-a
export BD_ROOT=workspace/licentiate-n
bd work 1
```

## Model

```
nodes/<id>.md              main version
nodes/<id>-<version>.md    alternative version
nodes/<id>-<version>.md    another alternative
```

A ref is `5` (main) or `5-1` (version 1). Filenames carry identity and version;
front matter carries everything else.

Reserved front-matter keys:

| Key | Meaning |
| --- | --- |
| `id` | Logical integer id; optional, must match the filename |
| `legacy` | Original identifier from an imported tree |
| `contains` | Ordered child refs; missing on a version inherits main |
| `links` | Semantic edges `{to, type, pinned?, propagates?}` |
| `home` | Optional presentation path inside a view |

Everything else is arbitrary user metadata (`layer`, `type`, `status`, `phase`,
`audience`, `order`, …) and is preserved on export. There is no fixed schema and
no fixed layer vocabulary.

## Commands

### Browse

```
bd tree [REF] [--depth N] [--summary] [--fields F,F]
bd show REF[+DEPTH] [--depth N] [--max-chars N] [--no-body] [--fields F,F] [--path]
bd ls [REF] [--depth N] [--columns F,F] [--max-chars N]
bd find QUERY [--field F] [--regex] [--where KEY=VALUE ...] [--limit N]
bd grep PATTERN [--field F] [--where KEY=VALUE ...] [--limit N]
bd path REF
```

`bd tree 1 --depth 2` is the map. `bd show 5+2` is the detail: node 5 plus two
levels of descendant bodies.

### Work folders (layout interface)

A work folder is a custom layout of one view inside the current checkout. It is
not a branch and not a copy; edits write through to `nodes/`.

```
bd work [REF] [--out DIR] [--name NAME] [--path-template T]
        [--title-field F] [--summary-field F]
        [--status] [--writeback] [--clean] [--force] [--print]
```

- Default directory: `<store>/build/work/<ref>`.
- `--name` gives `<store>/build/work/<ref>-<name>`, so several representations of
  the same root can coexist.
- Every node is a relative symlink to `nodes/<ref>.md`. There is no copy and no
  sync. Edits are visible through every work tree that contains the node.
- Re-running `bd work REF` refreshes a healthy tree without `--clean`.
- A detached or stray file blocks refresh. Use `--status` to inspect and
  `--writeback` to keep edits made through an editor that replaced the symlink.
- `--print` emits only the directory, for `cd "$(bd work 1 --print)"`.
- Generated files in a work tree: `INDEX.md`, `REFS.md` (path ↔ ref map),
  `AGENTS.md`.
- Inside a git checkout, `AGENTS.md` records the current branch, short commit and
  worktree, and the build output adds a `branch NAME` line. Outside git those
  fields are omitted.
- `--writeback` refuses detached files without valid front matter or with a
  mismatched `id`; a body-only replacement cannot silently erase `contains`.

### Versions

```
bd versions ID
bd fork ID [--version N]
bd promote REF [--keep]
bd retire-version REF
bd diff REF1 REF2
```

`5.md` is the mutable main version. Versions are snapshots by convention.
`promote 5-2` copies a version onto main; `--keep` retains the version file.

Versions are **node-local** alternatives inside one branch. They are not the
solution boundary. A solution-level alternative is a git branch and worktree;
mixing solutions is a merge or cherry-pick, not a version selector. If a version
and a branch express the same thing, prefer the branch.

### Structure and freshness

```
bd check [--root-ref REF] [--view REF] [--require FIELD] [--max-lines N] [--max-chars N]
bd stale [--view REF]
bd reconcile [--all | REF ...] [--view REF]
bd new --parent REF [--field KEY=VALUE ...] [--body TEXT]
bd contain PARENT CHILD [--before REF | --after REF]
bd uncontain PARENT CHILD
bd link FROM TO --type TYPE [--propagates]
bd unlink FROM TO [--type TYPE]
```

`links` are arbitrary typed edges. A link participates in freshness only when it
has `propagates: true` (or already has a `pinned` hash). `bd stale` reports edges
whose pinned target body changed; `bd reconcile` rewrites the pins.
`bd link --propagates` pins the target immediately, so a new edge starts fresh.

`bd contain` and `bd uncontain` edit one parent's effective list, materialising it
explicitly when it was inherited from a version's main. They never touch the
child file. `bd unlink` removes matching edges and never deletes nodes.

### Read-only projections

```
bd view REF --out DIR [--path-template T] [--clean]
bd export tree|context|dot --view REF --out PATH [...]
```

`bd view` writes a read-only copy of a containment view. `bd export context`
writes fresh node bodies plus `STALE.md` and `AGENTS.md` for an agent that should
not write. `bd export dot` writes Graphviz; colour and shape are chosen by
arbitrary fields.

## Workflow

1. Browse with `tree`, `show`, `ls`, `find`, `path`.
2. Make a solution boundary with git:
   `git worktree add ../sol-a -b sol-a`.
3. Inside the checkout, make a layout: `bd work REF` or `bd work 5 --name subtree`.
4. Edit through the layout, or edit `nodes/<ref>.md` directly.
5. Change structure with `bd contain`, `bd uncontain`, `bd link`, `bd unlink`;
   add nodes with `bd new`.
6. Validate with `bd check`; inspect freshness with `bd stale`.
7. Commit the node files. Compare solutions with `git diff`, `bd diff`, or two
   worktrees side by side.
8. Produce a read-only view only when publishing, reviewing, or feeding an agent
   that must not write.

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
  work.py                  symlink work trees, status, writeback
  ops.py                   versions, fork, promote, diff, new, structural edits
  cli.py, api.py           command line and public API
tests/                     pytest suite
tools/migrate_licentiate.py  one-off typed-id → numeric migration
workspace/licentiate/      legacy typed-id corpus, read-only evaluation source
workspace/licentiate-n/    numeric corpus, 128 nodes, derived containment
```

## Status

- 143 tests pass (`python3 -m pytest -q`).
- The 128-node evaluation corpus passes `bd check` with one size warning.
- Migration body gate: 0 mismatches; every node reachable from root `1`.
- No JSON, TOML, lock, or state data files. Derived output is gitignored.

## Known limits

- Node-local versions do not sync across branches. Use git merges for solutions;
  versions are for alternatives inside one branch.
- There is no automatic three-way merge between node versions; promotion is a
  copy, and synthesis is manual.
- One worktree per solution. Switching branches inside one worktree leaves the
  symlink layout pointing at paths that may not exist on the new branch; rebuild
  with `bd work REF --clean` and run `--status`.
- No locking. Concurrent editors can race on the same node file; git is the
  conflict detector.
- Some editors replace symlinks instead of writing through them. `--status` and
  `--writeback` exist for that case.
- Work trees rely on symlinks; Windows needs developer mode or elevated rights.
- Migration from the typed-id corpus is a one-off, domain-specific script.

## Further reading

- [`docs/DESIGN.md`](docs/DESIGN.md) — established model, decisions, invariants,
  rejected alternatives, migration details.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — next work.
- [`AGENTS.md`](AGENTS.md) — operating rules for future agent sessions.
