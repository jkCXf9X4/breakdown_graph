"""Load the flat numeric node store and resolve a view as a component.

Every node lives at ``nodes/<id>-<version>.md``.  The filename is the only
identity and the only version marker; there is no bare ``<id>.md`` file and no
privileged "main" version.  All versions of one logical id are peers.

Edges are declared ``links`` and nothing else.  A view is the weakly connected
component over those authored links, rooted at one ref; a node reached through
several neighbours appears once.  Data refs (``links`` and the ``ROOT`` file)
must be fully qualified ``<id>-<version>`` refs.  A bare id in data is recorded
as a ``bare-ref`` issue.  A leftover ``contains`` key is inert metadata here;
the checker reports it as ``contains-removed``.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import BreakdownError
from .frontmatter import FrontMatterError, parse_document
from .model import (
    Edge,
    Issue,
    Link,
    Node,
    Store,
    View,
)

NODE_SUFFIX = ".md"
ROOT_FILE = "ROOT"
ROOT_POINTER = ".bd_root"
STORE_DIR = ".bd_tree"

# Filename and data refs are version-only.  A CLI selector may still be bare.
FILENAME = re.compile(r"^(?P<id>[1-9]\d*)-(?P<version>[1-9]\d*)\.md$")
REF = re.compile(r"^(?P<id>[1-9]\d*)-(?P<version>[1-9]\d*)$")
SELECTOR = re.compile(r"^(?P<id>[1-9]\d*)(?:-(?P<version>[1-9]\d*))?$")


class FilenameError(ValueError):
    """A filename does not follow the version-only numeric grammar."""


def is_full_ref(text: object) -> bool:
    """Whether ``text`` is a complete ``<id>-<version>`` ref."""
    return isinstance(text, str) and REF.fullmatch(text.strip()) is not None


def is_bare_ref(text: object) -> bool:
    """Whether ``text`` is a bare ``<id>`` selector (never valid as data)."""
    return isinstance(text, str) and text.strip().isdigit() and text.strip()[0] != "0"


def parse_ref(text: str | int) -> tuple[int, int]:
    """Parse a full ``5-1`` ref into ``(id, version)``.

    A bare ``5`` is a selector, not a ref: resolve it through a view first.
    """
    if isinstance(text, bool) or not isinstance(text, (str, int)):
        raise ValueError(f"invalid ref {text!r}")
    match = REF.fullmatch(str(text).strip())
    if not match:
        raise ValueError(f"invalid ref {text!r}")
    return int(match.group("id")), int(match.group("version"))


def parse_selector(text: str | int) -> tuple[int, int | None]:
    """Parse ``5`` or ``5-1`` into ``(id, version)``; version is ``None`` if bare."""
    if isinstance(text, bool) or not isinstance(text, (str, int)):
        raise ValueError(f"invalid ref {text!r}")
    match = SELECTOR.fullmatch(str(text).strip())
    if not match:
        raise ValueError(f"invalid ref {text!r}")
    raw = match.group("version")
    return int(match.group("id")), (int(raw) if raw is not None else None)


def ref_of(node_id: int, version: int) -> str:
    if node_id < 1:
        raise ValueError(f"invalid id {node_id!r}")
    if version < 1:
        raise ValueError(f"invalid version {version!r}")
    return f"{node_id}-{version}"


def parse_filename(name: str) -> tuple[int, int]:
    """Parse ``<id>-<version>.md`` into ``(id, version)``."""
    if Path(name).name != name:
        raise FilenameError(f"not a bare filename: '{name}'")
    match = FILENAME.fullmatch(name)
    if not match:
        raise FilenameError(
            f"invalid node filename '{name}' (expected <id>-<version>.md)"
        )
    return int(match.group("id")), int(match.group("version"))


def node_path(root: str | Path, node_id: int, version: int) -> Path:
    return Path(root) / "nodes" / f"{ref_of(node_id, version)}{NODE_SUFFIX}"


def store_root_at(candidate: Path) -> Path | None:
    """Return the store root for a classic or project candidate, else ``None``.

    The classic ``nodes/`` layout wins when a candidate has both.
    """
    if (candidate / "nodes").is_dir():
        return candidate.resolve()
    if (candidate / STORE_DIR / "nodes").is_dir():
        return (candidate / STORE_DIR).resolve()
    return None


def resolve_store_root(path: str | Path) -> Path:
    """Return the store root for a project root or a store root.

    A project may keep its store in ``.bd_tree/`` or expose the classic
    ``nodes/`` layout directly.  The classic layout wins when a candidate has
    both.  A path with neither is returned unchanged, so callers can report
    the missing directory themselves.
    """
    candidate = Path(path)
    root = store_root_at(candidate)
    return root if root is not None else candidate.resolve()


def root_pointer_at(directory: str | Path) -> Path | None:
    """Read ``<directory>/.bd_root`` and return the store it names.

    The file holds one store path, resolved relative to ``directory`` unless
    absolute.  A missing file returns ``None``; a malformed or non-store
    pointer raises :class:`BreakdownError` with the ``invalid-bd-root:``
    prefix.
    """
    base = Path(directory).resolve()
    pointer = base / ROOT_POINTER
    if not pointer.is_file():
        return None
    try:
        text = pointer.read_text(encoding="utf-8")
    except OSError as exc:
        raise BreakdownError(f"invalid-bd-root: cannot read {pointer}: {exc}") from exc
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise BreakdownError(
            f"invalid-bd-root: {pointer} is empty (expected one store path)"
        )
    if len(lines) > 1:
        raise BreakdownError(
            f"invalid-bd-root: {pointer} must hold one path line, found {len(lines)}"
        )
    target = Path(lines[0])
    if not target.is_absolute():
        target = base / target
    store = store_root_at(target)
    if store is None:
        raise BreakdownError(
            f"invalid-bd-root: {pointer} names {target}, which is not a store "
            "(expected nodes/ or .bd_tree/nodes/)"
        )
    return store


DISCOVERY_DEPTH = 3
DISCOVERY_PRUNE = frozenset(
    {
        ".bd_tree",
        ".cache",
        ".git",
        ".hg",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".svn",
        ".tox",
        ".venv",
        "__pycache__",
        "bd_work",
        "build",
        "dist",
        "node_modules",
        "site-packages",
        "venv",
    }
)


def stores_below(base: Path, *, max_depth: int = DISCOVERY_DEPTH) -> list[Path]:
    """Find stores strictly below ``base``, bounded by ``max_depth``.

    The downward fallback is deterministic (paths sorted), does not follow
    symlinks, and prunes heavy or irrelevant directories.  A candidate is a
    directory holding ``nodes/`` or ``.bd_tree/nodes/`` and is returned in the
    same store-root form as :func:`resolve_store_root`.
    """
    if max_depth < 1:
        return []
    base = base.resolve()
    found: set[Path] = set()
    for dirpath, dirnames, _files in os.walk(base):
        current = Path(dirpath)
        depth = len(current.relative_to(base).parts)
        dirnames[:] = sorted(name for name in dirnames if name not in DISCOVERY_PRUNE)
        if depth >= max_depth:
            dirnames[:] = []
        if depth < 1:
            continue
        store = store_root_at(current)
        if store is not None:
            found.add(store)
            dirnames[:] = []
    return sorted(found, key=str)


def _issue(
    issues: list[Issue],
    level: str,
    code: str,
    message: str,
    *,
    node: str | None = None,
    path: Path | None = None,
    root: Path | None = None,
) -> None:
    rel = None
    if path is not None:
        rel = str(path.relative_to(root)) if root is not None else str(path)
    issues.append(Issue(level, code, message, node=node, path=rel))


def _classify_data_ref(value: object) -> tuple[str, str | None]:
    """Classify one data ref as ``full``, ``bare`` or ``invalid``."""
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return "invalid", None
    text = str(value).strip()
    if is_full_ref(text):
        return "full", text
    if is_bare_ref(text):
        return "bare", text
    return "invalid", None


def _parse_links(
    meta: dict[str, Any], issues: list[Issue], path: Path, root: Path
) -> tuple[list[Link], list[Any]]:
    raw = meta.get("links")
    if raw is None:
        return [], []
    if not isinstance(raw, list):
        _issue(issues, "error", "invalid-links", "'links' must be a list", path=path, root=root)
        return [], []
    links: list[Link] = []
    raws: list[Any] = []
    for index, item in enumerate(raw):
        if isinstance(item, (str, int)) and not isinstance(item, bool):
            kind, target = _classify_data_ref(item)
            if kind == "invalid":
                _issue(
                    issues,
                    "error",
                    "invalid-ref",
                    f"links[{index}] has invalid ref {item!r}",
                    path=path,
                    root=root,
                )
                continue
            if kind == "bare":
                _issue(
                    issues,
                    "error",
                    "bare-ref",
                    f"links[{index}] '{target}' is a bare id; use a full "
                    "<id>-<version> ref",
                    path=path,
                    root=root,
                )
            links.append(Link(to=str(target), type="", raw=item))
            raws.append(item)
            continue
        if not isinstance(item, dict):
            _issue(
                issues,
                "error",
                "invalid-link",
                f"links[{index}] must be a mapping or a ref",
                path=path,
                root=root,
            )
            continue
        to = item.get("to")
        ltype = item.get("type")
        kind, target = _classify_data_ref(to) if to is not None else ("invalid", None)
        if kind == "invalid":
            _issue(
                issues,
                "error",
                "invalid-ref",
                f"links[{index}] has invalid 'to' {to!r}",
                path=path,
                root=root,
            )
            continue
        if kind == "bare":
            _issue(
                issues,
                "error",
                "bare-ref",
                f"links[{index}] 'to' {target!r} is a bare id; use a full "
                "<id>-<version> ref",
                path=path,
                root=root,
            )
        if not isinstance(ltype, str) or not ltype.strip():
            _issue(
                issues,
                "error",
                "invalid-link",
                f"links[{index}] is missing 'type'",
                path=path,
                root=root,
            )
            continue
        propagates = item.get("propagates", False)
        if not isinstance(propagates, bool):
            _issue(
                issues,
                "error",
                "invalid-propagates",
                f"'propagates' on {target} must be a boolean",
                path=path,
                root=root,
            )
            propagates = False
        symmetric = item.get("symmetric", False)
        if not isinstance(symmetric, bool):
            _issue(
                issues,
                "error",
                "invalid-symmetric",
                f"'symmetric' on {target} must be a boolean",
                path=path,
                root=root,
            )
            symmetric = False
        inverse = item.get("inverse")
        if inverse is not None:
            if not isinstance(inverse, str) or not inverse.strip():
                _issue(
                    issues,
                    "error",
                    "inverse-without-symmetric",
                    f"'inverse' on {target} must be a non-empty string",
                    path=path,
                    root=root,
                )
                inverse = None
            elif not symmetric:
                _issue(
                    issues,
                    "error",
                    "inverse-without-symmetric",
                    f"'inverse' on {target} requires 'symmetric: true'",
                    path=path,
                    root=root,
                )
                inverse = None
            else:
                inverse = inverse.strip()
        pinned = item.get("pinned")
        if pinned is not None and not isinstance(pinned, str):
            _issue(
                issues,
                "error",
                "invalid-pin",
                f"'pinned' on {target} must be a string",
                path=path,
                root=root,
            )
            pinned = None
        links.append(
            Link(
                to=str(target),
                type=ltype,
                pinned=pinned,
                propagates=propagates,
                symmetric=symmetric,
                inverse=inverse,
                raw=dict(item),
            )
        )
        raws.append(dict(item))
    return links, raws


@dataclass
class Record:
    """One parsed node file."""

    path: Path
    node_id: int
    version: int
    node: Node | None


def _parse_node(
    path: Path,
    parsed_id: int,
    parsed_version: int,
    issues: list[Issue],
    root: Path,
) -> Node | None:
    try:
        doc = parse_document(path.read_text(encoding="utf-8"))
    except (OSError, FrontMatterError) as exc:
        _issue(issues, "error", "bad-frontmatter", str(exc), path=path, root=root)
        return None
    meta = dict(doc.meta)
    ref = ref_of(parsed_id, parsed_version)
    declared_id = meta.get("id")
    if declared_id is not None:
        if isinstance(declared_id, bool) or not isinstance(declared_id, int):
            _issue(
                issues,
                "error",
                "invalid-id",
                "'id' must be an integer",
                node=ref,
                path=path,
                root=root,
            )
        elif declared_id != parsed_id:
            _issue(
                issues,
                "error",
                "id-filename-mismatch",
                f"filename id '{parsed_id}' != front-matter id '{declared_id}'",
                node=ref,
                path=path,
                root=root,
            )
    links, raw_links = _parse_links(meta, issues, path, root)
    legacy = meta.get("legacy")
    return Node(
        id=parsed_id,
        version=parsed_version,
        ref=ref,
        legacy=str(legacy) if isinstance(legacy, str) else None,
        links=links,
        body=doc.body,
        path=path,
        raw_links=raw_links,
        meta=meta,
    )


def scan(root: str | Path) -> tuple[list[Record], list[Issue]]:
    """Scan ``root/nodes`` once, returning every record and global issues."""
    root = resolve_store_root(root)
    issues: list[Issue] = []
    nodes_dir = root / "nodes"
    records: list[Record] = []
    if not nodes_dir.is_dir():
        _issue(
            issues,
            "error",
            "missing-nodes-dir",
            "missing node store: neither nodes/ nor .bd_tree/nodes exists",
            path=root,
            root=root,
        )
        return records, issues

    seen: dict[str, Path] = {}
    for path in sorted(nodes_dir.glob(f"*{NODE_SUFFIX}")):
        try:
            parsed_id, parsed_version = parse_filename(path.name)
        except FilenameError as exc:
            _issue(issues, "error", "invalid-filename", str(exc), path=path, root=root)
            continue
        ref = ref_of(parsed_id, parsed_version)
        if ref in seen:
            _issue(
                issues,
                "error",
                "duplicate-version",
                f"duplicate ref {ref} (also {seen[ref].relative_to(root)})",
                node=ref,
                path=path,
                root=root,
            )
            continue
        seen[ref] = path

        node = _parse_node(path, parsed_id, parsed_version, issues, root)
        records.append(
            Record(path=path, node_id=parsed_id, version=parsed_version, node=node)
        )
    return records, issues


def _read_declared_root(root: Path, issues: list[Issue]) -> str | None:
    """Read the optional store-level ``ROOT`` file: one full ref, nothing else."""
    path = root / ROOT_FILE
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        _issue(
            issues,
            "error",
            "invalid-root",
            "ROOT file is empty (expected one ref, e.g. 1-4)",
            path=path,
            root=root,
        )
        return None
    if is_bare_ref(text):
        _issue(
            issues,
            "error",
            "bare-ref",
            f"ROOT file holds bare id {text!r}; use a full <id>-<version> ref",
            path=path,
            root=root,
        )
        return None
    if not is_full_ref(text):
        _issue(
            issues,
            "error",
            "invalid-root",
            f"ROOT file does not contain a ref: {text!r}",
            path=path,
            root=root,
        )
        return None
    return text


def _resolve_implicit_link_types(
    nodes: dict[str, Node], issues: list[Issue]
) -> None:
    """Fill ``type=""`` links from the target node's own ``type`` field."""
    for node in nodes.values():
        for link in node.links:
            if link.type:
                continue
            target = nodes.get(link.to)
            if target is None:
                link.type = "link"
                continue
            value = target.meta.get("type")
            if isinstance(value, str) and value.strip():
                link.type = value
            else:
                _issue(
                    issues,
                    "error",
                    "invalid-link",
                    f"implicit link to '{link.to}' needs a non-empty 'type' "
                    "on the target",
                    node=node.ref,
                )
                link.type = "link"


def load(root: str | Path) -> Store:
    """Load the full store index at a project root or a store root."""
    root = Path(root).resolve()
    if not root.is_dir():
        raise BreakdownError(f"root '{root}' is not a directory")
    root = resolve_store_root(root)
    records, issues = scan(root)
    declared_root = _read_declared_root(root, issues)
    nodes = {record.node.ref: record.node for record in records if record.node is not None}
    nodes = dict(sorted(nodes.items(), key=lambda item: _ref_sort_key(item[1])))
    _resolve_implicit_link_types(nodes, issues)
    return Store(
        root=root, nodes=nodes, issues=issues, declared_root=declared_root
    )


def _ref_sort_key(node: Node) -> tuple[int, int]:
    return node.id, node.version


def require_full_ref(text: str, role: str) -> str:
    """Return ``text`` as a full ref or raise a :class:`BreakdownError`."""
    if is_full_ref(text):
        return text.strip()
    if is_bare_ref(text):
        raise BreakdownError(
            f"bare ref '{text}' in {role}; use a full <id>-<version> ref"
        )
    raise BreakdownError(f"invalid ref '{text}' in {role}")


def _load_graph_view(store: Store, canonical: str) -> View:
    """Undirected BFS over ``Store.neighbors`` — the whole weak component.

    Repeated refs close the walk, so cycles are ordinary edges.  ``distance``
    records the hop count from ``canonical``.  ``edges`` keeps every authored
    link whose source and target are both in the component; symmetric masters
    stay in and derived opposites never enter.
    """
    included: dict[str, Node] = {}
    distance: dict[str, int] = {canonical: 0}
    queue = [canonical]
    while queue:
        current = queue.pop(0)
        node = store.nodes.get(current)
        if node is None:
            continue
        included[current] = node
        for neighbor in store.neighbors(current):
            if neighbor.ref in distance or neighbor.ref not in store.nodes:
                continue
            distance[neighbor.ref] = distance[current] + 1
            queue.append(neighbor.ref)

    edges: list[Edge] = []
    for node in included.values():
        for link in node.links:
            if link.to in included:
                edges.append(
                    Edge(
                        source=node.ref,
                        target=link.to,
                        type=link.type,
                        pinned=link.pinned,
                        origin="link",
                        propagates=link.propagating,
                        symmetric=link.symmetric,
                    )
                )
    return View(
        store=store,
        ref=canonical,
        nodes=included,
        edges=edges,
        issues=list(store.issues),
        distance=distance,
    )


def load_view(root: str | Path | Store, ref: str | None = None) -> View:
    """Return the weak component around ``ref``.

    ``ref`` defaults to the store's default anchor.  The walk is undirected BFS
    over ``links`` with a distance map: every member appears once, cycles are
    legal, and order is the anchor's hop count.  Bare data refs are already
    reported by ``scan``; a bare *view root* raises :class:`BreakdownError`
    because a view can never pick a version for the caller.
    """
    store = root if isinstance(root, Store) else load(root)
    issues: list[Issue] = []
    if ref is None:
        canonical = store.root_ref
        if canonical is None:
            issues.append(
                Issue("error", "view-root-missing", "store has no nodes")
            )
            return View(store=store, ref="", nodes={}, edges=[], issues=issues)
    else:
        try:
            node_id, version = parse_selector(ref)
        except ValueError:
            issues.append(Issue("error", "invalid-ref", f"invalid view ref {ref!r}"))
            return View(store=store, ref=str(ref), nodes={}, edges=[], issues=issues)
        if version is None:
            raise BreakdownError(
                f"bare ref '{ref}' used as a view root; resolve it through a view "
                "first"
            )
        canonical = ref_of(node_id, version)

    if canonical not in store.nodes:
        issues.append(
            Issue(
                "error",
                "view-root-missing",
                f"view root '{canonical}' does not exist",
                node=canonical,
            )
        )
        return View(store=store, ref=canonical, nodes={}, edges=[], issues=issues)

    return _load_graph_view(store, canonical)
