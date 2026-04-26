# Todo

- [x] Review lessons and local instructions
- [x] Inspect source docs and workflow
- [x] Design skill behavior and scope
- [x] Implement skill files and docs
- [x] Validate outputs and summarize
- [x] Review current skill trigger design
- [x] Strengthen trigger vocabulary
- [x] Add first-turn takeover template
- [ ] Self-review and summarize

## Review

- Extracted Agent4 workflow from `../ys-claw.pptx`: knowledge intake → planning → implementation → review gate.
- Extracted Agent5 workflow from `../ys-claw.pptx`: feedback monitoring → attribution → repair orchestration → re-validation → resubmission.
- Encoded both as a single triggerable skill for OpenClaw with hybrid mode support.
- Kept frontmatter concise for trigger quality, while moving detailed behavior into `references/` to reduce context cost.
- Expanded frontmatter and in-body trigger phrases to better catch planning, CI triage, review feedback, PR/patch refresh, and resubmission requests.
- Added a first-turn takeover template so OpenClaw starts with mode, captured inputs, checklist plan, and immediate next action.
