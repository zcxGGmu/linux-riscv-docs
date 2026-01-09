# SIMD 深入 1：RVV 子扩展（ZV*）在 KVM ISA 掩码中的可用性与 guest 暴露策略

## 结论摘要
- **现状**：RISC-V KVM 对 ZV*（向量加密/向量 BF16/向量 FP16 等）**采取“宿主镜像暴露”策略**——只要宿主内核认为该扩展可用，就会默认暴露给 guest。
- **问题**：KVM 几乎没有提供 “按 VM/按 vCPU 精细开关 ZV*” 的策略接口；多数字扩展 **不可禁用**，导致迁移与兼容策略受限。

## 关键证据（代码层）
1. **KVM 扩展映射表包含 ZV***：
   - `arch/riscv/kvm/vcpu_onereg.c` 的 `kvm_isa_ext_arr[]` 将 `KVM_RISCV_ISA_EXT_ZV*` 映射为 host ISA bit。

```c
// arch/riscv/kvm/vcpu_onereg.c
KVM_ISA_EXT_ARR(ZVBB), KVM_ISA_EXT_ARR(ZVBC), KVM_ISA_EXT_ARR(ZVFBFMIN), ...
```

2. **默认启用策略 = host 可用即启用**：
   - `kvm_riscv_vcpu_setup_isa()` 遍历映射表：
     - 若宿主有扩展且允许启用 -> 设置到 guest ISA bitmap。

```c
// arch/riscv/kvm/vcpu_onereg.c
if (kvm_riscv_vcpu_isa_enable_allowed(i))
    set_bit(guest_ext, vcpu->arch.isa);
```

3. **ZV* 扩展“不可禁用”**：
   - `kvm_riscv_vcpu_isa_disable_allowed()` 中 **大量扩展（含 ZV*）返回 false**。

```c
// arch/riscv/kvm/vcpu_onereg.c
case KVM_RISCV_ISA_EXT_ZVBB:
case KVM_RISCV_ISA_EXT_ZVBC:
case KVM_RISCV_ISA_EXT_ZVFBFMIN:
case KVM_RISCV_ISA_EXT_ZVFH:
case KVM_RISCV_ISA_EXT_ZVFHMIN:
case KVM_RISCV_ISA_EXT_ZVKB:
case KVM_RISCV_ISA_EXT_ZVKG:
case KVM_RISCV_ISA_EXT_ZVKNED:
case KVM_RISCV_ISA_EXT_ZVKNHA:
case KVM_RISCV_ISA_EXT_ZVKNHB:
case KVM_RISCV_ISA_EXT_ZVKSED:
case KVM_RISCV_ISA_EXT_ZVKSH:
case KVM_RISCV_ISA_EXT_ZVKT:
    return false;
```

4. **宿主侧能力校验由 cpufeature 完成**：
   - `arch/riscv/kernel/cpufeature.c` 对 ZV* 进行 validate（依赖 ZVE32X / vector crypto 约束），KVM 直接继承宿主结论。

## 当前暴露策略的行为总结
- ZV* 是否暴露 = 宿主是否支持 + KVM 是否允许启用（默认允许）。
- **缺少 per-VM policy**：用户态难以在同一 host 上对不同 VM 精细控制 ZV*。
- **不可禁用**：即便用户态希望关闭 ZV*，KVM 也会拒绝。

## 影响
- **迁移/兼容问题**：不同主机的 ZV* 支持不一致时，无法通过 guest 侧屏蔽来获得兼容性。
- **安全/性能策略缺失**：难以针对特定 VM 关闭向量加密或特殊算术扩展。

## 可改进方向（建议）
1. **允许禁用 ZV* 扩展**
   - 调整 `kvm_riscv_vcpu_isa_disable_allowed()`，为 ZV* 提供可控禁用策略。
2. **引入 per-VM 策略接口**
   - 增加 KVM capability 或 VM 属性，用于声明允许的 ZV* 子集。
3. **依赖关系校验**
   - 当禁用某些 ZV* 时，需与 `cpufeature` 的依赖逻辑对齐，避免暴露非法组合。

## 参考文件
- `arch/riscv/kvm/vcpu_onereg.c`
- `arch/riscv/include/uapi/asm/kvm.h`
- `arch/riscv/kernel/cpufeature.c`
