# Cheatsheet

Run `bd <command> --help` for the full flag list. Exit codes: 0 success, 1 check
or navigation failure, 2 structural refusal.

One topology: nodes joined by typed `links`. In-edges are derived; a link with
`symmetric: true` is one authored master whose opposite is derived at load and
never stored. A view is the weakly connected component of its anchor, ordered by
undirected BFS distance. Direction is a label (`child`, `parent`, `peer`);
cycles and back-edges are legal. There is no `contains` key; a node that still
declares one fails `bd check` with `contains-removed` and is converted by
`bd migrate`.

## Environment

```sh
export BD_ROOT=path/to/project       # or path/to/store
bd <command> --root path/to/project  # explicit per command
```

`bd` resolves a store in this order: `--root`, `BD_ROOT`, then the upward walk
from the current directory. At each directory a store (`nodes/` or
`.bd_tree/nodes/`) wins, otherwise a `.bd_root` pointer there names the store;
after that comes a unique store below the current directory (depth 3, symlinks
not followed). Several stores below cwd are refused with the list; one store per
checkout.

`.bd_root` is a one-line pointer a working folder may hold to name its store; a
relative path is resolved from that folder. `ROOT` is a different file: the
store-level default-anchor ref.

## View anchor

```sh
bd root                             # print: <ref>  (ROOT|lowest)
bd root REF                         # write ROOT: one full ref line, e.g. 1-1
bd root --clear                     # delete ROOT; use the lowest component member
```

`ROOT` sits at the store top level and holds one full `id-version` ref on one
line, nothing else. It is the default anchor for `graph`, `find`, `work`,
`check`, `stale`, and `reconcile`. An explicit ref where a command takes one
wins over `ROOT`; `ROOT` wins over the lowest component member.
`bd check --view REF` only narrows reporting. A declared but missing ref is
`root-ref-missing`; malformed content is `invalid-root`. `bd root` does not
rewrite the view already in the work area; use `bd work REF` for that.

Data refs are full `id-version`; `links` and `ROOT` never hold a bare id. A bare
id on the command line is a selector resolved inside the selected view and is
never written to data.

## Start

```sh
bd init [DIR]                       # create .bd_tree/nodes/1-1.md and .gitignore
bd new [--parent REF] [--type TYPE] [--field KEY=VALUE ...] [--body TEXT]
bd migrate [--dry-run] [--type T]   # convert a classic or containment store in place
bd migrate [--symmetric TYPE] [--inverse TYPE=TYPE2]
```

`bd init` writes a graph root with no links and no placement key; there is no
`--graph` flag because graph is the only topology. `bd new` allocates the next
global integer at version 1 and, when `--parent` is given, adds a typed link
(`--type`, default `breaks_down`). Without `--parent` the node starts its own
component. `bd new` has no placement flags: membership and order are derived from
links and BFS distance. It seeds `title` and `summary` as empty placeholders;
`--field` overrides them.

`bd migrate` renames every bare `nodes/<id>.md` to the next free version, and
converts a containment store: each `contains` list becomes ordered typed `links`,
scalar links gain an explicit type, and every link list is sorted by ref.
`--type` chooses the converted edge type (default `breaks_down`); `--dry-run`
prints the plan without touching disk. It also strips the retired placement
keys (`band`, `subpath`, `layer`, `stage`, `order`, and the ROOT `band_layout`
and `band_order`) while leaving `section` as inert front matter. The same
command upgrades an already-migrated store idempotently: `--symmetric TYPE`
marks every link of that type a master (and drops `propagates`/`pinned`), and
`--inverse TYPE=TYPE2` marks it and names the derived opposite.

## Inspect

```sh
bd check [--view REF] [--require FIELD] [--max-lines N] [--max-chars N]
bd show REF[+N] [--depth N] [--max-chars N] [--no-body] [--fields F,F] [--links]
bd find QUERY [--view REF|--all] [--field F] [--regex] [--where K=V ...] [--limit N]
bd path REF
bd views

bd graph [REF] [--depth N] [--distance A:B] [--type T] [--dot|--svg] [--out PATH]
bd out REF
bd in REF
bd audit [REF]
```

- `check` validates the store and the selected view. `audit` is the explicit
  graph audit; `bd check` already runs the graph checks, so `audit` is redundant
  but convenient.
- `graph` is the single view renderer: it prints ring sections from an anchor.
  The anchor is ring 0; ring 1 is split into `children`, `parents`, and `peers`;
  deeper rings are numbered.
- `views` lists one representative per component with its node count and title;
  `*` marks the store default and `anchor REF` marks the work-area view.
- `out` lists authored out-edges then derived symmetric opposites, marked
  `[derived]`; `in` lists derived in-edges.
- `bd graph --svg --out graph.svg` renders the same view as SVG with Graphviz;
  `--dot` is the dependency-free fallback and `--out` writes either render.
- `--depth N` on `bd graph` stops traversal after `N` link hops.
  `--distance A:B` keeps the inclusive ring range in the output but keeps
  traversing through hidden nodes; the anchor is always included. `--type T`
  follows only links of that type (repeatable).
- Direction is a label, not a filter: `→` child, `←` parent, `↔` peer. A cycle
  or a back-edge is legal and may put a distant node in a low ring.
- `show 5-1+2`: node 5-1 plus rings 0..2, each node once, with arrival arrows.
  With N > 0 the body is capped at 4000 characters per node unless
  `--max-chars N` is given; `--max-chars 0` prints the full body.
- `--links` appends a `links:` footer: one row per undirected neighbour of each
  printed node, with the direction arrow and the edge type.
- `path REF` prints the shortest undirected path from the store anchor to REF,
  with an arrow on every step. There is no ancestry and no first-parent chain.
- `find` searches title, summary, body, and all string fields; `--regex` treats
  the query as a pattern. It searches the anchor's component unless `--view REF`
  or `--all` is given; output stays capped.

## Structure

```sh
bd link FROM TO --type TYPE [--propagates] [--symmetric [--inverse TYPE]]
bd unlink FROM TO [--type TYPE]
```

- `link` appends a typed edge and keeps the target list sorted by ref.
  Back-edges, reciprocal edges, and cycles are legal. A self-loop on the same ref
  is refused, as is an identical edge to the same target with the same type.
- `link --symmetric` authors the single master of a two-way relation; the
  opposite is derived at load and shown `[derived]`. `--inverse TYPE` names the
  derived opposite's type and requires `--symmetric`.
- `link --propagates` pins the target body hash immediately. It cannot be
  combined with `--symmetric`.
- `link`, `unlink`, and `new` accept a bare id as a selector and resolve it in
  the selected view; they always write full refs.
- Structural commands preserve body bytes and unrelated front matter.
- `unlink` removes matching master links; derived opposites disappear with them.
- `contains` is not a command and not data. Run `bd migrate` to convert a store
  that uses it.

## Work folders

```sh
bd work [REF[+N]] [--depth N] [--path-template T] [--title-field F] [--summary-field F] [--force] [--status] [--writeback] [--clean]
bd current [--path|--view]
bd views
bd edit REF
```

- Default: `<project>/bd_work/`. A project has exactly one writable work area;
  a different REF replaces its contents.
- The view is the whole component of one ref. `REF+N` or `--depth N`
  materializes only rings `0..N` in the area (`0` is the anchor alone;
  `--depth` overrides a suffix). This is the same suffix that `bd show` accepts,
  and a rebuild with a different depth replaces the area.
- The area is flat: one node `.md` symlink per materialized ref, named after the
  store file. There are no node directories.
- The generated `REFS.md`, `INDEX.md`, and `AGENTS.md` carry `REF+N`, so
  `bd current`, `--status`, `--writeback`, and `bd edit` recover the materialized
  depth. The active view is the `# References — view REF[+N]` header in
  `REFS.md`; there is no separate state file.
- `INDEX.md` is one root file with ring sections (`## Active`,
  `## Distance 1 — children|parents|peers`, `## Distance 2`, …). It carries a
  `nodes:` front-matter path to the real node folder, each node entry links
  straight to its real file, and a `nodes/` link opens the folder for copying or
  deleting store files.
- `REFS.md` is the path/ref/kind/distance/title table sorted by
  `(distance, kind, ref)`.
- `AGENTS.md`, `INDEX.md`, and `REFS.md` are regular generated files, never
  symlinks. Those three names are reserved.
- `bd current` is read-only: it prints `<project>/bd_work (view <ref>)`;
  `--path` prints only the path, `--view` only the ref. It errors if no work
  area exists.
- `--status` and `--writeback` inspect the view actually in the area, not the
  requested or default view.
- `bd views` lists component representatives (`ref`, size, title), and marks the
  store default with `*` and the work-area anchor.
- `bd edit REF` prints the absolute path of REF in the active view and errors if
  the ref is not there.
- `--status`: `ok`, `missing`, `wrong-target`, `detached`, `stray`, `stale-ref`.
- `--writeback` keeps edits made by an editor that replaced a symlink.
- Switching with detached (edited but unsynced) files is refused: run
  `--writeback` to keep them, or `--clean` to discard them.
- Re-running a healthy tree refreshes it in place: stale links are removed and
  `INDEX.md`, `REFS.md`, and `AGENTS.md` are rewritten.

Switch the one area between views:

```sh
bd work 1-1                                    # write <project>/bd_work for view 1-1
bd current                                     # <project>/bd_work (view 1-1)
bd work 5-1                                    # switch the same area to view 5-1
bd work 1-1+1                                  # rings 0 and 1 only
bd work 1-1 --depth 0                          # anchor only
bd work 1-1                                    # restore the full component
bd work 1-1 --path-template '{ref}-d{distance}.md'
```

The layout is flat: each node uses the store file's basename.
`--path-template` overrides the whole area; placeholders are `{ref}`, `{id}`,
`{version}`, `{distance}`, `{slug}`, `{title}`, plus any front-matter key.
`{slug}` is the title slug, else the ref. `group`, `section`, `folder`, and
`home` place nothing.

```yaml
title: The Main Thesis    # -> 4-1.md (store basename)
name: custom-name         # metadata only; default path is still 4-1.md
```

`bd export graph` and the other `bd export` choices are read-only snapshots, not
a second work area.

## Solutions (git worktrees)

```sh
bd solution new NAME [--path PATH] [--from REF]
bd solution list
bd solution remove NAME|PATH [--force]
```

Thin wrapper over:

```sh
git worktree add ../NAME -b NAME
git worktree list
git worktree remove ../NAME
```

One worktree per solution. Edit and commit inside it; compare with `git diff` and
sync with `git merge`.

## Versions (node-local)

```sh
bd versions ID
bd clone REF [--version N] [--subtree] [--depth N]
bd replace OLD NEW
bd delete REF [--force]
bd diff LEFT RIGHT
```

Every node file is a version (`<id>-<version>.md`, version >= 1); versions of
one id are peers. `bd versions ID` accepts `5` or `5-1` and uses the logical id.
There is no per-node pointer. An edge pins a full ref, and a view warns when two
versions of one id are reachable (`graph-duplicate-version`). `bd clone REF`
copies the source file, including its declared `links`, to the next free version
of the same logical id (or to `--version N`) and wires nothing into the current
view. `bd clone REF --subtree` clones the whole weakly connected component and
rewrites each cloned node's `links`; edges whose targets were cloned are
rewired to the copies, while a depth prefix keeps edges that leave the prefix
pointing at the originals. The original stays untouched; `--depth N` narrows the
clone to rings `0..N` and implies `--subtree`. `--version` cannot be combined with `--subtree` or `--depth`.
`bd replace OLD NEW` is the separate wiring step: it repoints every inbound link,
or repoints `ROOT` when OLD is the store root; OLD's file stays as a peer. Clone
and swap in one logical flow with `bd clone REF --subtree` then
`bd replace REF <printed new root ref>`. If OLD is outside the default view,
`bd replace` errors. Several parents are legal; repoint the edge whose peer you
want to change.
`bd delete REF` removes one version and refuses an effective `ROOT` or a ref
that is an inbound target of another node unless `--force`.

Versions are alternatives inside one branch, not the solution boundary, and they
never sync across branches. To switch, use `bd clone REF` then
`bd replace REF NEW`, switch the work area with `bd work REF`, or switch the
store default with `bd root REF`. See
[Branches and versions](BRANCHES-AND-VERSIONS.md).

## Freshness

```sh
bd stale [--view REF]
bd reconcile [REF ...] [--all] [--view REF]
```

A structural link participates only with `propagates: true` (or an existing
`pinned`). Symmetric links never propagate: `propagates` on a symmetric link is
`propagates-on-symmetric`. Editing a propagating target makes the source edge
stale until reconciled.

## Read-only projections

```sh
bd export graph   --view REF --out DIR [--force] [--clean]
bd export context --view REF --out DIR [--force] [--clean] [--path-template T] [--title-field F] [--summary-field F]
bd export dot     --view REF --out FILE [--render FMT ...] [--render-out PATH] [--color-by FIELD] [--shape-by FIELD]
bd export svg     --view REF --out FILE [--color-by FIELD] [--shape-by FIELD]
```

`bd export graph` is the component projection: flat node files plus one
ring-section `INDEX.md`. `context` writes fresh node bodies plus `STALE.md` and
`AGENTS.md`; `dot` is Graphviz.

```sh
bd export dot --view 1-1 --out graph.dot --render svg   # graph.dot + graph.svg
bd export svg --view 1-1 --out graph.svg                # rendered only
```

`--render` repeats for `svg`, `png`, or `pdf`; each file sits next to the `.dot`
unless `--render-out` names the one rendered path. `bd graph --svg` remains the
ring visual.

## Git patterns

```sh
git worktree add ../sol-a -b sol-a
git diff main..sol-a -- .bd_tree/nodes/    # or your default branch
git merge sol-a
git cherry-pick <commit>
git restore --source=sol-a -- .bd_tree/nodes/5-1.md
```

- The flat node path (`.bd_tree/nodes/` in a project layout) is the merge unit.
- Worktrees are the simultaneous solutions.
- `git status` shows node edits, never the layout.

## Health checks

```sh
bd check
bd audit                    # explicit graph audit; bd check already runs it
bd stale
bd work --status
git status --porcelain
python3 -m pytest -q
```

## Frequent fixes

| Problem | Fix |
| --- | --- |
| Wrong store | `BD_ROOT` or `--root`; otherwise `bd` uses the nearest `nodes/`, `.bd_tree/nodes/`, or `.bd_root` upward. |
| `bd current` errors | No work area exists. Build one with `bd work [REF]`. |
| `bd edit REF` errors | The ref is not in the active view. Switch with `bd work REF` or pass a ref that is present. |
| `root-ref-missing` / `invalid-root` | The `ROOT` file names an absent ref or is malformed. Fix it, or run `bd root --clear`. |
| `contains-removed` | The store still declares `contains`. Run `bd migrate --dry-run` then `bd migrate`. |
| `invalid-symmetric` / `inverse-without-symmetric` | A link's `symmetric` must be a boolean, and `inverse` needs a non-empty string plus `symmetric: true`. Fix the link, or rerun `bd migrate --symmetric TYPE [--inverse TYPE=TYPE2]`. |
| `symmetric-self-edge` / `duplicate-symmetric-edge` | Author one master per pair, never to itself and never in both directions. Remove the extra link with `bd unlink`. |
| `propagates-on-symmetric` | Remove `propagates`/`pinned` from the symmetric link; freshness is structural-only. |
| `bare-ref` / `invalid-ref` in data | `links` and `ROOT` need full `id-version` refs. A classic bare-file store converts once with `bd migrate`. |
| `graph-dangling-link` | A link targets a missing node. Remove it or restore the target. |
| `graph-orphan` | A node is outside the default component. Link it in, or anchor the command on its component with `bd graph REF` / `bd work REF`. |
| `graph-duplicate-version` | Two versions of one id are reachable from the anchor. Repoint one edge to the peer you want. |
| A cycle or back-edge is rejected | It should not be. Update to the current version; only a self-loop is refused by `bd link`. |
| Detached work file | `bd work --status`, then `bd work --writeback`. Switching views with detached files is refused until you do. |
| Want two work folders | Not supported. `bd_work/` is the single area; switch with `bd work REF`. |
| Stale layout after branch change | `bd work REF --clean`. |
| Dangling link after removing a node | `bd check`, then `bd unlink` or restore the node. |
| Node too large | Split it, or raise `--max-lines` / `--max-chars`. |
| `bd_work/` in git status | `bd init` adds it to `.gitignore`; add `bd_work/` if the project predates that. |
