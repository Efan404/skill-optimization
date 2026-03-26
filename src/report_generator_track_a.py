"""Report generator for the ORQA Track A ablation."""

from pathlib import Path

from src.report_generator import compute_accuracy, compute_paired_win_loss


TRACK_A_CONDITIONS = [
    "baseline",
    "generic_scaffold",
    "v1_curated",
    "v1_component_minimal",
    "v1_component_enriched",
]

TRACK_A_COMPARISONS = [
    ("v1_component_minimal", "generic_scaffold"),
    ("v1_component_enriched", "generic_scaffold"),
    ("v1_component_minimal", "v1_curated"),
    ("v1_component_enriched", "v1_curated"),
]


def _accuracy_str(acc: float) -> str:
    return f"{acc:.0%}"


def _build_accuracy_table(title: str, questions: list[dict], results: dict) -> str:
    header = f"### {title}\n\n| Condition | Accuracy |\n|-----------|----------|\n"
    rows = []
    for condition in TRACK_A_CONDITIONS:
        acc = compute_accuracy(results.get(condition, {}), questions)
        rows.append(f"| {condition} | {_accuracy_str(acc)} |")
    return header + "\n".join(rows) + "\n"


def _build_baseline_comparison_table(test_results: dict, test_ids: list[str]) -> str:
    header = (
        "### Paired Win/Loss vs Baseline\n\n"
        "| Condition vs Baseline | Wins | Losses | Ties (correct) | Ties (wrong) | Net |\n"
        "|----------------------|------|--------|----------------|-------------|-----|\n"
    )
    rows = []
    baseline = test_results["baseline"]
    for condition in TRACK_A_CONDITIONS:
        if condition == "baseline":
            continue
        wl = compute_paired_win_loss(baseline, test_results.get(condition, {}), test_ids)
        rows.append(
            f"| {condition} | {wl['wins']} | {wl['losses']} | "
            f"{wl['ties_correct']} | {wl['ties_incorrect']} | {wl['net_delta']:+d} |"
        )
    return header + "\n".join(rows) + "\n"


def _build_direct_comparison_table(test_results: dict, test_ids: list[str]) -> str:
    header = (
        "### Direct Track A Comparisons\n\n"
        "| Comparison | Wins | Losses | Ties (correct) | Ties (wrong) | Net |\n"
        "|-----------|------|--------|----------------|-------------|-----|\n"
    )
    rows = []
    for challenger, reference in TRACK_A_COMPARISONS:
        wl = compute_paired_win_loss(
            test_results.get(reference, {}),
            test_results.get(challenger, {}),
            test_ids,
        )
        rows.append(
            f"| {challenger} vs {reference} | {wl['wins']} | {wl['losses']} | "
            f"{wl['ties_correct']} | {wl['ties_incorrect']} | {wl['net_delta']:+d} |"
        )
    return header + "\n".join(rows) + "\n"


def _build_dev_root_cause_table(dev_analysis: dict) -> str:
    codes = sorted(
        {
            code
            for condition in TRACK_A_CONDITIONS
            for item in dev_analysis.get(condition, {}).values()
            for code in item.get("root_causes", [])
        }
    )
    if not codes:
        return "### Dev Root Cause Distribution\n\nNo root causes recorded.\n"

    header = (
        "### Dev Root Cause Distribution\n\n"
        "| Root Cause | " + " | ".join(TRACK_A_CONDITIONS) + " |\n"
        "|-----------|" + "|".join(["----"] * len(TRACK_A_CONDITIONS)) + "|\n"
    )
    rows = []
    for code in codes:
        counts = []
        for condition in TRACK_A_CONDITIONS:
            count = sum(
                1
                for item in dev_analysis.get(condition, {}).values()
                if code in item.get("root_causes", [])
            )
            counts.append(str(count) if count else "—")
        rows.append(f"| {code} | " + " | ".join(counts) + " |")
    return header + "\n".join(rows) + "\n"


def generate_track_a_report(
    dev_results: dict,
    test_results: dict,
    dev_analysis: dict,
    questions: list[dict],
    run_id: str,
    model_name: str,
    dataset_label: str,
) -> str:
    """Generate and persist a markdown report for Track A."""
    dev_questions = [q for q in questions if q["split"] == "dev"]
    test_questions = [q for q in questions if q["split"] == "test"]
    test_ids = [q["id"] for q in test_questions]

    report = f"""# ORQA Track A Report

- **Run ID:** `{run_id}`
- **Model:** `{model_name}`
- **Dataset:** {dataset_label}
- **Conditions:** {", ".join(TRACK_A_CONDITIONS)}

## Accuracy

{_build_accuracy_table("Dev Accuracy Summary", dev_questions, dev_results)}

{_build_accuracy_table("Test Accuracy Summary", test_questions, test_results)}

## Comparisons

{_build_baseline_comparison_table(test_results, test_ids)}

{_build_direct_comparison_table(test_results, test_ids)}

## Error Analysis

{_build_dev_root_cause_table(dev_analysis)}
"""

    output_path = Path(f"results/runs/{run_id}/track_a_report.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report)
    return report
