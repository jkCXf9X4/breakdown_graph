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
4. **No schema.** Front matter is arbitrary; the built-in keys are listed below.
   Layers, types, and status values are user data.
5. **Work in the store, through one work area.** The writable work area is a
   symlink view, not a copy, and there is no sync-back. A project has exactly one
   such area at a time; switching views replaces its contents.
6. **No sidecar state.** No JSON manifests, TOML view configs, persistent lock
   files, or active-branch files; the only pointers are the store-level `ROOT`,
   one ref on one line, and the folder-level `.bd_root`, one store path on one
   line. Everything else needed is in the node files or derived. A writer's
   advisory lock is transient and lives in the system temp directory, keyed by
   the store path, so no lock file enters the store or git.
7. **Freshness is opt-in per edge.** A semantic link participates in staleness
   only when it declares `propagates: true`.
8. **Git owns the solution boundary; the flat store is the merge unit; views are
   lenses.** A branch/worktree isolates a solution; a work folder only
   changes the layout inside one checkout. Neither is a second source of truth.

## 3. Data model

### 3.1 Filenames

```
nodes/5-1.md        version 1 of node 5
nodes/5-2.md        version 2 of node 5
```

- Id and version are positive integers, no leading zeros; version starts at 1;
  bare `nodes/5.md` is invalid.
- The logical id is the part before the dash (`5`); versions of one id are
  peers with no privileged version.
- A ref in data is always the full `5-1`; the filename is the authority. A
  front-matter `id`, when present, must match the logical id.
- A bare id on the command line (`bd show 5`) is a selector resolved inside the
  selected view; it is never written to data.

In a project these files live under `.bd_tree/nodes/`; the project root is the
directory containing `.bd_tree/`. Classic stores with `<dir>/nodes/` remain
valid and have project root `<dir>`. Store resolution accepts either the project
root or the store root, and discovery walks up recognising both `nodes/` and
`.bd_tree/nodes`, plus an optional folder-level `.bd_root` pointer naming the
store. If neither appears upward, it scans below the current directory to depth
3 (sorted, pruned, symlinks not followed) and uses the store only when exactly
one is found; several candidates are a refusal. Precedence is `--root`,
`BD_ROOT`, then the upward walk from the current directory (at each directory a
store there first, then a `.bd_root`), then the downward scan. `ROOT` and
`.bd_root` are different files with different jobs: `ROOT` is the store-level
default-view ref; `.bd_root` is a one-line folder-level pointer that names a
store.

### 3.2 Front matter

Built-in keys (structural keys are reserved; presentation keys are placement only):

| Key | Type | Semantics |
| --- | --- | --- |
| `id` | int | Optional logical id; must match the filename |
| `legacy` | string | Original identifier from an imported tree |
| `contains` | list of refs | Ordered children for this view |
| `links` | list of edge objects | Semantic edges |
| `name` | string | Optional file stem; `.md` is appended |
| `section` | bool or string | Opens a directory for this node's descendants; a leading `/` resolves it from the output root |

Everything else is arbitrary and preserved on export. Typical fields: `title`,
`summary`, `layer`, `type`, `status`, `date`, `phase`, `audience`, `order`,
`tags`.

A link may be a scalar ref: `links: ['10-1']` takes its edge type from node
`10-1`'s own `type` field. Use the mapping form for an edge-specific label or
freshness.

Edge object:

```yaml
links:
  - { to: 6-2, type: supports, propagates: true, pinned: "sha256:ab12cd34ef56" }
  - { to: 27-1, type: see_also }
```

- `to`: a full ref. `type`: arbitrary label, never validated against an enum. A
  scalar ref omits `type` and uses the target node's `type`; a history view's
  root declares `type: decision`.
- `propagates`: opt-in freshness participation. `pinned`: target body hash
  recorded at the last reconciliation, written by `bd reconcile` and never
  required by hand.

### 3.3 Containment

`contains` is an ordered list of refs, in presentation order; the exporter and
browser do not re-sort it.

- A `contains` list holds full refs only. A node that omits `contains` is a
  leaf; there is no inheritance from another version. `bd clone` copies the
  source file, so the copy keeps its declared list; `bd clone --subtree` instead
  rewrites each cloned parent's `contains` to the cloned children, and
  `bd replace OLD NEW` wires a clone into the default view (see 3.5).
- Containment is a tree **per view**: two versions of an id may each contain a
  node in different views, but one view must not reach it through two parents,
  and one view must not hold two versions of the same logical id
  (`duplicate-id`). The chain selects exactly one version per id.
- Global check: a ref is reachable from the root through `contains`, through
  another file with the same logical id (versions are alternatives for one
  logical node), or through an outgoing link from a reachable node. A logical
  id connected by none of these paths is an `unreachable-node` warning.
- A bare ref in data is a `bare-ref` error; malformed syntax is `invalid-ref`.
  Views walk only full refs.

Containment and semantics are separate: `contains` decides view membership and
is a tree. `links` expresses provenance, support, contradiction, review, and
other relations as a DAG that may cross subtrees. A semantic link outside the
view does not pull the target in. It is reported as `external-link` unless the
target is itself a containment root — a link into another view, not a stray
edge.

### 3.4 Views

A view is the containment closure rooted at one ref; `bd export tree`, the
other `bd export` choices, and `bd work` take a root ref. The default root is
the store's `ROOT` file when present, else the lowest available node by
`(id, version)`; an explicit ref where a command takes one wins over both.
`bd check --view REF` only narrows reporting. `bd root REF` writes the file,
`bd root --clear` removes it, and `bd root` prints `<ref>  (ROOT|lowest)`. A
declared but missing ref is `root-ref-missing`; malformed content is
`invalid-root`. This default root is
separate from the view the work area holds: `bd root` changes the default used
by commands, while `bd work REF` replaces the contents of `<project>/bd_work/`.
`bd current` reports the area and the view actually there.
`bd check` validates the global tree and the view; `bd diff A B` compares
closures by logical id. A view is not a substitute for a git branch: a version
of the root (intent) node with its own `contains` list gives an alternative
closure inside the same checkout, and that closure is the realization. Many
closures can exist in one store and one working tree; only one of them is
writable at a time. Two axes, deliberately separate:

- **Solution boundary: git.** A branch and worktree hold one solution; git
  decides when to merge or discard it.
- **Merge unit: the flat `nodes/` store.** One file per node version and no
  nested output keep conflicts local to the version that changed.
- **Within a checkout: views.** `bd contain`/`bd uncontain` shape one parent's
  list; `bd link`/`bd unlink` shape typed edges. Both edit only the source file
  and preserve arbitrary front matter and body bytes.

### 3.5 Versions

- Every node file is a version: `5-1.md`, `5-2.md`, and so on are peers, each
  immutable by convention, not enforcement. No version is privileged.
- `bd clone 5-1` copies a ref to the next free version of the same logical id
  (or to `--version N`) and keeps the source file's declared `contains`; it wires
  nothing into the current view. `bd clone 5-1 --subtree` clones every
  containment descendant and rewrites each cloned parent's `contains` to the
  cloned children, producing a self-contained copy; the original tree is
  untouched, and `--version` cannot be combined with `--subtree`.
  `bd replace OLD NEW` is the separate wiring step: it finds OLD in the default
  view and puts NEW at OLD's exact index in its parent's `contains`, or repoints
  `ROOT` when OLD is the store root; OLD's file stays as a peer. Clone and swap
  in one logical flow with `bd clone 5-1 --subtree` then `bd replace 5-1
  <printed new root ref>`. If OLD is outside the default view, `bd replace`
  errors and asks for `bd contain`; multiple parents is an error.
  `bd delete 5-2` deletes a version, refusing a `ROOT`, a reachable ref, or one
  referenced by any `contains`/`links` unless `--force`.
- The version current in a view is the one its parent's `contains` names. There
  is no per-node pointer. Repoint one parent with `bd uncontain` / `bd contain`;
  use `bd clone REF` then `bd replace REF NEW` for the common clone-and-swap
  path, or run `bd uncontain P OLD`, then `bd contain P NEW --before NEXT` to
  choose a different position (the `duplicate-id` rule forbids both versions in
  one view).
  Switch whole trees with `bd work REF` (the work area) or `bd root REF` (the
  store default). Switching needs no copy step.

Version references in `contains` and `links` are exact full refs (`6-2`, not
`6`); this makes a view independent of later edits to any peer.

Versions are **node-local** alternatives inside one branch. They are not the
solution boundary and do not sync across branches. A solution-level alternative
is a git branch and worktree; mixing solutions is a merge or a cherry-pick. If a
version and a branch express the same thing, prefer the branch.

### 3.6 Branches versus versions

A branch is an isolation boundary over a whole checkout, owned by git. A version
is an alternative file for one node inside the current checkout. Neither can
express the other: refs carry no branch name, no operation copies a version
across a worktree, and a version is absent on another branch until the branches
merge.

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

`bd_work/` is the single output of `bd work`. In a classic `<dir>/nodes/` store
the project root is `<dir>`, so the work area is still `<dir>/bd_work/`.

```text
bd_work/claims/thesis-claim.md -> ../../.bd_tree/nodes/49-1.md
```

- Each node `.md` is a relative symlink to its node file; editing the link edits
  the store, with no copy and no sync. `INDEX.md`, `AGENTS.md`, and `REFS.md` are
  regular generated files. All views share one store, so an edit is visible in
  every view that includes the node.
- `bd work REF` writes the single `<project>/bd_work`. A different ref replaces
  the content of that area: stale links are removed, and `INDEX.md`, `REFS.md`,
  and `AGENTS.md` are rewritten for the new view. With no REF, `bd work` uses the
  default view. Never keep two writable work folders side by side.
- The view is still the full containment closure of one ref; the work area may
  materialize only the first `N` descendant levels of it. `bd work REF+N` (the
  same display suffix as `bd show`/`bd tree`) or `bd work REF --depth N` prunes
  the materialized prefix after the view is resolved; `N=0` leaves the root
  alone and `--depth` overrides a suffix. Containment alone decides the
  materialized prefix; placement is the one deliberate exception, where a
  `section` node opens a directory for its descendants.
  The generated `REFS.md`, `INDEX.md`, and `AGENTS.md` carry `REF+N`, so
  `bd current`, `--status`, `--writeback`, and `bd edit` recover the
  materialized depth; `bd edit` rejects a ref outside that prefix. A rebuild
  with a different depth, including a plain `bd work REF`, replaces the area and
  removes links that are no longer materialized.
- `bd current` is the read-only query for that area: it prints
  `<project>/bd_work (view <ref>)`, `--path` prints only the path, and `--view`
  only the ref; it errors when no area exists.
  `bd edit REF` prints the absolute path of a ref in the active view and errors
  if it is not there. `bd views` lists containment roots and marks the store
  default with `*`.
- A node is placed by `section`, `name`, and `title`. `section` is the only
  presentation key that creates directories: `section: true` names the directory
  by the node's placement name (explicit `name`, else the lowercase kebab-case
  `title` slug, else the ref), and `section: "<dir>"` uses the string verbatim
  and may contain `/`. A leading `/` resolves the directory from the output root
  instead of under the parent prefix, so a containment chain can keep layers as
  siblings. The section node's own file is
  `<dir>/<placement-name>.md`; every containment descendant is placed at its
  normal relative path under that prefix, and nested sections stack. Otherwise a
  node is placed by explicit `name` (`<name>.md`), else
  `<ref>-<title-slug>.md`, else `<ref>.md` when there is no usable title (none,
  or punctuation only), so the ref is never doubled. `--path-template` opts out
  of section inheritance, overrides the whole area, and never names another work
  area; in a template, `{name}`/`{slug}` is the explicit `name`, else the title
  slug, else the ref.
- `--status` classifies paths as `ok`, `missing`, `wrong-target`, `detached`,
  `stray`, or `stale-ref`; `--writeback` re-links detached files and refuses
  invalid front matter or a mismatched `id`, so a body-only replacement cannot
  erase `contains`. Both inspect the view actually in the area, not the requested
  or default view.
- Switching with detached (edited but unsynced) files is refused: they would be
  lost. Run `bd work --writeback` first to keep them, or `--clean` to discard
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

Two work folders at once would defeat that rule. They make the current view
ambiguous, let edits land through whichever link an agent happens to open, and
leave two `INDEX.md`/`AGENTS.md` files claiming authority. The store is what
scales; the context is not, and one work area is the interface that keeps them
apart.

Read-only projections remain: `bd export tree REF --out DIR` (the single tree
projection, for review or publishing), `bd export context` (fresh nodes only,
plus `STALE.md`, for an agent that must not write), and `bd export dot`
(Graphviz). They are disposable snapshots, not a second work area; an agent
session reads exactly one of them. A snapshot may be made many times because it
is never writable.

`bd solution` is a thin wrapper over `git worktree` (`new`, `list`, `remove`).
It stores no state and creates no layout: git remains authoritative for which
branch is checked out where; `bd work` remains the layout inside one checkout.

## 6. Schema-agnostic by construction

Nothing in the tool knows the article layers; `layer` is a field like any other.
The only reserved vocabulary is structural: `id`, `legacy`, `contains`,
`links`, and the freshness keys `to`, `type`, `propagates`, `pinned`. `name`,
`title`, and `section` are presentation fields: they change placement only,
never identity, containment, or validation, so they add no schema. `folder` is
ordinary front matter: preserved, never read, and it affects no placement,
naming, validation, or warning.

Consequences: any workflow can define layers (`phase`, `stage`, `stream`),
ordering, and statuses; path templates read any front-matter field; dot
styling is chosen by arbitrary fields (`--color-by`, `--shape-by`); and
`bd check --require FIELD` is the escape hatch when a project wants a schema.

## 7. Established decisions

1. **Running integer ids, no type prefixes.** Simpler filenames and refs; type
   information lives in front matter. Cost: ids are less self-describing.
2. **Flat storage, one file per node version.** Per-version diffs and merges, no
   path churn when titles change.
3. **Versions as mandatory filename suffixes.** `5-1`, `5-2`; every node is a
   version and no unsuffixed file exists.
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
10. **No JSON/TOML/lock/state sidecars.** The exceptions are the store-level
    `ROOT` file (one ref on one line) and the folder-level `.bd_root` pointer
    (one store path on one line). Derived output is disposable. The write lock
    is not a sidecar: it is transient and lives outside the store.
11. **Writeback requires valid front matter.** Protects `contains` from
    body-only replacements.
12. **Git owns solutions; `bd work` owns layout.** Worktrees isolate branches;
    the single `bd_work/` area shapes the current view inside one branch.
    Structural edits go through `bd contain` / `bd uncontain` / `bd clone` /
    `bd replace` / `bd link` / `bd unlink`.
13. **Branches and versions are disjoint layers.** Branches isolate whole
    checkouts; versions are peer files for single nodes. No cross-branch refs,
    no branch selector, no per-node active-version selector, and no copy step
    across branches. The one store-level pointer is `ROOT`, a single full ref
    line naming the default view root; a folder-level `.bd_root` pointer names a
    store for discovery only. See
    [`BRANCHES-AND-VERSIONS.md`](BRANCHES-AND-VERSIONS.md).
14. **One work area at a time.** `<project>/bd_work/` holds exactly one view;
    `bd work REF` switches it by replacing the contents. Two writable folders
    never exist at once. Read-only `bd export` snapshots (tree, context, dot) are
    not a second work area. The area's view is independent of the store default
    root: `bd root` sets the default, `bd work` sets what is in the area.

## 8. Rejected alternatives

- **Typed ids (`INT-001`, `CLM-003`).** Readable, but the prefix duplicates
  `type`, adds validation, and makes running order awkward. Simplicity won.
- **Branch directories (`branches/<name>/nodes/`).** Clean layering, but a
  global selector and branch metadata returned, needing duplicate state.
- **Filename branches (`<id>-<branch>`).** Better, but branch names were
  global, and exclusion needed a marker. Versions are smaller: the branch is
  the root version.
- **Git branches as the only variant mechanism.** Serial checkouts, no
  simultaneous views across checkouts, generated-index churn, and stale
  generated output surviving checkout while stale.
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
  A single store-level `ROOT` line is accepted as the default view root; it
  names the full ref a bare command starts from and selects no version for any
  other node (§7.10). A folder-level `.bd_root` pointer is accepted only for
  store discovery and selects no view or version.
- **`use` selection maps for cross-branch mixes.** A solution is a branch;
  mixing is a merge or `git restore --source`; a selector would be a second
  branch mechanism.
- **Symlink worktrees as solution isolation.** `bd work` is a layout inside one
  checkout; isolation belongs to `git worktree`, or branch switching and view
  refresh get entangled.

## 9. Invariants

These are enforced or assumed:

1. The filename is identity and version: every node file is `<id>-<version>.md`,
   version >= 1; a bare `<id>.md` is invalid.
2. `contains`, `links`, and `ROOT` hold full `id-version` refs; a bare id is a
   CLI selector resolved inside the selected view and is never written to data.
3. `contains` order is display order.
4. Containment is a tree per view; no node is reached twice in one view, and
   one view holds at most one version per logical id (`duplicate-id`).
5. Every logical id is reachable from the global root through containment,
   through another file of the same id, or through a link from a reachable node.
6. Semantic links resolve in the store; links outside a view never pull in and
   warn unless the target is another containment root.
7. Arbitrary front matter is preserved on export.
8. Work trees contain node `.md` symlinks plus regular generated files.
9. Generated files (`INDEX.md`, `AGENTS.md`, `REFS.md`) are never hand-edited.
10. No generated artifact is committed.
11. A view never crosses a branch, and neither does a version: a version is a
    node-local file in one branch; a solution is a git branch and worktree;
    neither substitutes for the other, and no ref resolves through a branch.
12. One worktree per solution. A project has exactly one writable work area,
    `<project>/bd_work/`, holding one view at a time; it is disposable and
    ignored. Read-only exports are separate and never a second work area.
13. Structural edits preserve body bytes and all unrelated front matter.

## 10. Known limits

- Node versions do not sync across branches; git merges sync solutions.
- No three-way merge between node versions; synthesis is manual.
- One worktree per solution; switching branches can leave a layout pointing
  at paths absent from the new branch, so rebuild and run `--status`.
- Concurrent writers to one store serialize on an advisory lock in the system
  temp directory, so `bd new` allocates distinct ids and no writer loses a
  sibling. The lock is per host and per resolved path; separate checkouts still
  conflict in git, and edits made outside `bd` are not serialized.
- Symlinks require a POSIX filesystem; Windows needs developer mode.
- Editors that replace symlinks need `--status`/`--writeback`.
- `bd check` validates every node-rooted view, costing more on large stores.
- There is no CI configuration yet; packaging is a `pyproject.toml` with the
  `bd` console script.

## 11. Open questions

1. Are versions immutable snapshots enforced by convention, or should the tool
   create a new version on every edit?
2. Should `bd replace` run automatically after `bd clone`, or stay a separate
   command?
3. Do we need filtered views (selectors over fields) in addition to closures?
4. How should two views be merged: repoint one parent, or synthesize a new
   version and repoint to it?
5. Should concurrent agent sessions share the one work area under leases, or
   each use a separate git worktree?
6. Are the generic projections (`tree`/`context`/`dot`) enough, or do we need
   per-workflow report renderers (traceability matrix, claim-evidence table)?
7. Should node-local versions be deprecated entirely in favour of git branches,
   or kept for cheap A/B variants inside one branch?
