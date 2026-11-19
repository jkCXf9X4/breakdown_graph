"""Materialize one containment view as a tree of per-file symlinks.

The work directory is the primary editing interface: it mirrors the templated
paths of ``bd export tree``, but every ``.md`` entry is a symlink back to its
original ``nodes/<ref>.md`` file.  Editing a file in the work tree therefore
edits the store directly: there is no sync layer, no state file and no copied
content.  Different work directories may show different views of the same
nodes, and an edit through one is visible through all of them.

Three regular files are generated: ``INDEX.md`` and ``REFS.md`` (navigation) and
``AGENTS.md`` (instructions for a human or agent browsing the tree).
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .errors import BreakdownError, ExportError
from .exporter import _build_paths, _index_text, _prepare_out
from .frontmatter import FrontMatterError, parse_document
from .loader import load, load_view
from .model import Node, View

GENERATED = ("INDEX.md", "AGENTS.md", "REFS.md")
GENERATED_SET = frozenset(GENERATED)

BANNER = "<!-- GENERATED FILE — do not edit. Regenerate with `bd work {ref}`. -->"

STATUS_OK = "ok"
STATUS_MISSING = "missing"
STATUS_WRONG_TARGET = "wrong-target"
STATUS_DETACHED = "detached"
STATUS_STRAY = "stray"
STATUS_STALE = "stale-ref"

_REF_ROW = re.compile(
    r"^\|\s*`(?P<path>[^`]+)`\s*\|\s*(?P<ref>\d+(?:-\d+)?)\s*\|"
)
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

GIT_TIMEOUT = 5.0


@dataclass(frozen=True)
class GitContext:
    """The checkout a store belongs to, when one can be detected."""

    branch: str
    commit: str
    toplevel: str


def _git(root: Path, *args: str) -> str | None:
    """Run one read-only git query; any failure yields ``None``."""
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def git_context(root: str | Path) -> GitContext | None:
    """Detect the git checkout that contains ``root``, without requiring git."""
    root = Path(root)
    if _git(root, "rev-parse", "--is-inside-work-tree") != "true":
        return None
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    commit = _git(root, "rev-parse", "--short", "HEAD")
    toplevel = _git(root, "rev-parse", "--show-toplevel")
    if not (branch and commit and toplevel):
        return None
    return GitContext(branch=branch, commit=commit, toplevel=toplevel)


@dataclass(frozen=True)
class WorkEntry:
    """One expected path, or one stray regular file, and its current state."""

    path: str  # relative POSIX path under the work directory
    ref: str | None
    status: str


@dataclass
class WorkResult:
    out: Path
    ref: str
    nodes: int
    symlinks: int
    files: list[Path] = field(default_factory=list)
    entries: list[WorkEntry] = field(default_factory=list)
    written: int = 0
    invalid: list[str] = field(default_factory=list)
    git: GitContext | None = None

    @property
    def ok(self) -> bool:
        return all(entry.status == STATUS_OK for entry in self.entries)


def _main_root(node_refs: dict[str, Node]) -> str:
    mains = [node for node in node_refs.values() if node.version == 0]
    if not mains:
        raise BreakdownError("store has no main nodes")
    return min(mains, key=lambda node: node.id).ref


def _resolve_view(root: str | Path, ref: str | int | None) -> View:
    store = load(root)
    target = _main_root(store.nodes) if ref is None else ref
    view = load_view(store, target)
    errors = [issue for issue in view.issues if issue.level == "error"]
    if errors:
        raise BreakdownError(
            f"view {view.ref} is invalid: "
            + "; ".join(issue.message for issue in errors)
        )
    return view


def _sorted_refs(view: View) -> list[str]:
    return sorted(view.nodes, key=lambda r: (view.nodes[r].id, view.nodes[r].version))


def _expected(view: View, path_template: str | None) -> dict[str, str]:
    return _build_paths(
        view, path_template, _sorted_refs(view), reserved=GENERATED_SET
    )


def _link(dest: Path, source: Path) -> None:
    """Point ``dest`` at ``source`` with a relative symlink, replacing anything."""
    target = os.path.relpath(source, dest.parent)
    if dest.is_symlink() or dest.exists():
        if dest.is_dir() and not dest.is_symlink():
            raise ExportError(f"cannot replace directory '{dest}' with a symlink")
        dest.unlink()
    dest.symlink_to(target)


def _classify(dest: Path, source: Path) -> str:
    if dest.is_symlink():
        try:
            return STATUS_OK if dest.resolve() == source.resolve() else STATUS_WRONG_TARGET
        except (OSError, RuntimeError):
            return STATUS_WRONG_TARGET
    if dest.exists():
        if dest.is_file():
            return STATUS_DETACHED
        return STATUS_WRONG_TARGET
    return STATUS_MISSING


def _strays(out: Path, expected: set[str]) -> list[WorkEntry]:
    if not out.is_dir():
        return []
    found: list[WorkEntry] = []
    for path in sorted(out.rglob("*.md")):
        if path.is_symlink() or not path.is_file():
            continue
        rel = path.relative_to(out).as_posix()
        if rel in expected or rel in GENERATED_SET:
            continue
        found.append(WorkEntry(rel, None, STATUS_STRAY))
    return found


def _manifest(out: Path) -> dict[str, str] | None:
    """Read the generated ``REFS.md`` path-to-ref map, if present."""
    refs = out / "REFS.md"
    if not refs.is_file():
        return None
    mapping: dict[str, str] = {}
    for line in refs.read_text(encoding="utf-8").splitlines():
        match = _REF_ROW.match(line.strip())
        if match:
            mapping[match.group("path")] = match.group("ref")
    return mapping or None


def _inspect(view: View, out: Path, path_template: str | None) -> list[WorkEntry]:
    manifest = _manifest(out)
    if manifest is not None:
        entries: list[WorkEntry] = []
        for rel, ref in manifest.items():
            node = view.nodes.get(ref)
            if node is None:
                entries.append(WorkEntry(rel, ref, STATUS_STALE))
                continue
            entries.append(WorkEntry(rel, ref, _classify(out / rel, node.path)))
        entries.extend(_strays(out, set(manifest)))
        return entries
    paths = _expected(view, path_template)
    entries = []
    for ref in _sorted_refs(view):
        rel = paths[ref]
        entries.append(WorkEntry(rel, ref, _classify(out / rel, view.nodes[ref].path)))
    entries.extend(_strays(out, set(paths.values())))
    return entries


def _index_file(view: View, paths: dict[str, str], title_field: str, summary_field: str) -> str:
    return _index_text(
        view,
        paths,
        title_field,
        summary_field,
        banner=BANNER.format(ref=view.ref),
    )


def _refs_text(view: View, paths: dict[str, str], title_field: str) -> str:
    lines = [
        BANNER.format(ref=view.ref),
        "",
        f"# References — view {view.ref}",
        "",
        "| Path | Ref | Title |",
        "| --- | --- | --- |",
    ]
    for ref in _sorted_refs(view):
        node = view.nodes[ref]
        title = str(node.meta.get(title_field) or node.ref)
        title = title.replace("|", "\\|").replace("\n", " ").replace("\r", " ")
        lines.append(f"| `{paths[ref]}` | {ref} | {title} |")
    lines.append("")
    return "\n".join(lines)


def _agents_text(view: View, git: GitContext | None = None) -> str:
    ref = view.ref
    lines = [
        f"# Working set — view `{ref}`",
        "",
        "This work directory is the primary editing interface for the store.",
        "",
        (
            "- Every `.md` file here is a symlink to its node under `nodes/`; "
            "editing it edits the store directly."
        ),
        (
            "- Other work directories may show different views of the same nodes. "
            "An edit here is visible in every view that includes the node."
        ),
        "- Create new nodes with `bd new` or `bd fork`, never by adding files here.",
        "- `INDEX.md`, `AGENTS.md` and `REFS.md` are generated; do not edit them.",
        (
            f"- `bd work {ref} --status` and `bd work {ref} --writeback` are the "
            "repair path if an editor replaces a symlink with a regular file."
        ),
    ]
    if git is not None:
        lines.extend(
            [
                "",
                "Git context:",
                "",
                f"- Git branch: `{git.branch}`",
                f"- Git commit: `{git.commit}`",
                f"- Worktree: `{git.toplevel}`",
            ]
        )
    lines.extend(["", f"Nodes in this view: {len(view.nodes)}.", ""])
    return "\n".join(lines)


def _refresh_guard(view: View, out: Path, path_template: str | None) -> list[WorkEntry]:
    """Inspect before a plain refresh; refuse if manual edits would be lost."""
    if out.exists() and not out.is_dir():
        raise ExportError(f"output '{out}' exists and is not a directory")
    entries = _inspect(view, out, path_template)
    blocking = [
        entry
        for entry in entries
        if entry.status in (STATUS_DETACHED, STATUS_STRAY)
    ]
    if blocking:
        raise ExportError(
            f"refusing to refresh '{out}': {len(blocking)} detached or stray "
            f"file(s); run `bd work {view.ref} --status` to inspect, "
            f"`bd work {view.ref} --writeback` to keep the edits, "
            f"or `bd work {view.ref} --clean` to discard them"
        )
    return entries


def _build(
    view: View,
    out: Path,
    *,
    path_template: str | None,
    title_field: str,
    summary_field: str,
    force: bool,
    clean: bool,
    git: GitContext | None = None,
) -> WorkResult:
    if clean:
        _prepare_out(out, force=True, clean=True)
        entries: list[WorkEntry] = []
    else:
        if force:
            _prepare_out(out, force=True, clean=False)
            entries = _inspect(view, out, path_template)
        else:
            entries = _refresh_guard(view, out, path_template)
            out.mkdir(parents=True, exist_ok=True)
        for entry in entries:
            if entry.status != STATUS_STALE:
                continue
            stale = out / entry.path
            if stale.is_symlink():
                stale.unlink()

    paths = _expected(view, path_template)
    files: list[Path] = []
    for ref in _sorted_refs(view):
        node = view.nodes[ref]
        dest = out / paths[ref]
        dest.parent.mkdir(parents=True, exist_ok=True)
        _link(dest, node.path)

    index_path = out / "INDEX.md"
    index_path.write_text(
        _index_file(view, paths, title_field, summary_field),
        encoding="utf-8",
        newline="",
    )
    refs_path = out / "REFS.md"
    refs_path.write_text(
        _refs_text(view, paths, title_field), encoding="utf-8", newline=""
    )
    agents_path = out / "AGENTS.md"
    agents_path.write_text(_agents_text(view, git), encoding="utf-8", newline="")
    files.extend((index_path, refs_path, agents_path))

    return WorkResult(
        out=out,
        ref=view.ref,
        nodes=len(view.nodes),
        symlinks=len(view.nodes),
        files=files,
        git=git,
    )


def _validate_target(target: Path, nodes_dir: Path) -> None:
    resolved = target.resolve()
    if not resolved.is_relative_to(nodes_dir):
        raise ExportError(f"refusing to write outside {nodes_dir}: '{target}'")
    if resolved.suffix != ".md":
        raise ExportError(f"refusing to write non-markdown file: '{target}'")


def _writeback(view: View, out: Path, path_template: str | None) -> WorkResult:
    nodes_dir = (view.root / "nodes").resolve()
    written = 0
    invalid: list[str] = []
    for entry in _inspect(view, out, path_template):
        if entry.status != STATUS_DETACHED or entry.ref is None:
            continue
        node = view.nodes[entry.ref]
        target = node.path
        _validate_target(target, nodes_dir)
        dest = out / entry.path
        text = dest.read_text(encoding="utf-8")
        try:
            document = parse_document(text)
        except (OSError, FrontMatterError):
            invalid.append(entry.path)
            continue
        declared = document.meta.get("id")
        if declared is not None and str(declared) != str(node.id):
            invalid.append(entry.path)
            continue
        target.write_text(text, encoding="utf-8", newline="")
        _link(dest, target)
        written += 1

    entries = _inspect(view, out, path_template)
    return WorkResult(
        out=out,
        ref=view.ref,
        nodes=len(view.nodes),
        symlinks=sum(1 for entry in entries if entry.status == STATUS_OK),
        entries=entries,
        written=written,
        invalid=invalid,
    )


def work(
    root: str | Path,
    ref: str | int | None = None,
    out: str | Path | None = None,
    *,
    name: str | None = None,
    path_template: str | None = None,
    title_field: str = "title",
    summary_field: str = "summary",
    force: bool = False,
    clean: bool = False,
    status: bool = False,
    writeback: bool = False,
) -> WorkResult:
    """Build, refresh, inspect or write back one view's symlink work tree."""
    if status and writeback:
        raise BreakdownError("--status and --writeback are mutually exclusive")
    if out is not None and name is not None:
        raise BreakdownError("--out and --name are mutually exclusive")
    if name is not None and not _NAME.fullmatch(name):
        raise BreakdownError(
            f"invalid --name {name!r}: use letters, digits, '.', '_' or '-' "
            "and start with a letter or digit"
        )

    view = _resolve_view(root, ref)
    if out is not None:
        out_path = Path(out).resolve()
    else:
        dirname = view.ref if name is None else f"{view.ref}-{name}"
        out_path = (view.root / "build" / "work" / dirname).resolve()

    if status:
        entries = _inspect(view, out_path, path_template)
        return WorkResult(
            out=out_path,
            ref=view.ref,
            nodes=len(view.nodes),
            symlinks=sum(1 for entry in entries if entry.status == STATUS_OK),
            entries=entries,
        )
    if writeback:
        return _writeback(view, out_path, path_template)
    return _build(
        view,
        out_path,
        path_template=path_template,
        title_field=title_field,
        summary_field=summary_field,
        force=force,
        clean=clean,
        git=git_context(view.root),
    )
