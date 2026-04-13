# RISC-V Gap Workflow Assets Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add reusable workflow assets for the RISC-V gap pipeline, including issue/design templates, agent prompt templates, and state-file schemas.

**Architecture:** Keep the pipeline declarative. Markdown templates capture human-readable workflow contracts, prompt templates define per-agent runtime behavior, and JSON Schemas validate the pipeline state exchanged between OpenClaw, Claude Code, and Codex. Assets live beside the existing design doc so the workflow can be executed from this directory with minimal extra setup.

**Tech Stack:** Markdown, JSON Schema Draft 2020-12, YAML, shell validation with `python3`

---

### Task 1: Planning And Todo Tracking

**Files:**
- Create: `docs/plans/2026-03-10-riscv-gap-assets-implementation.md`
- Modify: `tasks/todo.md`
- Test: `tasks/todo.md`

**Step 1: Write the task list**

Document the concrete assets to add:
- `templates/issue-template.md`
- `templates/design-template.md`
- `prompts/claude-planner-prompt.md`
- `prompts/codex-implementer-prompt.md`
- `prompts/codex-verifier-prompt.md`
- `state/README.md`
- `state/schema/*.schema.json`

**Step 2: Update todo tracking**

Run: `sed -n '1,260p' tasks/todo.md`
Expected: existing checklist is visible and ready to append implementation items.

**Step 3: Mark planning complete**

Run: `sed -n '1,260p' docs/plans/2026-03-10-riscv-gap-assets-implementation.md`
Expected: plan header and task sections render correctly.

### Task 2: Workflow Markdown Templates

**Files:**
- Create: `templates/issue-template.md`
- Create: `templates/design-template.md`
- Test: `templates/issue-template.md`
- Test: `templates/design-template.md`

**Step 1: Write the issue template**

Include sections for problem statement, parity evidence, repro, impact, acceptance criteria, and related lore threads.

**Step 2: Write the design template**

Include sections for root cause, options, files to touch, test matrix, risks, rollback, and DoD.

**Step 3: Verify both files exist**

Run: `find templates -maxdepth 1 -type f | sort`
Expected: both markdown template files are listed.

### Task 3: Agent Prompt Templates

**Files:**
- Create: `prompts/claude-planner-prompt.md`
- Create: `prompts/codex-implementer-prompt.md`
- Create: `prompts/codex-verifier-prompt.md`
- Test: `prompts/claude-planner-prompt.md`
- Test: `prompts/codex-implementer-prompt.md`
- Test: `prompts/codex-verifier-prompt.md`

**Step 1: Write the Claude planner prompt**

Define required inputs, required outputs, constraints, and explicit references to `templates/design-template.md`.

**Step 2: Write the Codex implementer prompt**

Define worktree rules, implementation loop, test expectations, failure handling, and output contract.

**Step 3: Write the Codex verifier prompt**

Define independent verification rules, blocking findings format, and pass/fail output JSON contract.

**Step 4: Verify files exist**

Run: `find prompts -maxdepth 1 -type f | sort`
Expected: three prompt templates are listed.

### Task 4: State Schemas

**Files:**
- Create: `state/README.md`
- Create: `state/schema/gaps.repo.schema.json`
- Create: `state/schema/gaps.mail.schema.json`
- Create: `state/schema/gap_backlog.schema.json`
- Create: `state/schema/issues.schema.json`
- Create: `state/schema/claimed.schema.json`
- Create: `state/schema/review_todos.schema.json`
- Create: `state/schema/verification.schema.json`
- Test: `state/schema/*.schema.json`

**Step 1: Write schema overview**

Document each state file, its owner agent, and when it is updated.

**Step 2: Write repository and mail evidence schemas**

Define entry arrays for code parity findings and mailing-list threads with stable IDs and timestamps.

**Step 3: Write backlog and issue lifecycle schemas**

Define normalized gap items, issue creation results, claim state, and review TODOs.

**Step 4: Write verification schema**

Define build/test/perf booleans, artifact links, and blocking findings.

**Step 5: Validate JSON syntax**

Run: `python3 - <<'PY'\nimport glob, json\nfor path in sorted(glob.glob('state/schema/*.json')):\n    with open(path) as f:\n        json.load(f)\n    print(path)\nPY`
Expected: every schema file path is printed with no exception.

### Task 5: Documentation And Final Verification

**Files:**
- Modify: `docs/plans/2026-03-10-riscv-gap-multi-agent-design.md`
- Modify: `tasks/todo.md`
- Test: `docs/plans/2026-03-10-riscv-gap-multi-agent-design.md`
- Test: `configs/workflow.example.yaml`
- Test: `state/schema/*.schema.json`

**Step 1: Update the design doc**

Add references to the new `templates/`, `prompts/`, and `state/schema/` assets so readers can discover executable artifacts.

**Step 2: Update review notes**

Append generated files and validation commands to `tasks/todo.md`.

**Step 3: Run full asset validation**

Run: `python3 - <<'PY'\nimport glob, json, yaml\nyaml.safe_load(open('configs/workflow.example.yaml'))\nfor path in sorted(glob.glob('state/schema/*.json')):\n    json.load(open(path))\nprint('asset-validation-ok')\nPY`
Expected: `asset-validation-ok`

**Step 4: Spot-check section coverage**

Run: `rg -n \"templates/|prompts/|state/schema|issue-template|design-template\" docs/plans/2026-03-10-riscv-gap-multi-agent-design.md`
Expected: the design doc points to the generated assets.
