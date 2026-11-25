"""Symmetric masters derive a read-only peer; they no longer gate membership."""

from __future__ import annotations

import pytest

from bd_tree import api
from bd_tree.cli import main
from bd_tree.errors import BreakdownError
from bd_tree.frontmatter import parse_document, rewrite_links
from bd_tree.graph import build_graph, render_in, render_out
from bd_tree.loader import load


def _pair(write, tmp_path, *, inverse: str | None = "verified_by", **extra):
    nodes = tmp_path / "nodes"
    link = {"to": "2", "type": "verifies", "symmetric": True}
    if inverse is not None:
        link["inverse"] = inverse
    link.update(extra)
    write(nodes, 1, band="root", links=[link])
    write(nodes, 2, band="claims")
    return nodes


def test_symmetric_master_parses_and_keeps_extra_link_keys(write, tmp_path):
    nodes = _pair(write, tmp_path, weight=3)
    link = load(tmp_path).nodes["1-1"].links[0]
    assert link.symmetric is True
    assert link.inverse == "verified_by"
    assert link.raw["weight"] == 3

    document = parse_document((nodes / "1-1.md").read_text(encoding="utf-8"))
    rewritten = parse_document(
        "---\n" + rewrite_links(document.raw_fm, document.meta["links"]) + "---\n"
    )
    assert rewritten.meta["links"] == [
        {
            "to": "2-1",
            "type": "verifies",
            "symmetric": True,
            "inverse": "verified_by",
            "weight": 3,
        }
    ]


def test_loader_reports_invalid_symmetric_and_inverse(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        band="root",
        links=[
            {"to": "2", "type": "x", "symmetric": "maybe"},
            {"to": "3", "type": "y", "inverse": "back"},
        ],
    )
    write(nodes, 2, band="claims")
    write(nodes, 3, band="claims")
    codes = {issue.code for issue in api.load(tmp_path).issues}
    assert "invalid-symmetric" in codes
    assert "inverse-without-symmetric" in codes


def test_symmetric_master_joins_the_component_as_a_peer(write, tmp_path):
    _pair(write, tmp_path)
    store = load(tmp_path)

    assert store.children("1-1") == []
    assert store.children("2-1") == []
    assert store.derived_links("1-1") == []
    derived = store.derived_links("2-1")
    assert [(edge.source, edge.target, edge.type, edge.origin) for edge in derived] == [
        ("2-1", "1-1", "verified_by", "derived")
    ]
    assert derived[0].symmetric is True

    assert store.node_edges("2-1") == []
    assert [edge.origin for edge in store.node_edges("2-1", include_derived=True)] == [
        "derived"
    ]
    master = store.node_edges("1-1")
    assert [edge.origin for edge in master] == ["link"]
    assert master[0].symmetric is True
    assert store.node_edges("1-1", include_derived=True) == master

    view = api.load_view(tmp_path, "1-1")
    assert set(view.nodes) == {"1-1", "2-1"}
    assert view.distance == {"1-1": 0, "2-1": 1}
    # The authored master is in the view; the derived opposite is not a second edge.
    assert [
        (edge.source, edge.target, edge.type, edge.origin) for edge in view.edges
    ] == [("1-1", "2-1", "verifies", "link")]

    assert [
        (neighbor.ref, neighbor.kind, neighbor.link.type)
        for neighbor in store.neighbors("1-1")
    ] == [("2-1", "peer", "verifies")]
    assert [
        (neighbor.ref, neighbor.kind, neighbor.link.type)
        for neighbor in store.neighbors("2-1")
    ] == [("1-1", "peer", "verifies")]


def test_derived_opposite_reuses_the_master_type_without_inverse(write, tmp_path):
    _pair(write, tmp_path, inverse=None)
    derived = load(tmp_path).derived_links("2-1")
    assert [edge.type for edge in derived] == ["verifies"]


def test_out_and_in_mark_master_and_derived(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        band="root",
        links=[
            {
                "to": "2",
                "type": "verifies",
                "symmetric": True,
                "inverse": "verified_by",
            }
        ],
    )
    write(
        nodes,
        2,
        band="claims",
        links=[
            {
                "to": "3",
                "type": "supports",
                "symmetric": True,
                "inverse": "supported_by",
            }
        ],
    )
    write(nodes, 3, band="claims", order=1)
    graph = build_graph(tmp_path)

    assert render_out(graph, "2-1").splitlines() == [
        "2-1 -> 3-1 (supports, symmetric)",
        "2-1 -> 1-1 (verified_by)  [derived]",
    ]
    assert "1-1 -> 2-1 (verifies)  [derived]" in render_in(graph, "2-1")


def test_link_cli_requires_symmetric_before_inverse(write, tmp_path, monkeypatch, capsys):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        band="root",
        links=[{"to": "2", "type": "breaks_down"}],
    )
    write(nodes, 2, band="claims")
    monkeypatch.chdir(tmp_path)

    assert (
        main(["link", "1", "2", "--type", "realizes", "--inverse", "realized_by"])
        == 2
    )
    assert "requires --symmetric" in capsys.readouterr().err
    with pytest.raises(BreakdownError, match="requires --symmetric"):
        api.link(tmp_path, "1", "2", link_type="realizes", inverse="realized_by")

    assert (
        main(
            [
                "link",
                "1",
                "2",
                "--type",
                "realizes",
                "--symmetric",
                "--inverse",
                "realized_by",
            ]
        )
        == 0
    )
    link = next(
        item for item in load(tmp_path).nodes["1-1"].links if item.type == "realizes"
    )
    assert link.symmetric is True and link.inverse == "realized_by"
