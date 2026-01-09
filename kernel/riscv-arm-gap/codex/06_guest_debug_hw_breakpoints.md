# RISC-V KVM 缺失特性：完善的 Guest Debug（单步/硬件断点/观察点）

## 差异概述
arm64 KVM 实现了完整的 guest debug 支持（单步、断点/观察点寄存器虚拟化、调试异常路由等）；RISC-V KVM 仅对 `KVM_GUESTDBG_ENABLE` 做最小化处理（主要是对断点异常的委派控制），缺乏调试寄存器/触发器的虚拟化。

## arm64 现状（实现要点）
- 主逻辑位于 `arch/arm64/kvm/debug.c`：
  - 配置 MDCR_EL2 以捕获调试/性能/追踪访问。
  - 管理断点/观察点寄存器的拥有权与加载策略。
  - 支持 `KVM_GUESTDBG_SINGLESTEP` / `KVM_GUESTDBG_USE_HW` 等控制。

参考代码片段（arm64）：
```c
// arch/arm64/kvm/debug.c
if (vcpu->guest_debug & KVM_GUESTDBG_SINGLESTEP)
    mdscr |= MDSCR_EL1_SS;
if (vcpu->guest_debug & KVM_GUESTDBG_USE_HW)
    mdscr |= MDSCR_EL1_MDE | MDSCR_EL1_KDE;
```

## RISC-V 现状（缺失与证据）
- `arch/riscv/kvm/vcpu.c` 中 `kvm_arch_vcpu_ioctl_set_guest_debug()` 仅修改 `hedeleg`，未处理触发器寄存器或单步控制：

```c
// arch/riscv/kvm/vcpu.c
if (dbg->control & KVM_GUESTDBG_ENABLE) {
    vcpu->guest_debug = dbg->control;
    vcpu->arch.cfg.hedeleg &= ~BIT(EXC_BREAKPOINT);
} else {
    vcpu->guest_debug = 0;
    vcpu->arch.cfg.hedeleg |= BIT(EXC_BREAKPOINT);
}
```

## 缺失影响
- 用户态调试器无法可靠地对 guest 设置硬件断点/观察点。
- 单步/调试异常行为与 arm64/x86 不一致，影响跨架构调试体验。

## 可支持性分析（RISC-V 侧）
- RISC-V Debug 规范提供 trigger CSRs（如 `tselect/tdata*`），理论上可在 HS 中虚拟化并转发给 VS guest。
- 通过 trap-and-emulate 可实现对 debug CSRs 的访问控制与保存恢复。

## 设计/实现路径建议
1. **虚拟触发器寄存器**
   - 在 `struct kvm_vcpu_arch` 中保存虚拟 tselect/tdata* 状态。
   - 在 CSR 访问陷入路径中模拟读写（拦截 VS 对调试寄存器的访问）。
2. **单步与断点异常路由**
   - 在 vcpu 运行/退出路径中支持 `KVM_GUESTDBG_SINGLESTEP`。
   - 将断点异常定向到 KVM，必要时注入到 guest 或返回用户态。
3. **与用户态接口对接**
   - 扩展 `KVM_GUESTDBG_*` 行为，支持 `KVM_GUESTDBG_USE_HW` 等语义。

## 关键难点
- RISC-V 调试触发器对 VS-mode 的可见性与可用性因实现而异。
- 触发器数量有限，需要分配策略与抢占恢复机制。

## 参考文件（建议阅读）
- `arch/arm64/kvm/debug.c`
- `arch/riscv/kvm/vcpu.c`
