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
    rewrite_links,
)
from .fsutil import atomic_copy, atomic_write, publish_new, store_lock
from .graph import ring_distances
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

    The root node carries only identity metadata and no links; placement keys
    are retired, so nothing declares a band or stage.  ``graph`` is accepted
    and ignored for backwards compatibility.
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
    meta: dict[str, Any] = {"id": 1, "title": "Root"}
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
    depth: int | None = None,
) -> list[tuple[str, str]]:
    """Copy one node, or its undirected neighbourhood, to new versions.

    The copy keeps the source bytes, including ``links``.  With ``subtree``
    the whole weak component of the source is copied; ``depth=N`` narrows that
    to BFS rings ``0..N`` over authored links.  Every cloned node is then
    rewired to cloned targets, so the result is a self-contained copy.
    Nothing is wired into the original component; use :func:`replace` for
    that.  Returns ``(source, clone)`` pairs.
    """
    root = resolve_store_root(root)
    store = load(root)
    source_ref = resolve_ref(store, ref)
    _existing(store, source_ref, "source")

    neighbourhood = subtree or depth is not None
    if neighbourhood:
        if version is not None:
            raise BreakdownError(
                "--version cannot be combined with --subtree or --depth"
            )
        if depth is not None:
            if isinstance(depth, bool) or not isinstance(depth, int) or depth < 0:
                raise BreakdownError(f"invalid depth {depth!r}")
        distances = ring_distances(store, source_ref)
        selected = [
            old_ref
            for old_ref, distance in distances.items()
            if depth is None or distance <= depth
        ]
        order = sorted(
            selected,
            key=lambda old_ref: (
                distances[old_ref],
                store.nodes[old_ref].id,
                store.nodes[old_ref].version,
            ),
        )
        seen_ids: dict[int, str] = {}
        for old_ref in order:
            node = store.nodes[old_ref]
            if node.id in seen_ids:
                raise BreakdownError(
                    f"cannot clone {source_ref}: the subtree holds two versions "
                    f"of id {node.id}"
                )
            seen_ids[node.id] = old_ref
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
        # Byte copy: the clone keeps the source file's declared links.
        atomic_copy(node.path, target)
        taken.add(target_version)
        mapping[old_ref] = target_ref

    if neighbourhood:
        # Rewire every cloned edge whose target was cloned too, leaving edges
        # that leave the neighbourhood pointing at the original nodes.
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

    return [(old_ref, mapping[old_ref]) for old_ref in order]


@_serialized
def replace(
    root: str | Path, old: str | int, new: str | int
) -> tuple[str, str, str]:
    """Repoint every inbound link from ``old`` to ``new``.

    The old node file is untouched, so it stays a peer version.  When ``old``
    is the store root, ``ROOT`` is repointed to ``new`` instead.  Returns
    ``(old_ref, parent_ref_or_ROOT, new_ref)``.
    """
    root = resolve_store_root(root)
    store = load(root)
    old_ref = resolve_ref(store, old)
    new_ref = resolve_ref(store, new)
    _existing(store, old_ref, "old ref")
    _existing(store, new_ref, "new ref")
    if old_ref == new_ref:
        raise BreakdownError(f"refusing to replace {old_ref} with itself")

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
    """Delete one node file, refusing the root and authored inbound targets."""
    root = Path(root).resolve()
    store = load(root)
    canonical = resolve_ref(store, ref)
    node = _existing(store, canonical, "node")
    if not force:
        if store.root_ref == canonical:
            raise BreakdownError(
                f"refusing to delete the store root {canonical} (use --force)"
            )
        referenced_by = sorted(
            other.ref
            for other in store.nodes.values()
            if other.ref != canonical
            and any(link.to == canonical for link in other.links)
        )
        if referenced_by:
            raise BreakdownError(
                f"refusing to delete {canonical}: inbound target of "
                + ", ".join(referenced_by)
                + " (use --force)"
            )
    node.path.unlink()
    return node.path


def diff(root: str | Path, left: str | int, right: str | int) -> list[DiffEntry]:
    """Compare two link views id by id."""
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
    link_type: str = "breaks_down",
) -> Path:
    """Create the next global id at version 1 and wire it to ``parent``.

    No authored placement is written: bands, stages and orders are retired.
    A typed edge is appended to the parent's ``links`` when ``parent`` is
    given; without a parent the node is a new component of its own.

    The whole id-pick/parent-rewrite/publish sequence holds the store lock, so
    concurrent writers get distinct ids and neither loses a sibling.  Both
    files are published atomically, so readers never see a partial document.
    """
    root = resolve_store_root(root)
    fields = dict(fields or {})
    if "id" in fields:
        raise BreakdownError("'id' is assigned by bd new and cannot be given")
    store = load(root)

    if parent is None:
        parent_node: Node | None = None
    else:
        parent_node = _existing(store, resolve_ref(store, parent), "parent")
        if not isinstance(link_type, str) or not link_type.strip():
            raise BreakdownError("link type must be a non-empty string")

    node_id = max((node.id for node in store.nodes.values()), default=0) + 1
    meta: dict[str, Any] = {"id": node_id}
    meta.update(NEW_NODE_DEFAULTS)
    meta.update(fields)
    if links:
        meta["links"] = links

    target = node_path(root, node_id, 1)
    if target.exists():
        raise BreakdownError(f"node {node_id}-1 already exists at {target}")

    new_ref = ref_of(node_id, 1)
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


@_serialized
def link(
    root: str | Path,
    source: str | int,
    target: str | int,
    *,
    link_type: str,
    propagates: bool = False,
    symmetric: bool = False,
    inverse: str | None = None,
) -> Path:
    """Append a typed link edge, pinning the target when it propagates.

    Direction is only a label: back-edges, reciprocal edges and cycles are
    legal, and targets stay sorted.  A symmetric link is the single authored
    master of a two-way relation; the opposite is derived at load time, never
    written.  ``inverse`` names the derived edge's type and requires
    ``symmetric``.  A ref may not link to itself.
    """
    root = Path(root).resolve()
    if not isinstance(link_type, str) or not link_type.strip():
        raise BreakdownError("link type must be a non-empty string")
    if inverse is not None:
        if not symmetric:
            raise BreakdownError("--inverse requires --symmetric")
        if not isinstance(inverse, str) or not inverse.strip():
            raise BreakdownError("inverse type must be a non-empty string")
        inverse = inverse.strip()
    if symmetric and propagates:
        raise BreakdownError("propagates cannot be combined with symmetric")
    store = load(root)
    source_ref = resolve_ref(store, source)
    target_ref = resolve_ref(store, target)
    source_node = _existing(store, source_ref, "source")
    target_node = _existing(store, target_ref, "target")
    if source_ref == target_ref:
        raise BreakdownError(
            f"link {source_ref} -> {target_ref} ({link_type}) is a self-loop; "
            "a ref cannot link to itself"
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
    if symmetric:
        edge["symmetric"] = True
        if inverse is not None:
            edge["inverse"] = inverse
    declared_type = target_node.meta.get("type")
    bare = (
        not propagates
        and not symmetric
        and isinstance(declared_type, str)
        and declared_type.strip()
        and declared_type == link_type
    )
    item = target_ref if bare else edge
    links = _insert_sorted_link(links, item)
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


def _key_pattern(key: str) -> re.Pattern[str]:
    return re.compile(rf"^{re.escape(key)}\s*:")


def _replace_block(lines: list[str], key: str, block: list[str]) -> list[str]:
    """Replace a top-level key and its continuation lines with ``block``."""
    pattern = _key_pattern(key)
    start = next(
        (index for index, line in enumerate(lines) if pattern.match(line)), None
    )
    if start is None:
        return lines + block
    end = start + 1
    while end < len(lines):
        line = lines[end]
        if line and not line[0].isspace() and not line.startswith("- "):
            break
        end += 1
    return lines[:start] + block + lines[end:]


def _finish(lines: list[str], raw_fm: str) -> str:
    rendered = "\n".join(lines)
    if raw_fm.endswith("\n") or not raw_fm:
        rendered += "\n"
    return rendered


def _remove_key(raw_fm: str, key: str) -> str:
    """Remove a top-level key and its continuation lines."""
    return _finish(_replace_block(raw_fm.splitlines(), key, []), raw_fm)


def _ref_text_key(text: str) -> tuple[int, int, int, str]:
    try:
        node_id, version = parse_ref(text)
    except (TypeError, ValueError):
        return (1, 0, 0, str(text))
    return (0, node_id, version, "")


@_serialized
def migrate(
    root: str | Path,
    *,
    dry_run: bool = False,
    link_type: str = "breaks_down",
    symmetric_types: list[str] | None = None,
    inverse_types: dict[str, str] | None = None,
) -> MigrationResult:
    """One-time, idempotent, in-place migration of a classic containment store.

    Classic bare filenames are versioned first.  Every ``contains`` list becomes
    typed ``links``; scalar links gain an explicit type; every list is sorted by
    ref.  Retired placement keys (``band``, ``subpath``, ``layer``, ``stage``,
    ``order``) are stripped from every node, and ``band_layout`` /
    ``band_order`` from the ROOT node, while bodies and unrelated front matter
    are preserved byte for byte.

    The flags also work on an already-migrated store: ``symmetric_types`` marks
    every master link of a type and ``inverse_types`` marks a type and names its
    derived opposite.  Running the same migration twice makes no further
    changes.
    """
    if not isinstance(link_type, str) or not link_type.strip():
        raise BreakdownError("link type must be a non-empty string")
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

    source_of: dict[Path, Path] = {
        rename_of.get(path, path): path for path, _nid, _ver in parsed
    }
    docs: dict[Path, Any] = {}
    for path, _node_id, _file_version in parsed:
        target = rename_of.get(path, path)
        where = str(path.relative_to(root))
        try:
            docs[target] = parse_document(path.read_text(encoding="utf-8"))
        except (OSError, FrontMatterError) as exc:
            raise BreakdownError(f"cannot migrate {where}: {exc}") from exc

    target_by_ref = {target.stem: target for target in docs}

    def target_type(ref: str) -> str | None:
        target = target_by_ref.get(ref)
        if target is None:
            return None
        value = docs[target].meta.get("type")
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    ambiguous: dict[int, set[str]] = {}
    converted: dict[Path, list[str]] = {}
    for target, document in docs.items():
        contains = document.meta.get("contains")
        if not isinstance(contains, list):
            continue
        where = str(source_of[target].relative_to(root))
        children: list[str] = []
        for item in contains:
            _changed, value = _map_data_ref(item, mapping, where, ambiguous)
            children.append(str(value).strip())
        converted[target] = children

    final_links: dict[str, list[Any]] = {}
    original_links: dict[str, list[Any]] = {}
    for target, document in docs.items():
        where = str(source_of[target].relative_to(root))
        original = _raw_links(document)
        original_links[target.stem] = original
        new_links: list[Any] = []
        for item in original:
            if isinstance(item, dict):
                if "to" in item:
                    item_changed, value = _map_data_ref(
                        item["to"], mapping, where, ambiguous
                    )
                    if item_changed:
                        item = {**item, "to": value}
                new_links.append(item)
            elif isinstance(item, (str, int)) and not isinstance(item, bool):
                _item_changed, value = _map_data_ref(
                    item, mapping, where, ambiguous
                )
                target_ref = str(value).strip()
                new_links.append(
                    {
                        "to": target_ref,
                        "type": target_type(target_ref) or link_type,
                    }
                )
            else:
                new_links.append(item)
        if target in converted:
            for child_ref in converted[target]:
                new_links.append({"to": child_ref, "type": link_type})
        new_links.sort(key=_link_sort_key)
        final_links[target.stem] = new_links

    symmetric_set: set[str] = set()
    for kind in symmetric_types or ():
        if not isinstance(kind, str) or not kind.strip():
            raise BreakdownError("--symmetric needs a non-empty link type")
        symmetric_set.add(kind.strip())
    inverse_map: dict[str, str] = {}
    for kind, opposite in (inverse_types or {}).items():
        if not isinstance(kind, str) or not kind.strip():
            raise BreakdownError("--inverse needs a non-empty link type")
        if not isinstance(opposite, str) or not opposite.strip():
            raise BreakdownError(
                f"--inverse {kind}: needs a non-empty inverse type"
            )
        inverse_map[kind.strip()] = opposite.strip()
    symmetric_set |= set(inverse_map)
    if symmetric_set:
        for ref, links in final_links.items():
            touched = 0
            kinds: set[str] = set()
            for index, item in enumerate(links):
                if not isinstance(item, dict):
                    continue
                etype = item.get("type")
                if not isinstance(etype, str) or etype.strip() not in symmetric_set:
                    continue
                clean = etype.strip()
                updated = {
                    key: value
                    for key, value in item.items()
                    if key not in ("propagates", "pinned")
                }
                updated["symmetric"] = True
                opposite = inverse_map.get(clean)
                if opposite is not None:
                    updated["inverse"] = opposite
                if updated != item:
                    links[index] = updated
                    touched += 1
                kinds.add(clean)
            if touched:
                where = str(source_of[target_by_ref[ref]].relative_to(root))
                detail = ", ".join(sorted(kinds))
                result.rewrites.append(
                    f"{where}: symmetric {detail} ({touched} links)"
                )

    root_path = root / ROOT_FILE
    declared = (
        root_path.read_text(encoding="utf-8").strip()
        if root_path.is_file()
        else ""
    )
    if declared and is_full_ref(declared):
        root_ref: str | None = declared
    elif declared and is_bare_ref(declared) and int(declared) in mapping:
        root_ref = mapping[int(declared)]
    else:
        root_ref = None
    if root_ref is None or root_ref not in target_by_ref:
        root_ref = (
            min(target_by_ref, key=_ref_text_key) if target_by_ref else None
        )

    pending: list[tuple[Path, Path, str]] = []
    for target, document in docs.items():
        where = str(source_of[target].relative_to(root))
        ref = target.stem
        raw_fm = document.raw_fm
        changed = False

        if final_links[ref] != original_links[ref]:
            raw_fm = rewrite_links(raw_fm, final_links[ref])
            changed = True

        if target in converted:
            raw_fm = _remove_key(raw_fm, "contains")
            result.rewrites.append(
                f"{where}: contains -> {len(converted[target])} links "
                f"({link_type})"
            )
            changed = True

        retired = [
            key
            for key in ("band", "subpath", "layer", "stage", "order")
            if key in document.meta
        ]
        if ref == root_ref:
            retired.extend(
                key
                for key in ("band_layout", "band_order")
                if key in document.meta
            )
        if retired:
            for key in retired:
                raw_fm = _remove_key(raw_fm, key)
            result.rewrites.append(f"{where}: strip {', '.join(retired)}")
            changed = True

        if changed:
            pending.append(
                (source_of[target], target, document.with_raw_fm(raw_fm))
            )

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

    renamed = {old for old, new, _text in pending if old != new}
    for old, new, text in pending:
        if old != new:
            old.rename(new)
        atomic_write(new, text)
    for target, old in source_of.items():
        if old != target and old not in renamed:
            old.rename(target)
    if root_text is not None:
        atomic_write(root_path, root_text + "\n")
    return result
