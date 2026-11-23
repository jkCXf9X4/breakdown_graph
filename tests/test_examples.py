"""The committed example store is a clean graph example with the documented shape."""

from __future__ import annotations

from pathlib import Path

from bd_tree import api
from bd_tree.graph import audit, build_graph, graph_view, render_in

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


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
        assert isinstance(node.meta.get("stage"), int)
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
        "03-verification/INDEX.md",
        "04-operation/INDEX.md",
    }

    root = (out / "INDEX.md").read_text(encoding="utf-8")
    assert "[stage 0 — intent](00-intent/INDEX.md) — 1 node" in root
    assert "[stage 4 — operation](04-operation/INDEX.md) — 2 nodes" in root
    operation = (out / "04-operation" / "INDEX.md").read_text(encoding="utf-8")
    assert "[9-1 Operate the graph](9-1-operate-the-graph.md)" in operation
    assert "[10-1 Require sorted links](10-1-require-sorted-links.md)" in operation
