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


def test_fan_out_header_example_matches_the_documented_layout(tmp_path):
    from bd_tree import api

    root = EXAMPLES
    view = load_view(root, "20-1")
    assert len(view.nodes) == 10
    headers = {
        "37-1": "00-intent",
        "38-1": "01-product",
        "43-1": "02-evolution",
    }
    for ref, section in headers.items():
        assert view.nodes[ref].section == section
        assert view.nodes[ref].section_rooted is True
    # Claims inherit the header prefix instead of declaring their own section.
    for ref in ("21-1", "24-1", "33-1"):
        assert view.nodes[ref].section is None
    assert view.nodes["36-1"].section == "suggested"
    assert view.nodes["36-1"].section_rooted is False
    assert view.nodes["34-1"].section == "01-placement"
    assert view.nodes["35-1"].section == "02-snapshots"
    assert set(load_view(root, "36-1").nodes) == {"36-1", "34-1", "35-1"}

    work = (tmp_path / "view").resolve()
    api.work(root, "20-1", work)
    paths = {
        path.relative_to(work).as_posix()
        for path in work.rglob("*.md")
        if path.is_symlink()
    }
    assert paths == {
        "00-root/product-breakdown.md",
        "00-intent/intent.md",
        "00-intent/credibility-of-the-chain.md",
        "01-product/product.md",
        "01-product/two-axes.md",
        "02-evolution/evolution.md",
        "02-evolution/per-folder-index.md",
        "02-evolution/suggested/suggested-work.md",
        "02-evolution/suggested/01-placement/section-flat-idea.md",
        "02-evolution/suggested/02-snapshots/snapshot-list-and-prune.md",
    }


def test_example_export_writes_one_index_per_folder(tmp_path):
    from bd_tree import api

    out = (tmp_path / "tree").resolve()
    result = api.export_view("tree", EXAMPLES, "20-1", out)
    assert result.nodes == 10

    generated = {
        path.relative_to(out).as_posix()
        for path in result.files
        if path.name == "INDEX.md"
    }
    assert generated == {
        "INDEX.md",
        "00-root/INDEX.md",
        "00-intent/INDEX.md",
        "01-product/INDEX.md",
        "02-evolution/INDEX.md",
        "02-evolution/suggested/INDEX.md",
        "02-evolution/suggested/01-placement/INDEX.md",
        "02-evolution/suggested/02-snapshots/INDEX.md",
    }

    root = (out / "INDEX.md").read_text(encoding="utf-8")
    assert "[Credibility belongs to the producing chain]" in root
    evolution = (out / "02-evolution" / "INDEX.md").read_text(encoding="utf-8")
    assert "[Evolution](evolution.md)" in evolution
    assert "[One index per folder](per-folder-index.md)" in evolution
    assert "[suggested](suggested/INDEX.md)" in evolution
    assert evolution.index("evolution.md") < evolution.index("per-folder-index.md")
    assert evolution.index("per-folder-index.md") < evolution.index("suggested/INDEX.md")
