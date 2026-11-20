---
id: INFO-009
type: info
title: A filename encodes identity and version
summary: The ref is the filename: id.md is main and id-version.md is one alternative inside a checkout.
date: 2026-11-20
status: current
---

# A filename encodes identity and version

The ref is the filename: `<id>.md` is main and `<id>-<version>.md` is one alternative inside the current checkout.

- **Grammar:** `^(?P<id>[1-9]\d*)(?:-(?P<version>[1-9]\d*))?\.md$` — positive integers, no leading zeros (`src/bd_tree/loader.py:32`).
- **Main:** version 0 is unsuffixed, so `5.md` is main while `5-1.md` and `5-2.md` are versions of node `5`.
- **Exact lookup:** a ref resolves to one file, and a missing version never falls back to main or to another branch.
- **Main required:** every id with a version keeps a main file, or `missing-main` is reported.
- **Front-matter `id`:** optional, and a value that differs from the filename raises `id-filename-mismatch`.
- **Scope:** a version is a tracked file in one branch and is absent from another branch until the branches merge.
