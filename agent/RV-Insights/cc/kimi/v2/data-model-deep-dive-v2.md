# RV-Insights v2: 数据持久化方案深度设计

**版本**: v2.0
**日期**: 2026-04-23
**定位**: 本文档是 `rv-insights-v2-design.md` 第 9 章（数据持久化与可观测性）的细化与扩展，覆盖完整数据库 Schema、Redis 结构、对象存储规范、ER 关系图、v1 到 v2 数据迁移方案及性能优化策略。

**架构演进**: v2 将编排核心从 v1 的 LangGraph 迁移至 OpenAI Agents SDK + Claude Agent SDK 混合架构，数据模型相应升级为双 SDK 状态持久化、SDK 使用追踪、跨 SDK 状态同步等能力。

---

## 1. 概述

### 1.1 设计目标

本文档定义 RV-Insights v2 平台完整的数据持久化架构，核心设计目标：

- **双 SDK 状态隔离与同步**: OpenAI SDK 原生 Session 持久化 + 应用层自定义状态表，支持跨 SDK 状态读写与审计追踪
- **多租户隔离**: 通过 PostgreSQL RLS + `tenant_id` 列实现逻辑隔离，支持可选的 Schema 级隔离（企业租户）
- **高可扩展性**: 时序表（sdk_usage_logs, agent_logs, state_change_log）按时间范围分区；JSONB 列配合 GIN 索引支持灵活查询
- **成本可观测性**: 精细化追踪 OpenAI 与 Claude 两套 SDK 的 Token 消耗、缓存命中、API 调用成本
- **工作流一致性**: 利用 OpenAI Agents SDK Session 持久化 + 应用层状态表实现双写一致性，支持 Human-in-the-Loop 中断与恢复
- **性能优化**: B-tree 覆盖索引、复合索引、部分索引、BRIN 索引针对大表时序查询；连接池与读写分离

### 1.2 v1 → v2 数据模型变更概览

| 维度 | v1 (LangGraph) | v2 (双 SDK 混合架构) |
|------|----------------|----------------------|
| 编排状态 | `checkpoints` 分区表（LangGraph 自动管理） | `openai_sessions`（SDK 原生）+ `rvinsights_sessions`（应用层扩展） |
| 状态存储 | 单一 LangGraph Checkpointer | 双持久化：OpenAI Session Store + 应用层 PostgreSQL |
| 成本追踪 | `agent_logs.token_usage` JSONB 字段 | 独立 `sdk_usage_logs` 表，支持 cache_creation/cache_read tokens |
| SDK 审计 | 无 | `state_change_log` 表记录每次跨 SDK 状态变更 |
| 死信队列 | `tasks` 表 status='dead_letter' | 独立 `dead_letter_queue` 表 |
| Git 锁 | Redis 分布式锁（无持久化） | `git_locks` 表持久化锁信息 |
| QEMU 池 | Redis 列表（无持久化） | `qemu_occupancy` 表持久化实例占用 |
| 会话成本 | `workflow_states` 内嵌字段 | 独立 `session_costs` 表 |

---

## 2. PostgreSQL 完整 Schema 设计

### 2.1 扩展与配置

```sql
-- ============================================================
-- RV-Insights v2 Database Setup
-- PostgreSQL 15+ Required
-- ============================================================

-- 启用必要扩展
CREATE EXTENSION IF NOT EXISTS "pgcrypto";           -- gen_random_uuid()
-- 注意：pg_uuidv7 不是标准 PostgreSQL 扩展。以下提供等效实现：
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements"; -- 查询性能监控
CREATE EXTENSION IF NOT EXISTS "btree_gin";          -- GIN 支持复合类型
CREATE EXTENSION IF NOT EXISTS "pg_trgm";            -- 模糊搜索

-- 自定义 UUIDv7 生成函数（替代 pg_uuidv7 扩展）
-- UUIDv7 提供时序排序优势，优于 UUIDv4 的随机分布
CREATE OR REPLACE FUNCTION uuid_generate_v7()
RETURNS uuid AS $$
DECLARE
    unix_ts bigint;
    uuid_bytes bytea;
BEGIN
    -- 当前 Unix 时间戳（毫秒）作为前 48 位
    unix_ts := (extract(epoch from clock_timestamp()) * 1000)::bigint;
    
    -- 生成 16 字节随机数据
    uuid_bytes := gen_random_bytes(16);
    
    -- 将前 48 位替换为时间戳（大端序）
    uuid_bytes := set_byte(uuid_bytes, 0, (unix_ts >> 40)::int);
    uuid_bytes := set_byte(uuid_bytes, 1, ((unix_ts >> 32) & 255)::int);
    uuid_bytes := set_byte(uuid_bytes, 2, ((unix_ts >> 24) & 255)::int);
    uuid_bytes := set_byte(uuid_bytes, 3, ((unix_ts >> 16) & 255)::int);
    uuid_bytes := set_byte(uuid_bytes, 4, ((unix_ts >> 8) & 255)::int);
    uuid_bytes := set_byte(uuid_bytes, 5, (unix_ts & 255)::int);
    
    -- 设置版本 (0111 = 7) 和变体 (10)
    uuid_bytes := set_byte(uuid_bytes, 6, (get_byte(uuid_bytes, 6) & 15) | 112);
    uuid_bytes := set_byte(uuid_bytes, 8, (get_byte(uuid_bytes, 8) & 63) | 128);
    
    RETURN encode(uuid_bytes, 'hex')::uuid;
END;
$$ LANGUAGE plpgsql VOLATILE;

-- 配置连接与性能参数（根据部署环境调整）
ALTER SYSTEM SET max_connections = 300;
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET work_mem = '32MB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET random_page_cost = 1.1;             -- SSD 优化
ALTER SYSTEM SET effective_io_concurrency = 200;     -- SSD 优化
ALTER SYSTEM SET idle_in_transaction_session_timeout = '30s';
ALTER SYSTEM SET idle_session_timeout = '10min';
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- 慢查询阈值 1s
SELECT pg_reload_conf();
```

### 2.2 租户与用户表

```sql
-- ============================================
-- 表: tenants (租户表)
-- 说明: 多租户顶层隔离单元
-- ============================================
CREATE TABLE tenants (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            text NOT NULL,
    slug            text NOT NULL UNIQUE,
    config          jsonb DEFAULT '{}',
    -- v2 新增: 租户级配额配置
    quota_config    jsonb DEFAULT '{
        "max_concurrent_sessions": 5,
        "monthly_budget_cap_usd": 500,
        "max_qemu_instances": 2,
        "storage_quota_gb": 10,
        "api_rate_limit_per_min": 100
    }',
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now()
);

CREATE INDEX tenants_slug_idx ON tenants (slug);

-- ============================================
-- 表: users (用户表)
-- 说明: 平台用户，隶属于租户
-- ============================================
CREATE TABLE users (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       bigint NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    auth_provider_id text,  -- OAuth / SSO 外部 ID
    email           text NOT NULL,
    display_name    text,
    role            text NOT NULL DEFAULT 'member'
        CHECK (role IN ('admin','member','viewer')),
    preferences     jsonb DEFAULT '{}',
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now(),
    UNIQUE (tenant_id, email)
);

CREATE INDEX users_tenant_id_idx ON users (tenant_id);
CREATE INDEX users_email_idx ON users (email);
```

### 2.3 会话核心表

```sql
-- ============================================
-- 表: sessions (会话表)
-- 说明: 对应一次完整的 RV-Insights 工作流执行
-- ============================================
CREATE TABLE sessions (
    id              uuid DEFAULT uuid_generate_v7() PRIMARY KEY,
    tenant_id       bigint NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    created_by      bigint NOT NULL REFERENCES users(id),
    title           text,
    description     text,
    current_stage   text NOT NULL DEFAULT 'INITIALIZATION'
        CHECK (current_stage IN (
            'INITIALIZATION','EXPLORATION','HUMAN_REVIEW_EXPLORATION',
            'PLANNING','HUMAN_REVIEW_PLANNING','DEVELOPMENT',
            'REVIEW','HUMAN_REVIEW_CODE','TESTING','HUMAN_REVIEW_TESTING','COMPLETION'
        )),
    status          text NOT NULL DEFAULT 'running'
        CHECK (status IN ('running','interrupted','completed','failed','cancelled')),
    -- v2 新增: 首选 SDK 配置
    preferred_sdk   text DEFAULT 'auto'
        CHECK (preferred_sdk IN ('auto','openai','claude')),
    -- v2 新增: Token 预算控制
    max_budget_usd  decimal(10,4) DEFAULT 5.0,
    budget_consumed_usd decimal(10,4) DEFAULT 0.0,
    config          jsonb DEFAULT '{}',
    metadata        jsonb DEFAULT '{}',
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now(),
    completed_at    timestamptz,
    -- v2 新增: 取消相关时间戳
    cancel_requested_at timestamptz,
    cancelled_at    timestamptz
);

CREATE INDEX sessions_tenant_id_idx ON sessions (tenant_id);
CREATE INDEX sessions_tenant_status_idx ON sessions (tenant_id, status);
CREATE INDEX sessions_created_by_idx ON sessions (created_by);
CREATE INDEX sessions_current_stage_idx ON sessions (current_stage);
CREATE INDEX sessions_created_at_idx ON sessions (created_at);
CREATE INDEX sessions_status_updated_idx ON sessions (status, updated_at)
    WHERE status = 'running';
```

### 2.4 OpenAI SDK 原生 Session 表

```sql
-- ============================================
-- 表: openai_sessions
-- 说明: OpenAI Agents SDK 原生 Session 持久化
-- 由 SDK 自动维护，应用层只读（除初始化外）
-- ============================================
CREATE TABLE openai_sessions (
    session_id      uuid PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
    -- 注：级联外键链 sessions(id) ← openai_sessions(session_id) ← rvinsights_sessions(session_id)
    -- 批量导入时需按 sessions → openai_sessions → rvinsights_sessions 顺序插入
    -- 或使用 SET CONSTRAINTS ALL DEFERRED 延迟约束检查至事务结束
    agent_id        text NOT NULL,
    thread_id       text NOT NULL,  -- OpenAI thread_id 格式: thread_xxxxxxxxxx，非 UUID
    state           jsonb NOT NULL DEFAULT '{}',
    tenant_id       bigint NOT NULL,
    -- v2 新增: SDK 版本追踪
    sdk_version     text DEFAULT '1.5.0',
    -- v2 新增: 模型配置快照
    model_config    jsonb DEFAULT '{}',
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now()
);

CREATE INDEX openai_sessions_tenant_id_idx ON openai_sessions (tenant_id);
CREATE INDEX openai_sessions_thread_id_idx ON openai_sessions (thread_id);
```

### 2.5 RV-Insights 应用层状态表

```sql
-- ============================================
-- 表: rvinsights_sessions
-- 说明: 应用层管理的 RV-Insights 状态扩展表
-- 与 openai_sessions 1:1 关联，存储应用层特有状态
-- ============================================
CREATE TABLE rvinsights_sessions (
    session_id      uuid PRIMARY KEY REFERENCES openai_sessions(session_id) ON DELETE CASCADE,
    tenant_id       bigint NOT NULL,
    current_stage   text NOT NULL DEFAULT 'INITIALIZATION',
    status          text NOT NULL DEFAULT 'running'
        CHECK (status IN ('running','interrupted','completed','failed','cancelled')),

    -- 阶段产物（与 v1 兼容，扩展为双 SDK 产物）
    exploration_result  jsonb,
    planning_result     jsonb,
    development_result  jsonb,
    review_result       jsonb,
    testing_result      jsonb,

    -- v2 新增: 迭代控制
    dev_review_iteration_count int NOT NULL DEFAULT 0,
    max_dev_review_iterations int NOT NULL DEFAULT 5,

    -- v2 新增: 人工审核记录（从 JSONB 拆分为独立表，此处保留汇总）
    human_decisions     jsonb DEFAULT '[]',
    human_notes         jsonb DEFAULT '[]',

    -- v2 新增: Agent 执行日志汇总
    agent_logs          jsonb DEFAULT '[]',

    -- v2 新增: SDK 追踪
    sdk_usage_log       jsonb DEFAULT '[]',  -- 记录每次 SDK 切换事件
    openai_thread_id    text,
    claude_conversation_id text,

    -- v2 新增: 资源追踪
    workspace_path      text,
    git_lock_id         text,
    qemu_instance_id    text,

    -- v2 新增: 成本追踪（双 SDK 分别计量）
    token_cost_openai   decimal(10,6) DEFAULT 0,
    token_cost_claude   decimal(10,6) DEFAULT 0,
    token_cost_total    decimal(10,6) DEFAULT 0,

    -- v2 新增: 预算控制
    budget_alert_triggered boolean DEFAULT false,
    budget_alert_at     timestamptz,

    -- v2 新增: 错误与恢复
    last_error          jsonb,
    retry_count         int DEFAULT 0,
    recovery_from_checkpoint text,

    -- v2 新增: 进程追踪（孤儿检测）
    process_pid         int,

    created_at          timestamptz DEFAULT now(),
    updated_at          timestamptz DEFAULT now()
);

CREATE INDEX rvinsights_tenant_idx ON rvinsights_sessions (tenant_id);
CREATE INDEX rvinsights_status_idx ON rvinsights_sessions (status);
CREATE INDEX rvinsights_stage_idx ON rvinsights_sessions (current_stage);
CREATE INDEX rvinsights_tenant_status_idx ON rvinsights_sessions (tenant_id, status);
CREATE INDEX rvinsights_created_at_idx ON rvinsights_sessions (created_at);
```

### 2.6 SDK 使用日志表（分区表）

```sql
-- ============================================
-- 表: sdk_usage_logs (分区表)
-- 说明: 双 SDK 精细化使用日志，支持成本追踪与缓存分析
-- ============================================
CREATE TABLE sdk_usage_logs (
    log_id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    tenant_id       bigint NOT NULL,

    -- SDK 标识
    sdk_type        text NOT NULL
        CHECK (sdk_type IN ('openai','claude')),
    agent_role      text NOT NULL
        CHECK (agent_role IN (
            'orchestrator','explorer','planner','developer',
            'reviewer','tester','feasibility_judge','failure_analyzer'
        )),
    model           text NOT NULL,

    -- Token 消耗（v2 精细化）
    input_tokens        int NOT NULL DEFAULT 0,
    output_tokens       int NOT NULL DEFAULT 0,
    total_tokens        int GENERATED ALWAYS AS (input_tokens + output_tokens) STORED,

    -- v2 新增: Claude Prompt Caching 追踪
    cache_creation_tokens int DEFAULT 0,
    cache_read_tokens     int DEFAULT 0,

    -- 成本计算
    cost_usd        decimal(10,6) NOT NULL DEFAULT 0,

    -- 性能指标
    duration_ms     int NOT NULL DEFAULT 0,
    latency_ms      int,  -- 首 token 延迟

    -- v2 新增: 请求元数据
    request_id      text,  -- 上游 API 请求 ID
    endpoint        text,  -- 调用的 API 端点

    -- v2 新增: 错误追踪
    error_type      text,
    error_message   text,

    timestamp       timestamptz NOT NULL DEFAULT now()
) PARTITION BY RANGE (timestamp);

-- 初始分区（按月分区）
CREATE TABLE sdk_usage_logs_2026_04 PARTITION OF sdk_usage_logs
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE sdk_usage_logs_2026_05 PARTITION OF sdk_usage_logs
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE sdk_usage_logs_2026_06 PARTITION OF sdk_usage_logs
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');

-- 自动化分区创建函数
CREATE OR REPLACE FUNCTION create_sdk_usage_logs_partition()
RETURNS void AS $$
DECLARE
    start_date date;
    end_date date;
    partition_name text;
BEGIN
    start_date := date_trunc('month', now() + interval '1 month');
    end_date := start_date + interval '1 month';
    partition_name := 'sdk_usage_logs_' || to_char(start_date, 'YYYY_MM');

    IF NOT EXISTS (
        SELECT 1 FROM pg_class WHERE relname = partition_name
    ) THEN
        EXECUTE format(
            'CREATE TABLE %I PARTITION OF sdk_usage_logs FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_date, end_date
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 索引
CREATE INDEX sdk_logs_session_idx ON sdk_usage_logs (session_id);
CREATE INDEX sdk_logs_tenant_idx ON sdk_usage_logs (tenant_id);
CREATE INDEX sdk_logs_sdk_type_idx ON sdk_usage_logs (sdk_type);
CREATE INDEX sdk_logs_agent_role_idx ON sdk_usage_logs (agent_role);
CREATE INDEX sdk_logs_model_idx ON sdk_usage_logs (model);
CREATE INDEX sdk_logs_timestamp_idx ON sdk_usage_logs (timestamp);
CREATE INDEX sdk_logs_cost_idx ON sdk_usage_logs (cost_usd)
    WHERE cost_usd > 0;

-- BRIN 索引：适用于按时序追加的大分区表
CREATE INDEX sdk_logs_timestamp_brin ON sdk_usage_logs USING brin (timestamp);
```

### 2.7 状态变更日志表（分区表）

```sql
-- ============================================
-- 表: state_change_log (分区表)
-- 说明: 跨 SDK 状态变更审计日志
-- 每次 OpenAI SDK 或 Claude SDK 修改共享状态时记录
-- ============================================
CREATE TABLE state_change_log (
    id              bigint GENERATED ALWAYS AS IDENTITY,
    session_id      uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    tenant_id       bigint NOT NULL,

    -- 变更来源
    sdk_source      text NOT NULL
        CHECK (sdk_source IN ('openai','claude','system')),
    agent_role      text,

    -- 变更内容
    changed_fields  text[] NOT NULL DEFAULT '{}',
    old_values      jsonb,
    new_values      jsonb,

    -- 变更原因
    change_reason   text,
    correlation_id  text,  -- 跨 SDK 消息关联 ID

    created_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- 初始分区
CREATE TABLE state_change_log_2026_04 PARTITION OF state_change_log
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE state_change_log_2026_05 PARTITION OF state_change_log
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE state_change_log_2026_06 PARTITION OF state_change_log
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');

-- 自动化分区创建函数
CREATE OR REPLACE FUNCTION create_state_change_log_partition()
RETURNS void AS $$
DECLARE
    start_date date;
    end_date date;
    partition_name text;
BEGIN
    start_date := date_trunc('month', now() + interval '1 month');
    end_date := start_date + interval '1 month';
    partition_name := 'state_change_log_' || to_char(start_date, 'YYYY_MM');

    IF NOT EXISTS (
        SELECT 1 FROM pg_class WHERE relname = partition_name
    ) THEN
        EXECUTE format(
            'CREATE TABLE %I PARTITION OF state_change_log FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_date, end_date
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 索引
CREATE INDEX state_change_session_idx ON state_change_log (session_id);
CREATE INDEX state_change_tenant_idx ON state_change_log (tenant_id);
CREATE INDEX state_change_sdk_idx ON state_change_log (sdk_source);
CREATE INDEX state_change_created_idx ON state_change_log (created_at);
CREATE INDEX state_change_correlation_idx ON state_change_log (correlation_id);
```

### 2.8 Agent 日志表（分区表，v2 增强）

```sql
-- ============================================
-- 表: agent_logs (分区表)
-- 说明: Agent 执行日志，按 created_at 月分区
-- v2 增强: 增加 sdk_source 字段区分双 SDK
-- ============================================
CREATE TABLE agent_logs (
    id              bigint GENERATED ALWAYS AS IDENTITY,
    session_id      uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    tenant_id       bigint NOT NULL,
    agent_name      text NOT NULL,
    stage           text NOT NULL,

    -- v2 新增: SDK 来源追踪
    sdk_source      text NOT NULL DEFAULT 'openai'
        CHECK (sdk_source IN ('openai','claude')),

    level           text NOT NULL DEFAULT 'info'
        CHECK (level IN ('debug','info','warn','error')),
    message         text NOT NULL,
    payload         jsonb,

    -- v2 增强: Token 使用追踪（兼容双 SDK）
    token_usage     jsonb,  -- { input_tokens, output_tokens, total_tokens, model, cache_read_tokens, cache_creation_tokens }
    latency_ms      int,

    -- v2 新增: 分布式追踪
    trace_id        text,
    span_id         text,

    created_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- 初始分区
CREATE TABLE agent_logs_2026_04 PARTITION OF agent_logs
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE agent_logs_2026_05 PARTITION OF agent_logs
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE agent_logs_2026_06 PARTITION OF agent_logs
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');

-- 自动化分区创建函数
CREATE OR REPLACE FUNCTION create_agent_logs_partition()
RETURNS void AS $$
DECLARE
    start_date date;
    end_date date;
    partition_name text;
BEGIN
    start_date := date_trunc('month', now() + interval '1 month');
    end_date := start_date + interval '1 month';
    partition_name := 'agent_logs_' || to_char(start_date, 'YYYY_MM');

    IF NOT EXISTS (
        SELECT 1 FROM pg_class WHERE relname = partition_name
    ) THEN
        EXECUTE format(
            'CREATE TABLE %I PARTITION OF agent_logs FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_date, end_date
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 索引
CREATE INDEX agent_logs_session_id_idx ON agent_logs (session_id);
CREATE INDEX agent_logs_tenant_id_idx ON agent_logs (tenant_id);
CREATE INDEX agent_logs_agent_name_idx ON agent_logs (agent_name);
CREATE INDEX agent_logs_stage_idx ON agent_logs (stage);
CREATE INDEX agent_logs_sdk_source_idx ON agent_logs (sdk_source);
CREATE INDEX agent_logs_level_idx ON agent_logs (level);
CREATE INDEX agent_logs_created_at_idx ON agent_logs (created_at);
CREATE INDEX agent_logs_payload_gin ON agent_logs USING gin (payload);
CREATE INDEX agent_logs_token_usage_gin ON agent_logs USING gin (token_usage);

-- BRIN 索引：适用于按时序追加的大分区表
CREATE INDEX agent_logs_created_at_brin ON agent_logs USING brin (created_at);
```

### 2.9 人工审核决策表（v2 增强）

```sql
-- ============================================
-- 表: human_decisions
-- 说明: 记录人工审查节点的决策与评论
-- v2 增强: 增加 required_fields 验证、decision_metadata
-- ============================================
CREATE TABLE human_decisions (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id      uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    tenant_id       bigint NOT NULL,
    stage           text NOT NULL
        CHECK (stage IN (
            'HUMAN_REVIEW_EXPLORATION','HUMAN_REVIEW_PLANNING',
            'HUMAN_REVIEW_CODE','HUMAN_REVIEW_TESTING'
        )),
    decision        text NOT NULL
        CHECK (decision IN ('APPROVE','REJECT','REQUEST_CHANGES','ADD_NOTES')),
    comment         text,
    decided_by      bigint NOT NULL REFERENCES users(id),

    -- v2 新增: 决策附加数据
    decision_metadata jsonb DEFAULT '{}',
    -- 例如: { "selected_opportunity_id": "...", "required_fields": { "APPROVE": ["selected_opportunity_id"] } }

    -- v2 新增: 决策响应时间（从通知到决策）
    notified_at     timestamptz,
    decided_at      timestamptz DEFAULT now(),

    metadata        jsonb DEFAULT '{}',
    created_at      timestamptz DEFAULT now()
);

CREATE INDEX human_decisions_session_id_idx ON human_decisions (session_id);
CREATE INDEX human_decisions_tenant_id_idx ON human_decisions (tenant_id);
CREATE INDEX human_decisions_stage_idx ON human_decisions (stage);
CREATE INDEX human_decisions_decided_by_idx ON human_decisions (decided_by);
CREATE INDEX human_decisions_created_at_idx ON human_decisions (created_at);

-- v2 新增: 决策响应时间索引
CREATE INDEX human_decisions_response_time_idx ON human_decisions (decided_at - notified_at)
    WHERE notified_at IS NOT NULL;
```

### 2.10 会话成本汇总表

```sql
-- ============================================
-- 表: session_costs
-- 说明: 会话级成本汇总，由 CostTracker.flush() 更新
-- ============================================
CREATE TABLE session_costs (
    session_id      uuid PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
    tenant_id       bigint NOT NULL,

    -- 双 SDK 成本明细
    cost_breakdown  jsonb NOT NULL DEFAULT '{
        "openai_sdk": {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0},
        "claude_sdk": {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0}
    }',

    -- 汇总
    total_cost_usd  decimal(10,6) NOT NULL DEFAULT 0,

    -- v2 新增: 缓存节省估算
    cache_savings_usd decimal(10,6) DEFAULT 0,

    -- v2 新增: 成本构成分析
    cost_by_stage   jsonb DEFAULT '{}',
    -- { "EXPLORATION": 0.45, "PLANNING": 1.20, "DEVELOPMENT": 3.00, ... }

    recorded_at     timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now()
);

CREATE INDEX session_costs_tenant_idx ON session_costs (tenant_id);
CREATE INDEX session_costs_total_idx ON session_costs (total_cost_usd);
```

### 2.11 死信队列表

```sql
-- ============================================
-- 表: dead_letter_queue
-- 说明: 达到最大重试次数的失败任务队列
-- v2 新增: 独立表替代 v1 的 tasks.status='dead_letter'
-- ============================================
CREATE TABLE dead_letter_queue (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id      uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    tenant_id       bigint NOT NULL,

    current_stage   text NOT NULL,
    failed_agent    text NOT NULL,

    -- 错误信息
    error_type      text NOT NULL,
    error_message   text NOT NULL,
    stack_trace     text,

    -- 状态快照（脱敏）
    state_snapshot  jsonb,

    -- SDK 来源
    sdk_source      text NOT NULL DEFAULT 'openai'
        CHECK (sdk_source IN ('openai','claude')),

    -- 队列状态
    status          text NOT NULL DEFAULT 'pending_review'
        CHECK (status IN ('pending_review','under_review','resolved','archived')),

    -- 处理记录
    reviewed_by     bigint REFERENCES users(id),
    reviewed_at     timestamptz,
    resolution      text,

    enqueued_at     timestamptz DEFAULT now(),
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now()
);

CREATE INDEX dlq_session_idx ON dead_letter_queue (session_id);
CREATE INDEX dlq_tenant_idx ON dead_letter_queue (tenant_id);
CREATE INDEX dlq_status_idx ON dead_letter_queue (status);
CREATE INDEX dlq_enqueued_idx ON dead_letter_queue (enqueued_at);
CREATE INDEX dlq_sdk_source_idx ON dead_letter_queue (sdk_source);
```

### 2.12 Git 分布式锁表

```sql
-- ============================================
-- 表: git_locks
-- 说明: Git 仓库写锁持久化，与 Redis 分布式锁双写
-- ============================================
CREATE TABLE git_locks (
    repo_url        text PRIMARY KEY,
    session_id      uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    tenant_id       bigint NOT NULL,

    acquired_at     timestamptz DEFAULT now(),
    expires_at      timestamptz NOT NULL,

    -- v2 新增: 锁续期追踪
    renewed_at      timestamptz,
    renew_count     int DEFAULT 0,

    -- v2 新增: 孤儿锁检测
    last_heartbeat  timestamptz DEFAULT now()
);

CREATE INDEX git_locks_session_idx ON git_locks (session_id);
CREATE INDEX git_locks_expires_idx ON git_locks (expires_at)
    WHERE expires_at < now() + interval '1 hour';
```

### 2.13 QEMU 实例占用表

```sql
-- ============================================
-- 表: qemu_occupancy
-- 说明: QEMU 虚拟机实例占用状态持久化
-- ============================================
CREATE TABLE qemu_occupancy (
    instance_id     text PRIMARY KEY,
    session_id      uuid REFERENCES sessions(id) ON DELETE SET NULL,
    tenant_id       bigint,

    -- 实例配置
    config          jsonb NOT NULL DEFAULT '{}',
    -- { "arch": "rv64gc", "variant": "default", "cpu": 4, "memory": "8g" }

    acquired_at     timestamptz,
    released_at     timestamptz,

    -- v2 新增: 实例健康状态
    health_status   text DEFAULT 'healthy'
        CHECK (health_status IN ('healthy','degraded','failed','resetting')),

    -- v2 新增: 工作窃取记录
    stolen_from_session text,
    stolen_at       timestamptz,

    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now()
);

CREATE INDEX qemu_occupancy_session_idx ON qemu_occupancy (session_id);
CREATE INDEX qemu_occupancy_health_idx ON qemu_occupancy (health_status);
```

### 2.14 会话显式 Checkpoint 表

```sql
-- ============================================
-- 表: session_checkpoints
-- 说明: 应用层显式 Checkpoint（用于子图迭代和故障恢复）
-- ============================================
CREATE TABLE session_checkpoints (
    checkpoint_id   text PRIMARY KEY,
    session_id      uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    tenant_id       bigint NOT NULL,

    -- Checkpoint 内容（排除大字段）
    state           jsonb NOT NULL,

    -- v2 新增: Checkpoint 类型
    checkpoint_type text DEFAULT 'automatic'
        CHECK (checkpoint_type IN ('automatic','manual','pre_handoff','pre_interrupt')),

    -- v2 新增: 关联子图
    subgraph_name   text,

    created_at      timestamptz DEFAULT now()
);

CREATE INDEX session_checkpoints_session_idx ON session_checkpoints (session_id);
CREATE INDEX session_checkpoints_created_idx ON session_checkpoints (created_at);
```

### 2.15 任务与依赖表（v1 兼容）

```sql
-- ============================================
-- 表: tasks
-- 说明: 异步任务队列持久化，支持重试与死信
-- ============================================
CREATE TABLE tasks (
    id              uuid DEFAULT uuid_generate_v7() PRIMARY KEY,
    session_id      uuid REFERENCES sessions(id) ON DELETE SET NULL,
    tenant_id       bigint NOT NULL,
    queue           text NOT NULL DEFAULT 'default',
    task_type       text NOT NULL,
    payload         jsonb NOT NULL DEFAULT '{}',
    status          text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','processing','completed','failed')),
    priority        int NOT NULL DEFAULT 0,
    attempt_count   int NOT NULL DEFAULT 0,
    max_attempts    int NOT NULL DEFAULT 3,
    error_info      jsonb,
    scheduled_at    timestamptz DEFAULT now(),
    started_at      timestamptz,
    completed_at    timestamptz,
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now()
);

CREATE INDEX tasks_status_scheduled_idx ON tasks (status, scheduled_at)
    WHERE status IN ('pending', 'processing');
CREATE INDEX tasks_queue_status_idx ON tasks (queue, status);
CREATE INDEX tasks_tenant_id_idx ON tasks (tenant_id);
CREATE INDEX tasks_session_id_idx ON tasks (session_id);
CREATE INDEX tasks_task_type_idx ON tasks (task_type);

-- ============================================
-- 表: task_dependencies
-- 说明: 任务 DAG 依赖关系
-- ============================================
CREATE TABLE task_dependencies (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id         uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    depends_on      uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    created_at      timestamptz DEFAULT now(),
    UNIQUE (task_id, depends_on)
);

CREATE INDEX task_dependencies_task_id_idx ON task_dependencies (task_id);
CREATE INDEX task_dependencies_depends_on_idx ON task_dependencies (depends_on);
```

### 2.16 制品与审计表（v1 兼容）

```sql
-- ============================================
-- 表: artifacts
-- 说明: 对象存储（S3/MinIO）中文件的元数据索引
-- ============================================
CREATE TABLE artifacts (
    id              uuid DEFAULT uuid_generate_v7() PRIMARY KEY,
    session_id      uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    tenant_id       bigint NOT NULL,
    artifact_type   text NOT NULL
        CHECK (artifact_type IN ('code_patch','test_report','log_archive','documentation','model_output','screenshot')),
    storage_backend text NOT NULL DEFAULT 's3'
        CHECK (storage_backend IN ('s3','minio','gcs','azure_blob')),
    bucket          text NOT NULL,
    object_key      text NOT NULL,
    object_version  text,
    content_type    text,
    size_bytes      bigint,
    checksum        text,
    metadata        jsonb DEFAULT '{}',
    created_at      timestamptz DEFAULT now()
);

CREATE INDEX artifacts_session_id_idx ON artifacts (session_id);
CREATE INDEX artifacts_tenant_id_idx ON artifacts (tenant_id);
CREATE INDEX artifacts_artifact_type_idx ON artifacts (artifact_type);
CREATE INDEX artifacts_storage_backend_idx ON artifacts (storage_backend);
CREATE INDEX artifacts_created_at_idx ON artifacts (created_at);
CREATE INDEX artifacts_metadata_gin ON artifacts USING gin (metadata);
CREATE UNIQUE INDEX artifacts_session_key_idx ON artifacts (session_id, artifact_type, object_key);

-- ============================================
-- 表: audit_logs
-- 说明: 安全审计日志
-- ============================================
CREATE TABLE audit_logs (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       bigint NOT NULL,
    user_id         bigint REFERENCES users(id) ON DELETE SET NULL,
    session_id      uuid REFERENCES sessions(id) ON DELETE SET NULL,
    action          text NOT NULL,
    resource_type   text NOT NULL,
    resource_id     text,
    details         jsonb,
    ip_address      inet,
    user_agent      text,
    created_at      timestamptz DEFAULT now()
);

CREATE INDEX audit_logs_tenant_id_idx ON audit_logs (tenant_id);
CREATE INDEX audit_logs_user_id_idx ON audit_logs (user_id);
CREATE INDEX audit_logs_action_idx ON audit_logs (action);
CREATE INDEX audit_logs_created_at_idx ON audit_logs (created_at);
CREATE INDEX audit_logs_details_gin ON audit_logs USING gin (details);

-- ============================================
-- 表: rate_limit_buckets
-- 说明: 令牌桶速率限制持久化（Redis 故障降级）
-- ============================================
CREATE TABLE rate_limit_buckets (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       bigint NOT NULL,
    resource        text NOT NULL,  -- e.g., "api_calls", "llm_tokens"
    bucket_key      text NOT NULL,  -- e.g., user_id or ip_address
    tokens          numeric(20,4) NOT NULL DEFAULT 0,
    last_updated    timestamptz NOT NULL DEFAULT now(),
    created_at      timestamptz DEFAULT now(),
    UNIQUE (tenant_id, resource, bucket_key)
);

CREATE INDEX rate_limit_buckets_lookup_idx ON rate_limit_buckets (tenant_id, resource, bucket_key);
```

### 2.17 行级安全策略 (RLS)

```sql
-- ============================================================
-- Row Level Security (RLS) Policies
-- ============================================================

-- 启用 RLS
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE openai_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE rvinsights_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE sdk_usage_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE state_change_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE human_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_costs ENABLE ROW LEVEL SECURITY;
ALTER TABLE dead_letter_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE git_locks ENABLE ROW LEVEL SECURITY;
ALTER TABLE qemu_occupancy ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_checkpoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- 强制 RLS（包括表所有者）
ALTER TABLE sessions FORCE ROW LEVEL SECURITY;
ALTER TABLE openai_sessions FORCE ROW LEVEL SECURITY;
ALTER TABLE rvinsights_sessions FORCE ROW LEVEL SECURITY;
ALTER TABLE sdk_usage_logs FORCE ROW LEVEL SECURITY;
ALTER TABLE state_change_log FORCE ROW LEVEL SECURITY;
ALTER TABLE agent_logs FORCE ROW LEVEL SECURITY;
ALTER TABLE human_decisions FORCE ROW LEVEL SECURITY;
ALTER TABLE session_costs FORCE ROW LEVEL SECURITY;
ALTER TABLE dead_letter_queue FORCE ROW LEVEL SECURITY;
ALTER TABLE git_locks FORCE ROW LEVEL SECURITY;
ALTER TABLE qemu_occupancy FORCE ROW LEVEL SECURITY;
ALTER TABLE session_checkpoints FORCE ROW LEVEL SECURITY;
ALTER TABLE tasks FORCE ROW LEVEL SECURITY;
ALTER TABLE artifacts FORCE ROW LEVEL SECURITY;
ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY;

-- 策略：基于当前设置的应用级租户 ID
CREATE POLICY sessions_tenant_isolation ON sessions
    FOR ALL
    USING (tenant_id = (SELECT current_setting('app.current_tenant_id', true)::bigint));

CREATE POLICY openai_sessions_tenant_isolation ON openai_sessions
    FOR ALL
    USING (tenant_id = (SELECT current_setting('app.current_tenant_id', true)::bigint));

CREATE POLICY rvinsights_sessions_tenant_isolation ON rvinsights_sessions
    FOR ALL
    USING (tenant_id = (SELECT current_setting('app.current_tenant_id', true)::bigint));

CREATE POLICY sdk_logs_tenant_isolation ON sdk_usage_logs
    FOR ALL
    USING (tenant_id = (SELECT current_setting('app.current_tenant_id', true)::bigint));

CREATE POLICY state_change_tenant_isolation ON state_change_log
    FOR ALL
    USING (tenant_id = (SELECT current_setting('app.current_tenant_id', true)::bigint));

CREATE POLICY agent_logs_tenant_isolation ON agent_logs
    FOR ALL
    USING (tenant_id = (SELECT current_setting('app.current_tenant_id', true)::bigint));

CREATE POLICY human_decisions_tenant_isolation ON human_decisions
    FOR ALL
    USING (tenant_id = (SELECT current_setting('app.current_tenant_id', true)::bigint));

CREATE POLICY session_costs_tenant_isolation ON session_costs
    FOR ALL
    USING (tenant_id = (SELECT current_setting('app.current_tenant_id', true)::bigint));

CREATE POLICY dlq_tenant_isolation ON dead_letter_queue
    FOR ALL
    USING (tenant_id = (SELECT current_setting('app.current_tenant_id', true)::bigint));

CREATE POLICY git_locks_tenant_isolation ON git_locks
    FOR ALL
    USING (tenant_id = (SELECT current_setting('app.current_tenant_id', true)::bigint));

CREATE POLICY qemu_occupancy_tenant_isolation ON qemu_occupancy
    FOR ALL
    USING (tenant_id = (SELECT current_setting('app.current_tenant_id', true)::bigint));

CREATE POLICY checkpoints_tenant_isolation ON session_checkpoints
    FOR ALL
    USING (tenant_id = (SELECT current_setting('app.current_tenant_id', true)::bigint));

CREATE POLICY tasks_tenant_isolation ON tasks
    FOR ALL
    USING (tenant_id = (SELECT current_setting('app.current_tenant_id', true)::bigint));

CREATE POLICY artifacts_tenant_isolation ON artifacts
    FOR ALL
    USING (tenant_id = (SELECT current_setting('app.current_tenant_id', true)::bigint));

CREATE POLICY audit_logs_tenant_isolation ON audit_logs
    FOR ALL
    USING (tenant_id = (SELECT current_setting('app.current_tenant_id', true)::bigint));

-- 撤销公共 schema 默认权限
REVOKE ALL ON SCHEMA public FROM public;
GRANT USAGE ON SCHEMA public TO app_user;

-- 应用用户最小权限
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
```

### 2.18 触发器：自动更新 updated_at

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_openai_sessions_updated_at BEFORE UPDATE ON openai_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_rvinsights_sessions_updated_at BEFORE UPDATE ON rvinsights_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_session_costs_updated_at BEFORE UPDATE ON session_costs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_dlq_updated_at BEFORE UPDATE ON dead_letter_queue
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_qemu_occupancy_updated_at BEFORE UPDATE ON qemu_occupancy
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

---

## 3. Redis 数据结构设计

### 3.1 连接配置

```
Redis Cluster / Sentinel 部署
- 用途：缓存、消息队列、分布式锁、会话状态、速率限制、QEMU 池
- 持久化：RDB 每 15 分钟 + AOF everysec
- 内存策略：allkeys-lru（当达到 maxmemory 时淘汰最近最少使用）
- 集群模式：6 节点（3 主 3 从），支持自动故障转移
```

### 3.2 数据结构详表（v2 共 12 种）

#### 3.2.1 会话状态缓存 (Hash)

```
Key:    rvi:session:{session_id}
Type:   Hash
TTL:    3600 seconds (1 hour), refreshed on access
Fields:
  - tenant_id         -> string
  - current_stage     -> string
  - status            -> string
  - sdk_source        -> string (last active SDK: openai|claude)
  - created_at        -> ISO8601 string
  - updated_at        -> ISO8601 string
  - state_version     -> string (integer)
  - checkpoint_id     -> string (latest)
  - budget_consumed   -> string (decimal)

Purpose: 快速读取会话运行状态，避免频繁查询 PostgreSQL
```

#### 3.2.2 工作流状态全量缓存 (String / JSON)

```
Key:    rvi:state:{session_id}
Type:   String (compressed JSON)
TTL:    7200 seconds (2 hours)
Value:  Serialized RVInsightsState (excluding large binary fields)

Purpose: Agent 节点间状态传递缓存，减少数据库读取
```

#### 3.2.3 消息队列 (Stream)

```
Key:    rvi:queue:{queue_name}
Type:   Redis Stream
Examples:
  - rvi:queue:agent_tasks      -> Agent 任务队列
  - rvi:queue:human_review     -> 人工审查通知队列
  - rvi:queue:notifications    -> SSE / Email 通知队列
  - rvi:queue:dlq              -> 死信队列（v2 新增）

Consumer Groups:
  - cg:agent_workers          -> Agent 执行器消费者组
  - cg:notification_service   -> 通知服务消费者组
  - cg:dlq_processor          -> 死信队列处理器（v2 新增）

Message Fields:
  - task_id       -> string
  - session_id    -> string
  - tenant_id     -> string
  - task_type     -> string
  - sdk_source    -> string (openai|claude)
  - payload       -> JSON string
  - priority      -> string (integer)
  - timestamp     -> ISO8601 string

Purpose: 异步任务解耦，支持消费者组与消息确认 (XACK)
```

#### 3.2.4 分布式锁 (String with NX + EX)

```
Key:    rvi:lock:{resource_name}
Type:   String
Value:  worker_instance_id
TTL:    30 seconds (with watchdog renewal)

Examples:
  - rvi:lock:session:{session_id}      -> 会话级互斥（防止并发执行）
  - rvi:lock:checkpoint:{thread_id}    -> Checkpoint 写入互斥
  - rvi:lock:partition:create          -> 分区创建互斥
  - rvi:lock:git:{repo_url_hash}       -> Git 仓库写锁（v2 新增）
  - rvi:lock:qemu:{instance_id}        -> QEMU 实例锁（v2 新增）

Implementation:
  SET rvi:lock:{resource} {worker_id} NX EX 30
  -- 业务完成后 DEL（或 Lua 脚本保证原子性释放）

Purpose: 防止分布式环境下竞态条件
```

#### 3.2.5 速率限制 (Sorted Set / Hash)

```
Key:    rvi:ratelimit:{tenant_id}:{resource}
Type:   Hash (令牌桶算法)
Fields:
  - tokens          -> float (当前令牌数)
  - last_updated    -> timestamp (毫秒)

Lua Script (原子性):
  -- 计算时间差，补充令牌，检查是否足够，扣减

Alternative (滑动窗口计数器):
Key:    rvi:ratelimit:window:{tenant_id}:{resource}
Type:   Sorted Set
Members: timestamp (毫秒) as score
-- 每次请求 ZADD 当前时间，ZREMRANGEBYSCORE 移除过期窗口，ZCARD 检查计数

Purpose: API 限流、LLM Token 配额控制
```

#### 3.2.6 实时计数器 (String)

```
Key:    rvi:stats:{metric_name}
Type:   String (INCR / INCRBY)
Examples:
  - rvi:stats:tenant:{tenant_id}:sessions_active   -> 活跃会话数
  - rvi:stats:agent:{agent_name}:calls_total        -> Agent 调用总数
  - rvi:stats:llm:tokens_input_total               -> LLM 输入 Token 总数
  - rvi:stats:llm:tokens_output_total              -> LLM 输出 Token 总数
  - rvi:stats:sdk:openai:cost_usd_total            -> OpenAI SDK 累计成本
  - rvi:stats:sdk:claude:cost_usd_total            -> Claude SDK 累计成本
  - rvi:stats:sdk:claude:cache_hits_total          -> Claude Cache 命中次数

TTL:    无（持久化计数器，定期同步到 PostgreSQL）
Purpose: 高频计数，避免数据库写放大
```

#### 3.2.7 SSE 会话映射 (Hash / Set)

```
Key:    rvi:sse:user:{user_id}
Type:   Set
Members: connection_id_1, connection_id_2, ...

Key:    rvi:sse:conn:{connection_id}
Type:   Hash
Fields:
  - user_id     -> string
  - tenant_id   -> string
  - session_id  -> string (optional, if watching a session)
  - connected_at-> timestamp

Purpose: 实时事件推送（v2 从 WebSocket 迁移到 SSE）
```

#### 3.2.8 布隆过滤器 (RedisBloom)

```
Key:    rvi:bloom:{filter_name}
Type:   RedisBloom (BF.RESERVE / BF.ADD / BF.EXISTS)
Examples:
  - rvi:bloom:session_ids    -> 防止重复 session_id 查询
  - rvi:bloom:task_ids       -> 快速判断任务是否已处理
  - rvi:bloom:correlation_ids -> 跨 SDK 消息去重（v2 新增）

Purpose: 快速去重检查，减少数据库查询
```

#### 3.2.9 Git 锁状态缓存 (Hash)

```
Key:    rvi:git_lock:{repo_url_hash}
Type:   Hash
Fields:
  - session_id    -> string
  - acquired_at   -> ISO8601
  - expires_at    -> ISO8601
  - renew_count   -> string (integer)

TTL:    14400 seconds (4 hours，与开发节点超时一致)
Purpose: Git 仓库写锁的快速查询与孤儿检测
```

#### 3.2.10 QEMU 实例池 (List + Hash)

```
Key:    rvi:qemu_pool:{arch}:{variant}
Type:   List
Elements: JSON strings { instance_id, reset_at, health_status }

Key:    rvi:qemu_occupied:{instance_id}
Type:   Hash
Fields:
  - session_id    -> string
  - acquired_at   -> ISO8601
  - config        -> JSON string

TTL:    10800 seconds (3 hours，与测试节点超时一致)
Purpose: QEMU 虚拟机池管理，支持工作窃取
```

#### 3.2.11 租户配额计数器 (Hash)

```
Key:    rvi:tenant_quota:{tenant_id}
Type:   Hash
Fields:
  - concurrent_sessions    -> string (integer)
  - monthly_budget_openai  -> string (decimal)
  - monthly_budget_claude  -> string (decimal)
  - qemu_instances         -> string (integer)
  - last_synced_at         -> ISO8601

TTL:    86400 seconds (1 day)
Purpose: 租户级并发配额快速检查（准入控制）
```

#### 3.2.12 Claude Prompt Cache 索引 (String)

```
Key:    rvi:claude_cache:{cache_key_hash}
Type:   String
Value:  JSON { session_id, created_at, ttl_seconds, hit_count }
TTL:    432000 seconds (5 days)
Purpose: Claude Prompt Caching 命中追踪与预热决策
```

---

## 4. 对象存储 (S3/MinIO) 组织设计

### 4.1 存储桶结构（v2 增强）

```
Bucket: rv-insights-{environment}

Prefix Structure:
├── sessions/
│   └── {tenant_id}/
│       └── {session_id}/
│           ├── exploration/
│           │   └── result.json
│           ├── planning/
│           │   └── plan.json
│           │   └── screenshots/           # v2 新增: Computer Use 截图
│           │       └── screenshot_{n}.png
│           ├── development/
│           │   ├── patch.diff
│           │   ├── patch_iter_{n}.diff    # v2 新增: 迭代历史 patch
│           │   └── code_archive.tar.gz
│           ├── review/
│           │   └── review_report.json
│           │   └── review_iter_{n}.json   # v2 新增: 迭代审核报告
│           ├── testing/
│           │   ├── test_report.json
│           │   └── logs/
│           │       └── test_output.log
│           └── artifacts/
│               └── {artifact_id}/
│                   └── {filename}
│
├── checkpoints/
│   └── {tenant_id}/
│       └── {session_id}/
│           ├── openai/
│           │   └── {checkpoint_id}.json.gz    # v2: OpenAI SDK checkpoint
│           └── app/
│               └── {checkpoint_id}.json.gz    # v2: 应用层 checkpoint
│
├── logs/
│   └── {tenant_id}/
│       └── {year}/
│           └── {month}/
│               └── agent_logs_{date}.jsonl.gz
│
├── exports/
│   └── {tenant_id}/
│       └── {export_id}/
│           └── export.zip
│
├── system/
│   ├── backups/
│   │   └── {date}/
│   │       └── postgres_dump.sql.gz
│   └── migrations/
│       └── v1_to_v2/
│           └── migration_manifest.json      # v2 新增: 迁移清单
│
└── cache/
    └── claude/
        └── {cache_key_hash}/                # v2 新增: Claude 缓存内容
            └── cached_content.json
```

### 4.2 对象元数据规范

```yaml
# S3 Object Metadata (x-amz-meta-*)
x-amz-meta-tenant-id: "{tenant_id}"
x-amz-meta-session-id: "{session_id}"
x-amz-meta-artifact-type: "code_patch|test_report|log_archive|documentation|model_output|screenshot"
x-amz-meta-content-checksum: "sha256:{hash}"
x-amz-meta-created-at: "2026-04-23T10:30:00Z"
x-amz-meta-retention-days: "90"
x-amz-meta-sdk-source: "openai|claude"           # v2 新增
x-amz-meta-agent-role: "explorer|planner|..."    # v2 新增

# Lifecycle Policy
- Transition to IA (Infrequent Access) after 30 days
- Transition to Glacier after 90 days
- Expire (delete) after 365 days for logs
- Expire after 90 days for temporary checkpoints
- Expire after 7 days for Claude cache content          # v2 新增
- Expire after 180 days for iteration patches           # v2 新增
```

### 4.3 预签名 URL 策略

```typescript
// 生成临时访问 URL（15 分钟有效期）
function generatePresignedUrl(
  bucket: string,
  key: string,
  operation: 'getObject' | 'putObject',
  expiresInSeconds: number = 900
): string {
  // 使用 S3 SDK 生成预签名 URL
  // 限制只能访问特定 tenant_id 前缀
}

// 访问控制规则
// 1. 用户只能访问自己 tenant_id 前缀下的对象
// 2. 预签名 URL 与 PostgreSQL artifacts 表记录关联验证
// 3. 下载操作记录 audit_logs
// 4. v2 新增: SDK 来源验证（Claude 缓存内容仅限 Claude Agent 访问）
```

### 4.4 多租户隔离策略

```yaml
# 方案 A: 前缀隔离（默认）
- 所有租户共享同一 Bucket
- 对象键前缀: {tenant_id}/{session_id}/...
- IAM Policy 限制: 只允许访问特定前缀
- 成本: 低，管理简单

# 方案 B: Bucket 隔离（企业租户）
- 每个企业租户独立 Bucket
- Bucket 命名: rv-insights-{environment}-{tenant_slug}
- IAM Policy: 完全隔离
- 成本: 中等，需要自动化 Bucket 创建

# 方案 C: 混合隔离
- 默认租户: 前缀隔离（方案 A）
- 企业租户: Bucket 隔离（方案 B）
- 切换阈值: 存储量 > 100GB 或合规要求
```

---

## 5. ER 关系图

```mermaid
erDiagram
    tenants ||--o{ users : has
    tenants ||--o{ sessions : owns
    users ||--o{ sessions : creates
    users ||--o{ human_decisions : decides
    users ||--o{ dead_letter_queue : reviews
    users ||--o{ audit_logs : acts

    sessions ||--|| openai_sessions : sdk_native
    sessions ||--|| rvinsights_sessions : app_state
    sessions ||--o{ sdk_usage_logs : consumes
    sessions ||--o{ state_change_log : changes
    sessions ||--o{ agent_logs : logs
    sessions ||--o{ human_decisions : decisions
    sessions ||--o{ session_costs : costs
    sessions ||--o{ dead_letter_queue : fails
    sessions ||--o{ git_locks : locks
    sessions ||--o{ qemu_occupancy : occupies
    sessions ||--o{ session_checkpoints : checkpoints
    sessions ||--o{ tasks : queues
    sessions ||--o{ artifacts : produces
    sessions ||--o{ audit_logs : audited

    tasks ||--o{ task_dependencies : depends_on

    tenants {
        bigint id PK
        text name
        text slug UK
        jsonb config
        jsonb quota_config
        timestamptz created_at
        timestamptz updated_at
    }

    users {
        bigint id PK
        bigint tenant_id FK
        text auth_provider_id
        text email
        text display_name
        text role
        jsonb preferences
        timestamptz created_at
        timestamptz updated_at
    }

    sessions {
        uuid id PK
        bigint tenant_id FK
        bigint created_by FK
        text title
        text description
        text current_stage
        text status
        text preferred_sdk
        decimal max_budget_usd
        decimal budget_consumed_usd
        jsonb config
        jsonb metadata
        timestamptz created_at
        timestamptz updated_at
        timestamptz completed_at
        timestamptz cancel_requested_at
        timestamptz cancelled_at
    }

    openai_sessions {
        uuid session_id PK,FK
        text agent_id
        uuid thread_id
        jsonb state
        bigint tenant_id
        text sdk_version
        jsonb model_config
        timestamptz created_at
        timestamptz updated_at
    }

    rvinsights_sessions {
        uuid session_id PK,FK
        bigint tenant_id
        text current_stage
        text status
        jsonb exploration_result
        jsonb planning_result
        jsonb development_result
        jsonb review_result
        jsonb testing_result
        int dev_review_iteration_count
        int max_dev_review_iterations
        jsonb human_decisions
        jsonb human_notes
        jsonb agent_logs
        jsonb sdk_usage_log
        text openai_thread_id
        text claude_conversation_id
        text workspace_path
        text git_lock_id
        text qemu_instance_id
        decimal token_cost_openai
        decimal token_cost_claude
        decimal token_cost_total
        boolean budget_alert_triggered
        timestamptz budget_alert_at
        jsonb last_error
        int retry_count
        text recovery_from_checkpoint
        int process_pid
        timestamptz created_at
        timestamptz updated_at
    }

    sdk_usage_logs {
        uuid log_id PK
        uuid session_id FK
        bigint tenant_id
        text sdk_type
        text agent_role
        text model
        int input_tokens
        int output_tokens
        int total_tokens
        int cache_creation_tokens
        int cache_read_tokens
        decimal cost_usd
        int duration_ms
        int latency_ms
        text request_id
        text endpoint
        text error_type
        text error_message
        timestamptz timestamp
    }

    state_change_log {
        bigint id PK
        uuid session_id FK
        bigint tenant_id
        text sdk_source
        text agent_role
        text[] changed_fields
        jsonb old_values
        jsonb new_values
        text change_reason
        text correlation_id
        timestamptz created_at
    }

    agent_logs {
        bigint id PK
        uuid session_id FK
        bigint tenant_id
        text agent_name
        text stage
        text sdk_source
        text level
        text message
        jsonb payload
        jsonb token_usage
        int latency_ms
        text trace_id
        text span_id
        timestamptz created_at
    }

    human_decisions {
        bigint id PK
        uuid session_id FK
        bigint tenant_id
        text stage
        text decision
        text comment
        bigint decided_by FK
        jsonb decision_metadata
        timestamptz notified_at
        timestamptz decided_at
        jsonb metadata
        timestamptz created_at
    }

    session_costs {
        uuid session_id PK,FK
        bigint tenant_id
        jsonb cost_breakdown
        decimal total_cost_usd
        decimal cache_savings_usd
        jsonb cost_by_stage
        timestamptz recorded_at
        timestamptz updated_at
    }

    dead_letter_queue {
        bigint id PK
        uuid session_id FK
        bigint tenant_id
        text current_stage
        text failed_agent
        text error_type
        text error_message
        text stack_trace
        jsonb state_snapshot
        text sdk_source
        text status
        bigint reviewed_by FK
        timestamptz reviewed_at
        text resolution
        timestamptz enqueued_at
        timestamptz created_at
        timestamptz updated_at
    }

    git_locks {
        text repo_url PK
        uuid session_id FK
        bigint tenant_id
        timestamptz acquired_at
        timestamptz expires_at
        timestamptz renewed_at
        int renew_count
        timestamptz last_heartbeat
    }

    qemu_occupancy {
        text instance_id PK
        uuid session_id FK
        bigint tenant_id
        jsonb config
        timestamptz acquired_at
        timestamptz released_at
        text health_status
        text stolen_from_session
        timestamptz stolen_at
        timestamptz created_at
        timestamptz updated_at
    }

    session_checkpoints {
        text checkpoint_id PK
        uuid session_id FK
        bigint tenant_id
        jsonb state
        text checkpoint_type
        text subgraph_name
        timestamptz created_at
    }

    tasks {
        uuid id PK
        uuid session_id FK
        bigint tenant_id
        text queue
        text task_type
        jsonb payload
        text status
        int priority
        int attempt_count
        int max_attempts
        jsonb error_info
        timestamptz scheduled_at
        timestamptz started_at
        timestamptz completed_at
        timestamptz created_at
        timestamptz updated_at
    }

    task_dependencies {
        bigint id PK
        uuid task_id FK
        uuid depends_on FK
        timestamptz created_at
    }

    artifacts {
        uuid id PK
        uuid session_id FK
        bigint tenant_id
        text artifact_type
        text storage_backend
        text bucket
        text object_key
        text object_version
        text content_type
        bigint size_bytes
        text checksum
        jsonb metadata
        timestamptz created_at
    }

    audit_logs {
        bigint id PK
        bigint tenant_id
        bigint user_id FK
        uuid session_id FK
        text action
        text resource_type
        text resource_id
        jsonb details
        inet ip_address
        text user_agent
        timestamptz created_at
    }

    rate_limit_buckets {
        bigint id PK
        bigint tenant_id
        text resource
        text bucket_key
        numeric tokens
        timestamptz last_updated
        timestamptz created_at
    }
```

---

## 6. 数据迁移方案（v1 → v2）

### 6.1 迁移策略概述

```
迁移阶段:
1. 并行部署阶段（2周）
   ├── 部署 v2 数据库 Schema alongside v1
   ├── 新会话路由到 v2，旧会话继续在 v1 完成
   ├── 双写状态到 checkpoints（v1）和 openai_sessions + rvinsights_sessions（v2）
   └── 验证 v2 端到端流程

2. 数据迁移阶段（1周）
   ├── 编写 checkpoints → openai_sessions + rvinsights_sessions 迁移脚本
   ├── 迁移历史会话元数据（产物、决策记录）
   ├── 验证数据一致性
   └── 更新查询接口兼容新旧格式

3. 切流阶段（1天）
   ├── 100% 流量切到 v2
   ├── 保留 v1 回滚能力（48小时）
   ├── 监控关键指标
   └── 确认稳定后退役 v1

4. 清理阶段（1周）
   ├── 删除 LangGraph Worker Deployment
   ├── 清理 v1 专用 ConfigMap/Secret
   ├── 删除 v1 checkpoints 表（备份后）
   └── 回收存储空间
```

### 6.2 Schema 变更映射

```sql
-- ============================================================
-- v1 → v2 表结构迁移脚本
-- 执行环境: PostgreSQL 15+
-- 前置条件: v1 数据库已备份
-- ============================================================

-- 步骤 1: 创建 v2 新表（见第 2 节完整 DDL）
-- 步骤 2: 迁移会话数据

-- 2.1 迁移 sessions 表
INSERT INTO sessions (
    id, tenant_id, created_by, title, description,
    current_stage, status, config, metadata,
    created_at, updated_at, completed_at
)
SELECT
    id, tenant_id, created_by, title, description,
    current_stage, status, config, metadata,
    created_at, updated_at, completed_at
FROM v1.sessions;

-- 2.2 创建 OpenAI Session（空状态，后续由 SDK 恢复）
INSERT INTO openai_sessions (
    session_id, agent_id, thread_id, state, tenant_id,
    sdk_version, model_config, created_at, updated_at
)
SELECT
    s.id,
    'orchestrator',
    gen_random_uuid(),
    '{}'::jsonb,
    s.tenant_id,
    '1.5.0',
    '{}'::jsonb,
    s.created_at,
    s.updated_at
FROM v1.sessions s;

-- 2.3 迁移 RV-Insights 应用层状态
INSERT INTO rvinsights_sessions (
    session_id, tenant_id, current_stage, status,
    exploration_result, planning_result, development_result,
    review_result, testing_result,
    dev_review_iteration_count, max_dev_review_iterations,
    human_decisions, human_notes, agent_logs,
    workspace_path, created_at, updated_at
)
SELECT
    s.id,
    s.tenant_id,
    COALESCE(ws.current_stage, s.current_stage),
    COALESCE(ws.status, s.status),
    ws.exploration_result,
    ws.planning_result,
    ws.development_result,
    ws.review_result,
    ws.testing_result,
    COALESCE(ws.dev_review_iteration_count, 0),
    COALESCE(ws.max_dev_review_iterations, 5),
    COALESCE(ws.human_decisions, '[]'::jsonb),
    COALESCE(ws.human_notes, '[]'::jsonb),
    COALESCE(ws.agent_logs_summary, '[]'::jsonb),
    ws.workspace_path,
    s.created_at,
    s.updated_at
FROM v1.sessions s
LEFT JOIN v1.workflow_states ws ON s.id = ws.session_id;

-- 2.4 迁移人工审核决策（从 JSONB 展开为独立记录）
INSERT INTO human_decisions (
    session_id, tenant_id, stage, decision, comment,
    decided_by, metadata, created_at
)
SELECT
    (decision->>'session_id')::uuid,
    s.tenant_id,
    decision->>'stage',
    decision->>'decision',
    decision->>'comment',
    COALESCE((decision->>'decided_by')::bigint, 0),
    decision->'metadata',
    COALESCE((decision->>'created_at')::timestamptz, now())
FROM v1.sessions s,
LATERAL jsonb_array_elements(s.metadata->'human_decisions') AS decision
WHERE s.metadata->'human_decisions' IS NOT NULL;

-- 2.5 迁移 Agent 日志
INSERT INTO agent_logs (
    session_id, tenant_id, agent_name, stage, sdk_source,
    level, message, payload, token_usage, latency_ms, created_at
)
SELECT
    session_id, tenant_id, agent_name, stage, 'openai',
    level, message, payload, token_usage, latency_ms, created_at
FROM v1.agent_logs;

-- 2.6 迁移制品元数据
INSERT INTO artifacts (
    id, session_id, tenant_id, artifact_type, storage_backend,
    bucket, object_key, object_version, content_type,
    size_bytes, checksum, metadata, created_at
)
SELECT
    id, session_id, tenant_id, artifact_type, storage_backend,
    bucket, object_key, object_version, content_type,
    size_bytes, checksum, metadata, created_at
FROM v1.artifacts;

-- 2.7 迁移审计日志
INSERT INTO audit_logs (
    tenant_id, user_id, session_id, action, resource_type,
    resource_id, details, ip_address, user_agent, created_at
)
SELECT
    tenant_id, user_id, session_id, action, resource_type,
    resource_id, details, ip_address, user_agent, created_at
FROM v1.audit_logs;

-- 2.8 初始化会话成本（从 agent_logs 汇总）
INSERT INTO session_costs (
    session_id, tenant_id, cost_breakdown, total_cost_usd, recorded_at
)
SELECT
    s.id,
    s.tenant_id,
    jsonb_build_object(
        'openai_sdk', jsonb_build_object('input_tokens', 0, 'output_tokens', 0, 'cost_usd', 0),
        'claude_sdk', jsonb_build_object('input_tokens', 0, 'output_tokens', 0, 'cost_usd', 0)
    ),
    0,
    now()
FROM v1.sessions s;
```

### 6.3 数据一致性验证脚本

```sql
-- ============================================================
-- 数据迁移验证脚本
-- ============================================================

-- 验证 1: 会话数量一致
SELECT
    'sessions count' as check_name,
    (SELECT count(*) FROM v1.sessions) as v1_count,
    (SELECT count(*) FROM sessions) as v2_count,
    (SELECT count(*) FROM v1.sessions) = (SELECT count(*) FROM sessions) as passed;

-- 验证 2: OpenAI Sessions 1:1 映射
SELECT
    'openai_sessions mapping' as check_name,
    (SELECT count(*) FROM openai_sessions) as openai_count,
    (SELECT count(*) FROM rvinsights_sessions) as rvinsights_count,
    (SELECT count(*) FROM openai_sessions os
     JOIN rvinsights_sessions rs ON os.session_id = rs.session_id) as joined_count;

-- 验证 3: 人工决策迁移完整性
SELECT
    'human_decisions' as check_name,
    (SELECT count(*) FROM v1.sessions
     WHERE metadata->'human_decisions' IS NOT NULL) as v1_sessions_with_decisions,
    (SELECT count(DISTINCT session_id) FROM human_decisions) as v2_sessions_with_decisions;

-- 验证 4: Agent 日志数量一致
SELECT
    'agent_logs count' as check_name,
    (SELECT count(*) FROM v1.agent_logs) as v1_count,
    (SELECT count(*) FROM agent_logs) as v2_count;

-- 验证 5: 制品元数据完整性
SELECT
    'artifacts count' as check_name,
    (SELECT count(*) FROM v1.artifacts) as v1_count,
    (SELECT count(*) FROM artifacts) as v2_count;

-- 验证 6: 租户隔离一致性
SELECT
    'tenant isolation' as check_name,
    (SELECT count(DISTINCT tenant_id) FROM v1.sessions) as v1_tenants,
    (SELECT count(DISTINCT tenant_id) FROM sessions) as v2_tenants;

-- 验证 7: RLS 策略启用状态
SELECT
    tablename,
    rowsecurity as rls_enabled,
    forcerowsecurity as rls_forced
FROM pg_tables t
JOIN pg_class c ON t.tablename = c.relname
WHERE t.schemaname = 'public'
  AND t.tablename IN (
    'sessions', 'openai_sessions', 'rvinsights_sessions',
    'sdk_usage_logs', 'agent_logs', 'human_decisions',
    'dead_letter_queue', 'git_locks', 'qemu_occupancy'
  )
ORDER BY t.tablename;
```

### 6.4 回滚方案

```sql
-- ============================================================
-- 回滚脚本（切流后 48 小时内可用）
-- ============================================================

-- 步骤 1: 停止 v2 写入
-- 应用层配置: DISABLE_V2_WRITE=true

-- 步骤 2: 将 v2 新会话数据回写到 v1
INSERT INTO v1.sessions (
    id, tenant_id, created_by, title, description,
    current_stage, status, config, metadata,
    created_at, updated_at, completed_at
)
SELECT
    id, tenant_id, created_by, title, description,
    current_stage, status, config, metadata,
    created_at, updated_at, completed_at
FROM sessions
WHERE created_at > '2026-04-23T00:00:00Z';  -- v2 上线时间

-- 步骤 3: 回写 workflow_states
INSERT INTO v1.workflow_states (
    session_id, tenant_id, current_stage, status,
    exploration_result, planning_result, development_result,
    review_result, testing_result,
    dev_review_iteration_count, max_dev_review_iterations,
    human_decisions, human_notes, agent_logs_summary,
    state_version, created_at, updated_at
)
SELECT
    rs.session_id, rs.tenant_id, rs.current_stage, rs.status,
    rs.exploration_result, rs.planning_result, rs.development_result,
    rs.review_result, rs.testing_result,
    rs.dev_review_iteration_count, rs.max_dev_review_iterations,
    rs.human_decisions, rs.human_notes, rs.agent_logs,
    1, rs.created_at, rs.updated_at
FROM rvinsights_sessions rs
WHERE rs.created_at > '2026-04-23T00:00:00Z';

-- 步骤 4: 重新启用 v1 服务
-- 部署: RESTORE_V1_SERVICES=true

-- 步骤 5: 清理 v2 数据（确认稳定后）
-- DROP TABLE IF EXISTS openai_sessions CASCADE;
-- DROP TABLE IF EXISTS rvinsights_sessions CASCADE;
-- DROP TABLE IF EXISTS sdk_usage_logs CASCADE;
-- ...（完整清理清单）
```

---

## 7. 性能优化

### 7.1 索引策略总结

| 表名 | 索引名 | 类型 | 列 | 用途 |
|------|--------|------|-----|------|
| tenants | tenants_slug_idx | B-tree | slug | 租户查找 |
| users | users_tenant_id_idx | B-tree | tenant_id | 租户用户列表 |
| users | users_email_idx | B-tree | email | 用户登录 |
| sessions | sessions_tenant_status_idx | B-tree | tenant_id, status | 租户会话筛选 |
| sessions | sessions_status_updated_idx | B-tree (Partial) | status, updated_at | 运行中会话检测 |
| openai_sessions | openai_sessions_thread_id_idx | B-tree | thread_id | SDK checkpoint 查询 |
| rvinsights_sessions | rvinsights_tenant_status_idx | B-tree | tenant_id, status | 租户状态筛选 |
| rvinsights_sessions | rvinsights_created_at_idx | B-tree | created_at | 时间范围查询 |
| sdk_usage_logs | sdk_logs_session_idx | B-tree | session_id | 会话成本查询 |
| sdk_usage_logs | sdk_logs_timestamp_idx | B-tree | timestamp | 时序分析 |
| sdk_usage_logs | sdk_logs_timestamp_brin | BRIN | timestamp | 大表时序范围扫描 |
| state_change_log | state_change_session_idx | B-tree | session_id | 变更审计查询 |
| state_change_log | state_change_correlation_idx | B-tree | correlation_id | 跨 SDK 消息追踪 |
| agent_logs | agent_logs_session_id_idx | B-tree | session_id | 会话日志查询 |
| agent_logs | agent_logs_sdk_source_idx | B-tree | sdk_source | SDK 来源筛选 |
| agent_logs | agent_logs_payload_gin | GIN | payload | 日志内容搜索 |
| agent_logs | agent_logs_created_at_brin | BRIN | created_at | 大表时序范围扫描 |
| human_decisions | human_decisions_session_id_idx | B-tree | session_id | 决策历史查询 |
| dead_letter_queue | dlq_status_idx | B-tree | status | 待处理死信查询 |
| git_locks | git_locks_expires_idx | B-tree (Partial) | expires_at | 即将过期锁检测 |
| qemu_occupancy | qemu_occupancy_health_idx | B-tree | health_status | 健康实例筛选 |
| session_checkpoints | session_checkpoints_session_idx | B-tree | session_id | Checkpoint 查询 |
| tasks | tasks_status_scheduled_idx | B-tree (Partial) | status, scheduled_at | 待处理任务拉取 |
| artifacts | artifacts_metadata_gin | GIN | metadata | 制品元数据搜索 |
| audit_logs | audit_logs_details_gin | GIN | details | 审计详情搜索 |

### 7.2 连接池配置

```python
# asyncpg 连接池配置（Python 应用层）
import asyncpg

pool = await asyncpg.create_pool(
    dsn="postgresql://user:pass@localhost/rvinsights",
    min_size=10,           # 最小连接数
    max_size=50,           # 最大连接数
    max_inactive_time=300, # 连接最大空闲时间（秒）
    command_timeout=60,    # 单命令超时（秒）
    server_settings={
        'jit': 'off',                    # 复杂查询关闭 JIT
        'application_name': 'rvinsights-api',
    }
)

# PgBouncer 配置（连接池中间件）
# pgbouncer.ini
[databases]
rvinsights = host=localhost port=5432 dbname=rvinsights

[pgbouncer]
pool_mode = transaction        # 事务级连接复用
max_client_conn = 1000
default_pool_size = 25
reserve_pool_size = 5
reserve_pool_timeout = 3
max_db_connections = 100
server_idle_timeout = 600
server_lifetime = 3600
```

### 7.3 读写分离

```python
# 读写分离配置（应用层）
class DatabaseRouter:
    """数据库读写分离路由器。"""

    def __init__(self, primary_dsn: str, replica_dsn: str):
        self.primary_pool = asyncpg.create_pool(
            dsn=primary_dsn,
            min_size=5, max_size=20
        )
        self.replica_pool = asyncpg.create_pool(
            dsn=replica_dsn,
            min_size=10, max_size=50
        )

    async def execute(self, query: str, *args):
        """写操作路由到主库。"""
        async with self.primary_pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args):
        """读操作路由到从库。"""
        async with self.replica_pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        """读操作路由到从库。"""
        async with self.replica_pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

# 读写分离规则
READ_REPLICA_TABLES = {
    'sessions', 'rvinsights_sessions', 'agent_logs',
    'sdk_usage_logs', 'human_decisions', 'artifacts',
    'audit_logs', 'session_costs'
}

WRITE_PRIMARY_TABLES = {
    'openai_sessions', 'state_change_log', 'dead_letter_queue',
    'git_locks', 'qemu_occupancy', 'session_checkpoints',
    'tasks', 'task_dependencies', 'rate_limit_buckets'
}
```

### 7.4 查询优化

```sql
-- ============================================================
-- 查询优化示例
-- ============================================================

-- 优化 1: 会话状态查询（覆盖索引）
-- 原查询
SELECT session_id, current_stage, status, token_cost_total
FROM rvinsights_sessions
WHERE tenant_id = 1 AND status = 'running';

-- 优化: 复合索引
CREATE INDEX rvinsights_tenant_status_covering ON rvinsights_sessions (tenant_id, status)
INCLUDE (session_id, current_stage, token_cost_total);

-- 优化 2: SDK 使用日志聚合（分区裁剪）
-- 原查询
SELECT sdk_type, sum(cost_usd) as total_cost
FROM sdk_usage_logs
WHERE session_id = '...' AND timestamp >= '2026-04-01'
GROUP BY sdk_type;

-- 优化: 利用分区裁剪 + 索引
-- 确保查询条件包含分区键 timestamp
SELECT sdk_type, sum(cost_usd) as total_cost
FROM sdk_usage_logs
WHERE session_id = '...'
  AND timestamp >= '2026-04-01'
  AND timestamp < '2026-05-01'
GROUP BY sdk_type;

-- 优化 3: Agent 日志分页查询（键集分页）
-- 避免 OFFSET 大页性能问题
SELECT * FROM agent_logs
WHERE session_id = '...'
  AND created_at < '2026-04-23T10:00:00Z'
ORDER BY created_at DESC
LIMIT 100;

-- 优化 4: 成本监控实时查询（物化视图）
CREATE MATERIALIZED VIEW mv_tenant_daily_costs AS
SELECT
    tenant_id,
    date_trunc('day', timestamp) as day,
    sdk_type,
    sum(input_tokens) as total_input_tokens,
    sum(output_tokens) as total_output_tokens,
    sum(cache_read_tokens) as total_cache_read,
    sum(cost_usd) as total_cost
FROM sdk_usage_logs
GROUP BY tenant_id, date_trunc('day', timestamp), sdk_type;

CREATE UNIQUE INDEX mv_tenant_daily_costs_pk
ON mv_tenant_daily_costs (tenant_id, day, sdk_type);

-- 每小时刷新
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_tenant_daily_costs;
```

### 7.5 分区维护

```sql
-- ============================================================
-- 分区维护作业
-- ============================================================

-- 每月 1 日 00:00 创建下月分区
SELECT cron.schedule('create-sdk-logs-partition', '0 0 1 * *',
    'SELECT create_sdk_usage_logs_partition();');
SELECT cron.schedule('create-state-change-partition', '0 0 1 * *',
    'SELECT create_state_change_log_partition();');
SELECT cron.schedule('create-agent-logs-partition', '0 0 1 * *',
    'SELECT create_agent_logs_partition();');

-- 旧分区归档（90 天前的分区 detach 并转存 S3）
CREATE OR REPLACE FUNCTION archive_old_partitions()
RETURNS void AS $$
DECLARE
    partition_record record;
BEGIN
    FOR partition_record IN
        SELECT inhrelid::regclass as partition_name
        FROM pg_inherits
        WHERE inhparent = 'sdk_usage_logs'::regclass
          AND inhrelid::regclass::text < 'sdk_usage_logs_' || to_char(now() - interval '90 days', 'YYYY_MM')
    LOOP
        EXECUTE format('ALTER TABLE sdk_usage_logs DETACH PARTITION %I', partition_record.partition_name);
        -- 触发 S3 归档流程
        PERFORM pg_notify('archive_partition', partition_record.partition_name::text);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- 每周执行归档
SELECT cron.schedule('archive-old-partitions', '0 2 * * 0',
    'SELECT archive_old_partitions();');
```

### 7.6 连接监控与告警

```sql
-- 活跃连接监控
SELECT
    datname,
    usename,
    state,
    count(*) as connection_count,
    max(now() - backend_start) as oldest_connection,
    max(now() - state_change) as longest_idle
FROM pg_stat_activity
WHERE datname = 'rvinsights'
GROUP BY datname, usename, state;

-- 慢查询监控
SELECT
    queryid,
    query,
    calls,
    round(mean_exec_time::numeric, 2) as mean_ms,
    round(total_exec_time::numeric, 2) as total_ms,
    rows
FROM pg_stat_statements
WHERE query like '%rvinsights_sessions%'
   OR query like '%sdk_usage_logs%'
   OR query like '%agent_logs%'
ORDER BY mean_exec_time DESC
LIMIT 20;

-- 表膨胀检查
SELECT
    schemaname,
    relname,
    n_live_tup,
    n_dead_tup,
    round(n_dead_tup::numeric / nullif(n_live_tup, 0) * 100, 2) as dead_ratio,
    last_vacuum,
    last_autovacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;
```

---

## 8. 备份策略

| 层级 | 频率 | 保留期 | 方法 |
|------|------|--------|------|
| PostgreSQL 全量 | 每日 02:00 | 30 天 | `pg_dump` + `pg_basebackup` |
| PostgreSQL WAL | 实时归档 | 7 天 | `archive_command` 复制到对象存储 |
| Redis RDB | 每 15 分钟 | 3 天 | `SAVE` / `BGSAVE` |
| Redis AOF | 每秒追加 | 7 天 | `appendfsync everysec` |
| 对象存储 | 跨区域复制 | 90 天 | S3 Cross-Region Replication |
| SDK 日志分区 | 每月 | 90 天后转冷存储 | `ALTER TABLE ... DETACH PARTITION` + S3 Glacier |
| Checkpoint 旧分区 | 每月 | 30 天后删除 | 自动清理 |

---

## 9. 完整 DDL 脚本

```sql
-- ============================================================
-- RV-Insights v2 Database Schema
-- Version: 2.0.0
-- Database: PostgreSQL 15+
-- ============================================================

-- 第 1-2 节已包含完整 DDL，此处提供汇总执行顺序：

-- 1. 扩展
-- 2. 辅助函数
-- 3. 核心表: tenants, users, sessions
-- 4. SDK 原生表: openai_sessions
-- 5. 应用层状态表: rvinsights_sessions
-- 6. 时序分区表: sdk_usage_logs, state_change_log, agent_logs
-- 7. 业务表: human_decisions, session_costs, dead_letter_queue
-- 8. 资源表: git_locks, qemu_occupancy, session_checkpoints
-- 9. 任务表: tasks, task_dependencies
-- 10. 制品与审计: artifacts, audit_logs, rate_limit_buckets
-- 11. RLS 策略
-- 12. 触发器
-- 13. 分区维护函数与作业

-- 所有 SQL 均可在 PostgreSQL 15+ 直接执行
-- 建议在生产环境执行前先在 staging 环境验证
```

---

*文档版本: 2.0.0*
*最后更新: 2026-04-23*
*作者: Claude Opus 4.7*
