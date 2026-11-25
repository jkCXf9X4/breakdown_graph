"""Scanner for reserved inline link tokens in node Markdown bodies.

Link declarations live in node bodies as reserved tokens, not in front
matter.  The token grammar is::

    (TITLE)[[REF,TYPE]]  or  [[REF,TYPE]]

The cached title is a *prefix*: zero or more spaces may sit between ``)`` and
``[[``, the title is non-empty, and it excludes ``)`` and newline.  The title is
tool-generated cache, not authored content; an author writes only the bare
token and tooling fills or refreshes the title.

``REF`` comes first and is a full ref only, ``[0-9]+-[0-9]+``; ``TYPE`` is
``[A-Za-z][A-Za-z0-9_-]*``.  Emission is canonical with no space around the
comma; the legacy spaced form ``[[REF, TYPE]]`` (at most one optional ASCII
space on each side of the comma) is still accepted on input, and no space may
sit after ``[[`` or before ``]]``.

The legacy suffix form ``[[TYPE, REF]](TITLE)`` (and its ref-first variant) is
*not* a token form: ``(TITLE)`` stays prose and a type-first bracket is an
anomaly (``bdg migrate`` normalizes older stores).

Ignored (neither links nor errors): fenced code blocks (backticks and tildes,
fence of three or more characters, with or without a language), inline code
spans (single-line backtick pairs), and the ``\\[[`` escape.  Indented code
blocks and HTML comments are NOT handled in this pass.

An unterminated token (no closing ``]]`` on the same token) is an anomaly with
reason ``unterminated``; any other ``[[]]``-shaped fragment that fails the
grammar is an anomaly with a short reason.  Code spans, fences and escapes
never produce anomalies.

The writer helpers (``append_token``, ``remove_token``, ``repoint_token``,
``retitle_tokens``) are the write unit's interface for maintaining tokens and
the trailing ``## Links`` section.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

_TYPE = r"[A-Za-z][A-Za-z0-9_-]*"
_REF = r"[0-9]+-[0-9]+"

# The full fragment between the brackets: `REF ?,( ?)TYPE`.
_FRAGMENT = re.compile(rf"(?P<ref>{_REF}) ?,( ?)(?P<type>{_TYPE})\Z")
# A token list line maintained under `## Links`: title is an optional prefix.
_LIST_TOKEN = re.compile(
    rf"^[-*+][ \t]+(?:\([^)\n]*\)[ \t]*)?"
    rf"\[\[(?P<ref>{_REF}) ?,( ?)(?P<type>{_TYPE})\]\]"
    r"[ \t]*$"
)
_OPEN_BRACKETS = re.compile(r"\[\[")
_BACKTICK_RUN = re.compile(r"`+")
_FENCE_OPEN = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$", re.DOTALL)
_HEADING_12 = re.compile(r"^ {0,3}#{1,2}(\s|$)")
# A cached title prefix ending exactly where `[[` begins: `(TITLE)` + spaces.
_PREFIX = re.compile(r"\((?P<title>[^)\n]*)\)[ ]*\Z")


@dataclass(frozen=True)
class InlineLink:
    """One scanned token.  ``line``/``col`` are 1-based, body-relative."""

    line: int
    col: int
    type: str
    to: str
    title: str | None


@dataclass(frozen=True)
class InlineAnomaly:
    """One scanned ``[[]]``-shaped fragment that failed the grammar."""

    line: int
    col: int
    reason: str


@dataclass(frozen=True)
class _Match:
    line: int
    col: int
    type: str
    ref: str
    title: str | None
    start: int  # absolute body offset of the token start (title prefix included)
    end: int  # absolute body offset past the last consumed character
    raw: str  # the literal source substring of the token


def _code_regions(line: str) -> list[tuple[int, int]]:
    """Single-line backtick pairs; same-length runs close an open span."""
    regions: list[tuple[int, int]] = []
    runs = [(m.start(), m.end(), m.end() - m.start()) for m in _BACKTICK_RUN.finditer(line)]
    open_start: int | None = None
    open_length = 0
    for start, end, length in runs:
        if open_start is None:
            open_start, open_length = start, length
        elif length == open_length:
            regions.append((open_start, end))
            open_start = None
    return regions


def _opening_fence(line: str) -> tuple[str, int] | None:
    match = _FENCE_OPEN.match(line)
    if match is None:
        return None
    char = match.group(2)[0]
    if char == "`" and "`" in match.group(3):
        # A backtick fence's info string cannot contain backticks.
        return None
    return char, len(match.group(2))


def _closing_fence(line: str, char: str, length: int) -> bool:
    return re.match(rf"^( {{0,3}}){re.escape(char)}{{{length},}}[ \t]*$", line) is not None


def _escaped_at(line: str, index: int) -> bool:
    """Odd number of backslashes directly before ``index`` escapes ``[[``."""
    count = 0
    cursor = index - 1
    while cursor >= 0 and line[cursor] == "\\":
        count += 1
        cursor -= 1
    return count % 2 == 1


def _prefix_title(line: str, index: int) -> tuple[str | None, int]:
    """The cached title ending right before ``index`` and its token start.

    Returns ``(None, index)`` when there is no ``(TITLE)`` prefix.  The title
    itself may be empty here; the caller reports that as ``empty title``.
    """
    match = _PREFIX.search(line[:index])
    if match is None:
        return None, index
    return match.group("title"), match.start()


def _fragment_reason(fragment: str) -> str:
    """A short reason for a fragment that failed `REF ?,( ?)TYPE`."""
    if fragment == "":
        return "empty token"
    if "," not in fragment:
        return "missing ','"
    ref_part, _, type_part = fragment.partition(",")
    ref_text = ref_part.strip()
    type_text = type_part.strip()
    if not re.fullmatch(rf"{_REF} ?", ref_part):
        if re.fullmatch(_TYPE, ref_text) and re.fullmatch(_REF, type_text):
            return "reversed components"
        if re.fullmatch(r"[0-9]+", ref_text):
            return "bare ref"
        if re.fullmatch(_REF, ref_text):
            return "bad spacing"
        return "invalid ref"
    if not re.fullmatch(_TYPE, type_text):
        return "invalid type"
    return "bad spacing"


def _scan_body(body: str) -> tuple[list[_Match], list[InlineAnomaly]]:
    """One pass over the body, tracking fences, code spans and escapes."""
    matches: list[_Match] = []
    anomalies: list[InlineAnomaly] = []
    fence_char: str | None = None
    fence_length = 0
    offset = 0  # absolute body offset of the current line start
    line_number = 0
    for line in body.splitlines(keepends=True):
        line_number += 1
        if fence_char is not None:
            if _closing_fence(line, fence_char, fence_length):
                fence_char = None
            offset += len(line)
            continue
        opened = _opening_fence(line)
        if opened is not None:
            fence_char, fence_length = opened
            offset += len(line)
            continue
        regions = _code_regions(line)
        cursor = 0
        while cursor < len(line):
            bracket = _OPEN_BRACKETS.search(line, cursor)
            if bracket is None:
                break
            index = bracket.start()
            cursor = index + 2
            if _escaped_at(line, index):
                cursor = index + 3  # the escape consumes ``\[[``
                continue
            if any(start <= index < end for start, end in regions):
                continue
            title, start = _prefix_title(line, index)
            close = line.find("]]", cursor)
            while close != -1 and any(start <= close < end for start, end in regions):
                close = line.find("]]", close + 2)
            if close == -1:
                anomalies.append(InlineAnomaly(line_number, start + 1, "unterminated"))
                continue
            fragment = line[cursor:close]
            parsed = _FRAGMENT.fullmatch(fragment)
            if parsed is None:
                anomalies.append(
                    InlineAnomaly(line_number, start + 1, _fragment_reason(fragment))
                )
                cursor = close + 2
                continue
            if title == "":
                anomalies.append(InlineAnomaly(line_number, start + 1, "empty title"))
                cursor = close + 2
                continue
            end = close + 2
            raw = line[start:end].rstrip("\r\n")
            matches.append(
                _Match(
                    line=line_number,
                    col=start + 1,
                    type=parsed.group("type"),
                    ref=parsed.group("ref"),
                    title=title,
                    start=offset + start,
                    end=offset + end,
                    raw=raw,
                )
            )
            cursor = end
        offset += len(line)
    return matches, anomalies


def scan_inline_links(body: str) -> tuple[list[InlineLink], list[InlineAnomaly]]:
    """Scan a node body.  ``line``/``col`` are 1-based, body-relative."""
    matches, anomalies = _scan_body(body)
    links = [
        InlineLink(
            line=match.line, col=match.col, type=match.type, to=match.ref,
            title=match.title,
        )
        for match in matches
    ]
    return links, anomalies


def parse_inline_links(body: str) -> list[InlineLink]:
    """Convenience: the links only."""
    return scan_inline_links(body)[0]


def raw_inline_tokens(body: str) -> list[str]:
    """The literal token strings, aligned 1:1 with :func:`parse_inline_links`."""
    return [match.raw for match in _scan_body(body)[0]]


def token_spans(body: str) -> list[tuple[int, int]]:
    """Absolute ``(start, end)`` body ranges of every token, titles included."""
    return [(match.start, match.end) for match in _scan_body(body)[0]]


def render_token(type: str, ref: str, title: str | None) -> str:
    """The canonical token text: ``(TITLE)[[REF,TYPE]]`` or bare."""
    token = f"[[{ref},{type}]]"
    return f"({title}){token}" if title is not None else token


def token_title(raw: str) -> str | None:
    """The cached title of a raw token string, else ``None``."""
    match = re.fullmatch(
        rf"(?:\((?P<title>[^)\n]+)\)[ ]*)?\[\[{_REF} ?,( ?){_TYPE}\]\]", raw
    )
    return match.group("title") if match is not None else None


def _line_index(lines: list[str]) -> int | None:
    """The index of the ``## Links`` heading line, else ``None``."""
    return next((i for i, line in enumerate(lines) if line.rstrip("\r\n") == "## Links"), None)


def _section_end(lines: list[str], start: int) -> int:
    """The first line after ``start`` holding a level-1 or level-2 heading."""
    end = start + 1
    while end < len(lines) and _HEADING_12.match(lines[end]) is None:
        end += 1
    return end


def _token_identity(text: str) -> tuple[str, str, str | None] | None:
    """``(ref, type, title)`` of a single token list line, else ``None``.

    Comma spacing is not part of the identity, so a legacy ``[[REF, TYPE]]``
    line and its canonical ``[[REF,TYPE]]`` form compare equal.
    """
    match = re.fullmatch(
        rf"[-*+][ \t]+(?:\((?P<title>[^)\n]*)\)[ \t]*)?"
        rf"\[\[(?P<ref>{_REF}) ?,( ?)(?P<type>{_TYPE})\]\]",
        text.strip(),
    )
    if match is None:
        return None
    return match.group("ref"), match.group("type"), match.group("title")


def append_token(text: str, type: str, ref: str, title: str) -> str:
    """Append ``- (TITLE)[[REF,TYPE]]`` to the trailing ``## Links`` section.

    The section is created at the end of the text (preceded by a blank line)
    when absent.  Appending an identical token line twice is a no-op; identity
    ignores comma spacing, so a legacy ``[[REF, TYPE]]`` line is not duplicated
    by its canonical form.
    """
    line = f"- {render_token(type, ref, title)}"
    if not text:
        return f"## Links\n{line}\n"
    lines = text.splitlines(keepends=True)
    index = _line_index(lines)
    if index is None:
        if not text.endswith("\n"):
            text += "\n"
        return f"{text}\n## Links\n{line}\n"
    end = _section_end(lines, index)
    body = lines[index + 1 : end]
    identity = _token_identity(line)
    if identity is not None and any(_token_identity(item) == identity for item in body):
        return text
    insert = end
    while insert > index + 1 and lines[insert - 1].strip() == "":
        insert -= 1
    return "".join(lines[:insert]) + line + "\n" + "".join(lines[insert:])


def _drop_emptied_list_lines(text: str) -> str:
    """Drop list bullets left holding nothing after a token was removed."""
    return "".join(
        line
        for line in text.splitlines(keepends=True)
        if line.strip() not in ("-", "*", "+")
    )


def remove_token(text: str, type: str, ref: str) -> tuple[str, int]:
    """Remove every token with the exact ``(type, ref)``, wherever it sits.

    Prose tokens, title prefix included, are cut in place; a list item that
    held nothing else is dropped whole.  Returns ``(new_text, removed_count)``.
    The ``## Links`` section is dropped when it holds no tokens afterwards.
    """
    matches = [
        match
        for match in _scan_body(text)[0]
        if match.type == type and match.ref == ref
    ]
    if not matches:
        return text, 0
    parts: list[str] = []
    cursor = 0
    for match in matches:
        start, end = match.start, match.end
        if (
            end < len(text)
            and text[end] == " "
            and (start == 0 or text[start - 1] == " ")
        ):
            end += 1
        elif start > 0 and text[start - 1] == " ":
            start -= 1
        parts.append(text[cursor:start])
        cursor = end
    parts.append(text[cursor:])
    text = _drop_emptied_list_lines("".join(parts))
    lines = text.splitlines(keepends=True)
    index = _line_index(lines)
    if index is not None:
        end = _section_end(lines, index)
        body = lines[index + 1 : end]
        if not any(_LIST_TOKEN.fullmatch(item.strip()) for item in body):
            # Drop the section: the heading line plus its (blank) body.
            del lines[index:end]
        text = "".join(lines)
    return text, len(matches)


def repoint_token(
    text: str, old_ref: str, new_ref: str, new_title: str | None = None
) -> tuple[str, int]:
    """Replace ``REF`` inside every token targeting ``old_ref``.

    Prose and list tokens alike, without touching fenced code, code spans or
    escapes.  Rewritten tokens are emitted in canonical form (no space around
    the comma); the cached title prefix is preserved.  When ``new_title`` is
    given, the cached title is set on every rewritten token too.  Returns
    ``(new_text, changed_count)``.
    """
    matches = [match for match in _scan_body(text)[0] if match.ref == old_ref]
    if not matches:
        return text, 0
    pattern = re.compile(rf"(\[\[){re.escape(old_ref)} ?,( ?)({_TYPE})(?=\]\])")
    parts: list[str] = []
    cursor = 0
    for match in matches:
        parts.append(text[cursor : match.start])
        if new_title is None:
            parts.append(pattern.sub(rf"\g<1>{new_ref},\g<3>", match.raw))
        else:
            parts.append(render_token(match.type, new_ref, new_title))
        cursor = match.end
    parts.append(text[cursor:])
    return "".join(parts), len(matches)


def retitle_tokens(
    text: str, titles: Mapping[str, str]
) -> tuple[str, int]:
    """Set the cached title of every token whose ref is a key in ``titles``.

    A missing prefix is added; an existing one is replaced.  Tokens whose ref
    is not mapped, and tokens in fenced code, code spans or escapes, are left
    untouched.  A token counts as changed when its rendered form differs.
    """
    if not titles:
        return text, 0
    matches = [match for match in _scan_body(text)[0] if match.ref in titles]
    if not matches:
        return text, 0
    parts: list[str] = []
    cursor = 0
    changed = 0
    for match in matches:
        replacement = render_token(match.type, match.ref, titles[match.ref])
        if replacement != match.raw:
            changed += 1
        parts.append(text[cursor : match.start])
        parts.append(replacement)
        cursor = match.end
    parts.append(text[cursor:])
    return "".join(parts), changed