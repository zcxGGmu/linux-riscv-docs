# oh-my-claw

**Batteries-included coding workflow enhancement for OpenClaw.**

`oh-my-claw` 是一个构建在 OpenClaw 之上的编码工作流增强项目。

它的目标不是重做 OpenClaw 的平台能力，而是把 OpenClaw 已有的 runtime / plugin / skills / workflow 能力，组织成一套更适合 coding task 的默认工程流程：

- 更少跑偏
- 更少忽略项目规则
- 更稳定地先计划、再执行、再验证
- 更容易在复杂任务中保持结构化输出
- 更适合演化为真正可用的 coding agent harness

---

## Why

OpenClaw 本身已经很强：

- 有 agent runtime
- 有 workflow / delegate / plugin / skills / MCP 生态
- 有 doctor、compaction、自动化和多渠道能力

但对于“编码代理”这个具体场景，还缺一层更明确的工程化增强：

- 任务入口要先做判断，而不是直接执行
- 进入仓库后要先理解规则，而不是靠模型临场发挥
- 非琐碎任务要先计划
- 结果必须有统一的 handoff summary
- 失败时也要输出有工程价值的部分结果

`oh-my-claw` 就是为了解决这个问题。

---

## Project Positioning

`oh-my-claw` 的定位是：

> **OpenClaw 的 coding workflow enhancement layer**

它聚焦五类增强：

1. **Task Decision**：判断当前任务应该走哪条流程
2. **Project Context Modeling**：自动识别项目规则、构建、测试和任务相关上下文
3. **Guarded Workflow Execution**：通过 Gate 机制稳定 plan / verify / handoff 行为
4. **Workflow Templates**：为高频 coding task 提供统一骨架
5. **Unified Output**：生成结构化、可复用的交付结果

在 Phase 2 之后，还会逐步加入：

- Continuity State
- Safe Edit
- Coding Doctor
- Advanced Orchestration

---

## MVP Focus

MVP / Phase 1 只做一件事：

> 证明 `oh-my-claw` 能把典型 coding task 变成一个稳定、受控、可验证、可总结的工程流程。

### MVP 包含

- `Task Decision Engine`
- `Project Context Model`
- `Guardrails Core`
- 3 个 workflow：
  - `design-proposal`
  - `feature-implementation`
  - `bug-fix`
- 统一 `handoff summary`
- 基础 commands

### MVP 不包含

- 前端面板
- 多 agent 并行 orchestration
- Safe Edit 完整协议
- Continuity State 完整恢复
- Coding Doctor 完整版

---

## Recommended Delivery Strategy

对于 `oh-my-claw`，最佳工程实践是：

> **先完成后端/插件核心闭环，再做轻量前端联调。**

原因很简单：

- MVP 的核心价值在 workflow 主链路，而不在 UI
- 过早前后端并行会导致接口和状态模型反复返工
- 文本/CLI/slash command 足以验证 Phase 1 是否成立

因此推荐顺序是：

1. Phase 0：准备与边界冻结
2. Phase 1：核心后端闭环
3. Phase 2：可靠性增强
4. Phase 3：轻量前端/联调
5. Phase 4：差异化增强

---

## Core Architecture

MVP / Phase 1 的主链路是：

```text
User Input / Command
  -> Task Intake
  -> Task Decision Engine
  -> Context Snapshot Builder
  -> Guardrails (Entry/Edit)
  -> Workflow Engine
  -> Guardrails (Verify/Exit)
  -> Summary Builder
  -> Output Formatter
  -> User
```

核心模块是：

- `Task Decision Engine`
- `Project Context Model`
- `Guarded Workflow Engine`
- `Summary Builder`

这意味着 `oh-my-claw` 的重点不是“堆功能”，而是把这条主链路做稳。

---

## MVP Workflows

Phase 1 只定义三个核心 workflow：

### `design-proposal`

适用于：

- 方案设计
- 差异分析
- 架构提案
- 路线图建议

### `feature-implementation`

适用于：

- 功能实现
- 实施计划
- 结构化交付任务

### `bug-fix`

适用于：

- 问题定位
- 根因分析
- 修复方案
- 回归验证建议

三个 workflow 使用统一骨架：

- `intake`
- `scan`
- `plan`
- `execute`
- `verify`
- `handoff`

---

## Document Map

当前项目的设计文档如下：

### 项目方案

- `oh-my-claw-proposal.md`：总体方案、定位、范围、模块和路线图

### MVP 推进

- `oh-my-claw-mvp-phases.md`：阶段任务清单与前后端推进策略
- `oh-my-claw-mvp-implementation-plan.md`：Phase 1 文件级 / 接口级 / 测试级实施计划

### 设计规格

- `oh-my-claw-architecture.md`：系统架构、模块边界、状态流、扩展点
- `oh-my-claw-workflow-specs.md`：三个 MVP workflow 的规格说明
- `oh-my-claw-config-spec.md`：MVP 配置模型、默认值、校验规则、稳定性等级

### 验收标准

- `oh-my-claw-acceptance-test-plan.md`：系统级验收场景与通过标准

---

## Current Status

当前状态是：

- 已完成总体方案文档
- 已完成 MVP 阶段拆分
- 已完成 Phase 1 实施计划
- 已完成架构、workflow、配置、验收等核心设计文档
- **尚未开始代码实现**

也就是说，当前仓库已经具备比较完整的 **MVP 设计前置文档集**。

---

## What To Do Next

如果下一步准备真正进入开发，推荐顺序是：

1. 按 `oh-my-claw-mvp-implementation-plan.md` 开始搭建项目骨架
2. 优先实现：
   - shared/config
   - decision
   - context
   - gates
   - workflow core
3. 再补：
   - summary
   - commands
   - plugin entry
4. 最后做：
   - integration tests
   - examples
   - README 使用说明完善

如果仍然不写代码，下一份可选文档通常是：

- 更面向对外展示的项目介绍页
- issue / milestone 拆分稿
- task board / roadmap board

---

## Guiding Principles

`oh-my-claw` 的设计遵循以下原则：

1. **Plan-first over freestyle**
2. **Project rules before code changes**
3. **Fail-safe over silent success**
4. **Minimal change over broad rewrite**
5. **Continuity over stateless turns**
6. **Opinionated defaults over config sprawl**

这些原则会直接影响后续实现和配置设计。

---

## Phase 1 Definition of Done

只有满足以下条件，才算 Phase 1 成立：

- 三个核心 workflow 可运行
- Decision / Context / Gates / Workflow / Summary 主链路打通
- 无前端也可完整演示
- 有统一结构的输出
- 有系统级验收场景和通过标准

---

## Long-term Direction

Phase 1 之后，`oh-my-claw` 的自然演进方向包括：

- Continuity State
- Safe Edit MVP
- Coding Doctor
- Advanced Orchestrator
- 更强的 reviewer/planner 能力
- 轻量状态面板

但这些增强都必须建立在 **Phase 1 主闭环已经稳定成立** 的前提上。

---

## Repository Goal

当前仓库的目标不是立刻成为一个“功能丰富的成品”，而是：

> 先把 `oh-my-claw` 设计成一个真正可实施、可验收、可渐进落地的 coding workflow product spec。

现在，第一阶段已经接近完成这个目标。
