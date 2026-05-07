# SIMD 深入 3：向量上下文在迁移/快照中的 ABI 兼容策略

## 结论摘要
- **现状**：RISC-V KVM 的向量寄存器 ABI 依赖宿主 VLEN（`vlenb`），且 **vlenb 为只读**。迁移/快照必须保证源/目标主机 VLEN 一致，否则 `KVM_SET_ONE_REG` 将因尺寸不匹配失败。
- **问题**：缺少类似 arm64 SVE 的“可变长度向量 ABI”，也缺少显式的 KVM capability 用于协商 VLEN。

## 关键证据（代码层）
1. **vlenb 只读、固定为宿主 VLEN**
```c
// arch/riscv/kvm/vcpu_vector.c
cntx->vector.vlenb = riscv_v_vsize / 32;
...
if (reg_num == KVM_REG_RISCV_VECTOR_CSR_REG(vlenb)) {
    if (reg_val != cntx->vector.vlenb)
        return -EINVAL;
}
```

2. **向量寄存器大小依赖 vlenb**
```c
// arch/riscv/kvm/vcpu_onereg.c
size = __builtin_ctzl(cntx->vector.vlenb);
size <<= KVM_REG_SIZE_SHIFT;
reg = KVM_REG_RISCV | KVM_REG_RISCV_VECTOR | size | KVM_REG_RISCV_VECTOR_REG(i);
```
这意味着用户态序列化/反序列化必须与 vlenb 完全一致。

3. **KVM ABI 仅暴露固定格式寄存器**
- `arch/riscv/include/uapi/asm/kvm.h` 中 `KVM_REG_RISCV_VECTOR` 只定义了 vstart/vl/vtype/vcsr/vlenb + 32 vreg。
- 没有“多切片”或“可变长度”机制。

## 影响
- **迁移限制**：VLEN 不一致的主机间迁移几乎不可行（除非用户态拒绝迁移）。
- **快照格式不稳定**：快照若不显式记录 vlenb，则恢复时无法验证一致性。

## 建议的兼容策略
### 策略 A：严格同构（现状可用）
- 在迁移/快照时读取 `vlenb`（KVM_REG_RISCV_VECTOR_CSR_REG(vlenb)）。
- 若目标主机 vlenb != 源主机 vlenb，则拒绝迁移。

### 策略 B：引入“虚拟 VLEN”ABI
- 新增 KVM capability / VM 属性，用于设置 `guest_vlenb <= host_vlenb`。
- 依据 `guest_vlenb` 分配/保存向量寄存器，并限制 guest 使用更大 VLEN。
- 类似 arm64 SVE 的“向量长度协商”。

### 策略 C：用户态自定义快照格式
- 在快照中记录 vlenb 与向量寄存器 blob。
- 恢复时先校验 vlenb，一致再恢复。

## 关键难点
- **虚拟 VLEN 需要指令级限制**：仅用寄存器过滤可能不足，可能需要在 vsetvl/vsetvli 处进行约束或陷入仿真。
- **性能与复杂度**：可变 VLEN 会带来更多检查与状态管理开销。

## 参考文件
- `arch/riscv/kvm/vcpu_vector.c`
- `arch/riscv/kvm/vcpu_onereg.c`
- `arch/riscv/include/uapi/asm/kvm.h`
