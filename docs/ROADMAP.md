# Roadmap

Ordered by leverage. Each item names the problem it removes.

## P0 — structural edit commands

```
bd contain PARENT CHILD [--before REF]
bd uncontain PARENT CHILD
bd link FROM TO --type TYPE [--propagates]
bd unlink FROM TO [--type TYPE]
```

Why: `contains` and `links` are currently edited by hand in YAML. Every structural
edit must preserve `contains` order, materialize inherited lists before editing,
and keep `REFS.md`/view paths consistent. These commands also give an agent a
safe protocol that never rewrites prose.

## P1 — work tree ergonomics

```
bd work --list
bd work REF --filter FIELD=VALUE
bd work REF --open
```

Why: several work trees over one store are now normal. A list shows what exists,
where, and whether it is healthy. Filters would make a view narrower than a
containment closure without inventing a new view root.

## P1 — diffs and comparison

- `bd diff A B --changed` (default to changed rows; `--all` for everything).
- `bd diff A B --body` with unified body diffs per node.
- Optional `--out FILE` for review reports.

Why: comparing two realizations is the core exploration loop, and the current diff
prints all ids.

## P2 — promotion and merge

- `bd promote REF --rewrite-refs`: rewrite incoming references from the version to
  main.
- `bd merge FROM INTO`: three-way per node with explicit conflict reporting.
- Keep the rule: a merge produces a decision record, not silent prose blending.

Why: promotion is a copy today; incoming references to the promoted version keep
pointing at the old snapshot.

## P2 — concurrency

- Per-node advisory lease or lock when a work tree is edited by an agent.
- `bd status` showing uncommitted node edits and which work trees see them.
- Keep git as the durable conflict detector.

Why: multiple agents can edit the same node through different work trees and
overwrite each other.

## P2 — validation

- `bd check --fix` for safe repairs: stale pins, missing main, unreachable version
  files, `REFS.md` out of date.
- `bd check --view all` for multi-view validation.
- Faster per-view tree validation for large stores.

## P3 — packaging and CI

- `pyproject.toml` with a console script.
- CI: pytest, `bd check` on both corpora, no tracked generated output.
- A small fixture store under `tests/fixtures/` for documentation examples.

## P3 — import

- Generalize the typed-id migration into `bd import` with a configurable
  parent-selection rule.
- Support imports without containment by assigning a temporary root and reporting
  orphans.
- Keep the body gate: imported bodies must match after ref substitution.

## P3 — renderers

- Traceability matrix (two fields as axes).
- Claim-evidence table.
- Timeline from date fields.
- Work-layer board (`status` columns).

Why: `tree`/`context`/`dot` cover structure; a few workflows want domain reports,
but they must stay data-driven.

## P3 — portability

- Windows symlink guidance or a `--copy` mode with explicit writeback.
- Optional `--json` output for scripts, explicitly opt-in, never a data file.
