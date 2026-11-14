from __future__ import annotations

import collections
import re
from pathlib import Path

from breakdown.api import check, load, load_view
from breakdown.frontmatter import parse_document

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "workspace" / "licentiate-n"
SOURCE = ROOT / "workspace" / "licentiate" / "nodes"


def test_migrated_corpus_check():
    result = check(CORPUS)
    assert result.nodes_scanned == 128
    assert result.errors == []
    assert len(result.warnings) == 1
    warning = result.warnings[0]
    assert warning.code == "oversize"
    assert warning.node == "65"
    assert load(CORPUS).nodes["65"].legacy == "INFO-038"


def test_migrated_corpus_is_a_tree_reachable_from_view_one():
    store = load(CORPUS)
    assert len(store.nodes) == 128
    assert len(load_view(CORPUS, "1").nodes) == 128

    parents: dict[str, list[str]] = collections.defaultdict(list)
    for node in store.nodes.values():
        for child in node.contains or []:
            parents[child].append(node.ref)
    assert all(len(sources) <= 1 for sources in parents.values())

    seen: set[str] = set()
    stack = ["1"]
    while stack:
        ref = stack.pop()
        if ref in seen:
            continue
        seen.add(ref)
        node = store.nodes[ref]
        stack.extend(store.effective_contains(ref))
        stack.extend(version.ref for version in store.versions(node.id))
    assert seen == set(store.nodes)


def test_migrated_bodies_equal_source_bodies_after_token_rewrite():
    store = load(CORPUS)
    legacy_to_ref = {node.legacy: node.ref for node in store.nodes.values() if node.legacy}
    assert len(legacy_to_ref) == 128

    def rewrite(text: str) -> str:
        for old in sorted(legacy_to_ref, key=len, reverse=True):
            text = re.sub(
                r"(?<![A-Za-z0-9])" + re.escape(old) + r"(?![A-Za-z0-9])",
                legacy_to_ref[old],
                text,
            )
        return text

    mismatches: list[str] = []
    for path in sorted(SOURCE.glob("*.md")):
        source = parse_document(path.read_text(encoding="utf-8"))
        old_id = source.meta["id"]
        target = CORPUS / "nodes" / f"{legacy_to_ref[old_id]}.md"
        migrated = parse_document(target.read_text(encoding="utf-8"))
        if migrated.body != rewrite(source.body):
            mismatches.append(old_id)
    assert mismatches == []
