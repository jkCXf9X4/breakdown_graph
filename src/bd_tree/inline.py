"""Scanner for reserved inline link tokens in node Markdown bodies.

Link declarations live in node bodies as reserved tokens, not in front
matter.  The token grammar is::

    [[ TYPE , REF ]]  optionally followed by zero or more spaces then ( TITLE )

``TYPE`` is ``[A-Za-z][A-Za-z0-9_-]*``; ``REF`` is a full ref only,
``[0-9]+-[0-9]+``; at most one optional space may sit on each side of the
comma, and none after ``[[`` or before ``]]``.  ``TITLE`` is any run of
characters except ``)`` and newline and must be non-empty.

Ignored (neither links nor errors): fenced code blocks (backticks and tildes,
fence of three or more characters, with or without a language), inline code
spans (single-line backtick pairs), and the ``\\[[`` escape.  Indented code
blocks and HTML comments are NOT handled in this pass.

An unterminated token (no closing ``]]`` on the same token) is an anomaly with
reason ``unterminated``; any other ``[[]]``-shaped fragment that fails the
grammar is an anomaly with a short reason.  Code spans, fences and escapes
never produce anomalies.

The writer helpers (``append_token``, ``remove_token``, ``repoint_token``) are
the write unit's interface for maintaining the trailing ``## Links`` section.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_TYPE = r"[A-Za-z][A-Za-z0-9_-]*"
_REF = r"[0-9]+-[0-9]+"

# The full fragment between the brackets: `TYPE ?,( ?)REF`.
_FRAGMENT = re.compile(rf"(?P<type>{_TYPE}) ?,( ?)(?P<ref>{_REF})\Z")
# A token list line maintained under `## Links`.
_LIST_TOKEN = re.compile(
    rf"^- \[\[(?P<type>{_TYPE}) ?,( ?)(?P<ref>{_REF})\]\]"
    r"(?: *\([^)]*\))?$"
)
_OPEN_BRACKETS = re.compile(r"\[\[")
_BACKTICK_RUN = re.compile(r"`+")
_FENCE_OPEN = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$", re.DOTALL)
_HEADING_12 = re.compile(r"^ {0,3}#{1,2}(\s|$)")


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
    start: int  # absolute body offset of the opening ``[[``
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


def _fragment_reason(fragment: str) -> str:
    """A short reason for a fragment that failed `TYPE ?,( ?)REF`."""
    if fragment == "":
        return "empty token"
    if "," not in fragment:
        return "missing ','"
    type_part, _, ref_part = fragment.partition(",")
    if not re.fullmatch(rf"{_TYPE} ?", type_part):
        return "invalid type"
    if re.fullmatch(r"[0-9]+", ref_part.strip()):
        return "bare ref"
    return "invalid ref"


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
            close = line.find("]]", cursor)
            while close != -1 and any(start <= close < end for start, end in regions):
                close = line.find("]]", close + 2)
            if close == -1:
                anomalies.append(InlineAnomaly(line_number, index + 1, "unterminated"))
                continue
            fragment = line[cursor:close]
            parsed = _FRAGMENT.fullmatch(fragment)
            if parsed is None:
                anomalies.append(
                    InlineAnomaly(
                        line_number, index + 1, _fragment_reason(fragment)
                    )
                )
                cursor = close + 2
                continue
            end = close + 2
            title: str | None = None
            rest = line[end:]
            stripped = rest.lstrip(" ")
            if stripped.startswith("("):
                parenthesis = stripped.find(")")
                if parenthesis == -1:
                    anomalies.append(
                        InlineAnomaly(line_number, index + 1, "unterminated title")
                    )
                    cursor = close + 2
                    continue
                title = stripped[1:parenthesis]
                if title == "":
                    anomalies.append(
                        InlineAnomaly(line_number, index + 1, "empty title")
                    )
                    cursor = close + 2
                    continue
                end += len(rest) - len(stripped) + parenthesis + 1
                cursor = end
            raw = line[index:end].rstrip("\r\n")
            matches.append(
                _Match(
                    line=line_number,
                    col=index + 1,
                    type=parsed.group("type"),
                    ref=parsed.group("ref"),
                    title=title,
                    start=offset + index,
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
    """The canonical token text: ``[[TYPE, REF]]`` plus ``(TITLE)``."""
    token = f"[[{type}, {ref}]]"
    return f"{token}({title})" if title is not None else token


def token_title(raw: str) -> str | None:
    """The cached title of a raw token string, else ``None``."""
    match = re.fullmatch(
        rf"\[\[{_TYPE} ?,( ?){_REF}\]\](?: *\((?P<title>[^)]*)\))?", raw
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


def append_token(text: str, type: str, ref: str, title: str) -> str:
    """Append ``- [[TYPE, REF]](TITLE)`` to the trailing ``## Links`` section.

    The section is created at the end of the text (preceded by a blank line)
    when absent.  Appending an identical token line twice is a no-op.
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
    if any(item.strip() == line for item in body):
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

    Prose tokens are cut in place; a list item that held nothing else is
    dropped whole.  Returns ``(new_text, removed_count)``.  The ``## Links``
    section is dropped when it holds no tokens afterwards.
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


def repoint_token(text: str, old_ref: str, new_ref: str) -> tuple[str, int]:
    """Replace ``REF`` inside every token targeting ``old_ref``.

    Prose and list tokens alike, without touching fenced code, code spans or
    escapes.  Returns ``(new_text, changed_count)``.
    """
    matches = [match for match in _scan_body(text)[0] if match.ref == old_ref]
    if not matches:
        return text, 0
    pattern = re.compile(rf"(\[\[{_TYPE} ?,( ?)){re.escape(old_ref)}(?=\]\])")
    parts: list[str] = []
    cursor = 0
    for match in matches:
        parts.append(text[cursor : match.start])
        parts.append(pattern.sub(rf"\g<1>{new_ref}", match.raw))
        cursor = match.end
    parts.append(text[cursor:])
    return "".join(parts), len(matches)
