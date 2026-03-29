# SkillsBench Implementation Checklist

> **For agents:** This document is a practical implementation checklist for bringing the current SkillsBench workstream from a partial Layer A pilot scaffold to a spec-compliant experimental pipeline.

**Goal:** Close the gap between the current repository state and the SkillsBench protocol-strength specs, with enough structure that another agent can execute the remaining work in a controlled way.

**Scope:** SkillsBench only. This document does not cover the legacy ORQA pipeline except where reuse is explicitly intended.

---

## Current Status

The repository already contains:

- task selection and pilot split documentation
- environment validation notes
- curated, generic scaffold, and self-generated one-shot skill artifacts for the 3 pilot tasks
- Harbor task directories for 4 conditions:
  - `baseline`
  - `generic_scaffold`
  - `curated`
  - `self_generated_one_shot`
- manual pilot execution evidence under `results/skillsbench/runs/`

The repository does **not** yet contain:

- `self_generated_optimized` skills
- `curated_optimized` skills
- a SkillsBench-specific orchestrator
- spec-compliant run manifests and standardized run artifacts
- a symmetric optimization loop for SkillsBench
- a Layer B held-out evaluation split

---

## Main Gaps To Close

### 1. Six-condition experiment is incomplete

The SkillsBench spec requires 6 conditions:

- `baseline`
- `generic_scaffold`
- `curated`
- `self_generated_one_shot`
- `self_generated_optimized`
- `curated_optimized`

Current builder and artifact directories only support the first 4.

### 2. Run schema is documented but not implemented

The spec requires standardized outputs such as:

- `manifest.json`
- `skill_used.yaml`
- `test_results.json`
- `error_analysis.json`
- provenance fields such as `author_model`, `optimizer_model`, `solver_model`

Current SkillsBench runs mostly expose raw Harbor outputs instead of the normalized schema.

### 3. No SkillsBench optimization pipeline exists yet

The repository has reusable ORQA components, but not a SkillsBench-native pipeline for:

1. running dev conditions
2. analyzing failures
3. optimizing skills under matched budgets
4. rerunning optimized conditions
5. reporting results in SkillsBench terms

### 4. Current split is valid for Layer A only

The current split file is explicitly a Layer A pilot artifact. It is useful for system validation, but not for the claim-bearing protocol-strength study.

---

## Workstream Checklist

### Workstream A: Build a SkillsBench Runner

**Target files**

- Create: `src/run_skillsbench.py`
- Reuse as needed:
  - `src/error_analyzer.py`
  - `src/skill_generator.py`
  - `src/skill_optimizer.py`
  - `src/report_generator.py`

**Required outcomes**

- Read `data/skillsbench/split.json`
- Support `layer=A_pilot` and future `layer=B_claim`
- Run the SkillsBench pipeline without depending on ORQA dataset semantics
- Keep solver runtime fixed across conditions for each comparison set

**Acceptance criteria**

- Running one command produces a structured SkillsBench run directory
- The runner can execute at least the current 3-task pilot subset end to end

---

### Workstream B: Extend Harbor Task Building To All 6 Conditions

**Target files**

- Modify: `scripts/build_harbor_tasks.py`

**Required changes**

- Add `self_generated_optimized`
- Add `curated_optimized`
- Add path resolution for both optimized skill directories
- Fail hard if a required skill artifact is missing
- Add optional filtering so the script can rebuild:
  - one task
  - one condition
  - or the full matrix

**Acceptance criteria**

- `data/skillsbench/harbor_tasks/<task>/<condition>/` exists for all 6 conditions
- all non-baseline conditions inject exactly one skill via `skills_dir`

---

### Workstream C: Formalize Skill Artifact Layout

**Target directories**

- Create: `skills/skillsbench/self_generated_optimized/`
- Create: `skills/skillsbench/curated_optimized/`

**Required changes**

- Define naming convention per task
- Store optimized skill YAML in a stable path
- Store a changelog or revision note per optimized skill
- Store optimization metadata sufficient to reconstruct how the skill was produced

**Acceptance criteria**

- every optimized condition resolves to exactly one artifact path
- optimized artifacts are reproducible and auditable

---

### Workstream D: Implement SkillsBench One-shot Skill Generation

**Target files**

- Modify or extend: `src/skill_generator.py`
- Modify or extend: `src/skill_manager.py`

**Required changes**

- Add a SkillsBench generation path separate from ORQA assumptions
- Limit inputs to allowed one-shot authoring inputs:
  - task description
  - tool/environment description
  - success criteria
  - other explicitly allowed context
- Do not expose:
  - curated skill text
  - dev failure logs
  - held-out test evidence

**Acceptance criteria**

- generated one-shot skills can be reproduced from documented inputs
- generation inputs are traceable in metadata

---

### Workstream E: Implement Symmetric SkillsBench Optimization

**Target files**

- Modify or extend: `src/skill_optimizer.py`
- Optional create: `src/skillsbench_optimizer.py`

**Required changes**

- Support two parallel optimization paths:
  - `self_generated_one_shot -> self_generated_optimized`
  - `curated -> curated_optimized`
- Enforce matched optimization budget across both paths:
  - number of rounds
  - dev failures shown
  - success cases shown
  - token budget per round
- Prevent information leakage across conditions

**Acceptance criteria**

- optimization metadata is recorded for both optimized conditions
- budget symmetry can be checked mechanically

---

### Workstream F: Add Structured SkillsBench Error Analysis

**Target files**

- Create: `src/skillsbench_error_analyzer.py`

**Required changes**

- Parse Harbor outputs into a structured failure representation
- Emit `error_analysis.json` for each run
- Distinguish at least:
  - `environment_failure`
  - `agent_system_failure`
  - `skill_failure`
- Split timeout-like outcomes more carefully when evidence differs:
  - true execution timeout
  - post-stop / runner cleanup timeout

**Acceptance criteria**

- every failed or ambiguous run receives a structured error category
- optimization code can consume error-analysis artifacts directly

---

### Workstream G: Implement Run Manifest And Artifact Normalization

**Target files**

- Create: `src/skillsbench_manifest.py`
- Create: `src/skillsbench_result_adapter.py`

**Required changes**

- Generate `manifest.json` with required provenance fields
- Snapshot `skill_used.yaml`
- Normalize verifier output into `test_results.json`
- Capture or link trajectory output consistently
- Compute and store:
  - `author_model`
  - `optimizer_model`
  - `solver_model`
  - `skill_token_count`
  - `optimization_budget`
  - `error_category`

**Acceptance criteria**

- every SkillsBench run directory conforms to the documented schema
- downstream analysis no longer depends on raw Harbor layout quirks

---

### Workstream H: Add Boundary Validation Checks

**Target files**

- Implement inside: `src/run_skillsbench.py`
- Optional helper: `src/skillsbench_validation.py`

**Required checks**

- same Docker image across compared conditions for a task
- same timeout across compared conditions for a task
- same solver model across a comparison set
- same instruction text except for skill injection
- no missing skill file for non-baseline conditions
- no condition-specific environment drift outside the skill artifact

**Acceptance criteria**

- invalid runs fail before execution
- boundary violations are surfaced clearly in logs or manifest metadata

---

### Workstream I: Separate Layer A From Layer B

**Target files**

- Modify usage of: `data/skillsbench/split.json`
- Likely create a future Layer B split file

**Required changes**

- preserve the current pilot as `Layer A`
- do not over-interpret Layer A as claim-bearing evidence
- create a real held-out task-family split for `Layer B`
- ensure held-out evaluation units are never reused for:
  - one-shot authoring
  - optimization feedback
  - final claim-bearing evaluation

**Acceptance criteria**

- Layer A and Layer B can be run independently
- the held-out boundary is explicit and machine-checkable

---

### Workstream J: Add Tests

**Suggested test files**

- Create: `tests/test_build_harbor_tasks.py`
- Create: `tests/test_skillsbench_manifest.py`
- Create: `tests/test_skillsbench_result_adapter.py`
- Create: `tests/test_skillsbench_error_analyzer.py`
- Create: `tests/test_skillsbench_optimizer.py`

**Minimum coverage**

- all 6 conditions can be built
- missing skill artifact causes a hard failure
- manifest fields are complete
- optimization budget symmetry is enforced
- timeout categorization behaves as expected for representative cases

**Acceptance criteria**

- the SkillsBench pipeline can be evolved without breaking the experiment contract silently

---

### Workstream K: Add SkillsBench Reporting

**Target files**

- Create: `src/skillsbench_report_generator.py`

**Required outputs**

- condition comparison table
- token-length and budget-symmetry table
- error taxonomy summary
- optimized-vs-base delta analysis
- explicit Layer A / Layer B interpretation boundary

**Acceptance criteria**

- report consumers can understand both performance and validity constraints from one output bundle

---

## Recommended Execution Order

Implement in this order:

1. run manifest and result normalization
2. 6-condition Harbor task builder
3. one-shot SkillsBench generation path
4. structured SkillsBench error analysis
5. symmetric optimization loop
6. SkillsBench reporting
7. Layer B held-out split and claim-bearing evaluation

This order keeps the work auditable. It avoids generating more pilot results before the run schema and optimization loop are stable.

---

## Review Notes For Future Agents

- Do not treat the current ORQA runner as the SkillsBench solution. Reuse code where useful, but keep benchmark semantics separate.
- Do not claim the protocol-strength study is implemented until both optimized conditions and the run schema are real, not just documented.
- Do not treat the current pilot split as held-out evidence.
- Preserve the skill-only intervention boundary. If the agent runtime, tool policy, planner, or environment wrapper changes across conditions, the comparison is no longer clean.
