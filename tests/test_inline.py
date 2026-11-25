"""The inline token scanner: grammar, ignored regions, and writer helpers."""

from __future__ import annotations

import pytest

from bdg import api
from bdg.inline import (
    InlineAnomaly,
    InlineLink,
    append_token,
    parse_inline_links,
    raw_inline_tokens,
    remove_token,
    render_token,
    repoint_token,
    retitle_tokens,
    scan_inline_links,
    token_title,
)
from bdg.loader import load


def _links(body: str) -> list[InlineLink]:
    return scan_inline_links(body)[0]


def _anomalies(body: str) -> list[InlineAnomaly]:
    return scan_inline_links(body)[1]


def _codes(result):
    return {(issue.code, issue.level) for issue in result.issues}


# -- grammar -----------------------------------------------------------------


def test_valid_token_and_positioning():
    links, anomalies = scan_inline_links("See (Child)[[2-1, supports]].\n")
    assert anomalies == []
    assert links == [
        InlineLink(line=1, col=5, type="supports", to="2-1", title="Child")
    ]


def test_spaced_variants_around_the_comma():
    for text in (
        "[[2-1, supports]]",
        "[[2-1,supports]]",
        "[[2-1 ,supports]]",
        "[[2-1 , supports]]",
    ):
        assert _links(text)[0].to == "2-1", text
    # Two spaces on either side of the comma fail.
    assert _anomalies("[[2-1  , supports]]")[0].reason == "bad spacing"
    assert _anomalies("[[2-1,  supports]]")[0].reason == "bad spacing"


def test_multiple_tokens_on_one_line_and_type_characters():
    links = _links("a [[1-1, x_1]] b [[2-1, Y-2]]\n")
    assert [(link.type, link.to) for link in links] == [("x_1", "1-1"), ("Y-2", "2-1")]


def test_title_cache_is_a_prefix_and_may_have_spaces():
    links, anomalies = scan_inline_links("(Two parents, one node)[[2-1, supports]]\n")
    assert anomalies == []
    assert links == [
        InlineLink(
            line=1, col=1, type="supports", to="2-1",
            title="Two parents, one node",
        )
    ]
    assert _links("(Spaced title) [[2-1, supports]]")[0].title == "Spaced title"
    assert _links("(Paren inner (title)[[2-1, supports]]")[0].title == (
        "Paren inner (title"
    )
    # No title: a following parenthetical is plain text.
    assert _links("[[2-1, supports]] text (Not a title)")[0].title is None


def test_legacy_suffix_is_not_a_token():
    links, anomalies = scan_inline_links("[[2-1, supports]](Old title)\n")
    assert anomalies == []
    assert links == [
        InlineLink(line=1, col=1, type="supports", to="2-1", title=None)
    ]
    assert raw_inline_tokens("[[2-1, supports]](Old title)\n") == ["[[2-1, supports]]"]


def test_type_first_token_is_rejected():
    links, anomalies = scan_inline_links("[[supports, 2-1]]\n")
    assert links == []
    assert anomalies == [
        InlineAnomaly(line=1, col=1, reason="reversed components")
    ]


# -- ignored regions ---------------------------------------------------------


def test_fenced_blocks_are_untouched():
    body = (
        "```python\n[[bad type, 9-9]]\n```\n"
        "```\n[[bad type, 9-9]]\n```\n"
        "~~~\n[[bad type, 9-9]]\n~~~\n"
        "~~~~~\n[[bad type, 9-9]]\n~~~~~\n"
    )
    assert _links(body) == []
    assert _anomalies(body) == []


def test_fence_with_language_open_and_close():
    body = "~~~markdown\n[[1-1, x]]\n~~~\n[[1-1, ok]]\n"
    assert [(link.type, link.to) for link in _links(body)] == [("ok", "1-1")]


def test_inline_code_spans_are_ignored():
    body = "`[[bad type, 9-9]]` and ``[[bad type, 9-9]]`` keep quiet\n"
    assert _links(body) == []
    assert _anomalies(body) == []


def test_escape_is_ignored():
    body = r"\[[2-1, supports]] stays text\n"
    assert _links(body) == []
    assert _anomalies(body) == []
    # The escape only consumes `\[[`; later tokens still scan.
    body = r"\[[9-9, x]] then [[1-1, ok]]\n"
    assert [link.to for link in _links(body)] == ["1-1"]


# -- malformed ---------------------------------------------------------------


def test_bad_ref_and_type_components():
    for text, reason in (
        ("[[2bad, 3-1]]", "invalid ref"),
        ("[[bad type, 3-1]]", "invalid ref"),
        ("[[, 3-1]]", "invalid ref"),
        ("[[2-1, 2bad]]", "invalid type"),
        ("[[2-1, bad type]]", "invalid type"),
        ("[[supports, 2-1]]", "reversed components"),
        ("[[supports 2-1]]", "missing ','"),
        ("[[]]", "empty token"),
    ):
        anomalies = _anomalies(text + "\n")
        assert len(anomalies) == 1, text
        assert anomalies[0].reason == reason, text
        assert anomalies[0].line == 1 and anomalies[0].col == 1


def test_bare_ref_fails_at_the_scanner():
    # A bare id fails the token grammar at the scanner.
    assert _anomalies("[[2, supports]]\n")[0].reason == "bare ref"


def test_unterminated_token():
    anomalies = _anomalies("[[2-1, supports more\n")
    assert anomalies == [InlineAnomaly(line=1, col=1, reason="unterminated")]


def test_empty_title_prefix_is_malformed():
    anomalies = _anomalies("()[[2-1, supports]]\n")
    assert len(anomalies) == 1
    assert anomalies[0].reason == "empty title"
    assert _links("()[[2-1, supports]]\n") == []


# -- loader integration ------------------------------------------------------


def _write_node(nodes, node_id, body, *, version=1, **fields):
    from bdg.frontmatter import render_document

    data = {"id": node_id, **fields}
    data.setdefault("title", f"Title of {node_id}-{version}")
    path = nodes / f"{node_id}-{version}.md"
    path.write_text(render_document(data, body), encoding="utf-8", newline="")
    return path


def test_loader_converts_tokens_and_merges_freshness(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        title="Root",
        body="Upstream. (Child)[[2-1, supports]]\n",
        freshness={"2-1": {"propagates": True, "pinned": "sha256:ab12cd34ef56"}},
    )
    write(nodes, 2, title="Child", body="down\n")
    store = load(tmp_path)
    assert store.issues == []
    link = store.nodes["1-1"].links[0]
    assert (link.to, link.type, link.raw) == (
        "2-1", "supports", "(Child)[[2-1, supports]]",
    )
    assert link.propagates is True and link.pinned == "sha256:ab12cd34ef56"
    assert link.propagating is True
    assert store.nodes["1-1"].raw_links == ["(Child)[[2-1, supports]]"]


def test_token_anomalies_become_loader_issues_with_line(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, body="first line\n\nbroken [[9-9, bad type]] here\n", title="A")
    store = load(tmp_path)
    issues = [issue for issue in store.issues if issue.code == "inline-malformed"]
    assert len(issues) == 1
    assert issues[0].level == "error"
    assert issues[0].line == 3
    assert "invalid type" in issues[0].message


def test_title_missing_is_a_warning_on_the_token_line(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, body="first line\n\n[[2-1, x]] here\n", title="A")
    write(nodes, 2, title="Two")
    store = load(tmp_path)
    issues = [issue for issue in store.issues if issue.code == "inline-title-missing"]
    assert len(issues) == 1
    assert issues[0].level == "warning"
    assert issues[0].line == 3
    assert api.check(tmp_path).ok


def test_duplicate_token_is_a_warning_on_the_second_line(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, body="[[2-1, x]]\n[[2-1, x]]\n", title="A")
    write(nodes, 2, body="down\n")
    store = load(tmp_path)
    issues = [issue for issue in store.issues if issue.code == "inline-duplicate"]
    assert len(issues) == 1
    assert issues[0].level == "warning"
    assert issues[0].line == 2
    # Only the first declaration becomes an edge.
    assert [(link.to, link.type) for link in store.nodes["1-1"].links] == [("2-1", "x")]
    assert api.check(tmp_path).ok


def test_fm_links_key_is_removed_with_a_migrate_hint(write, tmp_path):
    # Raw front matter: the fixture auto-converts links, so write it by hand.
    nodes = tmp_path / "nodes"
    nodes.mkdir(parents=True)
    from bdg.frontmatter import render_document

    (nodes / "1-1.md").write_text(
        render_document(
            {"id": 1, "title": "A", "links": [{"to": "2-1", "type": "x"}]},
            "body\n",
        ),
        encoding="utf-8",
    )
    (nodes / "2-1.md").write_text(
        render_document({"id": 2, "title": "B"}, "body\n"), encoding="utf-8"
    )
    result = api.check(tmp_path)
    issues = [issue for issue in result.errors if issue.code == "links-removed"]
    assert len(issues) == 1
    assert "bdg migrate" in issues[0].message


def test_unresolved_target_dangles(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, body="[[9-9, supports]]\n")
    result = api.check(tmp_path)
    assert any(issue.code == "graph-dangling-link" for issue in result.errors)
    assert not result.ok


def test_title_stale_mismatch_is_a_warning_and_match_is_clean(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, title="Root", body="(Wrong cached title)[[2-1, supports]]\n")
    write(nodes, 2, title="Child")
    result = api.check(tmp_path)
    issues = [issue for issue in result.warnings if issue.code == "link-title-stale"]
    assert len(issues) == 1
    assert issues[0].line == 1

    write(nodes, 1, title="Root", body="(Child)[[2-1, supports]]\n")
    result = api.check(tmp_path)
    assert not any(issue.code == "link-title-stale" for issue in result.issues)


def test_invalid_freshness_shape_is_an_error(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, body="[[2-1, x]]\n", freshness={"2-1": {"pinned": 9}})
    write(nodes, 2)
    result = api.check(tmp_path)
    assert any(issue.code == "invalid-freshness" for issue in result.errors)


def test_leading_zero_ref_is_invalid(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, body="[[02-1, x]]\n")
    write(nodes, 2)
    result = api.check(tmp_path)
    assert any(issue.code == "invalid-ref" for issue in result.errors)


# -- writer helpers ----------------------------------------------------------


def test_append_token_appends_and_is_idempotent():
    text = "body\n\n## Links\n\n- (Alpha)[[1-1, a]]\n"
    once = append_token(text, "a", "1-1", "Alpha")
    assert once == text
    twice = append_token(text, "b", "2-1", "Beta")
    assert twice == text + "- (Beta)[[2-1,b]]\n"


def test_append_token_creates_the_section_with_a_blank_line():
    assert append_token("tail\n", "c", "3-1", "Gamma") == (
        "tail\n\n## Links\n- (Gamma)[[3-1,c]]\n"
    )
    assert append_token("", "c", "3-1", "Gamma") == "## Links\n- (Gamma)[[3-1,c]]\n"


def test_append_token_skips_trailing_blank_lines():
    text = "## Links\n\n- (Alpha)[[1-1, a]]\n\n## Next\n"
    assert append_token(text, "b", "2-1", "Beta") == (
        "## Links\n\n- (Alpha)[[1-1, a]]\n- (Beta)[[2-1,b]]\n\n## Next\n"
    )


def test_append_token_sees_a_legacy_spaced_token_as_the_same_edge():
    text = "body\n\n## Links\n\n- (T)[[2-1, supports]]\n"
    assert append_token(text, "supports", "2-1", "T") == text


def test_append_token_appends_the_same_edge_with_a_different_title():
    text = "body\n\n## Links\n\n- (T)[[2-1, supports]]\n"
    assert append_token(text, "supports", "2-1", "U") == (
        text + "- (U)[[2-1,supports]]\n"
    )


def test_remove_token_and_empty_section_drop():
    text = "head\n\n## Links\n\n- (Alpha)[[1-1, a]]\n- (Beta)[[2-1, b]]\n"
    new_text, count = remove_token(text, "a", "1-1")
    assert count == 1
    assert new_text == "head\n\n## Links\n\n- (Beta)[[2-1, b]]\n"
    new_text, count = remove_token(new_text, "b", "2-1")
    assert count == 1
    assert new_text == "head\n\n"
    # Nothing to remove is a no-op.
    assert remove_token(text, "zz", "9-9") == (text, 0)


def test_remove_token_drops_the_section_with_its_content():
    text = "head\n\n## Links\n\nsome note\n\n- (Alpha)[[1-1, a]]\n"
    new_text, count = remove_token(text, "a", "1-1")
    assert count == 1
    assert new_text == "head\n\n"


def test_repoint_token():
    text = "head\n\n## Links\n\n- (Alpha)[[1-1, a]]\n- (Beta)[[2-1, b]]\n"
    new_text, count = repoint_token(text, "1-1", "5-1")
    assert count == 1
    assert new_text == (
        "head\n\n## Links\n\n- (Alpha)[[5-1,a]]\n- (Beta)[[2-1, b]]\n"
    )
    assert repoint_token(text, "9-9", "5-1") == (text, 0)


def test_repoint_token_can_set_a_new_title():
    text = "it links (Alpha)[[1-1, a]] here.\n"
    new_text, count = repoint_token(text, "1-1", "5-2", "New title")
    assert count == 1
    assert new_text == "it links (New title)[[5-2,a]] here.\n"
    bare, count = repoint_token("[[1-1, a]]\n", "1-1", "5-2", "Alpha")
    assert (bare, count) == ("(Alpha)[[5-2,a]]\n", 1)


def test_remove_token_from_prose_joins_the_sentence():
    text = "it supports the fan-in (Fan in)[[8-1, supports]] and the core.\n"
    new_text, count = remove_token(text, "supports", "8-1")
    assert count == 1
    assert new_text == "it supports the fan-in and the core.\n"
    # A token ending a line keeps its trailing newline without doubled spaces.
    assert remove_token("a (X)[[1-1, x]]\n", "x", "1-1") == ("a\n", 1)
    # A token at the start of a line is cut without eating a following space.
    assert remove_token("[[1-1, x]] starts\n", "x", "1-1") == ("starts\n", 1)


def test_remove_token_skips_tokens_in_code_and_escapes():
    text = "`[[1-1, a]]` and \\[[1-1, a]] stay.\n"
    assert remove_token(text, "a", "1-1") == (text, 0)
    fenced = "```\n[[1-1, a]]\n```\n"
    assert remove_token(fenced, "a", "1-1") == (fenced, 0)


def test_repoint_token_in_prose():
    text = "it links (Alpha)[[1-1, a]] here.\n"
    new_text, count = repoint_token(text, "1-1", "5-2")
    assert count == 1
    assert new_text == "it links (Alpha)[[5-2,a]] here.\n"
    # Code and escapes are not rewritten.
    untouched = "`[[1-1, a]]` and \\[[1-1, a]]\n"
    assert repoint_token(untouched, "1-1", "5-2") == (untouched, 0)


# -- retitle_tokens ----------------------------------------------------------


def test_retitle_tokens_adds_replaces_and_leaves_unresolved_alone():
    text = "a [[1-1, x]] b (Old)[[2-1, y]] c [[3-1, z]]\n"
    new_text, count = retitle_tokens(
        text, {"1-1": "Alpha", "2-1": "New", "9-9": "Nope"}
    )
    assert count == 2
    assert new_text == "a (Alpha)[[1-1,x]] b (New)[[2-1,y]] c [[3-1, z]]\n"


def test_retitle_tokens_is_a_noop_when_the_title_matches():
    text = "(Alpha)[[1-1,x]]\n"
    assert retitle_tokens(text, {"1-1": "Alpha"}) == (text, 0)
    assert retitle_tokens(text, {}) == (text, 0)


def test_retitle_tokens_skips_code_and_escapes():
    text = "`[[1-1, x]]` and \\[[1-1, x]] and (Alpha)[[1-1, x]]\n"
    new_text, count = retitle_tokens(text, {"1-1": "Beta"})
    assert count == 1
    assert new_text == "`[[1-1, x]]` and \\[[1-1, x]] and (Beta)[[1-1,x]]\n"


# -- convenience helpers -----------------------------------------------------


def test_parse_inline_links_and_raw_alignment():
    body = "one (Alpha)[[1-1, x]] two [[2-1, y]]\n"
    assert [(link.type, link.to) for link in parse_inline_links(body)] == [
        ("x", "1-1"),
        ("y", "2-1"),
    ]
    assert raw_inline_tokens(body) == [
        "(Alpha)[[1-1, x]]",
        "[[2-1, y]]",
    ]
    assert render_token("x", "1-1", "Alpha") == "(Alpha)[[1-1,x]]"
    assert render_token("x", "1-1", None) == "[[1-1,x]]"
    assert token_title("(Alpha)[[1-1, x]]") == "Alpha"
    assert token_title("[[1-1, x]]") is None