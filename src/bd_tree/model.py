"""In-memory representation of a loaded store and one containment view.

A store is the full index of every node file: ``ref -> Node`` plus the logical
``id -> versions`` grouping.  A view is the containment closure of one ref: the
nodes it reaches through declared ``contains`` lists.  The containment chain
from the view root is the only record of which version is current.

The model is deliberately schema-agnostic: ``id``, ``legacy``, ``contains`` and
``links`` are structural; ``name``, ``title`` and ``section`` are presentation
fields exposed as properties.  Every other front-matter key (including
``folder``) is user metadata and is carried in ``Node.meta`` untouched.
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
    """One node file.  ``version`` is always ``>= 1``; versions are peers."""

    id: int
    version: int
    ref: str
    contains: list[str]  # declared list; an omitted list is a leaf
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
        """Directory this node opens for its containment descendants.

        ``section: true`` uses the node's own placement name; a non-empty string
        is used verbatim.  Any other value (``false``, ``null``, ``0``, ``""``,
        a list) means the node is not a section.
        """
        value = self.meta.get("section")
        if value is True:
            return self.placement_name
        if isinstance(value, str) and value.strip():
            return value
        return None

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
        """The store's root: declared ``ROOT``, else the lowest node.

        "Lowest" is by ``(id, version)``.  A declared root is returned even when
        its file is missing, so the breakage is reported instead of silently
        falling back.
        """
        if self.declared_root is not None:
            return self.declared_root
        if not self.nodes:
            return None
        return min(
            self.nodes.values(), key=lambda node: (node.id, node.version)
        ).ref

    def versions(self, node_id: int) -> list[Node]:
        """Every existing version of ``node_id``, ascending by version."""
        return sorted(
            (node for node in self.nodes.values() if node.id == node_id),
            key=lambda node: node.version,
        )

    def effective_contains(self, ref: str) -> list[str]:
        """The node's declared ``contains`` list; an omitted list is a leaf.

        Raises :class:`~.errors.BreakdownError` when the data holds a bare ref:
        a view walk must never pick a version on the caller's behalf.
        """
        # Imported here because the loader imports this module.
        from .errors import BreakdownError
        from .loader import is_full_ref

        node = self.nodes.get(ref)
        if node is None:
            return []
        for child in node.contains:
            if not is_full_ref(child):
                raise BreakdownError(
                    f"bare ref '{child}' in contains of '{ref}'; data refs "
                    "must be full <id>-<version> refs"
                )
        return list(node.contains)

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

    def current_ref(self, node_id: int) -> str | None:
        """The ref of logical ``node_id`` inside this view, else ``None``.

        A version-only chain selects one version per id.  Two versions of the
        same id in one view would make "current" ambiguous, so that is an error
        rather than a silent first-match.
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
