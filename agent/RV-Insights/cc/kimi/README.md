# RV-Insights: 项目设计方案文档集

**版本**: v1.1  
**日期**: 2026-04-21  
**定位**: 大模型驱动的多Agent RISC-V开源贡献平台完整设计方案

---

## 快速导航

| 优先级 | 文档 | 阅读场景 |
|--------|------|----------|
| **必读** | [`rv-insights-design.md`](./rv-insights-design.md) | 首次阅读，建立全局认知 |
| **架构师** | [`architecture-deep-dive.md`](./architecture-deep-dive.md) | 关注部署、性能、扩展、多租户 |
| **安全工程师** | [`security-deep-dive.md`](./security-deep-dive.md) | 关注零信任、沙箱、合规、供应链安全 |
| **后端工程师** | [`data-model-deep-dive.md`](./data-model-deep-dive.md) | 关注数据库Schema、Redis、存储、恢复机制 |
| **领域专家** | [`riscv-domain-deep-dive.md`](./riscv-domain-deep-dive.md) | 关注RISC-V规范、静态分析、测试矩阵 |
| **前端工程师** | [`ui-design-deep-dive.md`](./ui-design-deep-dive.md) | 关注Web控制台、审核界面、实时通信 |
| **ML工程师** | [`llm-engineering-deep-dive.md`](./llm-engineering-deep-dive.md) | 关注Prompt工程、模型路由、成本控制 |
| **平台工程师** | [`workflow-deep-dive.md`](./workflow-deep-dive.md) | 关注LangGraph编排、错误处理、并发控制 |

---

## 文档统计

| 指标 | 数值 |
|------|------|
| 总文档数 | 8（1主方案 + 7深化专题） |
| 总行数 | ~10,200 行 |
| 总大小 | ~390 KB |
| Mermaid架构图 | 15+ 张 |
| 可直接执行的SQL/代码块 | 80+ 个 |
| 覆盖Agent类型 | 5（探索/规划/开发/审核/测试） |

---

## 设计原则速查

1. **人类在环**: 每个主要阶段后强制中断，等待人工审批
2. **迭代收敛**: 开发-审核循环支持最多5轮自动迭代
3. **分层融合**: LangGraph编排骨架 + AutoGen/MetaGPT/crewAI各取所长
4. **安全隔离**: MCP-Server沙箱 + Firecracker MicroVM四层防护
5. **RISC-V原生**: 专用RAG知识库 + 25条静态分析规则 + 多平台测试矩阵

---

## 演进路线

| 阶段 | 时间 | 目标 |
|------|------|------|
| MVP | 1-2月 | Linux Kernel `arch/riscv` 端到端通路 |
| v1.0 | 3-4月 | 多仓库扩展（QEMU/OpenSBI）、RAG知识库 |
| v1.5 | 5-6月 | RLHF微调、真实RISC-V硬件测试池 |
| v2.0 | 7-12月 | A2A跨实例协作、开放Agent Registry |
