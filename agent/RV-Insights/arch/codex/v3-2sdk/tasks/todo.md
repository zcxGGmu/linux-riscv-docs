# RV-Insights 设计任务清单

- [x] 复习项目约束与现有 lessons 状态
- [x] 调研 Claude / OpenAI 两套 SDK 的官方资料与对比文章
- [x] 产出中文项目设计方案到 `docs/plans/2026-04-23-rv-insights-design.md`
- [x] 补充架构图、阶段流转图与人工审核关卡说明
- [x] 校对 SDK 选型依据、节点职责、迭代闭环与测试策略
- [x] 在文末补充 review 结论

## Review

- 本次方案采用“双栈分层”而非“单栈统一”，核心原因是 OpenAI Agents SDK 更适合作为带人工审批的控制平面，Claude Agent SDK 更适合作为代码与环境执行平面。
- 文档已明确六阶段工作流、两条迭代闭环、每阶段人工审核状态机、节点间 artifact 契约，以及 RISC-V 领域数据源与候选点评分逻辑。
- 当前仍属架构设计稿，尚未进入实现计划与原型验证阶段；下一步应把该设计进一步拆成实现计划、服务边界和最小可运行闭环。

## Next

- 首先阅读 `tasks/session-handoff.md`
- 然后阅读 `docs/plans/2026-04-23-rv-insights-design.md`
- 下一步目标：产出 RV-Insights 的中文实现计划，优先拆出 MVP 最小闭环
