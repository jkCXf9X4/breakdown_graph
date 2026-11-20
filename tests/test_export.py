from __future__ import annotations

import pytest

from bd_tree.api import export_view
from bd_tree.errors import ExportError


def test_tree_view_writes_nodes_and_one_index(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], title="Root intent")
    write(nodes, 2, type="claim", layer="claims", title="Thesis")
    out = tmp_path / "tree"
    result = export_view("tree", tmp_path, "1-1", out)
    assert result.nodes == 2
    assert len(result.files) == 3
    index = (out / "INDEX.md").read_text(encoding="utf-8")
    assert "GENERATED FILE" in index
    assert "[Root intent](1-1-root-intent.md)" in index
    assert "[Thesis](claims/2-1.md)" in index
    assert (out / "1-1-root-intent.md").is_file()
    assert (out / "claims" / "2-1.md").is_file()
    assert not (out / "claims" / "INDEX.md").exists()


def test_tree_refuses_non_empty_unless_force_or_clean(write, tmp_path):
    write(tmp_path / "nodes", 1)
    out = tmp_path / "tree"
    export_view("tree", tmp_path, "1-1", out)
    (out / "stray.txt").write_text("x", encoding="utf-8")
    with pytest.raises(ExportError, match="refusing"):
        export_view("tree", tmp_path, "1-1", out)
    export_view("tree", tmp_path, "1-1", out, force=True)
    assert (out / "stray.txt").exists()
    export_view("tree", tmp_path, "1-1", out, clean=True)
    assert not (out / "stray.txt").exists()


def test_version_view_exports_only_that_closure(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2, contains=["3"])
    write(nodes, 3)
    write(nodes, 3, version=1, folder="evidence", name="three-v1")
    write(nodes, 2, version=1, contains=["3-1"], folder="claims", name="two-v1")
    out = tmp_path / "view"
    result = export_view("tree", tmp_path, "2-1", out)
    assert result.nodes == 2
    assert (out / "claims" / "two-v1.md").is_file()
    assert (out / "evidence" / "three-v1.md").is_file()
    assert not (out / "claims" / "two.md").exists()


def test_context_excludes_stale_nodes(write, tmp_path, pin):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"])
    write(nodes, 2, type="claim", layer="claims", body="v1\n")
    write(
        nodes,
        3,
        type="claim",
        layer="claims",
        links=[{"to": "2", "type": "serves", "pinned": pin("v1\n")}],
        body="stale dependent\n",
    )
    write(nodes, 2, type="claim", layer="claims", body="v2\n")
    out = tmp_path / "context"
    result = export_view("context", tmp_path, "1-1", out)
    assert result.nodes == 2
    assert not (out / "claims" / "3-1.md").exists()
    stale = (out / "STALE.md").read_text(encoding="utf-8")
    assert "`2-1`" in stale
    assert (out / "AGENTS.md").is_file()


def test_dot_export(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2, links=[{"to": "1", "type": "supports"}])
    out = tmp_path / "graph.dot"
    result = export_view("dot", tmp_path, "1-1", out)
    assert result.nodes == 2
    text = out.read_text(encoding="utf-8")
    assert "digraph bd_tree" in text
    assert '"2-1" -> "1-1" [label="supports"' in text
    assert 'label="1-1\\nTitle of 1-1"' in text


def test_generic_store_without_layer_type_or_placement(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"], phase="intent", audience="all", order=1, title="Objective")
    write(nodes, 2, contains=["4"], phase="build", audience="team", order=2, title="Build")
    write(nodes, 3, phase="review", audience="team", order=3, title="Review")
    write(nodes, 4, phase="build", audience="dev", order=4, title="Detail")

    from bd_tree.api import check

    result = check(tmp_path)
    assert result.ok
    assert not any(issue.code == "missing-field" for issue in result.issues)

    out = tmp_path / "generic-tree"
    exported = export_view(
        "tree",
        tmp_path,
        "1-1",
        out,
        path_template="{phase}/{ref}.md",
        title_field="phase",
        summary_field="audience",
    )
    assert exported.nodes == 4
    assert (out / "intent" / "1-1.md").is_file()
    assert (out / "build" / "2-1.md").is_file()
    assert (out / "build" / "4-1.md").is_file()
    index = (out / "INDEX.md").read_text(encoding="utf-8")
    assert "[build](build/2-1.md) — team" in index
    assert index.index("[build](build/2-1.md)") < index.index("[review](review/3-1.md)")

    import yaml

    front = (out / "build" / "4-1.md").read_text(encoding="utf-8").split("---")[1]
    data = yaml.safe_load(front)
    assert data["phase"] == "build"
    assert data["audience"] == "dev"
    assert data["order"] == 4
    assert "layer" not in data and "type" not in data and "folder" not in data


def test_default_path_adds_the_title_slug_to_the_ref(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], layer="intent")
    write(nodes, 2, title="Some Method (Draft)")  # no folder/name
    out = tmp_path / "fallback"
    export_view("tree", tmp_path, "1-1", out)
    assert (out / "intent" / "1-1.md").is_file()
    assert (out / "2-1-some-method-draft.md").is_file()
    assert not (out / "2-1.md").exists()


def test_default_path_keeps_the_version_in_the_slug_stem(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 2, version=1, title="Method Note")
    out = tmp_path / "version"
    export_view("tree", tmp_path, "2-1", out)
    assert (out / "2-1-method-note.md").is_file()
    assert not (out / "2-1.md").exists()
    assert not (out / "2-2.md").exists()


def test_default_path_falls_back_to_ref_without_a_usable_title(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"], layer="intent")
    write(nodes, 2, title="!!!")
    write(nodes, 3, title="")
    out = tmp_path / "fallback"
    export_view("tree", tmp_path, "1-1", out)
    assert (out / "2-1.md").is_file()
    assert (out / "3-1.md").is_file()
    assert not (out / "2-1-.md").exists()
    assert not (out / "3-1-.md").exists()


def test_folder_and_title_slug_build_the_default_path(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], folder="claims", title="The Main Thesis")
    write(nodes, 2, folder="06-evolution/suggested", title="Café: An Idea!")
    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out)
    assert (out / "claims" / "the-main-thesis.md").is_file()
    assert (out / "06-evolution" / "suggested" / "cafe-an-idea.md").is_file()


def test_name_overrides_the_title_for_the_file_stem(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], title="Root")
    write(nodes, 2, folder="claims", name="custom-name", title="Ignored")
    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out)
    assert (out / "claims" / "custom-name.md").is_file()
    assert not (out / "claims" / "ignored.md").exists()


def test_name_only_places_the_node_flat(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2, name="flat-name", title="Ignored")
    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out)
    assert (out / "flat-name.md").is_file()


def test_folder_and_name_win_over_home(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], title="Root")
    write(
        nodes,
        2,
        home="explicit/home.md",
        folder="claims",
        name="custom",
        title="Ignored",
    )
    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out)
    assert (out / "claims" / "custom.md").is_file()
    assert not (out / "explicit" / "home.md").exists()


def test_slug_falls_back_to_ref_when_title_has_no_slug(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"])
    write(nodes, 2, folder="odd", title="!!!")
    write(nodes, 3, folder="odd", title="")
    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out)
    assert (out / "odd" / "2-1.md").is_file()
    assert (out / "odd" / "3-1.md").is_file()


def test_folder_and_name_are_available_as_template_fields(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], folder="intent", title="Root")
    write(nodes, 2, folder="claims", title="Deep Claim")
    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out, path_template="{folder}/{name}.md")
    assert (out / "intent" / "root.md").is_file()
    assert (out / "claims" / "deep-claim.md").is_file()


def test_folder_paths_are_checked_for_duplicates(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"])
    write(nodes, 2, folder="claims", title="Same")
    write(nodes, 3, folder="claims", title="Same")
    out = tmp_path / "view"
    with pytest.raises(ExportError, match="both resolve"):
        export_view("tree", tmp_path, "1-1", out)


def test_home_is_inert_and_the_title_slug_places_the_node(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], title="Root")
    write(nodes, 2, home="somewhere.md", title="Some Method")
    out = tmp_path / "view"
    result = export_view("tree", tmp_path, "1-1", out)
    assert result.nodes == 2
    assert (out / "2-1-some-method.md").is_file()
    assert not (out / "somewhere.md").exists()
    index = (out / "INDEX.md").read_text(encoding="utf-8")
    assert "[Some Method](2-1-some-method.md)" in index


def test_prefix_collision_is_refused(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], folder="a", name="b")
    write(nodes, 2, folder="a/b.md", name="c")
    out = tmp_path / "tree"
    with pytest.raises(ExportError) as caught:
        export_view("tree", tmp_path, "1-1", out)
    message = str(caught.value)
    assert "1" in message and "2" in message
    assert "a/b.md" in message


def test_dot_color_and_shape_by_arbitrary_fields(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], phase="intent", audience="all")
    write(nodes, 2, contains=["3"], phase="build", audience="team")
    write(nodes, 3, phase="build", audience="dev")
    out = tmp_path / "graph.dot"
    export_view("dot", tmp_path, "1-1", out, color_by="phase", shape_by="audience")
    text = out.read_text(encoding="utf-8")
    assert "shape=ellipse" in text and "shape=diamond" in text
    colours = [
        line.split("fillcolor=")[1].split(",")[0]
        for line in text.splitlines()
        if "fillcolor=" in line
    ]
    assert len(colours) == 3
    # same phase -> same stable colour
    assert colours[1] == colours[2]
    assert colours[0] != colours[1]
