# Phase 2: Skill-Difficulty Alignment and Model Sensitivity

**Status:** superseded as the **primary research narrative** by [2026-03-26-skillsbench-protocol-strength-research-spec.md](/Users/efan404/Codes/research/skill-optimization/docs/superpowers/specs/2026-03-26-skillsbench-protocol-strength-research-spec.md).

This document is still useful as an ORQA-centered ablation spec. It should now be read as an `ORQA workstream / methodology-extension` document, not as the top-level research framing for the project.

## Research Question

**Do skills need to be aligned with a benchmark's actual difficulty gradient, and is this alignment modulated by model capability?**

This question arises directly from Phase 1's key finding: the archetype-prior skill failed Gate 1 on DeepSeek because it targeted global archetype identification, while ORQA's hard questions test local component semantics (Q4 model type, Q8 objective parameters, Q9 objective variables). Phase 2 tests whether a skill aligned to the real difficulty gradient produces a different outcome.

## Relationship to Phase 1

Phase 1 established:
- A complete skill optimization pipeline with 5-condition controlled design
- Scaffold control isolating domain content from prompt structure
- Dev/test split preventing train-on-test
- **DeepSeek result:** baseline=80%, all conditions within 80-85%. Gate 1 FAIL.
- **Error analysis:** archetype priors misaligned with ORQA's difficulty (Q4/Q8/Q9 component-semantics questions are the hard ones, not Q3/Q6 archetype questions)
- **StepFun result:** pending (Phase 1 收尾)

Phase 2 does NOT replace Phase 1. It builds on Phase 1's negative result as a new hypothesis test.

---

## Track A: Component-Semantics Skill Ablation (PRIMARY)

### Hypothesis

A skill targeting ORQA's actual difficulty gradient (component-level disambiguation) will outperform both the archetype-prior skill (v1_curated) and the generic scaffold, because it addresses the specific failure modes identified in Phase 1.

### Design: Two Skill Variants

**A1: Minimal Component-Semantics Skill**

Focuses narrowly on the three hardest question families:
- **Parameter vs Variable disambiguation:** "Is this quantity given (parameter) or chosen (variable)?" with concrete cues: "you know the cost" → parameter, "you decide how many" → variable
- **Objective participant identification:** "Which variables/parameters appear in the objective expression?" Procedure: find the goal sentence, trace which quantities it depends on
- **Model type classification cues:** continuous variables + linear functions → LP; any integer/binary → MILP; variable products → NLP

Same external structure as v1 (4 stages, matching scaffold), but Layer 2 content is component-semantics instead of archetypes. **Deliberately shorter/simpler than v1** to test whether targeted content outperforms comprehensive content.

**A2: Enriched Component-Semantics Skill**

Builds on A1 by adding:
- **Constraint-side semantics:** LHS meaning (what is summed over which index), RHS (what bound), applied-on (which set element)
- **Set vs parameter vs variable disambiguation:** sets are collections you iterate over, not individual values
- **Local disambiguation rules** (high-confidence only):
  - "assign X to Y" → binary variable, not parameter
  - "capacity of" / "demand of" → parameter, not variable
  - "for each" / "for all" → indicates a set index
  - "at most K" / "exactly K" → cardinality constraint, suggests integer variables

**Approximately same token length as v1** to control for length. The question being tested: is it the *type* of domain content that matters, or just the *amount*?

### What This Ablation Answers

| Comparison | What It Tests |
|------------|--------------|
| A1 vs scaffold | Does targeted component-semantics content help beyond generic structure? |
| A2 vs scaffold | Does richer component-semantics content help? |
| A1 vs A2 | Does adding more content help, or does the minimal version suffice? |
| A1 vs v1_archetype | Is component-semantics better than archetype-prior? |
| A2 vs v1_archetype | Same comparison with length-matched variant |
| All of the above across models | Is the pattern model-dependent? |

### Implementation

**No pipeline changes needed.** Only new skill YAML files:
- `skills/orqa/v1_component_minimal/or_model_identification.yaml` (A1)
- `skills/orqa/v1_component_enriched/or_model_identification.yaml` (A2)

**Pipeline runs required:**
1. DeepSeek with A1 skill (reuse existing scaffold and baseline from Phase 1)
2. DeepSeek with A2 skill
3. StepFun step-2-mini with A1 and A2 (if StepFun shows different baseline from DeepSeek)

**Scaffold:** Same generic scaffold as Phase 1. A1 must match scaffold step count; A2 must match scaffold token count (+/-15%).

### Experimental Conditions (per run)

| Condition | Skill |
|-----------|-------|
| baseline | None (reuse Phase 1 result if same model) |
| generic_scaffold | Same scaffold (reuse Phase 1 result) |
| v1_archetype | Phase 1's archetype skill (reuse result) |
| v1_component_minimal | A1 new skill |
| v1_component_enriched | A2 new skill |

Note: This is 5 conditions but different from Phase 1's 5. We drop v0_self_generated and v2_optimized, and add A1 and A2. The comparison that matters is: component skills vs archetype skill vs scaffold.

### Gate Criteria

**Track A signal confirmed if ANY of:**
- A1 or A2 test accuracy > baseline AND > scaffold (same model)
- A1 or A2 shows different error pattern than v1_archetype on the hard questions (Q4/Q8/Q9)
- Cross-model comparison shows consistent direction (e.g., A1 helps on weaker model even if flat on DeepSeek)

**Track A negative result if:**
- A1 ≈ A2 ≈ v1_archetype ≈ scaffold ≈ baseline on all models
- Conclusion: skill content type doesn't matter for ORQA with these models; the benchmark may be too easy or the task may not benefit from procedural prompting

---

## Track B: SkillsBench Modality Extension (SECONDARY, gated)

### Gate to Enter Track B

At least ONE of:
- Track A produces a clear positive or clearly-explained negative result
- Phase 1 + Track A together establish a complete ORQA story worth extending

Do NOT enter Track B as "ORQA didn't work so let's try something else." Enter it as "ORQA showed X, now we test whether X holds for agentic execution."

### Design

Select 3-5 self-contained SkillsBench tasks:
- No external API keys required
- Docker builds reliably
- Cover different domains to test skill generalization

For each task, the experiment is:
1. Run the task's existing SKILL.md as v1_curated
2. Run without any skill as baseline
3. Run with a generic scaffold
4. Compare: does the curated skill help for agentic execution where it didn't help (or did help) for QA?

### Implementation

Requires:
- Docker setup on Mac (already available per Phase 1 prerequisites)
- Harbor framework cloned
- Task selection from the 77 self-contained tasks
- Adapter to run our pipeline's evaluation on SkillsBench output format

### What It Adds to the Story

- ORQA tests "can the model identify model components?" (QA)
- SkillsBench tests "can the agent execute a task?" (execution)
- If skills help for execution but not QA: the value is in procedural guidance, not knowledge
- If skills don't help for either: the value proposition needs rethinking

---

## Track C: Autoresearch Loop (CONDITIONAL, strict gate)

### Gate to Enter Track C

ALL of:
1. Gate 1 passes on at least one model with at least one skill variant
2. The Gate 1 pass replicates on a second model OR a second random split
3. Single-step v2 does not show significant test regression

If ANY gate condition fails, Track C is not entered. The justification: autoresearch on a skill that doesn't show signal is just search-overfitting.

### Design (unchanged from Phase 1 spec)

If entered:
- `src/experiment_log.py` — JSONL append-only log
- `src/mutation_proposer.py` — 3 strategies: failure_fix, simplify, reorder
- `src/auto_optimizer.py` — 2-3 rounds, constraint-first acceptance, 3-layer stopping
- Positioned as ablation, not default pipeline

---

## Execution Priority

```
Phase 1 收尾
  ├── StepFun results + Gate check
  ├── Multi-model comparison (DeepSeek vs StepFun)
  └── Walkthrough document for professor

Track A (immediate next)
  ├── Write A1 and A2 skill YAMLs
  ├── Run A1 + A2 on DeepSeek
  ├── Run A1 + A2 on StepFun (if baseline differs)
  ├── Analyze: component-semantics vs archetype vs scaffold
  └── Write Track A results document

Track B (gated on Track A having a clear result)
  ├── Select 3-5 SkillsBench tasks
  ├── Set up Docker/Harbor
  ├── Run baseline vs skilled agent
  └── Cross-benchmark comparison

Track C (strictly gated)
  └── Only if Gate 1 passes + replicates on 2nd model/split
```

## What to Show the Professor

By the end of Phase 2, the demo package should include:

1. **Research narrative:** "We tested whether structured skills improve LLM reasoning on OR benchmarks. Phase 1 showed archetype-level skills don't help — the skill was misaligned with the benchmark's difficulty gradient. Phase 2 tested component-semantics skills aligned to the actual hard questions. [Results of Track A]."

2. **Multi-model comparison table:** DeepSeek + StepFun × {baseline, scaffold, archetype, component-minimal, component-enriched}

3. **Error pattern analysis:** Per question-subtype breakdown showing where each skill type helps or hurts

4. **Methodology contribution:** Controlled experimental design with scaffold control, dev/test split, error taxonomy — reusable for future skill research

5. **EvoMap bridge:** "If validated skills emerge, here's how they map to marketplace assets" — conceptual, not implemented

6. **Working code:** The full pipeline is reproducible and extensible
