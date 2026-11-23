"""The committed example store is a clean graph example with the documented shape."""

from __future__ import annotations

import shutil
from pathlib import Path

from bd_tree import api
from bd_tree.graph import (
    audit,
    build_graph,
    graph_view,
    layout_paths,
    render_in,
)

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
LAYER_PATHS = {
    "4-1": "claims/structural",
    "5-1": "claims/structural",
    "6-1": "claims/structural",
    "7-1": "claims/verification",
    "8-1": "verification/fan-in",
}
GROUPED_PATHS = {
    "02-claims/structural/4-1-two-parents-one-node.md",
    "02-claims/structural/5-1-forward-closure.md",
    "02-claims/structural/6-1-stage-monotonicity.md",
    "02-claims/verification/7-1-derived-in-edges.md",
    "03-verification/fan-in/8-1-verification-fan-in.md",
}


def _example_store(tmp_path: Path) -> Path:
    shutil.copytree(EXAMPLES / ".bd_tree", tmp_path / ".bd_tree")
    return tmp_path


def _relative_files(out: Path) -> set[str]:
    return {
        path.relative_to(out).as_posix()
        for path in out.rglob("*")
        if path.is_file()
    }


def test_example_store_is_a_clean_graph():
    hidden = api.load(EXAMPLES / ".bd_tree")
    assert hidden.root == (EXAMPLES / ".bd_tree").resolve()
    assert hidden.project_root == EXAMPLES.resolve()
    store = api.load(EXAMPLES)
    assert store.root == hidden.root
    assert store.root_ref == "1-1"
    assert len(store.nodes) == 10
    assert set(store.nodes) == {f"{node}-1" for node in range(1, 11)}

    for node in store.nodes.values():
        assert isinstance(node.meta.get("layer"), str) and node.meta["layer"].strip()
        assert "contains" not in node.meta
        assert "section" not in node.meta

    graph = build_graph(EXAMPLES)
    assert graph.roots == ["1-1"]
    assert audit(graph) == []


def test_forward_closure_reaches_every_node():
    graph = build_graph(EXAMPLES)
    refs = graph_view(graph, "1-1")
    assert len(refs) == 10
    assert set(refs) == {f"{node}-1" for node in range(1, 11)}


def test_two_parent_node_has_two_derived_in_edges():
    graph = build_graph(EXAMPLES)
    incoming = render_in(graph, "4-1")
    assert incoming.startswith("2 in-links  [derived]")
    assert "2-1 -> 4-1 (breaks_down)  [derived]" in incoming
    assert "3-1 -> 4-1 (supports)  [derived]" in incoming


def test_example_graph_export_writes_stages_and_indexes(tmp_path):
    out = (tmp_path / "graph").resolve()
    result = api.export_view("graph", EXAMPLES, "1-1", out)
    assert result.nodes == 10

    generated = {
        path.relative_to(out).as_posix()
        for path in result.files
        if path.name == "INDEX.md"
    }
    assert generated == {
        "INDEX.md",
        "00-intent/INDEX.md",
        "01-breakdown/INDEX.md",
        "02-claims/INDEX.md",
        "02-claims/structural/INDEX.md",
        "02-claims/verification/INDEX.md",
        "03-verification/INDEX.md",
        "03-verification/fan-in/INDEX.md",
        "04-operation/INDEX.md",
    }

    root = (out / "INDEX.md").read_text(encoding="utf-8")
    assert "[layer 0 — intent](00-intent/INDEX.md) — 1 node" in root
    assert "[layer 4 — operation](04-operation/INDEX.md) — 2 nodes" in root
    operation = (out / "04-operation" / "INDEX.md").read_text(encoding="utf-8")
    assert "[9-1 Operate the graph](9-1-operate-the-graph.md)" in operation
    assert "[10-1 Require sorted links](10-1-require-sorted-links.md)" in operation

    claims = (out / "02-claims" / "INDEX.md").read_text(encoding="utf-8")
    assert "[structural/](structural/INDEX.md)" in claims
    assert "[verification/](verification/INDEX.md)" in claims
    structural = (out / "02-claims" / "structural" / "INDEX.md").read_text(
        encoding="utf-8"
    )
    assert "[4-1 Two parents, one node](4-1-two-parents-one-node.md)" in structural
    assert "→ [8-1 Verification fan-in]" in structural
    assert "← [2-1 Structural claims]" in structural


def test_example_nodes_declare_layer_subpaths_and_no_group():
    graph = build_graph(EXAMPLES)
    declared = {
        ref: node.meta["layer"]
        for ref, node in graph.store.nodes.items()
        if "/" in node.meta["layer"]
    }
    assert declared == LAYER_PATHS
    assert all("group" not in node.meta for node in graph.store.nodes.values())
    paths = layout_paths(graph, graph_view(graph, "1-1"))
    assert {path for path in paths.values() if path.count("/") > 1} == GROUPED_PATHS
    # 4-1 has two parents and still lands in exactly one subpath.
    assert paths["4-1"] == "02-claims/structural/4-1-two-parents-one-node.md"


def test_example_work_places_grouped_nodes_and_edit_resolves(tmp_path):
    root = _example_store(tmp_path)
    out = root / "bd_work"
    result = api.work(root, "1-1")

    assert result.nodes == 10 and result.symlinks == 10
    assert api.edit_path(root, "5-1") == (
        out / "02-claims" / "structural" / "5-1-forward-closure.md"
    )
    assert api.edit_path(root, "7-1") == (
        out / "02-claims" / "verification" / "7-1-derived-in-edges.md"
    )
    assert api.edit_path(root, "8-1") == (
        out / "03-verification" / "fan-in" / "8-1-verification-fan-in.md"
    )
    for directory in (
        out / "02-claims" / "structural",
        out / "02-claims" / "verification",
        out / "03-verification" / "fan-in",
    ):
        index = directory / "INDEX.md"
        assert index.is_file() and not index.is_symlink()

    status = api.work(root, status=True)
    assert status.ok
    assert len(status.entries) == 10
    assert {entry.status for entry in status.entries} == {"ok"}


def test_example_tree_and_graph_export_agree_on_grouped_file_set(tmp_path):
    root = _example_store(tmp_path)
    tree = tmp_path / "tree"
    graph = tmp_path / "graph"
    api.export_view("tree", root, "1-1", tree)
    api.export_view("graph", root, "1-1", graph)

    tree_files = _relative_files(tree)
    assert tree_files == _relative_files(graph)
    assert GROUPED_PATHS <= tree_files
    assert {
        "02-claims/structural/INDEX.md",
        "02-claims/verification/INDEX.md",
        "03-verification/fan-in/INDEX.md",
    } <= tree_files

    stage = (tree / "02-claims" / "INDEX.md").read_text(encoding="utf-8")
    assert "structural/INDEX.md" in stage
    assert "verification/INDEX.md" in stage
