---
id: OPS-006
type: operation
layer: operation
home: operation/build-and-preview.md
title: Build and preview
summary: Commands to build and read the kappa locally
date: 2026-11-11
status: current
---

# Build and preview

Kappa builds with one Python script from repo root. The script wraps `latexmk`, `biber`, and `makeglossaries`.

**Build the kappa:**

- Run `python3 thesis/build.py` from repo root.
- PDF lands at `thesis/temp/thesis.pdf`.
- Open that file to read the built kappa.
- `latexmk` and `biber` must be on `PATH`; the script exits 127 when either is missing.
- The script merges the four appended papers' bibliographies and ensures their generated figures exist before LaTeX runs.
- The merged bibliography lands in `thesis/temp/papers/papers_combined.bib`.
- All four papers, including Paper I, enter the appendix as LaTeX; no paper PDF is input by the appendix.
- Acronym and glossary lists need `makeglossaries`; the script warns and skips when absent.

**Build papers and kappa:**

- Run `python3 build_all.py` to build Papers 1 to 5, then the kappa.
- Run `python3 build_all.py --only papers` to build only the papers.
- Run `python3 build_all.py --only thesis` to build only the kappa.
- Paper IV stays outside `build_all.py`; the kappa inputs its LaTeX adapter.

**Preconditions:**

- Initialize submodules first; see `OPS-007`.
- `--recursive` matters: Paper IV nests its own submodules.
- The `liuthesis` class comes from the `template/` submodule.
- Paper I enters through its LaTeX adapter; the kappa build never builds Paper I.

**Owns:**

- The commands that build the kappa and all papers, and where output lands.

**Excludes:**

- How the build stages papers and pins commits (`OPS-005`).
- What a green build proves (`VER-002`).
- Where the kappa sources live (`OPS-001`).
- Release snapshots (`OPS-010`).