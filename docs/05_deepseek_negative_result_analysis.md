# DeepSeek Chat Negative Result Analysis

## Summary

On a 20-question held-out test split of ORQA, the archetype-prior curated skill (v1_curated) showed **no improvement** over the no-skill baseline. Gate 1 failed: the experiment does not support proceeding to autoresearch-style skill optimization with this model.

## Results (Test Set, 20 Questions)

| Condition | Accuracy | vs Baseline |
|-----------|:--------:|:-----------:|
| baseline | 80% (16/20) | — |
| generic_scaffold | 85% (17/20) | +1 question |
| v0_self_generated | 85% (17/20) | +1 question |
| v1_curated | 80% (16/20) | 0 |
| v2_optimized | 80% (16/20) | 0 |

## Gate 1 Evaluation

- **v1_curated > baseline?** No. 80% = 80%. Tied.
- **v1_curated > generic_scaffold?** No. 80% < 85%. Scaffold outperforms domain skill.
- **Gate 1 verdict: FAIL.**

## What the Data Shows

### The signal is extremely weak

The entire spread across 5 conditions is 80-85% — a difference of exactly 1 question on 20. At this sample size, 1 question = 5% accuracy. There is a very weak directional signal that structured prompting (scaffold or v0) may help, but **no evidence that domain-specific archetype content adds value beyond generic structure**.

More conservative statement: all 5 conditions perform comparably. The model already achieves 80% without any skill.

### Error pattern analysis

Of 20 test questions:
- **16 questions:** All 5 conditions get the same answer (all correct or all wrong)
- **1 question (orqa_0039):** Only scaffold and v0 correct; baseline, v1, v2 wrong
- **3 questions always wrong (orqa_0041, orqa_0047, orqa_0050):** All conditions fail

The universally-failed questions by subtype:

| Question | Subtype | What It Asks |
|----------|---------|-------------|
| orqa_0041 | Q4 | "What is the type of optimization model?" (model type classification) |
| orqa_0047 | Q8 | "Which data parameters participate in the objective?" (objective parameter identification) |
| orqa_0050 | Q9 | "Which decision activities participate in the objective?" (objective variable identification) |

### Leading hypothesis: why the archetype skill didn't help

The v1_curated skill was designed around a **top-down archetype matching** approach: identify the problem category (assignment, routing, scheduling, etc.) then instantiate a model skeleton. But the hard questions in ORQA are not about global archetype recognition — they're about **fine-grained component semantics**:

- Q4 (model type): Requires distinguishing LP vs MILP vs NLP based on subtle variable-type and linearity cues — not which archetype the problem matches
- Q8 (parameters in objective): Requires tracing which specific data constants appear as coefficients in the objective function — a local parsing task, not a global structural one
- Q9 (variables in objective): Same — which specific decision variables participate in the objective expression

**Best current interpretation:** the archetype-prior skill may be misaligned with ORQA's actual difficulty gradient. ORQA's hard questions appear to test "local component semantics" (which specific parameters/variables are in the objective, what type of model emerges from the variable types), more than "global archetype identification" (is this an assignment problem or a scheduling problem).

The generic scaffold and v0 skill may avoid this misalignment because they do not lean as heavily on domain-specific archetype priors; they mainly provide general structure.

### Why scaffold/v0 marginally helped on orqa_0039

orqa_0039 is a Q3 subtype ("Under which category does this problem fall?"). This IS an archetype-identification question. But scaffold and v0 helped where v1 didn't — possibly because the structured "analyze context → identify category" flow in the generic scaffold was sufficient for this question type, while v1's elaborate archetype library introduced noise or distracted the model.

## Implications

### For the research

1. **DeepSeek Chat may already be relatively strong on this split.** At 80% baseline on ORQA, there is limited headroom for skill injection to help. A weaker model may show more differentiation.

2. **Archetype-level priors may be the wrong abstraction for ORQA.** The benchmark's difficulty is concentrated at the component-semantics level (Q4, Q8, Q9), not the archetype level (Q3, Q6). A skill designed around component disambiguation (parameter vs variable, LP vs MILP cues) might be more effective.

3. **The scaffold control was valuable.** Without it, we might have attributed the marginal 85% to domain content. The current evidence is more consistent with structure helping slightly than with domain-specific content helping.

### For next steps

Per the spec's gating logic:
- Gate 1 failed → do NOT proceed to Step 4 (autoresearch) with DeepSeek
- Run the same experiment on a weaker model (Mistral Small 24B, in progress) to test if skill value emerges at lower baseline performance
- If a weaker model also shows no signal, consider a new skill design hypothesis targeting component-semantics rather than archetypes

## Reproducibility

- **Run ID:** 20260326_132128
- **Model:** deepseek-chat (DeepSeek API)
- **Data:** ORQA subset, internal 25-dev/20-test split
- **Primary report:** `docs/03_results_and_analysis.md`
- **Note:** run-scoped artifact paths are still being stabilized; use the run ID above as the primary provenance handle for now
