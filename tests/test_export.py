from __future__ import annotations

import pytest

from bd_tree.api import export_view
from bd_tree.errors import ExportError


def test_tree_view_writes_nodes_and_one_index_per_folder(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], title="Root intent")
    write(nodes, 2, type="claim", layer="claims", section="claims", title="Thesis")
    out = tmp_path / "tree"
    result = export_view("tree", tmp_path, "1-1", out)
    assert result.nodes == 2
    assert len(result.files) == 4
    index = (out / "INDEX.md").read_text(encoding="utf-8")
    assert "GENERATED FILE" in index
    assert "[Root intent](1-1-root-intent.md)" in index
    assert "[Thesis](claims/2-1.md)" in index
    assert (out / "1-1-root-intent.md").is_file()
    assert (out / "claims" / "2-1.md").is_file()
    claims_index = (out / "claims" / "INDEX.md").read_text(encoding="utf-8")
    assert "# claims/" in claims_index
    assert "[Thesis](2-1.md)" in claims_index


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
    write(nodes, 3, version=1, section="evidence", name="three-v1")
    write(nodes, 2, version=1, contains=["3-1"], section="claims", name="two-v1")
    out = tmp_path / "view"
    result = export_view("tree", tmp_path, "2-1", out)
    assert result.nodes == 2
    assert (out / "claims" / "two-v1.md").is_file()
    assert (out / "claims" / "evidence" / "three-v1.md").is_file()
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
    write(nodes, 1, contains=["2"], layer="intent", name="intent/1-1")
    write(nodes, 2, title="Some Method (Draft)")  # no name
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


def test_section_and_title_slug_build_the_default_path(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], section="claims", title="The Main Thesis")
    write(nodes, 2, section="06-evolution/suggested", title="Café: An Idea!")
    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out)
    assert (out / "claims" / "the-main-thesis.md").is_file()
    assert (out / "claims" / "06-evolution" / "suggested" / "cafe-an-idea.md").is_file()


def test_name_overrides_the_title_for_the_file_stem(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], title="Root")
    write(nodes, 2, section="claims", name="custom-name", title="Ignored")
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


def test_section_and_name_win_over_home(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], title="Root")
    write(
        nodes,
        2,
        home="explicit/home.md",
        section="claims",
        name="custom",
        title="Ignored",
    )
    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out)
    assert (out / "claims" / "custom.md").is_file()
    assert not (out / "explicit" / "home.md").exists()


def test_slug_falls_back_to_ref_when_title_has_no_slug(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"], section="odd")
    write(nodes, 2, title="!!!")
    write(nodes, 3, title="")
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


def test_duplicate_flat_paths_are_checked(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"])
    write(nodes, 2, name="same", title="Same")
    write(nodes, 3, name="same", title="Same")
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


def test_folder_is_inert_and_the_title_slug_places_the_node(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], title="Root")
    write(nodes, 2, folder="x", title="Some Method")
    out = tmp_path / "view"
    result = export_view("tree", tmp_path, "1-1", out)
    assert result.nodes == 2
    assert (out / "2-1-some-method.md").is_file()
    assert not (out / "x").exists()


def test_prefix_collision_is_refused(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], name="a/b")
    write(nodes, 2, section="a/b.md", name="c")
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


def test_section_true_uses_the_title_slug_as_directory(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], section=True, title="Evolution")
    write(nodes, 2, title="New Idea")
    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out)
    assert (out / "evolution" / "evolution.md").is_file()
    assert (out / "evolution" / "2-1-new-idea.md").is_file()
    index = (out / "INDEX.md").read_text(encoding="utf-8")
    assert "[Evolution](evolution/evolution.md)" in index
    assert "[New Idea](evolution/2-1-new-idea.md)" in index


def test_section_string_sets_the_directory_verbatim(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], section="06-evolution", title="Root")
    write(nodes, 2, section="claims", name="idea")
    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out)
    assert (out / "06-evolution" / "root.md").is_file()
    assert (out / "06-evolution" / "claims" / "idea.md").is_file()


def test_nested_sections_stack_their_directories(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], section=True, title="Alpha")
    write(nodes, 2, contains=["3"], section=True, title="Beta")
    write(nodes, 3, title="Leaf")
    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out)
    assert (out / "alpha" / "alpha.md").is_file()
    assert (out / "alpha" / "beta" / "beta.md").is_file()
    assert (out / "alpha" / "beta" / "3-1-leaf.md").is_file()


def test_root_relative_section_resolves_from_the_output_root(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], section="/00-intent", title="Intent")
    write(nodes, 2, contains=["3"], section="/01-product", title="Product")
    write(nodes, 3, section="/01-product", title="Leaf")
    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out)
    assert (out / "00-intent" / "intent.md").is_file()
    assert (out / "01-product" / "product.md").is_file()
    assert (out / "01-product" / "leaf.md").is_file()


def test_relative_section_still_nests_under_a_root_relative_parent(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], section="/06-evolution", title="Evolution")
    write(nodes, 2, contains=["3"], section="suggested", title="Suggested")
    write(nodes, 3, title="Idea")
    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out)
    assert (out / "06-evolution" / "evolution.md").is_file()
    assert (out / "06-evolution" / "suggested" / "suggested.md").is_file()
    assert (out / "06-evolution" / "suggested" / "3-1-idea.md").is_file()


def test_relative_section_may_span_several_segments(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], section="/06-evolution", title="Evolution")
    write(nodes, 2, contains=["3"], section="suggested/01-indexes", title="Indexes")
    write(nodes, 3, title="Leaf")
    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out)
    assert (out / "06-evolution" / "suggested" / "01-indexes" / "indexes.md").is_file()
    assert (out / "06-evolution" / "suggested" / "01-indexes" / "3-1-leaf.md").is_file()


def test_root_relative_sections_may_share_a_layer_directory(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"], section="/00-intent", title="Root")
    write(nodes, 2, section="/00-intent", title="One")
    write(nodes, 3, section="/00-intent", title="Two")
    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out)
    assert (out / "00-intent" / "root.md").is_file()
    assert (out / "00-intent" / "one.md").is_file()
    assert (out / "00-intent" / "two.md").is_file()


def test_relative_sections_resolving_to_one_directory_are_refused(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"])
    write(nodes, 2, contains=["4"])
    write(nodes, 3, contains=["5"])
    write(nodes, 4, contains=["6"], section="shared", title="One")
    write(nodes, 5, contains=["7"], section="shared", title="Two")
    write(nodes, 6, title="A")
    write(nodes, 7, title="B")
    out = tmp_path / "view"
    with pytest.raises(ExportError, match="directory 'shared'"):
        export_view("tree", tmp_path, "1-1", out)


def test_relative_leaf_sections_may_share_a_stage_directory(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"], section="/06-evolution", title="Evolution")
    write(nodes, 2, section="suggested", title="One")
    write(nodes, 3, section="suggested", title="Two")
    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out)
    assert (out / "06-evolution" / "suggested" / "one.md").is_file()
    assert (out / "06-evolution" / "suggested" / "two.md").is_file()


def test_sections_coexist_with_unchanged_placement(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3", "4", "5"], title="Root")
    write(nodes, 2, contains=["6"], section=True, title="Section")
    write(nodes, 3, section="claims", name="named")
    write(nodes, 4, name="flat")
    write(nodes, 5, title="Titled")
    write(nodes, 6, title="Inside")
    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out)
    assert (out / "1-1-root.md").is_file()
    assert (out / "section" / "section.md").is_file()
    assert (out / "section" / "6-1-inside.md").is_file()
    assert (out / "claims" / "named.md").is_file()
    assert (out / "flat.md").is_file()
    assert (out / "5-1-titled.md").is_file()


@pytest.mark.parametrize("value", [False, "", None, 0, [], {}])
def test_non_section_values_are_ignored(write, tmp_path, value):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2, section=value, title="Plain")
    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out)
    assert (out / "2-1-plain.md").is_file()
    assert not (out / "plain").exists()


def test_two_sibling_sections_with_the_same_directory_are_refused(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"])
    write(nodes, 2, contains=["4"], section="same", title="One")
    write(nodes, 3, contains=["5"], section="same", title="Two")
    write(nodes, 4, title="A")
    write(nodes, 5, title="B")
    out = tmp_path / "view"
    with pytest.raises(ExportError, match="directory 'same'"):
        export_view("tree", tmp_path, "1-1", out)


def test_section_directory_colliding_with_a_file_path_is_refused(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"])
    write(nodes, 2, section="claims", name="2-1")
    write(nodes, 3, section="claims/2-1.md", title="Clash")
    out = tmp_path / "view"
    with pytest.raises(ExportError, match="conflicting paths"):
        export_view("tree", tmp_path, "1-1", out)


def test_path_template_disables_section_inheritance(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], section=True, title="Section")
    write(nodes, 2, name="child")
    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out, path_template="{ref}.md")
    assert (out / "1-1.md").is_file()
    assert (out / "2-1.md").is_file()
    assert not (out / "section").exists()


def test_section_is_available_as_a_template_field(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], section="/dir", title="Root")
    write(nodes, 2, section="child-dir", title="Child")
    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out, path_template="{section}/{ref}.md")
    assert (out / "dir" / "1-1.md").is_file()
    assert (out / "child-dir" / "2-1.md").is_file()


def _folder_order_view(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3", "4"], title="Root")
    write(nodes, 2, section="/00-evolution", title="Evolution")
    write(nodes, 3, section="/00-evolution", title="Index idea")
    write(nodes, 4, section="/00-evolution/suggested", title="Stage")
    return nodes


def test_folder_index_lists_direct_files_then_subfolders_in_view_order(
    write, tmp_path
):
    _folder_order_view(write, tmp_path)
    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out)

    index = (out / "00-evolution" / "INDEX.md").read_text(encoding="utf-8")
    assert "# 00-evolution/" in index
    assert "[Evolution](evolution.md)" in index
    assert "[Index idea](index-idea.md)" in index
    assert "[suggested](suggested/INDEX.md)" in index
    assert index.index("evolution.md") < index.index("index-idea.md")
    assert index.index("index-idea.md") < index.index("suggested/INDEX.md")
    assert "[Stage]" not in index  # the stage file belongs to suggested/


def test_folder_index_order_follows_contains_and_is_deterministic(write, tmp_path):
    nodes = _folder_order_view(write, tmp_path)
    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out)
    first = (out / "00-evolution" / "INDEX.md").read_bytes()

    write(nodes, 1, contains=["3", "2", "4"], title="Root")
    export_view("tree", tmp_path, "1-1", out, force=True)
    second = (out / "00-evolution" / "INDEX.md").read_text(encoding="utf-8")
    assert second.index("[Index idea](index-idea.md)") < second.index(
        "[Evolution](evolution.md)"
    )

    export_view("tree", tmp_path, "1-1", out, force=True)
    assert (out / "00-evolution" / "INDEX.md").read_bytes() == second.encode()


def test_multi_segment_section_indexes_each_prefix_directory(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], title="Root")
    write(nodes, 2, section="a/b", title="Nested")
    out = tmp_path / "view"
    export_view("tree", tmp_path, "1-1", out)

    assert (out / "a" / "INDEX.md").is_file()
    assert (out / "a" / "b" / "INDEX.md").is_file()
    a_index = (out / "a" / "INDEX.md").read_text(encoding="utf-8")
    assert "# a/" in a_index
    assert "[b](b/INDEX.md)" in a_index
    b_index = (out / "a" / "b" / "INDEX.md").read_text(encoding="utf-8")
    assert "[Nested](nested.md)" in b_index


def test_nested_index_name_collision_is_refused(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2, section="claims", name="INDEX", title="Clash")
    out = tmp_path / "view"
    with pytest.raises(ExportError, match="collides with generated"):
        export_view("tree", tmp_path, "1-1", out)


def test_no_exported_path_ends_in_index_md(write, tmp_path):
    _folder_order_view(write, tmp_path)
    out = tmp_path / "view"
    result = export_view("tree", tmp_path, "1-1", out)
    node_paths = [
        path.relative_to(out).as_posix()
        for path in result.files
        if path.name != "INDEX.md"
    ]
    assert all(not path.endswith("INDEX.md") for path in node_paths)
