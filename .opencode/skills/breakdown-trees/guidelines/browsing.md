# Browsing a breakdown store

Read only what the question needs: one view, the narrowest descendant depth,
and `--max-chars` on any body dump.

## Which store and which view

- `bd` resolves `--root`, then `$BD_ROOT`, then walks up from the current
  directory (at each directory a store there first, then a `.bd_root` pointer),
  then scans downward to depth 3 for a unique store. Several stores below the
  cwd is refused. A `.bd_root` file holds one store path, so a nested store does
  not require a flag when a pointer names it.
- Project layout: store at `<project>/.bd_tree/`, nodes under
  `.bd_tree/nodes/`. Classic layout: `nodes/` at the repo root.
- The store's topology is detected once: containment when any node declares
  `contains`; otherwise graph when at least one node has `links`, `stage`, or a
  non-empty `layer`/`band`. `Store.model`
  exposes it, and `bd tree` / `bd views` show the result.
- The default view root is `ROOT` when present, else a graph store's lowest
  graph root, else a containment store's lowest node by `(id, version)`. An
  explicit ref argument or `--view` wins over both; `bd check --view` only
  narrows reporting.
- Data refs are full `id-version`. A bare id on the command line is a selector
  resolved inside the selected view, never written to data.
- `bd work REF` does **not** change the default root; it changes the view held
  by the work area. Track them separately.

## Output shapes

`bd tree` — the topology outline. In a containment store it is one node per
line, `ref title`; `+-` marks a non-last child, `` `- `` the last, and `|`
continues an ancestor column. Default depth is 2; `--depth 0` is unlimited. In a
graph store it renders the graph bands (`layer N — label` in relative mode,
`stage N — label` in absolute mode, then `[ref] title`
with authored `→ out` and derived `← in` lines); inferred nested bands and
explicit subpaths print as indented folder headings. `--depth` bounds
containment only. `--summary` appends summaries and `--fields F,F` appends field values.
`--columns F,F` switches to the table view (`ref title summary` by default,
depth 1), with descendants indented two spaces per level and cells capped by
`--max-chars`. `--links` appends a `links:` footer for edges leaving a
containment view — in the outline only; the `--columns` table ignores it:

```
1-1 Root
+- 2-1 Why does this exist?
`- 3-1 What is true?
```

`bd graph [REF]` — graph-only: the forward closure as graph bands, with
`--depth N` link hops, `--stage A:B` (an absolute stage or top-level derived
band ordinal range; a nested band inherits its ancestor's ordinal), `--type T`,
and `--dot`. In relative mode a band comes from `band` (or the first `layer`
segment);
later segments are explicit subfolders and inferred nesting adds more.
`--svg [--out PATH]` renders the same graph through Graphviz; `bd export dot
--render svg|png|pdf` and `bd export svg` write rendered files. `bd out REF`
lists authored out-edges; `bd in REF` lists derived in-edges.

`bd show REF+N` — the node plus N levels of descendant bodies (link hops in a
graph store), each capped at 4000 characters when N > 0. `--max-chars 0` prints
the full body; `--no-body` prints headings only. `--links` appends the same
footer, as `source -> target  title  (type)`; it is a pointer, not membership —
open the target with `bd show REF`. `bd path REF` gives the breadcrumb: the
ancestor chain oldest first, or in a graph store the reverse link chain with the
first parent chosen when a node has several.

`bd current` — exactly `<project>/bd_work (view <ref>)`; `--path` prints only
the path, `--view` only the ref, and it errors when no area exists.

`bd views` — topology roots (containment roots or graph roots), one
`ref title` per line, store default marked `*`. A history or decisions view
appears here without joining the default containment closure; switch to it with
`bd work REF` when you need to edit it.

`bd root` — `<ref>  (ROOT|lowest node)`.

`bd check` — `N nodes, N errors, N warnings (view REF)` on the last line, with
one `LEVEL path: message` line per issue. It dispatches on topology: graph
audit for a graph store, containment checks otherwise. The output does not print
issue codes; use the code tables in [`validation.md`](validation.md) to read the
message. `bd audit [REF]` is the explicit graph audit.

## Search

`bd find QUERY` scans titles, summaries, bodies, and all string fields of the
default view. Narrow with `--field F`, `--where K=V`, `--limit N`, `--view REF`,
or widen with `--all`.

`bd find 'RE' --regex` treats the query as a Python regular expression. It
defaults to the default view, so a hit missing from your current area may
simply be outside it — check `--view` before concluding it does not exist.

## Reading discipline

- Start wide and cheap: `bd views`, then `bd tree REF --depth 1`; in a graph
  store read the graph bands once with `bd graph`.
- Go deep only on the branch the question is about; `+N` and `--max-chars`
  exist to keep bodies bounded. In a graph store `+N` is link hops.
- When a node cites another ref, trust the ref and read it directly rather
  than searching for the text again.
- `bd check` is a store-wide scan and can be slow on large stores; use it as a
  gate, not as a browsing tool.
