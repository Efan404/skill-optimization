# Marketplace Mapping: From Benchmark Skills to Reusable Assets

## Important Framing Note

The marketplace mapping in this demo is a **conceptual projection** — it demonstrates how the skill schema and evidence format could integrate with marketplace platforms like EvoMap. It is NOT validated marketplace evidence.

**What this demo proves about marketplace readiness:**
- That skills can be structured in a machine-readable schema
- That skills can carry versioned evidence (dev/test results, changelogs)
- That the schema format is compatible with marketplace asset concepts

**What this demo does NOT prove:**
- Cross-model generalization (only tested on DeepSeek Chat)
- Large-sample statistical validity (demo-level sample size)
- Production reliability (single-turn QA, not agentic execution)

The connection to marketplace assets is **motivation and future direction**, not a validated conclusion.

## Context

EvoMap is an AI agent marketplace where capabilities are organized as composable, tradable assets:

- **Gene**: Atomic unit of capability — a single, focused procedure or strategy
- **Capsule**: Gene + validation evidence — a capability bundled with proof of effectiveness
- **Recipe**: Multi-gene workflow — a composition of capabilities that work together
- **GDI (Gene Discovery Index)**: Ranking system based on quality, usage, social signals, and freshness

## Mapping: Skill Optimization -> EvoMap Assets

### Asset Type Mapping

| EvoMap Concept | Skill Optimization Equivalent | Example |
|----------------|-------------------------------|---------|
| **Gene** | Atomic skill — single task-type procedure | "LP solver procedure" |
| **Capsule** | Skill + evidence bundle — skill with benchmark validation, error analysis, version history | "LP solver v2 + ORQA results" |
| **Recipe** | Multi-skill workflow — task router + domain-specific skills | "Classify OR problem type -> apply matched skill" |

### Why This Mapping Matters

Traditional prompt engineering produces **disposable artifacts** — prompts that work for one task but carry no evidence, no versioning, and no reuse potential.

The skill optimization approach produces **structured artifacts** because each skill carries:

1. **Structured format** — machine-readable schema, not free-form text
2. **Benchmark evidence** — tested on known tasks with dev/test separation
3. **Error analysis** — documented failure modes and fixes
4. **Version history** — traceable evolution from v0 to v2 with changelogs
5. **Reproducibility metadata** — model, temperature, exact prompts used
6. **Scaffold control** — evidence that value comes from domain content, not just structure

This transforms skills from prompt hacks into artifacts that are **potentially publishable, rankable, and improvable** — though Phase 1 evidence is demo-level only.

## Demo Marketplace Card Format

Each validated skill produces a **demo metadata card** (not production marketplace evidence):

```yaml
# NOTE: This is demo metadata showing the schema format.
# Evidence strength is demo-level and requires cross-model,
# larger-sample validation before marketplace publication.

asset_name: "or-linear-programming"
asset_type: "capsule"
domain: "operations_research"
supported_models: ["deepseek-chat"]  # Only validated on this single model
evidence:
  evidence_level: "demo"             # NOT "validated" or "production"
  benchmark: "ORQA subset"          # or "ORQA-derived" if source (3) questions used
  methodology:
    dev_test_split: true
    scaffold_controlled: true
    optimizer_blind_to_test: true
  dev_set:
    n_tasks: 5
    conditions:
      baseline: { accuracy: 0.40 }
      generic_scaffold: { accuracy: 0.40 }
      v0_self_generated: { accuracy: 0.40 }
      v1_curated: { accuracy: 0.60 }
      v2_optimized: { accuracy: 0.80 }
  test_set:
    n_tasks: 5
    conditions:
      baseline: { accuracy: 0.40 }
      generic_scaffold: { accuracy: 0.40 }
      v0_self_generated: { accuracy: 0.40 }
      v1_curated: { accuracy: 0.60 }
      v2_optimized: { accuracy: 0.80 }
  dev_test_gap: "v2 dev: 0.80, test: 0.80 — no overfitting observed"
  key_optimization: "Added constraint verification step; test accuracy +20%"
version_history:
  - version: "v1_curated"
    author: "human"
    note: "Initial design based on OR textbook problem-solving procedure"
  - version: "v2_optimized"
    author: "deepseek-chat"
    note: "Added integer feasibility check after dev-set failures showed constraint_missed"
quality_signals:
  verification_type: "exact_match"
  reproducibility: "temperature 0; full determinism not guaranteed on hosted APIs"
limitations:
  - "Demo-level sample size (~10 test questions) — directional evidence only"
  - "Single model validation — cross-model testing required"
  - "Single-turn QA — agent-level task execution not validated"
  - "No statistical significance testing at this sample size"
```

## SkillsBench Capsule Cards

The following capsule cards represent the three SkillsBench task skills in the EvoMap schema format.
These cards are at **"conceptual" evidence level** — the skills are structured and ready for validation,
but have not yet been run through the SkillsBench evaluation pipeline.

These cards illustrate what the EvoMap listings would look like if these skills were published after
successful SkillsBench validation. Compare with the ORQA `or_model_identification` capsule (actual run, demo-level evidence)
above.

---

### Capsule: overfull-hbox

```yaml
# NOTE: Conceptual capsule — skill is structured but not yet evaluated on SkillsBench.
# Evidence strength is pre-validation. Requires SkillsBench run to upgrade to demo/validated level.

asset_name: "latex-overfull-hbox-fix"
asset_type: "capsule"
domain: "latex_typesetting"
task_type: "latex_debugging"
description: >
  Fixes "Overfull hbox" warnings in LaTeX documents by iteratively substituting
  words with shorter synonyms from a provided dictionary. The skill encodes the
  compile-check-fix loop, WAL file format parsing, and length-aware synonym selection.
when_to_use: >
  When a LaTeX document produces Overfull \hbox warnings and a synonym dictionary
  is provided. Iterative compile-fix-recompile required.
when_not_to_use: >
  Non-hbox LaTeX issues (underfull, syntax errors), page geometry changes,
  or when no synonym dictionary is available.
supported_models: []        # Pending SkillsBench validation
evidence:
  evidence_level: "conceptual"   # NOT "demo" or "validated" — awaiting SkillsBench run
  benchmark: "SkillsBench"       # Target benchmark
  methodology:
    dev_test_split: true
    scaffold_controlled: true    # Generic scaffold control exists
    optimizer_blind_to_test: true
  dev_set:
    n_tasks: "pending"          # Awaiting SkillsBench instance generation
    conditions:
      baseline: { accuracy: null }
      generic_scaffold: { accuracy: null }
      self_generated_one_shot: { accuracy: null }
      curated: { accuracy: null }
      self_generated_optimized: { accuracy: null }
      curated_optimized: { accuracy: null }
  test_set:
    n_tasks: "pending"
    conditions:
      baseline: { accuracy: null }
      generic_scaffold: { accuracy: null }
      self_generated_one_shot: { accuracy: null }
      curated: { accuracy: null }
      self_generated_optimized: { accuracy: null }
      curated_optimized: { accuracy: null }
  dev_test_gap: "pending SkillsBench execution"
  key_optimization: "TBD after first SkillsBench optimization round"
procedure_summary:
  6 steps: (1) understand constraints, (2) initial compile and log parse, (3) identify
  candidate words, (4) perform substitution, (5) recompile and iterate, (6) final validation
common_failures:
  - "Editing wrong file (main.tex instead of input.tex)"
  - "Using synonyms not in dictionary"
  - "Single-pass without iteration"
  - "Not stripping punctuation before dictionary lookup"
version_history:
  - version: "curated_v1"
    author: "human"
    note: "Initial curated design — 6-step iterative procedure with domain-specific log parsing heuristics"
quality_signals:
  verification_type: "exact_match"    # Zero overfull hbox warnings in log
  reproducibility: "deterministic — same input yields same output"
  domain_knowledge_depth: "high"      # Explicit LaTeX typesetting mechanics encoded
  scaffold_validated: true            # Generic scaffold exists for structural control
limitations:
  - "Conceptual stage — no SkillsBench evaluation results yet"
  - "Single task type (latex debugging) — narrow domain"
  - "Agent-level execution not validated at this stage"
  - "No cross-model validation"
```

---

### Capsule: db-wal-recovery

```yaml
# NOTE: Conceptual capsule — skill is structured but not yet evaluated on SkillsBench.
# Evidence strength is pre-validation. Requires SkillsBench run to upgrade to demo/validated level.

asset_name: "sqlite-wal-recovery"
asset_type: "capsule"
domain: "database_forensics"
task_type: "database_forensics"
description: >
  Recovers data from a SQLite database whose WAL (Write-Ahead Logging) file has been
  XOR-encrypted. The skill encodes WAL file format diagnosis, single-byte XOR key derivation,
  decryption, and JSON extraction from recovered records.
when_to_use: >
  When a SQLite database in WAL mode returns fewer records than expected due to an
  unreadable WAL file, and hex inspection shows non-standard WAL magic bytes.
when_not_to_use: >
  Non-SQLite databases, main .db file corruption, schema problems, or multi-byte
  encryption schemes beyond single-byte XOR.
supported_models: []        # Pending SkillsBench validation
evidence:
  evidence_level: "conceptual"   # NOT "demo" or "validated" — awaiting SkillsBench run
  benchmark: "SkillsBench"       # Target benchmark
  methodology:
    dev_test_split: true
    scaffold_controlled: true    # Generic scaffold control exists
    optimizer_blind_to_test: true
  dev_set:
    n_tasks: "pending"          # Awaiting SkillsBench instance generation
    conditions:
      baseline: { accuracy: null }
      generic_scaffold: { accuracy: null }
      self_generated_one_shot: { accuracy: null }
      curated: { accuracy: null }
      self_generated_optimized: { accuracy: null }
      curated_optimized: { accuracy: null }
  test_set:
    n_tasks: "pending"
    conditions:
      baseline: { accuracy: null }
      generic_scaffold: { accuracy: null }
      self_generated_one_shot: { accuracy: null }
      curated: { accuracy: null }
      self_generated_optimized: { accuracy: null }
      curated_optimized: { accuracy: null }
  dev_test_gap: "pending SkillsBench execution"
  key_optimization: "TBD after first SkillsBench optimization round"
procedure_summary:
  6 steps: (1) assess database state, (2) diagnose WAL corruption via hex inspection,
  (3) derive XOR key from magic bytes, (4) decrypt WAL file, (5) extract records via SQLite,
  (6) export as sorted JSON
common_failures:
  - "Querying base DB without fixing WAL (returns partial data)"
  - "Not recognizing XOR encryption pattern in WAL header"
  - "Using wrong XOR key or partial file decryption"
  - "Not backing up before modification"
  - "Using read-only mode after decryption (SQLite won't replay WAL)"
  - "Incorrect JSON format or unsorted output"
version_history:
  - version: "curated_v1"
    author: "human"
    note: "Initial curated design — 6-step procedure covering hex diagnosis, XOR derivation, and JSON export"
quality_signals:
  verification_type: "exact_match"    # Correct record count, sorted JSON, valid WAL magic
  reproducibility: "deterministic — same encrypted WAL yields same decrypted result"
  domain_knowledge_depth: "high"      # SQLite WAL internals, XOR cryptography, hex analysis
  scaffold_validated: true            # Generic scaffold exists for structural control
limitations:
  - "Conceptual stage — no SkillsBench evaluation results yet"
  - "Single task type (SQLite WAL forensics) — narrow domain"
  - "Agent-level execution not validated at this stage"
  - "No cross-model validation"
```

---

### Capsule: feal-differential-cryptanalysis

```yaml
# NOTE: Conceptual capsule — skill is structured but not yet evaluated on SkillsBench.
# Evidence strength is pre-validation. Requires SkillsBench run to upgrade to demo/validated level.

asset_name: "feal-differential-cryptanalysis"
asset_type: "capsule"
domain: "cryptography"
task_type: "cryptanalysis"
description: >
  Performs a chosen-plaintext differential cryptanalysis attack on a FEAL-like block cipher
  to recover the last round subkey (key[5]). The skill encodes Feistel network structure
  analysis, differential characteristic selection, last-round peel, and statistical filtering.
when_to_use: >
  When attacking a FEAL-like Feistel cipher with addition-based round functions,
  a 16-bit seed key schedule, and 4 rounds. Target is key[5] (last round).
when_not_to_use: >
  S-box based ciphers, full-entropy key schedules, ciphers requiring simultaneous
  multi-round key recovery, or when linear/algebraic attacks are more appropriate.
supported_models: []        # Pending SkillsBench validation
evidence:
  evidence_level: "conceptual"   # NOT "demo" or "validated" — awaiting SkillsBench run
  benchmark: "SkillsBench"       # Target benchmark
  methodology:
    dev_test_split: true
    scaffold_controlled: true    # Generic scaffold control exists
    optimizer_blind_to_test: true
  dev_set:
    n_tasks: "pending"          # Awaiting SkillsBench instance generation
    conditions:
      baseline: { accuracy: null }
      generic_scaffold: { accuracy: null }
      self_generated_one_shot: { accuracy: null }
      curated: { accuracy: null }
      self_generated_optimized: { accuracy: null }
      curated_optimized: { accuracy: null }
  test_set:
    n_tasks: "pending"
    conditions:
      baseline: { accuracy: null }
      generic_scaffold: { accuracy: null }
      self_generated_one_shot: { accuracy: null }
      curated: { accuracy: null }
      self_generated_optimized: { accuracy: null }
      curated_optimized: { accuracy: null }
  dev_test_gap: "pending SkillsBench execution"
  key_optimization: "TBD after first SkillsBench optimization round"
procedure_summary:
  6 steps: (1) understand cipher implementation, (2) implement F/G helper functions,
  (3) implement differential filtering attack, (4) handle last-round peel correctly,
  (5) test and validate attack, (6) ensure correct output file format
common_failures:
  - "Wrong byte ordering in F/G function (must copy from cipher source exactly)"
  - "Confusing cipher_left vs cipher_right in merge(right,left) output"
  - "Not accounting for post-round XOR mixing before last-round peel"
  - "Using wrong input differential (must be 0x8080000080800000)"
  - "Too few filtering rounds (need ~10 for 65536 candidates)"
  - "Hardcoding key value instead of using encrypt interface"
  - "Exceeding 30-second time limit"
version_history:
  - version: "curated_v1"
    author: "human"
    note: "Initial curated design — 6-step differential attack with explicit Feistel round peel procedure"
quality_signals:
  verification_type: "exact_match"    # Recovered key[5] matches actual key exactly
  reproducibility: "deterministic given same encrypt oracle and key"
  domain_knowledge_depth: "very high" # Differential cryptanalysis theory, Feistel networks, byte-level debugging
  scaffold_validated: true            # Generic scaffold exists for structural control
limitations:
  - "Conceptual stage — no SkillsBench evaluation results yet"
  - "Single task type (FEAL cryptanalysis) — very narrow domain"
  - "Agent-level execution not validated at this stage"
  - "No cross-model validation"
  - "Academic/capture-the-flag context — limited general-purpose applicability"
```

---

### Capsule Comparison: ORQA (actual) vs SkillsBench (conceptual)

| Property | ORQA or_model_identification | SkillsBench overfull-hbox | SkillsBench db-wal-recovery | SkillsBench feal-dc |
|----------|------------------------------|--------------------------|----------------------------|---------------------|
| **Evidence level** | demo (actual run) | conceptual | conceptual | conceptual |
| **Benchmark** | ORQA subset | SkillsBench (pending) | SkillsBench (pending) | SkillsBench (pending) |
| **Dev set** | 25 questions | pending | pending | pending |
| **Test set** | 20 questions | pending | pending | pending |
| **Baseline test acc** | 80% | null | null | null |
| **Curated test acc** | 85% | null | null | null |
| **Author** | human + AI | human | human | human |
| **Asset name** | or-or-model-identification | latex-overfull-hbox-fix | sqlite-wal-recovery | feal-differential-cryptanalysis |
| **Domain** | operations_research | latex_typesetting | database_forensics | cryptography |

The ORQA capsule has real numbers because it was actually run. The SkillsBench capsules are
shown in the same schema to illustrate the full pipeline from structured skill to
marketplace-ready capsule. Once SkillsBench validation completes, the `null` fields
would be replaced with actual accuracy values, and `evidence_level` would upgrade
from "conceptual" to "demo" (or "validated" if cross-model and larger-sample criteria are met).

---

## GDI Ranking Dimensions

If these skills were published on EvoMap, they would be ranked by:

| GDI Dimension | How Our Skills Would Score | Current Limitation |
|---------------|---------------------------|--------------------|
| **Quality** | Test-set accuracy + dev/test split + scaffold control | Small sample, single model |
| **Usage** | Number of task types supported, model compatibility | Only 2 task types, 1 model |
| **Social** | Version history shows human-AI collaboration | Single iteration only |
| **Freshness** | v2 is a recent optimization with documented changelog | Single optimization round |

## From Demo to Marketplace: The Path Forward

### What This Demo Proves

1. Skills can be **structured** in a machine-readable schema
2. Skills can be **validated** against benchmarks with proper dev/test methodology
3. Skills can be **optimized** through human-AI collaborative iteration
4. Skills can carry **evidence** in a format compatible with marketplace distribution
5. Improvement comes from **domain content**, not just structural scaffolding (if scaffold control confirms this)

### What Phase 2 Would Add to Reach "Validated" Evidence Level

1. **Cross-model validation** — test the same skill on 3+ models to establish `supported_models`
2. **Larger samples** — 50+ test questions per task type for statistical power
3. **SkillsBench integration** — validate that skills help in agentic execution, not just QA
4. **Skill composition** — combine multiple skills into Recipes (multi-step workflows)
5. **Community iteration** — allow others to fork, modify, and re-validate skills
6. **Formal statistical testing** — confidence intervals, paired significance tests

### The Research Contribution

The key insight connecting skill optimization to marketplaces:

> **Skills are not prompts. Skills are structured artifacts with evidence.**
>
> A prompt is a one-time instruction. A skill is a versioned, testable, optimizable artifact that carries its own validation data. This distinction is what makes skills potentially suitable for marketplace distribution — they can be compared, ranked, composed, and improved by multiple contributors over time.
>
> Phase 1 demonstrates this concept at demo scale. Phase 2 would validate it at production scale.
