# SIMD 差异 1：可配置向量长度/ABI（arm64 SVE） vs 固定 RVV（riscv）

## 差异概述
- **arm64 KVM**：完整支持 SVE（Scalable Vector Extension），并提供 **可配置的向量长度（VL）** 与 **明确的 KVM ABI**（`KVM_CAP_ARM_SVE`、`KVM_REG_ARM64_SVE*`、`KVM_ARM_VCPU_SVE`）。
- **riscv KVM**：支持 RVV 基本向量上下文保存/恢复，但 **向量寄存器长度固定为宿主 VLEN**，`vlenb` 只读，缺少“guest 可协商/限制向量长度”的 ABI 与能力查询。

## arm64 现状（代码证据）
1. **KVM 能力与 SVE 启用**：
   - `arch/arm64/kvm/arm.c` 中 `KVM_CAP_ARM_SVE`。
   - `arch/arm64/kvm/reset.c` 中 `kvm_arm_init_sve()`、`kvm_vcpu_enable_sve()`。
2. **SVE 向量长度配置与寄存器 ABI**：
   - `arch/arm64/kvm/guest.c` 提供 `KVM_REG_ARM64_SVE_*`、`KVM_REG_ARM64_SVE_VLS` 的 get/set。
   - `arch/arm64/kvm/reset.c` 的 `kvm_vcpu_finalize_sve()` 依据选择的 VL 分配状态。

相关片段（arm64）：
```c
// arch/arm64/kvm/arm.c
case KVM_CAP_ARM_SVE:
    r = system_supports_sve();
    break;
```

```c
// arch/arm64/kvm/reset.c
static void kvm_vcpu_enable_sve(struct kvm_vcpu *vcpu) { ... }
static int kvm_vcpu_finalize_sve(struct kvm_vcpu *vcpu) { ... }
```

## riscv 现状（缺失与证据）
1. **没有 KVM_CAP / enable_cap 用于 RVV**：
   - `arch/riscv/kvm/vm.c` 中 `kvm_vm_ioctl_check_extension()` 未提供 RVV 能力项。
2. **向量长度固定且只读**：
   - `arch/riscv/kvm/vcpu_vector.c`：
     - `vlenb` 初始化为 `riscv_v_vsize / 32`（宿主固定 VLEN）。
     - `set_reg_vector()` 中若写 `vlenb`，只能写回相同值（实质只读）。

```c
// arch/riscv/kvm/vcpu_vector.c
cntx->vector.vlenb = riscv_v_vsize / 32;
...
if (reg_num == KVM_REG_RISCV_VECTOR_CSR_REG(vlenb)) {
    if (reg_val != cntx->vector.vlenb)
        return -EINVAL;
}
```

## 影响
- **缺少向量长度协商能力**，导致：
  - live migration 或跨平台兼容性差（VLEN 不一致的主机无法迁移）。
  - 上层管理软件难以在同一镜像中适配不同 VLEN 主机。
- **ABI 不完整**：缺少类似 `KVM_CAP_ARM_SVE` 的机制来显式声明/选择 RVV 规格。

## 可支持性分析（RISC-V 侧）
- RVV 硬件 VLEN 固定，但 KVM 可以实现 **“虚拟 VLEN=宿主 VLEN 的子集”** 的模型，用于迁移/兼容。
- 需要在 KVM 中建立 **虚拟 vlenb** 与寄存器布局映射，并在必要时通过陷入/模拟限制 VLEN 可见性。

## 实现路径建议
1. **增加 RVV 能力 ABI**
   - 新增 `KVM_CAP_RISCV_VECTOR`（或扩展 `KVM_CAP_RISCV_*`）以报告 VLEN、支持的最小/最大 VLEN。
2. **虚拟 vlenb 与状态布局**
   - 在 `struct kvm_vcpu_arch` 中保存 `guest_vlenb`，允许用户态设定。
   - `kvm_riscv_vcpu_alloc_vector_context()` 依据 `guest_vlenb` 分配。
3. **VLEN 限制与一致性**
   - 在 `vsetvl/vsetvli` 路径或非法指令陷入中强制 guest 不超出 `guest_vlenb`。
   - 若不做指令仿真，可限制为“仅当 guest_vlenb == host_vlenb”时启用 RVV。

## 关键难点
- RVV 指令对 VLEN 强依赖，真正的“缩短 VLEN 虚拟化”可能需要指令仿真或硬件支持。
- 迁移场景下需要定义 VLEN 不一致时的策略（禁止迁移或引入软件适配层）。

## 参考文件
- `arch/arm64/kvm/arm.c`
- `arch/arm64/kvm/reset.c`
- `arch/arm64/kvm/guest.c`
- `arch/riscv/kvm/vm.c`
- `arch/riscv/kvm/vcpu_vector.c`
