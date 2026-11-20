"""Store discovery: project roots, hidden stores, and classic stores."""

from __future__ import annotations

from bd_tree.api import load, load_view
from bd_tree.cli import _find_root, main


def test_load_accepts_project_root_and_store_root(write, tmp_path):
    write(tmp_path / ".bd_tree" / "nodes", 1, contains=[])
    project = load(tmp_path)
    store = load(tmp_path / ".bd_tree")
    assert project.root == (tmp_path / ".bd_tree").resolve()
    assert project.root == store.root
    assert set(project.nodes) == {"1"}
    assert set(load_view(tmp_path, "1").nodes) == {"1"}


def test_discovery_walks_up_to_the_hidden_store(write, tmp_path, monkeypatch):
    write(tmp_path / ".bd_tree" / "nodes", 1, contains=[])
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BD_ROOT", raising=False)
    assert _find_root(None) == (tmp_path / ".bd_tree").resolve()
    monkeypatch.chdir(nested)
    assert _find_root(None) == (tmp_path / ".bd_tree").resolve()


def test_root_option_and_env_accept_the_project_root(
    write, tmp_path, monkeypatch, capsys
):
    write(tmp_path / ".bd_tree" / "nodes", 1, contains=[])
    monkeypatch.delenv("BD_ROOT", raising=False)
    assert main(["check", "--root", str(tmp_path)]) == 0
    assert "0 errors" in capsys.readouterr().out

    monkeypatch.setenv("BD_ROOT", str(tmp_path))
    assert _find_root(None) == (tmp_path / ".bd_tree").resolve()
    assert main(["tree", "1"]) == 0
    assert "1" in capsys.readouterr().out


def test_classic_nodes_wins_over_a_hidden_store(write, tmp_path, monkeypatch):
    write(tmp_path / "nodes", 1, contains=[])
    write(tmp_path / ".bd_tree" / "nodes", 2, contains=[])
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BD_ROOT", raising=False)
    store = load(tmp_path)
    assert store.root == tmp_path.resolve()
    assert store.project_root == tmp_path.resolve()
    assert set(store.nodes) == {"1"}
    assert _find_root(None) == tmp_path.resolve()


def test_empty_directory_reports_both_layouts(tmp_path):
    store = load(tmp_path)
    issue = next(issue for issue in store.issues if issue.code == "missing-nodes-dir")
    assert "nodes/" in issue.message
    assert ".bd_tree/nodes" in issue.message
