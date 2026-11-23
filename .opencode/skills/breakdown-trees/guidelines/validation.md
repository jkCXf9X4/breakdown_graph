# Validation: `bd check`, `bd stale`, pins

Two different questions. `bd check` asks whether the store and its views are
structurally sound. `bd stale` asks whether propagating edges still match their
targets.

## `bd check`

It dispatches on the store's topology. A containment store validates filenames,
front matter, `contains`, `links`, reachability, tree shape for every
node-rooted view, pins, and size. A graph store runs the graph audit: its band
mode (relative `band`/`subpath` or absolute `stage`), forward edges, cycles, dangling
links, fan-out, sorted links, duplicate
versions. Containment section placement is not checked here; collisions
surface when a work area or export is built.

`--view REF` narrows reporting to one closure. In a containment store the store
scan and per-view tree checks still cover the whole store; reachability,
freshness, size, and `--require` apply to the checked view. The checked root is
`ROOT`, else a graph store's lowest graph root, else a containment store's
lowest node by `(id, version)`. A bare id on the command line is a selector;
data refs must be full `id-version`.

Exit 0 means no `error` issues. Containment warnings do not fail:
`external-link`, `untracked-link`, `stale-link`, `oversize`,
`unreachable-node`. Graph warnings do not fail either: `graph-orphan`,
`graph-wide-fanout`, `graph-duplicate-version`, `graph-unsorted-links`,
`graph-group-ignored`.

Useful flags: `--require FIELD` (missing field becomes an error),
`--max-lines N` / `--max-chars N` (size budgets), `--view REF` (report only
that closure).

The CLI prints each issue as `LEVEL path: message` and does not echo the code;
the tables below name the codes used in messages and in the API.

### Error codes common to both

| Code | Meaning |
|---|---|
| `missing-nodes-dir` | No `nodes/` or `.bd_tree/nodes/` under the root |
| `invalid-filename`, `invalid-id`, `id-filename-mismatch` | Filename grammar or `id` disagrees with the filename |
| `duplicate-version` | Version file repeated |
| `bare-ref` | `contains`, `links`, or `ROOT` names a bare id instead of a full `id-version` |
| `bad-frontmatter`, `invalid-links`, `invalid-link`, `invalid-propagates`, `invalid-pin` | Front matter cannot be parsed or has the wrong shape; a scalar full-ref link needs a non-empty `type` on its target |
| `invalid-root`, `root-ref-missing`, `view-root-missing` | `ROOT` or a view ref is malformed or names a missing ref |
| `invalid-ref` | A `contains`/`links` ref or a command-line view ref is malformed, or a bare selector names an id absent from the default view |
| `missing-field` | A `--require` field is absent |
| `root` | The store could not be loaded at all; reported once as the fatal fallback |

### Containment error codes

| Code | Meaning |
|---|---|
| `invalid-contains` | `contains` is not a list of full refs |
| `missing-target` | A `contains` ref points at no file |
| `containment-cycle`, `multiple-parents` | View is not a tree |
| `duplicate-id` | One view holds two versions of the same logical id |
| `dangling-link` | A containment link points at no node at all |

Reachability in a containment store is per logical id and counts outgoing
links: versions of one id are alternatives, so a non-selected version of a
reachable id is not `unreachable-node`, and a history view linked from the root
is reachable too. A bare data ref is a `bare-ref` error, not an
`unreachable-node`.

### Graph error codes

Relative mode (no node declares `stage`):

| Code | Meaning |
|---|---|
| `graph-layer-missing` | The node has no `band` or `layer` |
| `graph-layer-invalid` | Invalid `band`, `subpath`, or `layer`, a `subpath` without `band`, or both forms at once |
| `graph-layer-cycle` | Cross-band edges form a cycle; the bands are reported |
| `graph-order-back-edge` | A same-band edge has `order(source) >= order(target)`, including across subpaths |

Absolute mode (any node declares `stage`):

| Code | Meaning |
|---|---|
| `graph-stage-missing` | The node has no `stage` |
| `graph-stage-invalid` | `stage` is not an integer (booleans are rejected) |
| `graph-back-edge` | `stage(source) >= stage(target)`; the edge is not strictly forward |

Shared graph errors:

| Code | Meaning |
|---|---|
| `graph-order-invalid` | `order` is not an integer |
| `graph-dangling-link` | A graph link target does not exist |
| `graph-cycle` | DFS finds a cycle; the path is reported |

`group` is not validated because it never places a node: a graph node that
declares it warns `graph-group-ignored`.

Invalid relative data still renders in one trailing `unlayered` band; the audit
still reports `graph-layer-missing` / `graph-layer-invalid`. A band cycle also
renders with a fallback order after `graph-layer-cycle` is reported.

### Warning codes

Containment warnings:

| Code | Meaning |
|---|---|
| `external-link` | Link target lies outside the view and is not another containment root; it is not pulled in |
| `untracked-link` | Propagating edge has no `pinned` hash |
| `stale-link` | Propagating edge's pin differs from the target body |
| `unreachable-node` | The node's logical id is not reachable from the root through containment or a link |
| `oversize` | Node exceeds the line/character budget |

Graph warnings:

| Code | Meaning |
|---|---|
| `graph-orphan` | A non-anchor node has no incoming edge |
| `graph-wide-fanout` | Out-degree above 200; split into an intermediate header |
| `graph-duplicate-version` | One id has several versions reachable from the anchor |
| `graph-unsorted-links` | A node's link targets are not sorted by ref |

## `bd stale` and `bd reconcile`

`bd stale` lists propagating link edges in one view whose target body moved
(`stale`) or was never pinned (`untracked`). Targets outside the view are
skipped. It never edits.

```bash
bd stale
bd stale --view REF
bd reconcile REF            # rewrite pins for the named nodes
bd reconcile --all          # every propagating edge in the view
```

`reconcile` mutates node files: it rewrites `pinned` hashes only. Refusing to
reconcile a stale edge means the dependent text was not reviewed — read the
target first, then reconcile.

`bd export context` omits stale source nodes entirely, not just their pins, so
a missing body there is a freshness signal, not a bug.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success; warnings allowed |
| 1 | Check failure or navigation error (bad ref, depth, regex) |
| 2 | Structural refusal (`BreakdownError`) or argparse usage error — the tool declined or the invocation was malformed |

## Gate before reporting done

```bash
bd check                    # must be exit 0; topology-aware
bd audit                    # graph store: band/stage and edge audit
bd stale                    # explain or reconcile every row
bd work --status            # no detached files (when an area is active)
git status --porcelain      # node files only
```

Do not suppress an error by clearing `ROOT`, deleting a version, or removing a
link. Each of those hides the defect the check just found.
