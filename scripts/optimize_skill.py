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
    parse_job_name,
)
from skillsbench_error_analysis import build_error_analysis

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

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
                        # Only consider complete trials (have verifier_result)
                        try:
                            rj = json.loads(result_path.read_text())
                            if rj.get("verifier_result") is not None:
                                candidates.append(trial_dir)
                        except (json.JSONDecodeError, OSError):
                            continue

    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def load_error_analysis(trial_dir: Path, task_id: str) -> dict | None:
    ea_path = trial_dir / "error_analysis.json"
    if ea_path.exists():
        return json.loads(ea_path.read_text())

    result_json = json.loads((trial_dir / "result.json").read_text())
    ctrf_path = trial_dir / "verifier" / "ctrf.json"
    ctrf_json = json.loads(ctrf_path.read_text()) if ctrf_path.exists() else None
    traj_path = trial_dir / "agent" / "opencode.txt"
    traj_str = str(traj_path) if traj_path.exists() else None
    exc_path = trial_dir / "exception.txt"
    exc_txt = exc_path.read_text() if exc_path.exists() else None

    return build_error_analysis(task_id, result_json, ctrf_json, traj_str, exc_txt)


def generate_revision(current_skill_yaml: str, error_analysis: dict,
                      api_key: str, max_retries: int = 3) -> str:
    if OpenAI is None:
        raise RuntimeError("openai package required. Run: pip install openai")
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    prompt = REVISION_PROMPT_TEMPLATE.format(
        current_skill=current_skill_yaml,
        error_analysis=json.dumps(error_analysis, indent=2),
    )

    import time
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=MAX_OUTPUT_TOKENS,
                temperature=0.3,
            )
            break
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 5 * (attempt + 1)
                print(f"  Retry {attempt + 1}/{max_retries} after error: {e.__class__.__name__}. Waiting {wait}s...")
                time.sleep(wait)
            else:
                raise

    content = response.choices[0].message.content.strip()
    if content.startswith("```yaml"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()


def mutation_gate(original_yaml: str, revised_yaml: str) -> tuple[bool, str]:
    try:
        revised = yaml.safe_load(revised_yaml)
    except yaml.YAMLError as e:
        return False, f"Invalid YAML: {e}"

    if not isinstance(revised, dict):
        return False, "YAML did not parse to a dict"

    if "name" not in revised:
        return False, "Missing 'name' field"

    orig_tokens = len(original_yaml.split())
    rev_tokens = len(revised_yaml.split())
    if rev_tokens > orig_tokens * 2:
        return False, f"Too long: {rev_tokens} words vs original {orig_tokens} (>{2}x)"

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

    input_skill_rel = skill_yaml_path(condition, task_id)
    output_skill_rel = skill_yaml_path(optimized_condition, task_id)
    input_skill_abs = PROJECT_ROOT / input_skill_rel
    output_skill_abs = PROJECT_ROOT / output_skill_rel

    if round_n > 1:
        prev_round_dir = OPTIMIZATION_DIR / task_id / condition / f"round_{round_n - 1}"
        prev_revised = prev_round_dir / "revised_skill.yaml"
        if prev_revised.exists():
            input_skill_abs = prev_revised
            print(f"Using round {round_n - 1} output as input")

    print(f"=== Optimization: {task_id} / {condition} -> {optimized_condition} / round {round_n} ===")
    print(f"Input:  {input_skill_abs}")
    print(f"Output: {output_skill_abs}")

    if not input_skill_abs.exists():
        print(f"ERROR: skill not found: {input_skill_abs}")
        sys.exit(1)
    current_skill_yaml = input_skill_abs.read_text()

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

    round_dir = OPTIMIZATION_DIR / task_id / condition / f"round_{round_n}"
    round_dir.mkdir(parents=True, exist_ok=True)

    (round_dir / "error_analysis.json").write_text(json.dumps(error_analysis, indent=2))

    if args.dry_run:
        print("\nDRY RUN — would call DeepSeek API for revision")
        return

    print("\nCalling DeepSeek API for revision...")
    revised_yaml = generate_revision(current_skill_yaml, error_analysis, api_key)
    (round_dir / "revised_skill.yaml").write_text(revised_yaml)

    passed, reason = mutation_gate(current_skill_yaml, revised_yaml)
    gate_result = {"passed": passed, "reason": reason, "round": round_n}
    (round_dir / "gate_result.json").write_text(json.dumps(gate_result, indent=2))

    if not passed:
        print(f"\nMUTATION GATE REJECTED: {reason}")
        print(f"Revised skill saved to {round_dir / 'revised_skill.yaml'} for inspection")
        return

    output_skill_abs.parent.mkdir(parents=True, exist_ok=True)
    output_skill_abs.write_text(revised_yaml)
    print(f"\nSUCCESS: Optimized skill written to {output_skill_abs}")

    changelog = f"# Round {round_n} Changelog\n\n"
    changelog += f"- Error category: {error_analysis['error_category']}\n"
    changelog += f"- Failure mode: {error_analysis['failure_mode']}\n"
    changelog += f"- Gate result: {reason}\n"
    changelog += f"- Input tokens: {len(current_skill_yaml.split())}\n"
    changelog += f"- Output tokens: {len(revised_yaml.split())}\n"
    (round_dir / "changelog.md").write_text(changelog)


if __name__ == "__main__":
    main()
