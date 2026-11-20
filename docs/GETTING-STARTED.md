# Getting started

This guide goes from no store to a browsable, editable graph with a work folder,
typed links, and a second solution in a git worktree.

You need Python 3.10+ and PyYAML. From a clone, install the package:

```sh
pip install .
bd --help
```

## 1. Create a store

```sh
mkdir -p ~/graphs/my-graph
cd ~/graphs/my-graph
bd init
```

`bd init` creates the store and ignores the work area:

```
.bd_tree/nodes/1.md
.gitignore          # bd_work/
```

```markdown
---
id: 1
title: Root
home: 1.md
contains: []
---
# Root

State the intent of this graph here.
```

`id` is identity and `contains` is the ordered child list. The rest of the front
matter is arbitrary.

Add two nodes and inspect the tree:

```sh
bd new --parent 1 --field title="Why does this exist?" --field layer=intent
bd new --parent 1 --field title="What is true?"       --field layer=claims
bd tree 1
```

```
1 Root
+- 2 Why does this exist?
`- 3 What is true?
```

`bd new` assigns the next integer and appends it to the parent's `contains`.
`layer` is metadata only; the tool knows no layer vocabulary.

```sh
bd check
```

```
3 nodes, 0 errors, 0 warnings (view 1)
```

## 2. Browse

```sh
bd tree 1 --depth 2
bd show 1+1 --max-chars 400
bd ls 1 --columns ref,title,layer
bd find true
bd path 2
```

- `tree` is the map.
- `show REF+N` prints the node body plus N levels of descendants.
- `ls` is the table view.
- `find` searches titles, summaries, bodies, and front-matter fields.
- `path` prints the ancestor chain.

Exit codes: `bd check` returns 1 on errors and 0 on clean. Structural commands
return 2 on refusal.

## 3. Edit in the work area

`bd work` renders a view as a tree of symlinks in the project's single writable
work area, `<project>/bd_work/`. Editing a link edits the store.

```sh
bd work 1
work_dir=$(bd work 1 --print)
ls "$work_dir"
```

```
1.md
intent/2.md
claims/3.md
INDEX.md  AGENTS.md  REFS.md
```

The path comes from `home` when present, otherwise from a template:

```sh
$EDITOR "$work_dir/claims/3.md"
bd work 1 --status
bd check
```

`--status` reports `ok`, `missing`, `wrong-target`, `detached`, `stray`, or
`stale-ref`. If an editor replaces a symlink with a regular file:

```sh
bd work 1 --status
bd work 1 --writeback
```

`--writeback` writes the detached content to the original node, refuses files
without valid front matter, and re-links them.

There is exactly one writable work area. `bd work REF` switches it to another
view by replacing its contents: stale links are removed, and `INDEX.md`,
`REFS.md`, and `AGENTS.md` are rewritten. Never keep two work folders side by
side.

```sh
bd work 1-1        # switch <project>/bd_work to another view
bd work 1          # switch back
```

Read-only snapshots (`bd view`, `bd export`) are separate disposable exports,
not a second work area.

## 4. Structure and typed links

Reorder or move a child:

```sh
bd uncontain 1 3
bd contain 1 3 --before 2
bd tree 1
```

`contain` refuses cycles and duplicates. It materialises an inherited `contains`
list before editing, so a version never silently inherits a changed order.

Add a typed edge and track freshness:

```sh
bd link 3 1 --type serves --propagates
bd stale
```

Then edit the intent body in `.bd_tree/nodes/1.md`:

```sh
printf '\nA new constraint.\n' >> .bd_tree/nodes/1.md
bd stale
```

```
3 -> 1 (serves): stale
```

Reconcile after reviewing the change:

```sh
bd reconcile 3
bd stale
```

`--propagates` is opt-in; a `see_also` edge never goes stale. Pins are body
hashes, so they survive a rebase.

Remove an edge:

```sh
bd unlink 3 1 --type serves
```

## 5. Switch between full trees

Two moves: point the store at another root ref, or repoint one parent.

```sh
bd fork 1 --version 1        # alternative root; contains materialised now
bd uncontain 1-1 3
bd tree 1-1                  # inspect the alternative before switching
bd root 1-1                  # write ROOT; tree, ls, work, check default here
bd tree
bd root                      # 1-1  (ROOT)
bd root --clear              # back to the lowest main ref
```

`ROOT` is one ref on one line at the store top level. An explicit ref or
`--root-ref` still wins over it; with no `ROOT`, the lowest main ref is the root.

Repoint one parent when only part of the tree moves:

```sh
bd uncontain 1 3
bd contain 2 3               # node 3 now hangs under 2
```

`bd promote` is not a switch: it copies one version onto main. `bd versions 1`
and `bd fork 1` show and create the alternatives.

## 6. A second solution with git

A solution is a git branch in a worktree; the flat store is the merge unit.

```sh
git init -b main
git add -A
git commit -m "init graph"

bd solution new sol-a
```

`bd solution new` prints:

```
worktree /home/you/graphs/sol-a
branch sol-a
store .
cd /home/you/graphs/sol-a
BD_ROOT=. bd work 1
```

```sh
cd ../sol-a
bd work 1
$EDITOR .bd_tree/nodes/1.md
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

If the project is nested inside the repo, `BD_ROOT` is the project path relative
to the worktree, for example `examples`.

## 7. Feed an agent

Two modes:

```sh
# writable: the single work area for one view
bd work 1

# read-only snapshot: fresh nodes, plus STALE.md and AGENTS.md
bd export context --view 1 --out /tmp/bd-context-1
```

`bd work` writes `<project>/bd_work/` and is the only work area; the export
directory is a disposable snapshot, not a second area. Both contain an
`AGENTS.md`; the work area also records the branch, commit, and worktree. Tell
the agent to read exactly one directory and not to read outside it. To change
view, switch the same area with `bd work REF`.

## 8. Use an existing markdown tree

There is no generic importer yet. The pattern is:

1. One file per node under the store's `nodes/` (`.bd_tree/nodes/` in a project
   layout), named by a running integer.
2. `id` matches the filename.
3. `contains` lists the ordered children.
4. Optional `home` gives the presentation path; otherwise use
   `--path-template`.
5. `links` holds typed edges; prose citations are separate.

`examples/` is a small worked project laid out this way, with its store under
`examples/.bd_tree/`: one file per node, `contains` listing ordered children, and
versions as alternatives.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `bd: unknown ref '1'` | No store found. Run from the project root or store root, or set `BD_ROOT` to the directory containing `nodes/` (or `.bd_tree/nodes/`). |
| `bd check` sees the wrong store | `BD_ROOT` or `--root` points elsewhere. `bd` uses the nearest `nodes/` or `.bd_tree/nodes/` upward. |
| `root-ref-missing` / `invalid-root` | The `ROOT` file names an absent ref or is malformed. Fix it, or run `bd root --clear`. |
| `bd work` refuses to switch | `bd_work/` has detached or stray files. Run `--status`, then `--writeback` to keep them or `--clean` to discard them. |
| Edit did not reach the node | The editor replaced the symlink. Run `--status`, then `--writeback`. |
| Want two work folders | Not supported. `bd_work/` is the single area; switch with `bd work REF`. |
| `bd_work/` appears in git status | `bd init` adds it to `.gitignore`; add `bd_work/` if the project predates that. |
| Work folder points at missing files | The branch changed under the layout. Rebuild with `bd work REF --clean`. |
| Size warning on a node | Cosmetic by default. Split the node, or pass `--max-lines` / `--max-chars`. |

## Next

- Command reference: [`CHEATSHEET.md`](CHEATSHEET.md)
- Model and decisions: [`DESIGN.md`](DESIGN.md)
- Change the tool: [`DEVELOPING.md`](DEVELOPING.md)
- Agent rules: [`../AGENTS.md`](../AGENTS.md)
