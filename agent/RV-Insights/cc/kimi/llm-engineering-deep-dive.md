# RV-Insights: LLM Engineering & Cost Optimization Deep Dive

**版本**: v1.0
**日期**: 2026-04-21
**目标**: 为 RV-Insights 多 Agent 平台建立生产级的 LLM 工程体系，在确保输出质量的前提下，将 Token 成本降低 40%-60%，并将端到端延迟控制在可接受范围内。

---

## 1. Prompt Engineering Standards

### 1.1 System Prompt Template Library

每个 Agent 角色的 System Prompt 采用**分层模板**设计：基础角色定义 + 领域知识注入 + 动态上下文插槽。

#### Explorer Agent (信息检索)

```markdown
You are {{agent_name}}, an autonomous RISC-V ecosystem intelligence analyst.
Your mission is to scan open-source repositories, mailing lists, and issue trackers to discover actionable contribution opportunities.

## Core Responsibilities
1. Identify unaddressed bugs, missing features, and optimization opportunities specific to RISC-V.
2. Validate all findings against source code and official specifications.
3. Cross-reference multiple data sources to eliminate hallucinations.

## Operational Constraints
- NEVER fabricate issue numbers, commit hashes, or file paths.
- If a source is unreachable, explicitly mark it as UNVERIFIED.
- Prioritize opportunities with evidence from >=2 independent sources.

## Output Format
You MUST respond with a valid JSON object conforming to the `ExplorationResult` schema.
Schema: {{injected_schema}}

## Domain Context (Injected)
{{rag_context}}

## Few-shot Examples (Injected)
{{few_shot_examples}}
```

#### Planner Agent (方案生成)

```markdown
You are {{agent_name}}, a senior RISC-V software architect and project planner.
You transform approved contribution opportunities into rigorous, executable development and testing plans.

## Core Responsibilities
1. Analyze target codebase structure and determine precise modification scope.
2. Produce a Work Breakdown Structure (WBS) with clear dependencies.
3. Design comprehensive test strategies including emulation configs.
4. Identify risks and provide rollback procedures.

## Operational Constraints
- All file paths MUST be relative to the repository root and verified to exist.
- ISA extension dependencies MUST be explicitly stated.
- ABI compliance (calling conventions, struct layout) MUST be considered.

## Output Format
You MUST respond with a valid JSON object conforming to the `PlanningResult` schema.
Schema: {{injected_schema}}

## RISC-V Domain Rules (Injected)
{{riscv_spec_excerpts}}

## Target Repository Conventions (Injected)
{{contributing_guide}}
```

#### Developer Agent (代码实现)

```markdown
You are {{agent_name}}, an expert RISC-V systems developer.
You implement approved plans by producing high-quality, community-compliant code patches.

## Core Responsibilities
1. Follow implementation steps precisely. Do not deviate without explicit reasoning.
2. Adhere to target project coding style (Linux Kernel, QEMU, etc.).
3. Ensure all modifications compile cleanly in the target architecture.
4. Write unit tests where specified in the test plan.

## Operational Constraints
- Prefer immutable changes; avoid mutating existing data structures in-place when possible.
- All inline assembly MUST include comments explaining the RISC-V instruction semantics.
- Memory barriers and atomic operations MUST follow RISC-V weak memory model rules.
- If compilation fails, you have {{max_retries}} self-correction attempts.

## Output Format
You MUST respond with a valid JSON object conforming to the `DevelopmentResult` schema.
Schema: {{injected_schema}}

## Development Plan (Injected)
{{development_plan}}

## Relevant Code Context (Injected)
{{relevant_source_files}}
```

#### Reviewer Agent (代码审核)

```markdown
You are {{agent_name}}, a meticulous RISC-V code reviewer with deep expertise in ISA compliance, security, and performance.
You evaluate code patches against the original development plan and RISC-V specifications.

## Review Dimensions (Weighted)
1. Functional Compliance (High): Does the code accurately implement the plan?
2. RISC-V Spec Compliance (High): Correct instruction usage? ABI adherence?
3. Security (High): Memory safety, concurrency risks, input validation.
4. Code Quality (Medium): Naming, simplicity, style adherence.
5. Performance (Medium): Algorithmic complexity, cache awareness.
6. Test Coverage (Medium): Sufficient tests, boundary conditions.
7. Maintainability (Low): Comments, TODO/FIXME tracking.

## Operational Constraints
- Every CRITICAL or HIGH issue MUST include a concrete fix suggestion with code snippet.
- Cite specific RISC-V spec sections for any ISA-related findings.
- Provide a confidence_score (0.0-1.0) reflecting your certainty.

## Output Format
You MUST respond with a valid JSON object conforming to the `ReviewResult` schema.
Schema: {{injected_schema}}

## Original Plan (Injected)
{{development_plan}}

## Patch Under Review (Injected)
{{patch_diff}}
```

#### Tester Agent (日志分析与测试)

```markdown
You are {{agent_name}}, a RISC-V integration test engineer.
You analyze test logs, emulation outputs, and performance benchmarks to produce a definitive test report.

## Core Responsibilities
1. Parse QEMU logs, build logs, and test suite outputs.
2. Identify root causes of failures (build, runtime, performance regression).
3. Compare results against success criteria from the test plan.

## Operational Constraints
- Do NOT assume a test passed unless the exit code and output explicitly confirm it.
- Flag any emulation warnings (e.g., unimplemented CSR accesses) as potential issues.

## Output Format
You MUST respond with a valid JSON object conforming to the `TestingResult` schema.
Schema: {{injected_schema}}

## Test Plan (Injected)
{{testing_plan}}

## Logs Under Analysis (Injected)
{{test_logs}}
```

### 1.2 Few-shot Example Management

#### Storage & Versioning

Few-shot examples are stored in a dedicated Git-tracked directory:

```
prompts/
  examples/
    explorer/
      v1/
        001_opportunity_discovery.json
        002_cross_validation.json
      v2/
        ...
    developer/
      v1/
        001_kernel_patch.json
        002_qemu_feature.json
```

Each example file follows a standardized format:

```json
{
  "id": "dev-001",
  "version": "v1",
  "tags": ["linux-kernel", "atomic", "memory-barrier"],
  "embedding_model": "text-embedding-3-large",
  "input": { "development_plan": "...", "relevant_source": "..." },
  "output": { "patch_content": "...", "implementation_notes": "..." },
  "quality_score": 0.95,
  "human_verified": true
}
```

#### Dynamic Injection via Vector Retrieval

Before each LLM call, the system retrieves the top-K most relevant few-shot examples:

```python
# Pseudocode for dynamic few-shot injection
async def inject_few_shots(agent_role: str, current_input: str, k: int = 3) -> str:
    query_embedding = await embedding_model.embed(current_input)
    examples = await vector_db.search(
        collection=f"few_shots_{agent_role}",
        vector=query_embedding,
        filter={"human_verified": True, "quality_score": { "$gte": 0.9 }},
        top_k=k
    )
    return format_examples_for_prompt(examples)
```

**Key Rules**:
- Only examples with `quality_score >= 0.9` and `human_verified == true` are eligible.
- Max 3 examples per prompt to avoid excessive token consumption.
- Examples are cached in Redis for 1 hour to reduce embedding costs.

### 1.3 Dynamic Context Compression

When code changes exceed the model's context window (e.g., large kernel patches), the system applies a tiered compression strategy:

#### Tier 1: Semantic Summarization (Lossy)
- **Function bodies** are replaced with docstring-style summaries.
- **Unchanged files** are represented by their path and a one-line description.
- **Import/include blocks** are collapsed into a single line.

#### Tier 2: Diff-of-Diff (Lossless for changes)
- In the Dev-Review iteration loop, the Reviewer Agent receives only the diff between the current patch and the previous iteration, not the full patch.
- Format: `git diff prev_iteration.patch current_iteration.patch`

#### Tier 3: AST Fingerprint Signature
- For caching and deduplication, an AST fingerprint is computed for each file.
- Identical AST fingerprints imply semantically equivalent code, even if formatting differs.

```python
# Pseudocode for AST fingerprinting
import hashlib

def compute_ast_fingerprint(source_code: str, language: str) -> str:
    tree = parse_ast(source_code, language)
    normalized = normalize_ast(tree)  # strip comments, normalize identifiers
    return hashlib.sha256(normalized.encode()).hexdigest()
```

### 1.4 Chain-of-Thought & Structured Output

All Agents are required to output **Chain-of-Thought (CoT)** reasoning before the final JSON payload. This reduces parsing errors and improves reasoning quality.

#### Prompt Template for CoT + JSON

```markdown
Before producing your final answer, think step-by-step inside <thinking> tags.
Analyze the problem, consider edge cases, and explain your reasoning.
After closing the </thinking> tag, output ONLY a valid JSON object.

<thinking>
1. ...
2. ...
</thinking>

```json
{ ... }
```
```

#### Post-processing Pipeline

```python
import json
import re

def extract_json_from_llm_output(raw_output: str) -> dict:
    # Extract content within <thinking> tags (for logging/auditing)
    thinking_match = re.search(r'<thinking>(.*?)</thinking>', raw_output, re.DOTALL)
    thinking = thinking_match.group(1).strip() if thinking_match else ""

    # Extract JSON block
    json_match = re.search(r'```json\s*(.*?)\s*```', raw_output, re.DOTALL)
    if not json_match:
        # Fallback: try to find raw JSON object
        json_match = re.search(r'\{.*\}', raw_output, re.DOTALL)

    if not json_match:
        raise ValueError("No JSON found in LLM output")

    try:
        parsed = json.loads(json_match.group(1))
        return {"thinking": thinking, "data": parsed}
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")
```

### 1.5 Prompt Version Control & A/B Testing Framework

#### Version Control

All prompts are stored in a Git repository with semantic versioning:

```
prompts/
  system/
    explorer/
      v1.0.0.md
      v1.1.0.md
      v2.0.0.md
    developer/
      ...
  schemas/
    exploration_result.json
    planning_result.json
    ...
```

**Change Rules**:
- Patch version (x.y.Z): typo fixes, clarifications.
- Minor version (x.Y.z): new constraints, additional examples.
- Major version (X.y.z): schema changes, output format modifications.

#### A/B Testing

New prompt versions are rolled out via a feature flag system:

```yaml
# config/prompt_ab_tests.yaml
ab_tests:
  - prompt_id: "developer_system_prompt"
    baseline_version: "v1.0.0"
    candidate_version: "v1.1.0"
    traffic_split: 0.1  # 10% traffic to candidate
    success_metric: "review_pass_rate"
    min_samples: 100
    auto_promote: true
```

**Metrics tracked per variant**:
- JSON parse success rate
- Average output token count
- Downstream task success rate (e.g., Reviewer PASS rate for Developer prompts)
- Token cost per successful task

---

## 2. Multi-Model Routing Strategy

### 2.1 Model Selection Matrix

| Agent Role | Primary Model | Fallback Model | Selection Rationale |
|------------|---------------|----------------|---------------------|
| **Explorer** (Info Retrieval) | `claude-3-5-haiku-20241022` | `gpt-4o-mini` | Low-cost, high-speed pattern matching for scanning and summarization. |
| **Planner** (Scheme Generation) | `claude-3-7-sonnet-20250219` | `gpt-4o` | Balanced reasoning and structured output for plan generation. |
| **Developer** (Code Implementation) | `claude-3-7-sonnet-20250219` (Claude Code API) | `codex` | Best-in-class code generation and contextual understanding for large patches. |
| **Reviewer** (Code Review) | `codex` | `claude-3-7-sonnet-20250219` | Deep reasoning for catching subtle bugs and spec violations. |
| **Tester** (Log Analysis) | `claude-3-5-haiku-20241022` | `gpt-4o-mini` | Pattern matching in logs and build outputs; low need for creative generation. |

### 2.2 Dynamic Upgrade Strategy

When a lower-tier model's output confidence is insufficient, the system automatically escalates to a higher-tier model.

#### Confidence Triggers for Upgrade

```python
class ModelRouter:
    UPGRADE_RULES = {
        "explorer": {
            "model": "haiku",
            "upgrade_to": "sonnet",
            "triggers": [
                {"metric": "output_parsing_failed", "action": "immediate_retry"},
                {"metric": "retrieval_relevance_score", "threshold": 0.6, "action": "upgrade"},
            ]
        },
        "reviewer": {
            "model": "codex",
            "upgrade_to": "opus",
            "triggers": [
                {"metric": "confidence_score", "threshold": 0.7, "action": "upgrade"},
                {"metric": "critical_issues_found", "threshold": 5, "action": "upgrade"},
            ]
        }
    }
```

**Upgrade Policy**:
- Max 1 upgrade per task to prevent runaway costs.
- Upgraded tasks are flagged in the cost dashboard for monitoring.
- If the upgraded model also fails, the task is routed to human intervention.

### 2.3 Fallback Mechanism

If the primary model provider is unavailable (rate limit, outage), the system switches to the fallback provider.

```yaml
# config/model_providers.yaml
providers:
  anthropic:
    base_url: "https://api.anthropic.com"
    priority: 1
    models: ["claude-3-7-sonnet", "claude-3-5-haiku", "claude-3-opus"]
  openai:
    base_url: "https://api.openai.com"
    priority: 2
    models: ["gpt-4o", "gpt-4o-mini", "codex"]
  azure_openai:
    base_url: "https://<resource>.openai.azure.com"
    priority: 3
    models: ["gpt-4o"]

fallback:
  enabled: true
  health_check_interval: 30s
  circuit_breaker_threshold: 5  # errors before switching
  cooldown_period: 300s         # seconds before retrying primary
```

**Circuit Breaker Logic**:
- Track error rate per provider per minute.
- If errors exceed threshold, mark provider as `DEGRADED` and route all new requests to next priority.
- Background health checks probe the degraded provider; restore when healthy.

---

## 3. Token Budget & Quota Control

### 3.1 Per-Session Token Budget Pool

Each session is allocated a fixed Token budget, expressed in USD equivalent for human readability.

```typescript
interface SessionBudget {
  session_id: string;
  total_budget_usd: number;      // e.g., 5.00
  total_budget_tokens: number;   // calculated based on current model pricing
  consumed_tokens: number;
  consumed_usd: number;
  currency: "USD";
  hard_limit: boolean;           // if true, halt on exceed; if false, warn
}
```

**Default Budgets by Task Complexity**:

| Task Complexity | Budget (USD) | Budget (Tokens, Sonnet equiv) |
|-----------------|--------------|-------------------------------|
| Quick Exploration | $0.50 | ~500K |
| Standard Contribution | $5.00 | ~5M |
| Deep Architectural Change | $20.00 | ~20M |

### 3.2 Per-Stage Token Quota Allocation

The session budget is subdivided by stage with strict enforcement:

| Stage | Quota % | Purpose |
|-------|---------|---------|
| Exploration | 20% | Multi-agent brainstorming, web search, RAG queries |
| Planning | 15% | SOP-driven structured plan generation |
| Development + Review | 50% | Iterative code generation and review (the most token-intensive phase) |
| Testing | 15% | Log analysis, report compilation |

**Enforcement Logic**:

```python
class TokenQuotaEnforcer:
    def check_quota(self, session_id: str, stage: str, estimated_tokens: int) -> QuotaDecision:
        budget = self.get_session_budget(session_id)
        stage_quota = budget.total_budget_tokens * STAGE_ALLOCATIONS[stage]
        stage_consumed = budget.get_stage_consumed(stage)

        if stage_consumed + estimated_tokens > stage_quota:
            if stage == "development_review":
                # Allow overage up to 10% if close to convergence
                if self.is_near_convergence(session_id):
                    return QuotaDecision.WARN_AND_ALLOW
            return QuotaDecision.REJECT
        return QuotaDecision.ALLOW
```

### 3.3 Real-time Token Consumption Dashboard

A WebSocket channel pushes live token metrics to the frontend.

```typescript
interface TokenMetricsEvent {
  session_id: string;
  timestamp: string;
  stage: string;
  event_type: "llm_call" | "embedding" | "retrieval";
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  cumulative_session_cost: number;
  cumulative_session_tokens: number;
  stage_remaining_quota: number;
}
```

**Frontend Dashboard Elements**:
- Live gauge: Session cost vs. budget.
- Per-stage bar chart: Consumed vs. allocated.
- Cost projection: Estimated total cost based on current burn rate.
- Alert banner: Triggered when any stage exceeds 80% of its quota.

### 3.4 Graceful Degradation on Budget Exhaustion

When a session approaches or exceeds its budget:

1. **80% Warning**: Frontend banner turns yellow; system logs a warning.
2. **95% Critical**: Frontend banner turns red; non-essential Agents (e.g., secondary Explorer sub-agents) are paused.
3. **100% Exhaustion**:
   - All active LLM calls are allowed to complete (to avoid corrupting state).
   - No new LLM calls are initiated.
   - A notification is sent to the human operator via UI and email.
   - The session state is checkpointed and marked as `BUDGET_EXHAUSTED`.
   - Human can approve a budget extension to resume.

---

## 4. Caching & Deduplication Strategy

### 4.1 LLM Result Cache (AST Fingerprint Based)

Identical code review requests are served from cache to avoid redundant LLM calls.

**Cache Key Construction**:

```python
def build_review_cache_key(patch_diff: str, review_config: dict) -> str:
    ast_fp = compute_ast_fingerprint(patch_diff, language="c")
    config_hash = hashlib.sha256(json.dumps(review_config, sort_keys=True).encode()).hexdigest()
    return f"review:{ast_fp}:{config_hash}"
```

**Cache Storage**:
- Backend: Redis with TTL of 7 days.
- Value: Serialized `ReviewResult` JSON.
- Invalidation: Manual or on prompt version change.

### 4.2 RAG Retrieval Result Cache

RISC-V specification queries are cached because the underlying documents change infrequently.

```python
async def cached_rag_query(query: str, knowledge_base: str) -> list[DocumentChunk]:
    cache_key = f"rag:{knowledge_base}:{hashlib.sha256(query.encode()).hexdigest()}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    results = await vector_db.search(query, knowledge_base)
    await redis.setex(cache_key, timedelta(hours=24), json.dumps(results))
    return results
```

### 4.3 Incremental Code Review (Diff-of-Diff)

In the Dev-Review loop, the Reviewer Agent only analyzes the delta between iterations.

```python
def compute_incremental_diff(previous_patch: str, current_patch: str) -> str:
    """
    Returns a minimal diff representing only the changes made in the latest iteration.
    """
    prev_files = parse_patch(previous_patch)
    curr_files = parse_patch(current_patch)

    incremental = {}
    for filepath, curr_content in curr_files.items():
        prev_content = prev_files.get(filepath, "")
        if prev_content != curr_content:
            incremental[filepath] = unified_diff(prev_content, curr_content)

    return format_patch(incremental)
```

**Benefits**:
- Reduces Reviewer input tokens by 60-80% after the first iteration.
- Focuses the model on recent changes, reducing distraction from already-reviewed code.

### 4.4 Embedding Cache

Document chunk embeddings are persisted to avoid recomputation.

```python
class EmbeddingCache:
    def __init__(self, db: AsyncPgStorage):
        self.db = db

    async def get_or_compute(self, chunk_id: str, text: str, model: str) -> list[float]:
        cached = await self.db.fetchrow(
            "SELECT embedding FROM embeddings WHERE chunk_id = $1 AND model = $2",
            chunk_id, model
        )
        if cached:
            return cached["embedding"]

        embedding = await embedding_model.embed(text)
        await self.db.execute(
            "INSERT INTO embeddings (chunk_id, model, embedding) VALUES ($1, $2, $3)",
            chunk_id, model, embedding
        )
        return embedding
```

**Schema**:

```sql
CREATE TABLE embeddings (
    chunk_id TEXT NOT NULL,
    model TEXT NOT NULL,
    embedding VECTOR(3072),  -- pgvector extension
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (chunk_id, model)
);

CREATE INDEX idx_embeddings_model ON embeddings(model);
```

---

## 5. Hallucination Detection & Quality Assurance

### 5.1 Self-Check Confidence Scoring

All Agents are required to include a `confidence_score` (0.0-1.0) in their structured output.

```json
{
  "confidence_score": 0.92,
  "confidence_breakdown": {
    "source_verification": 1.0,
    "cross_reference_check": 0.85,
    "spec_compliance": 0.90
  }
}
```

**Actions based on score**:

| Score Range | Action |
|-------------|--------|
| 0.90 - 1.00 | Accept without additional checks |
| 0.70 - 0.89 | Run secondary verification (e.g., link checker, static analysis) |
| 0.50 - 0.69 | Retry with higher-tier model or expanded context |
| < 0.50 | Reject and escalate to human |

### 5.2 Citation Verification

All factual claims must include source citations. The system validates these automatically.

```python
class CitationVerifier:
    async def verify(self, citations: list[str]) -> VerificationReport:
        results = []
        for url in citations:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.head(url, timeout=10) as resp:
                        results.append({"url": url, "status": resp.status, "reachable": resp.status < 400})
            except Exception as e:
                results.append({"url": url, "status": 0, "reachable": False, "error": str(e)})
        return VerificationReport(results)
```

**Reviewer Agent Prompt Addition**:
```markdown
For every factual claim about RISC-V specifications, Linux kernel behavior, or external libraries,
you MUST provide a source URL. Claims without verifiable sources will be flagged as UNVERIFIED.
```

### 5.3 Consistency Check: Plan vs. Implementation

After the Developer Agent produces a patch, an automated consistency checker compares the implementation against the plan.

```python
class PlanImplementationConsistencyChecker:
    async def check(self, plan: PlanningResult, implementation: DevelopmentResult) -> ConsistencyReport:
        # Use a lightweight LLM call (Haiku) for this check to save costs
        prompt = f"""
        Compare the following Development Plan and Implementation.
        Identify any discrepancies: missing steps, extra changes, or deviations from the plan.
        Plan: {json.dumps(plan)}
        Implementation: {json.dumps(implementation)}
        Output a JSON list of discrepancies.
        """
        response = await llm_router.call("haiku", prompt)
        return ConsistencyReport(discrepancies=response)
```

### 5.4 Automatic Retry with Temperature Variation

On low confidence or parse failure, the system retries with adjusted parameters.

```python
class RetryStrategy:
    TEMPERATURE_SEQUENCE = [0.2, 0.5, 0.8]

    async def execute_with_retry(self, agent_role: str, prompt: str, max_attempts: int = 3):
        for attempt in range(max_attempts):
            try:
                temp = self.TEMPERATURE_SEQUENCE[attempt % len(self.TEMPERATURE_SEQUENCE)]
                response = await llm_router.call(
                    agent_role,
                    prompt,
                    temperature=temp,
                    model_override="sonnet" if attempt > 0 else None  # upgrade on retry
                )
                parsed = extract_json_from_llm_output(response)
                if parsed["data"].get("confidence_score", 0) > 0.7:
                    return parsed
            except (ValueError, LLMError) as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                continue
        raise MaxRetriesExceeded("All retry attempts exhausted")
```

---

## 6. Agent Inter-Communication Protocol

### 6.1 Structured Output Priority

Agents communicate via strictly typed JSON messages to eliminate ambiguity.

#### Message Envelope Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AgentMessage",
  "type": "object",
  "required": ["message_id", "sender", "recipient", "timestamp", "payload_type", "payload"],
  "properties": {
    "message_id": { "type": "string", "format": "uuid" },
    "correlation_id": { "type": "string", "description": "Links related messages in a workflow" },
    "sender": { "type": "string", "enum": ["explorer", "planner", "developer", "reviewer", "tester", "orchestrator", "human"] },
    "recipient": { "type": "string", "enum": ["explorer", "planner", "developer", "reviewer", "tester", "orchestrator", "human", "broadcast"] },
    "timestamp": { "type": "string", "format": "date-time" },
    "payload_type": { "type": "string", "enum": ["task_assignment", "result_delivery", "review_feedback", "human_decisions", "status_update", "error"] },
    "payload": { "type": "object" },
    "metadata": {
      "type": "object",
      "properties": {
        "session_id": { "type": "string" },
        "stage": { "type": "string" },
        "iteration": { "type": "integer" },
        "token_cost": { "type": "number" }
      }
    }
  }
}
```

### 6.2 Natural Language Supplement

Complex reasoning that does not fit into structured fields is appended as an optional `reasoning_log` field, intended for human audit.

```json
{
  "payload": {
    "verdict": "NEEDS_REVISION",
    "issues": [...],
    "reasoning_log": "I flagged issue #3 as CRITICAL because the atomic operation on line 45 lacks a matching fence instruction. In the RISC-V weak memory model, this could lead to observable reordering by other harts. I cross-referenced the RISC-V ISA Manual, Volume I, Chapter 14, which explicitly requires a `fence rw, rw` after atomic SC instructions in this context."
  }
}
```

### 6.3 Message Bus Design: Redis Streams

Redis Streams serves as the asynchronous message bus between Agents.

#### Stream Topology

```
rv:queue:agent_tasks:exploration     # Explorer Agent task queue
rv:queue:agent_tasks:planning        # Planner Agent task queue
rv:queue:agent_tasks:development     # Developer Agent task queue
rv:queue:agent_tasks:review          # Reviewer Agent task queue
rv:queue:agent_tasks:testing         # Tester Agent task queue
rv:queue:human_review:requests       # Human review notifications
rv:queue:human_review:decisions      # Human decisions input
rv:queue:events:audit                # Immutable audit log of all messages
```

#### Producer/Consumer Pattern

```python
import redis.asyncio as redis
import json

class AgentMessageBus:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def publish_task(self, stream: str, message: dict) -> str:
        message_id = await self.redis.xadd(stream, {"payload": json.dumps(message)})
        # Also append to audit log
        await self.redis.xadd("rvinsights:events:audit", {"payload": json.dumps(message)})
        return message_id

    async def consume_tasks(self, stream: str, group: str, consumer: str, count: int = 1):
        messages = await self.redis.xreadgroup(
            groupname=group,
            consumername=consumer,
            streams={stream: ">"},
            count=count,
            block=5000
        )
        return messages

    async def acknowledge(self, stream: str, group: str, message_id: str):
        await self.redis.xack(stream, group, message_id)
```

#### Consumer Groups Configuration

```yaml
redis_streams:
  consumer_groups:
    - stream: "rvinsights:agent:developer:tasks"
      group: "developer-workers"
      consumers: ["dev-1", "dev-2", "dev-3"]
      max_deliveries: 3  # retry count before dead-letter
    - stream: "rvinsights:agent:reviewer:tasks"
      group: "reviewer-workers"
      consumers: ["rev-1", "rev-2"]
      max_deliveries: 3
  dead_letter_stream: "rvinsights:dead:letter"
```

#### Message Flow Example: Dev -> Review Loop

1. **Orchestrator** publishes to `rvinsights:agent:developer:tasks`.
2. **Developer** worker consumes, executes, publishes result to `rvinsights:agent:reviewer:tasks`.
3. **Reviewer** worker consumes, publishes review to `rvinsights:orchestrator:commands`.
4. **Orchestrator** inspects review; if `NEEDS_REVISION`, publishes back to `rvinsights:agent:developer:tasks` with `iteration` incremented.
5. If `MAX_ITERATIONS` reached, publishes to `rvinsights:human:review:requests`.

---

## 7. Implementation Checklist

- [ ] Implement `PromptTemplateRegistry` with versioning and A/B test support.
- [ ] Set up `FewShotVectorStore` with quality gating (`quality_score >= 0.9`).
- [ ] Build `ContextCompressor` with Tier 1/2/3 strategies.
- [ ] Deploy `ModelRouter` with circuit breaker and dynamic upgrade logic.
- [ ] Integrate `TokenQuotaEnforcer` into LangGraph state transitions.
- [ ] Develop real-time Token dashboard WebSocket endpoint.
- [ ] Configure Redis Streams topology and consumer groups.
- [ ] Implement `ASTFingerprint` utility for caching and deduplication.
- [ ] Build `CitationVerifier` with async HTTP head checks.
- [ ] Create `PlanImplementationConsistencyChecker` lightweight validator.
- [ ] Add `RetryStrategy` with temperature variation and model escalation.

---

## 8. Metrics & Success Criteria

| Metric | Baseline | Target |
|--------|----------|--------|
| Avg. Token Cost per Session | $8.00 | $3.50 (-56%) |
| JSON Parse Success Rate | 85% | 98% |
| Reviewer Confidence Score | 0.75 | 0.90 |
| Cache Hit Rate (LLM Results) | 0% | 25% |
| Cache Hit Rate (RAG) | 0% | 60% |
| End-to-End Latency (Standard Task) | 45 min | 25 min |
| Human Escalation Rate | 30% | 15% |

---

*This document is a living specification. All changes must be versioned and reviewed via the Prompt A/B Testing framework defined in Section 1.5.*
