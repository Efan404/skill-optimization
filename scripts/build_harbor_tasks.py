#!/usr/bin/env python3
"""Build Harbor-compatible task directories for all conditions × tasks.

Creates task directories under data/skillsbench/harbor_tasks/ with:
- Baseline: no skills_dir
- Generic scaffold: SKILL.md from generic scaffold YAML
- Curated: SKILL.md from curated YAML
- Self-generated one-shot: SKILL.md from self-generated YAML
- Self-generated optimized: (placeholder, built after dev optimization)
- Curated optimized: (placeholder, built after dev optimization)

Each directory mirrors the original task structure from terminal-bench-2-inspect
with an optional environment/skills/ overlay.
"""

import shutil
import textwrap
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TERMINAL_BENCH = Path("/Users/efan404/Codes/research/terminal-bench-2-inspect")
OUTPUT_DIR = PROJECT_ROOT / "data" / "skillsbench" / "harbor_tasks"

TASKS = {
    "overfull-hbox": "overfull_hbox",
    "db-wal-recovery": "db_wal_recovery",
    "feal-differential-cryptanalysis": "feal_differential_cryptanalysis",
}

CONDITIONS = [
    "baseline",
    "generic_scaffold",
    "curated",
    "self_generated_one_shot",
    "self_generated_optimized",
    "curated_optimized",
]

SKILL_PATHS = {
    "generic_scaffold": lambda task_yaml: PROJECT_ROOT / "skills" / "skillsbench" / "generic_scaffold" / "generic_task_execution.yaml",
    "curated": lambda task_yaml: PROJECT_ROOT / "skills" / "skillsbench" / "curated" / f"{task_yaml}.yaml",
    "self_generated_one_shot": lambda task_yaml: PROJECT_ROOT / "skills" / "skillsbench" / "self_generated_one_shot" / f"{task_yaml}.yaml",
    "self_generated_optimized": lambda task_yaml: PROJECT_ROOT / "skills" / "skillsbench" / "self_generated_optimized" / f"{task_yaml}.yaml",
    "curated_optimized": lambda task_yaml: PROJECT_ROOT / "skills" / "skillsbench" / "curated_optimized" / f"{task_yaml}.yaml",
}


def yaml_skill_to_markdown(yaml_path: Path) -> str:
    """Convert a YAML skill file to SKILL.md Markdown format."""
    with open(yaml_path) as f:
        skill = yaml.safe_load(f)

    name = skill.get("name", "skill")
    description = skill.get("when_to_use", "")

    lines = []
    lines.append(f"---")
    lines.append(f"name: {name}")
    lines.append(f"description: {description.strip()}")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"# {name}")
    lines.append(f"")

    # When to use
    if skill.get("when_to_use"):
        lines.append(f"## When to Use")
        lines.append(f"{skill['when_to_use'].strip()}")
        lines.append(f"")

    # Preconditions
    if skill.get("preconditions"):
        lines.append(f"## Preconditions")
        for pre in skill["preconditions"]:
            lines.append(f"- {pre}")
        lines.append(f"")

    # Procedure
    if skill.get("procedure"):
        lines.append(f"## Procedure")
        lines.append(f"")
        for i, step_obj in enumerate(skill["procedure"], 1):
            step_text = step_obj.get("step", "")
            lines.append(f"### Step {i}")
            lines.append(f"{step_text.strip()}")
            lines.append(f"")
            if step_obj.get("check"):
                lines.append(f"**Check:** {step_obj['check'].strip()}")
                lines.append(f"")

    # Common failures
    if skill.get("common_failures"):
        lines.append(f"## Common Failures")
        lines.append(f"")
        for failure in skill["common_failures"]:
            if isinstance(failure, str):
                lines.append(f"- {failure.strip()}")
            else:
                lines.append(f"- {str(failure).strip()}")
        lines.append(f"")

    # Verification
    if skill.get("verification"):
        lines.append(f"## Verification")
        verification = skill["verification"]
        if isinstance(verification, str):
            lines.append(f"{verification.strip()}")
        elif isinstance(verification, list):
            for v in verification:
                lines.append(f"- {str(v).strip()}")
        lines.append(f"")

    return "\n".join(lines)


def copy_task_base(task_name: str, dest: Path):
    """Copy task files from terminal-bench-2-inspect, excluding solution/."""
    src = TERMINAL_BENCH / task_name
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    # Copy task.toml, instruction.md, tests/
    for item in ["task.toml", "instruction.md"]:
        src_path = src / item
        if src_path.exists():
            shutil.copy2(src_path, dest / item)

    # Copy tests directory
    tests_src = src / "tests"
    if tests_src.exists():
        shutil.copytree(tests_src, dest / "tests")

    # Copy environment directory (Dockerfile etc)
    env_src = src / "environment"
    if env_src.exists():
        shutil.copytree(env_src, dest / "environment")


def add_skills_dir_to_toml(toml_path: Path):
    """Add skills_dir = '/skills' to the [environment] section of task.toml."""
    content = toml_path.read_text()
    if 'skills_dir' not in content:
        content = content.replace(
            '[environment]',
            '[environment]\nskills_dir = "/skills"'
        )
        toml_path.write_text(content)


def build_condition_dir(task_name: str, task_yaml: str, condition: str):
    """Build a single condition directory for a task."""
    dest = OUTPUT_DIR / task_name / condition
    print(f"  Building {task_name}/{condition}...")

    # Copy base task files
    copy_task_base(task_name, dest)

    if condition == "baseline":
        # No skill, no skills_dir
        return

    # All non-baseline conditions get a skill
    skill_yaml_path = SKILL_PATHS[condition](task_yaml)
    if not skill_yaml_path.exists():
        print(f"    WARNING: Skill not found: {skill_yaml_path}")
        return

    # Convert YAML to SKILL.md
    skill_md = yaml_skill_to_markdown(skill_yaml_path)

    # Create skills directory in environment
    skill_name = f"task-{condition.replace('_', '-')}"
    skills_dest = dest / "environment" / "skills" / skill_name
    skills_dest.mkdir(parents=True, exist_ok=True)
    (skills_dest / "SKILL.md").write_text(skill_md)

    # Add skills_dir to task.toml
    add_skills_dir_to_toml(dest / "task.toml")


def main():
    print(f"Building Harbor task directories in: {OUTPUT_DIR}")
    print(f"Source tasks from: {TERMINAL_BENCH}")
    print()

    for task_name, task_yaml in TASKS.items():
        print(f"Task: {task_name}")
        for condition in CONDITIONS:
            build_condition_dir(task_name, task_yaml, condition)
        print()

    # Summary
    print("=" * 60)
    print("Build complete. Directory structure:")
    for task_name in TASKS:
        for condition in CONDITIONS:
            d = OUTPUT_DIR / task_name / condition
            has_skill = (d / "environment" / "skills").exists()
            print(f"  {task_name}/{condition}/ {'[+skill]' if has_skill else '[no skill]'}")

    print()
    print("To run a task:")
    print(f"  cd /Users/efan404/Codes/research/harbor-skillsbench")
    print(f"  uv run harbor run --path {OUTPUT_DIR}/<task>/<condition> \\")
    print(f"    --agent claude-code --model anthropic/claude-sonnet-4-20250514")


if __name__ == "__main__":
    main()
