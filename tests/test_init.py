from __future__ import annotations

from bdg.api import check, init_store
from bdg.cli import main
from bdg.frontmatter import parse_document

EXPECTED = (
    "---\n"
    "id: 1\n"
    "title: Root\n"
    "---\n"
    "# Root\n"
    "\n"
    "State the intent of this graph here.\n"
)

GITIGNORE = "# generated work area (bdg work)\nbdg_work/\n"


def test_init_creates_hidden_store_and_gitignore(tmp_path):
    project = tmp_path / "store"
    root = init_store(project)
    assert root == project.resolve()
    path = project / "bdg_graph" / "nodes" / "1-1.md"
    assert path.is_file()
    assert path.read_text(encoding="utf-8") == EXPECTED
    assert (project / ".gitignore").read_text(encoding="utf-8") == GITIGNORE
    result = check(project)
    assert result.ok
    assert result.nodes_scanned == 1
    assert main(["check", "--root", str(project)]) == 0


def test_init_refuses_non_empty_hidden_store_and_keeps_it(tmp_path, capsys):
    nodes = tmp_path / "bdg_graph" / "nodes"
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
    assert not (tmp_path / "bdg_graph").exists()


def test_init_appends_gitignore_without_rewriting_other_lines(tmp_path):
    ignore = tmp_path / ".gitignore"
    ignore.write_text("# mine\nbuild/\n", encoding="utf-8")
    assert init_store(tmp_path) == tmp_path.resolve()
    assert ignore.read_text(encoding="utf-8") == "# mine\nbuild/\nbdg_work/\n"


def test_init_does_not_duplicate_an_existing_gitignore_entry(tmp_path):
    ignore = tmp_path / ".gitignore"
    ignore.write_text("bdg_work/\n", encoding="utf-8")
    init_store(tmp_path)
    assert ignore.read_text(encoding="utf-8") == "bdg_work/\n"


def test_init_default_dir_is_cwd(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init"]) == 0
    assert (tmp_path / "bdg_graph" / "nodes" / "1-1.md").is_file()
    assert "store initialized at" in capsys.readouterr().out


def test_init_prints_next_steps(tmp_path, capsys):
    assert main(["init", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    root = str(tmp_path.resolve())
    assert f"store initialized at {root}\n" in out
    assert (
        "next:\n"
        f"  cd {root}\n"
        '  bdg new --parent 1-1 --field title="First claim"\n'
        "  bdg graph 1-1\n"
        "  bdg work 1-1\n"
    ) in out


def test_graph_shows_root_after_init(tmp_path, capsys):
    assert main(["init", str(tmp_path)]) == 0
    capsys.readouterr()
    assert main(["graph", "1-1", "--root", str(tmp_path)]) == 0
    assert "Root" in capsys.readouterr().out
    assert parse_document(
        (tmp_path / "bdg_graph" / "nodes" / "1-1.md").read_text(encoding="utf-8")
    ).meta == {"id": 1, "title": "Root"}


def test_init_root_has_no_placement_and_fresh_store_checks_clean(tmp_path):
    project = tmp_path / "store"
    init_store(project)
    meta = parse_document(
        (project / "bdg_graph" / "nodes" / "1-1.md").read_text(encoding="utf-8")
    ).meta
    assert meta == {"id": 1, "title": "Root"}
    result = check(project)
    assert result.ok
    assert result.issues == []
    assert result.nodes_scanned == 1


def test_init_default_graph_end_to_end(tmp_path, capsys):
    project = tmp_path / "graph"
    assert main(["init", str(project)]) == 0
    meta = parse_document(
        (project / "bdg_graph" / "nodes" / "1-1.md").read_text(encoding="utf-8")
    ).meta
    assert meta == {"id": 1, "title": "Root"}

    assert main(["graph", "--root", str(project)]) == 0
    assert "## 0 — 1-1" in capsys.readouterr().out
    assert main(["check", "--root", str(project)]) == 0
    assert "0 errors, 0 warnings" in capsys.readouterr().out
    result = check(project)
    assert result.ok
    assert result.nodes_scanned == 1

    assert main(
        ["new", "--parent", "1-1", "--field", "title=X", "--root", str(project)]
    ) == 0
    doc = parse_document(
        (project / "bdg_graph" / "nodes" / "1-1.md").read_text(encoding="utf-8")
    )
    assert "links" not in doc.meta
    assert "[[2-1,breaks_down]]" in doc.body
    assert check(project).ok
