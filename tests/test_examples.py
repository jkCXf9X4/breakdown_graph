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


def test_section_placement_example_matches_the_documented_layout(tmp_path):
    from bd_tree import api

    root = EXAMPLES
    default = load_view(root, "1-1")
    assert default.nodes["5-1"].section == "05-limits"
    assert default.nodes["6-1"].section == "great-stuff"

    out = (tmp_path / "view").resolve()
    api.work(root, "1-1", out)
    paths = {
        path.relative_to(out).as_posix()
        for path in out.rglob("*.md")
        if path.is_symlink()
    }
    assert paths == {
        "1-1-root-alternative.md",
        "2-1-method.md",
        "3-1-data.md",
        "4-1-analysis.md",
        "05-limits/limits.md",
        "05-limits/great-stuff/great-stuff.md",
        "05-limits/great-stuff/7-1.md",
    }
    assert api.edit_path(root, "5-1", out) == out / "05-limits" / "limits.md"
    assert api.edit_path(root, "6-1", out) == (
        out / "05-limits" / "great-stuff" / "great-stuff.md"
    )
