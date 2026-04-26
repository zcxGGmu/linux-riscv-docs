# oh-my-claw 项目设计方案（详细版）

> **模型配置**: DeepSeek V4 Pro (ds-v4-pro)
> **参考项目**: [oh-my-openagent](https://github.com/code-yeongyu/oh-my-openagent) (OmO) v3.17.5 — opencode 增强插件
> **宿主项目**: [openclaw](https://github.com/openclaw/openclaw) v2026.4.24 — 多通道 AI 网关
> **生成日期**: 2026-04-25
> **关联方案**: [claude-4-6 方案](../claude-4-6/oh-my-claw-design.md)（模型变体参考）

---

## 目录

1. [背景与定位](#1-背景与定位)
2. [能力差距分析](#2-能力差距分析)
3. [架构设计](#3-架构设计)
4. [核心模块详细设计](#4-核心模块详细设计)
5. [Hook 优先级矩阵与冲突解决](#5-hook-优先级矩阵与冲突解决)
6. [韧性架构 (Resilience)](#6-韧性架构-resilience)
7. [通道兼容性矩阵](#7-通道兼容性矩阵)
8. [配置系统](#8-配置系统)
9. [实施路线图](#9-实施路线图)
10. [技术栈](#10-技术栈)
11. [测试策略](#11-测试策略)
12. [安全考量](#12-安全考量)
13. [可观测性与日志](#13-可观测性与日志)
14. [风险与应对](#14-风险与应对)
15. [附录](#15-附录)

---

## 1. 背景与定位

### 1.1 三项目关系

```
opencode (Go, TUI 编码助手)
    └── oh-my-openagent (纯插件) — 将单 agent → 多模型编排团队
            ├── 11 个专家 agent（Sisyphus/Oracle/Hephaestus/Prometheus/...）
            ├── 52 个生命周期 hook（5 层：Session/Tool-Guard/Transform/Continuation/Skill）
            ├── 26 个自定义工具（LSP×6 + AST-Grep×2 + Hashline + 背景任务 + ...）
            ├── 8 个任务分类（visual-engineering/ultrabrain/deep/artistry/quick/...）
            ├── 3 层 MCP 系统（内置 + .mcp.json + skill-embedded）
            └── BackgroundManager（5+ agent 并行执行 + circuit breaker）

openclaw (TS, 多通道 AI 网关)
    └── oh-my-claw (纯插件, 本项目) — 对标 OmO, 在 openclaw 上实现同等增强
            ├── 将 OmO 的编码编排能力完整移植到 openclaw 网关架构
            ├── 利用 openclaw 已有的 28 个 hook + 53 个 skill + 25+ 通道
            ├── 利用 openclaw 独有的 memory 系统 + cron 调度 + ACP 协议
            └── 主线模型使用 DeepSeek V4 Pro（高性价比推理模型）
```

### 1.2 设计哲学

继承 OmO 核心理念，与 openclaw 深度资产复用：

- **"Human intervention is a failure signal"** — agent 应自主完成，减少人工干预
- **专家分工** — 不同任务由不同专家 agent 处理（角色化 prompt + 工具策略）
- **韧性优先** — 双层 fallback、5 种 session 恢复、5 级优雅降级
- **质量管控** — AI slop 检测（Comment Checker）、计划审查（Momus）、Oracle 验证
- **Channel-agnostic** — 核心编排能力在所有通道上一致可用
- **薄增强层** — 复用 openclaw 原生能力（session/memory/plugin-sdk/subagent），仅在关键路径上增强

### 1.3 与 claude-4-6 方案的关键差异

| 维度 | claude-4-6 方案 | ds-v4-pro 方案（本方案） |
|------|----------------|------------------------|
| 主编排模型 | Claude Opus 4 | DeepSeek V4 Pro |
| 模型变体 | 4 种（Claude/GPT/GPT-5.5/Gemini 各一套 prompt） | 单一模型，prompt 统一 |
| 成本 | Opus 昂贵 | 高性价比 |
| 推理预算 | extended thinking (32K token budget) | 原生 reasoning（deepseek 推理模型） |
| prompt 工程 | 按模型族拆分（4 套 Sisyphus prompt） | 统一 prompt + 参数区分 |
| Category 路由 | 每 category 按 provider 分组选最优模型 | 统一使用 ds-v4-pro，参数区分 |
| 核心编排逻辑 | **完全一致** | **完全一致** |

> **简化收益**: 因为只有单一模型（DeepSeek V4 Pro），不需要 OmO 的 4 套模型变体 prompt、不需要 per-provider category 定义、不需要 unstable agent 检测。这使代码量减少约 **30-40%**，同时降低维护成本。

---

## 2. 能力差距分析

### 2.1 openclaw 已具备的能力 ✅（oh-my-claw 可直接复用）

| 系统 | 现状 | 详细说明 | oh-my-claw 复用方式 |
|------|------|---------|-------------------|
| 多 Agent | ✅ 完整 | `agents.list[]` 配置，独立 workspace/session/skills/sandbox | 通过 `before_agent_start` hook 注入角色化 prompt |
| Plugin Hook | ✅ 28 种 | void(并行) / modifying(顺序合并) / claiming(首位胜出) | 直接注册 22+ handler，利用 priority 排序 |
| MCP | ✅ 双向 | stdio + HTTP/SSE | 额外注册 3 个内置远程 MCP |
| Skill 系统 | ✅ 53 内置 | SKILL.md + ClawHub 市场 | 复用，额外注册 3 个专属 skill |
| Context Engine | ✅ 可插拔 | bootstrap/ingest/assemble/compact | 复用 compaction API，增加 preemptive 触发 |
| Memory 系统 | ✅ 高级 | embedding + decay + dreaming + QMD | 集成用于 agent 学习 + 历史成功率 + 用户偏好 |
| Cron 调度 | ✅ | 隔离 agent 定时执行 | 注册 3 个维护 cron job |
| ACP 协议 | ✅ | Codex/Claude Code 集成 | delegate-task 扩展支持外部 harness |
| 25+ 通道 | ✅ | Discord/Slack/Telegram/WhatsApp... | channel-aware 工具注册 |
| 120+ Provider | ✅ | DeepSeek/OpenAI/Anthropic/... | 无需改动 |
| Subagent API | ✅ | spawn(fork/isolated) / steer / kill | 封装为 BackgroundManager 薄增强层 |
| Plugin SDK | ✅ | `registerTool/registerHook/registerCommand` | 全部使用 |

### 2.2 openclaw 缺失的能力 ❌ — oh-my-claw 要实现

#### P0 — 核心编排（MVP 边界，15-19 天）

| # | 能力 | OmO 实现 | openclaw 现状 | oh-my-claw ds-v4-pro 方案 |
|---|------|---------|-------------|--------------------------|
| 1 | **专家 Agent 角色体系** | 11 角色 + 4 套模型变体 prompt | agent = 配置项，无角色化 | 11 角色 + 统一 ds-v4-pro prompt + tool policy 控制 |
| 2 | **Category 路由系统** | 8 分类 × 4 套 provider 映射 | 无 | 8 分类，统一 ds-v4-pro + 参数差异化 |
| 3 | **Background Agent 并行** | BackgroundManager + 并发控制 | subagent 串行 | 薄增强层 + concurrence + circuit breaker |

#### P1 — 质量与韧性

| # | 能力 | OmO 实现 | oh-my-claw ds-v4-pro 方案 |
|---|------|---------|--------------------------|
| 4 | **Ralph Loop** | session.idle → promise 检测 → 续跑 | 双路径检测 + 状态机 + ultrawork 变体 |
| 5 | **Todo Enforcer** | idle + incomplete todo → 注入 | 停滞检测 + 指数退避 + compaction guard |
| 6 | **Model Fallback** | 双层（pre-request + runtime） | 双层 + 错误分类 + cooldown |
| 7 | **Session Recovery** | 5 种错误自动恢复 | 5 种错误模式 + 去重 Set |
| 8 | **LSP 工具集** | 6 tools + 3 层 client | 6 tools + LSPServerManager 单例 + 35 server |
| 9 | **AST-Grep** | search/replace + 25 语言 | sg CLI 自动下载 + dry-run 默认 |

#### P2 — 增强体验

| # | 能力 | OmO 实现 | oh-my-claw ds-v4-pro 方案 |
|---|------|---------|--------------------------|
| 10 | **Preemptive Compaction** | 78% 阈值 + token 缓存 | 同 |
| 11 | **Comment Checker** | 外部 binary AI slop 检测 | 同 + pending call 注册 |
| 12 | **Dynamic Prompt Builder** | 模块化 prompt 组装 | 简化：统一 prompt + 动态 tool/delegation/constraint sections |
| 13 | **Hashline Edit** | LINE#ID hash 锚定编辑 | xxHash32 + 验证 pipeline |
| 14 | **Skill-Embedded MCP** | skill 声明 mcpConfig | SkillMcpManager 按需启停 |
| 15 | **Builtin MCP** | Exa + Context7 + Grep.app | 同 |

#### P3 — 高级特性

| # | 能力 | OmO 实现 | oh-my-claw ds-v4-pro 方案 |
|---|------|---------|--------------------------|
| 16 | **Keyword Detector** | 3 模式 + 多语言 | 同 |
| 17 | **Rules Injector** | 层级 AGENTS.md + /init-deep | 同 |
| 18 | **Interactive Bash** | tmux 集成终端 | 同 |
| 19 | **Team Mode** | tmux 多 agent 可视化 | 同 |

---

## 3. 架构设计

### 3.1 整体架构

```
┌──────────────────────────────────────────────────────────────────┐
│                        openclaw                                   │
│  gateway · agents · channels · plugins · context-engine           │
│  sessions · memory · cron · mcp · tasks · routing                 │
├──────────────────────────────────────────────────────────────────┤
│                    oh-my-claw plugin                               │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                    Plugin Entry                            │    │
│  │  definePluginEntry → register(api) →                     │    │
│  │  config → managers → tools → hooks                        │    │
│  ├───────────┬─────────┬─────────┬─────────┬───────────────┤    │
│  │  Agents   │Category │Backgnd  │ Tools   │    Hooks       │    │
│  │  (11)     │ Router  │ Manager │ (20+)   │    (22+)       │    │
│  │           │ (8 cat) │         │         │                │    │
│  │ sisyphus  │ visual  │concurr. │ LSP(6)  │ ralph-loop     │    │
│  │ oracle    │ eng.    │ mgr     │AST-grep │ todo-cont      │    │
│  │ hephaestus│ ultra-  │circuit  │delegate │ model-fallback │    │
│  │ prometheus│ brain   │breaker  │ bg-task │ runtime-fb     │    │
│  │ explore   │ deep    │depth    │hashline │ session-rcvry  │    │
│  │ librarian │ quick   │ limit   │ skill   │ preempt-compact│    │
│  │ metis     │ artistry│parent   │ skill-  │ comment-check  │    │
│  │ momus     │ writing │ notify  │  mcp    │ keyword-detect │    │
│  │ atlas     │ unspec* │         │ grep    │ prompt-build   │    │
│  │ junior    │         │         │ glob    │ rules-inject   │    │
│  │ m-looker  │         │         │ look-at │ bg-notify      │    │
│  ├───────────┴─────────┴─────────┴─────────┴───────────────┤    │
│  │  Skills (git-master, review-work, ai-slop-remover)       │    │
│  ├──────────────────────────────────────────────────────────┤    │
│  │  MCPs (Exa websearch, Context7 docs, Grep.app)           │    │
│  ├──────────────────────────────────────────────────────────┤    │
│  │  Commands (/ralph-loop /refactor /start-work /handoff)   │    │
│  ├──────────────────────────────────────────────────────────┤    │
│  │  Config (.oh-my-claw.json — Zod schema validation)       │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 集成方式

oh-my-claw 作为 openclaw extension 接入，通过 `openclaw/plugin-sdk` 的 `definePluginEntry` API：

```typescript
// extensions/oh-my-claw/src/index.ts
import { definePluginEntry } from "openclaw/plugin-sdk";

export default definePluginEntry({
  id: "oh-my-claw",
  name: "Oh My Claw",
  description: "Multi-model orchestration plugin — powered by DeepSeek V4 Pro",
  configSchema: ohMyClawConfigSchema,

  register(api) {
    // 1. 加载配置
    const config = loadPluginConfig(api.pluginConfig);

    // 2. 创建单例 managers
    const degradationManager = new DegradationManager(config);
    const hookCoordinator = new HookCoordinator();
    const backgroundManager = new BackgroundManager(api, config.background);
    const skillMcpManager = new SkillMcpManager(api);
    const notifier = api.runtime.channelType === "terminal"
      ? new ToastNotifier(api) : new ChannelMessageNotifier(api);

    // 3. 注册工具 (channel-aware)
    const isLocal = ["terminal", "acp"].includes(api.runtime.channelType);

    registerDelegateTaskTool(api, config);
    registerBackgroundTaskTools(api, backgroundManager);
    if (isLocal) {
      registerLspTools(api, config);
      registerAstGrepTools(api, config);
      registerHashlineEditTool(api, config);
    }
    registerSkillTool(api);
    registerSkillMcpTool(api, skillMcpManager);

    // 4. 注册 hooks (带 priority 和 withErrorBoundary)
    api.registerHook("before_prompt_build",
      withErrorBoundary("prompt-builder", promptBuilderHandler), { priority: 100 });
    api.registerHook("before_prompt_build",
      withErrorBoundary("rules-injector", rulesInjectorHandler), { priority: 50 });

    api.registerHook("agent_end",
      withErrorBoundary("ralph-loop", ralphLoopHandler), { priority: 100 });
    api.registerHook("agent_end",
      withErrorBoundary("todo-enforcer", todoEnforcerHandler(hookCoordinator, notifier)), { priority: 50 });

    api.registerHook("before_model_resolve",
      withErrorBoundary("model-fallback", modelFallbackHandler), { priority: 100 });

    api.registerHook("llm_output",
      withErrorBoundary("session-recovery", sessionRecoveryHandler), { priority: 100 });
    api.registerHook("llm_output",
      withErrorBoundary("runtime-fallback", runtimeFallbackHandler(hookCoordinator)), { priority: 50 });

    api.registerHook("before_tool_call",
      withErrorBoundary("hashline-validation", hashlineValidationHandler), { priority: 100 });
    api.registerHook("before_tool_call",
      withErrorBoundary("comment-checker-register", commentCheckerRegisterHandler), { priority: 50 });
    api.registerHook("after_tool_call",
      withErrorBoundary("comment-checker-detect", commentCheckerDetectHandler), { priority: 100 });
    api.registerHook("after_tool_call",
      withErrorBoundary("preemptive-compact", preemptiveCompactHandler), { priority: 50 });

    api.registerHook("subagent_spawning",
      withErrorBoundary("category-router", categoryRouterHandler), { priority: 100 });
    api.registerHook("subagent_spawning",
      withErrorBoundary("background-manager", backgroundManagerHandler), { priority: 50 });

    api.registerHook("subagent_ended",
      withErrorBoundary("bg-notify", backgroundNotifyHandler), { priority: 100 });

    api.registerHook("message_received",
      withErrorBoundary("keyword-detector", keywordDetectorHandler), { priority: 100 });

    // 5. 注册命令
    registerBuiltinCommands(api);

    // 6. 注册 MCP
    registerBuiltinMcps(api, config);

    // 7. 注册 service (lifecycle)
    api.registerService({
      id: "oh-my-claw",
      start: () => backgroundManager.start(),
      stop: () => backgroundManager.shutdown(),
    });

    logger.info("oh-my-claw loaded", {
      agents: 11, categories: 8, hooks: 22, localTools: isLocal,
      degradationLevel: degradationManager.level,
    });
  },
});
```

### 3.3 目录结构

```
extensions/oh-my-claw/
├── openclaw.plugin.json          # Plugin manifest
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts                  # Plugin entry (definePluginEntry + register)
│   │
│   ├── config/
│   │   ├── schema.ts             # Zod schema (完整配置)
│   │   ├── loader.ts             # 多级配置: project > user > defaults
│   │   ├── defaults.ts           # 默认值常量
│   │   └── types.ts              # 导出类型
│   │
│   ├── agents/                   # 角色化 agent 定义
│   │   ├── registry.ts           # Agent 注册表 + createBuiltinAgents()
│   │   ├── types.ts              # AgentDefinition, AgentPromptMetadata, FallbackEntry
│   │   ├── prompt-builder/       # 动态 prompt 组装（ds-v4-pro 统一模板）
│   │   │   ├── core-sections.ts  # Identity + Key Triggers + Tool Selection
│   │   │   ├── policy-sections.ts # Hard Blocks + Anti-Patterns
│   │   │   ├── delegation-table.ts # 从 agent metadata 动态生成委派表
│   │   │   ├── category-skills-guide.ts
│   │   │   └── tool-categorization.ts
│   │   ├── sisyphus/             # 编排者（5 阶段系统）
│   │   │   └── default.ts        # DeepSeek V4 Pro 主提示词
│   │   ├── oracle.ts             # 架构顾问（read-only）
│   │   ├── hephaestus.ts         # 深度执行者
│   │   ├── prometheus/           # 战略规划者（6 子模块）
│   │   │   ├── system-prompt.ts
│   │   │   ├── identity-constraints.ts
│   │   │   ├── interview-mode.ts # 7 种意图 × 研究策略
│   │   │   ├── plan-generation.ts
│   │   │   ├── high-accuracy-mode.ts # Momus 审查循环
│   │   │   └── plan-template.ts
│   │   ├── explore.ts            # 代码探索（search-only + LSP）
│   │   ├── librarian.ts          # 文档/OSS 检索（search-only）
│   │   ├── metis.ts              # 计划分析（read-only）
│   │   ├── momus.ts              # 计划审查（read-only, xhigh thinking）
│   │   ├── atlas/                # todo 编排者
│   │   ├── sisyphus-junior.ts    # category-spawned 执行者
│   │   └── multimodal-looker.ts  # 视觉分析（read only）
│   │
│   ├── categories/               # Category 路由
│   │   ├── registry.ts           # 分类注册 + 合并逻辑
│   │   ├── router.ts             # category → model resolution pipeline
│   │   ├── builtin.ts            # 8 内置分类（ds-v4-pro 统一）
│   │   ├── context-aware-router.ts # P2 动态增强层
│   │   └── types.ts
│   │
│   ├── background/               # 并行 agent 管理
│   │   ├── manager.ts            # BackgroundManager 主类
│   │   ├── concurrency.ts        # ConcurrencyManager (per-provider queue)
│   │   ├── loop-detector.ts      # Circuit breaker (20 连续 → 熔断)
│   │   ├── depth-limits.ts       # Subagent depth guard (default 3)
│   │   ├── spawner.ts            # Task spawner + fallback
│   │   ├── notification.ts       # Parent session 通知（<system-reminder>）
│   │   └── types.ts
│   │
│   ├── tools/                    # 增强工具
│   │   ├── lsp/                  # LSP 工具集 (6 tools)
│   │   │   ├── client-transport.ts   # JSON-RPC over stdin/stdout
│   │   │   ├── client-connection.ts  # initialize handshake
│   │   │   ├── client.ts             # protocol methods
│   │   │   ├── server-manager.ts     # single + ref counting + idle timeout
│   │   │   ├── server-definitions.ts # 35+ builtin server configs
│   │   │   ├── goto-definition.ts
│   │   │   ├── find-references.ts
│   │   │   ├── symbols.ts
│   │   │   ├── diagnostics.ts
│   │   │   └── rename.ts
│   │   ├── ast-grep/             # AST pattern search/replace
│   │   │   ├── tools.ts
│   │   │   ├── cli.ts            # sg binary invocation (auto-download)
│   │   │   └── types.ts
│   │   ├── delegate-task/        # category-based 任务委派
│   │   │   ├── tools.ts          # tool schema + handler
│   │   │   ├── category-resolver.ts
│   │   │   ├── model-selection.ts
│   │   │   ├── prompt-builder.ts
│   │   │   ├── sync-task.ts
│   │   │   ├── background-task.ts
│   │   │   └── types.ts
│   │   ├── background-task/      # 后台任务管理
│   │   │   ├── background-output.ts
│   │   │   ├── background-cancel.ts
│   │   │   └── types.ts
│   │   ├── hashline-edit/        # 哈希锚定编辑
│   │   │   ├── tools.ts
│   │   │   ├── hash-computation.ts   # xxHash32 → 2-char code
│   │   │   ├── validation.ts
│   │   │   ├── edit-operations.ts
│   │   │   └── constants.ts
│   │   ├── skill/                # skill 加载工具
│   │   └── skill-mcp/            # skill-embedded MCP 调用
│   │
│   ├── hooks/                    # 生命周期 hooks
│   │   ├── coordination.ts       # HookCoordinator (互斥状态)
│   │   ├── prompt-builder/       # Prompt 注入
│   │   ├── tool-policy/          # 工具调用限制
│   │   ├── ralph-loop/           # 自驱动循环
│   │   │   ├── hook.ts
│   │   │   ├── detector.ts       # promise 检测 (transcript + API)
│   │   │   ├── continuation.ts   # 续跑 prompt 注入
│   │   │   ├── state.ts          # RalphLoopState 状态机
│   │   │   ├── storage.ts        # 文件持久化
│   │   │   └── ultrawork.ts      # Oracle 验证流程
│   │   ├── todo-enforcer/        # idle 检测 + 续跑
│   │   │   ├── hook.ts
│   │   │   ├── detector.ts       # idle + incomplete todo 检测
│   │   │   ├── countdown.ts      # 2s 倒计时
│   │   │   ├── stagnation.ts     # 停滞检测 (3 次无进展)
│   │   │   └── prompt.ts         # 续跑 prompt 模板
│   │   ├── session-recovery/     # API 错误自动恢复
│   │   │   ├── hook.ts
│   │   │   ├── error-classifier.ts   # 5 种错误模式
│   │   │   ├── tool-result-missing.ts
│   │   │   ├── unavailable-tool.ts
│   │   │   ├── thinking-block.ts
│   │   │   └── resume.ts
│   │   ├── model-fallback/       # Agent-aware 模型切换
│   │   │   ├── hook.ts
│   │   │   ├── chain-traversal.ts
│   │   │   └── state.ts
│   │   ├── runtime-fallback/     # Error-triggered auto-retry
│   │   │   ├── hook.ts
│   │   │   ├── error-classifier.ts
│   │   │   ├── fallback-state.ts
│   │   │   ├── auto-retry.ts
│   │   │   └── constants.ts
│   │   ├── preemptive-compact/   # 主动上下文压缩
│   │   │   ├── hook.ts
│   │   │   ├── trigger.ts        # 78% 阈值检测
│   │   │   └── token-cache.ts
│   │   ├── comment-checker/      # AI slop 检测
│   │   │   ├── hook.ts
│   │   │   ├── cli.ts            # 外部 binary 调用
│   │   │   └── pending-calls.ts
│   │   ├── keyword-detector/     # 模式切换触发
│   │   │   ├── hook.ts
│   │   │   ├── detector.ts       # 多语言关键词匹配
│   │   │   └── prompts.ts        # ultrawork/search/analyze prompts
│   │   └── rules-injector/       # AGENTS.md 层级注入
│   │
│   ├── features/                 # 功能模块
│   │   ├── background-agent/
│   │   ├── skill-mcp-manager/
│   │   ├── builtin-commands/     # 9 个 slash 命令
│   │   ├── builtin-skills/       # 3 个内置 skill
│   │   └── context-injector/
│   │
│   ├── mcp/                      # 内置 MCP
│   │   ├── websearch.ts          # Exa (default) / Tavily
│   │   ├── context7.ts
│   │   └── grep-app.ts
│   │
│   ├── commands/                 # Slash 命令
│   │   ├── registry.ts
│   │   ├── ralph-loop.ts
│   │   ├── refactor.ts
│   │   ├── start-work.ts
│   │   ├── handoff.ts
│   │   ├── init-deep.ts
│   │   ├── stop-continuation.ts
│   │   └── remove-ai-slops.ts
│   │
│   └── shared/                   # 共享工具
│       ├── logger.ts             # 结构化日志
│       ├── error-boundary.ts     # withErrorBoundary 包装器
│       ├── metrics.ts            # 指标收集
│       └── degradation.ts        # DegradationManager (L0-L4)
│
├── skills/                       # 内置 skills (SKILL.md 格式)
│   ├── git-master/
│   │   └── SKILL.md
│   ├── review-work/
│   │   └── SKILL.md
│   └── ai-slop-remover/
│       └── SKILL.md
│
└── tests/
    ├── agents/
    ├── categories/
    ├── background/
    ├── tools/
    ├── hooks/
    └── integration/
```

### 3.4 Hook 集成映射（22+ handler 挂载到 openclaw 28 hook 点）

| openclaw Hook | 执行模式 | oh-my-claw Handler | Priority | 功能 |
|--------------|---------|-------------------|----------|------|
| `before_model_resolve` | modifying | Model Fallback | 100 | 替换为 fallback model |
| `before_prompt_build` | modifying | Dynamic Prompt Builder | 100 | 注入角色化 prompt |
| `before_prompt_build` | modifying | Rules Injector | 50 | 注入 AGENTS.md |
| `before_agent_start` | modifying | Agent Role System | 100 | 注入 agent-specific 配置 |
| `message_received` | void | Keyword Detector | 100 | 扫描用户消息 |
| `before_tool_call` | modifying | Hashline Validation | 100 | 验证 LINE#ID hash + tool policy |
| `before_tool_call` | modifying | Comment Checker (register) | 50 | 注册 pending write/edit |
| `after_tool_call` | void | Comment Checker (detect) | 100 | 运行 AI slop 检测 |
| `after_tool_call` | void | Preemptive Compaction | 50 | 78% 阈值检查 |
| `agent_end` | void | Ralph Loop | 100 | 检测完成 / 注入续跑 |
| `agent_end` | void | Todo Enforcer | 50 | idle 检测 → 续跑 |
| `llm_output` | void | Session Recovery | 100 | 错误检测 |
| `llm_output` | void | Runtime Fallback | 50 | 错误触发 fallback |
| `before_compaction` | void | Preemptive Compaction | 100 | 标记 compaction 进行中 |
| `after_compaction` | void | Todo Enforcer guard | 100 | compaction guard (60s) |
| `before_reset` | void | Ralph Loop cleanup | 100 | 清理状态 |
| `subagent_spawning` | modifying | Category Router | 100 | category → model 解析 |
| `subagent_spawning` | modifying | Background Manager | 50 | 并发控制 + depth check |
| `subagent_spawned` | void | Background Manager | 100 | 注册 task |
| `subagent_ended` | void | Background Notify | 100 | 结果收集 + 父 session 通知 |
| `subagent_delivery_target` | modifying | Background Manager | 100 | 路由到正确父 session |
| `gateway_start` | void | Service init | 100 | Plugin 生命周期 |
| `gateway_stop` | void | Service cleanup | 100 | Plugin 清理 |

---

## 4. 核心模块详细设计

### 4.1 专家 Agent 角色体系

#### 4.1.1 Agent 类型定义

```typescript
// agents/types.ts
interface AgentDefinition {
  id: string;
  role: "orchestrator" | "advisor" | "deep-worker" | "planner" | "grep"
      | "reference" | "plan-consultant" | "plan-reviewer" | "conductor"
      | "executor" | "vision";
  description: string;
  model: string;                        // ds-v4-pro 统一
  temperature?: number;
  maxTokens: number;
  thinking: { type: "enabled" | "disabled"; budgetTokens?: number };
  toolPolicy: "full" | "read-only" | "search-only";
  promptTemplate: string | ((ctx: PromptContext) => string);
  metadata: AgentPromptMetadata;
  color?: string;                       // TUI 显示颜色
}

interface AgentPromptMetadata {
  cost: "FREE" | "CHEAP" | "EXPENSIVE";
  category: "orchestration" | "specialist" | "exploration" | "planning" | "review";
  triggers: Array<{ domain: string; description: string }>;
  useWhen: string[];
  avoidWhen: string[];
  keyTrigger?: string;  // 出现在 Sisyphus Key Triggers 区域
}

interface FallbackEntry {
  providers: string[];
  model: string;
  variant?: string;
  thinking?: { type: "enabled" | "disabled"; budgetTokens?: number };
}
```

#### 4.1.2 完整 Agent 清单（ds-v4-pro 适配）

| Agent | Role | Temperature | maxTokens | Thinking | Tool Policy | Cost |
|-------|------|-------------|-----------|----------|-------------|------|
| **sisyphus** | orchestrator | 0.3 | 64000 | enabled (32K) | full | EXPENSIVE |
| **oracle** | advisor | 0.3 | 32000 | enabled (16K) | read-only | EXPENSIVE |
| **hephaestus** | deep-worker | 0.2 | 32000 | enabled (16K) | full (no task) | EXPENSIVE |
| **prometheus** | planner | 0.3 | 64000 | enabled (16K) | read-only + .md write | EXPENSIVE |
| **explore** | grep | 0.1 | 16000 | disabled | search-only + LSP | CHEAP |
| **librarian** | reference | 0.1 | 16000 | disabled | search-only | CHEAP |
| **metis** | plan-consultant | 0.3 | 32000 | enabled (16K) | read-only | EXPENSIVE |
| **momus** | plan-reviewer | 0.3 | 32000 | enabled (32K) | read-only | EXPENSIVE |
| **atlas** | conductor | 0.3 | 64000 | enabled (16K) | full (no task) | EXPENSIVE |
| **sisyphus-junior** | executor | category-dependent | 64000 | category-dependent | full (no task) | — |
| **multimodal-looker** | vision | 0.3 | 16000 | disabled | read only | EXPENSIVE |

**Fallback chain（所有 agent 共用）**: `ds-v4-pro → ds-v3 → ds-r1 → openclaw-native`

#### 4.1.3 Tool Policy 实现

```typescript
const TOOL_POLICIES = {
  "full": { deny: [] },
  "read-only": { deny: ["write", "edit", "apply_patch", "task", "call_omo_agent"] },
  "search-only": {
    deny: ["write", "edit", "apply_patch", "task", "call_omo_agent"],
    allow: ["lsp_symbols", "lsp_goto_definition", "lsp_find_references",
            "lsp_diagnostics", "ast_grep_search", "grep", "glob"]
  },
};

// 通过 before_tool_call hook 拦截
function toolPolicyHandler(ctx, call) {
  const policy = TOOL_POLICIES[ctx.agent.toolPolicy];
  if (policy.deny.includes(call.name) && !policy.allow?.includes(call.name)) {
    return { blocked: true, reason: `Tool "${call.name}" not allowed for ${ctx.agent.id}` };
  }
}
```

#### 4.1.4 Dynamic Prompt Builder（ds-v4-pro 简化版）

因为只有单一模型（DeepSeek V4 Pro），不需要 OmO 的 4 套模型变体 prompt。prompt 组装逻辑统一：

```typescript
interface PromptContext {
  agentId: string;
  agents: AvailableAgent[];
  tools: AvailableTool[];
  skills: AvailableSkill[];
  categories: AvailableCategory[];
}

function buildAgentPrompt(ctx: PromptContext): string {
  const agentDef = getAgentById(ctx.agentId);

  const sections = [
    // 1. Agent 身份
    buildIdentitySection(agentDef),

    // 2. 角色行为指令
    buildRoleSection(agentDef),

    // 3. 行为指令（依 agent 角色不同）
    ...buildBehaviorInstructions(agentDef, ctx),

    // 4. Oracle 使用指南（仅 Sisyphus）
    ...(agentDef.role === "orchestrator" ? [buildOracleSection(ctx.agents)] : []),

    // 5. 任务管理（仅 Sisyphus）
    ...(agentDef.role === "orchestrator" ? [buildTaskManagementSection()] : []),

    // 6. 风格语调
    buildToneAndStyleSection(),

    // 7. 约束（Hard Blocks + Anti-Patterns）
    buildConstraintsSection(),
  ];

  return sections.join("\n");
}

// Sisyphus 专属 behavior instructions（5 阶段系统）
function buildBehaviorInstructions(agentDef, ctx) {
  if (agentDef.role !== "orchestrator") return [];

  return [
    buildIntentGateSection(),              // Phase 0: 6 种意图分类
    buildKeyTriggersSection(ctx.agents),   // 从 agent metadata 动态提取
    buildCodebaseAssessmentSection(),      // Phase 1
    buildExplorationSection([              // Phase 2A
      buildToolSelectionTable(ctx.tools),  // 动态: cost-sorted
      buildExploreSection(ctx.agents),
      buildLibrarianSection(ctx.agents),
      buildAntiDuplicationSection(),
    ]),
    buildImplementationSection([           // Phase 2B
      buildCategorySkillsDelegationGuide(ctx.categories, ctx.skills),
      buildDelegationTable(ctx.agents),    // 从 triggers 动态生成
    ]),
    buildFailureRecoverySection(),         // Phase 2C
    buildCompletionSection(),              // Phase 3
  ];
}
```

#### 4.1.5 Sisyphus 关键设计 — 5 阶段系统

```
Phase 0 - Intent Gate (每条消息执行):
  分析用户真实意图 → 分类为: research | implementation | investigation | evaluation | fix | open-ended
  → 决定路由: explore 回答 | 委派执行 | 先 clarify | 先 plan

Phase 1 - Codebase Assessment (open-ended 任务):
  检查 linter/formatter/type config → 采样相似文件 → 分类:
    disciplined (严格遵循) | transitional (询问偏好) | legacy/chaotic (建议模式) | greenfield (现代实践)

Phase 2A - Exploration (所有任务):
  背景 agent 并行搜索 → 永不自身手动 grep
  停止条件: 足够上下文 | 相同信息重复 | 2 轮无新数据 | 直接答案

Phase 2B - Implementation:
  预实施: 加载 skills → 创建 todo list → 标记 in_progress
  委派: visual → visual-engineering | 复杂逻辑 → ultrabrain | 自研 → deep
  验证: lsp_diagnostics + build + test
  反模式: 永不 as any / @ts-ignore / 空 catch / 删除测试

Phase 3 - Completion:
  todo 全部 done + diagnostics 清洁 + build 通过 + test 通过
  失败 → 修复（最小改动，不重构）
  3 次失败 → stop → document → consult Oracle
```

#### 4.1.6 Prometheus 规划者详细设计

最复杂的 agent，由 6 个子模块组成：

```
PROMETHEUS_SYSTEM_PROMPT =
  IDENTITY_CONSTRAINTS      // "YOU ARE A PLANNER. NOT AN IMPLEMENTER."
  + INTERVIEW_MODE           // 7 种意图类型 × 研究策略
  + PLAN_GENERATION          // Metis 咨询 + gap 分类 + 增量写入 .md
  + HIGH_ACCURACY_MODE       // Momus 审查循环直到 OKAY
  + PLAN_TEMPLATE            // .oh-my-claw/plans/*.md 格式
  + BEHAVIORAL_SUMMARY
```

**Interview Mode — 7 种意图类型 × 策略：**

| 意图类型 | 研究策略 | 访谈焦点 |
|---------|---------|---------|
| Trivial/Simple | 快速确认 | 快速 Tiki-Taka |
| Refactoring | 安全优先 | 边界条件、测试覆盖 |
| Build from Scratch | 先 explore 后问 | 发现模式 |
| Mid-sized Task | 边界聚焦 | 范围界定、显式排除 |
| Collaborative | 对话聚焦 | 增量清晰 |
| Architecture | 战略聚焦 | **强制 Oracle 咨询** |
| Research | 调查聚焦 | 并行探测 + 退出标准 |

**High Accuracy Mode — Momus 审查循环：**

```
while (true) {
  result = task(subagent_type="momus",
    prompt=".oh-my-claw/plans/{name}.md")
  if (result.verdict === "OKAY") break;
  // 修复所有问题，重提交。无最大重试限制。
}
// OKAY 标准:
//   ≥ 80% 任务有参考来源
//   ≥ 90% 有具体验收标准
//   零业务逻辑假设
//   零关键红旗
```

### 4.2 Category 路由系统

#### 4.2.1 内置分类定义

ds-v4-pro 统一所有分类使用同一模型，仅参数不同：

```typescript
// categories/builtin.ts
const BUILTIN_CATEGORIES: Record<string, CategoryDefinition> = {
  "unspecified-low":  { model: "ds-v4-pro", temperature: 0.3, maxTokens: 32000,
                        description: "General low-complexity tasks" },
  "unspecified-high": { model: "ds-v4-pro", temperature: 0.3, maxTokens: 64000,
                        description: "General high-complexity tasks" },
  "visual-engineering": { model: "ds-v4-pro", temperature: 0.3, maxTokens: 32000,
                          description: "Frontend, UI/UX, design, styling, animation" },
  "ultrabrain": { model: "ds-v4-pro", temperature: 0.2, maxTokens: 64000,
                  thinking: { type: "enabled", budgetTokens: 32000 },
                  description: "Hard logic, architecture decisions, complex algorithms" },
  "deep": { model: "ds-v4-pro", temperature: 0.2, maxTokens: 32000,
            thinking: { type: "enabled", budgetTokens: 16000 },
            description: "Goal-oriented autonomous problem-solving" },
  "artistry": { model: "ds-v4-pro", temperature: 0.8, maxTokens: 32000,
                description: "Highly creative/artistic tasks, novel ideas" },
  "quick": { model: "ds-v4-pro", temperature: 0.1, maxTokens: 16000,
             description: "Trivial tasks - single file changes, typo fixes" },
  "writing": { model: "ds-v4-pro", temperature: 0.5, maxTokens: 32000,
               description: "Documentation, prose, technical writing" },
};
```

#### 4.2.2 Category → Model Resolution Pipeline

```typescript
// categories/router.ts
function resolveCategoryExecution(
  category: string,
  config: PluginConfig,
): ResolvedCategory {
  // 优先级链:
  // 1. 用户 config 覆盖: config.categories[category].model
  // 2. Category 默认: BUILTIN_CATEGORIES[category]
  // 3. 用户 fallback_models: config.categories[category].fallback_models
  // 4. Agent 的 fallback chain
  // 5. 系统默认: ds-v4-pro

  // ds-v4-pro 简化: 所有 category 都由 ds-v4-pro 执行
  // 仅在参数（temperature, maxTokens, thinking）上区分
}
```

#### 4.2.3 delegate-task 工具

```typescript
// tools/delegate-task/tools.ts
const DELEGATE_TASK_SCHEMA = {
  name: "task",
  description: "Spawn agent task with category-based or direct agent selection.",
  parameters: {
    load_skills:      { type: "array", items: { type: "string" }, required: true },
    prompt:           { type: "string", required: true },
    run_in_background:{ type: "boolean", required: true },
    category:         { type: "string" },   // REQUIRED if no subagent_type
    subagent_type:    { type: "string" },   // REQUIRED if no category
    description:      { type: "string" },   // Short 3-5 word description
    task_id:          { type: "string" },   // Resume existing task
    command:          { type: "string" },   // Triggering slash command
  }
};
```

**执行流程：**

```
用户/Sisyphus 调用 task(category="deep", load_skills=["tdd-workflow"], prompt="...")
  │
  ├─ 1. resolveCategoryExecution("deep")
  │    → { model: "ds-v4-pro", temperature: 0.2, thinking: enabled... }
  ├─ 2. buildSystemContent(skills, categoryPromptAppend)
  │    → 组装 subagent prompt（含 skill 注入）
  ├─ 3. depth guard → 检查 parent chain ≤ 3 层
  │
  ├─ [sync mode] ─────────────────────────────────────────
  │   ├─ 创建 openclaw session (via subagent spawn API)
  │   ├─ 发送 prompt (with resolved model/thinking/tools)
  │   ├─ 轮询直到 session.idle
  │   ├─ 获取结果 → 返回给调用者
  │   └─ 失败 → tryFallbackRetry()
  │
  └─ [background mode] ────────────────────────────────────
      ├─ backgroundManager.launch(config) → 返回 task_id
      ├─ 后台执行（concurrency control + circuit breaker）
      └─ 调用者通过 background_output(task_id) 获取结果
```

### 4.3 Background Agent 并行执行

#### 4.3.1 设计原则：薄增强层

BackgroundManager 是对 openclaw subagent API 的**薄增强层**，不是平行系统：

```typescript
// background/manager.ts
class BackgroundManager {
  // ❌ 不维护独立的 task 状态（避免双重状态漂移）
  // ✅ 仅维护增强层元数据
  private enhancements = new Map<string, TaskEnhancement>();
  // TaskEnhancement = { concurrencyKey, circuitBreaker, fallbackChain, parentSessionId }

  private concurrency: ConcurrencyManager;
  private loopDetector: LoopDetector;

  // 核心：包装 openclaw subagent spawn API
  async launch(input: LaunchInput): Promise<string> {
    // 1. 并发控制
    await this.concurrency.acquire(input.concurrencyKey);
    // 2. 深度检查
    this.checkDepth(input.parentSessionId);
    // 3. 调用 openclaw native
    const { childSessionKey } = await api.runtime.spawnSubagent(params);
    // 4. 注册增强元数据
    this.enhancements.set(childSessionKey, { ... });
    return childSessionKey;
  }

  // 状态查询：委托给 openclaw session API
  async getTaskStatus(taskId: string): Promise<TaskStatus> {
    const session = await api.runtime.getSession(taskId);
    return mapSessionToTaskStatus(session);
  }
}
```

#### 4.3.2 ConcurrencyManager

```typescript
class ConcurrencyManager {
  // 按 provider key 分组，Promise-based queue
  // 默认并发: 5（0 = unlimited）
  // settled-flag 防 double-resolution

  private limits = new Map<string, number>();
  private running = new Map<string, number>();
  private queues = new Map<string, Array<{ resolve: () => void }>>();

  async acquire(key: string): Promise<void> {
    const limit = this.limits.get(key) ?? 5;
    const current = this.running.get(key) ?? 0;
    if (current < limit) {
      this.running.set(key, current + 1);
      return;
    }
    // 入队等待
    return new Promise(resolve => {
      this.getQueue(key).push({ resolve });
    });
  }

  release(key: string): void {
    this.running.set(key, (this.running.get(key) ?? 1) - 1);
    const next = this.getQueue(key).shift();
    if (next) {
      this.running.set(key, (this.running.get(key) ?? 0) + 1);
      next.resolve();
    }
  }
}
```

#### 4.3.3 Circuit Breaker (Loop Detector)

```typescript
class LoopDetector {
  // 跟踪每个 session 的 tool call 窗口
  // signature = "toolName::JSON.stringify(sortedInput)"
  // 连续相同 signature ≥ threshold (20) → 触发熔断
  // 绝对上限: maxToolCalls (4000) → 触发熔断
  // 熔断动作: cancelTask(source="circuit-breaker")

  private windows = new Map<string, WindowTracker>();

  detectRepetitiveToolUse(sessionId: string, toolName: string, input: unknown): boolean {
    const sig = `${toolName}::${JSON.stringify(input, Object.keys(input).sort())}`;
    const tracker = this.getOrCreate(sessionId);

    tracker.totalCalls++;
    if (tracker.totalCalls >= 4000) return true;  // 绝对上限

    if (tracker.lastSignature === sig) {
      tracker.consecutiveSame++;
    } else {
      tracker.consecutiveSame = 1;
      tracker.lastSignature = sig;
    }
    return tracker.consecutiveSame >= 20;  // 连续 20 次
  }
}
```

#### 4.3.4 父 Session 通知系统

```
单个完成:
  <system-reminder>
  [BACKGROUND TASK COMPLETED]
  **ID:** `bg_abc123`
  **Description:** Find auth implementations
  **Duration:** 1m 20s

  **3 tasks still in progress.**
  Use `background_output(task_id="bg_abc123")` to retrieve this result.
  </system-reminder>

全部完成:
  <system-reminder>
  [ALL BACKGROUND TASKS COMPLETE]
  bg_abc123: Find auth implementations ✅ (80s)
  bg_def456: Find error patterns ✅ (45s)
  bg_ghi789: Find test patterns ✅ (32s)
  </system-reminder>
```

#### 4.3.5 background_output / background_cancel 工具

```typescript
// background_output schema
{
  task_id: string,              // REQUIRED
  block?: boolean,              // 等待完成 (default: false)
  timeout?: number,             // 最大等待 ms (default: 60000, max: 600000)
  full_session?: boolean,       // 返回完整 session messages
  include_thinking?: boolean,
  include_tool_results?: boolean,
  message_limit?: number,       // 最多 100 条
  since_message_id?: string,    // 增量获取
  thinking_max_chars?: number,  // 推理截断 (default: 2000)
}

// background_cancel schema
{
  taskId?: string,   // 取消指定 task
  all?: boolean,     // 取消所有（逐个 kill）
}
```

### 4.4 Ralph Loop — 自驱动完成循环

#### 4.4.1 状态机

```typescript
interface RalphLoopState {
  active: boolean;
  iteration: number;
  max_iterations: number;       // default: 100, ultrawork: 500
  completion_promise: string;   // default: "DONE"
  verification_pending: boolean; // ultrawork only
  strategy: "reset" | "continue";
  ultrawork: boolean;
}
// 持久化: .oh-my-claw/ralph-loop.local.json
```

#### 4.4.2 完成检测（双路径）

1. **Transcript 扫描**: 读取 JSONL transcript → 逆序解析 assistant parts → 正则 `<promise>\s*DONE\s*</promise>`
2. **Session Messages API**: `api.runtime.getSessionMessages(sessionId)` → 逆序扫描 assistant parts（备用）

#### 4.4.3 迭代流程

```
session.idle 事件
  │
  ├─ Guards: loop active? session 匹配? recovery 中? in-flight?
  ├─ 检测完成 (transcript → API fallback)
  │
  ├─ [已完成]
  │   ├─ [standard] → 清理状态, 显示完成通知
  │   └─ [ultrawork] → 转入验证:
  │       ├─ verification_pending = true
  │       ├─ completion_promise = "VERIFIED"
  │       └─ 注入验证 prompt: "Call Oracle to verify..."
  │
  ├─ [验证中 (ultrawork)]
  │   ├─ 扫描 Oracle tool_result 中的 <promise>VERIFIED</promise>
  │   ├─ [已验证] → 清理, 成功
  │   └─ [未验证] → 注入 "Oracle did not verify. Fix and retry."
  │
  ├─ [达到 max_iterations] → 停止, 警告通知
  │
  └─ [未完成] → iteration++ → 注入:
      "Previous attempt did not output completion promise.
       Continue working... When FULLY complete, output:
       <promise>DONE</promise>"
```

### 4.5 Todo Continuation Enforcer

```
session.idle 事件
  │
  ├─ Guards: recovery? cancelled? token limit? abort (3s)?
  │          bg tasks running? in-flight injection?
  │          skip agents (prometheus/compaction/plan)?
  │          Ralph active? → SKIP (互斥)
  │
  ├─ 获取 session messages → 检查 last assistant
  ├─ 获取 todos → 计算 incomplete count
  │
  ├─ [incomplete > 0]
  │   ├─ 停滞检测: 连续 3 次 incomplete 不减少 → 停止
  │   ├─ 连续失败: 5 次 → 停止 (指数退避: 5s × 2^min(failures,5))
  │   ├─ Compaction guard: compaction 后 60s 内跳过
  │   ├─ 2s 倒计时 (每秒通知)
  │   └─ 注入续跑 prompt:
  │       "[SYSTEM_DIRECTIVE: TODO_CONTINUATION]
  │        Incomplete tasks remain. Continue working.
  │        [Status: X/Y completed, Z remaining]
  │        Remaining tasks:
  │        - [pending] task content"
  │
  └─ [incomplete == 0] → 无操作
```

### 4.6 Model Fallback Chain

**双层架构：**

**Layer 1 — Agent-Aware (pre-request):**
- Hook: `before_model_resolve` (priority: 100)
- 触发: 其他 hook 设置 pending fallback flag
- 逻辑: 从 agent fallbackChain 中选择下一个可达模型
- No-op: canonicalize(provider+model) 相同则跳过

**Layer 2 — Runtime (error-triggered):**
- Hook: `llm_output` + `session_end` (priority: 50)
- 触发: HTTP 错误 (429/500/502/503/504) + 文本 pattern

```typescript
const RETRYABLE_PATTERNS = [
  "rate_limit", "too_many_requests", "quota_exceeded",
  "exhausted_capacity", "service_unavailable", "overloaded",
  "temporarily_unavailable", "try_again", "429", "503", "529"
];

// FallbackState
interface FallbackState {
  originalModel: string;
  currentModel: string;
  fallbackIndex: number;
  failedModels: Set<string>;
  attemptCount: number;
  cooldownUntil: Map<string, number>; // 60s per failed model
}
// Cooldown: 60s per failed model, max 3 attempts, 30s timeout
```

**ds-v4-pro Fallback Chain**: `ds-v4-pro → ds-v3 → ds-r1 → openclaw-native`

### 4.7 Session Recovery

**5 种错误模式 + 恢复策略：**

| 错误类型 | 检测模式 | 恢复策略 |
|---------|---------|---------|
| `tool_result_missing` | message 含 "tool_use" + 缺少 "tool_result" | 提取所有 tool_use parts → 注入 synthetic error result |
| `unavailable_tool` | "dummy_tool" / "unavailable tool" / "no such tool" | 提取工具名 → 注入 "Tool not available. Continue." |
| `thinking_block_order` | "thinking" + ("first block" \| "must start with") | 重排 thinking blocks → auto-resume |
| `thinking_disabled_violation` | "thinking is disabled" + "cannot contain" | 剥离 thinking/redacted_thinking parts → auto-resume |
| `assistant_prefill_unsupported` | "assistant message prefill" | 无恢复 (return false) |

恢复流程: `检测 → 去重(processingErrors Set, keyed by messageId) → abort → 获取 messages → 运行 handler → auto-resume`

### 4.8 LSP 工具集

**3 层 Client 架构：**

```
LSPClientTransport (base)
  ├─ 启动 LSP server (stdin/stdout)
  ├─ 创建 vscode-jsonrpc MessageConnection
  ├─ 处理 publishDiagnostics 通知
  └─ 15s 请求超时, SIGKILL 优雅关闭

LSPClientConnection (extends Transport)
  ├─ initialize() 握手 (声明完整 capabilities)
  └─ initialized + didChangeConfiguration

LSPClient (extends Connection)
  ├─ openFile() / definition() / references()
  ├─ documentSymbols() / workspaceSymbols()
  ├─ diagnostics() / prepareRename() / rename()
  └─ 行号转换: 1-based → 0-based LSP protocol
```

**LSPServerManager 单例：**
- Key: `${workspaceRoot}::${serverId}`
- 引用计数（多 agent 共用）
- 5min idle timeout → 自动停止
- 60s init timeout
- 35+ 内置 server: TypeScript, Go, Python, Rust, Java, C/C++, Vue, ESLint, Biome...

**6 个工具 Schema：**

| 工具 | 参数 | 说明 |
|------|------|------|
| `lsp_goto_definition` | filePath, line(1-based), character(0-based) | 跳转到定义 |
| `lsp_find_references` | filePath, line, character, includeDeclaration? | 查找所有引用 |
| `lsp_symbols` | filePath, scope, query?, limit? | 文档/工作区符号 |
| `lsp_diagnostics` | filePath, severity?("error"\|"warning"\|"all") | 诊断（支持目录） |
| `lsp_prepare_rename` | filePath, line, character | 重命名可行性检查 |
| `lsp_rename` | filePath, line, character, newName | 跨文件重命名 |

### 4.9 AST-Grep 工具

```typescript
// ast_grep_search
{ pattern: string, lang: CliLanguage, paths?: string[], globs?: string[], context?: number }

// ast_grep_replace
{ pattern: string, rewrite: string, lang: CliLanguage, paths?: string[], globs?: string[],
  dryRun?: boolean } // default: true

// 底层: sg CLI (auto-download binary)
// replace 需两遍: JSON 收集 + 写入 (--json 和 --update-all 互斥)
// 空结果提示: "Remove trailing colon" (Python), "Function patterns need params and body" (JS/TS)
```

### 4.10 Hashline Edit

**LINE#ID 哈希算法：**

```typescript
// Dictionary: 16-char nibble "ZPMQVRWSNKTXJBYH" → 256 个 2-char code
// computeLineHash(lineNumber, content):
//   1. normalize: strip \r, trimEnd()
//   2. seed: 0 (has significant chars), else lineNumber
//   3. hash: xxHash32(stripped, seed) % 256
//   4. lookup: DICT[index] → 2-char code
// 输出: "42#VR|  const x = 1"
// 引用: "42#VR"
```

**编辑 Pipeline：**

```
normalizeEdits → dedupeEdits → sort (bottom-up)
  → collectLineRefs → validateLineRefs (hash 对比当前文件)
  → detectOverlappingRanges → apply
  → canonicalizeFileText → write → runFormattersForFile (LSP)
  → publish diff metadata
```

### 4.11 Comment Checker

```
before_tool_call (write/edit/multiedit/apply_patch)
  → register PendingCall { callID, filePath, content, oldString, newString }

after_tool_call
  → 取出 PendingCall → 跳过失败的 tool output
  → 调用外部 binary: comment-checker check [--prompt custom]
  → stdin: JSON { session_id, tool_name, file_path, content, ... }
  → exit 0: 无问题 | exit 2: 检测到 AI slop
  → 警告追加到 tool output → agent 自动修复
  → 并发锁: withCommentCheckerLock()
  → timeout: 30s (SIGTERM → 1s → SIGKILL)
```

### 4.12 Keyword Detector

| 模式 | 触发正则 | 注入内容 |
|------|---------|---------|
| **ultrawork** | `/\b(ultrawork\|ulw)\b/i` | 完整 ultrawork prompt |
| **search** | 多语言: search/find/locate/検索/搜索/... | "MAXIMIZE SEARCH EFFORT. Launch multiple background agents IN PARALLEL..." |
| **analyze** | 多语言: analyze/investigate/debug/分析/調査/... | "ANALYSIS MODE. Gather context before diving deep..." |

注入方式: prepend 到首个 text part → `{messages}\n\n---\n\n{originalText}`

### 4.13 openclaw 原生能力深度集成

oh-my-claw 的核心优势之一是**深度复用** openclaw 的独有能力（OmO 完全不具备的能力）。

#### 4.13.1 Memory 系统集成（Agent 学习 + 历史成功率 + 用户偏好）

openclaw 的 memory 系统（embedding + 时间衰减 + dreaming + QMD）是目前最先进的 agent memory 实现之一。oh-my-claw 将在以下三个场景深度利用：

**a) Agent 跨 Session 学习**

```typescript
// 通过 api.registerMemoryPromptSection() 注入 memory 到 agent prompt
api.registerMemoryPromptSection({
  id: "omc-agent-memory",
  priority: 50,
  async build(ctx) {
    const memories = await ctx.memory.query({
      query: ctx.currentTask,
      limit: 5,
      minRelevance: 0.7,
      tags: ["omc-decision", "omc-pattern"],
    });
    if (memories.length === 0) return null;
    return {
      role: "system",
      content: `[Historical Context - from previous sessions]\n${memories.map(m => `- ${m.content}`).join("\n")}`,
    };
  },
});
```

**b) Category Router 历史成功率**

```typescript
// 每次 delegate-task 完成后，记录结果到 memory
api.registerMemoryCorpusSupplement({
  id: "omc-category-outcomes",
  async onTaskComplete(ctx, result) {
    await ctx.memory.store({
      content: `Category=${result.category} Task=${result.task} Status=${result.status} Duration=${result.durationMs}ms`,
      tags: ["omc-category-outcome"],
      metadata: { category: result.category, success: result.status === "completed" },
    });
  },
});

// ContextAwareRouter 查询:
const outcomes = await memory.query({ tags: ["omc-category-outcome"], limit: 50 });
const successRate = outcomes.filter(o => o.metadata.success).length / outcomes.length;
// 如果某 category 近期成功率 < 60% → 推荐切换到更保守的参数
```

**c) 用户偏好记忆**

当用户纠正 agent 行为时（如 "不要用 thinking mode"），存入 memory，后续 session 自动恢复偏好。

#### 4.13.2 Cron 调度集成

利用 openclaw 的 cron 系统，注册 3 个内置维护任务：

```typescript
const BUILTIN_CRON_JOBS = [
  {
    id: "omc-code-quality",
    schedule: "0 9 * * 1",  // 每周一 9:00
    description: "Weekly code quality scan",
    agentId: "sisyphus",
    task: "Run /review-work on the most recently changed files this week",
    skills: ["review-work"],
  },
  {
    id: "omc-dependency-check",
    schedule: "0 10 * * 3",  // 每周三 10:00
    description: "Dependency security audit",
    agentId: "sisyphus",
    task: "Check for known vulnerabilities in project dependencies and suggest updates",
  },
  {
    id: "omc-stale-branch-cleanup",
    schedule: "0 8 1 * *",  // 每月 1 号 8:00
    description: "Stale branch report",
    agentId: "explore",
    task: "List branches not updated in 30+ days with their last commit info and suggest cleanup",
    skills: ["git-master"],
  },
];
```

#### 4.13.3 ACP 协议集成

通过 openclaw 的 ACP (Agent Communication Protocol)，oh-my-claw 可以调用外部 coding harness：

```typescript
// delegate-task 扩展: 新增 harness 参数
{
  name: "task",
  parameters: {
    // ... 现有参数 ...
    harness: { type: "string" },  // "codex" | "claude-code" | "local"
  }
}

// 当 harness 指定时:
// 1. 通过 ACP 协议发送任务到外部 harness (persistent 模式保持长连接)
// 2. 外部 harness 在其自有环境中执行
// 3. 结果通过 ACP 回传
// 4. BackgroundManager 统一管理生命周期（超时/取消/fallback）
```

### 4.14 ContextAwareRouter — 动态增强路由层（P2）

静态 pipeline 不考虑运行时上下文。ContextAwareRouter 包装静态 pipeline，注入 runtime 信号：

```typescript
// categories/context-aware-router.ts
class ContextAwareRouter {
  constructor(
    private staticRouter: typeof resolveCategoryExecution,
    private memory: MemoryAPI,
    private contextEngine: ContextEngineAPI,
    private metrics: MetricsCollector,
  ) {}

  async resolve(category: string, config: PluginConfig): Promise<ResolvedCategory> {
    const baseline = this.staticRouter(category, config);

    // 1. Context window 感知
    //    如果当前 session 已用 >70% context → 考虑限制 maxTokens
    const contextUsage = await this.contextEngine.getUsageRatio();
    if (contextUsage > 0.7 && baseline.maxTokens > 32000) {
      // 降低 maxTokens 以避免 compaction 频繁触发
    }

    // 2. 历史成功率 (from memory)
    const outcomes = await this.memory.query({
      tags: ["omc-category-outcome"], filter: { category }, limit: 20,
    });
    // 如果近期 3 次失败 → 调整参数（降低 temperature、禁用 thinking 等）

    // 3. 通道约束
    //    Discord message limit (2000 char) → 控制 maxTokens 避免截断
    return adjustedResult;
  }
}
```

### 4.15 内置命令详细设计

#### 4.15.1 命令清单

| 命令 | 参数 | 说明 |
|------|------|------|
| `/ralph-loop [strategy]` | `strategy: "continue"\|"reset"` | 启动自驱动完成循环，默认 continue |
| `/ulw-loop [strategy]` | 同上 | Ultrawork 循环（含 Oracle 验证，max_iterations=500） |
| `/cancel-ralph` | — | 取消活跃 Ralph Loop，清理状态文件 |
| `/refactor [scope]` | `scope: "rename"\|"extract"\|"move"\|"inline"` | 6 阶段智能重构（LSP + AST-grep） |
| `/start-work [plan-path]` | plan 文件路径 | 从 Prometheus 计划启动工作 |
| `/stop-continuation` | — | 停止所有续跑机制 |
| `/init-deep [root-dir]` | 根目录，默认 `./` | 生成层级化 AGENTS.md |
| `/handoff [session-id]` | 可选 session | 生成 session 上下文摘要 |
| `/remove-ai-slops [branch]` | 分支名 | 清除 AI 代码异味 |
| `/omc-status` | — | 降级级别、tasks、hook 状态 |
| `/omc-metrics` | — | 最近 1h 关键指标 |
| `/omc-debug <hook>` | hook 名称 | 启用 debug 日志 |

#### 4.15.2 /refactor 命令 — 6 阶段流程

```
Phase 1: Intent Gate
  → 分类: rename / extract / move / inline / restructure / signature-change / pattern-replace

Phase 2: Codebase Analysis (5 parallel explore agents)
  → Agent 1: 目标代码结构 (LSP symbols + AST patterns)
  → Agent 2: 依赖关系图 (LSP find_references 双向追踪)
  → Agent 3: 测试覆盖 (glob test files + LSP diagnostics)
  → Agent 4: 类型系统约束 (LSP goto_definition, TypeScript checker)
  → Agent 5: 相关配置/构建文件 (glob + grep)

Phase 3: Codemap Generation
  → LSP symbols + AST-grep patterns → 生成影响范围图

Phase 4: Test Assessment
  → 现有测试覆盖率 → 需新增测试 → TDD 计划

Phase 5: Plan Generation
  → 原子步骤列表 → 每步验证标准 → 回滚策略

Phase 6: Deterministic Execution
  → 逐步执行 → 每步后 lsp_diagnostics 验证
  → 失败 → 回滚上一步 → 重试或报告
```

#### 4.15.3 /init-deep 命令 — 4 阶段流程

```
Phase 1: Discovery
  → 5 parallel explore agents 搜索项目结构
  → LSP symbols 提取模块边界
  → 评分: 目录深度 > 2 且含 ≥3 源码文件 → 高优先级

Phase 2: Score
  → 按文件数 + 最近修改时间排序
  → Top 15 目录生成 AGENTS.md
  → 相邻低分目录合并

Phase 3: Generate
  → 对每个目录: read 关键文件 → 提取职责/依赖/约定
  → 生成 AGENTS.md（遵循 openclaw AGENTS.md 格式）
  → 同步生成 CLAUDE.md symlink

Phase 4: Review
  → oracle agent 审查生成的 AGENTS.md
  → 去重检查（相邻目录内容相似度 > 80% → 合并）
  → 用户确认后写入
```

#### 4.15.4 /handoff 命令 — 4 阶段流程

```
Phase 1: Gather Context
  → session_read: 最近 20 条消息
  → todoread: 当前 todo 状态
  → git log / git diff: 最近改动

Phase 2: Extract
  → 提取关键决策（model 选择、architecture 决策）
  → 提取待办项
  → 提取未解决问题

Phase 3: Format
  → 生成 Markdown 摘要（对话摘要 + 决策记录 + 待办清单 + 下一步）

Phase 4: Instructions
  → 追加 "How to continue" 指南（agent/model/skills 建议）
```

### 4.16 内置 Skill 详细设计

#### 4.16.1 git-master — 3-Mode Git 专家

```typescript
// skills/git-master/SKILL.md 核心结构
interface GitMasterSkill {
  name: "git-master";
  description: "3-mode git expert: COMMIT (6-phase), REBASE (4-phase), HISTORY SEARCH (3-phase)";
  // 从用户请求自动检测操作模式
}
```

| 模式 | 阶段 | 关键行为 |
|------|------|---------|
| **COMMIT** | 6 阶段 | ① 并行上下文收集(7 parallel: git status/diff/log/branch/stash/config/recent) → ② 风格检测(语言占比 + commit message style) → ③ 分支上下文 → ④ 原子单元规划(min commits = ceil(files/3)) → ⑤ 策略选择(fixup/new/reset-rebuild) → ⑥ 执行 + git status 验证 |
| **REBASE** | 4 阶段 | ① 上下文分析(目标分支/commits 列表/冲突预测) → ② 执行(interactive/autosquash/onto) → ③ 验证 → ④ 报告 |
| **HISTORY SEARCH** | 3 阶段 | ① 搜索类型检测(pickaxe/regex/blame/bisect/file_log) → ② 执行 → ③ 呈现结果(按时间线/作者分组) |

#### 4.16.2 review-work — 5-Agent 并行审查

启动 5 个并行 background sub-agent，**ALL 5 必须 PASS** 才算通过：

| # | Agent Role | Loaded Skills | 审查维度 |
|---|-----------|--------------|---------|
| 1 | **Goal Verifier** (oracle) | — | 原始目标/约束 对应检查：功能是否完整？边界条件？异常处理？ |
| 2 | **QA Executor** (unspecified-high) | playwright, dev-browser | 动手测试：结构化场景头脑风暴 → 执行 → 记录 pass/fail |
| 3 | **Code Reviewer** (oracle) | — | 10 维 staff-engineer 审查：naming/conciseness/simplicity/type-safety/error-handling/patterns/test-quality/perf-security/documentation/over-engineering |
| 4 | **Security Auditor** (oracle) | — | 10 点 OWASP 清单：injection/auth/secrets/SSRF/XSS/deserialization/deps/logging/crypto/config |
| 5 | **Context Miner** (unspecified-high) | git-master | 搜索 git blame, GitHub issues/PRs, Slack threads, Notion pages → 确保变更与历史上下文一致 |

结果汇总: 5 个 agent 结果合并 → 生成统一 review report → agent 修复 → 重新 review（最多 3 轮）

#### 4.16.3 ai-slop-remover — AI 代码异味清除

```
检测模式:
  - 过度注释 (// This function does...)
  - 冗余解释 (explaining obvious logic)
  - 不必要的 try-catch (catch 后仅 rethrow 或 console.log)
  - 过度抽象 (单次使用的 wrapper/interfaces)
  - AI 语气标记 (诸如 "certainly", "of course" 出现在注释中)

执行:
  1. git diff main...HEAD → 识别所有变更文件
  2. 对每个文件: task(category="quick", load_skills=["ai-slop-remover"], prompt="...")
  3. 审查变更: oracle agent 检查是否功能退化
  4. 用户确认后 commit
```

### 4.17 内置 MCP 详细设计

| MCP | URL | 认证方式 | 说明 | 启用条件 |
|-----|-----|---------|------|---------|
| **Exa Web Search** | `https://mcp.exa.ai/mcp` | 可选 `EXA_API_KEY` 环境变量 | 语义搜索，返回清洁 Markdown 文本。工具: `web_search_exa` | `config.mcp.websearch.enabled !== false` |
| **Context7 Docs** | `https://mcp.context7.com/mcp` | 可选 `CONTEXT7_API_KEY` | 官方库文档查询。工具: `resolve-library-id` + `query-docs` | `config.mcp.context7.enabled !== false` |
| **Grep.app** | `https://mcp.grep.app` | 无需认证 | GitHub 代码搜索（100 万+ 仓库）。工具: `searchGitHub` | `config.mcp.grep_app.enabled !== false` |

**可选替代**: Tavily Web Search → `https://mcp.tavily.com/mcp/`，需 `TAVILY_API_KEY`，通过 `config.websearch.provider = "tavily"` 切换。

**MCP 注册代码:**

```typescript
function registerBuiltinMcps(api: PluginApi, config: PluginConfig) {
  if (config.mcp?.websearch?.enabled !== false) {
    api.registerMcpServer({
      id: "omc-websearch",
      transport: { type: "http", url: "https://mcp.exa.ai/mcp" },
      metadata: { source: "oh-my-claw", type: "websearch" },
    });
  }
  // ... context7, grep-app 同理
}
```

---

## 5. Hook 优先级矩阵与冲突解决

### 5.1 优先级矩阵

数字越大越先执行：

| Hook Point | Handler | Priority | 互斥规则 |
|-----------|---------|----------|---------|
| `agent_end` | Ralph Loop | 100 | Ralph active → 抑制 Todo |
| `agent_end` | Todo Enforcer | 50 | Ralph active 时跳过 |
| `before_model_resolve` | Model Fallback | 100 | — |
| `llm_output` | Session Recovery | 100 | Recovery 中 → 抑制 Runtime Fallback |
| `llm_output` | Runtime Fallback | 50 | Recovery 中跳过 |
| `before_tool_call` | Hashline Validation | 100 | 失败 → reject, Comment Checker 不触发 |
| `before_tool_call` | Comment Checker (register) | 50 | Hashline reject 时跳过 |
| `after_tool_call` | Comment Checker (detect) | 100 | — |
| `after_tool_call` | Preemptive Compaction | 50 | Compaction 中跳过 |
| `before_prompt_build` | Dynamic Prompt Builder | 100 | — |
| `before_prompt_build` | Rules Injector | 50 | — |
| `subagent_spawning` | Category Router | 100 | — |
| `subagent_spawning` | Background Manager | 50 | — |
| `message_received` | Keyword Detector | 100 | — |

### 5.2 HookCoordinator 互斥状态机

```typescript
class HookCoordinator {
  private ralphActive = new Set<string>();      // sessionId
  private recoveryActive = new Set<string>();
  private compactionActive = new Set<string>();

  isRalphActive(sid: string): boolean;
  isRecovering(sid: string): boolean;
  isCompacting(sid: string): boolean;
}
```

### 5.3 防双重注入

```typescript
const injectionInFlight = new Set<string>(); // sessionId

function guardedInject(sessionId: string, fn: () => Promise<void>): Promise<void> {
  if (injectionInFlight.has(sessionId)) return;
  injectionInFlight.add(sessionId);
  try { await fn(); } finally { injectionInFlight.delete(sessionId); }
}
```

---

## 6. 韧性架构 (Resilience)

### 6.1 错误边界

每个 hook/tool handler 包裹 `withErrorBoundary()`，异常不导致 openclaw 崩溃：

```typescript
function withErrorBoundary<T>(handlerName: string, fn: () => T, fallback?: T): T {
  try {
    const result = fn();
    if (result instanceof Promise) {
      return result.catch(err => {
        logger.error(`[oh-my-claw] ${handlerName} failed`, err);
        metrics.increment("hook.error", { handler: handlerName });
        return fallback as T;
      });
    }
    return result;
  } catch (err) {
    logger.error(`[oh-my-claw] ${handlerName} failed`, err);
    return fallback as T;
  }
}
```

### 6.2 优雅降级 5 级

| Level | 触发条件 | 降级行为 |
|-------|---------|---------|
| **L0** | 正常 | 全功能 |
| **L1** | 单 hook 连续失败 3 次 | 禁用该 hook，其余正常 |
| **L2** | LSP/AST-grep 启动失败 | 禁用相关工具 |
| **L3** | BackgroundManager 异常 | 所有 delegate-task 强制 sync |
| **L4** | 10+ hook 错误 / 配置失败 | Plugin 整体禁用，openclaw 回退原生 |

### 6.3 Kill Switch

```
1. 配置: oh-my-claw.json → { "enabled": false }
2. 命令: /omc-disable
3. 环境变量: OMC_DISABLED=1
4. 自动: DegradationManager L4
```

---

## 7. 通道兼容性矩阵

### 7.1 通道分类

| 通道类型 | 代表 | 文件系统 | 长消息 | 交互式 | 进程 |
|---------|------|---------|--------|--------|------|
| 本地 TUI | terminal, ACP | ✅ | ✅ | ✅ | ✅ |
| 桌面 IM | Discord, Slack | ❌ | ⚠️ (2000) | ⚠️ | ❌ |
| 移动 IM | Telegram, WhatsApp | ❌ | ⚠️ (4096) | ❌ | ❌ |
| API | HTTP gateway | ❌ | ✅ | ❌ | ❌ |

### 7.2 功能兼容性

| 功能 | 本地 TUI | 桌面 IM | 移动 IM | API | 适配策略 |
|------|---------|---------|---------|-----|---------|
| Agent 角色体系 | ✅ | ✅ | ✅ | ✅ | 纯 prompt，通道无关 |
| Category 路由 | ✅ | ✅ | ✅ | ✅ | 纯逻辑，通道无关 |
| Background Agent | ✅ | ✅ | ✅ | ✅ | subagent API，通道无关 |
| Ralph Loop | ✅ | ⚠️ | ⚠️ | ✅ | 完成检测用 session messages API；通知用 channel message |
| Todo Enforcer | ✅ | ⚠️ | ⚠️ | ✅ | 倒计时通知适配通道 |
| Model Fallback | ✅ | ✅ | ✅ | ✅ | 纯 API 层 |
| Session Recovery | ✅ | ✅ | ✅ | ✅ | 纯 API 层 |
| **LSP 工具** | ✅ | ❌ | ❌ | ❌ | 需本地文件系统 + LSP server |
| **AST-Grep** | ✅ | ❌ | ❌ | ❌ | 同上 |
| **Hashline Edit** | ✅ | ❌ | ❌ | ❌ | 同上 |
| **Comment Checker** | ✅ | ❌ | ❌ | ❌ | 需外部 binary |
| Keyword Detector | ✅ | ✅ | ✅ | ✅ | 纯文本匹配 |
| /refactor 命令 | ✅ | ❌ | ❌ | ❌ | 依赖 LSP + AST-grep |

### 7.3 通道感知注册

```typescript
function register(api) {
  const isLocal = ["terminal", "acp"].includes(api.runtime.channelType);

  // 通道无关: 始终注册
  registerAgentSystem(api, config);
  registerCategoryRouter(api, config);
  registerBackgroundManager(api, config);
  // ...

  // 本地专属: 仅本地通道
  if (isLocal) {
    registerLspTools(api, config);
    registerAstGrepTools(api, config);
    registerHashlineEditTool(api, config);
    registerCommentCheckerHook(api, config);
  }

  // 通知适配
  const notifier = isLocal
    ? new ToastNotifier(api) : new ChannelMessageNotifier(api);
}
```

---

## 8. 配置系统

### 8.1 配置文件

```
项目级: .oh-my-claw.json          (JSON5, jsonc 兼容)
用户级: ~/.openclaw/oh-my-claw.json
默认值: 代码内置
合并: project > user > defaults (deep merge)
```

### 8.2 完整 Zod Schema（节选）

```typescript
const OhMyClawConfigSchema = z.object({
  // Agents 覆盖
  agents: z.record(AgentOverrideSchema).optional(),
  // AgentOverrideSchema: model, temperature, top_p, maxTokens,
  //   thinking, prompt (支持 file:// URI), prompt_append,
  //   tools (record<toolName, boolean>), fallback_models,
  //   disable, description, mode ("subagent"|"primary"|"all"),
  //   color (hex)

  // Categories 自定义
  categories: z.record(CategoryConfigSchema).optional(),
  // CategoryConfigSchema: model, fallback_models, temperature,
  //   top_p, maxTokens, thinking, tools, prompt_append, disable

  // 开关
  disabled_agents: z.array(z.string()).optional(),
  disabled_hooks: z.array(z.string()).optional(),
  disabled_tools: z.array(z.string()).optional(),
  disabled_commands: z.array(z.string()).optional(),
  disabled_skills: z.array(z.string()).optional(),
  disabled_mcps: z.array(z.string()).optional(),

  // Ralph Loop
  ralph_loop: z.object({
    enabled: z.boolean().default(false),
    default_max_iterations: z.number().min(1).max(1000).default(100),
    default_strategy: z.enum(["reset", "continue"]).default("continue"),
  }).optional(),

  // Runtime Fallback
  runtime_fallback: z.object({
    enabled: z.boolean().default(true),
    retry_on_errors: z.array(z.number()).default([429, 500, 502, 503, 504]),
    max_fallback_attempts: z.number().min(1).max(20).default(3),
    cooldown_seconds: z.number().default(60),
    timeout_seconds: z.number().default(30),
  }).optional(),

  // Background Agent
  background_task: z.object({
    defaultConcurrency: z.number().default(5),
    providerConcurrency: z.record(z.number()).optional(),
    maxDepth: z.number().default(3),
    staleTimeoutMs: z.number().default(2_700_000),
    taskTtlMs: z.number().default(1_800_000),
    maxToolCalls: z.number().default(4000),
    circuitBreaker: z.object({
      enabled: z.boolean().default(true),
      consecutiveThreshold: z.number().default(20),
    }).optional(),
  }).optional(),

  // MCP
  mcp: z.object({
    websearch: z.object({ enabled: z.boolean().default(true) }).optional(),
    context7: z.object({ enabled: z.boolean().default(true) }).optional(),
    grep_app: z.object({ enabled: z.boolean().default(true) }).optional(),
  }).optional(),

  // 实验特性
  experimental: z.object({
    preemptive_compaction: z.boolean().default(false),
    aggressive_truncation: z.boolean().default(false),
    team_mode: z.boolean().default(false),
    interactive_bash: z.boolean().default(false),
  }).optional(),
});
```

### 8.3 Plugin Manifest

```json
// openclaw.plugin.json
{
  "id": "oh-my-claw",
  "name": "Oh My Claw",
  "version": "0.1.0",
  "description": "Multi-model orchestration plugin for openclaw — powered by DeepSeek V4 Pro",
  "author": "oh-my-claw",
  "license": "MIT"
}
```

---

## 9. 实施路线图

采用**垂直切片**策略，每阶段交付端到端可验证功能。

### 9.1 阶段总览

| 阶段 | 内容 | 工期 (单人) | 累计 |
|------|------|-----------|------|
| MVP-0 | Plugin 骨架 + 配置系统 | 3-4 天 | 3-4 天 |
| MVP-1 | Agent 角色体系 + Prompt Builder | 4-5 天 | 7-9 天 |
| MVP-2 | Category 路由 + delegate-task | 4-5 天 | 11-14 天 |
| MVP-3 | Background Agent 并行 | 4-5 天 | **15-19 天 (MVP!)** |
| MVP-4 | Ralph Loop + Todo Enforcer | 3-4 天 | 18-23 天 |
| MVP-5 | Fallback + Recovery + Compaction | 3-4 天 | 21-27 天 |
| MVP-6 | LSP + AST-Grep | 5-6 天 | 26-33 天 |
| MVP-7 | Hashline + Comment Checker + Keyword | 3-4 天 | 29-37 天 |
| MVP-8 | Skills + MCPs + Commands + 收尾 | 4-5 天 | **33-42 天 (完整版)** |

### 9.2 MVP 里程碑验收（阶段 0-3 完成后）

- [ ] Sisyphus 角色化 prompt + Intent Gate 6 种意图分类正确
- [ ] Category 路由: 8 个分类自动选择 ds-v4-pro + 参数差异
- [ ] delegate-task: sync/background 模式正确执行
- [ ] 5+ explore agent 并行执行，结果通过 `<system-reminder>` 回传父 session
- [ ] background_output 获取结果, background_cancel 取消任务
- [ ] circuit breaker 在 agent 循环时触发熔断
- [ ] 深度限制阻止无限嵌套（3 层）

### 9.3 完整版验收

- [ ] Ralph Loop 自主完成多步任务（≤50 iterations）
- [ ] Model fallback: API 错误 → 自动切换（≤3 次）
- [ ] Session recovery: 恢复 5 种错误中的 ≥4 种
- [ ] LSP 工具在 TypeScript/Python/Go 正常
- [ ] AST-Grep search/replace 正常
- [ ] Hashline: 编辑拒绝陈旧行
- [ ] 所有 hook 可通过配置独立 启用/禁用
- [ ] 9 个 slash 命令正常
- [ ] 3 个内置 MCP 可用
- [ ] 5 级降级正常

---

## 10. 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| 语言 | TypeScript (ESM, strict) | 与 openclaw 一致 |
| 运行时 | Node.js 24+ | openclaw 生态 |
| 包管理 | pnpm | openclaw monorepo |
| 配置校验 | Zod | openclaw 一致 |
| LSP Client | vscode-jsonrpc | 轻量 JSON-RPC |
| AST-Grep | sg CLI (auto-download) | @ast-grep/napi 或 binary |
| Hash | xxHash32 | Hashline |
| Comment Checker | @code-yeongyu/comment-checker | 外部 binary |
| 测试 | vitest | openclaw 一致 |

---

## 11. 测试策略

### 11.1 测试金字塔

```
        ╱╲
       ╱ E2E ╲          2-3 end-to-end scenarios per phase
      ╱────────╲
     ╱ Integration╲    1 integration test per hook chain
    ╱──────────────╲
   ╱   Unit Tests    ╲  80%+ coverage per module
  ╱────────────────────╲
```

### 11.2 单元测试重点

| 模块 | 测试重点 | Mock 策略 |
|------|---------|----------|
| config/schema.ts | Zod 合法/非法/默认值/合并 | 无需 mock |
| categories/router.ts | 解析优先级、fallback | mock providers |
| background/concurrency.ts | acquire/release、队列、limit 边界 | 无需 mock |
| background/loop-detector.ts | 连续相同签名、阈值、重置 | 无需 mock |
| hooks/ralph-loop/detector.ts | promise 正则、transcript 解析 | mock session API |
| hooks/todo-enforcer/stagnation.ts | 停滞检测、退避 | 无需 mock |
| hooks/session-recovery/error-classifier.ts | 5 种错误分类 | 无需 mock |
| tools/lsp/server-definitions.ts | 扩展名映射 | 无需 mock |
| tools/hashline-edit/hash-computation.ts | xxHash32、dictionary | 无需 mock |
| agents/prompt-builder/*.ts | section 生成 | mock agent/tool/skill 列表 |

### 11.3 集成测试场景

1. Ralph Loop + Todo Enforcer 互斥
2. Model Fallback + Runtime Fallback 链
3. Session Recovery + Ralph Loop 互斥
4. Category Router + Background Manager 协作
5. Comment Checker + Hashline: reject → skip

### 11.4 E2E 测试

| Phase | 场景 | 验证点 |
|-------|------|--------|
| P0 | "implement auth" → deep → Junior → done | 意图分类, category, subagent |
| P0 | 5 explore agents 并行 | 并发, 通知批量, 结果收集 |
| P1 | Ralph: 3 步任务 → auto-resume × 2 → done | 完成检测, 续跑, 持久化 |
| P1 | API 429 → fallback → 成功 | 错误分类, fallback, cooldown |

---

## 12. 安全考量

### 12.1 进程安全

| 风险 | 缓解 |
|------|------|
| LSP server 进程失控 | ulimit/资源限制, 60s init timeout, 15s request timeout, 5min idle kill |
| AST-grep replace 任意文件 | dryRun: true 默认, workspace 限制, diff 预览 + 确认 |
| Comment Checker 供应链 | SHA256 校验, 沙箱执行, 30s timeout + SIGKILL |

### 12.2 Prompt 安全

| 风险 | 缓解 |
|------|------|
| `file://` URI 路径穿越 | 限制 workspace 和 `~/.openclaw/`，拒绝 `..` 和 symlink |
| Background agent 权限提升 | 子 agent 继承父 toolPolicy，Junior 永远无 `task` 工具 |

### 12.3 数据安全

| 风险 | 缓解 |
|------|------|
| Ralph Loop 状态泄露 | 仅存 metadata，不存 transcript |
| Background task 跨 session 泄露 | parentSessionId 校验 |
| MCP API key | 环境变量传递，日志 mask |

---

## 13. 可观测性与日志

### 13.1 结构化日志

```typescript
interface LogEntry {
  timestamp: string;
  level: "debug" | "info" | "warn" | "error";
  module: string;          // "ralph-loop", "category-router"
  sessionId?: string;
  taskId?: string;
  correlationId?: string;  // 贯穿 delegation chain
  message: string;
  data?: Record<string, unknown>;
  durationMs?: number;
}
// 输出到: ~/.openclaw/logs/oh-my-claw.log
```

### 13.2 关键指标

| 指标 | 类型 | 说明 |
|------|------|------|
| `omc.hook.execution` | histogram | hook 执行时间 |
| `omc.hook.error` | counter | hook 错误次数 |
| `omc.background.active` | gauge | 活跃背景任务数 |
| `omc.background.completed` | counter | 完成数 (status: success/error/cancelled) |
| `omc.background.circuit_breaker` | counter | Circuit breaker 触发次数 |
| `omc.fallback.triggered` | counter | Fallback 触发 (layer: agent/runtime) |
| `omc.recovery.triggered` | counter | Recovery 触发 (by error_type) |
| `omc.ralph.iterations` | histogram | Ralph Loop 迭代次数 |
| `omc.category.resolution` | histogram | Category 解析时间 |
| `omc.lsp.request` | histogram | LSP 延迟 (by server, method) |
| `omc.degradation.level` | gauge | 降级级别 (0-4) |

### 13.3 诊断命令

```
/omc-status          — 降级级别、活跃 tasks、hook 状态、LSP servers
/omc-metrics         — 最近 1h 关键指标
/omc-debug <hook>    — 启用 debug 日志 (下次触发)
```

---

## 14. 风险与应对

| 风险 | 影响 | 概率 | 缓解 |
|------|------|------|------|
| DeepSeek API 不稳定 | 编排不可用 | 中 | 双层 fallback (ds-v3 → ds-r1 → native) |
| openclaw plugin-sdk 变更 | 编译错误 | 中 | 锁定版本, CI 兼容测试 |
| subagent 过多导致 OOM | 服务中断 | 低 | depth limit + TTL + circuit breaker |
| Channel-aware 不一致 | 体验差 | 低 | 核心编排 channel-agnostic |
| 配置复杂 | 上手难 | 中 | 默认值即最佳实践，零配置可用 |

---

## 15. 附录

### 附录 A: 功能清单

| 维度 | 数量 | 详情 |
|------|------|------|
| 专家 Agent | 11 | 编排/顾问/执行/规划/探索/检索/分析/审查/编排/执行/视觉 |
| 任务分类 | 8 | visual-engineering/ultrabrain/deep/artistry/quick/writing/unspecified-low/unspecified-high |
| 自定义 Hook | 22+ | 5 组: session/tool-guard/transform/continuation/skill |
| 自定义工具 | 20+ | 6 LSP + 2 AST-grep + delegate-task + bg-output + bg-cancel + hashline-edit + skill + skill_mcp + grep + glob + look-at + session-manager |
| Slash 命令 | 9 | /ralph-loop /ulw-loop /cancel-ralph /refactor /start-work /stop-continuation /init-deep /handoff /remove-ai-slops |
| 内置 Skill | 3 | git-master / review-work / ai-slop-remover |
| 内置 MCP | 3 | Exa websearch / Context7 docs / Grep.app |
| 降级级别 | 5 | L0 (全功能) → L4 (plugin 禁用) |
| 错误恢复 | 5 | tool_result_missing / unavailable_tool / thinking_block_order / thinking_disabled_violation / assistant_prefill_unsupported |
| 总工期 | 33-42 天 | 8 个垂直切片，MVP 在 15-19 天 |

### 附录 B: 参考资料

- [oh-my-openagent](https://github.com/code-yeongyu/oh-my-openagent) — npm: `oh-my-opencode` v3.17.5
- [oh-my-openagent AGENTS.md](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/AGENTS.md)
- [oh-my-openagent Features](https://github.com/code-yeongyu/oh-my-openagent/blob/dev/docs/reference/features.md)
- [openclaw](https://github.com/openclaw/openclaw) — npm: `openclaw` v2026.4.24
- [openclaw AGENTS.md](https://github.com/openclaw/openclaw/blob/main/AGENTS.md)
- [openclaw Vision](https://github.com/openclaw/openclaw/blob/main/VISION.md)
- [openclaw Plugin API](https://docs.openclaw.ai/tools/plugin)
- [openclaw Sub-agents](https://docs.openclaw.ai/tools/subagents)
- [openclaw Hooks](https://docs.openclaw.ai/automation/hooks)
- [openclaw MCP](https://docs.openclaw.ai/cli/mcp)
- [The Harness Problem](https://blog.can.ac/2026/02/12/the-harness-problem/) — Hashline Edit 灵感

### 附录 C: ds-v4-pro vs claude-4-6 方案对比

| 维度 | claude-4-6 | ds-v4-pro (本方案) |
|------|-----------|-------------------|
| 主编排模型 | Claude Opus 4 | DeepSeek V4 Pro |
| 模型变体 | 4 套 (Claude/GPT/GPT-5.5/Gemini) | 1 套统一 |
| 代码量 | 基准 | **减少 ~30-40%** |
| prompt count | 4 variants × 11 agents ≈ 44 | 1 template × 11 agents ≈ 11 |
| Category 路由 | per-provider mapping (4 套) | 统一模型 + 参数区分 |
| 成本 | Opus 高 | 高性价比 |
| 推理 | extended thinking (32K) | native reasoning |
| 核心逻辑 | 相同 | 相同 |

---

## 16. 模块依赖图与开发顺序

### 16.1 模块依赖关系

```
                   ┌─────────────────────────────┐
                   │       Plugin Entry            │
                   │  (index.ts + register)       │
                   └─────────────┬───────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
     ┌────▼─────┐         ┌─────▼─────┐         ┌──────▼─────┐
     │  config/ │         │  shared/  │         │ metrics/   │
     │ schema   │◄────────│  logger   │────────►│ degradation│
     │ loader   │         │  err-bndry│         │            │
     │ defaults │         │  types    │         │            │
     └────┬─────┘         └─────┬─────┘         └──────┬─────┘
          │                     │                      │
    ┌─────┴─────┐              │                      │
    │  agents/  │              │                      │
    │  registry │              │                      │
    │  prompt-  │              │                      │
    │  builder  │              │                      │
    └─────┬─────┘              │                      │
          │                    │                      │
    ┌─────┴─────────────────┐  │   ┌──────────────────┴──────┐
    │    categories/        │  │   │     background/          │
    │  builtin + registry   │  │   │  manager + concurrency   │
    │  router               │  │   │  loop-detector + spawner │
    └─────┬─────────────────┘  │   └──────────────────┬──────┘
          │                    │                      │
    ┌─────┴─────────────────┐  │   ┌──────────────────┴──────┐
    │  tools/               │  │   │     hooks/               │
    │  delegate-task ───────┼──┼───┤  ralph-loop              │
    │  background-task ─────┼──┘   │  todo-enforcer           │
    │  lsp/ ast-grep/       │      │  model-fallback          │
    │  hashline/ skill/     │      │  runtime-fallback        │
    └─────┬─────────────────┘      │  session-recovery        │
          │                        │  preemptive-compact      │
    ┌─────┴─────────────────┐      │  comment-checker         │
    │  mcp/ (3 builtin)     │      │  keyword-detector        │
    └───────────────────────┘      │  rules-injector          │
                                   │  coordination            │
    ┌───────────────────────┐      └─────────────────┬────────┘
    │  commands/ (9)        │                        │
    └───────────────────────┘      ┌─────────────────┴────────┐
    ┌───────────────────────┐      │  features/               │
    │  skills/ (3 SKILL.md) │      │  context-injector        │
    └───────────────────────┘      │  skill-mcp-manager       │
                                   └──────────────────────────┘
```

**依赖链:**

```
config → shared → agents → categories → tools → hooks → commands → mcp
  │       │         │                                              │
  └───────┴─────────┴──────────────────────────────────────────────┘
                    background/ (贯穿所有层级)
```

### 16.2 严格构建顺序

| 层 | 模块 | 上游依赖 | 说明 |
|----|------|---------|------|
| **L0 基础层** | config + shared + metrics | 无 | schema 定义、日志、错误边界 |
| **L1 模型层** | agents | config, shared | agent registry + prompt builder |
| **L2 路由层** | categories | config, agents | builtin categories + router |
| **L3 编排层** | background | config, shared | BackgroundManager 独立于 agent/category |
| **L4 工具层** | tools/* | config, categories, background | 每工具注册自身 |
| **L5 Hook 层** | hooks/* | config, agents, categories, background, tools | 每 hook 独立但需 HookCoordinator |
| **L6 命令层** | commands/* | hooks, tools, background | slash 命令 |
| **L7 资产层** | mcp, skills, features | config | MCP server 定义 + SKILL.md |

### 16.3 并行化机会

```
同层内模块可并行开发:
  L4 tools:   5 个子目录可并行（lsp/ast-grep/delegate-task/background-task/hashline-edit）
  L5 hooks:   12 个子目录可并行（ralph-loop/todo-enforcer/.../rules-injector）
  L6 commands: 9 个命令可并行

Ralph Loop 和 Todo Enforcer 互斥依赖 HookCoordinator → 需协调者先实现
Model Fallback 和 Runtime Fallback 互斥依赖 HookCoordinator → 同上
```

---

## 17. DeepSeek V4 Pro 特定约束

### 17.1 API 特性

| 特性 | DeepSeek V4 Pro | 对设计的影响 |
|------|----------------|-------------|
| **Context Window** | 128K tokens | Preemptive compaction 阈值可上调至 75% |
| **Max Output** | ~8K-16K tokens | 需要 truncation；大任务自动拆分为多个 subtask |
| **Reasoning** | 原生 reasoning mode（chain-of-thought） | thinking.budgetTokens 控制思考深度而非开关 |
| **Temperature** | 0.0-2.0 | 0.1 = 高确定性/quick, 0.3 = 均衡/编排, 0.8 = 创意/artistry |
| **Rate Limit** | 每分钟请求数（RPM）限制 | ConcurrencyManager 需要集成 RPM 感知 |
| **Function Calling** | 原生支持 tool use | 无需特殊格式处理 |
| **Vision** | 支持图片输入（vision model） | Multimodal-Looker 功能可用 |

### 17.2 DeepSeek 特定的 Fallback 策略

```
主链: ds-v4-pro → ds-v3 → ds-r1 → openclaw-native

fallback 触发条件:
  - HTTP 429 (rate limit) → 30s 冷却后重试 ds-v4-pro
                            → 仍失败 → 切换到 ds-v3
  - HTTP 500/502/503 → 立即切换
  - 超时 (30s 无响应) → 重试 1 次 → 失败则切换

RPM 感知:
  - 维护滑动窗口计数器 (60s)
  - 接近限制时自动排队 + 增加 temperature 降低 token 消耗
```

### 17.3 与 opencode 上的 OmO 对比的特殊考量

| 考量 | OmO (opencode/Claude) | oh-my-claw (openclaw/DeepSeek) |
|------|----------------------|-------------------------------|
| Thinking 模式 | extended_thinking (需要 API 参数) | 原生 reasoning chain-of-thought |
| 工具调用格式 | Claude tool_use XML | 标准 function call JSON |
| Context 管理 | 200K (Opus) | 128K → 更频繁的 compaction |
| 成本优化 | 不需要特别关注 | 高性价比模型 → 减少 fallback 压力 |

---

## 18. 开发环境与性能预算

### 18.1 开发环境搭建

```bash
# 1. 克隆 openclaw monorepo
git clone https://github.com/openclaw/openclaw.git
cd openclaw
pnpm install

# 2. 创建 oh-my-claw extension
mkdir -p extensions/oh-my-claw/src
# 按 §3.3 目录结构创建文件

# 3. 注册到 openclaw (通过 openclaw.json 的 plugins 配置)
openclaw config set plugins.entries.oh-my-claw.source "./extensions/oh-my-claw"

# 4. 启动开发
openclaw gateway --port 18789 --verbose
# 或: pnpm openclaw gateway --verbose

# 5. 运行测试
cd extensions/oh-my-claw
pnpm vitest
```

### 18.2 性能预算

| 指标 | 目标 | 说明 |
|------|------|------|
| **Plugin 加载时间** | < 2s | `register(api)` 执行完毕，不含 LSP warmup |
| **Hook handler 执行** | < 100ms per handler | 除 LSP/AST-grep/comment-checker 外 |
| **Background task 启动** | < 3s (P50), < 10s (P99) | spawnSubagent + 并发控制 |
| **LSP server 初始化** | < 60s (timeout) | 35 server 并行 warmup |
| **AST-Grep search** | < 5s (P50), < 15s (P99) | 取决于 repo 大小 |
| **Ralph Loop 迭代** | < 2s 完成检测 | 不阻塞 agent 响应 |
| **Memory 使用** | < 200MB (base), < 500MB (peak) | 含 BackgroundManager 活跃 tasks |
| **Plugin 关闭** | < 5s | 清理 background tasks + LSP servers |

### 18.3 CI/CD 集成

```yaml
# .github/workflows/oh-my-claw-ci.yml
name: oh-my-claw CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - run: pnpm install
      - run: pnpm vitest run --coverage
      - run: pnpm tsc --noEmit
      - name: Integration smoke
        run: |
          pnpm openclaw gateway &
          sleep 5
          curl http://localhost:18789/health
          # validate plugin loaded
```

---

## 19. 完善评估与迭代方向

### 19.1 当前方案已覆盖

| 维度 | 覆盖度 | 自评 |
|------|--------|------|
| 架构设计 | ✅ 完整 | 11 agent + 8 category + 22 hook + 20 tool + 3 层架构 |
| 实现细节 | ✅ 详细 | TypeScript 接口 + 算法 + 状态机 + 流程图 |
| 韧性设计 | ✅ 完整 | 5 级降级 + 5 种恢复 + 双层 fallback + error boundary |
| 通道兼容 | ✅ 完整 | 4 类通道 × 16 功能兼容性 |
| 安全考量 | ✅ 覆盖 | 进程/Prompt/数据 3 维度 |
| 可观测性 | ✅ 完整 | 结构化日志 + 11 指标 + 3 诊断命令 |
| 测试策略 | ✅ 有序 | 单位/集成/E2E 金字塔 |
| 开发顺序 | ✅ 新增 | 7 层依赖图 + 并行机会 |
| 平台约束 | ✅ 新增 | DeepSeek API 特定约束 |
| 性能预算 | ✅ 新增 | 8 项指标目标 |

### 19.2 后续可迭代方向

| 方向 | 说明 | 优先级 |
|------|------|--------|
| **多模型混合编排** | 当未来引入其他模型（GPT/Gemini）时，Category 路由可扩展 per-provider mapping | 低 |
| **Skill Workshop 集成** | 利用 openclaw 的 Skill Workshop 创建 oh-my-claw 专属技能 | 中 |
| **ACP 深度集成** | delegate-task 支持 ACP harness 参数，调用外部 Codex/Claude Code 实例 | 中 |
| **Team Mode 可视化** | tmux 多 agent 实时可视化（仅本地 TUI） | 低 |
| **Interactive Bash** | tmux 集成的 REPL/debugger 交互终端 | 低 |
| **Gemini prompt 变体** | 如果后续支持 Gemini，复刻 OmO 的 Gemini overlay | 低 |
| **Memory-aware Category** | ContextAwareRouter 利用 memory 历史成功率动态选参 | 中 |
| **Agent 自优化** | 监控 agent 成功率 → 自动调参 → memory 记录最优配置 | 低 |
