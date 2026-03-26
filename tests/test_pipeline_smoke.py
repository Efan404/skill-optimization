"""Fake-LLM pipeline smoke test — validates the full pipeline flow without real API calls.

Tests that the pipeline phases (load -> run -> evaluate) work end-to-end using
a FakeLLMClient, and that split boundaries are respected.
"""

import pytest

from src.task_loader import load_questions, validate_split_integrity
from src.agent_runner import run_condition, run_single, build_prompt
from src.evaluator import evaluate_condition, extract_answer
from src.error_analyzer import analyze_single_failure
from src.skill_optimizer import optimize_skill


# ---------------------------------------------------------------------------
# FakeLLMClient
# ---------------------------------------------------------------------------


class FakeLLMClient:
    """Mimics LLMClient interface without making real API calls."""

    def __init__(self, model_name="fake", run_id="test_run"):
        self.config = {"model": "fake-model", "base_url": "http://fake"}
        self.run_id = run_id
        self._call_count = 0

    def chat(self, messages, purpose="", response_format=None):
        self._call_count += 1
        # Return a canned response that always picks "A"
        return {
            "response": "Based on my analysis, the answer is clear.\n\nANSWER: A",
            "model": "fake-model",
            "tokens_used": 100,
            "request_id": f"fake_{self._call_count}",
        }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_client():
    """Fresh FakeLLMClient for each test."""
    return FakeLLMClient()


@pytest.fixture
def all_questions():
    """All ORQA questions from data/orqa/questions.json."""
    return load_questions()


@pytest.fixture
def dev_questions():
    """Dev-split questions only."""
    return load_questions(split="dev")


@pytest.fixture
def test_questions():
    """Test-split questions only."""
    return load_questions(split="test")


@pytest.fixture
def seed_questions():
    """Seed-split questions only."""
    return load_questions(split="seed")


# ---------------------------------------------------------------------------
# G2.2: Core pipeline flow tests
# ---------------------------------------------------------------------------


class TestSplitIntegrity:
    """validate_split_integrity() passes on real data."""

    def test_split_integrity_passes(self):
        assert validate_split_integrity() is True


class TestRunCondition:
    """run_condition() produces results for all questions using FakeLLMClient."""

    def test_run_condition_baseline_all_questions(self, fake_client, dev_questions):
        results = run_condition(fake_client, dev_questions, "baseline")
        # Every dev question should have a result
        assert len(results) == len(dev_questions)
        for q in dev_questions:
            assert q["id"] in results
            assert results[q["id"]]["response"] != ""
            assert results[q["id"]]["condition"] == "baseline"

    def test_run_condition_records_model(self, fake_client, dev_questions):
        results = run_condition(fake_client, dev_questions, "baseline")
        for qid, result in results.items():
            assert result["model"] == "fake-model"

    def test_run_condition_increments_call_count(self, fake_client, dev_questions):
        run_condition(fake_client, dev_questions, "baseline")
        assert fake_client._call_count == len(dev_questions)


class TestEvaluateCondition:
    """evaluate_condition() produces outcomes for all questions."""

    def test_evaluate_returns_outcomes_for_all(self, fake_client, dev_questions):
        # Run the pipeline first
        run_results = run_condition(fake_client, dev_questions, "baseline")
        # Build responses dict: {question_id: raw_response_string}
        responses = {qid: r["response"] for qid, r in run_results.items()}
        # Evaluate
        outcomes = evaluate_condition(dev_questions, responses)
        assert len(outcomes) == len(dev_questions)
        for q in dev_questions:
            assert q["id"] in outcomes
            assert outcomes[q["id"]]["outcome"] in ("correct", "incorrect", "extraction_failed")

    def test_evaluate_extracts_answer_from_fake(self, fake_client, dev_questions):
        """FakeLLMClient always answers 'A', so extraction should always yield 'A'."""
        run_results = run_condition(fake_client, dev_questions, "baseline")
        responses = {qid: r["response"] for qid, r in run_results.items()}
        outcomes = evaluate_condition(dev_questions, responses)
        for q in dev_questions:
            assert outcomes[q["id"]]["extracted"] == "A"


class TestExtractAnswer:
    """extract_answer() correctly parses the fake LLM response."""

    def test_extract_a_from_fake_response(self):
        fake_response = "Based on my analysis, the answer is clear.\n\nANSWER: A"
        assert extract_answer(fake_response) == "A"

    def test_extract_returns_none_for_empty(self):
        assert extract_answer("") is None

    def test_extract_returns_none_for_garbage(self):
        assert extract_answer("no answer here at all, just text with no letter") is None


class TestSeedQuestionsNotEvaluated:
    """Seed questions should be excluded from evaluation runs (split boundary)."""

    def test_seed_ids_not_in_dev(self, seed_questions, dev_questions):
        seed_ids = {q["id"] for q in seed_questions}
        dev_ids = {q["id"] for q in dev_questions}
        assert seed_ids.isdisjoint(dev_ids), "Seed IDs overlap with dev IDs"

    def test_seed_ids_not_in_test(self, seed_questions, test_questions):
        seed_ids = {q["id"] for q in seed_questions}
        test_ids = {q["id"] for q in test_questions}
        assert seed_ids.isdisjoint(test_ids), "Seed IDs overlap with test IDs"

    def test_run_condition_on_dev_excludes_seed(self, fake_client, dev_questions, seed_questions):
        """Running on dev questions should produce zero results for seed IDs."""
        results = run_condition(fake_client, dev_questions, "baseline")
        seed_ids = {q["id"] for q in seed_questions}
        for sid in seed_ids:
            assert sid not in results, f"Seed question {sid} found in dev results"


# ---------------------------------------------------------------------------
# G2.3: Split isolation tests
# ---------------------------------------------------------------------------


class TestErrorAnalyzerSplitIsolation:
    """error_analyzer.analyze_single_failure() rejects non-dev questions."""

    def test_rejects_test_split_question(self, fake_client, test_questions):
        """analyze_single_failure raises ValueError for a test-split question."""
        test_q = test_questions[0]
        assert test_q["split"] == "test"
        with pytest.raises(ValueError, match="split"):
            analyze_single_failure(
                client=fake_client,
                question=test_q,
                response="ANSWER: A",
                condition="baseline",
            )

    def test_rejects_seed_split_question(self, fake_client, seed_questions):
        """analyze_single_failure raises ValueError for a seed-split question."""
        seed_q = seed_questions[0]
        assert seed_q["split"] == "seed"
        with pytest.raises(ValueError, match="split"):
            analyze_single_failure(
                client=fake_client,
                question=seed_q,
                response="ANSWER: A",
                condition="baseline",
            )

    def test_accepts_dev_split_question(self, fake_client, dev_questions):
        """analyze_single_failure does NOT raise for a dev-split question."""
        dev_q = dev_questions[0]
        assert dev_q["split"] == "dev"
        # Should not raise — FakeLLMClient returns parseable JSON-like response
        # but the error analyzer expects JSON output. It will fall back gracefully.
        result = analyze_single_failure(
            client=fake_client,
            question=dev_q,
            response="ANSWER: A",
            condition="baseline",
        )
        assert "root_causes" in result
        assert "explanation" in result


class TestSkillOptimizerSplitIsolation:
    """skill_optimizer.optimize_skill() rejects non-dev items."""

    def test_rejects_test_split_failure_item(self, fake_client, test_questions):
        """optimize_skill raises ValueError when failure item has test-split question."""
        test_q = test_questions[0]
        failure_item = {
            "question": test_q,
            "response": "ANSWER: B",
            "root_causes": ["wrong_reasoning"],
            "explanation": "test failure",
        }
        current_skill = {"name": "test_skill", "procedure": []}
        with pytest.raises(ValueError, match="split"):
            optimize_skill(
                client=fake_client,
                current_skill=current_skill,
                dev_failures=[failure_item],
                dev_successes=[],
                task_type="or_model_identification",
            )

    def test_rejects_test_split_success_item(self, fake_client, test_questions):
        """optimize_skill raises ValueError when success item has test-split question."""
        test_q = test_questions[0]
        success_item = {
            "question": test_q,
            "response": "ANSWER: A",
        }
        current_skill = {"name": "test_skill", "procedure": []}
        with pytest.raises(ValueError, match="split"):
            optimize_skill(
                client=fake_client,
                current_skill=current_skill,
                dev_failures=[],
                dev_successes=[success_item],
                task_type="or_model_identification",
            )

    def test_rejects_seed_split_item(self, fake_client, seed_questions):
        """optimize_skill raises ValueError when item has seed-split question."""
        seed_q = seed_questions[0]
        failure_item = {
            "question": seed_q,
            "response": "ANSWER: B",
            "root_causes": ["wrong_reasoning"],
            "explanation": "seed failure",
        }
        current_skill = {"name": "test_skill", "procedure": []}
        with pytest.raises(ValueError, match="split"):
            optimize_skill(
                client=fake_client,
                current_skill=current_skill,
                dev_failures=[failure_item],
                dev_successes=[],
                task_type="or_model_identification",
            )


# ---------------------------------------------------------------------------
# G2.4: Build prompt smoke tests (no LLM call needed)
# ---------------------------------------------------------------------------


class TestBuildPrompt:
    """build_prompt produces valid message lists without calling LLM."""

    def test_baseline_prompt_has_context(self, dev_questions):
        q = dev_questions[0]
        messages = build_prompt(q, "baseline")
        assert len(messages) == 1
        assert q["context"] in messages[0]["content"]
        assert q["question"] in messages[0]["content"]

    def test_invalid_condition_raises(self, dev_questions):
        with pytest.raises(ValueError, match="Unknown condition"):
            build_prompt(dev_questions[0], "nonexistent_condition")
