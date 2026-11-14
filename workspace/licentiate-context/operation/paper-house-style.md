---
id: OPS-002
type: operation
layer: operation
home: operation/paper-house-style.md
title: Paper house style
summary: Shared environments, listing settings, column types, and numbering for Papers
  I-IV
date: 2026-11-11
status: current
---

# Paper house style

Papers I–IV share one layout layer, `thesis/custom/papers-import.tex`.
Adapters supply content; the layer supplies every format decision.
A local format override in an adapter is a defect in the layer, not a permission.

- **`ptable`:** a `table` float, placement `[tbp]`, centred, `\fontsize{8}{9.5}`, `\tabcolsep` 4pt, `\arraystretch` 1.1; an adapter supplies `\caption`, `\label`, and a `tabularx{\linewidth}` body.
- **`ptablewide`:** a `table*` float, placement `[tp]`, with the same font size, column separation and stretch.
- **`pfigure`:** a `figure` float, placement `[tbp]`, centred, caption below.
- **`listing`:** `\newfloat{listing}{tbp}{lop}`, styled `plaintop` through `\restylefloat`; the caption sits above the code and prints `Listing <paper>.<n>`.
- **Caption short forms:** a caption that cross-references another float carries a short form, because the list of figures re-executes captions in the front matter.
- **Listings settings:** one global `\lstset` sets `\fontsize{8}{9.5}\ttfamily`, `breaklines`, `columns=fullflexible`, `keepspaces`, `showstringspaces=false`, `upquote`, `frame=none`, `numbers=none`, and medskip skips.
- **Float spacing:** one `\textfloatsep` of 15pt plus 3pt minus 3pt and one `\intextsep` of 11pt plus 2pt minus 2pt serve every paper.
- **Two columns:** the papers run two columns at `\small` like the articles they came from; the one-column/two-column switch belongs to `\includearticletex` (`OPS-001`).
- **Float measure:** each float is one column or the full measure; `pfigure`, `ptable`, and `plisting` take one column, 163.0pt of the 336.0pt measure.
- **Wide forms:** `pfigurewide`, `ptablewide`, and `plistingwide` span both columns through the starred `figure*`/`table*` forms, and inside a wide float `\linewidth` is the full measure again.
- **`plistingwide`:** a `figure*` carrying `\captionsetup{type=listing}`; the adapter writes `\caption` and `\label` on the float, before the `lstlisting`; both listing forms number from the one `listing` counter.
- **No list of listings:** nothing calls `\listof{listing}`, so the book prints none (`IMP-010`).
- **No `[H]`:** two-column mode allows no `[H]` float.
- **Width choice:** an adapter picks column width per float, column width by default, full measure only for multi-panel rows, aspect ≥ 2 diagrams, and prose tables whose columns cannot hold their longest word.
- **Paper I:** 2 wide tables, 1 narrow table, 6 narrow figures, 3 wide figures; its three tables are `tabularx{\linewidth}` with booktabs rules and no vertical rules, no fixed centimetre width and no manual row space.
- **Paper II:** 5 wide tables, 7 narrow figures, 4 wide figures, 1 wide listing in the body; its second listing is appendix A.1.
- **Paper III:** 1 wide table, 3 narrow figures, 3 wide figures, 7 wide listings in the body; its other three listings are appendix B.1-B.3.
- **Appendix listings:** the book appendices run one column, so they use `plisting` and number `A.1`, `B.1`; `\theHlisting` follows the same prefix to keep hyperref destinations unique.
- **Paper IV:** 3 wide tables, 3 narrow figures, 3 wide figures.
- **Column types:** the shared types are `A`, `L`, `N`, `Y`, `X`; `A` is defined in `papers-import.tex`, the other four in `thesis/settings.tex`.
- **Single-letter rule:** a `\newcolumntype` name must be one character, because `array` appends `\NC@do#1` to `\NC@list` and `\NC@do` takes one undelimited token (`array.sty:249`, `array.sty:260`).
- **Single-letter rule, failure:** a longer name splits, so `\NC@find@p` matches an empty preamble fragment and array raises "Empty preamble: `l' used" for every later tabular, or `Missing number, treated as zero` at `\end{tabularx}`.
- **Column types, declared where:** adapters declare no column type of their own.
- **Numbering format:** a paper prints `IV.1` and `IV.1.1`, never `IV.0.1`; the counter mechanism is `OPS-001`.
- **Adapter body:** an adapter carries body content only; content, cells, captions, numbers, citekeys, and label names stay verbatim.
- **Adapter silence:** it sets no float placement, vertical-space patch, rule style, font size, `\tabcolsep`/`\arraystretch` value, listing frame, line number, or background.
- **Adapter declarations:** it declares no float, no `\captionsetup[sub]`, and no macro that duplicates house machinery.
- **Adapter prefix:** labels and macros stay under the paper prefix whose rule is `OPS-001`.

**Owns:**

- The paper layout layer, its environments, listing settings, and column types.
- The single-letter column-type rule and its `array` failure mode.
- The two widths per float kind and the per-paper float counts.
- The rule that adapters keep content verbatim and override nothing locally.
- That the book prints no list of listings.

**Excludes:**

- The `\includearticletex` behaviour, its counters, and the LaTeX tree: `OPS-001`.
- The build, staging, and pins: `OPS-005`.
- The form each paper ships in: `MS-012`.
- Paper identity and ordering: `RES-001` to `RES-004`, `ARG-003`.
- The appendix page budget: `IMP-008`.
- The two overfull display equations, the two overfull verbatim URLs, the three float-only pages, and the narrow axis text: `IMP-011`.