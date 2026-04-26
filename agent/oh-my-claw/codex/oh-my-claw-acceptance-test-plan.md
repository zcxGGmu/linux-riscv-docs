# oh-my-claw Acceptance Test Plan（MVP / Phase 1）

## 1. 文档目标

本文档用于定义 `oh-my-claw` 在 MVP / Phase 1 阶段的验收测试计划，重点回答以下问题：

- 如何判断 MVP 是否真正成立
- 哪些场景必须通过，哪些场景可以延后
- 每个场景的输入、预期 workflow、预期 Gate 行为、预期 summary 是什么
- 测试通过需要什么证据
- 哪些失败是可接受的，哪些失败说明架构或实现存在根本问题

本文档不替代单元测试或集成测试，而是定义 **系统级验收标准**。

本文档与以下文档保持一致：

- `oh-my-claw-proposal.md`
- `oh-my-claw-mvp-phases.md`
- `oh-my-claw-mvp-implementation-plan.md`
- `oh-my-claw-architecture.md`
- `oh-my-claw-workflow-specs.md`

---

## 2. 验收目标

## 2.1 Phase 1 必须证明什么

Phase 1 必须证明以下能力已经成立：

1. 系统能把典型 coding task 路由到正确 workflow
2. 系统能为任务构建足够的项目上下文摘要
3. 系统能在正确阶段触发 Guardrails
4. 系统能按统一 workflow 骨架执行
5. 系统能输出结构化 handoff summary
6. 系统即使在失败或信息不足时，也能输出有价值的阻塞/部分结果

## 2.2 Phase 1 不要求证明什么

以下能力不属于 Phase 1 验收范围：

- continuity state 完整恢复
- safe edit 协议
- doctor 完整诊断链路
- 多 agent 并行协作
- 前端面板
- 高级恢复机制

这些能力可以在后续阶段验收。

---

## 3. 验收原则

## 3.1 只看主闭环，不看边角功能

Phase 1 验收应优先看主闭环：

- decision
- context
- gates
- workflow
- summary

某些次要增强点未完善，不应阻塞 MVP 结论。

## 3.2 看“系统行为”，不只看“模块存在”

模块代码存在不等于通过验收。

通过验收的标志是：

- 用户输入进入后，系统行为正确
- 输出结构符合规格
- 阶段性 Gate 在正确地方触发

## 3.3 看可解释性，不只看成功率

即使 workflow 最终没有 `completed`，如果能明确：

- 当前阻塞点
- 缺失信息
- 建议下一步

也可以视为“合理失败”，而不是验收失败。

## 3.4 看统一性，不只看单个场景偶然成功

验收要确认：

- 三个 workflow 共用统一骨架
- summary 结构统一
- Gate 触发逻辑一致

---

## 4. 验收范围

## 4.1 必测范围

### 核心能力

- Task Decision Engine
- Project Context Model
- Guardrails Core
- Workflow Engine
- Summary Builder
- Commands 主入口

### 核心 workflows

- `design-proposal`
- `feature-implementation`
- `bug-fix`

### 核心命令

- `/design`
- `/implement`
- `/debug`
- `/plan`
- `/context-scan`

## 4.2 非阻塞范围

以下可以记录问题，但不作为 Phase 1 阻塞项：

- 输出文案风格微调
- 日志字段细节优化
- 配置项命名优化
- 低频边缘语义分类

---

## 5. 验收证据要求

每个验收场景至少应保留以下证据：

- 输入样例
- decision result
- context snapshot 摘要
- Gate 执行记录
- workflow 执行状态
- 最终 summary 输出
- 测试结论（pass / partial / fail）

推荐将这些证据保存为：

- 文本输出样例
- 结构化 JSON 样例
- 命令调用记录
- 测试报告摘要

---

## 6. 验收等级定义

## 6.1 Pass

满足以下条件：

- workflow 选择正确
- 必要 Gate 触发正确
- 输出结构完整
- 没有关键字段缺失
- 没有明显违背架构主链路

## 6.2 Partial

满足以下条件：

- 主链路基本成立
- 但某些阶段输出不完整或不够稳定
- 或 workflow 成功降级为部分结果

这种情况可以记录为阶段性通过，但不能视为最终稳定完成。

## 6.3 Fail

满足任一条件：

- workflow 路由明显错误
- Gate 未在关键阶段触发
- 没有输出结构化 summary
- 系统直接中断且无法说明原因
- 输出结果与任务类型严重不匹配

---

## 7. 核心验收场景

以下场景是 Phase 1 必须覆盖的系统级验收场景。

---

## 7.1 场景 A：方案设计任务（标准成功路径）

### 目标

验证系统能正确进入 `design-proposal`，并输出完整提案型结果。

### 输入示例

> 请你参考 oh-my-openagent 对 opencode 的优化，设计一个方案对 openclaw 进行相应的优化，并在当前路径下生成一个项目方案文档。

### 预期 Decision Result

- `intent = design_proposal`
- `complexity = medium` 或 `large`
- `workflow = design-proposal`
- `requirePlan = true`
- `requireContextScan = true`
- `requireVerification = true`

### 预期 Gate 行为

- Entry Gate：要求计划
- Edit Gate：要求上下文扫描后再执行
- Verify Gate：检查是否具备方案边界、优先级、风险
- Exit Gate：检查 summary 是否完整

### 预期 Workflow 行为

- 完成对目标系统和参考系统的扫描
- 输出差异识别
- 输出结构化方案
- 输出 MVP/路线图/风险

### 预期 Summary

必须包含：

- 已完成的分析工作
- 方案定位
- 模块建议
- 风险与边界
- 下一步建议

### 通过标准

- 输出明显是“方案提案”，不是泛泛答复
- 有结构化内容，不只是段落随笔
- 明确体现设计型 workflow 的特征

### 失败标准

- 被错误路由到 `feature-implementation` 或 `bug-fix`
- 无计划痕迹
- 无结构化提案

---

## 7.2 场景 B：功能实现请求（标准成功路径）

### 目标

验证系统能正确进入 `feature-implementation`，并输出实现导向结果。

### 输入示例

> 请为当前项目补充一份 MVP implementation plan，细化到目录、接口、文件和测试任务级别。

### 预期 Decision Result

- `intent = feature_implementation`
- `workflow = feature-implementation`
- `requirePlan = true`
- `requireContextScan = true`
- `requireVerification = true`

### 预期 Gate 行为

- Entry Gate：非琐碎任务，必须计划
- Edit Gate：确认项目上下文已就绪
- Verify Gate：要求说明验证方法或未验证项
- Exit Gate：要求统一 handoff 输出

### 预期 Workflow 行为

- 输出目标和范围
- 输出实施步骤
- 输出文件/接口/测试拆分
- 输出验证与下一步建议

### 预期 Summary

必须包含：

- 已完成内容
- 范围
- 验证说明
- 风险与假设
- 下一步建议

### 通过标准

- 输出明显面向“交付或实施”，而不是方案空谈
- 结构能支撑后续编码
- summary 结构统一

### 失败标准

- 结果停留在概念建议，没有实施颗粒度
- workflow 特征与 design-proposal 混淆

---

## 7.3 场景 C：bug 修复请求（标准成功路径）

### 目标

验证系统能正确进入 `bug-fix`，并输出 root-cause-first 的分析结果。

### 输入示例

> 当前插件在加载配置时会偶发失败，请帮我定位根因并给出修复方案。

### 预期 Decision Result

- `intent = bug_fix`
- `workflow = bug-fix`
- `requirePlan = true`（若为中等复杂任务）
- `requireContextScan = true`
- `requireVerification = true`

### 预期 Gate 行为

- Entry Gate：对于非简单问题，要求计划
- Edit Gate：确保扫描相关配置与规则
- Verify Gate：要求给出验证建议
- Exit Gate：要求输出症状/根因/修复/风险

### 预期 Workflow 行为

- 明确症状
- 提出根因或根因假设
- 给出修复方案
- 给出验证建议

### 预期 Summary

必须包含：

- issue
- rootCause
- fix
- verification
- risks
- nextSteps

### 通过标准

- 明显体现 bug-fix 特征
- 不只是“可能是这个”式泛答
- 有 root-cause-first 结构

### 失败标准

- 路由成普通 implementation
- 没有根因视角
- 没有验证建议

---

## 7.4 场景 D：信息不足的设计任务（合理阻塞路径）

### 目标

验证在信息不足时，系统能输出高质量阻塞结果，而不是胡乱继续。

### 输入示例

> 请帮我设计一个适合当前项目的升级方案。

### 特征

- 目标模糊
- 约束不足
- 参考对象不足

### 预期行为

- 可被路由到 `design-proposal`
- 但进入 `blocked` 或 `partial`
- 明确说明缺失信息
- 给出建议补充项

### 通过标准

- 没有装作已经完全理解
- 输出清晰的阻塞原因
- 仍保持结构化 summary

### 失败标准

- 用大量空泛内容掩盖信息缺失
- 不指出缺少哪些输入

---

## 7.5 场景 E：需求边界不清的实现任务（合理阻塞路径）

### 目标

验证 feature workflow 在需求模糊时不会盲目进入 execute。

### 输入示例

> 帮我把这个系统优化一下。

### 预期行为

- Decision 可初步倾向 `feature-implementation` 或 `design-proposal`
- Entry Gate 或 plan 阶段应识别边界不清
- 输出需要澄清的范围问题
- 状态可为 `blocked` 或 `partial`

### 通过标准

- 不会直接生成不受控的大而全计划
- 能明确告诉用户需要补充哪些信息

### 失败标准

- 直接进入执行口吻
- 没有澄清、没有边界控制

---

## 7.6 场景 F：无法复现的 bug 报告（合理降级路径）

### 目标

验证 bug-fix workflow 在证据不足时能形成合理部分结果。

### 输入示例

> 系统有 bug，帮我修一下。

### 预期行为

- 路由到 `bug-fix`
- intake/scan 后识别证据不足
- 输出最小补充材料要求
- 状态为 `blocked` 或 `partial`

### 通过标准

- 不盲目给出假修复
- 清晰列出所需日志/复现步骤/报错信息

### 失败标准

- 直接假设根因
- 给出无依据的修复结论

---

## 7.7 场景 G：显式命令优先（命令覆盖测试）

### 目标

验证显式命令可以覆盖普通文本语义。

### 输入示例

- 命令：`/design`
- 文本：`请帮我实现这个功能`

### 预期行为

- 明确进入 `design-proposal`
- decision reasons 中体现显式命令优先

### 通过标准

- command override 生效

### 失败标准

- 仍按文本语义进入 `feature-implementation`

---

## 7.8 场景 H：上下文扫描命令（上下文能力单独验证）

### 目标

验证 `/context-scan` 能独立输出结构化上下文结果。

### 输入示例

- 命令：`/context-scan`

### 预期行为

- 输出 invariant rules
- 输出 project summary
- 输出 relevant docs

### 通过标准

- 输出结构化，不是散乱文本
- 至少识别关键规则文件和项目摘要

### 失败标准

- 只输出文件列表，没有摘要
- 无法识别基础项目信息

---

## 8. Gate 验收专项检查

除了 workflow 场景外，还应单独检查 Gate 行为是否符合预期。

## 8.1 Entry Gate 验收

### 必须验证

- 中大任务要求计划
- 小任务允许简化
- 显式命令可影响行为

### Fail 条件

- 中大任务无计划要求
- Gate 形同虚设

## 8.2 Edit Gate 验收

### 必须验证

- 在执行前要求上下文存在
- 缺少上下文时阻止盲目继续

### Fail 条件

- 未做扫描就进入执行

## 8.3 Verify Gate 验收

### 必须验证

- 输出验证建议或未验证说明
- 不允许静默跳过验证语义

### Fail 条件

- 结果自称完成却没有任何验证信息

## 8.4 Exit Gate 验收

### 必须验证

- summary 结构完整
- 风险和下一步建议存在

### Fail 条件

- 没有统一 handoff 输出

---

## 9. Summary 验收专项检查

所有 workflow 的最终输出都应经过 summary 专项验收。

## 9.1 通用必填项

- 已完成内容
- 风险或假设
- 下一步建议

## 9.2 按 workflow 的关键字段

### `design-proposal`

- 方案定位
- 模块/路线图

### `feature-implementation`

- 范围
- 验证说明

### `bug-fix`

- 症状
- 根因
- 修复/修复方案

## 9.3 Fail 条件

- summary 缺关键字段
- workflow 之间输出结构混乱
- 没有体现任务类型差异

---

## 10. 验收执行方式建议

## 10.1 推荐执行顺序

1. 先跑核心成功路径场景：A/B/C
2. 再跑合理阻塞/降级场景：D/E/F
3. 再跑命令覆盖与独立能力场景：G/H
4. 最后做 Gate 专项检查和 summary 专项检查

## 10.2 推荐输出记录模板

每个场景记录：

- 场景编号
- 输入
- Decision Result
- Context Snapshot 摘要
- Gate 记录
- Workflow 状态
- Summary 输出
- 结论：Pass / Partial / Fail
- 备注

---

## 11. Phase 1 最终验收门槛

只有满足以下条件，Phase 1 才可视为通过：

### 核心场景通过

- 场景 A Pass
- 场景 B Pass
- 场景 C Pass

### 降级场景合理

- 场景 D 至少 Partial
- 场景 E 至少 Partial
- 场景 F 至少 Partial

### 命令与上下文专项通过

- 场景 G Pass
- 场景 H Pass

### Gate 与 Summary 专项无致命缺陷

- Entry/Edit/Verify/Exit Gate 无关键失效
- Summary 输出结构统一且完整

---

## 12. 何时判定 MVP 未成立

即使部分模块已完成，只要出现以下任一情况，就应判定 MVP 尚未成立：

1. 三个主 workflow 中任意一个无法稳定输出结构化结果
2. 系统无法稳定进行任务路由
3. Guardrails 只存在于实现中，但对系统行为没有影响
4. summary 输出不统一，无法作为稳定交付层
5. 系统在信息不足时倾向胡乱继续，而不是合理阻塞/降级

---

## 13. 验收结论模板

建议最终使用统一结论模板：

### 结论字段

- `overallStatus`: `pass | partial | fail`
- `coreWorkflows`: 各 workflow 的结果
- `guardrails`: Gate 验收结论
- `summaryQuality`: 输出层验收结论
- `blockingIssues`: 当前阻塞问题
- `recommendedNextStep`: 下一步建议

### 示例

```json
{
  "overallStatus": "partial",
  "coreWorkflows": {
    "design-proposal": "pass",
    "feature-implementation": "pass",
    "bug-fix": "partial"
  },
  "guardrails": "pass",
  "summaryQuality": "pass",
  "blockingIssues": [
    "bug-fix workflow still struggles on low-evidence reports"
  ],
  "recommendedNextStep": "improve bug-fix blocked/partial output quality"
}
```

---

## 14. 验收计划结论

Phase 1 的验收不是看“功能列表勾完了多少”，而是看：

> **`oh-my-claw` 是否已经具备一个稳定、受控、可解释的 coding workflow 主闭环。**

因此，这份验收计划最核心的判断标准是：

- 能否走对流程
- 能否在正确阶段触发约束
- 能否产出正确类型的结构化结果
- 在失败时是否仍然有工程价值

只有这些成立，MVP 才算真正成立。
