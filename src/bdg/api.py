"""Public Python API for bdg."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .checker import check as _check
from .errors import BreakdownError, ExportError
from .exporter import export_context as _export_context
from .freshness import reconcile as _reconcile
from .freshness import stale as _stale
from .frontmatter import body_hash
from .graph import (
    Graph,
    audit,
    build_graph,
    default_anchor,
    export_graph,
    graph_view,
    render_audit,
    render_dot,
    render_graph,
    render_in,
    render_out,
    resolve_graph_ref,
    ring_distances,
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
from .ops import MigrationResult, RetitleResult
from .ops import clear_root as _clear_root
from .ops import clone as _clone
from .ops import delete as _delete
from .ops import diff as _diff
from .ops import init_store as _init_store
from .ops import link as _link
from .ops import migrate as _migrate
from .ops import new_node as _new_node
from .ops import replace as _replace
from .ops import retitle as _retitle
from .ops import set_root as _set_root
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
    "RetitleResult",
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
    "current_ref",
    "default_anchor",
    "default_root",
    "delete",
    "diff",
    "edit_path",
    "export_graph",
    "graph_view",
    "init_store",
    "link",
    "load",
    "load_view",
    "migrate",
    "new_node",
    "node_path",
    "pack",
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
    "retitle",
    "ring_distances",
    "root_ref",
    "set_root",
    "solution_list",
    "solution_new",
    "solution_remove",
    "stale",
    "unlink",
    "versions",
    "work",
]


def init_store(root: str | Path = ".") -> Path:
    """Create a graph root in an empty project; return its root."""
    return _init_store(root)


def load(root: str | Path) -> Store:
    """Load the full numeric store at ``root``."""
    return _load(root)


def load_view(root: str | Path | Store, ref: str | int | None = None) -> View:
    """Link closure rooted at ``ref`` (default: the store anchor).

    ``ref`` may be a bare selector; it is resolved through the default view.
    """
    store = root if isinstance(root, Store) else _load(root)
    target = None if ref is None else _resolve_ref(store, ref)
    return _load_view(store, target)


def default_root(root: Store | str | Path) -> str:
    """Declared ``ROOT``, else the lowest component representative, else the lowest node."""
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
    """Validate the store, its edges, and the selected view."""
    return _check(
        root,
        view,
        root_ref=root_ref,
        require=require,
        max_lines=max_lines,
        max_chars=max_chars,
    )


def pack(
    root: str | Path,
    view: str | int,
    out: str | Path,
    *,
    fresh: bool = False,
    force: bool = False,
    clean: bool = False,
    path_template: str | None = None,
    title_field: str = "title",
    summary_field: str = "summary",
) -> ExportResult:
    """Materialize one view into a directory.

    Default: every node plus ``INDEX.md``, ordered by distance ring.
    ``fresh=True``: only fresh nodes, plus ``AGENTS.md`` and ``STALE.md``.
    """
    if fresh:
        resolved = _load_view(root, view)
        errors = [issue for issue in resolved.issues if issue.level == "error"]
        if errors:
            raise BreakdownError(
                f"view {resolved.ref} is invalid: "
                + "; ".join(issue.message for issue in errors)
            )
        return _export_context(
            resolved,
            Path(out),
            path_template=path_template,
            title_field=title_field,
            summary_field=summary_field,
            force=force,
            clean=clean,
        )
    built = build_graph(root)
    anchor = resolve_graph_ref(built, view)
    return export_graph(
        built,
        anchor,
        Path(out),
        path_template=path_template,
        force=force,
        clean=clean,
    )


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
    depth: int | None = None,
) -> list[tuple[str, str]]:
    """Copy a node, or its undirected neighbourhood, to new versions."""
    return _clone(root, ref, version, subtree=subtree, depth=depth)


def replace(
    root: str | Path, old: str | int, new: str | int
) -> tuple[str, str, str]:
    """Repoint every inbound link from ``old`` to ``new``."""
    return _replace(root, old, new)


def root_ref(root: str | Path) -> str | None:
    """The store root: declared ``ROOT``, else the lowest node."""
    return _load(root).root_ref


def migrate(
    root: str | Path,
    *,
    dry_run: bool = False,
    link_type: str = "breaks_down",
) -> MigrationResult:
    """Convert a legacy store in place (or print the plan).

    Retired placement keys are stripped from every node and ROOT; front-matter
    links move into node bodies as ref-first prefix-form token lines.  Tokens
    are normalized to ``(TITLE)[[REF, TYPE]]``, retired suffix tokens in
    either component order are rewritten, and missing titles are filled from
    the target.  Idempotent, so re-running the same migration is a no-op.
    """
    return _migrate(root, dry_run=dry_run, link_type=link_type)


def retitle(
    root: str | Path,
    *,
    view: str | int | None = None,
    dry_run: bool = False,
) -> RetitleResult:
    """Regenerate cached token titles from their targets' live titles.

    The whole store is the default scope; ``view`` narrows it to one
    undirected component.  Tokens whose target is unresolved are untouched.
    """
    return _retitle(root, view=view, dry_run=dry_run)


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
    parent: str | int | None = None,
    fields: dict[str, Any] | None = None,
    body: str = "",
    link_type: str = "breaks_down",
) -> Path:
    """Create the next global id at version 1, optionally linked to ``parent``."""
    return _new_node(
        root,
        parent=parent,
        fields=fields,
        body=body,
        link_type=link_type,
    )


def link(
    root: str | Path,
    source: str | int,
    target: str | int,
    *,
    link_type: str,
    propagates: bool = False,
    pinned: str | None = None,
) -> Path:
    """Append a typed edge token to the FROM node's ``## Links`` section.

    ``propagates`` and/or ``pinned`` are recorded in the FROM node's
    ``freshness`` front-matter map, keyed by the target ref.
    """
    return _link(
        root,
        source,
        target,
        link_type=link_type,
        propagates=propagates,
        pinned=pinned,
    )


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
