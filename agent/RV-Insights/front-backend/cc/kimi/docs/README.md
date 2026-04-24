# RV-Insights 项目设计方案文档集

## 文档清单

| 序号 | 文档 | 路径 | 说明 |
|------|------|------|------|
| 1 | 项目概述与SDK选型 | `00-project-overview.md` | 项目背景、OpenAI/Claude SDK选型分析、整体架构 |
| 2 | 系统架构设计 | `architecture/system-architecture.md` | 详细分层架构、服务拓扑、部署架构 |
| 3 | 后端设计方案 | `backend/backend-design.md` | 领域模型、API设计、数据库Schema、事件驱动 |
| 4 | 前端设计方案 | `frontend/frontend-design.md` | 技术栈、组件架构、状态管理、实时通信 |
| 5 | Agent工作流设计 | `workflow/agent-workflow.md` | 5阶段Agent详细设计、迭代循环、Handoff协议 |
| 6 | 测试方案 | `testing/testing-strategy.md` | 测试金字塔、单元/集成/E2E测试、CI/CD流水线 |

## 快速导航

- [1. 项目概述与SDK选型](#)
- [2. 系统架构设计](#)
- [3. 后端设计方案](#)
- [4. 前端设计方案](#)
- [5. Agent工作流设计](#)
- [6. 测试方案](#)

## 设计约定

- 所有架构图使用 **Mermaid** 语法，可在支持Markdown的平台上直接渲染
- 接口定义使用 **TypeScript** 类型语法
- 数据库Schema使用 **PostgreSQL** DDL语法
- API遵循 **RESTful** 设计规范，同时提供 **WebSocket** 实时事件通道
