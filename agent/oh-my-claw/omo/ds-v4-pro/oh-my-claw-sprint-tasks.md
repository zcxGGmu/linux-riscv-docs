# oh-my-claw MVP Sprint 任务清单

> **模型**: DeepSeek V4 Pro (ds-v4-pro)
> **总目标**: 15-19 天完成 MVP（核心编排能力可用）
> **策略**: 自底向上逐层构建，每层交付后即可验证
> **生成日期**: 2026-04-26

---

## 0. 开发策略说明

### 为什么不前后端并行？

oh-my-claw 是纯 TypeScript openclaw plugin，**不存在传统 Web 应用的前后端分离**。其真实的分层架构是：

```
┌────────────────────────────────────────────────┐
│  Layer 6: 命令 / Skill / MCP                   │  ← 最外层，用户可见
│  Layer 5: Hooks (ralph-loop, fallback, ...)    │
│  Layer 4: Tools (delegate-task, LSP, ...)      │
│  Layer 3: Background Manager (concurrency)     │
│  Layer 2: Category Router (task routing)       │
│  Layer 1: Agent System (prompt engine)         │
│  Layer 0: Config / Logger / Shared             │  ← 基础层
└────────────────────────────────────────────────┘
```

**依赖关系**: L(n) 严格依赖 L(n-1)。无法并行跨层。

### 正确的策略：自底向上，同层内并行

```
Layer 0: [config] [shared] [logger] ← 可并行
  ↓
Layer 1: [agents/types] [agents/registry] [agents/prompt-builder] ← 可并行
  ↓
Layer 2: [categories] ← 单体
  ↓
Layer 3: [background/manager] [background/concurrency] [background/loop-detector] ← 可并行
  ↓
Layer 4: [delegate-task] [background-task] [LSP] [AST-grep] ← 可并行
  ↓
Layer 5: [ralph-loop] [todo-enforcer] [model-fallback] [runtime-fallback] [session-recovery] ← 可并行
  ↓
Layer 6: [commands] [skills] [MCPs] ← 可并行
```

### 每日工作流

```
每日:
  1. 选一个 task → 标记 in_progress
  2. 编写代码
  3. 编写对应测试
  4. 运行 pnpm vitest → 确认通过
  5. 标记 completed → 选下一个
  6. 阶段结束时跑集成验证
```

---

## Phase 0: 项目骨架 + 配置系统（第 1-4 天）

> **目标**: Plugin 能被 openclaw 加载，配置能解析，日志能输出，测试框架就绪

---

### Day 1: 项目初始化（4 tasks）

| # | Task | 描述 | 产出 | 估时 |
|---|------|------|------|------|
| 0.1.1 | **创建项目骨架** | 在 `extensions/oh-my-claw/` 下创建目录结构；初始化 `package.json`（name/version/main/types/scripts）；创建 `tsconfig.json`（ESM, strict, moduleResolution: bundler）；创建 `vitest.config.ts` | 目录结构 + package.json | 1h |
| 0.1.2 | **创建 Plugin Manifest** | 创建 `openclaw.plugin.json`（id/name/version/description/author/license）；确认能被 openclaw 发现 | manifest 文件 | 0.5h |
| 0.1.3 | **创建 Plugin Entry 空壳** | 创建 `src/index.ts`，实现 `definePluginEntry({ id, name, configSchema: z.object({}), register(api) { logger.info("oh-my-claw loaded"); } })`；导入 logger | 可加载的空壳 plugin | 1h |
| 0.1.4 | **验证 Plugin 加载** | 启动 openclaw gateway → 检查日志输出 "oh-my-claw loaded" → 确认无报错；创建 `.gitignore` 和 `.npmignore` | 验证通过的基准 | 0.5h |

**Day 1 验收**: `openclaw gateway --verbose` 日志中看到 "oh-my-claw loaded"，无报错。

---

### Day 2: 配置 Schema（5 tasks）

| # | Task | 描述 | 产出 | 估时 |
|---|------|------|------|------|
| 0.2.1 | **定义配置类型** | 创建 `src/config/types.ts`：`AgentOverrideConfig`, `CategoryConfig`, `BackgroundTaskConfig`, `RalphLoopConfig`, `RuntimeFallbackConfig`, `McpConfig`, `ExperimentalConfig`；每个字段有 JSDoc 注释 | 完整类型文件 | 1.5h |
| 0.2.2 | **实现 Zod Schema** | 创建 `src/config/schema.ts`：`OhMyClawConfigSchema`（含所有子 schema）；仅 MVP 字段；`safeParse()` + partial fallback | Zod schema | 2h |
| 0.2.3 | **定义默认值** | 创建 `src/config/defaults.ts`：所有配置项的默认值常量；`DEFAULT_AGENTS`, `DEFAULT_CATEGORIES`, `DEFAULT_BACKGROUND`, `DEFAULT_FALLBACK_OPTIONS` | 默认值文件 | 1h |
| 0.2.4 | **实现配置加载器** | 创建 `src/config/loader.ts`：读取项目级 `.oh-my-claw.json`；读取用户级 `~/.openclaw/oh-my-claw.json`；deep merge（递归 merge 对象，Set union 数组）；Zod parse + partial fallback；日志输出合并结果 | 加载器 | 2h |
| 0.2.5 | **配置单元测试** | 测试：合法配置通过、非法配置 safeParse 返回 default、项目级覆盖用户级、空配置文件=全默认、禁用数组 set union、deep merge 嵌套对象；≥12 case | 测试文件 | 1.5h |

**Day 2 验收**: 12+ 单元测试全部通过。

---

### Day 3: 基础设施（5 tasks）

| # | Task | 描述 | 产出 | 估时 |
|---|------|------|------|------|
| 0.3.1 | **实现结构化日志** | 创建 `src/shared/logger.ts`：`LogEntry { timestamp, level, module, sessionId?, taskId?, correlationId?, message, data?, durationMs? }`；`debug/info/warn/error` 方法；输出到 `~/.openclaw/logs/oh-my-claw.log` | logger | 1.5h |
| 0.3.2 | **实现错误边界** | 创建 `src/shared/error-boundary.ts`：`withErrorBoundary(handlerName, fn, fallback?)`；同步/异步统一包装；异常时 log error + metrics.increment；返回 fallback | error boundary | 1h |
| 0.3.3 | **实现降级管理器** | 创建 `src/shared/degradation.ts`：`DegradationManager`；`recordFailure(hookName)` 跟踪连续失败；连续 3 次 → L1 禁用 hook；连续 10 次 → L4 禁用 plugin；`isHookEnabled(hookName)` | degradation | 1.5h |
| 0.3.4 | **实现指标收集器** | 创建 `src/shared/metrics.ts`：counter/gauge/histogram（内存存储）；`increment/count/set/observe` 方法；`getSummary()` 返回最近 1h 摘要；后续可接 Prometheus | metrics | 1h |
| 0.3.5 | **基础设施单元测试** | 测试：logger 各 level 输出、error-boundary 捕获同步异常、error-boundary 捕获异步异常、degradation 3 次 → L1、degradation 10 次 → L4、metrics counter increment、metrics gauge set/get；≥10 case | 测试文件 | 1.5h |

**Day 3 验收**: 10+ 基础设施单元测试通过。

---

### Day 4: Plugin Entry 完成（4 tasks）

| # | Task | 描述 | 产出 | 估时 |
|---|------|------|------|------|
| 0.4.1 | **实现完整的 register()** | 更新 `src/index.ts`：`register(api)` 中调用 `loadPluginConfig` → 初始化 logger → 初始化 degradation → `api.registerService({ start, stop })` → 日志输出完整加载信息 | 完整 entry | 1h |
| 0.4.2 | **实现 MockPluginApi** | 创建 `src/testing/mock-api.ts`：`MockPluginApi` 实现 openclaw PluginApi 接口（空壳）；`registerTool/registerHook/registerCommand/registerService` 方法记录调用；后续集成测试使用 | mock api | 1.5h |
| 0.4.3 | **Plugin Entry 集成测试** | 测试：register() 不抛异常、config 正确解析、service start/stop 调用、配置错误时 Zod 报错 + L4 降级、日志包含 "oh-my-claw loaded"；≥5 case | 测试文件 | 1.5h |
| 0.4.4 | **配置错误处理验证** | 手动测试：`oh-my-claw.json` 写入非法 JSON → 重启 → 确保 openclaw 不崩溃 → 日志显示 L4 degradation → plugin 禁用；`oh-my-claw.json` 写入合法配置 → 重启 → 正常加载 | 验证文档 | 1h |

**Day 4 / Phase 0 验收**:
- [x] openclaw 启动无报错
- [x] 日志输出 plugin 加载信息
- [x] 配置文件修改后重启生效
- [x] 错误配置不会导致 openclaw 崩溃
- [x] 25+ 单元测试 + 5+ 集成测试全部通过

---

## Phase 1: Agent 角色体系 + Prompt Builder（第 5-9 天）

> **目标**: Sisyphus 能用角色化 prompt 回复，Intent Gate 6 种意图分类正确

---

### Day 5: Agent 类型 + 注册表（4 tasks）

| # | Task | 描述 | 产出 | 估时 |
|---|------|------|------|------|
| 1.1.1 | **定义 Agent 类型** | 创建 `src/agents/types.ts`：`AgentDefinition { id, role, description, model, temperature?, maxTokens, thinking, toolPolicy, promptTemplate, metadata }`；`AgentPromptMetadata { cost, category, triggers, useWhen, avoidWhen, keyTrigger? }`；`FallbackEntry { providers, model, variant?, thinking? }`；`ToolPolicy` 枚举 + 映射函数 | 类型文件 | 1.5h |
| 1.1.2 | **定义 PromptContext 类型** | 创建 `src/agents/prompt-builder/types.ts`：`PromptContext { agentId, agents: AvailableAgent[], tools: AvailableTool[], skills: AvailableSkill[], categories: AvailableCategory[] }`；`AvailableAgent`, `AvailableTool`, `AvailableSkill`, `AvailableCategory` | prompt context 类型 | 0.5h |
| 1.1.3 | **实现 Agent 注册表** | 创建 `src/agents/registry.ts`：`AgentRegistry` 类；`register(definition)` / `getById(id)` / `getByRole(role)` / `listAll()` / `listByCost(cost)`；支持 merge user config overrides（`mergeAgentOverrides(builtin, user)`）；根据 `disabled_agents` 过滤 | registry | 2h |
| 1.1.4 | **Agent 注册表单元测试** | 测试：register + getById、role 查询、cost 过滤、config override、disabled_agents 过滤、重复注册覆盖；≥8 case | 测试文件 | 1.5h |

---

### Day 6: MVP Agent 定义 — Sisyphus（3 tasks）

| # | Task | 描述 | 产出 | 估时 |
|---|------|------|------|------|
| 1.2.1 | **实现 Sisyphus Prompt** | 创建 `src/agents/sisyphus/default.ts`；实现 5 阶段系统：Identity + Intent Gate（6 种意图 + 路由映射表） + Key Triggers（从 agent metadata 动态提取） + Codebase Assessment（4 种状态） + Exploration（tool selection table + explore/librarian + anti-duplication） + Implementation（delegation table + category-skills guide） + Failure Recovery + Completion + Constraints（hard blocks + anti-patterns） | Sisyphus prompt | 3h |
| 1.2.2 | **实现 Intent Gate 逻辑** | 创建 `src/agents/sisyphus/intent-gate.ts`；6 种意图分类规则：research → explore 回答 | implementation → 委派 | investigation → explore + report | evaluation → analyze + propose | fix → 诊断 + 最小修复 | open-ended → Codebase Assessment；路由决策逻辑 | intent gate | 1.5h |
| 1.2.3 | **Sisyphus Prompt 单元测试** | 测试：生成 prompt 包含所有 8 个 section、Intent Gate 6 意图正确映射、Key Triggers 从 metadata 动态生成、Delegation Table 从 agents 列表生成、Hard Blocks 包含完整的反模式列表；≥6 case | 测试文件 | 1.5h |

---

### Day 7: MVP Agent 定义 — Oracle + Explore + Junior（3 tasks）

| # | Task | 描述 | 产出 | 估时 |
|---|------|------|------|------|
| 1.3.1 | **实现 Oracle Prompt** | 创建 `src/agents/oracle.ts`；Read-only 顾问 prompt：身份 + 约束（只读 + 禁止 task/edit/write） + 行为指南（approach-first mentality） + 输出规范（confidence tagging: high/medium/low + 400-line hard cap） | Oracle prompt | 1.5h |
| 1.3.2 | **实现 Explore Prompt** | 创建 `src/agents/explore.ts`；Search-only prompt：身份 + 可用工具（仅 LSP + grep + glob） + 行为指南（parallel search mandate + 停止条件） | Explore prompt | 1h |
| 1.3.3 | **实现 Sisyphus-Junior Prompt** | 创建 `src/agents/sisyphus-junior.ts`；Category-spawned executor prompt：身份 + 角色（执行者，不编排） + 约束（禁止 task 工具 → 防止无限嵌套） + model/category 参数由 spawn 时注入 | Junior prompt | 1h |

---

### Day 8: Dynamic Prompt Builder（4 tasks）

| # | Task | 描述 | 产出 | 估时 |
|---|------|------|------|------|
| 1.4.1 | **实现 Identity Section** | 创建 `src/agents/prompt-builder/identity-section.ts`；根据 agent.id 生成身份声明（如 "Your designated identity is Sisyphus"）；包含 agent.description | identity section | 0.5h |
| 1.4.2 | **实现 Tool Selection Section** | 创建 `src/agents/prompt-builder/tool-selection.ts`；将 available tools 按 cost 排序（FREE → CHEAP → EXPENSIVE）；每个 tool 输出 name + description + parameters；支持 category filter（仅显示当前 agent 允许的工具） | tool selection | 1.5h |
| 1.4.3 | **实现 Delegation Table** | 创建 `src/agents/prompt-builder/delegation-table.ts`；从 `ctx.agents` 中提取每个 agent 的 `metadata.keyTrigger`；按 role 分组（orchestration/specialist/exploration/planning/review）；生成 Markdown 表格 | delegation table | 1h |
| 1.4.4 | **实现 Policy Sections** | 创建 `src/agents/prompt-builder/policy-sections.ts`；Hard Blocks（永不 as any/@ts-ignore/空 catch/删除测试/type suppression） + Anti-Patterns（跳过 todos/delegation duplication/background polling） + Task Management 规范；Category-Skills 映射指南 | policy sections | 1.5h |

---

### Day 9: MVP Agent 组装 + 验证（4 tasks）

| # | Task | 描述 | 产出 | 估时 |
|---|------|------|------|------|
| 1.5.1 | **实现 Prompt Builder 入口** | 创建 `src/agents/prompt-builder/index.ts`：`buildAgentPrompt(agentId, ctx)`；路由到正确的 agent prompt 生成器；Sisyphus: 8 section 完整拼装；Oracle/Explore/Junior: 各自简化版 | builder entry | 1h |
| 1.5.2 | **实现 Tool Policy Hook** | 创建 `src/hooks/tool-policy/hook.ts`；注册 `before_tool_call` hook；映射 `ToolPolicy` → deny/allow list；拦截后返回 blocked: true + reason；GPT/DeepSeek 无 model-specific deny | tool policy hook | 1h |
| 1.5.3 | **在 Plugin Entry 集成 Agent 系统** | 更新 `src/index.ts`：创建 AgentRegistry → 注册 4 个 MVP agent → `api.registerHook("before_prompt_build", promptBuilderHandler, { priority: 100 })` → `api.registerHook("before_tool_call", toolPolicyHandler, { priority: 75 })` | 集成代码 | 1h |
| 1.5.4 | **Phase 1 集成验证** | 手动测试：发消息给 Sisyphus → 验证回复包含 Intent Gate 分类 + 工具表 + 委派表 + Hard Blocks；Oracle session 验证 write/edit 被拒绝；Explore session 验证 task 工具被拒绝；用户 config agent override 生效 | 验证文档 | 1h |

**Phase 1 验收**:
- [x] Sisyphus 回复包含 8 个 section 的完整 prompt
- [x] Intent Gate 对 6 种意图正确分类和路由
- [x] Oracle 无法调用 write/edit 工具
- [x] Explore 无法调用 task 工具
- [x] Junior 无法二次委派（task 被禁）
- [x] 用户 `config.agents.sisyphus.prompt_append` 生效
- [x] 禁用 agent 后不可用

---

## Phase 2: Category 路由 + delegate-task（第 10-14 天）

> **目标**: Sisyphus 能通过 delegate-task 委派任务给 Junior，正确解析 category → 参数

---

### Day 10: Category 定义 + 注册（4 tasks）

| # | Task | 描述 | 产出 | 估时 |
|---|------|------|------|------|
| 2.1.1 | **定义 Category 类型** | 创建 `src/categories/types.ts`：`CategoryDefinition { name, model, temperature, maxTokens, thinking?, description, promptAppend? }`；`ResolvedCategory { ...CategoryDefinition, resolvedModel, resolvedTemperature, ... }` | types | 0.5h |
| 2.1.2 | **实现内置分类** | 创建 `src/categories/builtin.ts`：8 个内置分类 `BUILTIN_CATEGORIES`；ds-v4-pro 统一模型，仅参数区分（见下表）；每个分类有 description + promptAppend | builtin | 1.5h |
| 2.1.3 | **实现 Category 注册表** | 创建 `src/categories/registry.ts`：`CategoryRegistry`；merge `BUILTIN_CATEGORIES` + 用户 config categories（deep merge）；`getCategory(name)` / `listCategories()`；`disabled_categories` 过滤 | registry | 1h |
| 2.1.4 | **Category 单元测试** | 测试：8 个内置分类正确注册、用户覆盖生效、disabled 过滤、未知 category 返回 undefined、merge 逻辑、temperature 范围检查；≥10 case | tests | 1.5h |

**8 内置分类参数表:**

| Category | temp | maxTokens | thinking | 适用场景 |
|----------|------|-----------|----------|---------|
| `unspecified-low` | 0.3 | 32000 | disabled | 通用低复杂度 |
| `unspecified-high` | 0.3 | 64000 | enabled (16K) | 通用高复杂度 |
| `visual-engineering` | 0.3 | 32000 | disabled | 前端/UI/UX/样式 |
| `ultrabrain` | 0.2 | 64000 | enabled (32K) | 复杂逻辑/架构决策 |
| `deep` | 0.2 | 32000 | enabled (16K) | 自主研究+执行 |
| `artistry` | 0.8 | 32000 | disabled | 创意/艺术任务 |
| `quick` | 0.1 | 16000 | disabled | 琐碎修改/typo |
| `writing` | 0.5 | 32000 | disabled | 文档/技术写作 |

---

### Day 11: Category Router（4 tasks）

| # | Task | 描述 | 产出 | 估时 |
|---|------|------|------|------|
| 2.2.1 | **实现静态 Router** | 创建 `src/categories/router.ts`：`resolveCategoryExecution(category, config)`；优先级链: user override → category default → fallback_models → system default；ds-v4-pro 简化：跳过 per-provider mapping（不需要 unstable agent 检测） | router | 2h |
| 2.2.2 | **实现模型参数合并** | 创建 `src/categories/param-merger.ts`：`mergeCategoryParams(category, agentOverride?)`；合并 category 默认参数 + agent override 参数；temperature/maxTokens/thinking 的正确优先级；`canonicalizeModelName(model)` 标准化 | merger | 1h |
| 2.2.3 | **Category Router 单元测试** | 测试：user override 优先级、fallback chain 遍历、category default、未知 category → system default、参数合并（agent override > category）、disabled category → 跳过；≥12 case | tests | 1.5h |
| 2.2.4 | **实现 Category-Skills Guide** | 创建 `src/categories/category-skills-guide.ts`；生成 category ↔ skills 的映射指南（如 visual-engineering → frontend-ui-ux, playwright）；注入到 Sisyphus prompt | guide | 1h |

---

### Day 12: delegate-task 工具 — Sync 模式（4 tasks）

| # | Task | 描述 | 产出 | 估时 |
|---|------|------|------|------|
| 2.3.1 | **定义 delegate-task Schema** | 创建 `src/tools/delegate-task/types.ts`：`DelegateTaskInput { category, subagent_type, load_skills, prompt, run_in_background, description?, task_id?, command? }`；`DelegateTaskOutput { task_id, status }`；参数校验函数 | types | 1h |
| 2.3.2 | **实现 Category Resolver** | 创建 `src/tools/delegate-task/category-resolver.ts`：接收 category → 调用 `CategoryRegistry.get()` + `resolveCategoryExecution()` → 返回 `ResolvedCategory`；subagent_type 直接指定 → 跳过 category 解析 | resolver | 1.5h |
| 2.3.3 | **实现 Sync Task 执行** | 创建 `src/tools/delegate-task/sync-task.ts`：`executeSync(api, category, prompt, skills)`；调用 `api.runtime.spawnSubagent({ agentId: "sisyphus-junior", model, temperature, systemPrompt: buildSystemContent(...) })`；`syncSessionPoller` 轮询直到 session.idle；获取结果 → 返回 | sync executor | 2.5h |
| 2.3.4 | **实现 delegate-task Tool Handler** | 创建 `src/tools/delegate-task/tools.ts`：tool schema 定义 + handler；`run_in_background: false` → sync 路径；校验 category vs subagent_type 互斥；注入 skills 到 system prompt；返回结果 | tool handler | 2h |

---

### Day 13: Skill 加载 + 端到端验证（4 tasks）

| # | Task | 描述 | 产出 | 估时 |
|---|------|------|------|------|
| 2.4.1 | **实现 Skill 加载器** | 创建 `src/tools/skill/loader.ts`：扫描 skill 目录（project `.oh-my-claw/skills/` + user `~/.openclaw/skills/` + openclaw bundled）；读取 `SKILL.md` + YAML frontmatter；`listSkills()` / `loadSkill(name)` | skill loader | 2h |
| 2.4.2 | **实现 Skill 工具** | 创建 `src/tools/skill/tools.ts`：`skill` 工具 schema + handler；加载指定 skill → 返回 SKILL.md 内容 → agent 将其注入 context | skill tool | 1.5h |
| 2.4.3 | **在 Plugin Entry 集成 Category + delegate-task** | 更新 `src/index.ts`：创建 CategoryRegistry → `api.registerHook("subagent_spawning", categoryRouterHandler, { priority: 100 })` → `api.registerTool(delegateTaskTool)` → `api.registerTool(skillTool)` | 集成 | 1h |
| 2.4.4 | **Phase 2 E2E 验证** | 场景 1: "implement a simple function" → Sisyphus 分类为 implementation → delegate-task(category="quick") → Junior 执行 → 结果回传；场景 2: "explain how X works" → Sisyphus 分类为 research → 直接回答；场景 3: category config override 生效（改 temperature → Junior 用新值） | E2E | 1h |

**Phase 2 验收**:
- [x] delegate-task 工具出现在 Sisyphus 工具列表
- [x] Sisyphus 正确选择 category 并委派
- [x] Junior 使用 category 指定的参数执行
- [x] skill 内容正确注入到 Junior context
- [x] Sync 模式: spawn → 等待 → 获取结果
- [x] category/subagent_type 互斥校验
- [x] 无效 category 名称返回错误

---

## Phase 3: Background Agent 并行执行（第 15-19 天）

> **目标**: 5+ explore agent 并行搜索，结果通过通知回传父 session
> **🎯 MVP 里程碑**: Phase 3 完成后核心编排能力即可用

---

### Day 15: ConcurrencyManager + BackgroundManager 核心（4 tasks）

| # | Task | 描述 | 产出 | 估时 |
|---|------|------|------|------|
| 3.1.1 | **定义 Background 类型** | 创建 `src/background/types.ts`：`TaskEnhancement { concurrencyKey, circuitBreaker, fallbackChain, parentSessionId, createdAt }`；`LaunchInput`；`TaskStatus`；`WindowTracker { totalCalls, lastSignature, consecutiveSame }` | types | 0.5h |
| 3.1.2 | **实现 ConcurrencyManager** | 创建 `src/background/concurrency.ts`：按 key（provider/model）分组；Promise-based queue；`acquire(key)` → 有空位立即 resolve，否则入队；`release(key)` → 出队下一个；settled-flag 防止 double-resolution；默认并发 5；`getConcurrencyLimit(key)` | concurrency manager | 2.5h |
| 3.1.3 | **实现 BackgroundManager 核心** | 创建 `src/background/manager.ts`：`BackgroundManager` 类；`launch(input)` → concurrency.acquire → depth check → `api.runtime.spawnSubagent(params)` → 注册 TaskEnhancement → 返回 childSessionKey；`getTaskStatus(taskId)` → 委托 `api.runtime.getSession()`；`cancel(taskId)` → `api.runtime.killSubagent()` | manager core | 3h |
| 3.1.4 | **Concurrency 单元测试** | 测试：limit=2 时第 3 个排队、release 后 correct dequeue、不同 key 分组独立、同一 key 的 FIFO、settled-flag 防 double-release、getConcurrencyLimit 默认/自定义；≥8 case | tests | 1.5h |

---

### Day 16: Circuit Breaker + Depth Limits + Notification（4 tasks）

| # | Task | 描述 | 产出 | 估时 |
|---|------|------|------|------|
| 3.2.1 | **实现 Loop Detector** | 创建 `src/background/loop-detector.ts`：`LoopDetector` 类；跟踪每个 session 的 tool call 窗口；signature = `"toolName::sortedInput"`；连续 ≥20 次 → `cancelTask(source="circuit-breaker")`；绝对上限 4000 → 强制熔断；每次新 tool call 重置窗口 | loop detector | 2h |
| 3.2.2 | **实现 Depth Limits** | 创建 `src/background/depth-limits.ts`：`checkDepth(parentSessionId, maxDepth=3)`；通过 openclaw session API 查询 parent chain；深度 ≥ maxDepth → 拒绝 spawn；集成到 `BackgroundManager.launch()` | depth limits | 1h |
| 3.2.3 | **实现 Notification 系统** | 创建 `src/background/notification.ts`：`markForNotification(taskId, parentSessionId)`；`buildNotificationBatch(parentId)` → 生成 `<system-reminder>` XML；单个完成: `[BACKGROUND TASK COMPLETED] ID:` + description + duration + remaining count；全部完成: `[ALL BACKGROUND TASKS COMPLETE]` 汇总表 | notification | 2h |
| 3.2.4 | **Circuit Breaker + Depth 单元测试** | 测试：连续 20 次相同签名 → 触发、不同签名 → 不触发、签名重置、绝对上限 4000、depth=3 允许、depth=4 拒绝、notification 格式正确 ≥8 case | tests | 1.5h |

---

### Day 17: background_output + background_cancel 工具（4 tasks）

| # | Task | 描述 | 产出 | 估时 |
|---|------|------|------|------|
| 3.3.1 | **实现 background_output 工具** | 创建 `src/tools/background-task/background-output.ts`；schema: task_id, block?, timeout?, full_session?, include_thinking?, message_limit?, since_message_id?；非阻塞: `getTaskStatus(taskId)` → 返回状态或结果；阻塞: 轮询直到完成或超时；支持增量获取（since_message_id） | bg-output tool | 2h |
| 3.3.2 | **实现 background_cancel 工具** | 创建 `src/tools/background-task/background-cancel.ts`；schema: taskId? (单个) / all? (所有)；单个: `backgroundManager.cancel(taskId)`；全部: 获取所有后代 task → 逐个 `api.runtime.killSubagent()`；**绝不**使用 `all=true` 因会杀死无关 task | bg-cancel tool | 1h |
| 3.3.3 | **实现 Background Notification Hook** | 创建 `src/hooks/background-notify/hook.ts`；注册 `subagent_ended` hook (priority: 100)；检查是否 oh-my-claw 管理的 task → `notification.markForNotification()`；`subagent_delivery_target` hook → 确保结果路由到正确父 session | bg-notify hook | 2h |
| 3.3.4 | **background_output/cancel 单元测试** | 测试：background_output 非阻塞返回 "still running"、完成时返回 result、timeout 处理、background_cancel 单个、background_cancel all 逐个 kill、增量获取正确窗口；≥8 case | tests | 1.5h |

---

### Day 18: delegate-task Background 模式 + 全链路集成（4 tasks）

| # | Task | 描述 | 产出 | 估时 |
|---|------|------|------|------|
| 3.4.1 | **实现 delegate-task Background 模式** | 更新 `src/tools/delegate-task/background-task.ts`：`executeBackground(api, category, prompt, skills)` → `backgroundManager.launch(config)` → 返回 task_id；30s 确认 session 创建；注册 fallback chain + category 到 session metadata | bg mode | 2h |
| 3.4.2 | **更新 delegate-task Handler** | 更新 `tools.ts`：`run_in_background: true` → background 路径；`run_in_background: false` → 原有 sync 路径；添加 `subagent_type` 参数支持（直接指定 agent type）；注入 `TaskEnhancement` 元数据 | handler update | 1h |
| 3.4.3 | **全链路集成** | 更新 `src/index.ts`：创建 BackgroundManager → `api.registerHook("subagent_spawning", bgManagerHandler, { priority: 50 })` → `api.registerHook("subagent_ended", bgNotifyHandler, { priority: 100 })` → `api.registerHook("subagent_delivery_target", bgDeliveryHandler, { priority: 100 })` → `api.registerTool(backgroundOutputTool)` → `api.registerTool(backgroundCancelTool)` | integration | 1.5h |
| 3.4.4 | **Phase 3 集成测试** | 测试：5 explore(background=true) 并行执行 → 全部完成后 notification 正确显示 → background_output 获取 result → background_cancel 取消中间 task；circuit breaker 触发熔断；depth=4 拒绝；≥5 integration cases | tests | 2h |

---

### Day 19: MVP 全链路 E2E + 收尾（4 tasks）

| # | Task | 描述 | 产出 | 估时 |
|---|------|------|------|------|
| 3.5.1 | **E2E: 完整编排流程** | 场景: 用户发 "implement auth" → Sisyphus Intent Gate 分类为 implementation → Codebase Assessment → 5 parallel explore agents → 结果收集 → delegate-task(deep) → Junior 执行 → 完成 | E2E test | 1.5h |
| 3.5.2 | **E2E: 并行搜索流程** | 场景: 用户发 "find all JWT implementations and error patterns" → 5 parallel explore agents → 全部完成 → `<system-reminder>` notification → background_output 逐个获取结果 → Sisyphus 合并回答 | E2E test | 1h |
| 3.5.3 | **错误场景验证** | 模拟: circuit breaker → agent 循环 20 次 → 熔断 → cancel；depth=4 → 拒绝 spawn；subagent error → notification 包含错误状态；category unknown → 返回明确的错误消息 | error handling | 1.5h |
| 3.5.4 | **MVP Checklist 验证** | 逐项检查 MVP 验收清单；运行完整测试套件 → 生成覆盖率报告；修复残留问题；更新 README 安装说明 | docs + checklist | 1h |

**🎯 Phase 3 / MVP 验收**:
- [x] Sisyphus 角色化 prompt + Intent Gate 6 种意图分类正确
- [x] Category 路由: 8 分类自动选择 ds-v4-pro + 参数差异
- [x] delegate-task: sync 和 background 模式正确执行
- [x] 5+ explore agent 并行执行，结果通过 `<system-reminder>` 回传
- [x] background_output 获取完成结果
- [x] background_cancel 取消运行中 task
- [x] circuit breaker 在 agent 循环时触发熔断
- [x] depth limit 阻止无限嵌套（3 层）
- [x] notification 在所有完成时正确聚合
- [x] 所有 hook 通过 `withErrorBoundary` 包裹
- [x] 80%+ 测试覆盖率
- [x] openclaw 启动无报错

---

## 附录 A: 总览

### A.1 任务统计

| Phase | 天数 | Tasks | 单元测试 | 集成测试 | E2E |
|-------|------|-------|---------|---------|-----|
| Phase 0 (骨架+配置) | 4 天 | 18 | 35+ | 5+ | 0 |
| Phase 1 (Agent 体系) | 5 天 | 15 | 14+ | 1 | 0 |
| Phase 2 (Category) | 5 天 | 16 | 22+ | 0 | 1 |
| Phase 3 (Background) | 5 天 | 16 | 24+ | 5+ | 2 |
| **总计** | **19 天** | **65** | **95+** | **11+** | **3** |

### A.2 每日产出模式

```
上午 (3-4h): 实现 2-3 个功能代码 task
下午 (2-3h): 编写对应单元测试 + 验证通过
下班前: git commit + todowrite 更新
```

### A.3 关键依赖提醒

| 阻塞关系 | 说明 |
|---------|------|
| `ConcurrencyManager` 必须在 `BackgroundManager` 之前 | BackgroundManager.launch() 调用 acquire() |
| `AgentRegistry` 必须在 `DelegateTaskCategoryResolver` 之前 | 解析 subagent_type 需要查询 registry |
| `CategoryRouter` 必须在 `delegate-task` 工具之前 | 工具 handler 调用 router |
| `BackgroundManager` 必须在 `BackgroundNotificationHook` 之前 | hook 查询 manager 状态 |
| `HookCoordinator` 必须在 `TodoEnforcerHook` 之前（Phase 4） | 互斥检查 |
| `MockPluginApi` 在 Phase 0 创建 → 后续所有测试使用 |

### A.4 风险提示

| 风险 | 影响 Phase | 缓解 |
|------|-----------|------|
| openclaw subagent API 签名不确定 | Phase 2 (delegate-task) / Phase 3 (bg) | Day 1-2 提前用 `api.runtime` 快照验证，不确定的接口先 mock |
| DeepSeek reasoning mode API 格式不明确 | Phase 1 (thinking 参数) | 用 `temperature + max_tokens` 控制而非 thinking mode；后续再适配 |
| LSP server 二进制不在 PATH | Phase 4+ (不在 MVP 范围) | 不在 MVP 范围 |
| openclaw plugin config 加载时机 | Phase 0 | Day 1 即验证 `register(api)` 中的 `api.pluginConfig` 是否可用 |