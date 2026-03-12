# OpenClaw Linux RISC-V Report Diagrams Design

**Date:** 2026-03-12
**Target document:** `/home/zcxggmu/workspace/hello-projs/linux-riscv-docs/kernel/openclaw/docs/openclaw-linux-riscv-contribution-report.md`

## Goal

为现有调研报告补充 3 张 Mermaid 图，让读者能更直观看到 OpenClaw 在 Linux RISC-V 内核贡献场景中的角色分工、阶段流转和工件沉淀方式。

## Scope

- 不新增图片文件，只在 Markdown 中内嵌 Mermaid。
- 不补充 token 成本图。
- 不改动报告的总体论点，只增强表达清晰度。

## Diagram plan

### 1. 角色协作图

- 放置位置：`## 二 / ### 1. 目标架构` 表格之后
- 目标：把 `OpenClaw -> Claude Code / Codex / Human` 的调度关系可视化
- 关键信息：控制中枢、规划者、开发者、人类闸门、工件沉淀

### 2. 贡献流水线图

- 放置位置：`## 三 / ### 2. linux-riscv-contribute` 的 6 步流程之后
- 目标：把 `discover -> issue -> plan -> implement -> patch` 和 `Gate-1/2/3` 表达成一条流程线
- 关键信息：阶段顺序、人工审批点、Codex 迭代闭环

### 3. 工件流转图

- 放置位置：同一小节内，在“制度化价值”说明之后
- 目标：强调这不是纯聊天，而是带文件工件的可审计流水线
- 关键信息：`workflow.yaml`、`gap_registry.yaml`、`issue_map.yaml`、`plans/`、`run_history/`、`patches/`、`logs/`

## Writing principles

- 图前增加 1 句引导说明，避免图示悬空。
- Mermaid 节点文案尽量短，避免渲染后拥挤。
- 图与正文保持一致术语，不引入新的概念层级。
