# Results and Analysis

## Overview

- **Run ID:** `20260326_135533`
- **Timestamp:** `2026-03-26 14:25:43`
- **Model:** `deepseek-chat`
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
| baseline | 80% | 80% |
| generic_scaffold | 80% | 80% |
| v0_self_generated | 84% | 84% |
| v1_curated | 88% | 88% |
| v2_optimized | 80% | 80% |

### Dev Root Cause Distribution (Incorrect Answers Only)

| Root Cause | baseline | generic_scaffold | v0_self_generated | v1_curated | v2_optimized |
|-----------|----|----|----|----|----|
| task_misunderstood | 5 | 5 | 2 | 3 | — |
| constraint_missed | — | — | — | — | — |
| wrong_reasoning | 4 | 2 | 4 | 2 | — |
| calculation_error | — | — | — | — | — |
| skill_mismatch | — | — | — | — | — |
| skill_overfit | — | — | 2 | — | — |
| verbosity_overload | — | — | — | — | — |
| hallucinated_procedure | — | — | — | — | — |

## Held-Out Test Set Results

> **This is the primary evidence for all claims.**
> The optimizer never saw test set questions, answers, or failures.

### Test Accuracy Summary

| Condition | or_model_identification | Overall |
|-----------|----------|--------|
| baseline | 80% | 80% |
| generic_scaffold | 75% | 75% |
| v0_self_generated | 85% | 85% |
| v1_curated | 85% | 85% |
| v2_optimized | 85% | 85% |

### Paired Win/Loss vs Baseline (Test Set)

| Condition vs Baseline | Wins | Losses | Ties (correct) | Ties (wrong) | Net |
|----------------------|------|--------|----------------|-------------|-----|
| generic_scaffold | 0 | 1 | 15 | 4 | -1 |
| v0_self_generated | 1 | 0 | 16 | 3 | +1 |
| v1_curated | 1 | 0 | 16 | 3 | +1 |
| v2_optimized | 1 | 0 | 16 | 3 | +1 |


### v2_optimized vs v1_curated (Test Set)

| Comparison | Wins | Losses | Ties (correct) | Ties (wrong) |
|-----------|------|--------|----------------|-------------|
| v2 vs v1 | 0 | 0 | 17 | 3 |

### Dev-to-Test Gap (Descriptive Signal)

> At ~10 test questions, one question = ~10% swing. Treat as directional signal, not pass/fail.

| Condition | Dev Accuracy | Test Accuracy | Gap |
|-----------|-------------|--------------|-----|
| baseline | 80% | 80% | +0% |
| generic_scaffold | 80% | 75% | +5% |
| v0_self_generated | 84% | 85% | -1% |
| v1_curated | 88% | 85% | +3% |
| v2_optimized | 80% | 85% | -5% |

## Hypothesis Check

```
Expected: v2_optimized > v1_curated > generic_scaffold >= baseline >= v0_self_generated
Observed: v0_self_generated: 85%, v1_curated: 85%, v2_optimized: 85%, baseline: 80%, generic_scaffold: 75%
```

**Note:** These are directional findings from a small sample (~20 test questions). Statistical significance testing requires a larger dataset (Phase 2).

## Per-Question Test Results

| QID | Type | Baseline | Scaffold | v0 | v1 | v2 | Correct | vs_base(scaffold) | vs_base(v0) | vs_base(v1) | vs_base(v2) |
|-----|------|----------|----------|----|----|----|---------|--------------------|-------------|-------------|-------------|
| orqa_0031 | or_model_identification | D | D | D | D | D | D | =ok | =ok | =ok | =ok |
| orqa_0032 | or_model_identification | C | ~~A~~ | C | C | C | C | - | =ok | =ok | =ok |
| orqa_0033 | or_model_identification | D | D | D | D | D | D | =ok | =ok | =ok | =ok |
| orqa_0034 | or_model_identification | B | B | B | B | B | B | =ok | =ok | =ok | =ok |
| orqa_0035 | or_model_identification | A | A | A | A | A | A | =ok | =ok | =ok | =ok |
| orqa_0036 | or_model_identification | A | A | A | A | A | A | =ok | =ok | =ok | =ok |
| orqa_0037 | or_model_identification | D | D | D | D | D | D | =ok | =ok | =ok | =ok |
| orqa_0038 | or_model_identification | B | B | B | B | B | B | =ok | =ok | =ok | =ok |
| orqa_0039 | or_model_identification | D | D | D | D | D | D | =ok | =ok | =ok | =ok |
| orqa_0040 | or_model_identification | A | A | A | A | A | A | =ok | =ok | =ok | =ok |
| orqa_0041 | or_model_identification | ~~D~~ | ~~C~~ | ~~C~~ | ~~C~~ | ~~C~~ | A | =fail | =fail | =fail | =fail |
| orqa_0042 | or_model_identification | A | A | A | A | A | A | =ok | =ok | =ok | =ok |
| orqa_0043 | or_model_identification | A | A | A | A | A | A | =ok | =ok | =ok | =ok |
| orqa_0044 | or_model_identification | B | B | B | B | B | B | =ok | =ok | =ok | =ok |
| orqa_0045 | or_model_identification | C | C | C | C | C | C | =ok | =ok | =ok | =ok |
| orqa_0046 | or_model_identification | ~~C~~ | ~~C~~ | B | B | B | B | =fail | + | + | + |
| orqa_0047 | or_model_identification | ~~D~~ | ~~D~~ | ~~D~~ | ~~D~~ | ~~D~~ | B | =fail | =fail | =fail | =fail |
| orqa_0048 | or_model_identification | B | B | B | B | B | B | =ok | =ok | =ok | =ok |
| orqa_0049 | or_model_identification | D | D | D | D | D | D | =ok | =ok | =ok | =ok |
| orqa_0050 | or_model_identification | ~~A~~ | ~~A~~ | ~~A~~ | ~~A~~ | ~~A~~ | D | =fail | =fail | =fail | =fail |

## Skill Optimization Diff (v1 -> v2)

### Or Model Identification

No changelog provided by the optimizer.


## Case Studies

### Success: skill_helped (orqa_0046)

- Correct answer: B
- Baseline: C, v1: B, v2: B

