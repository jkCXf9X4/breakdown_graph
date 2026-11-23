"""Graph mode: forward links, stage ordering, audit and export."""

from __future__ import annotations

from pathlib import Path

import pytest

from bd_tree import api
from bd_tree.cli import main
from bd_tree.errors import ExportError
from bd_tree.graph import (
    audit,
    build_graph,
    graph_layout,
    graph_view,
    render_audit,
    render_dot,
    render_graph,
    render_in,
    render_out,
    resolve_graph_ref,
)

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


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
    assert "stage 0 — intent" in text
    assert text.count("[4-1]") == 1
    assert "← in: 2-1 (breaks_down), 3-1 (supports)" in text
    assert "→ out: 9-1 (operates), 10-1 (requires)" in text
    for node in graph.store.nodes.values():
        assert "contains" not in node.meta
        assert "section" not in node.meta
        assert isinstance(node.meta["stage"], int)
        assert node.meta["layer"]


def test_scratch_store_dot_and_in_edges():
    graph = build_graph(EXAMPLES)
    refs = graph_view(graph, "1-1")
    dot = render_dot(graph, refs)
    assert "digraph bd_graph {" in dot
    assert '"1-1" [label="1-1 Verify the staged graph"];' in dot
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
    assert "stage 0 — intent" in capsys.readouterr().out
