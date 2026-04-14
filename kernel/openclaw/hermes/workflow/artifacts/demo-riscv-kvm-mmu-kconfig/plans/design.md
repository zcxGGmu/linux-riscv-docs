# Design Plan

## Role
Planner

## Objective
把 demo issue 转化为可执行、可验证、可回滚的最小改动方案。

## Problem definition
`CONFIG_RISCV_KVM` 的依赖表达/帮助文本未充分把 host KVM 对 MMU 的依赖说清楚。即使底层实现事实上依赖 MMU，配置层若表述不清，仍会给探索 non-MMU 配置、阅读 Kconfig 帮助或做跨架构对照的人带来误导。

## Root-cause hypothesis
问题不在运行时代码，而在于配置层语义表达不够显式：
- dependency 没有足够直观地体现 MMU 约束，或
- help text 没有把 host-only / MMU-required 的前提说清楚，或
- 两者同时存在表达不足

## Refutation points
如果以下任一条件成立，则应停止当前方案并回到人工判断：
1. `CONFIG_RISCV_KVM` 实际上支持 non-MMU 场景
2. MMU 约束已经在目标 Kconfig 项完整、明确地表达
3. 问题真正根因是别的配置符号，而不是 `CONFIG_RISCV_KVM`

## Minimal change path
1. 只修改 `arch/riscv/kvm/Kconfig`
2. 让 `CONFIG_RISCV_KVM` 的 dependency 与 help text 都显式体现 host KVM 依赖 MMU
3. 不修改运行时代码
4. 不修改默认配置，除非验证表明现有默认配置文本会产生明显歧义

## File-level change list
- Modify: `arch/riscv/kvm/Kconfig`
- Review only:
  - `arch/riscv/Kconfig`
  - `arch/riscv/configs/defconfig`

## Must-not-do boundary
- 不引入新的 Kconfig symbol
- 不修改 KVM runtime 行为
- 不顺手整理无关 help text
- 不扩展为文档大修

## Patch split suggestion
- 单 patch 即可：`riscv/kvm: make MMU dependency explicit in Kconfig help text`

## Rollback strategy
- 该变更为纯 Kconfig 一致性修复，若审查不接受，可直接整 patch 回退
- 不涉及持久化格式或运行时 ABI，因此回滚成本极低

## Risks / pending confirmations
- 风险低，但属于 Kconfig 用户可见文本/依赖变化，需要在 Gate-2 明确记录
- 若 dependency 实际已包含 MMU，仅补 help text 即可，不应重复改动 dependency

## Decision
PASS

## Next Recommended Step
按测试矩阵执行最小实现，先做 dependency 调整，再接受规格审查。
