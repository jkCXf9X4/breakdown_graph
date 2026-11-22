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

| Layer | Carrier | Leaf | `section` (every node) |
| --- | --- | --- | --- |
| Intent | `21-1` | `22-1` | `/00-intent` |
| Product | `23-1` | `24-1` | `/01-product` |
| Architecture | `25-1` | `26-1` | `/02-architecture` |
| Implementation | `27-1` | `28-1` | `/03-implementation` |
| Verification | `29-1` | `30-1` | `/04-verification` |
| Operation | `31-1` | `32-1` | `/05-operation` |
| Evolution | `33-1` | `34-1` | `/06-evolution` |

```text
20-1 -> 21-1 -> 23-1 -> 25-1 -> 27-1 -> 29-1 -> 31-1 -> 33-1
        leaf     leaf     leaf     leaf     leaf     leaf     leaf
```

A leading `/` resolves the directory from the output root, so a carrier and its
leaf are siblings instead of nesting. A relative section still inherits the
parent prefix: `section: suggested` under `/06-evolution` lands at
`06-evolution/suggested/`.

Cross-layer references are links, not second parents: `27-1` links `25-1`
(`implements`), `29-1` links `25-1` and `30-1` links `27-1` (`verifies`). A node
reached through two parents would be a `multiple-parents` error.

## Placement

Every node is root-relative, so the default work area is already flat:

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
└── 06-evolution/section-flat-idea.md
```

`--path-template` still overrides the whole layout when a different route is
wanted. `INDEX.md` indents by the chain while the folders stay flat — the same
gap as the per-folder-index item (`33-1`, `34-1` here; `59-1` in
`docs/breakdown`).

## Try it

```sh
cd examples
bd root                         # 20-1  (ROOT)
bd tree                         # the chain, two levels
bd tree 20-1 --depth 0          # the whole chain
bd find links --limit 3
bd path 30-1                    # ancestor chain to a leaf
bd work 20-1                    # flat layer folders
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
