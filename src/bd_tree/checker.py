"""Structural validation over the full store and its containment views.

Only structure is checked: filename grammar, id/filename agreement, duplicate
refs, ref syntax in data, containment targets and cycles, per-view tree shape,
reachability, dangling links and size.  Front-matter fields, link types and
layers are never validated unless asked for with ``require``.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from .errors import BreakdownError
from .loader import (
    is_full_ref,
    load,
    load_view,
    parse_selector,
    ref_of,
)
from .model import CheckResult, Issue, Node, Store, View
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


def _cycles(adjacency: dict[str, list[str]]) -> list[list[str]]:
    color: dict[str, int] = {}
    stack: list[str] = []
    found: list[list[str]] = []
    seen_shapes: set[frozenset[str]] = set()

    def visit(node: str) -> None:
        color[node] = 1
        stack.append(node)
        for target in adjacency.get(node, ()):
            state = color.get(target, 0)
            if state == 0:
                visit(target)
            elif state == 1:
                cycle = stack[stack.index(target) :] + [target]
                shape = frozenset(cycle[:-1])
                if shape not in seen_shapes:
                    seen_shapes.add(shape)
                    found.append(cycle)
        stack.pop()
        color[node] = 2

    for node in sorted(adjacency):
        if color.get(node, 0) == 0:
            visit(node)
    return found


def _sort_key(node: Node) -> tuple[int, int]:
    return node.id, node.version


def default_root_ref(store: Store) -> str:
    """Declared ``ROOT``, else the lowest topology root; ``1-1`` when empty."""
    return store.root_ref or "1-1"


def _check_targets_and_cycles(store: Store, issues: list[Issue]) -> None:
    adjacency: dict[str, list[str]] = {}
    for node in store.nodes.values():
        targets: list[str] = []
        for child in node.contains:
            if not is_full_ref(child):
                # The loader already reported this as bare-ref / invalid-ref.
                continue
            if child not in store.nodes:
                issues.append(
                    Issue(
                        "error",
                        "missing-target",
                        f"contains target '{child}' does not exist",
                        node=node.ref,
                        path=str(node.path.relative_to(store.root)),
                    )
                )
                continue
            targets.append(child)
        if targets:
            adjacency[node.ref] = targets

    for cycle in _cycles(adjacency):
        issues.append(
            Issue(
                "error",
                "containment-cycle",
                "containment cycle: " + " -> ".join(cycle),
                node=cycle[0],
            )
        )


def _check_reachability(store: Store, root_ref: str, issues: list[Issue]) -> None:
    """Every logical id connected to the root through containment or a link.

    Reachability is per logical id: once an id appears in the root closure, all
    of its versions are normal alternatives and none is reported.  An id with no
    such path is an orphan and is reported as a warning.
    """
    if root_ref not in store.nodes:
        issues.append(
            Issue(
                "error",
                "root-ref-missing",
                f"root ref '{root_ref}' does not exist",
                node=root_ref,
            )
        )
        return

    reachable_ids: set[int] = set()
    seen: set[str] = set()
    queue = [root_ref]
    while queue:
        ref = queue.pop()
        if not is_full_ref(ref) or ref in seen:
            continue
        reached = store.nodes.get(ref)
        if reached is None:
            continue
        seen.add(ref)
        reachable_ids.add(reached.id)
        queue.extend(child for child in reached.contains if is_full_ref(child))
        queue.extend(
            link.to for link in reached.links if is_full_ref(link.to)
        )

    for ref in sorted(store.nodes, key=lambda r: _sort_key(store.nodes[r])):
        node = store.nodes[ref]
        if node.id in reachable_ids:
            continue
        issues.append(
            Issue(
                "warning",
                "unreachable-node",
                f"node '{ref}' is not reachable from root {root_ref} through "
                "containment or a link",
                node=ref,
                path=str(node.path.relative_to(store.root)),
            )
        )


def _check_view_trees(store: Store, issues: list[Issue]) -> None:
    """Tree shape per view: one parent per node, no cycles, no lost targets."""
    seen: set[tuple[str, str]] = set()
    for ref in sorted(store.nodes, key=lambda r: _sort_key(store.nodes[r])):
        try:
            resolved = load_view(store, ref)
        except BreakdownError:
            # Bare data refs are reported by the store scan; a view cannot walk.
            continue
        by_id: dict[int, list[str]] = {}
        for node_ref, node in resolved.nodes.items():
            by_id.setdefault(node.id, []).append(node_ref)
        for node_id, refs in by_id.items():
            if len(refs) < 2:
                continue
            key = ("duplicate-id", ",".join(sorted(refs)))
            if key in seen:
                continue
            seen.add(key)
            issues.append(
                Issue(
                    "error",
                    "duplicate-id",
                    f"view {resolved.ref} contains multiple versions of id "
                    f"{node_id}: " + ", ".join(sorted(refs)),
                    node=sorted(refs)[0],
                )
            )
        for issue in resolved.issues:
            if issue.code not in (
                "multiple-parents",
                "containment-cycle",
                "missing-target",
            ):
                continue
            key = (issue.code, issue.node or "")
            if key in seen:
                continue
            seen.add(key)
            issues.append(issue)


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
        key = (issue.level, issue.code, issue.node, issue.path, issue.message)
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

    if store.model == "graph":
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
            resolved = View(
                store=store, ref=str(selected), nodes={}, edges=[], issues=[]
            )
        else:
            graph = build_graph(store)
            issues.extend(graph_audit(graph, selected))
            resolved = load_view(store, selected)
            issues.extend(resolved.issues)
            _check_freshness(resolved, issues)
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

    _check_targets_and_cycles(store, issues)
    _check_reachability(store, canonical_root, issues)
    _check_view_trees(store, issues)

    selected = canonical_root
    if view is not None:
        selected, problem = _resolve(view)
        if selected is None:
            if problem is not None:
                issues.append(problem)
            issues = _dedupe(issues)
            issues.sort(key=lambda i: (i.level != "error", i.node or "", i.code, i.message))
            return CheckResult(root_path, str(view), 0, issues)
    try:
        resolved = load_view(store, selected)
    except BreakdownError as exc:
        # Already reported by the store scan; report once more with the ref.
        issues.append(Issue("error", "bare-ref", str(exc)))
        resolved = View(store=store, ref=str(selected), nodes={}, edges=[], issues=[])
    issues.extend(resolved.issues)
    _check_freshness(resolved, issues)
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
