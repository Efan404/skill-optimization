# Skill Optimization Demo

A lightweight pipeline that tests whether structured skills can improve LLM reasoning on operations research problems, with proper dev/test split and scaffold control.

## Quick Start

```bash
# Clone and setup
git clone <repo-url>
cd skill-optimization
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install "httpx[socks]"  # if using SOCKS proxy

# Configure API keys
cp .env.example .env
# Edit .env with your DeepSeek and/or OpenRouter API keys

# Run the full pipeline
python -m src.run_pipeline --model deepseek
```

## What This Does

Tests 5 prompting conditions on ORQA subset OR multiple-choice questions:

| Condition | Description |
|-----------|-------------|
| **baseline** | Plain CoT prompt, no skill |
| **generic_scaffold** | Length-matched generic problem-solving structure (controls for prompt length confound) |
| **v0_self_generated** | LLM generates its own skill from seed examples |
| **v1_curated** | Human-designed domain-specific skill |
| **v2_optimized** | AI refines v1 based on dev-set error analysis |

### Methodology

- **Dev/test split**: seed (5), dev (25), test (20) — optimizer never sees test data
- **Scaffold control**: generic scaffold matches v1 on step count, field density, and token length (+/-15%)
- **Two-layer classification**: automated outcome labels (Layer 1) + LLM-assisted root causes (Layer 2, dev only)
- **Error handling**: API failures per-question don't abort entire conditions; missing results count as failures in accuracy

### Pipeline Phases

```
Phase 0: Validate split integrity + scaffold token length
Phase 1: Run baseline, scaffold, v0, v1 on dev set
Phase 2: Error analysis — root cause classification (dev only)
Phase 3: Optimize v1 → v2 using dev evidence (never sees test)
Phase 4: Run ALL 5 conditions on held-out test set
Phase 5: Generate report + marketplace cards
```

## Project Structure

```
skill-optimization/
├── configs/           # Model and experiment configuration
├── data/orqa/         # 50 real ORQA questions with seed/dev/test split
├── docs/              # Problem framing, experiment design, results, marketplace mapping
├── results/           # Evaluations, logs, error analysis, marketplace cards
├── skills/            # Curated skills, generic scaffold, generated/optimized skills
├── src/               # Pipeline modules (10 files)
└── tests/             # Unit tests (111 tests)
```

## Results

See `docs/03_results_and_analysis.md` for the full report with:
- Dev and test accuracy tables (clearly separated)
- Paired win/loss analysis
- Dev-to-test gap (descriptive signal)
- Root cause distribution
- Per-question results
- Skill optimization changelog
- Case studies

## EvoMap Upload Status

The EvoMap publishing pipeline is now wired up end-to-end:

- real `POST /a2a/publish` succeeded for a SkillsBench bundle
- the hub returned `quarantine` rather than a schema error
- asset construction now goes through the official Node SDK
  `@evomap/gep-sdk`
- Python still handles node registration, local auth state, and the final
  publish request

Shareable asset links from the successful publish:

- Gene:
  `https://evomap.ai/asset/sha256%3A2149e05f60e118bad0f22881d9d2196e70212fe6831d0c125945fb1c1908cc12`
- Capsule:
  `https://evomap.ai/asset/sha256%3Ac120a9745b6739f3bd4d1caf35010ad1fe68c383d177dfa772f6176c64b6dd94`

Important caveat: the current decision is `quarantine`, not `promoted`, so
these links are useful for inspection and demo sharing, but they are not yet
evidence of full marketplace promotion.

For the current integration summary and account-binding steps, see
`docs/09_evomap_upload_update.md` and `docs/evomap_sdk_setup.md`.

## Existing EvoMap Reuse Options

The current stack is no longer pure hand-written HTTP. We verified these
existing reuse paths:

- SDK: `@evomap/gep-sdk`
- MCP server: `@evomap/gep-mcp-server`
- official Evolver workflow references in EvoMap docs
- public skill discovery via `npx skills find evomap`

At the time of writing, this repo does not include a local pre-installed
EvoMap-specific Codex skill; the public skills ecosystem does include entries
such as `evomap/evolver@capability-evolver`.

## Scope of Claims

**What this demo demonstrates:**
- Whether structured procedural prompting improves LLM reasoning on OR problems
- Whether human-AI skill refinement generalizes from dev to held-out test
- Whether improvement comes from domain content vs generic scaffolding

**What this demo cannot claim:**
- Generalization to agentic task execution (single-turn QA only)
- Statistical significance (directional evidence from ~20 test questions)
- Production-ready marketplace assets (demo metadata only)

## Configuration

Edit `configs/models.yaml` to change models. Supported:
- `deepseek` — DeepSeek Chat via `api.deepseek.com`
- `openrouter_free` — Free models via OpenRouter (e.g., `openai/gpt-oss-120b:free`)

## Related Work

- [SkillsBench](https://skillsbench.com) — Benchmark for agent skill effectiveness
- [ORQA](https://ojs.aaai.org/index.php/AAAI/article/view/1234) — OR reasoning benchmark (AAAI 2025)
- [EvoMap](https://evomap.ai) — AI agent marketplace
