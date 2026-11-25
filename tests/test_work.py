from __future__ import annotations

import os
import shutil

import pytest

from bd_tree import api


def _tree(write, tmp_path):
    """1 -> 2, 3; 2 -> 4.  The component is flat-ringed from 1-1."""
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[
            {"to": "2-1", "type": "breaks_down"},
            {"to": "3-1", "type": "breaks_down"},
        ],
    )
    write(nodes, 2, links=[{"to": "4-1", "type": "breaks_down"}])
    write(nodes, 3)
    write(nodes, 4)
    return nodes


def _cycle(write, tmp_path):
    """1 -> 2 -> 3 -> 1 plus 3 -> 4: a cycle must not duplicate a node."""
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2, links=[{"to": "3-1", "type": "supports"}])
    write(
        nodes,
        3,
        links=[
            {"to": "1-1", "type": "verifies"},
            {"to": "4-1", "type": "supports"},
        ],
    )
    write(nodes, 4)
    return nodes


def _entry(result, path):
    return next(entry for entry in result.entries if entry.path == path)


def test_work_links_every_node_and_writes_generated_files(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    result = api.work(tmp_path, "1-1", out)

    assert result.nodes == 4
    assert result.symlinks == 4
    store = api.load(tmp_path)
    status = api.work(tmp_path, "1-1", out, status=True)
    assert status.ok
    by_ref = {entry.ref: entry.path for entry in status.entries if entry.ref}
    assert set(by_ref) == set(store.nodes)
    for node in store.nodes.values():
        dest = out / by_ref[node.ref]
        assert dest.parent == out
        assert dest.is_symlink()
        assert dest.resolve() == node.path.resolve()
        assert not os.path.isabs(os.readlink(dest))
    for name in ("INDEX.md", "AGENTS.md", "REFS.md"):
        assert (out / name).is_file()
        assert not (out / name).is_symlink()
    agents = (out / "AGENTS.md").read_text(encoding="utf-8")
    assert "symlink" in agents and "--writeback" in agents
    refs = (out / "REFS.md").read_text(encoding="utf-8")
    assert "| Path | Ref | Kind | Distance | Title |" in refs
    assert "`2-1.md` | 2-1 | child | 1 |" in refs


def test_work_index_uses_ring_sections(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1-1", out)

    index = (out / "INDEX.md").read_text(encoding="utf-8")
    assert index.startswith("---\nnodes: ../nodes\n---\n")
    assert "# View 1-1" in index
    assert "[nodes/](../nodes/)" in index
    assert "## Active" in index
    assert "## Distance 1 — children" in index
    assert "## Distance 2" in index
    assert index.index("## Active") < index.index("## Distance 1 — children")
    assert index.index("## Distance 1 — children") < index.index("## Distance 2")
    assert "[Title of 1-1](1-1.md)" in index
    assert "[real file](../nodes/1-1.md)" in index
    assert "[Title of 4-1](4-1.md)" in index

    refs = (out / "REFS.md").read_text(encoding="utf-8")
    assert refs.startswith("<!-- GENERATED FILE")
    assert "# References — view 1-1" in refs
    assert "`1-1.md` | 1-1 | active | 0 |" in refs
    assert "`4-1.md` | 4-1 | - | 2 |" in refs


def test_work_cycle_appears_once_at_minimum_distance(write, tmp_path):
    _cycle(write, tmp_path)
    out = tmp_path / "work"
    result = api.work(tmp_path, "1-1", out)

    assert result.nodes == 4
    assert result.symlinks == 4
    refs = (out / "REFS.md").read_text(encoding="utf-8")
    assert refs.count("| 3-1 |") == 1
    # 3-1 is a neighbour of the anchor (3 -> 1), so it stays at distance 1.
    assert "| 3-1 | parent | 1 |" in refs
    assert "| 4-1 | - | 2 |" in refs
    index = (out / "INDEX.md").read_text(encoding="utf-8")
    assert index.count("[Title of 3-1]") == 1
    assert "## Distance 1 — parents" in index
    assert api.work(tmp_path, "1-1", out, status=True).ok


def test_work_cli_builds_the_same_tree(write, tmp_path, capsys):
    _tree(write, tmp_path)
    out = tmp_path / "bd_work"
    from bd_tree.cli import main

    assert main(["work", "1-1", "--root", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert "4 nodes, 4 symlinks" in output
    assert (out / "2-1.md").is_symlink()


def test_write_through_edits_the_store_file(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1-1", out)
    dest = out / "2-1.md"
    dest.write_text("edited through the link\n", encoding="utf-8")
    assert (tmp_path / "nodes" / "2-1.md").read_text(encoding="utf-8") == (
        "edited through the link\n"
    )


def test_status_is_clean_after_build(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1-1", out)
    status = api.work(tmp_path, "1-1", out, status=True)
    assert status.ok
    assert {entry.status for entry in status.entries} == {"ok"}


def test_status_inspects_the_areas_view_not_the_requested_ref(write, tmp_path):
    nodes = _tree(write, tmp_path)
    write(nodes, 1, version=2, links=[{"to": "2-2", "type": "breaks_down"}])
    write(nodes, 2, version=2)
    (tmp_path / "ROOT").write_text("1-1\n", encoding="utf-8")

    built = api.work(tmp_path, "1-1")
    assert built.ref == "1-1"

    status = api.work(tmp_path, status=True)
    assert status.ref == "1-1"
    assert status.ok

    status = api.work(tmp_path, "1-2", status=True)
    assert status.ref == "1-1"
    assert status.ok


@pytest.mark.parametrize("mode", ["status", "writeback"])
def test_status_and_writeback_require_a_built_area(write, tmp_path, mode):
    from bd_tree.errors import ExportError

    _tree(write, tmp_path)
    kwargs = {mode: True}

    with pytest.raises(ExportError, match="bd work"):
        api.work(tmp_path, "1-1", **kwargs)
    assert not (tmp_path / "bd_work").exists()


def test_area_and_edit_path_are_read_only(write, tmp_path):
    _tree(write, tmp_path)
    api.work(tmp_path, "1-1")
    out = (tmp_path / "bd_work").resolve()
    from bd_tree.work import area, edit_path

    watched = [
        out / "INDEX.md",
        out / "REFS.md",
        out / "AGENTS.md",
        out / "2-1.md",
    ]
    before = {
        path: (path.stat().st_mtime_ns, path.read_bytes()) for path in watched
    }

    current = area(tmp_path)
    assert current.out == out
    assert current.ref == "1-1"
    assert edit_path(tmp_path, "2") == out / "2-1.md"

    after = {
        path: (path.stat().st_mtime_ns, path.read_bytes()) for path in watched
    }
    assert after == before


def test_edit_path_returns_the_expected_path_without_building(write, tmp_path):
    _tree(write, tmp_path)
    api.work(tmp_path, "1-1")
    out = (tmp_path / "bd_work").resolve()
    dest = out / "2-1.md"
    dest.unlink()
    from bd_tree.work import edit_path

    assert edit_path(tmp_path, "2") == dest
    assert not dest.exists()


def test_edit_path_rejects_an_out_of_view_ref(write, tmp_path):
    from bd_tree.navigate import NavigationError
    from bd_tree.work import edit_path

    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2)
    write(nodes, 9)
    api.work(tmp_path, "1-1")

    with pytest.raises(NavigationError) as caught:
        edit_path(tmp_path, "9")
    message = str(caught.value)
    assert "id 9" in message
    assert "view 1-1" in message


def test_edit_path_requires_a_built_area(write, tmp_path):
    from bd_tree.errors import ExportError
    from bd_tree.work import edit_path

    _tree(write, tmp_path)
    with pytest.raises(ExportError, match="bd work"):
        edit_path(tmp_path, "1")


def test_status_reports_a_detached_file(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1-1", out)
    dest = out / "2-1.md"
    original = (tmp_path / "nodes" / "2-1.md").read_text(encoding="utf-8")
    dest.unlink()
    dest.write_text(original + "\nlocal note\n", encoding="utf-8")

    status = api.work(tmp_path, "1-1", out, status=True)
    assert not status.ok
    assert _entry(status, "2-1.md").status == "detached"
    assert _entry(status, "2-1.md").ref == "2-1"
    assert _entry(status, "1-1.md").status == "ok"


def test_writeback_restores_store_and_relinks(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1-1", out)
    dest = out / "2-1.md"
    edited = (tmp_path / "nodes" / "2-1.md").read_text(encoding="utf-8") + "\nlocal note\n"
    dest.unlink()
    dest.write_text(edited, encoding="utf-8")

    result = api.work(tmp_path, "1-1", out, writeback=True)
    assert result.written == 1
    assert (tmp_path / "nodes" / "2-1.md").read_text(encoding="utf-8") == edited
    assert dest.is_symlink()
    assert dest.resolve() == (tmp_path / "nodes" / "2-1.md").resolve()
    assert api.work(tmp_path, "1-1", out, status=True).ok


def test_stray_file_is_reported_and_left_alone(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1-1", out)
    stray = out / "stray.md"
    stray.write_text("not a view node\n", encoding="utf-8")

    status = api.work(tmp_path, "1-1", out, status=True)
    assert not status.ok
    assert _entry(status, "stray.md").status == "stray"

    result = api.work(tmp_path, "1-1", out, writeback=True)
    assert result.written == 0
    assert not result.ok
    assert stray.is_file() and not stray.is_symlink()
    assert not (tmp_path / "nodes" / "stray.md").exists()


def test_clean_rebuilds_without_touching_store_files(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1-1", out)
    store_before = {
        path.name: path.read_bytes() for path in (tmp_path / "nodes").glob("*.md")
    }

    result = api.work(
        tmp_path, "1-1", out, path_template="{ref}.md", clean=True
    )
    assert result.symlinks == 4
    assert (out / "1-1.md").is_symlink()
    store_after = {
        path.name: path.read_bytes() for path in (tmp_path / "nodes").glob("*.md")
    }
    assert store_before == store_after


def test_default_out_is_the_single_project_work_area(write, tmp_path):
    _tree(write, tmp_path)
    result = api.work(tmp_path, "1-1")
    expected = (tmp_path / "bd_work").resolve()
    assert result.out == expected
    assert expected.is_dir()
    assert (expected / "2-1.md").is_symlink()


def test_default_out_for_hidden_store_is_project_bd_work(write, tmp_path):
    store = tmp_path / ".bd_tree" / "nodes"
    write(store, 1, links=[{"to": "2-1", "type": "breaks_down"}])
    write(store, 2)
    result = api.work(tmp_path, "1-1")
    expected = (tmp_path / "bd_work").resolve()
    assert result.out == expected
    assert (expected / "1-1.md").is_symlink()
    assert (expected / "1-1.md").resolve() == (store / "1-1.md").resolve()


def test_ref_switch_replaces_the_same_work_area(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, version=1, links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2, version=1)
    write(nodes, 1, version=2, links=[{"to": "2-2", "type": "breaks_down"}])
    write(nodes, 2, version=2)

    first = api.work(tmp_path, "1-1")
    out = first.out
    assert out == (tmp_path / "bd_work").resolve()
    old_link = out / "1-1.md"
    assert old_link.is_symlink()
    assert old_link.resolve() == (nodes / "1-1.md").resolve()

    second = api.work(tmp_path, "1-2")

    assert second.out == out
    assert not (out / "1-1.md").is_symlink()
    assert not (out / "1-1.md").exists()
    assert not (out / "2-1.md").is_symlink()
    assert (out / "1-2.md").resolve() == (nodes / "1-2.md").resolve()
    assert (out / "2-2.md").resolve() == (nodes / "2-2.md").resolve()
    refs = (out / "REFS.md").read_text(encoding="utf-8")
    index = (out / "INDEX.md").read_text(encoding="utf-8")
    agents = (out / "AGENTS.md").read_text(encoding="utf-8")
    assert "view 1-2" in refs and "1-1" not in refs
    refs_body = refs.split("# References", 1)[1]
    assert "1-1" not in refs_body
    assert "# View 1-2" in index
    assert "view `1-2`" in agents
    assert api.work(tmp_path, "1-2", status=True).ok


def test_unexpected_store_symlink_is_cleaned_without_refs_manifest(write, tmp_path):
    _tree(write, tmp_path)
    write(tmp_path / "nodes", 5)
    out = tmp_path / "work"
    api.work(tmp_path, "1-1", out)
    (out / "REFS.md").unlink()
    stray = out / "extra.md"
    stray.symlink_to(os.path.relpath(tmp_path / "nodes" / "5-1.md", out))

    result = api.work(tmp_path, "1-1", out)

    assert result.symlinks == 4
    assert not stray.is_symlink()
    assert not stray.exists()
    assert (out / "REFS.md").is_file()
    assert api.work(tmp_path, "1-1", out, status=True).ok


def test_detached_file_blocks_a_ref_switch_until_clean(write, tmp_path):
    from bd_tree.errors import ExportError

    nodes = tmp_path / "nodes"
    write(nodes, 1, version=1, links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2, version=1)
    write(nodes, 1, version=2, links=[{"to": "2-2", "type": "breaks_down"}])
    write(nodes, 2, version=2)

    api.work(tmp_path, "1-1")
    out = tmp_path / "bd_work"
    dest = out / "1-1.md"
    dest.unlink()
    dest.write_text("detached\n", encoding="utf-8")

    with pytest.raises(ExportError) as caught:
        api.work(tmp_path, "1-2")
    message = str(caught.value)
    assert "--writeback" in message and "--clean" in message
    assert dest.read_text(encoding="utf-8") == "detached\n"

    api.work(tmp_path, "1-2", clean=True)
    assert not (out / "1-1.md").exists()
    assert (out / "1-2.md").is_symlink()


def test_path_template_uses_distance_and_ref(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "templated"
    api.work(
        tmp_path, "1-1", out, path_template="{distance}-{ref}.md"
    )
    assert (out / "0-1-1.md").is_symlink()
    assert (out / "1-2-1.md").is_symlink()
    assert (out / "1-3-1.md").is_symlink()
    assert (out / "2-4-1.md").is_symlink()
    assert "`1-2-1.md`" in (out / "REFS.md").read_text(encoding="utf-8")


def test_front_matter_name_does_not_change_the_link(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, links=[{"to": "2-1", "type": "breaks_down"}], name="a")
    write(nodes, 2, name="b")
    out = tmp_path / "work"
    api.work(tmp_path, "1-1", out)

    assert (out / "1-1.md").is_symlink()
    assert (out / "2-1.md").is_symlink()
    assert not (out / "a.md").exists()
    assert not (out / "b.md").exists()


def test_status_and_writeback_use_refs_manifest_when_ref_changes(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1-1", out)
    dest = out / "2-1.md"
    dest.unlink()
    dest.write_text(
        "---\n"
        "id: 2\n"
        "name: renamed\n"
        "title: Moved\n"
        "summary: s\n"
        "---\n"
        "new body\n"
        "\n## Links\n- [[breaks_down, 4-1]]\n",
        encoding="utf-8",
    )

    status = api.work(tmp_path, "1-1", out, status=True)
    entry = _entry(status, "2-1.md")
    assert entry.ref == "2-1"
    assert entry.status == "detached"
    assert not status.ok

    result = api.work(tmp_path, "1-1", out, writeback=True)
    assert result.written == 1
    assert (tmp_path / "nodes" / "2-1.md").read_text(encoding="utf-8").endswith(
        "- [[breaks_down, 4-1]]\n"
    )
    assert dest.is_symlink()
    assert api.work(tmp_path, "1-1", out, status=True).ok


def _link_count(out):
    return sum(1 for path in out.rglob("*.md") if path.is_symlink())


def test_two_work_dirs_share_the_same_nodes(write, tmp_path):
    _tree(write, tmp_path)
    a = tmp_path / "a"
    b = tmp_path / "b"
    api.work(tmp_path, "1-1", a)
    api.work(tmp_path, "2-1", b)

    through_b = b / "2-1.md"
    through_a = a / "2-1.md"
    assert through_b.is_symlink() and through_a.is_symlink()
    through_b.write_text("edited through b\n", encoding="utf-8")

    assert through_a.read_text(encoding="utf-8") == "edited through b\n"
    assert (tmp_path / "nodes" / "2-1.md").read_text(encoding="utf-8") == (
        "edited through b\n"
    )


def test_plain_refresh_is_idempotent(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1-1", out)
    before = _link_count(out)

    result = api.work(tmp_path, "1-1", out)

    assert result.symlinks == 4
    assert _link_count(out) == before
    assert api.work(tmp_path, "1-1", out, status=True).ok


def test_refresh_repairs_missing_and_wrong_target_links(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1-1", out)

    (out / "2-1.md").unlink()
    wrong = out / "4-1.md"
    wrong.unlink()
    wrong.symlink_to(os.path.relpath(tmp_path / "nodes" / "3-1.md", out))

    result = api.work(tmp_path, "1-1", out)

    assert result.symlinks == 4
    assert (out / "2-1.md").is_symlink()
    assert (out / "4-1.md").resolve() == (tmp_path / "nodes" / "4-1.md").resolve()
    assert api.work(tmp_path, "1-1", out, status=True).ok


def test_refresh_removes_stale_ref_links(write, tmp_path):
    _tree(write, tmp_path)
    write(tmp_path / "nodes", 5)
    out = tmp_path / "work"
    api.work(tmp_path, "1-1", out)

    result = api.work(tmp_path, "5-1", out)

    assert result.ref == "5-1"
    assert not (out / "1-1.md").exists()
    assert not (out / "3-1.md").exists()
    assert (out / "5-1.md").is_symlink()
    assert api.work(tmp_path, "5-1", out, status=True).ok


def test_detached_file_blocks_refresh_until_writeback(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "bd_work"
    api.work(tmp_path, "1-1")
    dest = out / "2-1.md"
    original = dest.read_text(encoding="utf-8")
    dest.unlink()
    dest.write_text(original + "detached edit\n", encoding="utf-8")
    from bd_tree.cli import main

    assert main(["work", "1-1", "--root", str(tmp_path)]) == 2
    assert not dest.is_symlink()
    assert dest.read_text(encoding="utf-8") == original + "detached edit\n"

    assert (
        main(
            [
                "work",
                "1-1",
                "--root",
                str(tmp_path),
                "--writeback",
            ]
        )
        == 0
    )
    assert dest.is_symlink()
    assert (tmp_path / "nodes" / "2-1.md").read_text(encoding="utf-8") == (
        original + "detached edit\n"
    )
    assert main(["work", "1-1", "--root", str(tmp_path)]) == 0


def test_stray_blocks_refresh_and_clean_discards(write, tmp_path):
    from bd_tree.errors import ExportError

    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1-1", out)
    stray = out / "stray.md"
    stray.write_text("not a view node\n", encoding="utf-8")

    with pytest.raises(ExportError):
        api.work(tmp_path, "1-1", out)
    assert stray.is_file()
    assert api.work(tmp_path, "1-1", out, status=True).ok is False

    api.work(tmp_path, "1-1", out, clean=True)
    assert not stray.exists()
    assert api.work(tmp_path, "1-1", out, status=True).ok


def test_current_path_is_read_only(write, tmp_path, capsys):
    _tree(write, tmp_path)
    api.work(tmp_path, "1-1")
    out = (tmp_path / "bd_work").resolve()
    from bd_tree.cli import main

    def snapshot():
        return {
            path: (path.stat().st_mtime_ns, path.read_bytes())
            for path in sorted(out.rglob("*"))
            if path.is_file() or path.is_symlink()
        }

    before = snapshot()
    argv = ["current", "--path", "--root", str(tmp_path)]
    assert main(argv) == 0
    captured = capsys.readouterr()
    assert captured.out == f"{out}\n"
    assert captured.err == ""
    assert snapshot() == before

    assert main(argv) == 0
    assert capsys.readouterr().out == f"{out}\n"
    assert snapshot() == before


def test_current_path_and_view_are_mutually_exclusive(write, tmp_path):
    _tree(write, tmp_path)
    from bd_tree.cli import main

    with pytest.raises(SystemExit) as exc:
        main(["current", "--path", "--view", "--root", str(tmp_path)])
    assert exc.value.code == 2


def test_force_overwrites_a_detached_file(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1-1", out)
    store_before = (tmp_path / "nodes" / "2-1.md").read_text(encoding="utf-8")
    dest = out / "2-1.md"
    dest.unlink()
    dest.write_text("detached edit\n", encoding="utf-8")

    result = api.work(tmp_path, "1-1", out, force=True)

    assert result.symlinks == 4
    assert dest.is_symlink()
    assert dest.read_text(encoding="utf-8") == store_before
    assert api.work(tmp_path, "1-1", out, status=True).ok


def test_writeback_refuses_a_detached_file_without_frontmatter(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1-1", out)
    dest = out / "2-1.md"
    dest.unlink()
    dest.write_text("body only\n", encoding="utf-8")
    before = (tmp_path / "nodes" / "2-1.md").read_text(encoding="utf-8")

    result = api.work(tmp_path, "1-1", out, writeback=True)

    assert result.written == 0
    assert result.invalid == ["2-1.md"]
    assert (tmp_path / "nodes" / "2-1.md").read_text(encoding="utf-8") == before
    assert not dest.is_symlink()


def _run_git(cwd, *args):
    import subprocess

    completed = subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def _git_repo(write, tmp_path):
    repo = tmp_path / "repo"
    write(repo / "nodes", 1, links=[{"to": "2-1", "type": "breaks_down"}])
    write(repo / "nodes", 2)
    _run_git(repo, "init", "-q")
    _run_git(repo, "config", "user.name", "Test User")
    _run_git(repo, "config", "user.email", "test@example.com")
    _run_git(repo, "add", "nodes")
    _run_git(repo, "commit", "-q", "-m", "nodes")
    return repo


git_only = pytest.mark.skipif(
    shutil.which("git") is None, reason="git not installed"
)


def test_work_without_git_omits_git_context(write, tmp_path, capsys):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    result = api.work(tmp_path, "1-1", out)
    assert result.git is None
    agents = (out / "AGENTS.md").read_text(encoding="utf-8")
    assert "Git branch:" not in agents

    from bd_tree.cli import main

    assert main(["work", "1-1", "--root", str(tmp_path)]) == 0
    assert "branch " not in capsys.readouterr().out


@git_only
def test_work_records_git_branch_commit_and_toplevel(write, tmp_path):
    repo = _git_repo(write, tmp_path)
    branch = _run_git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    commit = _run_git(repo, "rev-parse", "--short", "HEAD")
    toplevel = _run_git(repo, "rev-parse", "--show-toplevel")
    out = tmp_path / "work"

    result = api.work(repo, "1-1", out)

    assert result.git is not None
    assert (result.git.branch, result.git.commit, result.git.toplevel) == (
        branch,
        commit,
        toplevel,
    )
    agents = (out / "AGENTS.md").read_text(encoding="utf-8")
    assert f"- Git branch: `{branch}`" in agents
    assert f"- Git commit: `{commit}`" in agents
    assert f"- Worktree: `{toplevel}`" in agents


@git_only
def test_work_cli_prints_the_branch(write, tmp_path, capsys):
    repo = _git_repo(write, tmp_path)
    branch = _run_git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    from bd_tree.cli import main

    assert main(["work", "1-1", "--root", str(repo)]) == 0
    assert f"branch {branch}" in capsys.readouterr().out


@git_only
def test_write_through_is_visible_to_git_status(write, tmp_path):
    repo = _git_repo(write, tmp_path)
    out = tmp_path / "work"
    api.work(repo, "1-1", out)

    (out / "2-1.md").write_text("edited through the link\n", encoding="utf-8")

    porcelain = _run_git(repo, "status", "--porcelain")
    assert "nodes/2-1.md" in porcelain
    assert "work/" not in porcelain


def test_depth_limited_work_materializes_only_the_rings(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    result = api.work(tmp_path, "1-1", out, depth=1)

    assert result.depth == 1 and result.view_ref == "1-1+1"
    assert result.nodes == 3 and result.symlinks == 3
    assert (out / "1-1.md").is_symlink()
    assert (out / "2-1.md").is_symlink()
    assert (out / "3-1.md").is_symlink()
    assert not (out / "4-1.md").exists()
    for name in ("REFS.md", "INDEX.md", "AGENTS.md"):
        text = (out / name).read_text(encoding="utf-8")
        assert "1-1+1" in text
        assert "4-1.md" not in text
        assert "Title of 4-1" not in text

    agents = (out / "AGENTS.md").read_text(encoding="utf-8")
    assert "first 1 descendant levels" in agents
    assert "run `bd work 1-1` for the full closure" in agents


def test_depth_limited_work_edit_path_hides_excluded_refs(write, tmp_path):
    from bd_tree.errors import ExportError
    from bd_tree.work import area, edit_path

    _tree(write, tmp_path)
    out = (tmp_path / "bd_work").resolve()
    api.work(tmp_path, "1-1", depth=1)

    current = area(tmp_path)
    assert current.ref == "1-1" and current.depth == 1
    assert current.view_ref == "1-1+1"
    assert edit_path(tmp_path, "2") == out / "2-1.md"
    with pytest.raises(ExportError, match=r"current view 1-1\+1"):
        edit_path(tmp_path, "4")


def test_full_work_restores_the_component_and_drops_the_suffix(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1-1", out, depth=1)

    result = api.work(tmp_path, "1-1", out)

    assert result.depth is None and result.view_ref == "1-1"
    assert result.nodes == 4
    assert (out / "4-1.md").is_symlink()
    refs = (out / "REFS.md").read_text(encoding="utf-8")
    index = (out / "INDEX.md").read_text(encoding="utf-8")
    agents = (out / "AGENTS.md").read_text(encoding="utf-8")
    assert "view 1-1\n" in refs and "1-1+1" not in refs
    assert "# View 1-1\n" in index and "1-1+1" not in index
    assert "view `1-1`" in agents and "1-1+1" not in agents


def test_depth_status_is_clean_and_reports_the_materialized_ref(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1-1", out, depth=1)

    status = api.work(tmp_path, "1-1", out, status=True)

    assert status.ok
    assert status.depth == 1 and status.view_ref == "1-1+1"
    assert status.nodes == 3
    assert {entry.ref for entry in status.entries} == {"1-1", "2-1", "3-1"}


def test_switching_depth_removes_and_restores_stale_links(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1-1", out)
    assert _link_count(out) == 4

    api.work(tmp_path, "1-1", out, depth=1)
    assert _link_count(out) == 3
    assert not (out / "4-1.md").exists()
    assert api.work(tmp_path, "1-1", out, status=True).ok

    api.work(tmp_path, "1-1", out)
    assert _link_count(out) == 4
    assert (out / "4-1.md").is_symlink()
    assert api.work(tmp_path, "1-1", out, status=True).ok


def test_depth_zero_materializes_the_root_only(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    result = api.work(tmp_path, "1-1", out, depth=0)

    assert result.view_ref == "1-1+0" and result.nodes == 1
    assert _link_count(out) == 1
    assert (out / "1-1.md").is_symlink()
    assert not (out / "2-1.md").exists()


def test_depth_limited_cycle_keeps_minimum_distance(write, tmp_path):
    _cycle(write, tmp_path)
    out = tmp_path / "work"

    result = api.work(tmp_path, "1-1", out, depth=1)

    assert result.view_ref == "1-1+1"
    assert _link_count(out) == 3
    assert (out / "3-1.md").is_symlink()
    assert not (out / "4-1.md").exists()
    assert api.work(tmp_path, "1-1", out, status=True).ok


def test_export_and_work_agree_on_flat_paths(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(
        nodes,
        1,
        links=[
            {"to": "2-1", "type": "breaks_down"},
            {"to": "3-1", "type": "breaks_down"},
        ],
        title="Root",
    )
    write(nodes, 2, name="named")
    write(nodes, 3, title="Plain")
    graph = tmp_path / "graph"
    work = tmp_path / "work"

    api.export_view("graph", tmp_path, "1-1", graph)
    api.work(tmp_path, "1-1", work)

    generated = {"INDEX.md", "REFS.md", "AGENTS.md", "STALE.md"}

    def relpaths(root):
        return {
            path.relative_to(root).as_posix()
            for path in root.rglob("*.md")
            if path.name not in generated
        }

    assert relpaths(graph) == relpaths(work)
    assert relpaths(work) == {"1-1.md", "2-1.md", "3-1.md"}


def test_work_writes_only_the_root_index(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1-1", out)

    indexes = sorted(out.rglob("INDEX.md"))
    assert indexes == [out / "INDEX.md"]
    assert (out / "INDEX.md").is_file() and not (out / "INDEX.md").is_symlink()
    assert api.work(tmp_path, "1-1", out, status=True).ok

    stray = out / "stray.md"
    stray.write_text("not a view node\n", encoding="utf-8")
    status = api.work(tmp_path, "1-1", out, status=True)
    assert not status.ok
    assert _entry(status, "stray.md").status == "stray"

    stray.unlink()
    assert api.work(tmp_path, "1-1", out, status=True).ok


def test_work_index_name_collision_is_refused(write, tmp_path):
    from bd_tree.errors import ExportError

    _tree(write, tmp_path)
    out = tmp_path / "work"
    with pytest.raises(ExportError, match="collides with generated"):
        api.work(tmp_path, "1-1", out, path_template="INDEX.md")


def test_work_rebuild_is_byte_identical_for_generated_files(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1-1", out)
    before = {
        path.relative_to(out).as_posix(): path.read_bytes()
        for path in (out / "INDEX.md", out / "REFS.md", out / "AGENTS.md")
    }

    api.work(tmp_path, "1-1", out)

    after = {
        path.relative_to(out).as_posix(): path.read_bytes()
        for path in (out / "INDEX.md", out / "REFS.md", out / "AGENTS.md")
    }
    assert after == before


def test_switching_components_removes_old_links_and_keeps_one_index(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, version=1, links=[{"to": "2-1", "type": "breaks_down"}])
    write(nodes, 2, version=1)
    write(nodes, 1, version=2, links=[{"to": "2-2", "type": "breaks_down"}])
    write(nodes, 2, version=2)
    write(nodes, 7)

    api.work(tmp_path, "1-1")
    out = (tmp_path / "bd_work").resolve()

    api.work(tmp_path, "7-1")

    assert not (out / "1-1.md").exists()
    assert not (out / "2-1.md").exists()
    assert (out / "7-1.md").is_symlink()
    assert sorted(out.rglob("INDEX.md")) == [out / "INDEX.md"]
    assert api.work(tmp_path, "7-1", status=True).ok
