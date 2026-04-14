# Change Summary Round 1

## Role
Implementer

## Objective
根据 design.md 做第一轮最小实现。

## Modified files
- `arch/riscv/kvm/Kconfig`

## What changed
- 在 `CONFIG_RISCV_KVM` dependency 中显式加入 MMU 约束
- 未修改 help text

## Build / test summary
- `make ARCH=riscv olddefconfig`: simulated pass
- `make ARCH=riscv defconfig`: simulated pass
- 未观察到新的 dependency 解析错误

## Known limitations
- help text 仍然只隐含 host/KVM/MMU 关系，没有明确说明 non-MMU 场景不适用
- 这意味着“代码层 dependency 更准确了”，但“读者层语义澄清”仍可能不足

## Suggested next step
进入 Spec-Review
