"""Tests for skill_manager: load/save, token counting, scaffold validation, condition routing."""

import sys
from pathlib import Path

import pytest

# Ensure project root is on the path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.skill_manager import (
    count_skill_tokens,
    get_skill_for_condition,
    load_skill,
    save_skill,
    validate_scaffold_length,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_SKILL = {
    "name": "test-skill",
    "version": "v1",
    "source": "curated",
    "domain": "testing",
    "task_type": "unit_test",
    "when_to_use": "When running unit tests for the skill manager",
    "when_not_to_use": "In production",
    "preconditions": ["Tests are written", "pytest is installed"],
    "procedure": [
        {"step": "Run the test", "check": "Did it pass?"},
        {"step": "Check output", "check": "Is the output correct?"},
    ],
    "common_failures": ["Forgot to install deps", "Wrong path"],
    "verification": "All tests pass",
}

V1_LP_PATH = PROJECT_ROOT / "skills" / "orqa" / "v1_curated" / "linear_programming.yaml"
V1_CO_PATH = PROJECT_ROOT / "skills" / "orqa" / "v1_curated" / "combinatorial_optimization.yaml"
SCAFFOLD_PATH = PROJECT_ROOT / "skills" / "generic_scaffold" / "generic_problem_solving.yaml"


# ---------------------------------------------------------------------------
# Test: Round-trip load/save
# ---------------------------------------------------------------------------

def test_load_and_save_skill(tmp_path):
    """Round-trip: save then load produces identical dict."""
    path = tmp_path / "test_skill.yaml"
    save_skill(SAMPLE_SKILL, str(path))
    loaded = load_skill(str(path))
    assert loaded == SAMPLE_SKILL


def test_load_skill_file_not_found():
    """Loading a nonexistent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_skill("/nonexistent/path/skill.yaml")


# ---------------------------------------------------------------------------
# Test: Token counting
# ---------------------------------------------------------------------------

def test_count_skill_tokens():
    """Token count returns a positive integer for a valid skill."""
    tokens = count_skill_tokens(SAMPLE_SKILL)
    assert isinstance(tokens, int)
    assert tokens > 0


def test_count_skill_tokens_real_skills():
    """Real v1 skills have reasonable token counts (> 100 tokens)."""
    lp = load_skill(str(V1_LP_PATH))
    co = load_skill(str(V1_CO_PATH))
    lp_tokens = count_skill_tokens(lp)
    co_tokens = count_skill_tokens(co)
    assert lp_tokens > 100, f"LP tokens unexpectedly low: {lp_tokens}"
    assert co_tokens > 100, f"CO tokens unexpectedly low: {co_tokens}"


# ---------------------------------------------------------------------------
# Test: Scaffold validation pass/fail
# ---------------------------------------------------------------------------

def test_validate_scaffold_length_pass():
    """Scaffold within 15% of v1 returns True."""
    # Create two skills with similar content length
    skill_a = SAMPLE_SKILL.copy()
    skill_b = SAMPLE_SKILL.copy()
    is_valid, info = validate_scaffold_length(skill_a, skill_b, tolerance=0.15)
    assert is_valid is True
    assert info["ratio"] == pytest.approx(1.0, abs=0.001)


def test_validate_scaffold_length_fail():
    """Scaffold >15% different from v1 returns False."""
    small_skill = {
        "name": "tiny",
        "version": "v1",
        "source": "curated",
        "domain": "x",
        "task_type": "x",
        "when_to_use": "x",
        "procedure": [{"step": "x", "check": "x"}],
        "common_failures": ["x"],
        "verification": "x",
    }
    big_skill = {
        "name": "big-skill-with-lots-of-content",
        "version": "v1",
        "source": "curated",
        "domain": "extensive domain description with many details",
        "task_type": "complex_task",
        "when_to_use": "When doing extensive complex multi-step reasoning across many dimensions of the problem space requiring careful attention to detail",
        "procedure": [
            {"step": f"Do step {i} which involves careful detailed reasoning about the problem at hand", "check": f"Did step {i} complete correctly and produce the expected intermediate result?"}
            for i in range(20)
        ],
        "common_failures": [f"Failure mode {i} involving complex edge cases" for i in range(10)],
        "verification": "Perform thorough extensive verification of all intermediate and final results against all stated conditions and constraints in the original problem",
    }
    is_valid, info = validate_scaffold_length(small_skill, big_skill)
    assert is_valid is False
    assert info["ratio"] > 1.15


def test_validate_scaffold_real_skills():
    """Real scaffold is within 15% of both real v1 skills."""
    lp = load_skill(str(V1_LP_PATH))
    co = load_skill(str(V1_CO_PATH))
    scaffold = load_skill(str(SCAFFOLD_PATH))

    valid_lp, info_lp = validate_scaffold_length(lp, scaffold)
    valid_co, info_co = validate_scaffold_length(co, scaffold)

    assert valid_lp, (
        f"Scaffold not within 15% of LP: "
        f"LP={info_lp['v1_tokens']}, scaffold={info_lp['scaffold_tokens']}, "
        f"ratio={info_lp['ratio']:.3f}"
    )
    assert valid_co, (
        f"Scaffold not within 15% of CO: "
        f"CO={info_co['v1_tokens']}, scaffold={info_co['scaffold_tokens']}, "
        f"ratio={info_co['ratio']:.3f}"
    )


# ---------------------------------------------------------------------------
# Test: get_skill_for_condition
# ---------------------------------------------------------------------------

def test_get_skill_for_baseline():
    """Baseline condition returns None (no skill injection)."""
    result = get_skill_for_condition("baseline", "linear_programming")
    assert result is None


def test_get_skill_for_baseline_any_task_type():
    """Baseline returns None regardless of task_type."""
    assert get_skill_for_condition("baseline", "combinatorial_optimization") is None
    assert get_skill_for_condition("baseline", "anything") is None


def test_get_skill_for_curated():
    """v1_curated returns the correct skill file for each task type."""
    lp = get_skill_for_condition("v1_curated", "linear_programming")
    assert lp is not None
    assert lp["name"] == "linear-programming-solving"
    assert lp["task_type"] == "linear_programming"

    co = get_skill_for_condition("v1_curated", "combinatorial_optimization")
    assert co is not None
    assert co["name"] == "combinatorial-optimization-solving"
    assert co["task_type"] == "combinatorial_optimization"


def test_get_skill_for_generic_scaffold():
    """generic_scaffold returns the generic skill regardless of task_type."""
    scaffold = get_skill_for_condition("generic_scaffold", "linear_programming")
    assert scaffold is not None
    assert scaffold["name"] == "generic-problem-solving"
    assert scaffold["domain"] == "general"


def test_get_skill_for_unknown_condition():
    """Unknown condition raises ValueError."""
    with pytest.raises(ValueError, match="Unknown condition"):
        get_skill_for_condition("nonexistent_condition", "linear_programming")


def test_get_skill_for_missing_file():
    """Condition with missing file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        get_skill_for_condition("v0_self_generated", "linear_programming")
