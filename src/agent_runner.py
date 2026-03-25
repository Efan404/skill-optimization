"""Agent runner — build prompts from templates, call LLM, return raw responses.

Supports five experimental conditions:
  - baseline: plain prompt, no skill/scaffold
  - generic_scaffold: length-matched generic problem-solving scaffold
  - v0_self_generated: LLM-generated skill
  - v1_curated: hand-designed domain-specific skill
  - v2_optimized: iteratively refined skill
"""

from src.llm_client import LLMClient
from src.skill_manager import skill_to_yaml_string

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

BASELINE_PROMPT = """You are an expert in operations research. Solve the following multiple-choice problem.

**Problem:**
{question}

**Options:**
A) {choice_a}
B) {choice_b}
C) {choice_c}
D) {choice_d}

Think through this step by step, then provide your final answer.

**IMPORTANT:** Your final line MUST be exactly: "ANSWER: X" where X is A, B, C, or D."""

SCAFFOLD_PROMPT = """You are an expert in operations research. You have been given a structured problem-solving guide. Follow the procedure carefully.

**GUIDE:**
{scaffold_yaml}

**Problem:**
{question}

**Options:**
A) {choice_a}
B) {choice_b}
C) {choice_c}
D) {choice_d}

Follow the procedure step by step, then provide your final answer.

**IMPORTANT:** Your final line MUST be exactly: "ANSWER: X" where X is A, B, C, or D."""

SKILL_PROMPT = """You are an expert in operations research. You have been given a structured skill to guide your problem-solving approach. Follow the skill's procedure carefully.

**SKILL:**
{skill_yaml}

**Problem:**
{question}

**Options:**
A) {choice_a}
B) {choice_b}
C) {choice_c}
D) {choice_d}

Follow the skill procedure step by step, then provide your final answer.

**IMPORTANT:** Your final line MUST be exactly: "ANSWER: X" where X is A, B, C, or D."""

# Conditions that use a skill YAML (as opposed to scaffold or no skill)
_SKILL_CONDITIONS = {"v0_self_generated", "v1_curated", "v2_optimized"}
_SCAFFOLD_CONDITIONS = {"generic_scaffold"}
_ALL_CONDITIONS = {"baseline"} | _SCAFFOLD_CONDITIONS | _SKILL_CONDITIONS


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_prompt(
    question: dict, condition: str, skill: dict | None = None
) -> list[dict]:
    """Build chat messages for a given condition.

    Args:
        question: A question dict with keys 'question' and 'choices' (A-D).
        condition: One of 'baseline', 'generic_scaffold', 'v0_self_generated',
                   'v1_curated', 'v2_optimized'.
        skill: The skill/scaffold dict.  Required for all conditions except
               'baseline'.

    Returns:
        A list of message dicts ``[{"role": "user", "content": "..."}]``.

    Raises:
        ValueError: If the condition is unknown or a required skill is missing.
    """
    if condition not in _ALL_CONDITIONS:
        raise ValueError(
            f"Unknown condition: {condition!r}. "
            f"Valid conditions: {sorted(_ALL_CONDITIONS)}"
        )

    choices = question["choices"]
    fmt_kwargs = {
        "question": question["question"],
        "choice_a": choices["A"],
        "choice_b": choices["B"],
        "choice_c": choices["C"],
        "choice_d": choices["D"],
    }

    if condition == "baseline":
        content = BASELINE_PROMPT.format(**fmt_kwargs)

    elif condition in _SCAFFOLD_CONDITIONS:
        if skill is None:
            raise ValueError(
                f"Condition '{condition}' requires a scaffold skill, but None was provided."
            )
        fmt_kwargs["scaffold_yaml"] = skill_to_yaml_string(skill)
        content = SCAFFOLD_PROMPT.format(**fmt_kwargs)

    else:
        # v0_self_generated, v1_curated, v2_optimized
        if skill is None:
            raise ValueError(
                f"Condition '{condition}' requires a skill, but None was provided."
            )
        fmt_kwargs["skill_yaml"] = skill_to_yaml_string(skill)
        content = SKILL_PROMPT.format(**fmt_kwargs)

    return [{"role": "user", "content": content}]


def run_single(
    client: LLMClient,
    question: dict,
    condition: str,
    skill: dict | None = None,
) -> dict:
    """Run a single question under a single condition.

    Builds the appropriate prompt, calls the LLM, and returns the result
    along with metadata.

    Args:
        client: An initialised LLMClient instance.
        question: A question dict (must include 'id', 'question', 'choices').
        condition: The experimental condition name.
        skill: Optional skill/scaffold dict (required for non-baseline
               conditions).

    Returns:
        A dict with keys:
            - question_id (str)
            - condition (str)
            - response (str): raw LLM response text
            - model (str)
            - tokens_used (int)
    """
    messages = build_prompt(question, condition, skill=skill)
    purpose = f"{condition}_{question['id']}"
    result = client.chat(messages, purpose=purpose)

    return {
        "question_id": question["id"],
        "condition": condition,
        "response": result["response"],
        "model": result["model"],
        "tokens_used": result["tokens_used"],
    }


def run_condition(
    client: LLMClient,
    questions: list[dict],
    condition: str,
    skill: dict | None = None,
) -> dict:
    """Run all questions for a single condition.

    Iterates over the list of questions, calling :func:`run_single` for each.

    Args:
        client: An initialised LLMClient instance.
        questions: A list of question dicts.
        condition: The experimental condition name.
        skill: Optional skill/scaffold dict.

    Returns:
        A dict mapping ``question_id -> run_single result``.
    """
    results: dict[str, dict] = {}
    for question in questions:
        try:
            result = run_single(client, question, condition, skill=skill)
            results[result["question_id"]] = result
        except Exception as e:
            # Log failure but continue with remaining questions.
            # A transient API error should not abort the entire condition.
            qid = question.get("id", "unknown")
            results[qid] = {
                "question_id": qid,
                "condition": condition,
                "response": "",
                "model": getattr(client, "config", {}).get("model", "unknown"),
                "tokens_used": 0,
                "error": str(e),
            }
    return results
