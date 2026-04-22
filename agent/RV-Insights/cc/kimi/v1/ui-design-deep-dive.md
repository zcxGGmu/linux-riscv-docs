# RV-Insights 人工审核界面 UI/UX 深度规格

**版本**: v1.0  
**日期**: 2026-04-21  
**定位**: 本文档是 `rv-insights-design.md` 第 5 节（人工审核集成设计）的细化与扩展，可直接合并到主方案作为前端实现依据。

---

## 目录

1. [Web 控制台路由与页面结构](#1-web-控制台路由与页面结构)
2. [会话详情页面](#2-会话详情页面)
3. [人工审核界面（核心）](#3-人工审核界面核心)
4. [实时通信协议规范](#4-实时通信协议规范)
5. [离线断线处理](#5-离线断线处理)
6. [响应式设计](#6-响应式设计)
7. [附录：组件清单与依赖矩阵](#7-附录组件清单与依赖矩阵)

---

## 1. Web 控制台路由与页面结构

### 1.1 路由设计

采用 Next.js App Router 约定，所有受保护路由统一包裹 `AuthGuard` + `RoleGuard`。

| 路由 | 页面名称 | 访问角色 | 说明 |
|------|----------|----------|------|
| `/dashboard` | 仪表盘 | admin, reviewer, observer | 全局概览、待办审核队列、系统健康 |
| `/sessions` | 会话列表 | admin, reviewer, observer | 支持筛选/分页/搜索的会话管理 |
| `/sessions/:id` | 会话详情 | admin, reviewer, observer | 阶段时间线、实时日志、元数据 |
| `/sessions/:id/review/:stage` | 人工审核 | admin, reviewer | 核心审核界面，`:stage` 为枚举值（exploration / planning / code / testing） |
| `/settings` | 系统设置 | admin | 全局配置、通知渠道、Agent 参数 |
| `/agents` | Agent 管理 | admin | Agent 注册表、版本控制、启停状态 |
| `/login` | 登录页 | 公开 | OAuth2 / SSO 统一入口 |

**路由守卫行为**：
- 未登录用户访问受保护路由 → 重定向至 `/login`，携带 `redirect_to` 参数。
- `observer` 访问 `/sessions/:id/review/:stage` → 403 页面，提示“仅审核者可提交决策”。
- `reviewer` 访问 `/settings` 或 `/agents` → 403 页面。

### 1.2 全局布局（Global Layout）

所有受保护页面共享同一 `DashboardLayout`，结构如下：

```
+-------------------------------------------------------------+
|  [Logo]  RV-Insights          [GlobalSearch]   [Bell] [Avatar] |  <-- TopBar (高度: 56px)
+-------------------------------------------------------------+
| Sidebar (200px) |  Main Content Area (flex: 1)               |
|                 |                                            |
| - Dashboard     |                                            |
| - Sessions      |                                            |
| - Agents        |                                            |
| - Settings      |                                            |
|                 |                                            |
| -- Divider --   |                                            |
| - Docs          |                                            |
| - Feedback      |                                            |
+-------------------------------------------------------------+
```

**TopBar 组件**：
- **GlobalSearch**：Cmd+K 唤起全局搜索面板（Command Palette），可搜索会话 ID、仓库名、Agent 名称。输入框占位符："Search sessions, repos, agents..."
- **NotificationCenter（Bell）**：
  - 红点 Badge 显示未读人工审核待办数（`human_review_required` 事件触发）。
  - 下拉面板展示最近 20 条通知，按时间倒序，支持标记已读/全部已读。
  - 通知类型：审核请求、阶段完成、系统告警、Agent 错误。
- **UserAvatar**：下拉菜单展示当前用户角色、个人设置入口、登出。

**Sidebar 组件**：
- 可折叠（桌面端默认展开，平板以下默认收起，通过汉堡菜单触发）。
- 当前路由高亮（`bg-primary/10 text-primary`）。
- 底部固定区域放置文档与反馈链接。

### 1.3 权限控制矩阵（RBAC）

```typescript
interface User {
  id: string;
  name: string;
  email: string;
  role: "admin" | "reviewer" | "observer";
}

const PERMISSIONS: Record<string, string[]> = {
  "dashboard.view":   ["admin", "reviewer", "observer"],
  "sessions.view":    ["admin", "reviewer", "observer"],
  "sessions.review":  ["admin", "reviewer"],
  "sessions.decide":  ["admin", "reviewer"],
  "agents.manage":    ["admin"],
  "settings.manage":  ["admin"],
};
```

**前端实现**：通过 `usePermission(hook)` 在组件级控制按钮/面板的渲染，后端 API 同步做二次校验，防止前端绕过。

---

## 2. 会话详情页面

### 2.1 页面路由与数据加载

- **路由**: `/sessions/:id`
- **数据获取**: Next.js `generateMetadata` + 服务端组件预取会话元数据；实时数据通过 WebSocket/SSE 增量更新。
- **错误状态**: 会话不存在 → 404 页面；无权限 → 403 页面；加载中 → Skeleton 骨架屏。

### 2.2 顶部状态条（Session Status Bar）

固定于页面顶部（`position: sticky; top: 56px`），高度 64px，背景 `bg-card` 带底部阴影。

```
+----------------------------------------------------------------------------------+
| [StatusDot] EXPLORATION  |  Duration: 00:42:18  |  Tokens: 1.2M  |  [Badge] 3 pending |
|                          |  (实时递增)           |  (累计消耗)     |  点击跳转审核页     |
+----------------------------------------------------------------------------------+
```

**字段说明**：
- **StatusDot**: 当前阶段颜色编码（`INITIALIZATION` 灰 / `EXPLORATION` 蓝 / `HUMAN_REVIEW_*` 橙 / `COMPLETION` 绿 / `FAILED` 红）。
- **Duration**: 从会话创建开始的累计运行时长，每秒递增（通过 `requestAnimationFrame` 节流）。
- **Tokens**: 本会话累计 LLM Token 消耗（千分位格式化）。
- **Pending Badge**: 当前会话中处于 `HUMAN_REVIEW_*` 状态的阶段数量；点击直接跳转最新待审核阶段。

### 2.3 阶段时间线组件（StageTimeline）

垂直时间线，位于页面左侧固定宽度区域（桌面端 320px，可折叠）。

```
StageTimeline
|
|-- [Green] INITIALIZATION        10:00  (2m)
|      已完成
|
|-- [Blue]  EXPLORATION           10:02  (15m)
|      进行中 ----> [实时日志]
|
|-- [Gray]  HUMAN_REVIEW_EXPLORATION
|      未开始
|
|-- [Gray]  PLANNING
|      未开始
|
|-- [Gray]  HUMAN_REVIEW_PLANNING
|      未开始
|
|-- [Gray]  DEVELOPMENT
|      未开始
|
|-- [Gray]  REVIEW
|      未开始
|
|-- [Gray]  HUMAN_REVIEW_CODE
|      未开始
|
|-- [Gray]  TESTING
|      未开始
|
|-- [Gray]  HUMAN_REVIEW_TESTING
|      未开始
|
|-- [Gray]  COMPLETION
|      未开始
```

**交互设计**：
- 点击任意阶段节点 → 右侧主区域切换至该阶段详情（日志、产物摘要、审核历史）。
- 当前激活阶段高亮（左侧边框 3px 主色）。
- 人工审核阶段节点右侧显示决策按钮快捷入口（仅 `reviewer` 可见）。
- 时间线支持折叠/展开（点击阶段名称旁 Chevron）。

**状态图标**：
| 状态 | 图标 | 颜色 |
|------|------|------|
| 未开始 | Circle | `text-muted-foreground` |
| 进行中 | Loader2 (spin) | `text-blue-500` |
| 待审核 | AlertCircle | `text-orange-500` |
| 已完成 | CheckCircle2 | `text-green-500` |
| 失败 | XCircle | `text-red-500` |

### 2.4 实时日志流（RealtimeLogStream）

位于主内容区底部可折叠面板，高度默认 240px，可拖拽调整（`react-resizable-panels`）。

**视觉风格**：xterm.js 风格暗色终端，字体 `JetBrains Mono` 或 `Fira Code`。

```
+---------------------------------------------------------------+
| [Terminal] Agent Logs                              [Collapse] |
+---------------------------------------------------------------+
| [10:02:15] [Explorer] Scanning riscv-linux mailing list...   |
| [10:02:18] [Explorer] Found 3 potential opportunities        |
| [10:02:20] [Explorer] Validating opportunity #1...           |
| [10:02:22] [Explorer] Code existence check passed            |
| [10:02:25] [Explorer] Cross-validation passed                |
| [10:02:28] [Explorer] RAG spec reference confirmed           |
| [10:02:30] [Explorer] Outputting final report                |
| > _                                                           |
+---------------------------------------------------------------+
```

**功能规格**：
- 自动滚动到底部（`autoScroll` 开关，默认开启）。
- 支持按 Agent 名称过滤（多选下拉）。
- 支持按日志级别过滤（INFO / WARN / ERROR / DEBUG）。
- 搜索高亮：输入关键词后，匹配行高亮黄色背景，支持 `Enter` 跳转到下一条。
- 导出：按钮“Download Logs”下载当前会话完整日志（`.log` 文件）。

**性能优化**：
- 日志条目上限 10,000 条，超出时丢弃最早 20% 并显示提示“Older logs truncated”。
- 使用 `react-window` 或 `react-virtuoso` 虚拟滚动，避免 DOM 爆炸。

---

## 3. 人工审核界面（核心）

### 3.1 页面路由与入口

- **路由**: `/sessions/:id/review/:stage`
- **`:stage` 枚举值**: `exploration` | `planning` | `code` | `testing`
- **进入条件**: 该会话的 `current_stage` 必须处于对应的 `HUMAN_REVIEW_*` 状态，否则显示“当前阶段无需人工审核”提示页，并提供返回会话详情按钮。

### 3.2 全局布局（桌面端三栏）

```
+---------------------------------------------------------------------------------------------+
| [ReviewHeader] Session #12345 | Stage: HUMAN_REVIEW_CODE | Status: AWAITING_DECISION       |
+---------------------------------------------------------------------------------------------+
| LeftPanel (280px)       | CenterPanel (flex: 1)            | RightPanel (360px)             |
|                         |                                  |                                |
| [FileTreeNavigator]     | [ArtifactViewer]                 | [DecisionPanel]                |
| - repo/                 |                                  |                                |
|   - arch/               |  [DiffView / ReportView]         |  [ActionButtons]               |
|     - riscv/            |                                  |  [CommentEditor]               |
|       - Kconfig         |  [MonacoEditor / Markdown]       |  [IssueList]                   |
|       - Makefile        |                                  |  [HistoryTimeline]             |
|       - patch.c         |                                  |                                |
| ...                     |                                  |                                |
+---------------------------------------------------------------------------------------------+
```

**面板说明**：
- **LeftPanel**: 产物文件树导航（仅在 `code` 阶段展示代码 Diff；其他阶段展示报告章节树）。
- **CenterPanel**: 产物主查看区，根据阶段类型渲染 Diff 查看器或报告渲染器。
- **RightPanel**: 决策面板，固定宽度，包含操作按钮、注释编辑器、问题列表、历史决策时间线。

### 3.3 代码 Diff 查看器（CodeDiffViewer）

**技术选型**: Monaco Editor（VS Code 内核），原因：
- 原生支持 Diff 模式（`originalModel` / `modifiedModel`）。
- 支持行内注释（Glyph Margin Decoration + Content Widget）。
- 语法高亮覆盖 C/C++、Assembly、Makefile、Kconfig 等 RISC-V 项目常用语言。
- 支持 minimap、行号跳转、代码折叠。

**组件层级**：
```
CodeDiffViewer
|-- FileTreeNavigator (左侧文件树)
|   |-- FileTreeNode (递归渲染目录/文件)
|   |   |-- FileIcon (根据扩展名选择图标)
|   |   |-- ChangeStatsBadge (+12 / -5)
|   |   |-- ReviewStatusDot (该文件是否有未处理 Issue)
|
|-- DiffEditor (Monaco 实例)
|   |-- OriginalModel (base commit)
|   |-- ModifiedModel (patch)
|   |-- InlineCommentWidget (行内注释浮层)
|   |-- DecorationLayer (severity 颜色标记)
|
|-- DiffStatsBar (底部统计条)
    |-- TotalFilesChanged
    |-- TotalAdditions (绿)
    |-- TotalDeletions (红)
    |-- JumpToNextIssue (按钮)
```

**交互规格**：
1. **文件树导航**：
   - 点击文件 → CenterPanel 切换至该文件的 Diff。
   - 文件节点右侧显示变更统计（`+added / -removed`）。
   - 若该文件存在审核 Issue，节点左侧显示对应 severity 颜色的圆点。
   - 支持 `Cmd+Click` / `Ctrl+Click` 多选文件进行批量操作（见 3.6 批量操作）。

2. **Diff 渲染**：
   - 默认 side-by-side 模式，支持切换至 inline 模式（工具栏按钮）。
   - 变更行背景色：新增 `#e6ffec` / 删除 `#ffebe9`（GitHub 风格）。
   - 支持 `?w=1` 忽略空白变更（工具栏 Toggle）。

3. **行内注释**：
   - 点击行号旁的 `+` 图标 → 弹出 Markdown 编辑器浮层。
   - 注释支持 `@mention` 语法（高亮并通知相关用户）。
   - 注释保存后，该行号旁显示注释数量 Badge。
   - 注释可编辑/删除（仅创建者或 admin）。

4. **Severity 颜色标记**：
   审核 Issue 关联到具体行时，在 Monaco 的 Glyph Margin 渲染对应颜色竖条：
   | Severity | 颜色 | 用途 |
   |----------|------|------|
   | CRITICAL | `#dc2626` (红) | 阻塞性问题，必须修复 |
   | HIGH | `#ea580c` (橙) | 严重问题，强烈建议修复 |
   | MEDIUM | `#ca8a04` (黄) | 一般问题，建议修复 |
   | LOW | `#2563eb` (蓝) | 轻微问题，可选修复 |

### 3.4 审核报告渲染器（ReviewReportRenderer）

用于渲染 `exploration`、`planning`、`code`（审核Agent报告）、`testing` 阶段的结构化报告。

**组件层级**：
```
ReviewReportRenderer
|-- ReportHeader
|   |-- StageTitle
|   |-- OverallVerdictBadge (PASS / NEEDS_REVISION / REJECT)
|   |-- ConfidenceScore (0-100% 环形图)
|   |-- SummaryText
|
|-- IssueListSection
|   |-- IssueFilterBar (按 severity / category / blocking 筛选)
|   |-- IssueGroup (按文件或类别分组)
|   |   |-- IssueCard (可折叠)
|   |   |   |-- SeverityBadge
|   |   |   |-- CategoryTag
|   |   |   |-- FilePath + LineRange (点击跳转)
|   |   |   |-- Description (Markdown 渲染)
|   |   |   |-- Suggestion (代码块，支持一键复制)
|   |   |   |-- BlockingIndicator (是否阻塞通过)
|   |   |   |-- ResolutionCheckbox (已解决/未解决，仅 reviewer)
|
|-- PositiveFeedbackSection (优点列表，可折叠，默认收起)
|-- AgentLogPreview (该阶段 Agent 日志摘要，可展开)
```

**IssueCard 交互**：
- 点击文件路径/行号 → 若处于 `code` 阶段，CenterPanel 的 Diff 自动滚动到对应行并高亮 3 秒。
- 每个 Issue 右侧提供“批量接受建议”复选框（见 3.6）。
- 已解决的 Issue 自动折叠并置灰，移至列表底部。

### 3.5 决策工作流（DecisionWorkflow）

位于 RightPanel 顶部，是人工审核的核心交互区。

```
+----------------------------------+
| [DecisionWorkflow]               |
+----------------------------------+
| Action Required                    |
|                                  |
| [APPROVE] [REJECT] [REQUEST_CHANGES] [ADD_NOTES] |
|                                  |
| +------------------------------+ |
| | Comment Editor (Markdown)    | |
| |                              | |
| | _                            | |
| +------------------------------+ |
|                                  |
| [Preview] [Submit Decision]      |
+----------------------------------+
```

**四按钮组规格**：

| 按钮 | 颜色 | 语义 | 注释必填 | 确认对话框 |
|------|------|------|----------|------------|
| **APPROVE** | 绿色 (`bg-green-600`) | 接受产物，进入下一阶段 | 否 | 否（但需二次确认若存在未解决 CRITICAL Issue） |
| **REJECT** | 红色 (`bg-red-600`) | 终止会话，丢弃产物 | 是 | **是**（模态框确认，防止误操作） |
| **REQUEST_CHANGES** | 橙色 (`bg-orange-600`) | 退回当前阶段，要求修改 | 是 | 否 |
| **ADD_NOTES** | 蓝色 (`bg-blue-600`) | 接受并附带注释进入下一阶段 | 是 | 否 |

**确认对话框（REJECT 专用）**：
```
+------------------------------------------+
| Confirm Rejection                          |
|                                            |
| You are about to REJECT session #12345.    |
| This will terminate the workflow and       |
| discard all generated artifacts.           |
|                                            |
| This action CANNOT be undone.              |
|                                            |
| [Cancel]          [Confirm Reject]         |
+------------------------------------------+
```

**APPROVE 安全闸口**：
- 若当前审核报告存在 `blocking == true` 且未解决的 Issue，点击 APPROVE 时弹出警告：
  "There are N blocking issues unresolved. Are you sure you want to approve?"
- 用户需勾选 "I understand the risks" 后方可确认。

**注释编辑器（CommentEditor）**：
- 基于 `react-simplemde-editor` 或自研 Markdown 编辑器。
- 支持实时预览（Split 模式）。
- 支持 `@mention` 用户（下拉选择）。
- 支持粘贴图片自动上传至对象存储并插入链接。
- 最小高度 120px，最大高度 400px（超出滚动）。
- 内容实时保存至 `localStorage`（见第 5 节）。

**提交行为**：
- 点击 Submit → 按钮进入 Loading 状态（`disabled` + Spinner）。
- 前端先乐观更新本地状态，再发送 POST 请求。
- 请求成功 → 播放成功音效（可选），推送全局通知，路由跳转至 `/sessions/:id`（阶段时间线自动刷新）。
- 请求失败 → 按钮恢复，显示错误 Toast，保留编辑器内容。

### 3.6 批量操作（BatchOperations）

当审核报告包含大量 Issue（>5 条）时，启用批量操作功能。

```
+------------------------------------------+
| [BatchOperationsBar]                     |
|                                          |
| [Checkbox] Select All (23 issues)        |
| [Accept Selected Suggestions] [Mark as Resolved] [Ignore] |
+------------------------------------------+
```

**批量接受建议**：
- 用户可在 IssueList 中勾选多条 Issue，点击 "Accept Selected Suggestions"。
- 弹出确认框："This will mark N issues as accepted and append the suggested fixes to your comment. Continue?"
- 确认后，编辑器自动追加格式化文本：
  ```markdown
  ## Accepted Suggestions
  - [ ] `riscv-atomic-missing-fence` in `arch/riscv/mm/fault.c:142` (HIGH)
  - [ ] `riscv-misaligned-access` in `arch/riscv/kernel/head.S:88` (CRITICAL)
  ```
- 此操作不改变后端状态，仅辅助生成注释内容；最终仍需人类提交决策。

---

## 4. 实时通信协议规范

### 4.1 传输层选型

- **主通道**: WebSocket（`wss://api.rv-insights.io/v1/ws/sessions/:id`）
  - 双向通信，支持客户端发送心跳与确认消息。
  - 适合高频状态更新（Agent 思考日志、实时 Token 消耗）。
- **降级通道**: Server-Sent Events (SSE)（`/v1/sessions/:id/events`）
  - 用于不支持 WebSocket 的环境（部分企业防火墙）。
  - 仅服务端推送，客户端通过 HTTP POST 发送决策。

### 4.2 消息格式（JSON Schema）

所有消息统一包装为 `Envelope`：

```typescript
interface Envelope {
  id: string;           // UUID v4，用于去重与确认
  timestamp: string;    // ISO 8601
  type: EventType;
  payload: unknown;
}

type EventType =
  | "stage_started"
  | "agent_thinking"
  | "human_review_required"
  | "stage_completed"
  | "error_occurred"
  | "token_consumed"      -- 仅在 SSE 传输层作为独立事件推送
  | "heartbeat"
  | "ack"                 -- WebSocket 专用：客户端确认
  | "connection_established"
  | "state_sync";         -- WebSocket 专用：全量状态同步
```

**各事件详细规格**：

#### `stage_started`
```typescript
interface StageStartedPayload {
  session_id: string;
  stage: Stage;
  started_at: string;
  agent_name: string;   // 触发该阶段的 Agent 标识
}
```

#### `agent_thinking`
```typescript
interface AgentThinkingPayload {
  session_id: string;
  agent_name: string;
  thought_fragment: string;  // 当前思考片段（流式输出）
  token_count: number;       // 本次片段的 Token 数
  total_tokens: number;      // 本会话累计 Token 数
}
```

#### `human_review_required`（核心）
```typescript
interface HumanReviewRequiredPayload {
  session_id: string;
  stage: Stage;              // 如 "HUMAN_REVIEW_CODE"
  artifact_summary: {
    type: "exploration" | "planning" | "code" | "testing";
    title: string;
    description: string;
    artifact_url: string;    // 指向 S3/MinIO 的完整产物下载链接
  };
  review_deadline?: string;  // 可选的审核截止期限
  previous_decisions_count: number; // 该阶段已迭代次数
}
```

#### `stage_completed`
```typescript
interface StageCompletedPayload {
  session_id: string;
  stage: Stage;
  result_summary: string;
  next_stage: Stage | null;
  duration_seconds: number;
}
```

#### `error_occurred`
```typescript
interface ErrorOccurredPayload {
  session_id: string;
  stage: Stage;
  error_code: string;        // 标准化错误码，如 "AGENT_TIMEOUT", "SANDBOX_CRASH"
  error_message: string;
  recoverable: boolean;      // 是否可自动恢复
  suggested_action?: string; // 给人类的建议操作
}
```

#### `heartbeat`（双向）
```typescript
interface HeartbeatPayload {
  client_timestamp: string;  // 客户端发送时间
  server_timestamp: string;  // 服务端回复时间
}
```
客户端每 30 秒发送一次 `heartbeat`，服务端必须在 5 秒内回复，否则客户端判定连接异常。

#### `ack`
```typescript
interface AckPayload {
  original_message_id: string; // 确认收到的消息 ID
  received_at: string;
}
```

#### `state_sync`（重连后全量同步）
```typescript
interface StateSyncPayload {
  session_id: string;
  full_state: RVInsightsState; // 完整状态对象（见主方案 4.2 节）
  missed_events: Envelope[];   // 断线期间缓存的事件（最近 100 条）
}
```

### 4.3 连接状态管理

```typescript
type ConnectionStatus =
  | "idle"           // 初始状态
  | "connecting"     // 正在建立连接
  | "connected"      // 已连接，正常通信
  | "reconnecting"   // 断线后自动重连中
  | "disconnected"   // 主动断开或重连失败达到上限
  | "degraded";      // 降级至 SSE 模式
```

**状态机转换**：
```
idle --(用户打开会话页)--> connecting
connecting --(ws.onopen)--> connected
connected --(ws.onclose)--> reconnecting
reconnecting --(成功)--> connected
reconnecting --(失败 3 次)--> degraded --(SSE  fallback)--> connected
reconnecting --(失败 5 次)--> disconnected
disconnected --(用户手动刷新)--> connecting
```

**重连策略**：
- 指数退避：第 1 次 1s，第 2 次 2s，第 3 次 4s，第 4 次 8s，上限 30s。
- 每次重连携带 `last_event_id`（最后收到的消息 ID），服务端据此推送 `missed_events`。
- 重连成功后，客户端发送 `state_sync` 请求，服务端返回全量状态 + 遗漏事件。

### 4.4 消息去重与最终一致性

**去重机制**：
- 所有消息携带全局唯一 `id`（UUID v4）。
- 客户端维护 `Set<string>` 记录最近 1000 个已处理消息 ID。
- 收到重复 `id` 的消息 → 发送 `ack` 但不处理业务逻辑。

**乱序处理**：
- 事件天然具有时间戳，但网络可能导致乱序。
- 客户端为每个 `session_id` 维护一个优先队列（最小堆），按 `timestamp` 排序。
- 收到消息后不入队直接处理，而是缓冲 200ms（`debounce`），按序处理队列中所有时间戳 < 当前时间 - 200ms 的消息。
- 对于状态更新类消息（`stage_started`, `stage_completed`），采用“Last-Write-Wins”策略，以服务端 `timestamp` 为准覆盖本地状态。

**最终一致性保证**：
1. 任何状态变更事件必须由服务端通过 WebSocket/SSE 推送，而非客户端乐观推断。
2. 客户端提交决策后，不立即跳转，而是等待服务端推送 `stage_completed` 或 `human_review_required` 事件确认。
3. 若 10 秒内未收到确认，客户端主动轮询 `GET /sessions/:id/state` 进行状态校验。

---

## 5. 离线/断线处理

### 5.1 UI 降级策略

当连接状态变为 `reconnecting` 或 `disconnected` 时，全局显示连接状态横幅（ConnectionStatusBanner）：

```
+---------------------------------------------------------------+
| [AlertTriangle] Connection lost. Reconnecting in 4s... [Retry] |  <-- 黄色横幅，高度 40px
+---------------------------------------------------------------+
```

**不同状态的 UI 行为**：

| 状态 | 横幅文案 | 审核界面状态 | 操作按钮 |
|------|----------|--------------|----------|
| `reconnecting` | "Connection lost. Reconnecting in Ns..." | 只读模式（决策按钮 disabled，编辑器 readonly） | 显示 Retry 按钮 |
| `disconnected` | "Unable to reconnect. Please check your network." | 只读模式 | 显示 Refresh Page 按钮 |
| `degraded` | "Realtime updates unavailable. Using fallback mode." | 可用，但延迟较高（SSE 轮询） | 无 |

**只读模式实现**：
- 决策按钮组添加 `disabled` 属性，Tooltip 提示 "Reconnecting..."
- CommentEditor 切换至 `readOnly` 模式，禁止输入。
- Diff 查看器与报告渲染器保持可读，但禁止添加行内注释。
- 页面顶部状态条停止实时递增，显示最后一次已知值 + "(stale)" 标签。

### 5.2 本地草稿保存（LocalStorage）

审核注释在输入时实时保存，防止页面刷新或断线导致内容丢失。

**存储键名**: `rvi_review_draft:{session_id}:{stage}:{user_id}`

**存储结构**：
```typescript
interface ReviewDraft {
  session_id: string;
  stage: string;
  user_id: string;
  comment: string;           // Markdown 原文
  created_at: string;        // 草稿创建时间
  updated_at: string;        // 最后更新时间
  selected_issues: string[]; // 批量操作中选中的 Issue ID 列表
}
```

**自动保存策略**：
- 触发条件：编辑器 `onChange` 后 debounce 1000ms。
- 保存前校验：若内容为空或仅空白字符，删除 LocalStorage 键（避免垃圾数据）。
- 最大保存时长：草稿保留 7 天，过期自动清理（读取时检查 `updated_at`）。

**草稿恢复流程**：
1. 用户进入审核页面时，检查是否存在对应草稿。
2. 若存在，弹出 Toast："You have an unsaved draft from 2 hours ago. [Restore] [Discard]"
3. 点击 Restore → 将草稿内容填充至 CommentEditor，恢复批量选择状态。
4. 点击 Discard → 删除 LocalStorage 键，使用空白编辑器。
5. 成功提交决策后 → 自动删除对应草稿键。

### 5.3 重连后的状态同步策略

**步骤 1: 连接恢复检测**
- WebSocket `onopen` 触发后，客户端发送 `state_sync` 请求，携带 `last_event_id` 和 `last_known_checkpoint_id`。

**步骤 2: 服务端响应**
- 服务端返回 `state_sync` 事件，包含：
  - `full_state`: 当前完整状态（覆盖客户端本地状态）。
  - `missed_events`: 断线期间遗漏的事件队列（按时间排序）。

**步骤 3: 客户端合并**
- 用 `full_state` 完全替换本地 `sessionState`（避免增量合并的冲突）。
- 遍历 `missed_events`，按顺序处理，跳过已处理 ID（去重 Set）。
- 更新 UI 至最新状态，隐藏连接横幅。

**步骤 4: 冲突检测**
- 若用户在断线期间于本地编辑了注释（LocalStorage 草稿），而服务端状态显示该阶段已被其他用户审核通过：
  - 弹出模态框："This review stage has been completed by another user. Your draft is preserved but cannot be submitted."
  - 提供按钮："Copy Draft to Clipboard"、"Discard Draft"。

---

## 6. 响应式设计

### 6.1 断点定义

| 断点名称 | 宽度范围 | 目标设备 |
|----------|----------|----------|
| `mobile` | < 768px | 手机 |
| `tablet` | 768px - 1024px | 平板（竖屏/横屏） |
| `desktop` | 1024px - 1440px | 笔记本/小屏显示器 |
| `wide` | > 1440px | 大屏显示器 |

### 6.2 桌面端布局（三栏）

- **布局**: LeftPanel (280px) + CenterPanel (flex: 1, min 600px) + RightPanel (360px)。
- **行为**: 三个面板均可见，RightPanel 固定（`position: sticky`），滚动时决策面板始终可见。
- **文件树**: 完整目录树展开。
- **Diff 查看器**: Side-by-side 模式，字体大小 14px。

### 6.3 平板端布局（两栏）

- **布局**: LeftPanel 折叠为图标栏（60px 宽，hover 展开至 240px）+ CenterPanel (flex: 1) + RightPanel 变为可拖拽抽屉（Drawer）。
- **行为**: 
  - 默认隐藏 RightPanel，点击顶部 "Open Decision Panel" 按钮从右侧滑出 Drawer（宽度 400px，覆盖 CenterPanel）。
  - 提交决策后 Drawer 自动关闭。
- **Diff 查看器**: Inline 模式（空间不足），字体大小 13px。

### 6.4 移动端布局（单栏 + 底部浮层）

```
+----------------------------------+
| [ReviewHeader]                   |
+----------------------------------+
| [TabBar]  Artifact | Issues | Log |
+----------------------------------+
|                                  |
|  [Tab Content Area]              |
|  (Artifact / Issues / Log)       |
|                                  |
+----------------------------------+
| [BottomSheet] Decision Panel     |
| (可拖拽展开/收起)                  |
+----------------------------------+
```

- **布局**: 单栏，所有面板通过 Tab 切换。
  - `Artifact` Tab: 渲染 Diff 或报告（垂直滚动）。
  - `Issues` Tab: 审核 Issue 列表（可展开卡片）。
  - `Log` Tab: 实时日志流（暗色终端风格）。
- **决策面板**: 底部固定浮层（BottomSheet），默认高度 120px（仅显示四按钮组），向上拖拽展开至全屏 90%（显示注释编辑器与历史）。
- **Diff 查看器**: Inline 模式，字体大小 12px，隐藏 minimap，仅显示行号。
- **文件树**: 移至 `Artifact` Tab 顶部，以水平 Breadcrumb + 下拉选择器替代。

### 6.5 触摸优化

- 所有可交互元素最小点击区域 44x44px。
- 行内注释编辑器在移动端改为底部全屏 Modal，而非浮层（避免键盘遮挡）。
- 支持双指缩放 Diff 查看器（通过 CSS `touch-action: pan-x pan-y` + 手动处理 `gesturechange`）。
- 底部决策浮层支持下滑收起（`react-spring` 或 `framer-motion` 实现手势动画）。

---

## 7. 附录：组件清单与依赖矩阵

### 7.1 核心组件清单

| 组件名 | 文件路径建议 | 职责 | 复杂度 |
|--------|--------------|------|--------|
| `DashboardLayout` | `app/(dashboard)/layout.tsx` | 全局布局（TopBar + Sidebar） | 中 |
| `AuthGuard` | `components/auth/AuthGuard.tsx` | 路由权限守卫 | 低 |
| `RoleGuard` | `components/auth/RoleGuard.tsx` | 角色渲染控制 | 低 |
| `GlobalSearch` | `components/search/GlobalSearch.tsx` | Cmd+K 全局搜索面板 | 中 |
| `NotificationCenter` | `components/notification/NotificationCenter.tsx` | 通知中心下拉 | 中 |
| `SessionStatusBar` | `app/sessions/[id]/SessionStatusBar.tsx` | 顶部状态条 | 低 |
| `StageTimeline` | `app/sessions/[id]/StageTimeline.tsx` | 阶段时间线 | 中 |
| `RealtimeLogStream` | `components/log/RealtimeLogStream.tsx` | 实时日志终端 | 高 |
| `CodeDiffViewer` | `app/sessions/[id]/review/[stage]/CodeDiffViewer.tsx` | Monaco Diff 编辑器封装 | 高 |
| `FileTreeNavigator` | `components/file-tree/FileTreeNavigator.tsx` | 文件树导航 | 中 |
| `ReviewReportRenderer` | `app/sessions/[id]/review/[stage]/ReviewReportRenderer.tsx` | 审核报告渲染 | 中 |
| `IssueCard` | `components/review/IssueCard.tsx` | 单条 Issue 卡片 | 低 |
| `DecisionPanel` | `app/sessions/[id]/review/[stage]/DecisionPanel.tsx` | 决策按钮 + 编辑器 | 高 |
| `CommentEditor` | `components/editor/CommentEditor.tsx` | Markdown 编辑器 | 中 |
| `BatchOperationsBar` | `components/review/BatchOperationsBar.tsx` | 批量操作工具栏 | 低 |
| `ConnectionStatusBanner` | `components/connection/ConnectionStatusBanner.tsx` | 连接状态横幅 | 低 |
| `MobileBottomSheet` | `components/mobile/MobileBottomSheet.tsx` | 移动端底部决策浮层 | 中 |

### 7.2 外部依赖建议

| 依赖 | 版本 | 用途 |
|------|------|------|
| `next` | ^14 | 全栈框架 |
| `@monaco-editor/react` | ^4.6 | Monaco Editor React 封装 |
| `monaco-editor` | ^0.45 | Diff 编辑器内核 |
| `react-resizable-panels` | ^1.0 | 可拖拽面板（日志区、三栏布局） |
| `react-virtuoso` | ^4.6 | 日志虚拟滚动 |
| `react-simplemde-editor` | ^5.2 | Markdown 编辑器（或自研） |
| `framer-motion` | ^11 | 动画与移动端手势 |
| `lucide-react` | ^0.300 | 图标库 |
| `tailwindcss` | ^3.4 | 样式系统 |
| `shadcn/ui` | latest | 基础 UI 组件（Button, Dialog, Toast, Tabs 等） |
| `zustand` | ^4.5 | 全局状态管理（连接状态、会话状态） |
| `zod` | ^3.22 | 运行时数据校验（WebSocket 消息、API 响应） |

### 7.3 与主方案（`rv-insights-design.md`）的衔接点

| 本文档章节 | 主方案对应章节 | 衔接说明 |
|------------|----------------|----------|
| 3.5 决策工作流 | 5.2 人工审核界面规格 | 细化四按钮交互、确认对话框、安全闸口 |
| 3.3 代码 Diff 查看器 | 5.2 完整产物（代码 Diff） | 指定 Monaco Editor 技术选型与交互细节 |
| 3.4 审核报告渲染器 | 5.2 完整产物（审核报告） | 定义 IssueCard 结构与 severity 颜色编码 |
| 4 实时通信协议 | 5.1 审核交互流程 | 将序列图中的 SSE 抽象细化为 JSON Schema 与状态机 |
| 4.2 `human_review_required` | 4.2 LangGraph 状态定义 | 事件 Payload 引用 `RVInsightsState` 中的字段 |
| 5.3 重连状态同步 | 8.2 会话恢复机制 | 前端视角补充断线恢复与冲突检测 |
| 6 响应式设计 | 2.2 总体架构图（UI 层） | 明确 Next.js 前端的多端适配策略 |

---

**文档结束**
