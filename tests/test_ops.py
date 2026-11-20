from __future__ import annotations

import pytest

from bd_tree.api import (
    clone,
    delete,
    diff,
    link,
    load,
    migrate,
    new_node,
    replace,
    versions,
)
from bd_tree.errors import BreakdownError
from bd_tree.frontmatter import parse_document, render_document


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


def test_clone_copies_declared_containment(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2, contains=["3"])
    write(nodes, 3)
    assert clone(tmp_path, "2-1") == [("2-1", "2-2")]
    path = nodes / "2-2.md"
    assert parse_document(path.read_text(encoding="utf-8")).meta["contains"] == ["3-1"]
    assert set(load(tmp_path).effective_contains("2-2")) == {"3-1"}

    from bd_tree.api import check, load_view

    assert check(tmp_path).ok
    assert set(load_view(tmp_path, "2-2").nodes) == {"2-2", "3-1"}

    # The copy keeps its own declared list; editing its peer changes nothing.
    write(nodes, 2, contains=["4"])
    write(nodes, 4)
    assert set(load(tmp_path).effective_contains("2-2")) == {"3-1"}


def test_clone_subtree_rewires_descendants_in_order(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2, contains=["3", "4"])
    write(nodes, 3, contains=["5"])
    write(nodes, 4)
    write(nodes, 5)

    pairs = clone(tmp_path, "2-1", subtree=True)

    assert pairs == [
        ("2-1", "2-2"),
        ("3-1", "3-2"),
        ("5-1", "5-2"),
        ("4-1", "4-2"),
    ]
    root_copy = parse_document((nodes / "2-2.md").read_text(encoding="utf-8"))
    assert root_copy.meta["contains"] == ["3-2", "4-2"]
    child_copy = parse_document((nodes / "3-2.md").read_text(encoding="utf-8"))
    assert child_copy.meta["contains"] == ["5-2"]

    # The original tree is untouched and the clone is not wired into it.
    original = parse_document((nodes / "2-1.md").read_text(encoding="utf-8"))
    assert original.meta["contains"] == ["3-1", "4-1"]
    assert set(load(tmp_path).effective_contains("1-1")) == {"2-1"}

    from bd_tree.api import load_view

    assert set(load_view(tmp_path, "1-1").nodes) == {
        "1-1",
        "2-1",
        "3-1",
        "4-1",
        "5-1",
    }


def test_clone_subtree_refuses_explicit_version(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2)

    with pytest.raises(BreakdownError, match="cannot be combined with --subtree"):
        clone(tmp_path, "1-1", version=2, subtree=True)


def test_clone_subtree_refuses_two_versions_of_one_id_in_the_view(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2-1", "2-2"])
    write(nodes, 2, version=1)
    write(nodes, 2, version=2)

    with pytest.raises(BreakdownError, match="two versions of id 2"):
        clone(tmp_path, "1-1", subtree=True)


def test_replace_swaps_middle_child_in_place(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3", "4"])
    write(nodes, 2)
    write(nodes, 3)
    write(nodes, 4)

    assert clone(tmp_path, "3-1") == [("3-1", "3-2")]
    assert replace(tmp_path, "3-1", "3-2") == ("3-1", "1-1", "3-2")

    parent = parse_document((nodes / "1-1.md").read_text(encoding="utf-8"))
    assert parent.meta["contains"] == ["2-1", "3-2", "4-1"]
    assert (nodes / "3-1.md").is_file()
    assert (nodes / "3-2.md").is_file()

    from bd_tree.api import check

    assert check(tmp_path).ok


def test_subtree_clone_then_replace_repoints_parent_at_new_root(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2, contains=["3", "4"])
    write(nodes, 3)
    write(nodes, 4)

    pairs = clone(tmp_path, "2-1", subtree=True)
    assert pairs == [("2-1", "2-2"), ("3-1", "3-2"), ("4-1", "4-2")]
    assert replace(tmp_path, "2-1", "2-2") == ("2-1", "1-1", "2-2")

    parent = parse_document((nodes / "1-1.md").read_text(encoding="utf-8"))
    assert parent.meta["contains"] == ["2-2"]
    root_copy = parse_document((nodes / "2-2.md").read_text(encoding="utf-8"))
    assert root_copy.meta["contains"] == ["3-2", "4-2"]

    from bd_tree.api import check, load_view

    assert check(tmp_path).ok
    assert set(load_view(tmp_path).nodes) == {"1-1", "2-2", "3-2", "4-2"}


def test_replace_store_root_repoints_root_file(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2)

    assert clone(tmp_path, "1-1") == [("1-1", "1-2")]
    assert replace(tmp_path, "1-1", "1-2") == ("1-1", "ROOT", "1-2")

    assert (tmp_path / "ROOT").read_text(encoding="utf-8") == "1-2\n"
    assert load(tmp_path).root_ref == "1-2"

    from bd_tree.api import check, load_view

    assert check(tmp_path).ok
    assert set(load_view(tmp_path).nodes) == {"1-2", "2-1"}


def test_replace_outside_default_view_raises(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1)
    write(nodes, 9)

    assert clone(tmp_path, "9-1") == [("9-1", "9-2")]
    with pytest.raises(BreakdownError, match="not in the default view"):
        replace(tmp_path, "9-1", "9-2")


def test_replace_refuses_self_and_missing_refs(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2)

    with pytest.raises(BreakdownError, match="itself"):
        replace(tmp_path, "2-1", "2-1")
    with pytest.raises(BreakdownError, match="does not exist"):
        replace(tmp_path, "9-1", "2-1")
    with pytest.raises(BreakdownError, match="does not exist"):
        replace(tmp_path, "2-1", "9-1")


def test_delete_refuses_root_and_reachable_refs_then_force(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2)

    with pytest.raises(BreakdownError, match="store root"):
        delete(tmp_path, "1-1")
    with pytest.raises(BreakdownError, match="reachable"):
        delete(tmp_path, "2-1")

    removed = delete(tmp_path, "2-1", force=True)
    assert removed == (nodes / "2-1.md").resolve()
    assert not (nodes / "2-1.md").exists()


def test_delete_refuses_a_link_reference_then_force(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2)
    write(nodes, 3, links=[{"to": "4", "type": "supports"}])
    write(nodes, 4)

    with pytest.raises(BreakdownError, match="referenced by 3-1"):
        delete(tmp_path, "4-1")

    delete(tmp_path, "4-1", force=True)
    assert not (nodes / "4-1.md").exists()


def test_delete_allows_an_unreferenced_peer_version(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2)
    write(nodes, 2, version=2)

    delete(tmp_path, "2-2")

    assert not (nodes / "2-2.md").exists()
    assert (nodes / "2-1.md").is_file()


def test_diff_views_by_id(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"])
    write(nodes, 2, contains=["4"])
    write(nodes, 3)
    write(nodes, 4)
    write(nodes, 2, version=2, contains=["5"])
    write(nodes, 5)
    entries = {entry.id: entry.state for entry in diff(tmp_path, "1-1", "2-2")}
    assert entries == {
        1: "only-left",
        2: "same",
        3: "only-left",
        4: "only-left",
        5: "only-right",
    }


def test_new_uses_next_global_id_and_appends_to_parent(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], body="root body\n")
    write(nodes, 2)
    created = new_node(
        tmp_path,
        parent="1",
        fields={"type": "claim", "layer": "claims", "title": "New claim", "summary": ""},
    )
    assert created.name == "3-1.md"
    root = parse_document((nodes / "1-1.md").read_text(encoding="utf-8"))
    assert root.meta["contains"] == ["2-1", "3-1"]
    assert root.body == "root body\n"
    assert load(tmp_path).effective_contains("1-1") == ["2-1", "3-1"]

    second = new_node(
        tmp_path, parent="2", fields={"type": "claim", "layer": "claims", "title": "Under 2"}
    )
    assert second.name == "4-1.md"
    assert load(tmp_path).effective_contains("2-1") == ["4-1"]


def test_new_seeds_empty_title_and_summary_and_fields_override(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=[])
    created = new_node(tmp_path, parent="1")
    doc = parse_document(created.read_text(encoding="utf-8"))
    assert doc.meta == {"id": 2, "title": "", "summary": ""}
    assert list(doc.meta) == ["id", "title", "summary"]

    from bd_tree.api import export_view

    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out)
    assert (out / "2-1.md").is_file()

    overridden = new_node(
        tmp_path, parent="1", fields={"title": "X", "summary": "Y"}
    )
    meta = parse_document(overridden.read_text(encoding="utf-8")).meta
    assert meta["title"] == "X"
    assert meta["summary"] == "Y"


def test_new_appends_to_the_parent_version_only(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2, contains=["3"])
    write(nodes, 3)
    clone(tmp_path, "2-1")
    created = new_node(
        tmp_path,
        parent="2-2",
        fields={"type": "claim", "layer": "claims", "title": "Version child"},
    )
    assert created.name == "4-1.md"
    assert load(tmp_path).effective_contains("2-1") == ["3-1"]
    assert load(tmp_path).effective_contains("2-2") == ["3-1", "4-1"]
    version_meta = parse_document((nodes / "2-2.md").read_text(encoding="utf-8"))
    assert version_meta.meta["contains"] == ["3-1", "4-1"]


def test_new_rejects_missing_parent(write, tmp_path):
    write(tmp_path / "nodes", 1)
    with pytest.raises(BreakdownError, match="does not exist"):
        new_node(tmp_path, parent="9-1", fields={"layer": "intent", "title": "x"})


def test_new_does_not_derive_folder_and_renders_title_slug(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=[])
    by_type = new_node(
        tmp_path, parent="1", fields={"type": "build", "title": "Build Step"}
    )
    type_meta = parse_document(by_type.read_text(encoding="utf-8")).meta
    assert "folder" not in type_meta

    by_group = new_node(
        tmp_path, parent="1", fields={"group": "g", "title": "Grouped"}
    )
    group_meta = parse_document(by_group.read_text(encoding="utf-8")).meta
    assert "folder" not in group_meta

    flat = new_node(
        tmp_path, parent="1", fields={"phase": "build", "title": "Flat"}
    )
    flat_meta = parse_document(flat.read_text(encoding="utf-8")).meta
    assert "folder" not in flat_meta

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

    from bd_tree.api import export_view

    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out)
    assert (out / "2-1-build-step.md").is_file()
    assert (out / "3-1-grouped.md").is_file()
    assert (out / "4-1-flat.md").is_file()
    assert (out / "5-1-explicit-home.md").is_file()
    assert not (out / "custom" / "here.md").exists()
    assert (out / "6-1-explicit-folder.md").is_file()
    assert not (out / "picked").exists()


def test_folder_front_matter_survives_a_rewrite(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2, folder="x", title="Carrier")
    path = nodes / "2-1.md"
    before = path.read_text(encoding="utf-8")
    assert "folder: x" in before

    link(tmp_path, "2-1", "1-1", link_type="supports")

    after = path.read_text(encoding="utf-8")
    assert "folder: x" in after
    assert parse_document(after).meta["folder"] == "x"


def _classic(nodes, node_id, *, contains=None, links=None, body="body\n"):
    """Write a classic bare ``<id>.md`` file for migration tests."""
    nodes.mkdir(parents=True, exist_ok=True)
    meta = {"id": node_id, "title": f"Node {node_id}"}
    if contains is not None:
        meta["contains"] = contains
    if links is not None:
        meta["links"] = links
    path = nodes / f"{node_id}.md"
    path.write_text(render_document(meta, body), encoding="utf-8", newline="")
    return path


def test_migrate_dry_run_prints_the_plan_without_touching_disk(tmp_path):
    nodes = tmp_path / "nodes"
    _classic(nodes, 1, contains=[2])
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
    assert any(rewrite.startswith("ROOT:") for rewrite in result.rewrites)
    assert (nodes / "1.md").is_file()
    assert (nodes / "2.md").is_file()
    assert not (nodes / "1-1.md").exists()
    assert (tmp_path / "ROOT").read_text(encoding="utf-8") == "1\n"


def test_migrate_renames_rewrites_and_is_idempotent(write, tmp_path):
    nodes = tmp_path / "nodes"
    body = "# Node 1\n\nBody mentions contains: [2] and must stay put.\n"
    path = _classic(nodes, 1, contains=[2], body=body)
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
    assert migrated.meta["contains"] == ["2-1"]
    assert migrated.body == body
    assert (tmp_path / "ROOT").read_text(encoding="utf-8") == "1-1\n"

    store = load(tmp_path)
    assert store.root_ref == "1-1"
    assert store.effective_contains("1-1") == ["2-1"]

    again = migrate(tmp_path)
    assert again.count == 0
    assert again.rewrites == []


def test_migrate_fails_on_an_ambiguous_bare_ref(tmp_path):
    nodes = tmp_path / "nodes"
    _classic(nodes, 1, contains=[2])

    with pytest.raises(BreakdownError, match="ambiguous"):
        migrate(tmp_path)

    assert (nodes / "1.md").is_file()
    assert not (nodes / "1-1.md").exists()
