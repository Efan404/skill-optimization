# Project Governance, Provenance, and Contract Testing Spec

## Overview

This spec defines the governance layer for the skill-optimization project: how experiment results are organized and traced, how data invariants are enforced, and how artifacts carry provenance metadata. The goal is to make the project auditable, reproducible, and resilient to accidental regressions as the pipeline evolves.

This spec is complementary to the [Real ORQA Migration and Autoresearch Integration Spec](2026-03-26-real-orqa-migration-and-autoresearch-integration.md). That spec covers *what* the pipeline does; this spec covers *how we trust and trace what it produces*.

---

## Core Principles

### Single Source of Truth

- **Data truth** lives in three files: `data/orqa/questions.json`, `data/orqa/split.json`, and the skill YAMLs under `skills/`.
- **Policy truth** lives in the experiment manifest (`configs/experiments.yaml`).
- Everything else is derived. Code reads from these sources; it does not maintain independent copies of task type lists, question counts, or split assignments.

### Generated Docs, Not Hand-Written Results

Results documentation (`docs/03_results_and_analysis.md`) should be generated from run artifacts, not written by hand. A human edits the narrative framing; tables, accuracy numbers, and per-question breakdowns come from the pipeline.

### Contract Tests Lock Invariants

Migration decisions (e.g., "we only have one task type now") are easy to forget and hard to notice when violated. Lightweight contract tests assert these invariants so that a broken assumption fails loudly in the test suite rather than silently corrupting results.

### Run-Scoped Provenance for All Experiment Results

Every experiment run produces a self-contained directory with metadata sufficient to reproduce or audit the run. No result exists without knowing which model, data, code commit, and manifest version produced it.

---

## Design

### Priority 1: Run-Scoped Results

**Problem:** The current `results/` layout uses `results/logs/<timestamp>/` for raw logs and a flat `results/evaluations/{dev|test}/` structure (not yet populated). As the project adds conditions and re-runs experiments, flat directories make it impossible to tell which results came from which run.

**New structure:**

```
results/
  runs/
    <run_id>/
      metadata.json
      evaluations/
        dev/
          baseline_orqa_0006.json
          ...
        test/
          baseline_orqa_0030.json
          ...
      logs/
        baseline_orqa_0006_497d0631.json
        ...
      analysis/
        error_analysis_dev.json
      marketplace_cards/
        or_model_identification.json
```

**`run_id` format:** `<YYYYMMDD>_<HHMMSS>_<short_git_hash>` (e.g., `20260326_143022_a1b2c3d`). Deterministic, sortable, and traceable to a commit.

**`metadata.json` schema:**

```json
{
  "run_id": "20260326_143022_a1b2c3d",
  "timestamp": "2026-03-26T14:30:22Z",
  "model": "deepseek",
  "git_commit_hash": "a1b2c3d4e5f6...",
  "data_digest": "sha256:abcdef...",
  "manifest_version": "skill-optimization-v1",
  "conditions_run": ["baseline", "generic_scaffold", "v0_self_generated", "v1_curated", "v2_optimized"],
  "split_counts": {"seed": 5, "dev": 20, "test": 25}
}
```

- `data_digest` is the SHA-256 hash of `data/orqa/questions.json`. If the data changes between runs, the digest changes.
- `manifest_version` is the `experiment.name` field from `configs/experiments.yaml`.

**Deprecation:** The old flat `results/evaluations/` and `results/logs/` paths are deprecated. Existing log files under `results/logs/` remain as-is but new runs write exclusively to `results/runs/<run_id>/`.

---

### Priority 2: Fake-LLM Smoke Test

**Problem:** The only way to test the pipeline today is to run it against a real LLM API, which is slow, non-deterministic, and costs money. Pipeline regressions (broken imports, wrong split usage, missing fields) go undetected until a live run fails.

**Solution:** A deterministic `FakeLLMClient` that returns canned responses, enabling a fast end-to-end smoke test with no API calls.

**New file:** `tests/test_pipeline_smoke.py`

**FakeLLMClient behavior:**
- Implements the same interface as `src/llm_client.py`
- Returns a fixed response for each question ID (e.g., always answers "A" for `orqa_0006`, "B" for `orqa_0007`)
- Deterministic: same input always produces same output
- Tracks calls for assertion (which questions were sent, in what order)

**Fixture data:**
- 2-3 questions from the dev split, with known correct answers
- At least one question the fake client will get right, at least one it will get wrong (to exercise both paths in error analysis)

**Assertions:**
1. All pipeline phases complete without error (skill generation, evaluation, error analysis, optimization, reporting)
2. Dev/test split is used correctly: dev questions go through error analysis and optimization; test questions are evaluated but not analyzed
3. Error analysis reads only dev results
4. v2 optimization does not touch test set results
5. Output files are created in the expected locations

**Performance target:** Under 5 seconds, no network calls.

---

### Priority 3: Migration Contract Tests

**Problem:** The ORQA migration (Step 1 of the migration spec) changes fundamental assumptions: task types, question format, skill paths. If any code still references the old `linear_programming` or `combinatorial_optimization` task types, or if questions lack the new `context` field, the pipeline will silently produce wrong results.

**New file:** `tests/test_contracts.py`

**Contract assertions:**

1. **Single task type:** Every question in `data/orqa/questions.json` has `task_type` equal to `or_model_identification`. No other task types exist.

2. **Skill file exists:** `skills/orqa/v1_curated/or_model_identification.yaml` exists and is valid YAML.

3. **No legacy task type references:** No Python file under `src/` contains `linear_programming` or `combinatorial_optimization` as string literals (excluding comments and this test file itself). This catches hardcoded task type lists that weren't updated during migration.

4. **Context field present:** Every question in `data/orqa/questions.json` has a non-empty `context` field.

5. **Prompt templates include context:** The prompt construction code in `src/agent_runner.py` includes `{context}` in the template string. This ensures the model actually sees the problem description.

**Design note:** These are intentionally simple, fast assertions. They don't test behavior; they test structural invariants that should never change once the migration is complete.

---

### Priority 4: Provenance Metadata on Artifacts

**Problem:** When reviewing results weeks later, or when sharing marketplace cards, there is no way to trace an artifact back to the exact run that produced it.

**Solution:** Every JSON or YAML artifact produced by a pipeline run includes a `_provenance` block.

**Provenance block schema:**

```json
{
  "_provenance": {
    "run_id": "20260326_143022_a1b2c3d",
    "timestamp": "2026-03-26T14:30:22Z",
    "model": "deepseek",
    "git_commit": "a1b2c3d4e5f6...",
    "data_digest": "sha256:abcdef..."
  }
}
```

**Where provenance is embedded:**
- Evaluation result JSONs (per-question results)
- Error analysis output
- Marketplace cards
- Report generator output (as a header block or top-level key)

**Implementation rule:** Provenance is injected at write time by a shared utility function. Individual modules do not construct provenance dicts themselves; they receive one from the pipeline runner and include it in their output.

---

### Priority 5: project_manifest.yaml (Lightweight)

**Problem:** Policy decisions (allowed task types, expected data source, required provenance fields) are currently implicit. They live in the spec documents and the developer's memory, not in a machine-readable location.

**Solution:** Extend the existing `configs/experiments.yaml` rather than creating a new manifest file. Keep it lightweight; do not duplicate data that can be derived from `questions.json`.

**New fields added to `configs/experiments.yaml`:**

```yaml
experiment:
  name: "skill-optimization-v1"
  model: "deepseek"
  conditions:
    - "baseline"
    - "generic_scaffold"
    - "v0_self_generated"
    - "v1_curated"
    - "v2_optimized"
  task_types:
    - "or_model_identification"

dataset:
  expected_source_category: 1
  allowed_task_types:
    - "or_model_identification"

skills:
  active_paths:
    - "skills/orqa/v1_curated/or_model_identification.yaml"
    - "skills/orqa/v0_self_generated/or_model_identification.yaml"
    - "skills/generic_scaffold/generic_problem_solving.yaml"

artifacts:
  required_provenance_fields:
    - "run_id"
    - "timestamp"
    - "model"
    - "git_commit"
    - "data_digest"
```

**What this does NOT include:**
- Question counts (derived from `questions.json`)
- Split assignments (derived from `split.json`)
- Accuracy thresholds (those are in the spec, not in runtime config)

**Usage:** Contract tests (Priority 3) and the pipeline runner can read `configs/experiments.yaml` to validate that the data and skills match the manifest. This is a soft governance layer, not a hard enforcement gate.

---

### Priority 6: Generated Docs + Sync

**Problem:** `docs/03_results_and_analysis.md` currently contains hand-written results. As the pipeline re-runs, the doc drifts from reality.

**Solution:** The report generator stamps a header on generated docs:

```markdown
<!-- AUTO-GENERATED from run 20260326_143022_a1b2c3d; DO NOT EDIT BY HAND -->
```

This header appears at the top of `docs/03_results_and_analysis.md` whenever the report generator writes or overwrites it.

**Deferred (low priority for research demo):**
- A docs sync checker that compares the run_id in the header against the latest run and warns if they differ
- Automated doc regeneration as part of the pipeline

These are useful for production but not critical for a research demo where runs are infrequent and manually inspected.

---

## Implementation Plan

### Task G1: Run-Scoped Results

**Files modified:**
- `src/run_pipeline.py` — create `results/runs/<run_id>/` directory structure; write metadata.json; route all outputs to the run directory
- `src/report_generator.py` — read from and write to run-scoped paths

**Depends on:** Nothing (runs first)

---

### Task G2: Fake-LLM Smoke Test

**Files created:**
- `tests/test_pipeline_smoke.py` — FakeLLMClient class, fixture questions, end-to-end smoke test

**Files modified:** None (test-only change)

**Depends on:** Nothing (can run in parallel with G3)

---

### Task G3: Contract Tests

**Files created:**
- `tests/test_contracts.py` — structural invariant assertions for post-migration state

**Files modified:** None (test-only change)

**Depends on:** Nothing (can run in parallel with G2)

---

### Task G4: Provenance Metadata

**Files modified:**
- `src/run_pipeline.py` — construct provenance dict at run start, pass to all phase functions
- `src/report_generator.py` — embed provenance in generated reports and marketplace cards

**Depends on:** G1 (provenance references run_id from the run-scoped structure)

---

### Task G5: Manifest Extension

**Files modified:**
- `configs/experiments.yaml` — add `dataset`, `skills`, and `artifacts` sections

**Depends on:** G1 (manifest references the run-scoped artifact structure)

---

### Task G6: Generated Docs Header

**Files modified:**
- `src/report_generator.py` — prepend auto-generated header with run_id when writing docs

**Depends on:** G1 and G4 (needs run_id and provenance infrastructure)

---

## Execution Notes

### Dependency Graph

```
G1 (run-scoped results)
├── G4 (provenance metadata)
│   └── G6 (generated docs header)
├── G5 (manifest extension)
│
G2 (fake-LLM smoke test)  ── independent
G3 (contract tests)        ── independent
```

### Parallelism

- **G2 and G3** are fully independent of each other and of G1. They can be implemented and merged in any order.
- **G1 should land first** before G4, G5, or G6, since those depend on the new results directory structure and run_id format.
- **G4 before G6**, since the docs header uses provenance infrastructure.

### Commit Strategy

Each task is a single atomic commit:
- G1: `feat: add run-scoped results directory structure`
- G2: `test: add fake-LLM pipeline smoke test`
- G3: `test: add migration contract tests`
- G4: `feat: add provenance metadata to pipeline artifacts`
- G5: `config: extend experiments.yaml with manifest fields`
- G6: `feat: add auto-generated header to results docs`

### Deferred Work (Not in Scope)

- **Nightly live-API tests:** Useful for catching model-side regressions, but requires CI infrastructure and API budget. Deferred until the pipeline stabilizes.
- **Full CI docs sync checker:** A pre-commit or CI step that fails if docs are stale. Useful in production; overkill for a research demo with manual runs.
- **Provenance verification CLI:** A command that takes an artifact and verifies its provenance against the git history. Nice-to-have, not essential.
