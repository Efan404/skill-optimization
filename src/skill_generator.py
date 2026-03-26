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

Here are {n} example problems of this type (for context only — do NOT solve them):

{seed_examples_block}

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


def _parse_yaml_robust(yaml_text: str) -> dict:
    """Try to parse YAML with fallback sanitization for LLM-generated content.

    Handles common issues like unquoted values containing colons.

    Args:
        yaml_text: Raw YAML text extracted from LLM response.

    Returns:
        Parsed YAML as a dict.

    Raises:
        ValueError: If all parsing strategies fail.
    """
    # Strategy 1: direct parse
    try:
        result = yaml.safe_load(yaml_text)
        if isinstance(result, dict):
            return result
    except yaml.YAMLError:
        pass

    # Strategy 2: fix unquoted values containing colons
    lines = yaml_text.split("\n")
    fixed_lines = []
    for line in lines:
        stripped = line.rstrip()
        if not stripped or stripped.lstrip().startswith("#"):
            fixed_lines.append(stripped)
            continue

        content = stripped.lstrip()
        indent = " " * (len(stripped) - len(content))

        # Handle "- key: value" list items where value has unquoted colons
        if content.startswith("- "):
            inner = content[2:].strip()
            if ":" in inner:
                key_part, _, val_part = inner.partition(":")
                val_stripped = val_part.strip()
                if val_stripped and ":" in val_stripped and not (
                    val_stripped.startswith('"') or val_stripped.startswith("'") or
                    val_stripped.startswith(">") or val_stripped.startswith("|")
                ):
                    val_escaped = val_stripped.replace('"', '\\"')
                    fixed_lines.append(f'{indent}- {key_part}: "{val_escaped}"')
                    continue
            fixed_lines.append(stripped)
            continue

        # Handle "key: value" lines where value has unquoted colons
        if ":" in content:
            key_part, _, val_part = content.partition(":")
            val_stripped = val_part.strip()
            if val_stripped and ":" in val_stripped and not (
                val_stripped.startswith('"') or val_stripped.startswith("'") or
                val_stripped.startswith("[") or val_stripped.startswith(">") or
                val_stripped.startswith("|")
            ):
                val_escaped = val_stripped.replace('"', '\\"')
                fixed_lines.append(f'{indent}{key_part}: "{val_escaped}"')
                continue

        fixed_lines.append(stripped)

    fixed_yaml = "\n".join(fixed_lines)
    try:
        result = yaml.safe_load(fixed_yaml)
        if isinstance(result, dict):
            return result
    except yaml.YAMLError:
        pass

    raise ValueError(
        f"Could not parse YAML after sanitization. "
        f"Preview:\n{yaml_text[:500]}"
    )


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
    prompt_text = SKILL_GEN_PROMPT.format(
        task_type_description=TASK_TYPE_DESCRIPTIONS[task_type],
        n=len(seed_examples),
        seed_examples_block=seed_examples_block,
        task_type=task_type,
    )

    last_error = None
    for attempt in range(3):
        messages = [{"role": "user", "content": prompt_text}]
        result = client.chat(messages, purpose=f"skill_gen_{task_type}")

        # Parse the YAML from the response
        try:
            yaml_text = extract_yaml_from_response(result["response"])
            skill = _parse_yaml_robust(yaml_text)

            if not isinstance(skill, dict):
                raise ValueError(
                    f"Parsed YAML is not a dict (got {type(skill).__name__}). "
                    f"Raw YAML:\n{yaml_text}"
                )

            # Save to the v0 skill directory
            save_path = _V0_SKILL_DIR / f"{task_type}.yaml"
            save_skill(skill, str(save_path))

            return skill

        except (ValueError, yaml.YAMLError) as e:
            last_error = e
            if attempt < 2:
                # Retry with cleaner YAML instructions
                prompt_text += (
                    "\n\nIMPORTANT: Your previous YAML had formatting errors. "
                    "Ensure ALL string values containing colons, commas, or "
                    "special characters are properly quoted with double quotes. "
                    "Use the > or | YAML block scalar syntax for long text."
                )
                continue

    raise ValueError(
        f"Failed to generate valid YAML skill after 3 attempts. "
        f"Last error: {last_error}"
    )
