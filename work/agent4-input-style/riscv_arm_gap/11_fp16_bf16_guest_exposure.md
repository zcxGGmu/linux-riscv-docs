# SIMD 深入 2：FP16/BF16（Zfh/Zfbfmin）在 guest 侧的可控暴露与寄存器行为

## 结论摘要
- **现状**：RISC-V KVM 将 Zfh / Zfbfmin 等扩展纳入 ISA 掩码映射，但 **与其它多数扩展一样“不可禁用”**。只要宿主支持，默认就暴露给 guest。
- **寄存器行为**：Zfh/Zfbfmin 不引入新的寄存器文件，复用现有 F 寄存器与 FCSR；KVM 的 FP 保存/恢复逻辑只区分 F/D，未显式区分 FP16/BF16。

## 关键证据（代码层）
1. **KVM ISA 映射包含 Zfh/Zfbfmin**
```c
// arch/riscv/kvm/vcpu_onereg.c
KVM_ISA_EXT_ARR(ZFBFMIN),
KVM_ISA_EXT_ARR(ZFH),
KVM_ISA_EXT_ARR(ZFHMIN),
```

2. **Zfh/Zfbfmin 不可禁用**
```c
// arch/riscv/kvm/vcpu_onereg.c
case KVM_RISCV_ISA_EXT_ZFBFMIN:
case KVM_RISCV_ISA_EXT_ZFH:
case KVM_RISCV_ISA_EXT_ZFHMIN:
    return false;
```

3. **宿主侧依赖校验**
```c
// arch/riscv/kernel/cpufeature.c
__RISCV_ISA_EXT_DATA_VALIDATE(zfbfmin, RISCV_ISA_EXT_ZFBFMIN, riscv_ext_f_depends),
__RISCV_ISA_EXT_DATA_VALIDATE(zfh, RISCV_ISA_EXT_ZFH, riscv_ext_f_depends),
__RISCV_ISA_EXT_DATA_VALIDATE(zfhmin, RISCV_ISA_EXT_ZFHMIN, riscv_ext_f_depends),
```
`riscv_ext_f_depends()` 要求 F 扩展存在。

4. **KVM FP 上下文仅区分 F/D**
```c
// arch/riscv/kvm/vcpu_fp.c
if (riscv_isa_extension_available(isa, d))
    __kvm_riscv_fp_d_save(cntx);
else if (riscv_isa_extension_available(isa, f))
    __kvm_riscv_fp_f_save(cntx);
```

## 当前 guest 暴露策略的行为总结
- Zfh/Zfbfmin **随宿主 F 扩展启用而默认暴露**。
- guest 无法通过 KVM ISA mask 接口关闭 Zfh/Zfbfmin（被禁止 disable）。
- 从寄存器角度看，FP16/BF16 **不需要额外寄存器保存**，仍由 F/D 保存逻辑覆盖。

## 影响
- **兼容性**：在缺少 Zfh/Zfbfmin 的宿主间迁移时，无法靠 guest 侧屏蔽做降级。
- **控制性不足**：无法按 VM 禁用 FP16/BF16，影响确定性与安全策略（例如需要严格控制指令集暴露）。

## 可改进方向（建议）
1. **允许禁用 Zfh/Zfbfmin**
   - 修改 `kvm_riscv_vcpu_isa_disable_allowed()`，对 Zfh/Zfbfmin 放开禁用。
2. **能力协商接口**
   - 增加 KVM capability / VM 属性，明确是否允许暴露 FP16/BF16。
3. **迁移一致性检查**
   - 用户态在迁移时读取 guest ISA mask，强制源/目标主机 Zfh/Zfbfmin 兼容。

## 参考文件
- `arch/riscv/kvm/vcpu_onereg.c`
- `arch/riscv/kernel/cpufeature.c`
- `arch/riscv/kvm/vcpu_fp.c`
