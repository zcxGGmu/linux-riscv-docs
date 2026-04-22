# RV-Insights: 数据持久化方案深度设计

**版本**: v1.0  
**日期**: 2026-04-21  
**定位**: 本文档是 `rv-insights-design.md` 第 8 章（数据持久化与可观测性）的细化与扩展，覆盖完整数据库Schema、Redis结构、对象存储规范及会话恢复机制。

---

## 1. 概述

本文档定义 RV-Insights 平台完整的数据持久化架构，涵盖 PostgreSQL 主存储、Redis 缓存与消息队列、对象存储分层，以及基于 LangGraph Checkpointer 的会话恢复机制。

核心设计目标：
- **多租户隔离**：通过 PostgreSQL RLS + `tenant_id` 列实现逻辑隔离。
- **高可扩展性**：时序表（checkpoints, agent_logs）按时间范围分区；JSONB 列配合 GIN 索引支持灵活查询。
- **工作流一致性**：利用 LangGraph Checkpoint 机制实现状态机原子持久化，支持 Human-in-the-Loop 中断与恢复。
- **性能优化**：B-tree 覆盖索引、复合索引、部分索引、BRIN 索引针对大表时序查询。

---

## 2. PostgreSQL 完整 Schema 设计

### 2.1 扩展与配置

```sql
-- 启用必要扩展
CREATE EXTENSION IF NOT EXISTS "pgcrypto";       -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pg_uuidv7";      -- UUIDv7 时序排序
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements"; -- 查询性能监控
CREATE EXTENSION IF NOT EXISTS "btree_gin";      -- GIN 支持复合类型

-- 配置连接与性能参数（根据部署环境调整）
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET idle_in_transaction_session_timeout = '30s';
ALTER SYSTEM SET idle_session_timeout = '10min';
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
    role            text NOT NULL DEFAULT 'member' CHECK (role IN ('admin','member','viewer')),
    preferences     jsonb DEFAULT '{}',
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now(),
    UNIQUE (tenant_id, email)
);

CREATE INDEX users_tenant_id_idx ON users (tenant_id);
CREATE INDEX users_email_idx ON users (email);

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
        CHECK (status IN ('running','interrupted','completed','failed')),
    config          jsonb DEFAULT '{}',
    metadata        jsonb DEFAULT '{}',
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now(),
    completed_at    timestamptz
);

CREATE INDEX sessions_tenant_id_idx ON sessions (tenant_id);
CREATE INDEX sessions_tenant_status_idx ON sessions (tenant_id, status);
CREATE INDEX sessions_created_by_idx ON sessions (created_by);
CREATE INDEX sessions_current_stage_idx ON sessions (current_stage);
CREATE INDEX sessions_created_at_idx ON sessions (created_at);
```

### 2.3 LangGraph Checkpoint 表（分区表）

```sql
-- ============================================
-- 表: checkpoints (分区表)
-- 说明: LangGraph 状态快照，按 created_at 月分区
-- ============================================
CREATE TABLE checkpoints (
    thread_id           uuid NOT NULL,       -- 与 session_id 同值，LangGraph 分区键
    checkpoint_ns       text NOT NULL DEFAULT '',
    checkpoint_id       text NOT NULL,
    parent_checkpoint_id text,
    type                text,
    checkpoint          jsonb NOT NULL,
    metadata            jsonb,
    tenant_id           bigint NOT NULL,
    session_id          uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    created_at          timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, created_at)
) PARTITION BY RANGE (created_at);

-- 确保一个 session_id 只对应一个 thread_id（1:1 映射）
CREATE UNIQUE INDEX checkpoints_session_id_idx ON checkpoints (session_id);

-- 创建初始分区（示例：2024-2025）
CREATE TABLE checkpoints_2024_01 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE checkpoints_2024_02 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
CREATE TABLE checkpoints_2024_03 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');
CREATE TABLE checkpoints_2024_04 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');
CREATE TABLE checkpoints_2024_05 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-05-01') TO ('2024-06-01');
CREATE TABLE checkpoints_2024_06 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-06-01') TO ('2024-07-01');
CREATE TABLE checkpoints_2024_07 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-07-01') TO ('2024-08-01');
CREATE TABLE checkpoints_2024_08 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');
CREATE TABLE checkpoints_2024_09 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-09-01') TO ('2024-10-01');
CREATE TABLE checkpoints_2024_10 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');
CREATE TABLE checkpoints_2024_11 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
CREATE TABLE checkpoints_2024_12 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');
CREATE TABLE checkpoints_2025_01 PARTITION OF checkpoints
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- 自动化分区创建函数
CREATE OR REPLACE FUNCTION create_checkpoint_partition()
RETURNS void AS $$
DECLARE
    start_date date;
    end_date date;
    partition_name text;
BEGIN
    start_date := date_trunc('month', now() + interval '1 month');
    end_date := start_date + interval '1 month';
    partition_name := 'checkpoints_' || to_char(start_date, 'YYYY_MM');

    IF NOT EXISTS (
        SELECT 1 FROM pg_class WHERE relname = partition_name
    ) THEN
        EXECUTE format(
            'CREATE TABLE %I PARTITION OF checkpoints FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_date, end_date
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 索引
CREATE INDEX checkpoints_session_id_idx ON checkpoints (session_id);
CREATE INDEX checkpoints_tenant_id_idx ON checkpoints (tenant_id);
CREATE INDEX checkpoints_thread_id_idx ON checkpoints (thread_id);
CREATE INDEX checkpoints_created_at_idx ON checkpoints (created_at);
CREATE INDEX checkpoints_metadata_gin ON checkpoints USING gin (metadata);
```

### 2.4 工作流状态快照表

```sql
-- ============================================
-- 表: workflow_states
-- 说明: 反规范化存储 RVInsightsState 关键字段，便于快速查询
-- ============================================
CREATE TABLE workflow_states (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id          uuid NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
    tenant_id           bigint NOT NULL,
    current_stage       text NOT NULL,
    status              text NOT NULL,
    exploration_result  jsonb,
    planning_result     jsonb,
    development_result  jsonb,
    review_result       jsonb,
    testing_result      jsonb,
    dev_review_iteration_count int NOT NULL DEFAULT 0,
    max_dev_review_iterations int NOT NULL DEFAULT 5,
    human_decisions     jsonb DEFAULT '[]',
    human_notes         jsonb DEFAULT '[]',
    agent_logs_summary  jsonb DEFAULT '[]',
    timestamps          jsonb DEFAULT '[]',
    state_version       int NOT NULL DEFAULT 1,
    created_at          timestamptz DEFAULT now(),
    updated_at          timestamptz DEFAULT now()
);

CREATE INDEX workflow_states_session_id_idx ON workflow_states (session_id);
CREATE INDEX workflow_states_tenant_id_idx ON workflow_states (tenant_id);
CREATE INDEX workflow_states_current_stage_idx ON workflow_states (current_stage);
CREATE INDEX workflow_states_status_idx ON workflow_states (status);
CREATE INDEX workflow_states_exploration_gin ON workflow_states USING gin (exploration_result);
CREATE INDEX workflow_states_planning_gin ON workflow_states USING gin (planning_result);
```

### 2.5 Human-in-the-Loop 决策表

```sql
-- ============================================
-- 表: human_decisions
-- 说明: 记录人工审查节点的决策与评论
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
    metadata        jsonb DEFAULT '{}',
    created_at      timestamptz DEFAULT now()
);

CREATE INDEX human_decisions_session_id_idx ON human_decisions (session_id);
CREATE INDEX human_decisions_tenant_id_idx ON human_decisions (tenant_id);
CREATE INDEX human_decisions_stage_idx ON human_decisions (stage);
CREATE INDEX human_decisions_decided_by_idx ON human_decisions (decided_by);
CREATE INDEX human_decisions_created_at_idx ON human_decisions (created_at);
```

### 2.6 Agent 日志表（分区表）

```sql
-- ============================================
-- 表: agent_logs (分区表)
-- 说明: Agent 执行日志，按 created_at 月分区
-- ============================================
CREATE TABLE agent_logs (
    id              bigint GENERATED ALWAYS AS IDENTITY,
    session_id      uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    tenant_id       bigint NOT NULL,
    agent_name      text NOT NULL,
    stage           text NOT NULL,
    level           text NOT NULL DEFAULT 'info' CHECK (level IN ('debug','info','warn','error')),
    message         text NOT NULL,
    payload         jsonb,
    token_usage     jsonb,  -- { input_tokens, output_tokens, total_tokens, model }
    latency_ms      int,
    created_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- 初始分区
CREATE TABLE agent_logs_2024_01 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE agent_logs_2024_02 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
CREATE TABLE agent_logs_2024_03 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');
CREATE TABLE agent_logs_2024_04 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');
CREATE TABLE agent_logs_2024_05 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-05-01') TO ('2024-06-01');
CREATE TABLE agent_logs_2024_06 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-06-01') TO ('2024-07-01');
CREATE TABLE agent_logs_2024_07 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-07-01') TO ('2024-08-01');
CREATE TABLE agent_logs_2024_08 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');
CREATE TABLE agent_logs_2024_09 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-09-01') TO ('2024-10-01');
CREATE TABLE agent_logs_2024_10 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');
CREATE TABLE agent_logs_2024_11 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
CREATE TABLE agent_logs_2024_12 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');
CREATE TABLE agent_logs_2025_01 PARTITION OF agent_logs
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

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
CREATE INDEX agent_logs_level_idx ON agent_logs (level);
CREATE INDEX agent_logs_created_at_idx ON agent_logs (created_at);
CREATE INDEX agent_logs_payload_gin ON agent_logs USING gin (payload);
CREATE INDEX agent_logs_token_usage_gin ON agent_logs USING gin (token_usage);

-- BRIN 索引：适用于按时序追加的大分区表
CREATE INDEX agent_logs_created_at_brin ON agent_logs USING brin (created_at);
```

### 2.7 任务与队列表

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
        CHECK (status IN ('pending','processing','completed','failed','dead_letter')),
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

### 2.8 制品与对象存储元数据表

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
        CHECK (artifact_type IN ('code_patch','test_report','log_archive','documentation','model_output')),
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

-- 唯一约束：同一 session 同一类型同一 key 不重复
CREATE UNIQUE INDEX artifacts_session_key_idx ON artifacts (session_id, artifact_type, object_key);
```

### 2.9 审计与速率限制表

```sql
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

### 2.10 行级安全策略 (RLS)

```sql
-- 启用 RLS
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE human_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE checkpoints ENABLE ROW LEVEL SECURITY;

-- 强制 RLS（包括表所有者）
ALTER TABLE sessions FORCE ROW LEVEL SECURITY;
ALTER TABLE workflow_states FORCE ROW LEVEL SECURITY;
ALTER TABLE human_decisions FORCE ROW LEVEL SECURITY;
ALTER TABLE agent_logs FORCE ROW LEVEL SECURITY;
ALTER TABLE tasks FORCE ROW LEVEL SECURITY;
ALTER TABLE artifacts FORCE ROW LEVEL SECURITY;
ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY;
ALTER TABLE checkpoints FORCE ROW LEVEL SECURITY;

-- 策略：基于当前设置的应用级用户 ID（适用于应用连接池模式）
-- 使用 (SELECT current_setting('app.current_tenant_id', true)::bigint) 获取当前租户

CREATE POLICY sessions_tenant_isolation ON sessions
    FOR ALL
    USING (tenant_id = (SELECT current_setting('app.current_tenant_id', true)::bigint));

CREATE POLICY workflow_states_tenant_isolation ON workflow_states
    FOR ALL
    USING (tenant_id = (SELECT current_setting('app.current_tenant_id', true)::bigint));

CREATE POLICY human_decisions_tenant_isolation ON human_decisions
    FOR ALL
    USING (tenant_id = (SELECT current_setting('app.current_tenant_id', true)::bigint));

CREATE POLICY agent_logs_tenant_isolation ON agent_logs
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

CREATE POLICY checkpoints_tenant_isolation ON checkpoints
    FOR ALL
    USING (tenant_id = (SELECT current_setting('app.current_tenant_id', true)::bigint));

-- 撤销公共 schema 默认权限
REVOKE ALL ON SCHEMA public FROM public;
GRANT USAGE ON SCHEMA public TO app_user;

-- 应用用户最小权限
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
```

### 2.11 触发器：自动更新 updated_at

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
CREATE TRIGGER update_workflow_states_updated_at BEFORE UPDATE ON workflow_states
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

---

## 3. Redis 数据结构设计

### 3.1 连接配置

```
Redis Cluster / Sentinel 部署
- 用途：缓存、消息队列、分布式锁、会话状态、速率限制
- 持久化：RDB 每 15 分钟 + AOF everysec
- 内存策略：allkeys-lru（当达到 maxmemory 时淘汰最近最少使用）
```

### 3.2 数据结构详表

#### 3.2.1 会话状态缓存 (Hash)

```
Key:    rv:session:{session_id}
Type:   Hash
TTL:    3600 seconds (1 hour), refreshed on access
Fields:
  - tenant_id         -> string
  - current_stage     -> string
  - status            -> string
  - created_at        -> ISO8601 string
  - updated_at        -> ISO8601 string
  - state_version     -> string (integer)
  - checkpoint_id     -> string (latest)

Purpose: 快速读取会话运行状态，避免频繁查询 PostgreSQL
```

#### 3.2.2 工作流状态全量缓存 (String / JSON)

```
Key:    rv:state:{session_id}
Type:   String (compressed JSON)
TTL:    7200 seconds (2 hours)
Value:  Serialized RVInsightsState (excluding large binary fields)

Purpose: LangGraph 节点间状态传递缓存，减少 Checkpoint 表读取
```

#### 3.2.3 消息队列 (Stream)

```
Key:    rv:queue:{queue_name}
Type:   Redis Stream
Examples:
  - rv:queue:agent_tasks      -> Agent 任务队列
  - rv:queue:human_review     -> 人工审查通知队列
  - rv:queue:notifications    -> WebSocket / Email 通知队列

Consumer Groups:
  - cg:agent_workers          -> Agent 执行器消费者组
  - cg:notification_service   -> 通知服务消费者组

Message Fields:
  - task_id       -> string
  - session_id    -> string
  - tenant_id     -> string
  - task_type     -> string
  - payload       -> JSON string
  - priority      -> string (integer)
  - timestamp     -> ISO8601 string

Purpose: 异步任务解耦，支持消费者组与消息确认 (XACK)
```

#### 3.2.4 分布式锁 (String with NX + EX)

```
Key:    rv:lock:{resource_name}
Type:   String
Value:  worker_instance_id
TTL:    30 seconds (with watchdog renewal)

Examples:
  - rv:lock:session:{session_id}      -> 会话级互斥（防止并发执行）
  - rv:lock:checkpoint:{thread_id}    -> Checkpoint 写入互斥
  - rv:lock:partition:create          -> 分区创建互斥

Implementation:
  SET rv:lock:{resource} {worker_id} NX EX 30
  -- 业务完成后 DEL（或 Lua 脚本保证原子性释放）

Purpose: 防止分布式环境下竞态条件
```

#### 3.2.5 速率限制 (Sorted Set / Hash)

```
Key:    rv:ratelimit:{tenant_id}:{resource}
Type:   Hash (令牌桶算法)
Fields:
  - tokens          -> float (当前令牌数)
  - last_updated    -> timestamp (毫秒)

Lua Script (原子性):
  -- 计算时间差，补充令牌，检查是否足够，扣减

Alternative (滑动窗口计数器):
Key:    rv:ratelimit:window:{tenant_id}:{resource}
Type:   Sorted Set
Members: timestamp (毫秒) as score
-- 每次请求 ZADD 当前时间，ZREMRANGEBYSCORE 移除过期窗口，ZCARD 检查计数

Purpose: API 限流、LLM Token 配额控制
```

#### 3.2.6 实时计数器 (HyperLogLog / Counter)

```
Key:    rv:stats:{metric_name}
Type:   String (INCR / INCRBY)
Examples:
  - rv:stats:tenant:{tenant_id}:sessions_active   -> 活跃会话数
  - rv:stats:agent:{agent_name}:calls_total        -> Agent 调用总数
  - rv:stats:llm:tokens_input_total               -> LLM 输入 Token 总数
  - rv:stats:llm:tokens_output_total              -> LLM 输出 Token 总数

TTL:    无（持久化计数器，定期同步到 PostgreSQL）
Purpose: 高频计数，避免数据库写放大
```

#### 3.2.7 WebSocket 会话映射 (Hash / Set)

```
Key:    rv:ws:user:{user_id}
Type:   Set
Members: connection_id_1, connection_id_2, ...

Key:    rv:ws:conn:{connection_id}
Type:   Hash
Fields:
  - user_id     -> string
  - tenant_id   -> string
  - session_id  -> string (optional, if watching a session)
  - connected_at-> timestamp

Purpose: 实时通知推送，支持多设备登录
```

#### 3.2.8 布隆过滤器 (RedisBloom)

```
Key:    rv:bloom:{filter_name}
Type:   RedisBloom (BF.RESERVE / BF.ADD / BF.EXISTS)
Examples:
  - rv:bloom:session_ids    -> 防止重复 session_id 查询
  - rv:bloom:task_ids       -> 快速判断任务是否已处理

Purpose: 快速去重检查，减少数据库查询
```

---

## 4. 对象存储 (S3/MinIO) 组织设计

### 4.1 存储桶结构

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
│           ├── development/
│           │   ├── patch.diff
│           │   └── code_archive.tar.gz
│           ├── review/
│           │   └── review_report.json
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
│           └── {checkpoint_id}.json.gz
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
└── system/
    └── backups/
        └── {date}/
            └── postgres_dump.sql.gz
```

### 4.2 对象元数据规范

```yaml
# S3 Object Metadata (x-amz-meta-*)
x-amz-meta-tenant-id: "{tenant_id}"
x-amz-meta-session-id: "{session_id}"
x-amz-meta-artifact-type: "code_patch|test_report|log_archive|documentation|model_output"
x-amz-meta-content-checksum: "sha256:{hash}"
x-amz-meta-created-at: "2024-01-15T10:30:00Z"
x-amz-meta-retention-days: "90"

# Lifecycle Policy
- Transition to IA (Infrequent Access) after 30 days
- Transition to Glacier after 90 days
- Expire (delete) after 365 days for logs
- Expire after 90 days for temporary checkpoints
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
```

---

## 5. ER 关系图

```
+----------------+       +----------------+       +----------------+
|    tenants     |1     *|     users      |1     *|   sessions     |
+----------------+-------+----------------+-------+----------------+
| id (PK)        |       | id (PK)        |       | id (PK)        |
| name           |       | tenant_id (FK) |       | tenant_id (FK) |
| slug           |       | email          |       | created_by(FK) |
| config (JSONB) |       | display_name   |       | current_stage  |
| created_at     |       | role           |       | status         |
| updated_at     |       | preferences    |       | config (JSONB) |
+----------------+       | created_at     |       | metadata(JSONB)|
                         | updated_at     |       | created_at     |
                         +----------------+       | updated_at     |
                                                  | completed_at   |
                                                  +----------------+
                                                           |
                           +-------------------------------+-------------------------------+
                           |                               |                               |
                           |1                              |1                              |1
                           |                               |                               |
                           v*                              v*                              v*
                  +----------------+             +--------------------+           +----------------+
                  |   checkpoints  |             |  workflow_states   |           | human_decisions|
                  |   (partitioned)|             +--------------------+           +----------------+
                  +----------------+             | id (PK)            |           | id (PK)        |
                  | thread_id (PK) |             | session_id (FK,UQ) |           | session_id(FK) |
                  | checkpoint_ns  |             | tenant_id (FK)     |           | tenant_id (FK) |
                  | checkpoint_id  |             | current_stage      |           | stage          |
                  | parent_cp_id   |             | status             |           | decision       |
                  | type           |             | exploration_result |           | comment        |
                  | checkpoint     |             | planning_result    |           | decided_by(FK) |
                  | metadata       |             | development_result |           | metadata       |
                  | tenant_id (FK) |             | review_result      |           | created_at     |
                  | session_id(FK) |             | testing_result     |           +----------------+
                  | created_at     |             | human_decisions    |
                  +----------------+             | human_notes        |
                                                 | timestamps         |
                                                 | state_version      |
                                                 | created_at         |
                                                 | updated_at         |
                                                 +--------------------+
                           |
                           |1
                           |
                           v*
                  +----------------+
                  |   agent_logs   |
                  |  (partitioned) |
                  +----------------+
                  | id (PK)        |
                  | session_id(FK) |
                  | tenant_id (FK) |
                  | agent_name     |
                  | stage          |
                  | level          |
                  | message        |
                  | payload (JSONB)|
                  | token_usage    |
                  | latency_ms     |
                  | created_at     |
                  +----------------+
                           |
                           |1
                           |
                           v*
                  +----------------+
                  |    artifacts   |
                  +----------------+
                  | id (PK)        |
                  | session_id(FK) |
                  | tenant_id (FK) |
                  | artifact_type  |
                  | storage_backend|
                  | bucket         |
                  | object_key     |
                  | object_version |
                  | content_type   |
                  | size_bytes     |
                  | checksum       |
                  | metadata       |
                  | created_at     |
                  +----------------+

+----------------+       +--------------------+       +------------------------+
|     tasks      |1     *| task_dependencies  |*     1|       tasks (self-ref)  |
+----------------+       +--------------------+       +------------------------+
| id (PK)        |       | id (PK)            |
| session_id(FK) |       | task_id (FK)       |
| tenant_id (FK) |       | depends_on (FK)    |
| queue          |       | created_at         |
| task_type      |       +--------------------+
| payload        |
| status         |
| priority       |
| attempt_count  |
| max_attempts   |
| error_info     |
| scheduled_at   |
| started_at     |
| completed_at   |
| created_at     |
| updated_at     |
+----------------+

+----------------+       +------------------------+
|  audit_logs    |       |  rate_limit_buckets    |
+----------------+       +------------------------+
| id (PK)        |       | id (PK)                |
| tenant_id (FK) |       | tenant_id (FK)         |
| user_id (FK)   |       | resource               |
| session_id(FK) |       | bucket_key             |
| action         |       | tokens                 |
| resource_type  |       | last_updated           |
| resource_id    |       | created_at             |
| details        |       +------------------------+
| ip_address     |
| user_agent     |
| created_at     |
+----------------+
```

---

## 6. SQL DDL 完整脚本

```sql
-- ============================================================
-- RV-Insights Database Schema
-- Version: 1.0.0
-- Database: PostgreSQL 15+
-- ============================================================

-- --------------------------------------------------------
-- 1. Extensions
-- --------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_uuidv7";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- --------------------------------------------------------
-- 2. Helper Functions
-- --------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION create_checkpoint_partition()
RETURNS void AS $$
DECLARE
    start_date date;
    end_date date;
    partition_name text;
BEGIN
    start_date := date_trunc('month', now() + interval '1 month');
    end_date := start_date + interval '1 month';
    partition_name := 'checkpoints_' || to_char(start_date, 'YYYY_MM');
    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = partition_name) THEN
        EXECUTE format(
            'CREATE TABLE %I PARTITION OF checkpoints FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_date, end_date
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

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
    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = partition_name) THEN
        EXECUTE format(
            'CREATE TABLE %I PARTITION OF agent_logs FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_date, end_date
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- --------------------------------------------------------
-- 3. Core Tables
-- --------------------------------------------------------

CREATE TABLE tenants (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            text NOT NULL,
    slug            text NOT NULL UNIQUE,
    config          jsonb DEFAULT '{}',
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now()
);
CREATE INDEX tenants_slug_idx ON tenants (slug);
CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE users (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       bigint NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    auth_provider_id text,
    email           text NOT NULL,
    display_name    text,
    role            text NOT NULL DEFAULT 'member' CHECK (role IN ('admin','member','viewer')),
    preferences     jsonb DEFAULT '{}',
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now(),
    UNIQUE (tenant_id, email)
);
CREATE INDEX users_tenant_id_idx ON users (tenant_id);
CREATE INDEX users_email_idx ON users (email);
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

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
        CHECK (status IN ('running','interrupted','completed','failed')),
    config          jsonb DEFAULT '{}',
    metadata        jsonb DEFAULT '{}',
    created_at      timestamptz DEFAULT now(),
    updated_at      timestamptz DEFAULT now(),
    completed_at    timestamptz
);
CREATE INDEX sessions_tenant_id_idx ON sessions (tenant_id);
CREATE INDEX sessions_tenant_status_idx ON sessions (tenant_id, status);
CREATE INDEX sessions_created_by_idx ON sessions (created_by);
CREATE INDEX sessions_current_stage_idx ON sessions (current_stage);
CREATE INDEX sessions_created_at_idx ON sessions (created_at);
CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- --------------------------------------------------------
-- 4. Partitioned Tables
-- --------------------------------------------------------

CREATE TABLE checkpoints (
    thread_id           text NOT NULL,
    checkpoint_ns       text NOT NULL DEFAULT '',
    checkpoint_id       text NOT NULL,
    parent_checkpoint_id text,
    type                text,
    checkpoint          jsonb NOT NULL,
    metadata            jsonb,
    tenant_id           bigint NOT NULL,
    session_id          uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    created_at          timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, created_at)
) PARTITION BY RANGE (created_at);

CREATE TABLE checkpoints_2024_01 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE checkpoints_2024_02 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
CREATE TABLE checkpoints_2024_03 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');
CREATE TABLE checkpoints_2024_04 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');
CREATE TABLE checkpoints_2024_05 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-05-01') TO ('2024-06-01');
CREATE TABLE checkpoints_2024_06 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-06-01') TO ('2024-07-01');
CREATE TABLE checkpoints_2024_07 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-07-01') TO ('2024-08-01');
CREATE TABLE checkpoints_2024_08 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');
CREATE TABLE checkpoints_2024_09 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-09-01') TO ('2024-10-01');
CREATE TABLE checkpoints_2024_10 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');
CREATE TABLE checkpoints_2024_11 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
CREATE TABLE checkpoints_2024_12 PARTITION OF checkpoints
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');
CREATE TABLE checkpoints_2025_01 PARTITION OF checkpoints
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE INDEX checkpoints_session_id_idx ON checkpoints (session_id);
CREATE INDEX checkpoints_tenant_id_idx ON checkpoints (tenant_id);
CREATE INDEX checkpoints_thread_id_idx ON checkpoints (thread_id);
CREATE INDEX checkpoints_created_at_idx ON checkpoints (created_at);
CREATE INDEX checkpoints_metadata_gin ON checkpoints USING gin (metadata);

CREATE TABLE agent_logs (
    id              bigint GENERATED ALWAYS AS IDENTITY,
    session_id      uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    tenant_id       bigint NOT NULL,
    agent_name      text NOT NULL,
    stage           text NOT NULL,
    level           text NOT NULL DEFAULT 'info' CHECK (level IN ('debug','info','warn','error')),
    message         text NOT NULL,
    payload         jsonb,
    token_usage     jsonb,
    latency_ms      int,
    created_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

CREATE TABLE agent_logs_2024_01 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE agent_logs_2024_02 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
CREATE TABLE agent_logs_2024_03 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');
CREATE TABLE agent_logs_2024_04 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');
CREATE TABLE agent_logs_2024_05 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-05-01') TO ('2024-06-01');
CREATE TABLE agent_logs_2024_06 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-06-01') TO ('2024-07-01');
CREATE TABLE agent_logs_2024_07 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-07-01') TO ('2024-08-01');
CREATE TABLE agent_logs_2024_08 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');
CREATE TABLE agent_logs_2024_09 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-09-01') TO ('2024-10-01');
CREATE TABLE agent_logs_2024_10 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');
CREATE TABLE agent_logs_2024_11 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
CREATE TABLE agent_logs_2024_12 PARTITION OF agent_logs
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');
CREATE TABLE agent_logs_2025_01 PARTITION OF agent_logs
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE INDEX agent_logs_session_id_idx ON agent_logs (session_id);
CREATE INDEX agent_logs_tenant_id_idx ON agent_logs (tenant_id);
CREATE INDEX agent_logs_agent_name_idx ON agent_logs (agent_name);
CREATE INDEX agent_logs_stage_idx ON agent_logs (stage);
CREATE INDEX agent_logs_level_idx ON agent_logs (level);
CREATE INDEX agent_logs_created_at_idx ON agent_logs (created_at);
CREATE INDEX agent_logs_payload_gin ON agent_logs USING gin (payload);
CREATE INDEX agent_logs_token_usage_gin ON agent_logs USING gin (token_usage);
CREATE INDEX agent_logs_created_at_brin ON agent_logs USING brin (created_at);

-- --------------------------------------------------------
-- 5. Workflow & Human Review Tables
-- --------------------------------------------------------

CREATE TABLE workflow_states (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id          uuid NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
    tenant_id           bigint NOT NULL,
    current_stage       text NOT NULL,
    status              text NOT NULL,
    exploration_result  jsonb,
    planning_result     jsonb,
    development_result  jsonb,
    review_result       jsonb,
    testing_result      jsonb,
    dev_review_iteration_count int NOT NULL DEFAULT 0,
    max_dev_review_iterations int NOT NULL DEFAULT 5,
    human_decisions     jsonb DEFAULT '[]',
    human_notes         jsonb DEFAULT '[]',
    agent_logs_summary  jsonb DEFAULT '[]',
    timestamps          jsonb DEFAULT '[]',
    state_version       int NOT NULL DEFAULT 1,
    created_at          timestamptz DEFAULT now(),
    updated_at          timestamptz DEFAULT now()
);
CREATE INDEX workflow_states_session_id_idx ON workflow_states (session_id);
CREATE INDEX workflow_states_tenant_id_idx ON workflow_states (tenant_id);
CREATE INDEX workflow_states_current_stage_idx ON workflow_states (current_stage);
CREATE INDEX workflow_states_status_idx ON workflow_states (status);
CREATE INDEX workflow_states_exploration_gin ON workflow_states USING gin (exploration_result);
CREATE INDEX workflow_states_planning_gin ON workflow_states USING gin (planning_result);
CREATE TRIGGER update_workflow_states_updated_at BEFORE UPDATE ON workflow_states
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

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
    metadata        jsonb DEFAULT '{}',
    created_at      timestamptz DEFAULT now()
);
CREATE INDEX human_decisions_session_id_idx ON human_decisions (session_id);
CREATE INDEX human_decisions_tenant_id_idx ON human_decisions (tenant_id);
CREATE INDEX human_decisions_stage_idx ON human_decisions (stage);
CREATE INDEX human_decisions_decided_by_idx ON human_decisions (decided_by);
CREATE INDEX human_decisions_created_at_idx ON human_decisions (created_at);

-- --------------------------------------------------------
-- 6. Task Queue Tables
-- --------------------------------------------------------

CREATE TABLE tasks (
    id              uuid DEFAULT uuid_generate_v7() PRIMARY KEY,
    session_id      uuid REFERENCES sessions(id) ON DELETE SET NULL,
    tenant_id       bigint NOT NULL,
    queue           text NOT NULL DEFAULT 'default',
    task_type       text NOT NULL,
    payload         jsonb NOT NULL DEFAULT '{}',
    status          text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','processing','completed','failed','dead_letter')),
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
CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE task_dependencies (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id         uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    depends_on      uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    created_at      timestamptz DEFAULT now(),
    UNIQUE (task_id, depends_on)
);
CREATE INDEX task_dependencies_task_id_idx ON task_dependencies (task_id);
CREATE INDEX task_dependencies_depends_on_idx ON task_dependencies (depends_on);

-- --------------------------------------------------------
-- 7. Artifact & Audit Tables
-- --------------------------------------------------------

CREATE TABLE artifacts (
    id              uuid DEFAULT uuid_generate_v7() PRIMARY KEY,
    session_id      uuid NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    tenant_id       bigint NOT NULL,
    artifact_type   text NOT NULL
        CHECK (artifact_type IN ('code_patch','test_report','log_archive','documentation','model_output')),
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

CREATE TABLE rate_limit_buckets (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       bigint NOT NULL,
    resource        text NOT NULL,
    bucket_key      text NOT NULL,
    tokens          numeric(20,4) NOT NULL DEFAULT 0,
    last_updated    timestamptz NOT NULL DEFAULT now(),
    created_at      timestamptz DEFAULT now(),
    UNIQUE (tenant_id, resource, bucket_key)
);
CREATE INDEX rate_limit_buckets_lookup_idx ON rate_limit_buckets (tenant_id, resource, bucket_key);

-- --------------------------------------------------------
-- 8. Row Level Security (RLS)
-- --------------------------------------------------------

ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE human_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE checkpoints ENABLE ROW LEVEL SECURITY;

ALTER TABLE sessions FORCE ROW LEVEL SECURITY;
ALTER TABLE workflow_states FORCE ROW LEVEL SECURITY;
ALTER TABLE human_decisions FORCE ROW LEVEL SECURITY;
ALTER TABLE agent_logs FORCE ROW LEVEL SECURITY;
ALTER TABLE tasks FORCE ROW LEVEL SECURITY;
ALTER TABLE artifacts FORCE ROW LEVEL SECURITY;
ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY;
ALTER TABLE checkpoints FORCE ROW LEVEL SECURITY;

CREATE POLICY sessions_tenant_isolation ON sessions
    FOR ALL
    USING (tenant_id = (SELECT current_setting('app.current_tenant_id', true)::bigint));
CREATE POLICY workflow_states_tenant_isolation ON workflow_states
    FOR ALL
    USING (tenant_id = (SELECT current_setting('app.current_tenant_id', true)::bigint));
CREATE POLICY human_decisions_tenant_isolation ON human_decisions
    FOR ALL
    USING (tenant_id = (SELECT current_setting('app.current_tenant_id', true)::bigint));
CREATE POLICY agent_logs_tenant_isolation ON agent_logs
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
CREATE POLICY checkpoints_tenant_isolation ON checkpoints
    FOR ALL
    USING (tenant_id = (SELECT current_setting('app.current_tenant_id', true)::bigint));

-- --------------------------------------------------------
-- 9. Permissions
-- --------------------------------------------------------

REVOKE ALL ON SCHEMA public FROM public;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- --------------------------------------------------------
-- 10. Partition Maintenance Jobs (pg_cron or external scheduler)
-- --------------------------------------------------------

-- 每月 1 日 00:00 创建下月分区
-- SELECT cron.schedule('create-checkpoint-partition', '0 0 1 * *', 'SELECT create_checkpoint_partition();');
-- SELECT cron.schedule('create-agent-logs-partition', '0 0 1 * *', 'SELECT create_agent_logs_partition();');
```

---

## 7. 会话恢复机制伪代码

### 7.1 核心恢复流程

```python
class SessionRecoveryManager:
    def __init__(self, pg_pool, redis_client, s3_client):
        self.pg = pg_pool
        self.redis = redis_client
        self.s3 = s3_client

    # --------------------------------------------------
    # 1. 创建 Checkpoint（LangGraph 调用）
    # --------------------------------------------------
    def save_checkpoint(
        self,
        thread_id: str,
        checkpoint_ns: str,
        checkpoint_id: str,
        parent_checkpoint_id: Optional[str],
        checkpoint: dict,       # LangGraph StateSnapshot
        metadata: dict,
        tenant_id: int,
        session_id: str
    ) -> None:
        """
        原子保存 Checkpoint：
        1. 写入 PostgreSQL checkpoints 分区表
        2. 更新 Redis 缓存
        3. 更新 workflow_states 反规范化表
        """
        conn = self.pg.acquire()
        try:
            with conn.transaction():
                # 设置 RLS 上下文
                conn.execute(
                    "SET LOCAL app.current_tenant_id = %s", (tenant_id,)
                )

                # 插入 Checkpoint
                conn.execute("""
                    INSERT INTO checkpoints (
                        thread_id, checkpoint_ns, checkpoint_id,
                        parent_checkpoint_id, type, checkpoint,
                        metadata, tenant_id, session_id, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                """, (
                    thread_id, checkpoint_ns, checkpoint_id,
                    parent_checkpoint_id, checkpoint.get('type'),
                    json.dumps(checkpoint), json.dumps(metadata or {}),
                    tenant_id, session_id
                ))

                # 更新 workflow_states
                state = self._extract_state_from_checkpoint(checkpoint)
                conn.execute("""
                    INSERT INTO workflow_states (
                        session_id, tenant_id, current_stage, status,
                        exploration_result, planning_result,
                        development_result, review_result, testing_result,
                        dev_review_iteration_count, max_dev_review_iterations,
                        human_decisions, human_notes, timestamps, state_version
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (session_id) DO UPDATE SET
                        current_stage = EXCLUDED.current_stage,
                        status = EXCLUDED.status,
                        exploration_result = EXCLUDED.exploration_result,
                        planning_result = EXCLUDED.planning_result,
                        development_result = EXCLUDED.development_result,
                        review_result = EXCLUDED.review_result,
                        testing_result = EXCLUDED.testing_result,
                        dev_review_iteration_count = EXCLUDED.dev_review_iteration_count,
                        human_decisions = EXCLUDED.human_decisions,
                        human_notes = EXCLUDED.human_notes,
                        timestamps = EXCLUDED.timestamps,
                        state_version = workflow_states.state_version + 1,
                        updated_at = now()
                """, (
                    session_id, tenant_id, state.current_stage, state.status,
                    json.dumps(state.exploration_result),
                    json.dumps(state.planning_result),
                    json.dumps(state.development_result),
                    json.dumps(state.review_result),
                    json.dumps(state.testing_result),
                    state.dev_review_iteration_count,
                    state.max_dev_review_iterations,
                    json.dumps(state.human_decisions),
                    json.dumps(state.human_notes),
                    json.dumps(state.timestamps),
                    1
                ))

            # Redis 缓存更新（事务外，允许失败）
            self._update_redis_cache(session_id, state, checkpoint_id)

        finally:
            conn.release()

    # --------------------------------------------------
    # 2. 恢复会话状态
    # --------------------------------------------------
    def recover_session(self, session_id: str, tenant_id: int) -> RVInsightsState:
        """
        恢复会话状态：
        1. 尝试从 Redis 读取缓存
        2. 缓存未命中则从 PostgreSQL 重建
        3. 返回完整 RVInsightsState
        """
        # 1. 尝试 Redis
        cached = self.redis.get(f"rv:state:{session_id}")
        if cached:
            state = decompress_json(cached)
            if state.get('state_version'):
                return RVInsightsState(**state)

        # 2. PostgreSQL 重建
        conn = self.pg.acquire()
        try:
            conn.execute(
                "SET LOCAL app.current_tenant_id = %s", (tenant_id,)
            )

            # 读取最新 workflow_states
            row = conn.fetchone("""
                SELECT * FROM workflow_states
                WHERE session_id = %s
            """, (session_id,))

            if not row:
                raise SessionNotFoundError(f"Session {session_id} not found")

            # 读取最新 checkpoint 完整数据
            cp_row = conn.fetchone("""
                SELECT checkpoint, metadata
                FROM checkpoints
                WHERE session_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (session_id,))

            state = self._rebuild_state(row, cp_row)

            # 3. 回填 Redis
            self._update_redis_cache(session_id, state, cp_row.checkpoint_id)

            return state

        finally:
            conn.release()

    # --------------------------------------------------
    # 3. Human-in-the-Loop 中断与恢复
    # --------------------------------------------------
    def interrupt_for_human_review(
        self,
        session_id: str,
        tenant_id: int,
        stage: str,           # e.g., HUMAN_REVIEW_EXPLORATION
        payload: dict         # 提交给人类审查的数据
    ) -> str:
        """
        中断工作流等待人工审查：
        1. 更新 sessions 状态为 interrupted
        2. 写入 human_decisions 占位记录（decision = NULL）
        3. 发布通知到 Redis Stream
        4. 释放分布式锁
        """
        conn = self.pg.acquire()
        try:
            with conn.transaction():
                conn.execute(
                    "SET LOCAL app.current_tenant_id = %s", (tenant_id,)
                )

                conn.execute("""
                    UPDATE sessions
                    SET status = 'interrupted', current_stage = %s, updated_at = now()
                    WHERE id = %s
                """, (stage, session_id))

                conn.execute("""
                    INSERT INTO human_decisions (
                        session_id, tenant_id, stage, decision,
                        comment, decided_by, metadata, created_at
                    ) VALUES (%s, %s, %s, NULL, NULL, NULL, %s, now())
                """, (session_id, tenant_id, stage, json.dumps(payload)))

            # 发布通知
            self.redis.xadd("rv:queue:human_review", {
                "session_id": session_id,
                "tenant_id": str(tenant_id),
                "stage": stage,
                "timestamp": now_iso(),
                "payload": json.dumps(payload)
            })

            # 释放会话锁
            self.redis.delete(f"rv:lock:session:{session_id}")

            return f"Session {session_id} interrupted at {stage}"

        finally:
            conn.release()

    def resume_after_human_decision(
        self,
        session_id: str,
        tenant_id: int,
        decision_id: int,
        decision: str,        # APPROVE, REJECT, REQUEST_CHANGES, ADD_NOTES
        comment: Optional[str],
        decided_by: int
    ) -> None:
        """
        人工决策后恢复工作流：
        1. 更新 human_decisions 记录
        2. 更新 sessions 状态为 running
        3. 恢复 LangGraph 执行（从最新 checkpoint 继续）
        4. 重新获取分布式锁
        """
        conn = self.pg.acquire()
        try:
            with conn.transaction():
                conn.execute(
                    "SET LOCAL app.current_tenant_id = %s", (tenant_id,)
                )

                conn.execute("""
                    UPDATE human_decisions
                    SET decision = %s, comment = %s, decided_by = %s
                    WHERE id = %s AND session_id = %s
                """, (decision, comment, decided_by, decision_id, session_id))

                # 确定恢复后的阶段
                next_stage = self._determine_next_stage(decision)

                conn.execute("""
                    UPDATE sessions
                    SET status = 'running', current_stage = %s, updated_at = now()
                    WHERE id = %s
                """, (next_stage, session_id))

            # 重新获取分布式锁
            lock_key = f"rv:lock:session:{session_id}"
            acquired = self.redis.set(lock_key, worker_id, nx=True, ex=30)
            if not acquired:
                raise ConcurrentExecutionError("Session is being processed by another worker")

            # 发布恢复事件到任务队列
            self.redis.xadd("rv:queue:agent_tasks", {
                "task_type": "resume_workflow",
                "session_id": session_id,
                "tenant_id": str(tenant_id),
                "from_stage": next_stage,
                "timestamp": now_iso()
            })

        finally:
            conn.release()

    # --------------------------------------------------
    # 4. 辅助方法
    # --------------------------------------------------
    def _update_redis_cache(self, session_id: str, state: RVInsightsState, checkpoint_id: str):
        """更新 Redis 缓存（允许失败，不影响主流程）"""
        try:
            pipe = self.redis.pipeline()
            pipe.hset(f"rv:session:{session_id}", mapping={
                "tenant_id": str(state.tenant_id),
                "current_stage": state.current_stage,
                "status": state.status,
                "state_version": str(state.state_version),
                "checkpoint_id": checkpoint_id,
                "updated_at": now_iso()
            })
            pipe.set(f"rv:state:{session_id}", compress_json(state.dict()), ex=7200)
            pipe.execute()
        except Exception as e:
            logger.warning(f"Redis cache update failed for {session_id}: {e}")

    def _extract_state_from_checkpoint(self, checkpoint: dict) -> RVInsightsState:
        """从 LangGraph Checkpoint 提取 RVInsightsState"""
        values = checkpoint.get("channel_values", {})
        return RVInsightsState(
            session_id=values.get("session_id"),
            current_stage=values.get("current_stage", "INITIALIZATION"),
            status=values.get("status", "running"),
            exploration_result=values.get("exploration_result"),
            planning_result=values.get("planning_result"),
            development_result=values.get("development_result"),
            review_result=values.get("review_result"),
            testing_result=values.get("testing_result"),
            dev_review_iteration_count=values.get("dev_review_iteration_count", 0),
            max_dev_review_iterations=values.get("max_dev_review_iterations", 3),
            human_decisions=values.get("human_decisions", []),
            human_notes=values.get("human_notes", []),
            timestamps=values.get("timestamps", [])
        )

    def _determine_next_stage(self, decision: str, current_stage: str) -> str:
        """根据人工决策确定下一阶段"""
        transitions = {
            "HUMAN_REVIEW_EXPLORATION": {
                "APPROVE": "PLANNING",
                "REJECT": "COMPLETION",
                "REQUEST_CHANGES": "EXPLORATION"
            },
            "HUMAN_REVIEW_PLANNING": {
                "APPROVE": "DEVELOPMENT",
                "REJECT": "COMPLETION",
                "REQUEST_CHANGES": "PLANNING"
            },
            "HUMAN_REVIEW_CODE": {
                "APPROVE": "TESTING",
                "REJECT": "COMPLETION",
                "REQUEST_CHANGES": "DEVELOPMENT"
            },
            "HUMAN_REVIEW_TESTING": {
                "APPROVE": "COMPLETION",
                "REJECT": "COMPLETION",
                "REQUEST_CHANGES": "TESTING"
            }
        }
        return transitions.get(current_stage, {}).get(decision, current_stage)
```

### 7.2 故障恢复场景

```python
# --------------------------------------------------
# 场景 A: Worker 崩溃恢复
# --------------------------------------------------
def recover_crashed_worker(worker_id: str):
    """
    1. 查询 tasks 表中 status = 'processing' 且 started_at > timeout 的任务
    2. 将这些任务状态重置为 'pending'
    3. 释放这些任务持有的 Redis 分布式锁
    """
    timeout_threshold = now() - timedelta(minutes=5)

    conn = pg.acquire()
    try:
        stale_tasks = conn.fetchall("""
            SELECT id, session_id FROM tasks
            WHERE status = 'processing'
              AND started_at < %s
              AND (error_info->>'worker_id') = %s
        """, (timeout_threshold, worker_id))

        for task in stale_tasks:
            conn.execute("""
                UPDATE tasks
                SET status = 'pending', started_at = NULL, error_info = NULL
                WHERE id = %s
            """, (task["id"],))

            redis.delete(f"rv:lock:session:{task['session_id']}")
            redis.delete(f"rv:lock:task:{task['id']}")

    finally:
        conn.release()

# --------------------------------------------------
# 场景 B: 数据库连接中断恢复
# --------------------------------------------------
def resume_after_db_disconnect(session_id: str, tenant_id: int):
    """
    1. 重新建立数据库连接
    2. 验证分布式锁是否仍由当前 worker 持有
    3. 从最新 checkpoint 恢复状态
    4. 继续执行工作流
    """
    lock_key = f"rv:lock:session:{session_id}"
    lock_owner = redis.get(lock_key)

    if lock_owner != current_worker_id:
        raise ConcurrentExecutionError("Lost lock ownership during disconnect")

    state = recovery_manager.recover_session(session_id, tenant_id)
    graph = build_state_graph()
    graph.invoke(state, config={"thread_id": session_id, "checkpoint_ns": "main"})

# --------------------------------------------------
# 场景 C: 分区缺失恢复
# --------------------------------------------------
def ensure_partition_exists(target_date: date):
    """
    写入数据前检查目标分区是否存在，不存在则动态创建
    """
    partition_name = f"checkpoints_{target_date.strftime('%Y_%m')}"
    conn = pg.acquire()
    try:
        exists = conn.fetchval("""
            SELECT 1 FROM pg_class WHERE relname = %s
        """, (partition_name,))

        if not exists:
            conn.execute("SELECT create_checkpoint_partition()")
            conn.execute("SELECT create_agent_logs_partition()")
    finally:
        conn.release()
```

---

## 8. 索引策略总结

| 表名 | 索引名 | 类型 | 列 | 用途 |
|------|--------|------|-----|------|
| tenants | tenants_slug_idx | B-tree | slug | 租户查找 |
| users | users_tenant_id_idx | B-tree | tenant_id | 租户用户列表 |
| users | users_email_idx | B-tree | email | 用户登录 |
| sessions | sessions_tenant_status_idx | B-tree | tenant_id, status | 租户会话筛选 |
| sessions | sessions_created_at_idx | B-tree | created_at | 时间范围查询 |
| checkpoints | checkpoints_session_id_idx | B-tree | session_id | 会话 Checkpoint 查询 |
| checkpoints | checkpoints_metadata_gin | GIN | metadata | JSONB 灵活查询 |
| workflow_states | workflow_states_exploration_gin | GIN | exploration_result | 探索结果搜索 |
| workflow_states | workflow_states_planning_gin | GIN | planning_result | 计划结果搜索 |
| human_decisions | human_decisions_stage_idx | B-tree | stage | 按阶段统计 |
| agent_logs | agent_logs_payload_gin | GIN | payload | 日志内容搜索 |
| agent_logs | agent_logs_created_at_brin | BRIN | created_at | 大表时序范围扫描 |
| tasks | tasks_status_scheduled_idx | B-tree (Partial) | status, scheduled_at | 待处理任务拉取 |
| artifacts | artifacts_metadata_gin | GIN | metadata | 制品元数据搜索 |
| audit_logs | audit_logs_details_gin | GIN | details | 审计详情搜索 |

---

## 9. 运维与监控

### 9.1 慢查询监控

```sql
-- 查找最慢查询
SELECT calls, round(mean_exec_time::numeric, 2) as mean_ms, query
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;

-- 查找最频繁查询
SELECT calls, query
FROM pg_stat_statements
ORDER BY calls DESC
LIMIT 20;
```

### 9.2 表膨胀检查

```sql
SELECT relname, n_dead_tup, last_vacuum, last_autovacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;
```

### 9.3 缺失外键索引检查

```sql
SELECT conrelid::regclass as table_name, a.attname as column_name
FROM pg_constraint c
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
WHERE c.contype = 'f'
  AND NOT EXISTS (
    SELECT 1 FROM pg_index i
    WHERE i.indrelid = c.conrelid AND a.attnum = ANY(i.indkey)
  );
```

### 9.4 连接监控

```sql
SELECT count(*), state
FROM pg_stat_activity
WHERE datname = current_database()
GROUP BY state;
```

---

## 10. 备份策略

| 层级 | 频率 | 保留期 | 方法 |
|------|------|--------|------|
| PostgreSQL 全量 | 每日 02:00 | 30 天 | `pg_dump` + `pg_basebackup` |
| PostgreSQL WAL | 实时归档 | 7 天 | `archive_command` 复制到对象存储 |
| Redis RDB | 每 15 分钟 | 3 天 | `SAVE` / `BGSAVE` |
| Redis AOF | 每秒追加 | 7 天 | `appendfsync everysec` |
| 对象存储 | 跨区域复制 | 90 天 | S3 Cross-Region Replication |
| Checkpoint 旧分区 | 每月 | 90 天后转冷存储 | `ALTER TABLE ... DETACH PARTITION` + S3 Glacier |

---

*文档版本: 1.0.0*
*最后更新: 2024-01-15*
