# RV-Insights 设计方案文档集一致性审查报告

**审查日期**: 2026-04-21
**审查范围**: 8个设计方案文档
**审查人**: Claude Code Reviewer

---

## 总体一致性评分: 72/100

评分依据:
- 术语一致性: 存在多处术语混用 (MCP-Server vs MCP Server, Checkpointer vs Checkpoint, 人工审核 vs 人类审核)
- 数据类型一致性: 主方案 TypeScript 接口与深化文档 SQL Schema 存在字段名不一致
- 数值一致性: MAX_ITERATIONS 默认值、开发超时时间、预算默认值等多处不一致
- 架构一致性: 安全深化文档引入的 Falco、Kyverno、Vault 等组件未在主方案架构图中体现
- 链路一致性: WebSocket/SSE 事件类型基本匹配，但存在细微差异
- 引用有效性: 主方案深化文档引用基本正确，但部分章节映射关系模糊

---

## CRITICAL 级别问题 (必须修复)

### [CRITICAL-1] MAX_ITERATIONS 默认值不一致
**文件与位置**:
- `rv-insights-design.md` 第 501 行: `max_dev_review_iterations: number;  // 默认 5`
- `rv-insights-design.md` 第 382 行: `或 iteration_count >= MAX_ITERATIONS（如5次）`
- `data-model-deep-dive.md` 第 206 行: `max_dev_review_iterations int NOT NULL DEFAULT 3`
- `workflow-deep-dive.md` 第 40 行: `max_dev_review_iterations: int   # 默认 5`
- `workflow-deep-dive.md` 第 799 行: `max_dev_review_iterations=5`

**问题**: 主方案和数据模型深化文档对最大迭代次数的默认值定义冲突。主方案明确默认 5 次，但数据模型 DDL 中默认值为 3。这会导致新创建会话的迭代上限在不同模块间不一致，可能使工作流在达到 5 次迭代前被数据库默认值限制为 3 次。

**修复建议**: 统一默认值为 5 次（与主方案一致），修改 `data-model-deep-dive.md` 中 `workflow_states` 表的 `max_dev_review_iterations` 默认值为 5，并确保所有文档中该数值一致。

```sql
-- 修复前
max_dev_review_iterations int NOT NULL DEFAULT 3,

-- 修复后
max_dev_review_iterations int NOT NULL DEFAULT 5,
```

---

### [CRITICAL-2] 开发阶段超时时间不一致
**文件与位置**:
- `rv-insights-design.md` 第 7.1 节（安全设计）: 未明确提及超时
- `architecture-deep-dive.md` 第 2.1 节 SLO 表: 开发-审核单次迭代 P90 < 15min
- `workflow-deep-dive.md` 第 69 行: `run_development` 节点超时 `4h (14400s)`
- `workflow-deep-dive.md` 第 71 行: `run_review` 节点超时 `30min (1800s)`

**问题**: 虽然这两个超时属于不同节点，但主方案中未明确说明开发节点可长达 4 小时，而架构文档的 SLO 表暗示单次迭代应在 15 分钟内完成。4 小时与 15 分钟差距过大，且 `architecture-deep-dive.md` 的 SLO 未区分开发（代码生成+编译）和审核（代码审查）各自的独立超时。更重要的是，开发节点 4 小时超时与 Git 锁 TTL 4 小时（`workflow-deep-dive.md` 第 989 行）绑定，但未在架构文档中说明这种关联。

**修复建议**:
1. 在 `architecture-deep-dive.md` 的 SLO 表中明确区分 `run_development` 和 `run_review` 的独立目标值
2. 在主方案中增加对节点级超时配置的说明
3. 确保 Git 锁 TTL 与开发超时一致，并在文档中明确说明这种关联

---

### [CRITICAL-3] `human_decisions` vs `human_decision` 字段名单复数不一致
**文件与位置**:
- `rv-insights-design.md` 第 504 行: `human_decisions: HumanDecision[];`
- `rv-insights-design.md` 第 599 行: `更新 human_decisions`
- `data-model-deep-dive.md` 第 207 行: `human_decisions     jsonb DEFAULT '[]',`
- `data-model-deep-dive.md` 第 228 行: 表名 `human_decisions`
- `security-deep-dive.md` 第 1879 行: `"human_decisions.$[].decided_by": "[ANONYMIZED]"`
- `llm-engineering-deep-dive.md` 第 734 行: `"payload_type": "human_decision"` (单数)

**问题**: Agent 间通信协议（`llm-engineering-deep-dive.md`）中使用单数 `human_decision` 作为 payload_type，而状态定义和数据库 schema 中均使用复数 `human_decisions`。这会导致在解析消息和状态映射时出现字段名不匹配。

**修复建议**: 统一使用复数形式 `human_decisions`，修改 `llm-engineering-deep-dive.md` 中 AgentMessage Schema 的 payload_type 枚举值。

```json
// 修复前
"payload_type": { "enum": [..., "human_decision", ...] }

// 修复后
"payload_type": { "enum": [..., "human_decisions", ...] }
```

---

## HIGH 级别问题 (应该修复)

### [HIGH-1] `session_id` vs `thread_id` 混用
**文件与位置**:
- `rv-insights-design.md` 第 487 行: `session_id: string;`
- `rv-insights-design.md` 第 714 行: `thread_id TEXT NOT NULL,       -- 对应 session_id`
- `data-model-deep-dive.md` 第 115 行: `thread_id           text NOT NULL`
- `data-model-deep-dive.md` 第 123 行: `session_id          uuid NOT NULL REFERENCES sessions(id)`
- `workflow-deep-dive.md` 第 19 行: `session_id: str`
- `workflow-deep-dive.md` 第 1813 行: `thread_id = session_id`

**问题**: LangGraph Checkpointer 使用 `thread_id` 作为分区键，而应用层使用 `session_id`。虽然 `data-model-deep-dive.md` 和主方案都注明了 `thread_id` 对应 `session_id`，但在 `workflow-deep-dive.md` 的伪代码中，两者被直接等同使用（`thread_id = session_id`）。如果 `session_id` 是 UUID 格式而 `thread_id` 是字符串，可能存在类型不匹配风险。此外，`checkpoints` 表的主键包含 `thread_id` 但不包含 `session_id`，而 `workflow_states` 表使用 `session_id` 作为外键，这种不对称可能导致恢复时的关联查询问题。

**修复建议**:
1. 明确 `thread_id` 的数据类型为 UUID（与 `session_id` 一致），或明确允许字符串格式的 UUID
2. 在 `checkpoints` 表上为 `session_id` 创建唯一索引，确保一个 `session_id` 只对应一个 `thread_id`
3. 在文档中增加 `thread_id` 与 `session_id` 映射关系的明确说明

---

### [HIGH-2] `planning_result` 类型名不一致
**文件与位置**:
- `rv-insights-design.md` 第 494 行: `planning_result?: PlanningPlan;`
- `rv-insights-design.md` 第 248 行: `interface PlanningResult { ... }`
- `data-model-deep-dive.md` 第 201 行: `planning_result     jsonb`
- `workflow-deep-dive.md` 第 34 行: `planning_result: Optional[Dict[str, Any]]`

**问题**: 主方案中 `RVInsightsState` 接口的 `planning_result` 字段类型被标注为 `PlanningPlan`（第 494 行），但实际定义的接口名是 `PlanningResult`（第 248 行）。这是一个明显的笔误，会导致类型引用错误。

**修复建议**: 将 `rv-insights-design.md` 第 494 行的 `PlanningPlan` 修正为 `PlanningResult`。

```typescript
// 修复前
planning_result?: PlanningPlan;

// 修复后
planning_result?: PlanningResult;
```

---

### [HIGH-3] 安全组件在主方案架构图中缺失
**文件与位置**:
- `security-deep-dive.md`: 引入 Falco（第 1019 行）、Kyverno（第 1251 行）、HashiCorp Vault（第 2.1 节）、OPA/Istio AuthorizationPolicy（第 1.1 节）
- `rv-insights-design.md` 第 72-145 行: 总体架构图

**问题**: `security-deep-dive.md` 引入了多个关键安全组件（Falco 用于逃逸检测、Kyverno 用于镜像签名验证、Vault 用于密钥管理、OPA 用于细粒度授权），但这些组件在 `rv-insights-design.md` 的总体架构图中完全没有体现。这会导致读者无法从主方案中了解完整的安全架构。

**修复建议**: 在 `rv-insights-design.md` 的总体架构图中增加"安全与合规层"子图，至少包含：
- HashiCorp Vault（密钥管理）
- Falco（运行时安全监控）
- Kyverno/OPA（策略引擎）
- Istio/Linkerd（服务网格 mTLS）

或在架构图的"底层基础设施"层中增加这些安全组件的标注。

---

### [HIGH-4] WebSocket 事件类型不匹配
**文件与位置**:
- `architecture-deep-dive.md` 第 77-90 行: SSE 事件类型包含 `stage_started`, `agent_thinking`, `human_review_required`, `stage_completed`, `error_occurred`, `token_consumed`, `heartbeat`
- `ui-design-deep-dive.md` 第 452-461 行: WebSocket 事件类型包含 `stage_started`, `agent_thinking`, `human_review_required`, `stage_completed`, `error_occurred`, `heartbeat`, `ack`, `connection_established`, `state_sync`

**问题**:
1. `architecture-deep-dive.md` 包含 `token_consumed`，但 `ui-design-deep-dive.md` 中没有该事件类型
2. `ui-design-deep-dive.md` 包含 `ack`, `connection_established`, `state_sync`，但 `architecture-deep-dive.md` 中没有这些事件类型
3. 两个文档对实时通信的传输层描述不一致：`architecture-deep-dive.md` 主要描述 SSE，而 `ui-design-deep-dive.md` 以 WebSocket 为主、SSE 为降级

**修复建议**:
1. 统一事件类型列表，明确哪些是所有传输层共有的，哪些是特定于 WebSocket 的（如 `ack`, `connection_established`）
2. 决定 `token_consumed` 是否作为独立事件类型，还是作为 `agent_thinking` 或 `stage_completed` 的 payload 字段
3. 在 `architecture-deep-dive.md` 中补充 WebSocket 作为主通道的说明，与 `ui-design-deep-dive.md` 保持一致

---

### [HIGH-5] 预算默认值不一致
**文件与位置**:
- `rv-insights-design.md` 第 57 行: `max_budget_usd: number; default: 5.0`
- `architecture-deep-dive.md` 第 228-232 行: Quick $0.50 / Standard $5.00 / Deep $20.00
- `llm-engineering-deep-dive.md` 第 437-443 行: Quick $0.50 / Standard $5.00 / Deep $20.00

**问题**: 虽然架构文档和 LLM 工程文档的预算一致，但主方案中 `CreateSessionRequest` 的 `max_budget_usd` 默认值为 5.0，未明确说明这是 `Standard` 模式的默认值。此外，`architecture-deep-dive.md` 的 SLO 表中提到 `max_budget_usd`，但未与 `exploration_depth` 字段建立关联。

**修复建议**: 在 `rv-insights-design.md` 中明确说明 `max_budget_usd` 的默认值 5.0 对应 `exploration_depth: "standard"`，并建立两者的联动关系：

```yaml
exploration_depth:
  type: string
  enum: [quick, standard, deep]
  default: standard
max_budget_usd:
  type: number
  description: 会话Token预算上限（美元等值），与 exploration_depth 联动
  default: 5.0  # standard 模式默认值，quick 为 0.5，deep 为 20.0
```

---

### [HIGH-6] `decided_by` vs `decision_by` 字段名不一致
**文件与位置**:
- `rv-insights-design.md` 第 528 行: `decision_by: string;               // 用户ID`
- `data-model-deep-dive.md` 第 243 行: `decided_by      bigint NOT NULL REFERENCES users(id)`
- `security-deep-dive.md` 第 1879 行: `"human_decisions.$[].decided_by": "[ANONYMIZED]"`

**问题**: 主方案 TypeScript 接口中使用 `decision_by`，而数据库 Schema 和 GDPR 匿名化代码中使用 `decided_by`。这会导致 ORM/数据映射层出现字段名不匹配。

**修复建议**: 统一使用 `decided_by`（更符合英语语法，表示"被谁决定"），修改 `rv-insights-design.md` 中的 `HumanDecision` 接口。

```typescript
// 修复前
decision_by: string;

// 修复后
decided_by: string;
```

---

## MEDIUM 级别问题 (建议修复)

### [MEDIUM-1] 术语混用: "人工审核" vs "人类审核"
**文件与位置**:
- `rv-insights-design.md`: 混用"人工审核"（第 5 节标题、第 605 行等）和"人类审核"（第 46 行、第 582 行等）
- `ui-design-deep-dive.md`: 主要使用"人工审核"
- `data-model-deep-dive.md`: 使用"Human-in-the-Loop"（第 225 节标题）
- `workflow-deep-dive.md`: 使用"human_review"（节点名）

**问题**: 同一概念在中文语境下使用"人工审核"和"人类审核"两种说法，在英文/代码语境下使用 "human_review" 和 "Human-in-the-Loop"。这会给读者造成困惑，降低文档的专业性。

**修复建议**: 统一术语：
- 中文统一使用"人工审核"（更专业，强调"人工"而非"人类"）
- 英文/代码统一使用 `human_review`
- 在术语表（附录 A）中明确标注："人工审核 (Human Review / Human-in-the-Loop)"

---

### [MEDIUM-2] 术语混用: "MCP-Server" vs "MCP Server"
**文件与位置**:
- `rv-insights-design.md`: 使用 "MCP-Server"（第 59 行、第 106 行等）
- `architecture-deep-dive.md`: 使用 "MCP-Server"（第 169 行）和 "MCP Server"（第 423 行）
- `security-deep-dive.md`: 使用 "MCP-Server"（第 48 行）
- `workflow-deep-dive.md`: 使用 "MCP-Server"（第 367 行）和 "MCPClient"（第 394 行）

**问题**: "MCP-Server" 和 "MCP Server" 两种写法混用，且客户端类名 "MCPClient" 与服务端 "MCP-Server" 的命名风格不一致（一个有连字符，一个没有）。

**修复建议**: 统一使用 "MCP Server"（无连字符，符合通用命名习惯），类名统一为 `McpServer` 和 `McpClient`（驼峰命名）。

---

### [MEDIUM-3] 术语混用: "Checkpointer" vs "Checkpoint"
**文件与位置**:
- `rv-insights-design.md`: 使用 "Checkpointer"（第 71 行、第 711 行）和 "Checkpoint"（第 799 行术语表）
- `data-model-deep-dive.md`: 使用 "Checkpoint"（第 109 行）
- `workflow-deep-dive.md`: 使用 "checkpoint"（第 1762 行）

**问题**: "Checkpointer" 强调持久化机制/组件，"Checkpoint" 强调持久化数据本身。两者在文档中混用，容易混淆。

**修复建议**: 明确区分：
- "Checkpointer": 指 LangGraph 的持久化组件/机制
- "Checkpoint": 指具体的状态快照数据
在术语表中明确标注两者的区别。

---

### [MEDIUM-4] 探索超时时间不一致
**文件与位置**:
- `architecture-deep-dive.md` 第 217 行: 探索阶段延迟 P90 < 30min，告警阈值 > 45min
- `workflow-deep-dive.md` 第 65 行: `run_exploration` 节点超时 `2h (7200s)`

**问题**: SLO 目标值（30 分钟）与节点硬超时（2 小时）差距过大。虽然 2 小时是硬上限，但 SLO 表未明确说明这是 P90 目标而非绝对上限，可能导致运维误解。

**修复建议**: 在 `architecture-deep-dive.md` 的 SLO 表中增加一列"硬超时上限"，明确标注各阶段的绝对超时时间：

| 指标 | 目标值 | 硬超时 | 测量方式 | 告警阈值 |
|------|--------|--------|----------|----------|
| 探索阶段延迟 | P90 < 30min | 2h | 从触发到输出报告 | > 45min 触发告警 |

---

### [MEDIUM-5] 审核Agent通过标准不一致
**文件与位置**:
- `rv-insights-design.md` 第 380-382 行: `overall_verdict == "PASS"` 且不存在 `blocking == true` 的 Issue，或 `iteration_count >= MAX_ITERATIONS`
- `workflow-deep-dive.md` 第 526-536 行: `route_review` 函数中，`verdict == "PASS"` 直接返回 PASS，不检查 `blocking` 字段

**问题**: 主方案明确说明通过标准是 `overall_verdict == "PASS"` 且不存在 `blocking == true` 的 Issue，但 `workflow-deep-dive.md` 的 `route_review` 伪代码中只检查了 `overall_verdict`，未检查 `blocking` 字段。这会导致即使存在阻塞性 Issue，只要审核Agent给出了 PASS verdict，工作流就会继续。

**修复建议**: 修改 `workflow-deep-dive.md` 中 `route_review` 函数的逻辑：

```python
# 修复前
if verdict == "PASS":
    return "PASS"

# 修复后
if verdict == "PASS":
    # 检查是否存在未解决的 blocking issue
    blocking_issues = [
        issue for issue in review_result.get("issues", [])
        if issue.get("blocking", False)
    ]
    if not blocking_issues:
        return "PASS"
    # 存在 blocking issue 但 verdict 为 PASS，视为 NEEDS_REVISION
    return "NEEDS_REVISION"
```

---

### [MEDIUM-6] `ReviewResult` 中 `confidence_score` 类型不一致
**文件与位置**:
- `rv-insights-design.md` 第 361 行: `confidence_score: number;          // 审核Agent对自身判断的确信度 0-1`
- `llm-engineering-deep-dive.md` 第 622-631 行: `confidence_score` (0.0-1.0) 带有 `confidence_breakdown` 对象
- `ui-design-deep-dive.md` 第 314 行: `ConfidenceScore (0-100% 环形图)`

**问题**: 主方案中 `confidence_score` 范围是 0-1，但 UI 设计文档中显示为 0-100%。虽然 UI 可以将 0-1 映射为百分比，但文档未明确说明这种映射关系。此外，`llm-engineering-deep-dive.md` 中增加了 `confidence_breakdown` 字段，但主方案的 `ReviewResult` 接口中未定义该字段。

**修复建议**:
1. 在 `rv-insights-design.md` 的 `ReviewResult` 接口中增加可选的 `confidence_breakdown` 字段
2. 在 `ui-design-deep-dive.md` 中明确说明 `ConfidenceScore` 组件会将 0-1 的小数映射为 0-100% 的百分比显示

---

### [MEDIUM-7] Redis Stream 键名不一致
**文件与位置**:
- `architecture-deep-dive.md` 第 312 行: `agent_tasks:exploration`、`agent_tasks:development`
- `data-model-deep-dive.md` 第 607-616 行: `rv:queue:agent_tasks`、`rv:queue:human_review`
- `llm-engineering-deep-dive.md` 第 769-778 行: `rvinsights:agent:developer:tasks`、`rvinsights:human:review:requests`

**问题**: 三个文档使用了三种不同的 Redis Stream 键名前缀：`agent_tasks:`（架构）、`rv:queue:`（数据模型）、`rvinsights:`（LLM 工程）。这会导致不同模块在操作 Redis 时出现键名不匹配。

**修复建议**: 统一 Redis Stream 键名规范，建议采用 `rv:queue:{queue_name}` 格式（简洁且带命名空间）：

```
rv:queue:agent_tasks:exploration
rv:queue:agent_tasks:development
rv:queue:agent_tasks:review
rv:queue:human_review:requests
rv:queue:human_review:decisions
```

---

### [MEDIUM-8] 主方案引用指向错误
**文件与位置**:
- `rv-insights-design.md` 第 161 行: `详见 architecture-deep-dive.md`
- `rv-insights-design.md` 第 439 行: `详见 llm-engineering-deep-dive.md` 和 `riscv-domain-deep-dive.md`
- `rv-insights-design.md` 第 562 行: `详见 workflow-deep-dive.md`
- `rv-insights-design.md` 第 624 行: `详见 ui-design-deep-dive.md`
- `rv-insights-design.md` 第 703 行: `详见 security-deep-dive.md`
- `rv-insights-design.md` 第 755 行: `详见 data-model-deep-dive.md`

**问题**: 虽然引用关系基本正确，但存在以下问题：
1. `rv-insights-design.md` 第 161 行引用 `architecture-deep-dive.md` 对应"系统架构的组件交互协议"，但 `architecture-deep-dive.md` 的附录对照表（第 587-598 行）中，主方案章节 2.2 对应"全部"，映射关系过于宽泛
2. `rv-insights-design.md` 第 703 行引用 `security-deep-dive.md` 对应第 7 章安全设计，但 `security-deep-dive.md` 的定位说明（第 5 行）说它是"第 7 章的强化替代方案"，存在语义矛盾（是替代还是深化？）

**修复建议**:
1. 明确 `security-deep-dive.md` 的定位：是"替代"还是"深化补充"？如果是替代，主方案第 7 章应标注为"已废弃，详见 security-deep-dive.md"；如果是深化，应标注为"基础设计详见第 7 章，完整方案详见 security-deep-dive.md"
2. 在 `architecture-deep-dive.md` 的附录对照表中，将主方案章节映射细化到具体小节

---

## LOW 级别问题 (考虑改进)

### [LOW-1] 静态分析规则数量不一致
**文件与位置**:
- `rv-insights-design.md` 第 646-666 行: 列出 3 条示例规则
- `riscv-domain-deep-dive.md` 第 162-219 行: 列出 23 条完整规则（ISA 5条 + ABI 5条 + 内存模型 4条 + 性能 4条 + 安全 5条）

**问题**: 主方案说"25条RISC-V静态分析规则"（第 668 行），但 `riscv-domain-deep-dive.md` 实际只列出了 23 条。虽然 23 接近 25，但数量不一致。

**修复建议**: 核实实际规则数量，统一为 23 条或补充至 25 条。

---

### [LOW-2] 前端角色命名不一致
**文件与位置**:
- `rv-insights-design.md` 第 582 行: 序列图中使用 `actor Human as 人类审核者`
- `ui-design-deep-dive.md` 第 29-35 行: 角色定义为 `admin, reviewer, observer`
- `ui-design-deep-dive.md` 第 79 行: `role: "admin" | "reviewer" | "observer"`

**问题**: 主方案序列图中使用泛指的"人类审核者"，而 UI 设计文档中细化为三种角色。这种细化是好的，但主方案中未提及 `observer` 角色。

**修复建议**: 在 `rv-insights-design.md` 第 5 节中简要说明人工审核支持多角色（admin/reviewer/observer），并引用 `ui-design-deep-dive.md`。

---

### [LOW-3] 文档版本号不一致
**文件与位置**:
- `rv-insights-design.md` 第 5 行: `版本: v1.1`
- `architecture-deep-dive.md` 第 3 行: `版本: v1.0`
- `security-deep-dive.md` 第 3 行: `版本: v1.0`
- `data-model-deep-dive.md`: 未标注版本号（仅在末尾有 `文档版本: 1.0.0`）
- `riscv-domain-deep-dive.md` 第 3 行: `版本: v1.0`
- `ui-design-deep-dive.md` 第 3 行: `版本: v1.0`
- `llm-engineering-deep-dive.md` 第 3 行: `版本: v1.0`
- `workflow-deep-dive.md` 第 3 行: `版本: v1.1`

**问题**: 深化文档版本号与主方案不完全同步。主方案为 v1.1，但多数深化文档为 v1.0。虽然这不一定表示内容不一致，但版本号差异可能让读者困惑。

**修复建议**: 当深化文档根据主方案 v1.1 更新后，将版本号统一为 v1.1，或在文档中明确说明"基于主方案 v1.1"。

---

### [LOW-4] 测试矩阵覆盖范围不一致
**文件与位置**:
- `rv-insights-design.md` 第 435-436 行: 支持多种 RISC-V 配置（RV64GC、RV32I、带/不带特定扩展）
- `riscv-domain-deep-dive.md` 第 454-476 行: 详细列出 6 种 QEMU 配置组合
- `architecture-deep-dive.md` 第 220 行: 测试阶段延迟 P90 < 60min（QEMU）

**问题**: 主方案提到支持 RV32I，但 `riscv-domain-deep-dive.md` 的 QEMU 矩阵中使用的是 RV32 IMAC（`QEMU-05`），未单独列出 RV32I。此外，真实硬件测试池（VisionFive2/HiFive/Milk-V）在 `riscv-domain-deep-dive.md` 中有详细描述，但主方案中仅简单提及。

**修复建议**: 在 `riscv-domain-deep-dive.md` 的 QEMU 矩阵中增加 RV32I 基础配置，或在主方案中将 RV32I 修正为 RV32IMAC（如果后者才是实际支持的最低配置）。

---

### [LOW-5] 前端技术栈版本建议未同步
**文件与位置**:
- `rv-insights-design.md` 第 158 行: 前端选型为 **Next.js**，支持 Server-Sent Events
- `ui-design-deep-dive.md` 第 766-779 行: 列出具体依赖版本（`next: ^14`, `@monaco-editor/react: ^4.6` 等）

**问题**: `ui-design-deep-dive.md` 中列出的依赖版本可能随时间过时，但文档中未说明版本锁定策略或更新机制。

**修复建议**: 在 `ui-design-deep-dive.md` 中增加说明："依赖版本以实际 package.json 为准，本文档中的版本号为编写时的参考版本，建议定期审查并更新至最新稳定版。"

---

## 附录: 问题统计

| 级别 | 数量 | 状态 |
|------|------|------|
| CRITICAL | 3 | 待修复 |
| HIGH | 6 | 待修复 |
| MEDIUM | 8 | 建议修复 |
| LOW | 5 | 考虑改进 |
| **总计** | **22** | |

---

## 修复优先级建议

1. **第一批次 (CRITICAL)**: 修复 MAX_ITERATIONS 默认值、开发超时时间、`human_decisions` 字段名不一致。这些问题直接影响系统行为的一致性。
2. **第二批次 (HIGH)**: 修复 `session_id`/`thread_id` 映射、`PlanningPlan` 笔误、安全组件架构图缺失、WebSocket 事件类型不一致、预算默认值联动、`decided_by` 字段名。
3. **第三批次 (MEDIUM)**: 统一术语（人工审核/人类审核、MCP-Server/MCP Server、Checkpointer/Checkpoint）、补充 SLO 硬超时、修复审核通过标准、统一 Redis Stream 键名。
4. **第四批次 (LOW)**: 修正规则数量、同步角色命名、统一文档版本号、补充 RV32I 配置说明、增加依赖版本说明。
