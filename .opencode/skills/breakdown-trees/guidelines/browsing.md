# Browsing a breakdown store

Read only what the question needs: one view, the narrowest descendant depth,
and `--max-chars` on any body dump.

## Which store and which view

- `bd` walks up from the current directory for `nodes/` or `.bd_tree/nodes/`.
  A nested store needs `BD_ROOT=path/to/project` or `--root path/to/project`.
- Project layout: store at `<project>/.bd_tree/`, nodes under
  `.bd_tree/nodes/`. Classic layout: `nodes/` at the repo root.
- The default view root is `ROOT` when present, else the lowest main ref. An
  explicit ref argument or `--view` wins over both; `bd check --view` only
  narrows reporting.
- `bd work REF` does **not** change the default root; it changes the view held
  by the work area. Track them separately.

## Output shapes

`bd tree` — one node per line, `ref title`; `+-` marks a non-last child, `` `- ``
the last, and `|` continues an ancestor column. Default depth is 2; `--depth 0`
is unlimited. `--summary` appends summaries and `--fields F,F` appends field
values. `--columns F,F` switches to the table view (`ref title summary` by
default, depth 1), with descendants indented two spaces per level and cells
capped by `--max-chars`. `--links` appends a `links:` footer for edges leaving
the view:

```
1 Root
+- 2 Why does this exist?
`- 3 What is true?
```

`bd show REF+N` — the node plus N levels of descendant bodies, each capped at
4000 characters when N > 0. `--max-chars 0` prints the full body; `--no-body`
prints headings only; `bd path REF` gives the breadcrumb. `--links` appends the
same footer, as `source -> target  title  (type)`; it is a pointer, not
membership — open the target with `bd show REF`.

`bd current` — exactly `<project>/bd_work (view <ref>)`; `--path` prints only
the path, `--view` only the ref, and it errors when no area exists.

`bd views` — containment roots, one `ref title` per line, store default marked
`*`. A history or decisions view appears here without joining the default
closure; switch to it with `bd work REF` when you need to edit it.

`bd root` — `<ref>  (ROOT|lowest main)`.

`bd check` — `N nodes, N errors, N warnings (view REF)` on the last line.
`bd path REF` — the ancestor chain, oldest first.

## Search

`bd find QUERY` scans titles, summaries, bodies, and all string fields of the
default view. Narrow with `--field F`, `--where K=V`, `--limit N`, `--view REF`,
or widen with `--all`.

`bd find 'RE' --regex` treats the query as a Python regular expression. It
defaults to the default view, so a hit missing from your current area may
simply be outside it — check `--view` before concluding it does not exist.

## Reading discipline

- Start wide and cheap: `bd views`, then `bd tree REF --depth 1`.
- Go deep only on the branch the question is about; `+N` and `--max-chars`
  exist to keep bodies bounded.
- When a node cites another ref, trust the ref and read it directly rather
  than searching for the text again.
- `bd check` is a store-wide scan and can be slow on large stores; use it as a
  gate, not as a browsing tool.
