# oh-my-claw GitHub Issues Draft（MVP / Phase 1）

## 1. 文档目标

本文档将 `milestones-and-issues.md` 中的 milestone backlog 进一步转换为 **GitHub issue draft** 形式，方便后续直接复制到：

- GitHub Issues
- GitHub Projects
- Linear / Jira / Trello 等任务系统

每个 issue 草稿尽量包含：

- 标题
- 目标
- 背景
- 范围
- 非目标
- 依赖
- 建议标签
- 完成标准

本文档聚焦 MVP / Phase 1，不包含 Phase 2+ 的大功能扩展。

---

## 2. 使用建议

推荐按如下方式使用本文档：

1. 先在 GitHub 中创建 milestones：`M0` ~ `M5`
2. 按本文档中的 issue 顺序创建 issue
3. 为每个 issue 打上推荐 labels
4. 将 issue 挂到对应 milestone 下
5. 完成后用 `oh-my-claw-acceptance-test-plan.md` 做系统级验收

---

## 3. 推荐 Milestones

- `M0 - Project Foundation`
- `M1 - Task Decision and Context`
- `M2 - Guarded Workflow Core`
- `M3 - Workflow Templates and Summary`
- `M4 - Commands Integration and Acceptance`
- `M5 - Documentation and Handoff`

---

## 4. Issue Drafts

---

## M0 - Project Foundation

### Issue 01

**Title**
`[M0] Initialize repository structure for MVP Phase 1`

**Suggested Labels**
- `phase-1`
- `milestone-m0`
- `p0`
- `docs`
- `foundation`

**Goal**
Create the minimum repository structure required by the Phase 1 MVP plan.

**Background**
The current repo already contains design documents, but the eventual implementation phase needs a stable directory layout that matches the architecture and implementation plan.

**Scope**
- Create or confirm the target structure for:
  - `plugin/`
  - `docs/`
  - `examples/`
  - `tasks/`
- Ensure the structure aligns with `oh-my-claw-mvp-implementation-plan.md`

**Out of Scope**
- Implementing business logic
- Setting up all toolchain details

**Dependencies**
- None

**Done When**
- Repository structure is aligned with the MVP implementation plan
- The resulting layout is documented or confirmed for downstream work

---

### Issue 02

**Title**
`[M0] Set up base toolchain for plugin development`

**Suggested Labels**
- `phase-1`
- `milestone-m0`
- `p0`
- `foundation`
- `tooling`

**Goal**
Set up the minimum development toolchain for the plugin workspace.

**Scope**
- Package manager setup
- TypeScript config
- Lint/format baseline
- Test runner baseline
- Minimal scripts for local execution

**Out of Scope**
- Full CI hardening
- Production packaging pipeline

**Dependencies**
- Issue 01

**Done When**
- Basic development scripts run successfully
- Future modules can be added under a stable toolchain

---

### Issue 03

**Title**
`[M0] Define shared result, error, and base type models`

**Suggested Labels**
- `phase-1`
- `milestone-m0`
- `p0`
- `foundation`
- `types`

**Goal**
Freeze the shared types and core error model used by all Phase 1 modules.

**Scope**
- Shared utility types
- `Result<T, E>` pattern
- Core error classes/types
- Base constants if needed

**Out of Scope**
- Workflow-specific models
- Command-specific models

**Dependencies**
- Issue 02

**Done When**
- Shared layer is stable enough for decision/context/gates/workflow modules

---

### Issue 04

**Title**
`[M0] Implement base structured logger interface`

**Suggested Labels**
- `phase-1`
- `milestone-m0`
- `p1`
- `logging`
- `foundation`

**Goal**
Provide a minimal structured logger for decision/context/gate/workflow tracing.

**Scope**
- `debug/info/warn/error`
- Optional module name
- Optional task id field

**Dependencies**
- Issue 03

**Done When**
- Later modules can emit consistent structured logs

---

### Issue 05

**Title**
`[M0] Define MVP configuration types and built-in defaults`

**Suggested Labels**
- `phase-1`
- `milestone-m0`
- `p0`
- `config`

**Goal**
Translate `oh-my-claw-config-spec.md` into concrete configuration types and defaults.

**Scope**
- Top-level config object
- Module config sections
- Built-in defaults

**Out of Scope**
- Advanced migration logic
- Experimental Phase 2 fields beyond placeholders

**Dependencies**
- Issue 03

**Done When**
- Default config object exists and matches config spec

---

### Issue 06

**Title**
`[M0] Implement config schema validation and loader`

**Suggested Labels**
- `phase-1`
- `milestone-m0`
- `p0`
- `config`
- `validation`

**Goal**
Implement schema validation and normalized config loading.

**Scope**
- Schema validation
- Project-level override support
- Normalized output object
- Conflict checks from config spec

**Dependencies**
- Issue 05

**Done When**
- Config can be loaded and validated for downstream modules

---

### Issue 07

**Title**
`[M0] Add unit tests for shared and config layers`

**Suggested Labels**
- `phase-1`
- `milestone-m0`
- `p1`
- `tests`
- `config`

**Goal**
Establish baseline unit coverage for shared/config layers.

**Dependencies**
- Issue 03
- Issue 06

**Done When**
- Shared/config critical tests pass reliably

---

## M1 - Task Decision and Context

### Issue 08

**Title**
`[M1] Define task decision type system`

**Suggested Labels**
- `phase-1`
- `milestone-m1`
- `p0`
- `decision`
- `types`

**Goal**
Define the stable type system for task intake and decision results.

**Scope**
- `TaskIntake`
- `TaskIntent`
- `TaskComplexity`
- `DecisionResult`

**Dependencies**
- Issue 03

**Done When**
- Downstream modules can depend on stable decision interfaces

---

### Issue 09

**Title**
`[M1] Implement decision rules for commands, intent, complexity, and fallback`

**Suggested Labels**
- `phase-1`
- `milestone-m1`
- `p0`
- `decision`

**Goal**
Implement the initial decision rules used by the Task Decision Engine.

**Scope**
- Explicit command priority
- Keyword/intent detection
- Complexity heuristics
- Fallback workflow rules

**Dependencies**
- Issue 08
- Issue 06

**Done When**
- A typical input can be mapped to a meaningful decision output

---

### Issue 10

**Title**
`[M1] Implement Task Decision Engine`

**Suggested Labels**
- `phase-1`
- `milestone-m1`
- `p0`
- `decision`

**Goal**
Implement the main decision entrypoint that produces workflow and guardrail hints.

**Dependencies**
- Issue 09

**Done When**
- A single decision API produces workflow, plan, context, and verification recommendations

---

### Issue 11

**Title**
`[M1] Add unit tests for task decision engine`

**Suggested Labels**
- `phase-1`
- `milestone-m1`
- `p1`
- `decision`
- `tests`

**Goal**
Add unit coverage for design/implement/debug/override/fallback scenarios.

**Dependencies**
- Issue 10

**Done When**
- Key decision scenarios pass consistently

---

### Issue 12

**Title**
`[M1] Define context model and snapshot interfaces`

**Suggested Labels**
- `phase-1`
- `milestone-m1`
- `p0`
- `context`
- `types`

**Goal**
Define the stable interface for `ContextSnapshot` and related models.

**Dependencies**
- Issue 03

**Done When**
- Scanner and summarizer can share a stable contract

---

### Issue 13

**Title**
`[M1] Implement repository scanner for rules, docs, build, test, and task files`

**Suggested Labels**
- `phase-1`
- `milestone-m1`
- `p0`
- `context`
- `scanner`

**Goal**
Implement directory scanning for key project signals.

**Dependencies**
- Issue 12

**Done When**
- Scanner discovers the key file categories defined in the context spec

---

### Issue 14

**Title**
`[M1] Implement relevance ranking for task-related docs`

**Suggested Labels**
- `phase-1`
- `milestone-m1`
- `p1`
- `context`
- `ranking`

**Goal**
Rank discovered docs by relevance to the current task intent.

**Dependencies**
- Issue 13
- Issue 10

**Done When**
- Relevant docs can be prioritized for summary generation

---

### Issue 15

**Title**
`[M1] Implement context summarizer and snapshot builder`

**Suggested Labels**
- `phase-1`
- `milestone-m1`
- `p0`
- `context`
- `summary`

**Goal**
Produce structured `ContextSnapshot` objects from scan results.

**Dependencies**
- Issue 13
- Issue 14

**Done When**
- Invariant rules, project summary, and relevant docs are available as structured output

---

### Issue 16

**Title**
`[M1] Add context cache support`

**Suggested Labels**
- `phase-1`
- `milestone-m1`
- `p2`
- `context`
- `perf`

**Goal**
Add lightweight caching for context snapshots.

**Dependencies**
- Issue 15

**Done When**
- Repeated scans can reuse cached context where appropriate

---

### Issue 17

**Title**
`[M1] Add unit tests for context scanning and summarization`

**Suggested Labels**
- `phase-1`
- `milestone-m1`
- `p1`
- `context`
- `tests`

**Goal**
Test file discovery, ranking, and summary generation behavior.

**Dependencies**
- Issue 15
- Issue 16

**Done When**
- Context behavior is covered for the Phase 1 critical paths

---

## M2 - Guarded Workflow Core

### Issue 18

**Title**
`[M2] Define gate interfaces and gate execution model`

**Suggested Labels**
- `phase-1`
- `milestone-m2`
- `p0`
- `gates`
- `types`

**Goal**
Define a stable interface for all gates and the gate runner.

**Dependencies**
- Issue 10
- Issue 15

**Done When**
- Gate implementations can share one consistent contract

---

### Issue 19

**Title**
`[M2] Implement gate runner and gate order control`

**Suggested Labels**
- `phase-1`
- `milestone-m2`
- `p0`
- `gates`

**Goal**
Implement the shared execution mechanism for Entry/Edit/Verify/Exit Gates.

**Dependencies**
- Issue 18

**Done When**
- Gates can run in a deterministic order

---

### Issue 20

**Title**
`[M2] Implement Entry Gate`

**Suggested Labels**
- `phase-1`
- `milestone-m2`
- `p0`
- `gates`

**Goal**
Control planning requirements for non-trivial tasks.

**Dependencies**
- Issue 19

**Done When**
- Entry Gate produces stable planning decisions

---

### Issue 21

**Title**
`[M2] Implement Edit Gate`

**Suggested Labels**
- `phase-1`
- `milestone-m2`
- `p0`
- `gates`

**Goal**
Ensure execution does not start without sufficient context.

**Dependencies**
- Issue 19

**Done When**
- Missing context can block or redirect execution safely

---

### Issue 22

**Title**
`[M2] Implement Verify Gate`

**Suggested Labels**
- `phase-1`
- `milestone-m2`
- `p0`
- `gates`

**Goal**
Ensure verification semantics exist before final output.

**Dependencies**
- Issue 19

**Done When**
- Verification requirements or notes are generated reliably

---

### Issue 23

**Title**
`[M2] Implement Exit Gate`

**Suggested Labels**
- `phase-1`
- `milestone-m2`
- `p0`
- `gates`

**Goal**
Ensure final summaries meet minimum completeness rules.

**Dependencies**
- Issue 19

**Done When**
- Exit Gate can reject incomplete handoff results

---

### Issue 24

**Title**
`[M2] Add gate unit tests and gate-order tests`

**Suggested Labels**
- `phase-1`
- `milestone-m2`
- `p1`
- `gates`
- `tests`

**Goal**
Test each gate and the shared execution order.

**Dependencies**
- Issue 20
- Issue 21
- Issue 22
- Issue 23

**Done When**
- Gate behavior is covered for core scenarios

---

### Issue 25

**Title**
`[M2] Define workflow state model and workflow contracts`

**Suggested Labels**
- `phase-1`
- `milestone-m2`
- `p0`
- `workflow`
- `types`

**Goal**
Define the workflow state model used by the engine and templates.

**Dependencies**
- Issue 18

**Done When**
- Workflow templates can implement one shared state contract

---

### Issue 26

**Title**
`[M2] Implement workflow skeleton and lifecycle`

**Suggested Labels**
- `phase-1`
- `milestone-m2`
- `p0`
- `workflow`

**Goal**
Implement the shared workflow lifecycle: intake, scan, plan, execute, verify, handoff.

**Dependencies**
- Issue 25

**Done When**
- A workflow can execute the standard lifecycle in order

---

### Issue 27

**Title**
`[M2] Implement workflow registry`

**Suggested Labels**
- `phase-1`
- `milestone-m2`
- `p0`
- `workflow`

**Goal**
Provide workflow registration and lookup by workflow name.

**Dependencies**
- Issue 25

**Done When**
- Decision results can resolve a workflow implementation

---

### Issue 28

**Title**
`[M2] Implement workflow engine`

**Suggested Labels**
- `phase-1`
- `milestone-m2`
- `p0`
- `workflow`
- `integration`

**Goal**
Connect decision, context, gates, and workflow execution into one engine.

**Dependencies**
- Issue 19
- Issue 26
- Issue 27

**Done When**
- The core execution chain works before template specialization

---

### Issue 29

**Title**
`[M2] Add workflow core tests`

**Suggested Labels**
- `phase-1`
- `milestone-m2`
- `p1`
- `workflow`
- `tests`

**Goal**
Test workflow registry, skeleton, and engine behavior.

**Dependencies**
- Issue 28

**Done When**
- Workflow core tests pass reliably

---

## M3 - Workflow Templates and Summary

### Issue 30

**Title**
`[M3] Implement design-proposal workflow template`

**Suggested Labels**
- `phase-1`
- `milestone-m3`
- `p0`
- `workflow`
- `design`

**Goal**
Implement the `design-proposal` workflow per workflow spec.

**Dependencies**
- Issue 28

**Done When**
- Design tasks produce structured proposal outputs

---

### Issue 31

**Title**
`[M3] Implement feature-implementation workflow template`

**Suggested Labels**
- `phase-1`
- `milestone-m3`
- `p0`
- `workflow`
- `implementation`

**Goal**
Implement the `feature-implementation` workflow per workflow spec.

**Dependencies**
- Issue 28

**Done When**
- Implementation tasks produce structured execution-oriented outputs

---

### Issue 32

**Title**
`[M3] Implement bug-fix workflow template`

**Suggested Labels**
- `phase-1`
- `milestone-m3`
- `p0`
- `workflow`
- `bugfix`

**Goal**
Implement the `bug-fix` workflow per workflow spec.

**Dependencies**
- Issue 28

**Done When**
- Bug-fix tasks produce root-cause-first outputs

---

### Issue 33

**Title**
`[M3] Define summary type model`

**Suggested Labels**
- `phase-1`
- `milestone-m3`
- `p0`
- `summary`
- `types`

**Goal**
Define the shared summary contract for all workflows.

**Dependencies**
- Issue 25

**Done When**
- Summary structure is frozen for all workflows and commands

---

### Issue 34

**Title**
`[M3] Implement summary builder`

**Suggested Labels**
- `phase-1`
- `milestone-m3`
- `p0`
- `summary`

**Goal**
Generate unified handoff summaries from workflow state and gate results.

**Dependencies**
- Issue 33
- Issue 30
- Issue 31
- Issue 32

**Done When**
- All three workflows can emit structured summaries consistently

---

### Issue 35

**Title**
`[M3] Implement summary formatter`

**Suggested Labels**
- `phase-1`
- `milestone-m3`
- `p1`
- `summary`
- `formatting`

**Goal**
Render summary output in a stable text-first format.

**Dependencies**
- Issue 34

**Done When**
- Summary output matches Phase 1 handoff expectations

---

### Issue 36

**Title**
`[M3] Add workflow template and summary tests`

**Suggested Labels**
- `phase-1`
- `milestone-m3`
- `p1`
- `tests`
- `workflow`
- `summary`

**Goal**
Test normal, blocked, and partial paths for the three templates and shared summary output.

**Dependencies**
- Issue 30
- Issue 31
- Issue 32
- Issue 34
- Issue 35

**Done When**
- Template-level and summary-level tests pass

---

## M4 - Commands Integration and Acceptance

### Issue 37

**Title**
`[M4] Define command interfaces and command result model`

**Suggested Labels**
- `phase-1`
- `milestone-m4`
- `p1`
- `commands`
- `types`

**Goal**
Define stable command contracts for the MVP commands.

**Dependencies**
- Issue 34

**Done When**
- Command handlers share one consistent interface

---

### Issue 38

**Title**
`[M4] Implement /plan command`

**Suggested Labels**
- `phase-1`
- `milestone-m4`
- `p1`
- `commands`

**Goal**
Provide an explicit planning-oriented entrypoint.

**Dependencies**
- Issue 37
- Issue 28

**Done When**
- `/plan` can force plan-oriented behavior

---

### Issue 39

**Title**
`[M4] Implement /design command`

**Suggested Labels**
- `phase-1`
- `milestone-m4`
- `p0`
- `commands`

**Goal**
Provide an explicit entrypoint for the design workflow.

**Dependencies**
- Issue 37
- Issue 30

**Done When**
- `/design` routes to `design-proposal` and overrides plain text intent

---

### Issue 40

**Title**
`[M4] Implement /implement command`

**Suggested Labels**
- `phase-1`
- `milestone-m4`
- `p0`
- `commands`

**Goal**
Provide an explicit entrypoint for the feature workflow.

**Dependencies**
- Issue 37
- Issue 31

**Done When**
- `/implement` routes to `feature-implementation`

---

### Issue 41

**Title**
`[M4] Implement /debug command`

**Suggested Labels**
- `phase-1`
- `milestone-m4`
- `p0`
- `commands`

**Goal**
Provide an explicit entrypoint for the bug-fix workflow.

**Dependencies**
- Issue 37
- Issue 32

**Done When**
- `/debug` routes to `bug-fix`

---

### Issue 42

**Title**
`[M4] Implement /context-scan command`

**Suggested Labels**
- `phase-1`
- `milestone-m4`
- `p1`
- `commands`
- `context`

**Goal**
Expose context snapshot generation as a standalone command.

**Dependencies**
- Issue 15
- Issue 37

**Done When**
- `/context-scan` outputs a structured context summary

---

### Issue 43

**Title**
`[M4] Assemble plugin entrypoint and register MVP commands`

**Suggested Labels**
- `phase-1`
- `milestone-m4`
- `p0`
- `integration`
- `plugin`

**Goal**
Wire all core modules into the plugin entrypoint and register commands.

**Dependencies**
- Issue 06
- Issue 39
- Issue 40
- Issue 41
- Issue 42

**Done When**
- Plugin initializes successfully and exposes core commands

---

### Issue 44

**Title**
`[M4] Add end-to-end integration tests for the main chain`

**Suggested Labels**
- `phase-1`
- `milestone-m4`
- `p0`
- `integration`
- `tests`

**Goal**
Cover the full chain from command input to structured summary output.

**Dependencies**
- Issue 43

**Done When**
- Main chain integration tests pass

---

### Issue 45

**Title**
`[M4] Execute acceptance scenarios A/B/C`

**Suggested Labels**
- `phase-1`
- `milestone-m4`
- `p0`
- `acceptance`

**Goal**
Run and record the three core success-path acceptance scenarios.

**Dependencies**
- Issue 44

**Done When**
- Scenarios A, B, and C pass per acceptance test plan

---

### Issue 46

**Title**
`[M4] Execute acceptance scenarios D/E/F/G/H`

**Suggested Labels**
- `phase-1`
- `milestone-m4`
- `p1`
- `acceptance`

**Goal**
Run and record blocked/partial/override/context acceptance scenarios.

**Dependencies**
- Issue 44

**Done When**
- D/E/F are at least Partial, and G/H pass

---

## M5 - Documentation and Handoff

### Issue 47

**Title**
`[M5] Expand README into a runnable project entrypoint`

**Suggested Labels**
- `phase-1`
- `milestone-m5`
- `p1`
- `docs`

**Goal**
Extend the README from design entrypoint to implementation/run entrypoint.

**Dependencies**
- Issue 43

**Done When**
- README can guide a developer through the MVP usage path

---

### Issue 48

**Title**
`[M5] Add examples for design, implementation, and bug-fix flows`

**Suggested Labels**
- `phase-1`
- `milestone-m5`
- `p1`
- `docs`
- `examples`

**Goal**
Add representative inputs and outputs for the three workflows.

**Dependencies**
- Issue 45
- Issue 46

**Done When**
- Three workflow examples exist with representative outputs

---

### Issue 49

**Title**
`[M5] Record Phase 1 acceptance results`

**Suggested Labels**
- `phase-1`
- `milestone-m5`
- `p0`
- `docs`
- `acceptance`

**Goal**
Record the final acceptance results for Phase 1.

**Dependencies**
- Issue 45
- Issue 46

**Done When**
- Phase 1 has a documented pass/partial/fail conclusion

---

### Issue 50

**Title**
`[M5] Produce Phase 1 handoff and Phase 2 recommendations`

**Suggested Labels**
- `phase-1`
- `milestone-m5`
- `p1`
- `docs`
- `handoff`

**Goal**
Create a handoff summary covering what shipped, what remains, and what Phase 2 should address.

**Dependencies**
- Issue 49

**Done When**
- A future implementer can pick up Phase 2 work with minimal rediscovery effort

---

## 5. Recommended Issue Creation Order

Use this order when creating or scheduling issues:

1. 01 ~ 07
2. 08 ~ 17
3. 18 ~ 29
4. 30 ~ 36
5. 37 ~ 46
6. 47 ~ 50

This preserves the intended dependency chain from foundation to acceptance.

---

## 6. Suggested “Ready” Criteria for an Issue

Before an issue is marked ready for implementation, ensure:

- The milestone is known
- Dependencies are resolved or scheduled
- Relevant spec docs are linked
- Done criteria are concrete
- Scope and non-goals are clear

---

## 7. Suggested “Done” Criteria for an Issue

Before an issue is closed, ensure:

- The scoped implementation exists
- Relevant tests are added or updated
- Output behavior is consistent with architecture and workflow specs
- Related docs are updated if needed
- No unresolved blocker remains hidden in comments

---

## 8. Final Note

This file is intentionally written as a drafting layer between system design and issue tracker execution.

The intended workflow is:

> `design docs` -> `milestones-and-issues.md` -> `github-issues-draft.md` -> real GitHub issues

That means this document should optimize for clarity and actionability, not completeness of internal architecture discussion.
