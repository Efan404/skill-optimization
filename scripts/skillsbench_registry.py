"""Canonical condition registry for SkillsBench.

Single source of truth for condition names, task identifiers, skill paths,
and job-name parsing/generation used across all SkillsBench workstreams.
"""

from __future__ import annotations

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Conditions
# ---------------------------------------------------------------------------

CONDITIONS: list[str] = [
    "baseline",
    "generic_scaffold",
    "curated",
    "self_generated_one_shot",
    "self_generated_optimized",
    "curated_optimized",
]

PILOT_CONDITIONS: list[str] = CONDITIONS[:4]

# Explicit mapping — intentionally NOT constructed via string concatenation.
OPTIMIZED_CONDITION: dict[str, str] = {
    "self_generated_one_shot": "self_generated_optimized",
    "curated": "curated_optimized",
}

# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

TASKS: dict[str, str] = {
    "overfull-hbox": "overfull_hbox",
    "db-wal-recovery": "db_wal_recovery",
    "feal-differential-cryptanalysis": "feal_differential_cryptanalysis",
}

TASK_SHORT: dict[str, str] = {
    "overfull-hbox": "overfull",
    "db-wal-recovery": "dbwal",
    "feal-differential-cryptanalysis": "feal",
}

_SHORT_TO_TASK: dict[str, str] = {v: k for k, v in TASK_SHORT.items()}

# ---------------------------------------------------------------------------
# Author model provenance
# ---------------------------------------------------------------------------

AUTHOR_MODEL: dict[str, Optional[str]] = {
    "baseline": None,
    "generic_scaffold": None,
    "curated": "human",
    "self_generated_one_shot": "claude-opus-4-20250514",
    "self_generated_optimized": "claude-opus-4-20250514",
    "curated_optimized": "human",
}

# ---------------------------------------------------------------------------
# Job-name parsing helpers
# ---------------------------------------------------------------------------

IGNORED_JOB_NAMES: set[str] = {
    "dev-00-overfull-baseline",
    "opencode-api-test",
    "opencode-test-overfull-baseline",
    "overfull-baseline-gemini",
    "overfull-baseline-gemini-v2",
    "overfull-baseline-gemini2flash",
    "overfull-baseline-gemini15pro",
    "overfull-self_generated-gemini",
    "proxy-test-overfull-baseline",
    "proxy-test2-overfull-baseline",
    "smoke-test-overfull-baseline",
}

JOB_NAME_ALIASES: dict[str, tuple[str, str]] = {
    "smoke-deepseek-baseline": ("overfull-hbox", "baseline"),
    "feal-self_generated-deepseek": (
        "feal-differential-cryptanalysis",
        "self_generated_one_shot",
    ),
    "overfull-self_generated-deepseek": ("overfull-hbox", "self_generated_one_shot"),
}

_SOLVER_MODEL = "deepseek/deepseek-chat"
_SOLVER_SUFFIX = "deepseek"

_CONDITIONS_SET: set[str] = set(CONDITIONS)

# Pre-sort task short names longest-first so greedy prefix matching works.
_TASK_SHORTS_SORTED: list[str] = sorted(
    TASK_SHORT.values(), key=len, reverse=True
)

_ROUND_RE = re.compile(r"-r(\d+)$")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def skill_yaml_path(condition: str, task_id: str) -> Optional[str]:
    """Return the relative skill YAML path for *condition* and *task_id*.

    Returns ``None`` for the ``baseline`` condition (no skill injected).
    Raises ``KeyError`` for an unknown condition.
    """
    if condition not in _CONDITIONS_SET:
        raise KeyError(f"Unknown condition: {condition!r}")

    if condition == "baseline":
        return None

    if condition == "generic_scaffold":
        return "skills/skillsbench/generic_scaffold/generic_task_execution.yaml"

    yaml_stem = TASKS[task_id]
    return f"skills/skillsbench/{condition}/{yaml_stem}.yaml"


def parse_job_name(
    job_name: str,
) -> Optional[tuple[str, str, str, int]]:
    """Parse a job name into ``(task_id, condition, solver_model, round)``.

    Returns ``None`` for ignored, aliased-but-unrecognised, or unknown names.

    Canonical format: ``{task_short}-{condition}-deepseek[-r{round}]``
    """
    if job_name in IGNORED_JOB_NAMES:
        return None

    if job_name in JOB_NAME_ALIASES:
        task_id, condition = JOB_NAME_ALIASES[job_name]
        return (task_id, condition, _SOLVER_MODEL, 1)

    # Strip optional round suffix.
    round_num = 1
    m = _ROUND_RE.search(job_name)
    if m:
        round_num = int(m.group(1))
        job_name = job_name[: m.start()]

    # Must end with solver suffix.
    if not job_name.endswith(f"-{_SOLVER_SUFFIX}"):
        return None
    job_name = job_name[: -(len(_SOLVER_SUFFIX) + 1)]

    # Try each task short-name prefix (longest first).
    for short in _TASK_SHORTS_SORTED:
        prefix = f"{short}-"
        if job_name.startswith(prefix):
            remainder = job_name[len(prefix) :]
            if remainder in _CONDITIONS_SET:
                task_id = _SHORT_TO_TASK[short]
                return (task_id, remainder, _SOLVER_MODEL, round_num)

    return None


def make_job_name(task_id: str, condition: str, round_num: int) -> str:
    """Build the canonical job name for a run."""
    short = TASK_SHORT[task_id]
    return f"{short}-{condition}-{_SOLVER_SUFFIX}-r{round_num}"
