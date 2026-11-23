"""Layer paths: band/subpath validation, inference, folders, and materialization."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from bd_tree import api
from bd_tree.cli import main
from bd_tree.errors import BreakdownError
from bd_tree.frontmatter import parse_document, render_document
from bd_tree.graph import (
    audit,
    build_graph,
    graph_layout,
    graph_view,
    layout_paths,
    render_dot,
    render_graph,
)

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _w(
    nodes: Path,
    node_id: int,
    layer: str | None,
    *,
    links: list[str] | None = None,
    order: int = 0,
    **fields,
) -> Path:
    nodes.mkdir(parents=True, exist_ok=True)
    meta = {
        "id": node_id,
        "title": f"N{node_id}",
        "summary": "s",
        "name": f"{node_id}-1",
        "links": [{"to": target, "type": "breaks_down"} for target in links or []],
    }
    if layer is not None:
        meta["layer"] = layer
    if order:
        meta["order"] = order
    meta.update(fields)
    path = nodes / f"{node_id}-1.md"
    path.write_text(render_document(meta, "body\n"), encoding="utf-8", newline="")
    return path


def _fork(nodes: Path, *, nested: bool = False) -> None:
    _w(nodes, 1, "intent", links=["2-1"])
    if not nested:
        _w(nodes, 2, "breakdown", links=["3-1", "4-1", "5-1"])
    else:
        _w(nodes, 2, "breakdown", links=["3-1", "4-1", "5-1"])
    _w(nodes, 3, "sub-a", links=["6-1" if nested else "5-1"])
    _w(nodes, 4, "sub-b", links=["5-1"])
    _w(nodes, 5, "claims")
    if nested:
        _w(nodes, 6, "sub-sub", links=["5-1"])


def _codes(root: Path) -> list[str]:
    return [issue.code for issue in audit(build_graph(root), "1-1")]


def _paths(root: Path) -> dict[str, str]:
    graph = build_graph(root)
    return layout_paths(graph, graph_view(graph, "1-1"))


def test_single_chain_example_is_all_top_level_with_identical_paths():
    graph = build_graph(EXAMPLES)
    bands = graph_layout(
        graph,
        [
            "1-1", "2-1", "3-1", "4-1", "5-1", "6-1",
            "7-1", "8-1", "9-1", "10-1", "11-1", "12-1",
        ],
    )
    assert [band.label for band in bands] == [
        "intent", "breakdown", "claims", "verification", "operation"
    ]
    assert all(band.top_level for band in bands)
    assert {band.stage for band in bands} == {0, 1, 2, 3, 4}
    paths = layout_paths(graph, graph_view(graph, "1-1"))
    assert paths["4-1"] == "02-claims/structural/4-1-two-parents-one-node.md"
    assert paths["7-1"] == "02-claims/verification/7-1-derived-in-edges.md"
    assert paths["8-1"] == "03-verification/fan-in/8-1-verification-fan-in.md"
    assert paths["11-1"] == (
        "03-verification/fan-in2/11-1-verification-fan-in-2.md"
    )
    assert paths["12-1"] == "03-verification/12-1-verification-core.md"


def test_parallel_detours_nest_under_their_shortest_path_parent(write, tmp_path):
    nodes = tmp_path / "nodes"
    _fork(nodes)
    paths = _paths(tmp_path)
    assert paths["3-1"] == "01-breakdown/sub-a/3-1.md"
    assert paths["4-1"] == "01-breakdown/sub-b/4-1.md"
    assert paths["5-1"] == "02-claims/5-1.md"
    assert build_graph(tmp_path).band["3-1"] == 1
    assert build_graph(tmp_path).band["5-1"] == 2
    text = render_graph(build_graph(tmp_path), graph_view(build_graph(tmp_path), "1-1"))
    assert "  sub-a/" in text
    assert "  sub-b/" in text


def test_nested_detour_stacks_under_the_placed_child(write, tmp_path):
    nodes = tmp_path / "nodes"
    _fork(nodes, nested=True)
    paths = _paths(tmp_path)
    assert paths["6-1"] == "01-breakdown/sub-a/sub-sub/6-1.md"
    text = render_graph(build_graph(tmp_path), graph_view(build_graph(tmp_path), "1-1"))
    assert "    sub-sub/" in text


def test_equal_length_parallel_branches_are_both_top_level(write, tmp_path):
    nodes = tmp_path / "nodes"
    _w(nodes, 1, "intent", links=["2-1", "3-1"])
    _w(nodes, 2, "alpha", links=["4-1"])
    _w(nodes, 3, "beta", links=["4-1"])
    _w(nodes, 4, "sink")
    paths = _paths(tmp_path)
    assert paths["2-1"] == "01-alpha/2-1.md"
    assert paths["3-1"] == "02-beta/3-1.md"
    assert build_graph(tmp_path).band["2-1"] == 1
    assert build_graph(tmp_path).band["3-1"] == 2


def test_explicit_layer_path_wins_over_inference(write, tmp_path):
    nodes = tmp_path / "nodes"
    _w(nodes, 1, "intent", links=["2-1"])
    _w(nodes, 2, "breakdown/sub-a", links=["3-1"])
    _w(nodes, 3, "claims")
    paths = _paths(tmp_path)
    assert paths["2-1"] == "01-breakdown/sub-a/2-1.md"
    assert all(not path.startswith("01-breakdown/sub-a/breakdown") for path in paths.values())


def test_multi_segment_explicit_subpath_is_kept_verbatim(write, tmp_path):
    nodes = tmp_path / "nodes"
    _w(nodes, 1, "intent", links=["2-1"])
    _w(nodes, 2, "claims/structural/fan-in")
    assert _paths(tmp_path)["2-1"] == "01-claims/structural/fan-in/2-1.md"


def test_band_cycle_is_reported_and_rendering_is_deterministic(write, tmp_path):
    nodes = tmp_path / "nodes"
    _w(nodes, 1, "a", links=["2-1"])
    _w(nodes, 2, "b", links=["1-1"])
    graph = build_graph(tmp_path)
    assert "graph-layer-cycle" in _codes(tmp_path)
    first = render_graph(graph, list(graph.store.nodes))
    second = render_graph(build_graph(tmp_path), list(graph.store.nodes))
    assert first == second
    assert "layer 0 — a" in first and "layer 1 — b" in first


def test_missing_and_invalid_layers_fall_back_to_one_trailing_band(write, tmp_path):
    nodes = tmp_path / "nodes"
    _w(nodes, 2, "intent", links=["1-1", "3-1"])
    _w(nodes, 1, "a//b")
    _w(nodes, 3, None)
    codes = _codes(tmp_path)
    assert codes.count("graph-layer-invalid") == 1
    assert codes.count("graph-layer-missing") == 1
    graph = build_graph(tmp_path)
    paths = layout_paths(graph, list(graph.store.nodes))
    assert paths["1-1"].startswith("01-unlayered/")
    assert paths["3-1"].startswith("01-unlayered/")


def test_same_band_order_back_edge_is_reported_across_subpaths(write, tmp_path):
    nodes = tmp_path / "nodes"
    _w(nodes, 1, "build/x", order=2, links=["2-1"])
    _w(nodes, 2, "build/y", order=1)
    assert "graph-order-back-edge" in _codes(tmp_path)


def test_disconnected_bands_are_top_level_after_connected_ones(write, tmp_path):
    nodes = tmp_path / "nodes"
    _w(nodes, 1, "intent", links=["2-1"])
    _w(nodes, 2, "sink")
    _w(nodes, 3, "zebra")
    _w(nodes, 4, "alpha")
    graph = build_graph(tmp_path)
    paths = layout_paths(graph, list(graph.store.nodes))
    assert paths["1-1"].startswith("00-intent/")
    assert paths["2-1"].startswith("01-sink/")
    assert paths["4-1"].startswith("02-alpha/")
    assert paths["3-1"].startswith("03-zebra/")


def test_group_is_ordinary_metadata_and_warns_in_graph_mode(write, tmp_path):
    nodes = tmp_path / "nodes"
    _w(nodes, 1, "intent", links=["2-1"])
    _w(nodes, 2, "claims/structural", group="ignored")
    graph = build_graph(tmp_path)
    assert _codes(tmp_path).count("graph-group-ignored") == 1
    assert layout_paths(graph, graph_view(graph, "1-1"))["2-1"] == (
        "01-claims/structural/2-1.md"
    )
    assert "group" not in render_graph(graph, graph_view(graph, "1-1"))
    for node in build_graph(EXAMPLES).store.nodes.values():
        assert "group" not in node.meta


def test_link_refuses_band_cycle_and_same_band_order_and_new_accepts_paths(tmp_path):
    api.init_store(tmp_path, graph=True)
    api.new_node(tmp_path, parent="1-1", layer="alpha", fields={"title": "A"})
    api.new_node(tmp_path, parent="2-1", layer="beta", fields={"title": "B"})
    with pytest.raises(BreakdownError, match="layer cycle"):
        api.link(tmp_path, "3-1", "2-1", link_type="supports")
    with pytest.raises(BreakdownError, match="forward within layer"):
        api.link(tmp_path, "2-1", "2-1", link_type="self")

    created = api.new_node(
        tmp_path, parent="1-1", layer="alpha/structural", fields={"title": "Deep"}
    )
    assert parse_document(created.read_text(encoding="utf-8")).meta["layer"] == "alpha/structural"
    with pytest.raises(BreakdownError, match="graph-layer-invalid"):
        api.new_node(tmp_path, parent="1-1", layer="bad//path")


def test_materialization_tree_work_and_exports_use_nested_folders(write, tmp_path):
    root = tmp_path / "store"
    nodes = root / "nodes"
    _fork(nodes, nested=True)
    result = api.work(root, "1-1")
    out = root / "bd_work"
    assert result.symlinks == 6
    assert (out / "01-breakdown" / "sub-a" / "sub-sub" / "INDEX.md").is_file()
    assert api.edit_path(root, "6-1") == (
        out / "01-breakdown" / "sub-a" / "sub-sub" / "6-1.md"
    )

    tree, graph = tmp_path / "tree", tmp_path / "graph"
    api.export_view("tree", root, "1-1", tree)
    api.export_view("graph", root, "1-1", graph)
    for base in (tree, graph):
        assert (base / "01-breakdown" / "sub-a" / "sub-sub" / "6-1.md").is_file()
        assert (base / "01-breakdown" / "sub-a" / "sub-sub" / "INDEX.md").is_file()

    assert main(["--root", str(root), "tree", "1-1"]) == 0
    dot_file = tmp_path / "graph.dot"
    assert main(["--root", str(root), "graph", "--dot", "--out", str(dot_file)]) == 0
    dot = dot_file.read_text(encoding="utf-8")
    assert 'label="layer 1 — breakdown/sub-a"' in dot
    if shutil.which("dot"):
        svg_file = tmp_path / "graph.svg"
        assert main(["--root", str(root), "graph", "--svg", "--out", str(svg_file)]) == 0
        assert "<svg" in svg_file.read_text(encoding="utf-8")


def test_absolute_stage_mode_is_unchanged_and_ignores_group(write, tmp_path):
    nodes = tmp_path / "nodes"
    _w(nodes, 1, "intent", stage=0, links=["2-1", "3-1"])
    _w(nodes, 2, "claims", stage=1, group="structural")
    _w(nodes, 3, "claims", stage=1, group="verification", order=1)
    graph = build_graph(tmp_path)
    assert not graph.relative
    paths = layout_paths(graph, graph_view(graph, "1-1"))
    assert paths["2-1"] == "01-claims/2-1.md"
    assert paths["3-1"] == "01-claims/3-1.md"
    assert "graph-group-ignored" in _codes(tmp_path)
    dot = render_dot(graph, graph_view(graph, "1-1"))
    assert 'label="stage 1 — claims"' in dot
