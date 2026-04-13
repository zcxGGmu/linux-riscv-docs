# OpenClaw 多 Agent 流程操作手册（Runbook）

> 目标：让 OpenClaw 自动编排多个 Agent，完成
> `差距发现 -> issue管理 -> 方案设计 -> 实现验证 -> patch发信`。

适用仓库：`/home/zq/work-space/repo/ai-projs/linux-riscv-docs`

---

## 1. 你会得到什么

跑通后，你每天只做 3 次人工决策：

1. **Gate-1 差距项确认**（保留/删除、P0/P1/P2）
2. **Gate-2 方案审批**（架构方向、可上游性）
3. **Gate-3 发信审批**（最终 patch 邮件签发）

其余步骤由 OpenClaw + Claude Code + Codex 自动完成。

---

## 2. 一次性准备（只做一次）

## 2.1 本地仓库准备

```bash
# Linux 主线仓库（建议单独目录）
git clone git@github.com:torvalds/linux.git /data/src/linux

# 文档与项目编排仓库
git clone git@github.com:zcxGGmu/linux-riscv-docs.git /data/src/linux-riscv-docs
cd /data/src/linux-riscv-docs
```

把 `kernel/openclaw/` 目录同步到这个仓库（你当前已经有文档）。

## 2.2 OpenClaw 运行检查

```bash
openclaw status
openclaw gateway status
```

确保 Gateway 在线。

## 2.3 Agent 可用性检查

你的 ACP Agent 至少需要：
- `claude-code`（方案设计）
- `codex`（实现与验证）

如果你用的是 OpenClaw Control UI，直接在 UI 里确认 ACP Agent 名称与可用状态。

## 2.4 GitHub/邮件工具准备

- GitHub 需有 `zcxGGmu/linux-riscv-docs` 的 issue 写权限
- 邮件发送链路建议准备：
  - `git send-email` 或 `b4 send`
  - 能发往 `kvm@vger.kernel.org`、`linux-riscv@lists.infradead.org`

---

## 3. 推荐目录结构（必须）

在 `linux-riscv-docs/kernel/openclaw/` 下确保有：

```text
config/
  workflow.yaml
  prompts.yaml
  labels.yaml
state/
  gap_registry.yaml
  issue_map.yaml
  run_history/
scripts/
  01_scan_gaps.sh
  02_sync_issues.sh
  03_plan_with_claude.sh
  04_impl_with_codex.sh
  05_gen_patch_and_send.sh
templates/
  issue_template.md
  plan_template.md
  test_matrix_template.md
  cover_letter_template.md
```

---

## 4. 配置 workflow.yaml（关键）

`kernel/openclaw/config/workflow.yaml` 示例：

```yaml
project:
  linux_repo: /data/src/linux
  docs_repo: /data/src/linux-riscv-docs
  kvm_lore_url: https://yhbt.net/lore/kvm/

agents:
  scout:
    runtime: acp
    agentId: claude-code
    model: hanbbq/gpt-5.3-codex
  planner:
    runtime: acp
    agentId: claude-code
    model: hanbbq/gpt-5.3-codex
  implementer:
    runtime: acp
    agentId: codex
    model: hanbbq/gpt-5.3-codex
  verifier:
    runtime: acp
    agentId: codex
    model: hanbbq/gpt-5.3-codex

policy:
  max_parallel_issues: 3
  max_fix_iterations: 8
  require_human_gate:
    - gate_gap_triage
    - gate_plan_review
    - gate_patch_send

issue:
  repo: zcxGGmu/linux-riscv-docs
  assignee: zcxGGmu
  labels_default: ["riscv", "kvm-gap"]

mailing:
  target_lists:
    - kvm@vger.kernel.org
    - linux-riscv@lists.infradead.org
  dry_run: true
  use_b4: true
```

**你只需要改 4 件事**：
1. `linux_repo`
2. `docs_repo`
3. `issue.repo` / `assignee`
4. `agents.*.agentId`（如需替换执行器）

---

## 5. 日常运行流程（按这个顺序）

## Step-1 差距扫描

```bash
cd /data/src/linux-riscv-docs
bash kernel/openclaw/scripts/01_scan_gaps.sh
```

产物：`state/gap_registry.yaml`

### Gate-1（人工）

你需要在 `gap_registry.yaml` 里确认：
- 删除误报项
- 标注优先级 `P0/P1/P2`
- 标注证据置信度 `high/medium/low`

---

## Step-2 issue 同步

```bash
bash kernel/openclaw/scripts/02_sync_issues.sh
```

动作：
- 对每个 gap 自动建/更新 issue
- 写入 `state/issue_map.yaml`

验收：
- 每个 `gap_id` 都有 `issue_number`
- issue 模板字段完整

---

## Step-3 方案设计（Claude Code）

针对单个 issue：

```bash
bash kernel/openclaw/scripts/03_plan_with_claude.sh --issue 42
```

批量模式（建议先小规模）：

```bash
bash kernel/openclaw/scripts/03_plan_with_claude.sh --batch --limit 2
```

产物：
- `plans/issue-42-plan.md`
- `plans/issue-42-test-matrix.md`

### Gate-2（人工）

你审批：
- 方案是否符合 upstream 风格
- 测试矩阵是否覆盖关键路径
- 是否允许进入编码阶段

---

## Step-4 实现+验证循环（Codex）

```bash
bash kernel/openclaw/scripts/04_impl_with_codex.sh --issue 42
```

预期行为：
- Codex 根据已批准方案改代码
- 自动执行构建与测试
- 失败自动修复重试
- 达到上限后自动回退到“方案修订”

建议门禁：
- 编译必须通过
- kselftest/kvm-unit-tests 必须通过
- 关键性能项不退化（超阈值即 fail）

---

## Step-5 patch 生成与邮件发送

先 dry-run：

```bash
bash kernel/openclaw/scripts/05_gen_patch_and_send.sh --issue 42 --dry-run
```

产物：
- `patches/*.patch`
- `cover-letter.md`
- `send-plan.md`（To/Cc建议）

### Gate-3（人工）

你最终确认：
- commit message
- To/Cc
- cover letter 的风险与测试结果

确认后正式发送：

```bash
bash kernel/openclaw/scripts/05_gen_patch_and_send.sh --issue 42 --send
```

---

## 6. 在 OpenClaw Control UI 里怎么操作（最实用）

你可以按下面 6 条指令驱动（复制即用）：

1. **初始化本轮**
   - “读取 `kernel/openclaw/config/workflow.yaml`，检查路径、agentId、issue repo 配置并给出差异。”
2. **执行 Step-1**
   - “执行 `01_scan_gaps.sh`，输出 gap 摘要表（功能/性能/证据/优先级建议）。”
3. **等待 Gate-1 后执行 Step-2**
   - “按 `gap_registry.yaml` 同步 issue，输出新建/更新清单与 issue 链接。”
4. **执行 Step-3**
   - “对 issue #42 用 claude-code 生成详细设计与测试矩阵。”
5. **等待 Gate-2 后执行 Step-4**
   - “对 issue #42 用 codex 开发并运行验证循环，直到通过或达到上限。”
6. **执行 Step-5**
   - “生成 patch 与发信草案，先 dry-run；等我确认后再发送。”

---

## 7. 并发策略（避免跑崩）

建议：
- 并发 issue 数：`2~3`
- 每个 issue 最多修复循环：`6~8`
- 永远先小批量验证，再扩并发

不要一口气并发 10+ issue，会把测试资源和排障信噪比全部打烂。

---

## 8. 失败处理（按故障类型）

1. **扫描误报高**
   - 调整 `prompts.yaml` 的差距判定规则
   - 增加“证据置信度”字段，低置信不自动建 issue

2. **方案质量不稳**
   - 在 `03_plan_with_claude.sh` 强制输出固定模板
   - 必须包含“不可行路径”与“回滚策略”

3. **Codex 循环卡死**
   - 降低单轮修改范围（文件级拆任务）
   - 达到上限立即回退到 Claude 重做方案

4. **patch 评审反馈差**
   - 强化 cover letter：问题、方案、数据三段式
   - 引入历史 lore 线程引用，减少重复讨论

---

## 9. 运营节奏建议（你直接照抄）

- 每周一：Step-1 全量扫描
- 每周二~四：Step-3/4 开发闭环
- 每周五：Step-5 批量发信（先 dry-run，再正式）

这样能形成稳定节奏，不会被上下游打断。

---

## 10. 最短落地路径（今天就能开始）

今天你只做这 4 件事：

1. 配好 `workflow.yaml`
2. 跑 `01_scan_gaps.sh`
3. 手工确认 Top-3 gap（Gate-1）
4. 跑 `02_sync_issues.sh` + `03_plan_with_claude.sh --issue <top1>`

到这一步，你就已经进入可持续流水线了。

---

## 11. 你下一条可直接发给 OpenClaw 的指令

> “按 `kernel/openclaw/config/workflow.yaml` 执行 Step-1 和 Step-2：先扫描 riscv vs arm/x86 的 Linux/KVM 差距并生成 `state/gap_registry.yaml`，等待我完成 Gate-1 后再同步到 GitHub issue，最后给我一份新建/更新 issue 的汇总表。”

这条就能开始跑第一轮。