# ORQA Track A Results

**Date:** 2026-03-26  
**Run ID:** `track_a_stepfun_20260326`  
**Model:** `step-2-mini`  
**Scope:** StepFun-only Track A ablation (`baseline`, `generic_scaffold`, `v1_curated`, `v1_component_minimal`, `v1_component_enriched`)

## Why StepFun Only

Track A was run on `step-2-mini` only. This was deliberate, not an omission.

Phase 1 showed that DeepSeek had weak diagnostic value for this question. Its held-out test baseline was already high and the condition ordering was unstable across reruns, so additional Track A spend on DeepSeek was unlikely to clarify whether component-semantics content mattered. StepFun had lower baseline accuracy and larger skill sensitivity in Phase 1, so it was the more informative model for the first Track A pass.

## Primary Result: Held-Out Test

Held-out test remains the primary evidence.

| Condition | Accuracy | Correct/Total |
|-----------|:--------:|:-------------:|
| baseline | 55% | 11/20 |
| generic_scaffold | 60% | 12/20 |
| v1_curated | 65% | 13/20 |
| v1_component_minimal | 55% | 11/20 |
| v1_component_enriched | 65% | 13/20 |

### Direct Track A Comparisons

| Comparison | Wins | Losses | Net |
|-----------|:----:|:------:|:---:|
| `v1_component_minimal` vs `generic_scaffold` | 2 | 3 | -1 |
| `v1_component_enriched` vs `generic_scaffold` | 2 | 1 | +1 |
| `v1_component_minimal` vs `v1_curated` | 1 | 3 | -2 |
| `v1_component_enriched` vs `v1_curated` | 1 | 1 | 0 |

## Diagnostic Dev Result

Dev remains diagnostic only.

| Condition | Accuracy | Correct/Total |
|-----------|:--------:|:-------------:|
| baseline | 56% | 14/25 |
| generic_scaffold | 52% | 13/25 |
| v1_curated | 72% | 18/25 |
| v1_component_minimal | 64% | 16/25 |
| v1_component_enriched | 52% | 13/25 |

The dev pattern was already unfavorable for Track A:

- `v1_curated` remained the strongest condition.
- `v1_component_minimal` improved over baseline and scaffold, but did not catch `v1_curated`.
- `v1_component_enriched` collapsed to scaffold-level performance despite being the longest Track A variant.

## Decision Against Track A Hypothesis

Track A asked whether component-semantics skills outperform the archetype-prior skill and the generic scaffold on ORQA.

This run does **not** support that hypothesis.

- **A1 minimal:** failed clearly. It tied `baseline` at `55%`, underperformed `generic_scaffold` (`60%`), and underperformed `v1_curated` (`65%`).
- **A2 enriched:** partial but still negative. It matched `v1_curated` at `65%` and beat `generic_scaffold` by one question, but it did not exceed `v1_curated`, so it does not support the stronger Track A claim that component-semantics content is better aligned than the archetype skill.

The strongest defensible reading is:

> On `step-2-mini`, the enriched component-semantics skill can recover to the level of the archetype skill, but the minimal variant does not help, and neither variant establishes a clear improvement over the best existing curated condition.

## Per-Question Interpretation

The per-question table shows a mixed story rather than a clean semantic-alignment win.

- `v1_component_enriched` fixed `orqa_0041` (`Q4`, model type classification), where `baseline`, `generic_scaffold`, `v1_curated`, and `v1_component_minimal` all failed.
- But `v1_component_enriched` also **lost** `orqa_0046` (`Q8`), where `v1_curated` was correct and A2 was wrong.
- `v1_component_minimal` got `orqa_0039` (`Q3`) and `orqa_0045` (`Q6`) right where baseline was wrong, but it regressed on `orqa_0035` (`Q11`) and `orqa_0048` (`Q9`), which erased the gain.
- Neither A1 nor A2 solved the persistent hard cases `orqa_0047` and `orqa_0050`.

So the Track A content did not produce a stable “fix the hard component-semantics questions” pattern. It changed which questions were won and lost, but not in a direction strong enough to beat `v1_curated`.

## Dev Error Analysis Signal

The dev root-cause distribution also points away from a clean Track A win:

- `v1_curated` reduced `wrong_reasoning` counts relative to `baseline` and `generic_scaffold`.
- `v1_component_minimal` sat between `baseline` and `v1_curated`, which is directionally reasonable but not enough.
- `v1_component_enriched` showed the worst `skill_overfit` count in the run (`10`) and did not reduce `wrong_reasoning` relative to baseline.

This matters because A2 was meant to be the richer, more targeted semantics skill. Instead, the additional content appears to have increased prompt burden without creating a cleaner reasoning profile.

## Conclusion

Track A on StepFun is a **negative or at best flat result** for the component-semantics hypothesis.

What we can say:

- prompt structure alone still does not explain the best performance, because `v1_curated`/A2 are above `baseline`
- A1 minimal does not help on held-out test
- A2 enriched can tie the archetype skill, but does not beat it
- there is no evidence here that component-semantics content is decisively better aligned to ORQA than the archetype-prior skill

What we should not say:

- that Track A confirms the component-semantics hypothesis
- that richer semantics content reliably improves StepFun on ORQA
- that DeepSeek is required to interpret this result; this StepFun run is already informative

## Artifact References

All numbers above were copied from:

- `results/runs/track_a_stepfun_20260326/evaluations/dev/*.json`
- `results/runs/track_a_stepfun_20260326/evaluations/test/*.json`
- `results/runs/track_a_stepfun_20260326/analysis/dev_error_analysis.json`
- `results/runs/track_a_stepfun_20260326/track_a_report.md`
