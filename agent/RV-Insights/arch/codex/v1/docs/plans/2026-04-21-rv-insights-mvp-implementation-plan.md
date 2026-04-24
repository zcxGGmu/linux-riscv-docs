# RV-Insights MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first end-to-end, human-gated MVP of RV-Insights that can manage one RISC-V contribution case through case intake, planning, development/review loop bookkeeping, approval gates, artifact storage metadata, and test runtime preparation.

**Architecture:** Use a single Python control service to host the API, server-rendered review console, orchestrator, approval gateway, transition validator, and artifact registry. Back it with PostgreSQL-friendly models, local object storage references, and template-driven workspace/test runtime services so the MVP can run a single case serially while preserving auditability and extensibility.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, Jinja2, pytest, httpx, SQLite for local tests, PostgreSQL in real deployment

---

### Task 1: Bootstrap the Control Service

**Files:**
- Create: `pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/routes/__init__.py`
- Create: `backend/app/api/routes/health.py`
- Create: `tests/conftest.py`
- Create: `tests/api/test_health.py`

**Step 1: Write the failing API test**

```python
from fastapi.testclient import TestClient

from backend.app.main import app


def test_healthcheck_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_health.py -v`  
Expected: FAIL because `backend.app.main` or `/healthz` does not exist yet.

**Step 3: Write the minimal implementation**

```python
from fastapi import APIRouter, FastAPI

router = APIRouter()


@router.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


app = FastAPI(title="RV-Insights")
app.include_router(router)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_health.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml backend/app tests/api/test_health.py tests/conftest.py
git commit -m "feat: bootstrap rv-insights control service"
```

### Task 2: Add the Domain Models and Persistence Layer

**Files:**
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/case.py`
- Create: `backend/app/models/stage_run.py`
- Create: `backend/app/models/artifact.py`
- Create: `backend/app/models/approval.py`
- Create: `backend/app/models/finding.py`
- Create: `backend/app/models/state_transition.py`
- Create: `backend/app/core/enums.py`
- Create: `backend/app/schemas/case.py`
- Create: `backend/app/schemas/artifact.py`
- Create: `backend/app/schemas/approval.py`
- Create: `tests/models/test_case_models.py`

**Step 1: Write the failing model test**

```python
from backend.app.core.enums import CaseState, StageName
from backend.app.schemas.case import CaseCreate


def test_case_create_defaults_to_discovering() -> None:
    payload = CaseCreate(
        title="OpenSBI timer fix",
        target_project="opensbi",
        target_repo_url="https://example.com/opensbi.git",
        target_branch="master",
    )
    assert payload.current_state == CaseState.DISCOVERING
    assert payload.current_stage == StageName.DISCOVERING
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/models/test_case_models.py -v`  
Expected: FAIL because enums and schemas are undefined.

**Step 3: Write the minimal implementation**

```python
from enum import StrEnum
from pydantic import BaseModel


class CaseState(StrEnum):
    DISCOVERING = "DISCOVERING"


class StageName(StrEnum):
    DISCOVERING = "DISCOVERING"


class CaseCreate(BaseModel):
    title: str
    target_project: str
    target_repo_url: str
    target_branch: str
    current_state: CaseState = CaseState.DISCOVERING
    current_stage: StageName = StageName.DISCOVERING
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/models/test_case_models.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/db backend/app/models backend/app/core backend/app/schemas tests/models/test_case_models.py
git commit -m "feat: add core domain models and schemas"
```

### Task 3: Implement the Orchestrator and Transition Validator

**Files:**
- Create: `backend/app/core/orchestrator.py`
- Create: `backend/app/core/transition_validator.py`
- Create: `backend/app/core/policy.py`
- Create: `backend/app/services/cases.py`
- Create: `tests/orchestrator/test_transition_validator.py`

**Step 1: Write the failing transition test**

```python
from backend.app.core.enums import ApprovalAction, CaseState
from backend.app.core.transition_validator import validate_transition


def test_discovery_approval_can_advance_to_planning() -> None:
    next_state = validate_transition(
        current_state=CaseState.WAIT_APPROVE_DISCOVERY,
        action=ApprovalAction.APPROVE,
    )
    assert next_state == CaseState.PLANNING
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/orchestrator/test_transition_validator.py -v`  
Expected: FAIL because transition validation is not implemented.

**Step 3: Write the minimal implementation**

```python
from backend.app.core.enums import ApprovalAction, CaseState


TRANSITIONS = {
    (CaseState.WAIT_APPROVE_DISCOVERY, ApprovalAction.APPROVE): CaseState.PLANNING,
}


def validate_transition(current_state: CaseState, action: ApprovalAction) -> CaseState:
    return TRANSITIONS[(current_state, action)]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/orchestrator/test_transition_validator.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/core backend/app/services/cases.py tests/orchestrator/test_transition_validator.py
git commit -m "feat: add orchestrator transition validation"
```

### Task 4: Build the Approval Gateway and Audit Trail

**Files:**
- Create: `backend/app/api/routes/cases.py`
- Create: `backend/app/api/routes/approvals.py`
- Create: `backend/app/services/approvals.py`
- Create: `backend/app/services/audit.py`
- Create: `backend/app/schemas/audit.py`
- Create: `tests/api/test_approvals.py`

**Step 1: Write the failing approval API test**

```python
from fastapi.testclient import TestClient

from backend.app.main import app


def test_submit_approval_returns_transition_preview() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/approvals",
        json={
            "case_id": "case-1",
            "stage": "WAIT_APPROVE_DISCOVERY",
            "artifact_version": "opportunity_report:v1",
            "action": "approve",
            "reviewer_id": "reviewer-1",
            "reviewer_role": "Project Reviewer",
        },
    )
    assert response.status_code == 201
    assert response.json()["next_state"] == "PLANNING"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/api/test_approvals.py -v`  
Expected: FAIL because approval routes and services do not exist.

**Step 3: Write the minimal implementation**

```python
from fastapi import APIRouter, status

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_approval(payload: dict) -> dict:
    return {
        "case_id": payload["case_id"],
        "action": payload["action"],
        "next_state": "PLANNING",
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/api/test_approvals.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/api/routes backend/app/services/approvals.py backend/app/services/audit.py backend/app/schemas/audit.py tests/api/test_approvals.py
git commit -m "feat: add approval gateway and audit event logging"
```

### Task 5: Implement Artifact Registry and Agent Contracts

**Files:**
- Create: `backend/app/contracts/__init__.py`
- Create: `backend/app/contracts/envelope.py`
- Create: `backend/app/contracts/explore.py`
- Create: `backend/app/contracts/plan.py`
- Create: `backend/app/contracts/develop.py`
- Create: `backend/app/contracts/review.py`
- Create: `backend/app/contracts/debug.py`
- Create: `backend/app/contracts/testing.py`
- Create: `backend/app/services/artifacts.py`
- Create: `backend/app/services/agent_runner.py`
- Create: `tests/services/test_artifact_registry.py`

**Step 1: Write the failing artifact registry test**

```python
from backend.app.services.artifacts import ArtifactRegistry


def test_register_artifact_increments_version_per_stage() -> None:
    registry = ArtifactRegistry()
    first = registry.register(case_id="case-1", stage="PLANNING", artifact_type="execution_plan")
    second = registry.register(case_id="case-1", stage="PLANNING", artifact_type="execution_plan")
    assert first.version == 1
    assert second.version == 2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/services/test_artifact_registry.py -v`  
Expected: FAIL because the registry does not exist.

**Step 3: Write the minimal implementation**

```python
from dataclasses import dataclass


@dataclass
class RegisteredArtifact:
    version: int


class ArtifactRegistry:
    def __init__(self) -> None:
        self._versions: dict[tuple[str, str, str], int] = {}

    def register(self, case_id: str, stage: str, artifact_type: str) -> RegisteredArtifact:
        key = (case_id, stage, artifact_type)
        version = self._versions.get(key, 0) + 1
        self._versions[key] = version
        return RegisteredArtifact(version=version)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/services/test_artifact_registry.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/contracts backend/app/services/artifacts.py backend/app/services/agent_runner.py tests/services/test_artifact_registry.py
git commit -m "feat: add artifact registry and agent contracts"
```

### Task 6: Add Workspace Management and RISC-V Test Runtime Templates

**Files:**
- Create: `backend/app/services/workspaces.py`
- Create: `backend/app/services/test_runtime.py`
- Create: `backend/app/schemas/runtime.py`
- Create: `runtimes/templates/kernel-basic.yaml`
- Create: `runtimes/templates/opensbi-basic.yaml`
- Create: `runtimes/templates/uboot-basic.yaml`
- Create: `runtimes/templates/toolchain-basic.yaml`
- Create: `tests/services/test_runtime_templates.py`

**Step 1: Write the failing runtime template test**

```python
from pathlib import Path

import yaml


def test_kernel_template_declares_qemu_level() -> None:
    payload = yaml.safe_load(Path("runtimes/templates/kernel-basic.yaml").read_text())
    assert payload["name"] == "kernel-basic"
    assert payload["default_execution_mode"] == "qemu"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/services/test_runtime_templates.py -v`  
Expected: FAIL because runtime templates do not exist yet.

**Step 3: Write the minimal implementation**

```yaml
name: kernel-basic
default_execution_mode: qemu
toolchain: riscv64-linux-gnu
test_levels:
  - level0
  - level1
  - level2
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/services/test_runtime_templates.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/workspaces.py backend/app/services/test_runtime.py backend/app/schemas/runtime.py runtimes/templates tests/services/test_runtime_templates.py
git commit -m "feat: add workspace service and riscv runtime templates"
```

### Task 7: Build the Minimal Review Console

**Files:**
- Create: `backend/app/ui/__init__.py`
- Create: `backend/app/ui/routes.py`
- Create: `backend/app/templates/base.html`
- Create: `backend/app/templates/cases.html`
- Create: `backend/app/templates/case_detail.html`
- Create: `backend/app/templates/review_stage.html`
- Create: `backend/app/static/styles.css`
- Create: `tests/ui/test_review_console.py`

**Step 1: Write the failing UI test**

```python
from fastapi.testclient import TestClient

from backend.app.main import app


def test_cases_page_renders_review_console() -> None:
    client = TestClient(app)
    response = client.get("/cases")
    assert response.status_code == 200
    assert "RV-Insights Review Console" in response.text
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/ui/test_review_console.py -v`  
Expected: FAIL because the server-rendered review console does not exist.

**Step 3: Write the minimal implementation**

```python
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/cases", response_class=HTMLResponse)
def case_list() -> str:
    return "<html><body><h1>RV-Insights Review Console</h1></body></html>"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/ui/test_review_console.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/ui backend/app/templates backend/app/static tests/ui/test_review_console.py
git commit -m "feat: add minimal review console"
```

### Task 8: Prove the End-to-End MVP Case Flow

**Files:**
- Create: `tests/e2e/test_case_flow.py`
- Create: `backend/app/fixtures/sample_case.py`
- Create: `backend/app/services/demo_case_flow.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/routes/cases.py`
- Modify: `backend/app/api/routes/approvals.py`

**Step 1: Write the failing end-to-end test**

```python
from fastapi.testclient import TestClient

from backend.app.main import app


def test_case_can_move_from_discovery_to_planning_after_approval() -> None:
    client = TestClient(app)
    case_response = client.post(
        "/api/cases",
        json={
            "title": "OpenSBI timer fix",
            "target_project": "opensbi",
            "target_repo_url": "https://example.com/opensbi.git",
            "target_branch": "master",
        },
    )
    case_id = case_response.json()["case_id"]

    approval_response = client.post(
        "/api/approvals",
        json={
            "case_id": case_id,
            "stage": "WAIT_APPROVE_DISCOVERY",
            "artifact_version": "opportunity_report:v1",
            "action": "approve",
            "reviewer_id": "reviewer-1",
            "reviewer_role": "Project Reviewer",
        },
    )

    assert approval_response.status_code == 201
    assert approval_response.json()["next_state"] == "PLANNING"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/e2e/test_case_flow.py -v`  
Expected: FAIL because cases API and stateful orchestration are incomplete.

**Step 3: Write the minimal implementation**

```python
CASES: dict[str, dict] = {}


def create_case(payload: dict) -> dict:
    case_id = f"case-{len(CASES) + 1}"
    record = {"case_id": case_id, "current_state": "WAIT_APPROVE_DISCOVERY", **payload}
    CASES[case_id] = record
    return record
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/e2e/test_case_flow.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app tests/e2e/test_case_flow.py
git commit -m "feat: prove end-to-end mvp case flow"
```
