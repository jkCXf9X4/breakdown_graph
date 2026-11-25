"""Filesystem operations on the version-only numeric node store.

Links are declared as reserved tokens in node bodies, not front matter.  The
canonical token is ``[[REF, TYPE]]``; an optional cached title is a PREFIX,
``(TITLE)[[REF, TYPE]]``.  Cached titles are tool-written, never
hand-maintained: writers fill the target's live title and :func:`retitle`
regenerates them.

Operating rule for structural edits: a structural edit changes only the
source file, preserves unrelated front matter, and touches the body only
inside ``## Links`` sections — appending or removing token lines — except
:func:`replace`, which additionally rewrites token refs in place.  Per-edge
pins and participation live in the top-level ``freshness`` front-matter
map, keyed by target ref.
"""

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
    rewrite_freshness,
)
from .fsutil import atomic_copy, atomic_write, publish_new, store_lock
from .graph import ring_distances
from .inline import (
    append_token,
    parse_inline_links,
    remove_token,
    repoint_token,
    retitle_tokens,
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


def _raw_links(document) -> list[Any]:
    """Validate the legacy front-matter ``links`` list shape for migration."""
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


def _fm_freshness(meta: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The node's ``freshness`` front-matter map, normalized to plain dicts."""
    raw = meta.get("freshness")
    if not isinstance(raw, dict):
        return {}
    return {
        str(key): dict(value) if isinstance(value, dict) else {}
        for key, value in raw.items()
    }


def _merge_freshness_entry(
    freshness: dict[str, dict[str, Any]], target_ref: str, values: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """Return the map with ``values`` merged into the entry keyed ``target_ref``."""
    merged = {key: dict(value) for key, value in freshness.items()}
    merged[target_ref] = {**merged.get(target_ref, {}), **values}
    return merged


def _meta_title(meta: dict[str, Any], ref: str) -> str:
    """A not-yet-published node's live title: its ``title`` field, else the ref."""
    value = meta.get("title")
    return str(value) if value not in (None, "") else ref


_TOKEN_TYPE = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")


def _check_link_type(link_type: str) -> str:
    """A link type must be writable as a body token type."""
    if not isinstance(link_type, str) or not link_type.strip():
        raise BreakdownError("link type must be a non-empty string")
    if _TOKEN_TYPE.fullmatch(link_type) is None:
        raise BreakdownError(
            f"link type {link_type!r} cannot be written as a body token "
            "(expected [A-Za-z][A-Za-z0-9_-]*)"
        )
    return link_type


_ROOT_BODY = "# Root\n\nState the intent of this graph here.\n"
_GITIGNORE = "# generated work area (bdg work)\nbdg_work/\n"
_GITIGNORE_ENTRY = "bdg_work/"


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


def init_store(root: str | Path = ".") -> Path:
    """Create the canonical project with a hidden store and return its root.

    The root node carries only identity metadata and no links; placement keys
    are retired, so nothing declares a band or stage.
    """
    project = Path(root).resolve()
    hidden = project / STORE_DIR / "nodes"
    legacy = project / "nodes"
    for label, nodes in (("bdg_graph/nodes", hidden), ("nodes", legacy)):
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
        # that leave the neighbourhood pointing at the original nodes.  Token
        # refs are rewritten in place; every other byte is preserved.
        for old_ref, new_ref in mapping.items():
            target = node_path(root, *parse_ref(new_ref))
            document = parse_document(target.read_text(encoding="utf-8"))
            body = document.body
            changed = False
            for old, new in mapping.items():
                body, count = repoint_token(body, old, new)
                if count:
                    changed = True
            if changed:
                atomic_write(
                    target,
                    document.opening + document.raw_fm + document.closing + body,
                )

    return [(old_ref, mapping[old_ref]) for old_ref in order]


@_serialized
def replace(
    root: str | Path, old: str | int, new: str | int
) -> tuple[str, str, str]:
    """Repoint every inbound link from ``old`` to ``new``.

    Token refs are rewritten in place in every node body, and each rewritten
    token's cached title is set to the new node's live title.  Each node's
    ``freshness`` map is repointed from ``old`` to ``new`` keeping its values.
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

    new_title = store.nodes[new_ref].title
    repointed: list[str] = []
    for node in store.nodes.values():
        document = parse_document(node.path.read_text(encoding="utf-8"))
        body, count = repoint_token(
            document.body, old_ref, new_ref, new_title=new_title
        )
        raw_fm = document.raw_fm
        freshness = _fm_freshness(document.meta)
        if old_ref in freshness:
            merged = {
                (new_ref if key == old_ref else key): value
                for key, value in freshness.items()
            }
            raw_fm = rewrite_freshness(raw_fm, merged)
        if count or raw_fm != document.raw_fm:
            atomic_write(
                node.path,
                document.opening + raw_fm + document.closing + body,
            )
        if count:
            repointed.append(node.ref)
    was_root = store.root_ref == old_ref
    if was_root:
        set_root(root, new_ref)
    if not repointed and not was_root:
        raise BreakdownError(
            f"{old_ref} has no inbound links; wire {new_ref} with bdg link"
        )
    return old_ref, "ROOT" if was_root else "links", new_ref


@dataclass
class RetitleResult:
    """What :func:`retitle` did, or would do under ``--dry-run``."""

    changed: int = 0
    nodes: list[str] = field(default_factory=list)
    dry_run: bool = False


@_serialized
def retitle(
    root: str | Path,
    *,
    view: str | int | None = None,
    dry_run: bool = False,
) -> RetitleResult:
    """Rewrite every cached token title to its target's live title.

    The scope is the whole store by default, or the undirected view rooted at
    ``view`` when given.  Inside each in-scope node every token is retitled
    from the target's live title; a token whose target cannot be resolved is
    left untouched.  Only the title text inside tokens changes.  Nothing is
    written when no title differs; ``dry_run`` never writes and only reports.
    """
    root = resolve_store_root(root)
    store = load(root)
    if view is None:
        refs = list(store.nodes)
    else:
        canonical = resolve_ref(store, view)
        resolved = load_view(store, canonical)
        refs = list(resolved.nodes)
    titles = {ref: node.title for ref, node in store.nodes.items()}
    result = RetitleResult(dry_run=dry_run)
    order = sorted(
        refs, key=lambda item: (store.nodes[item].id, store.nodes[item].version)
    )
    for ref in order:
        node = store.nodes[ref]
        document = parse_document(node.path.read_text(encoding="utf-8"))
        body, count = retitle_tokens(document.body, titles)
        if not count:
            continue
        result.changed += count
        result.nodes.append(ref)
        if not dry_run:
            atomic_write(
                node.path,
                document.opening + document.raw_fm + document.closing + body,
            )
    return result


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
    link_type: str = "breaks_down",
) -> Path:
    """Create the next global id at version 1 and wire it to ``parent``.

    No authored placement is written: bands, stages and orders are retired.
    A typed edge token is appended to the parent's ``## Links`` body section
    when ``parent`` is given; without a parent the node is a new component
    of its own.  The new node file itself carries no links — a ``--body``
    containing tokens parses like any other.

    The whole id-pick/parent-rewrite/publish sequence holds the store lock, so
    concurrent writers get distinct ids and neither loses a sibling.  Both
    files are published atomically, so readers never see a partial document.
    """
    root = resolve_store_root(root)
    fields = dict(fields or {})
    if "id" in fields:
        raise BreakdownError("'id' is assigned by bdg new and cannot be given")
    store = load(root)

    if parent is None:
        parent_node: Node | None = None
    else:
        parent_node = _existing(store, resolve_ref(store, parent), "parent")
        _check_link_type(link_type)

    node_id = max((node.id for node in store.nodes.values()), default=0) + 1
    meta: dict[str, Any] = {"id": node_id}
    meta.update(NEW_NODE_DEFAULTS)
    meta.update(fields)

    target = node_path(root, node_id, 1)
    if target.exists():
        raise BreakdownError(f"node {node_id}-1 already exists at {target}")

    new_ref = ref_of(node_id, 1)
    if parent_node is not None:
        document = parse_document(parent_node.path.read_text(encoding="utf-8"))
        parent_body = append_token(
            document.body, link_type, new_ref, _meta_title(meta, new_ref)
        )
        if parent_body != document.body:
            atomic_write(
                parent_node.path,
                document.opening + document.raw_fm + document.closing + parent_body,
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
    pinned: str | None = None,
) -> Path:
    """Append a typed edge token to the source node's ``## Links`` section.

    The token is written in the FROM node body; the title is the target's
    live title at link time.  Direction is only a label: back-edges,
    reciprocal edges and cycles are legal, and a ref may not link to itself.
    When ``propagates`` and/or ``pinned`` are given they are recorded in the
    source node's ``freshness`` front-matter map, keyed by the target ref;
    a propagating edge without an explicit pin is pinned to the target's
    current body hash now.
    """
    root = Path(root).resolve()
    _check_link_type(link_type)
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
    for token in parse_inline_links(document.body):
        if token.to == target_ref and token.type == link_type:
            raise BreakdownError(
                f"link {source_ref} -> {target_ref} ({link_type}) already "
                "exists; use bdg unlink first"
            )

    body = append_token(document.body, link_type, target_ref, target_node.title)
    raw_fm = document.raw_fm
    if propagates or pinned is not None:
        values: dict[str, Any] = {}
        if propagates:
            values["propagates"] = True
        if propagates or pinned is not None:
            values["pinned"] = (
                str(pinned) if pinned is not None else target_node.body_hash
            )
        merged = _merge_freshness_entry(_fm_freshness(document.meta), target_ref, values)
        if merged != _fm_freshness(document.meta):
            raw_fm = rewrite_freshness(raw_fm, merged)
    atomic_write(
        source_node.path,
        document.opening + raw_fm + document.closing + body,
    )
    return source_node.path


@_serialized
def unlink(
    root: str | Path,
    source: str | int,
    target: str | int,
    *,
    link_type: str | None = None,
) -> Path:
    """Remove every matching edge token from the source node's body.

    ``link_type`` narrows the match.  The source node's ``freshness`` entry
    keyed by the target ref is deleted only when no token targeting that ref
    remains; all other body bytes are preserved.
    """
    root = Path(root).resolve()
    store = load(root)
    source_ref = resolve_ref(store, source)
    target_ref = resolve_ref(store, target)
    source_node = _existing(store, source_ref, "source")
    _existing(store, target_ref, "target")

    document = parse_document(source_node.path.read_text(encoding="utf-8"))
    matching = [
        token
        for token in parse_inline_links(document.body)
        if token.to == target_ref
        and (link_type is None or token.type == link_type)
    ]
    if not matching:
        suffix = f" ({link_type})" if link_type is not None else ""
        raise BreakdownError(f"no link {source_ref} -> {target_ref}{suffix} to remove")

    body = document.body
    removed = 0
    for etype in dict.fromkeys(token.type for token in matching):
        body, count = remove_token(body, etype, target_ref)
        removed += count
    if removed == 0:
        raise BreakdownError(
            f"no link {source_ref} -> {target_ref} could be removed"
        )

    raw_fm = document.raw_fm
    if target_ref not in {token.to for token in parse_inline_links(body)}:
        freshness = _fm_freshness(document.meta)
        if target_ref in freshness:
            merged = {key: value for key, value in freshness.items() if key != target_ref}
            raw_fm = rewrite_freshness(raw_fm, merged)
    atomic_write(
        source_node.path,
        document.opening + raw_fm + document.closing + body,
    )
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

# Two comma-separated components inside brackets, either order.
_COMPONENT_TOKEN = re.compile(
    r"\[\[[ ]*(?P<first>[^\[\],\n]*?)[ ]*,[ ]*(?P<second>[^\[\],\n]*?)[ ]*\]\]"
)
# The retired suffix form: ``[[TYPE, REF]](TITLE)`` or ``[[REF, TYPE]](TITLE)``.
_LEGACY_TITLE_TOKEN = re.compile(
    _COMPONENT_TOKEN.pattern + r"(?P<title>\([^)\n]+\))"
)


def _component_pair(first: str, second: str) -> tuple[str, str] | None:
    """``(ref, type)`` when the two components are a ref/type pair, either order."""
    first, second = first.strip(), second.strip()
    if is_full_ref(first) and _TOKEN_TYPE.fullmatch(second):
        return first, second
    if _TOKEN_TYPE.fullmatch(first) and is_full_ref(second):
        return second, first
    return None


def _prefix_legacy_titles(text: str) -> tuple[str, int]:
    """Rewrite ``[[TYPE, REF]](TITLE)`` or ``[[REF, TYPE]](TITLE)`` to prefix form."""
    changed = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        pair = _component_pair(match.group("first"), match.group("second"))
        if pair is None:
            return match.group(0)
        ref, type_ = pair
        changed += 1
        return f"{match.group('title')}[[{ref}, {type_}]]"

    return _LEGACY_TITLE_TOKEN.sub(replace, text), changed


def _normalize_token_order(text: str) -> tuple[str, int]:
    """Rewrite every ``[[TYPE, REF]]`` to the canonical ``[[REF, TYPE]]``."""
    changed = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        pair = _component_pair(match.group("first"), match.group("second"))
        if pair is None:
            return match.group(0)
        ref, type_ = pair
        canonical = f"[[{ref}, {type_}]]"
        if canonical != match.group(0):
            changed += 1
        return canonical

    return _COMPONENT_TOKEN.sub(replace, text), changed


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
) -> MigrationResult:
    """One-time, idempotent, in-place migration of a legacy store.

    Classic bare filenames are versioned first.  Front-matter ``links`` and
    ``contains`` lists move into node bodies as a trailing ``## Links``
    section of ``- (TITLE)[[REF, TYPE]]`` token lines, sorted by target ref;
    the token title is the target's live title at migration time.  Every
    token, in either component order, is normalized to ref-first; retired
    suffix tokens ``[[TYPE, REF]](TITLE)`` and ``[[REF, TYPE]](TITLE)`` are
    rewritten to the prefix form, and every token without a title is filled
    from its target (the ref when the target is dangling).  Per-link
    ``pinned``/``propagates`` keys are stripped and recorded in the node's
    top-level ``freshness`` front-matter map.  Retired placement keys
    (``band``, ``subpath``, ``layer``, ``stage``, ``order``) are stripped
    from every node, and ``band_layout`` / ``band_order`` from the ROOT
    node, while body bytes outside the appended section, titles, and
    unrelated front matter are preserved.

    Running the same migration twice makes no further changes; token-only
    stores are left untouched and ``--dry-run`` writes nothing.
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

    def target_title(ref: str) -> str:
        target = target_by_ref.get(ref)
        if target is None:
            return ref
        value = docs[target].meta.get("title")
        return str(value) if value not in (None, "") else ref

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

    # One plan per node: the FM entries to convert to tokens, plus the
    # merged ``freshness`` map.  Symmetric/inverse keys die here: the token
    # carries only the plain type and ref.
    plans: dict[Path, tuple[list[tuple[str, str]], dict[str, dict[str, Any]]]] = {}
    for target, document in docs.items():
        where = str(source_of[target].relative_to(root))
        entries: list[tuple[str, str]] = []
        freshness = _fm_freshness(document.meta)
        original_freshness = {key: dict(value) for key, value in freshness.items()}
        if "links" in document.meta:
            for item in _raw_links(document):
                if isinstance(item, dict):
                    to = item.get("to")
                    if to is None:
                        raise BreakdownError(
                            f"cannot migrate {where}: link without 'to'"
                        )
                    _changed, value = _map_data_ref(to, mapping, where, ambiguous)
                    target_ref = str(value).strip()
                    etype = item.get("type")
                    if not isinstance(etype, str) or not etype.strip():
                        etype = target_type(target_ref) or link_type
                    entries.append((etype.strip(), target_ref))
                    values: dict[str, Any] = {}
                    if item.get("propagates"):
                        values["propagates"] = True
                    if item.get("pinned") is not None:
                        values["pinned"] = str(item["pinned"])
                    if values:
                        freshness = _merge_freshness_entry(
                            freshness, target_ref, values
                        )
                else:
                    _changed, value = _map_data_ref(item, mapping, where, ambiguous)
                    target_ref = str(value).strip()
                    entries.append(
                        (target_type(target_ref) or link_type, target_ref)
                    )
        if target in converted:
            entries.extend(
                (link_type, child_ref) for child_ref in converted[target]
            )
        entries.sort(key=lambda pair: _ref_text_key(pair[1]))
        plans[target] = (entries, freshness)

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
        entries, freshness = plans[target]
        raw_fm = document.raw_fm
        changed = False

        if "links" in document.meta:
            raw_fm = _remove_key(raw_fm, "links")
            changed = True
            fm_count = len(entries) - (
                len(converted[target]) if target in converted else 0
            )
            result.rewrites.append(f"{where}: links -> {fm_count} tokens")

        if target in converted:
            raw_fm = _remove_key(raw_fm, "contains")
            result.rewrites.append(
                f"{where}: contains -> {len(converted[target])} links "
                f"({link_type})"
            )
            changed = True

        body, legacy_count = _prefix_legacy_titles(document.body)
        if legacy_count:
            result.rewrites.append(
                f"{where}: {legacy_count} suffix tokens -> prefix"
            )
        body, order_count = _normalize_token_order(body)
        if order_count:
            result.rewrites.append(
                f"{where}: {order_count} tokens -> ref-first order"
            )
        for etype, target_ref in entries:
            body = append_token(body, etype, target_ref, target_title(target_ref))
        token_refs = dict.fromkeys(link.to for link in parse_inline_links(body))
        retitled = 0
        if token_refs:
            body, retitled = retitle_tokens(
                body, {target_ref: target_title(target_ref) for target_ref in token_refs}
            )
        if retitled:
            result.rewrites.append(f"{where}: retitled {retitled} tokens")
        if body != document.body:
            changed = True

        if freshness != _fm_freshness(document.meta):
            raw_fm = rewrite_freshness(raw_fm, freshness)
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
                (
                    source_of[target],
                    target,
                    document.opening + raw_fm + document.closing + body,
                )
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
