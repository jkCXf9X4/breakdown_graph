"""Read-only navigation: show, tree (outline and columns), find, and path."""

from __future__ import annotations

import pytest

from bd_tree.cli import main
from bd_tree.loader import load
from bd_tree.navigate import (
    NavigationError,
    parse_ref_depth,
    render_find,
    render_path,
    render_show,
    render_tree,
    view_roots,
)


def _tree(write, tmp_path, body_by_id: dict[int, str] | None = None):
    nodes = tmp_path / "nodes"
    bodies = body_by_id or {}
    write(nodes, 1, title="Root", contains=["2", "3"], body=bodies.get(1, "root body\n"))
    write(
        nodes,
        2,
        title="Child",
        contains=["4"],
        body=bodies.get(2, "child body\n"),
    )
    write(nodes, 3, title="Sibling", body=bodies.get(3, "sibling body\n"))
    write(nodes, 4, title="Grandchild", body=bodies.get(4, "grandchild body\n"))
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
    assert "unknown ref" in capsys.readouterr().err


# -- show --------------------------------------------------------------------


def test_show_root_only_by_default(write, tmp_path):
    store = _tree(write, tmp_path)
    out = render_show(store, "1")
    assert out.startswith("# 1  Root")
    assert "## 2" not in out
    assert "child body" not in out


def test_show_depth_two_includes_grandchildren_in_order(write, tmp_path):
    store = _tree(write, tmp_path)
    out = render_show(store, "1", depth=2)
    assert out.index("## 2  Child") < out.index("### 4  Grandchild")
    assert out.index("### 4  Grandchild") < out.index("## 3  Sibling")
    assert "child body" in out
    assert "grandchild body" in out


def test_show_no_body_and_max_chars_and_fields(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, title="Root", layer="intent", type="intent", body="abcdefghij\n")
    store = load(tmp_path)

    stripped = render_show(store, "1", no_body=True)
    assert "abcdefghij" not in stripped

    clipped = render_show(store, "1", max_chars=5)
    assert "abcde ... [truncated; bd show 1]" in clipped

    selected = render_show(store, "1", fields=["layer"])
    assert "layer: intent" in selected
    assert "type:" not in selected


def test_show_auto_cap_by_depth(write, tmp_path):
    nodes = tmp_path / "nodes"
    body = "x" * 5000
    write(nodes, 1, title="Root", contains=["2"], body=body + "\n")
    write(nodes, 2, title="Child", body=body + "\n")
    store = load(tmp_path)

    full = render_show(store, "1")
    assert body in full
    assert "[truncated" not in full

    capped = render_show(store, "1", depth=1)
    assert body not in capped
    assert "[truncated; bd show 1]" in capped
    assert "[truncated; bd show 2]" in capped

    explicit_full = render_show(store, "1", depth=1, max_chars=0)
    assert body in explicit_full
    assert "[truncated" not in explicit_full

    explicit_cap = render_show(store, "1", max_chars=10)
    assert "xxxxxxxxxx ... [truncated; bd show 1]" in explicit_cap


def test_path_command_prints_breadcrumb(write, tmp_path, capsys):
    _tree(write, tmp_path)
    assert main(["path", "4", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out == "1  Root\n2  Child\n4  Grandchild\n"


# -- tree --------------------------------------------------------------------


def test_tree_glyphs(write, tmp_path):
    store = _tree(write, tmp_path)
    assert render_tree(store, "1", depth=2) == (
        "1 Root\n"
        "+- 2 Child\n"
        "|  `- 4 Grandchild\n"
        "`- 3 Sibling"
    )


def test_tree_default_depth_is_two_and_zero_is_unlimited(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, title="One", contains=["2"])
    write(nodes, 2, title="Two", contains=["3"])
    write(nodes, 3, title="Three", contains=["4"])
    write(nodes, 4, title="Four")
    store = load(tmp_path)

    assert "4 Four" not in render_tree(store, "1", depth=2)
    assert "3 Three" in render_tree(store, "1", depth=2)
    assert "4 Four" in render_tree(store, "1", depth=0)


def test_tree_summary_flag(write, tmp_path):
    store = _tree(write, tmp_path)
    out = render_tree(store, "1", depth=1, summary=True)
    assert "2 Child  summary" in out


def test_tree_renders_explicit_root(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 7, title="Seven", contains=["8"])
    write(nodes, 8, title="Eight")
    store = load(tmp_path)
    out = render_tree(store, "7", depth=1)
    assert out.startswith("7 Seven")


def _linked_tree(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, title="Root", contains=["2"])
    write(nodes, 2, title="Child", links=[{"to": "10", "type": "history"}])
    write(nodes, 10, title="Decisions")
    return load(tmp_path)


def test_show_links_footer_lists_edges_leaving_the_view(write, tmp_path):
    store = _linked_tree(write, tmp_path)
    assert "links:" not in render_show(store, "1", depth=1)
    out = render_show(store, "1", depth=1, links=True)
    assert out.endswith("links:\n- 2 -> 10  Decisions  (history)")


def test_tree_links_footer_lists_edges_leaving_the_view(write, tmp_path):
    store = _linked_tree(write, tmp_path)
    assert "links:" not in render_tree(store, "1", depth=1)
    out = render_tree(store, "1", depth=1, links=True)
    assert out.endswith("links:\n- 2 -> 10  Decisions  (history)")


def test_show_links_footer_uses_the_target_type_for_a_bare_ref(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, title="Root", contains=["2"])
    write(nodes, 2, title="Child", links=["10"])
    write(nodes, 10, title="Decisions", type="decision")
    store = load(tmp_path)
    out = render_show(store, "1", depth=1, links=True)
    assert out.endswith("links:\n- 2 -> 10  Decisions  (decision)")


def test_cli_show_links_flag(write, tmp_path, capsys):
    _linked_tree(write, tmp_path)
    assert (
        main(["show", "1", "--depth", "1", "--links", "--root", str(tmp_path)]) == 0
    )
    out = capsys.readouterr().out
    assert "links:" in out
    assert "- 2 -> 10  Decisions  (history)" in out


def test_tree_default_uses_root_file(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2)
    write(nodes, 5, version=1, contains=["2"])
    (tmp_path / "ROOT").write_text("5-1\n", encoding="utf-8")
    assert main(["tree", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out.startswith("5-1")


def test_root_command_show_set_clear(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2)
    write(nodes, 1, version=1, contains=["2"])
    assert main(["root", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out.split()[0] == "1"
    assert main(["root", "1-1", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out.startswith("1-1")
    assert (tmp_path / "ROOT").read_text(encoding="utf-8").strip() == "1-1"
    assert main(["root", "--clear", "--root", str(tmp_path)]) == 0
    assert not (tmp_path / "ROOT").exists()


# -- tree --columns ----------------------------------------------------------


def test_tree_columns_header_and_indentation(write, tmp_path, capsys):
    _tree(write, tmp_path)
    assert (
        main(
            ["tree", "1", "--columns", "ref,title", "--depth", "1", "--root", str(tmp_path)]
        )
        == 0
    )
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "ref  title"
    assert lines[1].startswith("2  Child")
    assert lines[2].startswith("3  Sibling")
    assert not any(line.startswith("1  Root") for line in lines)


def test_tree_columns_default_root_and_summary_truncation(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, title="Root", contains=["2"])
    write(nodes, 2, title="Child", summary="s" * 150)
    assert (
        main(
            [
                "tree",
                "--columns",
                "ref,title,summary",
                "--max-chars",
                "100",
                "--root",
                str(tmp_path),
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "ref  title  summary"
    assert "s" * 97 + "..." in out
    assert "s" * 150 not in out


def test_tree_columns_depth_zero_is_unlimited(write, tmp_path, capsys):
    _tree(write, tmp_path)
    assert (
        main(["tree", "1", "--columns", "ref,title", "--depth", "0", "--root", str(tmp_path)])
        == 0
    )
    lines = capsys.readouterr().out.splitlines()
    assert lines[1].startswith("2  Child")
    assert any(line.strip().startswith("4  Grandchild") for line in lines)
    assert any(line.startswith("3  Sibling") for line in lines)


# -- find --------------------------------------------------------------------


def _find_tree(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        title="Root topic",
        contains=["2"],
        layer="intent",
        body="alpha\ncredibility appears here\n",
    )
    write(
        nodes,
        2,
        title="Credibility child",
        layer="claims",
        body="needle line\ncredibility body line\n",
    )
    write(nodes, 3, title="Unrelated", layer="claims", body="other\n")
    return load(tmp_path)


def test_find_title_hit(write, tmp_path):
    store = _find_tree(write, tmp_path)
    out = render_find(store, "credibility child")
    assert "2  1 > 2  Credibility child" in out


def test_find_body_hit_has_line_number(write, tmp_path):
    store = _find_tree(write, tmp_path)
    out = render_find(store, "credibility body")
    assert "1 > 2:2  credibility body line" in out


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
        write(nodes, node_id, title=f"hit {node_id}")
    store = load(tmp_path)
    out = render_find(store, "hit", limit=2, all_nodes=True)
    assert len(out.split("\n\n")) == 2


def test_find_regex_opt_in(write, tmp_path):
    store = _find_tree(write, tmp_path)
    assert "Credibility" not in render_find(store, "Cred[a-z]+")
    assert "Credibility child" in render_find(store, "Cred[a-z]+", regex=True)


def _two_trees(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, title="First root", contains=["2"])
    write(nodes, 2, title="First child", body="needle first\n")
    write(nodes, 5, title="Second root", contains=["6"])
    write(nodes, 6, title="Second child", body="needle second\n")
    return load(tmp_path)


def test_find_default_scopes_to_root(write, tmp_path):
    store = _two_trees(write, tmp_path)
    out = render_find(store, "needle")
    assert "First child" in out
    assert "Second child" not in out

    (tmp_path / "ROOT").write_text("5\n", encoding="utf-8")
    store = load(tmp_path)
    out = render_find(store, "needle")
    assert "Second child" in out
    assert "First child" not in out


def test_find_view_restricts_to_named_closure(write, tmp_path):
    store = _two_trees(write, tmp_path)
    out = render_find(store, "needle", view="5")
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
        render_find(store, "needle", view="99")


def test_find_regex_flag_uses_regex(write, tmp_path, capsys):
    _find_tree(write, tmp_path)
    assert main(["find", "Cred.*child", "--regex", "--root", str(tmp_path)]) == 0
    assert "Credibility child" in capsys.readouterr().out


# -- path --------------------------------------------------------------------


def test_path_root_to_leaf(write, tmp_path):
    store = _tree(write, tmp_path)
    assert render_path(store, "4") == "1  Root\n2  Child\n4  Grandchild"


def test_path_version_ref(write, tmp_path):
    store = _tree(write, tmp_path)
    write(tmp_path / "nodes", 2, version=1, title="Child v1", body="v1\n")
    store = load(tmp_path)
    assert render_path(store, "2-1") == (
        "1  Root\n2  Child\n2-1  Child v1"
    )


# -- views -------------------------------------------------------------------


def test_view_roots_lists_each_complete_tree(write, tmp_path):
    store = _two_trees(write, tmp_path)
    assert [node.ref for node in view_roots(store)] == ["1", "5"]

    write(tmp_path / "nodes", 5, version=1, title="Second root v1", contains=["6"])
    store = load(tmp_path)
    assert [node.ref for node in view_roots(store)] == ["1", "5", "5-1"]
