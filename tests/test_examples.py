"""The committed example store is a clean undirected graph example."""

from __future__ import annotations

import shutil
from pathlib import Path

from bd_tree import api
from bd_tree.graph import (
    audit,
    build_graph,
    graph_view,
    layout_paths,
    render_in,
    render_out,
)

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
DOCS_BREAKDOWN = Path(__file__).resolve().parents[1] / "docs" / "breakdown"
REFS = {f"{node}-1" for node in range(1, 13)}
PLACEMENT_KEYS = ("band", "subpath", "layer", "stage", "order")
ROOT_HINTS = ("band_layout", "band_order")


def _example_store(tmp_path: Path) -> Path:
    shutil.copytree(EXAMPLES / ".bd_tree", tmp_path / ".bd_tree")
    return tmp_path


def _relative_files(out: Path) -> set[str]:
    return {
        path.relative_to(out).as_posix()
        for path in out.rglob("*")
        if path.is_file()
    }


def test_example_store_is_a_clean_graph():
    hidden = api.load(EXAMPLES / ".bd_tree")
    assert hidden.root == (EXAMPLES / ".bd_tree").resolve()
    assert hidden.project_root == EXAMPLES.resolve()
    store = api.load(EXAMPLES)
    assert store.root == hidden.root
    assert store.root_ref == "1-1"
    assert len(store.nodes) == 12
    assert set(store.nodes) == REFS

    for node in store.nodes.values():
        assert not (set(PLACEMENT_KEYS) & set(node.meta))
        assert "contains" not in node.meta
        assert "section" not in node.meta

    graph = build_graph(EXAMPLES)
    assert graph.roots == ["1-1"]
    assert audit(graph) == []


def test_undirected_component_reaches_every_node():
    graph = build_graph(EXAMPLES)
    refs = graph_view(graph, "1-1")
    assert len(refs) == 12
    assert set(refs) == REFS
    assert graph.distance["1-1"] == 0
    assert graph.distance["11-1"] == 4


def test_two_parent_node_has_two_derived_in_edges():
    graph = build_graph(EXAMPLES)
    incoming = render_in(graph, "4-1")
    assert incoming.startswith("2 in-links  [derived]")
    assert "2-1 -> 4-1 (breaks_down)  [derived]" in incoming
    assert "3-1 -> 4-1 (supports)  [derived]" in incoming


def test_verification_core_is_a_distance_three_fanout():
    graph = build_graph(EXAMPLES)
    core = graph.store.nodes["12-1"]
    assert not (set(PLACEMENT_KEYS) & set(core.meta))
    assert graph.distance["12-1"] == 3
    assert render_out(graph, "12-1").splitlines() == [
        "12-1 -> 8-1 (breaks_down)",
        "12-1 -> 11-1 (breaks_down)",
    ]

    incoming = render_in(graph, "11-1")
    assert incoming.startswith("2 in-links  [derived]")
    assert "8-1 -> 11-1 (breaks_down)  [derived]" in incoming
    assert "12-1 -> 11-1 (breaks_down)  [derived]" in incoming

    paths = layout_paths(graph)
    assert paths["12-1"].as_posix() == "12-1.md"
    assert paths["8-1"].as_posix() == "8-1.md"
    assert paths["11-1"].as_posix() == "11-1.md"


def test_example_graph_export_writes_one_flat_ring_index(tmp_path):
    out = (tmp_path / "graph").resolve()
    result = api.export_view("graph", EXAMPLES, "1-1", out)
    assert result.nodes == 12

    generated = {
        path.relative_to(out).as_posix()
        for path in result.files
        if path.name == "INDEX.md"
    }
    assert generated == {"INDEX.md"}

    root = (out / "INDEX.md").read_text(encoding="utf-8")
    assert "## 0 — 1-1" in root
    assert "## 1 — children" in root
    assert "## 2" in root
    assert "## 3" in root
    assert "## 4" in root
    assert "[12-1 Verification core](12-1.md)" in root
    assert "[8-1 Verification fan-in](8-1.md)" in root


def test_example_nodes_declare_no_placement_keys():
    graph = build_graph(EXAMPLES)
    for node in graph.store.nodes.values():
        assert not (set(PLACEMENT_KEYS) & set(node.meta))
        assert "group" not in node.meta
    paths = layout_paths(graph)
    assert {path.as_posix() for path in paths.values()} == {
        f"{ref}.md" for ref in REFS
    }


def test_example_work_is_flat_and_edit_resolves(tmp_path):
    root = _example_store(tmp_path)
    out = root / "bd_work"
    result = api.work(root, "1-1")

    assert result.nodes == 12 and result.symlinks == 12
    for ref in REFS:
        assert (out / f"{ref}.md").is_symlink()
    for name in ("INDEX.md", "REFS.md", "AGENTS.md"):
        assert (out / name).is_file() and not (out / name).is_symlink()

    assert api.edit_path(root, "5-1") == out / "5-1.md"
    assert api.edit_path(root, "7-1") == out / "7-1.md"
    assert api.edit_path(root, "8-1") == out / "8-1.md"
    assert api.edit_path(root, "12-1") == out / "12-1.md"

    index = (out / "INDEX.md").read_text(encoding="utf-8")
    assert "## Active" in index
    assert "## Distance 1 — children" in index
    assert "## Distance 2" in index
    refs = (out / "REFS.md").read_text(encoding="utf-8")
    assert "| Distance |" in refs
    assert "| `1-1.md` | 1-1 | active | 0 |" in refs

    status = api.work(root, status=True)
    assert status.ok
    assert len(status.entries) == 12
    assert {entry.status for entry in status.entries} == {"ok"}


def test_example_graph_export_uses_the_flat_file_set(tmp_path):
    root = _example_store(tmp_path)
    graph = tmp_path / "graph"
    api.export_view("graph", root, "1-1", graph)

    assert _relative_files(graph) == {f"{ref}.md" for ref in REFS} | {"INDEX.md"}


def test_cycles_are_legal_in_one_component(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "supports"}])
    write(nodes, 2, links=[{"to": "3", "type": "supports"}])
    write(nodes, 3, links=[{"to": "1", "type": "supports"}])

    result = api.check(tmp_path)
    assert result.ok
    assert not result.warnings

    graph = build_graph(tmp_path)
    assert graph.roots == ["1-1"]
    assert set(graph_view(graph, "1-1")) == {"1-1", "2-1", "3-1"}
    assert graph.distance == {"1-1": 0, "2-1": 1, "3-1": 1}
    assert audit(graph) == []


def test_migration_strips_placement_keys_and_keeps_the_graph(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        band="root",
        order=0,
        band_layout="flat",
        band_order=["root", "child"],
        links=[{"to": "2", "type": "breaks_down"}],
        body="root body\n",
    )
    write(
        nodes,
        2,
        band="child",
        subpath="sub",
        layer="older",
        stage=2,
        order=3,
        body="child body\n",
    )
    (tmp_path / "ROOT").write_text("1-1\n", encoding="utf-8")
    before = api.load(tmp_path)

    api.migrate(tmp_path)

    store = api.load(tmp_path)
    assert set(store.nodes) == set(before.nodes)
    for ref, node in store.nodes.items():
        assert not (set(PLACEMENT_KEYS) & set(node.meta))
        assert node.body == before.nodes[ref].body
        assert node.title == before.nodes[ref].title
        assert [(link.to, link.type) for link in node.links] == [
            (link.to, link.type) for link in before.nodes[ref].links
        ]
    assert not (set(ROOT_HINTS) & set(store.nodes["1-1"].meta))
    assert api.check(tmp_path).ok


def test_breakdown_store_checks_clean_after_migration(tmp_path):
    shutil.copytree(DOCS_BREAKDOWN / ".bd_tree", tmp_path / ".bd_tree")
    api.migrate(tmp_path)

    result = api.check(tmp_path)
    assert result.ok
    assert not result.warnings

    store = api.load(tmp_path)
    assert store.model == "graph"
    assert store.root_ref == "1-1"
    assert len(store.nodes) == 59
    for node in store.nodes.values():
        assert not (set(PLACEMENT_KEYS) & set(node.meta))
    assert not (set(ROOT_HINTS) & set(store.nodes["1-1"].meta))

    # After migration every link is a plain typed token in a node body:
    # collect (from, type, to) triples parsed from the bodies.
    triples = {
        (node.ref, link.type, link.to)
        for node in store.nodes.values()
        for link in node.links
    }
    assert triples
    assert {
        "realizes",
        "implements",
        "verifies",
        "operates",
        "changes",
    } <= {triple[1] for triple in triples}

    graph = build_graph(tmp_path)
    assert graph.roots == ["1-1"]
    assert set(graph_view(graph, "1-1")) == set(store.nodes)
    assert audit(graph) == []
