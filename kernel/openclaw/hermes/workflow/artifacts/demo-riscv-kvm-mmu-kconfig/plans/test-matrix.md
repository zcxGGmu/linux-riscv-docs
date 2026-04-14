# Test Matrix

## Role
Planner

## Objective
为 demo issue 提供最小但充分的验证矩阵。

## Must-have checks
1. Kconfig visibility sanity
   - 目标：确认 non-MMU 配置下 `CONFIG_RISCV_KVM` 不再呈现误导性可选状态，或帮助文本清楚说明限制
   - 方法：对比修改前后 Kconfig dependency/help text

2. RISC-V config resolution
   - 命令示例：
     - `make ARCH=riscv allnoconfig`
     - `make ARCH=riscv olddefconfig`
   - 目标：确认 Kconfig 解析无异常

3. RISC-V build smoke check
   - 命令示例：
     - `make ARCH=riscv defconfig`
     - `make ARCH=riscv -j$(nproc) arch/riscv/kvm/`
   - 目标：确认 Kconfig 改动未导致基础构建问题

## Nice-to-have checks
- x86/arm64 对照阅读，仅用于确认 RISC-V 帮助文本叙事与其他架构 host KVM 一致
- `scripts/checkpatch.pl` 对 patch 文本进行基本检查

## Regression focus
- 不应改变默认值
- 不应影响 unrelated KVM symbols
- 不应引入新的 unmet dependency warning

## Failure routing
- 若是 dependency 逻辑与设计不一致：回到 Spec-Review 或 Failure-Analyzer
- 若是构建/配置解析问题：进入 Failure-Analyzer
- 若只是 help text 仍不清晰：优先走 Spec-Review，再决定是否进入 debug

## Decision
PASS

## Next Recommended Step
进入实现阶段。
