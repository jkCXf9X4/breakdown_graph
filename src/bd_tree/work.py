"""Materialize one containment view as a tree of per-file symlinks.

The work directory is the primary editing interface: it mirrors the templated
paths of ``bd view``, but every node ``.md`` entry is a symlink back to its
original ``nodes/<ref>.md`` file.  Editing a file in the work tree therefore
edits the store directly: there is no sync layer, no state file and no copied
content.

There is one fixed work area per project, ``<project>/bd_work``.  Building a
different view replaces its contents, so a single area always shows exactly one
view.  The API's ``out`` parameter is a programmatic override for tests and
embedders; the CLI exposes only the one area.

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
from .fsutil import atomic_write, store_lock
from .loader import load, load_view
from .model import View
from .navigate import resolve_ref

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

_VIEW_IN_REFS = re.compile(
    r"^#\s*References\b.*\bview\s+(\d+(?:-\d+)?)(?:\+(\d+))?\s*$"
)
_VIEW_IN_INDEX = re.compile(r"^#\s*View\s+(\d+(?:-\d+)?)(?:\+(\d+))?\s*$")

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
class WorkArea:
    """The project work area and the view its generated headers declare."""

    out: Path
    ref: str | None
    depth: int | None = None

    @property
    def view_ref(self) -> str | None:
        if self.ref is None:
            return None
        return self.ref if self.depth is None else f"{self.ref}+{self.depth}"


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
    depth: int | None = None

    @property
    def ok(self) -> bool:
        return all(entry.status == STATUS_OK for entry in self.entries)

    @property
    def view_ref(self) -> str:
        return self.ref if self.depth is None else f"{self.ref}+{self.depth}"


def _resolve_view(root: str | Path, ref: str | int | None) -> View:
    store = load(root)
    if ref is None:
        target = store.root_ref
        if target is None:
            raise BreakdownError("store has no nodes")
    else:
        target = resolve_ref(store, ref)
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


def _depth_label(ref: str, depth: int | None) -> str:
    """The materialized expression: ``REF`` for a full closure, else ``REF+N``."""
    return ref if depth is None else f"{ref}+{depth}"


def _depth_view(view: View, depth: int | None) -> View:
    """Return ``view`` filtered to nodes within ``depth`` levels of its root.

    ``view`` is already the containment closure, so this is a prefix of that
    closure along ``effective_contains``.  ``None`` keeps the full closure.
    """
    if depth is None:
        return view
    kept: set[str] = set()
    seen: set[str] = set()

    def walk(ref: str, level: int) -> None:
        if ref in seen or ref not in view.nodes:
            return
        seen.add(ref)
        kept.add(ref)
        if level >= depth:
            return
        for child in view.store.effective_contains(ref):
            walk(child, level + 1)

    walk(view.ref, 0)
    nodes = {ref: node for ref, node in view.nodes.items() if ref in kept}
    edges = [
        edge for edge in view.edges if edge.source in kept and edge.target in kept
    ]
    return View(
        store=view.store,
        ref=view.ref,
        nodes=nodes,
        edges=edges,
        issues=view.issues,
    )


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


def _view_header(
    path: Path, pattern: re.Pattern[str]
) -> tuple[str, int | None] | None:
    """The view ref and optional materialized depth a header declares."""
    if not path.is_file():
        return None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    for line in lines:
        match = pattern.match(line.strip())
        if match:
            depth = int(match.group(2)) if match.group(2) is not None else None
            return match.group(1), depth
    return None


def area(root: str | Path, out: str | Path | None = None) -> WorkArea:
    """Return the work area and the view its own headers declare.

    Reads ``REFS.md`` first and falls back to ``INDEX.md``.  Never writes and
    never raises for an absent area or a missing header: ``ref`` is ``None``
    and the caller decides whether that is an error.
    """
    if out is None:
        out_path = (load(root).project_root / "bd_work").resolve()
    else:
        out_path = Path(out).resolve()
    ref: str | None = None
    depth: int | None = None
    if out_path.is_dir():
        for header, pattern in (
            (out_path / "REFS.md", _VIEW_IN_REFS),
            (out_path / "INDEX.md", _VIEW_IN_INDEX),
        ):
            parsed = _view_header(header, pattern)
            if parsed is not None:
                ref, depth = parsed
                break
    return WorkArea(out=out_path, ref=ref, depth=depth)


def _current_area(root: str | Path, out: str | Path | None = None) -> WorkArea:
    current = area(root, out)
    if not current.out.is_dir() or current.ref is None:
        raise ExportError(
            f"no work area with a readable view at '{current.out}'; "
            "run `bd work REF` first"
        )
    return current


def _node_link_strays(
    view: View, out: Path, known: set[str]
) -> list[WorkEntry]:
    """Unexpected symlinks into the store: leftovers from another view.

    Without ``REFS.md`` there is no manifest to classify them, so a link whose
    target lives under the store's ``nodes/`` and is not expected here is a
    stale view link and can be removed on rebuild.
    """
    if not out.is_dir():
        return []
    nodes_dir = (view.root / "nodes").resolve()
    found: list[WorkEntry] = []
    for path in sorted(out.rglob("*")):
        if not path.is_symlink():
            continue
        rel = path.relative_to(out).as_posix()
        if rel in known or rel in GENERATED_SET:
            continue
        try:
            target = path.resolve()
        except (OSError, RuntimeError):
            continue
        if target.is_relative_to(nodes_dir):
            found.append(WorkEntry(rel, None, STATUS_STALE))
    return found


def _inspect(view: View, out: Path, path_template: str | None) -> list[WorkEntry]:
    manifest = _manifest(out)
    if manifest is not None:
        entries: list[WorkEntry] = []
        for rel, ref in manifest.items():
            node = view.nodes.get(ref)
            dest = out / rel
            if node is None:
                # Left over from another view.  A symlink is disposable; a
                # regular file may hold detached edits and must block a switch.
                status = STATUS_STALE if dest.is_symlink() else STATUS_DETACHED
                if not dest.exists() and not dest.is_symlink():
                    status = STATUS_STALE
                entries.append(WorkEntry(rel, ref, status))
                continue
            entries.append(WorkEntry(rel, ref, _classify(dest, node.path)))
        entries.extend(_strays(out, set(manifest)))
        entries.extend(_node_link_strays(view, out, set(manifest)))
        return entries
    paths = _expected(view, path_template)
    entries = []
    for ref in _sorted_refs(view):
        rel = paths[ref]
        entries.append(WorkEntry(rel, ref, _classify(out / rel, view.nodes[ref].path)))
    entries.extend(_strays(out, set(paths.values())))
    entries.extend(_node_link_strays(view, out, set(paths.values())))
    return entries


def _index_file(
    view: View,
    paths: dict[str, str],
    title_field: str,
    summary_field: str,
    label: str,
) -> str:
    return _index_text(
        view,
        paths,
        title_field,
        summary_field,
        banner=BANNER.format(ref=label),
        label=label,
    )


def _refs_text(
    view: View, paths: dict[str, str], title_field: str, label: str
) -> str:
    lines = [
        BANNER.format(ref=label),
        "",
        f"# References — view {label}",
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


def _agents_text(
    view: View,
    label: str,
    git: GitContext | None = None,
    depth: int | None = None,
) -> str:
    ref = label
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
            "- This is the single writable work area. `bd work REF` replaces "
            "its contents when the view changes."
        ),
        (
            "- Create nodes with `bd new` and branch a node with `bd clone`, "
            "never by adding files here."
        ),
        "- `INDEX.md`, `AGENTS.md` and `REFS.md` are generated; do not edit them.",
        (
            f"- `bd work {ref} --status` and `bd work {ref} --writeback` are the "
            "repair path if an editor replaces a symlink with a regular file."
        ),
    ]
    if depth is not None:
        lines.append(
            f"- This area materializes only the first {depth} descendant levels "
            f"of view `{view.ref}`; run `bd work {view.ref}` for the full closure."
        )
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
            f"file(s); run `bd work {view.ref} --writeback` first to keep the "
            f"edits, or `bd work {view.ref} --clean` to discard them. "
            f"Run `bd work {view.ref} --status` to inspect."
        )
    return entries


def _prune_empty_dirs(out: Path) -> None:
    """Remove directories under ``out`` that the previous view left empty."""
    if not out.is_dir():
        return
    for path in sorted(out.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if path.is_dir() and not path.is_symlink() and not any(path.iterdir()):
            path.rmdir()


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
    depth: int | None = None,
) -> WorkResult:
    label = _depth_label(view.ref, depth)
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
        _prune_empty_dirs(out)

    paths = _expected(view, path_template)
    known = set(paths.values())
    for leftover in _node_link_strays(view, out, known):
        link = out / leftover.path
        if link.is_symlink():
            link.unlink()
    _prune_empty_dirs(out)
    files: list[Path] = []
    for ref in _sorted_refs(view):
        node = view.nodes[ref]
        dest = out / paths[ref]
        dest.parent.mkdir(parents=True, exist_ok=True)
        _link(dest, node.path)

    index_path = out / "INDEX.md"
    index_path.write_text(
        _index_file(view, paths, title_field, summary_field, label),
        encoding="utf-8",
        newline="",
    )
    refs_path = out / "REFS.md"
    refs_path.write_text(
        _refs_text(view, paths, title_field, label), encoding="utf-8", newline=""
    )
    agents_path = out / "AGENTS.md"
    agents_path.write_text(
        _agents_text(view, label, git, depth), encoding="utf-8", newline=""
    )
    files.extend((index_path, refs_path, agents_path))

    return WorkResult(
        out=out,
        ref=view.ref,
        nodes=len(view.nodes),
        symlinks=len(view.nodes),
        files=files,
        git=git,
        depth=depth,
    )


def _validate_target(target: Path, nodes_dir: Path) -> None:
    resolved = target.resolve()
    if not resolved.is_relative_to(nodes_dir):
        raise ExportError(f"refusing to write outside {nodes_dir}: '{target}'")
    if resolved.suffix != ".md":
        raise ExportError(f"refusing to write non-markdown file: '{target}'")


def _writeback(
    view: View,
    out: Path,
    path_template: str | None,
    *,
    depth: int | None = None,
) -> WorkResult:
    nodes_dir = (view.root / "nodes").resolve()
    written = 0
    invalid: list[str] = []
    with store_lock(view.root):
        for entry in _inspect(view, out, path_template):
            if entry.status != STATUS_DETACHED or entry.ref is None:
                continue
            # A detached file may belong to the view that was replaced.  Resolve
            # it against the whole store so `--writeback` can still preserve edits.
            node = view.nodes.get(entry.ref) or view.store.nodes.get(entry.ref)
            if node is None:
                continue
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
            atomic_write(target, text)
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
        depth=depth,
    )


def edit_path(
    root: str | Path, ref: str | int, out: str | Path | None = None
) -> Path:
    """Absolute path of ``ref`` in the area's current view.

    Read-only: a missing expected link still yields its path, never a build.
    """
    current = _current_area(root, out)
    view = _depth_view(_resolve_view(root, current.ref), current.depth)
    wanted = resolve_ref(view.store, ref, view_ref=current.ref)
    if wanted not in view.nodes:
        raise ExportError(
            f"ref {wanted} is not in current view {current.view_ref}; "
            "run `bd views` to list views or `bd work REF` to switch"
        )
    manifest = _manifest(current.out)
    if manifest is not None:
        for rel, mapped in manifest.items():
            if mapped == wanted:
                return current.out / rel
    return current.out / _expected(view, None)[wanted]


def work(
    root: str | Path,
    ref: str | int | None = None,
    out: str | Path | None = None,
    *,
    path_template: str | None = None,
    title_field: str = "title",
    summary_field: str = "summary",
    force: bool = False,
    clean: bool = False,
    status: bool = False,
    writeback: bool = False,
    depth: int | None = None,
) -> WorkResult:
    """Build, refresh, inspect or write back the single view work area."""
    if status and writeback:
        raise BreakdownError("--status and --writeback are mutually exclusive")

    if status or writeback:
        current = _current_area(root, out)
        view = _depth_view(_resolve_view(root, current.ref), current.depth)
        depth = current.depth
        out_path = current.out
    else:
        view = _depth_view(_resolve_view(root, ref), depth)
        if out is not None:
            out_path = Path(out).resolve()
        else:
            out_path = (view.store.project_root / "bd_work").resolve()

    if status:
        entries = _inspect(view, out_path, path_template)
        return WorkResult(
            out=out_path,
            ref=view.ref,
            nodes=len(view.nodes),
            symlinks=sum(1 for entry in entries if entry.status == STATUS_OK),
            entries=entries,
            depth=depth,
        )
    if writeback:
        return _writeback(view, out_path, path_template, depth=depth)
    return _build(
        view,
        out_path,
        path_template=path_template,
        title_field=title_field,
        summary_field=summary_field,
        force=force,
        clean=clean,
        git=git_context(view.root),
        depth=depth,
    )
