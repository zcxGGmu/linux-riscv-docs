# OpenClaw Report Diagrams Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在现有调研报告中补充 3 张 Mermaid 图，提升 OpenClaw Linux RISC-V 内核贡献工作流的可读性与直观性。

**Architecture:** 只修改现有 Markdown 报告，在对应章节前后插入简短引导语和 Mermaid 代码块。图示分别覆盖角色协作、阶段流水线和工件沉淀，避免与原有结论重复。

**Tech Stack:** Markdown, Mermaid

---

### Task 1: Add planning artifacts

**Files:**
- Create: `docs/plans/2026-03-12-openclaw-report-diagrams-design.md`
- Create: `docs/plans/2026-03-12-openclaw-report-diagrams.md`

**Step 1: Write the design note**

记录目标、图示类型、落点章节和写作约束。

**Step 2: Verify the files exist**

Run: `ls docs/plans`
Expected: 输出中包含两个 `2026-03-12-openclaw-report-diagrams*.md` 文件

### Task 2: Update the main report

**Files:**
- Modify: `docs/openclaw-linux-riscv-contribution-report.md`

**Step 1: Insert the collaboration diagram**

在“目标架构”表格后增加 Mermaid 图，展示 OpenClaw、Claude Code、Codex、人类与工件之间的关系。

**Step 2: Insert the workflow diagram**

在 `linux-riscv-contribute` 的流程列表后增加 Mermaid 图，展示阶段推进、Gate-1/2/3 和实现迭代。

**Step 3: Insert the artifact diagram**

在同一小节中补充工件流转图，强调文件化状态与审计能力。

### Task 3: Verify the document

**Files:**
- Test: `docs/openclaw-linux-riscv-contribution-report.md`

**Step 1: Check Mermaid blocks and captions**

Run: `rg -n '```mermaid|角色协作图|贡献流水线图|工件流转图' docs/openclaw-linux-riscv-contribution-report.md`
Expected: 能看到 3 个 Mermaid 代码块和对应标题

**Step 2: Read back the updated sections**

Run: `sed -n '1,220p' docs/openclaw-linux-riscv-contribution-report.md`
Expected: 图示插入位置自然，正文衔接通顺
