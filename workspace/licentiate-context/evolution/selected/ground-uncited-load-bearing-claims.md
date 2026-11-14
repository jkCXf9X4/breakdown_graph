---
id: IMP-034
type: imp
layer: evolution
home: evolution/selected/ground-uncited-load-bearing-claims.md
title: Ground the uncited load-bearing claims
summary: Thirty claims in ch02 and ch03 carry no citation, including the chapter's
  central conclusion
date: 2026-11-04
status: selected
---

# Ground the uncited load-bearing claims

The claim audit records 30 MISSING-CITATION findings in ch02 and ch03 alone.
Three of them are load-bearing.
`thesis/chapters/03_background.tex:91` says "a result that was valid for the previous configuration is not automatically valid for the current one"; this is the hinge from continuous development to the contract requirement, and it carries no citation.
`thesis/chapters/03_background.tex:137-138` says the contract is "necessary but insufficient"; this is the chapter's central conclusion, it carries zero citations, and the phrase appears in no library document.
`thesis/chapters/02_introduction.tex:7` pivots from model to decision with "is the result credible enough for this decision?", which is the thesis's motivating move and carries no citation.
`thesis/chapters/07_synthesis_and_discussion.tex:215` makes a strong negative existence claim about guidance that was tied to the dropped orchestration papers.
**Evidence:**

The three ch02-ch03 claims are the ones the argument stands on: without the first, continuous development does not imply a re-assessment requirement; without the second, the contract has no stated limit; without the third, the thesis has no motivation.
An uncited load-bearing claim is the easiest thing for an examiner to attack, because the attack needs no counter-argument, only the observation that nothing supports it.
The negative existence claim in ch07 is the most exposed of all: it asserts that a literature does not contain something, which requires either a search record or a citation to a survey that says so.
The library already holds sources that ground three of these, so the fix is mostly attaching citekeys that are already in the bibliography.

- 30 MISSING-CITATION findings in ch02 and ch03: `.dynamic-harness/261101_082500_e339/review/claims-intro-bg.md`.
- `thesis/chapters/03_background.tex:91` is uncited; groundable at `rosenlundObjectivelyDefinedIntended2024` text.md L260.
- `thesis/chapters/03_background.tex:137-138` has zero `\cite` commands and the phrase occurs in no library document; groundable from sources already cited at `03_background.tex:33` and `:39`.
- `thesis/chapters/02_introduction.tex:7` is uncited; groundable at `rosenlundObjectivelyDefinedIntended2024` text.md L9.
- `thesis/chapters/02_introduction.tex:19` is uncited; groundable at `ahmannContinuousSimulationCredibility2022` text.md L50-58.
- `thesis/chapters/02_introduction.tex:37` is uncited; groundable at `rosenlundObjectivelyDefinedIntended2024` L14.
- `thesis/chapters/03_background.tex:124` (zero-order-hold delay) groundable at `gomesCosimulationStateArt2017a` L925-926; phase shift at `rosenlundTemporalDecouplingWeakly2026` L46-47.
- `thesis/chapters/03_background.tex:127` (thread, process and machine allocation) is NOT-FOUND repo-wide.
- `thesis/chapters/07_synthesis_and_discussion.tex:215` is a negative existence claim with no citation, in a chapter with zero `\cite` commands.

- Review record `INFO-028`.

- `LIT-001` and `LIT-002` are the homes the grounded standard facts land in.
**Acceptance:**

- Each of the three load-bearing claims carries a citekey whose text contains the claim, or is weakened to what the thesis can support.
- The "necessary but insufficient" conclusion carries a citation, or is restated as the thesis's own finding with the reasoning that makes it one.
- The negative existence claim at `07_synthesis_and_discussion.tex:215` carries a citation to a source that states the absence, or is weakened to a claim about the sources the thesis examined.
- The thread/process/machine claim at `03_background.tex:127` is cited or removed.
- Every remaining MISSING-CITATION finding in ch02 and ch03 is either cited or recorded as deliberately uncited with a reason.
- No new citation is added whose library document does not contain the claim, per `OPS-004`.
**Out of scope:**

- The gap claim's two sentences (`IMP-020`).
- Citations in ch04 to ch09 beyond the one negative existence claim named here.
- Intaking new documents to support a claim (`IMP-016`).