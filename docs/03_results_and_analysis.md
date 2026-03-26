# Results and Analysis

## Overview

- **Run ID:** `20260326_024231`
- **Timestamp:** `2026-03-26 07:29:12`
- **Model:** `deepseek-chat`
- **Dataset label:** ORQA-derived evaluation set
- **Total questions:** 24 (seed: 4, dev: 10, test: 10)
- **Task types:** combinatorial_optimization, linear_programming
- **Conditions:** baseline, generic_scaffold, v0_self_generated, v1_curated, v2_optimized

## Development Set Results

> These results are used for error analysis and skill optimization.
> They are NOT the primary evidence for claims.

### Dev Accuracy Summary

| Condition | LP Accuracy | CO Accuracy | Overall |
|-----------|------------|------------|--------|
| baseline | 60% | 100% | 80% |
| generic_scaffold | 40% | 100% | 70% |
| v0_self_generated | 60% | 80% | 70% |
| v1_curated | 60% | 100% | 80% |
| v2_optimized | 60% | 80% | 70% |

### Dev Root Cause Distribution (Incorrect Answers Only)

| Root Cause | baseline | generic_scaffold | v0_self_generated | v1_curated | v2_optimized |
|-----------|----|----|----|----|----|
| task_misunderstood | — | — | — | — | — |
| constraint_missed | — | — | — | — | — |
| wrong_reasoning | — | 2 | — | — | — |
| calculation_error | 2 | 2 | 3 | 2 | — |
| skill_mismatch | — | — | — | — | — |
| skill_overfit | — | — | — | — | — |
| verbosity_overload | — | — | — | — | — |
| hallucinated_procedure | — | — | — | — | — |

## Held-Out Test Set Results

> **This is the primary evidence for all claims.**
> The optimizer never saw test set questions, answers, or failures.

### Test Accuracy Summary

| Condition | LP Accuracy | CO Accuracy | Overall |
|-----------|------------|------------|--------|
| baseline | 60% | 80% | 70% |
| generic_scaffold | 40% | 80% | 60% |
| v0_self_generated | 60% | 60% | 60% |
| v1_curated | 60% | 80% | 70% |
| v2_optimized | 40% | 80% | 60% |

### Paired Win/Loss vs Baseline (Test Set)

| Condition vs Baseline | Wins | Losses | Ties (correct) | Ties (wrong) | Net |
|----------------------|------|--------|----------------|-------------|-----|
| generic_scaffold | 0 | 1 | 6 | 3 | -1 |
| v0_self_generated | 0 | 1 | 6 | 3 | -1 |
| v1_curated | 0 | 0 | 7 | 3 | +0 |
| v2_optimized | 0 | 1 | 6 | 3 | -1 |


### v2_optimized vs v1_curated (Test Set)

| Comparison | Wins | Losses | Ties (correct) | Ties (wrong) |
|-----------|------|--------|----------------|-------------|
| v2 vs v1 | 0 | 1 | 6 | 3 |

### Dev-to-Test Gap (Descriptive Signal)

> At ~10 test questions, one question = ~10% swing. Treat as directional signal, not pass/fail.

| Condition | Dev Accuracy | Test Accuracy | Gap |
|-----------|-------------|--------------|-----|
| baseline | 80% | 70% | +10% |
| generic_scaffold | 70% | 60% | +10% |
| v0_self_generated | 70% | 60% | +10% |
| v1_curated | 80% | 70% | +10% |
| v2_optimized | 70% | 60% | +10% |

## Hypothesis Check

```
Expected: v2_optimized > v1_curated > generic_scaffold >= baseline >= v0_self_generated
Observed: baseline: 70%, v1_curated: 70%, generic_scaffold: 60%, v0_self_generated: 60%, v2_optimized: 60%
```

**Note:** These are directional findings from a small sample (~10 test questions). Statistical significance testing requires a larger dataset (Phase 2).

## Per-Question Test Results

| QID | Type | Baseline | Scaffold | v0 | v1 | v2 | Correct |
|-----|------|----------|----------|----|----|----|---------|
| orqa_co_008 | CO | A | A | A | A | A | A |
| orqa_co_009 | CO | B | B | — | B | B | B |
| orqa_co_010 | CO | B | B | B | B | B | B |
| orqa_co_011 | CO | — | ~~A~~ | — | — | — | C |
| orqa_co_012 | CO | A | A | A | A | A | A |
| orqa_lp_008 | LP | — | — | — | — | — | B |
| orqa_lp_009 | LP | A | — | A | A | — | A |
| orqa_lp_010 | LP | — | — | ~~C~~ | — | — | B |
| orqa_lp_011 | LP | B | B | B | B | B | B |
| orqa_lp_012 | LP | B | B | B | B | B | B |

## Skill Optimization Diff (v1 -> v2)

### Linear Programming

No changelog provided by the optimizer.

### Combinatorial Optimization

No changes — v1 was already perfect on dev set.


## Case Studies

### Failure: optimization_regressed (orqa_lp_009)

- Correct answer: A
- Baseline: A, v1: A, v2: None

