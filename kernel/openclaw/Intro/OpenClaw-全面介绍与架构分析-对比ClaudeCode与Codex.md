# OpenClaw 全面介绍与架构分析（对比 Claude Code / Codex）

## 1. OpenClaw 是什么

OpenClaw 是一个**自托管（self-hosted）的 AI 助手网关系统**。它的核心定位不是“某一个 IDE 里的编码助手”，而是“把 AI agent 接入多种消息入口 + 多端控制平面 + 设备节点能力”的统一中枢。

用一句话概括：

> OpenClaw = 多渠道消息网关 + Agent 运行时 + 会话/路由/权限治理层 + 控制台。

从官方文档和仓库介绍看，它的关键主张是：

- Any OS 部署（Linux/macOS 等）
- 多渠道接入（WhatsApp、Telegram、Discord、Signal、iMessage、WebChat 等）
- 单一 Gateway 统一管理连接、会话、路由与策略
- 面向 Agent 原生能力（工具调用、会话存储、多 agent 隔离、自动化、节点扩展）

---

## 2. 设计目标与产品边界

### 2.1 设计目标

OpenClaw 的目标不是替代 IDE，而是做“**个人/团队 AI 助手基础设施层**”：

1. **统一入口**：你在手机聊天软件、桌面控制台、Web UI 都能访问同一套 agent 系统。
2. **统一状态**：会话、路由、权限、自动化都在 Gateway 内集中治理。
3. **可控可扩展**：自托管、本地配置、插件化渠道、可接入节点能力（相机、位置、屏幕等）。
4. **多人格/多租户隔离**：多个 agentId 对应独立 workspace、会话存储和策略。

### 2.2 产品边界

OpenClaw 本身并不绑定单一模型厂商；它提供的是网关与运行时框架。

- 对上：接模型/Agent 运行时与工具体系
- 对下：接聊天渠道、设备节点、Web 控制面
- 中间：做会话管理、事件分发、认证鉴权、策略执行

---

## 3. OpenClaw 架构分析（重点）

## 3.1 总体架构

根据官方架构文档，OpenClaw 是一个**长生命周期 Gateway 进程**，通过 WebSocket 提供统一协议接口。

```text
[Chat Channels + Plugins]  ->
                            [Gateway (single source of truth)]
[Control UI / CLI / macOS] ->
[Nodes(iOS/Android/macOS)] ->
```

Gateway 同时承担：

- 渠道连接维护（各类 IM / 聊天入口）
- 控制平面 API（状态、会话、配置、自动化）
- Agent 运行编排（请求、流式事件、工具回传）
- 节点连接与命令调度（camera/location/screen/canvas 等）

## 3.2 协议层与连接生命周期

OpenClaw 的控制与数据流统一走 WS 文本帧 JSON 协议，首帧必须 `connect`，之后是 req/res/event 三类消息。

典型流程：

1. 客户端 `req:connect`
2. Gateway 返回 `res(ok)` + 初始快照
3. 客户端发起 `req:agent` 等请求
4. Gateway 流式推送 `event:agent` 并最终给出结束状态

关键价值：

- 协议统一（Web UI、CLI、节点都能挂到同一总线）
- 事件驱动（状态变化、流式输出天然适配）
- 可审计（会话与事件易记录）

## 3.3 核心组件拆解

### A) Gateway（守护进程）

- 渠道连接与生命周期管理
- JSON Schema 校验
- 事件广播（agent/chat/presence/health/heartbeat/cron）
- 鉴权与设备配对管理

### B) Agent Runtime

- OpenClaw 采用内嵌 agent runtime（文档描述为基于 pi-mono 派生）
- Workspace 作为默认工作目录
- Bootstrap 文件（AGENTS.md / SOUL.md / USER.md / TOOLS.md 等）注入上下文
- 工具调用、流式输出、会话落盘由 OpenClaw 侧编排

### C) Sessions（会话层）

- 每个 agent 拥有独立会话存储目录
- 会话 ID 稳定，支持历史与策略治理
- 队列模式（steer/followup/collect）支持并发输入下的可控行为

### D) Multi-Agent Routing（路由层）

- `agentId` 维度隔离 workspace / agentDir / session store
- 绑定规则支持 channel/accountId/peer/guild/team 等多维匹配
- 明确“最具体优先”的路由决策顺序

这套机制本质上是一个**内建的路由策略引擎**，很适合一个 Gateway 承载多人格、多账号、多场景。

### E) Control UI（控制平面）

Control UI 是 Gateway 同端口托管的前端，直连 WS；具备：

- 聊天、会话管理、中断运行
- 渠道状态、登录、配置下发
- cron 自动化管理
- 节点管理
- 配置编辑与生效、日志与调试

这意味着 OpenClaw 不是“纯 CLI 工具”，而是具备完整运维面的系统。

## 3.4 安全与治理模型（实用视角）

文档可见 OpenClaw 的治理粒度很细：

- Gateway token / password / tailscale 身份校验
- 新设备接入需要 pairing 审批（本地 loopback 可自动信任）
- 多 agent 可配置不同 sandbox 与 tools allow/deny
- side-effect 方法需要幂等键，降低重复执行风险

对生产化部署来说，这比“单机本地 coding CLI”更接近一个可长期运行的服务架构。

---

## 4. 与 Claude Code、Codex 的核心差异

> 先给结论：
> - **Claude Code / Codex** 更像“编码代理产品本体（开发者工作流工具）”。
> - **OpenClaw** 更像“跨渠道 AI 助手基础设施 + 编排控制层”。

## 4.1 定位差异

### OpenClaw

- 重心在“网关、路由、会话、渠道、节点、自动化治理”
- 关注“随时随地可访问 AI 助手”（手机 IM + Web + CLI）
- 可承载多个 agent/persona/account 隔离

### Claude Code

- 官方定位是 agentic coding tool
- 强调在 terminal / IDE / desktop / browser 的开发体验
- 关注代码库理解、编辑、执行命令、开发协作链路

### Codex（OpenAI）

- 官方页面强调 “One agent for everywhere you code”
- 生态覆盖 Codex App / CLI / IDE / workflows 等
- 核心仍围绕编码生产力与工程流程

## 4.2 架构层差异

| 维度 | OpenClaw | Claude Code | Codex |
|---|---|---|---|
| 主体架构 | 长驻 Gateway（WS 事件总线） | 以 coding agent 交互面为主 | 以 coding agent 平台能力为主 |
| 多渠道 IM 接入 | 强（WhatsApp/Telegram/Discord...） | 非主目标 | 非主目标 |
| 多 agent 路由 | 内建并可精细绑定 | 不是核心卖点 | 有 multi-agent/workflow 概念，但不是 IM 路由中枢 |
| 设备节点能力 | 有（camera/location/screen/canvas） | 不是核心 | 非核心 |
| 控制平面运维 | 强（Control UI + config + cron + logs） | 偏开发者工具面 | 偏开发者工具与平台面 |
| 适合场景 | 个人 AI 中台、团队 AI 入口编排、跨设备协同 | 代码开发/重构/提效 | 代码开发与自动化流水线 |

## 4.3 交互入口差异

- **OpenClaw**：消息应用是第一入口之一；终端只是入口之一。
- **Claude Code / Codex**：终端、IDE、Web 是主入口，消息渠道不是主路径。

## 4.4 可运维性差异

OpenClaw 对“持续运行 + 多端连接 + 多账号治理”考虑更重：

- 设备配对审批
- 网关鉴权策略
- 会话与路由统一治理
- 定时任务（cron）与节点指令

Claude Code / Codex 则更关注“开发任务闭环”本身：

- 代码理解 → 编辑 → 命令执行 → 审批/工作流集成

---

## 5. 适用场景建议

## 5.1 什么时候优先 OpenClaw

- 你要把 AI 助手接进多个聊天平台，手机随时可用
- 你要一个“个人 AI 中枢”而不是单一 IDE 插件
- 你要多 agent/persona/账号隔离与路由策略
- 你要把设备能力（相机、定位、屏幕）纳入自动化链路

## 5.2 什么时候优先 Claude Code / Codex

- 你的核心目标是“写代码效率最大化”
- 主要工作流发生在 terminal/IDE/CI
- 不需要自建多渠道消息网关与设备节点体系

## 5.3 组合策略（推荐）

对高级用户，最佳实践往往是：

- 用 **OpenClaw** 做入口与编排（消息触发、会话治理、路由、自动化）
- 把具体 coding heavy task 交给 **Claude Code / Codex**（或 ACP agent）执行

即：

> OpenClaw 负责“系统级调度”，Claude Code/Codex 负责“编码级执行”。

---

## 6. 架构优缺点（客观评估）

## 6.1 OpenClaw 优势

1. **体系完整**：网关 + 控制台 + 会话 + 路由 + 节点 + 自动化。
2. **入口天然广**：聊天渠道优先，移动场景友好。
3. **隔离能力强**：multi-agent + per-agent workspace/会话/策略。
4. **自托管可控**：数据、策略、权限、审计都可本地化。

## 6.2 OpenClaw 代价

1. **系统复杂度更高**：配置与运维心智成本高于单工具 CLI。
2. **部署责任在自己**：稳定性、安全、升级都要自己兜底。
3. **生态成熟度依赖社区迭代**：需要持续跟进版本与文档。

## 6.3 Claude Code / Codex 优势

1. **coding 体验聚焦**：对开发任务路径更短。
2. **工具链整合强**：IDE、CLI、CI 集成清晰。
3. **上手快**：对“只想写代码”的用户摩擦小。

## 6.4 Claude Code / Codex 代价

1. **不以多渠道消息网关为核心**。
2. **不天然提供 OpenClaw 这种统一路由编排中枢**。
3. **跨设备/跨消息渠道治理能力通常需外部系统补齐**。

---

## 7. 一句话结论

如果你要的是“一个能在手机/聊天软件里长期在线、可路由、可自动化、可治理的 AI 助手系统”，OpenClaw 的架构更对路；如果你要的是“最短路径完成编码任务”，Claude Code/Codex 更直接。实际落地里，二者并不冲突，分层组合是最强方案。

---

## 8. 参考资料（网络 + 本地文档）

### OpenClaw
- 官方文档首页: https://docs.openclaw.ai/
- 架构文档（Gateway Architecture）: https://docs.openclaw.ai/concepts/architecture
- Multi-Agent Routing: https://docs.openclaw.ai/concepts/multi-agent
- Agent Runtime: https://docs.openclaw.ai/concepts/agent
- Control UI: https://docs.openclaw.ai/web/control-ui
- Features: https://docs.openclaw.ai/concepts/features
- GitHub 仓库: https://github.com/openclaw/openclaw

### Claude Code
- Overview: https://code.claude.com/docs/en/overview
- Quickstart: https://code.claude.com/docs/en/quickstart

### Codex
- OpenAI Codex 首页: https://developers.openai.com/codex
- OpenAI Codex CLI 仓库: https://github.com/openai/codex
