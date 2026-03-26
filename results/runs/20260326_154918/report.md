<!-- AUTO-GENERATED from run 20260326_154918; DO NOT EDIT BY HAND -->

# Results and Analysis

## Overview

- **Run ID:** `20260326_154918`
- **Timestamp:** `2026-03-26 16:32:23`
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
| baseline | 56% | 56% |
| generic_scaffold | 52% | 52% |
| v0_self_generated | 60% | 60% |
| v1_curated | 84% | 84% |
| v2_optimized | 0% | 0% |

### Dev Root Cause Distribution (Incorrect Answers Only)

| Root Cause | baseline | generic_scaffold | v0_self_generated | v1_curated | v2_optimized |
|-----------|----|----|----|----|----|
| task_misunderstood | 2 | 4 | 7 | — | — |
| constraint_missed | 3 | 3 | 1 | — | — |
| wrong_reasoning | 11 | 9 | 2 | 1 | — |
| calculation_error | — | — | — | — | — |
| skill_mismatch | — | — | 1 | — | — |
| skill_overfit | 4 | 8 | 7 | 4 | — |
| verbosity_overload | — | — | — | — | — |
| hallucinated_procedure | — | — | — | 3 | — |

## Held-Out Test Set Results

> **This is the primary evidence for all claims.**
> The optimizer never saw test set questions, answers, or failures.

### Test Accuracy Summary

| Condition | or_model_identification | Overall |
|-----------|----------|--------|
| baseline | 0% | 0% |
| generic_scaffold | 0% | 0% |
| v0_self_generated | 0% | 0% |
| v1_curated | 0% | 0% |
| v2_optimized | 0% | 0% |

### Paired Win/Loss vs Baseline (Test Set)

| Condition vs Baseline | Wins | Losses | Ties (correct) | Ties (wrong) | Net |
|----------------------|------|--------|----------------|-------------|-----|
| generic_scaffold | 0 | 0 | 0 | 20 | +0 |
| v0_self_generated | 0 | 0 | 0 | 20 | +0 |
| v1_curated | 0 | 0 | 0 | 20 | +0 |
| v2_optimized | 0 | 0 | 0 | 20 | +0 |


### v2_optimized vs v1_curated (Test Set)

| Comparison | Wins | Losses | Ties (correct) | Ties (wrong) |
|-----------|------|--------|----------------|-------------|
| v2 vs v1 | 0 | 0 | 0 | 20 |

### Dev-to-Test Gap (Descriptive Signal)

> At ~10 test questions, one question = ~10% swing. Treat as directional signal, not pass/fail.

| Condition | Dev Accuracy | Test Accuracy | Gap |
|-----------|-------------|--------------|-----|
| baseline | 56% | 0% | +56% |
| generic_scaffold | 52% | 0% | +52% |
| v0_self_generated | 60% | 0% | +60% |
| v1_curated | 84% | 0% | +84% |
| v2_optimized | 0% | 0% | +0% |

## Hypothesis Check

```
Expected: v2_optimized > v1_curated > generic_scaffold >= baseline >= v0_self_generated
Observed: baseline: 0%, generic_scaffold: 0%, v0_self_generated: 0%, v1_curated: 0%, v2_optimized: 0%
```

**Note:** These are directional findings from a small sample (~20 test questions). Statistical significance testing requires a larger dataset (Phase 2).

## Per-Question Test Results

| QID | Type | Baseline | Scaffold | v0 | v1 | v2 | Correct | vs_base(scaffold) | vs_base(v0) | vs_base(v1) | vs_base(v2) |
|-----|------|----------|----------|----|----|----|---------|--------------------|-------------|-------------|-------------|
| orqa_0031 | or_model_identification | — | — | — | — | — | D | =fail | =fail | =fail | =fail |
| orqa_0032 | or_model_identification | — | — | — | — | — | C | =fail | =fail | =fail | =fail |
| orqa_0033 | or_model_identification | — | — | — | — | — | D | =fail | =fail | =fail | =fail |
| orqa_0034 | or_model_identification | — | — | — | — | — | B | =fail | =fail | =fail | =fail |
| orqa_0035 | or_model_identification | — | — | — | — | — | A | =fail | =fail | =fail | =fail |
| orqa_0036 | or_model_identification | — | — | — | — | — | A | =fail | =fail | =fail | =fail |
| orqa_0037 | or_model_identification | — | — | — | — | — | D | =fail | =fail | =fail | =fail |
| orqa_0038 | or_model_identification | — | — | — | — | — | B | =fail | =fail | =fail | =fail |
| orqa_0039 | or_model_identification | — | — | — | — | — | D | =fail | =fail | =fail | =fail |
| orqa_0040 | or_model_identification | — | — | — | — | — | A | =fail | =fail | =fail | =fail |
| orqa_0041 | or_model_identification | — | — | — | — | — | A | =fail | =fail | =fail | =fail |
| orqa_0042 | or_model_identification | — | — | — | — | — | A | =fail | =fail | =fail | =fail |
| orqa_0043 | or_model_identification | — | — | — | — | — | A | =fail | =fail | =fail | =fail |
| orqa_0044 | or_model_identification | — | — | — | — | — | B | =fail | =fail | =fail | =fail |
| orqa_0045 | or_model_identification | — | — | — | — | — | C | =fail | =fail | =fail | =fail |
| orqa_0046 | or_model_identification | — | — | — | — | — | B | =fail | =fail | =fail | =fail |
| orqa_0047 | or_model_identification | — | — | — | — | — | B | =fail | =fail | =fail | =fail |
| orqa_0048 | or_model_identification | — | — | — | — | — | B | =fail | =fail | =fail | =fail |
| orqa_0049 | or_model_identification | — | — | — | — | — | D | =fail | =fail | =fail | =fail |
| orqa_0050 | or_model_identification | — | — | — | — | — | D | =fail | =fail | =fail | =fail |

## Skill Optimization Diff (v1 -> v2)

### Or Model Identification

Optimization failed (Connection error.); v2 = v1 copy.


## Case Studies

*No notable case studies identified.*
