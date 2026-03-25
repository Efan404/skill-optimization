"""Error Analyzer — LLM-assisted root cause classification (Layer 2, dev only)."""

import json
from pathlib import Path

from src.llm_client import LLMClient

ROOT_CAUSE_CODES = [
    "task_misunderstood",
    "constraint_missed",
    "wrong_reasoning",
    "calculation_error",
    "skill_mismatch",
    "skill_overfit",
    "verbosity_overload",
    "hallucinated_procedure",
]

ERROR_ANALYSIS_PROMPT = """You are an expert at diagnosing reasoning failures in LLM outputs.

Given a question, the correct answer, and the LLM's response, classify WHY the LLM got it wrong.

**Question:** {question}
**Correct Answer:** {correct_answer}
**LLM's Response:** {response}
**Condition:** {condition} (the prompting strategy used)

Classify the failure into one or more of these root cause categories:
- task_misunderstood: LLM misread the problem
- constraint_missed: A constraint from the problem was ignored
- wrong_reasoning: Reasoning steps are logically flawed
- calculation_error: Math or arithmetic mistake
- skill_mismatch: Skill doesn't fit this task type
- skill_overfit: LLM followed skill too rigidly, missed nuance
- verbosity_overload: Skill too long, LLM lost focus
- hallucinated_procedure: LLM invented steps not in the skill

Respond with ONLY valid JSON (no markdown, no explanation outside JSON):
{{"root_causes": ["category1", "category2"], "explanation": "Brief explanation of what went wrong"}}"""


def _assert_dev_split(question: dict) -> None:
    """Validate that a question belongs to the dev split.

    Raises:
        ValueError: If the question's split is not 'dev'.
    """
    split = question.get("split")
    if split != "dev":
        raise ValueError(
            f"Split assertion failed: expected split='dev', got split='{split}' "
            f"for question '{question.get('id', 'unknown')}'. "
            f"Error analysis must only be performed on dev data."
        )


def analyze_single_failure(
    client: LLMClient,
    question: dict,
    response: str,
    condition: str,
) -> dict:
    """Use LLM to classify why a specific answer was wrong.

    ASSERTION: question["split"] must be "dev". Raises ValueError if not.

    Args:
        client: An initialized LLMClient instance.
        question: The question dict (must have split=="dev").
        response: The LLM's incorrect response text.
        condition: The prompting condition used (e.g. 'baseline', 'v1_curated').

    Returns:
        Dict with keys:
            - root_causes (list[str]): One or more root cause codes.
            - explanation (str): Brief explanation of what went wrong.
    """
    _assert_dev_split(question)

    prompt = ERROR_ANALYSIS_PROMPT.format(
        question=question["question"],
        correct_answer=question["correct_answer"],
        response=response,
        condition=condition,
    )

    messages = [{"role": "user", "content": prompt}]
    result = client.chat(
        messages,
        purpose=f"error_analysis_{condition}_{question.get('id', 'unknown')}",
    )

    # Parse the JSON response from the LLM
    try:
        analysis = json.loads(result["response"])
    except json.JSONDecodeError:
        # Attempt to extract JSON from the response if it contains extra text
        raw = result["response"]
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            try:
                analysis = json.loads(raw[start:end])
            except json.JSONDecodeError:
                analysis = {
                    "root_causes": ["wrong_reasoning"],
                    "explanation": f"Failed to parse LLM analysis. Raw: {raw[:200]}",
                }
        else:
            analysis = {
                "root_causes": ["wrong_reasoning"],
                "explanation": f"Failed to parse LLM analysis. Raw: {raw[:200]}",
            }

    # Validate root cause codes — filter to only known codes
    valid_causes = [c for c in analysis.get("root_causes", []) if c in ROOT_CAUSE_CODES]
    if not valid_causes:
        valid_causes = ["wrong_reasoning"]  # safe fallback

    return {
        "root_causes": valid_causes,
        "explanation": analysis.get("explanation", "No explanation provided."),
    }


def analyze_dev_failures(
    client: LLMClient,
    dev_questions: list[dict],
    dev_results: dict,
) -> dict:
    """Analyze all incorrect answers on the dev set.

    ASSERTION: all questions must have split=="dev". Raises ValueError if any
    test question is found.

    Args:
        client: An initialized LLMClient instance.
        dev_questions: List of question dicts, all with split=="dev".
        dev_results: Dict structured as:
            {condition: {question_id: {"outcome": str, "response": str, ...}}}

    Returns:
        Dict structured as:
            {condition: {question_id: {"root_causes": [...], "explanation": "..."}}}

    Side effects:
        Saves analysis to results/analysis/dev_error_analysis.json.
    """
    # Validate ALL questions have split=="dev"
    for q in dev_questions:
        _assert_dev_split(q)

    # Build a lookup from question ID to question dict
    q_lookup = {q["id"]: q for q in dev_questions}

    analysis_results: dict = {}

    for condition, condition_results in dev_results.items():
        analysis_results[condition] = {}

        for question_id, result_data in condition_results.items():
            outcome = result_data.get("outcome", "")

            # Only analyze failures (incorrect or extraction_failed)
            if outcome not in ("incorrect", "extraction_failed"):
                continue

            question = q_lookup.get(question_id)
            if question is None:
                continue  # skip if question not found in dev set

            response_text = result_data.get("response", "")
            single_analysis = analyze_single_failure(
                client=client,
                question=question,
                response=response_text,
                condition=condition,
            )
            analysis_results[condition][question_id] = single_analysis

    # Save results to disk
    output_dir = Path("results") / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "dev_error_analysis.json"

    with open(output_path, "w") as f:
        json.dump(analysis_results, f, indent=2)

    return analysis_results
