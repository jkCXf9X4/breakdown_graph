---
id: IMP-016
type: imp
layer: evolution
home: evolution/selected/intake-metadata-only-standards.md
title: Intake PDFs for the metadata-only standards
summary: Four cited-relevant standards have no extracted text and cannot be quoted
date: 2026-11-04
status: selected
---

# Intake PDFs for the metadata-only standards

`OPS-004` allows a citation only where the library document has extracted text.
Four documents that the background chapter would otherwise draw on hold `info.yaml` only: `asmeStandardVerificationValidation2009` (ASME V&V 20), `oberkampfPredictiveCapabilityMaturity2007` (PCMM), `associationDistributedCoSimulationProtocol2019` (DCP specification), and `modelicaassociationSSPTraceabilitySpecification2022`.
`bajajSystemsModelingLanguage2022` (SysML v2) is in the same state.
Each is real and resolves through the library; none can be quoted or checked against a claim.
**Evidence:**

The novelty positioning in `03_background` argues against four credibility frameworks and cites secondary descriptions where the primary text would be stronger.
Claims about DCP, the SSP Traceability specification and SysML v2 are either avoided or attributed to a paper that describes them, which weakens the section an examiner reads first.
A bibliography whose standards cannot be read is traceable in form and untraceable in substance, which is the failure `OPS-004` is written to prevent.

- `ls 3rd_party/references/library/asmeStandardVerificationValidation2009` returns `info.yaml` only, and the same holds for the other four.
- `refs get asmeStandardVerificationValidation2009` resolves the record, so the gap is text, not metadata.
- `03_background` cites `blattnigNASAStandardModels2013` for what PCMM covers, and `rosenlundObjectivelyDefinedIntended2024` for what SSP Traceability records, because the primaries cannot be quoted.
- DCP is cited through `arakiHybridPowerSystems2023`.
**Acceptance:**

- Each of the five documents has `text.md`, obtained through `refs intake` from a licensed copy.
- Each `text.md` covers the document's body, not only its front matter. Both checks must pass:
  - **Extent.** `text_pages` is at least half the document's real extent. Real extent is `numPages` when the record declares it, otherwise the highest page number in a table-of-contents entry in the first half of `text.md`, ignoring four-digit numbers in 1900-2100, which are years and not pages.
  - **Body heading.** `content.md` holds at least one heading that is not front matter: after stripping a leading roman-numeral page prefix, the heading is not one of contents, preface, foreword, acknowledgements, list of figures or tables, abstract, index, bibliography, or the document's own title, and it carries at least two words.
- A document failing either check is recorded as text-inadequate, and no claim is made against it past what its front matter contains.
- Where a licence forbids filing the text, the leaf records the exclusion and the claim is attributed to a source that can be read.
- The affected sentences in `03_background` are upgraded to the primary source or explicitly left on the secondary.
**Out of scope:**

- Documents cited only for metadata (title, venue, year, DOI).
- The library's 206 DOI-less records reported by `refs lint`.
- The adequacy criterion that decides whether an extracted `text.md` covers the body, and the recorded limitation on `oberkampfVerificationValidationScientific2010` (`IMP-030`).