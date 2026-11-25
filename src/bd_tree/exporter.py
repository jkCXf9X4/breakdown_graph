"""Export link-closure views.  Registry via ``@exporter``.

Everything display-related comes from front-matter fields chosen on the command
line: paths from the flat ring layout or a template, titles and summaries from
configurable keys, dot colours and shapes from arbitrary fields.  No folder or
link-type names live here.
"""

from __future__ import annotations

import shutil
import subprocess
from collections import defaultdict
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from .errors import ExportError
from .freshness import stale_edge_list
from .frontmatter import render_document
from .model import ExportResult, Node, StaleEdge, View

Exporter = Callable[..., ExportResult]
EXPORTERS: dict[str, Exporter] = {}

BANNER = "<!-- GENERATED FILE — do not edit. Regenerate with `bd export {name}`. -->"

DEFAULT_COLOR = "#eeeeee"
DEFAULT_EDGE = ("solid", "#555555", "1.0")

# Stable palettes: index by the sorted distinct field values, never by name.
COLOR_PALETTE: tuple[str, ...] = (
    "#f3d9a4",
    "#f4b6b6",
    "#c9d7f0",
    "#c7e6c7",
    "#e2d4f0",
    "#bfe4e4",
    "#dcdcdc",
    "#f0d0a0",
    "#e6e0b0",
    "#d4e6c7",
    "#f5cfd8",
    "#cfe0f5",
)
SHAPE_PALETTE: tuple[str, ...] = (
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
EDGE_COLORS: tuple[str, ...] = (
    "#333333",
    "#1f5fa8",
    "#7a4fa0",
    "#b00020",
    "#8a6d3b",
    "#555555",
)
EDGE_LINESTYLES: tuple[str, ...] = ("solid", "dashed", "dotted")


def exporter(name: str) -> Callable[[Exporter], Exporter]:
    def register(func: Exporter) -> Exporter:
        EXPORTERS[name] = func
        return func

    return register


def _prepare_out(out: Path, *, force: bool, clean: bool) -> None:
    if clean and out.exists():
        if out.is_dir():
            shutil.rmtree(out)
        else:
            out.unlink()
    if out.exists():
        if not out.is_dir():
            raise ExportError(f"output '{out}' exists and is not a directory")
        if any(out.iterdir()) and not force:
            raise ExportError(
                f"refusing non-empty output directory '{out}' (use --force or --clean)"
            )
    else:
        out.mkdir(parents=True)


def _text(value: object) -> str:
    return "" if value is None else str(value)


def _build_paths(
    view: View,
    template: str | None,
    refs: Iterable[str],
    *,
    reserved: frozenset[str] = frozenset(),
    graph: Any | None = None,
) -> dict[str, str]:
    """Resolve the flat materialization for ``refs`` from one anchored graph.

    ``graph`` is the anchored :class:`~.graph.Graph` when the caller already has
    one; otherwise it is built with this view's ref as the anchor.  The path
    source is :func:`bd_tree.graph.layout_paths`: the store file basename, or
    the template, with a ``-<ref>`` suffix on a collision.
    """
    # Imported lazily: graph.py imports this module's banner and helpers.
    from .graph import build_graph, layout_paths

    if graph is None:
        graph = build_graph(view.store, anchor=view.ref)
    resolved = layout_paths(graph, template)
    paths: dict[str, str] = {}
    for ref in refs:
        path = resolved[ref].as_posix()
        # Generated names are reserved in every directory: a node may never
        # resolve to a file such as ``INDEX.md`` or ``AGENTS.md``.
        if path.rsplit("/", 1)[-1] in reserved:
            raise ExportError(f"node {ref} path collides with generated '{path}'")
        paths[ref] = path
    return paths


def _write_node(out: Path, node: Node, path: str) -> Path:
    dest = out / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(render_document(node.meta, node.body), encoding="utf-8", newline="")
    return dest


def _display(node: Node, field: str, fallback: str) -> str:
    value = node.meta.get(field)
    if value in (None, ""):
        return fallback
    return str(value)


def _nodes_pointer(nodes_link: str) -> str:
    """A link from a generated index to the store's real node folder."""
    return (
        f"_Real node files: [nodes/]({nodes_link}/) — open, copy, or delete the "
        "store files there._"
    )


def _node_entry(
    node: Node,
    label: str,
    target: str,
    *,
    indent: str = "",
    summary: str = "",
    nodes_link: str | None = None,
) -> str:
    """One index entry: the view link, then a direct link to the real file."""
    line = f"{indent}- [{label}]({target})"
    if nodes_link is not None:
        line += f" — [real file]({nodes_link}/{node.path.name})"
    if summary:
        line += f" — {summary}"
    return line


_KIND_NOUN = {"child": "children", "parent": "parents"}
_KIND_ORDER = ("child", "parent")


def _identity(graph: Any, ref: str) -> tuple[int, int]:
    node = graph.store.nodes[ref]
    return node.id, node.version


def _ring_layout(
    graph: Any, refs: Iterable[str]
) -> list[tuple[str, str, list[str]]]:
    """Ordered ring sections: ``(heading, kind, members)`` for a flat view.

    Ring 0 is ``Active``; ring 1 splits into children and parents by the
    anchor's authored direction; deeper rings are one ``Distance N`` section.
    Every list is sorted by ``(distance, kind_rank, link type, id, version)``.
    """
    store = graph.store
    anchor = graph.anchor or store.root_ref
    distance = graph.distance or {}
    selected = [ref for ref in refs if ref in store.nodes]
    kinds: dict[str, str] = {}
    link_types: dict[str, str] = {}
    if anchor is not None and anchor in store.nodes:
        for neighbor in store.neighbors(anchor):
            kinds[neighbor.ref] = neighbor.kind
            link_types[neighbor.ref] = neighbor.link.type

    ring0: list[str] = []
    split: dict[str, list[str]] = {kind: [] for kind in _KIND_ORDER}
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

    sections: list[tuple[str, str, list[str]]] = []
    if ring0:
        sections.append(
            (
                "## Active",
                "active",
                sorted(ring0, key=lambda ref: _identity(graph, ref)),
            )
        )
    for kind in _KIND_ORDER:
        members = sorted(
            split[kind],
            key=lambda ref: (link_types.get(ref, ""), *_identity(graph, ref)),
        )
        if members:
            sections.append((f"## Distance 1 — {_KIND_NOUN[kind]}", kind, members))
    for level in sorted(higher):
        sections.append(
            (
                f"## Distance {level}",
                "",
                sorted(higher[level], key=lambda ref: _identity(graph, ref)),
            )
        )
    if other:
        sections.append(
            (
                "## Other",
                "",
                sorted(other, key=lambda ref: _identity(graph, ref)),
            )
        )
    return sections


def _graph_index_text(
    view: View,
    paths: dict[str, str],
    title_field: str,
    summary_field: str,
    *,
    graph: Any | None = None,
    banner: str | None = None,
    label: str | None = None,
    nodes_link: str | None = None,
) -> str:
    """Root index for a flat ring view: ring sections, split at ring 1."""
    from .graph import build_graph

    if graph is None:
        graph = build_graph(view.store, anchor=view.ref)
    lines: list[str] = []
    if nodes_link is not None:
        lines.extend(["---", f"nodes: {nodes_link}", "---", ""])
    lines.extend(
        [
            banner if banner is not None else BANNER.format(name="graph"),
            "",
            f"# View {view.ref if label is None else label}",
            "",
        ]
    )
    if nodes_link is not None:
        lines.extend([_nodes_pointer(nodes_link), ""])
    sections = _ring_layout(graph, view.nodes)
    if not sections:
        lines.append("_No nodes in this view._")
    for heading, _kind, members in sections:
        lines.extend([heading, ""])
        for ref in members:
            node = view.nodes[ref]
            title = _display(node, title_field, node.ref)
            summary = _display(node, summary_field, "")
            lines.append(
                _node_entry(
                    node,
                    title,
                    paths[ref],
                    summary=summary,
                    nodes_link=nodes_link,
                )
            )
        lines.append("")
    return "\n".join(lines)


def _directory_indexes(
    view: View,
    paths: dict[str, str],
    title_field: str,
    summary_field: str,
    *,
    graph: Any | None = None,
    banner: str | None = None,
    label: str | None = None,
    nodes_link: str | None = None,
) -> dict[str, str]:
    """Generated index text for the output root only.

    The flat ring layout has no node directories, so there is exactly one
    ``INDEX.md``.  ``nodes_link``, when given, is the path from the output root
    to the store's ``nodes/`` folder; the index carries it in front matter and
    as a clickable link back to the real files.
    """
    return {
        "": _graph_index_text(
            view,
            paths,
            title_field,
            summary_field,
            graph=graph,
            banner=banner,
            label=label,
            nodes_link=nodes_link,
        )
    }


def _write_indexes(out: Path, indexes: dict[str, str]) -> list[Path]:
    """Write every directory index and drop indexes no longer in the view."""
    files: list[Path] = []
    keep: set[Path] = set()
    for directory in sorted(indexes):
        path = out / directory / "INDEX.md" if directory else out / "INDEX.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(indexes[directory], encoding="utf-8", newline="")
        keep.add(path)
        files.append(path)
    for stale in sorted(out.rglob("INDEX.md")):
        if stale in keep:
            continue
        if stale.is_symlink() or stale.is_file():
            stale.unlink()
    return files


def _stale_section(
    node: Node, edges: list[StaleEdge], title_field: str
) -> list[str]:
    lines = [f"## {node.ref} — {_display(node, title_field, node.ref)}", ""]
    for edge in edges:
        if edge.state == "untracked":
            lines.append(
                f"- upstream: `{edge.target}` ({edge.type}) — untracked, "
                f"body is {edge.current}"
            )
        else:
            lines.append(
                f"- upstream: `{edge.target}` ({edge.type}) — target body changed "
                f"({edge.pinned} -> {edge.current})"
            )
    lines.append("- reason: a propagating edge is stale or untracked")
    lines.append("- action: re-derive this node from its upstream")
    lines.append("")
    return lines


@exporter("context")
def export_context(
    view: View,
    out: Path,
    *,
    path_template: str | None = None,
    title_field: str = "title",
    summary_field: str = "summary",
    force: bool = False,
    clean: bool = False,
) -> ExportResult:
    """Write only fresh nodes, plus STALE.md and AGENTS.md. No stale bodies leak."""
    out = Path(out)
    _prepare_out(out, force=force, clean=clean)
    all_stale = stale_edge_list(view)
    excluded_ids = sorted({edge.source for edge in all_stale})
    excluded = set(excluded_ids)
    included = [
        ref
        for ref in sorted(view.nodes, key=lambda r: (view.nodes[r].id, view.nodes[r].version))
        if ref not in excluded
    ]
    paths = _build_paths(
        view,
        path_template,
        included,
        reserved=frozenset({"AGENTS.md", "STALE.md"}),
    )
    files: list[Path] = []
    for ref in included:
        files.append(_write_node(out, view.nodes[ref], paths[ref]))

    stale_lines = [
        BANNER.format(name="context"),
        "",
        "# Stale context — open questions",
        "",
        (
            "These nodes are excluded because a propagating edge is stale or "
            "untracked. They are listed as open questions; their bodies are "
            "deliberately absent."
        ),
        "",
    ]
    if excluded_ids:
        for node_id in excluded_ids:
            edges = [edge for edge in all_stale if edge.source == node_id]
            stale_lines.extend(_stale_section(view.nodes[node_id], edges, title_field))
    else:
        stale_lines.extend(["_None._", ""])
    stale_path = out / "STALE.md"
    stale_path.write_text("\n".join(stale_lines), encoding="utf-8", newline="")
    files.append(stale_path)

    agents = [
        f"# Context for view `{view.ref}`",
        "",
        (
            "This directory is the complete context for this view. Every node "
            "required for the task is present here."
        ),
        "",
        (
            "Do not read files outside this directory. If something seems missing, "
            "it was excluded as stale; consult STALE.md and re-derive it upstream "
            "instead."
        ),
        "",
        (
            f"Nodes included: {len(included)}. "
            f"Nodes excluded as stale: {len(excluded)}."
        ),
        "",
    ]
    agents_path = out / "AGENTS.md"
    agents_path.write_text("\n".join(agents), encoding="utf-8", newline="")
    files.append(agents_path)
    return ExportResult("context", out, len(included), files)


def _quote(text: str) -> str:
    escaped = (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return '"' + escaped + '"'


def _value_map(
    nodes: Iterable[Node], field: str | None
) -> dict[str, int]:
    if not field:
        return {}
    values = {
        _text(node.meta.get(field))
        for node in nodes
        if node.meta.get(field) not in (None, "")
    }
    return {value: index for index, value in enumerate(sorted(values))}


def _dot_text(view: View, color_by: str | None, shape_by: str | None) -> str:
    nodes = list(view.nodes.values())
    if color_by is None:
        color_by = "type"
    color_index = _value_map(nodes, color_by)
    shape_index = _value_map(nodes, shape_by)

    edges = [edge for edge in view.edges if edge.target in view.nodes]
    edge_types = sorted({edge.type for edge in edges})
    edge_style = {name: index for index, name in enumerate(edge_types)}

    lines = [
        "digraph bd_tree {",
        "  rankdir=LR;",
        '  graph [fontname="Helvetica"];',
        '  node [fontname="Helvetica", fontsize=10, style="filled"];',
        '  edge [fontname="Helvetica", fontsize=8];',
    ]
    for node in sorted(nodes, key=lambda n: (n.id, n.version)):
        if color_by:
            index = color_index.get(_text(node.meta.get(color_by)))
            colour = (
                COLOR_PALETTE[index % len(COLOR_PALETTE)]
                if index is not None
                else DEFAULT_COLOR
            )
        else:
            colour = DEFAULT_COLOR
        if shape_by:
            index = shape_index.get(_text(node.meta.get(shape_by)))
            shape = (
                SHAPE_PALETTE[index % len(SHAPE_PALETTE)]
                if index is not None
                else "box"
            )
        else:
            shape = "box"
        label = f"{node.ref}\n{node.title}"
        if len(label) > 80:
            label = label[:77] + "..."
        lines.append(
            f"  {_quote(node.ref)} [shape={shape}, fillcolor={_quote(colour)}, "
            f"label={_quote(label)}];"
        )
    for edge in edges:
        index = edge_style.get(edge.type, 0)
        style = EDGE_LINESTYLES[index % len(EDGE_LINESTYLES)] if edge_types else DEFAULT_EDGE[0]
        colour = (
            EDGE_COLORS[index % len(EDGE_COLORS)] if edge_types else DEFAULT_EDGE[1]
        )
        width = DEFAULT_EDGE[2]
        lines.append(
            f"  {_quote(edge.source)} -> {_quote(edge.target)} "
            f"[label={_quote(edge.type)}, style={style}, color={_quote(colour)}, "
            f"penwidth={width}];"
        )
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def _run_dot(dot_text: str, fmt: str) -> bytes:
    dot_path = shutil.which("dot")
    if dot_path is None:
        raise ExportError(
            f"Graphviz 'dot' not found; install Graphviz to render {fmt}"
        )
    try:
        completed = subprocess.run(
            [dot_path, f"-T{fmt}"],
            input=dot_text.encode("utf-8"),
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise ExportError(f"failed to run Graphviz 'dot': {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", "replace").strip()
        raise ExportError(
            f"Graphviz 'dot' failed (exit {completed.returncode}): "
            f"{detail or 'no diagnostic'}"
        )
    return completed.stdout


@exporter("dot")
def export_dot(
    view: View,
    out: Path,
    *,
    color_by: str | None = None,
    shape_by: str | None = None,
    render: list[str] | None = None,
    render_out: str | None = None,
    force: bool = False,
    clean: bool = False,
) -> ExportResult:
    """Write a Graphviz graph, optionally rendering it with Graphviz."""
    out = Path(out)
    if out.exists() and out.is_dir():
        raise ExportError(f"output '{out}' is a directory")
    out.parent.mkdir(parents=True, exist_ok=True)

    text = _dot_text(view, color_by, shape_by)
    out.write_text(text, encoding="utf-8", newline="")
    files = [out]

    formats = list(render or [])
    if render_out is not None and len(formats) != 1:
        raise ExportError("--render-out requires exactly one --render format")
    for fmt in formats:
        destination = (
            Path(render_out) if render_out is not None else out.with_suffix(f".{fmt}")
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(_run_dot(text, fmt))
        files.append(destination)
    return ExportResult("dot", out, len(view.nodes), files)


@exporter("svg")
def export_svg(
    view: View,
    out: Path,
    *,
    color_by: str | None = None,
    shape_by: str | None = None,
    force: bool = False,
    clean: bool = False,
) -> ExportResult:
    """Render one view to SVG with Graphviz."""
    out = Path(out)
    if out.exists() and out.is_dir():
        raise ExportError(f"output '{out}' is a directory")
    out.parent.mkdir(parents=True, exist_ok=True)

    text = _dot_text(view, color_by, shape_by)
    out.write_bytes(_run_dot(text, "svg"))
    return ExportResult("svg", out, len(view.nodes), [out])
