# oh-my-claw Milestones and Issues（MVP / Phase 1 Backlog）

## 1. 文档目标

本文档将当前 `oh-my-claw` 设计文档集转化为可执行的 milestone 和 issue backlog，目标是：

- 把抽象设计变成可分配、可追踪、可验收的任务项
- 给出 Phase 1 的推荐开发顺序
- 明确 issue 的优先级、依赖关系和完成标准
- 为后续 GitHub issues / project board / sprint planning 提供基础稿

本文档与以下文档保持一致：

- `README.md`
- `oh-my-claw-proposal.md`
- `oh-my-claw-mvp-phases.md`
- `oh-my-claw-mvp-implementation-plan.md`
- `oh-my-claw-architecture.md`
- `oh-my-claw-workflow-specs.md`
- `oh-my-claw-acceptance-test-plan.md`
- `oh-my-claw-config-spec.md`

---

## 2. Backlog 设计原则

## 2.1 先闭环，后增强

所有 issue 的排序都服从一个原则：

> 先证明 Phase 1 主闭环成立，再进入增强项。

## 2.2 以 milestone 组织，不以模块平铺

虽然实现是模块化的，但管理上应以“阶段交付物”组织，而不是把所有模块平级堆在一个列表里。

## 2.3 每个 issue 都必须可验收

每个 issue 至少要有：

- 清晰目标
- 输入/输出边界
- 依赖说明
- 完成标准

## 2.4 避免超大 issue

每个 issue 应尽量做到：

- 单一目标
- 清晰边界
- 最好可在短周期内完成

不应使用“实现完整 workflow engine”这类过大的 issue 直接进入任务板。

---

## 3. 优先级定义

建议使用以下优先级：

- `P0`：阻塞主闭环，必须优先完成
- `P1`：提升完整性，属于 Phase 1 必需但不一定最先做
- `P2`：优化体验或增强稳定性，可在主链路稳定后完成
- `P3`：Phase 2+ 项目，不进入当前 MVP 冲刺

---

## 4. Milestone 总览

建议采用以下 milestone：

### M0：Project Foundation

目标：

- 建立项目骨架、共享类型、配置系统、最小工具链

### M1：Task Decision + Context

目标：

- 建立任务决策与项目上下文能力

### M2：Guarded Workflow Core

目标：

- 建立 Gate 机制、workflow 骨架和执行链路

### M3：Workflow Templates + Summary

目标：

- 跑通 3 个 MVP workflow 和统一 handoff summary

### M4：Commands + Integration + Acceptance

目标：

- 建立用户入口、集成链路和系统级验收能力

### M5：Phase 1 Documentation Completion

目标：

- 完善运行说明、示例、验收记录、handoff 文档

---

## 5. Milestone M0：Project Foundation

## 5.1 目标

建立所有后续模块都会依赖的基础骨架。

## 5.2 交付结果

- 项目目录初始化
- 基础构建/测试/配置框架
- 共享类型与错误模型
- 配置 schema 和默认值

## 5.3 Issues

### Issue M0-1：初始化项目目录结构

- **优先级**：`P0`
- **依赖**：无
- **目标**：创建 MVP 所需目录结构
- **涉及范围**：`plugin/`, `docs/`, `examples/`, `tasks/`
- **完成标准**：目录结构与实施计划一致

### Issue M0-2：建立基础工程工具链

- **优先级**：`P0`
- **依赖**：M0-1
- **目标**：建立包管理、TS 配置、lint、format、test 基础链路
- **完成标准**：最小脚本可运行

### Issue M0-3：定义 shared types / result / errors

- **优先级**：`P0`
- **依赖**：M0-2
- **目标**：冻结核心基础类型与 Result/Error 模型
- **完成标准**：后续模块可直接依赖 shared 层

### Issue M0-4：实现 logger 基础接口

- **优先级**：`P1`
- **依赖**：M0-3
- **目标**：提供最小结构化日志能力
- **完成标准**：后续模块可输出 decision/context/gates/workflow 日志

### Issue M0-5：定义配置类型与默认值

- **优先级**：`P0`
- **依赖**：M0-3
- **目标**：将 `oh-my-claw-config-spec.md` 转化为类型与 defaults
- **完成标准**：可加载 built-in defaults

### Issue M0-6：实现配置 schema 与 loader

- **优先级**：`P0`
- **依赖**：M0-5
- **目标**：支持配置校验与项目级覆盖
- **完成标准**：能返回标准化配置对象

### Issue M0-7：补基础单测（shared/config）

- **优先级**：`P1`
- **依赖**：M0-3, M0-6
- **目标**：为 shared/config 层建立基础测试
- **完成标准**：shared/config 关键单测通过

## 5.4 M0 验收标准

- 共享层与配置层已可复用
- 配置加载可工作
- 后续决策层可以开始实现

---

## 6. Milestone M1：Task Decision + Context

## 6.1 目标

完成主闭环前半段：知道任务是什么，并知道项目规则是什么。

## 6.2 交付结果

- Task Decision Engine
- Context Scanner / Summarizer
- Context Snapshot

## 6.3 Issues

### Issue M1-1：定义 decision 类型模型

- **优先级**：`P0`
- **依赖**：M0-3
- **目标**：定义 `TaskIntake`, `DecisionResult`, `TaskIntent`, `TaskComplexity`
- **完成标准**：接口稳定，可供 Gate 与 workflow 使用

### Issue M1-2：实现 decision rules

- **优先级**：`P0`
- **依赖**：M1-1, M0-6
- **目标**：实现显式命令优先、关键词识别、复杂度判断、回退逻辑
- **完成标准**：典型输入可得到正确决策结果

### Issue M1-3：实现 Task Decision Engine

- **优先级**：`P0`
- **依赖**：M1-2
- **目标**：统一输出 workflow、plan/context/verify 建议
- **完成标准**：主接口可用

### Issue M1-4：编写 decision 单测

- **优先级**：`P1`
- **依赖**：M1-3
- **目标**：覆盖 design/implement/debug/command override/low confidence
- **完成标准**：关键决策场景单测通过

### Issue M1-5：定义 context 类型模型

- **优先级**：`P0`
- **依赖**：M0-3
- **目标**：定义 `ContextSnapshot`, `ProjectSummary`, `InvariantRule`, `ScannedFile`
- **完成标准**：上下文接口稳定

### Issue M1-6：实现 repo scanner

- **优先级**：`P0`
- **依赖**：M1-5
- **目标**：识别关键规则文件、构建文件、测试文件、任务文件
- **完成标准**：扫描结果可供 summarizer 使用

### Issue M1-7：实现 relevance ranking

- **优先级**：`P1`
- **依赖**：M1-6, M1-3
- **目标**：基于任务类型排序相关文档
- **完成标准**：relevant docs 排序结果可用

### Issue M1-8：实现 context summarizer

- **优先级**：`P0`
- **依赖**：M1-6, M1-7
- **目标**：生成 invariant rules / project summary / relevant docs 摘要
- **完成标准**：可生成结构化 `ContextSnapshot`

### Issue M1-9：实现 context cache

- **优先级**：`P2`
- **依赖**：M1-8
- **目标**：对 snapshot 做最小缓存
- **完成标准**：重复扫描可命中缓存

### Issue M1-10：编写 context 单测

- **优先级**：`P1`
- **依赖**：M1-8, M1-9
- **目标**：覆盖 AGENTS/README/build/test/tasks 识别和排序
- **完成标准**：关键上下文测试通过

## 6.4 M1 验收标准

- 输入任务可得到稳定 decision result
- 项目上下文可形成结构化 snapshot
- M2 可以开始接入 decision + context

---

## 7. Milestone M2：Guarded Workflow Core

## 7.1 目标

建立工程门禁和 workflow 执行主骨架。

## 7.2 交付结果

- Gate types / runner
- 四个 Gate
- workflow state / skeleton / registry / engine

## 7.3 Issues

### Issue M2-1：定义 Gate 类型模型

- **优先级**：`P0`
- **依赖**：M1-3, M1-8
- **目标**：定义 `GateContext`, `GateResult`, `GateDecision`
- **完成标准**：所有 Gate 使用统一接口

### Issue M2-2：实现 Gate runner

- **优先级**：`P0`
- **依赖**：M2-1
- **目标**：定义 Gate 顺序与执行机制
- **完成标准**：可按顺序执行 Gate 链

### Issue M2-3：实现 Entry Gate

- **优先级**：`P0`
- **依赖**：M2-2
- **目标**：控制 planning 语义
- **完成标准**：中大任务可正确触发 plan enforcement

### Issue M2-4：实现 Edit Gate

- **优先级**：`P0`
- **依赖**：M2-2
- **目标**：控制执行前上下文就绪性
- **完成标准**：缺少 context 时可阻止盲目继续

### Issue M2-5：实现 Verify Gate

- **优先级**：`P0`
- **依赖**：M2-2
- **目标**：控制验证语义
- **完成标准**：可输出验证要求或未验证说明需求

### Issue M2-6：实现 Exit Gate

- **优先级**：`P0`
- **依赖**：M2-2
- **目标**：控制 handoff 完整性
- **完成标准**：summary 必填项可被检查

### Issue M2-7：编写 Gate 单测与顺序测试

- **优先级**：`P1`
- **依赖**：M2-3 ~ M2-6
- **目标**：验证每个 Gate 行为和顺序
- **完成标准**：关键 Gate 测试通过

### Issue M2-8：定义 workflow 类型与状态模型

- **优先级**：`P0`
- **依赖**：M2-1
- **目标**：定义 `WorkflowState`, `WorkflowStep`, `WorkflowExecutionResult`
- **完成标准**：workflow 骨架接口稳定

### Issue M2-9：实现 workflow skeleton

- **优先级**：`P0`
- **依赖**：M2-8
- **目标**：实现统一阶段骨架
- **完成标准**：workflow 能按统一阶段顺序运行

### Issue M2-10：实现 workflow registry

- **优先级**：`P0`
- **依赖**：M2-8
- **目标**：支持 workflow 注册与查找
- **完成标准**：decision result 可映射到 workflow

### Issue M2-11：实现 workflow engine

- **优先级**：`P0`
- **依赖**：M2-9, M2-10, M2-2
- **目标**：串联 decision/context/gates/workflow
- **完成标准**：主执行链路跑通

### Issue M2-12：编写 workflow core 测试

- **优先级**：`P1`
- **依赖**：M2-11
- **目标**：验证 registry / skeleton / engine 主链路
- **完成标准**：workflow core 集成测试通过

## 7.4 M2 验收标准

- workflow engine 可以在统一骨架上运行
- Gate 能控制 workflow 执行边界
- M3 可以开始填充模板和输出层

---

## 8. Milestone M3：Workflow Templates + Summary

## 8.1 目标

跑通 3 个 MVP workflow，并输出统一 handoff summary。

## 8.2 交付结果

- 三个模板
- summary builder
- formatter

## 8.3 Issues

### Issue M3-1：实现 `design-proposal` 模板

- **优先级**：`P0`
- **依赖**：M2-11
- **目标**：实现设计型 workflow
- **完成标准**：可完成提案型输出

### Issue M3-2：实现 `feature-implementation` 模板

- **优先级**：`P0`
- **依赖**：M2-11
- **目标**：实现实现型 workflow
- **完成标准**：可完成交付型输出

### Issue M3-3：实现 `bug-fix` 模板

- **优先级**：`P0`
- **依赖**：M2-11
- **目标**：实现 root-cause-first workflow
- **完成标准**：可完成排障型输出

### Issue M3-4：定义 summary 类型模型

- **优先级**：`P0`
- **依赖**：M2-8
- **目标**：定义 `TaskSummary` 及子结构
- **完成标准**：summary 结构稳定

### Issue M3-5：实现 summary builder

- **优先级**：`P0`
- **依赖**：M3-4, M3-1, M3-2, M3-3
- **目标**：从 workflow state 与 Gate 结果构建统一 summary
- **完成标准**：三个 workflow 都可产出统一 summary

### Issue M3-6：实现 summary formatter

- **优先级**：`P1`
- **依赖**：M3-5
- **目标**：输出文本型结构化结果
- **完成标准**：格式满足 workflow 规格要求

### Issue M3-7：编写 workflow 模板测试

- **优先级**：`P1`
- **依赖**：M3-1 ~ M3-6
- **目标**：覆盖三个 workflow 正常/partial/blocked 关键路径
- **完成标准**：模板级测试通过

## 8.4 M3 验收标准

- 三个 workflow 都可运行
- summary 输出结构统一
- Phase 1 主闭环只差入口与验收整合

---

## 9. Milestone M4：Commands + Integration + Acceptance

## 9.1 目标

为系统补上用户入口、端到端链路和系统级验收。

## 9.2 交付结果

- commands
- plugin entry
- 端到端集成
- 验收场景记录

## 9.3 Issues

### Issue M4-1：定义 command 类型模型

- **优先级**：`P1`
- **依赖**：M3-5
- **目标**：统一 command context 与 result 模型
- **完成标准**：commands 使用统一接口

### Issue M4-2：实现 `/plan` 命令

- **优先级**：`P1`
- **依赖**：M4-1, M2-11
- **目标**：提供计划入口
- **完成标准**：可强制进入 planning 语义

### Issue M4-3：实现 `/design` 命令

- **优先级**：`P0`
- **依赖**：M4-1, M3-1
- **目标**：绑定 design workflow
- **完成标准**：command override 生效

### Issue M4-4：实现 `/implement` 命令

- **优先级**：`P0`
- **依赖**：M4-1, M3-2
- **目标**：绑定 feature workflow
- **完成标准**：可触发实现型主链路

### Issue M4-5：实现 `/debug` 命令

- **优先级**：`P0`
- **依赖**：M4-1, M3-3
- **目标**：绑定 bug-fix workflow
- **完成标准**：可触发排障型主链路

### Issue M4-6：实现 `/context-scan` 命令

- **优先级**：`P1`
- **依赖**：M1-8
- **目标**：单独输出 context snapshot 摘要
- **完成标准**：上下文能力可独立验证

### Issue M4-7：实现 plugin entry 组装

- **优先级**：`P0`
- **依赖**：M4-2 ~ M4-6, M0-6
- **目标**：在插件入口中完成所有核心模块装配
- **完成标准**：插件可初始化并响应命令

### Issue M4-8：编写端到端集成测试

- **优先级**：`P0`
- **依赖**：M4-7
- **目标**：覆盖 decision -> context -> gates -> workflow -> summary -> command 主链路
- **完成标准**：主链路集成测试通过

### Issue M4-9：执行系统级验收场景 A/B/C

- **优先级**：`P0`
- **依赖**：M4-8
- **目标**：验证三个核心成功路径场景
- **完成标准**：A/B/C 均 Pass

### Issue M4-10：执行系统级验收场景 D/E/F/G/H

- **优先级**：`P1`
- **依赖**：M4-8
- **目标**：验证降级场景、命令覆盖和 context-scan
- **完成标准**：D/E/F 至少 Partial，G/H Pass

## 9.4 M4 验收标准

- 无前端即可完整演示 Phase 1
- 核心验收场景通过
- MVP 可判定为成立或明确未成立

---

## 10. Milestone M5：Phase 1 Documentation Completion

## 10.1 目标

整理用户入口、示例和交付记录，完成 Phase 1 handoff。

## 10.2 交付结果

- 完整 README
- 示例输入/输出
- 运行说明
- Phase 1 验收记录

## 10.3 Issues

### Issue M5-1：补充 README 运行说明

- **优先级**：`P1`
- **依赖**：M4-7
- **目标**：把 README 从设计入口扩展为运行入口
- **完成标准**：可指导本地验证主链路

### Issue M5-2：整理 examples 输入输出样例

- **优先级**：`P1`
- **依赖**：M4-9, M4-10
- **目标**：沉淀典型样例
- **完成标准**：三类主 workflow 均有示例

### Issue M5-3：整理 Phase 1 验收记录

- **优先级**：`P0`
- **依赖**：M4-9, M4-10
- **目标**：形成可复查的验收结论
- **完成标准**：有最终 pass/partial/fail 结论

### Issue M5-4：整理 Phase 1 handoff 文档

- **优先级**：`P1`
- **依赖**：M5-3
- **目标**：总结实现范围、限制、遗留项、Phase 2 建议
- **完成标准**：下一阶段可直接接手

## 10.4 M5 验收标准

- 仓库不仅有实现，还有可用的交接文档和验收记录

---

## 11. Backlog 依赖关系简表

推荐依赖顺序：

```text
M0 -> M1 -> M2 -> M3 -> M4 -> M5
```

关键阻塞点：

- M0 未完成，M1 无法稳定开始
- M1 未完成，M2 无法接 decision/context
- M2 未完成，M3 无法跑 workflow 模板
- M3 未完成，M4 无法形成完整用户入口链路
- M4 未完成，M5 无法给出有效验收结论

---

## 12. 推荐 Issue 标签

建议至少使用以下标签：

- `phase-1`
- `milestone-m0`
- `milestone-m1`
- `milestone-m2`
- `milestone-m3`
- `milestone-m4`
- `milestone-m5`
- `p0`
- `p1`
- `p2`
- `design`
- `decision`
- `context`
- `gates`
- `workflow`
- `summary`
- `commands`
- `integration`
- `docs`
- `acceptance`

---

## 13. 推荐执行方式

## 13.1 单人推进

严格按 milestone 顺序推进，不建议在 M2 之前提前做 M4 命令层。

## 13.2 双人推进

### 人员 A
- M0
- M1 decision
- M2 gates
- M4 plugin entry

### 人员 B
- M1 context
- M2 workflow core
- M3 templates/summary
- M4 commands/tests

## 13.3 三人推进

### 人员 A
- foundation + decision

### 人员 B
- context + gates

### 人员 C
- workflow + summary + commands

但依然要遵循：

- 类型先冻结
- 配置先冻结
- workflow state 先冻结
- summary 结构先冻结

---

## 14. Phase 1 完成定义（Backlog 视角）

只有满足以下条件，Phase 1 backlog 才算完成：

- M0 完成
- M1 完成
- M2 完成
- M3 完成
- M4 完成
- M5 至少完成核心文档与验收记录

并且：

- 核心场景 A/B/C 验收通过
- D/E/F 至少合理降级
- G/H 通过

---

## 15. Backlog 结论

当前 `oh-my-claw` 已经具备比较完整的设计前置文档集，现在最自然的下一步不是继续增加抽象设计，而是：

> **按 milestone 把 Phase 1 主闭环做出来。**

这份 backlog 的意义就在于：

- 把文档设计转成执行顺序
- 把“想法”转成 issue
- 把“可以开始”转成“知道先做什么”

后续如果需要进入真正开发，这份文档可以直接作为 GitHub Project / Issues 的初稿来源。
