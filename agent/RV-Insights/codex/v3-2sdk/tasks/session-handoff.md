# RV-Insights 会话交接记录

> 更新时间：2026-04-23  
> 用途：重新启动 Codex 后，先阅读此文件，再继续后续设计或实现工作。

## 1. 当前完成进度

本轮已经完成：

- 输出了 `RV-Insights` 的中文项目设计方案。
- 明确了平台推荐采用“双栈分层”架构：
  - `OpenAI Agents SDK` 负责控制平面。
  - `Claude Agent SDK` 负责执行平面。
- 明确了六阶段工作流：
  - 探索
  - 规划
  - 开发
  - 审核
  - 测试
  - 调试/回归
- 明确了两条核心闭环：
  - `开发 <-> 审核`
  - `测试失败 -> 调试 -> 审核 -> 测试`
- 明确了“每阶段结束必须人工审核后才能进入下一阶段”的门控机制。
- 补充了总体架构图、阶段流转图、状态机、阶段间 artifact 契约、RISC-V 领域数据源和优先级策略。

## 2. 关键产物

优先阅读以下文件：

1. `docs/plans/2026-04-23-rv-insights-design.md`
2. `tasks/todo.md`
3. `tasks/lessons.md`
4. `tasks/session-handoff.md`

## 3. 当前核心结论

### 推荐架构

- 控制平面使用 `OpenAI Agents SDK`
- 执行平面使用 `Claude Agent SDK`
- 审核节点由 OpenAI 侧 reviewer / Codex 能力承接
- 开发、测试、调试节点由 Claude Agent SDK 承接

### 不推荐的做法

- 不建议第一版就把两套 SDK 强行抹平成统一运行时抽象
- 不建议让审核节点默认具备写权限
- 不建议在没有结构化 artifact 契约的情况下直接靠 prompt 串阶段

## 4. 当前尚未开始的工作

设计文档已完成，但以下内容还没做：

- 没有把设计稿拆成“实现计划”
- 没有创建平台代码骨架
- 没有定义后端服务接口与目录结构对应的实际文件
- 没有落地 workflow engine、approval gate、artifact schema 的代码
- 没有搭建任何测试或原型环境

## 5. 建议下一步

建议下一轮按这个顺序推进：

1. 基于设计稿再产出一份“实现计划”
2. 先做最小闭环 MVP：
   - 探索
   - 规划
   - 开发
   - 审核
   - 人工审批
3. 明确服务边界，至少拆成：
   - `services/api`
   - `services/workflow`
   - `services/openai-orchestrator`
   - `services/claude-worker`
   - `services/review-adapter`
   - `libs/contracts`
4. 先定义 artifact schema 与审批状态机，再开始写 agent 调度代码

## 6. 建议下次启动后对 Codex 的指令

可直接对 Codex 说：

```text
请先阅读 tasks/session-handoff.md、tasks/todo.md 和 docs/plans/2026-04-23-rv-insights-design.md，然后基于当前设计稿继续产出 RV-Insights 的详细实现计划（中文）。
```

如果你希望下一次直接开始搭代码，可改成：

```text
请先阅读 tasks/session-handoff.md、tasks/todo.md 和 docs/plans/2026-04-23-rv-insights-design.md，然后开始为 RV-Insights 搭建最小可运行骨架，先实现控制平面、审批状态机和 artifact schema。
```

## 7. 风险与注意事项

- 当前文档是设计方案，不是实现计划。
- 设计中提到的 OpenAI / Claude 官方能力映射，是为了支撑架构选型，不等于具体 SDK API 已完成逐项代码验证。
- 下一步进入实现前，应该再补一份任务拆解更细的计划文档。
