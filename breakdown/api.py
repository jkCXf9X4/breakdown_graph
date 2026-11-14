"""Public Python API for the breakdown tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .checker import check as _check
from .errors import BreakdownError, ExportError
from .exporter import EXPORTERS
from .freshness import reconcile as _reconcile
from .freshness import stale as _stale
from .frontmatter import body_hash
from .loader import load as _load
from .loader import load_view as _load_view
from .loader import node_path, parse_filename, parse_ref, ref_of
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
from .ops import diff as _diff
from .ops import fork as _fork
from .ops import new_node as _new_node
from .ops import promote as _promote
from .ops import retire_version as _retire_version
from .ops import versions as _versions

__all__ = [
    "load",
    "load_view",
    "check",
    "export_view",
    "stale",
    "reconcile",
    "versions",
    "fork",
    "promote",
    "retire_version",
    "diff",
    "new_node",
    "parse_ref",
    "parse_filename",
    "ref_of",
    "node_path",
    "body_hash",
    "Store",
    "View",
    "Node",
    "Edge",
    "Issue",
    "CheckResult",
    "DiffEntry",
    "ExportResult",
    "ReconcileChange",
    "StaleEdge",
    "BreakdownError",
    "ExportError",
]


def load(root: str | Path) -> Store:
    """Load the full numeric store at ``root``."""
    return _load(root)


def load_view(root: str | Path | Store, ref: str | int = "1") -> View:
    """Containment closure rooted at ``ref`` (default ``1``)."""
    return _load_view(root, ref)


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
    resolved = _load_view(root, view)
    errors = [issue for issue in resolved.issues if issue.level == "error"]
    if errors:
        raise BreakdownError(
            f"view {resolved.ref} is invalid: "
            + "; ".join(issue.message for issue in errors)
        )
    return func(resolved, Path(out), **opts)


def stale(root: str | Path, view: str | int = "1") -> list[StaleEdge]:
    """List stale or untracked propagating edges in the view."""
    return _stale(root, view)


def reconcile(
    root: str | Path,
    refs: list[str] | None = None,
    view: str | int = "1",
    *,
    all_nodes: bool = False,
) -> list[ReconcileChange]:
    """Rewrite stale/untracked pins, preserving key order and body bytes."""
    return _reconcile(root, refs, view, all_nodes=all_nodes)


def versions(root: str | Path, node_id: str | int) -> list[Node]:
    """Every existing file for a logical id, main first."""
    return _versions(root, node_id)


def fork(
    root: str | Path, node_id: str | int, version: int | None = None
) -> Path:
    """Copy the main file to a version file."""
    return _fork(root, node_id, version)


def promote(root: str | Path, ref: str | int, *, keep: bool = False) -> Path:
    """Copy a version's content onto the main file."""
    return _promote(root, ref, keep=keep)


def retire_version(root: str | Path, ref: str | int) -> Path:
    """Delete a non-main version file."""
    return _retire_version(root, ref)


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
    """Create the next global id as a main file under ``parent``."""
    return _new_node(
        root,
        parent=parent,
        fields=fields,
        body=body,
        links=links,
    )
