"""Evaluator module: answer extraction, single evaluation, and outcome labels.

Provides a 3-tier answer extraction strategy for multiple-choice (A-D) LLM
responses, per-question correctness evaluation, cross-condition outcome
labelling, and a convenience function to evaluate an entire condition.
"""

from __future__ import annotations

import re


def extract_answer(response: str) -> str | None:
    """Extract A/B/C/D from an LLM response using a 3-tier strategy.

    1. Regex ``ANSWER:\\s*([A-D])`` in the **last 5 lines** of the response.
    2. Fallback ``(?:answer|choice|option)\\s*(?:is|:)\\s*([A-D])`` (case-insensitive,
       searched over the full response).
    3. Last non-whitespace character of the response, if it is A-D.

    Returns the extracted letter uppercased, or ``None`` if all tiers fail.
    """
    if not response or not response.strip():
        return None

    # --- Tier 1: ANSWER: X in last 5 lines ---
    last_5_lines = "\n".join(response.strip().splitlines()[-5:])
    m = re.search(r"ANSWER:\s*([A-Da-d])", last_5_lines)
    if m:
        return m.group(1).upper()

    # --- Tier 2: fallback pattern over full response ---
    m = re.search(
        r"(?:answer|choice|option)\s*(?:is|:)\s*([A-Da-d])",
        response,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).upper()

    # --- Tier 3: last non-whitespace character ---
    stripped = response.rstrip()
    if stripped:
        last_char = stripped[-1].upper()
        if last_char in "ABCD":
            return last_char

    return None


def evaluate_single(extracted: str | None, correct: str) -> str:
    """Compare an extracted answer to the correct answer.

    Returns:
        ``'correct'``           if they match (case-insensitive),
        ``'incorrect'``         if they don't,
        ``'extraction_failed'`` if *extracted* is ``None``.
    """
    if extracted is None:
        return "extraction_failed"
    if extracted.upper() == correct.upper():
        return "correct"
    return "incorrect"


def compute_outcome_labels(
    baseline_results: dict,
    condition_results: dict,
) -> dict:
    """Compute per-question cross-condition outcome labels.

    Both *baseline_results* and *condition_results* are dicts of the form
    ``{question_id: {"outcome": "correct"|"incorrect"|"extraction_failed", ...}}``.

    Returns ``{question_id: label}`` where *label* is one of:
        - ``'improved'``            — baseline not correct, condition correct
        - ``'degraded'``            — baseline correct, condition not correct
        - ``'no_change_correct'``   — both correct
        - ``'no_change_incorrect'`` — both not correct
    """
    labels: dict[str, str] = {}
    for qid in condition_results:
        baseline_correct = baseline_results.get(qid, {}).get("outcome") == "correct"
        condition_correct = condition_results[qid]["outcome"] == "correct"

        if baseline_correct and condition_correct:
            labels[qid] = "no_change_correct"
        elif not baseline_correct and condition_correct:
            labels[qid] = "improved"
        elif baseline_correct and not condition_correct:
            labels[qid] = "degraded"
        else:
            labels[qid] = "no_change_incorrect"

    return labels


def evaluate_condition(
    questions: list[dict],
    responses: dict[str, str],
) -> dict:
    """Evaluate all questions for one experimental condition.

    Args:
        questions: List of question dicts, each with at least ``"id"`` and
            ``"correct_answer"`` keys.
        responses: Mapping of ``{question_id: raw_response_string}``.

    Returns:
        ``{question_id: {"extracted": str|None, "correct": str,
        "outcome": str, "response": str}}``
    """
    results: dict = {}
    for q in questions:
        qid = q["id"]
        correct = q["correct_answer"]
        raw_response = responses.get(qid, "")

        extracted = extract_answer(raw_response) if raw_response else None
        outcome = evaluate_single(extracted, correct)

        results[qid] = {
            "extracted": extracted,
            "correct": correct,
            "outcome": outcome,
            "response": raw_response,
        }

    return results
