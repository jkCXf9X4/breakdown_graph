# Cheatsheet

Run `bdg <command> --help` for the full flag list. Exit codes: 0 success, 1 check
or navigation failure, 2 structural refusal.

One topology: nodes joined by typed link tokens in their bodies. A token is
`(TITLE)[[REF, TYPE]]`, with the cached title as a prefix (optional spaces
between `)` and `[[`); authors write the bare `[[REF, TYPE]]`, and the tool
fills the title. A bare token is valid but `bdg check` warns
`inline-title-missing`; a mismatch warns `link-title-stale`, and `bdg retitle`
regenerates the cache. In-edges are derived by reversing authored tokens; a
back-reference is an authored token in the other node, not a derived opposite.
A view is the weakly connected component of its anchor, ordered by undirected
BFS distance. Direction is a label (`child`, `parent`); cycles and back-edges
are legal. There is no `contains` key and no front-matter `links`; a node that
still declares either fails `bdg check` (`contains-removed`, `links-removed`)
and is converted by `bdg migrate`.

## Environment

```sh
export BDG_ROOT=path/to/project       # or path/to/store
bdg <command> --root path/to/project  # explicit per command
```

`bdg` resolves a store in this order: `--root`, `BDG_ROOT`, then the upward walk
from the current directory. At each directory a store (`nodes/` or
`bdg_graph/nodes/`) wins, otherwise a `.bdg_root` pointer there names the store;
after that comes a unique store below the current directory (depth 3, symlinks
not followed). Several stores below cwd are refused with the list; one store per
checkout.

`.bdg_root` is a one-line pointer a working folder may hold to name its store; a
relative path is resolved from that folder. `ROOT` is a different file: the
store-level default-anchor ref.

## View anchor

```sh
bdg root                             # print: <ref>  (ROOT|lowest)
bdg root REF                         # write ROOT: one full ref line, e.g. 1-1
bdg root --clear                     # delete ROOT; use the lowest component member
```

`ROOT` sits at the store top level and holds one full `id-version` ref on one
line, nothing else. It is the default anchor for `graph`, `find`, `work`,
`check`, and `stale`. An explicit ref where a command takes one
wins over `ROOT`; `ROOT` wins over the lowest component member.
`bdg check --view REF` only narrows reporting. A declared but missing ref is
`root-ref-missing`; malformed content is `invalid-root`. `bdg root` does not
rewrite the view already in the work area; use `bdg work REF` for that.

Data refs are full `id-version`; link tokens and `ROOT` never hold a bare id. A bare
id on the command line is a selector resolved inside the selected view and is
never written to data.

## Start

```sh
bdg init [DIR]                       # create bdg_graph/nodes/1-1.md and .gitignore
bdg new [--parent REF] [--type TYPE] [--field KEY=VALUE ...] [--body TEXT]
bdg migrate [--dry-run] [--type T]   # convert a classic, containment, or FM-links store
```

`bdg init` writes a graph root with no links and no placement key; there is no
`--graph` flag because graph is the only topology. `bdg new` allocates the next
global integer at version 1 and, when `--parent` is given, appends a typed token
(`--type`, default `breaks_down`). Without `--parent` the node starts its own
component. `bdg new` has no placement flags: membership and order are derived from
links and BFS distance. It seeds `title` and `summary` as empty placeholders;
`--field` overrides them.

`bdg migrate` renames every bare `nodes/<id>.md` to the next free version, and
converts the old edge shapes: each `contains` list becomes ordered typed body
tokens, and front-matter `links` moves into a trailing `## Links` section as
sorted `- (TITLE)[[REF, TYPE]]` lines. Legacy suffix tokens
`[[TYPE, REF]](TITLE)` or `[[REF, TYPE]](TITLE)` become the prefix form
`(TITLE)[[REF, TYPE]]`; tokens in either component order are normalized to
ref-first, and missing titles are filled.
Retired scalar links gain an explicit type; `symmetric`/`inverse` are dropped;
per-link `pinned`/`propagates` values move to the `freshness:` map. `--type`
chooses the converted containment edge type (default `breaks_down`);
`--dry-run` prints the plan without touching disk. It also strips the retired
placement keys (`band`, `subpath`, `layer`, `stage`, `order`, and the ROOT
`band_layout` and `band_order`) while leaving `section` as inert front matter.
Running it again is idempotent. `bdg retitle` is the explicit post-migration
refresh: it regenerates cached titles in the whole store or a view from each
target's live title.

## Inspect

```sh
bdg check [--view REF] [--require FIELD] [--max-lines N] [--max-chars N]
bdg show REF[+N] [--depth N] [--max-chars N] [--no-body] [--fields F,F] [--links]
bdg find QUERY [--view REF|--all] [--field F] [--regex] [--where K=V ...] [--limit N]
bdg path REF
bdg views

bdg graph [REF] [--depth N] [--rings A:B] [--type T] [--format text|dot|svg] [--color-by F] [--shape-by F] [--out PATH]
bdg out REF
bdg in REF
```

- `check` validates the store, the selected view, and the graph checks. There is
  no separate `audit` command.
- `graph` is the single view renderer: it prints ring sections from an anchor.
  The anchor is ring 0; ring 1 is split into `children` and `parents`; deeper
  rings are numbered.
- `views` lists one representative per component with its node count and title;
  `*` marks the store default and `anchor REF` marks the work-area view.
- `out` lists authored out-edge tokens; `in` lists derived reverse edges,
  every line marked `[derived]`.
- `bdg graph --format svg --out graph.svg` renders the same view as SVG with
  Graphviz; `--format dot` is the dependency-free fallback and `--out` writes
  either render. `--color-by` and `--shape-by` map front-matter fields to a
  stable colour or shape.
- `--depth N` on `bdg graph` stops traversal after `N` link hops.
  `--rings A:B` keeps the inclusive ring range in the output but keeps
  traversing through hidden nodes; the anchor is always included. `--type T`
  follows only links of that type (repeatable).
- Direction is a label, not a filter: `→` child, `←` parent. A cycle or a
  back-edge is legal and may put a distant node in a low ring.
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
bdg link FROM TO --type TYPE [--propagates]
bdg unlink FROM TO [--type TYPE]
bdg retitle [REF] [--dry-run]
```

- `link` appends `- (TITLE)[[TO, TYPE]]` to the source's `## Links` section in
  call order, writing the target's live title; existing lines are untouched.
  Keep that section in ascending target order (`graph-unsorted-links` warns
  otherwise). Back-edges, reciprocal edges, and cycles are legal. A self-loop
  on the same ref is refused, as is an identical edge to the same target with
  the same type. To make a back-reference, link from the other node; there is
  no symmetric flag.
- `link --propagates` records the edge in the source's `freshness:` map and pins
  the target body hash immediately.
- `link`, `unlink`, and `new` accept a bare id as a selector and resolve it in
  the selected view; they always write full refs.
- `retitle` regenerates every cached title in scope: the whole store by
  default, or the view of `REF`. Unresolved targets are left
  untouched. Use `--dry-run` to print `would retitle N tokens in M nodes`
  without writing; the real run prints `retitled N tokens in M nodes`.
- Structural commands preserve body bytes and unrelated front matter, except the
  token lines they append or remove.
- `unlink` removes matching token lines; any reverse edge is only a `bdg in`
  computation and disappears with the authored token.
- `contains` is not a command and not data. Run `bdg migrate` to convert a store
  that uses it.

## Work folders

```sh
bdg work [REF[+N]] [--depth N] [--path-template T] [--title-field F] [--summary-field F] [--force] [--clean] [--repair]
bdg current [--path|--view|--status]
bdg views
bdg edit REF
```

- Default: `<project>/bdg_work/`. A project has exactly one writable work area;
  a different REF replaces its contents.
- The view is the whole component of one ref. `REF+N` or `--depth N`
  materializes only rings `0..N` in the area (`0` is the anchor alone;
  `--depth` overrides a suffix). This is the same suffix that `bdg show` accepts,
  and a rebuild with a different depth replaces the area.
- The area is flat: one node `.md` symlink per materialized ref, named after the
  store file. There are no node directories.
- The generated `REFS.md`, `INDEX.md`, and `AGENTS.md` carry `REF+N`, so
  `bdg current`, `bdg current --status`, `bdg work --repair`, and `bdg edit` recover
  the materialized depth. The active view is the `# References — view REF[+N]`
  header in `REFS.md`; there is no separate state file.
- `INDEX.md` is one root file with ring sections (`## Active`,
  `## Distance 1 — children|parents`, `## Distance 2`, …). It carries a
  `nodes:` front-matter path to the real node folder, each node entry links
  straight to its real file, and a `nodes/` link opens the folder for copying or
  deleting store files.
- `REFS.md` is the path/ref/kind/distance/title table sorted by
  `(distance, kind, ref)`.
- `AGENTS.md`, `INDEX.md`, and `REFS.md` are regular generated files, never
  symlinks. Those three names are reserved.
- `bdg current` is read-only: it prints `<project>/bdg_work (view <ref>)`;
  `--path` prints only the path, `--view` only the ref. It errors if no work
  area exists.
- `bdg current --status` and `bdg work --repair` inspect the view actually in the
  area, not the requested or default view.
- `bdg views` lists component representatives (`ref`, size, title), and marks the
  store default with `*` and the work-area anchor.
- `bdg edit REF` prints the absolute path of REF in the active view and errors if
  the ref is not there.
- `bdg current --status`: `ok`, `missing`, `wrong-target`, `detached`, `stray`,
  `stale-ref`.
- `bdg work --repair` keeps edits made by an editor that replaced a symlink.
- Switching with detached (edited but unsynced) files is refused: run
  `bdg work --repair` to keep them, or `--clean` to discard them.
- Re-running a healthy tree refreshes it in place: stale links are removed and
  `INDEX.md`, `REFS.md`, and `AGENTS.md` are rewritten.

Switch the one area between views:

```sh
bdg work 1-1                                    # write <project>/bdg_work for view 1-1
bdg current                                     # <project>/bdg_work (view 1-1)
bdg work 5-1                                    # switch the same area to view 5-1
bdg work 1-1+1                                  # rings 0 and 1 only
bdg work 1-1 --depth 0                          # anchor only
bdg work 1-1                                    # restore the full component
bdg work 1-1 --path-template '{ref}-d{distance}.md'
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

`bdg pack` and `bdg graph --format` are read-only projections, not a second work
area: `bdg pack` writes a disposable regular-file copy, and `bdg graph --format`
writes a string render to `--out` or stdout.

## Solutions (git worktrees)

```sh
bdg solution new NAME [--path PATH] [--from REF]
bdg solution list
bdg solution remove NAME|PATH [--force]
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
bdg versions ID
bdg clone REF [--version N] [--subtree] [--depth N]
bdg replace OLD NEW
bdg delete REF [--force]
bdg diff LEFT RIGHT
```

Every node file is a version (`<id>-<version>.md`, version >= 1); versions of
one id are peers. `bdg versions ID` accepts `5` or `5-1` and uses the logical id.
There is no per-node pointer. An edge pins a full ref, and a view warns when two
versions of one id are reachable (`graph-duplicate-version`). `bdg clone REF`
copies the source file, including its link tokens, to the next free version
of the same logical id (or to `--version N`) and wires nothing into the current
view. `bdg clone REF --subtree` clones the whole weakly connected component and
rewrites each cloned node's token refs; edges whose targets were cloned are
rewired to the copies, while a depth prefix keeps edges that leave the prefix
pointing at the originals. The original stays untouched; `--depth N` narrows the
clone to rings `0..N` and implies `--subtree`. `--version` cannot be combined with `--subtree` or `--depth`.
`bdg replace OLD NEW` is the separate wiring step: it repoints every inbound
link and sets the rewritten tokens' cached title to NEW's live title, or
repoints `ROOT` when OLD is the store root; OLD's file stays as a peer. Clone
and swap in one logical flow with `bdg clone REF --subtree` then
`bdg replace REF <printed new root ref>`. If OLD is outside the default view,
`bdg replace` errors. Several parents are legal; repoint the edge whose peer you
want to change.
`bdg delete REF` removes one version and refuses an effective `ROOT` or a ref
that is an inbound target of another node unless `--force`.

Versions are alternatives inside one branch, not the solution boundary, and they
never sync across branches. To switch, use `bdg clone REF` then
`bdg replace REF NEW`, switch the work area with `bdg work REF`, or switch the
store default with `bdg root REF`. See
[Branches and versions](BRANCHES-AND-VERSIONS.md).

## Freshness

```sh
bdg stale [--view REF]
bdg stale --fix [REF ...] [--all] [--view REF]
```

A link participates only when the source node's `freshness:` map has an entry
for its target with `propagates: true` (or an existing `pinned`). The entry is
keyed by target ref; the pinned hash covers the target body with reserved tokens
and the `## Links` heading stripped, so token edits do not invalidate it.
Editing a propagating target makes the source edge stale until you run
`bdg stale --fix`.

## Read-only projections

```sh
bdg pack REF --out DIR [--force] [--clean] [--path-template T] [--title-field F] [--summary-field F]
bdg pack REF --fresh --out DIR [--force] [--clean] [--path-template T] [--title-field F] [--summary-field F]
bdg graph REF --format dot|svg [--color-by FIELD] [--shape-by FIELD] [--out PATH]
```

`bdg pack` default writes every node as a flat regular file plus one ring-section
`INDEX.md`. `--fresh` writes only fresh node bodies plus `STALE.md` and
`AGENTS.md`, for an agent that must not write. `bdg graph --format` renders the
same store as DOT or SVG; `text` (the default) is the ring view.

```sh
bdg pack 1-1 --out /tmp/bdg-graph                         # every node + INDEX.md
bdg pack 1-1 --fresh --out /tmp/bdg-context               # fresh nodes + STALE.md + AGENTS.md
bdg graph 1-1 --format dot --out graph.dot               # Graphviz source
bdg graph 1-1 --format svg --out graph.svg               # rendered image
```

`--format svg` needs the Graphviz `dot` binary on `PATH`; `--format dot` is the
dependency-free fallback. Three projections cover the same store: `bdg work`
(writable symlinks into the store), `bdg pack` (a disposable regular-file copy),
and `bdg graph --format` (a string render). Only `bdg work` is writable.

## Git patterns

```sh
git worktree add ../sol-a -b sol-a
git diff main..sol-a -- bdg_graph/nodes/    # or your default branch
git merge sol-a
git cherry-pick <commit>
git restore --source=sol-a -- bdg_graph/nodes/5-1.md
```

- The flat node path (`bdg_graph/nodes/` in a project layout) is the merge unit.
- Worktrees are the simultaneous solutions.
- `git status` shows node edits, never the layout.

## Health checks

```sh
bdg check
bdg stale
bdg current --status
git status --porcelain
python3 -m pytest -q
```

## Frequent fixes

| Problem | Fix |
| --- | --- |
| Wrong store | `BDG_ROOT` or `--root`; otherwise `bdg` uses the nearest `nodes/`, `bdg_graph/nodes/`, or `.bdg_root` upward. |
| `bdg current` errors | No work area exists. Build one with `bdg work [REF]`. |
| `bdg edit REF` errors | The ref is not in the active view. Switch with `bdg work REF` or pass a ref that is present. |
| `root-ref-missing` / `invalid-root` | The `ROOT` file names an absent ref or is malformed. Fix it, or run `bdg root --clear`. |
| `contains-removed` / `links-removed` | The store still declares `contains` or front-matter `links`. Run `bdg migrate --dry-run` then `bdg migrate`. |
| `inline-malformed` | A `[[...]]` fragment is not `[[REF, TYPE]]` with a full ref. Fix the token; use `\[[` to show one literally. |
| `inline-duplicate` | One node declares the same type and target twice. Remove one with `bdg unlink`. |
| `inline-title-missing` | A token is bare. Run `bdg retitle` to fill the cached title; do not hand-write it. |
| `link-title-stale` | A cached `(TITLE)` differs from the target's live title. Run `bdg retitle`; rendering already uses the live title. |
| `invalid-freshness` | The `freshness:` map must key full target refs to a mapping with string `pinned` and boolean `propagates`. |
| `bare-ref` / `invalid-ref` in data | `ROOT` needs a full `id-version` ref; a bare ref inside a token is `inline-malformed`. A classic bare-file store converts once with `bdg migrate`. |
| `graph-dangling-link` | A link targets a missing node. Remove it or restore the target. |
| `graph-orphan` | A node is outside the default component. Link it in, or anchor the command on its component with `bdg graph REF` / `bdg work REF`. |
| `graph-duplicate-version` | Two versions of one id are reachable from the anchor. Repoint one edge to the peer you want. |
| A cycle or back-edge is rejected | It should not be. Update to the current version; only a self-loop is refused by `bdg link`. |
| Detached work file | `bdg current --status`, then `bdg work --repair`. Switching views with detached files is refused until you do. |
| Want two work folders | Not supported. `bdg_work/` is the single area; switch with `bdg work REF`. |
| Stale layout after branch change | `bdg work REF --clean`. |
| Dangling link after removing a node | `bdg check`, then `bdg unlink` or restore the node. |
| Node too large | Split it, or raise `--max-lines` / `--max-chars`. |
| `bdg_work/` in git status | `bdg init` adds it to `.gitignore`; add `bdg_work/` if the project predates that. |
