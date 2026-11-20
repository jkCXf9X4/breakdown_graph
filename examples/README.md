# Example project

This folder is a complete bd project and a valid store. The store under
`.bd_tree/` is the only source of truth; `bd_work/` is the single writable work
area, derived and ignored. Read-only projections go elsewhere and are never a
second work area.

## Layout

| Path | Produced by |
| --- | --- |
| `.bd_tree/nodes/` | hand-written node files, one per `id-version`; the source of truth |
| `.bd_tree/ROOT` | hand-written store default: one full ref on one line |
| `bd_work/` | `bd work <ref>`; the single writable work area, ignored |

Every node file is `<id>-<version>.md`; `1-1` and `1-2` are peer versions of
logical node `1`. Work file names come from the title: `<ref>-<title>`, slugged.
The default `1-1` view reads `1-1-root-alternative.md`, `5-1-limits.md`,
`2-1-method.md`, `4-1-analysis.md`, `3-1-data.md`, `6-1-great-stuff.md`, and
`7-1.md`; the other `1-2` view reads `1-2-root.md`, `2-2-method.md`,
`5-2-limits.md`, `3-2-data.md`, and `4-2-analysis.md`. `folder`/`name` override
the default placement for stores that want directories.

`bd work <ref>` writes `bd_work/`; a different ref replaces its contents.
`bd current` reports the area and its view, and `bd edit REF` prints a ref's path
inside that view. `bd export tree` and the other `bd export` choices produce
read-only snapshots elsewhere (for example under `/tmp`), never another work
area.

## Switch trees

A seven-id store with two trees over the same ids. `ROOT` selects the default
root (`1-1`); `bd work REF` selects the view in the work area.

| Tree | Shape |
| --- | --- |
| `1-1` (default) | `1-1 -> {5-1, 2-1}`, `2-1 -> {4-1, 3-1}`, `5-1 -> {6-1}`, `6-1 -> {7-1}` |
| `1-2` | `1-2 -> {2-2, 5-2}`, `2-2 -> {3-2, 4-2}` |

The `1-1` tree reorders and rewrites the same ids, and adds `6-1` under `5-1`
and `7-1` under `6-1`, so both trees are valid and `bd check` stays clean.
Nothing is copied over another version.

## Try it

```sh
cd examples
bd root            # 1-1  (ROOT)
bd tree            # the default 1-1 tree
bd tree 1-2        # the other tree
bd diff 1-1 1-2    # ids differ across trees; 6-1 and 7-1 exist only on the left
bd root --clear    # default falls back to the lowest (id, version), 1-1
bd root 1-1        # switch the default back
bd views           # containment roots; default marked with *
bd work 1-1        # switch the work area to the default view
bd current         # <project>/bd_work (view 1-1)
bd edit 2-1        # path of ref 2-1 in the active view
```

These commands assume the package is installed (`pip install .` from the clone).

`bd versions 2` lists the peer files for one id (`2-1`, `2-2`), ascending by
version, with no privileged marker. Every version is an alternative for the same
logical node, so it needs no parent of its own to stay valid.

`ROOT` holds one full ref on one line. An explicit ref where a command takes one
wins over it; with no explicit ref, `ROOT` wins over the lowest available node by
`(id, version)`.

## Render outputs

From this directory:

```sh
bd check
bd work 1-1                       # write bd_work for the default tree
bd current                        # confirm the view actually there
bd work 1-2                       # switch the same area to the other tree
bd export tree 1-1 --out /tmp/bd-tree-1-1
bd export tree 1-2 --out /tmp/bd-tree-1-2
bd export context --view 1-1 --out /tmp/bd-context-1-1
bd export dot --view 1-1 --out /tmp/bd-graph-1-1.dot
```

The `/tmp` outputs are read-only snapshots, not the work area. `bd_work/` is
ignored by `examples/.gitignore`, so `git status` shows only node edits.
