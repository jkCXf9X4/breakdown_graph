from __future__ import annotations

import pytest

from bd_tree.cli import main


def test_check_exit_status(write, tmp_path):
    write(tmp_path / "nodes", 1)
    assert main(["check", "--root", str(tmp_path)]) == 0
    write(tmp_path / "nodes", 2, contains=["3"])
    assert main(["check", "--root", str(tmp_path)]) == 1


def test_export_tree_writes_view_output_shape(write, tmp_path):
    write(tmp_path / "nodes", 1, title="Root", layer="intent", section="intent")
    out = tmp_path / "out"
    assert (
        main(["export", "tree", "1", "--root", str(tmp_path), "--out", str(out), "--clean"])
        == 0
    )
    assert (out / "INDEX.md").is_file()
    assert (out / "intent" / "1-1.md").is_file()


def test_versions_and_delete_cli(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, version=1)
    write(nodes, 1, version=2)
    assert main(["versions", "1", "--root", str(tmp_path)]) == 0
    assert main(["versions", "1-1", "--root", str(tmp_path)]) == 0
    assert main(["delete", "1-2", "--root", str(tmp_path)]) == 0
    assert not (nodes / "1-2.md").exists()


def test_clone_and_delete_refusals_cli(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2-1"])
    write(nodes, 2)
    assert main(["clone", "2-1", "--root", str(tmp_path)]) == 0
    assert (nodes / "2-2.md").is_file()

    assert main(["delete", "2-1", "--root", str(tmp_path)]) == 2
    assert (nodes / "2-1.md").is_file()

    assert main(["delete", "2-2", "--root", str(tmp_path)]) == 0
    assert not (nodes / "2-2.md").exists()


def test_clone_cli_prints_source_and_clone(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2-1"])
    write(nodes, 2)

    assert main(["clone", "1-1", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out == "1-1 -> 1-2\n"


def test_clone_subtree_cli_prints_every_pair(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2-1"])
    write(nodes, 2, contains=["3-1", "4-1"])
    write(nodes, 3)
    write(nodes, 4)

    assert main(["clone", "2-1", "--subtree", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out == (
        "2-1 -> 2-2\n3-1 -> 3-2\n4-1 -> 4-2\n"
    )


def test_replace_cli_swaps_and_prints_canonical_message(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"])
    write(nodes, 2)
    write(nodes, 3)

    assert main(["clone", "3-1", "--root", str(tmp_path)]) == 0
    capsys.readouterr()
    assert main(["replace", "3-1", "3-2", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out == "replaced 3-1 with 3-2 in 1-1\n"

    from bd_tree.api import load

    assert load(tmp_path).effective_contains("1-1") == ["2-1", "3-2"]


def test_replace_outside_view_cli_exits_2(write, tmp_path):
    write(tmp_path / "nodes", 1)
    write(tmp_path / "nodes", 9)

    assert main(["clone", "9-1", "--root", str(tmp_path)]) == 0
    assert main(["replace", "9-1", "9-2", "--root", str(tmp_path)]) == 2


def test_clone_rejects_replace_flag_cli_exits_2(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2-1"])
    write(nodes, 2)

    with pytest.raises(SystemExit) as exc:
        main(["clone", "1-1", "--replace", "--root", str(tmp_path)])
    assert exc.value.code == 2


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

    doc = parse_document((nodes / "2-1.md").read_text(encoding="utf-8"))
    assert doc.meta["phase"] == "build"
    assert "folder" not in doc.meta
    assert doc.body == "hello\n"
    assert load(tmp_path).effective_contains("1-1") == ["2-1"]


def test_new_prefills_title_and_summary_cli(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=[])
    assert main(["new", "--parent", "1", "--root", str(tmp_path)]) == 0

    from bd_tree.frontmatter import parse_document

    doc = parse_document((nodes / "2-1.md").read_text(encoding="utf-8"))
    assert doc.meta["title"] == ""
    assert doc.meta["summary"] == ""


def test_check_require_flag_and_view_path_template(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2-1"], phase="intent")
    write(nodes, 2, phase="build")
    assert main(["check", "--root", str(tmp_path), "--require", "phase"]) == 0
    assert main(["check", "--root", str(tmp_path), "--require", "audience"]) == 1
    out = tmp_path / "out"
    assert (
        main(
            [
                "export",
                "tree",
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
    assert (out / "intent" / "1-1.md").is_file()
    assert (out / "build" / "2-1.md").is_file()


def test_current_views_and_edit_cli(write, tmp_path, capsys):
    write(tmp_path / "nodes", 1, contains=["2-1"], layer="intent", name="intent/1-1")
    write(tmp_path / "nodes", 2, layer="claims", name="claims/2-1")
    assert main(["work", "1-1", "--root", str(tmp_path)]) == 0
    capsys.readouterr()

    assert main(["current", "--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert out == f"{(tmp_path / 'bd_work').resolve()} (view 1-1)\n"

    assert main(["current", "--root", str(tmp_path), "--view"]) == 0
    assert capsys.readouterr().out == "1-1\n"

    assert main(["current", "--root", str(tmp_path), "--path"]) == 0
    assert capsys.readouterr().out == f"{(tmp_path / 'bd_work').resolve()}\n"

    assert main(["views", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out.startswith("1-1  Title of 1-1 *")

    assert main(["edit", "2-1", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out == f"{(tmp_path / 'bd_work' / 'claims' / '2-1.md')}\n"


def test_current_path_without_area_is_an_error(write, tmp_path, capsys):
    write(tmp_path / "nodes", 1)
    assert main(["current", "--path", "--root", str(tmp_path)]) == 2
    assert "no work area" in capsys.readouterr().err


def test_export_tree_is_available(write, tmp_path):
    write(tmp_path / "nodes", 1)
    assert (
        main(
            [
                "export",
                "tree",
                "1",
                "--out",
                str(tmp_path / "out"),
                "--root",
                str(tmp_path),
            ]
        )
        == 0
    )
    assert (tmp_path / "out" / "INDEX.md").is_file()


def test_check_view_narrows_reporting(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2-1", "3-1"])
    write(nodes, 2, body="line\n" * 121)
    write(nodes, 3)

    assert main(["check", "--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "WARNING nodes/2-1.md" in out
    assert "1 warnings" in out

    assert main(["check", "--view", "3-1", "--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "WARNING nodes/2-1.md" not in out
    assert "0 warnings" in out


def test_removed_subcommands_and_flags_exit_2(write, tmp_path):
    import pytest

    write(tmp_path / "nodes", 1)
    root = ["--root", str(tmp_path)]
    removed = [
        ["version", "1-1", *root],
        ["grep", "needle", *root],
        ["view", "1", "--out", str(tmp_path / "out"), *root],
        ["ls", *root],
        ["work", "1", "--print", *root],
        ["show", "1", "--path", *root],
        ["check", "--root-ref", "1", *root],
        ["fork", "1-1", *root],
        ["promote", "1-1", "2-1", *root],
        ["retire-version", "1-1", *root],
    ]
    for argv in removed:
        with pytest.raises(SystemExit) as exc:
            main(argv)
        assert exc.value.code == 2, argv


def test_bare_selector_resolves_inside_the_default_view(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2-1"])
    write(nodes, 2)

    assert main(["show", "2", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out.startswith("# 2-1  Title of 2-1")

    assert main(["path", "2", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out == (
        "1-1  Title of 1-1\n2-1  Title of 2-1\n"
    )


def test_bare_selector_outside_the_view_fails(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1)
    write(nodes, 9)

    assert main(["show", "9", "--root", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "id 9" in err
    assert "view 1-1" in err


def test_work_depth_suffix_reports_and_current_shows_it(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2-1"], layer="intent")
    write(nodes, 2, contains=["3-1"], layer="claims")
    write(nodes, 3, layer="evidence")

    assert main(["work", "1-1+1", "--root", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert "2 nodes, 2 symlinks" in output
    assert "(view 1-1+1)" in output

    assert main(["current", "--root", str(tmp_path), "--view"]) == 0
    assert capsys.readouterr().out == "1-1+1\n"

    assert main(["current", "--root", str(tmp_path)]) == 0
    assert "(view 1-1+1)" in capsys.readouterr().out

    assert main(["work", "--status", "--root", str(tmp_path)]) == 0
    assert "(view 1-1+1)" in capsys.readouterr().out


def test_work_depth_option_overrides_a_suffix(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2-1"], layer="intent", name="intent/1-1")
    write(nodes, 2, contains=["3-1"], layer="claims", name="claims/2-1")
    write(nodes, 3, layer="evidence", name="evidence/3-1")
    out = tmp_path / "bd_work"

    assert main(["work", "1-1+0", "--depth", "1", "--root", str(tmp_path)]) == 0
    assert "(view 1-1+1)" in capsys.readouterr().out
    assert (out / "claims" / "2-1.md").is_symlink()
    assert not (out / "evidence" / "3-1.md").exists()

    assert main(["work", "1-1", "--depth", "0", "--root", str(tmp_path)]) == 0
    assert "(view 1-1+0)" in capsys.readouterr().out
    assert not (out / "claims" / "2-1.md").exists()

    assert main(["work", "1-1+0", "--root", str(tmp_path)]) == 0
    assert "1 nodes, 1 symlinks" in capsys.readouterr().out
    assert not (out / "claims" / "2-1.md").exists()


def test_work_malformed_depth_suffix_exits_2(write, tmp_path, capsys):
    write(tmp_path / "nodes", 1)

    for ref in ("1-1+x", "1-1+-1"):
        assert main(["work", ref, "--root", str(tmp_path)]) == 2
        err = capsys.readouterr().err
        assert "invalid depth" in err
        assert "Traceback" not in err
    assert not (tmp_path / "bd_work").exists()


def test_edit_respects_materialized_depth(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2-1"], layer="intent", name="intent/1-1")
    write(nodes, 2, contains=["3-1"], layer="claims", name="claims/2-1")
    write(nodes, 3, layer="evidence", name="evidence/3-1")

    assert main(["work", "1-1+1", "--root", str(tmp_path)]) == 0
    capsys.readouterr()

    assert main(["edit", "2-1", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out.endswith("claims/2-1.md\n")

    assert main(["edit", "3-1", "--root", str(tmp_path)]) == 2
    assert "current view 1-1+1" in capsys.readouterr().err


def test_edit_prints_a_nested_section_path(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2-1"], section="06-evolution", title="Root")
    write(nodes, 2, section="claims", name="idea")

    assert main(["work", "1-1", "--root", str(tmp_path)]) == 0
    capsys.readouterr()

    assert main(["edit", "2-1", "--root", str(tmp_path)]) == 0
    expected = tmp_path / "bd_work" / "06-evolution" / "claims" / "idea.md"
    assert capsys.readouterr().out == f"{expected}\n"
