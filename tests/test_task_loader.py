"""Tests for src/task_loader.py — adapted for real ORQA data."""

import pytest
from src.task_loader import (
    load_questions,
    validate_split_integrity,
    get_seed_examples,
    get_dataset_label,
    get_questions_by_type,
)


class TestLoadQuestions:
    def test_load_all_questions(self):
        """All questions load and have required fields."""
        questions = load_questions()
        assert len(questions) == 50
        required_fields = [
            "id", "task_type", "split", "context", "question",
            "choices", "correct_answer", "source_category", "source_detail",
        ]
        for q in questions:
            for field in required_fields:
                assert field in q, f"Missing field '{field}' in question {q.get('id', '?')}"

    def test_load_by_split_seed(self):
        """Filtering by 'seed' returns only seed questions."""
        seed_qs = load_questions(split="seed")
        assert len(seed_qs) == 5
        assert all(q["split"] == "seed" for q in seed_qs)

    def test_load_by_split_dev(self):
        """Filtering by 'dev' returns only dev questions."""
        dev_qs = load_questions(split="dev")
        assert len(dev_qs) == 25
        assert all(q["split"] == "dev" for q in dev_qs)

    def test_load_by_split_test(self):
        """Filtering by 'test' returns only test questions."""
        test_qs = load_questions(split="test")
        assert len(test_qs) == 20
        assert all(q["split"] == "test" for q in test_qs)

    def test_load_invalid_split_raises(self):
        """Invalid split name raises ValueError."""
        with pytest.raises(ValueError, match="Invalid split"):
            load_questions(split="train")

    def test_correct_answer_in_choices(self):
        """Every question's correct_answer is a valid choice key."""
        for q in load_questions():
            assert q["correct_answer"] in q["choices"], (
                f"Question {q['id']}: answer '{q['correct_answer']}' not in choices"
            )

    def test_all_choices_are_abcd(self):
        """Every question has exactly A, B, C, D choices."""
        for q in load_questions():
            assert set(q["choices"].keys()) == {"A", "B", "C", "D"}, (
                f"Question {q['id']} has wrong choice keys: {set(q['choices'].keys())}"
            )

    def test_all_have_context(self):
        """Every ORQA question has a non-empty context field."""
        for q in load_questions():
            assert q.get("context"), f"Question {q['id']} missing or empty context"

    def test_all_have_question_subtype(self):
        """Every question has a question_subtype field (Q1-Q11)."""
        for q in load_questions():
            assert q.get("question_subtype", "").startswith("Q"), (
                f"Question {q['id']} missing or invalid question_subtype"
            )


class TestSplitIntegrity:
    def test_split_integrity_passes(self):
        """Real data passes split integrity check."""
        assert validate_split_integrity() is True

    def test_no_overlap_between_splits(self):
        """Seed, dev, test have no overlapping question IDs."""
        seed_ids = {q["id"] for q in load_questions(split="seed")}
        dev_ids = {q["id"] for q in load_questions(split="dev")}
        test_ids = {q["id"] for q in load_questions(split="test")}
        assert not seed_ids & dev_ids, "Overlap between seed and dev"
        assert not seed_ids & test_ids, "Overlap between seed and test"
        assert not dev_ids & test_ids, "Overlap between dev and test"

    def test_all_ids_covered(self):
        """Every question is in exactly one split."""
        all_qs = load_questions()
        seed_ids = {q["id"] for q in load_questions(split="seed")}
        dev_ids = {q["id"] for q in load_questions(split="dev")}
        test_ids = {q["id"] for q in load_questions(split="test")}
        for q in all_qs:
            count = sum([
                q["id"] in seed_ids,
                q["id"] in dev_ids,
                q["id"] in test_ids,
            ])
            assert count == 1, f"Question {q['id']} in {count} splits"


class TestSeedExamples:
    def test_seed_or_model_id(self):
        """Returns seed questions for or_model_identification."""
        seeds = get_seed_examples("or_model_identification")
        assert len(seeds) == 5
        assert all(q["task_type"] == "or_model_identification" for q in seeds)
        assert all(q["split"] == "seed" for q in seeds)

    def test_seed_covers_multiple_subtypes(self):
        """Seed questions cover at least 3 different question subtypes."""
        seeds = get_seed_examples("or_model_identification")
        subtypes = {q["question_subtype"] for q in seeds}
        assert len(subtypes) >= 3, f"Only {len(subtypes)} subtypes in seed: {subtypes}"

    def test_seed_unknown_type(self):
        """Unknown task type returns empty list."""
        seeds = get_seed_examples("nonexistent_type")
        assert seeds == []


class TestDatasetLabel:
    def test_label_orqa_subset(self):
        """Real ORQA data has source_category 1, label is 'ORQA subset'."""
        label = get_dataset_label()
        assert label == "ORQA subset"


class TestQuestionsByType:
    def test_dev_or_model_id(self):
        """Returns dev or_model_identification questions."""
        qs = get_questions_by_type("dev", "or_model_identification")
        assert len(qs) == 25
        assert all(q["split"] == "dev" for q in qs)
        assert all(q["task_type"] == "or_model_identification" for q in qs)

    def test_test_or_model_id(self):
        """Returns test or_model_identification questions."""
        qs = get_questions_by_type("test", "or_model_identification")
        assert len(qs) == 20
        assert all(q["split"] == "test" for q in qs)

    def test_seed_or_model_id(self):
        """Returns seed or_model_identification questions."""
        qs = get_questions_by_type("seed", "or_model_identification")
        assert len(qs) == 5

    def test_nonexistent_type_returns_empty(self):
        """Filtering by a type that doesn't exist returns empty."""
        qs = get_questions_by_type("dev", "linear_programming")
        assert len(qs) == 0


class TestORQADataIntegrity:
    """Regression tests for the real ORQA 50-instance subset."""

    def test_all_source_category_1(self):
        """All questions are source_category 1 (real ORQA data)."""
        for q in load_questions():
            assert q["source_category"] == 1, (
                f"Question {q['id']} has source_category {q['source_category']}, expected 1"
            )

    def test_all_task_type_or_model_identification(self):
        """All questions have unified task_type."""
        for q in load_questions():
            assert q["task_type"] == "or_model_identification"

    def test_seed_from_validation_set(self):
        """Seed questions should come from the ORQA validation set."""
        for q in load_questions(split="seed"):
            assert "validation" in q["source_detail"].lower(), (
                f"Seed question {q['id']} doesn't appear to be from validation set"
            )

    def test_dev_test_from_test_set(self):
        """Dev and test questions should come from the ORQA test set."""
        for q in load_questions(split="dev"):
            assert "test" in q["source_detail"].lower(), (
                f"Dev question {q['id']} doesn't appear to be from test set"
            )
        for q in load_questions(split="test"):
            assert "test" in q["source_detail"].lower(), (
                f"Test question {q['id']} doesn't appear to be from test set"
            )
