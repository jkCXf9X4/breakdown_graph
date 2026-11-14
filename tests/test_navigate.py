"""Read-only navigation: show, tree, ls, find, grep and path."""

from __future__ import annotations

from pathlib import Path

import pytest

from breakdown.cli import main
from breakdown.loader import load
from breakdown.navigate import (
    NavigationError,
    parse_ref_depth,
    render_find,
    render_ls,
    render_path,
    render_show,
    render_tree,
)

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "workspace" / "licentiate-n"


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


def test_show_path_prepends_breadcrumb(write, tmp_path):
    store = _tree(write, tmp_path)
    out = render_show(store, "4", no_body=True, show_path=True)
    assert out.startswith("path: 1 Root > 2 Child > 4 Grandchild")


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


def test_tree_default_root_is_lowest_main(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 7, title="Seven", contains=["8"])
    write(nodes, 8, title="Eight")
    store = load(tmp_path)
    out = render_tree(store, "7", depth=1)
    assert out.startswith("7 Seven")


# -- ls ----------------------------------------------------------------------


def test_ls_header_columns_and_indentation(write, tmp_path):
    store = _tree(write, tmp_path)
    out = render_ls(store, "1", depth=1, columns=["ref", "title"])
    lines = out.splitlines()
    assert lines[0] == "ref  title"
    assert lines[1].startswith("2  Child")
    assert lines[2].startswith("3  Sibling")
    assert not any(line.startswith("1  Root") for line in lines)


def test_ls_default_root_and_summary_truncation(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, title="Root", contains=["2"])
    write(nodes, 2, title="Child", summary="s" * 150)
    assert main(["ls", "--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "ref  title  summary"
    assert "s" * 97 + "..." in out
    assert "s" * 150 not in out


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
    out = render_find(store, "claims", field="layer")
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
    out = render_find(store, "hit", limit=2)
    assert len(out.split("\n\n")) == 2


def test_find_regex_opt_in(write, tmp_path):
    store = _find_tree(write, tmp_path)
    assert "Credibility" not in render_find(store, "Cred[a-z]+")
    assert "Credibility child" in render_find(store, "Cred[a-z]+", regex=True)


def test_grep_alias_uses_regex(write, tmp_path, capsys):
    _find_tree(write, tmp_path)
    assert main(["grep", "Cred.*child", "--root", str(tmp_path)]) == 0
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


# -- corpus smoke ------------------------------------------------------------


def test_corpus_tree_show_and_find(capsys):
    assert main(["tree", "1", "--depth", "1", "--root", str(CORPUS)]) == 0
    out = capsys.readouterr().out
    assert "+- 2 " in out
    assert "`- 128 " in out

    assert main(["show", "1+1", "--root", str(CORPUS), "--no-body"]) == 0
    out = capsys.readouterr().out
    assert "## 2  What does the licentiate cover?" in out

    assert main(["find", "credibility", "--limit", "3", "--root", str(CORPUS)]) == 0
    blocks = capsys.readouterr().out.split("\n\n")
    assert 1 <= len(blocks) <= 3
