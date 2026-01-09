# RISC-V KVM 缺失特性：VFIO 直通与 IRQ bypass（低延迟中断直注入）

## 差异概述
arm64 KVM 启用了 `KVM_VFIO` 和 `HAVE_KVM_IRQ_BYPASS`，并实现了 GICv4/vLPI 的中断直通注入路径；RISC-V KVM 未选择相关配置，也缺少 arch 级 irq bypass 实现。

## arm64 现状（实现要点）
- Kconfig 选择：`arch/arm64/kvm/Kconfig` 中 `select KVM_VFIO`、`select HAVE_KVM_IRQ_BYPASS`。
- irq bypass 入口：`arch/arm64/kvm/arm.c`
  - `kvm_arch_irq_bypass_add_producer()`/`del_producer()`
  - 通过 `kvm_vgic_v4_set_forwarding()` 实现 LPI 直注入。

参考代码片段（arm64）：
```c
// arch/arm64/kvm/arm.c
int kvm_arch_irq_bypass_add_producer(...){
    if (irq_entry->type != KVM_IRQ_ROUTING_MSI)
        return 0;
    return kvm_vgic_v4_set_forwarding(...);
}
```

## RISC-V 现状（缺失与证据）
- `arch/riscv/kvm/Kconfig` 未选择 `KVM_VFIO`、`HAVE_KVM_IRQ_BYPASS`。
- `arch/riscv/kvm` 中未实现 `kvm_arch_irq_bypass_*` 回调。

## 缺失影响
- VFIO 直通（尤其 PCIe 设备）缺乏与 KVM 的深度协作。
- 中断注入路径仍需经由内核软件注入，时延与抖动更大。

## 可支持性分析（RISC-V 侧）
- RISC-V AIA/IMSIC 支持 MSI 直接投递，具备实现“中断直注入”的硬件基础。
- 可在 KVM 中实现 IMSIC 的直注入绑定，与 VFIO/MSI 中断管理对接。

## 设计/实现路径建议
1. **Kconfig 能力开启**
   - 在 `arch/riscv/kvm/Kconfig` 增加 `select KVM_VFIO` 与 `select HAVE_KVM_IRQ_BYPASS`。
2. **irq bypass hooks**
   - 在 `arch/riscv/kvm` 实现 `kvm_arch_irq_bypass_add_producer()` 等接口。
   - 为 MSI 路由建立 IMSIC 直注入绑定（类似 arm64 的 vLPI forwarding）。
3. **AIA/IMSIC 直注入绑定**
   - 扩展 `arch/riscv/kvm/aia_*` 逻辑，支持将 host irqfd 与 guest IMSIC 目标绑定。
4. **VFIO 与 IOMMU 协作**
   - 需要确保 IOMMU 映射与中断路由的一致性，避免直通设备破坏隔离。

## 关键难点
- AIA/IMSIC 直注入的生命周期管理（设备解绑、irqfd 更新、迁移）。
- guest 侧 IMSIC 页面布局与 MSI doorbell 配置的 ABI 稳定性。

## 参考文件（建议阅读）
- `arch/arm64/kvm/Kconfig`
- `arch/arm64/kvm/arm.c`
- `arch/arm64/kvm/vgic/vgic-v4.c`
- `arch/riscv/kvm/aia_imsic.c`
- `arch/riscv/kvm/aia_device.c`
