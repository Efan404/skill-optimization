# SkillsBench Pilot: 3 Tasks × 4 Conditions — DeepSeek-V3 初步分析

**Date:** 2026-03-27
**Solver:** OpenCode + deepseek-chat (DeepSeek-V3)
**Trials:** n=1 per condition
**Status:** 12/12 runs 均产出结果（11 条正常结束，1 条 agent timeout）

---

## 1. 全景结果

| Task | baseline | generic_scaffold | curated | self_generated |
|------|:--------:|:----------------:|:-------:|:--------------:|
| **overfull-hbox** (easy) | 0 (2/4) | 0 (3/4) | 0 (3/4) | **1 (4/4)** |
| **db-wal-recovery** (medium) | 0 (5/7) | 0 (5/7) | 0 (5/7) | 0 (5/7) |
| **feal-cryptanalysis** (hard) | 0 (0/1) | **1 (1/1)** | 0 (0/1) | **1 (1/1)** |

**成功的条件（3/12）：**
- overfull-hbox: **self_generated_one_shot** (reward=1)
- feal-cryptanalysis: **generic_scaffold** (reward=1)
- feal-cryptanalysis: **self_generated_one_shot** (reward=1)

**总成本：** ~$0.60 (全部 12 条件)

---

## 2. 按任务分析

### 2.1 overfull-hbox (easy, LaTeX debugging)

| Condition | Reward | Tests | 失败 Test | 时间 | 成本 |
|-----------|:------:|:-----:|----------|:----:|:----:|
| baseline | 0 | 2/4 | hbox 残留 + 非法替换 | 267s | $0.039 |
| generic_scaffold | 0 | 3/4 | hbox 残留 | 296s | $0.047 |
| curated | 0 | 3/4 | 非法替换 | 156s | $0.017 |
| **self_generated** | **1** | **4/4** | 无 | 485s | $0.071 |

```text
                    test_no_overfull_hboxes    test_input_file_matches
baseline            ✗ (3 warnings残留)         ✗ ("a"→"an" 非法)
generic_scaffold    ✗ (1 warning残留)          ✓
curated             ✓                          ✗ (非法改写)
self_generated      ✓                          ✓
```

**四个条件失败在不同 test 上** — skill 确实改变了 agent 行为。

**为什么 self_generated 成功？** 简洁的迭代循环（"repeat until warnings gone"）+ 严格约束 + 72 步暴力搜索。curated skill 的 "expand your search" 指导反而导致 agent 越界。

### 2.2 db-wal-recovery (medium, WAL forensics)

| Condition | Reward | Tests | 时间 | 成本 |
|-----------|:------:|:-----:|:----:|:----:|
| baseline | 0 | 5/7 | 561s | $0.050 |
| generic_scaffold | 0 | 5/7 | 381s | $0.037 |
| curated | 0 | 5/7 | 492s | $0.055 |
| self_generated | 0 | 5/7 | 1191s | $0.098 |

**4 条件的 verifier 结果一致**（均 5/7 passed），失败在 `test_recovered_data_completeness` 和 `test_wal_was_decrypted`。但 **agent 的失败路径各不相同**：

| Condition | 失败路径 | 证据 |
|-----------|---------|------|
| baseline | 执行 `PRAGMA journal_mode=DELETE`，导致 SQLite 永久删除 WAL 文件 | agent log step 17 |
| generic_scaffold | checkpoint 后发现 WAL 消失，未尝试解密，转为基于模式猜测输出 5 条记录 | agent log steps 35, 46, 206, 229 |
| curated | 先 checkpoint，再按 pattern 直接写 11 条记录（猜测的数据不正确） | agent log steps 85, 89, 225 |
| self_generated | 长时间探索后未能解密，最终只输出基础 5 条记录 | 最长执行时间 (1191s) |

**共同结局但不同路径：** baseline 通过破坏性操作毁掉了 WAL；generic_scaffold 和 curated 在 checkpoint 后 WAL 消失，选择了猜测输出；self_generated 投入最多时间但仍未找到解密方法。没有任何 skill 成功引导 agent 完成 WAL 解密。

**含义：** DeepSeek-V3 对 WAL recovery 的领域知识不足。即使 curated skill 提供了 magic bytes 和 XOR 检测指导，模型也没能正确执行解密流程。这个任务可能需要更强的模型或更详细的逐行指导。

### 2.3 feal-differential-cryptanalysis (hard, cryptography)

| Condition | Reward | Tests | 时间 | 成本 |
|-----------|:------:|:-----:|:----:|:----:|
| baseline | 0 | 0/1 | 1124s | $0.045 |
| **generic_scaffold** | **1** | **1/1** | 1556s | $0.058 |
| curated | 0 (**AgentTimeout**) | 0/1 | 1800s | $0.055 |
| **self_generated** | **1** | **1/1** | 1615s | $0.053 |

**generic_scaffold 和 self_generated 都在 hard 任务上成功了** — baseline 和 curated 失败。

注意 curated 的失败是 **AgentTimeoutError**（1800s），不是正常的 verifier failure。在超时前 agent 进行了多轮失败的攻击实现迭代。timeout 与较长、较复杂的 skill 内容相关，但因果机制未确定 — 可能是 skill 导致了过度规划，也可能是 agent 碰巧在更多迭代中消耗了时间。

---

## 3. 跨任务核心洞察

### 3.1 结果矩阵模式

```text
                baseline    scaffold    curated     self_gen
overfull-hbox      0          0           0          ★ 1
db-wal-recovery    0          0           0            0
feal               0        ★ 1           0          ★ 1
                  ----       ----        ----        ----
wins              0/3        1/3         0/3         2/3
```

**self_generated 是整体最强条件（2/3 wins）。** baseline 和 curated 均为 0/3 wins。注意 curated 在 feal 上的 0 是 AgentTimeout 而非正常 verifier failure，应与其他 reward=0 区别对待。

### 3.2 Curated Skill 的困境

Curated skill 在所有 3 个任务上都是 reward=0：
- overfull-hbox: 解决了核心问题但引入约束违反（正常 verifier failure）
- db-wal-recovery: 领域知识没被有效执行（正常 verifier failure）
- feal: **AgentTimeoutError** — 在超时前进行了多轮失败迭代，与较复杂的 skill 内容相关但因果机制未确定

**假说（非结论）：** 对于 DeepSeek-V3 这个能力级别的模型，curated skill 中的领域知识可能构成一种"认知负担"。模型可能不够强到正确执行复杂的领域过程，同时被这些指导偏离了更简单的策略。需要更多数据（多次重复、多模型对比）来验证这一假说。

### 3.3 简洁过程 > 详细知识（在弱模型上）

三个成功案例的共同点：
- **self_generated (overfull-hbox):** 简洁的 6 步循环，无深度领域知识
- **generic_scaffold (feal):** 完全通用的过程框架，零领域知识
- **self_generated (feal):** 简洁的任务描述，无详细密码学推导

失败模式的观察（非因果结论）：
- **curated** 在三个任务上以不同方式失败：越界 (overfull-hbox)、无效执行 (db-wal)、超时 (feal)。与较长较复杂的 skill 内容相关，但不能确定是 skill 内容本身导致了失败
- **baseline** 在无指导下缺乏迭代纪律 (overfull-hbox) 且犯了破坏性错误 (db-wal)

**初步观察：** 在 DeepSeek-V3 上，简洁的结构化指令与更好的任务完成率相关。但 n=1 且模型单一，这一相关性是否构成因果关系、是否在其他模型上成立，需要进一步验证。

### 3.4 任务难度与 Skill 效果的非线性关系

| 难度 | 任务 | Baseline 能力 | Skill 效果 |
|------|------|-------------|-----------|
| Easy | overfull-hbox | 接近成功 (2/4) | self_gen 帮助完成最后一步 |
| Medium | db-wal-recovery | 结构性失败 | 无 skill 有效（模型能力瓶颈） |
| Hard | feal | 完全失败 (0/1) | scaffold + self_gen 成功 |

medium 任务反而是最难通过 skill 改善的 — 因为它需要特定的领域操作序列（WAL 解密），不是通用过程能替代的，而模型又不够强到执行 curated 的复杂指导。

---

## 4. 对研究假设的初步影响

### H1: One-shot self-generated < curated?

**不支持（在 DeepSeek-V3 上）。** self_generated 在 overfull-hbox 上优于 curated (1 vs 0)。在其他任务上两者均为 0。

### H2: Optimized > one-shot?

**未测试** — self_generated_optimized 和 curated_optimized 尚未生成。

### H3/H4: Protocol strength 假说

**初步信号方向出乎预期。** 原始假设预期 curated > self_generated，但实际数据显示相反方向。可能的解释：

1. **模型依赖性：** DeepSeek-V3 不是 SkillsBench 原始论文使用的模型。在更强的模型上（Claude Sonnet），curated skill 可能确实更有效
2. **Skill 质量：** 我们的 curated skill 可能写得不好（约束表达不够明确）
3. **真实信号：** 对于中等能力模型，简洁过程确实优于详细知识

这需要更多数据（多次重复、多模型对比）来区分。

---

## 5. 局限性

1. **n=1 per condition** — 所有结论可能不稳定
2. **单一模型** — DeepSeek-V3 的行为不代表所有模型
3. **二元 reward** — 3/4 和 2/4 都是 reward=0，丢失了梯度信息
4. **Gemini 受阻** — Docker 内地理限制阻止了 cross-model 对比
5. **feal curated 超时** — 不确定是模型能力不足还是 skill 导致的过度规划

---

## 6. 建议下一步

### 优先级 P0
- [x] 完成全部 12 条件
- [ ] 跑 2-3 次重复确认 3 个成功条件的稳定性

### 优先级 P1
- [ ] 用更强模型（Claude Sonnet 或通过 OpenRouter 的 GPT-4）做对比
- [ ] 分析 curated skill 的具体问题，为 optimization 阶段提供改进目标
- [ ] 实现 self_generated_optimized 和 curated_optimized

### 优先级 P2
- [ ] 解决 Gemini 的 Docker 地理限制问题
- [ ] 扩展到更多 SkillsBench 任务（Layer B）

---

## Artifact References

### overfull-hbox
- Baseline: `results/skillsbench/runs/smoke-deepseek-baseline/`
- Generic scaffold: `results/skillsbench/runs/overfull-generic_scaffold-deepseek/`
- Curated: `results/skillsbench/runs/overfull-curated-deepseek/`
- Self-generated: `results/skillsbench/runs/overfull-self_generated-deepseek/`

### db-wal-recovery
- Baseline: `results/skillsbench/runs/dbwal-baseline-deepseek/`
- Generic scaffold: `results/skillsbench/runs/dbwal-generic_scaffold-deepseek/`
- Curated: `results/skillsbench/runs/dbwal-curated-deepseek/`
- Self-generated: `results/skillsbench/runs/dbwal-self_generated_one_shot-deepseek/`

### feal-differential-cryptanalysis
- Baseline: `results/skillsbench/runs/feal-baseline-deepseek/`
- Generic scaffold: `results/skillsbench/runs/feal-generic_scaffold-deepseek/`
- Curated: `results/skillsbench/runs/feal-curated-deepseek/`
- Self-generated: `results/skillsbench/runs/feal-self_generated-deepseek/`
