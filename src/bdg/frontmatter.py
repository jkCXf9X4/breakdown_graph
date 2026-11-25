"""YAML front-matter parsing and surgical rewriting.

The body of a node is never parsed or re-serialised except for stripping the
reserved ``[[REF, TYPE]]`` tokens, which must not affect freshness pins.
``rewrite_freshness`` touches only the ``freshness:`` block of the front
matter so key order and comments elsewhere survive byte for byte.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

import yaml

from .inline import token_spans


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


_TOKEN_LINE = re.compile(
    r"^[ \t]*(?:[-*+][ \t]+)?"
    r"(?:\([^)\n]+\)[ \t]*)?"
    r"\[\[[0-9]+-[0-9]+[ \t]*,[ \t]*[A-Za-z][A-Za-z0-9_-]*\]\]"
    r"[ \t]*$"
)


def strip_tokens(body: str) -> str:
    """The body with every reserved inline token removed.

    A line that is nothing but a token (or a list item holding one) is dropped
    whole, together with the reserved ``## Links`` heading and the blank run it
    leaves behind.  Tokens embedded in prose are removed in place.  Both forms
    are writer noise, so neither may invalidate a freshness pin.
    """
    lines = [
        line
        for line in body.splitlines()
        if not _TOKEN_LINE.match(line) and line.strip().lower() != "## links"
    ]
    collapsed: list[str] = []
    for line in lines:
        if not line.strip() and collapsed and not collapsed[-1].strip():
            continue
        collapsed.append(line)
    return strip_inline_spans("\n".join(collapsed))


def strip_inline_spans(body: str) -> str:
    """The body with every inline token occurrence removed in place."""
    spans = token_spans(body)
    if not spans:
        return body
    parts: list[str] = []
    cursor = 0
    for start, end in spans:
        parts.append(body[cursor:start])
        cursor = end
    parts.append(body[cursor:])
    return "".join(parts)


def normalize_body(body: str) -> str:
    """Trailing blank lines stripped, exactly one trailing newline."""
    lines = body.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines) + "\n"


def body_hash(body: str) -> str:
    """SHA-256 of the normalized body with inline tokens stripped first.

    Tokens must not invalidate freshness pins, so they are removed before the
    body is normalized and hashed.
    """
    digest = hashlib.sha256(
        normalize_body(strip_tokens(body)).encode("utf-8")
    ).hexdigest()
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


_FRESHNESS_KEY = re.compile(r"^freshness\s*:")
_REF_TEXT_KEY = re.compile(r"^(?P<ref>[1-9]\d*)-(?P<version>[1-9]\d*)$")


def _ref_sort_key(text: str) -> tuple[int, int, int, str]:
    match = _REF_TEXT_KEY.fullmatch(text)
    if not match:
        return (1, 0, 0, text)
    return (0, int(match.group("ref")), int(match.group("version")), "")


def _format_freshness(freshness: dict[str, dict[str, Any]]) -> list[str]:
    """The canonical ``freshness:`` block: block YAML, quoted ref keys."""
    lines = ["freshness:"]
    for ref in sorted(freshness, key=_ref_sort_key):
        entry = freshness[ref] or {}
        details: list[str] = []
        if "pinned" in entry and entry["pinned"] is not None:
            details.append(f"pinned: \"{entry['pinned']}\"")
        if "propagates" in entry and entry["propagates"]:
            details.append("propagates: true")
        if not details:
            lines.append(f"  '{ref}': {{}}")
            continue
        lines.append(f"  '{ref}':")
        lines.extend(f"    {detail}" for detail in details)
    return lines


def _finish(lines: list[str], raw_fm: str) -> str:
    rendered = "\n".join(lines)
    if raw_fm.endswith("\n") or not raw_fm:
        rendered += "\n"
    return rendered


def rewrite_freshness(raw_fm: str, freshness: dict[str, dict[str, Any]]) -> str:
    """Replace the ``freshness:`` block, leaving every other line untouched.

    An empty mapping removes the block entirely; a missing block is appended.
    Every other front-matter line is byte-stable, so comments and key order
    survive.
    """
    lines = raw_fm.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if _FRESHNESS_KEY.match(line)), None
    )
    if not freshness:
        if start is None:
            return raw_fm
        end = start + 1
        while end < len(lines):
            line = lines[end]
            if line and not line[0].isspace() and not line.startswith("- "):
                break
            end += 1
        del lines[start:end]
        return _finish(lines, raw_fm)
    block = _format_freshness(freshness)
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
    return _finish(lines, raw_fm)
