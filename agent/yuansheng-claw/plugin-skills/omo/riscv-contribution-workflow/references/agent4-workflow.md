# Agent4: RISC-V Optimization Workflow

Use this reference when the task is primarily "understand, plan, implement, validate" for RISC-V software ecosystem work.

## Overview

Agent4 is a build-and-review loop, not a one-shot answer.
It covers four stages: knowledge intake, planning, implementation, and review gate.

## Step 1 — External knowledge intake

Input: specs, cases, community experience, ISA docs, toolchain manuals
Output: structured knowledge pages in the knowledge base

Actions:
- Ingest the relevant spec sections, issue threads, and prior patches
- Structure the knowledge into searchable context: ISA rules, toolchain constraints, community precedents
- Record only facts that affect implementation or validation decisions
- Avoid dumping general background

Exit condition: the knowledge needed for the current task is structured and retrievable

## Step 2 — Planning and decomposition

Input: goals, constraints, structured knowledge from Step 1
Output: executable plan with todos and acceptance checkpoints

Actions:
- Decompose the task into subtasks with clear dependencies
- Define acceptance checkpoints for each subtask
- Identify risks and mitigation strategies
- Set a review rhythm: when to self-test, when to pause for review

Plan format:
- objective
- decomposition steps (3-7 items)
- dependencies / risks
- acceptance checkpoints
- explicit verification step

Exit condition: plan is reviewed and agreed upon (even if only with yourself)

## Step 3 — Collaborative implementation

Input: plan items
Output: patch + self-test results

Actions:
- Implement the smallest coherent change set per plan item
- Self-test with the most specific checks first
- Inspect diffs, logs, and failures immediately
- Iterate on the same plan item until it passes its checkpoint
- Preserve a clean mapping between each plan item and each code change

Execution rules:
- Prefer root-cause fixes over surface patches
- Keep changes minimal and localized
- Record what was verified and what remains unverified
- When subagents are available, delegate isolated implementation slices in parallel

Exit condition: all plan items pass their acceptance checkpoints

## Step 4 — Review gate

Input: diff, logs, tests, issues
Output: fix advice or approval to export the patch

Actions:
- Check correctness against the original requirement
- Check regression risk
- Check maintainability and clarity
- Check test evidence completeness
- If any check fails, return to Step 3 with specific fix advice

Review checklist:
- [ ] Correctness: does the change do what the plan intended?
- [ ] Regression: could this break existing behavior?
- [ ] Maintainability: is the code clear and well-structured?
- [ ] Test evidence: are the checks specific and sufficient?
- [ ] Unresolved items: is there any deferred work that needs tracking?

Exit condition: review confirms correctness and the patch is ready for export

## Termination

The Agent4 loop terminates when:
- the review gate passes, or
- the user explicitly pauses the work

Output: code patch (export after review gate passes)
