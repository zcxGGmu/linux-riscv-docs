# Todo

- [x] Review lessons and local instructions
- [x] Inspect source docs and workflow
- [x] Design skill behavior and scope
- [x] Implement skill files and docs
- [x] Validate outputs and summarize
- [x] Review current skill trigger design
- [x] Strengthen trigger vocabulary
- [x] Add first-turn takeover template
- [x] Self-review and summarize
- [x] Add colloquial trigger examples
- [x] Update task review notes
- [x] Self-check wording and structure
- [x] Re-review current skill text
- [x] Group trigger examples by scenario
- [x] Add non-trigger guardrails
- [x] Tighten takeover guidance
- [x] Update task notes and summarize
- [x] Design failure-mode taxonomy
- [x] Add failure-modes reference
- [x] Link decision rules in skill
- [x] Update task notes and self-check

## Review

- Extracted Agent4 workflow from `../ys-claw.pptx`: knowledge intake → planning → implementation → review gate.
- Extracted Agent5 workflow from `../ys-claw.pptx`: feedback monitoring → attribution → repair orchestration → re-validation → resubmission.
- Encoded both as a single triggerable skill for OpenClaw with hybrid mode support.
- Kept frontmatter concise for trigger quality, while moving detailed behavior into `references/` to reduce context cost.
- Expanded frontmatter and in-body trigger phrases to better catch planning, CI triage, review feedback, PR/patch refresh, and resubmission requests.
- Added a first-turn takeover template so OpenClaw starts with mode, captured inputs, checklist plan, and immediate next action.
- Added colloquial Chinese request examples to improve automatic triggering on natural user phrasing.
- Reorganized trigger examples into Agent4, Agent5, and Hybrid buckets for easier maintenance.
- Added non-trigger guardrails so simple Q&A or tiny edits do not accidentally activate the workflow.
- Tightened first-turn guidance to keep takeover concise and operational.
- Added a dedicated failure-modes reference covering mis-trigger, miss-trigger, classification, and escalation rules.
- Linked ambiguous-trigger handling in the main skill back to the failure-modes reference.
