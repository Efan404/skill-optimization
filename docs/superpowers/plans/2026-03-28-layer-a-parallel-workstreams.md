# Layer A Parallel Workstreams Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Phase 0 (shared registry), then three parallel workstreams: optimization pipeline (A), run schema (B), and stability replication (C).

**Architecture:** Phase 0 creates `scripts/skillsbench_registry.py` and `scripts/skillsbench_error_analysis.py` as shared libraries. A/B/C each produce one script that imports from these. C runs Harbor experiments; B post-processes results; A uses error analysis to generate optimized skills.

**Tech Stack:** Python 3.13, PyYAML, DeepSeek API (via openai SDK), Harbor CLI

**Spec:** `docs/superpowers/specs/2026-03-28-layer-a-parallel-workstreams-design.md`
**Canonical Contract:** `docs/skillsbench/run_schema_and_adapter.md`

---

## File Map

| File | Responsibility | Task |
|------|---------------|------|
| `scripts/skillsbench_registry.py` | Condition names, task mapping, job name parsing, skill path resolution | Phase 0, Task 1 |
| `scripts/skillsbench_error_analysis.py` | Shared `build_error_analysis()` function | Phase 0, Task 2 |
| `tests/test_registry.py` | Tests for registry + error analysis | Phase 0, Tasks 1-2 |
| `scripts/generate_manifests.py` | Canonical manifest/test_results/skill_used/error_analysis generation | Workstream B, Task 3 |
| `scripts/run_replication.py` | Resilient batch runner for replication rounds | Workstream C, Task 4 |
| `scripts/optimize_skill.py` | Optimization pipeline: error analysis → revision → mutation gate | Workstream A, Task 5 |
| `scripts/build_harbor_tasks.py` | **Modify:** add optimized conditions to CONDITIONS + SKILL_PATHS | Workstream A, Task 5 |

---

## Phase 0: Shared Contracts (sequential, must complete before A/B/C)

### Task 1: Condition Registry

**Files:**
- Create: `scripts/skillsbench_registry.py`
- Create: `tests/test_registry.py`

- [ ] **Step 1: Write failing tests for registry constants and skill_yaml_path()**

```python
# tests/test_registry.py
import pytest
from scripts.skillsbench_registry import (
    CONDITIONS,
    PILOT_CONDITIONS,
    OPTIMIZED_CONDITION,
    TASKS,
    TASK_SHORT,
    AUTHOR_MODEL,
    IGNORED_JOB_NAMES,
    JOB_NAME_ALIASES,
    skill_yaml_path,
    parse_job_name,
    make_job_name,
)


class TestConditionConstants:
    def test_six_conditions(self):
        assert len(CONDITIONS) == 6

    def test_pilot_conditions_are_first_four(self):
        assert PILOT_CONDITIONS == CONDITIONS[:4]
        assert "self_generated_optimized" not in PILOT_CONDITIONS
        assert "curated_optimized" not in PILOT_CONDITIONS

    def test_optimized_mapping_not_string_concat(self):
        """self_generated_one_shot + _optimized != self_generated_optimized"""
        assert OPTIMIZED_CONDITION["self_generated_one_shot"] == "self_generated_optimized"
        assert OPTIMIZED_CONDITION["curated"] == "curated_optimized"
        assert len(OPTIMIZED_CONDITION) == 2

    def test_all_conditions_have_author_model(self):
        for c in CONDITIONS:
            assert c in AUTHOR_MODEL


class TestSkillYamlPath:
    def test_baseline_returns_none(self):
        assert skill_yaml_path("baseline", "overfull-hbox") is None

    def test_generic_scaffold_is_shared(self):
        path = skill_yaml_path("generic_scaffold", "overfull-hbox")
        assert path == "skills/skillsbench/generic_scaffold/generic_task_execution.yaml"
        assert skill_yaml_path("generic_scaffold", "db-wal-recovery") == path

    def test_curated_per_task(self):
        assert skill_yaml_path("curated", "overfull-hbox") == \
            "skills/skillsbench/curated/overfull_hbox.yaml"
        assert skill_yaml_path("curated", "db-wal-recovery") == \
            "skills/skillsbench/curated/db_wal_recovery.yaml"

    def test_optimized_uses_correct_dir(self):
        path = skill_yaml_path("self_generated_optimized", "overfull-hbox")
        assert path == "skills/skillsbench/self_generated_optimized/overfull_hbox.yaml"
        assert "one_shot" not in path

    def test_invalid_condition_raises(self):
        with pytest.raises(KeyError):
            skill_yaml_path("nonexistent", "overfull-hbox")


class TestParseJobName:
    def test_ignored_returns_none(self):
        assert parse_job_name("dev-00-overfull-baseline") is None
        assert parse_job_name("opencode-api-test") is None
        assert parse_job_name("overfull-baseline-gemini") is None

    def test_alias_smoke_baseline(self):
        result = parse_job_name("smoke-deepseek-baseline")
        assert result == ("overfull-hbox", "baseline", "deepseek/deepseek-chat", 1)

    def test_alias_feal_self_generated(self):
        result = parse_job_name("feal-self_generated-deepseek")
        assert result == (
            "feal-differential-cryptanalysis",
            "self_generated_one_shot",
            "deepseek/deepseek-chat",
            1,
        )

    def test_canonical_pilot_no_round(self):
        result = parse_job_name("dbwal-curated-deepseek")
        assert result == ("db-wal-recovery", "curated", "deepseek/deepseek-chat", 1)

    def test_canonical_with_round(self):
        result = parse_job_name("overfull-baseline-deepseek-r2")
        assert result == ("overfull-hbox", "baseline", "deepseek/deepseek-chat", 2)

    def test_canonical_long_condition_with_round(self):
        result = parse_job_name("feal-self_generated_one_shot-deepseek-r3")
        assert result == (
            "feal-differential-cryptanalysis",
            "self_generated_one_shot",
            "deepseek/deepseek-chat",
            3,
        )

    def test_unknown_returns_none(self):
        assert parse_job_name("totally-unknown-thing") is None


class TestMakeJobName:
    def test_basic(self):
        assert make_job_name("overfull-hbox", "baseline", 2) == \
            "overfull-baseline-deepseek-r2"

    def test_long_condition(self):
        assert make_job_name("db-wal-recovery", "self_generated_one_shot", 3) == \
            "dbwal-self_generated_one_shot-deepseek-r3"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/efan404/Codes/research/skill-optimization && python -m pytest tests/test_registry.py -v`
Expected: ImportError — module does not exist yet.

- [ ] **Step 3: Implement skillsbench_registry.py**

```python
# scripts/skillsbench_registry.py
"""Canonical condition registry, task mapping, and job name parsing.

Single source of truth for condition names, skill paths, and job name
resolution across all SkillsBench workstreams.

Canonical contract: docs/skillsbench/run_schema_and_adapter.md
"""
from __future__ import annotations

# --- Condition names (run_schema_and_adapter.md Section 4) ---

CONDITIONS = [
    "baseline",
    "generic_scaffold",
    "curated",
    "self_generated_one_shot",
    "self_generated_optimized",
    "curated_optimized",
]

PILOT_CONDITIONS = CONDITIONS[:4]

# Explicit mapping — cannot use string concatenation because
# "self_generated_one_shot" + "_optimized" != "self_generated_optimized"
OPTIMIZED_CONDITION = {
    "self_generated_one_shot": "self_generated_optimized",
    "curated": "curated_optimized",
}

# --- Task names ---

TASKS: dict[str, str] = {
    "overfull-hbox": "overfull_hbox",
    "db-wal-recovery": "db_wal_recovery",
    "feal-differential-cryptanalysis": "feal_differential_cryptanalysis",
}

TASK_SHORT: dict[str, str] = {
    "overfull-hbox": "overfull",
    "db-wal-recovery": "dbwal",
    "feal-differential-cryptanalysis": "feal",
}

# Reverse lookup: short name → full task_id
_SHORT_TO_TASK = {v: k for k, v in TASK_SHORT.items()}

# --- Author model per condition (run_schema_and_adapter.md Section 1) ---

AUTHOR_MODEL: dict[str, str | None] = {
    "baseline": None,
    "generic_scaffold": None,
    "curated": "human",
    "self_generated_one_shot": "deepseek/deepseek-chat",
    "self_generated_optimized": "deepseek/deepseek-chat",
    "curated_optimized": "human",
}

# --- Skill path resolution (run_schema_and_adapter.md Section 4) ---


def skill_yaml_path(condition: str, task_id: str) -> str | None:
    """Return skill path relative to project root, or None for baseline."""
    if condition == "baseline":
        return None
    if condition == "generic_scaffold":
        return "skills/skillsbench/generic_scaffold/generic_task_execution.yaml"
    yaml_stem = TASKS[task_id]  # raises KeyError for unknown task
    if condition not in CONDITIONS:
        raise KeyError(f"Unknown condition: {condition}")
    return f"skills/skillsbench/{condition}/{yaml_stem}.yaml"


# --- Job name parsing ---

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

JOB_NAME_ALIASES: dict[str, tuple[str, str]] = {
    "smoke-deepseek-baseline": ("overfull-hbox", "baseline"),
    "feal-self_generated-deepseek": (
        "feal-differential-cryptanalysis",
        "self_generated_one_shot",
    ),
    "overfull-self_generated-deepseek": ("overfull-hbox", "self_generated_one_shot"),
}


def parse_job_name(job_name: str) -> tuple[str, str, str, int] | None:
    """Parse job name → (task_id, condition, solver_model, round).

    Returns None for ignored or unrecognized job names.
    """
    if job_name in IGNORED_JOB_NAMES:
        return None

    if job_name in JOB_NAME_ALIASES:
        task_id, condition = JOB_NAME_ALIASES[job_name]
        return task_id, condition, "deepseek/deepseek-chat", 1

    # Canonical format: {task_short}-{condition}-deepseek[-r{round}]
    # Split off the round suffix first
    replication_round = 1
    rest = job_name
    if rest.endswith(tuple(f"-r{i}" for i in range(1, 100))):
        # Extract round number
        last_dash = rest.rfind("-r")
        round_str = rest[last_dash + 2:]
        if round_str.isdigit():
            replication_round = int(round_str)
            rest = rest[:last_dash]

    # Must end with -deepseek
    if not rest.endswith("-deepseek"):
        return None
    rest = rest[: -len("-deepseek")]

    # Split into task_short and condition
    # Try each known task_short prefix
    task_id = None
    condition = None
    for short, full_task in _SHORT_TO_TASK.items():
        prefix = short + "-"
        if rest.startswith(prefix):
            candidate_condition = rest[len(prefix):]
            if candidate_condition in CONDITIONS:
                task_id = full_task
                condition = candidate_condition
                break

    if task_id is None:
        return None

    return task_id, condition, "deepseek/deepseek-chat", replication_round


def make_job_name(task_id: str, condition: str, replication_round: int) -> str:
    """Build canonical job name from components."""
    short = TASK_SHORT[task_id]
    return f"{short}-{condition}-deepseek-r{replication_round}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/efan404/Codes/research/skill-optimization && python -m pytest tests/test_registry.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/skillsbench_registry.py tests/test_registry.py
git commit -m "feat: add canonical condition registry with job name parsing"
```

---

### Task 2: Shared Error Analysis Generator

**Files:**
- Create: `scripts/skillsbench_error_analysis.py`
- Modify: `tests/test_registry.py` (add error analysis tests)

- [ ] **Step 1: Write failing tests for build_error_analysis()**

Append to `tests/test_registry.py`:

```python
from scripts.skillsbench_error_analysis import build_error_analysis


class TestBuildErrorAnalysis:
    def test_success_returns_none(self):
        """Successful runs don't need error analysis."""
        result_json = {
            "verifier_result": {"rewards": {"reward": 1.0}},
            "exception_info": None,
        }
        ctrf = {
            "results": {
                "tests": [{"name": "test_a", "status": "passed"}],
                "summary": {"passed": 1, "failed": 0},
            }
        }
        assert build_error_analysis("overfull-hbox", result_json, ctrf, None, None) is None

    def test_timeout_classified_as_agent_system_failure(self):
        result_json = {
            "verifier_result": {"rewards": {"reward": 0.0}},
            "exception_info": {
                "exception_type": "AgentTimeoutError",
                "exception_message": "Agent execution timed out after 1800.0 seconds",
            },
        }
        ctrf = {
            "results": {
                "tests": [{"name": "test_a", "status": "failed"}],
                "summary": {"passed": 0, "failed": 1},
            }
        }
        ea = build_error_analysis("feal-differential-cryptanalysis", result_json, ctrf, None, None)
        assert ea["error_category"] == "agent_system_failure"
        assert ea["task_id"] == "feal-differential-cryptanalysis"
        assert "test_a" in ea["failed_tests"]

    def test_test_failure_classified_as_skill_failure(self):
        result_json = {
            "verifier_result": {"rewards": {"reward": 0.0}},
            "exception_info": None,
        }
        ctrf = {
            "results": {
                "tests": [
                    {"name": "test_pass", "status": "passed"},
                    {"name": "test_fail", "status": "failed"},
                ],
                "summary": {"passed": 1, "failed": 1},
            }
        }
        ea = build_error_analysis("db-wal-recovery", result_json, ctrf, None, None)
        assert ea["error_category"] == "skill_failure"
        assert ea["failed_tests"] == ["test_fail"]

    def test_all_canonical_fields_present(self):
        result_json = {
            "verifier_result": {"rewards": {"reward": 0.0}},
            "exception_info": None,
        }
        ctrf = {
            "results": {
                "tests": [{"name": "test_x", "status": "failed"}],
                "summary": {"passed": 0, "failed": 1},
            }
        }
        ea = build_error_analysis("overfull-hbox", result_json, ctrf, None, None)
        required_fields = {
            "task_id", "error_category", "failure_mode", "description",
            "failed_tests", "trajectory_summary", "optimization_hint",
        }
        assert set(ea.keys()) == required_fields
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/efan404/Codes/research/skill-optimization && python -m pytest tests/test_registry.py::TestBuildErrorAnalysis -v`
Expected: ImportError.

- [ ] **Step 3: Implement skillsbench_error_analysis.py**

```python
# scripts/skillsbench_error_analysis.py
"""Shared error analysis generator for SkillsBench runs.

Produces canonical error_analysis.json per run_schema_and_adapter.md:146-156.
This is the ONLY code path that generates error_analysis.json — both
generate_manifests.py (Workstream B) and optimize_skill.py (Workstream A)
must use this function.
"""
from __future__ import annotations

import json
from pathlib import Path


def build_error_analysis(
    task_id: str,
    result_json: dict,
    ctrf_json: dict | None,
    trajectory_path: str | None,
    exception_txt: str | None,
) -> dict | None:
    """Generate canonical error_analysis.json.

    Returns None for successful runs (reward > 0 and no failed tests).
    Returns dict with canonical fields for failed runs.
    """
    reward = result_json.get("verifier_result", {}).get("rewards", {}).get("reward", 0.0)
    exception_info = result_json.get("exception_info")

    # Determine if this is a failed run
    failed_tests = []
    if ctrf_json:
        for test in ctrf_json.get("results", {}).get("tests", []):
            if test.get("status") != "passed":
                failed_tests.append(test["name"])

    is_success = reward > 0 and not failed_tests and not exception_info
    if is_success:
        return None

    # Classify error_category
    if exception_info:
        exc_type = exception_info.get("exception_type", "")
        if "Timeout" in exc_type:
            error_category = "agent_system_failure"
        elif "Environment" in exc_type or "Docker" in exc_type:
            error_category = "environment_failure"
        else:
            error_category = "agent_system_failure"
    elif failed_tests:
        error_category = "skill_failure"
    else:
        error_category = "skill_failure"

    # Build trajectory summary from trajectory file if available
    trajectory_summary = _summarize_trajectory(trajectory_path)

    # Build failure_mode and description
    failure_mode, description = _describe_failure(
        error_category, exception_info, failed_tests
    )

    # Build optimization hint
    optimization_hint = _build_hint(error_category, failed_tests, failure_mode)

    return {
        "task_id": task_id,
        "error_category": error_category,
        "failure_mode": failure_mode,
        "description": description,
        "failed_tests": failed_tests,
        "trajectory_summary": trajectory_summary,
        "optimization_hint": optimization_hint,
    }


def _summarize_trajectory(trajectory_path: str | None) -> str:
    """Extract key decision points from agent trajectory."""
    if not trajectory_path or not Path(trajectory_path).exists():
        return "Trajectory not available."

    path = Path(trajectory_path)
    # Count steps from OpenCode JSON log
    step_count = 0
    try:
        content = path.read_text()
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                if event.get("type") in ("assistant", "tool_use"):
                    step_count += 1
            except json.JSONDecodeError:
                continue
    except Exception:
        return "Trajectory could not be parsed."

    return f"Agent executed {step_count} steps. See full trajectory for details."


def _describe_failure(
    error_category: str,
    exception_info: dict | None,
    failed_tests: list[str],
) -> tuple[str, str]:
    """Generate failure_mode and description strings."""
    if error_category == "agent_system_failure" and exception_info:
        exc_type = exception_info.get("exception_type", "unknown")
        exc_msg = exception_info.get("exception_message", "")
        return exc_type, exc_msg

    if failed_tests:
        mode = f"{len(failed_tests)}_test_failures"
        desc = f"Tests failed: {', '.join(failed_tests)}"
        return mode, desc

    return "unknown", "Run failed but no specific failure information available."


def _build_hint(
    error_category: str,
    failed_tests: list[str],
    failure_mode: str,
) -> str:
    """Generate a basic optimization hint."""
    if error_category == "agent_system_failure":
        return "Agent hit a system-level failure. Consider adding time management or error recovery guidance to the skill."

    if failed_tests:
        return f"Skill should address: {', '.join(failed_tests)}. Review agent trajectory for specific decision points that led to failure."

    return "Review agent trajectory to identify where the skill could provide better guidance."
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/efan404/Codes/research/skill-optimization && python -m pytest tests/test_registry.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/skillsbench_error_analysis.py tests/test_registry.py
git commit -m "feat: add shared error analysis generator for canonical error_analysis.json"
```

---

## Workstream B: Run Schema Implementation (parallel-ready after Phase 0)

### Task 3: generate_manifests.py

**Files:**
- Create: `scripts/generate_manifests.py`

**Depends on:** `scripts/skillsbench_registry.py`, `scripts/skillsbench_error_analysis.py`

- [ ] **Step 1: Write the script**

```python
#!/usr/bin/env python3
"""Generate canonical manifest.json, test_results.json, skill_used.yaml,
and error_analysis.json for all SkillsBench trial directories.

Implements docs/skillsbench/run_schema_and_adapter.md.
Writes artifacts in-place into each Harbor trial directory.
"""
from __future__ import annotations

import csv
import json
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add scripts/ to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from skillsbench_registry import (
    AUTHOR_MODEL,
    IGNORED_JOB_NAMES,
    parse_job_name,
    skill_yaml_path,
)
from skillsbench_error_analysis import build_error_analysis

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUNS_DIR = PROJECT_ROOT / "results" / "skillsbench" / "runs"


def count_tokens_approx(text: str) -> int:
    """Approximate token count (words * 1.3)."""
    return int(len(text.split()) * 1.3)


def find_trial_dirs(job_dir: Path) -> list[Path]:
    """Find trial subdirectories (pattern: {condition}__{hash})."""
    return [
        d for d in job_dir.iterdir()
        if d.is_dir() and "__" in d.name
    ]


def read_json(path: Path) -> dict | None:
    """Read JSON file, return None if missing."""
    if path.exists():
        return json.loads(path.read_text())
    return None


def build_manifest(
    trial_dir: Path,
    task_id: str,
    condition: str,
    solver_model: str,
    replication_round: int,
    result_json: dict,
    config_json: dict,
) -> dict:
    """Build canonical manifest.json per run_schema_and_adapter.md Section 1."""
    # Timing
    agent_exec = result_json.get("agent_execution", {})
    started = agent_exec.get("started_at", "")
    finished = agent_exec.get("finished_at", "")
    wall_time = 0.0
    if started and finished:
        try:
            t0 = datetime.fromisoformat(started.rstrip("Z")).replace(tzinfo=timezone.utc)
            t1 = datetime.fromisoformat(finished.rstrip("Z")).replace(tzinfo=timezone.utc)
            wall_time = (t1 - t0).total_seconds()
        except ValueError:
            pass

    # Reward
    reward = result_json.get("verifier_result", {}).get("rewards", {}).get("reward", 0.0)
    success = reward > 0

    # Exception / error_category
    exception_info = result_json.get("exception_info")
    if exception_info:
        exc_type = exception_info.get("exception_type", "")
        if "Timeout" in exc_type:
            error_category = "agent_system_failure"
        else:
            error_category = "agent_system_failure"
    elif not success:
        error_category = "skill_failure"
    else:
        error_category = None

    # Trajectory steps (count from agent log)
    trajectory_steps = 0
    agent_log = trial_dir / "agent" / "opencode.txt"
    if agent_log.exists():
        for line in agent_log.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                if event.get("type") in ("assistant", "tool_use"):
                    trajectory_steps += 1
            except (json.JSONDecodeError, TypeError):
                continue

    # Skill info
    skill_path_str = skill_yaml_path(condition, task_id)
    skill_token_count = None
    if skill_path_str:
        skill_abs = PROJECT_ROOT / skill_path_str
        if skill_abs.exists():
            skill_token_count = count_tokens_approx(skill_abs.read_text())

    # run_id from timestamp
    run_id = ""
    if started:
        try:
            dt = datetime.fromisoformat(started.rstrip("Z"))
            run_id = dt.strftime("%Y%m%d_%H%M%S")
        except ValueError:
            run_id = trial_dir.name

    # Docker image from task config path
    task_path = config_json.get("task", {}).get("path", "")
    docker_image = f"harbor-task:{Path(task_path).name}" if task_path else "unknown"

    # Agent timeout
    agent_timeout = config_json.get("agent", {}).get("override_timeout_sec") or 1800

    return {
        "run_id": run_id,
        "benchmark": "skillsbench",
        "layer": "A_pilot",
        "task_id": task_id,
        "condition": condition,
        "author_model": AUTHOR_MODEL.get(condition),
        "optimizer_model": None,
        "solver_model": solver_model,
        "skill_path": skill_path_str,
        "skill_token_count": skill_token_count,
        "optimization_budget": None,
        "agent_timeout_seconds": agent_timeout,
        "docker_image": docker_image,
        "result": {
            "success": success,
            "score": float(reward),
            "trajectory_steps": trajectory_steps,
            "wall_time_seconds": wall_time,
        },
        "error_category": error_category,
        "provenance": {
            "split_version": "A_pilot_v1",
            "runtime_version": "harbor-0.1.0",
            "host": f"{platform.system()}-{platform.release()}-{platform.machine()}",
            "timestamp": started or datetime.now(timezone.utc).isoformat(),
        },
    }


def build_test_results(task_id: str, ctrf_json: dict) -> dict:
    """Convert Harbor CTRF to canonical test_results.json."""
    tests = []
    for t in ctrf_json.get("results", {}).get("tests", []):
        tests.append({
            "name": t["name"],
            "passed": t["status"] == "passed",
            "message": None,
        })
    summary = ctrf_json.get("results", {}).get("summary", {})
    return {
        "task_id": task_id,
        "tests": tests,
        "overall_pass": summary.get("failed", 1) == 0,
        "pass_count": summary.get("passed", 0),
        "fail_count": summary.get("failed", 0),
    }


def copy_skill_used(trial_dir: Path, condition: str, task_id: str):
    """Copy skill YAML to trial dir as skill_used.yaml."""
    skill_path_str = skill_yaml_path(condition, task_id)
    if not skill_path_str:
        return
    skill_abs = PROJECT_ROOT / skill_path_str
    if skill_abs.exists():
        shutil.copy2(skill_abs, trial_dir / "skill_used.yaml")


def process_trial(trial_dir: Path, task_id: str, condition: str,
                  solver_model: str, replication_round: int,
                  csv_rows: list[dict]):
    """Process one trial directory: generate all canonical artifacts."""
    result_json = read_json(trial_dir / "result.json")
    if not result_json:
        print(f"  SKIP {trial_dir.name}: no result.json")
        return

    config_json = read_json(trial_dir / "config.json") or {}
    ctrf_json = read_json(trial_dir / "verifier" / "ctrf.json")

    # 1. manifest.json
    manifest = build_manifest(
        trial_dir, task_id, condition, solver_model, replication_round,
        result_json, config_json,
    )
    (trial_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"  + manifest.json (reward={manifest['result']['score']})")

    # 2. test_results.json
    if ctrf_json:
        test_results = build_test_results(task_id, ctrf_json)
        (trial_dir / "test_results.json").write_text(json.dumps(test_results, indent=2))
        print(f"  + test_results.json ({test_results['pass_count']}/{test_results['pass_count'] + test_results['fail_count']})")

    # 3. skill_used.yaml
    copy_skill_used(trial_dir, condition, task_id)

    # 4. error_analysis.json (failed runs only)
    exception_txt = None
    exc_path = trial_dir / "exception.txt"
    if exc_path.exists():
        exception_txt = exc_path.read_text()

    trajectory_path = trial_dir / "agent" / "opencode.txt"
    traj_str = str(trajectory_path) if trajectory_path.exists() else None

    ea = build_error_analysis(task_id, result_json, ctrf_json, traj_str, exception_txt)
    if ea:
        (trial_dir / "error_analysis.json").write_text(json.dumps(ea, indent=2))
        print(f"  + error_analysis.json ({ea['error_category']})")

    # 5. CSV row
    csv_rows.append({
        "run_id": manifest["run_id"],
        "task_id": task_id,
        "condition": condition,
        "solver_model": solver_model,
        "author_model": manifest["author_model"] or "",
        "optimizer_model": manifest["optimizer_model"] or "",
        "skill_token_count": manifest["skill_token_count"] or "",
        "success": manifest["result"]["success"],
        "score": manifest["result"]["score"],
        "trajectory_steps": manifest["result"]["trajectory_steps"],
        "wall_time_seconds": manifest["result"]["wall_time_seconds"],
        "error_category": manifest["error_category"] or "",
        "replication_round": replication_round,
    })


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate canonical SkillsBench manifests")
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    args = parser.parse_args()

    runs_dir = args.runs_dir
    csv_rows: list[dict] = []

    for job_dir in sorted(runs_dir.iterdir()):
        if not job_dir.is_dir():
            continue

        job_name = job_dir.name
        parsed = parse_job_name(job_name)
        if parsed is None:
            print(f"SKIP {job_name}")
            continue

        task_id, condition, solver_model, replication_round = parsed
        print(f"\n{job_name} → {task_id} / {condition} / r{replication_round}")

        for trial_dir in find_trial_dirs(job_dir):
            process_trial(
                trial_dir, task_id, condition, solver_model,
                replication_round, csv_rows,
            )

    # Write summary CSV
    csv_path = runs_dir.parent / "summary.csv"
    if csv_rows:
        fieldnames = list(csv_rows[0].keys())
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"\nSummary CSV: {csv_path} ({len(csv_rows)} rows)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run on existing pilot data**

Run: `cd /Users/efan404/Codes/research/skill-optimization && python scripts/generate_manifests.py`
Expected: manifest.json + test_results.json + skill_used.yaml + error_analysis.json generated for each of the 12 pilot trials. summary.csv at `results/skillsbench/summary.csv`.

- [ ] **Step 3: Verify a generated manifest matches canonical schema**

Run: `python -c "import json; m=json.load(open('results/skillsbench/runs/feal-generic_scaffold-deepseek/generic_scaffold__CVz62QA/manifest.json')); print(json.dumps(m, indent=2)); assert all(k in m for k in ['run_id','benchmark','layer','task_id','condition','author_model','optimizer_model','solver_model','skill_path','skill_token_count','result','error_category','provenance'])"`
Expected: Full manifest printed, assertion passes.

- [ ] **Step 4: Commit**

```bash
git add scripts/generate_manifests.py results/skillsbench/summary.csv
git commit -m "feat: implement canonical manifest generation for SkillsBench runs"
```

---

## Workstream C: Stability Replication (parallel-ready after Phase 0)

### Task 4: run_replication.py

**Files:**
- Create: `scripts/run_replication.py`

**Depends on:** `scripts/skillsbench_registry.py`

- [ ] **Step 1: Write the script**

```python
#!/usr/bin/env python3
"""Resilient batch runner for SkillsBench replication experiments.

Runs all 12 pilot conditions for a given round, with idempotent
job naming and disconnect recovery.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from skillsbench_registry import (
    PILOT_CONDITIONS,
    TASKS,
    TASK_SHORT,
    make_job_name,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HARBOR_TASKS_DIR = PROJECT_ROOT / "data" / "skillsbench" / "harbor_tasks"
RUNS_DIR = PROJECT_ROOT / "results" / "skillsbench" / "runs"
PROGRESS_FILE = PROJECT_ROOT / "results" / "skillsbench" / "replication_progress.json"

HARBOR_DIR = Path("/Users/efan404/Codes/research/harbor-skillsbench")
DEEPSEEK_MODEL = "deepseek/deepseek-chat"


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return {}


def save_progress(progress: dict):
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2))


def is_completed(job_name: str) -> bool:
    """Check if a job has result.json in any trial subdir."""
    job_dir = RUNS_DIR / job_name
    if not job_dir.exists():
        return False
    for trial_dir in job_dir.iterdir():
        if trial_dir.is_dir() and "__" in trial_dir.name:
            if (trial_dir / "result.json").exists():
                return True
    return False


def run_single(task_id: str, condition: str, replication_round: int,
               api_key: str) -> bool:
    """Run a single Harbor trial. Returns True on success."""
    job_name = make_job_name(task_id, condition, replication_round)

    # Map condition to Harbor task path
    harbor_task_path = HARBOR_TASKS_DIR / task_id / condition
    if not harbor_task_path.exists():
        print(f"  ERROR: task path not found: {harbor_task_path}")
        return False

    cmd = [
        "uv", "run", "harbor", "run",
        "--path", str(harbor_task_path),
        "--agent", "opencode",
        "--model", DEEPSEEK_MODEL,
        "--job-name", job_name,
        "--jobs-dir", str(RUNS_DIR),
        "--max-retries", "1",
        "--debug",
    ]

    env = {
        **dict(__import__("os").environ),
        "DEEPSEEK_API_KEY": api_key,
    }

    print(f"  CMD: {' '.join(cmd[:8])}...")
    try:
        result = subprocess.run(
            cmd,
            cwd=str(HARBOR_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=3600,  # 1h hard timeout per condition
        )
        if result.returncode == 0:
            return True
        else:
            print(f"  FAIL (exit {result.returncode})")
            if result.stderr:
                # Show last 5 lines of stderr
                for line in result.stderr.strip().splitlines()[-5:]:
                    print(f"    {line}")
            return False
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT (1h hard limit)")
        return False
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def main():
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Run SkillsBench replication round")
    parser.add_argument("--round", type=int, required=True, help="Replication round (2, 3, ...)")
    parser.add_argument("--resume", action="store_true", help="Resume from progress file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run without executing")
    args = parser.parse_args()

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key and not args.dry_run:
        print("ERROR: DEEPSEEK_API_KEY not set")
        sys.exit(1)

    progress = load_progress() if args.resume else {}

    # Build full list: 3 tasks × 4 pilot conditions = 12
    jobs = []
    for task_id in TASKS:
        for condition in PILOT_CONDITIONS:
            job_name = make_job_name(task_id, condition, args.round)
            jobs.append((task_id, condition, job_name))

    completed = 0
    skipped = 0
    failed = 0

    print(f"=== Replication Round {args.round} ===")
    print(f"Jobs: {len(jobs)} | Resume: {args.resume}")
    print()

    for task_id, condition, job_name in jobs:
        # Check if already completed
        if is_completed(job_name) or progress.get(job_name, {}).get("status") == "completed":
            print(f"SKIP {job_name} (already complete)")
            skipped += 1
            continue

        if args.dry_run:
            print(f"WOULD RUN: {job_name}")
            continue

        print(f"\nRUN: {job_name}")
        progress[job_name] = {
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        save_progress(progress)

        success = run_single(task_id, condition, args.round, api_key)

        if success and is_completed(job_name):
            progress[job_name] = {"status": "completed"}
            completed += 1
            print(f"  DONE")
        else:
            progress[job_name] = {"status": "failed"}
            failed += 1
            print(f"  FAILED")

        save_progress(progress)

    print(f"\n=== Summary ===")
    print(f"Completed: {completed} | Skipped: {skipped} | Failed: {failed}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test with --dry-run**

Run: `cd /Users/efan404/Codes/research/skill-optimization && python scripts/run_replication.py --round 2 --dry-run`
Expected: Lists 12 jobs with "WOULD RUN:" prefix. No actual Harbor calls.

- [ ] **Step 3: Verify idempotency by checking pilot round 1 detection**

Run: `python -c "from scripts.run_replication import is_completed; print(is_completed('feal-generic_scaffold-deepseek'))"`
Expected: `True` (pilot data exists)

- [ ] **Step 4: Commit**

```bash
git add scripts/run_replication.py
git commit -m "feat: add resilient replication runner with disconnect recovery"
```

- [ ] **Step 5: Start round 2 (long-running)**

Run: `cd /Users/efan404/Codes/research/skill-optimization && DEEPSEEK_API_KEY=REDACTED_DEEPSEEK_API_KEY python scripts/run_replication.py --round 2`
Expected: Runs 12 conditions serially. ~3.5h total. On disconnect, re-run with `--resume`.

---

## Workstream A: Optimization Pipeline (parallel-ready after Phase 0)

### Task 5: optimize_skill.py

**Files:**
- Create: `scripts/optimize_skill.py`
- Modify: `scripts/build_harbor_tasks.py:31-42` (add optimized conditions)

**Depends on:** `scripts/skillsbench_registry.py`, `scripts/skillsbench_error_analysis.py`

- [ ] **Step 1: Write the optimization script**

```python
#!/usr/bin/env python3
"""Skill optimization pipeline for SkillsBench.

Reads a skill YAML + error analysis from a failed trial, calls DeepSeek API
to generate a revised skill, and applies a mutation gate before writing.
"""
from __future__ import annotations

import json
import os
import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from skillsbench_registry import (
    OPTIMIZED_CONDITION,
    TASKS,
    skill_yaml_path,
)
from skillsbench_error_analysis import build_error_analysis

try:
    from openai import OpenAI
except ImportError:
    print("ERROR: openai package required. Run: pip install openai")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = PROJECT_ROOT / "results" / "skillsbench" / "runs"
OPTIMIZATION_DIR = PROJECT_ROOT / "results" / "skillsbench" / "optimization"

MAX_OUTPUT_TOKENS = 4096
REVISION_PROMPT_TEMPLATE = """You are a skill optimization assistant. Your job is to revise a procedural skill YAML that guides a coding agent through a task.

## Current Skill
```yaml
{current_skill}
```

## Error Analysis from Failed Run
```json
{error_analysis}
```

## Instructions
Revise the skill to address the identified failure. Follow these rules:
1. Do NOT add information the solver model could not have known from the task description alone.
2. Keep the skill concise — do not significantly increase length.
3. Output valid YAML matching the same structure as the input (name, when_to_use, procedure, etc.).
4. Focus on the specific failure mode identified in the error analysis.
5. If the failure was a timeout, consider simplifying or streamlining the procedure.
6. If the failure was a constraint violation, add explicit guardrails.

Output ONLY the revised YAML, no explanation."""


def find_latest_trial(task_id: str, condition: str) -> Path | None:
    """Find the most recent trial directory for a task/condition."""
    from skillsbench_registry import parse_job_name

    candidates = []
    for job_dir in RUNS_DIR.iterdir():
        if not job_dir.is_dir():
            continue
        parsed = parse_job_name(job_dir.name)
        if parsed is None:
            continue
        t_id, t_cond, _, _ = parsed
        if t_id == task_id and t_cond == condition:
            for trial_dir in job_dir.iterdir():
                if trial_dir.is_dir() and "__" in trial_dir.name:
                    result_path = trial_dir / "result.json"
                    if result_path.exists():
                        candidates.append(trial_dir)

    if not candidates:
        return None
    # Sort by modification time, return most recent
    return max(candidates, key=lambda p: p.stat().st_mtime)


def load_error_analysis(trial_dir: Path, task_id: str) -> dict | None:
    """Load existing error_analysis.json or generate from raw data."""
    ea_path = trial_dir / "error_analysis.json"
    if ea_path.exists():
        return json.loads(ea_path.read_text())

    # Generate using shared function
    result_json = json.loads((trial_dir / "result.json").read_text())
    ctrf_path = trial_dir / "verifier" / "ctrf.json"
    ctrf_json = json.loads(ctrf_path.read_text()) if ctrf_path.exists() else None
    traj_path = trial_dir / "agent" / "opencode.txt"
    traj_str = str(traj_path) if traj_path.exists() else None
    exc_path = trial_dir / "exception.txt"
    exc_txt = exc_path.read_text() if exc_path.exists() else None

    return build_error_analysis(task_id, result_json, ctrf_json, traj_str, exc_txt)


def generate_revision(current_skill_yaml: str, error_analysis: dict,
                      api_key: str) -> str:
    """Call DeepSeek API to generate revised skill."""
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    prompt = REVISION_PROMPT_TEMPLATE.format(
        current_skill=current_skill_yaml,
        error_analysis=json.dumps(error_analysis, indent=2),
    )

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=MAX_OUTPUT_TOKENS,
        temperature=0.3,
    )

    content = response.choices[0].message.content.strip()
    # Strip markdown code fences if present
    if content.startswith("```yaml"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()


def mutation_gate(original_yaml: str, revised_yaml: str) -> tuple[bool, str]:
    """Check if revised skill passes quality gates.

    Returns (passed, reason).
    """
    # Check valid YAML
    try:
        revised = yaml.safe_load(revised_yaml)
    except yaml.YAMLError as e:
        return False, f"Invalid YAML: {e}"

    if not isinstance(revised, dict):
        return False, "YAML did not parse to a dict"

    # Check required fields
    if "name" not in revised:
        return False, "Missing 'name' field"

    # Check length (must be within 2x of original)
    orig_tokens = len(original_yaml.split())
    rev_tokens = len(revised_yaml.split())
    if rev_tokens > orig_tokens * 2:
        return False, f"Too long: {rev_tokens} words vs original {orig_tokens} (>{2}x)"

    # Check for test data leakage (literal assertion patterns)
    leakage_patterns = ["assert ", "assertEqual", "test_", "expected_output"]
    for pattern in leakage_patterns:
        if pattern in revised_yaml.lower() and pattern not in original_yaml.lower():
            return False, f"Potential test data leakage: '{pattern}' added"

    return True, "Passed all gates"


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Optimize a SkillsBench skill")
    parser.add_argument("task_id", help="Task ID (e.g., overfull-hbox)")
    parser.add_argument("condition", help="Base condition (self_generated_one_shot or curated)")
    parser.add_argument("--round", type=int, default=1, help="Optimization round")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")
    args = parser.parse_args()

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key and not args.dry_run:
        print("ERROR: DEEPSEEK_API_KEY not set")
        sys.exit(1)

    task_id = args.task_id
    condition = args.condition
    round_n = args.round

    if condition not in OPTIMIZED_CONDITION:
        print(f"ERROR: condition must be one of {list(OPTIMIZED_CONDITION.keys())}")
        sys.exit(1)

    optimized_condition = OPTIMIZED_CONDITION[condition]

    # Resolve paths
    input_skill_rel = skill_yaml_path(condition, task_id)
    output_skill_rel = skill_yaml_path(optimized_condition, task_id)
    input_skill_abs = PROJECT_ROOT / input_skill_rel
    output_skill_abs = PROJECT_ROOT / output_skill_rel

    # For round 2+, read from previous round's output
    if round_n > 1:
        prev_round_dir = OPTIMIZATION_DIR / task_id / condition / f"round_{round_n - 1}"
        prev_revised = prev_round_dir / "revised_skill.yaml"
        if prev_revised.exists():
            input_skill_abs = prev_revised
            print(f"Using round {round_n - 1} output as input")

    print(f"=== Optimization: {task_id} / {condition} → {optimized_condition} / round {round_n} ===")
    print(f"Input:  {input_skill_abs}")
    print(f"Output: {output_skill_abs}")

    # Load current skill
    if not input_skill_abs.exists():
        print(f"ERROR: skill not found: {input_skill_abs}")
        sys.exit(1)
    current_skill_yaml = input_skill_abs.read_text()

    # Find latest trial and load error analysis
    trial_dir = find_latest_trial(task_id, condition)
    if trial_dir is None:
        print(f"ERROR: no trial found for {task_id}/{condition}")
        sys.exit(1)
    print(f"Trial:  {trial_dir}")

    error_analysis = load_error_analysis(trial_dir, task_id)
    if error_analysis is None:
        print("INFO: Run succeeded — no error analysis needed, no optimization to do.")
        return

    print(f"Error:  {error_analysis['error_category']} / {error_analysis['failure_mode']}")

    # Output directory
    round_dir = OPTIMIZATION_DIR / task_id / condition / f"round_{round_n}"
    round_dir.mkdir(parents=True, exist_ok=True)

    # Save error analysis
    (round_dir / "error_analysis.json").write_text(json.dumps(error_analysis, indent=2))

    if args.dry_run:
        print("\nDRY RUN — would call DeepSeek API for revision")
        return

    # Generate revision
    print("\nCalling DeepSeek API for revision...")
    revised_yaml = generate_revision(current_skill_yaml, error_analysis, api_key)
    (round_dir / "revised_skill.yaml").write_text(revised_yaml)

    # Mutation gate
    passed, reason = mutation_gate(current_skill_yaml, revised_yaml)
    gate_result = {"passed": passed, "reason": reason, "round": round_n}
    (round_dir / "gate_result.json").write_text(json.dumps(gate_result, indent=2))

    if not passed:
        print(f"\nMUTATION GATE REJECTED: {reason}")
        print(f"Revised skill saved to {round_dir / 'revised_skill.yaml'} for inspection")
        return

    # Write optimized skill to canonical path
    output_skill_abs.parent.mkdir(parents=True, exist_ok=True)
    output_skill_abs.write_text(revised_yaml)
    print(f"\nSUCCESS: Optimized skill written to {output_skill_abs}")

    # Generate changelog
    changelog = f"# Round {round_n} Changelog\n\n"
    changelog += f"- Error category: {error_analysis['error_category']}\n"
    changelog += f"- Failure mode: {error_analysis['failure_mode']}\n"
    changelog += f"- Gate result: {reason}\n"
    changelog += f"- Input tokens: {len(current_skill_yaml.split())}\n"
    changelog += f"- Output tokens: {len(revised_yaml.split())}\n"
    (round_dir / "changelog.md").write_text(changelog)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test with --dry-run on a failed condition**

Run: `cd /Users/efan404/Codes/research/skill-optimization && python scripts/optimize_skill.py overfull-hbox curated --round 1 --dry-run`
Expected: Shows input/output paths, finds trial, loads error analysis, prints "DRY RUN".

- [ ] **Step 3: Update build_harbor_tasks.py to support optimized conditions**

In `scripts/build_harbor_tasks.py`, make these changes:

Replace the `CONDITIONS` list (line 31-36):
```python
CONDITIONS = [
    "baseline",
    "generic_scaffold",
    "curated",
    "self_generated_one_shot",
    "self_generated_optimized",
    "curated_optimized",
]
```

Replace the `SKILL_PATHS` dict (line 38-42):
```python
SKILL_PATHS = {
    "generic_scaffold": lambda task_yaml: PROJECT_ROOT / "skills" / "skillsbench" / "generic_scaffold" / "generic_task_execution.yaml",
    "curated": lambda task_yaml: PROJECT_ROOT / "skills" / "skillsbench" / "curated" / f"{task_yaml}.yaml",
    "self_generated_one_shot": lambda task_yaml: PROJECT_ROOT / "skills" / "skillsbench" / "self_generated_one_shot" / f"{task_yaml}.yaml",
    "self_generated_optimized": lambda task_yaml: PROJECT_ROOT / "skills" / "skillsbench" / "self_generated_optimized" / f"{task_yaml}.yaml",
    "curated_optimized": lambda task_yaml: PROJECT_ROOT / "skills" / "skillsbench" / "curated_optimized" / f"{task_yaml}.yaml",
}
```

- [ ] **Step 4: Commit**

```bash
git add scripts/optimize_skill.py scripts/build_harbor_tasks.py
git commit -m "feat: add skill optimization pipeline with mutation gate"
```

- [ ] **Step 5: Run optimization for round 1 (all 6 task×condition pairs)**

Run sequentially:
```bash
export DEEPSEEK_API_KEY=REDACTED_DEEPSEEK_API_KEY
cd /Users/efan404/Codes/research/skill-optimization

# self_generated_one_shot optimizations
python scripts/optimize_skill.py overfull-hbox self_generated_one_shot --round 1
python scripts/optimize_skill.py db-wal-recovery self_generated_one_shot --round 1
python scripts/optimize_skill.py feal-differential-cryptanalysis self_generated_one_shot --round 1

# curated optimizations
python scripts/optimize_skill.py overfull-hbox curated --round 1
python scripts/optimize_skill.py db-wal-recovery curated --round 1
python scripts/optimize_skill.py feal-differential-cryptanalysis curated --round 1
```
Expected: 6 optimized skill YAMLs in `skills/skillsbench/self_generated_optimized/` and `skills/skillsbench/curated_optimized/`. Some may be gate-rejected if base condition succeeded (overfull self_gen, feal scaffold/self_gen).

- [ ] **Step 6: Build Harbor tasks for optimized conditions**

Run: `python scripts/build_harbor_tasks.py`
Expected: New directories under `data/skillsbench/harbor_tasks/{task}/self_generated_optimized/` and `.../curated_optimized/`.

- [ ] **Step 7: Commit optimized skills and harbor tasks**

```bash
git add skills/skillsbench/self_generated_optimized/ skills/skillsbench/curated_optimized/
git add results/skillsbench/optimization/
git commit -m "feat: generate round 1 optimized skills for Layer A"
```
