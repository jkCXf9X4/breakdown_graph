"""In-memory representation of a loaded store and one link-closure view.

A store is the full index of every node file: ``ref -> Node`` plus the logical
``id -> versions`` grouping.  There is one topology: edges are declared
``links``.  A view is the closure of one ref over those out-links; a node
reached through several parents appears once.

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
    """One ``links`` entry.  ``type`` is an arbitrary label, never an enum.

    A symmetric link is a *master*: exactly one node file authors the relation
    and the opposite is derived at load time.  ``inverse`` names the derived
    edge type; when absent the master type is reused.
    """

    to: str
    type: str
    pinned: str | None = None
    propagates: bool = False
    symmetric: bool = False
    inverse: str | None = None
    raw: Any = field(default_factory=dict)

    @property
    def propagating(self) -> bool:
        """Freshness propagates iff declared or already pinned."""
        return self.propagates or self.pinned is not None


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
        """Best-effort read of the ``section`` key, kept for compatibility.

        In the single link topology ``section`` is ordinary front matter with no
        effect on paths, layout or validation; bands are the only layout.
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
    origin: str  # "link" (master), "derived" (opposite) or "reference"
    propagates: bool = False
    symmetric: bool = False

    @property
    def propagating(self) -> bool:
        return self.origin == "link" and self.propagates

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

    def format(self) -> str:
        where = self.path or self.node or ""
        prefix = self.level.upper()
        if where:
            return f"{prefix} {where}: {self.message}"
        return f"{prefix}: {self.message}"


def _stage_key(node: Node) -> tuple[int, int, int, int]:
    """Deterministic graph order: ``(stage, id, version)`` when a stage exists.

    Nodes without an integer ``stage`` (a relative layer-only store, or a
    half-built absolute one) sort after staged nodes by ``(id, version)`` so
    the key is total and deterministic.
    """
    value = node.meta.get("stage")
    if isinstance(value, int) and not isinstance(value, bool):
        return (0, value, node.id, node.version)
    return (1, 0, node.id, node.version)


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

        Declared ``ROOT`` wins.  Otherwise the lowest topology root by
        ``(stage, id, version)``.  A declared root is returned even when its file
        is missing, so the breakage is reported instead of silently falling
        back.
        """
        if self.declared_root is not None:
            return self.declared_root
        if not self.nodes:
            return None
        roots = self.topology_roots()
        return roots[0].ref if roots else None

    def structural_links(self, ref: str) -> list[Link]:
        """Authored non-symmetric links of ``ref`` (the structural subset).

        Only these links expand a view, define ancestry and topology roots, and
        drive band inference.  A symmetric master is shown but never structural.
        """
        node = self.nodes.get(ref)
        if node is None:
            return []
        return [link for link in node.links if not link.symmetric]

    def derived_links(self, ref: str) -> list[Edge]:
        """Derived opposites targeting ``ref`` from other nodes' symmetric masters.

        For every other node's master ``X --T--> ref`` with ``symmetric``, the
        opposite ``ref --(inverse or T)--> X`` is returned with
        ``origin="derived"``.  Derived opposites are never stored or structural.
        """
        edges: list[Edge] = []
        for node in self.nodes.values():
            if node.ref == ref:
                continue
            for link in node.links:
                if not link.symmetric or link.to != ref:
                    continue
                edges.append(
                    Edge(
                        source=ref,
                        target=node.ref,
                        type=link.inverse or link.type,
                        pinned=None,
                        origin="derived",
                        propagates=False,
                        symmetric=True,
                    )
                )
        return edges

    def children(self, ref: str) -> list[str]:
        """Structural out-link targets of ``ref`` (full refs), authored order."""
        from .loader import is_full_ref

        return [link.to for link in self.structural_links(ref) if is_full_ref(link.to)]

    def parents(self, ref: str) -> list[str]:
        """Refs whose structural ``links`` target ``ref``, sorted by stage key."""
        found = [
            node
            for node in self.nodes.values()
            if any(
                link.to == ref and not link.symmetric for link in node.links
            )
        ]
        return [node.ref for node in sorted(found, key=_stage_key)]

    def topology_roots(self) -> list[Node]:
        """Nodes no other node reaches through structural links, by stage key."""
        roots = [
            node for node in self.nodes.values() if not self.parents(node.ref)
        ]
        return sorted(roots, key=_stage_key)

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
        include_derived: bool = False,
    ) -> list[Edge]:
        """Authored out-edges of ``ref``; optionally append derived opposites.

        ``include_derived`` leaves the default behaviour intact and adds the
        derived opposite edges whose source is ``ref``, marked
        ``origin="derived"`` and ``symmetric=True``.
        """
        edges = [
            Edge(
                source=node.ref,
                target=link.to,
                type=link.type,
                pinned=link.pinned,
                origin="link",
                propagates=link.propagating,
                symmetric=link.symmetric,
            )
            for node in self.nodes.values()
            if node.ref == ref
            for link in node.links
        ]
        if include_derived:
            edges.extend(self.derived_links(ref))
        if propagating_only:
            edges = [edge for edge in edges if edge.propagating]
        return edges


@dataclass
class View:
    """The link closure rooted at ``ref``: out-link targets, seen-set deduped."""

    store: Store
    ref: str
    nodes: dict[str, Node]  # ref -> node, view members only
    edges: list[Edge]
    issues: list[Issue]

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
