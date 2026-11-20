from __future__ import annotations

import pytest

from bd_tree.api import (
    diff,
    fork,
    load,
    new_node,
    promote,
    retire_version,
    versions,
)
from bd_tree.errors import BreakdownError
from bd_tree.frontmatter import parse_document


def test_fork_creates_next_and_explicit_versions(write, tmp_path):
    write(tmp_path / "nodes", 1)
    created = fork(tmp_path, "1")
    assert created.name == "1-1.md"
    assert [node.ref for node in versions(tmp_path, 1)] == ["1", "1-1"]
    assert fork(tmp_path, 1).name == "1-2.md"
    assert fork(tmp_path, 1, version=4).name == "1-4.md"
    with pytest.raises(BreakdownError, match="already exists"):
        fork(tmp_path, 1, version=4)
    with pytest.raises(BreakdownError, match="not found"):
        fork(tmp_path, 9)


def test_fork_materialises_containment(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2, contains=["3"])
    write(nodes, 3)
    path = fork(tmp_path, 2)
    assert parse_document(path.read_text(encoding="utf-8")).meta["contains"] == ["3"]
    assert set(load(tmp_path).effective_contains("2-1")) == {"3"}
    from bd_tree.api import check, load_view

    assert check(tmp_path).ok
    assert set(load_view(tmp_path, "2-1").nodes) == {"2-1", "3"}

    # A materialised list must not follow later edits to main.
    write(nodes, 2, contains=["4"])
    write(nodes, 4)
    assert set(load(tmp_path).effective_contains("2-1")) == {"3"}


def test_promote_preserves_effective_containment(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2, contains=["3"])
    write(nodes, 3)
    fork(tmp_path, 2)
    promote(tmp_path, "2-1")
    meta = parse_document((nodes / "2.md").read_text(encoding="utf-8")).meta
    assert meta["contains"] == ["3"]

    write(nodes, 2, version=1, contains=["4"])
    write(nodes, 4)
    promote(tmp_path, "2-1", keep=True)
    meta = parse_document((nodes / "2.md").read_text(encoding="utf-8")).meta
    assert meta["contains"] == ["4"]
    kept = parse_document((nodes / "2-1.md").read_text(encoding="utf-8")).meta
    assert "contains" not in kept


def test_promote_copies_onto_main_and_retire_version(write, tmp_path):
    write(tmp_path / "nodes", 1, body="main\n")
    write(tmp_path / "nodes", 1, version=1, body="version one\n")
    promote(tmp_path, "1-1")
    assert (tmp_path / "nodes" / "1.md").read_text(encoding="utf-8").endswith("version one\n")
    assert not (tmp_path / "nodes" / "1-1.md").exists()

    write(tmp_path / "nodes", 1, version=2, body="version two\n")
    promote(tmp_path, "1-2", keep=True)
    assert (tmp_path / "nodes" / "1.md").read_text(encoding="utf-8").endswith("version two\n")
    assert (tmp_path / "nodes" / "1-2.md").is_file()
    retire_version(tmp_path, "1-2")
    assert not (tmp_path / "nodes" / "1-2.md").exists()
    with pytest.raises(BreakdownError, match="main version"):
        retire_version(tmp_path, "1")


def test_diff_views_by_id(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"])
    write(nodes, 2, contains=["4"])
    write(nodes, 3)
    write(nodes, 4)
    write(nodes, 2, version=1, contains=["5"])
    write(nodes, 5)
    entries = {entry.id: entry.state for entry in diff(tmp_path, "1", "2-1")}
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
    assert created.name == "3.md"
    root = parse_document((nodes / "1.md").read_text(encoding="utf-8"))
    assert root.meta["contains"] == ["2", "3"]
    assert root.body == "root body\n"
    assert load(tmp_path).effective_contains("1") == ["2", "3"]

    second = new_node(
        tmp_path, parent="2", fields={"type": "claim", "layer": "claims", "title": "Under 2"}
    )
    assert second.name == "4.md"
    assert load(tmp_path).effective_contains("2") == ["4"]


def test_new_seeds_empty_title_and_summary_and_fields_override(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=[])
    created = new_node(tmp_path, parent="1")
    doc = parse_document(created.read_text(encoding="utf-8"))
    assert doc.meta == {"id": 2, "title": "", "summary": ""}
    assert list(doc.meta) == ["id", "title", "summary"]

    from bd_tree.api import export_view

    out = tmp_path / "view"
    export_view("tree", tmp_path, "1", out)
    assert (out / "2.md").is_file()

    overridden = new_node(
        tmp_path, parent="1", fields={"title": "X", "summary": "Y"}
    )
    meta = parse_document(overridden.read_text(encoding="utf-8")).meta
    assert meta["title"] == "X"
    assert meta["summary"] == "Y"


def test_new_materializes_inherited_contains_on_a_version(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2, contains=["3"])
    write(nodes, 3)
    write(nodes, 2, version=1)
    created = new_node(
        tmp_path,
        parent="2-1",
        fields={"type": "claim", "layer": "claims", "title": "Version child"},
    )
    assert created.name == "4.md"
    assert load(tmp_path).effective_contains("2") == ["3"]
    assert load(tmp_path).effective_contains("2-1") == ["3", "4"]
    version_meta = parse_document((nodes / "2-1.md").read_text(encoding="utf-8"))
    assert version_meta.meta["contains"] == ["3", "4"]


def test_new_rejects_missing_parent(write, tmp_path):
    write(tmp_path / "nodes", 1)
    with pytest.raises(BreakdownError, match="does not exist"):
        new_node(tmp_path, parent="9", fields={"layer": "intent", "title": "x"})


def test_new_derives_folder_from_group_fields_and_renders_title_slug(
    write, tmp_path
):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=[])
    by_type = new_node(
        tmp_path, parent="1", fields={"type": "build", "title": "Build Step"}
    )
    type_meta = parse_document(by_type.read_text(encoding="utf-8")).meta
    assert type_meta["folder"] == "build"

    by_group = new_node(
        tmp_path, parent="1", fields={"group": "g", "title": "Grouped"}
    )
    group_meta = parse_document(by_group.read_text(encoding="utf-8")).meta
    assert group_meta["folder"] == "g"

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
    assert home_meta["folder"] == "build"

    explicit_folder = new_node(
        tmp_path,
        parent="1",
        fields={"type": "build", "folder": "picked", "title": "Explicit Folder"},
    )
    folder_meta = parse_document(explicit_folder.read_text(encoding="utf-8")).meta
    assert folder_meta["folder"] == "picked"

    from bd_tree.api import export_view

    out = tmp_path / "view"
    export_view("tree", tmp_path, "1", out)
    assert (out / "build" / "build-step.md").is_file()
    assert (out / "g" / "grouped.md").is_file()
    assert (out / "4-flat.md").is_file()
    assert (out / "build" / "explicit-home.md").is_file()
    assert not (out / "custom" / "here.md").exists()
    assert (out / "picked" / "explicit-folder.md").is_file()
