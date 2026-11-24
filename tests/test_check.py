from __future__ import annotations

from bd_tree.api import check, load, load_view
from bd_tree.frontmatter import render_document


def _codes(result):
    return {issue.code for issue in result.issues}


def test_filename_grammar_and_id_mismatch(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="root")
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
        "band": "claims",
    }
    (nodes / "3-1.md").write_text(render_document(meta, "body\n"), encoding="utf-8")
    codes = _codes(check(tmp_path))
    assert "invalid-filename" in codes
    assert "id-filename-mismatch" in codes


def test_a_node_without_links_is_a_leaf(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="root", links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2, band="claims")
    result = check(tmp_path)
    assert result.ok
    assert load(tmp_path).children("2-1") == []


def test_dangling_link_is_an_error(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="root", links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2, band="claims", links=[{"to": "9", "type": "serves"}])
    result = check(tmp_path)
    assert any(issue.code == "graph-dangling-link" for issue in result.errors)


def test_freshness_warnings(write, tmp_path, pin):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        band="root",
        links=[
            {"to": "2", "type": "breaks_down"},
            {"to": "3", "type": "breaks_down"},
        ],
    )
    write(nodes, 2, band="claims")
    write(
        nodes,
        3,
        band="evidence",
        links=[{"to": "2", "type": "serves", "pinned": pin("old\n")}],
    )
    result = check(tmp_path)
    assert any(issue.code == "stale-link" for issue in result.warnings)


def test_home_keys_are_inert_arbitrary_front_matter(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        band="root",
        home="same/place.md",
        links=[
            {"to": "2", "type": "breaks_down"},
            {"to": "3", "type": "breaks_down"},
        ],
    )
    write(nodes, 2, band="claims", home="same/place.md")
    write(nodes, 3, band="evidence", home="bad/../place.md")
    result = check(tmp_path)
    assert result.ok
    assert not any(
        issue.code in ("bad-home", "duplicate-home") for issue in result.issues
    )


def test_untracked_link_and_oversize_warning(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="root", links=[{"to": "2", "type": "breaks_down"}])
    write(
        nodes,
        2,
        band="claims",
        links=[{"to": "3", "type": "supports", "propagates": True}],
    )
    write(nodes, 3, band="evidence")
    result = check(tmp_path)
    assert any(issue.code == "untracked-link" for issue in result.warnings)

    write(
        nodes,
        2,
        band="claims",
        body="line\n" * 121,
        links=[{"to": "3", "type": "supports", "propagates": True}],
    )
    result = check(tmp_path)
    assert any(issue.code == "oversize" for issue in result.warnings)


def test_arbitrary_fields_are_not_validated(write, tmp_path):
    # `version` and any other key are user metadata now; the filename wins.
    path = write(tmp_path / "nodes", 1, band="root")
    text = path.read_text(encoding="utf-8").replace("id: 1\n", "id: 1\nversion: 1\n")
    path.write_text(text, encoding="utf-8")
    assert check(tmp_path).ok


def test_require_field_catches_a_missing_field(write, tmp_path):
    write(tmp_path / "nodes", 1, band="root", phase="intent")
    assert check(tmp_path).ok
    result = check(tmp_path, require=["phase", "audience"])
    assert any(issue.code == "missing-field" for issue in result.errors)


def test_size_limits_are_configurable(write, tmp_path):
    write(tmp_path / "nodes", 1, band="root", body="x\n" * 10)
    assert check(tmp_path, max_lines=5).warnings
    assert not check(tmp_path, max_lines=50).warnings


def test_multiple_parents_appear_once_in_the_view(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        band="root",
        links=[
            {"to": "2", "type": "breaks_down"},
            {"to": "3", "type": "breaks_down"},
        ],
    )
    write(nodes, 2, band="claims", links=[{"to": "4", "type": "supports"}])
    write(nodes, 3, band="evidence", links=[{"to": "4", "type": "supports"}])
    write(nodes, 4, band="decisions")
    result = check(tmp_path)
    assert result.ok
    view = load_view(tmp_path, "1-1")
    assert "4-1" in view.nodes
    assert list(view.nodes).count("4-1") == 1


def test_view_with_two_versions_of_one_id_warns(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        band="root",
        links=[
            {"to": "2-1", "type": "breaks_down"},
            {"to": "2-2", "type": "breaks_down"},
        ],
    )
    write(nodes, 2, band="claims")
    write(nodes, 2, version=2, band="evidence")
    result = check(tmp_path)
    assert any(
        issue.code == "graph-duplicate-version" for issue in result.warnings
    )
    assert result.ok


def test_default_root_is_lowest_id_version(write, tmp_path):
    write(tmp_path / "nodes", 5, band="root", links=[{"to": "6", "type": "breaks_down"}])
    write(tmp_path / "nodes", 6, band="claims")
    result = check(tmp_path)
    assert result.ok
    assert result.view == "5-1"
    assert result.nodes_scanned == 2


def test_default_root_orders_by_id_then_version(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 2, band="root", links=[{"to": "3", "type": "breaks_down"}])
    write(nodes, 3, band="claims")
    write(nodes, 1, version=2, band="lone")
    result = check(tmp_path)
    assert result.view == "1-2"
    assert not any(
        issue.code == "graph-orphan" and issue.node == "1-2"
        for issue in result.issues
    )
    assert any(
        issue.code == "graph-orphan" and issue.node == "2-1"
        for issue in result.warnings
    )


def test_declared_root_wins_over_lowest_id_version(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="root", links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2, band="claims")
    write(nodes, 1, version=4, band="root", links=[{"to": "2-1", "type": "breaks_down"}])
    (tmp_path / "ROOT").write_text("1-4\n", encoding="utf-8")
    result = check(tmp_path)
    assert result.ok
    assert result.view == "1-4"


def test_missing_declared_root_is_an_error(write, tmp_path):
    write(tmp_path / "nodes", 1, band="root")
    (tmp_path / "ROOT").write_text("1-9\n", encoding="utf-8")
    result = check(tmp_path)
    assert any(issue.code == "root-ref-missing" for issue in result.errors)


def test_invalid_root_file_is_an_error(write, tmp_path):
    write(tmp_path / "nodes", 1, band="root")
    (tmp_path / "ROOT").write_text("not-a-ref\n", encoding="utf-8")
    result = check(tmp_path)
    assert any(issue.code == "invalid-root" for issue in result.errors)


def test_bare_root_ref_is_reported(write, tmp_path):
    write(tmp_path / "nodes", 1, band="root")
    (tmp_path / "ROOT").write_text("1\n", encoding="utf-8")
    result = check(tmp_path)
    assert any(issue.code == "bare-ref" for issue in result.errors)


def test_orphan_node_warns_as_graph_orphan(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="root", links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2, band="claims")
    write(nodes, 9, band="lone")
    result = check(tmp_path)
    assert any(
        issue.code == "graph-orphan" and issue.node == "9-1"
        for issue in result.warnings
    )


def test_link_target_outside_the_parent_band_is_reachable(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="root", links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2, band="claims", links=[{"to": "10", "type": "history"}])
    write(nodes, 10, band="evidence", title="Decisions", links=[{"to": "11", "type": "supports"}])
    write(nodes, 11, band="decisions")
    result = check(tmp_path)
    assert result.ok
    assert set(load_view(tmp_path, "1-1").nodes) == {"1-1", "2-1", "10-1", "11-1"}


def test_link_from_an_unreachable_node_rescues_nothing(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="root", links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2, band="claims")
    write(nodes, 3, band="lone", links=[{"to": "4", "type": "supports"}])
    write(nodes, 4, band="tail")
    view = load_view(tmp_path, "1-1")
    assert set(view.nodes) == {"1-1", "2-1"}


def test_dangling_link_still_errors(write, tmp_path):
    write(
        tmp_path / "nodes",
        1,
        band="root",
        links=[{"to": "99", "type": "supports"}],
    )
    result = check(tmp_path)
    assert any(issue.code == "graph-dangling-link" for issue in result.errors)


def test_scalar_link_to_a_target_without_type_is_invalid(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="root", links=["10"])
    write(nodes, 10, band="claims")
    result = check(tmp_path)
    assert any(
        issue.code == "invalid-link"
        and "implicit link to '10-1'" in issue.message
        for issue in result.errors
    )


def test_scalar_link_to_a_missing_node_still_dangles(write, tmp_path):
    write(tmp_path / "nodes", 1, band="root", links=["99"])
    result = check(tmp_path)
    assert any(issue.code == "graph-dangling-link" for issue in result.errors)
    assert not any(issue.code == "invalid-link" for issue in result.errors)


def test_contains_removed_is_an_error_with_a_migrate_hint(write, tmp_path):
    write(tmp_path / "nodes", 1, band="root", contains=[])
    result = check(tmp_path)
    assert any(
        issue.code == "contains-removed" and "bd migrate" in issue.message
        for issue in result.errors
    )
    assert not result.ok


def test_symmetric_link_checks(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        band="root",
        links=[{"to": "1", "type": "peer", "symmetric": True}],
    )
    codes = _codes(check(tmp_path))
    assert "symmetric-self-edge" in codes

    selfless = tmp_path / "selfless"
    other = selfless / "nodes"
    write(
        other,
        1,
        band="root",
        links=[{"to": "2", "type": "peer", "symmetric": True}],
    )
    write(
        other,
        2,
        band="claims",
        links=[{"to": "1", "type": "peer", "symmetric": True}],
    )
    assert "duplicate-symmetric-edge" in _codes(check(selfless))

    propagating = tmp_path / "propagating"
    prop = propagating / "nodes"
    write(
        prop,
        1,
        band="root",
        links=[
            {
                "to": "2",
                "type": "peer",
                "symmetric": True,
                "propagates": True,
            }
        ],
    )
    write(prop, 2, band="claims")
    assert "propagates-on-symmetric" in _codes(check(propagating))


def test_non_list_band_order_is_an_error(write, tmp_path):
    write(
        tmp_path / "nodes",
        1,
        band="root",
        band_order="root,intent",
    )
    result = check(tmp_path)
    assert any(
        issue.code == "invalid-band-order" for issue in result.errors
    )


def test_bare_ref_in_links_is_an_error_and_is_excluded_from_the_view(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="root", links=["2"], raw_refs=True)
    write(nodes, 2, band="claims")
    result = check(tmp_path)
    assert any(issue.code == "bare-ref" for issue in result.errors)
    assert set(load_view(tmp_path, "1-1").nodes) == {"1-1"}


def test_invalid_ref_in_links_is_an_error(write, tmp_path):
    write(tmp_path / "nodes", 1, band="root", links=["y-z"], raw_refs=True)
    result = check(tmp_path)
    assert any(issue.code == "invalid-ref" for issue in result.errors)
