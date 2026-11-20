"""The committed example stores stay valid and keep their documented shape."""

from __future__ import annotations

from pathlib import Path

from bd_tree.api import check, load, load_view

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_switch_trees_example_is_clean():
    root = EXAMPLES / "switch-trees"
    store = load(root)
    assert store.root_ref == "1-1"
    result = check(root)
    assert result.ok
    assert result.view == "1-1"


def test_switch_trees_example_has_two_complete_trees():
    root = EXAMPLES / "switch-trees"
    main = load_view(root, "1")
    alternative = load_view(root, "1-1")
    assert set(main.nodes) == {"1", "2", "3", "4", "5"}
    assert set(alternative.nodes) == {"1-1", "2-1", "3-1", "4-1", "5-1"}
