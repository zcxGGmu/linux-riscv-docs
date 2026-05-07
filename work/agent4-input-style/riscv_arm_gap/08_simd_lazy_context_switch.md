# SIMD 差异 2：EL2/HS Trap 触发的懒惰保存（arm64）vs 入口/退出即时保存（riscv）

## 差异概述
- **arm64 KVM**：采用“**首次访问触发陷入** + **懒惰切换**”的 FP/SIMD 管理策略，只有当 guest 真正触发 FP/SIMD/SVE 指令时才保存/恢复寄存器。
- **riscv KVM**：在 vCPU 进入/退出时直接保存/恢复 FP 与向量上下文，缺少 trap 驱动的懒惰切换机制。

## arm64 现状（代码证据）
1. **懒惰切换与 trap 处理**：
   - `arch/arm64/kvm/hyp/include/hyp/switch.h`：
     - `fpsimd_lazy_switch_to_guest()` / `fpsimd_lazy_switch_to_host()`
     - `kvm_hyp_handle_fpsimd()` 处理 FP/ASIMD/SVE trap
   - `arch/arm64/kvm/hyp/vhe/switch.c` / `arch/arm64/kvm/hyp/nvhe/switch.c`：
     - 将 `ESR_ELx_EC_FP_ASIMD`、`ESR_ELx_EC_SVE` 绑定到 `kvm_hyp_handle_fpsimd()`
2. **上下文协调**：
   - `arch/arm64/kvm/fpsimd.c`：在 guest/host 之间维护 FP ownership，避免不必要的寄存器保存。

相关片段（arm64）：
```c
// hyp/include/hyp/switch.h
static inline bool kvm_hyp_handle_fpsimd(struct kvm_vcpu *vcpu, u64 *exit_code)
{
    /* trap-first-use: save host, restore guest lazily */
}
```

```c
// hyp/vhe/switch.c
[ESR_ELx_EC_FP_ASIMD] = kvm_hyp_handle_fpsimd,
[ESR_ELx_EC_SVE]      = kvm_hyp_handle_fpsimd,
```

## riscv 现状（缺失与证据）
1. **进入/退出直接保存恢复**：
   - `arch/riscv/kvm/vcpu.c` 中 `kvm_arch_vcpu_load()` / `kvm_arch_vcpu_put()`：
     - 入口：`kvm_riscv_vcpu_host_fp_save()` + `kvm_riscv_vcpu_guest_fp_restore()`
     - 入口：`kvm_riscv_vcpu_host_vector_save()` + `kvm_riscv_vcpu_guest_vector_restore()`
     - 退出：`kvm_riscv_vcpu_guest_fp_save()` + `kvm_riscv_vcpu_host_fp_restore()`
     - 退出：`kvm_riscv_vcpu_guest_vector_save()` + `kvm_riscv_vcpu_host_vector_restore()`
2. **无 SIMD trap 处理路径**：
   - `arch/riscv/kvm/vcpu_exit.c` 仅处理通用 trap，并无 FP/Vector “首次访问”处理逻辑。

## 影响
- 在 **guest 很少使用 FP/Vector** 的场景中，riscv KVM 仍会在每次切换时保存/恢复，导致开销偏高。
- arm64 的 lazy 模式能显著降低开销，尤其在大量 vCPU 与频繁切换场景中收益明显。

## 可支持性分析（RISC-V 侧）
- RISC-V 通过 `FS/VS` 位可触发 FP/Vector 使用陷入（非法指令或异常），理论上可以借鉴 arm64 的“trap-first-use”策略。
- KVM 可在 HS-mode 中控制 guest 的 `VSSTATUS.VS/FS` 位，实现对首次使用的捕获，并完成上下文切换。

## 实现路径建议
1. **引入懒惰切换状态机**
   - 在 `struct kvm_vcpu_arch` 中维护“FP/Vector ownership”状态。
   - 在进入 guest 时仅标记“尚未加载”，不直接恢复寄存器。
2. **trap-first-use 处理**
   - 在 HS trap 路径中识别“FP/Vector 首次访问”，保存 host 状态并恢复 guest 状态。
3. **减少无意义保存**
   - 若 guest 从未触发 SIMD，则退出时无需保存 guest SIMD 状态。

## 关键难点
- 需要确保与内核其它组件（如 kernel vector/fpu 使用路径）协作正确。
- 需设计清晰的 ownership 状态迁移，避免 host/guest 状态污染。

## 参考文件
- `arch/arm64/kvm/fpsimd.c`
- `arch/arm64/kvm/hyp/include/hyp/switch.h`
- `arch/arm64/kvm/hyp/vhe/switch.c`
- `arch/riscv/kvm/vcpu.c`
- `arch/riscv/kvm/vcpu_fp.c`
- `arch/riscv/kvm/vcpu_vector.c`
