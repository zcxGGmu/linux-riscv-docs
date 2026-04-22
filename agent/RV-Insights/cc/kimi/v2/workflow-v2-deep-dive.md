# RV-Insights v2: OpenAI Agents SDK 编排深化设计

**版本**: v2.0
**日期**: 2026-04-23
**目标**: 细化 RV-Insights v2 五阶段工作流在 OpenAI Agents SDK + Claude Agent SDK 混合架构下的编排实现。覆盖 Handoff 图定义、开发-审核迭代子图、错误分类与重试、并发控制、会话生命周期管理及完整伪代码实现。

**依赖文档**:
- `rv-insights-v2-design.md` — 主方案与架构选型
- `v1/workflow-deep-dive.md` — v1 LangGraph 编排实现（迁移基准）

**SDK 版本要求**:
- `openai-agents >= 1.5.0` (Handoff + Interrupt + Guardrails + 原生沙箱)
- `anthropic >= 0.45.0` (Claude Agent SDK / Managed Agents Beta)

---

## 文档地图

| 章节 | 内容 | 行数估计 |
|------|------|----------|
| 1. OpenAI Agents SDK Handoff 图定义 | 全局 Handoff 图、条件 Handoff、interrupt 配置、状态传递 | ~150 |
| 2. 开发-审核迭代子图 | 子图状态、条件 Handoff 循环、Claude Subagent 修复注入、增量审核、强制退出 | ~250 |
| 3. 错误分类与重试策略 | 错误矩阵、指数退避、DLQ、部分失败处理 | ~150 |
| 4. 并发控制 | Git 锁、QEMU 池、Worker Pool、租户配额 | ~150 |
| 5. 会话生命周期管理 | 超时策略、优雅终止、孤儿检测、Checkpointer | ~180 |
| 6. 完整伪代码实现 | 全局图、子图、错误处理、并发、超时、会话启动 | ~350 |
| 7. v1 → v2 编排迁移 | LangGraph/AutoGen/crewAI → OpenAI Agents SDK 映射 | ~120 |

---

## 1. OpenAI Agents SDK Handoff 图定义

### 1.1 核心抽象映射

OpenAI Agents SDK v1.5+ 引入三个核心抽象，直接替代 v1 的 LangGraph 概念：

| LangGraph (v1) | OpenAI Agents SDK (v2) | 说明 |
|----------------|------------------------|------|
| `StateGraph` | `Agent` + `Handoff` | Agent 即节点，Handoff 即边 |
| `Node` | `Agent` (with `instructions` + `tools`) | Agent 定义封装了节点逻辑 |
| `Edge` / `Conditional Edge` | `handoff()` / `handoff(condition=...)` | 显式 Handoff 替代隐式边 |
| `interrupt` | `interrupt()` (原生) | 内建 Human-in-the-Loop，无需外部钩子 |
| `checkpointer` | `Session` 持久化 (PostgreSQL) | SDK 自动管理 checkpoint |
| `subgraph` | `Agent` 嵌套 / `Subagent` 调用 | 子图作为 Agent 的能力而非独立图 |

### 1.2 全局 Handoff 图

```mermaid
stateDiagram-v2
    [*] --> INITIALIZATION: 创建会话
    INITIALIZATION --> EXPLORATION: Orchestrator Handoff 到 Explorer

    EXPLORATION --> HUMAN_REVIEW_EXPLORATION: 探索完成，interrupt
    HUMAN_REVIEW_EXPLORATION --> EXPLORATION: [人类] REQUEST_CHANGES
    HUMAN_REVIEW_EXPLORATION --> PLANNING: [人类] APPROVE
    HUMAN_REVIEW_EXPLORATION --> [*]: [人类] REJECT

    PLANNING --> HUMAN_REVIEW_PLANNING: 规划完成，interrupt
    HUMAN_REVIEW_PLANNING --> PLANNING: [人类] REQUEST_CHANGES
    HUMAN_REVIEW_PLANNING --> DEVELOPMENT: [人类] APPROVE
    HUMAN_REVIEW_PLANNING --> [*]: [人类] REJECT

    DEVELOPMENT --> REVIEW: 开发完成，Handoff 到 Reviewer
    REVIEW --> DEVELOPMENT: [条件] NEEDS_REVISION ∧ iter < MAX
    REVIEW --> HUMAN_REVIEW_CODE: [条件] PASS
    REVIEW --> HUMAN_REVIEW_CODE: [条件] MAX_ITERATIONS

    HUMAN_REVIEW_CODE --> DEVELOPMENT: [人类] REQUEST_CHANGES
    HUMAN_REVIEW_CODE --> TESTING: [人类] APPROVE
    HUMAN_REVIEW_CODE --> [*]: [人类] REJECT

    TESTING --> HUMAN_REVIEW_TESTING: 测试完成，interrupt
    HUMAN_REVIEW_TESTING --> DEVELOPMENT: [人类] 测试失败需修复
    HUMAN_REVIEW_TESTING --> COMPLETION: [人类] APPROVE
    HUMAN_REVIEW_TESTING --> [*]: [人类] REJECT

    COMPLETION --> [*]: 归档会话
```

### 1.3 五阶段 Agent 定义与 Handoff 链

```python
# openai-agents >= 1.5.0
from agents import Agent, handoff, Tool, GuardrailFunction
from typing import List, Dict, Any, Literal
import os

# === 工具定义 (MCP Server 暴露) ===
web_search = Tool.from_mcp(server_url="http://mcp-tools:8080", tool_name="web_search")
github_api = Tool.from_mcp(server_url="http://mcp-tools:8080", tool_name="github_api")
rag_query = Tool.from_mcp(server_url="http://mcp-rag:8080", tool_name="query_riscv_knowledge")
static_analysis = Tool.from_mcp(server_url="http://mcp-tools:8080", tool_name="run_static_analyzer")
qemu_ctl = Tool.from_mcp(server_url="http://mcp-qemu:8080", tool_name="qemu_control")
test_runner = Tool.from_mcp(server_url="http://mcp-qemu:8080", tool_name="run_tests")

# === Guardrails 定义 ===
# === Guardrails 定义（目标 API 形态，待 SDK 正式发布后验证）===
# OpenAI Agents SDK 的 Guardrails 实际 API 可能使用回调函数而非字符串控制
riscv_spec_guardrail = GuardrailFunction(
    name="riscv_spec_compliance",
    check=lambda output: _check_csr_references(output),
    # on_fail 实际值取决于 SDK 版本，可能是 "halt" / "error" 或回调函数
    on_fail=lambda ctx: {"action": "route_to_developer", "reason": "csr_violation"},
)

security_guardrail = GuardrailFunction(
    name="security_scan",
    check=lambda output: _check_no_hardcoded_secrets(output),
    on_fail=lambda ctx: {"action": "route_to_developer", "reason": "security_issue"},
)

style_guardrail = GuardrailFunction(
    name="coding_style_compliance",
    check=lambda output: _check_coding_style(output),
    on_fail=lambda ctx: {"action": "route_to_developer", "reason": "style_issue"},
)

# === 五阶段 Agent 定义 ===

explorer_agent = Agent(
    name="explorer",
    model="gpt-4.1",  # 成本低，适合大量文本扫描
    instructions="""
    你是 RISC-V 生态探索 Agent。扫描邮件列表、Issue 和代码库，发现潜在贡献机会。
    输出结构化报告，包含：机会标题、描述、来源链接、可行性初步评估、相关代码路径。
    """,
    tools=[web_search, github_api, rag_query],
    # 探索完成后 Handoff 到规划阶段（由 Orchestrator 控制，非自动）
)

planner_agent = Agent(
    name="planner",
    # 目标 API 形态：通过 Provider-agnostic 模式调用 Claude 模型
    # 实际参数名取决于 OpenAI Agents SDK 正式发布版本（可能是 model_provider / extra_headers / custom_client）
    model="claude-sonnet-4-5",  # [假设：2026 Q2 模型版本]
    # provider="anthropic",  # 伪代码参数，待 SDK 验证
    instructions="""
    你是 RISC-V 软件架构师。将贡献机会转化为结构化的开发与测试方案。
    使用 Computer Use 浏览目标代码库，绘制精确的变更影响图。
    输出：开发方案（WBS、受影响文件、依赖项）、测试方案（QEMU配置、测试用例、通过标准）、风险评估。
    """,
    tools=[rag_query, git_checkout],  # git_checkout 通过 MCP 暴露
)

developer_agent = Agent(
    name="developer",
    model="claude-sonnet-4-5",  # [假设：2026 Q2 模型版本]
    # provider="anthropic",  # 伪代码参数，实际通过 Claude SDK 直接调用
    instructions="""
    你是专家级 RISC-V 系统开发者。根据 approved plan 实现代码变更。
    工作流：环境准备 → 代码实现 → 静态检查 → 编译验证 → 单元测试 → 产物打包。
    编译失败时最多自修复 3 次。所有操作在隔离沙箱中进行。
    """,
    tools=[bash, file_editor, git_commit, static_analysis],
    # Claude Managed Agents Beta 提供全托管容器环境
)

reviewer_agent = Agent(
    name="reviewer",
    model="codex",  # OpenAI Codex 代码审核专项模型
    instructions="""
    你是严格的 RISC-V 代码审核者。对代码变更进行多维度审查：
    1. 功能符合性 — 是否实现规划中的需求
    2. RISC-V 规范符合性 — CSR/指令/ABI 合法性
    3. 代码质量 — 可读性、命名、注释
    4. 安全性 — 无缓冲区溢出、无硬编码密钥
    5. 性能 — 避免不必要的内存拷贝
    6. 测试覆盖 — 单元测试是否充分
    7. 可维护性 — 是否符合目标项目贡献指南

    输出结构化审核报告，包含 overall_verdict (PASS/NEEDS_REVISION/REJECT) 和可执行的修复意见。
    """,
    tools=[static_analysis, rag_query],
    guardrails=[riscv_spec_guardrail, security_guardrail, style_guardrail],
)

tester_agent = Agent(
    name="tester",
    model="gpt-4.1",
    instructions="""
    你是 RISC-V 测试工程师。搭建 QEMU 环境并执行全面验证：
    单元测试、集成测试、仿真测试、性能基准。
    环境搭建失败时尝试备用镜像或配置。
    """,
    tools=[qemu_ctl, test_runner],
    sandbox=SandboxConfig(
        provider="e2b",  # 或 modal / cloudflare / daytona / runloop / vercel / blaxel
        image="rvinsights/qemu-riscv:rv64gc-2026q2",
        resources={"cpu": 4, "memory": "8g", "timeout": 3600},
        network={"egress": ["github.com", "cdn.kernel.org"]},
    ),
)

# === 人工审核 Agent (特殊 Agent，仅用于 interrupt 恢复) ===
human_review_agent = Agent(
    name="human_review",
    model="gpt-4.1",  # 用于生成审核摘要供人类参考
    instructions="""
    你是人工审核辅助 Agent。当工作流到达人工审核节点时，
    生成清晰的阶段产物摘要，帮助人类审核者快速理解当前状态并做出决策。
    """,
)

# === Orchestrator Agent (总指挥) ===
orchestrator_agent = Agent(
    name="orchestrator",
    model="gpt-4.1",
    instructions="""
    你是 RV-Insights 工作流 Orchestrator。管理五阶段流转：
    INITIALIZATION → EXPLORATION → PLANNING → DEVELOPMENT → REVIEW → TESTING → COMPLETION。
    在每个主要阶段完成后触发 interrupt 等待人工审核。
    开发-审核迭代由条件 Handoff 控制，达到 MAX_ITERATIONS 时强制退出到人工审核。
    """,
    # Orchestrator 的 handoffs 在运行时动态配置
)
```

### 1.4 条件 Handoff 定义

```python
from agents import handoff, HandoffCondition
from typing import Dict, Any

# === 全局 Handoff 链 ===
# 注意：OpenAI Agents SDK 的 handoff 是显式委托，由当前 Agent 决定下一个 Agent

# 探索 -> 人工审核探索 (探索完成后由 Orchestrator 触发 interrupt)
explorer_agent.handoffs = [
    handoff(
        target=orchestrator_agent,
        condition=HandoffCondition.AFTER_COMPLETION,
        metadata={"next_stage": "HUMAN_REVIEW_EXPLORATION"}
    )
]

# 规划 -> 人工审核规划
planner_agent.handoffs = [
    handoff(
        target=orchestrator_agent,
        condition=HandoffCondition.AFTER_COMPLETION,
        metadata={"next_stage": "HUMAN_REVIEW_PLANNING"}
    )
]

# 开发 -> 审核 (核心迭代循环的入口)
developer_agent.handoffs = [
    handoff(
        target=reviewer_agent,
        condition=HandoffCondition.AFTER_COMPLETION,
        metadata={"trigger": "dev_complete"}
    )
]

# 审核 -> 条件分支 (核心：迭代循环)
def review_routing_condition(context: Dict[str, Any]) -> str:
    """
    审核结果路由条件函数。
    根据审核结果和迭代次数决定下一跳。

    返回: "PASS" | "NEEDS_REVISION" | "REJECT" | "MAX_ITERATIONS"
    """
    review_result = context.get("review_result", {})
    verdict = review_result.get("overall_verdict", "NEEDS_REVISION")
    iteration = context.get("dev_review_iteration_count", 0)
    max_iter = context.get("max_dev_review_iterations", 5)

    if verdict == "PASS":
        # Guardrails 二次校验：即使 verdict 为 PASS，检查是否存在 blocking issue
        blocking_issues = [
            issue for issue in review_result.get("issues", [])
            if issue.get("blocking", False)
        ]
        if blocking_issues:
            # Guardrails 拦截：存在 blocking issue 但 verdict 为 PASS，降级为 NEEDS_REVISION
            return "NEEDS_REVISION"
        return "PASS"

    if verdict == "REJECT":
        return "REJECT"

    # NEEDS_REVISION 分支
    if iteration >= max_iter:
        return "MAX_ITERATIONS"

    return "NEEDS_REVISION"

reviewer_agent.handoffs = [
    # PASS: 审核通过，进入人工审核代码
    handoff(
        target=orchestrator_agent,
        condition=lambda ctx: review_routing_condition(ctx) == "PASS",
        metadata={"next_stage": "HUMAN_REVIEW_CODE", "reason": "review_passed"}
    ),
    # REJECT: 审核拒绝，进入人工审核代码
    handoff(
        target=orchestrator_agent,
        condition=lambda ctx: review_routing_condition(ctx) == "REJECT",
        metadata={"next_stage": "HUMAN_REVIEW_CODE", "reason": "review_rejected"}
    ),
    # NEEDS_REVISION: 需要修复，Handoff 回开发 Agent
    handoff(
        target=developer_agent,
        condition=lambda ctx: review_routing_condition(ctx) == "NEEDS_REVISION",
        metadata={"trigger": "revision_required", "increment_iteration": True}
    ),
    # MAX_ITERATIONS: 达到最大迭代次数，强制进入人工审核
    handoff(
        target=orchestrator_agent,
        condition=lambda ctx: review_routing_condition(ctx) == "MAX_ITERATIONS",
        metadata={"next_stage": "HUMAN_REVIEW_CODE", "reason": "max_iterations_reached"}
    ),
]

# 测试 -> 人工审核测试
tester_agent.handoffs = [
    handoff(
        target=orchestrator_agent,
        condition=HandoffCondition.AFTER_COMPLETION,
        metadata={"next_stage": "HUMAN_REVIEW_TESTING"}
    )
]
```

### 1.5 人工审核节点的 Interrupt 定义

OpenAI Agents SDK 的 `interrupt` 是原生机制，在 Agent 执行完成后暂停工作流，等待外部输入恢复。

```python
from agents import Session, interrupt, ResumeCommand
from typing import Dict, Any, Literal
import json

# === Interrupt 配置 ===
# 每个主要阶段完成后触发 interrupt，等待人类审核

INTERRUPT_CONFIGS = {
    "HUMAN_REVIEW_EXPLORATION": {
        "message_template": "探索阶段完成，请审核贡献机会报告。",
        "artifacts": ["exploration_report.json"],
        "allowed_decisions": ["APPROVE", "REJECT", "REQUEST_CHANGES", "ADD_NOTES"],
        "next_agent_map": {
            "APPROVE": "planner",
            "REJECT": "finalize",
            "REQUEST_CHANGES": "explorer",
            "ADD_NOTES": "planner",
        },
        "required_fields": {
            "APPROVE": ["selected_opportunity_id"],  # 必须指定选中哪个机会
            "REQUEST_CHANGES": ["comment"],
        },
    },
    "HUMAN_REVIEW_PLANNING": {
        "message_template": "规划阶段完成，请审核开发测试方案。",
        "artifacts": ["development_plan.md", "testing_plan.md"],
        "allowed_decisions": ["APPROVE", "REJECT", "REQUEST_CHANGES", "ADD_NOTES"],
        "next_agent_map": {
            "APPROVE": "developer",
            "REJECT": "finalize",
            "REQUEST_CHANGES": "planner",
            "ADD_NOTES": "developer",
        },
        "required_fields": {
            "REQUEST_CHANGES": ["comment"],
        },
    },
    "HUMAN_REVIEW_CODE": {
        "message_template": "开发-审核迭代完成，请审核最终代码变更。",
        "artifacts": ["final_patch.diff", "review_report.json", "iteration_history.json"],
        "allowed_decisions": ["APPROVE", "REJECT", "REQUEST_CHANGES", "ADD_NOTES"],
        "next_agent_map": {
            "APPROVE": "tester",
            "REJECT": "finalize",
            "REQUEST_CHANGES": "developer",
            "ADD_NOTES": "tester",
        },
        "required_fields": {
            "REQUEST_CHANGES": ["comment"],
        },
        # 特殊：如果从 MAX_ITERATIONS 进入，显示警告
        "warning_conditions": ["max_iterations_reached"],
    },
    "HUMAN_REVIEW_TESTING": {
        "message_template": "测试阶段完成，请审核测试报告。",
        "artifacts": ["test_report.json", "build_logs.tar.gz"],
        "allowed_decisions": ["APPROVE", "REJECT", "REQUEST_CHANGES", "ADD_NOTES"],
        "next_agent_map": {
            "APPROVE": "finalize",
            "REJECT": "finalize",
            "REQUEST_CHANGES": "developer",
            "ADD_NOTES": "finalize",
        },
        "required_fields": {
            "REQUEST_CHANGES": ["comment"],
        },
    },
}

async def trigger_human_review(
    session: Session,
    stage: Literal[
        "HUMAN_REVIEW_EXPLORATION",
        "HUMAN_REVIEW_PLANNING",
        "HUMAN_REVIEW_CODE",
        "HUMAN_REVIEW_TESTING",
    ],
    context: Dict[str, Any],
) -> ResumeCommand:
    """
    触发人工审核 interrupt。

    流程:
    1. 生成审核摘要
    2. 调用 interrupt() 暂停工作流
    3. 通过 SSE 推送通知到 UI
    4. 等待人类提交决策
    5. 验证决策合法性
    6. 返回 ResumeCommand 恢复工作流
    """
    config = INTERRUPT_CONFIGS[stage]

    # 生成审核摘要 (供 UI 快速展示)
    summary = await generate_review_summary(stage, context)

    # 调用 OpenAI SDK 原生 interrupt
    result = await interrupt(
        agent=human_review_agent,
        message=config["message_template"],
        metadata={
            "stage": stage,
            "artifacts": config["artifacts"],
            "summary": summary,
            "session_id": session.session_id,
        },
    )

    # result 包含人类的决策 (通过 UI -> API -> resume 链路传入)
    decision = result.decision
    comment = result.get("comment", "")
    selected_opportunity_id = result.get("selected_opportunity_id")

    # 验证决策合法性
    if decision not in config["allowed_decisions"]:
        raise InvalidDecisionError(
            f"Decision '{decision}' not allowed for stage {stage}. "
            f"Allowed: {config['allowed_decisions']}"
        )

    # 验证必填字段
    required = config["required_fields"].get(decision, [])
    for field in required:
        if not result.get(field):
            raise InvalidDecisionError(
                f"Field '{field}' is required for decision '{decision}'"
            )

    # 确定下一个 Agent
    next_agent_name = config["next_agent_map"][decision]

    # 构建 ResumeCommand
    resume_cmd = ResumeCommand(
        decision=decision,
        comment=comment,
        next_agent=next_agent_name,
        selected_opportunity_id=selected_opportunity_id,
        # 将人类决策追加到会话状态
        state_updates={
            "human_decisions": context.get("human_decisions", []) + [{
                "stage": stage,
                "decision": decision,
                "comment": comment,
                "selected_opportunity_id": selected_opportunity_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }],
            "status": "running",
        }
    )

    return resume_cmd
```

### 1.6 Handoff 时的状态传递

OpenAI Agents SDK 的 Handoff 通过 `Session` 对象的共享状态实现上下文传递。关键设计：从 Explorer 到 Planner 传递 `selected_opportunity`。

```python
from agents import Session, Context
from typing import Dict, Any

class RVInsightsContext(Context):
    """
    RV-Insights 专用上下文类。
    继承 OpenAI SDK 的 Context，增加应用层状态字段。
    """
    # === 会话元数据 ===
    session_id: str
    tenant_id: str
    created_at: str
    current_stage: str
    status: str

    # === 各阶段产物 ===
    exploration_result: Dict[str, Any]
    planning_result: Dict[str, Any]
    development_result: Dict[str, Any]
    review_result: Dict[str, Any]
    testing_result: Dict[str, Any]

    # === 迭代控制 ===
    dev_review_iteration_count: int
    max_dev_review_iterations: int

    # === 人工审核记录 ===
    human_decisions: list
    human_notes: list

    # === 审计与追踪 ===
    agent_logs: list
    timestamps: list

    # === 错误与恢复 ===
    last_error: Dict[str, Any]
    retry_count: int

    # === 资源与锁 ===
    workspace_path: str
    git_lock_id: str
    qemu_instance_id: str

    # === Handoff 专用传递字段 ===
    # 从 Explorer -> Planner: 人类选中的机会
    selected_opportunity: Dict[str, Any]
    # 从 Planner -> Developer: 开发方案
    development_plan: Dict[str, Any]
    # 从 Reviewer -> Developer (NEEDS_REVISION): 修复意见
    revision_notes: Dict[str, Any]
    # 增量审核: 历史 patch 列表
    patch_history: list

async def handoff_with_context(
    session: Session,
    from_agent: Agent,
    to_agent: Agent,
    context_updates: Dict[str, Any],
) -> None:
    """
    执行 Handoff，确保上下文正确传递。

    关键传递规则:
    1. 全量状态复制: Session 的 Context 在 Handoff 时完整传递
    2. 增量更新: context_updates 中的字段覆盖或追加
    3. 产物归档: 大字段（如 patch 内容）写入 S3，Context 中只保留引用
    4. 审计日志: 每次 Handoff 记录到 agent_logs
    """
    # 更新上下文
    for key, value in context_updates.items():
        setattr(session.context, key, value)

    # 大字段归档 (避免 Context 膨胀)
    if "patch_content" in context_updates:
        patch_key = f"sessions/{session.context.tenant_id}/{session.context.session_id}/patches/iter_{session.context.dev_review_iteration_count}.diff"
        await archive_to_s3(context_updates["patch_content"], patch_key)
        session.context.patch_history.append({
            "iteration": session.context.dev_review_iteration_count,
            "s3_key": patch_key,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # 从 Context 中移除大字段，只保留引用
        delattr(session.context, "patch_content")

    # 记录 Handoff 日志
    session.context.agent_logs.append({
        "event": "HANDOFF",
        "from": from_agent.name,
        "to": to_agent.name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "context_keys": list(context_updates.keys()),
    })

    # 执行 Handoff
    await session.handoff(to_agent)
```

---

## 2. 开发-审核迭代子图（核心）

开发-审核迭代是系统最复杂的部分。在 v2 中，该子图通过 OpenAI Agents SDK 的条件 Handoff + Claude Subagent 修复注入实现。

### 2.1 子图架构

```mermaid
graph TD
    subgraph "Dev-Review Iteration Subgraph (OpenAI Agents SDK)"
        ENTRY["子图入口<br/>接收 Development Plan + Context"] --> DEV["开发Agent<br/>Claude Code / Managed Agents"]

        DEV -->|输出 Patch + Build Status| REV["审核Agent<br/>Codex + Guardrails"]

        REV -->|输出 Review Report| ROUTE{"OpenAI 条件 Handoff<br/>route_review()"}

        ROUTE -->|PASS| EXIT_PASS["子图出口: PASS<br/>进入 HUMAN_REVIEW_CODE"]
        ROUTE -->|REJECT| EXIT_REJECT["子图出口: REJECT<br/>进入 HUMAN_REVIEW_CODE"]

        ROUTE -->|NEEDS_REVISION<br/>iter < MAX| INJECT["修复意见注入<br/>Claude Subagent 上下文构建"]
        INJECT --> DEV

        ROUTE -->|NEEDS_REVISION<br/>iter >= MAX| EXIT_MAX["子图出口: MAX_ITERATIONS<br/>强制进入 HUMAN_REVIEW_CODE"]
    end

    style DEV fill:#e1f5e1,stroke:#2e7d32,stroke-width:2px
    style REV fill:#fff2e1,stroke:#ef6c00,stroke-width:2px
    style ROUTE fill:#e1f0ff,stroke:#1565c0,stroke-width:2px
    style INJECT fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
```

### 2.2 子图状态定义

子图状态继承全局状态，增加局部迭代专用字段。

```python
from typing import TypedDict, Optional, List, Dict, Any
from dataclasses import dataclass

class DevReviewSubState(TypedDict):
    """
    开发-审核迭代子图状态。
    继承全局 RVInsightsContext 的所有字段，增加子图局部字段。
    """
    # === 继承自全局状态 (完整复制) ===
    session_id: str
    tenant_id: str
    workspace_path: str
    development_plan: Dict[str, Any]
    # ... (其他全局字段)

    # === 子图局部字段 ===
    # 局部迭代计数器 (与全局 dev_review_iteration_count 同步)
    local_iteration_count: int

    # 增量审核上下文
    previous_patches: List[str]  # 历史 patch 的 S3 引用列表
    review_history: List[Dict[str, Any]]  # 历史审核报告列表

    # 当前迭代产物
    current_patch: Optional[str]  # 当前 patch 内容 (大字段，迭代结束后归档)
    current_build_log: Optional[str]
    current_review_report: Optional[Dict[str, Any]]

    # 开发 Agent 内部状态
    build_attempts: int  # 开发Agent内部编译自修复次数
    last_build_status: Optional[Literal["SUCCESS", "FAILED", "PENDING"]]

    # 修复注入上下文
    revision_injection: Optional[Dict[str, Any]]  # 注入开发Agent的修复意见

    # 子图入口时间戳
    subgraph_entered_at: str
```

### 2.3 条件 Handoff 实现迭代循环

```python
from agents import Agent, handoff, Session
from typing import Dict, Any, Literal

# === 子图内 Agent 定义 ===
# 开发 Agent (子图专用实例，与全局 developer_agent 配置相同但上下文隔离)
subgraph_developer = Agent(
    name="subgraph_developer",
    model="claude-sonnet-4-5",  # [假设：2026 Q2 模型版本]
    # provider="anthropic",  # 伪代码参数，实际通过 Claude SDK 直接调用
    instructions="""
    你是开发 Agent (迭代模式)。根据 development_plan 和 revision_injection 实现代码变更。

    上下文规则:
    1. 如果是首次迭代 (local_iteration_count == 0): 按 development_plan 全新实现
    2. 如果是修复迭代 (local_iteration_count > 0):
       - 读取 previous_patches 了解已做变更
       - 严格按 revision_injection 中的修复意见修改
       - 不要回退已解决的问题
    3. 每次迭代输出完整 patch (不是增量 patch)
    4. 编译失败时内部自修复最多 3 次
    """,
    tools=[bash, file_editor, git_commit, static_analysis],
)

# 审核 Agent (子图专用实例)
subgraph_reviewer = Agent(
    name="subgraph_reviewer",
    model="codex",
    instructions="""
    你是审核 Agent (迭代模式)。对代码变更进行多维度审查。

    增量审核规则:
    1. 首次迭代: 审核完整代码
    2. 后续迭代: 只关注当前 patch 与 previous_patches[-1] 的 diff
       - 检查修复意见是否被正确执行
       - 检查是否引入新问题
       - 已解决的问题不再重复报告
    3. 输出 overall_verdict 和具体修复意见
    """,
    tools=[static_analysis, rag_query, git_diff],  # git_diff 用于增量审核
    guardrails=[riscv_spec_guardrail, security_guardrail, style_guardrail],
)

# === 条件 Handoff: 审核 -> 路由判断 ===
async def route_review_condition(session: Session) -> str:
    """
    审核结果路由条件函数。
    这是迭代循环的核心控制逻辑。
    """
    ctx = session.context
    review_result = ctx.get("current_review_report", {})
    verdict = review_result.get("overall_verdict", "NEEDS_REVISION")
    iteration = ctx.get("local_iteration_count", 0)
    max_iter = ctx.get("max_dev_review_iterations", 5)

    # Guardrails 二次校验
    if verdict == "PASS":
        blocking_issues = [
            issue for issue in review_result.get("issues", [])
            if issue.get("blocking", False)
        ]
        if blocking_issues:
            # 降级为 NEEDS_REVISION
            verdict = "NEEDS_REVISION"
            review_result["overall_verdict"] = "NEEDS_REVISION"
            review_result["guardrails_intercepted"] = True
            review_result["guardrails_reason"] = f"Found {len(blocking_issues)} blocking issues despite PASS verdict"

    # 记录路由决策日志
    ctx["agent_logs"].append({
        "event": "ROUTE_REVIEW",
        "iteration": iteration,
        "raw_verdict": review_result.get("original_verdict", verdict),
        "final_verdict": verdict,
        "guardrails_intercepted": review_result.get("guardrails_intercepted", False),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    if verdict == "PASS":
        return "PASS"
    if verdict == "REJECT":
        return "REJECT"
    if iteration >= max_iter:
        return "MAX_ITERATIONS"
    return "NEEDS_REVISION"

# === 子图 Handoff 定义 ===
subgraph_reviewer.handoffs = [
    # PASS: 审核通过，退出子图
    handoff(
        target=subgraph_exit_agent,
        condition=lambda session: route_review_condition(session) == "PASS",
        metadata={"exit_reason": "PASS", "final_iteration": True}
    ),
    # REJECT: 审核拒绝，退出子图
    handoff(
        target=subgraph_exit_agent,
        condition=lambda session: route_review_condition(session) == "REJECT",
        metadata={"exit_reason": "REJECT", "final_iteration": True}
    ),
    # NEEDS_REVISION: 继续迭代
    handoff(
        target=subgraph_developer,
        condition=lambda session: route_review_condition(session) == "NEEDS_REVISION",
        metadata={"trigger": "revision_required", "increment_iteration": True}
    ),
    # MAX_ITERATIONS: 强制退出
    handoff(
        target=subgraph_exit_agent,
        condition=lambda session: route_review_condition(session) == "MAX_ITERATIONS",
        metadata={"exit_reason": "MAX_ITERATIONS", "final_iteration": True}
    ),
]
```

### 2.4 Claude Subagent 修复注入

当审核 Agent 报出 NEEDS_REVISION 时，需要将修复意见注入 Claude 开发 Agent 的上下文。这是跨 SDK 协作的关键点。

```python
from anthropic import Anthropic
from typing import Dict, Any, List

async def build_revision_injection(
    session: Session,
    review_report: Dict[str, Any],
    iteration: int,
) -> Dict[str, Any]:
    """
    构建注入 Claude 开发 Agent 的修复意见上下文。

    策略:
    1. 提取所有 blocking issue 和高优先级 issue
    2. 按文件分组，生成结构化修复指令
    3. 附带历史 patch 引用，确保开发 Agent 了解已做变更
    4. 使用 Claude Subagent 对复杂修复意见进行预处理 (可选增强)
    """
    ctx = session.context

    # 提取需要修复的 issues
    issues_to_fix = [
        issue for issue in review_report.get("issues", [])
        if issue.get("blocking", False) or issue.get("severity") in ["HIGH", "CRITICAL"]
    ]

    # 按文件分组
    issues_by_file: Dict[str, List[Dict]] = {}
    for issue in issues_to_fix:
        file_path = issue.get("file_path", "unknown")
        issues_by_file.setdefault(file_path, []).append(issue)

    # 构建修复指令
    revision_instructions = []
    for file_path, issues in issues_by_file.items():
        revision_instructions.append(f"\n### 文件: {file_path}")
        for idx, issue in enumerate(issues, 1):
            revision_instructions.append(
                f"{idx}. [{issue['severity']}] {issue['description']}\n"
                f"   建议修复: {issue.get('suggested_fix', '见规范引用')}\n"
                f"   规范引用: {issue.get('spec_reference', 'N/A')}"
            )

    # 历史上下文
    history_context = ""
    if iteration > 0:
        history_context = f"""
## 迭代历史
当前为第 {iteration + 1} 次迭代。
历史 patch 列表: {ctx.get('previous_patches', [])}
历史审核报告: {ctx.get('review_history', [])}

重要: 请确保本次修复不引入新问题，不回退已解决的问题。
"""

    # 构建完整注入内容
    injection = {
        "iteration": iteration + 1,
        "total_issues": len(issues_to_fix),
        "blocking_issues": len([i for i in issues_to_fix if i.get("blocking")]),
        "revision_instructions": "\n".join(revision_instructions),
        "history_context": history_context,
        "review_verdict": review_report.get("overall_verdict"),
        "review_summary": review_report.get("summary", ""),
    }

    # === 可选增强: 使用 Claude Subagent 预处理复杂修复意见 ===
    # 当修复意见涉及复杂重构时，调用 Claude Subagent 生成更详细的修复步骤
    complex_issues = [i for i in issues_to_fix if i.get("complexity") == "HIGH"]
    if complex_issues:
        subagent_fix_plan = await claude_subagent_generate_fix_plan(
            issues=complex_issues,
            current_patch=ctx.get("current_patch"),
            development_plan=ctx.get("development_plan"),
        )
        injection["subagent_fix_plan"] = subagent_fix_plan

    return injection

async def claude_subagent_generate_fix_plan(
    issues: List[Dict[str, Any]],
    current_patch: str,
    development_plan: Dict[str, Any],
) -> Dict[str, Any]:
    """
    使用 Claude Subagent 对复杂修复意见生成详细修复计划。

    这是 Claude Agent SDK 的 Subagent 调用示例。
    利用 Claude 的 200K 上下文和深度推理能力，将模糊的审核意见转化为可执行的步骤。
    """
    from anthropic.agents import Subagent

    fix_planner = Subagent(
        model="claude-sonnet-4-5",
        instructions="""
        你是修复计划生成专家。根据审核意见和当前代码，生成详细的修复步骤。
        输出格式：
        1. 问题根因分析
        2. 修复步骤（具体到函数/行号）
        3. 验证方法（如何确认修复成功）
        4. 风险提示（可能引入的副作用）
        """,
        max_tokens=8000,
    )

    prompt = f"""
    审核意见:
    {json.dumps(issues, indent=2, ensure_ascii=False)}

    当前代码 patch:
    ```diff
    {current_patch[:50000]}  # 截断至 50K tokens
    ```

    开发方案:
    {json.dumps(development_plan, indent=2, ensure_ascii=False)}

    请生成详细修复计划。
    """

    result = await fix_planner.run(prompt)
    return {
        "plan": result.content,
        "estimated_steps": result.content.count("Step "),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

# === 修复注入到开发 Agent 上下文 ===
async def inject_revision_to_developer(
    session: Session,
    review_report: Dict[str, Any],
) -> None:
    """
    将修复意见注入开发 Agent 的上下文，准备下一次迭代。
    """
    ctx = session.context
    iteration = ctx.get("local_iteration_count", 0)

    # 构建注入内容
    injection = await build_revision_injection(session, review_report, iteration)

    # 归档当前 patch 到历史
    if ctx.get("current_patch"):
        ctx.setdefault("previous_patches", []).append({
            "iteration": iteration,
            "content_ref": await archive_patch(ctx["current_patch"], session),
        })

    # 归档当前审核报告
    ctx.setdefault("review_history", []).append({
        "iteration": iteration,
        "report": review_report,
    })

    # 更新迭代计数
    ctx["local_iteration_count"] = iteration + 1
    ctx["dev_review_iteration_count"] = iteration + 1  # 同步全局计数器

    # 注入修复意见到上下文
    ctx["revision_injection"] = injection

    # 清空当前迭代产物 (准备下一轮)
    ctx["current_patch"] = None
    ctx["current_build_log"] = None
    ctx["current_review_report"] = None
```

### 2.5 增量审核机制

审核 Agent 在后续迭代中只关注变更 diff，减少 Token 消耗并提高审核精度。

```python
async def incremental_review(
    session: Session,
    current_patch: str,
    review_report: Dict[str, Any],
) -> Dict[str, Any]:
    """
    增量审核：审核 Agent 只关注当前 patch 与上一版本的 diff。

    实现:
    1. 从历史中获取上一版本的 patch
    2. 计算 diff
    3. 审核 Agent 的 instructions 中注入增量审核提示
    4. 输出只包含新增/变更问题的审核报告
    """
    ctx = session.context
    iteration = ctx.get("local_iteration_count", 0)

    if iteration == 0:
        # 首次迭代：审核完整代码
        return await full_review(session, current_patch)

    # 获取上一版本 patch
    previous_patches = ctx.get("previous_patches", [])
    if not previous_patches:
        # 无历史，回退到完整审核
        return await full_review(session, current_patch)

    last_patch_ref = previous_patches[-1]["content_ref"]
    last_patch = await load_patch_from_s3(last_patch_ref)

    # 计算 diff
    patch_diff = compute_patch_diff(last_patch, current_patch)

    # 构建增量审核提示
    incremental_prompt = f"""
    ## 增量审核模式 (第 {iteration + 1} 次迭代)

    你只需要关注以下变更 diff，不需要重新审核未变更的代码：

    ```diff
    {patch_diff}
    ```

    上一版本的审核意见:
    {json.dumps(ctx.get("review_history", [])[-1], indent=2)}

    审核重点:
    1. 修复意见是否被正确执行
    2. 变更是否引入新问题
    3. 未变更部分无需重复报告

    输出格式与完整审核相同，但只包含新增/变更的问题。
    """

    # 调用审核 Agent (使用增量提示覆盖默认 instructions)
    result = await subgraph_reviewer.run(
        input=incremental_prompt,
        override_instructions=subgraph_reviewer.instructions + "\n" + incremental_prompt,
    )

    return result
```

### 2.6 强制退出机制

达到 `MAX_ITERATIONS` 时，OpenAI Orchestrator 强制 Handoff 到人工审核。

```python
async def enforce_max_iterations(
    session: Session,
    review_report: Dict[str, Any],
) -> Dict[str, Any]:
    """
    强制退出：达到最大迭代次数时的处理。

    流程:
    1. 生成强制退出报告，汇总所有迭代的历史
    2. 标记状态为 MAX_ITERATIONS_REACHED
    3. 附加警告信息供人工审核时参考
    4. 退出子图，Handoff 到 HUMAN_REVIEW_CODE
    """
    ctx = session.context
    max_iter = ctx.get("max_dev_review_iterations", 5)

    # 生成迭代历史汇总
    iteration_summary = {
        "total_iterations": ctx.get("local_iteration_count", 0),
        "max_allowed": max_iter,
        "review_history": ctx.get("review_history", []),
        "patch_history": ctx.get("previous_patches", []),
        "final_verdict": review_report.get("overall_verdict"),
        "unresolved_issues": [
            issue for issue in review_report.get("issues", [])
            if issue.get("blocking", False)
        ],
        "warning": f"开发-审核迭代达到最大次数 ({max_iter})，未能自动收敛。"
                   f"请人工审核决定是否接受当前代码、要求继续修改或终止会话。",
    }

    # 更新审核报告
    review_report["max_iterations_reached"] = True
    review_report["iteration_summary"] = iteration_summary
    review_report["overall_verdict"] = "MAX_ITERATIONS"  # 强制修改 verdict

    # 记录日志
    ctx["agent_logs"].append({
        "event": "MAX_ITERATIONS_ENFORCED",
        "iteration": ctx["local_iteration_count"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return review_report
```

---

## 3. 错误分类与重试策略

### 3.1 错误分类矩阵

| 错误类型 | 示例 | 可重试 | 节点级处理 | 全局处理 | SDK 来源 |
|----------|------|--------|------------|----------|----------|
| LLM API 限流 | `429 Too Many Requests` | 是 | 指数退避重试 | 记录告警 | OpenAI / Claude |
| LLM API 超时 | `504 Gateway Timeout` | 是 | 指数退避重试 | 记录告警 | OpenAI / Claude |
| LLM 内容过滤 | `content_filter_triggered` | **否** | 修改提示词重试 1 次 | 转人工审核 | OpenAI / Claude |
| 网络超时 | GitHub API 连接超时 | 是 | 指数退避重试 | 记录告警 | 通用 |
| 代码编译失败 | `make ARCH=riscv` 报错 | **否** | 开发 Agent 自修复 3 次 | 转人工审核 | Claude SDK |
| 沙箱崩溃 | Firecracker MicroVM panic | **否** | 清理并快速失败 | 通知运维 | OpenAI Sandbox |
| 沙箱启动失败 | E2B 环境初始化超时 | 是 (备用提供商) | 切换沙箱提供商 | 通知运维 | OpenAI Sandbox |
| 静态分析错误 | `sparse` 报告严重问题 | **否** | 记录到结果 | 转审核 Agent | MCP Server |
| RAG 查询失败 | 向量数据库连接断开 | 是 | 指数退避重试 | 降级到直连 | MCP Server |
| Git 操作失败 | 分支冲突、权限不足 | **否** | 记录错误详情 | 转人工 | Git CLI |
| QEMU 启动失败 | 镜像损坏、资源不足 | 是 (备用镜像) | 尝试备用方案 | 通知运维 | MCP Server |
| Guardrails 拦截 | 输出违反 RISC-V 规则 | **否** | 自动降级为 NEEDS_REVISION | 记录审计日志 | OpenAI SDK |
| Handoff 失败 | 目标 Agent 未响应 | 是 | 重试 Handoff 2 次 | 记录告警 | OpenAI SDK |
| Session 状态损坏 | PostgreSQL 写入失败 | 是 | 重试 3 次 | 通知运维 | OpenAI SDK |

### 3.2 错误处理装饰器

```python
import time
import random
import asyncio
from functools import wraps
from typing import Type, Callable, Any

# === 错误基类 ===
class RVIError(Exception):
    """RV-Insights 基础异常。"""
    pass

class RetryableError(RVIError):
    """可重试错误基类。"""
    pass

class NonRetryableError(RVIError):
    """不可重试错误基类。"""
    pass

# === SDK 特定错误映射 ===
class OpenAIRateLimitError(RetryableError):
    """OpenAI API 限流。"""
    pass

class OpenAIContentFilterError(NonRetryableError):
    """OpenAI 内容过滤触发。"""
    pass

class ClaudeRateLimitError(RetryableError):
    """Claude API 限流。"""
    pass

class SandboxCrashError(NonRetryableError):
    """沙箱崩溃。"""
    pass

class SandboxProviderSwitchError(RetryableError):
    """沙箱提供商切换 (可重试)。"""
    pass

class CompilationError(NonRetryableError):
    """编译错误。"""
    pass

class GitOperationError(NonRetryableError):
    """Git 操作错误。"""
    pass

class GuardrailsInterceptError(NonRetryableError):
    """Guardrails 拦截。"""
    pass

# === 指数退避重试装饰器 ===
def exponential_backoff_retry(
    base: float = 2.0,
    max_retries: int = 3,
    max_delay: float = 60.0,
    retryable_exceptions: tuple = (RetryableError,),
):
    """
    节点级指数退避重试装饰器。
    仅对 retryable_exceptions 中指定的异常触发重试。

    适用于 OpenAI Agents SDK 的 Agent 函数和工具函数。
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_error = e
                    if attempt >= max_retries:
                        break

                    # 指数退避 + 随机抖动
                    delay = min(base ** attempt + random.uniform(0, 1), max_delay)
                    await asyncio.sleep(delay)

                    # 记录重试日志
                    if args and hasattr(args[0], "context"):
                        args[0].context.setdefault("agent_logs", []).append({
                            "event": "RETRY",
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "delay": delay,
                            "error": str(e),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })

                except NonRetryableError:
                    # 不可重试错误立即抛出
                    raise

            # 达到最大重试次数
            raise MaxRetriesExceededError(
                f"Function {func.__name__} failed after {max_retries} retries: {last_error}"
            )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 同步版本 (用于非 async 上下文)
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_error = e
                    if attempt >= max_retries:
                        break
                    delay = min(base ** attempt + random.uniform(0, 1), max_delay)
                    time.sleep(delay)
                except NonRetryableError:
                    raise

            raise MaxRetriesExceededError(
                f"Function {func.__name__} failed after {max_retries} retries: {last_error}"
            )

        # 根据被装饰函数是否为 async 返回对应 wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator

# === 应用装饰器到各节点 ===
@exponential_backoff_retry(base=2, max_retries=3, max_delay=60.0)
async def run_exploration_agent(session: Session) -> Dict[str, Any]:
    """探索 Agent 执行 (可重试)。"""
    ...

@exponential_backoff_retry(base=2, max_retries=3, max_delay=60.0)
async def run_planning_agent(session: Session) -> Dict[str, Any]:
    """规划 Agent 执行 (可重试)。"""
    ...

@exponential_backoff_retry(base=2, max_retries=3, max_delay=60.0)
async def run_development_agent(session: Session) -> Dict[str, Any]:
    """开发 Agent 执行 (可重试)。"""
    ...

@exponential_backoff_retry(base=2, max_retries=3, max_delay=60.0)
async def run_review_agent(session: Session) -> Dict[str, Any]:
    """审核 Agent 执行 (可重试)。"""
    ...

@exponential_backoff_retry(base=2, max_retries=3, max_delay=60.0)
async def run_testing_agent(session: Session) -> Dict[str, Any]:
    """测试 Agent 执行 (可重试)。"""
    ...
```

### 3.3 死信队列 (DLQ) 实现

```python
from datetime import datetime, timezone
from typing import Dict, Any
import json

async def send_to_dlq(
    session: Session,
    error: Exception,
    failed_agent: str,
) -> None:
    """
    将达到最大重试次数的任务发送到死信队列。
    通知运维团队进行人工干预。
    """
    ctx = session.context

    dlq_record = {
        "session_id": ctx.get("session_id"),
        "tenant_id": ctx.get("tenant_id"),
        "current_stage": ctx.get("current_stage"),
        "failed_agent": failed_agent,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "stack_trace": getattr(error, "__traceback__", None),
        "state_snapshot": {
            k: v for k, v in ctx.items()
            if k not in ["agent_logs", "current_patch", "patch_history"]
        },
        "enqueued_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending_review",
        "sdk_source": "openai" if "openai" in str(type(error)).lower() else "claude",
    }

    # 写入 DLQ 表 (PostgreSQL)
    await db.execute("""
        INSERT INTO dead_letter_queue (
            session_id, tenant_id, current_stage, failed_agent,
            error_type, error_message, stack_trace, state_snapshot,
            enqueued_at, status, sdk_source
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
        )
    """, [
        dlq_record["session_id"], dlq_record["tenant_id"],
        dlq_record["current_stage"], dlq_record["failed_agent"],
        dlq_record["error_type"], dlq_record["error_message"],
        json.dumps(dlq_record["stack_trace"]),
        json.dumps(dlq_record["state_snapshot"]),
        dlq_record["enqueued_at"], dlq_record["status"],
        dlq_record["sdk_source"],
    ])

    # 发送运维告警
    await alert_ops_team(
        title=f"[RV-Insights] DLQ Alert: Session {ctx['session_id']} failed at {ctx['current_stage']}",
        severity="high",
        context=dlq_record,
    )

    # 更新会话状态为 failed
    await db.execute(
        "UPDATE rvinsights_sessions SET status = 'failed', failed_at = NOW() WHERE session_id = $1",
        (ctx["session_id"],)
    )

    # 释放所有资源
    await cleanup_session_resources(session)

class MaxRetriesExceededError(NonRetryableError):
    """达到最大重试次数。"""
    pass
```

### 3.4 部分失败处理 (探索 Agent)

```python
async def run_exploration_with_partial_failure_handling(
    session: Session,
) -> Dict[str, Any]:
    """
    探索 Agent 的部分失败处理。

    OpenAI Agents SDK 并发调度多个子 Agent (MailScanner, IssueMiner, CodeAnalyst)。
    当部分子 Agent 失败时，根据租户策略决定整体行为。
    """
    ctx = session.context
    tenant_config = await load_tenant_config(ctx["tenant_id"])
    partial_policy = tenant_config.get("exploration_partial_failure_policy", "continue")

    # 并发启动子 Agent
    sub_agents = [
        ("MailScanner", run_mail_scanner),
        ("IssueMiner", run_issue_miner),
        ("CodeAnalyst", run_code_analyst),
    ]

    results = {}
    failed_agents = []

    # 使用 asyncio.gather 并发执行，return_exceptions=True 捕获异常
    tasks = [agent_func(session) for _, agent_func in sub_agents]
    gathered = await asyncio.gather(*tasks, return_exceptions=True)

    for (name, _), result in zip(sub_agents, gathered):
        if isinstance(result, Exception):
            failed_agents.append({
                "agent": name,
                "error": str(result),
                "retryable": isinstance(result, RetryableError),
            })
            if isinstance(result, RetryableError):
                # 可重试错误：单独重试该子 Agent
                try:
                    result = await exponential_backoff_retry(max_retries=2)(sub_agents_dict[name])(session)
                    failed_agents.pop()  # 重试成功，移除失败记录
                except Exception as retry_error:
                    failed_agents[-1]["retry_failed"] = str(retry_error)
        else:
            results[name] = result

    # 应用部分失败策略
    if failed_agents:
        if partial_policy == "fail":
            raise ExplorationError(
                f"Subagents failed: {failed_agents}. Policy is 'fail'."
            )
        elif partial_policy == "continue":
            # 记录警告，继续流程
            ctx.setdefault("agent_logs", []).append({
                "event": "PARTIAL_FAILURE",
                "failed_agents": failed_agents,
                "policy": partial_policy,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    # 汇总结果
    return {
        "opportunities": _merge_opportunities(results),
        "partial_failures": failed_agents,
        "policy_applied": partial_policy,
    }
```

---

## 4. 并发控制

### 4.1 Git 仓库互斥锁（基于 Redis 的分布式锁）

同一仓库同一时间只能有一个开发 Agent 写操作。

```python
import redis
import redis.asyncio as aioredis
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from typing import Dict, Any

class GitLockManager:
    """
    基于 Redis 的分布式 Git 写锁管理器。
    支持锁续期、孤儿锁检测、死锁超时。
    """

    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)
        self.lock_ttl = 14400  # 4小时，与开发节点超时一致
        self.renew_interval = 300  # 每5分钟续期

    def _lock_key(self, repo_url: str) -> str:
        return f"rvi:git_lock:{repo_url}"

    async def is_session_alive(self, session_id: str) -> bool:
        """检查会话是否仍在运行。"""
        result = await db.fetchval(
            "SELECT status FROM rvinsights_sessions WHERE session_id = $1",
            session_id
        )
        return result in ("running", "interrupted")

    @asynccontextmanager
    async def acquire_lock(
        self,
        repo_url: str,
        session_id: str,
        timeout: int = 300,
    ):
        """
        获取 Git 写锁。

        Args:
            repo_url: 目标仓库 URL
            session_id: 当前会话 ID
            timeout: 等待锁的最长时间 (秒)
        """
        lock_key = self._lock_key(repo_url)
        lock_value = session_id
        start_time = datetime.now(timezone.utc)

        while True:
            # 尝试获取锁 (NX = 仅当不存在时设置)
            acquired = await self.redis.set(
                lock_key, lock_value, nx=True, ex=self.lock_ttl
            )

            if acquired:
                break

            # 锁已被占用，检查持有者是否已死亡 (孤儿锁检测)
            holder = await self.redis.get(lock_key)
            if holder:
                holder_session = holder.decode()
                if not await self.is_session_alive(holder_session):
                    # 强制释放孤儿锁
                    await self.redis.delete(lock_key)
                    continue

            # 检查超时
            if (datetime.now(timezone.utc) - start_time).total_seconds() > timeout:
                raise GitLockTimeoutError(
                    f"Could not acquire git lock for {repo_url} within {timeout}s"
                )

            await asyncio.sleep(1)

        # 持久化锁信息到 DB
        await db.execute("""
            INSERT INTO git_locks (repo_url, session_id, acquired_at, expires_at)
            VALUES ($1, $2, NOW(), NOW() + INTERVAL '4 hours')
            ON CONFLICT (repo_url) DO UPDATE SET
                session_id = EXCLUDED.session_id,
                acquired_at = EXCLUDED.acquired_at,
                expires_at = EXCLUDED.expires_at
        """, repo_url, session_id)

        # 启动锁续期任务
        renew_task = asyncio.create_task(self._renew_lock(lock_key, lock_value))

        try:
            yield {"lock_id": lock_key, "repo_url": repo_url, "session_id": session_id}
        finally:
            # 取消续期任务
            renew_task.cancel()
            try:
                await renew_task
            except asyncio.CancelledError:
                pass

            # 仅当持有者仍是当前会话时才释放
            current_holder = await self.redis.get(lock_key)
            if current_holder and current_holder.decode() == session_id:
                await self.redis.delete(lock_key)
                await db.execute(
                    "DELETE FROM git_locks WHERE repo_url = $1 AND session_id = $2",
                    repo_url, session_id
                )

    async def _renew_lock(self, lock_key: str, lock_value: str) -> None:
        """后台任务：定期续期锁。"""
        while True:
            try:
                await asyncio.sleep(self.renew_interval)
                current = await self.redis.get(lock_key)
                if current and current.decode() == lock_value:
                    await self.redis.expire(lock_key, self.lock_ttl)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Lock renewal failed for {lock_key}: {e}")

# === 使用示例 ===
git_lock_manager = GitLockManager(os.environ["REDIS_URL"])

async def run_development(session: Session) -> Dict[str, Any]:
    ctx = session.context
    repo_url = ctx["development_plan"]["target_repo"]["clone_url"]

    async with git_lock_manager.acquire_lock(repo_url, ctx["session_id"], timeout=300):
        # 在锁保护下执行开发操作
        developer = ClaudeCodeDeveloper(session=session)
        result = await developer.run()
        return result
```

### 4.2 QEMU 虚拟机池管理（基于 Redis 列表）

```python
import json
import asyncio
from typing import Dict, Any, Optional

class QEMUInstancePool:
    """
    QEMU 虚拟机池管理器。
    基于 Redis 列表实现实例池，支持工作窃取和孤儿检测。
    """

    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)
        self.instance_lock_ttl = 10800  # 3小时，与测试节点超时一致

    def _pool_key(self, arch: str, variant: str) -> str:
        return f"rvi:qemu_pool:{arch}:{variant}"

    def _occupied_key(self, instance_id: str) -> str:
        return f"rvi:qemu_occupied:{instance_id}"

    async def is_session_alive(self, session_id: str) -> bool:
        """检查会话是否仍在运行。"""
        result = await db.fetchval(
            "SELECT status FROM rvinsights_sessions WHERE session_id = $1",
            session_id
        )
        return result in ("running", "interrupted")

    async def acquire_instance(
        self,
        config: Dict[str, Any],
        session_id: str,
        timeout: int = 600,
    ) -> Dict[str, Any]:
        """
        从 QEMU 实例池中获取可用实例。

        Args:
            config: QEMU 配置 {arch, variant, ...}
            session_id: 当前会话 ID
            timeout: 等待实例的最长时间 (秒)
        """
        pool_key = self._pool_key(config["arch"], config["variant"])
        start_time = datetime.now(timezone.utc)

        while True:
            # 尝试从池中获取实例
            instance_data = await self.redis.lpop(pool_key)
            if instance_data:
                instance = json.loads(instance_data)
                # 标记为已占用
                await self.redis.setex(
                    self._occupied_key(instance["instance_id"]),
                    self.instance_lock_ttl,
                    session_id
                )
                # 持久化到 DB
                await db.execute("""
                    INSERT INTO qemu_occupancy (instance_id, session_id, acquired_at, config)
                    VALUES ($1, $2, NOW(), $3)
                    ON CONFLICT (instance_id) DO UPDATE SET
                        session_id = EXCLUDED.session_id,
                        acquired_at = EXCLUDED.acquired_at
                """, instance["instance_id"], session_id, json.dumps(config))
                return instance

            # 池为空，尝试工作窃取：检查孤儿实例
            stolen = await self._steal_orphan_instance(config, session_id)
            if stolen:
                return stolen

            # 检查超时
            if (datetime.now(timezone.utc) - start_time).total_seconds() > timeout:
                raise QuotaExceededError(
                    f"No QEMU instance available for {config} within {timeout}s"
                )

            await asyncio.sleep(5)

    async def _steal_orphan_instance(
        self,
        config: Dict[str, Any],
        new_session_id: str,
    ) -> Optional[Dict[str, Any]]:
        """工作窃取：回收孤儿会话占用的 QEMU 实例。"""
        occupied_pattern = "rvi:qemu_occupied:*"
        async for key in self.redis.scan_iter(match=occupied_pattern):
            holder_session = await self.redis.get(key)
            if holder_session:
                holder = holder_session.decode()
                if not await self.is_session_alive(holder):
                    instance_id = key.decode().split(":")[-1]
                    # 强制回收
                    await self.redis.delete(key)
                    await db.execute(
                        "DELETE FROM qemu_occupancy WHERE session_id = $1",
                        holder
                    )
                    # 重置实例状态 (通过 MCP-Server)
                    await reset_qemu_instance(instance_id)
                    return {
                        "instance_id": instance_id,
                        "stolen": True,
                        "previous_session": holder,
                        "new_session_id": new_session_id,
                    }
        return None

    async def release_instance(
        self,
        instance_id: str,
        delay_minutes: int = 30,
    ) -> None:
        """
        释放 QEMU 实例回池。

        Args:
            instance_id: 实例 ID
            delay_minutes: 延迟释放时间 (供人类调试查看)
        """
        if delay_minutes > 0:
            asyncio.create_task(self._delayed_release(instance_id, delay_minutes))
        else:
            await self._do_release(instance_id)

    async def _delayed_release(self, instance_id: str, delay_minutes: int) -> None:
        await asyncio.sleep(delay_minutes * 60)
        await self._do_release(instance_id)

    async def _do_release(self, instance_id: str) -> None:
        """实际释放逻辑。"""
        # 删除占用标记
        await self.redis.delete(self._occupied_key(instance_id))

        # 重置实例状态
        await reset_qemu_instance(instance_id)

        # 回池 (默认 RV64GC)
        await self.redis.rpush(
            self._pool_key("rv64gc", "default"),
            json.dumps({"instance_id": instance_id, "reset_at": datetime.now(timezone.utc).isoformat()})
        )

        # 更新 DB
        await db.execute(
            "DELETE FROM qemu_occupancy WHERE instance_id = $1",
            instance_id
        )

# === 使用示例 ===
qemu_pool = QEMUInstancePool(os.environ["REDIS_URL"])

async def run_testing(session: Session) -> Dict[str, Any]:
    ctx = session.context
    config = ctx["planning_result"]["testing_plan"]["emulation_configs"][0]

    instance = await qemu_pool.acquire_instance(config, ctx["session_id"], timeout=600)
    try:
        tester = OpenAITester(session=session, qemu_instance=instance)
        result = await tester.run()
        return result
    finally:
        await qemu_pool.release_instance(instance["instance_id"], delay_minutes=30)
```

### 4.3 Agent Worker Pool 与工作窃取

```python
import asyncio
from asyncio import PriorityQueue
from typing import Dict, Any, Optional, Callable
import logging

logger = logging.getLogger("rvinsights.worker_pool")

class AgentWorkerPool:
    """
    Agent 执行 Worker Pool，支持优先级队列和工作窃取。

    设计:
    - 全局优先级队列: 接收所有待执行任务
    - Worker 本地队列: 每个 worker 优先处理本地任务
    - 工作窃取: 空闲 worker 从其他 worker 队列窃取任务
    """

    def __init__(self, num_workers: int = 8):
        self.num_workers = num_workers
        self.global_queue: PriorityQueue = PriorityQueue()
        self.worker_queues: list[PriorityQueue] = [
            PriorityQueue() for _ in range(num_workers)
        ]
        self.workers: list[asyncio.Task] = []
        self.shutdown_event = asyncio.Event()
        self.running_tasks: Dict[str, asyncio.Task] = {}  # session_id -> task

    def submit(
        self,
        session: Session,
        agent_func: Callable,
        priority: int = 5,
    ) -> None:
        """
        提交任务到全局队列。

        Args:
            session: 会话对象
            agent_func: Agent 执行函数
            priority: 优先级 (1-10, 1 最高)
        """
        task = {
            "session_id": session.context["session_id"],
            "session": session,
            "agent_func": agent_func,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }
        self.global_queue.put_nowait((priority, task))
        logger.info(f"Task submitted: session={task['session_id']}, priority={priority}")

    def start(self) -> None:
        """启动 Worker 池。"""
        for i in range(self.num_workers):
            task = asyncio.create_task(self._worker_loop(i))
            self.workers.append(task)
        logger.info(f"Worker pool started with {self.num_workers} workers")

    async def stop(self) -> None:
        """优雅停止 Worker 池。"""
        self.shutdown_event.set()
        # 取消所有运行中的任务
        for session_id, task in self.running_tasks.items():
            task.cancel()
            logger.info(f"Cancelled task for session {session_id}")
        # 等待所有 worker 退出
        await asyncio.gather(*self.workers, return_exceptions=True)
        logger.info("Worker pool stopped")

    async def _worker_loop(self, worker_id: int) -> None:
        """Worker 主循环。"""
        local_queue = self.worker_queues[worker_id]

        while not self.shutdown_event.is_set():
            task = await self._get_task(worker_id, local_queue)
            if task:
                await self._execute_task(task)
            else:
                await asyncio.sleep(0.1)

    async def _get_task(
        self,
        worker_id: int,
        local_queue: PriorityQueue,
    ) -> Optional[Dict[str, Any]]:
        """获取任务：本地队列 -> 全局队列 -> 工作窃取。"""
        # 1. 优先处理本地队列
        if not local_queue.empty():
            _, task = local_queue.get_nowait()
            return task

        # 2. 从全局队列获取
        if not self.global_queue.empty():
            _, task = self.global_queue.get_nowait()
            return task

        # 3. 工作窃取：从其他 worker 队列窃取
        return await self._steal_task(worker_id)

    async def _steal_task(self, thief_id: int) -> Optional[Dict[str, Any]]:
        """从随机其他 worker 队列窃取任务。"""
        for i in range(self.num_workers):
            if i == thief_id:
                continue
            victim_queue = self.worker_queues[i]
            if not victim_queue.empty():
                try:
                    _, task = victim_queue.get_nowait()
                    logger.debug(f"Worker {thief_id} stole task from worker {i}")
                    return task
                except asyncio.QueueEmpty:
                    continue
        return None

    async def _execute_task(self, task: Dict[str, Any]) -> None:
        """执行任务。"""
        session_id = task["session_id"]
        session = task["session"]
        agent_func = task["agent_func"]

        # 记录任务开始
        session.context.setdefault("agent_logs", []).append({
            "event": "TASK_START",
            "worker": asyncio.current_task().get_name(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # 创建执行任务
        exec_task = asyncio.create_task(agent_func(session))
        self.running_tasks[session_id] = exec_task

        try:
            result = await exec_task
            # 保存结果到 Session
            await self._save_result(session, result)
        except asyncio.CancelledError:
            logger.warning(f"Task cancelled: session={session_id}")
            raise
        except Exception as e:
            logger.error(f"Task failed: session={session_id}, error={e}")
            await handle_task_failure(session, e)
        finally:
            self.running_tasks.pop(session_id, None)

    async def _save_result(self, session: Session, result: Dict[str, Any]) -> None:
        """保存任务结果到 Session 和数据库。"""
        # 更新 Session 状态
        for key, value in result.items():
            setattr(session.context, key, value)

        # 持久化到数据库
        await save_session_state(session)
```

### 4.4 租户级并发配额控制

```python
class TenantQuotaManager:
    """
    租户级并发配额管理。
    限制每个租户同时运行的会话数，防止资源抢占。
    """

    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)

    def _tenant_key(self, tenant_id: str) -> str:
        return f"rvi:tenant_sessions:{tenant_id}"

    async def check_concurrency(self, tenant_id: str, max_sessions: int = 5) -> bool:
        """检查租户是否还有并发会话额度。"""
        key = self._tenant_key(tenant_id)
        current = await self.redis.scard(key)
        return current < max_sessions

    async def register_session(self, tenant_id: str, session_id: str) -> None:
        """注册会话到租户配额。"""
        key = self._tenant_key(tenant_id)
        await self.redis.sadd(key, session_id)
        # 设置过期时间，防止孤儿记录
        await self.redis.expire(key, 86400 * 2)

    async def unregister_session(self, tenant_id: str, session_id: str) -> None:
        """从租户配额中注销会话。"""
        key = self._tenant_key(tenant_id)
        await self.redis.srem(key, session_id)

    async def get_tenant_usage(self, tenant_id: str) -> Dict[str, Any]:
        """获取租户当前使用情况。"""
        key = self._tenant_key(tenant_id)
        sessions = await self.redis.smembers(key)
        return {
            "tenant_id": tenant_id,
            "active_sessions": len(sessions),
            "session_ids": [s.decode() for s in sessions],
        }
```

---

## 5. 会话生命周期管理

### 5.1 超时策略

```python
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

class SessionTimeoutManager:
    """
    管理整体会话超时和单阶段超时。

    策略:
    - 全局会话超时: 24小时 (从创建到强制终止)
    - 单阶段超时: 各阶段独立配置
    - 人工审核节点: 不设超时 (等待人类决策)
    """

    # 整体会话超时
    GLOBAL_SESSION_TIMEOUT = timedelta(hours=24)

    # 单阶段超时配置
    STAGE_TIMEOUTS = {
        "INITIALIZATION": timedelta(seconds=30),
        "EXPLORATION": timedelta(hours=2),
        "PLANNING": timedelta(hours=1),
        "DEVELOPMENT": timedelta(hours=4),
        "REVIEW": timedelta(minutes=30),
        "TESTING": timedelta(hours=3),
        "COMPLETION": timedelta(seconds=60),
        # 人工审核节点不设超时
        "HUMAN_REVIEW_EXPLORATION": None,
        "HUMAN_REVIEW_PLANNING": None,
        "HUMAN_REVIEW_CODE": None,
        "HUMAN_REVIEW_TESTING": None,
    }

    def check_timeouts(self, session: Session) -> Optional[str]:
        """
        检查是否超时。返回超时类型或 None。
        """
        ctx = session.context
        now = datetime.now(timezone.utc)
        created_at = datetime.fromisoformat(ctx["created_at"])

        # 全局超时检查
        if now - created_at > self.GLOBAL_SESSION_TIMEOUT:
            return "GLOBAL_TIMEOUT"

        # 单阶段超时检查
        current_stage = ctx["current_stage"]
        stage_timeout = self.STAGE_TIMEOUTS.get(current_stage)

        if stage_timeout and ctx.get("status") == "running":
            # 获取当前阶段的进入时间
            stage_entries = [
                t for t in ctx.get("timestamps", [])
                if t["stage"] == current_stage
            ]
            if stage_entries:
                last_entry = datetime.fromisoformat(stage_entries[-1]["entered_at"])
                if now - last_entry > stage_timeout:
                    return f"STAGE_TIMEOUT:{current_stage}"

        return None

    async def enforce_timeout(self, session: Session) -> Optional[Dict[str, Any]]:
        """
        强制执行超时，返回状态更新。
        """
        timeout_type = self.check_timeouts(session)
        if not timeout_type:
            return None

        logger.warning(f"Session {session.context['session_id']} timed out: {timeout_type}")

        # 更新会话状态
        updates = {
            "status": "failed",
            "last_error": {
                "type": "TIMEOUT",
                "subtype": timeout_type,
                "message": f"Session or stage timed out: {timeout_type}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        }

        # 清理资源
        await cleanup_session_resources(session)

        return updates
```

### 5.2 优雅终止（取消）

```python
import signal
import asyncio
from typing import Dict, Any, Set

class GracefulTerminationManager:
    """
    处理人类点击"取消"时的优雅终止。

    流程:
    1. 标记会话为取消中
    2. 向 Agent 进程发送取消信号
    3. 等待清理完成 (SIGTERM -> 5s -> SIGKILL)
    4. 清理资源并归档部分产物
    """

    def __init__(self):
        self.cancelled_sessions: Set[str] = set()
        self.agent_tasks: Dict[str, asyncio.Task] = {}
        self.termination_timeout = 5.0  # SIGTERM 后等待秒数

    async def request_cancellation(self, session_id: str) -> None:
        """
        人类点击"取消"时调用。
        """
        self.cancelled_sessions.add(session_id)

        # 更新 DB
        await db.execute("""
            UPDATE rvinsights_sessions
            SET status = 'cancelling', cancel_requested_at = NOW()
            WHERE session_id = $1
        """, session_id)

        # 取消运行中的 Agent 任务
        task = self.agent_tasks.get(session_id)
        if task and not task.done():
            task.cancel()
            logger.info(f"Cancellation requested for session {session_id}, task cancelled")

            # 设置强制终止定时器
            asyncio.create_task(self._force_kill_after_timeout(session_id))

    async def _force_kill_after_timeout(self, session_id: str) -> None:
        """SIGTERM 后等待，若仍未退出则强制终止。"""
        await asyncio.sleep(self.termination_timeout)

        task = self.agent_tasks.get(session_id)
        if task and not task.done():
            logger.warning(f"Force killing agent task for session {session_id}")
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # 执行资源清理
        await self.cleanup_resources(session_id)

    async def cleanup_resources(self, session_id: str) -> None:
        """
        清理沙箱资源、释放锁、归档部分产物。
        """
        # 加载会话状态
        state = await load_session_state(session_id)
        if not state:
            logger.error(f"Cannot cleanup: session {session_id} not found")
            return

        # 释放 Git 锁
        if state.get("git_lock_id"):
            await git_lock_manager.release_lock_by_session(session_id)

        # 释放 QEMU 实例
        if state.get("qemu_instance_id"):
            await qemu_pool.release_instance(state["qemu_instance_id"], delay_minutes=0)

        # 清理沙箱工作目录 (保留 artifacts)
        workspace = state.get("workspace_path")
        if workspace:
            sandbox = os.path.join(workspace, "sandbox")
            if os.path.exists(sandbox):
                import shutil
                shutil.rmtree(sandbox, ignore_errors=True)

        # 归档部分产物 (即使取消也保留已产生的报告)
        await upload_partial_artifacts(state)

        # 最终状态更新
        await db.execute("""
            UPDATE rvinsights_sessions
            SET status = 'cancelled', cancelled_at = NOW()
            WHERE session_id = $1
        """, session_id)

        self.cancelled_sessions.discard(session_id)
        logger.info(f"Cleanup completed for session {session_id}")
```

### 5.3 孤儿会话检测与自动恢复

```python
import psutil
from datetime import datetime, timezone, timedelta

class OrphanSessionDetector:
    """
    定期检测 Agent 进程崩溃但会话状态未更新的情况。

    检测逻辑:
    1. 查询所有 status == 'running' 且 updated_at > 5分钟前 的会话
    2. 检查关联的 Agent 进程是否仍然存在
    3. 若进程不存在，标记为孤儿并自动恢复
    """

    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval

    def start(self) -> None:
        """启动后台检测循环。"""
        asyncio.create_task(self._detection_loop())
        logger.info("Orphan session detector started")

    async def _detection_loop(self) -> None:
        while True:
            try:
                await self._check_orphan_sessions()
            except Exception as e:
                logger.error(f"Orphan detection error: {e}")
            await asyncio.sleep(self.check_interval)

    async def _check_orphan_sessions(self) -> None:
        """检测孤儿会话。"""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)

        running_sessions = await db.fetch("""
            SELECT session_id, current_stage, updated_at, process_pid
            FROM rvinsights_sessions
            WHERE status = 'running' AND updated_at < $1
        """, cutoff)

        for session in running_sessions:
            pid = session.get("process_pid")
            if pid and not self._is_process_alive(pid):
                logger.error(
                    f"Orphan session detected: {session['session_id']}, "
                    f"stage={session['current_stage']}"
                )
                await self._recover_orphan_session(session)

    def _is_process_alive(self, pid: int) -> bool:
        """检查进程是否存活。"""
        try:
            proc = psutil.Process(pid)
            return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
        except psutil.NoSuchProcess:
            return False

    async def _recover_orphan_session(self, session: Dict[str, Any]) -> None:
        """
        自动恢复策略:
        1. 释放该会话持有的所有锁 (Git, QEMU)
        2. 从 OpenAI Session checkpoint 恢复状态
        3. 若中断于人工审核节点，恢复为 'interrupted' 状态
        4. 若中断于 Agent 执行中，重放该节点
        """
        session_id = session["session_id"]

        # 强制释放锁
        await db.execute(
            "DELETE FROM git_locks WHERE session_id = $1",
            session_id
        )
        await db.execute(
            "DELETE FROM qemu_occupancy WHERE session_id = $1",
            session_id
        )

        # 从 OpenAI Session checkpoint 恢复
        checkpoint = await load_openai_checkpoint(session_id)
        if not checkpoint:
            # 无 checkpoint，标记为失败
            await db.execute("""
                UPDATE rvinsights_sessions
                SET status = 'failed', failure_reason = 'orphan_no_checkpoint'
                WHERE session_id = $1
            """, session_id)
            return

        recovered_state = checkpoint["state"]
        interrupted_stage = recovered_state.get("current_stage")

        if "HUMAN_REVIEW" in interrupted_stage:
            # 恢复为中断状态，等待人类继续
            await db.execute("""
                UPDATE rvinsights_sessions
                SET status = 'interrupted', current_stage = $1
                WHERE session_id = $2
            """, interrupted_stage, session_id)
            # 通知 UI 重新连接
            await notify_ui_reconnect(session_id, interrupted_stage)
        else:
            # 重放 Agent 节点
            await db.execute("""
                UPDATE rvinsights_sessions
                SET status = 'running',
                    current_stage = $1,
                    retry_count = COALESCE(retry_count, 0) + 1,
                    recovery_from_checkpoint = $2
                WHERE session_id = $3
            """, interrupted_stage, checkpoint.get("checkpoint_id"), session_id)
            # 将任务重新提交到 Worker Pool
            await submit_node_retry(session_id, interrupted_stage)
```

### 5.4 Session Checkpointer

OpenAI Agents SDK 的 Session 持久化 + 应用层自定义状态。

```python
from agents import Session, PostgresSessionStore
from typing import Dict, Any, Optional

class RVInsightsCheckpointer:
    """
    双持久化策略:
    1. OpenAI SDK 原生 Session 持久化 (PostgreSQL)
    2. 应用层自定义状态持久化 (PostgreSQL)
    """

    def __init__(self, postgres_url: str):
        # OpenAI SDK 原生 Session Store
        self.openai_store = PostgresSessionStore(
            connection_string=postgres_url,
            table_name="openai_sessions",
        )
        self.postgres_url = postgres_url

    async def save_session(self, session: Session) -> None:
        """
        保存 Session 状态。
        同时更新 OpenAI SDK 表和应用层表。
        """
        # 1. OpenAI SDK 原生保存
        await self.openai_store.save(session)

        # 2. 应用层自定义状态保存
        ctx = session.context
        await db.execute("""
            INSERT INTO rvinsights_sessions (
                session_id, current_stage, status,
                exploration_result, planning_result,
                development_result, review_result, testing_result,
                dev_review_iteration_count, max_dev_review_iterations,
                human_decisions, agent_logs,
                workspace_path, git_lock_id, qemu_instance_id,
                updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, NOW())
            ON CONFLICT (session_id) DO UPDATE SET
                current_stage = EXCLUDED.current_stage,
                status = EXCLUDED.status,
                exploration_result = EXCLUDED.exploration_result,
                planning_result = EXCLUDED.planning_result,
                development_result = EXCLUDED.development_result,
                review_result = EXCLUDED.review_result,
                testing_result = EXCLUDED.testing_result,
                dev_review_iteration_count = EXCLUDED.dev_review_iteration_count,
                human_decisions = EXCLUDED.human_decisions,
                agent_logs = EXCLUDED.agent_logs,
                workspace_path = EXCLUDED.workspace_path,
                git_lock_id = EXCLUDED.git_lock_id,
                qemu_instance_id = EXCLUDED.qemu_instance_id,
                updated_at = NOW()
        """, [
            ctx["session_id"], ctx["current_stage"], ctx["status"],
            json.dumps(ctx.get("exploration_result")),
            json.dumps(ctx.get("planning_result")),
            json.dumps(ctx.get("development_result")),
            json.dumps(ctx.get("review_result")),
            json.dumps(ctx.get("testing_result")),
            ctx.get("dev_review_iteration_count", 0),
            ctx.get("max_dev_review_iterations", 5),
            json.dumps(ctx.get("human_decisions", [])),
            json.dumps(ctx.get("agent_logs", [])),
            ctx.get("workspace_path"),
            ctx.get("git_lock_id"),
            ctx.get("qemu_instance_id"),
        ])

    async def load_session(self, session_id: str) -> Optional[Session]:
        """
        加载 Session 状态。
        优先从 OpenAI SDK Store 加载，再补充应用层字段。
        """
        # 从 OpenAI SDK Store 加载
        session = await self.openai_store.load(session_id)
        if not session:
            return None

        # 从应用层表补充字段
        row = await db.fetchrow(
            "SELECT * FROM rvinsights_sessions WHERE session_id = $1",
            session_id
        )
        if row:
            # 将应用层字段合并到 session context
            for key in [
                "current_stage", "status", "exploration_result",
                "planning_result", "development_result", "review_result",
                "testing_result", "dev_review_iteration_count",
                "human_decisions", "agent_logs", "workspace_path",
                "git_lock_id", "qemu_instance_id",
            ]:
                if key in row and row[key] is not None:
                    setattr(session.context, key, row[key])

        return session

    async def create_checkpoint(self, session: Session) -> str:
        """
        创建显式 checkpoint (用于子图迭代和故障恢复)。
        """
        checkpoint_id = f"{session.context['session_id']}_{datetime.now(timezone.utc).timestamp()}"

        await db.execute("""
            INSERT INTO session_checkpoints (
                checkpoint_id, session_id, state, created_at
            ) VALUES ($1, $2, $3, NOW())
        """, checkpoint_id, session.context["session_id"], json.dumps({
            k: v for k, v in session.context.items()
            if k not in ["current_patch"]  # 排除大字段
        }))

        return checkpoint_id
```

---

## 6. 完整伪代码实现

### 6.1 全局 Handoff 图构建

```python
# openai-agents >= 1.5.0
from agents import Agent, handoff, Session, interrupt, ResumeCommand
from agents.sessions import PostgresSessionStore
from typing import Dict, Any, Literal
import os
import asyncio
from datetime import datetime, timezone

# === 初始化持久化 ===
session_store = PostgresSessionStore(
    connection_string=os.environ["POSTGRES_URL"],
    table_name="openai_sessions",
)
checkpointer = RVInsightsCheckpointer(os.environ["POSTGRES_URL"])

# === Agent 定义 (详见第1节) ===
# explorer_agent, planner_agent, developer_agent, reviewer_agent, tester_agent
# human_review_agent, orchestrator_agent

# === 全局 Handoff 图构建函数 ===
async def build_global_handoff_graph() -> Agent:
    """
    构建 RV-Insights 全局 Handoff 图。

    返回 Orchestrator Agent，其 handoffs 包含所有阶段流转。
    """

    # === Orchestrator 的 Handoff 定义 ===
    # Orchestrator 负责阶段之间的流转控制
    orchestrator_agent.handoffs = [
        # INITIALIZATION -> EXPLORATION
        handoff(
            target=explorer_agent,
            condition=lambda ctx: ctx.get("current_stage") == "INITIALIZATION",
            metadata={"stage_transition": "INITIALIZATION->EXPLORATION"}
        ),
        # EXPLORATION 完成后 -> HUMAN_REVIEW_EXPLORATION (通过 interrupt)
        handoff(
            target=human_review_agent,
            condition=lambda ctx: ctx.get("current_stage") == "EXPLORATION_COMPLETE",
            metadata={"stage_transition": "EXPLORATION->HUMAN_REVIEW_EXPLORATION"}
        ),
        # HUMAN_REVIEW_EXPLORATION -> PLANNING (APPROVE)
        handoff(
            target=planner_agent,
            condition=lambda ctx: (
                ctx.get("current_stage") == "HUMAN_REVIEW_EXPLORATION" and
                ctx.get("last_human_decision") == "APPROVE"
            ),
            metadata={"stage_transition": "HUMAN_REVIEW_EXPLORATION->PLANNING"}
        ),
        # HUMAN_REVIEW_EXPLORATION -> EXPLORATION (REQUEST_CHANGES)
        handoff(
            target=explorer_agent,
            condition=lambda ctx: (
                ctx.get("current_stage") == "HUMAN_REVIEW_EXPLORATION" and
                ctx.get("last_human_decision") == "REQUEST_CHANGES"
            ),
            metadata={"stage_transition": "HUMAN_REVIEW_EXPLORATION->EXPLORATION"}
        ),
        # PLANNING 完成后 -> HUMAN_REVIEW_PLANNING
        handoff(
            target=human_review_agent,
            condition=lambda ctx: ctx.get("current_stage") == "PLANNING_COMPLETE",
            metadata={"stage_transition": "PLANNING->HUMAN_REVIEW_PLANNING"}
        ),
        # HUMAN_REVIEW_PLANNING -> DEVELOPMENT (APPROVE)
        handoff(
            target=developer_agent,
            condition=lambda ctx: (
                ctx.get("current_stage") == "HUMAN_REVIEW_PLANNING" and
                ctx.get("last_human_decision") == "APPROVE"
            ),
            metadata={"stage_transition": "HUMAN_REVIEW_PLANNING->DEVELOPMENT"}
        ),
        # DEVELOPMENT -> REVIEW (进入迭代子图)
        handoff(
            target=reviewer_agent,
            condition=lambda ctx: ctx.get("current_stage") == "DEVELOPMENT_COMPLETE",
            metadata={"stage_transition": "DEVELOPMENT->REVIEW", "enter_subgraph": True}
        ),
        # REVIEW 子图退出 -> HUMAN_REVIEW_CODE
        handoff(
            target=human_review_agent,
            condition=lambda ctx: ctx.get("current_stage") == "REVIEW_COMPLETE",
            metadata={"stage_transition": "REVIEW->HUMAN_REVIEW_CODE"}
        ),
        # HUMAN_REVIEW_CODE -> TESTING (APPROVE)
        handoff(
            target=tester_agent,
            condition=lambda ctx: (
                ctx.get("current_stage") == "HUMAN_REVIEW_CODE" and
                ctx.get("last_human_decision") == "APPROVE"
            ),
            metadata={"stage_transition": "HUMAN_REVIEW_CODE->TESTING"}
        ),
        # HUMAN_REVIEW_CODE -> DEVELOPMENT (REQUEST_CHANGES)
        handoff(
            target=developer_agent,
            condition=lambda ctx: (
                ctx.get("current_stage") == "HUMAN_REVIEW_CODE" and
                ctx.get("last_human_decision") == "REQUEST_CHANGES"
            ),
            metadata={"stage_transition": "HUMAN_REVIEW_CODE->DEVELOPMENT"}
        ),
        # TESTING 完成后 -> HUMAN_REVIEW_TESTING
        handoff(
            target=human_review_agent,
            condition=lambda ctx: ctx.get("current_stage") == "TESTING_COMPLETE",
            metadata={"stage_transition": "TESTING->HUMAN_REVIEW_TESTING"}
        ),
        # HUMAN_REVIEW_TESTING -> COMPLETION (APPROVE)
        handoff(
            target=finalize_agent,
            condition=lambda ctx: (
                ctx.get("current_stage") == "HUMAN_REVIEW_TESTING" and
                ctx.get("last_human_decision") in ["APPROVE", "ADD_NOTES"]
            ),
            metadata={"stage_transition": "HUMAN_REVIEW_TESTING->COMPLETION"}
        ),
        # 任何阶段的 REJECT -> COMPLETION (失败归档)
        handoff(
            target=finalize_agent,
            condition=lambda ctx: ctx.get("last_human_decision") == "REJECT",
            metadata={"stage_transition": "*->COMPLETION(REJECT)"}
        ),
    ]

    return orchestrator_agent

# === 会话启动 ===
async def start_session(
    session_id: str,
    tenant_id: str,
    initial_input: Dict[str, Any],
) -> Session:
    """
    启动新会话。

    流程:
    1. 检查租户并发配额
    2. 创建 Session 和初始 Context
    3. 初始化工作目录
    4. 启动 Orchestrator
    """
    # 检查租户配额
    quota_manager = TenantQuotaManager(os.environ["REDIS_URL"])
    if not await quota_manager.check_concurrency(tenant_id):
        raise QuotaExceededError(
            f"Tenant {tenant_id} has reached max concurrent sessions limit"
        )

    # 创建初始 Context
    context = RVInsightsContext(
        session_id=session_id,
        tenant_id=tenant_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        current_stage="INITIALIZATION",
        status="running",
        dev_review_iteration_count=0,
        max_dev_review_iterations=5,
        human_decisions=[],
        agent_logs=[],
        timestamps=[{
            "stage": "INITIALIZATION",
            "entered_at": datetime.now(timezone.utc).isoformat(),
        }],
        **initial_input,
    )

    # 初始化工作目录
    workspace_base = os.environ.get("RVI_WORKSPACE_BASE", "/var/rv-insights/workspaces")
    workspace_path = os.path.join(workspace_base, tenant_id, session_id)
    os.makedirs(workspace_path, exist_ok=True)
    os.makedirs(os.path.join(workspace_path, "artifacts"), exist_ok=True)
    os.makedirs(os.path.join(workspace_path, "logs"), exist_ok=True)
    context.workspace_path = workspace_path

    # 创建 Session
    session = Session(
        session_id=session_id,
        context=context,
        store=session_store,
    )

    # 注册租户会话
    await quota_manager.register_session(tenant_id, session_id)

    # 保存初始状态
    await checkpointer.save_session(session)

    # 启动 Orchestrator
    orchestrator = await build_global_handoff_graph()
    asyncio.create_task(run_orchestrator(session, orchestrator))

    return session

async def run_orchestrator(session: Session, orchestrator: Agent) -> None:
    """
    运行 Orchestrator，管理整个工作流生命周期。
    """
    try:
        # 启动 Orchestrator Agent
        await orchestrator.run(session=session)
    except Exception as e:
        logger.error(f"Orchestrator failed for session {session.context['session_id']}: {e}")
        session.context["status"] = "failed"
        session.context["last_error"] = {
            "type": "ORCHESTRATOR_FAILURE",
            "message": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await checkpointer.save_session(session)
```

### 6.2 开发-审核迭代子图代码

```python
from agents import Agent, handoff, Session
from typing import Dict, Any, Literal

# === 子图退出 Agent ===
subgraph_exit_agent = Agent(
    name="subgraph_exit",
    model="gpt-4.1",
    instructions="子图退出节点，将控制权交还 Orchestrator。",
)

async def build_dev_review_subgraph() -> Agent:
    """
    构建开发-审核迭代子图。

    子图内部通过条件 Handoff 实现迭代循环。
    当达到退出条件时，Handoff 到 subgraph_exit_agent，再由 Orchestrator 接管。
    """

    # 开发 Agent (子图实例)
    subgraph_developer = Agent(
        name="subgraph_developer",
        model="claude-sonnet-4-5",  # [假设：2026 Q2 模型版本]
        # provider="anthropic",  # 伪代码参数，实际通过 Claude SDK 直接调用
        instructions="""
        你是开发 Agent (迭代模式)。
        根据 development_plan 和 revision_injection 实现代码变更。
        首次迭代按 plan 全新实现，后续迭代按修复意见修改。
        编译失败时内部自修复最多 3 次。
        """,
        tools=[bash, file_editor, git_commit, static_analysis],
    )

    # 审核 Agent (子图实例)
    subgraph_reviewer = Agent(
        name="subgraph_reviewer",
        model="codex",
        instructions="""
        你是审核 Agent (迭代模式)。
        首次迭代审核完整代码，后续迭代只关注 diff。
        输出 overall_verdict (PASS/NEEDS_REVISION/REJECT)。
        """,
        tools=[static_analysis, rag_query, git_diff],
        guardrails=[riscv_spec_guardrail, security_guardrail, style_guardrail],
    )

    # === 子图 Handoff 链 ===
    # 开发 -> 审核
    subgraph_developer.handoffs = [
        handoff(
            target=subgraph_reviewer,
            condition=HandoffCondition.AFTER_COMPLETION,
            metadata={"trigger": "dev_complete"}
        )
    ]

    # 审核 -> 条件分支
    subgraph_reviewer.handoffs = [
        handoff(
            target=subgraph_exit_agent,
            condition=lambda session: route_review_condition(session) == "PASS",
            metadata={"exit_reason": "PASS"}
        ),
        handoff(
            target=subgraph_exit_agent,
            condition=lambda session: route_review_condition(session) == "REJECT",
            metadata={"exit_reason": "REJECT"}
        ),
        handoff(
            target=subgraph_developer,
            condition=lambda session: route_review_condition(session) == "NEEDS_REVISION",
            metadata={"trigger": "revision_required"}
        ),
        handoff(
            target=subgraph_exit_agent,
            condition=lambda session: route_review_condition(session) == "MAX_ITERATIONS",
            metadata={"exit_reason": "MAX_ITERATIONS"}
        ),
    ]

    return subgraph_developer  # 子图入口是开发 Agent

async def run_dev_review_subgraph(session: Session) -> Dict[str, Any]:
    """
    执行开发-审核迭代子图。

    返回子图退出时的最终状态。
    """
    ctx = session.context

    # 初始化子图状态
    ctx["local_iteration_count"] = ctx.get("dev_review_iteration_count", 0)
    ctx["previous_patches"] = []
    ctx["review_history"] = []
    ctx["subgraph_entered_at"] = datetime.now(timezone.utc).isoformat()

    # 构建子图
    subgraph_entry = await build_dev_review_subgraph()

    # 执行子图 (循环直到退出条件满足)
    while True:
        # 执行开发 Agent
        dev_result = await subgraph_entry.run(session=session)

        # 保存开发产物
        ctx["current_patch"] = dev_result.get("patch")
        ctx["current_build_log"] = dev_result.get("build_log")
        ctx["development_result"] = dev_result

        # Handoff 到审核 Agent (由 subgraph_entry.handoffs 自动处理)
        # 审核完成后，route_review_condition 决定下一跳

        # 检查是否退出子图
        if ctx.get("subgraph_exit_reason"):
            break

        # 注入修复意见 (NEEDS_REVISION 分支)
        if ctx.get("revision_injection"):
            await inject_revision_to_developer(session, ctx["current_review_report"])

    # 子图退出，整理最终状态
    return {
        "development_result": ctx.get("development_result"),
        "review_result": ctx.get("current_review_report"),
        "dev_review_iteration_count": ctx["local_iteration_count"],
        "subgraph_exit_reason": ctx["subgraph_exit_reason"],
    }
```

### 6.3 错误处理装饰器完整实现

```python
import functools
import asyncio
import random
from typing import Callable, Any, Tuple, Type

class ErrorHandler:
    """
    统一的错误处理中心。
    根据错误类型决定重试、降级或进入 DLQ。
    """

    # 错误类型到处理策略的映射
    ERROR_STRATEGIES = {
        # OpenAI SDK 错误
        "RateLimitError": {"retry": True, "max_retries": 3, "backoff_base": 2},
        "APIError": {"retry": True, "max_retries": 3, "backoff_base": 2},
        "ContentFilterError": {"retry": False, "fallback": "modify_prompt"},
        "AuthenticationError": {"retry": False, "action": "alert_ops"},

        # Claude SDK 错误
        "AnthropicRateLimit": {"retry": True, "max_retries": 3, "backoff_base": 2},
        "AnthropicAPIError": {"retry": True, "max_retries": 3, "backoff_base": 2},

        # 沙箱错误
        "SandboxCrashError": {"retry": False, "action": "cleanup_and_fail"},
        "SandboxTimeoutError": {"retry": True, "max_retries": 1, "action": "switch_provider"},

        # 应用错误
        "GitLockTimeoutError": {"retry": True, "max_retries": 2, "backoff_base": 1.5},
        "QuotaExceededError": {"retry": True, "max_retries": 5, "backoff_base": 2},
        "CompilationError": {"retry": False, "action": "dev_self_fix"},
    }

    @classmethod
    async def handle(cls, error: Exception, session: Session, agent_name: str) -> Any:
        """
        处理错误，返回恢复策略或抛出。
        """
        error_type = type(error).__name__
        strategy = cls.ERROR_STRATEGIES.get(error_type, {"retry": False, "action": "dlq"})

        if strategy.get("retry"):
            # 重试逻辑由装饰器处理，此处记录日志
            session.context.setdefault("agent_logs", []).append({
                "event": "ERROR_RETRYABLE",
                "error_type": error_type,
                "agent": agent_name,
                "strategy": strategy,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            raise error  # 让装饰器处理重试

        # 不可重试错误
        if strategy.get("action") == "dlq":
            await send_to_dlq(session, error, agent_name)
            raise NonRetryableError(f"Agent {agent_name} failed: {error}")

        if strategy.get("action") == "dev_self_fix":
            # 开发 Agent 自修复 (在开发 Agent 内部处理)
            raise error

        if strategy.get("action") == "alert_ops":
            await alert_ops_team(
                title=f"[RV-Insights] Critical Error: {error_type}",
                severity="critical",
                context={"session_id": session.context["session_id"], "error": str(error)},
            )
            raise NonRetryableError(f"Critical error in {agent_name}: {error}")

        raise error

def with_error_handling(agent_name: str):
    """
    错误处理装饰器工厂。
    根据错误类型自动选择重试或 DLQ 策略。
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(session: Session, *args, **kwargs):
            last_error = None
            error_type = None
            strategy = None

            # 预查策略
            for attempt in range(4):  # 默认最多3次重试
                try:
                    return await func(session, *args, **kwargs)
                except Exception as e:
                    last_error = e
                    error_type = type(e).__name__
                    strategy = ErrorHandler.ERROR_STRATEGIES.get(
                        error_type, {"retry": False, "action": "dlq"}
                    )

                    if not strategy.get("retry"):
                        # 不可重试，立即处理
                        await ErrorHandler.handle(e, session, agent_name)
                        return  # handle 会抛出异常，不会执行到这里

                    if attempt >= strategy.get("max_retries", 3):
                        break

                    # 指数退避
                    delay = min(
                        strategy.get("backoff_base", 2) ** attempt + random.uniform(0, 1),
                        60.0
                    )
                    await asyncio.sleep(delay)

            # 达到最大重试次数
            await send_to_dlq(session, last_error, agent_name)
            raise MaxRetriesExceededError(
                f"Agent {agent_name} failed after max retries: {last_error}"
            )

        return async_wrapper
    return decorator

# === 应用装饰器 ===
@with_error_handling("explorer")
async def run_explorer(session: Session) -> Dict[str, Any]:
    ...

@with_error_handling("planner")
async def run_planner(session: Session) -> Dict[str, Any]:
    ...

@with_error_handling("developer")
async def run_developer(session: Session) -> Dict[str, Any]:
    ...

@with_error_handling("reviewer")
async def run_reviewer(session: Session) -> Dict[str, Any]:
    ...

@with_error_handling("tester")
async def run_tester(session: Session) -> Dict[str, Any]:
    ...
```

### 6.4 会话启动与人工决策恢复

```python
from agents import Session, ResumeCommand
from typing import Dict, Any, Literal, Optional

async def submit_human_decision(
    session_id: str,
    decision: Literal["APPROVE", "REJECT", "REQUEST_CHANGES", "ADD_NOTES"],
    comment: Optional[str] = None,
    selected_opportunity_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    人类提交审核决策，恢复工作流。

    流程:
    1. 加载当前 Session
    2. 验证决策合法性
    3. 更新 Session 状态
    4. 根据决策确定下一个 Agent
    5. 恢复工作流执行
    """
    # 加载 Session
    session = await checkpointer.load_session(session_id)
    if not session:
        raise InvalidStateError(f"Session {session_id} not found")

    ctx = session.context

    # 验证状态
    if ctx.get("status") != "interrupted":
        raise InvalidStateError(
            f"Session {session_id} is not in interrupted state (current: {ctx.get('status')})"
        )

    current_stage = ctx.get("current_stage")
    config = INTERRUPT_CONFIGS.get(current_stage)
    if not config:
        raise InvalidStateError(f"No interrupt config for stage {current_stage}")

    # 验证决策合法性
    if decision not in config["allowed_decisions"]:
        raise InvalidDecisionError(
            f"Decision '{decision}' not allowed for stage {current_stage}. "
            f"Allowed: {config['allowed_decisions']}"
        )

    # 验证必填字段
    required = config["required_fields"].get(decision, [])
    for field in required:
        if field == "selected_opportunity_id" and not selected_opportunity_id:
            raise InvalidDecisionError(
                f"Field 'selected_opportunity_id' is required for decision '{decision}'"
            )
        if field == "comment" and not comment:
            raise InvalidDecisionError(
                f"Field 'comment' is required for decision '{decision}'"
            )

    # 构建人类决策记录
    human_decision = {
        "stage": current_stage,
        "decision": decision,
        "comment": comment,
        "selected_opportunity_id": selected_opportunity_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # 更新 Session 状态
    ctx["human_decisions"] = ctx.get("human_decisions", []) + [human_decision]
    if comment:
        ctx["human_notes"] = ctx.get("human_notes", []) + [comment]
    ctx["status"] = "running"
    ctx["last_human_decision"] = decision

    # 特殊处理：选中机会传递
    if selected_opportunity_id and current_stage == "HUMAN_REVIEW_EXPLORATION":
        exploration_result = ctx.get("exploration_result", {})
        opportunities = exploration_result.get("opportunities", [])
        selected = next(
            (o for o in opportunities if o["id"] == selected_opportunity_id),
            None
        )
        if selected:
            ctx["selected_opportunity"] = selected
        else:
            raise InvalidDecisionError(
                f"Selected opportunity {selected_opportunity_id} not found in exploration result"
            )

    # 保存状态
    await checkpointer.save_session(session)

    # 确定下一个 Agent 并恢复
    next_agent_name = config["next_agent_map"][decision]

    # 构建 ResumeCommand
    resume_cmd = ResumeCommand(
        decision=decision,
        next_agent=next_agent_name,
        state_updates={
            "status": "running",
            "current_stage": _map_next_stage(current_stage, next_agent_name),
        }
    )

    # 恢复 Session 执行
    await session.resume(resume_cmd)

    return {
        "session_id": session_id,
        "decision": decision,
        "next_stage": resume_cmd.state_updates["current_stage"],
        "status": "resumed",
    }

def _map_next_stage(current_stage: str, next_agent: str) -> str:
    """映射下一个阶段名称。"""
    stage_map = {
        ("HUMAN_REVIEW_EXPLORATION", "planner"): "PLANNING",
        ("HUMAN_REVIEW_EXPLORATION", "explorer"): "EXPLORATION",
        ("HUMAN_REVIEW_PLANNING", "developer"): "DEVELOPMENT",
        ("HUMAN_REVIEW_PLANNING", "planner"): "PLANNING",
        ("HUMAN_REVIEW_CODE", "tester"): "TESTING",
        ("HUMAN_REVIEW_CODE", "developer"): "DEVELOPMENT",
        ("HUMAN_REVIEW_TESTING", "finalize"): "COMPLETION",
        ("HUMAN_REVIEW_TESTING", "developer"): "DEVELOPMENT",
    }
    return stage_map.get((current_stage, next_agent), "UNKNOWN")
```

---

## 7. v1 → v2 编排迁移

### 7.1 LangGraph → OpenAI Agents SDK 映射

| LangGraph (v1) | OpenAI Agents SDK (v2) | 迁移说明 |
|----------------|------------------------|----------|
| `StateGraph(RVInsightsState)` | `Agent(name="orchestrator", ...)` + `handoff()` | StateGraph 被 Orchestrator Agent 替代；状态从 TypedDict 变为 Session.context |
| `builder.add_node(name, func)` | `Agent(name, instructions, tools)` | 节点逻辑封装为 Agent 的 instructions 和 tools |
| `builder.add_edge(src, dst)` | `src_agent.handoffs = [handoff(target=dst_agent)]` | 显式 Handoff 替代隐式边 |
| `builder.add_conditional_edges(src, condition, mapping)` | `src_agent.handoffs = [handoff(target, condition=lambda ctx: ...), ...]` | 条件 Handoff 替代条件边 |
| `builder.compile(checkpointer=...)` | `Session(store=PostgresSessionStore)` | Checkpointer 被 Session Store 替代 |
| `graph.invoke(state, config)` | `session.run(agent)` 或 `agent.run(session=session)` | 调用方式从函数式变为面向对象 |
| `interrupt_before=[nodes]` | `interrupt(agent, message, metadata)` | 显式 interrupt 调用替代配置式中断 |
| `graph.get_state(config)` | `session.context` | 状态访问从查询变为属性访问 |

### 7.2 Checkpointer → OpenAI Session 持久化

```python
# === v1: LangGraph Checkpointer ===
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver(
    conn_string=os.environ["POSTGRES_URL"],
    checkpoint_table="checkpoints",
)

graph = builder.compile(checkpointer=checkpointer)

# 保存 checkpoint (自动)
# graph.invoke(state, config) 内部自动调用 checkpointer.put()

# 加载状态
state = graph.get_state(config={"configurable": {"thread_id": session_id}})

# === v2: OpenAI Session Store ===
from agents.sessions import PostgresSessionStore

session_store = PostgresSessionStore(
    connection_string=os.environ["POSTGRES_URL"],
    table_name="openai_sessions",
)

session = Session(
    session_id=session_id,
    context=RVInsightsContext(...),
    store=session_store,
)

# 保存 Session (显式或自动)
await session.save()  # 或 agent.run(session=session) 内部自动保存

# 加载 Session
session = await session_store.load(session_id)
context = session.context
```

**关键差异**:
1. **状态结构**: v1 的 `TypedDict` 变为 v2 的 `Context` 子类 (属性访问替代字典访问)
2. **保存时机**: v1 在每个节点后自动保存；v2 在每次 Handoff 后自动保存，也可显式调用 `session.save()`
3. **恢复方式**: v1 通过 `graph.get_state()` 恢复；v2 通过 `session_store.load()` 恢复完整 Session
4. **子图 checkpoint**: v1 使用独立的 `subgraph_checkpoints` 表；v2 使用 Session 的嵌套 Context 或独立的 Session 实例

### 7.3 AutoGen 群聊管理器 → OpenAI Handoff

```python
# === v1: AutoGen 群聊 ===
from autogen import GroupChat, GroupChatManager

groupchat = GroupChat(
    agents=[mail_scanner, issue_miner, code_analyst],
    messages=[],
    max_round=10,
)
manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)

# 启动群聊
result = manager.initiate_chat(
    recipient=manager,
    message="扫描 RISC-V 生态贡献机会",
)

# === v2: OpenAI Agents SDK 并发调度 + Claude Subagent ===
from agents import Agent, handoff
import asyncio

# OpenAI Agents 并发执行广度扫描
mail_scanner = Agent(name="MailScanner", model="gpt-4.1", ...)
issue_miner = Agent(name="IssueMiner", model="gpt-4.1", ...)
code_analyst = Agent(name="CodeAnalyst", model="gpt-4.1", ...)

async def run_exploration_parallel(session: Session) -> Dict[str, Any]:
    # 并发启动三个子 Agent
    tasks = [
        mail_scanner.run(session=session),
        issue_miner.run(session=session),
        code_analyst.run(session=session),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 汇总结果
    opportunities = _merge_results(results)

    # 对每个候选机会调用 Claude Subagent 深度验证
    validated = []
    for opp in opportunities:
        feasibility = await claude_subagent_validate(opp, session)
        opp["feasibility_score"] = feasibility["score"]
        opp["claude_confidence"] = feasibility["confidence"]
        validated.append(opp)

    return {"opportunities": validated}

# Claude Subagent (深度验证)
from anthropic.agents import Subagent

feasibility_judge = Subagent(
    model="claude-sonnet-4-5",
    instructions="验证候选贡献机会的技术可行性...",
    max_tokens=4000,
)

async def claude_subagent_validate(opportunity: Dict, session: Session) -> Dict:
    result = await feasibility_judge.run(
        prompt=f"验证以下机会: {json.dumps(opportunity)}"
    )
    return json.loads(result.content)
```

**关键差异**:
1. **调度方式**: AutoGen 群聊是顺序轮询；v2 使用 `asyncio.gather` 真正并发
2. **角色抽象**: AutoGen 的 `ConversableAgent` 角色抽象被 OpenAI `Agent` 替代，更轻量
3. **深度验证**: v1 在群聊内由特定角色执行；v2 通过 Claude Subagent 隔离上下文执行
4. **结果汇总**: v1 由 GroupChatManager 自动汇总；v2 显式合并结果

### 7.4 crewAI 顺序/分层任务流 → OpenAI 条件 Handoff

```python
# === v1: crewAI 分层任务流 ===
from crewai import Crew, Agent, Task

developer = Agent(role="Developer", ...)
reviewer = Agent(role="Reviewer", ...)

dev_task = Task(description="实现代码变更", agent=developer)
review_task = Task(description="审核代码", agent=reviewer)

# crewAI 的迭代循环通过自定义逻辑实现
crew = Crew(
    agents=[developer, reviewer],
    tasks=[dev_task, review_task],
    process=Process.sequential,
)

# 外部控制迭代 (v1 中需要手动实现)
for iteration in range(max_iterations):
    result = crew.kickoff()
    if result["verdict"] == "PASS":
        break
    # 否则继续迭代 (crewAI 不原生支持)

# === v2: OpenAI 条件 Handoff 迭代循环 ===
# 见第2节开发-审核迭代子图

# 核心差异：迭代循环是 OpenAI Handoff 的一等公民
reviewer_agent.handoffs = [
    handoff(
        target=developer_agent,
        condition=lambda ctx: route_review_condition(ctx) == "NEEDS_REVISION",
    ),
    handoff(
        target=orchestrator_agent,
        condition=lambda ctx: route_review_condition(ctx) in ["PASS", "MAX_ITERATIONS"],
    ),
]

# 迭代计数和状态管理通过 Session.context 实现
# 无需外部循环，Handoff 条件自动驱动迭代
```

**关键差异**:
1. **循环控制**: crewAI 需要外部循环控制；OpenAI Handoff 条件原生支持循环
2. **状态传递**: crewAI 通过 Task 上下文传递；OpenAI 通过 Session.context 共享
3. **退出条件**: crewAI 需要手动检查；OpenAI Handoff condition 自动判断
4. **人工介入**: crewAI 无原生支持；OpenAI interrupt 内建

### 7.5 迁移检查清单

| 检查项 | v1 状态 | v2 状态 | 验证方法 |
|--------|---------|---------|----------|
| 全局状态机 | LangGraph StateGraph | OpenAI Orchestrator Agent | 运行端到端测试 |
| 开发-审核迭代 | crewAI 外部循环 | OpenAI 条件 Handoff | 5次迭代收敛测试 |
| 人工审核中断 | LangGraph interrupt | OpenAI interrupt | UI 点击测试 |
| Session 持久化 | LangGraph Checkpointer | OpenAI PostgresSessionStore | 重启恢复测试 |
| 错误重试 | 自定义装饰器 | 增强装饰器 + SDK 错误映射 | 注入错误测试 |
| Git 锁 | Redis 分布式锁 | 同 v1 (无变更) | 并发写测试 |
| QEMU 池 | Redis 列表池 | 同 v1 (无变更) | 资源耗尽测试 |
| 超时管理 | 自定义 TimeoutManager | 同 v1 (适配 Session) | 长时运行测试 |
| 孤儿检测 | OrphanSessionDetector | 同 v1 (无变更) | 强制杀进程测试 |
| 子图 checkpoint | PostgresSaver | Session 嵌套 Context | 子图中断恢复测试 |

---

## 8. 附录

### 8.1 错误类型层次 (v2 完整版)

```python
class RVIError(Exception):
    """RV-Insights 基础异常。"""
    pass

class RetryableError(RVIError):
    """可重试错误基类。"""
    pass

class NonRetryableError(RVIError):
    """不可重试错误基类。"""
    pass

# === OpenAI SDK 错误 ===
class OpenAIRateLimitError(RetryableError): pass
class OpenAITimeoutError(RetryableError): pass
class OpenAIContentFilterError(NonRetryableError): pass
class OpenAIAuthError(NonRetryableError): pass
class GuardrailsInterceptError(NonRetryableError): pass

# === Claude SDK 错误 ===
class ClaudeRateLimitError(RetryableError): pass
class ClaudeTimeoutError(RetryableError): pass
class ClaudeContentFilterError(NonRetryableError): pass

# === 应用错误 ===
class ExplorationError(NonRetryableError): pass
class PlanningError(NonRetryableError): pass
class DevelopmentError(NonRetryableError): pass
class ReviewError(NonRetryableError): pass
class TestingError(NonRetryableError): pass
class GitLockTimeoutError(RetryableError): pass
class QuotaExceededError(RetryableError): pass
class SandboxCrashError(NonRetryableError): pass
class SandboxProviderError(RetryableError): pass
class CompilationError(NonRetryableError): pass
class MaxRetriesExceededError(NonRetryableError): pass
class InvalidStateError(NonRetryableError): pass
class InvalidDecisionError(NonRetryableError): pass
```

### 8.2 环境变量清单

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `RVI_WORKSPACE_BASE` | 工作目录根路径 | `/var/rv-insights/workspaces` |
| `POSTGRES_URL` | PostgreSQL 连接字符串 | `postgresql://user:pass@localhost/rvi` |
| `REDIS_URL` | Redis 连接字符串 | `redis://localhost:6379/0` |
| `OPENAI_API_KEY` | OpenAI API 密钥 | `sk-...` |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 | `sk-ant-...` |
| `MCP_SERVER_URL` | MCP-Server RPC 地址 | `http://localhost:8080` |
| `MCP_RAG_URL` | MCP-RAG Server 地址 | `http://localhost:8081` |
| `MCP_QEMU_URL` | MCP-QEMU Server 地址 | `http://localhost:8082` |
| `S3_BUCKET` | 产物存储桶 | `rvinsights-artifacts` |

### 8.3 数据库表清单

| 表名 | 用途 | 管理者 | SDK |
|------|------|--------|-----|
| `openai_sessions` | OpenAI SDK Session 持久化 | OpenAI SDK | OpenAI |
| `rvinsights_sessions` | 应用层会话状态 | 应用层 | - |
| `session_checkpoints` | 显式 checkpoint | 应用层 | - |
| `human_decisions` | 人工审核记录 | 应用层 | - |
| `git_locks` | Git 仓库写锁状态 | 应用层 | - |
| `qemu_occupancy` | QEMU 实例占用状态 | 应用层 | - |
| `dead_letter_queue` | 死信队列 | 应用层 | - |
| `agent_logs` | Agent 执行日志 | 应用层 | - |

---

*文档结束。本文件为 RV-Insights v2 编排层的设计基准，所有实现代码应与此文档保持一致。如有变更，需同步更新本文档。*
