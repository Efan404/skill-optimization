# Setup and Reproduction Guide

This document explains how to set up the repository for local development and
how to reproduce the core workflow inside Docker.

## What This Covers

This repo has two runtime layers:

- Python for the benchmark pipeline, reporting, and EvoMap publisher CLI
- Node.js for the EvoMap SDK bridge used to construct `Gene` and `Capsule`
  assets

The recommended toolchain is:

- `uv` for Python environment management
- `npm` for Node dependencies
- Docker for repo-level reproducibility

## Prerequisites

Install these tools first:

- Python `3.12`
- `uv`
- Node.js `24`
- npm
- Docker

You can confirm your host toolchain with:

```bash
python3 --version
uv --version
node --version
npm --version
docker --version
```

## Local Setup

### 1. Clone the repo

```bash
git clone <repo-url>
cd skill-optimization
```

### 2. Install Python dependencies

```bash
uv sync --dev
```

This creates `.venv/` and installs the project plus development tools.

### 3. Install Node dependencies

```bash
npm ci
```

This is required for the EvoMap SDK bridge in
`scripts/evomap_sdk_build.mjs`.

### 4. Configure environment variables

```bash
cp .env.example .env
```

Then edit `.env` with the model API keys you need. The current pipeline may
use providers such as DeepSeek or OpenRouter depending on
`configs/models.yaml`.

### 5. Verify the setup

```bash
uv run pytest tests/test_evomap_publisher.py -q
uv run pytest tests/test_tooling_setup.py -q
npm run evomap:list
```

## Common Local Commands

Run the main benchmark pipeline:

```bash
uv run python -m src.run_pipeline --model deepseek
```

Run ORQA Track A:

```bash
uv run python -m src.run_track_a --model stepfun
```

List publishable curated SkillsBench skills:

```bash
npm run evomap:list
```

Build EvoMap assets for a skill file:

```bash
npm run evomap:build -- skills/skillsbench/curated/overfull_hbox.yaml
```

Publish a skill to EvoMap:

```bash
uv run python scripts/publish_to_evomap.py overfull_hbox
```

This requires valid EvoMap node credentials. If `.evomap_secrets.json` does
not exist yet, initialize or rotate the node first before trying a real
publish.

## Docker Reproduction

The root `Dockerfile` is the repo-level reproduction image. It is different
from the benchmark task Dockerfiles under
`data/skillsbench/harbor_tasks/*/environment/`, which are task-specific.

### 1. Build the image

```bash
docker build -t skill-optimization-dev .
```

### 2. Run a smoke verification in the container

```bash
docker run --rm skill-optimization-dev uv run pytest tests/test_evomap_publisher.py -q
docker run --rm skill-optimization-dev python3 scripts/publish_to_evomap.py --list
```

### 3. Open an interactive shell

```bash
docker run --rm -it skill-optimization-dev bash
```

If you need API keys or publish secrets inside the container, mount or pass
them explicitly rather than baking them into the image.

## Docker Compose Reproduction

The repo also includes `compose.yaml` for the same image. This compose setup
is intentionally reproduction-oriented rather than live-edit oriented: it does
not bind-mount the repo into `/app`, so the container uses the exact checked-in
code and dependencies baked into the image.

### 1. Build through Compose

```bash
docker compose build
```

### 2. Run smoke checks

```bash
docker compose run --rm app uv run pytest tests/test_evomap_publisher.py -q
docker compose run --rm app python3 scripts/publish_to_evomap.py --list
```

### 3. Open an interactive shell

```bash
docker compose run --rm app bash
```

If you later want a live-edit development container, add a separate compose
override for bind mounts. Do not overload the default compose file, because
mounting the repo over `/app` would hide the preinstalled `.venv` and
`node_modules` directories from the image.

## EvoMap Credentials

EvoMap publisher state is stored locally in:

```text
.evomap_secrets.json
```

This file is intentionally excluded from git and Docker build context. If you
need to publish from inside Docker, mount it explicitly or perform a fresh
`--hello` / `--rotate` flow inside the container.

See also:

- [evomap_sdk_setup.md](evomap_sdk_setup.md)
- [09_evomap_upload_update.md](09_evomap_upload_update.md)
