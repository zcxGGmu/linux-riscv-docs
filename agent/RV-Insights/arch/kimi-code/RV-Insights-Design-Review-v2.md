# RV-Insights 设计方案评估报告

## 评估版本：v2.0 → v3.0 优化方向

> **评估日期**：2026-04-23  
> **评估维度**：架构完整性、Agent 设计深度、数据一致性、安全可靠性、性能成本、领域适配、工程实践、可扩展性  
> **评估结论**：当前方案（v2.0）已达到**可开发落地**的完整度，但在以下 8 个维度存在 30+ 项可优化点，按优先级分为 P0（必须）、P1（强烈建议）、P2（建议）三级。

---

## 一、架构层面（7 项）

### 1.1 [P0] 缺少 RAG 知识库详细设计

**现状**：v2.0 仅在工具层提到"知识库 (RAG)"，但未给出任何实现细节。RISC-V 领域知识密集，RAG 是方案的核心竞争力之一。

**问题**：
- 向量数据库选型未定（PGVector / Milvus / Chroma / Qdrant？）
- 文档切分策略缺失（ISA 规范按章节切？按指令切？）
- 检索策略未定义（ dense retrieval / hybrid search / rerank？）
- 知识更新机制缺失（ISA 规范更新后如何同步？）

**优化建议**：

```yaml
# 建议增加的 RAG 架构模块
rag_layer:
  vector_store: qdrant  # 或 pgvector（与 PostgreSQL 统一）
  embedding_model: "openai/text-embedding-3-large"
  chunk_strategy:
    isa_spec:
      chunk_size: 512
      overlap: 128
      split_by: ["chapter", "section", "instruction"]
    kernel_docs:
      chunk_size: 1024
      overlap: 256
      split_by: ["document", "section"]
    source_code:
      chunk_size: 2048  # 函数级
      overlap: 0
      split_by: ["function", "struct", "macro"]
  retrieval:
    top_k: 10
    reranker: "cohere/rerank-multilingual-v3.0"
    filters:
      - isa_version: "20240411"  # 过滤特定版本
      - project: "linux"         # 过滤特定项目
  update_policy:
    auto_sync_interval: "weekly"
    source_repos:
      - "https://github.com/riscv/riscv-isa-manual"
      - "https://github.com/torvalds/linux/tree/master/Documentation"
```

### 1.2 [P0] 缺少反馈闭环（Feedback Loop）设计

**现状**：方案是单向流水线（探索→规划→开发→审核→测试），没有设计 Agent 学习改进的机制。

**问题**：
- 人工修改后的最终代码，如何反哺开发 Agent 的 Prompt？
- 审核 Agent 的误报/漏报如何纠正？
- 探索 Agent 的准确率如何持续提升？

**优化建议**：引入三层反馈闭环：

```
┌─────────────────────────────────────────────────────────────┐
│                    反馈闭环架构                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  第一层：即时反馈（单任务内）                                │
│  • 人工 HITL 拒绝时，记录拒绝原因 → 直接修改当前任务 Prompt  │
│  • 审核迭代中，上一轮审核结果作为下一轮上下文                 │
│                                                             │
│  第二层：短期反馈（跨任务）                                  │
│  • 相似贡献点的历史成功方案 → 作为 Few-shot 示例             │
│  • 常见审核问题模式 → 生成"预审核检查清单"                   │
│                                                             │
│  第三层：长期反馈（模型优化）                                │
│  • 收集高质量人工修正数据 → 用于 RAG 知识库更新              │
│  • 收集 Prompt-Response 对 → 用于模型微调（如适用）         │
│  • Agent 表现指标趋势分析 → 自动调整模型选择策略             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**具体实现**：

```python
# rv_insights/feedback/loop.py
class FeedbackCollector:
    """
    反馈收集器
    
    收集以下数据用于持续改进：
    1. 人工 HITL 决策及反馈文本
    2. 审核迭代中问题的收敛路径
    3. 最终提交到上游社区的 Patch 接受率
    4. 每个 Agent 的 Token 效率指标
    """
    
    async def collect_hitl_feedback(self, task_id: str, decision: HITLDecision):
        """收集 HITL 反馈"""
        # 存储到 feedback 表
        await self.db.execute("""
            INSERT INTO agent_feedback 
            (task_id, stage, agent_name, feedback_type, feedback_text, original_output)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, task_id, decision.stage, decision.agent_name, 
             decision.decision, decision.feedback, decision.original_output)
    
    async def generate_few_shot_examples(self, category: str, limit: int = 5) -> List[dict]:
        """
        从成功任务中提取 Few-shot 示例
        
        用于增强 Agent 的 Prompt，提升任务质量
        """
        examples = await self.db.fetch("""
            SELECT 
                input_artifact.content as input,
                output_artifact.content as output,
                t.target_project
            FROM tasks t
            JOIN stages s ON t.task_id = s.task_id
            JOIN artifacts input_artifact ON s.input_artifact_id = input_artifact.artifact_id
            JOIN artifacts output_artifact ON s.output_artifact_id = output_artifact.artifact_id
            WHERE t.status = 'complete'
              AND s.stage_type = $1
              AND s.cost_usd < 10  -- 过滤异常高成本案例
            ORDER BY s.execution_time_seconds ASC  -- 优先学习高效的
            LIMIT $2
        """, category, limit)
        
        return examples
    
    async def analyze_agent_performance(self, agent_name: str, days: int = 30) -> dict:
        """分析 Agent 表现趋势"""
        stats = await self.db.fetchrow("""
            SELECT 
                AVG(cost_usd) as avg_cost,
                AVG(execution_time_seconds) as avg_time,
                AVG(token_input + token_output) as avg_tokens,
                COUNT(*) FILTER (WHERE status = 'completed') as success_count,
                COUNT(*) FILTER (WHERE status = 'failed') as fail_count
            FROM stages
            WHERE agent_name = $1
              AND created_at >= NOW() - INTERVAL '$2 days'
        """, agent_name, days)
        
        return dict(stats)
```

### 1.3 [P1] 缺少代码审查上下文链（Context Chain）

**现状**：审核 Agent 只看当前 diff，缺乏代码变更的完整上下文。

**问题**：
- 审核 Agent 不知道这个函数为什么存在
- 不了解相关函数的调用关系
- 无法判断变更是否符合整体设计意图

**优化建议**：构建代码审查上下文链

```python
# rv_insights/agents/review/context_chain.py
class ReviewContextBuilder:
    """
    构建审核所需的完整代码上下文
    """
    
    async def build_context(self, repo_path: Path, modified_files: List[str]) -> dict:
        context = {
            "modified_files": {},
            "related_functions": {},
            "callers": {},
            "callees": {},
            "recent_history": [],
            "maintainers": []
        }
        
        for file_path in modified_files:
            full_path = repo_path / file_path
            
            # 1. 文件完整内容（而非仅 diff）
            if full_path.exists():
                with open(full_path) as f:
                    context["modified_files"][file_path] = f.read()
            
            # 2. 使用 ctags/cscope 找出相关函数
            related = await self._find_related_symbols(repo_path, file_path)
            context["related_functions"][file_path] = related
            
            # 3. 调用关系（使用 callgraph 工具）
            callers = await self._find_callers(repo_path, file_path)
            callees = await self._find_callees(repo_path, file_path)
            context["callers"][file_path] = callers
            context["callees"][file_path] = callees
        
        # 4. 该文件最近 6 个月的修改历史
        context["recent_history"] = await self._get_file_history(repo_path, modified_files)
        
        # 5. MAINTAINERS 信息
        context["maintainers"] = await self._get_maintainers(repo_path, modified_files)
        
        return context
    
    async def _find_related_symbols(self, repo_path: Path, file_path: str) -> List[dict]:
        """使用 ctags 找到文件中定义的关键符号"""
        result = subprocess.run(
            ['ctags', '-x', '--c-kinds=fp', str(repo_path / file_path)],
            capture_output=True, text=True
        )
        symbols = []
        for line in result.stdout.split('\n')[:20]:
            parts = line.split(None, 3)
            if len(parts) >= 4:
                symbols.append({
                    "name": parts[0],
                    "type": parts[1],
                    "line": parts[2],
                    "context": parts[3]
                })
        return symbols
```

### 1.4 [P1] 缺少并发控制与冲突解决

**现状**：未考虑多任务同时修改同一仓库的场景。

**问题**：
- 两个任务同时基于同一分支开发，会产生 Git 冲突
- 多个开发 Agent 同时写同一文件
- 测试环境资源竞争

**优化建议**：

```python
# rv_insights/concurrency/controller.py
class WorkspaceManager:
    """
    工作空间管理器
    
    为每个任务分配独立的工作空间，避免冲突
    """
    
    async def allocate_workspace(self, task_id: str, project: str) -> Path:
        """
        分配独立工作空间
        
        策略：
        1. Git Worktree：为每个任务创建独立 worktree
        2. 分支命名：rv-insights/{task_id}
        3. 资源隔离：每个 worktree 独立 Docker 沙箱
        """
        base_repo = Path(f"/repos/{project}")
        workspace = Path(f"/workspaces/{task_id}/{project}")
        
        # 使用 git worktree 创建独立工作目录
        subprocess.run([
            'git', '-C', str(base_repo), 'worktree', 'add',
            '-b', f'rv-insights/{task_id}',
            str(workspace),
            'HEAD'
        ], check=True)
        
        # 记录锁
        await self.lock_manager.acquire(f"workspace:{task_id}")
        
        return workspace
    
    async def release_workspace(self, task_id: str):
        """释放工作空间"""
        workspace = Path(f"/workspaces/{task_id}")
        
        # 移除 git worktree
        subprocess.run([
            'git', 'worktree', 'remove', str(workspace)
        ], check=False)
        
        # 释放锁
        await self.lock_manager.release(f"workspace:{task_id}")

class ResourceQuotaManager:
    """
    资源配额管理
    
    限制同时运行的 Agent 数量和资源消耗
    """
    
    def __init__(self):
        self.max_concurrent_sandboxes = 10
        self.max_concurrent_llm_calls = 20
        self.daily_cost_budget = 100.0  # USD
    
    async def acquire_sandbox(self, task_id: str) -> bool:
        """申请沙箱资源"""
        current = await self.get_active_sandbox_count()
        if current >= self.max_concurrent_sandboxes:
            return False
        
        await redis.setex(f"sandbox:{task_id}", 3600, "active")
        return True
    
    async def check_cost_budget(self, estimated_cost: float) -> bool:
        """检查成本预算"""
        today_cost = await self.get_today_cost()
        return (today_cost + estimated_cost) <= self.daily_cost_budget
```

### 1.5 [P1] 缺少与外部社区系统的深度集成

**现状**：方案主要关注内部 Agent 流水线，缺少与 RISC-V 开源社区基础设施的集成设计。

**缺失功能**：
- 自动 `git format-patch` + `git send-email`
- 自动创建 GitHub PR（针对 GitHub 托管的项目如 OpenSBI）
- Patchwork 状态同步
- 与 Kernel CI / 0-Day Bot 集成

**优化建议**：

```python
# rv_insights/integrations/community.py
class CommunityIntegration:
    """社区集成模块"""
    
    async def submit_patch(self, task_id: str, method: str = "mail") -> dict:
        """
        提交 Patch 到社区
        
        Args:
            method: "mail" | "github_pr" | "gitlab_mr"
        """
        if method == "mail":
            return await self._send_email_patch(task_id)
        elif method == "github_pr":
            return await self._create_github_pr(task_id)
    
    async def _send_email_patch(self, task_id: str) -> dict:
        """通过 git send-email 发送 Patch"""
        workspace = Path(f"/workspaces/{task_id}")
        
        # 获取维护者列表
        result = subprocess.run(
            ['scripts/get_maintainer.pl', '--separator=,', '--nokeywords',
             str(workspace / '*.patch')],
            capture_output=True, text=True, cwd=workspace
        )
        recipients = result.stdout.strip()
        
        # 发送邮件
        result = subprocess.run([
            'git', 'send-email',
            '--to', recipients,
            '--cc', 'linux-riscv@lists.infradead.org',
            '--confirm=never',
            str(workspace / '*.patch')
        ], capture_output=True, text=True, cwd=workspace)
        
        return {
            "method": "mail",
            "recipients": recipients,
            "success": result.returncode == 0,
            "output": result.stdout
        }
    
    async def sync_patchwork_status(self, patch_url: str) -> dict:
        """同步 Patchwork 状态"""
        # Patchwork API
        # GET /api/1.2/patches/?msgid=<message-id>
        pass
```

### 1.6 [P2] 缺少多租户设计

**现状**：方案假设单租户运行，未考虑团队协作场景。

**优化建议**：
- 用户/团队隔离
- 资源配额（每个团队的 LLM 预算）
- 权限角色（管理员/审核员/开发者/只读）
- 团队共享知识库

### 1.7 [P2] 缺少插件/扩展机制

**现状**：Agent 工具是硬编码的，社区无法扩展。

**优化建议**：设计插件系统

```python
# rv_insights/plugins/manager.py
class PluginManager:
    """
    插件管理器
    
    允许社区贡献自定义工具和分析器
    """
    
    async def load_plugin(self, plugin_path: Path):
        """加载插件"""
        # 插件提供：tools/、analyzers/、prompts/ 目录
        pass
    
    async def register_custom_tool(self, agent_type: str, tool: Tool):
        """为特定 Agent 注册自定义工具"""
        pass
```

---

## 二、Agent 设计层面（6 项）

### 2.1 [P0] Prompt 工程不够系统化

**现状**：System Prompt 是硬编码的字符串，缺少版本管理和优化机制。

**问题**：
- Prompt 变更无法 A/B 测试
- 没有 Few-shot 示例管理
- Prompt 注入风险未防护
- 不同项目/难度级别使用相同 Prompt

**优化建议**：

```python
# rv_insights/prompts/engine.py
class PromptEngine:
    """
    Prompt 引擎
    
    功能：
    1. Prompt 版本管理
    2. 动态 Few-shot 注入
    3. A/B 测试支持
    4. Prompt 注入防护
    """
    
    def __init__(self, registry: PromptRegistry):
        self.registry = registry
    
    async def render(
        self,
        agent_name: str,
        task_context: dict,
        variant: str = "default"  # A/B 测试变体
    ) -> str:
        """渲染最终 Prompt"""
        
        # 1. 加载基础模板
        template = await self.registry.get_template(agent_name, variant)
        
        # 2. 动态注入 Few-shot 示例
        examples = await self._select_few_shots(
            agent_name=agent_name,
            category=task_context.get("category"),
            project=task_context.get("target_project"),
            limit=3
        )
        
        # 3. 注入 RAG 检索结果
        rag_context = await self._retrieve_relevant_context(task_context)
        
        # 4. 渲染模板
        prompt = template.render(
            task=task_context,
            examples=examples,
            rag=rag_context,
            guidelines=self._get_project_guidelines(task_context.get("target_project"))
        )
        
        # 5. 注入防护（防止用户输入污染 Prompt）
        prompt = self._sanitize_prompt(prompt)
        
        return prompt
    
    def _sanitize_prompt(self, prompt: str) -> str:
        """
        Prompt 注入防护
        
        策略：
        1. 用户输入使用 XML 标签包裹
        2. 转义特殊标记（如 </system>、</instruction>）
        3. 检测常见的注入模式
        """
        # 检测注入尝试
        injection_patterns = [
            r'</\s*(system|instruction|prompt)',
            r'ignore\s+(previous|above)\s+instructions',
            r'new\s+instructions?:',
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                logger.warning("Potential prompt injection detected")
                # 可以选择拒绝处理或转义
        
        return prompt
```

### 2.2 [P0] 错误处理和降级策略不足

**现状**：Agent 执行失败时的处理较粗糙。

**问题**：
- LLM API 超时/限流时无优雅降级
- 沙箱崩溃后任务状态丢失
- 长时间任务无法中断恢复
- 部分工具失败后整体失败

**优化建议**：引入熔断器和重试策略

```python
# rv_insights/resilience/circuit_breaker.py
from enum import Enum
import asyncio

class CircuitState(Enum):
    CLOSED = "closed"      # 正常
    OPEN = "open"          # 熔断
    HALF_OPEN = "half_open"  # 试探

class LLMCircuitBreaker:
    """
    LLM 调用熔断器
    
    防止 LLM API 故障拖垮整个系统
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
    
    async def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
            else:
                raise CircuitBreakerOpen("LLM API circuit is open")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
    
    def _on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        else:
            self.failure_count = 0
    
    def _should_attempt_reset(self) -> bool:
        if self.last_failure_time is None:
            return True
        return (time.time() - self.last_failure_time) >= self.recovery_timeout


# 使用示例
breaker = LLMCircuitBreaker()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def call_llm_with_resilience(agent, input_text):
    return await breaker.call(
        Runner.run,
        agent,
        input_text
    )
```

### 2.3 [P1] Agent 工具粒度太粗

**现状**：工具函数粒度较大（如 `search_codebase` 一个函数处理所有搜索）。

**问题**：
- LLM 难以精确控制搜索行为
- 工具输出太长，浪费 Token
- 无法组合细粒度操作

**优化建议**：细粒度工具设计

```python
# 将粗粒度工具拆分为细粒度工具

# 原设计（粗）
@function_tool
async def search_codebase(project: str, query: str, search_type: str) -> dict:
    ...

# 优化设计（细）
@function_tool
async def grep_code(project: str, pattern: str, path: str = "") -> list:
    """精确文本搜索"""
    ...

@function_tool
async def find_references(project: str, symbol: str) -> list:
    """查找符号引用"""
    ...

@function_tool
async def read_function_body(project: str, file: str, function: str) -> str:
    """读取特定函数实现"""
    ...

@function_tool
async def read_file_region(project: str, file: str, start_line: int, end_line: int) -> str:
    """读取文件特定行范围"""
    ...

@function_tool
async def get_file_history(project: str, file: str, limit: int = 10) -> list:
    """获取文件修改历史"""
    ...
```

### 2.4 [P1] 缺少 Agent 自检（Self-Correction）机制

**现状**：Agent 执行后没有自我验证步骤。

**优化建议**：为每个 Agent 增加自检步骤

```python
# 探索 Agent 自检
async def self_check_discovery(result: DiscoveryOutput) -> bool:
    """
    探索结果自检
    
    检查项：
    1. 贡献点是否确实在 RISC-V 范围内
    2. 是否提供了可验证的来源链接
    3. 可行性评分是否有依据
    4. 是否与已有贡献重复
    """
    checks = [
        result.has_riscv_relevance,
        all(cp.source_url for cp in result.contribution_points),
        all(cp.feasibility_score > 0 for cp in result.contribution_points),
        len(result.contribution_points) <= 20  # 防止输出爆炸
    ]
    return all(checks)

# 开发 Agent 自检
async def self_check_development(result: DevelopmentResult) -> bool:
    """
    开发结果自检
    
    检查项：
    1. 修改的文件是否在规划范围内
    2. 编译是否通过
    3. diff 是否包含无关变更
    4. 是否有明显的语法错误
    """
    ...
```

### 2.5 [P1] 审核 Agent 缺少"代码语义理解"

**现状**：审核主要基于文本模式匹配，缺乏对代码语义的深度理解。

**优化建议**：引入 AST 分析工具

```python
# 使用 Tree-sitter 进行代码语义分析
import tree_sitter_c as tspython
from tree_sitter import Language, Parser

class CodeSemanticAnalyzer:
    """代码语义分析器"""
    
    def __init__(self):
        self.parser = Parser(Language(tspython.language()))
    
    def analyze_change(self, old_code: str, new_code: str) -> dict:
        """分析代码变更的语义影响"""
        
        old_tree = self.parser.parse(old_code.encode())
        new_tree = self.parser.parse(new_code.encode())
        
        return {
            "api_changes": self._detect_api_changes(old_tree, new_tree),
            "control_flow_changes": self._detect_control_flow_changes(old_tree, new_tree),
            "data_flow_changes": self._detect_data_flow_changes(old_tree, new_tree),
            "lock_pattern_changes": self._detect_lock_changes(old_tree, new_tree),
        }
    
    def _detect_lock_changes(self, old_tree, new_tree) -> list:
        """检测锁模式变更（内核代码特别重要）"""
        # 检查 spin_lock/spin_unlock 配对
        # 检查 mutex 获取/释放
        # 检查 RCU 读临界区
        ...
```

### 2.6 [P2] 缺少 Agent 间"经验共享"

**现状**：每个任务独立运行，Agent 之间不共享经验。

**优化建议**：共享记忆机制

```python
class SharedMemory:
    """
    Agent 共享记忆
    
    存储：
    - 常见错误的修复模式
    - 特定维护者的偏好
    - 项目的特殊约定
    """
    
    async def record_fix_pattern(self, error_pattern: str, fix_pattern: str, project: str):
        """记录修复模式"""
        await self.db.execute("""
            INSERT INTO fix_patterns (error_pattern, fix_pattern, project, usage_count)
            VALUES ($1, $2, $3, 1)
            ON CONFLICT (error_pattern, project) 
            DO UPDATE SET usage_count = fix_patterns.usage_count + 1
        """, error_pattern, fix_pattern, project)
    
    async def get_relevant_patterns(self, error_message: str, project: str) -> List[dict]:
        """获取相关的修复模式"""
        return await self.db.fetch("""
            SELECT error_pattern, fix_pattern, usage_count
            FROM fix_patterns
            WHERE project = $1
            ORDER BY similarity(error_pattern, $2) DESC
            LIMIT 5
        """, project, error_message)
```

---

## 三、数据与状态管理（4 项）

### 3.1 [P0] 分布式事务缺失

**现状**：任务状态变更和 Artifact 存储是两个独立操作，可能出现不一致。

**问题**：
- 阶段标记为 completed 但 Artifact 写入失败
- HITL 决策已记录但阶段状态未更新

**优化建议**：引入 Saga 模式或 Outbox 模式

```python
# rv_insights/transaction/saga.py
class StageCompletionSaga:
    """
    阶段完成 Saga
    
    确保以下操作原子性：
    1. 更新阶段状态为 completed
    2. 写入 output Artifact
    3. 创建下一阶段或 HITL 请求
    4. 发送事件通知
    """
    
    async def execute(self, stage_id: str, artifact: Artifact) -> bool:
        compensations = []
        
        try:
            # Step 1: 写入 Artifact
            artifact_id = await self.artifact_store.save(artifact)
            compensations.append(lambda: self.artifact_store.delete(artifact_id))
            
            # Step 2: 更新阶段状态
            await self.db.execute(
                "UPDATE stages SET status = 'completed', output_artifact_id = $1 WHERE stage_id = $2",
                artifact_id, stage_id
            )
            compensations.append(lambda: self.db.execute(
                "UPDATE stages SET status = 'running', output_artifact_id = NULL WHERE stage_id = $1",
                stage_id
            ))
            
            # Step 3: 创建 HITL 请求
            hitl_request = await self.hitl_manager.create_request(stage_id)
            compensations.append(lambda: self.hitl_manager.cancel(hitl_request.request_id))
            
            # Step 4: 发送事件
            await self.event_bus.publish("stage.completed", {"stage_id": stage_id})
            
            return True
            
        except Exception as e:
            # 执行补偿
            for compensation in reversed(compensations):
                try:
                    await compensation()
                except Exception as ce:
                    logger.error(f"Compensation failed: {ce}")
            
            return False
```

### 3.2 [P1] 缺少 Artifact 版本管理

**现状**：Artifact 只有简单版本号，没有完整版本链。

**优化建议**：类似 Git 的 Artifact 版本管理

```python
class ArtifactVersionManager:
    """
    Artifact 版本管理
    
    支持：
    - 版本链（类似 Git commit graph）
    - 差异比较
    - 分支合并（多 Agent 并行修改）
    """
    
    async def create_version(self, artifact_id: str, content: dict, parent_id: str = None) -> str:
        version_id = f"{artifact_id}-v{uuid.uuid4().hex[:8]}"
        
        await self.db.execute("""
            INSERT INTO artifact_versions (version_id, artifact_id, parent_id, content, created_at)
            VALUES ($1, $2, $3, $4, NOW())
        """, version_id, artifact_id, parent_id, json.dumps(content))
        
        return version_id
    
    async def diff_versions(self, v1: str, v2: str) -> dict:
        """比较两个 Artifact 版本"""
        ...
```

### 3.3 [P1] 长时间任务的中断恢复

**现状**：Agent 执行超时后，任务需要从头开始。

**优化建议**：Checkpoint 机制

```python
class CheckpointManager:
    """
    检查点管理器
    
    支持 Agent 执行过程中的状态保存和恢复
    """
    
    async def save_checkpoint(self, task_id: str, stage_id: str, state: dict):
        """保存检查点"""
        checkpoint = {
            "task_id": task_id,
            "stage_id": stage_id,
            "agent_state": state,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await redis.setex(
            f"checkpoint:{task_id}:{stage_id}",
            86400 * 7,  # 保留 7 天
            json.dumps(checkpoint)
        )
    
    async def restore_checkpoint(self, task_id: str, stage_id: str) -> Optional[dict]:
        """恢复检查点"""
        data = await redis.get(f"checkpoint:{task_id}:{stage_id}")
        return json.loads(data) if data else None
```

### 3.4 [P2] 数据归档策略

**现状**：未定义历史数据的归档和清理策略。

**优化建议**：
- 30 天前的 Agent 对话日志归档到 S3 Glacier
- 90 天前的 Artifact 文件压缩归档
- 1 年前的审计日志迁移到冷存储

---

## 四、性能与成本（5 项）

### 4.1 [P0] Token 消耗优化策略缺失

**现状**：没有系统性的 Token 优化措施。

**优化建议**：

```python
# rv_insights/optimization/token.py
class TokenOptimizer:
    """Token 优化器"""
    
    async def optimize_prompt(self, prompt: str, max_tokens: int = 4000) -> str:
        """
        优化 Prompt 以减少 Token 消耗
        
        策略：
        1. 去除冗余空白
        2. 使用缩写和符号
        3. 截断过长的代码片段（保留头尾，中间省略）
        4. 优先使用更短的同义词
        """
        ...
    
    async def cache_prompt(self, prompt_hash: str, response: str):
        """
        Prompt 缓存
        
        对于重复的查询（如相同的代码风格检查），直接返回缓存结果
        """
        await redis.setex(f"prompt_cache:{prompt_hash}", 3600, response)
    
    async def summarize_context(self, context: str, target_length: int = 2000) -> str:
        """
        上下文摘要
        
        当上下文过长时，使用轻量级模型先进行摘要
        """
        if len(context) > target_length * 2:
            # 使用 gpt-4o-mini 或 claude-haiku 进行摘要
            summary = await self.summarizer.summarize(context, target_length)
            return summary
        return context
```

### 4.2 [P1] 模型路由策略可以更智能

**现状**：模型配置是静态的，没有根据任务复杂度动态选择。

**优化建议**：

```python
class AdaptiveModelRouter:
    """
    自适应模型路由器
    
    根据任务特征动态选择模型：
    - 简单任务（代码风格检查）→ gpt-4o-mini / claude-haiku
    - 中等任务（Bug 修复）→ gpt-4o / claude-sonnet
    - 复杂任务（架构设计）→ o3-mini / claude-opus
    """
    
    def select_model(self, task_complexity: str, accuracy_requirement: str) -> str:
        routing_table = {
            ("simple", "low"): "gpt-4o-mini",
            ("simple", "medium"): "gpt-4o",
            ("medium", "low"): "gpt-4o",
            ("medium", "medium"): "claude-sonnet-4",
            ("complex", "high"): "o3-mini",
            ("critical", "high"): "claude-opus-4",
        }
        return routing_table.get((task_complexity, accuracy_requirement), "gpt-4o")
```

### 4.3 [P1] 缺少并行执行优化

**现状**：审核层虽然提到并行审核，但没有具体的并行执行框架。

**优化建议**：

```python
# 审核层并行执行
async def run_parallel_review(code: DevelopmentResult) -> ReviewScorecard:
    """并行运行三个审核 Agent"""
    
    results = await asyncio.gather(
        run_style_review(code),
        run_logic_review(code),
        run_security_review(code),
        return_exceptions=True
    )
    
    scorecard = ReviewScorecard()
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Review agent failed: {result}")
            continue
        for issue in result.issues:
            scorecard.add_issue(issue)
    
    return scorecard
```

### 4.4 [P2] 缺少预热和连接池管理

**现状**：每次 LLM 调用都新建连接。

**优化建议**：
- 使用 httpx AsyncClient 连接池
- LLM API 连接预热
- 沙箱镜像预拉取

### 4.5 [P2] 批量处理支持

**现状**：每个贡献点单独处理，无法批量优化。

**优化建议**：支持批量探索结果的处理

---

## 五、安全与可靠性（4 项）

### 5.1 [P0] LLM 输出污染风险

**现状**：Agent 输出直接用于代码生成和命令执行，没有充分的输出校验。

**风险**：
- LLM 生成的代码包含恶意逻辑
- LLM 生成的命令包含危险操作
- LLM 被 Prompt 注入后执行非预期操作

**优化建议**：多层输出校验

```python
class OutputSanitizer:
    """输出消毒器"""
    
    FORBIDDEN_PATTERNS = [
        # 网络相关
        r'curl\s+.*\|\s*(sh|bash)',
        r'wget\s+.*\|\s*(sh|bash)',
        r'fetch\(.*http',
        # 系统破坏
        r'rm\s+-rf\s+/',
        r'mkfs\.',
        r'dd\s+if=/dev/zero\s+of=/dev/',
        # 信息窃取
        r'cat\s+/etc/shadow',
        r'cat\s+~/.ssh/id_rsa',
        # 后门
        r'nc\s+-[lL]\s+\d+',
        r'/bin/sh\s+-i',
    ]
    
    def sanitize_code(self, code: str) -> tuple[bool, list[str]]:
        """
        检查生成的代码是否包含可疑模式
        
        Returns: (是否安全, 发现的问题列表)
        """
        issues = []
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                issues.append(f"Suspicious pattern detected: {pattern}")
        
        return len(issues) == 0, issues
    
    def sanitize_command(self, command: str) -> tuple[bool, str]:
        """检查命令是否安全"""
        # 只允许白名单内的命令
        allowed_commands = {"make", "gcc", "git", "cat", "grep", ...}
        ...
```

### 5.2 [P1] 沙箱逃逸风险

**现状**：虽然使用了 gVisor，但 Docker Socket 挂载给 orchestrator 带来了特权提升风险。

**优化建议**：
- 使用 Kubernetes CRD + containerd 直接管理沙箱，不挂载 Docker Socket
- gVisor 使用 ptrace 平台而非 KVM（兼容性更好）
- 定期扫描沙箱镜像漏洞

### 5.3 [P1] 敏感信息泄露防护

**现状**：Agent 可能将 API Keys、密码等敏感信息输出到日志。

**优化建议**：

```python
class SecretMasker:
    """敏感信息掩码器"""
    
    PATTERNS = [
        (r'sk-[a-zA-Z0-9]{48}', '***API_KEY***'),
        (r'-----BEGIN (RSA |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END', '***PRIVATE_KEY***'),
        (r'password["\']?\s*[:=]\s*["\']?[^"\'\s]+', 'password=***'),
    ]
    
    def mask(self, text: str) -> str:
        for pattern, replacement in self.PATTERNS:
            text = re.sub(pattern, replacement, text)
        return text
```

### 5.4 [P2] 审计日志完整性

**现状**：审计日志可以被人为删除。

**优化建议**：
- 审计日志只追加，不允许删除
- 使用 WORM（Write Once Read Many）存储
- 定期哈希链校验

---

## 六、RISC-V 领域适配（3 项）

### 6.1 [P1] 缺少 RISC-V 扩展兼容性矩阵

**现状**：没有系统跟踪各项目对不同 RISC-V 扩展的支持状态。

**优化建议**：

```python
# rv_insights/riscv/extension_matrix.py
class RISCVExtensionMatrix:
    """
    RISC-V 扩展兼容性矩阵
    
    跟踪各项目对各扩展的支持状态，用于发现贡献机会
    """
    
    EXTENSIONS = {
        # 标准扩展
        "I": {"name": "Base Integer", "status": "mandatory"},
        "M": {"name": "Integer Multiplication", "status": "standard"},
        "A": {"name": "Atomic", "status": "standard"},
        "F": {"name": "Single-Precision FP", "status": "standard"},
        "D": {"name": "Double-Precision FP", "status": "standard"},
        "C": {"name": "Compressed", "status": "standard"},
        "V": {"name": "Vector", "status": "standard"},
        "Zicbom": {"name": "Cache Block Mgmt", "status": "standard"},
        "Zicond": {"name": "Conditional Operations", "status": "standard"},
        # 特权架构
        "S": {"name": "Supervisor", "status": "standard"},
        "U": {"name": "User", "status": "standard"},
        "H": {"name": "Hypervisor", "status": "standard"},
    }
    
    async def check_project_support(self, project: str) -> dict:
        """检查项目对各扩展的支持状态"""
        results = {}
        
        for ext, info in self.EXTENSIONS.items():
            # 在代码库中搜索扩展相关实现
            has_support = await self._check_extension_in_project(project, ext)
            results[ext] = {
                **info,
                "supported": has_support,
                "missing_opportunity": not has_support and info["status"] == "standard"
            }
        
        return results
```

### 6.2 [P1] 缺少硬件平台数据库

**现状**：没有跟踪各 RISC-V 硬件平台的内核支持状态。

**优化建议**：维护硬件平台数据库

```python
class HardwarePlatformDB:
    """
    RISC-V 硬件平台数据库
    
    用于发现新硬件的驱动移植机会
    """
    
    PLATFORMS = [
        {
            "name": "SpacemiT K1",
            "vendor": "SpacemiT",
            "cpu": "X60",
            "extensions": ["I", "M", "A", "F", "D", "C", "V"],
            "linux_support": {
                "status": "in_progress",  # supported | in_progress | none
                "since_version": None,
                "dts_files": ["k1.dtsi", "k1-bananapi-f3.dts"],
            },
            "opensbi_support": True,
            "qemu_support": False,
        },
        # ... 更多平台
    ]
```

### 6.3 [P2] 缺少与 RISC-V 国际组织的集成

**现状**：未考虑与 RISC-V International 的工具链集成。

**优化建议**：
- 同步 RISC-V ISA 规范发布
- 跟踪 riscv-non-isa 仓库的更新
- 集成 RISC-V 合规性测试套件（riscv-arch-test）

---

## 七、可观测性（3 项）

### 7.1 [P1] 缺少 Agent 级别的 SLA 监控

**现状**：只有基础的健康检查，没有对 Agent 服务质量的监控。

**优化建议**：

```python
# 监控指标
AGENT_SLA_METRICS = {
    "discovery.accuracy": "发现贡献点的可行性准确率",
    "development.compile_rate": "代码生成后的编译通过率",
    "review.convergence": "审核迭代收敛轮数分布",
    "testing.pass_rate": "测试通过率",
    "hitl.response_time": "人工审核响应时间分布",
    "cost.per_contribution": "每个成功贡献的平均成本",
    "token.efficiency": "Token 产出效率（有效代码 / 总 Token）",
}
```

### 7.2 [P1] 缺少成本实时看板

**现状**：成本信息分散在日志中。

**优化建议**：实时成本监控面板

```python
class CostDashboard:
    """成本监控面板数据"""
    
    async def get_realtime_metrics(self) -> dict:
        return {
            "today": {
                "total_cost_usd": await self.get_today_cost(),
                "total_tokens": await self.get_today_tokens(),
                "task_count": await self.get_today_task_count(),
                "cost_by_agent": await self.get_cost_breakdown(),
            },
            "alerts": await self.get_active_alerts(),
            "budget_status": await self.get_budget_status(),
        }
```

### 7.3 [P2] 缺少 Agent 决策可解释性

**现状**：Agent 的决策过程不透明。

**优化建议**：为每个关键决策生成解释报告

```python
class DecisionExplainer:
    """决策解释器"""
    
    async def explain_discovery(self, contribution: ContributionPoint) -> str:
        """解释为什么发现这个贡献点"""
        return f"""
        ## 贡献点发现依据
        
        **来源可靠性**: {contribution.source_type}
        **关键词匹配**: {contribution.matched_keywords}
        **社区活跃度**: {contribution.thread_activity}
        **技术可行性**: {contribution.feasibility_rationale}
        **历史相似案例**: {await self.find_similar_cases(contribution)}
        """
```

---

## 八、工程实践（3 项）

### 8.1 [P1] 测试策略不完善

**现状**：方案中缺少对 Agent 系统本身的测试设计。

**优化建议**：

```python
# 测试策略
"""
1. 单元测试
   - 每个工具函数的独立测试
   - Mock LLM 响应
   - 边界条件测试

2. 集成测试
   - 端到端流水线测试（使用模拟的 LLM 响应）
   - 沙箱环境测试
   - 数据库事务测试

3. Agent 行为测试
   - 给定固定输入，验证输出是否符合预期
   - 对抗性测试（恶意输入、畸形数据）
   - 压力测试（高并发任务）

4. 回归测试
   - 历史成功任务的复现
   - 版本升级后的兼容性测试
"""
```

### 8.2 [P1] 配置管理可以更强

**现状**：配置分散在多个文件中。

**优化建议**：使用 Pydantic Settings 统一配置管理

```python
from pydantic_settings import BaseSettings
from pydantic import Field

class RVInsightsSettings(BaseSettings):
    """统一配置类"""
    
    # 数据库
    database_url: str = Field(..., env="DATABASE_URL")
    
    # Redis
    redis_url: str = Field(..., env="REDIS_URL")
    
    # LLM
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    anthropic_api_key: str = Field(..., env="ANTHROPIC_API_KEY")
    litellm_base_url: str = Field("http://localhost:4000", env="LITELLM_BASE_URL")
    
    # 成本限制
    daily_cost_budget: float = Field(100.0, env="DAILY_COST_BUDGET")
    max_tokens_per_call: int = Field(8192, env="MAX_TOKENS_PER_CALL")
    
    # 沙箱
    sandbox_runtime: str = Field("runsc", env="SANDBOX_RUNTIME")
    sandbox_cpu_limit: str = Field("4", env="SANDBOX_CPU_LIMIT")
    sandbox_mem_limit: str = Field("8g", env="SANDBOX_MEM_LIMIT")
    
    # HITL
    hitl_timeout_hours: int = Field(24, env="HITL_TIMEOUT_HOURS")
    hitl_notification_channels: list = Field(["websocket"], env="HITL_CHANNELS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

### 8.3 [P2] 缺少文档自动生成

**现状**：Agent 产出的文档需要人工整理。

**优化建议**：自动生成以下文档
- 变更日志（ChangeLog）
- 技术方案文档
- 测试报告（HTML 格式）
- 贡献指南更新

---

## 总结：优先级排序与实施建议

| 优先级 | 数量 | 关键项 | 预期收益 |
|--------|------|--------|----------|
| **P0** | 6 项 | RAG知识库、反馈闭环、Prompt工程、错误处理、Token优化、分布式事务 | 决定系统能否真正落地运行 |
| **P1** | 16 项 | 上下文链、并发控制、社区集成、模型路由、代码语义分析、Saga事务、Artifact版本、SLA监控 | 决定系统质量和效率上限 |
| **P2** | 11 项 | 多租户、插件系统、数据归档、批量处理、硬件平台DB、决策可解释性 | 决定系统的长期扩展性 |

### 建议实施路线

**v2.1（1 个月）**：完成全部 P0 项 → 系统达到生产可用  
**v2.2（2 个月）**：完成 P1 项中前 8 项 → 系统质量大幅提升  
**v3.0（3-6 个月）**：完成全部 P1 + 核心 P2 项 → 平台化运营

---

*评估报告结束*
