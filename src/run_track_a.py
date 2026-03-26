"""Dedicated ORQA Track A runner.

Runs the component-semantics ablation without v0 generation or v2 optimization:
baseline, generic scaffold, archetype-curated v1, A1 minimal, and A2 enriched.
"""

import argparse
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from src.agent_runner import run_condition
from src.error_analyzer import analyze_dev_failures
from src.evaluator import evaluate_condition
from src.llm_client import LLMClient
from src.report_generator import compute_accuracy
from src.skill_manager import get_skill_for_condition, validate_scaffold_length
from src.task_loader import (
    get_dataset_label,
    get_questions_by_type,
    load_questions,
    validate_split_integrity,
)

console = Console()

TRACK_A_CONDITIONS = [
    "baseline",
    "generic_scaffold",
    "v1_curated",
    "v1_component_minimal",
    "v1_component_enriched",
]

DATA_DIR = Path(__file__).parent.parent / "data" / "orqa"


def _get_git_commit() -> str:
    """Return current git HEAD hash, or 'unknown' if unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
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


def build_track_a_metadata(
    run_id: str,
    model_name: str,
    git_commit: str,
    data_digest: str,
    split_counts: dict,
    dataset_label: str,
) -> dict:
    """Build the metadata payload for a Track A run."""
    return {
        "run_id": run_id,
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "model": model_name,
        "git_commit": git_commit,
        "data_digest": data_digest,
        "conditions_run": list(TRACK_A_CONDITIONS),
        "split_counts": split_counts,
        "dataset_label": dataset_label,
        "track": "orqa_track_a",
    }


def _run_split(
    client: LLMClient,
    split: str,
    task_types: list[str],
) -> tuple[dict, dict]:
    """Run all Track A conditions on a split.

    Returns:
        (evaluated_results, raw_responses_by_condition)
    """
    split_questions = load_questions(split=split)
    results = {}
    raw_by_condition = {}

    for condition in TRACK_A_CONDITIONS:
        console.print(f"\nRunning {condition} on {split} set...")
        condition_responses = {}

        for task_type in task_types:
            type_questions = get_questions_by_type(split, task_type)
            skill = get_skill_for_condition(condition, task_type)
            responses = run_condition(client, type_questions, condition, skill)
            condition_responses.update(responses)

        raw_responses = {qid: r["response"] for qid, r in condition_responses.items()}
        raw_by_condition[condition] = raw_responses

        eval_results = evaluate_condition(split_questions, raw_responses)
        results[condition] = eval_results

        correct = sum(1 for r in eval_results.values() if r["outcome"] == "correct")
        console.print(f"  [green]{condition}: {correct}/{len(eval_results)} correct")

    return results, raw_by_condition


def run_track_a(model_name: str = "step_2_mini", run_id: str | None = None) -> dict:
    """Run the ORQA Track A ablation."""
    if run_id is None:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    console.rule("[bold blue]ORQA Track A")
    console.print(f"Run ID: {run_id}")
    console.print(f"Model: {model_name}")

    all_questions = load_questions()
    task_types = sorted(set(q["task_type"] for q in all_questions))
    dataset_label = get_dataset_label()

    metadata = build_track_a_metadata(
        run_id=run_id,
        model_name=model_name,
        git_commit=_get_git_commit(),
        data_digest=_compute_data_digest(),
        split_counts=_compute_split_counts(all_questions),
        dataset_label=dataset_label,
    )
    run_dir = Path(f"results/runs/{run_id}")
    run_dir.mkdir(parents=True, exist_ok=True)
    with open(run_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    console.print(f"[green]Metadata written to {run_dir / 'metadata.json'}")

    console.rule("[bold yellow]Phase 0: Validation")
    validate_split_integrity()
    console.print("[green]Split integrity OK")

    for task_type in task_types:
        scaffold_skill = get_skill_for_condition("generic_scaffold", task_type)
        curated_skill = get_skill_for_condition("v1_curated", task_type)
        is_valid, info = validate_scaffold_length(curated_skill, scaffold_skill)
        console.print(
            f"  {task_type}: curated={info['v1_tokens']} scaffold={info['scaffold_tokens']} "
            f"ratio={info['ratio']:.2f} — {'[green]OK' if is_valid else '[red]FAIL'}"
        )

    client = LLMClient(model_name=model_name, run_id=run_id)
    console.print(f"[green]LLM client initialized: {client.config['model']}")

    console.rule("[bold yellow]Phase 1: Dev Set")
    dev_results, _ = _run_split(client, "dev", task_types)
    _save_results(dev_results, "dev", run_id)

    console.rule("[bold yellow]Phase 2: Dev Error Analysis")
    dev_questions = load_questions(split="dev")
    dev_analysis = analyze_dev_failures(client, dev_questions, dev_results)
    analysis_dir = Path(f"results/runs/{run_id}/analysis")
    analysis_dir.mkdir(parents=True, exist_ok=True)
    with open(analysis_dir / "dev_error_analysis.json", "w") as f:
        json.dump(dev_analysis, f, indent=2, default=str)
    console.print(f"[green]Dev error analysis saved to {analysis_dir / 'dev_error_analysis.json'}")

    console.rule("[bold yellow]Phase 3: Test Set")
    test_results, _ = _run_split(client, "test", task_types)
    _save_results(test_results, "test", run_id)

    console.rule("[bold green]Track A Complete")
    table = Table(title="Track A Test Results")
    table.add_column("Condition", style="bold")
    table.add_column("Accuracy", justify="right")
    test_questions = [q for q in all_questions if q["split"] == "test"]
    for condition in TRACK_A_CONDITIONS:
        acc = compute_accuracy(test_results.get(condition, {}), test_questions)
        table.add_row(condition, f"{acc:.0%}")
    console.print(table)

    return {
        "metadata": metadata,
        "dev_results": dev_results,
        "test_results": test_results,
        "dev_analysis": dev_analysis,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ORQA Track A ablation")
    parser.add_argument("--model", default="step_2_mini", help="Model name from configs/models.yaml")
    parser.add_argument("--run-id", default=None, help="Custom run ID (default: timestamp)")
    args = parser.parse_args()
    run_track_a(model_name=args.model, run_id=args.run_id)
