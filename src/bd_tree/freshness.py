"""Stale-edge reporting and pin reconciliation inside one view.

Pins live in the top-level ``freshness`` front-matter map, keyed by target
ref; reconciliation rewrites that map and never touches node bodies.
"""

from __future__ import annotations

from pathlib import Path

from .errors import BreakdownError
from .frontmatter import parse_document, rewrite_freshness
from .fsutil import atomic_write, store_lock
from .loader import load, load_view, resolve_store_root
from .model import Edge, Node, ReconcileChange, StaleEdge, View
from .navigate import resolve_ref


def edge_state(view: View, edge: Edge) -> str | None:
    """Return ``stale``/``untracked`` for a propagating edge, else ``None``."""
    if not edge.propagating:
        return None
    target = view.nodes.get(edge.target)
    if target is None:
        return None
    if edge.pinned is None:
        return "untracked"
    if edge.pinned != target.body_hash:
        return "stale"
    return None


def stale_edge_list(view: View) -> list[StaleEdge]:
    result: list[StaleEdge] = []
    for edge in view.edges:
        state = edge_state(view, edge)
        if state is None:
            continue
        target = view.nodes[edge.target]
        result.append(
            StaleEdge(
                source=edge.source,
                target=edge.target,
                type=edge.type,
                state=state,
                pinned=edge.pinned,
                current=target.body_hash,
            )
        )
    return result


def stale(root: str | Path, view: str | int | None = None) -> list[StaleEdge]:
    """List propagating edges whose pin is missing or out of date."""
    store = load(root)
    target = None if view is None else resolve_ref(store, view)
    return stale_edge_list(load_view(store, target))


def _reconcile_node(view: View, node: Node) -> list[ReconcileChange]:
    """Re-pin every stale/untracked propagating edge in the freshness map."""
    changes: list[ReconcileChange] = []
    freshness: dict[str, dict] = {}
    for link in node.links:
        entry: dict = {}
        if link.pinned is not None:
            entry["pinned"] = link.pinned
        if link.propagates:
            entry["propagates"] = True
        target = view.nodes.get(link.to)
        state = None
        if link.propagating and target is not None:
            if link.pinned is None:
                state = "untracked"
            elif link.pinned != target.body_hash:
                state = "stale"
        if state is not None:
            entry["pinned"] = target.body_hash
            if link.propagates:
                entry["propagates"] = True
            changes.append(
                ReconcileChange(
                    node=node.ref,
                    path=node.path,
                    target=link.to,
                    type=link.type,
                    old=link.pinned,
                    new=target.body_hash,
                )
            )
        if entry:
            freshness[link.to] = entry
    if not changes:
        return []
    doc = parse_document(node.path.read_text(encoding="utf-8"))
    atomic_write(node.path, doc.with_raw_fm(rewrite_freshness(doc.raw_fm, freshness)))
    return changes


def reconcile(
    root: str | Path,
    refs: list[str] | None = None,
    view: str | int | None = None,
    *,
    all_nodes: bool = False,
) -> list[ReconcileChange]:
    """Rewrite stale/untracked propagating pins, preserving body bytes."""
    root = resolve_store_root(root)
    with store_lock(root):
        store = load(root)
        target_ref = None if view is None else resolve_ref(store, view)
        resolved = load_view(store, target_ref)
        if all_nodes:
            targets = sorted(resolved.nodes)
        else:
            targets = []
            for ref in dict.fromkeys(refs or []):
                try:
                    canonical = resolve_ref(store, ref, view_ref=resolved.ref)
                except BreakdownError as exc:
                    raise BreakdownError(str(exc)) from None
                targets.append(canonical)
        if not all_nodes and not targets:
            raise BreakdownError("reconcile needs at least one ref or --all")
        missing = [ref for ref in targets if ref not in resolved.nodes]
        if missing:
            raise BreakdownError("ref(s) outside view: " + ", ".join(missing))
        changes: list[ReconcileChange] = []
        for ref in targets:
            changes.extend(_reconcile_node(resolved, resolved.nodes[ref]))
        return changes
