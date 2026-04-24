# RV-Insights Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the Python-first MVP skeleton for `RV-Insights`, including workflow state, approval gates, node contracts, and service boundaries for OpenAI orchestration and Claude-based development execution.

**Architecture:** A FastAPI orchestrator owns workflow state and approvals, specialized services implement explorer/planner/reviewer/developer/test roles, and shared packages define persistence models, stage schemas, and SDK adapters. The first milestone should prioritize resumable task state and a simulated end-to-end loop before real agent integration.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, OpenAI Agents SDK, Claude Agent SDK, pytest

---

### Task 1: Create the repository skeleton

**Files:**
- Create: `apps/orchestrator-api/app/main.py`
- Create: `apps/orchestrator-api/app/api/tasks.py`
- Create: `apps/orchestrator-api/app/api/stages.py`
- Create: `services/claude-dev-worker/app/main.py`
- Create: `services/test-runner/app/main.py`
- Create: `packages/core-models/src/__init__.py`
- Create: `packages/workflow-engine/src/__init__.py`
- Create: `packages/sdk-adapters/src/__init__.py`
- Create: `infra/migrations/README.md`
- Create: `tests/smoke/test_repo_layout.py`

**Step 1: Write the failing test**

```python
from pathlib import Path


def test_expected_directories_exist():
    expected = [
        Path("apps/orchestrator-api/app"),
        Path("services/claude-dev-worker/app"),
        Path("services/test-runner/app"),
        Path("packages/core-models/src"),
        Path("packages/workflow-engine/src"),
        Path("packages/sdk-adapters/src"),
        Path("infra/migrations"),
    ]
    missing = [path for path in expected if not path.exists()]
    assert not missing, f"Missing paths: {missing}"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/smoke/test_repo_layout.py -v`
Expected: FAIL because the directories and files do not exist yet

**Step 3: Write minimal implementation**

Create the directories and placeholder module files listed above.

**Step 4: Run test to verify it passes**

Run: `pytest tests/smoke/test_repo_layout.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps services packages infra tests
git commit -m "chore: scaffold rv-insights service layout"
```

### Task 2: Define workflow enums and stage schemas

**Files:**
- Create: `packages/core-models/src/enums.py`
- Create: `packages/core-models/src/contracts.py`
- Create: `packages/core-models/src/models.py`
- Create: `tests/core_models/test_stage_contracts.py`

**Step 1: Write the failing test**

```python
from packages.core_models.src.contracts import ReviewOutput


def test_review_output_requires_structured_decision():
    payload = ReviewOutput.model_validate(
        {
            "decision": "acceptable",
            "issues": [],
            "summary": "ready for test"
        }
    )
    assert payload.decision == "acceptable"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/core_models/test_stage_contracts.py::test_review_output_requires_structured_decision -v`
Expected: FAIL because the schema does not exist

**Step 3: Write minimal implementation**

Implement:

- stage enums
- task status enums
- `ExploreOutput`, `PlanOutput`, `DevelopOutput`, `ReviewOutput`, `TestOutput`
- top-level persistence models for `ContributionTask`, `StageRun`, `ApprovalRecord`, `Artifact`

**Step 4: Run test to verify it passes**

Run: `pytest tests/core_models/test_stage_contracts.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/core-models tests/core_models
git commit -m "feat: add workflow contracts and core models"
```

### Task 3: Implement the workflow state machine

**Files:**
- Create: `packages/workflow-engine/src/state_machine.py`
- Create: `packages/workflow-engine/src/transitions.py`
- Create: `tests/workflow/test_state_machine.py`

**Step 1: Write the failing test**

```python
from packages.workflow_engine.src.state_machine import WorkflowStateMachine


def test_approval_moves_stage_to_next_state():
    machine = WorkflowStateMachine()
    state = machine.transition("waiting_approval", "approve")
    assert state == "approved"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/workflow/test_state_machine.py::test_approval_moves_stage_to_next_state -v`
Expected: FAIL because the state machine is not implemented

**Step 3: Write minimal implementation**

Implement deterministic transitions for:

- `approve`
- `rework`
- `abort`
- `fail`
- `retry`

Reject illegal transitions with explicit exceptions.

**Step 4: Run test to verify it passes**

Run: `pytest tests/workflow/test_state_machine.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/workflow-engine tests/workflow
git commit -m "feat: add workflow state machine"
```

### Task 4: Build the task and approval API

**Files:**
- Modify: `apps/orchestrator-api/app/main.py`
- Modify: `apps/orchestrator-api/app/api/tasks.py`
- Modify: `apps/orchestrator-api/app/api/stages.py`
- Create: `apps/orchestrator-api/app/schemas.py`
- Create: `apps/orchestrator-api/app/services/task_service.py`
- Create: `tests/api/test_tasks_api.py`

**Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient

from apps.orchestrator_api.app.main import app


def test_create_task_returns_task_id():
    client = TestClient(app)
    response = client.post("/tasks", json={"title": "Investigate RV issue"})
    assert response.status_code == 201
    assert "task_id" in response.json()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_tasks_api.py::test_create_task_returns_task_id -v`
Expected: FAIL because the API endpoint does not exist

**Step 3: Write minimal implementation**

Implement:

- `POST /tasks`
- `GET /tasks/{task_id}`
- `POST /tasks/{task_id}/advance`
- `POST /tasks/{task_id}/rework`
- `POST /tasks/{task_id}/abort`

Back them with in-memory storage first if database wiring is not finished, but keep the service boundary so it can be swapped to PostgreSQL.

**Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_tasks_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/orchestrator-api tests/api
git commit -m "feat: add task and approval api skeleton"
```

### Task 5: Add artifact persistence metadata and storage abstraction

**Files:**
- Create: `packages/artifact-store/src/store.py`
- Create: `packages/artifact-store/src/models.py`
- Create: `tests/artifacts/test_artifact_store.py`

**Step 1: Write the failing test**

```python
from packages.artifact_store.src.store import LocalArtifactStore


def test_store_returns_stable_metadata(tmp_path):
    store = LocalArtifactStore(base_dir=tmp_path)
    result = store.write_text("task-1", "plan.md", "# plan")
    assert result.path.exists()
    assert result.task_id == "task-1"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/artifacts/test_artifact_store.py::test_store_returns_stable_metadata -v`
Expected: FAIL because the store is not implemented

**Step 3: Write minimal implementation**

Implement a local artifact store that:

- writes content under a task-specific directory
- returns stable metadata
- keeps paths deterministic

**Step 4: Run test to verify it passes**

Run: `pytest tests/artifacts/test_artifact_store.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/artifact-store tests/artifacts
git commit -m "feat: add artifact storage abstraction"
```

### Task 6: Wire a simulated end-to-end workflow

**Files:**
- Create: `packages/workflow-engine/src/orchestrator.py`
- Create: `packages/sdk-adapters/src/openai_runner.py`
- Create: `packages/sdk-adapters/src/claude_runner.py`
- Create: `tests/workflow/test_end_to_end_simulation.py`

**Step 1: Write the failing test**

```python
from packages.workflow_engine.src.orchestrator import simulate_task


def test_simulated_task_reaches_waiting_approval_after_explore():
    task = simulate_task(title="RV issue")
    assert task.current_stage == "explore"
    assert task.status == "waiting_approval"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/workflow/test_end_to_end_simulation.py::test_simulated_task_reaches_waiting_approval_after_explore -v`
Expected: FAIL because the orchestrator simulation does not exist

**Step 3: Write minimal implementation**

Implement a simple orchestrator loop that:

- creates a task
- runs a stub explorer adapter
- writes an exploration artifact
- transitions into `waiting_approval`

Keep OpenAI and Claude adapters stubbed but shaped like the final interfaces.

**Step 4: Run test to verify it passes**

Run: `pytest tests/workflow/test_end_to_end_simulation.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/workflow-engine packages/sdk-adapters tests/workflow
git commit -m "feat: wire simulated workflow orchestration"
```

### Task 7: Integrate tracing, logging, and review loop hooks

**Files:**
- Create: `packages/observability/src/logging.py`
- Create: `packages/observability/src/tracing.py`
- Modify: `packages/workflow-engine/src/orchestrator.py`
- Create: `tests/observability/test_trace_events.py`

**Step 1: Write the failing test**

```python
from packages.observability.src.tracing import collect_stage_event


def test_collect_stage_event_returns_normalized_payload():
    event = collect_stage_event("task-1", "explore", "stage.started")
    assert event["event_type"] == "stage.started"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/observability/test_trace_events.py::test_collect_stage_event_returns_normalized_payload -v`
Expected: FAIL because tracing helpers do not exist

**Step 3: Write minimal implementation**

Implement:

- normalized stage event logger
- tracing wrapper interface for OpenAI traces
- local fallback logger for Claude worker events

**Step 4: Run test to verify it passes**

Run: `pytest tests/observability/test_trace_events.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add packages/observability packages/workflow-engine tests/observability
git commit -m "feat: add workflow observability hooks"
```

### Task 8: Prepare real agent integration seams

**Files:**
- Create: `services/explorer-agent/README.md`
- Create: `services/planner-agent/README.md`
- Create: `services/reviewer-agent/README.md`
- Modify: `packages/sdk-adapters/src/openai_runner.py`
- Modify: `packages/sdk-adapters/src/claude_runner.py`
- Create: `tests/adapters/test_sdk_adapter_interfaces.py`

**Step 1: Write the failing test**

```python
from packages.sdk_adapters.src.openai_runner import OpenAIStageRunner
from packages.sdk_adapters.src.claude_runner import ClaudeDevRunner


def test_sdk_runners_expose_execute_interface():
    assert hasattr(OpenAIStageRunner, "execute")
    assert hasattr(ClaudeDevRunner, "execute")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/adapters/test_sdk_adapter_interfaces.py::test_sdk_runners_expose_execute_interface -v`
Expected: FAIL because the adapter classes are incomplete

**Step 3: Write minimal implementation**

Add explicit adapter interfaces for:

- explore
- plan
- review
- develop

Each adapter should accept structured contracts and return structured results matching the design document.

**Step 4: Run test to verify it passes**

Run: `pytest tests/adapters/test_sdk_adapter_interfaces.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services packages/sdk-adapters tests/adapters
git commit -m "feat: define sdk integration seams"
```

Plan complete and saved to `docs/plans/2026-04-22-rv-insights-implementation.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
