# RV-Insights：大模型驱动的RISC-V多Agent开源贡献平台

## 1. 项目概述

### 1.1 背景与目标

RISC-V作为开放指令集架构，其软件生态的繁荣依赖于全球开发者的持续贡献。然而，RISC-V开源项目的贡献门槛较高：开发者需要深入理解邮件列表讨论、跟踪代码库演进、熟悉社区规范，并具备跨平台调试能力。这导致大量潜在的贡献者因信息不对称或技术门槛而放弃。

**RV-Insights** 旨在构建一个由大模型驱动的多Agent智能平台，自主完成从需求发现到代码提交的全流程，同时保留关键节点的人工审核权，实现"AI自主执行 + 人类质量把关"的协作模式。

### 1.2 核心流程

平台包含5个智能体节点，形成完整的贡献流水线：

```mermaid
flowchart LR
    A[探索Agent] --> B[规划Agent]
    B --> C[开发Agent]
    C <-->|多轮迭代| D[审核Agent]
    D --> E[测试Agent]
    E --> F[完成]
```

每个节点输出后设置**人工审核Gate**，只有通过审核才能进入下一阶段。

### 1.3 关键角色分配

| 角色 | 承担方 | 原因 |
|------|--------|------|
| 开发Agent | **Claude Code** | 最强的代码编辑与OS级自动化能力 |
| 审核Agent | **OpenAI Codex** | 专门的代码审核模型，与代码理解深度结合 |
| 工作流编排 | **OpenAI Agents SDK** | 生态中最清晰的handoff与guardrails机制 |
| 执行层（探索/规划/测试）| **Claude Agent SDK** | 深度OS集成、MCP生态、Extended Thinking |

---

## 2. SDK选型深度分析

### 2.1 两大SDK核心特性对比

#### OpenAI Agents SDK（2026年4月最新版）

**核心设计哲学**：显式控制与极简编排。整个框架仅约2000行代码，围绕五大原语构建：

| 原语 | 职责 |
|------|------|
| **Agent** | 带指令、工具和可选handoff目标的LLM实例 |
| **Tool** | Agent可调用的Python/TS函数 |
| **Handoff** | 将控制权及对话上下文从一个Agent转移至另一个 |
| **Guardrail** | 输入、输出和单次工具调用的异步验证层 |
| **Runner** | 驱动Agent的执行循环 |

**关键优势**：
- **Handoff机制**：被公认为2026年生态中"最干净的多Agent委托模型"。Agent A通过类型化工具调用（如`transfer_to_reviewer_agent`）直接将上下文打包传递给Agent B，接收方获得精炼的摘要而非原始消息堆叠。
- **三层Guardrails**：输入、输出、工具三层guardrails默认并行运行，任何一层失败立即中断执行——这天然适合"每阶段后人工审核"的需求。
- **Provider-Agnostic**：2026年4月更新后支持100+非OpenAI模型，但深度集成仍偏向OpenAI生态。
- **原生Sandbox**：支持Blaxel、Cloudflare、Daytona、E2B等7个sandbox提供商，Agent获得文件系统和shell执行能力。

**局限性**：
- 无原生OS级工具，需依赖外部sandbox或自定义tool
- Handoff为线性链，不支持复杂图状拓扑
- 状态持久化需自行实现

#### Claude Agent SDK（2026年4月最新版）

**核心设计哲学**："给Agent一台计算机"。由Claude Code SDK演进而来，强调深度OS集成与确定性控制。

**关键优势**：
- **原生OS工具集**：Read、Write、Edit（行级精度）、Glob、Grep、Bash——无需任何外部集成即可操作文件系统和执行命令。
- **Hooks系统**：PreToolUse/PostToolUse/Stop三级钩子，可在工具执行前后和Agent结束时进行拦截、审批、修改。
- **Agent Teams（实验性）**：支持teammates直接通信、共享任务列表和依赖追踪的持久协作。
- **最强MCP集成**：作为MCP协议的创造者，支持200+ MCP服务器的一行配置接入。
- **Extended Thinking**：原生链式思考推理，适合复杂规划任务。

**局限性**：
- 锁定Claude模型生态
- 多Agent编排相对手动（依赖subagent作为tool调用）
- Agent Teams仍为实验性功能

### 2.2 混合架构设计

**结论：两者可以且应当结合使用。**

2026年的生产实践表明，许多团队通过**MCP协议**将两者结合：OpenAI SDK承担协调层，Claude SDK承担工具密集型推理任务。

#### 分层分工

```mermaid
flowchart TB
    subgraph 编排层 [编排层 - OpenAI Agents SDK]
        O1[主控Agent<br/>Triage/Routing]
        O2[审核Agent<br/>Codex模型]
        O3[Guardrails<br/>人工暂停检查]
    end

    subgraph 执行层 [执行层 - Claude Agent SDK]
        C1[探索Agent]
        C2[规划Agent]
        C3[开发Agent<br/>Claude Code]
        C4[测试Agent]
    end

    subgraph 基础设施 [基础设施层]
        I1[MCP服务器群]
        I2[PostgreSQL]
        I3[Redis]
        I4[MinIO/S3]
    end

    O1 -- Handoff --> O2
    O1 -- Tool Call --> C1
    O1 -- Tool Call --> C2
    O1 -- Tool Call --> C3
    O2 -- Tool Call --> C4
    C1 --> I1
    C2 --> I1
    C3 --> I1
    C4 --> I1
    O1 --> I2
    O1 --> I3
```

#### 各层SDK选择理由

| 平台层级 | 选用SDK | 核心理由 |
|----------|---------|----------|
| **工作流编排** | OpenAI Agents SDK | Handoff是生态中最清晰的阶段间上下文传递机制；Guardrails天然支持"阶段完成后暂停等待人工审核"的需求；线性pipeline与RV-Insights的5阶段流程完美匹配 |
| **探索Agent** | Claude Agent SDK | 需要WebSearch、WebFetch、Bash爬取邮件列表、Glob/Grep搜索代码库——Claude SDK原生具备所有这些工具 |
| **规划Agent** | Claude Agent SDK | Extended Thinking链式思考能力对复杂技术方案设计至关重要；MCP可接入RISC-V文档服务器 |
| **开发Agent** | Claude Agent SDK | 用户明确要求Claude Code承担；Claude SDK的Edit工具支持行级精度代码修改，是最强的代码Agent |
| **审核Agent** | OpenAI Agents SDK + Codex | Codex是OpenAI专门的代码模型，与OpenAI SDK深度集成；审核结果可通过Guardrail触发迭代或暂停 |
| **测试Agent** | Claude Agent SDK | 需要Bash执行编译命令、文件系统操作、日志解析——Claude SDK的原生OS工具无可替代 |

#### 集成方式

1. **API调用集成**：OpenAI编排Agent将Claude Agent作为Tool调用。Claude Agent SDK启动独立session，完成后返回结构化结果。
2. **MCP协议集成**：Claude Agent暴露的MCP服务器可被OpenAI Agent通过MCP客户端调用，实现跨SDK工具共享。
3. **事件驱动集成**：两者通过Redis Streams或消息队列异步通信，OpenAI Agent发布任务事件，Claude Agent订阅执行并返回结果事件。

---

## 3. 系统整体架构

### 3.1 分层架构

```mermaid
flowchart TB
    subgraph 前端层 [前端层]
        F1[React + WebSocket<br/>实时工作流看板]
        F2[代码Diff查看器]
        F3[人工审核Gate界面]
    end

    subgraph API网关 [API网关]
        A1[REST API]
        A2[WebSocket<br/>实时事件]
        A3[Auth/NAuth]
    end

    subgraph 服务层 [微服务层]
        S1[Orchestration Service<br/>OpenAI Agents SDK]
        S2[Agent Execution Service<br/>Claude Agent SDK]
        S3[Review Gate Service]
        S4[Artifact Service]
        S5[Notification Service]
    end

    subgraph 数据层 [数据层]
        D1[(PostgreSQL)]
        D2[(Redis<br/>缓存+消息)]
        D3[MinIO/S3<br/>产物存储]
    end

    F1 --> A1
    F1 --> A2
    A1 --> S1
    A1 --> S2
    A1 --> S3
    A1 --> S4
    A1 --> S5
    S1 --> D1
    S1 --> D2
    S2 --> D1
    S2 --> D2
    S3 --> D1
    S4 --> D3
    S5 --> D2
```

### 3.2 Agent运行时架构

```mermaid
sequenceDiagram
    actor User as 用户
    participant UI as 前端
    participant OS as Orchestration Service<br/>(OpenAI SDK)
    participant ES as Agent Execution Service<br/>(Claude SDK)
    participant DB as PostgreSQL
    participant RS as Redis

    User->>UI: 提交初始输入
    UI->>OS: POST /contributions
    OS->>DB: 创建Contribution记录
    OS->>RS: 发布Stage.Started事件
    OS->>UI: WebSocket推送状态

    Note over OS,ES: === 探索阶段 ===
    OS->>ES: Tool Call: 探索Agent
    ES->>ES: WebSearch + GitHub API + Bash
    ES-->>OS: 候选贡献点列表
    OS->>OS: Guardrail: 等待人工审核
    OS->>UI: WebSocket: 审核请求
    User->>UI: 选择贡献点并确认
    UI->>OS: POST /review/approve

    Note over OS,ES: === 规划阶段 ===
    OS->>ES: Tool Call: 规划Agent
    ES->>ES: Extended Thinking
    ES-->>OS: 开发计划 + 测试计划
    OS->>OS: Guardrail: 等待人工审核
    OS->>UI: WebSocket: 审核请求
    User->>UI: 审核通过
    UI->>OS: POST /review/approve

    Note over OS,ES: === 开发-审核迭代 ===
    loop 最多N轮迭代
        OS->>ES: Tool Call: 开发Agent
        ES->>ES: 代码编辑 + Git操作
        ES-->>OS: 代码补丁
        OS->>OS: Handoff to 审核Agent
        OS->>ES: Tool Call: 审核Agent<br/>(Codex)
        ES-->>OS: Review意见
        alt 审核通过
            OS->>OS: 退出迭代
        else 需要修改
            OS->>ES: Tool Call: 开发Agent<br/>携带Review意见
        end
    end
    OS->>OS: Guardrail: 等待人工审核
    User->>UI: 审核通过

    Note over OS,ES: === 测试阶段 ===
    OS->>ES: Tool Call: 测试Agent
    ES->>ES: 环境搭建 + 编译 + 测试
    ES-->>OS: 测试报告
    OS->>OS: Guardrail: 等待人工审核
    User->>UI: 最终确认
    OS->>DB: 更新状态为完成
```

---

## 4. 核心设计原则

1. **人类在环（Human-in-the-Loop）**：每个Agent阶段结束后强制停顿，用户拥有最终决策权
2. **最小权限原则**：每个Agent仅拥有完成当前阶段所需的最小工具集和权限
3. **不可变性**：阶段产物（代码补丁、测试报告）一旦生成为不可变artifact，修改通过新增版本实现
4. **可观测性**：所有Agent操作、推理过程、工具调用记录完整日志，支持回放
5. **优雅降级**：Agent失败时提供清晰的人工接管入口，而非静默重试
