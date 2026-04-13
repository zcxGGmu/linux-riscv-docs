# ARM64 vs RISC-V Kconfig 详细差异分析

## 配置项详情

### 内存管理模块

| ARM64 配置 | 功能描述 | RISC-V 现状 | 可支持性 | 优先级 |
|-----------|---------|-------------|----------|--------|
| ARM64_VA_BITS_36 | 36-bit 虚拟地址 (16KB页) | 不支持 | P2 | 中 |
| ARM64_VA_BITS_39 | 39-bit 虚拟地址 | Sv39 | ✅ 已支持 | - |
| ARM64_VA_BITS_42 | 42-bit 虚拟地址 (64KB页) | 不支持 | P2 | 中 |
| ARM64_VA_BITS_47 | 47-bit 虚拟地址 | 不支持 | P2 | 中 |
| ARM64_VA_BITS_48 | 48-bit 虚拟地址 (默认) | Sv48 | ✅ 已支持 | - |
| ARM64_VA_BITS_52 | 52-bit 虚拟地址 | Sv57 | P3 | 低 |
| ARM64_PA_BITS_48 | 48-bit 物理地址 | 支持 | ✅ 已支持 | - |
| ARM64_PA_BITS_52 | 52-bit 物理地址 (LPA2) | 不支持 | P3 | 低 |
| ARM64_LPA2 | 52-bit 物理地址支持 | 不支持 | P3 | 低 |
| ARM64_4K_PAGES | 4KB 页支持 | ✅ 支持 | ✅ 已支持 | - |
| ARM64_16K_PAGES | 16KB 页支持 | 不支持 | P2 | 中 |
| ARM64_64K_PAGES | 64KB 页支持 | 不支持 | P2 | 中 |
| UNMAP_KERNEL_AT_EL0 | KPTI 内核隔离 | 不支持 | P3 | 中 |
| KUSER_HELPERS | kuser helpers 页面 | 不支持 | P3 | 低 |
| ARM64_PSEUDO_NMI | 伪 NMI 支持 | 不支持 | P2 | 中 |
| ARM64_HW_AFDBM | 硬件脏页管理 | 支持 | ✅ 已支持 | - |
| ARCH_FORCE_MAX_ORDER | 最大阶配置 | 支持 | ✅ 已支持 | - |

### 安全特性模块

| ARM64 配置 | 功能描述 | RISC-V 现状 | 可支持性 | 优先级 |
|-----------|---------|-------------|----------|--------|
| ARM64_MTE | 内存标记扩展 | 不支持 | P3 | 高 |
| ARM64_BTI | 分支目标识别 | 不支持 | P3 | 高 |
| ARM64_BTI_KERNEL | 内核 BTI | 不支持 | P3 | 高 |
| ARM64_PTR_AUTH | 指针认证 (用户态) | Zpk (规划) | P2 | 高 |
| ARM64_PTR_AUTH_KERNEL | 内核指针认证 | Zpk (规划) | P2 | 高 |
| ARM64_SW_TTBR0_PAN | 软件 PAN | 不支持 | P2 | 中 |
| ARM64_TAGGED_ADDR_ABI | 标记地址 ABI | 不支持 | P2 | 中 |
| ARM64_GCS | Guarded Control Stack | 不支持 | P3 | 中 |
| ARM64_EPAN | 增强 PAN | 不支持 | P3 | 中 |
| CC_HAVE_SHADOW_CALL_STACK | 影子调用栈 | ✅ 支持 | ✅ 已支持 | - |
| ARM64_CONTPTE | 连续页表 | 支持 | ✅ 已支持 | - |

### SIMD/向量模块

| ARM64 配置 | 功能描述 | RISC-V 现状 | 可支持性 | 优先级 |
|-----------|---------|-------------|----------|--------|
| ARM64_SVE | 可伸缩向量扩展 | 不适用 | N/A | - |
| ARM64_SME | 可伸缩矩阵扩展 | 不支持 | P3 | 高 |
| KERNEL_MODE_NEON | 内核 NEON | 不适用 | N/A | - |
| ARM64_PMEM | 持久内存 | 支持 | ✅ 已支持 | - |

**RISC-V 向量对比**:
- RISCV_ISA_V: 向量扩展 ✅ 已支持
- RVV 虚拟化: 缺少 vlenb 协商

### 虚拟化模块

| ARM64 配置 | 功能描述 | RISC-V 现状 | 可支持性 | 优先级 |
|-----------|---------|-------------|----------|--------|
| XEN | Xen 虚拟化 | 不支持 | P2 | 中 |
| XEN_DOM0 | Xen Dom0 | 不支持 | P2 | 中 |
| ARM64_ACPI_PARKING_PROTOCOL | ACPI 停车协议 | 不支持 | P3 | 低 |

### 性能优化模块

| ARM64 配置 | 功能描述 | RISC-V 现状 | 可支持性 | 优先级 |
|-----------|---------|-------------|----------|--------|
| ARM64_AMU_EXTN | 性能监控单元 | SBI PMU | P1 | 高 |
| ARM64_CNP | 缓存非包含性 | 不支持 | P1 | 中 |
| ARM64_LSE_ATOMICS | 大端原子操作 | 不支持 | P2 | 中 |
| ARM64_MPAM | 内存资源管理 | 不支持 | P3 | 低 |
| ARM64_RAS_EXTN | RAS 扩展 | 不支持 | P2 | 中 |
| ARM64_E0PD | E0PD | 不支持 | P3 | 低 |

### 调试诊断模块

| ARM64 配置 | 功能描述 | RISC-V 现状 | 可支持性 | 优先级 |
|-----------|---------|-------------|----------|--------|
| ARM64_DEBUG_PRIORITY_MASKING | 调试优先级屏蔽 | 不支持 | P3 | 低 |
| ARM64_TLB_RANGE | TLB 范围刷新 | 不支持 | P2 | 中 |
| HW_PERF_EVENTS | 硬件性能事件 | ✅ 支持 | ✅ 已支持 | - |

### 处理器 Erratum (52个)

| 类型 | 数量 | RISC-V 现状 |
|------|------|-------------|
| 推测执行漏洞 | 10+ | 需时间积累 |
| Cache 相关 | 8+ | 架构特定 |
| TLB 相关 | 5+ | 架构特定 |
| 厂商特定 | 30+ | 需芯片支持 |

---

## Patch 链接索引

### 安全特性
1. ARM64_MTE: https://lore.kernel.org/lkml/20200131135034.26586-1-willdeacon@kernel.org/
2. ARM64_BTI: https://lore.kernel.org/lkml/20191210132617.26350-1-mark.salanders@arm.com/
3. ARM64_PTR_AUTH: https://lore.kernel.org/lkml/20171121093509.3172-1-mark.salanders@arm.com/

### SIMD/向量
4. ARM64_SVE: https://lore.kernel.org/lkml/20170421093508.30387-1-dave.martina@arm.com/

### 虚拟化
5. ARM64_SVE KVM: https://lore.kernel.org/lkml/20181002093724.17530-1-dave.martina@arm.com/

### 内存管理
6. ARM64 VA_BITS_52: https://lore.kernel.org/lkml/20190417132420.26414-1-catalin.marinas@arm.com/
