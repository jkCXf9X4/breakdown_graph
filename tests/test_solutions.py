"""Lifecycle tests for the ``bd solution`` wrapper over git worktrees."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from bd_tree.api import solution_list, solution_new, solution_remove
from bd_tree.cli import main
from bd_tree.errors import BreakdownError

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None, reason="git is not available"
)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init(repo: Path) -> None:
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "commit.gpgsign", "false")


def _commit(repo: Path, message: str = "init") -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def _store(write, repo: Path) -> None:
    write(repo / "nodes", 1)
    write(repo / "nodes", 2)


def _hidden_store(write, repo: Path) -> None:
    nodes = repo / ".bd_tree" / "nodes"
    write(nodes, 1, links=[{"to": "2", "type": "breaks_down"}])
    write(nodes, 2)
    (repo / ".bd_tree" / "ROOT").write_text("2-1\n", encoding="utf-8")


def test_new_creates_default_sibling_branch(write, tmp_path, capsys):
    _init(tmp_path)
    _store(write, tmp_path)
    _commit(tmp_path)

    assert main(["solution", "new", "sol-a", "--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out

    target = tmp_path.parent / "sol-a"
    assert target.is_dir()
    assert (target / "nodes").is_dir()
    assert _git(target, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "sol-a"
    assert f"worktree {target}" in out
    assert "branch sol-a" in out
    assert "project ." in out
    assert f"cd {target}" in out
    assert "bd work 1-1" in out
    assert "BD_ROOT=" not in out


def test_list_marks_main_and_store(write, tmp_path, capsys):
    _init(tmp_path)
    _store(write, tmp_path)
    _commit(tmp_path)
    assert main(["solution", "new", "sol-list", "--root", str(tmp_path)]) == 0

    assert main(["solution", "list", "--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    entries = solution_list(tmp_path)

    assert len(entries) == 2
    assert entries[0].primary is True
    assert entries[0].store is True
    sol = next(entry for entry in entries if entry.branch == "sol-list")
    assert sol.store is True
    assert str(tmp_path) in out
    assert "sol-list" in out
    assert "main" in out
    assert "store" in out


def test_remove_keeps_branch(write, tmp_path, capsys):
    _init(tmp_path)
    _store(write, tmp_path)
    _commit(tmp_path)
    assert main(["solution", "new", "sol-rm", "--root", str(tmp_path)]) == 0
    target = tmp_path.parent / "sol-rm"
    assert target.is_dir()

    assert main(["solution", "remove", "sol-rm", "--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out

    assert not target.exists()
    assert f"removed {target}" in out
    branch = subprocess.run(
        ["git", "-C", str(tmp_path), "show-ref", "--verify", "refs/heads/sol-rm"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert branch.returncode == 0
    assert all(entry.branch != "sol-rm" for entry in solution_list(tmp_path))


def test_new_outside_git_raises(write, tmp_path):
    store = tmp_path / "store"
    write(store / "nodes", 1)
    with pytest.raises(BreakdownError, match="not inside a git work tree"):
        solution_new(store, "sol-a")
    assert main(["solution", "new", "sol-a", "--root", str(store)]) == 2


def test_new_refuses_existing_path(write, tmp_path):
    _init(tmp_path)
    _store(write, tmp_path)
    _commit(tmp_path)
    taken = tmp_path / "taken"
    taken.mkdir()

    with pytest.raises(BreakdownError, match="already exists"):
        solution_new(tmp_path, "sol-taken", path=taken)


def test_new_from_starts_at_named_commit(write, tmp_path):
    _init(tmp_path)
    _store(write, tmp_path)
    first = _commit(tmp_path, "first")
    write(tmp_path / "nodes", 1, body="second\n")
    second = _commit(tmp_path, "second")
    assert first != second

    result = solution_new(tmp_path, "sol-from", from_ref=first)

    assert result.created_branch is True
    assert _git(result.path, "rev-parse", "HEAD").stdout.strip() == first


def test_new_exposes_the_classic_project_and_view(write, tmp_path):
    _init(tmp_path)
    _store(write, tmp_path)
    _commit(tmp_path)

    result = solution_new(tmp_path, "sol-fields")

    assert result.store == "."
    assert result.project == "."
    assert result.view == "1-1"


def test_new_and_list_expose_hidden_store_project_and_view(write, tmp_path):
    _init(tmp_path)
    _hidden_store(write, tmp_path)
    _commit(tmp_path)

    result = solution_new(tmp_path / ".bd_tree", "sol-hidden")

    assert result.store == ".bd_tree"
    assert result.project == "."
    assert result.view == "2-1"

    entries = solution_list(tmp_path / ".bd_tree")
    solved = next(entry for entry in entries if entry.branch == "sol-hidden")
    assert solved.store is True
    assert solved.project == "."
    assert {entry.project for entry in entries} == {"."}


def test_remove_refuses_primary(write, tmp_path):
    _init(tmp_path)
    _store(write, tmp_path)
    _commit(tmp_path)
    branch = _git(tmp_path, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()

    with pytest.raises(BreakdownError, match="primary worktree"):
        solution_remove(tmp_path, str(tmp_path))
    with pytest.raises(BreakdownError, match="primary worktree"):
        solution_remove(tmp_path, branch)
