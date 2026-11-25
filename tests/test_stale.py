from __future__ import annotations

import pytest

from bd_tree.api import reconcile, stale
from bd_tree.errors import BreakdownError
from bd_tree.frontmatter import parse_document


def test_stale_then_reconcile_keeps_body(write, tmp_path, pin):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "breaks_down"}, {"to": "3", "type": "breaks_down"}])
    write(nodes, 2, type="claim", layer="claims", body="v1\n")
    path = write(
        nodes,
        3,
        type="claim",
        layer="claims",
        links=[{"to": "2", "type": "serves", "pinned": pin("v1\n")}],
        body="dependent body stays identical\n\n",
    )
    before = parse_document(path.read_text(encoding="utf-8"))
    original_keys = [
        line.split(":", 1)[0]
        for line in before.raw_fm.splitlines()
        if line and not line[0].isspace() and not line.startswith("- ")
    ]
    assert stale(tmp_path, "1-1") == []

    write(nodes, 2, type="claim", layer="claims", body="v2\n")
    edges = stale(tmp_path, "1-1")
    assert len(edges) == 1
    assert edges[0].label == "3-1 -> 2-1 (serves)"
    assert edges[0].state == "stale"

    changes = reconcile(tmp_path, ["3-1"], "1-1")
    assert len(changes) == 1
    assert changes[0].new == pin("v2\n")
    assert stale(tmp_path, "1-1") == []

    after = parse_document(path.read_text(encoding="utf-8"))
    assert after.body == "dependent body stays identical\n\n"
    assert after.meta["links"][0]["pinned"] == pin("v2\n")
    keys = [
        line.split(":", 1)[0]
        for line in after.raw_fm.splitlines()
        if line and not line[0].isspace() and not line.startswith("- ")
    ]
    assert keys == original_keys


def test_untracked_edge_and_reconcile_all(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2, links=[{"to": "1", "type": "supports", "propagates": True}])
    edges = stale(tmp_path, "1-1")
    assert len(edges) == 1
    assert edges[0].state == "untracked"
    changes = reconcile(tmp_path, None, "1-1", all_nodes=True)
    assert len(changes) == 1
    assert stale(tmp_path, "1-1") == []


def test_non_propagating_edges_are_never_stale(write, tmp_path, pin):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "breaks_down"}])
    write(
        nodes,
        2,
        links=[
            {"to": "1", "type": "see_also"},
            {"to": "1", "type": "contradicts"},
        ],
    )
    assert stale(tmp_path, "1-1") == []


def test_propagation_is_declared_not_typed(write, tmp_path, pin):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2, links=[{"to": "1", "type": "depends_on"}])
    assert stale(tmp_path, "1-1") == []

    write(nodes, 2, links=[{"to": "1", "type": "depends_on", "propagates": True}])
    edges = stale(tmp_path, "1-1")
    assert len(edges) == 1
    assert edges[0].state == "untracked"
    reconcile(tmp_path, None, "1-1", all_nodes=True)
    assert stale(tmp_path, "1-1") == []


def test_already_pinned_link_propagates_without_the_flag(write, tmp_path, pin):
    nodes = tmp_path / "nodes"
    write(nodes, 2, body="v1\n")
    write(
        nodes,
        1,
        links=[{"to": "2", "type": "anything", "pinned": pin("v1\n")}],
    )
    assert stale(tmp_path, "1-1") == []
    write(nodes, 2, body="v2\n")
    assert [edge.state for edge in stale(tmp_path, "1-1")] == ["stale"]


def test_reconcile_reaches_a_parent_through_an_undirected_view(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2)
    # 1-1 is a parent of the view anchor but still inside its component.
    assert reconcile(tmp_path, ["1-1"], "2-1") == []


def test_reconcile_ref_outside_view_fails(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2)
    write(nodes, 9)
    with pytest.raises(BreakdownError, match="outside view"):
        reconcile(tmp_path, ["9-1"], "2-1")
