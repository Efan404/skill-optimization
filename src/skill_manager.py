"""Skill Manager — Load/save YAML skills, token counting, scaffold validation."""

import yaml
import tiktoken
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"

# Mapping from condition + task_type to skill file paths
_CONDITION_PATHS = {
    "generic_scaffold": lambda task_type: SKILLS_DIR / "generic_scaffold" / "generic_problem_solving.yaml",
    "v0_self_generated": lambda task_type: SKILLS_DIR / "orqa" / "v0_self_generated" / f"{task_type}.yaml",
    "v1_curated": lambda task_type: SKILLS_DIR / "orqa" / "v1_curated" / f"{task_type}.yaml",
    "v2_optimized": lambda task_type: SKILLS_DIR / "orqa" / "v2_optimized" / f"{task_type}.yaml",
}


def load_skill(path: str) -> dict:
    """Load a YAML skill file and return its contents as a dict.

    Args:
        path: Path to the YAML skill file (absolute or relative).

    Returns:
        The skill as a dictionary.

    Raises:
        FileNotFoundError: If the skill file does not exist.
        yaml.YAMLError: If the file contains invalid YAML.
    """
    p = Path(path)
    with open(p, "r") as f:
        skill = yaml.safe_load(f)
    return skill


def save_skill(skill: dict, path: str) -> None:
    """Save a skill dict as a YAML file.

    Args:
        skill: The skill dictionary to save.
        path: Destination file path (absolute or relative).
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        yaml.dump(skill, f, default_flow_style=False, sort_keys=False, width=200)


def skill_to_yaml_string(skill: dict) -> str:
    """Convert a skill dict to a YAML string for prompt injection.

    Args:
        skill: The skill dictionary.

    Returns:
        A YAML-formatted string representation of the skill.
    """
    return yaml.dump(skill, default_flow_style=False, sort_keys=False, width=200)


def get_skill_for_condition(condition: str, task_type: str) -> dict | None:
    """Return the appropriate skill for a given condition and task type.

    Args:
        condition: One of 'baseline', 'generic_scaffold', 'v0_self_generated',
                   'v1_curated', 'v2_optimized'.
        task_type: The task type, e.g. 'linear_programming' or
                   'combinatorial_optimization'.

    Returns:
        The skill dict if a skill exists for this condition, or None for
        baseline (which uses no skill).

    Raises:
        ValueError: If the condition is not recognized.
        FileNotFoundError: If the skill file does not exist.
    """
    if condition == "baseline":
        return None

    if condition not in _CONDITION_PATHS:
        raise ValueError(
            f"Unknown condition: {condition!r}. "
            f"Valid conditions: baseline, {', '.join(_CONDITION_PATHS.keys())}"
        )

    path = _CONDITION_PATHS[condition](task_type)
    return load_skill(str(path))


def count_skill_tokens(skill: dict, encoding: str = "cl100k_base") -> int:
    """Count tokens in the YAML string representation of a skill.

    Uses tiktoken to count tokens as they would appear when the skill
    YAML is injected into a prompt.  The default ``cl100k_base`` encoding
    is used by GPT-4 and DeepSeek models.

    Args:
        skill: The skill dictionary.
        encoding: The tiktoken encoding name (default ``"cl100k_base"``).

    Returns:
        The number of tokens in the YAML string.
    """
    yaml_str = skill_to_yaml_string(skill)
    enc = tiktoken.get_encoding(encoding)
    return len(enc.encode(yaml_str))


def validate_scaffold_length(
    v1_skill: dict,
    scaffold_skill: dict,
    tolerance: float = 0.15,
) -> tuple[bool, dict]:
    """Validate that the scaffold matches v1 on structural dimensions and token length.

    Checks:
    1. Same procedure step count
    2. Same common_failures count
    3. Same preconditions count
    4. Token count within +/-tolerance of v1

    Args:
        v1_skill: The domain-specific v1 curated skill.
        scaffold_skill: The generic scaffold skill.
        tolerance: Maximum allowed fractional deviation (default 0.15 = 15%).

    Returns:
        A tuple of (is_valid, info_dict) with details of all checks.
    """
    issues = []

    # Structural checks
    v1_steps = len(v1_skill.get("procedure", []))
    scaffold_steps = len(scaffold_skill.get("procedure", []))
    if v1_steps != scaffold_steps:
        issues.append(f"step_count: v1={v1_steps}, scaffold={scaffold_steps}")

    v1_failures = len(v1_skill.get("common_failures", []))
    scaffold_failures = len(scaffold_skill.get("common_failures", []))
    if v1_failures != scaffold_failures:
        issues.append(f"common_failures_count: v1={v1_failures}, scaffold={scaffold_failures}")

    v1_preconditions = len(v1_skill.get("preconditions", []))
    scaffold_preconditions = len(scaffold_skill.get("preconditions", []))
    if v1_preconditions != scaffold_preconditions:
        issues.append(f"preconditions_count: v1={v1_preconditions}, scaffold={scaffold_preconditions}")

    # Check each procedure step has a 'check' field
    for i, step in enumerate(scaffold_skill.get("procedure", [])):
        if "check" not in step:
            issues.append(f"procedure[{i}] missing 'check' field")

    # Token length check
    v1_tokens = count_skill_tokens(v1_skill)
    scaffold_tokens = count_skill_tokens(scaffold_skill)
    ratio = scaffold_tokens / v1_tokens if v1_tokens > 0 else float("inf")
    token_valid = abs(ratio - 1.0) <= tolerance
    if not token_valid:
        issues.append(f"token_ratio: {ratio:.2f} (outside +/-{tolerance:.0%})")

    is_valid = len(issues) == 0

    return is_valid, {
        "v1_tokens": v1_tokens,
        "scaffold_tokens": scaffold_tokens,
        "ratio": ratio,
        "tolerance": tolerance,
        "v1_steps": v1_steps,
        "scaffold_steps": scaffold_steps,
        "v1_failures": v1_failures,
        "scaffold_failures": scaffold_failures,
        "v1_preconditions": v1_preconditions,
        "scaffold_preconditions": scaffold_preconditions,
        "issues": issues,
    }
