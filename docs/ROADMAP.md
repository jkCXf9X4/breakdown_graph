# Roadmap

Ordered by leverage. Each item names the problem it removes.

## Done

- Structural edit commands: `bd contain`, `bd uncontain`, `bd link`, `bd unlink`.
- Two-axis model: git worktree is the solution boundary; `bd work` is the layout
  inside one checkout. Work folders record branch, commit, and worktree.
- Browsing: `bd tree`, `show`, `ls`, `find`, `grep`, `path`.
- Symlink work folders with `--status` and `--writeback`.

## P0 — solution ergonomics

- `bd solution new NAME [--from REF]` wraps
  `git worktree add ../NAME -b NAME` and then `bd work REF`.
- `bd solution list` shows `git worktree list` plus store root, branch, and node
  count.
- `bd solution remove NAME` wraps `git worktree remove`.

Why: worktrees are the solution boundary, and path mistakes are the common failure.
The wrapper must stay thin. Do not reimplement branch, merge, or checkout
semantics.

## P1 — work folder ergonomics

- `bd work --list` lists work folders in this checkout with root ref, node count,
  and status summary.
- `bd work REF --filter FIELD=VALUE` narrows a view without inventing a new
  containment root.
- `bd work REF --open` prints the path and opens `$EDITOR` at the view root.
- `--status` should report nodes added to the view since the last build, not only
  missing or detached ones.

Why: several layouts per checkout are normal. A list and a filter make them
discoverable; a status that notices additions keeps the folder honest.

## P1 — comparison

- `bd diff A B --changed` (default to changed rows; `--all` for everything).
- `bd diff A B --body` with unified body diffs per node.
- `bd where` prints store root, git branch, commit, and current view roots.

Why: comparing two realizations is the exploration loop. `git diff` compares
branches; `bd diff` compares containment views inside one branch.

## P2 — node-local versions

- Decide whether `bd fork` / `promote` / `retire-version` stay for cheap A/B
  variants inside one branch, or are deprecated in favour of git branches.
- If they stay: `bd promote REF --rewrite-refs` should rewrite incoming references
  from the version to main.
- Do not build a custom three-way merge. Solution merges are git merges.

Why: versions are useful for a local alternative, but they are the easiest place
to drift back into reimplementing git.

## P2 — concurrency

- Per-node advisory lease when a work folder is edited by an agent.
- `bd status` showing uncommitted node edits and which layouts see them.
- Keep git as the durable conflict detector.

Why: multiple agents can edit the same node through different worktrees or
layouts and overwrite each other.

## P2 — validation

- `bd check --fix` for safe repairs: stale pins, missing main, unreachable version
  files, `REFS.md` out of date.
- `bd check --view all` for multi-view validation.
- Faster per-view tree validation for large stores.

## P3 — packaging and CI

- `pyproject.toml` with a console script.
- CI: pytest, `bd check` on both corpora, git integration test, no tracked
  generated output.
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
