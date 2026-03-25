"""Tests for evaluator module: answer extraction, evaluation, and outcome labels."""

import pytest

from src.evaluator import (
    compute_outcome_labels,
    evaluate_condition,
    evaluate_single,
    extract_answer,
)


# --- extract_answer tests ---


class TestExtractAnswerStandard:
    """Tier 1: ANSWER: X in last 5 lines."""

    def test_answer_colon_at_end(self):
        response = "Some reasoning here.\nANSWER: B"
        assert extract_answer(response) == "B"

    def test_answer_colon_with_extra_whitespace(self):
        response = "Some reasoning.\nANSWER:   C"
        assert extract_answer(response) == "C"

    def test_answer_colon_not_in_last_5_lines_falls_through(self):
        """ANSWER: A on line 1 of a 10-line response shouldn't be caught by tier 1."""
        lines = ["ANSWER: A"] + ["filler line"] * 9
        response = "\n".join(lines)
        # Tier 1 checks last 5 lines only; line 1 is outside that window.
        # But tier 2 (fallback) should still catch it.
        assert extract_answer(response) == "A"

    def test_answer_colon_within_last_5_lines(self):
        lines = ["filler"] * 5 + ["ANSWER: D"] + ["some trailing text"]
        response = "\n".join(lines)
        assert extract_answer(response) == "D"


class TestExtractAnswerFallback:
    """Tier 2: case-insensitive (?:answer|choice|option) is/: X."""

    def test_the_answer_is(self):
        response = "After analysis, the answer is C. That's my final conclusion."
        assert extract_answer(response) == "C"

    def test_choice_is(self):
        response = "Based on the constraints, the choice is A."
        assert extract_answer(response) == "A"

    def test_option_colon(self):
        response = "The best option: D\nLet me verify."
        assert extract_answer(response) == "D"

    def test_case_insensitive(self):
        response = "THE ANSWER IS B"
        assert extract_answer(response) == "B"

    def test_answer_is_lowercase(self):
        response = "I think the answer is d based on my reasoning."
        assert extract_answer(response) == "D"


class TestExtractAnswerLastLetter:
    """Tier 3: response ends with a single A-D letter."""

    def test_ends_with_d(self):
        response = "After careful analysis...\nD"
        assert extract_answer(response) == "D"

    def test_ends_with_a_and_whitespace(self):
        response = "My pick is\nA  "
        assert extract_answer(response) == "A"

    def test_lowercase_last_letter(self):
        response = "My conclusion:\nb"
        assert extract_answer(response) == "B"


class TestExtractAnswerFailure:
    """All tiers fail -> None."""

    def test_no_answer_at_all(self):
        response = "I'm not sure about this problem. It seems complex."
        assert extract_answer(response) is None

    def test_empty_response(self):
        assert extract_answer("") is None

    def test_letter_not_abcd(self):
        response = "The answer is E"
        assert extract_answer(response) is None

    def test_only_whitespace(self):
        assert extract_answer("   \n\n  ") is None


# --- evaluate_single tests ---


class TestEvaluateSingle:
    def test_correct(self):
        assert evaluate_single("B", "B") == "correct"

    def test_incorrect(self):
        assert evaluate_single("A", "B") == "incorrect"

    def test_extraction_failed(self):
        assert evaluate_single(None, "B") == "extraction_failed"

    def test_correct_case_insensitive(self):
        """Extracted and correct should compare equal regardless of case."""
        assert evaluate_single("b", "B") == "correct"


# --- compute_outcome_labels tests ---


class TestComputeOutcomeLabels:
    def test_improved(self):
        """Baseline wrong, condition correct -> improved."""
        baseline = {"q1": {"outcome": "incorrect"}}
        condition = {"q1": {"outcome": "correct"}}
        labels = compute_outcome_labels(baseline, condition)
        assert labels["q1"] == "improved"

    def test_degraded(self):
        """Baseline correct, condition wrong -> degraded."""
        baseline = {"q1": {"outcome": "correct"}}
        condition = {"q1": {"outcome": "incorrect"}}
        labels = compute_outcome_labels(baseline, condition)
        assert labels["q1"] == "degraded"

    def test_no_change_correct(self):
        """Both correct -> no_change_correct."""
        baseline = {"q1": {"outcome": "correct"}}
        condition = {"q1": {"outcome": "correct"}}
        labels = compute_outcome_labels(baseline, condition)
        assert labels["q1"] == "no_change_correct"

    def test_no_change_incorrect(self):
        """Both wrong -> no_change_incorrect."""
        baseline = {"q1": {"outcome": "incorrect"}}
        condition = {"q1": {"outcome": "incorrect"}}
        labels = compute_outcome_labels(baseline, condition)
        assert labels["q1"] == "no_change_incorrect"

    def test_extraction_failed_baseline(self):
        """Baseline extraction_failed, condition correct -> improved."""
        baseline = {"q1": {"outcome": "extraction_failed"}}
        condition = {"q1": {"outcome": "correct"}}
        labels = compute_outcome_labels(baseline, condition)
        assert labels["q1"] == "improved"

    def test_extraction_failed_both(self):
        """Both extraction_failed -> no_change_incorrect."""
        baseline = {"q1": {"outcome": "extraction_failed"}}
        condition = {"q1": {"outcome": "extraction_failed"}}
        labels = compute_outcome_labels(baseline, condition)
        assert labels["q1"] == "no_change_incorrect"

    def test_multiple_questions(self):
        baseline = {
            "q1": {"outcome": "correct"},
            "q2": {"outcome": "incorrect"},
            "q3": {"outcome": "correct"},
        }
        condition = {
            "q1": {"outcome": "correct"},
            "q2": {"outcome": "correct"},
            "q3": {"outcome": "incorrect"},
        }
        labels = compute_outcome_labels(baseline, condition)
        assert labels["q1"] == "no_change_correct"
        assert labels["q2"] == "improved"
        assert labels["q3"] == "degraded"


# --- evaluate_condition tests ---


class TestEvaluateCondition:
    def test_basic_evaluation(self):
        questions = [
            {"id": "q1", "correct_answer": "B"},
            {"id": "q2", "correct_answer": "C"},
        ]
        responses = {
            "q1": "After analysis, ANSWER: B",
            "q2": "I think ANSWER: A",
        }
        results = evaluate_condition(questions, responses)
        assert results["q1"]["extracted"] == "B"
        assert results["q1"]["correct"] == "B"
        assert results["q1"]["outcome"] == "correct"
        assert results["q1"]["response"] == "After analysis, ANSWER: B"

        assert results["q2"]["extracted"] == "A"
        assert results["q2"]["correct"] == "C"
        assert results["q2"]["outcome"] == "incorrect"

    def test_missing_response(self):
        questions = [{"id": "q1", "correct_answer": "A"}]
        responses = {}  # no response for q1
        results = evaluate_condition(questions, responses)
        assert results["q1"]["extracted"] is None
        assert results["q1"]["outcome"] == "extraction_failed"

    def test_extraction_failure_in_response(self):
        questions = [{"id": "q1", "correct_answer": "A"}]
        responses = {"q1": "I have no idea what the answer is."}
        results = evaluate_condition(questions, responses)
        assert results["q1"]["extracted"] is None
        assert results["q1"]["outcome"] == "extraction_failed"
