# RV-Insights: LangGraph 工作流编排深度设计

**版本**: v1.1
**日期**: 2026-04-21
**目标**: 细化 RV-Insights 五阶段工作流的 LangGraph 编排实现，覆盖节点定义、边路由、错误处理、并发控制、生命周期管理、子图契约及完整伪代码实现。

---

## 1. 全局 StateGraph 节点详细定义

### 1.1 状态定义 (RVInsightsState)

```python
from typing import TypedDict, Optional, List, Dict, Any, Literal
from dataclasses import dataclass

class RVInsightsState(TypedDict):
    # === 会话元数据 ===
    session_id: str
    tenant_id: str
    created_at: str  # ISO 8601
    updated_at: str
    current_stage: Literal[
        "INITIALIZATION", "EXPLORATION", "HUMAN_REVIEW_EXPLORATION",
        "PLANNING", "HUMAN_REVIEW_PLANNING",
        "DEVELOPMENT", "REVIEW", "HUMAN_REVIEW_CODE",
        "TESTING", "HUMAN_REVIEW_TESTING", "COMPLETION", "FAILED"
    ]
    status: Literal["running", "interrupted", "completed", "failed", "cancelled"]

    # === 各阶段产物 ===
    exploration_result: Optional[Dict[str, Any]]
    planning_result: Optional[Dict[str, Any]]
    development_result: Optional[Dict[str, Any]]
    review_result: Optional[Dict[str, Any]]
    testing_result: Optional[Dict[str, Any]]

    # === 迭代控制 ===
    dev_review_iteration_count: int  # 默认 0
    max_dev_review_iterations: int   # 默认 5

    # === 人工审核记录 ===
    human_decisions: List[Dict[str, Any]]
    human_notes: List[str]

    # === 审计与追踪 ===
    agent_logs: List[Dict[str, Any]]
    timestamps: List[Dict[str, Any]]

    # === 错误与恢复 ===
    last_error: Optional[Dict[str, Any]]
    retry_count: int  # 当前节点重试次数

    # === 资源与锁 ===
    workspace_path: Optional[str]
    git_lock_id: Optional[str]
    qemu_instance_id: Optional[str]
```

### 1.2 节点定义总览

| 节点 | 类型 | 幂等性 | 超时 | 重试策略 |
|------|------|--------|------|----------|
| `initialize_session` | 普通节点 | 是 | 30s | 3次，指数退避 |
| `run_exploration` | 普通节点 | 否 | 2h | 3次，指数退避 |
| `human_review_exploration` | interrupt | - | 无限制 | - |
| `run_planning` | 普通节点 | 否 | 1h | 3次，指数退避 |
| `human_review_planning` | interrupt | - | 无限制 | - |
| `run_development` | 普通节点 | 否 | 4h | 3次，指数退避 |
| `run_review` | 普通节点 | 否 | 30min | 3次，指数退避 |
| `route_review` | 条件路由 | 是 | 5s | 不重试 |
| `human_review_code` | interrupt | - | 无限制 | - |
| `run_testing` | 普通节点 | 否 | 3h | 3次，指数退避 |
| `human_review_testing` | interrupt | - | 无限制 | - |
| `finalize` | 普通节点 | 是 | 60s | 3次，指数退避 |

---

### 1.3 `initialize_session` - 会话初始化

```python
def initialize_session(state: RVInsightsState) -> Dict[str, Any]:
    """
    会话初始化节点。
    加载租户配置，初始化工作目录，准备会话上下文。

    输入状态字段:
        - session_id: str (required)
        - tenant_id: str (required)
        - created_at: str (optional, 不存在则生成)

    输出状态字段 (updates):
        - current_stage: "INITIALIZATION"
        - status: "running"
        - workspace_path: str
        - timestamps: append {stage: "INITIALIZATION", entered_at: str}

    副作用:
        - DB: 写入 sessions 表 (session_id, tenant_id, status)
        - 文件系统: 创建 {WORKSPACE_BASE}/{tenant_id}/{session_id}/ 目录
        - 网络: 无

    幂等性: 是。重复调用时若目录已存在则跳过创建。
    超时: 30秒
    重试: 3次，base=2, max_delay=60s
    """
    import os
    from datetime import datetime, timezone

    session_id = state["session_id"]
    tenant_id = state["tenant_id"]
    workspace_base = os.environ.get("RVI_WORKSPACE_BASE", "/var/rv-insights/workspaces")
    workspace_path = os.path.join(workspace_base, tenant_id, session_id)

    # 幂等创建
    os.makedirs(workspace_path, exist_ok=True)
    os.makedirs(os.path.join(workspace_path, "artifacts"), exist_ok=True)
    os.makedirs(os.path.join(workspace_path, "logs"), exist_ok=True)

    return {
        "current_stage": "INITIALIZATION",
        "status": "running",
        "workspace_path": workspace_path,
        "timestamps": state.get("timestamps", []) + [{
            "stage": "INITIALIZATION",
            "entered_at": datetime.now(timezone.utc).isoformat()
        }],
        "retry_count": 0,
        "last_error": None,
    }
```

---

### 1.4 `run_exploration` - 探索执行

```python
def run_exploration(state: RVInsightsState) -> Dict[str, Any]:
    """
    调用探索Agent (AutoGen 多智能体群聊)。
    扫描 RISC-V 生态，发现、验证并排序贡献机会。

    输入状态字段:
        - session_id: str
        - workspace_path: str
        - exploration_result: None (覆盖写入)
        - agent_logs: List (追加)

    输出状态字段 (updates):
        - current_stage: "EXPLORATION"
        - exploration_result: Dict | None
        - agent_logs: append
        - timestamps: append
        - last_error: Dict | None

    副作用:
        - DB: 写入 agent_logs 表
        - 文件系统: 写入 {workspace}/artifacts/exploration_report.json
        - 网络: GitHub API, 邮件列表, Web搜索

    幂等性: 否。每次调用消耗 API Token，产生新结果。
    超时: 2小时 (7200s)
    重试: 3次，base=2, max_delay=60s (仅针对可重试错误)

    部分失败处理:
        - 若部分子Agent失败 (如 MailScanner 超时)，根据 tenant_config["exploration_partial_failure_policy"]
          决定: "continue" (继续，标记缺失数据) | "fail" (整体失败)
    """
    from datetime import datetime, timezone
    import json

    # 加载租户配置
    tenant_config = load_tenant_config(state["tenant_id"])
    partial_policy = tenant_config.get("exploration_partial_failure_policy", "continue")

    try:
        # 调用 AutoGen 探索Agent群
        explorer = AutoGenExplorerGroup(
            session_id=state["session_id"],
            workspace=state["workspace_path"],
            config=tenant_config["exploration"]
        )
        result = explorer.run(partial_failure_policy=partial_policy)

        # 持久化报告
        report_path = os.path.join(state["workspace_path"], "artifacts", "exploration_report.json")
        with open(report_path, "w") as f:
            json.dump(result, f, indent=2)

        return {
            "current_stage": "EXPLORATION",
            "exploration_result": result,
            "agent_logs": state.get("agent_logs", []) + [{
                "stage": "EXPLORATION",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "status": "completed",
                "partial_failures": result.get("partial_failures", [])
            }],
            "timestamps": state.get("timestamps", []) + [{
                "stage": "EXPLORATION",
                "entered_at": datetime.now(timezone.utc).isoformat()
            }],
            "last_error": None,
            "retry_count": 0,
        }

    except ExplorationError as e:
        return _handle_node_error(state, "EXPLORATION", e, retryable=isinstance(e, RetryableExplorationError))
```

---

### 1.5 `human_review_exploration` - 人工审核 (探索)

```python
def human_review_exploration(state: RVInsightsState) -> Dict[str, Any]:
    """
    interrupt 节点：等待人工审核探索结果。

    输入状态字段:
        - exploration_result: Dict (required, 供UI展示)
        - session_id: str

    输出状态字段 (updates):
        - status: "interrupted"
        - human_decisions: append (resume时写入)
        - human_notes: append (可选)

    副作用:
        - DB: 更新 sessions.status = "interrupted"
        - 网络: 向 UI 推送 SSE 事件 (review_required)

    幂等性: N/A (interrupt 节点由 LangGraph 运行时管理)
    超时: 无限制 (人工审核不设超时)
    重试: N/A

    恢复命令:
        - APPROVE: 进入 PLANNING
        - REJECT: 进入 COMPLETION (失败归档)
        - REQUEST_CHANGES: 回到 EXPLORATION (携带 human_notes)
        - ADD_NOTES: 进入 PLANNING (携带 human_notes)
    """
    # LangGraph interrupt 机制自动处理
    # 此处仅声明节点，实际 interrupt 由 graph.compile(checkpointer=...) 支持
    return {
        "status": "interrupted",
        "current_stage": "HUMAN_REVIEW_EXPLORATION",
    }
```

---

### 1.6 `run_planning` - 规划执行

```python
def run_planning(state: RVInsightsState) -> Dict[str, Any]:
    """
    调用规划Agent (MetaGPT SOP驱动)。
    将审核通过的贡献机会转化为结构化开发与测试方案。

    输入状态字段:
        - exploration_result: Dict (required, 取 opportunities 中人类选中的项)
        - human_decisions: List (最后一条应为 APPROVE/ADD_NOTES)
        - workspace_path: str

    输出状态字段 (updates):
        - current_stage: "PLANNING"
        - planning_result: Dict
        - agent_logs: append
        - timestamps: append

    副作用:
        - DB: 写入 agent_logs
        - 文件系统: 写入 {workspace}/artifacts/development_plan.md, testing_plan.md
        - 网络: RAG 知识库查询, GitHub API (确认代码路径)

    幂等性: 否。
    超时: 1小时 (3600s)
    重试: 3次，base=2, max_delay=60s
    """
    from datetime import datetime, timezone
    import json

    # 提取人类选中的机会 (由前端在 resume 时注入 selected_opportunity_id)
    approved_opportunity = _extract_approved_opportunity(state)

    try:
        planner = MetaGPTPlanner(
            session_id=state["session_id"],
            workspace=state["workspace_path"],
            opportunity=approved_opportunity,
            rag_client=RAGClient(),
        )
        result = planner.run()

        # 持久化方案文档
        for doc_name, content in result["artifacts"].items():
            doc_path = os.path.join(state["workspace_path"], "artifacts", f"{doc_name}.md")
            with open(doc_path, "w") as f:
                f.write(content)

        return {
            "current_stage": "PLANNING",
            "planning_result": result,
            "agent_logs": state.get("agent_logs", []) + [{
                "stage": "PLANNING",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "status": "completed",
            }],
            "timestamps": state.get("timestamps", []) + [{
                "stage": "PLANNING",
                "entered_at": datetime.now(timezone.utc).isoformat()
            }],
            "last_error": None,
            "retry_count": 0,
        }

    except PlanningError as e:
        return _handle_node_error(state, "PLANNING", e, retryable=isinstance(e, RetryablePlanningError))
```

---

### 1.7 `human_review_planning` - 人工审核 (规划)

```python
def human_review_planning(state: RVInsightsState) -> Dict[str, Any]:
    """
    interrupt 节点：等待人工审核规划方案。

    恢复命令:
        - APPROVE: 进入 DEVELOPMENT
        - REJECT: 进入 COMPLETION (失败归档)
        - REQUEST_CHANGES: 回到 PLANNING
        - ADD_NOTES: 进入 DEVELOPMENT
    """
    return {
        "status": "interrupted",
        "current_stage": "HUMAN_REVIEW_PLANNING",
    }
```

---

### 1.8 `run_development` - 开发执行

```python
def run_development(state: RVInsightsState) -> Dict[str, Any]:
    """
    调用开发Agent (Claude Code API)。
    在隔离环境中完成代码实现、静态检查、编译验证、单元测试。

    输入状态字段:
        - planning_result: Dict (required, development_plan)
        - workspace_path: str
        - git_lock_id: str | None

    输出状态字段 (updates):
        - current_stage: "DEVELOPMENT"
        - development_result: Dict
        - agent_logs: append
        - timestamps: append

    副作用:
        - DB: 写入 agent_logs, 更新 git_locks 表
        - 文件系统: 在 workspace 内执行 git clone/checkout/branch/commit
        - 网络: Git 操作 (clone/fetch), MCP-Server RPC (沙箱执行)
        - 外部: 占用 Git 仓库写锁

    幂等性: 否。
    超时: 4小时 (14400s)
    重试: 3次，base=2, max_delay=60s

    编译失败自修复:
        - 开发Agent内部实现最多 3 次自修复循环 (编译 -> 失败 -> 分析日志 -> 修复)
        - 若 3 次后仍失败，development_result["build_status"] = "FAILED"
        - 审核Agent会据此给出 REJECT 或 NEEDS_REVISION
    """
    from datetime import datetime, timezone

    # 获取或申请 Git 写锁
    git_lock = acquire_git_lock(
        repo_url=state["planning_result"]["target_repo"]["clone_url"],
        session_id=state["session_id"],
        timeout=300  # 等待锁最多5分钟
    )

    try:
        developer = ClaudeCodeDeveloper(
            session_id=state["session_id"],
            workspace=state["workspace_path"],
            development_plan=state["planning_result"]["development_plan"],
            git_lock=git_lock,
            mcp_client=MCPClient(),
        )
        result = developer.run(max_self_fix_attempts=3)

        return {
            "current_stage": "DEVELOPMENT",
            "development_result": result,
            "git_lock_id": git_lock["lock_id"],
            "agent_logs": state.get("agent_logs", []) + [{
                "stage": "DEVELOPMENT",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "status": "completed" if result["build_status"] == "SUCCESS" else "completed_with_errors",
                "build_status": result["build_status"],
                "self_fix_attempts": result.get("self_fix_attempts", 0),
            }],
            "timestamps": state.get("timestamps", []) + [{
                "stage": "DEVELOPMENT",
                "entered_at": datetime.now(timezone.utc).isoformat()
            }],
            "last_error": None,
            "retry_count": 0,
        }

    except DevelopmentError as e:
        return _handle_node_error(state, "DEVELOPMENT", e, retryable=isinstance(e, RetryableDevelopmentError))
    finally:
        # 注意：此处不释放锁，锁在子图退出或会话结束时释放
        pass
```

---

### 1.9 `run_review` - 审核执行

```python
def run_review(state: RVInsightsState) -> Dict[str, Any]:
    """
    调用审核Agent (Codex / Claude API)。
    对开发产物进行多维度结构化审查。

    输入状态字段:
        - development_result: Dict (required)
        - planning_result: Dict (required, 作为验收基准)
        - dev_review_iteration_count: int

    输出状态字段 (updates):
        - current_stage: "REVIEW"
        - review_result: Dict
        - agent_logs: append
        - timestamps: append

    副作用:
        - DB: 写入 agent_logs
        - 文件系统: 写入 {workspace}/artifacts/review_report_{iter}.json
        - 网络: LLM API 调用

    幂等性: 否 (每次迭代产生不同审核结果)。
    超时: 30分钟 (1800s)
    重试: 3次，base=2, max_delay=60s
    """
    from datetime import datetime, timezone
    import json

    iteration = state["dev_review_iteration_count"]

    try:
        reviewer = CodexReviewer(
            session_id=state["session_id"],
            development_result=state["development_result"],
            development_plan=state["planning_result"]["development_plan"],
            iteration_count=iteration,
            rag_client=RAGClient(),
        )
        result = reviewer.run()

        # 持久化审核报告
        report_path = os.path.join(
            state["workspace_path"], "artifacts", f"review_report_{iteration}.json"
        )
        with open(report_path, "w") as f:
            json.dump(result, f, indent=2)

        return {
            "current_stage": "REVIEW",
            "review_result": result,
            "agent_logs": state.get("agent_logs", []) + [{
                "stage": "REVIEW",
                "iteration": iteration,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "status": "completed",
                "verdict": result["overall_verdict"],
            }],
            "timestamps": state.get("timestamps", []) + [{
                "stage": "REVIEW",
                "iteration": iteration,
                "entered_at": datetime.now(timezone.utc).isoformat()
            }],
            "last_error": None,
            "retry_count": 0,
        }

    except ReviewError as e:
        return _handle_node_error(state, "REVIEW", e, retryable=isinstance(e, RetryableReviewError))
```

---

### 1.10 `route_review` - 审核路由判断

```python
def route_review(state: RVInsightsState) -> Literal["PASS", "NEEDS_REVISION", "REJECT", "MAX_ITERATIONS"]:
    """
    条件路由节点：根据审核结果和迭代次数决定下一跳。

    输入状态字段:
        - review_result: Dict (required)
        - dev_review_iteration_count: int
        - max_dev_review_iterations: int

    输出: 路由标签 (str)

    副作用: 无

    幂等性: 是 (纯函数，仅基于状态计算)。
    超时: 5秒
    重试: 不重试
    """
    review_result = state.get("review_result", {})
    verdict = review_result.get("overall_verdict", "NEEDS_REVISION")
    iteration = state["dev_review_iteration_count"]
    max_iter = state["max_dev_review_iterations"]

    if verdict == "PASS":
        # 即使verdict为PASS，也必须检查是否存在未解决的blocking issue
        blocking_issues = [
            issue for issue in review_result.get("issues", [])
            if issue.get("blocking", False)
        ]
        if not blocking_issues:
            return "PASS"
        # 存在blocking issue但verdict为PASS，降级为NEEDS_REVISION
        return "NEEDS_REVISION"

    if verdict == "REJECT":
        return "REJECT"

    # NEEDS_REVISION 分支
    if iteration >= max_iter:
        return "MAX_ITERATIONS"

    return "NEEDS_REVISION"
```

---

### 1.11 `human_review_code` - 人工审核 (代码)

```python
def human_review_code(state: RVInsightsState) -> Dict[str, Any]:
    """
    interrupt 节点：开发-审核迭代完成后，等待人类最终裁决。

    输入状态字段:
        - development_result: Dict (required, 展示 patch)
        - review_result: Dict (required, 展示审核报告)
        - dev_review_iteration_count: int
        - agent_logs: List (展示迭代历史)

    恢复命令:
        - APPROVE: 进入 TESTING
        - REJECT: 进入 COMPLETION (失败归档)
        - REQUEST_CHANGES: 回到 DEVELOPMENT (重置 iteration_count 或保留，取决于策略)
        - ADD_NOTES: 进入 TESTING
    """
    return {
        "status": "interrupted",
        "current_stage": "HUMAN_REVIEW_CODE",
    }
```

---

### 1.12 `run_testing` - 测试执行

```python
def run_testing(state: RVInsightsState) -> Dict[str, Any]:
    """
    调用测试Agent (crewAI 角色执行)。
    搭建环境并执行单元测试、集成测试、仿真测试、性能基准。

    输入状态字段:
        - testing_plan: Dict (from planning_result)
        - development_result: Dict (approved_code)
        - workspace_path: str
        - qemu_instance_id: str | None

    输出状态字段 (updates):
        - current_stage: "TESTING"
        - testing_result: Dict
        - agent_logs: append
        - timestamps: append

    副作用:
        - DB: 写入 agent_logs
        - 文件系统: 写入测试日志、报告
        - 网络: QEMU 镜像下载 (如需)
        - 外部: 占用 QEMU 虚拟机实例

    幂等性: 否。
    超时: 3小时 (10800s)
    重试: 3次，base=2, max_delay=60s

    环境搭建失败处理:
        - EnvSetupEngineer 失败时，尝试使用备用镜像或配置
        - 若所有备用方案失败，testing_result["overall_status"] = "FAIL"
        - 标记 environment_setup_failed = True，供人工审核时参考
    """
    from datetime import datetime, timezone

    # 申请 QEMU 实例
    qemu = acquire_qemu_instance(
        config=state["planning_result"]["testing_plan"]["emulation_configs"][0],
        session_id=state["session_id"],
        timeout=600  # 等待实例最多10分钟
    )

    try:
        tester = CrewAITester(
            session_id=state["session_id"],
            workspace=state["workspace_path"],
            testing_plan=state["planning_result"]["testing_plan"],
            approved_code=state["development_result"],
            qemu_instance=qemu,
            mcp_client=MCPClient(),
        )
        result = tester.run(environment_fallback=True)

        return {
            "current_stage": "TESTING",
            "testing_result": result,
            "qemu_instance_id": qemu["instance_id"],
            "agent_logs": state.get("agent_logs", []) + [{
                "stage": "TESTING",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "status": "completed",
                "overall_status": result["overall_status"],
            }],
            "timestamps": state.get("timestamps", []) + [{
                "stage": "TESTING",
                "entered_at": datetime.now(timezone.utc).isoformat()
            }],
            "last_error": None,
            "retry_count": 0,
        }

    except TestingError as e:
        return _handle_node_error(state, "TESTING", e, retryable=isinstance(e, RetryableTestingError))
    finally:
        # 测试完成后释放 QEMU 实例 (或延迟释放供调试)
        release_qemu_instance(qemu["instance_id"], delay_minutes=30)
```

---

### 1.13 `human_review_testing` - 人工审核 (测试)

```python
def human_review_testing(state: RVInsightsState) -> Dict[str, Any]:
    """
    interrupt 节点：等待人工审核测试结果。

    恢复命令:
        - APPROVE: 进入 COMPLETION (成功)
        - REJECT: 进入 COMPLETION (失败归档)
        - REQUEST_CHANGES: 回到 DEVELOPMENT (修复代码后重新测试)
        - ADD_NOTES: 进入 COMPLETION
    """
    return {
        "status": "interrupted",
        "current_stage": "HUMAN_REVIEW_TESTING",
    }
```

---

### 1.14 `finalize` - 会话归档

```python
def finalize(state: RVInsightsState) -> Dict[str, Any]:
    """
    归档会话，清理资源，生成最终产物包。

    输入状态字段:
        - session_id: str
        - status: str (completed | failed | cancelled)
        - workspace_path: str
        - all_results: Dict (各阶段产物)

    输出状态字段 (updates):
        - current_stage: "COMPLETION"
        - status: "completed" | "failed" | "cancelled"
        - timestamps: append

    副作用:
        - DB: 更新 sessions.status, 写入 session_summary
        - 文件系统: 打包 {workspace}/final_artifacts.zip
        - S3: 上传产物包、日志、报告
        - 外部: 释放 Git 锁、QEMU 实例、清理沙箱

    幂等性: 是。重复调用时若已归档则跳过。
    超时: 60秒
    重试: 3次，base=2, max_delay=60s
    """
    from datetime import datetime, timezone
    import shutil

    # 释放所有资源
    if state.get("git_lock_id"):
        release_git_lock(state["git_lock_id"])
    if state.get("qemu_instance_id"):
        release_qemu_instance(state["qemu_instance_id"], delay_minutes=0)

    # 清理沙箱工作目录 (保留 artifacts)
    sandbox_path = os.path.join(state["workspace_path"], "sandbox")
    if os.path.exists(sandbox_path):
        shutil.rmtree(sandbox_path, ignore_errors=True)

    # 上传产物到 S3
    s3_key = f"sessions/{state['tenant_id']}/{state['session_id']}/final_artifacts.zip"
    upload_workspace_to_s3(state["workspace_path"], s3_key)

    return {
        "current_stage": "COMPLETION",
        "status": state.get("status", "completed"),
        "timestamps": state.get("timestamps", []) + [{
            "stage": "COMPLETION",
            "entered_at": datetime.now(timezone.utc).isoformat()
        }],
    }
```

---

## 2. Edge 条件表达式

### 2.1 全局图边定义

```python
from langgraph.graph import StateGraph, END

# 构建图
builder = StateGraph(RVInsightsState)

# === 普通边 (无条件) ===
builder.add_edge("initialize_session", "run_exploration")
builder.add_edge("run_exploration", "human_review_exploration")
builder.add_edge("run_planning", "human_review_planning")
builder.add_edge("run_development", "run_review")
builder.add_edge("run_testing", "human_review_testing")
builder.add_edge("finalize", END)

# === 人工审核恢复边 (条件) ===

# exploration 审核后
builder.add_conditional_edges(
    "human_review_exploration",
    lambda state: state["human_decisions"][-1]["decision"],
    {
        "APPROVE": "run_planning",
        "REJECT": "finalize",
        "REQUEST_CHANGES": "run_exploration",
        "ADD_NOTES": "run_planning",
    }
)

# planning 审核后
builder.add_conditional_edges(
    "human_review_planning",
    lambda state: state["human_decisions"][-1]["decision"],
    {
        "APPROVE": "run_development",
        "REJECT": "finalize",
        "REQUEST_CHANGES": "run_planning",
        "ADD_NOTES": "run_development",
    }
)

# code 审核后 (从子图或人工审核节点退出)
builder.add_conditional_edges(
    "human_review_code",
    lambda state: state["human_decisions"][-1]["decision"],
    {
        "APPROVE": "run_testing",
        "REJECT": "finalize",
        "REQUEST_CHANGES": "run_development",
        "ADD_NOTES": "run_testing",
    }
)

# testing 审核后
builder.add_conditional_edges(
    "human_review_testing",
    lambda state: state["human_decisions"][-1]["decision"],
    {
        "APPROVE": "finalize",
        "REJECT": "finalize",
        "REQUEST_CHANGES": "run_development",
        "ADD_NOTES": "finalize",
    }
)

# === 审核路由条件边 (开发-审核子图内部) ===
builder.add_conditional_edges(
    "route_review",
    route_review,  # 调用节点函数
    {
        "PASS": "human_review_code",
        "REJECT": "human_review_code",
        "NEEDS_REVISION": "run_development",
        "MAX_ITERATIONS": "human_review_code",
    }
)
```

### 2.2 条件表达式详细说明

| 边源节点 | 条件表达式 | 目标节点 |
|----------|-----------|----------|
| `human_review_exploration` | `state["human_decisions"][-1]["decision"] == "APPROVE"` | `run_planning` |
| `human_review_exploration` | `state["human_decisions"][-1]["decision"] == "REJECT"` | `finalize` |
| `human_review_exploration` | `state["human_decisions"][-1]["decision"] == "REQUEST_CHANGES"` | `run_exploration` |
| `route_review` | `state["review_result"]["overall_verdict"] == "PASS"` | `human_review_code` |
| `route_review` | `state["review_result"]["overall_verdict"] == "REJECT"` | `human_review_code` |
| `route_review` | `state["review_result"]["overall_verdict"] == "NEEDS_REVISION" and state["dev_review_iteration_count"] < state["max_dev_review_iterations"]` | `run_development` |
| `route_review` | `state["review_result"]["overall_verdict"] == "NEEDS_REVISION" and state["dev_review_iteration_count"] >= state["max_dev_review_iterations"]` | `human_review_code` |

---

## 3. 错误处理与重试策略

### 3.1 错误分类矩阵

| 错误类型 | 示例 | 可重试 | 节点级处理 | 全局处理 |
|----------|------|--------|------------|----------|
| LLM API 限流 | `429 Too Many Requests` | 是 | 指数退避重试 | 记录告警 |
| LLM API 超时 | `504 Gateway Timeout` | 是 | 指数退避重试 | 记录告警 |
| 网络超时 | GitHub API 连接超时 | 是 | 指数退避重试 | 记录告警 |
| 代码编译失败 | `make ARCH=riscv` 报错 | **否** | 开发Agent自修复3次 | 转人工审核 |
| 沙箱崩溃 | Firecracker MicroVM panic | **否** | 清理并快速失败 | 通知运维 |
| 静态分析错误 | `sparse` 报告严重问题 | **否** | 记录到结果 | 转审核Agent |
| RAG 查询失败 | 向量数据库连接断开 | 是 | 指数退避重试 | 降级到直连 |
| Git 操作失败 | 分支冲突、权限不足 | **否** | 记录错误详情 | 转人工 |
| QEMU 启动失败 | 镜像损坏、资源不足 | 是 (备用镜像) | 尝试备用方案 | 通知运维 |

### 3.2 指数退避重试实现

```python
import time
import random
from functools import wraps

def exponential_backoff_retry(base: int = 2, max_retries: int = 3, max_delay: float = 60.0):
    """
    节点级指数退避重试装饰器。
    仅对 RetryableError 子类触发重试。
    """
    def decorator(func):
        @wraps(func)
        def wrapper(state: RVInsightsState, *args, **kwargs):
            retry_count = state.get("retry_count", 0)
            last_error = None

            for attempt in range(retry_count, max_retries + 1):
                try:
                    return func(state, *args, **kwargs)
                except RetryableError as e:
                    last_error = e
                    if attempt >= max_retries:
                        break

                    delay = min(base ** attempt + random.uniform(0, 1), max_delay)
                    time.sleep(delay)

                    # 更新状态中的重试计数
                    state["retry_count"] = attempt + 1
                except NonRetryableError as e:
                    # 不可重试错误立即抛出
                    raise

            # 达到最大重试次数，进入死信队列
            _send_to_dlq(state, last_error)
            raise MaxRetriesExceededError(
                f"Node {func.__name__} failed after {max_retries} retries: {last_error}"
            )
        return wrapper
    return decorator

# 应用装饰器到各节点
@exponential_backoff_retry(base=2, max_retries=3, max_delay=60.0)
def run_exploration(state: RVInsightsState) -> Dict[str, Any]:
    ...

@exponential_backoff_retry(base=2, max_retries=3, max_delay=60.0)
def run_planning(state: RVInsightsState) -> Dict[str, Any]:
    ...
```

### 3.3 死信队列 (DLQ) 实现

```python
from datetime import datetime, timezone

def _send_to_dlq(state: RVInsightsState, error: Exception) -> None:
    """
    将达到最大重试次数的任务发送到死信队列。
    通知运维团队进行人工干预。
    """
    dlq_record = {
        "session_id": state["session_id"],
        "tenant_id": state["tenant_id"],
        "current_stage": state["current_stage"],
        "failed_node": state.get("current_stage"),  # 当前执行的节点
        "error_type": type(error).__name__,
        "error_message": str(error),
        "stack_trace": getattr(error, "__traceback__", None),
        "state_snapshot": {k: v for k, v in state.items() if k != "agent_logs"},  # 省略大字段
        "enqueued_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending_review",
    }

    # 写入 DLQ 表 (PostgreSQL)
    db.execute("""
        INSERT INTO dead_letter_queue (
            session_id, tenant_id, current_stage, failed_node,
            error_type, error_message, stack_trace, state_snapshot,
            enqueued_at, status
        ) VALUES (
            %(session_id)s, %(tenant_id)s, %(current_stage)s, %(failed_node)s,
            %(error_type)s, %(error_message)s, %(stack_trace)s, %(state_snapshot)s,
            %(enqueued_at)s, %(status)s
        )
    """, dlq_record)

    # 发送运维告警 (PagerDuty / Slack / 邮件)
    alert_ops_team(
        title=f"[RV-Insights] DLQ Alert: Session {state['session_id']} failed at {state['current_stage']}",
        severity="high",
        context=dlq_record,
    )

    # 更新会话状态为 failed
    db.execute(
        "UPDATE sessions SET status = 'failed', failed_at = NOW() WHERE session_id = %s",
        (state["session_id"],)
    )
```

### 3.4 部分失败处理 (探索Agent)

```python
def run_exploration(state: RVInsightsState) -> Dict[str, Any]:
    tenant_config = load_tenant_config(state["tenant_id"])
    partial_policy = tenant_config.get("exploration_partial_failure_policy", "continue")

    # AutoGen 群聊执行
    result = explorer.run()

    failed_agents = result.get("failed_subagents", [])
    if failed_agents:
        if partial_policy == "fail":
            raise ExplorationError(
                f"Subagents failed: {failed_agents}. Policy is 'fail'."
            )
        elif partial_policy == "continue":
            # 记录警告，继续流程
            result["partial_failures"] = failed_agents
            result["warning"] = f"Some subagents failed but continuing per policy: {failed_agents}"

    return {"exploration_result": result, ...}
```

---

## 4. 并发控制

### 4.1 同仓库互斥锁 (Git Write Lock)

```python
import redis
from datetime import datetime, timezone
from contextlib import contextmanager

redis_client = redis.Redis.from_url(os.environ["REDIS_URL"])

@contextmanager
def git_write_lock(repo_url: str, session_id: str, timeout: int = 300):
    """
    基于 Redis 的分布式互斥锁。
    同一 Git 仓库在同一时间只能有一个开发Agent执行写操作。
    """
    lock_key = f"rvi:git_lock:{repo_url}"
    lock_value = session_id
    acquire_timeout = timeout
    lock_ttl = 14400  # 4小时，与开发节点超时一致

    # 尝试获取锁
    acquired = redis_client.set(lock_key, lock_value, nx=True, ex=lock_ttl)
    if not acquired:
        # 检查锁持有者是否已死亡 (孤儿锁检测)
        holder = redis_client.get(lock_key)
        if holder and not is_session_alive(holder.decode()):
            redis_client.delete(lock_key)
            acquired = redis_client.set(lock_key, lock_value, nx=True, ex=lock_ttl)

    if not acquired:
        raise GitLockTimeoutError(f"Could not acquire git lock for {repo_url} within {timeout}s")

    # 持久化锁信息到 DB
    db.execute("""
        INSERT INTO git_locks (repo_url, session_id, acquired_at, expires_at)
        VALUES (%s, %s, NOW(), NOW() + INTERVAL '4 hours')
        ON CONFLICT (repo_url) DO UPDATE SET
            session_id = EXCLUDED.session_id,
            acquired_at = EXCLUDED.acquired_at,
            expires_at = EXCLUDED.expires_at
    """, (repo_url, session_id))

    try:
        yield {"lock_id": lock_key, "repo_url": repo_url, "session_id": session_id}
    finally:
        # 仅当持有者仍是当前会话时才释放
        current_holder = redis_client.get(lock_key)
        if current_holder and current_holder.decode() == session_id:
            redis_client.delete(lock_key)
            db.execute(
                "DELETE FROM git_locks WHERE repo_url = %s AND session_id = %s",
                (repo_url, session_id)
            )

def acquire_git_lock(repo_url: str, session_id: str, timeout: int = 300) -> Dict[str, Any]:
    with git_write_lock(repo_url, session_id, timeout) as lock:
        return lock

def release_git_lock(lock_id: str) -> None:
    # 由上下文管理器自动处理
    pass
```

### 4.2 资源配额管理

```python
class ResourceQuotaManager:
    """
    管理租户级并发会话数限制和全局 QEMU 虚拟机池。
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def check_tenant_concurrency(self, tenant_id: str, max_sessions: int = 5) -> bool:
        """检查租户是否还有并发会话额度。"""
        key = f"rvi:tenant_sessions:{tenant_id}"
        current = self.redis.scard(key)
        return current < max_sessions

    def register_session(self, tenant_id: str, session_id: str) -> None:
        key = f"rvi:tenant_sessions:{tenant_id}"
        self.redis.sadd(key, session_id)
        # 设置过期时间，防止孤儿记录
        self.redis.expire(key, 86400 * 2)

    def unregister_session(self, tenant_id: str, session_id: str) -> None:
        key = f"rvi:tenant_sessions:{tenant_id}"
        self.redis.srem(key, session_id)

    # === QEMU 虚拟机池 ===
    def acquire_qemu_instance(self, config: Dict[str, Any], session_id: str, timeout: int = 600) -> Dict[str, Any]:
        """
        从 QEMU 实例池中获取可用实例。
        使用 Redis 列表作为简单池，配合工作窃取。
        """
        pool_key = f"rvi:qemu_pool:{config['arch']}:{config['variant']}"
        lock_key = f"rvi:qemu_lock:{config['arch']}:{config['variant']}"
        instance_lock_ttl = 10800  # 3小时，与测试节点超时一致

        start_time = time.time()
        while time.time() - start_time < timeout:
            # 尝试从池中获取实例
            instance_data = self.redis.lpop(pool_key)
            if instance_data:
                instance = json.loads(instance_data)
                # 标记为已占用
                self.redis.setex(
                    f"rvi:qemu_occupied:{instance['instance_id']}",
                    instance_lock_ttl,
                    session_id
                )
                return instance

            # 池为空，尝试工作窃取：检查是否有被占用但会话已死亡的实例
            stolen = self._steal_orphan_qemu(config, session_id)
            if stolen:
                return stolen

            time.sleep(5)

        raise QuotaExceededError(f"No QEMU instance available for {config} within {timeout}s")

    def _steal_orphan_qemu(self, config: Dict[str, Any], new_session_id: str) -> Optional[Dict[str, Any]]:
        """工作窃取：回收孤儿会话占用的 QEMU 实例。"""
        occupied_pattern = f"rvi:qemu_occupied:*"
        for key in self.redis.scan_iter(match=occupied_pattern):
            holder_session = self.redis.get(key)
            if holder_session and not is_session_alive(holder_session.decode()):
                instance_id = key.decode().split(":")[-1]
                # 强制回收
                self.redis.delete(key)
                return {"instance_id": instance_id, "stolen": True, "new_session_id": new_session_id}
        return None

    def release_qemu_instance(self, instance_id: str, delay_minutes: int = 30) -> None:
        """
        释放 QEMU 实例回池。
        delay_minutes: 延迟释放，供人类调试查看。
        """
        if delay_minutes > 0:
            threading.Timer(delay_minutes * 60, self._do_release, args=[instance_id]).start()
        else:
            self._do_release(instance_id)

    def _do_release(self, instance_id: str) -> None:
        self.redis.delete(f"rvi:qemu_occupied:{instance_id}")
        # 实例重置逻辑 (通过 MCP-Server 调用)
        reset_qemu_instance(instance_id)
        # 回池
        self.redis.rpush(f"rvi:qemu_pool:rv64gc:default", json.dumps({"instance_id": instance_id}))
```

### 4.3 Agent Worker Pool 与工作窃取

```python
from multiprocessing import Pool
from queue import PriorityQueue
import threading

class AgentWorkerPool:
    """
    Agent 执行 Worker Pool，支持工作窃取队列。
    """

    def __init__(self, num_workers: int = 8):
        self.num_workers = num_workers
        self.global_queue = PriorityQueue()  # (priority, task)
        self.worker_queues = [PriorityQueue() for _ in range(num_workers)]
        self.workers = []
        self.shutdown_event = threading.Event()

    def submit(self, task: Dict[str, Any], priority: int = 5) -> None:
        """提交任务到全局队列。"""
        self.global_queue.put((priority, task))

    def start(self) -> None:
        for i in range(self.num_workers):
            t = threading.Thread(target=self._worker_loop, args=(i,))
            t.daemon = True
            t.start()
            self.workers.append(t)

    def _worker_loop(self, worker_id: int) -> None:
        local_queue = self.worker_queues[worker_id]

        while not self.shutdown_event.is_set():
            task = None

            # 1. 优先处理本地队列
            if not local_queue.empty():
                _, task = local_queue.get()
            # 2. 从全局队列获取
            elif not self.global_queue.empty():
                _, task = self.global_queue.get()
            # 3. 工作窃取：从其他 worker 的队列窃取
            else:
                task = self._steal_task(worker_id)

            if task:
                self._execute_task(task)
            else:
                time.sleep(0.1)

    def _steal_task(self, thief_id: int) -> Optional[Dict[str, Any]]:
        """从随机其他 worker 队列的尾部窃取任务。"""
        for i in range(self.num_workers):
            if i == thief_id:
                continue
            victim_queue = self.worker_queues[i]
            if not victim_queue.empty():
                # 注意：PriorityQueue 不支持直接从尾部窃取，此处使用简化逻辑
                # 生产环境可改用 deque 实现双端队列
                try:
                    _, task = victim_queue.get(block=False)
                    return task
                except:
                    continue
        return None

    def _execute_task(self, task: Dict[str, Any]) -> None:
        session_id = task["session_id"]
        node_name = task["node_name"]
        try:
            # 调用 LangGraph 节点函数
            result = task["node_func"](task["state"])
            # 将结果写回 checkpoint
            save_checkpoint(session_id, result)
        except Exception as e:
            logger.error(f"Task failed: session={session_id}, node={node_name}, error={e}")
            # 触发重试或 DLQ 逻辑
            handle_task_failure(task, e)
```

---

## 5. 会话生命周期管理

### 5.1 超时策略

```python
from datetime import datetime, timezone, timedelta

class SessionTimeoutManager:
    """
    管理整体会话超时和单阶段超时。
    """

    # 整体会话超时: 24小时
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
    }

    def check_timeouts(self, state: RVInsightsState) -> Optional[str]:
        """
        检查是否超时。返回超时类型或 None。
        """
        now = datetime.now(timezone.utc)
        created_at = datetime.fromisoformat(state["created_at"])

        # 整体超时检查
        if now - created_at > self.GLOBAL_SESSION_TIMEOUT:
            return "GLOBAL_TIMEOUT"

        # 单阶段超时检查
        current_stage = state["current_stage"]
        stage_timeout = self.STAGE_TIMEOUTS.get(current_stage)

        if stage_timeout and state["status"] == "running":
            # 获取当前阶段的进入时间
            stage_entries = [t for t in state.get("timestamps", []) if t["stage"] == current_stage]
            if stage_entries:
                last_entry = datetime.fromisoformat(stage_entries[-1]["entered_at"])
                if now - last_entry > stage_timeout:
                    return f"STAGE_TIMEOUT:{current_stage}"

        return None

    def enforce_timeout(self, state: RVInsightsState) -> Dict[str, Any]:
        """强制执行超时，返回状态更新。"""
        timeout_type = self.check_timeouts(state)
        if not timeout_type:
            return {}

        logger.warning(f"Session {state['session_id']} timed out: {timeout_type}")

        return {
            "status": "failed",
            "last_error": {
                "type": "TIMEOUT",
                "subtype": timeout_type,
                "message": f"Session or stage timed out: {timeout_type}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        }
```

### 5.2 优雅终止 (取消)

```python
import signal
import os

class GracefulTerminationManager:
    """
    处理人类点击"取消"时的优雅终止。
    """

    def __init__(self):
        self.cancelled_sessions = set()
        self.agent_processes = {}  # session_id -> process

    def request_cancellation(self, session_id: str) -> None:
        """
        人类点击"取消"时调用。
        1. 标记会话为取消中
        2. 向 Agent 进程发送信号
        3. 等待清理完成
        """
        self.cancelled_sessions.add(session_id)

        # 更新 DB
        db.execute(
            "UPDATE sessions SET status = 'cancelling', cancel_requested_at = NOW() WHERE session_id = %s",
            (session_id,)
        )

        # 发送信号给 Agent 进程 (如果正在运行)
        proc = self.agent_processes.get(session_id)
        if proc and proc.poll() is None:
            # 先发送 SIGTERM，允许清理
            proc.send_signal(signal.SIGTERM)
            # 5秒后若仍未退出，发送 SIGKILL
            threading.Timer(5.0, self._force_kill, args=[session_id]).start()

    def _force_kill(self, session_id: str) -> None:
        proc = self.agent_processes.get(session_id)
        if proc and proc.poll() is None:
            logger.warning(f"Force killing agent process for session {session_id}")
            proc.kill()

    def cleanup_resources(self, session_id: str) -> None:
        """
        清理沙箱资源、释放锁、归档部分产物。
        """
        state = load_state(session_id)

        # 释放 Git 锁
        if state.get("git_lock_id"):
            release_git_lock(state["git_lock_id"])

        # 释放 QEMU 实例
        if state.get("qemu_instance_id"):
            release_qemu_instance(state["qemu_instance_id"], delay_minutes=0)

        # 清理沙箱
        if state.get("workspace_path"):
            sandbox = os.path.join(state["workspace_path"], "sandbox")
            if os.path.exists(sandbox):
                shutil.rmtree(sandbox, ignore_errors=True)

        # 归档部分产物 (即使取消也保留已产生的报告)
        upload_partial_artifacts(state)

        # 最终状态更新
        db.execute(
            "UPDATE sessions SET status = 'cancelled', cancelled_at = NOW() WHERE session_id = %s",
            (session_id,)
        )

        self.cancelled_sessions.discard(session_id)
```

### 5.3 孤儿会话检测与自动恢复

```python
import psutil

class OrphanSessionDetector:
    """
    定期检测 Agent 进程崩溃但会话状态未更新的情况。
    """

    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval

    def start(self) -> None:
        threading.Thread(target=self._detection_loop, daemon=True).start()

    def _detection_loop(self) -> None:
        while True:
            self._check_orphan_sessions()
            time.sleep(self.check_interval)

    def _check_orphan_sessions(self) -> None:
        """
        检测逻辑:
        1. 查询所有 status == 'running' 且 updated_at > 5分钟前 的会话
        2. 检查关联的 Agent 进程是否仍然存在
        3. 若进程不存在，标记为失败并从上一个 checkpoint 恢复
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)

        running_sessions = db.query("""
            SELECT session_id, current_stage, updated_at, process_pid
            FROM sessions
            WHERE status = 'running' AND updated_at < %s
        """, (cutoff,))

        for session in running_sessions:
            pid = session.get("process_pid")
            if pid and not self._is_process_alive(pid):
                logger.error(f"Orphan session detected: {session['session_id']}, stage={session['current_stage']}")
                self._recover_orphan_session(session)

    def _is_process_alive(self, pid: int) -> bool:
        try:
            proc = psutil.Process(pid)
            return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
        except psutil.NoSuchProcess:
            return False

    def _recover_orphan_session(self, session: Dict[str, Any]) -> None:
        """
        自动恢复策略:
        1. 释放该会话持有的所有锁 (Git, QEMU)
        2. 从上一个 LangGraph checkpoint 恢复状态
        3. 若中断于人工审核节点，恢复为 'interrupted' 状态
        4. 若中断于 Agent 执行中，重放该节点 (设置 retry_count)
        """
        session_id = session["session_id"]

        # 强制释放锁
        db.execute("DELETE FROM git_locks WHERE session_id = %s", (session_id,))
        db.execute("DELETE FROM qemu_occupancy WHERE session_id = %s", (session_id,))

        # 从 checkpoint 恢复
        checkpoint = load_latest_checkpoint(session_id)
        if not checkpoint:
            # 无 checkpoint，标记为失败
            db.execute(
                "UPDATE sessions SET status = 'failed', failure_reason = 'orphan_no_checkpoint' WHERE session_id = %s",
                (session_id,)
            )
            return

        recovered_state = checkpoint["state"]
        interrupted_stage = recovered_state["current_stage"]

        if "HUMAN_REVIEW" in interrupted_stage:
            # 恢复为中断状态，等待人类继续
            db.execute(
                "UPDATE sessions SET status = 'interrupted', current_stage = %s WHERE session_id = %s",
                (interrupted_stage, session_id)
            )
            # 通知 UI 重新连接
            notify_ui_reconnect(session_id, interrupted_stage)
        else:
            # 重放 Agent 节点
            db.execute(
                """UPDATE sessions
                   SET status = 'running',
                       current_stage = %s,
                       retry_count = COALESCE(retry_count, 0) + 1,
                       recovery_from_checkpoint = %s
                   WHERE session_id = %s""",
                (interrupted_stage, checkpoint["checkpoint_id"], session_id)
            )
            # 将任务重新提交到 Worker Pool
            submit_node_retry(session_id, interrupted_stage)
```

---

## 6. 子图接口契约

### 6.1 开发-审核迭代子图定义

```python
from langgraph.graph import StateGraph

# 子图状态继承全局状态，但增加局部字段
class DevReviewSubState(RVInsightsState):
    """
    开发-审核子图状态。
    继承父图所有字段，增加子图局部字段。
    """
    # 子图局部迭代计数 (与父图 dev_review_iteration_count 同步)
    local_iteration_count: int

    # 增量审核上下文
    previous_patches: List[str]  # 历史 patch 列表
    review_history: List[Dict[str, Any]]  # 历史审核报告

    # 开发Agent内部状态
    build_attempts: int
    last_build_log: Optional[str]

# 子图节点
def subgraph_run_development(state: DevReviewSubState) -> Dict[str, Any]:
    """子图内开发节点，与父图 run_development 逻辑一致。"""
    ...

def subgraph_run_review(state: DevReviewSubState) -> Dict[str, Any]:
    """子图内审核节点，与父图 run_review 逻辑一致。"""
    ...

def subgraph_route_review(state: DevReviewSubState) -> Literal["PASS", "NEEDS_REVISION", "REJECT", "MAX_ITERATIONS"]:
    """子图内路由节点，与父图 route_review 逻辑一致。"""
    ...

def build_dev_review_subgraph() -> StateGraph:
    """构建开发-审核迭代子图。"""
    subgraph = StateGraph(DevReviewSubState)

    subgraph.add_node("subgraph_development", subgraph_run_development)
    subgraph.add_node("subgraph_review", subgraph_run_review)
    subgraph.add_node("subgraph_route", subgraph_route_review)

    subgraph.add_edge("subgraph_development", "subgraph_review")
    subgraph.add_edge("subgraph_review", "subgraph_route")

    subgraph.add_conditional_edges(
        "subgraph_route",
        subgraph_route_review,
        {
            "PASS": END,
            "REJECT": END,
            "NEEDS_REVISION": "subgraph_development",
            "MAX_ITERATIONS": END,
        }
    )

    subgraph.set_entry_point("subgraph_development")
    return subgraph.compile()
```

### 6.2 子图状态访问规则

| 访问类型 | 规则 | 说明 |
|----------|------|------|
| 父图 -> 子图 | 只读 + 初始写入 | 父图在调用子图前，将 `development_plan`, `workspace_path` 等写入状态，子图读取 |
| 子图 -> 父图 | 写回指定字段 | 子图退出时，将 `development_result`, `review_result`, `dev_review_iteration_count` 写回父图状态 |
| 子图内部 | 读写自由 | 子图内部节点可自由读写 `DevReviewSubState` 的所有字段 |

```python
# 父图中调用子图
def run_dev_review_subgraph(state: RVInsightsState) -> Dict[str, Any]:
    """
    父图节点：调用开发-审核子图。
    """
    # 构建子图初始状态 (继承 + 局部字段)
    sub_state = DevReviewSubState(
        **state,
        local_iteration_count=state["dev_review_iteration_count"],
        previous_patches=[],
        review_history=[],
        build_attempts=0,
        last_build_log=None,
    )

    # 执行子图
    subgraph = build_dev_review_subgraph()
    final_sub_state = subgraph.invoke(sub_state)

    # 将子图结果映射回父图状态
    return {
        "development_result": final_sub_state["development_result"],
        "review_result": final_sub_state["review_result"],
        "dev_review_iteration_count": final_sub_state["local_iteration_count"],
        "agent_logs": state["agent_logs"] + final_sub_state.get("subgraph_agent_logs", []),
    }
```

### 6.3 子图 Checkpoint 策略

```python
from langgraph.checkpoint.postgres import PostgresSaver

# 父图 Checkpointer
parent_checkpointer = PostgresSaver(
    conn_string=os.environ["POSTGRES_URL"],
    checkpoint_table="checkpoints",
)

# 子图 Checkpointer (独立表，但同一数据库)
# 策略: 独立 checkpoint，但继承父图的 thread_id 作为命名空间前缀
subgraph_checkpointer = PostgresSaver(
    conn_string=os.environ["POSTGRES_URL"],
    checkpoint_table="subgraph_checkpoints",  # 独立表
)

# 子图 checkpoint 命名空间规则:
# thread_id = f"{parent_session_id}/dev_review"
# checkpoint_ns = f"iter_{iteration_count}"
#
# 这样即使子图内部迭代多次，每个迭代的 checkpoint 都独立保存，
# 同时与父图 session 关联，便于审计和调试。

def save_subgraph_checkpoint(session_id: str, iteration: int, state: DevReviewSubState) -> None:
    """保存子图 checkpoint。"""
    subgraph_checkpointer.put(
        thread_id=f"{session_id}/dev_review",
        checkpoint_ns=f"iter_{iteration}",
        checkpoint={
            "state": state,
            "parent_session_id": session_id,
            "iteration": iteration,
        }
    )

def load_subgraph_checkpoint(session_id: str, iteration: int) -> Optional[Dict[str, Any]]:
    """加载子图 checkpoint，用于迭代回滚或调试。"""
    return subgraph_checkpointer.get(
        thread_id=f"{session_id}/dev_review",
        checkpoint_ns=f"iter_{iteration}",
    )
```

---

## 7. 完整伪代码实现

### 7.1 全局图构建

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from typing import Dict, Any, Literal
import os

# === 状态定义 ===
class RVInsightsState(TypedDict):
    session_id: str
    tenant_id: str
    created_at: str
    updated_at: str
    current_stage: Literal[
        "INITIALIZATION", "EXPLORATION", "HUMAN_REVIEW_EXPLORATION",
        "PLANNING", "HUMAN_REVIEW_PLANNING",
        "DEVELOPMENT", "REVIEW", "HUMAN_REVIEW_CODE",
        "TESTING", "HUMAN_REVIEW_TESTING", "COMPLETION", "FAILED"
    ]
    status: Literal["running", "interrupted", "completed", "failed", "cancelled"]
    exploration_result: Optional[Dict[str, Any]]
    planning_result: Optional[Dict[str, Any]]
    development_result: Optional[Dict[str, Any]]
    review_result: Optional[Dict[str, Any]]
    testing_result: Optional[Dict[str, Any]]
    dev_review_iteration_count: int
    max_dev_review_iterations: int
    human_decisions: List[Dict[str, Any]]
    human_notes: List[str]
    agent_logs: List[Dict[str, Any]]
    timestamps: List[Dict[str, Any]]
    last_error: Optional[Dict[str, Any]]
    retry_count: int
    workspace_path: Optional[str]
    git_lock_id: Optional[str]
    qemu_instance_id: Optional[str]

# === 节点函数 (详见第1节) ===
def initialize_session(state: RVInsightsState) -> Dict[str, Any]: ...
def run_exploration(state: RVInsightsState) -> Dict[str, Any]: ...
def human_review_exploration(state: RVInsightsState) -> Dict[str, Any]: ...
def run_planning(state: RVInsightsState) -> Dict[str, Any]: ...
def human_review_planning(state: RVInsightsState) -> Dict[str, Any]: ...
def run_development(state: RVInsightsState) -> Dict[str, Any]: ...
def run_review(state: RVInsightsState) -> Dict[str, Any]: ...
def route_review(state: RVInsightsState) -> Literal["PASS", "NEEDS_REVISION", "REJECT", "MAX_ITERATIONS"]: ...
def human_review_code(state: RVInsightsState) -> Dict[str, Any]: ...
def run_testing(state: RVInsightsState) -> Dict[str, Any]: ...
def human_review_testing(state: RVInsightsState) -> Dict[str, Any]: ...
def finalize(state: RVInsightsState) -> Dict[str, Any]: ...

# === 构建全局 StateGraph ===
builder = StateGraph(RVInsightsState)

# 注册节点
builder.add_node("initialize_session", initialize_session)
builder.add_node("run_exploration", run_exploration)
builder.add_node("human_review_exploration", human_review_exploration)
builder.add_node("run_planning", run_planning)
builder.add_node("human_review_planning", human_review_planning)
builder.add_node("run_development", run_development)
builder.add_node("run_review", run_review)
builder.add_node("route_review", route_review)
builder.add_node("human_review_code", human_review_code)
builder.add_node("run_testing", run_testing)
builder.add_node("human_review_testing", human_review_testing)
builder.add_node("finalize", finalize)

# === 边连接 ===

# 初始化 -> 探索
builder.add_edge("initialize_session", "run_exploration")

# 探索 -> 人工审核
builder.add_edge("run_exploration", "human_review_exploration")

# 探索审核后分支
builder.add_conditional_edges(
    "human_review_exploration",
    lambda state: state["human_decisions"][-1]["decision"],
    {
        "APPROVE": "run_planning",
        "REJECT": "finalize",
        "REQUEST_CHANGES": "run_exploration",
        "ADD_NOTES": "run_planning",
    }
)

# 规划 -> 人工审核
builder.add_edge("run_planning", "human_review_planning")

# 规划审核后分支
builder.add_conditional_edges(
    "human_review_planning",
    lambda state: state["human_decisions"][-1]["decision"],
    {
        "APPROVE": "run_development",
        "REJECT": "finalize",
        "REQUEST_CHANGES": "run_planning",
        "ADD_NOTES": "run_development",
    }
)

# 开发 -> 审核 (进入迭代循环)
builder.add_edge("run_development", "run_review")

# 审核 -> 路由
builder.add_edge("run_review", "route_review")

# 路由判断
builder.add_conditional_edges(
    "route_review",
    route_review,
    {
        "PASS": "human_review_code",
        "REJECT": "human_review_code",
        "NEEDS_REVISION": "run_development",
        "MAX_ITERATIONS": "human_review_code",
    }
)

# 代码人工审核后分支
builder.add_conditional_edges(
    "human_review_code",
    lambda state: state["human_decisions"][-1]["decision"],
    {
        "APPROVE": "run_testing",
        "REJECT": "finalize",
        "REQUEST_CHANGES": "run_development",
        "ADD_NOTES": "run_testing",
    }
)

# 测试 -> 人工审核
builder.add_edge("run_testing", "human_review_testing")

# 测试审核后分支
builder.add_conditional_edges(
    "human_review_testing",
    lambda state: state["human_decisions"][-1]["decision"],
    {
        "APPROVE": "finalize",
        "REJECT": "finalize",
        "REQUEST_CHANGES": "run_development",
        "ADD_NOTES": "finalize",
    }
)

# 归档 -> 结束
builder.add_edge("finalize", END)

# === 入口点 ===
builder.set_entry_point("initialize_session")

# === Checkpointer 配置 ===
checkpointer = PostgresSaver(
    conn_string=os.environ["POSTGRES_URL"],
    checkpoint_table="checkpoints",
)

# === 中断配置 ===
# human_review_* 节点自动作为 interrupt 点
# LangGraph 会在这些节点执行前保存 checkpoint，然后暂停等待 resume

# === 编译图 ===
graph = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=[
        "human_review_exploration",
        "human_review_planning",
        "human_review_code",
        "human_review_testing",
    ],
    # 可选: 在以下节点后也保存 checkpoint，便于故障恢复
    checkpoint_every_node=True,
)

# === 会话启动 ===
def start_session(session_id: str, tenant_id: str, initial_input: Dict[str, Any]) -> str:
    """
    启动新会话。
    """
    initial_state = RVInsightsState(
        session_id=session_id,
        tenant_id=tenant_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat(),
        current_stage="INITIALIZATION",
        status="running",
        exploration_result=None,
        planning_result=None,
        development_result=None,
        review_result=None,
        testing_result=None,
        dev_review_iteration_count=0,
        max_dev_review_iterations=5,
        human_decisions=[],
        human_notes=[],
        agent_logs=[],
        timestamps=[],
        last_error=None,
        retry_count=0,
        workspace_path=None,
        git_lock_id=None,
        qemu_instance_id=None,
        **initial_input,
    )

    # 启动图执行 (异步)
    # thread_id 与 session_id 1:1 映射，确保 Checkpointer 分区键与应用层会话标识一致
    thread_id = session_id
    graph.invoke(
        initial_state,
        config={"configurable": {"thread_id": thread_id}},
    )

    return thread_id

# === 人工审核恢复 ===
def submit_human_decision(
    session_id: str,
    decision: Literal["APPROVE", "REJECT", "REQUEST_CHANGES", "ADD_NOTES"],
    comment: Optional[str] = None,
    selected_opportunity_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    人类提交审核决策，恢复工作流。
    """
    # 加载当前状态
    current_state = graph.get_state(
        config={"configurable": {"thread_id": session_id}}
    )

    # 验证决策合法性
    if current_state.values["status"] != "interrupted":
        raise InvalidStateError(f"Session {session_id} is not in interrupted state")

    # 构建恢复命令
    human_decision = {
        "stage": current_state.values["current_stage"],
        "decision": decision,
        "decision_by": "human_user_id",  # 从认证上下文获取
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "comment": comment,
        "selected_opportunity_id": selected_opportunity_id,
    }

    # 更新状态
    updated_state = {
        **current_state.values,
        "human_decisions": current_state.values["human_decisions"] + [human_decision],
        "status": "running",
    }

    if comment:
        updated_state["human_notes"] = current_state.values.get("human_notes", []) + [comment]

    # 恢复图执行
    result = graph.invoke(
        updated_state,
        config={"configurable": {"thread_id": session_id}},
    )

    return result
```

### 7.2 运行时监控与干预

```python
class WorkflowRuntimeMonitor:
    """
    运行时监控：超时检查、取消处理、状态推送。
    """

    def __init__(self, graph, checkpointer):
        self.graph = graph
        self.checkpointer = checkpointer
        self.timeout_manager = SessionTimeoutManager()
        self.termination_manager = GracefulTerminationManager()
        self.orphan_detector = OrphanSessionDetector()

    def run(self) -> None:
        """启动后台监控线程。"""
        threading.Thread(target=self._timeout_check_loop, daemon=True).start()
        threading.Thread(target=self._cancellation_loop, daemon=True).start()
        self.orphan_detector.start()

    def _timeout_check_loop(self) -> None:
        while True:
            # 查询所有 running 状态的会话
            running_sessions = db.query("SELECT session_id, state FROM sessions WHERE status = 'running'")
            for session in running_sessions:
                state = session["state"]
                timeout_update = self.timeout_manager.enforce_timeout(state)
                if timeout_update:
                    # 强制终止并归档
                    self.termination_manager.cleanup_resources(session["session_id"])
                    # 写入最终状态
                    self.checkpointer.put(
                        thread_id=session["session_id"],
                        checkpoint={"state": {**state, **timeout_update}},
                    )
            time.sleep(60)

    def _cancellation_loop(self) -> None:
        """监听取消请求队列 (Redis 或 DB)。"""
        while True:
            cancel_request = cancel_queue.pop()
            if cancel_request:
                session_id = cancel_request["session_id"]
                self.termination_manager.request_cancellation(session_id)
                self.termination_manager.cleanup_resources(session_id)
            time.sleep(1)

    def push_state_update(self, session_id: str) -> None:
        """向 UI 推送状态更新 (SSE)。"""
        state = self.graph.get_state(
            config={"configurable": {"thread_id": session_id}}
        )
        sse_broadcast(session_id, {
            "current_stage": state.values["current_stage"],
            "status": state.values["status"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
```

---

## 8. 附录

### 8.1 错误类型层次

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

# 可重试
class RetryableExplorationError(RetryableError): pass
class RetryablePlanningError(RetryableError): pass
class RetryableDevelopmentError(RetryableError): pass
class RetryableReviewError(RetryableError): pass
class RetryableTestingError(RetryableError): pass

# 不可重试
class ExplorationError(NonRetryableError): pass
class PlanningError(NonRetryableError): pass
class DevelopmentError(NonRetryableError): pass
class ReviewError(NonRetryableError): pass
class TestingError(NonRetryableError): pass
class GitLockTimeoutError(NonRetryableError): pass
class QuotaExceededError(NonRetryableError): pass
class MaxRetriesExceededError(NonRetryableError): pass
class InvalidStateError(NonRetryableError): pass
```

### 8.2 环境变量清单

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `RVI_WORKSPACE_BASE` | 工作目录根路径 | `/var/rv-insights/workspaces` |
| `POSTGRES_URL` | PostgreSQL 连接字符串 | `postgresql://user:pass@localhost/rvi` |
| `REDIS_URL` | Redis 连接字符串 | `redis://localhost:6379/0` |
| `MCP_SERVER_URL` | MCP-Server RPC 地址 | `http://localhost:8080` |
| `LANGSMITH_API_KEY` | LangSmith 观测密钥 | `ls-...` |

### 8.3 数据库表清单

| 表名 | 用途 | 管理者 |
|------|------|--------|
| `checkpoints` | LangGraph 状态 checkpoint | LangGraph |
| `subgraph_checkpoints` | 子图独立 checkpoint | 应用层 |
| `sessions` | 会话元数据与状态 | 应用层 |
| `human_decisions` | 人工审核记录 | 应用层 |
| `git_locks` | Git 仓库写锁状态 | 应用层 |
| `qemu_occupancy` | QEMU 实例占用状态 | 应用层 |
| `dead_letter_queue` | 死信队列 | 应用层 |
| `agent_logs` | Agent 执行日志 | 应用层 |
