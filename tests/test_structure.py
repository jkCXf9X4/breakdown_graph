from __future__ import annotations

import pytest

from bd_tree import api
from bd_tree.cli import main
from bd_tree.errors import BreakdownError
from bd_tree.frontmatter import body_hash, parse_document

BODIES = {
    1: "root body\n\nwith a blank line\n\n\n",
    2: "claims body\nsecond line\n\n",
    3: "review body\n",
    4: "evidence body\n\n",
}


def _split_section(text):
    """Split a body at the trailing ``## Links`` section marker."""
    marker = text.rfind("## Links")
    if marker == -1:
        return text, None
    return text[:marker], text[marker:]


def _split_doc(root, ref):
    """The node's body split into (outside-section bytes, section-or-None)."""
    return _split_section(_doc(root, ref).body)


def _doc(root, ref):
    return parse_document((root / "nodes" / f"{ref}.md").read_text(encoding="utf-8"))


def _meta(root, ref):
    return _doc(root, ref).meta


def _pairs(root, ref):
    return [
        (link.to, link.type) for link in api.load(root).nodes[ref].links
    ]


def _tree(write, tmp_path, *, links_1=None):
    nodes = tmp_path / "nodes"
    links = (
        links_1
        if links_1 is not None
        else [
            {"to": "2", "type": "breaks_down"},
            {"to": "3", "type": "breaks_down"},
        ]
    )
    write(nodes, 1, band="main", order=0, links=links, body=BODIES[1])
    write(
        nodes,
        2,
        band="main",
        order=1,
        links=[{"to": "4", "type": "breaks_down"}],
        body=BODIES[2],
    )
    write(nodes, 3, band="main", order=2, body=BODIES[3])
    write(nodes, 4, band="main", order=3, body=BODIES[4])
    return nodes


def test_link_appends_an_edge_and_keeps_existing_fields(write, tmp_path):
    _tree(write, tmp_path, links_1=[{"to": "3-1", "type": "reviews"}])
    api.link(tmp_path, "1-1", "4-1", link_type="supports")
    head, section = _split_doc(tmp_path, "1-1")
    assert head == BODIES[1] + "\n"  # outside-section bytes unchanged
    assert section == (
        "## Links\n\n- (Title of 3-1)[[3-1, reviews]]\n"
        "- (Title of 4-1)[[4-1, supports]]\n"
    )
    assert _pairs(tmp_path, "1-1") == [
        ("3-1", "reviews"),
        ("4-1", "supports"),
    ]


def test_link_writes_the_token_when_the_section_is_absent(write, tmp_path):
    _tree(write, tmp_path, links_1=[])
    api.link(tmp_path, "1-1", "4-1", link_type="decision")
    head, section = _split_doc(tmp_path, "1-1")
    assert head == BODIES[1] + "\n"
    assert section == "## Links\n- (Title of 4-1)[[4-1, decision]]\n"
    assert _pairs(tmp_path, "1-1") == [("4-1", "decision")]


def test_unlink_removes_a_token_by_type_and_by_target(write, tmp_path):
    nodes = _tree(
        write,
        tmp_path,
        links_1=[
            {"to": "10-1", "type": "decision"},
            {"to": "3-1", "type": "reviews"},
        ],
    )
    write(nodes, 10, band="main", order=4, body="decision body\n")
    api.unlink(tmp_path, "1-1", "10-1", link_type="decision")
    head, section = _split_doc(tmp_path, "1-1")
    assert head == BODIES[1] + "\n"
    assert section == "## Links\n\n- (Title of 3-1)[[3-1, reviews]]\n"

    nodes = _tree(write, tmp_path, links_1=[{"to": "10-1", "type": "decision"}])
    write(nodes, 10, band="main", order=4, body="decision body\n")
    api.unlink(tmp_path, "1-1", "10-1")
    head, section = _split_doc(tmp_path, "1-1")
    assert head == BODIES[1] + "\n"
    assert section is None  # the empty section is dropped


def test_unlink_drops_the_freshness_entry_only_when_no_token_remains(
    write, tmp_path
):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        band="main",
        order=0,
        links=[
            {"to": "4", "type": "a"},
            {"to": "4", "type": "b"},
        ],
        body=BODIES[1],
        freshness={"4-1": {"pinned": body_hash(BODIES[4]), "propagates": True}},
    )
    write(nodes, 4, band="main", order=3, body=BODIES[4])

    api.unlink(tmp_path, "1-1", "4-1", link_type="a")
    entry = _meta(tmp_path, "1-1")["freshness"]["4-1"]
    assert entry["pinned"] == body_hash(BODIES[4])  # b still targets 4-1

    api.unlink(tmp_path, "1-1", "4-1", link_type="b")
    assert "freshness" not in _meta(tmp_path, "1-1")


def test_link_propagates_pins_the_target_now(write, tmp_path):
    _tree(write, tmp_path, links_1=[])
    api.link(tmp_path, "1-1", "4-1", link_type="depends", propagates=True)
    entry = _meta(tmp_path, "1-1")["freshness"]["4-1"]
    assert entry["pinned"] == body_hash(BODIES[4])
    assert entry["propagates"] is True
    _, section = _split_doc(tmp_path, "1-1")
    assert "- (Title of 4-1)[[4-1, depends]]" in section
    assert api.stale(tmp_path, "1-1") == []


def test_structural_edits_preserve_unrelated_front_matter(write, tmp_path):
    _tree(write, tmp_path, links_1=[])
    api.link(tmp_path, "1-1", "4-1", link_type="supports", propagates=True)
    meta = _meta(tmp_path, "1-1")
    assert meta["band"] == "main"
    assert meta["order"] == 0
    assert meta["id"] == 1


def test_link_refuses_duplicates_and_accepts_arbitrary_types(write, tmp_path):
    _tree(write, tmp_path, links_1=[{"to": "3-1", "type": "reviews"}])
    with pytest.raises(BreakdownError, match="unlink first"):
        api.link(tmp_path, "1-1", "3-1", link_type="reviews")
    api.link(tmp_path, "1-1", "3-1", link_type="refines-claim_v2")
    assert _pairs(tmp_path, "1-1") == [
        ("3-1", "reviews"),
        ("3-1", "refines-claim_v2"),
    ]


def test_link_allows_a_backward_edge(write, tmp_path):
    _tree(write, tmp_path)
    api.link(tmp_path, "2-1", "1-1", link_type="supports")
    head, section = _split_doc(tmp_path, "2-1")
    assert head == BODIES[2] + "\n"
    assert section == (
        "## Links\n\n- (Title of 4-1)[[4-1, breaks_down]]\n"
        "- (Title of 1-1)[[1-1, supports]]\n"
    )
    assert _pairs(tmp_path, "2-1") == [("4-1", "breaks_down"), ("1-1", "supports")]


def test_unlink_by_type_and_by_target(write, tmp_path):
    _tree(
        write,
        tmp_path,
        links_1=[
            {"to": "4-1", "type": "a"},
            {"to": "4-1", "type": "b"},
            {"to": "3-1", "type": "a"},
        ],
    )
    api.unlink(tmp_path, "1-1", "4-1", link_type="a")
    _, section = _split_doc(tmp_path, "1-1")
    assert section == (
        "## Links\n\n- (Title of 4-1)[[4-1, b]]\n- (Title of 3-1)[[3-1, a]]\n"
    )

    api.unlink(tmp_path, "1-1", "4-1")
    _, section = _split_doc(tmp_path, "1-1")
    assert section == "## Links\n\n- (Title of 3-1)[[3-1, a]]\n"

    api.unlink(tmp_path, "1-1", "3-1")
    assert _split_doc(tmp_path, "1-1")[1] is None


def test_unlink_refuses_when_nothing_matches(write, tmp_path):
    _tree(write, tmp_path, links_1=[{"to": "3-1", "type": "reviews"}])
    with pytest.raises(BreakdownError, match="no link"):
        api.unlink(tmp_path, "1-1", "4-1")
    with pytest.raises(BreakdownError, match="no link"):
        api.unlink(tmp_path, "1-1", "3-1", link_type="other")
    with pytest.raises(BreakdownError, match="does not exist"):
        api.unlink(tmp_path, "1-1", "99-1")


def test_structural_edits_preserve_body_bytes_except_within_links(
    write, tmp_path
):
    _tree(write, tmp_path, links_1=[{"to": "3-1", "type": "reviews"}])
    before = {
        ref: _doc(tmp_path, ref).body for ref in ("1-1", "2-1", "3-1", "4-1")
    }

    api.link(tmp_path, "1-1", "4-1", link_type="supports", propagates=True)
    head, section = _split_doc(tmp_path, "1-1")
    before_head, before_section = _split_section(before["1-1"])
    assert head == before_head
    assert section == before_section + "- (Title of 4-1)[[4-1, supports]]\n"
    assert _doc(tmp_path, "3-1").body == before["3-1"]
    assert _doc(tmp_path, "4-1").body == before["4-1"]

    api.unlink(tmp_path, "1-1", "4-1")
    assert _doc(tmp_path, "1-1").body == before["1-1"]

    api.link(tmp_path, "2-1", "3-1", link_type="refines")
    head, section = _split_doc(tmp_path, "2-1")
    assert head == _split_section(before["2-1"])[0]  # head bytes untouched
    assert section == (
        _split_section(before["2-1"])[1] + "- (Title of 3-1)[[3-1, refines]]\n"
    )
    assert _doc(tmp_path, "3-1").body == before["3-1"]

    api.unlink(tmp_path, "2-1", "3-1")
    assert _doc(tmp_path, "2-1").body == before["2-1"]


def test_prose_tokens_unlink_and_repoint_in_place(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, body="Before [[2-1, supports]] after.\n")
    write(nodes, 2)
    write(nodes, 2, version=2, title="Second live")

    api.replace(tmp_path, "2-1", "2-2")

    assert _doc(tmp_path, "1-1").body == (
        "Before (Second live)[[2-2, supports]] after.\n"
    )

    api.unlink(tmp_path, "1-1", "2-2")

    assert _doc(tmp_path, "1-1").body == "Before after.\n"


def test_cli_structure_commands_and_exit_codes(write, tmp_path, capsys):
    _tree(write, tmp_path, links_1=[])
    root = str(tmp_path)

    assert main(["link", "1", "4-1", "--type", "supports", "--root", root]) == 0
    assert "linked 1-1 -> 4-1 (supports)" in capsys.readouterr().out
    _, section = _split_doc(tmp_path, "1-1")
    assert section == "## Links\n- (Title of 4-1)[[4-1, supports]]\n"

    assert main(["link", "1", "4-1", "--type", "supports", "--root", root]) == 2
    assert "unlink first" in capsys.readouterr().err

    assert (
        main(["unlink", "1", "4-1", "--type", "supports", "--root", root]) == 0
    )
    assert "unlinked 1-1 -> 4-1 (supports)" in capsys.readouterr().out
    assert _split_doc(tmp_path, "1-1")[1] is None

    assert main(["unlink", "1", "4-1", "--root", root]) == 2
    assert "no link" in capsys.readouterr().err


def test_link_allows_a_cycle_between_distinct_nodes(write, tmp_path):
    _tree(write, tmp_path)
    api.link(tmp_path, "4-1", "1-1", link_type="history")
    head, section = _split_doc(tmp_path, "4-1")
    assert head == BODIES[4] + "\n"
    assert section == "## Links\n- (Title of 1-1)[[1-1, history]]\n"
