from __future__ import annotations

import pytest

from bd_tree.api import check, current_ref, default_root, load_view, resolve_ref
from bd_tree.errors import BreakdownError


def _tree(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        band="a",
        order=0,
        links=[
            {"to": "2", "type": "breaks_down"},
            {"to": "3", "type": "breaks_down"},
        ],
    )
    write(nodes, 2, band="b", order=0, links=[{"to": "4", "type": "breaks_down"}])
    write(nodes, 3, band="b", order=1)
    write(nodes, 4, band="c", order=0)
    return nodes


def test_view_is_the_whole_connected_component(write, tmp_path):
    _tree(write, tmp_path)
    tree = {"1-1", "2-1", "3-1", "4-1"}
    assert set(load_view(tmp_path, "1-1").nodes) == tree
    assert set(load_view(tmp_path, "2-1").nodes) == tree
    assert set(load_view(tmp_path, "4-1").nodes) == tree


def test_view_distance_is_undirected_bfs(write, tmp_path):
    _tree(write, tmp_path)
    view = load_view(tmp_path, "2-1")
    assert view.distance == {"2-1": 0, "1-1": 1, "4-1": 1, "3-1": 2}


def test_a_multi_parent_node_appears_once_in_the_view(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="a", order=0, links=[{"to": "2", "type": "supports"}])
    write(nodes, 3, band="a", order=1, links=[{"to": "2", "type": "supports"}])
    write(nodes, 2, band="b", order=0)
    view = load_view(tmp_path, "1-1")
    assert list(view.nodes).count("2-1") == 1
    assert set(view.nodes) == {"1-1", "2-1", "3-1"}
    assert check(tmp_path).ok


def test_every_version_declares_its_own_links(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="a", order=0, links=[{"to": "2", "type": "breaks_down"}])
    write(
        nodes,
        2,
        band="b",
        order=0,
        links=[{"to": "3", "type": "breaks_down"}],
        body="parent v1\n",
    )
    write(nodes, 3, band="c", order=0)
    write(nodes, 2, version=2, band="b", order=0, body="no list means leaf\n")
    write(nodes, 2, version=3, band="b", order=0, links=[], body="closed\n")

    connected = {"1-1", "2-1", "3-1"}
    assert set(load_view(tmp_path, "1-1").nodes) == connected
    assert set(load_view(tmp_path, "2-1").nodes) == connected
    assert "3-1" in load_view(tmp_path, "2-1").nodes
    assert set(load_view(tmp_path, "2-2").nodes) == {"2-2"}
    assert set(load_view(tmp_path, "2-3").nodes) == {"2-3"}
    assert check(tmp_path, "1-1").ok


def test_graph_cycle_loads_once_and_is_not_an_error(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="a", order=0, links=[{"to": "2", "type": "x"}])
    write(nodes, 2, band="b", order=0, links=[{"to": "1", "type": "x"}])
    view = load_view(tmp_path, "1-1")
    assert set(view.nodes) == {"1-1", "2-1"}
    assert view.distance == {"1-1": 0, "2-1": 1}
    assert check(tmp_path).ok
    assert not any(issue.code == "graph-cycle" for issue in check(tmp_path).errors)


def test_missing_link_target(write, tmp_path):
    write(tmp_path / "nodes", 1, band="a", order=0, links=[{"to": "9", "type": "x"}])
    assert any(
        issue.code == "graph-dangling-link" for issue in check(tmp_path).errors
    )


def test_two_parents_is_legal(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="a", order=0, links=[{"to": "2", "type": "x"}])
    write(nodes, 3, band="a", order=1, links=[{"to": "2", "type": "x"}])
    write(nodes, 2, band="b", order=0)
    result = check(tmp_path)
    assert result.ok
    assert not any(issue.code == "multiple-parents" for issue in result.issues)


def test_unreachable_id_is_a_warning(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="a", order=0, links=[{"to": "2", "type": "x"}])
    write(nodes, 2, band="b", order=0)
    write(nodes, 3, band="a", order=1)
    result = check(tmp_path)
    assert any(
        issue.code == "graph-orphan" and issue.node == "3-1"
        for issue in result.warnings
    )
    assert result.ok


def test_view_root_missing_for_an_exact_ref(write, tmp_path):
    write(tmp_path / "nodes", 1)
    assert any(
        issue.code == "view-root-missing"
        for issue in load_view(tmp_path, "9-1").issues
    )
    result = check(tmp_path, "9-1")
    assert any(issue.code == "root-ref-missing" for issue in result.errors)


def test_missing_bare_selector_is_a_navigation_error(write, tmp_path):
    write(tmp_path / "nodes", 1)
    with pytest.raises(BreakdownError, match="not in view"):
        load_view(tmp_path, "9")


def test_linked_subtree_is_part_of_the_view(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="a", order=0, links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2, band="b", order=0, links=[{"to": "10", "type": "history"}])
    write(nodes, 10, title="Decisions", band="c", order=0, links=[{"to": "11", "type": "history"}])
    write(nodes, 11, band="d", order=0)
    assert set(load_view(tmp_path, "1-1").nodes) == {"1-1", "2-1", "10-1", "11-1"}
    assert check(tmp_path).ok


def test_full_ref_edge_target_and_its_closure_are_in_the_view(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="a", order=0, links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2, band="b", order=0, links=[{"to": "10-1", "type": "history"}])
    write(nodes, 10, title="Decisions", band="c", order=0, links=[{"to": "11", "type": "history"}])
    write(nodes, 11, band="d", order=0)
    view = load_view(tmp_path, "1-1")
    assert {"2-1", "10-1", "11-1"} <= set(view.nodes)
    assert ("2-1", "10-1", "history") in {
        (edge.source, edge.target, edge.type) for edge in view.edges
    }
    # A full-ref edge is ordinary topology now; it is not an "external link".
    assert not any(issue.code == "external-link" for issue in check(tmp_path).issues)


def test_default_root_and_current_ref_follow_the_view(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="a", order=0, links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2, band="b", order=0)
    write(
        nodes,
        1,
        version=2,
        band="a",
        order=0,
        links=[{"to": "2-2", "type": "breaks_down"}],
    )
    write(nodes, 2, version=2, band="b", order=0)

    assert default_root(tmp_path) == "1-1"
    assert current_ref(tmp_path, 2) == "2-1"
    assert current_ref(tmp_path, 2, "1-2") == "2-2"
    assert resolve_ref(tmp_path, "2", view_ref="1-2") == "2-2"
    assert resolve_ref(tmp_path, "2-1", view_ref="1-2") == "2-1"
    with pytest.raises(BreakdownError, match="not in view"):
        resolve_ref(tmp_path, "2", view_ref="3-1")


def test_neighbors_lists_both_directions_with_kind(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2)
    from bd_tree.loader import load

    store = load(tmp_path)
    assert [(n.ref, n.kind, n.link.type) for n in store.neighbors("1-1")] == [
        ("2-1", "child", "breaks_down")
    ]
    assert [(n.ref, n.kind, n.link.type) for n in store.neighbors("2-1")] == [
        ("1-1", "parent", "breaks_down")
    ]


def test_components_are_one_per_weak_component(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "x"}])
    write(nodes, 2, links=[{"to": "1", "type": "x"}])
    write(nodes, 5)
    from bd_tree.loader import load

    store = load(tmp_path)
    assert store.components() == [["1-1", "2-1"], ["5-1"]]
    assert [node.ref for node in store.topology_roots()] == ["1-1", "5-1"]
    assert store.root_ref == "1-1"


def test_declared_root_still_wins_over_components(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1)
    write(nodes, 5)
    (tmp_path / "ROOT").write_text("5-1\n", encoding="utf-8")
    from bd_tree.loader import load

    store = load(tmp_path)
    assert store.root_ref == "5-1"
    assert load_view(tmp_path, "1-1").distance == {"1-1": 0}
