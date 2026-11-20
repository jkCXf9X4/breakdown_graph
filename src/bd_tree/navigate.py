"""Read-only containment navigation: show, tree, ls, find and path.

Everything here is a pure projection of an already loaded :class:`~.model.Store`.
Containment order is the order of ``store.effective_contains(ref)``; cycles are
broken with a seen-set, and every walk is bounded by the requested depth.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from .errors import BreakdownError
from .loader import load_view, parse_ref, ref_of
from .model import Node, Store

# Front-matter keys that drive the model or are displayed separately.
RESERVED: frozenset[str] = frozenset(
    {"id", "legacy", "contains", "links", "home", "title", "summary"}
)

MAX_FIND_LINES = 3
FIND_LINE_CHARS = 160
SUMMARY_CHARS = 100


class NavigationError(BreakdownError):
    """A navigation request that cannot be served (bad ref, depth or pattern)."""


@dataclass(frozen=True)
class RefDepth:
    """``REF`` with an optional ``+DEPTH`` suffix."""

    ref: str
    depth: int | None


def parse_ref_depth(text: str, override: int | None = None) -> RefDepth:
    """Split ``5-1+2`` on the last ``+``; ``override`` wins over the suffix."""
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
        canonical = ref_of(*parse_ref(ref_text))
    except ValueError as exc:
        raise NavigationError(f"invalid ref {text!r}") from exc
    if override is not None:
        depth = override
    if depth is not None and depth < 0:
        raise NavigationError(f"invalid depth {depth} (must be non-negative)")
    return RefDepth(canonical, depth)


def main_root(store: Store) -> str:
    """Declared ``ROOT``, else the lowest main ref."""
    ref = store.root_ref
    if ref is None:
        raise NavigationError("store has no main nodes")
    return ref


def get_node(store: Store, ref: str) -> Node:
    node = store.nodes.get(ref)
    if node is None:
        raise NavigationError(f"unknown ref '{ref}'")
    return node


def view_roots(store: Store) -> list[Node]:
    """Refs that no node lists in ``contains`` (containment roots), sorted."""
    return store.containment_roots()


def _base_ref(node: Node) -> str:
    return node.ref if node.is_main else str(node.id)


def ancestor_chain(store: Store, ref: str, root: str | None = None) -> list[str]:
    """Refs from the main root down to ``ref`` (versions append their file)."""
    node = get_node(store, ref)
    target = _base_ref(node)
    start = root or main_root(store)
    path: list[str] = []
    seen: set[str] = set()

    def walk(current: str) -> bool:
        if current in seen or current not in store.nodes:
            return False
        seen.add(current)
        path.append(current)
        if current == target:
            return True
        for child in store.effective_contains(current):
            if walk(child):
                return True
        path.pop()
        return False

    found = walk(start)
    if not found:
        path = [target]
    if node.version != 0 and (not path or path[-1] != node.ref):
        path.append(node.ref)
    return path


def _breadcrumb(store: Store, ref: str) -> str:
    parts = []
    for current in ancestor_chain(store, ref):
        node = store.nodes.get(current)
        parts.append(f"{current} {node.title if node else ''}".rstrip())
    return " > ".join(parts)


def walk_containment(
    store: Store, ref: str, depth: int | None
) -> Iterator[tuple[Node, int]]:
    """Pre-order ``(node, level)`` pairs, bounded by ``depth`` (None = unlimited)."""
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
        for child in store.effective_contains(current):
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


def _link_footer(store: Store, ref: str, printed: Iterable[str]) -> str:
    """Links from printed nodes that leave the view (one level, no recursion)."""
    inside = set(load_view(store, ref).nodes)
    seen: set[tuple[str, str, str]] = set()
    rows: list[tuple[str, str, str, Node]] = []
    for source in printed:
        node = store.nodes.get(source)
        if node is None:
            continue
        for link in node.links:
            target = store.nodes.get(link.to)
            if target is None or link.to in inside:
                continue
            key = (source, link.to, link.type)
            if key in seen:
                continue
            seen.add(key)
            rows.append((source, link.to, link.type, target))
    if not rows:
        return ""
    rows.sort(key=lambda row: (row[0], row[1], row[2]))
    lines = ["links:"]
    lines.extend(
        f"- {source} -> {target_ref}  {target.title}  ({link_type})"
        for source, target_ref, link_type, target in rows
    )
    return "\n".join(lines)


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
    for node, level in walk_containment(store, ref, depth):
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
        footer = _link_footer(store, ref, printed)
        if footer:
            blocks.append(footer)
    return "\n\n".join(blocks)


def _outline_suffix(node: Node, fields: Iterable[str] | None, summary: bool) -> str:
    suffix = ""
    if summary and node.summary:
        suffix += f"  {node.summary[:SUMMARY_CHARS]}"
    if fields:
        for key, value in header_fields(node, fields):
            suffix += f"  {key}: {value}"
    return suffix


def render_tree(
    store: Store,
    ref: str,
    *,
    depth: int | None = 2,
    summary: bool = False,
    fields: Iterable[str] | None = None,
    links: bool = False,
) -> str:
    root = get_node(store, ref)
    lines = [f"{root.ref} {root.title}{_outline_suffix(root, fields, summary)}"]
    seen: set[str] = {root.ref}

    def walk(parent: str, level: int, continuation: str) -> None:
        if depth is not None and depth != 0 and level >= depth:
            return
        children = [
            child
            for child in store.effective_contains(parent)
            if child in store.nodes and child not in seen
        ]
        for index, child_ref in enumerate(children):
            last = index == len(children) - 1
            child = store.nodes[child_ref]
            seen.add(child_ref)
            branch = "`- " if last else "+- "
            lines.append(
                f"{continuation}{branch}{child.ref} {child.title}"
                f"{_outline_suffix(child, fields, summary)}"
            )
            walk(
                child_ref,
                level + 1,
                continuation + ("   " if last else "|  "),
            )

    walk(ref, 0, "")
    if links:
        footer = _link_footer(store, ref, seen)
        if footer:
            lines.append("")
            lines.append(footer)
    return "\n".join(lines)


def render_ls(
    store: Store,
    ref: str,
    *,
    depth: int | None = 1,
    columns: list[str] | None = None,
    max_chars: int = SUMMARY_CHARS,
) -> str:
    cols = columns or ["ref", "title", "summary"]
    get_node(store, ref)
    walk_depth = None if depth == 0 else depth
    lines = ["  ".join(cols)]
    for node, level in walk_containment(store, ref, walk_depth):
        if level == 0:
            continue
        cells: list[str] = []
        for column in cols:
            if column == "ref":
                value = node.ref
            elif column == "title":
                value = node.title
            elif column == "summary":
                value = node.summary
            elif column == "body":
                value = node.body.strip()
            else:
                value = format_value(node.meta.get(column, ""))
            value = " ".join(value.splitlines())
            if max_chars > 0 and len(value) > max_chars:
                value = value[: max(0, max_chars - 3)].rstrip() + "..."
            cells.append(value)
        lines.append("  " * (level - 1) + "  ".join(cells))
    return "\n".join(lines)


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
        ref = view if view is not None else main_root(store)
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
