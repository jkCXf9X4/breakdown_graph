---
id: INFO-011
type: info
title: Links form a DAG outside view membership
summary: Typed links express semantics and never add a node to a view; an outside target is reported as external.
date: 2026-11-20
status: current
---

# Links form a DAG outside view membership

Typed links express semantics and never add a node to a view; a target in the store but outside the closure is reported as `external-link`.

- **Shape:** `links` is a list of `{to, type, propagates?, pinned?}` objects that may cross subtrees as a DAG.
- **Membership:** only `contains` decides view membership; a link never pulls its target in.
- **External target:** a link to a node in the store outside the view yields a warning and is dropped from the view's edges (`src/bd_tree/loader.py:478`).
- **Dangling target:** a link to a ref absent from the store is an error, not a warning.
- **Freshness:** `propagates: true` opts this edge into staleness, and `pinned` holds the target body hash from the last reconciliation.
