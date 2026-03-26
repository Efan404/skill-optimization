# StepFun Interim Result Memo

## Status

This memo records an **in-progress Phase 1 StepFun run** and should not be treated as the final experiment report.

- **Run ID:** `20260326_154918`
- **Model:** `step_2_mini`
- **Git commit:** `e1f10dcd427da29a587b3f48e09c98f436c44172`
- **Dataset:** ORQA subset (`seed=5`, `dev=25`, `test=20`)
- **Pipeline note:** the run uses graceful optimizer fallback, so if YAML parsing fails, `v2_optimized` falls back to `v1_curated` and the pipeline continues to held-out test.

At the time of writing, the run metadata has been written, but the full evaluation artifacts for held-out test have not yet been finalized in the run directory. The conclusions below are therefore restricted to the currently observed **development-set signal**.

## Interim Development Results

The active StepFun run has shown the following dev summary so far:

| Condition | DeepSeek Dev | StepFun Dev |
|-----------|:------------:|:-----------:|
| baseline | 80% | 56% |
| generic_scaffold | 76% | 56% |
| v0_self_generated | 84% | 64% |
| v1_curated | 84% | 80% |

## Provisional Interpretation

This is a materially different pattern from the DeepSeek run.

On DeepSeek, the archetype-oriented curated skill was close to the other conditions, and the overall spread was small. On StepFun, the current dev signal suggests a much larger separation:

- `v1_curated` is substantially above `baseline`
- `generic_scaffold` does not appear to improve over `baseline`
- `v0_self_generated` helps somewhat, but less than `v1_curated`

If this pattern survives on the held-out test split, the main Phase 1 story changes from a simple negative result to a **model sensitivity result**:

> The value of a domain-specific skill may depend strongly on the underlying model.  
> DeepSeek showed little measurable benefit from the archetype skill, while StepFun appears substantially more responsive to it.

However, that conclusion is **not yet established**. The current evidence comes from the dev split only, and dev evidence is vulnerable to overinterpretation.

## What Can Already Be Said

Three claims are reasonable at this stage:

1. **StepFun appears weaker than DeepSeek on the ORQA dev split without skill support.**  
   The current baseline contrast is `56%` vs `80%`.

2. **Generic prompt structure alone does not explain the current StepFun gain.**  
   On the current dev numbers, `generic_scaffold` stays at baseline while `v1_curated` rises substantially above it.

3. **StepFun is a strong candidate model for Phase 2 skill studies.**  
   Even if the final held-out gain shrinks, the dev-stage separation suggests this model is more diagnostic than DeepSeek for testing whether skill content matters.

## What Cannot Yet Be Claimed

The following would be premature until the held-out test finishes:

- Gate 1 PASS on StepFun
- A confirmed positive result for the archetype skill
- Any claim that the optimizer improved over `v1_curated`
- Any final multi-model conclusion about skill usefulness

The `v2_optimized` condition in particular should be treated cautiously in this run, because graceful fallback preserves pipeline continuity but weakens interpretability if optimization fails and reuses `v1_curated`.

## Reporting Recommendation

The main report should **not** be rewritten yet. Instead:

1. Keep the current DeepSeek writeup as the completed Phase 1 result on one model.
2. Treat this StepFun memo as an interim addendum.
3. Wait for the held-out StepFun test artifacts before deciding whether the final Phase 1 narrative is:
   - `DeepSeek negative result + StepFun positive result`
   - `DeepSeek negative result + StepFun dev-only signal`
   - `mixed evidence requiring Phase 2 follow-up`

## Decision Rule After Test Completes

Once the held-out StepFun test finishes, the next action should be determined by the following rule:

- If `v1_curated > baseline` and `v1_curated > generic_scaffold` on test:
  StepFun provides a Phase 1 positive result, and the project should emphasize **model sensitivity** in the cross-model narrative.
- If the dev gain collapses on test:
  treat the StepFun run as a useful warning about dev overfitting or instability, not as a confirmed positive result.

In both cases, the next best Phase 2 experiment remains the same: test whether a **component-semantics** skill aligns better with ORQA's real difficulty than the archetype-oriented skill.

## Immediate Next Steps

1. Let the current StepFun run finish and record the held-out test table.
2. Merge the Track A skill variants (`component_minimal`, `component_enriched`).
3. Run Track A on StepFun first, because StepFun currently shows the clearest skill sensitivity.
4. Run the same Track A conditions on DeepSeek for comparison.
5. Write a final multi-model, multi-skill comparison after both the StepFun test and Track A ablations are complete.
