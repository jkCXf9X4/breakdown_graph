from __future__ import annotations

import os
import shutil

import pytest

from bd_tree import api


def _tree(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"], layer="intent")
    write(nodes, 2, contains=["4"], layer="claims")
    write(nodes, 3, layer="review")
    write(nodes, 4, layer="evidence")
    return nodes


def _entry(result, path):
    return next(entry for entry in result.entries if entry.path == path)


def test_work_links_every_node_and_writes_generated_files(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    result = api.work(tmp_path, "1", out)

    assert result.nodes == 4
    assert result.symlinks == 4
    store = api.load(tmp_path)
    for node in store.nodes.values():
        dest = out / node.folder / f"{node.ref}.md"
        assert dest.is_symlink()
        assert dest.resolve() == node.path.resolve()
        assert not os.path.isabs(os.readlink(dest))
    for name in ("INDEX.md", "AGENTS.md", "REFS.md"):
        assert (out / name).is_file()
        assert not (out / name).is_symlink()
    agents = (out / "AGENTS.md").read_text(encoding="utf-8")
    assert "symlink" in agents and "--writeback" in agents
    refs = (out / "REFS.md").read_text(encoding="utf-8")
    assert "| Path | Ref | Title |" in refs
    assert "`claims/2.md` | 2 |" in refs


def test_work_cli_builds_the_same_tree(write, tmp_path, capsys):
    _tree(write, tmp_path)
    out = tmp_path / "bd_work"
    from bd_tree.cli import main

    assert main(["work", "1", "--root", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert "4 nodes, 4 symlinks" in output
    assert (out / "claims" / "2.md").is_symlink()


def test_write_through_edits_the_store_file(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1", out)
    dest = out / "claims" / "2.md"
    dest.write_text("edited through the link\n", encoding="utf-8")
    assert (tmp_path / "nodes" / "2.md").read_text(encoding="utf-8") == (
        "edited through the link\n"
    )


def test_status_is_clean_after_build(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1", out)
    status = api.work(tmp_path, "1", out, status=True)
    assert status.ok
    assert {entry.status for entry in status.entries} == {"ok"}


def test_status_inspects_the_areas_view_not_the_requested_ref(write, tmp_path):
    nodes = _tree(write, tmp_path)
    write(nodes, 1, version=1, contains=["2-1"], layer="intent")
    write(nodes, 2, version=1, layer="claims")
    (tmp_path / "ROOT").write_text("1-1\n", encoding="utf-8")

    built = api.work(tmp_path, "1")
    assert built.ref == "1"

    status = api.work(tmp_path, status=True)
    assert status.ref == "1"
    assert status.ok

    status = api.work(tmp_path, "1-1", status=True)
    assert status.ref == "1"
    assert status.ok


@pytest.mark.parametrize("mode", ["status", "writeback"])
def test_status_and_writeback_require_a_built_area(write, tmp_path, mode):
    from bd_tree.errors import ExportError

    _tree(write, tmp_path)
    kwargs = {mode: True}

    with pytest.raises(ExportError, match="bd work"):
        api.work(tmp_path, "1", **kwargs)
    assert not (tmp_path / "bd_work").exists()


def test_area_and_edit_path_are_read_only(write, tmp_path):
    _tree(write, tmp_path)
    api.work(tmp_path, "1")
    out = (tmp_path / "bd_work").resolve()
    from bd_tree.work import area, edit_path

    watched = [
        out / "INDEX.md",
        out / "REFS.md",
        out / "AGENTS.md",
        out / "claims" / "2.md",
    ]
    before = {
        path: (path.stat().st_mtime_ns, path.read_bytes()) for path in watched
    }

    current = area(tmp_path)
    assert current.out == out
    assert current.ref == "1"
    assert edit_path(tmp_path, "2") == out / "claims" / "2.md"

    after = {
        path: (path.stat().st_mtime_ns, path.read_bytes()) for path in watched
    }
    assert after == before


def test_edit_path_returns_the_expected_path_without_building(write, tmp_path):
    _tree(write, tmp_path)
    api.work(tmp_path, "1")
    out = (tmp_path / "bd_work").resolve()
    dest = out / "claims" / "2.md"
    dest.unlink()
    from bd_tree.work import edit_path

    assert edit_path(tmp_path, "2") == dest
    assert not dest.exists()


def test_edit_path_rejects_an_out_of_view_ref(write, tmp_path):
    from bd_tree.errors import ExportError
    from bd_tree.work import edit_path

    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], layer="intent")
    write(nodes, 2, layer="claims")
    write(nodes, 9, layer="outside")
    api.work(tmp_path, "1")

    with pytest.raises(ExportError) as caught:
        edit_path(tmp_path, "9")
    message = str(caught.value)
    assert "current view 1" in message
    assert "bd views" in message and "bd work" in message


def test_edit_path_requires_a_built_area(write, tmp_path):
    from bd_tree.errors import ExportError
    from bd_tree.work import edit_path

    _tree(write, tmp_path)
    with pytest.raises(ExportError, match="bd work"):
        edit_path(tmp_path, "1")


def test_status_reports_a_detached_file(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1", out)
    dest = out / "claims" / "2.md"
    original = (tmp_path / "nodes" / "2.md").read_text(encoding="utf-8")
    dest.unlink()
    dest.write_text(original + "\nlocal note\n", encoding="utf-8")

    status = api.work(tmp_path, "1", out, status=True)
    assert not status.ok
    assert _entry(status, "claims/2.md").status == "detached"
    assert _entry(status, "claims/2.md").ref == "2"
    assert _entry(status, "intent/1.md").status == "ok"


def test_writeback_restores_store_and_relinks(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1", out)
    dest = out / "claims" / "2.md"
    edited = (tmp_path / "nodes" / "2.md").read_text(encoding="utf-8") + "\nlocal note\n"
    dest.unlink()
    dest.write_text(edited, encoding="utf-8")

    result = api.work(tmp_path, "1", out, writeback=True)
    assert result.written == 1
    assert (tmp_path / "nodes" / "2.md").read_text(encoding="utf-8") == edited
    assert dest.is_symlink()
    assert dest.resolve() == (tmp_path / "nodes" / "2.md").resolve()
    assert api.work(tmp_path, "1", out, status=True).ok


def test_stray_file_is_reported_and_left_alone(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1", out)
    stray = out / "stray.md"
    stray.write_text("not a view node\n", encoding="utf-8")

    status = api.work(tmp_path, "1", out, status=True)
    assert not status.ok
    assert _entry(status, "stray.md").status == "stray"

    result = api.work(tmp_path, "1", out, writeback=True)
    assert result.written == 0
    assert not result.ok
    assert stray.is_file() and not stray.is_symlink()
    assert not (tmp_path / "nodes" / "stray.md").exists()


def test_clean_rebuilds_without_touching_store_files(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1", out)
    store_before = {
        path.name: path.read_bytes() for path in (tmp_path / "nodes").glob("*.md")
    }

    result = api.work(
        tmp_path, "1", out, path_template="{ref}.md", clean=True
    )
    assert result.symlinks == 4
    assert (out / "1.md").is_symlink()
    assert not (out / "intent" / "1.md").exists()
    store_after = {
        path.name: path.read_bytes() for path in (tmp_path / "nodes").glob("*.md")
    }
    assert store_before == store_after


def test_default_out_is_the_single_project_work_area(write, tmp_path):
    _tree(write, tmp_path)
    result = api.work(tmp_path, "1")
    expected = (tmp_path / "bd_work").resolve()
    assert result.out == expected
    assert expected.is_dir()
    assert (expected / "claims" / "2.md").is_symlink()


def test_default_out_for_hidden_store_is_project_bd_work(write, tmp_path):
    store = tmp_path / ".bd_tree" / "nodes"
    write(store, 1, contains=["2"], layer="intent")
    write(store, 2, layer="claims")
    result = api.work(tmp_path, "1")
    expected = (tmp_path / "bd_work").resolve()
    assert result.out == expected
    assert (expected / "intent" / "1.md").is_symlink()
    assert (expected / "intent" / "1.md").resolve() == (store / "1.md").resolve()


def test_ref_switch_replaces_the_same_work_area(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], layer="intent")
    write(nodes, 2, layer="claims")
    write(nodes, 1, version=1, contains=["2-1"], layer="intent")
    write(nodes, 2, version=1, layer="claims")

    first = api.work(tmp_path, "1-1")
    out = first.out
    assert out == (tmp_path / "bd_work").resolve()
    old_link = out / "intent" / "1-1.md"
    assert old_link.is_symlink()
    assert old_link.resolve() == (nodes / "1-1.md").resolve()

    second = api.work(tmp_path, "1")

    assert second.out == out
    assert not (out / "intent" / "1-1.md").is_symlink()
    assert not (out / "intent" / "1-1.md").exists()
    assert not (out / "claims" / "2-1.md").is_symlink()
    assert (out / "intent" / "1.md").resolve() == (nodes / "1.md").resolve()
    assert (out / "claims" / "2.md").resolve() == (nodes / "2.md").resolve()
    refs = (out / "REFS.md").read_text(encoding="utf-8")
    index = (out / "INDEX.md").read_text(encoding="utf-8")
    agents = (out / "AGENTS.md").read_text(encoding="utf-8")
    assert "view 1" in refs and "1-1" not in refs
    assert "# View 1" in index and "1-1" not in index
    assert "view `1`" in agents
    assert api.work(tmp_path, "1", status=True).ok


def test_unexpected_store_symlink_is_cleaned_without_refs_manifest(write, tmp_path):
    _tree(write, tmp_path)
    write(tmp_path / "nodes", 5, layer="outside")
    out = tmp_path / "work"
    api.work(tmp_path, "1", out)
    (out / "REFS.md").unlink()
    stray = out / "extra.md"
    stray.symlink_to(os.path.relpath(tmp_path / "nodes" / "5.md", out))

    result = api.work(tmp_path, "1", out)

    assert result.symlinks == 4
    assert not stray.is_symlink()
    assert not stray.exists()
    assert (out / "REFS.md").is_file()
    assert api.work(tmp_path, "1", out, status=True).ok


def test_detached_file_blocks_a_ref_switch_until_clean(write, tmp_path):
    from bd_tree.errors import ExportError

    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], layer="intent")
    write(nodes, 2, layer="claims")
    write(nodes, 1, version=1, contains=["2-1"], layer="intent")
    write(nodes, 2, version=1, layer="claims")

    api.work(tmp_path, "1-1")
    out = tmp_path / "bd_work"
    dest = out / "intent" / "1-1.md"
    dest.unlink()
    dest.write_text("detached\n", encoding="utf-8")

    with pytest.raises(ExportError) as caught:
        api.work(tmp_path, "1")
    message = str(caught.value)
    assert "--writeback" in message and "--clean" in message
    assert dest.read_text(encoding="utf-8") == "detached\n"

    api.work(tmp_path, "1", clean=True)
    assert not (out / "intent" / "1-1.md").exists()
    assert (out / "intent" / "1.md").is_symlink()


def test_path_template_still_applies(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "templated"
    api.work(tmp_path, "1", out, path_template="{layer}/{ref}.md")
    assert (out / "intent" / "1.md").is_symlink()
    assert (out / "claims" / "2.md").is_symlink()
    assert (out / "evidence" / "4.md").is_symlink()
    assert "`claims/2.md`" in (out / "REFS.md").read_text(encoding="utf-8")


def test_changing_folder_removes_the_old_link_in_one_rebuild(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], folder="root", name="1")
    write(nodes, 2, folder="child", name="2", layer="claims")
    out = tmp_path / "work"
    api.work(tmp_path, "1", out)
    assert (out / "root" / "1.md").is_symlink()

    write(nodes, 1, contains=["2"], folder="renamed", name="1", layer="intent")
    api.work(tmp_path, "1", out)

    assert (out / "renamed" / "1.md").is_symlink()
    assert not (out / "root" / "1.md").is_symlink()
    assert not (out / "root" / "1.md").exists()
    assert api.work(tmp_path, "1", out, status=True).ok


def test_mixed_placement_produces_mixed_paths_and_rebuild_idempotently(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2", "3"], layer="intent")
    write(nodes, 2)  # no folder/name -> 2-title-of-2.md
    write(nodes, 3, home="deep/review/3.md", title="Deep Review")
    out = tmp_path / "work"

    result = api.work(tmp_path, "1", out)

    assert result.symlinks == 3
    expected = {
        "intent/1.md": nodes / "1.md",
        "2-title-of-2.md": nodes / "2.md",
        "3-deep-review.md": nodes / "3.md",
    }
    for rel, source in expected.items():
        dest = out / rel
        assert dest.is_symlink()
        assert dest.resolve() == source.resolve()
        assert not os.path.isabs(os.readlink(dest))
    assert api.work(tmp_path, "1", out, status=True).ok

    before = _link_count(out)
    again = api.work(tmp_path, "1", out)

    assert again.symlinks == 3
    assert _link_count(out) == before
    assert api.work(tmp_path, "1", out, status=True).ok


def test_folder_and_title_build_nested_named_work_area(write, tmp_path):
    nodes = tmp_path / "nodes"
    write(nodes, 1, contains=["2"], folder="intent", title="Root Intent")
    write(nodes, 2, folder="06-evolution/suggested", title="New Idea")
    out = tmp_path / "work"

    result = api.work(tmp_path, "1", out)

    assert result.symlinks == 2
    root_link = out / "intent" / "root-intent.md"
    idea_link = out / "06-evolution" / "suggested" / "new-idea.md"
    assert root_link.is_symlink() and root_link.resolve() == (nodes / "1.md").resolve()
    assert idea_link.is_symlink() and idea_link.resolve() == (nodes / "2.md").resolve()
    assert api.work(tmp_path, "1", out, status=True).ok

    before = _link_count(out)
    api.work(tmp_path, "1", out)
    assert _link_count(out) == before
    assert api.work(tmp_path, "1", out, status=True).ok

    from bd_tree.work import edit_path

    assert edit_path(tmp_path, "2", out) == idea_link
    index = (out / "INDEX.md").read_text(encoding="utf-8")
    refs = (out / "REFS.md").read_text(encoding="utf-8")
    assert "[Root Intent](intent/root-intent.md)" in index
    assert "[New Idea](06-evolution/suggested/new-idea.md)" in index
    assert "`06-evolution/suggested/new-idea.md` | 2 |" in refs


def test_status_and_writeback_use_refs_manifest_when_placement_changes(
    write, tmp_path
):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1", out)
    dest = out / "claims" / "2.md"
    dest.unlink()
    dest.write_text(
        "---\n"
        "id: 2\n"
        "folder: moved\n"
        "name: 2\n"
        "title: Moved\n"
        "summary: s\n"
        'contains: ["4"]\n'
        "---\n"
        "new body\n",
        encoding="utf-8",
    )

    status = api.work(tmp_path, "1", out, status=True)
    entry = _entry(status, "claims/2.md")
    assert entry.ref == "2"
    assert entry.status == "detached"
    assert not status.ok

    result = api.work(tmp_path, "1", out, writeback=True)
    assert result.written == 1
    assert (tmp_path / "nodes" / "2.md").read_text(encoding="utf-8").endswith(
        "new body\n"
    )
    assert dest.is_symlink()
    assert api.work(tmp_path, "1", out, status=True).ok


def _link_count(out):
    return sum(1 for path in out.rglob("*.md") if path.is_symlink())


def test_two_work_dirs_share_the_same_nodes(write, tmp_path):
    _tree(write, tmp_path)
    a = tmp_path / "a"
    b = tmp_path / "b"
    api.work(tmp_path, "1", a)
    api.work(tmp_path, "2", b)

    through_b = b / "claims" / "2.md"
    through_a = a / "claims" / "2.md"
    assert through_b.is_symlink() and through_a.is_symlink()
    through_b.write_text("edited through b\n", encoding="utf-8")

    assert through_a.read_text(encoding="utf-8") == "edited through b\n"
    assert (tmp_path / "nodes" / "2.md").read_text(encoding="utf-8") == (
        "edited through b\n"
    )


def test_plain_refresh_is_idempotent(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1", out)
    before = _link_count(out)

    result = api.work(tmp_path, "1", out)

    assert result.symlinks == 4
    assert _link_count(out) == before
    assert api.work(tmp_path, "1", out, status=True).ok


def test_refresh_repairs_missing_and_wrong_target_links(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1", out)

    (out / "claims" / "2.md").unlink()
    wrong = out / "evidence" / "4.md"
    wrong.unlink()
    wrong.symlink_to(os.path.relpath(tmp_path / "nodes" / "3.md", wrong.parent))

    result = api.work(tmp_path, "1", out)

    assert result.symlinks == 4
    assert (out / "claims" / "2.md").is_symlink()
    assert (out / "evidence" / "4.md").resolve() == (
        tmp_path / "nodes" / "4.md"
    ).resolve()
    assert api.work(tmp_path, "1", out, status=True).ok


def test_refresh_removes_stale_ref_links(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1", out)

    result = api.work(tmp_path, "2", out)

    assert result.ref == "2"
    assert not (out / "intent" / "1.md").exists()
    assert not (out / "review" / "3.md").exists()
    assert (out / "claims" / "2.md").is_symlink()
    assert api.work(tmp_path, "2", out, status=True).ok


def test_detached_file_blocks_refresh_until_writeback(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "bd_work"
    api.work(tmp_path, "1")
    dest = out / "claims" / "2.md"
    original = dest.read_text(encoding="utf-8")
    dest.unlink()
    dest.write_text(original + "detached edit\n", encoding="utf-8")
    from bd_tree.cli import main

    assert main(["work", "1", "--root", str(tmp_path)]) == 2
    assert not dest.is_symlink()
    assert dest.read_text(encoding="utf-8") == original + "detached edit\n"

    assert (
        main(
            [
                "work",
                "1",
                "--root",
                str(tmp_path),
                "--writeback",
            ]
        )
        == 0
    )
    assert dest.is_symlink()
    assert (tmp_path / "nodes" / "2.md").read_text(encoding="utf-8") == (
        original + "detached edit\n"
    )
    assert main(["work", "1", "--root", str(tmp_path)]) == 0


def test_stray_blocks_refresh_and_clean_discards(write, tmp_path):
    from bd_tree.errors import ExportError

    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1", out)
    stray = out / "stray.md"
    stray.write_text("not a view node\n", encoding="utf-8")

    with pytest.raises(ExportError):
        api.work(tmp_path, "1", out)
    assert stray.is_file()
    assert api.work(tmp_path, "1", out, status=True).ok is False

    api.work(tmp_path, "1", out, clean=True)
    assert not stray.exists()
    assert api.work(tmp_path, "1", out, status=True).ok


def test_print_is_read_only(write, tmp_path, capsys):
    _tree(write, tmp_path)
    api.work(tmp_path, "1")
    out = (tmp_path / "bd_work").resolve()
    from bd_tree.cli import main

    def snapshot():
        return {
            path: (path.stat().st_mtime_ns, path.read_bytes())
            for path in sorted(out.rglob("*"))
            if path.is_file() or path.is_symlink()
        }

    before = snapshot()
    argv = ["work", "1", "--root", str(tmp_path), "--print"]
    assert main(argv) == 0
    captured = capsys.readouterr()
    assert captured.out == f"{out}\n"
    assert captured.err == ""
    assert snapshot() == before

    assert main(argv) == 0
    assert capsys.readouterr().out == f"{out}\n"
    assert snapshot() == before


def test_print_is_mutually_exclusive_with_status(write, tmp_path):
    _tree(write, tmp_path)
    from bd_tree.cli import main

    with pytest.raises(SystemExit):
        main(["work", "1", "--root", str(tmp_path), "--print", "--status"])


def test_force_overwrites_a_detached_file(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1", out)
    store_before = (tmp_path / "nodes" / "2.md").read_text(encoding="utf-8")
    dest = out / "claims" / "2.md"
    dest.unlink()
    dest.write_text("detached edit\n", encoding="utf-8")

    result = api.work(tmp_path, "1", out, force=True)

    assert result.symlinks == 4
    assert dest.is_symlink()
    assert dest.read_text(encoding="utf-8") == store_before
    assert api.work(tmp_path, "1", out, status=True).ok


def test_writeback_refuses_a_detached_file_without_frontmatter(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1", out)
    dest = out / "claims" / "2.md"
    dest.unlink()
    dest.write_text("body only\n", encoding="utf-8")
    before = (tmp_path / "nodes" / "2.md").read_text(encoding="utf-8")

    result = api.work(tmp_path, "1", out, writeback=True)

    assert result.written == 0
    assert result.invalid == ["claims/2.md"]
    assert (tmp_path / "nodes" / "2.md").read_text(encoding="utf-8") == before
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
    write(repo / "nodes", 1, contains=["2"], layer="intent")
    write(repo / "nodes", 2, layer="claims")
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
    result = api.work(tmp_path, "1", out)
    assert result.git is None
    agents = (out / "AGENTS.md").read_text(encoding="utf-8")
    assert "Git branch:" not in agents

    from bd_tree.cli import main

    assert main(["work", "1", "--root", str(tmp_path)]) == 0
    assert "branch " not in capsys.readouterr().out


@git_only
def test_work_records_git_branch_commit_and_toplevel(write, tmp_path):
    repo = _git_repo(write, tmp_path)
    branch = _run_git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    commit = _run_git(repo, "rev-parse", "--short", "HEAD")
    toplevel = _run_git(repo, "rev-parse", "--show-toplevel")
    out = tmp_path / "work"

    result = api.work(repo, "1", out)

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

    assert main(["work", "1", "--root", str(repo)]) == 0
    assert f"branch {branch}" in capsys.readouterr().out


@git_only
def test_write_through_is_visible_to_git_status(write, tmp_path):
    repo = _git_repo(write, tmp_path)
    out = tmp_path / "work"
    api.work(repo, "1", out)

    (out / "claims" / "2.md").write_text("edited through the link\n", encoding="utf-8")

    porcelain = _run_git(repo, "status", "--porcelain")
    assert "nodes/2.md" in porcelain
    assert "work/" not in porcelain


def test_depth_limited_work_materializes_only_the_prefix(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    result = api.work(tmp_path, "1", out, depth=1)

    assert result.depth == 1 and result.view_ref == "1+1"
    assert result.nodes == 3 and result.symlinks == 3
    assert (out / "intent" / "1.md").is_symlink()
    assert (out / "claims" / "2.md").is_symlink()
    assert (out / "review" / "3.md").is_symlink()
    assert not (out / "evidence" / "4.md").exists()
    for name in ("REFS.md", "INDEX.md", "AGENTS.md"):
        text = (out / name).read_text(encoding="utf-8")
        assert "1+1" in text
        assert "4.md" not in text
        assert "Title of 4" not in text

    agents = (out / "AGENTS.md").read_text(encoding="utf-8")
    assert "first 1 descendant levels" in agents
    assert "run `bd work 1` for the full closure" in agents


def test_depth_limited_work_edit_path_hides_excluded_refs(write, tmp_path):
    from bd_tree.errors import ExportError
    from bd_tree.work import area, edit_path

    _tree(write, tmp_path)
    out = (tmp_path / "bd_work").resolve()
    api.work(tmp_path, "1", depth=1)

    current = area(tmp_path)
    assert current.ref == "1" and current.depth == 1
    assert current.view_ref == "1+1"
    assert edit_path(tmp_path, "2") == out / "claims" / "2.md"
    with pytest.raises(ExportError, match=r"current view 1\+1"):
        edit_path(tmp_path, "4")


def test_full_work_restores_the_closure_and_drops_the_suffix(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1", out, depth=1)

    result = api.work(tmp_path, "1", out)

    assert result.depth is None and result.view_ref == "1"
    assert result.nodes == 4
    assert (out / "evidence" / "4.md").is_symlink()
    refs = (out / "REFS.md").read_text(encoding="utf-8")
    index = (out / "INDEX.md").read_text(encoding="utf-8")
    agents = (out / "AGENTS.md").read_text(encoding="utf-8")
    assert "view 1\n" in refs and "1+1" not in refs
    assert "# View 1\n" in index and "1+1" not in index
    assert "view `1`" in agents and "1+1" not in agents


def test_depth_status_is_clean_and_reports_the_materialized_ref(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1", out, depth=1)

    status = api.work(tmp_path, "1", out, status=True)

    assert status.ok
    assert status.depth == 1 and status.view_ref == "1+1"
    assert status.nodes == 3
    assert {entry.ref for entry in status.entries} == {"1", "2", "3"}


def test_switching_depth_removes_and_restores_stale_links(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1", out)
    assert _link_count(out) == 4

    api.work(tmp_path, "1", out, depth=1)
    assert _link_count(out) == 3
    assert not (out / "evidence" / "4.md").exists()
    assert api.work(tmp_path, "1", out, status=True).ok

    api.work(tmp_path, "1", out)
    assert _link_count(out) == 4
    assert (out / "evidence" / "4.md").is_symlink()
    assert api.work(tmp_path, "1", out, status=True).ok


def test_depth_zero_materializes_the_root_only(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    result = api.work(tmp_path, "1", out, depth=0)

    assert result.view_ref == "1+0" and result.nodes == 1
    assert _link_count(out) == 1
    assert (out / "intent" / "1.md").is_symlink()
    assert not (out / "claims" / "2.md").exists()
