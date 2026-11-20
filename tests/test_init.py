from __future__ import annotations

from bd_tree.api import check, init_store
from bd_tree.cli import main
from bd_tree.frontmatter import parse_document

EXPECTED = (
    "---\n"
    "id: 1\n"
    "title: Root\n"
    "home: 1.md\n"
    "contains: []\n"
    "---\n"
    "# Root\n"
    "\n"
    "State the intent of this graph here.\n"
)


def test_init_creates_root_node_and_check_passes(tmp_path):
    store = tmp_path / "store"
    root = init_store(store)
    assert root == store.resolve()
    path = store / "nodes" / "1.md"
    assert path.is_file()
    assert path.read_text(encoding="utf-8") == EXPECTED
    result = check(store)
    assert result.ok
    assert result.nodes_scanned == 1
    assert main(["check", "--root", str(store)]) == 0


def test_init_refuses_existing_nodes_and_keeps_them(tmp_path, capsys):
    nodes = tmp_path / "nodes"
    nodes.mkdir()
    existing = nodes / "2.md"
    existing.write_text("keep me\n", encoding="utf-8")
    assert main(["init", str(tmp_path)]) == 2
    assert "store already exists at" in capsys.readouterr().err
    assert existing.read_text(encoding="utf-8") == "keep me\n"
    assert not (nodes / "1.md").exists()


def test_init_default_dir_is_cwd(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init"]) == 0
    assert (tmp_path / "nodes" / "1.md").is_file()
    assert "store initialized at" in capsys.readouterr().out


def test_init_prints_next_steps(tmp_path, capsys):
    assert main(["init", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    root = str(tmp_path.resolve())
    assert f"store initialized at {root}\n" in out
    assert (
        "next:\n"
        f"  cd {root}\n"
        '  bd new --parent 1 --field title="First claim" --field layer=claims\n'
        "  bd tree 1\n"
        "  bd work 1\n"
    ) in out


def test_tree_shows_root_after_init(tmp_path, capsys):
    assert main(["init", str(tmp_path)]) == 0
    capsys.readouterr()
    assert main(["tree", "1", "--root", str(tmp_path)]) == 0
    assert "Root" in capsys.readouterr().out
    assert parse_document(
        (tmp_path / "nodes" / "1.md").read_text(encoding="utf-8")
    ).meta == {"id": 1, "title": "Root", "home": "1.md", "contains": []}
