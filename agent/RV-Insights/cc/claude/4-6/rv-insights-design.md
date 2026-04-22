# RV-Insights：基于双 SDK 混合架构的多 Agent RISC-V 开源贡献平台设计方案

> 版本：v2.2（全面完善版）  
> 日期：2026-04-22  
> 模型：Claude Opus 4.6  
> 定位：面向 RISC-V 开源软件贡献的大模型驱动多 Agent 平台，采用 Claude Agent SDK + OpenAI Agents SDK 混合架构

---

## 目录

1. [项目概述](#1-项目概述)
   - 1.1 核心流程
   - 1.2 与现有工具的对比分析
2. [SDK 技术分析与选型决策](#2-sdk-技术分析与选型决策)
3. [混合架构总体设计](#3-混合架构总体设计)
   - 3.6 并发控制与资源调度
   - 3.7 API 接口设计
4. [五层 Agent 节点详细设计](#4-五层-agent-节点详细设计)
   - 4.6 Prompt 工程管理
5. [工作流状态机与人工审核机制](#5-工作流状态机与人工审核机制)
   - 5.4 通知与协作机制
   - 5.5 优雅停机与资源清理
6. [开发-审核迭代闭环设计](#6-开发-审核迭代闭环设计)
   - 6.4 最终产物格式与提交流程
7. [MCP 工具层设计](#7-mcp-工具层设计)
8. [RISC-V 领域知识库设计](#8-risc-v-领域知识库设计)
   - 8.4 知识摄入流水线
9. [可观测性设计](#9-可观测性设计)
   - 9.4 成本控制与预算管理
10. [安全设计](#10-安全设计)
11. [数据模型与状态持久化](#11-数据模型与状态持久化)
12. [部署架构](#12-部署架构)
    - 12.6 配置管理
    - 12.7 Schema 迁移策略
13. [MVP 范围与实施路线](#13-mvp-范围与实施路线)
14. [风险与缓解](#14-风险与缓解)
- [附录 A：项目目录结构](#附录-a项目目录结构)
- [附录 B：CLI 接口设计](#附录-bcli-接口设计)
- [附录 C：SDK 选型决策矩阵](#附录-csdk-选型决策矩阵)
- [附录 D：平台自身测试策略](#附录-d平台自身测试策略)
- [附录 E：参考资料](#附录-e参考资料)

---

## 1. 项目概述

### 1.1 目标

RV-Insights 是一个面向 RISC-V 开源软件生态的多 Agent 贡献平台。平台编排五个专业化 Agent 节点——探索、规划、开发、审核、测试——形成从"发现贡献机会"到"输出可验证补丁"的完整闭环。

核心约束：

- 每个阶段输出后必须停顿，接受人工审核，通过后才进入下一阶段
- 开发 Agent 与审核 Agent 进行多轮迭代，直到审核 Agent 认定合理
- 开发层由 Claude Code 承担，审核层由 OpenAI Codex 承担
- 所有产物可追溯、可审计、可回放

### 1.2 设计原则

1. **人始终在环（Human-in-the-Loop）**：每个阶段完成后必须暂停等待人工审批，高风险操作（如向上游提交）绝不自动执行。
2. **证据优先（Evidence-First）**：探索必须附带来源链接，审核必须引用具体代码行，测试必须输出可复现的日志——不接受无证据的结论。
3. **最小影响（Minimal Blast Radius）**：每个贡献案例只做一件事，一个 patch 只解决一个问题，避免跨模块大补丁。
4. **可恢复（Recoverable）**：任意阶段支持暂停、恢复、驳回、重试和回流，任何中断都不丢失已完成的工作。
5. **可审计（Auditable）**：所有 Agent 调用、工具执行、人工决策都落库，形成不可篡改的审计链。
6. **SDK 各取所长（Best-of-Both）**：不强求单一 SDK 覆盖所有场景，而是让每个 Agent 使用最适合其任务特征的 SDK。
7. **渐进式自动化（Progressive Automation）**：初期人工审核严格，随着信任积累逐步放宽低风险操作的自动化程度。

### 1.3 非目标

- 不追求完全无人值守的自动贡献——人工审核是设计核心，不是临时妥协
- 不在 MVP 阶段覆盖所有 RISC-V 仓库——优先 1-2 个高价值试点
- 不替代项目维护者的最终合入决策——平台只输出"贡献就绪产物"
- 不构建通用 Agent 框架——平台是面向 RISC-V 贡献的垂直解决方案
- 不在首期实现 Web Console——CLI 入口优先，UI 后置

### 1.4 Agent 流水线

```
用户输入 / 邮件列表 / 代码库
        │
        ▼
  ┌─────────────┐
  │  探索 Agent  │ ← 自主发现 + 可行性验证
  └──────┬──────┘
         │ 人工审核 ✓
         ▼
  ┌─────────────┐
  │  规划 Agent  │ ← 开发方案 + 测试方案
  └──────┬──────┘
         │ 人工审核 ✓
         ▼
  ┌─────────────────────────────────┐
  │  开发 Agent ⇄ 审核 Agent 迭代   │ ← 多轮生成-审查循环
  │  (Claude Code)  (OpenAI Codex)  │
  └──────┬──────────────────────────┘
         │ 人工审核 ✓
         ▼
  ┌─────────────┐
  │  测试 Agent  │ ← 环境搭建 + 测试执行 + 结果输出
  └──────┬──────┘
         │ 人工审核 ✓
         ▼
    贡献就绪产物
```

### 1.2 与现有工具的对比分析

| 维度 | SWE-Agent | Aider | OpenDevin | RV-Insights |
|------|-----------|-------|-----------|-------------|
| 定位 | 通用 SWE 任务 | 结对编程 | 通用 AI 开发者 | RISC-V 领域贡献 |
| Agent 架构 | 单 Agent + 工具 | 单 Agent + 编辑器 | 多 Agent（规划+执行） | 5 层 Agent + 人工门禁 |
| 模型支持 | 单模型 | 单模型 | 单模型 | 双 SDK 混合（Claude + OpenAI） |
| 人工介入 | 无 | 实时交互 | 有限 | 每阶段强制人工审核 |
| 领域知识 | 无 | 无 | 无 | RAG 知识库（RISC-V Spec + 内核文档） |
| 审核机制 | 无 | 无 | 自审 | 独立审核 Agent + 迭代闭环 |
| 产物格式 | PR/Patch | 本地编辑 | PR | 内核邮件列表格式 patch |
| 测试验证 | 运行已有测试 | 无 | 运行已有测试 | 专用测试 Agent + QEMU 交叉验证 |

**为什么不扩展现有方案**：

1. **领域特殊性**：RISC-V 内核贡献需要交叉编译、QEMU 验证、`checkpatch.pl` 合规——通用工具不覆盖这些
2. **质量门禁**：内核社区对补丁质量要求极高，需要多轮 AI 审核 + 人工审核的迭代闭环，现有工具缺乏这种机制
3. **双模型优势**：Claude 的文件操作能力 + OpenAI 的编排能力，单 SDK 方案无法兼得
4. **邮件列表工作流**：内核贡献走 `git send-email` 而非 GitHub PR，现有工具都假设 PR 工作流

---

## 2. SDK 技术分析与选型决策

### 2.1 Claude Agent SDK 架构深度解析

Claude Agent SDK 的核心架构是**子进程模型**——它不在 Python 进程内运行推理，而是 spawn Claude Code CLI 作为子进程，通过 stdin/stdout 的 JSON 控制协议通信：

```
Python 应用
  └── ClaudeSDKClient / query()
       └── SubprocessCLITransport
            └── spawns `claude` CLI binary（pip wheel 内置）
                 ├── stdin  ← JSON 控制消息（prompt, permissions, interrupt）
                 └── stdout → JSON 响应消息（assistant, tool_use, result）
```

核心 API 原语：

- `query()`：无状态、一次性调用，适合简单任务
- `ClaudeSDKClient`：有状态、双向交互，支持自定义工具、hooks、中断、权限模式切换
- `ClaudeAgentOptions`：配置中心，包含 `tools`、`allowed_tools`、`mcp_servers`、`permission_mode`、`max_turns`、`max_budget_usd`、`can_use_tool`、`session_store`、`sandbox`、`thinking` 等 30+ 配置项
- `AgentDefinition`：子 Agent 定义，支持独立的 model、tools、permissions、maxTurns
- `SessionStore`：会话持久化协议，支持 S3/Redis/PostgreSQL 适配器
- `@tool` + `create_sdk_mcp_server()`：进程内 MCP Server，Python 函数直接暴露为工具

消息类型体系：`AssistantMessage`、`UserMessage`、`SystemMessage`、`ResultMessage`（含 cost/duration/session_id）、`TaskStartedMessage`/`TaskProgressMessage`/`TaskNotificationMessage`（子 Agent 生命周期）、`RateLimitEvent`。

内容块类型：`TextBlock`、`ToolUseBlock`、`ToolResultBlock`、`ThinkingBlock`、`ServerToolUseBlock`、`ServerToolResultBlock`。

### 2.2 OpenAI Agents SDK 架构深度解析

OpenAI Agents SDK 是**库原生模型**——agent loop 在 Python 进程内运行，直接调用 OpenAI API：

```
Python 应用
  └── Runner.run(agent, input)
       └── Agent Loop（Python 进程内）
            ├── LLM 调用 → OpenAI API（HTTP）
            ├── Tool 执行 → 本地 Python 函数
            ├── Handoff → 切换到另一个 Agent
            └── Guardrail → 输入/输出校验
```

核心 API 原语：

- `Agent(name, instructions, tools, handoffs, model, output_type, guardrails)`：Agent 定义，声明式配置
- `Runner.run()` / `Runner.run_sync()` / `Runner.run_streamed()`：Agent 执行器，管理 agent loop
- `handoff(target_agent)`：Agent 间控制权转移，支持条件 handoff 和 handoff 过滤器
- `@function_tool`：工具定义装饰器，自动从 Python 类型签名生成 JSON Schema
- `@input_guardrail` / `@output_guardrail`：输入/输出校验，`tripwire_triggered=True` 时中断执行
- `Tracing`：内置追踪系统，自动记录 agent span、tool span、handoff span，支持 OpenTelemetry 导出
- `RunConfig`：运行时配置，包含 `model_provider`（支持 Custom Model Provider 接入任意 LLM）

多 Agent 编排模式：
- **Delegation（委托）**：Manager Agent 通过 handoff 将子任务分发给专业 Agent
- **Sequential（顺序）**：Agent A 完成后 handoff 给 Agent B，形成流水线
- **Parallel（并行）**：通过工具调用并行启动多个 Agent（非原生，需自行编排）

### 2.3 两个 SDK 的架构本质差异

| 维度 | Claude Agent SDK | OpenAI Agents SDK |
|------|-----------------|-------------------|
| 架构模型 | **子进程模型**：spawns Claude Code CLI 作为子进程，通过 stdin/stdout JSON 协议通信 | **库原生模型**：在 Python 进程内直接调用 API，agent loop 在用户代码中运行 |
| 内置工具 | 完整的 Claude Code 工具集（Read/Write/Edit/Bash/Grep/Glob/WebFetch 等） | 无内置工具，所有工具需用户通过 `@function_tool` 自行定义 |
| 多 Agent | 层级委托模型：主 Agent 通过 `AgentDefinition` 定义子 Agent，按需拉起 | **Handoff 模型**：Agent 之间通过 `handoff()` 进行控制权转移，支持对等通信 |
| 工具协议 | **MCP 原生支持**：同时支持外部 MCP Server（子进程）和 SDK MCP Server（进程内） | 通过 `mcp` extra 支持外部 MCP Server，无进程内 MCP |
| 人工介入 | `can_use_tool` 回调：拦截每个工具调用，支持修改输入、拒绝、中断 | **Guardrails**：输入/输出过滤器 + `input_filter`/`output_filter` |
| 会话持久化 | `SessionStore` 协议（S3/Redis/Postgres 适配器） | 无内置持久化 |
| 沙箱 | 内置沙箱设置（文件系统、网络隔离） | 无内置沙箱 |
| 可观测性 | 通过 hooks 和消息流 | **内置 Tracing**：原生追踪系统，支持 OpenTelemetry |
| 模型绑定 | 绑定 Claude 模型族（Opus/Sonnet/Haiku） | 默认绑定 OpenAI 模型，但支持 **Custom Model Provider** 接入任意 LLM |
| 编排能力 | 适合"给一个任务，让 Agent 自主完成"的场景 | 适合"精确控制 Agent 间协作流程"的场景 |
| 核心优势 | **代码操作能力无出其右**：文件读写、代码编辑、终端执行、Git 操作一体化 | **编排灵活性最强**：Handoff + Guardrails + Tracing 构成完整的生产级编排原语 |

### 2.4 两个 SDK 能否结合使用？

**可以，且推荐结合使用。** 两个 SDK 是完全独立的 Python 包，无依赖冲突：

```python
# 同一项目中同时使用
from claude_agent_sdk import query as claude_query, ClaudeAgentOptions
from agents import Agent, Runner

async def hybrid_workflow():
    # Claude Agent SDK：代码分析（利用内置文件工具）
    async for msg in claude_query(
        prompt="分析 src/arch/riscv/ 目录的代码结构",
        options=ClaudeAgentOptions(allowed_tools=["Read", "Grep", "Glob"]),
    ):
        analysis = extract_text(msg)

    # OpenAI Agents SDK：结构化决策
    reviewer = Agent(name="reviewer", instructions="基于分析结果评估可行性")
    result = await Runner.run(reviewer, input=analysis)
```

关键考量：
- Claude Agent SDK 每个会话 spawn 一个子进程，资源开销较大，适合需要文件系统/代码执行的重型任务
- OpenAI Agents SDK 直接 API 调用，轻量级，适合纯推理/决策/审查任务
- 两者通过 Python 层面的数据传递（字符串/JSON）即可互通，无需额外协议

### 2.5 各 Agent 节点的 SDK 选型与理由

| Agent 节点 | 选用 SDK | 理由 |
|-----------|---------|------|
| **探索 Agent** | OpenAI Agents SDK | 探索任务以信息检索和结构化分析为主，需要 Handoff 在多个子 Agent（邮件列表爬取、代码库分析、可行性验证）之间灵活切换。Guardrails 可防止幻觉输出。不需要直接操作文件系统。 |
| **规划 Agent** | OpenAI Agents SDK | 规划是纯推理任务，需要将探索结果转化为结构化方案。Guardrails 确保输出符合预定义 schema。Tracing 记录规划推理链路。无文件操作需求。 |
| **开发 Agent** | **Claude Agent SDK** | 开发是本平台最核心的重型任务。Claude Code 的内置工具集（Read/Write/Edit/Bash/Grep/Git）是不可替代的优势——无需从零构建代码操作工具链。`can_use_tool` 回调提供细粒度的操作审批。MCP 原生支持可接入自定义工具。 |
| **审核 Agent** | OpenAI Agents SDK | 审核是结构化评判任务，需要输出标准化的 review findings。Guardrails 确保审核意见格式一致。通过 Custom Model Provider 可接入 OpenAI Codex 或其他模型。Handoff 支持将不同类型的审核（安全/性能/风格）分发给专门子 Agent。 |
| **测试 Agent** | **Claude Agent SDK** | 测试需要搭建环境、执行命令、读取日志——这些都是 Claude Code 内置工具的强项。Bash 工具可直接执行测试命令，Read 工具可解析测试输出。沙箱设置提供安全隔离。 |

### 2.6 选型决策总结

```
┌─────────────────────────────────────────────────────────┐
│                    Python 编排层                         │
│              (asyncio + 状态机 + 人工审核)                │
├──────────────────────┬──────────────────────────────────┤
│  OpenAI Agents SDK   │       Claude Agent SDK           │
│  ┌────────────────┐  │  ┌────────────────────────────┐  │
│  │ 探索 Agent     │  │  │ 开发 Agent (Claude Code)   │  │
│  │ · Handoff 编排  │  │  │ · Read/Write/Edit/Bash     │  │
│  │ · Guardrails   │  │  │ · MCP 工具                  │  │
│  │ · Tracing      │  │  │ · can_use_tool 审批         │  │
│  ├────────────────┤  │  ├────────────────────────────┤  │
│  │ 规划 Agent     │  │  │ 测试 Agent (Claude Code)   │  │
│  │ · 结构化输出    │  │  │ · Bash 执行测试             │  │
│  │ · Guardrails   │  │  │ · Read 解析结果             │  │
│  ├────────────────┤  │  │ · 沙箱隔离                  │  │
│  │ 审核 Agent     │  │  └────────────────────────────┘  │
│  │ · Codex 模型    │  │                                  │
│  │ · Handoff 分发  │  │                                  │
│  │ · Guardrails   │  │                                  │
│  └────────────────┘  │                                  │
└──────────────────────┴──────────────────────────────────┘
```

选型原则：**需要操作文件系统和执行代码的 Agent 用 Claude Agent SDK，纯推理和结构化决策的 Agent 用 OpenAI Agents SDK。** 这不是折中，而是各取所长。

---

## 3. 混合架构总体设计

### 3.1 架构总览图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         用户交互层 (User Interface)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │  Web Console  │  │  CLI 入口     │  │  API Gateway (FastAPI)       │  │
│  │  (审核/干预)   │  │  (开发者)     │  │  (会话管理 + SSE 事件流)      │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┬───────────────┘  │
└─────────┼──────────────────┼────────────────────────┼──────────────────┘
          │                  │                        │
          ▼                  ▼                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    编排与状态管理层 (Orchestration)                       │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │              Pipeline State Machine (Python asyncio)             │    │
│  │                                                                  │    │
│  │  EXPLORING ──▶ PLANNING ──▶ DEVELOPING ──▶ REVIEWING ──▶ TESTING │    │
│  │      │            │            │     ▲         │           │      │    │
│  │      ▼            ▼            │     │         ▼           ▼      │    │
│  │  [人工审核]    [人工审核]       └─────┘     [人工审核]   [人工审核]  │    │
│  │                              迭代闭环                             │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │ Human Gate Svc   │  │ Audit Logger     │  │ Session Store        │  │
│  │ (审批/驳回/注释)  │  │ (全链路审计)      │  │ (PostgreSQL/Redis)   │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
          │                                           │
          ▼                                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Agent 能力层 (Agent Capabilities)                   │
│                                                                         │
│  ┌─── OpenAI Agents SDK ────────────┐  ┌─── Claude Agent SDK ────────┐ │
│  │                                   │  │                             │ │
│  │  ┌───────────┐  ┌───────────┐    │  │  ┌───────────────────────┐  │ │
│  │  │ 探索Agent │  │ 规划Agent │    │  │  │ 开发Agent             │  │ │
│  │  │           │  │           │    │  │  │ (Claude Code CLI)     │  │ │
│  │  │ Handoff:  │  │ Output:   │    │  │  │ Read/Write/Edit/Bash  │  │ │
│  │  │ ·邮件爬取  │  │ ·开发方案  │    │  │  │ MCP 自定义工具        │  │ │
│  │  │ ·代码分析  │  │ ·测试方案  │    │  │  │ can_use_tool 审批     │  │ │
│  │  │ ·可行性    │  │ ·风险评估  │    │  │  ├───────────────────────┤  │ │
│  │  │  验证     │  │           │    │  │  │ 测试Agent             │  │ │
│  │  ├───────────┤  └───────────┘    │  │  │ (Claude Code CLI)     │  │ │
│  │  │ 审核Agent │                   │  │  │ Bash 执行 + 日志解析   │  │ │
│  │  │ (Codex)   │                   │  │  │ 沙箱隔离              │  │ │
│  │  │ Guardrails│                   │  │  └───────────────────────┘  │ │
│  │  │ Tracing   │                   │  │                             │ │
│  │  └───────────┘                   │  │                             │ │
│  └───────────────────────────────────┘  └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
          │                                           │
          ▼                                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        工具与基础设施层 (Tools & Infra)                   │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ MCP Server   │  │ MCP Server   │  │ MCP Server   │  │ MCP Server │ │
│  │ 邮件列表检索  │  │ 代码库工具    │  │ RISC-V 知识库 │  │ 测试框架   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ PostgreSQL   │  │ Redis        │  │ MinIO/S3     │  │ Vector DB  │ │
│  │ (状态/审计)   │  │ (缓存/队列)   │  │ (产物存储)    │  │ (RAG 检索) │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 数据流全景

```
                    用户输入 / 外部事件
                           │
                           ▼
              ┌────────────────────────┐
              │     Pipeline Engine     │
              │   (Python asyncio)      │
              └────────┬───────────────┘
                       │
         ┌─────────────┼─────────────────────────────────┐
         │             │                                   │
         ▼             ▼                                   ▼
   OpenAI Agents  OpenAI Agents                    Claude Agent
   SDK Process    SDK Process                      SDK Subprocess
   (探索Agent)    (规划/审核Agent)                  (开发/测试Agent)
         │             │                                   │
         │  HTTP API   │  HTTP API              stdin/stdout JSON
         │  调用        │  调用                    协议通信
         ▼             ▼                                   ▼
   OpenAI API     OpenAI API                        Claude Code CLI
   (GPT-4o/       (Codex/                           (Opus/Sonnet)
    o3-mini)       GPT-4o)                               │
                                                         │
                                              内置工具执行层
                                              Read/Write/Edit
                                              Bash/Grep/Glob
                                              MCP Server 调用
```

### 3.3 跨 SDK 通信机制

两个 SDK 之间不需要直接通信。编排层（Python asyncio）作为中介，通过结构化数据（Pydantic 模型）在 Agent 之间传递上下文。

核心通信数据流：

```
Explorer ──ExplorationResult──▶ Planner ──ExecutionPlan──▶ Developer
                                                              │
                                                    DevelopmentResult
                                                              │
                                                              ▼
                                                          Reviewer
                                                              │
                                                        ReviewVerdict
                                                              │
                                              ┌───────────────┴───────────────┐
                                              │                               │
                                        approved=false                  approved=true
                                              │                               │
                                              ▼                               ▼
                                     Developer (修复)                     Tester
                                                                             │
                                                                        TestResult
```

所有跨 Agent 数据契约的完整 Pydantic 模型定义见 [Section 4.0](#40-agent-间数据契约完整-pydantic-模型)。这些模型是跨 SDK 通信的**唯一依据**——两个 SDK 的 Agent 只通过 Python 编排层传递这些模型的 JSON 序列化形式，无需任何额外协议。

### 3.4 跨 SDK 适配器层

为了隔离两个 SDK 的差异，编排层通过统一的 `AgentAdapter` 接口与各 Agent 交互：

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator

class AgentAdapter(ABC):
    """统一 Agent 适配器接口，屏蔽 SDK 差异"""

    @abstractmethod
    async def execute(self, input_data: BaseModel) -> BaseModel:
        """执行 Agent 任务，返回结构化结果"""

    @abstractmethod
    async def execute_streaming(self, input_data: BaseModel) -> AsyncIterator[str]:
        """流式执行，用于实时展示进度"""

    @abstractmethod
    async def get_cost(self) -> float:
        """返回本次执行的 API 成本（USD）"""

    @abstractmethod
    async def get_trace_id(self) -> str:
        """返回可追踪的执行 ID"""


class ClaudeAgentAdapter(AgentAdapter):
    """Claude Agent SDK 适配器（开发/测试 Agent）"""

    def __init__(self, options: ClaudeAgentOptions):
        self.options = options
        self._last_result: ResultMessage | None = None

    async def execute(self, input_data: BaseModel) -> BaseModel:
        result_text = ""
        async with ClaudeSDKClient(options=self.options) as client:
            await client.query(input_data.model_dump_json())
            async for msg in client.receive_response():
                if isinstance(msg, ResultMessage):
                    self._last_result = msg
                result_text += extract_text(msg)
        return parse_structured_output(result_text)

    async def get_cost(self) -> float:
        return self._last_result.cost_usd if self._last_result else 0.0

    async def get_trace_id(self) -> str:
        return self._last_result.session_id if self._last_result else ""


class OpenAIAgentAdapter(AgentAdapter):
    """OpenAI Agents SDK 适配器（探索/规划/审核 Agent）"""

    def __init__(self, agent: Agent):
        self.agent = agent
        self._last_result = None

    async def execute(self, input_data: BaseModel) -> BaseModel:
        result = await Runner.run(self.agent, input=input_data.model_dump_json())
        self._last_result = result
        return result.final_output

    async def get_cost(self) -> float:
        return sum(u.total_tokens * 0.00001 for u in self._last_result.raw_responses)

    async def get_trace_id(self) -> str:
        return self._last_result.trace_id if self._last_result else ""
```

### 3.5 错误处理与重试策略

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class AgentExecutionError(Exception):
    """Agent 执行失败"""
    def __init__(self, agent: str, phase: str, cause: str, recoverable: bool = True):
        self.agent = agent
        self.phase = phase
        self.cause = cause
        self.recoverable = recoverable

class APIRateLimitError(AgentExecutionError):
    """API 速率限制"""

class APIUnavailableError(AgentExecutionError):
    """API 服务不可用"""

class AgentTimeoutError(AgentExecutionError):
    """Agent 执行超时"""

# 重试策略：针对可恢复错误自动重试
RETRY_POLICY = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=10, max=120),
    retry=retry_if_exception_type((APIRateLimitError, APIUnavailableError)),
    before_sleep=lambda state: audit_log.record_retry(state),
)

# 超时策略
AGENT_TIMEOUTS = {
    "explorer": 300,     # 5 分钟
    "planner": 180,      # 3 分钟
    "developer": 600,    # 10 分钟（代码生成耗时长）
    "reviewer": 180,     # 3 分钟
    "tester": 900,       # 15 分钟（含环境搭建和测试执行）
}

# 模型降级策略
MODEL_FALLBACK_CHAIN = {
    "claude-opus-4-6": ["claude-sonnet-4-6", "claude-haiku-4-5"],
    "gpt-4o": ["gpt-4o-mini"],
    "o3-mini": ["gpt-4o-mini"],
}
```

### 3.6 并发控制与资源调度

多个贡献案例可能同时运行，需要对 SDK 资源进行统一调度：

```python
import asyncio
from dataclasses import dataclass, field

@dataclass
class WorkerPoolConfig:
    claude_max_concurrent: int = 2      # Claude CLI 子进程上限（每个 ~200MB）
    openai_max_concurrent: int = 10     # OpenAI API 并发上限（轻量级）
    qemu_max_concurrent: int = 1        # QEMU 实例上限（每个 2-4GB）
    max_cases_parallel: int = 3         # 同时运行的案例上限

class ResourceScheduler:
    """跨案例资源调度器"""

    def __init__(self, config: WorkerPoolConfig):
        self.config = config
        self._claude_sem = asyncio.Semaphore(config.claude_max_concurrent)
        self._openai_sem = asyncio.Semaphore(config.openai_max_concurrent)
        self._qemu_sem = asyncio.Semaphore(config.qemu_max_concurrent)
        self._case_sem = asyncio.Semaphore(config.max_cases_parallel)

    async def acquire_claude(self, case_id: str, agent: str) -> None:
        """获取 Claude CLI 子进程槽位（阻塞直到可用）"""
        await self._claude_sem.acquire()
        await self.audit_log.record(case_id, f"{agent}_resource_acquired", "claude_slot")

    def release_claude(self) -> None:
        self._claude_sem.release()

    async def acquire_openai(self) -> None:
        await self._openai_sem.acquire()

    def release_openai(self) -> None:
        self._openai_sem.release()

    async def acquire_qemu(self, case_id: str) -> None:
        await self._qemu_sem.acquire()
        await self.audit_log.record(case_id, "qemu_resource_acquired", "qemu_slot")

    def release_qemu(self) -> None:
        self._qemu_sem.release()
```

**API Rate Limit 共享策略**：

| SDK | Rate Limit 机制 | 跨案例共享方式 |
|-----|----------------|--------------|
| Claude Agent SDK | SDK 内置 `RateLimitEvent` 消息 | `ResourceScheduler` 信号量 + 指数退避 |
| OpenAI Agents SDK | HTTP 429 响应 + `Retry-After` | 全局 `httpx.AsyncClient` 共享连接池 + `tenacity` 重试 |

**调度优先级**：

1. 已进入开发-审核迭代的案例优先（避免浪费已消耗的 token）
2. 高优先级案例（`priority: "critical"/"high"`）优先
3. 等待时间最长的案例优先（防止饥饿）

### 3.7 API 接口设计

FastAPI Gateway 提供 RESTful API，支持 CLI 和 Web Console 接入：

```python
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer
from sse_starlette.sse import EventSourceResponse

app = FastAPI(title="RV-Insights API", version="0.1.0")
security = HTTPBearer()

# ── 案例管理 ──

@app.post("/api/v1/cases", response_model=CaseResponse, status_code=201)
async def create_case(req: CreateCaseRequest, token=Depends(security)):
    """创建新的贡献案例并启动流水线"""

@app.get("/api/v1/cases/{case_id}", response_model=CaseDetailResponse)
async def get_case(case_id: str, token=Depends(security)):
    """获取案例详情（含各阶段产物）"""

@app.get("/api/v1/cases", response_model=CaseListResponse)
async def list_cases(
    status: str | None = None,
    page: int = 1, limit: int = 20,
    token=Depends(security),
):
    """列出案例（支持按状态过滤和分页）"""

@app.get("/api/v1/cases/{case_id}/events")
async def case_events(case_id: str, token=Depends(security)):
    """SSE 事件流：实时推送案例状态变更和 Agent 输出"""
    return EventSourceResponse(stream_case_events(case_id))

# ── 人工审核 ──

@app.get("/api/v1/reviews/pending", response_model=PendingReviewsResponse)
async def list_pending_reviews(token=Depends(security)):
    """列出所有待审核项"""

@app.post("/api/v1/reviews/{case_id}/{phase}", response_model=ReviewResponse)
async def submit_review(
    case_id: str, phase: str,
    req: SubmitReviewRequest,
    token=Depends(security),
):
    """提交审核决策（approve/reject/reject_to/abandon/modify）"""

# ── 知识库 ──

@app.get("/api/v1/knowledge/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(q: str, category: str | None = None, limit: int = 10):
    """搜索知识库"""

# ── 系统管理 ──

@app.get("/api/v1/system/health")
async def health_check():
    """健康检查（含各组件状态）"""

@app.get("/api/v1/system/metrics")
async def system_metrics(token=Depends(security)):
    """系统指标（成本、Token 消耗、Agent 性能）"""
```

**认证方式**：Bearer Token（JWT），MVP 阶段使用静态 token，后续接入 OAuth2。

**请求/响应约定**：

```python
class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: str | None = None
    meta: PaginationMeta | None = None

class PaginationMeta(BaseModel):
    total: int
    page: int
    limit: int
    has_next: bool
```

### 4.0 Agent 间数据契约（完整 Pydantic 模型）

以下模型定义了所有 Agent 之间的数据传递契约，是跨 SDK 通信的唯一依据：

```python
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

# ── 输入上下文 ──

class InputSource(str, Enum):
    USER = "user"                    # 用户手动输入
    MAILING_LIST = "mailing_list"    # 邮件列表监控
    ISSUE_TRACKER = "issue_tracker"  # Issue 跟踪器
    CODE_SCAN = "code_scan"          # 代码扫描
    CI_FAILURE = "ci_failure"        # CI 失败事件

class InputContext(BaseModel):
    source: InputSource
    raw_content: str
    repo_url: str
    target_branch: str = "master"
    user_hint: str | None = None     # 用户提供的方向性提示
    priority: str = "normal"         # "low" | "normal" | "high" | "critical"
    metadata: dict = {}

# ── 探索层输出 ──

class EvidenceItem(BaseModel):
    type: str                        # "mailing_list_url" | "commit_hash" | "issue_url" | "code_snippet"
    url: str | None = None
    content: str
    relevance: float                 # 0.0 - 1.0

class ExplorationResult(BaseModel):
    opportunity_id: str
    title: str
    source: InputSource
    description: str
    feasibility_score: float         # 0.0 - 1.0
    evidence: list[EvidenceItem]
    affected_files: list[str]
    affected_subsystem: str          # "arch/riscv" | "drivers" | "mm" | ...
    risk_level: str                  # "low" | "medium" | "high"
    estimated_loc: int               # 预估修改行数
    upstream_status: str             # "no_existing_work" | "wip_by_others" | "stale_attempt"
    community_receptiveness: str     # "likely_accept" | "needs_discussion" | "controversial"

# ── 规划层输出 ──

class DevStep(BaseModel):
    order: int
    description: str
    target_files: list[str]
    depends_on: list[int] = []       # 依赖的步骤序号
    reference_docs: list[str] = []   # 需要参考的规范/文档
    estimated_loc: int

class DevPlan(BaseModel):
    steps: list[DevStep]
    coding_style_notes: str          # 目标仓库的编码规范要点
    commit_message_template: str
    total_estimated_loc: int

class TestCase(BaseModel):
    id: str
    type: str                        # "build" | "unit" | "integration" | "performance" | "boot"
    description: str
    command: str                     # 具体执行命令
    expected_outcome: str
    timeout_seconds: int = 300
    environment: str                 # "host" | "qemu_rv64" | "qemu_rv32" | "cross_compile"

class TestPlan(BaseModel):
    cases: list[TestCase]
    environment_setup: list[str]     # 环境搭建命令序列
    required_tools: list[str]        # 需要的工具链
    qemu_config: dict | None = None  # QEMU 配置（如需仿真）
    pass_criteria: str               # 整体通过标准

class RiskAssessment(BaseModel):
    affected_subsystems: list[str]
    regression_risk: str             # "low" | "medium" | "high"
    security_impact: bool
    abi_impact: bool
    community_acceptance: str        # "high" | "medium" | "low"
    rollback_strategy: str

class ExecutionPlan(BaseModel):
    opportunity_id: str
    dev_plan: DevPlan
    test_plan: TestPlan
    risk_assessment: RiskAssessment
    estimated_complexity: str        # "trivial" | "small" | "medium" | "large"
    estimated_iterations: int        # 预估开发-审核迭代次数

# ── 开发层输出 ──

class ChangedFile(BaseModel):
    path: str
    change_type: str                 # "modified" | "added" | "deleted"
    lines_added: int
    lines_removed: int
    diff_summary: str

class BuildResult(BaseModel):
    success: bool
    command: str
    output: str
    warnings: list[str] = []
    errors: list[str] = []

class DevelopmentResult(BaseModel):
    patch: str                       # unified diff 格式
    changed_files: list[ChangedFile]
    build_result: BuildResult
    commit_message: str
    summary: str
    iterations: int = 0
    review_verdict: ReviewVerdict | None = None
    escalated: bool = False
    escalation_reason: str | None = None

# ── 审核层输出 ──

class ReviewFinding(BaseModel):
    id: str
    severity: str                    # "critical" | "high" | "medium" | "low" | "info"
    category: str                    # "correctness" | "security" | "performance" | "style" | "isa_compliance"
    file_path: str
    line_range: tuple[int, int]
    description: str
    suggestion: str
    auto_fixable: bool = False       # 是否可自动修复
    reference: str | None = None     # 引用的规范/文档

class ReviewVerdict(BaseModel):
    approved: bool
    findings: list[ReviewFinding]
    critical_count: int
    high_count: int
    iteration: int
    summary: str
    confidence: float                # 审核置信度 0.0 - 1.0

# ── 测试层输出 ──

class TestCaseResult(BaseModel):
    case_id: str
    passed: bool
    output: str
    duration_seconds: float
    log_path: str | None = None      # MinIO/S3 中的日志路径

class TestResult(BaseModel):
    overall_passed: bool
    case_results: list[TestCaseResult]
    pass_rate: float
    total_duration_seconds: float
    environment_info: dict           # QEMU 版本、工具链版本等
    log_archive_path: str            # 完整日志归档路径
```

### 4.1 探索 Agent（Explorer）

**SDK**：OpenAI Agents SDK  
**模型**：GPT-4o（信息综合能力强，成本适中）  
**职责**：自主探索 RISC-V 邮件列表和代码库，结合用户输入，发现潜在贡献点并验证可行性

**架构**：采用 Handoff 模式，主 Agent 协调三个专业子 Agent：

```python
from agents import Agent, Runner, handoff, function_tool, GuardrailFunctionOutput
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

# 子 Agent 1：邮件列表监控
mail_scanner = Agent(
    name="mail_scanner",
    instructions="""你是 RISC-V 邮件列表分析专家。
    扫描 linux-riscv、qemu-devel 等邮件列表，识别：
    - 未解决的 bug 报告
    - 功能请求和 TODO 标记
    - 架构适配讨论中的缺失项
    - CI 失败模式
    输出结构化的候选贡献点列表。""",
    tools=[search_mailing_list, fetch_patchwork_status],
    model="gpt-4o",
)

# 子 Agent 2：代码库分析
code_analyzer = Agent(
    name="code_analyzer",
    instructions="""你是 RISC-V 代码库分析专家。
    分析目标仓库中的：
    - RISC-V 架构特定代码的 TODO/FIXME/HACK 注释
    - 与 ARM/x86 实现的差距
    - 缺失的测试覆盖
    - 编译警告和静态分析问题
    输出结构化的候选贡献点列表。""",
    tools=[clone_repo, grep_patterns, run_static_analysis],
    model="gpt-4o",
)

# 子 Agent 3：可行性验证
feasibility_checker = Agent(
    name="feasibility_checker",
    instructions="""你是贡献可行性评估专家。
    对每个候选贡献点进行验证：
    1. 该问题是否仍然存在（检查最新代码）
    2. 是否已有人在处理（检查 PR/邮件线程）
    3. 修复复杂度评估
    4. 社区接受可能性评估
    输出带评分的可行性报告。""",
    tools=[check_upstream_status, search_existing_patches, assess_complexity],
    model="gpt-4o",
)

# 主探索 Agent：协调三个子 Agent
explorer = Agent(
    name="explorer",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    你是 RV-Insights 探索层的总协调者。
    1. 接收用户输入或定时触发信号
    2. 将邮件列表扫描任务 handoff 给 mail_scanner
    3. 将代码库分析任务 handoff 给 code_analyzer
    4. 汇总候选点后，将每个候选点 handoff 给 feasibility_checker 验证
    5. 输出最终的 ExplorationResult 列表
    """,
    handoffs=[
        handoff(mail_scanner),
        handoff(code_analyzer),
        handoff(feasibility_checker),
    ],
    model="gpt-4o",
    output_type=list[ExplorationResult],  # 结构化输出
)
```

**Guardrails**：

```python
from agents import input_guardrail, output_guardrail, GuardrailFunctionOutput

@input_guardrail
async def validate_exploration_input(ctx, agent, input_data):
    """确保输入包含有效的仓库 URL 和上下文"""
    if "repo_url" not in input_data and "raw_content" not in input_data:
        return GuardrailFunctionOutput(
            output_info={"error": "探索输入必须包含 repo_url 或 raw_content"},
            tripwire_triggered=True,
        )
    return GuardrailFunctionOutput(output_info={"status": "valid"}, tripwire_triggered=False)

@output_guardrail
async def validate_exploration_output(ctx, agent, output):
    """确保探索结果包含必要的证据链"""
    for result in output.final_output_as(list[ExplorationResult]):
        if not result.evidence:
            return GuardrailFunctionOutput(
                output_info={"error": f"贡献点 {result.title} 缺少证据"},
                tripwire_triggered=True,
            )
        if result.feasibility_score < 0 or result.feasibility_score > 1:
            return GuardrailFunctionOutput(
                output_info={"error": "可行性评分必须在 0-1 之间"},
                tripwire_triggered=True,
            )
        if result.upstream_status == "wip_by_others":
            return GuardrailFunctionOutput(
                output_info={"warning": f"{result.title} 已有人在处理，需人工确认"},
                tripwire_triggered=True,
            )
    return GuardrailFunctionOutput(output_info={"status": "valid"}, tripwire_triggered=False)
```

**工具实现示例**：

```python
@function_tool
async def search_mailing_list(
    query: str,
    list_name: str = "linux-riscv",
    date_range: str = "30d",
) -> str:
    """搜索 RISC-V 相关邮件列表，返回匹配的邮件线程摘要"""
    # 通过 lore.kernel.org API 或本地镜像检索
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://lore.kernel.org/{list_name}/",
            params={"q": query, "x": "m", "o": date_range},
        )
    threads = parse_lore_results(resp.text)
    return json.dumps([t.model_dump() for t in threads[:20]])

@function_tool
async def check_upstream_status(
    repo_url: str,
    file_path: str,
    issue_keywords: list[str],
) -> str:
    """检查上游仓库中是否已有相关的修复或正在进行的工作"""
    # 检查最近的 commits、open PRs、mailing list patches
    recent_commits = await git_log_search(repo_url, file_path, keywords=issue_keywords)
    open_patches = await patchwork_search(issue_keywords)
    return json.dumps({
        "recent_related_commits": recent_commits,
        "open_patches": open_patches,
        "status": "no_existing_work" if not (recent_commits or open_patches) else "wip_by_others",
    })

@function_tool
async def assess_complexity(
    repo_url: str,
    affected_files: list[str],
    description: str,
) -> str:
    """评估贡献的实现复杂度"""
    # 分析文件大小、依赖关系、历史修改频率
    file_stats = await get_file_stats(repo_url, affected_files)
    return json.dumps({
        "total_loc": sum(f["loc"] for f in file_stats),
        "avg_change_frequency": sum(f["commits_30d"] for f in file_stats) / len(file_stats),
        "complexity_estimate": "small" if sum(f["loc"] for f in file_stats) < 500 else "medium",
    })
```

### 4.2 规划 Agent（Planner）

**SDK**：OpenAI Agents SDK  
**模型**：o3-mini（推理能力强，适合方案设计）  
**职责**：将探索结果转化为结构化的开发方案和测试方案

**架构**：采用 Handoff 模式，主 Agent 协调两个专业子 Agent：

```python
# 子 Agent：开发方案设计
dev_planner = Agent(
    name="dev_planner",
    instructions="""你是 RISC-V 代码开发方案设计专家。
    基于贡献机会描述和受影响文件列表，输出：
    1. 按依赖顺序排列的实现步骤
    2. 每步的目标文件和变更描述
    3. 需要参考的 ISA 规范/ABI 文档/社区指南
    4. 目标仓库的编码规范要点（通过分析现有代码推断）
    5. commit message 模板（符合目标社区格式）""",
    tools=[fetch_repo_style_guide, fetch_isa_spec_section, analyze_code_patterns],
    model="o3-mini",
    output_type=DevPlan,
)

# 子 Agent：测试方案设计
test_planner = Agent(
    name="test_planner",
    instructions="""你是 RISC-V 测试方案设计专家。
    基于开发方案和受影响子系统，输出：
    1. 测试用例列表（含具体执行命令）
    2. 测试环境要求（QEMU 配置、交叉编译工具链版本）
    3. 每个测试的通过/失败判定标准
    4. 环境搭建命令序列
    
    测试类型优先级：
    - build 测试（交叉编译通过）> boot 测试（QEMU 启动）> unit 测试 > integration 测试 > performance 测试""",
    tools=[list_existing_tests, get_qemu_config_template, get_toolchain_info],
    model="o3-mini",
    output_type=TestPlan,
)

# 主规划 Agent
planner = Agent(
    name="planner",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    你是 RV-Insights 规划层的总协调者。
    1. 分析探索结果，确定贡献范围和约束
    2. 将开发方案设计 handoff 给 dev_planner
    3. 将测试方案设计 handoff 给 test_planner
    4. 进行风险评估：受影响子系统、回归风险、ABI 影响、安全影响
    5. 汇总为完整的 ExecutionPlan
    
    关键约束：
    - 单个 patch 只解决一个问题
    - 预估修改行数超过 500 行时，建议拆分
    - 涉及 ABI 变更或安全路径时，risk_level 必须为 high""",
    handoffs=[handoff(dev_planner), handoff(test_planner)],
    model="o3-mini",
    output_type=ExecutionPlan,
    output_guardrails=[validate_plan_completeness],
)
```

**规划完整性校验**：

```python
@output_guardrail
async def validate_plan_completeness(ctx, agent, output):
    """确保规划方案完整且自洽"""
    plan: ExecutionPlan = output.final_output_as(ExecutionPlan)
    errors = []

    # 开发方案校验
    if not plan.dev_plan.steps:
        errors.append("开发方案缺少实现步骤")
    for step in plan.dev_plan.steps:
        if not step.target_files:
            errors.append(f"步骤 {step.order} 缺少目标文件")
        for dep in step.depends_on:
            if dep >= step.order:
                errors.append(f"步骤 {step.order} 的依赖 {dep} 不合法（前向依赖）")

    # 测试方案校验
    if not plan.test_plan.cases:
        errors.append("测试方案缺少测试用例")
    has_build_test = any(c.type == "build" for c in plan.test_plan.cases)
    if not has_build_test:
        errors.append("测试方案必须包含至少一个 build 测试")

    # 风险评估校验
    if plan.risk_assessment.security_impact and plan.risk_assessment.regression_risk != "high":
        errors.append("涉及安全影响时，回归风险应标记为 high")

    if errors:
        return GuardrailFunctionOutput(
            output_info={"errors": errors}, tripwire_triggered=True,
        )
    return GuardrailFunctionOutput(output_info={"status": "valid"}, tripwire_triggered=False)
```

### 4.3 开发 Agent（Developer）

**SDK**：Claude Agent SDK  
**模型**：Claude Opus 4.6（最强代码生成能力）  
**职责**：根据规划方案进行代码开发

这是平台最核心的 Agent。选用 Claude Agent SDK 的决定性理由：Claude Code 的内置工具集（Read/Write/Edit/Bash/Grep/Glob/Git）提供了完整的代码操作能力，无需从零构建。

```python
from claude_agent_sdk import (
    ClaudeSDKClient, ClaudeAgentOptions,
    PermissionResultAllow, PermissionResultDeny,
)

async def run_developer(plan: ExecutionPlan, worktree_path: str) -> DevelopmentResult:
    """执行开发任务，返回代码变更"""

    system_prompt = f"""你是 RV-Insights 的开发 Agent，负责 RISC-V 开源代码贡献。

当前任务：
{plan.dev_plan.model_dump_json(indent=2)}

工作目录：{worktree_path}

严格要求：
1. 只修改计划中列出的文件，除非发现必要的关联修改
2. 遵循目标仓库的代码风格（通过 Read 工具先阅读相邻代码）
3. 每次修改后用 Bash 工具执行基本编译检查
4. 生成符合社区规范的 commit message
5. 如果发现计划有误或不可行，立即停止并报告"""

    # 人工审批回调：拦截危险操作
    async def permission_gate(tool_name, input_data, context):
        safe_read_tools = {"Read", "Grep", "Glob"}
        if tool_name in safe_read_tools:
            return PermissionResultAllow()

        if tool_name == "Bash":
            cmd = input_data.get("command", "")
            # 禁止破坏性命令
            dangerous = ["rm -rf", "git push", "git reset --hard", "sudo"]
            if any(d in cmd for d in dangerous):
                return PermissionResultDeny(message=f"危险命令被拦截: {cmd}")
            # 允许编译和测试命令
            safe_prefixes = ["make", "gcc", "clang", "grep", "find", "git diff", "git log"]
            if any(cmd.strip().startswith(p) for p in safe_prefixes):
                return PermissionResultAllow()

        # 其他工具（Write/Edit）自动允许（在 worktree 中操作）
        if tool_name in {"Write", "Edit"}:
            return PermissionResultAllow()

        return PermissionResultDeny(message=f"未授权的工具调用: {tool_name}")

    options = ClaudeAgentOptions(
        model="claude-opus-4-6",
        system_prompt=system_prompt,
        cwd=worktree_path,
        can_use_tool=permission_gate,
        max_turns=50,
        allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
        thinking={"type": "enabled", "budget_tokens": 32000},
    )

    result_text = ""
    async with ClaudeSDKClient(options=options) as client:
        await client.query(f"请按照开发方案实现代码变更。方案详情：\n{plan.dev_plan.steps}")
        async for msg in client.receive_response():
            result_text += extract_text(msg)

    return DevelopmentResult(
        patch=generate_patch(worktree_path),
        changed_files=get_changed_files(worktree_path),
        build_status=check_build(worktree_path),
        summary=result_text,
    )
```

### 4.4 审核 Agent（Reviewer）

**SDK**：OpenAI Agents SDK  
**模型**：OpenAI Codex / GPT-4o（代码审查能力强）  
**职责**：对开发 Agent 的代码变更进行多维度审查

```python
# 审核子 Agent：安全审查
security_reviewer = Agent(
    name="security_reviewer",
    instructions="""你是安全审查专家。检查代码变更中的：
    - 缓冲区溢出风险
    - 整数溢出
    - 未初始化变量
    - 权限提升路径
    - 内存泄漏
    输出 ReviewFinding 列表。""",
    model="gpt-4o",
    output_type=list[ReviewFinding],
)

# 审核子 Agent：正确性审查
correctness_reviewer = Agent(
    name="correctness_reviewer",
    instructions="""你是 RISC-V 架构正确性审查专家。检查：
    - ISA 规范符合性
    - 寄存器使用正确性
    - 内存模型一致性
    - 边界条件处理
    - 与 ARM/x86 实现的一致性
    输出 ReviewFinding 列表。""",
    model="gpt-4o",
    output_type=list[ReviewFinding],
)

# 审核子 Agent：风格审查
style_reviewer = Agent(
    name="style_reviewer",
    instructions="""你是代码风格审查专家。检查：
    - 目标仓库的编码规范符合性
    - commit message 格式
    - 注释质量
    - 命名一致性
    输出 ReviewFinding 列表。""",
    model="gpt-4o",
    output_type=list[ReviewFinding],
)

# 主审核 Agent：汇总并做出最终判定
reviewer = Agent(
    name="reviewer",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    你是 RV-Insights 的首席代码审核者。
    1. 将代码变更分发给安全、正确性、风格三个专业审核者
    2. 汇总所有 findings
    3. 做出最终判定：
       - approved=True：无 critical/high findings，可进入测试
       - approved=False：存在必须修复的问题，附带具体修复建议
    """,
    handoffs=[
        handoff(security_reviewer),
        handoff(correctness_reviewer),
        handoff(style_reviewer),
    ],
    model="gpt-4o",
    output_type=ReviewVerdict,
    output_guardrails=[validate_review_completeness],
)
```

### 4.5 测试 Agent（Tester）

**SDK**：Claude Agent SDK  
**模型**：Claude Sonnet 4.6（性价比最优的代码执行模型）  
**职责**：搭建测试环境，执行测试方案，输出结构化测试结果

```python
async def run_tester(
    plan: TestPlan, worktree_path: str, patch: str
) -> TestResult:
    """执行测试任务"""

    system_prompt = f"""你是 RV-Insights 的测试 Agent。

测试方案：
{plan.model_dump_json(indent=2)}

工作目录：{worktree_path}

执行步骤：
1. 检查测试环境是否满足要求
2. 应用补丁到工作目录
3. 按测试方案逐项执行测试
4. 收集测试输出和日志
5. 判定每项测试的通过/失败状态
6. 输出结构化测试报告

注意：
- 使用 QEMU 进行 RISC-V 仿真测试
- 记录所有命令的完整输出
- 如果测试环境搭建失败，报告具体原因而非跳过"""

    async def test_permission_gate(tool_name, input_data, context):
        if tool_name in {"Read", "Grep", "Glob"}:
            return PermissionResultAllow()
        if tool_name == "Bash":
            cmd = input_data.get("command", "")
            # 测试 Agent 只允许执行测试相关命令
            allowed = ["make", "qemu", "gcc", "clang", "pytest", "cargo test",
                       "git apply", "git diff", "cat", "ls", "find"]
            if any(cmd.strip().startswith(a) for a in allowed):
                return PermissionResultAllow()
            return PermissionResultDeny(message=f"测试 Agent 不允许执行: {cmd}")
        return PermissionResultDeny(message=f"测试 Agent 不允许使用: {tool_name}")

    options = ClaudeAgentOptions(
        model="claude-sonnet-4-6",
        system_prompt=system_prompt,
        cwd=worktree_path,
        can_use_tool=test_permission_gate,
        max_turns=30,
        sandbox={"filesystem": "read_write", "network": "restricted"},
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("请按照测试方案执行所有测试项")
        async for msg in client.receive_response():
            process_test_output(msg)

    return collect_test_results(worktree_path)
```

### 4.6 Prompt 工程管理

每个 Agent 的 system prompt 是影响输出质量的最关键变量，需要系统化管理：

**Prompt 存储与版本化**：

```
rv-insights/
├── prompts/
│   ├── explorer/
│   │   ├── v1.0.0.md          # 主 prompt
│   │   ├── v1.1.0.md          # 迭代版本
│   │   └── sub_agents/
│   │       ├── mail_scanner.md
│   │       ├── code_analyzer.md
│   │       └── feasibility_checker.md
│   ├── planner/
│   │   ├── v1.0.0.md
│   │   └── sub_agents/
│   │       ├── dev_planner.md
│   │       └── test_planner.md
│   ├── developer/
│   │   └── v1.0.0.md
│   ├── reviewer/
│   │   ├── v1.0.0.md
│   │   └── sub_agents/
│   │       ├── security_reviewer.md
│   │       ├── correctness_reviewer.md
│   │       └── style_reviewer.md
│   └── tester/
│       └── v1.0.0.md
```

**Prompt 加载机制**：

```python
from pathlib import Path

class PromptManager:
    """Prompt 版本管理与加载"""

    def __init__(self, prompts_dir: Path, active_versions: dict[str, str]):
        self.prompts_dir = prompts_dir
        self.active_versions = active_versions  # {"explorer": "v1.1.0", ...}

    def load(self, agent: str, sub_agent: str | None = None) -> str:
        version = self.active_versions[agent]
        if sub_agent:
            path = self.prompts_dir / agent / "sub_agents" / f"{sub_agent}.md"
        else:
            path = self.prompts_dir / agent / f"{version}.md"
        return path.read_text()

    def load_with_context(self, agent: str, context: dict) -> str:
        """加载 prompt 并注入运行时上下文（仓库信息、编码规范等）"""
        template = self.load(agent)
        return template.format(**context)
```

**Prompt 效果评估**：

| 指标 | 计算方式 | 目标 |
|------|---------|------|
| 审核通过率 | 首轮审核通过的案例 / 总案例 | > 30% |
| 平均迭代次数 | 开发-审核迭代次数均值 | < 3 |
| 人工驳回率 | 人工审核驳回 / 总审核 | < 20% |
| Guardrail 触发率 | Guardrail 拦截 / 总调用 | < 10% |
| 领域准确率 | ISA 规范相关 findings 的准确率 | > 90% |

**Prompt 迭代流程**：修改 prompt → 在 staging 环境跑 3-5 个历史案例 → 对比指标 → 人工评审 → 合入主版本。Prompt 变更视同代码变更，需要 code review。

---

## 5. 工作流状态机与人工审核机制

### 5.1 案例状态机

每个贡献案例（ContributionCase）遵循以下状态流转：

```
                    ┌──────────────────────────────────────────────────────┐
                    │                                                      │
                    ▼                                                      │
  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
  │ CREATED  │─▶│  EXPLORING   │─▶│ EXPLORE_DONE │─▶│ HUMAN_REVIEW │     │
  └──────────┘  └──────────────┘  └──────────────┘  │  _EXPLORE    │     │
                                                     └──────┬───────┘     │
                                                            │             │
                                          ┌─── 驳回 ────────┘             │
                                          │     (回到 EXPLORING           │
                                          │      或 ABANDONED)            │
                                          ▼                               │
                                   ┌──────────────┐                       │
                                   │  PLANNING    │                       │
                                   └──────┬───────┘                       │
                                          │                               │
                                          ▼                               │
                                   ┌──────────────┐                       │
                                   │ PLAN_DONE    │                       │
                                   └──────┬───────┘                       │
                                          │                               │
                                          ▼                               │
                                   ┌──────────────┐                       │
                                   │ HUMAN_REVIEW │                       │
                                   │  _PLAN       │                       │
                                   └──────┬───────┘                       │
                                          │                               │
                                          ▼                               │
                              ┌───────────────────────┐                   │
                              │     DEVELOPING        │◀──┐               │
                              └───────────┬───────────┘   │               │
                                          │               │               │
                                          ▼               │               │
                              ┌───────────────────────┐   │               │
                              │     REVIEWING         │   │               │
                              └───────────┬───────────┘   │               │
                                          │               │               │
                                    ┌─────┴─────┐        │               │
                                    │           │        │               │
                              approved=false  approved=true              │
                                    │           │        │               │
                                    ▼           │        │               │
                              ┌──────────┐      │        │               │
                              │ 迭代修复  │──────┘        │               │
                              └──────────┘               │               │
                                          │               │               │
                                          ▼               │               │
                              ┌───────────────────────┐   │               │
                              │ HUMAN_REVIEW_DEV      │───┘               │
                              └───────────┬───────────┘  (驳回回开发)      │
                                          │                               │
                                          ▼                               │
                              ┌───────────────────────┐                   │
                              │     TESTING           │                   │
                              └───────────┬───────────┘                   │
                                          │                               │
                                          ▼                               │
                              ┌───────────────────────┐                   │
                              │ HUMAN_REVIEW_TEST     │───────────────────┘
                              └───────────┬───────────┘  (驳回可回到任意阶段)
                                          │
                                          ▼
                              ┌───────────────────────┐
                              │   READY_FOR_UPSTREAM  │
                              └───────────────────────┘
```

### 5.2 人工审核门禁实现

每个 `HUMAN_REVIEW_*` 状态是一个阻塞点。编排引擎在此暂停，等待人工操作：

```python
from enum import Enum
from pydantic import BaseModel
from datetime import datetime

class HumanDecision(str, Enum):
    APPROVE = "approve"           # 通过，进入下一阶段
    REJECT = "reject"             # 驳回，回到当前阶段重做
    REJECT_TO_PHASE = "reject_to" # 驳回到指定阶段
    ABANDON = "abandon"           # 放弃该贡献案例
    MODIFY = "modify"             # 通过但附带修改意见

class HumanReview(BaseModel):
    case_id: str
    phase: str
    reviewer: str
    decision: HumanDecision
    comments: str
    reject_to_phase: str | None = None
    timestamp: datetime

class HumanGateService:
    """人工审核门禁服务"""

    async def request_review(self, case_id: str, phase: str, artifacts: dict) -> None:
        """提交审核请求，通知人工审核者"""
        await self.db.create_review_request(case_id, phase, artifacts)
        await self.notify_reviewers(case_id, phase)

    async def wait_for_decision(self, case_id: str, phase: str) -> HumanReview:
        """阻塞等待人工决策（通过 WebSocket/SSE 推送到前端）"""
        while True:
            review = await self.db.get_review_decision(case_id, phase)
            if review is not None:
                await self.audit_log.record(case_id, phase, review)
                return review
            await asyncio.sleep(5)

    async def submit_decision(self, review: HumanReview) -> None:
        """人工审核者提交决策（由 Web Console 调用）"""
        await self.db.save_review_decision(review)
        await self.audit_log.record(review.case_id, review.phase, review)
```

### 5.3 Pipeline Engine 核心循环

```python
class PipelineEngine:
    """案例流水线引擎"""

    async def run_case(self, case: ContributionCase) -> None:
        """执行单个贡献案例的完整流水线"""

        # Phase 1: 探索
        case.status = "EXPLORING"
        exploration = await self.run_explorer(case.input_context)
        case.exploration_result = exploration
        case.status = "EXPLORE_DONE"

        review = await self.human_gate.request_and_wait(case.id, "explore", exploration)
        if review.decision == HumanDecision.ABANDON:
            case.status = "ABANDONED"; return
        if review.decision == HumanDecision.REJECT:
            return await self.run_case(case)  # 重新探索

        # Phase 2: 规划
        case.status = "PLANNING"
        plan = await self.run_planner(exploration)
        case.execution_plan = plan
        case.status = "PLAN_DONE"

        review = await self.human_gate.request_and_wait(case.id, "plan", plan)
        if review.decision == HumanDecision.REJECT:
            case.status = "PLANNING"
            return await self.run_case_from_phase(case, "plan")

        # Phase 3: 开发-审核迭代
        case.status = "DEVELOPING"
        dev_result = await self.run_dev_review_loop(case, plan)
        case.development_result = dev_result

        review = await self.human_gate.request_and_wait(case.id, "dev", dev_result)
        if review.decision == HumanDecision.REJECT:
            return await self.run_case_from_phase(case, review.reject_to_phase or "dev")

        # Phase 4: 测试
        case.status = "TESTING"
        test_result = await self.run_tester(plan.test_plan, dev_result)
        case.test_result = test_result

        review = await self.human_gate.request_and_wait(case.id, "test", test_result)
        if review.decision == HumanDecision.REJECT_TO_PHASE:
            return await self.run_case_from_phase(case, review.reject_to_phase)

        case.status = "READY_FOR_UPSTREAM"

    async def run_case_from_phase(self, case: ContributionCase, phase: str) -> None:
        """从指定阶段恢复执行——用于人工驳回后的部分重跑"""
        phase_order = ["explore", "plan", "dev", "review", "test"]
        start_idx = phase_order.index(phase)
        remaining_phases = phase_order[start_idx:]

        case.metadata["resumed_from"] = phase
        case.metadata["resumed_at"] = datetime.utcnow().isoformat()

        for p in remaining_phases:
            match p:
                case "explore":
                    case.exploration = await self.run_explore(case)
                    review = await self.human_gate.request_and_wait(case, "explore")
                    if not review.approved:
                        return await self._handle_rejection(case, review, "explore")
                case "plan":
                    case.plan = await self.run_plan(case)
                    review = await self.human_gate.request_and_wait(case, "plan")
                    if not review.approved:
                        return await self._handle_rejection(case, review, "plan")
                case "dev":
                    case.dev_result = await self.run_dev(case)
                case "review":
                    verdict = await self.run_dev_review_loop(case)
                    if not verdict.approved:
                        case.status = "DEV_REVIEW_FAILED"
                        return
                    review = await self.human_gate.request_and_wait(case, "review")
                    if not review.approved:
                        return await self._handle_rejection(case, review, "review")
                case "test":
                    case.test_result = await self.run_test(case)
                    review = await self.human_gate.request_and_wait(case, "test")
                    if not review.approved:
                        return await self._handle_rejection(case, review, "test")

        case.status = "READY_FOR_UPSTREAM"

    async def _handle_rejection(
        self, case: ContributionCase, review: HumanReview, current_phase: str
    ) -> None:
        match review.decision:
            case "reject":
                return await self.run_case_from_phase(case, current_phase)
            case "reject_to":
                return await self.run_case_from_phase(
                    case, review.reject_to_phase or current_phase
                )
            case "abandon":
                case.status = "ABANDONED"
            case "modify":
                case.apply_modifications(review.modifications)
                return await self.run_case_from_phase(case, current_phase)
```

### 5.4 通知与协作机制

`notify_reviewers()` 的具体实现——支持多渠道通知和多审核者协调：

```python
from enum import Enum

class NotificationChannel(str, Enum):
    WEBHOOK = "webhook"       # Slack / Feishu / DingTalk webhook
    EMAIL = "email"           # SMTP 邮件
    SSE = "sse"               # Web Console 实时推送
    CLI_POLL = "cli_poll"     # CLI 轮询（rv-insights reviews pending）

class NotificationService:
    """多渠道通知服务"""

    def __init__(self, channels: list[NotificationChannel], config: dict):
        self.channels = channels
        self.config = config

    async def notify_reviewers(
        self,
        case_id: str,
        phase: str,
        summary: str,
        artifacts_url: str,
    ) -> None:
        """向所有已配置渠道发送审核通知"""
        message = self._format_review_request(case_id, phase, summary, artifacts_url)
        tasks = [self._send(ch, message) for ch in self.channels]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _send(self, channel: NotificationChannel, message: dict) -> None:
        match channel:
            case NotificationChannel.WEBHOOK:
                await self._send_webhook(message)
            case NotificationChannel.EMAIL:
                await self._send_email(message)
            case NotificationChannel.SSE:
                await self._publish_sse_event(message)
            case NotificationChannel.CLI_POLL:
                pass  # CLI 通过 API 轮询 pending reviews

    def _format_review_request(self, case_id, phase, summary, url) -> dict:
        return {
            "type": "review_request",
            "case_id": case_id,
            "phase": phase,
            "summary": summary,
            "review_url": url,
            "timestamp": datetime.utcnow().isoformat(),
        }
```

**多审核者协调策略**：

| 策略 | 说明 | 适用场景 |
|------|------|---------|
| `first_response` | 第一个审核者的决策即为最终决策 | MVP 阶段，单人审核 |
| `majority_vote` | 多数审核者同意即通过 | 重要贡献，需要共识 |
| `all_approve` | 所有审核者都必须同意 | 安全敏感的内核补丁 |
| `role_based` | 不同角色审核不同维度（安全/正确性/风格） | 成熟阶段，分工审核 |

MVP 阶段默认使用 `first_response`，通过配置切换。

### 5.5 优雅停机与资源清理

Pipeline Engine 被中断（SIGTERM/SIGINT）时，需要安全清理所有资源：

```python
import signal

class GracefulShutdown:
    """优雅停机管理器"""

    def __init__(self, engine: PipelineEngine):
        self.engine = engine
        self._shutting_down = False
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum, frame):
        if self._shutting_down:
            return  # 防止重复触发
        self._shutting_down = True
        asyncio.create_task(self._shutdown())

    async def _shutdown(self):
        """按优先级清理资源"""
        # 1. 停止接受新案例
        self.engine.accepting_new_cases = False

        # 2. 保存所有运行中案例的状态快照
        for case in self.engine.active_cases.values():
            await self._save_checkpoint(case)

        # 3. 终止 Claude CLI 子进程（发送 SIGTERM，等待 10s 后 SIGKILL）
        for proc in self.engine.claude_processes:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=10)
            except asyncio.TimeoutError:
                proc.kill()

        # 4. 清理 Git worktree
        for worktree in self.engine.active_worktrees:
            await asyncio.create_subprocess_exec(
                "git", "worktree", "remove", "--force", worktree
            )

        # 5. 清理临时文件
        for tmp_dir in self.engine.temp_dirs:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        # 6. 释放信号量
        self.engine.resource_scheduler.release_all()

    async def _save_checkpoint(self, case: ContributionCase) -> None:
        """保存案例状态快照，支持后续恢复"""
        checkpoint = {
            "case_id": case.id,
            "status": case.status,
            "current_phase": case.current_phase,
            "artifacts": case.artifacts_summary(),
            "interrupted_at": datetime.utcnow().isoformat(),
        }
        await self.engine.db.save_checkpoint(case.id, checkpoint)
```

**恢复策略**：重启后，Pipeline Engine 扫描 `checkpoint` 表，对每个中断的案例调用 `run_case_from_phase()` 从断点恢复。

---

## 6. 开发-审核迭代闭环设计

这是平台最关键的机制：开发 Agent（Claude Code）和审核 Agent（Codex）之间的多轮迭代。

### 6.1 迭代流程图

```
                    ExecutionPlan
                         │
                         ▼
              ┌─────────────────────┐
              │   开发 Agent        │
              │   (Claude Agent SDK)│
              │                     │
              │   · 读取计划        │
              │   · 编写代码        │
              │   · 编译检查        │
              │   · 生成 patch      │
              └──────────┬──────────┘
                         │
                         │ DevelopmentResult
                         │ (patch + changed_files + build_status)
                         ▼
              ┌─────────────────────┐
              │   审核 Agent        │
              │   (OpenAI Agents SDK)│
              │                     │
              │   · 安全审查        │
              │   · 正确性审查      │
              │   · 风格审查        │
              │   · 汇总判定        │
              └──────────┬──────────┘
                         │
                         │ ReviewVerdict
                         │
                   ┌─────┴─────┐
                   │           │
             approved=false  approved=true
                   │           │
                   ▼           ▼
            ┌────────────┐  ┌──────────────┐
            │ 构造修复    │  │ 退出迭代     │
            │ 指令        │  │ 进入人工审核  │
            └──────┬─────┘  └──────────────┘
                   │
                   │ findings → 修复指令
                   │
                   ▼
              ┌─────────────────────┐
              │   开发 Agent        │
              │   (同一会话续写)     │
              │                     │
              │   · 读取 findings   │
              │   · 逐项修复        │
              │   · 重新编译检查    │
              │   · 更新 patch      │
              └──────────┬──────────┘
                         │
                         │ (回到审核 Agent)
                         ▼
                       ......
              (最多 MAX_ITERATIONS 轮)
```

### 6.2 迭代引擎实现

```python
MAX_DEV_REVIEW_ITERATIONS = 5

async def run_dev_review_loop(
    self,
    case: ContributionCase,
    plan: ExecutionPlan,
) -> DevelopmentResult:
    """开发-审核迭代闭环"""

    worktree = await create_git_worktree(case.repo_url, case.id)

    # 首次开发
    dev_result = await run_developer(plan, worktree.path)

    for iteration in range(1, MAX_DEV_REVIEW_ITERATIONS + 1):
        # 审核
        review_input = format_review_input(dev_result, plan, iteration)
        review_result = await Runner.run(reviewer, input=review_input)
        verdict: ReviewVerdict = review_result.final_output_as(ReviewVerdict)

        # 记录审计
        await self.audit_log.record_review(case.id, iteration, verdict)

        if verdict.approved:
            dev_result.review_verdict = verdict
            dev_result.iterations = iteration
            return dev_result

        if iteration == MAX_DEV_REVIEW_ITERATIONS:
            # 达到最大迭代次数，升级人工接管
            dev_result.escalated = True
            dev_result.escalation_reason = "达到最大迭代次数仍未通过审核"
            dev_result.review_verdict = verdict
            return dev_result

        # 构造修复指令
        fix_instructions = format_fix_instructions(verdict.findings)

        # 在同一 Claude Code 会话中续写修复
        async with ClaudeSDKClient(options=ClaudeAgentOptions(
            model="claude-opus-4-6",
            cwd=worktree.path,
            session_store=self.session_store,
            session_id=f"dev-{case.id}",
        )) as client:
            await client.query(f"""
审核 Agent 第 {iteration} 轮审查发现以下问题，请逐项修复：

{fix_instructions}

修复后请重新编译验证。""")
            async for msg in client.receive_response():
                dev_result = update_dev_result(dev_result, msg)

    return dev_result
```

### 6.3 迭代收敛保障

| 机制 | 说明 |
|------|------|
| 最大迭代次数 | `MAX_DEV_REVIEW_ITERATIONS = 5`，超过后升级人工 |
| 收敛检测 | 如果连续两轮的 findings 数量不减少，提前升级 |
| 会话复用 | 开发 Agent 使用 `SessionStore` 保持上下文，避免每轮重新理解代码 |
| 增量修复 | 每轮只传递未解决的 findings，而非全量重审 |
| 审核一致性 | 审核 Agent 的 Guardrails 确保输出格式一致，避免漂移 |

### 6.4 最终产物格式与提交流程

流水线的最终输出是"贡献就绪产物"，需要严格符合 Linux 内核社区的提交规范：

**产物格式**：

```
output/{case_id}/
├── patches/
│   ├── 0001-riscv-fix-xxx.patch    # git format-patch 格式
│   ├── 0002-riscv-add-xxx.patch    # 多 patch 按逻辑拆分
│   └── series                       # patch 顺序描述文件
├── cover-letter.txt                 # 封面信（系列补丁时必需）
├── metadata.json                    # 案例元数据（来源、Agent 轨迹等）
└── review-log.md                    # 审核历史记录
```

**Patch 生成规范**：

```python
class PatchGenerator:
    """生成符合 Linux 内核规范的 patch"""

    COMMIT_MSG_TEMPLATE = """{subsystem}: {summary}

{description}

{technical_details}

Signed-off-by: {author_name} <{author_email}>
Reviewed-by: RV-Insights <rv-insights@noreply>
---
Generated-by: RV-Insights v{version}
Case-ID: {case_id}
"""

    async def generate(self, case: ContributionCase) -> list[Path]:
        patches = []
        for commit in case.commits:
            self._validate_commit_message(commit)
            self._validate_checkpatch(commit)
            patch = await self._format_patch(commit)
            patches.append(patch)
        return patches

    def _validate_commit_message(self, commit) -> None:
        """验证 commit message 符合内核规范"""
        subject = commit.message.split("\n")[0]
        assert len(subject) <= 75, "Subject line too long (max 75 chars)"
        assert ":" in subject, "Missing subsystem prefix"
        assert "Signed-off-by:" in commit.message, "Missing Signed-off-by"

    async def _validate_checkpatch(self, commit) -> None:
        """运行 scripts/checkpatch.pl 验证补丁格式"""
        result = await asyncio.create_subprocess_exec(
            "perl", "scripts/checkpatch.pl", "--strict", "-",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await result.communicate(commit.diff.encode())
        if result.returncode != 0:
            raise CheckpatchError(stdout.decode())
```

**提交流程（人工最终确认后）**：

```
1. 人工审核者确认 patch 质量 ──▶ approve
2. 平台生成 git send-email 命令 ──▶ 展示给用户
3. 用户手动执行 git send-email   ──▶ 发送到邮件列表
   （平台不自动发送，避免垃圾邮件风险）
```

平台生成的命令示例：

```bash
git send-email \
  --to=linux-riscv@lists.infradead.org \
  --cc=palmer@dabbelt.com \
  --cc=paul.walmsley@sifive.com \
  output/{case_id}/patches/*.patch
```

**为什么不自动发送**：Linux 内核社区对邮件列表垃圾邮件零容忍。AI 生成的补丁必须经过人工确认后由真人发送，这是社区信任的底线。

---

## 7. MCP 工具层设计

### 7.1 MCP Server 规划

平台通过 MCP 协议统一接入外部工具，避免 Agent 与底层系统直接耦合：

```
┌─────────────────────────────────────────────────────────┐
│                    Agent 能力层                          │
│  探索Agent  规划Agent  开发Agent  审核Agent  测试Agent   │
└─────┬──────────┬──────────┬──────────┬──────────┬───────┘
      │          │          │          │          │
      ▼          ▼          ▼          ▼          ▼
┌─────────────────────────────────────────────────────────┐
│                   MCP 工具层                             │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ mcp-riscv   │  │ mcp-git     │  │ mcp-knowledge   │ │
│  │ -maillist   │  │ -tools      │  │ -base           │ │
│  │             │  │             │  │                 │ │
│  │ ·搜索邮件   │  │ ·clone/pull │  │ ·ISA 规范检索   │ │
│  │ ·解析线程   │  │ ·diff/patch │  │ ·历史补丁检索   │ │
│  │ ·Patchwork  │  │ ·worktree   │  │ ·社区规范检索   │ │
│  │  状态查询   │  │ ·blame      │  │ ·RAG 向量检索   │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
│                                                         │
│  ┌─────────────┐  ┌─────────────────────────────────┐   │
│  │ mcp-test    │  │ mcp-static-analysis             │   │
│  │ -runner     │  │                                 │   │
│  │             │  │ ·sparse (Linux 内核)             │   │
│  │ ·QEMU 启动  │  │ ·clang-tidy                     │   │
│  │ ·交叉编译   │  │ ·RISC-V 特定规则检查             │   │
│  │ ·测试执行   │  │ ·checkpatch.pl                  │   │
│  │ ·结果收集   │  │                                 │   │
│  └─────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 7.2 MCP Server 接入方式

对于 Claude Agent SDK（开发/测试 Agent），MCP Server 通过 `ClaudeAgentOptions.mcp_servers` 接入：

```python
# 进程内 SDK MCP Server（Python 函数直接暴露为工具）
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool("search_mailing_list", "搜索 RISC-V 邮件列表", {
    "query": str, "list_name": str, "date_range": str
})
async def search_mailing_list(args):
    results = await maillist_client.search(
        query=args["query"],
        list_name=args["list_name"],
        date_range=args["date_range"],
    )
    return {"content": [{"type": "text", "text": json.dumps(results)}]}

mcp_maillist = create_sdk_mcp_server(
    name="riscv-maillist", version="1.0.0",
    tools=[search_mailing_list, fetch_thread, get_patchwork_status],
)

# 外部 MCP Server（独立进程）
mcp_config = {
    "riscv-maillist": mcp_maillist,                    # 进程内
    "git-tools": {                                      # 外部进程
        "type": "stdio",
        "command": "python", "args": ["-m", "mcp_git_tools"],
    },
    "knowledge-base": {                                 # 外部进程
        "type": "stdio",
        "command": "python", "args": ["-m", "mcp_knowledge"],
    },
}
```

对于 OpenAI Agents SDK（探索/规划/审核 Agent），工具通过 `@function_tool` 装饰器定义，内部调用相同的 MCP Server：

```python
from agents import function_tool

@function_tool
async def search_mailing_list(query: str, list_name: str, date_range: str) -> str:
    """搜索 RISC-V 邮件列表中的相关讨论"""
    # 内部复用同一个 maillist_client
    results = await maillist_client.search(query, list_name, date_range)
    return json.dumps(results)
```

### 7.3 工具权限矩阵

| MCP Server | 探索 Agent | 规划 Agent | 开发 Agent | 审核 Agent | 测试 Agent |
|-----------|:----------:|:----------:|:----------:|:----------:|:----------:|
| mcp-riscv-maillist | ✅ 读取 | ❌ | ❌ | ❌ | ❌ |
| mcp-git-tools | ✅ 只读 | ❌ | ✅ 读写 | ✅ 只读 | ✅ 只读 |
| mcp-knowledge-base | ✅ 检索 | ✅ 检索 | ✅ 检索 | ✅ 检索 | ❌ |
| mcp-test-runner | ❌ | ❌ | ❌ | ❌ | ✅ 执行 |
| mcp-static-analysis | ❌ | ❌ | ✅ 执行 | ✅ 只读 | ✅ 执行 |

### 7.4 MCP Server 实现规范

每个 MCP Server 必须遵循以下规范：

```python
# MCP Server 标准骨架
from mcp.server import Server
from mcp.types import Tool, TextContent

class MCPServerBase:
    """MCP Server 基类，提供标准化的健康检查、日志和指标"""

    def __init__(self, name: str, version: str):
        self.server = Server(name)
        self.version = version
        self._call_count = 0
        self._error_count = 0

    def register_tool(self, name: str, description: str, handler, input_schema: dict):
        @self.server.tool(name=name, description=description, input_schema=input_schema)
        async def wrapped_handler(args):
            self._call_count += 1
            try:
                result = await handler(args)
                return result
            except Exception as e:
                self._error_count += 1
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def health_check(self) -> dict:
        return {
            "name": self.server.name,
            "version": self.version,
            "calls": self._call_count,
            "errors": self._error_count,
            "status": "healthy",
        }
```

**MCP Server 间的工具命名约定**：

| MCP Server | 工具命名前缀 | 示例 |
|-----------|------------|------|
| mcp-riscv-maillist | `mcp__maillist__` | `mcp__maillist__search`, `mcp__maillist__fetch_thread` |
| mcp-git-tools | `mcp__git__` | `mcp__git__clone`, `mcp__git__diff`, `mcp__git__apply_patch` |
| mcp-knowledge-base | `mcp__kb__` | `mcp__kb__search_spec`, `mcp__kb__search_patches` |
| mcp-test-runner | `mcp__test__` | `mcp__test__run_qemu`, `mcp__test__cross_compile` |
| mcp-static-analysis | `mcp__sa__` | `mcp__sa__checkpatch`, `mcp__sa__clang_tidy` |

---

## 8. RISC-V 领域知识库设计

平台的长期壁垒不在单次推理，而在知识沉淀。知识库为所有 Agent 提供 RAG 检索能力。

### 8.1 知识分类与来源

| 知识类别 | 内容 | 来源 | 更新频率 |
|---------|------|------|---------|
| ISA 规范 | RISC-V ISA Manual、Profiles、ABI、向量扩展 | riscv.org 官方文档 | 按版本更新 |
| 社区规范 | 各仓库的 CONTRIBUTING.md、代码风格、commit 格式 | 目标仓库 | 每周同步 |
| 历史补丁 | 已合入的 RISC-V 相关 patch 及其 review 过程 | git log + 邮件列表 | 每日增量 |
| 维护者画像 | 各子系统维护者的偏好、review 风格、关注点 | 邮件列表分析 | 每月更新 |
| 故障模式 | 常见的 RISC-V 编译/运行时/性能问题模式 | 历史案例积累 | 持续积累 |
| 拒绝原因 | 被上游拒绝的 patch 及其拒绝理由 | 邮件列表 + Patchwork | 持续积累 |

### 8.2 RAG 检索架构

```
查询（来自任意 Agent）
        │
        ▼
┌───────────────────┐
│  Query Router     │ ← 根据查询意图路由到不同检索策略
└───────┬───────────┘
        │
   ┌────┼────────────────┐
   │    │                │
   ▼    ▼                ▼
┌──────┐ ┌────────────┐ ┌──────────────┐
│向量   │ │关键词+标签  │ │结构化查询     │
│检索   │ │检索        │ │(SQL)         │
│(pgvec)│ │(全文索引)   │ │              │
└──┬───┘ └─────┬──────┘ └──────┬───────┘
   │           │               │
   └───────────┼───────────────┘
               │
               ▼
       ┌───────────────┐
       │  Re-Ranker    │ ← 基于查询相关性重排
       └───────┬───────┘
               │
               ▼
       ┌───────────────┐
       │  Citation      │ ← 附带来源引用
       │  Generator     │
       └───────────────┘
```

### 8.3 知识条目 Schema

```python
class KnowledgeEntry(BaseModel):
    id: str
    category: str          # "isa_spec" | "community_norm" | "historical_patch" | ...
    title: str
    content: str
    embedding: list[float] # 向量嵌入（1536 维，text-embedding-3-small）
    metadata: KnowledgeMetadata

class KnowledgeMetadata(BaseModel):
    repo: str | None = None
    subsystem: str | None = None
    architecture: str = "riscv"
    tags: list[str] = []
    source_url: str | None = None
    created_at: datetime
    updated_at: datetime
    citation_count: int = 0        # 被 Agent 引用次数
    usefulness_score: float = 0.0  # 人工标注的有用性评分
```

### 8.4 知识摄入流水线

知识库需要持续从多个来源摄入、处理和更新知识条目：

```
数据源                    摄入流水线                        存储
┌──────────────┐     ┌─────────────────────┐     ┌──────────────┐
│ RISC-V Spec  │────▶│ 1. 文档抓取/拉取     │────▶│              │
│ Linux 内核文档│────▶│ 2. 格式标准化        │     │  PostgreSQL  │
│ 邮件列表归档  │────▶│ 3. 分块 (Chunking)   │────▶│  + pgvector  │
│ Git 提交历史  │────▶│ 4. Embedding 生成    │     │              │
│ Issue/PR 讨论 │────▶│ 5. 元数据提取        │────▶│              │
└──────────────┘     │ 6. 去重 + 冲突检测    │     └──────────────┘
                     └─────────────────────┘
```

**分块策略**：

```python
class ChunkingStrategy:
    """文档分块策略——按语义边界切分，而非固定长度"""

    CHUNK_SIZE = 1024       # 目标 token 数
    CHUNK_OVERLAP = 128     # 重叠 token 数（保持上下文连贯）

    @staticmethod
    def chunk_document(doc: str, doc_type: str) -> list[dict]:
        match doc_type:
            case "spec":
                return ChunkingStrategy._chunk_by_section(doc)
            case "email":
                return ChunkingStrategy._chunk_by_thread(doc)
            case "code":
                return ChunkingStrategy._chunk_by_function(doc)
            case "commit":
                return [{"text": doc, "type": "commit"}]  # 单条不分块
            case _:
                return ChunkingStrategy._chunk_by_paragraph(doc)

    @staticmethod
    def _chunk_by_section(doc: str) -> list[dict]:
        """按 Markdown/RST 标题层级切分，保留层级路径作为元数据"""
        ...

    @staticmethod
    def _chunk_by_function(code: str) -> list[dict]:
        """按函数/结构体定义切分（使用 tree-sitter 解析 C/ASM）"""
        ...
```

**Embedding 生成**：

| 模型 | 维度 | 用途 | 成本 |
|------|------|------|------|
| `text-embedding-3-small` | 1536 | 通用文档检索 | $0.02/1M tokens |
| `text-embedding-3-large` | 3072 | 高精度代码检索（备选） | $0.13/1M tokens |

MVP 阶段使用 `text-embedding-3-small`，通过 `cosine` 距离检索。

**增量更新与过期淘汰**：

```python
class KnowledgeIngestionPipeline:
    """知识摄入流水线"""

    async def incremental_update(self, source: str) -> IngestionReport:
        """增量更新：只处理自上次摄入以来的新内容"""
        last_checkpoint = await self.db.get_checkpoint(source)
        new_docs = await self.fetcher.fetch_since(source, last_checkpoint)

        for doc in new_docs:
            content_hash = hashlib.sha256(doc.content.encode()).hexdigest()
            existing = await self.db.find_by_hash(content_hash)
            if existing:
                continue  # 去重：内容未变则跳过

            chunks = ChunkingStrategy.chunk_document(doc.content, doc.type)
            embeddings = await self.embedder.batch_embed([c["text"] for c in chunks])

            for chunk, embedding in zip(chunks, embeddings):
                await self.db.upsert_knowledge_entry(
                    content=chunk["text"],
                    embedding=embedding,
                    metadata=doc.metadata | chunk,
                    content_hash=content_hash,
                    source=source,
                )

        await self.db.update_checkpoint(source, datetime.utcnow())

    async def expire_stale_entries(self, max_age_days: int = 180) -> int:
        """淘汰过期知识：超过 max_age_days 未被引用且 usefulness_score < 0.3"""
        return await self.db.soft_delete_stale(
            max_age_days=max_age_days,
            min_usefulness=0.3,
            min_citations=1,
        )
```

**摄入调度**：通过 cron 定时触发，不同来源频率不同：

| 来源 | 摄入频率 | 说明 |
|------|---------|------|
| RISC-V Spec | 每月 | 规范更新不频繁 |
| Linux 内核文档 | 每周 | 跟踪 linux-next |
| 邮件列表 | 每日 | 高频信息源 |
| Git 提交历史 | 每日 | 跟踪上游变更 |
| Issue/PR | 每 6 小时 | 活跃讨论 |

---

## 9. 可观测性设计

### 9.1 双 SDK 统一追踪

两个 SDK 的追踪数据需要统一到一个可观测性平台：

```
┌─────────────────────────────────────────────────────┐
│                  Grafana Dashboard                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ 案例进度  │  │ Agent    │  │ 成本与 Token     │  │
│  │ 看板      │  │ 性能指标  │  │ 消耗监控         │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
└─────────────────────────┬───────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│              OpenTelemetry Collector                  │
└──────────┬──────────────────────────┬───────────────┘
           │                          │
           ▼                          ▼
┌──────────────────┐      ┌──────────────────────────┐
│ OpenAI Agents SDK│      │ Claude Agent SDK          │
│ 内置 Tracing     │      │ 消息流 → 自定义 Span     │
│                  │      │                          │
│ · agent_span     │      │ · AssistantMessage span  │
│ · tool_span      │      │ · ToolUseBlock span      │
│ · handoff_span   │      │ · ResultMessage span     │
│ · guardrail_span │      │ · TaskNotification span  │
└──────────────────┘      └──────────────────────────┘
```

### 9.2 关键指标（Metrics）

| 指标 | 类型 | 说明 |
|------|------|------|
| `case.duration.total` | Histogram | 案例从创建到完成的总耗时 |
| `case.duration.per_phase` | Histogram | 各阶段耗时 |
| `case.human_review.wait_time` | Histogram | 人工审核等待时间 |
| `agent.invocation.count` | Counter | 各 Agent 调用次数 |
| `agent.invocation.duration` | Histogram | 各 Agent 单次执行耗时 |
| `agent.invocation.error_rate` | Gauge | 各 Agent 错误率 |
| `agent.tokens.input` | Counter | 输入 Token 消耗 |
| `agent.tokens.output` | Counter | 输出 Token 消耗 |
| `agent.cost.usd` | Counter | API 成本（按 Agent 分） |
| `dev_review.iterations` | Histogram | 开发-审核迭代次数分布 |
| `dev_review.convergence_rate` | Gauge | 迭代收敛率（5 轮内通过的比例） |
| `mcp.tool.call_count` | Counter | MCP 工具调用次数 |
| `mcp.tool.error_rate` | Gauge | MCP 工具错误率 |
| `mcp.tool.latency` | Histogram | MCP 工具调用延迟 |
| `knowledge.rag.hit_rate` | Gauge | RAG 检索命中率 |

### 9.3 告警规则

```yaml
alerts:
  - name: agent_error_rate_high
    condition: agent.invocation.error_rate > 0.2
    duration: 5m
    severity: critical
    action: pause_pipeline_and_notify

  - name: dev_review_not_converging
    condition: dev_review.iterations == MAX_ITERATIONS
    severity: high
    action: escalate_to_human

  - name: cost_budget_exceeded
    condition: agent.cost.usd > case.budget_usd * 0.8
    severity: warning
    action: notify_and_switch_to_cheaper_model

  - name: human_review_stale
    condition: case.human_review.wait_time > 24h
    severity: medium
    action: send_reminder_notification
```

### 9.4 成本控制与预算管理

```python
from dataclasses import dataclass

@dataclass
class BudgetConfig:
    max_per_case_usd: float = 15.0       # 单案例硬上限
    warn_threshold_pct: float = 0.7       # 70% 时告警
    degrade_threshold_pct: float = 0.85   # 85% 时降级模型
    model_fallback_chain: dict = None     # 降级链

    def __post_init__(self):
        if self.model_fallback_chain is None:
            self.model_fallback_chain = {
                "claude-sonnet-4-6": "claude-haiku-4-5",
                "gpt-4o": "gpt-4o-mini",
            }

class CostTracker:
    """跨阶段成本追踪器"""

    def __init__(self, case_id: str, budget: BudgetConfig, metrics: MetricsCollector):
        self.case_id = case_id
        self.budget = budget
        self.metrics = metrics
        self._spent_usd: float = 0.0
        self._phase_costs: dict[str, float] = {}

    def record(self, phase: str, agent: str, token_usage: TokenUsage) -> None:
        cost = self._calculate_cost(agent, token_usage)
        self._spent_usd += cost
        self._phase_costs[phase] = self._phase_costs.get(phase, 0) + cost
        self.metrics.record_cost(self.case_id, phase, agent, cost)

    def check_budget(self) -> str:
        """返回预算状态：'ok' | 'warn' | 'degrade' | 'exceeded'"""
        ratio = self._spent_usd / self.budget.max_per_case_usd
        if ratio >= 1.0:
            return "exceeded"
        elif ratio >= self.budget.degrade_threshold_pct:
            return "degrade"
        elif ratio >= self.budget.warn_threshold_pct:
            return "warn"
        return "ok"

    def get_model_for_agent(self, agent: str, default_model: str) -> str:
        """根据预算状态决定使用的模型"""
        status = self.check_budget()
        if status == "degrade":
            return self.budget.model_fallback_chain.get(default_model, default_model)
        if status == "exceeded":
            raise BudgetExceededError(
                f"Case {self.case_id} exceeded budget: "
                f"${self._spent_usd:.2f} / ${self.budget.max_per_case_usd}"
            )
        return default_model

    @property
    def remaining_usd(self) -> float:
        return max(0, self.budget.max_per_case_usd - self._spent_usd)

    @property
    def summary(self) -> dict:
        return {
            "total_spent_usd": round(self._spent_usd, 4),
            "remaining_usd": round(self.remaining_usd, 4),
            "budget_status": self.check_budget(),
            "phase_breakdown": {k: round(v, 4) for k, v in self._phase_costs.items()},
        }
```

**与 Pipeline Engine 集成**：每个 Agent 调用前调用 `cost_tracker.get_model_for_agent()` 获取实际模型，调用后调用 `cost_tracker.record()` 记录消耗。预算超限时 Pipeline 进入 `BUDGET_EXCEEDED` 状态，等待人工决策（追加预算或放弃）。

---

## 10. 安全设计

### 10.1 威胁模型

| 威胁 | 攻击面 | 缓解措施 |
|------|--------|---------|
| Prompt 注入 | 邮件列表/Issue 中的恶意内容被 Agent 执行 | 输入净化 + Guardrails + 沙箱隔离 |
| 代码注入 | 开发 Agent 生成的代码包含恶意逻辑 | 审核 Agent 安全审查 + 人工审核 + 静态分析 |
| 命令注入 | Agent 通过 Bash 工具执行恶意命令 | `can_use_tool` 白名单 + 命令模式匹配 |
| 凭据泄露 | API Key 或仓库凭据被写入代码/日志 | 环境变量注入 + 日志脱敏 + 审计扫描 |
| 供应链攻击 | 恶意依赖被引入 | 依赖锁定 + 签名验证 + 沙箱网络隔离 |
| 数据泄露 | 私有仓库代码被发送到外部 API | 网络策略 + 数据分类 + 审计日志 |

### 10.2 沙箱隔离策略

```python
# 开发 Agent 沙箱配置
dev_sandbox = ClaudeAgentOptions(
    sandbox={
        "filesystem": "read_write",      # 仅限 worktree 目录
        "network": "restricted",          # 仅允许访问 MCP Server
        "max_file_size_mb": 10,           # 单文件大小限制
        "max_total_size_mb": 100,         # 总文件大小限制
    },
    cwd=worktree_path,                    # 限制工作目录
    env={
        "HOME": "/tmp/agent-home",        # 隔离 HOME 目录
        "PATH": "/usr/bin:/bin",          # 最小 PATH
    },
    disallowed_tools=["WebFetch", "WebSearch"],  # 禁止网络访问
)

# 测试 Agent 沙箱配置
# 注意：测试 Agent 需要 git apply 补丁、写测试输出和日志，因此不能设为 read_only。
# 通过 can_use_tool 回调限制只允许测试相关的写操作（见 Section 4.5）。
test_sandbox = ClaudeAgentOptions(
    sandbox={
        "filesystem": "read_write",       # 需要 git apply + 写测试输出
        "network": "restricted",          # 仅允许访问 MCP Server（QEMU 镜像拉取等）
        "max_file_size_mb": 50,           # 测试日志可能较大
        "max_total_size_mb": 500,         # 含 QEMU 镜像和编译产物
    },
    cwd=worktree_path,                    # 限制工作目录
    env={
        "HOME": "/tmp/test-agent-home",
        "PATH": "/usr/bin:/bin:/usr/local/bin",  # 需要交叉编译工具链
    },
    disallowed_tools=["WebFetch", "WebSearch"],  # 禁止直接网络访问
    # Write/Edit 通过 can_use_tool 限制为仅允许写入 test-output/ 目录
)
```

### 10.3 凭据管理

```python
# 所有凭据通过环境变量注入，绝不硬编码
REQUIRED_SECRETS = {
    "ANTHROPIC_API_KEY": "Claude Agent SDK 认证",
    "OPENAI_API_KEY": "OpenAI Agents SDK 认证",
    "POSTGRES_DSN": "数据库连接",
    "REDIS_URL": "缓存连接",
    "MINIO_ACCESS_KEY": "对象存储认证",
    "MINIO_SECRET_KEY": "对象存储认证",
}

def validate_secrets():
    """启动时验证所有必需凭据"""
    missing = [k for k in REQUIRED_SECRETS if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"缺少必需凭据: {', '.join(missing)}")
```

---

## 11. 数据模型与状态持久化

### 11.1 核心数据模型

```python
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class CaseStatus(str, Enum):
    CREATED = "created"
    EXPLORING = "exploring"
    EXPLORE_DONE = "explore_done"
    HUMAN_REVIEW_EXPLORE = "human_review_explore"
    PLANNING = "planning"
    PLAN_DONE = "plan_done"
    HUMAN_REVIEW_PLAN = "human_review_plan"
    DEVELOPING = "developing"
    REVIEWING = "reviewing"
    DEV_REVIEW_ITERATING = "dev_review_iterating"
    HUMAN_REVIEW_DEV = "human_review_dev"
    TESTING = "testing"
    HUMAN_REVIEW_TEST = "human_review_test"
    READY_FOR_UPSTREAM = "ready_for_upstream"
    ABANDONED = "abandoned"
    ESCALATED = "escalated"

class ContributionCase(BaseModel):
    id: str = Field(description="唯一案例 ID")
    status: CaseStatus
    created_at: datetime
    updated_at: datetime

    # 输入
    input_context: InputContext
    repo_url: str
    target_branch: str

    # 各阶段产物
    exploration_result: ExplorationResult | None = None
    execution_plan: ExecutionPlan | None = None
    development_result: DevelopmentResult | None = None
    review_history: list[ReviewVerdict] = []
    test_result: TestResult | None = None

    # 人工审核记录
    human_reviews: list[HumanReview] = []

    # 审计
    audit_trail: list[AuditEntry] = []

class AuditEntry(BaseModel):
    timestamp: datetime
    phase: str
    action: str
    agent: str              # "explorer" | "planner" | "developer" | "reviewer" | "tester" | "human"
    sdk: str                # "claude_agent_sdk" | "openai_agents_sdk" | "human"
    model: str | None       # "claude-opus-4-6" | "gpt-4o" | "o3-mini" | None
    input_summary: str
    output_summary: str
    tool_calls: list[dict]
    tokens_used: int
    cost_usd: float
    duration_ms: int
```

### 11.2 持久化策略

| 数据类型 | 存储 | 理由 |
|---------|------|------|
| ContributionCase 状态 | PostgreSQL | 事务性强，支持复杂查询和状态回溯 |
| 审计日志 | PostgreSQL + 追加写入 | 不可变审计链，支持合规审查 |
| Agent 会话上下文 | Redis + Claude SessionStore | 开发 Agent 需要跨迭代保持上下文 |
| 代码产物（patch/diff） | MinIO/S3 | 大文件对象存储，版本化 |
| 测试日志和报告 | MinIO/S3 | 大文件，需要长期归档 |
| RISC-V 知识库 | PostgreSQL + pgvector | 结构化元数据 + 向量检索 |
| OpenAI Tracing 数据 | OpenAI 平台 / 本地导出 | 利用 SDK 内置 Tracing |

### 11.3 会话恢复机制

Claude Agent SDK 的 `SessionStore` 支持开发 Agent 在迭代间保持上下文：

```python
from claude_agent_sdk import ClaudeAgentOptions, InMemorySessionStore

# 生产环境使用 PostgreSQL 或 Redis 适配器
session_store = PostgresSessionStore(dsn="postgresql://...")

# 首次开发
options = ClaudeAgentOptions(
    session_store=session_store,
    session_id=f"dev-{case.id}",
)

# 迭代修复时恢复会话
options_resume = ClaudeAgentOptions(
    session_store=session_store,
    session_id=f"dev-{case.id}",  # 同一 session_id 自动恢复上下文
)
```

---

## 12. 部署架构

### 12.1 部署拓扑

```
┌─────────────────────────────────────────────────────────────┐
│                     控制面 (Control Plane)                    │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ FastAPI  │  │ Pipeline │  │ Human    │  │ Audit      │  │
│  │ Gateway  │  │ Engine   │  │ Gate Svc │  │ Logger     │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ Web      │  │ Session  │  │ MCP      │                  │
│  │ Console  │  │ Manager  │  │ Registry │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Agent Worker │ │ Agent Worker │ │ Agent Worker │
│ Pool (Claude)│ │ Pool (OpenAI)│ │ Pool (MCP)   │
│              │ │              │ │              │
│ Claude Code  │ │ OpenAI API   │ │ MCP Servers  │
│ CLI 子进程   │ │ 直接调用      │ │ 独立进程      │
└──────────────┘ └──────────────┘ └──────────────┘
              │            │            │
              ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────┐
│                     数据面 (Data Plane)                       │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │PostgreSQL│  │  Redis   │  │ MinIO/S3 │  │ pgvector   │  │
│  │(状态/审计)│  │(缓存/会话)│  │(产物存储) │  │(知识库)     │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│                   执行面 (Execution Plane)                    │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ QEMU RISC-V  │  │ 交叉编译     │  │ Git Worktree     │  │
│  │ 仿真环境      │  │ 工具链       │  │ 隔离工作区        │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 12.2 资源估算

| 组件 | 资源需求 | 说明 |
|------|---------|------|
| Claude Agent SDK Worker | 每会话 ~200MB 内存（CLI 子进程） | 开发/测试 Agent 各需独立进程 |
| OpenAI Agents SDK Worker | 轻量级，~50MB 内存 | 纯 API 调用，无子进程 |
| MCP Server | 每 Server ~100MB | 独立进程，按需启停 |
| PostgreSQL | 4GB+ RAM | 状态、审计、知识库 |
| Redis | 2GB+ RAM | 会话缓存、消息队列 |
| QEMU 仿真 | 每实例 2-4GB RAM | 测试执行环境 |

### 12.3 模型成本估算（单案例）

| Agent | 模型 | 预估 Token 消耗 | 预估成本 |
|-------|------|----------------|---------|
| 探索 Agent | GPT-4o | ~20K input + 5K output | ~$0.15 |
| 规划 Agent | o3-mini | ~15K input + 8K output | ~$0.10 |
| 开发 Agent (×3 轮) | Claude Opus 4.6 | ~150K input + 30K output | ~$6.00 |
| 审核 Agent (×3 轮) | GPT-4o | ~60K input + 15K output | ~$0.50 |
| 测试 Agent | Claude Sonnet 4.6 | ~30K input + 10K output | ~$0.30 |
| **单案例总计** | | | **~$7.05** |

### 12.4 容器化部署（Docker Compose）

```yaml
# docker-compose.yml（开发/测试环境）
version: "3.9"
services:
  # ── 控制面 ──
  api-gateway:
    build: ./services/api-gateway
    ports: ["8000:8000"]
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - POSTGRES_DSN=postgresql://rv:rv@postgres:5432/rv_insights
      - REDIS_URL=redis://redis:6379/0
    depends_on: [postgres, redis]

  pipeline-engine:
    build: ./services/pipeline-engine
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - POSTGRES_DSN=postgresql://rv:rv@postgres:5432/rv_insights
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
    volumes:
      - worktrees:/var/lib/rv-insights/worktrees
      - claude-cli:/home/app/.claude
    depends_on: [postgres, redis, minio]

  # ── MCP Servers ──
  mcp-maillist:
    build: ./mcp-servers/maillist
    ports: ["9001:9001"]

  mcp-git-tools:
    build: ./mcp-servers/git-tools
    volumes:
      - worktrees:/var/lib/rv-insights/worktrees

  mcp-knowledge:
    build: ./mcp-servers/knowledge
    depends_on: [postgres]

  # ── 数据面 ──
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: rv
      POSTGRES_PASSWORD: rv
      POSTGRES_DB: rv_insights
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:7-alpine
    volumes:
      - redisdata:/data

  minio:
    image: minio/minio
    command: server /data --console-address ":9090"
    volumes:
      - miniodata:/data

  # ── 执行面 ──
  qemu-runner:
    build: ./services/qemu-runner
    privileged: true
    volumes:
      - worktrees:/var/lib/rv-insights/worktrees

volumes:
  pgdata:
  redisdata:
  miniodata:
  worktrees:
  claude-cli:
```

### 12.5 PostgreSQL Schema（核心表）

```sql
-- 案例表
CREATE TABLE contribution_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status VARCHAR(50) NOT NULL DEFAULT 'created',
    input_context JSONB NOT NULL,
    repo_url TEXT NOT NULL,
    target_branch TEXT NOT NULL DEFAULT 'master',
    exploration_result JSONB,
    execution_plan JSONB,
    development_result JSONB,
    test_result JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_cases_status ON contribution_cases(status);
CREATE INDEX idx_cases_created ON contribution_cases(created_at DESC);

-- 人工审核表
CREATE TABLE human_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES contribution_cases(id),
    phase VARCHAR(50) NOT NULL,
    reviewer VARCHAR(100) NOT NULL,
    decision VARCHAR(20) NOT NULL,
    comments TEXT,
    reject_to_phase VARCHAR(50),
    artifacts JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_reviews_case ON human_reviews(case_id, phase);
CREATE INDEX idx_reviews_pending ON human_reviews(case_id) WHERE decision IS NULL;

-- 审计日志表（追加写入，不可修改）
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    case_id UUID NOT NULL REFERENCES contribution_cases(id),
    phase VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    agent VARCHAR(50) NOT NULL,
    sdk VARCHAR(30) NOT NULL,
    model VARCHAR(50),
    input_summary TEXT,
    output_summary TEXT,
    tool_calls JSONB DEFAULT '[]',
    tokens_used INTEGER DEFAULT 0,
    cost_usd NUMERIC(10, 6) DEFAULT 0,
    duration_ms INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_case ON audit_log(case_id, created_at);
CREATE INDEX idx_audit_agent ON audit_log(agent, created_at);

-- 知识库表
CREATE TABLE knowledge_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_knowledge_category ON knowledge_entries(category);
CREATE INDEX idx_knowledge_embedding ON knowledge_entries
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### 12.6 配置管理

使用 Pydantic Settings 管理多环境配置，支持 `.env` 文件和环境变量覆盖：

```python
from pydantic_settings import BaseSettings

class RVInsightsSettings(BaseSettings):
    """全局配置——通过环境变量或 .env 文件注入"""

    # ── 环境标识 ──
    env: str = "development"  # development | staging | production

    # ── 数据库 ──
    database_url: str = "postgresql+asyncpg://rv:rv@localhost:5432/rv_insights"
    redis_url: str = "redis://localhost:6379/0"

    # ── Claude Agent SDK ──
    claude_api_key: str
    claude_default_model: str = "claude-sonnet-4-6"
    claude_max_turns: int = 30
    claude_max_budget_usd: float = 5.0

    # ── OpenAI Agents SDK ──
    openai_api_key: str
    openai_default_model: str = "gpt-4o"

    # ── 预算 ──
    budget_max_per_case_usd: float = 15.0
    budget_warn_threshold: float = 0.7
    budget_degrade_threshold: float = 0.85

    # ── Worker Pool ──
    worker_claude_max: int = 2
    worker_openai_max: int = 10
    worker_qemu_max: int = 1
    worker_cases_max: int = 3

    # ── 通知 ──
    notification_channels: list[str] = ["sse"]
    slack_webhook_url: str | None = None
    smtp_host: str | None = None

    # ── 知识库 ──
    embedding_model: str = "text-embedding-3-small"
    knowledge_chunk_size: int = 1024

    # ── 安全 ──
    jwt_secret: str = "change-me-in-production"
    api_rate_limit: int = 100  # requests per minute

    model_config = {"env_prefix": "RV_", "env_file": ".env"}
```

**环境差异**：

| 配置项 | development | staging | production |
|--------|------------|---------|------------|
| `claude_default_model` | `claude-haiku-4-5` | `claude-sonnet-4-6` | `claude-sonnet-4-6` |
| `openai_default_model` | `gpt-4o-mini` | `gpt-4o` | `gpt-4o` |
| `budget_max_per_case_usd` | 1.0 | 10.0 | 15.0 |
| `worker_cases_max` | 1 | 2 | 3 |
| `notification_channels` | `["sse"]` | `["sse", "webhook"]` | `["sse", "webhook", "email"]` |

`.env.example` 随代码库提交，`.env` 在 `.gitignore` 中。

### 12.7 Schema 迁移策略

使用 Alembic 管理 PostgreSQL schema 版本：

```
rv-insights/
├── alembic/
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
│       ├── 001_initial_schema.py
│       ├── 002_add_knowledge_entries.py
│       └── ...
```

```python
# alembic/versions/001_initial_schema.py
def upgrade():
    op.create_table("contribution_cases", ...)
    op.create_table("human_reviews", ...)
    op.create_table("audit_log", ...)

def downgrade():
    op.drop_table("audit_log")
    op.drop_table("human_reviews")
    op.drop_table("contribution_cases")
```

**迁移规范**：
- 每次 schema 变更必须有对应的 Alembic migration
- `upgrade()` 和 `downgrade()` 都必须实现
- 生产环境迁移前先在 staging 验证
- 大表变更使用 `op.execute()` 分批处理，避免长时间锁表
- CI 中自动运行 `alembic check` 确保 migration 与 model 同步

---

## 13. MVP 范围与实施路线

### 13.1 MVP 范围

**In Scope**：
- 1 个试点仓库（建议：Linux kernel RISC-V arch 子目录 或 QEMU RISC-V target）
- 5 个 Agent 节点的最小闭环
- 4 个人工审核门禁
- 开发-审核迭代闭环（最多 5 轮）
- 3 个 MCP Server：邮件列表、Git 工具、知识库
- PostgreSQL 状态持久化 + 审计日志
- CLI 入口（Web Console 可后置）

**Out of Scope（MVP 后）**：
- 多仓库并行
- 真实硬件测试（MVP 阶段用 QEMU）
- 自动向上游提交
- Web Console 完整 UI
- A2A 跨平台 Agent 协作

### 13.2 实施路线

```
Phase 0: 基础设施搭建（2 周）
├── Python 项目骨架（asyncio + Pydantic）
├── PostgreSQL schema + 审计表
├── Claude Agent SDK + OpenAI Agents SDK 集成验证
├── 基础 MCP Server 框架
└── Git worktree 管理工具

Phase 1: 单 Agent 验证（3 周）
├── 探索 Agent：接入邮件列表 + 代码库分析
├── 规划 Agent：结构化方案输出
├── 开发 Agent：Claude Code 代码生成
├── 审核 Agent：多维度代码审查
└── 测试 Agent：QEMU 环境测试执行

Phase 2: 流水线集成（3 周）
├── Pipeline Engine 状态机
├── 人工审核门禁服务
├── 开发-审核迭代闭环
├── 跨 SDK 数据传递
└── 审计日志全链路

Phase 3: 端到端验证（2 周）
├── 选取 3-5 个真实贡献案例
├── 跑通完整流水线
├── 收集质量指标
└── 迭代优化 prompt 和工具

Phase 4: 生产化加固（2 周）
├── 错误恢复和重试机制
├── 会话持久化和断点续传
├── 成本监控和预算控制
└── CLI 入口完善

总计：~12 周
```

> **详细任务清单**：各阶段 57 个细粒度开发任务（含依赖关系、验收标准、测试要求、预估工时）见 [rv-insights-tasks.md](./rv-insights-tasks.md)。

### 13.3 MVP 验收标准

| 验收项 | 标准 | 验证方式 |
|--------|------|---------|
| 端到端闭环 | 至少 1 个案例跑通从探索到测试的完整流水线 | 人工验证产物质量 |
| 人工审核门禁 | 4 个审核点均可正常暂停/通过/驳回 | 功能测试 |
| 开发-审核迭代 | 至少 1 个案例经历 2+ 轮迭代后通过审核 | 审计日志验证 |
| 补丁质量 | 生成的 patch 可通过 `checkpatch.pl --strict` | 自动化检查 |
| 编译通过 | 生成的 patch 可通过 RISC-V 交叉编译 | CI 验证 |
| QEMU 测试 | 至少 1 个案例通过 QEMU boot 测试 | 测试 Agent 输出 |
| 审计完整性 | 所有 Agent 调用和人工决策均有审计记录 | 数据库查询验证 |
| 成本可控 | 单案例成本不超过 $15 | 成本监控 |
| 断点续传 | 流水线中断后可从最近的检查点恢复 | 故障注入测试 |

### 13.4 试点仓库选择标准

| 标准 | 权重 | 说明 |
|------|------|------|
| RISC-V 代码占比 | 高 | 仓库中 RISC-V 特定代码越多越好 |
| 社区活跃度 | 高 | 邮件列表/PR 活跃，有快速反馈 |
| 贡献门槛 | 中 | 不要求 CLA 签署或复杂流程 |
| 测试基础设施 | 中 | 有现成的 CI/测试框架可复用 |
| 文档完善度 | 低 | CONTRIBUTING.md 和代码规范清晰 |

推荐试点：
1. **Linux kernel `arch/riscv/`**：最高价值，社区活跃，但贡献门槛较高
2. **QEMU `target/riscv/`**：门槛适中，测试友好，社区响应快
3. **OpenSBI**：代码量小，适合 MVP 验证，但贡献机会有限

---

## 14. 风险与缓解

### 14.1 技术风险

| 风险 | 概率 | 影响 | 缓解措施 | 监控指标 |
|------|:----:|:----:|---------|---------|
| Claude Code CLI 子进程资源开销大 | 高 | 中 | Worker Pool 限制并发（默认 2）；开发/测试 Agent 串行执行；空闲超时自动回收 | `system.memory.usage`, `agent.worker.pool_size` |
| 两个 SDK 版本升级不同步 | 中 | 中 | Pydantic 模型解耦 Agent 间通信；`pip freeze` 锁定版本；升级前在 staging 环境验证 | 依赖审计报告 |
| 开发-审核迭代不收敛 | 中 | 高 | 最大迭代 5 轮 + 连续 2 轮 findings 不减则提前升级 + 人工接管 | `dev_review.iterations`, `dev_review.convergence_rate` |
| 模型幻觉导致错误补丁 | 高 | 高 | 三层防线：AI 审核 → 静态分析（checkpatch/sparse/clang-tidy）→ 人工审核 | `review.finding.false_negative_rate` |
| OpenAI API 和 Claude API 同时不可用 | 低 | 高 | 任务持久化 + 断点续传 + 模型降级链 + 30 分钟内自动重试 | `api.availability`, `pipeline.recovery.success_rate` |
| RISC-V 领域知识不足 | 高 | 中 | RAG 知识库持续积累 + 人工审核兜底 + 维护者画像指导 prompt | `knowledge.rag.hit_rate`, `review.domain_error_rate` |
| 测试环境搭建失败 | 中 | 中 | QEMU 环境容器化 + 预构建镜像 + 环境健康检查 + 降级到纯编译测试 | `test.env_setup.failure_rate` |
| Prompt 注入攻击 | 中 | 高 | 输入净化 + Guardrails + 沙箱隔离 + 人工审核 | `security.prompt_injection.detected` |
| 成本失控 | 中 | 中 | `max_budget_usd` 硬限制 + 实时成本监控 + 超预算自动降级模型 | `agent.cost.usd`, `case.total_cost` |

### 14.2 运营风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|:----:|:----:|---------|
| 人工审核成为瓶颈 | 高 | 中 | 审核超时提醒（24h）+ 审核优先级队列 + 渐进式自动化（低风险操作逐步放开） |
| 上游社区不接受 AI 生成的补丁 | 中 | 高 | 补丁中不标注 AI 生成（由人工审核者以个人名义提交）+ 确保补丁质量超过人工平均水平 |
| 知识库数据过时 | 中 | 中 | 定时同步（每日增量）+ 知识条目 TTL + 引用计数衰减 |
| 团队对双 SDK 的学习曲线 | 中 | 低 | 统一 AgentAdapter 接口屏蔽差异 + 详细的开发者文档 + 示例代码 |

### 14.3 风险应对决策树

```
Agent 执行失败
    │
    ├── API 速率限制？
    │   └── 指数退避重试（最多 3 次）
    │
    ├── API 不可用？
    │   ├── 尝试降级模型（Opus → Sonnet → Haiku）
    │   └── 降级也失败 → 暂停案例，等待恢复
    │
    ├── Agent 超时？
    │   ├── 首次 → 重试（增加 timeout）
    │   └── 再次超时 → 升级人工
    │
    ├── 输出格式错误？
    │   ├── Guardrail 触发 → 自动重试（最多 2 次）
    │   └── 持续失败 → 升级人工
    │
    └── 未知错误？
        └── 记录完整上下文 → 暂停案例 → 通知人工
```

---

## 附录 A：项目目录结构

```
rv-insights/
├── pyproject.toml                    # 项目配置（uv/poetry）
├── docker-compose.yml                # 容器编排
├── .env.example                      # 环境变量模板
│
├── src/
│   ├── rv_insights/
│   │   ├── __init__.py
│   │   ├── cli.py                    # CLI 入口（click/typer）
│   │   ├── config.py                 # 全局配置
│   │   │
│   │   ├── models/                   # Pydantic 数据模型（跨 SDK 契约）
│   │   │   ├── __init__.py
│   │   │   ├── case.py               # ContributionCase, CaseStatus
│   │   │   ├── exploration.py        # ExplorationResult, EvidenceItem
│   │   │   ├── planning.py           # ExecutionPlan, DevPlan, TestPlan
│   │   │   ├── development.py        # DevelopmentResult, ChangedFile
│   │   │   ├── review.py             # ReviewVerdict, ReviewFinding
│   │   │   ├── testing.py            # TestResult, TestCaseResult
│   │   │   └── audit.py              # AuditEntry, HumanReview
│   │   │
│   │   ├── engine/                   # 编排引擎
│   │   │   ├── __init__.py
│   │   │   ├── pipeline.py           # PipelineEngine 状态机
│   │   │   ├── human_gate.py         # HumanGateService
│   │   │   ├── dev_review_loop.py    # 开发-审核迭代闭环
│   │   │   └── state_machine.py      # 状态转换规则
│   │   │
│   │   ├── agents/                   # Agent 实现
│   │   │   ├── __init__.py
│   │   │   ├── adapter.py            # AgentAdapter 基类
│   │   │   ├── explorer/             # 探索 Agent（OpenAI SDK）
│   │   │   │   ├── __init__.py
│   │   │   │   ├── agent.py          # Agent 定义
│   │   │   │   ├── tools.py          # 工具函数
│   │   │   │   └── guardrails.py     # 输入/输出校验
│   │   │   ├── planner/              # 规划 Agent（OpenAI SDK）
│   │   │   ├── developer/            # 开发 Agent（Claude SDK）
│   │   │   ├── reviewer/             # 审核 Agent（OpenAI SDK）
│   │   │   └── tester/               # 测试 Agent（Claude SDK）
│   │   │
│   │   ├── mcp_servers/              # MCP Server 实现
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # MCPServerBase
│   │   │   ├── maillist/             # 邮件列表 MCP
│   │   │   ├── git_tools/            # Git 工具 MCP
│   │   │   ├── knowledge/            # 知识库 MCP
│   │   │   ├── test_runner/          # 测试执行 MCP
│   │   │   └── static_analysis/      # 静态分析 MCP
│   │   │
│   │   ├── knowledge/                # 知识库
│   │   │   ├── __init__.py
│   │   │   ├── indexer.py            # 知识条目索引
│   │   │   ├── retriever.py          # RAG 检索
│   │   │   └── sync.py              # 数据同步
│   │   │
│   │   ├── observability/            # 可观测性
│   │   │   ├── __init__.py
│   │   │   ├── tracing.py            # 统一追踪
│   │   │   ├── metrics.py            # 指标收集
│   │   │   └── alerts.py             # 告警规则
│   │   │
│   │   └── storage/                  # 持久化
│   │       ├── __init__.py
│   │       ├── postgres.py           # PostgreSQL 操作
│   │       ├── redis_store.py        # Redis 操作
│   │       ├── s3.py                 # MinIO/S3 操作
│   │       └── session_store.py      # Claude SessionStore 适配
│   │
│   └── sql/
│       ├── init.sql                  # 初始化 schema
│       └── migrations/               # 数据库迁移
│
├── tests/
│   ├── unit/                         # 单元测试
│   ├── integration/                  # 集成测试
│   └── e2e/                          # 端到端测试
│
└── docs/
    └── rv-insights-design.md         # 本设计文档
```

## 附录 B：CLI 接口设计

```bash
# 创建新的贡献案例
rv-insights case create \
  --repo https://github.com/torvalds/linux \
  --branch master \
  --hint "RISC-V vector extension 缺少 vfwcvt 指令的测试覆盖"

# 从邮件列表自动探索
rv-insights explore \
  --list linux-riscv \
  --date-range 7d \
  --max-results 5

# 查看案例状态
rv-insights case status <case-id>

# 查看待审核列表
rv-insights review list --pending

# 提交审核决策
rv-insights review approve <case-id> --phase explore --comment "方向正确"
rv-insights review reject <case-id> --phase plan --comment "测试方案不完整"
rv-insights review reject-to <case-id> --phase test --to explore --comment "需要重新评估可行性"

# 查看审计日志
rv-insights audit show <case-id>
rv-insights audit cost --last 7d

# 知识库管理
rv-insights kb sync --source lore.kernel.org --list linux-riscv
rv-insights kb search "RISC-V vector extension vfwcvt"

# 系统管理
rv-insights system health
rv-insights system metrics --last 1h
```

## 附录 C：SDK 选型决策矩阵

| 评估维度 | Claude Agent SDK | OpenAI Agents SDK | 选型结论 |
|---------|:----------------:|:-----------------:|---------|
| 代码操作能力 | ⭐⭐⭐⭐⭐ | ⭐⭐ | 开发/测试 → Claude |
| 编排灵活性 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 探索/规划/审核 → OpenAI |
| 内置工具丰富度 | ⭐⭐⭐⭐⭐ | ⭐ | 需要文件操作 → Claude |
| 多 Agent 协作 | ⭐⭐⭐ (层级委托) | ⭐⭐⭐⭐⭐ (Handoff) | 需要灵活协作 → OpenAI |
| 人工介入机制 | ⭐⭐⭐⭐ (can_use_tool) | ⭐⭐⭐⭐ (Guardrails) | 两者各有优势，互补 |
| 可观测性 | ⭐⭐⭐ (hooks/消息流) | ⭐⭐⭐⭐⭐ (内置 Tracing) | 审核链路 → OpenAI |
| MCP 支持 | ⭐⭐⭐⭐⭐ (原生) | ⭐⭐⭐ (扩展) | 工具密集型 → Claude |
| 资源开销 | ⭐⭐ (子进程) | ⭐⭐⭐⭐⭐ (轻量) | 纯推理 → OpenAI |
| 会话持久化 | ⭐⭐⭐⭐ (SessionStore) | ⭐⭐ (无内置) | 需要跨轮上下文 → Claude |

---

## 附录 D：平台自身测试策略

RV-Insights 平台本身的质量保障——如何测试一个测试 AI 贡献的系统：

### D.1 测试金字塔

```
                    ┌─────────┐
                    │  E2E    │  2-3 个关键流程
                    │ (慢/贵) │  完整 Pipeline 端到端
                   ┌┴─────────┴┐
                   │ 集成测试   │  Agent ↔ SDK 交互
                   │ (中等)     │  Pipeline 状态转换
                  ┌┴───────────┴┐
                  │   单元测试    │  数据模型、工具函数
                  │   (快/多)    │  Prompt 模板渲染
                  └──────────────┘
```

### D.2 单元测试

```python
import pytest
from unittest.mock import AsyncMock

class TestPatchGenerator:
    def test_commit_message_validation_rejects_long_subject(self):
        gen = PatchGenerator()
        with pytest.raises(AssertionError, match="Subject line too long"):
            gen._validate_commit_message(
                MockCommit(message="x" * 80 + "\n\nSigned-off-by: Test <t@t>")
            )

    def test_commit_message_validation_rejects_missing_sob(self):
        gen = PatchGenerator()
        with pytest.raises(AssertionError, match="Missing Signed-off-by"):
            gen._validate_commit_message(
                MockCommit(message="riscv: fix something\n\nNo signoff here")
            )

class TestChunkingStrategy:
    def test_chunk_by_section_preserves_hierarchy(self):
        doc = "# Title\n## Sub1\nContent1\n## Sub2\nContent2"
        chunks = ChunkingStrategy.chunk_document(doc, "spec")
        assert len(chunks) >= 2
        assert all("text" in c for c in chunks)

class TestResourceScheduler:
    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrent_claude(self):
        config = WorkerPoolConfig(claude_max_concurrent=1)
        scheduler = ResourceScheduler(config)
        await scheduler.acquire_claude("case-1", "developer")
        # 第二次获取应该阻塞
        acquired = asyncio.Event()
        async def try_acquire():
            await scheduler.acquire_claude("case-2", "developer")
            acquired.set()
        task = asyncio.create_task(try_acquire())
        await asyncio.sleep(0.1)
        assert not acquired.is_set()
        scheduler.release_claude()
        await asyncio.wait_for(task, timeout=1.0)
        assert acquired.is_set()
```

### D.3 集成测试（Mock SDK 层）

```python
class TestPipelineIntegration:
    """集成测试：验证 Pipeline 状态转换，Mock 掉 SDK 调用"""

    @pytest.fixture
    def mock_claude_adapter(self):
        adapter = AsyncMock(spec=ClaudeAgentAdapter)
        adapter.run.return_value = DevelopmentResult(
            success=True,
            patches=["0001-test.patch"],
            files_modified=["arch/riscv/test.c"],
            commit_messages=["riscv: test fix"],
            token_usage=TokenUsage(input=1000, output=500),
        )
        return adapter

    @pytest.fixture
    def mock_openai_adapter(self):
        adapter = AsyncMock(spec=OpenAIAgentAdapter)
        adapter.run.return_value = ReviewVerdict(
            approved=True,
            findings=[],
            iteration=1,
            summary="LGTM",
        )
        return adapter

    @pytest.mark.asyncio
    async def test_happy_path_explore_to_ready(
        self, mock_claude_adapter, mock_openai_adapter
    ):
        """完整流水线：探索 → 规划 → 开发 → 审核 → 测试 → READY"""
        engine = PipelineEngine(
            claude_adapter=mock_claude_adapter,
            openai_adapter=mock_openai_adapter,
            human_gate=AutoApproveGate(),  # 测试用自动审批
        )
        case = create_test_case()
        result = await engine.run_case(case)
        assert result.status == "READY_FOR_UPSTREAM"

    @pytest.mark.asyncio
    async def test_dev_review_iteration_converges(
        self, mock_claude_adapter, mock_openai_adapter
    ):
        """开发-审核迭代：第一轮驳回，第二轮通过"""
        call_count = 0
        async def review_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ReviewVerdict(approved=False, findings=[...], iteration=1)
            return ReviewVerdict(approved=True, findings=[], iteration=2)

        mock_openai_adapter.run.side_effect = review_side_effect
        result = await run_dev_review_loop(...)
        assert result.approved
        assert call_count == 2
```

### D.4 E2E 测试

E2E 测试使用 Docker Compose 启动完整环境，跑真实 SDK 调用（使用低成本模型）：

```python
@pytest.mark.e2e
@pytest.mark.slow
class TestE2EPipeline:
    """E2E 测试：真实 SDK 调用，使用 Haiku/GPT-4o-mini 降低成本"""

    @pytest.fixture(scope="session")
    def e2e_env(self):
        """启动 Docker Compose 测试环境"""
        subprocess.run(["docker", "compose", "-f", "docker-compose.test.yml", "up", "-d"])
        yield
        subprocess.run(["docker", "compose", "-f", "docker-compose.test.yml", "down"])

    @pytest.mark.asyncio
    async def test_simple_typo_fix_e2e(self, e2e_env):
        """最简单的 E2E 场景：修复一个已知的 typo"""
        case = await create_case_via_api({
            "title": "Fix typo in arch/riscv/Kconfig",
            "source": "user",
            "description": "s/recieve/receive/ in line 42",
        })
        result = await wait_for_case_completion(case.id, timeout=300)
        assert result.status in ("READY_FOR_UPSTREAM", "HUMAN_REVIEW_PENDING")
```

**测试成本控制**：E2E 测试使用 `claude-haiku-4-5` + `gpt-4o-mini`，单次 E2E 运行成本 < $0.50。CI 中仅在 `main` 分支合并时运行 E2E，PR 只跑单元 + 集成。

---

## 附录 E：参考资料

- [Claude Agent SDK Python (GitHub)](https://github.com/anthropics/claude-agent-sdk-python)
- [Claude Agent SDK 官方文档](https://docs.anthropic.com/en/docs/agent-sdk/overview)
- [OpenAI Agents SDK (GitHub)](https://github.com/openai/openai-agents-python)
- [OpenAI Agents SDK 官方文档](https://openai.github.io/openai-agents-python)
- [OpenAI Agents SDK Handoffs](https://openai.github.io/openai-agents-python/handoffs/)
- [OpenAI Agents SDK Multi-Agent Orchestration](https://openai.github.io/openai-agents-python/multi_agent/)
- [OpenAI Agents SDK Tracing](https://openai.github.io/openai-agents-python/tracing/)
- [Multi-Model AI Agents: Combining Claude, GPT & Open-Source (Xcapit)](https://www.xcapit.com/en/blog/multi-model-ai-agents-workflow)
- [Custom Model Providers with OpenAI Agents SDK (CallSphere)](https://callsphere.tech/blog/custom-model-providers-openai-agents-sdk-any-llm-agent-brain)
- [Building Production-Ready Multi-Agent Systems with Claude Agent SDK (Claude Lab)](https://claudelab.net/en/articles/api-sdk/claude-agent-sdk-production-multi-agent-system)
- [Claude Agent SDK Guide (Claude Lab)](https://claudelab.net/en/articles/api-sdk/agent-sdk-guide)
- [Hybrid Agent Orchestration (CallSphere)](https://callsphere.tech/blog/hybrid-agent-orchestration-combining-handoffs-and-tools-openai-agents-sdk)
