---
name: riscv-contribution-workflow
description: >-
  Orchestrate RISC-V software ecosystem optimization and open-source contribution workflows. Use when the user asks to: (1) ingest specs/cases into structured knowledge then plan and implement RISC-V changes, (2) decompose RISC-V tasks into executable plans with acceptance checkpoints, (3) drive implementation with self-test and review gate iterations, (4) handle CI failures, review comments, patch refresh, or resubmission for RISC-V contributions, (5) take end-to-end ownership from planning through community feedback closure. Trigger on mentions of Agent4, Agent5, RISC-V optimization workflow, RISC-V contribution workflow, or any request implying staged execution with verification loops.
---

# RISC-V Contribution Workflow

Orchestrate the combined Agent4 (Optimization) + Agent5 (Contribution) workflow for RISC-V software ecosystem work.

## When this skill applies

Trigger this skill when the request involves any of these:
- RISC-V software ecosystem optimization, adaptation, performance or compatibility fixes
- Ingesting specs, cases, or community knowledge into a structured knowledge base before planning implementation
- Decomposing RISC-V tasks into plans with acceptance checkpoints, then executing with self-test and review
- Tracking and responding to CI failures, PR review comments, patch iterations, or resubmission cycles
- End-to-end ownership from knowledge intake through community feedback closure

### High-signal trigger phrases

**Optimization (Agent4)**:
- `按 Agent4 推进这个 RISC-V 优化`
- `先规划验收点，再改代码并自测`
- `整理规范/案例后给出实施计划`
- `拆计划、落地、review 收口`

**Contribution (Agent5)**:
- `把这个 patch/PR 带到 review 通过`
- `分析 CI 为什么挂了并修掉`
- `根据 review comments 更新补丁`
- `跟进社区反馈直到可重新提交`

**Hybrid**:
- `按 Agent4 + Agent5 的方式接管到底`
- `从规划、实现到反馈处理都接管`
- `先做技术修复，再跟进 CI 和 review 到闭环`

### Non-trigger guardrails

Do not trigger when the user only wants:
- One-shot factual Q&A with no execution loop
- A tiny code edit with no planning, review, or follow-up
- Generic writing, translation, or summary unrelated to RISC-V execution
- Simple tutorial help: explaining one concept, one command, or one error in isolation

If trigger confidence is low, read `references/failure-modes.md` before proceeding.

## Operating stance

You are orchestrating a workflow, not just answering questions.
Always keep the user moving through the next concrete stage.
Default to plan-first execution for non-trivial work.
If the task deviates, stop and re-plan instead of pushing forward blindly.

## Stage 0 — Classify the request

Classify into one mode before proceeding:
- **Agent4 / Optimization**: knowledge ingestion, task planning, implementation, self-test, review gate
- **Agent5 / Contribution**: CI failure triage, review comment response, patch refresh, re-validation, resubmission
- **Hybrid**: Agent4 first to produce a correct patch, then Agent5 for contribution follow-up

State the chosen mode in one sentence.
If the request is ambiguous, use `references/failure-modes.md`.

## Stage 1 — Capture inputs and constraints

Extract and restate the minimum execution inputs:
- target repo / branch / patch / PR / mail thread
- target subsystem, ISA extension, toolchain, or component
- expected output: patch, PR update, root-cause analysis, regression result, contribution response
- hard constraints: deadline, environment limits, style rules, compatibility targets, required tests
- evidence already available: logs, failing tests, review comments, specs, prior patches

If key inputs are missing, make the smallest safe assumption possible and record it explicitly.

## First-turn takeover template

On the first response after this skill triggers, use this exact structure and fill with task-specific content:

```text
Mode: Agent4 | Agent5 | Hybrid
Stage: Stage 0 / Stage 1 / Stage 2
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

If the user provided logs, diffs, review comments, CI links, or specs, summarize them under `Available evidence`.
If information is missing, mark it explicitly in `Constraints` or `Next action`.
Do not start with a long explanation; start with takeover.
Prefer 3-5 plan items on the first turn; expand only after more evidence appears.

## Stage 2 — Build the execution plan

Create or update a checklist plan before implementation.
The plan must include:
- objective
- decomposition steps
- dependencies and risks
- acceptance checkpoints
- explicit verification step

Use short executable plan items, not vague goals.
For contribution tasks, include a checkpoint for "community feedback addressed".

## Stage 3 — Knowledge intake

Before changing code, ingest only the knowledge needed for the current task.
Typical sources:
- local specs, design docs, issue threads, prior patches
- project conventions and project-specific skills or tools
- CI logs, test outputs, review comments
- community rules for commit / PR / patch submission

Summarize only the task-relevant facts that affect implementation or validation.
Avoid dumping general background.

If the task depends on Agent4 workflow details, read `references/agent4-workflow.md`.
If the task depends on Agent5 workflow details, read `references/agent5-workflow.md`.

## Stage 4 — Execute the Agent4 loop

For optimization / implementation work, drive this sequence:
1. Convert goals and constraints into executable subtasks
2. Implement the smallest coherent change set
3. Self-test with the most specific checks first
4. Inspect diffs, logs, and failures
5. Iterate until the review gate is likely to pass

During execution:
- Prefer root-cause fixes over surface patches
- Keep changes minimal and localized
- Preserve a clean mapping between each plan item and each code change
- Record what was verified and what remains unverified

For detailed Agent4 steps, read `references/agent4-workflow.md`.

## Stage 5 — Execute the Agent5 loop

For contribution / feedback work, drive this sequence:
1. Normalize incoming signals: CI failure, reviewer comment, maintainer request, new external event
2. Attribute the issue: regression, environment issue, flaky test, style/compliance gap, missing rationale, real bug
3. Choose the next action: fix code, refresh commit message, update patch/PR text, rerun validation, request clarification
4. Produce the response artifact: patch update, explanation, test evidence, or resubmission package
5. Monitor for the next feedback event and continue until merged or explicitly paused

When a failure appears, always tie it to evidence.
When proposing a fix, say why this fix addresses the attributed cause.

For detailed Agent5 steps, read `references/agent5-workflow.md`.

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
