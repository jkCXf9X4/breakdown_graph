from __future__ import annotations

import shutil

import pytest

from bd_tree.api import check, export_view
from bd_tree.errors import ExportError


def _chain(write, nodes):
    """intent -> claims -> evidence, with a review branch off the root."""
    write(
        nodes,
        1,
        links=[
            {"to": "2-1", "type": "breaks_down"},
            {"to": "3-1", "type": "breaks_down"},
        ],
        band="intent",
        band_layout="flat",
    )
    write(nodes, 2, links=[{"to": "4-1", "type": "breaks_down"}], band="claims")
    write(nodes, 3, band="review")
    write(nodes, 4, band="evidence")


def test_graph_view_writes_band_nodes_and_one_index_per_folder(write, tmp_path):
    nodes = tmp_path / "nodes"
    _chain(write, nodes)
    out = tmp_path / "graph"
    result = export_view("graph", tmp_path, "1-1", out)

    assert result.nodes == 4
    assert len(result.files) == 9  # 4 nodes, 4 folder indexes, 1 root index
    index = (out / "INDEX.md").read_text(encoding="utf-8")
    assert not index.startswith("---")
    assert "GENERATED FILE" in index
    assert "[layer 0 — intent](00-intent/INDEX.md) — 1 node" in index
    assert "[layer 3 — review](03-review/INDEX.md) — 1 node" in index
    assert (out / "00-intent" / "1-1.md").is_file()
    assert (out / "01-claims" / "2-1.md").is_file()
    assert (out / "02-evidence" / "4-1.md").is_file()
    claims_index = (out / "01-claims" / "INDEX.md").read_text(encoding="utf-8")
    assert "# 01-claims/" in claims_index
    assert "[2-1 Title of 2-1](2-1.md)" in claims_index


def test_graph_refuses_non_empty_unless_force_or_clean(write, tmp_path):
    write(tmp_path / "nodes", 1, band="root")
    out = tmp_path / "graph"
    export_view("graph", tmp_path, "1-1", out)
    (out / "stray.txt").write_text("x", encoding="utf-8")
    with pytest.raises(ExportError, match="refusing"):
        export_view("graph", tmp_path, "1-1", out)
    export_view("graph", tmp_path, "1-1", out, force=True)
    assert (out / "stray.txt").exists()
    export_view("graph", tmp_path, "1-1", out, clean=True)
    assert not (out / "stray.txt").exists()


def test_version_view_exports_only_that_closure(write, tmp_path):
    nodes = tmp_path / "nodes"
    _chain(write, nodes)
    out = tmp_path / "view"
    result = export_view("graph", tmp_path, "2-1", out)
    assert result.nodes == 2
    assert (out / "01-claims" / "2-1.md").is_file()
    assert (out / "02-evidence" / "4-1.md").is_file()
    assert not (out / "00-intent").exists()


def test_context_excludes_stale_nodes(write, tmp_path, pin):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[
            {"to": "2-1", "type": "breaks_down"},
            {"to": "3-1", "type": "breaks_down"},
        ],
        band="intent",
        band_layout="flat",
    )
    write(nodes, 2, band="claims", body="v1\n")
    write(
        nodes,
        3,
        band="review",
        links=[{"to": "2-1", "type": "serves", "pinned": pin("v1\n")}],
        body="stale dependent\n",
    )
    write(nodes, 2, band="claims", body="v2\n")
    out = tmp_path / "context"
    result = export_view("context", tmp_path, "1-1", out)
    assert result.nodes == 2
    assert not list(out.rglob("3-1.md"))
    stale = (out / "STALE.md").read_text(encoding="utf-8")
    assert "`2-1`" in stale
    assert (out / "AGENTS.md").is_file()


def test_dot_export(write, tmp_path):
    nodes = tmp_path / "nodes"
    _chain(write, nodes)
    out = tmp_path / "graph.dot"
    result = export_view("dot", tmp_path, "1-1", out)
    assert result.nodes == 4
    text = out.read_text(encoding="utf-8")
    assert "digraph bd_tree" in text
    assert '"1-1" -> "2-1" [label="breaks_down"' in text
    assert 'label="1-1\\nTitle of 1-1"' in text


def test_generic_store_path_template_and_fields(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[
            {"to": "2-1", "type": "breaks_down"},
            {"to": "3-1", "type": "breaks_down"},
        ],
        band="intent",
        phase="intent",
        audience="all",
        order=1,
        title="Objective",
    )
    write(
        nodes,
        2,
        links=[{"to": "4-1", "type": "breaks_down"}],
        band="claims",
        phase="build",
        audience="team",
        order=2,
        title="Build",
    )
    write(nodes, 3, band="review", phase="review", audience="team", order=3)
    write(nodes, 4, band="evidence", phase="build", audience="dev", order=4)

    result = check(tmp_path)
    assert result.ok
    assert not any(issue.code == "missing-field" for issue in result.issues)

    out = tmp_path / "context"
    exported = export_view(
        "context",
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

    import yaml

    front = (out / "build" / "4-1.md").read_text(encoding="utf-8").split("---")[1]
    data = yaml.safe_load(front)
    assert data["phase"] == "build"
    assert data["audience"] == "dev"
    assert data["order"] == 4
    assert "layer" not in data and "type" not in data and "folder" not in data


def test_default_path_adds_the_title_slug_to_the_ref(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[{"to": "2-1", "type": "breaks_down"}],
        band="intent",
        band_layout="flat",
        name="intent/1-1",
    )
    write(nodes, 2, band="claims", name=None, title="Some Method (Draft)")
    out = tmp_path / "fallback"
    export_view("graph", tmp_path, "1-1", out)
    assert (out / "00-intent" / "intent/1-1.md").is_file()
    assert (out / "01-claims" / "2-1-some-method-draft.md").is_file()
    assert not (out / "01-claims" / "2-1.md").exists()


def test_default_path_keeps_the_version_in_the_slug_stem(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 2, version=1, band="claims", name=None, title="Method Note")
    out = tmp_path / "version"
    export_view("graph", tmp_path, "2-1", out)
    assert (out / "00-claims" / "2-1-method-note.md").is_file()
    assert not (out / "00-claims" / "2-1.md").exists()


def test_name_overrides_title_and_home_and_folder_are_inert(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[{"to": "2-1", "type": "breaks_down"}],
        band="intent",
        band_layout="flat",
        name="custom-name",
        title="Ignored",
    )
    write(
        nodes,
        2,
        band="claims",
        name="flat-name",
        title="Ignored",
        home="explicit/home.md",
        folder="x",
    )
    out = tmp_path / "view"
    export_view("graph", tmp_path, "1-1", out)
    assert (out / "00-intent" / "custom-name.md").is_file()
    assert (out / "01-claims" / "flat-name.md").is_file()
    assert not (out / "explicit").exists()
    assert not (out / "x").exists()


def test_duplicate_flat_paths_are_checked(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[
            {"to": "2-1", "type": "breaks_down"},
            {"to": "3-1", "type": "breaks_down"},
        ],
        band="intent",
        band_layout="flat",
    )
    write(nodes, 2, band="claims", name="same", title="Same")
    write(nodes, 3, band="claims", name="same", title="Same", order=1)
    out = tmp_path / "view"
    with pytest.raises(ExportError, match="both resolve"):
        export_view("graph", tmp_path, "1-1", out)


def test_dot_color_and_shape_by_arbitrary_fields(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[{"to": "2-1", "type": "breaks_down"}],
        band="intent",
        band_layout="flat",
        phase="intent",
        audience="all",
    )
    write(nodes, 2, links=[{"to": "3-1", "type": "breaks_down"}], band="claims", phase="build", audience="team")
    write(nodes, 3, band="evidence", phase="build", audience="dev")
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
    assert colours[1] == colours[2]
    assert colours[0] != colours[1]


def test_band_subpath_gets_an_index_in_every_prefix_folder(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[{"to": "2-1", "type": "breaks_down"}],
        band="a",
        band_layout="flat",
        title="Root",
        name="root",
    )
    write(nodes, 2, band="a", subpath="b", order=1, title="Nested", name="nested")
    out = tmp_path / "graph"
    export_view("graph", tmp_path, "1-1", out)

    assert (out / "00-a" / "INDEX.md").is_file()
    assert (out / "00-a" / "b" / "INDEX.md").is_file()
    a_index = (out / "00-a" / "INDEX.md").read_text(encoding="utf-8")
    assert "# 00-a/" in a_index
    assert "[b/](b/INDEX.md)" in a_index
    b_index = (out / "00-a" / "b" / "INDEX.md").read_text(encoding="utf-8")
    assert "[2-1 Nested](nested.md)" in b_index


def test_nested_index_name_collision_is_refused(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[{"to": "2-1", "type": "breaks_down"}],
        band="intent",
        band_layout="flat",
    )
    write(nodes, 2, band="claims", name="INDEX", title="Clash")
    out = tmp_path / "view"
    with pytest.raises(ExportError, match="collides with generated"):
        export_view("graph", tmp_path, "1-1", out)


def test_no_exported_path_ends_in_index_md(write, tmp_path):
    nodes = tmp_path / "nodes"
    _chain(write, nodes)
    out = tmp_path / "view"
    result = export_view("graph", tmp_path, "1-1", out)
    node_paths = [
        path.relative_to(out).as_posix()
        for path in result.files
        if path.name != "INDEX.md"
    ]
    assert all(not path.endswith("INDEX.md") for path in node_paths)


@pytest.mark.skipif(shutil.which("dot") is None, reason="graphviz not installed")
def test_svg_export(write, tmp_path):
    write(tmp_path / "nodes", 1, band="root")
    out = tmp_path / "graph.svg"
    result = export_view("svg", tmp_path, "1-1", out)
    assert result.nodes == 1
    assert out.read_text(encoding="utf-8").lstrip().startswith("<?xml")
