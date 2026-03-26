"""Skill Optimizer — LLM refines v1 -> v2 skill using dev evidence only."""

import re

import yaml

from src.llm_client import LLMClient
from src.skill_manager import save_skill, skill_to_yaml_string

OPTIMIZER_PROMPT = """You are a skill optimization expert. You are given:

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

Output the complete updated skill in the same YAML format, followed by:

**CHANGELOG:**
- What you changed and why (one bullet per change)"""


def _try_parse_yaml(text: str) -> dict | None:
    """Try to parse YAML, with a repair pass for common LLM output issues.

    LLMs often produce YAML with unquoted strings containing colons, e.g.:
        check: Match the question to: objective, constraints
    This is invalid YAML. We attempt a repair by quoting such lines.

    Returns parsed dict, or None if parsing fails.
    """
    # First, try parsing as-is
    try:
        result = yaml.safe_load(text)
        if isinstance(result, dict):
            return result
    except yaml.YAMLError:
        pass

    # Repair: quote values that contain unquoted colons
    # Handle any key: value lines where value contains colons
    repaired_lines = []
    for line in text.split("\n"):
        stripped = line.lstrip()
        indent = line[:len(line) - len(stripped)]

        # Skip empty lines, comments, block scalar indicators
        if not stripped or stripped.startswith("#"):
            repaired_lines.append(line)
            continue

        # Handle list items: "- key: value with: colon"
        if stripped.startswith("- "):
            inner = stripped[2:].strip()
            if ":" in inner:
                key_part, _, val_part = inner.partition(":")
                val_stripped = val_part.strip()
                if val_stripped and ":" in val_stripped and not (
                    val_stripped.startswith("'") or val_stripped.startswith('"') or
                    val_stripped.startswith(">") or val_stripped.startswith("|")
                ):
                    val_escaped = val_stripped.replace("'", "''")
                    repaired_lines.append(f"{indent}- {key_part}: '{val_escaped}'")
                    continue
            repaired_lines.append(line)
            continue

        # Handle regular key: value lines
        if ":" in stripped:
            key_part, _, val_part = stripped.partition(":")
            val_stripped = val_part.strip()
            if val_stripped and ":" in val_stripped and not (
                val_stripped.startswith("'") or val_stripped.startswith('"') or
                val_stripped.startswith("[") or val_stripped.startswith(">") or
                val_stripped.startswith("|")
            ):
                val_escaped = val_stripped.replace("'", "''")
                repaired_lines.append(f"{indent}{key_part}: '{val_escaped}'")
                continue

        repaired_lines.append(line)

    repaired_text = "\n".join(repaired_lines)
    try:
        result = yaml.safe_load(repaired_text)
        if isinstance(result, dict):
            return result
    except yaml.YAMLError:
        pass

    return None


def extract_yaml_from_response(response: str) -> dict:
    """Extract a YAML skill dict from an LLM response.

    Tries multiple strategies:
    1. Look for a YAML code block (```yaml ... ```)
    1b. Unclosed ```yaml block (truncated response)
    2. Look for any code block (``` ... ```)
    3. Try to parse everything before the CHANGELOG marker as YAML
    4. Try the entire response as YAML

    All parsing attempts use _try_parse_yaml which includes a repair
    pass for common LLM YAML issues (unquoted colons in strings).

    Args:
        response: The raw LLM response text.

    Returns:
        The parsed YAML as a dictionary.

    Raises:
        ValueError: If no valid YAML could be extracted.
    """
    # Strategy 1: Look for ```yaml ... ``` code block (closed)
    yaml_block_match = re.search(r"```yaml\s*\n(.*?)```", response, re.DOTALL)
    if yaml_block_match:
        result = _try_parse_yaml(yaml_block_match.group(1).strip())
        if result:
            return result

    # Strategy 1b: Unclosed ```yaml block (LLM response truncated at max_tokens)
    yaml_open_match = re.search(r"```yaml\s*\n(.*)", response, re.DOTALL)
    if yaml_open_match:
        yaml_text = re.sub(r"\n?```\s*$", "", yaml_open_match.group(1).strip())
        result = _try_parse_yaml(yaml_text)
        if result:
            return result

    # Strategy 2: Look for any code block ``` ... ``` (closed)
    code_block_match = re.search(r"```\s*\n(.*?)```", response, re.DOTALL)
    if code_block_match:
        result = _try_parse_yaml(code_block_match.group(1).strip())
        if result:
            return result

    # Strategy 3: Everything before **CHANGELOG:** or CHANGELOG:
    changelog_match = re.search(r"\*?\*?CHANGELOG\*?\*?\s*:", response)
    if changelog_match:
        yaml_text = response[: changelog_match.start()].strip()
        yaml_text = re.sub(r"^```(?:yaml)?\s*\n?", "", yaml_text)
        yaml_text = re.sub(r"\n?```\s*$", "", yaml_text)
        result = _try_parse_yaml(yaml_text)
        if result:
            return result

    # Strategy 4: Try parsing the entire response as YAML (last resort)
    result = _try_parse_yaml(response)
    if result:
        return result

    raise ValueError(
        f"Could not extract valid YAML from LLM response. "
        f"Response preview: {response[:300]}"
    )


def _extract_changelog(response: str) -> str:
    """Extract the changelog section from an LLM response.

    Args:
        response: The raw LLM response text.

    Returns:
        The changelog text, or a default message if not found.
    """
    # Look for **CHANGELOG:** or CHANGELOG: section
    match = re.search(r"\*?\*?CHANGELOG\*?\*?\s*:\s*\n(.*)", response, re.DOTALL)
    if match:
        return match.group(1).strip()

    return "No changelog provided by the optimizer."


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

    prompt = OPTIMIZER_PROMPT.format(
        n=n_total,
        n_success=n_success,
        n_fail=n_fail,
        current_skill_yaml=skill_to_yaml_string(current_skill),
        dev_failure_details=_format_failure_details(dev_failures),
        dev_success_summaries=_format_success_summaries(dev_successes),
    )

    last_error = None
    for attempt in range(3):
        messages = [{"role": "user", "content": prompt}]
        result = client.chat(
            messages,
            purpose=f"optimize_skill_{task_type}",
        )

        response_text = result["response"]

        try:
            # Extract YAML skill and changelog from the response
            optimized_skill = extract_yaml_from_response(response_text)
            changelog = _extract_changelog(response_text)

            # Save the optimized skill
            output_path = f"skills/orqa/v2_optimized/{task_type}.yaml"
            save_skill(optimized_skill, output_path)

            return optimized_skill, changelog

        except (ValueError, yaml.YAMLError) as e:
            last_error = e
            if attempt < 2:
                # Add instruction for cleaner YAML on retry
                prompt += (
                    "\n\nIMPORTANT: Your previous response had YAML formatting errors. "
                    "Ensure ALL string values containing colons are properly quoted "
                    "with single quotes. Use > or | YAML block scalar syntax for long text."
                )
                continue

    raise ValueError(
        f"Failed to extract optimized skill after 3 attempts. "
        f"Last error: {last_error}"
    )
