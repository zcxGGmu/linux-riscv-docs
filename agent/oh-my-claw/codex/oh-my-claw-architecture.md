# oh-my-claw Architecture（MVP / Phase 1）

## 1. 文档目标

本文档定义 `oh-my-claw` 在 MVP / Phase 1 阶段的系统架构，重点回答以下问题：

- `oh-my-claw` 在 OpenClaw 生态中的位置是什么
- 系统核心模块有哪些，边界如何划分
- 任务是如何从输入流转到输出的
- 哪些状态需要在模块之间传递
- 哪些能力属于 MVP 必须实现，哪些应延后
- 为什么要用当前这种架构，而不是更复杂或更激进的方案

本文档与以下文档配套使用：

- `oh-my-claw-proposal.md`
- `oh-my-claw-mvp-phases.md`
- `oh-my-claw-mvp-implementation-plan.md`

如果三者存在冲突，以本架构文档对系统边界和状态流的定义为准；若要更改，应同步更新其他文档。

---

## 2. 设计目标

## 2.1 MVP 目标

MVP 要证明的是：

> `oh-my-claw` 可以将一个典型 coding task 转化为一个受控、可复用、可验证、可总结的工程流程。

在架构层面，这意味着系统必须具备五种核心能力：

1. **Task Decision**：知道应该走哪种流程
2. **Project Context Modeling**：知道当前项目有哪些约束
3. **Guarded Workflow Execution**：知道什么时候该计划、该验证、该总结
4. **Unified Output**：知道如何稳定交付结果
5. **Extensibility**：后续可以加入 continuity、safe edit、doctor，而不破坏主链路

## 2.2 非目标

MVP 架构不追求：

- 多前端终端的复杂适配
- UI 驱动架构
- 复杂异步任务调度系统
- 深度多 agent orchestration
- 高级 safe edit 协议
- 完整事件总线平台化

换句话说，MVP 架构要先保证：**简单、清晰、可扩展，但不过度工程化。**

---

## 3. 总体架构定位

## 3.1 在 OpenClaw 生态中的位置

`oh-my-claw` 不是 OpenClaw 的底层替代品，而是构建在 OpenClaw 之上的 **coding workflow enhancement layer**。

从职责上看，它位于：

- **下层**：OpenClaw 原生 runtime / plugin / skills / workflow / commands 能力
- **上层**：编码任务场景的策略、规则、流程和输出组织

因此，`oh-my-claw` 应该始终维持以下定位：

- 不重做通用平台能力
- 只做 coding workflow 的判断、编排、约束与交付增强

## 3.2 架构原则

本系统遵循以下架构原则：

1. **Single controlled main path**：存在一条稳定主链路
2. **Decision before execution**：先决定流程，再执行流程
3. **Context before mutation**：先理解项目，再进入执行
4. **Gates over scattered hooks**：优先门禁式控制，而非分散副作用
5. **Stable contracts over implicit behavior**：优先明确接口，而不是靠隐式 prompt 行为
6. **CLI/text-first over UI-first**：MVP 阶段以文本交付路径为主
7. **Extensible but not overgeneralized**：可扩展，但不一开始平台化过度

---

## 4. 核心架构视图

## 4.1 逻辑分层

建议把 `oh-my-claw` 划分为五层：

### Layer 1：Entry Layer

负责接收用户输入与命令，并形成标准化任务入口。

包含：

- commands
- plugin entry
- task intake normalizer

### Layer 2：Decision Layer

负责确定当前任务应走什么流程。

包含：

- Task Decision Engine
- complexity evaluator
- workflow selector

### Layer 3：Context Layer

负责理解当前仓库、当前目录和当前任务相关规则。

包含：

- repo scanner
- context summarizer
- relevance ranker
- context snapshot builder

### Layer 4：Execution Control Layer

负责在进入 workflow 前后施加工程门禁与约束。

包含：

- Entry Gate
- Edit Gate
- Verify Gate
- Exit Gate
- workflow engine

### Layer 5：Output Layer

负责将执行结果以统一格式交付给用户。

包含：

- summary builder
- formatter
- structured result emitter

---

## 4.2 主数据流

主路径如下：

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

这条链路体现两个重要原则：

- 决策和上下文在前，执行在后
- 输出构建是系统的一等公民，而不是执行后的临时拼接

---

## 5. 核心模块定义

## 5.1 Plugin Entry

### 职责

- 加载配置
- 初始化核心模块
- 注册 commands
- 暴露插件能力
- 管理最小生命周期

### 不负责

- 不做具体业务决策
- 不做上下文解析逻辑
- 不做 workflow 细节执行

### 依赖

- config
- logger
- decision engine
- context builder
- gate runner
- workflow registry
- summary builder

### 架构要求

Plugin Entry 必须保持“薄”，否则会成为系统中最难维护的神对象。

---

## 5.2 Task Intake Normalizer

### 职责

将用户输入转换成标准化的 `TaskIntake`。

### 输入来源

- 普通用户消息
- slash command
- 命令参数
- 当前目录信息
- 可选的最近摘要信息

### 输出

标准 `TaskIntake` 对象。

### 目标

让下游模块不关心“输入来自哪里”，只关心“任务是什么”。

---

## 5.3 Task Decision Engine

### 职责

根据 `TaskIntake` 生成：

- 任务意图
- 复杂度等级
- 推荐 workflow
- 是否必须 plan
- 是否必须 context scan
- 是否必须 verification
- 是否建议 safe edit
- 低置信度回退路径

### 本质

这不是一个纯分类器，而是一个 **任务决策器**。

### 为什么必须独立成模块

因为：

- 后续 Gate 和 workflow 都依赖其结果
- 它是主链路的第一个“强决策点”
- 如果和 command 或 workflow 耦合，会导致逻辑分散、难测试

### MVP 设计取舍

MVP 阶段只用：

- 规则
- 关键词
- 显式命令优先
- 简单复杂度信号

不引入复杂模型路由或黑盒分类器。

---

## 5.4 Project Context Model

### 职责

构建一个结构化 `ContextSnapshot`，提供任务所需的项目上下文。

### 组成

- Invariant Rules
- Project Summary
- Task-Relevant Docs

### 为什么采用三层模型

因为它兼顾：

- 必须遵守的规则
- 当前项目的基础认知
- 当前任务的特定信息

这样既能减少遗漏，也能控制上下文膨胀。

### 核心输出

`ContextSnapshot` 必须是结构化的，而不是一堆拼接文本。

这能让：

- Gate 更容易判断
- Workflow 更容易消费
- 后续 continuity 更容易接入

---

## 5.5 Repo Scanner

### 职责

扫描当前目录及其父目录，发现：

- `AGENTS.md`
- `README.md`
- `CONTRIBUTING.md`
- build/test 配置
- docs / architecture 文档
- `tasks/` 文件

### 不负责

- 不做最终摘要
- 不做 workflow 决策

### 设计原则

Scanner 应该“多发现、少解释”；解释交给 summarizer。

这样模块边界更稳定。

---

## 5.6 Context Summarizer

### 职责

将 scanner 的发现结果转换为：

- invariant rules
- project summary
- relevant docs 摘要

### 不负责

- 不做目录遍历
- 不做 workflow 决策

### 设计原则

Summarizer 只做“结构化摘要”，不做自由风格生成。

---

## 5.7 Guarded Workflow Engine

这是系统的执行控制核心。

### 职责

- 组织 Gate 执行顺序
- 运行 workflow
- 将上下文和决策结果传给 workflow
- 在执行前后施加工程化门禁

### 为什么不用“很多散落 hooks”

因为 coding workflow 最核心的问题不是“有没有 hook”，而是：

- 是否在正确阶段做了正确约束
- 是否能稳定重复
- 是否能被测试和理解

Gate 模式天然更适合控制这些阶段性行为。

---

## 5.8 Entry Gate

### 作用

控制是否必须先进入 planning 语义。

### 决策依据

- 任务复杂度
- 用户显式命令
- workflow 类型
- 项目规则要求

### 输出

- 允许继续
- 要求先计划
- 发出警告但允许继续

---

## 5.9 Edit Gate

### 作用

控制在进入执行前，是否具备足够项目上下文。

### MVP 阶段职责

- 检查是否已经构建 `ContextSnapshot`
- 检查是否存在必要规则摘要
- 给出是否建议 safe edit 的布尔信号

### 注意

MVP 中 Edit Gate 不直接实现 safe edit，只负责为后续阶段预留切入点。

---

## 5.10 Verify Gate

### 作用

在 workflow 完成前检查：

- 是否需要验证
- 推荐执行哪些验证动作
- 若未验证，如何在 summary 中体现

### 设计价值

这让“完成”不再是模型主观判断，而是工程门禁判断。

---

## 5.11 Exit Gate

### 作用

保证输出结果结构完整，并为未来 continuity 预留状态出口。

### 核心检查

- 是否有 summary 必填项
- 是否记录风险和假设
- 是否标注未完成事项
- 是否包含下一步建议

---

## 5.12 Workflow Registry

### 职责

集中管理可用 workflow 模板。

### MVP 范围

- `design-proposal`
- `feature-implementation`
- `bug-fix`

### 为什么需要 Registry

因为后续：

- command 需要通过名称调用 workflow
- decision engine 需要返回 workflow 名称
- testing 需要枚举所有 workflow

---

## 5.13 Workflow Engine

### 职责

按照统一骨架执行 workflow：

- intake
- scan
- plan
- execute
- verify
- handoff

### 不是做什么

它不是一个复杂异步调度器，也不是多 agent runtime。

### 为什么保持简单

MVP 阶段最重要的是统一流程，而不是复杂调度。

---

## 5.14 Workflow Templates

### 职责

定义不同任务类型下的步骤组织与输出要求。

### 三个 MVP 模板

#### `design-proposal`
强调：

- 对比
- 分析
- 方案结构
- 风险

#### `feature-implementation`
强调：

- 上下文理解
- 计划
- 实现
- 验证

#### `bug-fix`
强调：

- 症状
- 根因
- 修复
- 回归验证

### 设计要求

模板之间可以不同，但必须共享统一 workflow 骨架。

---

## 5.15 Summary Builder

### 职责

将 workflow 执行结果、Gate 结果、验证结果整合为统一 summary。

### 为什么必须独立出来

如果 summary 逻辑散落在每个 command 或 workflow 模板中，将造成：

- 输出风格不统一
- 测试困难
- 未来 continuity/doctor 难接入

因此 summary builder 是一等公民模块。

---

## 5.16 Commands Layer

### 职责

把用户命令映射到系统主路径。

### MVP 命令

- `/plan`
- `/design`
- `/implement`
- `/debug`
- `/context-scan`

### 原则

Command 层不应内嵌业务逻辑，只负责：

- 参数归一化
- 调用主链路
- 输出结果

---

## 6. 核心数据模型

本节定义 MVP 中最重要的状态对象。

## 6.1 TaskIntake

表示一个标准化任务输入。

建议字段：

- `userInput`
- `cwd`
- `explicitCommand`
- `recentSummary`
- `hasTaskState`

## 6.2 DecisionResult

表示任务决策结果。

建议字段：

- `intent`
- `complexity`
- `workflow`
- `requirePlan`
- `requireContextScan`
- `requireVerification`
- `recommendSafeEdit`
- `confidence`
- `fallbackWorkflow`
- `reasons`

## 6.3 ContextSnapshot

表示项目上下文的结构化摘要。

建议字段：

- `cwd`
- `rules`
- `projectSummary`
- `relevantDocs`

## 6.4 GateContext

表示 Gate 执行时需要看到的状态。

建议字段：

- `intake`
- `decision`
- `context`
- `workflowName`

## 6.5 WorkflowState

表示 workflow 当前执行状态。

建议字段：

- `workflowName`
- `steps`
- `currentStep`
- `status`
- `artifacts`
- `warnings`

## 6.6 TaskSummary

表示统一交付结果。

建议字段：

- `completed`
- `changedScope`
- `verification`
- `risks`
- `assumptions`
- `nextSteps`

---

## 7. 状态流设计

## 7.1 标准状态流

完整状态流如下：

```text
RAW_INPUT
  -> NORMALIZED_INTAKE
  -> DECIDED
  -> CONTEXT_READY
  -> ENTRY_GATED
  -> EDIT_GATED
  -> WORKFLOW_RUNNING
  -> VERIFY_GATED
  -> EXIT_GATED
  -> SUMMARY_READY
  -> OUTPUT_EMITTED
```

## 7.2 每一步的责任

### `RAW_INPUT -> NORMALIZED_INTAKE`

由 command / intake normalizer 完成。

### `NORMALIZED_INTAKE -> DECIDED`

由 Task Decision Engine 完成。

### `DECIDED -> CONTEXT_READY`

由 Context Layer 完成。

### `CONTEXT_READY -> ENTRY_GATED -> EDIT_GATED`

由 Gate Runner 顺序完成。

### `EDIT_GATED -> WORKFLOW_RUNNING`

由 Workflow Engine 完成。

### `WORKFLOW_RUNNING -> VERIFY_GATED -> EXIT_GATED`

由 Verify/Exit Gate 完成。

### `EXIT_GATED -> SUMMARY_READY`

由 Summary Builder 完成。

### `SUMMARY_READY -> OUTPUT_EMITTED`

由 Formatter / Command Layer 完成。

---

## 8. 错误处理架构

## 8.1 错误分类

建议分为五类：

1. `ConfigError`
2. `DecisionError`
3. `ContextError`
4. `GateError`
5. `WorkflowError`

## 8.2 错误原则

- 尽量在最靠近问题的层抛出结构化错误
- 上层只做转换，不吞掉语义
- 对用户展示时，要给出“影响 + 建议”

## 8.3 MVP 阶段策略

MVP 不需要复杂恢复系统，但必须保证：

- 错误来源可定位
- 输出不会 silently fail
- 命令层能统一呈现错误

---

## 9. 日志与可观测性架构

## 9.1 MVP 需要记录什么

至少记录：

- intake 摘要
- decision result
- context scan 概览
- Gate 触发结果
- workflow 名称与状态
- summary 生成完成

## 9.2 为什么日志要早做

因为：

- 这是判断决策是否合理的核心依据
- 这是未来 doctor 和 metrics 的基础
- 没有日志，架构问题难以定位

---

## 10. 可扩展性预留

尽管 MVP 不实现以下能力，但架构必须预留其接入位置。

## 10.1 Continuity State

未来挂载点：

- Exit Gate 后
- Summary Builder 前后
- WorkflowState 序列化出口

## 10.2 Safe Edit

未来挂载点：

- Edit Gate 决策信号
- Workflow execute 阶段的编辑实现
- summary 中的编辑结果输出

## 10.3 Coding Doctor

未来挂载点：

- config loader 状态
- workflow registry 状态
- context scanner 能力检查
- command 注册状态

## 10.4 Advanced Orchestration

未来挂载点：

- workflow engine 的 execute 阶段
- workflow template 的角色定义
- summary builder 的多子任务汇总

---

## 11. 为什么不采用其他架构

## 11.1 为什么不 UI-first

因为 MVP 核心价值不在可视化，而在执行闭环是否成立。

## 11.2 为什么不 event-bus-first

因为当前系统规模不足以证明复杂事件总线的必要性；过早引入会增加调试成本。

## 11.3 为什么不 multi-agent-first

因为当前阶段要先证明单链路工程化闭环，再做复杂协作。

## 11.4 为什么不 hook-everywhere

因为分散 hook 难以形成稳定、可测试、可解释的工程门禁。

---

## 12. Phase 1 架构验收标准

满足以下条件，说明架构已经成立：

### 功能成立

- 一个输入能稳定进入主链路
- 决策、上下文、Gate、workflow、summary 串联成功
- 三个模板在统一 workflow engine 中工作

### 边界清晰

- command 不承载决策逻辑
- workflow 不承载 summary 组装逻辑
- scanner 不承载摘要逻辑
- plugin entry 不承载业务逻辑

### 可扩展

- continuity 能找到明确挂载点
- safe edit 能找到明确挂载点
- doctor 能找到明确挂载点

### 可测试

- Decision Layer 可单测
- Context Layer 可单测
- Gate Layer 可单测
- Workflow Engine 可集成测试
- 命令主链路可冒烟测试

---

## 13. 架构结论

MVP / Phase 1 最推荐的架构不是“功能越多越好”，而是：

> **以 `Task Decision Engine + Project Context Model + Guarded Workflow Engine + Summary Builder` 为核心主链路的文本优先、门禁驱动、可扩展插件架构。**

这个架构满足当前所有关键要求：

- 足够简单，适合尽快做出 MVP
- 足够清晰，方便多人协作
- 足够稳定，能支持测试和文档化
- 足够可扩展，能承接 continuity / safe edit / doctor / orchestration

因此，后续所有实现和文档，都应围绕这条主链路推进，而不要偏离到 UI-first、multi-agent-first 或 hook-sprawl 的方向上。
