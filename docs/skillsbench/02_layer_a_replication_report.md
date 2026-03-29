# SkillsBench Layer A: Replication & Optimization Report

**Date:** 2026-03-29
**Solver:** OpenCode + deepseek-chat (DeepSeek-V3)
**Optimizer:** DeepSeek-V3 (symmetric, same as solver)
**Rounds:** R1 (pilot, n=1) + R2 (replication, 10/12 complete)
**Status:** 4 pilot conditions replicated; optimization pipeline implemented; optimized skills generated but not yet evaluated

---

## 1. Replication Results (R1 + R2)

### 1.1 Raw Reward Matrix

| Task | Condition | R1 | R2 | Stable? |
|------|-----------|:--:|:--:|:-------:|
| **overfull-hbox** | baseline | 0 | **1** | no |
| | generic_scaffold | 0 | 0 | yes |
| | curated | 0 | 0 | yes |
| | self_generated_one_shot | **1** | 0 (timeout) | no |
| **db-wal-recovery** | baseline | 0 | 0 | yes |
| | generic_scaffold | 0 | 0 | yes |
| | curated | 0 | 0 | yes |
| | self_generated_one_shot | 0 | 0 | yes |
| **feal** | baseline | 0 | 0 | yes |
| | generic_scaffold | **1** | **1** | **yes** |
| | curated | 0 (timeout) | **1** (timeout) | no |
| | self_generated_one_shot | **1** | missing | — |

### 1.2 Win Count Summary

| Condition | R1 wins | R2 wins | Total wins / total runs |
|-----------|:-------:|:-------:|:----------------------:|
| baseline | 0/3 | 1/3 | 1/6 |
| generic_scaffold | 1/3 | 1/3 | 2/6 |
| curated | 0/3 | 1/3 | 1/6 |
| self_generated_one_shot | 2/3 | 0/2* | 2/5* |

*feal-self_generated-r2 missing due to Docker interruption.

### 1.3 Key Findings from Replication

**Finding 1: n=1 results are unreliable.**
- overfull-hbox baseline: R1=0, R2=1 — baseline can succeed without any skill
- overfull-hbox self_generated: R1=1, R2=0 — the "best" condition from R1 failed in R2 (with timeout)
- This demonstrates that the original R1 analysis — which declared self_generated the clear winner — was premature

**Finding 2: feal generic_scaffold is the only stable success (R1=1, R2=1).**
- A fully generic process framework with zero domain knowledge succeeds consistently on a hard cryptanalysis task
- This is the strongest individual signal in the dataset

**Finding 3: feal curated R2 produced reward=1 despite AgentTimeoutError.**
- The agent wrote a working `attack.py` before the 1800s timeout
- The verifier ran successfully after timeout and confirmed the attack works
- This means curated on feal may actually be "slow but capable" rather than "failed"
- R1 curated on feal was also timeout with reward=0 — the attack wasn't ready in time that round

**Finding 4: db-wal-recovery is a hard floor — 0/8 across all conditions and rounds.**
- No skill of any type helps DeepSeek-V3 solve WAL recovery
- This is a model capability bottleneck, not a skill design problem

**Finding 5: overfull-hbox has high variance across all conditions.**
- Both baseline and self_generated can succeed (R2 and R1 respectively)
- This task may be near the model's capability threshold — sometimes it gets lucky, sometimes not
- No condition is reliably better than random on this task with n=2

---

## 2. Optimization Pipeline Status

### 2.1 Implementation Complete

| Script | Purpose | Status |
|--------|---------|--------|
| `scripts/skillsbench_registry.py` | Canonical condition/task/job name registry | committed |
| `scripts/skillsbench_error_analysis.py` | Shared error analysis generator | committed |
| `scripts/generate_manifests.py` | Canonical manifest/test_results generation | committed |
| `scripts/run_replication.py` | Resilient batch runner with resume | committed |
| `scripts/optimize_skill.py` | Optimization pipeline with mutation gate | committed |

### 2.2 Optimized Skills Generated (Round 1)

| Task | self_gen_optimized | curated_optimized |
|------|:------------------:|:-----------------:|
| overfull-hbox | SKIP (R1 succeeded) | generated |
| db-wal-recovery | generated | generated |
| feal | SKIP (R1 succeeded) | generated |

4 optimized skill YAMLs produced via DeepSeek-V3 optimizer, all passed mutation gate.
2 conditions skipped because the base skill already succeeded in R1.

### 2.3 Not Yet Done

- Harbor tasks built for optimized conditions but **not yet run**
- Round 2 optimization (if needed) depends on optimized condition results
- feal-self_generated-r2 still missing (1 run)

---

## 3. Revised Analysis (Post-Replication)

### 3.1 R1 Conclusions That Were Overturned

| R1 Claim | R2 Evidence | Revised |
|----------|------------|---------|
| "self_generated is the strongest condition (2/3 wins)" | R2 shows 0/2 wins; R1 successes didn't replicate | **Cannot claim.** Variance too high at n=2. |
| "curated is the weakest (0/3 wins)" | R2 feal curated got reward=1 (timeout but working attack) | **Partially revised.** Curated may work on feal but slowly. |
| "simple process > detailed knowledge" | Baseline also succeeds on overfull (R2); feal scaffold stable | **Directionally supported** but the mechanism is unclear. |

### 3.2 What We Can Claim (With Caveats)

1. **feal generic_scaffold is robustly successful (2/2).** A generic process framework helps on hard tasks. This is the one reliable signal.

2. **db-wal-recovery is beyond DeepSeek-V3's capability regardless of skill.** 0/8 across all conditions. This bounds the skill-improvement ceiling — skills can't fix fundamental model capability gaps.

3. **overfull-hbox results are dominated by variance, not skill quality.** Both baseline and self_generated succeeded once each. At n=2, no condition is distinguishable from noise on this task.

4. **Agent timeout ≠ task failure for feal curated.** The agent can produce a working attack even if it exceeds the time limit. The verifier still evaluates successfully.

### 3.3 What We Cannot Claim

- Any condition is reliably better than another (except feal scaffold, tentatively)
- Optimization will help (optimized conditions haven't been tested)
- These results generalize to other models or tasks

---

## 4. Cost Summary

| Category | Cost |
|----------|:----:|
| R1 pilot (12 runs) | $0.62 |
| R2 replication (10 runs) | $0.45 |
| Optimization API calls (4 revisions) | ~$0.02 |
| **Total** | **~$1.09** |

---

## 5. Remaining Work for Layer A Completion

### Must-Do

- [ ] Run feal-self_generated_one_shot-r2 (1 missing condition)
- [ ] Run optimized conditions on Harbor (4 tasks: curated_optimized × 3, self_gen_optimized × 1)
- [ ] Re-run generate_manifests.py to update summary.csv with R2 data
- [ ] Evaluate whether optimization round 2 is needed

### Should-Do (Before Layer B)

- [ ] Run round 3 for statistical power (n=3 per condition)
- [ ] Cross-model comparison (Claude Sonnet or GPT-4 via OpenRouter)

### Deferred to Layer B

- [ ] Define held-out task split
- [ ] Full 6-condition evaluation on held-out tasks
- [ ] Protocol-strength hypothesis testing (H1-H4)

---

## 6. Artifact References

### Scripts
- Registry: `scripts/skillsbench_registry.py`
- Error analysis: `scripts/skillsbench_error_analysis.py`
- Manifests: `scripts/generate_manifests.py`
- Replication: `scripts/run_replication.py`
- Optimization: `scripts/optimize_skill.py`
- Task builder: `scripts/build_harbor_tasks.py`

### Optimized Skills
- `skills/skillsbench/self_generated_optimized/db_wal_recovery.yaml`
- `skills/skillsbench/curated_optimized/overfull_hbox.yaml`
- `skills/skillsbench/curated_optimized/db_wal_recovery.yaml`
- `skills/skillsbench/curated_optimized/feal_differential_cryptanalysis.yaml`

### Optimization Traces
- `results/skillsbench/optimization/{task}/{condition}/round_1/`

### Run Data
- R1: `results/skillsbench/runs/{task_short}-{condition}-deepseek/`
- R2: `results/skillsbench/runs/{task_short}-{condition}-deepseek-r2/`
- Summary: `results/skillsbench/summary.csv`

### Specs
- Design: `docs/superpowers/specs/2026-03-28-layer-a-parallel-workstreams-design.md`
- Plan: `docs/superpowers/plans/2026-03-28-layer-a-parallel-workstreams.md`
- Canonical contract: `docs/skillsbench/run_schema_and_adapter.md`
