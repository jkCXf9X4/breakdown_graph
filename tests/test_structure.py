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


def _doc(root, ref):
    return parse_document((root / "nodes" / f"{ref}.md").read_text(encoding="utf-8"))


def _meta(root, ref):
    return _doc(root, ref).meta


def test_link_appends_an_edge_and_keeps_existing_fields(write, tmp_path):
    _tree(write, tmp_path, links_1=[{"to": "3-1", "type": "reviews"}])
    api.link(tmp_path, "1-1", "4-1", link_type="supports")
    links = _meta(tmp_path, "1-1")["links"]
    assert links == [
        {"to": "3-1", "type": "reviews"},
        {"to": "4-1", "type": "supports"},
    ]
    assert _doc(tmp_path, "1-1").body == BODIES[1]


def test_single_link_is_written_inline(write, tmp_path):
    _tree(write, tmp_path, links_1=[])
    api.link(tmp_path, "1-1", "4-1", link_type="decision")
    text = (tmp_path / "nodes" / "1-1.md").read_text(encoding="utf-8")
    assert "links: [{to: 4-1, type: decision}]" in text
    assert _meta(tmp_path, "1-1")["links"] == [{"to": "4-1", "type": "decision"}]


def test_scalar_link_writes_a_full_ref_when_the_target_declares_the_type(
    write, tmp_path
):
    nodes = _tree(write, tmp_path, links_1=[])
    write(nodes, 10, type="decision", band="main", order=4, body="decision body\n")
    api.link(tmp_path, "1-1", "10-1", link_type="decision")
    text = (tmp_path / "nodes" / "1-1.md").read_text(encoding="utf-8")
    assert "links: [10-1]" in text
    assert _meta(tmp_path, "1-1")["links"] == ["10-1"]
    assert _doc(tmp_path, "1-1").body == BODIES[1]


def test_link_keeps_a_mapping_when_the_type_does_not_match(write, tmp_path):
    nodes = _tree(write, tmp_path, links_1=[])
    write(nodes, 10, type="decision", band="main", order=4)
    api.link(tmp_path, "1-1", "10-1", link_type="supports")
    assert _meta(tmp_path, "1-1")["links"] == [{"to": "10-1", "type": "supports"}]


def test_link_propagating_keeps_a_mapping_even_when_the_type_matches(
    write, tmp_path
):
    nodes = _tree(write, tmp_path, links_1=[])
    write(nodes, 10, type="decision", band="main", order=4, body="decision body\n")
    api.link(tmp_path, "1-1", "10-1", link_type="decision", propagates=True)
    link = _meta(tmp_path, "1-1")["links"][0]
    assert link["to"] == "10-1"
    assert link["propagates"] is True


def test_unlink_removes_a_scalar_link_by_type_and_by_target(write, tmp_path):
    nodes = _tree(
        write,
        tmp_path,
        links_1=["10-1", {"to": "3-1", "type": "reviews"}],
    )
    write(nodes, 10, type="decision", band="main", order=4, body="decision body\n")
    api.unlink(tmp_path, "1-1", "10-1", link_type="decision")
    assert _meta(tmp_path, "1-1")["links"] == [
        {"to": "3-1", "type": "reviews"}
    ]
    assert _doc(tmp_path, "1-1").body == BODIES[1]

    nodes = _tree(write, tmp_path, links_1=["10-1"])
    write(nodes, 10, type="decision", band="main", order=4, body="decision body\n")
    api.unlink(tmp_path, "1-1", "10-1")
    assert _meta(tmp_path, "1-1").get("links") in (None, [])


def test_link_propagates_pins_the_target_now(write, tmp_path):
    _tree(write, tmp_path, links_1=[])
    api.link(tmp_path, "1-1", "4-1", link_type="depends", propagates=True)
    edge = _meta(tmp_path, "1-1")["links"][0]
    assert edge["to"] == "4-1"
    assert edge["type"] == "depends"
    assert edge["propagates"] is True
    assert edge["pinned"] == body_hash(BODIES[4])
    assert api.stale(tmp_path, "1-1") == []


def test_link_refuses_duplicates_and_accepts_arbitrary_types(write, tmp_path):
    _tree(write, tmp_path, links_1=[{"to": "3-1", "type": "reviews"}])
    with pytest.raises(BreakdownError, match="unlink first"):
        api.link(tmp_path, "1-1", "3-1", link_type="reviews")
    api.link(tmp_path, "1-1", "3-1", link_type="refines-claim v2")
    assert _meta(tmp_path, "1-1")["links"][-1] == {
        "to": "3-1",
        "type": "refines-claim v2",
    }


def test_link_allows_a_backward_edge(write, tmp_path):
    _tree(write, tmp_path)
    api.link(tmp_path, "2-1", "1-1", link_type="supports")
    assert {"to": "1-1", "type": "supports"} in _meta(tmp_path, "2-1")["links"]


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
    assert _meta(tmp_path, "1-1")["links"] == [
        {"to": "4-1", "type": "b"},
        {"to": "3-1", "type": "a"},
    ]

    api.unlink(tmp_path, "1-1", "4-1")
    assert _meta(tmp_path, "1-1")["links"] == [{"to": "3-1", "type": "a"}]

    api.unlink(tmp_path, "1-1", "3-1")
    assert _meta(tmp_path, "1-1").get("links") in (None, [])


def test_unlink_refuses_when_nothing_matches(write, tmp_path):
    _tree(write, tmp_path, links_1=[{"to": "3-1", "type": "reviews"}])
    with pytest.raises(BreakdownError, match="no link"):
        api.unlink(tmp_path, "1-1", "4-1")
    with pytest.raises(BreakdownError, match="no link"):
        api.unlink(tmp_path, "1-1", "3-1", link_type="other")
    with pytest.raises(BreakdownError, match="does not exist"):
        api.unlink(tmp_path, "1-1", "99-1")


def test_body_bytes_unchanged_by_every_structural_edit(write, tmp_path):
    _tree(write, tmp_path, links_1=[{"to": "3-1", "type": "reviews"}])
    before = {
        ref: _doc(tmp_path, ref).body for ref in ("1-1", "2-1", "3-1", "4-1")
    }

    api.link(tmp_path, "1-1", "4-1", link_type="supports", propagates=True)
    api.unlink(tmp_path, "1-1", "4-1")
    api.link(tmp_path, "2-1", "3-1", link_type="refines")
    api.unlink(tmp_path, "2-1", "3-1")

    after = {ref: _doc(tmp_path, ref).body for ref in ("1-1", "2-1", "3-1", "4-1")}
    assert after == before


def test_cli_structure_commands_and_exit_codes(write, tmp_path, capsys):
    _tree(write, tmp_path, links_1=[])
    root = str(tmp_path)

    assert main(["link", "1", "4-1", "--type", "supports", "--root", root]) == 0
    assert "linked 1-1 -> 4-1 (supports)" in capsys.readouterr().out

    assert main(["link", "1", "4-1", "--type", "supports", "--root", root]) == 2
    assert "unlink first" in capsys.readouterr().err

    assert (
        main(["unlink", "1", "4-1", "--type", "supports", "--root", root]) == 0
    )
    assert "unlinked 1-1 -> 4-1 (supports)" in capsys.readouterr().out
    assert _meta(tmp_path, "1-1").get("links") in (None, [])

    assert main(["unlink", "1", "4-1", "--root", root]) == 2
    assert "no link" in capsys.readouterr().err


def test_link_allows_a_cycle_between_distinct_nodes(write, tmp_path):
    _tree(write, tmp_path)
    api.link(tmp_path, "4-1", "1-1", link_type="history")
    assert {"to": "1-1", "type": "history"} in _meta(tmp_path, "4-1")["links"]
