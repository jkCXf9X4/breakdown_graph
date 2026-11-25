# Design

Status: established 2026-11-14; revised 2026-11-25 for undirected views and the
ring layout. This document records the model, the decisions behind it, and the
invariants the implementation relies on.

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
declared component, and make stale material visible rather than silently
present.

## 2. Principles

1. **One store, many projections.** The node files are the only source of truth;
   views, indexes, graphs, exports, and the work layout are derived and
   disposable. Read-only projections may be many; the writable work area is
   exactly one (§5).
2. **Identity is not location.** A node is a running integer; its path in a view
   is presentation metadata.
3. **One topology: typed links.** A node declares typed link tokens in its
   body; in-edges are derived. A view is the weakly connected component of one
   anchor. Direction remains in the data and as a label, but it does not gate
   membership. Ordering is the undirected BFS distance from the anchor.
4. **No schema.** Front matter is arbitrary; the built-in keys are listed below.
   Layer names, types, and status values are user data.
5. **Work in the store, through one work area.** The writable work area is a
   flat symlink view, not a copy, and there is no sync-back. A project has
   exactly one such area at a time; switching views replaces its contents.
6. **No sidecar state.** No JSON manifests, TOML view configs, persistent lock
   files, or active-branch files; the only pointers are the store-level `ROOT`,
   one ref on one line, and the folder-level `.bd_root`, one store path on one
   line. The active view of the work area is recorded in its generated
   `REFS.md`, not in a separate file. Everything else is in the node files or
   derived. A writer's advisory lock is transient and lives in the system temp
   directory, keyed by the store path, so no lock file enters the store or git.
7. **Freshness is opt-in per edge.** A link participates in staleness only when
   the source node's `freshness:` map names its target with `propagates: true`.
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

### 3.2 Node body and front matter

Reserved front-matter keys:

| Key | Type | Semantics |
| --- | --- | --- |
| `id` | int | Optional logical id; must match the filename |
| `legacy` | string | Original identifier from an imported tree |
| `freshness` | map | Per-target freshness entries, keyed by full target ref |

Everything else is arbitrary and preserved on export. Typical fields: `title`,
`summary`, `type`, `status`, `date`, `phase`, `audience`, `tags`.

`name` and `title` are presentation metadata. The default work-area path uses
the store file's basename; a `--path-template` may read any field, and its
`{slug}` is the title slug, else the ref. `group`, `section`, `folder`, and
`home` are ordinary front matter: preserved, never read for layout, and they add
no schema.

Link declarations are reserved tokens in the body, not front-matter keys:

```markdown
The intent breaks down into [[breaks_down, 2-1]](Structural claims).

## Links
- [[verifies, 12-1]](Verification core)
```

- **Grammar:** `[[TYPE, REF]]`, optionally followed by spaces and `(TITLE)`.
  `TYPE` matches `[A-Za-z][A-Za-z0-9_-]*`; `REF` is a full `id-version` ref and
  never a bare id; `TITLE` is non-empty and excludes `)` and newlines.
- **Two forms:** a token inside prose, or a `- [[TYPE, REF]](TITLE)` line in a
  trailing `## Links` section. `bd new --parent` appends to the parent,
  `bd link` appends to the source, `bd unlink` removes, and `bd replace` /
  `bd clone --subtree` rewrite refs in place. Authors may also write tokens
  directly in sentences.
- **Cached title:** `(TITLE)` is advisory. Rendering always uses the target's
  live title; only `bd check` compares the cache and reports
  `link-title-stale`.
- **Ignored:** fenced code blocks, inline code spans, and the `\[[` escape.
  Indented code blocks and HTML comments are not handled.
- **Back-references are authored.** There is no derived opposite: if `3-1`
  writes `[[verifies, 8-1]]` and `8-1` should acknowledge it, `8-1` authors its
  own token with its own type. `bd in` still derives the reverse list from
  authored tokens and marks it `[derived]`.
- **Front-matter `links` is retired.** A node that still declares it is
  `links-removed`; `bd migrate` moves the list into the body as tokens.

Freshness pins live in one top-level map, keyed by target ref:

```yaml
freshness:
  '5-1':
    pinned: sha256:abc123def456
    propagates: true
```

- `propagates: true` opts that target edge into staleness; `pinned` holds the
  target body hash recorded at the last reconciliation.
- The hash is computed over the body with reserved token lines and the
  `## Links` heading stripped, so appending or removing a token does not
  invalidate a pin.
- `bd stale` / `bd reconcile` read and rewrite this map; a malformed entry is
  `invalid-freshness`.

### 3.3 The graph

Typed body tokens are the authored edges. Each token names one full target ref
and a type; the source node owns it. Out-edges are the authored tokens;
in-edges are derived by reversing them and are never written to a node file.

- There is one topology. Every token is structural: it joins its two nodes in
  the undirected view and supplies the type of the step.
- A view is the **weakly connected component** of one anchor over authored
  links, walked in both directions. A node reached through several neighbours
  appears once. Multiple parents, reciprocal pairs, back-edges, and cycles are
  legal. Only a self-loop on one ref is refused by `bd link`.
- **Distance** is the undirected BFS hop count from the anchor. It is the only
  ordering primitive: ring 0 is the anchor, ring 1 is split into children and
  parents, and deeper rings are numbered.
- **Direction is a label.** `Store.neighbors(ref)` returns `child` or `parent`
  for each authored neighbour. Kind precedence is `child > parent`; a
  reciprocal pair is a `child` from each side. Direction never filters
  membership or creates a validation error.
- **No derived opposite exists.** Nothing is marked `[derived]` in the store;
  `bd in` derives the reverse list from authored tokens and labels every line
  `[derived]`. A back-reference is an ordinary token in the other node.
- Tokens are expected in ascending target-ref order; `graph-unsorted-links`
  warns otherwise. `bd link` appends in call order and rewrites no existing
  line, so add targets monotonically or re-sort the section. Fan-out above 200
  warns and suggests an intermediate header.
- A node that still declares `contains` is an error (`contains-removed`) telling
  the user to run `bd migrate`. The key is not part of the model.

### 3.4 Views

A view is the weakly connected component of one anchor over authored tokens.
`bd export graph`, the other `bd export` choices, `bd work`, and `bd graph` take
an anchor ref. The default anchor is the store's `ROOT` file when present, else
the lowest member of the first component; an explicit ref where a command takes
one wins over both.
`bd check --view REF` only narrows reporting. `bd root REF` writes the file,
`bd root --clear` removes it, and `bd root` prints `<ref>  (ROOT|lowest)`. A
declared but missing ref is `root-ref-missing`; malformed content is
`invalid-root`. This default anchor is separate from the view the work area
holds: `bd root` changes the default used by commands, while `bd work REF`
replaces the contents of `<project>/bd_work/`. `bd current` reports the area and
the view actually there. `bd check` validates the store and the selected view;
`bd audit` is the explicit graph audit. `bd diff A B` compares components by
logical id. A view is not a substitute for a git branch: a version of the root
node with its own out-links gives an alternative component inside the same
checkout, and that component is the realization. Many components can exist in
one store and one working tree; only one of them is writable at a time. Two
axes, deliberately separate:

- **Solution boundary: git.** A branch and worktree hold one solution; git
  decides when to merge or discard it.
- **Merge unit: the flat `nodes/` store.** One file per node version and no
  nested output keep conflicts local to the version that changed.
- **Within a checkout: views.** Shape edges with `bd link`/`bd unlink` (and
  `bd new --parent`). A structural edit changes only the source file: body
  bytes and arbitrary front matter are preserved, except the appended or
  removed token lines in its `## Links` section (and `bd replace`, which
  rewrites token refs in place).

### 3.5 Versions

- Every node file is a version: `5-1.md`, `5-2.md`, and so on are peers, each
  immutable by convention, not enforcement. No version is privileged.
- `bd clone 5-1` copies a ref to the next free version of the same logical id
  (or to `--version N`) and keeps the source file's link tokens; it wires
  nothing into the current component. `bd clone 5-1 --subtree` clones the whole
  weak component of the source and rewrites the cloned token refs whose target
  was also cloned; `--depth N` narrows that to BFS rings `0..N` and implies
  `--subtree`, so edges leaving the prefix still point at the originals. The
  original stays untouched, and `--version` cannot be combined with `--subtree`
  or `--depth`.
  `bd replace OLD NEW` is the separate wiring step: it repoints inbound links,
  or repoints `ROOT` when OLD is the store root; OLD's file stays as a peer.
  Clone and swap in one logical flow with `bd clone 5-1 --subtree` then
  `bd replace 5-1 <printed new root ref>`. If OLD is outside the default view,
  `bd replace` errors. Several parents are legal; a reachable duplicate version
  warns (`graph-duplicate-version`).
  `bd delete 5-2` deletes a version, refusing an effective `ROOT` or a ref that
  is an inbound target of any link unless `--force`.
- An edge pins a full ref; a view warns when two versions of one id are
  reachable. There is no per-node pointer. Use `bd clone REF` then
  `bd replace REF NEW` for the common clone-and-swap path. Switch whole trees
  with `bd work REF` (the work area) or `bd root REF` (the store default).
  Switching needs no copy step.

Version references in link tokens are exact full refs (`6-2`, not `6`); this
makes a view independent of later edits to any peer.

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
trailing newline), with reserved token lines and the `## Links` heading removed
first, truncated to 12 hex characters. A token change therefore never
invalidates a pin.

## 5. Work folders

A work folder is a flat symlink layout of one view inside one checkout, not a
second copy. The flat node files are the merge unit; the containing git
branch/worktree is the solution boundary.

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
bd_work/4-1.md -> ../.bd_tree/nodes/4-1.md
```

- Each node `.md` is a relative symlink to its node file; editing the link edits
  the store, with no copy and no sync. The area is flat: one symlink per
  materialized ref, named after the store file. `INDEX.md`, `AGENTS.md`, and
  `REFS.md` are regular generated files. All views share one store, so an edit
  is visible in every view that includes the node.
- `bd work REF` writes the single `<project>/bd_work`. A different ref replaces
  the content of that area: stale links are removed, and the generated
  `INDEX.md`, `REFS.md`, and `AGENTS.md` are rewritten for the new view. With no
  REF, `bd work` uses the default anchor. Never keep two writable work folders
  side by side.
- The view is the whole component of one ref; the work area may materialize
  only rings `0..N`. `bd work REF+N` (the same display suffix as `bd show`) or
  `bd work REF --depth N` prunes the materialized prefix after the view is
  resolved; `N=0` leaves the anchor alone and `--depth` overrides a suffix. The
  generated `REFS.md`, `INDEX.md`, and `AGENTS.md` carry `REF+N`, so
  `bd current`, `--status`, `--writeback`, and `bd edit` recover the
  materialized depth; `bd edit` rejects a ref outside that prefix. A rebuild
  with a different depth, including a plain `bd work REF`, replaces the area and
  removes links that are no longer materialized.
- The active node of the area is the view ref in the `REFS.md` header
  (`# References — view REF[+N]`). `work.area()` reads `REFS.md` first and
  falls back to `INDEX.md`; there is no separate state file.
- `bd current` is the read-only query for that area: it prints
  `<project>/bd_work (view <ref>)`, `--path` prints only the path, and `--view`
  only the ref; it errors when no area exists.
  `bd edit REF` prints the absolute path of a ref in the active view and errors
  if it is not there. `bd views` lists component representatives and marks the
  store default with `*` and the work-area anchor.
- File naming is flat: each node uses the store file's basename.
  `--path-template` overrides the layout; the placeholders are `{ref}`, `{id}`,
  `{version}`, `{distance}`, `{slug}`, `{title}`, plus any front-matter key.
  `{slug}` is the title slug, else the ref. `group`, `section`, `folder`, and
  `home` place nothing.
- `--status` classifies paths as `ok`, `missing`, `wrong-target`, `detached`,
  `stray`, or `stale-ref`; `--writeback` refuses invalid front matter or a
  mismatched `id`, then writes the detached file wholesale — its body, including
  link tokens, is taken as edited. Both inspect the view actually in the area,
  not the requested or default view.
- Switching with detached (edited but unsynced) files is refused: they would be
  lost. Run `bd work --writeback` first to keep them, or `--clean` to discard
  them.
- Generated files: one root `INDEX.md` with ring sections (`## Active`,
  `## Distance 1 — children`, …), `REFS.md` (path, ref, kind, distance, title),
  and `AGENTS.md`. The index carries a `nodes:` front-matter path to the store's
  real `nodes/` folder; every node entry also links straight to its real file,
  so the reader can open, copy, or delete the actual files instead of the
  symlinks. Inside a git checkout, `AGENTS.md` also records branch, short
  commit, and worktree, so the folder identifies its solution boundary.
  Detection is best-effort: outside git the fields are omitted and the layout is
  unchanged. The generated file names are reserved in every directory, so a
  node can never resolve to one.

### One work area at a time

A full tree is too large to dump into an agent context: it displaces the rest of
the conversation, and the oldest parts are dropped. An agent therefore gets a
bounded, navigable subset, and the tool enforces the boundary: it holds exactly
one writable layout, the one the current `bd_work/` names. Switching views is
`bd work REF`, which replaces the area's contents instead of accumulating a
second folder.

Two work folders at once would defeat that rule. They make the current view
ambiguous, let edits land through whichever link an agent happens to open, and
leave two generated files claiming authority. The store is what scales; the
context is not, and one work area is the interface that keeps them apart.

Read-only projections remain: `bd export graph --view REF --out DIR` (the
component projection with one ring-section index for review or publishing),
`bd export context` (fresh nodes only, plus `STALE.md`, for an agent that must
not write), and `bd export dot`/`bd export svg` (Graphviz). They are disposable
snapshots, not a second work area; an agent session reads exactly one of them. A
snapshot may be made many times because it is never writable.

`bd solution` is a thin wrapper over `git worktree` (`new`, `list`, `remove`).
It stores no state and creates no layout: git remains authoritative for which
branch is checked out where; `bd work` remains the layout inside one checkout.

## 6. Schema-agnostic by construction

Nothing in the tool knows a project's layer names. The only reserved vocabulary
is structural: the front-matter keys `id`, `legacy`, and `freshness`, plus the
body token grammar `[[TYPE, REF]]` and its optional cached `(TITLE)`. `name` and
`title` are presentation metadata; `title` supplies the template slug. `group`,
`section`, `folder`, and `home` are ordinary front matter: preserved, never
read, with no effect on placement or validation.

Consequences: any workflow can define fields (`phase`, `status`, `stream`); the
graph orders nodes by undirected distance from the anchor; path templates read
any front-matter field; dot styling is chosen by arbitrary fields (`--color-by`,
`--shape-by`); and `bd check --require FIELD` is the escape hatch when a project
wants a schema.

## 7. Established decisions

1. **Running integer ids, no type prefixes.** Simpler filenames and refs; type
   information lives in front matter. Cost: ids are less self-describing.
2. **Flat storage, one file per node version.** Per-version diffs and merges, no
   path churn when titles change.
3. **Versions as mandatory filename suffixes.** `5-1`, `5-2`; every node is a
   version and no unsuffixed file exists.
4. **One topology: typed body tokens, undirected views.** A node authors edges
   as `[[TYPE, REF]]` tokens in its body; in-edges are derived. A view is the
   weakly connected component of the anchor, and distance is undirected BFS.
   Direction survives as a label. `contains` is retired; `bd migrate` converts
   an older store, including front-matter `links`.
5. **Views as components, not branches.** No branch names, branch directories,
   or global selector.
6. **Direction is a label; back-references are authored.** Membership is
   undirected; several parents and reciprocal edges are legal. There is no
   derived opposite: a node that should acknowledge an edge authors its own
   token with its own type. Only `bd in` derives the reverse list, marked
   `[derived]`.
7. **A cached token title is advisory.** `(TITLE)` saves a lookup but rendering
   always uses the target's live title; only `bd check` reports
   `link-title-stale`.
8. **Freshness is a per-node map.** Pins and `propagates` live in the
   `freshness:` front-matter map keyed by target ref, not inside edge objects;
   the pinned hash ignores reserved tokens and the `## Links` heading.
9. **Arbitrary front matter.** The tool fits any workflow; projects opt into
   validation.
10. **Freshness per edge, opt-in.** No hardcoded `serves`/`supports` semantics.
11. **Work trees with symlinks are the primary interface.** Flat, no sync-back,
   and exactly one writable work area.
12. **No JSON/TOML/lock/state sidecars.** The exceptions are the store-level
    `ROOT` file (one ref on one line) and the folder-level `.bd_root` pointer
    (one store path on one line). The work-area view lives in generated
    `REFS.md`. Derived output is disposable. The write lock is not a sidecar: it
    is transient and lives outside the store.
13. **Writeback requires valid front matter.** A detached file is written only
    when it parses and its `id` matches; its body, including link tokens, is
    taken as edited.
14. **Git owns solutions; `bd work` owns layout.** Worktrees isolate branches;
    the single `bd_work/` area shapes the current view inside one branch.
    Structural edits go through `bd link` / `bd unlink` and `bd clone` /
    `bd replace`.
15. **Branches and versions are disjoint layers.** Branches isolate whole
    checkouts; versions are peer files for single nodes. No cross-branch refs,
    no branch selector, no per-node active-version selector, and no copy step
    across branches. The one store-level pointer is `ROOT`, a single full ref
    line naming the default view anchor; a folder-level `.bd_root` pointer names
    a store for discovery only. See
    [`BRANCHES-AND-VERSIONS.md`](BRANCHES-AND-VERSIONS.md).
16. **One work area at a time.** `<project>/bd_work/` holds exactly one view;
    `bd work REF` switches it by replacing the contents. Two writable folders
    never exist at once. Read-only `bd export` snapshots (graph, context, dot,
    svg) are not a second work area. The area's view is independent of the store
    default anchor: `bd root` sets the default, `bd work` sets what is in the
    area.
17. **Flat ring layout is the only layout.** The work area holds one symlink per
    node at its store basename, plus one ring-section `INDEX.md` and one
    `REFS.md`. `group`, `section`, `folder`, and `home` are inert.
18. **2026-11-25: topology moved from a DAG with authored bands to an
    undirected component with a ring layout.** Cycles and back-edges broke the
    old assumptions: a cycle could leave a component with no root and no
    topological order, so the tool needed placement fields (`band`, `subpath`,
    `layer`, `stage`, `order`, and the ROOT `band_layout`/`band_order` hints) to
    answer a question the graph can answer itself. Membership is now the weak
    component of the anchor; ordering is undirected BFS distance; direction is a
    label. The cost is that distance is graph nearness, not semantic order, and a
    cycle has no privileged entry point. The gain is one fewer schema, no
    order-refusal class, legal cycles, and a work area that is a simple flat ring
    projection. Existing stores are converted by `bd migrate`, which strips the
    retired placement fields.
19. **2026-11-25: link declarations moved from front matter into body tokens,
    and symmetric masters were retired.** `links: [{to, type}]` split the
    assertion from the sentence it belonged to; a body token keeps the edge next
    to the prose and lets `bd link` append one line without rewriting a YAML
    list. Symmetry is no longer inferred: each node authors every edge it
    asserts, so a back-reference is an ordinary token and no `inverse`,
    `[derived]` opposite, or one-master rule survives. The cached `(TITLE)` is
    advisory only. Freshness moved out of the edge object into the top-level
    `freshness:` map, keyed by target ref, so pins survive token edits. Cost: a
    malformed token is a body-level error (`inline-malformed`) and indented code
    blocks and HTML comments are not shielded. Gain: one place for an assertion,
    no second copy to keep in sync, and no symmetric special case.

## 8. Rejected alternatives

- **Typed ids (`INT-001`, `CLM-003`).** Readable, but the prefix duplicates
  `type`, adds validation, and makes running order awkward. Simplicity won.
- **Authored placement (the retired `band`/`subpath`/`stage`/`order` model).**
  Now the rejected option. It asked every node to declare a position, forced a
  DAG assumption on a graph that legal cycles violate, and made cycles and
  back-edges unrepresentable without an error. BFS distance answers the same
  layout question from the graph itself. Migration strips the keys.
- **Containment as a second topology.** An ordered `contains` list duplicated
  the link relation, forced per-store detection and dispatch, and made
  `section` a second placement language. Removed: one typed-link topology;
  `bd migrate` converts an older store.
- **Front-matter `links` as the authoring surface.** It kept edges in a YAML
  block away from the sentence that asserts them, and a scalar link had to
  borrow the target's `type`. Body tokens are the authored assertion; a node
  that still declares `links` is `links-removed`.
- **Symmetric master with a derived opposite.** One file owned a two-way
  relation, but the relation could not be read from the other node, and
  validation needed `symmetric`/`inverse`, one-master, and
  propagation-refusal rules. Retired: each node authors its own token; `bd in`
  still derives the reverse list.
- **Per-link freshness keys.** `propagates`/`pinned` inside an edge object made
  every token append rewrite the YAML list. The top-level `freshness:` map
  keeps pins stable while tokens move.
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
  A single store-level `ROOT` line is accepted as the default view anchor; it
  names the full ref a bare command starts from and selects no version for any
  other node (§7.15). A folder-level `.bd_root` pointer is accepted only for
  store discovery and selects no view or version.
- **`use` selection maps for cross-branch mixes.** A solution is a branch;
  mixing is a merge or `git restore --source`; a selector would be a second
  branch mechanism.
- **Symlink worktrees as solution isolation.** `bd work` is a layout inside one
  checkout; isolation belongs to `git worktree`, or branch switching and view
  refresh get entangled.

## 9. Migration

`bd migrate` is the only conversion path. It keeps the classic-store path (bare
`nodes/<id>.md` files become `<id>-<version>.md`) and converts a containment
or front-matter-link store in place:

1. Each `contains: [c0, c1, ...]` becomes a typed body token
   `[[T, c0]]` in a trailing `## Links` section, in the same order, and the key
   is removed. `T` is `--type`, default `breaks_down`.
2. Front-matter `links` becomes one `- [[TYPE, REF]](TITLE)` line per edge,
   sorted by ref; a retired scalar link gains an explicit type taken from the
   target. Per-link `pinned`/`propagates` values move to the node's top-level
   `freshness:` map. `symmetric` and `inverse` are dropped.
3. Retired placement keys are stripped from every node (`band`, `subpath`,
   `layer`, `stage`, `order`) and from the ROOT node (`band_layout`,
   `band_order`). `section` stays as inert front matter and places nothing.
4. `--dry-run` reports the plan; the default applies atomically. `--root` works.

There is no placement flag and no symmetry flag: the token carries only its
type and ref.

A store that still declares `contains` fails `bd check` with `contains-removed`
until it is migrated. After migration `bd check` passes.

## 10. Invariants

These are enforced or assumed:

1. The filename is identity and version: every node file is `<id>-<version>.md`,
   version >= 1; a bare `<id>.md` is invalid.
2. Link tokens and `ROOT` hold full `id-version` refs; a bare id is a CLI
   selector resolved inside the selected view and is never written to data.
3. A view is the weakly connected component of its anchor over authored links.
   Membership is undirected; a node appears once at its minimum BFS distance.
4. Direction is a label: `child` or `parent`. It orders ring 1 but never filters
   membership.
5. Cycles, back-edges, and reciprocal pairs are legal. A self-loop on one ref is
   refused by `bd link`.
6. There is one edge relation: typed body tokens. Multiple parents are legal,
   and every node authors its own back-reference. No derived opposite exists;
   only reversed in-edges are marked `[derived]`.
7. No placement key exists in the model. `group`, `section`, `folder`, and
   `home` are inert front matter.
8. Every link resolves in the store, and every authored link inside one view is
   an edge.
9. Arbitrary front matter is preserved on export.
10. Work trees contain flat node `.md` symlinks plus regular generated files.
11. Generated files (`INDEX.md`, `AGENTS.md`, `REFS.md`) are never hand-edited.
12. No generated artifact is committed.
13. A view never crosses a branch, and neither does a version: a version is a
    node-local file in one branch; a solution is a git branch and worktree;
    neither substitutes for the other, and no ref resolves through a branch.
14. One worktree per solution. A project has exactly one writable work area,
    `<project>/bd_work/`, holding one view at a time; it is disposable and
    ignored. Read-only exports are separate and never a second work area. The
    active view is recorded in the generated `REFS.md`, not in extra state.
15. Structural edits preserve body bytes and all unrelated front matter, except
    the appended or removed token lines in a `## Links` section; `bd replace`
    and `bd clone --subtree` rewrite token refs in place.
16. `contains` is not data. A node that declares it is an error and is migrated,
    not interpreted.
17. Front-matter `links` is not data either: a node that declares it is
    `links-removed` and is migrated into body tokens.
18. A cached token title is advisory. All rendering reads the live title; only
    `bd check` compares the cache and warns `link-title-stale`.
19. Freshness pins live in the `freshness:` map keyed by target ref; the pinned
    body hash excludes reserved tokens and the `## Links` heading.

## 11. Known limits

- Node versions do not sync across branches; git merges sync solutions.
- No three-way merge between node versions; synthesis is manual.
- One worktree per solution; switching branches can leave a layout pointing
  at paths absent from the new branch, so rebuild and run `--status`.
- Distance is a graph metric, not a semantic order. A deeply linked but
  important node can sit in a high ring.
- Cycles shorten distances deterministically but have no privileged entry.
- Concurrent writers to one store serialize on an advisory lock in the system
  temp directory, so `bd new` allocates distinct ids and no writer loses a
  sibling. The lock is per host and per resolved path; separate checkouts still
  conflict in git, and edits made outside `bd` are not serialized.
- Symlinks require a POSIX filesystem; Windows needs developer mode.
- Editors that replace symlinks need `--status`/`--writeback`.
- `bd check` validates the store and the selected view, costing more on large
  stores.
- There is no CI configuration yet; packaging is a `pyproject.toml` with the
  `bd` console script.

## 12. Open questions

1. Are versions immutable snapshots enforced by convention, or should the tool
   create a new version on every edit?
2. Should `bd replace` run automatically after `bd clone`, or stay a separate
   command?
3. Do we need field selectors inside a component in addition to distance
   filters?
4. How should two views be merged: repoint one parent, or synthesize a new
   version and repoint to it?
5. Should concurrent agent sessions share the one work area under leases, or
   each use a separate git worktree?
6. Are the generic projections (`graph`/`context`/`dot`) enough, or do we need
   per-workflow report renderers (traceability matrix, claim-evidence table)?
7. Should node-local versions be deprecated entirely in favour of git branches,
   or kept for cheap A/B variants inside one branch?
