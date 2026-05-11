# Symphony 服务规格

状态：草案 v1（语言无关）

目的：定义一个用于编排编码智能体完成项目工作的服务。

## 规范性语言

本文档中的关键词 `MUST`、`MUST NOT`、`REQUIRED`、`SHOULD`、`SHOULD NOT`、`RECOMMENDED`、`MAY` 和 `OPTIONAL` 应按 RFC 2119 的说明解释。

`Implementation-defined` 表示该行为属于实现契约的一部分，但本规格不规定一种通用策略。实现方 MUST 记录所选择的行为。

## 1. 问题陈述

Symphony 是一个长期运行的自动化服务，它持续从 issue tracker（本规格版本中为 Linear）读取工作，为每个 issue 创建隔离工作区，并在该工作区内为该 issue 运行一个编码智能体会话。

该服务解决四类运维问题：

- 将 issue 执行变成可重复的守护进程工作流，而不是手工脚本。
- 在每个 issue 专属工作区中隔离智能体执行，使智能体命令只在对应 issue 的工作区目录内运行。
- 将工作流策略保存在仓库内（`WORKFLOW.md`），使团队能够随代码一起版本化智能体提示词和运行时设置。
- 提供足够的可观测性，以运维和调试多个并发智能体运行。

实现方应显式记录自己的信任与安全姿态。本规格不要求单一的审批、沙箱或操作员确认策略；有些实现面向高信任配置的可信环境，而另一些实现要求更严格的审批或沙箱。

重要边界：

- Symphony 是调度器/运行器和 tracker 读取器。
- 工单写入（状态转换、评论、PR 链接）通常由编码智能体使用工作流/运行时环境中的工具完成。
- 一次成功运行可以结束在工作流定义的交接状态（例如 `Human Review`），不一定是 `Done`。

## 2. 目标与非目标

### 2.1 目标

- 按固定节奏轮询 issue tracker，并以有界并发分发工作。
- 为分发、重试和协调维护一个单一权威的编排器状态。
- 创建确定性的每 issue 工作区，并跨运行保留它们。
- 当 issue 状态变化导致其不再合格时，停止活动运行。
- 使用指数退避从瞬时故障中恢复。
- 从仓库拥有的 `WORKFLOW.md` 契约加载运行时行为。
- 暴露操作员可见的可观测性（至少是结构化日志）。
- 支持由 tracker/文件系统驱动的重启恢复，而无需持久数据库；精确的内存调度器状态不会恢复。

### 2.2 非目标

- 丰富的 Web UI 或多租户控制平面。
- 规定具体的 dashboard 或终端 UI 实现。
- 通用工作流引擎或分布式作业调度器。
- 内置如何编辑工单、PR 或评论的业务逻辑。（该逻辑存在于工作流提示词和智能体工具中。）
- 强制要求超出编码智能体和宿主 OS 所提供能力的强沙箱控制。
- 为所有实现强制要求单一默认的审批、沙箱或操作员确认姿态。

## 3. 系统概览

### 3.1 主要组件

1. `Workflow Loader`
   - 读取 `WORKFLOW.md`。
   - 解析 YAML front matter 和提示词正文。
   - 返回 `{config, prompt_template}`。

2. `Config Layer`
   - 为工作流配置值暴露类型化 getter。
   - 应用默认值和环境变量间接引用。
   - 执行编排器在分发前使用的校验。

3. `Issue Tracker Client`
   - 获取活动状态中的候选 issue。
   - 获取特定 issue ID 的当前状态（协调）。
   - 在启动清理期间获取终止状态 issue。
   - 将 tracker payload 归一化为稳定的 issue 模型。

4. `Orchestrator`
   - 拥有轮询 tick。
   - 拥有内存运行时状态。
   - 决定哪些 issue 需要分发、重试、停止或释放。
   - 跟踪会话指标和重试队列状态。

5. `Workspace Manager`
   - 将 issue 标识符映射到工作区路径。
   - 确保每 issue 工作区目录存在。
   - 运行工作区生命周期 hook。
   - 清理终止 issue 的工作区。

6. `Agent Runner`
   - 创建工作区。
   - 根据 issue + 工作流模板构建提示词。
   - 启动编码智能体 app-server 客户端。
   - 将智能体更新流式传回编排器。

7. `Status Surface`（OPTIONAL）
   - 展示人类可读的运行时状态（例如终端输出、dashboard 或其他面向操作员的视图）。

8. `Logging`
   - 向一个或多个已配置 sink 发出结构化运行时日志。

### 3.2 抽象层级

Symphony 在保持以下层次时最容易移植：

1. `Policy Layer`（仓库定义）
   - `WORKFLOW.md` 提示词正文。
   - 团队特定的工单处理、校验和交接规则。

2. `Configuration Layer`（类型化 getter）
   - 将 front matter 解析为类型化运行时设置。
   - 处理默认值、环境 token 和路径归一化。

3. `Coordination Layer`（编排器）
   - 轮询循环、issue 合格性、并发、重试、协调。

4. `Execution Layer`（工作区 + 智能体子进程）
   - 文件系统生命周期、工作区准备、编码智能体协议。

5. `Integration Layer`（Linear adapter）
   - 针对 tracker 数据的 API 调用和归一化。

6. `Observability Layer`（日志 + OPTIONAL 状态表面）
   - 操作员对编排器和智能体行为的可见性。

### 3.3 外部依赖

- Issue tracker API（本规格版本中 `tracker.kind: linear` 对应 Linear）。
- 用于工作区和日志的本地文件系统。
- OPTIONAL 工作区填充工具（例如使用 Git CLI 时）。
- 支持目标 Codex app-server 模式的编码智能体可执行文件。
- 宿主环境中用于 issue tracker 和编码智能体的认证。

## 4. 核心领域模型

### 4.1 实体

#### 4.1.1 Issue

编排、提示词渲染和可观测性输出所使用的归一化 issue 记录。

字段：

- `id`（string）
  - 稳定的 tracker 内部 ID。
- `identifier`（string）
  - 人类可读的工单键（示例：`ABC-123`）。
- `title`（string）
- `description`（string 或 null）
- `priority`（integer 或 null）
  - 在分发排序中，数字越小优先级越高。
- `state`（string）
  - 当前 tracker 状态名称。
- `branch_name`（string 或 null）
  - 如果可用，由 tracker 提供的分支元数据。
- `url`（string 或 null）
- `labels`（字符串列表）
  - 归一化为小写。
- `blocked_by`（blocker refs 列表）
  - 每个 blocker ref 包含：
    - `id`（string 或 null）
    - `identifier`（string 或 null）
    - `state`（string 或 null）
- `created_at`（timestamp 或 null）
- `updated_at`（timestamp 或 null）

#### 4.1.2 Workflow Definition

解析后的 `WORKFLOW.md` payload：

- `config`（map）
  - YAML front matter 根对象。
- `prompt_template`（string）
  - front matter 之后裁剪过的 Markdown 正文。

#### 4.1.3 Service Config（类型化视图）

从 `WorkflowDefinition.config` 派生并经过环境解析的类型化运行时值。

示例：

- 轮询间隔
- 工作区根目录
- 活动和终止 issue 状态
- 并发限制
- 编码智能体可执行文件/参数/超时
- 工作区 hook

#### 4.1.4 Workspace

分配给一个 issue 标识符的文件系统工作区。

字段（逻辑）：

- `path`（绝对工作区路径）
- `workspace_key`（净化后的 issue 标识符）
- `created_now`（布尔值，用于控制 `after_create` hook）

#### 4.1.5 Run Attempt

某个 issue 的一次执行尝试。

字段（逻辑）：

- `issue_id`
- `issue_identifier`
- `attempt`（integer 或 null，首次运行时为 `null`，重试/继续时为 `>=1`）
- `workspace_path`
- `started_at`
- `status`
- `error`（OPTIONAL）

#### 4.1.6 Live Session（智能体会话元数据）

编码智能体子进程运行期间跟踪的状态。

字段：

- `session_id`（string，`<thread_id>-<turn_id>`）
- `thread_id`（string）
- `turn_id`（string）
- `codex_app_server_pid`（string 或 null）
- `last_codex_event`（string/enum 或 null）
- `last_codex_timestamp`（timestamp 或 null）
- `last_codex_message`（汇总后的 payload）
- `codex_input_tokens`（integer）
- `codex_output_tokens`（integer）
- `codex_total_tokens`（integer）
- `last_reported_input_tokens`（integer）
- `last_reported_output_tokens`（integer）
- `last_reported_total_tokens`（integer）
- `turn_count`（integer）
  - 当前 worker 生命周期内已启动的编码智能体 turn 数量。

#### 4.1.7 Retry Entry

某个 issue 的计划重试状态。

字段：

- `issue_id`
- `identifier`（供状态表面/日志使用的尽力而为人类 ID）
- `attempt`（integer，重试队列中从 1 开始）
- `due_at_ms`（单调时钟时间戳）
- `timer_handle`（运行时特定的 timer 引用）
- `error`（string 或 null）

#### 4.1.8 Orchestrator Runtime State

由编排器拥有的单一权威内存状态。

字段：

- `poll_interval_ms`（当前有效轮询间隔）
- `max_concurrent_agents`（当前有效全局并发限制）
- `running`（map `issue_id -> running entry`）
- `claimed`（已保留/运行中/重试中的 issue ID 集合）
- `retry_attempts`（map `issue_id -> RetryEntry`）
- `completed`（issue ID 集合；仅用于记账，不作为分发门控）
- `codex_totals`（聚合 tokens + 运行秒数）
- `codex_rate_limits`（来自智能体事件的最新 rate-limit snapshot）

### 4.2 稳定标识符与归一化规则

- `Issue ID`
  - 用于 tracker 查询和内部 map key。
- `Issue Identifier`
  - 用于人类可读日志和工作区命名。
- `Workspace Key`
  - 由 `issue.identifier` 派生，将不属于 `[A-Za-z0-9._-]` 的任何字符替换为 `_`。
  - 使用净化后的值作为工作区目录名。
- `Normalized Issue State`
  - 在 `lowercase` 后比较状态。
- `Session ID`
  - 由编码智能体的 `thread_id` 和 `turn_id` 组合为 `<thread_id>-<turn_id>`。

## 5. 工作流规格（仓库契约）

### 5.1 文件发现与路径解析

工作流文件路径优先级：

1. 显式应用/运行时设置（由 CLI 启动路径设置）。
2. 默认：当前进程工作目录中的 `WORKFLOW.md`。

加载器行为：

- 如果文件不可读，返回 `missing_workflow_file` 错误。
- 工作流文件应由仓库拥有并纳入版本控制。

### 5.2 文件格式

`WORKFLOW.md` 是一个带 OPTIONAL YAML front matter 的 Markdown 文件。

设计说明：

- `WORKFLOW.md` SHOULD 足够自包含，以描述并运行不同工作流（提示词、运行时设置、hook，以及 tracker 选择/配置），而不需要带外的服务专用配置。

解析规则：

- 如果文件以 `---` 开头，将直到下一个 `---` 的各行解析为 YAML front matter。
- 剩余行成为提示词正文。
- 如果不存在 front matter，将整个文件视为提示词正文，并使用空配置 map。
- YAML front matter MUST 解码为 map/object；非 map YAML 是错误。
- 提示词正文在使用前会被裁剪。

返回的工作流对象：

- `config`：front matter 根对象（不嵌套在 `config` key 下）。
- `prompt_template`：裁剪后的 Markdown 正文。

### 5.3 Front Matter Schema

顶层 key：

- `tracker`
- `polling`
- `workspace`
- `hooks`
- `agent`
- `codex`

未知 key SHOULD 被忽略，以便向前兼容。

说明：

- 工作流 front matter 可扩展。扩展 MAY 定义额外顶层 key，而不改变上述核心 schema。
- 扩展 SHOULD 记录其字段 schema、默认值、校验规则，以及变更是动态生效还是需要重启。

#### 5.3.1 `tracker`（object）

字段：

- `kind`（string）
  - 分发所 REQUIRED。
  - 当前支持值：`linear`
- `endpoint`（string）
  - 当 `tracker.kind == "linear"` 时默认：`https://api.linear.app/graphql`
- `api_key`（string）
  - MAY 是字面 token 或 `$VAR_NAME`。
  - 当 `tracker.kind == "linear"` 时的规范环境变量：`LINEAR_API_KEY`。
  - 如果 `$VAR_NAME` 解析为空字符串，将该 key 视为缺失。
- `project_slug`（string）
  - 当 `tracker.kind == "linear"` 时分发所 REQUIRED。
- `active_states`（字符串列表）
  - 默认：`Todo`、`In Progress`
- `terminal_states`（字符串列表）
  - 默认：`Closed`、`Cancelled`、`Canceled`、`Duplicate`、`Done`

#### 5.3.2 `polling`（object）

字段：

- `interval_ms`（integer）
  - 默认：`30000`
  - 变更 SHOULD 在运行时重新应用，并影响未来 tick 调度，无需重启。

#### 5.3.3 `workspace`（object）

字段：

- `root`（path string 或 `$VAR`）
  - 默认：`<system-temp>/symphony_workspaces`
  - `~` 会展开。
  - 相对路径相对于包含 `WORKFLOW.md` 的目录解析。
  - 有效工作区根目录在使用前归一化为绝对路径。

#### 5.3.4 `hooks`（object）

字段：

- `after_create`（多行 shell 脚本字符串，OPTIONAL）
  - 仅在工作区目录新建时运行。
  - 失败会中止工作区创建。
- `before_run`（多行 shell 脚本字符串，OPTIONAL）
  - 在每次智能体尝试之前、工作区准备之后、启动编码智能体之前运行。
  - 失败会中止当前尝试。
- `after_run`（多行 shell 脚本字符串，OPTIONAL）
  - 在每次智能体尝试之后运行（成功、失败、超时或取消），前提是工作区存在。
  - 失败会记录日志但被忽略。
- `before_remove`（多行 shell 脚本字符串，OPTIONAL）
  - 如果目录存在，在删除工作区之前运行。
  - 失败会记录日志但被忽略；清理仍继续。
- `timeout_ms`（integer，OPTIONAL）
  - 默认：`60000`
  - 适用于所有工作区 hook。
  - 无效值会导致配置校验失败。
  - 变更 SHOULD 在运行时为未来 hook 执行重新应用。

#### 5.3.5 `agent`（object）

字段：

- `max_concurrent_agents`（integer）
  - 默认：`10`
  - 变更 SHOULD 在运行时重新应用，并影响后续分发决策。
- `max_turns`（正整数）
  - 默认：`20`
  - 限制一个 worker 会话内编码智能体 turn 的数量。
  - 无效值会导致配置校验失败。
- `max_retry_backoff_ms`（integer）
  - 默认：`300000`（5 分钟）
  - 变更 SHOULD 在运行时重新应用，并影响未来重试调度。
- `max_concurrent_agents_by_state`（map `state_name -> positive integer`）
  - 默认：空 map。
  - 状态 key 会归一化（`lowercase`）后用于查找。
  - 无效条目（非正数或非数字）会被忽略。

#### 5.3.6 `codex`（object）

字段：

对于 `approval_policy`、`thread_sandbox` 和 `turn_sandbox_policy` 等 Codex 拥有的配置值，受支持值由目标 Codex app-server 版本定义。实现方 SHOULD 将它们视为透传 Codex 配置值，而不是依赖本规格中手工维护的 enum。要检查已安装的 Codex schema，运行 `codex app-server generate-json-schema --out <dir>`，并检查 `v2/ThreadStartParams.json` 和 `v2/TurnStartParams.json` 所引用的相关定义。如果实现方想要更严格的启动检查，MAY 在本地校验这些字段。

- `command`（string shell command）
  - 默认：`codex app-server`
  - 运行时在工作区目录中通过 `bash -lc` 启动该命令。
  - 启动的进程 MUST 通过 stdio 使用兼容的 app-server 协议。
- `approval_policy`（Codex `AskForApproval` 值）
  - 默认：implementation-defined。
- `thread_sandbox`（Codex `SandboxMode` 值）
  - 默认：implementation-defined。
- `turn_sandbox_policy`（Codex `SandboxPolicy` 值）
  - 默认：implementation-defined。
- `turn_timeout_ms`（integer）
  - 默认：`3600000`（1 小时）
- `read_timeout_ms`（integer）
  - 默认：`5000`
- `stall_timeout_ms`（integer）
  - 默认：`300000`（5 分钟）
  - 如果 `<= 0`，则禁用停滞检测。

### 5.4 提示词模板契约

`WORKFLOW.md` 的 Markdown 正文是每 issue 的提示词模板。

渲染要求：

- 使用严格模板引擎（Liquid 兼容语义已足够）。
- 未知变量 MUST 导致渲染失败。
- 未知 filter MUST 导致渲染失败。

模板输入变量：

- `issue`（object）
  - 包含所有归一化 issue 字段，包括标签和 blocker。
- `attempt`（integer 或 null）
  - 首次尝试时为 `null`/缺省。
  - 重试或继续运行时为整数。

回退提示词行为：

- 如果工作流提示词正文为空，运行时 MAY 使用最小默认提示词（`You are working on an issue from Linear.`）。
- 工作流文件读取/解析失败是配置/校验错误，SHOULD NOT 静默回退到提示词。

### 5.5 工作流校验与错误表面

错误类别：

- `missing_workflow_file`
- `workflow_parse_error`
- `workflow_front_matter_not_a_map`
- `template_parse_error`（提示词渲染期间）
- `template_render_error`（未知变量/filter，无效插值）

分发门控行为：

- 工作流文件读取/YAML 错误会阻止新分发，直到修复。
- 模板错误只会使受影响的运行尝试失败。

## 6. 配置规格

### 6.1 配置解析流水线

配置按以下顺序解析：

1. 选择工作流文件路径（显式运行时设置，否则为 cwd 默认）。
2. 将 YAML front matter 解析为原始配置 map。
3. 对缺失的 OPTIONAL 字段应用内置默认值。
4. 仅对显式包含 `$VAR_NAME` 的配置值解析 `$VAR_NAME` 间接引用。
5. 强制转换并校验类型化值。

环境变量不会全局覆盖 YAML 值。只有在配置值显式引用环境变量时才使用它们。

值强制转换语义：

- 路径/命令字段支持：
  - `~` home 展开
  - 针对 env-backed 路径值的 `$VAR` 展开
  - 仅对意图为本地文件系统路径的值应用展开；不要重写 URI 或任意 shell 命令字符串。
- 相对 `workspace.root` 值相对于所选 `WORKFLOW.md` 所在目录解析。

### 6.2 动态重新加载语义

动态重新加载是 REQUIRED：

- 软件 MUST 检测 `WORKFLOW.md` 变更。
- 发生变更时，它 MUST 重新读取并重新应用工作流配置和提示词模板，无需重启。
- 软件 MUST 尝试将实时行为调整到新配置（例如轮询节奏、并发限制、活动/终止状态、codex 设置、工作区路径/hook，以及未来运行的提示词内容）。
- 重新加载的配置适用于未来分发、重试调度、协调决策、hook 执行和智能体启动。
- 当配置变更时，实现不 REQUIRED 自动重启飞行中的智能体会话。
- 管理自身 listener/resource 的扩展（例如 HTTP server 端口变更）MAY 要求重启，除非实现显式支持实时重新绑定。
- 实现 SHOULD 也在运行时操作期间进行防御性重新校验/重新加载（例如分发前），以防文件系统 watch 事件丢失。
- 无效重新加载 MUST NOT 使服务崩溃；继续使用最后一个已知良好的有效配置运行，并发出操作员可见错误。

### 6.3 分发前置校验

该校验是在尝试分发新工作前运行的调度器前置检查。它校验轮询和启动 worker 所需的工作流/配置，而不是对所有可能工作流行为的完整审计。

启动校验：

- 在启动调度循环前校验配置。
- 如果启动校验失败，则启动失败并发出操作员可见错误。

每 tick 分发校验：

- 每次分发周期前重新校验。
- 如果校验失败，跳过该 tick 的分发，保持协调活动，并发出操作员可见错误。

校验检查：

- 工作流文件可加载和解析。
- `tracker.kind` 存在且受支持。
- `tracker.api_key` 在 `$` 解析后存在。
- 当所选 tracker kind REQUIRED 时，`tracker.project_slug` 存在。
- `codex.command` 存在且非空。

### 6.4 核心配置字段摘要（速查表）

本节有意冗余，便于编码智能体快速实现配置层。扩展字段记录在定义它们的扩展章节中。核心一致性不要求识别或校验扩展字段，除非实现了该扩展。

- `tracker.kind`：string，REQUIRED，当前为 `linear`
- `tracker.endpoint`：string，当 `tracker.kind=linear` 时默认 `https://api.linear.app/graphql`
- `tracker.api_key`：string 或 `$VAR`，当 `tracker.kind=linear` 时规范 env 为 `LINEAR_API_KEY`
- `tracker.project_slug`：string，当 `tracker.kind=linear` 时 REQUIRED
- `tracker.active_states`：字符串列表，默认 `["Todo", "In Progress"]`
- `tracker.terminal_states`：字符串列表，默认 `["Closed", "Cancelled", "Canceled", "Duplicate", "Done"]`
- `polling.interval_ms`：integer，默认 `30000`
- `workspace.root`：解析为绝对路径的 path，默认 `<system-temp>/symphony_workspaces`
- `hooks.after_create`：shell 脚本或 null
- `hooks.before_run`：shell 脚本或 null
- `hooks.after_run`：shell 脚本或 null
- `hooks.before_remove`：shell 脚本或 null
- `hooks.timeout_ms`：integer，默认 `60000`
- `agent.max_concurrent_agents`：integer，默认 `10`
- `agent.max_turns`：integer，默认 `20`
- `agent.max_retry_backoff_ms`：integer，默认 `300000`（5m）
- `agent.max_concurrent_agents_by_state`：正整数 map，默认 `{}`
- `codex.command`：shell command string，默认 `codex app-server`
- `codex.approval_policy`：Codex `AskForApproval` 值，默认 implementation-defined
- `codex.thread_sandbox`：Codex `SandboxMode` 值，默认 implementation-defined
- `codex.turn_sandbox_policy`：Codex `SandboxPolicy` 值，默认 implementation-defined
- `codex.turn_timeout_ms`：integer，默认 `3600000`
- `codex.read_timeout_ms`：integer，默认 `5000`
- `codex.stall_timeout_ms`：integer，默认 `300000`

## 7. 编排状态机

编排器是唯一会修改调度状态的组件。所有 worker 结果都会回报给它，并转换为显式状态转换。

### 7.1 Issue 编排状态

这不同于 tracker 状态（`Todo`、`In Progress` 等）。这是服务内部的 claim 状态。

1. `Unclaimed`
   - Issue 未运行且未计划重试。

2. `Claimed`
   - 编排器已保留该 issue，以防重复分发。
   - 实践中，claimed issue 要么是 `Running`，要么是 `RetryQueued`。

3. `Running`
   - Worker 任务存在，并且该 issue 在 `running` map 中被跟踪。

4. `RetryQueued`
   - Worker 未运行，但 `retry_attempts` 中存在重试 timer。

5. `Released`
   - 由于 issue 终止、非活动、缺失，或重试路径结束且未重新分发，claim 被移除。

重要细节：

- Worker 成功退出并不意味着 issue 永久完成。
- Worker MAY 在退出前连续执行多个编码智能体 turn。
- 每个正常 turn 完成后，worker 会重新检查 tracker issue 状态。
- 如果 issue 仍处于活动状态，worker SHOULD 在同一工作区中的同一实时编码智能体线程上启动另一个 turn，最多达到 `agent.max_turns`。
- 第一个 turn SHOULD 使用完整渲染后的任务提示词。
- 继续 turn SHOULD 只向已有线程发送继续指导，而不要重新发送已存在于线程历史中的原始任务提示词。
- 一旦 worker 正常退出，编排器仍会调度一个短暂的继续重试（约 1 秒），以重新检查 issue 是否仍保持活动并需要另一个 worker 会话。

### 7.2 Run Attempt 生命周期

一次运行尝试会经过以下阶段：

1. `PreparingWorkspace`
2. `BuildingPrompt`
3. `LaunchingAgentProcess`
4. `InitializingSession`
5. `StreamingTurn`
6. `Finishing`
7. `Succeeded`
8. `Failed`
9. `TimedOut`
10. `Stalled`
11. `CanceledByReconciliation`

不同终止原因很重要，因为重试逻辑和日志会不同。

### 7.3 转换触发器

- `Poll Tick`
  - 协调活动运行。
  - 校验配置。
  - 获取候选 issue。
  - 分发直到 slot 耗尽。

- `Worker Exit (normal)`
  - 移除 running entry。
  - 更新聚合运行时总量。
  - 当 worker 耗尽或完成其进程内 turn 循环后，调度继续重试（attempt `1`）。

- `Worker Exit (abnormal)`
  - 移除 running entry。
  - 更新聚合运行时总量。
  - 调度指数退避重试。

- `Codex Update Event`
  - 更新实时会话字段、token 计数器和 rate limit。

- `Retry Timer Fired`
  - 重新获取活动候选 issue 并尝试重新分发，或在不再合格时释放 claim。

- `Reconciliation State Refresh`
  - 停止 issue 状态为终止或不再活动的运行。

- `Stall Timeout`
  - 杀死 worker 并调度重试。

### 7.4 幂等性与恢复规则

- 编排器通过单一权威序列化状态变更，以避免重复分发。
- 启动任何 worker 前 REQUIRED 检查 `claimed` 和 `running`。
- 每个 tick 中，协调都先于分发运行。
- 重启恢复由 tracker 和文件系统驱动（没有持久编排器 DB）。
- 启动时的终止清理会删除已经处于终止状态 issue 的陈旧工作区。

## 8. 轮询、调度与协调

### 8.1 轮询循环

启动时，服务校验配置、执行启动清理、调度立即 tick，然后每隔 `polling.interval_ms` 重复。

当工作流配置变更被重新应用时，有效轮询间隔 SHOULD 更新。

Tick 顺序：

1. 协调运行中的 issue。
2. 运行分发前置校验。
3. 使用活动状态从 tracker 获取候选 issue。
4. 按分发优先级排序 issue。
5. 在 slot 仍可用时分发合格 issue。
6. 通知可观测性/状态消费者状态变化。

如果每 tick 校验失败，该 tick 会跳过分发，但协调仍会先发生。

### 8.2 候选选择规则

Issue 仅在以下条件全为 true 时才可分发：

- 它有 `id`、`identifier`、`title` 和 `state`。
- 其状态在 `active_states` 中且不在 `terminal_states` 中。
- 它尚不在 `running` 中。
- 它尚不在 `claimed` 中。
- 全局并发 slot 可用。
- 每状态并发 slot 可用。
- `Todo` 状态的 blocker 规则通过：
  - 如果 issue 状态为 `Todo`，当任何 blocker 非终止时不要分发。

排序顺序（稳定意图）：

1. `priority` 升序（优先 1..4；null/未知排最后）
2. `created_at` 最早优先
3. `identifier` 字典序作为平局裁决

### 8.3 并发控制

全局限制：

- `available_slots = max(max_concurrent_agents - running_count, 0)`

每状态限制：

- 如果存在则使用 `max_concurrent_agents_by_state[state]`（状态 key 已归一化）
- 否则回退到全局限制

运行时按 `running` map 中当前跟踪状态统计 issue。

### 8.4 重试与退避

重试 entry 创建：

- 取消同一 issue 的任何现有重试 timer。
- 存储 `attempt`、`identifier`、`error`、`due_at_ms` 和新的 timer handle。

退避公式：

- 干净 worker 退出后的正常继续重试使用 `1000` ms 的短固定延迟。
- 故障驱动重试使用 `delay = min(10000 * 2^(attempt - 1), agent.max_retry_backoff_ms)`。
- 幂由已配置最大重试退避封顶（默认 `300000` / 5m）。

重试处理行为：

1. 获取活动候选 issue（不是所有 issue）。
2. 按 `issue_id` 查找特定 issue。
3. 如果未找到，释放 claim。
4. 如果找到且仍然符合候选条件：
   - 如果 slot 可用则分发。
   - 否则以错误 `no available orchestrator slots` 重新入队。
5. 如果找到但不再活动，释放 claim。

说明：

- 终止状态工作区清理由启动清理和活动运行协调处理（包括当前运行 issue 的终止转换）。
- 重试处理主要作用于活动候选，并在 issue 缺席时释放 claim，而不是自己执行终止清理。

### 8.5 活动运行协调

协调每个 tick 运行，并包含两部分。

部分 A：停滞检测

- 对每个运行中 issue，计算 `elapsed_ms`，起点为：
  - 如果已经看到任何事件，则从 `last_codex_timestamp` 开始，否则
  - 从 `started_at` 开始
- 如果 `elapsed_ms > codex.stall_timeout_ms`，终止 worker 并排队重试。
- 如果 `stall_timeout_ms <= 0`，完全跳过停滞检测。

部分 B：Tracker 状态刷新

- 获取所有运行中 issue ID 的当前 issue 状态。
- 对每个运行中 issue：
  - 如果 tracker 状态为终止：终止 worker 并清理工作区。
  - 如果 tracker 状态仍活动：更新内存 issue snapshot。
  - 如果 tracker 状态既非活动也非终止：终止 worker 且不清理工作区。
- 如果状态刷新失败，保持 worker 运行，并在下一个 tick 重试。

### 8.6 启动时终止工作区清理

服务启动时：

1. 查询 tracker 中处于终止状态的 issue。
2. 对每个返回的 issue 标识符，移除对应工作区目录。
3. 如果获取终止 issue 失败，记录警告并继续启动。

这会防止重启后陈旧终止工作区不断累积。

## 9. 工作区管理与安全

### 9.1 工作区布局

工作区根：

- `workspace.root`（归一化后的绝对路径）

每 issue 工作区路径：

- `<workspace.root>/<sanitized_issue_identifier>`

工作区持久性：

- 同一 issue 的工作区会跨运行复用。
- 成功运行不会自动删除工作区。

### 9.2 工作区创建与复用

输入：`issue.identifier`

算法摘要：

1. 将标识符净化为 `workspace_key`。
2. 在工作区根目录下计算工作区路径。
3. 确保工作区路径作为目录存在。
4. 仅当目录在本次调用中被创建时标记 `created_now=true`；否则 `created_now=false`。
5. 如果 `created_now=true`，且已配置，则运行 `after_create` hook。

说明：

- 本节不假设任何特定仓库/VCS 工作流。
- 超出目录创建的工作区准备（例如依赖引导、checkout/sync、代码生成）是 implementation-defined，通常通过 hook 处理。

### 9.3 OPTIONAL 工作区填充（Implementation-Defined）

本规格不要求任何内置 VCS 或仓库引导行为。

实现 MAY 使用 implementation-defined 逻辑和/或 hook（例如 `after_create` 和/或 `before_run`）填充或同步工作区。

失败处理：

- 工作区填充/同步失败会为当前尝试返回错误。
- 如果在创建全新工作区时失败，实现 MAY 移除部分准备好的目录。
- 复用工作区在填充失败时 SHOULD NOT 被破坏性重置，除非显式选择并记录该策略。

### 9.4 工作区 Hook

受支持 hook：

- `hooks.after_create`
- `hooks.before_run`
- `hooks.after_run`
- `hooks.before_remove`

执行契约：

- 在适合宿主 OS 的本地 shell 上下文中执行，并以工作区目录作为 `cwd`。
- 在 POSIX 系统上，`sh -lc <script>`（或更严格的等价形式，如 `bash -lc <script>`）是符合规范的默认值。
- Hook 超时使用 `hooks.timeout_ms`；默认：`60000 ms`。
- 记录 hook 启动、失败和超时。

失败语义：

- `after_create` 失败或超时对工作区创建是致命的。
- `before_run` 失败或超时对当前运行尝试是致命的。
- `after_run` 失败或超时会被记录并忽略。
- `before_remove` 失败或超时会被记录并忽略。

### 9.5 安全不变量

这是最重要的可移植性约束。

不变量 1：仅在每 issue 工作区路径中运行编码智能体。

- 启动编码智能体子进程前，校验：
  - `cwd == workspace_path`

不变量 2：工作区路径 MUST 保持在工作区根目录内。

- 将两个路径都归一化为绝对路径。
- 要求 `workspace_path` 以 `workspace_root` 作为前缀目录。
- 拒绝工作区根目录外的任何路径。

不变量 3：工作区 key 已净化。

- 工作区目录名只允许 `[A-Za-z0-9._-]`。
- 将所有其他字符替换为 `_`。

## 10. Agent Runner 协议（编码智能体集成）

本节定义 Symphony 在集成 Codex app-server 时的语言中立职责。目标 Codex 版本的 Codex app-server 协议是协议 schema、消息 payload、传输 framing 和 method 名称的事实来源。

协议事实来源：

- 实现 MUST 发送对目标 Codex app-server 版本有效的消息。
- 实现 MUST 查阅目标 Codex app-server 文档或生成的 schema，而不是把本规格当作协议 schema。
- 如果本规格看起来与目标 Codex app-server 协议冲突，Codex 协议控制协议形状和传输行为。
- 本节中的 Symphony 特定要求仍控制编排行为、工作区选择、提示词构造、继续处理和可观测性提取。

### 10.1 启动契约

子进程启动参数：

- Command：`codex.command`
- Invocation：`bash -lc <codex.command>`
- Working directory：工作区路径
- Transport/framing：目标 Codex app-server 版本要求的协议传输

说明：

- 默认命令是 `codex app-server`。
- 审批策略、沙箱策略、cwd、提示词输入和 OPTIONAL 工具声明使用目标 Codex app-server 版本支持的字段提供。

RECOMMENDED 额外进程设置：

- 最大行大小：10 MB（用于安全 buffering）

### 10.2 会话启动职责

参考：https://developers.openai.com/codex/app-server/

启动 MUST 遵循目标 Codex app-server 契约。Symphony 还要求客户端：

- 在每 issue 工作区中启动 app-server 子进程。
- 使用目标 Codex app-server 协议初始化 app-server 会话。
- 根据目标协议创建或恢复编码智能体线程。
- 在目标协议接受 cwd 的任何位置，将绝对每 issue 工作区路径作为 thread/turn 工作目录提供。
- 使用渲染后的 issue 提示词启动第一个 turn。
- 后续 worker 内继续 turn 在同一实时线程上以继续指导启动，而不是重发原始 issue 提示词。
- 使用目标协议支持的字段提供实现所记录的审批和沙箱策略。
- 当目标协议支持 turn 或 session title 时，包含标识 issue 的元数据，例如 `<issue.identifier>: <issue.title>`。
- 使用目标协议公布已实现的客户端侧工具。

会话标识符：

- 从目标 Codex app-server 协议返回的线程身份中提取 `thread_id`。
- 从目标 Codex app-server 协议返回的每个 turn 身份中提取 `turn_id`。
- 发出 `session_id = "<thread_id>-<turn_id>"`
- 在一个 worker 运行内的所有继续 turn 复用同一个 `thread_id`

### 10.3 流式 Turn 处理

客户端按目标 Codex app-server 协议处理 app-server 更新，直到活动 turn 终止。

完成条件：

- 目标协议 turn 完成信号 -> 成功
- 目标协议 turn 失败信号 -> 失败
- 目标协议 turn 取消信号 -> 失败
- turn 超时（`turn_timeout_ms`）-> 失败
- 子进程退出 -> 失败

继续处理：

- 如果 worker 在成功 turn 后决定继续，它 SHOULD 使用目标协议在同一实时线程上启动另一个 turn。
- App-server 子进程 SHOULD 在这些继续 turn 之间保持存活，并仅在 worker 运行结束时停止。

传输处理要求：

- 遵循目标 Codex app-server 版本的传输和 framing 规则。
- 对于基于 stdio 的传输，除非目标协议另有规定，否则将协议流处理与诊断 stderr 处理分离。

### 10.4 发出的运行时事件（上游到编排器）

App-server 客户端向编排器 callback 发出结构化事件。每个事件 SHOULD 包含：

- `event`（enum/string）
- `timestamp`（UTC timestamp）
- `codex_app_server_pid`（如果可用）
- OPTIONAL `usage` map（token counts）
- 按需包含 payload 字段

重要发出事件包括，例如：

- `session_started`
- `startup_failed`
- `turn_completed`
- `turn_failed`
- `turn_cancelled`
- `turn_ended_with_error`
- `turn_input_required`
- `approval_auto_approved`
- `unsupported_tool_call`
- `notification`
- `other_message`
- `malformed`

### 10.5 审批、工具调用和用户输入策略

审批、沙箱和用户输入行为是 implementation-defined。

策略要求：

- 每个实现 MUST 记录其选择的审批、沙箱和操作员确认姿态。
- 审批请求和需要用户输入的事件 MUST NOT 使运行无限期停滞。实现 MAY 根据其记录的策略满足它们、向操作员呈现它们、自动解决它们，或使运行失败。

示例高信任行为：

- 自动批准会话中的命令执行审批。
- 自动批准会话中的文件变更审批。
- 将需要用户输入的 turn 视为硬失败。

不受支持的动态工具调用：

- 运行时明确实现并公布的受支持动态工具调用 SHOULD 按其扩展契约处理。
- 如果智能体请求不受支持的动态工具调用，使用目标协议返回工具失败响应并继续会话。
- 这可以防止会话在不受支持的工具执行路径上停滞。

可选客户端侧工具扩展：

- 实现 MAY 向 app-server 会话暴露一组有限的客户端侧工具。
- 当前标准化的可选工具：`linear_graphql`。
- 如果实现，支持的工具 SHOULD 在启动期间使用目标 Codex app-server 版本支持的协议机制向 app-server 会话公布。
- 不受支持的工具名称 SHOULD 仍使用目标协议返回失败结果并继续会话。

`linear_graphql` 扩展契约：

- 目的：使用当前会话的 Symphony 已配置 tracker auth，对 Linear 执行原始 GraphQL 查询或 mutation。
- 可用性：仅当 `tracker.kind == "linear"` 且配置了有效 Linear auth 时有意义。
- 首选输入形状：

  ```json
  {
    "query": "single GraphQL query or mutation document",
    "variables": {
      "optional": "graphql variables object"
    }
  }
  ```

- `query` MUST 是非空字符串。
- `query` MUST 恰好包含一个 GraphQL operation。
- `variables` 是 OPTIONAL，存在时 MUST 是 JSON object。
- 实现 MAY 额外接受原始 GraphQL 查询字符串作为简写输入。
- 每次工具调用执行一个 GraphQL operation。
- 如果提供的 document 包含多个 operation，拒绝该工具调用为无效输入。
- `operationName` 选择故意不在该扩展范围内。
- 复用活动 Symphony 工作流/运行时配置中的 Linear endpoint 和 auth；不要要求编码智能体从磁盘读取原始 token。
- 工具结果语义：
  - transport success + 没有顶层 GraphQL `errors` -> `success=true`
  - 存在顶层 GraphQL `errors` -> `success=false`，但保留 GraphQL 响应正文以便调试
  - 无效输入、缺失 auth 或传输失败 -> `success=false` 且包含错误 payload
- 将 GraphQL 响应或错误 payload 作为结构化工具输出返回，使模型可在会话内检查。

需要用户输入策略：

- 实现 MUST 记录如何处理目标协议的 user-input-required 信号。
- 运行 MUST NOT 无限期等待用户输入。
- 符合规范的实现 MAY 使运行失败、向操作员呈现请求、通过批准的操作员通道满足请求，或按其记录的策略自动解决请求。
- 上述示例高信任行为会立即使 user-input-required turn 失败。

### 10.6 超时与错误映射

超时：

- `codex.read_timeout_ms`：启动和同步请求期间的 request/response 超时
- `codex.turn_timeout_ms`：总 turn stream 超时
- `codex.stall_timeout_ms`：由编排器基于事件非活动强制执行

错误映射（RECOMMENDED 归一化类别）：

- `codex_not_found`
- `invalid_workspace_cwd`
- `response_timeout`
- `turn_timeout`
- `port_exit`
- `response_error`
- `turn_failed`
- `turn_cancelled`
- `turn_input_required`

### 10.7 Agent Runner 契约

`Agent Runner` 封装工作区 + 提示词 + app-server 客户端。

行为：

1. 为 issue 创建/复用工作区。
2. 从工作流模板构建提示词。
3. 启动 app-server 会话。
4. 将 app-server 事件转发给编排器。
5. 任何错误都会使 worker 尝试失败（编排器将重试）。

说明：

- 工作区在成功运行后会被有意保留。

## 11. Issue Tracker 集成契约（Linear 兼容）

### 11.1 REQUIRED 操作

实现 MUST 支持这些 tracker adapter 操作：

1. `fetch_candidate_issues()`
   - 返回已配置项目中处于已配置活动状态的 issue。

2. `fetch_issues_by_states(state_names)`
   - 用于启动时终止清理。

3. `fetch_issue_states_by_ids(issue_ids)`
   - 用于活动运行协调。

### 11.2 查询语义（Linear）

当 `tracker.kind == "linear"` 时的 Linear 特定要求：

- `tracker.kind == "linear"`
- GraphQL endpoint（默认 `https://api.linear.app/graphql`）
- Auth token 在 `Authorization` header 中发送
- `tracker.project_slug` 映射到 Linear project `slugId`
- 候选 issue 查询使用 `project: { slugId: { eq: $projectSlug } }` 过滤项目
- Issue 状态刷新查询使用 GraphQL issue ID，变量类型为 `[ID!]`
- 候选 issue REQUIRED 支持分页
- 默认 page size：`50`
- 网络超时：`30000 ms`

重要：

- Linear GraphQL schema 细节可能漂移。保持查询构造隔离，并测试本规格 REQUIRED 的确切查询字段/类型。

非 Linear 实现 MAY 改变传输细节，但归一化输出 MUST 匹配第 4 节中的领域模型。

### 11.3 归一化规则

候选 issue 归一化 SHOULD 产出第 4.1.1 节列出的字段。

额外归一化细节：

- `labels` -> 小写字符串
- `blocked_by` -> 从 relation type 为 `blocks` 的反向关系派生
- `priority` -> 仅 integer（非整数变为 null）
- `created_at` 和 `updated_at` -> 解析 ISO-8601 timestamp

### 11.4 错误处理契约

RECOMMENDED 错误类别：

- `unsupported_tracker_kind`
- `missing_tracker_api_key`
- `missing_tracker_project_slug`
- `linear_api_request`（传输失败）
- `linear_api_status`（非 200 HTTP）
- `linear_graphql_errors`
- `linear_unknown_payload`
- `linear_missing_end_cursor`（分页完整性错误）

Tracker 错误时的编排器行为：

- 候选获取失败：记录日志并跳过该 tick 的分发。
- 运行状态刷新失败：记录日志并保持活动 worker 运行。
- 启动时终止清理失败：记录警告并继续启动。

### 11.5 Tracker 写入（重要边界）

Symphony 不要求在编排器中提供一等 tracker 写 API。

- 工单 mutation（状态转换、评论、PR 元数据）通常由编码智能体使用工作流提示词定义的工具处理。
- 服务仍然是调度器/运行器和 tracker 读取器。
- 工作流特定的成功通常意味着“达到下一个交接状态”（例如 `Human Review`），而不是 tracker 终止状态 `Done`。
- 如果实现 `linear_graphql` 客户端侧工具扩展，它仍然是智能体工具链的一部分，而不是编排器业务逻辑。

## 12. 提示词构造与上下文组装

### 12.1 输入

提示词渲染的输入：

- `workflow.prompt_template`
- 归一化 `issue` object
- OPTIONAL `attempt` integer（重试/继续元数据）

### 12.2 渲染规则

- 使用严格变量检查进行渲染。
- 使用严格 filter 检查进行渲染。
- 将 issue object key 转换为字符串，以兼容模板。
- 保留嵌套数组/map（labels、blockers），以便模板迭代。

### 12.3 重试/继续语义

`attempt` SHOULD 传给模板，因为工作流提示词可以为以下场景提供不同指令：

- 首次运行（`attempt` 为 null 或缺省）
- 成功的先前会话之后的继续运行
- 错误/超时/停滞后的重试

### 12.4 失败语义

如果提示词渲染失败：

- 立即使运行尝试失败。
- 让编排器像处理任何其他 worker 失败一样处理它并决定重试行为。

## 13. 日志、状态与可观测性

### 13.1 日志约定

Issue 相关日志的 REQUIRED 上下文字段：

- `issue_id`
- `issue_identifier`

编码智能体会话生命周期日志的 REQUIRED 上下文：

- `session_id`

消息格式要求：

- 使用稳定的 `key=value` 表述。
- 包含动作结果（`completed`、`failed`、`retrying` 等）。
- 如存在，包含简洁失败原因。
- 避免记录大量原始 payload，除非必要。

### 13.2 日志输出与 Sink

本规格不规定日志写入位置（stderr、文件、远程 sink 等）。

要求：

- 操作员 MUST 能够在不附加 debugger 的情况下看到启动/校验/分发失败。
- 实现 MAY 写入一个或多个 sink。
- 如果已配置的 log sink 失败，服务 SHOULD 在可能时继续运行，并通过任何剩余 sink 发出操作员可见警告。

### 13.3 运行时 Snapshot / 监控接口（OPTIONAL 但 RECOMMENDED）

如果实现暴露同步运行时 snapshot（用于 dashboard 或监控），它 SHOULD 返回：

- `running`（运行中 session 行列表）
- 每个 running 行 SHOULD 包含 `turn_count`
- `retrying`（重试队列行列表）
- `codex_totals`
  - `input_tokens`
  - `output_tokens`
  - `total_tokens`
  - `seconds_running`（snapshot 时刻的聚合运行秒数，包括活动会话）
- `rate_limits`（最新编码智能体 rate limit payload，如果可用）

RECOMMENDED snapshot 错误模式：

- `timeout`
- `unavailable`

### 13.4 OPTIONAL 人类可读状态表面

人类可读状态表面（终端输出、dashboard 等）是 OPTIONAL 且 implementation-defined。

如果存在，它 SHOULD 仅来自编排器状态/指标，并且 MUST NOT 是正确性所 REQUIRED 的。

### 13.5 会话指标与 Token 计量

Token 计量规则：

- 智能体事件可以以多种 payload 形状包含 token 计数。
- 可用时优先使用绝对线程总量，例如：
  - `thread/tokenUsage/updated` payload
  - token-count wrapper 事件内的 `total_token_usage`
- 对 dashboard/API 总量，忽略 delta 风格 payload，例如 `last_token_usage`。
- 从所选 payload 的常见字段名中宽松提取 input/output/total token 计数。
- 对于绝对总量，跟踪相对上次报告总量的增量，以避免重复计数。
- 不要将通用 `usage` map 视为累计总量，除非事件类型这样定义。
- 在编排器状态中累计聚合总量。

运行时间计量：

- 运行时间 SHOULD 在 snapshot/render 时作为实时聚合报告。
- 实现 MAY 为已结束会话维护累计计数器，并在产生 snapshot/status 视图时添加从 `running` entry（例如 `started_at`）派生的活动会话已运行时间。
- 当会话结束（正常退出或取消/终止）时，将运行时长秒数添加到已结束会话累计运行时间。
- 不 REQUIRED 对运行时间总量做连续后台 tick。

Rate-limit 跟踪：

- 跟踪在任何智能体更新中看到的最新 rate-limit payload。
- Rate-limit 数据的任何人类可读呈现都是 implementation-defined。

### 13.6 人类化智能体事件摘要（OPTIONAL）

原始智能体协议事件的人类化摘要是 OPTIONAL。

如果实现：

- 将它们视为仅用于可观测性的输出。
- 不要让编排器逻辑依赖人类化字符串。

### 13.7 OPTIONAL HTTP Server 扩展

本节定义用于可观测性和运维控制的 OPTIONAL HTTP 接口。

如果实现：

- HTTP server 是一个扩展，不是符合性所 REQUIRED 的。
- 实现 MAY 为 dashboard 提供服务端渲染 HTML 或客户端应用。
- Dashboard/API MUST 只是可观测性/控制表面，并且 MUST NOT 成为编排器正确性所 REQUIRED 的。

扩展配置：

- `server.port`（integer，OPTIONAL）
  - 启用 HTTP server 扩展。
  - `0` 为本地开发和测试请求临时端口。
  - 当两者同时存在时，CLI `--port` 覆盖 `server.port`。

启用（扩展）：

- 当提供 CLI `--port` 参数时启动 HTTP server。
- 当 `WORKFLOW.md` front matter 中存在 `server.port` 时启动 HTTP server。
- `server` 顶层 key 归此扩展拥有。
- 正数 `server.port` 值绑定该端口。
- 实现 SHOULD 默认绑定 loopback（`127.0.0.1` 或宿主等价形式），除非显式配置其他行为。
- HTTP listener 设置变更（例如 `server.port`）不需要热重新绑定；需要重启的行为符合规范。

#### 13.7.1 人类可读 Dashboard（`/`）

- 在 `/` 托管人类可读 dashboard。
- 返回文档 SHOULD 描绘系统当前状态（例如活动会话、重试延迟、token 消耗、运行时间总量、近期事件和健康/错误指示器）。
- 由实现决定这是服务端生成的 HTML，还是消费下方 JSON API 的客户端应用。

#### 13.7.2 JSON REST API（`/api/v1/*`）

在 `/api/v1/*` 下提供 JSON REST API，用于当前运行时状态和运维调试。

最小端点：

- `GET /api/v1/state`
  - 返回当前系统状态的摘要视图（运行中会话、重试队列/延迟、聚合 token/运行时间总量、最新 rate limit，以及任何额外跟踪的摘要字段）。
  - 建议响应形状：

    ```json
    {
      "generated_at": "2026-02-24T20:15:30Z",
      "counts": {
        "running": 2,
        "retrying": 1
      },
      "running": [
        {
          "issue_id": "abc123",
          "issue_identifier": "MT-649",
          "state": "In Progress",
          "session_id": "thread-1-turn-1",
          "turn_count": 7,
          "last_event": "turn_completed",
          "last_message": "",
          "started_at": "2026-02-24T20:10:12Z",
          "last_event_at": "2026-02-24T20:14:59Z",
          "tokens": {
            "input_tokens": 1200,
            "output_tokens": 800,
            "total_tokens": 2000
          }
        }
      ],
      "retrying": [
        {
          "issue_id": "def456",
          "issue_identifier": "MT-650",
          "attempt": 3,
          "due_at": "2026-02-24T20:16:00Z",
          "error": "no available orchestrator slots"
        }
      ],
      "codex_totals": {
        "input_tokens": 5000,
        "output_tokens": 2400,
        "total_tokens": 7400,
        "seconds_running": 1834.2
      },
      "rate_limits": null
    }
    ```

- `GET /api/v1/<issue_identifier>`
  - 返回所标识 issue 的 issue 特定运行时/调试详情，包括实现所跟踪的、对调试有用的任何信息。
  - 建议响应形状：

    ```json
    {
      "issue_identifier": "MT-649",
      "issue_id": "abc123",
      "status": "running",
      "workspace": {
        "path": "/tmp/symphony_workspaces/MT-649"
      },
      "attempts": {
        "restart_count": 1,
        "current_retry_attempt": 2
      },
      "running": {
        "session_id": "thread-1-turn-1",
        "turn_count": 7,
        "state": "In Progress",
        "started_at": "2026-02-24T20:10:12Z",
        "last_event": "notification",
        "last_message": "Working on tests",
        "last_event_at": "2026-02-24T20:14:59Z",
        "tokens": {
          "input_tokens": 1200,
          "output_tokens": 800,
          "total_tokens": 2000
        }
      },
      "retry": null,
      "logs": {
        "codex_session_logs": [
          {
            "label": "latest",
            "path": "/var/log/symphony/codex/MT-649/latest.log",
            "url": null
          }
        ]
      },
      "recent_events": [
        {
          "at": "2026-02-24T20:14:59Z",
          "event": "notification",
          "message": "Working on tests"
        }
      ],
      "last_error": null,
      "tracked": {}
    }
    ```

  - 如果当前内存状态不知道该 issue，返回 `404` 和错误响应（例如 `{\"error\":{\"code\":\"issue_not_found\",\"message\":\"...\"}}`）。

- `POST /api/v1/refresh`
  - 排队一次立即 tracker poll + reconciliation cycle（尽力而为触发；实现 MAY 合并重复请求）。
  - 建议请求 body：空 body 或 `{}`。
  - 建议响应（`202 Accepted`）形状：

    ```json
    {
      "queued": true,
      "coalesced": false,
      "requested_at": "2026-02-24T20:15:30Z",
      "operations": ["poll", "reconcile"]
    }
    ```

API 设计说明：

- 上述 JSON 形状是用于互操作性和调试易用性的 RECOMMENDED baseline。
- 实现 MAY 添加字段，但 SHOULD 避免破坏版本内的既有字段。
- 除 `/refresh` 这类运维触发器外，端点 SHOULD 是只读的。
- 已定义路由上的不支持方法 SHOULD 返回 `405 Method Not Allowed`。
- API 错误 SHOULD 使用 JSON envelope，例如 `{"error":{"code":"...","message":"..."}}`。
- 如果 dashboard 是客户端应用，它 SHOULD 消费该 API，而不是复制状态逻辑。

## 14. 失败模型与恢复策略

### 14.1 失败类别

1. `Workflow/Config Failures`
   - 缺失 `WORKFLOW.md`
   - 无效 YAML front matter
   - 不受支持的 tracker kind 或缺失 tracker 凭据/project slug
   - 缺失编码智能体可执行文件

2. `Workspace Failures`
   - 工作区目录创建失败
   - 工作区填充/同步失败（implementation-defined；可能来自 hook）
   - 无效工作区路径配置
   - Hook 超时/失败

3. `Agent Session Failures`
   - 启动握手失败
   - Turn failed/cancelled
   - Turn 超时
   - 请求用户输入，并被实现记录的策略作为失败处理
   - 子进程退出
   - 会话停滞（无活动）

4. `Tracker Failures`
   - API 传输错误
   - 非 200 status
   - GraphQL 错误
   - 格式错误 payload

5. `Observability Failures`
   - Snapshot 超时
   - Dashboard 渲染错误
   - Log sink 配置失败

### 14.2 恢复行为

- 分发校验失败：
  - 跳过新分发。
  - 保持服务存活。
  - 在可能时继续协调。

- Worker 失败：
  - 转换为带指数退避的重试。

- Tracker 候选获取失败：
  - 跳过本 tick。
  - 下一个 tick 再试。

- 协调状态刷新失败：
  - 保持当前 worker。
  - 下一个 tick 重试。

- Dashboard/log 失败：
  - 不使编排器崩溃。

### 14.3 部分状态恢复（重启）

当前设计有意让调度器状态保存在内存中。重启恢复意味着服务可以通过轮询 tracker 状态并复用保留的工作区来恢复有用操作。它不意味着重试 timer、运行中会话或实时 worker 状态能跨进程重启存活。

重启后：

- 不从先前进程内存恢复任何重试 timer。
- 不假设任何运行中会话可恢复。
- 服务通过以下方式恢复：
  - 启动时终止工作区清理
  - 重新轮询活动 issue
  - 重新分发合格工作

### 14.4 操作员介入点

操作员可以通过以下方式控制行为：

- 编辑 `WORKFLOW.md`（提示词和大多数运行时设置）。
- 按第 6.2 节，`WORKFLOW.md` 变更会被检测并自动重新应用，无需重启。
- 在 tracker 中更改 issue 状态：
  - 终止状态 -> 协调时停止运行会话并清理工作区
  - 非活动状态 -> 停止运行会话但不清理
- 为进程恢复或部署重启服务（不是应用工作流配置变更的常规路径）。

## 15. 安全与运维安全

### 15.1 信任边界假设

每个实现定义自己的信任边界。

运维安全要求：

- 实现 SHOULD 清楚说明它们面向可信环境、更严格环境，还是二者兼顾。
- 实现 SHOULD 清楚说明它们依赖自动批准动作、操作员审批、更严格沙箱，还是这些控制的某种组合。
- 工作区隔离和路径校验是重要的基线控制，但不能替代实现所选择的任何审批和沙箱策略。

### 15.2 文件系统安全要求

强制：

- 工作区路径 MUST 保持在已配置工作区根目录下。
- 编码智能体 cwd MUST 是当前运行的每 issue 工作区路径。
- 工作区目录名 MUST 使用净化后的标识符。

RECOMMENDED 额外 port 加固：

- 在专用 OS 用户下运行。
- 限制工作区根目录权限。
- 如可能，将工作区根目录挂载到专用卷。

### 15.3 密钥处理

- 支持工作流配置中的 `$VAR` 间接引用。
- 不要记录 API token 或 secret env 值。
- 校验 secret 存在性，但不打印它们。

### 15.4 Hook 脚本安全

工作区 hook 是来自 `WORKFLOW.md` 的任意 shell 脚本。

影响：

- Hook 是完全受信任的配置。
- Hook 在工作区目录内运行。
- Hook 输出 SHOULD 在日志中截断。
- Hook 超时 REQUIRED，以避免挂起编排器。

### 15.5 Harness 加固指导

针对仓库、issue tracker 和其他可能包含敏感数据或外部控制内容的输入运行 Codex 智能体可能很危险。如果智能体被诱导执行有害命令或使用权限过大的集成，宽松部署可能导致数据泄漏、破坏性 mutation，甚至整机失陷。

实现 SHOULD 明确评估自己的风险画像，并在适当位置加固执行 harness。本规格有意不强制单一加固姿态，但实现 SHOULD NOT 仅因为 tracker 数据、仓库内容、提示词输入或工具参数来自正常工作流内部，就假设它们完全可信。

可能的加固措施包括：

- 收紧本规格其他位置描述的 Codex 审批和沙箱设置，而不是使用最大权限配置运行。
- 添加外部隔离层，例如 OS/container/VM 沙箱、网络限制，或内置 Codex 策略控制之外的独立凭据。
- 过滤哪些 Linear issue、项目、团队、标签或其他 tracker 来源有资格分发，使不受信任或范围外任务不会自动到达智能体。
- 缩窄 `linear_graphql` 工具，使其只能读取或修改目标项目范围内的数据，而不是暴露一般性的整个工作区 tracker 访问。
- 将智能体可用的客户端侧工具、凭据、文件系统路径和网络目的地集合减少到工作流所需的最小范围。

正确控制取决于部署，但实现 SHOULD 清楚记录它们，并将 harness 加固视为核心安全模型的一部分，而不是可选的事后补充。

## 16. 参考算法（语言无关）

### 16.1 服务启动

```text
function start_service():
  configure_logging()
  start_observability_outputs()
  start_workflow_watch(on_change=reload_and_reapply_workflow)

  state = {
    poll_interval_ms: get_config_poll_interval_ms(),
    max_concurrent_agents: get_config_max_concurrent_agents(),
    running: {},
    claimed: set(),
    retry_attempts: {},
    completed: set(),
    codex_totals: {input_tokens: 0, output_tokens: 0, total_tokens: 0, seconds_running: 0},
    codex_rate_limits: null
  }

  validation = validate_dispatch_config()
  if validation is not ok:
    log_validation_error(validation)
    fail_startup(validation)

  startup_terminal_workspace_cleanup()
  schedule_tick(delay_ms=0)

  event_loop(state)
```

### 16.2 Poll-and-Dispatch Tick

```text
on_tick(state):
  state = reconcile_running_issues(state)

  validation = validate_dispatch_config()
  if validation is not ok:
    log_validation_error(validation)
    notify_observers()
    schedule_tick(state.poll_interval_ms)
    return state

  issues = tracker.fetch_candidate_issues()
  if issues failed:
    log_tracker_error()
    notify_observers()
    schedule_tick(state.poll_interval_ms)
    return state

  for issue in sort_for_dispatch(issues):
    if no_available_slots(state):
      break

    if should_dispatch(issue, state):
      state = dispatch_issue(issue, state, attempt=null)

  notify_observers()
  schedule_tick(state.poll_interval_ms)
  return state
```

### 16.3 协调活动运行

```text
function reconcile_running_issues(state):
  state = reconcile_stalled_runs(state)

  running_ids = keys(state.running)
  if running_ids is empty:
    return state

  refreshed = tracker.fetch_issue_states_by_ids(running_ids)
  if refreshed failed:
    log_debug("keep workers running")
    return state

  for issue in refreshed:
    if issue.state in terminal_states:
      state = terminate_running_issue(state, issue.id, cleanup_workspace=true)
    else if issue.state in active_states:
      state.running[issue.id].issue = issue
    else:
      state = terminate_running_issue(state, issue.id, cleanup_workspace=false)

  return state
```

### 16.4 分发一个 Issue

```text
function dispatch_issue(issue, state, attempt):
  worker = spawn_worker(
    fn -> run_agent_attempt(issue, attempt, parent_orchestrator_pid) end
  )

  if worker spawn failed:
    return schedule_retry(state, issue.id, next_attempt(attempt), {
      identifier: issue.identifier,
      error: "failed to spawn agent"
    })

  state.running[issue.id] = {
    worker_handle,
    monitor_handle,
    identifier: issue.identifier,
    issue,
    session_id: null,
    codex_app_server_pid: null,
    last_codex_message: null,
    last_codex_event: null,
    last_codex_timestamp: null,
    codex_input_tokens: 0,
    codex_output_tokens: 0,
    codex_total_tokens: 0,
    last_reported_input_tokens: 0,
    last_reported_output_tokens: 0,
    last_reported_total_tokens: 0,
    retry_attempt: normalize_attempt(attempt),
    started_at: now_utc()
  }

  state.claimed.add(issue.id)
  state.retry_attempts.remove(issue.id)
  return state
```

### 16.5 Worker Attempt（工作区 + 提示词 + 智能体）

```text
function run_agent_attempt(issue, attempt, orchestrator_channel):
  workspace = workspace_manager.create_for_issue(issue.identifier)
  if workspace failed:
    fail_worker("workspace error")

  if run_hook("before_run", workspace.path) failed:
    fail_worker("before_run hook error")

  session = app_server.start_session(workspace=workspace.path)
  if session failed:
    run_hook_best_effort("after_run", workspace.path)
    fail_worker("agent session startup error")

  max_turns = config.agent.max_turns
  turn_number = 1

  while true:
    prompt = build_turn_prompt(workflow_template, issue, attempt, turn_number, max_turns)
    if prompt failed:
      app_server.stop_session(session)
      run_hook_best_effort("after_run", workspace.path)
      fail_worker("prompt error")

    turn_result = app_server.run_turn(
      session=session,
      prompt=prompt,
      issue=issue,
      on_message=(msg) -> send(orchestrator_channel, {codex_update, issue.id, msg})
    )

    if turn_result failed:
      app_server.stop_session(session)
      run_hook_best_effort("after_run", workspace.path)
      fail_worker("agent turn error")

    refreshed_issue = tracker.fetch_issue_states_by_ids([issue.id])
    if refreshed_issue failed:
      app_server.stop_session(session)
      run_hook_best_effort("after_run", workspace.path)
      fail_worker("issue state refresh error")

    issue = refreshed_issue[0] or issue

    if issue.state is not active:
      break

    if turn_number >= max_turns:
      break

    turn_number = turn_number + 1

  app_server.stop_session(session)
  run_hook_best_effort("after_run", workspace.path)

  exit_normal()
```

### 16.6 Worker 退出与重试处理

```text
on_worker_exit(issue_id, reason, state):
  running_entry = state.running.remove(issue_id)
  state = add_runtime_seconds_to_totals(state, running_entry)

  if reason == normal:
    state.completed.add(issue_id)  # bookkeeping only
    state = schedule_retry(state, issue_id, 1, {
      identifier: running_entry.identifier,
      delay_type: continuation
    })
  else:
    state = schedule_retry(state, issue_id, next_attempt_from(running_entry), {
      identifier: running_entry.identifier,
      error: format("worker exited: %reason")
    })

  notify_observers()
  return state
```

```text
on_retry_timer(issue_id, state):
  retry_entry = state.retry_attempts.pop(issue_id)
  if missing:
    return state

  candidates = tracker.fetch_candidate_issues()
  if fetch failed:
    return schedule_retry(state, issue_id, retry_entry.attempt + 1, {
      identifier: retry_entry.identifier,
      error: "retry poll failed"
    })

  issue = find_by_id(candidates, issue_id)
  if issue is null:
    state.claimed.remove(issue_id)
    return state

  if available_slots(state) == 0:
    return schedule_retry(state, issue_id, retry_entry.attempt + 1, {
      identifier: issue.identifier,
      error: "no available orchestrator slots"
    })

  return dispatch_issue(issue, state, attempt=retry_entry.attempt)
```

## 17. 测试与校验矩阵

符合规范的实现 SHOULD 包含覆盖本规格所定义行为的测试。

校验 profile：

- `Core Conformance`：所有符合规范实现 REQUIRED 的确定性测试。
- `Extension Conformance`：仅对实现选择发布的 OPTIONAL 功能 REQUIRED。
- `Real Integration Profile`：生产使用前 RECOMMENDED 的环境相关 smoke/integration 检查。

除非另有说明，第 17.1 到 17.7 节属于 `Core Conformance`。以 `If ... is implemented` 开头的 bullet 属于 `Extension Conformance`。

### 17.1 工作流与配置解析

- 工作流文件路径优先级：
  - 提供显式运行时路径时使用该路径
  - 没有显式运行时路径时，cwd 默认是 `WORKFLOW.md`
- 工作流文件变更会被检测，并触发重新读取/重新应用，无需重启
- 无效工作流重新加载会保留最后一个已知良好的有效配置，并发出操作员可见错误
- 缺失 `WORKFLOW.md` 返回类型化错误
- 无效 YAML front matter 返回类型化错误
- Front matter 非 map 返回类型化错误
- OPTIONAL 值缺失时应用配置默认值
- `tracker.kind` 校验强制当前支持的 kind（`linear`）
- `tracker.api_key` 可用（包括 `$VAR` 间接引用）
- `$VAR` 解析对 tracker API key 和路径值可用
- `~` 路径展开可用
- `codex.command` 作为 shell command string 保留
- 每状态并发 override map 会归一化状态名并忽略无效值
- 提示词模板渲染 `issue` 和 `attempt`
- 提示词渲染在未知变量上失败（严格模式）

### 17.2 工作区管理器与安全

- 每个 issue 标识符对应确定性工作区路径
- 缺失的工作区目录会被创建
- 现有工作区目录会被复用
- 工作区位置处存在的非目录路径会被安全处理（替换或按实现策略失败）
- OPTIONAL 工作区填充/同步错误会被暴露
- `after_create` hook 仅在新建工作区时运行
- `before_run` hook 在每次尝试前运行，其失败/超时会中止当前尝试
- `after_run` hook 在每次尝试后运行，其失败/超时会被记录并忽略
- `before_remove` hook 在清理时运行，其失败/超时会被忽略
- 工作区路径净化和根目录包含不变量会在智能体启动前强制执行
- 智能体启动使用每 issue 工作区路径作为 cwd，并拒绝根目录外路径

### 17.3 Issue Tracker Client

- 候选 issue 获取使用活动状态和 project slug
- Linear 查询使用指定项目过滤字段（`slugId`）
- 空 `fetch_issues_by_states([])` 不进行 API 调用并返回空
- 分页在多页之间保留顺序
- Blocker 从 relation type 为 `blocks` 的反向关系归一化
- Label 归一化为小写
- 按 ID 刷新 issue 状态返回最小归一化 issue
- Issue 状态刷新查询使用第 11.2 节规定的 GraphQL ID 类型（`[ID!]`）
- 请求错误、非 200、GraphQL 错误、格式错误 payload 的错误映射

### 17.4 编排器分发、协调与重试

- 分发排序顺序是 priority，然后是最早创建时间
- 带有非终止 blocker 的 `Todo` issue 不合格
- 带有终止 blocker 的 `Todo` issue 合格
- 活动状态 issue 刷新会更新 running entry 状态
- 非活动状态停止运行中智能体且不清理工作区
- 终止状态停止运行中智能体并清理工作区
- 无运行中 issue 时协调是 no-op
- 正常 worker 退出会调度短继续重试（attempt 1）
- 异常 worker 退出会以基于 10s 的指数退避递增重试
- 重试退避上限使用已配置 `agent.max_retry_backoff_ms`
- 重试队列 entry 包含 attempt、due time、identifier 和 error
- 停滞检测会杀死停滞会话并调度重试
- Slot 耗尽会以显式错误原因重新入队重试
- 如果实现 snapshot API，它会返回 running 行、retry 行、token 总量和 rate limit
- 如果实现 snapshot API，timeout/unavailable 情况会被暴露

### 17.5 Coding-Agent App-Server Client

- 启动命令使用工作区 cwd，并调用 `bash -lc <codex.command>`
- 会话启动遵循目标 Codex app-server 协议。
- 当目标 Codex app-server 协议要求时，客户端 identity/capability payload 有效。
- 策略相关启动 payload 使用实现记录的 approval/sandbox 设置
- 提取目标协议暴露的 thread 和 turn identity，并用于发出 `session_started`
- 强制执行 request/response read timeout
- 强制执行 turn timeout
- 正确处理目标协议要求的 transport framing
- 对于基于 stdio 的传输，诊断 stderr 处理与协议流保持分离
- 命令/文件变更审批按实现记录的策略处理
- 不受支持的动态工具调用会被拒绝，且不会使会话停滞
- 用户输入请求按实现记录的策略处理，并且不会无限期停滞
- 提取目标协议暴露的 usage 和 rate-limit telemetry
- Approval、user-input-required、usage 和 rate-limit 信号按目标协议解释
- 如果实现客户端侧工具，会话启动使用目标 app-server 协议公布支持的工具 spec
- 如果实现 `linear_graphql` 客户端侧工具扩展：
  - 工具会向会话公布
  - 有效 `query` / `variables` 输入会使用已配置 Linear auth 执行
  - 顶层 GraphQL `errors` 产生 `success=false`，同时保留 GraphQL body
  - 无效参数、缺失 auth 和传输失败返回结构化失败 payload
  - 不受支持工具名仍失败且不会使会话停滞

### 17.6 可观测性

- 校验失败对操作员可见
- 结构化日志包含 issue/session 上下文字段
- Logging sink 失败不会使编排崩溃
- Token/rate-limit 聚合在重复智能体更新之间保持正确
- 如果实现人类可读状态表面，它由编排器状态驱动，且不影响正确性
- 如果实现人类化事件摘要，它们覆盖关键 wrapper/agent 事件类别，但不改变编排器行为

### 17.7 CLI 与宿主生命周期

- CLI 接受位置工作流路径参数（`path-to-WORKFLOW.md`）
- 未提供工作流路径参数时，CLI 使用 `./WORKFLOW.md`
- CLI 对不存在的显式工作流路径或缺失默认 `./WORKFLOW.md` 报错
- CLI 清晰呈现启动失败
- 当应用启动并正常关闭时，CLI 以成功退出
- 当启动失败或宿主进程异常退出时，CLI 非零退出

### 17.8 真实集成 Profile（RECOMMENDED）

这些检查对生产就绪 RECOMMENDED；当凭据、网络访问或外部服务权限不可用时，MAY 在 CI 中跳过。

- 可以使用由 `LINEAR_API_KEY` 或已记录本地引导机制（例如 `~/.linear_api_key`）提供的有效凭据运行真实 tracker smoke test。
- 真实集成测试 SHOULD 使用隔离测试标识符/工作区，并在实际可行时清理 tracker artifact。
- 被跳过的真实集成测试 SHOULD 报告为 skipped，而不是静默视为 passed。
- 如果真实集成 profile 在 CI 或 release validation 中显式启用，失败 SHOULD 使该 job 失败。

## 18. 实现清单（完成定义）

使用与第 17 节相同的校验 profile：

- 第 18.1 节 = `Core Conformance`
- 第 18.2 节 = `Extension Conformance`
- 第 18.3 节 = `Real Integration Profile`

### 18.1 符合性 REQUIRED 项

- 工作流路径选择支持显式运行时路径和 cwd 默认
- 带 YAML front matter + 提示词正文拆分的 `WORKFLOW.md` loader
- 带默认值和 `$` 解析的类型化配置层
- 动态 `WORKFLOW.md` watch/reload/re-apply，用于配置和提示词
- 使用单一权威可变状态的轮询编排器
- Issue tracker client，支持候选获取 + 状态刷新 + 终止获取
- 使用净化后的每 issue 工作区的工作区管理器
- 工作区生命周期 hook（`after_create`、`before_run`、`after_run`、`before_remove`）
- Hook 超时配置（`hooks.timeout_ms`，默认 `60000`）
- 使用 JSON line protocol 的编码智能体 app-server 子进程客户端
- Codex 启动命令配置（`codex.command`，默认 `codex app-server`）
- 使用 `issue` 和 `attempt` 变量的严格提示词渲染
- 指数重试队列，正常退出后带继续重试
- 可配置重试退避上限（`agent.max_retry_backoff_ms`，默认 5m）
- 在终止/非活动 tracker 状态上停止运行的协调逻辑
- 终止 issue 的工作区清理（启动 sweep + 活动转换）
- 带 `issue_id`、`issue_identifier` 和 `session_id` 的结构化日志
- 操作员可见可观测性（结构化日志；OPTIONAL snapshot/status 表面）

### 18.2 RECOMMENDED 扩展（符合性不 REQUIRED）

- 如果发布 HTTP server 扩展，它遵守 CLI `--port` 覆盖 `server.port`、使用安全默认 bind host，并暴露第 13.7 节中的 baseline endpoint/error 语义。
- `linear_graphql` 客户端侧工具扩展通过 app-server 会话，使用已配置 Symphony auth 暴露原始 Linear GraphQL 访问。
- TODO：跨进程重启持久化重试队列和会话元数据。
- TODO：使可观测性设置可在工作流 front matter 中配置，而不规定 UI 实现细节。
- TODO：在编排器中添加一等 tracker 写 API（评论/状态转换），而不只是通过智能体工具。
- TODO：添加 Linear 之外的可插拔 issue tracker adapter。

### 18.3 生产前运维校验（RECOMMENDED）

- 使用有效凭据和网络访问运行第 17.8 节中的 `Real Integration Profile`。
- 在目标宿主 OS/shell 环境上验证 hook 执行和工作流路径解析。
- 如果发布 OPTIONAL HTTP server，验证目标环境上的已配置端口行为和 loopback/默认 bind 预期。

## 附录 A. SSH Worker 扩展（OPTIONAL）

本附录描述一种常见扩展 profile：Symphony 保持一个中央编排器，但通过 SSH 在一个或多个远程主机上执行 worker 运行。

扩展配置：

- `worker.ssh_hosts`（SSH host 字符串列表，OPTIONAL）
  - 省略时，本地运行工作。
- `worker.max_concurrent_agents_per_host`（正整数，OPTIONAL）
  - 应用于已配置 SSH host 的共享每主机 cap。

### A.1 执行模型

- 编排器仍然是轮询、claim、重试和协调的唯一事实来源。
- `worker.ssh_hosts` 提供远程执行的候选 SSH 目的地。
- 每次 worker 运行一次分配给一个 host，该 host 会与 issue 工作区一起成为运行有效执行身份的一部分。
- `workspace.root` 在远程 host 上解释，而不是在编排器 host 上解释。
- 编码智能体 app-server 通过 SSH stdio 启动，而不是作为本地子进程启动，因此编排器仍拥有会话生命周期，即使命令在远程执行。
- 一个 worker 生命周期内的继续 turn SHOULD 保持在同一个 host 和工作区上。
- 远程 host SHOULD 满足与本地 worker 环境相同的基本契约：可达 shell、可写工作区根目录、编码智能体可执行文件，以及任何所需 auth 或仓库前置条件。

### A.2 调度说明

- SSH host MAY 被视为分发池。
- 实现 MAY 在重试时偏好先前使用过且仍可用的 host。
- `worker.max_concurrent_agents_per_host` 是跨已配置 SSH host 的 OPTIONAL 共享每主机 cap。
- 当所有 SSH host 都已达容量时，分发 SHOULD 等待，而不是静默回退到不同执行模式。
- 当原始 host 在工作有意义地开始前不可用时，实现 MAY 故障转移到另一个 host。
- 一旦运行已经产生副作用，在另一个 host 上透明重跑 SHOULD 被视为新尝试，而不是不可见 failover。

### A.3 需要考虑的问题

- 远程环境漂移：
  - 每个 host 都需要预期的 shell 环境、编码智能体可执行文件、auth 和仓库前置条件。
- 工作区局部性：
  - 工作区通常是 host-local 的，因此将 issue 移动到不同 host 通常是冷重启，除非存在共享存储。
- 路径和命令安全：
  - 一旦执行跨机器，远程路径解析、shell quoting 和工作区边界检查会更重要。
- 启动与故障转移语义：
  - 实现 SHOULD 区分 host-connectivity/startup 故障和 in-workspace agent 故障，以免同一工单意外在多个 host 上重新执行。
- Host 健康与饱和：
  - 死亡或过载的 host SHOULD 降低可用容量，而不是导致重复执行或意外回退到本地工作。
- 清理与可观测性：
  - 操作员需要知道哪个 host 拥有一次运行、其工作区在哪里，以及清理是否发生在正确机器上。
