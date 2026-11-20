"""Thin wrapper over ``git worktree``: one worktree per solution.

Git owns the solution boundary; a work folder built by :mod:`bd_tree.work`
owns the layout inside one checkout.  This module only translates the three
lifecycle steps (create, list, remove) into git commands.  It keeps no state:
the worktree list reported by git is the only source of truth.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .errors import BreakdownError
from .loader import load, resolve_store_root

GIT_TIMEOUT = 5.0


@dataclass(frozen=True)
class SolutionEntry:
    """One worktree, as reported by ``git worktree list --porcelain``."""

    path: Path
    branch: str | None
    head: str
    project: str
    primary: bool = False
    store: bool = False

    @property
    def label(self) -> str:
        return self.branch or "detached"


@dataclass(frozen=True)
class SolutionResult:
    """A newly created solution worktree."""

    path: Path
    branch: str
    store: str
    project: str
    view: str
    created_branch: bool


def _git(
    root: Path, *args: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT,
            check=False,
        )
    except FileNotFoundError as exc:
        raise BreakdownError("git is not installed or not on PATH") from exc
    except (OSError, subprocess.SubprocessError) as exc:
        raise BreakdownError(f"git failed: {exc}") from exc
    if check and completed.returncode != 0:
        detail = (
            completed.stderr.strip()
            or completed.stdout.strip()
            or f"exit {completed.returncode}"
        )
        raise BreakdownError(f"git {' '.join(args)} failed: {detail}")
    return completed


def _repo_root(root: Path) -> Path:
    completed = _git(root, "rev-parse", "--show-toplevel", check=False)
    top = completed.stdout.strip()
    if completed.returncode != 0 or not top:
        raise BreakdownError(f"not inside a git work tree: {root}")
    return Path(top).resolve()


def _relative_store(store: Path, repo_root: Path) -> str:
    try:
        return store.resolve().relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise BreakdownError(
            f"store '{store}' is not inside git work tree '{repo_root}'"
        ) from exc


def _project_relative(store: Path, repo_root: Path) -> str:
    """Project root relative to the repo; a hidden store uses its parent."""
    relative = Path(_relative_store(store, repo_root))
    if relative.name == ".bd_tree":
        relative = relative.parent
    return relative.as_posix()


def _validate_name(name: str) -> None:
    if not name:
        raise BreakdownError("solution name must not be empty")
    if name.startswith("-"):
        raise BreakdownError(f"invalid solution name {name!r}: must not start with '-'")
    if ".." in name:
        raise BreakdownError(f"invalid solution name {name!r}: must not contain '..'")
    if name[0] in ("/", "\\"):
        raise BreakdownError(
            f"invalid solution name {name!r}: must not start with a path separator"
        )


def _branch_exists(root: Path, name: str) -> bool:
    completed = _git(
        root, "show-ref", "--verify", "--quiet", f"refs/heads/{name}", check=False
    )
    return completed.returncode == 0


def new(
    root: str | Path,
    name: str,
    *,
    path: str | Path | None = None,
    from_ref: str | None = None,
) -> SolutionResult:
    """Create a worktree for ``name`` without touching the new checkout."""
    _validate_name(name)
    store = resolve_store_root(Path(root).resolve())
    repo_root = _repo_root(store)
    relative = _relative_store(store, repo_root)
    project = _project_relative(store, repo_root)
    view = load(store).root_ref or ""

    if path is None:
        target = repo_root.parent / name
    else:
        candidate = Path(path).expanduser()
        target = candidate if candidate.is_absolute() else repo_root.parent / candidate
    target = target.resolve()
    if os.path.lexists(target):
        raise BreakdownError(f"path already exists: {target}")

    exists = _branch_exists(repo_root, name)
    args = ["worktree", "add", str(target)]
    if exists:
        args.append(name)
    else:
        args.extend(["-b", name, from_ref or "HEAD"])
    _git(repo_root, *args)

    return SolutionResult(
        path=target,
        branch=name,
        store=relative,
        project=project,
        view=view,
        created_branch=not exists,
    )


def _entries(store: Path) -> tuple[list[SolutionEntry], Path]:
    store = resolve_store_root(store)
    repo_root = _repo_root(store)
    relative = Path(_relative_store(store, repo_root))
    project = _project_relative(store, repo_root)
    completed = _git(repo_root, "worktree", "list", "--porcelain")
    entries: list[SolutionEntry] = []
    path: Path | None = None
    head = ""
    branch: str | None = None
    for line in completed.stdout.splitlines():
        if line.startswith("worktree "):
            if path is not None:
                entries.append(
                    SolutionEntry(
                        path=path,
                        branch=branch,
                        head=head,
                        project=project,
                        primary=not entries,
                        store=(path / relative / "nodes").is_dir(),
                    )
                )
            path = Path(line[len("worktree ") :])
            head = ""
            branch = None
        elif line.startswith("HEAD ") and path is not None:
            head = line[len("HEAD ") :]
        elif line.startswith("branch ") and path is not None:
            branch = line[len("branch ") :].removeprefix("refs/heads/")
    if path is not None:
        entries.append(
            SolutionEntry(
                path=path,
                branch=branch,
                head=head,
                project=project,
                primary=not entries,
                store=(path / relative / "nodes").is_dir(),
            )
        )
    return entries, repo_root


def listing(root: str | Path) -> list[SolutionEntry]:
    """Every worktree of the repository that contains ``root``."""
    return _entries(Path(root).resolve())[0]


def remove(root: str | Path, target: str, *, force: bool = False) -> SolutionEntry:
    """Remove one worktree by branch name or path; the branch is kept."""
    store = Path(root).resolve()
    entries, repo_root = _entries(store)
    match: SolutionEntry | None = None
    for entry in entries:
        if entry.branch == target:
            match = entry
            break
    if match is None:
        candidate = Path(target).expanduser()
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        resolved = candidate.resolve()
        for entry in entries:
            if entry.path.resolve() == resolved or str(entry.path) == target:
                match = entry
                break
    if match is None:
        raise BreakdownError(f"no worktree for {target!r} in {repo_root}")
    if match.primary:
        raise BreakdownError(f"refusing to remove the primary worktree: {match.path}")

    args = ["worktree", "remove", str(match.path)]
    if force:
        args.append("--force")
    _git(repo_root, *args)
    return match
