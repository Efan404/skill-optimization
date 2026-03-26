"""Skill Optimizer — LLM refines v1 -> v2 skill using dev evidence only."""

import json

from src.llm_client import LLMClient
from src.skill_manager import save_skill, skill_to_yaml_string
from src.skill_schema import validate_skill_dict

OPTIMIZER_SCHEMA_FOR_PROMPT = """
Output a JSON object with this structure:
{
  "skill": {
    "name": "string",
    "version": "v2_optimized",
    "source": "optimized",
    "domain": "string",
    "task_type": "string",
    "when_to_use": "string",
    "when_not_to_use": "string",
    "preconditions": ["string", ...],
    "procedure": [{"step": "string", "check": "string"}, ...],
    "common_failures": ["string", ...],
    "verification": "string"
  },
  "changelog": ["string - what changed and why", ...]
}
"""

def _build_optimizer_prompt(n: int, n_success: int, n_fail: int,
                            current_skill_yaml: str, dev_failure_details: str,
                            dev_success_summaries: str) -> str:
    """Build the optimizer prompt without .format() brace conflicts."""
    return f"""You are a skill optimization expert. You are given:

1. A problem-solving skill that was tested on {n} development tasks
2. It succeeded on {n_success} tasks and failed on {n_fail} tasks
3. Root cause analysis for each failure
4. The full reasoning traces for both successes and failures

**Current Skill:**
{current_skill_yaml}

**Failure Analysis (development set only):**
{dev_failure_details}

**Success Cases (do not break these):**
{dev_success_summaries}

Your job: produce an IMPROVED version of the skill that:
1. Fixes the identified failure patterns
2. Does NOT break the cases that already succeed
3. Stays concise — do not make the skill longer than necessary
4. Produces GENERAL improvements — not fixes targeted at specific questions

{OPTIMIZER_SCHEMA_FOR_PROMPT.strip()}"""


def _assert_dev_split(item: dict, label: str) -> None:
    """Validate that an item's question belongs to the dev split.

    Args:
        item: A dict that must contain a 'question' key with a 'split' field.
        label: A human-readable label for error messages (e.g. 'failure', 'success').

    Raises:
        ValueError: If the item's question split is not 'dev'.
    """
    question = item.get("question", {})
    split = question.get("split")
    if split != "dev":
        q_id = question.get("id", "unknown")
        raise ValueError(
            f"Split assertion failed for {label} item: expected split='dev', "
            f"got split='{split}' for question '{q_id}'. "
            f"Skill optimization must only use dev data."
        )


def _format_failure_details(dev_failures: list[dict]) -> str:
    """Format failure details for the optimizer prompt.

    Args:
        dev_failures: List of dicts, each with keys:
            - question (dict): The question dict.
            - response (str): The LLM's response.
            - root_causes (list[str]): Root cause codes.
            - explanation (str): Root cause explanation.

    Returns:
        Formatted string of failure details.
    """
    if not dev_failures:
        return "No failures to report."

    parts = []
    for i, failure in enumerate(dev_failures, 1):
        q = failure["question"]
        parts.append(
            f"Failure {i}: {q.get('id', 'unknown')}\n"
            f"  Question: {q.get('question', 'N/A')[:200]}\n"
            f"  Correct Answer: {q.get('correct_answer', 'N/A')}\n"
            f"  Root Causes: {', '.join(failure.get('root_causes', []))}\n"
            f"  Explanation: {failure.get('explanation', 'N/A')}\n"
            f"  LLM Response (truncated): {failure.get('response', '')[:300]}"
        )
    return "\n\n".join(parts)


def _format_success_summaries(dev_successes: list[dict]) -> str:
    """Format success summaries for the optimizer prompt.

    Args:
        dev_successes: List of dicts, each with keys:
            - question (dict): The question dict.
            - response (str): The LLM's response.

    Returns:
        Formatted string of success summaries.
    """
    if not dev_successes:
        return "No successes to report."

    parts = []
    for i, success in enumerate(dev_successes, 1):
        q = success["question"]
        parts.append(
            f"Success {i}: {q.get('id', 'unknown')}\n"
            f"  Question: {q.get('question', 'N/A')[:200]}\n"
            f"  Correct Answer: {q.get('correct_answer', 'N/A')}"
        )
    return "\n\n".join(parts)


def optimize_skill(
    client: LLMClient,
    current_skill: dict,
    dev_failures: list[dict],
    dev_successes: list[dict],
    task_type: str,
) -> tuple[dict, str]:
    """Use LLM to refine a v1 skill based on dev-set error analysis.

    ASSERTION: all failure/success items must come from dev split. Validates
    by checking that each item's question has split=="dev". Raises ValueError
    if test data is detected.

    Args:
        client: An initialized LLMClient instance.
        current_skill: The current skill dict to optimize.
        dev_failures: List of failure dicts, each containing:
            - question (dict): The question dict with split=="dev".
            - response (str): The LLM's incorrect response.
            - root_causes (list[str]): Root cause codes from error analysis.
            - explanation (str): Root cause explanation.
        dev_successes: List of success dicts, each containing:
            - question (dict): The question dict with split=="dev".
            - response (str): The LLM's correct response.
        task_type: The task type (e.g. 'linear_programming').

    Returns:
        Tuple of (optimized_skill_dict, changelog_string).

    Raises:
        ValueError: If any item's question split is not 'dev'.
    """
    # Validate ALL items come from dev split
    for item in dev_failures:
        _assert_dev_split(item, "failure")
    for item in dev_successes:
        _assert_dev_split(item, "success")

    n_total = len(dev_failures) + len(dev_successes)
    n_success = len(dev_successes)
    n_fail = len(dev_failures)

    prompt = _build_optimizer_prompt(
        n=n_total,
        n_success=n_success,
        n_fail=n_fail,
        current_skill_yaml=skill_to_yaml_string(current_skill),
        dev_failure_details=_format_failure_details(dev_failures),
        dev_success_summaries=_format_success_summaries(dev_successes),
    )

    messages = [{"role": "user", "content": prompt}]
    result = client.chat(
        messages,
        purpose=f"optimize_skill_{task_type}",
        response_format={"type": "json_object"},
    )

    # Parse JSON response
    try:
        response_data = json.loads(result["response"])
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM returned invalid JSON for skill optimization. "
            f"Error: {e}. Response preview: {result['response'][:300]}"
        ) from e

    if not isinstance(response_data, dict):
        raise ValueError(
            f"LLM returned JSON but not a dict (got {type(response_data).__name__}). "
            f"Response preview: {result['response'][:300]}"
        )

    # Extract skill and changelog from the response
    if "skill" not in response_data:
        raise ValueError(
            f"LLM JSON response missing 'skill' key. "
            f"Keys found: {list(response_data.keys())}. "
            f"Response preview: {result['response'][:300]}"
        )

    optimized_skill = response_data["skill"]

    # Validate required fields
    issues = validate_skill_dict(optimized_skill)
    if issues:
        raise ValueError(
            f"Optimized skill is missing required fields: {'; '.join(issues)}. "
            f"Response preview: {result['response'][:300]}"
        )

    # Build changelog string
    changelog_items = response_data.get("changelog", [])
    changelog = "\n".join(f"- {item}" for item in changelog_items)
    if not changelog:
        changelog = "No changelog provided by the optimizer."

    # Save the optimized skill (internal storage remains YAML)
    output_path = f"skills/orqa/v2_optimized/{task_type}.yaml"
    save_skill(optimized_skill, output_path)

    return optimized_skill, changelog
