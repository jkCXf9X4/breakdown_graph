"""Graph mode: forward links, stage ordering, audit and export."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from bd_tree import api
from bd_tree.cli import main
from bd_tree.errors import BreakdownError, ExportError
from bd_tree.frontmatter import parse_document
from bd_tree.graph import (
    audit,
    build_graph,
    graph_layout,
    graph_view,
    layout_paths,
    render_audit,
    render_dot,
    render_graph,
    render_in,
    render_out,
    resolve_graph_ref,
)

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
STAGE_DIRS = (
    "00-intent",
    "01-breakdown",
    "02-claims",
    "03-verification",
    "04-operation",
)


def _example_store(tmp_path: Path) -> Path:
    shutil.copytree(EXAMPLES / ".bd_tree", tmp_path / ".bd_tree")
    return tmp_path


def _file_map(out: Path) -> dict[str, bytes]:
    return {
        path.relative_to(out).as_posix(): path.read_bytes()
        for path in sorted(out.rglob("*"))
        if path.is_file()
    }


def _codes(graph, anchor=None):
    return [issue.code for issue in audit(graph, anchor)]


def test_stage_missing_and_invalid_are_collected(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, stage=0)
    write(nodes, 2)
    write(nodes, 3, stage="one")
    write(nodes, 4, stage=True)
    codes = _codes(build_graph(tmp_path), "1-1")
    assert codes.count("graph-stage-missing") == 1
    assert codes.count("graph-stage-invalid") == 2


def test_order_invalid_is_an_error(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, stage=0, order="first")
    assert "graph-order-invalid" in _codes(build_graph(tmp_path), "1-1")


def test_back_edge_is_an_error(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, stage=2, links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2, stage=1)
    issues = audit(build_graph(tmp_path), "1-1")
    assert [issue.code for issue in issues].count("graph-back-edge") == 1


def test_dangling_link_is_an_error(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, stage=0, links=[{"to": "9-1", "type": "breaks_down"}])
    issues = audit(build_graph(tmp_path), "1-1")
    assert any(issue.code == "graph-dangling-link" for issue in issues)


def test_cycle_is_reported_as_a_path(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, stage=0, links=[{"to": "2", "type": "supports"}])
    write(nodes, 2, stage=1, links=[{"to": "1", "type": "supports"}])
    issues = audit(build_graph(tmp_path), "1-1")
    cycle = [issue for issue in issues if issue.code == "graph-cycle"]
    assert cycle
    assert "1-1 -> 2-1 -> 1-1" in cycle[0].message


def test_forward_closure_includes_a_two_parent_node_once(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, stage=0, links=[{"to": "2", "type": "breaks_down"}, {"to": "3", "type": "breaks_down"}])
    write(nodes, 2, stage=1, links=[{"to": "4", "type": "supports"}])
    write(nodes, 3, stage=1, links=[{"to": "4", "type": "supports"}])
    write(nodes, 4, stage=2)
    refs = graph_view(build_graph(tmp_path), "1-1")
    assert refs.count("4-1") == 1
    assert set(refs) == {"1-1", "2-1", "3-1", "4-1"}


def test_type_and_stage_filters(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, stage=0, links=[{"to": "2", "type": "supports"}, {"to": "3", "type": "refutes"}])
    write(nodes, 2, stage=1, links=[{"to": "4", "type": "supports"}])
    write(nodes, 3, stage=1, links=[{"to": "5", "type": "refutes"}])
    write(nodes, 4, stage=2)
    write(nodes, 5, stage=2)
    graph = build_graph(tmp_path)
    assert set(graph_view(graph, "1-1", types=["supports"])) == {"1-1", "2-1", "4-1"}
    assert set(graph_view(graph, "1-1", stages=(1, 1))) == {"1-1", "2-1", "3-1"}
    assert set(graph_view(graph, "1-1", stages=(2, 2))) == {"1-1", "4-1", "5-1"}
    assert set(graph_view(graph, "1-1", depth=1)) == {"1-1", "2-1", "3-1"}


def test_layout_labels_and_order(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, stage=0, layer="intent", links=[{"to": "2", "type": "breaks_down"}, {"to": "3", "type": "breaks_down"}, {"to": "4", "type": "breaks_down"}])
    write(nodes, 2, stage=1, layer="alpha", order=2)
    write(nodes, 3, stage=1, layer="alpha", order=1)
    write(nodes, 4, stage=1, layer="beta", order=0)
    bands = graph_layout(build_graph(tmp_path), ["1-1", "2-1", "3-1", "4-1"])
    assert [band.stage for band in bands] == [0, 1]
    assert bands[0].directory == "00-intent"
    assert bands[1].label == "alpha"
    assert bands[1].directory == "01-alpha"
    assert bands[1].refs == ["4-1", "3-1", "2-1"]


def test_layout_tie_break_is_lexicographic(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, stage=0, links=[{"to": "2", "type": "breaks_down"}, {"to": "3", "type": "breaks_down"}])
    write(nodes, 2, stage=1, layer="zebra")
    write(nodes, 3, stage=1, layer="alpha")
    band = graph_layout(build_graph(tmp_path), ["2-1", "3-1"])[0]
    assert band.label == "alpha"


def test_layer_subpath_paths_and_headings(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        layer="intent",
        links=[
            {"to": "2", "type": "breaks_down"},
            {"to": "3", "type": "breaks_down"},
            {"to": "4", "type": "breaks_down"},
        ],
    )
    write(nodes, 2, layer="claims/structural")
    write(nodes, 3, layer="claims/verification", order=1)
    write(nodes, 4, layer="claims")
    graph = build_graph(tmp_path)
    refs = graph_view(graph, "1-1")

    paths = layout_paths(graph, refs)
    assert paths["2-1"] == "01-claims/structural/2-1.md"
    assert paths["3-1"] == "01-claims/verification/3-1.md"
    assert paths["4-1"] == "01-claims/4-1.md"

    text = render_graph(graph, refs)
    assert "  structural/" in text
    assert "  verification/" in text
    # The band root comes first, then subpaths in lexicographic order.
    assert text.index("[4-1]") < text.index("  structural/") < text.index("[2-1]")
    assert text.index("[2-1]") < text.index("  verification/") < text.index("[3-1]")


@pytest.mark.parametrize(
    "value",
    ["/absolute", "a/../b", "a\\b", "notes.md", "INDEX.md", "a//b", ".", ".."],
)
def test_layer_rejects_bad_values(write, tmp_path, value):
    nodes = tmp_path / "nodes"
    write(nodes, 2, layer="intent", links=[{"to": "1", "type": "x"}])
    write(nodes, 1, layer=value)
    graph = build_graph(tmp_path)
    assert "graph-layer-invalid" in _codes(graph, "1-1")
    assert "unlayered" in render_graph(graph, list(graph.store.nodes))


def test_layout_paths_rejects_file_directory_collision(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        stage=0,
        links=[
            {"to": "2", "type": "breaks_down"},
            {"to": "3", "type": "breaks_down"},
        ],
    )
    write(nodes, 2, stage=1, layer="claims", name="foo")
    write(nodes, 3, stage=1, layer="claims", name="foo.md/x")
    graph = build_graph(tmp_path)
    with pytest.raises(ExportError, match="conflicting paths"):
        layout_paths(graph, ["1-1", "2-1", "3-1"])


def test_layer_subpath_export_creates_nested_indexes(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, layer="intent", links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2, layer="claims/outer/inner")
    out = tmp_path / "graph"
    result = api.export_view("graph", tmp_path, "1-1", out)
    files = {path.relative_to(out).as_posix() for path in result.files}
    assert "01-claims/outer/INDEX.md" in files
    assert "01-claims/outer/inner/INDEX.md" in files

    stage = (out / "01-claims" / "INDEX.md").read_text(encoding="utf-8")
    assert "[outer/](outer/INDEX.md)" in stage
    outer = (out / "01-claims" / "outer" / "INDEX.md").read_text(encoding="utf-8")
    assert "[inner/](inner/INDEX.md)" in outer
    inner = (out / "01-claims" / "outer" / "inner" / "INDEX.md").read_text(
        encoding="utf-8"
    )
    assert "[2-1 Title of 2-1](2-1.md)" in inner
    assert "← [1-1 Title of 1-1](../../../00-intent/1-1.md) (breaks_down) [derived]" in inner


def test_example_graph_and_tree_show_subpath_headings(monkeypatch, capsys):
    monkeypatch.chdir(EXAMPLES)
    for argv in (["graph"], ["tree", "1-1"]):
        assert main(argv) == 0
        out = capsys.readouterr().out
        assert "  structural/" in out
        assert "  verification/" in out
        assert "  fan-in/" in out


def test_out_is_authored_and_sorted_and_in_is_derived(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, stage=0, links=[{"to": "3", "type": "supports"}, {"to": "2", "type": "supports"}])
    write(nodes, 2, stage=1)
    write(nodes, 3, stage=1)
    graph = build_graph(tmp_path)
    out = render_out(graph, "1-1")
    assert out.splitlines() == ["1-1 -> 2-1 (supports)", "1-1 -> 3-1 (supports)"]
    incoming = render_in(graph, "2-1")
    assert "1-1 -> 2-1 (supports)  [derived]" in incoming
    assert "2-1 -> 1-1" not in incoming


def test_audit_reports_orphan_wide_fanout_duplicate_and_unsorted(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, stage=0, links=[{"to": "3", "type": "supports"}, {"to": "2", "type": "supports"}])
    write(nodes, 2, stage=1)
    write(nodes, 3, stage=1)
    write(nodes, 9, stage=0)
    issues = audit(build_graph(tmp_path), "1-1")
    codes = [issue.code for issue in issues]
    assert "graph-orphan" in codes
    assert "graph-unsorted-links" in codes

    fan = tmp_path / "fan"
    wide = fan / "nodes"
    targets = list(range(2, 203))
    write(wide, 1, stage=0, links=[{"to": str(target), "type": "supports"} for target in targets])
    for target in targets:
        write(wide, target, stage=1)
    assert "graph-wide-fanout" in _codes(build_graph(fan), "1-1")

    duplicate = tmp_path / "duplicate"
    dup_nodes = duplicate / "nodes"
    write(dup_nodes, 1, stage=0, links=[{"to": "2-1", "type": "supports"}, {"to": "2-2", "type": "supports"}])
    write(dup_nodes, 2, version=1, stage=1)
    write(dup_nodes, 2, version=2, stage=1)
    assert "graph-duplicate-version" in _codes(build_graph(duplicate), "1-1")


def test_graph_export_writes_stage_dirs_indexes_and_is_byte_stable(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, stage=0, layer="intent", links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2, stage=1, layer="claims", links=[{"to": "3", "type": "supports"}])
    write(nodes, 3, stage=2, layer="verification")
    out = tmp_path / "graph"
    result = api.export_view("graph", tmp_path, "1-1", out)
    assert result.nodes == 3
    assert (out / "00-intent" / "1-1.md").is_file()
    assert (out / "01-claims" / "2-1.md").is_file()
    assert (out / "02-verification" / "3-1.md").is_file()
    root_index = (out / "INDEX.md").read_text(encoding="utf-8")
    assert "[stage 0 — intent](00-intent/INDEX.md) — 1 node" in root_index
    stage_index = (out / "01-claims" / "INDEX.md").read_text(encoding="utf-8")
    assert "→ [3-1 Title of 3-1](../02-verification/3-1.md) (supports)" in stage_index
    assert "← [1-1 Title of 1-1](../00-intent/1-1.md) (breaks_down) [derived]" in stage_index
    node_paths = [path for path in result.files if path.name != "INDEX.md"]
    assert all(not path.name.endswith("INDEX.md") for path in node_paths)
    first = {
        path.relative_to(out).as_posix(): path.read_bytes()
        for path in sorted(out.rglob("*"))
        if path.is_file()
    }
    api.export_view("graph", tmp_path, "1-1", out, clean=True)
    second = {
        path.relative_to(out).as_posix(): path.read_bytes()
        for path in sorted(out.rglob("*"))
        if path.is_file()
    }
    assert first == second


def test_graph_export_refuses_a_node_path_ending_in_index(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, stage=0, name="INDEX")
    out = tmp_path / "graph"
    with pytest.raises(ExportError, match="INDEX.md"):
        api.export_view("graph", tmp_path, "1-1", out)


def test_scratch_store_renders_and_audits_clean():
    graph = build_graph(EXAMPLES)
    assert graph.roots == ["1-1"]
    assert audit(graph) == []
    assert render_audit(graph) == "no issues\n0 errors, 0 warnings"
    text = render_graph(graph, graph_view(graph, None))
    assert "layer 0 — intent" in text
    assert text.count("[4-1]") == 1
    assert "← in: 2-1 (breaks_down), 3-1 (supports)" in text
    assert "→ out: 9-1 (operates), 10-1 (requires)" in text
    for node in graph.store.nodes.values():
        assert "contains" not in node.meta
        assert "section" not in node.meta
        assert isinstance(node.meta["band"], str) and node.meta["band"].strip()
        assert "layer" not in node.meta
        assert "stage" not in node.meta


def test_scratch_store_dot_and_in_edges():
    graph = build_graph(EXAMPLES)
    refs = graph_view(graph, "1-1")
    dot = render_dot(graph, refs)
    assert "digraph bd_graph {" in dot
    assert 'label="layer 0 — intent"' in dot
    assert '"1-1" [label="1-1\\nVerify the staged graph"];' in dot
    assert '"1-1" -> "2-1" [label="breaks_down"];' in dot
    incoming = render_in(graph, "4")
    assert incoming.startswith("2 in-links  [derived]")
    assert "2-1 -> 4-1 (breaks_down)  [derived]" in incoming
    assert "3-1 -> 4-1 (supports)  [derived]" in incoming


def test_bare_selector_picks_the_highest_version(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, version=1, stage=0, links=[{"to": "2-1", "type": "supports"}])
    write(nodes, 1, version=2, stage=0, links=[{"to": "2-2", "type": "supports"}])
    write(nodes, 2, version=1, stage=1)
    write(nodes, 2, version=2, stage=1)
    graph = build_graph(tmp_path)
    assert resolve_graph_ref(graph, "1") == "1-2"
    assert resolve_graph_ref(graph, "1-1") == "1-1"
    assert graph_view(graph, "1") == ["1-2", "2-2"]


def test_graph_cli_commands_and_exit_status(write, tmp_path, monkeypatch, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, stage=0, links=[{"to": "2", "type": "supports"}])
    write(nodes, 2, stage=1)
    monkeypatch.chdir(tmp_path)
    assert main(["graph"]) == 0
    assert "stage 0 — stage-00" in capsys.readouterr().out
    assert main(["graph", "--dot"]) == 0
    assert "digraph bd_graph" in capsys.readouterr().out
    assert main(["out", "1"]) == 0
    assert "1-1 -> 2-1 (supports)" in capsys.readouterr().out
    assert main(["in", "2"]) == 0
    assert "[derived]" in capsys.readouterr().out
    assert main(["audit"]) == 0
    assert "0 errors, 0 warnings" in capsys.readouterr().out

    write(nodes, 2, stage=0)
    assert main(["audit"]) == 1


def test_example_store_resolves_from_inside_and_by_root(monkeypatch, capsys):
    monkeypatch.chdir(EXAMPLES)
    assert main(["audit"]) == 0
    capsys.readouterr()
    monkeypatch.chdir(EXAMPLES.parent)
    assert main(["--root", "examples", "graph"]) == 0
    assert "layer 0 — intent" in capsys.readouterr().out


# -- phase 2: materialization and mutation -----------------------------------


def test_work_materializes_graph_stage_bands_and_indexes(tmp_path):
    root = _example_store(tmp_path)
    out = root / "bd_work"
    result = api.work(root, "1-1")

    assert result.nodes == 12 and result.symlinks == 12
    assert {path.name for path in out.iterdir() if path.is_dir()} == set(STAGE_DIRS)
    for directory in STAGE_DIRS:
        assert (out / directory / "INDEX.md").is_file()
        assert not (out / directory / "INDEX.md").is_symlink()

    status = api.work(root, status=True)
    assert status.ok
    assert len(status.entries) == 12
    assert {entry.status for entry in status.entries} == {"ok"}

    edited = api.edit_path(root, "4-1")
    assert edited == (
        out / "02-claims" / "structural" / "4-1-two-parents-one-node.md"
    )
    assert edited.is_symlink()
    for directory in ("structural", "verification"):
        assert (out / "02-claims" / directory / "INDEX.md").is_file()
    assert (out / "03-verification" / "fan-in" / "INDEX.md").is_file()
    assert (out / "03-verification" / "fan-in2" / "INDEX.md").is_file()


def test_work_depth_limits_graph_closure_to_link_hops(tmp_path):
    root = _example_store(tmp_path)
    out = root / "bd_work"
    result = api.work(root, "1-1", depth=1)

    assert result.view_ref == "1-1+1" and result.nodes == 3
    assert {path.name for path in out.iterdir() if path.is_dir()} == {
        "00-intent",
        "01-breakdown",
    }
    assert (out / "01-breakdown" / "INDEX.md").is_file()
    assert not (out / "02-claims").exists()
    assert api.work(root, status=True).ok


def test_export_tree_uses_the_graph_stage_layout_and_indexes(tmp_path):
    root = _example_store(tmp_path)
    tree = tmp_path / "tree"
    graph = tmp_path / "graph"

    api.export_view("tree", root, "1-1", tree)
    api.export_view("graph", root, "1-1", graph)

    assert set(_file_map(tree)) == set(_file_map(graph))
    assert sorted(path.name for path in tree.iterdir() if path.is_dir()) == list(
        STAGE_DIRS
    )
    for directory in STAGE_DIRS:
        assert (tree / directory / "INDEX.md").is_file()

    before = _file_map(tree)
    api.export_view("tree", root, "1-1", tree, clean=True)
    assert _file_map(tree) == before


def _mutation_graph(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, stage=0, links=[{"to": "3", "type": "breaks_down"}])
    write(nodes, 2, stage=1)
    write(nodes, 3, stage=1)
    write(nodes, 4, stage=2)
    return nodes


def test_new_on_a_graph_appends_a_link_and_sets_stage_order(write, tmp_path):
    nodes = _mutation_graph(write, tmp_path)
    created = api.new_node(tmp_path, parent="3", fields={"title": "New claim"})

    assert created.name == "5-1.md"
    new_meta = parse_document(created.read_text(encoding="utf-8")).meta
    assert new_meta["stage"] == 2 and new_meta["order"] == 0
    assert "contains" not in new_meta

    parent = parse_document((nodes / "3-1.md").read_text(encoding="utf-8")).meta
    assert {"to": "5-1", "type": "breaks_down"} in parent["links"]
    assert "contains" not in parent

    override = api.new_node(
        tmp_path, parent="4-1", fields={"title": "Later"}, stage=5, order=2
    )
    override_meta = parse_document(override.read_text(encoding="utf-8")).meta
    assert override_meta["stage"] == 5 and override_meta["order"] == 2


def test_link_on_a_graph_refuses_a_back_edge_and_keeps_targets_sorted(
    write, tmp_path
):
    _mutation_graph(write, tmp_path)
    with pytest.raises(BreakdownError, match="strictly forward"):
        api.link(tmp_path, "4-1", "2-1", link_type="supports")

    api.link(tmp_path, "1-1", "4-1", link_type="supports")
    api.link(tmp_path, "1-1", "2-1", link_type="supports")
    links = parse_document(
        (tmp_path / "nodes" / "1-1.md").read_text(encoding="utf-8")
    ).meta["links"]
    targets = [item.get("to") if isinstance(item, dict) else item for item in links]
    assert targets == ["2-1", "3-1", "4-1"]


def test_contain_and_uncontain_refuse_a_graph_store(write, tmp_path):
    _mutation_graph(write, tmp_path)
    for call in (
        lambda: api.contain(tmp_path, "1-1", "2-1"),
        lambda: api.uncontain(tmp_path, "1-1", "3-1"),
    ):
        with pytest.raises(BreakdownError, match="bd link / bd unlink"):
            call()


def test_replace_on_a_graph_repoints_inbound_links_and_root(write, tmp_path):
    _mutation_graph(write, tmp_path)
    api.clone(tmp_path, "3-1")
    assert api.replace(tmp_path, "3-1", "3-2") == ("3-1", "links", "3-2")
    links = parse_document(
        (tmp_path / "nodes" / "1-1.md").read_text(encoding="utf-8")
    ).meta["links"]
    assert {"to": "3-2", "type": "breaks_down"} in links

    (tmp_path / "ROOT").write_text("1-1\n", encoding="utf-8")
    api.clone(tmp_path, "1-1")
    assert api.replace(tmp_path, "1-1", "1-2") == ("1-1", "ROOT", "1-2")
    assert (tmp_path / "ROOT").read_text(encoding="utf-8") == "1-2\n"


def test_clone_subtree_on_a_graph_rewires_edges_among_the_copies(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, stage=0, links=[{"to": "2", "type": "breaks_down"}, {"to": "3", "type": "breaks_down"}])
    write(nodes, 2, stage=1, links=[{"to": "4", "type": "supports"}])
    write(nodes, 3, stage=1)
    write(nodes, 4, stage=2)

    pairs = dict(api.clone(tmp_path, "1-1", subtree=True))
    assert pairs == {"1-1": "1-2", "2-1": "2-2", "3-1": "3-2", "4-1": "4-2"}
    root_links = parse_document(
        (nodes / "1-2.md").read_text(encoding="utf-8")
    ).meta["links"]
    assert {"to": "2-2", "type": "breaks_down"} in root_links
    assert {"to": "3-2", "type": "breaks_down"} in root_links
    mid_links = parse_document(
        (nodes / "2-2.md").read_text(encoding="utf-8")
    ).meta["links"]
    assert {"to": "4-2", "type": "supports"} in mid_links


def test_delete_on_a_graph_uses_link_reachability(write, tmp_path):
    _mutation_graph(write, tmp_path)
    with pytest.raises(BreakdownError, match="reachable|referenced"):
        api.delete(tmp_path, "3-1")
    api.delete(tmp_path, "3-1", force=True)
    assert not (tmp_path / "nodes" / "3-1.md").exists()

    write(tmp_path / "nodes", 9, stage=4)
    api.delete(tmp_path, "9-1")
    assert not (tmp_path / "nodes" / "9-1.md").exists()


# -- mode guard and graph-only exports ----------------------------------------


def test_build_graph_refuses_a_containment_store(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2)
    with pytest.raises(BreakdownError, match="this store is containment"):
        build_graph(tmp_path)


def test_graph_commands_refuse_a_containment_store(
    write, tmp_path, monkeypatch, capsys
):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"])
    write(nodes, 2)
    monkeypatch.chdir(tmp_path)
    commands = [
        ["audit"],
        ["graph"],
        ["out", "1-1"],
        ["in", "1-1"],
        [
            "export",
            "graph",
            "--view",
            "1-1",
            "--out",
            str(tmp_path / "out"),
        ],
    ]
    for argv in commands:
        assert main(argv) == 2
        err = capsys.readouterr().err
        assert "this store is containment; graph commands need links and stages" in err


def test_graph_export_context_and_dot(tmp_path):
    root = _example_store(tmp_path)
    context = api.export_view("context", root, "1-1", tmp_path / "ctx")
    assert context.nodes == 12
    assert (tmp_path / "ctx" / "STALE.md").is_file()
    dot_file = tmp_path / "graph.dot"
    dot = api.export_view("dot", root, "1-1", dot_file)
    assert dot.nodes == 12
    text = dot_file.read_text(encoding="utf-8")
    assert text.startswith("digraph bd_tree {")
    assert '"1-1"' in text
    assert "->" in text
