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
    write(nodes, 1, contains=["2", "3"], links=links_1, body=BODIES[1])
    write(nodes, 2, contains=["4"], body=BODIES[2])
    write(nodes, 3, body=BODIES[3])
    write(nodes, 4, body=BODIES[4])
    return nodes


def _doc(root, ref):
    return parse_document((root / "nodes" / f"{ref}.md").read_text(encoding="utf-8"))


def _meta(root, ref):
    return _doc(root, ref).meta


def _contains(root, ref):
    return api.load(root).effective_contains(ref)


def test_contain_appends_in_order_and_preserves_body(write, tmp_path):
    _tree(write, tmp_path)
    path = api.contain(tmp_path, "2-1", "3-1")
    assert path == (tmp_path / "nodes" / "2-1.md").resolve()
    assert _meta(tmp_path, "2-1")["contains"] == ["4-1", "3-1"]
    assert _contains(tmp_path, "2-1") == ["4-1", "3-1"]
    assert _doc(tmp_path, "2-1").body == BODIES[2]
    assert (tmp_path / "nodes" / "3-1.md").is_file()


def test_contain_before_and_after_position_a_sibling(write, tmp_path):
    _tree(write, tmp_path)
    api.contain(tmp_path, "1-1", "4-1", before="3-1")
    assert _meta(tmp_path, "1-1")["contains"] == ["2-1", "4-1", "3-1"]

    _tree(write, tmp_path)
    api.contain(tmp_path, "1-1", "4-1", after="2-1")
    assert _meta(tmp_path, "1-1")["contains"] == ["2-1", "4-1", "3-1"]


def test_contain_refuses_a_second_version_of_a_contained_id(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2-1"])
    write(nodes, 2)
    write(nodes, 2, version=2)
    with pytest.raises(BreakdownError, match="already holds version"):
        api.contain(tmp_path, "1-1", "2-2")


def test_contain_in_a_peer_version_does_not_touch_the_other(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 2, contains=["3"])
    write(nodes, 2, version=2)
    write(nodes, 3)
    write(nodes, 4)

    api.contain(tmp_path, "2-2", "4-1")

    assert _meta(tmp_path, "2-2")["contains"] == ["4-1"]
    assert _meta(tmp_path, "2-1")["contains"] == ["3-1"]
    assert _contains(tmp_path, "2-2") == ["4-1"]
    assert _contains(tmp_path, "2-1") == ["3-1"]


def test_contain_materializes_when_parent_had_no_list(write, tmp_path):
    _tree(write, tmp_path)
    assert "contains" not in _meta(tmp_path, "4-1")
    api.contain(tmp_path, "4-1", "3-1")
    assert _meta(tmp_path, "4-1")["contains"] == ["3-1"]


def test_contain_refuses_self_and_cycle(write, tmp_path):
    _tree(write, tmp_path)
    with pytest.raises(BreakdownError, match="itself"):
        api.contain(tmp_path, "1-1", "1-1")
    with pytest.raises(BreakdownError, match="cycle"):
        api.contain(tmp_path, "4-1", "1-1")
    assert _meta(tmp_path, "4-1").get("contains") is None


def test_contain_refuses_duplicate_and_missing_refs(write, tmp_path):
    _tree(write, tmp_path)
    with pytest.raises(BreakdownError, match="already contained"):
        api.contain(tmp_path, "1-1", "2-1")
    with pytest.raises(BreakdownError, match="does not exist"):
        api.contain(tmp_path, "1-1", "99-1")
    with pytest.raises(BreakdownError, match="does not exist"):
        api.contain(tmp_path, "99-1", "1-1")


def test_contain_position_must_be_a_sibling(write, tmp_path):
    _tree(write, tmp_path)
    with pytest.raises(BreakdownError, match="not contained"):
        api.contain(tmp_path, "1-1", "4-1", before="99-1")
    with pytest.raises(BreakdownError, match="not contained"):
        api.contain(tmp_path, "1-1", "4-1", after="99-1")


def test_uncontain_preserves_order_and_keeps_the_child_file(write, tmp_path):
    _tree(write, tmp_path)
    api.uncontain(tmp_path, "1-1", "2-1")
    assert _meta(tmp_path, "1-1")["contains"] == ["3-1"]
    assert _doc(tmp_path, "1-1").body == BODIES[1]
    assert _doc(tmp_path, "2-1").body == BODIES[2]
    assert (tmp_path / "nodes" / "2-1.md").is_file()
    assert _contains(tmp_path, "1-1") == ["3-1"]


def test_uncontain_last_child_writes_an_explicit_empty_list(write, tmp_path):
    _tree(write, tmp_path)
    api.uncontain(tmp_path, "1-1", "2-1")
    api.uncontain(tmp_path, "1-1", "3-1")
    meta = _meta(tmp_path, "1-1")
    assert "contains" in meta and meta["contains"] == []
    assert _contains(tmp_path, "1-1") == []


def test_uncontain_is_confined_to_the_named_version(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 1, version=2, contains=["2"])
    write(nodes, 2)

    api.uncontain(tmp_path, "1-2", "2-1")

    assert _meta(tmp_path, "1-2")["contains"] == []
    assert _contains(tmp_path, "1-2") == []
    assert _contains(tmp_path, "1-1") == ["2-1"]


def test_uncontain_refuses_a_missing_child(write, tmp_path):
    _tree(write, tmp_path)
    with pytest.raises(BreakdownError, match="not contained"):
        api.uncontain(tmp_path, "2-1", "3-1")
    with pytest.raises(BreakdownError, match="does not exist"):
        api.uncontain(tmp_path, "1-1", "99-1")
    assert (tmp_path / "nodes" / "3-1.md").is_file()


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
    _tree(write, tmp_path)
    api.link(tmp_path, "1-1", "4-1", link_type="decision")
    text = (tmp_path / "nodes" / "1-1.md").read_text(encoding="utf-8")
    assert "links: [{to: 4-1, type: decision}]" in text
    assert _meta(tmp_path, "1-1")["links"] == [{"to": "4-1", "type": "decision"}]


def test_scalar_link_writes_a_full_ref_when_the_target_declares_the_type(
    write, tmp_path
):
    nodes = _tree(write, tmp_path)
    write(nodes, 10, type="decision", body="decision body\n")
    api.link(tmp_path, "1-1", "10-1", link_type="decision")
    text = (tmp_path / "nodes" / "1-1.md").read_text(encoding="utf-8")
    assert "links: [10-1]" in text
    assert _meta(tmp_path, "1-1")["links"] == ["10-1"]
    assert _doc(tmp_path, "1-1").body == BODIES[1]


def test_link_keeps_a_mapping_when_the_type_does_not_match(write, tmp_path):
    nodes = _tree(write, tmp_path)
    write(nodes, 10, type="decision")
    api.link(tmp_path, "1-1", "10-1", link_type="supports")
    assert _meta(tmp_path, "1-1")["links"] == [{"to": "10-1", "type": "supports"}]


def test_link_propagating_keeps_a_mapping_even_when_the_type_matches(
    write, tmp_path
):
    nodes = _tree(write, tmp_path)
    write(nodes, 10, type="decision", body="decision body\n")
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
    write(nodes, 10, type="decision", body="decision body\n")
    api.unlink(tmp_path, "1-1", "10-1", link_type="decision")
    assert _meta(tmp_path, "1-1")["links"] == [
        {"to": "3-1", "type": "reviews"}
    ]
    assert _doc(tmp_path, "1-1").body == BODIES[1]

    nodes = _tree(write, tmp_path, links_1=["10-1"])
    write(nodes, 10, type="decision", body="decision body\n")
    api.unlink(tmp_path, "1-1", "10-1")
    assert _meta(tmp_path, "1-1").get("links") in (None, [])


def test_link_propagates_pins_the_target_now(write, tmp_path):
    _tree(write, tmp_path)
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

    api.contain(tmp_path, "1-1", "4-1")
    api.link(tmp_path, "1-1", "4-1", link_type="supports", propagates=True)
    api.unlink(tmp_path, "1-1", "4-1")
    api.contain(tmp_path, "2-1", "3-1")
    api.uncontain(tmp_path, "2-1", "3-1")

    after = {ref: _doc(tmp_path, ref).body for ref in ("1-1", "2-1", "3-1", "4-1")}
    assert after == before


def test_cli_structure_commands_and_exit_codes(write, tmp_path, capsys):
    _tree(write, tmp_path)
    root = str(tmp_path)

    assert main(["contain", "1", "4", "--after", "2", "--root", root]) == 0
    assert "contained 4-1 in 1-1" in capsys.readouterr().out
    assert _contains(tmp_path, "1-1") == ["2-1", "4-1", "3-1"]

    assert main(["uncontain", "1", "4", "--root", root]) == 0
    assert "removed 4-1 from 1-1" in capsys.readouterr().out
    assert _contains(tmp_path, "1-1") == ["2-1", "3-1"]

    assert main(["link", "1", "4", "--type", "supports", "--root", root]) == 0
    assert "linked 1-1 -> 4-1 (supports)" in capsys.readouterr().out

    assert (
        main(["unlink", "1", "4", "--type", "supports", "--root", root]) == 0
    )
    assert "unlinked 1-1 -> 4-1 (supports)" in capsys.readouterr().out
    assert _meta(tmp_path, "1-1").get("links") in (None, [])

    assert main(["contain", "1", "2", "--root", root]) == 2
    assert "already contained" in capsys.readouterr().err
    assert main(["contain", "4", "1", "--root", root]) == 2
    assert "cycle" in capsys.readouterr().err
    assert main(["unlink", "1", "4", "--root", root]) == 2
    assert "no link" in capsys.readouterr().err
