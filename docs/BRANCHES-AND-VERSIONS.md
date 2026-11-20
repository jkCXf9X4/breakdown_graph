# Branches and versions

This tool separates two layers: the git branch that isolates a solution, and the
node version that forks one file. They are not two kinds of branch, do not
substitute for each other, and no third mechanism chooses between them.

- A **branch** is an isolation boundary over a whole checkout, owned by git.
  `bd solution` only translates lifecycle verbs into `git worktree` commands.
- A **version** is an alternative file for one node, inside whichever branch is
  checked out. `5.md` is main; `5-1.md` and `5-2.md` are versions of node `5`.
- A **view** is a containment closure rooted at one ref. It is derived,
  disposable, and never crosses a branch.
- The **flat store** is the merge unit. One file per node keeps a conflict local
  to the changed node.

A branch exists only in git; `bd` sees the checkout it runs in. A version
exists only as a filename that git tracks. They meet exactly once, in a merge.

## Side by side

|  | Git branch and worktree | Node version |
| --- | --- | --- |
| Scope | the whole store checkout | one node file |
| Created by | `bd solution new` (`git worktree add`) | `bd fork` |
| Identity | git ref name | filename suffix, e.g. `5-1` |
| In ref resolution | none; refs carry no branch name | the ref itself, e.g. `5-1` |
| Isolation | full; other branches are absent | none; shares the checkout |
| Reconciliation | `git merge`, `cherry-pick` | `bd promote` copies onto main |
| History | commits | none; main is the only mutable ref |

## Rules

1. **Refs are filenames in the current checkout.** The ref grammar is a numeric
   id plus an optional numeric version (`src/bd_tree/loader.py:30-34`). With no
   room for a branch name, `bd` never appends one, reads git state to resolve a
   node, or offers a branch selector.
2. **Lookup is exact.** A ref resolves to one node key; a missing version never
   falls back to main or to another branch (`src/bd_tree/navigate.py:72-76`).
3. **Versions are tracked files.** "Node-local" describes scope, not storage: a
   version created on branch A is absent on branch B until they merge.
4. **`bd promote` is filesystem-only.** It copies the version file onto main in
   the checkout, never reads or changes git (`src/bd_tree/ops.py:172-202`). It
   cannot cross worktrees; check out or merge the version's branch first. It is
   a per-node copy, not how you switch trees.
5. **Neither a view nor a version crosses a branch.** Mixing is `git merge` or
   `git restore --source`. There is no branch selector, no per-node
   active-version selector, and no cross-branch view. The one store-level
   pointer is `ROOT`, a single ref line naming the default view root; it selects
   no version. The default root and the view in the work area are separate:
   `bd root REF` changes the default, `bd work REF` changes the contents of
   `<project>/bd_work/`.
6. **Containment decides membership, not location.** `contains` is a tree per
   view; `links` is a DAG and never adds a node to a view
   (`src/bd_tree/checker.py:164-179`).

## Choosing the right layer

Ask what must move.

- If the alternative must be **isolated, reviewed, or merged as a unit**, it is a
  branch; several nodes and history move together, and git decides when it lands.
- If it changes **one node and the closure beneath it**, it is a version. It
  stays in the same store, shares the checkout, and costs one extra file.
- If the alternative is only a **different reading order over the same files**,
  it is a view. Nothing moves at all.

The closest a version comes to a branch is a root (intent) version with its own
`contains` list: an alternative closure over the same files. Make it the default
with `bd root 1-4`, open it in the work area with `bd work 1-4`, or pass the ref
to one command; it is still a lens on one checkout, with no isolation and no
separate history.

## Consequences worth stating

- Switching between full trees needs no promotion: write `ROOT` with
  `bd root REF` for the default root, run `bd work REF` for the work-area view,
  or repoint one parent with `bd uncontain` / `bd contain`. `bd promote` remains
  a per-node copy of one version onto main.
- `bd fork` materialises the effective `contains` list, so an alternative keeps
  its own tree when main's containment changes. A hand-written version that
  omits `contains` still inherits main's list.
- Two worktrees hold independent copies of the store. A version file committed on
  one is invisible on the other until a merge.
- Two branches editing the same node conflict per file on
  `.bd_tree/nodes/<ref>.md` (`nodes/<ref>.md` in a classic layout). That is the
  intended merge unit; a pointer or selector would hide the change and let the
  branches diverge silently.
- Deleting a worktree never deletes a version; deleting a version never touches
  git history.
- The invariant "every id is reachable from the global root" is evaluated per
  checkout, through containment, a shared id, or a link from a reachable node.
  Another branch's nodes are not missing; they are simply not present.

## Why not one mechanism

Each unification was considered and rejected in `DESIGN.md` §8:

- branch directories (`branches/<name>/nodes/`) — reintroduced a global selector
  and duplicated state;
- filename branches (`<id>-<branch>`) — branch names are global and exclusion
  needs a marker; a version of the root is smaller;
- git branches as the only variant mechanism — serial checkouts, no simultaneous
  views across checkouts, stale generated output across checkouts;
- `use` selection maps for cross-branch mixes — a second branch mechanism.

The split is deliberate: git owns isolation and history, filenames own identity
and versions, views own presentation. One store, many projections.
