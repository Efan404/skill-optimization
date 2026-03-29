# CLAUDE.md

## Local Worktree Convention

- Create repository-local worktrees in `.worktrees/`.
- Treat `.worktrees/` as the default location for isolated feature work in this repository.
- Keep the main workspace clean; use a worktree when doing substantial implementation or parallel development.

## Required Workflow

- Use the available superpowers skills as part of normal execution, not as an optional extra.
- Apply the relevant skill before implementation, debugging, planning, or review.
- Typical expected flow:
  - `using-superpowers`
  - `brainstorming` for design or feature shaping
  - `writing-plans` for multi-step implementation
  - `using-git-worktrees` before isolated feature work
  - `systematic-debugging` for bugs and unexpected behavior
  - `verification-before-completion` before claiming success

## Commit Policy

- Follow atomic commit discipline.
- Keep each commit focused on one logical unit of change.
- Separate documentation, infrastructure, runtime fixes, and experimental logic unless they must land together.
- Make changes easy to review, test, and revert.

## Repository Expectations

- Prefer explicit experiment contracts over implicit conventions.
- Keep SkillsBench and ORQA workstreams clearly separated unless a file is intentionally shared infrastructure.
- Do not claim a spec is implemented unless the corresponding artifacts, validation, and run outputs actually exist.
