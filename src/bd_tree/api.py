"""Public Python API for bd_tree."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .checker import check as _check
from .errors import BreakdownError, ExportError
from .exporter import EXPORTERS
from .freshness import reconcile as _reconcile
from .freshness import stale as _stale
from .frontmatter import body_hash
from .graph import (
    Graph,
    audit,
    build_graph,
    default_anchor,
    export_graph,
    graph_layout,
    graph_view,
    order,
    render_audit,
    render_dot,
    render_graph,
    render_in,
    render_out,
    resolve_graph_ref,
    stage,
)
from .loader import load as _load
from .loader import load_view as _load_view
from .loader import node_path, parse_filename, parse_ref, parse_selector, ref_of
from .model import (
    CheckResult,
    DiffEntry,
    Edge,
    ExportResult,
    Issue,
    Node,
    ReconcileChange,
    StaleEdge,
    Store,
    View,
)
from .navigate import current_ref as _current_ref
from .navigate import default_root as _default_root
from .navigate import resolve_ref as _resolve_ref
from .ops import MigrationResult
from .ops import clear_root as _clear_root
from .ops import clone as _clone
from .ops import contain as _contain
from .ops import delete as _delete
from .ops import diff as _diff
from .ops import init_store as _init_store
from .ops import link as _link
from .ops import migrate as _migrate
from .ops import new_node as _new_node
from .ops import replace as _replace
from .ops import set_root as _set_root
from .ops import uncontain as _uncontain
from .ops import unlink as _unlink
from .ops import versions as _versions
from .solutions import SolutionEntry, SolutionResult
from .solutions import listing as _solution_list
from .solutions import new as _solution_new
from .solutions import remove as _solution_remove
from .work import GitContext, WorkArea, WorkEntry, WorkResult
from .work import area as _area
from .work import edit_path as _edit_path
from .work import work as _work

__all__ = [
    "BreakdownError",
    "CheckResult",
    "DiffEntry",
    "Edge",
    "ExportError",
    "ExportResult",
    "GitContext",
    "Graph",
    "Issue",
    "MigrationResult",
    "Node",
    "ReconcileChange",
    "SolutionEntry",
    "SolutionResult",
    "StaleEdge",
    "Store",
    "View",
    "WorkArea",
    "WorkEntry",
    "WorkResult",
    "area",
    "audit",
    "body_hash",
    "build_graph",
    "check",
    "clear_root",
    "clone",
    "contain",
    "current_ref",
    "default_anchor",
    "default_root",
    "delete",
    "diff",
    "edit_path",
    "export_graph",
    "export_view",
    "graph_layout",
    "graph_view",
    "init_store",
    "link",
    "load",
    "load_view",
    "migrate",
    "new_node",
    "node_path",
    "order",
    "parse_filename",
    "parse_ref",
    "parse_selector",
    "reconcile",
    "ref_of",
    "render_audit",
    "render_dot",
    "render_graph",
    "render_in",
    "render_out",
    "replace",
    "resolve_graph_ref",
    "resolve_ref",
    "root_ref",
    "set_root",
    "solution_list",
    "solution_new",
    "solution_remove",
    "stage",
    "stale",
    "uncontain",
    "unlink",
    "versions",
    "work",
]


def init_store(root: str | Path = ".") -> Path:
    """Create ``.bd_tree/nodes/1-1.md`` in an empty project and return its root."""
    return _init_store(root)


def load(root: str | Path) -> Store:
    """Load the full numeric store at ``root``."""
    return _load(root)


def load_view(root: str | Path | Store, ref: str | int | None = None) -> View:
    """Containment closure rooted at ``ref`` (default: the store root).

    ``ref`` may be a bare selector; it is resolved through the default view.
    """
    store = root if isinstance(root, Store) else _load(root)
    target = None if ref is None else _resolve_ref(store, ref)
    return _load_view(store, target)


def default_root(root: Store | str | Path) -> str:
    """Declared ``ROOT``, else the lowest node by ``(id, version)``."""
    store = root if isinstance(root, Store) else _load(root)
    return _default_root(store)


def current_ref(
    root: Store | str | Path, node_id: int, view_ref: str | None = None
) -> str | None:
    """The ref of ``node_id`` in ``view_ref`` (default: the store view)."""
    store = root if isinstance(root, Store) else _load(root)
    return _current_ref(store, node_id, view_ref)


def resolve_ref(
    root: Store | str | Path, text: str | int, *, view_ref: str | None = None
) -> str:
    """Resolve a bare CLI selector to the ref the chosen view contains."""
    store = root if isinstance(root, Store) else _load(root)
    return _resolve_ref(store, text, view_ref=view_ref)


def check(
    root: str | Path,
    view: str | int | None = None,
    *,
    root_ref: str | int | None = None,
    require: tuple[str, ...] | list[str] = (),
    max_lines: int | None = None,
    max_chars: int | None = None,
) -> CheckResult:
    """Validate the global tree, every view tree, and the selected view."""
    return _check(
        root,
        view,
        root_ref=root_ref,
        require=require,
        max_lines=max_lines,
        max_chars=max_chars,
    )


def export_view(
    name: str, root: str | Path, view: str | int, out: str | Path, **opts: Any
) -> ExportResult:
    """Run a registered exporter (``tree``, ``context`` or ``dot``)."""
    func = EXPORTERS.get(name)
    if func is None:
        raise BreakdownError(
            f"unknown export '{name}' (available: {', '.join(sorted(EXPORTERS))})"
        )
    if name == "graph":
        graph = build_graph(root)
        anchor = resolve_graph_ref(graph, view)
        return func(graph, anchor, Path(out), **opts)
    resolved = _load_view(root, view)
    errors = [issue for issue in resolved.issues if issue.level == "error"]
    if errors:
        raise BreakdownError(
            f"view {resolved.ref} is invalid: "
            + "; ".join(issue.message for issue in errors)
        )
    return func(resolved, Path(out), **opts)


def stale(root: str | Path, view: str | int | None = None) -> list[StaleEdge]:
    """List stale or untracked propagating edges in the view."""
    return _stale(root, view)


def reconcile(
    root: str | Path,
    refs: list[str] | None = None,
    view: str | int | None = None,
    *,
    all_nodes: bool = False,
) -> list[ReconcileChange]:
    """Rewrite stale/untracked pins, preserving key order and body bytes."""
    return _reconcile(root, refs, view, all_nodes=all_nodes)


def versions(root: str | Path, node_id: str | int) -> list[Node]:
    """Every existing file for a logical id, ascending by version."""
    return _versions(root, node_id)


def clone(
    root: str | Path,
    ref: str | int,
    version: int | None = None,
    *,
    subtree: bool = False,
) -> list[tuple[str, str]]:
    """Copy a node, or its containment subtree, to new versions."""
    return _clone(root, ref, version, subtree=subtree)


def replace(
    root: str | Path, old: str | int, new: str | int
) -> tuple[str, str, str]:
    """Swap one contained ref for another, preserving its position."""
    return _replace(root, old, new)


def root_ref(root: str | Path) -> str | None:
    """The store root: declared ``ROOT``, else the lowest node."""
    return _load(root).root_ref


def migrate(root: str | Path, *, dry_run: bool = False) -> MigrationResult:
    """Migrate a classic bare-file store in place (or print the plan)."""
    return _migrate(root, dry_run=dry_run)


def set_root(root: str | Path, ref: str | int) -> Path:
    """Write the store-level ``ROOT`` file."""
    return _set_root(root, ref)


def clear_root(root: str | Path) -> Path | None:
    """Delete the ``ROOT`` file, restoring the lowest-node fallback."""
    return _clear_root(root)


def delete(root: str | Path, ref: str | int, *, force: bool = False) -> Path:
    """Delete one node file, refusing refs still bound into the graph."""
    return _delete(root, ref, force=force)


def diff(root: str | Path, left: str | int, right: str | int) -> list[DiffEntry]:
    """Compare two views id by id."""
    return _diff(root, left, right)


def new_node(
    root: str | Path,
    *,
    parent: str | int,
    fields: dict[str, Any] | None = None,
    body: str = "",
    links: list[dict[str, Any]] | None = None,
) -> Path:
    """Create the next global id at version 1 under ``parent``."""
    return _new_node(
        root,
        parent=parent,
        fields=fields,
        body=body,
        links=links,
    )


def contain(
    root: str | Path,
    parent: str | int,
    child: str | int,
    *,
    before: str | int | None = None,
    after: str | int | None = None,
) -> Path:
    """Add ``child`` to ``parent``'s containment list."""
    return _contain(root, parent, child, before=before, after=after)


def uncontain(root: str | Path, parent: str | int, child: str | int) -> Path:
    """Remove ``child`` from ``parent``'s containment list."""
    return _uncontain(root, parent, child)


def link(
    root: str | Path,
    source: str | int,
    target: str | int,
    *,
    link_type: str,
    propagates: bool = False,
) -> Path:
    """Append a typed link edge, pinning the target when it propagates."""
    return _link(root, source, target, link_type=link_type, propagates=propagates)


def unlink(
    root: str | Path,
    source: str | int,
    target: str | int,
    *,
    link_type: str | None = None,
) -> Path:
    """Remove matching link edges between two refs."""
    return _unlink(root, source, target, link_type=link_type)


def solution_new(
    root: str | Path,
    name: str,
    *,
    path: str | Path | None = None,
    from_ref: str | None = None,
) -> SolutionResult:
    """Create a git worktree for a solution; git owns branch semantics."""
    return _solution_new(root, name, path=path, from_ref=from_ref)


def solution_list(root: str | Path) -> list[SolutionEntry]:
    """List the repository's worktrees with branch, HEAD and store markers."""
    return _solution_list(root)


def solution_remove(
    root: str | Path, target: str, *, force: bool = False
) -> SolutionEntry:
    """Remove one worktree by branch name or path, keeping the branch."""
    return _solution_remove(root, target, force=force)


def area(root: str | Path, out: str | Path | None = None) -> WorkArea:
    """Read the active work area without building or repairing it."""
    return _area(root, out)


def edit_path(
    root: str | Path, ref: str | int, out: str | Path | None = None
) -> Path:
    """Absolute path of ``ref`` inside the active work area."""
    return _edit_path(root, ref, out)


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
    return _work(
        root,
        ref,
        out,
        path_template=path_template,
        title_field=title_field,
        summary_field=summary_field,
        force=force,
        clean=clean,
        status=status,
        writeback=writeback,
        depth=depth,
    )
