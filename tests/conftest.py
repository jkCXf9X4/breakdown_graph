"""Shared fixtures for the breakdown test suite."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from breakdown.frontmatter import body_hash, render_document  # noqa: E402


def write_node(
    directory: Path,
    node_id: int,
    *,
    version: int = 0,
    contains: list[str] | None = None,
    links: list[dict[str, Any]] | None = None,
    body: str = "body\n",
    meta: dict[str, Any] | None = None,
    **fields: Any,
) -> Path:
    """Write one node.  Fields are arbitrary; only what you pass is written.

    Convenience: when ``layer`` is given and ``home`` is not, derive
    ``<layer>/<ref>.md`` so path assertions stay readable.
    """
    directory.mkdir(parents=True, exist_ok=True)
    ref = str(node_id) if version == 0 else f"{node_id}-{version}"
    data: dict[str, Any] = {
        "id": node_id,
        "title": fields.pop("title", f"Title of {ref}"),
        "summary": fields.pop("summary", "summary"),
    }
    data.update(fields)
    if "home" not in data and isinstance(data.get("layer"), str):
        data["home"] = f"{data['layer']}/{ref}.md"
    if meta:
        data.update(meta)
    if contains is not None:
        data["contains"] = contains
    if links is not None:
        data["links"] = links
    path = directory / f"{ref}.md"
    path.write_text(render_document(data, body), encoding="utf-8", newline="")
    return path


@pytest.fixture
def write():
    return write_node


@pytest.fixture
def pin():
    return body_hash
