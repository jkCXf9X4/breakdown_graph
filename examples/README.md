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

Every node file is `<id>-<version>.md`; this store ships one version per id.
`ROOT` names `20-1`, the only containment root.

## A header-free, chained tree

`20-1` has no grouping nodes: every node states a claim, and `contains` is a
single chain from Intent to Evolution. Layer order is the chain; layer identity
is a root-relative `section`:

| Layer | Nodes | `section` |
| --- | --- | --- |
| Intent | `21-1` carrier, `22-1` leaf | `/00-intent` |
| Product | `23-1` carrier, `24-1` leaf | `/01-product` |
| Architecture | `25-1` carrier, `26-1` leaf | `/02-architecture` |
| Implementation | `27-1` carrier, `28-1` leaf | `/03-implementation` |
| Verification | `29-1` carrier, `30-1` leaf | `/04-verification` |
| Operation | `31-1` carrier, `32-1` leaf | `/05-operation` |
| Evolution | `33-1` carrier, `36-1` stage, `34-1`/`35-1` leaves | `/06-evolution`, `suggested`, `01-placement`/`02-snapshots` |

```text
20-1 -> 21-1 -> 23-1 -> 25-1 -> 27-1 -> 29-1 -> 31-1 -> 33-1 -> 36-1
        leaf     leaf     leaf     leaf     leaf     leaf     stage   {34-1, 35-1}
```

A leading `/` resolves the directory from the output root, so layer carriers and
their leaves are siblings. A relative section inherits the parent prefix: `36-1`
opens `06-evolution/suggested/` once, and its leaves declare only `01-placement`
and `02-snapshots`. Because `36-1` is a real node, the stage is also a view root
(`bd tree 36-1`) and a link target in its own right, parallel to the layer chain;
links may target the stage or skip it for a leaf.

That is both axes in one view: the seven layers are sequential sibling
directories, Evolution has a nested `suggested/` stage, and that stage is itself
sequenced with `01-`/`02-` folders. Two sections may share a directory when at
most one of them opens a subtree; two nodes that both have containment children
on one directory are refused.

Cross-layer references are links, not second parents: `27-1` links `25-1`
(`implements`), `29-1` links `25-1` and `30-1` links `27-1` (`verifies`). A node
reached through two parents would be a `multiple-parents` error.

## Placement

The layer carriers are root-relative, so they stay as sibling directories; the
Evolution stage node and its leaves are relative and nest two levels:

```sh
bd work 20-1
```

```text
bd_work/
├── 00-root/product-breakdown-header-free.md
├── 00-intent/credibility-of-the-chain.md
├── 00-intent/no-layer-schema.md
├── 01-product/claims-are-closure-data.md
├── 01-product/two-axes.md
├── 02-architecture/contains-is-ordered.md
├── 02-architecture/links-is-a-dag.md
├── 03-implementation/bd-check-validates.md
├── 03-implementation/bd-tree-renders.md
├── 04-verification/exit-code-tests.md
├── 04-verification/multiple-parents-rejected.md
├── 05-operation/exports-are-disposable.md
├── 05-operation/run-check-and-stale.md
├── 06-evolution/per-folder-index.md
└── 06-evolution/suggested/
    ├── suggested-work.md
    ├── 01-placement/section-flat-idea.md
    └── 02-snapshots/snapshot-list-and-prune.md
```

`--path-template` still overrides the whole layout when a different route is
wanted. `INDEX.md` indents by the chain while the folders follow the section
layout — the same gap as the per-folder-index item (`33-1`, `34-1` here;
`59-1` in `docs/breakdown`).

## Try it

```sh
cd examples
bd root                         # 20-1  (ROOT)
bd tree                         # the chain, two levels
bd tree 20-1 --depth 0          # the whole chain
bd find links --limit 3
bd path 30-1                    # ancestor chain to a leaf
bd tree 36-1                    # the stage as its own parallel view
bd work 20-1                    # layer folders plus the nested stage
bd current                      # <project>/bd_work (view 20-1)
bd edit 22-1                    # path inside the active view
```

These commands assume the package is installed (`pip install .` from the clone).

`ROOT` holds one full ref on one line. An explicit ref where a command takes one
wins over it; with no explicit ref, `ROOT` wins over the lowest available node by
`(id, version)`.

## Render outputs

From this directory:

```sh
bd check
bd work 20-1
bd export tree 20-1 --out /tmp/bd-tree-20-1
bd export context --view 20-1 --out /tmp/bd-context-20-1
bd export dot --view 20-1 --out /tmp/bd-graph-20-1.dot
```

The `/tmp` outputs are read-only snapshots, not the work area. `bd_work/` is
ignored by `examples/.gitignore`, so `git status` shows only node edits.
