"""Tests for the dedicated ORQA Track A runner."""

from pathlib import Path

import src.run_track_a as run_track_a_module
from src.run_track_a import TRACK_A_CONDITIONS, build_track_a_metadata


def test_track_a_condition_order():
    """Track A should evaluate only baseline, scaffold, v1, A1, and A2."""
    assert TRACK_A_CONDITIONS == [
        "baseline",
        "generic_scaffold",
        "v1_curated",
        "v1_component_minimal",
        "v1_component_enriched",
    ]


def test_track_a_conditions_exclude_phase1_generation_and_optimization():
    """Track A should not run v0 self-generation or v2 optimization."""
    assert "v0_self_generated" not in TRACK_A_CONDITIONS
    assert "v2_optimized" not in TRACK_A_CONDITIONS


def test_build_track_a_metadata_uses_track_a_conditions():
    """Metadata should record the exact Track A condition set."""
    metadata = build_track_a_metadata(
        run_id="track_a_test",
        model_name="step_2_mini",
        git_commit="abc123",
        data_digest="sha256:test",
        split_counts={"seed": 5, "dev": 25, "test": 20},
        dataset_label="ORQA subset",
    )
    assert metadata["conditions_run"] == TRACK_A_CONDITIONS
    assert metadata["model"] == "step_2_mini"
    assert metadata["run_id"] == "track_a_test"


def test_run_track_a_writes_report(monkeypatch, tmp_path):
    """Runner should invoke the Track A report generator after evaluations."""
    monkeypatch.chdir(tmp_path)

    questions = [
        {"id": "q1", "split": "dev", "task_type": "or_model_identification", "correct_answer": "A"},
        {"id": "q2", "split": "test", "task_type": "or_model_identification", "correct_answer": "A"},
    ]

    class FakeClient:
        config = {"model": "fake-model"}

        def __init__(self, model_name, run_id):
            self.model_name = model_name
            self.run_id = run_id

    def fake_load_questions(split=None):
        if split is None:
            return questions
        return [q for q in questions if q["split"] == split]

    def fake_get_questions_by_type(split, task_type):
        return [q for q in questions if q["split"] == split and q["task_type"] == task_type]

    def fake_run_condition(client, split_questions, condition, skill):
        return {
            q["id"]: {
                "question_id": q["id"],
                "condition": condition,
                "response": "ANSWER: A",
                "model": "fake-model",
                "tokens_used": 1,
            }
            for q in split_questions
        }

    def fake_evaluate_condition(split_questions, raw_responses):
        return {
            q["id"]: {"outcome": "correct", "extracted": "A"}
            for q in split_questions
        }

    def fake_generate_track_a_report(**kwargs):
        report_path = Path(f"results/runs/{kwargs['run_id']}/track_a_report.md")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("track a report")
        return "track a report"

    monkeypatch.setattr(run_track_a_module, "LLMClient", FakeClient)
    monkeypatch.setattr(run_track_a_module, "load_questions", fake_load_questions)
    monkeypatch.setattr(run_track_a_module, "get_questions_by_type", fake_get_questions_by_type)
    monkeypatch.setattr(run_track_a_module, "run_condition", fake_run_condition)
    monkeypatch.setattr(run_track_a_module, "evaluate_condition", fake_evaluate_condition)
    monkeypatch.setattr(run_track_a_module, "analyze_dev_failures", lambda client, questions, results: {})
    monkeypatch.setattr(run_track_a_module, "get_skill_for_condition", lambda condition, task_type: None if condition == "baseline" else {"name": condition})
    monkeypatch.setattr(run_track_a_module, "validate_split_integrity", lambda: True)
    monkeypatch.setattr(run_track_a_module, "get_dataset_label", lambda: "ORQA subset")
    monkeypatch.setattr(run_track_a_module, "_get_git_commit", lambda: "abc123")
    monkeypatch.setattr(run_track_a_module, "_compute_data_digest", lambda: "sha256:test")
    monkeypatch.setattr(
        run_track_a_module,
        "validate_scaffold_length",
        lambda curated, scaffold: (True, {"v1_tokens": 100, "scaffold_tokens": 95, "ratio": 0.95}),
    )
    monkeypatch.setattr(run_track_a_module, "generate_track_a_report", fake_generate_track_a_report)

    run_track_a_module.run_track_a(model_name="step_2_mini", run_id="track_a_runner_test")

    report_path = Path("results/runs/track_a_runner_test/track_a_report.md")
    assert report_path.exists()
    assert report_path.read_text() == "track a report"
