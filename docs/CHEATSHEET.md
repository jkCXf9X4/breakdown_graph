# Cheatsheet

Run `bd <command> --help` for the full flag list. Exit codes: 0 success, 1 check
or navigation failure, 2 structural refusal.

One topology: nodes joined by typed `links`. A link is structural by default; a
link with `symmetric: true` is one authored master whose opposite is derived at
load and never stored. There is no `contains` key; a node that still declares one
fails `bd check` with `contains-removed` and is converted by `bd migrate`.

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
store-level default-view ref.

## View root

```sh
bd root                             # print: <ref>  (ROOT|lowest)
bd root REF                         # write ROOT: one full ref line, e.g. 1-1
bd root --clear                     # delete ROOT; use the lowest graph root
```

`ROOT` sits at the store top level and holds one full `id-version` ref on one
line, nothing else. It is the default view root for `graph`, `find`, `work`,
`check`, `stale`, and `reconcile`. An explicit ref where a command takes one
wins over `ROOT`; `ROOT` wins over the lowest graph root. `bd check --view REF`
only narrows reporting. A declared but missing ref is `root-ref-missing`;
malformed content is `invalid-root`. `bd root` does not rewrite the view already
in the work area; use `bd work REF` for that.

Data refs are full `id-version`; `links` and `ROOT` never hold a bare id. A bare
id on the command line is a selector resolved inside the selected view and is
never written to data.

## Start

```sh
bd init [DIR]                       # create .bd_tree/nodes/1-1.md and .gitignore
bd new --parent REF --type TYPE --band BAND [--subpath SUB] [--order N]
bd new --parent REF --type TYPE --stage N [--order N]
bd new --parent REF --field KEY=VALUE ... [--body TEXT]
bd migrate [--dry-run] [--type T]   # convert a classic or containment store in place
bd migrate [--symmetric TYPE] [--inverse TYPE=TYPE2] [--band-order]
```

`bd init` writes a relative-band graph root (`band: root`, no `stage`); there is
no `--graph` flag because graph is the only topology. `bd new` allocates the next
global integer at version 1 and adds a typed link (`--type`, default
`breaks_down`). In relative mode `--band` is required and `--subpath` adds an
explicit folder below the band (`--layer BAND[/SUB]` is the older shorthand);
`--stage` is refused. In absolute mode it takes `--stage`; both take `--order`.
It seeds `title` and `summary` as empty placeholders; `--field` overrides them.

`bd migrate` renames every bare `nodes/<id>.md` to the next free version, and
converts a containment store: each `contains` list becomes ordered typed
`links`, converted children get `order: i` when they had none, and a `section`
path on a node without `band` becomes `band` plus `subpath`. `--type` chooses
the converted edge type (default `breaks_down`); `--dry-run` prints the plan
without touching disk. The same command upgrades an already-migrated store
idempotently: `--symmetric TYPE` marks every link of that type a master (and
drops `propagates`/`pinned`), `--inverse TYPE=TYPE2` marks it and names the
derived opposite, and `--band-order` writes the ROOT `band_order` hint plus
`band_layout: flat`.

## Inspect

```sh
bd check [--view REF] [--require FIELD] [--max-lines N] [--max-chars N]
bd show REF[+N] [--max-chars N] [--no-body] [--fields F,F] [--links]
bd find QUERY [--view REF|--all] [--field F] [--regex] [--where K=V ...] [--limit N]
bd path REF
bd views

bd graph [REF] [--depth N] [--stage A:B] [--type T] [--dot|--svg] [--out PATH]
bd out REF
bd in REF
bd audit [REF]
```

- `check` validates the store and its views. `audit` is the explicit graph
  audit; `bd check` already runs the graph checks, so `audit` is redundant but
  convenient.
- `graph` is the single view renderer: it prints the band layout from an anchor.
- `views` lists graph roots.
- `out` lists authored master out-edges then derived symmetric opposites, marked
  `[derived]`; `in` lists derived in-edges; `audit` validates bands and edges.
- `bd graph --svg --out graph.svg` renders the same view as SVG with Graphviz;
  `--dot` is the dependency-free fallback and `--out` writes either render.
- `--stage A:B` on `bd graph` keeps the inclusive band range: an absolute stage
  ordinal or a top-level derived band ordinal. A nested band inherits its
  top-level ancestor's ordinal. The anchor band is always included.
- `band` names the band; `subpath` is an explicit folder below the band folder
  (`layer: band/sub` is the older shorthand). Bands are inferred from
  cross-band structural links by the shortest-path rule, so a detour may nest
  under a parent band. See [`GRAPH-LAYOUT.md`](GRAPH-LAYOUT.md).
- `group: <value>` is ordinary metadata. It places nothing; the audit warns
  `graph-group-ignored`. `section` is likewise inert: ordinary front matter with
  no effect on paths or validation. Use `band` plus `subpath` for folders.
- `show 5-1+2`: node 5-1 plus two hops of descendant bodies. With N > 0 the
  body is capped at 4000 characters per node unless `--max-chars N` is given;
  `--max-chars 0` prints the full body.
- `--links` appends a `links:` footer for edges that leave the view, one level,
  as `source -> target`, with `[derived]` on derived opposites. The target stays
  out of the closure; read it with `bd show REF` or switch with `bd work REF`.
- A missing ref uses the store root.
- `find` searches title, summary, body, and all string fields; `--regex` treats
  the query as a pattern. It searches the default view unless `--view REF` or
  `--all` is given; output stays capped.

## Structure

```sh
bd link FROM TO --type TYPE [--propagates] [--symmetric [--inverse TYPE]]
bd unlink FROM TO [--type TYPE]
```

- A structural `link` is the child relation: in absolute mode it refuses a
  back-edge (`stage(FROM) < stage(TO)` must hold); in relative mode it refuses
  a link that would create a band cycle and a same-band edge where
  `order(FROM) >= order(TO)`, including across subpaths. It keeps the target
  list sorted by ref.
- `link --symmetric` authors the single master of a two-way relation; the
  opposite is derived at load and shown `[derived]`. It skips the band/stage
  ordering checks. `--inverse TYPE` names the derived opposite's type and
  requires `--symmetric`.
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
bd work [REF[+N]] [--depth N] [--path-template T] [--status] [--writeback] [--clean]
bd current [--path|--view]
bd views
bd edit REF
```

- Default: `<project>/bd_work/`. A project has exactly one writable work area;
  a different REF replaces its contents.
- The view stays the full closure of one ref over forward structural links.
  `REF+N` or
  `--depth N` materializes only the first `N` descendant levels in the area
  (`0` is the root alone; `--depth` overrides a suffix). A level is a link hop
  and the layout is the band plan. This is the same suffix that `bd show`
  accepts, and a rebuild with a different depth replaces the area.
- The generated `REFS.md`, each folder's `INDEX.md`, and `AGENTS.md` carry
  `REF+N`, so `bd current`, `--status`, `--writeback`, and `bd edit` recover the
  materialized depth.
- Node `.md` files are symlinks to the store's `nodes/<ref>.md`, where `<ref>`
  is the full `id-version` (`.bd_tree/nodes/<ref>.md` in a project layout).
  `INDEX.md` in every directory, `AGENTS.md`, and `REFS.md` are regular
  generated files, never symlinks. Those three names are reserved in every
  directory. Each `INDEX.md` carries a `nodes:` front-matter path to the real
  node folder, each node entry links straight to its real file, and a
  `[nodes/](…)` link opens the folder for copying or deleting store files.
- `bd current` is read-only: it prints `<project>/bd_work (view <ref>)`;
  `--path` prints only the path, `--view` only the ref. It errors if no work
  area exists.
- `--status` and `--writeback` inspect the view actually in the area, not the
  requested or default view.
- `bd views` lists graph roots (`ref`, title), one per line, and marks the
  store default (`ROOT`) with `*`.
- `bd edit REF` prints the absolute path of REF in the active view and errors if
  the ref is not there.
- `--status`: `ok`, `missing`, `wrong-target`, `detached`, `stray`, `stale-ref`.
- `--writeback` keeps edits made by an editor that replaced a symlink.
- Switching with detached (edited but unsynced) files is refused: run
  `--writeback` to keep them, or `--clean` to discard them.
- Re-running a healthy tree refreshes it in place: stale links are removed and
  every folder's `INDEX.md`, plus `REFS.md` and `AGENTS.md`, are rewritten.

Switch the one area between views:

```sh
bd work 1-1                                    # write <project>/bd_work for view 1-1
bd current                                     # <project>/bd_work (view 1-1)
bd work 5-1                                    # switch the same area to view 5-1
bd work 1-1+1                                  # root plus immediate children only
bd work 1-1 --depth 0                          # root only
bd work 1-1                                    # restore the full closure
bd work 1-1 --path-template '{band}/{ref}.md'
```

Bands are the only layout. A node's folder is its band folder
(`<NN>-<slug(band)>`, zero-based derived ordinal) plus an explicit `subpath`.
An explicit `name` sets the file stem (`<name>.md`); otherwise the file is
`<ref>-<title-slug>.md`, or `<ref>.md` when the title is unusable.
`--path-template` overrides the whole area. `section` and `group` place nothing.
A ROOT `band_order: [band, ...]` breaks ties among ready bands in the
topological order (and orders `band_layout: flat` top-level folders); it never
overrides an edge constraint. Unknown or duplicate names are ignored; a
non-list value is `invalid-band-order`.

```yaml
band: claims
subpath: structural      # -> 01-claims/structural/
title: The Main Thesis    # no name -> 01-claims/structural/4-1-the-main-thesis.md
name: custom-name         # -> 01-claims/structural/custom-name.md
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
bd clone REF [--version N] [--subtree]
bd replace OLD NEW
bd delete REF [--force]
bd diff LEFT RIGHT
```

Every node file is a version (`<id>-<version>.md`, version >= 1); versions of
one id are peers. `bd versions ID` accepts `5` or `5-1` and uses the logical
id. There is no per-node pointer. An edge pins a full ref, and a view warns when
two versions of one id are reachable (`graph-duplicate-version`). `bd clone REF`
copies the source file, including its declared `links`, to the next free version
of the same logical id (or to `--version N`) and wires nothing into the current
view. `bd clone REF --subtree` clones every descendant in the structural forward
closure and rewrites each cloned parent's `links`, producing a self-contained
copy while the original stays untouched; `--version` cannot be combined with
`--subtree`. `bd replace OLD NEW` is the separate wiring step: it repoints every
inbound link, or repoints `ROOT` when OLD is the store root; OLD's file stays as
a peer. Clone and swap in one logical flow with `bd clone REF --subtree` then
`bd replace REF <printed new root ref>`. If OLD is outside the default view,
`bd replace` errors. Several parents are legal; repoint the edge whose peer you
want to change. `bd delete REF` removes one version and refuses a `ROOT`, a
reachable ref, or one referenced by any link unless `--force`.

Versions are alternatives inside one branch, not the solution boundary, and they
never sync across branches. To switch, use `bd clone REF` then `bd replace REF
NEW`, switch the work area with `bd work REF`, or switch the store default with
`bd root REF`. See [Branches and versions](BRANCHES-AND-VERSIONS.md).

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
bd export context --view REF --out DIR
bd export dot     --view REF --out FILE [--render FMT ...] [--render-out PATH] [--color-by FIELD] [--shape-by FIELD]
bd export svg     --view REF --out FILE [--color-by FIELD] [--shape-by FIELD]
```

`bd export graph` is the topology projection: the band plan (relative bands with
inferred nesting and explicit subpaths, or absolute stages) with per-folder
indexes. `context` writes fresh node bodies plus `STALE.md` and `AGENTS.md`;
`dot` is Graphviz.

```sh
bd export dot --view 1-1 --out graph.dot --render svg   # graph.dot + graph.svg
bd export svg --view 1-1 --out graph.svg                # rendered only
```

`--render` repeats for `svg`, `png`, or `pdf`; each file sits next to the `.dot`
unless `--render-out` names the one rendered path. `bd graph --svg` remains the
band-clustered visual.

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
| `invalid-band-order` | The ROOT `band_order` must be a YAML list of band names. Fix it or ignore the hint by removing the key. |
| `bare-ref` / `invalid-ref` in data | `links` and `ROOT` need full `id-version` refs. A classic bare-file store converts once with `bd migrate`. |
| `graph-layer-missing` / `graph-layer-invalid` | Relative mode: every node needs a valid `band`/`subpath` (or `layer` path). Add or fix it. |
| `graph-layer-cycle` | Cross-band edges form a loop. Repoint an edge with `bd unlink` then `bd link`. |
| `graph-order-back-edge` | A same-band edge has `order(source) >= order(target)`, including across subpaths. Raise the target's `order` or lower the source's. |
| `graph-group-ignored` | Warning: `group` is ordinary metadata. Replace it with `band` plus `subpath`. |
| `graph-stage-missing` / `graph-stage-invalid` | Absolute mode only: a node lacks an integer `stage`. Add or fix it, or move the store to relative bands by removing `stage`. |
| `graph-back-edge` / `graph-cycle` | Absolute mode: an edge does not strictly increase `stage`, or links loop. Repoint the edge with `bd unlink` then `bd link`. |
| `graph-dangling-link` | A link targets a missing node. Remove it or restore the target. |
| `graph-orphan` | A non-anchor root has no incoming edge. Make it the anchor or link it into the graph. |
| `graph-duplicate-version` | Two versions of one id are reachable from the anchor. Repoint one edge to the peer you want. |
| Detached work file | `bd work --status`, then `bd work --writeback`. Switching views with detached files is refused until you do. |
| Want two work folders | Not supported. `bd_work/` is the single area; switch with `bd work REF`. |
| Stale layout after branch change | `bd work REF --clean`. |
| Dangling link after removing a node | `bd check`, then `bd unlink` or restore the node. |
| Node too large | Split it, or raise `--max-lines` / `--max-chars`. |
| `bd_work/` in git status | `bd init` adds it to `.gitignore`; add `bd_work/` if the project predates that. |
