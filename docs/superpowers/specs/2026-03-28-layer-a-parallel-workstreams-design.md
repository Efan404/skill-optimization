# Layer A Parallel Workstreams Design

**Date:** 2026-03-28
**Context:** SkillsBench pilot (12/12 conditions complete). Next: optimization, schema, replication.
**Decision Log:** See brainstorming conversation 2026-03-28.
**Canonical Contracts:** This spec implements (not replaces) `docs/skillsbench/run_schema_and_adapter.md`.

---

## Scope

A prerequisite Phase 0 to freeze shared contracts, followed by three parallel workstreams.

| Phase | Deliverable | Dependency |
|-------|-------------|------------|
| **Phase 0** | Condition registry + job name alias map | None — must complete before A/B/C |
| **A** Optimization Pipeline | `self_generated_optimized` + `curated_optimized` skills for 3 tasks | Phase 0 |
| **B** Run Schema Implementation | Canonical `manifest.json` + `error_analysis.json` + `summary.csv` | Phase 0 |
| **C** Stability Replication | 12 conditions x 2 additional rounds | Phase 0 |

A, B, C are independent of each other and can execute in parallel once Phase 0 is done.

---

## Phase 0: Shared Contract Freeze

### Problem

Pilot runs used ad-hoc job names. Condition names are inconsistent across runs:

```
feal-self_generated-deepseek          # missing "_one_shot"
dbwal-self_generated_one_shot-deepseek  # has "_one_shot"
smoke-deepseek-baseline               # different order
```

A canonical contract already exists in `docs/skillsbench/run_schema_and_adapter.md`. Phase 0 implements the minimum shared infrastructure so that A/B/C can consume the same data.

### Deliverable 1: Condition Registry

File: `scripts/skillsbench_registry.py`

```python
# Canonical condition names (from run_schema_and_adapter.md Section 4)
CONDITIONS = [
    "baseline",
    "generic_scaffold",
    "curated",
    "self_generated_one_shot",
    "self_generated_optimized",
    "curated_optimized",
]

# The 4 pilot conditions (Layer A, before optimization)
PILOT_CONDITIONS = CONDITIONS[:4]

# Explicit mapping: base condition → optimized condition name
# Cannot be derived by string concatenation because
# "self_generated_one_shot" + "_optimized" != "self_generated_optimized"
OPTIMIZED_CONDITION = {
    "self_generated_one_shot": "self_generated_optimized",
    "curated": "curated_optimized",
}

# Canonical task names (hyphenated, matching Harbor task directory names)
TASKS = {
    "overfull-hbox": "overfull_hbox",           # task_id: yaml_stem
    "db-wal-recovery": "db_wal_recovery",
    "feal-differential-cryptanalysis": "feal_differential_cryptanalysis",
}

# Short names used in job naming (for Harbor --job-name)
TASK_SHORT = {
    "overfull-hbox": "overfull",
    "db-wal-recovery": "dbwal",
    "feal-differential-cryptanalysis": "feal",
}

# Author model per condition (from run_schema_and_adapter.md Section 1)
AUTHOR_MODEL = {
    "baseline": None,
    "generic_scaffold": None,
    "curated": "human",
    "self_generated_one_shot": "deepseek/deepseek-chat",
    "self_generated_optimized": "deepseek/deepseek-chat",
    "curated_optimized": "human",
}

# Skill path resolution (from run_schema_and_adapter.md Section 4)
def skill_yaml_path(condition: str, task_id: str) -> str | None:
    """Return path relative to project root, or None for baseline."""
    if condition == "baseline":
        return None
    if condition == "generic_scaffold":
        return "skills/skillsbench/generic_scaffold/generic_task_execution.yaml"
    yaml_stem = TASKS[task_id]
    return f"skills/skillsbench/{condition}/{yaml_stem}.yaml"
```

### Deliverable 2: Job Name Alias Map + Ignore List

Resolves existing inconsistent job names to canonical `(task_id, condition)` tuples.
Non-experiment runs (dev tests, smoke tests, Gemini experiments) are excluded.

**Scope:** Only the 12 DeepSeek pilot runs + future canonical runs are in-scope.
All other directories are ignored (not aliased, not errored).

File: `scripts/skillsbench_registry.py` (continued)

```python
# Job names that are NOT part of the DeepSeek pilot experiment.
# These are dev/smoke/Gemini test runs and should be skipped by all workstreams.
IGNORED_JOB_NAMES = {
    "dev-00-overfull-baseline",
    "opencode-api-test",
    "opencode-test-overfull-baseline",
    "overfull-baseline-gemini",
    "overfull-baseline-gemini-v2",
    "overfull-baseline-gemini15pro",
    "overfull-baseline-gemini2flash",
    "overfull-self_generated-gemini",
    "proxy-test-overfull-baseline",
    "proxy-test2-overfull-baseline",
    "smoke-test-overfull-baseline",
}

# Alias map for the 12 DeepSeek pilot runs with non-canonical job names.
# Only entries that deviate from the canonical parsing logic need to be listed.
JOB_NAME_ALIASES = {
    "smoke-deepseek-baseline": ("overfull-hbox", "baseline"),
    "feal-self_generated-deepseek": ("feal-differential-cryptanalysis", "self_generated_one_shot"),
    "overfull-self_generated-deepseek": ("overfull-hbox", "self_generated_one_shot"),
}

def parse_job_name(job_name: str) -> tuple[str, str, str, int] | None:
    """Parse job name → (task_id, condition, solver_model, replication_round).

    Returns None for ignored (non-experiment) job names.

    Canonical format: {task_short}-{condition}-deepseek-r{round}
    Original pilot runs omit the -r{round} suffix (treated as round 1).
    """
    if job_name in IGNORED_JOB_NAMES:
        return None

    # Check alias map first
    if job_name in JOB_NAME_ALIASES:
        task_id, condition = JOB_NAME_ALIASES[job_name]
        return task_id, condition, "deepseek/deepseek-chat", 1

    # Parse canonical format
    # ... (implementation details: split on '-deepseek', resolve task_short, etc.)
```

### Deliverable 3: Canonical Job Name Format

Going forward, all new runs use:

```
{task_short}-{condition}-deepseek-r{round}
```

Examples:
```
overfull-baseline-deepseek-r2
dbwal-self_generated_one_shot-deepseek-r2     # full condition name
feal-curated_optimized-deepseek-r1
```

Rules:
- `condition` is always the full canonical name from `CONDITIONS` list
- `task_short` comes from `TASK_SHORT` dict
- Round 1 for new runs includes `-r1`; original pilot omits it (handled by alias map)

---

## Workstream A: Optimization Pipeline

### Goal

Produce two new skill conditions per task by revising existing skills using dev-time failure data.

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Optimizer model | DeepSeek-V3 first, Claude fallback | Experimental purity: same model family avoids confounding optimizer strength with protocol strength |
| Dev episodes | Current 3 pilot tasks | Layer A is methodology validation, not claim-bearing |
| Automation level | Manual-trigger scripts | 6 optimization jobs total; auditability over automation |
| Max rounds | 2-3 per (task, condition) | Per spec stopping policy |

### Skill Artifact Format

**YAML files** following existing convention (not Markdown). The optimization pipeline reads and writes YAML.

Input path resolved via `registry.skill_yaml_path(condition, task_id)`.
Output path resolved via `registry.skill_yaml_path(OPTIMIZED_CONDITION[condition], task_id)`.

**The output condition name must use `OPTIMIZED_CONDITION` lookup, not string concatenation.**
`"self_generated_one_shot" + "_optimized"` would produce the wrong directory name.

| Base Condition | Optimized Condition | Input Path | Output Path |
|----------------|--------------------|-----------:|------------:|
| `self_generated_one_shot` | `self_generated_optimized` | `.../self_generated_one_shot/overfull_hbox.yaml` | `.../self_generated_optimized/overfull_hbox.yaml` |
| `curated` | `curated_optimized` | `.../curated/overfull_hbox.yaml` | `.../curated_optimized/overfull_hbox.yaml` |

### Pipeline

```
scripts/optimize_skill.py <task_id> <condition> --round N

Input:
  - Current skill artifact (YAML, resolved via registry.skill_yaml_path())
  - Trial result.json + agent trajectory from most recent run
  - Canonical error_analysis.json (if already generated by Workstream B)
    OR raw trajectory + test results (for first pass before B completes)
  - (Round 2+) Previous optimization changelog

Step 1: load or generate error_analysis.json
  - If the trial directory already contains error_analysis.json (generated by
    Workstream B or a previous optimization round), consume it directly.
  - If not, call the SHARED function build_error_analysis() from
    scripts/skillsbench_error_analysis.py (see "Shared: error_analysis generator" below)
  - NEVER generate error_analysis.json with inline logic — always use the shared function

Step 2: generate_revision(current_skill_yaml, error_analysis)
  - Prompt DeepSeek-V3 API with:
    - Current skill text (YAML content)
    - error_analysis.json (structured, canonical format)
    - Constraint: "revise the skill to address the identified failure. Do not add
      information the solver model could not have known. Keep the skill concise.
      Output valid YAML matching the input format."
  - Budget: max 4096 output tokens per revision
  - Output: revised skill YAML + rationale.md

Step 3: mutation_gate(original_skill_yaml, revised_skill_yaml)
  - Check: valid YAML, parseable skill structure, length within 2x of original
  - Check: no test-data leakage (no literal test assertions in skill)
  - If pass: write to skills/skillsbench/{OPTIMIZED_CONDITION[condition]}/{task_yaml_stem}.yaml
  - If fail: log rejection reason, stop

Output per (task, condition, round):
  results/skillsbench/optimization/{task_id}/{condition}/round_N/
  ├── error_analysis.json     # canonical format
  ├── revised_skill.yaml      # the new skill artifact
  ├── rationale.md            # optimizer's reasoning
  ├── gate_result.json        # pass/fail + reasons
  └── changelog.md            # diff summary
```

### Symmetric Budget Enforcement

Per `run_schema_and_adapter.md` Section 5, both `self_generated_optimized` and `curated_optimized` receive identical:
- Number of optimization rounds (same N for both)
- error_analysis.json files shown (same format, same number per round)
- DeepSeek-V3 API calls per round (1 revision call)
- Max output tokens per revision (4096)
- Same prompt template (only the current skill YAML differs)

Logged in manifest.json as `optimization_budget` object per canonical schema.

### Stopping Policy

- Stop after round where revised skill shows no gain on dev task
- Stop after max 3 rounds regardless
- Stop if mutation gate rejects (skill quality regressing)

### Execution Order

For each task (overfull-hbox, db-wal-recovery, feal-differential-cryptanalysis):
1. Run `optimize_skill.py <task_id> self_generated_one_shot --round 1`
2. Run `optimize_skill.py <task_id> curated --round 1`
3. Run `build_harbor_tasks.py` to build Harbor task dirs for optimized conditions
4. Run optimized conditions on Harbor
5. If gain: repeat round 2; if no gain: stop

---

## Workstream B: Run Schema Implementation

### Goal

Implement the canonical run schema from `docs/skillsbench/run_schema_and_adapter.md` by generating all required artifacts for the 12 DeepSeek pilot trials and all future trials.

**This workstream implements the existing spec, not a new schema.**

### Output Location: In-Place Nested Write

Harbor produces: `results/skillsbench/runs/{job_name}/{condition}__{trial_hash}/`

Canonical artifacts are written **inside each trial directory**, alongside Harbor's own files:

```
results/skillsbench/runs/feal-curated-deepseek/curated__dVkEmeV/
  # Harbor's original files (untouched):
  config.json
  result.json
  trial.log
  exception.txt
  agent/
  verifier/
  artifacts/

  # Canonical artifacts (added by generate_manifests.py):
  manifest.json         # per run_schema_and_adapter.md Section 1
  test_results.json     # per run_schema_and_adapter.md:131-143
  skill_used.yaml       # copy of skill artifact at run time
  error_analysis.json   # per run_schema_and_adapter.md:146-156 (failed runs only)
```

This is **additive** — no Harbor files are modified or moved. The script skips
directories in `IGNORED_JOB_NAMES` and any job name that `parse_job_name()` returns None for.

### Script

```
scripts/generate_manifests.py [--runs-dir results/skillsbench/runs]

For each job directory:
  0. Skip if job_name in IGNORED_JOB_NAMES or parse_job_name() returns None
  For each trial subdirectory ({condition}__{hash}):
    1. Resolve (task_id, condition, solver_model, round) via registry.parse_job_name()
    2. Read Harbor's result.json → reward, cost, timing, exception
    3. Read Harbor's config.json → agent type, model config
    4. Read Harbor's verifier/ctrf.json → per-test pass/fail
    5. Detect error_category from exception_info and test results
    6. Generate canonical artifacts (written into the trial directory):
       a. manifest.json (per run_schema_and_adapter.md Section 1)
       b. test_results.json (per run_schema_and_adapter.md:131-143)
       c. skill_used.yaml (copy from skill source, per run_schema_and_adapter.md:124)
       d. error_analysis.json (per run_schema_and_adapter.md:146-156, for failed runs only)
    7. Append row to summary CSV

Summary CSV written to: results/skillsbench/summary.csv
```

### manifest.json

Follows canonical schema exactly from `run_schema_and_adapter.md` Section 1:

```json
{
  "run_id": "20260327_094400",
  "benchmark": "skillsbench",
  "layer": "A_pilot",
  "task_id": "feal-differential-cryptanalysis",
  "condition": "curated",
  "author_model": "human",
  "optimizer_model": null,
  "solver_model": "deepseek/deepseek-chat",
  "skill_path": "skills/skillsbench/curated/feal_differential_cryptanalysis.yaml",
  "skill_token_count": 1842,
  "optimization_budget": null,
  "agent_timeout_seconds": 1800,
  "docker_image": "alexgshaw/feal-differential-cryptanalysis:20250913",
  "result": {
    "success": false,
    "score": 0.0,
    "trajectory_steps": 155,
    "wall_time_seconds": 1800.0
  },
  "error_category": "agent_system_failure",
  "provenance": {
    "split_version": "A_pilot_v1",
    "runtime_version": "harbor-0.1.0",
    "host": "macOS-Darwin-24.6.0-arm64",
    "timestamp": "2026-03-27T09:44:00Z"
  }
}
```

### error_category Classification

Per canonical schema, maps Harbor exceptions to categories:

| error_category | Condition |
|----------------|-----------|
| null | All tests pass (success=true) |
| `skill_failure` | Tests fail, no agent exception (skill didn't guide agent well enough) |
| `agent_system_failure` | AgentTimeoutError or other agent-level exception |
| `environment_failure` | Docker/verifier infrastructure failure |

### test_results.json

Per canonical format (`run_schema_and_adapter.md:131-143`), converted from Harbor's CTRF format:

```json
{
  "task_id": "feal-differential-cryptanalysis",
  "tests": [
    {"name": "test_feal_differential_cryptanalysis_attack", "passed": false, "message": null}
  ],
  "overall_pass": false,
  "pass_count": 0,
  "fail_count": 1
}
```

### error_analysis.json

Per canonical format (`run_schema_and_adapter.md:146-156`). Generated for all failed runs by calling the shared `build_error_analysis()` function from `scripts/skillsbench_error_analysis.py`.

This is the artifact consumed by Workstream A's optimizer. Both B and A use the exact same function — see "Shared: error_analysis Generator" section below.

### summary.csv

Columns match canonical manifest fields for easy aggregation:

```
run_id, task_id, condition, solver_model, author_model, optimizer_model,
skill_token_count, success, score, trajectory_steps, wall_time_seconds,
error_category, replication_round
```

---

## Workstream C: Stability Replication

### Goal

Run all 12 conditions 2 additional times (rounds 2 and 3) to assess result stability.

### Design: Resilient Batch Runner

```
scripts/run_replication.py --round N [--resume]

Core logic:
  for (task_id, condition) in ALL_12_CONDITIONS:
    task_short = registry.TASK_SHORT[task_id]
    job_name = f"{task_short}-{condition}-deepseek-r{round}"
    trial_dir = runs_dir / job_name
    if trial_dir has result.json:
      log "SKIP (already complete)"
      continue
    task_path = resolve_harbor_task_path(task_id, condition)
    harbor run --path <task_path> --agent opencode \
      --model deepseek/deepseek-chat \
      --job-name <job_name> \
      --jobs-dir <runs_dir> \
      --max-retries 1
```

Uses `registry.CONDITIONS`, `registry.TASKS`, and `registry.TASK_SHORT` for all naming — no free-form string construction.

### Resilience / Disconnect Recovery

1. **Idempotent job naming** — Each `(condition, round)` has a unique job name via canonical format. Script checks for `result.json` existence before starting; completed runs are skipped.

2. **Progress file** — `results/skillsbench/replication_progress.json`:
   ```json
   {
     "overfull-baseline-deepseek-r2": {"status": "completed", "reward": 0},
     "feal-curated-deepseek-r2": {"status": "running", "started_at": "..."},
     "dbwal-curated-deepseek-r2": {"status": "pending"}
   }
   ```
   On resume: skip `completed`, retry `running` (may have been interrupted), start `pending`.

3. **Harbor --max-retries 1** — Handles transient Docker errors.

4. **Serial execution** — One condition at a time to avoid resource contention. A single failure does not block subsequent conditions.

5. **Usage:**
   ```bash
   # Start round 2
   python scripts/run_replication.py --round 2

   # Disconnect happens... reconnect and resume:
   python scripts/run_replication.py --round 2 --resume
   # Automatically skips completed, retries from breakpoint
   ```

### Time & Cost Estimate

| Round | Conditions | Est. Time (serial) | Est. Cost |
|-------|:----------:|:------------------:|:---------:|
| Round 2 | 12 | ~3.5h | ~$0.60 |
| Round 3 | 12 | ~3.5h | ~$0.60 |
| **Total** | **24 runs** | **~7h** | **~$1.20** |

---

## Shared: error_analysis Generator

Workstream A and B both need to produce `error_analysis.json`. To prevent drift, a single
shared function is the **only** code path that generates this artifact.

File: `scripts/skillsbench_error_analysis.py`

```python
def build_error_analysis(
    task_id: str,
    result_json: dict,       # Harbor's result.json
    ctrf_json: dict | None,  # Harbor's verifier/ctrf.json
    trajectory_path: str,    # path to agent/opencode.txt or trajectory.json
    exception_txt: str | None,  # contents of exception.txt if present
) -> dict:
    """Generate canonical error_analysis.json per run_schema_and_adapter.md:146-156.

    Returns dict with fields:
      task_id, error_category, failure_mode, description,
      failed_tests, trajectory_summary, optimization_hint
    """
    # 1. Classify error_category from exception and test results
    # 2. Extract failed_tests from ctrf_json
    # 3. Summarize trajectory (key decision points, step count)
    # 4. Generate failure_mode + description + optimization_hint
    #    (LLM-assisted via DeepSeek API for non-trivial failures)
    ...
```

**Consumers:**
- Workstream B (`generate_manifests.py`): calls `build_error_analysis()` for each failed trial
- Workstream A (`optimize_skill.py`): reads the already-generated `error_analysis.json` from the trial directory; only calls `build_error_analysis()` as fallback if B hasn't run yet

**Rule:** Workstream A must never inline its own error analysis logic. If `error_analysis.json` doesn't exist in the trial directory, it imports and calls `build_error_analysis()` from the shared module.

---

## Execution Plan

```
Phase 0 (sequential, ~30min)
  └─ Implement scripts/skillsbench_registry.py
     ├─ Condition registry + TASK_SHORT + AUTHOR_MODEL
     ├─ skill_yaml_path() resolver
     ├─ parse_job_name() with alias map
     └─ Canonical job name format

Then parallel:
  ├─ Agent A: Workstream A (optimize_skill.py)
  │   - Reads YAML skills via registry.skill_yaml_path()
  │   - Produces error_analysis.json in canonical format
  │   - Writes optimized YAML to canonical paths
  │
  ├─ Agent B: Workstream B (generate_manifests.py)
  │   - Resolves identity via registry.parse_job_name()
  │   - Generates canonical manifest.json, test_results.json, skill_used.yaml
  │   - Generates error_analysis.json for failed runs
  │   - Outputs summary.csv
  │
  └─ Agent C: Workstream C (run_replication.py)
      - Uses registry for job naming and condition enumeration
      - Runs 12 conditions x 2 rounds
      - Produces raw Harbor output for B to process later

After all three:
  1. Re-run Agent B on new replication data
  2. Agent A consumes error_analysis.json from B for optimization rounds
  3. Update analysis report
```

---

## Out of Scope

- Layer B task selection and held-out split (deferred)
- Automated optimization loop (deferred to Layer B)
- Gemini cross-model comparison (blocked by Docker geo-restriction)
- Harbor code modifications
- Non-DeepSeek runs (dev tests, smoke tests, Gemini experiments are in IGNORED_JOB_NAMES)
- Restructuring existing Harbor trial directories (canonical artifacts are added in-place)
