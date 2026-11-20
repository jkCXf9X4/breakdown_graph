# Structure: containment, links, versions

Structure is data in front matter. Change it with `bd` commands so ordering,
cycles, and pins stay consistent; never hand-edit `contains` or `links` unless
the tool cannot express the change.

## Containment

`contains` is an ordered list on the parent; a view is the closure of one ref
and must be a tree.

```bash
bd new --parent REF --field title=... --field layer=...   # next global id
bd contain P C --before REF
bd contain P C --after REF
bd uncontain P C
```

- Order is meaningful: `--before`/`--after` place the child relative to an
  existing sibling; passing both is refused.
- Moving a child is two operations: `bd uncontain P C`, then
  `bd contain NEW C --before REF`.
- `contain` refuses self-containment, cycles, duplicates, and unknown
  siblings. A node reachable twice in one view is `multiple-parents`.
- A node without `contains` is a leaf; nothing is inherited. `contains` holds
  full refs only, and `bd new` appends the full `<newid>-1`.
- `contain` and `uncontain` accept a bare id as a selector and resolve it in the
  selected view; they always write full refs.
- `bd new` derives `folder` from `layer`/`group`/`type` when absent and
  refuses an explicit `id`.

Containment decides what a view shows. A fact that belongs to another branch
does not get contained "for now" — it gets its own node in its own place.

## Links

`links` is a DAG of typed edges, and every `to` is a full ref. A link never
pulls a node into a view, but it keeps its target reachable and a link to
another containment root is not `external-link`. A scalar link
(`links: ['10-1']`) takes its type from the target node's `type`; the mapping
form carries an edge-specific label or freshness.

```bash
bd link FROM TO --type supports --propagates
bd unlink FROM TO [--type TYPE]
```

- `--type` is required and must be non-empty; duplicate edges are refused.
- `--propagates` marks the edge as tracking the target's body: the edge stores
  a `pinned` hash and `bd stale` reports when it moves. Do not add it by
  reflex — only for an edge whose meaning depends on the target's current
  text.
- `unlink` errors when nothing matched, so a silent no-op cannot mask a typo.

## Versions

A version is a node file in the same checkout, not a branch. Every file is
`<id>-<version>.md`; versions of one id are peers.

```bash
bd versions ID              # peer files of one id, ascending by version
bd version REF              # copy to the next free version of the same id
bd version REF --version N  # explicit version slot
bd delete REF               # delete a version (refuses ROOT/reachable/referenced)
bd delete REF --force       # delete anyway
bd diff LEFT RIGHT          # compare two views id by id
```

- The version current in a view is the one its parent's `contains` names; there
  is no per-node pointer and no copy step.
- `bd version` copies the source file, including its declared `contains`; a
  version that omits `contains` is a leaf, not an inheritor.
- To make another version current, repoint the parent with `bd contain` /
  `bd uncontain`.
- Refs inside `contains`/`links` are full and exact (`6-2`, not `6`); a bare
  data ref is `bare-ref`.
- A classic store with bare `nodes/<id>.md` files converts once with
  `bd migrate [--dry-run]`.

## Solutions

```bash
bd solution new NAME            # git worktree ../NAME on branch NAME
bd solution list
bd solution remove NAME|PATH --force
```

Git owns the solution boundary: one worktree per solution, merge in git.
`bd work` is a layout inside one checkout and never a branch mechanism. A
solution never sees another branch's nodes or versions; merge before repointing
to them.

## Switching trees

Three distinct operations, often confused:

| Goal | Command |
|---|---|
| Change the store default view | `bd root REF` / `bd root --clear` |
| Change the view in the work area | `bd work REF` |
| Repoint one parent | `bd uncontain P C` then `bd contain P C --before REF` |

None of them copies a file over another: the parent's `contains` is the record
of which version a view uses.
