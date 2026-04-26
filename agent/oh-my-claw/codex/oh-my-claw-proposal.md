# oh-my-claw 项目方案（优化版）

## 1. 文档定位

本文档是 `oh-my-claw` 的优化版项目方案，目标不是继续横向堆功能，而是进一步提升：

- 决策清晰度
- 范围收敛程度
- 架构边界明确度
- MVP 落地性
- 后续实施可管理性

相较前一版，本版重点优化以下问题：

1. **方案还偏“能力罗列”**，需要更明确的主线与优先级
2. **模块之间依赖关系不够显式**，容易导致实现时并行失控
3. **成功指标偏概念化**，需要更可验证的衡量标准
4. **缺少治理机制**，例如哪些行为必须稳定、哪些允许实验
5. **缺少用户分层与场景分层**，导致功能设计可能过重
6. **缺少明确的实施顺序和淘汰规则**，不利于 MVP 聚焦

---

## 2. 先给结论：当前方案还能优化什么

基于当前方案，仍有以下几个方向可继续优化。

## 2.1 需要从“模块清单”升级为“价值闭环”

当前方案已经有较完整的模块设计，但还可以进一步强化“最小闭环”的定义。

对 `oh-my-claw` 而言，真正的闭环不是“有 Intent Router、有 Guardrails、有 Workflow”，而是：

> 用户提出一个编码任务 → 系统正确判断任务类型 → 自动读取项目约束 → 进入合适流程 → 执行时不容易改错代码 → 完成前强制验证 → 会话中断后还能继续。

因此，后续实现与文档都应围绕这个闭环来组织，而不是按模块平铺推进。

## 2.2 需要更明确地区分“平台能力”和“增强能力”

当前方案已经强调不重复 OpenClaw 平台能力，但还可以更进一步：

- 凡是 OpenClaw 已提供底层能力的，`oh-my-claw` 只做**策略层**与**体验层**
- 凡是 OpenClaw 未提供且与 coding workflow 高度相关的，`oh-my-claw` 才做**工具层**扩展
- 凡是尚不确定 OpenClaw 后续是否会原生吸收的能力，优先做成**松耦合插件能力**，避免未来难以合并或迁移

## 2.3 需要引入“强决策、弱配置”的原则

当前方案已有配置设计，但如果开放太多开关，会导致：

- 用户不知道应该如何配置
- 文档复杂
- 真实体验不一致
- 调试与诊断变难

建议 `oh-my-claw` 采用：

- **少量强默认值**
- **有限可调参数**
- **关键安全行为不可轻易关闭**

也就是说，`oh-my-claw` 不应是“一个可无限配置的工具箱”，而应是“带明确工作哲学的 coding workflow opinionated layer”。

## 2.4 需要加入“放弃清单”

一个成熟方案不只要说明做什么，也要说明**明确不做什么**。

建议把“不做”分为三类：

- **MVP 不做**：现在先不做，后面可能做
- **长期不做**：不符合项目定位
- **依赖 OpenClaw 原生演进，不单独做**

这会让方案更加稳健。

## 2.5 需要更明确的风险优先级

当前文档已有风险分析，但仍可优化为：

- 哪些是 **项目失败级风险**
- 哪些是 **体验退化级风险**
- 哪些是 **可接受技术债**

否则开发时很容易把精力花在次要问题上。

---

## 3. 优化后的核心定义

## 3.1 一句话定义

> `oh-my-claw` 是一个建立在 OpenClaw 之上的、面向编码任务的“默认工程化执行层”，让代理像资深工程师团队一样稳定地规划、执行、验证和续做任务。

## 3.2 核心价值主张

它的核心不是“更强的模型能力”，而是：

- 更少走错流程
- 更少忽略项目约束
- 更少编辑冲突和误改
- 更稳定的计划 / todo / 验证行为
- 更可靠的中断恢复与任务续做

## 3.3 核心产品哲学

建议明确写入项目哲学：

1. **Plan-first over freestyle**
2. **Project rules before code changes**
3. **Fail-safe over silent success**
4. **Minimal change over broad rewrite**
5. **Continuity over stateless turns**
6. **Opinionated defaults over config sprawl**

这组原则会决定很多设计取舍。

---

## 4. 优化后的项目边界

## 4.1 `oh-my-claw` 应该做什么

`oh-my-claw` 只聚焦五类增强：

1. **入口决策增强**：任务分类、复杂度判断、流程路由
2. **工程上下文增强**：项目规则扫描与结构化注入
3. **执行可靠性增强**：计划、todo、验证、恢复、continuity
4. **编辑安全性增强**：Hashline-style safe edit
5. **默认协作增强**：coding roles + workflow templates

## 4.2 `oh-my-claw` 不应该做什么

### 长期不做

- 不做通用聊天产品层
- 不做 OpenClaw 网关能力替代
- 不做通用 MCP 平台替代
- 不做全功能 IDE 插件平台
- 不做笨重 dashboard first 产品

### MVP 不做

- 高级 UI 状态面板
- 多维度 telemetry / analytics 平台
- 复杂 model fallback orchestration
- 跨文件事务 safe edit
- AST refactor engine

### 不单独做，依赖 OpenClaw 原生演进

- 通用插件安装/生命周期管理
- 通用 skills registry
- 通用 compaction 基础设施
- 通用 subagent runtime

---

## 5. 用户分层与场景分层

当前方案还可以优化的一点，是增加“为谁设计”的维度。

## 5.1 目标用户分层

### 用户类型 A：个人开发者

痛点：

- 希望 agent 少跑偏
- 希望进入仓库后少解释
- 希望 agent 更像靠谱 coding assistant

最需要：

- Intent Router
- Context Injector
- Guardrails
- 基础 Workflow Templates

### 用户类型 B：重度 agent 工作流用户

痛点：

- 多步骤任务不稳定
- 任务容易中断
- 多 agent 结果汇总差

最需要：

- Continuity State
- Orchestrator
- Safe Edit
- Reviewer / Planner roles

### 用户类型 C：团队级规范使用者

痛点：

- 希望 agent 遵守项目流程
- 希望结果可复查、可验证、可审计

最需要：

- Todo Sync
- Lessons Hook
- Verification Hook
- Coding Doctor
- 统一 workflow 模板

## 5.2 场景优先级分层

建议按真实收益排序：

### P0 场景

- 方案设计
- 小功能实现
- bug 修复
- 仓库 onboarding

### P1 场景

- 多文件重构
- 大任务多角色协作
- compaction / resume 后续做

### P2 场景

- 高级多模型路由
- 深度分析与追踪
- UI 可视化调度

这样可以帮助项目避免过早围绕低频高级场景设计架构。

---

## 6. 优化后的主闭环

建议把整个项目方案收敛为一个主闭环。

## 6.1 主闭环定义

### Step 1：Task Intake

接收任务，提取用户目标、上下文、显式命令和目录信息。

### Step 2：Intent + Complexity Decision

判断：

- 这是什么任务
- 有多复杂
- 是否需要计划
- 是否需要多角色
- 是否需要 safe edit

### Step 3：Project Context Acquisition

自动扫描：

- 项目规则
- 构建系统
- 测试系统
- 任务文件
- 架构/说明文档

### Step 4：Workflow Selection

进入对应模板：

- design
- feature
- bugfix
- refactor
- onboarding

### Step 5：Guarded Execution

执行过程中自动保证：

- 有计划
- todo 同步
- 编辑更安全
- 失败可恢复
- 最终有验证

### Step 6：Continuity Persistence

如果任务没结束，自动保留状态，方便继续。

### Step 7：Final Handoff

输出统一结构总结：

- 做了什么
- 改了哪里
- 如何验证
- 剩余风险
- 下一步建议

## 6.2 为什么这个闭环重要

因为后续所有模块都可以通过这个闭环判断价值：

- 不能增强闭环的，不优先做
- 不能减少失败率的，不优先做
- 不能减少用户手动提醒的，不优先做

---

## 7. 模块之间的依赖关系优化

当前方案一个可继续优化的点是：模块虽全，但依赖关系还可以更加明确。

## 7.1 依赖分层

### 第一层：必须最先实现

1. `Intent Router`
2. `Project Context Injector`
3. `Guardrails Core`

因为这三者决定主闭环是否成立。

### 第二层：建立完整体验

4. `Workflow Templates`
5. `Continuity State`
6. `Coding Doctor`

因为这些能力使系统从“能用”变成“稳定可重复”。

### 第三层：建立强差异化

7. `Hashline-style Safe Edit`
8. `Advanced Orchestrator`
9. `Recovery Extensions`

这些能力重要，但不该阻塞 MVP 第一阶段。

## 7.2 依赖图（逻辑）

- `Intent Router` 依赖轻量上下文，但不依赖 full workflow
- `Context Injector` 依赖 repo scanner 与 summarizer
- `Guardrails` 依赖任务复杂度判断与 workflow state
- `Workflow Templates` 依赖 intent 路由结果
- `Continuity State` 依赖 workflow state 与 task state
- `Safe Edit` 依赖 execution layer，但不应成为 routing 前置依赖
- `Doctor` 依赖配置与能力注册状态

## 7.3 实施启示

实现时不要并行推动所有模块，应按依赖顺序推进，否则测试复杂度和集成成本会迅速膨胀。

---

## 8. 当前方案最值得继续优化的具体点

下面给出对现有方案的直接优化建议。

## 8.1 对 Intent Router 的优化

### 当前可改进点

- 目前更像分类器描述，还不够“决策器”
- 缺少“低置信度回退”的操作规范
- 缺少“错误分类代价”的设计

### 优化建议

Intent Router 不只输出 `intent`，还应输出：

- 推荐 workflow
- 推荐角色数
- 推荐是否启用 plan enforcement
- 推荐是否需要 verification gate
- 推荐是否需要 safe edit
- 回退策略

建议把它定义为 **Task Decision Engine**，其中 `Intent Router` 是子能力。

### 优化后的输出示意

```json
{
  "intent": "feature_implementation",
  "complexity": "medium",
  "workflow": "feature-implementation",
  "plan_mode": "required",
  "context_scan": "required",
  "safe_edit": "recommended",
  "verification": "required",
  "fallback": "repo-onboarding"
}
```

## 8.2 对 Context Injector 的优化

### 当前可改进点

- 目前强调扫描，但还不够强调“过滤与优先级”
- 没有区分“仓库级规则”和“任务级相关文档”

### 优化建议

把上下文分成三层：

1. **Invariant Rules**：AGENTS、CONTRIBUTING、关键安全约束
2. **Project Summary**：技术栈、构建、测试、目录结构
3. **Task-Relevant Docs**：和当前任务直接相关的文档/模块

这样注入效率更高，也更容易控制 token。

## 8.3 对 Guardrails 的优化

### 当前可改进点

- 目前像 hook 列表，尚未形成“关键门禁点”

### 优化建议

把 Guardrails 明确设计为四个 Gate：

1. **Entry Gate**：任务是否需要计划
2. **Edit Gate**：修改前是否已有足够上下文
3. **Verify Gate**：完成前是否进行了合理验证
4. **Exit Gate**：是否保留 continuity state / review summary

这样比“很多 hook”更容易落地与解释。

## 8.4 对 Safe Edit 的优化

### 当前可改进点

- 目前主要是工具协议描述，缺少“什么时候启用”的策略

### 优化建议

定义启用策略：

### 默认启用场景

- 中大型多步骤 coding 任务
- 多 agent 协作修改
- 长上下文会话后的编辑
- 对配置文件、核心逻辑文件的编辑

### 默认不强制启用场景

- 小规模单文件文档编辑
- 快速一次性文本改动

这样 safe edit 不会因为“太重”拖慢所有任务。

## 8.5 对 Workflow Templates 的优化

### 当前可改进点

- 目前阶段定义明确，但各模板之间复用关系还不清楚

### 优化建议

为所有 workflow 定义统一骨架：

- `intake`
- `scan`
- `plan`
- `execute`
- `verify`
- `handoff`

不同 workflow 只是在具体步骤和角色配置上不同。这样：

- 模板维护更容易
- continuity state 更统一
- 验收更容易标准化

## 8.6 对 Coding Doctor 的优化

### 当前可改进点

- 当前更偏 readiness check，缺少“建议优先级”

### 优化建议

Doctor 输出不只要有 `OK/WARN/FAIL`，还应有：

- `severity`
- `blocking`
- `recommended_fix_order`

例如：

1. 缺少项目根识别 → blocking
2. 未检测到测试命令 → warn
3. 未启用 safe edit → info

这样用户知道先修什么。

---

## 9. 新增一个关键优化：治理与稳定性策略

这是当前方案中最应该增加的一块。

## 9.1 为什么需要治理策略

如果没有治理规则，项目很容易走向：

- 模块越来越多
- 行为越来越不可预测
- hooks 相互干扰
- 用户难以理解为什么 agent 这样做

## 9.2 建议引入三层稳定性等级

### Stable

- plan enforcement
- todo sync
- verification gate
- context scan core

这些是项目核心，行为应稳定、默认开启。

### Beta

- continuity enhancements
- advanced orchestration
- recovery strategies

这些能力可以逐步增强，但要有明确边界。

### Experimental

- aggressive auto-routing
- advanced safe edit modes
- model fallback experiments
- adaptive workflow tuning

这些能力必须可单独关闭，并且不能影响核心主闭环。

## 9.3 Hook 冲突治理

建议规定：

- 同一阶段只能有一个主决策器
- Hook 之间必须有明确顺序
- Hook 失败默认回退到保守流程
- 不允许 hook 静默篡改用户关键意图

---

## 10. 新增一个关键优化：衡量指标体系

当前方案已有成功标准，但可以进一步量化。

## 10.1 北极星指标

建议把北极星指标定义为：

> 在中等复杂度 coding 任务中，用户无需重复提醒即可完成“计划 → 执行 → 验证 → 总结”的比例。

## 10.2 核心度量指标

### Routing Quality

- 意图分类正确率
- 低置信度回退率
- 错误路由后的人工纠正率

### Context Quality

- 关键规则命中率
- 遗漏 AGENTS/README 约束的比例
- 平均注入 token 规模

### Execution Quality

- 中大型任务的 plan 生成率
- todo 自动更新覆盖率
- 完成前验证触发率

### Reliability

- stale edit 拦截率
- compaction 后恢复成功率
- 子任务失败后的可恢复率

### User Friction

- 用户显式提醒“先计划/别忘验证/更新 todo”的频率
- 用户重述项目规则的频率

## 10.3 为什么这很重要

有了这些指标，后续每个模块都可以判断：

- 是否真的带来收益
- 是否值得继续迭代
- 是否应降级或删除

---

## 11. 优化后的 MVP 定义

当前 MVP 还可以进一步收敛。

## 11.1 MVP 的唯一目标

> 让 OpenClaw 在典型编码任务中，默认表现得更像一个稳定的资深工程师工作流，而不是一个偶尔聪明、偶尔跑偏的通用 agent。

## 11.2 MVP 必须覆盖的四个能力

MVP 不应平均用力，而应确保以下四个闭环能力成立：

1. **能正确进入流程**：Task Decision Engine
2. **能正确读取项目规则**：Context Injector
3. **能稳定执行工程动作**：Guardrails Core
4. **能稳定交付结果**：Workflow Templates + Exit Summary

## 11.3 MVP 可以推迟的能力

推迟到 Phase 2：

- Safe Edit 完整版
- Advanced Orchestrator
- Lessons Hook 自动化增强
- 高级恢复链路

这能让 MVP 更聚焦、更可交付。

---

## 12. 优化后的阶段路线图

## Phase 1：Core Decision + Guarded Workflow

交付：

- Task Decision Engine
- Context Injector
- Guardrails Core
- 3 个 workflows
- Exit Summary 统一格式

目标：

- 先证明闭环成立

## Phase 2：Continuity + Reliability

交付：

- Continuity State
- Coding Doctor
- Recovery hooks
- Safe Edit MVP

目标：

- 解决中断、恢复、误改和 readiness 问题

## Phase 3：Differentiated Collaboration

交付：

- Advanced Orchestrator
- 多角色优化
- 高级 safe edit 模式
- Beta/Experimental 能力

目标：

- 形成明显差异化

这个阶段划分比原先更强调“闭环先于炫技”。

---

## 13. 对当前方案的直接优化结论

如果要对当前方案做进一步优化，我建议明确做以下五项调整：

### 调整 1：把 `Intent Router` 升级为 `Task Decision Engine`

因为它不应只分类，还应决定后续治理策略。

### 调整 2：把 `Guardrails Pack` 收敛为“四个 Gate”

比大量 hook 更清晰、更可控。

### 调整 3：把 `Workflow Templates` 统一成一套骨架

便于复用、测试、continuity 和文档统一。

### 调整 4：把 `MVP` 进一步收敛到“先证明闭环成立”

先不追求过强的 safe edit、复杂 orchestration、analytics。

### 调整 5：补充治理与度量体系

避免项目后期变成一堆彼此干扰的增强功能。

---

## 14. 优化后的推荐结构

经过以上优化后，我建议将 `oh-my-claw` 的方案主线改写为：

### 核心主线

- `Task Decision Engine`
- `Project Context Model`
- `Guarded Workflow Engine`
- `Continuity State`
- `Safe Edit`（Phase 2 差异化）

### 其中

- `Task Decision Engine` 决定任务入口
- `Project Context Model` 决定系统是否“理解当前项目”
- `Guarded Workflow Engine` 决定流程是否稳定
- `Continuity State` 决定任务是否能跨中断延续
- `Safe Edit` 决定执行是否足够可靠

这个结构比“很多平级模块”更有主次。

---

## 15. 最终优化建议

当前项目方案已经比较完整，但为了真正适合进入实施，我建议把它再收束成下面这个版本的判断标准：

### 每个新能力上线前都要问五个问题

1. 它是否直接增强主闭环？
2. 它是否减少用户重复提醒？
3. 它是否降低错误率或恢复成本？
4. 它是否与 OpenClaw 平台边界清晰？
5. 它是否值得进入 Stable，而不是只做 Experimental？

如果其中大多数答案是否，那么这个能力不应该进入近期计划。

---

## 16. 对现有文档的优化结果

基于本轮评估，当前方案最需要加强的点已经明确为：

- 从“模块设计”转向“闭环设计”
- 从“可配置功能堆叠”转向“强默认工程化流程”
- 从“很多 hook”转向“明确 Gate 机制”
- 从“能力列表”转向“治理 + 度量 + 分阶段收敛”

因此，`oh-my-claw` 更推荐被定义为：

> 一个以 `Task Decision Engine + Project Context Model + Guarded Workflow Engine` 为核心、并逐步引入 Continuity 与 Safe Edit 差异化能力的 OpenClaw 编码工作流增强套件。

---

## 17. 下一步最推荐的动作

如果继续优化，我最建议下一步产出以下两份文档，而不是继续泛化方案：

1. **`MVP implementation plan`**
   - 细化到目录、模块、文件、依赖顺序
   - 明确 Phase 1 只做哪些 Gate 和哪些 workflow

2. **`architecture.md`**
   - 详细定义 `Task Decision Engine`
   - 详细定义 `Project Context Model`
   - 详细定义 `Guarded Workflow Engine`
   - 详细定义状态流和 Hook/Gate 顺序

这两份文档将把当前方案真正推进到可实施状态。
