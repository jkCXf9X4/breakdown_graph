#!/usr/bin/env python3
"""One-off migration: typed-ID licentiate corpus -> numeric containment tree.

Source: ``workspace/licentiate/nodes`` (read-only, 128 typed-ID nodes).
Destination: ``workspace/licentiate-n``.

The rule, per the migration spec:
- layer order: intent 0, claims 1, argument 2, evidence 3, manuscript 4,
  verification 5, operation 6, review 7, evolution 8 (default);
- root is ``INT-001``;
- a node's parent is its cited target with the lowest strictly-lower layer
  index, ties broken by the lowest old numeric suffix; with no candidate the
  parent is the root;
- the tree is laid out DFS pre-order from the root, children sorted by
  (layer index, old id), and new ids are assigned 1..N in that order.
"""

from __future__ import annotations

import argparse
import collections
import re
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml

LAYERS = {
    "intent": 0,
    "claims": 1,
    "argument": 2,
    "evidence": 3,
    "manuscript": 4,
    "verification": 5,
    "operation": 6,
    "review": 7,
    "evolution": 8,
}
DEFAULT_LAYER = 8
ROOT_OLD = "INT-001"
OLD_ID = re.compile(r"^([A-Z][A-Z0-9]*)-(\d{2,4})$")
FENCED = re.compile(r"^[ \t]*(```|~~~).*?^[ \t]*\1[ \t]*$", re.S | re.M)
CITATION = re.compile(r"`([A-Z][A-Z0-9]{1,9}-\d{2,4})`")


def split_document(text: str) -> tuple[dict[str, Any], str]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening '---'")
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            meta = yaml.safe_load("".join(lines[1:i])) or {}
            if not isinstance(meta, dict):
                raise ValueError("front matter is not a mapping")
            return meta, "".join(lines[i + 1 :])
    raise ValueError("missing closing '---'")


def render_document(meta: dict[str, Any], body: str) -> str:
    fm = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, default_flow_style=False)
    if not fm.endswith("\n"):
        fm += "\n"
    return "---\n" + fm + "---\n" + body


def old_suffix(old_id: str) -> int:
    match = OLD_ID.match(old_id)
    if not match:
        raise ValueError(f"not a typed id: {old_id}")
    return int(match.group(2))


def layer_index(meta: dict[str, Any]) -> int:
    return LAYERS.get(str(meta.get("layer") or ""), DEFAULT_LAYER)


def replace_tokens_independent(text: str, mapping: dict[str, str]) -> str:
    """Deliberately separate replacer, used for the body gate."""
    result = text
    for old_id in sorted(mapping, key=len, reverse=True):
        result = re.sub(
            r"(?<![A-Za-z0-9])" + re.escape(old_id) + r"(?![A-Za-z0-9])",
            mapping[old_id],
            result,
        )
    return result


def rewrite_strings(value: Any, pattern: re.Pattern[str], mapping: dict[str, str]) -> Any:
    if isinstance(value, str):
        return pattern.sub(lambda match: mapping.get(match.group(1), match.group(1)), value)
    if isinstance(value, list):
        return [rewrite_strings(item, pattern, mapping) for item in value]
    if isinstance(value, dict):
        return {key: rewrite_strings(item, pattern, mapping) for key, item in value.items()}
    return value


def migrate(src: Path, dest: Path, *, force: bool = False) -> int:
    source_dir = src / "nodes"
    if not source_dir.is_dir():
        raise SystemExit(f"source nodes directory not found: {source_dir}")
    if dest.resolve() == src.resolve() or src.resolve() in dest.resolve().parents:
        raise SystemExit("destination must not be inside the read-only source")
    nodes_dir = dest / "nodes"
    if nodes_dir.exists() and any(nodes_dir.iterdir()):
        if not force:
            raise SystemExit(f"destination {nodes_dir} is not empty (use --force)")
        shutil.rmtree(nodes_dir)
    nodes_dir.mkdir(parents=True, exist_ok=True)

    docs: dict[str, tuple[dict[str, Any], str, Path]] = {}
    for path in sorted(source_dir.glob("*.md")):
        meta, body = split_document(path.read_text(encoding="utf-8"))
        old_id = meta.get("id")
        if not isinstance(old_id, str) or not OLD_ID.match(old_id):
            raise SystemExit(f"{path.name}: typed id expected, got {old_id!r}")
        if old_id in docs:
            raise SystemExit(f"duplicate old id {old_id}")
        docs[old_id] = (meta, body, path)

    if ROOT_OLD not in docs:
        raise SystemExit(f"root {ROOT_OLD} not found in source")

    anomalies: list[str] = []
    parent: dict[str, str] = {}
    root_children: list[str] = []
    cited_unknown: set[str] = set()
    for old_id, (meta, body, _path) in docs.items():
        if old_id == ROOT_OLD:
            continue
        visible = FENCED.sub("", body)
        citations = set(CITATION.findall(visible))
        missing = sorted(token for token in citations if token not in docs)
        cited_unknown.update(missing)
        node_layer = layer_index(meta)
        candidates: list[tuple[int, int, str]] = []
        for token in citations:
            if token == old_id or token not in docs:
                continue
            target_layer = layer_index(docs[token][0])
            if target_layer < node_layer:
                candidates.append((target_layer, old_suffix(token), token))
        if candidates:
            parent[old_id] = min(candidates)[2]
        else:
            parent[old_id] = ROOT_OLD
            root_children.append(old_id)

    children: dict[str, list[str]] = collections.defaultdict(list)
    for old_id, parent_id in parent.items():
        children[parent_id].append(old_id)
    for parent_id in children:
        children[parent_id].sort(key=lambda oid: (layer_index(docs[oid][0]), oid))

    ordered: list[str] = []
    depth: dict[str, int] = {ROOT_OLD: 0}

    def visit(old_id: str) -> None:
        ordered.append(old_id)
        for child in children.get(old_id, []):
            depth[child] = depth[old_id] + 1
            visit(child)

    visit(ROOT_OLD)
    if len(ordered) != len(docs):
        missing = sorted(set(docs) - set(ordered))
        anomalies.append("not reached by DFS: " + ", ".join(missing))
        ordered.extend(missing)

    mapping = {old_id: str(index) for index, old_id in enumerate(ordered, start=1)}
    pattern = re.compile(
        r"(?<![A-Za-z0-9])("
        + "|".join(sorted((re.escape(oid) for oid in mapping), key=len, reverse=True))
        + r")(?![A-Za-z0-9])"
    )

    mismatches: list[str] = []
    written = 0
    for old_id in ordered:
        meta, body, _path = docs[old_id]
        new_ref = mapping[old_id]
        new_body = pattern.sub(lambda m: mapping.get(m.group(1), m.group(1)), body)
        expected = replace_tokens_independent(body, mapping)
        if new_body != expected:
            mismatches.append(old_id)
        new_contains = [mapping[child] for child in children.get(old_id, [])]

        new_meta: dict[str, Any] = {
            "id": int(new_ref),
            "legacy": old_id,
            "type": meta.get("type"),
            "layer": meta.get("layer"),
            "home": rewrite_strings(meta.get("home"), pattern, mapping),
            "title": rewrite_strings(meta.get("title"), pattern, mapping),
            "summary": rewrite_strings(meta.get("summary"), pattern, mapping),
            "date": meta.get("date"),
            "status": meta.get("status"),
        }
        if new_contains:
            new_meta["contains"] = new_contains
        if meta.get("links"):
            links = rewrite_strings(meta["links"], pattern, mapping)
            for link in links:
                if isinstance(link, dict):
                    target = link.get("to")
                    if isinstance(target, str) and OLD_ID.match(target):
                        link["to"] = mapping.get(target, target)
            new_meta["links"] = links
        (nodes_dir / f"{new_ref}.md").write_text(
            render_document(new_meta, new_body), encoding="utf-8", newline=""
        )
        written += 1

    unknown_tokens = sorted(
        {
            token
            for _meta, body, _path in docs.values()
            for token in CITATION.findall(FENCED.sub("", body))
            if token not in docs
        }
    )
    root_children.sort(key=lambda oid: (layer_index(docs[oid][0]), oid))
    max_children = max((len(kids) for kids in children.values()), default=0)
    max_children_id = max(children, key=lambda oid: len(children[oid])) if children else ROOT_OLD
    max_depth = max(depth.values(), default=0)
    intent_root_kids = [oid for oid in root_children if layer_index(docs[oid][0]) == 0]
    other_root_kids = [oid for oid in root_children if oid not in intent_root_kids]

    lines = [
        "# Migration: typed IDs -> numeric refs",
        "",
        f"Source: `{src}` (read-only, {len(docs)} nodes)",
        f"Destination: `{dest}`",
        "",
        "## Rule",
        "",
        "- Parent = the cited target with the lowest strictly-lower layer index; "
        "ties broken by the lowest old numeric suffix; no candidate means the root.",
        "- Layer order: intent 0, claims 1, argument 2, evidence 3, manuscript 4, "
        "verification 5, operation 6, review 7, evolution 8 (default).",
        "- Root = `INT-001`. Children are DFS pre-ordered by (layer index, old id); "
        "new ids are assigned 1..N in that order, so `1` is the intent root.",
        "- Each new file keeps body, type, layer, title, summary, date, status and "
        "home; sets integer `id`, adds `legacy`, maps links and rewrites every old "
        "typed-ID token in the body and string fields.",
        "",
        "## Counts",
        "",
        f"- nodes written: {written}",
        f"- root: `{ROOT_OLD}` -> `1`",
        f"- parented nodes (parent != root): {len(parent) - len(root_children)}",
        f"- attached directly to root: {len(root_children)} "
        f"({len(other_root_kids)} non-intent + {len(intent_root_kids)} intent-layer)",
        f"- max depth: {max_depth}",
        f"- max children: {max_children} (`{max_children_id}` -> `{mapping[max_children_id]}`)",
        "",
        "## Root-attached nodes",
        "",
    ]
    for old_id in root_children:
        marker = " (intent layer)" if old_id in intent_root_kids else ""
        lines.append(f"- `{old_id}` -> `{mapping[old_id]}`{marker}")
    lines.extend(["", "## Anomalies", ""])
    if unknown_tokens:
        lines.append("- citations to ids outside the source: " + ", ".join(unknown_tokens))
    if cited_unknown:
        lines.append(
            f"- {len(cited_unknown)} distinct outside citations were left unchanged"
        )
    if mismatches:
        lines.append("- body gate mismatches: " + ", ".join(mismatches))
    if not unknown_tokens and not mismatches:
        lines.append("- none; body gate: 0 mismatches")
    lines.append("")

    (dest / "MIGRATION.md").write_text("\n".join(lines), encoding="utf-8", newline="")

    print(f"wrote {written} nodes to {nodes_dir}")
    print(
        f"parented={len(parent) - len(root_children)} root-attached={len(root_children)} "
        f"(non-intent={len(other_root_kids)}, intent={len(intent_root_kids)})"
    )
    print(f"max-depth={max_depth} max-children={max_children} ({max_children_id})")
    print(f"body-gate-mismatches={len(mismatches)}")
    print(f"unknown-citations={len(unknown_tokens)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    here = Path(__file__).resolve().parents[1]
    parser.add_argument("--src", default=str(here / "workspace" / "licentiate"))
    parser.add_argument("--dest", default=str(here / "workspace" / "licentiate-n"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    return migrate(Path(args.src).resolve(), Path(args.dest).resolve(), force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
