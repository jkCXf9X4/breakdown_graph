# Rebuild plan — evaluation of the updated breakdown skills

Date: 2026-11-25
Baseline: `docs/breakdown/.bd_tree` archived to `bd_tree.tar.gz` in this folder.
Baseline metrics: 59 nodes, 0 `## Purpose` sections, 51 detached `## Links`
sections, 1 inline token, 105 list tokens, average body 172 words.

The rebuild uses the updated skills in
`src/agent_methods/methods/` (topology, node authoring, product-breakdown,
pb-alignment). Scope is the same product, bd_tree. Titles are derived from the
archived coverage list and the tool docs. Prose and links are authored fresh
from the tool documentation; archived bodies are not copied.

Cleanup after the audit: `42-1` was merged into `8-1`, so the live store is 48
nodes. The table below is the initial 49-row scaffold; `rebuild-plan.tsv` is the
same initial scaffold.

## Coverage merges

| Archived title | Merged into |
|---|---|
| 41-1 Git-dependent tests skip without git | 33-1 Temporary stores drive the test suite |
| 46-1 Generated files stay generated | 22-1 The work area is a flat symlink layout |
| 48-1 Snapshots stay outside the work area | 46-1 Snapshot list and prune |
| 49-1 Solution worktrees are created per branch | 30-1 The work area and the git boundary are separate modules |
| 50-1 Switching views replaces the work area | 22-1 The work area is a flat symlink layout |
| 53-1 Cross-branch version synchronization | 45-1 Three-way merge between versions |
| 55-1 Recovery for symlink-replacing editors | 38-1 Detached edits block a switch until repair |
| 59-1 Flat view index grouped by ring | 1-1 Product Breakdown — bd_tree |

`36-1` (install/upgrade) and `37-1` (migration) are new nodes covering the README
install and migration sections; the archive had no separate titles for them.

Layer groups:

| Ref | Layer | Kind |
|---|---|---|
| 1-1 | root | group |
| 2-1 | intent | group |
| 3-1 | product | group |
| 4-1 | architecture | group |
| 5-1 | implementation | group |
| 6-1 | verification | group |
| 7-1 | operation | group |
| 8-1 | evolution | group |
| 9-1 | review | group |
| 10-1 | decisions (history) | index |

Node list:

| Ref | Parent | Kind | Title | Coverage from archive |
|---|---|---|---|---|
| 1-1 | — | group | Product Breakdown — bd_tree | 1-1 |
| 2-1 | 1-1 | group | Intent — why bd_tree exists | 2-1 |
| 3-1 | 1-1 | group | Product — what bd_tree promises | 3-1 |
| 4-1 | 1-1 | group | Architecture — how bd_tree is organized | 4-1 |
| 5-1 | 1-1 | group | Implementation — where bd_tree is built | 5-1 |
| 6-1 | 1-1 | group | Verification — how bd_tree proves its claims | 6-1 |
| 7-1 | 1-1 | group | Operation — how bd_tree is run | 7-1 |
| 8-1 | 1-1 | group | Evolution — what might change | 8-1 |
| 9-1 | 1-1 | group | Review — what is still contested | new layer |
| 10-1 | 1-1 | index | Decisions — why bd_tree changed | 10-1 |
| 11-1 | 2-1 | claim | Credibility belongs to the producing chain | 16-1 |
| 12-1 | 2-1 | claim | Large trees need a bounded agent context | 17-1 |
| 13-1 | 2-1 | claim | Layered breakdowns lose credibility across handovers | 18-1 |
| 14-1 | 3-1 | claim | Front matter stays project-defined | 19-1 |
| 15-1 | 3-1 | claim | Git owns the solution boundary | 20-1 |
| 16-1 | 3-1 | claim | One project has one writable work area | 21-1 |
| 17-1 | 3-1 | claim | One store yields many read-only projections | 22-1 |
| 18-1 | 4-1 | claim | A filename encodes identity and version | 23-1 |
| 19-1 | 4-1 | claim | Typed links define the component view | 25-1 + 27-1 |
| 20-1 | 4-1 | claim | Node files are the only source of truth | 28-1 |
| 21-1 | 4-1 | claim | Root precedence selects the default view | 29-1 + 24-1 |
| 22-1 | 4-1 | claim | The work area is a flat symlink layout | 30-1 |
| 23-1 | 4-1 | claim | Freshness is opt-in per edge | 26-1 |
| 24-1 | 5-1 | claim | CLI and API share one command surface | 31-1 |
| 25-1 | 5-1 | claim | Exporter renders read-only projections | 32-1 |
| 26-1 | 5-1 | claim | Loader owns filenames, discovery, and views | 33-1 |
| 27-1 | 5-1 | claim | Model and checker separate shape from validation | 34-1 |
| 28-1 | 5-1 | claim | Inline scanner preserves body bytes | 35-1 (split) |
| 29-1 | 5-1 | claim | Ops performs body-preserving structural edits | 35-1 |
| 30-1 | 5-1 | claim | Work and solutions own the writable area | 36-1 + 37-1 |
| 31-1 | 6-1 | claim | Check validates store and view invariants | 38-1 |
| 32-1 | 6-1 | claim | The example store is the clean reference | 39-1 |
| 33-1 | 6-1 | claim | Temporary stores drive the test suite | 43-1 |
| 34-1 | 6-1 | claim | Stale checking is view-scoped | 42-1 |
| 35-1 | 6-1 | claim | Exit codes separate success, navigation, and structure | 40-1 |
| 36-1 | 7-1 | claim | Install and upgrade preserve the store | 47-1 + rg |
| 37-1 | 7-1 | claim | Migration converts retired data | new |
| 38-1 | 7-1 | claim | Detached edits block a switch until repair | 44-1 + 51-1 |
| 39-1 | 7-1 | claim | Discovery walks up, then scans down | 45-1 |
| 40-1 | 7-1 | claim | Init scaffolds a hidden-store project | 47-1 |
| 41-1 | 7-1 | claim | Writers serialize on an advisory lock | 52-1 |
| 42-1 | 8-1 | contract (merged into 8-1) | The IMP funnel has three stages | 11-1..15-1, 59-1 |
| 43-1 | 8-1 | work | Windows symlink support | 58-1 |
| 44-1 | 8-1 | work | Generic markdown importer | 54-1 |
| 45-1 | 8-1 | work | Three-way merge between versions | 57-1 |
| 46-1 | 8-1 | work | Snapshot list and prune | 56-1 |
| 47-1 | 9-1 | review | Known limits and open questions | 11-1 (section) |
| 48-1 | 9-1 | review | Coverage gaps in the reference store | 59-1 |
| 49-1 | 10-1 | history | Decision log index | 60-1 |

Cross-layer relations to author (in the source node, inline):

- Product claims realize an intent claim where the product choice exists because
  of the intent claim (`realizes`).
- Architecture claims realize an intent claim or a product claim (`realizes`).
- Implementation claims implement an architecture claim (`implements`).
- Verification claims verify an architecture or implementation claim (`verifies`).
- Operation claims operate an architecture or product claim (`operates`).
- Evolution work items change an architecture or implementation claim (`changes`).
- Review findings assess the layer or nodes they name (`assesses` or `relates_to`
  with a stated sentence).
- The decision index links the decision record; the record cites the affected
  nodes (`supersedes` or `relates_to` with a stated sentence).

All links live inline in the asserting sentence or membership list. No `## Links`
section survives. Every current node opens with `## Purpose`.
