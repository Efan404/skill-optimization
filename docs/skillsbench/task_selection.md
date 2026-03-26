# SkillsBench Task Selection

## Source

Tasks sourced from **Terminal-Bench 2.0** (https://github.com/laude-institute/terminal-bench-2),
run via the **Harbor** evaluation framework (https://github.com/laude-institute/harbor).

The Harbor repo is cloned at `/Users/efan404/Codes/research/harbor-skillsbench/`.
The Terminal-Bench-2 repo (task source) is cloned at `/Users/efan404/Codes/research/terminal-bench-2-inspect/`.

Total tasks: **89**.  All use pre-built Docker images (`alexgshaw/*:20251031`), require no
external API keys, and include oracle solutions.

---

## All Self-Contained Tasks (89 total)

### Easy (4 tasks)

| Task | Category | Expert Est. | Description |
|------|----------|-------------|-------------|
| cobol-modernization | software-engineering | 20 min | Re-implement a COBOL program in Python to produce identical output |
| fix-git | software-engineering | 5 min | Find lost changes and merge them into master |
| overfull-hbox | debugging | 60 min | Fix LaTeX overfull hbox warnings by replacing words with synonyms |
| prove-plus-comm | software-engineering | 5 min | Complete a Coq proof of addition commutativity |

### Medium (55 tasks)

| Task | Category | Expert Est. | Description |
|------|----------|-------------|-------------|
| adaptive-rejection-sampler | scientific-computing | 180 min | Implement adaptive-rejection sampling (Gilks et al. 1992) |
| break-filter-js-from-html | security | 20 min | Bypass a JavaScript filter to achieve XSS |
| build-cython-ext | debugging | 60 min | Fix Numpy 2.x compatibility and build Cython extensions |
| build-pmars | software-engineering | 90 min | Build pMARS from Debian source packages without X11 |
| build-pov-ray | software-engineering | 60 min | Build POV-Ray 2.2 from source archives |
| caffe-cifar-10 | machine-learning | N/A | Install BVLC Caffe, train CNN on CIFAR-10 for 500 iterations |
| chess-best-move | games | 45 min | Identify best chess move from a board image |
| code-from-image | software-engineering | 30 min | Implement pseudocode from an image, produce output |
| compile-compcert | system-administration | 60 min | Build CompCert C verified compiler v3.13.1 from source |
| constraints-scheduling | personal-assistant | 15 min | Find a 1-hour meeting slot satisfying availability constraints |
| count-dataset-tokens | model-training | 30 min | Count tokens in a HuggingFace dataset using specific tokenizer |
| crack-7z-hash | security | 5 min | Crack 7z archive password and extract secret |
| custom-memory-heap-crash | debugging | 30 min | Fix C++ crash that occurs in RELEASE but not DEBUG mode |
| db-wal-recovery | file-operations | 45 min | Recover data from SQLite DB with corrupted/encrypted WAL file |
| distribution-search | machine-learning | 120 min | Find target probability distribution for LLM confidence metrics |
| dna-insert | scientific-computing | 30 min | Design PCR primers for site-directed mutagenesis |
| extract-elf | file-operations | 30 min | Write JS to extract memory values from compiled C binary |
| filter-js-from-html | security | 45 min | Create Python XSS filter that removes JS while preserving HTML |
| financial-document-processor | data-processing | 30 min | Classify documents as invoice/other using OCR |
| gcode-to-text | file-operations | 60 min | Decode 3D printer G-code to determine printed text |
| git-leak-recovery | software-engineering | 30 min | Recover secret from rewritten git history, then sanitize |
| git-multibranch | system-administration | 180 min | Set up Git server with SSH + Nginx multi-branch deployment |
| headless-terminal | software-engineering | 120 min | Implement headless terminal interface in Python |
| hf-model-inference | data-science | 20 min | Set up local Flask API for HuggingFace sentiment analysis |
| kv-store-grpc | software-engineering | 15 min | Build gRPC key-value store server in Python |
| large-scale-text-editing | file-operations | 40 min | Transform 1M-row CSV with keystroke-efficient Vim macros |
| largest-eigenval | mathematics | 60 min | Optimize dominant eigenvalue computation to beat numpy |
| log-summary-date-ranges | data-processing | 75 min | Analyze log files and count severity levels across date ranges |
| mailman | system-administration | 60 min | Set up email server with mailing list |
| merge-diff-arc-agi-task | debugging | 20 min | Fix merge conflicts in ARC-AGI task |
| modernize-scientific-stack | scientific-computing | 120 min | Modernize legacy scientific Python codebase |
| mteb-leaderboard | data-science | 5 min | Query MTEB leaderboard data |
| mteb-retrieve | data-science | 15 min | Retrieve documents using MTEB embedding model |
| multi-source-data-merger | data-processing | 30 min | Merge data from multiple sources with format handling |
| nginx-request-logging | system-administration | 20 min | Configure Nginx with logging, rate limiting, custom errors |
| openssl-selfsigned-cert | security | 20 min | Generate self-signed SSL certificate with OpenSSL |
| polyglot-c-py | software-engineering | 20 min | Write code that runs as both valid C and Python |
| portfolio-optimization | optimization | 120 min | Implement C extension for portfolio risk/return calculation |
| pypi-server | software-engineering | 60 min | Set up local PyPI server |
| pytorch-model-cli | model-training | 30 min | Build CLI for PyTorch model operations |
| pytorch-model-recovery | model-training | 15 min | Recover PyTorch model from corrupted checkpoint |
| qemu-alpine-ssh | system-administration | 30 min | Boot Alpine Linux in QEMU with SSH access |
| qemu-startup | system-administration | 30 min | Boot a QEMU virtual machine |
| query-optimize | data-science | 60 min | Optimize database query performance |
| raman-fitting | scientific-computing | 5 min | Fit Raman spectroscopy data |
| regex-log | data-processing | 45 min | Extract structured data from logs using regex |
| reshard-c4-data | data-science | 30 min | Reshard C4 dataset |
| rstan-to-pystan | data-science | 180 min | Port RStan model to PyStan |
| sanitize-git-repo | security | 30 min | Remove all API keys from a git repository |
| schemelike-metacircular-eval | software-engineering | 300 min | Implement metacircular evaluator for Scheme-like language |
| sqlite-db-truncate | debugging | 60 min | Debug SQLite database truncation issue |
| sqlite-with-gcov | system-administration | 30 min | Build SQLite with gcov coverage instrumentation |
| tune-mjcf | scientific-computing | 30 min | Tune MuJoCo MJCF simulation parameters |
| vulnerable-secret | security | 20 min | Find and exploit vulnerable secret storage |
| winning-avg-corewars | software-engineering | 60 min | Write Core Wars warrior with winning average |

### Hard (30 tasks)

| Task | Category | Expert Est. | Description |
|------|----------|-------------|-------------|
| bn-fit-modify | scientific-computing | 480 min | Recover Bayesian Network DAG from data |
| cancel-async-tasks | software-engineering | 120 min | Implement concurrent async task runner with graceful cancellation |
| circuit-fibsqrt | software-engineering | 960 min | Build logic gate circuit for Fibonacci + square root |
| configure-git-webserver | system-administration | 15 min | Configure git server with post-push web deployment |
| dna-assembly | scientific-computing | 60 min | Design primers for Golden Gate DNA assembly |
| extract-moves-from-video | file-operations | 120 min | Transcribe game moves from a YouTube video |
| feal-differential-cryptanalysis | mathematics | 480 min | Implement chosen-plaintext differential attack on FEAL cipher |
| feal-linear-cryptanalysis | mathematics | 960 min | Implement known-plaintext linear attack on FEAL cipher |
| fix-code-vulnerability | security | 120 min | Identify and fix CWE vulnerability in Bottle web framework |
| fix-ocaml-gc | software-engineering | 1440 min | Debug OCaml GC crash in run-length compressed free space |
| gpt2-codegolf | software-engineering | 2400 min | Write dependency-free GPT-2 inference in C under 5000 bytes |
| install-windows-3.11 | system-administration | 300 min | Run Windows 3.11 in QEMU with VNC |
| llm-inference-batching-scheduler | machine-learning | 45 min | Implement shape-aware LLM inference batching scheduler |
| make-doom-for-mips | software-engineering | 480 min | Cross-compile Doom for MIPS architecture |
| make-mips-interpreter | software-engineering | 480 min | Build MIPS interpreter to run Doom |
| mcmc-sampling-stan | data-science | 180 min | Hierarchical Bayesian MCMC sampling with RStan |
| model-extraction-relu-logits | mathematics | 480 min | Extract neural network model from ReLU logits |
| password-recovery | security | 100 min | Recover password from encrypted data |
| path-tracing | software-engineering | 360 min | Implement path tracing renderer |
| path-tracing-reverse | software-engineering | 120 min | Reverse-engineer path tracing scene from rendered image |
| polyglot-rust-c | software-engineering | 180 min | Write code that runs as both valid Rust and C |
| protein-assembly | scientific-computing | 60 min | Design gBlock for FRET fusion protein with specific constraints |
| regex-chess | software-engineering | 1440 min | Implement chess move validation via regex |
| sam-cell-seg | data-science | 600 min | Cell segmentation using SAM model |
| sparql-university | data-querying | 800 min | Complex SPARQL queries over university knowledge graph |
| torch-pipeline-parallelism | software-engineering | 240 min | Implement LLaMA pipeline parallel training |
| torch-tensor-parallelism | software-engineering | 240 min | Implement LLaMA tensor parallel training |
| train-fasttext | model-training | 30 min | Train FastText model with specific configuration |
| video-processing | video-processing | 400 min | Complex video processing pipeline |
| write-compressor | software-engineering | 1440 min | Write data compressor from scratch |

---

## Difficulty Categorization Rationale

The tasks have author-assigned difficulty labels (easy/medium/hard) in their `task.toml` files.
These correlate well with expert time estimates:

- **Easy** (4 tasks): Expert estimate 5--60 min. Single-concept tasks, straightforward tool usage.
- **Medium** (55 tasks): Expert estimate 5--300 min. Multi-step tasks requiring moderate domain
  knowledge, tool chaining, or configuration.
- **Hard** (30 tasks): Expert estimate 15--2400 min. Complex multi-step tasks requiring significant
  domain expertise, algorithmic reasoning, or system-level debugging.

For our skill-optimization study, we want tasks where **procedural guidance** (a SKILL.md)
plausibly affects success rate. This means:

1. The task is not trivially solvable by an LLM without domain-specific procedure knowledge.
2. The task has identifiable procedural steps that, if documented, reduce failure modes.
3. The task is not so open-ended that a skill document cannot meaningfully constrain the approach.

---

## Selected Tasks

### 1. Simple: `overfull-hbox`

**Category:** debugging | **Difficulty:** easy | **Expert time:** 60 min | **Agent timeout:** 750s

**Task summary:** Fix LaTeX overfull hbox warnings by replacing words in `input.tex` with
synonyms from `synonyms.txt`. Cannot modify `main.tex` or `synonyms.txt`.

**Why selected:**
- Self-contained, no external dependencies beyond LaTeX (pre-installed in Docker image).
- Requires a non-obvious iterative procedure: compile, parse log for overfull lines, identify
  which word on the offending line has a shorter synonym, substitute, recompile, repeat.
- An agent without this procedure will likely try ad-hoc approaches (e.g., random substitution,
  editing main.tex) that fail the constraints.
- A well-written skill would describe: (1) compile + check loop, (2) log parsing for overfull
  hbox line numbers, (3) synonym lookup strategy, (4) substitution with length-aware selection.

**Skill would provide:** The compile-check-replace iterative workflow, log parsing patterns,
and the insight that shorter synonyms fix overfull hboxes.

---

### 2. Medium: `db-wal-recovery`

**Category:** file-operations | **Difficulty:** medium | **Expert time:** 45 min | **Agent timeout:** 900s

**Task summary:** Recover 11 records from a SQLite database whose WAL (Write-Ahead Logging)
file has been XOR-encrypted. The base database only shows 5 records; the remaining 6 are
locked in the corrupted WAL.

**Why selected:**
- Requires domain knowledge of SQLite WAL file format (magic bytes, structure).
- Multi-step forensic procedure: (1) observe that only 5 of 11 records are visible,
  (2) examine WAL file header to detect it is not valid SQLite WAL, (3) identify the
  XOR encryption by comparing expected vs actual magic bytes, (4) determine the XOR key,
  (5) decrypt the WAL file, (6) re-read the database to extract all 11 records as JSON.
- Without procedural guidance, an agent might try SQL queries or generic database repair
  tools, missing the encryption entirely.
- Diverse domain (database forensics) compared to the other selections.

**Skill would provide:** SQLite WAL magic bytes (`0x377f0682`/`0x377f0683`), XOR detection
heuristic (compare first bytes against known magic), decryption procedure, and the
final JSON extraction workflow.

---

### 3. Hard: `feal-differential-cryptanalysis`

**Category:** mathematics | **Difficulty:** hard | **Expert time:** 480 min | **Agent timeout:** 1800s

**Task summary:** Implement a chosen-plaintext differential cryptanalysis attack on a
FEAL-like cipher to recover the value of round key `key[5]`. The attack must run
in under 30 seconds.

**Why selected:**
- Requires significant cryptography domain knowledge (differential cryptanalysis technique).
- The procedural steps are well-defined in the academic literature but unlikely to be
  directly known by an LLM without guidance: (1) understand FEAL round function,
  (2) identify good input differentials, (3) collect chosen plaintext pairs,
  (4) exploit differential propagation through rounds, (5) use statistical counting to
  recover the target subkey.
- Expert estimate of 480 minutes reflects genuine difficulty; even domain experts need
  substantial time.
- The 16-bit seed per round key means brute force of the full keyspace is infeasible,
  but differential analysis on chosen plaintexts is tractable.
- This is the kind of task where a skill document can provide the specific differential
  characteristics and attack procedure, dramatically improving success probability.

**Skill would provide:** FEAL round function analysis, recommended input differentials,
the counting method for subkey recovery, and the specific steps to target `key[5]`.

---

## Summary Table

| Tier | Task | Category | Difficulty | Expert Est. | Key Skill Benefit |
|------|------|----------|------------|-------------|-------------------|
| Simple | overfull-hbox | debugging | easy | 60 min | Iterative compile-check-replace workflow |
| Medium | db-wal-recovery | file-operations | medium | 45 min | WAL forensics + XOR detection procedure |
| Hard | feal-differential-cryptanalysis | mathematics | hard | 480 min | Differential cryptanalysis attack procedure |
