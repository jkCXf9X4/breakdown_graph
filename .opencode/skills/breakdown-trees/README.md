# Method: breakdown-trees

Work a `bd` breakdown store correctly: find the store, read one view, edit
through the single `bd_work/` area, change structure with `bd` commands, and
prove the result valid.

Why: the store is a flat set of node files and everything else is derived.
Agents break it by editing the wrong layer — hand-editing generated files,
keeping a second work folder, or hand-writing `contains` — so the method fixes
the mechanism and leaves content decisions to the breakdown skills.

File map: [`__INDEX__.md`](__INDEX__.md).

## Adopt it

This copy is project-local: it lives at `.opencode/skills/breakdown-trees/`
and opencode loads it when the project is opened.

1. Install `bd` once from this clone: `pip install -e '.[test]'`; otherwise
   prefix commands with `PYTHONPATH=src python3 -m bd_tree`.
2. Confirm the baseline with `bd check` before any edit.
3. Pair it with the `product-breakdown` skill (what a node should say) and
   `pb-alignment` (whether the tree is right). This skill only owns the
   mechanism.
