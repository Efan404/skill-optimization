#!/usr/bin/env python3
"""Deterministic sampling of ORQA instances into seed/dev/test splits.

Reads the raw ORQA validation and test JSONL files and produces:
  - data/orqa/questions.json  (50 instances in our canonical format)
  - data/orqa/split.json      (id lists keyed by split name)

Sampling protocol
-----------------
**Seed (5 from validation):**
  Group validation instances by QUESTION_TYPE.  Within each group sort by
  len(REASONING) descending (ties broken by file order, i.e. stable sort).
  Take the top-1 from each type, iterating over types in sorted order
  (Q1, Q10, Q11, Q2, ...), until 5 are selected.

**Dev + Test (45 from test):**
  Stratified random sample (seed=42) of 45 from the 1 468 test instances.
  Each QUESTION_TYPE with >= 3 instances gets at least 1 in dev.
  Assignment is alternating: 1st sampled -> dev, 2nd -> test, 3rd -> dev, ...
  yielding ~20 dev and ~25 test.

Output format per question:
  {
    "id": "orqa_0001",
    "task_type": "or_model_identification",
    "split": "seed",
    "context": "...",
    "question": "...",
    "choices": {"A": "...", "B": "...", "C": "...", "D": "..."},
    "correct_answer": "A",
    "source_category": 1,
    "source_detail": "ORQA validation set, QUESTION_TYPE Q6, instance index 0",
    "question_subtype": "Q6"
  }
"""

from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
RAW_DIR = Path("/tmp/orqa_raw")
VALIDATION_PATH = RAW_DIR / "ORQA_validation.jsonl"
TEST_PATH = RAW_DIR / "ORQA_test.jsonl"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "data" / "orqa"

ANSWER_MAP = {0: "A", 1: "B", 2: "C", 3: "D"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file, returning a list of dicts."""
    records: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def to_canonical(
    raw: dict,
    *,
    seq: int,
    split: str,
    source_file: str,
    instance_index: int,
) -> dict:
    """Convert a raw ORQA record to our canonical format."""
    opts = raw["OPTIONS"]
    return {
        "id": f"orqa_{seq:04d}",
        "task_type": "or_model_identification",
        "split": split,
        "context": raw["CONTEXT"],
        "question": raw["QUESTION"],
        "choices": {
            "A": opts[0],
            "B": opts[1],
            "C": opts[2],
            "D": opts[3],
        },
        "correct_answer": ANSWER_MAP[raw["TARGET_ANSWER"]],
        "source_category": 1,
        "source_detail": (
            f"ORQA {source_file}, "
            f"QUESTION_TYPE {raw['QUESTION_TYPE']}, "
            f"instance index {instance_index}"
        ),
        "question_subtype": raw["QUESTION_TYPE"],
    }


# ---------------------------------------------------------------------------
# Sampling logic
# ---------------------------------------------------------------------------

def select_seed(validation: list[dict], n: int = 5) -> list[tuple[dict, int]]:
    """Select *n* seed instances from the validation set.

    Algorithm:
      1. Group by QUESTION_TYPE.
      2. Within each group, sort by len(REASONING) descending (stable sort
         preserves original file order for ties).
      3. Iterate over types in sorted order; take top-1 from each type
         until *n* are collected.

    Returns a list of (record, original_index) tuples.
    """
    # Build groups preserving file order via index
    groups: dict[str, list[tuple[dict, int]]] = defaultdict(list)
    for idx, rec in enumerate(validation):
        groups[rec["QUESTION_TYPE"]].append((rec, idx))

    # Sort each group by REASONING length descending (stable)
    for qtype in groups:
        groups[qtype].sort(key=lambda pair: len(pair[0]["REASONING"]), reverse=True)

    selected: list[tuple[dict, int]] = []
    for qtype in sorted(groups.keys()):
        if len(selected) >= n:
            break
        selected.append(groups[qtype][0])  # top-1

    return selected


def select_dev_test(
    test_data: list[dict],
    n: int = 45,
    seed: int = 42,
) -> tuple[list[tuple[dict, int]], list[tuple[dict, int]]]:
    """Select *n* instances from the test set, split into dev and test.

    Algorithm:
      1. Stratified random sample of *n* from test_data by QUESTION_TYPE.
      2. Each type with >= 3 instances gets at least 1 representative in dev.
      3. Alternating assignment: 1st -> dev, 2nd -> test, 3rd -> dev, ...

    Returns (dev_list, test_list) where each element is (record, original_index).
    """
    rng = random.Random(seed)

    # Group by QUESTION_TYPE, preserving original index
    groups: dict[str, list[tuple[dict, int]]] = defaultdict(list)
    for idx, rec in enumerate(test_data):
        groups[rec["QUESTION_TYPE"]].append((rec, idx))

    # Determine per-type sample counts (proportional, rounded)
    type_counts: dict[str, int] = {}
    total = len(test_data)
    remaining = n

    # First pass: allocate proportionally (floor)
    for qtype in sorted(groups.keys()):
        frac = len(groups[qtype]) / total * n
        type_counts[qtype] = int(frac)
        remaining -= type_counts[qtype]

    # Second pass: distribute remainder by largest fractional parts
    fractionals = []
    for qtype in sorted(groups.keys()):
        frac = len(groups[qtype]) / total * n
        fractionals.append((frac - int(frac), qtype))
    fractionals.sort(key=lambda x: x[0], reverse=True)

    for _, qtype in fractionals:
        if remaining <= 0:
            break
        type_counts[qtype] += 1
        remaining -= 1

    # Sample from each group and do per-type alternating assignment.
    # Within each QUESTION_TYPE, the first sampled instance goes to dev,
    # the second to test, the third to dev, etc.  This guarantees that
    # every type with at least 1 sampled instance has representation in dev.
    dev: list[tuple[dict, int]] = []
    test: list[tuple[dict, int]] = []
    for qtype in sorted(groups.keys()):
        k = type_counts[qtype]
        chosen = rng.sample(groups[qtype], k)
        # Sort chosen by original index for determinism
        chosen.sort(key=lambda pair: pair[1])
        for i, item in enumerate(chosen):
            if i % 2 == 0:
                dev.append(item)
            else:
                test.append(item)

    # Verify that each type with >= 3 instances has at least 1 in dev
    dev_types = {rec["QUESTION_TYPE"] for rec, _ in dev}
    for qtype in sorted(groups.keys()):
        if len(groups[qtype]) >= 3 and qtype not in dev_types:
            # This shouldn't happen with alternating assignment on a
            # stratified sample, but guard against it.
            print(f"WARNING: {qtype} has >= 3 instances but none in dev", file=sys.stderr)

    return dev, test


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # Load raw data
    validation = load_jsonl(VALIDATION_PATH)
    test_data = load_jsonl(TEST_PATH)
    print(f"Loaded {len(validation)} validation instances, {len(test_data)} test instances")

    # --- Seed selection (from validation) ---
    seed_items = select_seed(validation, n=5)
    print(f"\nSeed: {len(seed_items)} instances selected from validation")

    # --- Dev/test selection (from test) ---
    dev_items, test_items = select_dev_test(test_data, n=45, seed=42)
    print(f"Dev:  {len(dev_items)} instances selected from test")
    print(f"Test: {len(test_items)} instances selected from test")

    # --- Convert to canonical format ---
    questions: list[dict] = []
    seq = 1

    for rec, orig_idx in seed_items:
        questions.append(to_canonical(
            rec, seq=seq, split="seed",
            source_file="validation set", instance_index=orig_idx,
        ))
        seq += 1

    for rec, orig_idx in dev_items:
        questions.append(to_canonical(
            rec, seq=seq, split="dev",
            source_file="test set", instance_index=orig_idx,
        ))
        seq += 1

    for rec, orig_idx in test_items:
        questions.append(to_canonical(
            rec, seq=seq, split="test",
            source_file="test set", instance_index=orig_idx,
        ))
        seq += 1

    # --- Build split.json ---
    split_map: dict[str, list[str]] = {"seed": [], "dev": [], "test": []}
    for q in questions:
        split_map[q["split"]].append(q["id"])

    # --- Write output ---
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    questions_path = OUT_DIR / "questions.json"
    with open(questions_path, "w", encoding="utf-8") as fh:
        json.dump(questions, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"\nWrote {len(questions)} questions to {questions_path}")

    split_path = OUT_DIR / "split.json"
    with open(split_path, "w", encoding="utf-8") as fh:
        json.dump(split_map, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"Wrote split map to {split_path}")

    # --- Summary statistics ---
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    # Per-split counts
    print(f"\n{'Split':<8} {'Count':>5}")
    print("-" * 15)
    for s in ("seed", "dev", "test"):
        print(f"{s:<8} {len(split_map[s]):>5}")
    print(f"{'TOTAL':<8} {sum(len(v) for v in split_map.values()):>5}")

    # Per-QUESTION_TYPE distribution across splits
    type_split: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for q in questions:
        type_split[q["question_subtype"]][q["split"]] += 1

    print(f"\n{'QType':<8} {'seed':>5} {'dev':>5} {'test':>5} {'total':>6}")
    print("-" * 32)
    for qtype in sorted(type_split.keys()):
        row = type_split[qtype]
        total = sum(row.values())
        print(f"{qtype:<8} {row.get('seed', 0):>5} {row.get('dev', 0):>5} {row.get('test', 0):>5} {total:>6}")

    # Answer distribution
    ans_dist: dict[str, int] = defaultdict(int)
    for q in questions:
        ans_dist[q["correct_answer"]] += 1
    print(f"\nAnswer distribution: {dict(sorted(ans_dist.items()))}")

    print("\nDone.")


if __name__ == "__main__":
    main()
