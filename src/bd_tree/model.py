"""In-memory representation of a loaded store and one containment view.

A store is the full index of every node file: ``ref -> Node`` plus the logical
``id -> versions`` grouping.  A view is the containment closure of one ref: the
nodes it reaches through effective ``contains`` lists.

The model is deliberately schema-agnostic: ``id``, ``legacy``, ``contains`` and
``links`` are structural; ``folder``, ``name`` and ``title`` are presentation
fields exposed as properties.  Every other front-matter key is user metadata and
is carried in ``Node.meta`` untouched.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .frontmatter import body_hash


@dataclass
class Link:
    """One ``links`` entry.  ``type`` is an arbitrary label, never an enum."""

    to: str
    type: str
    pinned: str | None = None
    propagates: bool = False
    raw: Any = field(default_factory=dict)

    @property
    def propagating(self) -> bool:
        """Freshness propagates iff declared or already pinned."""
        return self.propagates or self.pinned is not None


@dataclass
class Node:
    """One node file.  ``version`` is 0 for the mutable main file."""

    id: int
    version: int
    ref: str
    contains: list[str] | None  # declared list; None means inherit the main
    legacy: str | None
    links: list[Link]
    body: str
    path: Path
    raw_links: list[Any]
    meta: dict[str, Any]

    @property
    def is_main(self) -> bool:
        return self.version == 0

    @property
    def main_ref(self) -> str:
        return str(self.id)

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
    def folder(self) -> str | None:
        value = self.meta.get("folder")
        if isinstance(value, str) and value.strip():
            return value
        return None

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
    origin: str  # "link" or "reference"
    propagates: bool = False

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


@dataclass
class Store:
    root: Path
    nodes: dict[str, Node]  # ref -> node, every file
    issues: list[Issue]
    declared_root: str | None = None  # ref read from the store's ROOT file

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
        """The store's root: declared ``ROOT``, else the lowest main ref.

        A declared root is returned even when its file is missing, so the
        breakage is reported instead of silently falling back.
        """
        if self.declared_root is not None:
            return self.declared_root
        mains = [node for node in self.nodes.values() if node.is_main]
        if not mains:
            return None
        return min(mains, key=lambda node: node.id).ref

    def main(self, node_id: int) -> Node | None:
        return self.nodes.get(str(node_id))

    def versions(self, node_id: int) -> list[Node]:
        """Every existing version of ``node_id``, main first."""
        return sorted(
            (node for node in self.nodes.values() if node.id == node_id),
            key=lambda node: node.version,
        )

    def effective_contains(self, ref: str) -> list[str]:
        """Declared list, or the main version's list when this version omits one."""
        node = self.nodes.get(ref)
        if node is None:
            return []
        if node.contains is not None:
            return list(node.contains)
        if node.version == 0:
            return []
        main = self.nodes.get(str(node.id))
        if main is not None and main.contains is not None:
            return list(main.contains)
        return []

    def containment_roots(self) -> list[Node]:
        """Refs that no node lists in ``effective_contains``, sorted."""
        listed = {
            child
            for node in self.nodes.values()
            for child in self.effective_contains(node.ref)
        }
        roots = [node for node in self.nodes.values() if node.ref not in listed]
        return sorted(roots, key=lambda node: (node.id, node.version))

    def node_edges(self, ref: str, *, propagating_only: bool = False) -> list[Edge]:
        edges = [
            Edge(
                node.ref,
                link.to,
                link.type,
                link.pinned,
                "link",
                link.propagating,
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
    """The containment closure rooted at ``ref``."""

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
