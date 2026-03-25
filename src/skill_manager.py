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


def count_skill_tokens(skill: dict, model: str = "gpt-4") -> int:
    """Count tokens in the YAML string representation of a skill.

    Uses tiktoken to count tokens as they would appear when the skill
    YAML is injected into a prompt for the specified model.

    Args:
        skill: The skill dictionary.
        model: The model name for tiktoken encoding selection.

    Returns:
        The number of tokens in the YAML string.
    """
    yaml_str = skill_to_yaml_string(skill)
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(yaml_str))


def validate_scaffold_length(
    v1_skill: dict,
    scaffold_skill: dict,
    tolerance: float = 0.15,
) -> tuple[bool, dict]:
    """Check that the scaffold skill is within tolerance of the v1 skill token count.

    Args:
        v1_skill: The domain-specific v1 curated skill.
        scaffold_skill: The generic scaffold skill.
        tolerance: Maximum allowed fractional deviation (default 0.15 = 15%).

    Returns:
        A tuple of (is_valid, info_dict) where info_dict contains:
        - v1_tokens: token count for the v1 skill
        - scaffold_tokens: token count for the scaffold skill
        - ratio: scaffold_tokens / v1_tokens
        - tolerance: the tolerance used
    """
    v1_tokens = count_skill_tokens(v1_skill)
    scaffold_tokens = count_skill_tokens(scaffold_skill)
    ratio = scaffold_tokens / v1_tokens if v1_tokens > 0 else float("inf")
    is_valid = abs(ratio - 1.0) <= tolerance

    return is_valid, {
        "v1_tokens": v1_tokens,
        "scaffold_tokens": scaffold_tokens,
        "ratio": ratio,
        "tolerance": tolerance,
    }
