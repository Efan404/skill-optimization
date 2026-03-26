"""Contract tests that assert project invariants after ORQA migration."""

import json
from pathlib import Path

from src.task_loader import load_questions, validate_split_integrity
from src.agent_runner import BASELINE_PROMPT, SCAFFOLD_PROMPT, SKILL_PROMPT

PROJECT_ROOT = Path(__file__).parent.parent


def test_only_or_model_identification_task_type():
    """All questions must use the unified task type."""
    for q in load_questions():
        assert q["task_type"] == "or_model_identification"


def test_no_legacy_task_types_in_data():
    """No linear_programming or combinatorial_optimization in question data."""
    for q in load_questions():
        assert q["task_type"] not in ("linear_programming", "combinatorial_optimization")


def test_v1_curated_skill_exists():
    """The ORQA v1 curated skill file must exist."""
    path = PROJECT_ROOT / "skills" / "orqa" / "v1_curated" / "or_model_identification.yaml"
    assert path.exists(), f"Missing v1 curated skill: {path}"


def test_old_skills_removed():
    """Old LP/CO skill files must not exist."""
    for name in ["linear_programming.yaml", "combinatorial_optimization.yaml"]:
        path = PROJECT_ROOT / "skills" / "orqa" / "v1_curated" / name
        assert not path.exists(), f"Legacy skill still exists: {path}"


def test_all_questions_have_context():
    """Every ORQA question must have a non-empty context field."""
    for q in load_questions():
        assert q.get("context"), f"Question {q['id']} missing context"


def test_all_questions_have_question_subtype():
    """Every question must have a question_subtype (Q1-Q11)."""
    for q in load_questions():
        assert q.get("question_subtype", "").startswith("Q")


def test_all_source_category_1():
    """All real ORQA questions must be source_category 1."""
    for q in load_questions():
        assert q["source_category"] == 1


def test_prompt_templates_include_context():
    """All prompt templates must have a {context} placeholder."""
    for name, template in [("baseline", BASELINE_PROMPT), ("scaffold", SCAFFOLD_PROMPT), ("skill", SKILL_PROMPT)]:
        assert "{context}" in template, f"{name} prompt missing {{context}}"


def test_prompt_templates_include_answer_format():
    """All prompts must instruct ANSWER: X format."""
    for name, template in [("baseline", BASELINE_PROMPT), ("scaffold", SCAFFOLD_PROMPT), ("skill", SKILL_PROMPT)]:
        assert "ANSWER: X" in template or "ANSWER:" in template, f"{name} prompt missing answer format"


def test_generic_scaffold_exists():
    """Generic scaffold file must exist."""
    path = PROJECT_ROOT / "skills" / "generic_scaffold" / "generic_problem_solving.yaml"
    assert path.exists()


def test_split_json_consistent():
    """split.json must be consistent with questions.json."""
    assert validate_split_integrity()
