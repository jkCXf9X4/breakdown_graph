"""Shared fixtures for the bd_tree test suite.

Fixture contract (the write unit consumes this — follow it):

- ``write_node(directory, node_id, **fields)`` writes one node file.  Arbitrary
  front-matter fields are written as given.  Bodies are plain strings holding
  link declarations directly as canonical ``(TITLE)[[REF, TYPE]]`` tokens.
- ``write_node(..., links=[...])`` is accepted for backwards compatibility and
  auto-converts a front-matter links list into *prefix-form* body tokens plus a
  ``freshness:`` front-matter map (``to``/``type`` become the token,
  ``propagates``/``pinned`` become freshness entries; other link keys are
  dropped).  The cached title is the target's live title when the target file
  already exists, else the target's default title ``Title of <ref>``; pass
  ``title=`` on the link to override.  Bare target ids are qualified to
  ``<id>-1`` unless ``raw_refs=True``.
- ``make_store(path)`` writes the default store: twelve nodes ``1-1``..``12-1``
  mirroring ``examples/`` (same topology, same titles), every link declared as a
  prefix token, empty freshness maps, so ``api.check`` is clean on it.  It ends
  with a finalize pass (``retitle_store``), so the default store is
  title-clean: no ``link-title-stale`` and no ``inline-title-missing`` warnings.
- ``retitle_store(directory)`` is the finalize pass: it re-reads every node's
  live ``title`` and rewrites the cached title of every token targeting it.  A
  test that writes a referenced node *after* its source and cares about a clean
  check can call it once at the end; the default store fixture already does.
  (Deliberately stale titles written through ``body=`` are left alone unless
  this helper is called.)
- ``add_token(store_path, ref, token_text)`` appends ``- <token_text>`` as a
  new list line under the trailing ``## Links`` section of ``nodes/<ref>.md``
  (creating the section, preceded by a blank line, when absent).
- ``set_freshness(store_path, ref, map)`` surgically replaces the whole
  top-level ``freshness:`` mapping of ``nodes/<ref>.md`` (an empty map removes
  it).  Keys are refs like ``"2-1"``; values carry ``pinned`` (str),
  ``propagates`` (bool), or both.
- The ``write`` fixture exposes ``write_node``; the ``pin`` fixture exposes
  ``body_hash``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bd_tree.frontmatter import (  # noqa: E402
    body_hash,
    parse_document,
    render_document,
    rewrite_freshness,
)
from bd_tree.inline import render_token, retitle_tokens  # noqa: E402


def _qualify(value: Any, version: int) -> Any:
    """Turn a bare id in test data into the full ref of ``version``.

    Tests write readable data like ``to="2"``; the store only accepts full
    refs, so the fixture qualifies it to ``"2-1"`` unless a test asks for raw
    data (``raw_refs=True``) to exercise rejection.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        return value
    if text.isdigit() and text and text[0] != "0":
        return f"{text}-{version}"
    return value


def _live_titles(directory: Path) -> dict[str, str]:
    """Every node file's live ``title``, keyed by ``<id>-<version>``."""
    titles: dict[str, str] = {}
    for path in sorted(Path(directory).glob("*.md")):
        try:
            document = parse_document(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        title = document.meta.get("title")
        if isinstance(title, str) and title:
            titles[path.stem] = title
    return titles


def _token_lines(
    links: list[Any], version: int, titles: dict[str, str]
) -> list[str]:
    """Render a links list as prefix-form token list lines."""
    lines: list[str] = []
    for item in links:
        if not isinstance(item, dict) or "to" not in item:
            continue
        target = str(_qualify(item["to"], version))
        title = item.get("title")
        if not title:
            title = titles.get(target, f"Title of {target}")
        token = render_token(item.get("type") or "link", target, title)
        lines.append(f"- {token}")
    return lines


def _freshness_of(links: list[Any], version: int) -> dict[str, dict[str, Any]]:
    """The freshness entries a links list carries, keyed by qualified ref."""
    entries: dict[str, dict[str, Any]] = {}
    for item in links:
        if not isinstance(item, dict) or "to" not in item:
            continue
        target = str(_qualify(item["to"], version))
        entry: dict[str, Any] = {}
        if "pinned" in item and item["pinned"] is not None:
            entry["pinned"] = item["pinned"]
        if "propagates" in item:
            entry["propagates"] = bool(item["propagates"])
        if entry:
            entries[target] = entry
    return entries


def _links_body(
    directory: Path,
    links: list[Any] | None,
    body: str,
    version: int,
    raw_refs: bool,
) -> tuple[str, dict[str, dict[str, Any]]]:
    """Body plus freshness for the given links list.

    With ``raw_refs=True`` the token target text is written unchanged (for
    bare-ref validation tests).  Otherwise the cached title is the target's
    live title when its file already exists, else its default title.
    """
    if links is None:
        return body, {}
    if raw_refs:
        lines = [
            f"- [[{item['to']}, {item.get('type') or 'link'}]]"
            if isinstance(item, dict) and "to" in item
            else f"- [[{item}, link]]"
            for item in links
        ]
    else:
        lines = _token_lines(links, version, _live_titles(directory))
    freshness = _freshness_of(links, version)
    if not lines:
        return body, freshness
    section = "\n".join(["", "## Links", ""] + lines)
    if body and not body.endswith("\n"):
        body += "\n"
    return body + section + "\n", freshness


def write_node(
    directory: Path,
    node_id: int,
    *,
    version: int = 1,
    links: list[Any] | None = None,
    body: str = "body\n",
    meta: dict[str, Any] | None = None,
    raw_refs: bool = False,
    freshness: dict[str, dict[str, Any]] | None = None,
    **fields: Any,
) -> Path:
    """Write one node.  Fields are arbitrary; only what you pass is written.

    Link declarations belong in the body as prefix-form
    ``(TITLE)[[REF, TYPE]]`` tokens; pass ``links=[...]`` to have the fixture
    auto-convert a front-matter-style list into tokens plus freshness entries
    (see the module docstring).

    Convenience: when ``layer`` is given, set ``name`` to ``<ref>`` so path
    assertions stay readable.
    """
    directory.mkdir(parents=True, exist_ok=True)
    ref = f"{node_id}-{version}"
    data: dict[str, Any] = {
        "id": node_id,
        "title": fields.pop("title", f"Title of {ref}"),
        "summary": fields.pop("summary", "summary"),
    }
    data.update(fields)
    if isinstance(data.get("layer"), str) or isinstance(data.get("band"), str):
        data.setdefault("name", ref)
    if meta:
        data.update(meta)
    body_text, auto_freshness = _links_body(
        directory, links, body, 1, raw_refs
    )
    entries = dict(auto_freshness)
    if freshness:
        entries.update(freshness)
    if entries:
        data["freshness"] = entries
    path = directory / f"{ref}.md"
    path.write_text(render_document(data, body_text), encoding="utf-8", newline="")
    return path


@pytest.fixture
def write():
    return write_node


@pytest.fixture
def pin():
    return body_hash


# ---------------------------------------------------------------------------
# The default store: twelve nodes mirroring examples/, links as body tokens.

_DEFAULT_TITLES: dict[int, str] = {
    1: "Verify the undirected graph",
    2: "Structural claims",
    3: "Verification claims",
    4: "Two parents, one node",
    5: "The component view",
    6: "Direction is a label",
    7: "Derived in-edges",
    8: "Verification fan-in",
    9: "Operate the graph",
    10: "Require sorted links",
    11: "Verification fan-in 2",
    12: "Verification core",
}

_DEFAULT_LINKS: dict[int, list[tuple[str, int]]] = {
    1: [("breaks_down", 2), ("breaks_down", 3)],
    2: [("breaks_down", 4), ("breaks_down", 5), ("breaks_down", 6)],
    3: [("supports", 4), ("supports", 7)],
    4: [("supports", 8), ("supports", 12)],
    5: [("supports", 8)],
    6: [("evidences", 8)],
    7: [("verifies", 8), ("verifies", 12)],
    8: [("operates", 9), ("requires", 10), ("breaks_down", 11)],
    9: [],
    10: [],
    11: [],
    12: [("breaks_down", 8), ("breaks_down", 11)],
}


def _token_text(link_type: str, target: int) -> str:
    return render_token(link_type, f"{target}-1", _DEFAULT_TITLES[target])


def _default_body(node_id: int) -> str:
    links = _DEFAULT_LINKS[node_id]
    if not links:
        return f"{_DEFAULT_TITLES[node_id]} stands on its own.\n"
    parts = [f"{_DEFAULT_TITLES[node_id]} declares:"]
    for link_type, target in links:
        parts.append(f"- {_token_text(link_type, target)}")
    return "\n".join(parts) + "\n"


def retitle_store(directory: Path) -> int:
    """Finalize pass: retitle every token from the target's live title.

    Re-reads every node in ``directory`` (``<id>-<version>.md``), builds the
    ref -> title map, and rewrites cached token titles in place.  Returns the
    number of tokens changed.  Call this after writing nodes out of order when
    the default store must be title-clean; ``make_store`` already does.
    """
    directory = Path(directory)
    titles = _live_titles(directory)
    if not titles:
        return 0
    changed = 0
    for path in sorted(directory.glob("*.md")):
        document = parse_document(path.read_text(encoding="utf-8"))
        new_body, count = retitle_tokens(document.body, titles)
        if count:
            path.write_text(
                document.opening + document.raw_fm + document.closing + new_body,
                encoding="utf-8",
                newline="",
            )
            changed += count
    return changed


def make_store(path: Path) -> Path:
    """Write the default twelve-node store at ``path/nodes/`` and return it.

    The nodes are ``(ref, title, body, freshness)`` mirroring ``examples/``:
    same topology, same titles, every link declared as a prefix token, empty
    freshness maps.  A finalize pass (``retitle_store``) makes it title-clean,
    so ``api.check`` is clean on it (0 errors, 0 warnings).
    """
    nodes = Path(path) / "nodes"
    nodes.mkdir(parents=True, exist_ok=True)
    for node_id in range(1, 13):
        data: dict[str, Any] = {"id": node_id, "title": _DEFAULT_TITLES[node_id]}
        if node_id in (1, 2, 3):
            data["summary"] = "summary"
        (nodes / f"{node_id}-1.md").write_text(
            render_document(data, _default_body(node_id)),
            encoding="utf-8",
            newline="",
        )
    retitle_store(nodes)
    return nodes


def add_token(store_path: Path, ref: str, token_text: str) -> Path:
    """Append ``- <token_text>`` under the trailing ``## Links`` section.

    Creates the section (preceded by a blank line) when the node has none.
    """
    node_file = Path(store_path) / f"{ref}.md"
    text = node_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    index = next(
        (i for i, line in enumerate(lines) if line.rstrip() == "## Links"), None
    )
    row = f"- {token_text}"
    if index is None:
        if text and not text.endswith("\n"):
            text += "\n"
        text = f"{text}\n## Links\n{row}\n"
    else:
        end = index + 1
        while end < len(lines) and not lines[end].startswith("# "):
            end += 1
        lines.insert(end, row)
        text = "\n".join(lines) + "\n"
    node_file.write_text(text, encoding="utf-8", newline="")
    return node_file


def set_freshness(
    store_path: Path, ref: str, map_: dict[str, dict[str, Any]]
) -> Path:
    """Surgically replace the whole ``freshness:`` mapping of one node.

    An empty map removes the block.  Keys are refs like ``"2-1"``; values
    carry ``pinned`` (str), ``propagates`` (bool), or both.
    """
    node_file = Path(store_path) / f"{ref}.md"
    document = parse_document(node_file.read_text(encoding="utf-8"))
    rewritten = rewrite_freshness(document.raw_fm, map_)
    node_file.write_text(
        document.with_raw_fm(rewritten), encoding="utf-8", newline=""
    )
    return node_file
