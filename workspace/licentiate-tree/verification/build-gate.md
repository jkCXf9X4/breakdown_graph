---
id: VER-002
type: verification
layer: verification
home: verification/build-gate.md
title: Build gate
summary: What a green build proves about the kappa
date: 2026-11-11
status: current
---

# Build gate

`python3 thesis/build.py` compiles the kappa and writes `thesis/temp/thesis.pdf`.
The current run produces 184 pages and 5494645 bytes with the papers two-column at `\small` (`OPS-002`).
It proves `OPS-011`'s length obligation and none of `VER-007` (`VER-005`).

**Current state:**

- `thesis/temp/thesis.blg` reports 0 biber errors and 15 warnings: 9 legacy `month` fields, 3 month-over-date overwrites, 3 invalid ISBNs.
- `thesis/temp/thesis.log` names no missing citation and no missing label; the rendered PDF carries no `??`.
- The log prints one `There were undefined references` line with no label behind it; it is biblatex's rerun request, not a missing label.
- The run reports 0 array errors, 0 undefined citations, 0 undefined glossary entries and 0 `Float too large` warnings.
- It reports 3 overfull and 188 underfull `\hbox` warnings: two 4.90pt Paper IV zenodo URLs (`IMP-011`) and one 39.11pt Papyrus project URL in a paper table; every kappa-chapter overfull is cleared.
- `grep Lnköping` over the rendered PDF text returns 0 matches.

**Acceptance criterion:**

- `python3 thesis/build.py` exits 0 and no line in `thesis/temp/thesis.log` contains `!`.
- Page count is 184 and file size 5494645 bytes at the recorded pins; a change is explained before the build counts green.
- The generic undefined-reference warning and the three recorded overfull hboxes are the tolerated state; a new unrecorded one needs an explanation, and a named missing label does not.

**What a green build proves:**

- The document compiles end to end from the current sources and paper pins.
- Every `\ref` and `\cite` resolves, and one bibliography serves the kappa chapters and all four papers.
- The acronym table loads and the appendix includes resolve without a guard dropping one.

**What it does not prove:**

- Content quality: a compiling chapter can still be wrong or unreadable.
- Citation completeness, claim support and terminology consistency (`VER-003`, `ARG-004`, `VER-004`).
- That the paper pin matches the accepted version (`OPS-007`).
- Any reader criterion: nothing here opens the PDF and judges it (`VER-007`).

**Limits of the evidence:**

- The `Lnköping` grep covers rendered text only; the `liu` key was never used, so a clean log cannot clear the acronym table (`VER-004`).

**Owns:**

- The build gate: its acceptance criterion, reference page count and size.
- The recorded evidence that the gate last passed, and what that run did not cover.
- That it proves `OPS-011`'s length obligation and no criterion of `VER-007`.

**Excludes:**

- Build commands and preview steps (`OPS-006`).
- Build tooling, paper staging and pin mechanics (`OPS-005`, `OPS-007`).
- Citation gate and its gap (`VER-003`, `IMP-001`).
- Terminology checks (`VER-004`).
- The requirement to check map (`VER-005`).