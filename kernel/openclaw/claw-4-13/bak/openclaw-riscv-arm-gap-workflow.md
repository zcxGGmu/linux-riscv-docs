# OpenClaw 多 Agent 工作流方案：RISC-V vs ARM Linux 内核差距发现与修复

> 目标：在 **可配置、可运行、可追踪** 的前提下，持续发现并推进 RISC-V 相较 ARM 的功能/性能差距，最终形成可投递到 `linux-riscv` 邮件列表的补丁。

---

## 0. 总体设计（你给的 5 步的增强版）

你给出的 5 步非常合理，我做了 3 个关键增强：

1. **引入“差距登记与优先级队列”**（避免并发 Agent 重复工作）
2. **在开发环节前置“可复现基线”**（统一复现脚本 + 指标口径）
3. **补丁投递前加“邮件质量闸门”**（checkpatch、cover letter、版本迭代）

最终流程：

- **Phase A 发现**：代码仓库 + 邮件列表 + patchwork 数据采集
- **Phase B 建档**：差距条目标准化（类别、影响、复现、证据）
- **Phase C Issue 化**：在 `zcxGGmu/linux-riscv` 仓库创建 issue
- **Phase D 方案化**：Claude Code 产出设计/测试计划
- **Phase E 实现化**：Codex 编码 + 构建 + 测试循环
- **Phase F 投递化**：生成 patch/series，邮件列表发送并跟踪 review

---

## 1. 角色分工（Multi-Agent）

建议至少 5 类 Agent：

1. **Scout-Agent（侦察）**
   - 输入：Linux upstream、linux-riscv 邮件列表、已有 ARM 能力清单
   - 输出：`gap-candidates.yaml`

2. **Triage-Agent（分诊）**
   - 对候选差距做去重、分级（P0/P1/P2）、可修复性评估
   - 输出：`gap-backlog.yaml`

3. **Issue-Agent（治理）**
   - 按模板批量创建 GitHub issue（避免速率限制，串行或小批）
   - 输出：issue 链接回写 `gap-backlog.yaml`

4. **Design-Agent（Claude Code）**
   - 每个 issue 产出：设计方案、风险点、测试矩阵
   - 输出：`design/<issue-id>-plan.md`

5. **Implement-Agent（Codex）**
   - 按设计编码并执行测试循环，直到质量闸门通过
   - 输出：commit、patch、测试报告

---

## 2. 数据模型（建议）

使用一个统一文件驱动流水线（YAML/JSON 都可），例如：

```yaml
# gap-backlog.yaml
items:
  - id: GAP-2026-001
    title: "riscv lacks XYZ compared to arm64"
    type: "feature|perf|stability|tooling"
    evidence:
      code_refs: []
      mailing_list_refs: []
      benchmark_refs: []
    impact:
      area: "scheduler/mm/io/..."
      severity: "P0|P1|P2"
      user_visible: true
    reproducibility:
      status: "reproducible|needs-env|unknown"
      script: "scripts/repro/GAP-2026-001.sh"
    github:
      issue: null
      assignee: null
    design_doc: null
    impl:
      branch: null
      commits: []
      test_report: null
    patch:
      series_path: null
      sent_to_mailing_list: false
```

---

## 3. OpenClaw 可执行编排（核心）

> 核心原则：长任务交给 ACP 子会话，主会话只做编排与审计。

### 3.1 ACP 会话建议

- **Claude Code 会话**：用于设计文档（深度分析）
- **Codex 会话**：用于实现与迭代（高频改码）

建议参数（概念层）：

- `runtime: "acp"`
- `mode: "session"`（便于持续迭代）
- `thread: true`（保留上下文）
- 显式设置 `agentId`

### 3.2 调度方式建议

- **发现/分诊**：每日定时（cron）运行
- **Issue 创建**：限速串行（避免 API 429）
- **设计与实现**：按 issue 队列并发 2~3 个（可控并发）
- **邮件投递**：必须人工确认后执行（可配置为 gate）

---

## 4. 分步骤落地（对应你的 Step-1~5）

## Step-1 探索差距（仓库 + 邮件列表）

### 输入源

- Linux 主线源码（含 arm64、riscv 子系统对比）
- `linux-riscv` 邮件列表历史线程
-（可选）patchwork / lore 标签过滤

### 方法

1. 建立能力对照表：arm64 功能项 vs riscv 功能项
2. 按子系统扫描：`mm/`, `arch/*`, `kernel/`, `drivers/`
3. 在邮件列表找 “已讨论未落地” 项，避免重复造轮子

### 输出

- `gap-candidates.yaml`
- 每项含：证据链接、受影响版本、最小复现条件

---

## Step-2 在目标仓库创建 issue

目标仓库：`git@github.com:zcxGGmu/linux-riscv.git`

### issue 模板建议

- 背景与对比（ARM 现状 vs RISC-V 现状）
- 影响范围
- 复现步骤
- 预期行为
- 相关讨论/邮件链接
- 验收标准

### 自动化策略

- Triage 后只创建 `P0/P1`，P2 先放 backlog
- 每轮最多创建 N 个（建议 5）
- 写回 issue URL 到 backlog 文件

---

## Step-3 申领 issue + Claude Code 设计方案

### Claude Code 输出要求

每个 issue 产出以下结构：

1. 问题根因假设
2. 设计备选方案（A/B）
3. 兼容性影响（ABI/Kconfig/平台）
4. 测试矩阵（QEMU、真实板卡、内核版本）
5. 回归风险与回滚策略

输出文件：`design/<issue-id>-plan.md`

---

## Step-4 Codex 编码与测试闭环

### 循环机制

1. 拉取设计文档
2. 编码到独立分支 `feat/<issue-id>`
3. 本地构建 + 单测 + 集成测试
4. 若失败，自动修复并重跑
5. 达到闸门后停止

### 质量闸门（最小）

- 编译通过（riscv defconfig + 关键变体）
- 相关测试通过（新增 + 受影响模块）
- 无明显性能倒退（基准阈值如 >3% 触发阻断）
- `checkpatch.pl` 无 blocker

输出：

- `reports/<issue-id>-test-report.md`
- 对应 commits

---

## Step-5 生成 patch 并发送邮件列表

### 规范建议

- 使用 `git format-patch` 生成 series
- cover letter 包含：问题背景、方案摘要、测试结果
- 通过 `git send-email` 发送到 `linux-riscv` 相关列表
- 记录 message-id，后续用于 v2/v3 跟踪

### 审查跟踪

- Review-Agent 定时抓取回复
- 将 review comment 结构化成 TODO
- 驱动 Design + Implement 进入下一轮

---

## 5. 目录结构建议

```text
kernel/openclaw/
  README.md
  openclaw-riscv-arm-gap-workflow.md
  templates/
    issue-template.md
    design-template.md
    test-report-template.md
    cover-letter-template.md
  backlog/
    gap-candidates.yaml
    gap-backlog.yaml
  design/
  reports/
  scripts/
    scan/
    repro/
    issue/
    patch/
```

---

## 6. 运行策略（建议配置）

- **并发上限**：实现 Agent 同时最多 2~3 个
- **失败重试**：同一任务自动重试最多 2 次
- **人工闸门**：
  - 创建 issue 前可选人工审批
  - 发送邮件前强制人工审批（推荐）
- **状态追踪**：任务状态写回 backlog（single source of truth）

---

## 7. 风险与控制

1. **误报差距**：用“证据三元组”（代码/邮件/基准）降低误判
2. **重复 issue**：创建前做标题/关键词近似去重
3. **测试环境漂移**：容器化或固定工具链版本
4. **邮件列表礼仪风险**：严格遵循提交规范与讨论上下文

---

## 8. 最小可运行版本（MVP）

第一阶段建议只做 3 个子系统（例如 mm/sched/arch），每个子系统挑 2 个 gap：

- 6 个 gap 全量跑通 Step-1~5
- 至少形成 2 组可发送 patch series
- 累积一版“模板 + 脚本 + 指标”的可复用流水线

---

## 9. 你可以直接执行的下一步

1. 在 `kernel/openclaw/templates/` 下落 4 个模板文件
2. 先手工产出 `gap-backlog.yaml`（6 条）
3. 启动 Claude Code 会话批量生成设计文档
4. 启动 Codex 会话逐条实现并跑测试
5. 人工审阅后统一发送首轮 patch

---

## 10. 验收标准（Definition of Done）

- 每个 gap 均有：issue + 设计 + 实现 + 测试报告 + patch
- patch 至少发送到邮件列表并获得可追踪反馈
- 流水线可在新增 gap 时复用（无需重搭）

---

如果你愿意，我下一步可以继续给你补一份 **“可直接粘贴的 OpenClaw 编排指令清单（含 ACP 会话启动参数、任务状态机字段、失败重试策略）”**，用于直接上线跑第一轮。
---

## 11. 可直接粘贴的 OpenClaw 编排指令清单（实操版）

> 说明：下面采用 OpenClaw 工具调用风格（JSON 参数），你可以直接作为编排参考。`agentId` 请替换成你环境里可用的 ACP 代理标识。

### 11.1 初始化目录与骨架文件

```bash
mkdir -p /home/zq/work-space/repo/ai-projs/linux-riscv-docs/kernel/openclaw/{templates,backlog,design,reports,scripts/{scan,repro,issue,patch},state}
```

初始化 `backlog/gap-backlog.yaml`：

```yaml
items: []
meta:
  version: 1
  updated_at: null
```

---

### 11.2 Step-1：启动 Scout/Triage（发现 + 分诊）

#### A) 启动 Claude Code（侦察分析会话）

```json
{
  "runtime": "acp",
  "agentId": "claude-code",
  "mode": "session",
  "thread": true,
  "task": "扫描 Linux upstream 与 linux-riscv 邮件列表，输出 RISC-V 相对 ARM 的候选差距到 backlog/gap-candidates.yaml。每条需含 code_refs/mailing_list_refs/impact/repro 建议。"
}
```

#### B) 启动 Claude Code（分诊会话）

```json
{
  "runtime": "acp",
  "agentId": "claude-code",
  "mode": "session",
  "thread": true,
  "task": "读取 backlog/gap-candidates.yaml，做去重、优先级分层(P0/P1/P2)、可修复性评估，并写回 backlog/gap-backlog.yaml。"
}
```

---

### 11.3 Step-2：Issue-Agent 创建 GitHub Issue（限速）

#### Issue 模板（`templates/issue-template.md`）

```md
## 背景
- ARM 现状：
- RISC-V 现状：

## 影响
- 子系统：
- 严重级别：P0/P1/P2

## 复现
1.
2.
3.

## 预期行为

## 参考链接
- 代码：
- 邮件列表：

## 验收标准
- [ ]
```

#### 执行策略

- 每次仅处理 `P0/P1`
- 单次最多创建 5 个 issue
- 每创建一个就写回 `github.issue` 字段
- 如果遇到 429，按 `Retry-After` 退避

---

### 11.4 Step-3：申领 Issue + Claude Code 出设计

对每个 `github.issue` 非空且 `design_doc` 为空的条目，启动设计会话：

```json
{
  "runtime": "acp",
  "agentId": "claude-code",
  "mode": "session",
  "thread": true,
  "task": "针对 ISSUE-<id> 生成详细设计文档 design/<gap-id>-plan.md，包含根因、方案A/B、兼容性影响、测试矩阵、回滚策略。"
}
```

设计模板（`templates/design-template.md`）建议字段：

```md
# <gap-id> 设计方案
## 1. 问题定义
## 2. 根因分析
## 3. 方案A/B对比
## 4. 实施计划（按 commit 切分）
## 5. 测试计划（QEMU/板卡/版本矩阵）
## 6. 风险与回滚
## 7. 验收标准
```

---

### 11.5 Step-4：Codex 实现 + 开发测试验证循环

对每个已有设计、尚未完成实现的条目启动 Codex 会话：

```json
{
  "runtime": "acp",
  "agentId": "codex",
  "mode": "session",
  "thread": true,
  "task": "读取 design/<gap-id>-plan.md，在 linux-riscv 仓库创建分支 feat/<gap-id> 开发实现；执行构建+测试循环，直到通过质量闸门；输出 reports/<gap-id>-test-report.md。"
}
```

质量闸门脚本建议（`scripts/patch/quality-gate.sh`）：

```bash
#!/usr/bin/env bash
set -euo pipefail

# 1) build
make ARCH=riscv defconfig
make -j$(nproc) ARCH=riscv

# 2) checkpatch on new commits (示例)
./scripts/checkpatch.pl --strict --codespell --no-tree $(git format-patch -1 --stdout | cat)

# 3) 可插入自定义 benchmark / kselftest
# ./tools/testing/kunit/kunit.py run
# ./your-benchmark.sh

echo "QUALITY_GATE_PASS"
```

失败重试策略：

- 同一条目最多自动修复重试 2 次
- 第 3 次失败转人工（状态置 `blocked`）

---

### 11.6 Step-5：格式化 Patch 并发送邮件列表

```bash
# 在实现分支上
git format-patch -N -o /tmp/patches/<gap-id> origin/master
```

发送前检查：

1. `checkpatch.pl` 无 blocker
2. `reports/<gap-id>-test-report.md` 完整
3. cover letter 包含测试环境、结果摘要、已知限制

发送（示例）：

```bash
git send-email /tmp/patches/<gap-id>/*.patch
```

回写字段：

- `patch.series_path`
- `patch.sent_to_mailing_list=true`
- `patch.message_id`

---

## 12. 状态机定义（建议直接落到 backlog 字段）

每个 gap 条目的 `state`：

- `new`
- `triaged`
- `issue_created`
- `design_ready`
- `impl_in_progress`
- `impl_failed`
- `impl_passed`
- `patch_ready`
- `sent`
- `blocked`
- `closed`

状态流转：

```text
new -> triaged -> issue_created -> design_ready -> impl_in_progress
impl_in_progress -> impl_passed -> patch_ready -> sent -> closed
impl_in_progress -> impl_failed -> (retry<=2 ? impl_in_progress : blocked)
```

---

## 13. Cron 调度配置建议（OpenClaw）

### 13.1 每日发现任务（隔离会话）

- `sessionTarget`: `isolated`
- `payload.kind`: `agentTurn`
- 计划：每天 09:30（Asia/Shanghai）

任务文案建议：

- “执行 RISC-V vs ARM 差距扫描，更新 gap-candidates.yaml 与 gap-backlog.yaml，输出新增/变化摘要。”

### 13.2 每 2 小时推进队列

- 拉取 `state in {issue_created, design_ready, impl_failed}` 条目
- 按并发上限推进（2~3）

### 13.3 人工审批提醒

- 当出现 `patch_ready` 条目时，发送提醒：
  - “有 N 个 patch 已就绪，待人工审核并发送至 linux-riscv 邮件列表。”

---

## 14. 一轮完整运行 Playbook（MVP）

1. 手工填 6 条 gap 到 `gap-backlog.yaml`
2. 运行 Triage（校验优先级与去重）
3. 创建首批 3~5 个 issue
4. Claude Code 产出全部设计文档
5. Codex 并发实现 2 个，跑质量闸门
6. 产出 patch + test-report
7. 人工审阅后 send-email
8. 记录 message-id，开启 review 跟踪

---

## 15. 实施备注（关键）

- ACP 会话请固定 `mode: session` + `thread: true`，避免上下文丢失
- `agentId` 建议显式区分：`claude-code`（设计）/ `codex`（实现）
- 对外写操作（建 issue、发邮件）要串行或小批，避免限流
- 建议先从 `mm/sched/arch` 三个子系统做 MVP，再扩容到驱动层
