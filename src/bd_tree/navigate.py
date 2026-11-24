"""Read-only navigation over the link closure: show, find and path.

Everything here is a pure projection of an already loaded :class:`~.model.Store`.
Children are the ``links`` targets of a node; cycles are broken with a seen-set,
and every walk is bounded by the requested depth.

Bare ids are CLI selectors, never refs: :func:`resolve_ref` maps ``5`` to the
version of id 5 that the chosen view contains.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from .errors import BreakdownError
from .loader import load_view, parse_selector
from .model import Node, Store

# Front-matter keys that drive the model or are displayed separately.
RESERVED: frozenset[str] = frozenset(
    {"id", "legacy", "links", "title", "summary"}
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
    """Declared ``ROOT``, else the lowest topology root, else the lowest node."""
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
    """Topology roots: nodes no other node reaches through ``links``, sorted."""
    return store.topology_roots()


def ancestor_chain(store: Store, ref: str, root: str | None = None) -> list[str]:
    """Refs from a topology root down to ``ref``, following ``Store.parents``.

    When a node has several parents the first by ``(stage, id, version)`` is
    chosen, so the chain is deterministic but one of several possible paths; the
    ambiguity is intentional and reported by ``bd check`` rather than hidden.
    """
    target = get_node(store, ref).ref
    chain = [target]
    seen: set[str] = {target}
    current = target
    while True:
        parents = [
            parent for parent in store.parents(current) if parent in store.nodes
        ]
        if not parents or parents[0] in seen:
            break
        seen.add(parents[0])
        chain.append(parents[0])
        current = parents[0]
    chain.reverse()
    if root is not None and root in chain:
        return chain[chain.index(root) :]
    return chain


def _breadcrumb(store: Store, ref: str) -> str:
    parts = []
    for current in ancestor_chain(store, ref):
        node = store.nodes.get(current)
        parts.append(f"{current} {node.title if node else ''}".rstrip())
    return " > ".join(parts)


def walk_links(
    store: Store, ref: str, depth: int | None
) -> Iterator[tuple[Node, int]]:
    """Pre-order ``(node, level)`` pairs over ``Store.children`` (out-links).

    The seen-set breaks cycles, and ``depth`` (None = unlimited) bounds the walk.
    """
    seen: set[str] = set()

    def walk(current: str, level: int) -> Iterator[tuple[Node, int]]:
        if current in seen:
            return
        node = store.nodes.get(current)
        if node is None:
            return
        seen.add(current)
        yield node, level
        if depth is not None and level >= depth:
            return
        for child in store.children(current):
            yield from walk(child, level + 1)

    yield from walk(ref, 0)


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
        body = cut.rstrip() + f" ... [truncated; bd show {node.ref}]"
    return body


def _graph_link_footer(store: Store, printed: Iterable[str]) -> str:
    """Authored out-edges and derived opposites for every printed node.

    Structural in-edges are shown as ``[derived]`` because only the source node
    authors them.  A symmetric master is shown as an out-edge; its opposite is
    derived on the target node and also carries ``[derived]``.
    """
    rows: list[str] = []
    seen: set[tuple[str, str, str, str]] = set()
    for ref in printed:
        node = store.nodes.get(ref)
        if node is None:
            continue
        for link in node.links:
            key = ("out", ref, link.to, link.type)
            if key in seen:
                continue
            seen.add(key)
            target = store.nodes.get(link.to)
            title = target.title if target is not None else "(missing)"
            rows.append(f"- {ref} -> {link.to}  {title}  ({link.type})")
        for edge in store.derived_links(ref):
            key = ("derived", ref, edge.target, edge.type)
            if key in seen:
                continue
            seen.add(key)
            target = store.nodes.get(edge.target)
            title = target.title if target is not None else "(missing)"
            rows.append(
                f"- {ref} -> {edge.target}  {title}  ({edge.type})  [derived]"
            )
        for parent in store.parents(ref):
            parent_node = store.nodes.get(parent)
            if parent_node is None:
                continue
            for link in parent_node.links:
                if link.to != ref or link.symmetric:
                    continue
                key = ("in", parent, ref, link.type)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    f"- {ref} <- {parent}  {parent_node.title}  "
                    f"({link.type})  [derived]"
                )
    if not rows:
        return ""
    return "links:\n" + "\n".join(rows)


def _link_footer(store: Store, printed: Iterable[str]) -> str:
    """Authored out-edges and derived in-edges for printed nodes."""
    return _graph_link_footer(store, printed)


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
    for node, level in walk_links(store, ref, depth):
        printed.append(node.ref)
        heading = "#" * min(level + 1, 6)
        parts = [f"{heading} {node.ref}  {node.title}"]
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
        footer = _link_footer(store, printed)
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
    if all_nodes:
        nodes: Iterable[Node] = store.nodes.values()
    else:
        ref = resolve_ref(store, view) if view is not None else default_root(store)
        get_node(store, ref)
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
        path = " > ".join(ancestor_chain(store, node.ref))
        head = f"{node.ref}  {node.title}" if path == node.ref else f"{node.ref}  {path}  {node.title}"
        lines = [head]
        for number, text in hits[:MAX_FIND_LINES]:
            text = " ".join(text.split())
            if len(text) > FIND_LINE_CHARS:
                text = text[: FIND_LINE_CHARS - 3].rstrip() + "..."
            lines.append(f"{path}:{number}  {text}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def render_path(store: Store, ref: str) -> str:
    get_node(store, ref)
    lines = []
    for current in ancestor_chain(store, ref):
        node = store.nodes[current]
        lines.append(f"{node.ref}  {node.title}")
    return "\n".join(lines)
