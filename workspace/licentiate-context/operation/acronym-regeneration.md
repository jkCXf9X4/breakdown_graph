---
id: OPS-009
type: operation
layer: operation
home: operation/acronym-regeneration.md
title: Acronym regeneration
summary: Rebuilding the union table after a paper changes
date: 2026-11-11
status: current
---

# Acronym regeneration

The union table merges acronym files from four paper roots plus the kappa. The generated output is `acronyms.tex`.

**Regenerate:**

- Run from `3rd_party/article_common_artifacts/latex/acronyms`.

```bash
python3 build_union.py --out-dir . \
  /home/eriro/pwa/notes/phd/licentiate/papers/Simulation_and_models \
  /home/eriro/pwa/notes/phd/licentiate/papers/model_domain_classification \
  /home/eriro/pwa/notes/phd/licentiate/papers/automation_complex_vv_workflows \
  /home/eriro/pwa/notes/phd/licentiate/papers/2026_purpose_driven_modelling
```

- Output is byte-identical across runs given the same root arguments; the header echoes the roots as passed, so relative and absolute paths render differently.
- The committed `acronyms.tex` header also lists `thesis/custom` under the label `kappa`, so it was generated with that fifth root; the four-root command reproduces the body, not that header line.
- The 2026-11-04 run of this command exits 2 on two form conflicts and one option conflict; see `VER-004`.
- The kappa includes the table through `thesis/custom/acronyms.tex`.
- Never hand-edit `acronyms.tex` or `conflicts.md`.

**Conflicts:**

- The script exits 2 when `conflicts.md` is non-empty.
- The open conflicts are `hla` and `liu` (form) and `opscon` (option); a dry run with those three declared in `resolutions.yml` exits 0 and leaves the table body byte-identical.
- `resolutions.yml` is not in this repo: it lives beside `build_union.py` in the pinned tooling submodule, so accepting a conflict means a submodule edit and a re-pin (`VER-004`).
- Fix a paper's own source when that paper is wrong; commit in its repo (`OPS-007`).
- Record an accepted meaning clash in `resolutions.yml`.
- `--resolutions FILE` defaults to `<out-dir>/resolutions.yml`.
- Do not use `--allow-conflicts`; it hides the conflict instead of accepting it.
- `--prefer ROOT` picks the root that wins a conflict; default is the last root.

**Kappa-only terms:**

- Put terms the kappa alone uses in `thesis/custom/acronyms-local.tex`.
- Do not add the kappa as a fifth root; it includes the union and keeps local terms.

**Owns:**

- The command that rebuilds the union acronym table and how conflicts are accepted.

**Excludes:**

- How the glossary and acronym pipeline is built (`OPS-003`).
- Terminology consistency checks (`VER-004`).
- Editing a paper's own acronym source (`OPS-007`).