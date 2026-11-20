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
- `bd new` derives `home` from `layer`/`group`/`type` when absent and refuses
  an explicit `id`.

Containment decides what a view shows. A fact that belongs to another branch
does not get contained "for now" — it gets its own node in its own place.

## Links

`links` is a DAG of typed edges. A link never pulls a node into a view, but it
keeps its target reachable and a link to another containment root is not
`external-link`.

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

A version is a node file in the same checkout, not a branch.

```bash
bd versions ID              # main and version files of one id
bd fork ID                  # copy main to the next free version
bd fork ID --version N      # explicit version slot
bd promote REF              # copy version onto main, delete the version
bd promote REF --keep       # keep the version file
bd retire-version REF       # delete a non-main version
bd diff LEFT RIGHT          # compare two views id by id
```

- Every versioned id must have a main file; a version without one is
  `missing-main`.
- `fork`, `promote`, and `retire-version` each reject main-vs-version refs the
  other way round.
- `promote --keep` strips `contains` from the kept version so it inherits from
  the promoted main again.
- Version references inside `contains`/`links` are exact (`6-2`, not `6`) so a
  view does not silently follow later main edits.

## Solutions

```bash
bd solution new NAME            # git worktree ../NAME on branch NAME
bd solution list
bd solution remove NAME|PATH --force
```

Git owns the solution boundary: one worktree per solution, merge in git.
`bd work` is a layout inside one checkout and never a branch mechanism. A
solution never sees another branch's nodes or versions; merge before
promoting.

## Switching trees

Three distinct operations, often confused:

| Goal | Command |
|---|---|
| Change the store default view | `bd root REF` / `bd root --clear` |
| Change the view in the work area | `bd work REF` |
| Repoint one parent | `bd uncontain P C` then `bd contain P C --before REF` |

`bd promote` appears in none of them: it copies bytes onto main.
