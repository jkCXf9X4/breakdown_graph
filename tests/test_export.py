from __future__ import annotations

import shutil

import pytest

from bdg.api import check, pack
from bdg.errors import ExportError
from bdg.graph import build_graph, graph_view, render_dot, render_svg


def _chain(write, nodes):
    """1 -> 2, 3; 2 -> 4.  One undirected component of four nodes."""
    write(
        nodes,
        1,
        links=[
            {"to": "2-1", "type": "breaks_down"},
            {"to": "3-1", "type": "breaks_down"},
        ],
    )
    write(nodes, 2, links=[{"to": "4-1", "type": "breaks_down"}])
    write(nodes, 3)
    write(nodes, 4)


def test_graph_view_writes_flat_nodes_and_one_ring_index(write, tmp_path):
    nodes = tmp_path / "nodes"
    _chain(write, nodes)
    out = tmp_path / "graph"
    result = pack(tmp_path, "1-1", out, fresh=False)

    assert result.nodes == 4
    assert len(result.files) == 5  # 4 nodes, 1 root index
    index = (out / "INDEX.md").read_text(encoding="utf-8")
    assert not index.startswith("---")
    assert "GENERATED FILE" in index
    assert "# Graph 1-1" in index
    assert "## 0 — 1-1" in index
    assert "## 1 — children" in index
    assert "## 2" in index
    assert "[1-1 Title of 1-1](1-1.md)" in index
    assert "[4-1 Title of 4-1](4-1.md)" in index
    for name in ("1-1.md", "2-1.md", "3-1.md", "4-1.md"):
        assert (out / name).is_file()
        assert (out / name).parent == out
    assert not (out / "00-intent").exists()
    assert sorted(out.rglob("INDEX.md")) == [out / "INDEX.md"]


def test_graph_index_splits_ring_one_by_direction(write, tmp_path):
    nodes = tmp_path / "nodes"
    _chain(write, nodes)
    out = tmp_path / "view"
    pack(tmp_path, "2-1", out, fresh=False)

    index = (out / "INDEX.md").read_text(encoding="utf-8")
    assert "## 0 — 2-1" in index
    assert "## 1 — children" in index
    assert "## 1 — parents" in index
    assert index.index("## 1 — children") < index.index("## 1 — parents")
    assert "[4-1 Title of 4-1](4-1.md)" in index
    assert "[1-1 Title of 1-1](1-1.md)" in index


def test_graph_refuses_non_empty_unless_force_or_clean(write, tmp_path):
    write(tmp_path / "nodes", 1)
    out = tmp_path / "graph"
    pack(tmp_path, "1-1", out, fresh=False)
    (out / "stray.txt").write_text("x", encoding="utf-8")
    with pytest.raises(ExportError, match="refusing"):
        pack(tmp_path, "1-1", out, fresh=False)
    pack(tmp_path, "1-1", out, fresh=False, force=True)
    assert (out / "stray.txt").exists()
    pack(tmp_path, "1-1", out, fresh=False, clean=True)
    assert not (out / "stray.txt").exists()


def test_graph_view_exports_the_whole_component(write, tmp_path):
    nodes = tmp_path / "nodes"
    _chain(write, nodes)
    out = tmp_path / "view"
    result = pack(tmp_path, "2-1", out, fresh=False)

    assert result.nodes == 4
    assert (out / "1-1.md").is_file()
    assert (out / "2-1.md").is_file()
    assert (out / "3-1.md").is_file()
    assert (out / "4-1.md").is_file()


def test_context_excludes_stale_nodes(write, tmp_path, pin):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[
            {"to": "2-1", "type": "breaks_down"},
            {"to": "3-1", "type": "breaks_down"},
        ],
    )
    write(nodes, 2, body="v1\n")
    write(
        nodes,
        3,
        links=[{"to": "2-1", "type": "serves", "pinned": pin("v1\n")}],
        body="stale dependent\n",
    )
    write(nodes, 2, body="v2\n")
    out = tmp_path / "context"
    result = pack(tmp_path, "1-1", out, fresh=True)
    assert result.nodes == 2
    assert not list(out.rglob("3-1.md"))
    stale = (out / "STALE.md").read_text(encoding="utf-8")
    assert "`2-1`" in stale
    assert (out / "AGENTS.md").is_file()


def test_context_path_template_has_distance(write, tmp_path):
    nodes = tmp_path / "nodes"
    _chain(write, nodes)
    out = tmp_path / "context"
    pack(
        tmp_path,
        "1-1",
        out,
        fresh=True,
        path_template="{distance}-{ref}.md",
    )

    assert (out / "0-1-1.md").is_file()
    assert (out / "1-2-1.md").is_file()
    assert (out / "1-3-1.md").is_file()
    assert (out / "2-4-1.md").is_file()


def test_dot_render(write, tmp_path):
    nodes = tmp_path / "nodes"
    _chain(write, nodes)
    graph = build_graph(tmp_path)
    refs = graph_view(graph, "1-1")
    text = render_dot(graph, refs)
    assert len(refs) == 4
    assert "digraph bd_graph" in text
    assert '"1-1" -> "2-1" [label="breaks_down"' in text
    assert 'label="1-1\\nTitle of 1-1"' in text
    assert "fillcolor" in text


def test_generic_store_path_template_and_fields(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[
            {"to": "2-1", "type": "breaks_down"},
            {"to": "3-1", "type": "breaks_down"},
        ],
        phase="intent",
        audience="all",
        order=1,
        title="Objective",
    )
    write(
        nodes,
        2,
        links=[{"to": "4-1", "type": "breaks_down"}],
        phase="build",
        audience="team",
        order=2,
        title="Build",
    )
    write(nodes, 3, phase="review", audience="team", order=3)
    write(nodes, 4, phase="build", audience="dev", order=4)

    result = check(tmp_path)
    assert result.ok
    assert not any(issue.code == "missing-field" for issue in result.issues)

    out = tmp_path / "context"
    exported = pack(
        tmp_path,
        "1-1",
        out,
        fresh=True,
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


def test_default_path_uses_the_store_basename(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[{"to": "2-1", "type": "breaks_down"}],
        name="ignored-name",
        title="Ignored Title",
    )
    write(nodes, 2, name="also-ignored", title="Some Method (Draft)")
    out = tmp_path / "fallback"
    pack(tmp_path, "1-1", out, fresh=False)
    assert (out / "1-1.md").is_file()
    assert (out / "2-1.md").is_file()
    assert not (out / "ignored-name.md").exists()
    assert not (out / "2-1-some-method-draft.md").exists()


def test_template_collision_appends_the_ref(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[
            {"to": "2-1", "type": "breaks_down"},
            {"to": "3-1", "type": "breaks_down"},
        ],
    )
    write(nodes, 2)
    write(nodes, 3)
    out = tmp_path / "view"
    pack(tmp_path, "1-1", out, fresh=True, path_template="same.md")

    assert (out / "same.md").is_file()
    assert (out / "same-2-1.md").is_file()
    assert (out / "same-3-1.md").is_file()


def test_reserved_template_is_refused(write, tmp_path):
    nodes = tmp_path / "nodes"
    _chain(write, nodes)
    out = tmp_path / "view"
    with pytest.raises(ExportError, match="collides with generated"):
        pack(tmp_path, "1-1", out, fresh=True, path_template="INDEX.md")
    with pytest.raises(ExportError, match="collides with generated"):
        pack(tmp_path, "1-1", out, fresh=True, path_template="AGENTS.md")


def test_dot_color_and_shape_by_arbitrary_fields(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[{"to": "2-1", "type": "breaks_down"}],
        phase="intent",
        audience="all",
    )
    write(
        nodes,
        2,
        links=[{"to": "3-1", "type": "breaks_down"}],
        phase="build",
        audience="team",
    )
    write(nodes, 3, phase="build", audience="dev")
    graph = build_graph(tmp_path)
    text = render_dot(
        graph,
        graph_view(graph, "1-1"),
        color_by="phase",
        shape_by="audience",
    )
    assert "shape=ellipse" in text and "shape=diamond" in text
    colours = [
        line.split("fillcolor=")[1].split(",")[0]
        for line in text.splitlines()
        if "[label=" in line and "fillcolor=" in line
    ]
    assert len(colours) == 3
    assert colours[1] == colours[2]
    assert colours[0] != colours[1]


def test_no_exported_path_ends_in_index_md(write, tmp_path):
    nodes = tmp_path / "nodes"
    _chain(write, nodes)
    out = tmp_path / "view"
    result = pack(tmp_path, "1-1", out, fresh=False)
    node_paths = [
        path.relative_to(out).as_posix()
        for path in result.files
        if path.name != "INDEX.md"
    ]
    assert all(not path.endswith("INDEX.md") for path in node_paths)


@pytest.mark.skipif(shutil.which("dot") is None, reason="graphviz not installed")
def test_svg_render(write, tmp_path):
    write(tmp_path / "nodes", 1)
    graph = build_graph(tmp_path)
    svg = render_svg(graph, graph_view(graph, "1-1"))
    assert svg.lstrip().startswith("<?xml")
    assert "<svg" in svg
