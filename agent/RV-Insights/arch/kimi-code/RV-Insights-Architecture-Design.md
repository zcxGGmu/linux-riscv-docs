# RV-Insights：大模型驱动的 RISC-V 开源贡献平台

## 项目设计方案 v1.0

> **版本**：v1.0  
> **日期**：2026-04-23  
> **目标**：面向 RISC-V 开源软件生态，构建由大模型驱动的多 Agent 自动化贡献平台，实现从探索、规划、开发、审核到测试的完整开源贡献流水线。

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

---

## 1. 项目背景与目标

### 1.1 背景

RISC-V 作为开放指令集架构（ISA），其开源软件生态（包括 Linux 内核、GCC、LLVM、QEMU、OpenSBI 等）正在快速发展。然而，对 RISC-V 生态做出贡献存在以下挑战：

- **信息分散**：贡献机会散落在邮件列表、GitHub Issues、Patchwork 等多个渠道
- **门槛较高**：需要深入理解 RISC-V 架构规范、ABI 约定、内核子系统等专业知识
- **流程复杂**：从发现问题到提交 Patch，涉及探索、验证、编码、测试等多个环节
- **审核资源有限**：核心维护者时间宝贵，大量初级贡献因质量不足被退回

### 1.2 目标

构建 **RV-Insights** 平台，利用大模型驱动的多 Agent 系统，实现：

1. **自主探索**：持续监控 RISC-V 相关渠道，自动识别可行的贡献点
2. **智能规划**：为每个贡献点生成完整的开发和测试方案
3. **自动开发**：基于规划自动进行代码开发
4. **迭代审核**：开发-审核多轮迭代，确保代码质量
5. **自动验证**：搭建测试环境并执行验证
6. **人机协同**：每个关键节点接受人工审核，确保最终输出质量

---

## 2. 核心设计原则

| 原则 | 说明 |
|------|------|
| **分而治之** | 每个 Agent 专注于单一职责，通过清晰接口协作 |
| **人机协同** | 人工在每个阶段拥有最终决定权，Agent 提供辅助决策 |
| **可观测性** | 全流程可追踪、可审计、可回放 |
| **安全优先** | Agent 操作受限于沙箱环境，关键操作需审批 |
| **模型无关** | 架构层不绑定特定模型，支持灵活切换和 A/B 测试 |
| **渐进交付** | 支持从简单任务到复杂任务的渐进式能力扩展 |

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
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                  工作流编排层 (Workflow Orchestration)                 │   │
│  │                     【OpenAI Agents SDK 主导】                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │   │
│  │  │ 状态机引擎   │  │  HITL 控制器 │  │  事件总线    │  │ 调度器     │  │   │
│  │  │  (State)    │  │  (Human)    │  │  (Event)    │  │(Scheduler)│  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Agent 执行层 (Agent Execution Layer)               │   │
│  │                                                                     │   │
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────┐  │   │
│  │  │  OpenAI Agents   │◄──►│   MCP 协议网关    │◄──►│Claude Agent  │  │   │
│  │  │     集群         │    │  (互操作层)       │    │    SDK       │  │   │
│  │  │                  │    │                  │    │              │  │   │
│  │  │ • Discovery      │    │                  │    │ • Developer  │  │   │
│  │  │ • Planner        │    │                  │    │ • Tester     │  │   │
│  │  │ • Reviewer       │    │                  │    │              │  │   │
│  │  │ • Orchestrator   │    │                  │    │              │  │   │
│  │  └──────────────────┘    └──────────────────┘    └──────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    工具与数据层 (Tools & Data Layer)                  │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │ 邮件列表  │ │ GitHub   │ │ 代码分析  │ │ 测试环境  │ │ 知识库   │  │   │
│  │  │ 爬虫     │ │  API    │ │ 工具链   │ │ 沙箱    │ │ (RAG)   │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 五层架构说明

| 层级 | 名称 | 职责 | 主导 SDK |
|------|------|------|----------|
| L1 | 用户交互层 | 提供 Web UI、CLI、API 等交互入口 | — |
| L2 | 工作流编排层 | 状态机驱动、HITL 控制、事件调度 | OpenAI Agents SDK |
| L3 | Agent 执行层 | 具体 Agent 的执行逻辑与协作 | 双 SDK 融合 |
| L4 | MCP 协议网关 | 两个 SDK 生态的工具互操作 | MCP Protocol |
| L5 | 工具与数据层 | 外部工具、数据源、沙箱环境 | — |

---

## 4. 智能体节点详细设计

### 4.1 探索层（Discovery Agent）

#### 4.1.1 职责定义

- **自主探索**：持续监控 RISC-V 邮件列表（如 `linux-riscv`、`qemu-riscv` 等）、GitHub Issues、Patchwork
- **用户输入处理**：接收用户给定的方向或问题，分析可行性
- **可行性验证**：对发现的贡献点进行初步验证（如是否能复现问题、是否已有 PR 等）
- **输出结构化报告**：包含问题描述、复现步骤、预期贡献方向、参考资源

#### 4.1.2 子 Agent 设计（OpenAI Agents SDK）

```python
# 探索层 Agent 集群定义
from agents import Agent, Runner, function_tool, guardrail

# 1. 邮件列表探索 Agent
mail_explorer = Agent(
    name="MailExplorer",
    instructions="""
    你是一个 RISC-V 开源社区邮件列表分析专家。
    你的任务是分析指定的 RISC-V 相关邮件列表，识别以下类型的贡献机会：
    - 未被修复的 Bug 报告
    - 功能请求（Feature Request）
    - 性能优化线索
    - 文档改进建议
    - 测试覆盖不足的模块
    
    对每个发现的贡献点，你需要：
    1. 提取问题的核心描述
    2. 判断问题的技术领域（内核/工具链/QEMU/文档等）
    3. 评估问题的难度等级（初/中/高级）
    4. 验证是否已有相关 Patch 或 PR
    5. 输出结构化的贡献机会报告
    """,
    model="gpt-4o",
    tools=[fetch_mail_list, search_mail_archive, extract_patch_links],
    handoff_description="当需要从邮件列表中发现贡献机会时使用"
)

# 2. 代码库探索 Agent
repo_explorer = Agent(
    name="RepoExplorer",
    instructions="""
    你是一个 RISC-V 代码库分析专家，擅长 Linux 内核、GCC、LLVM、QEMU 等项目的代码结构分析。
    你的任务是探索代码库，发现以下类型的贡献机会：
    - TODO/FIXME 注释标记的未完成工作
    - 代码风格不一致或需要重构的模块
    - 缺少错误处理的代码路径
    - 未实现的 RISC-V 特性（对照 RISC-V ISA 规范）
    - 测试用例覆盖盲区
    
    你需要结合 RISC-V ISA 规范和代码库的实际状态进行交叉分析。
    """,
    model="gpt-4o",
    tools=[search_codebase, analyze_git_log, check_todo_comments, 
           compare_with_isa_spec, check_test_coverage],
    handoff_description="当需要从代码库中发现贡献机会时使用"
)

# 3. 可行性验证 Agent
feasibility_validator = Agent(
    name="FeasibilityValidator",
    instructions="""
    你是一个技术可行性分析专家。
    你的任务是对发现的贡献点进行初步可行性验证：
    - 检查问题是否已有解决方案（避免重复劳动）
    - 评估问题的边界清晰度
    - 判断是否具备足够的技术资料支持开发
    - 评估预期工作量
    - 给出 Go / No-Go 建议
    """,
    model="o3-mini",  # 使用推理模型进行深度分析
    tools=[search_existing_patches, check_issue_status, estimate_effort],
    handoff_description="当需要对贡献点进行可行性验证时使用"
)

# 4. 探索协调 Agent（入口点）
discovery_orchestrator = Agent(
    name="DiscoveryOrchestrator",
    instructions="""
    你是 RV-Insights 探索层的协调者。
    你的任务是根据用户输入或自主触发条件，决定探索策略：
    - 如果用户指定了具体方向，路由到对应的探索 Agent
    - 如果需要全面扫描，并行启动多个探索 Agent
    - 收集所有探索结果后，统一调用可行性验证 Agent
    - 输出最终的探索报告
    """,
    model="gpt-4o",
    handoffs=[mail_explorer, repo_explorer, feasibility_validator]
)
```

#### 4.1.3 为什么使用 OpenAI Agents SDK

| 特性 | 在探索层的价值 |
|------|--------------|
| **Handoff 机制** | 邮件列表探索、代码库探索、可行性验证三个 Agent 之间的任务交接非常自然，由协调 Agent 统一调度 |
| **Guardrails** | 输入护栏防止探索偏离 RISC-V 领域；输出护栏确保报告格式统一、信息完整 |
| **Tracing** | 完整记录探索过程，便于人工审核时了解 Agent 的思考路径和决策依据 |
| **Web Search 工具** | 内置 Web Search 能力，方便搜索 RISC-V 规范、社区讨论等外部信息 |
| **模型兼容性** | 可根据任务复杂度灵活选择 GPT-4o 或 o3-mini |

#### 4.1.4 输出格式

```json
{
  "discovery_report": {
    "contribution_id": "RV-2026-0423-001",
    "title": "RISC-V 内核: 修复 hartid 越界访问问题",
    "source": {
      "type": "mail_list",
      "url": "https://lore.kernel.org/linux-riscv/...",
      "date": "2026-04-20"
    },
    "category": "linux_kernel",
    "difficulty": "intermediate",
    "description": "在 SMP 初始化过程中，...",
    "reproduction_steps": [...],
    "technical_context": {...},
    "feasibility": {
      "status": "GO",
      "rationale": "问题边界清晰，已有部分讨论，无现有 Patch",
      "estimated_effort": "3-5 days"
    },
    "references": [...]
  }
}
```

---

### 4.2 规划层（Planning Agent）

#### 4.2.1 职责定义

- **方案设计**：基于探索报告，设计完整的代码开发和测试方案
- **任务拆解**：将贡献任务拆解为可执行的子任务序列
- **依赖分析**：识别任务间的依赖关系和资源需求
- **风险评估**：识别潜在的技术风险并制定应对策略

#### 4.2.2 Agent 设计（OpenAI Agents SDK）

```python
# 规划层 Agent
planner = Agent(
    name="ContributionPlanner",
    instructions="""
    你是 RV-Insights 的规划专家，负责为 RISC-V 开源贡献设计完整的执行方案。
    
    输入：探索层输出的贡献机会报告
    输出：详细的开发和测试方案
    
    你的方案必须包含：
    1. **开发方案**
       - 涉及的文件和模块清单
       - 预期的代码变更范围
       - 编码规范和风格要求
       - 依赖的头文件和库
    
    2. **测试方案**
       - 单元测试策略和覆盖目标
       - 集成测试场景
       - 硬件在环测试需求（如需要 QEMU/真实硬件）
       - 回归测试计划
    
    3. **验证清单**
       - 编译验证命令
       - 静态分析检查项
       - 运行时测试命令
       - 性能基准测试（如适用）
    
    4. **执行计划**
       - 子任务列表（带优先级和依赖关系）
       - 预估时间线
       - 关键里程碑
    
    你需要参考 RISC-V 社区的贡献规范（如 Linux 内核的 Coding Style、Patch 提交规范等）。
    """,
    model="o3-mini",  # 使用推理模型进行深度规划
    tools=[query_coding_standards, fetch_contribution_guide, 
           analyze_code_dependencies, estimate_test_coverage],
    guardrails=[plan_completeness_check, scope_guardrail]
)
```

#### 4.2.3 为什么使用 OpenAI Agents SDK

| 特性 | 在规划层的价值 |
|------|--------------|
| **o3-mini 推理模型** | 规划需要深度推理能力，OpenAI 的 o3-mini 在复杂任务规划上表现优异 |
| **Guardrails** | `plan_completeness_check` 护栏确保方案不遗漏关键环节（如测试、文档） |
| **Tracing** | 规划过程的完整追踪，便于人工理解方案的推导逻辑 |
| **工具链** | 通过工具查询编码规范、依赖关系等外部信息 |

#### 4.2.4 输出格式

```json
{
  "plan": {
    "contribution_id": "RV-2026-0423-001",
    "version": "1.0",
    "development_plan": {
      "target_files": ["arch/riscv/kernel/smp.c", "arch/riscv/include/asm/smp.h"],
      "change_summary": "在 smp_boot 函数中添加 hartid 边界检查...",
      "coding_standards": ["Linux Kernel Coding Style", "RISC-V 内核 Patch 规范"],
      "estimated_loc": "30-50 行"
    },
    "testing_plan": {
      "unit_tests": {...},
      "integration_tests": {...},
      "qemu_tests": {...},
      "hardware_tests": "可选：在 HiFive Unmatched 上验证"
    },
    "validation_checklist": [
      "make ARCH=riscv CROSS_COMPILE=riscv64-linux-gnu- defconfig",
      "make ARCH=riscv CROSS_COMPILE=riscv64-linux-gnu- -j$(nproc)",
      "checkpatch.pl --strict 检查 Patch 格式",
      "在 QEMU 中启动并验证 SMP 初始化"
    ],
    "execution_schedule": [
      {"task": "环境准备", "duration": "2h", "depends_on": []},
      {"task": "代码开发", "duration": "1d", "depends_on": ["环境准备"]},
      {"task": "单元测试", "duration": "4h", "depends_on": ["代码开发"]},
      {"task": "集成测试", "duration": "1d", "depends_on": ["单元测试"]}
    ]
  }
}
```

---

### 4.3 开发层（Development Agent）

#### 4.3.1 职责定义

- **代码实现**：根据规划方案，在沙箱环境中进行代码开发
- **增量提交**：按逻辑步骤进行代码变更，生成清晰的 Git 提交历史
- **文档编写**：编写/更新相关文档和注释
- **自检**：在提交前进行基本的编译和格式检查

#### 4.3.2 Agent 设计（Claude Agent SDK）

```python
# 开发层 Agent（Claude Agent SDK）
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

dev_options = ClaudeAgentOptions(
    system_prompt="""
    你是 RV-Insights 的开发专家，负责 RISC-V 开源项目的代码开发。
    
    你的工作规范：
    1. 严格遵循项目编码规范（如 Linux Kernel Coding Style）
    2. 每个变更必须有清晰的提交信息
    3. 优先使用最小化变更原则
    4. 所有代码变更必须在沙箱环境中完成
    5. 变更后必须进行编译验证
    6. 使用 checkpatch.pl 检查 Patch 格式
    
    你的工具：
    - 文件读写：读取和修改源代码
    - Bash 执行：编译、测试、Git 操作
    - 代码导航：跳转到定义、查找引用
    """,
    permission_mode="accept_edits",  # 自动接受编辑操作（沙箱内安全）
    read_write_tools=True,           # 启用文件读写
    bash_tools=True,                 # 启用 Bash 执行
    cwd="/sandbox/riscv-projects",   # 沙箱工作目录
    max_cost=5.0,                    # 成本上限
    audit_log_path="/logs/dev_agent.log"
)

dev_client = ClaudeSDKClient(options=dev_options)

# 绑定开发专用工具（通过 MCP）
dev_client.register_tools([
    "git_commit",           # Git 提交工具
    "checkpatch",           # Linux 内核 Patch 检查
    "cross_compile",        # 交叉编译工具
    "qemu_boot",            # QEMU 启动验证
])
```

#### 4.3.3 为什么使用 Claude Agent SDK

| 特性 | 在开发层的价值 |
|------|--------------|
| **原生文件读写** | 代码开发的核心是文件操作，Claude SDK 原生支持，无需额外工具定义 |
| **Bash 执行** | 编译、Git 操作、checkpatch 等都需要 Bash，Claude SDK 开箱即用 |
| **代码导航** | 基于 AST 的代码导航能力，便于理解大型代码库（如 Linux 内核） |
| **权限控制** | `permission_mode` 可精细控制 Agent 的编辑权限，配合沙箱保障安全 |
| **上下文管理** | 自动上下文压缩，在处理大型代码文件时保持高效 |
| **会话持久化** | 开发会话可暂停、恢复，适合长时间运行的开发任务 |
| **Claude Code 生态** | 用户明确要求 "Claude Code 承担该角色"，Claude SDK 正是 Claude Code 的底层架构 |

> **关键决策依据**：开发层的核心需求是**代码生成与修改**，这正是 Claude Agent SDK 的设计目标。Claude SDK 将 Claude Code（已在十亿美元级产品中验证）的完整能力 API 化，提供文件操作、Bash 执行、代码导航等原生能力，是开发层的最佳选择。

---

### 4.4 审核层（Review Agent）

#### 4.4.1 职责定义

- **代码 Review**：对开发 Agent 产出的代码进行全面审查
- **问题分类**：将发现的问题分类为致命/严重/一般/建议
- **迭代反馈**：将问题反馈给开发 Agent，要求修复
- **质量把关**：直到代码质量达到可提交标准

#### 4.4.2 Agent 设计（OpenAI Agents SDK + Codex）

```python
# 审核层 Agent 集群

# 1. 代码风格审核 Agent
style_reviewer = Agent(
    name="StyleReviewer",
    instructions="""
    你是代码风格审核专家，专注于：
    - 编码规范合规性（缩进、命名、注释风格）
    - 代码可读性和可维护性
    - 文档和注释的完整性
    - Commit Message 的规范性
    """,
    model="gpt-4o",
    tools=[run_checkpatch, check_coding_style, analyze_commit_message]
)

# 2. 逻辑正确性审核 Agent（使用 Codex 模型）
logic_reviewer = Agent(
    name="LogicReviewer",
    instructions="""
    你是代码逻辑审核专家，专注于：
    - 算法正确性
    - 边界条件处理
    - 并发安全性
    - 资源泄漏风险
    - 与 RISC-V 架构规范的符合性
    
    你需要深入理解 RISC-V ISA 和内核代码逻辑。
    """,
    model="codex-latest",  # OpenAI Codex 模型
    tools=[static_analysis, semantic_diff, reference_spec_check]
)

# 3. 安全审核 Agent
security_reviewer = Agent(
    name="SecurityReviewer",
    instructions="""
    你是安全审核专家，专注于：
    - 内存安全（越界访问、UAF、缓冲区溢出）
    - 整数溢出
    - 权限检查遗漏
    - 竞争条件
    """,
    model="gpt-4o",
    tools=[run_semgrep, run_codeql, analyze_cwe_patterns]
)

# 4. 审核协调 Agent
review_orchestrator = Agent(
    name="ReviewOrchestrator",
    instructions="""
    你是审核层的协调者。
    你的任务：
    1. 并行启动多个专项审核 Agent
    2. 收集所有审核结果
    3. 综合评估代码质量
    4. 如果发现问题，生成结构化的修复要求
    5. 如果审核通过，生成审核报告
    
    迭代终止条件：
    - 所有致命和严重问题已修复
    - 一般问题不超过 3 个（可接受）
    - 连续两轮审核无新问题产生
    """,
    model="gpt-4o",
    handoffs=[style_reviewer, logic_reviewer, security_reviewer],
    guardrails=[review_completeness_guardrail, iteration_limit_guardrail]
)
```

#### 4.4.3 迭代机制

```
┌─────────────┐     提交代码      ┌─────────────┐
│  开发 Agent  │ ───────────────► │  审核 Agent  │
│ (Claude SDK)│                  │(OpenAI SDK) │
└─────────────┘                  └──────┬──────┘
     ▲                                  │
     │         返回修复要求              │
     └──────────────────────────────────┘
              
迭代终止条件（满足任一）：
1. 审核通过（PASS）
2. 达到最大迭代次数（默认 5 轮）
3. 人工介入终止
```

#### 4.4.4 为什么使用 OpenAI Agents SDK + Codex

| 特性 | 在审核层的价值 |
|------|--------------|
| **Codex 模型** | 用户明确要求 "Codex 承担该角色"，OpenAI Agents SDK 原生支持 Codex 模型调用 |
| **并行审核** | 风格、逻辑、安全三个审核 Agent 可并行执行，提高效率 |
| **Guardrails** | `iteration_limit_guardrail` 防止无限迭代；`review_completeness_guardrail` 确保审核全面 |
| **Tracing** | 记录每轮审核的详细结果，便于追溯代码质量演进过程 |
| **HITL 集成** | 2025年6月新增的 HITL 审批机制，支持人工在迭代过程中介入 |

---

### 4.5 测试层（Testing Agent）

#### 4.5.1 职责定义

- **环境搭建**：根据测试方案搭建编译和测试环境
- **测试执行**：执行单元测试、集成测试、QEMU 测试等
- **结果分析**：分析测试结果，识别失败原因
- **报告生成**：生成结构化的测试报告

#### 4.5.2 Agent 设计（Claude Agent SDK）

```python
# 测试层 Agent（Claude Agent SDK）
test_options = ClaudeAgentOptions(
    system_prompt="""
    你是 RV-Insights 的测试专家，负责搭建测试环境并执行验证。
    
    你的工作规范：
    1. 严格按照规划层的测试方案执行
    2. 环境搭建必须可复现（使用容器或脚本）
    3. 所有测试命令和输出必须记录
    4. 测试失败时进行根因分析
    5. 区分"环境问题"和"代码问题"
    
    你的工具：
    - 文件读写：修改配置文件、编写测试脚本
    - Bash 执行：编译、运行测试、环境配置
    - Docker 控制：管理测试容器
    """,
    permission_mode="prompt",  # 危险操作需要确认
    read_write_tools=True,
    bash_tools=True,
    cwd="/sandbox/test-env",
    max_cost=3.0,
    audit_log_path="/logs/test_agent.log"
)

test_client = ClaudeSDKClient(options=test_options)

test_client.register_tools([
    "docker_run",           # Docker 容器管理
    "qemu_launch",          # QEMU 启动
    "cross_compile_test",   # 交叉编译测试
    "kunit_runner",         # KUnit 测试执行
    "capture_test_output",  # 测试输出捕获
])
```

#### 4.5.3 为什么使用 Claude Agent SDK

| 特性 | 在测试层的价值 |
|------|--------------|
| **Bash 执行** | 测试环境搭建涉及大量命令行操作（安装依赖、配置编译器、启动 QEMU） |
| **文件读写** | 修改内核配置（`.config`）、编写测试脚本、解析测试输出 |
| **Docker 控制** | 通过 Bash 调用 Docker，实现可复现的测试环境 |
| **权限控制** | `permission_mode="prompt"` 对危险操作（如清理环境）进行确认 |
| **上下文管理** | 测试输出可能很长，自动上下文压缩保留关键信息 |

---

## 5. SDK 选型分析与融合策略

### 5.1 OpenAI Agents SDK 核心特性

| 维度 | 详情 |
|------|------|
| **定位** | 轻量级多 Agent 编排框架 |
| **核心概念** | Agent + Handoff + Guardrail |
| **设计哲学** | 框架做减法，模型负责智能 |
| **多 Agent 模式** | Handoff（接力式交接） |
| **安全机制** | Guardrails（输入/输出护栏） |
| **可观测性** | 内置 Tracing 系统 |
| **模型兼容** | 开放兼容第三方模型 |
| **HITL** | 2025年6月新增人机回路审批机制 |
| **独特优势** | 编排直觉优雅、RealtimeAgent 语音、浏览器端运行 |

### 5.2 Claude Agent SDK 核心特性

| 维度 | 详情 |
|------|------|
| **定位** | 企业级 Agent 运行时系统 |
| **核心概念** | Agent + Tool + MCP Server + Hooks |
| **设计哲学** | 给 Agent 一台完整的"电脑" |
| **多 Agent 模式** | Sub-Agent（指挥官-执行者） |
| **安全机制** | 生命周期钩子 + 细粒度权限 |
| **可观测性** | 流式会话 + 审计日志 |
| **上下文管理** | 自动压缩 + 动态工具搜索 |
| **内置能力** | 文件读写、Bash 执行、代码导航 |
| **独特优势** | 会话传送、技能热重载、自动模型路由 |

### 5.3 双 SDK 融合架构

#### 5.3.1 融合策略总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        RV-Insights SDK 融合架构                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────┐         ┌─────────────────────────┐   │
│  │    OpenAI Agents SDK    │         │    Claude Agent SDK     │   │
│  │    【编排与决策中心】     │◄───────►│    【执行与操作中心】     │   │
│  │                         │  MCP    │                         │   │
│  │ • 工作流状态机           │ Protocol│ • 代码文件操作           │   │
│  │ • Agent 路由 (Handoff)  │         │ • Bash 命令执行          │   │
│  │ • 质量护栏 (Guardrail)  │         │ • 代码导航与分析          │   │
│  │ • 迭代协调               │         │ • 环境搭建与管理          │   │
│  │ • 人机回路 (HITL)       │         │ • 编译与测试执行          │   │
│  │ • 全流程追踪 (Tracing)  │         │ • 会话持久化             │   │
│  │                         │         │                         │   │
│  │ 负责：                  │         │ 负责：                  │   │
│  │ • 探索层                │         │ • 开发层                │   │
│  │ • 规划层                │         │ • 测试层                │   │
│  │ • 审核层（协调）         │         │ • 复杂工具操作          │   │
│  │ • 整体工作流编排          │         │ • 沙箱环境管理          │   │
│  └─────────────────────────┘         └─────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    MCP 协议网关层                             │   │
│  │  • 统一工具注册与发现                                         │   │
│  │  • 跨 SDK 工具调用转发                                        │   │
│  │  • 结果格式标准化                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 5.3.2 各层 SDK 选型理由

| 层级 | 选用 SDK | 核心理由 |
|------|----------|----------|
| **探索层** | OpenAI Agents SDK | 1. **Handoff 机制**：多数据源（邮件列表/代码库/Issues）之间的任务路由；2. **Web Search 工具**：内置搜索 RISC-V 规范等外部信息；3. **Guardrails**：防止探索偏离主题 |
| **规划层** | OpenAI Agents SDK | 1. **o3-mini 推理模型**：复杂任务规划需要深度推理；2. **Guardrails**：确保方案完整性；3. **Tracing**：记录规划推理过程 |
| **开发层** | Claude Agent SDK | 1. **用户明确要求**："Claude Code 承担该角色"；2. **原生文件/Bash 能力**：代码开发的核心需求；3. **Claude Code 生态**：经过大规模生产验证的代码 Agent |
| **审核层** | OpenAI Agents SDK + Codex | 1. **用户明确要求**："Codex 承担该角色"；2. **并行审核**：多专项 Agent 并行；3. **迭代协调**：开发-审核循环的编排 |
| **测试层** | Claude Agent SDK | 1. **Bash 执行**：大量命令行操作；2. **文件操作**：配置修改、脚本编写；3. **环境管理**：沙箱内 Docker/QEMU 控制 |
| **工作流编排** | OpenAI Agents SDK | 1. **HITL 机制**：2025年6月新增的人机回路审批；2. **状态管理**：`to_input_list()` 支持状态持久化；3. **Tracing**：全流程可观测 |

#### 5.3.3 融合的关键：MCP 协议网关

两个 SDK 都支持 **Model Context Protocol (MCP)**，这是实现融合的关键：

```python
# MCP 网关实现示意
from mcp.server import Server
from mcp.types import Tool

class RVInsightsMCPGateway:
    """
    RV-Insights MCP 协议网关
    实现 OpenAI SDK 和 Claude SDK 之间的工具互操作
    """
    
    def __init__(self):
        self.openai_tools = {}   # OpenAI SDK 注册的工具
        self.claude_tools = {}   # Claude SDK 注册的工具
        self.server = Server("rv-insights-gateway")
    
    def register_openai_tool(self, tool: Tool):
        """注册 OpenAI SDK 工具，使其可被 Claude SDK 调用"""
        self.openai_tools[tool.name] = tool
        # 包装为 Claude SDK 兼容的 MCP Server
        
    def register_claude_tool(self, tool: Tool):
        """注册 Claude SDK 工具，使其可被 OpenAI SDK 调用"""
        self.claude_tools[tool.name] = tool
        # 包装为 OpenAI SDK 兼容的 function_tool
    
    async def forward(self, source_sdk: str, target_sdk: str, 
                      tool_name: str, params: dict):
        """
        跨 SDK 工具调用转发
        
        Args:
            source_sdk: 调用方 SDK ("openai" | "claude")
            target_sdk: 目标 SDK ("openai" | "claude")
            tool_name: 工具名称
            params: 调用参数
        """
        if target_sdk == "claude":
            return await self.claude_tools[tool_name].execute(params)
        else:
            return await self.openai_tools[tool_name].execute(params)
```

**融合示例**：审核 Agent（OpenAI SDK）需要查看代码文件 → 通过 MCP 网关调用 Claude SDK 的文件读取工具 → 结果返回给审核 Agent。

---

## 6. 人机回路（HITL）机制

### 6.1 设计原则

- **每个阶段后必须人工确认**：探索→规划→开发→审核→测试
- **人工拥有最终否决权**：Agent 的建议仅供参考
- **支持随时介入**：不仅限于阶段边界，可在 Agent 执行中暂停
- **决策可追溯**：所有人工决策记录到审计日志

### 6.2 HITL 状态机

```
                    ┌──────────────┐
                    │    START     │
                    └──────┬───────┘
                           │ 启动探索
                           ▼
                    ┌──────────────┐
         ┌─────────│  EXPLORING   │◄────────┐
         │         │   (探索中)    │         │
         │         └──────┬───────┘         │
         │                │ 探索完成          │
         │                ▼                 │ 拒绝/修改
         │         ┌──────────────┐         │
         │    ┌───►│ HITL_REVIEW  │─────────┘
         │    │    │ (人工审核探索结果)│
         │    │    └──────┬───────┘
         │    │           │ 通过
         │    │           ▼
         │    │    ┌──────────────┐
         │    │    │   PLANNING   │
         │    │    │   (规划中)    │
         │    │    └──────┬───────┘
         │    │           │ 规划完成
         │    │           ▼
         │    │    ┌──────────────┐
         │    ├───►│ HITL_REVIEW  │
         │    │    │ (人工审核规划方案)│
         │    │    └──────┬───────┘
         │    │           │ 通过
         │    │           ▼
         │    │    ┌──────────────┐
         │    │    │ DEVELOPING   │◄─────────────────┐
         │    │    │   (开发中)    │                  │
         │    │    └──────┬───────┘                  │
         │    │           │ 开发完成                   │
         │    │           ▼                          │
         │    │    ┌──────────────┐                  │
         │    ├───►│ HITL_REVIEW  │                  │
         │    │    │(人工审核开发结果)│                 │
         │    │    └──────┬───────┘                  │
         │    │           │ 通过                     │
         │    │           ▼                          │
         │    │    ┌──────────────┐     审核不通过    │
         │    │    │  REVIEWING   │──────────────────┘
         │    │    │   (审核中)    │
         │    │    └──────┬───────┘
         │    │           │ 审核迭代完成
         │    │           ▼
         │    │    ┌──────────────┐
         │    ├───►│ HITL_REVIEW  │
         │    │    │(人工审核审核结果)│
         │    │    └──────┬───────┘
         │    │           │ 通过
         │    │           ▼
         │    │    ┌──────────────┐
         │    │    │   TESTING    │◄─────────────────┐
         │    │    │   (测试中)    │                  │
         │    │    └──────┬───────┘                  │
         │    │           │ 测试失败需修复             │
         │    │           ▼                          │
         │    │    ┌──────────────┐                  │
         │    └───►│ HITL_REVIEW  │                  │
         │         │(人工审核测试结果)│                 │
         │         └──────┬───────┘                  │
         │                │ 通过                     │
         │                ▼                          │
         │         ┌──────────────┐                  │
         │         │   COMPLETE   │                  │
         └────────►│   (完成)     │                  │
                   └──────────────┘                  │
                                                     │
                     用户可随时从任何状态            │
                     发起 "PAUSE" 或 "ABORT"        │
```

### 6.3 HITL 交互界面

```json
{
  "hitl_request": {
    "stage": "development",
    "task_id": "RV-2026-0423-001",
    "agent_output": {
      "summary": "已完成 hartid 越界访问修复",
      "files_modified": ["arch/riscv/kernel/smp.c"],
      "commit_hash": "a1b2c3d",
      "diff_stats": {"insertions": 12, "deletions": 3}
    },
    "required_action": "请审核代码变更，确认是否进入审核阶段",
    "options": [
      {"action": "approve", "label": "通过，进入下一阶段"},
      {"action": "reject", "label": "拒绝，返回修改"},
      {"action": "modify", "label": "提出修改意见"},
      {"action": "abort", "label": "终止任务"}
    ],
    "timeout": "24h"
  }
}
```

---

## 7. 数据流与状态管理

### 7.1 数据流架构

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
│  └────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘     └───┬────┘│
│       │               │               │               │               │    │
│       └───────────────┴───────────────┴───────────────┴───────────────┘    │
│                                   │                                        │
│                                   ▼                                        │
│                         ┌─────────────────┐                                │
│                         │   State Store    │                                │
│                         │  (PostgreSQL +   │                                │
│                         │   Redis Cache)   │                                │
│                         └─────────────────┘                                │
│                                   │                                        │
│                                   ▼                                        │
│                         ┌─────────────────┐                                │
│                         │   Event Bus      │                                │
│                         │   (Redis Pub/Sub)│                                │
│                         └─────────────────┘                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 核心数据模型

```python
# 任务（Task）- 顶层实体
class Task:
    task_id: str           # RV-YYYY-MM-DD-NNN
    status: TaskStatus     # PENDING -> EXPLORING -> PLANNING -> ... -> COMPLETE
    title: str
    description: str
    created_at: datetime
    updated_at: datetime
    current_stage: Stage
    hitl_pending: bool     # 是否等待人工审核

# 阶段（Stage）
class Stage:
    stage_id: str
    stage_type: StageType  # DISCOVERY / PLANNING / DEVELOPMENT / REVIEW / TESTING
    status: StageStatus    # RUNNING / HITL_PENDING / COMPLETED / FAILED
    input_artifact: str    # 输入 Artifact ID
    output_artifact: str   # 输出 Artifact ID
    agent_logs: List[AgentLog]
    iteration_count: int   # 迭代次数（用于审核阶段）

# Artifact（阶段产出物）
class Artifact:
    artifact_id: str
    artifact_type: str     # report / plan / code / review_result / test_result
    content: dict          # 结构化内容
    raw_data: bytes        # 原始数据（如 diff 文件）
    created_by: str        # Agent 名称
    parent_artifact: str   # 父 Artifact（形成链路）
```

---

## 8. 安全与权限控制

### 8.1 安全架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              安全控制体系                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        网络安全层                                     │   │
│  │  • API Gateway（认证/限流/WAF）                                       │   │
│  │  • 零信任网络架构                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        沙箱隔离层                                     │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │ 开发沙箱      │  │ 测试沙箱      │  │ 探索沙箱      │              │   │
│  │  │ (Docker)     │  │ (Docker/KVM) │  │ (受限网络)    │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  │                                                                     │   │
│  │  约束：                                                             │   │
│  │  • 无网络访问或仅允许白名单域名                                       │   │
│  │  • 文件系统只读挂载（除工作目录）                                     │   │
│  │  • CPU/内存/磁盘配额限制                                              │   │
│  │  • 禁止特权容器                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        权限控制层                                     │   │
│  │                                                                     │   │
│  │  OpenAI Agents SDK:              Claude Agent SDK:                  │   │
│  │  ┌─────────────────────┐         ┌─────────────────────┐           │   │
│  │  │ • Guardrails        │         │ • permission_mode   │           │   │
│  │  │   - 输入护栏          │         │   - accept_all      │           │   │
│  │  │   - 输出护栏          │         │   - accept_edits    │           │   │
│  │  │ • Tracing 审计        │         │   - prompt          │           │   │
│  │  │ • Function 白名单    │         │ • PreToolUse Hooks  │           │   │
│  │  └─────────────────────┘         │ • PostToolUse Hooks │           │   │
│  │                                  └─────────────────────┘           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        审计与合规层                                   │   │
│  │  • 所有 Agent 操作记录到不可篡改日志                                   │   │
│  │  • LLM 调用记录（输入/输出/token 消耗）                                │   │
│  │  • 工具调用记录（参数/结果/执行时间）                                  │   │
│  │  • 人工决策记录（操作人/时间/理由）                                    │   │
│  │  • 数据保留策略（符合 GDPR/等保要求）                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Agent 权限矩阵

| Agent | 文件读取 | 文件写入 | Bash 执行 | 网络访问 | Git 操作 | Docker 控制 |
|-------|----------|----------|-----------|----------|----------|-------------|
| 探索 Agent | ✅ | ❌ | ⚠️（受限） | ✅（白名单） | ❌ | ❌ |
| 规划 Agent | ✅ | ❌ | ❌ | ✅（白名单） | ❌ | ❌ |
| 开发 Agent | ✅ | ✅（工作目录） | ✅（受限命令） | ❌ | ✅ | ❌ |
| 审核 Agent | ✅ | ❌ | ⚠️（静态分析工具） | ❌ | ✅（只读） | ❌ |
| 测试 Agent | ✅ | ✅（测试目录） | ✅ | ⚠️（受限） | ❌ | ✅ |

> **图例**：✅ 允许 / ❌ 禁止 / ⚠️ 受限

---

## 9. 技术栈与依赖

### 9.1 核心技术栈

| 层级 | 技术选型 | 版本要求 |
|------|----------|----------|
| **编排框架** | OpenAI Agents SDK (Python) | >= 0.1.0 |
| **执行框架** | Claude Agent SDK (Python) | >= 0.1.0 |
| **互操作协议** | Model Context Protocol (MCP) | >= 1.0.0 |
| **Web 框架** | FastAPI | >= 0.110.0 |
| **前端** | React + TypeScript | >= 18.0 |
| **数据库** | PostgreSQL | >= 16 |
| **缓存** | Redis | >= 7.0 |
| **消息队列** | Redis Pub/Sub / RabbitMQ | >= 3.12 |
| **沙箱** | Docker + gVisor / Firecracker | >= 24.0 |
| **任务调度** | Celery + Flower | >= 5.3 |
| **可观测性** | OpenTelemetry + Jaeger + Prometheus | >= 1.20 |
| **LLM 网关** | LiteLLM Proxy | >= 1.0 |

### 9.2 LLM 模型配置

| Agent | 推荐模型 | 备选模型 | 说明 |
|-------|----------|----------|------|
| 探索协调 | `gpt-4o` | `claude-sonnet-4` | 通用推理和调度 |
| 邮件探索 | `gpt-4o` | `claude-sonnet-4` | 自然语言理解和信息提取 |
| 代码探索 | `gpt-4o` | `claude-sonnet-4` | 代码理解和分析 |
| 可行性验证 | `o3-mini` | `claude-opus-4` | 深度推理和判断 |
| 规划 | `o3-mini` | `claude-opus-4` | 复杂方案规划 |
| 开发 | `claude-sonnet-4` | `claude-opus-4` | 代码生成（Claude SDK 绑定） |
| 风格审核 | `gpt-4o` | `codex` | 编码规范检查 |
| 逻辑审核 | `codex-latest` | `o3-mini` | 代码逻辑深度分析 |
| 安全审核 | `gpt-4o` | `codex` | 安全模式识别 |
| 测试 | `claude-sonnet-4` | `claude-haiku-4` | 命令执行和脚本生成 |

### 9.3 RISC-V 专用工具链

| 工具 | 用途 |
|------|------|
| `riscv64-linux-gnu-gcc` | 交叉编译器 |
| `qemu-system-riscv64` | RISC-V 系统模拟 |
| `spike` | RISC-V ISA 模拟器（黄金参考） |
| `opensbi` | RISC-V 固件 |
| `u-boot` | RISC-V Bootloader |
| `linux-riscv` | RISC-V Linux 内核源码 |
| `checkpatch.pl` | Linux 内核 Patch 格式检查 |
| `sparse` | Linux 内核静态分析 |
| `coccinelle` | 内核代码变换工具 |

---

## 10. 部署架构

### 10.1 容器化部署

```yaml
# docker-compose.yml 核心服务定义
version: '3.8'

services:
  # API 网关
  api-gateway:
    image: rv-insights/api-gateway:latest
    ports:
      - "8080:8080"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - postgres
      - redis

  # 编排服务（OpenAI Agents SDK）
  orchestrator:
    image: rv-insights/orchestrator:latest
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/rvinsights
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock  # 管理沙箱容器

  # 执行服务（Claude Agent SDK）
  executor:
    image: rv-insights/executor:latest
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - REDIS_URL=redis://redis:6379
    # 特权模式用于管理沙箱容器（生产环境使用更安全的方案）
    privileged: true

  # 沙箱池（动态创建）
  sandbox-pool:
    image: rv-insights/sandbox:latest
    scale: 0  # 由 orchestrator 动态创建
    runtime: runc  # 或 gVisor / Firecracker
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=1g
    cpus: '4'
    mem_limit: 8g

  # 数据库
  postgres:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=rvinsights
      - POSTGRES_PASSWORD=${DB_PASSWORD}

  # 缓存
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  # 可观测性
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

volumes:
  postgres_data:
  redis_data:
```

### 10.2 沙箱架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          宿主机 (Host)                               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Docker Daemon                             │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │   │
│  │  │  开发沙箱-1  │  │  测试沙箱-1  │  │  探索沙箱-1  │         │   │
│  │  │ (gVisor)   │  │ (gVisor)   │  │ (gVisor)   │         │   │
│  │  │            │  │            │  │            │         │   │
│  │  │ • 源码挂载  │  │ • 源码挂载  │  │ • 隔离网络  │         │   │
│  │  │ • 编译工具  │  │ • QEMU     │  │ • 爬虫工具  │         │   │
│  │  │ • Git      │  │ • 测试框架  │  │ • 分析工具  │         │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘         │   │
│  │                                                             │   │
│  │  网络策略：                                                  │   │
│  │  • 沙箱间禁止通信                                             │   │
│  │  • 仅允许出站连接到白名单域名                                   │   │
│  │  • 所有入站连接禁止                                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 11. 演进路线

### Phase 1：MVP（0-3 个月）

- [ ] 搭建基础架构（OpenAI + Claude SDK 融合框架）
- [ ] 实现探索层（邮件列表 + GitHub Issues）
- [ ] 实现规划层（基础方案生成）
- [ ] 实现开发层（单文件代码修改）
- [ ] 实现基础 HITL 机制
- [ ] 支持 Linux 内核 RISC-V 子系统

### Phase 2：能力扩展（3-6 个月）

- [ ] 增加审核层多轮迭代机制
- [ ] 增加测试层（QEMU 测试）
- [ ] 支持更多项目（GCC、LLVM、QEMU）
- [ ] 完善 MCP 工具生态
- [ ] 引入 RAG 知识库

### Phase 3：生产就绪（6-12 个月）

- [ ] 多租户支持
- [ ] 完善的审计和合规
- [ ] 性能优化和成本优化
- [ ] 社区集成（自动提交 PR/Mail）
- [ ] A/B 测试框架

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
│  │ (State)      │  │ (Human)      │  │ (Event)      │  │ (Celery)   │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘ │
│         │                 │                 │                │        │
│         └─────────────────┴─────────────────┘                │        │
└────────────────────────────────────────┬─────────────────────┴────────┘
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
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ 邮件列表  │  │ GitHub   │  │ 代码分析  │  │ 测试沙箱  │  │ RAG      │ │
│  │ 爬虫     │  │ API     │  │ 工具链   │  │ (Docker) │  │ 知识库   │ │
│  │          │  │         │  │          │  │          │  │          │ │
│  │ • lore   │  │ • Issues│  │ • AST   │  │ • QEMU  │  │ • ISA   │ │
│  │ • patchwa│  │ • PRs   │  │ • Call  │  │ • Spike │  │ • ABI   │ │
│  │ • groups │  │ • Commits│ │ • Graph │  │ • HW    │  │ • Docs  │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
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

## 总结

**RV-Insights** 平台采用 **OpenAI Agents SDK + Claude Agent SDK 融合架构**，充分发挥两个框架的优势：

| 维度 | 策略 |
|------|------|
| **编排与路由** | OpenAI Agents SDK 的 Handoff 和 HITL 机制 |
| **代码开发与执行** | Claude Agent SDK 的原生文件/Bash 能力 |
| **互操作** | MCP 协议网关实现两个生态的无缝集成 |
| **安全** | 双层 Guardrails + 生命周期 Hooks + 沙箱隔离 |
| **可观测性** | OpenAI Tracing + Claude 审计日志的统一汇聚 |

这种融合策略不仅满足了 RV-Insights 各节点的特定需求，也为未来接入更多 Agent 框架（如 Google ADK、AutoGen 等）预留了扩展空间。

---

*文档结束*
