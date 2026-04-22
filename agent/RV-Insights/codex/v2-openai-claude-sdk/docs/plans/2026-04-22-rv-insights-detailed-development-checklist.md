# RV-Insights Detailed Development Checklist

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn the approved `RV-Insights` architecture into a fine-grained, execution-ready development checklist where every completed task is immediately verified by tests before work proceeds.

**Architecture:** Build the platform in layered phases: repository baseline, domain contracts, persistence, workflow engine, API, execution services, agent adapters, approval UI, end-to-end recovery, and hardening. Each task below is intentionally small enough to implement and verify in isolation while preserving the larger workflow architecture.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, Redis, Arq or Celery, OpenAI Agents SDK, Claude Agent SDK, pytest, httpx, Docker, Playwright

---

## Execution Rules

- Every task must end with a test run.
- If the test fails, fix the task before starting the next one.
- Do not batch multiple unverified tasks together.
- Keep commits scoped to one checklist task unless two adjacent tasks touch the same files and are inseparable.
- Use the smallest viable implementation that satisfies the task and test.
- If a task changes a contract, update both unit tests and at least one integration test that consumes that contract.

## Definition of Done Per Task

Every task is complete only if all of the following are true:

- implementation for the task is in place
- targeted tests for the task pass
- no previously passing tests for the touched area regress
- logs, artifacts, or traces required by the task can be inspected
- any new schema or API behavior is documented inline or in the relevant doc file

## Phase 0: Project Bootstrap and Delivery Guardrails

### Task 0.1: Establish repository directory skeleton

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

**Development checklist:**
- Create the top-level app, service, and package directories from the architecture plan.
- Add placeholder Python package markers where needed.
- Add a minimal README placeholder for the approval console.

**Test after completion:**
- Run: `pytest tests/smoke/test_repository_layout.py -v`

**Pass criteria:**
- All expected directories and package entry files exist.

### Task 0.2: Add Python workspace metadata and toolchain config

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `pytest.ini`
- Create: `.gitignore`
- Test: `tests/smoke/test_pyproject_metadata.py`

**Development checklist:**
- Define the project package metadata and Python version.
- Configure pytest discovery and test paths.
- Add sensible ignore rules for caches, virtual environments, workspaces, artifacts, and logs.

**Test after completion:**
- Run: `pytest tests/smoke/test_pyproject_metadata.py -v`

**Pass criteria:**
- Test confirms the metadata file and pytest configuration exist and parse.

### Task 0.3: Add local developer commands and Makefile targets

**Files:**
- Create: `Makefile`
- Create: `scripts/README.md`
- Test: `tests/smoke/test_make_targets.py`

**Development checklist:**
- Add baseline targets for `test`, `lint`, `format`, `run-api`, and `run-worker`.
- Keep the target implementations minimal but valid.
- Document the meaning of each target in `scripts/README.md`.

**Test after completion:**
- Run: `pytest tests/smoke/test_make_targets.py -v`

**Pass criteria:**
- Tests confirm the required Makefile targets exist.

### Task 0.4: Add baseline CI workflow shape

**Files:**
- Create: `.github/workflows/ci.yml`
- Test: `tests/smoke/test_ci_workflow.py`

**Development checklist:**
- Add a baseline CI workflow covering install, unit test, and lint stages.
- Keep the workflow generic enough for early scaffolding.

**Test after completion:**
- Run: `pytest tests/smoke/test_ci_workflow.py -v`

**Pass criteria:**
- Test confirms the workflow file exists and contains expected job names.

## Phase 1: Core Domain Enums and Contracts

### Task 1.1: Define workflow stage enums

**Files:**
- Create: `packages/core-models/enums.py`
- Test: `tests/core_models/test_stage_enums.py`

**Development checklist:**
- Define canonical stage enum values for `explore`, `plan`, `develop`, `review`, `test`, `done`, and `aborted`.
- Add transition-safe status enum values for run-level and task-level lifecycle states.

**Test after completion:**
- Run: `pytest tests/core_models/test_stage_enums.py -v`

**Pass criteria:**
- Test validates all expected enum values and rejects invalid ones.

### Task 1.2: Define common artifact envelope schema

**Files:**
- Create: `packages/core-models/contracts/common.py`
- Test: `tests/core_models/test_common_artifact_envelope.py`

**Development checklist:**
- Add the shared artifact wrapper with `schema_version`, `task_id`, `stage`, `summary`, `confidence`, `blocking_items`, `open_questions`, `recommended_next_action`, and `payload`.
- Ensure validation rules are explicit for required fields.

**Test after completion:**
- Run: `pytest tests/core_models/test_common_artifact_envelope.py -v`

**Pass criteria:**
- Test confirms the envelope accepts valid payloads and rejects missing required metadata.

### Task 1.3: Define explorer input and output schemas

**Files:**
- Create: `packages/core-models/contracts/explore.py`
- Test: `tests/core_models/test_explore_contracts.py`

**Development checklist:**
- Model explorer request schema.
- Model evidence item schema.
- Model candidate output schema and feasibility score fields.

**Test after completion:**
- Run: `pytest tests/core_models/test_explore_contracts.py -v`

**Pass criteria:**
- Tests validate both valid explorer payloads and invalid score or evidence shapes.

### Task 1.4: Define planner input and output schemas

**Files:**
- Create: `packages/core-models/contracts/plan.py`
- Test: `tests/core_models/test_plan_contracts.py`

**Development checklist:**
- Model implementation plan payload.
- Model test plan payload.
- Model risk and non-goal sections.

**Test after completion:**
- Run: `pytest tests/core_models/test_plan_contracts.py -v`

**Pass criteria:**
- Tests confirm planner outputs require target files, change steps, and test instructions.

### Task 1.5: Define developer input and output schemas

**Files:**
- Create: `packages/core-models/contracts/develop.py`
- Test: `tests/core_models/test_develop_contracts.py`

**Development checklist:**
- Model approved plan input reference, unresolved issue list, and repo snapshot reference.
- Model code result output, branch, commit, diff artifact, self-check commands, and limitations.

**Test after completion:**
- Run: `pytest tests/core_models/test_develop_contracts.py -v`

**Pass criteria:**
- Tests confirm developer output cannot omit commit or self-check metadata.

### Task 1.6: Define reviewer input and output schemas

**Files:**
- Create: `packages/core-models/contracts/review.py`
- Test: `tests/core_models/test_review_contracts.py`

**Development checklist:**
- Model review issue schema.
- Model `acceptable` vs `rework` decision schema.
- Enforce severity enum constraints.

**Test after completion:**
- Run: `pytest tests/core_models/test_review_contracts.py -v`

**Pass criteria:**
- Tests validate structured issue output and invalid severity rejection.

### Task 1.7: Define test runner input and output schemas

**Files:**
- Create: `packages/core-models/contracts/testing.py`
- Test: `tests/core_models/test_testing_contracts.py`

**Development checklist:**
- Model test environment manifest.
- Model test command result schema.
- Model final test result state and blocking failure list.

**Test after completion:**
- Run: `pytest tests/core_models/test_testing_contracts.py -v`

**Pass criteria:**
- Tests confirm required environment and execution fields are enforced.

### Task 1.8: Define failure artifact schema

**Files:**
- Create: `packages/core-models/contracts/failure.py`
- Test: `tests/core_models/test_failure_contracts.py`

**Development checklist:**
- Model failure type, reason, logs, retry recommendation, and next action.
- Ensure the schema can be emitted from any stage.

**Test after completion:**
- Run: `pytest tests/core_models/test_failure_contracts.py -v`

**Pass criteria:**
- Tests validate valid failure artifacts and reject invalid next actions.

## Phase 2: Persistence Models and Database Foundation

### Task 2.1: Define `ContributionTask` ORM model

**Files:**
- Create: `packages/core-models/models/task.py`
- Test: `tests/db/test_task_model.py`

**Development checklist:**
- Add ORM fields for task identity, stage, status, objective, and active stage run.
- Add indexes for task ID and current status.

**Test after completion:**
- Run: `pytest tests/db/test_task_model.py -v`

**Pass criteria:**
- Tests confirm model creation and expected column names.

### Task 2.2: Define `StageRun` ORM model

**Files:**
- Create: `packages/core-models/models/stage_run.py`
- Test: `tests/db/test_stage_run_model.py`

**Development checklist:**
- Add stage attempt tracking, runtime type, session ref JSON field, input artifact references, and status.
- Add foreign key relation to `ContributionTask`.

**Test after completion:**
- Run: `pytest tests/db/test_stage_run_model.py -v`

**Pass criteria:**
- Tests validate one task can own multiple stage runs with attempt ordering.

### Task 2.3: Define `ApprovalRecord` ORM model

**Files:**
- Create: `packages/core-models/models/approval.py`
- Test: `tests/db/test_approval_model.py`

**Development checklist:**
- Add decision, reviewer, reason type, must-fix items, and timestamps.
- Add foreign key relation to `StageRun`.

**Test after completion:**
- Run: `pytest tests/db/test_approval_model.py -v`

**Pass criteria:**
- Tests validate approval records attach to a single stage run and preserve structured reasons.

### Task 2.4: Define `Artifact` ORM model

**Files:**
- Create: `packages/core-models/models/artifact.py`
- Test: `tests/db/test_artifact_model.py`

**Development checklist:**
- Add artifact type, format, storage URI, summary, version, and stage ownership.
- Index by task, stage run, and artifact type.

**Test after completion:**
- Run: `pytest tests/db/test_artifact_model.py -v`

**Pass criteria:**
- Tests validate artifact versioning and ownership fields.

### Task 2.5: Define optional support models

**Files:**
- Create: `packages/core-models/models/repository_profile.py`
- Create: `packages/core-models/models/workspace_lease.py`
- Create: `packages/core-models/models/environment_snapshot.py`
- Test: `tests/db/test_support_models.py`

**Development checklist:**
- Add repository profile metadata for default branch, test tier, maintainer map, and command entry points.
- Add workspace lease metadata for owner, TTL, status, and last heartbeat.
- Add environment snapshot fields for toolchain and image identity.

**Test after completion:**
- Run: `pytest tests/db/test_support_models.py -v`

**Pass criteria:**
- Tests validate field presence and basic relation integrity.

### Task 2.6: Add SQLAlchemy base and database session factory

**Files:**
- Create: `packages/core-models/db/base.py`
- Create: `packages/core-models/db/session.py`
- Test: `tests/db/test_session_factory.py`

**Development checklist:**
- Define declarative base and session creation helper.
- Add a minimal config-driven engine factory.

**Test after completion:**
- Run: `pytest tests/db/test_session_factory.py -v`

**Pass criteria:**
- Tests confirm the session factory opens and closes a test database session.

### Task 2.7: Add first Alembic migration

**Files:**
- Create: `infra/migrations/alembic.ini`
- Create: `infra/migrations/env.py`
- Create: `infra/migrations/versions/0001_initial_schema.py`
- Test: `tests/db/test_initial_migration.py`

**Development checklist:**
- Initialize Alembic config.
- Add initial schema migration for the core models.

**Test after completion:**
- Run: `pytest tests/db/test_initial_migration.py -v`

**Pass criteria:**
- Tests confirm the migration can apply successfully to a fresh database.

## Phase 3: Artifact Store, Trace Store, and Local Persistence Helpers

### Task 3.1: Add deterministic local artifact path builder

**Files:**
- Create: `packages/artifact-store/pathing.py`
- Test: `tests/artifacts/test_artifact_pathing.py`

**Development checklist:**
- Implement task/stage/attempt/version-aware artifact path generation.
- Ensure path rules are deterministic and filesystem-safe.

**Test after completion:**
- Run: `pytest tests/artifacts/test_artifact_pathing.py -v`

**Pass criteria:**
- Tests verify generated paths match the expected layout and do not overwrite by default.

### Task 3.2: Add local artifact write and read helpers

**Files:**
- Create: `packages/artifact-store/store.py`
- Test: `tests/artifacts/test_local_artifact_store.py`

**Development checklist:**
- Implement text and JSON write helpers.
- Implement read-by-artifact helper for local storage.

**Test after completion:**
- Run: `pytest tests/artifacts/test_local_artifact_store.py -v`

**Pass criteria:**
- Tests confirm artifacts can be written and read back intact.

### Task 3.3: Add artifact metadata service

**Files:**
- Create: `packages/artifact-store/metadata_service.py`
- Test: `tests/artifacts/test_metadata_service.py`

**Development checklist:**
- Implement DB metadata persistence for newly written artifacts.
- Link artifact metadata rows to stored files.

**Test after completion:**
- Run: `pytest tests/artifacts/test_metadata_service.py -v`

**Pass criteria:**
- Tests confirm stored artifacts have both physical files and database rows.

### Task 3.4: Add trace event model and storage helper

**Files:**
- Create: `packages/observability/traces.py`
- Test: `tests/observability/test_trace_store.py`

**Development checklist:**
- Define normalized trace payload structure.
- Add helper to persist stage events in a store or file-backed fallback.

**Test after completion:**
- Run: `pytest tests/observability/test_trace_store.py -v`

**Pass criteria:**
- Tests confirm trace events are normalized and retrievable.

## Phase 4: Workflow State Machine and Core Orchestrator Logic

### Task 4.1: Implement allowed state transitions

**Files:**
- Create: `packages/workflow-engine/state_machine.py`
- Test: `tests/workflow/test_state_machine.py`

**Development checklist:**
- Implement valid transition map for approve, rework, abort, fail, and retry.
- Reject illegal transitions with explicit errors.

**Test after completion:**
- Run: `pytest tests/workflow/test_state_machine.py -v`

**Pass criteria:**
- Tests confirm valid transitions pass and invalid transitions fail.

### Task 4.2: Add stage command abstraction

**Files:**
- Create: `packages/workflow-engine/commands.py`
- Test: `tests/workflow/test_stage_commands.py`

**Development checklist:**
- Define a command object for dispatching work to a stage worker.
- Include task ID, stage run ID, attempt, contract references, and timeout budget.

**Test after completion:**
- Run: `pytest tests/workflow/test_stage_commands.py -v`

**Pass criteria:**
- Tests confirm commands serialize and validate correctly.

### Task 4.3: Add workflow service to create tasks

**Files:**
- Create: `packages/workflow-engine/task_service.py`
- Test: `tests/workflow/test_task_creation_service.py`

**Development checklist:**
- Add service for creating a new task and initial stage run.
- Ensure task creation does not auto-skip approval boundaries.

**Test after completion:**
- Run: `pytest tests/workflow/test_task_creation_service.py -v`

**Pass criteria:**
- Tests confirm a new task starts with the correct initial stage and status.

### Task 4.4: Add stage advancement service

**Files:**
- Create: `packages/workflow-engine/advance_service.py`
- Test: `tests/workflow/test_stage_advancement.py`

**Development checklist:**
- Implement logic to move from an approved stage to the next stage.
- Keep stage transition ownership in the orchestrator only.

**Test after completion:**
- Run: `pytest tests/workflow/test_stage_advancement.py -v`

**Pass criteria:**
- Tests confirm only valid approved stages can advance.

### Task 4.5: Add rework and rollback service

**Files:**
- Create: `packages/workflow-engine/rework_service.py`
- Test: `tests/workflow/test_rework_and_rollback.py`

**Development checklist:**
- Implement `rework_current_stage`, `reopen_previous_stage`, and `restart_from_plan`.
- Ensure new attempts are created rather than overwriting old state.

**Test after completion:**
- Run: `pytest tests/workflow/test_rework_and_rollback.py -v`

**Pass criteria:**
- Tests confirm a rework creates a new stage attempt and preserves old artifacts.

### Task 4.6: Add failure classification service

**Files:**
- Create: `packages/workflow-engine/failure_service.py`
- Test: `tests/workflow/test_failure_classification.py`

**Development checklist:**
- Classify failures into `transient`, `deterministic`, and `governance`.
- Return retry recommendation and next action.

**Test after completion:**
- Run: `pytest tests/workflow/test_failure_classification.py -v`

**Pass criteria:**
- Tests confirm failure classes produce correct retry semantics.

## Phase 5: Orchestrator API and Application Wiring

### Task 5.1: Add FastAPI app bootstrap

**Files:**
- Create: `apps/orchestrator-api/app/main.py`
- Test: `tests/api/test_app_boot.py`

**Development checklist:**
- Initialize FastAPI app.
- Add health endpoint and application startup wiring.

**Test after completion:**
- Run: `pytest tests/api/test_app_boot.py -v`

**Pass criteria:**
- Tests confirm app startup and health route success.

### Task 5.2: Add `POST /tasks`

**Files:**
- Create: `apps/orchestrator-api/app/api/tasks.py`
- Create: `apps/orchestrator-api/app/schemas/tasks.py`
- Test: `tests/api/test_create_task_api.py`

**Development checklist:**
- Add request/response schema for task creation.
- Wire endpoint to task creation service.

**Test after completion:**
- Run: `pytest tests/api/test_create_task_api.py -v`

**Pass criteria:**
- Tests confirm task creation returns canonical IDs and initial status.

### Task 5.3: Add `GET /tasks/{task_id}`

**Files:**
- Modify: `apps/orchestrator-api/app/api/tasks.py`
- Test: `tests/api/test_get_task_api.py`

**Development checklist:**
- Return task state, current stage, current attempt, and summary artifact references.

**Test after completion:**
- Run: `pytest tests/api/test_get_task_api.py -v`

**Pass criteria:**
- Tests confirm task lookup returns correct data for an existing task and 404 for missing task.

### Task 5.4: Add approval endpoints

**Files:**
- Create: `apps/orchestrator-api/app/api/approvals.py`
- Create: `apps/orchestrator-api/app/schemas/approvals.py`
- Test: `tests/api/test_approval_api.py`

**Development checklist:**
- Add endpoints for approve, rework, and abort.
- Enforce `stage_run_id` and `attempt` checks.

**Test after completion:**
- Run: `pytest tests/api/test_approval_api.py -v`

**Pass criteria:**
- Tests confirm approvals are idempotent and stale attempts are rejected.

### Task 5.5: Add stage detail endpoint

**Files:**
- Create: `apps/orchestrator-api/app/api/stages.py`
- Test: `tests/api/test_get_stage_api.py`

**Development checklist:**
- Return stage run details, artifact IDs, approval history, and failure summary.

**Test after completion:**
- Run: `pytest tests/api/test_get_stage_api.py -v`

**Pass criteria:**
- Tests confirm stage run detail is complete and accurate.

### Task 5.6: Add artifact listing endpoint

**Files:**
- Create: `apps/orchestrator-api/app/api/artifacts.py`
- Test: `tests/api/test_artifact_listing_api.py`

**Development checklist:**
- Add endpoint to list artifacts by task and stage.
- Return metadata only, not raw file contents.

**Test after completion:**
- Run: `pytest tests/api/test_artifact_listing_api.py -v`

**Pass criteria:**
- Tests confirm artifacts are listed in version order with expected metadata.

## Phase 6: Queueing, Worker Commands, and Callback Handling

### Task 6.1: Add worker queue abstraction

**Files:**
- Create: `packages/workflow-engine/queue.py`
- Test: `tests/workflow/test_queue_abstraction.py`

**Development checklist:**
- Define a minimal queue interface for enqueue, ack, retry, and dead-letter behavior.
- Keep the implementation abstract enough for `Arq` or `Celery`.

**Test after completion:**
- Run: `pytest tests/workflow/test_queue_abstraction.py -v`

**Pass criteria:**
- Tests confirm the queue interface and a local fake implementation behave consistently.

### Task 6.2: Add stage dispatch service

**Files:**
- Create: `packages/workflow-engine/dispatch_service.py`
- Test: `tests/workflow/test_dispatch_service.py`

**Development checklist:**
- Map each stage to its owning worker target.
- Create and enqueue stage commands from the orchestrator.

**Test after completion:**
- Run: `pytest tests/workflow/test_dispatch_service.py -v`

**Pass criteria:**
- Tests confirm each stage dispatches to the correct worker route.

### Task 6.3: Add worker callback schema and validation

**Files:**
- Create: `packages/core-models/contracts/callbacks.py`
- Test: `tests/core_models/test_callback_contracts.py`

**Development checklist:**
- Define callback payloads for success and failure.
- Require task ID, stage run ID, attempt, and artifact references.

**Test after completion:**
- Run: `pytest tests/core_models/test_callback_contracts.py -v`

**Pass criteria:**
- Tests confirm stale or partial callback payloads are rejected.

### Task 6.4: Add webhook callback endpoint

**Files:**
- Create: `apps/orchestrator-api/app/api/webhooks.py`
- Test: `tests/api/test_worker_webhook_api.py`

**Development checklist:**
- Add stage result webhook.
- Enforce signature verification and stage attempt checks.

**Test after completion:**
- Run: `pytest tests/api/test_worker_webhook_api.py -v`

**Pass criteria:**
- Tests confirm valid callbacks are accepted and stale/unsigned callbacks are rejected.

## Phase 7: SDK Adapter Layer

### Task 7.1: Add provider-neutral runner interfaces

**Files:**
- Create: `packages/sdk-adapters/interfaces.py`
- Test: `tests/adapters/test_runner_interfaces.py`

**Development checklist:**
- Define abstract interfaces for explorer, planner, reviewer, developer, and test runners.
- Keep return types tied to the core contracts.

**Test after completion:**
- Run: `pytest tests/adapters/test_runner_interfaces.py -v`

**Pass criteria:**
- Tests confirm all runner interfaces expose `execute`.

### Task 7.2: Add OpenAI stage runner stub

**Files:**
- Create: `packages/sdk-adapters/openai_runner.py`
- Test: `tests/adapters/test_openai_runner_stub.py`

**Development checklist:**
- Add a stubbed OpenAI runner for explore, plan, and review use cases.
- Keep shape aligned with final OpenAI SDK integration.

**Test after completion:**
- Run: `pytest tests/adapters/test_openai_runner_stub.py -v`

**Pass criteria:**
- Tests confirm the runner accepts a stage request and returns a typed stage result.

### Task 7.3: Add Claude development runner stub

**Files:**
- Create: `packages/sdk-adapters/claude_runner.py`
- Test: `tests/adapters/test_claude_runner_stub.py`

**Development checklist:**
- Add a stubbed Claude runner that returns session ref and code result placeholders.
- Keep shape aligned with final Claude SDK integration.

**Test after completion:**
- Run: `pytest tests/adapters/test_claude_runner_stub.py -v`

**Pass criteria:**
- Tests confirm the runner returns session, branch, and diff placeholders in the expected schema.

### Task 7.4: Add provider config and timeout policy objects

**Files:**
- Create: `packages/sdk-adapters/config.py`
- Test: `tests/adapters/test_provider_config.py`

**Development checklist:**
- Add per-provider model, timeout, retry, and budget config objects.
- Keep configuration serializable for diagnostics.

**Test after completion:**
- Run: `pytest tests/adapters/test_provider_config.py -v`

**Pass criteria:**
- Tests confirm provider config validates and can be rendered in logs.

## Phase 8: Explorer Service

### Task 8.1: Add explorer service entrypoint

**Files:**
- Create: `services/explorer-agent/main.py`
- Test: `tests/services/test_explorer_entrypoint.py`

**Development checklist:**
- Add service entrypoint that receives stage commands and returns callbacks.
- Keep implementation stubbed but wired through contracts.

**Test after completion:**
- Run: `pytest tests/services/test_explorer_entrypoint.py -v`

**Pass criteria:**
- Tests confirm the entrypoint accepts a valid command and emits a valid callback envelope.

### Task 8.2: Add evidence normalization module

**Files:**
- Create: `services/explorer-agent/evidence_normalizer.py`
- Test: `tests/services/test_evidence_normalizer.py`

**Development checklist:**
- Normalize raw mailing list, repo, and user hint inputs into a shared evidence model.

**Test after completion:**
- Run: `pytest tests/services/test_evidence_normalizer.py -v`

**Pass criteria:**
- Tests confirm all supported source shapes normalize into the same evidence schema.

### Task 8.3: Add candidate scoring module

**Files:**
- Create: `services/explorer-agent/scoring.py`
- Test: `tests/services/test_candidate_scoring.py`

**Development checklist:**
- Implement scoring against relevance, bounded scope, reproducibility, upstreamability, and verifiability.
- Apply threshold logic for recommendation.

**Test after completion:**
- Run: `pytest tests/services/test_candidate_scoring.py -v`

**Pass criteria:**
- Tests confirm weight totals and threshold decisions behave as documented.

### Task 8.4: Add explorer artifact builder

**Files:**
- Create: `services/explorer-agent/artifact_builder.py`
- Test: `tests/services/test_explorer_artifact_builder.py`

**Development checklist:**
- Build final explore artifact from normalized evidence and scored candidates.

**Test after completion:**
- Run: `pytest tests/services/test_explorer_artifact_builder.py -v`

**Pass criteria:**
- Tests confirm generated artifacts conform to the shared artifact envelope.

### Task 8.5: Add explorer integration flow

**Files:**
- Modify: `services/explorer-agent/main.py`
- Test: `tests/integration/test_explorer_flow.py`

**Development checklist:**
- Connect command handling, evidence normalization, scoring, and artifact generation.

**Test after completion:**
- Run: `pytest tests/integration/test_explorer_flow.py -v`

**Pass criteria:**
- Tests confirm the explorer flow produces a valid approval-ready artifact.

## Phase 9: Planner Service

### Task 9.1: Add planner service entrypoint

**Files:**
- Create: `services/planner-agent/main.py`
- Test: `tests/services/test_planner_entrypoint.py`

**Development checklist:**
- Add planner command handling and callback emission.

**Test after completion:**
- Run: `pytest tests/services/test_planner_entrypoint.py -v`

**Pass criteria:**
- Tests confirm planner entrypoint validates approved explorer artifacts before processing.

### Task 9.2: Add implementation plan generator

**Files:**
- Create: `services/planner-agent/implementation_plan.py`
- Test: `tests/services/test_implementation_plan_generator.py`

**Development checklist:**
- Generate target files, change steps, and non-goals from approved candidate input.

**Test after completion:**
- Run: `pytest tests/services/test_implementation_plan_generator.py -v`

**Pass criteria:**
- Tests confirm implementation plans include target files and scoped change steps.

### Task 9.3: Add test plan generator

**Files:**
- Create: `services/planner-agent/test_plan.py`
- Test: `tests/services/test_test_plan_generator.py`

**Development checklist:**
- Generate env requirements, command list, tier mapping, and expected results.

**Test after completion:**
- Run: `pytest tests/services/test_test_plan_generator.py -v`

**Pass criteria:**
- Tests confirm generated test plans include at least one concrete command and expected result.

### Task 9.4: Add planner artifact builder

**Files:**
- Create: `services/planner-agent/artifact_builder.py`
- Test: `tests/services/test_planner_artifact_builder.py`

**Development checklist:**
- Wrap implementation plan, test plan, and risk list in the shared artifact envelope.

**Test after completion:**
- Run: `pytest tests/services/test_planner_artifact_builder.py -v`

**Pass criteria:**
- Tests confirm the planner artifact is approval-ready and schema-valid.

### Task 9.5: Add planner integration flow

**Files:**
- Modify: `services/planner-agent/main.py`
- Test: `tests/integration/test_planner_flow.py`

**Development checklist:**
- Connect planner entrypoint, generators, and artifact persistence.

**Test after completion:**
- Run: `pytest tests/integration/test_planner_flow.py -v`

**Pass criteria:**
- Tests confirm approved explorer output becomes an approval-ready plan artifact.

## Phase 10: Claude Development Worker

### Task 10.1: Add development worker entrypoint

**Files:**
- Create: `services/claude-dev-worker/main.py`
- Test: `tests/services/test_dev_worker_entrypoint.py`

**Development checklist:**
- Add command intake and callback output for development stage runs.

**Test after completion:**
- Run: `pytest tests/services/test_dev_worker_entrypoint.py -v`

**Pass criteria:**
- Tests confirm the development worker only accepts approved plan inputs.

### Task 10.2: Add workspace manager

**Files:**
- Create: `services/claude-dev-worker/workspace_manager.py`
- Test: `tests/services/test_workspace_manager.py`

**Development checklist:**
- Implement workspace create, restore, freeze, and cleanup helpers.
- Record base commit and branch metadata.

**Test after completion:**
- Run: `pytest tests/services/test_workspace_manager.py -v`

**Pass criteria:**
- Tests confirm workspaces can be created and restored by task/stage identity.

### Task 10.3: Add workspace lease service

**Files:**
- Create: `services/claude-dev-worker/lease_service.py`
- Test: `tests/services/test_workspace_lease_service.py`

**Development checklist:**
- Implement lease acquisition, renewal, expiry, and stale lease recovery.

**Test after completion:**
- Run: `pytest tests/services/test_workspace_lease_service.py -v`

**Pass criteria:**
- Tests confirm only one active lease can own a workspace at a time.

### Task 10.4: Add Claude session manager wrapper

**Files:**
- Create: `services/claude-dev-worker/session_manager.py`
- Test: `tests/services/test_session_manager.py`

**Development checklist:**
- Track Claude session refs separately from filesystem state.
- Add support for session restore or fallback replay.

**Test after completion:**
- Run: `pytest tests/services/test_session_manager.py -v`

**Pass criteria:**
- Tests confirm session metadata is persisted and fallback restore logic is available.

### Task 10.5: Add execution policy and command allowlist

**Files:**
- Create: `services/claude-dev-worker/policy.py`
- Test: `tests/services/test_dev_execution_policy.py`

**Development checklist:**
- Define path restrictions, shell allowlist, and permission mode policy.
- Separate read-only and write-capable policy modes.

**Test after completion:**
- Run: `pytest tests/services/test_dev_execution_policy.py -v`

**Pass criteria:**
- Tests confirm forbidden commands or paths are blocked.

### Task 10.6: Add self-check runner

**Files:**
- Create: `services/claude-dev-worker/self_check.py`
- Test: `tests/services/test_self_check_runner.py`

**Development checklist:**
- Execute self-check commands from the approved plan.
- Capture command outputs as artifacts.

**Test after completion:**
- Run: `pytest tests/services/test_self_check_runner.py -v`

**Pass criteria:**
- Tests confirm all self-check results are captured in structured form.

### Task 10.7: Add development result bundler

**Files:**
- Create: `services/claude-dev-worker/result_bundle.py`
- Test: `tests/services/test_dev_result_bundle.py`

**Development checklist:**
- Bundle diff, changed files, commit, workspace ref, session ref, and self-check summary.

**Test after completion:**
- Run: `pytest tests/services/test_dev_result_bundle.py -v`

**Pass criteria:**
- Tests confirm the development artifact contains all required metadata.

### Task 10.8: Add development worker integration flow

**Files:**
- Modify: `services/claude-dev-worker/main.py`
- Test: `tests/integration/test_dev_worker_flow.py`

**Development checklist:**
- Connect workspace creation, session management, execution policy, self-check, and artifact bundling.

**Test after completion:**
- Run: `pytest tests/integration/test_dev_worker_flow.py -v`

**Pass criteria:**
- Tests confirm a development command produces an approval-ready artifact and callback.

## Phase 11: Reviewer Service

### Task 11.1: Add reviewer service entrypoint

**Files:**
- Create: `services/reviewer-agent/main.py`
- Test: `tests/services/test_reviewer_entrypoint.py`

**Development checklist:**
- Add reviewer command handling and callback emission.

**Test after completion:**
- Run: `pytest tests/services/test_reviewer_entrypoint.py -v`

**Pass criteria:**
- Tests confirm reviewer entrypoint only accepts approved plan and valid patch references.

### Task 11.2: Add issue classifier

**Files:**
- Create: `services/reviewer-agent/issue_classifier.py`
- Test: `tests/services/test_issue_classifier.py`

**Development checklist:**
- Classify findings into `high`, `medium`, and `low`.
- Normalize issue output fields.

**Test after completion:**
- Run: `pytest tests/services/test_issue_classifier.py -v`

**Pass criteria:**
- Tests confirm severity assignment and field normalization.

### Task 11.3: Add promotion policy evaluator

**Files:**
- Create: `services/reviewer-agent/promotion_policy.py`
- Test: `tests/services/test_reviewer_promotion_policy.py`

**Development checklist:**
- Enforce no unresolved high severity issues.
- Allow only explicitly waived medium issues.

**Test after completion:**
- Run: `pytest tests/services/test_reviewer_promotion_policy.py -v`

**Pass criteria:**
- Tests confirm issue sets map correctly to `acceptable` or `rework`.

### Task 11.4: Add review artifact builder

**Files:**
- Create: `services/reviewer-agent/artifact_builder.py`
- Test: `tests/services/test_review_artifact_builder.py`

**Development checklist:**
- Build review decision artifact with summary and issue list.

**Test after completion:**
- Run: `pytest tests/services/test_review_artifact_builder.py -v`

**Pass criteria:**
- Tests confirm review outputs conform to the review schema and shared envelope.

### Task 11.5: Add reviewer integration flow

**Files:**
- Modify: `services/reviewer-agent/main.py`
- Test: `tests/integration/test_reviewer_flow.py`

**Development checklist:**
- Connect issue classification, promotion policy, and artifact creation.

**Test after completion:**
- Run: `pytest tests/integration/test_reviewer_flow.py -v`

**Pass criteria:**
- Tests confirm the reviewer can return either `rework` or `acceptable` with valid schema.

## Phase 12: Test Runner Service

### Task 12.1: Add test runner entrypoint

**Files:**
- Create: `services/test-runner/main.py`
- Test: `tests/services/test_test_runner_entrypoint.py`

**Development checklist:**
- Add command intake and callback output for the test stage.

**Test after completion:**
- Run: `pytest tests/services/test_test_runner_entrypoint.py -v`

**Pass criteria:**
- Tests confirm the runner accepts approved test plan input only.

### Task 12.2: Add environment manifest builder

**Files:**
- Create: `services/test-runner/environment_manifest.py`
- Test: `tests/services/test_environment_manifest.py`

**Development checklist:**
- Build environment metadata including image, toolchain, emulator, and env vars.

**Test after completion:**
- Run: `pytest tests/services/test_environment_manifest.py -v`

**Pass criteria:**
- Tests confirm the manifest captures all required identity fields.

### Task 12.3: Add command execution wrapper

**Files:**
- Create: `services/test-runner/command_runner.py`
- Test: `tests/services/test_command_runner.py`

**Development checklist:**
- Execute test commands with timeout and structured result capture.
- Persist logs as artifacts.

**Test after completion:**
- Run: `pytest tests/services/test_command_runner.py -v`

**Pass criteria:**
- Tests confirm command results include status, exit code, and log references.

### Task 12.4: Add result classifier

**Files:**
- Create: `services/test-runner/result_classifier.py`
- Test: `tests/services/test_test_result_classifier.py`

**Development checklist:**
- Map raw command outcomes to `pass`, `fail`, and `inconclusive`.
- Separate blocking failures from non-blocking failures.

**Test after completion:**
- Run: `pytest tests/services/test_test_result_classifier.py -v`

**Pass criteria:**
- Tests confirm expected mapping for success, failure, and timeout cases.

### Task 12.5: Add test runner integration flow

**Files:**
- Modify: `services/test-runner/main.py`
- Test: `tests/integration/test_test_runner_flow.py`

**Development checklist:**
- Connect environment manifest, command runner, result classifier, and artifact persistence.

**Test after completion:**
- Run: `pytest tests/integration/test_test_runner_flow.py -v`

**Pass criteria:**
- Tests confirm the test runner produces a final test artifact and callback.

## Phase 13: Approval Console and Human Review Workflow

### Task 13.1: Add approval console scaffolding

**Files:**
- Create: `apps/approval-console/package.json`
- Create: `apps/approval-console/src/main.tsx`
- Test: `apps/approval-console/tests/smoke/approval_console.spec.ts`

**Development checklist:**
- Scaffold a minimal frontend shell for the approval console.
- Add route placeholders for task list, task detail, and stage review.

**Test after completion:**
- Run: `pnpm --dir apps/approval-console test -- --runInBand`

**Pass criteria:**
- Frontend smoke tests confirm the console boots and routes render.

### Task 13.2: Add task list page

**Files:**
- Create: `apps/approval-console/src/pages/task-list.tsx`
- Test: `apps/approval-console/tests/task_list.spec.ts`

**Development checklist:**
- Display tasks with current stage, status, and latest update time.

**Test after completion:**
- Run: `pnpm --dir apps/approval-console test -- task_list.spec.ts`

**Pass criteria:**
- Tests confirm tasks render with required summary fields.

### Task 13.3: Add task detail page

**Files:**
- Create: `apps/approval-console/src/pages/task-detail.tsx`
- Test: `apps/approval-console/tests/task_detail.spec.ts`

**Development checklist:**
- Show task metadata, stage timeline, artifacts, and approval history.

**Test after completion:**
- Run: `pnpm --dir apps/approval-console test -- task_detail.spec.ts`

**Pass criteria:**
- Tests confirm the task detail page renders timeline and artifact sections.

### Task 13.4: Add approval action panel

**Files:**
- Create: `apps/approval-console/src/components/approval-panel.tsx`
- Test: `apps/approval-console/tests/approval_panel.spec.ts`

**Development checklist:**
- Provide buttons for approve, rework, and abort.
- Require `must_fix` input for rework.

**Test after completion:**
- Run: `pnpm --dir apps/approval-console test -- approval_panel.spec.ts`

**Pass criteria:**
- Tests confirm rework cannot submit without at least one required fix item.

### Task 13.5: Add frontend integration with approval APIs

**Files:**
- Modify: `apps/approval-console/src/pages/task-detail.tsx`
- Create: `apps/approval-console/src/lib/api.ts`
- Test: `apps/approval-console/tests/task_detail_integration.spec.ts`

**Development checklist:**
- Integrate the task detail page with task and approval API endpoints.

**Test after completion:**
- Run: `pnpm --dir apps/approval-console test -- task_detail_integration.spec.ts`

**Pass criteria:**
- Tests confirm approval actions call the expected API and update UI state.

## Phase 14: Orchestrated End-to-End Flow

### Task 14.1: Add stubbed end-to-end happy path

**Files:**
- Create: `tests/e2e/test_happy_path_stubbed.py`

**Development checklist:**
- Simulate the full task lifecycle using stubbed explorer, planner, developer, reviewer, and test runner services.

**Test after completion:**
- Run: `pytest tests/e2e/test_happy_path_stubbed.py -v`

**Pass criteria:**
- Test confirms the task reaches final approval readiness through all stages.

### Task 14.2: Add develop-review iteration loop test

**Files:**
- Create: `tests/e2e/test_develop_review_loop.py`

**Development checklist:**
- Simulate one rework round between reviewer and developer.

**Test after completion:**
- Run: `pytest tests/e2e/test_develop_review_loop.py -v`

**Pass criteria:**
- Test confirms a review `rework` decision creates a new develop attempt rather than overwriting state.

### Task 14.3: Add approval pause and resume test

**Files:**
- Create: `tests/e2e/test_approval_pause_resume.py`

**Development checklist:**
- Pause the workflow at an approval boundary, restart the orchestrator context, and resume.

**Test after completion:**
- Run: `pytest tests/e2e/test_approval_pause_resume.py -v`

**Pass criteria:**
- Test confirms workflow resumes from persisted state without rerunning the previous completed stage.

### Task 14.4: Add worker failure recovery test

**Files:**
- Create: `tests/e2e/test_worker_failure_recovery.py`

**Development checklist:**
- Simulate a transient worker failure and a deterministic failure.
- Confirm retry and no-retry behavior differ correctly.

**Test after completion:**
- Run: `pytest tests/e2e/test_worker_failure_recovery.py -v`

**Pass criteria:**
- Test confirms transient failures can retry and deterministic failures route to rework or stop.

### Task 14.5: Add stale callback rejection test

**Files:**
- Create: `tests/e2e/test_stale_callback_rejection.py`

**Development checklist:**
- Submit a worker callback for an outdated stage attempt.

**Test after completion:**
- Run: `pytest tests/e2e/test_stale_callback_rejection.py -v`

**Pass criteria:**
- Test confirms stale callbacks do not mutate current task state.

## Phase 15: Observability, Security, and Drift Controls

### Task 15.1: Add structured stage logging

**Files:**
- Create: `packages/observability/logging.py`
- Test: `tests/observability/test_structured_logging.py`

**Development checklist:**
- Emit normalized logs for stage start, completion, failure, and approval.

**Test after completion:**
- Run: `pytest tests/observability/test_structured_logging.py -v`

**Pass criteria:**
- Tests confirm log payloads include task ID, stage, attempt, and event type.

### Task 15.2: Add trace correlation IDs

**Files:**
- Modify: `packages/observability/traces.py`
- Test: `tests/observability/test_trace_correlation.py`

**Development checklist:**
- Add correlation ID propagation across task, stage, and worker boundaries.

**Test after completion:**
- Run: `pytest tests/observability/test_trace_correlation.py -v`

**Pass criteria:**
- Tests confirm related logs and traces share the same correlation identifiers.

### Task 15.3: Add command redaction and secret filtering

**Files:**
- Create: `packages/observability/redaction.py`
- Test: `tests/observability/test_redaction.py`

**Development checklist:**
- Redact secrets from logs, artifact previews, and approval UI payloads.

**Test after completion:**
- Run: `pytest tests/observability/test_redaction.py -v`

**Pass criteria:**
- Tests confirm known secret patterns are removed or masked.

### Task 15.4: Add drift detection helper

**Files:**
- Create: `packages/workflow-engine/drift_policy.py`
- Test: `tests/workflow/test_drift_policy.py`

**Development checklist:**
- Detect branch drift, changed-path overlap, and stale plan/test environment conditions.

**Test after completion:**
- Run: `pytest tests/workflow/test_drift_policy.py -v`

**Pass criteria:**
- Tests confirm drift policy flags stale stages correctly.

### Task 15.5: Add drift revalidation flow

**Files:**
- Modify: `packages/workflow-engine/advance_service.py`
- Test: `tests/e2e/test_drift_revalidation.py`

**Development checklist:**
- Prevent advancement when drift policy requires revalidation.

**Test after completion:**
- Run: `pytest tests/e2e/test_drift_revalidation.py -v`

**Pass criteria:**
- Tests confirm stale plans or repo drift reopen the required earlier stage.

## Phase 16: Upstream Contribution Packaging

### Task 16.1: Define upstream contribution bundle schema

**Files:**
- Create: `packages/core-models/contracts/upstream_bundle.py`
- Test: `tests/core_models/test_upstream_bundle_contract.py`

**Development checklist:**
- Model patch series, commit messages, cover letter, recipients, sign-off, and test evidence references.

**Test after completion:**
- Run: `pytest tests/core_models/test_upstream_bundle_contract.py -v`

**Pass criteria:**
- Tests confirm the schema requires patch metadata and evidence references.

### Task 16.2: Add bundle builder service

**Files:**
- Create: `packages/workflow-engine/upstream_bundle_service.py`
- Test: `tests/workflow/test_upstream_bundle_service.py`

**Development checklist:**
- Build a contribution bundle from approved development, review, and test artifacts.

**Test after completion:**
- Run: `pytest tests/workflow/test_upstream_bundle_service.py -v`

**Pass criteria:**
- Tests confirm the bundle contains only approved artifacts and references.

### Task 16.3: Add export endpoint for contribution bundle

**Files:**
- Create: `apps/orchestrator-api/app/api/export.py`
- Test: `tests/api/test_export_bundle_api.py`

**Development checklist:**
- Add endpoint to retrieve or export the final upstream-ready bundle after final approval.

**Test after completion:**
- Run: `pytest tests/api/test_export_bundle_api.py -v`

**Pass criteria:**
- Tests confirm export is blocked until all required approvals and test results are present.

## Phase 17: Final Verification and Release Readiness

### Task 17.1: Add full backend test aggregate target

**Files:**
- Modify: `Makefile`
- Test: `tests/smoke/test_backend_test_target.py`

**Development checklist:**
- Add a single backend aggregate test command covering unit, integration, and e2e suites.

**Test after completion:**
- Run: `pytest tests/smoke/test_backend_test_target.py -v`

**Pass criteria:**
- Test confirms the Makefile exposes the expected aggregate target.

### Task 17.2: Add full frontend test aggregate target

**Files:**
- Modify: `Makefile`
- Test: `tests/smoke/test_frontend_test_target.py`

**Development checklist:**
- Add a frontend aggregate target for approval console tests.

**Test after completion:**
- Run: `pytest tests/smoke/test_frontend_test_target.py -v`

**Pass criteria:**
- Test confirms the frontend aggregate test target exists.

### Task 17.3: Run complete MVP regression suite

**Files:**
- No new files required
- Test: full backend and frontend suites

**Development checklist:**
- Run all backend tests.
- Run frontend approval console tests.
- Record the final passing test summary in release notes or task review notes.

**Test after completion:**
- Run: `pytest -v`
- Run: `pnpm --dir apps/approval-console test`

**Pass criteria:**
- All previously defined suites pass with no blocking failures.

### Task 17.4: Validate MVP walkthrough scenario manually and by test

**Files:**
- Create: `docs/plans/mvp-walkthrough-checklist.md`
- Test: `tests/e2e/test_mvp_walkthrough.py`

**Development checklist:**
- Write the exact manual walkthrough for the MVP scenario.
- Add an automated test mirroring the same happy path as far as the system allows.

**Test after completion:**
- Run: `pytest tests/e2e/test_mvp_walkthrough.py -v`

**Pass criteria:**
- Automated walkthrough passes and manual checklist reflects the actual implemented flow.

### Task 17.5: Final readiness review

**Files:**
- Update: `tasks/todo.md`
- Update: `docs/plans/2026-04-22-rv-insights-implementation.md`

**Development checklist:**
- Mark completed phases.
- Record remaining gaps, deferred work, and known risks.
- Confirm whether the MVP is ready for internal demo or needs another stabilization round.

**Test after completion:**
- Run: `pytest -q`

**Pass criteria:**
- Final review notes reflect actual test status and remaining work accurately.

## Recommended Execution Order

1. Phase 0 to Phase 2
2. Phase 3 to Phase 5
3. Phase 6 to Phase 7
4. Phase 8 to Phase 12
5. Phase 13 to Phase 17

## Recommended Verification Gates Between Phases

- After Phase 2: core schema and database tests all pass
- After Phase 5: API and workflow engine tests all pass
- After Phase 7: adapter and dispatch tests all pass
- After Phase 12: each worker service has passing unit and integration tests
- After Phase 14: e2e flow, retry, and approval-resume tests all pass
- After Phase 17: full regression suite passes

## Suggested Commit Rhythm

- one commit per checklist task where practical
- one merge or squash review per phase completion
- one tagged checkpoint after Phase 5, Phase 12, and Phase 17

Plan complete and saved to `docs/plans/2026-04-22-rv-insights-detailed-development-checklist.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
