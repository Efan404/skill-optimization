"""Skill schema validation for JSON output from LLMs."""

REQUIRED_SKILL_FIELDS = [
    "name", "version", "source", "domain", "task_type",
    "when_to_use", "procedure", "common_failures", "verification",
]


def validate_skill_dict(skill: dict) -> list[str]:
    """Validate a skill dict has required fields.

    Returns list of issues (empty = valid).
    """
    issues = []
    for field in REQUIRED_SKILL_FIELDS:
        if field not in skill:
            issues.append(f"Missing required field: {field}")

    if "procedure" in skill:
        if not isinstance(skill["procedure"], list):
            issues.append("'procedure' must be a list")
        else:
            for i, step in enumerate(skill["procedure"]):
                if not isinstance(step, dict):
                    issues.append(f"procedure[{i}] must be a dict")
                elif "step" not in step:
                    issues.append(f"procedure[{i}] missing 'step' field")

    return issues
