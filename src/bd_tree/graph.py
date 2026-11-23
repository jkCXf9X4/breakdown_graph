"""Graph mode: ``links`` are forward parent -> child edges, ``stage`` orders them.

This is a prototype beside containment.  It reads the same flat store but
ignores ``contains`` completely: a view is the forward closure of one anchor over
declared ``links``, and no node is placed by a containment tree.

Authored data is the declared out-edge list on each node.  In-edges are always
computed from those declarations and are reported as derived.

Ordering is monotone by ``stage`` (an integer on every node) with ``order`` as
the within-stage tie-break.  A bare CLI id selects the highest existing version;
a full ref is used verbatim.
"""

from __future__ import annotations

import posixpath
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from .checker import path_problem
from .errors import BreakdownError, ExportError
from .exporter import BANNER, _prepare_out, exporter
from .frontmatter import render_document
from .loader import load, parse_ref, parse_selector
from .model import ExportResult, Issue, Link, Node, Store, View, slugify

FANOUT_LIMIT = 200
RESERVED = frozenset({"INDEX.md"})


# ---------------------------------------------------------------------------
# Ordering keys


def _invalid(
    issues: list[Issue] | None, code: str, message: str, node: str
) -> None:
    if issues is None:
        raise BreakdownError(f"{code}: {message}")
    issues.append(Issue("error", code, message, node=node))


def stage(node: Node, issues: list[Issue] | None = None) -> int | None:
    """The node's integer ``stage``, or report the missing/invalid value.

    With no ``issues`` list the error raises :class:`BreakdownError`; audit
    passes a list so every bad node is collected instead of aborting.
    """
    value = node.meta.get("stage")
    if value is None:
        _invalid(
            issues,
            "graph-stage-missing",
            f"node '{node.ref}' has no 'stage'",
            node.ref,
        )
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        _invalid(
            issues,
            "graph-stage-invalid",
            f"node '{node.ref}' has non-integer 'stage' {value!r}",
            node.ref,
        )
        return None
    return value


def order(node: Node, issues: list[Issue] | None = None) -> int | None:
    """The node's integer ``order`` (default 0), or report an invalid value."""
    if "order" not in node.meta:
        return 0
    value = node.meta.get("order")
    if isinstance(value, bool) or not isinstance(value, int):
        _invalid(
            issues,
            "graph-order-invalid",
            f"node '{node.ref}' has non-integer 'order' {value!r}",
            node.ref,
        )
        return None
    return value


def _stage_of(node: Node) -> int | None:
    value = node.meta.get("stage")
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _order_of(node: Node) -> int:
    value = node.meta.get("order", 0)
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return value


def _ref_key(node: Node) -> tuple[int, int]:
    return node.id, node.version


def _text_ref_key(text: str) -> tuple[int, int, int, str]:
    try:
        node_id, version = parse_ref(text)
    except ValueError:
        return (1, 0, 0, text)
    return (0, node_id, version, "")


def _edge_key(link: Link) -> tuple[tuple[int, int, int, str], str]:
    return _text_ref_key(link.to), link.type


# ---------------------------------------------------------------------------
# The graph


@dataclass
class Graph:
    """A loaded store plus authored out-edges and derived in-edges."""

    store: Store
    out: dict[str, list[Link]]
    inn: dict[str, list[Link]]
    roots: list[str]

    def node(self, ref: str) -> Node | None:
        return self.store.nodes.get(ref)


def build_graph(root: Store | str | Path) -> Graph:
    """Build adjacency from ``node.links``; ``contains`` is never consulted."""
    store = root if isinstance(root, Store) else load(root)
    out = {ref: list(node.links) for ref, node in store.nodes.items()}
    inn: dict[str, list[Link]] = {ref: [] for ref in store.nodes}
    for ref in sorted(out, key=lambda r: _ref_key(store.nodes[r])):
        for link in out[ref]:
            reverse = Link(
                to=ref,
                type=link.type,
                pinned=link.pinned,
                propagates=link.propagates,
                raw=link.raw,
            )
            inn.setdefault(link.to, []).append(reverse)
    incoming = {link.to for links in out.values() for link in links}
    roots = sorted(
        (ref for ref in store.nodes if ref not in incoming),
        key=lambda ref: _ref_key(store.nodes[ref]),
    )
    return Graph(store=store, out=out, inn=inn, roots=roots)


def resolve_graph_ref(graph: Graph, text: str | int) -> str:
    """Resolve a CLI selector: full refs verbatim, a bare id to its highest version."""
    raw = str(text).strip()
    try:
        node_id, version = parse_selector(raw)
    except ValueError as exc:
        raise BreakdownError(f"invalid ref '{text}'") from exc
    if version is not None:
        return f"{node_id}-{version}"
    matches = [node for node in graph.store.nodes.values() if node.id == node_id]
    if not matches:
        raise BreakdownError(f"id {node_id} has no node files")
    return max(matches, key=lambda node: node.version).ref


def default_anchor(graph: Graph) -> str | None:
    """The store ``ROOT``, else the lowest root by ``(id, version)``."""
    if graph.store.declared_root is not None:
        return graph.store.declared_root
    if graph.roots:
        return graph.roots[0]
    return graph.store.root_ref


def _normalise_types(types: Iterable[str] | str | None) -> set[str] | None:
    if types is None:
        return None
    if isinstance(types, str):
        return {types}
    return set(types)


def _normalise_stages(
    stages: Sequence[int] | tuple[int, int] | str | None,
) -> tuple[int, int] | None:
    if stages is None:
        return None
    if isinstance(stages, str):
        left, sep, right = stages.partition(":")
        if not sep:
            raise BreakdownError(f"invalid stage range '{stages}' (expected A:B)")
        try:
            low, high = int(left), int(right)
        except ValueError as exc:
            raise BreakdownError(
                f"invalid stage range '{stages}' (expected integers A:B)"
            ) from exc
        stages = (low, high)
    values = list(stages)
    if len(values) == 1:
        values = [values[0], values[0]]
    if len(values) != 2:
        raise BreakdownError("invalid stage range (expected A:B)")
    low, high = int(values[0]), int(values[1])
    if low > high:
        raise BreakdownError(f"invalid stage range {low}:{high} (A must be <= B)")
    return low, high


def _stage_ok(node: Node, stages: tuple[int, int] | None) -> bool:
    if stages is None:
        return True
    value = _stage_of(node)
    return value is not None and stages[0] <= value <= stages[1]


def graph_view(
    graph: Graph,
    anchor: str | int | None,
    *,
    depth: int | None = None,
    types: Iterable[str] | str | None = None,
    stages: Sequence[int] | tuple[int, int] | str | None = None,
) -> list[str]:
    """Forward closure over authored out-edges, filtered by type and stage.

    A node reached through several parents is included once.  The anchor is
    always included; descendants outside ``stages`` are omitted but traversal
    continues through them, so a later in-range stage stays reachable.
    """
    if depth is not None and depth < 0:
        raise BreakdownError(f"invalid depth {depth} (must be non-negative)")
    target = default_anchor(graph) if anchor is None else resolve_graph_ref(graph, anchor)
    if target is None:
        raise BreakdownError("store has no graph nodes")
    if target not in graph.store.nodes:
        raise BreakdownError(f"anchor '{target}' does not exist")
    type_set = _normalise_types(types)
    stage_range = _normalise_stages(stages)

    included: list[str] = []
    seen: set[str] = set()
    queue: list[tuple[str, int]] = [(target, 0)]
    while queue:
        current, level = queue.pop(0)
        if current in seen or current not in graph.store.nodes:
            continue
        seen.add(current)
        node = graph.store.nodes[current]
        if current == target or _stage_ok(node, stage_range):
            included.append(current)
        if depth is not None and level >= depth:
            continue
        for link in sorted(graph.out.get(current, ()), key=_edge_key):
            if type_set is not None and link.type not in type_set:
                continue
            if link.to in graph.store.nodes and link.to not in seen:
                queue.append((link.to, level + 1))
    return included


# ---------------------------------------------------------------------------
# Layout


@dataclass(frozen=True)
class StageBand:
    stage: int
    label: str
    directory: str
    refs: list[str]


def _band_label(graph: Graph, refs: Iterable[str]) -> str:
    counts: Counter[str] = Counter()
    for ref in refs:
        node = graph.store.nodes[ref]
        value = node.meta.get("layer")
        if isinstance(value, str) and value.strip():
            counts[value.strip()] += 1
    if not counts:
        return ""
    value = min(counts.items(), key=lambda item: (-item[1], item[0]))[0]
    return slugify(value)


def graph_layout(graph: Graph, refs: Iterable[str]) -> list[StageBand]:
    """Group refs by ``stage``; order inside a stage by ``(order, id, version)``."""
    groups: dict[int, list[str]] = defaultdict(list)
    for ref in refs:
        node = graph.store.nodes.get(ref)
        if node is None:
            continue
        value = _stage_of(node)
        if value is None:
            raise BreakdownError(
                f"node '{ref}' needs an integer 'stage' for the graph layout"
            )
        groups[value].append(ref)

    bands: list[StageBand] = []
    for value in sorted(groups):
        members = groups[value]
        members.sort(
            key=lambda ref: (
                _order_of(graph.store.nodes[ref]),
                graph.store.nodes[ref].id,
                graph.store.nodes[ref].version,
            )
        )
        label = _band_label(graph, members) or f"stage-{value:02d}"
        bands.append(
            StageBand(
                stage=value,
                label=label,
                directory=f"{value:02d}-{label}",
                refs=members,
            )
        )
    return bands


# ---------------------------------------------------------------------------
# Text and DOT rendering


def _link_text(link: Link) -> str:
    return f"{link.to} ({link.type})"


def render_graph(graph: Graph, refs: Iterable[str]) -> str:
    """Per-stage text: ``stage N — label``, nodes, then derived in/out lines."""
    lines: list[str] = []
    for band in graph_layout(graph, refs):
        lines.append(f"stage {band.stage} — {band.label}")
        for ref in band.refs:
            node = graph.store.nodes[ref]
            lines.append(f"[{ref}] {node.title}")
            incoming = sorted(graph.inn.get(ref, ()), key=_edge_key)
            if incoming:
                lines.append(
                    "  ← in: " + ", ".join(_link_text(link) for link in incoming)
                )
            outgoing = sorted(graph.out.get(ref, ()), key=_edge_key)
            if outgoing:
                lines.append(
                    "  → out: " + ", ".join(_link_text(link) for link in outgoing)
                )
        lines.append("")
    return "\n".join(lines).rstrip("\n")


def _dot_quote(text: str) -> str:
    escaped = (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return '"' + escaped + '"'


def render_dot(graph: Graph, refs: Iterable[str]) -> str:
    """Graphviz DOT: node labels ``ref title``, one edge per authored link."""
    wanted = set(refs)
    ordered = sorted(
        wanted,
        key=lambda ref: (
            _stage_of(graph.store.nodes[ref])
            if _stage_of(graph.store.nodes[ref]) is not None
            else 10**9,
            _order_of(graph.store.nodes[ref]),
            graph.store.nodes[ref].id,
            graph.store.nodes[ref].version,
        ),
    )
    lines = ["digraph bd_graph {"]
    for ref in ordered:
        node = graph.store.nodes[ref]
        lines.append(f"  {_dot_quote(ref)} [label={_dot_quote(f'{ref} {node.title}')}];")
    edges = sorted(
        {
            (source, link.to, link.type)
            for source in ordered
            for link in graph.out.get(source, ())
            if link.to in wanted
        }
    )
    for source, target, link_type in edges:
        lines.append(
            f"  {_dot_quote(source)} -> {_dot_quote(target)} "
            f"[label={_dot_quote(link_type)}];"
        )
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_out(graph: Graph, ref: str | int) -> str:
    """Authored out-edges only, sorted; no inference and no in-edges."""
    target = resolve_graph_ref(graph, ref)
    if target not in graph.store.nodes:
        raise BreakdownError(f"unknown ref '{target}'")
    links = sorted(graph.out.get(target, ()), key=_edge_key)
    if not links:
        return f"{target} -> (no declared out-links)"
    return "\n".join(f"{target} -> {_link_text(link)}" for link in links)


def render_in(graph: Graph, ref: str | int) -> str:
    """Computed in-edges, every line explicitly marked derived."""
    target = resolve_graph_ref(graph, ref)
    if target not in graph.store.nodes:
        raise BreakdownError(f"unknown ref '{target}'")
    links = sorted(graph.inn.get(target, ()), key=_edge_key)
    if not links:
        return f"{target} <- (no computed in-links)  [derived]"
    lines = [f"{len(links)} in-links  [derived]"]
    lines.extend(
        f"{link.to} -> {target} ({link.type})  [derived]" for link in links
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Audit


def _cycles(graph: Graph) -> list[list[str]]:
    adjacency = {
        ref: sorted(
            {link.to for link in graph.out.get(ref, ()) if link.to in graph.store.nodes}
        )
        for ref in graph.store.nodes
    }
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

    for node in sorted(adjacency, key=_text_ref_key):
        if color.get(node, 0) == 0:
            visit(node)
    return found


def audit(graph: Graph, anchor: str | int | None = None) -> list[Issue]:
    """Collect every graph-mode issue as :class:`~.model.Issue`."""
    issues: list[Issue] = []
    nodes = sorted(graph.store.nodes, key=lambda ref: _ref_key(graph.store.nodes[ref]))

    for ref in nodes:
        node = graph.store.nodes[ref]
        stage(node, issues)
        order(node, issues)

    for ref in nodes:
        node = graph.store.nodes[ref]
        source_stage = _stage_of(node)
        for link in graph.out.get(ref, ()):
            if link.to not in graph.store.nodes:
                issues.append(
                    Issue(
                        "error",
                        "graph-dangling-link",
                        f"link to missing node '{link.to}' ({link.type})",
                        node=ref,
                    )
                )
                continue
            target_stage = _stage_of(graph.store.nodes[link.to])
            if (
                source_stage is not None
                and target_stage is not None
                and source_stage >= target_stage
            ):
                issues.append(
                    Issue(
                        "error",
                        "graph-back-edge",
                        f"edge {ref} -> {link.to} ({link.type}) is not strictly "
                        f"forward: stage {source_stage} >= {target_stage}",
                        node=ref,
                    )
                )

    for cycle in _cycles(graph):
        issues.append(
            Issue(
                "error",
                "graph-cycle",
                "graph cycle: " + " -> ".join(cycle),
                node=cycle[0],
            )
        )

    anchor_ref: str | None
    if anchor is None:
        anchor_ref = default_anchor(graph)
    else:
        anchor_ref = resolve_graph_ref(graph, anchor)
        if anchor_ref not in graph.store.nodes:
            raise BreakdownError(f"anchor '{anchor_ref}' does not exist")

    for ref in graph.roots:
        if ref != anchor_ref:
            issues.append(
                Issue(
                    "warning",
                    "graph-orphan",
                    f"node '{ref}' has no incoming edge",
                    node=ref,
                )
            )

    for ref in nodes:
        degree = len(graph.out.get(ref, ()))
        if degree > FANOUT_LIMIT:
            issues.append(
                Issue(
                    "warning",
                    "graph-wide-fanout",
                    f"node '{ref}' has {degree} out-links; split it into an "
                    "intermediate header",
                    node=ref,
                )
            )
        targets = [link.to for link in graph.out.get(ref, ())]
        if targets != sorted(targets, key=_text_ref_key):
            issues.append(
                Issue(
                    "warning",
                    "graph-unsorted-links",
                    f"links of '{ref}' are not sorted by ref: "
                    + ", ".join(targets),
                    node=ref,
                )
            )

    if anchor_ref is not None and anchor_ref in graph.store.nodes:
        versions: dict[int, list[str]] = defaultdict(list)
        for ref in graph_view(graph, anchor_ref):
            node = graph.store.nodes[ref]
            versions[node.id].append(ref)
        for node_id in sorted(versions):
            refs = versions[node_id]
            if len(refs) > 1:
                issues.append(
                    Issue(
                        "warning",
                        "graph-duplicate-version",
                        f"id {node_id} has {len(refs)} versions reachable from "
                        f"{anchor_ref}: " + ", ".join(sorted(refs, key=_text_ref_key)),
                        node=min(refs, key=_text_ref_key),
                    )
                )
    return issues


def render_audit(graph: Graph, anchor: str | int | None = None) -> str:
    """Issues grouped error/warning, then a one-line summary."""
    issues = audit(graph, anchor)
    errors = [issue for issue in issues if issue.level == "error"]
    warnings = [issue for issue in issues if issue.level == "warning"]
    lines: list[str] = []
    if errors:
        lines.append("errors:")
        lines.extend(f"  {issue.format()}" for issue in errors)
    if warnings:
        lines.append("warnings:")
        lines.extend(f"  {issue.format()}" for issue in warnings)
    if not issues:
        lines.append("no issues")
    lines.append(f"{len(errors)} errors, {len(warnings)} warnings")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Export


def _node_path(node: Node, directory: str) -> str:
    if node.name:
        stem = node.name
        path = f"{directory}/{stem}.md"
    else:
        slug = slugify(node.title)
        if slug and slug != node.ref:
            path = f"{directory}/{node.ref}-{slug}.md"
        else:
            path = f"{directory}/{node.ref}.md"
    problem = path_problem(path)
    if problem:
        raise ExportError(
            f"node {node.ref} resolves to invalid path '{path}': {problem}"
        )
    if path.rsplit("/", 1)[-1] in RESERVED:
        raise ExportError(f"node {node.ref} path collides with generated '{path}'")
    return path


def _relative(path: str, start: str) -> str:
    return posixpath.relpath(path, start)


def _ref_link(
    graph: Graph, ref: str, paths: dict[str, str], directory: str
) -> str:
    node = graph.store.nodes[ref]
    label = f"{ref} {node.title}"
    path = paths.get(ref)
    if path is None:
        return f"{label} (`{ref}`)"
    return f"[{label}]({_relative(path, directory)})"


def _stage_index(
    graph: Graph, band: StageBand, paths: dict[str, str]
) -> str:
    lines = [BANNER.format(name="graph"), "", f"# {band.directory}/", ""]
    for ref in band.refs:
        lines.append(f"- {_ref_link(graph, ref, paths, band.directory)}")
        for link in sorted(graph.out.get(ref, ()), key=_edge_key):
            lines.append(
                f"  → {_ref_link(graph, link.to, paths, band.directory)} "
                f"({link.type})"
                if link.to in graph.store.nodes
                else f"  → {link.to} ({link.type})"
            )
        for link in sorted(graph.inn.get(ref, ()), key=_edge_key):
            lines.append(
                f"  ← {_ref_link(graph, link.to, paths, band.directory)} "
                f"({link.type}) [derived]"
                if link.to in graph.store.nodes
                else f"  ← {link.to} ({link.type}) [derived]"
            )
    lines.append("")
    return "\n".join(lines)


def _root_index(graph: Graph, anchor: str, bands: list[StageBand]) -> str:
    lines = [BANNER.format(name="graph"), "", f"# Graph {anchor}", ""]
    for band in bands:
        count = len(band.refs)
        noun = "node" if count == 1 else "nodes"
        lines.append(
            f"- [stage {band.stage} — {band.label}]"
            f"({band.directory}/INDEX.md) — {count} {noun}"
        )
    lines.append("")
    return "\n".join(lines)


@exporter("graph")
def export_graph(
    graph: Graph | View,
    anchor: str | Path,
    out: Path | None = None,
    *,
    force: bool = False,
    clean: bool = False,
) -> ExportResult:
    """Write a staged, read-only graph snapshot with root and per-stage indexes."""
    if isinstance(graph, View):
        store_view = graph
        target = store_view.ref
        destination = Path(anchor)
        built = build_graph(store_view.store)
    else:
        built = graph
        if out is None:
            raise ExportError("export graph needs an output directory")
        target = resolve_graph_ref(built, anchor)
        destination = Path(out)

    refs = graph_view(built, target)
    bands = graph_layout(built, refs)
    _prepare_out(destination, force=force, clean=clean)

    paths: dict[str, str] = {}
    used: dict[str, str] = {}
    for band in bands:
        for ref in band.refs:
            path = _node_path(built.store.nodes[ref], band.directory)
            previous = used.get(path)
            if previous is not None:
                raise ExportError(
                    f"nodes {previous} and {ref} both resolve to path '{path}'"
                )
            used[path] = ref
            paths[ref] = path

    files: list[Path] = []
    for band in bands:
        for ref in band.refs:
            node = built.store.nodes[ref]
            dest = destination / paths[ref]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(
                render_document(node.meta, node.body),
                encoding="utf-8",
                newline="",
            )
            files.append(dest)

    for band in bands:
        path = destination / band.directory / "INDEX.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            _stage_index(built, band, paths), encoding="utf-8", newline=""
        )
        files.append(path)

    root_index = destination / "INDEX.md"
    root_index.write_text(
        _root_index(built, target, bands), encoding="utf-8", newline=""
    )
    files.append(root_index)
    return ExportResult("graph", destination, len(refs), files)
