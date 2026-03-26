"""Pipeline orchestrator for skill optimization experiments.

Runs all 5 conditions through dev and test sets with strict split enforcement.
The optimizer NEVER sees test data.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from src.llm_client import LLMClient
from src.task_loader import (
    load_questions,
    validate_split_integrity,
    get_seed_examples,
    get_dataset_label,
    get_questions_by_type,
)
from src.skill_manager import (
    get_skill_for_condition,
    validate_scaffold_length,
    load_skill,
    skill_to_yaml_string,
)
from src.skill_generator import generate_skill
from src.agent_runner import run_condition
from src.evaluator import evaluate_condition
from src.error_analyzer import analyze_dev_failures
from src.skill_optimizer import optimize_skill
from src.report_generator import generate_report, generate_marketplace_cards

console = Console()

PRE_OPT_CONDITIONS = ["baseline", "generic_scaffold", "v0_self_generated", "v1_curated"]
ALL_CONDITIONS = ["baseline", "generic_scaffold", "v0_self_generated", "v1_curated", "v2_optimized"]

DATA_DIR = Path(__file__).parent.parent / "data" / "orqa"


def _get_git_commit() -> str:
    """Return current git HEAD hash, or 'unknown' if not in a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "unknown"


def _compute_data_digest() -> str:
    """Compute SHA-256 hex digest of data/orqa/questions.json."""
    questions_path = DATA_DIR / "questions.json"
    sha = hashlib.sha256(questions_path.read_bytes()).hexdigest()
    return f"sha256:{sha}"


def _compute_split_counts(questions: list[dict]) -> dict:
    """Count questions per split."""
    counts: dict[str, int] = {}
    for q in questions:
        split = q.get("split", "unknown")
        counts[split] = counts.get(split, 0) + 1
    return counts


def _save_results(results: dict, split: str, run_id: str):
    """Save evaluation results to results/runs/{run_id}/evaluations/{split}/."""
    output_dir = Path(f"results/runs/{run_id}/evaluations/{split}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for condition, cond_results in results.items():
        path = output_dir / f"{condition}.json"
        with open(path, "w") as f:
            json.dump(cond_results, f, indent=2)


def run_pipeline(model_name: str = "deepseek", run_id: str = None):
    """Run the full skill optimization pipeline.

    Phase 0: Validate data + scaffold
    Phase 1: Run baseline, generic_scaffold, v0, v1 on DEV set
    Phase 2: Error analysis on dev results (root causes)
    Phase 3: Optimize v1 -> v2 using dev evidence, run v2 on dev
    Phase 4: Run ALL 5 conditions on TEST set (held-out)
    Phase 5: Generate report + marketplace cards
    """
    if run_id is None:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    console.rule("[bold blue]Skill Optimization Pipeline")
    console.print(f"Run ID: {run_id}")
    console.print(f"Model: {model_name}")

    # Derive task types dynamically from data
    all_data_questions = load_questions()

    # ─── Write run metadata.json ───────────────────────────────────────
    git_commit = _get_git_commit()
    data_digest = _compute_data_digest()
    split_counts = _compute_split_counts(all_data_questions)
    conditions_run = list(ALL_CONDITIONS)
    dataset_label = get_dataset_label()

    metadata = {
        "run_id": run_id,
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "model": model_name,
        "git_commit": git_commit,
        "data_digest": data_digest,
        "conditions_run": conditions_run,
        "split_counts": split_counts,
        "dataset_label": dataset_label,
    }

    run_dir = Path(f"results/runs/{run_id}")
    run_dir.mkdir(parents=True, exist_ok=True)
    with open(run_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    console.print(f"[green]Metadata written to {run_dir / 'metadata.json'}")
    TASK_TYPES = sorted(set(q["task_type"] for q in all_data_questions))
    console.print(f"Task types: {TASK_TYPES}")

    # ─── Phase 0: Validation ───────────────────────────────────────────
    console.rule("[bold yellow]Phase 0: Validation")

    console.print("Validating split integrity...")
    validate_split_integrity()
    console.print("[green]Split integrity OK")

    console.print("Validating scaffold token length...")
    for task_type in TASK_TYPES:
        try:
            v1_skill = get_skill_for_condition("v1_curated", task_type)
            scaffold_skill = get_skill_for_condition("generic_scaffold", task_type)
            is_valid, info = validate_scaffold_length(v1_skill, scaffold_skill)
            console.print(
                f"  {task_type}: v1={info['v1_tokens']} tokens, "
                f"scaffold={info['scaffold_tokens']} tokens, "
                f"ratio={info['ratio']:.2f} — {'[green]OK' if is_valid else '[red]FAIL'}"
            )
            if not is_valid:
                console.print("[red]Scaffold length mismatch! Adjust scaffold before running.")
                sys.exit(1)
        except FileNotFoundError as e:
            console.print(f"[red]Missing skill file: {e}")
            sys.exit(1)

    console.print(f"Dataset label: {dataset_label}")

    # Initialize LLM client
    client = LLMClient(model_name=model_name, run_id=run_id)
    console.print(f"[green]LLM client initialized: {client.config['model']}")

    # ─── Phase 1: Run conditions on DEV set ────────────────────────────
    console.rule("[bold yellow]Phase 1: Dev Set — Baseline, Scaffold, v0, v1")

    dev_questions = load_questions(split="dev")
    console.print(f"Dev questions: {len(dev_questions)}")

    # Generate v0 skills from seed examples
    console.print("\nGenerating v0 self-generated skills...")
    v0_skills = {}
    for task_type in TASK_TYPES:
        seed_examples = get_seed_examples(task_type)
        console.print(f"  {task_type}: using {len(seed_examples)} seed examples")
        v0_skill = generate_skill(client, task_type, seed_examples)
        v0_skills[task_type] = v0_skill
        console.print(f"  [green]v0 skill generated for {task_type}")

    # Run all pre-optimization conditions on dev
    dev_results = {}
    dev_raw_responses = {}

    for condition in PRE_OPT_CONDITIONS:
        console.print(f"\nRunning {condition} on dev set...")
        condition_responses = {}

        for task_type in TASK_TYPES:
            type_questions = get_questions_by_type("dev", task_type)

            if condition == "v0_self_generated":
                skill = v0_skills[task_type]
            else:
                skill = get_skill_for_condition(condition, task_type)

            responses = run_condition(client, type_questions, condition, skill)
            condition_responses.update(responses)

        # Extract raw responses for error analysis later
        raw_responses = {qid: r["response"] for qid, r in condition_responses.items()}
        dev_raw_responses[condition] = raw_responses

        # Evaluate
        eval_results = evaluate_condition(dev_questions, raw_responses)
        dev_results[condition] = eval_results

        correct = sum(1 for r in eval_results.values() if r["outcome"] == "correct")
        console.print(f"  [green]{condition}: {correct}/{len(eval_results)} correct")

    # ─── Phase 2: Error Analysis (DEV ONLY) ────────────────────────────
    console.rule("[bold yellow]Phase 2: Dev Error Analysis")

    console.print("Analyzing dev failures (root causes)...")
    dev_analysis = analyze_dev_failures(client, dev_questions, dev_results)

    # Save analysis
    analysis_dir = Path(f"results/runs/{run_id}/analysis")
    analysis_dir.mkdir(parents=True, exist_ok=True)
    with open(analysis_dir / "dev_error_analysis.json", "w") as f:
        json.dump(dev_analysis, f, indent=2, default=str)
    console.print(f"[green]Dev error analysis saved to results/runs/{run_id}/analysis/")

    # ─── Phase 3: Optimize v1 -> v2 (DEV evidence ONLY) ────────────────
    console.rule("[bold yellow]Phase 3: Skill Optimization (v1 -> v2)")

    changelogs = {}
    v2_skills = {}

    for task_type in TASK_TYPES:
        console.print(f"\nOptimizing {task_type}...")
        v1_skill = get_skill_for_condition("v1_curated", task_type)
        v1_results = dev_results.get("v1_curated", {})
        v1_analysis = dev_analysis.get("v1_curated", {})

        # Collect dev failures and successes for v1
        type_dev_qs = get_questions_by_type("dev", task_type)
        dev_failures = []
        dev_successes = []

        for q in type_dev_qs:
            qid = q["id"]
            eval_r = v1_results.get(qid, {})
            response = dev_raw_responses.get("v1_curated", {}).get(qid, "")
            analysis = v1_analysis.get(qid, {})

            item = {
                "question": q,
                "response": response,
                "evaluation": eval_r,
            }

            if eval_r.get("outcome") == "correct":
                dev_successes.append(item)
            else:
                item["root_causes"] = analysis.get("root_causes", [])
                item["explanation"] = analysis.get("explanation", "")
                dev_failures.append(item)

        console.print(f"  v1 on dev: {len(dev_successes)} correct, {len(dev_failures)} failed")

        if dev_failures:
            try:
                v2_skill, changelog = optimize_skill(
                    client, v1_skill, dev_failures, dev_successes, task_type
                )
                v2_skills[task_type] = v2_skill
                changelogs[task_type] = changelog
                console.print(f"  [green]v2 optimized skill saved for {task_type}")
                console.print(f"  Changelog: {changelog[:200]}")
            except (ValueError, Exception) as e:
                console.print(f"  [yellow]Optimization failed: {e}")
                console.print(f"  [yellow]Falling back to v1 as v2")
                from src.skill_manager import save_skill
                v2_path = f"skills/orqa/v2_optimized/{task_type}.yaml"
                Path(v2_path).parent.mkdir(parents=True, exist_ok=True)
                save_skill(v1_skill, v2_path)
                v2_skills[task_type] = v1_skill
                changelogs[task_type] = f"Optimization failed ({e}); v2 = v1 copy."
        else:
            console.print(f"  [yellow]No failures on dev — v1 is already perfect, skipping optimization")
            # Copy v1 as v2
            from src.skill_manager import save_skill
            v2_path = f"skills/orqa/v2_optimized/{task_type}.yaml"
            Path(v2_path).parent.mkdir(parents=True, exist_ok=True)
            save_skill(v1_skill, v2_path)
            v2_skills[task_type] = v1_skill
            changelogs[task_type] = "No changes — v1 was already perfect on dev set."

    # Run v2 on dev (for tracking only)
    console.print("\nRunning v2_optimized on dev set (tracking only)...")
    v2_dev_responses = {}
    for task_type in TASK_TYPES:
        type_questions = get_questions_by_type("dev", task_type)
        skill = v2_skills.get(task_type) or get_skill_for_condition("v2_optimized", task_type)
        responses = run_condition(client, type_questions, "v2_optimized", skill)
        v2_dev_responses.update(responses)

    v2_dev_raw = {qid: r["response"] for qid, r in v2_dev_responses.items()}
    dev_results["v2_optimized"] = evaluate_condition(dev_questions, v2_dev_raw)

    correct = sum(1 for r in dev_results["v2_optimized"].values() if r["outcome"] == "correct")
    console.print(f"  [green]v2_optimized on dev: {correct}/{len(dev_results['v2_optimized'])} correct")

    _save_results(dev_results, "dev", run_id)

    # ─── Phase 4: Held-Out TEST Evaluation ──────────────────────────────
    console.rule("[bold yellow]Phase 4: Test Set — All 5 Conditions (Held Out)")

    test_questions = load_questions(split="test")
    console.print(f"Test questions: {len(test_questions)}")
    console.print("[bold red]CRITICAL: This is the held-out test set. Optimizer never saw these questions.")

    test_results = {}

    for condition in ALL_CONDITIONS:
        console.print(f"\nRunning {condition} on test set...")
        condition_responses = {}

        for task_type in TASK_TYPES:
            type_questions = get_questions_by_type("test", task_type)

            if condition == "v0_self_generated":
                skill = v0_skills.get(task_type)
            elif condition == "v2_optimized":
                skill = v2_skills.get(task_type) or get_skill_for_condition("v2_optimized", task_type)
            else:
                skill = get_skill_for_condition(condition, task_type)

            responses = run_condition(client, type_questions, condition, skill)
            condition_responses.update(responses)

        raw_responses = {qid: r["response"] for qid, r in condition_responses.items()}
        eval_results = evaluate_condition(test_questions, raw_responses)
        test_results[condition] = eval_results

        correct = sum(1 for r in eval_results.values() if r["outcome"] == "correct")
        console.print(f"  [green]{condition}: {correct}/{len(eval_results)} correct")

    _save_results(test_results, "test", run_id)

    # ─── Phase 5: Report Generation ────────────────────────────────────
    console.rule("[bold yellow]Phase 5: Report Generation")

    all_questions = load_questions()

    # Collect skills for report
    skills_dict = {
        "v1_curated": {tt: get_skill_for_condition("v1_curated", tt) for tt in TASK_TYPES},
        "v2_optimized": v2_skills,
    }

    # Build provenance block for artifacts
    provenance = {
        "run_id": metadata["run_id"],
        "timestamp": metadata["timestamp"],
        "model": metadata["model"],
        "git_commit": metadata["git_commit"],
    }

    report = generate_report(
        dev_results=dev_results,
        test_results=test_results,
        dev_analysis=dev_analysis,
        skills=skills_dict,
        changelogs=changelogs,
        dataset_label=dataset_label,
        run_id=run_id,
        model_name=client.config["model"],
        questions=all_questions,
        provenance=provenance,
    )
    console.print("[green]Report saved to docs/03_results_and_analysis.md")

    generate_marketplace_cards(
        test_results=test_results,
        dev_results=dev_results,
        skills=skills_dict,
        changelogs=changelogs,
        dataset_label=dataset_label,
        model_name=client.config["model"],
        questions=all_questions,
        run_id=run_id,
        provenance=provenance,
    )
    console.print(f"[green]Marketplace cards saved to results/runs/{run_id}/marketplace_cards/")

    # ─── Summary ────────────────────────────────────────────────────────
    console.rule("[bold green]Pipeline Complete")

    table = Table(title="Test Set Results (Primary Evidence)")
    table.add_column("Condition", style="bold")
    table.add_column("Accuracy", justify="right")

    for cond in ALL_CONDITIONS:
        test_qs = [q for q in all_questions if q["split"] == "test"]
        from src.report_generator import compute_accuracy
        acc = compute_accuracy(test_results.get(cond, {}), test_qs)
        table.add_row(cond, f"{acc:.0%}")

    console.print(table)
    console.print(f"\nFull report: docs/03_results_and_analysis.md")
    console.print(f"Run ID: {run_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run skill optimization pipeline")
    parser.add_argument("--model", default="deepseek", help="Model name from configs/models.yaml")
    parser.add_argument("--run-id", default=None, help="Custom run ID (default: timestamp)")
    args = parser.parse_args()
    run_pipeline(model_name=args.model, run_id=args.run_id)
