# Cheatsheet

Run `bd <command> --help` for the full flag list. Exit codes: 0 success, 1 check
or navigation failure, 2 structural refusal.

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

## Tree root

```sh
bd root                             # print: <ref>  (ROOT|lowest)
bd root REF                         # write ROOT: one full ref line, e.g. 1-1
bd root --clear                     # delete ROOT; lowest (id, version) is the default
```

`ROOT` sits at the store top level and holds one full `id-version` ref on one
line, nothing else. It is the default view root for `tree`, `find`, `work`,
`check`, `stale`, and `reconcile`. An explicit ref where a command takes one
wins over `ROOT`; `ROOT` wins over the lowest available node by
`(id, version)`. `bd check --view REF` only narrows reporting; the checked root
is `ROOT`, else the lowest `(id, version)`. A declared but missing ref is
`root-ref-missing`; malformed content is `invalid-root`. `bd root` does not
rewrite the view already in the work area; use `bd work REF` for that.

Data refs are full `id-version`; `contains`, `links`, and `ROOT` never hold a
bare id. A bare id on the command line is a selector resolved inside the
selected view and is never written to data.

## Start

```sh
bd init [DIR]                       # create .bd_tree/nodes/1-1.md and .gitignore
bd new --parent REF --field KEY=VALUE ... [--body TEXT]
bd migrate [--dry-run]              # convert a classic bare <id>.md store in place
```

`bd new` allocates the next global integer at version 1, appends that full ref
to the parent's `contains`, and seeds `title` and `summary` as empty
placeholders; `--field` overrides them. `bd migrate` renames every bare
`nodes/<id>.md` to the next free version and rewrites `contains`, `links`, and a
bare `ROOT`; `--dry-run` prints the plan without touching disk.

## Inspect

```sh
bd check [--view REF] [--require FIELD] [--max-lines N] [--max-chars N]
bd tree [REF] [--depth N] [--summary] [--fields F,F] [--links]
bd tree [REF] --columns F,F [--depth N] [--max-chars N]
bd show REF[+N] [--max-chars N] [--no-body] [--fields F,F] [--links]
bd find QUERY [--view REF|--all] [--field F] [--regex] [--where K=V ...] [--limit N]
bd path REF
```

- `show 5-1+2`: node 5-1 plus two levels of descendant bodies. With N > 0 the
  body is capped at 4000 characters per node unless `--max-chars N` is given;
  `--max-chars 0` prints the full body.
- `--links` appends a `links:` footer for edges that leave the view, one level,
  as `source -> target`. The target stays out of the closure; read it with
  `bd show REF` or switch with `bd work REF`.
- `tree 5-1 --depth 0`: whole subtree. A missing ref uses the store root.
- `tree 1-1 --columns ref,title,layer,status`: arbitrary fields as columns
  (tables default to depth 1); without `--columns`, `tree` prints the outline.
- `find` searches title, summary, body, and all string fields; `--regex` treats
  the query as a pattern. It searches the default view unless `--view REF` or
  `--all` is given; output stays capped.

## Structure

```sh
bd contain PARENT CHILD [--before REF | --after REF]
bd uncontain PARENT CHILD
bd link FROM TO --type TYPE [--propagates]
bd unlink FROM TO [--type TYPE]
```

- `contain` refuses cycles and duplicates; reorder with `uncontain` then `contain`.
- `uncontain` writes `contains: []` when the list becomes empty.
- `link --propagates` pins the target body hash immediately.
- A scalar link: `links: ['10-1']` takes the type from node `10-1`'s `type`;
  `bd link` writes that form when the requested type matches.
- `contain`, `uncontain`, `link`, `unlink`, and `new` accept a bare id as a
  selector and resolve it in the selected view; they always write full refs.
- Structural commands preserve body bytes and unrelated front matter.

## Work folders

```sh
bd work [REF[+N]] [--depth N] [--path-template T] [--status] [--writeback] [--clean]
bd current [--path|--view]
bd views
bd edit REF
```

- Default: `<project>/bd_work/`. A project has exactly one writable work area;
  a different REF replaces its contents.
- The view stays the full containment closure of one ref. `REF+N` or `--depth N`
  materializes only the first `N` descendant levels in the area (`0` is the root
  alone; `--depth` overrides a suffix). This is the same suffix that `bd show`
  and `bd tree` accept, and a rebuild with a different depth replaces the area.
- The generated `REFS.md`, `INDEX.md`, and `AGENTS.md` carry `REF+N`, so
  `bd current`, `--status`, `--writeback`, and `bd edit` recover the materialized
  depth.
- Node `.md` files are symlinks to the store's `nodes/<ref>.md`, where `<ref>`
  is the full `id-version` (`.bd_tree/nodes/<ref>.md` in a project layout).
  `INDEX.md`, `AGENTS.md`, and `REFS.md` are regular generated files, never
  symlinks.
- `bd current` is read-only: it prints `<project>/bd_work (view <ref>)`;
  `--path` prints only the path, `--view` only the ref. It errors if no work
  area exists.
- `--status` and `--writeback` inspect the view actually in the area, not the
  requested or default view.
- `bd views` lists containment roots (`ref`, title), one per line, and marks the
  store default (`ROOT`) with `*`.
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
bd work 1-1+1                                  # root plus immediate children only
bd work 1-1 --depth 0                          # root only
bd work 1-1                                    # restore the full closure
bd work 1-1 --path-template '{layer}/{ref}.md'
```

`section` is the only presentation key that creates directories: `section: true`
opens a directory at the node's placement name (explicit `name`, else the `title`
slug, else the ref) and nests its containment descendants inside; the node's own
file is `<dir>/<placement-name>.md`. `section: "<dir>"` names the directory
verbatim, slashes included, and nested sections stack. A leading `/` resolves
the directory from the output root instead of under the parent prefix, so a
containment chain can keep layers as siblings. Otherwise `name` sets the
file stem (`<name>.md`); without it the file is `<ref>-<title-slug>.md`, or
`<ref>.md` when the title is unusable. `--path-template` opts out of section
inheritance.

```yaml
section: claims           # opens claims/ for this node's subtree
section: /00-intent       # root-relative: 00-intent/ at the output root
title: The Main Thesis    # -> claims/the-main-thesis.md
name: custom-name         # optional override -> claims/custom-name.md
```

`folder` is ordinary front matter: preserved, never read, with no effect on
placement, naming, validation, or warnings. `bd new` no longer derives `folder`
from `layer`, `group`, or `type`.
`--path-template '{name}.md'` uses the computed fields directly;
`{name}` and `{slug}` are the explicit `name`, else the title slug, else the
ref. A template such as `'{layer}/{ref}.md'` needs `layer` on every node in the
view.
`bd export tree` and the other `bd export` choices are read-only snapshots, not
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
id. The version current in a view is the one its
parent's `contains` names — there is no per-node pointer. `bd clone REF` copies
the source file, including its declared `contains`, to the next free version of
the same logical id (or to `--version N`) and wires nothing into the current
view. `bd clone REF --subtree` clones every containment descendant and rewrites
each cloned parent's `contains` to the cloned children, producing a
self-contained copy while the original tree stays untouched; `--version` cannot
be combined with `--subtree`. `bd replace OLD NEW` is the separate wiring step:
it finds OLD in the store's default view and puts NEW at OLD's exact index in
its parent's `contains`, or repoints `ROOT` when OLD is the store root; OLD's
file stays as a peer. Clone and swap in one logical flow with `bd clone REF
--subtree` then `bd replace REF <printed new root ref>`. If OLD is outside the
default view, `bd replace` errors and asks for `bd contain`; multiple parents is
an error. The `duplicate-id` rule still forbids both versions in one view; to
choose a different position, run `bd uncontain P OLD`,
then `bd contain P NEW --before NEXT`. `bd delete REF` removes one version
and refuses a `ROOT`, a reachable ref, or one referenced by any
`contains`/`links` unless `--force`.

Versions are alternatives inside one branch, not the solution boundary, and they
never sync across branches. To switch, use `bd clone REF` then `bd replace REF
NEW` (or repoint one parent with `bd uncontain` / `bd contain`), switch the work area with
`bd work REF`, or switch the store default with `bd root REF`. See
[Branches and versions](BRANCHES-AND-VERSIONS.md).

## Freshness

```sh
bd stale [--view REF]
bd reconcile [REF ...] [--all] [--view REF]
```

A link participates only with `propagates: true` (or an existing `pinned`). Editing
a propagating target makes the source edge stale until reconciled.

## Read-only projections

```sh
bd export tree REF --out DIR [--path-template T] [--title-field F] [--summary-field F] [--clean] [--force]
bd export context --view REF --out DIR
bd export dot     --view REF --out FILE [--color-by FIELD] [--shape-by FIELD]
```

`bd export tree` is the single read-only tree projection. `context` writes fresh
node bodies plus `STALE.md` and `AGENTS.md`. `dot` is Graphviz.

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
| `bare-ref` / `invalid-ref` in data | `contains`, `links`, and `ROOT` need full `id-version` refs. A classic bare-file store converts once with `bd migrate`. |
| `duplicate-id` | One view holds two versions of the same logical id. `bd uncontain` the unwanted one; `bd contain` refuses this clash up front. |
| Detached work file | `bd work --status`, then `bd work --writeback`. Switching views with detached files is refused until you do. |
| Want two work folders | Not supported. `bd_work/` is the single area; switch with `bd work REF`. |
| Stale layout after branch change | `bd work REF --clean`. |
| Dangling link after removing a node | `bd check`, then `bd unlink` or restore the node. |
| Node too large | Split it, or raise `--max-lines` / `--max-chars`. |
| `bd_work/` in git status | `bd init` adds it to `.gitignore`; add `bd_work/` if the project predates that. |
