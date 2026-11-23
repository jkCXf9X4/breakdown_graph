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

## A fan-out header tree

`20-1` is the only containment root and the view's front page. It fans out into
three header nodes, one per layer, in pipeline order. A header is not a claim: it
is the folder that places its layer's claims in context. Its body says what the
folder answers; it never lists the children, because placement and sequence come
from the view — `contains` order plus the generated `INDEX.md` in every folder —
not from hand-maintained text.

| Layer | Header | Claims | `section` |
| --- | --- | --- | --- |
| Intent | `37-1` | `21-1` | `/00-intent` |
| Product | `38-1` | `24-1` | `/01-product` |
| Evolution | `43-1` | `33-1`, `36-1` stage, `34-1`/`35-1` leaves | `/02-evolution`, `suggested`, `01-placement`/`02-snapshots` |

```text
20-1 Product Breakdown
├── 37-1 Intent
│   └── 21-1 Credibility belongs to the producing chain
├── 38-1 Product
│   └── 24-1 Two axes, containment and links
└── 43-1 Evolution
    ├── 33-1 One index per folder
    └── 36-1 Suggested work
        ├── 34-1 Per-node placement mode
        └── 35-1 Snapshot list and prune
```

A leading `/` resolves the directory from the output root, so each header opens a
top-level folder and its claims inherit that prefix. A relative section inherits
the parent prefix: `36-1` opens `02-evolution/suggested/` under the Evolution
header, and its leaves declare only `01-placement` and `02-snapshots`, so the
final path is `02-evolution/suggested/01-placement/…`. Numeric prefixes on
headers and sub-folders make disk order match view order.

Because every section node emits its own file inside its directory
(`src/bd_tree/exporter.py`), no folder is empty; each folder also gets a
generated `INDEX.md`, so a header body stays context-only. At most one
child-bearing section may use a directory, so sibling sub-folders need distinct
names (`01-placement`, `02-snapshots`).

Both axes live in one view: the three layers are sequential sibling directories,
Evolution has a nested `suggested/` stage, and that stage is itself sequenced with
`01-`/`02-` folders. Because `36-1` is a real node, the stage is also a view root
(`bd tree 36-1`) and a link target in its own right, parallel to its parent
header.

## Placement

The headers are root-relative, so they stay as sibling directories; the Evolution
stage node and its leaves are relative and nest two levels beneath their header:

```sh
bd work 20-1
```

```text
bd_work/
├── 00-root/product-breakdown.md
├── 00-intent/
│   ├── intent.md
│   └── credibility-of-the-chain.md
├── 01-product/
│   ├── product.md
│   └── two-axes.md
└── 02-evolution/
    ├── evolution.md
    ├── per-folder-index.md
    └── suggested/
        ├── suggested-work.md
        ├── 01-placement/section-flat-idea.md
        └── 02-snapshots/snapshot-list-and-prune.md
```

`--path-template` still overrides the whole layout when a different route is
wanted. Every folder gets its own generated `INDEX.md`: a folder lists the node
files placed directly in it, then its immediate subfolders, both in view order.
The root `INDEX.md` still indents by the containment tree while the folders
follow the section layout. This closes the per-folder-index item (`33-1`, `34-1`
here; `59-1` in `docs/breakdown`).

## Try it

```sh
cd examples
bd root                         # 20-1  (ROOT)
bd tree                         # root, headers, and claims
bd tree 20-1 --depth 0          # the whole fan-out
bd find links --limit 3
bd path 34-1                    # ancestor path to the deepest leaf
bd tree 37-1                    # one layer as its own parallel view
bd tree 36-1                    # the stage as its own parallel view
bd work 20-1                    # header folders plus the nested stage
bd current                      # <project>/bd_work (view 20-1)
bd edit 21-1                    # path inside the active view
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
