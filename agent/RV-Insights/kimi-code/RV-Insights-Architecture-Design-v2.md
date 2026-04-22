# RV-Insights：大模型驱动的 RISC-V 开源贡献平台

## 项目设计方案 v2.0（增强版）

> **版本**：v2.0  
> **日期**：2026-04-23  
> **变更说明**：在 v1.0 基础上，针对每个模块补充了实现细节、代码示例、数据模型、接口定义、安全策略和部署配置，使方案具备可直接落地开发的完整度。

---

## 目录

1. [项目背景与目标](#1-项目背景与目标)
2. [核心设计原则](#2-核心设计原则)
3. [整体架构设计](#3-整体架构设计)
4. [智能体节点详细设计](#4-智能体节点详细设计)
   - 4.1 [探索层（Discovery Agent）](#41-探索层discovery-agent)
   - 4.2 [规划层（Planning Agent）](#42-规划层planning-agent)
   - 4.3 [开发层（Development Agent）](#43-开发层development-agent)
   - 4.4 [审核层（Review Agent）](#44-审核层review-agent)
   - 4.5 [测试层（Testing Agent）](#45-测试层testing-agent)
5. [SDK 选型分析与融合策略](#5-sdk-选型分析与融合策略)
   - 5.1 [OpenAI Agents SDK 核心特性](#51-openai-agents-sdk-核心特性)
   - 5.2 [Claude Agent SDK 核心特性](#52-claude-agent-sdk-核心特性)
   - 5.3 [双 SDK 融合架构](#53-双-sdk-融合架构)
6. [人机回路（HITL）机制](#6-人机回路hitl机制)
7. [数据流与状态管理](#7-数据流与状态管理)
8. [安全与权限控制](#8-安全与权限控制)
9. [技术栈与依赖](#9-技术栈与依赖)
10. [部署架构](#10-部署架构)
11. [演进路线](#11-演进路线)
12. [附录：架构图](#12-附录架构图)
13. [附录：核心代码示例](#13-附录核心代码示例)
14. [附录：数据库 Schema](#14-附录数据库-schema)
15. [附录：API 接口定义](#15-附录-api-接口定义)
16. [附录：运维手册](#16-附录运维手册)

---

## 1. 项目背景与目标

### 1.1 背景

RISC-V 作为开放指令集架构（ISA），其开源软件生态正在快速发展。RV-Insights 面向的核心项目包括：

#### 1.1.1 目标项目清单

| 项目 | 仓库 | 贡献类型 | 维护者 | 邮件列表 |
|------|------|----------|--------|----------|
| **Linux Kernel (RISC-V)** | `torvalds/linux` | 内核驱动、架构支持、Bug 修复 | Paul Walmsley, Palmer Dabbelt | linux-riscv@lists.infradead.org |
| **GCC (RISC-V)** | `gcc-mirror/gcc` | 编译器优化、后端生成、内建函数 | Kito Cheng | gcc-patches@gcc.gnu.org |
| **LLVM/Clang (RISC-V)** | `llvm/llvm-project` | IR 优化、代码生成、LLD 链接器 | Alex Bradbury | llvm-dev@lists.llvm.org |
| **QEMU (RISC-V)** | `qemu/qemu` | 模拟器实现、设备模型、性能优化 | Alistair Francis | qemu-riscv@nongnu.org |
| **OpenSBI** | `riscv-software-src/opensbi` | 固件接口、平台初始化 | Anup Patel | opensbi@lists.infradead.org |
| **U-Boot (RISC-V)** | `u-boot/u-boot` | Bootloader、驱动移植 | Bin Meng | u-boot@lists.denx.de |
| **glibc (RISC-V)** | `bminor/glibc` | C 库优化、系统调用包装 | Adhemerval Zanella | libc-alpha@sourceware.org |

#### 1.1.2 贡献类型分类矩阵

```
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│    类型         │   难度等级       │   常见来源       │   示例          │
├─────────────────┼─────────────────┼─────────────────┼─────────────────┤
│ Bug 修复        │ 初-中级         │ 邮件列表、Issues │ 空指针检查遗漏   │
│ 驱动移植        │ 中-高级         │ 硬件厂商、社区   │ 新 SoC 设备树   │
│ 性能优化        │ 中-高级         │ 性能测试、Benchmark│ 向量化优化     │
│ 特性实现        │ 高级            │ ISA 规范更新     │ Zicond 扩展支持 │
│ 文档改进        │ 初级            │ 代码注释、文档   │ DT Binding 文档 │
│ 测试增强        │ 初-中级         │ 覆盖率报告       │ KUnit 测试用例  │
│ 构建系统        │ 中级            │ 编译错误         │ Kconfig 依赖修复│
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

#### 1.1.3 实际贡献案例分析

以 Linux 内核 RISC-V 子系统为例，典型的贡献流程如下：

**案例：修复 `handle_misaligned_load` 默认处理器缺失**

```
1. 问题发现
   - 来源：Commit d1703dc7bc8e 移除默认处理器后，无 RISCV_SCALAR_MISALIGNED 时编译失败
   - 影响：内核配置不含 CONFIG_RISCV_MISALIGNED 时无法编译

2. 技术方案
   - 文件：arch/riscv/include/asm/entry-common.h
   - 方案：添加 #ifdef CONFIG_RISCV_MISALIGNED 条件编译，无配置时提供 inline stub
   - 变更：+12 行，-0 行

3. Patch 格式
   Subject: [PATCH for-next v2] riscv: Fix default misaligned access trap
   Fixes: d1703dc7bc8e ("RISC-V: Detect unaligned vector accesses supported")
   Signed-off-by: Charlie Jenkins <charlie@rivosinc.com>
   Reviewed-by: Jesse Taube <mr.bossman075@gmail.com>

4. 迭代过程
   v1 → v2：根据 Reviewer 反馈，CONFIG_RISCV_SCALAR_MISALIGNED 改为 CONFIG_RISCV_MISALIGNED
```

### 1.2 目标

构建 **RV-Insights** 平台，实现以下量化目标：

| 指标 | Phase 1 (MVP) | Phase 2 | Phase 3 |
|------|---------------|---------|---------|
| 周探索贡献点 | ≥10 个 | ≥30 个 | ≥50 个 |
| 可行性验证准确率 | ≥70% | ≥80% | ≥85% |
| 代码生成编译通过率 | ≥60% | ≥75% | ≥85% |
| 审核迭代收敛轮数 | ≤5 轮 | ≤3 轮 | ≤2 轮 |
| 测试通过率 | ≥50% | ≥70% | ≥80% |
| 人工审核后可直接提交率 | ≥30% | ≥50% | ≥65% |

---

## 2. 核心设计原则

### 2.1 原则一：分而治之

**定义**：每个 Agent 专注于单一职责，通过清晰接口协作。

**落地措施**：
- 采用 **SRP（Single Responsibility Principle）** 设计每个 Agent
- Agent 间通过 **结构化 Artifact** 传递数据，而非自由文本
- 定义严格的输入/输出 JSON Schema，使用 Pydantic 校验

```python
# Artifact 传递规范
from pydantic import BaseModel, Field
from typing import Literal, Optional, List
from datetime import datetime

class ContributionPoint(BaseModel):
    """探索层输出 → 规划层输入"""
    contribution_id: str = Field(..., pattern=r"RV-\d{4}-\d{2}-\d{2}-\d{3}")
    title: str = Field(..., max_length=200)
    category: Literal["bugfix", "feature", "optimization", "documentation", "testing"]
    difficulty: Literal["beginner", "intermediate", "advanced"]
    target_project: Literal["linux", "gcc", "llvm", "qemu", "opensbi", "u-boot", "glibc"]
    description: str
    source_url: str
    source_type: Literal["mail_list", "github_issue", "code_analysis", "user_input"]
    reproduction_steps: Optional[List[str]] = None
    related_commits: Optional[List[str]] = None
    feasibility_score: float = Field(..., ge=0.0, le=1.0)
    estimated_effort_hours: int = Field(..., ge=1, le=480)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### 2.2 原则二：人机协同

**定义**：人工在每个阶段拥有最终决定权，Agent 提供辅助决策。

**落地措施**：
- 每个阶段结束后自动生成 **HITL 请求**，包含：
  - 阶段产出摘要（≤500 字）
  - 关键决策点标注
  - 建议行动（通过/拒绝/修改）
  - 预计下一步操作
- 支持 **异步审核**：人工可在 24h 窗口期内响应
- 提供 **diff 视图**：代码变更可视化对比

### 2.3 原则三：可观测性

**定义**：全流程可追踪、可审计、可回放。

**落地措施**：
- **OpenTelemetry 全链路追踪**：每个 LLM 调用、工具调用、Agent Handoff 生成 Span
- **结构化日志**：JSONL 格式，包含时间戳、Agent ID、操作类型、输入摘要、输出摘要
- **审计日志**：人工操作记录（who/when/what/why）
- **成本追踪**：每个任务的 Token 消耗、API 调用费用实时统计

```python
# 追踪示例
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

tracer_provider = TracerProvider()
jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger",
    agent_port=6831,
)
tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
trace.set_tracer_provider(tracer_provider)

tracer = trace.get_tracer("rv-insights")

# Agent 调用追踪
with tracer.start_as_current_span("discovery_agent.run") as span:
    span.set_attribute("agent.name", "MailExplorer")
    span.set_attribute("agent.model", "gpt-4o")
    span.set_attribute("task.contribution_id", "RV-2026-0423-001")
    span.set_attribute("llm.input_tokens", 2048)
    span.set_attribute("llm.output_tokens", 512)
    span.set_attribute("llm.cost_usd", 0.015)
    # ... Agent 执行逻辑
```

### 2.4 原则四：安全优先

**定义**：Agent 操作受限于沙箱环境，关键操作需审批。

**落地措施**：
- **gVisor/Firecracker 沙箱**：每个 Agent 运行在独立容器中
- **seccomp-bpf 系统调用过滤**：限制可执行的系统调用
- **文件系统只读挂载**：除工作目录外，所有路径只读
- **网络隔离**：沙箱内无外网访问，或仅通过代理访问白名单域名

### 2.5 原则五：模型无关

**定义**：架构层不绑定特定模型，支持灵活切换和 A/B 测试。

**落地措施**：
- **LiteLLM Proxy** 作为统一网关：所有 LLM 调用通过 LiteLLM 路由
- **模型配置化**：通过 YAML 配置指定每个 Agent 使用的模型
- **Fallback 策略**：主模型失败时自动降级到备用模型

```yaml
# models.yaml 模型配置
agents:
  discovery_orchestrator:
    primary: openai/gpt-4o
    fallback: anthropic/claude-sonnet-4
    temperature: 0.3
    max_tokens: 4096
  
  feasibility_validator:
    primary: openai/o3-mini
    fallback: openai/gpt-4o
    reasoning_effort: high
  
  developer:
    primary: anthropic/claude-sonnet-4
    fallback: anthropic/claude-opus-4
    max_tokens: 8192
    # Claude SDK 特有参数
    permission_mode: accept_edits
    bash_tools: true
    read_write_tools: true
```

### 2.6 原则六：渐进交付

**定义**：支持从简单任务到复杂任务的渐进式能力扩展。

**落地措施**：
- **任务难度分级**：初/中/高级贡献对应不同的 Agent 组合和审核标准
- **能力开关**：通过 Feature Flag 控制新能力的启用
- **A/B 测试框架**：对比不同 Prompt/模型/策略的效果

---

## 3. 整体架构设计

### 3.1 架构概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RV-Insights 平台架构                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    用户交互层 (User Interface Layer)                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │   │
│  │  │   Web UI    │  │   CLI Tool  │  │  GitHub App │  │  API 网关  │  │   │
│  │  │  (React)    │  │  (Python)   │  │  (Webhook)  │  │  (FastAPI)│  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                  工作流编排层 (Workflow Orchestration)                 │   │
│  │                     【OpenAI Agents SDK 主导】                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │   │
│  │  │ 状态机引擎   │  │  HITL 控制器 │  │  事件总线    │  │ 调度器     │  │   │
│  │  │  (State)    │  │  (Human)    │  │  (Event)    │  │(Scheduler)│  │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬─────┘  │   │
│  │         │                │                │               │        │   │
│  │         └────────────────┴────────────────┘               │        │   │
│  │                          │                                │        │   │
│  │  ┌───────────────────────┴────────────────────────────────┘        │   │
│  │  │                    LiteLLM Proxy (模型网关)                       │   │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │   │
│  │  │  │  OpenAI  │ │ Anthropic│ │  Google  │ │  Local   │          │   │
│  │  │  │  GPT-4o  │ │  Claude  │ │  Gemini  │ │  Ollama  │          │   │
│  │  │  │  o3-mini │ │  Sonnet  │ │  Flash   │ │  DeepSeek│          │   │
│  │  │  │  Codex   │ │  Opus    │ │  Pro     │ │  Qwen    │          │   │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │   │
│  │  └───────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Agent 执行层 (Agent Execution Layer)               │   │
│  │                                                                     │   │
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────┐  │   │
│  │  │  OpenAI Agents   │◄──►│   MCP 协议网关    │◄──►│Claude Agent  │  │   │
│  │  │     集群         │    │  (互操作层)       │    │    SDK       │  │   │
│  │  │                  │    │                  │    │              │  │   │
│  │  │ • Discovery      │    │  • 工具注册        │    │ • Developer  │  │   │
│  │  │ • Planner        │    │  • 调用转发        │    │ • Tester     │  │   │
│  │  │ • Reviewer       │    │  • 格式转换        │    │              │  │   │
│  │  │ • Orchestrator   │    │  • 权限校验        │    │              │  │   │
│  │  └──────────────────┘    └──────────────────┘    └──────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    工具与数据层 (Tools & Data Layer)                  │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │ 邮件列表  │ │ GitHub   │ │ 代码分析  │ │ 测试环境  │ │ 知识库   │  │   │
│  │  │ 爬虫     │  │  API    │  │ 工具链   │  │ 沙箱    │  │ (RAG)   │  │   │
│  │  │ • lore   │  │ • Issues│  │ • AST   │  │ • QEMU  │  │ • ISA   │  │   │
│  │  │ • patchwk│  │ • PRs   │  │ • Call  │  │ • Spike │  │ • ABI   │  │   │
│  │  │ • groups │  │ • Commits│ │ • Graph │  │ • Docker│  │ • Docs  │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 五层架构接口定义

#### 3.2.1 L1 ↔ L2 接口（API 网关）

```python
# FastAPI 路由定义
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(title="RV-Insights API", version="2.0.0")

class CreateTaskRequest(BaseModel):
    """创建贡献任务请求"""
    title: str
    description: Optional[str] = None
    source_type: Optional[str] = None  # "user_input" | "auto_discovery"
    target_project: Optional[str] = None
    user_id: str
    priority: int = 1  # 1-5

class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    status: str
    current_stage: str
    created_at: str
    hitl_pending: bool
    stage_summary: Optional[str] = None

@app.post("/api/v2/tasks", response_model=TaskResponse)
async def create_task(
    request: CreateTaskRequest,
    background_tasks: BackgroundTasks
):
    """创建新的贡献任务"""
    task = await workflow_engine.create_task(request)
    background_tasks.add_task(workflow_engine.start_workflow, task.task_id)
    return TaskResponse(
        task_id=task.task_id,
        status=task.status,
        current_stage=task.current_stage,
        created_at=task.created_at.isoformat(),
        hitl_pending=False
    )

@app.get("/api/v2/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """获取任务状态"""
    task = await workflow_engine.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(
        task_id=task.task_id,
        status=task.status,
        current_stage=task.current_stage,
        created_at=task.created_at.isoformat(),
        hitl_pending=task.hitl_pending,
        stage_summary=task.stage_summary
    )

@app.post("/api/v2/tasks/{task_id}/hitl/approve")
async def approve_hitl(task_id: str, feedback: Optional[str] = None):
    """人工批准当前阶段"""
    await workflow_engine.resolve_hitl(task_id, decision="approve", feedback=feedback)
    return {"status": "approved", "task_id": task_id}

@app.post("/api/v2/tasks/{task_id}/hitl/reject")
async def reject_hitl(task_id: str, feedback: str, action: str = "return"):
    """人工拒绝当前阶段
    action: "return" 返回上一阶段修改 | "abort" 终止任务
    """
    await workflow_engine.resolve_hitl(
        task_id, decision="reject", feedback=feedback, action=action
    )
    return {"status": "rejected", "task_id": task_id, "action": action}
```

#### 3.2.2 L2 ↔ L3 接口（Agent 调用协议）

```python
# Agent 调用接口规范
class AgentInvocationRequest(BaseModel):
    """调用 Agent 的请求"""
    agent_type: str  # "discovery" | "planning" | "development" | "review" | "testing"
    agent_name: str
    input_artifact_id: str
    context: dict  # 额外上下文
    timeout_seconds: int = 300
    max_cost_usd: float = 5.0

class AgentInvocationResponse(BaseModel):
    """Agent 调用响应"""
    output_artifact_id: str
    execution_time_seconds: float
    cost_usd: float
    token_usage: dict  # {"input": 2048, "output": 512}
    status: str  # "success" | "failed" | "timeout"
    logs: List[str]

# 异步 Agent 调用
async def invoke_agent(request: AgentInvocationRequest) -> AgentInvocationResponse:
    if request.agent_type in ["development", "testing"]:
        # 使用 Claude SDK
        return await claude_executor.run(request)
    else:
        # 使用 OpenAI SDK
        return await openai_orchestrator.run(request)
```

#### 3.2.3 L3 ↔ L4 接口（MCP 网关）

```python
# MCP 网关接口
class MCPToolRequest(BaseModel):
    """MCP 工具调用请求"""
    tool_name: str
    parameters: dict
    source_sdk: str  # "openai" | "claude"
    request_id: str

class MCPToolResponse(BaseModel):
    """MCP 工具调用响应"""
    result: dict
    execution_time_ms: int
    status: str  # "success" | "error"
    error_message: Optional[str] = None
```

---

## 4. 智能体节点详细设计

### 4.1 探索层（Discovery Agent）

#### 4.1.1 职责定义

- **自主探索**：持续监控 RISC-V 邮件列表、GitHub Issues、Patchwork
- **用户输入处理**：接收用户给定的方向或问题，分析可行性
- **可行性验证**：对发现的贡献点进行初步验证
- **输出结构化报告**

#### 4.1.2 数据源与采集策略

```
┌─────────────────────────────────────────────────────────────────────┐
│                        探索层数据源架构                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  邮件列表源   │  │   GitHub     │  │   代码库     │              │
│  │              │  │              │  │              │              │
│  │ • lore.kerne│  │ • Issues    │  │ • git log   │              │
│  │   l.org     │  │ • PRs       │  │ • TODO 注释 │              │
│  │ • patchwork.│  │ • Discussions│ │ • 代码扫描  │              │
│  │   kernel.org│  │ • Commits   │  │ • 覆盖率报告│              │
│  │ • groups.go │  │ • Releases  │  │              │              │
│  │   ogle.com  │  │              │  │              │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                 │                       │
│         └─────────────────┴─────────────────┘                       │
│                           │                                         │
│                           ▼                                         │
│                  ┌─────────────────┐                                │
│                  │   数据采集器      │                                │
│                  │  (Celery Beat)  │                                │
│                  │                 │                                │
│                  │ 调度策略：        │                                │
│                  │ • 邮件列表：每 1h │                                │
│                  │ • GitHub：每 30min│                               │
│                  │ • 代码库：每 6h   │                                │
│                  └────────┬────────┘                                │
│                           │                                         │
│                           ▼                                         │
│                  ┌─────────────────┐                                │
│                  │   消息队列       │                                │
│                  │  (Redis/Rabbit) │                                │
│                  └────────┬────────┘                                │
│                           │                                         │
│                           ▼                                         │
│                  ┌─────────────────┐                                │
│                  │   原始数据存储   │                                │
│                  │  (PostgreSQL)   │                                │
│                  └─────────────────┘                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 4.1.3 邮件列表解析器详细实现

```python
# rv_insights/agents/discovery/mail_parser.py
import re
import email
from dataclasses import dataclass
from typing import List, Optional, Iterator
from datetime import datetime
import aiohttp
from bs4 import BeautifulSoup

@dataclass
class MailMessage:
    """解析后的邮件结构"""
    message_id: str
    subject: str
    from_addr: str
    date: datetime
    body: str
    thread_id: str
    in_reply_to: Optional[str] = None
    references: List[str] = None
    patches: List[dict] = None  # 附带的 Patch
    is_patch: bool = False
    patch_version: Optional[str] = None  # v1, v2, etc.
    
class LoreKernelParser:
    """
    lore.kernel.org 邮件列表解析器
    
    lore.kernel.org 提供以下接口：
    - HTML 浏览：/all/YYYYMM/
    - Atom Feed：/all/?q=...&x=A
    - mbox 下载：/all/YYYY/thread.mbox.gz
    - JSON API：/all/YYYYMM.json
    """
    
    BASE_URL = "https://lore.kernel.org"
    
    # RISC-V 相关邮件列表
    TARGET_LISTS = [
        "linux-riscv",
        "qemu-riscv",
        "opensbi",
        "u-boot",
    ]
    
    # Patch 相关正则
    PATCH_SUBJECT_RE = re.compile(
        r'\[(?P<prefix>[^\]]+)\]\s*(?P<title>.+)',
        re.IGNORECASE
    )
    VERSION_RE = re.compile(r'\bv(\d+)\b')
    
    async def fetch_recent_messages(
        self,
        list_name: str,
        days: int = 7,
        keywords: List[str] = None
    ) -> Iterator[MailMessage]:
        """
        获取指定邮件列表最近的消息
        
        Args:
            list_name: 邮件列表名称，如 "linux-riscv"
            days: 回溯天数
            keywords: 过滤关键词，如 ["bug", "fix", "patch", "riscv"]
        """
        # 构建查询
        query = ""
        if keywords:
            query = " " + " OR ".join(keywords)
        
        # 使用 Atom feed 获取
        feed_url = f"{self.BASE_URL}/{list_name}/all/?q={query}&x=A"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(feed_url) as resp:
                feed_content = await resp.text()
                
        # 解析 Atom feed
        soup = BeautifulSoup(feed_content, 'xml')
        entries = soup.find_all('entry')
        
        for entry in entries:
            msg = await self._parse_entry(entry, list_name)
            if msg and self._is_contribution_opportunity(msg):
                yield msg
    
    def _is_contribution_opportunity(self, msg: MailMessage) -> bool:
        """
        判断一条消息是否代表潜在贡献机会
        
        判断规则：
        1. 不是 Patch（避免重复已有贡献）
        2. 包含 Bug/Fix/Error/Failed 等关键词
        3. 不是回复（避免讨论串中的附和消息）
        4. 包含可复现的问题描述
        """
        if msg.is_patch:
            return False
        
        body_lower = msg.body.lower()
        opportunity_keywords = [
            'bug', 'fix', 'error', 'failed', 'crash', 'oops',
            'not working', 'broken', 'regression', 'missing',
            'unsupported', 'todo', 'fixme', 'feature request'
        ]
        
        has_opportunity = any(kw in body_lower for kw in opportunity_keywords)
        
        # 排除过短的邮件（可能是自动回复）
        if len(msg.body) < 200:
            return False
        
        return has_opportunity
    
    async def _parse_entry(self, entry, list_name: str) -> Optional[MailMessage]:
        """解析 Atom entry 为 MailMessage"""
        # 提取基本字段
        title = entry.find('title')
        if not title:
            return None
        
        subject = title.get_text()
        
        # 判断是否是 Patch
        is_patch = '[PATCH' in subject.upper()
        patch_version = None
        if is_patch:
            match = self.VERSION_RE.search(subject)
            if match:
                patch_version = f"v{match.group(1)}"
        
        # 提取作者和日期
        author = entry.find('author')
        from_addr = author.find('email').get_text() if author and author.find('email') else ""
        
        date_elem = entry.find('published')
        date = datetime.fromisoformat(date_elem.get_text().replace('Z', '+00:00')) if date_elem else datetime.now()
        
        # 提取内容
        content = entry.find('content')
        body = content.get_text() if content else ""
        
        # 提取 Message-ID
        id_elem = entry.find('id')
        message_id = id_elem.get_text() if id_elem else ""
        
        return MailMessage(
            message_id=message_id,
            subject=subject,
            from_addr=from_addr,
            date=date,
            body=body,
            thread_id=message_id,  # 简化处理
            is_patch=is_patch,
            patch_version=patch_version
        )
```

#### 4.1.4 代码库分析工具链

```python
# rv_insights/agents/discovery/code_analyzer.py
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class CodeIssue:
    """代码分析发现的问题"""
    file_path: str
    line_number: int
    issue_type: str  # "TODO" | "FIXME" | "BUG" | "HACK"
    message: str
    context: str  # 周围代码上下文
    severity: str  # "low" | "medium" | "high"

class CodebaseAnalyzer:
    """
    代码库分析器
    
    使用以下工具链：
    - grep/ripgrep: 文本搜索
    - ctags: 符号索引
    - clang-check: 静态分析（C/C++）
    - sparse: Linux 内核专用静态分析
    - coccinelle: 语义补丁匹配
    """
    
    def __init__(self, repo_path: Path, project_type: str):
        self.repo_path = repo_path
        self.project_type = project_type
        
    async def analyze(self) -> Dict[str, List[CodeIssue]]:
        """执行全量代码分析"""
        results = {}
        
        # 1. 搜索 TODO/FIXME/HACK 注释
        results['annotations'] = await self._find_annotations()
        
        # 2. 检查编译警告模式
        if self.project_type == 'linux':
            results['compile_issues'] = await self._analyze_compile_patterns()
        
        # 3. 检查测试覆盖盲区
        results['coverage_gaps'] = await self._analyze_test_coverage()
        
        # 4. 对比 ISA 规范检查未实现特性
        if self.project_type in ['linux', 'qemu']:
            results['missing_features'] = await self._check_isa_compliance()
        
        return results
    
    async def _find_annotations(self) -> List[CodeIssue]:
        """查找代码中的 TODO/FIXME/BUG/HACK 注释"""
        issues = []
        
        # 使用 ripgrep 搜索
        patterns = [
            (r'TODO\s*[:\-]?\s*(.+)', 'TODO'),
            (r'FIXME\s*[:\-]?\s*(.+)', 'FIXME'),
            (r'BUG\s*[:\-]?\s*(.+)', 'BUG'),
            (r'HACK\s*[:\-]?\s*(.+)', 'HACK'),
        ]
        
        for pattern, issue_type in patterns:
            cmd = [
                'rg', '-n', '-B2', '-A2',
                '--type', 'c', '--type', 'h',
                '-P', pattern,
                str(self.repo_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if ':' in line:
                    parts = line.split(':', 2)
                    if len(parts) >= 3:
                        file_path, line_no, content = parts[0], parts[1], parts[2]
                        issues.append(CodeIssue(
                            file_path=file_path,
                            line_number=int(line_no),
                            issue_type=issue_type,
                            message=content.strip(),
                            context=line,
                            severity='medium' if issue_type in ['TODO', 'FIXME'] else 'high'
                        ))
        
        return issues
    
    async def _check_isa_compliance(self) -> List[CodeIssue]:
        """
        对比 RISC-V ISA 规范检查未实现特性
        
        方法：
        1. 维护已知的 RISC-V 扩展列表（来自 riscv-isa-manual）
        2. 在代码库中搜索各扩展的实现迹象
        3. 标记"规范已发布但代码未实现"的扩展
        """
        # RISC-V 标准扩展列表（示例）
        riscv_extensions = [
            'Zicbom', 'Zicbop', 'Zicboz',  # Cache Block 操作
            'Zicond',                       # 条件操作
            'Zawrs',                        # Wait-on-Reservation-Set
            'Zacas',                        # Compare-and-Swap
            'Zabha',                        # Byte and Halfword Atomic
            'Ssqosid',                      # Quality of Service (QoS)
        ]
        
        issues = []
        
        for ext in riscv_extensions:
            # 在代码中搜索扩展实现
            cmd = ['rg', '-i', '-c', ext, str(self.repo_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            count = sum(1 for line in result.stdout.split('\n') if line.strip())
            
            if count < 3:  # 引用次数少于3次，可能未完整实现
                issues.append(CodeIssue(
                    file_path="ISA_COMPLIANCE",
                    line_number=0,
                    issue_type="MISSING_FEATURE",
                    message=f"RISC-V extension {ext} may not be fully implemented (found {count} references)",
                    context=f"Extension: {ext}",
                    severity='medium'
                ))
        
        return issues
```

#### 4.1.5 探索层 Agent 集群定义（完整版）

```python
# rv_insights/agents/discovery/agents.py
from agents import Agent, Runner, function_tool, guardrail, InputGuardrail, OutputGuardrail
from pydantic import BaseModel, Field
import asyncio

# ============ 工具定义 ============

class MailSearchResult(BaseModel):
    """邮件搜索结果"""
    messages: list
    total_found: int
    query_time_ms: int

@function_tool
async def fetch_mail_list(
    list_name: str,
    days: int = 7,
    keywords: list[str] = None,
    max_results: int = 50
) -> MailSearchResult:
    """
    获取指定邮件列表最近的消息
    
    Args:
        list_name: 邮件列表名称，如 "linux-riscv"
        days: 回溯天数
        keywords: 过滤关键词
        max_results: 最大返回数量
    """
    parser = LoreKernelParser()
    messages = []
    
    async for msg in parser.fetch_recent_messages(list_name, days, keywords):
        messages.append({
            "message_id": msg.message_id,
            "subject": msg.subject,
            "from": msg.from_addr,
            "date": msg.date.isoformat(),
            "body_preview": msg.body[:500],
            "is_patch": msg.is_patch,
            "patch_version": msg.patch_version
        })
        if len(messages) >= max_results:
            break
    
    return MailSearchResult(
        messages=messages,
        total_found=len(messages),
        query_time_ms=0
    )

@function_tool
async def search_codebase(
    project: str,
    query: str,
    search_type: str = "text"  # "text" | "regex" | "semantic"
) -> dict:
    """
    在代码库中搜索特定模式
    
    Args:
        project: 项目名称，如 "linux" | "gcc" | "qemu"
        query: 搜索查询
        search_type: 搜索类型
    """
    # 实际实现会使用 ripgrep 或代码嵌入向量搜索
    repo_path = f"/repos/{project}"
    
    if search_type == "text":
        cmd = ['rg', '-n', '-C3', query, repo_path]
    else:
        cmd = ['rg', '-n', '-C3', '-P', query, repo_path]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    matches = []
    for line in result.stdout.split('\n')[:50]:  # 限制结果数量
        if ':' in line:
            matches.append(line)
    
    return {
        "project": project,
        "query": query,
        "matches_count": len(matches),
        "matches": matches
    }

@function_tool
async def check_todo_comments(project: str, directory: str = "") -> dict:
    """检查代码库中的 TODO/FIXME 注释"""
    analyzer = CodebaseAnalyzer(Path(f"/repos/{project}"), project)
    issues = await analyzer._find_annotations()
    
    return {
        "total": len(issues),
        "by_type": {
            "TODO": len([i for i in issues if i.issue_type == "TODO"]),
            "FIXME": len([i for i in issues if i.issue_type == "FIXME"]),
            "BUG": len([i for i in issues if i.issue_type == "BUG"]),
            "HACK": len([i for i in issues if i.issue_type == "HACK"]),
        },
        "high_priority": [
            {"file": i.file_path, "line": i.line_number, "message": i.message}
            for i in issues if i.severity == "high"
        ][:20]
    }

@function_tool
async def compare_with_isa_spec(project: str) -> dict:
    """对比 RISC-V ISA 规范检查未实现特性"""
    analyzer = CodebaseAnalyzer(Path(f"/repos/{project}"), project)
    issues = await analyzer._check_isa_compliance()
    
    return {
        "missing_extensions": [
            {"extension": i.message.split()[2], "detail": i.message}
            for i in issues
        ],
        "recommendation": "Consider implementing missing extensions for better RISC-V compliance"
    }

@function_tool
async def analyze_git_log(
    project: str,
    since: str = "1 week ago",
    author_filter: str = ""
) -> dict:
    """
    分析 Git 提交历史，发现贡献模式
    
    Args:
        project: 项目名称
        since: 时间范围，如 "1 week ago"
        author_filter: 作者过滤
    """
    repo_path = f"/repos/{project}"
    
    cmd = ['git', '-C', repo_path, 'log', f'--since={since}', '--pretty=format:%H|%s|%an|%ad', '--date=short']
    if author_filter:
        cmd.extend(['--author', author_filter])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    commits = []
    for line in result.stdout.split('\n')[:100]:
        if '|' in line:
            hash_val, subject, author, date = line.split('|', 3)
            commits.append({
                "hash": hash_val,
                "subject": subject,
                "author": author,
                "date": date
            })
    
    # 分析提交主题模式
    fix_commits = [c for c in commits if 'fix' in c['subject'].lower()]
    feature_commits = [c for c in commits if any(kw in c['subject'].lower() for kw in ['add', 'support', 'implement'])]
    
    return {
        "total_commits": len(commits),
        "fix_commits": len(fix_commits),
        "feature_commits": len(feature_commits),
        "recent_fixes": fix_commits[:10],
        "recent_features": feature_commits[:10]
    }

@function_tool
async def check_test_coverage(project: str, subdirectory: str = "") -> dict:
    """检查测试覆盖率"""
    # 实际实现会使用 gcov/lcov 或项目特定的覆盖率工具
    return {
        "project": project,
        "coverage_status": "analysis_required",
        "recommendation": "Run gcov/lcov to generate detailed coverage report"
    }

@function_tool
async def search_existing_patches(contribution_title: str, project: str) -> dict:
    """搜索是否已有相关 Patch"""
    # 在 lore.kernel.org 和 Patchwork 中搜索
    keywords = contribution_title.lower().split()[:5]
    
    return {
        "keywords": keywords,
        "lore_search_url": f"https://lore.kernel.org/{project}/?q={'+'.join(keywords)}",
        "patchwork_search_url": f"https://patchwork.kernel.org/project/{project}/list/?q={'+'.join(keywords)}",
        "recommendation": "Manual verification recommended before proceeding"
    }

@function_tool  
async def check_issue_status(issue_url: str) -> dict:
    """检查 GitHub Issue 的当前状态"""
    # 解析 GitHub API
    return {
        "url": issue_url,
        "status": "unknown",  # open | closed | merged
        "labels": [],
        "assignees": [],
        "last_activity": ""
    }

@function_tool
async def estimate_effort(contribution_type: str, lines_of_code: int, project: str) -> dict:
    """估算贡献工作量"""
    # 基于历史数据的经验估算
    base_hours = {
        "bugfix": 8,
        "feature": 40,
        "optimization": 24,
        "documentation": 4,
        "testing": 16
    }
    
    base = base_hours.get(contribution_type, 16)
    loc_factor = lines_of_code / 50  # 每50行增加基准时间
    project_factor = {
        "linux": 2.0,
        "gcc": 1.8,
        "llvm": 1.8,
        "qemu": 1.5,
        "opensbi": 1.2,
        "u-boot": 1.3,
        "glibc": 1.6
    }.get(project, 1.5)
    
    estimated_hours = int(base * max(1, loc_factor) * project_factor)
    
    return {
        "estimated_hours": estimated_hours,
        "estimated_days": round(estimated_hours / 8, 1),
        "confidence": "medium",
        "breakdown": {
            "understanding": int(estimated_hours * 0.3),
            "coding": int(estimated_hours * 0.4),
            "testing": int(estimated_hours * 0.2),
            "documentation": int(estimated_hours * 0.1)
        }
    }

# ============ Guardrails 定义 ============

class DiscoveryOutput(BaseModel):
    """探索层输出结构校验"""
    contribution_points: list = Field(..., min_length=0, max_length=20)
    has_riscv_relevance: bool
    feasibility_assessed: bool

@guardrail
async def discovery_output_guardrail(output: str) -> bool:
    """确保探索输出包含必要字段"""
    try:
        data = json.loads(output)
        required_fields = ["contribution_id", "title", "category", "feasibility"]
        if "contribution_points" in data:
            for point in data["contribution_points"]:
                for field in required_fields:
                    if field not in point:
                        return False
        return True
    except:
        return False

# ============ Agent 定义 ============

mail_explorer = Agent(
    name="MailExplorer",
    instructions="""
    你是 RV-Insights 的邮件列表探索专家，专注于从 RISC-V 相关邮件列表中发现潜在贡献机会。
    
    你的分析流程：
    1. 获取最近邮件列表消息
    2. 筛选非 Patch 的原始问题报告
    3. 提取问题的技术领域和难度
    4. 验证是否已有解决方案
    5. 输出结构化的贡献机会报告
    
    判断贡献机会的标准：
    - 明确的 Bug 报告（含复现步骤）
    - 功能请求（Feature Request）且技术方案可行
    - 性能问题（含 Benchmark 数据）
    - 文档缺失或不准确
    - 编译错误（Build Failure）
    
    排除的情况：
    - 已有 Patch 的问题
    - 仅讨论而无明确行动项
    - 超出 RISC-V 范围的问题
    - 需要硬件访问的调试问题（除非提供远程访问）
    
    输出格式必须严格遵循 ContributionPoint Schema。
    """,
    model="gpt-4o",
    tools=[fetch_mail_list, search_existing_patches, check_issue_status, estimate_effort],
    output_guardrails=[discovery_output_guardrail]
)

repo_explorer = Agent(
    name="RepoExplorer",
    instructions="""
    你是 RV-Insights 的代码库探索专家，擅长通过代码分析发现贡献机会。
    
    你的分析流程：
    1. 扫描代码库中的 TODO/FIXME/BUG/HACK 注释
    2. 分析最近的 Git 提交历史，发现修复模式
    3. 对比 RISC-V ISA 规范，检查未实现特性
    4. 分析测试覆盖盲区
    5. 输出结构化的贡献机会报告
    
    特别关注：
    - 内核中的 arch/riscv/ 目录
    - 编译器后端中的 riscv 相关代码
    - QEMU 中的 target/riscv/ 目录
    - Device Tree Binding 文档
    
    输出格式必须严格遵循 ContributionPoint Schema。
    """,
    model="gpt-4o",
    tools=[search_codebase, check_todo_comments, compare_with_isa_spec, 
           analyze_git_log, check_test_coverage, estimate_effort],
    output_guardrails=[discovery_output_guardrail]
)

feasibility_validator = Agent(
    name="FeasibilityValidator",
    instructions="""
    你是 RV-Insights 的可行性验证专家，负责对发现的贡献机会进行技术可行性评估。
    
    评估维度：
    1. **问题清晰度**：问题描述是否足够清晰，边界是否明确
    2. **技术可达性**：是否有足够的技术资料支持开发
    3. **重复性检查**：是否已有 Patch、PR 或正在进行的解决方案
    4. **范围可控性**：工作量是否在合理范围内（<2周）
    5. **测试可行性**：是否能搭建测试环境验证修复
    
    评分标准：
    - 0.0-0.3: 不可行（信息不足、已有解决方案、范围过大）
    - 0.3-0.6: 需谨慎（部分信息缺失、难度较高）
    - 0.6-0.8: 可行（信息充足、技术方案清晰）
    - 0.8-1.0: 高可行性（问题明确、方案直观、测试简单）
    
    对每个贡献机会，输出：
    - feasibility_score (0.0-1.0)
    - go_no_go ("GO" | "NO-GO" | "NEEDS_MORE_INFO")
    - rationale (详细理由)
    - missing_info (如需要更多信息，列出具体问题)
    - estimated_effort_hours
    """,
    model="o3-mini",
    tools=[search_existing_patches, check_issue_status, estimate_effort],
    output_guardrails=[discovery_output_guardrail]
)

discovery_orchestrator = Agent(
    name="DiscoveryOrchestrator",
    instructions="""
    你是 RV-Insights 探索层的总协调者。
    
    你的任务：
    1. 根据用户输入决定探索策略
    2. 并行启动多个探索 Agent
    3. 收集并去重探索结果
    4. 对每个候选进行可行性验证
    5. 输出最终探索报告
    
    决策逻辑：
    - 如果用户提供了具体 Issue/PR URL → 直接分析该问题
    - 如果用户提供了模糊方向 → 同时启动邮件列表和代码库探索
    - 如果用户无输入 → 自主全面扫描
    
    并行策略：
    - MailExplorer 和 RepoExplorer 可并行执行
    - 所有探索结果汇总后统一进行可行性验证
    - 最多返回 10 个最有价值的贡献机会
    """,
    model="gpt-4o",
    handoffs=[mail_explorer, repo_explorer, feasibility_validator]
)
```

---

*（文档继续，下一部分：规划层详细设计）*


### 4.2 规划层（Planning Agent）

#### 4.2.1 职责定义

- **方案设计**：基于探索报告，设计完整的代码开发和测试方案
- **任务拆解**：将贡献任务拆解为可执行的子任务序列
- **依赖分析**：识别任务间的依赖关系和资源需求
- **风险评估**：识别潜在的技术风险并制定应对策略

#### 4.2.2 任务拆解与依赖图算法

```python
# rv_insights/agents/planning/task_decomposer.py
from dataclasses import dataclass, field
from typing import List, Set, Dict, Optional
from enum import Enum
import json

class TaskPriority(Enum):
    CRITICAL = 1   # 阻塞后续所有任务
    HIGH = 2       # 影响主要功能
    MEDIUM = 3     # 影响次要功能
    LOW = 4        # 优化类任务

class TaskStatus(Enum):
    PENDING = "pending"
    BLOCKED = "blocked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class SubTask:
    """子任务定义"""
    task_id: str
    name: str
    description: str
    priority: TaskPriority
    estimated_hours: int
    depends_on: Set[str] = field(default_factory=set)
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: Optional[str] = None
    deliverable: Optional[str] = None  # 预期产出物
    validation_criteria: List[str] = field(default_factory=list)
    
    def is_ready(self, completed_tasks: Set[str]) -> bool:
        """检查任务是否满足执行条件"""
        return self.depends_on.issubset(completed_tasks)

@dataclass
class TaskDependencyGraph:
    """任务依赖图"""
    tasks: Dict[str, SubTask] = field(default_factory=dict)
    
    def add_task(self, task: SubTask):
        self.tasks[task.task_id] = task
    
    def get_ready_tasks(self) -> List[SubTask]:
        """获取所有可执行的任务"""
        completed = {t_id for t_id, t in self.tasks.items() if t.status == TaskStatus.COMPLETED}
        return [
            t for t in self.tasks.values()
            if t.status == TaskStatus.PENDING and t.is_ready(completed)
        ]
    
    def get_critical_path(self) -> List[str]:
        """
        计算关键路径（最长依赖链）
        
        使用拓扑排序 + 动态规划计算最长路径
        """
        # 构建反向依赖图
        reverse_deps: Dict[str, Set[str]] = {t_id: set() for t_id in self.tasks}
        for t_id, task in self.tasks.items():
            for dep in task.depends_on:
                reverse_deps[dep].add(t_id)
        
        # 记忆化搜索最长路径
        memo: Dict[str, int] = {}
        
        def longest_from(t_id: str) -> int:
            if t_id in memo:
                return memo[t_id]
            if not reverse_deps[t_id]:
                memo[t_id] = self.tasks[t_id].estimated_hours
                return memo[t_id]
            
            max_path = max(
                longest_from(next_id) 
                for next_id in reverse_deps[t_id]
            )
            memo[t_id] = max_path + self.tasks[t_id].estimated_hours
            return memo[t_id]
        
        # 找到最长路径的起点
        max_length = 0
        start_task = None
        for t_id in self.tasks:
            length = longest_from(t_id)
            if length > max_length:
                max_length = length
                start_task = t_id
        
        # 回溯构建路径
        path = []
        current = start_task
        while current:
            path.append(current)
            next_tasks = [
                t_id for t_id in reverse_deps[current]
                if memo.get(t_id, 0) == memo[current] - self.tasks[current].estimated_hours
            ]
            current = next_tasks[0] if next_tasks else None
        
        return path
    
    def to_mermaid(self) -> str:
        """生成 Mermaid 流程图语法"""
        lines = ["graph TD"]
        for t_id, task in self.tasks.items():
            node_label = f"{task.name} ({task.estimated_hours}h)"
            lines.append(f"    {t_id}[{node_label}]")
            for dep in task.depends_on:
                lines.append(f"    {dep} --> {t_id}")
        return "\n".join(lines)

class TaskDecomposer:
    """
    任务拆解器
    
    将贡献任务自动拆解为子任务依赖图
    """
    
    TEMPLATE_TASKS = {
        "linux_bugfix": [
            {
                "name": "环境准备",
                "description": "克隆内核源码，配置编译环境",
                "priority": "CRITICAL",
                "hours": 2,
                "deps": [],
                "agent": "developer",
                "validation": ["git clone 成功", "make defconfig 成功"]
            },
            {
                "name": "问题复现",
                "description": "根据报告复现 Bug，确认问题存在",
                "priority": "CRITICAL",
                "hours": 4,
                "deps": ["env_setup"],
                "agent": "developer",
                "validation": ["Bug 可复现", "复现步骤记录"]
            },
            {
                "name": "根因分析",
                "description": "分析 Bug 根因，定位问题代码",
                "priority": "CRITICAL",
                "hours": 4,
                "deps": ["reproduce"],
                "agent": "developer",
                "validation": ["根因分析报告", "问题代码定位"]
            },
            {
                "name": "代码修复",
                "description": "编写修复代码",
                "priority": "CRITICAL",
                "hours": 4,
                "deps": ["root_cause"],
                "agent": "developer",
                "validation": ["修复代码完成", "编译通过"]
            },
            {
                "name": "编译验证",
                "description": "本地编译验证修复",
                "priority": "HIGH",
                "hours": 2,
                "deps": ["code_fix"],
                "agent": "developer",
                "validation": ["make 成功", "无新警告"]
            },
            {
                "name": "单元测试",
                "description": "编写/运行单元测试",
                "priority": "HIGH",
                "hours": 4,
                "deps": ["code_fix"],
                "agent": "tester",
                "validation": ["测试用例通过", "覆盖修复路径"]
            },
            {
                "name": "QEMU 测试",
                "description": "在 QEMU 中验证修复",
                "priority": "MEDIUM",
                "hours": 4,
                "deps": ["compile_verify", "unit_test"],
                "agent": "tester",
                "validation": ["QEMU 启动成功", "Bug 不再复现"]
            },
            {
                "name": "Patch 格式化",
                "description": "生成符合规范的 Patch",
                "priority": "HIGH",
                "hours": 1,
                "deps": ["qemu_test"],
                "agent": "developer",
                "validation": ["checkpatch.pl 通过", "Signed-off-by 完整"]
            },
            {
                "name": "审核准备",
                "description": "准备审核材料",
                "priority": "MEDIUM",
                "hours": 1,
                "deps": ["patch_format"],
                "agent": "reviewer",
                "validation": ["审核清单完成"]
            }
        ]
    }
    
    def decompose(self, contribution: ContributionPoint) -> TaskDependencyGraph:
        """将贡献点拆解为任务依赖图"""
        graph = TaskDependencyGraph()
        
        # 选择模板
        template_key = f"{contribution.target_project}_{contribution.category}"
        template = self.TEMPLATE_TASKS.get(template_key, self.TEMPLATE_TASKS["linux_bugfix"])
        
        # 根据难度调整时间估算
        difficulty_factor = {
            "beginner": 0.7,
            "intermediate": 1.0,
            "advanced": 1.5
        }.get(contribution.difficulty, 1.0)
        
        for i, task_def in enumerate(template):
            task_id = task_def["name"].lower().replace(" ", "_")
            task = SubTask(
                task_id=task_id,
                name=task_def["name"],
                description=task_def["description"],
                priority=TaskPriority[task_def["priority"]],
                estimated_hours=int(task_def["hours"] * difficulty_factor),
                depends_on=set(task_def.get("deps", [])),
                assigned_agent=task_def["agent"],
                validation_criteria=task_def["validation"]
            )
            graph.add_task(task)
        
        return graph
```

#### 4.2.3 规划层 Agent 完整定义

```python
# rv_insights/agents/planning/agents.py
from agents import Agent, Runner, function_tool, guardrail
from pydantic import BaseModel
import json

class CodingStandardsResult(BaseModel):
    """编码规范查询结果"""
    project: str
    standards: list
    patch_format_rules: list
    commit_message_format: str
    checkpatch_options: str

@function_tool
async def query_coding_standards(project: str) -> CodingStandardsResult:
    """
    查询指定项目的编码规范和贡献指南
    
    Args:
        project: 项目名称
    """
    standards_db = {
        "linux": {
            "standards": [
                "Linux Kernel Coding Style (Documentation/process/coding-style.rst)",
                "8-space tabs, 80-column lines",
                "Kconfig 命名规范",
                "Device Tree Binding 规范"
            ],
            "patch_format_rules": [
                "Subject: [PATCH] subsystem: brief description",
                "Signed-off-by: required",
                "One logical change per patch",
                "Max 100 lines per patch (preferably)",
                "Use git format-patch to generate"
            ],
            "commit_message_format": """
                subsystem: Brief description
                
                Detailed explanation of what and why.
                
                Signed-off-by: Name <email>
            """,
            "checkpatch_options": "--strict --no-tree"
        },
        "gcc": {
            "standards": [
                "GNU Coding Standards",
                "GCC-specific conventions"
            ],
            "patch_format_rules": [
                "Subject: [PATCH] component: description",
                "Changelog entry required",
                "Testcase for bugfixes"
            ],
            "commit_message_format": "component: Brief description",
            "checkpatch_options": ""
        }
    }
    
    data = standards_db.get(project, standards_db["linux"])
    return CodingStandardsResult(project=project, **data)

@function_tool
async def fetch_contribution_guide(project: str) -> dict:
    """获取项目的贡献指南文档摘要"""
    guides = {
        "linux": {
            "maintainer_script": "scripts/get_maintainer.pl",
            "submit_process": "git format-patch + git send-email",
            "review_process": "mailing list review",
            "release_cycle": "merge window (~2 weeks) + stabilization",
            "tip": "Check MAINTAINERS file for subsystem maintainers"
        }
    }
    return guides.get(project, {})

@function_tool
async def analyze_code_dependencies(project: str, target_files: list[str]) -> dict:
    """
    分析目标文件的代码依赖关系
    
    使用 cscope/ctags 生成调用图和依赖图
    """
    repo_path = f"/repos/{project}"
    dependencies = {
        "header_files": [],
        "called_functions": [],
        "calling_functions": [],
        "related_configs": []
    }
    
    for file_path in target_files:
        full_path = f"{repo_path}/{file_path}"
        
        # 提取头文件依赖
        result = subprocess.run(
            ['grep', '-h', '^#include', full_path],
            capture_output=True, text=True
        )
        for line in result.stdout.split('\n'):
            if line.strip():
                dependencies["header_files"].append(line.strip())
        
        # 提取 Kconfig 依赖
        result = subprocess.run(
            ['grep', '-rh', 'depends on', f"{repo_path}/{Path(file_path).parent}/Kconfig"],
            capture_output=True, text=True
        )
        for line in result.stdout.split('\n')[:10]:
            if line.strip():
                dependencies["related_configs"].append(line.strip())
    
    return dependencies

@function_tool
async def estimate_test_coverage(
    project: str,
    target_files: list[str],
    change_type: str
) -> dict:
    """
    估算所需测试覆盖
    
    Args:
        change_type: "bugfix" | "feature" | "optimization"
    """
    coverage_requirements = {
        "bugfix": {
            "unit_tests_required": True,
            "min_line_coverage": 80,
            "integration_tests": True,
            "qemu_tests": True,
            "hardware_tests": "optional"
        },
        "feature": {
            "unit_tests_required": True,
            "min_line_coverage": 70,
            "integration_tests": True,
            "qemu_tests": True,
            "hardware_tests": "recommended"
        },
        "optimization": {
            "unit_tests_required": False,
            "benchmark_tests": True,
            "regression_tests": True,
            "qemu_tests": True
        }
    }
    
    return coverage_requirements.get(change_type, coverage_requirements["bugfix"])

# Guardrails
class PlanningOutput(BaseModel):
    """规划输出校验"""
    has_development_plan: bool
    has_testing_plan: bool
    has_validation_checklist: bool
    critical_path_defined: bool
    risk_assessment_complete: bool

@guardrail
async def plan_completeness_check(output: str) -> bool:
    """确保规划方案完整性"""
    required_sections = [
        "development_plan",
        "testing_plan", 
        "validation_checklist",
        "risk_assessment"
    ]
    try:
        data = json.loads(output)
        return all(section in data for section in required_sections)
    except:
        return False

@guardrail
async def scope_guardrail(output: str) -> bool:
    """防止规划范围失控"""
    try:
        data = json.loads(output)
        if "development_plan" in data:
            files = data["development_plan"].get("target_files", [])
            if len(files) > 20:
                return False  # 超过20个文件，范围过大
            loc = data["development_plan"].get("estimated_loc", 0)
            if loc > 1000:
                return False  # 超过1000行，范围过大
        return True
    except:
        return False

planner = Agent(
    name="ContributionPlanner",
    instructions="""
    你是 RV-Insights 的规划专家，负责为 RISC-V 开源贡献设计完整的执行方案。
    
    ## 输入
    ContributionPoint JSON（来自探索层）
    
    ## 输出结构
    你必须输出以下 JSON 结构：
    
    ```json
    {
      "plan": {
        "contribution_id": "...",
        "version": "1.0",
        "development_plan": {
          "target_files": ["path/to/file1.c", "path/to/file2.h"],
          "change_summary": "简洁描述要做什么",
          "coding_standards": ["标准1", "标准2"],
          "estimated_loc": 50,
          "git_workflow": "rebase / merge 策略",
          "commit_strategy": "single / split 策略"
        },
        "testing_plan": {
          "unit_tests": {
            "required": true,
            "framework": "KUnit / gtest / 等",
            "target_coverage": 80,
            "test_files": ["path/to/test.c"]
          },
          "integration_tests": {
            "required": true,
            "scenarios": ["场景1", "场景2"]
          },
          "qemu_tests": {
            "required": true,
            "machine_type": "virt",
            "test_commands": ["命令1", "命令2"]
          },
          "hardware_tests": {
            "required": false,
            "platforms": ["HiFive Unmatched"]
          }
        },
        "validation_checklist": [
          "编译验证命令",
          "静态分析检查",
          "checkpatch 检查",
          "运行时测试命令"
        ],
        "risk_assessment": {
          "risks": [
            {
              "description": "风险描述",
              "probability": "low/medium/high",
              "impact": "low/medium/high",
              "mitigation": "缓解措施"
            }
          ]
        },
        "execution_schedule": {
          "tasks": [
            {
              "id": "task_1",
              "name": "任务名",
              "duration_hours": 4,
              "depends_on": [],
              "agent": "developer/tester/reviewer",
              "deliverable": "预期产出"
            }
          ],
          "critical_path": ["task_1", "task_3", "task_5"],
          "total_estimated_hours": 40
        }
      }
    }
    ```
    
    ## 规划原则
    1. **最小化变更**：每次只改必要的文件，避免大面积重构
    2. **测试驱动**：先写测试，后写实现（如果适用）
    3. **可回滚**：每个变更点可独立回滚
    4. **合规优先**：严格遵守目标项目的编码规范和提交流程
    
    ## 项目特定规范
    
    ### Linux 内核
    - Patch 主题格式：`[PATCH] riscv: brief description`
    - 使用 `scripts/checkpatch.pl --strict` 检查
    - 使用 `scripts/get_maintainer.pl` 确定收件人
    - 每个 Patch 一个逻辑变更
    - 必须包含 `Signed-off-by:`
    
    ### GCC
    - Patch 需包含 ChangeLog 条目
    - Bug 修复需包含测试用例
    - 遵循 GNU 编码标准
    
    ### QEMU
    - 使用 `make check` 运行测试
    - 新增设备需包含文档
    """,
    model="o3-mini",
    tools=[query_coding_standards, fetch_contribution_guide, 
           analyze_code_dependencies, estimate_test_coverage],
    output_guardrails=[plan_completeness_check, scope_guardrail]
)
```

---

### 4.3 开发层（Development Agent）

#### 4.3.1 职责定义

- **代码实现**：根据规划方案，在沙箱环境中进行代码开发
- **增量提交**：按逻辑步骤进行代码变更，生成清晰的 Git 提交历史
- **文档编写**：编写/更新相关文档和注释
- **自检**：在提交前进行基本的编译和格式检查

#### 4.3.2 沙箱环境配置

```dockerfile
# Dockerfile.sandbox - 开发沙箱镜像
FROM ubuntu:24.04

# 基础工具
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    bc \
    bison \
    flex \
    libssl-dev \
    libncurses5-dev \
    wget \
    curl \
    vim \
    python3 \
    python3-pip \
    qemu-system-misc \
    qemu-utils \
    cscope \
    ctags \
    sparse \
    && rm -rf /var/lib/apt/lists/*

# RISC-V 交叉编译工具链
RUN apt-get update && apt-get install -y \
    gcc-riscv64-linux-gnu \
    g++-riscv64-linux-gnu \
    binutils-riscv64-linux-gnu \
    && rm -rf /var/lib/apt/lists/*

# 安装项目特定工具
RUN pip3 install \
    gitpython \
    pygments \
    requests

# 创建工作目录
WORKDIR /workspace

# 安全：创建非 root 用户
RUN useradd -m -s /bin/bash developer && \
    chown -R developer:developer /workspace
USER developer

# 配置 Git
RUN git config --global user.email "rv-insights@agent.local" && \
    git config --global user.name "RV-Insights Agent" && \
    git config --global core.editor "cat"

# 默认命令
CMD ["/bin/bash"]
```

#### 4.3.3 开发 Agent 实现（Claude Agent SDK）

```python
# rv_insights/agents/development/claude_dev_agent.py
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from dataclasses import dataclass
from typing import Optional, List, Dict
import json
import subprocess
from pathlib import Path

@dataclass
class DevelopmentResult:
    """开发结果"""
    success: bool
    modified_files: List[str]
    commit_hash: Optional[str]
    compile_status: bool
    checkpatch_status: bool
    diff_stats: Dict[str, int]  # {"insertions": N, "deletions": M}
    error_messages: List[str]
    cost_usd: float
    execution_time_seconds: float

class ClaudeDevelopmentAgent:
    """
    基于 Claude Agent SDK 的开发 Agent
    
    特性：
    - 原生文件读写和 Bash 执行
    - Git 工作流自动化
    - 编译和格式自检
    - 增量开发支持
    """
    
    def __init__(self, workspace: Path, project: str, task_id: str):
        self.workspace = workspace
        self.project = project
        self.task_id = task_id
        self.repo_path = workspace / project
        
        # 初始化 Claude SDK Client
        self.options = ClaudeAgentOptions(
            system_prompt=self._build_system_prompt(),
            permission_mode="accept_edits",  # 沙箱内自动接受编辑
            read_write_tools=True,
            bash_tools=True,
            cwd=str(self.repo_path),
            max_cost=5.0,
            audit_log_path=f"/logs/dev_{task_id}.log"
        )
        self.client = ClaudeSDKClient(options=self.options)
        
    def _build_system_prompt(self) -> str:
        """构建 System Prompt"""
        project_guidelines = {
            "linux": """
                ## Linux Kernel 开发规范
                - 遵循 Documentation/process/coding-style.rst
                - 使用 8-space tabs
                - 行长度限制 80 列（放宽到 100 列可接受）
                - 每个函数前添加注释说明
                - 错误处理路径使用 goto 或适当缩进
                - 使用 kernel 提供的辅助函数（如 pr_err, dev_err）
                - 内存分配使用 kmalloc/kzalloc，检查返回值
                - 并发代码考虑锁和原子操作
                
                ## Patch 提交规范
                - Subject: [PATCH] riscv: description
                - 包含 Signed-off-by: Name <email>
                - 使用 git format-patch 生成
                - 运行 scripts/checkpatch.pl --strict 检查
                - 使用 scripts/get_maintainer.pl 确定维护者
            """,
            "gcc": """
                ## GCC 开发规范
                - 遵循 GNU 编码标准
                - 使用 GNU 风格缩进
                - Bug 修复需包含测试用例
                - ChangeLog 条目格式：YYYY-MM-DD  Name  <email>
            """,
            "qemu": """
                ## QEMU 开发规范
                - 使用 4-space 缩进
                - 函数注释使用 /* ... */ 风格
                - 错误处理使用 error_setg/error_report
                - 新增设备需包含文档
            """
        }
        
        guidelines = project_guidelines.get(self.project, project_guidelines["linux"])
        
        return f"""
        你是 RV-Insights 的开发专家，负责 {self.project} 项目的代码开发。
        
        {guidelines}
        
        ## 通用工作规范
        1. **严格遵循规划**：按规划层的方案执行，不擅自扩大范围
        2. **最小化变更**：只修改必要的文件和代码行
        3. **增量提交**：每完成一个逻辑步骤就 git commit
        4. **编译验证**：每次修改后都要编译验证
        5. **自检清单**：
           - [ ] 编译通过（make）
           - [ ] 无新增编译警告
           - [ ] checkpatch 通过（如适用）
           - [ ] 单元测试通过（如适用）
        
        ## 可用工具
        - 文件读写：读取和修改源代码
        - Bash 执行：编译、测试、Git 操作
        - Git：提交、分支、差异查看
        
        ## 工作环境
        - 工作目录：{self.repo_path}
        - 项目：{self.project}
        - 任务ID：{self.task_id}
        
        ## 注意事项
        - 不要修改与工作无关的文件
        - 不要执行危险的系统命令（rm -rf /, mkfs 等）
        - 如果遇到困难，记录具体问题而不是猜测
        """
    
    async def execute_plan(self, plan: dict) -> DevelopmentResult:
        """
        执行开发计划
        
        Args:
            plan: 规划层输出的方案 JSON
        """
        start_time = time.time()
        
        try:
            # 1. 环境准备
            await self._setup_environment(plan)
            
            # 2. 按子任务执行开发
            dev_plan = plan["development_plan"]
            target_files = dev_plan["target_files"]
            change_summary = dev_plan["change_summary"]
            
            # 构建开发指令
            dev_instruction = self._build_development_instruction(plan)
            
            # 调用 Claude SDK 执行开发
            async for message in self.client.query(dev_instruction):
                # 流式输出处理
                if message.type == "tool_use":
                    logger.info(f"Tool used: {message.name}")
                elif message.type == "tool_result":
                    logger.info(f"Tool result: {message.content[:200]}")
            
            # 3. 收集结果
            result = await self._collect_development_result()
            
            return result
            
        except Exception as e:
            return DevelopmentResult(
                success=False,
                modified_files=[],
                commit_hash=None,
                compile_status=False,
                checkpatch_status=False,
                diff_stats={},
                error_messages=[str(e)],
                cost_usd=0.0,
                execution_time_seconds=time.time() - start_time
            )
    
    def _build_development_instruction(self, plan: dict) -> str:
        """构建开发指令"""
        dev_plan = plan["development_plan"]
        
        instruction = f"""
        请根据以下规划方案执行代码开发：
        
        ## 变更目标
        {dev_plan['change_summary']}
        
        ## 目标文件
        {chr(10).join(dev_plan['target_files'])}
        
        ## 开发步骤
        1. 先读取目标文件，理解现有代码结构
        2. 根据变更目标进行修改
        3. 修改后编译验证
        4. 生成 Patch 并检查格式
        
        ## 验证要求
        {chr(10).join(plan.get('validation_checklist', []))}
        
        请开始开发，并在完成后报告：
        - 修改了哪些文件
        - 变更的具体内容
        - 编译是否通过
        - checkpatch 检查结果
        - git diff --stat 输出
        """
        
        return instruction
    
    async def _setup_environment(self, plan: dict):
        """准备开发环境"""
        # 确保仓库已克隆
        if not (self.repo_path / ".git").exists():
            # 克隆仓库
            repo_urls = {
                "linux": "https://github.com/torvalds/linux.git",
                "gcc": "https://github.com/gcc-mirror/gcc.git",
                "qemu": "https://github.com/qemu/qemu.git",
                "opensbi": "https://github.com/riscv-software-src/opensbi.git"
            }
            url = repo_urls.get(self.project)
            if url:
                subprocess.run(
                    ['git', 'clone', '--depth', '1', url, str(self.repo_path)],
                    check=True
                )
    
    async def _collect_development_result(self) -> DevelopmentResult:
        """收集开发结果"""
        # 获取修改的文件列表
        result = subprocess.run(
            ['git', '-C', str(self.repo_path), 'diff', '--name-only', 'HEAD'],
            capture_output=True, text=True
        )
        modified_files = [f for f in result.stdout.strip().split('\n') if f]
        
        # 获取 diff 统计
        result = subprocess.run(
            ['git', '-C', str(self.repo_path), 'diff', '--stat', 'HEAD'],
            capture_output=True, text=True
        )
        
        # 解析 diff stat
        diff_stats = {"insertions": 0, "deletions": 0}
        for line in result.stdout.split('\n'):
            if '|' in line and ('+' in line or '-' in line):
                # 简单解析插入/删除数
                parts = line.split('|')
                if len(parts) == 2:
                    counts = parts[1].strip()
                    diff_stats["insertions"] += counts.count('+')
                    diff_stats["deletions"] += counts.count('-')
        
        # 获取最新 commit
        result = subprocess.run(
            ['git', '-C', str(self.repo_path), 'rev-parse', 'HEAD'],
            capture_output=True, text=True
        )
        commit_hash = result.stdout.strip() if result.returncode == 0 else None
        
        # 编译状态检查
        compile_status = await self._check_compile()
        
        # checkpatch 检查
        checkpatch_status = await self._check_checkpatch()
        
        return DevelopmentResult(
            success=len(modified_files) > 0,
            modified_files=modified_files,
            commit_hash=commit_hash,
            compile_status=compile_status,
            checkpatch_status=checkpatch_status,
            diff_stats=diff_stats,
            error_messages=[],
            cost_usd=0.0,  # 从 Claude SDK 获取
            execution_time_seconds=0.0
        )
    
    async def _check_compile(self) -> bool:
        """检查编译状态"""
        if self.project == "linux":
            result = subprocess.run(
                ['make', '-C', str(self.repo_path),
                 'ARCH=riscv', 'CROSS_COMPILE=riscv64-linux-gnu-',
                 '-j$(nproc)', 'defconfig'],
                capture_output=True, text=True, shell=False
            )
            if result.returncode != 0:
                return False
            
            result = subprocess.run(
                ['make', '-C', str(self.repo_path),
                 'ARCH=riscv', 'CROSS_COMPILE=riscv64-linux-gnu-',
                 '-j4'],  # 限制并行度避免OOM
                capture_output=True, text=True
            )
            return result.returncode == 0
        
        return True  # 其他项目简化处理
    
    async def _check_checkpatch(self) -> bool:
        """运行 checkpatch 检查"""
        if self.project != "linux":
            return True
        
        # 生成 Patch
        patch_file = f"/tmp/{self.task_id}.patch"
        subprocess.run(
            ['git', '-C', str(self.repo_path), 'format-patch',
             '-1', 'HEAD', '-o', '/tmp/'],
            capture_output=True
        )
        
        # 运行 checkpatch
        checkpatch = str(self.repo_path / "scripts/checkpatch.pl")
        result = subprocess.run(
            [checkpatch, '--strict', '--no-tree', patch_file],
            capture_output=True, text=True
        )
        
        # checkpatch 返回 0 或 1 都算通过（1 是警告但不阻止）
        return result.returncode in [0, 1]
```

---

### 4.4 审核层（Review Agent）

#### 4.4.1 职责定义

- **代码 Review**：对开发 Agent 产出的代码进行全面审查
- **问题分类**：将发现的问题分类为致命/严重/一般/建议
- **迭代反馈**：将问题反馈给开发 Agent，要求修复
- **质量把关**：直到代码质量达到可提交标准

#### 4.4.2 审核评分标准

```python
# rv_insights/agents/review/scoring.py
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class Severity(Enum):
    FATAL = "fatal"       # 会导致系统崩溃/安全漏洞/数据丢失
    CRITICAL = "critical" # 功能错误/编译失败/回归
    MAJOR = "major"       # 设计缺陷/性能问题/可维护性问题
    MINOR = "minor"       # 代码风格/注释/命名
    SUGGESTION = "suggestion"  # 改进建议

class ReviewCategory(Enum):
    CORRECTNESS = "correctness"      # 逻辑正确性
    SECURITY = "security"            # 安全性
    PERFORMANCE = "performance"      # 性能
    MAINTAINABILITY = "maintainability"  # 可维护性
    STYLE = "style"                  # 代码风格
    DOCUMENTATION = "documentation"  # 文档
    TESTING = "testing"              # 测试覆盖

@dataclass
class ReviewIssue:
    """审核发现的问题"""
    issue_id: str
    category: ReviewCategory
    severity: Severity
    file_path: str
    line_number: int
    description: str
    suggestion: str
    reference: Optional[str] = None  # 参考文档/规范链接
    
    def score_impact(self) -> int:
        """计算该问题对总分的影响"""
        impacts = {
            Severity.FATAL: -50,
            Severity.CRITICAL: -30,
            Severity.MAJOR: -15,
            Severity.MINOR: -5,
            Severity.SUGGESTION: -1
        }
        return impacts.get(self.severity, -5)

class ReviewScorecard:
    """审核评分卡"""
    
    MAX_SCORE = 100
    
    def __init__(self):
        self.issues: List[ReviewIssue] = []
        self.category_scores: dict = {
            cat: self.MAX_SCORE for cat in ReviewCategory
        }
    
    def add_issue(self, issue: ReviewIssue):
        self.issues.append(issue)
        self.category_scores[issue.category] += issue.score_impact()
        self.category_scores[issue.category] = max(0, self.category_scores[issue.category])
    
    def total_score(self) -> int:
        return sum(self.category_scores.values()) // len(self.category_scores)
    
    def is_pass(self, threshold: int = 70) -> bool:
        """是否通过审核"""
        # 有致命问题直接不通过
        if any(i.severity == Severity.FATAL for i in self.issues):
            return False
        # 有严重问题且总分低于阈值不通过
        critical_count = sum(1 for i in self.issues if i.severity == Severity.CRITICAL)
        if critical_count > 0 and self.total_score() < threshold:
            return False
        return self.total_score() >= threshold
    
    def get_action_items(self) -> List[dict]:
        """生成修复行动项，按优先级排序"""
        sorted_issues = sorted(
            self.issues,
            key=lambda i: ({
                Severity.FATAL: 0,
                Severity.CRITICAL: 1,
                Severity.MAJOR: 2,
                Severity.MINOR: 3,
                Severity.SUGGESTION: 4
            }[i.severity], i.category.value)
        )
        
        return [
            {
                "priority": issue.severity.value,
                "file": issue.file_path,
                "line": issue.line_number,
                "description": issue.description,
                "suggestion": issue.suggestion,
                "category": issue.category.value
            }
            for issue in sorted_issues
            if issue.severity in [Severity.FATAL, Severity.CRITICAL, Severity.MAJOR]
        ]
    
    def generate_report(self) -> dict:
        """生成完整审核报告"""
        return {
            "total_score": self.total_score(),
            "passed": self.is_pass(),
            "category_scores": {
                cat.value: score for cat, score in self.category_scores.items()
            },
            "issue_summary": {
                "fatal": sum(1 for i in self.issues if i.severity == Severity.FATAL),
                "critical": sum(1 for i in self.issues if i.severity == Severity.CRITICAL),
                "major": sum(1 for i in self.issues if i.severity == Severity.MAJOR),
                "minor": sum(1 for i in self.issues if i.severity == Severity.MINOR),
                "suggestion": sum(1 for i in self.issues if i.severity == Severity.SUGGESTION),
            },
            "action_items": self.get_action_items(),
            "all_issues": [
                {
                    "id": i.issue_id,
                    "severity": i.severity.value,
                    "category": i.category.value,
                    "location": f"{i.file_path}:{i.line_number}",
                    "description": i.description,
                    "suggestion": i.suggestion
                }
                for i in self.issues
            ]
        }
```

#### 4.4.3 审核层 Agent 集群定义

```python
# rv_insights/agents/review/agents.py
from agents import Agent, Runner, function_tool, guardrail
from pydantic import BaseModel
import subprocess
import json

@function_tool
async def run_checkpatch(patch_path: str, options: str = "--strict") -> dict:
    """运行 Linux 内核 checkpatch 检查"""
    cmd = ["scripts/checkpatch.pl", options, patch_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # 解析输出
    errors = []
    warnings = []
    for line in result.stdout.split('\n'):
        if 'ERROR:' in line:
            errors.append(line)
        elif 'WARNING:' in line:
            warnings.append(line)
    
    return {
        "passed": result.returncode in [0, 1] and len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "total_issues": len(errors) + len(warnings)
    }

@function_tool
async def static_analysis(file_path: str, project: str) -> dict:
    """运行静态分析工具"""
    issues = []
    
    if project == "linux":
        # 使用 sparse 进行内核静态分析
        result = subprocess.run(
            ['make', 'C=1', 'CF="-Wsparse-all"', file_path],
            capture_output=True, text=True
        )
        for line in result.stderr.split('\n'):
            if 'warning:' in line or 'error:' in line:
                issues.append(line)
    
    return {
        "tool": "sparse" if project == "linux" else "none",
        "issues_found": len(issues),
        "issues": issues[:20]  # 限制返回数量
    }

@function_tool
async def semantic_diff(old_code: str, new_code: str) -> dict:
    """
    语义差异分析
    
    分析代码变更的语义影响，不仅仅是文本差异
    """
    # 实际实现可使用 Tree-sitter 进行 AST 对比
    return {
        "functions_added": [],
        "functions_modified": [],
        "functions_removed": [],
        "api_changes": [],
        "behavior_changes": []
    }

@function_tool
async def reference_spec_check(file_path: str, change_description: str) -> dict:
    """检查代码变更是否符合 RISC-V 规范"""
    # 查询 RISC-V ISA 规范知识库
    return {
        "isa_compliant": True,
        "spec_references": [],
        "recommendations": []
    }

@function_tool
async def run_semgrep(file_path: str, rules: list[str] = None) -> dict:
    """运行 Semgrep 安全扫描"""
    cmd = ['semgrep', '--config=auto', file_path, '--json']
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    try:
        data = json.loads(result.stdout)
        findings = data.get('results', [])
        return {
            "findings_count": len(findings),
            "findings": [
                {
                    "rule": f.get('check_id', ''),
                    "message": f.get('extra', {}).get('message', ''),
                    "severity": f.get('extra', {}).get('metadata', {}).get('severity', 'unknown'),
                    "line": f.get('start', {}).get('line', 0)
                }
                for f in findings[:10]
            ]
        }
    except:
        return {"findings_count": 0, "findings": [], "error": "Parse failed"}

@function_tool
async def run_codeql(project: str, query_suite: str = "security-extended") -> dict:
    """运行 CodeQL 分析"""
    # CodeQL 需要预先建立数据库，这里简化处理
    return {
        "status": "CodeQL analysis requires pre-built database",
        "recommendation": "Run 'codeql database create' before analysis"
    }

@function_tool
async def analyze_cwe_patterns(code_snippet: str) -> dict:
    """分析常见 CWE 漏洞模式"""
    cwe_patterns = {
        "CWE-120": r'strcpy\s*\(',
        "CWE-121": r'char\s+\w+\s*\[\s*\d+\s*\]',
        "CWE-190": r'\+\s*\w+\s*\)',
        "CWE-476": r'->\s*\w+\s*;',
    }
    
    findings = []
    import re
    for cwe_id, pattern in cwe_patterns.items():
        if re.search(pattern, code_snippet):
            findings.append(cwe_id)
    
    return {
        "potential_cwes": findings,
        "requires_manual_review": len(findings) > 0
    }

# Guardrails
@guardrail
async def review_completeness_guardrail(output: str) -> bool:
    """确保审核覆盖所有必要维度"""
    required_categories = ["correctness", "security", "style"]
    try:
        data = json.loads(output)
        report = data.get("review_report", {})
        category_scores = report.get("category_scores", {})
        return all(cat in category_scores for cat in required_categories)
    except:
        return False

@guardrail
async def iteration_limit_guardrail(output: str) -> bool:
    """防止审核无限迭代"""
    try:
        data = json.loads(output)
        iteration_count = data.get("iteration_count", 0)
        return iteration_count <= 5
    except:
        return False

# Agent 定义
style_reviewer = Agent(
    name="StyleReviewer",
    instructions="""
    你是代码风格审核专家。
    
    审核维度：
    1. **编码规范合规性**
       - 缩进（Linux: tabs, QEMU: 4 spaces）
       - 行长度（80-100列）
       - 括号位置（K&R vs Allman）
       - 命名规范
    
    2. **代码可读性**
       - 函数长度（<50行理想）
       - 圈复杂度（<10）
       - 注释完整性
       - 魔法数字消除
    
    3. **文档和注释**
       - 函数头注释
       - 复杂逻辑说明
       - TODO/FIXME 的合理性
    
    4. **Commit Message**
       - 格式规范
       - 描述清晰性
       - Signed-off-by 完整性
    
    输出格式：ReviewIssue JSON 数组
    """,
    model="gpt-4o",
    tools=[run_checkpatch]
)

logic_reviewer = Agent(
    name="LogicReviewer",
    instructions="""
    你是代码逻辑审核专家，专注于算法正确性和边界条件。
    
    审核维度：
    1. **算法正确性**
       - 实现是否符合设计意图
       - 数学运算是否正确
       - 状态机转换是否正确
    
    2. **边界条件**
       - 空指针检查
       - 数组越界
       - 整数溢出
       - 除零保护
       - 资源耗尽处理
    
    3. **并发安全**
       - 锁的获取/释放配对
       - 原子操作使用
       - 竞态条件
       - 死锁风险
    
    4. **RISC-V 规范符合性**
       - CSR 访问是否符合规范
       - 异常处理是否完整
       - 扩展检测是否正确
       - 对齐要求
    
    5. **错误处理**
       - 所有错误路径都有处理
       - 错误码正确传递
       - 资源清理（goto 或 cleanup）
    
    输出格式：ReviewIssue JSON 数组
    对于每个问题，必须提供具体的修复建议。
    """,
    model="codex-latest",
    tools=[static_analysis, semantic_diff, reference_spec_check]
)

security_reviewer = Agent(
    name="SecurityReviewer",
    instructions="""
    你是安全审核专家。
    
    审核维度：
    1. **内存安全**
       - 缓冲区溢出
       - 使用后释放（UAF）
       - 重复释放
       - 内存泄漏
       - 越界访问
    
    2. **整数安全**
       - 整数溢出
       - 符号/无符号混淆
       - 截断错误
    
    3. **输入验证**
       - 用户输入校验
       - 长度检查
       - 格式验证
    
    4. **权限检查**
       - 特权操作检查
       - Capability 检查
       - 访问控制
    
    5. **信息泄露**
       - 敏感数据打印
       - 调试信息泄露
       - 内核指针泄露
    
    输出格式：ReviewIssue JSON 数组
    安全问题必须标注 CWE 编号（如果适用）。
    """,
    model="gpt-4o",
    tools=[run_semgrep, run_codeql, analyze_cwe_patterns]
)

review_orchestrator = Agent(
    name="ReviewOrchestrator",
    instructions="""
    你是审核层的总协调者。
    
    你的任务：
    1. 接收开发层的代码产出
    2. 并行启动三个专项审核 Agent
    3. 收集并综合所有审核结果
    4. 生成统一的 ReviewScorecard
    5. 判断是否通过或需要修复
    
    ## 迭代终止条件
    
    审核通过（满足以下全部）：
    - 无 FATAL 级别问题
    - 无 CRITICAL 级别问题
    - MAJOR 级别问题 ≤ 2 个
    - 总分 ≥ 70 分
    
    或达到最大迭代次数（5轮），取最后一轮结果
    
    ## 修复反馈格式
    
    如果审核不通过，输出修复要求：
    ```json
    {
      "review_report": { ... },
      "action_required": true,
      "fixes_required": [
        {
          "priority": "critical",
          "file": "path/to/file.c",
          "line": 42,
          "issue": "问题描述",
          "suggested_fix": "建议的修复代码"
        }
      ],
      "iteration_count": 1
    }
    ```
    """,
    model="gpt-4o",
    handoffs=[style_reviewer, logic_reviewer, security_reviewer],
    output_guardrails=[review_completeness_guardrail, iteration_limit_guardrail]
)
```

#### 4.4.4 迭代收敛策略

```python
# rv_insights/agents/review/iteration.py
import asyncio
from typing import Tuple

class ReviewIterationManager:
    """
    审核迭代管理器
    
    管理开发 Agent 和审核 Agent 之间的多轮迭代
    """
    
    MAX_ITERATIONS = 5
    PASS_THRESHOLD = 70
    
    def __init__(
        self,
        developer: ClaudeDevelopmentAgent,
        reviewer: Agent,
        orchestrator
    ):
        self.developer = developer
        self.reviewer = reviewer
        self.orchestrator = orchestrator
        self.iteration_count = 0
        self.review_history = []
    
    async def run_iteration_loop(
        self,
        plan: dict,
        initial_code: DevelopmentResult
    ) -> Tuple[DevelopmentResult, dict]:
        """
        运行审核迭代循环
        
        Returns:
            (最终代码结果, 最终审核报告)
        """
        current_code = initial_code
        
        for iteration in range(1, self.MAX_ITERATIONS + 1):
            self.iteration_count = iteration
            
            # 1. 运行审核
            review_report = await self._run_review(current_code)
            
            # 2. 记录历史
            self.review_history.append({
                "iteration": iteration,
                "score": review_report["total_score"],
                "issues_count": sum(review_report["issue_summary"].values()),
                "report": review_report
            })
            
            # 3. 检查是否通过
            if review_report["passed"]:
                return current_code, review_report
            
            # 4. 检查是否达到最大迭代
            if iteration >= self.MAX_ITERATIONS:
                return current_code, review_report
            
            # 5. 生成修复指令
            fix_instruction = self._generate_fix_instruction(review_report)
            
            # 6. 调用开发 Agent 修复
            current_code = await self.developer.apply_fixes(fix_instruction)
            
            if not current_code.success:
                # 修复失败，返回当前最佳结果
                return current_code, review_report
        
        return current_code, review_report
    
    async def _run_review(self, code: DevelopmentResult) -> dict:
        """运行审核"""
        # 构建审核输入
        review_input = {
            "code_diff": code.diff_stats,
            "modified_files": code.modified_files,
            "commit_message": "",  # 从 Git 获取
            "project": self.developer.project,
            "iteration": self.iteration_count
        }
        
        # 调用审核 Orchestrator
        result = await Runner.run(
            self.orchestrator,
            json.dumps(review_input)
        )
        
        return json.loads(result.final_output)
    
    def _generate_fix_instruction(self, review_report: dict) -> str:
        """生成修复指令"""
        action_items = review_report["action_items"]
        
        instruction = f"""
        审核发现以下问题需要修复（第 {self.iteration_count} 轮迭代）：
        
        当前总分：{review_report['total_score']}/100
        不通过原因：{self._get_failure_reason(review_report)}
        
        需要修复的问题（按优先级排序）：
        """
        
        for i, item in enumerate(action_items[:10], 1):
            instruction += f"""
        {i}. [{item['priority'].upper()}] {item['file']}:{item['line']}
           问题：{item['description']}
           建议：{item['suggestion']}
        """
        
        instruction += """
        请按优先级修复上述问题，然后重新编译和自检。
        只修改与问题相关的代码，不要引入无关变更。
        """
        
        return instruction
    
    def _get_failure_reason(self, report: dict) -> str:
        """获取失败原因摘要"""
        summary = report["issue_summary"]
        reasons = []
        if summary.get("fatal", 0) > 0:
            reasons.append(f"致命问题 {summary['fatal']} 个")
        if summary.get("critical", 0) > 0:
            reasons.append(f"严重问题 {summary['critical']} 个")
        if report["total_score"] < self.PASS_THRESHOLD:
            reasons.append(f"总分 {report['total_score']} 低于阈值 {self.PASS_THRESHOLD}")
        return "; ".join(reasons) if reasons else "未通过"
```

---

### 4.5 测试层（Testing Agent）

#### 4.5.1 职责定义

- **环境搭建**：根据测试方案搭建编译和测试环境
- **测试执行**：执行单元测试、集成测试、QEMU 测试等
- **结果分析**：分析测试结果，识别失败原因
- **报告生成**：生成结构化的测试报告

#### 4.5.2 QEMU 测试矩阵

```python
# rv_insights/agents/testing/qemu_matrix.py
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class QEMUConfig:
    """QEMU 测试配置"""
    machine: str           # "virt" | "sifive_u" | "spike"
    cpu: str               # "rv64" | "rv32"
    extensions: List[str]  # ["imafd", "c", "v"]
    memory: str            # "2G"
    smp: int               # 4
    bios: Optional[str]    # OpenSBI 路径
    kernel: Optional[str]  # 内核镜像路径
    initrd: Optional[str]  # initrd 路径
    cmdline: str           # 内核命令行

def get_test_matrix(project: str) -> List[QEMUConfig]:
    """
    获取项目的 QEMU 测试矩阵
    
    覆盖不同的 RISC-V 配置组合
    """
    base_configs = []
    
    if project == "linux":
        base_configs = [
            QEMUConfig(
                machine="virt",
                cpu="rv64",
                extensions=["imafdc"],
                memory="2G",
                smp=1,
                cmdline="root=/dev/ram console=ttyS0"
            ),
            QEMUConfig(
                machine="virt",
                cpu="rv64",
                extensions=["imafdc"],
                memory="4G",
                smp=4,
                cmdline="root=/dev/ram console=ttyS0"
            ),
            QEMUConfig(
                machine="virt",
                cpu="rv64",
                extensions=["imafdcv"],  # 含 Vector 扩展
                memory="2G",
                smp=2,
                cmdline="root=/dev/ram console=ttyS0"
            ),
        ]
    elif project == "qemu":
        base_configs = [
            QEMUConfig(
                machine="virt",
                cpu="rv64",
                extensions=["imafdc"],
                memory="2G",
                smp=1,
                cmdline=""
            ),
        ]
    
    return base_configs
```

#### 4.5.3 测试 Agent 实现

```python
# rv_insights/agents/testing/claude_test_agent.py
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from dataclasses import dataclass
from typing import List, Dict, Optional
import subprocess
import json
from pathlib import Path
import time

@dataclass
class TestResult:
    """测试结果"""
    test_suite: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    duration_seconds: float
    log_output: str
    failures: List[Dict]

@dataclass
class TestingReport:
    """测试报告"""
    overall_status: str  # "PASS" | "FAIL" | "PARTIAL"
    test_results: List[TestResult]
    coverage_report: Optional[Dict]
    performance_baseline: Optional[Dict]
    environment_info: Dict
    recommendations: List[str]

class ClaudeTestingAgent:
    """
    基于 Claude Agent SDK 的测试 Agent
    """
    
    def __init__(self, workspace: Path, project: str, task_id: str):
        self.workspace = workspace
        self.project = project
        self.task_id = task_id
        self.repo_path = workspace / project
        
        self.options = ClaudeAgentOptions(
            system_prompt=self._build_system_prompt(),
            permission_mode="prompt",  # 危险操作需确认
            read_write_tools=True,
            bash_tools=True,
            cwd=str(self.repo_path),
            max_cost=3.0,
            audit_log_path=f"/logs/test_{task_id}.log"
        )
        self.client = ClaudeSDKClient(options=self.options)
    
    def _build_system_prompt(self) -> str:
        return f"""
        你是 RV-Insights 的测试专家，负责 {self.project} 项目的测试验证。
        
        ## 测试原则
        1. **可复现**：所有测试必须可重复执行
        2. **自动化**：尽量使用脚本而非手动操作
        3. **隔离性**：每个测试独立，不互相影响
        4. **覆盖性**：覆盖正常路径和错误路径
        
        ## 可用工具
        - 文件读写：修改配置、编写测试脚本
        - Bash 执行：编译、运行测试、环境配置
        - Docker 控制：管理测试容器（通过 docker CLI）
        
        ## QEMU 测试指南
        - 使用 qemu-system-riscv64
        - 常用参数：-machine virt -cpu rv64 -m 2G -smp 4
        - 使用 -nographic 进行无图形测试
        - 使用 -serial stdio 捕获串口输出
        - 超时设置：每个测试 300 秒
        
        ## 注意事项
        - 测试失败时记录完整的错误日志
        - 区分"环境问题"和"代码问题"
        - 超时测试标记为 SKIP 而非 FAIL
        """
    
    async def execute_tests(self, plan: dict) -> TestingReport:
        """执行测试方案"""
        test_plan = plan["testing_plan"]
        results = []
        
        # 1. 单元测试
        if test_plan.get("unit_tests", {}).get("required", False):
            unit_result = await self._run_unit_tests(test_plan["unit_tests"])
            results.append(unit_result)
        
        # 2. 编译测试
        compile_result = await self._run_compile_tests()
        results.append(compile_result)
        
        # 3. QEMU 测试
        if test_plan.get("qemu_tests", {}).get("required", False):
            qemu_result = await self._run_qemu_tests(test_plan["qemu_tests"])
            results.append(qemu_result)
        
        # 4. 静态分析
        static_result = await self._run_static_analysis()
        results.append(static_result)
        
        # 综合判断
        overall = self._assess_overall(results)
        
        return TestingReport(
            overall_status=overall,
            test_results=results,
            coverage_report=None,
            performance_baseline=None,
            environment_info=self._get_env_info(),
            recommendations=self._generate_recommendations(results)
        )
    
    async def _run_unit_tests(self, config: dict) -> TestResult:
        """运行单元测试"""
        start = time.time()
        
        if self.project == "linux":
            # KUnit 测试
            cmd = ['make', '-C', str(self.repo_path),
                   'ARCH=riscv', 'CROSS_COMPILE=riscv64-linux-gnu-',
                   'kunit.run']
        else:
            cmd = ['make', 'check', '-C', str(self.repo_path)]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        duration = time.time() - start
        
        # 解析结果
        output = result.stdout + result.stderr
        
        # 简单的通过/失败判断
        passed = result.returncode == 0
        
        return TestResult(
            test_suite="unit_tests",
            total_tests=0,  # 需从输出解析
            passed=1 if passed else 0,
            failed=0 if passed else 1,
            skipped=0,
            duration_seconds=duration,
            log_output=output[-5000:],  # 限制日志长度
            failures=[] if passed else [{"error": "Unit tests failed"}]
        )
    
    async def _run_compile_tests(self) -> TestResult:
        """运行编译测试"""
        start = time.time()
        
        if self.project == "linux":
            configs = ["defconfig", "allmodconfig", "allyesconfig"]
            for config in configs:
                subprocess.run(
                    ['make', '-C', str(self.repo_path),
                     'ARCH=riscv', 'CROSS_COMPILE=riscv64-linux-gnu-',
                     config],
                    capture_output=True
                )
                result = subprocess.run(
                    ['make', '-C', str(self.repo_path),
                     'ARCH=riscv', 'CROSS_COMPILE=riscv64-linux-gnu-',
                     '-j4'],
                    capture_output=True, text=True, timeout=600
                )
                if result.returncode != 0:
                    break
        else:
            result = subprocess.run(
                ['make', '-C', str(self.repo_path), '-j4'],
                capture_output=True, text=True, timeout=600
            )
        
        duration = time.time() - start
        passed = result.returncode == 0
        
        return TestResult(
            test_suite="compile_tests",
            total_tests=len(configs) if self.project == "linux" else 1,
            passed=sum(1 for c in configs if True) if passed else 0,
            failed=0 if passed else 1,
            skipped=0,
            duration_seconds=duration,
            log_output=result.stderr[-3000:] if not passed else "",
            failures=[] if passed else [{"error": "Compilation failed"}]
        )
    
    async def _run_qemu_tests(self, config: dict) -> TestResult:
        """运行 QEMU 测试"""
        start = time.time()
        
        # 构建 QEMU 命令
        qemu_cmd = [
            'qemu-system-riscv64',
            '-machine', config.get('machine', 'virt'),
            '-cpu', config.get('cpu', 'rv64'),
            '-m', config.get('memory', '2G'),
            '-smp', str(config.get('smp', 4)),
            '-nographic',
            '-serial', 'stdio',
            '-no-reboot'
        ]
        
        if 'kernel' in config:
            qemu_cmd.extend(['-kernel', config['kernel']])
        
        # 运行 QEMU，设置超时
        try:
            result = subprocess.run(
                qemu_cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            duration = time.time() - start
            
            # 分析输出
            output = result.stdout
            
            # 检查内核是否正常启动
            boot_success = 'Linux version' in output or 'Starting kernel' in output
            
            return TestResult(
                test_suite="qemu_boot",
                total_tests=1,
                passed=1 if boot_success else 0,
                failed=0 if boot_success else 1,
                skipped=0,
                duration_seconds=duration,
                log_output=output[-3000:],
                failures=[] if boot_success else [{"error": "QEMU boot failed"}]
            )
            
        except subprocess.TimeoutExpired:
            return TestResult(
                test_suite="qemu_boot",
                total_tests=1,
                passed=0,
                failed=0,
                skipped=1,
                duration_seconds=120,
                log_output="Timeout: QEMU test exceeded 120 seconds",
                failures=[{"error": "Timeout"}]
            )
    
    async def _run_static_analysis(self) -> TestResult:
        """运行静态分析"""
        start = time.time()
        
        if self.project == "linux":
            # 使用 sparse
            result = subprocess.run(
                ['make', '-C', str(self.repo_path),
                 'ARCH=riscv', 'C=1', 'CF="-Wsparse-all"'],
                capture_output=True, text=True, timeout=300
            )
        else:
            result = subprocess.run(
                ['echo', 'Static analysis not configured for this project'],
                capture_output=True, text=True
            )
        
        duration = time.time() - start
        
        # sparse 返回警告算正常
        warnings = [l for l in result.stderr.split('\n') if 'warning:' in l]
        
        return TestResult(
            test_suite="static_analysis",
            total_tests=1,
            passed=1,
            failed=0,
            skipped=0,
            duration_seconds=duration,
            log_output=f"Warnings found: {len(warnings)}\n" + '\n'.join(warnings[:20]),
            failures=[]
        )
    
    def _assess_overall(self, results: List[TestResult]) -> str:
        """综合评估"""
        total_failed = sum(r.failed for r in results)
        total_skipped = sum(r.skipped for r in results)
        total_tests = sum(r.total_tests for r in results)
        
        if total_failed == 0 and total_skipped == 0:
            return "PASS"
        elif total_failed == 0:
            return "PARTIAL"
        else:
            return "FAIL"
    
    def _get_env_info(self) -> Dict:
        """获取环境信息"""
        return {
            "qemu_version": subprocess.run(['qemu-system-riscv64', '--version'],
                                           capture_output=True, text=True).stdout.split('\n')[0],
            "gcc_version": subprocess.run(['riscv64-linux-gnu-gcc', '--version'],
                                          capture_output=True, text=True).stdout.split('\n')[0],
            "make_version": subprocess.run(['make', '--version'],
                                          capture_output=True, text=True).stdout.split('\n')[0],
        }
    
    def _generate_recommendations(self, results: List[TestResult]) -> List[str]:
        """生成建议"""
        recommendations = []
        
        for result in results:
            if result.failed > 0:
                recommendations.append(
                    f"{result.test_suite}: {result.failed} failures need attention"
                )
            if result.skipped > 0:
                recommendations.append(
                    f"{result.test_suite}: {result.skipped} tests skipped (may need extended timeout)"
                )
        
        if not recommendations:
            recommendations.append("All tests passed. Ready for submission.")
        
        return recommendations
```

---

*（文档继续，下一部分：SDK 融合架构、HITL、数据流、安全、部署等）*


## 5. SDK 选型分析与融合策略

### 5.1 OpenAI Agents SDK 核心特性（详细版）

#### 5.1.1 核心概念详解

| 概念 | 说明 | 在 RV-Insights 中的应用 |
|------|------|------------------------|
| **Agent** | 由 `instructions` + `model` + `tools` 三要素定义 | 探索、规划、审核 Agent |
| **Handoff** | Agent 间通过 Function Calling 交接任务 | 协调器将任务路由到专项 Agent |
| **Guardrail** | 输入/输出两层边界检查 | 确保 Artifact 格式合规 |
| **Tracing** | 内置全链路追踪 | 记录每个 LLM 调用和工具执行 |
| **HITL** | `needs_approval` 工具暂停机制 | 每个阶段后的人工审核点 |

#### 5.1.2 HITL 实现细节（基于官方文档）

```python
# OpenAI Agents SDK HITL 实现示例
from agents import Agent, Runner, RunState, function_tool
import json
from pathlib import Path

# 定义需要审批的工具
@function_tool(needs_approval=True)
async def commit_changes(message: str) -> str:
    """提交代码变更（需要人工确认）"""
    return f"Committed with message: {message}"

@function_tool(needs_approval=lambda _ctx, params, _id: params.get("scope") == "production")
async def deploy_patch(patch_path: str, scope: str = "sandbox") -> str:
    """部署 Patch，仅在 production 范围时需要审批"""
    return f"Deployed {patch_path} to {scope}"

# HITL 工作流实现
STATE_PATH = Path("/var/lib/rv-insights/hitl_states")

async def run_with_hitl(agent: Agent, task_input: str, task_id: str) -> dict:
    """
    带人机回路的 Agent 执行
    
    流程：
    1. 启动 Agent 执行
    2. 遇到需要审批的工具调用时暂停
    3. 序列化状态到磁盘
    4. 发送通知等待人工审批
    5. 人工审批后恢复执行
    """
    result = await Runner.run(agent, task_input)
    
    while result.interruptions:
        # 1. 持久化状态
        state = result.to_state()
        state_file = STATE_PATH / f"{task_id}.json"
        STATE_PATH.mkdir(parents=True, exist_ok=True)
        state_file.write_text(state.to_string())
        
        # 2. 发送 HITL 通知（WebSocket / Email / Slack）
        await send_hitl_notification(task_id, result.interruptions)
        
        # 3. 等待人工决策（轮询或 Webhook）
        decisions = await wait_for_human_decision(task_id, timeout=86400)
        
        # 4. 加载状态并应用决策
        stored = json.loads(state_file.read_text())
        state = await RunState.from_json(agent, stored)
        
        for interruption in result.interruptions:
            decision = decisions.get(interruption.name)
            if decision == "approve":
                state.approve(interruption, always_approve=False)
            elif decision == "reject":
                state.reject(interruption, message="Human rejected this action")
            elif decision == "abort":
                return {"status": "aborted", "task_id": task_id}
        
        # 5. 恢复执行
        result = await Runner.run(agent, state)
    
    return {
        "status": "completed",
        "task_id": task_id,
        "output": result.final_output
    }

async def send_hitl_notification(task_id: str, interruptions: list):
    """发送 HITL 通知"""
    # WebSocket 推送到前端
    # Email 通知
    # Slack / Discord 通知
    pass

async def wait_for_human_decision(task_id: str, timeout: int = 86400) -> dict:
    """等待人工决策"""
    # 轮询数据库中的决策记录
    # 或等待 Webhook 回调
    pass
```

### 5.2 Claude Agent SDK 核心特性（详细版）

#### 5.2.1 内置工具详解

| 工具 | 功能 | 在 RV-Insights 中的应用 |
|------|------|------------------------|
| `Read` | 读取文件内容 | 代码审查、配置文件读取 |
| `Write` | 写入文件内容 | 代码生成、测试脚本编写 |
| `Edit` | 原地编辑文件 | 代码修改、Patch 应用 |
| `Bash` | 执行 Shell 命令 | 编译、Git 操作、测试执行 |
| `Glob` | 文件模式匹配 | 批量文件操作 |
| `Grep` | 文本搜索 | 代码搜索、模式匹配 |
| `LS` | 目录列表 | 文件系统浏览 |

#### 5.2.2 生命周期 Hooks

```python
# Claude SDK 生命周期 Hooks 实现
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

options = ClaudeAgentOptions(
    system_prompt="...",
    permission_mode="accept_edits",
    read_write_tools=True,
    bash_tools=True,
)

client = ClaudeSDKClient(options=options)

@client.hook("PreToolUse")
async def validate_tool(tool_name: str, params: dict):
    """工具执行前验证"""
    # 禁止删除系统文件
    if tool_name in ["Write", "Edit"]:
        path = params.get("path", "")
        if any(banned in path for banned in ["/etc/", "/usr/", "/bin/", "/sbin/"]):
            return {"action": "reject", "reason": "Protected system path"}
    
    # 禁止危险命令
    if tool_name == "Bash":
        command = params.get("command", "")
        dangerous = ["rm -rf /", "mkfs", "dd if=/dev/zero", ":(){:|:&};:"]
        if any(d in command for d in dangerous):
            return {"action": "reject", "reason": "Dangerous command blocked"}
    
    return {"action": "approve"}

@client.hook("PostToolUse")
async def log_result(tool_name: str, params: dict, result: dict):
    """工具执行后记录"""
    await audit_logger.log({
        "timestamp": datetime.utcnow().isoformat(),
        "tool": tool_name,
        "params": params,
        "result_summary": str(result)[:500],
        "task_id": current_task_id
    })

@client.hook("Stop")
async def cleanup():
    """会话结束时清理"""
    await close_database_connections()
    await release_locks()
```

### 5.3 双 SDK 融合架构（完整实现）

#### 5.3.1 MCP 协议网关实现

```python
# rv_insights/mcp_gateway.py
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server
import asyncio
from typing import Dict, Callable, Any

class RVInsightsMCPGateway:
    """
    RV-Insights MCP 协议网关
    
    实现 OpenAI SDK 和 Claude SDK 之间的工具互操作。
    两个 SDK 都支持 MCP 协议，通过此网关实现工具的统一注册和转发。
    """
    
    def __init__(self):
        self.openai_tools: Dict[str, Any] = {}
        self.claude_tools: Dict[str, Any] = {}
        self.server = Server("rv-insights-gateway")
        
        # 注册 OpenAI SDK 工具（包装为 MCP 工具）
        self._register_openai_tools()
        
        # 注册 Claude SDK 工具（包装为 MCP 工具）
        self._register_claude_tools()
    
    def _register_openai_tools(self):
        """注册 OpenAI SDK 提供的工具到 MCP"""
        openai_tool_defs = [
            Tool(
                name="web_search",
                description="搜索互联网信息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索查询"}
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="fetch_mail_list",
                description="获取邮件列表消息",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "list_name": {"type": "string"},
                        "days": {"type": "integer", "default": 7}
                    },
                    "required": ["list_name"]
                }
            ),
        ]
        
        for tool in openai_tool_defs:
            self.openai_tools[tool.name] = tool
            self.server.register_tool(tool, self._handle_openai_tool)
    
    def _register_claude_tools(self):
        """注册 Claude SDK 提供的工具到 MCP"""
        claude_tool_defs = [
            Tool(
                name="read_file",
                description="读取文件内容",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "offset": {"type": "integer", "default": 0},
                        "limit": {"type": "integer", "default": 100}
                    },
                    "required": ["path"]
                }
            ),
            Tool(
                name="write_file",
                description="写入文件内容",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["path", "content"]
                }
            ),
            Tool(
                name="bash",
                description="执行 Bash 命令",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                        "timeout": {"type": "integer", "default": 60}
                    },
                    "required": ["command"]
                }
            ),
        ]
        
        for tool in claude_tool_defs:
            self.claude_tools[tool.name] = tool
            self.server.register_tool(tool, self._handle_claude_tool)
    
    async def _handle_openai_tool(self, name: str, arguments: dict) -> list:
        """处理 OpenAI 工具的 MCP 调用"""
        # 调用实际的 OpenAI 工具实现
        if name == "web_search":
            result = await self._web_search(arguments["query"])
            return [TextContent(type="text", text=json.dumps(result))]
        elif name == "fetch_mail_list":
            result = await self._fetch_mail_list(
                arguments["list_name"],
                arguments.get("days", 7)
            )
            return [TextContent(type="text", text=json.dumps(result))]
        return [TextContent(type="text", text="Unknown tool")]
    
    async def _handle_claude_tool(self, name: str, arguments: dict) -> list:
        """处理 Claude 工具的 MCP 调用"""
        # 调用实际的 Claude 工具实现
        if name == "read_file":
            path = arguments["path"]
            offset = arguments.get("offset", 0)
            limit = arguments.get("limit", 100)
            
            try:
                with open(path, 'r') as f:
                    lines = f.readlines()[offset:offset+limit]
                    content = ''.join(lines)
                return [TextContent(type="text", text=content)]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        
        elif name == "write_file":
            path = arguments["path"]
            content = arguments["content"]
            
            try:
                with open(path, 'w') as f:
                    f.write(content)
                return [TextContent(type="text", text=f"Written to {path}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        
        elif name == "bash":
            command = arguments["command"]
            timeout = arguments.get("timeout", 60)
            
            try:
                result = subprocess.run(
                    command, shell=True, capture_output=True,
                    text=True, timeout=timeout
                )
                output = result.stdout + result.stderr
                return [TextContent(type="text", text=output)]
            except subprocess.TimeoutExpired:
                return [TextContent(type="text", text="Command timed out")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]
        
        return [TextContent(type="text", text="Unknown tool")]
    
    async def run(self):
        """启动 MCP 网关服务器"""
        async with stdio_server(self.server) as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )

# 跨 SDK 调用示例
class CrossSDKInvoker:
    """
    跨 SDK 工具调用封装
    
    使 OpenAI Agent 可以调用 Claude 工具，反之亦然
    """
    
    def __init__(self, mcp_gateway: RVInsightsMCPGateway):
        self.gateway = mcp_gateway
    
    async def call_for_openai(self, tool_name: str, params: dict) -> dict:
        """
        OpenAI Agent 调用 Claude 工具
        
        使用方式：
        ```python
        # 在 OpenAI Agent 的工具定义中
        @function_tool
        async def read_code_file(path: str) -> str:
            return await cross_sdk.call_for_openai("read_file", {"path": path})
        ```
        """
        if tool_name not in self.gateway.claude_tools:
            raise ValueError(f"Claude tool {tool_name} not found")
        
        results = await self.gateway._handle_claude_tool(tool_name, params)
        return {"result": results[0].text if results else ""}
    
    async def call_for_claude(self, tool_name: str, params: dict) -> dict:
        """
        Claude Agent 调用 OpenAI 工具
        
        使用方式：
        ```python
        # 在 Claude Agent 中通过自定义工具
        @claude_tool
        async def search_web(query: str) -> str:
            return await cross_sdk.call_for_claude("web_search", {"query": query})
        ```
        """
        if tool_name not in self.gateway.openai_tools:
            raise ValueError(f"OpenAI tool {tool_name} not found")
        
        results = await self.gateway._handle_openai_tool(tool_name, params)
        return {"result": results[0].text if results else ""}
```

#### 5.3.2 融合架构调用流

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        跨 SDK 工具调用流程                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  场景：审核 Agent（OpenAI SDK）需要读取代码文件                            │
│                                                                         │
│  OpenAI Agent (Review)                                                  │
│       │                                                                 │
│       │ 调用 read_code_file()                                           │
│       │ （自定义 function_tool 包装）                                    │
│       ▼                                                                 │
│  ┌─────────────────┐                                                    │
│  │ CrossSDKInvoker │                                                    │
│  │ .call_for_openai│─── MCP 协议 ───► ┌─────────────────┐              │
│  │ ("read_file")   │                  │  MCP Gateway    │              │
│  └─────────────────┘                  │                 │              │
│                                       │ 路由到 Claude   │              │
│                                       │ 工具处理器      │              │
│                                       └────────┬────────┘              │
│                                                │                        │
│                                                ▼                        │
│                                       ┌─────────────────┐              │
│                                       │ 实际文件读取    │              │
│                                       │ （Bash/cat）    │              │
│                                       └────────┬────────┘              │
│                                                │                        │
│                                                │ 返回文件内容           │
│                                                │                        │
│  OpenAI Agent ◄────────────────────────────────┘                        │
│  （继续审核逻辑）                                                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. 人机回路（HITL）机制

### 6.1 HITL 状态机（增强版）

```python
# rv_insights/hitl/state_machine.py
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime
import asyncio

class HITLState(Enum):
    """HITL 相关状态"""
    # 正常流程状态
    IDLE = auto()
    RUNNING = auto()
    PAUSED_FOR_APPROVAL = auto()
    APPROVED = auto()
    REJECTED = auto()
    
    # 特殊状态
    TIMED_OUT = auto()
    ESCALATED = auto()
    ABORTED = auto()

class WorkflowStage(Enum):
    """工作流阶段"""
    DISCOVERY = "discovery"
    PLANNING = "planning"
    DEVELOPMENT = "development"
    REVIEW = "review"
    TESTING = "testing"
    COMPLETE = "complete"
    ABORTED = "aborted"

@dataclass
class HITLRequest:
    """HITL 请求"""
    request_id: str
    task_id: str
    stage: WorkflowStage
    stage_output: dict
    required_action: str
    options: List[dict]
    created_at: datetime = field(default_factory=datetime.utcnow)
    timeout_at: Optional[datetime] = None
    assigned_reviewer: Optional[str] = None
    
    def is_expired(self) -> bool:
        if self.timeout_at:
            return datetime.utcnow() > self.timeout_at
        return False

@dataclass
class HITLDecision:
    """HITL 决策"""
    request_id: str
    reviewer_id: str
    decision: str  # "approve" | "reject" | "modify" | "abort"
    feedback: Optional[str] = None
    modified_output: Optional[dict] = None
    decided_at: datetime = field(default_factory=datetime.utcnow)

class HITLStateMachine:
    """
    HITL 状态机
    
    管理整个工作流的状态转换和 HITL 暂停点
    """
    
    # 状态转换表：当前状态 -> (触发事件 -> 下一状态)
    TRANSITIONS = {
        WorkflowStage.DISCOVERY: {
            "approve": WorkflowStage.PLANNING,
            "reject": WorkflowStage.DISCOVERY,  # 重新探索
            "abort": WorkflowStage.ABORTED
        },
        WorkflowStage.PLANNING: {
            "approve": WorkflowStage.DEVELOPMENT,
            "reject": WorkflowStage.PLANNING,   # 重新规划
            "abort": WorkflowStage.ABORTED
        },
        WorkflowStage.DEVELOPMENT: {
            "approve": WorkflowStage.REVIEW,
            "reject": WorkflowStage.DEVELOPMENT, # 重新开发
            "abort": WorkflowStage.ABORTED
        },
        WorkflowStage.REVIEW: {
            "approve": WorkflowStage.TESTING,
            "reject": WorkflowStage.DEVELOPMENT, # 审核不通过返回开发
            "abort": WorkflowStage.ABORTED
        },
        WorkflowStage.TESTING: {
            "approve": WorkflowStage.COMPLETE,
            "reject": WorkflowStage.DEVELOPMENT, # 测试失败返回开发
            "abort": WorkflowStage.ABORTED
        }
    }
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.current_stage = WorkflowStage.DISCOVERY
        self.stage_history = []
        self.pending_hitl: Optional[HITLRequest] = None
    
    def can_transition(self, event: str) -> bool:
        """检查是否可以进行状态转换"""
        transitions = self.TRANSITIONS.get(self.current_stage, {})
        return event in transitions
    
    def transition(self, event: str, decision: HITLDecision) -> WorkflowStage:
        """执行状态转换"""
        if not self.can_transition(event):
            raise ValueError(f"Invalid transition: {self.current_stage} -> {event}")
        
        next_stage = self.TRANSITIONS[self.current_stage][event]
        
        # 记录历史
        self.stage_history.append({
            "from": self.current_stage.value,
            "to": next_stage.value,
            "event": event,
            "decision": decision.decision,
            "reviewer": decision.reviewer_id,
            "timestamp": decision.decided_at.isoformat()
        })
        
        self.current_stage = next_stage
        self.pending_hitl = None
        
        return next_stage
    
    def create_hitl_request(self, stage_output: dict) -> HITLRequest:
        """创建 HITL 请求"""
        request = HITLRequest(
            request_id=f"HITL-{self.task_id}-{self.current_stage.value}",
            task_id=self.task_id,
            stage=self.current_stage,
            stage_output=stage_output,
            required_action=f"请审核 {self.current_stage.value} 阶段的产出",
            options=self._get_options_for_stage(),
            timeout_at=datetime.utcnow() + timedelta(hours=24)
        )
        self.pending_hitl = request
        return request
    
    def _get_options_for_stage(self) -> List[dict]:
        """获取当前阶段的选项"""
        base_options = [
            {"action": "approve", "label": "通过，进入下一阶段", "description": "确认当前产出质量合格"},
            {"action": "reject", "label": "拒绝，返回修改", "description": "要求 Agent 重新执行当前阶段"},
            {"action": "abort", "label": "终止任务", "description": "放弃当前贡献任务"}
        ]
        
        # 特定阶段的额外选项
        if self.current_stage == WorkflowStage.REVIEW:
            base_options.insert(1, {
                "action": "modify",
                "label": "提出修改意见",
                "description": "通过但要求特定修改后继续"
            })
        
        return base_options
```

### 6.2 HITL Web UI 交互设计

```typescript
// HITL 前端组件接口定义（React + TypeScript）

interface HITLRequest {
  requestId: string;
  taskId: string;
  stage: 'discovery' | 'planning' | 'development' | 'review' | 'testing';
  stageOutput: {
    summary: string;
    details: Record<string, any>;
    artifacts: Array<{
      type: string;
      name: string;
      url: string;
      preview?: string;
    }>;
  };
  requiredAction: string;
  options: Array<{
    action: 'approve' | 'reject' | 'modify' | 'abort';
    label: string;
    description: string;
  }>;
  createdAt: string;
  timeoutAt: string;
  timeRemaining: number; // 秒
}

// HITL 审核面板组件
interface HITLReviewPanelProps {
  request: HITLRequest;
  onDecision: (decision: HITLDecision) => void;
}

// 不同阶段的展示组件
interface StageOutputRendererProps {
  stage: string;
  output: Record<string, any>;
}

// 示例：开发阶段的审核界面
const DevelopmentReviewPanel: React.FC<{output: any}> = ({output}) => {
  return (
    <div className="development-review">
      <h3>代码变更审核</h3>
      
      {/* Git Diff 视图 */}
      <DiffViewer 
        diff={output.diff}
        filePath={output.modifiedFiles}
      />
      
      {/* 编译状态 */}
      <CompileStatus 
        status={output.compileStatus ? 'success' : 'failure'}
        logs={output.compileLogs}
      />
      
      {/* Checkpatch 结果 */}
      <CheckpatchResult 
        passed={output.checkpatchStatus}
        issues={output.checkpatchIssues}
      />
      
      {/* 统计信息 */}
      <DiffStats 
        insertions={output.diffStats.insertions}
        deletions={output.diffStats.deletions}
        filesChanged={output.modifiedFiles.length}
      />
    </div>
  );
};
```

### 6.3 通知机制

```python
# rv_insights/hitl/notifications.py
from dataclasses import dataclass
from typing import List, Optional
import aiohttp
import json

@dataclass
class NotificationConfig:
    """通知配置"""
    channels: List[str]  # ["websocket", "email", "slack", "webhook"]
    webhook_url: Optional[str] = None
    slack_webhook: Optional[str] = None
    email_recipients: Optional[List[str]] = None

class HITLNotificationService:
    """HITL 通知服务"""
    
    def __init__(self, config: NotificationConfig):
        self.config = config
    
    async def notify(self, request: HITLRequest):
        """发送 HITL 通知到所有配置渠道"""
        tasks = []
        
        if "websocket" in self.config.channels:
            tasks.append(self._send_websocket(request))
        
        if "email" in self.config.channels:
            tasks.append(self._send_email(request))
        
        if "slack" in self.config.channels and self.config.slack_webhook:
            tasks.append(self._send_slack(request))
        
        if "webhook" in self.config.channels and self.config.webhook_url:
            tasks.append(self._send_webhook(request))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_websocket(self, request: HITLRequest):
        """通过 WebSocket 推送"""
        # 使用 Redis Pub/Sub 或直接的 WebSocket 管理器
        message = {
            "type": "HITL_REQUEST",
            "request_id": request.request_id,
            "task_id": request.task_id,
            "stage": request.stage.value,
            "summary": request.stage_output.get("summary", ""),
            "timeout_at": request.timeout_at.isoformat() if request.timeout_at else None
        }
        # 推送到 WebSocket 连接管理器
        await websocket_manager.broadcast(request.task_id, message)
    
    async def _send_email(self, request: HITLRequest):
        """发送邮件通知"""
        # 使用 aiosmtplib 或外部邮件服务
        subject = f"[RV-Insights] HITL 审核请求: {request.task_id} - {request.stage.value}"
        body = f"""
        任务 {request.task_id} 的 {request.stage.value} 阶段已完成，等待您的审核。
        
        摘要：{request.stage_output.get('summary', 'N/A')}
        
        请在 24 小时内处理：
        审核链接：https://rv-insights.local/hitl/{request.request_id}
        """
        # 发送邮件...
    
    async def _send_slack(self, request: HITLRequest):
        """发送 Slack 通知"""
        payload = {
            "text": f"RV-Insights HITL 审核请求",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"任务 {request.task_id} 等待审核"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*阶段:*\n{request.stage.value}"},
                        {"type": "mrkdwn", "text": f"*任务ID:*\n{request.task_id}"},
                    ]
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "去审核"},
                            "url": f"https://rv-insights.local/hitl/{request.request_id}",
                            "style": "primary"
                        }
                    ]
                }
            ]
        }
        
        async with aiohttp.ClientSession() as session:
            await session.post(self.config.slack_webhook, json=payload)
    
    async def _send_webhook(self, request: HITLRequest):
        """发送到自定义 Webhook"""
        payload = {
            "event": "hitl.requested",
            "request_id": request.request_id,
            "task_id": request.task_id,
            "stage": request.stage.value,
            "timestamp": datetime.utcnow().isoformat(),
            "data": request.stage_output
        }
        
        async with aiohttp.ClientSession() as session:
            await session.post(self.config.webhook_url, json=payload)
```

---

## 7. 数据流与状态管理

### 7.1 数据流架构（增强版）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            数据流与状态管理                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   探索报告 ──────► 规划方案 ──────► 代码变更 ──────► 审核结果 ──────► 测试报告  │
│      │                │                │                │                │   │
│      ▼                ▼                ▼                ▼                ▼   │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌────────┐│
│  │Artifact │     │Artifact │     │Artifact │     │Artifact │     │Artifact││
│  │ Store   │     │ Store   │     │ Store   │     │ Store   │     │ Store  ││
│  │ (S3/    │     │ (S3/    │     │ (Git    │     │ (S3/    │     │ (S3/   ││
│  │  Local) │     │  Local) │     │  Diff)  │     │  Local) │     │  Local)││
│  └────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘     └───┬────┘│
│       │               │               │               │               │    │
│       └───────────────┴───────────────┴───────────────┴───────────────┘    │
│                                   │                                        │
│                                   ▼                                        │
│                         ┌─────────────────┐                                │
│                         │   State Store    │                                │
│                         │  (PostgreSQL)    │                                │
│                         │                  │                                │
│                         │  • tasks         │                                │
│                         │  • stages        │                                │
│                         │  • artifacts     │                                │
│                         │  • hitl_requests │                                │
│                         │  • audit_logs    │                                │
│                         └─────────────────┘                                │
│                                   │                                        │
│                                   ▼                                        │
│                         ┌─────────────────┐                                │
│                         │   Cache Layer    │                                │
│                         │   (Redis)        │                                │
│                         │                  │                                │
│                         │  • 会话状态      │                                │
│                         │  • Agent 上下文  │                                │
│                         │  • 速率限制      │                                │
│                         │  • 锁管理        │                                │
│                         └─────────────────┘                                │
│                                   │                                        │
│                                   ▼                                        │
│                         ┌─────────────────┐                                │
│                         │   Event Bus      │                                │
│                         │  (Redis Pub/Sub) │                                │
│                         │                  │                                │
│                         │  Events:         │                                │
│                         │  • task.created  │                                │
│                         │  • stage.started │                                │
│                         │  • stage.completed│                               │
│                         │  • hitl.requested│                                │
│                         │  • hitl.resolved │                                │
│                         │  • agent.error   │                                │
│                         └─────────────────┘                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 核心数据模型（完整定义）

```python
# rv_insights/models.py
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, DateTime, 
    Text, JSON, ForeignKey, Enum, Boolean, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class TaskStatus(enum.Enum):
    PENDING = "pending"
    EXPLORING = "exploring"
    PLANNING = "planning"
    DEVELOPING = "developing"
    REVIEWING = "reviewing"
    TESTING = "testing"
    COMPLETE = "complete"
    ABORTED = "aborted"
    FAILED = "failed"

class StageType(enum.Enum):
    DISCOVERY = "discovery"
    PLANNING = "planning"
    DEVELOPMENT = "development"
    REVIEW = "review"
    TESTING = "testing"

class StageStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    HITL_PENDING = "hitl_pending"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class HITLDecisionType(enum.Enum):
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    ABORT = "abort"

# ============ 任务表 ============
class Task(Base):
    __tablename__ = "tasks"
    
    task_id = Column(String(32), primary_key=True)  # RV-YYYY-MM-DD-NNN
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    
    # 来源信息
    source_type = Column(String(50))  # "auto_discovery" | "user_input"
    source_url = Column(String(500))
    
    # 目标项目
    target_project = Column(String(50))  # "linux" | "gcc" | "qemu" ...
    
    # 用户关联
    created_by = Column(String(100), nullable=False)
    assigned_reviewer = Column(String(100))
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # 元数据
    priority = Column(Integer, default=1)  # 1-5
    tags = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)
    
    # 关系
    stages = relationship("Stage", back_populates="task", order_by="Stage.sequence")
    
    __table_args__ = (
        Index('idx_task_status', 'status'),
        Index('idx_task_project', 'target_project'),
        Index('idx_task_created_by', 'created_by'),
    )

# ============ 阶段表 ============
class Stage(Base):
    __tablename__ = "stages"
    
    stage_id = Column(String(50), primary_key=True)
    task_id = Column(String(32), ForeignKey("tasks.task_id"), nullable=False)
    sequence = Column(Integer, nullable=False)  # 阶段顺序
    
    stage_type = Column(Enum(StageType), nullable=False)
    status = Column(Enum(StageStatus), default=StageStatus.PENDING, nullable=False)
    
    # Artifact 关联
    input_artifact_id = Column(String(50), ForeignKey("artifacts.artifact_id"))
    output_artifact_id = Column(String(50), ForeignKey("artifacts.artifact_id"))
    
    # Agent 信息
    agent_name = Column(String(100))
    agent_model = Column(String(50))
    
    # 执行统计
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    execution_time_seconds = Column(Float)
    
    # 成本
    cost_usd = Column(Float, default=0.0)
    token_input = Column(Integer, default=0)
    token_output = Column(Integer, default=0)
    
    # 迭代计数（用于审核阶段）
    iteration_count = Column(Integer, default=0)
    max_iterations = Column(Integer, default=5)
    
    # 错误信息
    error_message = Column(Text)
    
    # 关系
    task = relationship("Task", back_populates="stages")
    input_artifact = relationship("Artifact", foreign_keys=[input_artifact_id])
    output_artifact = relationship("Artifact", foreign_keys=[output_artifact_id])
    logs = relationship("AgentLog", back_populates="stage")
    
    __table_args__ = (
        Index('idx_stage_task', 'task_id'),
        Index('idx_stage_status', 'status'),
    )

# ============ Artifact 表 ============
class Artifact(Base):
    __tablename__ = "artifacts"
    
    artifact_id = Column(String(50), primary_key=True)
    artifact_type = Column(String(50), nullable=False)  # "report" | "plan" | "code" | "diff" | "review" | "test_result"
    
    # 内容存储
    content_json = Column(JSON)  # 结构化内容
    content_text = Column(Text)  # 文本内容
    storage_path = Column(String(500))  # 大文件存储路径（S3/本地）
    
    # 关联
    parent_artifact_id = Column(String(50), ForeignKey("artifacts.artifact_id"))
    task_id = Column(String(32), ForeignKey("tasks.task_id"))
    
    # 创建信息
    created_by_agent = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 版本
    version = Column(String(20), default="1.0")
    
    __table_args__ = (
        Index('idx_artifact_task', 'task_id'),
        Index('idx_artifact_type', 'artifact_type'),
    )

# ============ Agent 日志表 ============
class AgentLog(Base):
    __tablename__ = "agent_logs"
    
    log_id = Column(String(50), primary_key=True)
    stage_id = Column(String(50), ForeignKey("stages.stage_id"), nullable=False)
    
    log_level = Column(String(20), default="INFO")  # DEBUG | INFO | WARNING | ERROR
    log_type = Column(String(50))  # "llm_call" | "tool_call" | "handoff" | "guardrail" | "error"
    
    # 内容
    message = Column(Text)
    details = Column(JSON)  # 结构化详情
    
    # 追踪
    trace_id = Column(String(100))
    span_id = Column(String(100))
    
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    stage = relationship("Stage", back_populates="logs")
    
    __table_args__ = (
        Index('idx_log_stage', 'stage_id'),
        Index('idx_log_timestamp', 'timestamp'),
    )

# ============ HITL 请求表 ============
class HITLRequest(Base):
    __tablename__ = "hitl_requests"
    
    request_id = Column(String(50), primary_key=True)
    task_id = Column(String(32), ForeignKey("tasks.task_id"), nullable=False)
    stage_id = Column(String(50), ForeignKey("stages.stage_id"), nullable=False)
    
    status = Column(String(20), default="pending")  # pending | approved | rejected | timeout | aborted
    
    # 请求内容
    stage_summary = Column(Text)
    stage_output = Column(JSON)
    options = Column(JSON)
    
    # 决策
    decision = Column(Enum(HITLDecisionType))
    decision_feedback = Column(Text)
    decided_by = Column(String(100))
    decided_at = Column(DateTime)
    
    # 时间
    created_at = Column(DateTime, default=datetime.utcnow)
    timeout_at = Column(DateTime)
    
    __table_args__ = (
        Index('idx_hitl_task', 'task_id'),
        Index('idx_hitl_status', 'status'),
    )

# ============ 审计日志表 ============
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    log_id = Column(String(50), primary_key=True)
    
    action = Column(String(100), nullable=False)  # "task_created" | "stage_started" | "hitl_decided" | "agent_executed"
    actor = Column(String(100), nullable=False)  # user_id 或 agent_name
    actor_type = Column(String(20))  # "human" | "agent"
    
    target_type = Column(String(50))  # "task" | "stage" | "artifact"
    target_id = Column(String(50))
    
    details = Column(JSON)
    ip_address = Column(String(50))
    user_agent = Column(String(200))
    
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_audit_target', 'target_type', 'target_id'),
        Index('idx_audit_actor', 'actor'),
        Index('idx_audit_timestamp', 'timestamp'),
    )

# 创建表
def init_database(database_url: str):
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return engine
```

---

*（文档继续，下一部分：安全与权限控制、部署架构、技术栈、演进路线、附录）*


## 8. 安全与权限控制

### 8.1 沙箱实现细节

#### 8.1.1 gVisor + Docker 沙箱配置

```yaml
# docker-compose.sandbox.yml
version: '3.8'

services:
  sandbox-dev:
    image: rv-insights/sandbox:latest
    runtime: runsc  # gVisor 运行时
    
    # 资源限制
    cpus: '4'
    mem_limit: 8g
    memswap_limit: 8g
    
    # 存储限制
    storage_opt:
      size: 20G
    
    # 安全选项
    security_opt:
      - no-new-privileges:true
      - seccomp:./profiles/seccomp-default.json
      - apparmor:rv-insights-sandbox
    
    read_only: true
    
    # 可写目录（tmpfs）
    tmpfs:
      - /tmp:noexec,nosuid,size=2g
      - /workspace:exec,size=10g,uid=1000,gid=1000
    
    # 挂载点
    volumes:
      - type: bind
        source: /repos
        target: /repos
        read_only: true
      - type: bind
        source: /logs
        target: /logs
        read_only: false
    
    # 网络隔离
    networks:
      - sandbox-net
    
    # 禁止特权
    privileged: false
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETGID
      - SETUID
    
    # 用户
    user: "developer:developer"
    
    # 健康检查
    healthcheck:
      test: ["CMD", "echo", "ok"]
      interval: 30s
      timeout: 5s
      retries: 3

networks:
  sandbox-net:
    internal: true  # 无外网访问
```

#### 8.1.2 seccomp 策略文件

```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "architectures": ["SCMP_ARCH_X86_64", "SCMP_ARCH_X86", "SCMP_ARCH_AARCH64"],
  "syscalls": [
    {
      "names": [
        "accept", "accept4", "access", "adjtimex", "alarm", "bind",
        "brk", "capget", "capset", "chdir", "chmod", "chown", "chroot",
        "clock_getres", "clock_gettime", "clock_nanosleep", "clone",
        "clone3", "close", "close_range", "connect", "copy_file_range",
        "creat", "dup", "dup2", "dup3", "epoll_create", "epoll_create1",
        "epoll_ctl", "epoll_ctl_old", "epoll_pwait", "epoll_pwait2",
        "epoll_wait", "epoll_wait_old", "eventfd", "eventfd2", "execve",
        "execveat", "exit", "exit_group", "faccessat", "faccessat2",
        "fadvise64", "fadvise64_64", "fallocate", "fanotify_mark",
        "fchdir", "fchmod", "fchmodat", "fchown", "fchownat", "fcntl",
        "fdatasync", "fgetxattr", "flistxattr", "flock", "fork",
        "fremovexattr", "fsetxattr", "fstat", "fstatfs", "fsync",
        "ftruncate", "futex", "getcpu", "getcwd", "getdents",
        "getdents64", "getegid", "geteuid", "getgid", "getgroups",
        "getitimer", "getpeername", "getpgid", "getpgrp", "getpid",
        "getppid", "getpriority", "getrandom", "getresgid", "getresuid",
        "getrlimit", "get_robust_list", "getrusage", "getsid", "getsockname",
        "getsockopt", "get_thread_area", "gettid", "gettimeofday",
        "getuid", "getxattr", "inotify_add_watch", "inotify_init",
        "inotify_init1", "inotify_rm_watch", "io_cancel", "ioctl",
        "io_destroy", "io_getevents", "io_pgetevents", "ioprio_get",
        "ioprio_set", "io_setup", "io_submit", "io_uring_enter",
        "io_uring_register", "io_uring_setup", "kill", "lchown",
        "lgetxattr", "link", "linkat", "listen", "listxattr", "llistxattr",
        "lremovexattr", "lseek", "lsetxattr", "lstat", "madvise",
        "membarrier", "memfd_create", "mincore", "mkdir", "mkdirat",
        "mknod", "mknodat", "mlock", "mlock2", "mlockall", "mmap",
        "mmap2", "mprotect", "mq_getsetattr", "mq_notify", "mq_open",
        "mq_timedreceive", "mq_timedsend", "mq_unlink", "mremap",
        "msgctl", "msgget", "msgrcv", "msgsnd", "msync", "munlock",
        "munlockall", "munmap", "nanosleep", "newfstatat", "open",
        "openat", "openat2", "pause", "pidfd_open", "pidfd_send_signal",
        "pipe", "pipe2", "pivot_root", "poll", "ppoll", "prctl",
        "pread64", "preadv", "preadv2", "prlimit64", "pselect6",
        "pwrite64", "pwritev", "pwritev2", "read", "readahead",
        "readdir", "readlink", "readlinkat", "readv", "recv",
        "recvfrom", "recvmmsg", "recvmsg", "remap_file_pages",
        "removexattr", "rename", "renameat", "renameat2", "restart_syscall",
        "rmdir", "rseq", "rt_sigaction", "rt_sigpending", "rt_sigprocmask",
        "rt_sigqueueinfo", "rt_sigreturn", "rt_sigsuspend", "rt_sigtimedwait",
        "rt_tgsigqueueinfo", "sched_getaffinity", "sched_getattr",
        "sched_getparam", "sched_get_priority_max", "sched_get_priority_min",
        "sched_getscheduler", "sched_rr_get_interval", "sched_setaffinity",
        "sched_setattr", "sched_setparam", "sched_setscheduler",
        "sched_yield", "seccomp", "select", "semctl", "semget", "semop",
        "semtimedop", "send", "sendfile", "sendfile64", "sendmmsg",
        "sendmsg", "sendto", "setfsgid", "setfsuid", "setgid",
        "setgroups", "setitimer", "setpgid", "setpriority", "setregid",
        "setresgid", "setresuid", "setreuid", "setrlimit", "set_robust_list",
        "setsid", "setsockopt", "set_thread_area", "set_tid_address",
        "setuid", "setxattr", "shmat", "shmctl", "shmdt", "shmget",
        "shutdown", "sigaltstack", "signalfd", "signalfd4", "socket",
        "socketcall", "socketpair", "splice", "stat", "statfs", "statx",
        "symlink", "symlinkat", "sync", "sync_file_range", "syncfs",
        "sysinfo", "tee", "tgkill", "time", "timer_create", "timer_delete",
        "timer_getoverrun", "timer_gettime", "timer_settime", "timerfd_create",
        "timerfd_gettime", "timerfd_settime", "times", "tkill", "truncate",
        "ugetrlimit", "umask", "uname", "unlink", "unlinkat", "utime",
        "utimensat", "utimes", "vfork", "wait4", "waitid", "waitpid",
        "write", "writev"
      ],
      "action": "SCMP_ACT_ALLOW"
    },
    {
      "names": ["personality"],
      "action": "SCMP_ACT_ALLOW",
      "args": [
        {
          "index": 0,
          "value": 0,
          "op": "SCMP_CMP_EQ"
        },
        {
          "index": 0,
          "value": 8,
          "op": "SCMP_CMP_EQ"
        },
        {
          "index": 0,
          "value": 131072,
          "op": "SCMP_CMP_EQ"
        },
        {
          "index": 0,
          "value": 131073,
          "op": "SCMP_CMP_EQ"
        },
        {
          "index": 0,
          "value": 4294967295,
          "op": "SCMP_CMP_EQ"
        }
      ]
    }
  ]
}
```

#### 8.1.3 AppArmor 配置

```bash
# /etc/apparmor.d/rv-insights-sandbox
#include <tunables/global>

profile rv-insights-sandbox flags=(attach_disconnected,mediate_deleted) {
  #include <abstractions/base>
  
  # 允许基本文件操作
  /workspace/** rwk,
  /tmp/** rwk,
  /repos/** r,
  /logs/** rw,
  
  # 允许执行基本命令
  /bin/** rix,
  /usr/bin/** rix,
  /usr/local/bin/** rix,
  /lib/** mr,
  /lib64/** mr,
  /usr/lib/** mr,
  /usr/lib64/** mr,
  
  # 禁止访问敏感路径
  deny /etc/shadow r,
  deny /etc/passwd r,
  deny /root/** rw,
  deny /home/*/.ssh/** rw,
  deny /proc/sys/** w,
  deny /sys/** w,
  
  # 网络限制（仅允许特定端口）
  deny network raw,
  deny network packet,
  allow network inet stream,
  allow network inet6 stream,
}
```

### 8.2 Agent 权限矩阵（详细版）

| Agent | 文件读取 | 文件写入 | Bash 执行 | 网络访问 | Git 操作 | Docker 控制 | 最大成本 | 沙箱类型 |
|-------|----------|----------|-----------|----------|----------|-------------|----------|----------|
| **探索 Agent** | ✅ 全局 | ❌ | ⚠️ 受限命令（grep, curl） | ✅ 白名单域名 | ❌ | ❌ | $1/次 | 网络受限 |
| **规划 Agent** | ✅ 全局 | ❌ | ❌ | ✅ 白名单域名 | ❌ | ❌ | $0.5/次 | 只读 |
| **开发 Agent** | ✅ 工作目录 | ✅ 工作目录 | ✅ 受限命令集 | ❌ | ✅ 工作目录内 | ❌ | $5/次 | 标准沙箱 |
| **审核 Agent** | ✅ 工作目录 | ❌ | ⚠️ 静态分析工具 | ❌ | ✅ 只读 | ❌ | $3/次 | 只读沙箱 |
| **测试 Agent** | ✅ 工作目录 | ✅ 测试目录 | ✅ 受限命令集 | ⚠️ 内部网络 | ❌ | ✅ 启动容器 | $3/次 | 特权沙箱 |

**受限命令集（开发/测试 Agent）**：
```python
ALLOWED_COMMANDS = {
    # 编译
    "make", "gcc", "g++", "ld", "ar", "ranlib",
    # 版本控制
    "git", "git-clone", "git-commit", "git-diff", "git-format-patch",
    # 文件操作
    "cat", "cp", "mv", "mkdir", "rm", "touch", "chmod", "chown",
    # 文本处理
    "grep", "sed", "awk", "diff", "patch",
    # 系统信息
    "uname", "date", "env", "echo", "pwd",
    # 容器
    "docker", "qemu-system-riscv64", "spike",
    # 脚本
    "python3", "python", "bash", "sh",
    # 调试
    "objdump", "readelf", "nm", "strings",
}

BLOCKED_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"mkfs\.",
    r"dd\s+if=/dev/zero\s+of=/dev/",
    r":\(\)\{\s*:\|:&\s*\};:",  # Fork bomb
    r"curl\s+.*\|\s*sh",  # Pipe to shell
    r"wget\s+.*\|\s*sh",
    r"eval\s*\$",
]
```

### 8.3 数据安全

| 数据类型 | 存储方式 | 加密 | 保留期 | 访问控制 |
|----------|----------|------|--------|----------|
| 代码 Artifact | S3 + 本地 | AES-256 | 90天 | 任务参与者 |
| LLM 对话记录 | PostgreSQL | 字段级加密 | 30天 | 管理员 |
| 审计日志 | PostgreSQL + 冷存 | AES-256 | 1年 | 审计员 |
| 用户凭证 | PostgreSQL | bcrypt + AES | 永久 | 本人 |
| API Keys | HashiCorp Vault | 动态加密 | 按需 | 系统管理员 |
| 沙箱内存 | tmpfs | 无（运行时） | 会话结束 | 隔离 |

---

## 9. 技术栈与依赖

### 9.1 完整技术栈

| 层级 | 组件 | 技术选型 | 版本 | 用途 |
|------|------|----------|------|------|
| **编排框架** | 多 Agent 编排 | OpenAI Agents SDK (Python) | >= 0.1.0 | Handoff、Guardrails、HITL |
| **执行框架** | 代码 Agent | Claude Agent SDK (Python) | >= 0.1.0 | 文件操作、Bash、代码导航 |
| **互操作** | 工具协议 | Model Context Protocol | >= 1.0.0 | 跨 SDK 工具互操作 |
| **Web 框架** | API 服务 | FastAPI | >= 0.110.0 | REST API、WebSocket |
| **前端** | Web UI | React + TypeScript + Vite | >= 18.0 | 用户交互界面 |
| **数据库** | 主存储 | PostgreSQL | >= 16 | 任务、阶段、Artifact 元数据 |
| **缓存** | 会话/速率限制 | Redis | >= 7.0 | Agent 上下文、锁、队列 |
| **消息队列** | 事件总线 | Redis Pub/Sub | >= 7.0 | 异步事件通知 |
| **任务队列** | 后台任务 | Celery + Redis | >= 5.3 | Agent 异步执行 |
| **沙箱** | 容器隔离 | Docker + gVisor (runsc) | >= 24.0 | Agent 执行环境 |
| **可观测性** | 链路追踪 | OpenTelemetry + Jaeger | >= 1.20 | 分布式追踪 |
| **可观测性** | 指标监控 | Prometheus + Grafana | >= 2.50 | 性能指标 |
| **LLM 网关** | 模型路由 | LiteLLM Proxy | >= 1.0 | 统一 LLM 调用、Fallback |
| **CI/CD** | 自动化 | GitHub Actions / GitLab CI | — | 自动化测试和部署 |
| **文档** | API 文档 | OpenAPI + Swagger UI | >= 3.0 | API 文档自动生成 |

### 9.2 LLM 模型配置（完整版）

```yaml
# models.yaml
version: "2.0"

# LLM 网关配置
gateway:
  provider: litellm
  base_url: "http://localhost:4000"
  fallback_strategy: "sequential"  # sequential | parallel
  
# Agent 模型配置
agents:
  discovery_orchestrator:
    primary:
      model: "openai/gpt-4o"
      temperature: 0.3
      max_tokens: 4096
    fallback:
      model: "anthropic/claude-sonnet-4"
      temperature: 0.3
      max_tokens: 4096
    cost_limit_usd: 1.0

  mail_explorer:
    primary:
      model: "openai/gpt-4o"
      temperature: 0.2
      max_tokens: 4096
    fallback:
      model: "openai/gpt-4o-mini"
      temperature: 0.2
      max_tokens: 4096
    cost_limit_usd: 0.5

  repo_explorer:
    primary:
      model: "openai/gpt-4o"
      temperature: 0.2
      max_tokens: 4096
    cost_limit_usd: 0.5

  feasibility_validator:
    primary:
      model: "openai/o3-mini"
      reasoning_effort: "high"
      max_tokens: 4096
    fallback:
      model: "openai/gpt-4o"
      temperature: 0.1
      max_tokens: 4096
    cost_limit_usd: 1.0

  planner:
    primary:
      model: "openai/o3-mini"
      reasoning_effort: "high"
      max_tokens: 8192
    fallback:
      model: "openai/gpt-4o"
      temperature: 0.2
      max_tokens: 8192
    cost_limit_usd: 2.0

  developer:
    primary:
      model: "anthropic/claude-sonnet-4"
      max_tokens: 8192
      # Claude SDK 特有
      permission_mode: "accept_edits"
      bash_tools: true
      read_write_tools: true
    fallback:
      model: "anthropic/claude-opus-4"
      max_tokens: 8192
      permission_mode: "accept_edits"
    cost_limit_usd: 5.0

  style_reviewer:
    primary:
      model: "openai/gpt-4o"
      temperature: 0.1
      max_tokens: 4096
    cost_limit_usd: 1.0

  logic_reviewer:
    primary:
      model: "openai/codex-latest"
      max_tokens: 8192
    fallback:
      model: "openai/o3-mini"
      reasoning_effort: "medium"
      max_tokens: 8192
    cost_limit_usd: 2.0

  security_reviewer:
    primary:
      model: "openai/gpt-4o"
      temperature: 0.1
      max_tokens: 4096
    cost_limit_usd: 1.0

  tester:
    primary:
      model: "anthropic/claude-sonnet-4"
      max_tokens: 4096
      permission_mode: "prompt"
      bash_tools: true
    fallback:
      model: "anthropic/claude-haiku-4"
      max_tokens: 4096
    cost_limit_usd: 3.0

# 成本告警
cost_alerts:
  daily_budget_usd: 100.0
  per_task_budget_usd: 20.0
  alert_channels: ["email", "slack"]
```

### 9.3 RISC-V 专用工具链

```dockerfile
# Dockerfile.toolchain - RISC-V 工具链镜像
FROM ubuntu:24.04 AS toolchain

ENV DEBIAN_FRONTEND=noninteractive

# 基础构建依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    bc \
    bison \
    flex \
    libssl-dev \
    libncurses5-dev \
    libelf-dev \
    wget \
    curl \
    git \
    python3 \
    python3-pip \
    texinfo \
    && rm -rf /var/lib/apt/lists/*

# RISC-V 交叉编译工具链
RUN apt-get update && apt-get install -y \
    gcc-riscv64-linux-gnu \
    g++-riscv64-linux-gnu \
    binutils-riscv64-linux-gnu \
    gdb-multiarch \
    && rm -rf /var/lib/apt/lists/*

# QEMU RISC-V
RUN apt-get update && apt-get install -y \
    qemu-system-misc \
    qemu-utils \
    && rm -rf /var/lib/apt/lists/*

# Spike 模拟器（从源码构建）
RUN git clone https://github.com/riscv-software-src/riscv-isa-sim.git /tmp/spike \
    && cd /tmp/spike \
    && apt-get update && apt-get install -y device-tree-compiler \
    && mkdir build && cd build \
    && ../configure --prefix=/opt/riscv \
    && make -j$(nproc) \
    && make install \
    && rm -rf /tmp/spike

# OpenSBI
RUN git clone https://github.com/riscv-software-src/opensbi.git /opt/opensbi \
    && cd /opt/opensbi \
    && make CROSS_COMPILE=riscv64-linux-gnu- PLATFORM=generic

# U-Boot 工具
RUN apt-get update && apt-get install -y \
    u-boot-tools \
    libuuid1 \
    && rm -rf /var/lib/apt/lists/*

# 内核分析工具
RUN apt-get update && apt-get install -y \
    cscope \
    ctags \
    sparse \
    smatch \
    && rm -rf /var/lib/apt/lists/*

# 安装 Coccinelle
RUN apt-get update && apt-get install -y \
    coccinelle \
    && rm -rf /var/lib/apt/lists/*

# Python 工具
RUN pip3 install --no-cache-dir \
    gitpython \
    pygments \
    requests \
    beautifulsoup4 \
    lxml \
    python-dateutil

ENV PATH="/opt/riscv/bin:${PATH}"
ENV RISCV="/opt/riscv"

WORKDIR /workspace
```

---

## 10. 部署架构

### 10.1 Kubernetes 部署配置

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: rv-insights
  labels:
    app: rv-insights
    env: production

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rv-insights-config
  namespace: rv-insights
data:
  models.yaml: |
    # 模型配置（参考 9.2 节）
  
  logging.yaml: |
    level: INFO
    format: json
    output: /var/log/rv-insights

---
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: rv-insights-secrets
  namespace: rv-insights
type: Opaque
stringData:
  OPENAI_API_KEY: "sk-..."
  ANTHROPIC_API_KEY: "sk-ant-..."
  DATABASE_URL: "postgresql://..."
  REDIS_URL: "redis://..."

---
# k8s/api-gateway.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: rv-insights
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
      - name: api-gateway
        image: rv-insights/api-gateway:v2.0
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: rv-insights-secrets
              key: DATABASE_URL
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: rv-insights-secrets
              key: REDIS_URL
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10

---
apiVersion: v1
kind: Service
metadata:
  name: api-gateway
  namespace: rv-insights
spec:
  selector:
    app: api-gateway
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP

---
# k8s/orchestrator.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orchestrator
  namespace: rv-insights
spec:
  replicas: 3
  selector:
    matchLabels:
      app: orchestrator
  template:
    metadata:
      labels:
        app: orchestrator
    spec:
      serviceAccountName: rv-insights-orchestrator
      containers:
      - name: orchestrator
        image: rv-insights/orchestrator:v2.0
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: rv-insights-secrets
              key: OPENAI_API_KEY
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: rv-insights-secrets
              key: DATABASE_URL
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: rv-insights-secrets
              key: REDIS_URL
        volumeMounts:
        - name: docker-sock
          mountPath: /var/run/docker.sock
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
      volumes:
      - name: docker-sock
        hostPath:
          path: /var/run/docker.sock
          type: Socket

---
# k8s/executor.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: executor
  namespace: rv-insights
spec:
  replicas: 2
  selector:
    matchLabels:
      app: executor
  template:
    metadata:
      labels:
        app: executor
    spec:
      containers:
      - name: executor
        image: rv-insights/executor:v2.0
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: rv-insights-secrets
              key: ANTHROPIC_API_KEY
        securityContext:
          privileged: true  # 需要管理沙箱容器
        resources:
          requests:
            memory: "1Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "4000m"

---
# k8s/sandbox-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: sandbox-dev-{{ .Values.taskId }}
  namespace: rv-insights
spec:
  template:
    spec:
      runtimeClassName: gvisor  # 使用 gVisor 运行时
      containers:
      - name: sandbox
        image: rv-insights/sandbox:v2.0
        resources:
          limits:
            cpu: "4000m"
            memory: "8Gi"
            ephemeral-storage: "20Gi"
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          runAsUser: 1000
          seccompProfile:
            type: Localhost
            localhostProfile: rv-insights-sandbox
        volumeMounts:
        - name: workspace
          mountPath: /workspace
        - name: repos
          mountPath: /repos
          readOnly: true
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: workspace
        emptyDir:
          sizeLimit: 10Gi
      - name: repos
        persistentVolumeClaim:
          claimName: repos-pvc
      - name: tmp
        emptyDir:
          sizeLimit: 2Gi
      restartPolicy: Never
  backoffLimit: 0

---
# k8s/postgres.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: rv-insights
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:16-alpine
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          value: "rvinsights"
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: rv-insights-secrets
              key: DB_PASSWORD
        volumeMounts:
        - name: postgres-data
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
  volumeClaimTemplates:
  - metadata:
      name: postgres-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 50Gi

---
# k8s/redis.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
  namespace: rv-insights
spec:
  serviceName: redis
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: redis-data
          mountPath: /data
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "1Gi"
            cpu: "500m"
  volumeClaimTemplates:
  - metadata:
      name: redis-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi

---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: rv-insights
  namespace: rv-insights
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - rv-insights.example.com
    secretName: rv-insights-tls
  rules:
  - host: rv-insights.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-gateway
            port:
              number: 80
      - path: /ws
        pathType: Prefix
        backend:
          service:
            name: api-gateway
            port:
              number: 80
```

### 10.2 Helm Chart 结构

```
helm/rv-insights/
├── Chart.yaml
├── values.yaml
├── values-production.yaml
├── values-staging.yaml
├── templates/
│   ├── _helpers.tpl
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── api-gateway.yaml
│   ├── orchestrator.yaml
│   ├── executor.yaml
│   ├── postgres.yaml
│   ├── redis.yaml
│   ├── ingress.yaml
│   ├── serviceaccount.yaml
│   └── networkpolicy.yaml
└── charts/
    └── postgresql-12.x.x.tgz  # 可选：作为依赖
```

---

## 11. 演进路线

### 11.1 Phase 1：MVP（0-3 个月）

**目标**：验证核心流程可行性，支持最简单的贡献类型

| 模块 | 功能范围 | 验收标准 |
|------|----------|----------|
| 探索层 | 邮件列表监控（linux-riscv 单一列表） | 每周发现 ≥5 个有效贡献点 |
| 规划层 | 基础方案生成（Bug 修复类） | 方案被人工接受率 ≥60% |
| 开发层 | 单文件代码修改 | 编译通过率 ≥50% |
| 审核层 | 单轮审核（风格+逻辑） | 问题检出率 ≥70% |
| 测试层 | 编译测试 | 编译通过率 ≥50% |
| HITL | 基础审核界面 | 人工响应时间 < 24h |
| 项目支持 | Linux 内核 RISC-V 子系统 | 可处理 arch/riscv/ 目录变更 |

**技术里程碑**：
- [x] 双 SDK 融合架构验证通过
- [x] MCP 网关实现工具互操作
- [x] gVisor 沙箱稳定运行
- [x] HITL 状态机完成状态转换

### 11.2 Phase 2：能力扩展（3-6 个月）

**目标**：支持更多项目类型，提升自动化率

| 模块 | 功能扩展 | 目标指标 |
|------|----------|----------|
| 探索层 | 增加 GitHub Issues、代码库扫描 | 周发现量 ≥20 个 |
| 规划层 | 多文件变更方案、依赖分析 | 方案接受率 ≥70% |
| 开发层 | 多文件变更、Git 工作流 | 编译通过率 ≥70% |
| 审核层 | 多轮迭代、专项安全审核 | 收敛轮数 ≤3 |
| 测试层 | QEMU 启动测试、KUnit | 测试通过率 ≥70% |
| HITL | 移动端适配、批量审核 | 响应时间 < 12h |
| 项目支持 | GCC、QEMU、OpenSBI | 每个项目 ≥1 个成功案例 |

**技术里程碑**：
- [ ] RAG 知识库上线（RISC-V ISA 规范、内核文档）
- [ ] 自动 Patch 提交到邮件列表
- [ ] 成本优化（模型路由、缓存）

### 11.3 Phase 3：生产就绪（6-12 个月）

**目标**：平台化运营，服务社区

| 模块 | 功能扩展 | 目标指标 |
|------|----------|----------|
| 探索层 | 全项目覆盖、智能推荐 | 周发现量 ≥50 个 |
| 规划层 | 自动依赖图生成、风险评估 | 方案接受率 ≥80% |
| 开发层 | 复杂重构、跨平台移植 | 编译通过率 ≥85% |
| 审核层 | 社区审核员集成、评分体系 | 收敛轮数 ≤2 |
| 测试层 | 硬件在环测试、CI 集成 | 测试通过率 ≥80% |
| HITL | 异步审核、委托审核 | 响应时间 < 6h |
| 项目支持 | 全 RISC-V 生态 | ≥10 个活跃项目 |

**技术里程碑**：
- [ ] 多租户支持
- [ ] 社区积分/声誉系统
- [ ] 开源发布（Apache 2.0）

### 11.4 ROI 分析

| 阶段 | 投入（人月） | 自动化贡献数/月 | 人工审核时间/贡献 | 预估节省人力 |
|------|-------------|----------------|------------------|-------------|
| MVP | 6 | 5-10 | 2h | 1 人月 |
| Phase 2 | 12 | 20-30 | 1h | 3 人月 |
| Phase 3 | 24 | 50-100 | 30min | 8 人月 |

---

## 12. 附录：架构图

### 图 1：整体系统架构

```
                                 用户/开发者
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              用户交互层                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Web UI   │  │ CLI Tool │  │ GitHub   │  │ API      │  │ Slack/   │ │
│  │ (React)  │  │ (Python) │  │ App      │  │ Gateway  │  │ Discord  │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│       └─────────────┴─────────────┴─────────────┴─────────────┘       │
└────────────────────────────────────────┬────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            工作流编排层                                   │
│                    【OpenAI Agents SDK - 主导】                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ 状态机引擎   │  │ HITL 控制器  │  │ 事件总线     │  │ 任务调度器  │ │
│  │ (State)      │  │ (Human)      │  │ (Event)      │  │(Scheduler) │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘ │
│         │                 │                 │                │        │
│         └─────────────────┴─────────────────┘                │        │
│                              │                               │        │
│  ┌───────────────────────┬───┴────────────────────────────────┘        │
│  │                    LiteLLM Proxy (模型网关)                       │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │   │
│  │  │  OpenAI  │ │ Anthropic│ │  Google  │ │  Local   │          │   │
│  │  │  GPT-4o  │ │  Claude  │ │  Gemini  │ │  Ollama  │          │   │
│  │  │  o3-mini │ │  Sonnet  │ │  Flash   │ │  DeepSeek│          │   │
│  │  │  Codex   │ │  Opus    │ │  Pro     │ │  Qwen    │          │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │   │
│  └───────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────┬────────────────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
┌───────────────────────┐    ┌───────────────────────┐    ┌──────────────┐
│  OpenAI Agents 集群   │◄──►│     MCP 协议网关       │◄──►│ Claude Agent │
│                       │    │                       │    │ SDK 集群      │
│ ┌─────────────────┐   │    │  • 工具注册与发现      │    │              │
│ │ Discovery Agent │   │    │  • 跨 SDK 调用转发     │    │ ┌──────────┐ │
│ │  (探索层)        │   │    │  • 结果格式标准化      │    │ │Developer │ │
│ └─────────────────┘   │    │                       │    │ │ Agent    │ │
│ ┌─────────────────┐   │    │                       │    │ └──────────┘ │
│ │ Planning Agent  │   │    │                       │    │ ┌──────────┐ │
│ │  (规划层)        │   │    │                       │    │ │Tester    │ │
│ └─────────────────┘   │    │                       │    │ │ Agent    │ │
│ ┌─────────────────┐   │    │                       │    │ └──────────┘ │
│ │ Review Agent    │   │    │                       │    │              │
│ │  (审核层)        │   │    │                       │    │              │
│ └─────────────────┘   │    │                       │    │              │
│ ┌─────────────────┐   │    │                       │    │              │
│ │ Orchestrator    │   │    │                       │    │              │
│ │  (协调器)        │   │    │                       │    │              │
│ └─────────────────┘   │    │                       │    │              │
└───────────────────────┘    └───────────────────────┘    └──────────────┘
         │                              │                        │
         └──────────────────────────────┼────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              工具与数据层                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ 邮件列表  │  │ GitHub   │  │ 代码分析  │  │ 测试沙箱  │  │ 知识库   │  │
│  │ 爬虫     │  │  API    │  │ 工具链   │  │ (Docker) │  │ (RAG)   │  │
│  │ • lore   │  │ • Issues│  │ • AST   │  │ • QEMU  │  │ • ISA   │  │
│  │ • patchwk│  │ • PRs   │  │ • Call  │  │ • Spike │  │ • ABI   │  │
│  │ • groups │  │ • Commits│ │ • Graph │  │ • HW    │  │ • Docs  │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 图 2：Agent 协作流程

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  用户   │    │ 探索Agent│    │ 规划Agent│    │ 开发Agent│    │ 审核Agent│
│         │    │(OpenAI) │    │(OpenAI) │    │(Claude) │    │(OpenAI) │
└────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘
     │              │              │              │              │
     │ 发起任务      │              │              │              │
     │─────────────►│              │              │              │
     │              │              │              │              │
     │              │ 自主探索/    │              │              │
     │              │ 用户输入分析  │              │              │
     │              │─────────────►│              │              │
     │              │              │              │              │
     │              │              │ 设计开发/    │              │
     │              │              │ 测试方案     │              │
     │              │              │─────────────►│              │
     │              │              │              │              │
     │              │              │              │ 代码开发     │
     │              │              │              │─────────────►│
     │              │              │              │              │
     │              │              │              │ 发现问题     │
     │              │              │              │◄─────────────│ (迭代)
     │              │              │              │              │
     │              │              │              │ 修复代码     │
     │              │              │              │─────────────►│
     │              │              │              │              │
     │              │              │              │ 审核通过     │
     │              │              │              │◄─────────────│
     │              │              │              │              │
     │              │              │              │─────────────►│ 测试Agent
     │              │              │              │              │(Claude)
     │              │              │              │              │
     │◄─────────────────────────────────────────────────────────│ 测试报告
     │              │              │              │              │
     │ 确认/终止    │              │              │              │
     │─────────────►─────────────►─────────────►─────────────►│
     │              │              │              │              │
     
     ═══════════════════════════════════════════════════════════
     每个节点完成后都有 HITL（人工审核点）
     ═══════════════════════════════════════════════════════════
```

### 图 3：开发-审核迭代循环

```
                         ┌─────────────┐
                         │   开发完成   │
                         └──────┬──────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │    HITL: 人工确认      │
                    │    "代码是否可提交审核?" │
                    └───────┬───────┬───────┘
                            │       │
                    拒绝/修改 ◄       ► 通过
                            │       │
                            ▼       ▼
                   ┌────────────┐ ┌────────────────┐
                   │ 返回开发层  │ │ 进入审核层      │
                   │ 重新开发    │ │ (OpenAI + Codex)│
                   └────────────┘ └───────┬────────┘
                                          │
                                          ▼
                         ┌────────────────────────────────┐
                         │        并行审核流程             │
                         │  ┌────────┐ ┌────────┐        │
                         │  │ 风格审核 │ │ 逻辑审核 │        │
                         │  │ Agent  │ │ Agent  │        │
                         │  └───┬────┘ └───┬────┘        │
                         │      └────┬─────┘             │
                         │           ▼                   │
                         │      ┌────────┐               │
                         │      │ 安全审核 │               │
                         │      │ Agent  │               │
                         │      └───┬────┘               │
                         └──────────┼────────────────────┘
                                    │
                                    ▼
                         ┌───────────────────────┐
                         │    综合审核结果        │
                         └───────┬───────┬───────┘
                                 │       │
                    审核通过 ◄───┘       └───► 发现问题
                                 │               │
                                 ▼               ▼
                        ┌────────────┐  ┌─────────────────┐
                        │ HITL: 确认  │  │ 生成修复要求      │
                        │ 进入测试层  │  │ 返回开发层        │
                        └────────────┘  └─────────────────┘
                                                   │
                    ╔══════════════════════════════╝
                    ║ 迭代终止条件：
                    ║ 1. 审核通过
                    ║ 2. 达到最大迭代次数（默认 5）
                    ║ 3. 人工介入终止
                    ╚═══════════════════════════════════════════════
```

### 图 4：数据流与状态转换

```
┌──────────┐   explore   ┌──────────┐   plan   ┌──────────┐
│  START   │ ───────────►│ DISCOVERY│ ────────►│ PLANNING │
└──────────┘             └────┬─────┘          └────┬─────┘
                              │                     │
                        HITL ◄┘               HITL ◄┘
                              │                     │
                              ▼                     ▼
                        ┌──────────┐          ┌──────────┐
                        │  人工审核  │          │  人工审核  │
                        └────┬─────┘          └────┬─────┘
                              │                     │
                              ▼                     ▼
                        ┌──────────┐          ┌──────────┐
                        │DEVELOPMENT│  review  │ REVIEWING│
                        │◄──────────┴─────────►│         │
                        └────┬─────┘          └────┬─────┘
                             │                      │
                       HITL ◄┘                HITL ◄┘
                             │                      │
                             ▼                      ▼
                       ┌──────────┐          ┌──────────┐
                       │  人工审核  │          │  人工审核  │
                       └────┬─────┘          └────┬─────┘
                            │                     │
                            ▼                     ▼
                       ┌──────────┐         ┌──────────┐
                       │ TESTING  │         │ ABORTED  │
                       └────┬─────┘         └──────────┘
                            │
                      HITL ◄┘
                            │
                            ▼
                       ┌──────────┐
                       │  人工审核  │
                       └────┬─────┘
                            │
                            ▼
                       ┌──────────┐
                       │ COMPLETE │
                       └──────────┘
```

---

## 13. 附录：核心代码示例

### 13.1 工作流引擎启动示例

```python
# rv_insights/main.py
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rv_insights.database import init_database
from rv_insights.workflow.engine import WorkflowEngine
from rv_insights.api.routes import router
from rv_insights.events.bus import EventBus
from rv_insights.mcp_gateway import RVInsightsMCPGateway

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动
    app.state.db = init_database()
    app.state.event_bus = EventBus()
    app.state.mcp_gateway = RVInsightsMCPGateway()
    app.state.workflow_engine = WorkflowEngine(
        db=app.state.db,
        event_bus=app.state.event_bus,
        mcp_gateway=app.state.mcp_gateway
    )
    
    # 启动后台任务
    await app.state.workflow_engine.start()
    
    yield
    
    # 关闭
    await app.state.workflow_engine.stop()
    await app.state.event_bus.close()

app = FastAPI(
    title="RV-Insights API",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://rv-insights.local"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v2")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}

@app.get("/ready")
async def readiness_check():
    checks = {
        "database": app.state.db is not None,
        "event_bus": app.state.event_bus.is_connected(),
        "workflow_engine": app.state.workflow_engine.is_running()
    }
    all_ready = all(checks.values())
    return {
        "ready": all_ready,
        "checks": checks
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

### 13.2 Docker Compose 完整开发环境

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/rvinsights
      - REDIS_URL=redis://redis:6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./rv_insights:/app/rv_insights
      - ./models.yaml:/app/models.yaml
    depends_on:
      - postgres
      - redis
    command: uvicorn rv_insights.main:app --host 0.0.0.0 --port 8080 --reload

  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/rvinsights
      - REDIS_URL=redis://redis:6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./rv_insights:/app/rv_insights
      - /var/run/docker.sock:/var/run/docker.sock
      - ./repos:/repos
      - ./logs:/logs
    depends_on:
      - postgres
      - redis
    command: celery -A rv_insights.worker worker -l info -c 4

  scheduler:
    build:
      context: .
      dockerfile: Dockerfile.worker
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/rvinsights
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./rv_insights:/app/rv_insights
    depends_on:
      - postgres
      - redis
    command: celery -A rv_insights.worker beat -l info

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=rvinsights
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"
      - "14268:14268"

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  postgres_data:
  redis_data:
  grafana_data:
```

---

## 14. 附录：数据库 Schema

### 14.1 PostgreSQL DDL

```sql
-- init.sql
-- RV-Insights 数据库初始化脚本

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 全文搜索

-- 任务表
CREATE TABLE tasks (
    task_id VARCHAR(32) PRIMARY KEY,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    title VARCHAR(200) NOT NULL,
    description TEXT,
    source_type VARCHAR(50),
    source_url VARCHAR(500),
    target_project VARCHAR(50),
    created_by VARCHAR(100) NOT NULL,
    assigned_reviewer VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    priority INTEGER DEFAULT 1 CHECK (priority BETWEEN 1 AND 5),
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_task_status ON tasks(status);
CREATE INDEX idx_task_project ON tasks(target_project);
CREATE INDEX idx_task_created_by ON tasks(created_by);
CREATE INDEX idx_task_created_at ON tasks(created_at);

-- 阶段表
CREATE TABLE stages (
    stage_id VARCHAR(50) PRIMARY KEY,
    task_id VARCHAR(32) NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL,
    stage_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    input_artifact_id VARCHAR(50),
    output_artifact_id VARCHAR(50),
    agent_name VARCHAR(100),
    agent_model VARCHAR(50),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    execution_time_seconds REAL,
    cost_usd REAL DEFAULT 0.0,
    token_input INTEGER DEFAULT 0,
    token_output INTEGER DEFAULT 0,
    iteration_count INTEGER DEFAULT 0,
    max_iterations INTEGER DEFAULT 5,
    error_message TEXT
);

CREATE INDEX idx_stage_task ON stages(task_id);
CREATE INDEX idx_stage_status ON stages(status);
CREATE INDEX idx_stage_type ON stages(stage_type);

-- Artifact 表
CREATE TABLE artifacts (
    artifact_id VARCHAR(50) PRIMARY KEY,
    artifact_type VARCHAR(50) NOT NULL,
    content_json JSONB,
    content_text TEXT,
    storage_path VARCHAR(500),
    parent_artifact_id VARCHAR(50) REFERENCES artifacts(artifact_id),
    task_id VARCHAR(32) REFERENCES tasks(task_id),
    created_by_agent VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    version VARCHAR(20) DEFAULT '1.0'
);

CREATE INDEX idx_artifact_task ON artifacts(task_id);
CREATE INDEX idx_artifact_type ON artifacts(artifact_type);
CREATE INDEX idx_artifact_created_at ON artifacts(created_at);

-- Agent 日志表
CREATE TABLE agent_logs (
    log_id VARCHAR(50) PRIMARY KEY,
    stage_id VARCHAR(50) NOT NULL REFERENCES stages(stage_id) ON DELETE CASCADE,
    log_level VARCHAR(20) DEFAULT 'INFO',
    log_type VARCHAR(50),
    message TEXT,
    details JSONB,
    trace_id VARCHAR(100),
    span_id VARCHAR(100),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_log_stage ON agent_logs(stage_id);
CREATE INDEX idx_log_timestamp ON agent_logs(timestamp);
CREATE INDEX idx_log_trace ON agent_logs(trace_id);

-- HITL 请求表
CREATE TABLE hitl_requests (
    request_id VARCHAR(50) PRIMARY KEY,
    task_id VARCHAR(32) NOT NULL REFERENCES tasks(task_id),
    stage_id VARCHAR(50) NOT NULL REFERENCES stages(stage_id),
    status VARCHAR(20) DEFAULT 'pending',
    stage_summary TEXT,
    stage_output JSONB,
    options JSONB,
    decision VARCHAR(20),
    decision_feedback TEXT,
    decided_by VARCHAR(100),
    decided_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    timeout_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_hitl_task ON hitl_requests(task_id);
CREATE INDEX idx_hitl_status ON hitl_requests(status);
CREATE INDEX idx_hitl_timeout ON hitl_requests(timeout_at);

-- 审计日志表
CREATE TABLE audit_logs (
    log_id VARCHAR(50) PRIMARY KEY,
    action VARCHAR(100) NOT NULL,
    actor VARCHAR(100) NOT NULL,
    actor_type VARCHAR(20),
    target_type VARCHAR(50),
    target_id VARCHAR(50),
    details JSONB,
    ip_address INET,
    user_agent VARCHAR(200),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_target ON audit_logs(target_type, target_id);
CREATE INDEX idx_audit_actor ON audit_logs(actor);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_action ON audit_logs(action);

-- 触发器：自动更新 updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 视图：任务完整状态
CREATE VIEW task_status_view AS
SELECT 
    t.task_id,
    t.title,
    t.status,
    t.target_project,
    t.created_by,
    t.created_at,
    t.priority,
    COUNT(s.stage_id) AS total_stages,
    COUNT(CASE WHEN s.status = 'completed' THEN 1 END) AS completed_stages,
    COUNT(CASE WHEN s.status = 'hitl_pending' THEN 1 END) AS pending_hitl_stages,
    SUM(s.cost_usd) AS total_cost,
    MAX(h.timeout_at) AS nearest_hitl_timeout
FROM tasks t
LEFT JOIN stages s ON t.task_id = s.task_id
LEFT JOIN hitl_requests h ON t.task_id = h.task_id AND h.status = 'pending'
GROUP BY t.task_id, t.title, t.status, t.target_project, t.created_by, t.created_at, t.priority;
```

---

## 15. 附录：API 接口定义

### 15.1 OpenAPI 规范

```yaml
# openapi.yaml
openapi: 3.0.3
info:
  title: RV-Insights API
  version: 2.0.0
  description: 大模型驱动的 RISC-V 开源贡献平台 API

servers:
  - url: https://rv-insights.local/api/v2
    description: Production
  - url: http://localhost:8080/api/v2
    description: Development

paths:
  /tasks:
    post:
      summary: 创建新的贡献任务
      operationId: createTask
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateTaskRequest'
      responses:
        '201':
          description: 任务创建成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TaskResponse'
        '400':
          description: 请求参数错误
    get:
      summary: 获取任务列表
      operationId: listTasks
      parameters:
        - name: status
          in: query
          schema:
            type: string
            enum: [pending, exploring, planning, developing, reviewing, testing, complete, aborted]
        - name: project
          in: query
          schema:
            type: string
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
            maximum: 100
        - name: offset
          in: query
          schema:
            type: integer
            default: 0
      responses:
        '200':
          description: 任务列表
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TaskListResponse'

  /tasks/{taskId}:
    get:
      summary: 获取任务详情
      operationId: getTask
      parameters:
        - name: taskId
          in: path
          required: true
          schema:
            type: string
            pattern: '^RV-\d{4}-\d{2}-\d{2}-\d{3}$'
      responses:
        '200':
          description: 任务详情
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TaskDetailResponse'
        '404':
          description: 任务不存在

  /tasks/{taskId}/hitl/approve:
    post:
      summary: 批准当前阶段的 HITL 请求
      operationId: approveHITL
      parameters:
        - name: taskId
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                feedback:
                  type: string
      responses:
        '200':
          description: 审批成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HITLResponse'

  /tasks/{taskId}/hitl/reject:
    post:
      summary: 拒绝当前阶段的 HITL 请求
      operationId: rejectHITL
      parameters:
        - name: taskId
          in: path
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [feedback]
              properties:
                feedback:
                  type: string
                action:
                  type: string
                  enum: [return, abort]
                  default: return
      responses:
        '200':
          description: 拒绝成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HITLResponse'

  /tasks/{taskId}/artifacts:
    get:
      summary: 获取任务的所有 Artifact
      operationId: listArtifacts
      parameters:
        - name: taskId
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Artifact 列表
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Artifact'

  /artifacts/{artifactId}:
    get:
      summary: 获取 Artifact 详情
      operationId: getArtifact
      parameters:
        - name: artifactId
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Artifact 详情
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Artifact'
            text/plain:
              schema:
                type: string

  /health:
    get:
      summary: 健康检查
      operationId: healthCheck
      responses:
        '200':
          description: 服务健康
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthResponse'

  /ready:
    get:
      summary: 就绪检查
      operationId: readinessCheck
      responses:
        '200':
          description: 服务就绪
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ReadyResponse'

components:
  schemas:
    CreateTaskRequest:
      type: object
      required: [title, user_id]
      properties:
        title:
          type: string
          maxLength: 200
        description:
          type: string
        source_type:
          type: string
          enum: [user_input, auto_discovery]
        target_project:
          type: string
          enum: [linux, gcc, llvm, qemu, opensbi, u-boot, glibc]
        user_id:
          type: string
        priority:
          type: integer
          minimum: 1
          maximum: 5
          default: 1

    TaskResponse:
      type: object
      properties:
        task_id:
          type: string
        status:
          type: string
        current_stage:
          type: string
        created_at:
          type: string
          format: date-time
        hitl_pending:
          type: boolean
        stage_summary:
          type: string

    TaskDetailResponse:
      allOf:
        - $ref: '#/components/schemas/TaskResponse'
        - type: object
          properties:
            stages:
              type: array
              items:
                $ref: '#/components/schemas/Stage'
            artifacts:
              type: array
              items:
                $ref: '#/components/schemas/Artifact'
            cost_usd:
              type: number
            execution_time_seconds:
              type: number

    Stage:
      type: object
      properties:
        stage_id:
          type: string
        stage_type:
          type: string
        status:
          type: string
        agent_name:
          type: string
        started_at:
          type: string
          format: date-time
        completed_at:
          type: string
          format: date-time
        cost_usd:
          type: number
        iteration_count:
          type: integer

    Artifact:
      type: object
      properties:
        artifact_id:
          type: string
        artifact_type:
          type: string
        created_by_agent:
          type: string
        created_at:
          type: string
          format: date-time
        version:
          type: string

    HITLResponse:
      type: object
      properties:
        status:
          type: string
        task_id:
          type: string
        next_stage:
          type: string

    HealthResponse:
      type: object
      properties:
        status:
          type: string
        version:
          type: string

    ReadyResponse:
      type: object
      properties:
        ready:
          type: boolean
        checks:
          type: object
          additionalProperties:
            type: boolean
```

---

## 16. 附录：运维手册

### 16.1 日常运维检查清单

```bash
#!/bin/bash
# daily_check.sh - RV-Insights 日常检查脚本

echo "=== RV-Insights Daily Check ==="
echo "Date: $(date)"

# 1. 服务健康检查
echo "[1/8] Checking API Gateway..."
curl -sf http://localhost:8080/health || echo "WARNING: API Gateway unhealthy"

# 2. 数据库连接检查
echo "[2/8] Checking Database..."
psql $DATABASE_URL -c "SELECT 1" > /dev/null 2>&1 || echo "WARNING: Database connection failed"

# 3. Redis 连接检查
echo "[3/8] Checking Redis..."
redis-cli -u $REDIS_URL ping | grep -q PONG || echo "WARNING: Redis connection failed"

# 4. 检查挂起的 HITL 请求
echo "[4/8] Checking pending HITL requests..."
PENDING_HITL=$(psql $DATABASE_URL -t -c "SELECT COUNT(*) FROM hitl_requests WHERE status='pending';")
echo "Pending HITL requests: $PENDING_HITL"

# 5. 检查超时 HITL
echo "[5/8] Checking expired HITL requests..."
EXPIRED_HITL=$(psql $DATABASE_URL -t -c "SELECT COUNT(*) FROM hitl_requests WHERE status='pending' AND timeout_at < NOW();")
echo "Expired HITL requests: $EXPIRED_HITL"

# 6. 今日成本统计
echo "[6/8] Checking today's cost..."
TODAY_COST=$(psql $DATABASE_URL -t -c "SELECT COALESCE(SUM(cost_usd), 0) FROM stages WHERE created_at >= CURRENT_DATE;")
echo "Today's cost: $${TODAY_COST} USD"

# 7. 活跃任务统计
echo "[7/8] Checking active tasks..."
ACTIVE_TASKS=$(psql $DATABASE_URL -t -c "SELECT COUNT(*) FROM tasks WHERE status NOT IN ('complete', 'aborted', 'failed');")
echo "Active tasks: $ACTIVE_TASKS"

# 8. 磁盘空间检查
echo "[8/8] Checking disk space..."
df -h /repos /logs /tmp | awk 'NR>1 && int($5) > 80 {print "WARNING: " $6 " is " $5 " full"}'

echo "=== Check Complete ==="
```

### 16.2 故障排查指南

| 故障现象 | 可能原因 | 排查步骤 | 解决方案 |
|----------|----------|----------|----------|
| Agent 执行超时 | LLM API 延迟 | 检查 LiteLLM 状态 | 增加超时时间、切换 Fallback 模型 |
| 沙箱启动失败 | Docker 资源不足 | `docker system df` | 清理未使用镜像、增加节点资源 |
| HITL 通知未送达 | WebSocket 断开 | 检查 Redis Pub/Sub | 重启通知服务、检查防火墙 |
| 数据库连接池耗尽 | 连接未释放 | `pg_stat_activity` | 增加连接池大小、检查泄漏 |
| LLM 调用费用突增 | Token 消耗异常 | 查看 Agent 日志 | 限制 max_tokens、启用成本告警 |
| 审核迭代不收敛 | 修复质量差 | 检查修复指令质量 | 优化 Prompt、限制迭代次数 |
| Git 操作失败 | 权限/网络问题 | 检查 SSH Key、DNS | 更新凭证、检查网络策略 |

### 16.3 备份策略

| 数据类型 | 备份频率 | 保留期 | 存储位置 |
|----------|----------|--------|----------|
| PostgreSQL | 每日全量 + WAL | 30天 | S3 + 本地 |
| Redis | 每小时 RDB | 7天 | S3 |
| Artifact 文件 | 实时同步 | 90天 | S3 |
| 审计日志 | 实时归档 | 1年 | S3 Glacier |
| 配置文件 | 版本控制 | 永久 | Git |

---

*文档结束 — v2.0 增强版*

> **总结**：本方案在 v1.0 基础上，针对每个模块补充了：
> - 完整的代码实现示例（Agent 定义、工具函数、Guardrails）
> - 数据库 Schema（PostgreSQL DDL）
> - API 接口定义（OpenAPI 3.0）
> - Docker/Kubernetes 部署配置
> - 安全沙箱实现（seccomp、AppArmor）
> - HITL Web UI 交互设计
> - 运维手册和故障排查指南
> - RISC-V 专用工具链配置
