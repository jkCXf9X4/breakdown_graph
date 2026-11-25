"""DOT and SVG rendering of a graph view."""

from __future__ import annotations

import shutil

import pytest

from bdg.cli import main
from bdg.graph import build_graph, graph_view, render_dot, render_svg

DOT = shutil.which("dot")
needs_dot = pytest.mark.skipif(DOT is None, reason="Graphviz 'dot' is not installed")


def _graph_store(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "supports"}], title="Root intent")
    write(nodes, 2, title="Child claim")
    return tmp_path


def test_render_dot_labels_nodes_and_edges(write, tmp_path):
    root = _graph_store(write, tmp_path)
    graph = build_graph(root)
    text = render_dot(graph, graph_view(graph, "1-1"))
    assert text.startswith("digraph bd_graph {")
    assert '"1-1" -> "2-1" [label="supports"]' in text
    assert 'label="1-1\\nRoot intent"' in text
    assert '"2-1" [label="2-1\\nChild claim"' in text
    assert "fillcolor" in text


def test_render_dot_is_deterministic(write, tmp_path):
    root = _graph_store(write, tmp_path)
    graph = build_graph(root)
    refs = graph_view(graph, "1-1")
    assert render_dot(graph, refs) == render_dot(graph, refs)


@needs_dot
def test_render_svg_returns_svg_with_labels(write, tmp_path):
    root = _graph_store(write, tmp_path)
    graph = build_graph(root)
    svg = render_svg(graph, graph_view(graph, "1-1"))
    assert svg.startswith(("<?xml", "<svg"))
    assert "<svg" in svg
    assert "Root intent" in svg
    assert "supports" in svg


def test_cli_graph_format_dot_writes_a_dot(write, tmp_path):
    root = _graph_store(write, tmp_path)
    out = tmp_path / "only.dot"
    code = main(
        ["graph", "--root", str(root), "--format", "dot", "--out", str(out)]
    )
    assert code == 0
    text = out.read_text(encoding="utf-8")
    assert text.startswith("digraph bd_graph {")
    assert '"1-1" -> "2-1" [label="supports"]' in text
    assert not out.with_suffix(".svg").exists()


@needs_dot
def test_cli_graph_format_svg_writes_an_svg(write, tmp_path):
    root = _graph_store(write, tmp_path)
    out = tmp_path / "only.svg"
    code = main(
        ["graph", "--root", str(root), "--format", "svg", "--out", str(out)]
    )
    assert code == 0
    assert "<svg" in out.read_text(encoding="utf-8")
    assert not out.with_suffix(".dot").exists()
