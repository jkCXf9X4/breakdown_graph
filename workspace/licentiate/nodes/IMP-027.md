---
id: IMP-027
type: imp
layer: evolution
home: evolution/selected/derive-future-work-from-synthesis-gaps.md
title: Derive ch08's future work from ch07's gaps
summary: The synthesis promises three future-work items by cross-reference and the
  conclusions chapter contains none of them
date: 2026-11-04
status: selected
---

# Derive ch08's future work from ch07's gaps

`thesis/chapters/07_synthesis_and_discussion.tex:98` promises one future-work item by cross-reference to the conclusions chapter: applying Paper IV's architecture-driven workflow to the in-repo case (`IMP-039`).
`thesis/chapters/07_synthesis_and_discussion.tex:101` promises a second: validating the rubric with independent raters.
`IMP-017` records a third: attaching an intended-use block to the case's SSP.
`thesis/chapters/08_conclusions_and_future_work.tex:19-27` contains none of the three; it lists five items and has zero occurrences of rater or rubric.
`thesis/chapters/07_synthesis_and_discussion.tex:204` says the openings are what the conclusions chapter "turns into future work", and two of the five items have no antecedent there: closing the industry-academia gap (`08:26`) and linking definition provenance to recorded results (`08:25`).
`MS-008` requires future work to be "a prioritized plan toward the doctoral thesis"; the five items are unordered and the chapter never states an intended doctoral direction.
**Evidence:**

The cross-references are the thesis's own promise that the gaps it identifies become work, and the promise is broken in the direction an examiner is most likely to check.
A future-work list that is not derived from the identified gaps reads as filler, and two items with no antecedent read as borrowed from elsewhere.
The absence of an ordering and of a stated doctoral direction is the difference between a conclusions chapter and a list, and `MS-008` asks for the former.
The three promised items are also the ones that would most strengthen the thesis if done, so losing them costs the argument, not just the chapter.

- `thesis/chapters/07_synthesis_and_discussion.tex:98` promises the benchmark application by cross-reference.
- `thesis/chapters/07_synthesis_and_discussion.tex:101` promises independent-rater validation.
- `thesis/chapters/08_conclusions_and_future_work.tex` has zero hits for rater and rubric.
- `thesis/chapters/07_synthesis_and_discussion.tex:204` states that ch08 turns the openings into future work.
- `thesis/chapters/08_conclusions_and_future_work.tex:25` and `:26` list two items with no antecedent in ch07.
- `thesis/chapters/08_conclusions_and_future_work.tex:19` is the only framing sentence and never states a doctoral direction.
- `MS-008` requires a prioritized plan toward the doctoral thesis.
- Review record `INFO-028`; audit: `.dynamic-harness/261101_082500_e339/review/claims-synthesis.md` F-36, NOT-FOUND.
- Audit: `.dynamic-harness/261101_082500_e339/review/structure-back.md` S-12 and S-13.
**Acceptance:**

- Every future-work item in ch08 has an antecedent in ch07, named by section or line.
- The three promised items appear in ch08: Paper IV's workflow applied to the in-repo case, independent-rater validation of the rubric, and the intended-use block on that case's SSP.
- The items are ordered by dependency, and the ordering is stated as an ordering.
- The chapter states the intended doctoral direction in one sentence, and the ordering is a plan toward it.
- Any item retained without a ch07 antecedent states where it comes from.
- The cross-references at `07_synthesis_and_discussion.tex:98`, `:101` and `:204` resolve to the items they promise.
**Out of scope:**

- Performing any of the future work.
- The second rater itself (`IMP-017`).
- The contract's status as an instrument (`IMP-022`).