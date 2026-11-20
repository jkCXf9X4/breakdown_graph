"""Load the flat numeric node store and resolve containment views.

A node lives at ``nodes/<id>.md`` (main, version 0) or
``nodes/<id>-<version>.md``.  The filename is the only identity and the only
version marker; the front matter carries arbitrary user metadata.  Containment
is a tree per view: ``contains:`` lists child refs in display order, and a
version that omits ``contains`` inherits the main version's list.
"""

from __future__ import annotations

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
STORE_DIR = ".bd_tree"

FILENAME = re.compile(r"^(?P<id>[1-9]\d*)(?:-(?P<version>[1-9]\d*))?\.md$")
REF = re.compile(r"^(?P<id>[1-9]\d*)(?:-(?P<version>[1-9]\d*))?$")


class FilenameError(ValueError):
    """A filename does not follow the numeric node grammar."""


def parse_ref(text: str | int) -> tuple[int, int]:
    """Parse ``5`` or ``5-1`` into ``(id, version)``; version 0 is main."""
    if isinstance(text, bool) or not isinstance(text, (str, int)):
        raise ValueError(f"invalid ref {text!r}")
    match = REF.fullmatch(str(text).strip())
    if not match:
        raise ValueError(f"invalid ref {text!r}")
    return int(match.group("id")), int(match.group("version") or 0)


def ref_of(node_id: int, version: int = 0) -> str:
    if node_id < 1:
        raise ValueError(f"invalid id {node_id!r}")
    if version < 0:
        raise ValueError(f"invalid version {version!r}")
    return str(node_id) if version == 0 else f"{node_id}-{version}"


def parse_filename(name: str) -> tuple[int, int]:
    """Parse ``<id>.md`` or ``<id>-<version>.md`` into ``(id, version)``."""
    if Path(name).name != name:
        raise FilenameError(f"not a bare filename: '{name}'")
    match = FILENAME.fullmatch(name)
    if not match:
        raise FilenameError(f"invalid node filename '{name}'")
    return int(match.group("id")), int(match.group("version") or 0)


def node_path(root: str | Path, node_id: int, version: int = 0) -> Path:
    return Path(root) / "nodes" / f"{ref_of(node_id, version)}{NODE_SUFFIX}"


def resolve_store_root(path: str | Path) -> Path:
    """Return the store root for a project root or a store root.

    A project may keep its store in ``.bd_tree/`` or expose the classic
    ``nodes/`` layout directly.  The classic layout wins when a candidate has
    both.  A path with neither is returned unchanged, so callers can report
    the missing directory themselves.
    """
    candidate = Path(path)
    if (candidate / "nodes").is_dir():
        return candidate.resolve()
    if (candidate / STORE_DIR / "nodes").is_dir():
        return (candidate / STORE_DIR).resolve()
    return candidate.resolve()


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
            try:
                target = ref_of(*parse_ref(item))
            except ValueError:
                _issue(
                    issues,
                    "error",
                    "invalid-link",
                    f"links[{index}] has invalid ref {item!r}",
                    path=path,
                    root=root,
                )
                continue
            links.append(Link(to=target, type="", raw=item))
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
        try:
            target = ref_of(*parse_ref(to)) if to is not None else None
        except ValueError:
            target = None
        if target is None:
            _issue(
                issues,
                "error",
                "invalid-link-target",
                f"links[{index}] has invalid 'to' {to!r}",
                path=path,
                root=root,
            )
            continue
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
                to=target,
                type=ltype,
                pinned=pinned,
                propagates=propagates,
                raw=dict(item),
            )
        )
        raws.append(dict(item))
    return links, raws


def _parse_contains(
    meta: dict[str, Any], issues: list[Issue], path: Path, root: Path
) -> list[str] | None:
    if "contains" not in meta or meta.get("contains") is None:
        return None
    raw = meta.get("contains")
    if not isinstance(raw, list):
        _issue(
            issues,
            "error",
            "invalid-contains",
            "'contains' must be a list",
            path=path,
            root=root,
        )
        return None
    refs: list[str] = []
    for index, item in enumerate(raw):
        try:
            ref = ref_of(*parse_ref(item))
        except ValueError:
            _issue(
                issues,
                "error",
                "invalid-contains",
                f"contains[{index}] has invalid ref {item!r}",
                path=path,
                root=root,
            )
            continue
        refs.append(ref)
    return refs


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
    contains = _parse_contains(meta, issues, path, root)
    legacy = meta.get("legacy")
    return Node(
        id=parsed_id,
        version=parsed_version,
        ref=ref,
        contains=contains,
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
    mains: set[int] = set()
    versioned: set[int] = set()
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
        if parsed_version == 0:
            mains.add(parsed_id)
        else:
            versioned.add(parsed_id)

        node = _parse_node(path, parsed_id, parsed_version, issues, root)
        records.append(
            Record(path=path, node_id=parsed_id, version=parsed_version, node=node)
        )

    for node_id in sorted(versioned - mains):
        _issue(
            issues,
            "error",
            "missing-main",
            f"id {node_id} has version files but no main nodes/{node_id}.md",
            node=str(node_id),
            root=root,
        )
    return records, issues


def _read_declared_root(root: Path, issues: list[Issue]) -> str | None:
    """Read the optional store-level ``ROOT`` file: one ref, nothing else."""
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
    try:
        return ref_of(*parse_ref(text))
    except ValueError:
        _issue(
            issues,
            "error",
            "invalid-root",
            f"ROOT file does not contain a ref: {text!r}",
            path=path,
            root=root,
        )
        return None


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


def load_view(root: str | Path | Store, ref: str | int = "1") -> View:
    """Walk effective ``contains`` from ``ref`` and return the closure."""
    store = root if isinstance(root, Store) else load(root)
    issues: list[Issue] = []
    try:
        canonical = ref_of(*parse_ref(ref))
    except ValueError:
        issues.append(Issue("error", "invalid-ref", f"invalid view ref {ref!r}"))
        return View(store=store, ref=str(ref), nodes={}, edges=[], issues=issues)

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

    included: dict[str, Node] = {}
    parents: dict[str, str] = {}
    path: list[str] = []

    def walk(ref: str, parent: str | None) -> None:
        if ref in path:
            cycle = path[path.index(ref) :] + [ref]
            issues.append(
                Issue(
                    "error",
                    "containment-cycle",
                    "containment cycle: " + " -> ".join(cycle),
                    node=ref,
                )
            )
            return
        if ref in included:
            previous = parents.get(ref)
            if parent is not None and previous != parent:
                issues.append(
                    Issue(
                        "error",
                        "multiple-parents",
                        f"node '{ref}' is reached through two parents in view "
                        f"{canonical}: '{previous}', '{parent}'",
                        node=ref,
                    )
                )
            return
        node = store.nodes.get(ref)
        if node is None:
            issues.append(
                Issue(
                    "error",
                    "missing-target",
                    f"contains target '{ref}' does not exist",
                    node=path[-1] if path else None,
                )
            )
            return
        included[ref] = node
        parents[ref] = parent or ""
        path.append(ref)
        for child in store.effective_contains(ref):
            walk(child, ref)
        path.pop()

    walk(canonical, None)

    listed = {
        child
        for node in store.nodes.values()
        for child in store.effective_contains(node.ref)
    }
    containment_roots = {
        node.ref for node in store.nodes.values() if node.ref not in listed
    }

    edges: list[Edge] = []
    for node in included.values():
        for link in node.links:
            if link.to in included:
                edges.append(
                    Edge(
                        node.ref,
                        link.to,
                        link.type,
                        link.pinned,
                        "link",
                        link.propagating,
                    )
                )
            elif link.to in store.nodes:
                if link.to in containment_roots:
                    continue
                issues.append(
                    Issue(
                        "warning",
                        "external-link",
                        f"link to '{link.to}' ({link.type}) outside view {canonical}",
                        node=node.ref,
                    )
                )
            else:
                issues.append(
                    Issue(
                        "error",
                        "dangling-link",
                        f"link to missing node '{link.to}' ({link.type})",
                        node=node.ref,
                    )
                )
    return View(
        store=store,
        ref=canonical,
        nodes=included,
        edges=edges,
        issues=issues,
    )
