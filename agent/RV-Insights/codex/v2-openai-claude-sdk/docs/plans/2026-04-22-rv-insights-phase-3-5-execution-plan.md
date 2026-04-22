# RV-Insights Phase 3-5 Execution Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Execute `RV-Insights` storage, workflow engine, and orchestrator API work for `Phase 3` to `Phase 5` in a strict order so artifact persistence, state transitions, and API surfaces are all stable and test-verified before queueing, worker callbacks, and SDK integration begin.

**Architecture:** This execution plan assumes `Phase 0` to `Phase 2` are already complete and passing. It builds upward in three layers: local artifact and trace persistence, orchestration state and transition services, and the FastAPI application surface that exposes task, stage, approval, and artifact operations.

**Tech Stack:** Python 3.12, pytest, Pydantic, SQLAlchemy, FastAPI, httpx, local filesystem storage, PostgreSQL-backed metadata

---

## Scope

This plan executes only these phases from the detailed checklist:

- `Phase 3: Artifact Store, Trace Store, and Local Persistence Helpers`
- `Phase 4: Workflow State Machine and Core Orchestrator Logic`
- `Phase 5: Orchestrator API and Application Wiring`

Out of scope for this plan:

- queue broker implementation
- worker callbacks
- OpenAI / Claude runner integration
- explorer, planner, reviewer, developer, and test-runner services
- approval console frontend
- end-to-end cross-service execution

## Preconditions

Do not start this plan until all `Phase 0 - Phase 2` exit criteria are true:

- `tests/smoke -v` passes
- `tests/core_models -v` passes
- `tests/db -v` passes
- the initial migration applies successfully on a fresh database

## Execution Rules

- Do not begin any `Phase 4` task until all `Phase 3` tests pass.
- Do not begin any `Phase 5` endpoint task until the relevant orchestration service it depends on has passing tests.
- After completing each day block, run the full suite for that block, not only the last task's test.
- If a service change affects persistence assumptions, rerun both the direct workflow test and the artifact or database suite it depends on.
- Treat API route tests as integration boundaries; if one fails because of an underlying service issue, fix the service and rerun its direct tests before retrying the API suite.

## Recommended Delivery Rhythm

- `Day 6`: artifact pathing, local artifact IO, metadata persistence
- `Day 7`: trace storage and workflow state machine foundation
- `Day 8`: workflow services for task creation, advancement, rework, and failure handling
- `Day 9`: FastAPI bootstrap and task or approval API surface
- `Day 10`: remaining API routes and full Phase 3-5 regression gate

Keep the order fixed even if staffing changes. These layers depend on one another.

## Task Dependency Map

```text
3.1 -> 3.2 -> 3.3 -> 3.4
3.4 -> 4.1 -> 4.2 -> 4.3 -> 4.4 -> 4.5 -> 4.6
4.6 -> 5.1 -> 5.2 -> 5.3 -> 5.4 -> 5.5 -> 5.6
```

## Day 6: Artifact and Trace Persistence Foundation

### Task 21: Add deterministic local artifact path builder

**References:**
- Checklist task: `3.1`

**Files:**
- Create: `packages/artifact-store/pathing.py`
- Test: `tests/artifacts/test_artifact_pathing.py`

**Step 1: Write the failing test**

Write tests that assert generated artifact paths include task, stage, attempt, and version components and are deterministic.

**Step 2: Run test to verify it fails**

Run: `pytest tests/artifacts/test_artifact_pathing.py -v`
Expected: FAIL because the artifact path builder does not exist.

**Step 3: Write minimal implementation**

Implement deterministic path generation only. Do not add write logic yet.

**Step 4: Run test to verify it passes**

Run: `pytest tests/artifacts/test_artifact_pathing.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/artifact-store/pathing.py tests/artifacts
git commit -m "feat: add deterministic artifact path builder"
```

### Task 22: Add local artifact write and read helpers

**References:**
- Checklist task: `3.2`

**Files:**
- Create: `packages/artifact-store/store.py`
- Test: `tests/artifacts/test_local_artifact_store.py`

**Step 1: Write the failing test**

Write tests for writing text and JSON artifacts and reading them back by metadata or path reference.

**Step 2: Run test to verify it fails**

Run: `pytest tests/artifacts/test_local_artifact_store.py -v`
Expected: FAIL because the local artifact store does not exist.

**Step 3: Write minimal implementation**

Add text and JSON write helpers plus a minimal read helper, using the deterministic path builder from Task 21.

**Step 4: Run test to verify it passes**

Run: `pytest tests/artifacts/test_local_artifact_store.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/artifact-store/store.py tests/artifacts
git commit -m "feat: add local artifact read and write helpers"
```

### Task 23: Add artifact metadata service

**References:**
- Checklist task: `3.3`

**Files:**
- Create: `packages/artifact-store/metadata_service.py`
- Test: `tests/artifacts/test_metadata_service.py`

**Step 1: Write the failing test**

Write tests that ensure writing an artifact also creates a database metadata record linked to its storage location.

**Step 2: Run test to verify it fails**

Run: `pytest tests/artifacts/test_metadata_service.py -v`
Expected: FAIL because the metadata service does not exist.

**Step 3: Write minimal implementation**

Implement metadata persistence that links the local artifact file to the `Artifact` ORM model.

**Step 4: Run test to verify it passes**

Run: `pytest tests/artifacts/test_metadata_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/artifact-store/metadata_service.py tests/artifacts
git commit -m "feat: add artifact metadata service"
```

### Task 24: Add trace event model and storage helper

**References:**
- Checklist task: `3.4`

**Files:**
- Create: `packages/observability/traces.py`
- Test: `tests/observability/test_trace_store.py`

**Step 1: Write the failing test**

Write tests that normalize trace payloads and persist them to a local or fallback store.

**Step 2: Run test to verify it fails**

Run: `pytest tests/observability/test_trace_store.py -v`
Expected: FAIL because trace storage helpers do not exist.

**Step 3: Write minimal implementation**

Add normalized trace payload structure and minimal persistence helpers.

**Step 4: Run test to verify it passes**

Run: `pytest tests/observability/test_trace_store.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/observability/traces.py tests/observability
git commit -m "feat: add trace storage helper"
```

### Day 6 checkpoint

Run:

```bash
pytest tests/artifacts tests/observability/test_trace_store.py -v
```

Expected:

- all artifact persistence tests PASS
- trace payloads are normalized and retrievable

Do not begin Day 7 until this suite passes.

## Day 7: Workflow State and Command Foundation

### Task 25: Implement allowed state transitions

**References:**
- Checklist task: `4.1`

**Files:**
- Create: `packages/workflow-engine/state_machine.py`
- Test: `tests/workflow/test_state_machine.py`

**Step 1: Write the failing test**

Write tests for valid transitions and explicit failure on illegal transitions.

**Step 2: Run test to verify it fails**

Run: `pytest tests/workflow/test_state_machine.py -v`
Expected: FAIL because the workflow state machine does not exist.

**Step 3: Write minimal implementation**

Implement only the documented transition map for approve, rework, abort, fail, and retry.

**Step 4: Run test to verify it passes**

Run: `pytest tests/workflow/test_state_machine.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/workflow-engine/state_machine.py tests/workflow
git commit -m "feat: add workflow state machine"
```

### Task 26: Add stage command abstraction

**References:**
- Checklist task: `4.2`

**Files:**
- Create: `packages/workflow-engine/commands.py`
- Test: `tests/workflow/test_stage_commands.py`

**Step 1: Write the failing test**

Write tests that validate task ID, stage run ID, attempt number, contract references, and timeout budget on a stage command.

**Step 2: Run test to verify it fails**

Run: `pytest tests/workflow/test_stage_commands.py -v`
Expected: FAIL because the command abstraction does not exist.

**Step 3: Write minimal implementation**

Add a typed command object only; do not dispatch it yet.

**Step 4: Run test to verify it passes**

Run: `pytest tests/workflow/test_stage_commands.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/workflow-engine/commands.py tests/workflow
git commit -m "feat: add stage command abstraction"
```

### Task 27: Add workflow service to create tasks

**References:**
- Checklist task: `4.3`

**Files:**
- Create: `packages/workflow-engine/task_service.py`
- Test: `tests/workflow/test_task_creation_service.py`

**Step 1: Write the failing test**

Write tests that create a task and confirm initial stage and status are correct and no approval gate is skipped.

**Step 2: Run test to verify it fails**

Run: `pytest tests/workflow/test_task_creation_service.py -v`
Expected: FAIL because the task service does not exist.

**Step 3: Write minimal implementation**

Implement a task creation service that uses the ORM models and initializes the first stage run.

**Step 4: Run test to verify it passes**

Run: `pytest tests/workflow/test_task_creation_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/workflow-engine/task_service.py tests/workflow
git commit -m "feat: add task creation service"
```

### Day 7 checkpoint

Run:

```bash
pytest tests/workflow/test_state_machine.py \
       tests/workflow/test_stage_commands.py \
       tests/workflow/test_task_creation_service.py -v
```

Expected:

- core transition logic and stage command modeling PASS
- task creation path is stable enough to support advancement services

## Day 8: Workflow Services and Recovery Semantics

### Task 28: Add stage advancement service

**References:**
- Checklist task: `4.4`

**Files:**
- Create: `packages/workflow-engine/advance_service.py`
- Test: `tests/workflow/test_stage_advancement.py`

**Step 1: Write the failing test**

Write tests that allow advancement only from valid approved stages and ensure stage ownership remains in the orchestrator.

**Step 2: Run test to verify it fails**

Run: `pytest tests/workflow/test_stage_advancement.py -v`
Expected: FAIL because the advancement service does not exist.

**Step 3: Write minimal implementation**

Implement valid advancement logic only; do not mix in rework or failure rules.

**Step 4: Run test to verify it passes**

Run: `pytest tests/workflow/test_stage_advancement.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/workflow-engine/advance_service.py tests/workflow
git commit -m "feat: add stage advancement service"
```

### Task 29: Add rework and rollback service

**References:**
- Checklist task: `4.5`

**Files:**
- Create: `packages/workflow-engine/rework_service.py`
- Test: `tests/workflow/test_rework_and_rollback.py`

**Step 1: Write the failing test**

Write tests for `rework_current_stage`, `reopen_previous_stage`, and `restart_from_plan`, ensuring old attempts are preserved.

**Step 2: Run test to verify it fails**

Run: `pytest tests/workflow/test_rework_and_rollback.py -v`
Expected: FAIL because the rework service does not exist.

**Step 3: Write minimal implementation**

Implement new-attempt semantics and reference preservation for old artifacts.

**Step 4: Run test to verify it passes**

Run: `pytest tests/workflow/test_rework_and_rollback.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/workflow-engine/rework_service.py tests/workflow
git commit -m "feat: add rework and rollback service"
```

### Task 30: Add failure classification service

**References:**
- Checklist task: `4.6`

**Files:**
- Create: `packages/workflow-engine/failure_service.py`
- Test: `tests/workflow/test_failure_classification.py`

**Step 1: Write the failing test**

Write tests for transient, deterministic, and governance failure classification and next-action recommendations.

**Step 2: Run test to verify it fails**

Run: `pytest tests/workflow/test_failure_classification.py -v`
Expected: FAIL because the failure service does not exist.

**Step 3: Write minimal implementation**

Implement only the documented failure classes and retry recommendations.

**Step 4: Run test to verify it passes**

Run: `pytest tests/workflow/test_failure_classification.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/workflow-engine/failure_service.py tests/workflow
git commit -m "feat: add failure classification service"
```

### Task 31: Run full workflow engine regression gate

**References:**
- Checklist tasks: `4.1` to `4.6`

**Files:**
- No new files required
- Test: `tests/workflow`

**Step 1: Run the workflow suite**

Run:

```bash
pytest tests/workflow -v
```

Expected: all workflow tests PASS

**Step 2: Fix cross-service regressions**

If a task service, advancement rule, or rollback behavior regresses another workflow test, fix the underlying service before moving to API wiring.

**Step 3: Commit**

```bash
git add packages/workflow-engine tests/workflow
git commit -m "test: verify workflow engine regression gate"
```

## Day 9: FastAPI Bootstrap and Core Task APIs

### Task 32: Add FastAPI app bootstrap

**References:**
- Checklist task: `5.1`

**Files:**
- Create: `apps/orchestrator-api/app/main.py`
- Test: `tests/api/test_app_boot.py`

**Step 1: Write the failing test**

Write tests for application startup and a health endpoint.

**Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_app_boot.py -v`
Expected: FAIL because the FastAPI app bootstrap does not exist.

**Step 3: Write minimal implementation**

Create the FastAPI app and a health route only.

**Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_app_boot.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/orchestrator-api/app/main.py tests/api
git commit -m "feat: add orchestrator api bootstrap"
```

### Task 33: Add `POST /tasks`

**References:**
- Checklist task: `5.2`

**Files:**
- Create: `apps/orchestrator-api/app/api/tasks.py`
- Create: `apps/orchestrator-api/app/schemas/tasks.py`
- Test: `tests/api/test_create_task_api.py`

**Step 1: Write the failing test**

Write API tests for task creation request and response behavior.

**Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_create_task_api.py -v`
Expected: FAIL because the endpoint does not exist.

**Step 3: Write minimal implementation**

Wire `POST /tasks` to the task creation service with request and response schemas.

**Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_create_task_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/orchestrator-api/app/api/tasks.py \
        apps/orchestrator-api/app/schemas/tasks.py \
        tests/api
git commit -m "feat: add create task api"
```

### Task 34: Add `GET /tasks/{task_id}`

**References:**
- Checklist task: `5.3`

**Files:**
- Modify: `apps/orchestrator-api/app/api/tasks.py`
- Test: `tests/api/test_get_task_api.py`

**Step 1: Write the failing test**

Write API tests for returning task state, stage, attempt, and summary artifact references.

**Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_get_task_api.py -v`
Expected: FAIL because the endpoint does not exist.

**Step 3: Write minimal implementation**

Add a task detail lookup endpoint using the task service and persistence layer.

**Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_get_task_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/orchestrator-api/app/api/tasks.py tests/api
git commit -m "feat: add get task api"
```

### Task 35: Add approval endpoints

**References:**
- Checklist task: `5.4`

**Files:**
- Create: `apps/orchestrator-api/app/api/approvals.py`
- Create: `apps/orchestrator-api/app/schemas/approvals.py`
- Test: `tests/api/test_approval_api.py`

**Step 1: Write the failing test**

Write API tests for approve, rework, and abort flows, including stale attempt rejection and idempotency behavior.

**Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_approval_api.py -v`
Expected: FAIL because approval endpoints do not exist.

**Step 3: Write minimal implementation**

Add approval endpoints and connect them to workflow services while enforcing `stage_run_id` and `attempt`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_approval_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/orchestrator-api/app/api/approvals.py \
        apps/orchestrator-api/app/schemas/approvals.py \
        tests/api
git commit -m "feat: add approval api"
```

### Day 9 checkpoint

Run:

```bash
pytest tests/api/test_app_boot.py \
       tests/api/test_create_task_api.py \
       tests/api/test_get_task_api.py \
       tests/api/test_approval_api.py -v
```

Expected:

- app boot and core task or approval routes PASS
- API layer is stable enough for stage and artifact route expansion

## Day 10: Stage APIs, Artifact APIs, and Phase Exit Gate

### Task 36: Add stage detail endpoint

**References:**
- Checklist task: `5.5`

**Files:**
- Create: `apps/orchestrator-api/app/api/stages.py`
- Test: `tests/api/test_get_stage_api.py`

**Step 1: Write the failing test**

Write tests for stage detail lookup including artifact IDs, approval history, and failure summary.

**Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_get_stage_api.py -v`
Expected: FAIL because the stage detail endpoint does not exist.

**Step 3: Write minimal implementation**

Add stage detail route and wire it to stage query logic.

**Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_get_stage_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/orchestrator-api/app/api/stages.py tests/api
git commit -m "feat: add stage detail api"
```

### Task 37: Add artifact listing endpoint

**References:**
- Checklist task: `5.6`

**Files:**
- Create: `apps/orchestrator-api/app/api/artifacts.py`
- Test: `tests/api/test_artifact_listing_api.py`

**Step 1: Write the failing test**

Write tests for listing artifacts by task and stage with version-ordered metadata.

**Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_artifact_listing_api.py -v`
Expected: FAIL because the artifact listing endpoint does not exist.

**Step 3: Write minimal implementation**

Add metadata-only artifact listing route. Do not return raw file content.

**Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_artifact_listing_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/orchestrator-api/app/api/artifacts.py tests/api
git commit -m "feat: add artifact listing api"
```

### Task 38: Run full Phase 3-5 regression gate

**References:**
- Checklist tasks: `3.1` to `5.6`

**Files:**
- No new files required
- Test: `tests/artifacts`
- Test: `tests/observability/test_trace_store.py`
- Test: `tests/workflow`
- Test: `tests/api`

**Step 1: Run the focused regression suites**

Run:

```bash
pytest tests/artifacts tests/observability/test_trace_store.py tests/workflow tests/api -v
```

Expected: all suites PASS

**Step 2: Fix integration regressions immediately**

Do not proceed to queueing or callback work if any artifact, workflow, or API test fails.

**Step 3: Record the phase exit review**

Update task tracking or review notes with:

- passing suites
- remaining API gaps
- whether Phase 6 can begin

**Step 4: Commit**

```bash
git add tasks/todo.md docs/plans
git commit -m "docs: record phase 3 to 5 execution gate"
```

## Phase Exit Criteria

Phase 3 to Phase 5 are complete only if all of the following are true:

- `tests/artifacts -v` passes
- `tests/observability/test_trace_store.py -v` passes
- `tests/workflow -v` passes
- `tests/api -v` passes
- artifact metadata persistence works end-to-end against the local store and database metadata model
- task, stage, approval, and artifact API routes return the documented metadata
- no unresolved mismatch remains between workflow service behavior and API semantics

## Handoff To Phase 6

Only begin `Phase 6: Queueing, Worker Commands, and Callback Handling` if:

- the full Phase 3-5 regression gate passes
- stage command and workflow services are stable
- the API surface can create, inspect, and approve tasks reliably
- phase review notes clearly state which assumptions remain local-only and which are ready for queue-backed execution

## Suggested Daily Review Questions

At the end of each working day, answer:

1. Which persistence, workflow, or API tasks were completed and which suites passed?
2. Did any service change force rework in artifact metadata, workflow transitions, or API response shape?
3. Are any route semantics still depending on implicit in-memory assumptions rather than persisted state?
4. Is Phase 6 blocked by missing queue abstractions, unstable APIs, or unresolved state-transition behavior?

Plan complete and saved to `docs/plans/2026-04-22-rv-insights-phase-3-5-execution-plan.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
