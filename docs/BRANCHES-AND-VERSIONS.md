# Branches and versions

This tool separates two layers: the git branch that isolates a solution, and the
node version that keeps an alternative for one file. They are not two kinds of branch, do not
substitute for each other, and no third mechanism chooses between them.

- A **branch** is an isolation boundary over a whole checkout, owned by git.
  `bd solution` only translates lifecycle verbs into `git worktree` commands.
- A **version** is an alternative file for one node, inside whichever branch is
  checked out. Every node file is `<id>-<version>.md`; `5-1` and `5-2` are peer
  versions of logical node `5`.
- A **view** is a closure rooted at one full ref over the store's child relation
  (`contains`, or forward `links` in a graph store). It is derived, disposable,
  and never crosses a branch.
- The **flat store** is the merge unit. One file per node version keeps a
  conflict local to the version that changed.

A branch exists only in git; `bd` sees the checkout it runs in. A version
exists only as a filename that git tracks. They meet exactly once, in a merge.

## Side by side

|  | Git branch and worktree | Node version |
| --- | --- | --- |
| Scope | the whole store checkout | one node file |
| Created by | `bd solution new` (`git worktree add`) | `bd clone REF` |
| Identity | git ref name | full ref, e.g. `5-1` |
| In ref resolution | none; refs carry no branch name | the full ref itself, e.g. `5-1` |
| Isolation | full; other branches are absent | none; shares the checkout |
| Reconciliation | `git merge`, `cherry-pick` | repoint a parent's `contains` (containment) or inbound links (graph); no copy step |
| History | commits | none; peer files, all equally current for their view |

## Rules

1. **Refs are filenames in the current checkout.** The ref grammar is a numeric
   id plus a numeric version (`src/bd_tree/loader.py`). With no room for a
   branch name, `bd` never appends one, reads git state to resolve a node, or
   offers a branch selector.
2. **Lookup is exact.** A ref is always the full `id-version`; a bare id on the
   command line is a selector resolved inside the selected view. A missing
   version never falls back to another version or to another branch
   (`src/bd_tree/navigate.py`).
3. **Versions are tracked files.** "Node-local" describes scope, not storage: a
   version created on branch A is absent on branch B until they merge.
4. **A parent's `contains` is the only record of the current version in a
   containment store.** There a view uses the version its parent's `contains`
   names. To make another version current, repoint the parent with `bd contain` /
   `bd uncontain`, or use `bd clone REF` then `bd replace REF NEW` for the common
   clone-and-swap path; `bd clone` alone only copies to a new peer, and
   `bd delete` only removes a file. In a graph store, an edge pins a full ref: a
   version is current where an edge targets it, and a view warns
   (`graph-duplicate-version`) when two versions of one id are reachable. Neither
   form reads or changes git, and neither can cross a worktree. Band ordinals,
   inferred folders, and the `unlayered` fallback are layout projection, never
   version state; see [`GRAPH-LAYOUT.md`](GRAPH-LAYOUT.md).
5. **Neither a view nor a version crosses a branch.** Mixing is `git merge` or
   `git restore --source`. There is no branch selector, no per-node
   active-version selector, and no cross-branch view. The one store-level
   pointer is `ROOT`, a single full ref line naming the default view root; it
   selects no version for any other node. The default root and the view in the
   work area are separate: `bd root REF` changes the default, `bd work REF`
   changes the contents of `<project>/bd_work/`.
6. **The store's child relation decides membership, not location.** In a
   containment store, `contains` is a tree per view and `links` is a DAG that
   never adds a node to a view (`src/bd_tree/checker.py`). In a graph store,
   forward `links` is the child relation and in-edges are derived
   (`src/bd_tree/graph.py`).

## Choosing the right layer

Ask what must move.

- If the alternative must be **isolated, reviewed, or merged as a unit**, it is a
  branch; several nodes and history move together, and git decides when it lands.
- If it changes **one node and the closure beneath it**, it is a version. It
  stays in the same store, shares the checkout, and costs one extra file.
- If the alternative is only a **different reading order over the same files**,
  it is a view. Nothing moves at all.

The closest a version comes to a branch is a root (intent) version with its own
child relation (`contains`, or out-links in a graph store): an alternative
closure over the same files. Make it the default
with `bd root 1-2`, open it in the work area with `bd work 1-2`, or pass the ref
to one command; it is still a lens on one checkout, with no isolation and no
separate history.

## Consequences worth stating

- Switching between full trees needs no copy step: write `ROOT` with
  `bd root REF` for the default root, run `bd work REF` for the work-area view,
  or, in a containment store, repoint one parent with `bd uncontain` /
  `bd contain`.
- `bd clone REF` copies the source file, so the new peer keeps its declared
  `contains`; a containment version that omits `contains` is a leaf, not an
  inheritor. `bd clone REF --subtree` clones the whole descendant closure and
  rewires the copies to each other (`contains`, or `links` in a graph store),
  leaving the original untouched. `bd replace OLD NEW` is the separate wiring
  step: it puts NEW at OLD's exact index in its parent's `contains`
  (containment), repoints inbound links (graph), or repoints `ROOT` when OLD is
  the store root; OLD's file stays as a peer. Clone and swap in one logical flow
  with `bd clone REF --subtree` then `bd replace REF <printed new root ref>`.
  If OLD is outside the default view, `bd replace` errors. Multiple parents is a
  containment error; graph edges may have several. The containment
  `duplicate-id` rule still forbids both versions in one view, so to choose a
  different position, run `bd uncontain P OLD`, then `bd contain P NEW --before
  NEXT`.
- Two worktrees hold independent copies of the store. A version file committed on
  one is invisible on the other until a merge.
- Two branches editing the same node conflict per file on
  `.bd_tree/nodes/<ref>.md` (`nodes/<ref>.md` in a classic layout). That is the
  intended merge unit; a pointer or selector would hide the change and let the
  branches diverge silently.
- Deleting a worktree never deletes a version; deleting a version never touches
  git history.
- The invariant "every logical id is reachable from the global root" is
  evaluated per checkout. In a containment store it holds through containment, a
  shared id, or a link from a reachable node; in a graph store it holds through
  forward links from a graph root. Another branch's nodes are not missing; they
  are simply not present.

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
