from __future__ import annotations

import shutil

import pytest

from bd_tree import exporter
from bd_tree.api import export_view
from bd_tree.cli import main
from bd_tree.errors import BreakdownError

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _graph_store(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "supports"}], title="Root intent")
    write(nodes, 2, title="Child claim")
    return tmp_path


def _require_graphviz():
    if shutil.which("dot") is None:
        pytest.skip("Graphviz 'dot' is not installed")


def test_export_dot_without_render_writes_only_the_dot_file(write, tmp_path):
    root = _graph_store(write, tmp_path)
    out = tmp_path / "graph.dot"
    result = export_view("dot", root, "1-1", out)
    assert result.files == [out]
    assert [p.name for p in tmp_path.iterdir() if p.is_file()] == ["graph.dot"]


def test_render_svg_writes_dot_and_svg(write, tmp_path):
    _require_graphviz()
    root = _graph_store(write, tmp_path)
    out = tmp_path / "graph.dot"
    result = export_view("dot", root, "1-1", out, render=["svg"])
    svg = out.with_suffix(".svg")
    assert sorted(result.files) == sorted([out, svg])
    text = svg.read_text(encoding="utf-8")
    assert "<svg" in text
    assert "Root intent" in text
    assert "supports" in text


def test_render_png_writes_the_png_signature(write, tmp_path):
    _require_graphviz()
    root = _graph_store(write, tmp_path)
    out = tmp_path / "graph.dot"
    result = export_view("dot", root, "1-1", out, render=["png"])
    png = out.with_suffix(".png")
    assert png in result.files
    assert png.read_bytes()[:8] == PNG_SIGNATURE


def test_render_two_formats_writes_three_files(write, tmp_path):
    _require_graphviz()
    root = _graph_store(write, tmp_path)
    out = tmp_path / "graph.dot"
    result = export_view("dot", root, "1-1", out, render=["svg", "png"])
    names = sorted(p.name for p in result.files)
    assert names == ["graph.dot", "graph.png", "graph.svg"]
    assert all(p.is_file() for p in result.files)


def test_render_out_with_two_formats_errors(write, tmp_path):
    _require_graphviz()
    root = _graph_store(write, tmp_path)
    out = tmp_path / "graph.dot"
    with pytest.raises(BreakdownError, match="render-out"):
        export_view(
            "dot",
            root,
            "1-1",
            out,
            render=["svg", "png"],
            render_out=tmp_path / "one.svg",
        )


def test_render_out_with_one_format_writes_exactly_that_path(write, tmp_path):
    _require_graphviz()
    root = _graph_store(write, tmp_path)
    out = tmp_path / "graph.dot"
    target = tmp_path / "custom" / "picture.svg"
    result = export_view(
        "dot", root, "1-1", out, render=["svg"], render_out=target
    )
    assert sorted(result.files) == sorted([out, target])
    assert target.is_file()
    assert not out.with_suffix(".svg").exists()


def test_missing_dot_raises_but_leaves_the_dot_file(write, tmp_path, monkeypatch):
    root = _graph_store(write, tmp_path)
    out = tmp_path / "graph.dot"
    monkeypatch.setattr(exporter.shutil, "which", lambda _name: None)
    with pytest.raises(BreakdownError, match="Graphviz"):
        export_view("dot", root, "1-1", out, render=["svg"])
    assert out.is_file()
    assert "digraph bd_tree" in out.read_text(encoding="utf-8")


def test_cli_export_svg_writes_an_svg(write, tmp_path):
    _require_graphviz()
    root = _graph_store(write, tmp_path)
    out = tmp_path / "only.svg"
    code = main(
        ["export", "svg", "--root", str(root), "--view", "1-1", "--out", str(out)]
    )
    assert code == 0
    assert "<svg" in out.read_text(encoding="utf-8")
    assert not out.with_suffix(".dot").exists()


def test_cli_export_svg_requires_out(write, tmp_path):
    root = _graph_store(write, tmp_path)
    with pytest.raises(SystemExit):
        main(["export", "svg", "--root", str(root), "--view", "1-1"])


def test_cli_render_out_mismatch_exits_nonzero(write, tmp_path):
    _require_graphviz()
    root = _graph_store(write, tmp_path)
    out = tmp_path / "graph.dot"
    code = main(
        [
            "export",
            "dot",
            "--root",
            str(root),
            "--view",
            "1-1",
            "--out",
            str(out),
            "--render",
            "svg",
            "--render",
            "png",
            "--render-out",
            str(tmp_path / "one.svg"),
        ]
    )
    assert code == 2
