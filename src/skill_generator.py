"""Skill generator — use an LLM to create a v0 self-generated skill from seed examples.

The generator takes seed examples (disjoint from dev/test) for a given task
type, asks the LLM to produce a structured JSON skill, parses the response,
and saves the result to ``skills/orqa/v0_self_generated/{task_type}.yaml``.
"""

import json
from pathlib import Path

from src.llm_client import LLMClient
from src.skill_manager import save_skill
from src.skill_schema import validate_skill_dict

# ---------------------------------------------------------------------------
# Prompt template & task-type descriptions
# ---------------------------------------------------------------------------

SKILL_SCHEMA_FOR_PROMPT = """
Output a JSON object with this structure:
{
  "name": "string - skill name",
  "version": "v0_self_generated",
  "source": "self_generated",
  "domain": "operations_research",
  "task_type": "string",
  "when_to_use": "string",
  "when_not_to_use": "string",
  "preconditions": ["string", ...],
  "procedure": [{"step": "string", "check": "string"}, ...],
  "common_failures": ["string", ...],
  "verification": "string"
}
"""

def _build_gen_prompt(task_type_description: str, n: int, seed_examples_block: str) -> str:
    """Build the skill generation prompt without .format() brace conflicts."""
    return f"""You are an expert in operations research and problem-solving methodology.

I need you to create a structured problem-solving skill for the following type of OR problem: {task_type_description}

Here are {n} example problems of this type (for context only — do NOT solve them):

{seed_examples_block}

NOTE: These examples are provided only to illustrate the problem format. Your skill must be general-purpose — it should work for ANY problem of this type, not just these examples.

Create a general-purpose skill as a step-by-step procedure with verification checks.

{SKILL_SCHEMA_FOR_PROMPT.strip()}"""

TASK_TYPE_DESCRIPTIONS = {
    "or_model_identification": (
        "Operations research model identification problems where you must "
        "identify optimization model components (decision variables, parameters, "
        "constraints, objectives, model type) from a natural language problem "
        "description"
    ),
    "linear_programming": (
        "Linear programming problems where you must optimize a linear "
        "objective function subject to linear constraints"
    ),
    "combinatorial_optimization": (
        "Combinatorial optimization problems involving discrete choices, "
        "assignments, scheduling, or counting"
    ),
}

# Destination directory for v0 skills (relative to project root)
_V0_SKILL_DIR = Path("skills") / "orqa" / "v0_self_generated"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_example(example: dict) -> str:
    """Format a seed example question for inclusion in the prompt.

    Produces a readable text block containing the context (if present),
    question, and choices.
    """
    choices = example["choices"]
    lines = []
    if example.get("context"):
        lines.append(f"Context: {example['context']}")
    lines.extend([
        f"Question: {example['question']}",
        f"  A) {choices['A']}",
        f"  B) {choices['B']}",
        f"  C) {choices['C']}",
        f"  D) {choices['D']}",
    ])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_skill(
    client: LLMClient,
    task_type: str,
    seed_examples: list[dict],
) -> dict:
    """Use the LLM to generate a v0 skill for a task type.

    Args:
        client: An initialised LLMClient instance.
        task_type: e.g. ``"linear_programming"`` or
                   ``"combinatorial_optimization"``.
        seed_examples: A list of seed question dicts (must contain at least 2).

    Returns:
        The parsed skill as a dictionary.

    Raises:
        ValueError: If *task_type* is not recognised, fewer than 2 seed
            examples are provided, or the LLM response cannot be parsed.
    """
    if task_type not in TASK_TYPE_DESCRIPTIONS:
        raise ValueError(
            f"Unknown task type: {task_type!r}. "
            f"Valid types: {sorted(TASK_TYPE_DESCRIPTIONS.keys())}"
        )

    if len(seed_examples) < 2:
        raise ValueError(
            f"Need at least 2 seed examples, got {len(seed_examples)}."
        )

    # Build the prompt — use ALL seed examples
    seed_examples_block = "\n\n".join(
        f"Example {i + 1}:\n{_format_example(ex)}"
        for i, ex in enumerate(seed_examples)
    )
    prompt_text = _build_gen_prompt(
        task_type_description=TASK_TYPE_DESCRIPTIONS[task_type],
        n=len(seed_examples),
        seed_examples_block=seed_examples_block,
    )

    messages = [{"role": "user", "content": prompt_text}]
    result = client.chat(
        messages,
        purpose=f"skill_gen_{task_type}",
        response_format={"type": "json_object"},
    )

    # Parse JSON response
    try:
        skill = json.loads(result["response"])
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM returned invalid JSON for skill generation. "
            f"Error: {e}. Response preview: {result['response'][:300]}"
        ) from e

    if not isinstance(skill, dict):
        raise ValueError(
            f"LLM returned JSON but not a dict (got {type(skill).__name__}). "
            f"Response preview: {result['response'][:300]}"
        )

    # Validate required fields
    issues = validate_skill_dict(skill)
    if issues:
        raise ValueError(
            f"Generated skill is missing required fields: {'; '.join(issues)}. "
            f"Response preview: {result['response'][:300]}"
        )

    # Save to the v0 skill directory (internal storage remains YAML)
    save_path = _V0_SKILL_DIR / f"{task_type}.yaml"
    save_skill(skill, str(save_path))

    return skill
