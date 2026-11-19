# Getting started

This guide takes you from no store to a browsable, editable graph with a work
folder, typed links, and a second solution in a git worktree.

You need Python 3.10+ and PyYAML. The repository ships `bin/bd`; no install step.

```sh
export PATH="/path/to/info_graph/bin:$PATH"
bd --help
```

## 1. Create a store

```sh
mkdir -p ~/graphs/my-graph
cd ~/graphs/my-graph
bd init
```

`bd init` creates one file:

```
nodes/1.md
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

`id` is identity. `contains` is the ordered child list. Everything else is
arbitrary front matter.

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
The `layer` field is just metadata; the tool does not know any layer vocabulary.

Check the store:

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

Exit codes matter: `bd check` returns 1 on errors, 0 on clean. Structural
commands return 2 on refusal.

## 3. Edit in a work folder

`bd work` renders a view as a tree of symlinks. Editing a link edits the store.

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

The path comes from `home` when present, otherwise from a template. Open a file
and edit it:

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

Several layouts of the same view can coexist:

```sh
bd work 1 --name flat --path-template '{ref}.md'
```

The default layout uses `home` when every node has one, so the first `bd work 1`
is the tree-shaped layout; `--name flat` is the numeric layout. Both point at the
same `nodes/` files. An edit through one is visible through the other.

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

Then edit the intent body in `nodes/1.md`:

```sh
printf '\nA new constraint.\n' >> nodes/1.md
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

`--propagates` is opt-in. A `see_also` edge never goes stale. Pins are body
hashes, so they survive a rebase.

Remove an edge:

```sh
bd unlink 3 1 --type serves
```

## 5. A second solution with git

A solution is a git branch checked out in a worktree. The flat store is the merge
unit.

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

Follow it:

```sh
cd ../sol-a
bd work 1
$EDITOR nodes/1.md
bd check
git add -A && git commit -m "sol-a: alternative intent"
```

Compare without switching:

```sh
cd ../my-graph
git diff main..sol-a -- nodes/
bd solution list
```

Remove the checkout when done; the branch remains:

```sh
bd solution remove sol-a
```

If the store is nested inside the repo, `BD_ROOT` is the store path relative to
the worktree, for example `workspace/licentiate-n`.

## 6. Feed an agent

Two modes:

```sh
# read-only: only fresh nodes, plus STALE.md and AGENTS.md
bd export context --view 1 --out build/ctx

# writable layout: edits write through to nodes/
bd work 1
```

Both produce an `AGENTS.md`. The work folder version also records the git branch,
commit, and worktree. Point the agent at that directory and tell it not to read
outside it.

## 7. Use an existing markdown tree

There is no generic importer yet. The pattern is:

1. One file per node under `nodes/`, named by a running integer.
2. `id` matches the filename.
3. `contains` lists the ordered children.
4. Optional `home` gives the presentation path; otherwise use
   `--path-template`.
5. `links` holds typed edges; prose citations are separate.

`workspace/licentiate/` and `tools/migrate_licentiate.py` are a worked example:
typed ids were renumbered, containment was derived from the citation graph, and
bodies were checked byte-for-byte after id substitution.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `bd: unknown ref '1'` | No store found. Run from the store root or set `BD_ROOT` to the directory containing `nodes/`. |
| `bd check` sees the wrong corpus | `BD_ROOT` or `--root` points elsewhere. `bd` uses the nearest `nodes/` upward. |
| `bd work` refuses a directory | It has detached or stray files. Run `--status`, then `--writeback` or `--clean`. |
| Edit did not reach the node | The editor replaced the symlink. Run `--status`, then `--writeback`. |
| `build/` appears in git status | Add `build/` to `.gitignore`. |
| Work folder points at missing files | The branch changed under the layout. Rebuild with `bd work REF --clean`. |
| Size warning on a node | Cosmetic by default. Split the node, or pass `--max-lines` / `--max-chars`. |

## Next

- Command reference: [`CHEATSHEET.md`](CHEATSHEET.md)
- Model and decisions: [`DESIGN.md`](DESIGN.md)
- Change the tool: [`DEVELOPING.md`](DEVELOPING.md)
- Agent rules: [`../AGENTS.md`](../AGENTS.md)
