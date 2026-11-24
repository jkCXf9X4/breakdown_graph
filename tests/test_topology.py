"""One topology: typed links, a link-closure view, and band layout."""

from __future__ import annotations

from bd_tree import api
from bd_tree.cli import main
from bd_tree.frontmatter import parse_document
from bd_tree.graph import build_graph, default_anchor
from bd_tree.loader import load
from bd_tree.navigate import render_find, render_path, render_show


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


# -- model -------------------------------------------------------------------


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


def test_relative_band_store_is_always_the_graph_model(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="a", order=0, links=[{"to": "2", "type": "x"}])
    write(nodes, 2, band="b", order=0)
    store = load(tmp_path)
    assert store.model == "graph"
    assert api.load_view(tmp_path, "1-1").model == "graph"


def test_graph_anchor_uses_stage_order_among_roots(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, title="Late root", stage=2, links=[{"to": "3", "type": "x"}])
    write(nodes, 2, title="Early root", stage=0, links=[{"to": "3", "type": "x"}])
    write(nodes, 3, title="Leaf", stage=3)
    store = load(tmp_path)
    assert [node.ref for node in store.topology_roots()] == ["2-1", "1-1"]
    assert store.root_ref == "2-1"


# -- view --------------------------------------------------------------------


def test_graph_view_is_the_out_link_closure_with_a_shared_node_once(
    write, tmp_path
):
    _graph(write, tmp_path)
    view = api.load_view(tmp_path, "1-1")
    assert view.model == "graph"
    assert set(view.nodes) == {"1-1", "2-1", "3-1", "4-1"}
    assert list(view.nodes).count("4-1") == 1
    edges = {(edge.source, edge.target, edge.type) for edge in view.edges}
    assert edges == {
        ("1-1", "2-1", "breaks_down"),
        ("1-1", "3-1", "breaks_down"),
        ("2-1", "4-1", "supports"),
        ("3-1", "4-1", "supports"),
    }

    # A narrower closure is exactly the nodes reachable from its own root.
    assert set(api.load_view(tmp_path, "2-1").nodes) == {"2-1", "4-1"}


# -- navigation --------------------------------------------------------------


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


def test_graph_cli_views_graph_show_path_and_find(
    write, tmp_path, monkeypatch, capsys
):
    _graph(write, tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["views"]) == 0
    assert capsys.readouterr().out.strip() == "1-1  Root *"
    assert main(["graph"]) == 0
    assert "stage 2 — stage-02" in capsys.readouterr().out
    assert main(["show", "1+2"]) == 0
    assert "4-1" in capsys.readouterr().out
    assert main(["path", "4"]) == 0
    assert "2-1  Left" in capsys.readouterr().out
    assert main(["find", "needle"]) == 0
    assert "4-1" in capsys.readouterr().out


# -- diff and freshness ------------------------------------------------------


def test_graph_diff_compares_link_closures(write, tmp_path):
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


def test_check_reports_a_surviving_contains_key(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="a", order=0, contains=[])
    write(nodes, 2, band="b", order=0)
    result = api.check(tmp_path)
    assert not result.ok
    assert any(issue.code == "contains-removed" for issue in result.errors)
    assert not any(issue.code == "multiple-parents" for issue in result.issues)


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
