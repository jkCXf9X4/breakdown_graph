from __future__ import annotations

from bd_tree.api import check
from bd_tree.frontmatter import render_document


def _codes(result):
    return {issue.code for issue in result.issues}


def test_filename_grammar_and_id_mismatch(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1)
    (nodes / "01.md").write_text("---\nid: 1\n---\n", encoding="utf-8")
    meta = {
        "id": 3,
        "type": "intent",
        "layer": "intent",
        "title": "two",
        "summary": "",
        "date": "2026-01-01",
        "status": "current",
    }
    (nodes / "2.md").write_text(render_document(meta, "body\n"), encoding="utf-8")
    codes = _codes(check(tmp_path))
    assert "invalid-filename" in codes
    assert "id-filename-mismatch" in codes


def test_missing_main_for_version(write, tmp_path):
    write(tmp_path / "nodes", 1)
    write(tmp_path / "nodes", 3, version=1)
    codes = _codes(check(tmp_path))
    assert "missing-main" in codes


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


def test_main_and_version_may_be_parents_in_different_views(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2, contains=["3"])
    write(nodes, 3)
    write(nodes, 2, version=1, contains=["3"])
    result = check(tmp_path)
    assert not any(issue.code == "multiple-parents" for issue in result.issues)
    assert result.ok


def test_default_root_ref_is_lowest_main(write, tmp_path):
    write(tmp_path / "nodes", 5, contains=["6"])
    write(tmp_path / "nodes", 6)
    result = check(tmp_path)
    assert result.ok
    assert result.nodes_scanned == 2


def test_declared_root_wins_over_lowest_main(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2)
    write(nodes, 1, version=4, contains=["2"])
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


def test_alternative_branch_is_reachable_through_its_id(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2)
    write(nodes, 1, version=3, contains=["4"])
    write(nodes, 4)
    result = check(tmp_path)
    assert result.ok


def test_orphan_id_with_no_alternative_still_errors(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2)
    write(nodes, 1, version=3, contains=["4"])
    write(nodes, 4)
    write(nodes, 9)
    result = check(tmp_path)
    assert any(
        issue.code == "unreachable" and issue.node == "9" for issue in result.errors
    )


def test_link_target_outside_contains_is_reachable(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2, links=[{"to": "10", "type": "history"}])
    write(nodes, 10, title="Decisions", contains=["11"])
    write(nodes, 11)
    result = check(tmp_path)
    assert result.ok
    assert not any(issue.code == "unreachable" for issue in result.issues)
    assert not any(issue.code == "external-link" for issue in result.issues)


def test_link_from_an_unreachable_node_rescues_nothing(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2)
    write(nodes, 3, links=[{"to": "4", "type": "supports"}])
    write(nodes, 4)
    result = check(tmp_path)
    unreachable = {
        issue.node for issue in result.errors if issue.code == "unreachable"
    }
    assert {"3", "4"} <= unreachable


def test_dangling_link_still_errors(write, tmp_path):
    write(tmp_path / "nodes", 1, links=[{"to": "99", "type": "supports"}])
    result = check(tmp_path)
    assert any(issue.code == "dangling-link" for issue in result.errors)


def test_bare_link_to_a_target_without_type_is_invalid(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=["10"])
    write(nodes, 10)
    result = check(tmp_path)
    assert any(
        issue.code == "invalid-link"
        and "implicit link to '10'" in issue.message
        for issue in result.errors
    )


def test_bare_link_to_a_missing_node_still_dangles(write, tmp_path):
    write(tmp_path / "nodes", 1, links=["99"])
    result = check(tmp_path)
    assert any(issue.code == "dangling-link" for issue in result.errors)
    assert not any(issue.code == "invalid-link" for issue in result.errors)
