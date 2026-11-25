"""Graph mode: undirected rings, audit, rendering and flat export."""

from __future__ import annotations

from pathlib import Path

import pytest

from bd_tree import api
from bd_tree.cli import main
from bd_tree.errors import ExportError
from bd_tree.graph import (
    audit,
    build_graph,
    graph_view,
    layout_paths,
    render_audit,
    render_dot,
    render_graph,
    render_in,
    render_out,
    resolve_graph_ref,
    ring_distances,
)

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _codes(graph, anchor=None):
    return [issue.code for issue in audit(graph, anchor)]


# -- rings -------------------------------------------------------------------


def test_ring_distances_maps_every_reachable_ref(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2, links=[{"to": "3", "type": "supports"}])
    write(nodes, 3)
    write(nodes, 9)
    graph = build_graph(tmp_path)
    assert ring_distances(graph.store, "1-1") == {"1-1": 0, "2-1": 1, "3-1": 2}
    assert ring_distances(graph, None) == {"1-1": 0, "2-1": 1, "3-1": 2}
    assert ring_distances(graph.store, "9-1") == {"9-1": 0}
    assert ring_distances(graph.store, "99-1") == {}


def test_a_cycle_loads_and_rings_use_the_minimum_distance(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "supports"}])
    write(nodes, 2, links=[{"to": "3", "type": "supports"}])
    write(nodes, 3, links=[{"to": "1", "type": "supports"}])
    graph = build_graph(tmp_path)
    assert audit(graph, "1-1") == []
    # The closing 3 -> 1 edge makes 3-1 a ring-1 neighbour of the anchor.
    assert ring_distances(graph.store, "1-1") == {"1-1": 0, "2-1": 1, "3-1": 1}
    refs = graph_view(graph, "1-1")
    assert refs.count("1-1") == 1 and set(refs) == {"1-1", "2-1", "3-1"}


def test_a_reciprocal_pair_is_legal_and_not_a_back_edge(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "supports"}])
    write(nodes, 2, links=[{"to": "1", "type": "supports"}])
    graph = build_graph(tmp_path)
    assert _codes(graph, "1-1") == []
    assert graph.store.neighbors("1-1")[0].kind == "child"
    assert graph.store.neighbors("2-1")[0].kind == "child"


def test_dangling_link_is_an_error(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "9-1", "type": "breaks_down"}])
    issues = audit(build_graph(tmp_path), "1-1")
    assert any(issue.code == "graph-dangling-link" for issue in issues)


def test_two_parent_node_appears_once_in_the_component(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[
            {"to": "2", "type": "breaks_down"},
            {"to": "3", "type": "breaks_down"},
        ],
    )
    write(nodes, 2, links=[{"to": "4", "type": "supports"}])
    write(nodes, 3, links=[{"to": "4", "type": "supports"}])
    write(nodes, 4)
    refs = graph_view(build_graph(tmp_path), "1-1")
    assert refs.count("4-1") == 1
    assert set(refs) == {"1-1", "2-1", "3-1", "4-1"}


def test_type_and_distance_filters(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[
            {"to": "2", "type": "supports"},
            {"to": "3", "type": "refutes"},
        ],
    )
    write(nodes, 2, links=[{"to": "4", "type": "supports"}])
    write(nodes, 3, links=[{"to": "5", "type": "refutes"}])
    write(nodes, 4)
    write(nodes, 5)
    graph = build_graph(tmp_path)
    assert set(graph_view(graph, "1-1", types=["supports"])) == {"1-1", "2-1", "4-1"}
    # A distance window hides nodes but traversal continues through them.
    assert set(graph_view(graph, "1-1", distance=(1, 1))) == {"1-1", "2-1", "3-1"}
    assert set(graph_view(graph, "1-1", distance="2:2")) == {"1-1", "4-1", "5-1"}
    assert set(graph_view(graph, "1-1", distance=1)) == {"1-1", "2-1", "3-1"}
    assert set(graph_view(graph, "1-1", depth=1)) == {"1-1", "2-1", "3-1"}


# -- layout ------------------------------------------------------------------


def test_layout_paths_is_flat_and_uses_store_basenames(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "x"}])
    write(nodes, 2)
    paths = layout_paths(build_graph(tmp_path))
    assert paths == {"1-1": Path("1-1.md"), "2-1": Path("2-1.md")}


def test_layout_paths_template_placeholders_and_front_matter(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "x"}], audience="ops")
    write(nodes, 2, audience="ops")
    graph = build_graph(tmp_path)
    paths = layout_paths(graph, "{distance}/{audience}/{slug}.md")
    assert paths["1-1"].as_posix() == "0/ops/title-of-1-1.md"
    assert paths["2-1"].as_posix() == "1/ops/title-of-2-1.md"
    # The fixture always writes ``summary``, so any front-matter key works.
    assert layout_paths(graph, "{summary}/{ref}.md")["2-1"].as_posix() == (
        "summary/2-1.md"
    )


def test_layout_paths_template_drops_band_and_folder(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1)
    graph = build_graph(tmp_path)
    with pytest.raises(ExportError, match="band"):
        layout_paths(graph, "{band}/{ref}.md")
    with pytest.raises(ExportError, match="folder"):
        layout_paths(graph, "{folder}/{ref}.md")


def test_layout_paths_collision_appends_the_ref(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1)
    write(nodes, 2)
    paths = layout_paths(build_graph(tmp_path), "same.md")
    assert paths["1-1"].as_posix() == "same.md"
    assert paths["2-1"].as_posix() == "same-2-1.md"


# -- text and dot ------------------------------------------------------------


def test_render_graph_ring_headings_split_ring_one(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[
            {"to": "2", "type": "breaks_down"},
            {"to": "4", "type": "references"},
        ],
    )
    write(nodes, 2)
    write(nodes, 3, links=[{"to": "1", "type": "serves"}])
    write(nodes, 4)
    graph = build_graph(tmp_path)
    text = render_graph(graph, graph_view(graph, "1-1"))
    assert "## 0 — 1-1" in text
    assert text.index("## 1 — children") < text.index("## 1 — parents")
    assert "## 1 — peers" not in text
    assert text.count("[4-1]") == 1


def test_example_graph_renders_rings_and_audits_clean():
    graph = build_graph(EXAMPLES)
    refs = graph_view(graph, None)
    assert graph.anchor == "1-1"
    assert graph.roots == ["1-1"]
    assert audit(graph) == []
    text = render_graph(graph, refs)
    assert "## 0 — 1-1" in text
    assert "## 1 — children" in text
    assert "← in: 2-1 (breaks_down), 3-1 (supports)" in text
    assert "→ out: 9-1 (operates), 10-1 (requires)" in text
    assert text.count("[4-1]") == 1
    assert render_audit(graph) == "no issues\n0 errors, 0 warnings"


def test_out_is_authored_and_sorted_and_in_is_derived(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[
            {"to": "3", "type": "supports"},
            {"to": "2", "type": "supports"},
        ],
    )
    write(nodes, 2)
    write(nodes, 3)
    graph = build_graph(tmp_path)
    out = render_out(graph, "1-1")
    assert out.splitlines() == ["1-1 -> 2-1 (supports)", "1-1 -> 3-1 (supports)"]
    incoming = render_in(graph, "2-1")
    assert "1-1 -> 2-1 (supports)  [derived]" in incoming
    assert "2-1 -> 1-1" not in incoming


def test_render_dot_has_no_band_clusters_and_labels_edges():
    graph = build_graph(EXAMPLES)
    refs = graph_view(graph, "1-1")
    dot = render_dot(graph, refs)
    assert "subgraph cluster_" not in dot
    assert "rankdir=LR;" in dot
    assert '"1-1" [label="1-1\\nVerify the undirected graph"' in dot
    assert '"1-1" -> "2-1" [label="breaks_down"];' in dot
    assert '"4-1" -> "8-1" [label="supports"];' in dot
    assert dot.count('-> "4-1"') == 2
    assert '"4-1" -> "2-1"' not in dot
    assert render_dot(graph, refs) == dot


# -- audit -------------------------------------------------------------------


def test_audit_reports_orphan_wide_fanout_duplicate_and_unsorted(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[
            {"to": "3", "type": "supports"},
            {"to": "2", "type": "supports"},
        ],
    )
    write(nodes, 2)
    write(nodes, 3)
    write(nodes, 9)
    issues = audit(build_graph(tmp_path), "1-1")
    codes = [issue.code for issue in issues]
    assert "graph-orphan" in codes
    assert "graph-unsorted-links" in codes

    fan = tmp_path / "fan"
    wide = fan / "nodes"
    targets = list(range(2, 203))
    write(
        wide,
        1,
        links=[{"to": str(target), "type": "supports"} for target in targets],
    )
    for target in targets:
        write(wide, target)
    assert "graph-wide-fanout" in _codes(build_graph(fan), "1-1")

    duplicate = tmp_path / "duplicate"
    dup_nodes = duplicate / "nodes"
    write(
        dup_nodes,
        1,
        links=[
            {"to": "2-1", "type": "supports"},
            {"to": "2-2", "type": "supports"},
        ],
    )
    write(dup_nodes, 2, version=1)
    write(dup_nodes, 2, version=2)
    assert "graph-duplicate-version" in _codes(build_graph(duplicate), "1-1")


# -- export ------------------------------------------------------------------


def test_graph_export_is_flat_with_ring_sections_and_byte_stable(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2, links=[{"to": "3", "type": "supports"}])
    write(nodes, 3)
    out = tmp_path / "graph"
    result = api.pack(tmp_path, "1-1", out, fresh=False)
    assert result.nodes == 3
    assert {path.name for path in result.files} == {
        "1-1.md",
        "2-1.md",
        "3-1.md",
        "INDEX.md",
    }
    assert not any(path.is_dir() for path in out.iterdir())
    root_index = (out / "INDEX.md").read_text(encoding="utf-8")
    assert "## 0 — 1-1" in root_index
    assert "## 1 — children" in root_index
    assert "[2-1 Title of 2-1](2-1.md)" in root_index
    first = {
        path.relative_to(out).as_posix(): path.read_bytes()
        for path in sorted(out.rglob("*"))
        if path.is_file()
    }
    api.pack(tmp_path, "1-1", out, fresh=False, clean=True)
    second = {
        path.relative_to(out).as_posix(): path.read_bytes()
        for path in sorted(out.rglob("*"))
        if path.is_file()
    }
    assert first == second


# -- selectors and CLI -------------------------------------------------------


def test_bare_selector_picks_the_highest_version(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, version=1, links=[{"to": "2-1", "type": "supports"}])
    write(nodes, 1, version=2, links=[{"to": "2-2", "type": "supports"}])
    write(nodes, 2, version=1)
    write(nodes, 2, version=2)
    graph = build_graph(tmp_path)
    assert resolve_graph_ref(graph, "1") == "1-2"
    assert resolve_graph_ref(graph, "1-1") == "1-1"
    assert graph_view(graph, "1") == ["1-2", "2-2"]


def test_graph_cli_commands_and_exit_status(write, tmp_path, monkeypatch, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "supports"}])
    write(nodes, 2)
    monkeypatch.chdir(tmp_path)
    assert main(["graph"]) == 0
    out = capsys.readouterr().out
    assert "## 0 — 1-1" in out
    assert main(["graph", "--format", "dot"]) == 0
    assert "digraph bd_graph" in capsys.readouterr().out
    assert main(["out", "1"]) == 0
    assert "1-1 -> 2-1 (supports)" in capsys.readouterr().out
    assert main(["in", "2"]) == 0
    assert "[derived]" in capsys.readouterr().out
    assert main(["check"]) == 0
    assert "0 errors, 0 warnings" in capsys.readouterr().out

    # A cycle and a reciprocal edge are legal now.
    write(nodes, 2, links=[{"to": "1", "type": "supports"}])
    assert main(["check"]) == 0


def test_example_store_resolves_from_inside_and_by_root(monkeypatch, capsys):
    monkeypatch.chdir(EXAMPLES)
    assert main(["check"]) == 0
    capsys.readouterr()
    monkeypatch.chdir(EXAMPLES.parent)
    assert main(["--root", "examples", "graph"]) == 0
    assert "## 0 — 1-1" in capsys.readouterr().out
