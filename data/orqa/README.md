# ORQA-Derived Evaluation Set

## Dataset Label

**ORQA-derived evaluation set** — all questions are constructed (source_category: 3), not extracted from the original ORQA benchmark dataset.

## Source

Questions are inspired by the operations research problem types described in:

> "Evaluating LLM Reasoning in the Operations Research Domain with ORQA" (AAAI 2025)

The ORQA dataset was not directly downloadable at the time of data collection. Per the manual curation protocol in the spec, all questions are constructed to match the described problem types and difficulty distribution.

## Composition

- **Total questions:** 24
- **Task types:** linear_programming (12), combinatorial_optimization (12)

### Split Distribution

| Split | LP | CO | Total | Purpose |
|-------|----|----|-------|---------|
| seed  | 2  | 2  | 4     | v0 skill generation examples only |
| dev   | 5  | 5  | 10    | All conditions + error analysis + optimization |
| test  | 5  | 5  | 10    | Held-out final evaluation |

### LP Problem Types

Resource allocation, production planning, transportation, diet/blending, advertising mix

### CO Problem Types

Knapsack (0/1), assignment, shortest path, scheduling, minimum spanning tree, TSP, critical path, capital budgeting

## Methodology

- All questions are source_category 3 (constructed)
- Questions target undergraduate/graduate OR course level
- Each question has exactly 4 multiple-choice options (A/B/C/D)
- Split assignment is fixed in `split.json` and never modified after initial creation
- Seed questions are disjoint from dev and test — used only for v0 skill generation
