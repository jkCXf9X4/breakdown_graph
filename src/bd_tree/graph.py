"""Graph mode: typed ``links`` projected as one undirected ring graph.

A view is the weakly connected component of one anchor over authored links.
Direction survives in the data (parent -> child) and as a label, but it no
longer gates membership, ordering or audit.  Ordering is the undirected BFS hop
count from the anchor; cycles are ordinary edges.
"""

from __future__ import annotations

import shutil
import subprocess
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .checker import path_problem
from .errors import BreakdownError, ExportError
from .exporter import BANNER, _prepare_out
from .frontmatter import render_document
from .loader import load, parse_ref, parse_selector
from .model import ExportResult, Issue, Link, Node, Store, View, slugify

FANOUT_LIMIT = 200
RESERVED = frozenset({"INDEX.md"})

_KIND_NOUN = {"child": "children", "parent": "parents"}


# ---------------------------------------------------------------------------
# Ordering keys


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
    """A loaded store with authored out-edges, derived in-edges, and rings."""

    store: Store
    out: dict[str, list[Link]]
    inn: dict[str, list[Link]]
    roots: list[str]
    anchor: str | None = None
    distance: dict[str, int] = field(default_factory=dict)
    components: list[list[str]] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    def node(self, ref: str) -> Node | None:
        return self.store.nodes.get(ref)


def ring_distances(
    store_or_graph: Store | Graph, anchor: str | None
) -> dict[str, int]:
    """Undirected BFS hop count from ``anchor`` over authored links.

    Every reachable ref is mapped to its minimum ring.  An empty mapping means
    the anchor is absent from the store.  Cycles need no special handling: a
    ref is enqueued exactly once.
    """
    if isinstance(store_or_graph, Graph):
        store = store_or_graph.store
        if anchor is None:
            anchor = store_or_graph.anchor
    else:
        store = store_or_graph
    if anchor is None:
        anchor = store.root_ref
    if anchor is None or anchor not in store.nodes:
        return {}
    distance: dict[str, int] = {anchor: 0}
    queue: list[str] = [anchor]
    head = 0
    while head < len(queue):
        current = queue[head]
        head += 1
        for neighbor in store.neighbors(current):
            if neighbor.ref in distance or neighbor.ref not in store.nodes:
                continue
            distance[neighbor.ref] = distance[current] + 1
            queue.append(neighbor.ref)
    return distance


def _root_refs(store: Store) -> list[str]:
    """The representative ref of every weak component, in store order."""
    return [
        root.ref if isinstance(root, Node) else str(root)
        for root in store.topology_roots()
    ]


def build_graph(root: Store | str | Path, anchor: str | None = None) -> Graph:
    """Build adjacency, components, and the undirected ring map.

    ``anchor`` defaults to :attr:`Store.root_ref`.  The graph is undirected:
    ``out``/``inn`` keep the authored directions for display and explicit
    directional commands, while membership and ordering use ``distance``.
    """
    store = root if isinstance(root, Store) else load(root)
    out = {ref: list(node.links) for ref, node in store.nodes.items()}
    inn: dict[str, list[Link]] = {ref: [] for ref in store.nodes}
    for ref in sorted(out, key=lambda r: _ref_key(store.nodes[r])):
        for link in out[ref]:
            reverse = Link(to=ref, type=link.type)
            inn.setdefault(link.to, []).append(reverse)
    chosen = store.root_ref if anchor is None else anchor
    return Graph(
        store=store,
        out=out,
        inn=inn,
        roots=_root_refs(store),
        anchor=chosen,
        distance=ring_distances(store, chosen),
        components=store.components(),
        issues=list(store.issues),
    )


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
    """The graph anchor: the explicit build anchor, else ``Store.root_ref``."""
    if graph.anchor is not None:
        return graph.anchor
    return graph.store.root_ref


def _normalise_types(types: Iterable[str] | str | None) -> set[str] | None:
    if types is None:
        return None
    if isinstance(types, str):
        return {types}
    return set(types)


def _normalise_distances(
    distances: Sequence[int] | tuple[int, int] | str | int | None,
) -> tuple[int, int] | None:
    """Normalise a ring filter to an inclusive ``(low, high)`` pair."""
    if distances is None:
        return None
    if isinstance(distances, int) and not isinstance(distances, bool):
        return distances, distances
    if isinstance(distances, str):
        left, sep, right = distances.partition(":")
        if not sep:
            raise BreakdownError(
                f"invalid distance range '{distances}' (expected A:B)"
            )
        try:
            low, high = int(left), int(right)
        except ValueError as exc:
            raise BreakdownError(
                f"invalid distance range '{distances}' (expected integers A:B)"
            ) from exc
        distances = (low, high)
    values = list(distances)
    if len(values) == 1:
        values = [values[0], values[0]]
    if len(values) != 2:
        raise BreakdownError("invalid distance range (expected A:B)")
    low, high = int(values[0]), int(values[1])
    if low > high:
        raise BreakdownError(
            f"invalid distance range {low}:{high} (A must be <= B)"
        )
    return low, high


def graph_view(
    graph: Graph,
    anchor: str | int | None,
    *,
    depth: int | None = None,
    distance: Sequence[int] | tuple[int, int] | str | int | None = None,
    types: Iterable[str] | str | None = None,
) -> list[str]:
    """The anchor's undirected component, walked outward in rings.

    ``types`` restricts which authored links are traversed.  ``distance A:B`` is
    a display-only filter: out-of-range nodes are omitted from the result but
    traversal still continues through them, so a later in-range ring stays
    reachable.  The anchor is always included, and every node appears once at
    its minimum ring.
    """
    if depth is not None and depth < 0:
        raise BreakdownError(f"invalid depth {depth} (must be non-negative)")
    target = default_anchor(graph) if anchor is None else resolve_graph_ref(graph, anchor)
    if target is None:
        raise BreakdownError("store has no graph nodes")
    if target not in graph.store.nodes:
        raise BreakdownError(f"anchor '{target}' does not exist")
    type_set = _normalise_types(types)
    window = _normalise_distances(distance)

    included: list[str] = []
    seen: set[str] = set()
    level: dict[str, int] = {target: 0}
    queue: list[str] = [target]
    head = 0
    while head < len(queue):
        current = queue[head]
        head += 1
        if current in seen or current not in graph.store.nodes:
            continue
        seen.add(current)
        current_level = level[current]
        if (
            window is None
            or current == target
            or window[0] <= current_level <= window[1]
        ):
            included.append(current)
        if depth is not None and current_level >= depth:
            continue
        for neighbor in graph.store.neighbors(current):
            if type_set is not None and neighbor.link.type not in type_set:
                continue
            if neighbor.ref in seen or neighbor.ref not in graph.store.nodes:
                continue
            level.setdefault(neighbor.ref, current_level + 1)
            queue.append(neighbor.ref)
    return included


# ---------------------------------------------------------------------------
# Text and DOT rendering


def _link_text(link: Link) -> str:
    return f"{link.to} ({link.type})"


def _identity(ref: str, graph: Graph) -> tuple[int, int]:
    node = graph.store.nodes[ref]
    return node.id, node.version


def _ring_sections(
    graph: Graph, refs: Iterable[str]
) -> list[tuple[str, list[str]]]:
    """Ordered ``(heading, refs)`` sections: ring 0, ring 1 split, then rings."""
    anchor = default_anchor(graph)
    selected = [ref for ref in refs if ref in graph.store.nodes]
    if not selected:
        return []
    distance = graph.distance or {}
    kinds: dict[str, str] = {}
    link_types: dict[str, str] = {}
    if anchor is not None and anchor in graph.store.nodes:
        for neighbor in graph.store.neighbors(anchor):
            kinds[neighbor.ref] = neighbor.kind
            link_types[neighbor.ref] = neighbor.link.type

    ring0: list[str] = []
    split: dict[str, list[str]] = {"child": [], "parent": []}
    higher: dict[int, list[str]] = defaultdict(list)
    other: list[str] = []
    for ref in selected:
        if ref == anchor:
            ring0.append(ref)
            continue
        level = distance.get(ref)
        if level is None:
            other.append(ref)
        elif level == 1:
            split.setdefault(kinds.get(ref, "child"), []).append(ref)
        else:
            higher[level].append(ref)

    sections: list[tuple[str, list[str]]] = []
    if ring0:
        sections.append(
            (f"## 0 — {anchor}", sorted(ring0, key=lambda ref: _identity(ref, graph)))
        )
    for kind in ("child", "parent"):
        members = sorted(
            split[kind],
            key=lambda ref: (
                link_types.get(ref, ""),
                *_identity(ref, graph),
            ),
        )
        if members:
            sections.append((f"## 1 — {_KIND_NOUN[kind]}", members))
    for level in sorted(higher):
        sections.append(
            (
                f"## {level}",
                sorted(higher[level], key=lambda ref: _identity(ref, graph)),
            )
        )
    if other:
        sections.append(
            ("## other", sorted(other, key=lambda ref: _identity(ref, graph)))
        )
    return sections


def render_graph(graph: Graph, refs: Iterable[str]) -> str:
    """Text render: ``## <ring>`` headings, with ring 1 split by direction."""
    lines: list[str] = []
    for heading, members in _ring_sections(graph, refs):
        lines.append(heading)
        for ref in members:
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


# Subtle (fill, border) pairs, cycled by value.  Fixed so the DOT is
# deterministic.
_DOT_PALETTE = (
    ("#eef4fb", "#9bb7d4"),
    ("#f1f7ee", "#a9c59b"),
    ("#fbf4e8", "#d4b483"),
    ("#f6eef6", "#b79bb7"),
    ("#eef7f7", "#94c0c0"),
    ("#f4f1ea", "#bdb29b"),
)
_DOT_TITLE_LIMIT = 48

# Graphviz node shapes, cycled by value.  Fixed so the DOT is deterministic.
_SHAPE_PALETTE = (
    "box",
    "ellipse",
    "diamond",
    "hexagon",
    "octagon",
    "note",
    "tab",
    "component",
    "folder",
    "box3d",
    "cylinder",
    "parallelogram",
)


def _short_title(title: str, limit: int = _DOT_TITLE_LIMIT) -> str:
    """Collapse whitespace and truncate so a DOT box stays readable."""
    text = " ".join(title.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _dot_value(node: Node, color_by: str) -> str:
    value = node.meta.get(color_by)
    return "" if value is None else str(value)


def render_dot(
    graph: Graph,
    refs: Iterable[str],
    *,
    color_by: str = "type",
    shape_by: str | None = None,
) -> str:
    """Graphviz DOT: flat nodes coloured and shaped by front-matter keys.

    Nodes are drawn flat, with no clusters inferred.  Only authored out-edges
    inside the view are rendered, each labelled with its link type.  ``color_by``
    defaults to ``type``; ``shape_by`` is opt-in and defaults to a box.
    """
    selected = [ref for ref in refs if ref in graph.store.nodes]
    selected.sort(
        key=lambda ref: (
            graph.distance.get(ref, 0),
            *_identity(ref, graph),
        )
    )
    values = sorted({_dot_value(graph.store.nodes[ref], color_by) for ref in selected})
    color_index = {value: index for index, value in enumerate(values)}
    shape_index: dict[str, int] = {}
    if shape_by:
        shape_values = sorted(
            {
                value
                for ref in selected
                if (value := _dot_value(graph.store.nodes[ref], shape_by))
            }
        )
        shape_index = {value: index for index, value in enumerate(shape_values)}

    lines = [
        "digraph bd_graph {",
        "  rankdir=LR;",
        (
            "  graph [fontname=\"Helvetica\", fontsize=11, bgcolor=\"white\", "
            "pad=\"0.3\", nodesep=\"0.35\", ranksep=\"0.9\"];"
        ),
        (
            "  node [shape=box, style=\"rounded,filled\", fontname=\"Helvetica\", "
            "fontsize=10, color=\"#4a4a4a\", fillcolor=\"white\", "
            "margin=\"0.12,0.08\"];"
        ),
        (
            "  edge [fontname=\"Helvetica\", fontsize=9, color=\"#555555\", "
            "fontcolor=\"#333333\"];"
        ),
    ]
    for ref in selected:
        node = graph.store.nodes[ref]
        fill, _border = _DOT_PALETTE[
            color_index[_dot_value(node, color_by)] % len(_DOT_PALETTE)
        ]
        node_label = _dot_quote(f"{ref}\n{_short_title(node.title)}")
        shape = "box"
        if shape_by:
            value = _dot_value(node, shape_by)
            if value in shape_index:
                shape = _SHAPE_PALETTE[shape_index[value] % len(_SHAPE_PALETTE)]
        lines.append(
            f"    {_dot_quote(ref)} [label={node_label}, shape={shape}, "
            f"fillcolor={_dot_quote(fill)}];"
        )
    wanted = set(selected)
    edges = sorted(
        {
            (source, link.to, link.type)
            for source in selected
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


def render_svg(
    graph: Graph,
    refs: Iterable[str],
    *,
    color_by: str = "type",
    shape_by: str | None = None,
) -> str:
    """Render :func:`render_dot` to SVG through the Graphviz ``dot`` binary.

    No Python dependency: the DOT text is piped to ``dot -Tsvg``.  A missing
    binary or a non-zero exit raises :class:`BreakdownError` with the stderr.
    """
    dot_path = shutil.which("dot")
    if dot_path is None:
        raise BreakdownError(
            "Graphviz 'dot' not found; install Graphviz or use 'bd graph --format dot'"
        )
    try:
        completed = subprocess.run(
            [dot_path, "-Tsvg"],
            input=render_dot(graph, refs, color_by=color_by, shape_by=shape_by),
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise BreakdownError(f"failed to run Graphviz 'dot': {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or "(no stderr)"
        raise BreakdownError(
            f"Graphviz 'dot' failed (exit {completed.returncode}): {detail}"
        )
    return completed.stdout


def render_out(graph: Graph, ref: str | int) -> str:
    """The declared out-links of ``ref``, sorted."""
    target = resolve_graph_ref(graph, ref)
    if target not in graph.store.nodes:
        raise BreakdownError(f"unknown ref '{target}'")
    links = sorted(graph.out.get(target, ()), key=_edge_key)
    lines = [f"{target} -> {_link_text(link)}" for link in links]
    if not lines:
        return f"{target} -> (no declared out-links)"
    return "\n".join(lines)


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


def audit(
    graph: Graph, view: str | int | View | None = None, anchor: str | int | None = None
) -> list[Issue]:
    """Collect graph issues; cycles and authored order are never errors.

    Kept: dangling targets, ``graph-orphan`` (a node outside the anchor's
    component), duplicate reachable versions, and the source-level issues
    already collected by the loader/checker.  No cycle or back-edge issue is
    emitted.
    """
    issues: list[Issue] = list(graph.issues)

    if anchor is None:
        anchor = view.ref if isinstance(view, View) else view

    nodes = sorted(
        graph.store.nodes, key=lambda ref: _ref_key(graph.store.nodes[ref])
    )
    for ref in nodes:
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

    if anchor is None:
        anchor_ref = default_anchor(graph)
    else:
        anchor_ref = resolve_graph_ref(graph, anchor)
        if anchor_ref not in graph.store.nodes:
            raise BreakdownError(f"anchor '{anchor_ref}' does not exist")

    if anchor_ref is not None and anchor_ref not in graph.store.nodes:
        issues.append(
            Issue(
                "error",
                "root-ref-missing",
                f"root ref '{anchor_ref}' does not exist",
                node=anchor_ref,
            )
        )

    if anchor_ref is not None and anchor_ref in graph.store.nodes:
        component = set(ring_distances(graph.store, anchor_ref))
        for ref in nodes:
            if ref not in component:
                issues.append(
                    Issue(
                        "warning",
                        "graph-orphan",
                        f"node '{ref}' is not in the default component",
                        node=ref,
                    )
                )
        versions: dict[int, list[str]] = defaultdict(list)
        for ref in sorted(component, key=lambda r: _ref_key(graph.store.nodes[r])):
            versions[graph.store.nodes[ref].id].append(ref)
        for node_id in sorted(versions):
            reachable = versions[node_id]
            if len(reachable) > 1:
                issues.append(
                    Issue(
                        "warning",
                        "graph-duplicate-version",
                        f"id {node_id} has {len(reachable)} versions reachable from "
                        f"{anchor_ref}: "
                        + ", ".join(sorted(reachable, key=_text_ref_key)),
                        node=min(reachable, key=_text_ref_key),
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
    return issues


def render_audit(
    graph: Graph, view: str | int | View | None = None, anchor: str | int | None = None
) -> str:
    """Issues grouped error/warning, then a one-line summary."""
    issues = audit(graph, view, anchor)
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
# Layout and export


def _template_fields(graph: Graph, node: Node) -> dict[str, str]:
    fields = {
        key: "" if value is None else str(value)
        for key, value in node.meta.items()
    }
    fields.update(
        {
            "ref": node.ref,
            "id": str(node.id),
            "version": str(node.version),
            "slug": slugify(node.title) or node.ref,
            "title": node.title,
            "distance": str(graph.distance.get(node.ref, "")),
        }
    )
    return fields


def _path_problem(path: Path) -> str | None:
    problem = path_problem(path.as_posix())
    if problem:
        return problem
    if path.name in RESERVED:
        return f"collides with generated '{path.name}'"
    return None


def layout_paths(graph: Graph, template: str | None = None) -> dict[str, Path]:
    """Flat materialization: one path per node, using its store file basename.

    On a basename collision the ref is appended to the stem.  With ``template``
    the placeholders are ``{ref} {id} {version} {slug} {title} {distance}`` plus
    any front-matter key; the layout is always flat.
    """
    paths: dict[str, Path] = {}
    used: set[str] = set()
    for ref in sorted(
        graph.store.nodes, key=lambda r: _ref_key(graph.store.nodes[r])
    ):
        node = graph.store.nodes[ref]
        if template is None:
            candidate = node.path.name
        else:
            try:
                candidate = template.format_map(_template_fields(graph, node))
            except KeyError as exc:
                raise ExportError(
                    f"path template '{template}' uses unknown field "
                    f"{exc.args[0]!r}"
                ) from None
            except (ValueError, IndexError) as exc:
                raise ExportError(
                    f"invalid path template '{template}': {exc}"
                ) from None
        path = Path(candidate)
        problem = _path_problem(path)
        if problem:
            raise ExportError(
                f"node {ref} resolves to invalid path '{candidate}': {problem}"
            )
        if path.as_posix() in used:
            stem, suffix = path.stem, path.suffix
            path = path.with_name(f"{stem}-{ref}{suffix}")
            counter = 1
            while path.as_posix() in used:
                counter += 1
                path = path.with_name(f"{stem}-{ref}-{counter}{suffix}")
            problem = _path_problem(path)
            if problem:
                raise ExportError(
                    f"node {ref} resolves to invalid path "
                    f"'{path.as_posix()}': {problem}"
                )
        used.add(path.as_posix())
        paths[ref] = path
    return paths


def _ring_index(
    graph: Graph, anchor: str, refs: Iterable[str], paths: dict[str, Path]
) -> str:
    lines = [BANNER, "", f"# Graph {anchor}", ""]
    for heading, members in _ring_sections(graph, refs):
        lines.append(heading)
        for ref in members:
            node = graph.store.nodes[ref]
            lines.append(
                f"- [{ref} {node.title}]({paths[ref].as_posix()})"
            )
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def export_graph(
    graph: Graph | View,
    anchor: str | Path,
    out: Path | None = None,
    *,
    path_template: str | None = None,
    force: bool = False,
    clean: bool = False,
) -> ExportResult:
    """Write a flat, read-only graph snapshot with one ring-section index."""
    if isinstance(graph, View):
        store = graph.store
        target = graph.ref
        destination = Path(anchor)
    else:
        store = graph.store
        if out is None:
            raise ExportError("export graph needs an output directory")
        target = resolve_graph_ref(graph, anchor)
        destination = Path(out)

    built = build_graph(store, anchor=target)
    refs = graph_view(built, target)
    _prepare_out(destination, force=force, clean=clean)

    paths = layout_paths(built, path_template)
    files: list[Path] = []
    for ref in refs:
        node = built.store.nodes[ref]
        dest = destination / paths[ref]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            render_document(node.meta, node.body),
            encoding="utf-8",
            newline="",
        )
        files.append(dest)

    root_index = destination / "INDEX.md"
    root_index.write_text(
        _ring_index(built, target, refs, paths),
        encoding="utf-8",
        newline="",
    )
    files.append(root_index)
    return ExportResult("graph", destination, len(refs), files)
