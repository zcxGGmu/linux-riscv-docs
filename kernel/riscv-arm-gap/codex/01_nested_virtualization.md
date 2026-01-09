# RISC-V KVM 缺失特性：嵌套虚拟化（Nested Virtualization）

## 差异概述
arm64 KVM 已实现较完整的嵌套虚拟化框架（L1 guest 作为 hypervisor 运行 L2 guest），包含嵌套 S2 MMU、VNCR 管理、以及 GICv3 嵌套中断等配套逻辑；而 RISC-V KVM 当前明确未实现嵌套虚拟化，相关 SBI HFENCE 路径直接返回不支持。

## arm64 现状（实现要点）
- 核心实现位于 `arch/arm64/kvm/nested.c`，包含：
  - 嵌套 S2 MMU 初始化与生命周期管理（`kvm_init_nested()`、`kvm_vcpu_init_nested()`）。
  - VNCR（虚拟化 EL2 寄存器）映射/缓存与相关 TLB 处理。
  - 嵌套 S2 页表的 walk/校验逻辑。
- 指令/系统寄存器层面的嵌套仿真：`arch/arm64/kvm/emulate-nested.c`。
- GICv3 嵌套：`arch/arm64/kvm/vgic/vgic-v3-nested.c`。

参考代码片段（arm64）：
```c
// arch/arm64/kvm/nested.c
void kvm_init_nested(struct kvm *kvm) { ... }
int kvm_vcpu_init_nested(struct kvm_vcpu *vcpu) { ... }
```

## RISC-V 现状（缺失与证据）
- arch/riscv/kvm 未见嵌套虚拟化的核心实现文件（无 nested.c/emulate-nested.c）。
- SBI RFENCE 扩展对 HFENCE（用于嵌套 TLB 刷新）明确返回不支持：

```c
// arch/riscv/kvm/vcpu_sbi_replace.c
case SBI_EXT_RFENCE_REMOTE_HFENCE_GVMA:
case SBI_EXT_RFENCE_REMOTE_HFENCE_GVMA_VMID:
case SBI_EXT_RFENCE_REMOTE_HFENCE_VVMA:
case SBI_EXT_RFENCE_REMOTE_HFENCE_VVMA_ASID:
    /* Until nested virtualization is implemented ... */
    retdata->err_val = SBI_ERR_NOT_SUPPORTED;
```

## 缺失影响
- L1 hypervisor 无法在 guest 内运行 L2 guest，限制云原生虚拟化、嵌套测试、轻量云平台（如 KubeVirt-in-VM）的部署。
- HFENCE 相关 SBI 路径缺失意味着无法正确维护嵌套页表与 TLB 一致性。

## 可支持性分析（RISC-V 侧）
- RISC-V H 扩展提供 HS/VS 模式与二级地址转换（G-stage），理论上可以通过“陷入+影子页表”方式实现嵌套。
- 需要在 HS 中虚拟化“Guest 的 H 扩展行为”，即让 VS guest 看到虚拟的 hgatp/hstatus/hie/hvip 等，并为其维护虚拟的 G-stage（影子 S2）。
- 虽缺少硬件 NV 扩展，但软件仿真路径是可行的（arm64 也有大量软件仿真）。

## 设计/实现路径建议
1. **嵌套状态与寄存器建模**
   - 在 `struct kvm_vcpu_arch` 增加虚拟 H 扩展寄存器组（虚拟 hgatp/hstatus/hcounteren/hien 等）。
   - 扩展 `vcpu_onereg`/`vcpu_sbi` 以支持 L1 访问这些虚拟寄存器。
2. **影子 G-stage（嵌套 S2）**
   - 复用 `arch/riscv/kvm/gstage.c` 的页表管理，新增 nested gstage 对象与回收策略。
   - 实现 L2 GPA -> L1 GPA -> HPA 的双层翻译，必要时建立缓存以减少 walk 开销。
3. **SBI HFENCE 虚拟化**
   - 在 `vcpu_sbi_replace.c` 中实现 HFENCE 分支，驱动影子页表与 TLB 刷新。
4. **AIA 嵌套中断**
   - 需要对 AIA（APLIC/IMSIC）做 L1 级虚拟化，让 L1 能为 L2 提供虚拟 IMSIC 页面。

## 关键难点
- 影子页表性能开销与一致性维护（尤其是 L1 的页表更新频繁时）。
- AIA 嵌套的中断重映射与注入路径设计。
- 与现有 SBI/NACL 加速路径的交互（避免破坏现有 HS/VS 切换加速）。

## 参考文件（建议阅读）
- `arch/arm64/kvm/nested.c`
- `arch/arm64/kvm/emulate-nested.c`
- `arch/arm64/kvm/vgic/vgic-v3-nested.c`
- `arch/riscv/kvm/vcpu_sbi_replace.c`
- `arch/riscv/kvm/gstage.c`
