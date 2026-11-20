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
    assert "folder" not in doc.meta
    assert doc.body == "hello\n"
    assert load(tmp_path).effective_contains("1") == ["2"]


def test_new_prefills_title_and_summary_cli(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=[])
    assert main(["new", "--parent", "1", "--root", str(tmp_path)]) == 0

    from bd_tree.frontmatter import parse_document

    doc = parse_document((nodes / "2.md").read_text(encoding="utf-8"))
    assert doc.meta["title"] == ""
    assert doc.meta["summary"] == ""


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


def test_current_views_and_edit_cli(write, tmp_path, capsys):
    write(tmp_path / "nodes", 1, contains=["2"], layer="intent")
    write(tmp_path / "nodes", 2, layer="claims")
    assert main(["work", "1", "--root", str(tmp_path)]) == 0
    capsys.readouterr()

    assert main(["current", "--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert out == f"{(tmp_path / 'bd_work').resolve()} (view 1)\n"

    assert main(["current", "--root", str(tmp_path), "--view"]) == 0
    assert capsys.readouterr().out == "1\n"

    assert main(["current", "--root", str(tmp_path), "--path"]) == 0
    assert capsys.readouterr().out == f"{(tmp_path / 'bd_work').resolve()}\n"

    assert main(["views", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out.startswith("1  Title of 1 *")

    assert main(["edit", "2", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out == f"{(tmp_path / 'bd_work' / 'claims' / '2.md')}\n"


def test_work_print_without_area_is_an_error(write, tmp_path, capsys):
    write(tmp_path / "nodes", 1)
    assert main(["work", "--print", "--root", str(tmp_path)]) == 2
    assert "no work area" in capsys.readouterr().err


def test_export_tree_is_gone(write, tmp_path):
    import pytest

    write(tmp_path / "nodes", 1)
    with pytest.raises(SystemExit):
        main(
            [
                "export",
                "tree",
                "--view",
                "1",
                "--out",
                str(tmp_path / "out"),
                "--root",
                str(tmp_path),
            ]
        )


def test_work_depth_suffix_reports_and_current_shows_it(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], layer="intent")
    write(nodes, 2, contains=["3"], layer="claims")
    write(nodes, 3, layer="evidence")

    assert main(["work", "1+1", "--root", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert "2 nodes, 2 symlinks" in output
    assert "(view 1+1)" in output

    assert main(["current", "--root", str(tmp_path), "--view"]) == 0
    assert capsys.readouterr().out == "1+1\n"

    assert main(["current", "--root", str(tmp_path)]) == 0
    assert "(view 1+1)" in capsys.readouterr().out

    assert main(["work", "--status", "--root", str(tmp_path)]) == 0
    assert "(view 1+1)" in capsys.readouterr().out


def test_work_depth_option_overrides_a_suffix(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], layer="intent")
    write(nodes, 2, contains=["3"], layer="claims")
    write(nodes, 3, layer="evidence")
    out = tmp_path / "bd_work"

    assert main(["work", "1+0", "--depth", "1", "--root", str(tmp_path)]) == 0
    assert "(view 1+1)" in capsys.readouterr().out
    assert (out / "claims" / "2.md").is_symlink()
    assert not (out / "evidence" / "3.md").exists()

    assert main(["work", "1", "--depth", "0", "--root", str(tmp_path)]) == 0
    assert "(view 1+0)" in capsys.readouterr().out
    assert not (out / "claims" / "2.md").exists()

    assert main(["work", "1+0", "--root", str(tmp_path)]) == 0
    assert "1 nodes, 1 symlinks" in capsys.readouterr().out
    assert not (out / "claims" / "2.md").exists()


def test_work_malformed_depth_suffix_exits_2(write, tmp_path, capsys):
    write(tmp_path / "nodes", 1)

    for ref in ("1+x", "1+-1"):
        assert main(["work", ref, "--root", str(tmp_path)]) == 2
        err = capsys.readouterr().err
        assert "invalid depth" in err
        assert "Traceback" not in err
    assert not (tmp_path / "bd_work").exists()


def test_edit_respects_materialized_depth(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], layer="intent")
    write(nodes, 2, contains=["3"], layer="claims")
    write(nodes, 3, layer="evidence")

    assert main(["work", "1+1", "--root", str(tmp_path)]) == 0
    capsys.readouterr()

    assert main(["edit", "2", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out.endswith("claims/2.md\n")

    assert main(["edit", "3", "--root", str(tmp_path)]) == 2
    assert "current view 1+1" in capsys.readouterr().err
