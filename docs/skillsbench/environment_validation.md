# SkillsBench Environment Validation

**Date:** 2026-03-26
**Host:** macOS Darwin 24.6.0, Apple Silicon (M-series)
**Docker:** OrbStack v28.5.2 (Docker context: orbstack)

---

## 1. Docker Status

- **Client:** Docker v28.5.2 with buildx v0.29.1 and compose v2.40.3
- **Daemon:** OrbStack-managed Docker daemon
- **Issue:** During validation, the OrbStack Docker daemon consistently failed to
  reach Docker Hub (`EOF` / `TLS handshake timeout`), despite the host having
  working HTTPS connectivity to `registry-1.docker.io` via curl. This appears to
  be an OrbStack networking issue (possibly DNS or proxy-related). Restart did not
  resolve it.
- **Mitigation:** Docker Hub API confirms all three images exist and are pullable.
  The network issue is transient and environment-specific, not a blocker for the
  benchmark itself. Images should be pre-pulled before running trials.

---

## 2. Task Inspection

### 2.1 overfull-hbox (Easy)

| Field | Value |
|-------|-------|
| Docker image | `alexgshaw/overfull-hbox:20251031` |
| Architecture | **amd64 only** (131 MB) |
| Base image | `ubuntu:24.04` |
| Agent timeout | 750s |
| Verifier timeout | 360s |
| Resources | 2 CPUs, 4 GB RAM, 10 GB storage |
| SKILL.md | **Not present** |

**Environment contents (inside Docker):**
- `/app/main.tex` -- LaTeX main document (not to be edited)
- `/app/input.tex` -- text input file (agent edits this)
- `/app/synonyms.txt` -- synonym lookup table (not to be edited)
- `texlive-latex-base` is pre-installed

**Instruction:** Replace words in `input.tex` with synonyms from `synonyms.txt` to
eliminate all "overfull hbox" warnings when compiling with pdflatex.

**Oracle approach (from `solution/solve.sh`):**
1. Compile with pdflatex to generate `main.log`
2. Parse log for "Overfull" warnings, extract line numbers
3. Look up words on offending lines in synonyms dict
4. Replace words with shorter synonyms (hardcoded substitution LUT)
5. Repeat until no overfull warnings remain

**Verification (`tests/test_outputs.py`):**
- `main.tex` and `synonyms.txt` must be unmodified
- Document must compile successfully
- No "Overfull \hbox" warnings in the log
- All word substitutions must come from the synonyms file

**Apple Silicon:** Runs via Rosetta 2 emulation (amd64). No architecture-specific
issues expected -- LaTeX is pure computation.

**Status: READY** (once Docker Hub connectivity is resolved)

---

### 2.2 db-wal-recovery (Medium)

| Field | Value |
|-------|-------|
| Docker image | `alexgshaw/db-wal-recovery:20251031` |
| Architecture | **amd64 only** (175 MB) |
| Base image | `ubuntu:24.04` |
| Agent timeout | 900s |
| Verifier timeout | 900s |
| Resources | 1 CPU, 2 GB RAM, 10 GB storage |
| SKILL.md | **Not present** |

**Environment contents (inside Docker):**
- `/app/main.db` -- SQLite database (5 base records visible)
- `/app/main.db-wal` -- XOR-encrypted WAL file (copied from `main.db-wal.encrypted`)
- Python3, sqlite3, xxd pre-installed

**Instruction:** Recover all 11 records from a SQLite database whose WAL file is
corrupted/encrypted. Write results to `/app/recovered.json` as a sorted JSON array.

**Oracle approach (from `solution/solve.sh`):**
1. Query base DB (read-only) to see only 5 records
2. Examine WAL file header bytes with `xxd`
3. Detect XOR encryption by comparing expected SQLite WAL magic bytes
   (`0x377f0682`/`0x377f0683`) against actual bytes
4. Determine XOR key is `0x42`
5. Decrypt WAL file by XORing every byte with `0x42`
6. Replace encrypted WAL with decrypted version
7. Open database normally, extract all 11 records as JSON

**Verification (`tests/test_outputs.py`):**
- `recovered.json` must exist and be valid JSON
- Must contain exactly 11 records with ids 1-11, sorted
- Specific values checked: id=1 value=150, id=2 value=250 (from WAL updates)
- Records 6-11 (fig, grape, honeydew, kiwi, lemon, mango) must be from WAL
- No duplicate IDs

**Apple Silicon:** Runs via Rosetta 2 emulation (amd64). No architecture-specific
issues -- Python and SQLite are straightforward.

**Status: READY** (once Docker Hub connectivity is resolved)

---

### 2.3 feal-differential-cryptanalysis (Hard)

| Field | Value |
|-------|-------|
| Docker image | `alexgshaw/feal-differential-cryptanalysis:20251031` |
| Architecture | **amd64 only** (52 MB) |
| Base image | `python:3.13-slim-bookworm` |
| Agent timeout | 1800s |
| Verifier timeout | 1800s |
| Resources | 1 CPU, 2 GB RAM, 10 GB storage |
| SKILL.md | **Not present** |

**Environment contents (inside Docker):**
- `/app/feal.py` -- Python FEAL cipher implementation with `encrypt()` function
- `setuptools==80.9.0` pre-installed

**Instruction:** Implement a chosen-plaintext differential cryptanalysis attack in
`/app/attack.py` that recovers `key[5]`. Must implement `attack(encrypt_fn)` returning
the uint32 value. Must run in under 30 seconds. Each of 6 round keys is derived from
a 16-bit seed via `(seed * 1234567) & 0xFFFFFFFF`.

**Oracle approach (from `solution/solve.sh`):**
1. Uses input differential `0x8080000080800000` (chosen to propagate through
   the FEAL round function in a predictable way)
2. Iterates over all 65536 candidate seeds for key[5]
3. For each candidate, encrypts random plaintext pair with the differential
4. Decrypts through the last round using the candidate key
5. Checks if the output differential matches expected value `0x02000000`
6. Repeats 10 rounds of filtering to narrow candidates to 1

**Verification (`tests/test_outputs.py`):**
- Builds a C extension (`feal_in_c`) from test files for faster encryption
- Creates random keys via C extension
- Calls `attack.attack(feal_in_c.encrypt)` and asserts the returned key
  matches `feal_in_c.get_keys()[5]`
- Note: The test uses the C implementation (not Python) for encryption,
  so the attack must work with any encrypt function, not just the Python one

**Apple Silicon:** Runs via Rosetta 2 emulation (amd64). The C extension build
(`feal.c`, `feal_module.c`) needs `gcc` which the test script installs. The
emulation overhead is minimal since the attack is computationally light (16-bit
seed space).

**Status: READY** (once Docker Hub connectivity is resolved)

---

## 3. Apple Silicon Compatibility

All three images are **amd64/linux only** (no multi-arch manifests). On Apple
Silicon Macs:

- **OrbStack** transparently runs amd64 containers via Rosetta 2 emulation
- Performance overhead is ~20-40% for CPU-bound tasks
- None of the three tasks are performance-critical (all have generous timeouts)
- No known architecture-specific failures for these workloads

**Recommendation:** No adaptation needed. OrbStack + Rosetta handles this
transparently.

---

## 4. Skill Injection Point Analysis

### How Harbor delivers tasks to agents

The Harbor framework flow is:

1. **Instruction:** `instruction.md` is read from the task directory and passed
   as a string to `agent.run(instruction, environment, context)`
2. **Prompt template:** An optional `@with_prompt_template` decorator wraps the
   instruction through a Jinja2 template before delivery (e.g., prepending system
   context or appending guidelines)
3. **Skills directory:** `task.toml` can declare `skills_dir` in `[environment]`,
   and Harbor copies its contents to `$CLAUDE_CONFIG_DIR/skills/` before the
   agent runs

For Claude Code specifically, the instruction is passed as a CLI argument:
```
claude --verbose --output-format=stream-json --permission-mode=bypassPermissions \
  --print -- '<instruction text>' 2>&1 | tee /logs/agent/claude-code.txt
```

### Skill injection mechanisms (three options)

#### Option A: `skills_dir` in task.toml (Native Harbor mechanism)

Add to `task.toml`:
```toml
[environment]
skills_dir = "/skills"
```

Place skill files (e.g., `SKILL.md`) in a directory that gets copied into the
Docker image at `/skills/`. Harbor's Claude Code agent copies these to
`$CLAUDE_CONFIG_DIR/skills/` during setup.

**Pros:** Native Harbor mechanism, clean separation of concerns.
**Cons:** Requires building a custom Docker image (or volume-mounting the skills
directory). Claude Code discovers these as "skills" in its config -- the exact
mechanism by which Claude Code surfaces skills to the model depends on its version.

#### Option B: `--append-system-prompt` CLI flag

The Claude Code agent supports `append_system_prompt` as a CLI flag:
```
harbor run ... --agent-kwarg append_system_prompt="<skill content>"
```

**Pros:** No Docker image modification needed, injects directly into system prompt.
**Cons:** Content length limits, less structured than a file.

#### Option C: Prepend/append to instruction.md

Modify the instruction text at the adapter level to include the skill content:
```
<task_instruction>
{original instruction.md content}
</task_instruction>

<skill>
{SKILL.md content}
</skill>
```

**Pros:** Simple, works with any agent, full control over formatting.
**Cons:** Requires a custom adapter or instruction-rewriting layer.

### Recommended approach

**Option A (`skills_dir`)** is the cleanest for Claude Code because:
1. It uses Harbor's built-in mechanism
2. Skills are placed in the standard Claude Code skills directory
3. No instruction modification needed
4. Clean A/B testing: baseline runs have no `skills_dir`, treatment runs do

For the curated-skill condition, we would:
1. Create a `skills/` directory in each task's environment
2. Place a `SKILL.md` file there with the curated procedural guidance
3. Set `skills_dir = "/skills"` in the task.toml `[environment]` section
4. Build a variant Docker image (or use a volume mount) that includes the skills dir

### Skill format

Since none of the three tasks include a `SKILL.md` file, we need to author them.
The format should be Markdown (`.md`) matching Claude Code's skills convention:

```markdown
# Task: <task-name>

## Overview
<Brief description of what this task requires>

## Procedure
1. <Step 1>
2. <Step 2>
...

## Key Insights
- <Domain-specific knowledge the agent needs>
- <Common pitfalls to avoid>
```

### Per-task injection summary

| Task | SKILL.md exists? | Injection method | Notes |
|------|-------------------|-----------------|-------|
| overfull-hbox | No | `skills_dir` | Skill describes compile-check-replace loop |
| db-wal-recovery | No | `skills_dir` | Skill describes WAL magic bytes + XOR detection |
| feal-differential-cryptanalysis | No | `skills_dir` | Skill describes differential attack procedure |

---

## 5. task.toml Adaptation Needed

The existing `task.toml` files from Terminal-Bench-2 need **no modification** for
baseline (no-skill) runs. For treatment (with-skill) runs, the only change is
adding `skills_dir` to `[environment]`:

```toml
[environment]
# ... existing fields ...
skills_dir = "/skills"
```

The Harbor framework handles the rest (copying skills to Claude Code's config dir).

---

## 6. Docker Image Pull Results

| Image | Exists on Hub? | Architecture | Size | Pull status |
|-------|---------------|-------------|------|-------------|
| `alexgshaw/overfull-hbox:20251031` | Yes | amd64/linux | 131 MB | Failed (OrbStack network) |
| `alexgshaw/db-wal-recovery:20251031` | Yes | amd64/linux | 175 MB | Failed (OrbStack network) |
| `alexgshaw/feal-differential-cryptanalysis:20251031` | Yes | amd64/linux | 52 MB | Failed (OrbStack network) |

All images confirmed to exist via Docker Hub REST API. Pull failures are due to
OrbStack daemon connectivity issues, not missing images.

---

## 7. Summary and Recommendations

### Overall verdict: READY (pending network fix for image pulls)

All three tasks are well-structured, self-contained, have clear verification
criteria, and the Harbor framework provides a native skill injection mechanism.
No code changes to Harbor or the tasks are needed for baseline runs.

### Action items before running trials

1. **Resolve OrbStack Docker Hub connectivity** -- restart OrbStack or check
   proxy/VPN settings, then pre-pull all three images
2. **Smoke-test each image** -- run `docker run --rm <image> ls /app/` to verify
   expected files are present
3. **Author SKILL.md files** for each task (curated skills based on oracle solutions)
4. **Set up adapter layer** to toggle skills_dir on/off for baseline vs treatment
5. **Run oracle solutions** -- verify scoring works end-to-end
