# Cheatsheet

Run `bd <command> --help` for the full flag list. Exit codes: 0 success, 1 check
or navigation failure, 2 structural refusal.

## Environment

```sh
export BD_ROOT=path/to/project       # or path/to/store
bd --root path/to/project <command>  # explicit per command
```

`bd` walks up from the current directory and recognises both `nodes/` and
`.bd_tree/nodes/`; one store per checkout.

## Tree root

```sh
bd root                             # print: <ref>  (ROOT|lowest main)
bd root REF                         # write ROOT: one ref line, e.g. 1-4
bd root --clear                     # delete ROOT; lowest main ref is the default
```

`ROOT` sits at the store top level and holds one ref on one line, nothing else.
It is the default view root for `tree`, `ls`, `find`, `grep`, `work`, `check`,
`stale`, and `reconcile`, and the view root `bd check` reports. An explicit ref
or `--root-ref` wins over `ROOT`; `ROOT` wins over the lowest main ref. A
declared but missing ref is `root-ref-missing`; malformed content is
`invalid-root`. `bd root` does not rewrite the view already in the work area;
use `bd work REF` for that.

## Start

```sh
bd init [DIR]                       # create .bd_tree/nodes/1.md and .gitignore
bd new --parent REF --field KEY=VALUE ... [--body TEXT]
```

`bd new` assigns the next integer and appends to the parent's `contains`.

## Inspect

```sh
bd check [--view REF] [--require FIELD] [--max-lines N] [--max-chars N]
bd tree [REF] [--depth N] [--summary] [--fields F,F]
bd show REF[+N] [--max-chars N] [--no-body] [--fields F,F] [--path]
bd ls [REF] [--depth N] [--columns F,F] [--max-chars N]
bd find QUERY [--view REF|--all] [--field F] [--regex] [--where K=V ...] [--limit N]
bd grep PATTERN [--view REF|--all] [--field F] [--where K=V ...] [--limit N]
bd path REF
```

- `show 5+2`: node 5 plus two levels of descendant bodies. With N > 0 the body
  is capped at 4000 characters per node unless `--max-chars N` is given;
  `--max-chars 0` prints the full body.
- `tree 5 --depth 0`: whole subtree. `ls 5 --depth 0` is also unlimited. A
  missing ref uses the store root.
- `ls 1 --columns ref,title,layer,status`: arbitrary fields as columns.
- `find` searches title, summary, body, and all string fields. It searches the
  default view unless `--view REF` or `--all` is given; output stays capped.
- `grep` has the same view scope: default view, `--view REF`, or `--all`.

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
- Structural commands preserve body bytes and unrelated front matter.

## Work folders

```sh
bd work [REF] [--path-template T] [--status] [--writeback] [--clean] [--print]
bd current [--path|--view]
bd views
bd edit REF
```

- Default: `<project>/bd_work/`. A project has exactly one writable work area;
  a different REF replaces its contents.
- Node `.md` files are symlinks to the store's `nodes/<ref>.md`
  (`.bd_tree/nodes/<ref>.md` in a project layout). `INDEX.md`, `AGENTS.md`, and
  `REFS.md` are regular generated files, never symlinks.
- `bd current` is read-only: it prints `<project>/bd_work (view <ref>)`;
  `--path` prints only the path, `--view` only the ref. It errors if no work
  area exists.
- `--print` prints only the directory, is read-only, does not build, and errors
  if no area exists.
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
bd work 1                                      # write <project>/bd_work for view 1
bd current                                     # <project>/bd_work (view 1)
bd work 5                                      # switch the same area to view 5
bd work 1 --path-template '{layer}/{ref}.md'
```

`home` is an explicit full path and wins over everything. Otherwise `folder` is
the directory prefix and `name` the file stem; without a `name` the file uses
the slug of `title`, falling back to the ref. With none of these, a node lands
at `<ref>.md`. `bd new --field layer=...` derives `folder` from the first of
`layer`, `group`, `type`:

```yaml
folder: claims            # 06-evolution/suggested also works
title: The Main Thesis    # -> claims/the-main-thesis.md
name: custom-name         # optional override -> claims/custom-name.md
home: claims/2.md         # explicit full path; wins over folder/name
```

`--path-template '{folder}/{name}.md'` uses the computed fields directly; a
template such as `'{layer}/{ref}.md'` needs `layer` on every node in the view.
`bd view` and `bd export` are read-only snapshots, not a second work area.

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
bd fork ID [--version N]
bd promote REF [--keep]
bd retire-version REF
bd diff LEFT RIGHT
```

Versions are alternatives inside one branch, not the solution boundary, and they
never sync across branches. `bd fork` materialises the effective `contains` list
into the version, so later edits to main's containment do not change it; a
hand-written version that omits `contains` still inherits main's list.
`bd promote` copies one version onto main in the current checkout only, so check
out or merge the branch first — it is not a way to switch trees. Switch the
work area with `bd work REF`, the store default with `bd root REF`, or repoint
one parent with `bd uncontain` / `bd contain`. See
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
bd view REF --out DIR [--path-template T] [--clean]
bd export context --view REF --out DIR
bd export dot     --view REF --out FILE [--color-by FIELD] [--shape-by FIELD]
```

`bd view` is the single read-only tree projection. `context` writes fresh node
bodies plus `STALE.md` and `AGENTS.md`. `dot` is Graphviz.

## Git patterns

```sh
git worktree add ../sol-a -b sol-a
git diff main..sol-a -- .bd_tree/nodes/    # or your default branch
git merge sol-a
git cherry-pick <commit>
git restore --source=sol-a -- .bd_tree/nodes/5.md
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
| Wrong store | `BD_ROOT` or `--root`; `bd` uses the nearest `nodes/` or `.bd_tree/nodes/` upward. |
| `bd current` errors | No work area exists. Build one with `bd work [REF]`. |
| `bd edit REF` errors | The ref is not in the active view. Switch with `bd work REF` or pass a ref that is present. |
| `root-ref-missing` / `invalid-root` | The `ROOT` file names an absent ref or is malformed. Fix it, or run `bd root --clear`. |
| Detached work file | `bd work --status`, then `bd work --writeback`. Switching views with detached files is refused until you do. |
| Want two work folders | Not supported. `bd_work/` is the single area; switch with `bd work REF`. |
| Stale layout after branch change | `bd work REF --clean`. |
| Dangling link after removing a node | `bd check`, then `bd unlink` or restore the node. |
| Node too large | Split it, or raise `--max-lines` / `--max-chars`. |
| `bd_work/` in git status | `bd init` adds it to `.gitignore`; add `bd_work/` if the project predates that. |
