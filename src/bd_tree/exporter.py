"""Export containment views.  Registry via ``@exporter``.

Everything display-related comes from front-matter fields chosen on the command
line: paths from a template, titles and summaries from configurable keys, dot
colours and shapes from arbitrary fields.  No layer or link-type names live
here.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Iterable

from .checker import path_problem
from .errors import ExportError
from .freshness import stale_edge_list
from .frontmatter import render_document
from .model import ExportResult, Node, StaleEdge, View, slugify

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


def _placement_name(node: Node) -> str:
    """Explicit ``name``, else the title slug, else the ref."""
    return node.placement_name


def _template_fields(node: Node) -> dict[str, str]:
    fields = {key: _text(value) for key, value in node.meta.items()}
    fields.update(
        {
            "ref": node.ref,
            "id": str(node.id),
            "version": str(node.version),
            "name": _placement_name(node),
            "slug": _placement_name(node),
            "section": node.section or "",
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


def _with_prefix(prefix: str, path: str) -> str:
    return f"{prefix}/{path}" if prefix else path


_ORDINAL = re.compile(r"^\d+-")


def _numbered_section(
    parent: str, section: str, siblings: dict[str, dict[str, int]]
) -> str:
    """Number a section's first segment; inner segments stay explicit subpaths.

    The ordinal is the section base's first-encounter position among the distinct
    sibling directories under ``parent`` in containment traversal order, at least
    two digits.  A leading authored ordinal is stripped first, and sections that
    strip to the same base share one numbered directory.
    """
    segments = section.split("/")
    base = _ORDINAL.sub("", segments[0], count=1) or "section"
    under = siblings.setdefault(parent, {})
    if base not in under:
        under[base] = len(under)
    first = f"{under[base]:02d}-{base}"
    return _with_prefix(parent, "/".join([first, *segments[1:]]))


def _section_layout(view: View) -> tuple[dict[str, str], dict[str, str]]:
    """Directory holding each reachable ref's own file, and its containment parent.

    Mirrors :func:`bd_tree.loader.load_view`: walk declared ``contains`` from the
    view root, restricted to the refs in ``view.nodes``.  A non-section node sits
    in its parent's directory.  A section node opens a numbered directory for its
    descendants and its own file sits there; relative sections stack under the
    parent directory, while a leading ``/`` numbers from the output root.  A ref
    unreachable from the root gets no directory.
    """
    directories: dict[str, str] = {}
    parents: dict[str, str] = {}
    siblings: dict[str, dict[str, int]] = {}
    seen: set[str] = set()

    def walk(ref: str, directory: str, parent: str) -> None:
        if ref in seen or ref not in view.nodes:
            return
        seen.add(ref)
        node = view.nodes[ref]
        if node.section:
            base = "" if node.section_rooted else directory
            directory = _numbered_section(base, node.section, siblings)
        directories[ref] = directory
        parents[ref] = parent
        for child in view.store.effective_contains(ref):
            walk(child, directory, ref)

    walk(view.ref, "", "")
    return directories, parents


def _check_section_dirs(view: View, directories: dict[str, str]) -> None:
    """Refuse two sections that would merge their descendant subtrees.

    Sharing a directory is intentional when at most one node opens a subtree
    there (a carrier beside its layer's leaves, or several leaves in one stage).
    Two nodes that both have containment children would silently merge those
    children, so that case is refused.
    """
    used: dict[str, tuple[str, bool]] = {}
    for ref in sorted(
        view.nodes, key=lambda r: (view.nodes[r].id, view.nodes[r].version)
    ):
        node = view.nodes[ref]
        section = node.section
        if not section or ref not in directories:
            continue
        directory = directories[ref]
        has_children = any(
            child in view.nodes for child in view.store.effective_contains(ref)
        )
        previous = used.get(directory)
        if previous is None:
            used[directory] = (ref, has_children)
            continue
        if has_children and previous[1]:
            raise ExportError(
                f"sections {previous[0]} and {ref} both use directory '{directory}'"
            )
        used[directory] = (previous[0], previous[1] or has_children)


def _default_path(node: Node, directory: str = "") -> str:
    """Place the node's file in the directory that holds it.

    A section node's stem is its placement name; the directory already carries
    its numbered section.  Every other node sits in its inherited directory and
    uses its ``name``, else ``<ref>-<title-slug>``, else its ref.  ``folder`` is
    ordinary front matter and never affects placement.
    """
    if node.section:
        stem = _placement_name(node)
    elif node.name:
        stem = node.name
    else:
        slug = slugify(node.title)
        # ``Node.title`` falls back to the ref, so an equal slug is not a title.
        stem = f"{node.ref}-{slug}" if slug and slug != node.ref else node.ref
    return _validated_path(node, _with_prefix(directory, f"{stem}.md"))


def _build_paths(
    view: View,
    template: str | None,
    refs: Iterable[str],
    *,
    reserved: frozenset[str] = frozenset(),
) -> dict[str, str]:
    paths: dict[str, str] = {}
    used: dict[str, str] = {}
    refs = list(refs)
    graph_paths: dict[str, str] | None = None
    directories: dict[str, str] = {}
    if template is None and view.model == "graph":
        # Imported lazily: graph.py imports this module's banner and helpers.
        from .graph import build_graph, layout_paths

        graph_paths = layout_paths(build_graph(view.store), refs)
    elif template is None:
        directories, _ = _section_layout(view)
        _check_section_dirs(view, directories)
    for ref in refs:
        node = view.nodes[ref]
        if graph_paths is not None:
            path = graph_paths[ref]
        elif template is None:
            path = _default_path(node, directories.get(ref, ""))
        else:
            path = render_path(node, template)
        # Reserved names are refused in every directory, not only the root: a
        # node may never resolve to a nested generated file such as
        # ``<dir>/INDEX.md``.
        if path.rsplit("/", 1)[-1] in reserved:
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


def _index_text(
    view: View,
    paths: dict[str, str],
    title_field: str,
    summary_field: str,
    *,
    banner: str | None = None,
    label: str | None = None,
    nodes_link: str | None = None,
) -> str:
    lines: list[str] = []
    if nodes_link is not None:
        lines.extend(["---", f"nodes: {nodes_link}", "---", ""])
    lines.extend(
        [
            banner if banner is not None else BANNER.format(name="tree"),
            "",
            f"# View {view.ref if label is None else label}",
            "",
        ]
    )
    if nodes_link is not None:
        lines.extend([_nodes_pointer(nodes_link), ""])
    emitted: set[str] = set()

    def walk(ref: str, depth: int) -> None:
        if ref in emitted or ref not in view.nodes:
            return
        emitted.add(ref)
        node = view.nodes[ref]
        title = _display(node, title_field, node.ref)
        summary = _display(node, summary_field, "")
        lines.append(
            _node_entry(
                node,
                title,
                paths[ref],
                indent="  " * depth,
                summary=summary,
                nodes_link=nodes_link,
            )
        )
        for child in view.store.children(ref):
            walk(child, depth + 1)

    walk(view.ref, 0)
    for ref in sorted(view.nodes, key=lambda r: (view.nodes[r].id, view.nodes[r].version)):
        if ref not in emitted:
            walk(ref, 0)
    if not view.nodes:
        lines.append("_No nodes in this view._")
    lines.append("")
    return "\n".join(lines)


def _preorder_refs(view: View) -> list[str]:
    """View refs in containment pre-order, matching :func:`_index_text`."""
    order: list[str] = []
    emitted: set[str] = set()

    def walk(ref: str) -> None:
        if ref in emitted or ref not in view.nodes:
            return
        emitted.add(ref)
        order.append(ref)
        for child in view.store.children(ref):
            walk(child)

    walk(view.ref)
    for ref in sorted(view.nodes, key=lambda r: (view.nodes[r].id, view.nodes[r].version)):
        if ref not in emitted:
            walk(ref)
    return order


def _directory_indexes(
    view: View,
    paths: dict[str, str],
    title_field: str,
    summary_field: str,
    *,
    banner: str | None = None,
    label: str | None = None,
    nodes_link: str | None = None,
) -> dict[str, str]:
    """Generated index text for the output root and every node directory.

    The keys are output-relative directory POSIX paths (``""`` is the root).
    Each non-root directory lists its direct node files in view pre-order, then
    its immediate subdirectories in first-appearance order.  Every ancestor of
    a node directory is included, so a multi-segment section never leaves a
    bare prefix folder unindexed.  ``nodes_link``, when given, is the path from
    the output root to the store's ``nodes/`` folder; each index carries it in
    front matter and as a clickable link back to the real files.
    """
    indexes = {
        "": _index_text(
            view,
            paths,
            title_field,
            summary_field,
            banner=banner,
            label=label,
            nodes_link=nodes_link,
        )
    }
    banner_text = banner if banner is not None else BANNER.format(name="tree")
    directories: set[str] = {""}
    subdirectories: dict[str, list[str]] = {}
    direct: dict[str, list[str]] = {}

    def parent(directory: str) -> str:
        return directory.rsplit("/", 1)[0] if "/" in directory else ""

    for ref in _preorder_refs(view):
        path = paths.get(ref)
        if path is None:
            continue
        directory = parent(path)
        direct.setdefault(directory, []).append(ref)
        chain: list[str] = []
        current = directory
        while current:
            chain.append(current)
            current = parent(current)
        for current in reversed(chain):
            if current in directories:
                continue
            directories.add(current)
            subdirectories.setdefault(parent(current), []).append(
                current.rsplit("/", 1)[-1]
            )

    for directory in sorted(directories):
        if directory == "":
            continue
        link = None
        if nodes_link is not None:
            link = "../" * len(directory.split("/")) + nodes_link
        lines: list[str] = []
        if link is not None:
            lines.extend(["---", f"nodes: {link}", "---", ""])
        lines.extend([banner_text, "", f"# {directory}/", ""])
        if link is not None:
            lines.extend([_nodes_pointer(link), ""])
        for ref in direct.get(directory, []):
            node = view.nodes[ref]
            title = _display(node, title_field, node.ref)
            summary = _display(node, summary_field, "")
            filename = paths[ref].rsplit("/", 1)[-1]
            lines.append(
                _node_entry(
                    node,
                    title,
                    filename,
                    summary=summary,
                    nodes_link=link,
                )
            )
        for name in subdirectories.get(directory, []):
            lines.append(f"- [{name}]({name}/INDEX.md)")
        lines.append("")
        indexes[directory] = "\n".join(lines)
    return indexes


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
    """Write every view node at its templated path plus one INDEX.md per folder."""
    out = Path(out)
    _prepare_out(out, force=force, clean=clean)
    refs = sorted(view.nodes, key=lambda r: (view.nodes[r].id, view.nodes[r].version))
    paths = _build_paths(
        view, path_template, refs, reserved=frozenset({"INDEX.md"})
    )
    files: list[Path] = []
    for ref in refs:
        files.append(_write_node(out, view.nodes[ref], paths[ref]))
    indexes = _directory_indexes(
        view, paths, title_field, summary_field, banner=None, label=None
    )
    files.extend(_write_indexes(out, indexes))
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


def _dot_text(view: View, color_by: str | None, shape_by: str | None) -> str:
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
