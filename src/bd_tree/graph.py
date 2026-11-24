"""Graph mode: ``links`` are forward parent -> child edges ordered into bands.

A view is the forward closure of one anchor over declared ``links``; every edge
is authored on its source node and in-edges are derived.  There is no other
topology.

Two band modes exist per store.  If any node declares ``stage``, bands are the
absolute integer stages and ``order`` is the within-stage tie-break.  If no
node declares ``stage``, bands are relative: every node needs a non-empty
``band`` (or the older ``layer: band/subpath`` shorthand), the band order is
derived from cross-band edges, and ``order`` positions nodes inside a band.  A
bare CLI id selects the highest existing version; a full ref is used verbatim.
"""

from __future__ import annotations

import heapq
import posixpath
import shutil
import subprocess
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .checker import path_problem
from .errors import BreakdownError, ExportError
from .exporter import BANNER, _prepare_out, exporter
from .frontmatter import render_document
from .loader import load, parse_ref, parse_selector
from .model import ExportResult, Issue, Link, Node, Store, View, slugify

FANOUT_LIMIT = 200
RESERVED = frozenset({"INDEX.md"})
RESERVED_NAMES = frozenset({"INDEX.md", "AGENTS.md", "REFS.md"})
UNLAYERED = "__unlayered__"


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


def group(node: Node) -> str:
    """The node's optional ``group`` as ordinary metadata, never placement.

    ``group`` is inert in every topology: it changes no path, no band, and no
    validation.  Use ``band`` plus ``subpath`` (or the older
    ``layer: <band>/<subpath>``) for graph placement.
    """
    value = node.meta.get("group")
    return value if isinstance(value, str) else ""


@dataclass(frozen=True)
class LayerPath:
    """A parsed band: its ``band`` name and optional ``subpath`` placement."""

    raw: str
    band: str
    subpath: str


def _layer_problem(value: object) -> str | None:
    """Why ``value`` is not a safe layer path, or ``None`` when it is one."""
    if not isinstance(value, str):
        return "must be a string"
    if not value.strip():
        return "must not be empty"
    if "\\" in value:
        return "must use '/' separators, not backslashes"
    for segment in value.split("/"):
        if segment in ("", ".", ".."):
            return "must not contain empty, '.', or '..' segments"
        if segment in RESERVED_NAMES:
            return f"must not use the reserved name '{segment}'"
        if segment.lower().endswith(".md"):
            return "must not contain a '.md' segment"
    return None


def _band_problem(value: object) -> str | None:
    """Why ``value`` is not a safe band name, or ``None`` when it is one."""
    if isinstance(value, str) and "/" in value:
        return "must be a single band name, not a path"
    return _layer_problem(value)


def parse_layer(value: object) -> LayerPath | None:
    """Parse a valid ``layer: band/subpath`` value; invalid/absent yields None."""
    if _layer_problem(value):
        return None
    assert isinstance(value, str)
    text = value.strip()
    band, _, subpath = text.partition("/")
    return LayerPath(text, band, subpath)


def parse_band_fields(band: object, subpath: object = None) -> LayerPath:
    """Validate and parse explicit ``band`` plus optional ``subpath`` values."""
    problem = _band_problem(band)
    if problem:
        raise BreakdownError(f"graph-layer-invalid: band {band!r}: {problem}")
    assert isinstance(band, str)
    band = band.strip()
    sub = ""
    if subpath is not None and not (
        isinstance(subpath, str) and not subpath.strip()
    ):
        problem = _layer_problem(subpath)
        if problem:
            raise BreakdownError(
                f"graph-layer-invalid: subpath {subpath!r}: {problem}"
            )
        assert isinstance(subpath, str)
        sub = subpath.strip()
    raw = f"{band}/{sub}" if sub else band
    return LayerPath(raw, band, sub)


def _band_fields(node: Node) -> LayerPath | None:
    """The normalized path from ``band``/``subpath``, or None when absent.

    None also covers a malformed pair; :func:`layer_path` reports the reason.
    An empty ``subpath`` counts as absent.
    """
    meta = node.meta
    if "band" not in meta:
        return None
    try:
        return parse_band_fields(meta.get("band"), meta.get("subpath"))
    except BreakdownError:
        return None


def node_layer_path(node: Node) -> LayerPath | None:
    """Normalize ``layer`` or ``band``/``subpath`` to one path; None if absent.

    A malformed value, a pair missing ``band``, or a node declaring both
    forms also yields None; the audit reports the reason.
    """
    meta = node.meta
    if "layer" in meta and ("band" in meta or "subpath" in meta):
        return None
    if "band" in meta:
        return _band_fields(node)
    if "subpath" in meta or "layer" not in meta:
        return None
    value = meta.get("layer")
    if _layer_problem(value):
        return None
    return parse_layer(value)


def require_layer_value(value: object) -> LayerPath:
    """Parse ``value`` or raise :class:`BreakdownError` for an invalid layer."""
    problem = _layer_problem(value)
    if problem:
        raise BreakdownError(
            f"graph-layer-invalid: layer {value!r}: {problem}"
        )
    parsed = parse_layer(value)
    assert parsed is not None
    return parsed


def layer_path(node: Node, issues: list[Issue] | None = None) -> LayerPath | None:
    """The node's parsed band path, reporting missing/invalid values.

    Accepts ``layer: band/subpath`` or the split ``band`` plus optional
    ``subpath``.  With no ``issues`` list the error raises
    :class:`BreakdownError`; audit passes a list so every bad node is
    collected instead of aborting.
    """
    meta = node.meta
    has_layer = "layer" in meta
    has_band = "band" in meta
    has_subpath = "subpath" in meta
    if has_layer and (has_band or has_subpath):
        _invalid(
            issues,
            "graph-layer-invalid",
            f"node '{node.ref}' declares 'layer' and 'band'/'subpath'; use one form",
            node.ref,
        )
        return None
    if has_subpath and not has_band:
        _invalid(
            issues,
            "graph-layer-invalid",
            f"node '{node.ref}' declares 'subpath' without 'band'",
            node.ref,
        )
        return None
    if has_band:
        problem = _band_problem(meta.get("band"))
        if problem:
            _invalid(
                issues,
                "graph-layer-invalid",
                f"node '{node.ref}' has invalid 'band' {meta.get('band')!r}: "
                f"{problem}",
                node.ref,
            )
            return None
        value = meta.get("subpath")
        if value is not None and not (
            isinstance(value, str) and not value.strip()
        ):
            problem = _layer_problem(value)
            if problem:
                _invalid(
                    issues,
                    "graph-layer-invalid",
                    f"node '{node.ref}' has invalid 'subpath' {value!r}: "
                    f"{problem}",
                    node.ref,
                )
                return None
        return _band_fields(node)
    if not has_layer:
        _invalid(
            issues,
            "graph-layer-missing",
            f"node '{node.ref}' has no 'layer' or 'band'; stores without "
            "'stage' order bands by band",
            node.ref,
        )
        return None
    value = meta.get("layer")
    problem = _layer_problem(value)
    if problem:
        _invalid(
            issues,
            "graph-layer-invalid",
            f"node '{node.ref}' has invalid 'layer' {value!r}: {problem}",
            node.ref,
        )
        return None
    return parse_layer(value)


def require_layer(node: Node) -> LayerPath:
    """The node's parsed band path or a :class:`BreakdownError`."""
    parsed = layer_path(node)
    assert parsed is not None
    return parsed


def _stage_of(node: Node) -> int | None:
    value = node.meta.get("stage")
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def node_layer(node: Node) -> str | None:
    """The node's normalized band path, or ``None`` when absent/invalid."""
    parsed = node_layer_path(node)
    return parsed.raw if parsed is not None else None


def relative_store(store: Store) -> bool:
    """True when no node declares ``stage``: bands derive from ``layer``."""
    return not any("stage" in node.meta for node in store.nodes.values())


def flat_bands(store: Store) -> bool:
    """True when the store's ROOT node declares ``band_layout: flat``.

    Flat mode keeps every relative band top-level and orders them by the band
    graph's topological order.  Explicit subpaths still nest below their band.
    """
    root = store.root_ref
    node = store.nodes.get(root) if root is not None else None
    if node is None:
        return False
    value = node.meta.get("band_layout")
    return isinstance(value, str) and value.strip().lower() == "flat"


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


def _structural(link: Link) -> bool:
    """True for an authored link that defines structure (never symmetric)."""
    return not link.symmetric


# ---------------------------------------------------------------------------
# Bands: absolute ``stage`` or relative ``layer``


@dataclass
class BandPlan:
    """Derived band ordinals, folders, labels, and the issues found.

    ``band`` maps every ref to its **top-level band ordinal** (the value
    ``--stage`` filters on).  ``layer`` maps every valid ref to its band name;
    ``folders`` maps every ref to its effective output folder.  ``band_folder``
    maps each band name to its base folder.
    """

    relative: bool
    band: dict[str, int]
    label: dict[int, str]
    issues: list[Issue]
    band_folder: dict[str, str] = field(default_factory=dict)
    folders: dict[str, str] = field(default_factory=dict)
    layer: dict[str, str] = field(default_factory=dict)


def band_order_hint(store: Store) -> list[str]:
    """The ROOT node's ``band_order`` list, normalized; ``[]`` when absent.

    Non-list values are reported by the checker and ignored here.  Duplicates
    and unknown band names are tolerated; the first occurrence wins.
    """
    root = store.root_ref
    node = store.nodes.get(root) if root is not None else None
    if node is None:
        return []
    value = node.meta.get("band_order")
    if not isinstance(value, list):
        return []
    hint: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip() and item.strip() not in hint:
            hint.append(item.strip())
    return hint


def _band_edges(
    store: Store, extra: tuple[str, str] | None = None
) -> dict[str, set[str]]:
    """Band constraints from structural links crossing band boundaries."""
    edges: dict[str, set[str]] = defaultdict(set)
    for node in store.nodes.values():
        source = node_layer_path(node)
        if source is None:
            continue
        for link in node.links:
            if not _structural(link):
                continue
            target = store.nodes.get(link.to)
            if target is None:
                continue
            destination = node_layer_path(target)
            if destination is not None and destination.band != source.band:
                edges[source.band].add(destination.band)
    if extra is not None and extra[0] != extra[1]:
        edges[extra[0]].add(extra[1])
    return edges


def layer_reaches(
    store: Store, start: str, target: str, extra: tuple[str, str] | None = None
) -> bool:
    """Whether band ``target`` is reachable from band ``start`` over band edges."""
    if start == target:
        return True
    edges = _band_edges(store, extra)
    seen: set[str] = set()
    stack = [start]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        for nxt in edges.get(current, ()):
            if nxt == target:
                return True
            stack.append(nxt)
    return False


def _layer_order(
    edges: dict[str, set[str]],
    layers: list[str],
    band_order: Sequence[str] = (),
) -> list[str]:
    """Topological layer order; cycles are omitted.

    Ready layers are tie-broken by ``band_order`` (earlier index wins) and then
    lexicographically.  Real edge constraints always win; bands absent from the
    hint sort after listed ones.
    """
    hint = {name: index for index, name in enumerate(band_order)}

    def rank(layer: str) -> tuple[int, int, str]:
        if layer in hint:
            return (0, hint[layer], layer)
        return (1, 0, layer)

    indegree = {layer: 0 for layer in layers}
    for targets in edges.values():
        for target in targets:
            if target in indegree:
                indegree[target] += 1
    ready = [(rank(layer), layer) for layer in layers if indegree[layer] == 0]
    heapq.heapify(ready)
    ordered: list[str] = []
    while ready:
        _key, current = heapq.heappop(ready)
        ordered.append(current)
        for target in sorted(edges.get(current, ())):
            if target not in indegree:
                continue
            indegree[target] -= 1
            if indegree[target] == 0:
                heapq.heappush(ready, (rank(target), target))
    return ordered


def _layer_cycles(
    nodes: set[str], edges: dict[str, set[str]]
) -> list[list[str]]:
    """Strongly connected components of size > 1: the layers in a cycle."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[list[str]] = []
    counter = 0

    def visit(node: str) -> None:
        nonlocal counter
        index[node] = low[node] = counter
        counter += 1
        stack.append(node)
        on_stack.add(node)
        for target in sorted(edges.get(node, ())):
            if target not in nodes:
                continue
            if target not in index:
                visit(target)
                low[node] = min(low[node], low[target])
            elif target in on_stack:
                low[node] = min(low[node], index[target])
        if low[node] == index[node]:
            component: list[str] = []
            while True:
                member = stack.pop()
                on_stack.discard(member)
                component.append(member)
                if member == node:
                    break
            components.append(sorted(component))

    for node in sorted(nodes):
        if node not in index:
            visit(node)
    return sorted(component for component in components if len(component) > 1)


def _dominant_layer(store: Store, refs: Iterable[str]) -> str:
    counts: Counter[str] = Counter()
    for ref in refs:
        value = node_layer(store.nodes[ref])
        if value is not None:
            counts[value] += 1
    if not counts:
        return ""
    return slugify(min(counts.items(), key=lambda item: (-item[1], item[0]))[0])


def _band_components(
    bands: Iterable[str], edges: dict[str, set[str]]
) -> list[list[str]]:
    """Weakly connected components of the undirected band graph."""
    adjacency: dict[str, set[str]] = defaultdict(set)
    for source, targets in edges.items():
        for target in targets:
            adjacency[source].add(target)
            adjacency[target].add(source)
    seen: set[str] = set()
    components: list[list[str]] = []
    for band in sorted(bands):
        if band in seen:
            continue
        stack = [band]
        component: set[str] = set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            stack.extend(adjacency.get(current, set()) - component)
        seen |= component
        components.append(sorted(component))
    return components


def _distances(
    starts: Iterable[str], edges: dict[str, set[str]]
) -> dict[str, int]:
    """Unweighted multi-source BFS distance from ``starts`` over ``edges``."""
    distance: dict[str, int] = {start: 0 for start in starts}
    queue = list(distance)
    head = 0
    while head < len(queue):
        current = queue[head]
        head += 1
        for target in edges.get(current, ()):
            if target in distance:
                continue
            distance[target] = distance[current] + 1
            queue.append(target)
    return distance


def _top_level_bands(
    bands: Iterable[str], edges: dict[str, set[str]]
) -> tuple[list[str], dict[str, int]]:
    """Top-level bands by the shortest-path rule, with root distances.

    Each weakly connected component is placed independently so a disconnected
    band is top-level.  Inside a component the top-level set is every band on a
    shortest root-to-sink path; a cycle-only component falls back to all its
    bands sorted.  Components with edges sort before isolated bands, and cycle
    components after acyclic ones, both deterministically.
    """
    bands = list(bands)
    components = _band_components(bands, edges)
    ranked: list[tuple[tuple[int, int, str], str]] = []
    distances: dict[str, int] = {}
    for component in components:
        members = set(component)
        internal = {
            band: {target for target in edges.get(band, ()) if target in members}
            for band in component
        }
        indegree = {band: 0 for band in component}
        outdegree = {band: 0 for band in component}
        for source in component:
            for target in internal.get(source, ()):
                indegree[target] += 1
                outdegree[source] += 1
        has_edges = any(outdegree[band] for band in component)
        roots = [band for band in component if indegree[band] == 0]
        sinks = [band for band in component if outdegree[band] == 0]
        if not has_edges:
            for band in component:
                distances[band] = 0
            for band in component:
                ranked.append(((2, 0, band), band))
            continue
        if not roots or not sinks:
            for band in component:
                distances[band] = 0
            for band in component:
                ranked.append(((1, 0, band), band))
            continue
        from_roots = _distances(roots, internal)
        reverse: dict[str, set[str]] = defaultdict(set)
        for source in component:
            for target in internal.get(source, ()):
                reverse[target].add(source)
        to_sinks = _distances(sinks, reverse)
        lengths = [
            from_roots[sink]
            for sink in sinks
            if sink in from_roots
        ]
        shortest = min(lengths) if lengths else 0
        top = [
            band
            for band in component
            if band in from_roots
            and band in to_sinks
            and from_roots[band] + to_sinks[band] == shortest
        ]
        if not top:
            top = roots
        for band in component:
            distances[band] = from_roots.get(band, 0)
        for band in top:
            ranked.append(((0, distances[band], band), band))
    ranked.sort(key=lambda item: item[0])
    return [band for _key, band in ranked], distances


def _relative_plan(store: Store) -> BandPlan:
    issues: list[Issue] = []
    layer_paths: dict[str, LayerPath] = {}
    nodes = sorted(store.nodes.values(), key=_ref_key)
    for node in nodes:
        parsed = layer_path(node, issues)
        if parsed is not None:
            layer_paths[node.ref] = parsed

    bands = sorted({parsed.band for parsed in layer_paths.values()})
    edges = _band_edges(store)
    ordered = _layer_order(edges, bands, band_order_hint(store))
    remaining = sorted(set(bands) - set(ordered))
    for component in _layer_cycles(set(bands), edges):
        issues.append(
            Issue(
                "error",
                "graph-layer-cycle",
                "layer cycle: " + " -> ".join(component),
            )
        )
    topological = ordered + remaining
    if flat_bands(store):
        top_level = list(topological)
        distances = {band: 0 for band in top_level}
    else:
        top_level, distances = _top_level_bands(bands, edges)
    ordinal = {band: index for index, band in enumerate(top_level)}

    band_folder: dict[str, str] = {}
    root_of: dict[str, str] = {}
    label: dict[int, str] = {}
    for band in top_level:
        band_folder[band] = f"{ordinal[band]:02d}-{slugify(band) or 'band'}"
        root_of[band] = band
        label[ordinal[band]] = band

    incoming: dict[str, set[str]] = defaultdict(set)
    for source in edges:
        for target in edges[source]:
            incoming[target].add(source)

    placed = set(top_level)
    fallback: list[str] = []
    for band in topological:
        if band in placed:
            continue
        candidates = [parent for parent in incoming.get(band, ()) if parent in placed]
        if not candidates:
            fallback.append(band)
            continue
        parent = min(
            candidates, key=lambda item: (-distances.get(item, 0), item)
        )
        band_folder[band] = (
            f"{band_folder[parent]}/{slugify(band) or 'band'}"
        )
        root_of[band] = root_of[parent]
        placed.add(band)
    for band in sorted(fallback):
        index = len(top_level)
        top_level.append(band)
        ordinal[band] = index
        distances[band] = 0
        band_folder[band] = f"{index:02d}-{slugify(band) or 'band'}"
        root_of[band] = band
        label[index] = band

    band: dict[str, int] = {}
    folders: dict[str, str] = {}
    layer: dict[str, str] = {}
    for ref, parsed in layer_paths.items():
        root = root_of[parsed.band]
        band[ref] = ordinal[root]
        folder = band_folder[parsed.band]
        if parsed.subpath:
            folder = f"{folder}/{parsed.subpath}"
        folders[ref] = folder
        layer[ref] = parsed.band

    for node in nodes:
        source = layer_paths.get(node.ref)
        if source is None:
            continue
        for link in node.links:
            if not _structural(link):
                continue
            target = store.nodes.get(link.to)
            if target is None:
                continue
            destination = layer_paths.get(target.ref)
            if destination is None or destination.band != source.band:
                continue
            if _order_of(node) >= _order_of(target):
                issues.append(
                    Issue(
                        "error",
                        "graph-order-back-edge",
                        f"edge {node.ref} -> {target.ref} ({link.type}) is not "
                        f"forward within band '{source.band}': order "
                        f"{_order_of(node)} >= {_order_of(target)}",
                        node=node.ref,
                    )
                )

    # Invalid data still renders: missing/invalid layers share one trailing
    # band.  This is not an ordering claim; audit has already reported it.
    missing = [node.ref for node in nodes if node.ref not in band]
    if missing:
        index = len(top_level)
        folder = f"{index:02d}-unlayered"
        label[index] = "unlayered"
        band_folder[UNLAYERED] = folder
        for ref in missing:
            band[ref] = index
            folders[ref] = folder
            layer[ref] = UNLAYERED
    return BandPlan(
        True,
        band,
        label,
        issues,
        band_folder=band_folder,
        folders=folders,
        layer=layer,
    )


def _absolute_plan(store: Store) -> BandPlan:
    band: dict[str, int] = {}
    for ref, node in store.nodes.items():
        value = _stage_of(node)
        if value is not None:
            band[ref] = value
    groups: dict[int, list[str]] = defaultdict(list)
    for ref, value in band.items():
        groups[value].append(ref)
    label = {
        value: _dominant_layer(store, refs) or f"stage-{value:02d}"
        for value, refs in groups.items()
    }
    band_folder = {
        f"stage-{value:02d}": f"{value:02d}-{slugify(text) or f'stage-{value:02d}'}"
        for value, text in label.items()
    }
    folders = {
        ref: band_folder[f"stage-{value:02d}"] for ref, value in band.items()
    }
    return BandPlan(
        False, band, label, [], band_folder=band_folder, folders=folders
    )


# ---------------------------------------------------------------------------
# The graph


@dataclass
class Graph:
    """A loaded store plus authored out-edges and derived in-edges."""

    store: Store
    out: dict[str, list[Link]]
    inn: dict[str, list[Link]]
    roots: list[str]
    relative: bool = False
    band: dict[str, int] = field(default_factory=dict)
    band_label: dict[int, str] = field(default_factory=dict)
    band_folder: dict[str, str] = field(default_factory=dict)
    folders: dict[str, str] = field(default_factory=dict)
    layer: dict[str, str] = field(default_factory=dict)
    issues: list[Issue] = field(default_factory=list)

    def node(self, ref: str) -> Node | None:
        return self.store.nodes.get(ref)


def build_graph(root: Store | str | Path) -> Graph:
    """Build adjacency from authored ``node.links``.

    Selects absolute bands when any node declares ``stage``, relative
    ``layer`` bands otherwise, and records the band issues for the audit.
    """
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
    incoming = {
        link.to
        for links in out.values()
        for link in links
        if _structural(link)
    }
    roots = sorted(
        (ref for ref in store.nodes if ref not in incoming),
        key=lambda ref: _ref_key(store.nodes[ref]),
    )
    plan = _relative_plan(store) if relative_store(store) else _absolute_plan(store)
    return Graph(
        store=store,
        out=out,
        inn=inn,
        roots=roots,
        relative=plan.relative,
        band=plan.band,
        band_label=plan.label,
        band_folder=plan.band_folder,
        folders=plan.folders,
        layer=plan.layer,
        issues=plan.issues,
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
    """The store anchor: declared ``ROOT``, else the lowest root by
    ``(stage, id, version)`` — exactly :attr:`Store.root_ref`."""
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


def _band_ok(graph: Graph, ref: str, stages: tuple[int, int] | None) -> bool:
    if stages is None:
        return True
    value = graph.band.get(ref)
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
        if current == target or _band_ok(graph, current, stage_range):
            included.append(current)
        if depth is not None and level >= depth:
            continue
        for link in sorted(graph.out.get(current, ()), key=_edge_key):
            if not _structural(link):
                continue
            if type_set is not None and link.type not in type_set:
                continue
            if link.to in graph.store.nodes and link.to not in seen:
                queue.append((link.to, level + 1))
    return included


# ---------------------------------------------------------------------------
# Layout


@dataclass(frozen=True)
class StageBand:
    """One band: its top-level ordinal, folder, and member refs."""

    stage: int
    label: str
    directory: str
    refs: list[str]
    top_level: bool = True
    depth: int = 0
    root_label: str = ""


def _member_key(graph: Graph, ref: str) -> tuple[str, int, int, int]:
    node = graph.store.nodes[ref]
    return (
        graph.folders.get(ref, ""),
        _order_of(node),
        node.id,
        node.version,
    )


def graph_layout(graph: Graph, refs: Iterable[str]) -> list[StageBand]:
    """Group refs by band; order inside an effective folder by ``(order, id, version)``."""
    if graph.relative:
        groups: dict[str, list[str]] = defaultdict(list)
        for ref in refs:
            if ref not in graph.store.nodes:
                continue
            band = graph.layer.get(ref)
            if band is None:
                raise BreakdownError(
                    f"node '{ref}' needs a non-empty 'layer' for the graph layout"
                )
            groups[band].append(ref)
        bands: list[StageBand] = []
        for band in sorted(
            groups, key=lambda name: graph.band_folder.get(name, name)
        ):
            members = groups[band]
            members.sort(key=lambda ref: _member_key(graph, ref))
            folder = graph.band_folder.get(band, band)
            stage = graph.band.get(members[0])
            if stage is None:
                raise BreakdownError(
                    f"band '{band}' has no derived top-level ordinal"
                )
            top_level = "/" not in folder
            bands.append(
                StageBand(
                    stage=stage,
                    label=(graph.band_label.get(stage) or band)
                    if top_level
                    else band,
                    directory=folder,
                    refs=members,
                    top_level=top_level,
                    depth=folder.count("/"),
                    root_label=graph.band_label.get(stage, band),
                )
            )
        return bands

    groups = defaultdict(list)
    for ref in refs:
        node = graph.store.nodes.get(ref)
        if node is None:
            continue
        value = graph.band.get(ref)
        if value is None:
            raise BreakdownError(
                f"node '{ref}' needs an integer 'stage' for the graph layout"
            )
        groups[value].append(ref)

    bands = []
    for value in sorted(groups):
        members = groups[value]
        members.sort(key=lambda ref: _member_key(graph, ref))
        label = graph.band_label.get(value) or f"stage-{value:02d}"
        bands.append(
            StageBand(
                stage=value,
                label=label,
                directory=graph.band_folder.get(
                    f"stage-{value:02d}", f"{value:02d}-{slugify(label)}"
                ),
                refs=members,
                root_label=label,
            )
        )
    return bands


def _add_folder_chain(directory: str, directories: set[str]) -> None:
    parts = directory.split("/")
    for index in range(1, len(parts) + 1):
        directories.add("/".join(parts[:index]))


def _folder_members(
    graph: Graph, refs: Iterable[str]
) -> tuple[dict[str, list[str]], list[str], dict[str, StageBand]]:
    """Effective folder -> members, every directory, and band folders by path."""
    bands = graph_layout(graph, refs)
    members: dict[str, list[str]] = defaultdict(list)
    directories: set[str] = set()
    by_directory: dict[str, StageBand] = {}
    for band in bands:
        by_directory.setdefault(band.directory, band)
        _add_folder_chain(band.directory, directories)
    for band in bands:
        for ref in band.refs:
            folder = graph.folders.get(ref, band.directory)
            members[folder].append(ref)
            _add_folder_chain(folder, directories)
    for folder, refs_in_folder in members.items():
        refs_in_folder.sort(key=lambda ref: _member_key(graph, ref))
    return members, sorted(directories), by_directory


# ---------------------------------------------------------------------------
# Text and DOT rendering


def _link_text(link: Link) -> str:
    label = f"{link.type}, symmetric" if link.symmetric else link.type
    return f"{link.to} ({label})"


def band_prefix(graph: Graph) -> str:
    """The band noun: ``layer`` in relative mode, ``stage`` in absolute mode."""
    return "layer" if graph.relative else "stage"


def render_graph(graph: Graph, refs: Iterable[str]) -> str:
    """Per-band text: ``<noun> N — band``, nested ``<subpath>/`` headings."""
    members, directories, by_directory = _folder_members(graph, refs)
    lines: list[str] = []
    prefix = band_prefix(graph)
    for directory in directories:
        band = by_directory.get(directory)
        if band is not None and band.top_level:
            lines.append(f"{prefix} {band.stage} — {band.label}")
        else:
            indent = "  " * directory.count("/")
            name = directory.rsplit("/", 1)[-1]
            lines.append(f"{indent}{name}/")
        for ref in members.get(directory, ()):
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


# Subtle (fill, border) pairs, cycled by band position.  Fixed so the DOT is
# deterministic; each band still gets its own colour.
_DOT_PALETTE = (
    ("#eef4fb", "#9bb7d4"),
    ("#f1f7ee", "#a9c59b"),
    ("#fbf4e8", "#d4b483"),
    ("#f6eef6", "#b79bb7"),
    ("#eef7f7", "#94c0c0"),
    ("#f4f1ea", "#bdb29b"),
)
_DOT_TITLE_LIMIT = 48


def _short_title(title: str, limit: int = _DOT_TITLE_LIMIT) -> str:
    """Collapse whitespace and truncate so a DOT box stays readable."""
    text = " ".join(title.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _dot_folder_label(
    graph: Graph,
    folder: str,
    member: str,
    by_directory: dict[str, StageBand],
    prefix: str,
) -> str:
    """``<noun> N — <band>[/<subpath>]`` for one effective DOT cluster."""
    ordinal = graph.band.get(member)
    root = graph.band_label.get(ordinal, "") if ordinal is not None else ""
    band = by_directory.get(folder)
    if band is not None and band.top_level:
        return f"{prefix} {band.stage} — {band.label}"
    suffix = folder.split("/", 1)[1] if "/" in folder else ""
    path = f"{root}/{suffix}" if suffix else root
    return f"{prefix} {ordinal} — {path}"


def render_dot(graph: Graph, refs: Iterable[str]) -> str:
    """Graphviz DOT: one cluster per effective band folder.

    The label is ``<noun> N — <band>[/<subpath>]``; absolute mode keeps one
    cluster per stage with its dominant layer label.  Only authored out-edges
    inside the view are drawn, each labelled with its link type.
    """
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
    prefix = band_prefix(graph)
    if graph.relative:
        members, _directories, by_directory = _folder_members(graph, refs)
        clusters = [
            (
                f"cluster_{index}",
                _dot_folder_label(
                    graph, folder, refs_in_folder[0], by_directory, prefix
                ),
                refs_in_folder,
            )
            for index, (folder, refs_in_folder) in enumerate(
                sorted(members.items())
            )
            if refs_in_folder
        ]
    else:
        clusters = []
        for band in graph_layout(graph, refs):
            clusters.append(
                (
                    f"cluster_{band.stage}",
                    f"{prefix} {band.stage} — {band.label}",
                    band.refs,
                )
            )
    wanted = {ref for _name, _label, refs_in_cluster in clusters for ref in refs_in_cluster}
    for index, (name, label, refs_in_cluster) in enumerate(clusters):
        fill, border = _DOT_PALETTE[index % len(_DOT_PALETTE)]
        lines.append(f"  subgraph {name} {{")
        lines.append(f"    label={_dot_quote(label)};")
        lines.append("    style=\"rounded,filled\";")
        lines.append(f"    color={_dot_quote(border)};")
        lines.append(f"    fillcolor={_dot_quote(fill)};")
        for ref in refs_in_cluster:
            node = graph.store.nodes[ref]
            node_label = _dot_quote(f"{ref}\n{_short_title(node.title)}")
            lines.append(f"    {_dot_quote(ref)} [label={node_label}];")
        lines.append("  }")
    edges = sorted(
        {
            (source, link.to, f"{link.type}, symmetric" if link.symmetric else link.type)
            for source in wanted
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


def render_svg(graph: Graph, refs: Iterable[str]) -> str:
    """Render :func:`render_dot` to SVG through the Graphviz ``dot`` binary.

    No Python dependency: the DOT text is piped to ``dot -Tsvg``.  A missing
    binary or a non-zero exit raises :class:`BreakdownError` with the stderr.
    """
    dot_path = shutil.which("dot")
    if dot_path is None:
        raise BreakdownError(
            "Graphviz 'dot' not found; install Graphviz or use 'bd graph --dot'"
        )
    try:
        completed = subprocess.run(
            [dot_path, "-Tsvg"],
            input=render_dot(graph, refs),
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
    """Authored master links, then derived symmetric opposites."""
    target = resolve_graph_ref(graph, ref)
    if target not in graph.store.nodes:
        raise BreakdownError(f"unknown ref '{target}'")
    links = sorted(graph.out.get(target, ()), key=_edge_key)
    lines = [f"{target} -> {_link_text(link)}" for link in links]
    derived = sorted(
        graph.store.derived_links(target), key=lambda edge: _text_ref_key(edge.target)
    )
    lines.extend(
        f"{target} -> {edge.target} ({edge.type})  [derived]" for edge in derived
    )
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


def _cycles(graph: Graph) -> list[list[str]]:
    adjacency = {
        ref: sorted(
            {
                link.to
                for link in graph.out.get(ref, ())
                if _structural(link) and link.to in graph.store.nodes
            }
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
    if graph.relative:
        issues.extend(graph.issues)

    for ref in nodes:
        node = graph.store.nodes[ref]
        if not graph.relative:
            stage(node, issues)
        order(node, issues)
        if "group" in node.meta:
            issues.append(
                Issue(
                    "warning",
                    "graph-group-ignored",
                    "node "
                    f"'{ref}' declares 'group', which is ordinary metadata in "
                    "a graph; use 'band' plus 'subpath' for placement",
                    node=ref,
                )
            )

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
            if not _structural(link):
                continue
            if graph.relative:
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
    base = directory
    if node.name:
        stem = node.name
        path = f"{base}/{stem}.md"
    else:
        slug = slugify(node.title)
        if slug and slug != node.ref:
            path = f"{base}/{node.ref}-{slug}.md"
        else:
            path = f"{base}/{node.ref}.md"
    problem = path_problem(path)
    if problem:
        raise ExportError(
            f"node {node.ref} resolves to invalid path '{path}': {problem}"
        )
    if path.rsplit("/", 1)[-1] in RESERVED:
        raise ExportError(f"node {node.ref} path collides with generated '{path}'")
    return path


def layout_paths(graph: Graph, refs: Iterable[str]) -> dict[str, str]:
    """The effective-folder path of every ref: ``<folder>/<stem>.md``.

    A relative band contributes ``<NN>-<slug(band)>`` plus its inferred nested
    band path plus the node's explicit ``layer`` subpath.  An absolute store
    keeps one ``<NN>-<label>`` folder per stage.  The rule is exactly
    :func:`export_graph`'s, extracted so ``bd work`` and ``bd export tree``
    materialize the same paths.
    """
    paths: dict[str, str] = {}
    used: dict[str, str] = {}
    for band in graph_layout(graph, refs):
        for ref in band.refs:
            folder = graph.folders.get(ref, band.directory)
            path = _node_path(graph.store.nodes[ref], folder)
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


def _provenance_lines(
    graph: Graph, refs: Iterable[str], paths: dict[str, str], directory: str
) -> list[str]:
    lines: list[str] = []
    for ref in refs:
        lines.append(f"- {_ref_link(graph, ref, paths, directory)}")
        for link in sorted(graph.out.get(ref, ()), key=_edge_key):
            lines.append(
                f"  → {_ref_link(graph, link.to, paths, directory)} "
                f"({link.type})"
                if link.to in graph.store.nodes
                else f"  → {link.to} ({link.type})"
            )
        for link in sorted(graph.inn.get(ref, ()), key=_edge_key):
            lines.append(
                f"  ← {_ref_link(graph, link.to, paths, directory)} "
                f"({link.type}) [derived]"
                if link.to in graph.store.nodes
                else f"  ← {link.to} ({link.type}) [derived]"
            )
    return lines


def _graph_indexes(
    graph: Graph, bands: list[StageBand], paths: dict[str, str]
) -> dict[str, str]:
    """One index per folder: direct nodes plus links to child folders.

    Every band folder and every node folder is included, with each ancestor of
    a node directory, so inferred nesting and explicit subpaths all have an
    index.  Direct nodes keep band order and out/in provenance.
    """
    direct: dict[str, list[str]] = defaultdict(list)
    children: dict[str, set[str]] = defaultdict(set)
    directories: set[str] = set()
    for band in bands:
        _add_folder_chain(band.directory, directories)
        for ref in band.refs:
            directory = posixpath.dirname(paths[ref])
            direct[directory].append(ref)
            _add_folder_chain(directory, directories)
    for directory in directories:
        if "/" in directory:
            parent = directory.rsplit("/", 1)[0]
            children[parent].add(directory.rsplit("/", 1)[-1])

    indexes: dict[str, str] = {}
    for directory in sorted(directories):
        lines = [BANNER.format(name="graph"), "", f"# {directory}/", ""]
        lines.extend(
            _provenance_lines(graph, direct.get(directory, ()), paths, directory)
        )
        for name in sorted(children.get(directory, ())):
            lines.append(f"- [{name}/]({name}/INDEX.md)")
        lines.append("")
        indexes[directory] = "\n".join(lines)
    return indexes


def _root_index(graph: Graph, anchor: str, bands: list[StageBand]) -> str:
    lines = [BANNER.format(name="graph"), "", f"# Graph {anchor}", ""]
    prefix = band_prefix(graph)
    for band in bands:
        if not band.top_level:
            continue
        count = len(band.refs)
        noun = "node" if count == 1 else "nodes"
        lines.append(
            f"- [{prefix} {band.stage} — {band.label}]"
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

    paths = layout_paths(built, refs)

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

    indexes = _graph_indexes(built, bands, paths)
    for directory in sorted(indexes):
        path = destination / directory / "INDEX.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(indexes[directory], encoding="utf-8", newline="")
        files.append(path)

    root_index = destination / "INDEX.md"
    root_index.write_text(
        _root_index(built, target, bands), encoding="utf-8", newline=""
    )
    files.append(root_index)
    return ExportResult("graph", destination, len(refs), files)
