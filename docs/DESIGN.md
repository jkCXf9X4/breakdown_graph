# Design

Status: established 2026-11-14. This document records the model, the decisions
behind it, and the invariants the implementation relies on.

## 1. Originating problem

The motivating case is a layered project breakdown:
intent → claims → argument → evidence → manuscript → verification → operation,
plus a work layer of investigations, selected improvements, and implemented
changes. The case argues that credibility belongs to the chain that produces a
result, not to a single model, and that a handover loss is neither repaired nor
detected downstream by default. The same failure appears in the documentation:

- A top-layer change leaves lower-layer nodes asserting the old solution.
- An agent reading the repository sees both and cannot tell which is current.
- A git branch on the whole tree cannot show two variants side by side.
- Deleting the old branch is the only well-defined removal, and it loses the
  reasoning that produced it.

The tool applies that diagnosis: make dependencies explicit, make a view a
declared closure, and make stale material visible rather than silently present.

## 2. Principles

1. **One store, many projections.** The node files are the only source of truth;
   views, indexes, graphs, exports, and the work layout are derived and
   disposable. Read-only projections may be many; the writable work area is
   exactly one (§5).
2. **Identity is not location.** A node is a running integer; its path in a view
   is presentation metadata.
3. **Containment is data.** The tree is an ordered `contains` list, not a
   directory hierarchy. A view is the closure of one ref.
4. **No schema.** Front matter is arbitrary; only five keys are built in.
   Layers, types, and status values are user data.
5. **Work in the store, through one work area.** The writable work area is a
   symlink view, not a copy, and there is no sync-back. A project has exactly one
   such area at a time; switching views replaces its contents.
6. **No sidecar state.** No JSON manifests, TOML view configs, lock files, or
   active-branch files; the only store-level pointer is `ROOT`, one ref on one
   line. Everything else needed is in the node files or derived.
7. **Freshness is opt-in per edge.** A semantic link participates in staleness
   only when it declares `propagates: true`.
8. **Git owns the solution boundary; the flat store is the merge unit; views are
   lenses.** A branch/worktree isolates a solution; a work folder only
   changes the layout inside one checkout. Neither is a second source of truth.

## 3. Data model

### 3.1 Filenames

```
nodes/5.md          main version of node 5
nodes/5-1.md        version 1 of node 5
nodes/5-2.md        version 2 of node 5
```

- Id and version are positive integers, no leading zeros; main has no suffix.
- Ref `5` or `5-1` is the only citation form; the filename is the authority.
  A front-matter `id`, when present, must match the logical id.

In a project these files live under `.bd_tree/nodes/`; the project root is the
directory containing `.bd_tree/`. Classic stores with `<dir>/nodes/` remain
valid and have project root `<dir>`. Store resolution accepts either the project
root or the store root, and discovery walks up recognising both `nodes/` and
`.bd_tree/nodes`.

### 3.2 Front matter

Reserved keys:

| Key | Type | Semantics |
| --- | --- | --- |
| `id` | int | Optional logical id; must match the filename |
| `legacy` | string | Original identifier from an imported tree |
| `contains` | list of refs | Ordered children for this view |
| `links` | list of edge objects | Semantic edges |
| `home` | string | Optional presentation path |

Everything else is arbitrary and preserved on export. Typical fields: `title`,
`summary`, `layer`, `type`, `status`, `date`, `phase`, `audience`, `order`,
`tags`.

Edge object:

```yaml
links:
  - { to: 6-2, type: supports, propagates: true, pinned: "sha256:ab12cd34ef56" }
  - { to: 27, type: see_also }
```

- `to`: ref. `type`: arbitrary label, never validated against an enum.
- `propagates`: opt-in freshness participation. `pinned`: target body hash
  recorded at the last reconciliation, written by `bd reconcile` and never
  required by hand.

### 3.3 Containment

`contains` is an ordered list of refs, in presentation order; the exporter and
browser do not re-sort it.

- Missing `contains` on a version inherits main's list; `contains: []` means no
  children. `bd fork` materialises the effective list into the new version, so
  later edits to main's containment do not silently change the alternative.
- Containment is a tree **per view**: main and a version may both contain a node
  in different views, but one view must not reach it through two parents.
- Global check: a ref is reachable from the root through `contains`, or through
  another file with the same id (main and its versions are alternatives for one
  logical node). A ref connected by neither path is an `unreachable` error.

Containment and semantics are separate: `contains` decides view membership and
is a tree. `links` expresses provenance, support, contradiction, review, and
other relations as a DAG that may cross subtrees. A semantic link outside the
view is reported as `external-link` and does not pull the target in.

### 3.4 Views

A view is the containment closure rooted at one ref; `bd view`, `bd export`,
and `bd work` take a root ref. The default root is the store's `ROOT` file when
present, else the lowest main ref; an explicit ref or `--root-ref` wins over
both. `bd root REF` writes the file, `bd root --clear` removes it, and
`bd root` prints `<ref>  (ROOT|lowest main)`. A declared but missing ref is
`root-ref-missing`; malformed content is `invalid-root`.
`bd check` validates the global tree and the view; `bd diff A B` compares
closures by logical id. A view is not a substitute for a git branch: a version
of the root (intent) node with its own `contains` list gives an alternative
closure inside the same checkout, and that closure is the realization. Many
closures can exist in one store and one working tree; only one of them is
writable at a time. Two axes, deliberately separate:

- **Solution boundary: git.** A branch and worktree hold one solution; git
  decides when to merge or discard it.
- **Merge unit: the flat `nodes/` store.** One file per node and no nested
  output keep conflicts local to the node that changed.
- **Within a checkout: views.** `bd contain`/`bd uncontain` shape one parent's
  list; `bd link`/`bd unlink` shape typed edges. Both edit only the source file
  and preserve arbitrary front matter and body bytes.

### 3.5 Versions

- `5.md` is the mutable main version, the current truth. `5-1.md` and `5-2.md`
  are alternatives or snapshots, immutable by convention, not enforcement.
- `bd fork 5` copies main to the next free version and materialises the effective
  `contains` list; `bd promote 5-2` copies the version onto main (`--keep`
  retains it); `bd retire-version 5-2` deletes a non-main version.
- Switching between full trees is `bd root REF` (whole store) or repointing one
  parent with `bd uncontain` / `bd contain`. `bd promote` is not a switch.

Version references in `contains` and `links` are exact (`6-2`, not `6`); this
makes a view independent of later edits to main.

Versions are **node-local** alternatives inside one branch. They are not the
solution boundary and do not sync across branches. A solution-level alternative
is a git branch and worktree; mixing solutions is a merge or a cherry-pick. If a
version and a branch express the same thing, prefer the branch.

### 3.6 Branches versus versions

A branch is an isolation boundary over a whole checkout, owned by git. A version
is an alternative file for one node inside the current checkout. Neither can
express the other: refs carry no branch name, `bd promote` never crosses a
worktree, and a version is absent on another branch until the branches merge.

The full model, comparison table, and decision rule are in
[`BRANCHES-AND-VERSIONS.md`](BRANCHES-AND-VERSIONS.md).

## 4. Freshness

Git answers "what changed", not "what depends on it". Pins answer the second
question: a propagating edge stores the target body hash at reconciliation;
`bd stale` compares pins with current target bodies in the same view; and
`bd reconcile` rewrites pins after an intentional review. One evidence node
supporting two claims can be fresh for one edge and stale for the other;
freshness is per edge, not per node.

Hash: SHA-256 of the normalized body (trailing blank lines stripped, exactly one
trailing newline), truncated to 12 hex characters.

## 5. Work folders

A work folder is a symlink layout of one view inside one checkout, not a second
copy. The flat node files are the merge unit; the containing git branch/worktree
is the solution boundary.

The project keeps exactly one writable work area:

```text
<project>/
├── .bd_tree/        store: nodes/, ROOT — source of truth, tracked
├── bd_work/         the single writable work area — derived, ignored
└── ...
```

`bd_work/` is the default output of `bd work`. In a classic `<dir>/nodes/` store
the project root is `<dir>`, so the work area is still `<dir>/bd_work/`.
`--out DIR` is an explicit single-area override, for a scratch path outside the
project; it names that one area, not a second one.

```text
bd_work/claims/thesis-claim.md -> ../../.bd_tree/nodes/49.md
```

- Every `.md` is a relative symlink to its node file; editing the link edits the
  store, with no copy and no sync. All views share one store, so an edit is
  visible in every view that includes the node.
- By default `bd work REF` writes the same `<project>/bd_work`. A different ref
  replaces the content of that area: stale links are removed, and `INDEX.md`,
  `REFS.md`, and `AGENTS.md` are rewritten for the new view. Never keep two
  writable work folders side by side.
- `--path-template` chooses presentation paths for that one area; there is no
  separate name for a second area.
- `--status` classifies paths as `ok`, `missing`, `wrong-target`, `detached`,
  `stray`, or `stale-ref`; `--writeback` re-links detached files and refuses
  invalid front matter or a mismatched `id`, so a body-only replacement cannot
  erase `contains`.
- Switching with detached (edited but unsynced) files is refused: they would be
  lost. Run `bd work REF --writeback` first to keep them, or `--clean` to discard
  them.
- Generated files: `INDEX.md`, `REFS.md` (path ↔ ref), and `AGENTS.md`. Inside
  a git checkout, `AGENTS.md` also records branch, short commit, worktree, so
  the folder identifies its solution boundary. Detection is best-effort: outside
  git the fields are omitted and the layout is unchanged.

### One work area at a time

A full tree is too large to dump into an agent context: it displaces the rest of
the conversation, and the oldest parts are dropped. An agent therefore gets a
bounded, navigable subset, and the tool enforces the boundary: it holds exactly
one writable layout, the one the current `bd_work/` names. Switching views is
`bd work REF`, which replaces the area's contents instead of accumulating a
second folder.

Two work folders side by side would defeat that rule. They make the current view
ambiguous, let edits land through whichever link an agent happens to open, and
leave two `INDEX.md`/`AGENTS.md` files claiming authority. The store is what
scales; the context is not, and one work area is the interface that keeps them
apart.

Read-only projections remain: `bd view` (a copy for review or publishing),
`bd export context` (fresh nodes only, plus `STALE.md`, for an agent that must
not write), and `bd export dot` (Graphviz). They are disposable snapshots, not a
second work area; an agent session reads exactly one of them. A snapshot may be
made many times because it is never writable.

`bd solution` is a thin wrapper over `git worktree` (`new`, `list`, `remove`).
It stores no state and creates no layout: git remains authoritative for which
branch is checked out where; `bd work` remains the layout inside one checkout.

## 6. Schema-agnostic by construction

Nothing in the tool knows the article layers; `layer` is a field like any other.
The only fixed vocabulary is structural: `contains`, `links`, `id`, `legacy`,
`home`, and the freshness keys `to`, `type`, `propagates`, `pinned`.

Consequences: any workflow can define layers (`phase`, `stage`, `stream`),
ordering, and statuses; path templates read any front-matter field; dot
styling is chosen by arbitrary fields (`--color-by`, `--shape-by`); and
`bd check --require FIELD` is the escape hatch when a project wants a schema.

## 7. Established decisions

1. **Running integer ids, no type prefixes.** Simpler filenames and refs; type
   information lives in front matter. Cost: ids are less self-describing.
2. **Flat storage, one file per ref.** Per-node diffs and merges, no path churn
   when titles change.
3. **Versions as filename suffixes.** `5`, `5-1`, `5-2`; main is unsuffixed.
4. **Containment as explicit ordered data.** The tree survives renames of refs
   and can differ per view.
5. **Views as closures, not branches.** No branch names, branch directories, or
   global selector.
6. **Containment is a tree per view; links are a DAG.** Membership is decidable;
   semantics stay expressive.
7. **Arbitrary front matter.** The tool fits any workflow; projects opt into
   validation.
8. **Freshness per edge, opt-in.** No hardcoded `serves`/`supports` semantics.
9. **Work trees with symlinks are the primary interface.** No sync-back, and
   exactly one writable work area.
10. **No JSON/TOML/lock/state sidecars.** The one exception is the store-level
    `ROOT` file: one ref on one line. Derived output is disposable.
11. **Writeback requires valid front matter.** Protects `contains` from
    body-only replacements.
12. **Git owns solutions; `bd work` owns layout.** Worktrees isolate branches;
    the single `bd_work/` area shapes the current view inside one branch.
    Structural edits go through `bd contain` / `bd uncontain` / `bd link` /
    `bd unlink`.
13. **Branches and versions are disjoint layers.** Branches isolate whole
    checkouts; versions are alternative files for single nodes. No cross-branch
    refs, no branch selector, no per-node active-version selector, no promote
    across branches. The one store-level pointer is `ROOT`, a single ref line
    naming the default view root. See
    [`BRANCHES-AND-VERSIONS.md`](BRANCHES-AND-VERSIONS.md).
14. **One work area at a time.** `<project>/bd_work/` holds exactly one view;
    `bd work REF` switches it by replacing the contents. Two writable folders
    never coexist. Read-only `bd view`/`bd export` snapshots are not a second
    work area.

## 8. Rejected alternatives

- **Typed ids (`INT-001`, `CLM-003`).** Readable, but the prefix duplicates
  `type`, adds validation, and makes running order awkward. Simplicity won.
- **Branch directories (`branches/<name>/nodes/`).** Clean inheritance, but a
  global selector and branch metadata returned, needing duplicate state.
- **Filename branches (`<id>-<branch>`).** Better, but branch names were
  global, and exclusion needed a marker. Versions are smaller: the branch is
  the root version.
- **Git branches as the only variant mechanism.** Serial checkouts, no
  side-by-side views, generated-index churn, and stale generated output
  surviving checkout while stale.
- **Writable views with sync-back.** Requires path→ref, new/deleted/moved
  semantics, and conflict handling; creates a second source of truth.
- **Content-addressed store, SQLite graph, CRDT, Dolt.** More machinery than a
  small markdown repository needs; markdown review and git diffs matter more.
- **Extending the older `pb` tool.** Its checks, registers, and archive model
  are bound to the article schema and a single tree.
- **A custom merge engine and `based_on` lineage.** Git already has commits,
  branches, and three-way merges; node-local merge would duplicate that with
  worse conflict handling.
- **Root/active-version pointers.** A per-node selector that chooses among
  alternatives implicitly stays rejected: refs and diffs must show the choice.
  A single store-level `ROOT` ref line is accepted as the default view root; it
  selects no version, only the ref a bare command starts from (§7.10).
- **`use` selection maps for cross-branch mixes.** A solution is a branch;
  mixing is a merge or `git restore --source`; a selector would be a second
  branch mechanism.
- **Symlink worktrees as solution isolation.** `bd work` is a layout inside one
  checkout; isolation belongs to `git worktree`, or branch switching and view
  refresh get entangled.

## 9. Invariants

These are enforced or assumed:

1. The filename is identity and version.
2. Main exists for every id that has a version.
3. `contains` order is display order.
4. Containment is a tree per view; no node is reached twice in one view.
5. Every id is reachable from the global root through containment or through
   another file of the same id.
6. Semantic links resolve in the store; links outside a view warn, never pull
   in.
7. Arbitrary front matter is preserved on export.
8. Work trees contain only symlinks plus generated files.
9. Generated files (`INDEX.md`, `AGENTS.md`, `REFS.md`) are never hand-edited.
10. No generated artifact is committed.
11. A view never crosses a branch, and neither does a version: a version is a
    node-local file in one branch; a solution is a git branch and worktree;
    neither substitutes for the other, and promote never crosses a branch.
12. One worktree per solution. A project has exactly one writable work area,
    `<project>/bd_work/`, holding one view at a time; it is disposable and
    ignored. Read-only exports are separate and never a second work area.
13. Structural edits preserve body bytes and all unrelated front matter.

## 10. Known limits

- Node-local versions do not sync across branches; git merges sync solutions.
- No three-way merge between node versions: promotion is a copy; synthesis is
  manual.
- One worktree per solution; switching branches can leave a layout pointing
  at paths absent from the new branch, so rebuild and run `--status`.
- No locking: concurrent editors can race, and git is the conflict detector.
- Symlinks require a POSIX filesystem; Windows needs developer mode.
- Editors that replace symlinks need `--status`/`--writeback`.
- `bd check` validates every node-rooted view, costing more on large stores.
- There is no CI configuration yet; packaging is a `pyproject.toml` with the
  `bd` console script.

## 11. Open questions

1. Are versions immutable snapshots enforced by convention, or should the tool
   create a new version on every edit of a non-main file?
2. Should a hand-written version inherit `contains` by default (current) or
   require the full list? `bd fork` already materialises it.
3. Do we need filtered views (selectors over fields) in addition to closures?
4. How should two views be merged: promote one, or synthesize a third version?
5. Should concurrent agent sessions share the one work area under leases, or
   each use a separate git worktree?
6. Is a generic exporter (`tree`/`context`) enough, or do we need per-workflow
   report renderers (traceability matrix, claim-evidence table)?
7. Should node-local versions be deprecated entirely in favour of git branches,
   or kept for cheap A/B variants inside one branch?
