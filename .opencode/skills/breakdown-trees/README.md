# Method: breakdown-trees

Work a `bd` breakdown store correctly: find the store, detect its topology,
read one view, edit through the single `bd_work/` area, change structure with
`bd` commands, and prove the result valid.

Why: the store is a flat set of node files and everything else is derived. A
store is a graph (forward `links` with relative `layer` or absolute `stage`
bands) or containment (`contains`), detected per store. Agents break it by
editing the wrong layer — hand-editing
generated files, keeping a second work folder, hand-writing `contains` or
`links`, or treating a graph as containment — so the method fixes the mechanism
and leaves content decisions to the breakdown skills.

File map: [`__INDEX__.md`](__INDEX__.md).

## Adopt it

This copy is installed globally: it lives at
`~/.config/opencode/skills/breakdown-trees/` and opencode loads it in every
project. The source of truth is `.opencode/skills/breakdown-trees/` in the
`info_graph` repository; edit it there and republish, never edit the installed
copy in place.

1. Install the `bd` CLI once (`pip install -e '.[test]'` from a `bd_tree`
   clone); without installing, run it as `PYTHONPATH=src python3 -m bd_tree`.
2. Confirm the baseline with `bd check` before any edit; add `bd audit` in a
   graph store.
3. Pair it with the `product-breakdown` skill (what a node should say) and
   `pb-alignment` (whether the tree is right). This skill only owns the
   mechanism.
