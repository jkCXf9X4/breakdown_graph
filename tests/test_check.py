from __future__ import annotations

import pytest

from bd_tree.api import check, load, load_view
from bd_tree.errors import BreakdownError
from bd_tree.frontmatter import render_document


def _codes(result):
    return {issue.code for issue in result.issues}


def test_filename_grammar_and_id_mismatch(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1)
    (nodes / "01.md").write_text("---\nid: 1\n---\n", encoding="utf-8")
    (nodes / "2.md").write_text("---\nid: 2\n---\n", encoding="utf-8")
    (nodes / "5-0.md").write_text("---\nid: 5\n---\n", encoding="utf-8")
    meta = {
        "id": 4,
        "type": "intent",
        "layer": "intent",
        "title": "two",
        "summary": "",
        "date": "2026-01-01",
        "status": "current",
    }
    (nodes / "3-1.md").write_text(render_document(meta, "body\n"), encoding="utf-8")
    codes = _codes(check(tmp_path))
    assert "invalid-filename" in codes
    assert "id-filename-mismatch" in codes


def test_version_without_contains_is_a_leaf(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2)
    result = check(tmp_path)
    assert result.ok
    assert "missing-main" not in _codes(result)
    assert load(tmp_path).effective_contains("2-1") == []


def test_dangling_link_and_external_link(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"])
    write(nodes, 2, links=[{"to": "9", "type": "serves"}])
    write(nodes, 3)
    dangling = check(tmp_path)
    assert any(issue.code == "dangling-link" for issue in dangling.errors)

    write(nodes, 2, links=[{"to": "3", "type": "serves"}])
    external = check(tmp_path, "2")
    assert external.ok
    assert any(issue.code == "external-link" for issue in external.warnings)
    assert not any(issue.code == "external-link" for issue in check(tmp_path, "1").warnings)


def test_freshness_warnings(write, tmp_path, pin):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"])
    write(nodes, 2)
    write(nodes, 3, links=[{"to": "2", "type": "serves", "pinned": pin("old\n")}])
    result = check(tmp_path)
    assert any(issue.code == "stale-link" for issue in result.warnings)


def test_home_keys_are_inert_arbitrary_front_matter(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"], home="same/place.md")
    write(nodes, 2, home="same/place.md")
    write(nodes, 3, home="bad/../place.md")
    result = check(tmp_path)
    assert result.ok
    assert not any(
        issue.code in ("bad-home", "duplicate-home") for issue in result.issues
    )


def test_untracked_link_and_oversize_warning(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2, links=[{"to": "1", "type": "supports", "propagates": True}])
    result = check(tmp_path)
    assert any(issue.code == "untracked-link" for issue in result.warnings)

    write(nodes, 2, body="line\n" * 121)
    result = check(tmp_path)
    assert any(issue.code == "oversize" for issue in result.warnings)


def test_arbitrary_fields_are_not_validated(write, tmp_path):
    # `version` and any other key are user metadata now; the filename wins.
    path = write(tmp_path / "nodes", 1)
    text = path.read_text(encoding="utf-8").replace("id: 1\n", "id: 1\nversion: 1\n")
    path.write_text(text, encoding="utf-8")
    assert check(tmp_path).ok


def test_require_field_catches_a_missing_field(write, tmp_path):
    write(tmp_path / "nodes", 1, phase="intent")
    assert check(tmp_path).ok
    result = check(tmp_path, require=["phase", "audience"])
    assert any(issue.code == "missing-field" for issue in result.errors)


def test_size_limits_are_configurable(write, tmp_path):
    write(tmp_path / "nodes", 1, body="x\n" * 10)
    assert check(tmp_path, max_lines=5).warnings
    assert not check(tmp_path, max_lines=50).warnings


def test_per_view_two_parents_is_an_error(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"])
    write(nodes, 2, contains=["4"])
    write(nodes, 3, contains=["4"])
    write(nodes, 4)
    result = check(tmp_path)
    assert any(issue.code == "multiple-parents" for issue in result.errors)


def test_peer_versions_may_be_parents_in_different_views(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2-1"])
    write(nodes, 2, contains=["3-1"])
    write(nodes, 3)
    write(nodes, 1, version=2, contains=["2-2"])
    write(nodes, 2, version=2, contains=["3-1"])
    result = check(tmp_path)
    assert not any(issue.code == "multiple-parents" for issue in result.issues)
    assert result.ok


def test_view_with_two_versions_of_one_id_is_an_error(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2-1", "2-2"])
    write(nodes, 2)
    write(nodes, 2, version=2)
    result = check(tmp_path)
    assert any(issue.code == "duplicate-id" for issue in result.errors)
    assert not result.ok


def test_default_root_is_lowest_id_version(write, tmp_path):
    write(tmp_path / "nodes", 5, contains=["6"])
    write(tmp_path / "nodes", 6)
    result = check(tmp_path)
    assert result.ok
    assert result.view == "5-1"
    assert result.nodes_scanned == 2


def test_default_root_orders_by_id_then_version(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 2, contains=["3"])
    write(nodes, 3)
    write(nodes, 1, version=2)
    result = check(tmp_path)
    assert result.view == "1-2"
    assert not any(
        issue.code == "unreachable-node" and issue.node == "1-2"
        for issue in result.issues
    )
    assert any(
        issue.code == "unreachable-node" and issue.node == "2-1"
        for issue in result.warnings
    )


def test_declared_root_wins_over_lowest_id_version(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2)
    write(nodes, 1, version=4, contains=["2-1"])
    (tmp_path / "ROOT").write_text("1-4\n", encoding="utf-8")
    result = check(tmp_path)
    assert result.ok
    assert result.view == "1-4"


def test_missing_declared_root_is_an_error(write, tmp_path):
    write(tmp_path / "nodes", 1)
    (tmp_path / "ROOT").write_text("1-9\n", encoding="utf-8")
    result = check(tmp_path)
    assert any(issue.code == "root-ref-missing" for issue in result.errors)


def test_invalid_root_file_is_an_error(write, tmp_path):
    write(tmp_path / "nodes", 1)
    (tmp_path / "ROOT").write_text("not-a-ref\n", encoding="utf-8")
    result = check(tmp_path)
    assert any(issue.code == "invalid-root" for issue in result.errors)


def test_bare_root_ref_is_reported(write, tmp_path):
    write(tmp_path / "nodes", 1)
    (tmp_path / "ROOT").write_text("1\n", encoding="utf-8")
    result = check(tmp_path)
    assert any(issue.code == "bare-ref" for issue in result.errors)


def test_non_selected_version_of_a_reachable_id_is_not_an_issue(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2)
    write(nodes, 1, version=3, contains=["4"])
    write(nodes, 4)
    result = check(tmp_path)
    assert result.ok
    assert not any(
        issue.code == "unreachable-node" and issue.node == "1-3"
        for issue in result.issues
    )
    assert any(
        issue.code == "unreachable-node" and issue.node == "4-1"
        for issue in result.warnings
    )


def test_orphan_id_with_no_alternative_still_warns(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2)
    write(nodes, 9)
    result = check(tmp_path)
    assert any(
        issue.code == "unreachable-node" and issue.node == "9-1"
        for issue in result.warnings
    )


def test_link_target_outside_contains_is_reachable(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2, links=[{"to": "10", "type": "history"}])
    write(nodes, 10, title="Decisions", contains=["11"])
    write(nodes, 11)
    result = check(tmp_path)
    assert result.ok
    assert not any(issue.code == "unreachable-node" for issue in result.issues)
    assert not any(issue.code == "external-link" for issue in result.issues)


def test_link_from_an_unreachable_node_rescues_nothing(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2)
    write(nodes, 3, links=[{"to": "4", "type": "supports"}])
    write(nodes, 4)
    result = check(tmp_path)
    unreachable = {
        issue.node for issue in result.warnings if issue.code == "unreachable-node"
    }
    assert {"3-1", "4-1"} <= unreachable


def test_dangling_link_still_errors(write, tmp_path):
    write(tmp_path / "nodes", 1, links=[{"to": "99", "type": "supports"}])
    result = check(tmp_path)
    assert any(issue.code == "dangling-link" for issue in result.errors)


def test_scalar_link_to_a_target_without_type_is_invalid(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=["10"])
    write(nodes, 10)
    result = check(tmp_path)
    assert any(
        issue.code == "invalid-link"
        and "implicit link to '10-1'" in issue.message
        for issue in result.errors
    )


def test_scalar_link_to_a_missing_node_still_dangles(write, tmp_path):
    write(tmp_path / "nodes", 1, links=["99"])
    result = check(tmp_path)
    assert any(issue.code == "dangling-link" for issue in result.errors)
    assert not any(issue.code == "invalid-link" for issue in result.errors)


def test_bare_ref_in_contains_is_an_error_and_blocks_the_view(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], raw_refs=True)
    write(nodes, 2)
    result = check(tmp_path)
    assert any(issue.code == "bare-ref" for issue in result.errors)
    with pytest.raises(BreakdownError, match="bare ref '2'"):
        load_view(tmp_path, "1-1")


def test_bare_ref_in_links_is_an_error_and_blocks_the_view(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=["2"], raw_refs=True)
    write(nodes, 2)
    result = check(tmp_path)
    assert any(issue.code == "bare-ref" for issue in result.errors)
    with pytest.raises(BreakdownError, match="bare ref '2'"):
        load_view(tmp_path, "1-1")


def test_invalid_ref_in_contains_and_links_is_an_error(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["x"], links=["y-z"], raw_refs=True)
    result = check(tmp_path)
    assert any(issue.code == "invalid-ref" for issue in result.errors)
