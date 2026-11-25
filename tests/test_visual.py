"""Visual graph renders: flat DOT and Graphviz-backed SVG."""

from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from bd_tree import graph as graph_module
from bd_tree.cli import main
from bd_tree.errors import BreakdownError
from bd_tree.graph import (
    build_graph,
    graph_view,
    render_dot,
    render_svg,
)

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
DOT = shutil.which("dot")

needs_dot = pytest.mark.skipif(DOT is None, reason="Graphviz dot is not installed")


def _example_graph():
    graph = build_graph(EXAMPLES)
    return graph, graph_view(graph, "1-1")


def _node_lines(dot: str) -> list[str]:
    return [
        line
        for line in dot.splitlines()
        if " -> " not in line and line.strip().startswith('"') and "[label=" in line
    ]


def test_render_dot_is_flat_with_node_and_edge_labels():
    graph, refs = _example_graph()
    dot = render_dot(graph, refs)

    assert "subgraph cluster_" not in dot
    assert "rankdir=LR;" in dot
    assert len(_node_lines(dot)) == 12
    assert '"1-1" [label="1-1\\nVerify the undirected graph"' in dot
    assert '"4-1" [label="4-1\\nTwo parents, one node"' in dot
    assert '"1-1" -> "2-1" [label="breaks_down"];' in dot
    assert '"3-1" -> "4-1" [label="supports"];' in dot
    # Derived in-edges are not drawn: only the authored 2-1 -> 4-1 exists.
    assert dot.count('-> "4-1"') == 2
    assert '"4-1" -> "2-1"' not in dot


def test_render_dot_is_deterministic():
    graph, refs = _example_graph()
    assert render_dot(graph, refs) == render_dot(graph, refs)


def test_render_dot_color_by_front_matter_is_deterministic():
    graph, refs = _example_graph()
    assert render_dot(graph, refs, color_by="status") == render_dot(
        graph, refs, color_by="status"
    )


@needs_dot
def test_render_svg_returns_svg_with_titles_and_edges():
    graph, refs = _example_graph()
    svg = render_svg(graph, refs)

    assert svg.startswith(("<?xml", "<svg"))
    assert "<svg" in svg
    assert "Two parents, one node" in svg
    assert "breaks_down" in svg
    assert render_svg(graph, refs) == svg


@needs_dot
def test_graph_svg_prints_to_stdout(monkeypatch, capsys):
    monkeypatch.chdir(EXAMPLES)
    assert main(["graph", "--svg"]) == 0
    out = capsys.readouterr().out
    assert out.startswith(("<?xml", "<svg"))


@needs_dot
def test_graph_svg_out_writes_file(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(EXAMPLES)
    target = tmp_path / "graph.svg"
    assert main(["graph", "--svg", "--out", str(target)]) == 0
    assert f"svg -> {target}" in capsys.readouterr().out
    text = target.read_text(encoding="utf-8")
    assert "<svg" in text and "Two parents, one node" in text


def test_graph_dot_out_writes_file(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(EXAMPLES)
    target = tmp_path / "graph.dot"
    assert main(["graph", "--dot", "--out", str(target)]) == 0
    assert f"dot -> {target}" in capsys.readouterr().out
    text = target.read_text(encoding="utf-8")
    assert text.startswith("digraph bd_graph {")
    assert "subgraph cluster_" not in text
    assert '"1-1" -> "2-1"' in text


def test_graph_text_out_writes_file(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(EXAMPLES)
    target = tmp_path / "graph.txt"
    assert main(["graph", "--out", str(target)]) == 0
    assert f"text -> {target}" in capsys.readouterr().out
    assert "## 0 — 1-1" in target.read_text(encoding="utf-8")


def test_graph_dot_and_svg_are_mutually_exclusive(monkeypatch):
    monkeypatch.chdir(EXAMPLES)
    with pytest.raises(SystemExit) as exc:
        main(["graph", "--dot", "--svg"])
    assert exc.value.code == 2


def test_visual_filters_narrow_the_render(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(EXAMPLES)

    def render(*argv: str) -> str:
        target = tmp_path / f"{len(list(tmp_path.iterdir()))}.dot"
        assert main(["graph", "--dot", "--out", str(target), *argv]) == 0
        capsys.readouterr()
        return target.read_text(encoding="utf-8")

    full = _node_lines(render())
    depth = _node_lines(render("--depth", "1"))
    window = _node_lines(render("--distance", "0:1"))
    typed = _node_lines(render("--type", "breaks_down"))

    assert len(full) == 12
    assert len(depth) == 3 and len(depth) < len(full)
    assert len(window) == 3 and len(window) < len(full)
    assert len(typed) == 6 and len(typed) < len(full)
    assert "Two parents, one node" in "\n".join(typed)
    assert "Derived in-edges" not in "\n".join(typed)


def test_render_svg_reports_a_missing_dot_binary(monkeypatch):
    graph, refs = _example_graph()
    monkeypatch.setattr(graph_module.shutil, "which", lambda name: None)
    with pytest.raises(BreakdownError, match="Graphviz 'dot' not found"):
        render_svg(graph, refs)


def test_render_svg_includes_dot_stderr_on_failure(monkeypatch):
    graph, refs = _example_graph()
    monkeypatch.setattr(
        graph_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1, stdout="", stderr="syntax error near line 3"
        ),
    )
    with pytest.raises(BreakdownError, match="syntax error near line 3"):
        render_svg(graph, refs)
