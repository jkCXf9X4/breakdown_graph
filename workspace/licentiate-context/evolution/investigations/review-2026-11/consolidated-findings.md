---
id: INFO-028
type: info
layer: evolution
home: evolution/investigations/review-2026-11/consolidated-findings.md
title: Kappa review 2026-11 — consolidated findings
summary: Index to the consolidated review of the whole kappa — 212 severity-ranked
  defects, the verdict, and the verbatim source audits
date: 2026-11-01
status: current
---

# Kappa review 2026-11 — consolidated findings

**The patch plan is `INFO-044`** (`patch-plan.md`), with batch detail and the file:line
verification in `INFO-045`. Start there if you are fixing rather than reading.

Seven independent audits of the whole kappa, consolidated into one severity-ranked record.
212 defects, each with a stable `R-ID`, a location, a one-line fix and an effort estimate.

**Read in this order.**

1. `INFO-043` — the verdict: does the thesis hold up, the three must-fix defects, the top ten
   by cost/benefit, and the per-chapter grounding scoreboard.
2. `INFO-030` — the twelve blockers, cheapest first.
3. `INFO-029` — the full register: severity key, crosswalk, and the severity re-gradings.

**Evidence.**

`source-audits/` holds the seven verbatim audit transcripts, unedited, plus the supporting
verification files. They are raw evidence, not breakdown state: no front matter, never edited.

It also holds the run's remaining raw evidence, preserved verbatim when the run's scratch
directory was cleaned up: the ten per-source and per-topic working notes (`float-inventory-kappa`,
`typography-house-style-audit`, `paper2_kappa_audit`, `paperIV_kappa_audit`,
`grounding_audit_kappa_ch2_110-114`, `intended_use_domain_cluster`,
`mengist2021_traceability_capability`, `blattnig2013_intended_use_findings`,
`findings_broman2015_determinism`, `audit_grounding_batch`) and `verify-final.md`, the
independent audit of the run itself. Their findings are folded into the `R-ID` rows above;
the files are kept as the evidence behind those rows.
