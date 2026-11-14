from __future__ import annotations

from breakdown.api import check, load_view


def _tree(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"])
    write(nodes, 2, contains=["4"])
    write(nodes, 3)
    write(nodes, 4)
    return nodes


def test_view_is_containment_closure(write, tmp_path):
    _tree(write, tmp_path)
    assert set(load_view(tmp_path, "1").nodes) == {"1", "2", "3", "4"}
    assert set(load_view(tmp_path, "2").nodes) == {"2", "4"}
    assert set(load_view(tmp_path, "4").nodes) == {"4"}


def test_version_override_and_inheritance(write, tmp_path):
    _tree(write, tmp_path)
    write(tmp_path / "nodes", 3, version=1, body="child v1\n")
    write(tmp_path / "nodes", 2, version=1, contains=["3-1"], body="parent v1\n")
    write(tmp_path / "nodes", 2, version=2, body="inherit\n")
    write(tmp_path / "nodes", 2, version=3, contains=[], body="closed\n")

    assert set(load_view(tmp_path, "1").nodes) == {"1", "2", "3", "4"}
    versioned = load_view(tmp_path, "2-1")
    assert set(versioned.nodes) == {"2-1", "3-1"}
    assert "3" not in versioned.nodes
    assert set(load_view(tmp_path, "2-2").nodes) == {"2-2", "4"}
    assert set(load_view(tmp_path, "2-3").nodes) == {"2-3"}
    assert check(tmp_path, "1").ok


def test_containment_cycle_is_reported(write, tmp_path):
    write(tmp_path / "nodes", 1, contains=["2"])
    write(tmp_path / "nodes", 2, contains=["1"])
    view = load_view(tmp_path, "1")
    assert any(issue.code == "containment-cycle" for issue in view.issues)
    assert any(issue.code == "containment-cycle" for issue in check(tmp_path).errors)


def test_missing_contains_target(write, tmp_path):
    write(tmp_path / "nodes", 1, contains=["9"])
    view = load_view(tmp_path, "1")
    assert any(issue.code == "missing-target" for issue in view.issues)


def test_two_parents_is_an_error(write, tmp_path):
    write(tmp_path / "nodes", 1, contains=["2", "3"])
    write(tmp_path / "nodes", 2)
    write(tmp_path / "nodes", 3, contains=["2"])
    result = check(tmp_path)
    assert any(issue.code == "multiple-parents" for issue in result.errors)


def test_unreachable_node_is_an_error(write, tmp_path):
    write(tmp_path / "nodes", 1, contains=["2"])
    write(tmp_path / "nodes", 2)
    write(tmp_path / "nodes", 3)
    result = check(tmp_path)
    assert any(
        issue.code == "unreachable" and issue.node == "3" for issue in result.errors
    )


def test_view_root_missing(write, tmp_path):
    write(tmp_path / "nodes", 1)
    assert any(issue.code == "view-root-missing" for issue in load_view(tmp_path, "9").issues)
    result = check(tmp_path, "9")
    assert any(issue.code == "view-root-missing" for issue in result.errors)
