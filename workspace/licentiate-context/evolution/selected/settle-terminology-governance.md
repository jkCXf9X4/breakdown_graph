---
id: IMP-031
type: imp
layer: evolution
home: evolution/selected/settle-terminology-governance.md
title: Settle terminology governance
summary: Two definitions of the contract differ, the terminology chapter has no prose,
  and three terms carry three names each
date: 2026-11-04
status: selected
---

# Settle terminology governance

The credibility contract has two full definitions that differ: `thesis/custom/glossary.tex:25-28` and `thesis/chapters/03_background.tex:80`.
The prose defers to the glossary as authoritative, so the glossary is the stated authority and the chapter states a different thing.
`thesis/chapters/01_terminology.tex` is 25 lines of pure LaTeX with no prose, and `\glsaddall[types={main}]` at `:12` prints every entry, including three the kappa never uses: `gls-intended-use`, `gls-od` and `gls-dov`.
`gls-credibility` is defined and used nowhere at all, and `gls-credibility-contract` is used once in the whole kappa, so the two domain terms the argument most depends on are defined and then never named in the prose that needs them.
One gap has one name in the thesis and one role word, but the thesis counts the premise as a gap: motivation (`thesis/chapters/04_research_questions_and_contributions.tex:24`), premise (`thesis/chapters/02_introduction.tex:20`, "the motivation premise"), while `INT-001` counts three gaps and `ARG-001` treats this one as the premise.
One clause has one name in the thesis: Intended use (`tab:taxonomy`, `07_synthesis_and_discussion.tex:114`, `06_summary_of_papers.tex:14`, `04_research_questions_and_contributions.tex:20`), and `ARG-001` and `INT-001` now use the same name for the gap.
**Evidence:**

A thesis whose central term has two definitions and whose central clause has three names cannot be checked for consistency, and the examiner's first question about a construct is what it is.
The terminology chapter is the natural home for the answer and currently contains no prose, so the one place a reader looks for the authority is empty.
`\glsaddall` makes the glossary look complete while hiding the fact that the two load-bearing terms are never used, which is the opposite of what a glossary is for.
`07_synthesis_and_discussion.tex:140` makes two promises: that "the rest of the thesis uses the clause names", and that the coarser Kind grouping (definition / process / numerical) is "not used as a third enumeration in the prose". The first is broken at `:178` and `:180`, which call execution a clause and use "scope clause": execution is a delimitation outside the objective (`ARG-006`), and the taxonomy names the other clause "Intended use"; the second is broken at `:169` and `:171`, which argue in terms of "definition credibility" and "definition traceability".

- `thesis/custom/glossary.tex:25-28` and `thesis/chapters/03_background.tex:80` are two differing full definitions.
- `thesis/chapters/03_background.tex:80` states the glossary entry is authoritative.
- `thesis/chapters/01_terminology.tex` is 25 lines, no prose; `:12` is `\glsaddall[types={main}]`, `:16` and `:25` are the two `\printglossary` calls.
- `gls-intended-use`, `gls-od`, `gls-dov` and `gls-credibility` are printed and used zero times in `thesis/chapters/` and `thesis/pre/`; `gls-credibility-contract` is used once.
- Gap naming: the thesis calls the premise a motivation gap (`02_introduction.tex:20`, `04_research_questions_and_contributions.tex:24`); `INT-001` counts three gaps and `ARG-001` treats it as the premise.
- Clause naming: `tab:taxonomy`, `07_synthesis_and_discussion.tex:114`, `06_summary_of_papers.tex:14` and `04_research_questions_and_contributions.tex:20` all name it Intended use; `ARG-001` alone keeps Scope.
- `07_synthesis_and_discussion.tex:140` promises consistent clause names and no third enumeration; `:178` and `:180` call execution a clause and use "scope clause" — execution is a delimitation outside the objective (`ARG-006`), and the taxonomy names the other clause Intended use; `:169` and `:171` use the Kind terms "definition credibility" and "definition traceability".
- Review record `INFO-028`; audit: `.dynamic-harness/261101_082500_e339/review/claims-synthesis.md` F-52 and F-53.
- Audit: `.dynamic-harness/261101_082500_e339/review/prematter-check.md`.
**Acceptance:**

- Each contested term has exactly one authority, named in the thesis, and every other occurrence points at it.
- The two contract definitions are reconciled: one text, or one text plus a stated reason the other differs.
- The terminology chapter states in prose which terms are load-bearing and where their authority lives.
- `\glsaddall` is replaced by use-driven printing, or the three unused entries are removed and the two load-bearing terms are used in the prose that needs them.
- Each gap has one name across `INT-001`, `ARG-001`, ch02 and ch04, and the premise is not counted as a fourth gap.
- The clause has one name across the taxonomy table, the chain steps and the gap list.
- The promises at `07_synthesis_and_discussion.tex:140` hold: `:169`, `:171`, `:178` and `:180` use the clause names and do not reintroduce the Kind grouping as a third enumeration.
**Out of scope:**

- The contract's warrant (`IMP-021`) and its status as an instrument (`IMP-022`).
- The Swedish rendering of the terms (`IMP-026`).
- The ordering of the argument (`IMP-032`).