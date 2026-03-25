"""Task loader for ORQA evaluation data.

Loads questions from data/orqa/questions.json, enforces split boundaries
(seed/dev/test), and computes the conditional dataset label.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "orqa"

VALID_SPLITS = {"seed", "dev", "test"}


def load_questions(split: str = None) -> list[dict]:
    """Load questions from data/orqa/questions.json.

    Args:
        split: If specified, filter to only that split (seed/dev/test).
               If None, return all questions.

    Returns:
        List of question dicts.

    Raises:
        ValueError: If split is not a valid split name.
        FileNotFoundError: If questions.json does not exist.
    """
    if split is not None and split not in VALID_SPLITS:
        raise ValueError(f"Invalid split '{split}'. Must be one of: {VALID_SPLITS}")

    questions_path = DATA_DIR / "questions.json"
    with open(questions_path) as f:
        questions = json.load(f)

    if split is not None:
        questions = [q for q in questions if q["split"] == split]

    return questions


def validate_split_integrity() -> bool:
    """Verify no overlap between seed/dev/test and all IDs are accounted for.

    Checks:
    - All question IDs in questions.json appear in exactly one split in split.json
    - All IDs in split.json exist in questions.json
    - No overlap between seed, dev, and test sets

    Returns:
        True if all checks pass.

    Raises:
        ValueError: If any integrity check fails.
    """
    with open(DATA_DIR / "questions.json") as f:
        questions = json.load(f)
    with open(DATA_DIR / "split.json") as f:
        split_def = json.load(f)

    question_ids = {q["id"] for q in questions}
    question_splits = {q["id"]: q["split"] for q in questions}

    seed_ids = set(split_def.get("seed", []))
    dev_ids = set(split_def.get("dev", []))
    test_ids = set(split_def.get("test", []))

    # Check no overlap
    if seed_ids & dev_ids:
        raise ValueError(f"Overlap between seed and dev: {seed_ids & dev_ids}")
    if seed_ids & test_ids:
        raise ValueError(f"Overlap between seed and test: {seed_ids & test_ids}")
    if dev_ids & test_ids:
        raise ValueError(f"Overlap between dev and test: {dev_ids & test_ids}")

    # Check all split.json IDs exist in questions.json
    all_split_ids = seed_ids | dev_ids | test_ids
    missing_from_questions = all_split_ids - question_ids
    if missing_from_questions:
        raise ValueError(f"IDs in split.json not found in questions.json: {missing_from_questions}")

    # Check all question IDs are in split.json
    missing_from_split = question_ids - all_split_ids
    if missing_from_split:
        raise ValueError(f"IDs in questions.json not found in split.json: {missing_from_split}")

    # Check split labels in questions.json match split.json
    for qid, qsplit in question_splits.items():
        if qid in seed_ids and qsplit != "seed":
            raise ValueError(f"Question {qid} has split '{qsplit}' but is in seed set in split.json")
        if qid in dev_ids and qsplit != "dev":
            raise ValueError(f"Question {qid} has split '{qsplit}' but is in dev set in split.json")
        if qid in test_ids and qsplit != "test":
            raise ValueError(f"Question {qid} has split '{qsplit}' but is in test set in split.json")

    return True


def get_seed_examples(task_type: str) -> list[dict]:
    """Return seed questions for a specific task type.

    Used by v0 skill generator. These questions are disjoint from dev and test.

    Args:
        task_type: e.g. "linear_programming" or "combinatorial_optimization"

    Returns:
        List of seed question dicts for the given task type.
    """
    questions = load_questions(split="seed")
    return [q for q in questions if q["task_type"] == task_type]


def get_dataset_label() -> str:
    """Compute the conditional dataset label based on source categories.

    Returns:
        'ORQA subset' if all source_category <= 2,
        'ORQA-derived evaluation set' if any source_category == 3.
    """
    questions = load_questions()
    if any(q.get("source_category", 1) >= 3 for q in questions):
        return "ORQA-derived evaluation set"
    return "ORQA subset"


def get_questions_by_type(split: str, task_type: str) -> list[dict]:
    """Return questions filtered by both split and task_type.

    Args:
        split: One of 'seed', 'dev', 'test'.
        task_type: e.g. 'linear_programming' or 'combinatorial_optimization'.

    Returns:
        List of question dicts matching both criteria.
    """
    questions = load_questions(split=split)
    return [q for q in questions if q["task_type"] == task_type]
