"""Visual graph renders: clustered DOT and Graphviz-backed SVG."""

from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from bd_tree.cli import main
from bd_tree.errors import BreakdownError
from bd_tree import graph as graph_module
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


def test_render_dot_has_one_cluster_per_effective_folder_and_edge_labels():
    graph, refs = _example_graph()
    dot = render_dot(graph, refs)

    assert dot.count("subgraph cluster_") == 6
    for label in (
        "layer 0 — intent",
        "layer 1 — breakdown",
        "layer 2 — claims/structural",
        "layer 2 — claims/verification",
        "layer 3 — verification/fan-in",
        "layer 4 — operation",
    ):
        assert f'label="{label}"' in dot
    assert "rankdir=LR;" in dot
    assert '"1-1" [label="1-1\\nVerify the staged graph"];' in dot
    assert '"4-1" [label="4-1\\nTwo parents, one node"];' in dot
    assert '"1-1" -> "2-1" [label="breaks_down"];' in dot
    assert '"3-1" -> "4-1" [label="supports"];' in dot
    # Derived in-edges are not drawn: only the authored 2-1 -> 4-1 exists.
    assert dot.count('-> "4-1"') == 2
    assert '"4-1" -> "2-1"' not in dot


def test_render_dot_is_deterministic():
    graph, refs = _example_graph()
    assert render_dot(graph, refs) == render_dot(graph, refs)


@needs_dot
def test_render_svg_returns_svg_with_titles_and_stage():
    graph, refs = _example_graph()
    svg = render_svg(graph, refs)

    assert svg.startswith("<?xml") or svg.startswith("<svg")
    assert "<svg" in svg
    assert "Two parents, one node" in svg
    assert "layer 0" in svg
    assert "breaks_down" in svg
    assert render_svg(graph, refs) == svg


@needs_dot
def test_graph_svg_prints_to_stdout(monkeypatch, capsys):
    monkeypatch.chdir(EXAMPLES)
    assert main(["graph", "--svg"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("<?xml") or out.startswith("<svg")
    assert "layer 0" in out


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
    assert "subgraph cluster_0" in text


def test_graph_text_out_writes_file(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(EXAMPLES)
    target = tmp_path / "graph.txt"
    assert main(["graph", "--out", str(target)]) == 0
    assert f"text -> {target}" in capsys.readouterr().out
    assert "layer 0 — intent" in target.read_text(encoding="utf-8")


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
    stage = _node_lines(render("--stage", "0:1"))
    typed = _node_lines(render("--type", "breaks_down"))

    assert len(full) == 10
    assert len(depth) == 3 and len(depth) < len(full)
    assert len(stage) == 3 and len(stage) < len(full)
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
