"""The committed example store stays valid and keeps its documented shape."""

from __future__ import annotations

from pathlib import Path

from bd_tree.api import check, load, load_view

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_example_store_is_clean():
    hidden = load(EXAMPLES / ".bd_tree")
    assert hidden.root == (EXAMPLES / ".bd_tree").resolve()
    assert hidden.project_root == EXAMPLES.resolve()
    store = load(EXAMPLES)
    assert store.root == hidden.root
    assert store.root_ref == "20-1"
    result = check(EXAMPLES)
    assert result.ok
    assert result.view == "20-1"


def test_header_free_chain_example_matches_the_documented_layout(tmp_path):
    from bd_tree import api

    root = EXAMPLES
    view = load_view(root, "20-1")
    assert len(view.nodes) == 17
    assert view.nodes["21-1"].section == "00-intent"
    assert view.nodes["21-1"].section_rooted is True
    assert view.nodes["22-1"].section == "00-intent"
    assert view.nodes["22-1"].section_rooted is True
    assert view.nodes["36-1"].section == "suggested"
    assert view.nodes["36-1"].section_rooted is False
    assert view.nodes["35-1"].section == "02-snapshots"
    assert set(load_view(root, "36-1").nodes) == {"36-1", "34-1", "35-1"}

    work = (tmp_path / "view").resolve()
    api.work(root, "20-1", work)
    paths = {
        path.relative_to(work).as_posix()
        for path in work.rglob("*.md")
        if path.is_symlink()
    }
    assert len(paths) == 17
    assert "00-root/product-breakdown-header-free.md" in paths
    assert "00-intent/no-layer-schema.md" in paths
    assert "04-verification/multiple-parents-rejected.md" in paths
    assert "06-evolution/per-folder-index.md" in paths
    assert "06-evolution/suggested/suggested-work.md" in paths
    assert "06-evolution/suggested/01-placement/section-flat-idea.md" in paths
    assert "06-evolution/suggested/02-snapshots/snapshot-list-and-prune.md" in paths
