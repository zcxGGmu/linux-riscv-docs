# Risk Review

## Role
Risk-Reviewer

## Objective
识别 demo issue 的风险边界，并标记是否需要人工闸门。

## Risk items

### Risk Item 1
- Severity: low
- Item: Kconfig 用户可见文本/依赖变化
- Why it matters: 虽不涉及运行时行为，但会改变用户读取配置时的理解，属于用户可见配置层变更
- Mitigation: 保持改动最小，只澄清 MMU 依赖，不改默认值与菜单结构
- Human gate needed?: yes

### Risk Item 2
- Severity: low
- Item: 过度扩展为 broader RISC-V KVM cleanup
- Why it matters: 容易破坏“一个 patch 一个问题”的上游偏好
- Mitigation: 严格限制在 `arch/riscv/kvm/Kconfig`
- Human gate needed?: no

### Risk Item 3
- Severity: low
- Item: dependency 改了但 help text 仍含糊
- Why it matters: 会导致“看似修了，实际仍然误导”的半成品 patch
- Mitigation: 审查时同时检查 dependency 和 help text
- Human gate needed?: no

## Summary
- ABI / UAPI: none
- DT / firmware ABI: none
- Kconfig user-visible change: yes, but low risk
- Rollback difficulty: trivial

## Decision
NEED_HUMAN

## Next Recommended Step
通过 Gate-2 后进入实现；审查时把“是否同时修正 help text”作为必查项。
