# Getting started

This guide goes from the default example to a browsable, editable store with a
flat work area, typed links, and a second solution in a git worktree. `bd` has
one topology: markdown nodes joined by typed link tokens in their bodies. A
token is `[[TYPE, REF]]`, optionally with a cached `(TITLE)`. In-edges are
derived by reversing authored tokens; a back-reference is an authored token in
the other node, not a derived opposite. A view is the weakly connected component
of its anchor, ordered by undirected BFS distance.

You need Python 3.10+ and PyYAML. From a clone, install the package:

```sh
pip install .
bd --help
```

## 1. See the default store

The repository ships `examples/` as the default store (`ROOT` `1-1`). Linked
nodes carry typed tokens in their bodies, and the store is one component.

```sh
export BD_ROOT=examples
bd check
```

```
12 nodes, 0 errors, 0 warnings (view 1-1)
```

The store layout:

```
examples/.bd_tree/nodes/1-1.md
examples/.bd_tree/ROOT          # 1-1
examples/.bd_tree/nodes/4-1.md
```

A node file looks like this:

```markdown
---
id: 1
title: <the intent of this graph>
---
# <the intent of this graph>

The intent breaks down into [[breaks_down, 2-1]](Structural claims) and
[[breaks_down, 3-1]](Verification claims).
```

The filename is identity and version: logical id `1`, version `1`. The rest of
the front matter is arbitrary. A token declares one typed edge to a full
`id-version` ref; `(TITLE)` is a cached copy of the target's live title and is
advisory. Tooling appends the same token as a `- [[TYPE, REF]](TITLE)` line
under `## Links`. Front-matter `links` is retired (`links-removed`). There is no
placement field: membership and order come from the graph.

There is no second topology and no `contains` key. A node that still declares
`contains` fails `bd check` with `contains-removed`; `bd migrate` converts it
(§10).

## 2. Browse the graph

```sh
bd graph 1-1
bd graph --depth 1
bd graph 1-1 --distance 2:3
bd show 2-1+1 --max-chars 400
bd find closure --limit 3
bd path 4-1
bd out 1-1
bd in 4-1
bd views
```

- `graph` renders ring sections from an anchor, with authored `→ out` edges and
  derived `← in` edges. The anchor is ring 0; ring 1 is split into `children`
  and `parents`; deeper rings are numbered. `bd graph` is the only view
  renderer.
- `--depth N` stops traversal after `N` hops. `--distance A:B` keeps an
  inclusive ring range in the output but keeps traversing through hidden nodes;
  the anchor is always included.
- `show REF+N` prints the node body plus rings `0..N`, each node once. Arrival
  arrows label the direction (`→` child, `←` parent).
- `find` searches titles, summaries, bodies, and front-matter fields.
- `path` prints the shortest undirected chain from the anchor, with an arrow on
  every step. `4-1` has two parents; the path is deterministic but is only one
  of several equally short routes.
- `out` lists authored out-edge tokens; `in` lists derived reverse edges.
- `views` lists one representative per component, marking the default with `*`
  and the work-area anchor.

A node reached through several neighbours appears once in a view. Multiple
parents, cycles, and back-edges are legal.

Exit codes: `bd check` returns 1 on errors and 0 on clean. Structural commands
return 2 on refusal.

## 3. Audit the graph

```sh
bd audit
bd check
```

```
0 errors, 0 warnings
```

The graph audit checks the rules that make the undirected view meaningful:

- tokens resolve to existing full refs and are kept in ascending target order;
- a token that does not match `[[TYPE, REF]]` is `inline-malformed`, and the
  same type and target twice on one node warns `inline-duplicate`;
- a cached `(TITLE)` that differs from the target's live title warns
  `link-title-stale`; rendering still uses the live title;
- a bare `ROOT` ref is `bare-ref`, and malformed `ROOT` content is
  `invalid-root`;
- a node outside the default component warns (`graph-orphan`); out-degree above
  200 warns (`graph-wide-fanout`);
- a reachable duplicate version warns (`graph-duplicate-version`);
- a node declaring `contains` is `contains-removed`, and one declaring
  front-matter `links` is `links-removed`.

Cycles, back-edges, reciprocal edges, and direction are not errors. Only a
self-loop on one ref is refused by `bd link`.

Structure is edited with links:

```sh
bd new --parent 1-1 --type breaks_down --field title="A new claim"
bd link 2-1 8-1 --type supports
bd link 8-1 2-1 --type supported_by
bd unlink 2-1 8-1 --type supports
```

`bd new` allocates the next global id at version 1 and appends a typed token to
the parent's `## Links` section; `--type` defaults to `breaks_down`. It has no
placement flags. Without `--parent`, the node starts its own component.
`bd link` appends `- [[TYPE, TO]](TITLE)` to the source in call order; existing
lines are untouched, so add targets in ascending order or re-sort the section.
Back-edges and cycles are legal. A back-reference is a second authored token on
the other node with its own type — there is no `--symmetric`.

## 4. Edit in the work area

`bd work` renders a view as a flat set of symlinks in the project's single
writable work area, `<project>/bd_work/`. Editing a link edits the store.

```sh
bd work 1-1
bd current                 # <project>/bd_work (view 1-1)
work_dir=$(bd current --path)
ls "$work_dir"
```

```
1-1.md   2-1.md   3-1.md   4-1.md   5-1.md   6-1.md
7-1.md   8-1.md   9-1.md   10-1.md  11-1.md  12-1.md
INDEX.md  REFS.md  AGENTS.md
```

Every node `.md` is a symlink named after the store file. The area is flat:
there are no node directories. `INDEX.md`, `REFS.md`, and `AGENTS.md` are
regular generated files.

`INDEX.md` has ring sections:

```markdown
## Active

- [<title>](1-1.md) — [real file](../.bd_tree/nodes/1-1.md)

## Distance 1 — children

- [<title>](2-1.md) — [real file](../.bd_tree/nodes/2-1.md)

## Distance 2

- [<title>](4-1.md) — [real file](../.bd_tree/nodes/4-1.md)
```

`REFS.md` is the sorted navigation table:

```markdown
# References — view 1-1

| Path | Ref | Kind | Distance | Title |
| --- | --- | --- | --- | --- |
| `1-1.md` | 1-1 | active | 0 | <title> |
| `2-1.md` | 2-1 | child | 1 | <title> |
| `4-1.md` | 4-1 | - | 2 | <title> |
```

The `# References — view REF[+N]` header is the active node of the area.
`bd current`, `bd edit`, `--status`, and `--writeback` read it. There is no
separate state file.

`bd edit REF` prints the ref's absolute path inside the active view and errors
if the ref is not there. `bd current` is read-only; `--path` prints only the
path and `--view` only the ref, and it errors if no area exists.

`--status` reports `ok`, `missing`, `wrong-target`, `detached`, `stray`, or
`stale-ref`. If an editor replaces a symlink with a regular file:

```sh
bd work --status
bd work --writeback
```

`--writeback` writes the detached content to the original node, refuses files
without valid front matter, and re-links them.

There is exactly one writable work area. `bd work REF` switches it to another
view by replacing its contents: stale links are removed, and `INDEX.md`,
`REFS.md`, and `AGENTS.md` are rewritten. Never keep two work folders side by
side.

A work area may also materialize only rings `0..N` of a component:
`bd work REF+N`, or `bd work REF --depth N`, where `0` materializes the anchor
alone and `--depth` overrides a suffix. The view itself is still the whole
component. The generated headers carry `REF+N`, so `bd current --view` reports
it and `bd edit` only resolves refs that are materialized. A rebuild with a
different depth, or a plain `bd work REF`, replaces the area.

```sh
bd work 1-1+1      # rings 0 and 1
bd current --view  # 1-1+1
bd work 1-1        # restore the full component
```

Read-only snapshots (`bd export graph`, `bd export context`, `bd export dot`)
are separate disposable exports, not a second work area. `bd work` and
`bd export graph` materialize the same flat view; the export writes regular
files plus a ring-section `INDEX.md`.

## 5. Create a store

```sh
mkdir -p ~/stores/my-graph
cd ~/stores/my-graph
bd init
```

```
.bd_tree/nodes/1-1.md
.gitignore          # bd_work/
```

```markdown
---
id: 1
title: Root
---
# Root
```

`bd init` always writes a graph root with no links and no placement key; there
is no `--graph` flag because graph is the only topology. Add nodes and check:

```sh
bd new --parent 1-1 --type breaks_down --field title="Why does this exist?"
bd new --parent 1-1 --type breaks_down --field title="What is true?"
bd check
```

```
3 nodes, 0 errors, 0 warnings (view 1-1)
```

`bd graph 1-1` renders rings `0` and `1`. `bd new` appends a typed token to the
parent's `## Links` section; it writes no position.

The work area is flat: each node's path is its store basename. `group`,
`section`, `folder`, and `home` are inert front matter: they place nothing.

To change the view, edit the links. There is no separate move command: position
is derived from edges and undirected distance.

## 6. Typed links and freshness

The body carries typed tokens. Add a propagating edge and track freshness:

```sh
bd link 2-1 3-1 --type supports --propagates
bd stale
```

Then edit a target through its work area, or open it with `bd edit REF`. A
propagating edge records `pinned` under the target's ref in the source node's
top-level `freshness:` map; `bd stale` reports when the target moves.
`--propagates` is opt-in; a `see_also` edge never goes stale. The pinned hash
ignores token lines and the `## Links` heading, so adding an edge does not
invalidate another edge's pin.

Reconcile after reviewing the change:

```sh
bd reconcile REF           # or --all
bd stale
```

Remove an edge:

```sh
bd unlink FROM TO --type supports
```

Pins are body hashes, so they survive a rebase.

## 7. Versions and switching

Two separate moves: change the default anchor, or switch the view held by the
work area.

```sh
bd root 1-1                 # write ROOT; commands default here
bd root                     # 1-1  (ROOT)
bd work 1-1                 # switch the work area
bd current                  # <project>/bd_work (view 1-1)
bd root --clear             # back to the lowest component member
```

`ROOT` is one full ref on one line at the store top level. An explicit ref where
a command takes one still wins over it; with no `ROOT`, the store uses the
lowest member of its first component. `bd check --view REF` only narrows
reporting, not the checked anchor. `bd root` changes the default anchor used by
commands but does not rewrite the view already in `<project>/bd_work/`; run
`bd work REF` for that. `bd views` lists component representatives and marks the
default with `*`.

Versions are node-local alternatives inside one branch:

```sh
bd versions 1
bd clone 1-1 --version 2
bd replace 1-1 1-2
```

`bd clone REF` copies a ref to the next free version of the same logical id (or
to `--version N`) and keeps the source file's link tokens; it wires nothing into
a view. `bd clone REF --subtree` clones the whole weakly connected component and
rewrites the cloned token refs whose target was also cloned; a depth prefix
keeps edges that leave the prefix pointing at the originals. `--depth N`
narrows the clone to rings `0..N` and implies `--subtree`.
`--version` cannot be combined with `--subtree` or `--depth`.
`bd replace OLD NEW` is the separate wiring step: it repoints every inbound
link, or repoints `ROOT` when OLD is the store root; OLD's file stays as a peer.

An edge pins a full ref, several parents are allowed, and a view warns
(`graph-duplicate-version`) when two versions of one id are reachable. Repoint
the edge whose peer you want to change.

## 8. A second solution with git

A solution is a git branch in a worktree; the flat store is the merge unit.

```sh
git init -b main
git add -A
git commit -m "init store"

bd solution new sol-a
```

`bd solution new` prints:

```
worktree /home/you/stores/sol-a
branch sol-a
project .
cd /home/you/stores/sol-a
bd work 1-1
```

The project directory is printed relative to the worktree. In a nested project,
`cd` into the printed project path instead, for example
`cd /home/you/stores/sol-a/examples`, then run the printed `bd work` command.

```sh
cd ../sol-a
bd work 1-1
$EDITOR "$(bd edit 1-1)"
bd check
git add -A && git commit -m "sol-a: alternative intent"
```

Compare without switching:

```sh
cd ../my-graph
git diff main..sol-a -- .bd_tree/nodes/
bd solution list
```

Remove the checkout when done; the branch remains:

```sh
bd solution remove sol-a
```

If the project is nested inside the repo, use the printed `cd` line to enter the
project path inside the worktree, for example `cd /home/you/stores/sol-a/examples`.
Store discovery then finds `.bd_tree/` there. From the worktree root it also
finds a single store below the current directory; `BD_ROOT` is only needed when
several stores are below that root.

## 9. Feed an agent

Two modes:

```sh
# writable: the single work area for one view
bd work 1-1
bd current

# read-only snapshot: fresh nodes, plus STALE.md and AGENTS.md
bd export context --view 1-1 --out /tmp/bd-context-1-1
```

`bd work` writes `<project>/bd_work/` and is the only work area; the export
directory is a disposable snapshot, not a second area. Both contain an
`AGENTS.md`; the work area also records the branch, commit, and worktree, and
its `REFS.md` names the active view. Tell the agent to read exactly one
directory and not to read outside it, and to use `bd edit REF` rather than
guessing paths. To change view, switch the same area with `bd work REF` and
confirm with `bd current`.

## 10. Use an existing markdown tree

There is no generic importer yet. The pattern is:

1. One file per node version under the store's `nodes/` (`.bd_tree/nodes/` in a
   project layout), named `<id>-<version>.md` with a running integer id and a
   version starting at `1`.
2. `id` matches the logical id in the filename.
3. Link tokens name typed edges with full refs, in ascending target order. No
   placement key is needed: the view is the component of the anchor and the
   order is BFS distance. If the tree must read as a hierarchy, encode the
   parent -> child tokens; a `child` label comes from the authored direction.
4. Prose citations are separate; an edge is a link, not a bibliography entry.
5. The flat work area uses store basenames; `--path-template` overrides naming.

An older store that used `contains` or authored placement is converted in place:

```sh
bd migrate --dry-run     # print the plan
bd migrate               # contains/links -> body tokens; retired keys stripped
bd check                 # clean
```

`bd migrate` writes converted edges as sorted body tokens, uses `--type`
(default `breaks_down`) for `contains` edges, moves per-link freshness into the
`freshness:` map, removes the retired placement fields, and keeps `section` as
inert front matter. It is idempotent and leaves a token-only store untouched.

`examples/` is the default worked project: a twelve-node graph under
`examples/.bd_tree/` with one file per node version, typed tokens in the linked
bodies, one component, rings 0 through 4 from `1-1`, and no `contains`.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `bd: unknown ref '1-1'` | No store found, or the ref is absent from the selected view. Run from the project root or store root, or set `BD_ROOT` to the directory containing `nodes/` (or `.bd_tree/nodes/`). |
| `bd check` sees the wrong store | `BD_ROOT` or `--root` points elsewhere. `bd` uses the nearest `nodes/` or `.bd_tree/nodes/` upward. |
| `root-ref-missing` / `invalid-root` | The `ROOT` file names an absent ref or is malformed. Fix it, or run `bd root --clear`. |
| `contains-removed` / `links-removed` | The store still declares `contains` or front-matter `links`. Run `bd migrate --dry-run`, then `bd migrate`. |
| `inline-malformed` | A `[[...]]` fragment is not `[[TYPE, REF]]` with a full ref. Fix the token; escape it as `\[[` to show it literally. |
| `inline-duplicate` | One node declares the same type and target twice. Remove one with `bd unlink`. |
| `link-title-stale` | A cached `(TITLE)` differs from the target's live title. Update or drop the parenthetical. |
| `invalid-freshness` | `freshness:` must key full target refs to a mapping with string `pinned` and boolean `propagates`. |
| `bare-ref` / `invalid-ref` in data | `ROOT` needs a full `id-version` ref; a bare ref inside a token is `inline-malformed`. Convert a classic bare-file store once with `bd migrate`. |
| A cycle or back-edge is reported | It should not be. Update to the current version; only a self-loop is refused by `bd link`. |
| `graph-orphan` | A node is outside the default component. Link it in, or anchor on its component with `bd graph REF` / `bd work REF`. |
| `bd work` refuses to switch | `bd_work/` has detached or stray files. Run `--status`, then `--writeback` to keep them or `--clean` to discard them. |
| `bd current` errors | No work area exists. Build one with `bd work [REF]`. |
| `bd edit REF` errors | The ref is not in the active view. Switch with `bd work REF` or use a ref that is present. |
| Edit did not reach the node | The editor replaced the symlink. Run `--status`, then `--writeback`. |
| Want two work folders | Not supported. `bd_work/` is the single area; switch with `bd work REF`. |
| `bd_work/` appears in git status | `bd init` adds it to `.gitignore`; add `bd_work/` if the project predates that. |
| Work folder points at missing files | The branch changed under the layout. Rebuild with `bd work REF --clean`. |
| Size warning on a node | Cosmetic by default. Split the node, or pass `--max-lines` / `--max-chars`. |

## Next

- Command reference: [`CHEATSHEET.md`](CHEATSHEET.md)
- Graph topology: [`GRAPH.md`](GRAPH.md)
- Ring layout and work area: [`GRAPH-LAYOUT.md`](GRAPH-LAYOUT.md)
- Model and decisions: [`DESIGN.md`](DESIGN.md)
- Change the tool: [`DEVELOPING.md`](DEVELOPING.md)
- Agent rules: [`../AGENTS.md`](../AGENTS.md)
