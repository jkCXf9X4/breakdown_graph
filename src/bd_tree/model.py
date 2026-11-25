"""In-memory representation of a loaded store and one undirected view.

A store is the full index of every node file: ``ref -> Node`` plus the logical
``id -> versions`` grouping.  There is one topology: edges are declared
``links``.  A view is the weakly connected component of one ref over those
authored links; a node reached through several neighbours appears once.

The model is deliberately schema-agnostic: ``id``, ``legacy`` and ``links`` are
structural; every other front-matter key (including ``name``, ``title``,
``section`` and the raw ``contains`` key) is metadata and is carried in
``Node.meta`` untouched.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import BreakdownError
from .frontmatter import body_hash


def slugify(text: str) -> str:
    """Lowercase ASCII filename stem; non-ASCII and punctuation collapse to ``-``."""
    normalised = unicodedata.normalize("NFKD", text).lower()
    ascii_text = "".join(
        char if char.isascii() else "-"
        for char in normalised
        if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")


@dataclass
class Link:
    """One typed link.  ``type`` is an arbitrary label, never an enum.

    Links are declared in the node body as reserved tokens; ``raw`` holds the
    raw token string.  ``pinned`` and ``propagates`` come from the
    ``freshness:`` front-matter map keyed by target ref.
    """

    to: str
    type: str
    pinned: str | None = None
    propagates: bool = False
    raw: Any = field(default_factory=dict)

    @property
    def propagating(self) -> bool:
        """Freshness propagates iff declared or already pinned."""
        return self.propagates or self.pinned is not None


@dataclass(frozen=True)
class Neighbor:
    """One undirected neighbour of a ref.

    ``kind`` is the direction from the queried ref's point of view: ``child``
    (an authored out-link) or ``parent`` (another node's authored link targets
    the queried ref).  ``link`` is the representative authored link.
    """

    ref: str
    kind: str
    link: Link


KIND_RANK: dict[str, int] = {"child": 0, "parent": 1}
_KIND_BY_RANK: tuple[str, ...] = ("child", "parent")


def _offer_neighbor(
    chosen: dict[str, tuple[int, str, Link]],
    target: str,
    kind: str,
    link: Link,
) -> None:
    """Keep the best authored link per neighbour: kind rank, then type."""
    key = (KIND_RANK[kind], link.type)
    current = chosen.get(target)
    if current is not None and (current[0], current[1]) <= key:
        return
    chosen[target] = (key[0], key[1], link)


@dataclass
class Node:
    """One node file.  ``version`` is always ``>= 1``; versions are peers."""

    id: int
    version: int
    ref: str
    legacy: str | None
    links: list[Link]
    body: str
    path: Path
    raw_links: list[Any]
    meta: dict[str, Any]

    @property
    def body_hash(self) -> str:
        return body_hash(self.body)

    @property
    def body_lines(self) -> int:
        return len(self.body.splitlines())

    @property
    def body_chars(self) -> int:
        return len(self.body)

    @property
    def name(self) -> str | None:
        value = self.meta.get("name")
        if isinstance(value, str) and value.strip():
            return value
        return None

    @property
    def title(self) -> str:
        value = self.meta.get("title")
        return str(value) if value not in (None, "") else self.ref

    @property
    def placement_name(self) -> str:
        """Explicit ``name``, else the title slug, else the ref."""
        return self.name or slugify(self.title) or self.ref

    @property
    def section(self) -> str | None:
        """Best-effort read of the inert ``section`` key.

        ``section`` is ordinary front matter and places nothing: membership and
        order come from the undirected component and BFS distance.  The value
        ``section: true`` still resolves to this node's placement name and a
        leading ``/`` is stripped, but callers must not treat either as
        structure.
        """
        value = self.meta.get("section")
        if value is True:
            return self.placement_name
        if isinstance(value, str) and value.strip():
            text = value.strip()
            if text.startswith("/"):
                return text.lstrip("/").rstrip("/") or None
            return text
        return None

    @property
    def section_rooted(self) -> bool:
        """True when the inert ``section`` value starts with ``/``."""
        value = self.meta.get("section")
        return isinstance(value, str) and value.strip().startswith("/")

    @property
    def summary(self) -> str:
        value = self.meta.get("summary")
        return str(value) if value not in (None, "") else ""

    def field(self, name: str, default: Any = None) -> Any:
        """Any front-matter value, by key."""
        return self.meta.get(name, default)


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    type: str
    pinned: str | None
    origin: str  # always "authored"
    propagates: bool = False

    @property
    def propagating(self) -> bool:
        return self.propagates

    @property
    def label(self) -> str:
        return f"{self.source} -> {self.target} ({self.type})"


@dataclass(frozen=True)
class Issue:
    level: str  # "error" or "warning"
    code: str
    message: str
    node: str | None = None
    path: str | None = None
    line: int | None = None

    def format(self) -> str:
        where = self.path or self.node or ""
        prefix = self.level.upper()
        if where:
            return f"{prefix} {where}: {self.message}"
        return f"{prefix}: {self.message}"


def _ref_key(node: Node) -> tuple[int, int]:
    """Deterministic identity order: ``(id, version)``."""
    return node.id, node.version


@dataclass
class Store:
    root: Path
    nodes: dict[str, Node]  # ref -> node, every file
    issues: list[Issue]
    declared_root: str | None = None  # ref read from the store's ROOT file

    @property
    def model(self) -> str:
        """Topology family of this store: always ``"graph"``.

        Kept as a property for internal compatibility.  Edges are ``links`` and
        there is exactly one topology, so any stray ``contains`` key in
        front matter is inert metadata (``bd check`` reports it as
        ``contains-removed``).
        """
        return "graph"

    @property
    def project_root(self) -> Path:
        """The project directory that owns this store.

        A hidden ``.bd_tree`` store belongs to its parent; a classic ``nodes/``
        store is its own project root.
        """
        if self.root.name == ".bd_tree" and (self.root / "nodes").is_dir():
            return self.root.parent
        return self.root

    @property
    def root_ref(self) -> str | None:
        """The store's default anchor.

        Declared ``ROOT`` wins.  Otherwise the lowest member of the first weak
        component by ``(id, version)``.  A declared root is returned even when
        its file is missing, so the breakage is reported instead of silently
        falling back.
        """
        if self.declared_root is not None:
            return self.declared_root
        if not self.nodes:
            return None
        roots = self.topology_roots()
        return roots[0].ref if roots else None

    def structural_links(self, ref: str) -> list[Link]:
        """The authored links of ``ref``.

        Kept under its historical name.  There is one topology and every
        authored link is structural; the method no longer filters.
        """
        node = self.nodes.get(ref)
        if node is None:
            return []
        return list(node.links)

    def children(self, ref: str) -> list[str]:
        """Structural out-link targets of ``ref`` (full refs), authored order."""
        from .loader import is_full_ref

        return [link.to for link in self.structural_links(ref) if is_full_ref(link.to)]

    def neighbors(self, ref: str) -> list[Neighbor]:
        """Undirected neighbours of ``ref`` over authored links.

        Both directions are considered, one entry per neighbour ref.  Kind
        precedence is ``child > parent``: a reciprocal pair is a ``child`` from
        each side.  The representative ``link`` is always an authored link.
        Sorted by ``(kind_rank, link.type, id, version)``.
        """
        from .loader import is_full_ref, parse_ref

        chosen: dict[str, tuple[int, str, Link]] = {}
        node = self.nodes.get(ref)
        if node is not None:
            for link in node.links:
                if link.to == ref or not is_full_ref(link.to):
                    continue
                _offer_neighbor(chosen, link.to, "child", link)
        for other in self.nodes.values():
            if other.ref == ref:
                continue
            for link in other.links:
                if link.to != ref:
                    continue
                _offer_neighbor(chosen, other.ref, "parent", link)

        def sort_key(item: tuple[str, tuple[int, str, Link]]):
            target, (rank, link_type, _link) = item
            try:
                node_id, version = parse_ref(target)
            except ValueError:
                node_id, version = 0, 0
            return rank, link_type, node_id, version

        return [
            Neighbor(ref=target, kind=_KIND_BY_RANK[rank], link=link)
            for target, (rank, _type, link) in sorted(chosen.items(), key=sort_key)
        ]

    def components(self) -> list[list[str]]:
        """Weak components over :meth:`neighbors`, members sorted by identity.

        Every ref appears in exactly one component.  Members are sorted by
        ``(id, version)`` and the components by their first member, so the
        result is deterministic even with cycles.
        """
        seen: set[str] = set()
        found: list[list[str]] = []
        for start in sorted(self.nodes.values(), key=_ref_key):
            if start.ref in seen:
                continue
            component: list[str] = []
            queue = [start.ref]
            seen.add(start.ref)
            while queue:
                current = queue.pop(0)
                component.append(current)
                for neighbor in self.neighbors(current):
                    if neighbor.ref in seen or neighbor.ref not in self.nodes:
                        continue
                    seen.add(neighbor.ref)
                    queue.append(neighbor.ref)
            component.sort(key=lambda ref: _ref_key(self.nodes[ref]))
            found.append(component)
        found.sort(key=lambda component: _ref_key(self.nodes[component[0]]))
        return found

    def parents(self, ref: str) -> list[str]:
        """Refs whose authored links target ``ref``, by ``(id, version)``."""
        found = [
            node
            for node in self.nodes.values()
            if any(link.to == ref for link in node.links)
        ]
        return [node.ref for node in sorted(found, key=_ref_key)]

    def topology_roots(self) -> list[Node]:
        """One representative per weak component, lowest member by identity.

        Kept under its historical name so callers and the ``ROOT`` fallback keep
        working.  Cycles are ordinary edges, so a non-empty store always has at
        least one representative.
        """
        return [self.nodes[members[0]] for members in self.components()]

    def versions(self, node_id: int) -> list[Node]:
        """Every existing version of ``node_id``, ascending by version."""
        return sorted(
            (node for node in self.nodes.values() if node.id == node_id),
            key=lambda node: node.version,
        )

    def node_edges(
        self,
        ref: str,
        *,
        propagating_only: bool = False,
    ) -> list[Edge]:
        """Authored out-edges of ``ref``."""
        edges = [
            Edge(
                source=node.ref,
                target=link.to,
                type=link.type,
                pinned=link.pinned,
                origin="authored",
                propagates=link.propagating,
            )
            for node in self.nodes.values()
            if node.ref == ref
            for link in node.links
        ]
        if propagating_only:
            edges = [edge for edge in edges if edge.propagating]
        return edges


@dataclass
class View:
    """The weakly connected component around ``ref``.

    ``nodes`` holds every member exactly once.  ``distance`` is the undirected
    BFS hop count from ``ref``.  ``edges`` keeps authored links with both ends
    inside the component; derived opposites are never stored here.
    """

    store: Store
    ref: str
    nodes: dict[str, Node]  # ref -> node, view members only
    edges: list[Edge]
    issues: list[Issue]
    distance: dict[str, int] = field(default_factory=dict)

    @property
    def root(self) -> Path:
        return self.store.root

    @property
    def root_ref(self) -> str:
        return self.ref

    @property
    def model(self) -> str:
        """Topology family inherited from the store; always ``"graph"``."""
        return self.store.model

    def current_ref(self, node_id: int) -> str | None:
        """The ref of logical ``node_id`` inside this view, else ``None``.

        A link closure can reach two versions of one id; that makes "current"
        ambiguous, so it is an error rather than a silent first-match.
        """
        matches = [
            ref for ref, node in self.nodes.items() if node.id == node_id
        ]
        if len(matches) > 1:
            raise BreakdownError(
                f"view {self.ref} contains multiple versions of id {node_id}: "
                + ", ".join(sorted(matches))
            )
        return matches[0] if matches else None

    def node_edges(self, ref: str, *, propagating_only: bool = False) -> list[Edge]:
        """Authored out-edges of ``ref`` inside this view."""
        edges = [edge for edge in self.edges if edge.source == ref]
        if propagating_only:
            edges = [edge for edge in edges if edge.propagating]
        return edges


@dataclass
class CheckResult:
    root: Path
    view: str
    nodes_scanned: int
    issues: list[Issue]

    @property
    def errors(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.level == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.level == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class StaleEdge:
    source: str
    target: str
    type: str
    state: str  # "stale" or "untracked"
    pinned: str | None
    current: str | None

    @property
    def label(self) -> str:
        return f"{self.source} -> {self.target} ({self.type})"

    def format(self) -> str:
        return f"{self.label}: {self.state}"


@dataclass(frozen=True)
class ReconcileChange:
    node: str
    path: Path
    target: str
    type: str
    old: str | None
    new: str

    def format(self) -> str:
        old = self.old or "untracked"
        return f"{self.node} -> {self.target} ({self.type}): {old} -> {self.new}"


@dataclass(frozen=True)
class DiffEntry:
    id: int
    state: str  # same, changed, only-left, only-right


@dataclass
class ExportResult:
    name: str
    out: Path
    nodes: int
    files: list[Path]
