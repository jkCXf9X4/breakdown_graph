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
.bd_tree/nodes/1-1.md
.gitignore          # bd_work/
```

```markdown
---
id: 1
title: Root
contains: []
---
# Root

State the intent of this graph here.
```

The filename is identity and version: logical id `1`, version `1`. `contains` is
the ordered child list of full refs. The rest of the front matter is arbitrary.
`bd init` writes no `name` or `section`, so the title `Root` lands at
`1-1-root.md`; add `name` (or `section`) only to place it elsewhere.

Add two nodes and inspect the tree:

```sh
bd new --parent 1-1 --field title="Why does this exist?" --field layer=intent
bd new --parent 1-1 --field title="What is true?"       --field layer=claims
bd tree 1-1
```

```
1-1 Root
+- 2-1 Why does this exist?
`- 3-1 What is true?
```

`bd new` allocates the next global integer at version 1 and appends that full
ref to the parent's `contains`. It seeds `title` and `summary` as empty
placeholders; `--field` overrides them. `layer` is metadata only; the tool knows
no layer vocabulary.

```sh
bd check
```

```
3 nodes, 0 errors, 0 warnings (view 1-1)
```

## 2. Browse

```sh
bd tree 1-1 --depth 2
bd show 1-1+1 --max-chars 400
bd tree 1-1 --columns ref,title,layer
bd find true
bd path 2-1
```

- `tree` is the map; `--columns F,F` prints a table instead.
- `show REF+N` prints the node body plus N levels of descendants.
- `find` searches titles, summaries, bodies, and front-matter fields.
- `path` prints the ancestor chain.

Exit codes: `bd check` returns 1 on errors and 0 on clean. Structural commands
return 2 on refusal.

## 3. Edit in the work area

`bd work` renders a view as a tree of symlinks in the project's single writable
work area, `<project>/bd_work/`. Editing a link edits the store.

```sh
bd work 1-1
bd current                 # <project>/bd_work (view 1-1)
work_dir=$(bd current --path)
ls "$work_dir"
```

```
1-1-root.md
intent/why-does-this-exist.md
claims/what-is-true.md
INDEX.md  AGENTS.md  REFS.md
```

Only the node `.md` files are symlinks; `INDEX.md`, `AGENTS.md`, and `REFS.md`
are regular generated files. `section` is the only presentation key that opens
directories: `section: true` names the directory by the node's placement name
(explicit `name`, else the `title` slug, else the ref), and its containment
descendants land inside; with `title: Evolution` the node becomes
`evolution/evolution.md`. `section: "<dir>"` names the directory verbatim.
Otherwise a node is placed by `name` (`<name>.md`), else `<ref>-<title-slug>.md`,
else `<ref>.md` when there is no usable title. `--path-template` sets another
route for the whole view:

```sh
$EDITOR "$(bd edit 3-1)"
bd work --status
bd check
```

`bd edit REF` prints the ref's absolute path inside the active view and errors if
the ref is not there. `bd current` is read-only; `--path` prints only the path and
`--view` only the ref, and it errors if no area exists.

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

A work area may also materialize only the first `N` descendant levels of a view:
`bd work REF+N`, or `bd work REF --depth N`, where `0` materializes the root
alone and `--depth` overrides a suffix. This is the same `+N` suffix `bd show`
and `bd tree` accept. The view itself is still the full containment closure of
one ref, not a smaller view. The generated headers carry `REF+N`, so
`bd current --view` reports it and `bd edit` only resolves refs that are
materialized. A rebuild with a different depth, or a plain `bd work REF`,
replaces the area.

```sh
bd work 1-1+1      # root plus immediate children
bd current --view  # 1-1+1
bd work 1-1        # restore the full closure (headers drop the suffix)
```

Section 5 creates a second root version; `bd work 1-2` switches this same area
to that view.

Read-only snapshots (`bd export tree`, `bd export context`, `bd export dot`) are
separate disposable exports, not a second work area.

## 4. Structure and typed links

Reorder or move a child:

```sh
bd uncontain 1-1 3-1
bd contain 1-1 3-1 --before 2-1
bd tree 1-1
```

`contain` refuses cycles and duplicates, accepts a bare id as a selector, and
writes full refs. `contains` is the declared list: nothing is inherited, so
every version that has children lists them itself.

Add a typed edge and track freshness:

```sh
bd link 3-1 1-1 --type serves --propagates
bd stale
```

Then edit the intent body through the work area:

```sh
printf '\nA new constraint.\n' >> "$(bd edit 1-1)"
bd stale
```

Edit through `bd_work/`; `bd edit REF` resolves the path for you. A direct edit of
`.bd_tree/nodes/1-1.md` is an escape hatch when no work area is active: it
bypasses the active-view check, so prefer `bd edit REF`.

```
3-1 -> 1-1 (serves): stale
```

Reconcile after reviewing the change:

```sh
bd reconcile 3-1
bd stale
```

`--propagates` is opt-in; a `see_also` edge never goes stale. Pins are body
hashes, so they survive a rebase.

Remove an edge:

```sh
bd unlink 3-1 1-1 --type serves
```

## 5. Switch between full trees

Two separate moves: change the default view root, or switch the view held by the
work area. You can also repoint one parent.

```sh
bd clone 1-1 --version 2     # copy the root to a second peer, keeping contains
bd uncontain 1-2 3-1         # prune one child from the alternative
bd tree 1-2                  # inspect the alternative before switching
bd root 1-2                  # write ROOT; tree, find, check default here
bd tree
bd root                      # 1-2  (ROOT)
bd work 1-2                  # switch the work area to the alternative view
bd current                   # <project>/bd_work (view 1-2)
bd root --clear              # back to the lowest (id, version), here 1-1
```

`ROOT` is one full ref on one line at the store top level. An explicit ref where
a command takes one still wins over it; with no `ROOT`, the lowest
`(id, version)` is the root. `bd check --view REF` only narrows reporting, not
the checked root. `bd root` changes the default root used by commands but does
not rewrite the view already in `<project>/bd_work/`; run `bd work REF` for
that. `bd views` lists the containment roots and marks the default with `*`.

Repoint one parent when only part of the tree moves:

```sh
bd uncontain 1-1 3-1
bd contain 2-1 3-1           # node 3-1 now hangs under 2-1
```

A parent's `contains` names the version that is current in that view. `bd versions 1` lists the peers and `bd clone 1-1`
creates a new one with the same declared `contains`, wired into no view.

`bd clone REF --subtree` copies a node and its whole containment subtree,
rewiring each cloned parent to its cloned children so the copy is
self-contained; the original tree is untouched and `--version` cannot be
combined with `--subtree`. `bd replace OLD NEW` is the separate wiring step: it
finds OLD in the store's default view and puts NEW at OLD's exact index in its
parent's `contains`, or repoints `ROOT` when OLD is the store root; OLD's file
stays as a peer. Clone and swap in one logical flow with `bd clone REF --subtree`
then `bd replace REF <printed new root ref>`. If OLD is outside the default
view, `bd replace` errors and asks for `bd contain`; multiple parents is an
error. The `duplicate-id` rule still forbids both versions in one view, so to
choose a different position, run `bd uncontain P OLD`, then `bd contain P NEW
--before NEXT`.

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
project .
cd /home/you/graphs/sol-a
bd work 1-1
```

The project directory is printed relative to the worktree. In a nested project,
`cd` into the printed project path instead, for example
`cd /home/you/graphs/sol-a/examples`, then run the printed `bd work` command.

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
project path inside the worktree, for example `cd /home/you/graphs/sol-a/examples`.
Store discovery then finds `.bd_tree/` there. From the worktree root it also
finds a single store below the current directory; `BD_ROOT` is only needed when
several stores are below that root.

## 7. Feed an agent

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
`AGENTS.md`; the work area also records the branch, commit, and worktree. Tell
the agent to read exactly one directory and not to read outside it, and to use
`bd edit REF` rather than guessing paths. To change view, switch the same area
with `bd work REF` and confirm with `bd current`.

## 8. Use an existing markdown tree

There is no generic importer yet. The pattern is:

1. One file per node version under the store's `nodes/` (`.bd_tree/nodes/` in a
   project layout), named `<id>-<version>.md` with a running integer id and a
   version starting at `1`.
2. `id` matches the logical id in the filename.
3. `contains` lists ordered children as full `id-version` refs.
4. `section` opens directories; `name` sets the file stem. Without `section`,
   the path is `<name>.md`, else `<ref>-<title-slug>.md`, else `<ref>.md` when
   the title is unusable. `--path-template` sets another route for the whole view.
5. `links` holds typed edges with full refs; prose citations are separate.

`examples/` is a small worked project laid out this way, with its store under
`examples/.bd_tree/`: one file per node version, `contains` listing ordered
children, and peer versions as alternatives.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `bd: unknown ref '1-1'` | No store found, or the ref is absent from the selected view. Run from the project root or store root, or set `BD_ROOT` to the directory containing `nodes/` (or `.bd_tree/nodes/`). |
| `bd check` sees the wrong store | `BD_ROOT` or `--root` points elsewhere. `bd` uses the nearest `nodes/` or `.bd_tree/nodes/` upward. |
| `root-ref-missing` / `invalid-root` | The `ROOT` file names an absent ref or is malformed. Fix it, or run `bd root --clear`. |
| `bare-ref` / `invalid-ref` in data | `contains`, `links`, and `ROOT` need full `id-version` refs. Convert a classic bare-file store once with `bd migrate`. |
| `duplicate-id` | A view holds two versions of the same logical id. `bd uncontain` the unwanted one. |
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
- Model and decisions: [`DESIGN.md`](DESIGN.md)
- Change the tool: [`DEVELOPING.md`](DEVELOPING.md)
- Agent rules: [`../AGENTS.md`](../AGENTS.md)
