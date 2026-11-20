# Validation: `bd check`, `bd stale`, pins

Two different questions. `bd check` asks whether the store and its views are
structurally sound. `bd stale` asks whether propagating edges still match their
targets.

## `bd check`

Validates filenames, front matter, `contains`, `links`, reachability, tree
shape for every node-rooted view, `home` paths, pins, and size. `--view` and
`--root-ref` choose what is reported; all views are still checked.

Exit 0 means no `error` issues. Warnings do not fail: `external-link`,
`untracked-link`, `stale-link`, `oversize`.

Useful flags: `--require FIELD` (missing field becomes an error),
`--max-lines N` / `--max-chars N` (size budgets), `--view REF`,
`--root-ref REF`.

### Error codes

| Code | Meaning |
|---|---|
| `missing-nodes-dir` | No `nodes/` or `.bd_tree/nodes/` under the root |
| `invalid-filename`, `invalid-id`, `id-filename-mismatch` | Filename grammar or `id` disagrees with the filename |
| `duplicate-version`, `missing-main` | Version file repeated, or a version with no main |
| `bad-frontmatter`, `invalid-contains`, `invalid-links`, `invalid-link`, `invalid-link-target`, `invalid-propagates`, `invalid-pin` | Front matter cannot be parsed or has the wrong shape; a bare link needs a non-empty `type` on its target |
| `missing-target` | A `contains` ref points at no file |
| `containment-cycle`, `multiple-parents` | View is not a tree |
| `unreachable`, `root-ref-missing` | Nothing reaches the node from the root, or `ROOT` names a missing ref |
| `invalid-root`, `invalid-ref`, `view-root-missing` | `ROOT` or a view ref is malformed or absent |
| `dangling-link` | A link points at no node at all |
| `bad-home`, `duplicate-home` | `home` path invalid or claimed twice |
| `missing-field` | A `--require` field is absent |

Note that reachability counts a shared id and outgoing links: main and its
versions are one logical node, so a version reachable only through its main is
not `unreachable`, and a history view linked from the root is reachable too.

### Warning codes

| Code | Meaning |
|---|---|
| `external-link` | Link target lies outside the view and is not another containment root; it is not pulled in |
| `untracked-link` | Propagating edge has no `pinned` hash |
| `stale-link` | Propagating edge's pin differs from the target body |
| `oversize` | Node exceeds the line/character budget |

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
| 2 | Structural refusal (`BreakdownError`) — the tool declined |

## Gate before reporting done

```bash
bd check                    # must be exit 0
bd stale                    # explain or reconcile every row
bd work --status            # no detached files (when an area is active)
git status --porcelain      # node files only
```

Do not suppress an error by clearing `ROOT`, deleting a version, or removing a
link. Each of those hides the defect the check just found.
