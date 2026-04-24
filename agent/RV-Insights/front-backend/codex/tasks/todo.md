# RV-Insights 多 Agent 开源贡献平台设计任务

## Plan

- [x] 复习项目工作流要求与可用技能。
- [x] 调研 Claude Agent SDK、OpenAI Agents SDK 公开资料与用户给定文章。
- [x] 生成中文前后端架构设计方案，包含 SDK 选型与架构图。
- [x] 生成中文测试方案，覆盖节点、人审、迭代与端到端验证。
- [x] 校验 Markdown 文档结构、中文输出与 Mermaid 图可读性。

## Enhancement Plan

- [x] 复查当前任务记录与 lessons。
- [x] 补充官方 SDK 资料依据，更新方案中的选型论证。
- [x] 深化架构文档：领域模型、Agent 契约、队列、前端交互、部署、权限、RISC-V 数据源、失败恢复。
- [x] 深化测试文档：用例矩阵、质量门禁、mock 策略、评测集、混沌测试、CI 分层和验收标准。
- [x] 再次校验文档完整性和中文输出。

## Review

- 已生成并扩展 `docs/RV-Insights-architecture-design.md`：包含总体架构、前后端边界、多 Agent 状态机、SDK 选型、人工审核、数据模型、API、事件流、安全、部署、领域模型、统一 Agent 契约、错误模型、RISC-V 数据源、探索评分、开发 worktree、审核 finding 生命周期、队列并发、幂等性、取消恢复、上游贡献输出和 MVP 分阶段交付。
- 已生成并扩展 `docs/RV-Insights-test-plan.md`：包含单元、契约、集成、端到端、RISC-V 专项、非功能、安全测试、Mock Agent、质量评测集、详细用例矩阵、前端测试、后端事务/事件一致性、RISC-V Docker/QEMU/硬件测试、混沌恢复、CI 分层、测试数据版本化和用户验收脚本。
- 已将 Mermaid 图控制为常见 flowchart/stateDiagram/sequenceDiagram，降低 Markdown 渲染兼容风险。
- 上一轮校验结果已记录：架构文档 1365 行，测试文档 1064 行，任务记录 23 行；未发现占位内容。

## Optimization Plan

- [x] 评估当前方案缺口：治理边界、成本预算、数据新鲜度、插件化、风险分级、产品体验和运营指标。
- [x] 优化架构文档：补充项目方案评估、控制平面/执行平面、策略引擎、成本预算、数据索引、插件系统、PR 准备和运营指标。
- [x] 优化测试文档：补充需求追踪矩阵、Agent 评测指标、成本回归、策略回归、数据新鲜度测试和发布演练。
- [x] 校验优化后的文档结构和占位内容。

## Optimization Review

- 当前方案可继续优化的主要方向包括：控制平面/执行平面分离、RISC-V Evidence Index、Policy-as-Code、成本预算、Runtime 能力矩阵、插件化、贡献点看板、Maintainer Profile、数据治理和运营指标。
- 已在架构文档追加 `附录 B：方案评估与优化建议`，补充成熟度评估、优化后的架构图、索引模型、策略模型、预算模型、插件接口、产品体验、上游贡献流程和优先级路线图。
- 已在测试文档追加 `附录 B：测试方案优化补充`，补充需求追踪矩阵、Agent 评测阈值、成本回归、Evidence Index 测试、Policy-as-Code 回归、证据链评分、提交准备测试、发布演练和测试优先级。

- 本轮优化后校验结果：架构文档 1802 行，测试文档 1290 行，任务记录 37 行；未发现新的未完成占位项。

## Third Optimization Plan

- [x] 新增可执行实施计划文档，按 Phase/Task 拆分 MVP 落地步骤。
- [x] 架构文档补充工程落地细节：MVP 边界、后端模块、Worker 模块、API、Prompt 模板、schema 版本、数据库索引、并发锁、运维 runbook 和关键取舍。
- [x] 测试文档补充执行落地细节：测试目录、命令分层、Replay 模式、最小 fixture、发布 checklist、缺陷 SLA、评审模板、监控告警和手工探索清单。

- 第三轮优化后校验结果：架构文档 2142 行，测试文档 1489 行，实施计划 396 行，任务记录 45 行；测试文档中的未勾选项属于发布验收 checklist 模板，不是未完成任务。

## MVP Task List Plan

- [x] 单独生成 MVP 阶段任务清单，强调契约先行、前后端并行、Mock Runtime 驱动联调。
- [x] 将任务拆分到 1-2 天可完成的细粒度节点，并标注后端、前端、联调、测试责任。
- [x] 补充每个阶段的验收标准、产出物和阻塞条件。
- [x] 校验新文档结构和中文输出。

## MVP Task List Review

- 已生成独立 MVP 阶段任务清单：`docs/plans/2026-04-24-rv-insights-mvp-task-list.md`。
- 清单采用契约先行、前后端并行、Mock Runtime 驱动联调、真实 Agent 后置的路线。
- 任务粒度拆分到 Phase 0-5，覆盖契约冻结、后端骨架、前端骨架、Mock 联调、自动化测试、MVP 打磨和最终验收脚本。
