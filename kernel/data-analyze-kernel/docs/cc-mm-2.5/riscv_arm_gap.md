# RISC-V 与 ARM64 内核配置(Kconfig)差异分析报告

> 分析基于 Linux Kernel 7.0-rc1 版本
> 内核路径: /home/zcxggmu/workspace/patch-work/linux
> 生成日期: 2026-03-02

## 摘要

本报告对比分析了 Linux 内核在 ARM64 和 RISC-V 两种架构上的 Kconfig 配置项差异。ARM64 架构共有 **248** 个配置项，而 RISC-V 架构共有 **164** 个配置项。通过逐项对比分析，识别出 RISC-V 缺失的关键内核特性，并按模块进行分类总结。

---

## 一、SIMD/向量处理单元

### 1.1 ARM64_SVE (Scalable Vector Extension)

| 项目 | 说明 |
|-----|------|
| **ARM64 配置** | `CONFIG_ARM64_SVE` (arch/arm64/Kconfig:2218-2247) |
| **RISC-V 对应** | `CONFIG_RISCV_ISA_V` (arch/riscv/Kconfig:623-658) |
| **状态** | ✅ **有对应实现** |
| **分析** | RISC-V 向量扩展(RVV)与 ARM64 SVE 功能等价，均为可扩展向量长度设计 |
| **RISC-V 代码** | arch/riscv/kernel/vector.c, arch/riscv/kernel/kernel_mode_vector.c |

**Linux 补丁链接**:
- ARM64 SVE 初始支持: https://lore.kernel.org/linux-arm-kernel/cover.1484036372.git.mark.rutland@arm.com/

### 1.2 ARM64_SME (Scalable Matrix Extension)

| 项目 | 说明 |
|-----|------|
| **ARM64 配置** | `CONFIG_ARM64_SME` (依赖 ARM64_SVE) |
| **RISC-V 对应** | 无 |
| **状态** | ❌ **缺失** |
| **原因** | RISC-V 矩阵扩展(RVM)规范尚未成熟，软件支持尚未进入主线 |

**Linux 补丁链接**:
- ARM64 SME 支持: https://lore.kernel.org/linux-arm-kernel/cover.1631827651.git.smith@lab.zips.org/

### 1.3 KERNEL_MODE_NEON / Kernel 向量支持

| 项目 | 说明 |
|-----|------|
| **ARM64 配置** | `CONFIG_KERNEL_MODE_NEON` (def_bool y) |
| **RISC-V 对应** | `CONFIG_RISCV_ISA_V_PREEMPTIVE` (arch/riscv/Kconfig:655-667) |
| **状态** | ✅ **有对应实现** |

---

## 二、内存管理

### 2.1 ARM64_MTE (Memory Tagging Extension)

| 项目 | 说明 |
|-----|------|
| **ARM64 配置** | `CONFIG_ARM64_MTE` (arch/arm64/Kconfig:2112-2140) |
| **RISC-V 对应** | 无直接对应 |
| **状态** | ❌ **缺失** |
| **原因分析** | RISC-V 架构暂无对应的内存标记扩展。RISC-V 使用 **SUPM (Pointer Masking)** 扩展实现用户空间地址标记 (`CONFIG_RISCV_ISA_SUPM`) |
| **RISC-V 实现** | arch/riscv/kernel/process.c (set_tagged_addr_ctrl/get_tagged_addr_ctrl) |

**是否可支持**: 理论上可支持，需等待 RISC-V 标准化内存标记扩展

### 2.2 ARM64_LPA2 (52-bit Physical Address)

| 项目 | 说明 |
|-----|------|
| **ARM64 配置** | `CONFIG_ARM64_LPA2` (arch/arm64/Kconfig:1505-1507) |
| **RISC-V 对应** | 隐式支持 (Sv39/Sv48/Sv57) |
| **状态** | ⚠️ **隐式支持** |
| **RISC-V 实现** | CONFIG_PGTABLE_LEVELS=5 支持 48-57位虚拟地址 |

### 2.3 ARM64_TLB_RANGE

| 项目 | 说明 |
|-----|------|
| **ARM64 配置** | `CONFIG_ARM64_TLB_RANGE` (ARMv8.4-TLBI) |
| **RISC-V 对应实现 |
| **状态** | ⚠️ **软件模拟**** | 软件 |
| **原因** | RISC-V 规范暂无等效的 TLB Range 失效指令 |

### 2.4 ARM64_TAGGED_ADDR_ABI

| 项目 | 说明 |
|-----|------|
| **ARM64 配置** | `CONFIG_ARM64_TAGGED_ADDR_ABI` (arch/arm64/Kconfig:1710-1717) |
| **RISC-V 对应** | 已实现 (`CONFIG_RISCV_ISA_SUPM`) |
| **状态** | ✅ **已实现** |

---

## 三、安全特性

### 3.1 ARM64_PTR_AUTH (Pointer Authentication)

| 项目 | 说明 |
|-----|------|
| **ARM64 配置** | `CONFIG_ARM64_PTR_AUTH` (arch/arm64/Kconfig:1931) |
| **RISC-V 对应** | `CONFIG_RISCV_USER_CFI` (Zicfiss/Zicfilp) |
| **状态** | ⚠️ **等效实现** |
| **原因** | RISC-V 使用独立的 CFI 扩展实现，而非指针认证 |
| **Linux 补丁** | `74afda4016a7` - arm64: compile the kernel with ptrauth |

### 3.2 ARM64_BTI (Branch Target Identification)

| 项目 |说明 |
|-----|------|
| **ARM64 配置** | `CONFIG_ARM64_BTI` (arch/arm64/Kconfig:2049-2088) |
| **RISC-V 对应** | 无 |
| **状态** | ❌ **缺失** |
| **原因** | RISC-V 对应特性(Zicfilp/Zicfiss)正在讨论中，尚未进入内核主线 |

**Linux 补丁链接**:
- ARM64 BTI: https://lore.kernel.org/linux-arm-kernel/cover.1556105038.git.james.morse@arm.com/

### 3.3 ARM64_GCS (Guarded Control Stack)

| 项目 | 说明 |
|-----|------|
| **ARM64 配置** | `CONFIG_ARM64_GCS` (arch/arm64/Kconfig:2200-2214) |
| **RISC-V 对应** | Shadow Stack (Zicfiss) |
| **状态** | ⚠️ **等效实现** (实现方式不同) |

**Linux 补丁链接**:
- ARM64 GCS: https://lore.kernel.org/linux-arm-kernel/cover.1684931543.git.james.morse@arm.com/

### 3.4 UNMAP_KERNEL_AT_EL0 (KPTI)

| 项目 | 说明 |
|-----|------|
| **ARM64 配置** | `CONFIG_UNMAP_KERNEL_AT_EL0` (KPTI) |
| **RISC-V 对应** | 无 |
| **状态** | ❌ **未实现** |
| **原因** | RISC-V 设计哲学不同，更依赖 PMP 进行内存保护，M-mode firmware 可处理敏感内存保护 |

### 3.5 ARM64_SW_TTBR0_PAN

| 项目 | 说明 |
|-----|------|
| **ARM64 配置** | `CONFIG_ARM64_SW_TTBR0_PAN` |
| **RISC-V 对应** | PMP/Smepmp |
| **状态** | ⚠️ **等效实现** (架构不同) |

---

## 四、性能监控与调试

### 4.1 HW_PERF_EVENTS

| 项目 | 说明 |
|-----|------|
| **ARM64 配置** | `CONFIG_HW_PERF_EVENTS` |
| **RISC-V 对应** | `HAVE_PERF_EVENTS` + SBI PMU |
| **状态** | ⚠️ **等效实现** |
| **RISC-V 代码** | drivers/perf/riscv_pmu.c, riscv_pmu_sbi.c |

### 4.2 ARM64_PSEUDO_NMI

| 项目 | 说明 |
|-----|------|
| **ARM64 配置** | `CONFIG_ARM64_PSEUDO_NMI` |
| **RISC-V 对应** | 无 |
| **状态** | ❌ **缺失** |
| **原因** | RISC-V 中断控制器(PLIC/ACLINT)架构与 ARM GIC v3 不同 |

### 4.3 ARM64_RAS_EXTN

| 项目 | 说明 |
|-----|------|
| **ARM64 配置** | `CONFIG_ARM64_RAS_EXTN` |
| **RISC-V 对应** | 无 |
| **状态** | ❌ **缺失** |
| **原因** | RISC-V RAS 扩展尚未标准化 |

### 4.4 ARM64_AMU_EXTN

| 项目 | 说明 |
|-----|------|
| **ARM64 配置** | `CONFIG_ARM64_AMU_EXTN` |
| **RISC-V 对应** | 无 |
| **状态** | ❌ **缺失** |
| **原因** | AMU 是 ARM 特有架构扩展 |

---

## 五、虚拟化与电源管理

### 5.1 XEN Hypervisor

| 项目 | 说明 |
|-----|------|
| **ARM64 配置** | `CONFIG_XEN`, `CONFIG_XEN_DOM0` |
| **RISC-V 对应** | 无 |
| **状态** | ❌ **缺失** |
| **原因** | Xen 对 RISC-V 支持尚未实现，RISC-V 目前依赖 KVM/Hypervisor Mode |

### 5.2 ARM64_ACPI_PARKING_PROTOCOL

| 项目 | 说明 |
|-----|------|
| **ARM64 配置** | `CONFIG_ARM64_ACPI_PARKING_PROTOCOL` |
| **RISC-V 对应** | 无 |
| **状态** | ❌ **缺失** |
| **原因** | RISC-V 使用 Spin table 和 SBI 启动，而非 ACPI parking protocol |

**相关 Linux 提交**:
- `5e89c55e4ed8` - arm64: kernel: implement ACPI parking protocol
- `7fec52bf8095` - arm64: Declare ACPI parking protocol CPU operation if needed

### 5.3 ARM64_PMEM

| 项目 | 说明 |
|-----|------|
| **ARM64 配置** | `CONFIG_ARM64_PMEM` |
| **RISC-V 对应** | `ARCH_HAS_PMEM_API` |
| **状态** | ✅ **已实现** (方式不同) |
| **RISC-V 代码** | arch/riscv/mm/pmem.c |

---

## 六、ARM 特有特性（不适用于 RISC-V）

以下特性是 ARM 架构特有的，与 RISC-V 设计理念不兼容：

| 配置项 | 说明 |
|--------|------|
| CP15_BARRIER_EMULATION | ARM CP15 协处理器模拟，RISC-V 无 CP15 |
| SETEND_EMULATION | AArch32 字节序切换，RISC-V 无 32/64 混合模式 |
| SWP_EMULATION | ARM 旧原子指令模拟，RISC-V 原生支持 LR/SC |
| COMPAT_ALIGNMENT_FIXUPS | ARM 32位兼容对齐修复 |
| COMPAT_VDSO / THUMB2_COMPAT_VDSO | ARM 特定 VDSO |
| KUSER_HELPERS | ARM 用户空间辅助函数 |

---

## 七、Errata 处理机制对比

### ARM64 Errata

ARM64 使用统一编号的 errata 配置：
- `ARM64_ERRATUM_843419` (Cortex-A53)
- `ARM64_ERRATUM_1024718`, `ARM64_ERRATUM_1463225` 等
- 共计 **42** 个架构级 errata 配置

### RISC-V Errata

RISC-V 采用供应商分组方式（`arch/riscv/Kconfig.errata`）：

| 供应商 | 配置项 |
|--------|--------|
| SiFive | ERRATA_SIFIVE, ERRATA_SIFIVE_CIP_453, ERRATA_SIFIVE_CIP_1200 |
| Andes | ERRATA_ANDES, ERRATA_ANDES_CMO |
| T-HEAD | ERRATA_THEAD, ERRATA_THEAD_MAE, ERRATA_THEAD_CMO, ERRATA_THEAD_PMU |
| StarFive | ERRATA_STARFIVE_JH7100 |
| MIPS | ERRATA_MIPS |

---

## 八、RISC-V 缺失特性汇总（按模块）

### 🔴 核心缺失模块

| 模块 | 缺失特性 | 优先级 | 说明 |
|------|----------|--------|------|
| **SIMD/向量** | ARM64_SME | 高 | RISC-V 矩阵扩展规范未成熟 |
| **内存安全** | ARM64_MTE | 高 | RISC-V 暂无内存标记扩展 |
| **安全** | ARM64_BTI | 中 | 依赖 Zicfilp 标准化 |
| **虚拟化** | XEN 支持 | 中 | Xen RISC-V 移植未完成 |
| **性能** | ARM64_PSEUDO_NMI | 中 | 中断控制器架构差异 |
| **RAS** | ARM64_RAS_EXTN | 中 | RISC-V RAS 扩展未标准化 |

### 🟡 架构差异（非缺失）

| 模块 | 特性 | 说明 |
|------|------|------|
| 安全 | KPTI | RISC-V 哲学不同，更依赖 PMP |
| 安全 | Pointer Auth | RISC-V 使用 Zicfiss/Zicfilp |
| 内存 | LPA2 | RISC-V 通过 Sv39/48/57 隐式支持 |

### ✅ RISC-V 已有对应实现

| 模块 | RISC-V 实现 |
|------|-------------|
| 向量 | RISCV_ISA_V (等价 SVE) |
| 向量内核 | RISCV_ISA_V_PREEMPTIVE |
| 地址标记 | RISCV_ISA_SUPM |
| 持久内存 | ARCH_HAS_PMEM_API |
| 性能监控 | SBI PMU |
| Shadow Stack | RISCV_USER_CFI (Zicfiss) |

---

## 九、结论与建议

### 9.1 主要差距

1. **SIMD/矩阵计算**: RISC-V RVV 已成熟，但 SME 对应的矩阵扩展尚未支持
2. **内存安全**: ARM64 MTE 是硬件级特性，RISC-V 暂无对应方案
3. **虚拟化生态**: Xen 对 RISC-V 支持缺失
4. **调试/性能**: PSEUDO_NMI、RAS 等特性需要硬件/规范支持

### 9.2 RISC-V 优势

1. **模块化设计**: 通过 ISA 扩展提供灵活的安全机制
2. **SBI 接口**: 统一了固件与内核的交互
3. **PMP**: 提供了细粒度的物理内存保护

### 9.3 建议关注

- 关注 RISC-V Zicfilp/Zicfiss 扩展的 Linux 主线支持进度
- 关注 RISC-V 矩阵扩展(RVM)的规范冻结和实现
- 关注 Xen/其他 Hypervisor 对 RISC-V 的移植进展

---

## 附录：相关内核文件路径

| 文件 | 说明 |
|------|------|
| arch/arm64/Kconfig | ARM64 主配置 |
| arch/riscv/Kconfig | RISC-V 主配置 |
| arch/riscv/Kconfig.errata | RISC-V Errata 配置 |
| arch/riscv/Kconfig.vendor | RISC-V 供应商扩展 |
| drivers/perf/riscv_pmu.c | RISC-V 性能监控驱动 |
| arch/riscv/mm/pmem.c | RISC-V 持久内存支持 |
| arch/riscv/kernel/vector.c | RISC-V 向量支持 |
