# ORQA Subset (source_category 1)

## Overview

This directory contains a deterministic 50-instance subset of the
**ORQA** benchmark dataset (Operations Research Question Answering).
These are real questions extracted from the published ORQA validation and
test sets -- **not** constructed/synthetic questions.

> **Important:** This is an internal re-split of published ORQA data for
> the skill-optimization project.  It is **NOT** the canonical ORQA test
> benchmark.  Results on this subset should not be compared directly with
> published ORQA leaderboard numbers.

## Source

> Evaluating LLM Reasoning in the Operations Research Domain with ORQA
> (AAAI 2025)

- Raw files: `ORQA_validation.jsonl` (45 instances) and
  `ORQA_test.jsonl` (1,468 instances)
- All instances have exactly 4 options and a single correct answer (A-D)
- `source_category: 1` in the canonical schema

## Sampling Protocol

The sampling is fully deterministic and reproducible via
`scripts/sample_orqa.py`.

### Seed split (5 instances, from validation set)

1. Group validation instances by `QUESTION_TYPE` (Q1-Q11).
2. Within each group, sort by `len(REASONING)` descending.  Ties are
   broken by file order (stable sort).
3. Iterate over types in sorted order (Q1, Q10, Q11, Q2, Q3);
   take the top-1 from each type until 5 are selected.

### Dev + Test splits (45 instances, from test set)

1. Stratified random sample of 45 from 1,468 test instances, proportional
   to each `QUESTION_TYPE`'s share.  Random seed = 42.
2. Per-type alternating assignment: within each type's sampled instances
   (sorted by original file index), the 1st goes to dev, the 2nd to test,
   the 3rd to dev, etc.
3. This guarantees every type with at least 1 sampled instance has
   representation in dev.

## Split Distribution

| Split | Count | Purpose                                    |
|-------|------:|---------------------------------------------|
| seed  |     5 | v0 skill generation examples only           |
| dev   |    25 | All conditions + error analysis + optimization |
| test  |    20 | Held-out final evaluation                   |
| TOTAL |    50 |                                             |

### Per QUESTION_TYPE breakdown

| QType | seed | dev | test | total |
|-------|-----:|----:|-----:|------:|
| Q1    |    1 |   2 |    1 |     4 |
| Q2    |    1 |   2 |    2 |     5 |
| Q3    |    1 |   2 |    2 |     5 |
| Q4    |    0 |   2 |    2 |     4 |
| Q5    |    0 |   3 |    2 |     5 |
| Q6    |    0 |   3 |    2 |     5 |
| Q7    |    0 |   1 |    0 |     1 |
| Q8    |    0 |   3 |    2 |     5 |
| Q9    |    0 |   3 |    3 |     6 |
| Q10   |    1 |   2 |    2 |     5 |
| Q11   |    1 |   2 |    2 |     5 |

## Files

- `questions.json` -- array of 50 question objects in canonical format
- `split.json` -- `{"seed": [...], "dev": [...], "test": [...]}` of question IDs
- `README.md` -- this file
