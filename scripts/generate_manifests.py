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

sys.path.insert(0, str(Path(__file__).parent))
from skillsbench_registry import (
    AUTHOR_MODEL,
    parse_job_name,
    skill_yaml_path,
)
from skillsbench_error_analysis import build_error_analysis

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUNS_DIR = PROJECT_ROOT / "results" / "skillsbench" / "runs"


def count_tokens_approx(text: str) -> int:
    return int(len(text.split()) * 1.3)


def find_trial_dirs(job_dir: Path) -> list[Path]:
    return [d for d in job_dir.iterdir() if d.is_dir() and "__" in d.name]


def read_json(path: Path) -> dict | None:
    if path.exists():
        return json.loads(path.read_text())
    return None


def build_manifest(trial_dir, task_id, condition, solver_model, replication_round, result_json, config_json):
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

    reward = result_json.get("verifier_result", {}).get("rewards", {}).get("reward", 0.0)
    success = reward > 0

    exception_info = result_json.get("exception_info")
    if exception_info:
        error_category = "agent_system_failure"
    elif not success:
        error_category = "skill_failure"
    else:
        error_category = None

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

    skill_path_str = skill_yaml_path(condition, task_id)
    skill_token_count = None
    if skill_path_str:
        skill_abs = PROJECT_ROOT / skill_path_str
        if skill_abs.exists():
            skill_token_count = count_tokens_approx(skill_abs.read_text())

    run_id = ""
    if started:
        try:
            dt = datetime.fromisoformat(started.rstrip("Z"))
            run_id = dt.strftime("%Y%m%d_%H%M%S")
        except ValueError:
            run_id = trial_dir.name

    task_path = config_json.get("task", {}).get("path", "")
    docker_image = f"harbor-task:{Path(task_path).name}" if task_path else "unknown"
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


def build_test_results(task_id, ctrf_json):
    tests = []
    for t in ctrf_json.get("results", {}).get("tests", []):
        tests.append({"name": t["name"], "passed": t["status"] == "passed", "message": None})
    summary = ctrf_json.get("results", {}).get("summary", {})
    return {
        "task_id": task_id,
        "tests": tests,
        "overall_pass": summary.get("failed", 1) == 0,
        "pass_count": summary.get("passed", 0),
        "fail_count": summary.get("failed", 0),
    }


def copy_skill_used(trial_dir, condition, task_id):
    skill_path_str = skill_yaml_path(condition, task_id)
    if not skill_path_str:
        return
    skill_abs = PROJECT_ROOT / skill_path_str
    if skill_abs.exists():
        shutil.copy2(skill_abs, trial_dir / "skill_used.yaml")


def process_trial(trial_dir, task_id, condition, solver_model, replication_round, csv_rows):
    result_json = read_json(trial_dir / "result.json")
    if not result_json:
        print(f"  SKIP {trial_dir.name}: no result.json")
        return

    config_json = read_json(trial_dir / "config.json") or {}
    ctrf_json = read_json(trial_dir / "verifier" / "ctrf.json")

    manifest = build_manifest(trial_dir, task_id, condition, solver_model, replication_round, result_json, config_json)
    (trial_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"  + manifest.json (reward={manifest['result']['score']})")

    if ctrf_json:
        test_results = build_test_results(task_id, ctrf_json)
        (trial_dir / "test_results.json").write_text(json.dumps(test_results, indent=2))
        print(f"  + test_results.json ({test_results['pass_count']}/{test_results['pass_count'] + test_results['fail_count']})")

    copy_skill_used(trial_dir, condition, task_id)

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
    csv_rows = []

    for job_dir in sorted(runs_dir.iterdir()):
        if not job_dir.is_dir():
            continue
        job_name = job_dir.name
        parsed = parse_job_name(job_name)
        if parsed is None:
            print(f"SKIP {job_name}")
            continue
        task_id, condition, solver_model, replication_round = parsed
        print(f"\n{job_name} -> {task_id} / {condition} / r{replication_round}")
        for trial_dir in find_trial_dirs(job_dir):
            process_trial(trial_dir, task_id, condition, solver_model, replication_round, csv_rows)

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
