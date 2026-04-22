# RV-Insights 各阶段开发任务清单

> 版本：v1.0  
> 日期：2026-04-22  
> 关联设计文档：[rv-insights-design.md](./rv-insights-design.md) v2.2  
> 任务编号格式：`P{阶段}.{序号}`

---

## 任务总览

| 阶段 | 名称 | 任务数 | 预估工时 |
|------|------|:------:|:--------:|
| Phase 0 | 基础设施搭建 | 12 | 2 周 |
| Phase 1 | 单 Agent 验证 | 15 | 3 周 |
| Phase 2 | 流水线集成 | 12 | 3 周 |
| Phase 3 | 端到端验证 | 8 | 2 周 |
| Phase 4 | 生产化加固 | 10 | 2 周 |
| **合计** | | **57** | **~12 周** |

---

## 任务依赖关系总图

```
P0.1 ──▶ P0.2 ──▶ P0.5 ──▶ P0.7 ──▶ P1.1
  │        │                    │
  │        └──▶ P0.3 ──▶ P0.6  └──▶ P1.2
  │               │                   │
  └──▶ P0.4      └──▶ P0.8           └──▶ P1.3 ──▶ P1.4 ──▶ P1.5
         │              │
         └──▶ P0.9     └──▶ P0.10 ──▶ P0.11 ──▶ P0.12

P1.1 ──▶ P1.6 ──▶ P1.8 ──▶ P1.10 ──▶ P1.12
P1.2 ──▶ P1.7 ──▶ P1.9 ──▶ P1.11 ──▶ P1.13 ──▶ P1.14 ──▶ P1.15

P1.* ──▶ P2.1 ──▶ P2.2 ──▶ P2.3 ──▶ P2.4 ──▶ P2.5
                                        │
                                        └──▶ P2.6 ──▶ P2.7 ──▶ P2.8
                                                        │
                                                        └──▶ P2.9 ──▶ P2.10 ──▶ P2.11 ──▶ P2.12

P2.* ──▶ P3.1 ──▶ P3.2 ──▶ P3.3 ──▶ P3.4 ──▶ P3.5 ──▶ P3.6 ──▶ P3.7 ──▶ P3.8

P3.* ──▶ P4.1 ──▶ P4.2 ──▶ P4.3
                    │
                    └──▶ P4.4 ──▶ P4.5 ──▶ P4.6
                                    │
                                    └──▶ P4.7 ──▶ P4.8 ──▶ P4.9 ──▶ P4.10
```

---

## Phase 0：基础设施搭建（2 周）

### P0.1 Python 项目骨架初始化

- **描述**：使用 `uv` 初始化 Python 项目，配置 `pyproject.toml`（依赖声明、构建配置、linter/formatter 规则），创建 `src/rv_insights/` 包结构，配置 `ruff`、`mypy`、`pytest`。
- **涉及文件**：
  - `pyproject.toml`
  - `src/rv_insights/__init__.py`
  - `src/rv_insights/py.typed`
  - `.python-version`
  - `ruff.toml`
- **依赖**：无
- **验收标准**：
  - [ ] `uv sync` 成功安装所有依赖
  - [ ] `ruff check src/` 零警告
  - [ ] `mypy src/` 零错误
  - [ ] `pytest` 可运行（空测试套件通过）
  - [ ] Python >= 3.12
- **测试**：`pytest tests/ -v` 通过（含一个 `test_import.py` 验证包可导入）
- **预估工时**：2h

---

### P0.2 Pydantic 数据模型层

- **描述**：实现设计文档 Section 4.0 中定义的所有跨 Agent 数据契约 Pydantic 模型：`InputContext`, `ExplorationResult`, `ExecutionPlan`, `DevPlan`, `TestPlan`, `DevelopmentResult`, `ReviewFinding`, `ReviewVerdict`, `TestResult`, `TokenUsage`, `CaseStatus` 等。
- **涉及文件**：
  - `src/rv_insights/models/__init__.py`
  - `src/rv_insights/models/case.py`
  - `src/rv_insights/models/exploration.py`
  - `src/rv_insights/models/planning.py`
  - `src/rv_insights/models/development.py`
  - `src/rv_insights/models/review.py`
  - `src/rv_insights/models/testing.py`
  - `src/rv_insights/models/audit.py`
  - `src/rv_insights/models/common.py`（TokenUsage 等共享类型）
- **依赖**：P0.1
- **验收标准**：
  - [ ] 所有模型可正常实例化和 JSON 序列化/反序列化
  - [ ] 字段校验规则生效（如 `feasibility_score: float` 范围 0-1）
  - [ ] 模型间引用关系正确（如 `ExecutionPlan` 包含 `DevPlan` 和 `TestPlan`）
  - [ ] `mypy` 类型检查通过
- **测试**：
  - 单元测试：每个模型至少 3 个用例（正常值、边界值、非法值）
  - 序列化往返测试：`model == Model.model_validate_json(model.model_dump_json())`
  - 覆盖率 >= 90%
- **预估工时**：4h

---

### P0.3 全局配置模块（Pydantic Settings）

- **描述**：实现设计文档 Section 12.6 的 `RVInsightsSettings`，支持 `.env` 文件和环境变量注入，包含所有配置项（数据库、SDK 密钥、预算、Worker Pool 等）。创建 `.env.example` 模板。
- **涉及文件**：
  - `src/rv_insights/config.py`
  - `.env.example`
  - `.gitignore`（确保 `.env` 被忽略）
- **依赖**：P0.1
- **验收标准**：
  - [ ] 从 `.env` 文件加载配置成功
  - [ ] 环境变量覆盖 `.env` 文件值
  - [ ] 缺少必填项（如 `claude_api_key`）时抛出明确错误
  - [ ] `RV_` 前缀正确映射
  - [ ] `.env.example` 包含所有配置项及注释
- **测试**：
  - 单元测试：默认值、环境变量覆盖、必填项缺失、类型转换
  - 覆盖率 >= 90%
- **预估工时**：2h

---

### P0.4 Docker Compose 基础设施

- **描述**：编写 `docker-compose.yml`，包含 PostgreSQL（含 pgvector 扩展）、Redis、MinIO 三个基础服务。编写 `docker-compose.test.yml` 用于测试环境。
- **涉及文件**：
  - `docker-compose.yml`
  - `docker-compose.test.yml`
  - `Dockerfile`（应用镜像）
- **依赖**：P0.1
- **验收标准**：
  - [ ] `docker compose up -d` 三个服务全部健康
  - [ ] PostgreSQL 可连接且 pgvector 扩展已启用
  - [ ] Redis 可连接
  - [ ] MinIO 可连接且 bucket 已创建
  - [ ] 测试环境使用独立端口，不与开发环境冲突
- **测试**：
  - 集成测试：连接三个服务并执行基本操作（INSERT/GET/PUT）
  - 健康检查脚本：`scripts/healthcheck.sh`
- **预估工时**：3h

---

### P0.5 PostgreSQL Schema 与 Alembic 迁移

- **描述**：实现设计文档 Section 12.5 的核心表（`contribution_cases`, `human_reviews`, `audit_log`, `knowledge_entries`）。配置 Alembic 迁移框架，创建初始迁移。
- **涉及文件**：
  - `alembic.ini`
  - `alembic/env.py`
  - `alembic/versions/001_initial_schema.py`
  - `src/sql/init.sql`（备用手动初始化）
- **依赖**：P0.2, P0.4
- **验收标准**：
  - [ ] `alembic upgrade head` 成功创建所有表
  - [ ] `alembic downgrade base` 成功回滚
  - [ ] 表结构与设计文档 Section 12.5 一致
  - [ ] pgvector 索引正确创建
  - [ ] `alembic check` 确认 model 与 migration 同步
- **测试**：
  - 集成测试：upgrade → 插入测试数据 → 查询验证 → downgrade → 验证表已删除
  - 覆盖率 >= 80%
- **预估工时**：3h

---

### P0.6 PostgreSQL 存储层（Repository）

- **描述**：实现 `storage/postgres.py`，封装对核心表的 CRUD 操作。使用 `asyncpg` 异步驱动，实现 Repository 模式。包含：`CaseRepository`, `ReviewRepository`, `AuditRepository`, `KnowledgeRepository`。
- **涉及文件**：
  - `src/rv_insights/storage/__init__.py`
  - `src/rv_insights/storage/postgres.py`
- **依赖**：P0.3, P0.5
- **验收标准**：
  - [ ] 所有 CRUD 操作正确执行
  - [ ] 事务支持（批量操作原子性）
  - [ ] 连接池配置合理（默认 5-20）
  - [ ] SQL 注入防护（参数化查询）
  - [ ] 查询结果正确映射到 Pydantic 模型
- **测试**：
  - 集成测试（需要真实 PostgreSQL）：CRUD 全流程、事务回滚、并发写入
  - 覆盖率 >= 85%
- **预估工时**：5h

---

### P0.7 Redis 存储层

- **描述**：实现 `storage/redis_store.py`，封装 Redis 操作：会话缓存、案例状态缓存、分布式锁（用于并发控制）。
- **涉及文件**：
  - `src/rv_insights/storage/redis_store.py`
- **依赖**：P0.3, P0.4
- **验收标准**：
  - [ ] 会话数据的存取和过期正确
  - [ ] 分布式锁的获取和释放正确
  - [ ] 连接断开后自动重连
- **测试**：
  - 集成测试：存取、过期、锁竞争
  - 覆盖率 >= 80%
- **预估工时**：2h

---

### P0.8 MinIO/S3 存储层

- **描述**：实现 `storage/s3.py`，封装产物存储操作：上传 patch 文件、下载产物、列出案例产物。
- **涉及文件**：
  - `src/rv_insights/storage/s3.py`
- **依赖**：P0.3, P0.4
- **验收标准**：
  - [ ] 文件上传/下载/列出/删除正确
  - [ ] 大文件分片上传
  - [ ] bucket 不存在时自动创建
- **测试**：
  - 集成测试：上传 → 列出 → 下载 → 内容比对 → 删除
  - 覆盖率 >= 80%
- **预估工时**：2h

---

### P0.9 审计日志服务

- **描述**：实现 `AuditLogger`，记录所有 Agent 调用、人工决策、状态转换到 `audit_log` 表。支持结构化日志（JSON 格式的 `details` 字段）。
- **涉及文件**：
  - `src/rv_insights/observability/__init__.py`
  - `src/rv_insights/observability/audit.py`
- **依赖**：P0.6
- **验收标准**：
  - [ ] 所有审计事件正确写入数据库
  - [ ] 事件类型覆盖：`agent_call`, `human_review`, `state_transition`, `error`
  - [ ] 按 `case_id` 查询完整审计链
  - [ ] 异步写入不阻塞主流程
- **测试**：
  - 集成测试：写入多种事件 → 按 case_id 查询 → 验证顺序和完整性
  - 覆盖率 >= 85%
- **预估工时**：3h

---

### P0.10 Claude Agent SDK 集成验证

- **描述**：安装 `claude-code-sdk`，实现 `ClaudeAgentAdapter`（设计文档 Section 3.4），验证 SDK 基本功能：启动子进程、发送 prompt、接收响应、工具调用回调（`can_use_tool`）。
- **涉及文件**：
  - `src/rv_insights/agents/__init__.py`
  - `src/rv_insights/agents/adapter.py`（AgentAdapter 基类）
  - `src/rv_insights/agents/claude_adapter.py`
- **依赖**：P0.3
- **验收标准**：
  - [ ] 成功启动 Claude Code CLI 子进程
  - [ ] 发送简单 prompt 并收到响应
  - [ ] `can_use_tool` 回调正确拦截危险工具
  - [ ] 会话 ID 正确传递
  - [ ] 子进程超时和异常处理正确
- **测试**：
  - 集成测试（需要 Claude API Key）：简单问答、工具回调验证
  - 单元测试：Mock SDK 的 adapter 接口测试
  - 覆盖率 >= 80%
- **预估工时**：4h

---

### P0.11 OpenAI Agents SDK 集成验证

- **描述**：安装 `openai-agents`，实现 `OpenAIAgentAdapter`（设计文档 Section 3.4），验证 SDK 基本功能：创建 Agent、运行 Runner、Handoff、Guardrails、Tracing。
- **涉及文件**：
  - `src/rv_insights/agents/openai_adapter.py`
- **依赖**：P0.3, P0.10（共享 adapter 基类）
- **验收标准**：
  - [ ] 成功创建 Agent 并运行
  - [ ] Handoff 在子 Agent 间正确传递
  - [ ] Guardrails 正确拦截不合规输出
  - [ ] Tracing 事件正确记录
  - [ ] 异常处理和重试正确
- **测试**：
  - 集成测试（需要 OpenAI API Key）：简单 Agent 运行、Handoff 验证
  - 单元测试：Mock SDK 的 adapter 接口测试
  - 覆盖率 >= 80%
- **预估工时**：4h

---

### P0.12 MCP Server 基础框架

- **描述**：实现 `MCPServerBase` 基类（设计文档 Section 7），定义 MCP Server 的标准接口、注册机制、健康检查。创建一个 `echo` 示例 Server 验证框架可用。
- **涉及文件**：
  - `src/rv_insights/mcp_servers/__init__.py`
  - `src/rv_insights/mcp_servers/base.py`
  - `src/rv_insights/mcp_servers/echo.py`（示例）
- **依赖**：P0.10, P0.11
- **验收标准**：
  - [ ] MCP Server 可启动并注册工具
  - [ ] Claude Agent SDK 可调用 MCP Server 工具
  - [ ] 健康检查端点正常
  - [ ] 工具调用的输入/输出 schema 正确
- **预估工时**：4h

---

## Phase 1：单 Agent 验证（3 周）

### P1.1 探索 Agent — 邮件列表扫描子 Agent

- **描述**：实现 `mail_scanner` 子 Agent（OpenAI Agents SDK），负责从 RISC-V 邮件列表（lore.kernel.org）抓取和分析邮件，识别潜在贡献机会。包含 `@function_tool` 定义和输入 Guardrail。
- **涉及文件**：
  - `src/rv_insights/agents/explorer/__init__.py`
  - `src/rv_insights/agents/explorer/mail_scanner.py`
  - `src/rv_insights/agents/explorer/tools.py`
  - `src/rv_insights/agents/explorer/guardrails.py`
- **依赖**：P0.2, P0.11
- **验收标准**：
  - [ ] 成功从 lore.kernel.org 抓取指定日期范围的邮件
  - [ ] 正确识别 bug 报告、feature request、RFC 等类型
  - [ ] 输入 Guardrail 拦截非 RISC-V 相关内容
  - [ ] 输出符合 `ExplorationResult` 模型
- **测试**：
  - 单元测试：Mock HTTP 响应，验证邮件解析逻辑
  - 集成测试：真实 API 调用（限制 3 封邮件）
  - Guardrail 测试：注入非 RISC-V 内容验证拦截
  - 覆盖率 >= 80%
- **预估工时**：5h

---

### P1.2 探索 Agent — 代码分析子 Agent

- **描述**：实现 `code_analyzer` 子 Agent（OpenAI Agents SDK），负责分析目标仓库代码，识别代码质量问题、缺失测试、TODO/FIXME 等贡献机会。
- **涉及文件**：
  - `src/rv_insights/agents/explorer/code_analyzer.py`
- **依赖**：P0.2, P0.11
- **验收标准**：
  - [ ] 正确克隆/拉取目标仓库
  - [ ] 识别 `arch/riscv/` 目录下的代码问题
  - [ ] 输出包含 `affected_files` 和 `evidence` 字段
  - [ ] 输出符合 `ExplorationResult` 模型
- **测试**：
  - 单元测试：Mock git 操作，验证分析逻辑
  - 集成测试：对小型测试仓库运行分析
  - 覆盖率 >= 80%
- **预估工时**：4h

---

### P1.3 探索 Agent — 可行性评估子 Agent

- **描述**：实现 `feasibility_checker` 子 Agent（OpenAI Agents SDK），对前两个子 Agent 的发现进行可行性评估，输出 `feasibility_score` 和风险等级。
- **涉及文件**：
  - `src/rv_insights/agents/explorer/feasibility_checker.py`
- **依赖**：P1.1, P1.2
- **验收标准**：
  - [ ] 综合邮件和代码分析结果给出评分
  - [ ] `feasibility_score` 在 0-1 范围内
  - [ ] `risk_level` 为 "low"/"medium"/"high" 之一
  - [ ] 高风险项附带具体原因说明
- **测试**：
  - 单元测试：不同输入组合的评分验证
  - 覆盖率 >= 85%
- **预估工时**：3h

---

### P1.4 探索 Agent — 主 Agent 编排与 Handoff

- **描述**：实现探索 Agent 主入口，使用 OpenAI Agents SDK 的 `handoff()` 机制编排三个子 Agent（mail_scanner → code_analyzer → feasibility_checker），汇总输出最终 `ExplorationResult`。
- **涉及文件**：
  - `src/rv_insights/agents/explorer/agent.py`
- **依赖**：P1.1, P1.2, P1.3
- **验收标准**：
  - [ ] Handoff 链正确执行：mail → code → feasibility
  - [ ] 最终输出为完整的 `ExplorationResult`
  - [ ] Tracing 记录完整的子 Agent 调用链
  - [ ] 异常时正确降级（某个子 Agent 失败不影响其他）
- **测试**：
  - 集成测试：完整 Handoff 链运行
  - 单元测试：Mock 子 Agent，验证编排逻辑
  - 覆盖率 >= 80%
- **预估工时**：4h

---

### P1.5 邮件列表 MCP Server

- **描述**：实现 `mcp_servers/maillist/` MCP Server，提供邮件列表检索工具：`search_threads`, `get_thread_detail`, `get_patch_from_thread`。数据源为 lore.kernel.org REST API。
- **涉及文件**：
  - `src/rv_insights/mcp_servers/maillist/__init__.py`
  - `src/rv_insights/mcp_servers/maillist/server.py`
  - `src/rv_insights/mcp_servers/maillist/tools.py`
- **依赖**：P0.12, P1.4
- **验收标准**：
  - [ ] `search_threads` 按关键词和日期范围检索
  - [ ] `get_thread_detail` 返回完整邮件内容
  - [ ] `get_patch_from_thread` 提取内联 patch
  - [ ] 结果缓存（Redis）避免重复请求
- **测试**：
  - 集成测试：真实 API 调用（限制请求数）
  - 单元测试：Mock HTTP，验证解析逻辑
  - 覆盖率 >= 80%
- **预估工时**：5h

---

### P1.6 规划 Agent — 开发方案子 Agent

- **描述**：实现 `dev_planner` 子 Agent（OpenAI Agents SDK），根据 `ExplorationResult` 生成结构化的 `DevPlan`（修改文件列表、实现步骤、预估复杂度）。
- **涉及文件**：
  - `src/rv_insights/agents/planner/__init__.py`
  - `src/rv_insights/agents/planner/dev_planner.py`
  - `src/rv_insights/agents/planner/tools.py`
  - `src/rv_insights/agents/planner/guardrails.py`
- **依赖**：P0.2, P0.11, P1.4
- **验收标准**：
  - [ ] 输出符合 `DevPlan` 模型
  - [ ] 修改文件列表与 `ExplorationResult.affected_files` 一致
  - [ ] 实现步骤可执行（非空泛描述）
  - [ ] Guardrail 验证方案完整性（必须包含测试步骤）
- **测试**：
  - 单元测试：不同 ExplorationResult 输入的方案生成
  - Guardrail 测试：不完整方案被拦截
  - 覆盖率 >= 80%
- **预估工时**：4h

---

### P1.7 规划 Agent — 测试方案子 Agent

- **描述**：实现 `test_planner` 子 Agent（OpenAI Agents SDK），根据 `ExplorationResult` 和 `DevPlan` 生成 `TestPlan`（测试类型、测试用例、QEMU 配置）。
- **涉及文件**：
  - `src/rv_insights/agents/planner/test_planner.py`
- **依赖**：P0.2, P0.11, P1.6
- **验收标准**：
  - [ ] 输出符合 `TestPlan` 模型
  - [ ] 测试类型覆盖：编译测试、单元测试、boot 测试
  - [ ] QEMU 配置参数合理
  - [ ] 测试用例与 DevPlan 的修改范围匹配
- **测试**：
  - 单元测试：不同 DevPlan 输入的测试方案生成
  - 覆盖率 >= 80%
- **预估工时**：3h

---

### P1.8 规划 Agent — 主 Agent 编排

- **描述**：实现规划 Agent 主入口，编排 dev_planner 和 test_planner，合并输出 `ExecutionPlan`（含 `DevPlan` + `TestPlan` + `RiskAssessment`）。
- **涉及文件**：
  - `src/rv_insights/agents/planner/agent.py`
- **依赖**：P1.6, P1.7
- **验收标准**：
  - [ ] 输出为完整的 `ExecutionPlan`
  - [ ] `RiskAssessment` 综合 dev 和 test 两个维度
  - [ ] Guardrail 验证 plan 完整性
- **测试**：
  - 集成测试：完整规划流程
  - 单元测试：Mock 子 Agent
  - 覆盖率 >= 80%
- **预估工时**：3h

---

### P1.9 Git 工具 MCP Server

- **描述**：实现 `mcp_servers/git_tools/` MCP Server，提供 Git 操作工具：`create_worktree`, `apply_patch`, `format_patch`, `run_checkpatch`, `get_diff`。
- **涉及文件**：
  - `src/rv_insights/mcp_servers/git_tools/__init__.py`
  - `src/rv_insights/mcp_servers/git_tools/server.py`
  - `src/rv_insights/mcp_servers/git_tools/tools.py`
- **依赖**：P0.12
- **验收标准**：
  - [ ] `create_worktree` 正确创建和清理 worktree
  - [ ] `apply_patch` 成功应用 git format-patch 格式补丁
  - [ ] `format_patch` 生成符合内核规范的 patch
  - [ ] `run_checkpatch` 调用 `scripts/checkpatch.pl` 并解析结果
  - [ ] `get_diff` 返回指定 commit 范围的 diff
- **测试**：
  - 集成测试：在测试仓库上执行全部工具
  - 单元测试：Mock git 命令输出
  - 覆盖率 >= 85%
- **预估工时**：5h

---

### P1.10 开发 Agent

- **描述**：实现开发 Agent（Claude Agent SDK），根据 `ExecutionPlan` 在 Git worktree 中执行代码修改。包含 `can_use_tool` 权限回调（白名单机制）、沙箱配置、MCP Server 接入。
- **涉及文件**：
  - `src/rv_insights/agents/developer/__init__.py`
  - `src/rv_insights/agents/developer/agent.py`
  - `src/rv_insights/agents/developer/permissions.py`
- **依赖**：P0.10, P1.8, P1.9
- **验收标准**：
  - [ ] 在 worktree 中正确执行代码修改
  - [ ] `can_use_tool` 拦截非白名单工具（如 WebFetch）
  - [ ] 输出符合 `DevelopmentResult` 模型
  - [ ] commit message 符合内核规范（subsystem 前缀 + Signed-off-by）
  - [ ] 沙箱配置正确（网络受限、文件系统受限）
- **测试**：
  - 集成测试：在测试仓库上执行简单修改（如修复 typo）
  - 单元测试：权限回调、沙箱配置
  - 覆盖率 >= 80%
- **预估工时**：6h

---

### P1.11 审核 Agent — 子 Agent 实现

- **描述**：实现审核 Agent 的三个子 Agent（OpenAI Agents SDK）：`security_reviewer`（安全审查）、`correctness_reviewer`（正确性审查）、`style_reviewer`（风格审查）。每个子 Agent 输出 `ReviewFinding` 列表。
- **涉及文件**：
  - `src/rv_insights/agents/reviewer/__init__.py`
  - `src/rv_insights/agents/reviewer/security_reviewer.py`
  - `src/rv_insights/agents/reviewer/correctness_reviewer.py`
  - `src/rv_insights/agents/reviewer/style_reviewer.py`
  - `src/rv_insights/agents/reviewer/guardrails.py`
- **依赖**：P0.2, P0.11, P1.10
- **验收标准**：
  - [ ] 每个子 Agent 输出 `list[ReviewFinding]`
  - [ ] `severity` 分级正确（critical/high/medium/low/info）
  - [ ] `category` 与子 Agent 职责匹配
  - [ ] Guardrail 确保输出格式一致
- **测试**：
  - 单元测试：预设代码片段 → 验证 findings 输出
  - 覆盖率 >= 80%
- **预估工时**：5h

---

### P1.12 审核 Agent — 主 Agent 编排与 Verdict

- **描述**：实现审核 Agent 主入口，使用 Handoff 分发到三个子 Agent，汇总 findings 并生成 `ReviewVerdict`（approved/rejected + 理由）。
- **涉及文件**：
  - `src/rv_insights/agents/reviewer/agent.py`
- **依赖**：P1.11
- **验收标准**：
  - [ ] 三个子 Agent 并行执行
  - [ ] findings 按 severity 排序
  - [ ] 存在 critical finding 时自动 reject
  - [ ] 输出为完整的 `ReviewVerdict`
- **测试**：
  - 集成测试：完整审核流程
  - 单元测试：不同 findings 组合的 verdict 逻辑
  - 覆盖率 >= 85%
- **预估工时**：4h

---

### P1.13 测试 Agent

- **描述**：实现测试 Agent（Claude Agent SDK），根据 `TestPlan` 在沙箱环境中执行测试：交叉编译、QEMU boot 测试、单元测试。包含沙箱配置（设计文档 Section 4.5 修正版）。
- **涉及文件**：
  - `src/rv_insights/agents/tester/__init__.py`
  - `src/rv_insights/agents/tester/agent.py`
  - `src/rv_insights/agents/tester/permissions.py`
- **依赖**：P0.10, P1.9, P1.12
- **验收标准**：
  - [ ] 成功执行 RISC-V 交叉编译
  - [ ] QEMU boot 测试正确启动和验证
  - [ ] 测试输出写入 `test-output/` 目录
  - [ ] 输出符合 `TestResult` 模型
  - [ ] 沙箱限制生效（禁止 WebFetch/WebSearch）
- **测试**：
  - 集成测试：对简单 patch 执行编译测试
  - 单元测试：沙箱配置、权限回调
  - 覆盖率 >= 80%
- **预估工时**：6h

---

### P1.14 测试执行 MCP Server

- **描述**：实现 `mcp_servers/test_runner/` MCP Server，提供测试执行工具：`cross_compile`, `qemu_boot_test`, `run_unit_tests`, `parse_test_output`。
- **涉及文件**：
  - `src/rv_insights/mcp_servers/test_runner/__init__.py`
  - `src/rv_insights/mcp_servers/test_runner/server.py`
  - `src/rv_insights/mcp_servers/test_runner/tools.py`
- **依赖**：P0.12, P1.13
- **验收标准**：
  - [ ] `cross_compile` 调用 RISC-V 交叉编译工具链
  - [ ] `qemu_boot_test` 启动 QEMU 并验证 boot 成功
  - [ ] `parse_test_output` 正确解析编译/测试日志
  - [ ] 超时控制（编译 10min，boot 5min）
- **测试**：
  - 集成测试：编译简单内核模块
  - 单元测试：日志解析
  - 覆盖率 >= 80%
- **预估工时**：5h

---

### P1.15 Prompt 模板初始版本

- **描述**：为 5 个 Agent 编写初始版本的 system prompt（设计文档 Section 4.6），存储在 `prompts/` 目录。实现 `PromptManager` 加载机制。
- **涉及文件**：
  - `prompts/explorer/v1.0.0.md` 及子 Agent prompts
  - `prompts/planner/v1.0.0.md` 及子 Agent prompts
  - `prompts/developer/v1.0.0.md`
  - `prompts/reviewer/v1.0.0.md` 及子 Agent prompts
  - `prompts/tester/v1.0.0.md`
  - `src/rv_insights/agents/prompt_manager.py`
- **依赖**：P1.4, P1.8, P1.10, P1.12, P1.13
- **验收标准**：
  - [ ] 每个 prompt 包含：角色定义、任务描述、输出格式要求、领域约束
  - [ ] `PromptManager.load()` 正确加载指定版本
  - [ ] `PromptManager.load_with_context()` 正确注入运行时变量
  - [ ] prompt 中无硬编码的仓库路径或 API Key
- **测试**：
  - 单元测试：加载、版本切换、上下文注入
  - 覆盖率 >= 90%
- **预估工时**：6h

---

## Phase 2：流水线集成（3 周）

### P2.1 Pipeline Engine 状态机骨架

- **描述**：实现 `PipelineEngine` 核心状态机（设计文档 Section 5），定义状态枚举和合法转换规则。不含 Agent 调用，仅状态流转逻辑。
- **涉及文件**：
  - `src/rv_insights/engine/__init__.py`
  - `src/rv_insights/engine/state_machine.py`
  - `src/rv_insights/engine/pipeline.py`
- **依赖**：P0.2, P0.6
- **验收标准**：
  - [ ] 所有合法状态转换正确执行
  - [ ] 非法状态转换抛出 `InvalidTransitionError`
  - [ ] 状态变更自动写入数据库和审计日志
- **测试**：
  - 单元测试：所有合法/非法转换组合
  - 集成测试：状态持久化到 PostgreSQL
  - 覆盖率 >= 95%
- **预估工时**：4h

---

### P2.2 人工审核门禁服务

- **描述**：实现 `HumanGateService`（设计文档 Section 5.2），包含 `request_review()`, `wait_for_decision()`, `submit_decision()`。支持 5 种决策类型。
- **涉及文件**：
  - `src/rv_insights/engine/human_gate.py`
- **依赖**：P0.6, P0.9, P2.1
- **验收标准**：
  - [ ] 5 种决策类型全部正确处理
  - [ ] 审核超时后发送提醒
  - [ ] 所有决策记录到 `human_reviews` 表和审计日志
- **测试**：
  - 单元测试：每种决策类型的处理逻辑
  - 集成测试：完整审核流程（request → wait → submit）
  - 超时测试：验证超时提醒触发
  - 覆盖率 >= 90%
- **预估工时**：5h

---

### P2.3 通知服务

- **描述**：实现 `NotificationService`（设计文档 Section 5.4），支持 SSE 和 Webhook 两个渠道。
- **涉及文件**：
  - `src/rv_insights/engine/notification.py`
- **依赖**：P0.3, P2.2
- **验收标准**：
  - [ ] SSE 推送正确发送到已连接客户端
  - [ ] Webhook 正确发送 HTTP POST（支持 Slack/飞书格式）
  - [ ] 发送失败时重试（最多 3 次）
- **测试**：
  - 单元测试：消息格式化、重试逻辑
  - 集成测试：SSE 端到端
  - 覆盖率 >= 80%
- **预估工时**：4h

---

### P2.4 Pipeline Engine 集成 Agent 调用

- **描述**：在 `PipelineEngine.run_case()` 中集成 5 个 Agent 的实际调用，实现完整的 `探索 → 规划 → 开发 → 审核 → 测试` 流程，每阶段之间插入人工审核门禁。
- **涉及文件**：
  - `src/rv_insights/engine/pipeline.py`（扩展）
- **依赖**：P1.4, P1.8, P1.10, P1.12, P1.13, P2.1, P2.2
- **验收标准**：
  - [ ] 完整流水线可从头到尾执行
  - [ ] 4 个人工审核门禁正确触发
  - [ ] Agent 输出正确传递到下一阶段
  - [ ] 每个阶段的产物正确持久化
- **测试**：
  - 集成测试（Mock Agent）：完整流水线 happy path
  - 集成测试（Mock Agent）：各阶段人工驳回场景
  - 覆盖率 >= 85%
- **预估工时**：6h

---

### P2.5 开发-审核迭代闭环

- **描述**：实现 `run_dev_review_loop()`（设计文档 Section 6），包含迭代控制（最大 5 轮）、收敛检测、会话复用、增量修复。
- **涉及文件**：
  - `src/rv_insights/engine/dev_review_loop.py`
- **依赖**：P1.10, P1.12, P2.4
- **验收标准**：
  - [ ] 最大迭代次数限制生效
  - [ ] 收敛检测正确触发提前终止
  - [ ] Claude 会话正确复用（同一 session_id）
- **测试**：
  - 单元测试：收敛检测算法、迭代计数
  - 集成测试（Mock Agent）：1 轮通过、3 轮收敛、5 轮超限
  - 覆盖率 >= 90%
- **预估工时**：5h

---

### P2.6 `run_case_from_phase()` 部分恢复

- **描述**：实现从任意阶段恢复执行（设计文档 Section 5.3），包含 4 种驳回处理逻辑。
- **涉及文件**：
  - `src/rv_insights/engine/pipeline.py`（扩展）
- **依赖**：P2.4, P2.5
- **验收标准**：
  - [ ] 从每个阶段恢复执行均正确
  - [ ] 4 种驳回类型（reject/reject_to/abandon/modify）全部正确处理
  - [ ] 恢复元数据正确记录
- **测试**：
  - 单元测试：每种驳回类型的处理
  - 集成测试：中断 → 恢复 → 完成
  - 覆盖率 >= 85%
- **预估工时**：4h

---

### P2.7 资源调度器

- **描述**：实现 `ResourceScheduler`（设计文档 Section 3.6），管理 Claude CLI、OpenAI API、QEMU 的并发信号量和调度优先级。
- **涉及文件**：
  - `src/rv_insights/engine/scheduler.py`
- **依赖**：P0.3, P2.4
- **验收标准**：
  - [ ] 信号量正确限制各资源并发数
  - [ ] 优先级调度：迭代中案例 > 高优先级 > 等待最久
  - [ ] 死锁检测（超时释放）
- **测试**：
  - 单元测试：信号量竞争、优先级排序
  - 并发测试：多个 asyncio task 竞争资源
  - 覆盖率 >= 85%
- **预估工时**：4h

---

### P2.8 成本追踪器

- **描述**：实现 `CostTracker`（设计文档 Section 9.4），跨阶段追踪费用，支持预算告警、模型降级、超预算阻断。
- **涉及文件**：
  - `src/rv_insights/observability/cost_tracker.py`
- **依赖**：P0.3, P0.9, P2.4
- **验收标准**：
  - [ ] 70% 预算时 warn，85% 时降级模型，100% 时阻断
  - [ ] 模型降级链正确（Sonnet → Haiku, GPT-4o → GPT-4o-mini）
  - [ ] 费用按阶段分类统计
- **测试**：
  - 单元测试：各预算阈值的状态判断、模型降级
  - 覆盖率 >= 90%
- **预估工时**：3h

---

### P2.9 FastAPI Gateway 核心端点

- **描述**：实现 REST API（设计文档 Section 3.7）：案例 CRUD、审核提交、SSE 事件流、健康检查。包含 JWT 认证。
- **涉及文件**：
  - `src/rv_insights/api/__init__.py`
  - `src/rv_insights/api/app.py`
  - `src/rv_insights/api/routes/cases.py`
  - `src/rv_insights/api/routes/reviews.py`
  - `src/rv_insights/api/routes/system.py`
  - `src/rv_insights/api/auth.py`
  - `src/rv_insights/api/schemas.py`
- **依赖**：P0.6, P2.2, P2.4
- **验收标准**：
  - [ ] 案例 CRUD 端点正常工作
  - [ ] 审核提交端点正确触发 HumanGateService
  - [ ] SSE 事件流正常推送
  - [ ] 无 token 时返回 401
- **测试**：
  - 集成测试：每个端点的 happy path + 错误场景
  - 认证测试：无 token、过期 token、无效 token
  - 覆盖率 >= 85%
- **预估工时**：6h

---

### P2.10 CLI 入口

- **描述**：实现 CLI 命令（设计文档附录 B，使用 `typer`）：`case`, `explore`, `review`, `audit`, `kb`, `system` 子命令组。
- **涉及文件**：
  - `src/rv_insights/cli.py`
- **依赖**：P2.9
- **验收标准**：
  - [ ] 所有命令可执行且输出格式正确
  - [ ] `--help` 显示完整帮助信息
  - [ ] 支持 `--format json` 输出
- **测试**：
  - 单元测试：使用 `typer.testing.CliRunner` 测试每个命令
  - 覆盖率 >= 80%
- **预估工时**：4h

---

### P2.11 知识库 MCP Server

- **描述**：实现知识库检索 MCP Server，提供 `search_knowledge`, `get_spec_section`, `get_maintainer_info` 工具。基于 pgvector 向量检索。
- **涉及文件**：
  - `src/rv_insights/mcp_servers/knowledge/__init__.py`
  - `src/rv_insights/mcp_servers/knowledge/server.py`
  - `src/rv_insights/mcp_servers/knowledge/tools.py`
  - `src/rv_insights/knowledge/retriever.py`
- **依赖**：P0.5, P0.12
- **验收标准**：
  - [ ] 向量检索使用 cosine 距离，结果按相关度排序
  - [ ] 结果包含相关度分数和来源引用
- **测试**：
  - 集成测试：插入测试知识条目 → 检索 → 验证排序
  - 覆盖率 >= 80%
- **预估工时**：5h

---

### P2.12 知识摄入流水线

- **描述**：实现 `KnowledgeIngestionPipeline`（设计文档 Section 8.4），包含文档分块、Embedding 生成、增量更新、过期淘汰。
- **涉及文件**：
  - `src/rv_insights/knowledge/indexer.py`
  - `src/rv_insights/knowledge/chunking.py`
  - `src/rv_insights/knowledge/sync.py`
- **依赖**：P0.5, P0.6, P2.11
- **验收标准**：
  - [ ] 按语义边界分块（spec 按章节、code 按函数、email 按线程）
  - [ ] 增量更新：content_hash 去重
  - [ ] 过期淘汰：超过 180 天未引用且评分低的条目被软删除
- **测试**：
  - 单元测试：分块策略、去重逻辑
  - 集成测试：完整摄入流程
  - 覆盖率 >= 80%
- **预估工时**：6h

---

## Phase 3：端到端验证（2 周）

### P3.1 E2E 测试基础设施

- **描述**：搭建端到端测试环境。编写 `docker-compose.e2e.yml`（PostgreSQL + Redis + MinIO + 应用），配置 E2E 专用 `.env.e2e`（使用低成本模型 `claude-haiku-4-5` + `gpt-4o-mini`），编写 `conftest.py` 提供 E2E fixture（数据库清理、环境初始化、超时控制）。
- **涉及文件**：
  - `docker-compose.e2e.yml`
  - `.env.e2e`
  - `tests/e2e/conftest.py`
  - `tests/e2e/__init__.py`
  - `scripts/e2e-setup.sh`
- **依赖**：P2.5（Pipeline Engine 完整可运行）
- **验收标准**：
  - [ ] `docker compose -f docker-compose.e2e.yml up` 可启动完整环境
  - [ ] E2E fixture 自动清理数据库、重置状态
  - [ ] 单次 E2E 运行成本 < $0.50（使用低成本模型）
  - [ ] 超时控制：单个 E2E 用例最长 10 分钟
- **测试**：
  - 冒烟测试：环境启动 → 健康检查通过 → 环境销毁
  - 覆盖率 >= 80%
- **预估工时**：6h

---

### P3.2 试点仓库选择与数据准备

- **描述**：根据设计文档 Section 13.4 的选择标准，确定 1-2 个试点仓库。准备 3-5 个真实贡献案例的种子数据（issue 描述、相关代码路径、预期产物）。创建 `tests/e2e/fixtures/` 目录存放案例定义。
- **涉及文件**：
  - `tests/e2e/fixtures/cases.json`
  - `tests/e2e/fixtures/README.md`
  - `docs/pilot-repos.md`
- **依赖**：P3.1
- **验收标准**：
  - [ ] 至少 3 个案例覆盖不同类型（typo 修复、bug 修复、功能增强）
  - [ ] 每个案例包含：仓库 URL、目标分支、issue 描述、预期变更范围
  - [ ] 案例数据可被 E2E 测试 fixture 加载
- **测试**：
  - 单元测试：案例数据加载、schema 校验
  - 覆盖率 >= 80%
- **预估工时**：4h

---

### P3.3 单案例端到端跑通

- **描述**：选取最简单的案例（如 typo 修复），跑通从 CREATED → EXPLORING → PLANNING → DEVELOPING → REVIEWING → TESTING → COMPLETED 的完整流水线。验证所有 Agent 调用、状态流转、产物生成均正常。
- **涉及文件**：
  - `tests/e2e/test_single_case.py`
  - `src/rv_insights/pipeline/engine.py`（可能需要调试修复）
- **依赖**：P3.2
- **验收标准**：
  - [ ] 案例从 CREATED 到 COMPLETED 全流程无人工干预（审核门禁自动通过模式）
  - [ ] 每个阶段产物存在且格式正确（探索报告、执行计划、补丁、审核报告、测试报告）
  - [ ] 审计日志记录完整（所有 Agent 调用和状态变更）
  - [ ] 生成的 patch 可通过 `git apply` 应用
- **测试**：
  - E2E 测试：完整流水线断言
  - 覆盖率 >= 80%
- **预估工时**：8h

---

### P3.4 人工审核门禁验证

- **描述**：验证 4 个人工审核点（探索后、计划后、开发后、最终）均可正常暂停、通过、驳回。测试驳回后的回流逻辑（回到上一阶段重新执行）。验证审核超时提醒（24h）。
- **涉及文件**：
  - `tests/e2e/test_human_review.py`
  - `src/rv_insights/pipeline/engine.py`
  - `src/rv_insights/services/notification.py`
- **依赖**：P3.3
- **验收标准**：
  - [ ] 4 个审核点均可暂停流水线等待人工决策
  - [ ] 通过后流水线继续下一阶段
  - [ ] 驳回后流水线回到对应阶段重新执行（附带驳回原因）
  - [ ] 审核等待超过 24h 触发提醒通知
- **测试**：
  - E2E 测试：模拟审核通过/驳回/超时场景
  - 覆盖率 >= 80%
- **预估工时**：6h

---

### P3.5 开发-审核迭代闭环验证

- **描述**：验证开发 Agent 和审核 Agent 之间的多轮迭代机制。至少 1 个案例经历 2+ 轮迭代后通过审核。验证收敛检测（连续 2 轮 findings 不减则提前升级）和最大迭代限制（5 轮）。
- **涉及文件**：
  - `tests/e2e/test_dev_review_loop.py`
  - `src/rv_insights/pipeline/dev_review.py`
- **依赖**：P3.4
- **验收标准**：
  - [ ] 至少 1 个案例经历 2+ 轮迭代后审核通过
  - [ ] 每轮迭代的 findings 数量递减（收敛趋势）
  - [ ] 连续 2 轮 findings 不减时触发升级（人工介入）
  - [ ] 超过 5 轮自动停止并标记为需人工处理
  - [ ] 迭代过程中 session 复用（不重新创建 Agent）
- **测试**：
  - E2E 测试：多轮迭代场景、收敛检测、超限处理
  - 覆盖率 >= 80%
- **预估工时**：6h

---

### P3.6 补丁质量验证

- **描述**：验证生成的补丁符合 Linux 内核贡献标准。运行 `checkpatch.pl --strict` 检查、RISC-V 交叉编译验证、`git format-patch` 格式正确性。验证 PatchGenerator（设计文档 Section 6.4）的完整输出。
- **涉及文件**：
  - `tests/e2e/test_patch_quality.py`
  - `src/rv_insights/tools/patch_generator.py`
- **依赖**：P3.5
- **验收标准**：
  - [ ] 生成的 patch 通过 `checkpatch.pl --strict`（0 error, 0 warning）
  - [ ] patch 可通过 RISC-V 交叉编译（`make ARCH=riscv CROSS_COMPILE=riscv64-linux-gnu-`）
  - [ ] commit message 格式符合内核规范（Subsystem: summary, Signed-off-by）
  - [ ] `git format-patch` 输出可直接用于 `git send-email`
- **测试**：
  - E2E 测试：补丁格式、编译、checkpatch 验证
  - 覆盖率 >= 80%
- **预估工时**：5h

---

### P3.7 质量指标收集与基线建立

- **描述**：收集端到端验证的质量指标，建立 MVP 基线。指标包括：审核通过率、平均迭代次数、人工驳回率、单案例成本、端到端耗时。将指标写入 Prometheus/metrics 并生成基线报告。
- **涉及文件**：
  - `tests/e2e/test_metrics.py`
  - `src/rv_insights/metrics/collector.py`
  - `docs/baseline-report.md`
- **依赖**：P3.6
- **验收标准**：
  - [ ] 审核通过率（首轮）> 30%
  - [ ] 平均迭代次数 < 3
  - [ ] 人工驳回率 < 20%
  - [ ] 单案例成本 < $15
  - [ ] 所有指标可通过 `/api/v1/system/metrics` 查询
- **测试**：
  - 集成测试：指标记录、查询、聚合
  - 覆盖率 >= 80%
- **预估工时**：5h

---

### P3.8 Prompt 迭代优化

- **描述**：基于 P3.7 收集的质量指标，对各 Agent 的 prompt 进行迭代优化。遵循设计文档 Section 4.6 的迭代流程：修改 prompt → 跑历史案例 → 对比指标 → 人工评审 → 合入主版本。
- **涉及文件**：
  - `prompts/explore/v2.md`（或其他需要优化的 prompt）
  - `prompts/develop/v2.md`
  - `prompts/review/v2.md`
  - `src/rv_insights/prompts/manager.py`
  - `tests/e2e/test_prompt_iteration.py`
- **依赖**：P3.7
- **验收标准**：
  - [ ] 至少 1 个 Agent 的 prompt 完成 v1 → v2 迭代
  - [ ] v2 prompt 在 3-5 个历史案例上的指标优于 v1
  - [ ] PromptManager 支持版本切换和 A/B 对比
  - [ ] prompt 变更有 code review 记录
- **测试**：
  - 集成测试：prompt 版本切换、指标对比
  - 覆盖率 >= 80%
- **预估工时**：6h

---

## Phase 4：生产化加固（2 周）

### P4.1 错误分类与重试策略

- **描述**：实现完整的错误分类体系和重试策略（设计文档 Section 3.5）。区分可恢复错误（API 超时、速率限制）和不可恢复错误（认证失败、预算超限）。实现指数退避重试、断路器模式。
- **涉及文件**：
  - `src/rv_insights/core/errors.py`
  - `src/rv_insights/core/retry.py`
  - `src/rv_insights/core/circuit_breaker.py`
  - `tests/unit/test_retry.py`
  - `tests/unit/test_circuit_breaker.py`
- **依赖**：P3.3（Pipeline 基本可运行）
- **验收标准**：
  - [ ] 错误分类覆盖所有 SDK 异常类型（Claude API、OpenAI API、数据库、文件系统）
  - [ ] 可恢复错误自动重试（指数退避，最大 3 次）
  - [ ] 不可恢复错误立即上报，不重试
  - [ ] 断路器：连续 5 次失败后熔断 60s，半开状态探测恢复
  - [ ] HTTP 429 响应正确解析 `Retry-After` 头
- **测试**：
  - 单元测试：各错误类型分类、重试逻辑、断路器状态机
  - 集成测试：模拟 API 故障场景
  - 覆盖率 >= 85%
- **预估工时**：6h

---

### P4.2 会话持久化与断点续传

- **描述**：实现 `SessionStore` 协议和 checkpoint 机制（设计文档 Section 5.5）。Pipeline 中断后可从最近的检查点恢复。支持 PostgreSQL 适配器存储 checkpoint。实现 `GracefulShutdown` 的完整逻辑。
- **涉及文件**：
  - `src/rv_insights/pipeline/checkpoint.py`
  - `src/rv_insights/pipeline/session_store.py`
  - `src/rv_insights/pipeline/graceful_shutdown.py`
  - `tests/unit/test_checkpoint.py`
  - `tests/integration/test_session_recovery.py`
- **依赖**：P4.1
- **验收标准**：
  - [ ] 每个阶段完成后自动保存 checkpoint（case_id, status, phase, artifacts_summary）
  - [ ] SIGTERM/SIGINT 触发优雅停机：保存状态 → 终止子进程 → 清理 worktree → 释放信号量
  - [ ] 重启后自动扫描 checkpoint 表，恢复中断的案例
  - [ ] 恢复后从断点阶段继续，不重复已完成的阶段
  - [ ] 故障注入测试：在各阶段随机 kill 进程，验证恢复正确性
- **测试**：
  - 单元测试：checkpoint 序列化/反序列化
  - 集成测试：故障注入 → 恢复 → 验证状态一致性
  - 覆盖率 >= 85%
- **预估工时**：8h

---

### P4.3 成本监控与预算控制集成

- **描述**：将 `CostTracker`（设计文档 Section 9.4）集成到 Pipeline Engine。每个 Agent 调用前查询预算状态，调用后记录消耗。实现模型降级链和预算超限处理。
- **涉及文件**：
  - `src/rv_insights/cost/tracker.py`
  - `src/rv_insights/cost/budget.py`
  - `src/rv_insights/pipeline/engine.py`（集成点）
  - `tests/unit/test_cost_tracker.py`
  - `tests/integration/test_budget_control.py`
- **依赖**：P4.1
- **验收标准**：
  - [ ] 每次 Agent 调用自动记录 token 消耗和成本
  - [ ] 70% 预算时告警（日志 + 通知）
  - [ ] 85% 预算时自动降级模型（`claude-sonnet-4-6` → `claude-haiku-4-5`）
  - [ ] 100% 预算时进入 `BUDGET_EXCEEDED` 状态，等待人工决策
  - [ ] 成本明细可通过 `/api/v1/cases/{id}/cost` 查询
  - [ ] 单案例成本硬上限 $15
- **测试**：
  - 单元测试：预算计算、降级逻辑、状态判断
  - 集成测试：模拟成本累积 → 告警 → 降级 → 超限
  - 覆盖率 >= 85%
- **预估工时**：6h

---

### P4.4 CLI 入口完善

- **描述**：完善 CLI 入口（`rv-insights` 命令），补充所有子命令的参数校验、帮助信息、输出格式化。支持 `--format json` 机器可读输出。添加 `config` 子命令管理配置。
- **涉及文件**：
  - `src/rv_insights/cli/main.py`
  - `src/rv_insights/cli/commands/config.py`
  - `src/rv_insights/cli/formatters.py`
  - `tests/unit/test_cli_commands.py`
- **依赖**：P4.2（断点续传支持 `resume` 命令）
- **验收标准**：
  - [ ] 所有子命令（`run`, `list`, `show`, `review`, `resume`, `config`）可执行
  - [ ] `--help` 显示完整帮助信息（含示例）
  - [ ] `--format json` 输出合法 JSON
  - [ ] `config set/get/list` 管理 `.env` 和 `settings.toml`
  - [ ] 参数校验错误给出友好提示
  - [ ] 退出码规范：0=成功, 1=用户错误, 2=系统错误
- **测试**：
  - 单元测试：使用 `typer.testing.CliRunner` 测试每个命令和参数组合
  - 覆盖率 >= 85%
- **预估工时**：5h

---

### P4.5 日志系统与审计完整性

- **描述**：完善结构化日志系统（设计文档 Section 9.1-9.2）。确保所有 Agent 调用、状态变更、人工决策均有审计记录。实现日志轮转和归档。
- **涉及文件**：
  - `src/rv_insights/core/logging.py`
  - `src/rv_insights/audit/logger.py`
  - `src/rv_insights/audit/models.py`
  - `tests/unit/test_audit_logger.py`
  - `tests/integration/test_audit_completeness.py`
- **依赖**：P4.4
- **验收标准**：
  - [ ] 所有 Agent 调用记录：agent_name, model, input_tokens, output_tokens, duration, cost
  - [ ] 所有状态变更记录：case_id, from_status, to_status, trigger, timestamp
  - [ ] 所有人工决策记录：reviewer, decision, reason, timestamp
  - [ ] 日志格式为结构化 JSON（便于 ELK/Loki 采集）
  - [ ] 审计日志不可篡改（append-only 表，无 UPDATE/DELETE 权限）
- **测试**：
  - 单元测试：日志格式、字段完整性
  - 集成测试：跑完整案例后查询审计表，验证记录完整
  - 覆盖率 >= 85%
- **预估工时**：5h

---

### P4.6 并发控制与资源调度

- **描述**：实现 `ResourceScheduler`（设计文档 Section 3.6）的生产级并发控制。Worker Pool 限制并发案例数，API 速率限制共享，优先级调度。
- **涉及文件**：
  - `src/rv_insights/core/scheduler.py`
  - `src/rv_insights/core/rate_limiter.py`
  - `tests/unit/test_scheduler.py`
  - `tests/integration/test_concurrent_cases.py`
- **依赖**：P4.5
- **验收标准**：
  - [ ] Worker Pool 默认并发 2 个案例，可配置
  - [ ] API 速率限制：Claude 50 RPM / OpenAI 500 RPM 共享
  - [ ] 优先级调度：CRITICAL > HIGH > NORMAL > LOW
  - [ ] 空闲超时自动回收 worker（默认 5 分钟）
  - [ ] 资源争用时排队等待，不丢弃任务
- **测试**：
  - 单元测试：信号量逻辑、优先级排序
  - 集成测试：并发提交多个案例，验证调度顺序和资源限制
  - 覆盖率 >= 85%
- **预估工时**：6h

---

### P4.7 安全加固

- **描述**：实现安全防护措施：输入净化（防 prompt 注入）、沙箱隔离（Agent 文件系统权限）、凭据管理（环境变量，不硬编码）、API 端点速率限制。
- **涉及文件**：
  - `src/rv_insights/security/sanitizer.py`
  - `src/rv_insights/security/sandbox.py`
  - `src/rv_insights/api/middleware/rate_limit.py`
  - `tests/unit/test_sanitizer.py`
  - `tests/unit/test_sandbox.py`
- **依赖**：P4.4
- **验收标准**：
  - [ ] 用户输入（issue 描述、审核意见）经过净化处理
  - [ ] Agent 沙箱：开发 Agent 只能写 worktree 目录，测试 Agent 限制写入范围
  - [ ] 无硬编码凭据（API key 全部从环境变量读取）
  - [ ] API 端点速率限制：认证用户 100 RPM，未认证 10 RPM
  - [ ] 错误消息不泄露内部路径或堆栈信息
- **测试**：
  - 单元测试：净化规则、沙箱权限检查
  - 集成测试：模拟注入攻击、越权访问
  - 覆盖率 >= 85%
- **预估工时**：6h

---

### P4.8 Docker Compose 生产配置

- **描述**：完善 `docker-compose.yml` 生产配置。添加健康检查、资源限制、日志驱动、重启策略。编写 `docker-compose.override.yml` 用于开发环境覆盖。编写部署文档。
- **涉及文件**：
  - `docker-compose.yml`（生产配置）
  - `docker-compose.override.yml`（开发覆盖）
  - `Dockerfile`
  - `.dockerignore`
  - `docs/deployment.md`
- **依赖**：P4.7
- **验收标准**：
  - [ ] 所有服务配置健康检查（`healthcheck`）
  - [ ] 资源限制：内存上限、CPU 配额
  - [ ] 重启策略：`unless-stopped`
  - [ ] 日志驱动：JSON 格式，最大 50MB 轮转
  - [ ] `docker compose up` 一键启动完整环境
  - [ ] 开发环境：热重载、调试端口暴露
- **测试**：
  - 集成测试：`docker compose up` → 健康检查全部通过 → 基本功能验证
  - 覆盖率 >= 80%
- **预估工时**：5h

---

### P4.9 CI/CD 流水线

- **描述**：配置 GitHub Actions CI/CD。PR 触发：lint + type check + 单元测试 + 集成测试。`main` 合并触发：E2E 测试 + Docker 镜像构建。配置测试覆盖率报告和徽章。
- **涉及文件**：
  - `.github/workflows/ci.yml`
  - `.github/workflows/e2e.yml`
  - `.github/workflows/docker-build.yml`
  - `scripts/ci-setup.sh`
- **依赖**：P4.8
- **验收标准**：
  - [ ] PR 检查：ruff lint + mypy type check + pytest 单元/集成测试（< 5 分钟）
  - [ ] `main` 合并：E2E 测试 + Docker 镜像构建推送
  - [ ] 测试覆盖率报告自动生成（codecov 或类似工具）
  - [ ] 覆盖率低于 80% 时 CI 失败
  - [ ] E2E 测试使用低成本模型，单次运行 < $1
- **测试**：
  - 验证：提交 PR → CI 自动运行 → 结果正确
  - 覆盖率 >= 80%
- **预估工时**：5h

---

### P4.10 MVP 验收与文档收尾

- **描述**：按照设计文档 Section 13.3 的 MVP 验收标准逐项验证。补充用户文档（README、快速开始指南、配置说明）。生成最终的质量报告。
- **涉及文件**：
  - `README.md`
  - `docs/quickstart.md`
  - `docs/configuration.md`
  - `docs/architecture.md`
  - `docs/mvp-acceptance-report.md`
- **依赖**：P4.9
- **验收标准**：
  - [ ] 端到端闭环：至少 1 个案例跑通完整流水线
  - [ ] 人工审核门禁：4 个审核点均正常工作
  - [ ] 开发-审核迭代：至少 1 个案例经历 2+ 轮迭代后通过
  - [ ] 补丁质量：通过 `checkpatch.pl --strict`
  - [ ] 编译通过：RISC-V 交叉编译成功
  - [ ] 审计完整性：所有操作有审计记录
  - [ ] 成本可控：单案例 < $15
  - [ ] 断点续传：故障注入后可恢复
  - [ ] README 包含：项目简介、架构图、快速开始、配置说明
- **测试**：
  - 验收测试：逐项对照 MVP 验收标准
  - 文档审查：所有文档无过时信息
- **预估工时**：6h

---

> **全部 57 个任务定义完毕。**  
> Phase 0: 12 tasks (~2 周) | Phase 1: 15 tasks (~3 周) | Phase 2: 12 tasks (~3 周) | Phase 3: 8 tasks (~2 周) | Phase 4: 10 tasks (~2 周)
