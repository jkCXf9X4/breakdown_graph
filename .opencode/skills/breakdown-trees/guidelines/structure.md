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
- `bd new` refuses an explicit `id` and derives no placement fields.

Containment decides what a view shows. A fact that belongs to another branch
does not get contained "for now" — it gets its own node in its own place.

## Links

`links` is a typed edge graph, kept a DAG by convention: containment cycles are
checked (`containment-cycle`), link cycles are neither refused nor reported.
Every `to` is a full ref. A link never pulls a node into a view, but it keeps
its target reachable and a link to another containment root is not
`external-link`. A scalar link (`links: ['10-1']`) takes its type from the
target node's `type`; the mapping form carries an edge-specific label or
freshness.

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
bd clone REF                # copy to the next free version of the same id
bd clone REF --version N    # explicit version slot
bd clone REF --subtree      # copy the node and every containment descendant
bd replace OLD NEW          # wire NEW in at OLD's index (or repoint ROOT)
bd delete REF               # delete a version (refuses ROOT/reachable/referenced)
bd delete REF --force       # delete anyway
bd diff LEFT RIGHT          # compare two views id by id
```

- The version current in a view is the one its parent's `contains` names; there
  is no per-node pointer and switching needs no copy step.
- `bd clone` copies the source file, including its declared `contains`, and
  wires nothing into the current view; a version that omits `contains` is a
  leaf, not an inheritor.
- `bd clone REF --subtree` clones every containment descendant and rewrites
  each cloned parent's `contains` to the cloned children, producing a
  self-contained copy; the original tree is untouched. `--version` cannot be
  combined with `--subtree`.
- `bd replace OLD NEW` is the separate wiring step: it finds OLD in the default
  view and puts NEW at OLD's exact index in its parent's `contains`, or repoints
  `ROOT` when OLD is the store root; OLD's file stays as a peer. Clone and swap
  in one logical flow with `bd clone REF --subtree` then `bd replace REF
  <printed new root ref>`. If OLD is outside the default view, `bd replace`
  errors and asks for `bd contain`; multiple parents is an error.
- To make another version current, repoint the parent with `bd contain` /
  `bd uncontain`, or use `bd clone REF` then `bd replace REF NEW`. To choose a
  different position, run `bd uncontain P OLD`, then `bd contain P NEW --before
  NEXT` (the `duplicate-id` rule forbids both versions in one view).
- Refs inside `contains`/`links` are full and exact (`6-2`, not `6`); a bare
  data ref is `bare-ref`.
- A classic store with bare `nodes/<id>.md` files converts once with
  `bd migrate [--dry-run]`.

## Solutions

```bash
bd solution new NAME                 # git worktree ../NAME on branch NAME
bd solution new NAME --path DIR      # explicit worktree path
bd solution new NAME --from REF      # branch start point (default: HEAD)
bd solution list                     # worktrees and checkouts holding this store
bd solution remove NAME|PATH [--force]
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
| Repoint one parent | `bd uncontain P OLD` then `bd contain P NEW --before REF`, or `bd replace OLD NEW` |

None of them copies a file over another: the parent's `contains` is the record
of which version a view uses.
