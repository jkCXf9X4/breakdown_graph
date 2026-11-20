"""Export containment views.  Registry via ``@exporter``.

Everything display-related comes from front-matter fields chosen on the command
line: paths from a template, titles and summaries from configurable keys, dot
colours and shapes from arbitrary fields.  No layer or link-type names live
here.
"""

from __future__ import annotations

import re
import shutil
import unicodedata
from pathlib import Path
from typing import Callable, Iterable

from .checker import path_problem
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


def slugify(text: str) -> str:
    """Lowercase ASCII filename stem; non-ASCII and punctuation collapse to ``-``."""
    normalised = unicodedata.normalize("NFKD", text).lower()
    ascii_text = "".join(
        char if char.isascii() else "-"
        for char in normalised
        if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")


def _placement_name(node: Node) -> str:
    """Explicit ``name``, else the title slug, else the ref."""
    return node.name or slugify(node.title) or node.ref


def _template_fields(node: Node) -> dict[str, str]:
    fields = {key: _text(value) for key, value in node.meta.items()}
    fields.update(
        {
            "ref": node.ref,
            "id": str(node.id),
            "version": str(node.version),
            "home": node.home or "",
            "folder": node.folder or "",
            "name": _placement_name(node),
            "slug": _placement_name(node),
        }
    )
    return fields


def _validated_path(node: Node, path: str) -> str:
    problem = path_problem(path)
    if problem:
        raise ExportError(
            f"node {node.ref} resolves to invalid path '{path}': {problem}"
        )
    return path


def render_path(node: Node, template: str) -> str:
    try:
        path = template.format_map(_template_fields(node))
    except KeyError as exc:
        raise ExportError(
            f"path template '{template}' uses unknown field {exc.args[0]!r}"
        ) from None
    except (ValueError, IndexError) as exc:
        raise ExportError(f"invalid path template '{template}': {exc}") from None
    return _validated_path(node, path)


def _default_path(node: Node) -> str:
    """One placement rule: ``home``, then ``folder``/``name``, then ``<ref>.md``."""
    if node.home:
        return _validated_path(node, node.home)
    if node.folder or node.name:
        parts = [part for part in (node.folder, _placement_name(node)) if part]
        return _validated_path(node, "/".join(parts) + ".md")
    return _validated_path(node, f"{node.ref}.md")


def _build_paths(
    view: View,
    template: str | None,
    refs: Iterable[str],
    *,
    reserved: frozenset[str] = frozenset(),
) -> dict[str, str]:
    paths: dict[str, str] = {}
    used: dict[str, str] = {}
    for ref in refs:
        node = view.nodes[ref]
        path = render_path(node, template) if template else _default_path(node)
        if path in reserved:
            raise ExportError(f"node {ref} path collides with generated '{path}'")
        previous = used.get(path)
        if previous is not None:
            raise ExportError(
                f"nodes {previous} and {ref} both resolve to path '{path}'"
            )
        for other, other_ref in used.items():
            if path.startswith(other + "/") or other.startswith(path + "/"):
                raise ExportError(
                    f"nodes {other_ref} and {ref} resolve to conflicting paths "
                    f"'{other}' and '{path}'"
                )
        used[path] = ref
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


def _index_text(
    view: View,
    paths: dict[str, str],
    title_field: str,
    summary_field: str,
    *,
    banner: str | None = None,
) -> str:
    lines = [
        banner if banner is not None else BANNER.format(name="tree"),
        "",
        f"# View {view.ref}",
        "",
    ]
    emitted: set[str] = set()

    def walk(ref: str, depth: int) -> None:
        if ref in emitted or ref not in view.nodes:
            return
        emitted.add(ref)
        node = view.nodes[ref]
        title = _display(node, title_field, node.ref)
        summary = _display(node, summary_field, "")
        indent = "  " * depth
        suffix = f" — {summary}" if summary else ""
        lines.append(f"{indent}- [{title}]({paths[ref]}){suffix}")
        for child in view.store.effective_contains(ref):
            walk(child, depth + 1)

    walk(view.ref, 0)
    for ref in sorted(view.nodes, key=lambda r: (view.nodes[r].id, view.nodes[r].version)):
        if ref not in emitted:
            walk(ref, 0)
    if not view.nodes:
        lines.append("_No nodes in this view._")
    lines.append("")
    return "\n".join(lines)


@exporter("tree")
def export_tree(
    view: View,
    out: Path,
    *,
    path_template: str | None = None,
    title_field: str = "title",
    summary_field: str = "summary",
    force: bool = False,
    clean: bool = False,
) -> ExportResult:
    """Write every view node at its templated path plus one INDEX.md."""
    out = Path(out)
    _prepare_out(out, force=force, clean=clean)
    refs = sorted(view.nodes, key=lambda r: (view.nodes[r].id, view.nodes[r].version))
    paths = _build_paths(
        view, path_template, refs, reserved=frozenset({"INDEX.md"})
    )
    files: list[Path] = []
    for ref in refs:
        files.append(_write_node(out, view.nodes[ref], paths[ref]))
    index_path = out / "INDEX.md"
    index_path.write_text(
        _index_text(view, paths, title_field, summary_field),
        encoding="utf-8",
        newline="",
    )
    files.append(index_path)
    return ExportResult("tree", out, len(refs), files)


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
        "These nodes are excluded because a propagating edge is stale or untracked. "
        "They are listed as open questions; their bodies are deliberately absent.",
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
        "This directory is the complete context for this view. Every node required "
        "for the task is present here.",
        "",
        "Do not read files outside this directory. If something seems missing, it was "
        "excluded as stale; consult STALE.md and re-derive it upstream instead.",
        "",
        f"Nodes included: {len(included)}. "
        f"Nodes excluded as stale: {len(excluded)}.",
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


@exporter("dot")
def export_dot(
    view: View,
    out: Path,
    *,
    color_by: str | None = None,
    shape_by: str | None = None,
    force: bool = False,
    clean: bool = False,
) -> ExportResult:
    """Write a Graphviz graph with field-driven colours and shapes."""
    out = Path(out)
    if out.exists() and out.is_dir():
        raise ExportError(f"output '{out}' is a directory")
    out.parent.mkdir(parents=True, exist_ok=True)

    nodes = list(view.nodes.values())
    if color_by is None and any(node.meta.get("layer") not in (None, "") for node in nodes):
        color_by = "layer"
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
    out.write_text("\n".join(lines), encoding="utf-8", newline="")
    return ExportResult("dot", out, len(nodes), [out])
