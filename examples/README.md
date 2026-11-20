# Example project

This folder is a complete bd project and a valid store. The store under
`.bd_tree/` is the only source of truth; `bd_work/` is the single writable work
area, derived and ignored. There is no `build/`.

## Layout

| Path | Produced by |
| --- | --- |
| `.bd_tree/nodes/` | hand-written node files, one per ref; the source of truth |
| `.bd_tree/ROOT` | hand-written store default: one ref on one line |
| `bd_work/` | `bd work <ref>`; the single writable work area, ignored |

`bd work <ref>` writes `bd_work/`; a different ref replaces its contents.
`bd view` and `bd export` produce read-only snapshots elsewhere (for example
under `/tmp`), never another work area.

## Switch trees

A five-id store with two complete trees over the same ids. `ROOT` selects the
default.

| Tree | Shape |
| --- | --- |
| main `1` | `1 -> {2, 5}`, `2 -> {3, 4}` |
| version `1-1` | `1-1 -> {5-1, 2-1}`, `2-1 -> {4-1, 3-1}` |

The version tree reorders and rewrites the same ids, so both trees are valid and
`bd check` stays clean. Nothing is promoted or copied over the main files.

## Try it

```sh
cd examples
bd root            # 1-1  (ROOT)
bd tree            # the version tree
bd tree 1          # the main tree
bd diff 1 1-1      # every id changed
bd root --clear    # default falls back to 1
bd root 1-1        # switch back
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
bd work 1                         # switch the same area to the main tree
bd view 1-1 --out /tmp/bd-view-1-1
bd view 1 --out /tmp/bd-view-1
bd export context --view 1-1 --out /tmp/bd-context-1-1
bd export dot --view 1-1 --out /tmp/bd-graph-1-1.dot
```

The `/tmp` outputs are read-only snapshots, not the work area. `bd_work/` is
ignored by `examples/.gitignore`, so `git status` shows only node edits.
