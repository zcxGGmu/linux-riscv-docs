# Agent4/5 Workflow Reference

## Agent4: Optimization workflow

Source abstraction from `ys-claw.pptx`:
- Step 1: 外部知识接入 → LLM Wiki / 结构化知识页
- Step 2: 规划拆解 → Plan Mode / Todo / 验收点
- Step 3: 协同开发 → Agent Teams / 实现 / Self-test
- Step 4: Review Gate → diff / logs / tests / issues / fix advice
- Exit condition: review confirms correctness

## Agent4 operating intent

Use Agent4 when the work is primarily “understand, plan, implement, validate”.
It is a build-and-review loop, not a one-shot answer.

## Agent5: Contribution workflow

Source abstraction from `ys-claw.pptx`:
- Inputs: repository state, submission norms, project knowledge, external feedback events
- Execution resources: project skills, tools, action modules, build env, test platform, internet, MCP / APIs / CLI
- Outputs: regression test result, commit generation, PR/Patch update, review feedback monitoring
- Triggered continuation: when CI fails, review arrives, or a new external event occurs
- Core action: attribution and repair orchestration, then re-validation and resubmission

## Agent5 operating intent

Use Agent5 when the work is primarily “observe community/system feedback, attribute, fix, re-verify, resubmit”.
It is a contribution-closure loop, not just code editing.

## Hybrid rule

Many real tasks are hybrid:
- first use Agent4 to produce or refine the patch
- then use Agent5 to react to CI / review / maintainer feedback
- continue until the contribution is accepted or the user pauses the work
