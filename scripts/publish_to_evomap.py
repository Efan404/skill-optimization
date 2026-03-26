#!/usr/bin/env python3
"""Publish a SkillsBench skill to EvoMap as a Gene+Capsule bundle.

Usage:
    python scripts/publish_to_evomap.py overfull_hbox
    python scripts/publish_to_evomap.py db_wal_recovery
    python scripts/publish_to_evomap.py feal_differential_cryptanalysis
    python scripts/publish_to_evomap.py --list          # show available skills
    python scripts/publish_to_evomap.py --hello         # register node only
"""

import argparse
import sys
from pathlib import Path

# Add project root to path so we can import src modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.evomap_publisher import (
    hello,
    publish_skill,
    DEFAULT_SENDER_ID,
)


SKILLS_DIR = PROJECT_ROOT / "skills" / "skillsbench" / "curated"

SKILL_MAP = {
    "overfull_hbox": SKILLS_DIR / "overfull_hbox.yaml",
    "db_wal_recovery": SKILLS_DIR / "db_wal_recovery.yaml",
    "feal_differential_cryptanalysis": SKILLS_DIR / "feal_differential_cryptanalysis.yaml",
}


def list_skills():
    print("Available SkillsBench curated skills for publishing:\n")
    for name, path in SKILL_MAP.items():
        status = "✓ exists" if path.exists() else "✗ missing"
        print(f"  {name:<35} {status}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Publish a skill to EvoMap")
    parser.add_argument(
        "skill_name",
        nargs="?",
        help="Skill name (e.g. overfull_hbox, db_wal_recovery, feal_differential_cryptanalysis)",
    )
    parser.add_argument("--list", action="store_true", help="List available skills and exit")
    parser.add_argument("--hello", action="store_true", help="Register node only, don't publish")
    args = parser.parse_args()

    if args.list:
        list_skills()
        return

    if args.hello:
        print(f"[evomap] Registering node '{DEFAULT_SENDER_ID}' with EvoMap hub...")
        try:
            resp = hello()
            print(f"[evomap] Node registered. Response:\n{resp}")
        except Exception as e:
            print(f"[evomap] ERROR during hello: {e}")
            sys.exit(1)
        return

    if not args.skill_name:
        parser.print_help()
        print("\nAvailable skills:")
        list_skills()
        sys.exit(1)

    skill_path = SKILL_MAP.get(args.skill_name)
    if not skill_path:
        print(f"[evomap] Unknown skill: {args.skill_name!r}")
        print("Available skills:")
        list_skills()
        sys.exit(1)

    if not skill_path.exists():
        print(f"[evomap] Skill file not found: {skill_path}")
        sys.exit(1)

    print(f"[evomap] Publishing skill: {args.skill_name}")
    print(f"[evomap] Skill file: {skill_path}")
    print(f"[evomap] Sender ID: {DEFAULT_SENDER_ID}")
    print()

    try:
        resp = publish_skill(str(skill_path), sender_id=DEFAULT_SENDER_ID)
        print(f"\n[evomap] Publish response:\n{resp}")
        # Extract asset_id from response if present
        if isinstance(resp, dict):
            asset_ids = resp.get("asset_ids", [])
            if asset_ids:
                print(f"\n[evomap] Published asset IDs:")
                for aid in asset_ids:
                    print(f"  {aid}")
            elif "error" in resp:
                print(f"\n[evomap] ERROR from server: {resp['error']}")
                sys.exit(1)
    except Exception as e:
        print(f"[evomap] Publish failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
