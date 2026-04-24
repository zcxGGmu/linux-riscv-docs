# RV-Insights MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 尽快完成 `RV-Insights` 的最小可用版本，打通前后端、人审状态机、Mock Agent Runtime、artifact、事件流和基础工作流闭环。

**Architecture:** 采用“契约先行、前后端并行、Mock 驱动联调、真实 Agent 后置”的 MVP 路线。后端优先实现状态机、人审、artifact、事件流和 Mock Runtime；前端基于 OpenAPI/Mock 数据同步开发工作流页面；第二阶段完成 Mock E2E 后再逐步接入真实 OpenAI、Claude Code、Codex 和测试 Worker。

**Tech Stack:** 后端建议 FastAPI 或 NestJS，PostgreSQL，Redis，MinIO/S3，SSE/WebSocket；前端建议 React/Next.js，TypeScript，Tailwind 或同类 UI 方案，Monaco/CodeMirror diff viewer；测试使用 pytest 或 vitest/playwright，Mock Runtime 作为首个 Agent runtime。

---

## 0. MVP 总目标

MVP 首要目标不是完成真实 RISC-V 自动贡献，而是证明平台主链路可用：

```text
创建任务
  -> Mock 探索输出贡献点
  -> 人工审核探索
  -> Mock 规划输出开发/测试方案
  -> 人工审核规划
  -> Mock 开发输出 diff
  -> 人工审核开发
  -> Mock 审核输出 approve/request_changes
  -> 人工审核审核结果
  -> Mock 测试输出测试报告
  -> 人工验收完成
```

MVP 必须证明：

- 前后端可以围绕稳定契约联调。
- 每个阶段完成后必须等待人工审核。
- artifact 可以保存、查询、展示。
- 事件流可以驱动前端实时更新。
- Mock Runtime 可以替代真实 Agent，支持可重复 E2E 测试。
- 后续接入真实 OpenAI / Claude Code / Codex 不需要重写前端主流程。

## 1. MVP 范围边界

### 1.1 MVP 必须包含

- Workflow 创建、查询、列表。
- Stage 状态机。
- Human Review 审批动作。
- Mock Agent Runtime。
- Artifact 保存与展示。
- SSE 或 WebSocket 事件流。
- 工作流详情页。
- 阶段时间线。
- 人工审核面板。
- Diff 展示。
- Review Finding 展示。
- 测试报告展示。
- Mock E2E 自动测试。

### 1.2 MVP 暂不包含

- 真实邮件列表爬取。
- 真实 RISC-V Evidence Index。
- 真实 OpenAI / Claude / Codex Agent。
- 真实 Docker/QEMU 测试执行。
- 真实硬件测试。
- 自动提交 PR 或邮件。
- 多租户计费。
- 复杂 RBAC。

### 1.3 MVP 完成定义

满足以下条件即认为 MVP 完成：

- 用户可以在前端创建工作流。
- 后端能自动调度 Mock 阶段。
- 每个阶段结束后前端显示“等待人工审核”。
- 用户点击批准后进入下一阶段。
- 用户点击要求修改后回到当前阶段并生成新 attempt。
- 开发阶段能展示 mock diff。
- 审核阶段能展示 mock findings。
- 测试阶段能展示 mock test report。
- 工作流最终进入 `DONE`。
- 刷新页面后状态和 artifact 不丢失。
- 至少一条 Mock E2E 测试通过。

## 2. 推荐开发节奏

| 周期 | 目标 | 核心产出 |
| --- | --- | --- |
| Day 1-2 | 契约冻结 | OpenAPI、事件 schema、状态枚举、artifact schema、mock 输出样例 |
| Day 3-5 | 后端骨架 | 状态机、人审 API、artifact、Mock Runtime |
| Day 3-6 | 前端骨架 | 工作流列表、详情、时间线、人审面板 |
| Day 6-8 | Mock 联调 | 前后端跑通探索到测试闭环 |
| Day 9-10 | 打磨验收 | E2E 测试、错误处理、刷新恢复、文档 |

## 3. Phase 0：契约冻结

### Task 0.1：定义 Workflow 状态枚举

**Owner:** 后端主导，前端参与确认  
**预计耗时:** 0.5 天  
**产出:** 状态枚举文档和共享类型

**任务清单:**

- [ ] 定义 `WorkflowStatus`：`CREATED`、`RUNNING`、`WAITING_HUMAN_REVIEW`、`DONE`、`FAILED`、`TERMINATED`。
- [ ] 定义 `StageStatus`：`PENDING`、`RUNNING`、`WAITING_HUMAN_REVIEW`、`APPROVED`、`REJECTED`、`FAILED`、`SKIPPED`。
- [ ] 定义 `StageType`：`EXPLORATION`、`PLANNING`、`DEVELOPMENT`、`REVIEW`、`TESTING`。
- [ ] 定义 `HumanReviewDecision`：`APPROVE`、`REQUEST_CHANGES`、`SEND_BACK`、`TERMINATE`。
- [ ] 定义 `ReviewVerdict`：`APPROVE`、`REQUEST_CHANGES`、`REJECT`。
- [ ] 与前端确认状态对应的 UI 文案和颜色。

**验收标准:**

- [ ] 前后端使用同一套状态命名。
- [ ] 每个状态都有明确中文展示文案。
- [ ] 不存在前端自造状态。

### Task 0.2：定义核心 API 契约

**Owner:** 后端主导，前端评审  
**预计耗时:** 0.5-1 天  
**产出:** OpenAPI 草案

**任务清单:**

- [ ] 定义 `POST /api/workflows`。
- [ ] 定义 `GET /api/workflows`。
- [ ] 定义 `GET /api/workflows/{workflow_id}`。
- [ ] 定义 `POST /api/workflows/{workflow_id}/human-reviews`。
- [ ] 定义 `GET /api/workflows/{workflow_id}/artifacts`。
- [ ] 定义 `GET /api/artifacts/{artifact_id}`。
- [ ] 定义 `GET /api/workflows/{workflow_id}/events`。
- [ ] 定义错误响应：400、403、404、409、500。
- [ ] 给每个接口写一个 JSON 示例。

**验收标准:**

- [ ] 前端能根据契约写 mock client。
- [ ] 后端能根据契约写 contract test。
- [ ] API 字段包含 `id`、`status`、`stage_type`、`created_at`、`updated_at`。

### Task 0.3：定义 Artifact schema

**Owner:** 后端主导  
**预计耗时:** 0.5 天

**任务清单:**

- [ ] 定义 `exploration_report` artifact 示例。
- [ ] 定义 `planning_report` artifact 示例。
- [ ] 定义 `development_diff` artifact 示例。
- [ ] 定义 `review_report` artifact 示例。
- [ ] 定义 `test_report` artifact 示例。
- [ ] 每个 artifact 包含 `artifact_id`、`artifact_type`、`schema_version`、`summary`、`content`、`created_at`。

**验收标准:**

- [ ] 前端能根据 `artifact_type` 选择展示组件。
- [ ] 所有 artifact 都可 JSON 序列化。
- [ ] mock artifact 样例可直接用于前端开发。

### Task 0.4：定义事件 schema

**Owner:** 后端主导，前端评审  
**预计耗时:** 0.5 天

**任务清单:**

- [ ] 定义 `workflow.created`。
- [ ] 定义 `stage.started`。
- [ ] 定义 `stage.completed`。
- [ ] 定义 `human_review.required`。
- [ ] 定义 `human_review.submitted`。
- [ ] 定义 `artifact.created`。
- [ ] 定义 `workflow.completed`。
- [ ] 定义统一字段：`event_type`、`event_version`、`workflow_id`、`stage_id`、`seq`、`payload`、`created_at`。

**验收标准:**

- [ ] `seq` 单调递增。
- [ ] 前端断线重连后可重新拉取 workflow 详情恢复状态。
- [ ] 事件 payload 不包含 SDK 原生对象。

### Task 0.5：准备 Mock 输出样例

**Owner:** 后端和前端共同  
**预计耗时:** 0.5 天

**任务清单:**

- [ ] 准备探索阶段 mock artifact。
- [ ] 准备规划阶段 mock artifact。
- [ ] 准备开发阶段 mock diff。
- [ ] 准备审核阶段 mock findings。
- [ ] 准备测试阶段 mock report。
- [ ] 准备 request_changes 场景 mock 数据。

**验收标准:**

- [ ] 前端可以脱离后端用 mock JSON 渲染所有核心页面。
- [ ] 后端 Mock Runtime 可以直接复用同一批样例。

## 4. Phase 1：后端 MVP 骨架

### Task 1.1：创建后端项目骨架

**Owner:** 后端  
**预计耗时:** 0.5 天

**任务清单:**

- [ ] 初始化后端项目。
- [ ] 添加健康检查接口 `GET /health`。
- [ ] 添加配置加载。
- [ ] 添加基础日志。
- [ ] 添加测试框架。
- [ ] 添加本地启动命令。

**验收标准:**

- [ ] 本地可以启动后端服务。
- [ ] `GET /health` 返回 200。
- [ ] 测试命令可以运行。

### Task 1.2：实现领域模型

**Owner:** 后端  
**预计耗时:** 0.5-1 天

**任务清单:**

- [ ] 实现 `Workflow` 模型。
- [ ] 实现 `WorkflowStage` 模型。
- [ ] 实现 `HumanReview` 模型。
- [ ] 实现 `Artifact` 模型。
- [ ] 实现 `AgentRun` 模型。
- [ ] 实现 `ReviewFinding` 模型。
- [ ] 实现 `TestRun` 模型。
- [ ] 添加数据库迁移。

**验收标准:**

- [ ] 数据库可以创建所有核心表。
- [ ] 模型字段覆盖 MVP API 所需数据。
- [ ] 单元测试覆盖模型序列化。

### Task 1.3：实现状态机

**Owner:** 后端  
**预计耗时:** 1 天

**任务清单:**

- [ ] 实现创建 workflow 后进入 `CREATED`。
- [ ] 实现启动探索阶段。
- [ ] 实现阶段完成后进入 `WAITING_HUMAN_REVIEW`。
- [ ] 实现 `APPROVE` 后进入下一阶段。
- [ ] 实现 `REQUEST_CHANGES` 后当前阶段 attempt +1。
- [ ] 实现 `TERMINATE` 后终止工作流。
- [ ] 阻止未审批直接进入下一阶段。
- [ ] 阻止同一 workflow 同时运行两个阶段。

**验收标准:**

- [ ] 状态机单元测试通过。
- [ ] 非法状态转换返回明确错误。
- [ ] 所有阶段完成后都等待人工审核。

### Task 1.4：实现 Workflow API

**Owner:** 后端  
**预计耗时:** 1 天

**任务清单:**

- [ ] 实现创建 workflow。
- [ ] 实现 workflow 列表。
- [ ] 实现 workflow 详情。
- [ ] 实现 workflow timeline。
- [ ] 实现取消 workflow。
- [ ] 实现 retry 当前阶段。
- [ ] 添加 API contract test。

**验收标准:**

- [ ] 前端可以创建并查询 workflow。
- [ ] API 响应符合 Phase 0 契约。
- [ ] 错误响应结构统一。

### Task 1.5：实现 Human Review API

**Owner:** 后端  
**预计耗时:** 0.5-1 天

**任务清单:**

- [ ] 实现 `POST /api/workflows/{workflow_id}/human-reviews`。
- [ ] 支持 `APPROVE`。
- [ ] 支持 `REQUEST_CHANGES`。
- [ ] 支持 `SEND_BACK` 的 MVP 简化版本，允许退回上一阶段。
- [ ] 支持 `TERMINATE`。
- [ ] 驳回和终止必须要求 comment。
- [ ] 重复审批返回 409。

**验收标准:**

- [ ] 人审动作能正确推进状态机。
- [ ] 未等待审核的阶段不能审批。
- [ ] 审批记录可查询。

### Task 1.6：实现 Artifact 服务

**Owner:** 后端  
**预计耗时:** 0.5-1 天

**任务清单:**

- [ ] 实现 artifact 元数据存储。
- [ ] 实现 artifact 内容保存，MVP 可先用数据库 JSON 或本地文件。
- [ ] 实现 artifact 列表 API。
- [ ] 实现 artifact 详情 API。
- [ ] 为 artifact 计算 checksum。
- [ ] 支持同一阶段多 attempt artifact 保留。

**验收标准:**

- [ ] 前端可以查看每个阶段 artifact。
- [ ] 旧 artifact 不会被新 attempt 覆盖。
- [ ] artifact 与 workflow/stage 关联正确。

### Task 1.7：实现事件流 MVP

**Owner:** 后端  
**预计耗时:** 0.5-1 天

**任务清单:**

- [ ] 实现事件表或内存事件 outbox。
- [ ] 状态变化时写入事件。
- [ ] artifact 创建时写入事件。
- [ ] 人审提交时写入事件。
- [ ] 提供 SSE endpoint。
- [ ] 支持前端订阅 workflow 事件。

**验收标准:**

- [ ] 前端能收到阶段状态变化。
- [ ] 刷新页面后可以通过 workflow 详情恢复状态。
- [ ] 事件结构符合契约。

### Task 1.8：实现 Mock Runtime

**Owner:** 后端  
**预计耗时:** 1 天

**任务清单:**

- [ ] 定义 `AgentRuntimeAdapter` 接口。
- [ ] 实现 `MockRuntime`。
- [ ] Mock 探索阶段生成 exploration artifact。
- [ ] Mock 规划阶段生成 planning artifact。
- [ ] Mock 开发阶段生成 diff artifact。
- [ ] Mock 审核阶段生成 review artifact。
- [ ] Mock 测试阶段生成 test report artifact。
- [ ] 支持 request_changes 场景。

**验收标准:**

- [ ] 创建 workflow 后可以自动跑探索 mock。
- [ ] 人工批准后可以继续调度下一 mock 阶段。
- [ ] 所有 mock artifact 都可被前端展示。

## 5. Phase 2：前端 MVP 骨架

### Task 2.1：创建前端项目骨架

**Owner:** 前端  
**预计耗时:** 0.5 天

**任务清单:**

- [ ] 初始化前端项目。
- [ ] 配置 TypeScript。
- [ ] 配置 UI 基础样式。
- [ ] 配置 API client。
- [ ] 配置本地开发代理。
- [ ] 添加测试框架。

**验收标准:**

- [ ] 前端本地可启动。
- [ ] 首页可访问。
- [ ] 能调用后端 `GET /health` 或 mock API。

### Task 2.2：实现 Workflow 列表页

**Owner:** 前端  
**预计耗时:** 0.5-1 天

**任务清单:**

- [ ] 展示 workflow 列表。
- [ ] 展示状态、标题、创建时间、当前阶段。
- [ ] 支持按状态筛选。
- [ ] 支持进入详情页。
- [ ] 空状态展示创建入口。

**验收标准:**

- [ ] 能看到后端返回的 workflow。
- [ ] 状态颜色和文案符合契约。

### Task 2.3：实现创建任务页

**Owner:** 前端  
**预计耗时:** 0.5-1 天

**任务清单:**

- [ ] 实现任务标题输入。
- [ ] 实现用户需求输入。
- [ ] 实现仓库 URL 输入。
- [ ] 实现数据源输入的 MVP 简化版本。
- [ ] 提交后调用 `POST /api/workflows`。
- [ ] 创建成功后跳转详情页。
- [ ] 显示创建失败错误。

**验收标准:**

- [ ] 用户可以从 UI 创建 workflow。
- [ ] 创建后进入详情页并看到探索阶段运行或等待审核。

### Task 2.4：实现 Workflow 详情页布局

**Owner:** 前端  
**预计耗时:** 1 天

**任务清单:**

- [ ] 顶部展示标题、状态、当前阶段。
- [ ] 左侧或顶部展示阶段时间线。
- [ ] 中间展示当前阶段 artifact。
- [ ] 右侧展示人工审核面板。
- [ ] 底部或 Tab 展示事件日志。
- [ ] 支持刷新后重新加载 workflow 详情。

**验收标准:**

- [ ] 详情页能展示完整 workflow 状态。
- [ ] 没有 artifact 时有清晰占位提示。

### Task 2.5：实现 Stage Timeline 组件

**Owner:** 前端  
**预计耗时:** 0.5 天

**任务清单:**

- [ ] 展示探索、规划、开发、审核、测试五个阶段。
- [ ] 每个阶段展示状态 icon。
- [ ] 展示 attempt 次数。
- [ ] 当前阶段高亮。
- [ ] 点击阶段可查看对应 artifact。

**验收标准:**

- [ ] 时间线能反映状态机变化。
- [ ] request_changes 后 attempt 数增加可见。

### Task 2.6：实现 Artifact Viewer

**Owner:** 前端  
**预计耗时:** 1 天

**任务清单:**

- [ ] 根据 `artifact_type` 路由到不同展示组件。
- [ ] 实现探索报告展示。
- [ ] 实现规划报告展示。
- [ ] 实现开发 diff 摘要展示。
- [ ] 实现审核报告展示。
- [ ] 实现测试报告展示。
- [ ] 展示 artifact 创建时间、schema version、checksum。

**验收标准:**

- [ ] 五类 MVP artifact 都能展示。
- [ ] 未知 artifact 类型有兜底 JSON 展示。

### Task 2.7：实现 Diff Viewer

**Owner:** 前端  
**预计耗时:** 0.5-1 天

**任务清单:**

- [ ] 展示 mock patch 文件列表。
- [ ] 展示新增、删除、修改行。
- [ ] 支持按文件折叠。
- [ ] 显示超范围修改警告字段，若 mock 数据存在。

**验收标准:**

- [ ] 开发阶段 diff 可读。
- [ ] 审核 findings 可关联到文件路径。

### Task 2.8：实现 Review Findings 面板

**Owner:** 前端  
**预计耗时:** 0.5 天

**任务清单:**

- [ ] 展示 verdict。
- [ ] 展示 blocking issues。
- [ ] 展示 non-blocking suggestions。
- [ ] 展示 severity。
- [ ] 展示 finding 状态。

**验收标准:**

- [ ] request_changes 场景中，用户能清晰看到需要修复的问题。

### Task 2.9：实现 Human Review Panel

**Owner:** 前端  
**预计耗时:** 1 天

**任务清单:**

- [ ] 判断当前阶段是否等待人工审核。
- [ ] 显示 approve 按钮。
- [ ] 显示 request_changes 按钮。
- [ ] 显示 terminate 按钮。
- [ ] 驳回和终止时要求填写 comment。
- [ ] 提交后禁用按钮直到响应返回。
- [ ] 处理 409 重复审批错误。

**验收标准:**

- [ ] 用户可以从 UI 推进 workflow。
- [ ] 非等待审核状态下按钮不可用。
- [ ] 审批后页面状态更新。

### Task 2.10：实现事件流订阅

**Owner:** 前端  
**预计耗时:** 0.5-1 天

**任务清单:**

- [ ] 连接 workflow SSE endpoint。
- [ ] 收到事件后追加到事件日志。
- [ ] 收到关键事件后刷新 workflow 详情。
- [ ] 断线后自动重连。
- [ ] 重连失败时显示提示。

**验收标准:**

- [ ] 后端阶段变化后前端无需手动刷新即可看到更新。
- [ ] 刷新页面后状态仍正确。

## 6. Phase 3：Mock 前后端联调

### Task 3.1：联调创建 workflow 到探索完成

**Owner:** 前后端共同  
**预计耗时:** 0.5 天

**任务清单:**

- [ ] 从前端创建 workflow。
- [ ] 后端创建探索 stage。
- [ ] Mock Runtime 生成探索 artifact。
- [ ] 后端进入等待人工审核。
- [ ] 前端显示探索 artifact 和审核按钮。

**验收标准:**

- [ ] 不刷新页面也能看到探索完成。
- [ ] 刷新页面后探索 artifact 仍在。

### Task 3.2：联调探索批准到规划完成

**Owner:** 前后端共同  
**预计耗时:** 0.5 天

**任务清单:**

- [ ] 前端点击 approve 探索。
- [ ] 后端记录 human review。
- [ ] 后端启动规划 stage。
- [ ] Mock Runtime 生成 planning artifact。
- [ ] 前端展示规划内容。

**验收标准:**

- [ ] 审批记录可见。
- [ ] 规划阶段不能在 approve 前启动。

### Task 3.3：联调规划批准到开发 diff

**Owner:** 前后端共同  
**预计耗时:** 0.5 天

**任务清单:**

- [ ] 前端 approve 规划。
- [ ] 后端启动开发 stage。
- [ ] Mock Runtime 生成 diff artifact。
- [ ] 前端 Diff Viewer 展示 patch。

**验收标准:**

- [ ] diff 文件路径和变更行可读。
- [ ] 开发阶段完成后等待人工审核。

### Task 3.4：联调开发批准到审核 request_changes

**Owner:** 前后端共同  
**预计耗时:** 0.5 天

**任务清单:**

- [ ] 前端 approve 开发。
- [ ] 后端启动审核 stage。
- [ ] Mock Runtime 生成 request_changes review artifact。
- [ ] 前端展示 blocking findings。
- [ ] 人工点击 request_changes。
- [ ] 后端回到开发 stage attempt +1。

**验收标准:**

- [ ] review finding 能展示 severity 和 required fix。
- [ ] request_changes 后 attempt 增加。

### Task 3.5：联调第二轮开发到审核通过

**Owner:** 前后端共同  
**预计耗时:** 0.5 天

**任务清单:**

- [ ] Mock 第二轮开发生成修复 diff。
- [ ] 人工 approve 第二轮开发。
- [ ] Mock 审核输出 approve。
- [ ] 前端展示审核通过。
- [ ] 人工 approve 进入测试。

**验收标准:**

- [ ] 第一轮和第二轮 artifact 都保留。
- [ ] 审核通过后仍需要人工批准才能测试。

### Task 3.6：联调测试报告到完成

**Owner:** 前后端共同  
**预计耗时:** 0.5 天

**任务清单:**

- [ ] 后端启动测试 stage。
- [ ] Mock Runtime 生成 test report。
- [ ] 前端展示测试命令、环境、结果。
- [ ] 人工 approve 测试结果。
- [ ] workflow 进入 DONE。

**验收标准:**

- [ ] workflow 最终状态为 DONE。
- [ ] 时间线全部阶段完成。
- [ ] 所有 artifact 可回看。

### Task 3.7：联调终止路径

**Owner:** 前后端共同  
**预计耗时:** 0.5 天

**任务清单:**

- [ ] 在等待审核阶段点击 terminate。
- [ ] 输入终止原因。
- [ ] 后端终止 workflow。
- [ ] 前端禁用后续操作。

**验收标准:**

- [ ] 终止后不会继续调度 Mock Runtime。
- [ ] 终止原因可见。

## 7. Phase 4：MVP 自动化测试

### Task 4.1：后端状态机单元测试

**Owner:** 后端  
**预计耗时:** 0.5 天

**任务清单:**

- [ ] 测试成功路径状态转换。
- [ ] 测试未审批不能进入下一阶段。
- [ ] 测试 request_changes。
- [ ] 测试 terminate。
- [ ] 测试重复审批。

**验收标准:**

- [ ] 状态机测试全部通过。

### Task 4.2：API 契约测试

**Owner:** 后端  
**预计耗时:** 0.5-1 天

**任务清单:**

- [ ] 测试创建 workflow。
- [ ] 测试查询 workflow。
- [ ] 测试提交 human review。
- [ ] 测试查询 artifact。
- [ ] 测试错误响应。

**验收标准:**

- [ ] API 响应符合契约。

### Task 4.3：前端组件测试

**Owner:** 前端  
**预计耗时:** 0.5-1 天

**任务清单:**

- [ ] 测试 Stage Timeline。
- [ ] 测试 Artifact Viewer。
- [ ] 测试 Human Review Panel。
- [ ] 测试 Diff Viewer。
- [ ] 测试 Review Findings 面板。

**验收标准:**

- [ ] 核心组件能基于 mock 数据渲染。

### Task 4.4：Mock E2E 成功路径测试

**Owner:** 全栈  
**预计耗时:** 1 天

**任务清单:**

- [ ] 自动创建 workflow。
- [ ] 等待探索完成。
- [ ] 自动 approve 探索。
- [ ] 自动 approve 规划。
- [ ] 自动 approve 开发。
- [ ] 自动 approve 审核。
- [ ] 自动 approve 测试。
- [ ] 断言最终 DONE。

**验收标准:**

- [ ] E2E 测试稳定通过。

### Task 4.5：Mock E2E 审核迭代测试

**Owner:** 全栈  
**预计耗时:** 1 天

**任务清单:**

- [ ] 第一轮审核输出 request_changes。
- [ ] 人工 request_changes 回到开发。
- [ ] 第二轮开发输出修复 diff。
- [ ] 第二轮审核 approve。
- [ ] 断言两轮 artifact 都存在。

**验收标准:**

- [ ] 迭代路径稳定通过。

## 8. Phase 5：MVP 打磨和交付

### Task 5.1：错误处理打磨

**Owner:** 前后端共同  
**预计耗时:** 0.5-1 天

**任务清单:**

- [ ] 后端统一错误结构。
- [ ] 前端展示 API 错误。
- [ ] 409 冲突给出刷新提示。
- [ ] 500 错误给出重试提示。
- [ ] SSE 断线给出连接状态。

**验收标准:**

- [ ] 常见错误不会让页面白屏或状态混乱。

### Task 5.2：刷新恢复打磨

**Owner:** 前后端共同  
**预计耗时:** 0.5 天

**任务清单:**

- [ ] 刷新工作流详情页。
- [ ] 从后端重建当前状态。
- [ ] 重新拉取 artifact。
- [ ] 重新连接事件流。
- [ ] 当前可执行动作正确恢复。

**验收标准:**

- [ ] 任何等待审核阶段刷新后都能继续审批。

### Task 5.3：MVP 演示数据准备

**Owner:** 全栈  
**预计耗时:** 0.5 天

**任务清单:**

- [ ] 准备一条成功路径 demo。
- [ ] 准备一条 request_changes demo。
- [ ] 准备一条 terminate demo。
- [ ] 为每条 demo 准备中文说明。

**验收标准:**

- [ ] 可以 5 分钟内演示平台核心价值。

### Task 5.4：MVP 文档更新

**Owner:** 全栈  
**预计耗时:** 0.5 天

**任务清单:**

- [ ] 写本地启动说明。
- [ ] 写 MVP 功能说明。
- [ ] 写 Mock Runtime 说明。
- [ ] 写已知限制。
- [ ] 写下一阶段真实 Agent 接入计划。

**验收标准:**

- [ ] 新成员可以根据 README 启动并跑通 MVP。

## 9. MVP 后真实 Agent 接入顺序

MVP 完成后，按以下顺序替换 Mock Runtime：

1. OpenAI 探索 Agent。
2. OpenAI 规划 Agent。
3. Codex 审核 Agent。
4. Claude Code 开发 Agent。
5. Docker Test Worker。
6. QEMU RISC-V Test Worker。
7. 调试 Agent。
8. Evidence Index。
9. 真实硬件池。

注意：每接入一个真实 runtime，都必须保留 Mock Runtime 用于回归测试。

## 10. MVP 风险和控制措施

| 风险 | 控制措施 |
| --- | --- |
| 前后端契约反复变化 | Day 1-2 冻结契约，后续变更走版本化。 |
| 后端做太重导致前端无法联调 | 优先 Mock Runtime 和基础状态机，不接真实 Agent。 |
| 前端缺少真实数据 | Phase 0 准备完整 mock artifact。 |
| 状态机复杂度失控 | MVP 只保留五阶段和核心动作。 |
| SSE 不稳定 | 刷新详情页作为恢复兜底。 |
| Diff 展示耗时 | MVP 先展示小型 mock diff。 |
| 测试环境复杂 | MVP 不接真实 Docker/QEMU，只展示 mock test report。 |

## 11. 每日检查清单

每天站会只问以下问题：

- 昨天是否推进了 Mock E2E 主链路？
- 当前是否有前后端契约不一致？
- 是否有状态机无法解释的状态？
- 是否有页面依赖后端未实现字段？
- 是否有后端 API 缺前端必要字段？
- 今天能否让某一段链路从 UI 跑通？

## 12. MVP 最终验收脚本

1. 打开前端首页。
2. 创建一个 `RV-Insights Mock Demo` 工作流。
3. 等待探索阶段完成。
4. 查看探索报告 artifact。
5. 点击批准探索。
6. 查看规划报告 artifact。
7. 点击批准规划。
8. 查看开发 diff。
9. 点击批准开发。
10. 查看审核 findings。
11. 如果审核要求修改，点击要求修改并进入第二轮开发。
12. 第二轮审核通过后，点击批准进入测试。
13. 查看测试报告。
14. 点击验收测试结果。
15. 确认 workflow 状态为 `DONE`。
16. 刷新页面。
17. 确认所有阶段、artifact、审批记录仍可查看。

通过以上脚本，即认为 MVP 前后端基础功能打通。
