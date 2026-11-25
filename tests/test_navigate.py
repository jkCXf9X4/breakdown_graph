"""Read-only navigation: show, find, and path over a link closure."""

from __future__ import annotations

import pytest

from bd_tree.cli import main
from bd_tree.frontmatter import render_document
from bd_tree.loader import load
from bd_tree.navigate import (
    NavigationError,
    parse_ref_depth,
    render_find,
    render_path,
    render_show,
    view_roots,
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


def _tree(write, tmp_path, body_by_id=None):
    nodes = tmp_path / "nodes"
    bodies = body_by_id or {}
    _write_tokens(
        nodes,
        1,
        title="Root",
        tokens=["[[breaks_down, 2-1]]", "[[breaks_down, 3-1]]"],
        body=bodies.get(1, "root body\n"),
    )
    _write_tokens(
        nodes,
        2,
        title="Child",
        tokens=["[[breaks_down, 4-1]]"],
        body=bodies.get(2, "child body\n"),
    )
    _write_tokens(nodes, 3, title="Sibling", tokens=[], body=bodies.get(3, "sibling body\n"))
    _write_tokens(nodes, 4, title="Grandchild", tokens=[], body=bodies.get(4, "grandchild body\n"))
    return load(tmp_path)


# -- ref+depth parsing -------------------------------------------------------


def test_ref_depth_suffix_and_override():
    assert (parse_ref_depth("5").ref, parse_ref_depth("5").depth) == ("5", None)
    parsed = parse_ref_depth("5+2")
    assert (parsed.ref, parsed.depth) == ("5", 2)
    parsed = parse_ref_depth("5-1+2")
    assert (parsed.ref, parsed.depth) == ("5-1", 2)
    assert parse_ref_depth("5+1", override=3).depth == 3
    assert parse_ref_depth("5+1", override=0).depth == 0


@pytest.mark.parametrize("text", ["5+", "5+x", "5+-1", "0", "5+1+", "+2"])
def test_ref_depth_invalid(text):
    with pytest.raises(NavigationError):
        parse_ref_depth(text)


def test_cli_rejects_unknown_ref_and_bad_depth(write, tmp_path, capsys):
    _tree(write, tmp_path)
    assert main(["show", "99", "--root", str(tmp_path)]) == 1
    assert main(["show", "1+oops", "--root", str(tmp_path)]) == 1
    assert main(["show", "1", "--depth", "-1", "--root", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "id 99" in err
    assert "view 1-1" in err


# -- show --------------------------------------------------------------------


def test_show_root_only_by_default(write, tmp_path):
    store = _tree(write, tmp_path)
    out = render_show(store, "1-1")
    assert out.startswith("# 1-1  Root")
    assert "## 2-1" not in out
    assert "child body" not in out


def test_show_depth_two_uses_undirected_bfs_rings(write, tmp_path):
    store = _tree(write, tmp_path)
    out = render_show(store, "1-1", depth=2)
    # Ring 1 is the two children, ring 2 the grandchild.
    assert out.index("## 2-1  Child") < out.index("## 3-1  Sibling")
    assert out.index("## 3-1  Sibling") < out.index("### 4-1  Grandchild")
    assert "child body" in out
    assert "grandchild body" in out


def test_show_direction_labels(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="Root", tokens=["[[breaks_down, 2-1]]"], body="b\n")
    _write_tokens(nodes, 3, title="Parent", tokens=["[[supports, 1-1]]"], body="b\n")
    _write_tokens(nodes, 2, title="Child", tokens=[], body="b\n")
    store = load(tmp_path)
    out = render_show(store, "1-1", depth=1)
    assert "## 2-1  Child  →" in out
    assert "## 3-1  Parent  ←" in out


def test_show_no_body_and_max_chars_and_fields(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(
        nodes, 1, title="Root", tokens=[], body="abcdefghij\n", layer="intent", type="intent"
    )
    store = load(tmp_path)

    stripped = render_show(store, "1-1", no_body=True)
    assert "abcdefghij" not in stripped

    clipped = render_show(store, "1-1", max_chars=5)
    assert "abcde ... [truncated; bd show 1-1]" in clipped

    selected = render_show(store, "1-1", fields=["layer"])
    assert "layer: intent" in selected
    assert "type:" not in selected


def test_show_auto_cap_by_depth(write, tmp_path):
    nodes = tmp_path / "nodes"
    body = "x" * 5000
    _write_tokens(
        nodes, 1, title="Root", tokens=["[[breaks_down, 2-1]]"], body=body + "\n"
    )
    _write_tokens(nodes, 2, title="Child", tokens=[], body=body + "\n")
    store = load(tmp_path)

    full = render_show(store, "1-1")
    assert body in full
    assert "[truncated" not in full

    capped = render_show(store, "1-1", depth=1)
    assert body not in capped
    assert "[truncated; bd show 1-1]" in capped
    assert "[truncated; bd show 2-1]" in capped

    explicit_full = render_show(store, "1-1", depth=1, max_chars=0)
    assert body in explicit_full
    assert "[truncated" not in explicit_full

    explicit_cap = render_show(store, "1-1", max_chars=10)
    assert "xxxxxxxxxx ... [truncated; bd show 1-1]" in explicit_cap


def test_path_command_prints_shortest_path_with_arrows(write, tmp_path, capsys):
    _tree(write, tmp_path)
    assert main(["path", "4", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out == (
        "1-1  Root\n→ 2-1  Child\n→ 4-1  Grandchild\n"
    )


def _linked_tree(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="Root", tokens=["[[breaks_down, 2-1]]"], body="b\n")
    _write_tokens(nodes, 2, title="Child", tokens=["[[history, 10-1]]"], body="b\n")
    _write_tokens(nodes, 10, title="Decisions", tokens=[], body="b\n")
    return load(tmp_path)


def test_show_links_footer_labels_direction(write, tmp_path):
    store = _linked_tree(write, tmp_path)
    assert "links:" not in render_show(store, "1-1", depth=1)
    out = render_show(store, "1-1", depth=1, links=True)
    assert "- 1-1 → 2-1  Child  (breaks_down)" in out
    assert "- 2-1 → 10-1  Decisions  (history)" in out
    assert "- 2-1 ← 1-1  Root  (breaks_down)" in out


def test_cli_show_links_flag(write, tmp_path, capsys):
    _linked_tree(write, tmp_path)
    assert (
        main(["show", "1-1", "--depth", "1", "--links", "--root", str(tmp_path)]) == 0
    )
    out = capsys.readouterr().out
    assert "links:" in out
    assert "- 2-1 → 10-1  Decisions  (history)" in out


def test_graph_default_uses_root_file(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="One", tokens=["[[x, 2-1]]"], body="b\n")
    _write_tokens(nodes, 2, title="Two", tokens=[], body="b\n")
    _write_tokens(nodes, 5, title="Five", tokens=["[[x, 2-1]]"], body="b\n")
    (tmp_path / "ROOT").write_text("5-1\n", encoding="utf-8")
    assert main(["graph", "--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "## 0 — 5-1" in out
    assert "## 0 — 1-1" not in out
    assert "[1-1]" in out
    assert "## 2" in out


def test_root_command_show_set_clear(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="One", tokens=["[[breaks_down, 2-1]]"], body="b\n")
    _write_tokens(nodes, 2, title="Two", tokens=[], body="b\n")
    assert main(["root", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out.split()[0] == "1-1"
    assert main(["root", "1", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out.startswith("1-1")
    assert (tmp_path / "ROOT").read_text(encoding="utf-8").strip() == "1-1"
    assert main(["root", "--clear", "--root", str(tmp_path)]) == 0
    assert not (tmp_path / "ROOT").exists()


# -- find --------------------------------------------------------------------


def _find_tree(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(
        nodes,
        1,
        title="Root topic",
        tokens=["[[breaks_down, 2-1]]"],
        layer="intent",
        body="alpha\ncredibility appears here\n",
    )
    _write_tokens(
        nodes,
        2,
        title="Credibility child",
        tokens=[],
        layer="claims",
        body="needle line\ncredibility body line\n",
    )
    _write_tokens(nodes, 3, title="Unrelated", tokens=[], layer="claims", body="other\n")
    return load(tmp_path)


def test_find_title_hit(write, tmp_path):
    store = _find_tree(write, tmp_path)
    out = render_find(store, "credibility child")
    assert "2-1  1-1 > 2-1  Credibility child" in out


def test_find_body_hit_has_line_number(write, tmp_path):
    store = _find_tree(write, tmp_path)
    out = render_find(store, "credibility body")
    assert "1-1 > 2-1:2  credibility body line" in out


def test_find_field_restricts_search(write, tmp_path):
    store = _find_tree(write, tmp_path)
    assert "Credibility child" not in render_find(store, "credibility", field="layer")
    out = render_find(store, "claims", field="layer", all_nodes=True)
    assert "Credibility child" in out
    assert "Unrelated" in out


def test_find_where_filter(write, tmp_path):
    store = _find_tree(write, tmp_path)
    out = render_find(store, "credibility", where=[("layer", "claims")])
    assert "Credibility child" in out
    assert "Root topic" not in out


def test_find_limit(write, tmp_path):
    nodes = tmp_path / "nodes"
    for node_id in (1, 2, 3):
        _write_tokens(nodes, node_id, title=f"hit {node_id}", tokens=[], body="b\n")
    store = load(tmp_path)
    out = render_find(store, "hit", limit=2, all_nodes=True)
    assert len(out.split("\n\n")) == 2


def test_find_regex_opt_in(write, tmp_path):
    store = _find_tree(write, tmp_path)
    assert "Credibility" not in render_find(store, "Cred[a-z]+")
    assert "Credibility child" in render_find(store, "Cred[a-z]+", regex=True)


def _two_trees(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(
        nodes, 1, title="First root", tokens=["[[breaks_down, 2-1]]"], body="b\n"
    )
    _write_tokens(nodes, 2, title="First child", tokens=[], body="needle first\n")
    _write_tokens(
        nodes, 5, title="Second root", tokens=["[[breaks_down, 6-1]]"], body="b\n"
    )
    _write_tokens(nodes, 6, title="Second child", tokens=[], body="needle second\n")
    return load(tmp_path)


def test_find_default_scopes_to_root(write, tmp_path):
    store = _two_trees(write, tmp_path)
    out = render_find(store, "needle")
    assert "First child" in out
    assert "Second child" not in out

    (tmp_path / "ROOT").write_text("5-1\n", encoding="utf-8")
    store = load(tmp_path)
    out = render_find(store, "needle")
    assert "Second child" in out
    assert "First child" not in out


def test_find_view_restricts_to_named_closure(write, tmp_path):
    store = _two_trees(write, tmp_path)
    out = render_find(store, "needle", view="5-1")
    assert "Second child" in out
    assert "Second root" not in out
    assert "First child" not in out


def test_find_all_nodes_preserves_whole_store(write, tmp_path):
    store = _two_trees(write, tmp_path)
    out = render_find(store, "needle", all_nodes=True)
    assert "First child" in out
    assert "Second child" in out


def test_find_rejects_an_unknown_view(write, tmp_path):
    store = _two_trees(write, tmp_path)
    with pytest.raises(NavigationError):
        render_find(store, "needle", view="99-1")


def test_find_regex_flag_uses_regex(write, tmp_path, capsys):
    _find_tree(write, tmp_path)
    assert main(["find", "Cred.*child", "--regex", "--root", str(tmp_path)]) == 0
    assert "Credibility child" in capsys.readouterr().out


# -- path --------------------------------------------------------------------


def test_path_root_to_leaf(write, tmp_path):
    store = _tree(write, tmp_path)
    assert render_path(store, "4-1") == "1-1  Root\n→ 2-1  Child\n→ 4-1  Grandchild"


def test_path_version_ref(write, tmp_path):
    nodes = tmp_path / "nodes"
    _tree(write, tmp_path)
    _write_tokens(nodes, 2, title="Child v2", tokens=[], body="v2\n", version=2)
    _write_tokens(
        nodes, 1, title="Root", tokens=["[[breaks_down, 2-2]]"], body="root body\n"
    )
    store = load(tmp_path)
    assert render_path(store, "2-2") == "1-1  Root\n→ 2-2  Child v2"


def test_path_follows_children_and_parents(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="Root", tokens=["[[verifies, 2-1]]"], body="b\n")
    _write_tokens(nodes, 2, title="Claim", tokens=["[[supports, 3-1]]"], body="b\n")
    _write_tokens(nodes, 3, title="Evidence", tokens=[], body="b\n")
    store = load(tmp_path)

    assert render_path(store, "2-1") == "1-1  Root\n→ 2-1  Claim"
    assert render_path(store, "3-1") == (
        "1-1  Root\n→ 2-1  Claim\n→ 3-1  Evidence"
    )


def test_path_rejects_a_ref_in_another_component(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="Root", tokens=[], body="b\n")
    _write_tokens(nodes, 5, title="Elsewhere", tokens=[], body="b\n")
    store = load(tmp_path)
    with pytest.raises(NavigationError, match="no undirected path"):
        render_path(store, "5-1")


# -- views -------------------------------------------------------------------


def test_view_roots_lists_one_representative_per_component(write, tmp_path):
    nodes = tmp_path / "nodes"
    store = _two_trees(write, tmp_path)
    assert [node.ref for node in view_roots(store)] == ["1-1", "5-1"]

    _write_tokens(
        nodes,
        5,
        title="Second root v2",
        tokens=["[[breaks_down, 6-1]]"],
        body="b\n",
        version=2,
    )
    store = load(nodes.parent)
    # 5-1 and 5-2 are peers of the same component through 6-1.
    assert [node.ref for node in view_roots(store)] == ["1-1", "5-1"]


def test_view_roots_survive_a_cycle(write, tmp_path):
    nodes = tmp_path / "nodes"
    _write_tokens(nodes, 1, title="One", tokens=["[[x, 2-1]]"], body="b\n")
    _write_tokens(nodes, 2, title="Two", tokens=["[[x, 1-1]]"], body="b\n")
    store = load(nodes.parent)
    assert [node.ref for node in view_roots(store)] == ["1-1"]
