# RV-Insights v2 方案优化任务清单

> 生成时间: 2026-04-23
> 基于全量文档质量审计（8 份文档，~20,000 行）

---

## 阶段一：术语与定义统一（Terminology Consistency）

### 1.1 主文档术语表扩充（rv-insights-v2-design.md Appendix C）
- [ ] **TASK-1.1.1**: 添加 "Human-in-the-Loop / 人类在环" 定义
  - 定义：工作流在关键节点暂停等待人类决策的机制
  - 说明：不是缺陷而是特性，明确 4 个介入点（探索确认/规划审批/审核仲裁/测试验收）
- [ ] **TASK-1.1.2**: 添加 "Dev-Review Iteration / 开发-审核迭代" 定义
  - 定义：Claude Developer 与 Codex Reviewer 之间的自动循环子图
  - 说明：最大迭代次数、退出条件（PASS/MAX_ITERATIONS/REJECT）
- [ ] **TASK-1.1.3**: 添加 "Deep Worker / 深度工作器" 定义
  - 定义：Claude Agent SDK 承担深度推理/分析/生成任务的子代理角色
  - 说明：与 OpenAI Orchestrator 的指挥角色相对
- [ ] **TASK-1.1.4**: 添加 "Orchestrator / 总指挥" 定义
  - 定义：OpenAI Agents SDK 担任的多 Agent 编排总指挥
  - 说明：统一使用 "Orchestrator" 作为代码/文档中的英文标识，"总指挥" 仅用于中文描述
- [ ] **TASK-1.1.5**: 校准现有术语定义一致性
  - Guardrails：统一补充 "声明式配置" 限定词
  - Subagent：统一补充 "隔离上下文" 限定词
  - MCP：统一补充 "Anthropic 提出"  attribution

### 1.2 跨文档术语引用修正
- [ ] **TASK-1.2.1**: `riscv-domain-deep-dive-v2.md` — 添加 "中断" 消歧注释
  - 在 RISC-V CPU 中断规则处添加备注，区分 "CPU 中断" 与 "工作流 interrupt"
- [ ] **TASK-1.2.2**: `workflow-v2-deep-dive.md` — 在首章添加术语表索引引用
  - 增加 "本文档涉及的核心术语定义见 `rv-insights-v2-design.md` Appendix C"
- [ ] **TASK-1.2.3**: `architecture-v2-deep-dive.md` — 在首章添加术语表索引引用
- [ ] **TASK-1.2.4**: `data-model-deep-dive-v2.md` — 在首章添加术语表索引引用
- [ ] **TASK-1.2.5**: `security-deep-dive-v2.md` — 在首章添加术语表索引引用
- [ ] **TASK-1.2.6**: `ui-design-deep-dive-v2.md` — 在首章添加术语表索引引用

---

## 阶段二：成本模型对齐（Cost Model Alignment）

### 2.1 模型单价统一
- [ ] **TASK-2.1.1**: 修正 Codex 定价冲突
  - 当前问题：叙述文档写 $8/MTok，代码表写 output $16/MTok
  - 方案：以 sdk-integration-deep-dive.md 代码表为准（input $4, output $16），叙述文档同步修正
  - 影响文件：`architecture-v2-deep-dive.md` line 886, `rv-insights-v2-design.md` line 349
- [ ] **TASK-2.1.2**: 明确叙述文档中的 "$/MTok" 含义
  - 在 `rv-insights-v2-design.md` 2.1 SDK 对比表添加脚注："价格为 output 端定价，input 端详见各 SDK 章节"
  - 在 `architecture-v2-deep-dive.md` 3.4 添加相同脚注
- [ ] **TASK-2.1.3**: 补充缺失模型说明
  - 在叙述文档中提及 GPT-4.1-mini 和 Claude-Haiku-4-5 的用途（轻量 fallback/快速预检）

### 2.2 月度成本估算对齐
- [ ] **TASK-2.2.1**: 统一 Architecture Doc 与 Design Doc 的月度总成本
  - 当前：Architecture 计算 $11,600（LLM） vs Design 层级分解隐含 ~$17,400
  - 方案：以 Design Doc 的 token 用量（1,700M）为基准重新计算，修正 Architecture Doc
  - 计算验证：(300+150)*8 + 600*16 + (200+400+50)*15 = 22,950，需说明这是 "峰值估算"
- [ ] **TASK-2.2.2**: 对齐优化策略节省比例
  - Architecture Doc 写 "增量审核节省 15-20%"
  - Design Doc 写 "增量审核减少 review token 消耗 60%"
  - 方案：统一口径为 "增量审核减少 review token 消耗 50-60%，整体成本节省 15-20%"

### 2.3 UI 模拟数据修正
- [ ] **TASK-2.3.1**: 修正 `ui-design-deep-dive-v2.md` Session #12345 成本数据
  - 当前：line 193 写 $0.84，line 419-435 写 $6.64，均与单价不符
  - 方案：按正确单价重新计算（800K OpenAI @ $8 + 400K Claude @ $15 = $12.40）
  - 同步修正状态栏示例和详细分解表

---

## 阶段三：SSE/Event 类型统一（待审计完成后补充）

### 3.1 SSE 事件类型审计（需重新执行被中断的审计）
- [ ] **TASK-3.1.1**: 提取所有文档中的 SSE event type 定义
- [ ] **TASK-3.1.2**: 比对事件名一致性（如 session.update vs session_state_update）
- [ ] **TASK-3.1.3**: 比对 payload schema 一致性
- [ ] **TASK-3.1.4**: 统一后更新 `data-model-deep-dive-v2.md` 中的 event_type 枚举
- [ ] **TASK-3.1.5**: 统一后更新 `ui-design-deep-dive-v2.md` 中的前端事件处理代码

---

## 阶段四：缺失实现细节补充（Missing Implementation Details）

### 4.1 RISC-V 静态分析规则可执行配置框架
- [ ] **TASK-4.1.1**: 在 `riscv-domain-deep-dive-v2.md` 中补充 25 条规则的 YAML/JSON 配置格式
  - 每条规则需包含：id, severity, pattern_regex, fix_suggestion_template, enabled
- [ ] **TASK-4.1.2**: 补充 Guardrails 集成伪代码
  - 展示如何将 25 条规则加载为 OpenAI Agents SDK Guardrail 配置
- [ ] **TASK-4.1.3**: 补充规则动态开关机制
  - 通过 MCP Server 在运行时启用/禁用特定规则

### 4.2 ProviderFallbackRouter 完整错误处理
- [ ] **TASK-4.2.1**: 在 `sdk-integration-deep-dive-v2.md` 中补充异常分类表
  - 网络异常（超时/连接重置/DNS 失败）
  - 速率限制（429/配额耗尽）
  - 内容审核（400/内容策略拦截）
  - 模型不可用（503/模型下线）
- [ ] **TASK-4.2.2**: 补充每类异常的重试策略（指数退避/固定延迟/直接降级）
- [ ] **TASK-4.2.3**: 补充熔断器（Circuit Breaker）伪代码
  - 连续失败阈值、半开状态探测、恢复策略

### 4.3 K8s MCP-Server Sidecar 部署拓扑图
- [ ] **TASK-4.3.1**: 在 `architecture-v2-deep-dive.md` 中补充 Mermaid 拓扑图
  - 展示 Orchestrator Pod + MCP-Server Sidecar 的容器布局
  - 展示 MCP-Server 与外部工具（Git/QEMU/文件系统）的连线
- [ ] **TASK-4.3.2**: 补充 Sidecar 资源配置（CPU/内存/健康检查）
- [ ] **TASK-4.3.3**: 补充 Sidecar 与主容器间的 IPC 机制（Unix Socket / gRPC）

### 4.4 并发控制完善（ workflow-v2-deep-dive.md ）
- [ ] **TASK-4.4.1**: 验证 GitLockManager 的 DB 表 `git_locks` 与 schema 一致性
  - 检查 `data-model-deep-dive-v2.md` 中是否定义了该表
  - 如未定义，补充建表语句
- [ ] **TASK-4.4.2**: 验证 QEMUInstancePool 的 DB 表 `qemu_occupancy` 与 schema 一致性
  - 检查 `data-model-deep-dive-v2.md` 中是否定义了该表
  - 如未定义，补充建表语句
- [ ] **TASK-4.4.3**: 补充 Worker Pool 任务优先级策略说明
  - 优先级 1-10 的具体含义映射（如 1=人类触发紧急修复，5=普通 PR，10=低优后台分析）

---

## 阶段五：跨文档引用与导航（Cross-Reference）

### 5.1 文档间链接补充
- [ ] **TASK-5.1.1**: 在每个文档开头添加 "相关文档" 导航块
  - 格式：`> **相关文档**: [主方案](rv-insights-v2-design.md) | [SDK集成](sdk-integration-deep-dive.md) | ...`
- [ ] **TASK-5.1.2**: 在涉及其他文档内容的段落添加直接锚点链接
  - 例如 workflow doc 提及 "数据模型见第 X 章" 时改为可点击链接

### 5.2 Migration Notes 完善
- [ ] **TASK-5.2.1**: 在 `rv-insights-v2-design.md` 8.1 v1->v2 迁移章节补充变更点对照表
  - 列出每项架构变更的具体影响（文件/配置/数据库）
- [ ] **TASK-5.2.2**: 为每个子文档添加独立的 "与 v1 对比" 小结段落

---

## 阶段六：最终审校（Final Review）

### 6.1 代码可执行性抽检
- [ ] **TASK-6.1.1**: 抽样检查 3 段核心伪代码的语法合理性
  - CostRouter 类
  - GitLockManager 类
  - AgentWorkerPool 类
- [ ] **TASK-6.1.2**: 验证所有 SQL 建表语句在 PostgreSQL 15+ 中可执行

### 6.2 Mermaid 图表渲染检查
- [ ] **TASK-6.2.1**: 确认所有 Mermaid 图表语法正确（不少于 2 张/文档）
- [ ] **TASK-6.2.2**: 检查图表中的节点命名与正文一致

### 6.3 假设声明最终复核
- [ ] **TASK-6.3.1**: 确认所有 v2 文档均在显眼位置包含假设声明横幅
- [ ] **TASK-6.3.2**: 确认模型版本、SDK 版本、价格数据均标注置信度

---

## 执行优先级汇总

| 优先级 | 任务编号 | 说明 |
|--------|----------|------|
| P0 | 2.1.1, 2.2.1, 2.3.1 | 成本数据矛盾直接影响商业可行性评估 |
| P0 | 3.1.x | SSE 事件类型不一致影响前后端联调 |
| P1 | 1.1.x, 1.2.x | 术语缺失导致读者理解障碍 |
| P1 | 4.1.x, 4.2.x, 4.3.x | 缺失实现细节降低可落地性 |
| P1 | 4.4.1, 4.4.2 | DB 表缺失导致伪代码无法运行 |
| P2 | 5.1.x, 5.2.x | 导航优化提升阅读体验 |
| P2 | 6.x | 最终质量把关 |
