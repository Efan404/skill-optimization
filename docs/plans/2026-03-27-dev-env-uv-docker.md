# Dev Environment and Docker Repro Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a repo-level reproducible environment using `uv` for Python dependency management, keep Node dependencies explicit for EvoMap integration, and document a fast-start path for local setup and Docker-based reproduction.

**Architecture:** Python package management moves from ad hoc `requirements.txt` usage to a `pyproject.toml` plus `uv.lock` workflow. Node remains managed by `npm` because the EvoMap SDK bridge is JavaScript-native and already isolated. A root `Dockerfile` installs both runtimes and uses the checked-in dependency manifests so the same commands work locally and in containers.

**Tech Stack:** Python 3.12, uv, pytest, Node.js 24, npm, Docker, Markdown docs

---

### Task 1: Define the Python package metadata and uv workflow

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `uv.lock`
- Modify: `requirements.txt`
- Test: `tests/test_evomap_publisher.py`

**Step 1: Write the failing environment expectation**

Document the current issue in the plan:

- `pytest --collect-only -q tests/test_pipeline_smoke.py` currently fails with `ModuleNotFoundError: No module named 'tqdm'`
- `pytest --collect-only -q tests/test_llm_client.py` currently fails with `ModuleNotFoundError: No module named 'openai'`

This proves the repo lacks a reproducible Python environment bootstrap.

**Step 2: Add package metadata**

Create `pyproject.toml` with:

- project name such as `skill-optimization-demo`
- `requires-python = ">=3.12,<3.13"` to avoid claiming compatibility with the current unvalidated 3.14 runtime
- runtime dependencies migrated from `requirements.txt`
- optional dev dependency group with `pytest`

Create `.python-version` with `3.12`.

**Step 3: Keep requirements compatibility**

Replace `requirements.txt` contents with a small compatibility shim comment block plus `-e .` only if that works cleanly, or generate a minimal pinned export if needed. Do not maintain two independent dependency lists.

**Step 4: Generate the lock file**

Run:

```bash
uv lock
```

Expected: `uv.lock` is created successfully.

**Step 5: Verify the environment**

Run:

```bash
uv sync --dev
uv run pytest tests/test_evomap_publisher.py -q
```

Expected: `7 passed`

**Step 6: Commit**

```bash
git add pyproject.toml .python-version uv.lock requirements.txt
git commit -m "build: add uv-managed Python environment"
```

### Task 2: Add repo-level Docker support

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`
- Modify: `.gitignore`
- Test: `tests/test_evomap_publisher.py`

**Step 1: Define the container contract**

The Docker image must:

- install Python 3.12 and `uv`
- install Node.js 24 and npm
- install Python deps via `uv sync --frozen --dev`
- install Node deps via `npm ci`
- default to a shell or a neutral command, not an eager experiment run

**Step 2: Implement the Dockerfile**

Create a root `Dockerfile` using a slim Python 3.12 base. Install curl/ca-certificates and Node.js 24. Copy `pyproject.toml`, `uv.lock`, `package.json`, and `package-lock.json` first for cache efficiency, install dependencies, then copy the repo.

**Step 3: Add Docker ignore rules**

Create `.dockerignore` to exclude:

- `.git`
- `.worktrees`
- `.venv`
- `node_modules`
- `results`
- `__pycache__`
- `.pytest_cache`
- `.env`
- `.evomap_secrets.json`

**Step 4: Verify container build**

Run:

```bash
docker build -t skill-optimization-dev .
```

Expected: image builds successfully.

**Step 5: Verify container workflow**

Run:

```bash
docker run --rm skill-optimization-dev uv run pytest tests/test_evomap_publisher.py -q
```

Expected: `7 passed`

**Step 6: Commit**

```bash
git add Dockerfile .dockerignore .gitignore
git commit -m "build: add repo-level Docker reproduction image"
```

### Task 3: Add command-level ergonomics for local users

**Files:**
- Modify: `package.json`
- Modify: `README.md`
- Create: `docs/setup_and_repro.md`
- Test: `README.md`

**Step 1: Add npm helper scripts**

Update `package.json` with scripts such as:

- `evomap:build`
- `evomap:list`

Only add scripts that remove friction for real workflows already present in the repo.

**Step 2: Restructure README**

Make `README.md` focus on:

- what the repo is
- fastest local setup
- fastest Docker setup
- where detailed docs live

Do not overload the README with every caveat.

**Step 3: Write dedicated setup/repro doc**

Create `docs/setup_and_repro.md` that covers:

- required tools
- `uv sync --dev`
- `npm ci`
- `.env` setup
- common commands
- Docker build and run examples
- EvoMap-specific note that publish credentials live in `.evomap_secrets.json`

**Step 4: Review docs against actual commands**

Manually execute every command written into README and `docs/setup_and_repro.md`, or adjust docs so every documented command is known-good.

**Step 5: Commit**

```bash
git add package.json README.md docs/setup_and_repro.md
git commit -m "docs: add local and Docker reproduction guide"
```

### Task 4: Full verification and branch handoff

**Files:**
- Modify if needed: `README.md`
- Modify if needed: `docs/setup_and_repro.md`
- Modify if needed: `Dockerfile`
- Modify if needed: `pyproject.toml`

**Step 1: Verify local workflow**

Run:

```bash
uv sync --dev
npm ci
uv run pytest tests/test_evomap_publisher.py -q
python3 scripts/publish_to_evomap.py --list
```

Expected:

- dependency installation succeeds
- tests pass
- SkillsBench curated skills list prints correctly

**Step 2: Verify Docker workflow**

Run:

```bash
docker build -t skill-optimization-dev .
docker run --rm skill-optimization-dev uv run pytest tests/test_evomap_publisher.py -q
docker run --rm skill-optimization-dev python3 scripts/publish_to_evomap.py --list
```

Expected:

- image builds
- tests pass in container
- CLI works in container without credentials

**Step 3: Inspect the final diff**

Run:

```bash
git diff --stat main...HEAD
git status --short
```

Expected: only intended environment, Docker, and documentation files changed.

**Step 4: Commit**

```bash
git add pyproject.toml .python-version uv.lock requirements.txt Dockerfile .dockerignore .gitignore package.json README.md docs/setup_and_repro.md
git commit -m "feat: add reproducible dev environment and Docker workflow"
```
