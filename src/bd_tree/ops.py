"""Filesystem operations on the version-only numeric node store."""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import BreakdownError
from .frontmatter import (
    FrontMatterError,
    parse_document,
    render_document,
    rewrite_contains,
    rewrite_links,
)
from .fsutil import atomic_copy, atomic_write, publish_new, store_lock
from .graph import (
    layer_reaches,
    parse_band_fields,
    relative_store,
    require_layer,
    require_layer_value,
)
from .loader import (
    ROOT_FILE,
    STORE_DIR,
    is_bare_ref,
    is_full_ref,
    load,
    load_view,
    node_path,
    parse_ref,
    parse_selector,
    ref_of,
    resolve_store_root,
)
from .model import DiffEntry, Node, Store
from .navigate import resolve_ref


def _logical_id(text: str | int) -> int:
    try:
        node_id, _version = parse_selector(text)
    except ValueError:
        raise BreakdownError(f"invalid id {text!r}") from None
    return node_id


def _existing(store: Store, ref: str, role: str) -> Node:
    node = store.nodes.get(ref)
    if node is None:
        raise BreakdownError(f"{role} {ref} does not exist")
    return node


def _reaches(store: Store, start: str, target: str) -> bool:
    """Whether ``target`` is reachable from ``start`` through the topology."""
    seen: set[str] = set()
    stack = [start]
    while stack:
        current = stack.pop()
        if current == target:
            return True
        if current in seen:
            continue
        seen.add(current)
        stack.extend(store.children(current))
    return False


def _stage_value(node: Node) -> int | None:
    """The node's integer ``stage``, or ``None`` when missing/invalid."""
    value = node.meta.get("stage")
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _order_value(node: Node) -> int:
    """The node's integer ``order``; a missing or invalid value is ``0``."""
    value = node.meta.get("order", 0)
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return value


def _link_sort_key(item: Any) -> tuple[int, int, int, str]:
    target = _link_target(item)
    if target is None:
        return (1, 0, 0, "")
    node_id, version = parse_ref(target)
    return (0, node_id, version, "")


def _insert_sorted_link(links: list[Any], edge: Any) -> list[Any]:
    """Insert ``edge`` so the list stays ordered by target ref (merge-friendly)."""
    key = _link_sort_key(edge)
    for index, item in enumerate(links):
        if _link_sort_key(item) > key:
            return links[:index] + [edge] + links[index:]
    return links + [edge]


def _raw_links(document) -> list[Any]:
    raw = document.meta.get("links")
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(
        isinstance(item, dict)
        or (isinstance(item, (str, int)) and not isinstance(item, bool))
        for item in raw
    ):
        raise BreakdownError("'links' must be a list of mappings or refs")
    return [dict(item) if isinstance(item, dict) else item for item in raw]


def _link_target(item: Any) -> str | None:
    value = item.get("to") if isinstance(item, dict) else item
    if value is None:
        return None
    text = str(value).strip()
    return text if is_full_ref(text) else None


def _link_type(item: Any, store: Store) -> str | None:
    """An item's effective edge type: its own, or the target's ``type``."""
    if isinstance(item, dict):
        value = item.get("type")
        return value if isinstance(value, str) else None
    target = _link_target(item)
    node = store.nodes.get(target) if target is not None else None
    value = node.meta.get("type") if node is not None else None
    return value if isinstance(value, str) and value.strip() else None


_ROOT_BODY = "# Root\n\nState the intent of this graph here.\n"
_GITIGNORE = "# generated work area (bd work)\nbd_work/\n"
_GITIGNORE_ENTRY = "bd_work/"


def _ensure_work_ignored(project: Path) -> None:
    """Keep the derived work area out of git without rewriting other lines."""
    path = project / ".gitignore"
    if not path.exists():
        path.write_text(_GITIGNORE, encoding="utf-8", newline="")
        return
    text = path.read_text(encoding="utf-8")
    if any(line.strip() == _GITIGNORE_ENTRY for line in text.splitlines()):
        return
    if text and not text.endswith("\n"):
        text += "\n"
    path.write_text(text + _GITIGNORE_ENTRY + "\n", encoding="utf-8", newline="")


def _serialized(func):
    """Run a structural writer under the store lock (reentrant per thread)."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        root = args[0] if args else kwargs.get("root", ".")
        with store_lock(resolve_store_root(root)):
            return func(*args, **kwargs)

    return wrapper


def init_store(root: str | Path = ".", *, graph: bool = False) -> Path:
    """Create the canonical project with a hidden store and return its root.

    The default store is containment (``contains: []``).  ``graph=True`` writes
    a root with ``band: root``, no ``stage``, no ``contains`` and no links,
    which the topology detection reads as a relative-band graph store ready
    for ``bd new --parent --band``.
    """
    project = Path(root).resolve()
    hidden = project / STORE_DIR / "nodes"
    legacy = project / "nodes"
    for label, nodes in ((".bd_tree/nodes", hidden), ("nodes", legacy)):
        if nodes.is_dir() and any(nodes.iterdir()):
            raise BreakdownError(
                f"store already exists at {project} ({label} is not empty)"
            )
    hidden.mkdir(parents=True, exist_ok=True)
    target = node_path(project / STORE_DIR, 1, 1)
    if graph:
        meta: dict[str, Any] = {"id": 1, "title": "Root", "band": "root"}
    else:
        meta = {"id": 1, "title": "Root", "contains": []}
    target.write_text(
        render_document(meta, _ROOT_BODY),
        encoding="utf-8",
        newline="",
    )
    _ensure_work_ignored(project)
    return project


def versions(root: str | Path, node_id: str | int) -> list[Node]:
    """Every existing file for a logical id, ascending by version."""
    return load(root).versions(_logical_id(node_id))


@_serialized
def clone(
    root: str | Path,
    ref: str | int,
    version: int | None = None,
    *,
    subtree: bool = False,
) -> list[tuple[str, str]]:
    """Copy a node, or its whole containment subtree, to new versions.

    The copy keeps the source bytes, including ``links``.  With ``subtree``,
    every cloned parent is then rewired to the cloned children, so the result
    is a self-contained copy.  Nothing is wired into the original view; use
    :func:`replace` for that.  Returns ``(source, clone)`` pairs.
    """
    root = resolve_store_root(root)
    store = load(root)
    source_ref = resolve_ref(store, ref)
    _existing(store, source_ref, "source")

    if subtree:
        if version is not None:
            raise BreakdownError("--version cannot be combined with --subtree")
        view = load_view(store, source_ref)
        errors = [issue for issue in view.issues if issue.level == "error"]
        if errors:
            raise BreakdownError(
                "cannot clone an invalid view: "
                + "; ".join(issue.message for issue in errors)
            )
        order = list(view.nodes)
        seen_ids: set[int] = set()
        for old_ref in order:
            node = store.nodes[old_ref]
            if node.id in seen_ids:
                raise BreakdownError(
                    f"cannot clone {source_ref}: the view holds two versions "
                    f"of id {node.id}"
                )
            seen_ids.add(node.id)
    else:
        order = [source_ref]

    used: dict[int, set[int]] = {}
    mapping: dict[str, str] = {}
    for old_ref in order:
        node = store.nodes[old_ref]
        taken = used.setdefault(
            node.id,
            {other.version for other in store.nodes.values() if other.id == node.id},
        )
        if version is None:
            target_version = 1
            while target_version in taken:
                target_version += 1
        else:
            if isinstance(version, bool) or not isinstance(version, int) or version < 1:
                raise BreakdownError(f"invalid version {version!r}")
            if version in taken:
                raise BreakdownError(
                    f"version {ref_of(node.id, version)} already exists"
                )
            target_version = version
        target_ref = ref_of(node.id, target_version)
        target = node_path(root, node.id, target_version)
        if target.exists():
            raise BreakdownError(f"version {target_ref} already exists")
        # Byte copy: the clone keeps the source file's declared contains/links.
        atomic_copy(node.path, target)
        taken.add(target_version)
        mapping[old_ref] = target_ref

    if subtree and store.model == "graph":
        # Rewire every cloned edge whose target was cloned too, leaving edges
        # that leave the subtree pointing at the original nodes.
        for old_ref, new_ref in mapping.items():
            target = node_path(root, *parse_ref(new_ref))
            document = parse_document(target.read_text(encoding="utf-8"))
            links = _raw_links(document)
            changed = False
            new_links: list[Any] = []
            for item in links:
                mapped = _link_target(item)
                if mapped in mapping:
                    replacement = mapping[mapped]
                    item = (
                        {**item, "to": replacement}
                        if isinstance(item, dict)
                        else replacement
                    )
                    changed = True
                new_links.append(item)
            if changed:
                atomic_write(
                    target,
                    document.with_raw_fm(
                        rewrite_links(document.raw_fm, new_links)
                    ),
                )
    elif subtree:
        for old_ref, new_ref in mapping.items():
            old_node = store.nodes[old_ref]
            new_children = [mapping.get(child, child) for child in old_node.contains]
            if new_children == old_node.contains:
                continue
            target = node_path(root, *parse_ref(new_ref))
            document = parse_document(target.read_text(encoding="utf-8"))
            atomic_write(
                target,
                document.with_raw_fm(
                    rewrite_contains(document.raw_fm, new_children)
                ),
            )

    return [(old_ref, mapping[old_ref]) for old_ref in order]


@_serialized
def replace(
    root: str | Path, old: str | int, new: str | int
) -> tuple[str, str, str]:
    """Swap ``old`` for ``new`` in ``old``'s parent's containment list.

    The position is preserved and the old node file is untouched, so it stays
    a peer version.  When ``old`` is the store root, ``ROOT`` is repointed to
    ``new`` instead.  Returns ``(old_ref, parent_ref_or_ROOT, new_ref)``.
    """
    root = resolve_store_root(root)
    store = load(root)
    old_ref = resolve_ref(store, old)
    new_ref = resolve_ref(store, new)
    _existing(store, old_ref, "old ref")
    _existing(store, new_ref, "new ref")
    if old_ref == new_ref:
        raise BreakdownError(f"refusing to replace {old_ref} with itself")

    if store.model == "graph":
        repointed: list[str] = []
        for node in store.nodes.values():
            document = parse_document(node.path.read_text(encoding="utf-8"))
            links = _raw_links(document)
            changed = False
            new_links: list[Any] = []
            for item in links:
                if _link_target(item) == old_ref:
                    item = (
                        {**item, "to": new_ref}
                        if isinstance(item, dict)
                        else new_ref
                    )
                    changed = True
                new_links.append(item)
            if changed:
                atomic_write(
                    node.path,
                    document.with_raw_fm(rewrite_links(document.raw_fm, new_links)),
                )
                repointed.append(node.ref)
        was_root = store.root_ref == old_ref
        if was_root:
            set_root(root, new_ref)
        if not repointed and not was_root:
            raise BreakdownError(
                f"{old_ref} has no inbound links; wire {new_ref} with bd link"
            )
        return old_ref, "ROOT" if was_root else "links", new_ref

    view = load_view(store)
    parents = [
        ref for ref, node in view.nodes.items() if old_ref in node.contains
    ]
    if len(parents) > 1:
        raise BreakdownError(
            f"{old_ref} has multiple parents in view {view.ref}: "
            + ", ".join(parents)
        )
    if not parents:
        if store.root_ref == old_ref:
            set_root(root, new_ref)
            return old_ref, "ROOT", new_ref
        raise BreakdownError(
            f"{old_ref} is not in the default view; wire {new_ref} with "
            "bd contain"
        )

    parent = parents[0]
    siblings = list(store.nodes[parent].contains)
    index = siblings.index(old_ref)
    next_ref = siblings[index + 1] if index + 1 < len(siblings) else None
    uncontain(root, parent, old_ref)
    contain(root, parent, new_ref, before=next_ref)
    return old_ref, parent, new_ref


@_serialized
def set_root(root: str | Path, ref: str | int) -> Path:
    """Write the store-level ``ROOT`` file to an existing, fully qualified ref."""
    root = resolve_store_root(root)
    store = load(root)
    canonical = resolve_ref(store, ref)
    if canonical not in store.nodes:
        raise BreakdownError(f"root ref {canonical} does not exist")
    path = root / ROOT_FILE
    atomic_write(path, canonical + "\n")
    return path


@_serialized
def clear_root(root: str | Path) -> Path | None:
    """Remove the ``ROOT`` file; the lowest ``(id, version)`` becomes the root."""
    path = resolve_store_root(root) / ROOT_FILE
    if not path.is_file():
        return None
    path.unlink()
    return path


@_serialized
def delete(root: str | Path, ref: str | int, *, force: bool = False) -> Path:
    """Delete one node file, refusing anything still bound into the graph."""
    root = Path(root).resolve()
    store = load(root)
    canonical = resolve_ref(store, ref)
    node = _existing(store, canonical, "node")
    if not force:
        if store.root_ref == canonical:
            raise BreakdownError(
                f"refusing to delete the store root {canonical} (use --force)"
            )
        if _reaches(store, store.root_ref or canonical, canonical):
            raise BreakdownError(
                f"refusing to delete {canonical}: it is reachable from root "
                f"{store.root_ref} (use --force)"
            )
        referenced_by = [
            other.ref
            for other in store.nodes.values()
            if other.ref != canonical
            and (
                canonical in other.contains
                or any(link.to == canonical for link in other.links)
            )
        ]
        if referenced_by:
            raise BreakdownError(
                f"refusing to delete {canonical}: referenced by "
                + ", ".join(sorted(referenced_by))
                + " (use --force)"
            )
    node.path.unlink()
    return node.path


def diff(root: str | Path, left: str | int, right: str | int) -> list[DiffEntry]:
    """Compare two containment views id by id."""
    store = load(root)
    a = load_view(store, resolve_ref(store, left))
    b = load_view(store, resolve_ref(store, right))
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


NEW_NODE_DEFAULTS: dict[str, Any] = {"title": "", "summary": ""}


@_serialized
def new_node(
    root: str | Path,
    *,
    parent: str | int | None = None,
    fields: dict[str, Any] | None = None,
    body: str = "",
    links: list[dict[str, Any]] | None = None,
    stage: int | None = None,
    layer: str | None = None,
    band: str | None = None,
    subpath: str | None = None,
    order: int | None = None,
    link_type: str = "breaks_down",
) -> Path:
    """Create the next global id at version 1 and wire it to ``parent``.

    Containment appends the new ref to the parent's ``contains`` list.  A graph
    store instead appends a typed edge to the parent's ``links``.  An absolute
    graph (some node declares ``stage``) sets an integer ``stage`` (parent
    stage + 1, else 0); a relative graph (no ``stage`` anywhere) requires
    ``--band`` (with optional ``--subpath``) or the older ``--layer`` path
    shorthand, and derives the band from it.  Both set ``order`` (0).

    The whole id-pick/parent-rewrite/publish sequence holds the store lock, so
    concurrent writers get distinct ids and neither loses a sibling.  Both
    files are published atomically, so readers never see a partial document.
    """
    root = resolve_store_root(root)
    fields = dict(fields or {})
    if "id" in fields:
        raise BreakdownError("'id' is assigned by bd new and cannot be given")
    store = load(root)
    graph = store.model == "graph"

    if parent is None:
        if not graph:
            raise BreakdownError("a containment node needs a parent")
        parent_ref: str | None = None
        parent_node: Node | None = None
    else:
        parent_ref = resolve_ref(store, parent)
        parent_node = _existing(store, parent_ref, "parent")

    node_id = max((node.id for node in store.nodes.values()), default=0) + 1
    meta: dict[str, Any] = {"id": node_id}
    meta.update(NEW_NODE_DEFAULTS)
    meta.update(fields)
    if links:
        meta["links"] = links

    if graph and relative_store(store):
        if stage is not None or "stage" in fields:
            raise BreakdownError("stores without stage use --band or --layer")
        if layer is not None and (band is not None or subpath is not None):
            raise BreakdownError(
                "use either --layer or --band/--subpath, not both"
            )
        if "layer" in fields and (band is not None or subpath is not None):
            raise BreakdownError(
                "fields cannot mix 'layer' with --band/--subpath"
            )
        if ("band" in fields or "subpath" in fields) and layer is not None:
            raise BreakdownError(
                "fields cannot mix 'band'/'subpath' with --layer"
            )
        if layer is not None:
            if not isinstance(layer, str) or not layer.strip():
                raise BreakdownError("a band graph needs a non-empty --layer")
            parsed_layer = require_layer_value(layer)
            meta["layer"] = parsed_layer.raw
        elif band is not None or subpath is not None:
            parsed_layer = parse_band_fields(band, subpath)
            meta["band"] = parsed_layer.band
            if parsed_layer.subpath:
                meta["subpath"] = parsed_layer.subpath
        else:
            raise BreakdownError(
                "a band graph needs a non-empty --band (or --layer)"
            )
        if order is not None:
            if isinstance(order, bool) or not isinstance(order, int):
                raise BreakdownError(f"invalid order {order!r}")
            meta["order"] = order
        elif "order" not in meta:
            meta["order"] = 0
        if not isinstance(meta.get("order"), int) or isinstance(
            meta.get("order"), bool
        ):
            raise BreakdownError(
                f"invalid order {meta.get('order')!r} (expected an integer)"
            )
        if parent_node is not None:
            if not isinstance(link_type, str) or not link_type.strip():
                raise BreakdownError("link type must be a non-empty string")
            parent_layer = require_layer(parent_node)
            new_ref = f"{node_id}-1"
            if parent_layer.band == parsed_layer.band:
                if _order_value(parent_node) >= meta["order"]:
                    raise BreakdownError(
                        f"edge {parent_ref} -> {new_ref} is not forward within "
                        f"layer '{parent_layer.band}': order "
                        f"{_order_value(parent_node)} >= {meta['order']}"
                    )
            elif layer_reaches(store, parsed_layer.band, parent_layer.band):
                raise BreakdownError(
                    f"edge {parent_ref} -> {new_ref} ({link_type}) would create "
                    f"a layer cycle through '{parent_layer.band}' and "
                    f"'{parsed_layer.band}'"
                )
    elif graph:
        if band is not None or subpath is not None:
            raise BreakdownError("stores with stage use --stage")
        if layer is not None:
            meta["layer"] = layer
        if stage is not None:
            if isinstance(stage, bool) or not isinstance(stage, int):
                raise BreakdownError(f"invalid stage {stage!r}")
            meta["stage"] = stage
        elif "stage" not in meta:
            parent_stage = (
                _stage_value(parent_node) if parent_node is not None else None
            )
            meta["stage"] = parent_stage + 1 if parent_stage is not None else 0
        if not isinstance(meta.get("stage"), int) or isinstance(
            meta.get("stage"), bool
        ):
            raise BreakdownError(
                f"invalid stage {meta.get('stage')!r} (expected an integer)"
            )
        if order is not None:
            if isinstance(order, bool) or not isinstance(order, int):
                raise BreakdownError(f"invalid order {order!r}")
            meta["order"] = order
        elif "order" not in meta:
            meta["order"] = 0
        if not isinstance(meta.get("order"), int) or isinstance(
            meta.get("order"), bool
        ):
            raise BreakdownError(
                f"invalid order {meta.get('order')!r} (expected an integer)"
            )
        if parent_node is not None and (
            not isinstance(link_type, str) or not link_type.strip()
        ):
            raise BreakdownError("link type must be a non-empty string")

    target = node_path(root, node_id, 1)
    if target.exists():
        raise BreakdownError(f"node {node_id}-1 already exists at {target}")

    new_ref = ref_of(node_id, 1)
    if graph:
        if parent_node is not None:
            document = parse_document(parent_node.path.read_text(encoding="utf-8"))
            raw = _insert_sorted_link(
                _raw_links(document), {"to": new_ref, "type": link_type}
            )
            atomic_write(
                parent_node.path,
                document.with_raw_fm(rewrite_links(document.raw_fm, raw)),
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        publish_new(target, render_document(meta, body))
        return target

    siblings = store.effective_contains(parent_ref)
    document = parse_document(parent_node.path.read_text(encoding="utf-8"))
    rewritten = rewrite_contains(document.raw_fm, siblings + [new_ref])
    atomic_write(parent_node.path, document.with_raw_fm(rewritten))
    target.parent.mkdir(parents=True, exist_ok=True)
    publish_new(target, render_document(meta, body))
    return target


def _sibling_index(
    store: Store,
    siblings: list[str],
    before: str | int | None,
    after: str | int | None,
) -> int:
    before_ref = None if before is None else resolve_ref(store, before)
    after_ref = None if after is None else resolve_ref(store, after)
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


@_serialized
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
    store = load(root)
    if store.model == "graph":
        raise BreakdownError("graph stores use edges: bd link / bd unlink")
    parent_ref = resolve_ref(store, parent)
    child_ref = resolve_ref(store, child)
    parent_node = _existing(store, parent_ref, "parent")
    child_node = _existing(store, child_ref, "child")
    if parent_ref == child_ref:
        raise BreakdownError(f"refusing to contain {child_ref} in itself")
    if _reaches(store, child_ref, parent_ref):
        raise BreakdownError(
            f"refusing to create a containment cycle: "
            f"{child_ref} already reaches {parent_ref}"
        )
    subtree = load_view(store, parent_ref)
    clash = [
        ref
        for ref, node in subtree.nodes.items()
        if node.id == child_node.id and ref != child_ref
    ]
    if clash:
        raise BreakdownError(
            f"refusing to contain {child_ref}: the view of {parent_ref} already "
            f"holds version {clash[0]} of id {child_node.id}"
        )

    siblings = store.effective_contains(parent_ref)
    if child_ref in siblings:
        raise BreakdownError(f"{child_ref} is already contained by {parent_ref}")
    index = _sibling_index(store, siblings, before, after)
    new_contains = siblings[:index] + [child_ref] + siblings[index:]

    document = parse_document(parent_node.path.read_text(encoding="utf-8"))
    rewritten = rewrite_contains(document.raw_fm, new_contains)
    atomic_write(parent_node.path, document.with_raw_fm(rewritten))
    return parent_node.path


@_serialized
def uncontain(root: str | Path, parent: str | int, child: str | int) -> Path:
    """Remove ``child`` from ``parent``'s containment list; never delete it."""
    root = Path(root).resolve()
    store = load(root)
    if store.model == "graph":
        raise BreakdownError("graph stores use edges: bd link / bd unlink")
    parent_ref = resolve_ref(store, parent)
    child_ref = resolve_ref(store, child)
    parent_node = _existing(store, parent_ref, "parent")
    _existing(store, child_ref, "child")

    siblings = store.effective_contains(parent_ref)
    if child_ref not in siblings:
        raise BreakdownError(f"{child_ref} is not contained by {parent_ref}")
    new_contains = [ref for ref in siblings if ref != child_ref]

    document = parse_document(parent_node.path.read_text(encoding="utf-8"))
    rewritten = rewrite_contains(document.raw_fm, new_contains)
    atomic_write(parent_node.path, document.with_raw_fm(rewritten))
    return parent_node.path


@_serialized
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
    store = load(root)
    source_ref = resolve_ref(store, source)
    target_ref = resolve_ref(store, target)
    source_node = _existing(store, source_ref, "source")
    target_node = _existing(store, target_ref, "target")
    if store.model == "graph" and relative_store(store):
        source_layer = require_layer(source_node)
        target_layer = require_layer(target_node)
        if source_layer.band == target_layer.band:
            if _order_value(source_node) >= _order_value(target_node):
                raise BreakdownError(
                    f"edge {source_ref} -> {target_ref} ({link_type}) is not "
                    f"forward within layer '{source_layer.band}': order "
                    f"{_order_value(source_node)} >= {_order_value(target_node)}"
                )
        elif layer_reaches(store, target_layer.band, source_layer.band):
            raise BreakdownError(
                f"edge {source_ref} -> {target_ref} ({link_type}) would create "
                f"a layer cycle through '{source_layer.band}' and "
                f"'{target_layer.band}'"
            )
    elif store.model == "graph":
        source_stage = _stage_value(source_node)
        target_stage = _stage_value(target_node)
        if (
            source_stage is not None
            and target_stage is not None
            and source_stage >= target_stage
        ):
            raise BreakdownError(
                f"edge {source_ref} -> {target_ref} ({link_type}) is not "
                f"strictly forward: stage {source_stage} >= {target_stage}"
            )

    document = parse_document(source_node.path.read_text(encoding="utf-8"))
    links = _raw_links(document)
    for item in links:
        if (
            _link_target(item) == target_ref
            and _link_type(item, store) == link_type
        ):
            raise BreakdownError(
                f"link {source_ref} -> {target_ref} ({link_type}) already exists; "
                "use bd unlink first"
            )

    edge: dict[str, Any] = {"to": target_ref, "type": link_type}
    if propagates:
        edge["propagates"] = True
        edge["pinned"] = target_node.body_hash
    declared_type = target_node.meta.get("type")
    bare = (
        not propagates
        and isinstance(declared_type, str)
        and declared_type.strip()
        and declared_type == link_type
    )
    item = target_ref if bare else edge
    links = (
        _insert_sorted_link(links, item)
        if store.model == "graph"
        else links + [item]
    )
    rewritten = rewrite_links(document.raw_fm, links)
    atomic_write(source_node.path, document.with_raw_fm(rewritten))
    return source_node.path


@_serialized
def unlink(
    root: str | Path,
    source: str | int,
    target: str | int,
    *,
    link_type: str | None = None,
) -> Path:
    """Remove every matching edge; ``link_type`` narrows the match."""
    root = Path(root).resolve()
    store = load(root)
    source_ref = resolve_ref(store, source)
    target_ref = resolve_ref(store, target)
    source_node = _existing(store, source_ref, "source")
    _existing(store, target_ref, "target")

    document = parse_document(source_node.path.read_text(encoding="utf-8"))
    links = _raw_links(document)
    kept: list[Any] = []
    removed = 0
    for item in links:
        existing = _link_target(item)
        matches = existing == target_ref and (
            link_type is None or _link_type(item, store) == link_type
        )
        if matches:
            removed += 1
        else:
            kept.append(item)
    if removed == 0:
        suffix = f" ({link_type})" if link_type is not None else ""
        raise BreakdownError(f"no link {source_ref} -> {target_ref}{suffix} to remove")

    rewritten = rewrite_links(document.raw_fm, kept)
    atomic_write(source_node.path, document.with_raw_fm(rewritten))
    return source_node.path


@dataclass
class MigrationResult:
    """What a migration did, or would do under ``--dry-run``."""

    renames: list[tuple[str, str]] = field(default_factory=list)
    rewrites: list[str] = field(default_factory=list)
    dry_run: bool = False

    @property
    def count(self) -> int:
        return len(self.renames)


CLASSIC_FILENAME = re.compile(
    r"^(?P<id>[1-9]\d*)(?:-(?P<version>[1-9]\d*))?\.md$"
)


def _map_data_ref(
    value: object,
    mapping: dict[int, str],
    where: str,
    ambiguous: dict[int, set[str]],
) -> tuple[bool, object]:
    """Map one bare data ref through ``mapping``; return ``(changed, value)``.

    A bare ref whose id has no bare file cannot be resolved; it is collected in
    ``ambiguous`` so the caller can report every offender at once.
    """
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return False, value
    text = str(value).strip()
    if is_full_ref(text):
        return False, text
    if is_bare_ref(text):
        node_id = int(text)
        if node_id not in mapping:
            ambiguous.setdefault(node_id, set()).add(where)
            return False, value
        return True, mapping[node_id]
    return False, value


@_serialized
def migrate(root: str | Path, *, dry_run: bool = False) -> MigrationResult:
    """One-time, idempotent, in-place migration of a classic bare-file store."""
    root = resolve_store_root(root)
    nodes_dir = root / "nodes"
    if not nodes_dir.is_dir():
        raise BreakdownError(f"no node store at {nodes_dir}")
    result = MigrationResult(dry_run=dry_run)

    parsed: list[tuple[Path, int, int | None]] = []
    used: dict[int, set[int]] = {}
    for path in sorted(nodes_dir.glob("*.md")):
        match = CLASSIC_FILENAME.fullmatch(path.name)
        if not match:
            raise BreakdownError(
                f"cannot migrate: invalid node filename '{path.name}'"
            )
        node_id = int(match.group("id"))
        raw_version = match.group("version")
        file_version = int(raw_version) if raw_version is not None else None
        parsed.append((path, node_id, file_version))
        if file_version is not None:
            used.setdefault(node_id, set()).add(file_version)

    mapping: dict[int, str] = {}
    rename_of: dict[Path, Path] = {}
    for path, node_id, file_version in parsed:
        if file_version is not None:
            continue
        new_version = 1
        while new_version in used.get(node_id, set()):
            new_version += 1
        new_ref = ref_of(node_id, new_version)
        mapping[node_id] = new_ref
        new_path = nodes_dir / f"{new_ref}.md"
        rename_of[path] = new_path
        result.renames.append(
            (str(path.relative_to(root)), str(new_path.relative_to(root)))
        )
        used.setdefault(node_id, set()).add(new_version)

    ambiguous: dict[int, set[str]] = {}
    pending: list[tuple[Path, Path, str]] = []
    for path, _node_id, _file_version in parsed:
        target = rename_of.get(path, path)
        where = str(path.relative_to(root))
        text = path.read_text(encoding="utf-8")
        try:
            document = parse_document(text)
        except (OSError, FrontMatterError) as exc:
            raise BreakdownError(
                f"cannot migrate {where}: {exc}"
            ) from exc
        raw_fm = document.raw_fm
        changed = False

        contains = document.meta.get("contains")
        if isinstance(contains, list):
            new_contains: list[object] = []
            contains_changed = False
            for item in contains:
                item_changed, value = _map_data_ref(
                    item, mapping, where, ambiguous
                )
                contains_changed = contains_changed or item_changed
                new_contains.append(value)
            if contains_changed:
                raw_fm = rewrite_contains(raw_fm, [str(v) for v in new_contains])
                result.rewrites.append(f"{where}: contains {contains} -> {new_contains}")
                changed = True

        links = document.meta.get("links")
        if isinstance(links, list):
            new_links: list[object] = []
            links_changed = False
            for item in links:
                if isinstance(item, dict):
                    if "to" in item:
                        item_changed, value = _map_data_ref(
                            item["to"], mapping, where, ambiguous
                        )
                        if item_changed:
                            item = {**item, "to": value}
                            links_changed = True
                    new_links.append(item)
                elif isinstance(item, (str, int)) and not isinstance(item, bool):
                    item_changed, value = _map_data_ref(
                        item, mapping, where, ambiguous
                    )
                    links_changed = links_changed or item_changed
                    new_links.append(value)
                else:
                    new_links.append(item)
            if links_changed:
                raw_fm = rewrite_links(raw_fm, new_links)
                result.rewrites.append(f"{where}: links {links} -> {new_links}")
                changed = True

        if changed:
            pending.append((path, target, document.with_raw_fm(raw_fm)))

    root_path = root / ROOT_FILE
    root_text: str | None = None
    if root_path.is_file():
        value = root_path.read_text(encoding="utf-8").strip()
        if is_bare_ref(value):
            node_id = int(value)
            if node_id not in mapping:
                ambiguous.setdefault(node_id, set()).add(ROOT_FILE)
            else:
                root_text = mapping[node_id]
                result.rewrites.append(f"{ROOT_FILE}: {value} -> {root_text}")

    if ambiguous:
        details = "; ".join(
            f"id {node_id} in {', '.join(sorted(where))}"
            for node_id, where in sorted(ambiguous.items())
        )
        raise BreakdownError(
            "cannot migrate ambiguous bare refs (no bare file to map): " + details
        )

    if dry_run:
        return result

    for old, new, text in pending:
        if old != new:
            old.rename(new)
        new.write_text(text, encoding="utf-8", newline="")
    for old, new in rename_of.items():
        if not any(pending_old == old for pending_old, _n, _t in pending):
            old.rename(new)
    if root_text is not None:
        root_path.write_text(root_text + "\n", encoding="utf-8", newline="")
    return result
