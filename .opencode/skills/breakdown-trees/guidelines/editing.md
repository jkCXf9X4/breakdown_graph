# Editing through the work area

One writable area, one view, symlinks into the store. Editing a symlink edits
the store file; git sees the node file, never the layout.

## Enter and confirm

```bash
bd work REF                 # build or replace <project>/bd_work for one view
bd work                     # no REF: use the default view
bd work REF --depth 2       # materialize only two descendant levels
bd current                  # <project>/bd_work (view REF+N)
work_dir=$(bd current --path)
$EDITOR "$(bd edit REF)"    # exits 2 if REF is outside the materialized prefix
```

`bd work REF` replaces the area's contents: stale links are removed and
`INDEX.md`, `AGENTS.md`, `REFS.md` are regenerated. The area never accumulates
two views, and a second work folder is not supported. The view is always the
full containment closure; `REF+N` or `--depth N` only prunes which descendant
levels are materialized (`N=0` leaves the root alone). `bd edit` honors that
prefix, so a ref in the full closure but below the materialized depth is
refused. A bare id such as `bd edit 5` is a selector resolved in the active
view; the path returned is the placement path (for example
`bd_work/5-1-<title-slug>.md`, or a `section`/`name` path when the node sets
them), not a file named only by the ref.

`bd current --path` prints the directory without building anything;
`bd work REF --clean` discards detached files while switching.

## Placement paths

`section` is the only key that opens a directory. `section: true` uses the
node's placement name (explicit `name`, else the title slug, else the ref);
`section: "<dir>"` is verbatim and may contain several segments.

- A relative value (`suggested`, `suggested/01-indexes`) inherits the parent
  prefix, so nested stages stack inside one another.
- A leading `/` (`/06-evolution`) resolves from the output root, so a
  containment chain can keep layers as sibling directories.
- Several nodes may land in one directory when at most one of them has
  containment children there (a carrier beside its leaves, or leaves in one
  stage). Two nodes that both have containment children on one directory is an
  export error.
- `--path-template` opts out of section placement for the whole view; `{name}`
  and `{slug}` are the placement name, and any front-matter field is available.

A nested directory deserves an owning node: declare `section: suggested` once on
a stage node, then let its children declare only `01-indexes`, `02-snapshots`.
That keeps the chain out of every leaf and makes the stage usable as its own
view root and link target.

## Symlinks and generated files

- Node `.md` files in the area are relative symlinks to the store file
  `.bd_tree/nodes/<id>-<version>.md` (or `nodes/<id>-<version>.md` in a classic
  store); they are the store.
- `INDEX.md`, `AGENTS.md`, `REFS.md` are regular generated files. Never edit
  them; `bd work REF` rewrites them.
- Never copy node content into the area and never add a sync layer.

## When an editor replaces a symlink

Some editors write a new file over the link, leaving a detached copy.

```bash
bd work --status            # report links vs detached files for the active area
bd work --writeback         # copy detached edits back into the store
bd work REF --clean         # or discard them and rebuild
```

Switching views with detached files is refused until one of those runs.
`--writeback` refuses invalid front matter or a mismatched `id` rather than
corrupting the store.

## Direct store edits

`bd edit REF` resolves the path inside the active view and fails for a ref
outside the materialized `REF+N` prefix. Editing
`.bd_tree/nodes/<id>-<version>.md` directly works but bypasses the active-view
check; use it only when no area is active and the ref is known. `bd init`
already ignores `bd_work/`; an export directory is not auto-ignored.

Direct edits skip nothing else: the same `bd check` applies afterwards.

## After editing

```bash
bd work --status            # no detached files left
bd check                    # structure and views
git status --porcelain      # node files only, never bd_work/
```

Commit node files, never `bd_work/` or an export directory. If `bd_work/`
appears in `git status`, add it to `.gitignore` instead of committing it.
