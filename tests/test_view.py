from __future__ import annotations

import pytest

from bd_tree.api import check, current_ref, default_root, load_view, resolve_ref
from bd_tree.errors import BreakdownError


def _tree(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"])
    write(nodes, 2, contains=["4"])
    write(nodes, 3)
    write(nodes, 4)
    return nodes


def test_view_is_containment_closure(write, tmp_path):
    _tree(write, tmp_path)
    assert set(load_view(tmp_path, "1-1").nodes) == {"1-1", "2-1", "3-1", "4-1"}
    assert set(load_view(tmp_path, "2-1").nodes) == {"2-1", "4-1"}
    assert set(load_view(tmp_path, "4-1").nodes) == {"4-1"}


def test_every_version_declares_its_own_contains(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2, contains=["3"], body="parent v1\n")
    write(nodes, 3)
    write(nodes, 2, version=2, body="no list means leaf\n")
    write(nodes, 2, version=3, contains=[], body="closed\n")

    assert set(load_view(tmp_path, "1-1").nodes) == {"1-1", "2-1", "3-1"}
    versioned = load_view(tmp_path, "2-1")
    assert set(versioned.nodes) == {"2-1", "3-1"}
    assert "3-1" in versioned.nodes
    assert set(load_view(tmp_path, "2-2").nodes) == {"2-2"}
    assert set(load_view(tmp_path, "2-3").nodes) == {"2-3"}
    assert check(tmp_path, "1-1").ok


def test_containment_cycle_is_reported(write, tmp_path):
    write(tmp_path / "nodes", 1, contains=["2"])
    write(tmp_path / "nodes", 2, contains=["1"])
    view = load_view(tmp_path, "1-1")
    assert any(issue.code == "containment-cycle" for issue in view.issues)
    assert any(issue.code == "containment-cycle" for issue in check(tmp_path).errors)


def test_missing_contains_target(write, tmp_path):
    write(tmp_path / "nodes", 1, contains=["9"])
    view = load_view(tmp_path, "1-1")
    assert any(issue.code == "missing-target" for issue in view.issues)


def test_two_parents_is_an_error(write, tmp_path):
    write(tmp_path / "nodes", 1, contains=["2", "3"])
    write(tmp_path / "nodes", 2)
    write(tmp_path / "nodes", 3, contains=["2"])
    result = check(tmp_path)
    assert any(issue.code == "multiple-parents" for issue in result.errors)


def test_unreachable_id_is_a_warning(write, tmp_path):
    write(tmp_path / "nodes", 1, contains=["2"])
    write(tmp_path / "nodes", 2)
    write(tmp_path / "nodes", 3)
    result = check(tmp_path)
    assert any(
        issue.code == "unreachable-node" and issue.node == "3-1"
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
    assert any(issue.code == "view-root-missing" for issue in result.errors)


def test_missing_bare_selector_is_a_navigation_error(write, tmp_path):
    write(tmp_path / "nodes", 1)
    with pytest.raises(BreakdownError, match="not in view"):
        load_view(tmp_path, "9")


def test_linked_subtree_stays_out_of_the_view(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2, links=[{"to": "10", "type": "history"}])
    write(nodes, 10, title="Decisions", contains=["11"])
    write(nodes, 11)
    assert set(load_view(tmp_path, "1-1").nodes) == {"1-1", "2-1"}
    assert check(tmp_path).ok


def test_full_link_target_is_reachable_but_outside_the_view(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2, links=["10"])
    write(nodes, 10, title="Decisions", type="history", contains=["11"])
    write(nodes, 11)
    assert set(load_view(tmp_path, "1-1").nodes) == {"1-1", "2-1"}
    result = check(tmp_path)
    assert result.ok
    assert not any(issue.code == "external-link" for issue in result.issues)


def test_default_root_and_current_ref_follow_the_view(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2)
    write(nodes, 1, version=2, contains=["2-2"])
    write(nodes, 2, version=2)

    assert default_root(tmp_path) == "1-1"
    assert current_ref(tmp_path, 2) == "2-1"
    assert current_ref(tmp_path, 2, "1-2") == "2-2"
    assert resolve_ref(tmp_path, "2", view_ref="1-2") == "2-2"
    assert resolve_ref(tmp_path, "2-1", view_ref="1-2") == "2-1"
    with pytest.raises(BreakdownError, match="not in view"):
        resolve_ref(tmp_path, "2", view_ref="3-1")
