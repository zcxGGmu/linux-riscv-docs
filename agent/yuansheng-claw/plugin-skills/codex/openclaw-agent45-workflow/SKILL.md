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

## Trigger patterns

### Optimization / Agent4

High-signal phrases:
- `帮我拆这个 RISC-V 任务并推进`
- `openclaw 按 agent4 跑这个优化`
- `先规划验收点，再改代码并自测`
- `整理规范/案例后给出实施计划`

Natural request examples:
- `这个 RISC-V 适配任务你先接管，帮我拆计划、落地、再做 review 收口`
- `这里有规范、报错和现有 patch，你按 agent4 的方式把它推进完`
- `别直接改，先整理约束和验收点，再开始实现`
- `先把案例和规范吃透，再给我一个可执行的计划和风险点`
- `这个工具链改动容易回归，你按计划推进并把验证做扎实`

### Contribution / Agent5

High-signal phrases:
- `把这个 patch/PR 带到 review 通过`
- `分析 CI 为什么挂了并修掉`
- `根据 review comments 更新补丁`
- `跟进社区反馈直到可重新提交`
- `做一次归因、修复、回归验证、再提交`
- `把这个问题按贡献工作流接管`

Natural request examples:
- `这个问题不是一次改完就算了，你要盯着 CI 和 review 一直跟进`
- `帮我看下这个 PR 为什么没过，修完后再补验证结论`
- `我把 review 意见贴给你，你按贡献工作流逐条归因并更新补丁`
- `这个补丁已经发出去了，后面社区回复、CI 失败、重新提交都由你接管`
- `如果主线 review 不通过，就继续迭代，直到能合入或者明确卡点`
- `这个不是普通问答，我要你像 Agent5 一样跟进到反馈闭环`

### Workflow takeover / Hybrid

High-signal phrases:
- `你别只回答建议，直接按 workflow 带着这个任务往前走`
- `先做技术修复，再跟进 CI 和 review 到闭环`
- `按 agent4 + agent5 的方式把这件事接管到底`

Natural request examples:
- `先把问题修到 review 能看，再继续盯 CI 和社区反馈`
- `这个事情从规划、实现到反馈处理都由你接管`
- `不要只给方案，直接把这个 patch 从开发推进到可重新提交`

## Non-trigger guardrails

Do not use this skill when the user only wants:
- one-shot factual Q&A with no execution loop
- a tiny code edit with no planning, review, or follow-up
- generic writing, translation, summary, or brainstorming unrelated to RISC-V or open-source contribution workflow
- simple tutorial help such as explaining one concept, one command, or one error message in isolation

Borderline rule:
- if the request can be completed correctly in one short response or one tiny patch, do not trigger this skill
- if the request implies staged execution, verification, or external feedback handling, trigger this skill

If trigger confidence is low or the request is ambiguous, read `references/failure-modes.md`.

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
If the request is ambiguous, classify using `references/failure-modes.md` before proceeding.

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
Prefer 3-5 plan items on the first turn; expand only after more evidence appears.

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
