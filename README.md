# info_graph — `bd`

A flat markdown store for layered project information, with running numeric refs,
per-node versions, containment views, and writable symlink work trees.

The store is the data. Work trees are disposable views over it. Agents read views;
edits go straight to the node files.

## Why this exists

Layered breakdown documents (intent → claims → argument → evidence → manuscript →
verification → operation, or any other layering) describe one realization of a
solution. Exploring another realization by editing the tree in place leaves old
lower-layer nodes in the working tree, and an AI agent reading the repository picks
them up as current. Git branches isolate a whole checkout but keep one view at a
time, and they do not make stale lower-layer nodes disappear from a generated
index.

`bd` separates four things that file trees usually conflate:

1. **Identity** — a node is a file named by a running integer (`5.md`).
2. **Version** — `5-1.md`, `5-2.md` are alternative realizations of node 5.
3. **Containment** — `contains:` defines the tree for a view.
4. **Projection** — a view is a containment closure; a work tree is that closure
   materialized as symlinks to the same files.

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
`nodes/<ref>.md`.

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

### Work trees (primary interface)

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

### Structure and freshness

```
bd check [--root-ref REF] [--view REF] [--require FIELD] [--max-lines N] [--max-chars N]
bd stale [--view REF]
bd reconcile [--all | REF ...] [--view REF]
bd new --parent REF [--field KEY=VALUE ...] [--body TEXT]
```

`links` are arbitrary typed edges. A link participates in freshness only when it
has `propagates: true` (or already has a `pinned` hash). `bd stale` reports edges
whose pinned target body changed; `bd reconcile` rewrites the pins.

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

1. Browse with `tree`, `show`, `ls`, `find`.
2. Work in a symlink tree: `bd work REF`.
3. Explore an alternative: `bd fork 5`, edit `nodes/5-1.md`, work its view.
4. Keep what survives: `bd promote 5-1`, or write the outcome into nodes and
   retire the version.
5. Validate with `bd check`; inspect freshness with `bd stale`.
6. Produce a read-only view only when publishing, reviewing, or feeding an agent
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
  ops.py                   versions, fork, promote, diff, new
  cli.py, api.py           command line and public API
tests/                     pytest suite
tools/migrate_licentiate.py  one-off typed-id → numeric migration
workspace/licentiate/      legacy typed-id corpus, read-only evaluation source
workspace/licentiate-n/    numeric corpus, 128 nodes, derived containment
```

## Status

- 121 tests pass (`python3 -m pytest -q`).
- The 128-node evaluation corpus passes `bd check` with one size warning.
- Migration body gate: 0 mismatches; every node reachable from root `1`.
- No JSON, TOML, lock, or state data files. Derived output is gitignored.

## Known limits

- No structural edit commands yet (`bd contain`, `bd uncontain`, `bd link`,
  `bd unlink`); edit `contains`/`links` in the node file for now.
- Merging is promotion plus manual synthesis; there is no automatic three-way
  merge between versions.
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
