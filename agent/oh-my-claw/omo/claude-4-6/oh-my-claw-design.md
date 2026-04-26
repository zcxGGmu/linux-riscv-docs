# oh-my-claw 项目设计方案 (详细版)

> 参考 oh-my-openagent (OmO) 对 opencode 的增强模式，为 openclaw 设计同等级别的增强层。

---

## 1. 项目定位

### 1.1 背景

oh-my-openagent (OmO) 是 opencode 的一个纯插件增强层，通过 `@opencode-ai/plugin` 接口将单 agent 编码助手升级为多模型编排团队。它不修改 opencode 源码，而是通过 10 个 hook 点注入 11 个专家 agent、40+ 行为 hook、26 个自定义工具、8 个任务分类、7 个内置 skill 和 3 个 MCP server。

oh-my-claw 的目标是将同样的增强理念应用到 openclaw —— 一个功能更丰富的多通道 AI 网关平台。

### 1.2 定位对比

| 维度 | oh-my-openagent (参考) | oh-my-claw (目标) |
|------|----------------------|-------------------|
| 宿主 | opencode (Go, TUI 编码助手) | openclaw (TS, 多通道 AI 网关) |
| 宿主 hook 数量 | 10 个 | 28 个 (更细粒度) |
| 形态 | opencode plugin (`PluginModule`) | openclaw plugin (`openclaw.plugin.json` + `register(api)`) |
| 核心价值 | 单 agent → 多模型编排团队 | 多通道网关 → 深度编排 + 自愈 + 质量管控智能体平台 |
| 运行环境 | 本地 TUI 终端 | 本地网关 + 25+ 远程通道 (Discord/Slack/Telegram...) |

### 1.3 设计哲学

继承 OmO 的核心理念：
- **"Human intervention is a failure signal"** — 减少人工干预，agent 应自主完成任务
- **专家分工** — 不同任务由不同专家 agent 处理，而非一个通用 agent 做所有事
- **韧性优先** — 自动恢复错误、自动切换模型、自动续跑未完成任务
- **质量管控** — AI slop 检测、代码审查、计划审查、Oracle 验证

---

## 2. 能力差距分析 (Gap Analysis)

### 2.1 openclaw 已具备的能力 ✅

| 能力 | openclaw 现状 | 详细说明 |
|------|-------------|---------|
| 多 Agent | ✅ 完整 | `agents.list[]` 配置，每个 agent 有独立 id/model/skills/sandbox/workspace/identity/thinkingDefault。subagent 完整生命周期: spawn(fork/isolated context) / steer(重定向) / kill |
| Plugin Hook 系统 | ✅ 28 种 hook | 三种执行模式: void(并行fire-and-forget), modifying(顺序合并), claiming(首个handled胜出)。覆盖 agent/message/tool/session/subagent/gateway/install 全生命周期 |
| MCP 支持 | ✅ 双向 | stdio + HTTP/SSE transport，plugin-bundled MCP，openclaw 自身也作为 MCP server 暴露工具 |
| Skill 系统 | ✅ 53 个内置 | SKILL.md 格式 + ClawHub 市场 + Skill Workshop (agent 驱动的 skill 创建/审查)。per-agent skill 过滤 + prompt chars 限制 |
| Slash 命令 | ✅ 完整 | 命令注册 + 参数解析 + 平台原生映射 (Discord slash commands, Telegram bot menus)。skill 也可注册命令 |
| Context Engine | ✅ 可插拔 | 完整接口: bootstrap/ingest/assemble/compact/maintenance/subagent lifecycle。支持 transcript rewrite、prompt cache retention |
| Task/Workflow | ✅ 完整 | TaskFlowRegistry: flow/step/blocking/wait conditions/cancel。TaskRegistry: 状态跟踪/owner access/audit |
| Session 管理 | ✅ SQLite | 持久化 + 锁 + compaction + 修复 (transcript repair, attachment repair) |
| Memory 系统 | ✅ 高级 | embedding + 时间衰减 + dreaming (consolidation) + QMD (query-managed documents)。OmO 无此能力 |
| 多通道 | ✅ 25+ | Discord/Slack/Telegram/WhatsApp/Matrix/Feishu/IRC/Nostr/Signal/Line/iMessage 等 |
| 多 Provider | ✅ 120+ extension | OpenAI/Anthropic/Google/Ollama/LMStudio/Bedrock/DeepSeek/Qwen/Kimi 等 |
| Cron 调度 | ✅ | 隔离 agent 定时执行，model override + skill snapshot + delivery dispatch |
| ACP 协议 | ✅ | 外部 harness 集成 (Codex/Claude Code)，persistent/oneshot 模式 |

### 2.2 oh-my-openagent 有而 openclaw 缺失的能力 ❌

以下按优先级分组，每项包含 OmO 的实现细节和 openclaw 的现状分析：

#### P0 — 核心编排能力 (必须首批实现)

| # | 能力 | OmO 实现摘要 | openclaw 现状 |
|---|------|-------------|-------------|
| 1 | **专家 Agent 角色体系** | 11 个角色化 agent，每个有: 专属 prompt 模板 (含 model-specific 变体: Claude/GPT/Gemini)、工具限制 (deny/allow list)、模型分配 + fallback chain、AgentPromptMetadata (cost/category/triggers/useWhen/avoidWhen)。Sisyphus prompt 含 Intent Gate → Codebase Assessment → Exploration → Implementation → Completion 五阶段系统 | agent 有 id/model/skills 配置，但无角色化 prompt 工程、无工具限制策略、无 model-specific prompt 变体、无 delegation table |
| 2 | **Category 路由系统** | 8 个领域分类，每个绑定最优模型 + thinking level + temperature。delegate-task 工具实现: category → model resolution pipeline (user override → category default → fallback chain → connected providers)。支持 unstable agent 检测 (gemini/minimax → 强制 background) | 无。subagent 需手动指定 agentId + model，无按领域自动路由 |
| 3 | **Background Agent 并行执行** | BackgroundManager: per-provider 并发控制 (ConcurrencyManager, promise-based queue)、circuit breaker (连续 20 次相同 tool call → 熔断)、subagent depth limit (默认 3 层)、task TTL (30min)、stale timeout (45min)。通知系统: batch `<system-reminder>` 注入父 session。tmux 可视化 (可选) | subagent 是串行的 (spawn → wait → result)，无并行编排、无并发控制、无 circuit breaker、无父 session 通知机制 |

#### P1 — 质量与韧性 (第二批实现)

| # | 能力 | OmO 实现摘要 | openclaw 现状 |
|---|------|-------------|-------------|
| 4 | **Ralph Loop (自驱动循环)** | 监听 session.idle 事件。检测 `<promise>DONE</promise>` 完成标记 (双路径: transcript 文件扫描 + session messages API)。未完成 → 注入续跑 prompt。安全阀: 默认 100 次迭代。Ultrawork 变体: 需 Oracle 验证 `<promise>VERIFIED</promise>` 才算完成。状态持久化到 `.sisyphus/ralph-loop.local.md` | 无。agent 回复后即停止，无自动续跑机制 |
| 5 | **Todo Continuation Enforcer** | 监听 session.idle。检测未完成 todo → 2s 倒计时 → 注入续跑 prompt。防呆: 停滞检测 (连续 3 次 incomplete 不减少 → 停止)、连续失败上限 (5 次 + 指数退避)、compaction guard (60s)、token limit 检测 | 无 |
| 6 | **Model Fallback Chain** | 双层: (1) model-fallback: per-agent fallback chain，pre-request 拦截 chat.message，检查 connected providers 可达性，跳过 no-op (同 provider+model)。(2) runtime-fallback: 错误触发 (429/500/502/503/504)，abort → 用 fallback model 重发 last user message，cooldown 60s，最多 3 次 | 仅 `model.fallbacks[]` 基础配置，无 runtime 自动切换、无 connected providers 检查、无 cooldown |
| 7 | **Session Recovery** | 5 种错误模式自动恢复: tool_result_missing (注入 synthetic error result) / unavailable_tool (注入 "tool not available" result) / thinking_block_order (重排 thinking blocks) / thinking_disabled_violation (剥离 thinking parts) / assistant_prefill_unsupported。去重 via processingErrors Set | 无自动恢复机制 |
| 8 | **LSP 工具集** | 6 个工具 + 3 层 client 架构: Transport (JSON-RPC over stdin/stdout) → Connection (initialize handshake) → Client (protocol methods)。LSPServerManager 单例: 引用计数 + 5min idle timeout + 60s init timeout。35+ 内置 server 定义 (TypeScript/Go/Python/Rust/Java...) | 无 LSP 集成 |
| 9 | **AST-Grep 工具** | 2 个工具 (search/replace)，25 种语言。底层调用 sg CLI (auto-download binary)。replace 需两遍执行 (JSON 收集 + 写入)。空结果提示 pattern 修复建议 | 无 |

#### P2 — 增强体验

| # | 能力 | OmO 实现摘要 | openclaw 现状 |
|---|------|-------------|-------------|
| 10 | **Preemptive Compaction** | 阈值: 78% context window。token 缓存: 每次 assistant 完成时更新。触发: tool.execute.after。cooldown: 60s。调用 session.summarize() 执行压缩 | 仅被动 compaction |
| 11 | **Comment Checker** | 外部 binary (@code-yeongyu/comment-checker)。拦截 write/edit/multiedit/apply_patch 的 before/after。检测到 AI slop → 将警告追加到 tool output，agent 自动修复。支持 custom_prompt | 无 |
| 12 | **Dynamic Prompt Builder** | 模块化 prompt 组装: identity → key triggers → tool selection table (cost-sorted) → explore/librarian sections → delegation table → category+skills guide → hard blocks → anti-patterns。输入: AvailableAgent/Tool/Skill/Category 数组 | 静态 system prompt |
| 13 | **Hashline Edit** | LINE#ID 哈希锚定: xxHash32 → 256 个 2-char code (16-char nibble dictionary)。验证: 所有 ref 对比当前文件内容，mismatch → 显示 context window + 更新后的 hash。编辑: bottom-up 排序 → 去重 → overlap 检测 → apply → formatter 触发 | 无 |
| 14 | **Skill-Embedded MCP** | skill 声明 mcpConfig → SkillMcpManager 按需启停 MCP server。tool: skill_mcp(mcp_name, tool_name/resource_name/prompt_name, arguments, grep)。生命周期: skill 加载时启动，session 结束时清理 | skill 无 MCP 绑定 |
| 15 | **Builtin MCP** | 3 个远程 MCP: Exa web search (mcp.exa.ai)、Context7 docs (mcp.context7.com)、Grep.app GitHub search (mcp.grep.app)。均为 HTTPS transport，可选 API key | 需手动配置 |

#### P3 — 高级特性

| # | 能力 | OmO 实现摘要 | openclaw 现状 |
|---|------|-------------|-------------|
| 16 | **Keyword Detector** | 3 种模式: ultrawork (`/\b(ultrawork\|ulw)\b/i`)、search (多语言关键词 EN/KR/JP/CN/VN)、analyze (多语言)。ultrawork 有 4 种 model-specific prompt (Claude/GPT/GPT-5.5/Gemini)。注入: prepend 到首个 text part | 无 |
| 17 | **Rules Injector** | 自动注入层级化 AGENTS.md。/init-deep 命令: 4 阶段生成 (Discovery → Score → Generate → Review) | 已有 context files (agents.md/soul.md/identity.md) 但无层级化注入和自动生成 |
| 18 | **Interactive Bash** | tmux 集成的交互式终端，支持长时间运行的命令 | 无 |
| 19 | **Team Mode** | tmux 多 agent 可视化布局 (main-horizontal/vertical/tiled)，per-pane agent 隔离 | 无 |

---

## 3. 架构设计

### 3.1 整体架构

```
┌──────────────────────────────────────────────────────────────┐
│                        openclaw                               │
│  gateway ─ agents ─ channels ─ plugins ─ context-engine       │
│  sessions ─ memory ─ cron ─ mcp ─ tasks ─ routing             │
├──────────────────────────────────────────────────────────────┤
│                    oh-my-claw plugin                           │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    Plugin Entry                          │ │
│  │  setup(api) → config → managers → tools → hooks          │ │
│  ├──────────┬──────────┬──────────┬──────────┬────────────┤ │
│  │ Agents   │ Category │Background│  Tools   │   Hooks    │ │
│  │          │ Router   │ Manager  │          │            │ │
│  │ sisyphus │ visual-  │ concurr- │ LSP (6)  │ ralph-loop │ │
│  │ oracle   │ engineer │ ency mgr │ AST-grep │ todo-cont  │ │
│  │ hephaest │ ultra-   │ circuit  │ delegate │ model-fall │ │
│  │ promethe │ brain    │ breaker  │ bg-task  │ session-   │ │
│  │ explore  │ deep     │ depth    │ hashline │  recovery  │ │
│  │ libraria │ quick    │ limit    │ skill    │ preemptive │ │
│  │ metis    │ artistry │ tmux viz │ skill-   │ comment-   │ │
│  │ momus    │ writing  │ notify   │  mcp     │  checker   │ │
│  │ atlas    │ unspec-* │          │ look-at  │ keyword-   │ │
│  │ junior   │          │          │          │  detector  │ │
│  ├──────────┴──────────┴──────────┴──────────┴────────────┤ │
│  │  Skills (git-master, review-work, ai-slop-remover)      │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │  MCPs (Exa websearch, Context7 docs, Grep.app)          │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │  Commands (/ralph-loop /refactor /start-work /handoff)  │ │
│  ├─────────────────────────────────────────────────────────┤ │
│  │  Config (oh-my-claw.json — Zod schema validation)       │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 集成方式 — openclaw Plugin 接入

oh-my-claw 作为 openclaw extension 接入，利用 openclaw 的 plugin-sdk：

```typescript
// extensions/oh-my-claw/index.ts
import { definePluginEntry } from "openclaw/plugin-sdk";

export default definePluginEntry({
  id: "oh-my-claw",
  name: "Oh My Claw",
  configSchema: ohMyClawConfigSchema,

  register(api) {
    // 1. 加载配置
    const config = loadPluginConfig(api.pluginConfig);

    // 2. 创建 managers
    const backgroundManager = new BackgroundManager(api, config.background);
    const skillMcpManager = new SkillMcpManager(api);

    // 3. 注册工具
    registerLspTools(api, config);
    registerAstGrepTools(api, config);
    registerDelegateTaskTool(api, config, backgroundManager);
    registerBackgroundTaskTools(api, backgroundManager);
    registerHashlineEditTool(api, config);
    registerSkillTool(api);
    registerSkillMcpTool(api, skillMcpManager);

    // 4. 注册 hooks
    registerRalphLoopHook(api, config);
    registerTodoContinuationHook(api, config);
    registerModelFallbackHook(api, config);
    registerRuntimeFallbackHook(api, config);
    registerSessionRecoveryHook(api, config);
    registerPreemptiveCompactionHook(api, config);
    registerCommentCheckerHook(api, config);
    registerKeywordDetectorHook(api, config);
    registerPromptBuilderHook(api, config);

    // 5. 注册命令
    registerBuiltinCommands(api, config);

    // 6. 注册 MCP
    registerBuiltinMcps(api, config);

    // 7. 注册 service (lifecycle)
    api.registerService({
      id: "oh-my-claw",
      start: () => backgroundManager.start(),
      stop: () => backgroundManager.shutdown(),
    });
  },
});
```

### 3.3 目录结构

```
extensions/oh-my-claw/
├── openclaw.plugin.json          # plugin manifest
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts                  # plugin entry (definePluginEntry)
│   │
│   ├── config/
│   │   ├── schema.ts             # Zod schema (root + all sub-schemas)
│   │   ├── loader.ts             # 多级配置: project > user > defaults
│   │   ├── defaults.ts           # 默认值常量
│   │   └── types.ts              # 导出类型
│   │
│   ├── agents/                   # 角色化 agent 定义
│   │   ├── registry.ts           # agent 注册表 + createBuiltinAgents()
│   │   ├── types.ts              # AgentDefinition, AgentPromptMetadata
│   │   ├── prompt-builder/       # 动态 prompt 组装
│   │   │   ├── core-sections.ts  # identity, key-triggers, tool-selection
│   │   │   ├── policy-sections.ts # hard-blocks, anti-patterns
│   │   │   ├── category-skills-guide.ts
│   │   │   └── tool-categorization.ts
│   │   ├── sisyphus/             # 编排者 (4 prompt 变体)
│   │   │   ├── default.ts        # Claude prompt
│   │   │   ├── gpt.ts            # GPT prompt
│   │   │   ├── gpt-5-5.ts        # GPT-5.5 prompt
│   │   │   └── gemini.ts         # Gemini overlay
│   │   ├── oracle.ts             # 架构顾问 (3 prompt 变体)
│   │   ├── hephaestus/           # 深度执行者 (4 prompt 变体)
│   │   ├── prometheus/           # 战略规划者 (6 子模块)
│   │   │   ├── system-prompt.ts
│   │   │   ├── identity-constraints.ts
│   │   │   ├── interview-mode.ts
│   │   │   ├── plan-generation.ts
│   │   │   ├── high-accuracy-mode.ts
│   │   │   └── plan-template.ts
│   │   ├── explore.ts            # 代码探索
│   │   ├── librarian.ts          # 文档/OSS 检索
│   │   ├── metis.ts              # 计划分析
│   │   ├── momus.ts              # 计划审查
│   │   ├── atlas/                # todo 编排者
│   │   ├── sisyphus-junior/      # category-spawned 执行者
│   │   └── multimodal-looker.ts  # 视觉分析
│   │
│   ├── categories/               # Category 路由
│   │   ├── registry.ts           # 分类注册 + 合并逻辑
│   │   ├── router.ts             # category → model resolution pipeline
│   │   ├── builtin/              # 内置分类定义
│   │   │   ├── anthropic.ts
│   │   │   ├── openai.ts
│   │   │   ├── google.ts
│   │   │   └── kimi.ts
│   │   └── types.ts
│   │
│   ├── background/               # 并行 agent 管理
│   │   ├── manager.ts            # BackgroundManager 主类
│   │   ├── concurrency.ts        # ConcurrencyManager (per-provider queue)
│   │   ├── loop-detector.ts      # Circuit breaker
│   │   ├── depth-limits.ts       # Subagent depth guard
│   │   ├── spawner.ts            # Task spawner + fallback
│   │   ├── notification.ts       # Parent session notification
│   │   ├── constants.ts          # 时间常量
│   │   ├── tmux.ts               # tmux 可视化 (可选)
│   │   └── types.ts
│   │
│   ├── tools/                    # 增强工具
│   │   ├── lsp/                  # LSP 工具集 (6 tools)
│   │   │   ├── client-transport.ts   # JSON-RPC over stdin/stdout
│   │   │   ├── client-connection.ts  # initialize handshake
│   │   │   ├── client.ts             # protocol methods
│   │   │   ├── server-manager.ts     # singleton + ref counting + idle timeout
│   │   │   ├── server-definitions.ts # 35+ builtin server configs
│   │   │   ├── goto-definition.ts
│   │   │   ├── find-references.ts
│   │   │   ├── symbols.ts
│   │   │   ├── diagnostics.ts
│   │   │   └── rename.ts
│   │   ├── ast-grep/             # AST pattern search/replace
│   │   │   ├── tools.ts
│   │   │   ├── cli.ts            # sg binary invocation
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
│   ├── hooks/                    # 增强 hooks
│   │   ├── ralph-loop/           # 自驱动完成循环
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
│   │   ├── model-fallback/       # agent-aware 模型切换
│   │   │   ├── hook.ts
│   │   │   ├── chain-traversal.ts
│   │   │   └── state.ts
│   │   ├── runtime-fallback/     # 错误触发的 auto-retry
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
│   │   │   └── ultrawork/        # model-specific prompts
│   │   └── rules-injector/       # AGENTS.md 层级注入
│   │
│   ├── skills/                   # 内置 skill 定义
│   │   ├── registry.ts
│   │   ├── git-master/           # 3-mode git 专家
│   │   ├── review-work/          # 5-agent 并行审查
│   │   └── ai-slop-remover/      # AI 代码异味清除
│   │
│   ├── commands/                 # 内置 slash 命令
│   │   ├── registry.ts
│   │   ├── ralph-loop.ts         # /ralph-loop, /ulw-loop, /cancel-ralph
│   │   ├── refactor.ts           # /refactor (6-phase LSP+AST)
│   │   ├── start-work.ts         # /start-work (Prometheus planning)
│   │   ├── handoff.ts            # /handoff (context preservation)
│   │   ├── init-deep.ts          # /init-deep (AGENTS.md generation)
│   │   ├── stop-continuation.ts
│   │   └── remove-ai-slops.ts
│   │
│   └── mcp/                      # 内置 MCP server
│       ├── websearch.ts          # Exa (default) / Tavily
│       ├── context7.ts           # Context7 docs
│       └── grep-app.ts           # Grep.app GitHub search
│
├── skills/                       # SKILL.md 格式的 skill 文件
│   ├── git-master/SKILL.md
│   ├── review-work/SKILL.md
│   └── ai-slop-remover/SKILL.md
│
└── docs/
    ├── guide/
    │   ├── overview.md
    │   ├── orchestration.md
    │   └── installation.md
    └── reference/
        ├── features.md
        └── configuration.md
```

### 3.4 与 openclaw 的 28 个 Hook 集成映射

| openclaw Hook | 执行模式 | oh-my-claw 使用 |
|--------------|---------|----------------|
| `before_model_resolve` | modifying (first-defined wins) | Model Fallback: 替换为 fallback model |
| `before_prompt_build` | modifying (concat context) | Dynamic Prompt Builder: 注入角色化 prompt + rules + AGENTS.md |
| `before_agent_start` | modifying | Agent 角色体系: 注入 agent-specific 配置 |
| `before_agent_reply` | claiming | Ralph Loop: 检测完成/注入续跑; Keyword Detector: 模式切换 |
| `llm_input` | void | Token 缓存更新 (for preemptive compaction) |
| `llm_output` | void | Session Recovery: 错误检测; Runtime Fallback: 错误触发 |
| `agent_end` | void | Todo Continuation: idle 检测触发 |
| `before_compaction` | void | Preemptive Compaction: 标记 compaction 进行中 |
| `after_compaction` | void | Todo Enforcer: compaction guard 激活 (60s) |
| `before_reset` | void | Ralph Loop: 清理状态 |
| `message_received` | void | Keyword Detector: 扫描用户消息 |
| `before_tool_call` | modifying | Comment Checker: 注册 pending write/edit; Hashline: 验证 |
| `after_tool_call` | void | Comment Checker: 运行检测; Preemptive Compaction: 触发检查 |
| `tool_result_persist` | sync modifying | Hashline Edit: diff 增强 |
| `session_start` | void | Session Recovery: 初始化状态 |
| `session_end` | void | Background Manager: 清理; Ralph Loop: 清理 |
| `subagent_spawning` | modifying | Category Router: 解析 category → model; Background Manager: 并发控制 |
| `subagent_spawned` | void | Background Manager: 注册 task |
| `subagent_ended` | void | Background Manager: 结果收集 + 父 session 通知 |
| `subagent_delivery_target` | modifying | Background Manager: 路由结果到正确的父 session |
| `gateway_start` | void | Service 初始化 |
| `gateway_stop` | void | Service 清理 |

---

## 4. 核心模块详细设计

### 4.1 专家 Agent 角色体系 (P0)

#### 4.1.1 Agent 注册表

11 个角色化 agent，通过 openclaw 的 `api.registerHook("before_agent_start", ...)` 注入配置：

```typescript
// agents/types.ts
interface AgentDefinition {
  id: string;
  role: "orchestrator" | "advisor" | "deep-worker" | "planner" | "grep" | "reference"
        | "plan-consultant" | "plan-reviewer" | "conductor" | "executor" | "vision";
  description: string;
  model: { primary: string; fallbacks: FallbackEntry[] };
  thinkingDefault: "off" | "low" | "medium" | "high" | "xhigh";
  reasoningEffort?: "none" | "low" | "medium" | "high" | "xhigh";
  maxTokens: number;
  toolPolicy: "full" | "read-only" | "search-only";  // 映射到 deny/allow list
  promptTemplate: string | ((ctx: PromptContext) => string);  // 支持 model-specific 动态生成
  metadata: AgentPromptMetadata;
  color?: string;
}

interface AgentPromptMetadata {
  cost: "FREE" | "CHEAP" | "EXPENSIVE";
  category: "orchestration" | "specialist" | "exploration" | "planning" | "review";
  triggers: Array<{ domain: string; description: string }>;
  useWhen: string[];
  avoidWhen: string[];
  keyTrigger?: string;  // 出现在 Sisyphus 的 Key Triggers 区域
}

interface FallbackEntry {
  providers: string[];   // e.g. ["openai", "github-copilot"]
  model: string;         // e.g. "gpt-5.5"
  variant?: string;
  reasoningEffort?: string;
  thinking?: { type: "enabled" | "disabled"; budgetTokens?: number };
}
```

#### 4.1.2 完整 Agent 清单

| Agent | Role | Primary Model | Fallbacks | Thinking | maxTokens | Tool Policy | Cost |
|-------|------|--------------|-----------|----------|-----------|-------------|------|
| sisyphus | orchestrator | claude-opus-4-7 | kimi-k2.5 → gpt-5.5 → glm-5 | high (32K budget) | 64000 | full | EXPENSIVE |
| oracle | advisor | gpt-5.5 | gemini-3.1-pro → claude-opus-4-7 → glm-5 | high | 32000 | read-only | EXPENSIVE |
| hephaestus | deep-worker | gpt-5.5 | claude-sonnet-4-6 | medium | 32000 | full (无 call_omo_agent) | EXPENSIVE |
| prometheus | planner | claude-opus-4-7 | gpt-5.5 → glm-5 → gemini-3.1-pro | high | 64000 | read-only + .md write | EXPENSIVE |
| explore | grep | gpt-5.4-mini-fast | minimax → claude-haiku → gpt-5.4-nano | off | 16000 | search-only + LSP | FREE |
| librarian | reference | gpt-5.4-mini-fast | minimax → claude-haiku → gpt-5.4-nano | off | 16000 | search-only | CHEAP |
| metis | plan-consultant | claude-opus-4-7 | gpt-5.5 → glm-5 | high | 32000 | read-only | EXPENSIVE |
| momus | plan-reviewer | gpt-5.5 | claude-opus-4-7 → gemini-3.1-pro → glm-5 | xhigh | 32000 | read-only | EXPENSIVE |
| atlas | conductor | claude-sonnet-4-6 | kimi-k2.5 → gpt-5.5 → minimax | medium | 64000 | full | EXPENSIVE |
| sisyphus-junior | executor | claude-sonnet-4-6 | kimi-k2.5 → gpt-5.5 → minimax | medium (32K) | 64000 | full (无 task) | — |
| multimodal-looker | vision | gpt-5.5 | claude-opus-4-7 | medium | 16000 | read-only | EXPENSIVE |

#### 4.1.3 Tool Policy 实现

通过 openclaw 的 `before_tool_call` hook 拦截：

```typescript
// Tool Policy 映射
const TOOL_POLICIES = {
  "full": { deny: [] },
  "read-only": { deny: ["write", "edit", "apply_patch", "task"] },
  "search-only": {
    deny: ["write", "edit", "apply_patch", "task", "call_omo_agent"],
    allow: ["lsp_symbols", "lsp_goto_definition", "lsp_find_references",
            "lsp_diagnostics", "ast_grep_search", "grep", "glob"]
  },
};

// GPT 模型额外限制
function getModelSpecificDeny(modelId: string): string[] {
  if (isGptModel(modelId)) return ["apply_patch"];  // GPT 不擅长 apply_patch
  return [];
}
```

#### 4.1.4 Dynamic Prompt Builder

模块化 prompt 组装系统，根据当前可用的 agents/tools/skills/categories 动态生成 prompt：

```typescript
// agents/prompt-builder/core-sections.ts

// 输入类型
interface PromptContext {
  agents: AvailableAgent[];      // 当前注册的 agents
  tools: AvailableTool[];        // 当前注册的 tools (分类: lsp/ast/search/session/command/other)
  skills: AvailableSkill[];      // 当前可用的 skills (标记 user/project/plugin 来源)
  categories: AvailableCategory[]; // 当前可用的 categories
  modelId: string;               // 当前模型 (用于 model-specific 变体选择)
  providerId: string;
}

// 组装流程 (以 Sisyphus 为例)
function buildSisyphusPrompt(ctx: PromptContext): string {
  const sections = [
    buildAgentIdentitySection("Sisyphus", "Powerful AI Agent with orchestration capabilities"),
    buildRoleSection(),                              // 身份 + 核心能力 + 运行模式
    buildBehaviorInstructions([
      buildIntentGateSection(),                      // Phase 0: 意图分类 (6 种)
      buildKeyTriggersSection(ctx.agents, ctx.skills), // 动态: 从 agent metadata 提取
      buildCodebaseAssessmentSection(),              // Phase 1: 代码库评估
      buildExplorationSection([
        buildToolSelectionTable(ctx.agents, ctx.tools, ctx.skills), // 动态: cost-sorted
        buildExploreSection(ctx.agents),             // 动态: 从 explore agent metadata
        buildLibrarianSection(ctx.agents),           // 动态: 从 librarian agent metadata
        buildAntiDuplicationSection(),
      ]),
      buildImplementationSection([
        buildCategorySkillsDelegationGuide(ctx.categories, ctx.skills), // 动态
        buildDelegationTable(ctx.agents),            // 动态: 从 agent triggers
      ]),
      buildFailureRecoverySection(),                 // Phase 2C
      buildCompletionSection(),                      // Phase 3
    ]),
    buildOracleSection(ctx.agents),                  // 动态: Oracle 使用指南
    buildTaskManagementSection(),
    buildToneAndStyleSection(),
    buildConstraintsSection([
      buildHardBlocksSection(),
      buildAntiPatternsSection(),
    ]),
  ];
  return sections.join("\n");
}
```

#### 4.1.5 Model-Specific Prompt 变体

每个 agent 支持多个 prompt 变体，根据实际使用的模型自动选择：

```typescript
// 检测模型家族
function resolvePromptVariant(modelId: string): "claude" | "gpt" | "gpt-5-5" | "gemini" {
  if (isGpt55Model(modelId)) return "gpt-5-5";
  if (isGptModel(modelId)) return "gpt";
  if (isGeminiModel(modelId)) return "gemini";
  return "claude";  // default
}

// Sisyphus 变体差异:
// - Claude (default): 完整 5-phase 系统 + extended thinking (32K budget)
// - GPT: reasoningEffort: "medium", 无 thinking, 简化 phase 系统
// - GPT-5.5: 更详细的 tool call 格式指导
// - Gemini: 在 default 基础上注入 overlay (intent gate enforcement, tool mandate, tool guide, delegation override)

// Oracle 变体差异:
// - Claude: XML-tagged sections, extended thinking
// - GPT: "approach-first mentality", prose-first output
// - GPT-5.5: confidence tagging (high/medium/low), 400-line hard cap
```

#### 4.1.6 Prometheus 规划者详细设计

Prometheus 是最复杂的 agent，由 6 个子模块组成：

```
PROMETHEUS_SYSTEM_PROMPT =
  IDENTITY_CONSTRAINTS      // "YOU ARE A PLANNER. NOT AN IMPLEMENTER."
  + INTERVIEW_MODE           // 7 种意图类型 × 研究策略
  + PLAN_GENERATION          // Metis 咨询 + gap 分类 + 增量写入
  + HIGH_ACCURACY_MODE       // Momus 审查循环直到 OKAY
  + PLAN_TEMPLATE            // .sisyphus/plans/*.md 格式
  + BEHAVIORAL_SUMMARY
```

**Interview Mode — 7 种意图类型:**

| 意图类型 | 研究策略 | 访谈焦点 |
|---------|---------|---------|
| Trivial/Simple | 快速 Tiki-Taka | 快速确认 |
| Refactoring | 安全优先 (行为保持, 测试覆盖) | 边界条件 |
| Build from Scratch | 先 explore 再问用户 | 发现模式 |
| Mid-sized Task | 边界聚焦 (精确输出, 显式排除) | 范围界定 |
| Collaborative | 对话聚焦 (增量清晰) | 渐进式 |
| Architecture | 战略聚焦 (强制 Oracle 咨询) | 系统级 |
| Research | 调查聚焦 (并行探测, 退出标准) | 证据收集 |

**High Accuracy Mode — Momus 审查循环:**
```
while (true) {
  result = task(subagent_type="momus", prompt=".sisyphus/plans/{name}.md")
  if (result.verdict === "OKAY") break;
  // 修复所有问题，重新提交。无最大重试限制。
}
// OKAY 标准: 100% 文件引用已验证, ≥80% 任务有参考来源,
// ≥90% 有具体验收标准, 零业务逻辑假设, 零关键红旗
```

### 4.2 Category 路由系统 (P0)

#### 4.2.1 内置分类定义

8 个内置分类，按 provider 分组定义 (支持不同 provider 的最优模型)：

```typescript
// categories/builtin/anthropic.ts
const ANTHROPIC_CATEGORIES = {
  "unspecified-low":  { model: "claude-sonnet-4-6", thinking: "medium" },
  "unspecified-high": { model: "claude-opus-4-7", thinking: "high", variant: "max" },
};

// categories/builtin/openai.ts
const OPENAI_CATEGORIES = {
  "ultrabrain": { model: "gpt-5.5", thinking: "xhigh" },
  "deep":       { model: "gpt-5.5", thinking: "medium" },
  "quick":      { model: "gpt-5.4-mini", thinking: "low" },
};

// categories/builtin/google.ts
const GOOGLE_CATEGORIES = {
  "visual-engineering": { model: "gemini-3.1-pro", thinking: "high" },
  "artistry":           { model: "gemini-3.1-pro", thinking: "high" },
  "writing":            { model: "gemini-3-flash", thinking: "off" },
};
```

| Category | 领域 | 默认模型 | Thinking | 典型用途 |
|----------|------|---------|----------|---------|
| visual-engineering | 前端/UI/UX | gemini-3.1-pro | high | CSS, 组件设计, 动画 |
| ultrabrain | 硬逻辑/算法 | gpt-5.5 | xhigh | 架构决策, 复杂算法 |
| deep | 自主研究+实现 | gpt-5.5 | medium | 端到端功能开发 |
| artistry | 创意/非常规 | gemini-3.1-pro | high | 创造性问题解决 |
| quick | 琐碎修改 | gpt-5.4-mini | low | 单文件修改, typo |
| writing | 文档/散文 | gemini-3-flash | off | README, 技术文档 |
| unspecified-low | 通用低复杂度 | claude-sonnet-4-6 | medium | 不匹配其他分类的简单任务 |
| unspecified-high | 通用高复杂度 | claude-opus-4-7 | high | 不匹配其他分类的复杂任务 |

#### 4.2.2 Category → Model Resolution Pipeline

```typescript
// categories/router.ts — 静态解析 (与 OmO 一致)
function resolveCategoryExecution(
  category: string,
  config: PluginConfig,
  connectedProviders: Set<string>
): ResolvedCategory {
  // 优先级链:
  // 1. 用户 config 覆盖: config.categories[category].model
  // 2. Category 默认模型: BUILTIN_CATEGORIES[category].model
  // 3. 用户 fallback_models: config.categories[category].fallback_models
  // 4. 内置 FallbackEntry[] chain (per-category, per-provider)
  // 5. 系统默认模型
  // 6. Connected providers cache (冷启动优化)

  // 每一步都检查 provider 可达性:
  // - 从 connectedProviders 缓存中验证
  // - 跳过 no-op (同 provider+model, canonicalized: lowercase, dots→dashes)
}

// Unstable agent 检测:
// 如果 category 解析到 gemini/minimax 模型 → is_unstable_agent = true
// → 强制 background 模式 (即使用户请求 sync)
```

#### 4.2.3 ContextAwareRouter — 动态增强层 (P2)

> 静态 pipeline 不考虑运行时上下文。ContextAwareRouter 包装静态 pipeline，注入来自 context engine、memory 和 runtime metrics 的信号。

```typescript
// categories/context-aware-router.ts
class ContextAwareRouter {
  constructor(
    private staticRouter: typeof resolveCategoryExecution,
    private memory: MemoryAPI,
    private contextEngine: ContextEngineAPI,
    private metrics: MetricsCollector,
  ) {}

  async resolve(category: string, config: PluginConfig, providers: Set<string>): Promise<ResolvedCategory> {
    // 1. 静态解析 (baseline)
    const baseline = this.staticRouter(category, config, providers);

    // 2. Context window 感知
    //    如果当前 session 已用 >70% context → 优先选择大 context 模型
    const contextUsage = await this.contextEngine.getUsageRatio();
    if (contextUsage > 0.7 && baseline.model !== largeContextModel) {
      // 考虑切换到更大 context 的模型
    }

    // 3. 历史成功率 (from memory)
    //    查询最近 50 次该 category 的执行结果
    //    如果某模型连续失败 3 次 → 降低优先级
    const outcomes = await this.memory.query({
      tags: ["omc-category-outcome"],
      filter: { category },
      limit: 50,
    });
    const modelFailures = countConsecutiveFailures(outcomes, baseline.model);
    if (modelFailures >= 3) {
      // 跳到 fallback chain 的下一个
    }

    // 4. 用户偏好 (from memory)
    //    如果用户曾说 "不要用 Gemini" → 排除 Gemini 模型
    const preferences = await this.memory.query({
      tags: ["omc-user-preference"],
      limit: 10,
    });
    // 应用偏好过滤

    // 5. 通道约束
    //    Discord 消息长度限制 → 可能影响模型选择 (偏好简洁输出的模型)

    return adjustedResult;
  }
}
```

#### 4.2.3 delegate-task 工具 Schema

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

**执行流程:**

```
用户/Sisyphus 调用 task(category="deep", skills=["tdd-workflow"], prompt="...")
  │
  ├─ 1. resolveCategoryExecution("deep") → { model: "gpt-5.5", thinking: "medium" }
  ├─ 2. buildSystemContent(skills, categoryPromptAppend) → 组装 subagent prompt
  ├─ 3. 检查 unstable agent → 如果是, 强制 background
  │
  ├─ [sync mode] ──────────────────────────────────────────────
  │   ├─ reserveSubagentSpawn() → depth guard (max 3)
  │   ├─ 创建 openclaw session (via subagent spawn API)
  │   ├─ 发送 prompt (with resolved model/thinking/tools)
  │   ├─ syncSessionPoller → 轮询直到 session.idle
  │   ├─ 获取结果 → 返回给调用者
  │   └─ 失败 → tryFallbackRetry() → 用 fallback model 重试
  │
  └─ [background mode] ────────────────────────────────────────
      ├─ backgroundManager.launch(config) → 返回 task_id
      ├─ 等待 30s 确认 session 创建
      ├─ 注册 fallback chain + category 到 session
      └─ 调用者通过 background_output(task_id) 获取结果
```

### 4.3 Background Agent 并行执行 (P0)

#### 4.3.1 设计原则: 薄增强层而非平行系统

> **关键决策**: BackgroundManager 是 openclaw subagent API 的薄增强层，不是平行的任务管理系统。openclaw 的 session 跟踪是唯一的 source of truth。

```typescript
// background/manager.ts
class BackgroundManager {
  // ❌ 不维护独立的 task 状态 (避免双重状态漂移)
  // ✅ 仅维护增强层元数据
  private enhancements: Map<string, TaskEnhancement> = new Map();
  // TaskEnhancement = { concurrencyKey, circuitBreaker, fallbackChain, parentSessionId, createdAt }

  private concurrency: ConcurrencyManager;
  private loopDetector: LoopDetector;

  // 核心: 包装 openclaw 的 subagent spawn API
  async launch(input: LaunchInput): Promise<string> {
    // 1. 并发控制: concurrency.acquire(key)
    // 2. 深度检查: 通过 openclaw session API 查询 parent chain
    // 3. 调用 openclaw: api.runtime.spawnSubagent(params)
    // 4. 注册增强元数据
    // 5. 返回 openclaw 的 childSessionKey 作为 taskId
    return childSessionKey;
  }

  // 状态查询: 委托给 openclaw session API
  async getTaskStatus(taskId: string): Promise<TaskStatus> {
    const session = await api.runtime.getSession(taskId);
    return mapSessionToTaskStatus(session);
  }
}
```

#### 4.3.2 ConcurrencyManager

```typescript
// background/concurrency.ts
class ConcurrencyManager {
  // 按 "provider/model" 或 agent name 分组
  // 默认并发: 5 (0 = unlimited)
  // Promise-based queue: acquire() 返回 Promise, 在有空位时 resolve
  // settled-flag pattern 防止 double-resolution

  getConcurrencyLimit(key: string): number {
    // model-specific → provider-specific → default → 5
  }

  async acquire(key: string): Promise<void> {
    // 如果当前 running < limit → 立即 resolve
    // 否则 → 入队等待
  }

  release(key: string): void {
    // running-- → 从队列中 dequeue 下一个 → resolve
  }
}
```

#### 4.3.3 Circuit Breaker (Loop Detector)

```typescript
// background/loop-detector.ts
class LoopDetector {
  // 跟踪每个 session 的 tool call 窗口
  // signature = "toolName::JSON.stringify(sortedInput)"
  // 连续相同 signature >= threshold (20) → 触发熔断
  // 绝对上限: maxToolCalls (4000) → 触发熔断
  // 熔断动作: cancelTask(source="circuit-breaker")

  detectRepetitiveToolUse(sessionId: string, toolName: string, input: unknown): boolean;
}
```

#### 4.3.4 父 Session 通知系统

```typescript
// background/notification.ts
// 当 background task 完成时:
// 1. markForNotification(taskId) → 加入 pendingByParent Map
// 2. notifyParentSession() → 批量生成 <system-reminder>:
//
//    <system-reminder>
//    [BACKGROUND TASK COMPLETED]
//    **ID:** `bg_abc123`
//    **Description:** Find auth implementations
//    **Duration:** 1m 20s
//
//    **2 tasks still in progress.**
//    Use `background_output(task_id="bg_abc123")` to retrieve this result.
//    </system-reminder>
//
// 3. 注入到父 session 的下一条 chat message 中
```

#### 4.3.5 background_output / background_cancel 工具

```typescript
// background_output schema
{
  task_id: string,              // REQUIRED
  block?: boolean,              // 等待完成 (default: false)
  timeout?: number,             // 最大等待 ms (default: 60000, max: 600000)
  full_session?: boolean,       // 返回完整 session messages
  include_thinking?: boolean,   // 包含推理过程
  include_tool_results?: boolean,
  message_limit?: number,       // 最多 100 条
  since_message_id?: string,    // 增量获取
  thinking_max_chars?: number,  // 推理内容截断 (default: 2000)
}

// background_cancel schema
{
  taskId?: string,   // 取消指定 task
  all?: boolean,     // 取消所有 (default: false) — 获取所有后代 task, 逐个取消
}
```

### 4.4 Hook 系统详细设计

#### 4.4.1 Ralph Loop — 自驱动完成循环 (P1)

**挂载 Hook:** `agent_end` (session.idle 事件)

**状态机:**
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
// 持久化: .sisyphus/ralph-loop.local.md
```

**完成检测 (双路径):**
1. Transcript 文件扫描: 读取 JSONL transcript → 解析每行 → 正则 `<promise>\s*DONE\s*</promise>`
2. Session Messages API: 查询 session messages → 逆序扫描 assistant parts

**迭代流程:**
```
session.idle 事件
  │
  ├─ 检查: loop active? session 匹配? recovery 中? in-flight?
  ├─ 检测完成 (transcript → API fallback)
  │
  ├─ [已完成]
  │   ├─ [standard] → 清理状态, 显示成功 toast
  │   └─ [ultrawork] → 转入验证阶段:
  │       ├─ verification_pending = true
  │       ├─ completion_promise = "VERIFIED"
  │       └─ 注入验证 prompt: "Call Oracle to verify..."
  │
  ├─ [验证中 (ultrawork)]
  │   ├─ 扫描 Oracle tool_result 中的 <promise>VERIFIED</promise>
  │   ├─ [已验证] → 清理状态, 成功
  │   └─ [未验证] → 注入 "Oracle did not verify. Fix and retry."
  │
  ├─ [达到 max_iterations] → 停止, 警告 toast
  │
  └─ [未完成] → iteration++ → 注入续跑 prompt:
      "Your previous attempt did not output the completion promise.
       Continue working... When FULLY complete, output:
       <promise>DONE</promise>"
```

**Strategy 模式:**
- `"continue"` (默认): 在同一 session 注入续跑 prompt
- `"reset"`: 创建新 session，继承 agent/model/tools，在 TUI 中选中

#### 4.4.2 Todo Continuation Enforcer (P1)

**挂载 Hook:** `agent_end` (session.idle 事件)

**检测 + 注入流程:**
```
session.idle 事件
  │
  ├─ Guards: recovery? cancelled? token limit? abort window (3s)?
  │          background tasks running? in-flight injection?
  │          skip agents (prometheus/compaction/plan)?
  │          non-write-permission agent?
  │
  ├─ 获取 session messages → 检查 last assistant (aborted? pending question?)
  ├─ 获取 todos → 计算 incomplete count
  │
  ├─ [incomplete > 0]
  │   ├─ 停滞检测: 连续 3 次 incomplete 不减少 → 停止
  │   ├─ 连续失败: 5 次 → 停止 (指数退避 cooldown: 5s × 2^min(failures,5))
  │   ├─ Compaction guard: compaction 后 60s 内跳过
  │   │
  │   ├─ 2s 倒计时 (每秒 toast: "Resuming in Ns... (X tasks remaining)")
  │   │
  │   └─ 注入续跑 prompt:
  │       "[SYSTEM_DIRECTIVE: TODO_CONTINUATION]
  │        Incomplete tasks remain. Continue working.
  │        - Proceed without asking for permission
  │        - Mark each task complete when finished
  │        - Do not stop until all tasks are done
  │        [Status: X/Y completed, Z remaining]
  │        Remaining tasks:
  │        - [status] task content"
  │
  └─ [incomplete == 0] → 无操作
```

#### 4.4.3 Model Fallback Chain (P1)

**双层架构:**

**Layer 1 — Agent-Aware Fallback (pre-request):**
- 挂载: `before_model_resolve` hook
- 触发: 其他 hook (session.error) 设置 pending fallback flag
- 逻辑: 从 agent 的 fallbackChain 中选择下一个可达模型
- 可达性检查: connected providers cache
- No-op 跳过: canonicalize(provider+model) 相同则跳过

**Layer 2 — Runtime Fallback (error-triggered):**
- 挂载: `llm_output` + `session_end` hooks
- 触发: HTTP 错误 (429/500/502/503/504)
- 逻辑: abort session → 用 fallback model 重发 last user message
- 状态: `FallbackState { originalModel, currentModel, fallbackIndex, failedModels, attemptCount }`
- Cooldown: 60s per failed model
- 最大尝试: 3 次
- Timeout: 30s per fallback attempt

```typescript
// 错误分类
const RETRYABLE_PATTERNS = [
  "rate_limit", "too_many_requests", "quota_exceeded",
  "exhausted_capacity", "service_unavailable", "overloaded",
  "temporarily_unavailable", "try_again", "429", "503", "529"
];

// Fallback model 解析优先级:
// 1. Session category → config.categories[category].fallback_models
// 2. Agent config → config.agents[agent].fallback_models
// 3. Agent's category → config.categories[agentCategory].fallback_models
```

#### 4.4.4 Session Recovery (P1)

**挂载 Hook:** `llm_output` + `after_tool_call`

**5 种错误模式 + 恢复策略:**

| 错误类型 | 检测模式 | 恢复策略 |
|---------|---------|---------|
| `tool_result_missing` | message 含 "tool_use" + "tool_result" | 提取所有 tool_use parts → 注入 synthetic error result: `{"status":"error","error":"Tool crashed or was interrupted..."}` |
| `unavailable_tool` | "dummy_tool", "unavailable tool", "no such tool" | 提取工具名 → 注入 `{"status":"error","error":"Tool not available. Continue without this tool."}` |
| `thinking_block_order` | "thinking" + ("first block" \| "must start with") | 重排/修复 thinking blocks → auto-resume |
| `thinking_disabled_violation` | "thinking is disabled" + "cannot contain" | 剥离所有 thinking/redacted_thinking/reasoning parts → auto-resume |
| `assistant_prefill_unsupported` | "assistant message prefill" | 无恢复 (返回 false) |

**恢复流程:**
```
错误检测 → 去重 (processingErrors Set, keyed by message ID)
  → abort session → 获取 messages → 显示 toast
  → 运行特定 handler → auto-resume (如果配置启用)
```

#### 4.4.5 Preemptive Compaction (P2)

**挂载 Hook:** `after_tool_call`

```typescript
// 阈值: 78% context window
const THRESHOLD = 0.78;
const COOLDOWN_MS = 60_000;  // 60s between compactions
const TIMEOUT_MS = 60_000;   // 60s compaction timeout

// Token 缓存: 每次 assistant 完成时更新
// usageRatio = (input_tokens + cache_read_tokens) / actualContextLimit
// 如果 usageRatio >= 0.78 → 触发 session.summarize()
```

#### 4.4.6 Comment Checker (P2)

**挂载 Hook:** `before_tool_call` + `after_tool_call`

```
before_tool_call (write/edit/multiedit/apply_patch)
  → 注册 PendingCall { callID, filePath, content, oldString, newString }

after_tool_call
  → 取出 PendingCall → 跳过失败的 tool output
  → 调用外部 binary: comment-checker check [--prompt custom]
  → stdin: JSON { session_id, tool_name, file_path, content, ... }
  → exit 0: 无问题 | exit 2: 检测到 AI slop (stderr 含警告)
  → 将警告追加到 tool output → agent 看到后自动修复
  → 并发锁: withCommentCheckerLock() 防止并行运行
  → timeout: 30s (SIGTERM → 1s → SIGKILL)
```

#### 4.4.7 Keyword Detector (P3)

**挂载 Hook:** `message_received` (chat.message)

**3 种模式:**

| 模式 | 触发正则 | 注入内容 |
|------|---------|---------|
| ultrawork | `/\b(ultrawork\|ulw)\b/i` | 完整 ultrawork prompt (model-specific: Claude/GPT/GPT-5.5/Gemini 4 种变体) |
| search | 多语言: search/find/locate/grep/검색/探して/搜索/tìm kiếm... | `"[search-mode] MAXIMIZE SEARCH EFFORT. Launch multiple background agents IN PARALLEL..."` |
| analyze | 多语言: analyze/investigate/debug/분석/調査/调查/phân tích... | `"[analyze-mode] ANALYSIS MODE. Gather context before diving deep..."` |

**注入方式:** prepend 到首个 text part: `{messages}\n\n---\n\n{originalText}`

### 4.5 工具系统详细设计

#### 4.5.1 LSP 工具集 (P1)

**3 层 Client 架构:**

```
LSPClientTransport (base)
  ├─ 启动 LSP server 进程 (stdin/stdout)
  ├─ 创建 vscode-jsonrpc MessageConnection
  ├─ 处理 publishDiagnostics 通知
  └─ 15s 请求超时, SIGKILL 优雅关闭

LSPClientConnection (extends Transport)
  ├─ initialize() 握手 (声明完整 capabilities)
  └─ initialized + didChangeConfiguration 通知

LSPClient (extends Connection)
  ├─ openFile() / definition() / references()
  ├─ documentSymbols() / workspaceSymbols()
  ├─ diagnostics() / prepareRename() / rename()
  └─ 行号转换: 1-based input → 0-based LSP protocol
```

**LSPServerManager (单例):**
- Key: `${workspaceRoot}::${serverId}`
- 引用计数 (`refCount`) 共享 client
- Idle timeout: 5 min → 自动停止
- Init timeout: 60s → 清理 stale init
- Warmup: `warmupClient()` with refCount=0
- 35+ 内置 server 定义 (TypeScript, Go, Python, Rust, Java, C/C++, Vue, ESLint, Biome...)

**6 个工具 Schema:**

| 工具 | 参数 | 说明 |
|------|------|------|
| `lsp_goto_definition` | filePath, line(1-based), character(0-based) | 跳转到定义 |
| `lsp_find_references` | filePath, line, character, includeDeclaration? | 查找所有引用 |
| `lsp_symbols` | filePath, scope("document"\|"workspace"), query?, limit? | 符号搜索 |
| `lsp_diagnostics` | filePath, severity?("error"\|"warning"\|"all") | 获取诊断 (支持目录) |
| `lsp_prepare_rename` | filePath, line, character | 检查重命名可行性 |
| `lsp_rename` | filePath, line, character, newName | 跨文件重命名 |

#### 4.5.2 AST-Grep 工具 (P1)

```typescript
// ast_grep_search
{
  pattern: string,      // AST pattern: $VAR (单节点), $$$ (多节点)
  lang: CliLanguage,    // 25 种语言
  paths?: string[],     // 默认: [ctx.directory]
  globs?: string[],     // 包含/排除 (! 前缀排除)
  context?: number,     // 匹配周围的上下文行数
}

// ast_grep_replace
{
  pattern: string,      // 匹配 pattern
  rewrite: string,      // 替换 pattern (可用 $VAR)
  lang: CliLanguage,
  paths?: string[],
  globs?: string[],
  dryRun?: boolean,     // 默认: true (仅预览)
}

// 底层: sg CLI (auto-download binary)
// replace 需两遍: JSON 收集 + 写入 (因为 --json 和 --update-all 互斥)
// 空结果提示: "Remove trailing colon" (Python), "Function patterns need params and body" (JS/TS)
```

#### 4.5.3 Hashline Edit 工具 (P2)

**LINE#ID 哈希算法:**
```typescript
// Dictionary: 16-char nibble string "ZPMQVRWSNKTXJBYH" → 256 个 2-char code
// computeLineHash(lineNumber, content):
//   1. normalize: strip \r, trimEnd()
//   2. seed: 0 (if has significant chars \p{L}\p{N}), else lineNumber
//   3. hash: xxHash32(stripped, seed) % 256
//   4. lookup: HASHLINE_DICT[index] → 2-char code
// 输出: "42#VR|  const x = 1"
// 引用: "42#VR"
```

**编辑执行 Pipeline:**
```
normalizeEdits → dedupeEdits → sort (bottom-up, by precedence)
  → collectLineRefs → validateLineRefs (hash 对比当前文件)
  → detectOverlappingRanges → apply operations
  → canonicalizeFileText → write → runFormattersForFile (LSP)
  → publish diff metadata
```

---

## 5. 配置系统

### 5.1 配置文件格式

```jsonc
// oh-my-claw.json (项目级) 或 ~/.openclaw/oh-my-claw.json (用户级)
// 支持 JSON5 (与 openclaw 一致)
// Zod schema 校验
```

### 5.2 完整配置 Schema

```typescript
// config/schema.ts
const OhMyClawConfigSchema = z.object({
  $schema: z.string().optional(),

  // ── Agent 覆盖 ──
  agents: z.record(AgentNameSchema, AgentOverrideSchema).optional(),
  // AgentOverrideSchema 支持:
  //   model, variant, fallback_models, category
  //   skills (注入 skill 名), temperature (0-2), top_p (0-1)
  //   prompt (完整替换, 支持 file:// URI), prompt_append (追加)
  //   tools (record<toolName, boolean>)
  //   disable, description, mode ("subagent"|"primary"|"all")
  //   color (hex), maxTokens
  //   thinking ({type: "enabled"|"disabled", budgetTokens?})
  //   reasoningEffort ("none"|"minimal"|"low"|"medium"|"high"|"xhigh")
  //   permission ({edit/bash/webfetch/task/doom_loop: "ask"|"allow"|"deny"})
  //   ultrawork ({model?, variant?}), compaction ({model?, variant?})

  // ── Category 自定义 ──
  categories: z.record(z.string(), CategoryConfigSchema).optional(),
  // CategoryConfigSchema 支持:
  //   description, model, fallback_models, variant
  //   temperature, top_p, maxTokens
  //   thinking, reasoningEffort, textVerbosity
  //   tools, prompt_append, max_prompt_tokens
  //   is_unstable_agent, disable

  // ── 开关 ──
  disabled_agents: z.array(z.string()).optional(),
  disabled_skills: z.array(z.string()).optional(),
  disabled_hooks: z.array(z.string()).optional(),
  disabled_commands: z.array(z.string()).optional(),
  disabled_tools: z.array(z.string()).optional(),
  disabled_mcps: z.array(z.string()).optional(),

  // ── Hook 配置 ──
  ralph_loop: z.object({
    enabled: z.boolean().default(false),
    default_max_iterations: z.number().min(1).max(1000).default(100),
    default_strategy: z.enum(["reset", "continue"]).default("continue"),
    state_dir: z.string().optional(),
  }).optional(),

  runtime_fallback: z.union([
    z.boolean(),
    z.object({
      enabled: z.boolean(),
      retry_on_errors: z.array(z.number()).default([429, 500, 502, 503, 504]),
      max_fallback_attempts: z.number().min(1).max(20).default(3),
      cooldown_seconds: z.number().default(60),
      timeout_seconds: z.number().default(30),
      notify_on_fallback: z.boolean().default(true),
    }),
  ]).optional(),

  model_fallback: z.boolean().optional(),

  comment_checker: z.object({
    custom_prompt: z.string().optional(),  // 支持 {{comments}} 占位符
  }).optional(),

  // ── Background Agent ──
  background_task: z.object({
    defaultConcurrency: z.number().default(5),
    providerConcurrency: z.record(z.string(), z.number()).optional(),
    modelConcurrency: z.record(z.string(), z.number()).optional(),
    maxDepth: z.number().default(3),
    staleTimeoutMs: z.number().default(2_700_000),
    taskTtlMs: z.number().default(1_800_000),
    maxToolCalls: z.number().default(4000),
    circuitBreaker: z.object({
      enabled: z.boolean().default(true),
      consecutiveThreshold: z.number().default(20),
    }).optional(),
  }).optional(),

  // ── Skill 配置 ──
  skills: z.union([
    z.array(z.string()),  // 简单启用列表
    z.object({
      sources: z.array(z.union([
        z.string(),
        z.object({ path: z.string(), recursive: z.boolean().optional(), glob: z.string().optional() }),
      ])).optional(),
      enable: z.array(z.string()).optional(),
      disable: z.array(z.string()).optional(),
    }),
  ]).optional(),

  // ── MCP 配置 ──
  mcp: z.object({
    websearch: z.object({ enabled: z.boolean().default(true) }).optional(),
    context7: z.object({ enabled: z.boolean().default(true) }).optional(),
    grep_app: z.object({ enabled: z.boolean().default(true) }).optional(),
  }).optional(),

  // ── 工具配置 ──
  tools: z.object({
    lsp: z.object({ enabled: z.boolean().default(true) }).optional(),
    ast_grep: z.object({ enabled: z.boolean().default(true) }).optional(),
    hashline_edit: z.object({ enabled: z.boolean().default(false) }).optional(),
  }).optional(),

  // ── Tmux 配置 ──
  tmux: z.object({
    enabled: z.boolean().default(false),
    layout: z.enum(["main-horizontal", "main-vertical", "tiled"]).default("main-vertical"),
    main_pane_size: z.number().min(20).max(80).default(60),
    isolation: z.enum(["inline", "window", "session"]).default("inline"),
  }).optional(),

  // ── 实验性功能 ──
  experimental: z.object({
    preemptive_compaction: z.boolean().default(false),
    aggressive_truncation: z.boolean().default(false),
    dynamic_context_pruning: z.object({
      deduplication: z.boolean().optional(),
      supersede_writes: z.boolean().optional(),
      purge_errors: z.boolean().optional(),
    }).optional(),
    max_tools: z.number().optional(),
    team_mode: z.boolean().default(false),
    interactive_bash: z.boolean().default(false),
  }).optional(),

  // ── 通知 ──
  notification: z.object({
    force_enable: z.boolean().default(false),
  }).optional(),

  // ── Websearch Provider ──
  websearch: z.object({
    provider: z.enum(["exa", "tavily"]).default("exa"),
  }).optional(),

  // ── Git Master ──
  git_master: z.object({
    commit_footer: z.boolean().default(true),
    include_co_authored_by: z.boolean().default(true),
    git_env_prefix: z.string().default("GIT_MASTER=1"),
  }).optional(),

  // ── Start Work ──
  start_work: z.object({
    auto_commit: z.boolean().default(true),
  }).optional(),

  // ── Browser Automation ──
  browser_automation_engine: z.object({
    provider: z.enum(["playwright", "agent-browser", "dev-browser"]).default("playwright"),
  }).optional(),
});
```

### 5.3 多级配置合并

```
优先级: 项目级 (./.oh-my-claw.json) > 用户级 (~/.openclaw/oh-my-claw.json) > 默认值
合并策略: deep merge (对象递归合并, 数组替换)
```

---

## 6. 内置 Slash 命令

### 6.1 命令清单

| 命令 | 说明 | 实现要点 |
|------|------|---------|
| `/ralph-loop` | 启动自驱动完成循环 | 初始化 RalphLoopState，设置 completion_promise="DONE"，激活 hook |
| `/ulw-loop` | Ultrawork 循环 (含 Oracle 验证) | 同上 + ultrawork=true, max_iterations=500, 需 Oracle `<promise>VERIFIED</promise>` |
| `/cancel-ralph` | 取消活跃的 Ralph Loop | 清理状态文件，停止 hook |
| `/refactor` | 智能重构 (LSP + AST-grep + TDD) | 6 阶段: Intent gate → Codebase analysis (5 parallel explore) → Codemap → Test assessment → Plan → Deterministic execution with continuous verification |
| `/start-work` | 从 Prometheus 计划启动工作 | 读取 `.sisyphus/plans/`，管理 `boulder.json` 状态，支持 git worktree，强制任务分解 |
| `/stop-continuation` | 停止所有续跑机制 | 停止 todo-continuation + ralph loop + boulder state |
| `/init-deep` | 生成层级化 AGENTS.md | 4 阶段: Discovery (parallel explore + LSP) → Score directories → Generate files → Review/deduplicate |
| `/handoff` | 创建 session 上下文摘要 | 4 阶段: Gather context (session_read, todoread, git) → Extract → Format → Provide instructions |
| `/remove-ai-slops` | 清除分支中的 AI 代码异味 | 4 阶段: Identify changed files → Parallel ai-slop-remover per file → Critical review → Fix |

### 6.2 /refactor 命令详细流程

```
Phase 1: Intent Gate
  → 分类: rename / extract / move / inline / restructure / signature-change / pattern-replace

Phase 2: Codebase Analysis (5 parallel explore agents)
  → Agent 1: 目标代码结构
  → Agent 2: 依赖关系图
  → Agent 3: 测试覆盖
  → Agent 4: 类型系统约束
  → Agent 5: 相关配置/构建文件

Phase 3: Codemap Generation
  → LSP symbols + AST-grep patterns → 生成影响范围图

Phase 4: Test Assessment
  → 现有测试覆盖率 → 需要新增的测试 → TDD 计划

Phase 5: Plan Generation
  → 原子步骤列表 → 每步的验证标准 → 回滚策略

Phase 6: Deterministic Execution
  → 按计划逐步执行 → 每步后 lsp_diagnostics 验证
  → 失败 → 回滚到上一步 → 重试或报告
```

---

## 7. 内置 Skill 系统

### 7.1 Skill 定义格式

```typescript
interface BuiltinSkill {
  name: string;
  description: string;
  template: string;           // 注入 agent context 的 prompt 模板
  license?: string;
  compatibility?: string;
  metadata?: Record<string, unknown>;
  allowedTools?: string[];    // 限制 skill 可用的工具
  agent?: string;             // 绑定到特定 agent
  model?: string;             // 推荐模型
  subtask?: boolean;
  argumentHint?: string;
  mcpConfig?: SkillMcpConfig; // 嵌入的 MCP server 配置
}
```

### 7.2 内置 Skill 清单

#### git-master — 3-Mode Git 专家

**3 种操作模式 (从用户请求自动检测):**

| 模式 | 阶段 | 关键行为 |
|------|------|---------|
| COMMIT | 6 阶段 | 并行上下文收集 → 风格检测 (语言+commit style) → 分支上下文 → 原子单元规划 (min commits = ceil(files/3)) → 策略选择 (fixup/new/reset-rebuild) → 执行+验证 |
| REBASE | 4 阶段 | 上下文分析 → 执行 (interactive/autosquash/onto) → 验证 → 报告 |
| HISTORY SEARCH | 3 阶段 | 搜索类型检测 (pickaxe/regex/blame/bisect/file_log) → 执行 → 呈现结果 |

#### review-work — 5-Agent 并行审查

启动 5 个并行 background sub-agent，ALL 5 必须 PASS 才算通过：

| # | Agent | 角色 | 使用的 agent type | 加载的 skills |
|---|-------|------|------------------|-------------|
| 1 | Goal Verifier | 检查实现是否满足原始目标/约束 | oracle | — |
| 2 | QA Executor | 动手执行测试，结构化场景头脑风暴 | unspecified-high | playwright, dev-browser |
| 3 | Code Reviewer | 10 维度的 staff-engineer 级代码质量审查 | oracle | — |
| 4 | Security Auditor | 10 点安全检查清单 | oracle | — |
| 5 | Context Miner | 搜索 git history, GitHub issues/PRs, Slack, Notion | unspecified-high | git-master |

#### ai-slop-remover — AI 代码异味清除

- 针对单个文件运行
- 检测并移除: 过度注释、冗余解释、不必要的 try-catch、过度抽象
- 多文件时并行调用 (每文件一个 task)

### 7.3 Skill-Embedded MCP

Skill 可以声明自己的 MCP server，按需启停：

```typescript
// skill 定义中
{
  name: "playwright",
  mcpConfig: {
    "playwright": {
      command: "npx",
      args: ["@playwright/mcp-server"],
      env: { DISPLAY: ":0" },
    }
  }
}

// 使用: skill_mcp(mcp_name="playwright", tool_name="navigate", arguments={url: "..."})
// SkillMcpManager 负责: 启动 → 连接 → 调用 → 空闲清理
```

---

## 8. 内置 MCP Server

| MCP | URL | 认证 | 说明 |
|-----|-----|------|------|
| Exa Web Search | `https://mcp.exa.ai/mcp` | 可选 `EXA_API_KEY` | 语义搜索，返回清洁文本 |
| Context7 Docs | `https://mcp.context7.com/mcp` | 可选 `CONTEXT7_API_KEY` | 官方库文档查询 |
| Grep.app | `https://mcp.grep.app` | 无需 | GitHub 代码搜索 (100万+ 仓库) |

可选替代: Tavily (`https://mcp.tavily.com/mcp/`, 需 `TAVILY_API_KEY`)，通过 `websearch.provider` 配置切换。

---

## 9. 实施路线图

> 基于 Oracle 架构评审反馈，原 9 周计划调整为 16 周，更符合实际工程量。

### Phase 1 — 基础框架 + Plugin 骨架 (3 周)

| 周 | 任务 | 交付物 |
|----|------|--------|
| W1 | Plugin 骨架 + 配置系统 | `openclaw.plugin.json`, `register(api)`, Zod schema, 多级配置加载, DegradationManager, 结构化日志 |
| W2 | Agent 注册表 + prompt builder | 11 个 agent 定义, dynamic prompt builder (core + policy sections), model-specific 变体 (Claude/GPT) |
| W3 | 单元测试 + 集成测试基础 | MockPluginApi, config schema 测试, prompt builder 测试, 通道感知注册 |

### Phase 2 — P0 核心编排 (4 周)

| 周 | 任务 | 交付物 |
|----|------|--------|
| W4 | Category 路由 + delegate-task 工具 | 8 个内置分类, category → model resolution pipeline, sync/background 模式 |
| W5 | BackgroundManager (薄增强层) | ConcurrencyManager, 深度检查 (via openclaw session API), 父 session 通知 |
| W6 | Circuit breaker + background_output/cancel | LoopDetector, 工具 schema + handler, Hook Priority Matrix 实现 (HookCoordinator) |
| W7 | P0 集成测试 + E2E | Sisyphus → delegate-task → Junior 全链路, 5 并行 explore, hook 互斥验证 |

### Phase 3 — P1 质量与韧性 (4 周)

| 周 | 任务 | 交付物 |
|----|------|--------|
| W8 | Ralph Loop + Todo Enforcer | 自驱动循环 (含 ultrawork 变体), idle 检测 + 续跑, 互斥协调 |
| W9 | Model Fallback (双层) + Session Recovery | Agent-aware pre-request fallback + runtime error-triggered fallback + 5 种错误恢复 |
| W10 | LSP 工具集 | 3 层 client 架构, LSPServerManager 单例, 6 个工具, 35+ server 定义 |
| W11 | AST-Grep + P1 集成测试 | search + replace, sg CLI 集成, Ralph Loop E2E, fallback E2E |

### Phase 4 — P2 增强体验 (3 周)

| 周 | 任务 | 交付物 |
|----|------|--------|
| W12 | Preemptive Compaction + Comment Checker | 78% 阈值, token 缓存, 外部 binary 集成 |
| W13 | ContextAwareRouter + Memory 集成 | 动态路由 (context/memory/metrics 信号), agent 学习, 历史成功率 |
| W14 | Hashline Edit + Skill-Embedded MCP + 内置 MCP | xxHash32, SkillMcpManager, Exa + Context7 + Grep.app |

### Phase 5 — P3 高级特性 + 命令 + Skill (2 周)

| 周 | 任务 | 交付物 |
|----|------|--------|
| W15 | Keyword Detector + Rules Injector + 内置命令 | 3 种模式, AGENTS.md 注入, 9 个 slash 命令 |
| W16 | 内置 Skill + Cron 集成 + 文档 | git-master, review-work, ai-slop-remover, 3 个 cron job, 配置参考文档 |

### 延伸 Phase (按需)

| 任务 | 说明 |
|------|------|
| ACP 集成 | 外部 harness 委派 (Codex/Claude Code) |
| Tmux/Team Mode | 多 agent 可视化 (仅本地 TUI) |
| Gemini prompt 变体 | Sisyphus/Oracle/Hephaestus 的 Gemini overlay |
| Interactive Bash | tmux 集成的交互式终端 |

### 验收标准

- [ ] Sisyphus 能正确分类意图并委派到对应 agent/category
- [ ] 5+ background agent 并行执行，结果正确回传父 session
- [ ] Ralph Loop 能自主完成多步任务 (≤50 iterations)
- [ ] Model fallback 在 API 错误时自动切换 (≤3 次)
- [ ] Session recovery 能恢复 5 种错误模式中的至少 4 种
- [ ] LSP 工具在 TypeScript/Python/Go 项目中正常工作
- [ ] 配置系统支持项目级 + 用户级合并
- [ ] 所有 hook 可通过配置独立启用/禁用

---

## 10. 关键设计决策

### 10.1 为什么是 Plugin 而非 Fork？

- openclaw 的 plugin-sdk 提供 28 个 hook 点 + `registerTool/registerHook/registerCommand/registerService` API，足以实现所有增强
- 不侵入 openclaw 核心代码，可独立升级
- 与 OmO 对 opencode 的增强模式一致
- openclaw 的 extension 生态已有 120+ 插件，oh-my-claw 可以复用这个生态

### 10.2 openclaw 已有能力的复用策略

| openclaw 能力 | oh-my-claw 策略 |
|--------------|----------------|
| subagent spawn/steer/kill | 封装为 BackgroundManager 薄增强层 (见 4.3 修订)，增加并发控制 + circuit breaker |
| plugin hooks (28 种) | 直接挂载 oh-my-claw hooks，利用 priority 排序 (见 Section 12) |
| skill 系统 (53 skills) | 复用，额外注册 oh-my-claw 专属 skill (git-master, review-work, ai-slop-remover) |
| MCP 配置 | 复用 transport 层，额外注册 3 个内置远程 MCP |
| context engine | 复用 compaction API，增加 preemptive 触发 (78% 阈值) + ContextAwareRouter (见 4.2 修订) |
| task flow | 复用 TaskFlowRegistry，增加 category-aware 路由 |
| memory 系统 | **具体集成** (见下方 10.2.1) |
| cron 调度 | **具体集成** (见下方 10.2.2) |
| ACP 协议 | **具体集成** (见下方 10.2.3) |

#### 10.2.1 Memory 系统集成 (P2)

openclaw 的 memory 系统 (embedding + 时间衰减 + dreaming + QMD) 是 OmO 完全不具备的能力。oh-my-claw 将在以下场景利用它：

**a) Agent 学习 — 跨 session 记忆**

```typescript
// 通过 api.registerMemoryPromptSection() 注入 memory 到 agent prompt
api.registerMemoryPromptSection({
  id: "omc-agent-memory",
  priority: 50,
  async build(ctx) {
    // 从 memory 中检索与当前任务相关的历史决策
    const memories = await ctx.memory.query({
      query: ctx.currentTask,
      limit: 5,
      minRelevance: 0.7,
      tags: ["omc-decision", "omc-pattern"],
    });
    if (memories.length === 0) return null;
    return {
      role: "system",
      content: `[Historical Context]\n${memories.map(m => `- ${m.content}`).join("\n")}`,
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
      content: `Category=${result.category} Model=${result.model} Status=${result.status} Duration=${result.durationMs}ms`,
      tags: ["omc-category-outcome"],
      metadata: { category: result.category, model: result.model, success: result.status === "completed" },
    });
  },
});

// ContextAwareRouter 查询历史成功率:
const outcomes = await memory.query({ tags: ["omc-category-outcome"], limit: 50 });
const successRate = outcomes.filter(o => o.metadata.success).length / outcomes.length;
```

**c) 用户偏好记忆**

```typescript
// 当用户纠正 agent 行为时 (e.g., "不要用 Gemini")，存入 memory
// 后续 category resolution 时检索偏好
```

#### 10.2.2 Cron 调度集成 (P3)

利用 openclaw 的 cron 系统，定期运行维护任务：

```typescript
// 通过 plugin config 声明 cron jobs
// openclaw.plugin.json → configSchema 中定义 cron 配置

// 内置 cron jobs:
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
    agentId: "oracle",
    task: "Check for known vulnerabilities in project dependencies",
  },
  {
    id: "omc-stale-branch-cleanup",
    schedule: "0 8 1 * *",  // 每月 1 号 8:00
    description: "Stale branch report",
    agentId: "explore",
    task: "List branches not updated in 30+ days with their last commit info",
    skills: ["git-master"],
  },
];
```

#### 10.2.3 ACP 协议集成 (P3)

通过 openclaw 的 ACP (Agent Communication Protocol)，oh-my-claw 的 agent 可以调用外部 harness：

```typescript
// 场景: Sisyphus 委派任务给外部 Claude Code 实例
// 通过 ACP persistent 模式，保持长连接

// delegate-task 工具扩展: 新增 harness 参数
{
  name: "task",
  parameters: {
    // ... 现有参数 ...
    harness: { type: "string" },  // 可选: "codex" | "claude-code" | "local"
  }
}

// 当 harness 指定时:
// 1. 通过 ACP 协议发送任务到外部 harness
// 2. 外部 harness 执行任务 (在其自己的环境中)
// 3. 结果通过 ACP 回传
// 4. BackgroundManager 统一管理生命周期
```

### 10.3 与 OmO 的关键差异

| 维度 | OmO (opencode plugin) | oh-my-claw (openclaw plugin) |
|------|----------------------|------------------------------|
| 宿主 hook 数量 | 10 个 | 28 个 (更细粒度控制) |
| subagent 机制 | 自建 BackgroundManager + tmux | 复用 openclaw subagent API + 增强层 |
| 多通道 | 仅 terminal | 继承 openclaw 25+ 通道 |
| Memory | 无 | 继承 openclaw memory (embedding + dreaming) |
| Cron | 无 | 继承 openclaw cron 调度 |
| ACP | 无 | 继承 openclaw ACP (Codex/Claude Code harness) |
| 配置格式 | JSONC | JSON5 (与 openclaw 一致) |
| Plugin 注册 | `PluginModule { id, server }` | `definePluginEntry({ id, configSchema, register(api) })` |
| 工具注册 | 通过 config handler 注入 | `api.registerTool(tool)` 直接注册 |
| Hook 注册 | 通过 plugin interface 映射 | `api.registerHook(name, handler, { priority })` 直接注册 |

### 10.4 openclaw 独有优势的利用

oh-my-claw 可以利用 openclaw 的独有能力实现 OmO 无法做到的增强：

1. **Memory-Aware Agent**: 利用 openclaw 的 memory 系统，agent 可以跨 session 记忆用户偏好、项目模式、历史决策
2. **Cron-Driven Maintenance**: 利用 cron 调度，定期运行代码质量检查、依赖更新、安全扫描
3. **Multi-Channel Orchestration**: 同一个 agent 团队可以通过 Discord/Slack/Telegram 等多通道协作
4. **ACP Harness Integration**: 通过 ACP 协议，oh-my-claw 的 agent 可以调用外部 Codex/Claude Code 实例

---

## 11. 技术栈

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| 语言 | TypeScript (ESM) | 与 openclaw 一致 |
| 运行时 | Node.js | 与 openclaw 一致 (OmO 用 Bun，但 openclaw 生态是 Node) |
| 包管理 | pnpm | 与 openclaw monorepo 一致 |
| 配置校验 | Zod | 与 openclaw 一致 |
| LSP Client | vscode-jsonrpc | 轻量级 JSON-RPC 实现 |
| AST-Grep | sg CLI (auto-download) | @ast-grep/napi 或 sg binary |
| Hash | xxHash32 (via node binding) | Hashline Edit 用 |
| 测试 | vitest | 与 openclaw 一致 |
| Comment Checker | @code-yeongyu/comment-checker | 外部 binary |

---

## 12. Hook 优先级矩阵与冲突解决

### 12.1 问题

oh-my-claw 在 openclaw 的 28 个 hook 点上注册了 22+ handler。多个 handler 挂载到同一 hook 点时，执行顺序和互斥关系必须明确定义，否则会出现：
- Ralph Loop 和 Todo Enforcer 同时注入续跑 prompt (双重注入)
- Keyword Detector 在 `claiming` 模式下抢先 claim，阻断 Ralph Loop
- Comment Checker 注册 pending call 后，Hashline 验证失败导致 pending 孤儿

### 12.2 优先级矩阵

数字越大越先执行 (openclaw 的 `registerHook(name, handler, { priority })`)：

| Hook Point | Handler | Priority | 互斥规则 |
|-----------|---------|----------|---------|
| `agent_end` | Ralph Loop | 100 | Ralph active → 抑制 Todo Enforcer |
| `agent_end` | Todo Enforcer | 50 | Ralph active 时跳过 |
| `before_agent_reply` | Ralph Loop | 100 | Ralph active → claim, 阻断后续 |
| `before_agent_reply` | Keyword Detector | 80 | Ralph active 时跳过 |
| `before_model_resolve` | Model Fallback | 100 | — |
| `llm_output` | Session Recovery | 100 | Recovery 中 → 抑制 Runtime Fallback |
| `llm_output` | Runtime Fallback | 50 | Recovery 中跳过 |
| `before_tool_call` | Hashline Validation | 100 | 验证失败 → reject, Comment Checker 不触发 |
| `before_tool_call` | Comment Checker (register) | 50 | Hashline reject 时跳过注册 |
| `after_tool_call` | Comment Checker (detect) | 100 | — |
| `after_tool_call` | Preemptive Compaction | 50 | Compaction 进行中跳过 |
| `before_prompt_build` | Dynamic Prompt Builder | 100 | — |
| `before_prompt_build` | Rules Injector | 50 | — |
| `subagent_spawning` | Category Router | 100 | — |
| `subagent_spawning` | Background Manager | 50 | — |
| `message_received` | Keyword Detector | 100 | — |

### 12.3 互斥状态机

```typescript
// hooks/coordination.ts
class HookCoordinator {
  private ralphActive = new Set<string>();      // sessionId set
  private recoveryActive = new Set<string>();   // sessionId set
  private compactionActive = new Set<string>(); // sessionId set

  isRalphActive(sessionId: string): boolean;
  isRecovering(sessionId: string): boolean;
  isCompacting(sessionId: string): boolean;

  // 每个 hook handler 在执行前检查:
  // if (coordinator.isRalphActive(sid) && this.name === "todo-enforcer") return; // skip
}
```

### 12.4 防双重注入

Ralph Loop 和 Todo Enforcer 都通过 `promptAsync()` 注入 prompt。防止同一 session 在同一 idle 周期内被双重注入：

```typescript
// 全局 injection guard
const injectionInFlight = new Set<string>(); // sessionId

function guardedInject(sessionId: string, fn: () => Promise<void>): Promise<void> {
  if (injectionInFlight.has(sessionId)) return;
  injectionInFlight.add(sessionId);
  try { await fn(); }
  finally { injectionInFlight.delete(sessionId); }
}
```

---

## 13. 韧性架构 (Resilience Architecture)

### 13.1 Plugin 级错误边界

oh-my-claw 的任何 hook/tool handler 抛出异常时，不应导致 openclaw 崩溃：

```typescript
// shared/error-boundary.ts
function withErrorBoundary<T>(
  handlerName: string,
  fn: () => T | Promise<T>,
  fallback?: T
): T | Promise<T> {
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
    metrics.increment("hook.error", { handler: handlerName });
    return fallback as T;
  }
}

// 每个 hook 注册时包裹:
api.registerHook("agent_end", withErrorBoundary("ralph-loop", ralphLoopHandler), { priority: 100 });
```

### 13.2 优雅降级层级

| 级别 | 触发条件 | 降级行为 |
|------|---------|---------|
| L0 正常 | 无错误 | 全功能运行 |
| L1 单 hook 降级 | 某 hook 连续失败 3 次 | 禁用该 hook，其余正常。日志警告 |
| L2 子系统降级 | LSP/AST-grep 启动失败 | 禁用相关工具，agent prompt 中移除工具描述。toast 通知 |
| L3 Background 降级 | BackgroundManager 异常 | 所有 delegate-task 强制 sync 模式。禁用并行 |
| L4 Plugin 降级 | 连续 10 次 hook 错误 / 配置加载失败 | oh-my-claw 整体禁用，openclaw 回退到原生行为。显著警告 |

```typescript
// shared/degradation.ts
class DegradationManager {
  private hookFailures: Map<string, number> = new Map();
  private disabledHooks: Set<string> = new Set();
  private level: 0 | 1 | 2 | 3 | 4 = 0;

  recordFailure(hookName: string): void {
    const count = (this.hookFailures.get(hookName) ?? 0) + 1;
    this.hookFailures.set(hookName, count);
    if (count >= 3) {
      this.disabledHooks.add(hookName);
      this.level = Math.max(this.level, 1) as any;
      logger.warn(`[oh-my-claw] Hook ${hookName} disabled after ${count} failures`);
    }
    if (this.disabledHooks.size >= 10) {
      this.level = 4;
      this.shutdown();
    }
  }

  isHookEnabled(hookName: string): boolean {
    return this.level < 4 && !this.disabledHooks.has(hookName);
  }
}
```

### 13.3 Kill Switch

```typescript
// 用户可通过配置或命令紧急禁用:
// 1. 配置: oh-my-claw.json → { "enabled": false }
// 2. 命令: /omc-disable (注册为 openclaw command)
// 3. 环境变量: OMC_DISABLED=1
// 4. 自动: DegradationManager L4 触发
```

---

## 14. 通道兼容性矩阵

### 14.1 问题

openclaw 运行在 25+ 通道上，但 oh-my-claw 的许多功能源自 OmO 的 TUI 终端假设。需要明确每个功能在不同通道类型上的兼容性。

### 14.2 通道分类

| 通道类型 | 代表 | 文件系统 | 长消息 | 交互式 | 进程 |
|---------|------|---------|--------|--------|------|
| 本地 TUI | terminal, ACP | ✅ | ✅ | ✅ | ✅ |
| 桌面 IM | Discord, Slack | ❌ | ⚠️ (2000 char) | ⚠️ | ❌ |
| 移动 IM | Telegram, WhatsApp | ❌ | ⚠️ (4096 char) | ❌ | ❌ |
| API | HTTP gateway | ❌ | ✅ | ❌ | ❌ |

### 14.3 功能兼容性矩阵

| 功能 | 本地 TUI | 桌面 IM | 移动 IM | API | 适配策略 |
|------|---------|---------|---------|-----|---------|
| Agent 角色体系 | ✅ | ✅ | ✅ | ✅ | 纯 prompt 层，通道无关 |
| Category 路由 | ✅ | ✅ | ✅ | ✅ | 纯逻辑层，通道无关 |
| Background Agent | ✅ | ✅ | ✅ | ✅ | 通过 openclaw subagent API，通道无关 |
| Ralph Loop | ✅ | ⚠️ | ⚠️ | ✅ | 完成检测: 仅用 session messages API (不依赖 transcript 文件)。通知: 用 channel message 替代 toast |
| Todo Enforcer | ✅ | ⚠️ | ⚠️ | ✅ | 倒计时: 用 channel message 替代 toast。注入: 通过 session API |
| Model Fallback | ✅ | ✅ | ✅ | ✅ | 纯 API 层，通道无关 |
| Session Recovery | ✅ | ✅ | ✅ | ✅ | 纯 API 层，通道无关 |
| LSP 工具 | ✅ | ❌ | ❌ | ❌ | 需要本地文件系统 + LSP server 进程。非本地通道: 工具不注册 |
| AST-Grep | ✅ | ❌ | ❌ | ❌ | 同 LSP |
| Hashline Edit | ✅ | ❌ | ❌ | ❌ | 同 LSP |
| Comment Checker | ✅ | ❌ | ❌ | ❌ | 需要外部 binary。非本地通道: hook 不注册 |
| Keyword Detector | ✅ | ✅ | ✅ | ✅ | 纯文本匹配，通道无关 |
| Tmux/Team Mode | ✅ | ❌ | ❌ | ❌ | 仅本地 TUI |
| /refactor 命令 | ✅ | ❌ | ❌ | ❌ | 依赖 LSP + AST-grep |
| /start-work 命令 | ✅ | ⚠️ | ⚠️ | ✅ | 计划文件写入需 workspace。IM 通道: 计划输出为消息 |
| /handoff 命令 | ✅ | ✅ | ✅ | ✅ | 纯文本输出 |

### 14.4 通道感知注册

```typescript
// index.ts — register() 中根据通道类型条件注册
function register(api) {
  const isLocal = api.runtime.channelType === "terminal" || api.runtime.channelType === "acp";

  // 通道无关功能: 始终注册
  registerAgentSystem(api, config);
  registerCategoryRouter(api, config);
  registerBackgroundManager(api, config);
  registerRalphLoopHook(api, config);
  registerModelFallbackHook(api, config);
  registerSessionRecoveryHook(api, config);
  registerKeywordDetectorHook(api, config);

  // 本地专属功能: 仅本地通道注册
  if (isLocal) {
    registerLspTools(api, config);
    registerAstGrepTools(api, config);
    registerHashlineEditTool(api, config);
    registerCommentCheckerHook(api, config);
    registerTmuxIntegration(api, config);
  }

  // 通知适配: 根据通道选择 toast vs channel message
  const notifier = isLocal ? new ToastNotifier(api) : new ChannelMessageNotifier(api);
  registerTodoContinuationHook(api, config, notifier);
}
```

---

## 15. 测试策略

### 15.1 测试金字塔

```
        ╱╲
       ╱ E2E ╲          2-3 个端到端场景 (per phase)
      ╱────────╲
     ╱ Integration╲     每个 hook chain 1 个集成测试
    ╱──────────────╲
   ╱   Unit Tests    ╲  每个模块 80%+ 覆盖率
  ╱────────────────────╲
```

### 15.2 单元测试 (vitest)

| 模块 | 测试重点 | Mock 策略 |
|------|---------|----------|
| config/schema.ts | Zod schema 验证: 合法/非法配置, 默认值, 合并逻辑 | 无需 mock |
| categories/router.ts | category → model 解析: 优先级链, fallback, unstable 检测 | mock connectedProviders |
| background/concurrency.ts | 并发控制: acquire/release, 队列排序, limit 边界 | 无需 mock |
| background/loop-detector.ts | Circuit breaker: 连续相同 signature, 阈值触发, 重置 | 无需 mock |
| hooks/ralph-loop/detector.ts | 完成检测: promise 正则, transcript 解析, 边界 case | mock session messages API |
| hooks/todo-enforcer/stagnation.ts | 停滞检测: 3 次无进展, 进度重置, 失败退避 | 无需 mock |
| hooks/session-recovery/error-classifier.ts | 5 种错误模式分类: 正则匹配, 边界 case | 无需 mock |
| hooks/model-fallback/chain-traversal.ts | Fallback chain: 可达性, no-op 跳过, 耗尽 | mock providers |
| tools/lsp/server-definitions.ts | Server 定义: 扩展名映射, 命令解析 | 无需 mock |
| tools/hashline-edit/hash-computation.ts | Hash 算法: xxHash32, dictionary lookup, 边界 | 无需 mock |
| agents/prompt-builder/*.ts | Prompt 组装: section 生成, model-specific 变体 | mock agent/tool/skill 列表 |

### 15.3 集成测试

```typescript
// Mock openclaw Plugin API
class MockPluginApi implements OpenClawPluginApi {
  registeredTools: Map<string, AnyAgentTool> = new Map();
  registeredHooks: Map<string, Function[]> = new Map();
  mockSessions: Map<string, MockSession> = new Map();

  registerTool(tool) { this.registeredTools.set(tool.name, tool); }
  registerHook(name, handler, opts) { ... }

  // 模拟 subagent spawn
  async spawnSubagent(params) { return { status: "accepted", childSessionKey: "mock-child" }; }
}

// 集成测试场景:
// 1. Ralph Loop + Todo Enforcer 互斥: Ralph active 时 Todo 不触发
// 2. Model Fallback + Runtime Fallback 链: API 429 → fallback → 成功
// 3. Session Recovery + Ralph Loop: recovery 中 Ralph 不注入
// 4. Category Router + Background Manager: delegate-task → spawn → notify
// 5. Comment Checker + Hashline: Hashline reject → Comment Checker skip
```

### 15.4 E2E 测试 (per phase)

| Phase | E2E 场景 | 验证点 |
|-------|---------|--------|
| P1 | Sisyphus 接收 "implement auth" → 分类为 deep → delegate-task → Junior 执行 → 结果回传 | 意图分类, category 路由, subagent 生命周期 |
| P1 | 5 个 explore agent 并行搜索 → 全部完成 → 结果合并 | 并发控制, 通知批量, 结果收集 |
| P2 | Ralph Loop: agent 执行 3 步任务 → 前 2 步 idle → 续跑 → 第 3 步完成 → `<promise>DONE</promise>` | 完成检测, 续跑注入, 状态持久化 |
| P2 | API 429 → runtime fallback → 成功 → 原模型 cooldown 后恢复 | 错误分类, fallback 切换, cooldown |

---

## 16. 安全考量

### 16.1 进程安全

| 风险 | 缓解措施 |
|------|---------|
| LSP server 进程失控 (内存泄漏, CPU 占用) | 资源限制: `ulimit` 或 cgroup。强制 timeout: 60s init, 15s per request。idle 5min 自动 kill |
| AST-grep replace 修改任意文件 | `dryRun: true` 默认。非 dry-run 时: 仅允许 workspace 内文件。diff 预览 + agent 确认 |
| Comment Checker binary 供应链风险 | SHA256 校验 (pinned version)。沙箱执行 (无网络, 只读 stdin/stdout)。30s timeout + SIGKILL |

### 16.2 Prompt 安全

| 风险 | 缓解措施 |
|------|---------|
| `file://` URI 路径穿越 | 验证: 必须在 workspace 或 `~/.openclaw/` 内。拒绝 `..` 和符号链接 |
| 用户 prompt_append 注入恶意指令 | 不做过滤 (用户自己的配置)，但日志记录来源 |
| Background agent 权限提升 | 子 agent 继承父 agent 的 toolPolicy，不可升级。Junior 永远无 `task` 工具 |

### 16.3 数据安全

| 风险 | 缓解措施 |
|------|---------|
| Ralph Loop 状态文件泄露 session 内容 | 状态文件仅存 metadata (iteration, promise, strategy)，不存 transcript |
| Background task 结果跨 session 泄露 | task 结果仅可被父 session 访问 (parentSessionId 校验) |
| MCP API key 泄露 | 通过环境变量传递，不写入配置文件。日志中 mask |

---

## 17. 可观测性与日志

### 17.1 结构化日志

```typescript
// shared/logger.ts
interface LogEntry {
  timestamp: string;
  level: "debug" | "info" | "warn" | "error";
  module: string;          // e.g. "ralph-loop", "category-router"
  sessionId?: string;
  taskId?: string;
  correlationId?: string;  // 贯穿 delegation chain
  message: string;
  data?: Record<string, unknown>;
  durationMs?: number;
}

// 示例:
// {"timestamp":"...","level":"info","module":"category-router","sessionId":"ses_abc",
//  "correlationId":"cor_xyz","message":"resolved category","data":{"category":"deep",
//  "model":"gpt-5.5","provider":"openai","fallbackIndex":0},"durationMs":12}
```

### 17.2 关键指标

| 指标 | 类型 | 说明 |
|------|------|------|
| `omc.hook.execution` | histogram | 每个 hook handler 的执行时间 |
| `omc.hook.error` | counter | 每个 hook handler 的错误次数 |
| `omc.background.active` | gauge | 当前活跃的 background task 数 |
| `omc.background.completed` | counter | 完成的 background task 数 (by status: success/error/cancelled) |
| `omc.background.circuit_breaker` | counter | Circuit breaker 触发次数 |
| `omc.fallback.triggered` | counter | Model fallback 触发次数 (by layer: agent/runtime) |
| `omc.recovery.triggered` | counter | Session recovery 触发次数 (by error_type) |
| `omc.ralph.iterations` | histogram | Ralph Loop 完成所需的迭代次数 |
| `omc.category.resolution` | histogram | Category → model 解析时间 |
| `omc.lsp.request` | histogram | LSP 请求延迟 (by server, method) |
| `omc.degradation.level` | gauge | 当前降级级别 (0-4) |

### 17.3 诊断命令

```
/omc-status          — 显示: 降级级别, 活跃 background tasks, hook 状态, LSP servers
/omc-metrics         — 显示: 最近 1h 的关键指标摘要
/omc-debug <hook>    — 启用指定 hook 的 debug 日志 (下次触发时输出详细信息)
```
