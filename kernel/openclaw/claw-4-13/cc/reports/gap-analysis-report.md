# RISC-V vs ARM/x86 Linux内核差距分析报告

生成时间: 2026-03-10

---

## 一、KVM支持文件差异

### 1.1 ARM64有但RISC-V缺失的核心文件

| 功能模块 | ARM64文件 | RISC-V状态 |
|---------|----------|-----------|
| 嵌套虚拟化 | arch/arm64/kvm/nested.c | **缺失** |
| 嵌套仿真 | arch/arm64/kvm/emulate-nested.c | **缺失** |
| GICv3嵌套中断 | arch/arm64/kvm/vgic/vgic-v3-nested.c | **缺失** |
| pKVM保护 | arch/arm64/kvm/pkvm.c | **缺失** |
| PV Time | arch/arm64/kvm/pvtime.c | **缺失** |
| Debug支持 | arch/arm64/kvm/debug.c | **缺失** |
| SVE支持 | arch/arm64/kvm/reset.c, fpsimd.c | RVV简化版 |

---

## 二、处理器特性支持差距

### 2.1 Vector/SIMD扩展

| 特性 | ARM64 | RISC-V | 差距 |
|------|-------|--------|------|
| 向量长度协商 | SVE支持可变VL | vlenb固定 | **高** |
| 子扩展控制 | 策略决定 | ZV*/Zfh默认暴露 | **中** |
| 懒惰切换 | EL2 trap first-use | 强制保存 | **中** |
| SME矩阵扩展 | 支持 | 无对应 | **高** |

### 2.2 调试机制

| 特性 | ARM64 | RISC-V |
|------|-------|--------|
| 硬件断点 | 完整实现 | 仅最小化 |
| 观察点 | 支持 | 不支持 |
| 单步调试 | 完整 | 未完整实现 |

---

## 三、虚拟化特性差距

### 3.1 嵌套虚拟化
- **ARM64**: 完整实现
- **RISC-V**: 完全缺失（返回SBI_ERR_NOT_SUPPORTED）

### 3.2 PV Time/Stolen Time
- **ARM64**: 完整实现
- **RISC-V**: 缺失

### 3.3 中断控制器
- **ARM64**: GICv3/v4完整
- **RISC-V**: APLIC/IMSIC基础

---

## 四、性能特性差距

### 4.1 VMID分配器
- **问题**: 全局vmid_next线性分配，回卷时全CPU IPI刷新
- **优化方向**: 引入bitmap + per-CPU active/reserved机制

### 4.2 IPI效率
- **ARM64**: 细粒度控制
- **RISC-V**: 全局广播

---

## 五、优先级建议

### P0 (关键)
1. VMID分配器优化
2. PV Time实现
3. IRQ Bypass

### P1 (重要)
1. 嵌套虚拟化规划
2. 硬件断点/观察点
3. VFIO集成

### P2 (优化)
1. pKVM保护VM
2. MTE/BTI支持（需硬件）

---

## 六、相关资源

- 现有分析文档: docs/riscv-gap/
- VMID优化方案: kernel/vmid/codex/
- KVM差距分析: kernel/riscv-arm-gap/codex/
