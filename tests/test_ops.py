from __future__ import annotations

import pytest

from bd_tree.api import (
    check,
    clone,
    delete,
    diff,
    link,
    load,
    load_view,
    migrate,
    new_node,
    replace,
    retitle,
    versions,
)
from bd_tree.cli import main
from bd_tree.errors import BreakdownError
from bd_tree.frontmatter import parse_document, render_document


def _split_section(text):
    """Split a body at the trailing ``## Links`` section marker."""
    marker = text.rfind("## Links")
    if marker == -1:
        return text, None
    return text[:marker], text[marker:]


def _doc(root, ref):
    return parse_document((root / "nodes" / f"{ref}.md").read_text(encoding="utf-8"))


def _split_doc(root, ref):
    """The node's body split into (outside-section bytes, section-or-None)."""
    return _split_section(_doc(root, ref).body)


def _pairs(root, ref):
    return [
        (link.to, link.type) for link in load(root).nodes[ref].links
    ]


def _legacy(nodes, node_id, **meta):
    """Write a versioned file still declaring ``links`` in front matter."""
    nodes.mkdir(parents=True, exist_ok=True)
    meta.setdefault("id", node_id)
    meta.setdefault("title", f"Node {node_id}")
    path = nodes / f"{node_id}-1.md"
    path.write_text(render_document(meta, "body\n"), encoding="utf-8", newline="")
    return path


def test_clone_creates_next_and_explicit_versions(write, tmp_path):
    write(tmp_path / "nodes", 1)
    assert clone(tmp_path, "1-1") == [("1-1", "1-2")]
    assert [node.ref for node in versions(tmp_path, 1)] == ["1-1", "1-2"]
    assert clone(tmp_path, 1) == [("1-1", "1-3")]
    assert clone(tmp_path, 1, version=4) == [("1-1", "1-4")]
    with pytest.raises(BreakdownError, match="already exists"):
        clone(tmp_path, 1, version=4)
    with pytest.raises(BreakdownError, match="does not exist"):
        clone(tmp_path, "9-1")


def test_clone_copies_declared_links(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2, links=[{"to": "3-1", "type": "breaks_down"}])
    write(nodes, 3)
    assert clone(tmp_path, "2-1") == [("2-1", "2-2")]
    path = nodes / "2-2.md"
    text = path.read_text(encoding="utf-8")
    # Byte copy: the token line survives untouched, unparsed.
    assert "- (Title of 3-1)[[3-1, breaks_down]]" in text
    assert load(tmp_path).children("2-2") == ["3-1"]
    assert check(tmp_path).ok

    # The copy keeps its own links; editing its peer changes nothing.
    write(nodes, 2, links=[{"to": "4-1", "type": "breaks_down"}])
    write(nodes, 4)
    assert load(tmp_path).children("2-2") == ["3-1"]


def test_clone_subtree_clones_the_whole_component_and_rewires(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2-1", "type": "breaks_down"}])
    write(
        nodes,
        2,
        links=[
            {"to": "3-1", "type": "breaks_down"},
            {"to": "4-1", "type": "breaks_down"},
        ],
    )
    write(nodes, 3, links=[{"to": "5-1", "type": "breaks_down"}])
    write(nodes, 4)
    write(nodes, 5)

    pairs = clone(tmp_path, "2-1", subtree=True)

    assert pairs == [
        ("2-1", "2-2"),
        ("1-1", "1-2"),
        ("3-1", "3-2"),
        ("4-1", "4-2"),
        ("5-1", "5-2"),
    ]
    assert load(tmp_path).children("1-2") == ["2-2"]
    assert load(tmp_path).children("2-2") == ["3-2", "4-2"]
    assert load(tmp_path).children("3-2") == ["5-2"]

    # Tokens among the copies are repointed; every other byte is preserved.
    head, section = _split_doc(tmp_path, "2-2")
    source_head, source_section = _split_doc(tmp_path, "2-1")
    assert head == source_head
    assert section == (
        "## Links\n\n- (Title of 3-1)[[3-2, breaks_down]]\n"
        "- (Title of 4-1)[[4-2, breaks_down]]\n"
    )
    assert source_section == (
        "## Links\n\n- (Title of 3-1)[[3-1, breaks_down]]\n"
        "- (Title of 4-1)[[4-1, breaks_down]]\n"
    )

    # The original component is untouched and the clone is not wired into it.
    assert load(tmp_path).children("2-1") == ["3-1", "4-1"]
    assert load(tmp_path).children("1-1") == ["2-1"]
    assert set(load_view(tmp_path, "1-1").nodes) == {
        "1-1",
        "2-1",
        "3-1",
        "4-1",
        "5-1",
    }


def test_clone_depth_materializes_rings(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2, links=[{"to": "3-1", "type": "breaks_down"}])
    write(nodes, 3, links=[{"to": "4-1", "type": "breaks_down"}])
    write(nodes, 4)

    pairs = clone(tmp_path, "2-1", depth=1)

    assert pairs == [("2-1", "2-2"), ("1-1", "1-2"), ("3-1", "3-2")]
    assert not (nodes / "4-2.md").exists()


def test_clone_subtree_refuses_explicit_version(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2)

    with pytest.raises(BreakdownError, match="cannot be combined"):
        clone(tmp_path, "1-1", version=2, subtree=True)
    with pytest.raises(BreakdownError, match="cannot be combined"):
        clone(tmp_path, "1-1", version=2, depth=1)


def test_clone_subtree_refuses_two_versions_of_one_id_in_the_component(
    write, tmp_path
):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[
            {"to": "2-1", "type": "breaks_down"},
            {"to": "2-2", "type": "breaks_down"},
        ],
    )
    write(nodes, 2, version=1)
    write(nodes, 2, version=2)

    with pytest.raises(BreakdownError, match="two versions of id 2"):
        clone(tmp_path, "1-1", subtree=True)


def test_replace_swaps_middle_child_in_place(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[
            {"to": "2-1", "type": "breaks_down"},
            {"to": "3-1", "type": "breaks_down"},
            {"to": "4-1", "type": "breaks_down"},
        ],
    )
    write(nodes, 2)
    write(nodes, 3)
    write(nodes, 4)

    assert clone(tmp_path, "3-1") == [("3-1", "3-2")]
    assert replace(tmp_path, "3-1", "3-2") == ("3-1", "links", "3-2")

    parent_text = (nodes / "1-1.md").read_text(encoding="utf-8")
    assert "[[3-2, breaks_down]]" in parent_text
    assert "[[3-1, breaks_down]]" not in parent_text
    assert load(tmp_path).children("1-1") == ["2-1", "3-2", "4-1"]
    assert (nodes / "3-1.md").is_file()
    assert (nodes / "3-2.md").is_file()

    assert check(tmp_path).ok


def test_replace_retitles_tokens_to_the_new_nodes_live_title(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[{"to": "3-1", "type": "breaks_down"}],
        body="old target\n",
    )
    write(nodes, 3, title="Old title")
    write(nodes, 3, version=2, title="New live title")

    assert replace(tmp_path, "3-1", "3-2") == ("3-1", "links", "3-2")

    text = (nodes / "1-1.md").read_text(encoding="utf-8")
    assert "- (New live title)[[3-2, breaks_down]]" in text
    assert "[[3-1, breaks_down]]" not in text


def test_component_clone_then_replace_repoints_parent_at_new_root(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2-1", "type": "breaks_down"}])
    write(
        nodes,
        2,
        links=[
            {"to": "3-1", "type": "breaks_down"},
            {"to": "4-1", "type": "breaks_down"},
        ],
    )
    write(nodes, 3)
    write(nodes, 4)

    pairs = clone(tmp_path, "2-1", subtree=True)
    assert pairs == [
        ("2-1", "2-2"),
        ("1-1", "1-2"),
        ("3-1", "3-2"),
        ("4-1", "4-2"),
    ]
    assert replace(tmp_path, "2-1", "2-2") == ("2-1", "links", "2-2")

    head, section = _split_doc(tmp_path, "1-1")
    assert head == "body\n\n"
    assert section == "## Links\n\n- (Title of 2-1)[[2-2, breaks_down]]\n"
    assert load(tmp_path).children("2-2") == ["3-2", "4-2"]

    assert check(tmp_path).ok
    # 1-1 and its peer 1-2 both point at 2-2, so one component holds both.
    assert set(load_view(tmp_path).nodes) == {"1-1", "1-2", "2-2", "3-2", "4-2"}


def test_replace_store_root_repoints_root_file(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2)

    assert clone(tmp_path, "1-1") == [("1-1", "1-2")]
    assert replace(tmp_path, "1-1", "1-2") == ("1-1", "ROOT", "1-2")

    assert (tmp_path / "ROOT").read_text(encoding="utf-8") == "1-2\n"
    assert load(tmp_path).root_ref == "1-2"

    assert check(tmp_path).ok
    # The component is undirected, so the peer 1-1 stays reachable.
    assert set(load_view(tmp_path).nodes) == {"1-1", "1-2", "2-1"}


def test_replace_outside_default_view_raises(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1)
    write(nodes, 9)

    assert clone(tmp_path, "9-1") == [("9-1", "9-2")]
    with pytest.raises(BreakdownError, match="not in view 1-1"):
        replace(tmp_path, "9", "9-2")


def test_replace_requires_an_inbound_link(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1)
    write(nodes, 9)

    assert clone(tmp_path, "9-1") == [("9-1", "9-2")]
    with pytest.raises(BreakdownError, match="no inbound links"):
        replace(tmp_path, "9-1", "9-2")


def test_replace_refuses_self_and_missing_refs(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2)

    with pytest.raises(BreakdownError, match="itself"):
        replace(tmp_path, "2-1", "2-1")
    with pytest.raises(BreakdownError, match="does not exist"):
        replace(tmp_path, "9-1", "2-1")
    with pytest.raises(BreakdownError, match="does not exist"):
        replace(tmp_path, "2-1", "9-1")


def test_delete_refuses_the_root_then_force(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2)

    with pytest.raises(BreakdownError, match="store root"):
        delete(tmp_path, "1-1")

    removed = delete(tmp_path, "1-1", force=True)
    assert removed == (nodes / "1-1.md").resolve()
    assert not (nodes / "1-1.md").exists()


def test_delete_refuses_an_inbound_target_and_lists_it(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2)

    with pytest.raises(BreakdownError, match="inbound target of 1-1"):
        delete(tmp_path, "2-1")

    delete(tmp_path, "2-1", force=True)
    assert not (nodes / "2-1.md").exists()


def test_delete_refuses_a_link_reference_then_force(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2)
    write(nodes, 3, links=[{"to": "4-1", "type": "supports"}])
    write(nodes, 4)

    with pytest.raises(BreakdownError, match="inbound target of 3-1"):
        delete(tmp_path, "4-1")

    delete(tmp_path, "4-1", force=True)
    assert not (nodes / "4-1.md").exists()


def test_delete_allows_an_unreferenced_peer_version(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2, version=1)
    write(nodes, 2, version=2)

    delete(tmp_path, "2-2")

    assert not (nodes / "2-2.md").exists()
    assert (nodes / "2-1.md").is_file()


def test_delete_allows_a_ref_with_only_outbound_links(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2)
    write(nodes, 3)

    delete(tmp_path, "3-1")

    assert not (nodes / "3-1.md").exists()
    assert (nodes / "1-1.md").is_file()


def test_diff_views_by_id(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[
            {"to": "2-1", "type": "breaks_down"},
            {"to": "3-1", "type": "breaks_down"},
        ],
    )
    write(nodes, 2, version=1, links=[{"to": "4-1", "type": "breaks_down"}])
    write(nodes, 3)
    write(nodes, 4)
    write(nodes, 2, version=2, links=[{"to": "5-1", "type": "breaks_down"}])
    write(nodes, 5)
    entries = {entry.id: entry.state for entry in diff(tmp_path, "1-1", "2-2")}
    # Links now live in bodies, so the two versions of id 2 differ in content.
    assert entries == {
        1: "only-left",
        2: "changed",
        3: "only-left",
        4: "only-left",
        5: "only-right",
    }


def test_new_uses_next_global_id_and_appends_to_parent(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[{"to": "2-1", "type": "breaks_down"}],
        body="root body\n",
    )
    write(nodes, 2)
    created = new_node(
        tmp_path,
        parent="1",
        fields={"type": "claim", "title": "New claim", "summary": ""},
    )
    assert created.name == "3-1.md"
    head, section = _split_doc(tmp_path, "1-1")
    assert head == "root body\n\n"  # parent body preserved outside the section
    assert section == (
        "## Links\n\n- (Title of 2-1)[[2-1, breaks_down]]\n"
        "- (New claim)[[3-1, breaks_down]]\n"
    )  # title is the new node's live title
    assert load(tmp_path).children("1-1") == ["2-1", "3-1"]

    second = new_node(
        tmp_path,
        parent="2",
        fields={"type": "claim", "title": "Under 2"},
    )
    assert second.name == "4-1.md"
    assert load(tmp_path).children("2-1") == ["4-1"]


def test_new_seeds_empty_title_and_summary_without_placement(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1)
    created = new_node(tmp_path, parent="1")
    doc = parse_document(created.read_text(encoding="utf-8"))
    assert doc.meta["id"] == 2
    assert doc.meta["title"] == ""
    assert doc.meta["summary"] == ""
    for retired in ("band", "subpath", "layer", "stage", "order"):
        assert retired not in doc.meta

    overridden = new_node(
        tmp_path,
        parent="1",
        fields={"title": "X", "summary": "Y"},
    )
    meta = parse_document(overridden.read_text(encoding="utf-8")).meta
    assert meta["title"] == "X"
    assert meta["summary"] == "Y"


def test_new_without_parent_starts_its_own_component(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1)
    created = new_node(tmp_path, fields={"title": "Lone"})

    assert created.name == "2-1.md"
    assert load(tmp_path).children("1-1") == []
    components = load(tmp_path).components()
    assert components == [["1-1"], ["2-1"]]


def test_new_appends_to_the_parent_version_only(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[{"to": "2-1", "type": "breaks_down"}],
    )
    write(nodes, 2, links=[{"to": "3-1", "type": "breaks_down"}])
    write(nodes, 3)
    clone(tmp_path, "2-1")
    created = new_node(
        tmp_path,
        parent="2-2",
        fields={"type": "claim", "title": "Version child"},
    )
    assert created.name == "4-1.md"
    assert load(tmp_path).children("2-1") == ["3-1"]
    assert load(tmp_path).children("2-2") == ["3-1", "4-1"]
    head, section = _split_doc(tmp_path, "2-2")
    assert head == "body\n\n"
    assert section == (
        "## Links\n\n- (Title of 3-1)[[3-1, breaks_down]]\n"
        "- (Version child)[[4-1, breaks_down]]\n"
    )


def test_new_rejects_missing_parent(write, tmp_path):
    write(tmp_path / "nodes", 1)
    with pytest.raises(BreakdownError, match="does not exist"):
        new_node(tmp_path, parent="9-1", fields={"title": "x"})


def test_new_does_not_derive_folder(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1)
    by_type = new_node(
        tmp_path,
        parent="1",
        fields={"type": "build", "title": "Build Step"},
    )
    type_meta = parse_document(by_type.read_text(encoding="utf-8")).meta
    assert "folder" not in type_meta

    by_group = new_node(
        tmp_path,
        parent="1",
        fields={"group": "g", "title": "Grouped"},
    )
    group_meta = parse_document(by_group.read_text(encoding="utf-8")).meta
    assert "folder" not in group_meta

    explicit_home = new_node(
        tmp_path,
        parent="1",
        fields={"type": "build", "home": "custom/here.md", "title": "Explicit Home"},
    )
    home_meta = parse_document(explicit_home.read_text(encoding="utf-8")).meta
    assert home_meta["home"] == "custom/here.md"
    assert "folder" not in home_meta

    explicit_folder = new_node(
        tmp_path,
        parent="1",
        fields={"type": "build", "folder": "picked", "title": "Explicit Folder"},
    )
    folder_meta = parse_document(explicit_folder.read_text(encoding="utf-8")).meta
    assert folder_meta["folder"] == "picked"


def test_link_allows_back_edges_reciprocals_and_cycles(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2, links=[{"to": "3-1", "type": "breaks_down"}])
    write(nodes, 3, links=[{"to": "1-1", "type": "breaks_down"}])

    # A back-edge from the deepest node to the root is legal.
    assert link(tmp_path, "2-1", "1-1", link_type="supports")
    # A reciprocal structural edge is legal too.
    assert link(tmp_path, "3-1", "2-1", link_type="breaks_down")
    # The cycle closes and the store stays valid.
    assert set(load(tmp_path).children("2-1")) == {"1-1", "3-1"}
    assert check(tmp_path).ok


def test_link_refuses_a_self_loop(write, tmp_path):
    write(tmp_path / "nodes", 1)
    with pytest.raises(BreakdownError, match="self-loop"):
        link(tmp_path, "1-1", "1-1", link_type="supports")


def test_link_appends_tokens_in_call_order(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1)
    write(nodes, 2)
    write(nodes, 3)
    write(nodes, 4)
    link(tmp_path, "1-1", "3-1", link_type="supports")
    link(tmp_path, "1-1", "2-1", link_type="supports")
    _, section = _split_doc(tmp_path, "1-1")
    assert section == (
        "## Links\n- (Title of 3-1)[[3-1, supports]]\n"
        "- (Title of 2-1)[[2-1, supports]]\n"
    )
    # Monotone appends keep the section sorted by ref.
    link(tmp_path, "1-1", "4-1", link_type="supports")
    _, section = _split_doc(tmp_path, "1-1")
    assert section.endswith("- (Title of 4-1)[[4-1, supports]]\n")


def test_link_refuses_a_type_that_cannot_be_a_token(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1)
    write(nodes, 2)
    with pytest.raises(BreakdownError, match="body token"):
        link(tmp_path, "1-1", "2-1", link_type="has space")
    assert _split_doc(tmp_path, "1-1")[1] is None


def test_folder_front_matter_survives_a_rewrite(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, folder="x", title="Carrier")
    write(nodes, 2)
    path = nodes / "1-1.md"
    before = path.read_text(encoding="utf-8")
    assert "folder: x" in before

    link(tmp_path, "1-1", "2-1", link_type="supports")

    after = path.read_text(encoding="utf-8")
    assert "folder: x" in after
    assert parse_document(after).meta["folder"] == "x"


def _classic(nodes, node_id, *, contains=None, links=None, body="body\n", **extra):
    """Write a classic bare ``<id>.md`` file for migration tests."""
    nodes.mkdir(parents=True, exist_ok=True)
    meta = {"id": node_id, "title": f"Node {node_id}"}
    meta.update(extra)
    if contains is not None:
        meta["contains"] = contains
    if links is not None:
        meta["links"] = links
    path = nodes / f"{node_id}.md"
    path.write_text(render_document(meta, body), encoding="utf-8", newline="")
    return path


def test_migrate_dry_run_prints_the_plan_without_touching_disk(tmp_path):
    nodes = tmp_path / "nodes"
    _classic(nodes, 1, contains=[2], band="root", order=0)
    _classic(nodes, 2)
    (tmp_path / "ROOT").write_text("1\n", encoding="utf-8")

    result = migrate(tmp_path, dry_run=True)

    assert result.dry_run is True
    assert result.count == 2
    assert result.renames == [
        ("nodes/1.md", "nodes/1-1.md"),
        ("nodes/2.md", "nodes/2-1.md"),
    ]
    assert any("contains" in rewrite for rewrite in result.rewrites)
    assert any("strip band, order" in rewrite for rewrite in result.rewrites)
    assert any(rewrite.startswith("ROOT:") for rewrite in result.rewrites)
    assert (nodes / "1.md").is_file()
    assert (nodes / "2.md").is_file()
    assert not (nodes / "1-1.md").exists()
    assert (tmp_path / "ROOT").read_text(encoding="utf-8") == "1\n"


def test_migrate_renames_rewrites_and_is_idempotent(write, tmp_path):
    nodes = tmp_path / "nodes"
    body = "# Node 1\n\nBody mentions contains: [2] and must stay put.\n"
    path = _classic(nodes, 1, contains=[2], body=body, layout="flat")
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "---\nid: 1\n", "---\n# keep this comment\nid: 1\n"
        ),
        encoding="utf-8",
    )
    _classic(nodes, 2)
    write(nodes, 2, version=2)
    (tmp_path / "ROOT").write_text("1\n", encoding="utf-8")

    result = migrate(tmp_path)

    assert result.dry_run is False
    assert not (nodes / "1.md").exists()
    assert not (nodes / "2.md").exists()
    assert (nodes / "1-1.md").is_file()
    assert (nodes / "2-1.md").is_file()
    assert (nodes / "2-2.md").is_file()
    migrated_text = (nodes / "1-1.md").read_text(encoding="utf-8")
    assert "# keep this comment" in migrated_text
    migrated = parse_document(migrated_text)
    assert "contains" not in migrated.meta
    assert "links" not in migrated.meta
    assert migrated.meta["layout"] == "flat"
    # Body preserved; the conversion only appends the trailing token section.
    assert migrated.body == body + "\n## Links\n- (Node 2)[[2-1, breaks_down]]\n"
    assert (tmp_path / "ROOT").read_text(encoding="utf-8") == "1-1\n"

    store = load(tmp_path)
    assert store.root_ref == "1-1"
    assert store.children("1-1") == ["2-1"]

    again = migrate(tmp_path)
    assert again.count == 0
    assert again.rewrites == []


def test_migrate_strips_retired_placement_keys(tmp_path):
    nodes = tmp_path / "nodes"
    nodes.mkdir(parents=True)
    layout = {
        1: {
            "contains": ["2-1", "3-1"],
            "section": "00-intent",
            "band": "intent",
            "order": 0,
            "band_layout": "flat",
            "band_order": ["intent", "claims"],
        },
        2: {
            "contains": ["4-1"],
            "section": "00-claims",
            "band": "claims",
            "subpath": "nested",
            "layer": "legacy",
            "order": 1,
        },
        3: {"section": "00-claims", "band": "claims", "stage": 2, "order": 2},
        4: {"section": "00-evidence/suggested", "band": "evidence", "order": 3},
    }
    for node_id, extra in layout.items():
        meta = {"id": node_id, "title": f"Node {node_id}", **extra}
        (nodes / f"{node_id}-1.md").write_text(
            render_document(meta, "body\n"), encoding="utf-8", newline=""
        )
    (tmp_path / "ROOT").write_text("1-1\n", encoding="utf-8")

    result = migrate(tmp_path)

    for node_id in (1, 2, 3, 4):
        meta = parse_document(
            (nodes / f"{node_id}-1.md").read_text(encoding="utf-8")
        ).meta
        for retired in ("band", "subpath", "layer", "stage", "order"):
            assert retired not in meta, (node_id, retired)
        assert "section" in meta
        assert "links" not in meta, node_id

    first_meta = _doc(tmp_path, "1-1").meta
    assert "band_layout" not in first_meta
    assert "band_order" not in first_meta
    assert "contains" not in first_meta
    head, section = _split_doc(tmp_path, "1-1")
    assert head == "body\n\n"
    assert section == (
        "## Links\n- (Node 2)[[2-1, breaks_down]]\n"
        "- (Node 3)[[3-1, breaks_down]]\n"
    )
    assert any("strip" in rewrite for rewrite in result.rewrites)

    report = check(tmp_path)
    assert report.ok
    assert not any(issue.code == "contains-removed" for issue in report.issues)

    again = migrate(tmp_path)
    assert again.count == 0
    assert again.rewrites == []


def test_migrate_cli_converts_front_matter_links_to_tokens(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    _legacy(
        nodes,
        1,
        band="root",
        section="00-root",
        links=[
            {"to": "2-1", "type": "realizes"},
            {"to": "3-1", "type": "implements"},
        ],
    )
    _legacy(nodes, 2, band="intent", section="00-intent")
    _legacy(nodes, 3, band="product", section="01-product")
    args = ["migrate", "--root", str(tmp_path)]

    assert main(args) == 0

    root_doc = _doc(tmp_path, "1-1")
    assert "links" not in root_doc.meta
    assert "band" not in root_doc.meta
    assert "band_order" not in root_doc.meta
    assert "band_layout" not in root_doc.meta
    head, section = _split_doc(tmp_path, "1-1")
    assert head == "body\n\n"
    assert section == (
        "## Links\n- (Node 2)[[2-1, realizes]]\n"
        "- (Node 3)[[3-1, implements]]\n"
    )
    assert _pairs(tmp_path, "1-1") == [
        ("2-1", "realizes"),
        ("3-1", "implements"),
    ]

    capsys.readouterr()
    assert main(args) == 0
    assert "migrated: 0 renames, 0 rewrites" in capsys.readouterr().out


def test_migrate_fails_on_an_ambiguous_bare_ref(tmp_path):
    nodes = tmp_path / "nodes"
    _classic(nodes, 1, contains=[2])

    with pytest.raises(BreakdownError, match="ambiguous"):
        migrate(tmp_path)

    assert (nodes / "1.md").is_file()
    assert not (nodes / "1-1.md").exists()


def test_migrate_converts_legacy_suffix_tokens_and_fills_titles(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        body=(
            "Prose [[breaks_down, 2-1]](Stale title), bare [[supports, 3-1]], "
            "dangling [[9-1, verifies]].\n"
        ),
    )
    write(nodes, 2, title="Live title")
    write(nodes, 3, title="Third")
    before = (nodes / "1-1.md").read_text(encoding="utf-8")

    dry = migrate(tmp_path, dry_run=True)

    assert dry.dry_run is True
    assert (nodes / "1-1.md").read_text(encoding="utf-8") == before
    assert any("suffix tokens -> prefix" in line for line in dry.rewrites)

    result = migrate(tmp_path)

    body = _doc(tmp_path, "1-1").body
    assert "(Live title)[[2-1, breaks_down]]" in body
    assert "(Third)[[3-1, supports]]" in body
    assert "(9-1)[[9-1, verifies]]" in body  # dangling target falls back to ref
    assert "Stale title" not in body
    assert "[[breaks_down, 2-1]](Stale title)" not in body
    assert any("suffix tokens -> prefix" in line for line in result.rewrites)

    again = migrate(tmp_path)
    assert again.rewrites == []


def test_migrate_normalizes_component_order(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        body=(
            "Type-first bare [[breaks_down, 2-1]], "
            "ref-first suffix [[3-1, supports]](Stale suffix title).\n"
        ),
    )
    write(nodes, 2, title="Second")
    write(nodes, 3, title="Third")

    dry = migrate(tmp_path, dry_run=True)
    assert any("tokens -> ref-first order" in line for line in dry.rewrites)

    result = migrate(tmp_path)

    body = _doc(tmp_path, "1-1").body
    assert "(Second)[[2-1, breaks_down]]" in body
    assert "(Third)[[3-1, supports]]" in body
    assert "[[breaks_down, 2-1]]" not in body
    assert "Stale suffix title" not in body
    assert result.rewrites

    assert migrate(tmp_path, dry_run=True).rewrites == []


def test_migrate_normalizes_a_type_first_links_line(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, body="body\n\n## Links\n- [[supports, 2-1]]\n")
    write(nodes, 2, title="Second")

    migrate(tmp_path)

    section = _split_doc(tmp_path, "1-1")[1]
    assert section == "## Links\n- (Second)[[2-1, supports]]\n"


def test_retitle_fills_and_refreshes_titles_in_prose_and_links(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        body=(
            "Prose (Stale)[[2-1, breaks_down]].\n\n"
            "## Links\n- [[3-1, supports]]\n- [[9-1, verifies]]\n"
        ),
    )
    write(nodes, 2, title="Live title")
    write(nodes, 3, title="Third")
    before = (nodes / "1-1.md").read_text(encoding="utf-8")

    dry = retitle(tmp_path, dry_run=True)

    assert dry.dry_run is True
    assert dry.changed == 2
    assert dry.nodes == ["1-1"]
    assert (nodes / "1-1.md").read_text(encoding="utf-8") == before

    result = retitle(tmp_path)

    body = _doc(tmp_path, "1-1").body
    assert "(Live title)[[2-1, breaks_down]]" in body
    assert "- (Third)[[3-1, supports]]" in body
    assert "[[9-1, verifies]]" in body  # unresolved target left untouched
    assert "(9-1)" not in body
    assert result.changed == 2 and result.dry_run is False

    assert retitle(tmp_path).changed == 0


def test_retitle_view_scope_touches_only_that_component(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, body="(Old)[[2-1, breaks_down]]\n")
    write(nodes, 2, title="Two")
    write(nodes, 9, body="(Old)[[10-1, breaks_down]]\n")
    write(nodes, 10, title="Ten")

    scoped = retitle(tmp_path, view="1-1")

    assert scoped.nodes == ["1-1"]
    assert "(Two)[[2-1, breaks_down]]" in _doc(tmp_path, "1-1").body
    assert "(Old)[[10-1, breaks_down]]" in _doc(tmp_path, "9-1").body

    whole = retitle(tmp_path)
    assert whole.nodes == ["9-1"]
    assert "(Ten)[[10-1, breaks_down]]" in _doc(tmp_path, "9-1").body

