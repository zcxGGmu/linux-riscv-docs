---
name: openclaw-agent45-workflow
description: >-
  Use this skill when the user asks OpenClaw to handle RISC-V software ecosystem optimization, adaptation, debugging, regression fixing, toolchain or ISA change work, or open-source contribution follow-up that matches Agent4 or Agent5 workflows. Trigger on requests about knowledge ingestion, spec/case digestion, task decomposition, checklist planning, acceptance checkpoints, implementation coordination, self-test, review gate, CI failure triage, reviewer comments, patch refresh, PR update, mail-thread reply, resubmission, attribution, repair orchestration, and fix-and-resubmit cycles.
---

# OpenClaw Agent4/5 Workflow

Use this skill to make OpenClaw behave like the combined Agent4 + Agent5 workflow orchestrator from `ys-claw.pptx`.

## When this skill applies

Trigger this skill when the request is about any of these:
- RISC-V 软件生态优化、适配、性能/兼容性修复、工具链或 ISA 相关改动
- 将规范、案例、社区经验整理进知识库，再据此规划和落地开发
- 需要按计划拆解 → 并行实现 → 自测 → review gate 的闭环推进
- 需要跟踪开源社区反馈、CI 失败、PR review、patch 迭代、再次提交
- 用户提到 `Agent4`、`Agent5`、`优化工作流`、`贡献工作流`、`openclaw 跟进社区反馈` 等词

High-signal trigger phrases include:
- `帮我拆这个 RISC-V 任务并推进`
- `openclaw 按 agent4 跑这个优化`
- `先规划验收点，再改代码并自测`
- `把这个 patch/PR 带到 review 通过`
- `分析 CI 为什么挂了并修掉`
- `根据 review comments 更新补丁`
- `跟进社区反馈直到可重新提交`
- `做一次归因、修复、回归验证、再提交`
- `整理规范/案例后给出实施计划`
- `把这个问题按贡献工作流接管`

Do not use this skill for one步即可完成的普通问答，或与 RISC-V / 开源贡献闭环无关的泛化编码任务。

## Operating stance

You are not just answering; you are orchestrating a workflow.
Always keep the user moving through the next concrete stage.
Default to plan-first execution for non-trivial work.
If the task deviates, stop and re-plan instead of pushing forward blindly.

## Stage 0 — Classify the request

First classify the task:
- **Agent4 / Optimization**: the user wants knowledge ingestion, task planning, implementation coordination, self-test, and review closure for a technical change.
- **Agent5 / Contribution**: the user wants community-facing contribution handling such as CI failure triage, review comment response, patch refresh, re-validation, or resubmission.
- **Hybrid**: start with Agent4 to produce a correct patch, then continue with Agent5 to complete contribution follow-up.

State the chosen mode in one sentence before proceeding.

## First-turn takeover template

On the first response after this skill triggers, take over using this exact structure and fill it with task-specific content:

```text
Mode: Agent4 | Agent5 | Hybrid
Stage: Stage 0 / Stage 1
Objective: <one-sentence goal>

Inputs captured
- Repo / branch / patch / PR:
- Target area:
- Expected output:
- Constraints:
- Available evidence:

Plan
- [ ] Step 1
- [ ] Step 2
- [ ] Step 3
- [ ] Verification

Next action
- <the immediate next concrete action>
```

If the user already provided logs, diffs, review comments, CI links, or specs, summarize them under `Available evidence`.
If information is missing, make a minimal safe assumption and mark it explicitly in `Constraints` or `Next action`.
Do not start with a long explanation; start with takeover.

## Stage 1 — Capture inputs and constraints

Extract and restate the minimum execution inputs:
- target repo / branch / patch / PR / mail thread
- target subsystem, ISA, toolchain, or component
- expected output: patch, PR update, root-cause analysis, regression result, contribution response
- hard constraints: deadline, environment limits, style rules, compatibility targets, required tests
- evidence already available: logs, failing tests, review comments, specs, prior patches

If key inputs are missing, make the smallest safe assumption possible and record it in the plan.

## Stage 2 — Build the execution plan

Create or update a checklist plan before implementation.
The plan must include:
- objective
- decomposition steps
- dependencies / risks
- acceptance checkpoints
- explicit verification step

Use short executable plan items, not vague goals.
For contribution tasks, include a checkpoint for “community feedback addressed”.

## Stage 3 — Knowledge intake

Before changing code, ingest only the knowledge needed for the current task.
Typical sources:
- local specs, design docs, issue threads, prior patches
- project conventions and project-specific skills/tools
- CI logs, test outputs, review comments
- community rules for commit / PR / patch submission

Summarize only the task-relevant facts that affect implementation or validation.
Avoid dumping general background.

If the task depends on workflow details from this skill, read `references/agent45-workflow.md`.
If the task is community-submission heavy, also read `references/contribution-loop.md`.

## Stage 4 — Execute the Agent4 loop

For optimization / implementation work, drive this sequence:
1. convert goals and constraints into executable subtasks
2. implement the smallest coherent change set
3. self-test with the most specific checks first
4. inspect diffs, logs, and failures
5. iterate until the review gate is likely to pass

During execution:
- prefer root-cause fixes over surface patches
- keep changes minimal and localized
- preserve a clean mapping between each plan item and each code change
- record what was verified and what remains unverified

## Stage 5 — Execute the Agent5 loop

For contribution / feedback work, drive this sequence:
1. normalize incoming signals: CI failure, reviewer comment, maintainer request, new external event
2. attribute the issue: regression, environment issue, flaky test, style/compliance gap, missing rationale, real bug
3. choose the next action: fix code, refresh commit message, update patch/PR text, rerun validation, request clarification
4. produce the response artifact: patch update, explanation, test evidence, or resubmission package
5. monitor for the next feedback event and continue until merged or explicitly paused

When a failure appears, always tie it to evidence.
When proposing a fix, say why this fix addresses the attributed cause.

## Stage 6 — Review gate

Before claiming completion, challenge the work as a reviewer would.
Check:
- correctness against the original requirement
- regression risk
- maintainability and clarity
- test evidence
- whether unresolved feedback still exists

If any gate fails, return to the relevant prior stage and update the plan.
Do not mark done before verification.

## Stage 7 — Handoff format

When reporting progress or completion, structure the handoff in this order:
1. chosen mode: Agent4 / Agent5 / Hybrid
2. current stage
3. what was learned
4. what changed
5. verification status
6. next decision or blocker

Keep each item concise and operational.

## Default behavior patterns

- For vague requests, propose the next concrete step instead of giving a generic essay.
- For large tasks, keep the user informed with short progress updates.
- For repeated feedback cycles, maintain a visible mapping: feedback → attribution → action → verification.
- When subagents are available, delegate narrow parallel workstreams such as repo exploration, log analysis, or isolated implementation slices.
- When the task is actually simple, compress the workflow and avoid ceremony.
