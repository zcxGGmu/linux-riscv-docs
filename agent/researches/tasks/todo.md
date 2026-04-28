# ScienceClaw 项目深度分析任务

## 背景与目标

- 目标项目：`/home/zq/work-space/repo/ai-projs/posp/ScienceClaw`
- 输出要求：在当前目录生成一份详细的 Markdown 分析报告
- 关注重点：项目定位、系统架构、关键模块、运行链路、扩展机制、工程质量与风险

## 执行计划

- [x] 检查当前目录是否已有 `tasks/lessons.md` 与 `tasks/todo.md`
- [x] 阅读顶层 README、部署文档、提交历史，确认项目定位与演进状态
- [x] 分析顶层目录结构与容器/服务编排关系
- [x] 分析 `backend` 与 `deepagent` 的主执行链路
- [x] 分析 `frontend` 的技术栈、页面结构与 API 交互方式
- [x] 分析 `task-service`、`sandbox`、`websearch` 等辅助服务的职责
- [x] 分析 `Skills/`、`Tools/` 与内建技能的扩展机制
- [x] 归纳架构优势、设计取舍、潜在风险与改进建议
- [x] 在当前目录生成最终 Markdown 分析报告
- [x] 复核报告内容并补充 review

## 备注

- `tasks/lessons.md` 当前不存在，本次仅记录检查结果；若后续收到用户纠正，再补充 lessons。

## Review

- 状态：已完成
- 产物：`ScienceClaw-深度分析报告.md`
- 验证方式：静态阅读 README、部署文档、compose 文件、核心后端/前端/调度/沙箱/工具与技能相关源码；补充了提交历史、文件规模、测试存在性检查
- 验证边界：未实际启动 Docker 服务，未做运行时日志验证，未执行自动化测试；项目内也未发现成型测试目录
- 主要发现：
  1. 该项目已经具备“本地科研 Agent 工作台”的完整产品骨架，而非单一聊天 demo
  2. 最强的差异化来自会话级工作区、SSE 透明执行流、ToolUniverse 集成和 Skills/Tools 生命周期管理
  3. 当前最需要补强的是测试体系、安全默认值治理、超大文件拆分和版本/文档口径统一
