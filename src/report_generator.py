"""Report generator for skill optimization experiments.

Produces markdown reports with dev/test separation, paired win/loss tables,
case studies, and demo marketplace cards.
"""

import json
import yaml
from datetime import datetime
from pathlib import Path
from collections import Counter

from src.evaluator import compute_outcome_labels


CONDITIONS = ["baseline", "generic_scaffold", "v0_self_generated", "v1_curated", "v2_optimized"]


def compute_accuracy(results: dict, questions: list[dict], task_type: str = None) -> float:
    """Compute accuracy for a set of results, optionally filtered by task_type.

    The denominator is always the number of questions in the target set, NOT the
    number of results returned. Missing results are treated as failures — this
    prevents API errors from inflating accuracy.

    Args:
        results: {question_id: {"outcome": "correct"|"incorrect"|"extraction_failed", ...}}
        questions: list of question dicts (defines the denominator)
        task_type: if specified, only count questions of this type

    Returns:
        Accuracy as float between 0 and 1. Returns 0.0 if no matching questions.
    """
    if task_type:
        target_ids = [q["id"] for q in questions if q["task_type"] == task_type]
    else:
        target_ids = [q["id"] for q in questions]

    if not target_ids:
        return 0.0

    correct = sum(
        1 for qid in target_ids
        if results.get(qid, {}).get("outcome") == "correct"
    )
    return correct / len(target_ids)


def compute_paired_win_loss(
    baseline_results: dict,
    condition_results: dict,
    question_ids: list[str] | None = None,
) -> dict:
    """Compute paired win/loss between baseline and a condition.

    Uses the union of all question IDs (or an explicit list) as the denominator,
    so missing results are treated as failures — not silently excluded.

    Args:
        baseline_results: {qid: {"outcome": ...}}
        condition_results: {qid: {"outcome": ...}}
        question_ids: If provided, use this as the authoritative set of question IDs.
                      Otherwise uses the union of both result dicts.

    Returns:
        {"wins": N, "losses": N, "ties_correct": N, "ties_incorrect": N,
         "net_delta": N, "missing_baseline": N, "missing_condition": N}
    """
    if question_ids is not None:
        all_ids = set(question_ids)
    else:
        all_ids = set(baseline_results.keys()) | set(condition_results.keys())

    wins = losses = ties_correct = ties_incorrect = 0
    missing_baseline = missing_condition = 0

    for qid in all_ids:
        b = baseline_results.get(qid)
        c = condition_results.get(qid)

        if b is None:
            missing_baseline += 1
        if c is None:
            missing_condition += 1

        b_correct = (b.get("outcome") == "correct") if b else False
        c_correct = (c.get("outcome") == "correct") if c else False

        if not b_correct and c_correct:
            wins += 1
        elif b_correct and not c_correct:
            losses += 1
        elif b_correct and c_correct:
            ties_correct += 1
        else:
            ties_incorrect += 1

    return {
        "wins": wins,
        "losses": losses,
        "ties_correct": ties_correct,
        "ties_incorrect": ties_incorrect,
        "net_delta": wins - losses,
        "missing_baseline": missing_baseline,
        "missing_condition": missing_condition,
    }


def _accuracy_str(acc: float) -> str:
    """Format accuracy as percentage string."""
    return f"{acc:.0%}"


def _build_overview(run_id: str, model_name: str, dataset_label: str, questions: list[dict]) -> str:
    """Build the overview section."""
    n_total = len(questions)
    n_seed = len([q for q in questions if q["split"] == "seed"])
    n_dev = len([q for q in questions if q["split"] == "dev"])
    n_test = len([q for q in questions if q["split"] == "test"])
    task_types = sorted(set(q["task_type"] for q in questions))

    return f"""## Overview

- **Run ID:** `{run_id}`
- **Timestamp:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`
- **Model:** `{model_name}`
- **Dataset label:** {dataset_label}
- **Total questions:** {n_total} (seed: {n_seed}, dev: {n_dev}, test: {n_test})
- **Task types:** {', '.join(task_types)}
- **Conditions:** {', '.join(CONDITIONS)}
"""


def _build_accuracy_table(results: dict, questions: list[dict], split_name: str) -> str:
    """Build an accuracy summary table for a given split."""
    task_types = sorted(set(q["task_type"] for q in questions))

    header = f"### {split_name} Accuracy Summary\n\n"
    col_headers = " | ".join(tt for tt in task_types)
    header += f"| Condition | {col_headers} | Overall |\n"
    header += "|-----------|" + "|".join(["----------"] * len(task_types)) + "|--------|\n"

    rows = []
    for cond in CONDITIONS:
        if cond not in results:
            dashes = " | ".join("—" for _ in task_types)
            rows.append(f"| {cond} | {dashes} | — |")
            continue
        cond_results = results[cond]
        tt_accs = [_accuracy_str(compute_accuracy(cond_results, questions, tt)) for tt in task_types]
        overall = compute_accuracy(cond_results, questions)
        rows.append(f"| {cond} | {' | '.join(tt_accs)} | {_accuracy_str(overall)} |")

    return header + "\n".join(rows) + "\n"


def _build_root_cause_table(dev_analysis: dict) -> str:
    """Build root cause distribution table from dev error analysis."""
    from src.error_analyzer import ROOT_CAUSE_CODES

    header = "### Dev Root Cause Distribution (Incorrect Answers Only)\n\n"
    header += "| Root Cause | " + " | ".join(CONDITIONS) + " |\n"
    header += "|-----------|" + "|".join(["----"] * len(CONDITIONS)) + "|\n"

    rows = []
    for code in ROOT_CAUSE_CODES:
        counts = []
        for cond in CONDITIONS:
            cond_analysis = dev_analysis.get(cond, {})
            count = sum(
                1 for qa in cond_analysis.values()
                if code in qa.get("root_causes", [])
            )
            counts.append(str(count) if count > 0 else "—")
        rows.append(f"| {code} | " + " | ".join(counts) + " |")

    return header + "\n".join(rows) + "\n"


def _build_paired_tables(test_results: dict) -> str:
    """Build paired win/loss tables for test set."""
    if "baseline" not in test_results:
        return "### Paired Win/Loss (Test Set)\n\nBaseline results not available.\n"

    baseline = test_results["baseline"]
    sections = []

    # Each condition vs baseline
    header = "### Paired Win/Loss vs Baseline (Test Set)\n\n"
    header += "| Condition vs Baseline | Wins | Losses | Ties (correct) | Ties (wrong) | Net |\n"
    header += "|----------------------|------|--------|----------------|-------------|-----|\n"

    rows = []
    for cond in CONDITIONS:
        if cond == "baseline" or cond not in test_results:
            continue
        wl = compute_paired_win_loss(baseline, test_results[cond])
        rows.append(
            f"| {cond} | {wl['wins']} | {wl['losses']} | "
            f"{wl['ties_correct']} | {wl['ties_incorrect']} | {wl['net_delta']:+d} |"
        )
    sections.append(header + "\n".join(rows))

    # v2 vs v1
    if "v2_optimized" in test_results and "v1_curated" in test_results:
        header2 = "\n\n### v2_optimized vs v1_curated (Test Set)\n\n"
        header2 += "| Comparison | Wins | Losses | Ties (correct) | Ties (wrong) |\n"
        header2 += "|-----------|------|--------|----------------|-------------|\n"
        wl = compute_paired_win_loss(test_results["v1_curated"], test_results["v2_optimized"])
        sections.append(
            header2 + f"| v2 vs v1 | {wl['wins']} | {wl['losses']} | "
            f"{wl['ties_correct']} | {wl['ties_incorrect']} |"
        )

    return "\n".join(sections) + "\n"


def _build_dev_test_gap(dev_results: dict, test_results: dict, questions: list[dict]) -> str:
    """Build dev-to-test gap table (descriptive signal only)."""
    dev_qs = [q for q in questions if q["split"] == "dev"]
    test_qs = [q for q in questions if q["split"] == "test"]

    header = "### Dev-to-Test Gap (Descriptive Signal)\n\n"
    header += "> At ~10 test questions, one question = ~10% swing. Treat as directional signal, not pass/fail.\n\n"
    header += "| Condition | Dev Accuracy | Test Accuracy | Gap |\n"
    header += "|-----------|-------------|--------------|-----|\n"

    rows = []
    for cond in CONDITIONS:
        dev_acc = compute_accuracy(dev_results.get(cond, {}), dev_qs)
        test_acc = compute_accuracy(test_results.get(cond, {}), test_qs)
        gap = dev_acc - test_acc
        rows.append(
            f"| {cond} | {_accuracy_str(dev_acc)} | {_accuracy_str(test_acc)} | {gap:+.0%} |"
        )

    return header + "\n".join(rows) + "\n"


def _build_hypothesis_check(test_results: dict, questions: list[dict]) -> str:
    """Build hypothesis check section."""
    test_qs = [q for q in questions if q["split"] == "test"]
    accs = {}
    for cond in CONDITIONS:
        if cond in test_results:
            accs[cond] = compute_accuracy(test_results[cond], test_qs)

    expected = "v2_optimized > v1_curated > generic_scaffold >= baseline >= v0_self_generated"
    observed_parts = [f"{cond}: {_accuracy_str(acc)}" for cond, acc in sorted(accs.items(), key=lambda x: -x[1])]
    observed = ", ".join(observed_parts)

    return f"""## Hypothesis Check

```
Expected: {expected}
Observed: {observed}
```

**Note:** These are directional findings from a small sample (~{len(test_qs)} test questions). Statistical significance testing requires a larger dataset (Phase 2).
"""


def _build_per_question_table(test_results: dict, questions: list[dict]) -> str:
    """Build per-question test results table with outcome labels vs baseline."""
    test_qs = sorted(
        [q for q in questions if q["split"] == "test"],
        key=lambda q: q["id"]
    )

    # Compute outcome labels for each non-baseline condition vs baseline
    baseline_results = test_results.get("baseline", {})
    non_baseline = [c for c in CONDITIONS if c != "baseline"]
    outcome_labels = {}
    for cond in non_baseline:
        if cond in test_results:
            outcome_labels[cond] = compute_outcome_labels(baseline_results, test_results[cond])

    # Short display names for the outcome label columns
    label_short = {
        "improved": "+",
        "degraded": "-",
        "no_change_correct": "=ok",
        "no_change_incorrect": "=fail",
    }

    header = "## Per-Question Test Results\n\n"
    header += "| QID | Type | Baseline | Scaffold | v0 | v1 | v2 | Correct | vs_base(scaffold) | vs_base(v0) | vs_base(v1) | vs_base(v2) |\n"
    header += "|-----|------|----------|----------|----|----|----|---------|--------------------|-------------|-------------|-------------|\n"

    rows = []
    for q in test_qs:
        qid = q["id"]
        qtype = q["task_type"]
        correct = q["correct_answer"]

        cells = [qid, qtype]
        for cond in CONDITIONS:
            cond_r = test_results.get(cond, {}).get(qid, {})
            extracted = cond_r.get("extracted", "—")
            outcome = cond_r.get("outcome", "—")
            if outcome == "correct":
                cells.append(f"{extracted}")
            elif outcome == "incorrect":
                cells.append(f"~~{extracted}~~")
            else:
                cells.append("—")
        cells.append(correct)

        # Append outcome labels vs baseline for each non-baseline condition
        for cond in non_baseline:
            label = outcome_labels.get(cond, {}).get(qid, "—")
            cells.append(label_short.get(label, label))

        rows.append("| " + " | ".join(cells) + " |")

    return header + "\n".join(rows) + "\n"


def _build_changelog(changelogs: dict) -> str:
    """Build skill optimization diff section."""
    section = "## Skill Optimization Diff (v1 -> v2)\n\n"

    for task_type, changelog in changelogs.items():
        display_name = task_type.replace("_", " ").title()
        section += f"### {display_name}\n\n{changelog}\n\n"

    return section


def _build_case_studies(test_results: dict, questions: list[dict]) -> str:
    """Build case studies section — pick notable success and failure cases."""
    test_qs = {q["id"]: q for q in questions if q["split"] == "test"}
    section = "## Case Studies\n\n"

    # Find success cases: baseline wrong, v1 or v2 correct
    successes = []
    failures = []
    for qid, q in test_qs.items():
        baseline_correct = test_results.get("baseline", {}).get(qid, {}).get("outcome") == "correct"
        v1_correct = test_results.get("v1_curated", {}).get(qid, {}).get("outcome") == "correct"
        v2_correct = test_results.get("v2_optimized", {}).get(qid, {}).get("outcome") == "correct"
        scaffold_correct = test_results.get("generic_scaffold", {}).get(qid, {}).get("outcome") == "correct"

        if not baseline_correct and v1_correct:
            successes.append(("skill_helped", qid, q))
        if not v1_correct and v2_correct:
            successes.append(("optimization_helped", qid, q))
        if not baseline_correct and not scaffold_correct and v1_correct:
            successes.append(("domain_over_scaffold", qid, q))
        if baseline_correct and not v1_correct:
            failures.append(("skill_hurt", qid, q))
        if v1_correct and not v2_correct:
            failures.append(("optimization_regressed", qid, q))

    # Report up to 3 successes
    reported = set()
    for label, qid, q in successes[:6]:
        if qid in reported:
            continue
        reported.add(qid)
        if len(reported) > 3:
            break
        baseline_ans = test_results.get("baseline", {}).get(qid, {}).get("extracted", "—")
        v1_ans = test_results.get("v1_curated", {}).get(qid, {}).get("extracted", "—")
        v2_ans = test_results.get("v2_optimized", {}).get(qid, {}).get("extracted", "—")
        section += f"### Success: {label} ({qid})\n\n"
        section += f"- Correct answer: {q['correct_answer']}\n"
        section += f"- Baseline: {baseline_ans}, v1: {v1_ans}, v2: {v2_ans}\n\n"

    # Report up to 3 failures
    reported_fail = set()
    for label, qid, q in failures[:6]:
        if qid in reported_fail:
            continue
        reported_fail.add(qid)
        if len(reported_fail) > 3:
            break
        baseline_ans = test_results.get("baseline", {}).get(qid, {}).get("extracted", "—")
        v1_ans = test_results.get("v1_curated", {}).get(qid, {}).get("extracted", "—")
        v2_ans = test_results.get("v2_optimized", {}).get(qid, {}).get("extracted", "—")
        section += f"### Failure: {label} ({qid})\n\n"
        section += f"- Correct answer: {q['correct_answer']}\n"
        section += f"- Baseline: {baseline_ans}, v1: {v1_ans}, v2: {v2_ans}\n\n"

    if not successes and not failures:
        section += "*No notable case studies identified.*\n"

    return section


def generate_report(
    dev_results: dict,
    test_results: dict,
    dev_analysis: dict,
    skills: dict,
    changelogs: dict,
    dataset_label: str,
    run_id: str,
    model_name: str,
    questions: list[dict],
    provenance: dict | None = None,
) -> str:
    """Generate the full markdown report.

    Saves to docs/03_results_and_analysis.md.

    Returns:
        The markdown report string.
    """
    sections = [
        f"<!-- AUTO-GENERATED from run {run_id}; DO NOT EDIT BY HAND -->\n",
        "# Results and Analysis\n",
        _build_overview(run_id, model_name, dataset_label, questions),
        "## Development Set Results\n\n"
        "> These results are used for error analysis and skill optimization.\n"
        "> They are NOT the primary evidence for claims.\n",
        _build_accuracy_table(dev_results, [q for q in questions if q["split"] == "dev"], "Dev"),
        _build_root_cause_table(dev_analysis),
        "## Held-Out Test Set Results\n\n"
        "> **This is the primary evidence for all claims.**\n"
        "> The optimizer never saw test set questions, answers, or failures.\n",
        _build_accuracy_table(test_results, [q for q in questions if q["split"] == "test"], "Test"),
        _build_paired_tables(test_results),
        _build_dev_test_gap(dev_results, test_results, questions),
        _build_hypothesis_check(test_results, questions),
        _build_per_question_table(test_results, questions),
        _build_changelog(changelogs),
        _build_case_studies(test_results, questions),
    ]

    report = "\n".join(sections)

    # Save report to run-scoped directory
    run_report_path = Path(f"results/runs/{run_id}/report.md")
    run_report_path.parent.mkdir(parents=True, exist_ok=True)
    run_report_path.write_text(report)

    # Also save to docs/ as the canonical latest report
    docs_path = Path("docs/03_results_and_analysis.md")
    docs_path.parent.mkdir(parents=True, exist_ok=True)
    docs_path.write_text(report)

    return report


def generate_marketplace_cards(
    test_results: dict,
    dev_results: dict,
    skills: dict,
    changelogs: dict,
    dataset_label: str,
    model_name: str,
    questions: list[dict],
    run_id: str = "latest",
    provenance: dict | None = None,
) -> None:
    """Generate demo marketplace cards for each task type.

    Saves to results/runs/{run_id}/marketplace_cards/{task_type}.yaml.
    """
    output_dir = Path(f"results/runs/{run_id}/marketplace_cards")
    output_dir.mkdir(parents=True, exist_ok=True)

    dev_qs = [q for q in questions if q["split"] == "dev"]
    test_qs = [q for q in questions if q["split"] == "test"]
    task_types = sorted(set(q["task_type"] for q in questions))

    for task_type in task_types:
        dev_accs = {}
        test_accs = {}
        for cond in CONDITIONS:
            dev_accs[cond] = round(compute_accuracy(dev_results.get(cond, {}), dev_qs, task_type), 2)
            test_accs[cond] = round(compute_accuracy(test_results.get(cond, {}), test_qs, task_type), 2)

        v2_dev = dev_accs.get("v2_optimized", 0)
        v2_test = test_accs.get("v2_optimized", 0)

        card = {
            "_note": (
                "This is demo metadata showing the schema format. "
                "Evidence strength is demo-level and requires cross-model, "
                "larger-sample validation before marketplace publication."
            ),
            "_provenance": provenance if provenance else {},
            "asset_name": f"or-{task_type.replace('_', '-')}",
            "asset_type": "capsule",
            "domain": "operations_research",
            "supported_models": [model_name],
            "evidence": {
                "benchmark": dataset_label,
                "evidence_level": "demo",
                "methodology": {
                    "dev_test_split": True,
                    "scaffold_controlled": True,
                    "optimizer_blind_to_test": True,
                },
                "dev_set": {
                    "n_tasks": len([q for q in dev_qs if q["task_type"] == task_type]),
                    "conditions": {cond: {"accuracy": dev_accs[cond]} for cond in CONDITIONS},
                },
                "test_set": {
                    "n_tasks": len([q for q in test_qs if q["task_type"] == task_type]),
                    "conditions": {cond: {"accuracy": test_accs[cond]} for cond in CONDITIONS},
                },
                "dev_test_gap": f"v2 dev: {v2_dev:.0%}, test: {v2_test:.0%}",
            },
            "version_history": [],
            "quality_signals": {
                "verification_type": "exact_match",
                "reproducibility": "temperature 0; full determinism not guaranteed on hosted APIs",
            },
            "limitations": [
                f"Demo-level sample size (~{len([q for q in test_qs if q['task_type'] == task_type])} test questions) — directional evidence only",
                "Single model validation — cross-model testing required",
                "Single-turn QA — agent-level task execution not validated",
                "No statistical significance testing at this sample size",
            ],
        }

        # Add version history from changelogs
        if task_type in (skills.get("v1_curated", {}) or {}):
            card["version_history"].append({
                "version": "v1_curated",
                "author": "human",
                "note": "Initial domain-specific skill design",
            })
        if task_type in changelogs:
            card["version_history"].append({
                "version": "v2_optimized",
                "author": model_name,
                "note": changelogs[task_type][:200],  # truncate if long
            })

        card_path = output_dir / f"{task_type}.yaml"
        with open(card_path, "w") as f:
            yaml.dump(card, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
