# oh-my-claw MVP Implementation Plan（Phase 1 细化版）

## 1. 文档目标

本文档将 `oh-my-claw` 的 `Phase 1` 拆分为：

- 工作流级任务
- 模块级任务
- 文件级任务
- 接口级任务
- 测试级任务
- 集成顺序

目标不是继续讨论“做什么”，而是明确：

> **先创建哪些目录和文件，先实现哪些接口，先跑通哪些最小链路，如何一步步做出 Phase 1 的无前端可演示 MVP。**

---

## 2. Phase 1 的唯一目标

Phase 1 只证明一个闭环：

> 用户输入一个典型 coding 任务后，`oh-my-claw` 能完成任务决策、项目上下文扫描、guardrails 执行、workflow 运行和统一 handoff summary 输出。

Phase 1 不追求：

- continuity state
- safe edit
- doctor 完整版
- 前端面板
- 高级多角色 orchestration

这些属于后续阶段。

---

## 3. Phase 1 最终交付物

完成 Phase 1 后，应至少具备：

### 3.1 可运行产物

- 一个可加载的 `oh-my-claw` 插件原型
- 一套 MVP 配置 schema
- 一个可工作的 Task Decision Engine
- 一个可工作的 Project Context Injector
- 一套 Guardrails Core（四个 Gate 中至少 3 个完整可用）
- 三个 workflow 模板：
  - `design-proposal`
  - `feature-implementation`
  - `bug-fix`
- 一套统一 exit summary 输出
- 一组 CLI/slash command 入口

### 3.2 可验证产物

- 单元测试
- 最小集成测试
- 示例输入与示例输出
- 一份运行说明

### 3.3 可演示场景

- 方案设计任务
- 小功能实现任务
- bug 修复任务

---

## 4. 推荐目录结构（Phase 1 范围）

建议直接以最终可演进结构开始，但只实现 Phase 1 必要部分。

```text
oh-my-claw/
├── README.md
├── docs/
│   ├── architecture.md
│   ├── mvp-plan.md
│   └── workflows.md
├── plugin/
│   ├── package.json
│   ├── tsconfig.json
│   ├── src/
│   │   ├── index.ts
│   │   ├── config/
│   │   │   ├── schema.ts
│   │   │   ├── defaults.ts
│   │   │   ├── loader.ts
│   │   │   └── types.ts
│   │   ├── shared/
│   │   │   ├── errors.ts
│   │   │   ├── logger.ts
│   │   │   ├── result.ts
│   │   │   ├── constants.ts
│   │   │   └── types.ts
│   │   ├── decision/
│   │   │   ├── engine.ts
│   │   │   ├── rules.ts
│   │   │   ├── complexity.ts
│   │   │   ├── intents.ts
│   │   │   └── types.ts
│   │   ├── context/
│   │   │   ├── scanner.ts
│   │   │   ├── summarizer.ts
│   │   │   ├── relevance.ts
│   │   │   ├── cache.ts
│   │   │   └── types.ts
│   │   ├── gates/
│   │   │   ├── base.ts
│   │   │   ├── entry-gate.ts
│   │   │   ├── edit-gate.ts
│   │   │   ├── verify-gate.ts
│   │   │   ├── exit-gate.ts
│   │   │   └── types.ts
│   │   ├── workflows/
│   │   │   ├── registry.ts
│   │   │   ├── engine.ts
│   │   │   ├── types.ts
│   │   │   ├── skeleton.ts
│   │   │   └── templates/
│   │   │       ├── design-proposal.ts
│   │   │       ├── feature-implementation.ts
│   │   │       └── bug-fix.ts
│   │   ├── summary/
│   │   │   ├── builder.ts
│   │   │   ├── format.ts
│   │   │   └── types.ts
│   │   ├── commands/
│   │   │   ├── register.ts
│   │   │   ├── plan.ts
│   │   │   ├── design.ts
│   │   │   ├── implement.ts
│   │   │   ├── debug.ts
│   │   │   ├── context-scan.ts
│   │   │   └── types.ts
│   │   └── __tests__/
│   │       ├── decision/
│   │       ├── context/
│   │       ├── gates/
│   │       ├── workflows/
│   │       ├── commands/
│   │       └── integration/
├── workflows/
│   └── examples.md
├── examples/
│   ├── design-input.md
│   ├── feature-input.md
│   └── bugfix-input.md
└── tasks/
    ├── todo.md
    └── lessons.md
```

---

## 5. 实施总顺序（强依赖顺序）

严格推荐以下顺序，不建议打乱：

1. **shared + config 基础层**
2. **decision engine**
3. **context scanner / summarizer**
4. **gates core**
5. **workflow skeleton + registry**
6. **三套模板**
7. **summary builder**
8. **commands 接线**
9. **integration tests**
10. **文档与示例**

原因：

- 决策层依赖配置和共享类型
- 上下文层依赖共享类型与日志
- Gate 层依赖 decision + context
- Workflow 层依赖 Gate
- Commands 依赖 workflow engine
- 集成测试必须在链路成形后再补

---

## 6. 工作流拆分（按开发泳道）

## 6.1 Workstream A：Foundation

### 目标

建立所有后续模块都会依赖的基础能力。

### 文件任务

#### `plugin/src/shared/types.ts`
- [ ] 定义通用基础类型
- [ ] 定义 `MaybePromise`
- [ ] 定义 `KeyValue`
- [ ] 定义 `Timestamp` 类型别名

#### `plugin/src/shared/result.ts`
- [ ] 定义统一 `Result<T, E>` 结构
- [ ] 定义 `ok()`
- [ ] 定义 `err()`

#### `plugin/src/shared/errors.ts`
- [ ] 定义基础错误类型
- [ ] 定义配置错误
- [ ] 定义决策错误
- [ ] 定义 workflow 错误
- [ ] 定义 gate 错误

#### `plugin/src/shared/logger.ts`
- [ ] 定义结构化 logger 接口
- [ ] 实现 `debug/info/warn/error`
- [ ] 支持模块名字段
- [ ] 支持 taskId 字段

#### `plugin/src/shared/constants.ts`
- [ ] 定义默认最大文档数量
- [ ] 定义默认复杂度阈值
- [ ] 定义默认日志字段名

### 配置层文件任务

#### `plugin/src/config/types.ts`
- [ ] 定义配置类型
- [ ] 定义模块开关类型
- [ ] 定义 workflow 配置类型

#### `plugin/src/config/defaults.ts`
- [ ] 定义默认配置
- [ ] 定义默认 workflow 映射

#### `plugin/src/config/schema.ts`
- [ ] 定义 schema
- [ ] 定义校验规则
- [ ] 定义可选字段

#### `plugin/src/config/loader.ts`
- [ ] 实现默认配置加载
- [ ] 实现项目级覆盖
- [ ] 返回标准化配置对象

### 测试任务

- [ ] `shared/result` 单测
- [ ] `config/schema` 单测
- [ ] `config/loader` 单测

### 验收

- [ ] 所有后续模块可以依赖统一配置和基础类型

---

## 6.2 Workstream B：Task Decision Engine

### 目标

实现任务的最小正确路由能力。

### 文件任务

#### `plugin/src/decision/types.ts`
- [ ] 定义 `TaskIntent`
- [ ] 定义 `TaskComplexity`
- [ ] 定义 `TaskIntake`
- [ ] 定义 `DecisionResult`
- [ ] 定义 `DecisionHints`

#### `plugin/src/decision/intents.ts`
- [ ] 定义 intent 常量
- [ ] 提供 intent label helper

#### `plugin/src/decision/complexity.ts`
- [ ] 定义 complexity 规则 helper
- [ ] 定义从信号到复杂度的映射函数

#### `plugin/src/decision/rules.ts`
- [ ] 编写显式命令匹配规则
- [ ] 编写关键词匹配规则
- [ ] 编写复杂度信号规则
- [ ] 编写回退规则

#### `plugin/src/decision/engine.ts`
- [ ] 实现 `decideTask()` 主函数
- [ ] 接入 rules
- [ ] 输出 workflow 推荐
- [ ] 输出 plan/verify/context scan 建议
- [ ] 输出 fallback 策略

### 接口任务

建议主接口：

```ts
export interface TaskIntake {
  userInput: string
  cwd?: string
  explicitCommand?: string
  hasTaskState?: boolean
  recentSummary?: string
}

export interface DecisionResult {
  intent: TaskIntent
  complexity: TaskComplexity
  workflow: string
  requirePlan: boolean
  requireContextScan: boolean
  requireVerification: boolean
  recommendSafeEdit: boolean
  confidence: number
  fallbackWorkflow: string
  reasons: string[]
}
```

### 测试任务

- [ ] design proposal 场景分类测试
- [ ] feature implementation 场景分类测试
- [ ] bug fix 场景分类测试
- [ ] 显式命令优先测试
- [ ] 低置信度回退测试
- [ ] 大任务复杂度判断测试

### 验收

- [ ] 典型输入能路由到正确 workflow
- [ ] 决策结果足够驱动后续 Gate 和 workflow

---

## 6.3 Workstream C：Project Context Injector

### 目标

完成项目规则与任务相关文档的最小扫描和摘要注入。

### 文件任务

#### `plugin/src/context/types.ts`
- [ ] 定义 `ScannedFile`
- [ ] 定义 `ProjectSummary`
- [ ] 定义 `InvariantRule`
- [ ] 定义 `ContextSnapshot`

#### `plugin/src/context/scanner.ts`
- [ ] 实现目录扫描入口
- [ ] 实现父目录遍历
- [ ] 实现关键文件匹配
- [ ] 实现 build/test 文件识别
- [ ] 实现 tasks 文件识别

#### `plugin/src/context/relevance.ts`
- [ ] 定义文档相关性评分规则
- [ ] 实现任务类型与文档类型的映射
- [ ] 实现排序函数

#### `plugin/src/context/summarizer.ts`
- [ ] 实现 invariant rules 提取
- [ ] 实现 project summary 提取
- [ ] 实现 task-relevant docs 摘要生成
- [ ] 实现最大数量裁剪

#### `plugin/src/context/cache.ts`
- [ ] 实现最小缓存接口
- [ ] 按 cwd 缓存 snapshot
- [ ] 支持简单失效策略

### 接口任务

建议主接口：

```ts
export interface ContextSnapshot {
  cwd: string
  rules: InvariantRule[]
  projectSummary: ProjectSummary
  relevantDocs: ScannedFile[]
}

export async function buildContextSnapshot(input: {
  cwd: string
  intent?: string
  maxDocs?: number
}): Promise<ContextSnapshot>
```

### 测试任务

- [ ] AGENTS 提取测试
- [ ] README 识别测试
- [ ] build/test 文件识别测试
- [ ] relevance 排序测试
- [ ] maxDocs 限制测试
- [ ] cache 命中测试

### 验收

- [ ] 能输出结构化上下文摘要
- [ ] 不依赖全文注入也能表达核心规则

---

## 6.4 Workstream D：Guardrails Core

### 目标

用 Gate 机制稳定工程动作，而不是散落的 hook。

### 文件任务

#### `plugin/src/gates/types.ts`
- [ ] 定义 `GateContext`
- [ ] 定义 `GateResult`
- [ ] 定义 `GateDecision`
- [ ] 定义 `VerificationRequirement`

#### `plugin/src/gates/base.ts`
- [ ] 定义 Gate 接口
- [ ] 定义统一执行器
- [ ] 定义 Gate 顺序控制

#### `plugin/src/gates/entry-gate.ts`
- [ ] 实现是否要求先计划
- [ ] 实现小任务豁免
- [ ] 实现显式命令 override

#### `plugin/src/gates/edit-gate.ts`
- [ ] 实现是否已有足够上下文检查
- [ ] 实现缺少上下文时的建议
- [ ] 实现 safe edit 建议字段

#### `plugin/src/gates/verify-gate.ts`
- [ ] 实现是否要求验证
- [ ] 实现按项目类型推荐验证动作
- [ ] 实现未验证警告结构

#### `plugin/src/gates/exit-gate.ts`
- [ ] 实现 handoff 完整性检查
- [ ] 实现未完成任务标记
- [ ] 实现 summary 必填项检查

### 接口任务

建议主接口：

```ts
export interface GateContext {
  intake: TaskIntake
  decision: DecisionResult
  context?: ContextSnapshot
  workflowName?: string
}

export interface GateResult {
  allow: boolean
  warnings: string[]
  actions: string[]
  metadata?: Record<string, unknown>
}
```

### 测试任务

- [ ] Entry Gate 必须计划测试
- [ ] Edit Gate 上下文不足测试
- [ ] Verify Gate 验证建议测试
- [ ] Exit Gate 必填字段测试
- [ ] Gate 链执行顺序测试

### 验收

- [ ] 中大型任务能稳定触发计划与验证要求
- [ ] 输出结构可供 workflow engine 使用

---

## 6.5 Workstream E：Workflow Engine + Registry

### 目标

把 Phase 1 的三个 workflow 做成统一骨架。

### 文件任务

#### `plugin/src/workflows/types.ts`
- [ ] 定义 `WorkflowName`
- [ ] 定义 `WorkflowState`
- [ ] 定义 `WorkflowStep`
- [ ] 定义 `WorkflowContext`
- [ ] 定义 `WorkflowExecutionResult`

#### `plugin/src/workflows/skeleton.ts`
- [ ] 定义统一步骤骨架
- [ ] 定义步骤执行约定
- [ ] 定义 step 状态转换逻辑

#### `plugin/src/workflows/registry.ts`
- [ ] 实现模板注册表
- [ ] 支持按名称查找模板
- [ ] 支持从决策结果解析模板

#### `plugin/src/workflows/engine.ts`
- [ ] 实现 workflow 执行器
- [ ] 接入 Gate 链
- [ ] 接入 context snapshot
- [ ] 接入 summary builder

### 模板文件任务

#### `plugin/src/workflows/templates/design-proposal.ts`
- [ ] 定义 design workflow 步骤
- [ ] 组织 output sections
- [ ] 输出方案型 handoff 数据

#### `plugin/src/workflows/templates/feature-implementation.ts`
- [ ] 定义 feature workflow 步骤
- [ ] 输出实现型 handoff 数据

#### `plugin/src/workflows/templates/bug-fix.ts`
- [ ] 定义 bugfix workflow 步骤
- [ ] 输出根因 + 修复 + 验证数据

### 测试任务

- [ ] workflow registry 注册测试
- [ ] workflow selection 测试
- [ ] skeleton 顺序执行测试
- [ ] 三个模板基本执行测试

### 验收

- [ ] 三个模板都能在统一引擎中跑通

---

## 6.6 Workstream F：Summary / Handoff

### 目标

为所有 workflows 生成稳定、统一的输出结构。

### 文件任务

#### `plugin/src/summary/types.ts`
- [ ] 定义 `TaskSummary`
- [ ] 定义 `CompletedItem`
- [ ] 定义 `VerificationSummary`
- [ ] 定义 `RiskItem`
- [ ] 定义 `NextStep`

#### `plugin/src/summary/builder.ts`
- [ ] 实现 summary builder
- [ ] 从 workflow state 提取 summary
- [ ] 从 Gate 结果提取警告与验证信息

#### `plugin/src/summary/format.ts`
- [ ] 实现文本格式化
- [ ] 实现结构化对象输出
- [ ] 保持 command 与 workflow 输出一致

### 测试任务

- [ ] summary builder 单测
- [ ] verification summary 单测
- [ ] risk / next step 格式测试

### 验收

- [ ] 所有 workflows 输出结构统一
- [ ] summary 能直接用于 CLI / slash command 返回

---

## 6.7 Workstream G：Commands 接线

### 目标

将决策、上下文、workflow 和 summary 连接成用户入口。

### 文件任务

#### `plugin/src/commands/types.ts`
- [ ] 定义 command context
- [ ] 定义 command result

#### `plugin/src/commands/register.ts`
- [ ] 注册所有 MVP commands
- [ ] 统一 command 到 handler 的映射

#### `plugin/src/commands/plan.ts`
- [ ] 强制走 plan 模式
- [ ] 输出计划摘要

#### `plugin/src/commands/design.ts`
- [ ] 绑定 `design-proposal`
- [ ] 强制 context scan

#### `plugin/src/commands/implement.ts`
- [ ] 绑定 `feature-implementation`
- [ ] 默认走 decision + workflow

#### `plugin/src/commands/debug.ts`
- [ ] 绑定 `bug-fix`
- [ ] 默认输出根因导向结构

#### `plugin/src/commands/context-scan.ts`
- [ ] 直接输出 context snapshot 摘要

### 测试任务

- [ ] register 测试
- [ ] design 命令集成测试
- [ ] implement 命令集成测试
- [ ] debug 命令集成测试
- [ ] context-scan 输出测试

### 验收

- [ ] 用户能通过命令直接跑通 3 个 workflow

---

## 6.8 Workstream H：Plugin Entry Integration

### 目标

把所有模块在插件入口中组装起来。

### 文件任务

#### `plugin/src/index.ts`
- [ ] 加载配置
- [ ] 初始化 logger
- [ ] 初始化 decision engine
- [ ] 初始化 context builder
- [ ] 初始化 gates
- [ ] 初始化 workflow registry
- [ ] 初始化 summary builder
- [ ] 注册 commands
- [ ] 暴露插件入口

### 测试任务

- [ ] 插件初始化冒烟测试
- [ ] 配置加载 + command 注册集成测试

### 验收

- [ ] 插件能成功初始化并响应命令

---

## 7. 集成顺序（按迭代执行）

## Iteration 1：Foundation

目标：先把基础层准备好。

- [ ] 完成 `shared/*`
- [ ] 完成 `config/*`
- [ ] 跑通配置加载测试

## Iteration 2：Decision

目标：让系统先能“知道自己该走哪条路”。

- [ ] 完成 `decision/*`
- [ ] 跑通意图/复杂度测试
- [ ] 准备示例输入样本

## Iteration 3：Context

目标：让系统先能“理解项目规则”。

- [ ] 完成 `context/*`
- [ ] 跑通上下文提取测试
- [ ] 打通 decision + context 的最小链路

## Iteration 4：Gates

目标：让系统有工程门禁。

- [ ] 完成 `gates/*`
- [ ] 跑通 Gate 顺序测试
- [ ] 打通 decision + context + gates 链路

## Iteration 5：Workflow Core

目标：让系统有统一 workflow 骨架。

- [ ] 完成 `workflows/types.ts`
- [ ] 完成 `skeleton.ts`
- [ ] 完成 `registry.ts`
- [ ] 完成 `engine.ts`

## Iteration 6：Templates + Summary

目标：让系统能产出真正可交付结果。

- [ ] 完成三个模板
- [ ] 完成 summary builder
- [ ] 跑通 workflow 到 summary 链路

## Iteration 7：Commands + Entry

目标：形成可演示 MVP。

- [ ] 完成 commands
- [ ] 完成入口组装
- [ ] 跑通命令级集成测试

## Iteration 8：Examples + Docs

目标：让 MVP 可运行、可演示、可交接。

- [ ] 补 README 最小运行说明
- [ ] 补示例输入
- [ ] 补示例输出
- [ ] 补 Phase 1 演示脚本

---

## 8. 测试计划（按层）

## 8.1 单元测试

### 决策层
- [ ] intent 规则测试
- [ ] complexity 测试
- [ ] fallback 测试

### 上下文层
- [ ] scanner 测试
- [ ] summarizer 测试
- [ ] relevance 测试
- [ ] cache 测试

### Gate 层
- [ ] entry gate 测试
- [ ] edit gate 测试
- [ ] verify gate 测试
- [ ] exit gate 测试

### Workflow 层
- [ ] registry 测试
- [ ] skeleton 测试
- [ ] template 测试

### Summary 层
- [ ] builder 测试
- [ ] formatter 测试

## 8.2 集成测试

- [ ] decision → context → gates
- [ ] decision → workflow selection
- [ ] workflow → summary
- [ ] command → workflow → summary
- [ ] plugin init → commands ready

## 8.3 场景测试

- [ ] 方案设计场景
- [ ] 小功能实现场景
- [ ] bug 修复场景

## 8.4 冒烟测试

- [ ] 配置加载冒烟
- [ ] 命令注册冒烟
- [ ] 三个 command 启动冒烟

---

## 9. 文档任务

## 9.1 最低必需文档

- [ ] `README.md`：如何安装、如何运行、有哪些命令
- [ ] `docs/architecture.md`：Phase 1 架构概览
- [ ] `docs/mvp-plan.md`：MVP 边界
- [ ] `docs/workflows.md`：三个 workflow 的说明

## 9.2 示例文档

- [ ] `examples/design-input.md`
- [ ] `examples/feature-input.md`
- [ ] `examples/bugfix-input.md`
- [ ] 三个对应的预期输出样例

---

## 10. 团队并行建议（Phase 1）

## 10.1 如果只有 1 人

严格按以下顺序：

1. Foundation
2. Decision
3. Context
4. Gates
5. Workflow Core
6. Templates
7. Summary
8. Commands
9. Entry
10. Tests + Docs

## 10.2 如果有 2 人

### 人员 A
- shared/config
- decision
- gates
- entry integration

### 人员 B
- context
- workflows
- summary
- commands

约束：

- A 和 B 先对齐共享类型
- `workflows/types.ts` 与 `decision/types.ts` 要优先冻结
- summary 类型在模板开发前冻结

## 10.3 如果有 3 人

### 人员 A
- shared/config/decision

### 人员 B
- context/gates

### 人员 C
- workflows/summary/commands

额外建议：

- 第 3 人不要过早开始 commands，先等 workflow core 稳定

---

## 11. Phase 1 完成定义（Definition of Done）

只有满足以下条件，才能认为 Phase 1 完成：

### 功能
- [ ] 三个 workflows 可运行
- [ ] 至少五个基础命令可调用
- [ ] 决策/上下文/gates/workflow/summary 链路打通

### 质量
- [ ] 核心模块均有单测
- [ ] 主链路有集成测试
- [ ] 配置加载与命令注册具备冒烟测试

### 体验
- [ ] 无前端也可完整演示
- [ ] 输出结构稳定
- [ ] 对三类典型任务有清晰结果

### 文档
- [ ] README 可指导本地运行
- [ ] 示例输入输出可复现

---

## 12. 最终建议

Phase 1 的本质不是“把所有模块先搭出来”，而是：

> **以最少的模块，证明 `oh-my-claw` 能稳定地把 coding task 变成一个受控、可复用、可总结的工程流程。**

所以实施时最重要的不是功能数量，而是顺序：

1. 先冻结共享类型和最小接口
2. 先跑通决策和上下文
3. 再加工程 Gate
4. 再套统一 workflow 骨架
5. 最后接命令、示例和文档

如果顺序反了，后期返工会明显增加。
