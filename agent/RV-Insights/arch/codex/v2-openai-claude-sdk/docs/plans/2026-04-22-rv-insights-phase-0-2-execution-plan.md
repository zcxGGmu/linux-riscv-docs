# RV-Insights Phase 0-2 Execution Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Execute `RV-Insights` foundation work for `Phase 0` to `Phase 2` in a strict order so the repository skeleton, core contracts, and persistence layer are all in place and fully test-verified before higher layers begin.

**Architecture:** This execution plan covers only the foundation stack: repository scaffolding, Python/tooling configuration, contract schemas, ORM models, and database migration setup. The plan intentionally delays workflow orchestration, APIs, and agent runtimes until the underlying structure and persistence primitives are stable and passing tests.

**Tech Stack:** Python 3.12, pytest, Pydantic, SQLAlchemy, Alembic, PostgreSQL, FastAPI project scaffolding

---

## Scope

This plan executes only these phases from the detailed checklist:

- `Phase 0: Project Bootstrap and Delivery Guardrails`
- `Phase 1: Core Domain Enums and Contracts`
- `Phase 2: Persistence Models and Database Foundation`

Out of scope for this plan:

- artifact store implementation
- workflow engine implementation
- API routes
- queueing or workers
- OpenAI / Claude SDK integration
- frontend work

## Execution Rules

- Do not start the next task until the current task's targeted test passes.
- After finishing each day block, run the full suite for the covered area, not just the single targeted test.
- If a contract changes, rerun the full `tests/core_models` suite before moving on.
- If a model changes, rerun both the direct model test and the relevant migration or session tests.
- If a later task reveals a flaw in an earlier task, fix the earlier task immediately and rerun all impacted suites.

## Recommended Delivery Rhythm

- `Day 1`: repository and tooling baseline
- `Day 2`: stage enums and shared/base contracts
- `Day 3`: remaining stage contracts and contract-wide verification
- `Day 4`: ORM models and support models
- `Day 5`: database session and Alembic migration, followed by phase exit verification

If velocity is lower than expected, keep the sequence but shorten the daily scope. Do not collapse verification gates.

## Task Dependency Map

```text
0.1 -> 0.2 -> 0.3 -> 0.4
0.4 -> 1.1 -> 1.2
1.2 -> 1.3 -> 1.4 -> 1.5 -> 1.6 -> 1.7 -> 1.8
1.8 -> 2.1 -> 2.2 -> 2.3 -> 2.4 -> 2.5 -> 2.6 -> 2.7
```

## Day 1: Repository and Tooling Baseline

### Task 1: Establish repository directory skeleton

**References:**
- Checklist task: `0.1`

**Files:**
- Create: `apps/orchestrator-api/app/__init__.py`
- Create: `apps/orchestrator-api/app/api/__init__.py`
- Create: `apps/approval-console/README.md`
- Create: `services/explorer-agent/__init__.py`
- Create: `services/planner-agent/__init__.py`
- Create: `services/reviewer-agent/__init__.py`
- Create: `services/claude-dev-worker/__init__.py`
- Create: `services/test-runner/__init__.py`
- Create: `packages/core-models/__init__.py`
- Create: `packages/workflow-engine/__init__.py`
- Create: `packages/sdk-adapters/__init__.py`
- Create: `packages/artifact-store/__init__.py`
- Create: `packages/observability/__init__.py`
- Test: `tests/smoke/test_repository_layout.py`

**Step 1: Write the failing test**

Write a smoke test that asserts the expected repository directories and package entry files exist.

**Step 2: Run test to verify it fails**

Run: `pytest tests/smoke/test_repository_layout.py -v`
Expected: FAIL because the directories and package files do not exist yet.

**Step 3: Write minimal implementation**

Create only the directories and package markers needed by the architecture.

**Step 4: Run test to verify it passes**

Run: `pytest tests/smoke/test_repository_layout.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps services packages tests
git commit -m "chore: scaffold repository layout"
```

### Task 2: Add Python workspace metadata and toolchain config

**References:**
- Checklist task: `0.2`

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `pytest.ini`
- Create: `.gitignore`
- Test: `tests/smoke/test_pyproject_metadata.py`

**Step 1: Write the failing test**

Write a smoke test that checks the presence and basic parseability of `pyproject.toml` and `pytest.ini`.

**Step 2: Run test to verify it fails**

Run: `pytest tests/smoke/test_pyproject_metadata.py -v`
Expected: FAIL because the config files do not exist.

**Step 3: Write minimal implementation**

Add:

- project metadata
- Python version pin
- pytest discovery configuration
- ignore rules for build output, virtualenvs, artifacts, logs, and temporary workspaces

**Step 4: Run test to verify it passes**

Run: `pytest tests/smoke/test_pyproject_metadata.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml .python-version pytest.ini .gitignore tests/smoke
git commit -m "chore: add python workspace metadata"
```

### Task 3: Add local developer commands and Makefile targets

**References:**
- Checklist task: `0.3`

**Files:**
- Create: `Makefile`
- Create: `scripts/README.md`
- Test: `tests/smoke/test_make_targets.py`

**Step 1: Write the failing test**

Write a smoke test that asserts the Makefile contains `test`, `lint`, `format`, `run-api`, and `run-worker` targets.

**Step 2: Run test to verify it fails**

Run: `pytest tests/smoke/test_make_targets.py -v`
Expected: FAIL because the Makefile does not exist.

**Step 3: Write minimal implementation**

Create a Makefile with those targets and document them in `scripts/README.md`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/smoke/test_make_targets.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add Makefile scripts/README.md tests/smoke
git commit -m "chore: add developer make targets"
```

### Task 4: Add baseline CI workflow shape

**References:**
- Checklist task: `0.4`

**Files:**
- Create: `.github/workflows/ci.yml`
- Test: `tests/smoke/test_ci_workflow.py`

**Step 1: Write the failing test**

Write a smoke test that checks the CI workflow exists and contains basic install, lint, and test jobs.

**Step 2: Run test to verify it fails**

Run: `pytest tests/smoke/test_ci_workflow.py -v`
Expected: FAIL because the workflow file does not exist.

**Step 3: Write minimal implementation**

Add a baseline GitHub Actions workflow that reflects the local developer commands.

**Step 4: Run test to verify it passes**

Run: `pytest tests/smoke/test_ci_workflow.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add .github/workflows/ci.yml tests/smoke
git commit -m "chore: add baseline ci workflow"
```

### Day 1 checkpoint

Run:

```bash
pytest tests/smoke -v
```

Expected:

- all Phase 0 smoke tests PASS
- repository can serve as a stable base for schema work

Do not start Day 2 until this suite passes.

## Day 2: Shared Contracts and Early Core Schemas

### Task 5: Define workflow stage enums

**References:**
- Checklist task: `1.1`

**Files:**
- Create: `packages/core-models/enums.py`
- Test: `tests/core_models/test_stage_enums.py`

**Step 1: Write the failing test**

Write tests asserting valid stage enum values and invalid value rejection.

**Step 2: Run test to verify it fails**

Run: `pytest tests/core_models/test_stage_enums.py -v`
Expected: FAIL because enums are not implemented.

**Step 3: Write minimal implementation**

Add stage and status enums only; do not mix in schema logic yet.

**Step 4: Run test to verify it passes**

Run: `pytest tests/core_models/test_stage_enums.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core-models/enums.py tests/core_models
git commit -m "feat: add workflow stage enums"
```

### Task 6: Define common artifact envelope schema

**References:**
- Checklist task: `1.2`

**Files:**
- Create: `packages/core-models/contracts/common.py`
- Test: `tests/core_models/test_common_artifact_envelope.py`

**Step 1: Write the failing test**

Write tests for a valid shared envelope and for missing required metadata.

**Step 2: Run test to verify it fails**

Run: `pytest tests/core_models/test_common_artifact_envelope.py -v`
Expected: FAIL because the shared artifact envelope does not exist.

**Step 3: Write minimal implementation**

Add the shared artifact envelope schema with only the required fields and validation.

**Step 4: Run test to verify it passes**

Run: `pytest tests/core_models/test_common_artifact_envelope.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core-models/contracts/common.py tests/core_models
git commit -m "feat: add shared artifact envelope schema"
```

### Task 7: Define explorer contracts

**References:**
- Checklist task: `1.3`

**Files:**
- Create: `packages/core-models/contracts/explore.py`
- Test: `tests/core_models/test_explore_contracts.py`

**Step 1: Write the failing test**

Write tests for valid explorer input, valid evidence items, and invalid feasibility scores.

**Step 2: Run test to verify it fails**

Run: `pytest tests/core_models/test_explore_contracts.py -v`
Expected: FAIL because explorer contracts are not implemented.

**Step 3: Write minimal implementation**

Define explorer input, evidence item, and recommended candidate output schemas.

**Step 4: Run test to verify it passes**

Run: `pytest tests/core_models/test_explore_contracts.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core-models/contracts/explore.py tests/core_models
git commit -m "feat: add explorer contracts"
```

### Task 8: Define planner contracts

**References:**
- Checklist task: `1.4`

**Files:**
- Create: `packages/core-models/contracts/plan.py`
- Test: `tests/core_models/test_plan_contracts.py`

**Step 1: Write the failing test**

Write tests for required target files, change steps, and test instructions in the planner output.

**Step 2: Run test to verify it fails**

Run: `pytest tests/core_models/test_plan_contracts.py -v`
Expected: FAIL because planner contracts are not implemented.

**Step 3: Write minimal implementation**

Define implementation plan and test plan schemas.

**Step 4: Run test to verify it passes**

Run: `pytest tests/core_models/test_plan_contracts.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core-models/contracts/plan.py tests/core_models
git commit -m "feat: add planner contracts"
```

### Day 2 checkpoint

Run:

```bash
pytest tests/core_models/test_stage_enums.py \
       tests/core_models/test_common_artifact_envelope.py \
       tests/core_models/test_explore_contracts.py \
       tests/core_models/test_plan_contracts.py -v
```

Expected:

- all enum and early contract tests PASS
- no schema import or dependency-cycle issues

## Day 3: Remaining Stage Contracts and Contract Suite Lock

### Task 9: Define developer contracts

**References:**
- Checklist task: `1.5`

**Files:**
- Create: `packages/core-models/contracts/develop.py`
- Test: `tests/core_models/test_develop_contracts.py`

**Step 1: Write the failing test**

Write tests asserting commit hash, diff artifact, and self-check metadata are required.

**Step 2: Run test to verify it fails**

Run: `pytest tests/core_models/test_develop_contracts.py -v`
Expected: FAIL because developer contracts are not implemented.

**Step 3: Write minimal implementation**

Define the developer request and result schema with only required fields.

**Step 4: Run test to verify it passes**

Run: `pytest tests/core_models/test_develop_contracts.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core-models/contracts/develop.py tests/core_models
git commit -m "feat: add developer contracts"
```

### Task 10: Define reviewer contracts

**References:**
- Checklist task: `1.6`

**Files:**
- Create: `packages/core-models/contracts/review.py`
- Test: `tests/core_models/test_review_contracts.py`

**Step 1: Write the failing test**

Write tests covering valid issue payloads and invalid severity values.

**Step 2: Run test to verify it fails**

Run: `pytest tests/core_models/test_review_contracts.py -v`
Expected: FAIL because reviewer contracts are not implemented.

**Step 3: Write minimal implementation**

Define review issue and review decision schemas.

**Step 4: Run test to verify it passes**

Run: `pytest tests/core_models/test_review_contracts.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core-models/contracts/review.py tests/core_models
git commit -m "feat: add reviewer contracts"
```

### Task 11: Define test runner contracts

**References:**
- Checklist task: `1.7`

**Files:**
- Create: `packages/core-models/contracts/testing.py`
- Test: `tests/core_models/test_testing_contracts.py`

**Step 1: Write the failing test**

Write tests for environment manifest requirements and test execution result shape.

**Step 2: Run test to verify it fails**

Run: `pytest tests/core_models/test_testing_contracts.py -v`
Expected: FAIL because testing contracts are not implemented.

**Step 3: Write minimal implementation**

Define environment manifest, command result, and final test result schemas.

**Step 4: Run test to verify it passes**

Run: `pytest tests/core_models/test_testing_contracts.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core-models/contracts/testing.py tests/core_models
git commit -m "feat: add testing contracts"
```

### Task 12: Define failure artifact contract

**References:**
- Checklist task: `1.8`

**Files:**
- Create: `packages/core-models/contracts/failure.py`
- Test: `tests/core_models/test_failure_contracts.py`

**Step 1: Write the failing test**

Write tests for valid failure artifacts and invalid next-action values.

**Step 2: Run test to verify it fails**

Run: `pytest tests/core_models/test_failure_contracts.py -v`
Expected: FAIL because failure artifact contracts are not implemented.

**Step 3: Write minimal implementation**

Define the failure artifact schema and keep allowed failure types explicit.

**Step 4: Run test to verify it passes**

Run: `pytest tests/core_models/test_failure_contracts.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core-models/contracts/failure.py tests/core_models
git commit -m "feat: add failure artifact contract"
```

### Day 3 checkpoint

Run:

```bash
pytest tests/core_models -v
```

Expected:

- all core contract and enum tests PASS
- contract layer is stable enough for ORM model work

Do not begin Phase 2 model work until the full `tests/core_models` suite passes.

## Day 4: Core ORM Models

### Task 13: Define `ContributionTask` ORM model

**References:**
- Checklist task: `2.1`

**Files:**
- Create: `packages/core-models/models/task.py`
- Test: `tests/db/test_task_model.py`

**Step 1: Write the failing test**

Write tests for task model creation, expected columns, and default status behavior.

**Step 2: Run test to verify it fails**

Run: `pytest tests/db/test_task_model.py -v`
Expected: FAIL because the task ORM model does not exist.

**Step 3: Write minimal implementation**

Define `ContributionTask` with only the documented core fields and indexes.

**Step 4: Run test to verify it passes**

Run: `pytest tests/db/test_task_model.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core-models/models/task.py tests/db
git commit -m "feat: add contribution task orm model"
```

### Task 14: Define `StageRun` ORM model

**References:**
- Checklist task: `2.2`

**Files:**
- Create: `packages/core-models/models/stage_run.py`
- Test: `tests/db/test_stage_run_model.py`

**Step 1: Write the failing test**

Write tests for stage attempt ordering, relation to task, and runtime metadata fields.

**Step 2: Run test to verify it fails**

Run: `pytest tests/db/test_stage_run_model.py -v`
Expected: FAIL because the stage run model does not exist.

**Step 3: Write minimal implementation**

Define `StageRun` with foreign key link to `ContributionTask`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/db/test_stage_run_model.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core-models/models/stage_run.py tests/db
git commit -m "feat: add stage run orm model"
```

### Task 15: Define `ApprovalRecord` ORM model

**References:**
- Checklist task: `2.3`

**Files:**
- Create: `packages/core-models/models/approval.py`
- Test: `tests/db/test_approval_model.py`

**Step 1: Write the failing test**

Write tests for approval ownership, reason type persistence, and structured must-fix data.

**Step 2: Run test to verify it fails**

Run: `pytest tests/db/test_approval_model.py -v`
Expected: FAIL because the approval model does not exist.

**Step 3: Write minimal implementation**

Define `ApprovalRecord` with relation to `StageRun`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/db/test_approval_model.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core-models/models/approval.py tests/db
git commit -m "feat: add approval record orm model"
```

### Task 16: Define `Artifact` ORM model

**References:**
- Checklist task: `2.4`

**Files:**
- Create: `packages/core-models/models/artifact.py`
- Test: `tests/db/test_artifact_model.py`

**Step 1: Write the failing test**

Write tests for artifact ownership, versioning, and indexable metadata fields.

**Step 2: Run test to verify it fails**

Run: `pytest tests/db/test_artifact_model.py -v`
Expected: FAIL because the artifact model does not exist.

**Step 3: Write minimal implementation**

Define `Artifact` with task and stage associations, storage URI, type, version, and summary.

**Step 4: Run test to verify it passes**

Run: `pytest tests/db/test_artifact_model.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core-models/models/artifact.py tests/db
git commit -m "feat: add artifact orm model"
```

### Task 17: Define support models

**References:**
- Checklist task: `2.5`

**Files:**
- Create: `packages/core-models/models/repository_profile.py`
- Create: `packages/core-models/models/workspace_lease.py`
- Create: `packages/core-models/models/environment_snapshot.py`
- Test: `tests/db/test_support_models.py`

**Step 1: Write the failing test**

Write tests for repository profile fields, workspace lease ownership, TTL behavior fields, and environment snapshot identity fields.

**Step 2: Run test to verify it fails**

Run: `pytest tests/db/test_support_models.py -v`
Expected: FAIL because the support models do not exist.

**Step 3: Write minimal implementation**

Define the support models with only documented MVP fields.

**Step 4: Run test to verify it passes**

Run: `pytest tests/db/test_support_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core-models/models/repository_profile.py \
        packages/core-models/models/workspace_lease.py \
        packages/core-models/models/environment_snapshot.py \
        tests/db
git commit -m "feat: add repository and lease support models"
```

### Day 4 checkpoint

Run:

```bash
pytest tests/db/test_task_model.py \
       tests/db/test_stage_run_model.py \
       tests/db/test_approval_model.py \
       tests/db/test_artifact_model.py \
       tests/db/test_support_models.py -v
```

Expected:

- all current ORM model tests PASS
- relationship and field definitions are stable enough for session and migration setup

## Day 5: Database Session and Migration Readiness

### Task 18: Add SQLAlchemy base and session factory

**References:**
- Checklist task: `2.6`

**Files:**
- Create: `packages/core-models/db/base.py`
- Create: `packages/core-models/db/session.py`
- Test: `tests/db/test_session_factory.py`

**Step 1: Write the failing test**

Write tests that create a test engine and open/close a database session successfully.

**Step 2: Run test to verify it fails**

Run: `pytest tests/db/test_session_factory.py -v`
Expected: FAIL because the session factory does not exist.

**Step 3: Write minimal implementation**

Implement the declarative base and engine/session helpers.

**Step 4: Run test to verify it passes**

Run: `pytest tests/db/test_session_factory.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core-models/db/base.py packages/core-models/db/session.py tests/db
git commit -m "feat: add sqlalchemy base and session factory"
```

### Task 19: Add Alembic configuration and initial migration

**References:**
- Checklist task: `2.7`

**Files:**
- Create: `infra/migrations/alembic.ini`
- Create: `infra/migrations/env.py`
- Create: `infra/migrations/versions/0001_initial_schema.py`
- Test: `tests/db/test_initial_migration.py`

**Step 1: Write the failing test**

Write a test that applies the initial migration against a fresh test database.

**Step 2: Run test to verify it fails**

Run: `pytest tests/db/test_initial_migration.py -v`
Expected: FAIL because Alembic configuration and migration files do not exist.

**Step 3: Write minimal implementation**

Add Alembic environment config and the first migration containing all Phase 2 models.

**Step 4: Run test to verify it passes**

Run: `pytest tests/db/test_initial_migration.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add infra/migrations tests/db
git commit -m "feat: add initial database migration"
```

### Task 20: Run full Phase 0-2 regression gate

**References:**
- Checklist tasks: `0.1` to `2.7`

**Files:**
- No new files required
- Test: `tests/smoke`
- Test: `tests/core_models`
- Test: `tests/db`

**Step 1: Run focused smoke and contract suites**

Run:

```bash
pytest tests/smoke tests/core_models tests/db -v
```

Expected: all suites PASS

**Step 2: Fix any regressions immediately**

Do not proceed if any smoke, contract, model, or migration test fails.

**Step 3: Record the phase exit review**

Update the working review notes or task tracking with:

- passing suites
- known follow-up issues
- whether Phase 3 can begin

**Step 4: Commit**

```bash
git add tasks/todo.md docs/plans
git commit -m "docs: record phase 0 to 2 execution gate"
```

## Phase Exit Criteria

Phase 0 to Phase 2 are complete only if all of the following are true:

- `tests/smoke -v` passes
- `tests/core_models -v` passes
- `tests/db -v` passes
- the initial migration applies successfully on a fresh database
- all Phase 0 to Phase 2 files exist in the expected paths
- no unresolved contract shape disagreement remains between docs and code

## Handoff To Phase 3

Only begin `Phase 3: Artifact Store, Trace Store, and Local Persistence Helpers` if:

- the full Phase 0-2 regression gate passes
- migration and session helpers are stable
- task tracking notes clearly indicate the foundation layer is complete

## Suggested Daily Review Questions

At the end of each working day, answer:

1. Which tasks were completed and which test suites passed?
2. Did any contract or model change force a regression in an earlier task?
3. Are there any naming, schema, or package layout issues that should be corrected before moving on?
4. Is the next day blocked by missing tooling, flaky tests, or unresolved design ambiguity?

Plan complete and saved to `docs/plans/2026-04-22-rv-insights-phase-0-2-execution-plan.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
