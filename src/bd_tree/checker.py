"""Structural validation over the full store and its containment views.

Only structure is checked: filename grammar, id/filename agreement, duplicate
refs, missing mains, containment targets and cycles, per-view tree shape,
reachability, duplicate home paths, dangling links and size.  Front-matter
fields, link types and layers are never validated unless asked for with
``require``.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from .errors import BreakdownError
from .loader import load, load_view, parse_ref, ref_of
from .model import CheckResult, Issue, Node, Store, View

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


# Kept as an alias for callers that predate optional homes.
home_problem = path_problem


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
    """Declared ``ROOT``, else the lowest main ref; ``1`` when empty."""
    return store.root_ref or "1"


def _check_targets_and_cycles(store: Store, issues: list[Issue]) -> None:
    adjacency: dict[str, list[str]] = {}
    for node in store.nodes.values():
        targets: list[str] = []
        for child in node.contains or []:
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
    """Every file connected to the root through containment, shared id or link.

    A main and its versions are alternatives for one logical node, so reaching
    any of them reaches the others and the closures beneath them.  An outgoing
    link from a reached node is a reachability edge too.  A ref with no such
    path is an orphan and is reported.
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

    by_id: dict[int, list[str]] = {}
    for ref, node in store.nodes.items():
        by_id.setdefault(node.id, []).append(ref)

    reachable: set[str] = set()
    queue = [root_ref]
    while queue:
        ref = queue.pop()
        if ref in reachable:
            continue
        reached = store.nodes.get(ref)
        if reached is None:
            continue
        reachable.add(ref)
        queue.extend(store.effective_contains(ref))
        queue.extend(peer for peer in by_id[reached.id] if peer != ref)
        queue.extend(link.to for link in reached.links)

    for ref in sorted(store.nodes, key=lambda r: _sort_key(store.nodes[r])):
        if ref in reachable:
            continue
        node = store.nodes[ref]
        issues.append(
            Issue(
                "error",
                "unreachable",
                f"node '{ref}' is not reachable from root {root_ref} through "
                "containment, another file of the same id, or a link",
                node=ref,
                path=str(node.path.relative_to(store.root)),
            )
        )


def _check_view_trees(store: Store, issues: list[Issue]) -> None:
    """Tree shape per view: one parent per node, no cycles, no lost targets."""
    seen: set[tuple[str, str]] = set()
    for ref in sorted(store.nodes, key=lambda r: _sort_key(store.nodes[r])):
        resolved = load_view(store, ref)
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


def _check_homes(view: View, issues: list[Issue]) -> None:
    by_home: dict[str, list[Node]] = {}
    for node in view.nodes.values():
        home = node.home
        if home is None:
            continue  # optional; the export template supplies a fallback
        problem = path_problem(home)
        if problem:
            issues.append(
                Issue(
                    "error",
                    "bad-home",
                    f"invalid home '{home}': {problem}",
                    node=node.ref,
                    path=str(node.path.relative_to(view.root)),
                )
            )
            continue
        by_home.setdefault(home, []).append(node)
    for home, nodes in sorted(by_home.items()):
        if len(nodes) > 1:
            refs = ", ".join(sorted(node.ref for node in nodes))
            for node in nodes:
                issues.append(
                    Issue(
                        "error",
                        "duplicate-home",
                        f"home '{home}' is used by {refs}",
                        node=node.ref,
                        path=str(node.path.relative_to(view.root)),
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

    if root_ref is None:
        canonical_root = default_root_ref(store)
    else:
        try:
            canonical_root = ref_of(*parse_ref(root_ref))
        except ValueError:
            return CheckResult(
                root_path,
                str(root_ref),
                0,
                [Issue("error", "invalid-ref", f"invalid root ref {root_ref!r}")],
            )

    issues: list[Issue] = list(store.issues)
    _check_targets_and_cycles(store, issues)
    _check_reachability(store, canonical_root, issues)
    _check_view_trees(store, issues)

    resolved = load_view(store, view if view is not None else canonical_root)
    issues.extend(resolved.issues)
    _check_homes(resolved, issues)
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
