"""Pluggable topology: graph stores follow links, containment stays a tree."""

from __future__ import annotations

from bd_tree import api
from bd_tree.cli import main
from bd_tree.frontmatter import parse_document
from bd_tree.graph import build_graph, default_anchor
from bd_tree.loader import load
from bd_tree.navigate import render_find, render_path, render_show, render_tree


def _graph(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        title="Root",
        stage=0,
        links=[
            {"to": "2", "type": "breaks_down"},
            {"to": "3", "type": "breaks_down"},
        ],
    )
    write(nodes, 2, title="Left", stage=1, links=[{"to": "4", "type": "supports"}])
    write(nodes, 3, title="Right", stage=1, links=[{"to": "4", "type": "supports"}])
    write(nodes, 4, title="Claim", stage=2, body="needle claim body\n")
    return load(tmp_path)


def _containment(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, title="Root", contains=["2", "3"])
    write(nodes, 2, title="Left", contains=["4"])
    write(nodes, 3, title="Right")
    write(nodes, 4, title="Leaf")
    return load(tmp_path)


# -- model seam --------------------------------------------------------------


def test_graph_model_children_parents_roots_and_anchor(write, tmp_path):
    store = _graph(write, tmp_path)
    assert store.model == "graph"
    assert store.children("1-1") == ["2-1", "3-1"]
    assert store.children("4-1") == []
    assert store.parents("4-1") == ["2-1", "3-1"]
    assert store.parents("1-1") == []
    assert [node.ref for node in store.topology_roots()] == ["1-1"]
    assert store.root_ref == "1-1"
    assert api.load(tmp_path).root_ref == "1-1"


def test_containment_model_is_unchanged(write, tmp_path):
    store = _containment(write, tmp_path)
    assert store.model == "containment"
    assert store.children("1-1") == ["2-1", "3-1"]
    assert store.parents("4-1") == ["2-1"]
    assert [node.ref for node in store.topology_roots()] == ["1-1"]
    assert store.root_ref == "1-1"


def test_graph_anchor_uses_stage_order_among_roots(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, title="Late root", stage=2, links=[{"to": "3", "type": "x"}])
    write(nodes, 2, title="Early root", stage=0, links=[{"to": "3", "type": "x"}])
    write(nodes, 3, title="Leaf", stage=3)
    store = load(tmp_path)
    assert [node.ref for node in store.topology_roots()] == ["2-1", "1-1"]
    assert store.root_ref == "2-1"


# -- view --------------------------------------------------------------------


def test_graph_view_includes_two_parent_node_once_and_keeps_both_edges(
    write, tmp_path
):
    _graph(write, tmp_path)
    view = api.load_view(tmp_path, "1-1")
    assert view.model == "graph"
    assert set(view.nodes) == {"1-1", "2-1", "3-1", "4-1"}
    assert list(view.nodes).count("4-1") == 1
    edges = {(edge.source, edge.target, edge.type) for edge in view.edges}
    assert ("2-1", "4-1", "supports") in edges
    assert ("3-1", "4-1", "supports") in edges
    assert not any(
        issue.code in {"multiple-parents", "duplicate-id", "external-link"}
        for issue in view.issues
    )


# -- navigation --------------------------------------------------------------


def test_graph_tree_renders_stage_bands(write, tmp_path):
    store = _graph(write, tmp_path)
    out = render_tree(store, "1-1")
    assert "stage 0 — stage-00" in out
    assert "stage 1 — stage-01" in out
    assert "stage 2 — stage-02" in out
    assert "[4-1] Claim" in out
    assert "← in: 2-1 (supports), 3-1 (supports)" in out


def test_graph_tree_renders_layer_subpath_headings(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        title="Root",
        layer="intent",
        links=[
            {"to": "2", "type": "breaks_down"},
            {"to": "3", "type": "breaks_down"},
        ],
    )
    write(nodes, 2, title="Left", layer="build/left")
    write(nodes, 3, title="Right", layer="build/right")
    store = load(tmp_path)
    out = render_tree(store, "1-1")
    assert "  left/" in out
    assert "  right/" in out
    assert out.index("  left/") < out.index("[2-1] Left")
    assert out.index("[2-1] Left") < out.index("  right/") < out.index("[3-1] Right")


def test_containment_store_ignores_group_for_placement(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2, group="structural")
    out = tmp_path / "tree"
    result = api.export_view("tree", tmp_path, "1-1", out)
    assert result.nodes == 2
    assert (out / "2-1-title-of-2-1.md").is_file()
    assert not any("structural" in path.parts for path in out.rglob("*"))
    assert api.check(tmp_path).ok


def test_containment_tree_output_is_unchanged(write, tmp_path):
    store = _containment(write, tmp_path)
    assert render_tree(store, "1-1") == (
        "1-1 Root\n"
        "+- 2-1 Left\n"
        "|  `- 4-1 Leaf\n"
        "`- 3-1 Right"
    )


def test_graph_show_follows_link_hops(write, tmp_path):
    store = _graph(write, tmp_path)
    out = render_show(store, "1-1", depth=2)
    assert "## 2-1  Left" in out
    assert "### 4-1  Claim" in out
    assert "## 3-1  Right" in out


def test_graph_path_chooses_the_first_parent_deterministically(write, tmp_path):
    store = _graph(write, tmp_path)
    assert render_path(store, "4-1") == "1-1  Root\n2-1  Left\n4-1  Claim"


def test_graph_find_scopes_to_the_link_closure(write, tmp_path):
    store = _graph(write, tmp_path)
    out = render_find(store, "needle")
    assert "4-1" in out
    assert "1-1 > 2-1 > 4-1" in out


def test_graph_cli_views_tree_show_path_and_find(
    write, tmp_path, monkeypatch, capsys
):
    _graph(write, tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["views"]) == 0
    assert capsys.readouterr().out.strip() == "1-1  Root *"
    assert main(["tree"]) == 0
    assert "stage 2 — stage-02" in capsys.readouterr().out
    assert main(["show", "1+2"]) == 0
    assert "4-1" in capsys.readouterr().out
    assert main(["path", "4"]) == 0
    assert "2-1  Left" in capsys.readouterr().out
    assert main(["find", "needle"]) == 0
    assert "4-1" in capsys.readouterr().out


# -- diff and freshness ------------------------------------------------------


def test_graph_diff_compares_dispatched_closures(write, tmp_path):
    _graph(write, tmp_path)
    states = {entry.id: entry.state for entry in api.diff(tmp_path, "1", "2")}
    assert states == {1: "only-left", 2: "same", 3: "only-left", 4: "same"}


def test_graph_stale_reads_link_edges(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        stage=0,
        links=[{"to": "2", "type": "serves", "propagates": True}],
    )
    write(nodes, 2, stage=1)
    edges = api.stale(tmp_path)
    assert [(edge.source, edge.target, edge.state) for edge in edges] == [
        ("1-1", "2-1", "untracked")
    ]


# -- check -------------------------------------------------------------------


def test_graph_check_is_clean_on_a_forward_example(write, tmp_path):
    _graph(write, tmp_path)
    result = api.check(tmp_path)
    assert result.ok
    assert result.warnings == []
    assert result.nodes_scanned == 4
    assert result.view == "1-1"


def test_graph_check_reports_a_back_edge_and_exits_nonzero(
    write, tmp_path, monkeypatch, capsys
):
    nodes = tmp_path / "nodes"
    write(nodes, 1, stage=1, links=[{"to": "2", "type": "x"}])
    write(nodes, 2, stage=1)
    result = api.check(tmp_path)
    assert not result.ok
    assert any(issue.code == "graph-back-edge" for issue in result.errors)
    monkeypatch.chdir(tmp_path)
    assert main(["check"]) == 1


def test_graph_check_reports_a_cycle(write, tmp_path, monkeypatch, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, stage=0, links=[{"to": "2", "type": "x"}])
    write(nodes, 2, stage=1, links=[{"to": "1", "type": "x"}])
    result = api.check(tmp_path)
    assert not result.ok
    assert any(issue.code == "graph-cycle" for issue in result.errors)
    monkeypatch.chdir(tmp_path)
    assert main(["check"]) == 1
    assert "graph cycle:" in capsys.readouterr().out


def test_containment_check_still_reports_tree_rules(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"])
    write(nodes, 2)
    write(nodes, 3, contains=["2"])
    result = api.check(tmp_path)
    assert any(issue.code == "multiple-parents" for issue in result.errors)
    assert not any(
        issue.code.startswith("graph-") for issue in result.issues
    )


# -- materialization ---------------------------------------------------------


def test_graph_work_materializes_stage_bands_and_limits_by_link_hops(
    write, tmp_path, monkeypatch, capsys
):
    _graph(write, tmp_path)
    monkeypatch.chdir(tmp_path)

    assert main(["work", "1-1"]) == 0
    out = tmp_path / "bd_work"
    assert {path.name for path in out.iterdir() if path.is_dir()} == {
        "00-stage-00",
        "01-stage-01",
        "02-stage-02",
    }
    assert (out / "02-stage-02" / "4-1-claim.md").is_symlink()
    assert (out / "00-stage-00" / "INDEX.md").is_file()
    assert main(["work", "--status"]) == 0
    assert "4 ok, 0 not ok" in capsys.readouterr().out

    assert main(["work", "1-1+1"]) == 0
    assert {path.name for path in out.iterdir() if path.is_dir()} == {
        "00-stage-00",
        "01-stage-01",
    }
    assert main(["work", "--status"]) == 0
    assert "3 ok, 0 not ok" in capsys.readouterr().out


# -- mode seam and link footer ------------------------------------------------


def test_stage_only_store_is_detected_as_a_graph(write, tmp_path):
    write(tmp_path / "nodes", 1, stage=0)
    store = load(tmp_path)
    assert store.model == "graph"
    assert store.root_ref == "1-1"
    assert api.check(tmp_path).ok


def test_default_anchor_agrees_with_store_root_when_ids_and_stages_disagree(
    write, tmp_path
):
    nodes = tmp_path / "nodes"
    write(nodes, 1, title="Late root", stage=2, links=[{"to": "3", "type": "x"}])
    write(nodes, 2, title="Early root", stage=0, links=[{"to": "3", "type": "x"}])
    write(nodes, 3, title="Leaf", stage=3)
    store = load(tmp_path)
    graph = build_graph(store)
    assert store.root_ref == "2-1"
    assert default_anchor(graph) == store.root_ref == "2-1"


def test_graph_show_links_lists_authored_out_and_derived_in(write, tmp_path):
    store = _graph(write, tmp_path)
    out = render_show(store, "1-1", depth=1, links=True)
    assert "links:" in out
    assert "- 1-1 -> 2-1  Left  (breaks_down)" in out
    assert "- 2-1 <- 1-1  Root  (breaks_down)  [derived]" in out


def test_graph_reconcile_pins_a_propagating_edge(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        stage=0,
        links=[{"to": "2", "type": "serves", "propagates": True}],
    )
    write(nodes, 2, stage=1, body="old body\n")
    assert api.stale(tmp_path)[0].state == "untracked"

    changes = api.reconcile(tmp_path, refs=["1-1"])
    assert len(changes) == 1
    raw = parse_document((nodes / "1-1.md").read_text(encoding="utf-8")).meta[
        "links"
    ][0]
    assert raw["pinned"] == changes[0].new
    assert api.stale(tmp_path) == []

    write(nodes, 2, stage=1, body="changed body\n")
    assert api.stale(tmp_path)[0].state == "stale"
    api.reconcile(tmp_path, refs=["1-1"])
    assert api.stale(tmp_path) == []
