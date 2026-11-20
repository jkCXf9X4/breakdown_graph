# Cheatsheet

Run `bd <command> --help` for the full flag list. Exit codes: 0 success, 1 check
or navigation failure, 2 structural refusal.

## Environment

```sh
export BD_ROOT=path/to/store        # directory containing nodes/
bd --root path/to/store <command>   # explicit per command
```

`bd` walks up from the current directory to find `nodes/`; one store per checkout.

## Tree root

```sh
bd root                             # print: <ref>  (ROOT|lowest main)
bd root REF                         # write ROOT: one ref line, e.g. 1-4
bd root --clear                     # delete ROOT; lowest main ref is the default
```

`ROOT` sits at the store top level and holds one ref on one line, nothing else.
It is the default view root for `tree`, `ls`, `work`, `check`, `stale`, and
`reconcile`, and the view root `bd check` reports. An explicit ref or
`--root-ref` wins over `ROOT`; `ROOT` wins over the lowest main ref. A declared
but missing ref is `root-ref-missing`; malformed content is `invalid-root`.

## Start

```sh
bd init [DIR]                       # create nodes/1.md
bd new --parent REF --field KEY=VALUE ... [--body TEXT]
```

`bd new` assigns the next integer and appends to the parent's `contains`.

## Inspect

```sh
bd check [--view REF] [--require FIELD] [--max-lines N] [--max-chars N]
bd tree [REF] [--depth N] [--summary] [--fields F,F]
bd show REF[+N] [--max-chars N] [--no-body] [--fields F,F] [--path]
bd ls [REF] [--depth N] [--columns F,F] [--max-chars N]
bd find QUERY [--field F] [--regex] [--where K=V ...] [--limit N]
bd grep PATTERN [--field F] [--where K=V ...] [--limit N]
bd path REF
```

- `show 5+2`: node 5 plus two levels of descendant bodies.
- `tree 5 --depth 0`: whole subtree. A missing ref uses the store root.
- `ls 1 --columns ref,title,layer,status`: arbitrary fields as columns.
- `find` searches title, summary, body, and all string fields.

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
bd work [REF] [--name NAME] [--path-template T] [--print]
bd work REF --status
bd work REF --writeback
bd work REF --clean
```

- Default: `<store>/build/work/<ref>`; `--name` gives `<ref>-<name>`.
- Every `.md` is a symlink to `nodes/<ref>.md`.
- `--print` emits only the directory.
- `--status`: `ok`, `missing`, `wrong-target`, `detached`, `stray`, `stale-ref`.
- `--writeback` keeps edits made by an editor that replaced a symlink.
- Re-running refreshes a healthy tree; detached or stray files block it.

Common layouts:

```sh
bd work 1                                      # home paths
bd work 5 --name subtree                       # subtree view
bd work 1 --name flat --path-template '{ref}.md'
bd work 1 --name claims --path-template '{layer}/{ref}.md'
```

`{layer}/{ref}.md` needs `layer` on every node in the view. The default uses
`home` when all nodes have one.

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
out or merge the branch first — it is not a way to switch trees. Switching is
`bd root REF` or repointing one parent with `bd uncontain` / `bd contain`. See
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
bd export tree    --view REF --out DIR
bd export context --view REF --out DIR
bd export dot     --view REF --out FILE [--color-by FIELD] [--shape-by FIELD]
```

`context` writes fresh node bodies plus `STALE.md` and `AGENTS.md`. `dot` is
Graphviz.

## Git patterns

```sh
git worktree add ../sol-a -b sol-a
git diff main..sol-a -- nodes/    # or your default branch
git merge sol-a
git cherry-pick <commit>
git restore --source=sol-a -- nodes/5.md
```

- The flat `nodes/` path is the merge unit.
- Worktrees are the simultaneous solutions.
- `git status` shows node edits, never the layout.

## Health checks

```sh
bd check
bd stale
bd work REF --status
git status --porcelain
python3 -m pytest -q
```

## Frequent fixes

| Problem | Fix |
| --- | --- |
| Wrong store | `BD_ROOT` or `--root`; `bd` uses the nearest `nodes/` upward. |
| `root-ref-missing` / `invalid-root` | The `ROOT` file names an absent ref or is malformed. Fix it, or run `bd root --clear`. |
| Detached work file | `bd work REF --status`, then `--writeback`. |
| Stale layout after branch change | `bd work REF --clean`. |
| Dangling link after removing a node | `bd check`, then `bd unlink` or restore the node. |
| Node too large | Split it, or raise `--max-lines` / `--max-chars`. |
| `build/` in git status | Add `build/` to `.gitignore`. |
