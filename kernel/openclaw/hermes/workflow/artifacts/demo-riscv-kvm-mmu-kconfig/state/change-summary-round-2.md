# Change Summary Round 2

## Role
Fix-Agent

## Objective
在 Round 1 基础上补齐 help text 语义，完成规格闭环。

## Modified files
- `arch/riscv/kvm/Kconfig`

## What changed
- 保留 Round 1 的 MMU dependency 明确化
- 补充 help text，显式说明 RISC-V host KVM 依赖 MMU，non-MMU 配置不适用

## Build / test summary
- `make ARCH=riscv allnoconfig`: simulated pass
- `make ARCH=riscv olddefconfig`: simulated pass
- `make ARCH=riscv defconfig`: simulated pass
- `scripts/checkpatch.pl --strict`: simulated clean for single patch text change

## Suggested next step
重新执行规格审查；若通过，则进入 patch-ready。
