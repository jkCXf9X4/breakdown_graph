"""Shared fixtures for the bd_tree test suite."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bd_tree.frontmatter import body_hash, render_document  # noqa: E402


def _qualify(value: Any, version: int) -> Any:
    """Turn a bare id in test data into the full ref of ``version``.

    Tests write readable data like ``contains=["2"]``; the store only accepts
    full refs, so the fixture qualifies it to ``"2-1"`` unless a test asks for
    raw data (``raw_refs=True``) to exercise rejection.
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


def _qualify_link(item: Any, version: int) -> Any:
    if isinstance(item, dict):
        if "to" not in item:
            return item
        return {**item, "to": _qualify(item["to"], version)}
    return _qualify(item, version)


def write_node(
    directory: Path,
    node_id: int,
    *,
    version: int = 1,
    contains: list[str] | None = None,
    links: list[Any] | None = None,
    body: str = "body\n",
    meta: dict[str, Any] | None = None,
    raw_refs: bool = False,
    **fields: Any,
) -> Path:
    """Write one node.  Fields are arbitrary; only what you pass is written.

    Bare ids in ``contains``/``links`` are qualified to ``<id>-<version>``
    because data refs are always full refs; pass ``raw_refs=True`` to write the
    given text unchanged (for bare-ref validation tests).

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
    if contains is not None:
        data["contains"] = (
            list(contains)
            if raw_refs
            else [_qualify(item, 1) for item in contains]
        )
    if links is not None:
        data["links"] = (
            list(links)
            if raw_refs
            else [_qualify_link(item, 1) for item in links]
        )
    path = directory / f"{ref}.md"
    path.write_text(render_document(data, body), encoding="utf-8", newline="")
    return path


@pytest.fixture
def write():
    return write_node


@pytest.fixture
def pin():
    return body_hash
