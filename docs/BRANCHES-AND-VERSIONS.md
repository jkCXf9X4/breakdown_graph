# Branches and versions

This tool separates two layers: the git branch that isolates a solution, and the
node version that keeps an alternative for one file. They are not two kinds of
branch, do not substitute for each other, and no third mechanism chooses between
them.

- A **branch** is an isolation boundary over a whole checkout, owned by git.
  `bdg solution` only translates lifecycle verbs into `git worktree` commands.
- A **version** is an alternative file for one node, inside whichever branch is
  checked out. Every node file is `<id>-<version>.md`; `5-1` and `5-2` are peer
  versions of logical node `5`.
- A **view** is the weakly connected component of one full ref over authored
  tokens, walked in both directions. It is derived, disposable, and never
  crosses a branch.
- The **flat store** is the merge unit. One file per node version keeps a
  conflict local to the version that changed.

A branch exists only in git; `bdg` sees the checkout it runs in. A version
exists only as a filename that git tracks. They meet exactly once, in a merge.

## Side by side

|  | Git branch and worktree | Node version |
| --- | --- | --- |
| Scope | the whole store checkout | one node file |
| Created by | `bdg solution new` (`git worktree add`) | `bdg clone REF` |
| Identity | git ref name | full ref, e.g. `5-1` |
| In ref resolution | none; refs carry no branch name | the full ref itself, e.g. `5-1` |
| Isolation | full; other branches are absent | none; shares the checkout |
| Reconciliation | `git merge`, `cherry-pick` | repoint inbound links; no copy step |
| History | commits | none; peer files, all equally current for their view |

## Rules

1. **Refs are filenames in the current checkout.** The ref grammar is a numeric
   id plus a numeric version (`src/bdg/loader.py`). With no room for a
   branch name, `bdg` never appends one, reads git state to resolve a node, or
   offers a branch selector.
2. **Lookup is exact.** A ref is always the full `id-version`; a bare id on the
   command line is a selector resolved inside the selected view. A missing
   version never falls back to another version or to another branch
   (`src/bdg/navigate.py`).
3. **Versions are tracked files.** "Node-local" describes scope, not storage: a
   version created on branch A is absent on branch B until they merge.
4. **An edge pins a full ref.** A version is current where an edge targets it,
   and a view warns (`graph-duplicate-version`) when two versions of one id are
   reachable. To make another version current, repoint the inbound edges with
   `bdg replace OLD NEW`, or clone and swap with `bdg clone REF` then
   `bdg replace REF NEW`; `bdg clone` alone only copies to a new peer, and
   `bdg delete` only removes a file. Nothing here reads or changes git, and
   nothing can cross a worktree.
5. **Neither a view nor a version crosses a branch.** Mixing is `git merge` or
   `git restore --source`. There is no branch selector, no per-node
   active-version selector, and no cross-branch view. The one store-level
   pointer is `ROOT`, a single full ref line naming the default view root; it
   selects no version for any other node. The default root and the view in the
   work area are separate: `bdg root REF` changes the default, `bdg work REF`
   changes the contents of `<project>/bdg_work/`.
6. **Links decide membership, not location.** Typed body tokens are the child
   relation, and in-edges are derived by reversing them (`src/bdg/graph.py`).
   A back-reference is a separately authored token, not a derived opposite. A
   node with several parents appears once in a view. `contains` is not data; a
   node that still declares it fails `bdg check` with `contains-removed` until
   `bdg migrate` converts it.

## Choosing the right layer

Ask what must move.

- If the alternative must be **isolated, reviewed, or merged as a unit**, it is a
  branch; several nodes and history move together, and git decides when it lands.
- If it changes **one node and the component around it**, it is a version. It
  stays in the same store, shares the checkout, and costs one extra file.
- If the alternative is only a **different reading order over the same files**,
  it is a view. Nothing moves at all.

The closest a version comes to a branch is a root (intent) version with its own
out-links: an alternative component over the same files. Make it the default
with `bdg root 1-2`, open it in the work area with `bdg work 1-2`, or pass the ref
to one command; it is still a lens on one checkout, with no isolation and no
separate history.

## Consequences worth stating

- Switching between full trees needs no copy step: write `ROOT` with
  `bdg root REF` for the default root, run `bdg work REF` for the work-area view,
  or repoint inbound edges with `bdg replace OLD NEW`.
- `bdg clone REF` copies the source file, so the new peer keeps its link tokens.
  `bdg clone REF --subtree` clones the whole weakly connected component (or rings
  `0..N` with `--depth N`) and rewires the copies to each other, leaving the
  original untouched.
  `bdg replace OLD NEW` is the separate wiring step: it repoints every inbound
  link, or repoints `ROOT` when OLD is the store root; OLD's file stays as a
  peer. Clone and swap in one logical flow with `bdg clone REF --subtree` then
  `bdg replace REF <printed new root ref>`. If OLD is outside the default view,
  `bdg replace` errors. Several parents are legal, and a reachable duplicate
  version warns (`graph-duplicate-version`), so repoint the edge you want to
  change.
- Two worktrees hold independent copies of the store. A version file committed on
  one is invisible on the other until a merge.
- Two branches editing the same node conflict per file on
  `bdg_graph/nodes/<ref>.md` (`nodes/<ref>.md` in a classic layout). That is the
  intended merge unit; a pointer or selector would hide the change and let the
  branches diverge silently.
- Deleting a worktree never deletes a version; deleting a version never touches
  git history.
- The invariant "every node is reachable from the anchor" is evaluated per
  checkout, over authored links in either direction. Another branch's nodes are
  not missing; they are simply not present.

## Why not one mechanism

Each unification was considered and rejected in `DESIGN.md` §8:

- containment as a second topology — duplicated the link relation and made
  `section` a second placement language; removed, with `bdg migrate` as the
  conversion path;
- branch directories (`branches/<name>/nodes/`) — reintroduced a global selector
  and duplicated state;
- filename branches (`<id>-<branch>`) — branch names are global and exclusion
  needs a marker; a version of the root is smaller;
- git branches as the only variant mechanism — serial checkouts, no simultaneous
  views across checkouts, stale generated output across checkouts;
- `use` selection maps for cross-branch mixes — a second branch mechanism.

The split is deliberate: git owns isolation and history, filenames own identity
and versions, views own presentation. One store, many projections.
