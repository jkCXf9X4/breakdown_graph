# Migration: typed IDs -> numeric refs

Source: `/home/eriro/pwa/2_work/info_graph/workspace/licentiate` (read-only, 128 nodes)
Destination: `/home/eriro/pwa/2_work/info_graph/workspace/licentiate-n`

## Rule

- Parent = the cited target with the lowest strictly-lower layer index; ties broken by the lowest old numeric suffix; no candidate means the root.
- Layer order: intent 0, claims 1, argument 2, evidence 3, manuscript 4, verification 5, operation 6, review 7, evolution 8 (default).
- Root = `INT-001`. Children are DFS pre-ordered by (layer index, old id); new ids are assigned 1..N in that order, so `1` is the intent root.
- Each new file keeps body, type, layer, title, summary, date, status and home; sets integer `id`, adds `legacy`, maps links and rewrites every old typed-ID token in the body and string fields.

## Counts

- nodes written: 128
- root: `INT-001` -> `1`
- parented nodes (parent != root): 108
- attached directly to root: 19 (15 non-intent + 4 intent-layer)
- max depth: 4
- max children: 29 (`INT-001` -> `1`)

## Root-attached nodes

- `INT-002` -> `2` (intent layer)
- `INT-003` -> `27` (intent layer)
- `INT-004` -> `33` (intent layer)
- `RQ-001` -> `34` (intent layer)
- `CLM-003` -> `83`
- `ARG-005` -> `90`
- `ARG-008` -> `106`
- `LIT-005` -> `112`
- `LIT-006` -> `114`
- `MS-009` -> `117`
- `MS-010` -> `118`
- `MS-011` -> `119`
- `RV-002` -> `120`
- `IMP-025` -> `121`
- `IMP-026` -> `122`
- `IMP-028` -> `123`
- `IMP-029` -> `124`
- `IMP-030` -> `125`
- `INFO-028` -> `128`

## Anomalies

- none; body gate: 0 mismatches
