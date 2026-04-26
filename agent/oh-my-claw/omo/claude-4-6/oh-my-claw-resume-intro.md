# oh-my-claw — 多智能体编排增强平台

**角色：** 项目架构设计者 / 核心开发者

---

## 项目简介

oh-my-claw 是构建在 OpenClaw（多通道 AI 网关平台）之上的**编码工作流增强层**，借鉴 oh-my-openagent 对 opencode 的增强模式，以纯插件方式（不修改宿主源码）将通用 AI 网关升级为具备**多模型编排、自驱动任务闭环、故障自愈、质量管控**能力的工程化智能体平台。

核心设计哲学：**"人工干预是一种失败信号"** —— 系统应自主完成任务的规划、分发、执行、验证、恢复与交付，而非依赖用户反复提醒。

---

## 核心功能特性

### 多智能体角色编排体系

- 设计 11 个角色化专家 Agent（Sisyphus 编排者、Oracle 架构顾问、Prometheus 战略规划者、Hephaestus 深度执行者、Explore 代码探索、Librarian 文档检索、Metis 计划分析、Momus 计划审查、Atlas 并行编排、Junior 任务执行、Multimodal-Looker 视觉分析）
- 每个 Agent 拥有独立的模型配置、Fallback 链、工具权限策略（full / read-only / search-only）和 Model-Specific Prompt 变体（Claude / GPT / GPT-5.5 / Gemini 四种变体自动适配）
- 实现 Dynamic Prompt Builder，根据当前可用的 Agent / Tool / Skill / Category 动态组装 Prompt，避免静态 Prompt 与运行时能力不匹配

### Category 智能路由系统

- 构建 8 个领域分类（visual-engineering / ultrabrain / deep / artistry / quick / writing / unspecified-low / unspecified-high），每个分类绑定最优模型与思考强度
- 实现 Category → Model Resolution Pipeline：用户配置覆盖 → 分类默认模型 → Fallback Chain → Provider 可达性检测，支持 Unstable Agent 自动强制后台执行
- 预留 ContextAwareRouter 动态增强层（P2），支持上下文窗口感知、历史成功率加权、用户偏好记忆的动态路由

### Background Agent 并行执行引擎

- 基于 openclaw Subagent API 的薄增强层设计，不维护独立任务状态，避免双重状态漂移
- 实现 ConcurrencyManager（按 Provider/Model 分组的 Promise Queue 并发控制）、LoopDetector（Circuit Breaker，连续 20 次相同 Tool Call 触发熔断，绝对上限 4000 次）、Depth Limit（默认 3 层子 Agent 嵌套）
- 父 Session 批量通知机制：后台任务完成时生成 `<system-reminder>` 注入父 Session，支持增量结果获取

### 自驱动任务完成循环

- **Ralph Loop**：监听 Session 空闲事件，双路径完成检测（Transcript 文件扫描 + Session Messages API），未完成时自动注入续跑 Prompt，支持 Ultrawork 变体（需 Oracle 验证 `<promise>VERIFIED</promise>` 才算完成），安全阀默认 100 次迭代
- **Todo Continuation Enforcer**：检测未完成 Todo → 2s 倒计时 → 注入续跑指令，内置停滞检测（连续 3 次无进展停止）、连续失败上限（5 次 + 指数退避）、Compaction Guard（60s 冷却）
- 两套循环通过 HookCoordinator 互斥状态机协调，防止双重注入

### 模型故障自愈与 Session 恢复

- **双层 Model Fallback**：Agent-Aware Pre-request Fallback（检查 Provider 可达性，遍历 Agent Fallback Chain）+ Runtime Error-Triggered Fallback（429/500/502/503/504 错误自动切换模型重试，Cooldown 60s，最多 3 次）
- **Session Recovery**：识别 5 种 API 错误模式（tool_result_missing / unavailable_tool / thinking_block_order / thinking_disabled_violation / assistant_prefill_unsupported）并自动修复，通过 processingErrors Set 去重，无需人工介入

### 门禁式工程化工作流

- 五层逻辑分层：Entry → Decision → Context → Execution Control → Output
- 核心主链路：Task Intake → Task Decision Engine（意图/复杂度/Workflow 推荐/Plan Enforcement 决策）→ Context Snapshot Builder（三层模型：Invariant Rules / Project Summary / Task-Relevant Docs）→ 4 级 Gate（Entry Gate 计划强制 / Edit Gate 上下文充分性 / Verify Gate 验证要求 / Exit Gate 输出完整性）→ Workflow Engine（统一骨架：intake → scan → plan → execute → verify → handoff）→ Summary Builder
- 3 个 MVP Workflow 模板：design-proposal（方案设计）、feature-implementation（功能实现）、bug-fix（缺陷修复），共享统一状态模型与 Gate 机制

### LSP + AST-Grep 工具链

- 自研 LSP Client 三层架构：Transport（JSON-RPC over stdin/stdout）→ Connection（Initialize 握手）→ Client（协议方法），LSPServerManager 单例管理（引用计数 + 5min 空闲超时 + 60s 初始化超时）
- 集成 35+ 语言服务器定义（TypeScript / Go / Python / Rust / Java / C/C++ / Vue / ESLint 等），提供 6 个工具：goto-definition / find-references / symbols / diagnostics / prepare-rename / rename
- AST-Grep 支持 25 种语言的模式搜索与替换，底层调用 sg CLI（自动下载 Binary）

### 安全编辑协议（Hashline Edit）

- 基于 xxHash32 的行级哈希锚定：16-char Nibble Dictionary → 256 个 2-char Code，为每行生成唯一标识
- 编辑执行 Pipeline：Normalize → Dedupe → Bottom-up Sort → Validate Line Refs（Hash 对比当前文件）→ Overlap Detection → Apply → Formatter 触发
- 有效防止 Stale Edit（过期编辑）和并发编辑冲突

### 质量管控与可观测性

- **AI Slop 检测**：拦截 write/edit 工具调用 → 外部 Binary 检测 → 将警告追加到 Tool Output → Agent 自动修复
- **Preemptive Compaction**：78% 上下文窗口阈值触发主动压缩，Token 缓存每次 Assistant 完成时更新
- **Review Work**：5-Agent 并行审查（Goal Verifier + QA Executor + Code Reviewer + Security Auditor + Context Miner），全部通过才算审查通过
- 结构化日志 + 关键指标体系（Hook 执行时间、Background Task 状态、Fallback 触发次数、Circuit Breaker 触发、降级级别等）

### 韧性架构与优雅降级

- 4 级降级策略：L1 单 Hook 降级（连续 3 次失败禁用）→ L2 子系统降级（LSP/AST-Grep 不可用时移除工具）→ L3 Background 降级（强制同步模式）→ L4 Plugin 整体降级（回退到 openclaw 原生行为）
- Plugin 级错误边界：所有 Hook/Tool Handler 包裹 withErrorBoundary，异常不传播到宿主
- Kill Switch 支持：配置文件 / 命令 / 环境变量 / 自动降级四种紧急禁用方式

### 多通道兼容与生态集成

- 通道感知注册：根据通道类型（本地 TUI / 桌面 IM / 移动 IM / API）条件注册功能，核心编排能力通道无关，LSP/AST-Grep/Hashline 等本地工具仅在本地通道注册
- 复用 openclaw 独有能力：Memory 系统（跨 Session 记忆用户偏好与历史决策）、Cron 调度（定期代码质量扫描与依赖审计）、ACP 协议（委派任务到外部 Codex/Claude Code 实例）
- 内置 3 个远程 MCP Server（Exa Web Search / Context7 Docs / Grep.app GitHub Search）+ Skill-Embedded MCP（Skill 按需启停 MCP Server）

---

## 架构亮点

- 以 openclaw 28 个 Hook 为接入点，覆盖 Agent / Message / Tool / Session / Subagent / Gateway 全生命周期
- 10 段标准状态流：RAW_INPUT → NORMALIZED_INTAKE → DECIDED → CONTEXT_READY → ENTRY_GATED → EDIT_GATED → WORKFLOW_RUNNING → VERIFY_GATED → EXIT_GATED → OUTPUT_EMITTED
- Hook 优先级矩阵 + 互斥状态机，解决 Ralph Loop / Todo Enforcer / Keyword Detector / Comment Checker 等多 Hook 并发冲突
- 遵循"强决策、弱配置"原则：少量强默认值 + 有限可调参数 + 关键安全行为不可关闭
- 三层稳定性治理：Stable（核心闭环）/ Beta（可靠性增强）/ Experimental（高级实验特性，可独立关闭）

---

## 技术栈

TypeScript (ESM) · OpenClaw Plugin SDK · Zod · xxHash32 · AST-Grep (sg CLI) · JSON-RPC (vscode-jsonrpc) · SQLite · vitest · pnpm · tmux

---

## 简历精简版（适合一段话描述）

设计并开发 oh-my-claw 多智能体编排增强平台，基于 openclaw 插件体系实现非侵入式扩展。构建 11 个角色化专家 Agent + 8 类 Category 智能路由 + Background Agent 并行引擎的多模型编排体系；实现 Ralph Loop 自驱动完成循环、双层 Model Fallback 故障自愈、5 种 Session 错误自动恢复；设计 Task Decision Engine → 4 级 Gate 门禁 → 3 套 Workflow 模板的工程化闭环主链路；集成 LSP 工具链（35+ 语言服务器）、AST-Grep（25 种语言）、Hashline 安全编辑协议；实现 4 级优雅降级、Hook 优先级矩阵与互斥状态机、AI Slop 检测与 5-Agent 并行审查等质量管控能力。

---

## 简历要点版（适合 3-5 条 Bullet）

- 负责 oh-my-claw 智能体增强平台架构设计与核心开发，基于 openclaw 28 个 Hook 生命周期实现非侵入式插件扩展，构建 11 个角色化专家 Agent 与 8 类 Category 智能路由的多模型编排体系
- 设计 Background Agent 并行引擎（Provider 级并发控制 + Circuit Breaker 熔断 + 3 层 Depth Limit），实现 Ralph Loop 自驱动完成循环与 Todo Continuation Enforcer，通过互斥状态机协调多 Hook 并发
- 实现双层 Model Fallback（Pre-request + Runtime Error-Triggered）与 5 种 Session 错误模式自动恢复，构建 4 级优雅降级策略，确保系统韧性
- 设计 Task Decision Engine → Context Snapshot（三层模型）→ 4 级 Gate 门禁 → Workflow Engine → Unified Summary 的工程化闭环主链路，支持 design-proposal / feature-implementation / bug-fix 三套 Workflow 模板
- 自研 LSP Client 三层架构（集成 35+ 语言服务器）、AST-Grep 工具（25 种语言）、Hashline 安全编辑协议（xxHash32 行级锚定），集成 AI Slop 检测与 5-Agent 并行审查质量管控体系

---

## 项目经历版（可直接粘贴）

### oh-my-claw｜多智能体 AI 编排增强平台

- 面向 openclaw 多通道 AI 网关设计插件式增强层，构建 11 个角色化专家 Agent + 8 类 Category 智能路由 + Background Agent 并行引擎的多模型编排体系，支持 Model-Specific Prompt 变体自动适配与 Provider 可达性检测
- 实现 Ralph Loop 自驱动完成循环（双路径完成检测 + Ultrawork Oracle 验证）、双层 Model Fallback 故障自愈、5 种 Session 错误自动恢复，通过 Hook 优先级矩阵与互斥状态机协调多 Hook 并发
- 设计 Task Decision Engine → 三层 Context Snapshot → 4 级 Gate 门禁 → 3 套 Workflow 模板 → Unified Summary 的工程化闭环主链路，遵循"决策在前、上下文在前、执行在后"原则
- 自研 LSP Client 三层架构（35+ 语言服务器）、AST-Grep（25 种语言模式搜索替换）、Hashline 安全编辑协议（xxHash32 行级锚定防 Stale Edit），集成 AI Slop 检测与 5-Agent 并行审查
- 构建 4 级优雅降级策略与 Plugin 级错误边界，支持多通道感知注册（本地 TUI / Discord / Slack / Telegram 等 25+ 通道），复用 openclaw Memory / Cron / ACP 独有能力
