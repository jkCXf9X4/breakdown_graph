"""Read-only navigation over the undirected view: show, find and path.

Everything here is a pure projection of an already loaded :class:`~.model.Store`.
Neighbours are the authored links in both directions; the anchor is a focus, not
a filter.  Every walk is a breadth-first search with a seen-set, so cycles are
ordinary and a node appears once.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from .errors import BreakdownError
from .loader import load_view, parse_selector
from .model import KIND_RANK, Node, Store

# Direction labels for one step out of a node.
ARROW: dict[str, str] = {"child": "→", "parent": "←"}
_KIND_BY_RANK: dict[int, str] = {rank: kind for kind, rank in KIND_RANK.items()}
_INVERSE_KIND: dict[str, str] = {
    "child": "parent",
    "parent": "child",
}

# Front-matter keys that drive the model or are displayed separately.
RESERVED: frozenset[str] = frozenset(
    {"id", "legacy", "links", "freshness", "title", "summary"}
)

MAX_FIND_LINES = 3
FIND_LINE_CHARS = 160


class NavigationError(BreakdownError):
    """A navigation request that cannot be served (bad ref, depth or pattern)."""


@dataclass(frozen=True)
class RefDepth:
    """``REF`` with an optional ``+DEPTH`` suffix."""

    ref: str
    depth: int | None


def parse_ref_depth(text: str, override: int | None = None) -> RefDepth:
    """Split ``5-1+2`` on the last ``+``; ``override`` wins over the suffix.

    The ref part may be a bare selector; :func:`resolve_ref` turns it into a
    full ref once the view is known.
    """
    ref_text = str(text).strip()
    depth: int | None = None
    if "+" in ref_text:
        ref_text, _, suffix = ref_text.rpartition("+")
        if not suffix.isdigit():
            raise NavigationError(
                f"invalid depth in {text!r} (expected REF+N with N a non-negative int)"
            )
        depth = int(suffix)
    if not ref_text:
        raise NavigationError(f"invalid ref {text!r}")
    try:
        parse_selector(ref_text)
    except ValueError as exc:
        raise NavigationError(f"invalid ref {text!r}") from exc
    if override is not None:
        depth = override
    if depth is not None and depth < 0:
        raise NavigationError(f"invalid depth {depth} (must be non-negative)")
    return RefDepth(ref_text, depth)


def default_root(store: Store) -> str:
    """Declared ``ROOT``, else the first component representative."""
    ref = store.root_ref
    if ref is None:
        raise NavigationError("store has no nodes")
    return ref


def current_ref(store: Store, node_id: int, view_ref: str | None = None) -> str | None:
    """The ref of ``node_id`` in ``view_ref`` (default: the store view)."""
    view = load_view(store, view_ref if view_ref is not None else default_root(store))
    return view.current_ref(node_id)


def resolve_ref(
    store: Store, text: str | int, *, view_ref: str | None = None
) -> str:
    """Resolve a CLI selector to a full ref.

    A full ref is returned unchanged and is never re-resolved.  A bare id is
    looked up in ``view_ref`` (default: the store's default view); failure
    raises :class:`NavigationError` naming the id and the view searched.
    """
    raw = str(text).strip()
    try:
        node_id, version = parse_selector(raw)
    except ValueError as exc:
        raise NavigationError(f"invalid ref {text!r}") from exc
    if version is not None:
        return f"{node_id}-{version}"
    view = view_ref if view_ref is not None else default_root(store)
    resolved = current_ref(store, node_id, view)
    if resolved is None:
        raise NavigationError(f"id {node_id} is not in view {view}")
    return resolved


def get_node(store: Store, ref: str) -> Node:
    node = store.nodes.get(ref)
    if node is None:
        raise NavigationError(f"unknown ref '{ref}'")
    return node


def view_roots(store: Store) -> list[Node]:
    """One representative per weak component, sorted by ``(id, version)``."""
    return store.topology_roots()


def shortest_path(
    store: Store, start: str, target: str
) -> list[tuple[str, str]] | None:
    """Shortest undirected path from ``start`` to ``target``.

    Returns ``[(ref, arrow_into_ref), ...]`` starting with ``(start, "")`` in
    which each later arrow is the direction of that step (``→`` child, ``←``
    parent).  ``None`` means the two refs are in different components.
    """
    if start not in store.nodes or target not in store.nodes:
        return None
    if start == target:
        return [(start, "")]
    previous: dict[str, tuple[str, str]] = {}
    seen = {start}
    queue = [start]
    while queue:
        current = queue.pop(0)
        for neighbor in store.neighbors(current):
            if neighbor.ref in seen or neighbor.ref not in store.nodes:
                continue
            seen.add(neighbor.ref)
            previous[neighbor.ref] = (current, ARROW.get(neighbor.kind, "→"))
            if neighbor.ref == target:
                path: list[tuple[str, str]] = []
                cursor = target
                while cursor != start:
                    parent, arrow = previous[cursor]
                    path.append((cursor, arrow))
                    cursor = parent
                path.append((start, ""))
                path.reverse()
                return path
            queue.append(neighbor.ref)
    return None


def _path_text(store: Store, start: str, target: str) -> str:
    """Ref chain for display; the target alone when no path exists."""
    path = shortest_path(store, start, target)
    if path is None:
        return target
    return " > ".join(ref for ref, _arrow in path)


def _breadcrumb(store: Store, ref: str) -> str:
    path = shortest_path(store, default_root(store), ref)
    if path is None:
        return ref
    parts = []
    for current, arrow in path:
        node = store.nodes.get(current)
        label = f"{current} {node.title}".rstrip() if node else current
        parts.append(f"{arrow} {label}".strip())
    return " > ".join(parts)


def walk_neighbors(
    store: Store, ref: str, depth: int | None
) -> Iterator[tuple[Node, int, str]]:
    """BFS ``(node, distance, arrow)`` pairs over undirected neighbours.

    Rings are emitted in order 0..``depth`` (``None`` = the whole component) and
    each node once.  Inside a ring the order is ``(kind_rank, link.type, id,
    version)``; the arrow labels the best arriving step from the previous ring,
    or is empty for the anchor.
    """
    get_node(store, ref)
    distance: dict[str, int] = {ref: 0}
    queue = [ref]
    while queue:
        current = queue.pop(0)
        if depth is not None and distance[current] >= depth:
            continue
        for neighbor in store.neighbors(current):
            if neighbor.ref in distance or neighbor.ref not in store.nodes:
                continue
            distance[neighbor.ref] = distance[current] + 1
            queue.append(neighbor.ref)

    entries: list[tuple[int, int, str, int, int, str, str]] = []
    for current, hops in distance.items():
        node = store.nodes[current]
        if hops == 0:
            entries.append((0, -1, "", node.id, node.version, current, ""))
            continue
        best: tuple[int, str] | None = None
        for neighbor in store.neighbors(current):
            if distance.get(neighbor.ref) != hops - 1:
                continue
            # The neighbour entry is its view of ``current``; invert it to
            # label the step from the previous ring into ``current``.
            arrival = _INVERSE_KIND[neighbor.kind]
            key = (KIND_RANK[arrival], neighbor.link.type)
            if best is None or key < best:
                best = key
        assert best is not None
        entries.append(
            (hops, best[0], best[1], node.id, node.version, current,
             _KIND_BY_RANK[best[0]])
        )
    entries.sort(key=lambda entry: entry[:5])
    for hops, _rank, _type, _node_id, _version, current, kind in entries:
        yield store.nodes[current], hops, ARROW.get(kind, "")


def format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ", ".join(format_value(item) for item in value)
    if isinstance(value, dict):
        return ", ".join(f"{key}={format_value(item)}" for key, item in value.items())
    return str(value)


def header_fields(node: Node, fields: Iterable[str] | None) -> list[tuple[str, str]]:
    keys = list(fields) if fields else [
        key for key in node.meta if key not in RESERVED
    ]
    return [
        (key, format_value(node.meta.get(key)))
        for key in keys
        if key in node.meta
    ]


def _display_body(node: Node, max_chars: int) -> str:
    body = node.body.strip("\n")
    lines = body.splitlines()
    if lines and lines[0].lstrip().startswith("# "):
        heading = lines[0].lstrip()[2:].strip()
        if heading.casefold() == node.title.casefold():
            body = "\n".join(lines[1:]).lstrip("\n")
    if max_chars > 0 and len(body) > max_chars:
        cut = body[:max_chars]
        space = cut.rfind(" ")
        if space > max_chars * 0.6:
            cut = cut[:space]
        body = cut.rstrip() + f" ... [truncated; bdg show {node.ref}]"
    return body


def _graph_link_footer(store: Store, printed: Iterable[str]) -> str:
    """Undirected neighbour rows for every printed node.

    Direction is a label on the row: ``→`` child, ``←`` parent.  In-edges
    arrive from other nodes' authored tokens.
    """
    rows: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for ref in printed:
        if ref not in store.nodes:
            continue
        for neighbor in store.neighbors(ref):
            key = (ref, neighbor.ref, neighbor.link.type)
            if key in seen:
                continue
            seen.add(key)
            target = store.nodes.get(neighbor.ref)
            title = target.title if target is not None else "(missing)"
            arrow = ARROW.get(neighbor.kind, "→")
            rows.append(
                f"- {ref} {arrow} {neighbor.ref}  {title}  "
                f"({neighbor.link.type})"
            )
    if not rows:
        return ""
    return "links:\n" + "\n".join(rows)


def render_show(
    store: Store,
    ref: str,
    *,
    depth: int = 0,
    fields: Iterable[str] | None = None,
    no_body: bool = False,
    max_chars: int | None = None,
    show_path: bool = False,
    links: bool = False,
) -> str:
    blocks: list[str] = []
    get_node(store, ref)
    cap = max_chars
    if cap is None:
        cap = 0 if depth == 0 else 4000
    if show_path:
        blocks.append(f"path: {_breadcrumb(store, ref)}")
    printed: list[str] = []
    for node, level, arrow in walk_neighbors(store, ref, depth):
        printed.append(node.ref)
        heading = "#" * min(level + 1, 6)
        parts = [f"{heading} {node.ref}  {node.title}"]
        if arrow:
            parts[0] = f"{parts[0]}  {arrow}"
        if node.summary:
            parts.append(f"summary: {node.summary}")
        for key, value in header_fields(node, fields):
            parts.append(f"{key}: {value}")
        if not no_body:
            body = _display_body(node, cap)
            if body:
                parts.append(body)
        blocks.append("\n".join(parts))
    if links:
        footer = _graph_link_footer(store, printed)
        if footer:
            blocks.append(footer)
    return "\n\n".join(blocks)


def _field_values(node: Node, field: str | None) -> list[str]:
    if field == "body":
        return node.body.splitlines()
    if field == "title":
        return [node.title]
    if field == "summary":
        return [node.summary] if node.summary else []
    if field is not None:
        value = node.meta.get(field)
        return [value] if isinstance(value, str) else []
    values = [node.title]
    if node.summary:
        values.append(node.summary)
    values.extend(
        value for value in node.meta.values() if isinstance(value, str)
    )
    values.extend(node.body.splitlines())
    return values


def _matches(text: str, query: str, pattern: re.Pattern[str] | None) -> bool:
    if pattern is not None:
        return pattern.search(text) is not None
    return query.lower() in text.lower()


def _compile(query: str, regex: bool) -> re.Pattern[str] | None:
    if not regex:
        return None
    try:
        return re.compile(query)
    except re.error as exc:
        raise NavigationError(f"invalid regex {query!r}: {exc}") from exc


def _where_ok(node: Node, where: list[tuple[str, str]]) -> bool:
    for key, expected in where:
        if key == "ref":
            actual = node.ref
        elif key == "title":
            actual = node.title
        elif key == "summary":
            actual = node.summary
        else:
            value = node.meta.get(key)
            if value is None:
                return False
            actual = format_value(value)
        if actual != expected:
            return False
    return True


def parse_where(items: Iterable[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for item in items:
        key, sep, value = item.partition("=")
        if not sep or not key.strip():
            raise NavigationError(f"invalid --where {item!r} (expected KEY=VALUE)")
        pairs.append((key.strip(), value))
    return pairs


def render_find(
    store: Store,
    query: str,
    *,
    field: str | None = None,
    regex: bool = False,
    where: list[tuple[str, str]] | None = None,
    limit: int = 20,
    view: str | None = None,
    all_nodes: bool = False,
) -> str:
    pattern = _compile(query, regex)
    conditions = where or []
    anchor: str | None = None
    if all_nodes:
        nodes: Iterable[Node] = store.nodes.values()
        anchor = store.root_ref
    else:
        ref = resolve_ref(store, view) if view is not None else default_root(store)
        get_node(store, ref)
        anchor = ref
        nodes = load_view(store, ref).nodes.values()
    blocks: list[str] = []
    found = 0
    for node in nodes:
        if found >= limit:
            break
        if not _where_ok(node, conditions):
            continue
        hits: list[tuple[int, str]] = []
        if field == "body":
            for number, line in enumerate(node.body.splitlines(), 1):
                if _matches(line, query, pattern):
                    hits.append((number, line))
        else:
            values = _field_values(node, field)
            if any(_matches(value, query, pattern) for value in values):
                if field is None:
                    for number, line in enumerate(node.body.splitlines(), 1):
                        if _matches(line, query, pattern):
                            hits.append((number, line))
                    for value in [node.title, node.summary, *node.meta.values()]:
                        if isinstance(value, str) and _matches(value, query, pattern):
                            hits.append((0, value))
                else:
                    for value in values:
                        if _matches(value, query, pattern):
                            hits.append((0, value))
        if not hits:
            continue
        found += 1
        path = (
            _path_text(store, anchor, node.ref)
            if anchor is not None
            else node.ref
        )
        head = f"{node.ref}  {path}  {node.title}" if path != node.ref else f"{node.ref}  {node.title}"
        lines = [head]
        for number, text in hits[:MAX_FIND_LINES]:
            text = " ".join(text.split())
            if len(text) > FIND_LINE_CHARS:
                text = text[: FIND_LINE_CHARS - 3].rstrip() + "..."
            lines.append(f"{path}:{number}  {text}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def render_path(store: Store, ref: str, *, anchor: str | None = None) -> str:
    """Shortest undirected path from the anchor to ``ref``, with arrows.

    The anchor defaults to the store anchor (declared ``ROOT``, else the first
    component representative).  There is no ancestry and no first-parent chain:
    a BFS gives the shortest path and each step carries ``→`` (child) or ``←``
    (parent).
    """
    get_node(store, ref)
    start = anchor if anchor is not None else default_root(store)
    get_node(store, start)
    path = shortest_path(store, start, ref)
    if path is None:
        raise NavigationError(
            f"no undirected path from {start} to {ref}"
        )
    lines = []
    for current, arrow in path:
        node = store.nodes[current]
        prefix = f"{arrow} " if arrow else ""
        lines.append(f"{prefix}{node.ref}  {node.title}")
    return "\n".join(lines)
