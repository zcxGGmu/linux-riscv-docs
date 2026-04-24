# RV-Insights MVP 阶段任务清单 v2

> 基于 `rv-insights-design.md` v3.0 设计方案
> 策略：**三轨并行** — 后端骨架稳定后，前端 / Agent 实现 / 集成测试同步推进
> 参考：hermes-agent Web UI 实现
> 预计总工期：3.5 周（对比 v1 的 5 周）

---

## 优化说明（v1 → v2 变更）

| 问题 | v1 做法 | v2 改进 |
|------|---------|---------|
| 前端启动太晚 | Week 4-5 才开始 | Week 2 API 稳定后立即启动，与 Agent 并行 |
| 严格串行 8 Phase | 关键路径 5 周 | 三轨并行，压缩到 3.5 周 |
| 5 个独立 Celery worker | 过早优化 | MVP 用 1 个 worker 处理所有队列 |
| 所有 Agent 都要真实实现 | 5 个 Agent 全部接 LLM | MVP 只需 Explore 真实调用，其余 smart stub |
| ORM model 每个一个任务 | 粒度过细 | 合并为"数据库层"一个批次 |
| 事件总线 Redis pub/sub | MVP 不需要 | 砍掉，前端直接轮询 API |

---

## Sprint 0: 项目脚手架 (Day 1)

- [ ] **S0.1** 创建 `rv-insights/` 根目录，`git init`，创建 `.gitignore`（Python + Node + .env + IDE）
- [ ] **S0.2** 创建 `backend/pyproject.toml` — 依赖：fastapi, uvicorn[standard], sqlalchemy[asyncio], asyncpg, alembic, celery[redis], redis, pydantic-settings, httpx, anthropic
- [ ] **S0.3** 创建 `.env.example` — DATABASE_URL, REDIS_URL, ANTHROPIC_API_KEY, OPENAI_API_KEY
- [ ] **S0.4** 创建 `docker-compose.yml` — postgres:16-alpine + redis:7-alpine
- [ ] **S0.5** 创建 `Makefile` — up, down, migrate, test, lint, worker 目标
- [ ] **S0.6** 验证：`make up` → postgres + redis 健康运行

---

## Sprint 1: 后端核心骨架 (Day 2-5)

> 目标：API 可交互 + 状态机可测试 + stub 流水线全链路跑通

### 1A: 数据库 + ORM（一个批次完成）

- [ ] **S1.1** 创建 `app/config.py` — Pydantic BaseSettings，读取所有环境变量
- [ ] **S1.2** 创建 `app/database.py` — async engine + sessionmaker + `get_db` 依赖
- [ ] **S1.3** 创建 `app/models/` — base.py (DeclarativeBase + UUID/Timestamp mixins) + task.py + stage_output.py + human_review.py + audit_record.py，一次性完成 4 个 model
- [ ] **S1.4** 初始化 Alembic + 生成 `001_initial_schema.py` 迁移（4 张表 + 索引 + updated_at 触发器）
- [ ] **S1.5** 验证：`make migrate` 成功，`psql` 确认表结构

### 1B: 状态机

- [ ] **S1.6** 创建 `app/orchestration/state_machine.py` — TaskStage 枚举（11 个状态）+ TRANSITIONS 字典 + `transition(task, event)` 方法 + 守卫逻辑
- [ ] **S1.7** 编写 `tests/test_state_machine.py` — 参数化测试：所有合法转换 + 非法转换 + iteration 守卫边界
- [ ] **S1.8** 验证：`make test` 全部通过

### 1C: Schemas + Auth + API 骨架

- [ ] **S1.9** 创建 `app/schemas/` — task.py + review.py + output.py + status.py，一次性完成所有 Pydantic 模型
- [ ] **S1.10** 创建 `app/api/deps.py` — `verify_session_token` 依赖（X-RV-Session-Token header 校验）
- [ ] **S1.11** 创建 `app/main.py` — FastAPI app + startup 生成 session_token + CORS localhost + 挂载 v1 router
- [ ] **S1.12** 验证：`uvicorn` 启动，/docs Swagger UI 可访问

### 1D: Task CRUD + 审核 API

- [ ] **S1.13** 实现 `POST /api/v1/tasks` — 创建 Task (stage=EXPLORING)
- [ ] **S1.14** 实现 `GET /api/v1/tasks` — 分页 + ?stage=&status= 过滤
- [ ] **S1.15** 实现 `GET /api/v1/tasks/{id}` — TaskDetailResponse (含 latest_outputs + pending_review)
- [ ] **S1.16** 实现 `GET /api/v1/tasks/{id}/outputs` + `GET /api/v1/tasks/{id}/outputs/{stage}`
- [ ] **S1.17** 实现 `GET /api/v1/tasks/{id}/review` + `POST /api/v1/tasks/{id}/review` — approve 触发下一阶段，reject 触发回退
- [ ] **S1.18** 实现 `GET /api/v1/status` — 仪表盘聚合统计
- [ ] **S1.19** 编写 `tests/test_api_tasks.py` + `tests/test_api_reviews.py` — 集成测试覆盖所有端点
- [ ] **S1.20** 验证：所有 API 测试通过

### 1E: Celery + Stub 全链路

- [ ] **S1.21** 创建 `celery_app.py` — Celery 实例 (broker=redis)
- [ ] **S1.22** 创建 `tasks/base.py` — AgentTask 基类 (autoretry + backoff)
- [ ] **S1.23** 创建 5 个 stub tasks — explore/plan/develop/review/test_tasks.py，每个 stub 存储 mock StageOutput + 创建 HumanReview(pending) + transition
- [ ] **S1.24** docker-compose.yml 添加 1 个 worker 服务：`celery -A celery_app worker -Q explore,plan,develop,review,test --concurrency=2`
- [ ] **S1.25** 编写 `tests/test_pipeline_e2e.py` — Celery eager mode，验证 EXPLORING → ... → COMPLETED 全链路
- [ ] **S1.26** 验证：`POST /tasks` → stub explore → approve → stub plan → ... → COMPLETED

**Sprint 1 里程碑：stub 流水线全链路跑通，所有 API 可通过 Swagger UI 交互**

---

## Sprint 2: 三轨并行 (Week 2-3)

> API 契约已稳定，三条轨道同时推进

### Track A: 前端 (与 Track B/C 并行)

#### A1: 脚手架 + API 客户端

- [ ] **A1.1** `npm create vite@latest frontend -- --template react-ts`
- [ ] **A1.2** 安装依赖：react-router-dom, tailwindcss, @tailwindcss/vite, lucide-react, clsx, tailwind-merge
- [ ] **A1.3** 配置 `vite.config.ts` — TailwindCSS 插件 + alias "@" + proxy "/api" → localhost:8000
- [ ] **A1.4** 创建 `src/lib/utils.ts` — `cn()` = clsx + twMerge
- [ ] **A1.5** 创建 `src/lib/api.ts` — fetchJSON + session token 注入 + api 对象 (getStatus, getTasks, getTask, createTask, getTaskOutputs, getTaskReview, submitReview)
- [ ] **A1.6** 创建 `src/hooks/usePolling.ts` — setInterval 轮询 hook (interval + enabled 参数)
- [ ] **A1.7** 验证：`npm run dev` 启动，proxy 到后端 API 正常

#### A2: SPA Shell + Dashboard

- [ ] **A2.1** 创建 `src/App.tsx` — BrowserRouter + 固定 header + NavLink tabs (Dashboard / Pipeline) + 404 fallback
- [ ] **A2.2** 创建 `src/components/StatusBadge.tsx` — stage/status 颜色徽章
- [ ] **A2.3** 创建 `src/pages/DashboardPage.tsx` — 统计卡片 (usePolling → getStatus) + 任务列表 (usePolling → getTasks) + stage 过滤器
- [ ] **A2.4** 创建 `src/components/TaskCard.tsx` — 任务卡片，点击跳转 /tasks/:id
- [ ] **A2.5** 验证：Dashboard 显示 stub 任务列表，轮询自动刷新

#### A3: Task 详情 + 审核

- [ ] **A3.1** 创建 `src/components/PipelineProgress.tsx` — 5 阶段水平步进器 (Explore→Plan→Develop→Review→Test)，当前高亮 + 已完成打勾
- [ ] **A3.2** 创建 `src/components/OutputViewer.tsx` — JSON 格式化 / diff 展示 / markdown 渲染（根据 stage 类型切换）
- [ ] **A3.3** 创建 `src/components/ReviewForm.tsx` — approve/reject 按钮 + comment textarea + loading 状态
- [ ] **A3.4** 创建 `src/pages/TaskDetailPage.tsx` — 任务元信息 + PipelineProgress + OutputViewer + ReviewForm (仅 awaiting_review 时显示)，usePolling 5s 刷新
- [ ] **A3.5** 创建 `src/pages/PipelinePage.tsx` — 所有进行中任务的流水线视图，每行：标题 + 进度条 + 状态 + 跳转
- [ ] **A3.6** 验证：浏览器中可创建任务、查看详情、提交审核，stub 流水线全程可视化

#### A4: 前后端集成

- [ ] **A4.1** FastAPI main.py 添加 StaticFiles mount + session token 注入 index.html
- [ ] **A4.2** `vite build --outDir ../backend/static`
- [ ] **A4.3** docker-compose.yml 添加 frontend multi-stage build
- [ ] **A4.4** 验证：`docker compose up` → http://localhost:8000 → Dashboard 正常

---

### Track B: Explore Agent 真实实现 (与 Track A/C 并行)

> MVP 核心价值验证：真实 LLM 能否从邮件列表中识别贡献机会

- [ ] **B1** 创建 `app/agents/base.py` — BaseAgent ABC: `async run(task_id)`, `store_output()`, `_parse_structured_output(raw, schema)` (Pydantic 校验 + 重试)
- [ ] **B2** 创建 `app/mcp/maillist_server.py` — HTTP GET lore.kernel.org/linux-riscv/ Atom feed，`search_threads(query, limit)` 工具，httpx 缓存 (TTL 30min)
- [ ] **B3** 编写 `tests/test_mcp_maillist.py` — mock HTTP 响应，验证 Atom XML 解析
- [ ] **B4** 创建 `app/agents/explore/scanner.py` — ExploreAgent: Claude SDK anthropic.messages.create() + tool_use 调用 search_threads
- [ ] **B5** 定义 system prompt：引导 Claude 识别 RISC-V 贡献机会，输出 ContributionPoint[] (title, category, description, evidence, feasibility_score, risk_level, estimated_effort)
- [ ] **B6** 替换 explore_tasks.py stub 为真实 ExploreAgent
- [ ] **B7** 编写 `tests/test_explore_agent.py` — mock anthropic API，验证输出结构 + 错误重试
- [ ] **B8** 手动验证：真实 API key，POST /tasks → explore 返回真实贡献机会列表

---

### Track C: Smart Stub 升级 (与 Track A/B 并行)

> 其余 4 个 Agent 暂不接真实 LLM，但 stub 输出要足够真实以验证全链路

- [ ] **C1** 升级 plan stub — 输出真实结构的 DevelopmentPlan (implementation_steps, affected_files, acceptance_criteria)，数据来自预定义模板
- [ ] **C2** 升级 develop stub — 输出真实结构的 PatchSet (含一个简单的 .c 文件 diff + commit message)
- [ ] **C3** 升级 review stub — 模拟审核逻辑：第 1 轮 reject (附 2 个 issues)，第 2 轮 approve，验证迭代循环
- [ ] **C4** 升级 test stub — 输出 TestReport (checkpatch pass, build pass)
- [ ] **C5** 实现 dev-review 迭代循环 — review reject 时 iteration++ → dispatch develop(fix_request) → 最多 3 轮 → 超限升级人工
- [ ] **C6** 编写 `tests/test_dev_review_loop.py` — 验证迭代计数 + 超限升级
- [ ] **C7** 验证：smart stub 全链路 EXPLORING → COMPLETED，含 1 轮 dev-review 迭代

---

## Sprint 3: 集成 + 收尾 (Week 3.5)

- [ ] **S3.1** 全流水线浏览器测试：创建任务 → explore (真实 LLM) → approve → plan (stub) → approve → develop (stub) → review (stub, 含迭代) → approve → test (stub) → approve → COMPLETED
- [ ] **S3.2** 验证轮询更新：状态变更后 Dashboard + TaskDetail 自动刷新
- [ ] **S3.3** 错误场景测试：LLM 超时重试、非法 JSON 重试、网络中断 Celery 重试
- [ ] **S3.4** 补充测试覆盖率至 ≥ 80%
- [ ] **S3.5** 编写 README.md — 项目简介 + 快速启动 (docker compose up) + 架构概览
- [ ] **S3.6** 代码清理 — 移除 debug 输出、统一错误格式、检查 .env.example
- [ ] **S3.7** 最终验证：全新环境 `git clone` → `make up` → `make migrate` → 浏览器 → 创建任务 → 全流程跑通

---

## 里程碑总结

| 里程碑 | 时间 | 验收标准 |
|--------|------|---------|
| Sprint 0 | Day 1 | docker compose up 正常 |
| Sprint 1 | Day 2-5 | stub 全链路跑通，Swagger UI 可交互 |
| Sprint 2 Track A | Week 2-3 | 浏览器中完成完整审核流程 |
| Sprint 2 Track B | Week 2-3 | Explore Agent 真实 LLM 调用成功 |
| Sprint 2 Track C | Week 2 | smart stub 全链路含迭代循环 |
| Sprint 3 | Week 3.5 | 全新环境一键启动，全流程可用 |

---

## 并行依赖图

```
Sprint 0 (Day 1)
    │
    ▼
Sprint 1 (Day 2-5): 后端骨架 + stub 全链路
    │
    ├──────────────────┬──────────────────┐
    ▼                  ▼                  ▼
Track A (前端)    Track B (Explore)   Track C (Smart Stub)
 A1: 脚手架         B1-B3: Base+MCP     C1-C4: 升级 stub
 A2: Dashboard       B4-B6: Agent        C5-C6: 迭代循环
 A3: 详情+审核       B7-B8: 验证         C7: 验证
 A4: 集成
    │                  │                  │
    └──────────────────┴──────────────────┘
                       │
                       ▼
                Sprint 3: 集成 + 收尾
```

Track A / B / C 完全独立，可由不同开发者（或 Agent 会话）并行推进。

---

## 后续迭代（MVP 之后）

以下任务不在 MVP 范围内，但已在设计文档中规划：

1. **Plan Agent 真实实现** — Claude SDK + extended thinking
2. **Develop Agent 真实实现** — Claude SDK + WorkspaceManager (git worktree) + text_editor/bash tools
3. **Review Agent 真实实现** — OpenAI Agents SDK + Guardrails (security + style)
4. **Test Agent 真实实现** — checkpatch.pl + 可选 cross-compile
5. **codebase-mcp** — git 操作 MCP server
6. **RAG 知识库** — Qdrant + Dense/Sparse 混合检索
7. **提交后状态管理** — git send-email + 上游反馈闭环
8. **安全加固** — 容器沙箱、prompt injection 防御、RBAC
9. **可观测性** — OpenTelemetry + Prometheus + Grafana
