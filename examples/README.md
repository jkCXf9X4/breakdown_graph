# Example project

This folder is a complete bd project and a valid store. The store under
`.bd_tree/` is the only source of truth; `bd_work/` is the single writable work
area, derived and ignored. Read-only projections go elsewhere and are never a
second work area.

## Layout

| Path | Produced by |
| --- | --- |
| `.bd_tree/nodes/` | hand-written node files, one per ref; the source of truth |
| `.bd_tree/ROOT` | hand-written store default: one ref on one line |
| `bd_work/` | `bd work <ref>`; the single writable work area, ignored |

Work file names come from the title: `<ref>-<title>`, slugged. The version view
reads `1-1-root-alternative.md`, `2-1-method.md`, `3-1-data.md`,
`4-1-analysis.md`, `5-1-limits.md`, `6-great-stuff.md`; the main view reads
`1-root.md`, `2-method.md`, `5-limits.md`. `folder`/`name` override the default
placement for stores that want directories.

`bd work <ref>` writes `bd_work/`; a different ref replaces its contents.
`bd current` reports the area and its view, and `bd edit REF` prints a ref's path
inside that view. `bd view` and `bd export` produce read-only snapshots
elsewhere (for example under `/tmp`), never another work area.

## Switch trees

A six-id store with two trees over the same ids. `ROOT` selects the default
root; `bd work REF` selects the view in the work area.

| Tree | Shape |
| --- | --- |
| main `1` | `1 -> {2, 5}`, `2 -> {3, 4}` |
| version `1-1` | `1-1 -> {5-1, 2-1}`, `2-1 -> {4-1, 3-1}`, `5-1 -> {6}` |

The version tree reorders and rewrites the same ids, and adds `6` under `5-1`,
so both trees are valid and `bd check` stays clean. Nothing is promoted or
copied over the main files.

## Try it

```sh
cd examples
bd root            # 1-1  (ROOT)
bd tree            # the version tree
bd tree 1          # the main tree
bd diff 1 1-1      # ids differ across trees; 6 only exists on the right
bd root --clear    # default falls back to 1
bd root 1-1        # switch the default back
bd views           # containment roots; default marked with *
bd work 1-1        # switch the work area to the version view
bd current         # <project>/bd_work (view 1-1)
bd edit 2-1        # path of ref 2-1 in the active view
```

These commands assume the package is installed (`pip install .` from the clone).

`bd versions 2` lists the main and version files for one id. Every version is an
alternative for the same logical node, so it needs no parent of its own to stay
valid.

`ROOT` holds one ref on one line. An explicit ref or `--root-ref` wins over it.

## Render outputs

From this directory:

```sh
bd check
bd work 1-1                       # write bd_work for the version tree
bd current                        # confirm the view actually there
bd work 1                         # switch the same area to the main tree
bd view 1-1 --out /tmp/bd-view-1-1
bd view 1 --out /tmp/bd-view-1
bd export context --view 1-1 --out /tmp/bd-context-1-1
bd export dot --view 1-1 --out /tmp/bd-graph-1-1.dot
```

The `/tmp` outputs are read-only snapshots, not the work area. `bd_work/` is
ignored by `examples/.gitignore`, so `git status` shows only node edits.
