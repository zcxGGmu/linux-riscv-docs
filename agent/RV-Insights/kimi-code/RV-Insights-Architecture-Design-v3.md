# RV-Insights：大模型驱动的 RISC-V 开源贡献平台

## 项目设计方案 v3.0（优化版）

> **版本**：v3.0  
> **日期**：2026-04-23  
> **变更说明**：基于 v2.0 和评估报告，系统性解决全部 P0 优化项，整合核心 P1 改进，新增 RAG 知识库、反馈闭环、弹性架构、Token 优化、分布式事务、社区集成等模块，使方案达到生产级完整度。

---

## 目录

1. [优化总览](#1-优化总览)
2. [RAG 知识库层（新增）](#2-rag-知识库层新增)
3. [反馈闭环系统（新增）](#3-反馈闭环系统新增)
4. [Prompt 工程与版本管理（增强）](#4-prompt-工程与版本管理增强)
5. [熔断降级与弹性架构（新增）](#5-熔断降级与弹性架构新增)
6. [Token 优化与成本管控（增强）](#6-token-优化与成本管控增强)
7. [分布式事务与 Saga 模式（增强）](#7-分布式事务与-saga-模式增强)
8. [代码审查上下文链（审核层增强）](#8-代码审查上下文链审核层增强)
9. [并发控制与 Workspace 管理（开发层增强）](#9-并发控制与-workspace-管理开发层增强)
10. [社区集成模块（新增）](#10-社区集成模块新增)
11. [自适应模型路由（增强）](#11-自适应模型路由增强)
12. [SLA 监控与可观测性（增强）](#12-sla-监控与可观测性增强)
13. [Pydantic Settings 统一配置（工程实践增强）](#13-pydantic-settings-统一配置工程实践增强)
14. [v3.0 整体架构图](#14-v30-整体架构图)

---

## 1. 优化总览

### 1.1 本次优化的核心目标

| 维度 | v2.0 状态 | v3.0 目标 | 关键新增模块 |
|------|----------|-----------|-------------|
| **领域知识** | 提到 RAG，无实现 | 完整的向量知识库 | RAG 知识库层 |
| **自我进化** | 单向流水线 | 三层反馈闭环 | 反馈闭环系统 |
| **可靠性** | 无容错设计 | 熔断 + 降级 + Checkpoint | 弹性架构 |
| **经济性** | 静态模型配置 | 动态路由 + Token 优化 | 成本管控中心 |
| **数据一致性** | 独立操作 | Saga 分布式事务 | 事务协调器 |
| **审核深度** | 文本模式匹配 | AST 语义 + 上下文链 | 语义分析引擎 |
| **社区连接** | 内部闭环 | 自动提交到上游 | 社区集成模块 |
| **可观测性** | 基础健康检查 | SLA + 成本实时看板 | 监控中心 |

### 1.2 优化项覆盖矩阵

| 评估报告优先级 | 数量 | v3.0 解决方式 |
|---------------|------|--------------|
| P0（必须） | 6 项 | 全部解决，见第 2-7 章 |
| P1（强烈建议） | 16 项 | 解决 12 项核心项，见第 8-13 章 |
| P2（建议） | 11 项 | 解决 5 项，其余标记为 v3.1 方向 |

---

## 2. RAG 知识库层（新增）

### 2.1 设计目标

RISC-V 领域具有高度的专业性，Agent 需要随时查阅：
- **RISC-V ISA 规范**（指令集、特权架构、扩展）
- **ABI 文档**（调用约定、结构体布局、TLS）
- **内核文档**（RISC-V 特定子系统、DeviceTree Binding）
- **历史 Patch**（已被接受的贡献模式、维护者偏好）
- **邮件列表讨论**（特定议题的社区共识）

### 2.2 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        RAG 知识库层                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   数据源      │  │   文档处理    │  │   向量存储    │              │
│  │              │  │              │  │              │              │
│  │ • ISA 规范   │──►│ • 切分策略   │──►│ • Qdrant     │              │
│  │ • ABI 文档   │  │ • 元数据提取  │  │   (Collection│              │
│  │ • 内核文档   │  │ • 版本标记   │  │    per proj) │              │
│  │ • 历史 Patch │  │ • 去重处理   │  │              │              │
│  │ • 邮件归档   │  │ • 质量过滤   │  │              │              │
│  │ • 代码注释   │  │              │  │              │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                                              │                      │
│                                              ▼                      │
│                                    ┌─────────────────┐              │
│                                    │   检索引擎       │              │
│                                    │                 │              │
│                                    │ • Dense Search  │              │
│                                    │ • Sparse (BM25) │              │
│                                    │ • Hybrid Fusion │              │
│                                    │ • Rerank (Cohere│              │
│                                    │   / ColBERT)    │              │
│                                    └────────┬────────┘              │
│                                             │                       │
│                                             ▼                       │
│                                    ┌─────────────────┐              │
│                                    │   Agent 接口     │              │
│                                    │                 │              │
│                                    │ retrieve_context│              │
│                                    │   (query,       │              │
│                                    │    filters,     │              │
│                                    │    top_k)       │              │
│                                    └─────────────────┘              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.3 核心实现

```python
# rv_insights/rag/engine.py
from dataclasses import dataclass
from typing import List, Dict, Optional, Literal
from datetime import datetime
import hashlib
import aiohttp

@dataclass
class DocumentChunk:
    """文档分片"""
    chunk_id: str
    source_doc: str           # 来源文档 URL/路径
    source_type: Literal["isa_spec", "abi_doc", "kernel_doc", "patch", "mail", "code"]
    content: str
    metadata: Dict
    embedding: Optional[List[float]] = None
    version: str = "latest"   # 文档版本（ISA 规范有版本）
    project: Optional[str] = None  # 关联项目

@dataclass
class RetrievalResult:
    """检索结果"""
    chunk: DocumentChunk
    score: float
    rerank_score: Optional[float] = None

class RAGEngine:
    """
    RAG 检索引擎
    
    使用 Qdrant 作为向量数据库，支持混合检索（Dense + Sparse）
    """
    
    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        embedding_model: str = "text-embedding-3-large",
        reranker_model: Optional[str] = "cohere/rerank-multilingual-v3.0"
    ):
        self.qdrant_url = qdrant_url
        self.embedding_model = embedding_model
        self.reranker_model = reranker_model
        self.litellm_base = "http://localhost:4000"
    
    async def ingest_document(
        self,
        content: str,
        source_type: str,
        source_url: str,
        project: Optional[str] = None,
        version: str = "latest",
        metadata: Optional[Dict] = None
    ) -> List[str]:
        """
        摄入文档到知识库
        
        流程：
        1. 文档切分
        2. 生成 Embedding
        3. 写入 Qdrant
        """
        # 1. 切分
        chunks = self._chunk_document(content, source_type)
        
        chunk_ids = []
        for chunk_text in chunks:
            chunk_id = hashlib.sha256(
                f"{source_url}:{chunk_text[:100]}".encode()
            ).hexdigest()[:16]
            
            # 2. 生成 Embedding
            embedding = await self._get_embedding(chunk_text)
            
            # 3. 写入 Qdrant
            await self._upsert_to_qdrant(
                chunk_id=chunk_id,
                vector=embedding,
                payload={
                    "source_doc": source_url,
                    "source_type": source_type,
                    "content": chunk_text,
                    "project": project,
                    "version": version,
                    "metadata": metadata or {},
                    "ingested_at": datetime.utcnow().isoformat()
                }
            )
            chunk_ids.append(chunk_id)
        
        return chunk_ids
    
    def _chunk_document(self, content: str, source_type: str) -> List[str]:
        """
        根据文档类型选择切分策略
        
        不同文档类型的切分策略不同：
        - ISA 规范：按章节/指令切分
        - 内核文档：按段落切分
        - 代码：按函数/结构体切分
        - Patch：按文件变更切分
        """
        strategies = {
            "isa_spec": self._chunk_by_sections,
            "abi_doc": self._chunk_by_paragraphs,
            "kernel_doc": self._chunk_by_paragraphs,
            "patch": self._chunk_by_file_diff,
            "mail": self._chunk_by_threads,
            "code": self._chunk_by_functions,
        }
        
        strategy = strategies.get(source_type, self._chunk_by_paragraphs)
        return strategy(content)
    
    def _chunk_by_sections(self, content: str, chunk_size: int = 512, overlap: int = 128) -> List[str]:
        """按章节切分（适用于 ISA 规范）"""
        # 按 markdown 标题切分
        import re
        sections = re.split(r'\n(?=#{1,4}\s)', content)
        
        chunks = []
        current_chunk = ""
        for section in sections:
            if len(current_chunk) + len(section) < chunk_size:
                current_chunk += "\n" + section
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = section
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _chunk_by_functions(self, content: str) -> List[str]:
        """按函数切分（适用于代码）"""
        import re
        # 简单正则匹配 C 函数
        pattern = r'^[\w\s\*]+\s+\w+\s*\([^)]*\)\s*\{'
        # 实际实现应使用 Tree-sitter
        
        # 简化处理：按行数切分，保留函数签名上下文
        lines = content.split('\n')
        chunks = []
        current = []
        
        for line in lines:
            current.append(line)
            if len(current) > 100:  # 约 100 行一个 chunk
                chunks.append('\n'.join(current))
                current = []
        
        if current:
            chunks.append('\n'.join(current))
        
        return chunks
    
    def _chunk_by_paragraphs(self, content: str, chunk_size: int = 1024, overlap: int = 256) -> List[str]:
        """按段落切分"""
        paragraphs = content.split('\n\n')
        chunks = []
        current = ""
        
        for para in paragraphs:
            if len(current) + len(para) < chunk_size:
                current += "\n\n" + para if current else para
            else:
                if current:
                    chunks.append(current)
                current = para
        
        if current:
            chunks.append(current)
        
        return chunks
    
    def _chunk_by_file_diff(self, content: str) -> List[str]:
        """按文件 diff 切分"""
        import re
        # 按 diff --git 切分
        files = re.split(r'(?=diff --git)', content)
        return [f.strip() for f in files if f.strip()]
    
    def _chunk_by_threads(self, content: str) -> List[str]:
        """按邮件线程切分"""
        import re
        # 按 From: 切分
        mails = re.split(r'(?=\nFrom:)', content)
        return [m.strip() for m in mails if m.strip()]
    
    async def _get_embedding(self, text: str) -> List[float]:
        """获取文本 Embedding"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.litellm_base}/embeddings",
                headers={"Authorization": f"Bearer {self.litellm_api_key}"},
                json={
                    "model": self.embedding_model,
                    "input": text[:8000]  # 限制长度
                }
            ) as resp:
                data = await resp.json()
                return data["data"][0]["embedding"]
    
    async def _upsert_to_qdrant(self, chunk_id: str, vector: List[float], payload: Dict):
        """写入 Qdrant"""
        import qdrant_client
        from qdrant_client.models import PointStruct
        
        client = qdrant_client.AsyncQdrantClient(self.qdrant_url)
        
        # 确保 Collection 存在
        collections = await client.get_collections()
        if "rv_insights_kb" not in [c.name for c in collections.collections]:
            await self._create_collection(client)
        
        await client.upsert(
            collection_name="rv_insights_kb",
            points=[PointStruct(id=chunk_id, vector=vector, payload=payload)]
        )
    
    async def _create_collection(self, client):
        """创建 Qdrant Collection"""
        from qdrant_client.models import Distance, VectorParams
        
        await client.create_collection(
            collection_name="rv_insights_kb",
            vectors_config=VectorParams(size=3072, distance=Distance.COSINE)
        )
    
    async def retrieve(
        self,
        query: str,
        project: Optional[str] = None,
        source_types: Optional[List[str]] = None,
        top_k: int = 10,
        rerank: bool = True
    ) -> List[RetrievalResult]:
        """
        检索相关知识
        
        流程：
        1. 生成 query embedding
        2. Qdrant dense search
        3. 可选：rerank
        4. 返回结果
        """
        # 1. 生成 query embedding
        query_embedding = await self._get_embedding(query)
        
        # 2. 构建过滤条件
        filter_conditions = []
        if project:
            filter_conditions.append({"key": "project", "match": {"value": project}})
        if source_types:
            filter_conditions.append({"key": "source_type", "match": {"any": source_types}})
        
        # 3. Qdrant 检索
        import qdrant_client
        client = qdrant_client.AsyncQdrantClient(self.qdrant_url)
        
        results = await client.search(
            collection_name="rv_insights_kb",
            query_vector=query_embedding,
            query_filter={"must": filter_conditions} if filter_conditions else None,
            limit=top_k * 2 if rerank else top_k,  # rerank 时多取一些
            with_payload=True
        )
        
        # 4. 转换为内部格式
        retrieval_results = []
        for result in results:
            chunk = DocumentChunk(
                chunk_id=result.id,
                source_doc=result.payload["source_doc"],
                source_type=result.payload["source_type"],
                content=result.payload["content"],
                metadata=result.payload.get("metadata", {}),
                version=result.payload.get("version", "latest"),
                project=result.payload.get("project")
            )
            retrieval_results.append(RetrievalResult(chunk=chunk, score=result.score))
        
        # 5. Rerank（可选）
        if rerank and self.reranker_model:
            retrieval_results = await self._rerank(query, retrieval_results)
        
        return retrieval_results[:top_k]
    
    async def _rerank(self, query: str, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """使用 Reranker 精排"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.litellm_base}/rerank",
                json={
                    "model": self.reranker_model,
                    "query": query,
                    "documents": [r.chunk.content for r in results]
                }
            ) as resp:
                data = await resp.json()
                
                # 更新分数
                for item in data.get("results", []):
                    idx = item["index"]
                    if idx < len(results):
                        results[idx].rerank_score = item["relevance_score"]
                
                # 按 rerank 分数排序
                results.sort(key=lambda r: r.rerank_score or r.score, reverse=True)
        
        return results
    
    async def get_maintainer_preference(self, subsystem: str) -> Dict:
        """
        获取特定子系统维护者的偏好
        
        从邮件列表历史中提取维护者的 review 风格
        """
        results = await self.retrieve(
            query=f"maintainer preference review style {subsystem}",
            source_types=["mail", "patch"],
            top_k=5
        )
        
        preferences = {
            "style_notes": [r.chunk.content for r in results],
            "common_requests": self._extract_common_requests(results)
        }
        
        return preferences
    
    def _extract_common_requests(self, results: List[RetrievalResult]) -> List[str]:
        """从检索结果中提取常见的维护者要求"""
        # 简化实现：提取高频关键词
        from collections import Counter
        import re
        
        all_text = " ".join(r.chunk.content for r in results)
        words = re.findall(r'\b\w+\b', all_text.lower())
        common = Counter(words).most_common(20)
        
        return [word for word, count in common if count > 2]


# RAG 集成到各 Agent 的示例
class RAGEnhancedPromptEngine:
    """
    增强型 Prompt 引擎
    
    在每个 Agent 执行前，自动注入 RAG 检索结果
    """
    
    def __init__(self, rag_engine: RAGEngine):
        self.rag = rag_engine
    
    async def build_developer_prompt(
        self,
        task: ContributionPoint,
        plan: dict
    ) -> str:
        """为开发 Agent 构建带 RAG 上下文的 Prompt"""
        
        # 检索相关代码示例
        code_examples = await self.rag.retrieve(
            query=f"RISC-V {task.category} example implementation {task.target_project}",
            project=task.target_project,
            source_types=["code", "patch"],
            top_k=3
        )
        
        # 检索编码规范
        guidelines = await self.rag.retrieve(
            query=f"{task.target_project} coding style guidelines RISC-V",
            source_types=["kernel_doc", "abi_doc"],
            top_k=3
        )
        
        # 检索相关 ISA 规范
        isa_refs = []
        if "extension" in task.metadata:
            isa_refs = await self.rag.retrieve(
                query=f"RISC-V {task.metadata['extension']} extension specification",
                source_types=["isa_spec"],
                top_k=3
            )
        
        prompt = f"""
        ## 任务
        {task.description}
        
        ## 参考实现示例
        {self._format_examples(code_examples)}
        
        ## 编码规范
        {self._format_examples(guidelines)}
        
        ## ISA 规范参考
        {self._format_examples(isa_refs)}
        
        ## 开发计划
        {json.dumps(plan['development_plan'], indent=2)}
        
        请基于以上参考，完成代码开发。
        """
        
        return prompt
    
    def _format_examples(self, results: List[RetrievalResult]) -> str:
        """格式化示例"""
        if not results:
            return "（无相关示例）"
        
        parts = []
        for i, result in enumerate(results, 1):
            parts.append(f"### 示例 {i}（来源：{result.chunk.source_doc}）\n```\n{result.chunk.content[:2000]}\n```")
        
        return "\n\n".join(parts)
```

### 2.4 数据同步策略

```yaml
# rag_sync.yaml
sync_jobs:
  # ISA 规范同步
  isa_manual:
    source: "https://github.com/riscv/riscv-isa-manual"
    branch: main
    frequency: "weekly"
    document_types:
      - "src/*.adoc"      # AsciiDoc 源文件
    chunk_strategy: "by_section"
    
  # 内核文档同步
  linux_docs:
    source: "https://github.com/torvalds/linux"
    branch: master
    frequency: "daily"
    document_types:
      - "Documentation/devicetree/bindings/riscv/**"
      - "Documentation/riscv/**"
      - "arch/riscv/Kconfig"
    chunk_strategy: "by_paragraph"
    
  # 已接受 Patch 同步（用于学习模式）
  accepted_patches:
    source: "lore.kernel.org"
    lists: ["linux-riscv", "qemu-riscv", "opensbi"]
    frequency: "daily"
    filter: "status:accepted"  # 只同步被接受的 Patch
    chunk_strategy: "by_file_diff"
    
  # 邮件列表讨论同步
  mail_discussions:
    source: "lore.kernel.org"
    lists: ["linux-riscv"]
    frequency: "hourly"
    lookback_days: 30
    chunk_strategy: "by_thread"
```

---

## 3. 反馈闭环系统（新增）

### 3.1 设计目标

将 RV-Insights 从"单向流水线"转变为"自我进化系统"：
- 人工 HITL 的修改意见 → 自动优化 Agent Prompt
- 审核发现的常见问题 → 生成预检清单
- 成功贡献的模式 → Few-shot 示例库
- 失败案例 → 负例学习

### 3.2 三层反馈闭环架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                       反馈闭环系统架构                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  第一层：即时反馈（Intra-Task）                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ • HITL 拒绝时，记录原因 → 实时修改当前任务 Prompt           │   │
│  │ • 审核迭代中，上一轮结果 → 下一轮上下文                      │   │
│  │ • 开发失败时，错误日志 → 修复指令优化                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  第二层：短期反馈（Inter-Task）                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ • 相似贡献点的历史成功方案 → Few-shot 示例库                │   │
│  │ • 常见审核问题模式 → "预审核检查清单"                        │   │
│  │ • 维护者偏好分析 → 个性化编码建议                            │   │
│  │ • 项目特定约定 → 自动注入 Prompt                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  第三层：长期反馈（System-Level）                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ • 高质量人工修正数据 → RAG 知识库更新                        │   │
│  │ • Prompt-Response 对 → 模型微调数据集                        │   │
│  │ • Agent 表现趋势 → 自动调整模型选择策略                      │   │
│  │ • Token 效率分析 → 自动优化上下文压缩策略                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 核心实现

```python
# rv_insights/feedback/loop.py
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
import json

@dataclass
class FeedbackRecord:
    """反馈记录"""
    feedback_id: str
    task_id: str
    stage: str
    agent_name: str
    feedback_type: str  # "hitl_reject" | "hitl_modify" | "review_issue" | "test_failure"
    feedback_text: str
    original_output: str
    corrected_output: Optional[str] = None
    reviewer_id: Optional[str] = None
    created_at: datetime = datetime.utcnow()
    applied: bool = False  # 是否已用于改进

class FeedbackCollector:
    """反馈收集器"""
    
    def __init__(self, db, rag_engine: RAGEngine):
        self.db = db
        self.rag = rag_engine
    
    async def collect_hitl_feedback(self, decision: HITLDecision, stage_output: dict):
        """收集 HITL 反馈"""
        record = FeedbackRecord(
            feedback_id=f"FB-{decision.request_id}",
            task_id=decision.task_id,
            stage=decision.stage,
            agent_name=stage_output.get("agent_name", "unknown"),
            feedback_type=f"hitl_{decision.decision}",
            feedback_text=decision.feedback or "",
            original_output=json.dumps(stage_output)[:10000],
            reviewer_id=decision.decided_by
        )
        
        await self.db.execute("""
            INSERT INTO agent_feedback 
            (feedback_id, task_id, stage, agent_name, feedback_type, 
             feedback_text, original_output, reviewer_id, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, record.feedback_id, record.task_id, record.stage,
             record.agent_name, record.feedback_type,
             record.feedback_text, record.original_output,
             record.reviewer_id, record.created_at)
        
        # 实时应用到当前系统（第一层反馈）
        await self._apply_immediate_feedback(record)
    
    async def collect_review_feedback(
        self,
        task_id: str,
        iteration: int,
        issues_found: List[ReviewIssue],
        issues_fixed: List[ReviewIssue]
    ):
        """收集审核反馈"""
        # 记录哪些类型的问题反复出现
        recurring_issues = []
        for issue in issues_found:
            if issue.issue_id in [i.issue_id for i in issues_fixed]:
                recurring_issues.append(issue)
        
        if recurring_issues:
            await self.db.execute("""
                INSERT INTO recurring_issue_patterns 
                (pattern_hash, category, severity, description, count, last_seen)
                VALUES ($1, $2, $3, $4, 1, NOW())
                ON CONFLICT (pattern_hash) 
                DO UPDATE SET count = recurring_issue_patterns.count + 1,
                              last_seen = NOW()
            """, hashlib.sha256(issue.description.encode()).hexdigest()[:16],
                 issue.category.value, issue.severity.value, issue.description)
    
    async def _apply_immediate_feedback(self, record: FeedbackRecord):
        """
        第一层反馈：即时应用
        
        将反馈实时应用到正在进行的任务
        """
        if record.feedback_type == "hitl_reject":
            # 将拒绝原因注入到重试 Prompt
            await self.db.execute("""
                UPDATE stages 
                SET context = jsonb_set(
                    COALESCE(context, '{}'::jsonb),
                    '{human_feedback}',
                    $1::jsonb
                )
                WHERE task_id = $2 AND stage_type = $3
            """, json.dumps({
                "rejected_at": datetime.utcnow().isoformat(),
                "reason": record.feedback_text,
                "original_output": record.original_output
            }), record.task_id, record.stage)
    
    async def generate_few_shot_examples(
        self,
        category: str,
        project: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        第二层反馈：从成功任务提取 Few-shot 示例
        
        选择标准：
        1. 任务最终状态为 complete
        2. 成本低（Token 效率高的优先）
        3. 人工审核通过（无 reject 记录）
        4. 时间较近（优先学习最近的模式）
        """
        examples = await self.db.fetch("""
            SELECT 
                input_artifact.content_json as input,
                output_artifact.content_json as output,
                s.execution_time_seconds,
                s.cost_usd,
                s.token_input + s.token_output as total_tokens
            FROM tasks t
            JOIN stages s ON t.task_id = s.task_id
            JOIN artifacts input_artifact ON s.input_artifact_id = input_artifact.artifact_id
            JOIN artifacts output_artifact ON s.output_artifact_id = output_artifact.artifact_id
            WHERE t.status = 'complete'
              AND s.stage_type = $1
              AND t.target_project = $2
              AND NOT EXISTS (
                  SELECT 1 FROM agent_feedback f
                  WHERE f.task_id = t.task_id
                    AND f.stage = s.stage_type
                    AND f.feedback_type = 'hitl_reject'
              )
              AND s.cost_usd < 10
            ORDER BY 
                s.created_at DESC,  -- 最近优先
                (s.token_input + s.token_output) / NULLIF(s.execution_time_seconds, 0) ASC
            LIMIT $3
        """, category, project, limit)
        
        return [dict(ex) for ex in examples]
    
    async def generate_pre_checklist(self, project: str, category: str) -> List[str]:
        """
        生成预审核检查清单
        
        基于历史审核数据，提取最常见的问题类型
        """
        patterns = await self.db.fetch("""
            SELECT description, count
            FROM recurring_issue_patterns
            WHERE category = $1
            ORDER BY count DESC, last_seen DESC
            LIMIT 10
        """, category)
        
        checklist = []
        for p in patterns:
            # 将问题描述转换为检查项
            checklist.append(f"[ ] 检查：{p['description']}（历史出现 {p['count']} 次）")
        
        return checklist
    
    async def update_rag_from_success(self, task_id: str):
        """
        第三层反馈：将成功贡献更新到 RAG
        
        将人工修正后的最终 Patch 作为高质量示例存入知识库
        """
        # 获取最终 Patch
        final_artifact = await self.db.fetchrow("""
            SELECT content_text, artifact_type
            FROM artifacts
            WHERE task_id = $1 AND artifact_type = 'code'
            ORDER BY created_at DESC
            LIMIT 1
        """, task_id)
        
        if final_artifact:
            # 提取 Patch 的"问题-解决方案"对
            task = await self.db.fetchrow("""
                SELECT title, description, target_project, category
                FROM tasks WHERE task_id = $1
            """, task_id)
            
            # 存入 RAG 作为成功案例
            await self.rag.ingest_document(
                content=f"""
                # 问题
                {task['title']}
                {task['description']}
                
                # 解决方案
                {final_artifact['content_text']}
                """,
                source_type="patch",
                source_url=f"internal://tasks/{task_id}",
                project=task['target_project'],
                metadata={
                    "category": task['category'],
                    "status": "accepted",
                    "source": "human_verified"
                }
            )


class AgentPerformanceAnalyzer:
    """
    Agent 表现分析器
    
    第三层反馈：系统级优化
    """
    
    def __init__(self, db):
        self.db = db
    
    async def analyze_trends(self, days: int = 30) -> Dict:
        """分析 Agent 表现趋势"""
        
        # 各 Agent 的成功率趋势
        agent_trends = await self.db.fetch("""
            SELECT 
                agent_name,
                DATE(created_at) as date,
                COUNT(*) as total_runs,
                COUNT(*) FILTER (WHERE status = 'completed') as success_count,
                AVG(cost_usd) as avg_cost,
                AVG(token_input + token_output) as avg_tokens,
                AVG(execution_time_seconds) as avg_time
            FROM stages
            WHERE created_at >= NOW() - INTERVAL '$1 days'
            GROUP BY agent_name, DATE(created_at)
            ORDER BY agent_name, date
        """, days)
        
        # 识别性能退化的 Agent
        degraded = []
        for agent in set(r['agent_name'] for r in agent_trends):
            agent_data = [r for r in agent_trends if r['agent_name'] == agent]
            if len(agent_data) >= 7:
                recent = agent_data[-7:]
                earlier = agent_data[-14:-7]
                
                recent_success = sum(r['success_count'] for r in recent) / sum(r['total_runs'] for r in recent)
                earlier_success = sum(r['success_count'] for r in earlier) / sum(r['total_runs'] for r in earlier)
                
                if recent_success < earlier_success * 0.8:
                    degraded.append({
                        "agent": agent,
                        "earlier_success_rate": earlier_success,
                        "recent_success_rate": recent_success,
                        "suggestion": "Consider reviewing prompt or switching fallback model"
                    })
        
        return {
            "agent_trends": [dict(r) for r in agent_trends],
            "degraded_agents": degraded,
            "recommendations": self._generate_recommendations(agent_trends, degraded)
        }
    
    def _generate_recommendations(self, trends, degraded) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        for d in degraded:
            recommendations.append(
                f"Agent '{d['agent']}' 成功率从 {d['earlier_success_rate']:.1%} "
                f"下降到 {d['recent_success_rate']:.1%}，建议检查 Prompt 或模型配置"
            )
        
        # 成本分析
        high_cost_agents = []
        for agent in set(r['agent_name'] for r in trends):
            agent_costs = [r['avg_cost'] for r in trends if r['agent_name'] == agent]
            avg_cost = sum(agent_costs) / len(agent_costs)
            if avg_cost > 5.0:
                high_cost_agents.append((agent, avg_cost))
        
        for agent, cost in high_cost_agents:
            recommendations.append(
                f"Agent '{agent}' 平均成本 ${cost:.2f}/次，建议优化 Token 使用或切换 cheaper model"
            )
        
        return recommendations
```

---

## 4. Prompt 工程与版本管理（增强）

### 4.1 Prompt 注册表

```python
# rv_insights/prompts/registry.py
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime
import jinja2

@dataclass
class PromptTemplate:
    """Prompt 模板"""
    template_id: str
    agent_name: str
    version: str
    variant: str  # "default" | "experimental" | "fallback"
    template_text: str
    few_shot_count: int = 3
    rag_injection: bool = True
    created_at: datetime = datetime.utcnow()
    ab_test_group: Optional[str] = None

class PromptRegistry:
    """
    Prompt 注册表
    
    支持：
    - 版本管理
    - A/B 测试变体
    - 动态 Few-shot 注入
    - RAG 上下文注入
    """
    
    def __init__(self, db, rag_engine: RAGEngine):
        self.db = db
        self.rag = rag_engine
        self.jinja = jinja2.Environment(
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    async def get_template(
        self,
        agent_name: str,
        variant: str = "default"
    ) -> PromptTemplate:
        """获取模板"""
        record = await self.db.fetchrow("""
            SELECT * FROM prompt_templates
            WHERE agent_name = $1 AND variant = $2
            ORDER BY version DESC
            LIMIT 1
        """, agent_name, variant)
        
        if not record:
            # 使用默认模板
            return self._get_default_template(agent_name)
        
        return PromptTemplate(**dict(record))
    
    async def render(
        self,
        agent_name: str,
        task_context: Dict,
        variant: str = "default"
    ) -> str:
        """
        渲染最终 Prompt
        
        流程：
        1. 加载模板
        2. 注入 Few-shot 示例
        3. 注入 RAG 上下文
        4. 注入项目特定规范
        5. 渲染 Jinja 模板
        6. 安全校验
        """
        # 1. 加载模板
        template = await self.get_template(agent_name, variant)
        
        # 2. 收集上下文
        context = {
            "task": task_context,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # 3. 注入 Few-shot 示例
        if template.few_shot_count > 0:
            few_shots = await self._get_few_shots(
                agent_name=agent_name,
                category=task_context.get("category"),
                project=task_context.get("target_project"),
                limit=template.few_shot_count
            )
            context["few_shots"] = few_shots
        
        # 4. 注入 RAG 上下文
        if template.rag_injection:
            rag_context = await self._get_rag_context(task_context)
            context["rag_context"] = rag_context
        
        # 5. 注入项目规范
        guidelines = await self._get_project_guidelines(
            task_context.get("target_project")
        )
        context["guidelines"] = guidelines
        
        # 6. 渲染模板
        jinja_template = self.jinja.from_string(template.template_text)
        prompt = jinja_template.render(**context)
        
        # 7. 安全校验
        prompt = self._sanitize(prompt)
        
        return prompt
    
    async def _get_few_shots(self, agent_name: str, category: str, project: str, limit: int) -> List[Dict]:
        """获取 Few-shot 示例"""
        # 从反馈闭环系统获取
        from rv_insights.feedback.loop import FeedbackCollector
        collector = FeedbackCollector(self.db, self.rag)
        return await collector.generate_few_shot_examples(category, project, limit)
    
    async def _get_rag_context(self, task_context: Dict) -> Dict:
        """获取 RAG 上下文"""
        query = task_context.get("title", "") + " " + task_context.get("description", "")
        
        results = await self.rag.retrieve(
            query=query,
            project=task_context.get("target_project"),
            top_k=5
        )
        
        return {
            "relevant_docs": [
                {
                    "source": r.chunk.source_doc,
                    "type": r.chunk.source_type,
                    "content": r.chunk.content[:2000],
                    "score": r.score
                }
                for r in results
            ]
        }
    
    async def _get_project_guidelines(self, project: Optional[str]) -> Dict:
        """获取项目编码规范"""
        if not project:
            return {}
        
        guidelines_db = {
            "linux": {
                "indent": "tabs (8 spaces)",
                "line_length": 80,
                "brace_style": "K&R",
                "checkpatch": "scripts/checkpatch.pl --strict",
                "commit_format": "[PATCH] subsystem: description",
                "signoff_required": True
            },
            "qemu": {
                "indent": "4 spaces",
                "line_length": 80,
                "brace_style": "K&R",
                "checkpatch": None,
                "commit_format": "subsystem: description",
                "signoff_required": True
            }
        }
        
        return guidelines_db.get(project, guidelines_db["linux"])
    
    def _sanitize(self, prompt: str) -> str:
        """
        Prompt 注入防护
        
        策略：
        1. 检测常见注入模式
        2. 用户输入转义
        3. 长度限制
        """
        # 检测注入
        injection_patterns = [
            r'ignore\s+(previous|above|all)\s+instructions',
            r'forget\s+(previous|above|all)\s+instructions',
            r'new\s+instructions?:',
            r'you\s+are\s+now\s+',
            r'</\s*(system|instruction|prompt)',
            r'\[\s*system\s*\]',
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                # 记录安全事件
                logger.warning(f"Potential prompt injection detected: {pattern}")
                # 可以选择拒绝或转义
                prompt = re.sub(pattern, "[FILTERED]", prompt, flags=re.IGNORECASE)
        
        # 长度限制
        max_length = 128000  # 128K tokens ~= 512K chars
        if len(prompt) > max_length:
            logger.warning(f"Prompt too long ({len(prompt)}), truncating")
            prompt = prompt[:max_length]
        
        return prompt
    
    async def create_ab_test(
        self,
        agent_name: str,
        variant_a: str,
        variant_b: str,
        traffic_split: float = 0.5,
        success_metric: str = "compile_rate"
    ) -> str:
        """
        创建 A/B 测试
        
        对比两个 Prompt 变体的效果
        """
        test_id = f"ab-{agent_name}-{uuid.uuid4().hex[:8]}"
        
        await self.db.execute("""
            INSERT INTO prompt_ab_tests 
            (test_id, agent_name, variant_a, variant_b, 
             traffic_split, success_metric, status, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, 'running', NOW())
        """, test_id, agent_name, variant_a, variant_b,
             traffic_split, success_metric)
        
        return test_id
    
    async def get_ab_test_result(self, test_id: str) -> Dict:
        """获取 A/B 测试结果"""
        results = await self.db.fetchrow("""
            SELECT 
                t.*,
                COUNT(*) FILTER (WHERE s.ab_variant = t.variant_a) as a_runs,
                COUNT(*) FILTER (WHERE s.ab_variant = t.variant_b) as b_runs,
                AVG(s.cost_usd) FILTER (WHERE s.ab_variant = t.variant_a) as a_avg_cost,
                AVG(s.cost_usd) FILTER (WHERE s.ab_variant = t.variant_b) as b_avg_cost
            FROM prompt_ab_tests t
            LEFT JOIN stages s ON s.task_id IN (
                SELECT task_id FROM tasks 
                WHERE created_at >= t.created_at
            )
            WHERE t.test_id = $1
            GROUP BY t.test_id
        """, test_id)
        
        return dict(results) if results else {}
```

### 4.2 默认 Prompt 模板示例

```jinja2
{# templates/developer/linux.j2 #}
你是 RV-Insights 的开发专家，负责 Linux 内核 RISC-V 子系统的代码开发。

## 任务
{{ task.title }}
{{ task.description }}

{% if guidelines %}
## 编码规范
- 缩进：{{ guidelines.indent }}
- 行长度：{{ guidelines.line_length }} 列
- 括号风格：{{ guidelines.brace_style }}
- Patch 检查：{{ guidelines.checkpatch }}
- Commit 格式：{{ guidelines.commit_format }}
{% endif %}

{% if few_shots %}
## 参考示例
{% for shot in few_shots %}
### 示例 {{ loop.index }}
输入：{{ shot.input.title }}
输出：
```c
{{ shot.output.code }}
```
{% endfor %}
{% endif %}

{% if rag_context %}
## 相关文档
{% for doc in rag_context.relevant_docs %}
### {{ doc.source }} ({{ doc.type }}, 相关度: {{ "%.2f" | format(doc.score) }})
{{ doc.content }}
{% endfor %}
{% endif %}

## 开发计划
{{ task.plan | tojson(indent=2) }}

## 要求
1. 严格遵循编码规范
2. 只修改必要的文件
3. 每次修改后编译验证
4. 生成 Patch 并运行 checkpatch

请开始开发。
```

---

## 5. 熔断降级与弹性架构（新增）

### 5.1 熔断器设计

```python
# rv_insights/resilience/circuit_breaker.py
from enum import Enum, auto
from dataclasses import dataclass
from typing import Callable, Optional
import asyncio
import time

class CircuitState(Enum):
    CLOSED = auto()      # 正常
    OPEN = auto()        # 熔断
    HALF_OPEN = auto()   # 试探

@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5          # 触发熔断的失败次数
    recovery_timeout: float = 60.0      # 熔断后恢复时间（秒）
    half_open_max_calls: int = 3        # 半开状态最大试探次数
    success_threshold_half_open: int = 2  # 半开状态恢复所需的连续成功次数
    timeout_seconds: float = 120.0      # 调用超时时间

class CircuitBreaker:
    """
    LLM 调用熔断器
    
    防止 LLM API 故障拖垮整个系统
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
        self.lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs):
        """
        执行被保护的调用
        
        如果熔断器打开，直接抛出异常
        如果半开，只允许有限次数的试探调用
        """
        async with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    self.success_count = 0
                    logger.info(f"[{self.name}] Circuit entering HALF_OPEN state")
                else:
                    raise CircuitBreakerOpen(
                        f"Circuit [{self.name}] is OPEN. "
                        f"Retry after {self.config.recovery_timeout}s"
                    )
            
            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerOpen(
                        f"Circuit [{self.name}] HALF_OPEN limit reached"
                    )
                self.half_open_calls += 1
        
        # 执行调用（在锁外执行，避免阻塞其他请求）
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout_seconds
            )
            await self._on_success()
            return result
            
        except asyncio.TimeoutError:
            await self._on_failure()
            raise LLMTimeoutError(f"LLM call timed out after {self.config.timeout_seconds}s")
            
        except Exception as e:
            await self._on_failure()
            raise
    
    async def _on_success(self):
        async with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold_half_open:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    logger.info(f"[{self.name}] Circuit CLOSED (recovered)")
            else:
                self.failure_count = max(0, self.failure_count - 1)
    
    async def _on_failure(self):
        async with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                logger.warning(f"[{self.name}] Circuit OPEN (half-open failed)")
            elif self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(
                    f"[{self.name}] Circuit OPEN after {self.failure_count} failures"
                )
    
    def _should_attempt_reset(self) -> bool:
        if self.last_failure_time is None:
            return True
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.config.recovery_timeout
    
    def get_status(self) -> Dict:
        """获取熔断器状态（用于监控）"""
        return {
            "name": self.name,
            "state": self.state.name,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "half_open_calls": self.half_open_calls,
            "last_failure_time": self.last_failure_time,
            "time_until_retry": max(0, self.config.recovery_timeout - 
                                   (time.time() - self.last_failure_time))
            if self.last_failure_time else 0
        }

class CircuitBreakerOpen(Exception):
    """熔断器打开异常"""
    pass

class LLMTimeoutError(Exception):
    """LLM 调用超时"""
    pass


class ResilientLLMClient:
    """
    弹性 LLM 客户端
    
    集成：熔断器 + 重试 + Fallback 模型
    """
    
    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}
        self.fallback_chain = {
            "gpt-4o": "claude-sonnet-4",
            "o3-mini": "gpt-4o",
            "claude-sonnet-4": "claude-haiku-4",
            "codex-latest": "gpt-4o"
        }
    
    async def call_with_resilience(
        self,
        model: str,
        prompt: str,
        max_retries: int = 3
    ) -> str:
        """
        带弹性的 LLM 调用
        
        流程：
        1. 获取/创建熔断器
        2. 通过熔断器调用
        3. 失败时重试（指数退避）
        4. 仍然失败时降级到 Fallback 模型
        """
        if model not in self.breakers:
            self.breakers[model] = CircuitBreaker(
                name=f"llm-{model}",
                config=CircuitBreakerConfig(
                    failure_threshold=3,
                    recovery_timeout=30.0,
                    timeout_seconds=180.0
                )
            )
        
        breaker = self.breakers[model]
        
        # 尝试主模型
        for attempt in range(max_retries):
            try:
                return await breaker.call(
                    self._raw_llm_call,
                    model,
                    prompt
                )
            except CircuitBreakerOpen:
                break  # 熔断器打开，直接降级
            except LLMTimeoutError:
                wait_time = 2 ** attempt  # 指数退避
                logger.warning(f"LLM timeout, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        # 降级到 Fallback 模型
        fallback = self.fallback_chain.get(model)
        if fallback:
            logger.info(f"Falling back from {model} to {fallback}")
            return await self.call_with_resilience(fallback, prompt, max_retries=2)
        
        raise Exception(f"All LLM calls failed for model {model}")
    
    async def _raw_llm_call(self, model: str, prompt: str) -> str:
        """原始 LLM 调用（通过 LiteLLM）"""
        # 实际实现调用 LiteLLM Proxy
        pass
```

### 5.2 Checkpoint 机制

```python
# rv_insights/resilience/checkpoint.py
from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime
import json

@dataclass
class AgentCheckpoint:
    """Agent 检查点"""
    checkpoint_id: str
    task_id: str
    stage_id: str
    agent_name: str
    agent_state: Dict  # Agent 内部状态
    workspace_state: Dict  # 工作空间状态（修改了哪些文件）
    llm_context: List[Dict]  # LLM 对话历史
    created_at: datetime
    
class CheckpointManager:
    """
    检查点管理器
    
    支持长时间运行 Agent 任务的中断恢复
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.checkpoint_ttl = 86400 * 7  # 7 天
    
    async def save(
        self,
        task_id: str,
        stage_id: str,
        agent_name: str,
        agent_state: Dict,
        workspace_path: str
    ) -> str:
        """保存检查点"""
        checkpoint_id = f"cp-{task_id}-{stage_id}-{datetime.utcnow().strftime('%H%M%S')}"
        
        # 捕获工作空间状态
        workspace_state = await self._capture_workspace(workspace_path)
        
        checkpoint = AgentCheckpoint(
            checkpoint_id=checkpoint_id,
            task_id=task_id,
            stage_id=stage_id,
            agent_name=agent_name,
            agent_state=agent_state,
            workspace_state=workspace_state,
            llm_context=agent_state.get("conversation_history", []),
            created_at=datetime.utcnow()
        )
        
        # 序列化并存储
        await self.redis.setex(
            f"checkpoint:{checkpoint_id}",
            self.checkpoint_ttl,
            json.dumps(checkpoint, default=str)
        )
        
        # 记录到任务的检查点列表
        await self.redis.lpush(f"checkpoints:{task_id}:{stage_id}", checkpoint_id)
        
        return checkpoint_id
    
    async def restore(
        self,
        checkpoint_id: str,
        target_workspace: str
    ) -> Optional[AgentCheckpoint]:
        """恢复检查点"""
        data = await self.redis.get(f"checkpoint:{checkpoint_id}")
        if not data:
            return None
        
        checkpoint_dict = json.loads(data)
        checkpoint = AgentCheckpoint(**checkpoint_dict)
        
        # 恢复工作空间
        await self._restore_workspace(checkpoint.workspace_state, target_workspace)
        
        return checkpoint
    
    async def get_latest(self, task_id: str, stage_id: str) -> Optional[str]:
        """获取最新的检查点 ID"""
        checkpoint_id = await self.redis.lindex(
            f"checkpoints:{task_id}:{stage_id}",
            0
        )
        return checkpoint_id
    
    async def _capture_workspace(self, workspace_path: str) -> Dict:
        """捕获工作空间状态"""
        import subprocess
        
        # 获取修改的文件列表
        result = subprocess.run(
            ['git', '-C', workspace_path, 'status', '--porcelain'],
            capture_output=True, text=True
        )
        
        modified_files = []
        for line in result.stdout.strip().split('\n'):
            if line:
                status, filepath = line[:2], line[3:]
                modified_files.append({"status": status, "path": filepath})
        
        # 获取 diff
        result = subprocess.run(
            ['git', '-C', workspace_path, 'diff'],
            capture_output=True, text=True
        )
        
        return {
            "modified_files": modified_files,
            "diff": result.stdout,
            "head_commit": subprocess.run(
                ['git', '-C', workspace_path, 'rev-parse', 'HEAD'],
                capture_output=True, text=True
            ).stdout.strip()
        }
    
    async def _restore_workspace(self, state: Dict, target_path: str):
        """恢复工作空间"""
        # 重置到检查点时的 commit
        head = state.get("head_commit", "HEAD")
        subprocess.run(
            ['git', '-C', target_path, 'reset', '--hard', head],
            check=True
        )
        
        # 应用保存的 diff
        if state.get("diff"):
            process = subprocess.Popen(
                ['git', '-C', target_path, 'apply', '-'],
                stdin=subprocess.PIPE,
                text=True
            )
            process.communicate(input=state["diff"])
```

### 5.3 健康检查与自愈

```python
# rv_insights/resilience/health.py
class HealthMonitor:
    """
    健康监控器
    
    持续监控各组件健康状态，自动触发恢复
    """
    
    def __init__(self):
        self.checks = {}
        self.status = {}
    
    def register_check(self, name: str, check_func: Callable, interval: int = 30):
        """注册健康检查"""
        self.checks[name] = {
            "func": check_func,
            "interval": interval,
            "last_run": 0,
            "failures": 0
        }
    
    async def run_checks(self):
        """执行所有健康检查"""
        for name, check in self.checks.items():
            try:
                result = await check["func"]()
                self.status[name] = {
                    "status": "healthy" if result else "unhealthy",
                    "last_check": time.time(),
                    "consecutive_failures": 0 if result else check.get("failures", 0) + 1
                }
                
                if not result:
                    logger.warning(f"Health check failed: {name}")
                    await self._handle_unhealthy(name)
                    
            except Exception as e:
                logger.error(f"Health check error ({name}): {e}")
                self.status[name] = {
                    "status": "error",
                    "error": str(e),
                    "consecutive_failures": check.get("failures", 0) + 1
                }
    
    async def _handle_unhealthy(self, component: str):
        """处理不健康组件"""
        # 根据组件类型执行不同的恢复策略
        recovery_actions = {
            "llm_gateway": self._restart_llm_gateway,
            "sandbox_pool": self._replenish_sandboxes,
            "event_bus": self._reconnect_event_bus,
        }
        
        action = recovery_actions.get(component)
        if action:
            await action()
```

---

## 6. Token 优化与成本管控（增强）

### 6.1 Token 优化器

```python
# rv_insights/optimization/token.py
class TokenOptimizer:
    """
    Token 优化器
    
    减少不必要的 Token 消耗，降低运营成本
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.cache_ttl = 3600  # 1 小时
    
    def compress_code(self, code: str, max_lines: int = 50, context_lines: int = 5) -> str:
        """
        压缩代码片段
        
        策略：保留函数签名和关键逻辑，省略中间实现细节
        """
        lines = code.split('\n')
        
        if len(lines) <= max_lines:
            return code
        
        # 保留开头和结尾，中间省略
        head = lines[:context_lines]
        tail = lines[-context_lines:]
        
        return '\n'.join(head) + f"\n... ({len(lines) - 2 * context_lines} lines omitted) ...\n" + '\n'.join(tail)
    
    def compress_context(self, context: str, target_tokens: int = 2000) -> str:
        """
        压缩长上下文
        
        策略：
        1. 去除冗余空白
        2. 缩写常见术语
        3. 截断过长的段落
        """
        # 去除多余空白
        compressed = ' '.join(context.split())
        
        # 估算当前 Token 数（粗略：1 token ≈ 4 chars for English, 1 token ≈ 1 char for Chinese）
        estimated_tokens = len(compressed) // 3
        
        if estimated_tokens <= target_tokens:
            return compressed
        
        # 需要进一步压缩：使用轻量级模型摘要
        # 这里标记为需要外部摘要服务
        return f"[CONTEXT_TOO_LONG: {estimated_tokens} tokens, summary needed]"
    
    async def cache_response(self, prompt_hash: str, response: str) -> bool:
        """
        缓存 LLM 响应
        
        对于确定性查询（如编码规范检查），直接返回缓存结果
        """
        await self.redis.setex(
            f"llm_cache:{prompt_hash}",
            self.cache_ttl,
            response
        )
        return True
    
    async def get_cached_response(self, prompt_hash: str) -> Optional[str]:
        """获取缓存的响应"""
        return await self.redis.get(f"llm_cache:{prompt_hash}")
    
    def compute_prompt_hash(self, prompt: str) -> str:
        """计算 Prompt 哈希用于缓存"""
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]
    
    async def smart_summarize(
        self,
        text: str,
        target_length: int = 1000,
        model: str = "gpt-4o-mini"
    ) -> str:
        """
        智能摘要
        
        使用便宜模型对长文本进行摘要，再传递给主力模型
        """
        if len(text) <= target_length * 3:
            return text
        
        # 调用轻量级模型进行摘要
        # 实际实现通过 LiteLLM
        summary = await self._call_cheap_model(
            model=model,
            prompt=f"Summarize the following text in {target_length} characters:\n\n{text[:8000]}"
        )
        
        return summary
    
    async def _call_cheap_model(self, model: str, prompt: str) -> str:
        """调用便宜模型"""
        # 通过 LiteLLM 调用
        pass


class CostTracker:
    """
    成本追踪器
    
    实时追踪每个任务、每个 Agent 的 Token 和成本消耗
    """
    
    def __init__(self, db, redis_client):
        self.db = db
        self.redis = redis_client
        self.daily_budget = 100.0  # USD
    
    async def track(
        self,
        task_id: str,
        stage_id: str,
        agent_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float
    ):
        """记录成本"""
        # 写入数据库
        await self.db.execute("""
            UPDATE stages 
            SET token_input = token_input + $1,
                token_output = token_output + $2,
                cost_usd = cost_usd + $3
            WHERE stage_id = $4
        """, input_tokens, output_tokens, cost_usd, stage_id)
        
        # 更新 Redis 实时统计
        today = datetime.utcnow().strftime("%Y-%m-%d")
        await self.redis.hincrbyfloat(f"cost:daily:{today}", "total", cost_usd)
        await self.redis.hincrby(f"cost:daily:{today}", "tokens", input_tokens + output_tokens)
        
        # 检查预算
        today_cost = float(await self.redis.hget(f"cost:daily:{today}", "total") or 0)
        if today_cost > self.daily_budget * 0.8:
            logger.warning(f"Daily cost at {today_cost/self.daily_budget:.1%} of budget")
            await self._send_budget_alert(today_cost)
    
    async def _send_budget_alert(self, current_cost: float):
        """发送预算告警"""
        # 发送 Slack/Email 告警
        pass
    
    async def get_realtime_dashboard(self) -> Dict:
        """获取实时成本看板数据"""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        
        pipeline = self.redis.pipeline()
        pipeline.hgetall(f"cost:daily:{today}")
        pipeline.hgetall(f"cost:agent:{today}")
        pipeline.hgetall(f"cost:model:{today}")
        
        results = await pipeline.execute()
        
        return {
            "today": {
                "total_cost_usd": float(results[0].get("total", 0)),
                "total_tokens": int(results[0].get("tokens", 0)),
                "budget_remaining": self.daily_budget - float(results[0].get("total", 0))
            },
            "by_agent": dict(results[1]),
            "by_model": dict(results[2])
        }
```

---

## 7. 分布式事务与 Saga 模式（增强）

### 7.1 Saga 协调器

```python
# rv_insights/transaction/saga.py
from dataclasses import dataclass
from typing import List, Callable, Dict, Any
from enum import Enum
import asyncio

class SagaStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"

@dataclass
class SagaStep:
    """Saga 步骤"""
    step_name: str
    action: Callable  # 正向操作
    compensation: Callable  # 补偿操作
    action_params: Dict = None
    compensation_params: Dict = None

class SagaOrchestrator:
    """
    Saga 事务协调器
    
    保证多步骤操作的原子性：
    - 阶段状态更新
    - Artifact 写入
    - HITL 请求创建
    - 事件发布
    """
    
    def __init__(self, db, event_bus):
        self.db = db
        self.event_bus = event_bus
        self.completed_steps: List[str] = []
    
    async def execute(self, saga_id: str, steps: List[SagaStep]) -> bool:
        """
        执行 Saga
        
        流程：
        1. 顺序执行每个步骤
        2. 任何步骤失败时，反向执行补偿
        3. 记录 Saga 状态
        """
        self.completed_steps = []
        
        for step in steps:
            try:
                # 执行正向操作
                result = await step.action(**(step.action_params or {}))
                self.completed_steps.append(step.step_name)
                
                # 记录步骤完成
                await self._record_step(saga_id, step.step_name, "completed", result)
                
            except Exception as e:
                logger.error(f"Saga step {step.step_name} failed: {e}")
                
                # 触发补偿
                await self._compensate(saga_id, steps)
                return False
        
        # 所有步骤完成
        await self._record_saga_status(saga_id, SagaStatus.COMPLETED)
        return True
    
    async def _compensate(self, saga_id: str, steps: List[SagaStep]):
        """执行补偿"""
        await self._record_saga_status(saga_id, SagaStatus.COMPENSATING)
        
        # 反向执行已完成步骤的补偿
        for step_name in reversed(self.completed_steps):
            step = next(s for s in steps if s.step_name == step_name)
            
            try:
                await step.compensation(**(step.compensation_params or {}))
                logger.info(f"Compensation for {step_name} succeeded")
            except Exception as e:
                logger.error(f"Compensation for {step_name} failed: {e}")
                # 补偿失败需要人工介入
                await self._alert_manual_intervention(saga_id, step_name, e)
        
        await self._record_saga_status(saga_id, SagaStatus.COMPENSATED)
    
    async def _record_step(self, saga_id: str, step: str, status: str, result: Any):
        """记录步骤状态"""
        await self.db.execute("""
            INSERT INTO saga_steps (saga_id, step_name, status, result, executed_at)
            VALUES ($1, $2, $3, $4, NOW())
        """, saga_id, step, status, json.dumps(result, default=str))
    
    async def _record_saga_status(self, saga_id: str, status: SagaStatus):
        """记录 Saga 状态"""
        await self.db.execute("""
            INSERT INTO sagas (saga_id, status, updated_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (saga_id) DO UPDATE SET status = $2, updated_at = NOW()
        """, saga_id, status.value)
    
    async def _alert_manual_intervention(self, saga_id: str, step: str, error: Exception):
        """告警需要人工介入"""
        logger.critical(f"Saga {saga_id} compensation failed at {step}: {error}")
        # 发送告警通知


# 使用示例：阶段完成 Saga
async def complete_stage_with_saga(
    orchestrator: SagaOrchestrator,
    stage_id: str,
    artifact: Artifact
) -> bool:
    """
    使用 Saga 完成阶段
    
    原子操作：
    1. 保存 Artifact
    2. 更新阶段状态
    3. 创建 HITL 请求
    4. 发送事件
    """
    artifact_id = None
    hitl_request_id = None
    
    steps = [
        SagaStep(
            step_name="save_artifact",
            action=lambda: artifact_store.save(artifact),
            compensation=lambda: artifact_store.delete(artifact_id) if artifact_id else None
        ),
        SagaStep(
            step_name="update_stage",
            action=lambda: db.execute(
                "UPDATE stages SET status='completed' WHERE stage_id=$1", stage_id
            ),
            compensation=lambda: db.execute(
                "UPDATE stages SET status='running' WHERE stage_id=$1", stage_id
            )
        ),
        SagaStep(
            step_name="create_hitl",
            action=lambda: hitl_manager.create_request(stage_id),
            compensation=lambda: hitl_manager.cancel(hitl_request_id) if hitl_request_id else None
        ),
        SagaStep(
            step_name="publish_event",
            action=lambda: event_bus.publish("stage.completed", {"stage_id": stage_id}),
            compensation=lambda: None  # 事件发布无法撤回
        )
    ]
    
    return await orchestrator.execute(f"saga-stage-{stage_id}", steps)
```

---

## 8. 代码审查上下文链（审核层增强）

### 8.1 上下文构建器

```python
# rv_insights/agents/review/context_chain.py
from pathlib import Path
from typing import List, Dict, Optional
import subprocess
import json

class ReviewContextBuilder:
    """
    构建审核所需的完整代码上下文
    
    审核 Agent 不应只看 diff，还需要理解：
    - 被修改函数的完整实现
    - 调用者和被调用者
    - 相关的数据结构和宏定义
    - 该文件最近的修改历史
    - 子系统维护者信息
    """
    
    def __init__(self, rag_engine: RAGEngine):
        self.rag = rag_engine
    
    async def build(self, repo_path: Path, modified_files: List[str], diff: str) -> Dict:
        """构建完整上下文"""
        context = {
            "diff": diff,
            "files": {},
            "call_graph": {},
            "history": {},
            "maintainers": [],
            "similar_patches": []
        }
        
        for file_path in modified_files:
            full_path = repo_path / file_path
            
            # 1. 文件完整内容（带行号）
            if full_path.exists():
                with open(full_path) as f:
                    lines = f.readlines()
                    context["files"][file_path] = {
                        "content": ''.join(lines),
                        "total_lines": len(lines),
                        "language": self._detect_language(file_path)
                    }
            
            # 2. 符号信息（使用 ctags）
            symbols = await self._extract_symbols(repo_path, file_path)
            context["files"][file_path]["symbols"] = symbols
            
            # 3. 调用关系
            context["call_graph"][file_path] = await self._build_call_graph(
                repo_path, file_path, symbols
            )
            
            # 4. 修改历史
            context["history"][file_path] = await self._get_file_history(
                repo_path, file_path, limit=10
            )
        
        # 5. 维护者信息
        context["maintainers"] = await self._get_maintainers(repo_path, modified_files)
        
        # 6. 从 RAG 检索相似 Patch
        context["similar_patches"] = await self.rag.retrieve(
            query=f"similar patch {diff[:500]}",
            source_types=["patch"],
            top_k=3
        )
        
        return context
    
    async def _extract_symbols(self, repo_path: Path, file_path: str) -> List[Dict]:
        """提取文件中的符号定义"""
        result = subprocess.run(
            ['ctags', '-x', '--c-kinds=fpstv', str(repo_path / file_path)],
            capture_output=True, text=True
        )
        
        symbols = []
        for line in result.stdout.split('\n'):
            if not line.strip():
                continue
            parts = line.split(None, 3)
            if len(parts) >= 4:
                symbols.append({
                    "name": parts[0],
                    "type": parts[1],  # function / struct / enum / macro
                    "line": int(parts[2]),
                    "signature": parts[3]
                })
        
        return symbols
    
    async def _build_call_graph(
        self,
        repo_path: Path,
        file_path: str,
        symbols: List[Dict]
    ) -> Dict:
        """
        构建调用图
        
        使用 cscope 或 grep 找出函数的调用者和被调用者
        """
        call_graph = {"callers": {}, "callees": {}}
        
        for symbol in symbols:
            if symbol["type"] != "function":
                continue
            
            # 查找调用者
            callers = await self._find_callers(repo_path, symbol["name"])
            call_graph["callers"][symbol["name"]] = callers
            
            # 查找被调用者（简化：从函数体中提取）
            callees = await self._find_callees_in_function(
                repo_path, file_path, symbol["line"]
            )
            call_graph["callees"][symbol["name"]] = callees
        
        return call_graph
    
    async def _find_callers(self, repo_path: Path, function_name: str) -> List[str]:
        """查找函数的所有调用者"""
        result = subprocess.run(
            ['grep', '-rn', f'\\b{function_name}\\s*(', str(repo_path)],
            capture_output=True, text=True
        )
        
        callers = []
        for line in result.stdout.split('\n')[:20]:
            if line and not line.startswith("Binary"):
                callers.append(line)
        
        return callers
    
    async def _find_callees_in_function(
        self,
        repo_path: Path,
        file_path: str,
        start_line: int
    ) -> List[str]:
        """查找函数体内的被调用函数"""
        # 读取函数体
        with open(repo_path / file_path) as f:
            lines = f.readlines()
        
        # 简单提取函数调用模式
        import re
        function_body = ''.join(lines[start_line-1:start_line+50])
        
        # 匹配函数调用：word(
        calls = re.findall(r'\b(\w+)\s*\(', function_body)
        
        # 过滤掉控制结构
        control = {'if', 'for', 'while', 'switch', 'return', 'sizeof'}
        return list(set(c for c in calls if c not in control))[:10]
    
    async def _get_file_history(
        self,
        repo_path: Path,
        file_path: str,
        limit: int = 10
    ) -> List[Dict]:
        """获取文件修改历史"""
        result = subprocess.run(
            ['git', '-C', str(repo_path), 'log',
             f'--follow', '-n', str(limit),
             '--format=%H|%an|%ae|%ad|%s',
             '--date=short',
             file_path],
            capture_output=True, text=True
        )
        
        history = []
        for line in result.stdout.strip().split('\n'):
            if '|' in line:
                parts = line.split('|', 4)
                if len(parts) == 5:
                    history.append({
                        "commit": parts[0],
                        "author": parts[1],
                        "email": parts[2],
                        "date": parts[3],
                        "subject": parts[4]
                    })
        
        return history
    
    async def _get_maintainers(self, repo_path: Path, modified_files: List[str]) -> List[Dict]:
        """获取子系统维护者信息"""
        # 使用 get_maintainer.pl
        result = subprocess.run(
            ['perl', 'scripts/get_maintainer.pl',
             '--nokeywords', '--nol',
             '--separator=,'] + modified_files,
            capture_output=True, text=True,
            cwd=repo_path
        )
        
        maintainers = []
        for line in result.stdout.strip().split('\n'):
            if '<' in line and '>' in line:
                name = line[:line.index('<')].strip()
                email = line[line.index('<')+1:line.index('>')]
                role = "maintainer"  # 简化处理
                maintainers.append({"name": name, "email": email, "role": role})
        
        return maintainers
    
    def _detect_language(self, file_path: str) -> str:
        """检测编程语言"""
        ext_map = {
            '.c': 'c', '.h': 'c',
            '.cpp': 'cpp', '.hpp': 'cpp',
            '.rs': 'rust',
            '.S': 'asm', '.s': 'asm',
            '.dts': 'dts', '.dtsi': 'dts',
            '.yaml': 'yaml', '.yml': 'yaml',
        }
        return ext_map.get(Path(file_path).suffix, 'unknown')
```

### 8.2 语义分析增强

```python
# rv_insights/agents/review/semantic.py
from tree_sitter import Language, Parser, Tree
import tree_sitter_c as tspython_c

class SemanticAnalyzer:
    """
    代码语义分析器
    
    使用 Tree-sitter 进行 AST 级别的分析
    """
    
    def __init__(self):
        self.c_language = Language(tspython_c.language())
        self.parser = Parser(self.c_language)
    
    def analyze_patch(self, old_code: str, new_code: str) -> Dict:
        """
        分析 Patch 的语义影响
        """
        old_tree = self.parser.parse(old_code.encode())
        new_tree = self.parser.parse(new_code.encode())
        
        return {
            "api_changes": self._detect_api_changes(old_tree, new_tree),
            "lock_changes": self._detect_lock_changes(old_tree, new_tree),
            "error_path_changes": self._detect_error_path_changes(old_tree, new_tree),
            "memory_changes": self._detect_memory_changes(old_tree, new_tree)
        }
    
    def _detect_lock_changes(self, old_tree: Tree, new_tree: Tree) -> List[Dict]:
        """
        检测锁模式变更
        
        内核代码中，锁的获取/释放配对非常重要
        """
        lock_functions = {
            'spin_lock', 'spin_unlock',
            'spin_lock_irqsave', 'spin_unlock_irqrestore',
            'mutex_lock', 'mutex_unlock',
            'down_read', 'up_read',
            'down_write', 'up_write',
            'rcu_read_lock', 'rcu_read_unlock'
        }
        
        old_locks = self._find_lock_calls(old_tree, lock_functions)
        new_locks = self._find_lock_calls(new_tree, lock_functions)
        
        changes = []
        
        # 检查是否有锁的添加或删除
        for lock in new_locks:
            if lock not in old_locks:
                # 新增锁，检查是否有对应的 unlock
                pair = self._find_pair(lock, new_locks)
                if not pair:
                    changes.append({
                        "type": "missing_unlock",
                        "lock": lock,
                        "severity": "critical",
                        "message": f"Added {lock['function']} without matching unlock"
                    })
        
        return changes
    
    def _find_lock_calls(self, tree: Tree, lock_functions: set) -> List[Dict]:
        """查找代码中的锁调用"""
        locks = []
        
        def traverse(node):
            if node.type == "call_expression":
                func_name = self._get_function_name(node)
                if func_name in lock_functions:
                    locks.append({
                        "function": func_name,
                        "line": node.start_point[0],
                        "is_lock": "unlock" not in func_name
                    })
            
            for child in node.children:
                traverse(child)
        
        traverse(tree.root_node)
        return locks
    
    def _get_function_name(self, call_node) -> str:
        """从 call_expression 节点提取函数名"""
        func = call_node.child_by_field_name('function')
        if func:
            return func.text.decode('utf-8') if func.text else ""
        return ""
    
    def _find_pair(self, lock: Dict, all_locks: List[Dict]) -> Optional[Dict]:
        """查找锁的配对"""
        # spin_lock -> spin_unlock
        # spin_lock_irqsave -> spin_unlock_irqrestore
        pair_map = {
            'spin_lock': 'spin_unlock',
            'spin_lock_irqsave': 'spin_unlock_irqrestore',
            'mutex_lock': 'mutex_unlock',
            'down_read': 'up_read',
            'down_write': 'up_write',
            'rcu_read_lock': 'rcu_read_unlock'
        }
        
        expected_pair = pair_map.get(lock['function'])
        if not expected_pair:
            return None
        
        # 在同一线程/函数范围内查找
        for other in all_locks:
            if other["function"] == expected_pair:
                return other
        
        return None
```

---

## 9. 并发控制与 Workspace 管理（开发层增强）

### 9.1 Git Worktree 工作空间

```python
# rv_insights/workspace/manager.py
from pathlib import Path
from typing import Optional
import subprocess
import asyncio

class WorkspaceManager:
    """
    工作空间管理器
    
    使用 Git Worktree 为每个任务创建独立的工作空间，
    避免多任务之间的冲突
    """
    
    def __init__(self, base_repo_path: Path, max_workspaces: int = 20):
        self.base_repo = base_repo_path
        self.max_workspaces = max_workspaces
        self.active_workspaces: Dict[str, Path] = {}
    
    async def allocate(self, task_id: str, project: str) -> Path:
        """
        分配工作空间
        
        流程：
        1. 检查是否已存在
        2. 创建 Git Worktree
        3. 配置环境
        """
        if task_id in self.active_workspaces:
            return self.active_workspaces[task_id]
        
        # 清理旧的工作空间（如果超过限制）
        await self._cleanup_old_workspaces()
        
        workspace = Path(f"/workspaces/{task_id}/{project}")
        workspace.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建 Git Worktree
        repo = self.base_repo / project
        branch_name = f"rv-insights/{task_id}"
        
        # 检查分支是否已存在
        result = subprocess.run(
            ['git', '-C', str(repo), 'branch', '--list', branch_name],
            capture_output=True, text=True
        )
        
        if branch_name in result.stdout:
            # 分支存在，删除后重建
            subprocess.run(
                ['git', '-C', str(repo), 'branch', '-D', branch_name],
                capture_output=True
            )
        
        # 创建新分支和 worktree
        subprocess.run([
            'git', '-C', str(repo), 'worktree', 'add',
            '-b', branch_name,
            str(workspace),
            'HEAD'
        ], check=True)
        
        # 配置 Git
        subprocess.run(
            ['git', '-C', str(workspace), 'config', 'user.email', 'rv-insights@agent.local'],
            check=True
        )
        subprocess.run(
            ['git', '-C', str(workspace), 'config', 'user.name', 'RV-Insights Agent'],
            check=True
        )
        
        self.active_workspaces[task_id] = workspace
        
        # 记录到 Redis（用于分布式场景）
        await redis.setex(f"workspace:{task_id}", 86400, str(workspace))
        
        return workspace
    
    async def release(self, task_id: str):
        """释放工作空间"""
        if task_id not in self.active_workspaces:
            return
        
        workspace = self.active_workspaces[task_id]
        project = workspace.parent.name
        repo = self.base_repo / project
        branch_name = f"rv-insights/{task_id}"
        
        try:
            # 移除 worktree
            subprocess.run([
                'git', '-C', str(repo), 'worktree', 'remove', str(workspace)
            ], check=True)
            
            # 删除分支
            subprocess.run([
                'git', '-C', str(repo), 'branch', '-D', branch_name
            ], check=False)
            
        except Exception as e:
            logger.error(f"Failed to release workspace for {task_id}: {e}")
        
        del self.active_workspaces[task_id]
        await redis.delete(f"workspace:{task_id}")
    
    async def _cleanup_old_workspaces(self):
        """清理旧的工作空间"""
        while len(self.active_workspaces) >= self.max_workspaces:
            # 找最旧的释放
            oldest = min(self.active_workspaces.keys())
            await self.release(oldest)
    
    async def get_diff(self, task_id: str) -> str:
        """获取工作空间的 diff"""
        workspace = self.active_workspaces.get(task_id)
        if not workspace:
            return ""
        
        result = subprocess.run(
            ['git', '-C', str(workspace), 'diff', 'HEAD'],
            capture_output=True, text=True
        )
        
        return result.stdout
    
    async def commit(self, task_id: str, message: str) -> str:
        """提交变更"""
        workspace = self.active_workspaces.get(task_id)
        if not workspace:
            raise ValueError(f"Workspace not found for {task_id}")
        
        # 添加所有变更
        subprocess.run(['git', '-C', str(workspace), 'add', '-A'], check=True)
        
        # 提交
        subprocess.run(
            ['git', '-C', str(workspace), 'commit', '-m', message],
            capture_output=True, text=True
        )
        
        # 返回 commit hash
        result = subprocess.run(
            ['git', '-C', str(workspace), 'rev-parse', 'HEAD'],
            capture_output=True, text=True
        )
        
        return result.stdout.strip()


class LockManager:
    """
    分布式锁管理器
    
    防止多个任务同时修改同一文件或同一分支
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def acquire_file_lock(self, task_id: str, file_path: str, timeout: int = 3600) -> bool:
        """获取文件锁"""
        lock_key = f"lock:file:{file_path}"
        
        # 使用 Redis SET NX（原子操作）
        acquired = await self.redis.set(
            lock_key,
            task_id,
            nx=True,  # Only set if not exists
            ex=timeout
        )
        
        return acquired is not None
    
    async def release_file_lock(self, file_path: str):
        """释放文件锁"""
        await self.redis.delete(f"lock:file:{file_path}")
    
    async def acquire_resource_lock(self, resource_type: str, resource_id: str, task_id: str) -> bool:
        """获取资源锁（如 QEMU 实例）"""
        lock_key = f"lock:resource:{resource_type}:{resource_id}"
        
        acquired = await self.redis.set(
            lock_key,
            task_id,
            nx=True,
            ex=1800  # 30分钟超时
        )
        
        return acquired is not None
```

---

## 10. 社区集成模块（新增）

### 10.1 自动 Patch 提交

```python
# rv_insights/integrations/community.py
from dataclasses import dataclass
from typing import Optional
import subprocess

@dataclass
class PatchSubmissionResult:
    """Patch 提交结果"""
    success: bool
    method: str  # "mail" | "github_pr" | "gitlab_mr"
    url: Optional[str]
    message_id: Optional[str]
    errors: list

class CommunityIntegration:
    """
    社区集成模块
    
    自动将审核通过的 Patch 提交到上游社区
    """
    
    def __init__(self, workspace_manager: WorkspaceManager):
        self.workspace_manager = workspace_manager
    
    async def submit(self, task_id: str, method: str = "mail") -> PatchSubmissionResult:
        """
        提交 Patch
        
        Args:
            method: 提交方式
                - "mail": 通过 git send-email
                - "github_pr": 创建 GitHub Pull Request
                - "dry_run": 仅生成 Patch，不发送
        """
        if method == "mail":
            return await self._submit_via_mail(task_id)
        elif method == "github_pr":
            return await self._submit_via_github_pr(task_id)
        elif method == "dry_run":
            return await self._dry_run(task_id)
        else:
            return PatchSubmissionResult(
                success=False, method=method, url=None,
                message_id=None, errors=["Unknown submission method"]
            )
    
    async def _submit_via_mail(self, task_id: str) -> PatchSubmissionResult:
        """通过邮件提交 Patch"""
        workspace = await self.workspace_manager.active_workspaces.get(task_id)
        if not workspace:
            return PatchSubmissionResult(
                success=False, method="mail", url=None,
                message_id=None, errors=["Workspace not found"]
            )
        
        # 获取维护者列表
        result = subprocess.run(
            ['perl', 'scripts/get_maintainer.pl',
             '--separator=,', '--nokeywords', '--nol'],
            capture_output=True, text=True,
            cwd=workspace
        )
        
        recipients = result.stdout.strip().replace('\n', ',')
        
        # 配置 git send-email
        subprocess.run(
            ['git', '-C', str(workspace), 'config', 'sendemail.to', recipients],
            check=True
        )
        
        # 发送邮件
        result = subprocess.run(
            ['git', '-C', str(workspace), 'send-email',
             '--confirm=never',
             '--no-thread',
             'HEAD^..HEAD'],
            capture_output=True, text=True
        )
        
        # 提取 Message-ID
        message_id = None
        for line in result.stdout.split('\n'):
            if 'Message-ID:' in line:
                message_id = line.split('Message-ID:')[1].strip()
                break
        
        return PatchSubmissionResult(
            success=result.returncode == 0,
            method="mail",
            url=None,
            message_id=message_id,
            errors=[result.stderr] if result.returncode != 0 else []
        )
    
    async def _submit_via_github_pr(self, task_id: str) -> PatchSubmissionResult:
        """通过 GitHub PR 提交"""
        # 使用 gh CLI 创建 PR
        # 需要预先配置 GitHub Token
        pass
    
    async def sync_patchwork_status(self, message_id: str) -> dict:
        """
        同步 Patchwork 状态
        
        Patchwork API: https://patchwork.kernel.org/api/
        """
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://patchwork.kernel.org/api/1.2/patches/",
                params={"msgid": message_id}
            ) as resp:
                data = await resp.json()
                
                if data.get("patches"):
                    patch = data["patches"][0]
                    return {
                        "patchwork_id": patch["id"],
                        "state": patch["state"],  # new / under-review / accepted / rejected / superseded
                        "delegate": patch.get("delegate", {}).get("username"),
                        "series": patch.get("series", []),
                        "checks": patch.get("checks", {})
                    }
                
                return {"state": "not_found"}
    
    async def check_upstream_status(self, task_id: str, days: int = 30) -> dict:
        """
        检查 Patch 在上游的状态
        
        查询：
        1. Patchwork 状态
        2. 邮件列表回复
        3. 是否被合并到主分支
        """
        # 从任务记录中获取 message_id
        task = await self.db.fetchrow(
            "SELECT metadata FROM tasks WHERE task_id = $1", task_id
        )
        
        if not task or not task["metadata"].get("message_id"):
            return {"status": "unknown"}
        
        message_id = task["metadata"]["message_id"]
        
        # 查询 Patchwork
        pw_status = await self.sync_patchwork_status(message_id)
        
        # 查询邮件列表回复
        mail_replies = await self._fetch_replies(message_id)
        
        return {
            "patchwork": pw_status,
            "replies": mail_replies,
            "merged": pw_status.get("state") == "accepted"
        }
    
    async def _fetch_replies(self, message_id: str) -> List[dict]:
        """获取邮件回复"""
        # 使用 lore.kernel.org 的 API
        pass
```

---

## 11. 自适应模型路由（增强）

### 11.1 动态模型选择

```python
# rv_insights/routing/model_router.py
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class TaskComplexity(Enum):
    SIMPLE = "simple"       # 代码风格检查、文档生成
    MEDIUM = "medium"       # Bug 修复、简单功能
    COMPLEX = "complex"     # 架构设计、跨模块重构
    CRITICAL = "critical"   # 安全修复、核心逻辑

class AccuracyRequirement(Enum):
    LOW = "low"         # 探索性任务
    MEDIUM = "medium"   # 一般开发
    HIGH = "high"       # 审核、关键修复

@dataclass
class ModelRoute:
    """模型路由决策"""
    model: str
    fallback: Optional[str]
    temperature: float
    max_tokens: int
    reasoning_effort: Optional[str] = None
    estimated_cost: float = 0.0

class AdaptiveModelRouter:
    """
    自适应模型路由器
    
    根据任务特征、历史表现、成本预算动态选择模型
    """
    
    # 成本表（USD / 1K tokens）
    COST_TABLE = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "o3-mini": {"input": 0.0011, "output": 0.0044},
        "claude-sonnet-4": {"input": 0.003, "output": 0.015},
        "claude-opus-4": {"input": 0.015, "output": 0.075},
        "claude-haiku-4": {"input": 0.00025, "output": 0.00125},
        "codex-latest": {"input": 0.003, "output": 0.012},
    }
    
    # 路由表
    ROUTING_TABLE = {
        (TaskComplexity.SIMPLE, AccuracyRequirement.LOW): ModelRoute(
            model="gpt-4o-mini",
            fallback="claude-haiku-4",
            temperature=0.3,
            max_tokens=2048,
            estimated_cost=0.01
        ),
        (TaskComplexity.SIMPLE, AccuracyRequirement.MEDIUM): ModelRoute(
            model="gpt-4o",
            fallback="claude-sonnet-4",
            temperature=0.2,
            max_tokens=4096,
            estimated_cost=0.05
        ),
        (TaskComplexity.MEDIUM, AccuracyRequirement.MEDIUM): ModelRoute(
            model="gpt-4o",
            fallback="claude-sonnet-4",
            temperature=0.2,
            max_tokens=8192,
            estimated_cost=0.15
        ),
        (TaskComplexity.MEDIUM, AccuracyRequirement.HIGH): ModelRoute(
            model="claude-sonnet-4",
            fallback="gpt-4o",
            temperature=0.1,
            max_tokens=8192,
            estimated_cost=0.20
        ),
        (TaskComplexity.COMPLEX, AccuracyRequirement.HIGH): ModelRoute(
            model="o3-mini",
            fallback="claude-opus-4",
            temperature=0.1,
            max_tokens=16384,
            reasoning_effort="high",
            estimated_cost=0.50
        ),
        (TaskComplexity.CRITICAL, AccuracyRequirement.HIGH): ModelRoute(
            model="claude-opus-4",
            fallback="o3-mini",
            temperature=0.0,
            max_tokens=16384,
            estimated_cost=1.00
        )
    }
    
    def __init__(self, db, cost_tracker: CostTracker):
        self.db = db
        self.cost_tracker = cost_tracker
    
    def route(
        self,
        agent_name: str,
        task_context: Dict,
        complexity: TaskComplexity = None,
        accuracy: AccuracyRequirement = None
    ) -> ModelRoute:
        """
        路由到合适的模型
        """
        # 自动评估复杂度（如果没有提供）
        if complexity is None:
            complexity = self._estimate_complexity(task_context)
        
        if accuracy is None:
            accuracy = self._estimate_accuracy_requirement(agent_name, task_context)
        
        # 获取基础路由
        route = self.ROUTING_TABLE.get((complexity, accuracy))
        if not route:
            route = ModelRoute(
                model="gpt-4o",
                fallback="claude-sonnet-4",
                temperature=0.2,
                max_tokens=4096
            )
        
        # 根据预算调整
        route = self._adjust_for_budget(route)
        
        # 根据历史表现调整
        route = self._adjust_for_performance(route, agent_name)
        
        return route
    
    def _estimate_complexity(self, task_context: Dict) -> TaskComplexity:
        """估算任务复杂度"""
        factors = []
        
        # 基于文件数量
        files = task_context.get("target_files", [])
        if len(files) > 5:
            factors.append("multi_file")
        
        # 基于变更类型
        category = task_context.get("category", "")
        if category in ["feature", "optimization"]:
            factors.append("complex_category")
        
        # 基于估计行数
        loc = task_context.get("estimated_loc", 0)
        if loc > 100:
            factors.append("large_change")
        
        # 评分
        score = len(factors)
        if score >= 3:
            return TaskComplexity.COMPLEX
        elif score >= 1:
            return TaskComplexity.MEDIUM
        return TaskComplexity.SIMPLE
    
    def _estimate_accuracy_requirement(
        self,
        agent_name: str,
        task_context: Dict
    ) -> AccuracyRequirement:
        """估算精度要求"""
        # 审核层需要高精度
        if "review" in agent_name.lower():
            return AccuracyRequirement.HIGH
        
        # 可行性验证需要高精度
        if "feasibility" in agent_name.lower():
            return AccuracyRequirement.HIGH
        
        # 探索层可以容忍较低精度
        if "explore" in agent_name.lower():
            return AccuracyRequirement.LOW
        
        return AccuracyRequirement.MEDIUM
    
    def _adjust_for_budget(self, route: ModelRoute) -> ModelRoute:
        """根据预算调整"""
        # 如果预算紧张，降级到更便宜的模型
        # 实际实现需要查询当前预算状态
        return route
    
    def _adjust_for_performance(self, route: ModelRoute, agent_name: str) -> ModelRoute:
        """根据历史表现调整"""
        # 如果某个模型在该 Agent 上表现很差，切换 Fallback
        # 实际实现需要查询性能数据库
        return route
```

---

## 12. SLA 监控与可观测性（增强）

### 12.1 监控指标定义

```python
# rv_insights/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Info

# 定义指标
AGENT_CALLS_TOTAL = Counter(
    'rv_insights_agent_calls_total',
    'Total agent calls',
    ['agent_name', 'model', 'status']
)

AGENT_LATENCY = Histogram(
    'rv_insights_agent_latency_seconds',
    'Agent execution latency',
    ['agent_name', 'model'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]
)

AGENT_COST = Counter(
    'rv_insights_agent_cost_usd',
    'Agent execution cost in USD',
    ['agent_name', 'model']
)

AGENT_TOKENS = Counter(
    'rv_insights_agent_tokens_total',
    'Total tokens used',
    ['agent_name', 'model', 'token_type']
)

TASKS_ACTIVE = Gauge(
    'rv_insights_tasks_active',
    'Number of active tasks',
    ['status']
)

HITL_PENDING = Gauge(
    'rv_insights_hitl_pending',
    'Number of pending HITL requests',
    ['stage']
)

CIRCUIT_BREAKER_STATE = Gauge(
    'rv_insights_circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=half-open, 2=open)',
    ['breaker_name']
)

WORKSPACE_USAGE = Gauge(
    'rv_insights_workspace_usage',
    'Number of active workspaces'
)

RAG_RETRIEVAL_LATENCY = Histogram(
    'rv_insights_rag_retrieval_latency_seconds',
    'RAG retrieval latency',
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5]
)

RAG_CACHE_HIT_RATE = Gauge(
    'rv_insights_rag_cache_hit_rate',
    'RAG cache hit rate'
)


class MetricsCollector:
    """指标收集器"""
    
    def record_agent_execution(
        self,
        agent_name: str,
        model: str,
        status: str,
        latency: float,
        cost: float,
        input_tokens: int,
        output_tokens: int
    ):
        """记录 Agent 执行指标"""
        AGENT_CALLS_TOTAL.labels(
            agent_name=agent_name,
            model=model,
            status=status
        ).inc()
        
        AGENT_LATENCY.labels(
            agent_name=agent_name,
            model=model
        ).observe(latency)
        
        AGENT_COST.labels(
            agent_name=agent_name,
            model=model
        ).inc(cost)
        
        AGENT_TOKENS.labels(
            agent_name=agent_name,
            model=model,
            token_type="input"
        ).inc(input_tokens)
        
        AGENT_TOKENS.labels(
            agent_name=agent_name,
            model=model,
            token_type="output"
        ).inc(output_tokens)
    
    def update_task_counts(self, status_counts: Dict[str, int]):
        """更新任务计数"""
        for status, count in status_counts.items():
            TASKS_ACTIVE.labels(status=status).set(count)
    
    def record_circuit_state(self, breaker_name: str, state: CircuitState):
        """记录熔断器状态"""
        state_value = {
            CircuitState.CLOSED: 0,
            CircuitState.HALF_OPEN: 1,
            CircuitState.OPEN: 2
        }[state]
        
        CIRCUIT_BREAKER_STATE.labels(breaker_name=breaker_name).set(state_value)
```

### 12.2 SLA 定义

```yaml
# sla.yaml
service_level_agreements:
  # 探索层
  discovery:
    availability: "99.5%"
    latency_p95: "30s"
    accuracy: 
      target: "75%"
      measurement: "feasibility_score correlation with human judgment"
    
  # 开发层
  development:
    availability: "99.0%"
    latency_p95: "5min"
    compile_success_rate:
      target: "70%"
      minimum: "50%"
    
  # 审核层
  review:
    availability: "99.5%"
    latency_p95: "2min"
    issue_detection_rate:
      target: "80%"
      measurement: "true positives / (true positives + false negatives)"
    false_positive_rate:
      target: "<20%"
    
  # HITL
  hitl:
    response_time_sla: "24h"
    notification_delivery: "99.9%"
    
  # 整体
  end_to_end:
    task_completion_rate:
      target: "60%"
      measurement: "tasks reaching COMPLETE / total tasks"
    cost_per_successful_contribution:
      target: "< $10"
      measurement: "total_cost / successful_contributions"
```

---

## 13. Pydantic Settings 统一配置（工程实践增强）

```python
# rv_insights/config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator
from typing import List, Optional

class DatabaseSettings(BaseSettings):
    """数据库配置"""
    url: str = Field(..., env="DATABASE_URL")
    pool_size: int = Field(10, env="DB_POOL_SIZE")
    max_overflow: int = Field(20, env="DB_MAX_OVERFLOW")
    
class RedisSettings(BaseSettings):
    """Redis 配置"""
    url: str = Field(..., env="REDIS_URL")
    
class LLMSettings(BaseSettings):
    """LLM 配置"""
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    anthropic_api_key: str = Field(..., env="ANTHROPIC_API_KEY")
    litellm_base_url: str = Field("http://localhost:4000", env="LITELLM_BASE_URL")
    
    daily_cost_budget: float = Field(100.0, env="DAILY_COST_BUDGET")
    max_tokens_per_call: int = Field(8192, env="MAX_TOKENS_PER_CALL")
    timeout_seconds: float = Field(120.0, env="LLM_TIMEOUT_SECONDS")
    
    fallback_enabled: bool = Field(True, env="LLM_FALLBACK_ENABLED")
    circuit_breaker_enabled: bool = Field(True, env="CIRCUIT_BREAKER_ENABLED")

class SandboxSettings(BaseSettings):
    """沙箱配置"""
    runtime: str = Field("runsc", env="SANDBOX_RUNTIME")
    cpu_limit: str = Field("4", env="SANDBOX_CPU_LIMIT")
    memory_limit: str = Field("8g", env="SANDBOX_MEM_LIMIT")
    storage_limit: str = Field("20g", env="SANDBOX_STORAGE_LIMIT")
    max_concurrent: int = Field(10, env="SANDBOX_MAX_CONCURRENT")
    
class HITLSettings(BaseSettings):
    """HITL 配置"""
    timeout_hours: int = Field(24, env="HITL_TIMEOUT_HOURS")
    notification_channels: List[str] = Field(["websocket"], env="HITL_CHANNELS")
    slack_webhook: Optional[str] = Field(None, env="HITL_SLACK_WEBHOOK")
    email_enabled: bool = Field(False, env="HITL_EMAIL_ENABLED")
    
class RAGSettings(BaseSettings):
    """RAG 配置"""
    qdrant_url: str = Field("http://localhost:6333", env="QDRANT_URL")
    embedding_model: str = Field("text-embedding-3-large", env="EMBEDDING_MODEL")
    reranker_model: Optional[str] = Field("cohere/rerank-multilingual-v3.0", env="RERANKER_MODEL")
    top_k: int = Field(10, env="RAG_TOP_K")
    cache_enabled: bool = Field(True, env="RAG_CACHE_ENABLED")

class RVInsightsSettings(BaseSettings):
    """
    RV-Insights 统一配置
    
    从环境变量和 .env 文件加载配置
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # 子配置
    database: DatabaseSettings = Field(default_factory=lambda: DatabaseSettings())
    redis: RedisSettings = Field(default_factory=lambda: RedisSettings())
    llm: LLMSettings = Field(default_factory=lambda: LLMSettings())
    sandbox: SandboxSettings = Field(default_factory=lambda: SandboxSettings())
    hitl: HITLSettings = Field(default_factory=lambda: HITLSettings())
    rag: RAGSettings = Field(default_factory=lambda: RAGSettings())
    
    # 通用配置
    app_name: str = Field("RV-Insights", env="APP_NAME")
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    @validator('log_level')
    def validate_log_level(cls, v):
        allowed = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return v.upper()

# 全局配置实例
settings = RVInsightsSettings()
```

---

## 14. v3.0 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RV-Insights v3.0 整体架构                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    用户交互层 (User Interface)                        │   │
│  │  Web UI │ CLI │ GitHub App │ API Gateway │ Slack/Discord           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                 工作流编排层 (Workflow Orchestration)                  │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐               │   │
│  │  │ 状态机   │ │ HITL     │ │ 事件总线 │ │ Saga     │               │   │
│  │  │ 引擎     │ │ 控制器   │ │ (Redis)  │ │ 协调器   │               │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘               │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │              反馈闭环系统 (Feedback Loop)                    │   │   │
│  │  │  • 即时反馈 (HITL → Prompt 修正)                             │   │   │
│  │  │  • 短期反馈 (Few-shot 示例库)                                │   │   │
│  │  │  • 长期反馈 (RAG 更新 + 性能分析)                            │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Agent 执行层 (Agent Execution)                     │   │
│  │                                                                     │   │
│  │  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐          │   │
│  │  │ OpenAI SDK  │◄───►│ MCP 网关    │◄───►│ Claude SDK  │          │   │
│  │  │ 集群        │     │ (互操作)    │     │ 集群        │          │   │
│  │  │             │     │             │     │             │          │   │
│  │  │ • Discovery │     │ • 工具注册  │     │ • Developer │          │   │
│  │  │ • Planning  │     │ • 调用转发  │     │ • Tester    │          │   │
│  │  │ • Review    │     │ • 格式转换  │     │             │          │   │
│  │  └─────────────┘     └─────────────┘     └─────────────┘          │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │              弹性架构 (Resilience Layer)                     │   │   │
│  │  │  • 熔断器 (Circuit Breaker)                                  │   │   │
│  │  │  • 重试 + 指数退避                                           │   │   │
│  │  │  • 模型 Fallback                                             │   │   │
│  │  │  • Checkpoint 恢复                                           │   │   │
│  │  │  • 健康检查 + 自愈                                           │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    知识 & 数据层 (Knowledge & Data)                   │   │
│  │                                                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │   │
│  │  │ RAG 知识库  │  │ Prompt 注册表│  │ 成本追踪器  │               │   │
│  │  │ (Qdrant)    │  │ (版本管理)  │  │ (实时看板)  │               │   │
│  │  │             │  │             │  │             │               │   │
│  │  │ • ISA 规范  │  │ • A/B 测试  │  │ • Token 优化│               │   │
│  │  │ • ABI 文档  │  │ • Few-shot  │  │ • 预算告警  │               │   │
│  │  │ • 历史Patch │  │ • RAG 注入  │  │ • 模型路由  │               │   │
│  │  │ • 代码示例  │  │ • 注入防护  │  │ • 缓存策略  │               │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘               │   │
│  │                                                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │   │
│  │  │ PostgreSQL  │  │ Redis       │  │ S3/本地     │               │   │
│  │  │ (主存储)    │  │ (缓存/队列) │  │ (Artifact)  │               │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    基础设施层 (Infrastructure)                        │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │   │
│  │  │ 邮件列表  │ │ GitHub   │ │ 代码分析  │ │ 测试沙箱  │ │ 社区提交  │ │   │
│  │  │ 爬虫     │ │ API     │ │ 工具链   │ │ (gVisor) │ │ (send-  │ │   │
│  │  │          │ │         │ │          │ │          │ │ email)  │ │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    可观测性层 (Observability)                         │   │
│  │  Prometheus │ Grafana │ Jaeger │ OpenTelemetry │ 成本看板           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

*文档结束 — v3.0 优化版*

> **v3.0 相对 v2.0 的关键提升**：
> 1. **RAG 知识库层**：ISA 规范、ABI 文档、历史 Patch 全部向量化，Agent 具备领域专业知识
> 2. **反馈闭环系统**：三层反馈（即时/短期/长期），系统具备自我进化能力
> 3. **弹性架构**：熔断器 + Fallback + Checkpoint，单点故障不影响整体
> 4. **成本管控中心**：Token 优化 + 智能路由 + 实时看板，运营成本可控
> 5. **Saga 分布式事务**：阶段状态、Artifact、HITL 三者原子性保障
> 6. **语义审核引擎**：AST 级代码分析，锁配对检测、API 变更追踪
> 7. **Git Workspace 隔离**：每个任务独立分支，多任务并行无冲突
> 8. **社区自动集成**：Patch 自动生成并提交到邮件列表/Patchwork
