---
id: OPS-005
type: operation
layer: operation
home: operation/build-and-pin-system.md
title: Build and pin system
summary: Build script, staging paths, and submodule pins
date: 2026-11-11
status: current
---

# Build and pin system

`thesis/build.py` builds the kappa; `build_all.py` builds the papers first, then the kappa.
Each paper is a git submodule pinned at a commit, not at a branch tip.

- **Thesis build:** `thesis/build.py` runs `latexmk -pdf` with `-outdir=thesis/temp`; it requires `latexmk` and `biber` in `PATH` and returns 127 when either is missing.
- **Stale files:** it deletes stale `thesis.*` aux, bcf, bbl, blg, log, fls, fdb_latexmk, run.xml, glo/gls/glg, and acn/acr/alg files under `thesis/temp`.
- **Glossary pass:** it merges the paper bibliographies, runs `makeglossaries` when `thesis.glo` or `thesis.acn` exists, then reruns latexmk.
- **Search paths:** it sets `TEXINPUTS` to the staged papers, `thesis/`, then `template//`, and `BIBINPUTS` to the staged papers and `thesis/`, because biber ignores `TEXINPUTS`.
- **Paper figures:** no paper PDF is staged, so the build regenerates no paper figure; every figure the appended papers need is already committed, and `thesis/build.py` carries no figure hook.
- **Build all:** `build_all.py` runs five paper build scripts in order (Papers I–III plus the two co-simulation repositories that stay pinned outside the book), then `thesis/build.py`; it stops at the first failing paper and returns that exit code, and `--only {thesis,papers}` narrows the run.
- **Paper IV entry:** `\includearticletex{paper4_purpose_driven_modelling}` at `thesis/thesis.tex:54`; the shim is `thesis/papers/paper4_purpose_driven_modelling.tex`.
- **Paper IV adapter:** `papers/2026_purpose_driven_modelling/kappa/paper.tex`, pinned at `101c21f` on branch `kappa`, past tag `final-submission` (`64523ba`); `IMP-004` holds its accepted-body confirmation.
- **Adapter shape:** a self-contained snapshot of the paper's `sections/`, with `\begingroup`, `\graphicspath` to the paper root, headings demoted one level, and labels and refs prefixed `p6:`.
- **Adapter tables:** its three tables use `ptable` with a `tabularx{\linewidth}` body and booktabs rules; cells stay verbatim (`OPS-002`).
- **Adapter headings:** its six miniheadings are `\paragraph`, run-in and unnumbered, because their numbers are hand-typed content.
- **Adapter drops:** the Acknowledgments stay; abstract, title, authors, INCOSE block, keywords, `multicols*`, `\newacronym`, per-paper bibliography, and biographies are dropped.
- **Standalone build:** the paper keeps building standalone with its own `python3 build.py`.
- **Submodules:** `.gitmodules` gives each of the six paper submodules `branch = kappa`, of which four enter the book and two stay pinned outside it (`INT-002`); `template` carries no branch key; `3rd_party/references` and `3rd_party/article_common_artifacts` track `main`.
- **Paper pins:** Paper I `0e841a2`, Paper II `f685882`, Paper III `e8c8aad`, Paper IV `101c21f`; the two co-simulation repositories pin `faa4987` and `6ed1a90` and are not cited by the kappa.
- **Paper tags:** each paper repo carries a `final-submission` tag; Paper I also carries `published` at `56ff392` on `main`, and its `kappa` branch sits past it.
- **Tool pins:** `template` `5982845`, `3rd_party/references` `dcba044`, `3rd_party/article_common_artifacts` `9c4421f`.
- **Listing captions:** every listing caption sits as plain `\caption`/`\label` on the float (`OPS-002`).
- **Pin discipline:** edit in the paper repo, commit there, then bump the pointer here.

**Owns:**

- The build scripts, their staging paths, and their per-paper exceptions.
- The submodule inventory, pin commits, and tag naming.

**Excludes:**

- Build gate criteria: `VER-002`.
- The merged paper bibliography and the printed list: `OPS-004`.
- The paper house style, column types, and adapter contract: `OPS-002`.
- The `\includearticletex` behaviour and the LaTeX tree: `OPS-001`.
- Submodule routine steps: `OPS-007`.
- Release and submission: `OPS-010`.
- Paper roles and ordering: `ARG-003`, `RES-001` to `RES-004`.