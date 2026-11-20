"""The committed example stores stay valid and keep their documented shape."""

from __future__ import annotations

from pathlib import Path

from bd_tree.api import check, load, load_view

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_switch_trees_example_is_clean():
    root = EXAMPLES
    hidden = load(EXAMPLES / ".bd_tree")
    assert hidden.root == (EXAMPLES / ".bd_tree").resolve()
    assert hidden.project_root == EXAMPLES.resolve()
    store = load(root)
    assert store.root == hidden.root
    assert store.root_ref == "1-1"
    result = check(root)
    assert result.ok
    assert result.view == "1-1"


def test_switch_trees_example_has_two_complete_trees():
    root = EXAMPLES
    default = load_view(root, "1-1")
    alternative = load_view(root, "1-2")
    assert set(default.nodes) == {
        "1-1",
        "2-1",
        "3-1",
        "4-1",
        "5-1",
        "6-1",
        "7-1",
    }
    assert set(alternative.nodes) == {"1-2", "2-2", "3-2", "4-2", "5-2"}
