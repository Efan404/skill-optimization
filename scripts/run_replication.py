#!/usr/bin/env python3
"""Resilient batch runner for SkillsBench replication experiments.

Runs all 12 pilot conditions for a given round, with idempotent
job naming and disconnect recovery.
"""
from __future__ import annotations

import functools
import json
import os

# Force unbuffered output so background runs show progress
print = functools.partial(print, flush=True)
import subprocess
import sys
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
    job_name = make_job_name(task_id, condition, replication_round)
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

    env = {**os.environ, "DEEPSEEK_API_KEY": api_key}

    print(f"  CMD: {' '.join(cmd[:8])}...")
    try:
        result = subprocess.run(
            cmd, cwd=str(HARBOR_DIR), env=env,
            capture_output=True, text=True, timeout=3600,
        )
        if result.returncode == 0:
            return True
        else:
            print(f"  FAIL (exit {result.returncode})")
            if result.stderr:
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

    parser = argparse.ArgumentParser(description="Run SkillsBench replication round")
    parser.add_argument("--round", type=int, required=True, help="Replication round (2, 3, ...)")
    parser.add_argument("--resume", action="store_true", help="Resume from progress file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run")
    args = parser.parse_args()

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key and not args.dry_run:
        print("ERROR: DEEPSEEK_API_KEY not set")
        sys.exit(1)

    progress = load_progress() if args.resume else {}

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
