from __future__ import annotations

from bd_tree.api import check, load, load_view
from bd_tree.frontmatter import (
    parse_document,
    render_document,
    rewrite_freshness,
)
from bd_tree.inline import token_title


def _set_freshness(nodes, ref, map_):
    """Replace the whole ``freshness:`` mapping of one node, surgically."""
    node_file = nodes / f"{ref}.md"
    document = parse_document(node_file.read_text(encoding="utf-8"))
    node_file.write_text(
        document.with_raw_fm(rewrite_freshness(document.raw_fm, map_)),
        encoding="utf-8",
        newline="",
    )


def _write_tokens(nodes, node_id, *, title, tokens, body, version=1, **fields):
    """One node whose body declares its links directly as tokens."""
    nodes.mkdir(parents=True, exist_ok=True)
    ref = f"{node_id}-{version}"
    data = {"id": node_id, "title": title, **fields}
    rows = "".join(f"- {token}\n" for token in tokens)
    text = body if body.endswith("\n") else body + "\n"
    text = text + rows
    (nodes / f"{ref}.md").write_text(
        render_document(data, text), encoding="utf-8", newline=""
    )


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
        "title": "two",
        "summary": "",
        "date": "2026-01-01",
        "status": "current",
    }
    (nodes / "3-1.md").write_text(render_document(meta, "body\n"), encoding="utf-8")
    codes = _codes(check(tmp_path))
    assert "invalid-filename" in codes
    assert "id-filename-mismatch" in codes


def test_a_node_without_tokens_is_a_leaf(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="Root", tokens=["[[breaks_down, 2-1]]"], body="b\n")
    _write_tokens(nodes, 2, title="Two", tokens=[], body="b\n")
    result = check(tmp_path)
    assert result.ok
    assert load(tmp_path).children("2-1") == []


def test_dangling_token_target_is_an_error(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="Root", tokens=["[[breaks_down, 2-1]]"], body="b\n")
    _write_tokens(nodes, 2, title="Two", tokens=["[[serves, 9-1]]"], body="b\n")
    result = check(tmp_path)
    assert any(issue.code == "graph-dangling-link" for issue in result.errors)


def test_freshness_warnings(write, tmp_path, pin):
    nodes = tmp_path / "nodes"
    _write_tokens(
        nodes,
        1,
        title="Root",
        tokens=["[[breaks_down, 2-1]]", "[[breaks_down, 3-1]]"],
        body="b\n",
    )
    _write_tokens(nodes, 2, title="Two", tokens=[], body="b\n")
    _write_tokens(nodes, 3, title="Three", tokens=["[[serves, 2-1]]"], body="b\n")
    _set_freshness(nodes, "3-1", {"2-1": {"pinned": pin("old\n")}})
    result = check(tmp_path)
    assert any(issue.code == "stale-link" for issue in result.warnings)


def test_home_keys_are_inert_arbitrary_front_matter(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(
        nodes,
        1,
        title="Root",
        tokens=["[[breaks_down, 2-1]]", "[[breaks_down, 3-1]]"],
        body="b\n",
        home="same/place.md",
    )
    _write_tokens(nodes, 2, title="Two", tokens=[], body="b\n", home="same/place.md")
    _write_tokens(nodes, 3, title="Three", tokens=[], body="b\n", home="bad/../place.md")
    result = check(tmp_path)
    assert result.ok
    assert not any(
        issue.code in ("bad-home", "duplicate-home") for issue in result.issues
    )


def test_untracked_token_and_oversize_warning(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="Root", tokens=["[[breaks_down, 2-1]]"], body="b\n")
    _write_tokens(nodes, 2, title="Two", tokens=["[[supports, 3-1]]"], body="b\n")
    _write_tokens(nodes, 3, title="Three", tokens=[], body="b\n")
    _set_freshness(nodes, "2-1", {"3-1": {"propagates": True}})
    result = check(tmp_path)
    assert any(issue.code == "untracked-link" for issue in result.warnings)

    _write_tokens(nodes, 2, title="Two", tokens=["[[supports, 3-1]]"], body="line\n" * 121)
    _set_freshness(nodes, "2-1", {"3-1": {"propagates": True}})
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


def test_multiple_parents_appear_once_in_the_view(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(
        nodes,
        1,
        title="Root",
        tokens=["[[breaks_down, 2-1]]", "[[breaks_down, 3-1]]"],
        body="b\n",
    )
    _write_tokens(nodes, 2, title="Two", tokens=["[[supports, 4-1]]"], body="b\n")
    _write_tokens(nodes, 3, title="Three", tokens=["[[supports, 4-1]]"], body="b\n")
    _write_tokens(nodes, 4, title="Four", tokens=[], body="b\n")
    result = check(tmp_path)
    assert result.ok
    view = load_view(tmp_path, "1-1")
    assert "4-1" in view.nodes
    assert list(view.nodes).count("4-1") == 1


def test_view_with_two_versions_of_one_id_warns(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(
        nodes,
        1,
        title="Root",
        tokens=["[[breaks_down, 2-1]]", "[[breaks_down, 2-2]]"],
        body="b\n",
    )
    _write_tokens(nodes, 2, title="Two", tokens=[], body="b\n")
    _write_tokens(nodes, 2, title="Two v2", tokens=[], body="b\n", version=2)
    result = check(tmp_path)
    assert any(
        issue.code == "graph-duplicate-version" for issue in result.warnings
    )
    assert result.ok


def test_default_root_is_lowest_id_version(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 5, title="Five", tokens=["[[breaks_down, 6-1]]"], body="b\n")
    _write_tokens(nodes, 6, title="Six", tokens=[], body="b\n")
    result = check(tmp_path)
    assert result.ok
    assert result.view == "5-1"
    assert result.nodes_scanned == 2


def test_default_root_is_the_first_component_representative(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 2, title="Two", tokens=["[[breaks_down, 3-1]]"], body="b\n")
    _write_tokens(nodes, 3, title="Three", tokens=[], body="b\n")
    _write_tokens(nodes, 1, title="One v2", tokens=[], body="b\n", version=2)
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


def test_declared_root_wins_over_the_representative(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="One", tokens=["[[breaks_down, 2-1]]"], body="b\n")
    _write_tokens(nodes, 2, title="Two", tokens=[], body="b\n")
    _write_tokens(nodes, 1, title="One v4", tokens=["[[breaks_down, 2-1]]"], body="b\n", version=4)
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


def test_node_outside_the_anchor_component_warns_as_graph_orphan(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="Root", tokens=["[[breaks_down, 2-1]]"], body="b\n")
    _write_tokens(nodes, 2, title="Two", tokens=[], body="b\n")
    _write_tokens(nodes, 9, title="Nine", tokens=[], body="b\n")
    result = check(tmp_path)
    assert any(
        issue.code == "graph-orphan" and issue.node == "9-1"
        for issue in result.warnings
    )


def test_token_target_joins_the_component(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="Root", tokens=["[[breaks_down, 2-1]]"], body="b\n")
    _write_tokens(nodes, 2, title="Two", tokens=["[[history, 10-1]]"], body="b\n")
    _write_tokens(nodes, 10, title="Decisions", tokens=["[[supports, 11-1]]"], body="b\n")
    _write_tokens(nodes, 11, title="Eleven", tokens=[], body="b\n")
    result = check(tmp_path)
    assert result.ok
    assert set(load_view(tmp_path, "1-1").nodes) == {"1-1", "2-1", "10-1", "11-1"}


def test_a_separate_component_is_not_in_the_view(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="Root", tokens=["[[breaks_down, 2-1]]"], body="b\n")
    _write_tokens(nodes, 2, title="Two", tokens=[], body="b\n")
    _write_tokens(nodes, 3, title="Three", tokens=["[[supports, 4-1]]"], body="b\n")
    _write_tokens(nodes, 4, title="Four", tokens=[], body="b\n")
    view = load_view(tmp_path, "1-1")
    assert set(view.nodes) == {"1-1", "2-1"}


def test_cycle_is_legal_and_the_view_is_the_whole_component(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="One", tokens=["[[supports, 2-1]]"], body="b\n")
    _write_tokens(nodes, 2, title="Two", tokens=["[[supports, 3-1]]"], body="b\n")
    _write_tokens(nodes, 3, title="Three", tokens=["[[supports, 1-1]]"], body="b\n")
    result = check(tmp_path)
    assert result.ok
    assert set(load_view(tmp_path, "1-1").nodes) == {"1-1", "2-1", "3-1"}


def test_dangling_token_target_still_errors(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="Root", tokens=["[[supports, 99-1]]"], body="b\n")
    result = check(tmp_path)
    assert any(issue.code == "graph-dangling-link" for issue in result.errors)


def test_band_keys_are_inert_front_matter(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(
        nodes,
        1,
        title="One",
        tokens=[],
        body="b\n",
        band="root",
        band_order="root,intent",
        band_layout="flat",
    )
    result = check(tmp_path)
    assert result.ok
    assert "invalid-band-order" not in _codes(result)


def test_bare_id_in_a_token_is_malformed_and_excluded(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="Root", tokens=["[[x, 2]]"], body="b\n")
    _write_tokens(nodes, 2, title="Two", tokens=[], body="b\n")
    result = check(tmp_path)
    assert any(issue.code == "inline-malformed" for issue in result.errors)
    assert set(load_view(tmp_path, "1-1").nodes) == {"1-1"}


def test_fm_links_key_is_an_error(write, tmp_path):
    nodes = tmp_path / "nodes"
    nodes.mkdir(parents=True)
    (nodes / "1-1.md").write_text(
        render_document(
            {"id": 1, "title": "One", "links": [{"to": "2-1", "type": "x"}]},
            "body\n",
        ),
        encoding="utf-8",
    )
    (nodes / "2-1.md").write_text(
        render_document({"id": 2, "title": "Two"}, "body\n"), encoding="utf-8"
    )
    result = check(tmp_path)
    assert any(issue.code == "links-removed" for issue in result.errors)


def test_cached_title_matches_the_live_title(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="One", tokens=["[[x, 2-1]](Two)"], body="b\n")
    _write_tokens(nodes, 2, title="Two", tokens=[], body="b\n")
    assert check(tmp_path).ok
    assert token_title("[[x, 2-1]](Two)") == "Two"
