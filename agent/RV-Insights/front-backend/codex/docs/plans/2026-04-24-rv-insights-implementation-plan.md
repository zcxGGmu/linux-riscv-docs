# RV-Insights Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建一个面向 RISC-V 开源贡献的多 Agent 平台 MVP，使其能够完成人审驱动的探索、规划、开发、审核、测试闭环。

**Architecture:** 采用控制平面、执行平面、数据平面分离设计。控制平面负责工作流状态机、人审、策略和预算；执行平面通过 Runtime Adapter 调用 OpenAI Agents SDK、Claude Code/Codex 和测试 Worker；数据平面负责 Evidence Index、artifact、日志和 trace。

**Tech Stack:** 后端建议 Python/FastAPI 或 TypeScript/NestJS，PostgreSQL，Redis/队列，S3/MinIO，OpenAI Agents SDK，Claude Code/Claude Agent SDK，Codex Runtime，Docker/QEMU，React/Next.js。

---

## Phase 0：仓库与工程骨架

### Task 0.1：确定技术栈和目录结构

**Files:**
- Create: `README.md`
- Create: `docs/adr/0001-tech-stack.md`
- Create: `backend/README.md`
- Create: `frontend/README.md`
- Create: `workers/README.md`

**Step 1: 写技术栈 ADR**

记录：后端语言、前端框架、队列、数据库、对象存储、Agent SDK 接入方式。

**Step 2: 创建目录说明**

建议目录：

```text
backend/
  app/
    api/
    workflow/
    policy/
    budget/
    artifacts/
    events/
    adapters/
frontend/
workers/
  agent_worker/
  test_worker/
infra/
  docker-compose.yml
  migrations/
tests/
  unit/
  contract/
  e2e/
  fixtures/
docs/
  adr/
  plans/
```

**Step 3: 验证**

Run: `find . -maxdepth 3 -type f | sort`
Expected: 能看到新增 README 和 ADR。

### Task 0.2：定义领域模型和数据库迁移

**Files:**
- Create: `backend/app/domain/models.py`
- Create: `infra/migrations/0001_initial.sql`
- Create: `tests/unit/test_domain_models.py`

**Step 1: 写失败测试**

覆盖 workflow、stage、human_review、artifact、agent_run、test_run、review_finding。

**Step 2: 实现领域模型**

按架构文档中的数据模型实现最小字段。

**Step 3: 写数据库迁移**

创建核心表和索引。

**Step 4: 验证**

Run: `pytest tests/unit/test_domain_models.py -v`
Expected: PASS。

## Phase 1：工作流状态机与人审闸门

### Task 1.1：实现状态机

**Files:**
- Create: `backend/app/workflow/state_machine.py`
- Create: `tests/unit/test_workflow_state_machine.py`

**Step 1: 写状态转换失败测试**

测试：探索完成后必须进入等待人工审核；未审批不能进入规划；request_changes 回到当前阶段；terminate 终止。

**Step 2: 实现最小状态机**

提供：`transition(workflow, event)`。

**Step 3: 验证**

Run: `pytest tests/unit/test_workflow_state_machine.py -v`
Expected: 全部通过。

### Task 1.2：实现人工审核 API

**Files:**
- Create: `backend/app/api/workflows.py`
- Modify: `backend/app/workflow/state_machine.py`
- Create: `tests/contract/test_human_review_api.py`

**Step 1: 写 API 契约测试**

覆盖 approve、request_changes、send_back、terminate、重复审批、无权限审批。

**Step 2: 实现 API**

`POST /api/workflows/{workflow_id}/human-reviews`。

**Step 3: 验证**

Run: `pytest tests/contract/test_human_review_api.py -v`
Expected: PASS。

## Phase 2：Artifact、事件流和 Mock Runtime

### Task 2.1：实现 Artifact 服务

**Files:**
- Create: `backend/app/artifacts/service.py`
- Create: `tests/unit/test_artifact_service.py`

**Step 1: 测试 checksum 和版本保留**

上传 artifact 后计算 sha256，多次 attempt 不覆盖旧产物。

**Step 2: 实现 artifact 存储接口**

先用本地文件系统或 MinIO adapter。

**Step 3: 验证**

Run: `pytest tests/unit/test_artifact_service.py -v`
Expected: PASS。

### Task 2.2：实现统一事件流

**Files:**
- Create: `backend/app/events/schema.py`
- Create: `backend/app/events/outbox.py`
- Create: `tests/contract/test_event_schema.py`

**Step 1: 写事件 schema 测试**

事件必须包含 `event_type`、`event_version`、`workflow_id`、`seq`、`payload`、`created_at`。

**Step 2: 实现 outbox**

状态落库后写 outbox，再由事件发布器发送。

**Step 3: 验证**

Run: `pytest tests/contract/test_event_schema.py -v`
Expected: PASS。

### Task 2.3：实现 Mock Agent Runtime

**Files:**
- Create: `backend/app/adapters/base.py`
- Create: `workers/agent_worker/mock_runtime.py`
- Create: `tests/e2e/test_workflow_mock_success.py`

**Step 1: 定义 Runtime Adapter 接口**

`run`、`stream`、`cancel`、`get_artifacts`。

**Step 2: 实现 mock 场景**

支持 `EXP_OK_001`、`PLAN_OK_001`、`DEV_PATCH_OK_001`、`REV_APPROVE_001`、`TEST_PASS_001`。

**Step 3: 验证端到端成功路径**

Run: `pytest tests/e2e/test_workflow_mock_success.py -v`
Expected: 工作流最终 DONE，且每阶段都有人工审核记录。

## Phase 3：策略、预算和 Evidence Index

### Task 3.1：实现策略引擎

**Files:**
- Create: `backend/app/policy/engine.py`
- Create: `backend/app/policy/policies.yaml`
- Create: `tests/unit/test_policy_engine.py`

**Step 1: 写正反用例**

测试人审策略、工具权限、文件范围、网络策略、成本策略。

**Step 2: 实现策略决策**

输出 `allow`、`deny`、`require_human_approval`。

**Step 3: 验证**

Run: `pytest tests/unit/test_policy_engine.py -v`
Expected: PASS。

### Task 3.2：实现预算管理

**Files:**
- Create: `backend/app/budget/service.py`
- Create: `tests/unit/test_budget_service.py`

**Step 1: 测试预算熔断**

token、模型成本、QEMU 分钟、硬件分钟超限时阻止继续执行。

**Step 2: 实现预算累计和检查**

每个 agent_run 和 test_run 回写用量。

**Step 3: 验证**

Run: `pytest tests/unit/test_budget_service.py -v`
Expected: PASS。

### Task 3.3：实现 Evidence Index MVP

**Files:**
- Create: `backend/app/evidence/schema.py`
- Create: `backend/app/evidence/indexer.py`
- Create: `backend/app/evidence/search.py`
- Create: `tests/unit/test_evidence_index.py`

**Step 1: 写索引测试**

测试 canonical key 去重、content hash、freshness 状态、实体抽取字段。

**Step 2: 实现最小索引**

先支持本地 fixture、GitHub issue fixture、邮件列表 fixture。

**Step 3: 验证**

Run: `pytest tests/unit/test_evidence_index.py -v`
Expected: PASS。

## Phase 4：真实 Agent 接入

### Task 4.1：接入 OpenAI Agents SDK 探索/规划 Runtime

**Files:**
- Create: `workers/agent_worker/openai_runtime.py`
- Create: `workers/agent_worker/prompts/exploration.md`
- Create: `workers/agent_worker/prompts/planning.md`
- Create: `tests/integration/test_openai_explore_plan.py`

**Step 1: 写 adapter 契约测试**

验证输出符合统一 `AgentRunResult`。

**Step 2: 实现探索和规划 runtime**

通过工具访问 Evidence Index 和 artifact。

**Step 3: 验证**

Run: `pytest tests/integration/test_openai_explore_plan.py -v`
Expected: 真实或录制模式下通过。

### Task 4.2：接入 Claude Code 开发 Runtime

**Files:**
- Create: `workers/agent_worker/claude_code_runtime.py`
- Create: `workers/agent_worker/prompts/development.md`
- Create: `tests/integration/test_claude_development_runtime.py`

**Step 1: 写 worktree fixture 测试**

给定计划和小仓库，生成可应用 patch。

**Step 2: 实现 Claude Code adapter**

限制 worktree、文件范围、命令权限。

**Step 3: 验证**

Run: `pytest tests/integration/test_claude_development_runtime.py -v`
Expected: patch 可应用，且不超范围。

### Task 4.3：接入 Codex 审核 Runtime

**Files:**
- Create: `workers/agent_worker/codex_review_runtime.py`
- Create: `workers/agent_worker/prompts/review.md`
- Create: `tests/integration/test_codex_review_runtime.py`

**Step 1: 写 review fixture 测试**

包含有 bug diff 和正确 diff。

**Step 2: 实现 Codex review adapter**

输出 verdict、blocking findings、suggestions、confidence。

**Step 3: 验证**

Run: `pytest tests/integration/test_codex_review_runtime.py -v`
Expected: 有 bug diff 输出 request_changes，正确 diff 输出 approve。

## Phase 5：测试 Worker 与前端 MVP

### Task 5.1：实现 Docker/QEMU Test Worker

**Files:**
- Create: `workers/test_worker/runner.py`
- Create: `workers/test_worker/docker_runner.py`
- Create: `workers/test_worker/qemu_runner.py`
- Create: `tests/integration/test_test_worker.py`

**Step 1: 写测试 worker fixture**

覆盖 pass、fail、timeout、cancel。

**Step 2: 实现 runner**

输出标准 test report artifact。

**Step 3: 验证**

Run: `pytest tests/integration/test_test_worker.py -v`
Expected: PASS。

### Task 5.2：实现前端工作流详情和人审页面

**Files:**
- Create: `frontend/src/pages/workflows/[id].tsx`
- Create: `frontend/src/components/StageTimeline.tsx`
- Create: `frontend/src/components/HumanReviewPanel.tsx`
- Create: `frontend/src/components/ArtifactViewer.tsx`
- Create: `frontend/src/components/DiffViewer.tsx`
- Create: `frontend/src/components/TestReportViewer.tsx`

**Step 1: 写组件测试**

使用 mock API 验证状态展示和审批按钮。

**Step 2: 实现页面**

展示时间线、artifact、人审、diff、测试报告、事件流。

**Step 3: 验证**

Run: `npm test`
Expected: PASS。

## Phase 6：发布前验收

### Task 6.1：完整 E2E 验收

**Files:**
- Create: `tests/e2e/test_review_loop.py`
- Create: `tests/e2e/test_test_failure_debug_loop.py`
- Create: `tests/e2e/test_security_prompt_injection.py`

**Step 1: 审核迭代 E2E**

开发第一次失败，Codex request_changes，Claude Code 修复，Codex approve。

**Step 2: 测试失败调试 E2E**

测试失败，人工批准调试，修复后复测。

**Step 3: 安全 E2E**

恶意 issue 不得改变工具权限或泄露 secret。

**Step 4: 验证**

Run: `pytest tests/e2e -v`
Expected: PASS。

## 交付顺序建议

1. P0：Mock 全流程、人审状态机、artifact、事件流。
2. P1：策略、预算、Evidence Index。
3. P2：OpenAI 探索/规划。
4. P3：Claude Code 开发、Codex 审核。
5. P4：Docker/QEMU 测试。
6. P5：前端工作台和人审体验。
7. P6：上游贡献材料生成。
8. P7：真实硬件实验室。
