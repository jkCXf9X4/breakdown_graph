"""Filesystem operations on the numeric, versioned node store."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .errors import BreakdownError
from .frontmatter import parse_document, render_document, rewrite_contains
from .loader import load, load_view, node_path, parse_ref, ref_of
from .model import DiffEntry, Node


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
