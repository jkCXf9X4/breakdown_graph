from __future__ import annotations

import shutil

import pytest

from bd_tree.cli import main


def test_check_exit_status(write, tmp_path):
    write(tmp_path / "nodes", 1, band="root")
    assert main(["check", "--root", str(tmp_path)]) == 0
    write(tmp_path / "nodes", 2, band="claims", links=[{"to": "9", "type": "serves"}])
    assert main(["check", "--root", str(tmp_path)]) == 1


def test_pack_default_writes_all_nodes_and_index(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="root", links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2, band="claims")
    out = tmp_path / "out"
    assert (
        main(
            [
                "pack",
                "1",
                "--root",
                str(tmp_path),
                "--out",
                str(out),
                "--clean",
            ]
        )
        == 0
    )
    assert (out / "INDEX.md").is_file()
    assert (out / "1-1.md").is_file()
    assert (out / "2-1.md").is_file()
    assert not (out / "AGENTS.md").exists()
    assert not (out / "STALE.md").exists()


def test_pack_fresh_writes_agents_and_stale_without_stale_bodies(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="root")
    write(
        nodes,
        2,
        band="claims",
        body="stale secret body\n",
        links=[{"to": "1-1", "type": "supports", "propagates": True}],
    )
    out = tmp_path / "out"
    assert (
        main(
            [
                "pack",
                "1-1",
                "--fresh",
                "--root",
                str(tmp_path),
                "--out",
                str(out),
                "--clean",
            ]
        )
        == 0
    )
    assert (out / "1-1.md").is_file()
    assert (out / "AGENTS.md").is_file()
    assert (out / "STALE.md").is_file()
    assert not (out / "2-1.md").exists()
    assert not (out / "INDEX.md").exists()
    assert "stale secret body" not in (out / "STALE.md").read_text(encoding="utf-8")


def test_graph_format_dot(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2)

    assert main(["graph", "1", "--format", "dot", "--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "digraph bd_graph" in out
    assert '"1-1" -> "2-1"' in out


@pytest.mark.skipif(shutil.which("dot") is None, reason="graphviz not installed")
def test_graph_format_svg(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2)

    assert main(["graph", "1", "--format", "svg", "--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "<svg" in out


def test_versions_and_delete_cli(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, version=1, band="root")
    write(nodes, 1, version=2, band="root")
    assert main(["versions", "1", "--root", str(tmp_path)]) == 0
    assert main(["versions", "1-1", "--root", str(tmp_path)]) == 0
    assert main(["delete", "1-2", "--root", str(tmp_path)]) == 0
    assert not (nodes / "1-2.md").exists()


def test_clone_and_delete_refusals_cli(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="root", links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2, band="claims")
    assert main(["clone", "2-1", "--root", str(tmp_path)]) == 0
    assert (nodes / "2-2.md").is_file()

    assert main(["delete", "2-1", "--root", str(tmp_path)]) == 2
    assert (nodes / "2-1.md").is_file()

    assert main(["delete", "2-2", "--root", str(tmp_path)]) == 0
    assert not (nodes / "2-2.md").exists()


def test_clone_cli_prints_source_and_clone(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="root", links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2, band="claims")

    assert main(["clone", "1-1", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out == "1-1 -> 1-2\n"


def test_clone_subtree_cli_prints_every_pair(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="root", links=[{"to": "2-1", "type": "breaks_down"}])
    write(
        nodes,
        2,
        band="claims",
        links=[
            {"to": "3-1", "type": "breaks_down"},
            {"to": "4-1", "type": "breaks_down"},
        ],
    )
    write(nodes, 3, band="evidence")
    write(nodes, 4, band="decisions")

    assert main(["clone", "2-1", "--subtree", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out == (
        "2-1 -> 2-2\n1-1 -> 1-2\n3-1 -> 3-2\n4-1 -> 4-2\n"
    )


def test_clone_depth_cli(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2, links=[{"to": "3-1", "type": "breaks_down"}])
    write(nodes, 3)

    assert main(["clone", "2-1", "--depth", "1", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out == "2-1 -> 2-2\n1-1 -> 1-2\n3-1 -> 3-2\n"


def test_replace_cli_swaps_and_prints_canonical_message(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        band="root",
        links=[
            {"to": "2", "type": "breaks_down"},
            {"to": "3", "type": "breaks_down"},
        ],
    )
    write(nodes, 2, band="claims")
    write(nodes, 3, band="evidence")

    assert main(["clone", "3-1", "--root", str(tmp_path)]) == 0
    capsys.readouterr()
    assert main(["replace", "3-1", "3-2", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out == "replaced 3-1 with 3-2 in links\n"

    from bd_tree.api import load

    assert load(tmp_path).children("1-1") == ["2-1", "3-2"]


def test_replace_outside_view_cli_exits_2(write, tmp_path):
    write(tmp_path / "nodes", 1, band="root")
    write(tmp_path / "nodes", 9, band="lone")

    assert main(["clone", "9-1", "--root", str(tmp_path)]) == 0
    assert main(["replace", "9-1", "9-2", "--root", str(tmp_path)]) == 2


def test_clone_rejects_replace_flag_cli_exits_2(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="root", links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2, band="claims")

    with pytest.raises(SystemExit) as exc:
        main(["clone", "1-1", "--replace", "--root", str(tmp_path)])
    assert exc.value.code == 2


def test_new_with_arbitrary_field_cli(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1)
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
    assert "band" not in doc.meta
    assert "folder" not in doc.meta
    assert doc.body == "hello\n"
    assert load(tmp_path).children("1-1") == ["2-1"]


def test_new_prefills_title_and_summary_cli(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1)
    assert main(["new", "--parent", "1", "--root", str(tmp_path)]) == 0

    from bd_tree.frontmatter import parse_document

    doc = parse_document((nodes / "2-1.md").read_text(encoding="utf-8"))
    assert doc.meta["title"] == ""
    assert doc.meta["summary"] == ""


def test_new_rejects_retired_placement_flags_cli(write, tmp_path):
    write(tmp_path / "nodes", 1)
    for flag, value in (
        ("--band", "claims"),
        ("--subpath", "nested"),
        ("--order", "1"),
        ("--stage", "2"),
    ):
        with pytest.raises(SystemExit) as exc:
            main(["new", "--parent", "1", flag, value, "--root", str(tmp_path)])
        assert exc.value.code == 2


def test_check_require_flag_and_view_path_template(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="root", phase="intent", links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2, band="claims", phase="build")
    assert main(["check", "--root", str(tmp_path), "--require", "phase"]) == 0
    assert main(["check", "--root", str(tmp_path), "--require", "audience"]) == 1
    out = tmp_path / "out"
    assert (
        main(
            [
                "pack",
                "1-1",
                "--fresh",
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
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="intent", links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2, band="claims")
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
    out = capsys.readouterr().out
    assert out.startswith("1-1")
    assert "2 nodes" in out
    assert "Title of 1-1" in out
    assert "*" in out
    assert "anchor 1-1" in out

    assert main(["edit", "2-1", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out == f"{(tmp_path / 'bd_work' / '2-1.md')}\n"


def test_current_path_without_area_is_an_error(write, tmp_path, capsys):
    write(tmp_path / "nodes", 1, band="root")
    assert main(["current", "--path", "--root", str(tmp_path)]) == 2
    assert "no work area" in capsys.readouterr().err


def test_check_view_narrows_reporting(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2, body="line\n" * 121)
    write(nodes, 3)

    assert main(["check", "--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "WARNING nodes/2-1.md" in out
    assert "2 nodes, 0 errors, 2 warnings (view 1-1)" in out

    assert main(["check", "--view", "3-1", "--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "WARNING nodes/2-1.md" not in out
    assert "1 nodes, 0 errors, 2 warnings (view 3-1)" in out
    # Nodes outside the selected component are reported as orphans.
    assert "not in the default component" in out


def test_retitle_dry_run_cli(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, body="(Old)[[2-1, breaks_down]]\n")
    write(nodes, 2, title="Two")
    node = nodes / "1-1.md"
    before = node.read_text(encoding="utf-8")

    assert main(["retitle", "--dry-run", "--root", str(tmp_path)]) == 0
    assert "would retitle 1 tokens in 1 nodes" in capsys.readouterr().out
    assert node.read_text(encoding="utf-8") == before

    assert main(["retitle", "--root", str(tmp_path)]) == 0
    assert "retitled 1 tokens in 1 nodes" in capsys.readouterr().out
    assert "(Two)[[2-1, breaks_down]]" in node.read_text(encoding="utf-8")


def test_removed_subcommands_and_flags_exit_2(write, tmp_path):
    write(tmp_path / "nodes", 1, band="root")
    root = ["--root", str(tmp_path)]
    removed = [
        ["tree", "1-1", *root],
        ["contain", "1-1", "2-1", *root],
        ["uncontain", "1-1", "2-1", *root],
        ["export", "tree", "1", "--out", str(tmp_path / "out"), *root],
        ["audit", *root],
        ["reconcile", "1-1", *root],
        ["export", "graph", "--view", "1", "--out", str(tmp_path / "out"), *root],
        ["version", "1-1", *root],
        ["grep", "needle", *root],
        ["view", "1", "--out", str(tmp_path / "out"), *root],
        ["ls", *root],
        ["work", "1", "--print", *root],
        ["work", "1-1", "--status", *root],
        ["work", "1-1", "--writeback", *root],
        ["graph", "--dot", *root],
        ["graph", "--svg", *root],
        ["graph", "--distance", "1:2", *root],
        ["retitle", "--view", "1", *root],
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
    write(nodes, 1, band="root", links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2, band="claims")

    assert main(["show", "2", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out.startswith("# 2-1  Title of 2-1")

    assert main(["path", "2", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out == (
        "1-1  Title of 1-1\n→ 2-1  Title of 2-1\n"
    )


def test_bare_selector_outside_the_view_fails(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="root")
    write(nodes, 9, band="lone")

    assert main(["show", "9", "--root", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "id 9" in err
    assert "view 1-1" in err


def test_work_depth_suffix_reports_and_current_shows_it(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="intent", links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2, band="claims", links=[{"to": "3-1", "type": "breaks_down"}])
    write(nodes, 3, band="evidence")

    assert main(["work", "1-1+1", "--root", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert "2 nodes, 2 symlinks" in output
    assert "(view 1-1+1)" in output

    assert main(["current", "--root", str(tmp_path), "--view"]) == 0
    assert capsys.readouterr().out == "1-1+1\n"

    assert main(["current", "--root", str(tmp_path)]) == 0
    assert "(view 1-1+1)" in capsys.readouterr().out

    assert main(["current", "--status", "--root", str(tmp_path)]) == 0
    assert "(view 1-1+1)" in capsys.readouterr().out


def test_work_depth_option_overrides_a_suffix(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="intent", links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2, band="claims", links=[{"to": "3-1", "type": "breaks_down"}])
    write(nodes, 3, band="evidence")
    out = tmp_path / "bd_work"

    assert main(["work", "1-1+0", "--depth", "1", "--root", str(tmp_path)]) == 0
    assert "(view 1-1+1)" in capsys.readouterr().out
    assert (out / "2-1.md").is_symlink()
    assert not (out / "3-1.md").exists()

    assert main(["work", "1-1", "--depth", "0", "--root", str(tmp_path)]) == 0
    assert "(view 1-1+0)" in capsys.readouterr().out
    assert not (out / "2-1.md").exists()

    assert main(["work", "1-1+0", "--root", str(tmp_path)]) == 0
    assert "1 nodes, 1 symlinks" in capsys.readouterr().out
    assert not (out / "2-1.md").exists()


def test_work_malformed_depth_suffix_exits_2(write, tmp_path, capsys):
    write(tmp_path / "nodes", 1, band="root")

    for ref in ("1-1+x", "1-1+-1"):
        assert main(["work", ref, "--root", str(tmp_path)]) == 2
        err = capsys.readouterr().err
        assert "invalid depth" in err
        assert "Traceback" not in err
    assert not (tmp_path / "bd_work").exists()


def test_edit_respects_materialized_depth(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(nodes, 1, band="intent", links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2, band="claims", links=[{"to": "3-1", "type": "breaks_down"}])
    write(nodes, 3, band="evidence")

    assert main(["work", "1-1+1", "--root", str(tmp_path)]) == 0
    capsys.readouterr()

    assert main(["edit", "2-1", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out.endswith("2-1.md\n")

    assert main(["edit", "3-1", "--root", str(tmp_path)]) == 2
    assert "current view 1-1+1" in capsys.readouterr().err


def test_edit_prints_a_flat_basename(write, tmp_path, capsys):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        title="Root",
        links=[{"to": "2-1", "type": "breaks_down"}],
    )
    write(nodes, 2, name="idea")

    assert main(["work", "1-1", "--root", str(tmp_path)]) == 0
    capsys.readouterr()

    assert main(["edit", "2-1", "--root", str(tmp_path)]) == 0
    expected = tmp_path / "bd_work" / "2-1.md"
    assert capsys.readouterr().out == f"{expected}\n"


def test_help_texts_are_topology_neutral(capsys):
    commands = [
        ["views", "--help"],
        ["graph", "--help"],
        ["diff", "--help"],
        ["clone", "--help"],
        ["replace", "--help"],
        ["new", "--help"],
        ["pack", "--help"],
        ["stale", "--help"],
        ["current", "--help"],
        ["out", "--help"],
        ["in", "--help"],
        ["check", "--help"],
    ]
    for argv in commands:
        with pytest.raises(SystemExit) as excinfo:
            main(argv)
        assert excinfo.value.code == 0
        out = capsys.readouterr().out
        assert "prototype" not in out
        assert "containment" not in out


    with pytest.raises(SystemExit) as excinfo:
        main(["new", "--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "--band" not in out
    assert "--stage" not in out
    assert "--order" not in out
    assert "--subpath" not in out

    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "undirected distance rings" in out
    assert "component representatives" in out
    assert "containment views" not in out
