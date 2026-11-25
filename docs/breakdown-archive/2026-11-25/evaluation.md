# Evaluation: updated breakdown skills on a rebuilt bd_tree store

Date: 2026-11-25
Store: `docs/breakdown` (bd topology, 48 nodes, ROOT `1-1`)
Archived baseline: `bd_tree.tar.gz` in this folder (59 nodes, pre-rebuild)

## Setup

- Captured baseline metrics and the old graph before moving the store.
- Archived the old `.bd_tree` as a tarball; the live tree was moved out of the
  active path for the session. The new store was created with `bd init`, then
  scaffolded with `bd new`.
- Scope came from the archived title list and the tool docs; prose and links
  were authored fresh from `README.md`, `docs/DESIGN.md`, `docs/GRAPH.md`,
  `docs/GRAPH-LAYOUT.md`, `docs/DEVELOPING.md`,
  `docs/BRANCHES-AND-VERSIONS.md`, `AGENTS.md`, and the source modules.
  Archived bodies were not copied.
- Four exemplars were written first: the root map, an intent group, one claim,
  and one verification contract. Six disjoint layer authoring units then wrote
  the remaining nodes from the updated source skills.
- Three independent read-only scouts audited the result: pathology, authoring
  and structure, and identity/process/coverage. None had authored the nodes.

## Baseline versus rebuild

| Metric | Archived | Rebuilt |
|---|---:|---:|
| Nodes | 59 | 48 |
| `## Purpose` sections | 0 | 48 |
| Detached `## Links` sections | 51 | 0 |
| Real typed links | 99 | 88 |
| Links per node | 1.68 | 1.83 |
| Average content words | 123.9 | 140.3 |
| Content word range | 53-315 | 93-298 |
| `bd check` | 0 errors, 0 warnings | 0 errors, 0 warnings |
| `bd stale` | 0 rows | 0 rows |
| `bd current --status` | not recorded | 48 ok |
| Full test suite | not recorded | 405 passed |

The rebuild is smaller because the five empty stage nodes and the nine
suggested-candidate nodes were merged into the evolution group's funnel contract
plus four work items. The 59-to-48 reduction is that merge: stage groups are
state in one contract, not nodes of their own.

## Rule compliance

- Purpose: 48/48 nodes open with `## Purpose`; the scouts found a consumer,
  decision, and failure in every sentence.
- Inline links: 89 real typed links; 0 detached sections; 0 bare node references
  in bodies; one token per membership item.
- Membership motivation: after the fix described below, 0 membership items are
  bare titles. Every item states the member's role or order.
- Identity: full refs in tokens and `ROOT`; 0 dangling or duplicate links; 0
  stale title caches; declared vocabulary in `1-1` covers every type used.
- Structure: one component, no orphans, no duplicate versions, 48 symlinks ok.
- History: decision history is one record reached by a `records` edge to the
  index and a `breaks_down` edge to the record; live leaves do not cite it.

## What the first pass exposed

The first pass satisfied "no `## Links` section" with a bare
`Members, in reading order:` list of titled tokens. That is a link parking lot:
the list is detached from any sentence that says why a member belongs. The
skills allowed it because "membership list" was treated as a form, not as a
claim.

Fix in the skills:

- `breakdown-node-authoring/SKILL.md`: a membership list is not an exception;
  each item is a sentence that states why the member belongs.
- `breakdown-node-authoring/references/encoding.md`: the membership example now
  uses sentence items; a bare title list is named a parking lot.
- `product-breakdown-topology/SKILL.md` and `guidelines/structure.md`: a bare
  `Members:`/`Children:` title list parks links and is a finding.
- `pb-alignment/SKILL.md`: added the "Bare membership list" pathology.

Fix in the store: the root, all nine groups, and the decision index were
rewritten so every membership item is a sentence. This is the difference
between "the link is in the body" and "the body says why the link exists".

## Independent audit

The three scouts found the core rules held: purpose coverage, inline tokens, no
detached sections, no bare refs, one component, clean `bd check`/`bd stale`.
They also found real defects. Fixed in this pass:

- `16-1` duplicated `22-1`'s flat-symlink mechanics; `16-1` now states only the
  single-writable-surface promise.
- `49-1` was titled as an index but held a decision record, and claimed
  history was "out of the default view"; retitled and corrected to the actual
  `records`/`breaks_down` path.
- `36-1` repeated the migration fact owned by `37-1`; it now links the owner.
- `39-1` repeated root precedence and cited the loader for a CLI refusal.
- `3-1` said the tool writes `.bd_root`; only `ROOT` is store-owned.
- `24-1` claimed every command has a public API function; renderers are
  CLI-only and the claim now says so.
- `40-1` named a node file in its purpose; it now names a consumer by role.
- `42-1` cited a later sibling and repeated the group's aggregate; it was merged
  into `8-1`, which now owns the funnel contract.
- `48-1` carried a stale 59-node assertion; the test now asserts 48.
- `43-1`..`46-1` used `changes` where the sentence asserted a dependency; the
  sentences now assert the change.
- `10-1` no longer restates the record model; `30-1` is one claim about the
  work/git split.
- Source citations were corrected in `21-1`, `37-1`, `38-1`, `41-1`, and
  `29-1`; `rebuild-plan.md` now states the eight coverage merges; group lead
  sentences name the set and order, not each member's fact.
- Cross-repo skill citations were corrected to `../../src/agent_methods/...`;
  `records` replaced the noun `decision` as the history link type.

Residual finding:

- `47-1` keeps the contested design questions in Review. The layer guide routes
  investigations to Evolution; the node now frames them as contested findings,
  not selected work. This is a deliberate judgment call, not a broken rule.

## Process caveats

- The source skills in `src/agent_methods/methods/` are updated. The installed
  copies under `~/.config/opencode/skills` were not reinstalled; one fixer read
  the stale installed copies despite the brief. Its output was verified against
  the source rule and the store, but a clean evaluation should install the
  updated bundles before the run.
- The committed-store test `tests/test_examples.py` hardcoded 59 nodes; it now
  asserts 48. The full suite passes.

## Verdict

The three rules are teachable and observable after the membership-list fix:
purpose coverage, inline placement, and reference-as-link all hold on a fresh
store. The first pass shows where the doctrine was still gameable; the fix is
now in both the skill text and the store.

The remaining weaknesses are not link placement. They are citation discipline
and the layer placement of method-level meta-rules. Those are the next
evaluation pass, not a reason to reopen the three rules.
