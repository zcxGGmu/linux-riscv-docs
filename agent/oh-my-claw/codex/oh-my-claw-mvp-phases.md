# oh-my-claw MVP 阶段任务清单（含后端/前端推进策略）

## 1. 先回答核心问题：先后端，还是前后端并行？

### 结论

对于 `oh-my-claw` 这个项目，**最佳工程实践是：先以后端/插件核心链路为主完成 MVP 闭环，再在接口稳定后补前端或可视化层；不建议一开始前后端同时重度并行开发。**

更准确地说，推荐采用：

> **后端核心先行 + 极薄交互层占位 + 接口稳定后再做前端增强**

而不是：

- 纯粹“全做完后端再看前端”的瀑布式方式
- 也不是“一开始前后端完全并行”的高耦合推进方式

---

## 2. 为什么推荐“后端核心先行”

`oh-my-claw` 的 MVP 核心价值并不在 UI，而在以下能力是否成立：

1. 任务能否被正确决策和路由
2. 项目上下文能否被正确扫描和注入
3. 工程 guardrails 能否稳定执行
4. workflow 模板是否形成闭环
5. continuity / summary / verification 是否成立

这些都属于 **后端逻辑 / 插件逻辑 / workflow 引擎逻辑**，不是前端先行能解决的问题。

如果太早让前端重度参与，会出现典型问题：

- 核心接口尚未稳定，前端频繁返工
- 团队注意力从闭环能力转移到展示层
- 早期 UI 容易把未稳定能力“产品化固化”
- 会误以为“有界面 = MVP 已成立”，但实际上核心体验还不稳定

因此，MVP 阶段应该优先证明：

> **即使没有复杂 UI，`oh-my-claw` 也能作为一个可靠的 coding workflow augment 工作。**

---

## 3. 那前端完全不做吗？

也不是。

更合理的做法是：

### MVP 阶段前端策略

- **只做极薄的一层可观测/可触发能力**
- 优先 CLI / slash commands / 文本输出
- 如果必须有前端，只做只读状态展示或最小触发面板
- 不做复杂 dashboard、调度 UI、可视化编排器

也就是说：

- **核心能力开发顺序：后端优先**
- **联调策略：中后期做窄接口联调**
- **前端目标：验证可用性，不追求产品完成度**

---

## 4. 推荐开发策略

## 4.1 最佳实践建议

推荐采用以下策略：

### 阶段 1：后端/插件核心单线闭环

先把这些做通：

- Task Decision Engine
- Context Injector
- Guardrails Core
- Workflow Templates
- Exit Summary

### 阶段 2：建立稳定接口，再做轻量联调

此时再补：

- doctor 命令输出
- continuity state 查询接口
- workflow 状态查询接口
- 可选的只读前端/控制面板原型

### 阶段 3：在真实使用中验证后，再扩前端

此时再考虑：

- 可视化状态面板
- workflow 执行视图
- continuity 状态浏览器
- 配置界面

---

## 4.2 什么时候可以前后端并行？

只有在以下条件满足后，才建议前后端并行推进：

1. workflow 状态模型已经稳定
2. CLI / slash commands 输出结构已经稳定
3. continuity state 数据结构已经稳定
4. doctor 输出结构已经稳定
5. 前端仅消费这些稳定接口，不反向推动核心逻辑设计

换句话说：

> **前后端可以并行，但只能在“核心状态模型和接口契约稳定之后”并行。**

---

## 5. MVP 阶段总原则

在拆分任务前，先明确工程原则。

### 原则 1：先证明闭环，再做增强

闭环指的是：

- 能 intake 任务
- 能路由任务
- 能读取项目约束
- 能执行 workflow
- 能做最基本的验证与总结

### 原则 2：先做稳定接口，再做界面

没有稳定接口的数据面板价值很低。

### 原则 3：先命令行和文本交互，再图形化

因为 `oh-my-claw` 的本质是 workflow augment，不是 dashboard 产品。

### 原则 4：前端只服务于验证，不主导架构

MVP 阶段前端的任务是帮助观察和触发，不是反向定义系统边界。

### 原则 5：每阶段都要可运行、可演示、可验证

每个阶段结束时都要能回答：

- 现在能运行什么？
- 现在能演示什么？
- 现在怎么验证？

---

## 6. 阶段任务清单（详细拆分）

下面按“推荐真实执行顺序”拆分。

---

# Phase 0：项目落地准备

## 目标

建立 MVP 开发所需的最小项目骨架、约束和交付标准。

## 任务清单

### 0.1 项目定义与边界冻结

- [ ] 明确 MVP 目标说明，写成单独文档或 README 小节
- [ ] 明确 MVP 非目标清单
- [ ] 明确 Phase 1 / Phase 2 的分界线
- [ ] 确认 `oh-my-claw` 作为插件优先，而不是 fork
- [ ] 确认交付形态：plugin + workflows + skills（前端暂缓）

### 0.2 仓库结构初始化

- [ ] 初始化 `README.md`
- [ ] 初始化 `docs/architecture.md`
- [ ] 初始化 `docs/mvp-plan.md`
- [ ] 创建 `plugin/` 目录
- [ ] 创建 `skills/` 目录
- [ ] 创建 `workflows/` 目录
- [ ] 创建 `examples/` 目录
- [ ] 创建 `tasks/todo.md`
- [ ] 创建 `tasks/lessons.md`

### 0.3 工程基础设施

- [ ] 确定包管理器与构建工具
- [ ] 初始化 `package.json`
- [ ] 初始化 TypeScript 配置
- [ ] 配置 lint
- [ ] 配置 format
- [ ] 配置基础测试框架
- [ ] 配置开发启动脚本
- [ ] 配置最小 CI 检查（lint + typecheck + unit test）

### 0.4 开发规范冻结

- [ ] 明确代码目录边界
- [ ] 明确模块命名规范
- [ ] 明确状态对象命名规范
- [ ] 明确日志字段规范
- [ ] 明确错误码/错误类型规范
- [ ] 明确配置 schema 管理方式

### 0.5 架构冻结（MVP 级）

- [ ] 冻结 `Task Decision Engine` 的最小职责
- [ ] 冻结 `Project Context Model` 的最小职责
- [ ] 冻结 `Guarded Workflow Engine` 的最小职责
- [ ] 冻结 workflow 状态骨架
- [ ] 冻结 exit summary 输出骨架
- [ ] 冻结 slash commands MVP 范围

### Phase 0 验收标准

- [ ] 仓库能安装依赖
- [ ] 基础脚本可运行
- [ ] CI 最小链路可执行
- [ ] MVP 边界已书面冻结

---

# Phase 1：核心后端闭环（最优先）

## 目标

不依赖前端，先完成一个“可工作的 coding workflow MVP”。

## 任务清单

## 1.1 插件入口与运行骨架

- [ ] 创建插件入口文件
- [ ] 定义插件初始化流程
- [ ] 注册基础 commands
- [ ] 注册基础 hooks
- [ ] 注册配置加载入口
- [ ] 建立最小日志输出
- [ ] 建立统一错误处理入口

## 1.2 配置系统（MVP）

- [ ] 定义 `ohMyClaw` 顶层配置 schema
- [ ] 支持默认配置
- [ ] 支持项目级配置覆盖
- [ ] 支持启用/禁用核心模块
- [ ] 支持 workflow 级最小配置
- [ ] 支持 doctor 开关
- [ ] 补配置示例
- [ ] 编写配置校验测试

## 1.3 Task Decision Engine（先做）

### 数据结构
- [ ] 定义 task intake 数据结构
- [ ] 定义 decision result 数据结构
- [ ] 定义 complexity 等级枚举
- [ ] 定义 intent 枚举
- [ ] 定义 fallback 策略枚举

### 核心逻辑
- [ ] 实现显式命令优先级解析
- [ ] 实现关键词规则初版
- [ ] 实现复杂度判断规则
- [ ] 实现 workflow 推荐逻辑
- [ ] 实现 plan enforcement 决策逻辑
- [ ] 实现 verification 决策逻辑
- [ ] 实现低置信度回退策略

### 验证
- [ ] 编写典型任务分类单测
- [ ] 编写低置信度回退单测
- [ ] 编写命令覆盖普通文本输入的单测

## 1.4 Project Context Injector（紧随其后）

### Repo Scanner
- [ ] 定义扫描输入输出模型
- [ ] 实现当前目录识别
- [ ] 实现父目录扫描
- [ ] 实现关键文件发现器
- [ ] 实现构建文件发现器
- [ ] 实现测试配置发现器
- [ ] 实现任务文件发现器

### Context Model
- [ ] 定义 invariant rules 结构
- [ ] 定义 project summary 结构
- [ ] 定义 task-relevant docs 结构
- [ ] 实现摘要聚合器
- [ ] 实现相关性排序
- [ ] 实现最大注入文档数限制
- [ ] 实现缓存机制

### 注入流程
- [ ] 实现首次进入仓库注入
- [ ] 实现任务执行前注入
- [ ] 实现目录变化后刷新注入
- [ ] 实现 workflow 切换时增量注入

### 验证
- [ ] 为规则提取编写单测
- [ ] 为项目摘要编写单测
- [ ] 为任务文档排序编写单测

## 1.5 Guardrails Core（四个 Gate）

### Entry Gate
- [ ] 定义 Gate 接口
- [ ] 实现“是否必须先计划”判定
- [ ] 实现小任务豁免逻辑
- [ ] 实现用户显式覆盖策略

### Edit Gate
- [ ] 实现编辑前上下文是否充分的检查
- [ ] 实现缺少上下文时的补扫流程
- [ ] 实现是否建议 safe edit 的判定

### Verify Gate
- [ ] 定义验证要求模型
- [ ] 实现按项目类型推荐验证动作
- [ ] 实现未验证时的输出告警结构

### Exit Gate
- [ ] 定义 exit summary 模型
- [ ] 实现未完成任务状态检测
- [ ] 实现 continuity state 预留写入点
- [ ] 实现统一总结输出结构

### 验证
- [ ] 为四个 Gate 编写单测
- [ ] 为 Gate 顺序编写集成测试

## 1.6 Workflow Engine（MVP）

### Workflow Skeleton
- [ ] 定义统一 workflow 生命周期
- [ ] 定义统一 workflow state
- [ ] 定义 step 状态枚举
- [ ] 定义 workflow registry

### 首批模板
- [ ] 实现 `design-proposal` 模板
- [ ] 实现 `feature-implementation` 模板
- [ ] 实现 `bug-fix` 模板

### 模板内步骤
- [ ] 为每个模板定义 `intake`
- [ ] 为每个模板定义 `scan`
- [ ] 为每个模板定义 `plan`
- [ ] 为每个模板定义 `execute`
- [ ] 为每个模板定义 `verify`
- [ ] 为每个模板定义 `handoff`

### 验证
- [ ] 为 workflow registry 编写单测
- [ ] 为模板选择编写单测
- [ ] 为模板执行顺序编写集成测试

## 1.7 Commands / CLI / Slash Commands（MVP）

- [ ] 定义 `/plan`
- [ ] 定义 `/design`
- [ ] 定义 `/implement`
- [ ] 定义 `/debug`
- [ ] 定义 `/context-scan`
- [ ] 定义 `/doctor-coding`（可先占位）
- [ ] 实现命令参数解析
- [ ] 实现命令到 workflow 的映射
- [ ] 实现命令帮助文本

## 1.8 Exit Summary（统一交付）

- [ ] 定义 summary 数据模型
- [ ] 定义已完成项格式
- [ ] 定义修改范围格式
- [ ] 定义验证结果格式
- [ ] 定义风险与假设格式
- [ ] 定义下一步建议格式
- [ ] 将 summary 接入所有 MVP workflows

## 1.9 最小观测能力

- [ ] 定义结构化日志字段
- [ ] 记录 task intake
- [ ] 记录 decision result
- [ ] 记录 context scan 摘要
- [ ] 记录 workflow 选择结果
- [ ] 记录 gate 触发情况
- [ ] 记录最终 handoff 摘要

### Phase 1 验收标准

- [ ] 无需前端即可完整演示 3 个 workflows
- [ ] 对中等复杂任务能自动进入正确流程
- [ ] 能自动抽取项目规则并注入
- [ ] 能稳定执行 plan/verify/handoff 闭环
- [ ] 所有核心模块具备基本测试

---

# Phase 2：可靠性增强（仍以后端为主）

## 目标

在 MVP 核心闭环成立后，补齐“能稳定续做、能诊断、能减少误改”的能力。

## 任务清单

## 2.1 Continuity State

### 数据模型
- [ ] 定义 continuity state schema
- [ ] 定义 task id 生成策略
- [ ] 定义 workflow 恢复点结构
- [ ] 定义 next action 结构

### 存储与恢复
- [ ] 实现状态写入
- [ ] 实现状态读取
- [ ] 实现状态过期策略
- [ ] 实现 resume 命令
- [ ] 实现未完成任务检测
- [ ] 实现 workflow 恢复逻辑

### 验证
- [ ] 编写状态写入/读取单测
- [ ] 编写 resume 集成测试

## 2.2 Coding Doctor

### 检查模型
- [ ] 定义 check result 结构
- [ ] 定义 severity 枚举
- [ ] 定义 blocking 字段
- [ ] 定义 recommended fix order

### 检查项
- [ ] 实现项目根识别检查
- [ ] 实现构建系统检查
- [ ] 实现测试命令识别检查
- [ ] 实现插件启用检查
- [ ] 实现 workflow 可用性检查
- [ ] 实现关键文件存在性检查

### 输出
- [ ] 实现文本输出
- [ ] 实现 JSON 输出
- [ ] 实现 CLI 命令接线

### 验证
- [ ] 编写 doctor checks 单测
- [ ] 编写 doctor 命令集成测试

## 2.3 Safe Edit MVP（建议此时再做）

### Read Path
- [ ] 定义 file revision 模型
- [ ] 定义 line anchor 模型
- [ ] 实现 `hashline_read`
- [ ] 实现文件摘要输出

### Edit Path
- [ ] 定义 edit 操作模型
- [ ] 实现 `replace` 操作
- [ ] 实现 `insert_before`
- [ ] 实现 `insert_after`
- [ ] 实现 `delete`
- [ ] 实现 revision 校验
- [ ] 实现 anchor 校验
- [ ] 实现失败后重读提示

### Diff Path
- [ ] 实现 `hashline_diff`
- [ ] 实现应用结果摘要

### 验证
- [ ] 编写 stale edit 单测
- [ ] 编写冲突拒绝单测
- [ ] 编写成功编辑集成测试

## 2.4 Recovery Hooks

- [ ] 实现 edit failure recovery
- [ ] 实现 JSON/配置编辑失败恢复
- [ ] 实现 workflow 中断后恢复建议
- [ ] 实现重复失败次数限制
- [ ] 编写 recovery 相关测试

## 2.5 Reviewer / Planner 强化

- [ ] 定义 reviewer 输出结构
- [ ] 定义 planner 输出结构
- [ ] 为大任务提供 review checkpoint
- [ ] 为大任务提供 plan refinement checkpoint

### Phase 2 验收标准

- [ ] 任务中断后可以恢复
- [ ] doctor 能给出可操作建议
- [ ] safe edit 能拦截基础 stale edit 问题
- [ ] recovery 链路能降低失败中断率

---

# Phase 3：轻量联调层（前端/可视化只在此时进入）

## 目标

在核心模型和接口稳定后，引入最小前端/展示层做可观测性验证，而不是做完整产品 UI。

## 任务清单

## 3.1 先定义“前端只读范围”

- [ ] 冻结前端 MVP 只读边界
- [ ] 明确前端不反向主导核心状态模型
- [ ] 明确只展示哪些信息

## 3.2 暴露稳定查询接口

- [ ] 暴露 workflow 当前状态查询接口
- [ ] 暴露 continuity state 查询接口
- [ ] 暴露 doctor 结果查询接口
- [ ] 暴露最近 task summary 查询接口
- [ ] 暴露配置摘要查询接口

## 3.3 最小前端/面板原型（可选）

### 只读视图
- [ ] 任务列表视图
- [ ] 当前 workflow 状态视图
- [ ] 最近 summary 视图
- [ ] doctor 结果视图

### 最小触发动作
- [ ] 触发 `/design`
- [ ] 触发 `/implement`
- [ ] 触发 `/debug`
- [ ] 触发 `resume`
- [ ] 触发 `doctor`

### 交互限制
- [ ] 不实现复杂可视化编排
- [ ] 不实现配置编辑器
- [ ] 不实现拖拽 workflow 设计器

## 3.4 联调与回归

- [ ] 验证前端对状态查询结构的兼容性
- [ ] 验证前端不依赖实验字段
- [ ] 验证接口变化的回归测试

### Phase 3 验收标准

- [ ] 前端仅作为观察和触发层即可成立
- [ ] 接口不因前端引入而被迫扭曲
- [ ] 前端新增不会破坏 CLI/slash command 主路径

---

# Phase 4：增强协作与差异化（非 MVP）

## 目标

在 MVP 已成立并经过实际使用后，再引入更强差异化。

## 任务清单

- [ ] 实现 advanced orchestrator
- [ ] 实现更丰富角色系统
- [ ] 实现高级 workflow policies
- [ ] 实现 safe edit 增强模式
- [ ] 实现高级 telemetry/metrics
- [ ] 实现 beta / experimental 能力分层

---

## 7. 实际资源安排建议

如果是 **1~2 人小团队**，推荐：

### 推荐方式

- **先单线程把 Phase 1 跑通**
- 然后并行推进 `Phase 2 doctor/continuity` 与 `Phase 2 safe edit`
- 前端等到 Phase 3 再进入

### 不推荐方式

- 一人做 routing，一人做前端 dashboard，同时推进

原因：

- 此时接口和状态模型都不稳定
- 很容易造成双方都在返工

---

如果是 **3~5 人团队**，推荐：

### 阶段式并行

#### 阶段 A
- 1 人：Task Decision Engine + Guardrails
- 1 人：Context Injector + Repo Scanner
- 1 人：Workflow Engine + Commands

#### 阶段 B
- 1 人：Continuity + Doctor
- 1 人：Safe Edit MVP
- 1 人：测试/集成/文档

#### 阶段 C
- 1 人：最小前端只读面板
- 其余人继续稳定后端与回归

这才是比较稳妥的“并行开发”。

---

## 8. 推荐里程碑

## Milestone 1：无前端的可演示 MVP

要求：

- 能用命令触发 workflow
- 能输出计划
- 能扫描项目约束
- 能完成 handoff summary

## Milestone 2：可恢复、可诊断、可减少误改

要求：

- continuity 可用
- doctor 可用
- safe edit MVP 可用

## Milestone 3：有轻量可视化层

要求：

- 只读面板可看状态
- 不破坏 CLI/command 主路径

---

## 9. 最终建议

### 最推荐的开发顺序

> **先后端核心闭环，再后端可靠性，再轻量前端联调，最后才做增强型协作与可视化。**

也就是：

1. `Phase 0` 准备
2. `Phase 1` 核心后端闭环
3. `Phase 2` 可靠性增强
4. `Phase 3` 轻量前端/联调
5. `Phase 4` 差异化增强

### 为什么这是最佳实践

因为它同时满足：

- MVP 最快成立
- 核心接口先稳定
- 前端返工最少
- 架构边界更清晰
- 风险最低
- 更符合插件型/工作流型产品的成长路径

---

## 10. 一句话决策

> 对 `oh-my-claw` 而言，**MVP 阶段应以后端/插件核心闭环为绝对优先，不建议前后端一开始重度并行；应在状态模型和命令接口稳定后，再做轻量前端联调。**
