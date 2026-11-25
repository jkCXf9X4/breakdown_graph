from __future__ import annotations

import pytest

from bdg.api import load, reconcile, stale
from bdg.cli import main
from bdg.errors import BreakdownError
from bdg.frontmatter import parse_document
from conftest import add_token, set_freshness


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

    dependent_before = parse_document(path.read_text(encoding="utf-8"))
    dependent_body_before = dependent_before.body

    changes = reconcile(tmp_path, ["3-1"], "1-1")
    assert len(changes) == 1
    assert changes[0].new == pin("v2\n")
    assert stale(tmp_path, "1-1") == []

    after = parse_document(path.read_text(encoding="utf-8"))
    # The dependent's body bytes are identical through reconciliation.
    assert after.body == dependent_body_before
    # Reconciliation re-pins through the top-level freshness map.
    assert after.meta["freshness"]["2-1"]["pinned"] == pin("v2\n")
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


def test_pins_compare_body_hashes_not_titles(write, tmp_path, pin):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2, body="v1\n")
    write(nodes, 3, links=[{"to": "2", "type": "serves"}])
    target_hash = load(tmp_path).nodes["2-1"].body_hash
    set_freshness(nodes, "3-1", {"2-1": {"pinned": target_hash}})
    assert stale(tmp_path, "1-1") == []

    # A front-matter title change does not touch the target's body hash.
    write(nodes, 2, title="Renamed", body="v1\n")
    assert stale(tmp_path, "1-1") == []


def test_target_hash_ignores_token_text(write, tmp_path, pin):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2, links=[{"to": "1", "type": "see_also"}], body="v1\n")
    write(nodes, 3, links=[{"to": "2", "type": "serves"}])
    target_hash = load(tmp_path).nodes["2-1"].body_hash
    set_freshness(nodes, "3-1", {"2-1": {"pinned": target_hash}})
    assert stale(tmp_path, "1-1") == []

    # Token text is stripped from body_hash: retitling a token in place
    # does not make dependents stale.
    write(
        nodes,
        2,
        links=[{"to": "1", "type": "see_also", "title": "Renamed"}],
        body="v1\n",
    )
    assert stale(tmp_path, "1-1") == []


def test_target_hash_ignores_appended_tokens(write, tmp_path, pin):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2, body="v1\n")
    write(nodes, 3, links=[{"to": "2", "type": "serves"}])
    target_hash = load(tmp_path).nodes["2-1"].body_hash
    set_freshness(nodes, "3-1", {"2-1": {"pinned": target_hash}})
    assert stale(tmp_path, "1-1") == []

    # An appended token in the target's Links section is stripped from the
    # target's body hash, so the dependent stays fresh.
    add_token(nodes, "2-1", "[[3-1, supports]]")
    assert stale(tmp_path, "1-1") == []


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


def _untracked_store(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2, links=[{"to": "1-1", "type": "supports", "propagates": True}])
    return nodes


def test_stale_fix_with_an_explicit_ref(write, tmp_path, capsys):
    _untracked_store(write, tmp_path)
    assert [edge.state for edge in stale(tmp_path, "1-1")] == ["untracked"]

    assert main(["stale", "2-1", "--fix", "--root", str(tmp_path)]) == 0
    assert "1 pins rewritten" in capsys.readouterr().out
    assert stale(tmp_path, "1-1") == []


def test_stale_fix_all(write, tmp_path, capsys):
    _untracked_store(write, tmp_path)
    assert len(stale(tmp_path, "1-1")) == 1

    assert main(["stale", "--all", "--fix", "--root", str(tmp_path)]) == 0
    assert "1 pins rewritten" in capsys.readouterr().out
    assert stale(tmp_path, "1-1") == []


def test_stale_fix_requires_a_ref_or_all(write, tmp_path, capsys):
    _untracked_store(write, tmp_path)

    assert main(["stale", "--fix", "--root", str(tmp_path)]) == 2
    assert "give one or more REFs or --all" in capsys.readouterr().err
