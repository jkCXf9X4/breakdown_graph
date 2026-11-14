---
id: IMP-026
type: imp
layer: evolution
home: evolution/selected/rewrite-the-swedish-abstract.md
title: Rewrite the Swedish abstract as a faithful equivalent
summary: The Swedish abstract omits the contract, the compilation framing and the
  retrospective result, and substitutes accuracy for credibility
date: 2026-11-04
status: selected
---

# Rewrite the Swedish abstract as a faithful equivalent

`thesis/pre/sammanfattning.tex:33-41` is 278 words and is not a translation of the English abstract.
It omits the credibility contract entirely, which is the English abstract's central contribution and the synthesis's organizing term.
It omits the six-paper compilation framing, so a Swedish-only reader is not told the thesis is a compilation.
It omits the application to the in-repo case and its clause verdicts.
It reframes the research question as how simulations "påverkar trovärdighet och komplexitet" (`:39`), which is the descriptive question `thesis/chapters/04_research_questions_and_contributions.tex:50` explicitly disclaims.
It renders the thesis's aim as "noggrannhet och prestanda" (`:39`), where `04_research_questions_and_contributions.tex:47` says improving credibility "does not mean increasing numerical accuracy" and `08_conclusions_and_future_work.tex:9` says the improvement "is in definition traceability, not in numerical accuracy".
**Evidence:**

The Swedish abstract is the only description of the thesis a Swedish-reading examiner or opponent may read before the defence.
As written it describes a different thesis: descriptive rather than constructive, about accuracy rather than credibility, and without the device the thesis asks to be judged by.
The accuracy substitution is the exact conflation the background chapter warns against, so the abstract commits the error the thesis is written to correct.
This is a correctness defect, not a translation-quality defect, and it is fixable without touching the argument.

- `thesis/pre/sammanfattning.tex:33-41` is the whole Swedish abstract, 278 words.
- The contract is not named anywhere in it; the English abstract names it as the contribution.
- The six-paper compilation framing is absent.
- The application to the in-repo case and its clause verdicts are absent.
- `thesis/pre/sammanfattning.tex:39` states the question as how simulations affect credibility and complexity.
- `thesis/chapters/04_research_questions_and_contributions.tex:50` disclaims the descriptive question.
- `thesis/pre/sammanfattning.tex:39` uses "noggrannhet och prestanda"; `04_research_questions_and_contributions.tex:47` and `08_conclusions_and_future_work.tex:9` both deny that accuracy is the aim.
- R-012, the other front-matter gap: `thesis/pre/acknowledgments.tex:5-7` prints two bare headings, "Supervisors" and "Family", with no text under them.
- Review record `INFO-028`; audit: `.dynamic-harness/261101_082500_e339/review/prematter-check.md` findings 9 and 10, both MAJOR.
**Acceptance:**

- The Swedish abstract names the credibility contract and states it as the contribution.
- It states the six-paper compilation framing.
- It states the retrospective application and its result, or states that the contract was applied retrospectively without a number if `IMP-022` changes the instrument.
- It states the research question as the constructive question, not the descriptive one.
- It does not use "noggrannhet" as the aim; the Swedish term chosen for credibility is used consistently and matches the glossary's Swedish rendering if one exists.
- A Swedish-only reader can state what the thesis claims, what it contributes, and on what evidence, after reading only the abstract.
- The Swedish and English abstracts agree on every claim, checked sentence by sentence.
- R-012 is closed: both acknowledgment sections carry text, or the empty headings are removed.
**Out of scope:**

- The English abstract, except where the two must be made to agree.
- The terminology authority for "credibility" (`IMP-031`).
- Translation of the kappa's chapters.