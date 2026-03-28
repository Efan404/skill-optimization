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

    trajectory_summary = _summarize_trajectory(trajectory_path)
    failure_mode, description = _describe_failure(error_category, exception_info, failed_tests)
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
    if not trajectory_path or not Path(trajectory_path).exists():
        return "Trajectory not available."
    path = Path(trajectory_path)
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


def _describe_failure(error_category, exception_info, failed_tests):
    if error_category == "agent_system_failure" and exception_info:
        exc_type = exception_info.get("exception_type", "unknown")
        exc_msg = exception_info.get("exception_message", "")
        return exc_type, exc_msg
    if failed_tests:
        mode = f"{len(failed_tests)}_test_failures"
        desc = f"Tests failed: {', '.join(failed_tests)}"
        return mode, desc
    return "unknown", "Run failed but no specific failure information available."


def _build_hint(error_category, failed_tests, failure_mode):
    if error_category == "agent_system_failure":
        return "Agent hit a system-level failure. Consider adding time management or error recovery guidance to the skill."
    if failed_tests:
        return f"Skill should address: {', '.join(failed_tests)}. Review agent trajectory for specific decision points that led to failure."
    return "Review agent trajectory to identify where the skill could provide better guidance."
