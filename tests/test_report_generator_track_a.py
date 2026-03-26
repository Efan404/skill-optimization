"""Tests for the Track A report generator."""

from pathlib import Path

from src.report_generator_track_a import generate_track_a_report


def _results(correct_ids: set[str], all_ids: list[str]) -> dict:
    data = {}
    for qid in all_ids:
        if qid in correct_ids:
            data[qid] = {"outcome": "correct", "extracted": "A"}
        else:
            data[qid] = {"outcome": "incorrect", "extracted": "B"}
    return data


def test_generate_track_a_report_includes_required_sections(tmp_path, monkeypatch):
    """Track A report should summarize the five conditions and direct comparisons."""
    monkeypatch.chdir(tmp_path)

    questions = [
        {"id": "q1", "split": "dev", "task_type": "or_model_identification", "correct_answer": "A", "question_subtype": "Q4"},
        {"id": "q2", "split": "dev", "task_type": "or_model_identification", "correct_answer": "A", "question_subtype": "Q8"},
        {"id": "q3", "split": "test", "task_type": "or_model_identification", "correct_answer": "A", "question_subtype": "Q9"},
        {"id": "q4", "split": "test", "task_type": "or_model_identification", "correct_answer": "A", "question_subtype": "Q2"},
    ]

    dev_results = {
        "baseline": _results({"q1"}, ["q1", "q2"]),
        "generic_scaffold": _results({"q1"}, ["q1", "q2"]),
        "v1_curated": _results({"q1", "q2"}, ["q1", "q2"]),
        "v1_component_minimal": _results({"q2"}, ["q1", "q2"]),
        "v1_component_enriched": _results({"q1", "q2"}, ["q1", "q2"]),
    }
    test_results = {
        "baseline": _results({"q3"}, ["q3", "q4"]),
        "generic_scaffold": _results({"q3"}, ["q3", "q4"]),
        "v1_curated": _results({"q3", "q4"}, ["q3", "q4"]),
        "v1_component_minimal": _results({"q4"}, ["q3", "q4"]),
        "v1_component_enriched": _results({"q3", "q4"}, ["q3", "q4"]),
    }
    dev_analysis = {
        "baseline": {"q2": {"root_causes": ["wrong_reasoning"]}},
        "generic_scaffold": {"q2": {"root_causes": ["wrong_reasoning"]}},
        "v1_curated": {},
        "v1_component_minimal": {"q1": {"root_causes": ["skill_mismatch"]}},
        "v1_component_enriched": {},
    }

    report = generate_track_a_report(
        dev_results=dev_results,
        test_results=test_results,
        dev_analysis=dev_analysis,
        questions=questions,
        run_id="track_a_report_test",
        model_name="step-2-mini",
        dataset_label="ORQA subset",
    )

    assert "baseline" in report
    assert "generic_scaffold" in report
    assert "v1_curated" in report
    assert "v1_component_minimal" in report
    assert "v1_component_enriched" in report
    assert "### Dev Accuracy Summary" in report
    assert "### Test Accuracy Summary" in report
    assert "v1_component_minimal vs generic_scaffold" in report
    assert "v1_component_enriched vs generic_scaffold" in report
    assert "v1_component_minimal vs v1_curated" in report
    assert "v1_component_enriched vs v1_curated" in report

    report_path = Path("results/runs/track_a_report_test/track_a_report.md")
    assert report_path.exists()
    assert report_path.read_text() == report
