from __future__ import annotations

from bd_tree.cli import main


def test_check_exit_status(write, tmp_path):
    write(tmp_path / "nodes", 1)
    assert main(["check", "--root", str(tmp_path)]) == 0
    write(tmp_path / "nodes", 2)
    assert main(["check", "--root", str(tmp_path)]) == 1


def test_view_alias_exports_tree(write, tmp_path):
    write(tmp_path / "nodes", 1, title="Root", layer="intent")
    out = tmp_path / "out"
    assert main(["view", "1", "--root", str(tmp_path), "--out", str(out), "--clean"]) == 0
    assert (out / "INDEX.md").is_file()
    assert (out / "intent" / "1.md").is_file()


def test_versions_and_retire_version_cli(write, tmp_path):
    write(tmp_path / "nodes", 1)
    write(tmp_path / "nodes", 1, version=1)
    assert main(["versions", "1", "--root", str(tmp_path)]) == 0
    assert main(["retire-version", "1-1", "--root", str(tmp_path)]) == 0
    assert not (tmp_path / "nodes" / "1-1.md").exists()


def test_new_with_arbitrary_field_cli(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=[])
    assert (
        main(
            [
                "new",
                "--parent",
                "1",
                "--root",
                str(tmp_path),
                "--field",
                "phase=build",
                "--field",
                "audience=team",
                "--body",
                "hello\n",
            ]
        )
        == 0
    )
    from bd_tree.api import load
    from bd_tree.frontmatter import parse_document

    doc = parse_document((nodes / "2.md").read_text(encoding="utf-8"))
    assert doc.meta["phase"] == "build"
    assert doc.meta["home"] == "2.md"
    assert doc.body == "hello\n"
    assert load(tmp_path).effective_contains("1") == ["2"]


def test_check_require_flag_and_view_path_template(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], phase="intent")
    write(nodes, 2, phase="build")
    assert main(["check", "--root", str(tmp_path), "--require", "phase"]) == 0
    assert main(["check", "--root", str(tmp_path), "--require", "audience"]) == 1
    out = tmp_path / "out"
    assert (
        main(
            [
                "view",
                "1",
                "--root",
                str(tmp_path),
                "--out",
                str(out),
                "--path-template",
                "{phase}/{ref}.md",
                "--clean",
            ]
        )
        == 0
    )
    assert (out / "intent" / "1.md").is_file()
    assert (out / "build" / "2.md").is_file()
