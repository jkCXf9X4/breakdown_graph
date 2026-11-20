---
id: INFO-016
type: info
title: Model and checker separate shape from validation
summary: Dataclasses hold the loaded graph; structural issues are reported by an independent checker.
date: 2026-11-20
status: current
---

# Model and checker separate shape from validation

`model.py` defines the containers and `checker.py` inspects a freshly loaded store without mutating it.

- **Model types:** `Node`, `Store`, `View`, `Edge`, and `Issue`; `Store.effective_contains` applies version inheritance and `View` holds the closure.
- **Issues as data:** the loader records `Issue(level, code, message, node, path)`, and `CheckResult.ok` is true when no error remains.
- **Checker scope:** filename grammar, id mismatch, duplicate refs, missing mains, containment targets and cycles, per-view trees, reachability, homes, links, and size.
- **Independent pass:** `check()` calls `load` again, so it validates the files instead of trusting an edited in-memory graph.
- **Opt-in schema:** `--require FIELD` is the only front-matter validation; arbitrary keys, link types, and layer names pass untouched.
