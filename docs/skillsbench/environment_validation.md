# SkillsBench Environment Validation

## Docker Status

**Docker daemon not running at time of validation.** OrbStack needs to be started before Docker builds/pulls can be tested. All 3 tasks use pre-built Docker images (`alexgshaw/*:20251031`) from Docker Hub.

**Action required:** Start OrbStack, then run:
```bash
docker pull alexgshaw/overfull-hbox:20251031
docker pull alexgshaw/db-wal-recovery:20251031
docker pull alexgshaw/feal-differential-cryptanalysis:20251031
```

## Task Analysis

### 1. overfull-hbox (Simple)

| Field | Value |
|-------|-------|
| Difficulty | Easy |
| Category | Debugging |
| Docker image | `alexgshaw/overfull-hbox:20251031` |
| Agent timeout | 750s |
| Verifier timeout | 360s |
| Resources | 2 CPUs, 4GB RAM, 10GB storage |

**Task:** Fix LaTeX overfull hbox warnings by replacing words in `input.tex` with synonyms from `synonyms.txt`. Cannot edit `main.tex` or `synonyms.txt`.

**Skill injection point:** The instruction is provided via `instruction.md`. A skill would be injected as additional context alongside the instruction — likely as a system prompt or appended to the instruction.

**SKILL.md:** Does NOT exist. Need to write curated skill ourselves.

**Curated skill would cover:**
- Iterative workflow: compile → parse warnings → find synonym replacement → substitute → recompile
- How to identify which word causes the overfull hbox
- How to pick the shortest synonym that fixes the issue
- Common pitfalls: replacing in wrong order, breaking other constraints

**Skill relevance:** High — the task requires a non-obvious iterative workflow that an unskilled agent might not discover.

---

### 2. db-wal-recovery (Medium)

| Field | Value |
|-------|-------|
| Difficulty | Medium |
| Category | File operations |
| Docker image | `alexgshaw/db-wal-recovery:20251031` |
| Agent timeout | 900s |
| Verifier timeout | 900s |
| Resources | 1 CPU, 2GB RAM, 10GB storage |

**Task:** Recover 11 records from a SQLite database whose WAL file is corrupted/encrypted. Base database shows only 5 records. Must produce `recovered.json` with all 11.

**Skill injection point:** Same as above — alongside `instruction.md`.

**SKILL.md:** Does NOT exist. Need to write curated skill ourselves.

**Curated skill would cover:**
- WAL file structure: magic bytes, page size, checksum format
- How to detect XOR encryption on WAL
- How to identify the XOR key (compare known structure bytes)
- Decryption procedure: XOR each page with the key
- How to extract records from decrypted WAL pages
- Verification: count should be 11 records

**Skill relevance:** High — requires domain-specific forensics knowledge that generic problem-solving won't provide.

---

### 3. feal-differential-cryptanalysis (Hard)

| Field | Value |
|-------|-------|
| Difficulty | Hard |
| Category | Mathematics |
| Docker image | `alexgshaw/feal-differential-cryptanalysis:20251031` |
| Agent timeout | 1800s |
| Verifier timeout | 1800s |
| Resources | 1 CPU, 2GB RAM, 10GB storage |

**Task:** Implement a chosen-plaintext differential cryptanalysis attack on a FEAL-like cipher to recover `key[5]`. Attack must run in <30 seconds.

**Skill injection point:** Same as above.

**SKILL.md:** Does NOT exist. Need to write curated skill ourselves.

**Curated skill would cover:**
- Differential cryptanalysis fundamentals: input differentials, output differentials
- FEAL-specific differential characteristics
- How to choose plaintext pairs with specific differentials
- Subkey recovery technique: count matching candidates across many pairs
- Implementation structure: encrypt pairs → filter by output differential → count subkey votes → pick majority

**Skill relevance:** Very high — this is expert-level cryptographic knowledge that an agent without the skill would need to derive from scratch.

---

## Key Finding: No SKILL.md Files

**None of the 3 selected tasks have existing SKILL.md files.** This is different from the SkillsBench paper's claim of curated skills. Possible explanations:
1. Terminal-Bench-2 is a newer version that may not include SKILL.md files
2. The SKILL.md files may be in a different location or repository
3. The original SkillsBench paper's skill files may not be in this dataset

**Impact on experiment design:**
- The `curated` condition needs skills written from scratch (using solution/ as reference)
- This is actually more realistic — it tests whether a researcher can write an effective skill
- The `self_generated_one_shot` condition is unaffected (AI generates from instruction only)

## Skill Injection Architecture

For all 3 tasks, the skill injection follows the same pattern:

```
Agent receives:
1. instruction.md content (task description)
2. [OPTIONAL] skill content (injected as additional context)
3. Access to the Docker environment (terminal, files)

Agent must:
1. Read/understand the task
2. Use the skill (if provided) to guide its approach
3. Execute commands in the Docker container
4. Produce the required output
```

The skill should be injected as a **system prompt addition** or **prepended to the instruction**, formatted as:

```
You have been given a structured skill to guide your approach. Follow the procedure carefully.

**SKILL:**
{skill_content}

**TASK INSTRUCTION:**
{instruction_md_content}
```

This matches the ORQA pipeline's skill injection pattern.

## Apple Silicon Compatibility

All 3 images are tagged `20251031` without architecture specification. Potential issues on M-series:
- LaTeX (overfull-hbox): should work fine under ARM/Rosetta
- SQLite tools (db-wal-recovery): should work fine
- Python/crypto (feal): should work fine

No ARM-specific concerns expected for these 3 tasks.

## Next Steps

1. **Start OrbStack** — required for Docker validation
2. **Pull the 3 Docker images** — verify they exist and work
3. **Run oracle solutions** — verify scoring works
4. **Write curated skills** for all 3 tasks (from solution/ reference)
5. **Implement SkillsBench adapter** — bridge between our pipeline and Harbor
