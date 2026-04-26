# Failure Modes and Classification Rules

Use this reference when the request is ambiguous, easy to over-trigger, or easy to under-trigger.

## 1. Mis-trigger patterns

These requests should usually **not** activate the full Agent4/5 workflow:
- asking for a quick explanation of one error, one command, or one concept
- asking for a tiny edit with no verification loop or follow-up ownership
- asking for translation, rewriting, formatting, or summary only
- asking for general RISC-V background knowledge with no execution intent

Why mis-trigger happens:
- the request contains words like `优化`, `review`, or `修复`, but the user only wants advice
- the request mentions `PR` or `CI`, but only wants the status explained, not handled

Safe response pattern:
- answer directly first
- do not create a workflow plan unless the user asks for ownership, iteration, validation, or follow-up

## 2. Miss-trigger patterns

These requests **should** activate the workflow even if the user does not say `Agent4` or `Agent5`:
- the user asks to `接管`, `推进`, `跟到底`, `闭环`, or `带着往前走`
- the user asks for `先规划再实现`
- the user asks to track `CI`, `review comments`, `社区反馈`, or `再次提交`
- the user provides logs, diffs, patches, and asks for a fix plus verification

Why miss-trigger happens:
- the wording is colloquial and does not contain the formal workflow names
- the user describes a loop implicitly rather than explicitly

Safe response pattern:
- infer likely workflow ownership from verbs like `接管`, `推进`, `盯着`, `跟进`
- classify before acting, then start the first-turn takeover template

## 3. Mode classification rules

Choose **Agent4** when most of the work is:
- understanding constraints
- building a plan
- implementing or refining a technical change
- running focused self-tests
- iterating toward review readiness

Choose **Agent5** when most of the work is:
- responding to CI failures
- addressing reviewer or maintainer feedback
- refreshing patches, commit messages, PR text, or submission artifacts
- re-validating and resubmitting after external feedback

Choose **Hybrid** when:
- the patch still needs technical work and also needs contribution follow-up
- the user wants end-to-end ownership from planning to submission closure
- implementation and external feedback handling are both first-class parts of the task

## 4. Borderline examples

### Example A
`解释一下这个 RISC-V 报错是什么意思`

- Default: do **not** trigger
- Reason: explanation only, no ownership loop

### Example B
`帮我修这个 RISC-V 兼容性问题，并把验证结论补齐`

- Default: trigger **Agent4**
- Reason: implementation + verification loop

### Example C
`这个 PR 被 review 打回来了，帮我改完并重新整理提交内容`

- Default: trigger **Agent5**
- Reason: feedback handling + resubmission

### Example D
`这个补丁从拆计划到修复、再到 CI 和 review 跟进都交给你`

- Default: trigger **Hybrid**
- Reason: full ownership across build and contribution loops

## 5. Escalation rule

If the first classification was too light:
- upgrade from no-skill → Agent4 when a real execution plan becomes necessary
- upgrade from Agent4 → Hybrid when CI/review/community follow-up becomes part of the task
- upgrade from Agent5 → Hybrid when the feedback reveals deeper technical rework is needed

If uncertain, prefer the lightest mode that still preserves ownership, then upgrade explicitly once evidence appears.
