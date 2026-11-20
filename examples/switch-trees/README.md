# Switch trees

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
cd examples/switch-trees
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
