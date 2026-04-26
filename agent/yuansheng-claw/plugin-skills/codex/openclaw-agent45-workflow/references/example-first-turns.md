# Example First Turns

Use this reference when you want a concrete example of how the first takeover response should look after the skill triggers.

Keep the same skeleton as the main skill:
- `Mode`
- `Stage`
- `Objective`
- `Inputs captured`
- `Plan`
- `Next action`

Do not copy examples mechanically. Adapt them to the current task.

## Agent4 examples

### Example A — RISC-V adaptation fix

```text
Mode: Agent4
Stage: Stage 1
Objective: 修复该 RISC-V 兼容性问题，并形成可验证的实现与验收结论。

Inputs captured
- Repo / branch / patch / PR: 当前仓库，目标分支待确认
- Target area: RISC-V 适配路径与相关工具链逻辑
- Expected output: 可提交补丁 + 自测结论
- Constraints: 需要最小改动，避免引入回归
- Available evidence: 用户已提供报错现象与相关规范线索

Plan
- [ ] 整理约束、影响面与验收点
- [ ] 定位根因并设计最小改动
- [ ] 实现修复并执行针对性自测
- [ ] Verification

Next action
- 先读取报错、规范和现有实现，明确根因候选与验收条件。
```

### Example B — Spec to plan

```text
Mode: Agent4
Stage: Stage 0
Objective: 先吃透规范和案例，再输出可执行计划与风险点。

Inputs captured
- Repo / branch / patch / PR: 暂未指定
- Target area: 待实现的 RISC-V 功能点
- Expected output: 计划清单 + 后续实现路径
- Constraints: 先规划，暂不盲目改代码
- Available evidence: 规范、案例、需求说明

Plan
- [ ] 提炼任务目标、约束和输入缺口
- [ ] 形成执行步骤与验收点
- [ ] 标记风险、依赖与待确认项
- [ ] Verification

Next action
- 先归纳规范中的硬约束，并把实现前必须确认的点列出来。
```

## Agent5 examples

### Example A — CI failure follow-up

```text
Mode: Agent5
Stage: Stage 1
Objective: 归因 CI 失败原因，修复后补齐验证并推动再次提交。

Inputs captured
- Repo / branch / patch / PR: 指向当前 PR
- Target area: CI 失败涉及的模块与提交流程
- Expected output: 修复补丁 + 回归结论 + 重新提交建议
- Constraints: 先基于日志归因，不做无证据猜测
- Available evidence: CI 日志、失败测试项、现有补丁

Plan
- [ ] 归纳失败信号并确认归因路径
- [ ] 修复问题或整理提交内容
- [ ] 复跑相关验证并记录结论
- [ ] Verification

Next action
- 先读取 CI 日志和失败测试，确认这是代码回归、环境问题还是提交流程问题。
```

### Example B — Review comments handling

```text
Mode: Agent5
Stage: Stage 1
Objective: 逐条消化 review 意见，完成补丁更新并准备再次提交。

Inputs captured
- Repo / branch / patch / PR: 当前 PR / patch series
- Target area: review 指出的实现与说明问题
- Expected output: 更新后的补丁与反馈响应
- Constraints: 每条评论都要建立“意见 → 动作 → 验证”映射
- Available evidence: review comments、当前 diff、已有测试结果

Plan
- [ ] 逐条归类 review 意见
- [ ] 确认哪些需要改代码，哪些只需补解释
- [ ] 更新补丁并补齐证据
- [ ] Verification

Next action
- 先把 review comments 归类为代码修改、说明补充、流程修正三类。
```

## Hybrid examples

### Example A — End-to-end ownership

```text
Mode: Hybrid
Stage: Stage 0
Objective: 从任务拆解、实现修复到 CI 和 review 跟进，完整接管这次贡献闭环。

Inputs captured
- Repo / branch / patch / PR: 当前仓库与待更新 PR
- Target area: RISC-V 相关改动及其提交链路
- Expected output: 可通过 review 的补丁 + 跟进结论
- Constraints: 先做计划和根因分析，再进入实现与反馈闭环
- Available evidence: 需求描述、现有 patch、CI / review 线索

Plan
- [ ] 明确约束、根因候选与验收点
- [ ] 完成技术修复和针对性验证
- [ ] 跟进 CI / review 反馈并更新提交
- [ ] Verification

Next action
- 先统一整理需求、现有补丁和外部反馈，确定应该先走 Agent4 还是直接进入 Hybrid 执行。
```

### Example B — Patch plus community follow-up

```text
Mode: Hybrid
Stage: Stage 1
Objective: 把当前 patch 修到可验证状态，并继续盯住社区反馈直到可重新提交。

Inputs captured
- Repo / branch / patch / PR: 当前 patch / mail thread
- Target area: 当前补丁涉及模块与社区反馈点
- Expected output: patch refresh + 验证结论 + 后续跟进动作
- Constraints: 需要最小改动，并保留反馈到动作的映射
- Available evidence: patch diff、review 回复、失败日志

Plan
- [ ] 先归因当前技术问题与反馈问题
- [ ] 更新补丁并完成局部验证
- [ ] 整理 resubmit 所需说明与证据
- [ ] Verification

Next action
- 先把 patch diff、失败日志和社区反馈合并成一份可执行问题清单。
```
