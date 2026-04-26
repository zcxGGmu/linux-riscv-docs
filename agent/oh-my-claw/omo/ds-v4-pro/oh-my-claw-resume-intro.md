## oh-my-claw — OpenClaw Coding Workflow Enhancement Layer

**角色：** 项目架构设计者 / 核心开发者

### 项目简介

`oh-my-claw` 是一个构建在 OpenClaw（多通道 AI 网关平台）之上的 **编码工作流增强层**。它借鉴 `oh-my-openagent` 对 opencode 的成功增强模式，在不修改宿主源码的前提下，通过插件系统将单 Agent 通用编码助手升级为一套 **多模型编排、自愈恢复、质量管控** 的智能体工程平台。

核心理念：**"人工干预是一种失败信号"** —— Agent 应自主完成规划、执行、验证、恢复和交付的完整闭环，而非频繁依赖用户提醒。

### 核心技术能力

- **多模型编排体系**：设计 11 个角色化专家 Agent（Sisyphus 编排者、Oracle 架构顾问、Prometheus 战略规划者、Hephaestus 深度执行者、Atlas 并行编排者等），每个 Agent 拥有独立模型配置、工具权限策略、Model-Specific Prompt 变体（Claude/GPT/Gemini）和 Fallback 链
- **Category 智能路由**：实现 8 个领域分类（visual-engineering/ultrabrain/deep/quick 等）→ 最优模型自动解析 Pipeline，支持 Provider 可达性检测、历史成功率加权、上下文窗口感知的动态路由增强
- **Background Agent 并行引擎**：基于 Promise Queue 的 Provider 级并发控制 + Circuit Breaker 熔断机制（连续 20 次重复 tool call 触发熔断），支持 Depth Limit（3 层）、Task TTL、Batch Notification 父 Session 注入
- **自驱动完成循环**：Ralph Loop + Todo Continuation Enforcer 双循环机制，Session 空闲时自动检测未完成任务 → 注入续跑指令，支持 Ultrawork 模式（Oracle 验证通过才算完成），防呆停滞检测（3 次无进展停止）
- **模型故障自愈**：双层 Fallback（Agent-Aware Pre-request + Runtime Error-Triggered），支持 Rate Limit / 429 / 503 等错误自动切换模型重试，Cooldown 60s，最多 3 次尝试
- **Session 自动恢复**：识别 5 种 API 错误模式（tool_result_missing / unavailable_tool / thinking_block_order / thinking_disabled_violation / assistant_prefill_unsupported）并自动修复，无需人工介入
- **门禁式工程流程**：以 Task Decision Engine → Context Snapshot（3 层模型：规则/摘要/任务文档）→ 4 级 Gate（Entry/Edit/Verify/Exit）→ Workflow Engine → Unified Summary 为核心主链路，确保"决策在前、上下文在前、执行在后"
- **LSP + AST-Grep 工具链**：自研 LSP Client（JSON-RPC Transport → Connection → Client 三层架构），集成 35+ 语言服务器，支持 Go-to-Definition、Find References、Diagnostics、Rename；AST-Grep 支持 25 种语言的模式搜索与替换
- **安全编辑协议**：Hashline-style Safe Edit，基于 xxHash32 哈希锚定的行级编辑验证，支持 Bottom-up 排序 → 去重 → Overlap 检测，防止 Stale Edit
- **质量管控**：AI Slop 自动检测（拦截 write/edit → 追加警告 → Agent 自动修复）、Preemptive Compaction（78% 上下文阈值触发主动压缩）、Dynamic Prompt Builder（根据可用 Agent/Tool/Skill/Category 实时组装 Prompt）
- **增强工具生态**：Git Master（Atomic Commit/Rebase/History Search）、Review Work（5-Agent 并行审查：Goal + Quality + Security + QA + Context Mining）、Skill-Embedded MCP（Skill 按需启停 MCP Server）

### 架构特点

- 以 **OpenClaw 28 个 Hook** 为接入点，覆盖 Agent 全生命周期（before_model_resolve / before_prompt_build / before_agent_start / agent_end / subagent_spawning 等）
- 五层逻辑分层：Entry → Decision → Context → Execution Control → Output
- 10 段标准状态流：RAW_INPUT → NORMALIZED_INTAKE → DECIDED → CONTEXT_READY → ENTRY_GATED → EDIT_GATED → WORKFLOW_RUNNING → VERIFY_GATED → EXIT_GATED → SUMMARY_READY → OUTPUT_EMITTED
- 遵循 **"强决策、弱配置"** 原则，少量强默认值 + 有限可调参数 + 关键安全行为不可轻易关闭
- 三层稳定性治理：Stable（核心闭环）/ Beta（可靠性增强）/ Experimental（高级实验特性，可单独关闭）

### 技术栈

`TypeScript` · `OpenClaw Plugin SDK` · `Zod` · `xxHash32` · `AST-Grep` · `JSON-RPC` · `SQLite` · `tmux`
