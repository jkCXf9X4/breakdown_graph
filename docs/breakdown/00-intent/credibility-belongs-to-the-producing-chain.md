---
id: INFO-002
type: info
title: Credibility belongs to the producing chain
summary: A result is credible through the chain that produces it, not through one model or document.
date: 2026-11-20
status: current
---

# Credibility belongs to the producing chain

A result is credible through the chain that produces it — intent, claims, argument, evidence, manuscript, verification, operation — not through one model or one document.

- **Chain scope:** credibility is a property of the layered chain, so a missing or contradicting layer weakens the result without changing any single node.
- **Linked layers:** typed `links` record support, contradiction, provenance, and review between nodes of different layers.
- **Freshness:** a link with `propagates: true` stores the target body hash at reconciliation, and `bd stale` compares it with the current body.
- **Per-edge state:** one evidence node can be fresh for one claim and stale for another; freshness is per edge, not per node.
- **Handover:** the chain is what a handover carries, so losing a layer loses the argument even when every remaining document is current.
