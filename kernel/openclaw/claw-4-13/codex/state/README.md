# State Files

`state/` is the pipeline's source of truth. Agents should exchange progress through these files instead of relying on chat context.

The schemas in `state/schema/` use JSON Schema Draft 2020-12. They validate JSON directly and can also be applied to YAML documents after parsing.

## Files

| File | Owner Agent | Updated When | Purpose |
| --- | --- | --- | --- |
| `gaps.repo.json` | `Repo Scanner` | After repository parity scans in Step-1 | Raw code-side gap candidates comparing `riscv`, `arm64`, and `x86` |
| `gaps.mail.json` | `Mailing List Miner` | After lore / yhbt mining in Step-1 | Raw mailing-list threads, signals, and discussion status tied to gap IDs |
| `gap_backlog.yaml` | `Gap Normalizer` | After deduping and triage, before Gap Review | Normalized backlog with severity, evidence bundle, and issue proposal fields |
| `issues.yaml` | `Issue Author` | After Step-2 issue creation | Persistent record of created GitHub issues and metadata |
| `claimed.yaml` | `Issue Claimer` | After issue assignment and branch planning | Ownership, assignee, status label, and issue-to-branch linkage |
| `review_todos.yaml` | `Review Feedback Miner` | After mailing-list replies land in lore | Action items extracted from review threads for v2/v3 follow-up |
| `reports/<issue>-verification.json` | `Verifier` | After independent validation in Step-4 | Pass/fail evidence for build, tests, perf, and blocking findings |

## Lifecycle

1. `Repo Scanner` writes `gaps.repo.json`.
2. `Mailing List Miner` writes `gaps.mail.json`.
3. `Gap Normalizer` merges both into `gap_backlog.yaml`.
4. `Issue Author` creates GitHub issues and records them in `issues.yaml`.
5. `Issue Claimer` adds assignee and branch ownership in `claimed.yaml`.
6. `Verifier` writes per-issue verification results using `verification.schema.json`.
7. `Review Feedback Miner` converts mailing-list responses into `review_todos.yaml`.

## Notes

- `gap_backlog.yaml`, `issues.yaml`, `claimed.yaml`, and `review_todos.yaml` may be stored as YAML for readability; use the matching schema after YAML parsing.
- Keep stable IDs across files: `gap_id`, `issue_number`, `message_id`, and `branch`.
- If a human gate overrides an automated decision, record the final outcome in the state file rather than only in chat.
