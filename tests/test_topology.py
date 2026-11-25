"""One topology: typed links, a weak-component view, and undirected navigation."""

from __future__ import annotations

from bd_tree import api
from bd_tree.cli import main
from bd_tree.frontmatter import render_document
from bd_tree.graph import build_graph, default_anchor
from bd_tree.loader import load
from bd_tree.navigate import render_find, render_path, render_show


def _write_tokens(nodes, node_id, *, title, tokens, body, **fields):
    """One node whose body declares its links directly as bare tokens.

    The cached titles are then generated for the whole store, as the tool
    does: fixtures never hand-write a title cache.
    """
    nodes.mkdir(parents=True, exist_ok=True)
    ref = f"{node_id}-1"
    data = {"id": node_id, "title": title, **fields}
    rows = "".join(f"- {token}\n" for token in tokens)
    text = body if body.endswith("\n") else body + "\n"
    text = text + rows
    (nodes / f"{ref}.md").write_text(
        render_document(data, text), encoding="utf-8", newline=""
    )
    api.retitle(nodes.parent)


def _graph(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(
        nodes,
        1,
        title="Root",
        tokens=["[[2-1, breaks_down]]", "[[3-1, breaks_down]]"],
        body="# Root\n\nThe intent.\n",
    )
    _write_tokens(
        nodes,
        2,
        title="Left",
        tokens=["[[4-1, supports]]"],
        body="left body\n",
    )
    _write_tokens(
        nodes,
        3,
        title="Right",
        tokens=["[[4-1, supports]]"],
        body="right body\n",
    )
    _write_tokens(nodes, 4, title="Claim", tokens=[], body="needle claim body\n")
    return load(tmp_path)


# -- model -------------------------------------------------------------------


def test_graph_model_children_parents_roots_and_anchor(write, tmp_path):
    store = _graph(write, tmp_path)
    assert store.children("1-1") == ["2-1", "3-1"]
    assert store.children("4-1") == []
    assert store.parents("4-1") == ["2-1", "3-1"]
    assert store.parents("1-1") == []
    assert [node.ref for node in store.topology_roots()] == ["1-1"]
    assert store.root_ref == "1-1"
    assert api.load(tmp_path).root_ref == "1-1"


def test_anchor_is_the_lowest_component_member_not_the_stage(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="Late", tokens=["[[3-1, x]]"], body="b\n", stage=2)
    _write_tokens(nodes, 2, title="Early", tokens=["[[3-1, x]]"], body="b\n", stage=0)
    _write_tokens(nodes, 3, title="Leaf", tokens=[], body="b\n", stage=3)
    store = load(tmp_path)
    assert [node.ref for node in store.topology_roots()] == ["1-1"]
    assert store.root_ref == "1-1"


def test_default_anchor_agrees_with_store_root(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="Late", tokens=["[[3-1, x]]"], body="b\n", stage=2)
    _write_tokens(nodes, 2, title="Early", tokens=["[[3-1, x]]"], body="b\n", stage=0)
    _write_tokens(nodes, 3, title="Leaf", tokens=[], body="b\n", stage=3)
    store = load(tmp_path)
    graph = build_graph(store)
    assert store.root_ref == "1-1"
    assert default_anchor(graph) == store.root_ref


def test_graph_roots_lists_one_representative_per_component(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="One", tokens=["[[2-1, x]]"], body="b\n")
    _write_tokens(nodes, 2, title="Two", tokens=[], body="b\n")
    _write_tokens(nodes, 7, title="Seven", tokens=[], body="b\n")
    _write_tokens(nodes, 5, title="Five", tokens=["[[6-1, x]]"], body="b\n")
    _write_tokens(nodes, 6, title="Six", tokens=[], body="b\n")
    graph = build_graph(tmp_path)
    assert graph.roots == ["1-1", "5-1", "7-1"]
    assert graph.components == [["1-1", "2-1"], ["5-1", "6-1"], ["7-1"]]


# -- view --------------------------------------------------------------------


def test_graph_view_is_the_weak_component_with_distances(write, tmp_path):
    _graph(write, tmp_path)
    view = api.load_view(tmp_path, "1-1")
    assert set(view.nodes) == {"1-1", "2-1", "3-1", "4-1"}
    assert list(view.nodes).count("4-1") == 1
    assert view.distance == {"1-1": 0, "2-1": 1, "3-1": 1, "4-1": 2}
    edges = {(edge.source, edge.target, edge.type) for edge in view.edges}
    assert edges == {
        ("1-1", "2-1", "breaks_down"),
        ("1-1", "3-1", "breaks_down"),
        ("2-1", "4-1", "supports"),
        ("3-1", "4-1", "supports"),
    }

    # The anchor is a focus, not a filter: a non-root anchor sees the component.
    assert set(api.load_view(tmp_path, "2-1").nodes) == {
        "1-1",
        "2-1",
        "3-1",
        "4-1",
    }


# -- navigation --------------------------------------------------------------


def test_graph_show_walks_rings(write, tmp_path):
    store = _graph(write, tmp_path)
    out = render_show(store, "1-1", depth=2)
    assert "## 2-1  Left" in out
    assert "## 4-1  Claim" in out
    assert "## 3-1  Right" in out


def test_graph_path_is_the_shortest_undirected_chain(write, tmp_path):
    store = _graph(write, tmp_path)
    assert render_path(store, "4-1") == (
        "1-1  Root\n→ 2-1  Left\n→ 4-1  Claim"
    )


def test_graph_find_scopes_to_the_component(write, tmp_path):
    store = _graph(write, tmp_path)
    out = render_find(store, "needle")
    assert "4-1" in out
    assert "1-1 > 2-1 > 4-1" in out


def test_graph_show_links_labels_direction(write, tmp_path):
    store = _graph(write, tmp_path)
    out = render_show(store, "1-1", depth=1, links=True)
    assert "links:" in out
    assert "- 1-1 → 2-1  Left  (breaks_down)" in out
    assert "- 2-1 ← 1-1  Root  (breaks_down)" in out


def test_graph_cli_views_graph_show_path_and_find(
    write, tmp_path, monkeypatch, capsys
):
    _graph(write, tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["views"]) == 0
    views = capsys.readouterr().out
    assert "1-1" in views
    assert main(["graph"]) == 0
    assert "## 0 — 1-1" in capsys.readouterr().out
    assert main(["show", "1+2"]) == 0
    assert "4-1" in capsys.readouterr().out
    assert main(["path", "4"]) == 0
    path = capsys.readouterr().out
    assert "2-1" in path and "4-1" in path
    assert main(["find", "needle"]) == 0
    assert "4-1" in capsys.readouterr().out


# -- check -------------------------------------------------------------------


def test_graph_check_is_clean_on_a_connected_store(write, tmp_path):
    _graph(write, tmp_path)
    result = api.check(tmp_path)
    assert result.ok
    assert result.warnings == []
    assert result.nodes_scanned == 4
    assert result.view == "1-1"


def test_graph_check_accepts_a_cycle(write, tmp_path, monkeypatch, capsys):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="One", tokens=["[[2-1, x]]"], body="b\n")
    _write_tokens(nodes, 2, title="Two", tokens=["[[1-1, x]]"], body="b\n")
    result = api.check(tmp_path)
    assert result.ok
    monkeypatch.chdir(tmp_path)
    assert main(["check"]) == 0
    assert "0 errors, 0 warnings" in capsys.readouterr().out


def test_graph_check_accepts_a_back_edge(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="One", tokens=["[[2-1, x]]"], body="b\n", stage=1)
    _write_tokens(nodes, 2, title="Two", tokens=[], body="b\n", stage=1)
    result = api.check(tmp_path)
    assert result.ok
    assert not any(
        issue.code.startswith(("graph-back-edge", "graph-stage", "graph-order"))
        for issue in result.issues
    )


def test_check_reports_a_surviving_contains_key(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="One", tokens=[], body="b\n", contains=[])
    _write_tokens(nodes, 2, title="Two", tokens=[], body="b\n")
    result = api.check(tmp_path)
    assert not result.ok
    assert any(issue.code == "contains-removed" for issue in result.errors)
