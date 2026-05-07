# SIMD 差异 3：按需/按 VL 分配状态（arm64 SVE） vs 固定全量分配（riscv RVV）

## 差异概述
- **arm64 KVM**：SVE 状态 **按需分配**，并按 guest 选择的最大 VL 进行精确分配。
- **riscv KVM**：在 vCPU 创建时 **固定分配** host/guest 的向量上下文，大小为宿主 `riscv_v_vsize`，与 guest 是否启用 V 无关。

## arm64 现状（代码证据）
1. **延迟分配**：
   - `arch/arm64/kvm/reset.c`：
     - `kvm_vcpu_enable_sve()` 仅设置配置，延迟分配。
     - `kvm_vcpu_finalize_sve()` 在 finalize 阶段按 VL 大小 `kzalloc()`。

```c
// arch/arm64/kvm/reset.c
static int kvm_vcpu_finalize_sve(struct kvm_vcpu *vcpu)
{
    size_t reg_sz = vcpu_sve_state_size(vcpu);
    void *buf = kzalloc(reg_sz, GFP_KERNEL_ACCOUNT);
    ...
}
```

2. **VL 驱动的状态大小**：
   - `vcpu_sve_state_size(vcpu)` 根据选择的 VL 计算实际分配大小。

## riscv 现状（缺失与证据）
1. **固定全量分配**：
   - `arch/riscv/kvm/vcpu_vector.c` 中 `kvm_riscv_vcpu_alloc_vector_context()`：
     - 对 guest 和 host 都使用 `kzalloc(riscv_v_vsize)`。
     - 即便 guest 未启用 V，仍分配完整向量状态。

```c
// arch/riscv/kvm/vcpu_vector.c
vcpu->arch.guest_context.vector.datap = kzalloc(riscv_v_vsize, GFP_KERNEL);
vcpu->arch.host_context.vector.datap  = kzalloc(riscv_v_vsize, GFP_KERNEL);
```

## 影响
- VLEN 较大时，每个 vCPU 的内存开销显著，且 host/guest 双份分配。
- 对不使用 RVV 的 guest 来说是无谓开销。

## 可支持性分析（RISC-V 侧）
- RVV 状态布局由 VLEN 决定，理论上可以 **按需分配/按 guest 配置分配**。
- 即便暂不实现“虚拟 VLEN”，也可在 guest 不启用 V 时不分配向量上下文。

## 实现路径建议
1. **延迟分配**
   - 将 `kvm_riscv_vcpu_alloc_vector_context()` 改为按需调用，或在 enable V 扩展时分配。
2. **按配置分配**
   - 如果引入 `guest_vlenb`（见 SIMD 差异 1），则按 `guest_vlenb` 分配。
3. **释放策略**
   - 当 guest 禁用 V（或 vCPU finalize 之后确定不使用）时释放向量上下文。

## 关键难点
- 与 vCPU 生命周期/ISA 扩展 enable/disable 的状态同步。
- 在 vCPU 已运行后动态变更 V 可能需要严格限制或拒绝。

## 参考文件
- `arch/arm64/kvm/reset.c`
- `arch/riscv/kvm/vcpu_vector.c`
- `arch/riscv/kvm/vcpu.c`
