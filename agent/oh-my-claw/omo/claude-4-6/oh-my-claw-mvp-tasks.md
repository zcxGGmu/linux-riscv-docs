# oh-my-claw MVP 阶段任务清单

> 目标: 以最快速度交付可运行的 MVP，验证核心编排能力。
> 架构说明: oh-my-claw 是纯 TypeScript openclaw plugin，不存在传统的"前后端"分离。
> 真正的分层是: **基础设施层 → 核心编排层 → 韧性层 → 增强层**。
> 策略: **自底向上，逐层叠加，每层交付后即可验证**。

---

## 开发策略评估

### 为什么不是"前后端并行"？

oh-my-claw 的架构是单一 TypeScript plugin，所有模块运行在同一进程中。真正的依赖关系是：

```
配置系统 ← Agent 定义 ← Category 路由 ← delegate-task 工具
                                          ↑
                              BackgroundManager ← background_output/cancel
                                          ↑
                              Hook 系统 (ralph-loop, fallback, recovery...)
                                          ↑
                              命令 + Skill + MCP
```

这是一条**严格的依赖链**，不适合并行开发不同层。但**同一层内的模块可以并行**。

### 最优策略: 垂直切片 (Vertical Slice)

每个阶段交付一个**端到端可验证的垂直切片**：

| 阶段 | 垂直切片 | 验证方式 |
|------|---------|---------|
| MVP-0 | Plugin 能加载 + 配置能解析 | openclaw 启动不报错 |
| MVP-1 | Sisyphus 能接收消息 + 分类意图 | 发消息，看 agent 回复 |
| MVP-2 | Sisyphus 能委派任务给 Junior | delegate-task → subagent 执行 → 结果回传 |
| MVP-3 | 5 个 explore 并行 + 结果合并 | 并行搜索，看通知 + 结果 |
| MVP-4 | Ralph Loop 自驱动完成多步任务 | 给复杂任务，看自动续跑 |
| MVP-5 | API 错误自动恢复 + 模型切换 | 模拟 429，看 fallback |

**MVP = MVP-0 到 MVP-3 完成**。此时核心编排能力已可用。

---

## 阶段 0: 项目骨架 + 配置系统 (3-4 天)

> 目标: plugin 能被 openclaw 加载，配置能解析，日志能输出。

### 0.1 项目初始化 (0.5 天)

- [ ] 0.1.1 创建 `extensions/oh-my-claw/` 目录结构
- [ ] 0.1.2 初始化 `package.json` (name, version, main, types, dependencies)
- [ ] 0.1.3 配置 `tsconfig.json` (ESM, strict, paths)
- [ ] 0.1.4 创建 `openclaw.plugin.json` manifest (id, name, version, entry)
- [ ] 0.1.5 创建 `src/index.ts` 空壳 (`definePluginEntry` + 空 `register`)
- [ ] 0.1.6 验证: openclaw 能发现并加载 plugin (无报错)

### 0.2 配置 Schema (1 天)

- [ ] 0.2.1 创建 `src/config/types.ts` — 导出所有配置类型
- [ ] 0.2.2 创建 `src/config/schema.ts` — 根 Zod schema (仅 MVP 字段):
  - `agents` (AgentOverrideSchema: model, disabled, prompt_append)
  - `categories` (CategoryConfigSchema: model, thinking, disabled)
  - `disabled_agents`, `disabled_hooks`, `disabled_tools`
  - `background_task` (defaultConcurrency, maxDepth)
  - `tmux` (enabled, layout, isolation)
- [ ] 0.2.3 创建 `src/config/defaults.ts` — 所有默认值常量
- [ ] 0.2.4 创建 `src/config/loader.ts` — 多级配置加载:
  - 读取项目级 `.oh-my-claw.json`
  - 读取用户级 `~/.openclaw/oh-my-claw.json`
  - deep merge + Zod parse
- [ ] 0.2.5 单元测试: schema 合法/非法输入, 默认值, 合并逻辑 (≥10 case)

### 0.3 基础设施 (1 天)

- [ ] 0.3.1 创建 `src/shared/logger.ts` — 结构化日志 (module, sessionId, correlationId, durationMs)
- [ ] 0.3.2 创建 `src/shared/error-boundary.ts` — `withErrorBoundary()` 包装器
- [ ] 0.3.3 创建 `src/shared/degradation.ts` — DegradationManager (L0-L4 降级)
- [ ] 0.3.4 创建 `src/shared/metrics.ts` — 简单 counter/gauge/histogram (内存存储, 后续可接 prometheus)
- [ ] 0.3.5 单元测试: error-boundary 异常捕获, degradation 级别升降

### 0.4 Plugin Entry 集成 (0.5 天)

- [ ] 0.4.1 在 `src/index.ts` 的 `register(api)` 中:
  - 调用 `loadPluginConfig(api.pluginConfig)`
  - 初始化 logger, degradation manager
  - 注册 `api.registerService({ start, stop })`
- [ ] 0.4.2 验证: openclaw 启动 → plugin 加载 → 配置解析 → 日志输出 "oh-my-claw loaded"
- [ ] 0.4.3 验证: 配置错误时 → Zod 报错 → plugin 降级到 L4 → openclaw 正常运行

### 阶段 0 验收
- [ ] openclaw 启动无报错
- [ ] 日志输出 plugin 加载信息
- [ ] 配置文件修改后重启生效
- [ ] 错误配置不会导致 openclaw 崩溃

---

## 阶段 1: Agent 角色体系 + Prompt Builder (4-5 天)

> 目标: Sisyphus 能接收消息，用角色化 prompt 回复，正确分类意图。

### 1.1 Agent 类型定义 (0.5 天)

- [ ] 1.1.1 创建 `src/agents/types.ts`:
  - `AgentDefinition` (id, role, description, model, thinkingDefault, toolPolicy, promptTemplate, metadata)
  - `AgentPromptMetadata` (cost, category, triggers, useWhen, avoidWhen)
  - `FallbackEntry` (providers, model, variant, reasoningEffort, thinking)
  - `ToolPolicy` ("full" | "read-only" | "search-only") + deny/allow list 映射
- [ ] 1.1.2 单元测试: ToolPolicy → deny/allow list 转换

### 1.2 MVP Agent 定义 (1 天)

> MVP 仅需 4 个 agent: sisyphus, oracle, explore, sisyphus-junior

- [ ] 1.2.1 创建 `src/agents/sisyphus/default.ts` — Sisyphus Claude prompt:
  - Identity section
  - Intent Gate (6 种意图分类)
  - Delegation table (仅 MVP agents)
  - Hard blocks + anti-patterns
- [ ] 1.2.2 创建 `src/agents/oracle.ts` — Oracle prompt (read-only 顾问)
- [ ] 1.2.3 创建 `src/agents/explore.ts` — Explore prompt (代码搜索)
- [ ] 1.2.4 创建 `src/agents/sisyphus-junior.ts` — Junior prompt (category 执行者)
- [ ] 1.2.5 创建 `src/agents/registry.ts`:
  - `BUILTIN_AGENTS: AgentDefinition[]` (4 个)
  - `getAgentById(id)`, `getAgentsByRole(role)`
  - 合并用户 config overrides

### 1.3 Dynamic Prompt Builder — MVP 版 (1.5 天)

- [ ] 1.3.1 创建 `src/agents/prompt-builder/types.ts` — PromptContext 类型
- [ ] 1.3.2 创建 `src/agents/prompt-builder/identity-section.ts` — agent 身份生成
- [ ] 1.3.3 创建 `src/agents/prompt-builder/tool-selection.ts` — 可用工具表 (cost-sorted)
- [ ] 1.3.4 创建 `src/agents/prompt-builder/delegation-table.ts` — 委派表 (从 agent metadata 动态生成)
- [ ] 1.3.5 创建 `src/agents/prompt-builder/policy-sections.ts` — hard blocks + anti-patterns
- [ ] 1.3.6 创建 `src/agents/prompt-builder/index.ts` — `buildAgentPrompt(agentId, ctx)` 组装入口
- [ ] 1.3.7 单元测试: 给定 agents/tools/skills 列表 → 验证生成的 prompt 包含正确 section

### 1.4 Hook 集成: Prompt 注入 (1 天)

- [ ] 1.4.1 创建 `src/hooks/coordination.ts` — HookCoordinator (互斥状态管理)
- [ ] 1.4.2 创建 `src/hooks/prompt-builder/hook.ts`:
  - 注册 `before_prompt_build` hook
  - 检测当前 agentId → 查找 AgentDefinition → 调用 buildAgentPrompt → 注入
- [ ] 1.4.3 创建 `src/hooks/tool-policy/hook.ts`:
  - 注册 `before_tool_call` hook
  - 检测当前 agent 的 toolPolicy → deny 不允许的工具
- [ ] 1.4.4 在 `src/index.ts` 注册 hooks
- [ ] 1.4.5 集成测试: 发消息给 Sisyphus → 验证回复包含意图分类

### 阶段 1 验收
- [ ] Sisyphus 回复包含 Intent Gate 分类
- [ ] Oracle 无法调用 write/edit 工具 (tool policy 生效)
- [ ] 用户 config 中 `agents.sisyphus.prompt_append` 生效
- [ ] 禁用 agent (`disabled_agents: ["oracle"]`) 后 Oracle 不可用

---

## 阶段 2: Category 路由 + delegate-task (4-5 天)

> 目标: Sisyphus 能通过 delegate-task 工具委派任务给 Junior，Junior 用正确的模型执行。

### 2.1 Category 注册 (1 天)

- [ ] 2.1.1 创建 `src/categories/types.ts` — CategoryDefinition, ResolvedCategory
- [ ] 2.1.2 创建 `src/categories/builtin.ts` — 8 个内置分类 (model + thinking + description)
- [ ] 2.1.3 创建 `src/categories/registry.ts`:
  - 合并 builtin + 用户 config categories
  - `getCategory(name)`, `listCategories()`
- [ ] 2.1.4 创建 `src/categories/router.ts` — 静态 resolution pipeline:
  - user override → category default → fallback chain → connected providers
  - provider 可达性检查
  - unstable agent 检测
- [ ] 2.1.5 单元测试: resolution 优先级链, fallback, unstable 检测 (≥8 case)

### 2.2 delegate-task 工具 — Sync 模式 (1.5 天)

- [ ] 2.2.1 创建 `src/tools/delegate-task/types.ts` — tool schema, input/output types
- [ ] 2.2.2 创建 `src/tools/delegate-task/category-resolver.ts` — category → model 解析
- [ ] 2.2.3 创建 `src/tools/delegate-task/prompt-builder.ts` — 组装 subagent system prompt (skills 注入)
- [ ] 2.2.4 创建 `src/tools/delegate-task/sync-task.ts`:
  - 调用 openclaw `api.runtime.spawnSubagent()`
  - 轮询 session 直到 idle
  - 提取结果返回
- [ ] 2.2.5 创建 `src/tools/delegate-task/tools.ts` — tool 定义 + handler (sync 路径)
- [ ] 2.2.6 在 `src/index.ts` 注册 delegate-task 工具
- [ ] 2.2.7 集成测试: `task(category="quick", prompt="...")` → Junior 执行 → 结果回传

### 2.3 Skill 加载工具 (1 天)

- [ ] 2.3.1 创建 `src/tools/skill/tools.ts`:
  - `skill` 工具: 加载 SKILL.md → 注入到 agent context
  - 扫描可用 skill 目录 (project/.oh-my-claw/skills/ + user/~/.openclaw/skills/)
- [ ] 2.3.2 更新 Sisyphus prompt: 添加 available skills 列表 + `load_skills` 参数说明
- [ ] 2.3.3 集成测试: `task(category="quick", load_skills=["git-master"], prompt="...")` → skill 内容注入

### 2.4 端到端验证 (0.5 天)

- [ ] 2.4.1 E2E: 用户发 "implement a simple function" → Sisyphus 分类为 implementation → delegate-task(category="quick") → Junior 执行 → 结果回传给用户
- [ ] 2.4.2 E2E: 用户发 "explain how X works" → Sisyphus 分类为 research → 直接回答 (不委派)
- [ ] 2.4.3 验证: category config override 生效 (改 model → Junior 用新 model)

### 阶段 2 验收
- [ ] delegate-task 工具出现在 Sisyphus 的工具列表中
- [ ] Sisyphus 能正确选择 category 并委派
- [ ] Junior 使用 category 指定的模型执行
- [ ] skill 内容正确注入到 Junior 的 context

---

## 阶段 3: Background Agent 并行执行 (4-5 天)

> 目标: 5+ explore agent 并行搜索，结果通过通知回传父 session。
> 这是 MVP 的最后一块拼图 — 完成后核心编排能力即可用。

### 3.1 BackgroundManager 核心 (1.5 天)

- [ ] 3.1.1 创建 `src/background/types.ts` — TaskEnhancement, LaunchInput, TaskStatus
- [ ] 3.1.2 创建 `src/background/concurrency.ts` — ConcurrencyManager:
  - per-provider/model 并发控制
  - promise-based queue (acquire/release)
  - 默认并发 5, 可配置
- [ ] 3.1.3 创建 `src/background/manager.ts` — BackgroundManager:
  - `launch(input)` → 并发控制 → spawnSubagent → 返回 taskId
  - `getTaskStatus(taskId)` → 委托 openclaw session API
  - `cancel(taskId)` → steer/kill subagent
  - `shutdown()` → 清理所有活跃 task
- [ ] 3.1.4 单元测试: 并发控制 (limit=2, 3 个 task → 第 3 个排队), cancel, shutdown

### 3.2 Circuit Breaker (0.5 天)

- [ ] 3.2.1 创建 `src/background/loop-detector.ts`:
  - 跟踪 tool call signature (toolName + sorted input hash)
  - 连续相同 signature ≥ 20 → 触发熔断
  - 绝对上限 4000 tool calls → 触发熔断
- [ ] 3.2.2 集成到 BackgroundManager: subagent_ended hook 检查
- [ ] 3.2.3 单元测试: 连续相同 call 触发, 不同 call 不触发, 重置逻辑

### 3.3 父 Session 通知 (1 天)

- [ ] 3.3.1 创建 `src/background/notification.ts`:
  - `markForNotification(taskId, parentSessionId)`
  - `buildNotificationBatch(parentSessionId)` → 生成 `<system-reminder>` XML
  - 单个完成: 显示 task ID + description + duration + 剩余数量
  - 全部完成: 显示 `[ALL BACKGROUND TASKS COMPLETE]` + 所有 task 列表
- [ ] 3.3.2 创建 `src/hooks/background-notify/hook.ts`:
  - 注册 `subagent_ended` hook
  - 调用 notification.markForNotification
  - 注入 `<system-reminder>` 到父 session 的下一条消息
- [ ] 3.3.3 集成测试: 3 个 background task → 逐个完成 → 通知正确

### 3.4 background_output / background_cancel 工具 (1 天)

- [ ] 3.4.1 创建 `src/tools/background-task/background-output.ts`:
  - 参数: task_id, block?, timeout?, full_session?, message_limit?
  - 非阻塞: 查询 task 状态 → 返回结果或 "still running"
  - 阻塞: 轮询直到完成或超时
- [ ] 3.4.2 创建 `src/tools/background-task/background-cancel.ts`:
  - 参数: taskId? | all?
  - 单个取消: kill subagent
  - 全部取消: 遍历所有活跃 task → 逐个 kill
- [ ] 3.4.3 在 `src/index.ts` 注册两个工具
- [ ] 3.4.4 集成测试: launch → output(block=true) → 获取结果; launch → cancel → 确认取消

### 3.5 delegate-task 扩展: Background 模式 (0.5 天)

- [ ] 3.5.1 更新 `src/tools/delegate-task/tools.ts`:
  - `run_in_background: true` → 调用 backgroundManager.launch → 返回 task_id
  - `run_in_background: false` → 原有 sync 路径
- [ ] 3.5.2 更新 `src/tools/delegate-task/types.ts`: 添加 subagent_type 参数 (直接指定 agent)
- [ ] 3.5.3 E2E: Sisyphus 发起 5 个 explore(background=true) → 全部完成 → 通知 → background_output 获取结果

### 3.6 深度检查 (0.5 天)

- [ ] 3.6.1 创建 `src/background/depth-limits.ts`:
  - 查询 openclaw session 的 parent chain
  - 默认最大深度 3
  - 超过 → 拒绝 spawn, 返回错误
- [ ] 3.6.2 集成到 BackgroundManager.launch
- [ ] 3.6.3 单元测试: depth=3 允许, depth=4 拒绝

### 阶段 3 验收 (MVP 完成!)
- [ ] 5 个 explore agent 并行执行，结果正确回传
- [ ] `<system-reminder>` 通知正确显示 (单个完成 + 全部完成)
- [ ] background_output 能获取完成的 task 结果
- [ ] background_cancel 能取消运行中的 task
- [ ] circuit breaker 在 agent 循环时触发熔断
- [ ] 深度限制阻止无限嵌套

---

## ★ MVP 里程碑 ★

> 阶段 0-3 完成后，oh-my-claw 的核心编排能力已可用:
> - Sisyphus 角色化 prompt + 意图分类
> - Category 路由 + 模型自动选择
> - delegate-task 同步/异步委派
> - 5+ agent 并行执行 + 结果回传
>
> 预计工期: **15-19 天** (单人全职)
> 此后的阶段为增量增强，每个阶段独立可交付。

---

## 阶段 4: 韧性 — Ralph Loop + Todo Enforcer (3-4 天)

> 目标: agent 能自主完成多步任务，不需要人工续跑。

### 4.1 Ralph Loop (2 天)

- [ ] 4.1.1 创建 `src/hooks/ralph-loop/state.ts` — RalphLoopState 状态机:
  - active, iteration, max_iterations, completion_promise, strategy
  - 持久化到 `.oh-my-claw/ralph-loop.local.json`
- [ ] 4.1.2 创建 `src/hooks/ralph-loop/detector.ts` — 完成检测:
  - 路径 1: session messages API → 逆序扫描 assistant parts → 正则 `<promise>\s*DONE\s*</promise>`
  - 路径 2: fallback (如果 API 无结果)
- [ ] 4.1.3 创建 `src/hooks/ralph-loop/continuation.ts` — 续跑 prompt 模板
- [ ] 4.1.4 创建 `src/hooks/ralph-loop/hook.ts`:
  - 注册 `agent_end` hook (priority: 100)
  - 检查 loop active → 检测完成 → 未完成则注入续跑 prompt
  - 安全阀: max_iterations (默认 100)
- [ ] 4.1.5 创建 `src/commands/ralph-loop.ts` — `/ralph-loop` 启动, `/cancel-ralph` 停止
- [ ] 4.1.6 集成测试: 3 步任务 → 前 2 步 idle → 自动续跑 → 第 3 步完成 → `<promise>DONE</promise>` → 停止

### 4.2 Todo Continuation Enforcer (1.5 天)

- [ ] 4.2.1 创建 `src/hooks/todo-enforcer/detector.ts`:
  - 获取 session todos → 计算 incomplete count
  - 停滞检测: 连续 3 次 incomplete 不减少 → 停止
  - 连续失败上限: 5 次 + 指数退避
- [ ] 4.2.2 创建 `src/hooks/todo-enforcer/prompt.ts` — 续跑 prompt 模板 (含 todo 状态摘要)
- [ ] 4.2.3 创建 `src/hooks/todo-enforcer/hook.ts`:
  - 注册 `agent_end` hook (priority: 50)
  - 检查 HookCoordinator: Ralph active → 跳过
  - 检查 injection guard → 2s 倒计时 → 注入
- [ ] 4.2.4 更新 `src/hooks/coordination.ts`: 添加 Ralph/Todo 互斥逻辑
- [ ] 4.2.5 集成测试: 5 个 todo → agent 完成 3 个后 idle → 自动续跑 → 完成剩余 2 个

### 阶段 4 验收
- [ ] Ralph Loop 能自主完成多步任务 (≤20 iterations)
- [ ] Todo Enforcer 在 agent idle 时自动续跑
- [ ] Ralph active 时 Todo Enforcer 不触发 (互斥)
- [ ] 停滞检测正常工作 (3 次无进展 → 停止)

---

## 阶段 5: 韧性 — Model Fallback + Session Recovery (3-4 天)

> 目标: API 错误时自动切换模型，session 异常时自动恢复。

### 5.1 Model Fallback — Agent-Aware 层 (1 天)

- [ ] 5.1.1 创建 `src/hooks/model-fallback/chain-traversal.ts`:
  - 从 agent 的 fallbackChain 中选择下一个可达模型
  - provider 可达性检查 (connected providers cache)
  - no-op 跳过 (canonicalize provider+model)
- [ ] 5.1.2 创建 `src/hooks/model-fallback/hook.ts`:
  - 注册 `before_model_resolve` hook (priority: 100)
  - 检查 pending fallback flag → 替换模型
- [ ] 5.1.3 单元测试: fallback chain 遍历, 可达性过滤, no-op 跳过

### 5.2 Runtime Fallback — Error-Triggered 层 (1 天)

- [ ] 5.2.1 创建 `src/hooks/runtime-fallback/error-classifier.ts`:
  - 匹配 HTTP 错误: 429, 500, 502, 503, 504
  - 匹配文本模式: rate_limit, quota_exceeded, overloaded, try_again
- [ ] 5.2.2 创建 `src/hooks/runtime-fallback/fallback-state.ts`:
  - FallbackState: originalModel, currentModel, fallbackIndex, attemptCount
  - cooldown: 60s per failed model, max 3 attempts
- [ ] 5.2.3 创建 `src/hooks/runtime-fallback/hook.ts`:
  - 注册 `llm_output` hook (priority: 50)
  - 检测错误 → abort → 用 fallback model 重发 last user message
- [ ] 5.2.4 集成测试: 模拟 429 → fallback 到备用模型 → 成功

### 5.3 Session Recovery (1.5 天)

- [ ] 5.3.1 创建 `src/hooks/session-recovery/error-classifier.ts`:
  - 5 种错误模式分类 (tool_result_missing, unavailable_tool, thinking_block_order, thinking_disabled_violation, assistant_prefill_unsupported)
- [ ] 5.3.2 创建 `src/hooks/session-recovery/handlers/`:
  - `tool-result-missing.ts` — 注入 synthetic error result
  - `unavailable-tool.ts` — 注入 "tool not available" result
  - `thinking-block.ts` — 重排/剥离 thinking blocks
- [ ] 5.3.3 创建 `src/hooks/session-recovery/hook.ts`:
  - 注册 `llm_output` hook (priority: 100)
  - 去重 (processingErrors Set)
  - 分类 → 调用对应 handler → auto-resume
- [ ] 5.3.4 更新 `src/hooks/coordination.ts`: recovery active → 抑制 runtime fallback
- [ ] 5.3.5 集成测试: 模拟 tool_result_missing → 自动注入 → session 恢复

### 阶段 5 验收
- [ ] API 429 → 自动切换到 fallback 模型 (≤3 次)
- [ ] tool_result_missing → 自动注入 synthetic result → session 恢复
- [ ] thinking_disabled_violation → 自动剥离 → session 恢复
- [ ] recovery 中 runtime fallback 不触发 (互斥)

---

## 阶段 6: 增强工具 — LSP + AST-Grep (5-6 天)

> 目标: agent 能使用 LSP 和 AST-Grep 进行精确的代码分析和重构。

### 6.1 LSP Client 基础 (2 天)

- [ ] 6.1.1 创建 `src/tools/lsp/client-transport.ts` — JSON-RPC over stdin/stdout
- [ ] 6.1.2 创建 `src/tools/lsp/client-connection.ts` — initialize handshake + capabilities
- [ ] 6.1.3 创建 `src/tools/lsp/client.ts` — protocol methods (definition, references, symbols, diagnostics, rename)
- [ ] 6.1.4 创建 `src/tools/lsp/server-manager.ts` — LSPServerManager 单例:
  - key: `${workspaceRoot}::${serverId}`
  - 引用计数, 5min idle timeout, 60s init timeout
- [ ] 6.1.5 创建 `src/tools/lsp/server-definitions.ts` — MVP: TypeScript, Python, Go (3 个)

### 6.2 LSP 工具注册 (1.5 天)

- [ ] 6.2.1 创建 `src/tools/lsp/goto-definition.ts` — tool schema + handler
- [ ] 6.2.2 创建 `src/tools/lsp/find-references.ts`
- [ ] 6.2.3 创建 `src/tools/lsp/symbols.ts` (document + workspace scope)
- [ ] 6.2.4 创建 `src/tools/lsp/diagnostics.ts` (支持目录, severity 过滤)
- [ ] 6.2.5 创建 `src/tools/lsp/rename.ts` (prepare_rename + rename)
- [ ] 6.2.6 在 `src/index.ts` 条件注册 (仅本地通道)
- [ ] 6.2.7 集成测试: TypeScript 项目 → goto_definition → 正确跳转

### 6.3 AST-Grep 工具 (1.5 天)

- [ ] 6.3.1 创建 `src/tools/ast-grep/cli.ts` — sg binary 调用封装 (auto-download)
- [ ] 6.3.2 创建 `src/tools/ast-grep/tools.ts`:
  - `ast_grep_search` — pattern + lang + paths + globs + context
  - `ast_grep_replace` — pattern + rewrite + lang + dryRun (默认 true)
- [ ] 6.3.3 在 `src/index.ts` 条件注册 (仅本地通道)
- [ ] 6.3.4 集成测试: `ast_grep_search(pattern="console.log($MSG)", lang="typescript")` → 找到匹配

### 阶段 6 验收
- [ ] LSP goto_definition 在 TypeScript 项目中正常工作
- [ ] LSP diagnostics 返回正确的错误/警告
- [ ] AST-grep search 找到 pattern 匹配
- [ ] AST-grep replace (dryRun) 显示正确的预览
- [ ] 非本地通道 (Discord) 不注册 LSP/AST-grep 工具

---

## 阶段 7: 增强 Hooks + 命令 + Skill (4-5 天)

> 目标: 补齐剩余 hooks、内置命令和 skill。

### 7.1 Preemptive Compaction (0.5 天)

- [ ] 7.1.1 创建 `src/hooks/preemptive-compact/hook.ts`:
  - 注册 `after_tool_call` hook
  - token 缓存 + 78% 阈值检测 + 60s cooldown
  - 触发 session.summarize()

### 7.2 Keyword Detector (0.5 天)

- [ ] 7.2.1 创建 `src/hooks/keyword-detector/hook.ts`:
  - 注册 `message_received` hook
  - 3 种模式: ultrawork, search, analyze
  - 多语言关键词匹配 → prepend 到首个 text part

### 7.3 Comment Checker (1 天)

- [ ] 7.3.1 创建 `src/hooks/comment-checker/hook.ts`:
  - 注册 `before_tool_call` + `after_tool_call`
  - pending call 注册 → 外部 binary 调用 → 警告追加到 tool output
- [ ] 7.3.2 条件注册 (仅本地通道)

### 7.4 内置命令 (1.5 天)

- [ ] 7.4.1 创建 `src/commands/registry.ts` — 命令注册入口
- [ ] 7.4.2 `/stop-continuation` — 停止 ralph loop + todo enforcer
- [ ] 7.4.3 `/handoff` — 生成 session 上下文摘要
- [ ] 7.4.4 `/start-work` — 从计划文件启动工作
- [ ] 7.4.5 `/refactor` — 智能重构 (LSP + AST-grep + 6 阶段)

### 7.5 内置 Skill (1 天)

- [ ] 7.5.1 创建 `skills/git-master/SKILL.md` — 3-mode git 专家
- [ ] 7.5.2 创建 `skills/review-work/SKILL.md` — 5-agent 并行审查
- [ ] 7.5.3 创建 `skills/ai-slop-remover/SKILL.md` — AI 代码异味清除
- [ ] 7.5.4 创建 `src/skills/registry.ts` — 内置 skill 注册

### 阶段 7 验收
- [ ] Preemptive compaction 在 78% context 时触发
- [ ] Keyword "ultrawork" 触发模式切换
- [ ] /handoff 生成正确的上下文摘要
- [ ] git-master skill 正确注入到 agent context

---

## 阶段 8: 内置 MCP + 收尾 (2-3 天)

### 8.1 内置 MCP (1 天)

- [ ] 8.1.1 创建 `src/mcp/websearch.ts` — Exa MCP 注册 (HTTPS transport)
- [ ] 8.1.2 创建 `src/mcp/context7.ts` — Context7 MCP 注册
- [ ] 8.1.3 创建 `src/mcp/grep-app.ts` — Grep.app MCP 注册
- [ ] 8.1.4 在 `src/index.ts` 注册 (可通过 config 禁用)

### 8.2 Skill-Embedded MCP (0.5 天)

- [ ] 8.2.1 创建 `src/tools/skill-mcp/manager.ts` — SkillMcpManager (按需启停)
- [ ] 8.2.2 创建 `src/tools/skill-mcp/tools.ts` — skill_mcp 工具

### 8.3 诊断命令 (0.5 天)

- [ ] 8.3.1 `/omc-status` — 降级级别, 活跃 tasks, hook 状态, LSP servers
- [ ] 8.3.2 `/omc-metrics` — 最近 1h 关键指标摘要

### 8.4 文档 + 示例配置 (0.5 天)

- [ ] 8.4.1 创建 3 个示例配置: minimal, standard, full
- [ ] 8.4.2 README: 安装、配置、功能概览

### 阶段 8 验收
- [ ] Exa web search 通过 MCP 可用
- [ ] Context7 docs 查询可用
- [ ] /omc-status 显示正确的 plugin 状态

---

## 总工期估算

| 阶段 | 内容 | 工期 (单人) | 累计 |
|------|------|-----------|------|
| 0 | 骨架 + 配置 | 3-4 天 | 3-4 天 |
| 1 | Agent + Prompt Builder | 4-5 天 | 7-9 天 |
| 2 | Category + delegate-task | 4-5 天 | 11-14 天 |
| 3 | Background Agent | 4-5 天 | **15-19 天 (MVP)** |
| 4 | Ralph Loop + Todo | 3-4 天 | 18-23 天 |
| 5 | Fallback + Recovery | 3-4 天 | 21-27 天 |
| 6 | LSP + AST-Grep | 5-6 天 | 26-33 天 |
| 7 | Hooks + Commands + Skills | 4-5 天 | 30-38 天 |
| 8 | MCP + 收尾 | 2-3 天 | **32-41 天 (完整版)** |

**MVP (阶段 0-3): 约 3-4 周**
**完整版 (阶段 0-8): 约 7-9 周**
