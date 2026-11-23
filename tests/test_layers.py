"""Relative graph mode: bands derived from ``layer`` when no ``stage`` exists."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from bd_tree import api
from bd_tree.cli import main
from bd_tree.errors import BreakdownError
from bd_tree.frontmatter import parse_document
from bd_tree.graph import (
    audit,
    build_graph,
    graph_layout,
    graph_view,
    render_graph,
)

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
STAGES = {
    "intent": 0,
    "breakdown": 1,
    "claims": 2,
    "verification": 3,
    "operation": 4,
}


def _codes(graph, anchor=None):
    return [issue.code for issue in audit(graph, anchor)]


def _labels(graph, refs):
    return [band.label for band in graph_layout(graph, refs)]


def _relative_files(out: Path) -> set[str]:
    return {
        path.relative_to(out).as_posix()
        for path in out.rglob("*")
        if path.is_file()
    }


def _copy_example(tmp_path: Path, name: str) -> Path:
    root = tmp_path / name
    shutil.copytree(EXAMPLES / ".bd_tree", root / ".bd_tree")
    return root


def test_band_order_is_derived_from_cross_layer_edges(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, layer="intent", links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2, layer="build", links=[{"to": "3", "type": "supports"}])
    write(nodes, 3, layer="verify")

    graph = build_graph(tmp_path)
    assert graph.relative
    assert graph.band == {"1-1": 0, "2-1": 1, "3-1": 2}
    assert _labels(graph, graph_view(graph, "1-1")) == ["intent", "build", "verify"]
    # --stage filters by the derived band ordinal in relative mode.
    assert set(graph_view(graph, "1-1", stages=(1, 1))) == {"1-1", "2-1"}
    assert set(graph_view(graph, "1-1", stages=(2, 2))) == {"1-1", "3-1"}
    text = render_graph(graph, graph_view(graph, "1-1"))
    assert "layer 0 — intent" in text
    assert "layer 2 — verify" in text


def test_unconnected_layers_get_a_deterministic_tie_break(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, layer="intent", links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2, layer="build")
    write(nodes, 3, layer="ops")

    graph = build_graph(tmp_path)
    assert _labels(graph, list(graph.store.nodes)) == ["intent", "build", "ops"]
    assert render_graph(graph, list(graph.store.nodes)) == render_graph(
        build_graph(tmp_path), list(graph.store.nodes)
    )


def test_layer_cycle_is_reported_and_rendering_still_works(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, layer="build", links=[{"to": "2", "type": "supports"}])
    write(nodes, 2, layer="verify")
    write(nodes, 3, layer="verify", links=[{"to": "4", "type": "supports"}])
    write(nodes, 4, layer="build")

    graph = build_graph(tmp_path)
    assert "graph-layer-cycle" in _codes(graph, "1-1")
    text = render_graph(graph, list(graph.store.nodes))
    assert "layer 0 — build" in text
    assert "layer 1 — verify" in text


def test_missing_and_invalid_layers_are_collected(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, layer="intent", links=[{"to": "2", "type": "supports"}])
    write(nodes, 2)
    write(nodes, 3, layer="")

    codes = _codes(build_graph(tmp_path), "1-1")
    assert codes.count("graph-layer-missing") == 1
    assert codes.count("graph-layer-invalid") == 1
    text = render_graph(build_graph(tmp_path), ["1-1", "2-1", "3-1"])
    assert "layer 0 — intent" in text
    assert "unlayered" in text


def test_same_layer_order_back_edge_is_reported(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, layer="build", order=2, links=[{"to": "2", "type": "supports"}])
    write(nodes, 2, layer="build", order=1)

    assert "graph-order-back-edge" in _codes(build_graph(tmp_path), "1-1")


def test_link_refuses_a_layer_cycle(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, layer="build", links=[{"to": "2", "type": "supports"}])
    write(nodes, 2, layer="verify")

    with pytest.raises(BreakdownError, match="layer cycle"):
        api.link(tmp_path, "2-1", "1-1", link_type="supports")


def test_link_refuses_a_same_layer_order_back_edge(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, layer="build", order=0)
    write(nodes, 2, layer="build", order=0)

    with pytest.raises(BreakdownError, match="forward within layer"):
        api.link(tmp_path, "2-1", "1-1", link_type="supports")


def test_new_requires_layer_and_rejects_stage(tmp_path):
    api.init_store(tmp_path, graph=True)

    with pytest.raises(BreakdownError, match="needs a non-empty --layer"):
        api.new_node(tmp_path, parent="1-1", fields={"title": "No layer"})
    with pytest.raises(BreakdownError, match="stores without stage use --layer"):
        api.new_node(tmp_path, parent="1-1", stage=1)

    created = api.new_node(
        tmp_path, parent="1-1", layer="next", fields={"title": "Next"}
    )
    meta = parse_document(created.read_text(encoding="utf-8")).meta
    assert meta["layer"] == "next" and "stage" not in meta
    assert not api.check(tmp_path).issues


def test_new_validates_the_parent_edge_in_relative_mode(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes, 1, layer="build", order=5,
        links=[{"to": "2", "type": "supports"}],
    )
    write(nodes, 2, layer="verify")

    with pytest.raises(BreakdownError, match="forward within layer"):
        api.new_node(tmp_path, parent="1-1", layer="build", order=5)
    with pytest.raises(BreakdownError, match="layer cycle"):
        api.new_node(tmp_path, parent="2-1", layer="build")


def test_init_graph_writes_a_layer_root_and_audits_clean(tmp_path):
    api.init_store(tmp_path, graph=True)
    meta = parse_document(
        (tmp_path / ".bd_tree" / "nodes" / "1-1.md").read_text(encoding="utf-8")
    ).meta
    assert meta == {"id": 1, "title": "Root", "layer": "root"}
    assert api.load(tmp_path).model == "graph"
    assert _codes(build_graph(tmp_path), "1-1") == []


def test_relative_tree_and_graph_label_bands_as_layers(write, tmp_path, monkeypatch, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, layer="intent", links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2, layer="build")
    monkeypatch.chdir(tmp_path)

    assert main(["tree", "1-1"]) == 0
    assert "layer 0 — intent" in capsys.readouterr().out
    assert main(["graph"]) == 0
    assert "layer 1 — build" in capsys.readouterr().out


def test_relative_and_absolute_exports_share_simple_band_paths(write, tmp_path):
    relative = tmp_path / "relative"
    absolute = tmp_path / "absolute"
    for root, stages in ((relative, None), (absolute, {"intent": 0, "build": 1, "verify": 2})):
        nodes = root / "nodes"
        write(nodes, 1, layer="intent", links=[{"to": "2", "type": "breaks_down"}], **({} if stages is None else {"stage": stages["intent"]}))
        write(nodes, 2, layer="build", links=[{"to": "3", "type": "supports"}], **({} if stages is None else {"stage": stages["build"]}))
        write(nodes, 3, layer="verify", **({} if stages is None else {"stage": stages["verify"]}))

    rel_tree, abs_tree = tmp_path / "rel_tree", tmp_path / "abs_tree"
    rel_graph, abs_graph = tmp_path / "rel_graph", tmp_path / "abs_graph"
    for root, out in ((relative, rel_tree), (absolute, abs_tree)):
        api.export_view("tree", root, "1-1", out)
    for root, out in ((relative, rel_graph), (absolute, abs_graph)):
        api.export_view("graph", root, "1-1", out)

    assert _relative_files(rel_tree) == _relative_files(abs_tree)
    assert _relative_files(rel_graph) == _relative_files(abs_graph)
    assert _relative_files(rel_tree) == _relative_files(rel_graph)
