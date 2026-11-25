"""Structural validation over the full store and one link-closure view.

Only structure is checked: filename grammar, id/filename agreement, duplicate
refs, ref syntax in data, graph edges, dangling links, inline token grammar
and size, plus the retired ``contains`` key and the retired front-matter
``links`` key.  Front-matter fields and link types are never validated unless
asked for with ``require``.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from .errors import BreakdownError
from .inline import parse_inline_links
from .loader import (
    load,
    load_view,
    parse_selector,
    ref_of,
)
from .model import CheckResult, Issue, Store, View
from .navigate import current_ref

SIZE_LINES = 120
SIZE_CHARS = 8000


def path_problem(path: str) -> str | None:
    """Return a reason when ``path`` is not a safe relative markdown path."""
    if not isinstance(path, str) or not path.strip():
        return "missing or empty"
    if "\\" in path:
        return "uses backslashes"
    pure = PurePosixPath(path)
    if pure.is_absolute():
        return "absolute path"
    if any(part in ("..", ".") for part in pure.parts):
        return "escapes with '..' or '.'"
    if pure.suffix.lower() != ".md":
        return "not a .md path"
    return None


def default_root_ref(store: Store) -> str:
    """Declared ``ROOT``, else the first component's representative; ``1-1``."""
    return store.root_ref or "1-1"


def _check_contains_removed(store: Store, issues: list[Issue]) -> None:
    """Report any surviving ``contains`` key; only ``bdg migrate`` removes it."""
    for node in store.nodes.values():
        if "contains" not in node.meta:
            continue
        issues.append(
            Issue(
                "error",
                "contains-removed",
                "node still declares 'contains'; containment is retired, "
                "run `bdg migrate`",
                node=node.ref,
                path=str(node.path.relative_to(store.root)),
            )
        )


def _check_freshness(view: View, issues: list[Issue]) -> None:
    for edge in view.edges:
        if not edge.propagating:
            continue
        target = view.nodes.get(edge.target)
        if target is None:
            continue
        if edge.pinned is None:
            issues.append(
                Issue(
                    "warning",
                    "untracked-link",
                    f"{edge.target} ({edge.type}) has no pinned hash",
                    node=edge.source,
                )
            )
        elif edge.pinned != target.body_hash:
            issues.append(
                Issue(
                    "warning",
                    "stale-link",
                    f"{edge.target} ({edge.type}) pinned {edge.pinned} "
                    f"but body is {target.body_hash}",
                    node=edge.source,
                )
            )


def _check_link_titles(view: View, issues: list[Issue]) -> None:
    """Cached inline token titles must match the target node's live title."""
    for node in view.nodes.values():
        inline_links = parse_inline_links(node.body)
        for found in inline_links:
            if found.title is None:
                continue
            target = view.nodes.get(found.to)
            if target is None:
                continue
            if target.title != found.title:
                issues.append(
                    Issue(
                        "warning",
                        "link-title-stale",
                        f"inline title {found.title!r} does not match the live "
                        f"title of {found.to} ({target.title!r})",
                        node=node.ref,
                        line=found.line,
                    )
                )


def _check_sizes(
    view: View, issues: list[Issue], max_lines: int, max_chars: int
) -> None:
    for node in view.nodes.values():
        if node.body_lines > max_lines or node.body_chars > max_chars:
            issues.append(
                Issue(
                    "warning",
                    "oversize",
                    f"node is {node.body_lines} lines / {node.body_chars} chars "
                    f"(limit {max_lines} / {max_chars})",
                    node=node.ref,
                    path=str(node.path.relative_to(view.root)),
                )
            )


def _check_required(store: Store, fields: list[str], issues: list[Issue]) -> None:
    for node in store.nodes.values():
        missing = [
            field
            for field in fields
            if node.meta.get(field) is None or node.meta.get(field) == ""
        ]
        if missing:
            issues.append(
                Issue(
                    "error",
                    "missing-field",
                    "missing required field(s): " + ", ".join(missing),
                    node=node.ref,
                    path=str(node.path.relative_to(store.root)),
                )
            )


def _dedupe(issues: list[Issue]) -> list[Issue]:
    seen: set[tuple] = set()
    result: list[Issue] = []
    for issue in issues:
        key = (
            issue.level, issue.code, issue.node, issue.path, issue.message,
            issue.line,
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(issue)
    return result


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
    root_path = Path(root).resolve()
    try:
        store = load(root_path)
    except BreakdownError as exc:
        return CheckResult(root_path, str(view or root_ref or "1"), 0, [
            Issue("error", "root", str(exc))
        ])

    def _resolve(value: str | int) -> tuple[str | None, Issue | None]:
        """Resolve a full ref or a bare selector through the default view."""
        try:
            node_id, version = parse_selector(value)
        except ValueError:
            return None, Issue("error", "invalid-ref", f"invalid ref {value!r}")
        if version is not None:
            return ref_of(node_id, version), None
        try:
            found = current_ref(store, node_id)
        except BreakdownError as exc:
            return None, Issue("error", "bare-ref", str(exc))
        if found is None:
            return None, Issue(
                "error",
                "invalid-ref",
                f"id {node_id} is not in view {default_root_ref(store)}",
            )
        return found, None

    if root_ref is None:
        canonical_root = default_root_ref(store)
    else:
        canonical_root, problem = _resolve(root_ref)
        if canonical_root is None:
            return CheckResult(
                root_path, str(root_ref), 0, [problem] if problem else []
            )

    issues: list[Issue] = list(store.issues)
    _check_contains_removed(store, issues)

    from .graph import audit as graph_audit
    from .graph import build_graph

    selected = canonical_root
    if view is not None:
        selected, problem = _resolve(view)
        if selected is None:
            if problem is not None:
                issues.append(problem)
            issues = _dedupe(issues)
            issues.sort(
                key=lambda i: (i.level != "error", i.node or "", i.code, i.message)
            )
            return CheckResult(root_path, str(view), 0, issues)

    if selected not in store.nodes:
        issues.append(
            Issue(
                "error",
                "root-ref-missing",
                f"root ref '{selected}' does not exist",
                node=selected,
            )
        )
        resolved = View(store=store, ref=str(selected), nodes={}, edges=[], issues=[])
    else:
        graph = build_graph(store)
        issues.extend(graph_audit(graph, selected))
        resolved = load_view(store, selected)
        issues.extend(resolved.issues)
        _check_freshness(resolved, issues)
        _check_link_titles(resolved, issues)
        _check_sizes(
            resolved,
            issues,
            SIZE_LINES if max_lines is None else max_lines,
            SIZE_CHARS if max_chars is None else max_chars,
        )
    _check_required(store, list(require), issues)

    issues = _dedupe(issues)
    issues.sort(key=lambda i: (i.level != "error", i.node or "", i.code, i.message))
    return CheckResult(root_path, resolved.ref, len(resolved.nodes), issues)
