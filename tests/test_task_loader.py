"""Tests for src/task_loader.py"""

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
        assert len(questions) >= 20  # at least 20 questions expected
        required_fields = [
            "id", "task_type", "split", "question",
            "choices", "correct_answer", "source_category", "source_detail",
        ]
        for q in questions:
            for field in required_fields:
                assert field in q, f"Missing field '{field}' in question {q.get('id', '?')}"

    def test_load_by_split_seed(self):
        """Filtering by 'seed' returns only seed questions."""
        seed_qs = load_questions(split="seed")
        assert len(seed_qs) >= 2
        assert all(q["split"] == "seed" for q in seed_qs)

    def test_load_by_split_dev(self):
        """Filtering by 'dev' returns only dev questions."""
        dev_qs = load_questions(split="dev")
        assert len(dev_qs) >= 8
        assert all(q["split"] == "dev" for q in dev_qs)

    def test_load_by_split_test(self):
        """Filtering by 'test' returns only test questions."""
        test_qs = load_questions(split="test")
        assert len(test_qs) >= 8
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
    def test_seed_lp(self):
        """Returns seed questions for linear_programming."""
        seeds = get_seed_examples("linear_programming")
        assert len(seeds) >= 2
        assert all(q["task_type"] == "linear_programming" for q in seeds)
        assert all(q["split"] == "seed" for q in seeds)

    def test_seed_co(self):
        """Returns seed questions for combinatorial_optimization."""
        seeds = get_seed_examples("combinatorial_optimization")
        assert len(seeds) >= 2
        assert all(q["task_type"] == "combinatorial_optimization" for q in seeds)
        assert all(q["split"] == "seed" for q in seeds)

    def test_seed_unknown_type(self):
        """Unknown task type returns empty list."""
        seeds = get_seed_examples("nonexistent_type")
        assert seeds == []


class TestDatasetLabel:
    def test_label_with_source_3(self):
        """If any source_category == 3, label is 'ORQA-derived evaluation set'."""
        label = get_dataset_label()
        # Our data is all source_category 3
        assert label == "ORQA-derived evaluation set"


class TestQuestionsByType:
    def test_dev_lp(self):
        """Returns dev LP questions."""
        qs = get_questions_by_type("dev", "linear_programming")
        assert len(qs) == 5
        assert all(q["split"] == "dev" for q in qs)
        assert all(q["task_type"] == "linear_programming" for q in qs)

    def test_dev_co(self):
        """Returns dev CO questions."""
        qs = get_questions_by_type("dev", "combinatorial_optimization")
        assert len(qs) == 5
        assert all(q["split"] == "dev" for q in qs)
        assert all(q["task_type"] == "combinatorial_optimization" for q in qs)

    def test_test_lp(self):
        """Returns test LP questions."""
        qs = get_questions_by_type("test", "linear_programming")
        assert len(qs) == 5

    def test_seed_lp(self):
        """Returns seed LP questions."""
        qs = get_questions_by_type("seed", "linear_programming")
        assert len(qs) == 2
