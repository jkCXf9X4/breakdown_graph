---
id: VER-003
type: verification
layer: verification
home: verification/citation-and-bibliography-gate.md
title: Citation and bibliography gate
summary: How citations are proven complete, resolvable, and grounded in library text
date: 2026-11-11
status: current
---

# Citation and bibliography gate

Citekeys live in `thesis/references.yml`; `thesis/references.bib` is generated from the pinned library.
`./thesis/references.sh check` renders a temporary bib, diffs it against the committed file, then scans `thesis/**/*.tex` for cite commands.
Last run reported: `references.bib is up to date; 60 cited keys all listed`.
`references.yml` lists the keys the kappa cites; the two co-simulation papers left it (`INT-002`).
It proves `VER-006`'s backing obligation, and only that one of the six (`VER-005`).

**What check proves:**

- The generated bib matches `references.yml` at the pinned library commit.
- Every cited key appears in `references.yml`, so none drops silently from the bibliography.
- Failure is loud: a cited key outside `references.yml` exits 1 and names the key; a stale bib exits 1 with `run ./thesis/references.sh update`.
- The scan sees `\cite`, `\textcite`, `\parencite` and `\fullcite`; a key used only through one of them is still required in the yml.

**What update and verify do:**

- `update` regenerates `references.bib`, which is never hand-edited; it needs the papis cache dropped after a library metadata edit.
- `verify` refetches metadata for listed keys from Crossref and OpenAlex, report only, no writes; `status` prints the pinned library commit and the document count.

**Grounding rule:**

- Every citation must resolve to a library document with extracted text, and the text must support the sentence (`OPS-004`).
- A metadata-only record is cited only for what its metadata states.
- The rule is enforced by reading, not by a script: no gate compares a sentence to its source text.

**Marker state:**

- 0 `[CN]` markers remain across `thesis/chapters/`, `thesis/tables/` and `thesis/pre/`, down from 101 occurrences in 47 lines.
- The abstract carries no citations by design; markers in the paper summaries became `\Cref` pointers into the appended papers, not new literature (`ARG-004`).

**Remaining gap:**

- `check` cannot see an uncited sentence, only a cited key with no library entry.
- The grounding rule has no mechanical check: a plausible key attached to the wrong sentence passes.
- Four cited-relevant standards are metadata-only and cannot be quoted until a PDF is intaken (`IMP-016`).

**Owns:**

- The citation gate: what `check`, `update`, `verify` and `status` each prove.
- The grounding rule's statement and its stated lack of enforcement.
- The recorded pass line and the marker count.
- That it proves `VER-006`'s backing obligation.

**Excludes:**

- How the bibliography pipeline renders the bib (`OPS-004`).
- Claim-to-result pointers inside the kappa (`ARG-004`).
- Terminology and acronym consistency (`VER-004`).
- Intake steps for a new source (`OPS-008`).
- The four `VER-006` obligations that no check proves (`VER-004`, `VER-005`, `IMP-036`), and the open change that would close a remaining gap (`IMP-016`).