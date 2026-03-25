"""Skill generator — use an LLM to create a v0 self-generated skill from seed examples.

The generator takes seed examples (disjoint from dev/test) for a given task
type, asks the LLM to produce a structured YAML skill, parses the response,
and saves the result to ``skills/orqa/v0_self_generated/{task_type}.yaml``.
"""

import re
from pathlib import Path

import yaml

from src.llm_client import LLMClient
from src.skill_manager import save_skill

# ---------------------------------------------------------------------------
# Prompt template & task-type descriptions
# ---------------------------------------------------------------------------

SKILL_GEN_PROMPT = """You are an expert in operations research and problem-solving methodology.

I need you to create a structured problem-solving skill for the following type of OR problem: {task_type_description}

Here are 2 example problems of this type (for context only — do NOT solve them):

Example 1:
{seed_example_1}

Example 2:
{seed_example_2}

NOTE: These examples are provided only to illustrate the problem format. Your skill must be general-purpose — it should work for ANY problem of this type, not just these examples.

Create a general-purpose skill as a step-by-step procedure with verification checks.

Output the skill in this exact YAML format:

name: [skill name]
version: "v0_self_generated"
source: "self_generated"
domain: "operations_research"
task_type: {task_type}
when_to_use: [when this skill applies]
when_not_to_use: [when this skill should NOT be used]
preconditions:
  - [precondition 1]
  - [precondition 2]
procedure:
  - step: [what to do]
    check: [how to verify]
  - step: [what to do]
    check: [how to verify]
common_failures:
  - [failure mode 1]
  - [failure mode 2]
verification: [final check procedure]"""

TASK_TYPE_DESCRIPTIONS = {
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

    Produces a readable text block containing the question and its choices.
    """
    choices = example["choices"]
    lines = [
        example["question"],
        f"  A) {choices['A']}",
        f"  B) {choices['B']}",
        f"  C) {choices['C']}",
        f"  D) {choices['D']}",
    ]
    return "\n".join(lines)


def extract_yaml_from_response(response: str) -> str:
    """Extract YAML content from an LLM response.

    Strategy:
      1. Look for a fenced code block (```yaml ... ``` or ``` ... ```).
      2. Fall back to detecting raw YAML starting with ``name:``.

    Args:
        response: The full LLM response text.

    Returns:
        A string containing the YAML content.

    Raises:
        ValueError: If no YAML content could be found.
    """
    # Strategy 1: fenced code block
    # Match ```yaml ... ``` or ``` ... ``` (greedy-minimal)
    pattern = r"```(?:yaml|yml)?\s*\n(.*?)```"
    match = re.search(pattern, response, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Strategy 2: raw YAML — look for a block starting with "name:"
    pattern_raw = r"(^name:\s*.+(?:\n.+)*)"
    match_raw = re.search(pattern_raw, response, re.MULTILINE)
    if match_raw:
        return match_raw.group(1).strip()

    raise ValueError(
        "Could not extract YAML from LLM response. "
        "Expected a ```yaml``` code block or raw YAML starting with 'name:'."
    )


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

    # Build the prompt
    prompt_text = SKILL_GEN_PROMPT.format(
        task_type_description=TASK_TYPE_DESCRIPTIONS[task_type],
        seed_example_1=_format_example(seed_examples[0]),
        seed_example_2=_format_example(seed_examples[1]),
        task_type=task_type,
    )

    messages = [{"role": "user", "content": prompt_text}]
    result = client.chat(messages, purpose=f"skill_gen_{task_type}")

    # Parse the YAML from the response
    yaml_text = extract_yaml_from_response(result["response"])
    skill = yaml.safe_load(yaml_text)

    if not isinstance(skill, dict):
        raise ValueError(
            f"Parsed YAML is not a dict (got {type(skill).__name__}). "
            f"Raw YAML:\n{yaml_text}"
        )

    # Save to the v0 skill directory
    save_path = _V0_SKILL_DIR / f"{task_type}.yaml"
    save_skill(skill, str(save_path))

    return skill
