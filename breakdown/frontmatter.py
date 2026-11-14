"""YAML front-matter parsing and surgical rewriting.

The body of a node is never parsed or re-serialised.  Every writer in this
package appends the body string verbatim, and ``rewrite_links`` touches only
the ``links:`` block of the front matter so key order and comments elsewhere
survive.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

import yaml


class FrontMatterError(ValueError):
    """Raised when a markdown file has no usable YAML front matter."""


class InvalidFrontMatter(FrontMatterError):
    """Front matter delimiters exist but the YAML itself is unusable."""


@dataclass
class Document:
    opening: str
    raw_fm: str
    closing: str
    body: str
    meta: dict[str, Any]
    repaired: bool = False
    error: str | None = None

    def render(self) -> str:
        """Byte-identical reconstruction."""
        return self.opening + self.raw_fm + self.closing + self.body

    def with_raw_fm(self, raw_fm: str) -> str:
        return self.opening + raw_fm + self.closing + self.body


_TOP_LEVEL_SCALAR = re.compile(r"^([A-Za-z_][\w-]*):[ \t]+(.+)$")
# Values starting with these characters are already valid YAML scalars or blocks.
_SAFE_LEADING = ('"', "'", "[", "{", "|", ">", "#")


def _quote_value(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\t", "\\t")
        .replace("\r", "\\r")
    )
    return f'"{escaped}"'


def repair_front_matter(raw_fm: str) -> tuple[str, bool]:
    """Quote top-level plain scalars containing ``": "``.

    Only top-level ``key: value`` lines are touched; indented lines, list items
    and the body are left alone.  Values already quoted or starting a YAML
    construct are skipped.
    """
    repaired: list[str] = []
    changed = False
    for line in raw_fm.splitlines(keepends=True):
        ending = ""
        content = line
        for candidate in ("\r\n", "\n", "\r"):
            if content.endswith(candidate):
                ending = candidate
                content = content[: -len(candidate)]
                break
        match = _TOP_LEVEL_SCALAR.match(content)
        if match:
            value = match.group(2).rstrip()
            if ": " in value and not value.startswith(_SAFE_LEADING):
                content = f"{match.group(1)}: {_quote_value(value)}"
                changed = True
        repaired.append(content + ending)
    return "".join(repaired), changed


def _load_mapping(raw_fm: str) -> dict[str, Any]:
    meta = yaml.safe_load(raw_fm)
    if meta is None:
        meta = {}
    if not isinstance(meta, dict):
        raise InvalidFrontMatter("front matter is not a mapping")
    return meta


def parse_document(text: str) -> Document:
    """Split a markdown file into front matter and an untouched body."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise FrontMatterError("missing opening '---'")
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            raw_fm = "".join(lines[1:i])
            body = "".join(lines[i + 1 :])
            try:
                meta = _load_mapping(raw_fm)
            except yaml.YAMLError as exc:
                error = f"invalid YAML front matter: {exc}"
                repaired_fm, changed = repair_front_matter(raw_fm)
                if not changed:
                    raise InvalidFrontMatter(error) from exc
                try:
                    meta = _load_mapping(repaired_fm)
                except yaml.YAMLError as retry:
                    raise InvalidFrontMatter(
                        f"{error} (conservative repair failed: {retry})"
                    ) from exc
                return Document(
                    lines[0], raw_fm, lines[i], body, meta, repaired=True, error=error
                )
            return Document(lines[0], raw_fm, lines[i], body, meta)
    raise FrontMatterError("missing closing '---'")


def normalize_body(body: str) -> str:
    """Trailing blank lines stripped, exactly one trailing newline."""
    lines = body.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines) + "\n"


def body_hash(body: str) -> str:
    digest = hashlib.sha256(normalize_body(body).encode("utf-8")).hexdigest()
    return f"sha256:{digest[:12]}"


def render_document(meta: dict[str, Any], body: str) -> str:
    """Render new front matter (canonical YAML) plus a verbatim body."""
    fm = yaml.safe_dump(
        meta,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    if not fm.endswith("\n"):
        fm += "\n"
    return "---\n" + fm + "---\n" + body


_LINKS_KEY = re.compile(r"^links\s*:")


def _format_link(link: dict[str, Any]) -> str:
    data: dict[str, Any] = {}
    for key, value in link.items():
        if value is None and key != "pinned":
            continue
        data[key] = str(value) if key == "pinned" else value
    dumped = yaml.safe_dump(
        data, default_flow_style=True, width=10**9, allow_unicode=True
    ).strip()
    return "  - " + dumped


_CONTAINS_KEY = re.compile(r"^contains\s*:")


def rewrite_contains(raw_fm: str, refs: list[str]) -> str:
    """Replace (or append) the ``contains:`` list, leaving every other line alone."""
    lines = raw_fm.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if _CONTAINS_KEY.match(line)), None
    )
    dumped = yaml.safe_dump(
        list(refs), default_flow_style=True, width=10**9, allow_unicode=True
    ).strip()
    block = [f"contains: {dumped}"]
    if start is None:
        lines.extend(block)
    else:
        end = start + 1
        while end < len(lines):
            line = lines[end]
            if line and not line[0].isspace() and not line.startswith("- "):
                break
            end += 1
        lines[start:end] = block
    rendered = "\n".join(lines)
    if raw_fm.endswith("\n") or not raw_fm:
        rendered += "\n"
    return rendered


def rewrite_links(raw_fm: str, links: list[dict[str, Any]]) -> str:
    """Replace the ``links:`` block, leaving every other line untouched."""
    lines = raw_fm.splitlines()
    start = next((i for i, line in enumerate(lines) if _LINKS_KEY.match(line)), None)
    block = ["links:"] + [_format_link(link) for link in links]
    if start is None:
        lines.extend(block)
    else:
        end = start + 1
        while end < len(lines):
            line = lines[end]
            if line and not line[0].isspace() and not line.startswith("- "):
                break
            end += 1
        lines[start:end] = block
    rendered = "\n".join(lines)
    if raw_fm.endswith("\n") or not raw_fm:
        rendered += "\n"
    return rendered
