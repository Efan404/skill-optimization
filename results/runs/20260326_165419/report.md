<!-- AUTO-GENERATED from run 20260326_165419; DO NOT EDIT BY HAND -->

# Results and Analysis

## Overview

- **Run ID:** `20260326_165419`
- **Timestamp:** `2026-03-26 17:31:47`
- **Model:** `step-2-mini`
- **Dataset label:** ORQA subset
- **Total questions:** 50 (seed: 5, dev: 25, test: 20)
- **Task types:** or_model_identification
- **Conditions:** baseline, generic_scaffold, v0_self_generated, v1_curated, v2_optimized

## Development Set Results

> These results are used for error analysis and skill optimization.
> They are NOT the primary evidence for claims.

### Dev Accuracy Summary

| Condition | or_model_identification | Overall |
|-----------|----------|--------|
| baseline | 60% | 60% |
| generic_scaffold | 64% | 64% |
| v0_self_generated | 60% | 60% |
| v1_curated | 68% | 68% |
| v2_optimized | 64% | 64% |

### Dev Root Cause Distribution (Incorrect Answers Only)

| Root Cause | baseline | generic_scaffold | v0_self_generated | v1_curated | v2_optimized |
|-----------|----|----|----|----|----|
| task_misunderstood | 1 | 4 | 4 | — | — |
| constraint_missed | 3 | 1 | — | — | — |
| wrong_reasoning | 10 | 8 | 6 | 3 | — |
| calculation_error | — | — | — | — | — |
| skill_mismatch | — | — | — | 1 | — |
| skill_overfit | 5 | 5 | 6 | 7 | — |
| verbosity_overload | — | — | — | — | — |
| hallucinated_procedure | — | — | — | 5 | — |

## Held-Out Test Set Results

> **This is the primary evidence for all claims.**
> The optimizer never saw test set questions, answers, or failures.

### Test Accuracy Summary

| Condition | or_model_identification | Overall |
|-----------|----------|--------|
| baseline | 55% | 55% |
| generic_scaffold | 60% | 60% |
| v0_self_generated | 55% | 55% |
| v1_curated | 60% | 60% |
| v2_optimized | 55% | 55% |

### Paired Win/Loss vs Baseline (Test Set)

| Condition vs Baseline | Wins | Losses | Ties (correct) | Ties (wrong) | Net |
|----------------------|------|--------|----------------|-------------|-----|
| generic_scaffold | 1 | 0 | 11 | 8 | +1 |
| v0_self_generated | 4 | 4 | 7 | 5 | +0 |
| v1_curated | 1 | 0 | 11 | 8 | +1 |
| v2_optimized | 1 | 1 | 10 | 8 | +0 |


### v2_optimized vs v1_curated (Test Set)

| Comparison | Wins | Losses | Ties (correct) | Ties (wrong) |
|-----------|------|--------|----------------|-------------|
| v2 vs v1 | 0 | 1 | 11 | 8 |

### Dev-to-Test Gap (Descriptive Signal)

> At ~10 test questions, one question = ~10% swing. Treat as directional signal, not pass/fail.

| Condition | Dev Accuracy | Test Accuracy | Gap |
|-----------|-------------|--------------|-----|
| baseline | 60% | 55% | +5% |
| generic_scaffold | 64% | 60% | +4% |
| v0_self_generated | 60% | 55% | +5% |
| v1_curated | 68% | 60% | +8% |
| v2_optimized | 64% | 55% | +9% |

## Hypothesis Check

```
Expected: v2_optimized > v1_curated > generic_scaffold >= baseline >= v0_self_generated
Observed: generic_scaffold: 60%, v1_curated: 60%, baseline: 55%, v0_self_generated: 55%, v2_optimized: 55%
```

**Note:** These are directional findings from a small sample (~20 test questions). Statistical significance testing requires a larger dataset (Phase 2).

## Per-Question Test Results

| QID | Type | Baseline | Scaffold | v0 | v1 | v2 | Correct | vs_base(scaffold) | vs_base(v0) | vs_base(v1) | vs_base(v2) |
|-----|------|----------|----------|----|----|----|---------|--------------------|-------------|-------------|-------------|
| orqa_0031 | or_model_identification | D | D | D | D | D | D | =ok | =ok | =ok | =ok |
| orqa_0032 | or_model_identification | ~~A~~ | ~~A~~ | C | ~~A~~ | ~~A~~ | C | =fail | + | =fail | =fail |
| orqa_0033 | or_model_identification | ~~C~~ | D | ~~C~~ | ~~C~~ | ~~C~~ | D | + | =fail | =fail | =fail |
| orqa_0034 | or_model_identification | B | B | B | B | B | B | =ok | =ok | =ok | =ok |
| orqa_0035 | or_model_identification | A | A | A | A | A | A | =ok | =ok | =ok | =ok |
| orqa_0036 | or_model_identification | A | A | A | A | A | A | =ok | =ok | =ok | =ok |
| orqa_0037 | or_model_identification | D | D | D | D | D | D | =ok | =ok | =ok | =ok |
| orqa_0038 | or_model_identification | B | B | B | B | B | B | =ok | =ok | =ok | =ok |
| orqa_0039 | or_model_identification | ~~B~~ | ~~B~~ | D | ~~B~~ | ~~B~~ | D | =fail | + | =fail | =fail |
| orqa_0040 | or_model_identification | A | A | — | A | A | A | =ok | - | =ok | =ok |
| orqa_0041 | or_model_identification | ~~C~~ | ~~C~~ | A | ~~C~~ | ~~C~~ | A | =fail | + | =fail | =fail |
| orqa_0042 | or_model_identification | A | A | — | A | A | A | =ok | - | =ok | =ok |
| orqa_0043 | or_model_identification | A | A | — | A | A | A | =ok | - | =ok | =ok |
| orqa_0044 | or_model_identification | B | B | B | B | B | B | =ok | =ok | =ok | =ok |
| orqa_0045 | or_model_identification | ~~B~~ | ~~B~~ | C | C | C | C | =fail | + | + | + |
| orqa_0046 | or_model_identification | ~~C~~ | ~~C~~ | ~~C~~ | ~~C~~ | ~~C~~ | B | =fail | =fail | =fail | =fail |
| orqa_0047 | or_model_identification | ~~D~~ | ~~D~~ | ~~D~~ | ~~D~~ | ~~D~~ | B | =fail | =fail | =fail | =fail |
| orqa_0048 | or_model_identification | B | B | ~~D~~ | B | ~~D~~ | B | =ok | - | =ok | - |
| orqa_0049 | or_model_identification | ~~A~~ | ~~B~~ | ~~B~~ | ~~B~~ | ~~A~~ | D | =fail | =fail | =fail | =fail |
| orqa_0050 | or_model_identification | ~~A~~ | ~~A~~ | ~~A~~ | ~~A~~ | ~~A~~ | D | =fail | =fail | =fail | =fail |

## Skill Optimization Diff (v1 -> v2)

### Or Model Identification

- Updated the procedure to emphasize the importance of directly textual evidence for each model component, addressing common failures related to overfitting and hallucinated procedures.
- Clarified the preconditions and when_to_use sections to better guide the user on the appropriate use cases for the skill.
- Added specific examples to the common_failures section to illustrate common pitfalls and how to avoid them.
- Revised the verification step to provide a more detailed checklist for ensuring the accuracy of the identified model components.


## Case Studies

### Success: skill_helped (orqa_0045)

- Correct answer: C
- Baseline: B, v1: C, v2: C

### Failure: optimization_regressed (orqa_0048)

- Correct answer: B
- Baseline: B, v1: B, v2: D

