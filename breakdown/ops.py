"""Filesystem operations on the numeric, versioned node store."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .errors import BreakdownError
from .frontmatter import (
    parse_document,
    render_document,
    rewrite_contains,
    rewrite_links,
)
from .loader import load, load_view, node_path, parse_ref, ref_of
from .model import DiffEntry, Node, Store


def _logical_id(text: str | int) -> int:
    try:
        node_id, version = parse_ref(text)
    except ValueError:
        raise BreakdownError(f"invalid id {text!r}") from None
    if version != 0:
        raise BreakdownError(f"expected a bare id, got ref {text!r}")
    return node_id


def _version_ref(text: str | int) -> tuple[int, int]:
    try:
        node_id, version = parse_ref(text)
    except ValueError:
        raise BreakdownError(f"invalid ref {text!r}") from None
    if version == 0:
        raise BreakdownError(f"ref {text!r} is a main version, not a version")
    return node_id, version


def _canonical(text: str | int) -> str:
    try:
        return ref_of(*parse_ref(text))
    except ValueError:
        raise BreakdownError(f"invalid ref {text!r}") from None


def _existing(store: Store, ref: str, role: str) -> Node:
    node = store.nodes.get(ref)
    if node is None:
        raise BreakdownError(f"{role} {ref} does not exist")
    return node


def _reaches(store: Store, start: str, target: str) -> bool:
    """Whether ``target`` is reachable from ``start`` through effective contains."""
    seen: set[str] = set()
    stack = [start]
    while stack:
        current = stack.pop()
        if current == target:
            return True
        if current in seen:
            continue
        seen.add(current)
        stack.extend(store.effective_contains(current))
    return False


def _raw_links(document) -> list[dict[str, Any]]:
    raw = document.meta.get("links")
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(isinstance(item, dict) for item in raw):
        raise BreakdownError("'links' must be a list of mappings")
    return [dict(item) for item in raw]


def _strip_contains(path: Path) -> None:
    """Drop an explicit ``contains`` so a version inherits its main's list."""
    document = parse_document(path.read_text(encoding="utf-8"))
    if "contains" not in document.meta:
        return
    meta = dict(document.meta)
    meta.pop("contains", None)
    path.write_text(
        render_document(meta, document.body), encoding="utf-8", newline=""
    )


_ROOT_BODY = "# Root\n\nState the intent of this graph here.\n"


def init_store(root: str | Path = ".") -> Path:
    """Create a minimal store with one root node and return the store root."""
    root = Path(root).resolve()
    nodes = root / "nodes"
    if nodes.is_dir() and any(nodes.iterdir()):
        raise BreakdownError(f"store already exists at {root}")
    nodes.mkdir(parents=True, exist_ok=True)
    target = node_path(root, 1, 0)
    target.write_text(
        render_document(
            {"id": 1, "title": "Root", "home": "1.md", "contains": []}, _ROOT_BODY
        ),
        encoding="utf-8",
        newline="",
    )
    return root


def versions(root: str | Path, node_id: str | int) -> list[Node]:
    """Every existing file for a logical id, main first."""
    return load(root).versions(_logical_id(node_id))


def fork(
    root: str | Path, node_id: str | int, version: int | None = None
) -> Path:
    """Copy ``nodes/<id>.md`` to the next free (or explicit) version file."""
    root = Path(root).resolve()
    node_id = _logical_id(node_id)
    source = node_path(root, node_id, 0)
    if not source.is_file():
        raise BreakdownError(f"main node {node_id} not found at {source}")
    store = load(root)
    used = {node.version for node in store.versions(node_id)}
    if version is None:
        version = 1
        while version in used:
            version += 1
    else:
        if version < 1:
            raise BreakdownError(f"invalid version {version!r}")
        if version in used:
            raise BreakdownError(f"version {ref_of(node_id, version)} already exists")
    target = node_path(root, node_id, version)
    if target.exists():
        raise BreakdownError(f"version {ref_of(node_id, version)} already exists")
    shutil.copyfile(source, target)
    # A version inherits containment by default; copying a declared list would
    # give every child a second parent in that view.
    _strip_contains(target)
    return target


def promote(root: str | Path, ref: str | int, *, keep: bool = False) -> Path:
    """Copy a version's content onto the main file, preserving the tree."""
    root = Path(root).resolve()
    node_id, version = _version_ref(ref)
    source = node_path(root, node_id, version)
    if not source.is_file():
        raise BreakdownError(f"version {ref_of(node_id, version)} not found at {source}")
    store = load(root)
    node = store.nodes.get(ref_of(node_id, version))
    if node is None:
        raise BreakdownError(f"version {ref_of(node_id, version)} is not loadable")
    document = parse_document(source.read_text(encoding="utf-8"))
    meta = dict(document.meta)
    if node.contains is not None:
        meta["contains"] = list(node.contains)
    else:
        main = store.main(node_id)
        if main is not None and main.contains is not None:
            meta["contains"] = list(main.contains)
        else:
            meta.pop("contains", None)
    target = node_path(root, node_id, 0)
    target.write_text(
        render_document(meta, document.body), encoding="utf-8", newline=""
    )
    if keep:
        # The kept version now inherits the promoted main's containment.
        _strip_contains(source)
    else:
        source.unlink()
    return target


def retire_version(root: str | Path, ref: str | int) -> Path:
    """Delete a non-main version file."""
    root = Path(root).resolve()
    node_id, version = _version_ref(ref)
    path = node_path(root, node_id, version)
    if not path.is_file():
        raise BreakdownError(f"version {ref_of(node_id, version)} not found at {path}")
    path.unlink()
    return path


def diff(root: str | Path, left: str | int, right: str | int) -> list[DiffEntry]:
    """Compare two containment views id by id."""
    a = load_view(root, left)
    b = load_view(root, right)
    for view in (a, b):
        errors = [issue for issue in view.issues if issue.level == "error"]
        if errors:
            raise BreakdownError(
                f"view {view.ref} is invalid: "
                + "; ".join(issue.message for issue in errors)
            )
    left_nodes = {node.id: node for node in a.nodes.values()}
    right_nodes = {node.id: node for node in b.nodes.values()}
    entries: list[DiffEntry] = []
    for node_id in sorted(set(left_nodes) | set(right_nodes)):
        if node_id in left_nodes and node_id in right_nodes:
            state = (
                "same"
                if left_nodes[node_id].body == right_nodes[node_id].body
                else "changed"
            )
        elif node_id in left_nodes:
            state = "only-left"
        else:
            state = "only-right"
        entries.append(DiffEntry(node_id, state))
    return entries


def _derive_home(fields: dict[str, Any], node_id: int) -> str:
    """``{group}/{id}.md`` from the first of layer/group/type, else flat."""
    for key in ("layer", "group", "type"):
        value = fields.get(key)
        if isinstance(value, str) and value.strip():
            return f"{value.strip()}/{node_id}.md"
    return f"{node_id}.md"


def new_node(
    root: str | Path,
    *,
    parent: str | int,
    fields: dict[str, Any] | None = None,
    body: str = "",
    links: list[dict[str, Any]] | None = None,
) -> Path:
    """Create the next global id as a main file and append it to ``parent``."""
    root = Path(root).resolve()
    fields = dict(fields or {})
    if "id" in fields:
        raise BreakdownError("'id' is assigned by bd new and cannot be given")
    store = load(root)
    try:
        parent_ref = ref_of(*parse_ref(parent))
    except ValueError:
        raise BreakdownError(f"invalid parent ref {parent!r}") from None
    parent_node = store.nodes.get(parent_ref)
    if parent_node is None:
        raise BreakdownError(f"parent {parent_ref} does not exist")

    node_id = max((node.id for node in store.nodes.values()), default=0) + 1
    meta: dict[str, Any] = {"id": node_id}
    meta.update(fields)
    home = meta.get("home")
    if not isinstance(home, str) or not home.strip():
        meta["home"] = _derive_home(fields, node_id)
    if links:
        meta["links"] = links
    target = node_path(root, node_id, 0)
    if target.exists():
        raise BreakdownError(f"node {node_id} already exists at {target}")

    effective = store.effective_contains(parent_ref)
    new_contains = effective + [str(node_id)]
    document = parse_document(parent_node.path.read_text(encoding="utf-8"))
    rewritten = rewrite_contains(document.raw_fm, new_contains)
    parent_node.path.write_text(
        document.with_raw_fm(rewritten), encoding="utf-8", newline=""
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_document(meta, body), encoding="utf-8", newline="")
    return target


def _sibling_index(
    siblings: list[str], before: str | None, after: str | None
) -> int:
    before_ref = None if before is None else _canonical(before)
    after_ref = None if after is None else _canonical(after)
    if before_ref is not None and after_ref is not None:
        raise BreakdownError("use either --before or --after, not both")
    if before_ref is not None:
        if before_ref not in siblings:
            raise BreakdownError(f"{before_ref} is not contained by this parent")
        return siblings.index(before_ref)
    if after_ref is not None:
        if after_ref not in siblings:
            raise BreakdownError(f"{after_ref} is not contained by this parent")
        return siblings.index(after_ref) + 1
    return len(siblings)


def contain(
    root: str | Path,
    parent: str | int,
    child: str | int,
    *,
    before: str | int | None = None,
    after: str | int | None = None,
) -> Path:
    """Add ``child`` to ``parent``'s containment list, optionally positioned."""
    root = Path(root).resolve()
    parent_ref = _canonical(parent)
    child_ref = _canonical(child)
    store = load(root)
    parent_node = _existing(store, parent_ref, "parent")
    _existing(store, child_ref, "child")
    if parent_ref == child_ref:
        raise BreakdownError(f"refusing to contain {child_ref} in itself")
    if _reaches(store, child_ref, parent_ref):
        raise BreakdownError(
            f"refusing to create a containment cycle: "
            f"{child_ref} already reaches {parent_ref}"
        )

    siblings = store.effective_contains(parent_ref)
    if child_ref in siblings:
        raise BreakdownError(f"{child_ref} is already contained by {parent_ref}")
    index = _sibling_index(
        siblings,
        None if before is None else _canonical(before),
        None if after is None else _canonical(after),
    )
    new_contains = siblings[:index] + [child_ref] + siblings[index:]

    document = parse_document(parent_node.path.read_text(encoding="utf-8"))
    rewritten = rewrite_contains(document.raw_fm, new_contains)
    parent_node.path.write_text(
        document.with_raw_fm(rewritten), encoding="utf-8", newline=""
    )
    return parent_node.path


def uncontain(root: str | Path, parent: str | int, child: str | int) -> Path:
    """Remove ``child`` from ``parent``'s containment list; never delete it."""
    root = Path(root).resolve()
    parent_ref = _canonical(parent)
    child_ref = _canonical(child)
    store = load(root)
    parent_node = _existing(store, parent_ref, "parent")
    _existing(store, child_ref, "child")

    siblings = store.effective_contains(parent_ref)
    if child_ref not in siblings:
        raise BreakdownError(f"{child_ref} is not contained by {parent_ref}")
    new_contains = [ref for ref in siblings if ref != child_ref]

    document = parse_document(parent_node.path.read_text(encoding="utf-8"))
    # An empty explicit list must not fall back to inheriting main's list.
    rewritten = rewrite_contains(document.raw_fm, new_contains)
    parent_node.path.write_text(
        document.with_raw_fm(rewritten), encoding="utf-8", newline=""
    )
    return parent_node.path


def link(
    root: str | Path,
    source: str | int,
    target: str | int,
    *,
    link_type: str,
    propagates: bool = False,
) -> Path:
    """Append a typed link edge, pinning the target when it propagates."""
    root = Path(root).resolve()
    if not isinstance(link_type, str) or not link_type.strip():
        raise BreakdownError("link type must be a non-empty string")
    source_ref = _canonical(source)
    target_ref = _canonical(target)
    store = load(root)
    source_node = _existing(store, source_ref, "source")
    target_node = _existing(store, target_ref, "target")

    document = parse_document(source_node.path.read_text(encoding="utf-8"))
    links = _raw_links(document)
    for item in links:
        try:
            existing = ref_of(*parse_ref(item.get("to")))
        except ValueError:
            continue
        if existing == target_ref and item.get("type") == link_type:
            raise BreakdownError(
                f"link {source_ref} -> {target_ref} ({link_type}) already exists; "
                "use bd unlink first"
            )

    edge: dict[str, Any] = {"to": target_ref, "type": link_type}
    if propagates:
        edge["propagates"] = True
        edge["pinned"] = target_node.body_hash
    links.append(edge)
    rewritten = rewrite_links(document.raw_fm, links)
    source_node.path.write_text(
        document.with_raw_fm(rewritten), encoding="utf-8", newline=""
    )
    return source_node.path


def unlink(
    root: str | Path,
    source: str | int,
    target: str | int,
    *,
    link_type: str | None = None,
) -> Path:
    """Remove every matching edge; ``link_type`` narrows the match."""
    root = Path(root).resolve()
    source_ref = _canonical(source)
    target_ref = _canonical(target)
    store = load(root)
    source_node = _existing(store, source_ref, "source")
    _existing(store, target_ref, "target")

    document = parse_document(source_node.path.read_text(encoding="utf-8"))
    links = _raw_links(document)
    kept: list[dict[str, Any]] = []
    removed = 0
    for item in links:
        try:
            existing = ref_of(*parse_ref(item.get("to")))
        except ValueError:
            kept.append(item)
            continue
        matches = existing == target_ref and (
            link_type is None or item.get("type") == link_type
        )
        if matches:
            removed += 1
        else:
            kept.append(item)
    if removed == 0:
        suffix = f" ({link_type})" if link_type is not None else ""
        raise BreakdownError(f"no link {source_ref} -> {target_ref}{suffix} to remove")

    rewritten = rewrite_links(document.raw_fm, kept)
    source_node.path.write_text(
        document.with_raw_fm(rewritten), encoding="utf-8", newline=""
    )
    return source_node.path
