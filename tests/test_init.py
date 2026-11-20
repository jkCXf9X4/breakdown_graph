from __future__ import annotations

from bd_tree.api import check, init_store
from bd_tree.cli import main
from bd_tree.frontmatter import parse_document

EXPECTED = (
    "---\n"
    "id: 1\n"
    "title: Root\n"
    "contains: []\n"
    "---\n"
    "# Root\n"
    "\n"
    "State the intent of this graph here.\n"
)

GITIGNORE = "# generated work area (bd work)\nbd_work/\n"


def test_init_creates_hidden_store_and_gitignore(tmp_path):
    project = tmp_path / "store"
    root = init_store(project)
    assert root == project.resolve()
    path = project / ".bd_tree" / "nodes" / "1-1.md"
    assert path.is_file()
    assert path.read_text(encoding="utf-8") == EXPECTED
    assert (project / ".gitignore").read_text(encoding="utf-8") == GITIGNORE
    result = check(project)
    assert result.ok
    assert result.nodes_scanned == 1
    assert main(["check", "--root", str(project)]) == 0


def test_init_refuses_non_empty_hidden_store_and_keeps_it(tmp_path, capsys):
    nodes = tmp_path / ".bd_tree" / "nodes"
    nodes.mkdir(parents=True)
    existing = nodes / "2.md"
    existing.write_text("keep me\n", encoding="utf-8")
    assert main(["init", str(tmp_path)]) == 2
    assert "store already exists at" in capsys.readouterr().err
    assert existing.read_text(encoding="utf-8") == "keep me\n"
    assert not (nodes / "1-1.md").exists()


def test_init_refuses_non_empty_legacy_store_and_keeps_it(tmp_path, capsys):
    nodes = tmp_path / "nodes"
    nodes.mkdir()
    existing = nodes / "2.md"
    existing.write_text("keep me\n", encoding="utf-8")
    assert main(["init", str(tmp_path)]) == 2
    assert "store already exists at" in capsys.readouterr().err
    assert existing.read_text(encoding="utf-8") == "keep me\n"
    assert not (tmp_path / ".bd_tree").exists()


def test_init_appends_gitignore_without_rewriting_other_lines(tmp_path):
    ignore = tmp_path / ".gitignore"
    ignore.write_text("# mine\nbuild/\n", encoding="utf-8")
    assert init_store(tmp_path) == tmp_path.resolve()
    assert ignore.read_text(encoding="utf-8") == "# mine\nbuild/\nbd_work/\n"


def test_init_does_not_duplicate_an_existing_gitignore_entry(tmp_path):
    ignore = tmp_path / ".gitignore"
    ignore.write_text("bd_work/\n", encoding="utf-8")
    init_store(tmp_path)
    assert ignore.read_text(encoding="utf-8") == "bd_work/\n"


def test_init_default_dir_is_cwd(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init"]) == 0
    assert (tmp_path / ".bd_tree" / "nodes" / "1-1.md").is_file()
    assert "store initialized at" in capsys.readouterr().out


def test_init_prints_next_steps(tmp_path, capsys):
    assert main(["init", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    root = str(tmp_path.resolve())
    assert f"store initialized at {root}\n" in out
    assert (
        "next:\n"
        f"  cd {root}\n"
        '  bd new --parent 1-1 --field title="First claim" --field layer=claims\n'
        "  bd tree 1-1\n"
        "  bd work 1-1\n"
    ) in out


def test_tree_shows_root_after_init(tmp_path, capsys):
    assert main(["init", str(tmp_path)]) == 0
    capsys.readouterr()
    assert main(["tree", "1-1", "--root", str(tmp_path)]) == 0
    assert "Root" in capsys.readouterr().out
    assert parse_document(
        (tmp_path / ".bd_tree" / "nodes" / "1-1.md").read_text(encoding="utf-8")
    ).meta == {"id": 1, "title": "Root", "contains": []}


def test_init_root_has_no_placement_fields_and_fresh_store_checks_clean(tmp_path):
    project = tmp_path / "store"
    init_store(project)
    meta = parse_document(
        (project / ".bd_tree" / "nodes" / "1-1.md").read_text(encoding="utf-8")
    ).meta
    assert meta == {"id": 1, "title": "Root", "contains": []}
    result = check(project)
    assert result.ok
    assert result.issues == []
    assert result.nodes_scanned == 1
