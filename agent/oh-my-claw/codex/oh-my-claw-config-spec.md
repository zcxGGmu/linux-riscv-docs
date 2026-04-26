# oh-my-claw Config Spec（MVP / Phase 1）

## 1. 文档目标

本文档定义 `oh-my-claw` 在 MVP / Phase 1 阶段的配置模型，重点回答以下问题：

- 哪些能力可以配置，哪些能力不应该暴露为配置
- MVP 阶段的默认行为是什么
- 用户可以在哪些层级覆盖配置
- 配置冲突时如何决策
- 哪些配置属于 Stable，哪些应保留为 Beta/Experimental

本文档的目标不是把配置做得“尽可能全”，而是：

> **用最少但足够的配置，把 `oh-my-claw` 的默认工程化行为稳定下来。**

本文档与以下文档保持一致：

- `oh-my-claw-proposal.md`
- `oh-my-claw-mvp-phases.md`
- `oh-my-claw-mvp-implementation-plan.md`
- `oh-my-claw-architecture.md`
- `oh-my-claw-workflow-specs.md`
- `oh-my-claw-acceptance-test-plan.md`

---

## 2. 配置设计原则

## 2.1 强默认值，弱自定义

`oh-my-claw` 的定位不是“高度自由的工具箱”，而是“带明确工作流哲学的增强层”。

因此，配置设计必须遵循：

- 默认值优先
- 覆盖点尽量少
- 不把所有内部实现细节都暴露给用户

## 2.2 配置只控制策略，不泄漏实现细节

配置应表达：

- 是否启用某种行为
- 某种行为的强度/阈值
- 默认 workflow / command 行为

配置不应表达：

- 内部模块类名
- 模块装配顺序
- 低层实现分支

## 2.3 安全与工程化行为优先稳定

某些行为即使提供开关，也不应鼓励关闭，例如：

- 非琐碎任务的 plan enforcement
- handoff summary 的结构完整性要求
- verification 信息的最小存在性

## 2.4 MVP 只做必要配置

MVP 不应提供过多配置，以避免：

- 文档复杂
- 测试矩阵爆炸
- 用户行为不可预测

---

## 3. 配置层级

建议采用三层配置模型：

1. **Built-in Defaults**
2. **Project-level Config**
3. **Per-command / Runtime Overrides**

MVP 阶段不建议引入更多层级。

## 3.1 Built-in Defaults

由 `oh-my-claw` 提供的默认配置，保证系统开箱即用。

特点：

- 最稳定
- 最能体现产品哲学
- 不依赖用户配置文件也可工作

## 3.2 Project-level Config

用于当前项目/仓库范围内覆盖默认行为。

适用于：

- 不同仓库的规则差异
- 某些 workflow 偏好
- 某些 Gate 强度差异

## 3.3 Per-command / Runtime Overrides

只允许覆盖极少量行为，例如：

- 强制进入某个 workflow
- 强制执行 plan 模式
- 强制触发 context scan

不建议允许 runtime 任意改动深层策略。

---

## 4. 配置优先级规则

配置冲突时，建议采用如下优先级：

1. **Explicit Command Override**
2. **Project-level Config**
3. **Built-in Defaults**

注意：

- 即使有 override，某些核心门禁仍不能被完全绕开
- override 可以影响 workflow 选择，但不能让系统跳过最基本的输出结构要求

## 4.1 不可被完全绕过的规则

以下行为即使允许弱化，也不应完全绕过：

- exit summary 结构完整性
- 关键风险/下一步建议输出
- 中大任务的 planning 语义
- verify 信息的存在性（至少要说明“未验证”）

---

## 5. 顶层配置模型

MVP 阶段建议统一挂在：

```jsonc
{
  "ohMyClaw": {
    ...
  }
}
```

建议顶层子模块如下：

- `decision`
- `context`
- `guardrails`
- `workflows`
- `commands`
- `summary`
- `logging`
- `experimental`（MVP 尽量为空或极少字段）

---

## 6. `decision` 配置

## 6.1 目标

控制 Task Decision Engine 的默认策略，而不是暴露所有规则细节。

## 6.2 建议字段

```jsonc
{
  "decision": {
    "enabled": true,
    "fallbackWorkflow": "design-proposal",
    "preferExplicitCommands": true,
    "mediumTaskStepThreshold": 3,
    "largeTaskSignalThreshold": 2
  }
}
```

## 6.3 字段说明

### `enabled`

- 类型：`boolean`
- 默认：`true`
- 说明：是否启用 Task Decision Engine

MVP 中不建议关闭，保留字段主要用于测试或极端调试。

### `fallbackWorkflow`

- 类型：`string`
- 默认：`design-proposal`
- 可选值：`design-proposal | feature-implementation | bug-fix`
- 说明：低置信度时的保守回退 workflow

建议默认回退到更保守的设计/分析路径，而不是直接执行路径。

### `preferExplicitCommands`

- 类型：`boolean`
- 默认：`true`
- 说明：显式命令是否优先于文本语义

### `mediumTaskStepThreshold`

- 类型：`number`
- 默认：`3`
- 说明：达到多少步骤信号后判为中等任务

### `largeTaskSignalThreshold`

- 类型：`number`
- 默认：`2`
- 说明：达到多少高复杂度信号后判为大型任务

## 6.4 不暴露的内容

MVP 不应把如下内容暴露为配置：

- 每条关键词规则
- 每个 intent 的内部权重
- 每一步决策的内部评分函数

---

## 7. `context` 配置

## 7.1 目标

控制项目上下文扫描与摘要强度。

## 7.2 建议字段

```jsonc
{
  "context": {
    "enabled": true,
    "scanParents": true,
    "maxRelevantDocs": 8,
    "maxRules": 12,
    "includeTasksFiles": true,
    "injectMode": "summary",
    "cacheEnabled": true
  }
}
```

## 7.3 字段说明

### `enabled`

- 类型：`boolean`
- 默认：`true`
- 说明：是否启用上下文扫描与摘要构建

MVP 不建议关闭。

### `scanParents`

- 类型：`boolean`
- 默认：`true`
- 说明：是否扫描父目录中的关键规则文件

### `maxRelevantDocs`

- 类型：`number`
- 默认：`8`
- 说明：任务相关文档最大注入数量

### `maxRules`

- 类型：`number`
- 默认：`12`
- 说明：规则摘要的最大条数

### `includeTasksFiles`

- 类型：`boolean`
- 默认：`true`
- 说明：是否纳入 `tasks/todo.md` 与 `tasks/lessons.md`

### `injectMode`

- 类型：`string`
- 默认：`summary`
- 可选值：`summary`
- 说明：MVP 只支持摘要注入，不支持全文注入模式

### `cacheEnabled`

- 类型：`boolean`
- 默认：`true`
- 说明：是否启用上下文快照缓存

## 7.4 不暴露的内容

MVP 不应暴露：

- 具体文件打分函数
- 文件逐个 include/exclude DSL
- 复杂正则级规则定制

---

## 8. `guardrails` 配置

## 8.1 目标

控制四个 Gate 的启用与强度。

## 8.2 建议字段

```jsonc
{
  "guardrails": {
    "entryGate": true,
    "editGate": true,
    "verifyGate": true,
    "exitGate": true,
    "planEnforcement": "auto",
    "requireSummary": true,
    "requireVerificationNote": true
  }
}
```

## 8.3 字段说明

### `entryGate`
- 类型：`boolean`
- 默认：`true`
- 说明：是否启用 Entry Gate

### `editGate`
- 类型：`boolean`
- 默认：`true`
- 说明：是否启用 Edit Gate

### `verifyGate`
- 类型：`boolean`
- 默认：`true`
- 说明：是否启用 Verify Gate

### `exitGate`
- 类型：`boolean`
- 默认：`true`
- 说明：是否启用 Exit Gate

### `planEnforcement`
- 类型：`string`
- 默认：`auto`
- 可选值：`off | auto | strict`
- 说明：planning 语义强度

建议：

- `off` 仅用于调试，不应用于生产默认
- `auto` 作为 MVP 默认
- `strict` 用于高度流程化团队

### `requireSummary`
- 类型：`boolean`
- 默认：`true`
- 说明：是否要求统一 handoff summary

### `requireVerificationNote`
- 类型：`boolean`
- 默认：`true`
- 说明：是否要求 summary 中至少出现验证或未验证说明

## 8.4 哪些配置不应关闭

虽然字段存在，但实际建议中：

- `exitGate` 不应关闭
- `requireSummary` 不应关闭
- `requireVerificationNote` 不应关闭

这些构成 MVP 输出层的最低标准。

---

## 9. `workflows` 配置

## 9.1 目标

定义可用 workflow、默认映射和少量 workflow 级偏好。

## 9.2 建议字段

```jsonc
{
  "workflows": {
    "defaultWorkflow": "design-proposal",
    "enabled": [
      "design-proposal",
      "feature-implementation",
      "bug-fix"
    ],
    "designProposal": {
      "requireComparisonStructure": true
    },
    "featureImplementation": {
      "preferMinimalChange": true
    },
    "bugFix": {
      "requireRootCauseSection": true
    }
  }
}
```

## 9.3 字段说明

### `defaultWorkflow`

- 类型：`string`
- 默认：`design-proposal`
- 说明：无更好判断时的默认 workflow

### `enabled`

- 类型：`string[]`
- 默认：三个 MVP workflow 全启用
- 说明：允许启用的 workflow 列表

### `designProposal.requireComparisonStructure`

- 类型：`boolean`
- 默认：`true`
- 说明：design-proposal 是否必须输出比较/差异结构

### `featureImplementation.preferMinimalChange`

- 类型：`boolean`
- 默认：`true`
- 说明：feature workflow 是否强调最小改动原则

### `bugFix.requireRootCauseSection`

- 类型：`boolean`
- 默认：`true`
- 说明：bug-fix 是否必须包含 root cause 段落

## 9.4 不暴露的内容

MVP 不应暴露：

- 自定义 workflow DSL
- 自定义步骤图编排
- 任意注入 workflow step

---

## 10. `commands` 配置

## 10.1 目标

控制命令层的基础行为和可用命令。

## 10.2 建议字段

```jsonc
{
  "commands": {
    "enablePlan": true,
    "enableDesign": true,
    "enableImplement": true,
    "enableDebug": true,
    "enableContextScan": true,
    "preferExplicitCommandRouting": true
  }
}
```

## 10.3 说明

MVP 只允许启用/禁用基础命令，不提供复杂命令别名或动态命令注册配置。

---

## 11. `summary` 配置

## 11.1 目标

保证输出层结构稳定，同时允许少量风格控制。

## 11.2 建议字段

```jsonc
{
  "summary": {
    "enabled": true,
    "includeRisks": true,
    "includeNextSteps": true,
    "includeVerification": true,
    "format": "structured-text"
  }
}
```

## 11.3 字段说明

### `enabled`
- 类型：`boolean`
- 默认：`true`

### `includeRisks`
- 类型：`boolean`
- 默认：`true`

### `includeNextSteps`
- 类型：`boolean`
- 默认：`true`

### `includeVerification`
- 类型：`boolean`
- 默认：`true`

### `format`
- 类型：`string`
- 默认：`structured-text`
- 可选值：`structured-text`

MVP 不做多种复杂输出格式。

---

## 12. `logging` 配置

## 12.1 目标

支持最小可观测性而不过度复杂化。

## 12.2 建议字段

```jsonc
{
  "logging": {
    "level": "info",
    "includeDecision": true,
    "includeContextSummary": true,
    "includeGateResults": true,
    "includeWorkflowStatus": true
  }
}
```

## 12.3 字段说明

### `level`
- 类型：`string`
- 默认：`info`
- 可选值：`debug | info | warn | error`

### `includeDecision`
- 类型：`boolean`
- 默认：`true`

### `includeContextSummary`
- 类型：`boolean`
- 默认：`true`

### `includeGateResults`
- 类型：`boolean`
- 默认：`true`

### `includeWorkflowStatus`
- 类型：`boolean`
- 默认：`true`

---

## 13. `experimental` 配置

## 13.1 目标

为 Phase 2+ 的能力预留位置，但 MVP 阶段尽量不用。

## 13.2 建议字段

```jsonc
{
  "experimental": {
    "enableSafeEditHints": false,
    "enableAdvancedRouting": false
  }
}
```

## 13.3 说明

MVP 阶段建议：

- 字段存在即可
- 默认关闭
- 不纳入核心验收标准

---

## 14. 完整配置示例

```jsonc
{
  "ohMyClaw": {
    "decision": {
      "enabled": true,
      "fallbackWorkflow": "design-proposal",
      "preferExplicitCommands": true,
      "mediumTaskStepThreshold": 3,
      "largeTaskSignalThreshold": 2
    },
    "context": {
      "enabled": true,
      "scanParents": true,
      "maxRelevantDocs": 8,
      "maxRules": 12,
      "includeTasksFiles": true,
      "injectMode": "summary",
      "cacheEnabled": true
    },
    "guardrails": {
      "entryGate": true,
      "editGate": true,
      "verifyGate": true,
      "exitGate": true,
      "planEnforcement": "auto",
      "requireSummary": true,
      "requireVerificationNote": true
    },
    "workflows": {
      "defaultWorkflow": "design-proposal",
      "enabled": [
        "design-proposal",
        "feature-implementation",
        "bug-fix"
      ],
      "designProposal": {
        "requireComparisonStructure": true
      },
      "featureImplementation": {
        "preferMinimalChange": true
      },
      "bugFix": {
        "requireRootCauseSection": true
      }
    },
    "commands": {
      "enablePlan": true,
      "enableDesign": true,
      "enableImplement": true,
      "enableDebug": true,
      "enableContextScan": true,
      "preferExplicitCommandRouting": true
    },
    "summary": {
      "enabled": true,
      "includeRisks": true,
      "includeNextSteps": true,
      "includeVerification": true,
      "format": "structured-text"
    },
    "logging": {
      "level": "info",
      "includeDecision": true,
      "includeContextSummary": true,
      "includeGateResults": true,
      "includeWorkflowStatus": true
    },
    "experimental": {
      "enableSafeEditHints": false,
      "enableAdvancedRouting": false
    }
  }
}
```

---

## 15. 稳定性等级

建议对配置字段进行稳定性分级。

## 15.1 Stable

这些字段应纳入核心保证范围：

- `decision.enabled`
- `decision.fallbackWorkflow`
- `context.enabled`
- `context.scanParents`
- `guardrails.*`
- `workflows.enabled`
- `summary.*`
- `logging.level`

## 15.2 Beta

这些字段可以保留，但后续仍可能调整：

- `mediumTaskStepThreshold`
- `largeTaskSignalThreshold`
- `maxRelevantDocs`
- `maxRules`
- workflow 局部偏好字段

## 15.3 Experimental

这些字段默认关闭，不应影响主闭环：

- `experimental.enableSafeEditHints`
- `experimental.enableAdvancedRouting`

---

## 16. 配置校验规则

## 16.1 基础校验

- 顶层必须存在 `ohMyClaw`
- 所有布尔字段必须为布尔值
- 枚举字段必须命中允许值
- 数值阈值必须为正整数

## 16.2 交叉校验

- 若 `summary.enabled = false`，应直接报错或拒绝，因为不符合 MVP 输出标准
- 若 `exitGate = false` 且 `requireSummary = true`，应报冲突
- 若 workflow `enabled` 为空，应报错
- 若 `defaultWorkflow` 不在 `enabled` 中，应报错

## 16.3 宽容策略

MVP 可以对未知字段采取宽容忽略或 warning，但不建议 silent swallow 所有异常配置。

---

## 17. 配置迁移与演进建议

## 17.1 MVP 阶段原则

- 配置结构优先稳定
- 字段名优先清晰而非短小
- 不轻易重命名

## 17.2 Phase 2+ 演进方向

后续可考虑增加：

- continuity 配置
- safe edit 配置
- doctor 配置
- advanced orchestration 配置

但必须保持：

- 顶层结构不大改
- Stable 字段尽量不破坏兼容

---

## 18. 配置规格结论

MVP / Phase 1 的配置系统最重要的不是“有很多开关”，而是：

> **用少量强默认配置，把 `oh-my-claw` 的核心工程化行为固定下来。**

因此，本配置规格的核心结论是：

- 默认行为比自定义更重要
- Gate 和 summary 相关配置优先稳定
- workflow 和 decision 只暴露最小必要字段
- 实验性字段必须默认关闭
- 配置不能破坏主闭环

只有这样，后续实现才能既稳定又不失可扩展性。
