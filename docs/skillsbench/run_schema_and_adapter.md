# SkillsBench Run Schema and Adapter Boundary

**Date:** 2026-03-26
**Depends on:** [experiment design spec](../superpowers/specs/2026-03-26-skillsbench-experiment-design.md), [task selection](task_selection.md), [environment validation](environment_validation.md)

---

## 1. Run Schema

Every SkillsBench run must log the following provenance fields in `manifest.json`.

### Core Identity

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | string | Timestamp-based ID: `YYYYMMDD_HHMMSS` (same format as ORQA) |
| `benchmark` | string | Always `"skillsbench"` |
| `layer` | string | `"A_pilot"` or `"B_claim"` |
| `task_id` | string | Task name (e.g., `"overfull-hbox"`) |

### Condition and Model Provenance

| Field | Type | Description |
|-------|------|-------------|
| `condition` | string | One of: `baseline`, `generic_scaffold`, `curated`, `self_generated_one_shot`, `self_generated_optimized`, `curated_optimized` |
| `author_model` | string or null | Model that wrote the skill. Null for `baseline` and `generic_scaffold`. Specific model ID for self-generated conditions. `"human"` for `curated`. |
| `optimizer_model` | string or null | Model that revised the skill. Null unless the condition is `self_generated_optimized` or `curated_optimized`. |
| `solver_model` | string | Model that executes the task (the agent model). Always populated. |

### Skill Artifact

| Field | Type | Description |
|-------|------|-------------|
| `skill_path` | string or null | Path to skill YAML/MD used. Null for `baseline`. |
| `skill_token_count` | integer or null | Token count of the skill artifact. Null for `baseline`. |

### Optimization Budget

| Field | Type | Description |
|-------|------|-------------|
| `optimization_budget` | object or null | Null unless an optimized condition. When present: `{"rounds": N, "dev_failures_shown": N, "success_cases_shown": N, "token_budget_per_round": N}` |

### Execution Context

| Field | Type | Description |
|-------|------|-------------|
| `agent_timeout_seconds` | integer | Timeout used for this run |
| `docker_image` | string | Exact Docker image used (e.g., `"alexgshaw/overfull-hbox:20251031"`) |

### Result

| Field | Type | Description |
|-------|------|-------------|
| `result` | object | `{"success": bool, "score": float, "trajectory_steps": int, "wall_time_seconds": float}` |
| `error_category` | string or null | Null if success. Otherwise one of: `environment_failure`, `agent_system_failure`, `skill_failure` |

### Provenance Metadata

| Field | Type | Description |
|-------|------|-------------|
| `provenance` | object | `{"split_version": str, "runtime_version": str, "host": str, "timestamp": str}` |

### Example manifest.json

```json
{
  "run_id": "20260326_143022",
  "benchmark": "skillsbench",
  "layer": "A_pilot",
  "task_id": "db-wal-recovery",
  "condition": "self_generated_optimized",
  "author_model": "claude-opus-4-20250514",
  "optimizer_model": "claude-opus-4-20250514",
  "solver_model": "claude-opus-4-20250514",
  "skill_path": "skills/skillsbench/self_generated_optimized/db-wal-recovery.yaml",
  "skill_token_count": 1842,
  "optimization_budget": {
    "rounds": 3,
    "dev_failures_shown": 2,
    "success_cases_shown": 1,
    "token_budget_per_round": 4096
  },
  "agent_timeout_seconds": 900,
  "docker_image": "alexgshaw/db-wal-recovery:20251031",
  "result": {
    "success": true,
    "score": 1.0,
    "trajectory_steps": 14,
    "wall_time_seconds": 287.3
  },
  "error_category": null,
  "provenance": {
    "split_version": "A_pilot_v1",
    "runtime_version": "harbor-0.1.0",
    "host": "macOS-Darwin-24.6.0-arm64",
    "timestamp": "2026-03-26T14:30:22Z"
  }
}
```

---

## 2. Run Directory Structure

Each run produces a self-contained directory under `results/skillsbench/runs/`:

```
results/skillsbench/runs/<run_id>/
  manifest.json          # All provenance fields from Section 1
  trajectory.jsonl       # Agent action log (if available from Harbor)
  skill_used.yaml        # Copy of skill artifact at time of run (null-run has no file)
  task_output/           # Task-specific output files
    (varies by task)     #   e.g., recovered.json, attack.py, input.tex
  test_results.json      # Pass/fail for each test function from the verifier
  error_analysis.json    # Structured failure analysis (for optimization feedback)
```

### File Details

**manifest.json** -- Written by the adapter at run start (provenance fields) and updated at run end (result, error_category). This is the single source of truth for what happened in a run.

**trajectory.jsonl** -- One JSON object per line, each representing an agent action. Format depends on the Harbor agent logger. If the agent does not emit structured trajectory, this file is absent.

**skill_used.yaml** -- Exact copy of the skill artifact injected for this run. For `baseline` condition this file does not exist. For all other conditions, this is a frozen snapshot so that later analysis can inspect exactly what the agent received.

**task_output/** -- Raw output files produced by the agent. Contents vary by task:
- `overfull-hbox`: modified `input.tex`
- `db-wal-recovery`: `recovered.json`
- `feal-differential-cryptanalysis`: `attack.py`

**test_results.json** -- Structured verifier output:
```json
{
  "task_id": "db-wal-recovery",
  "tests": [
    {"name": "test_recovered_json_exists", "passed": true, "message": null},
    {"name": "test_record_count", "passed": true, "message": null},
    {"name": "test_specific_values", "passed": false, "message": "id=2 expected 250, got 200"}
  ],
  "overall_pass": false,
  "pass_count": 2,
  "fail_count": 1
}
```

**error_analysis.json** -- Structured failure categorization used as input to the optimization loop:
```json
{
  "task_id": "db-wal-recovery",
  "error_category": "skill_failure",
  "failure_mode": "incomplete_procedure",
  "description": "Skill described WAL decryption but omitted the XOR key derivation step. Agent attempted brute-force XOR keys instead of comparing against known magic bytes.",
  "failed_tests": ["test_specific_values"],
  "trajectory_summary": "Agent opened DB, saw 5 records, examined WAL header, attempted XOR with keys 0x00-0xFF sequentially, timed out before completing.",
  "optimization_hint": "Add explicit step: compare first 4 bytes of WAL against expected magic 0x377f0682 to derive XOR key directly."
}
```

---

## 3. Skill-Only Adapter Boundary

This is the most critical design constraint. The adapter enforces that the **only variable across conditions is the skill artifact**.

### Frozen (must not change across conditions)

| Component | Description |
|-----------|-------------|
| Agent runtime | Harbor framework version, Claude Code version |
| Planner | Agent's planning/reasoning strategy (no prompt changes beyond skill) |
| Tool policy | Which tools the agent can use, permission settings |
| Memory | No persistent memory across runs; each run starts clean |
| Tool inventory | Same tools available in every condition |
| Environment | Same Docker image, same resources, same file system layout |
| Scoring logic | Same verifier tests, same pass/fail criteria |
| Retry policy | Same for all conditions (no retries within a run, or identical retry policy) |

### Variable (the only thing that changes)

| Component | Description |
|-----------|-------------|
| Skill artifact | The YAML/MD file injected via `skills_dir` |

The skill artifact may vary in:
- Procedure steps
- Checks and guardrails
- Failure warnings
- Ordering of steps
- Wording and organization
- Token length (logged for budget analysis)

### Adapter Execution Sequence

The adapter must perform these steps in order for every run:

1. **Start Docker container** for the task using the exact image from `split.json`
2. **Inject skill (or not)**
   - For `baseline`: no skill injected, `skills_dir` not set
   - For all other conditions: copy the skill file to the skills directory, set `skills_dir` in the environment
   - Injection uses Harbor's native `skills_dir` mechanism (Option A from environment validation)
3. **Run the agent** with fixed configuration
   - Same `solver_model` across all conditions in a comparison set
   - Same timeout from `split.json`
   - Same CLI flags: `--verbose --output-format=stream-json --permission-mode=bypassPermissions --print`
   - No other prompt modifications beyond the skill
4. **Collect trajectory and test results**
   - Capture agent output log
   - Run the task verifier
   - Parse test results into structured format
5. **Log all provenance fields** into `manifest.json`
   - Write initial fields at run start (identity, condition, skill info)
   - Update result fields at run end (success, score, wall time, error category)
6. **Snapshot the skill artifact** by copying it to `skill_used.yaml` in the run directory

### Boundary Violation Checks

Before claiming any result, verify:

- [ ] Same Docker image SHA across all conditions for a given task
- [ ] Same agent CLI flags across all conditions
- [ ] Same timeout across all conditions for a given task
- [ ] No instruction text differences beyond skill injection
- [ ] No tool policy differences between conditions
- [ ] `manifest.json` present and complete for every run

If any of these checks fail, the run is invalid and must be re-executed.

---

## 4. Six-Condition Skill Paths

Each condition uses a specific skill artifact (or none). Paths are relative to the project root.

| Condition | Skill Path | Description |
|-----------|-----------|-------------|
| `baseline` | null (no skill injected) | Raw agent performance, no procedural guidance |
| `generic_scaffold` | `skills/skillsbench/generic_scaffold/generic_task_execution.yaml` | Structure-only control: generic task execution template with no domain content |
| `curated` | `skills/skillsbench/curated/{task_name}.yaml` | Human-authored skill based on oracle solution analysis |
| `self_generated_one_shot` | `skills/skillsbench/self_generated_one_shot/{task_name}.yaml` | AI-authored skill from task description only, single generation pass |
| `self_generated_optimized` | `skills/skillsbench/self_generated_optimized/{task_name}.yaml` | One-shot skill improved using dev feedback via optimization loop |
| `curated_optimized` | `skills/skillsbench/curated_optimized/{task_name}.yaml` | Curated skill improved using the same optimization machinery |

### Directory Layout

```
skills/skillsbench/
  generic_scaffold/
    generic_task_execution.yaml        # One file shared across all tasks
  curated/
    overfull-hbox.yaml
    db-wal-recovery.yaml
    feal-differential-cryptanalysis.yaml
  self_generated_one_shot/
    overfull-hbox.yaml
    db-wal-recovery.yaml
    feal-differential-cryptanalysis.yaml
  self_generated_optimized/
    overfull-hbox.yaml
    db-wal-recovery.yaml
    feal-differential-cryptanalysis.yaml
  curated_optimized/
    overfull-hbox.yaml
    db-wal-recovery.yaml
    feal-differential-cryptanalysis.yaml
```

### Skill Path Resolution

The adapter resolves skill paths as follows:
1. Look up the `condition` for the run
2. If `baseline`, inject no skill and set `skill_path = null`
3. Otherwise, construct the path: `skills/skillsbench/{condition}/{task_name}.yaml`
4. For `generic_scaffold`, the path is always `skills/skillsbench/generic_scaffold/generic_task_execution.yaml` regardless of task
5. Verify the file exists before starting the run; abort with `environment_failure` if missing

---

## 5. Budget Symmetry Contract

The study must prevent confounds where one condition simply receives more optimization budget than another. This section defines the exact budget constraints.

### Authoring Budget

| Condition | Generation Attempts | Context Provided | Notes |
|-----------|-------------------|-----------------|-------|
| `baseline` | 0 | N/A | No skill |
| `generic_scaffold` | 0 | N/A | Pre-written template, not generated |
| `curated` | N/A | Oracle solution + domain expertise | Human-authored, pre-existing |
| `self_generated_one_shot` | 1 | Task description, tool description, success criterion, environment info | Single generation pass, no feedback |
| `self_generated_optimized` | 1 + optimization rounds | Same as one-shot, plus dev feedback | Starts from one-shot artifact |
| `curated_optimized` | N/A + optimization rounds | Same dev feedback as self_generated_optimized | Starts from curated artifact |

### Optimization Budget (must be identical for both optimized conditions)

| Parameter | Value | Notes |
|-----------|-------|-------|
| `rounds` | Fixed N (to be determined in pilot) | Same for `self_generated_optimized` and `curated_optimized` |
| `dev_failures_shown` | Fixed N per round | Same structured error analysis format for both |
| `success_cases_shown` | Fixed N per round | Same number of success trajectories shown |
| `token_budget_per_round` | Fixed N | Maximum tokens the optimizer may use per revision |

The exact values will be set during Layer A pilot execution and frozen before Layer B.

### What the Optimizer Receives (per round)

For both `self_generated_optimized` and `curated_optimized`, the optimizer receives:

1. The current skill artifact
2. N failed run `error_analysis.json` files from dev runs
3. N successful run trajectories from dev runs (for regression protection)
4. The task description (same as what the agent sees)
5. A revision instruction asking for targeted improvements

The optimizer does NOT receive:
- Test run results (held-out)
- The other condition's skill artifact
- The curated skill (for self-generated optimization path)
- The oracle solution

### Skill Token Count Tracking

Every `manifest.json` must include `skill_token_count`. After all runs complete, the analysis must report:

| Condition | Mean Token Count | Min | Max |
|-----------|-----------------|-----|-----|
| `generic_scaffold` | (logged) | - | - |
| `curated` | (logged) | - | - |
| `self_generated_one_shot` | (logged) | - | - |
| `self_generated_optimized` | (logged) | - | - |
| `curated_optimized` | (logged) | - | - |

If any optimized condition's skill is substantially larger (e.g., 2x+ tokens) than the corresponding base condition, this must be flagged as a potential confound in the analysis. The improvement might be partly due to more prompt content rather than better procedural guidance.

### Symmetry Violations to Watch

The following would invalidate the comparison and must be checked:

1. **Asymmetric rounds**: `self_generated_optimized` gets more optimization rounds than `curated_optimized` (or vice versa)
2. **Asymmetric feedback**: one condition sees more dev failures or successes than the other
3. **Asymmetric token budget**: one condition's optimizer is allowed more tokens per round
4. **Information leakage**: optimizer for one condition sees the other condition's skill or test results
5. **Prompt inflation**: optimized skill is dramatically longer without corresponding quality improvement

---

## Relationship to Experiment Phases

This schema and adapter specification covers **Steps 2-4** of the execution plan from the experiment design spec:

- **Step 2 (Adapter Validation)**: Use this document to validate that the adapter correctly enforces the boundary
- **Step 3 (Condition Authoring)**: Populate the skill paths defined in Section 4
- **Step 4 (Dev Optimization)**: Use the run schema to log dev runs, use error_analysis.json as optimizer input

Step 1 (Task Subset Definition) is complete: see [task_selection.md](task_selection.md).
Step 5 (Held-Out Test) uses the same schema but with `layer: "B_claim"` and a proper held-out split.
