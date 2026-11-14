from __future__ import annotations

import os
from pathlib import Path

from breakdown import api

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "workspace" / "licentiate-n"


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
        dest = out / node.home
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
    out = tmp_path / "cli"
    from breakdown.cli import main

    assert main(["work", "1", "--root", str(tmp_path), "--out", str(out)]) == 0
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


def test_corpus_smoke_work_tree(write, tmp_path):
    out = tmp_path / "corpus-work"
    result = api.work(CORPUS, "1", out)
    assert result.nodes == 128
    assert result.symlinks == 128
    assert sum(1 for path in out.rglob("*.md") if path.is_symlink()) == 128
    generated = {path.name for path in out.iterdir() if path.is_file()}
    assert {"INDEX.md", "AGENTS.md", "REFS.md"} <= generated


def test_default_out_is_under_build_work(write, tmp_path):
    _tree(write, tmp_path)
    result = api.work(tmp_path, "1")
    expected = (tmp_path / "build" / "work" / "1").resolve()
    assert result.out == expected
    assert expected.is_dir()
    assert (expected / "claims" / "2.md").is_symlink()


def test_path_template_still_applies(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "templated"
    api.work(tmp_path, "1", out, path_template="{layer}/{ref}.md")
    assert (out / "intent" / "1.md").is_symlink()
    assert (out / "claims" / "2.md").is_symlink()
    assert (out / "evidence" / "4.md").is_symlink()
    assert "`claims/2.md`" in (out / "REFS.md").read_text(encoding="utf-8")


def test_status_and_writeback_use_refs_manifest_when_home_changes(write, tmp_path):
    _tree(write, tmp_path)
    out = tmp_path / "work"
    api.work(tmp_path, "1", out)
    dest = out / "claims" / "2.md"
    dest.unlink()
    dest.write_text(
        "---\n"
        "id: 2\n"
        "home: moved/2.md\n"
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
