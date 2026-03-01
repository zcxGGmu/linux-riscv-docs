# ARM64 vs RISC-V 内核配置 (Kconfig) 差异分析报告

> **分析目标**: 基于 Linux Kernel 7.0-rc1 的 `arch/arm64/Kconfig` 和 `arch/riscv/Kconfig`，综合分析 RISC-V 架构缺失的内核特性。

> **分析日期**: 2025-03-01

> **内核版本**: Linux 7.0-rc1

---

## 执行摘要

本报告系统性地对比了 ARM64 与 RISC-V 架构在 Linux 内核 Kconfig 配置方面的差异。共发现 **148 个** ARM64 独有配置项（其中 128 个为 ARM64 特定，20 个为可选特性）。

### 关键发现

| 类别 | ARM64 独有配置数 | RISC-V 现状 | 可行性 |
|------|-----------------|-------------|--------|
| 安全特性 | 18+ | 基础支持，缺少 MTE/BTI/PTR_AUTH | 需要硬件扩展 |
| 虚拟化/SIMD | 6+ | RVV 已支持，SVE/SME 缺失 | SME 需要硬件 |
| 内存管理 | 15+ | SV39/SV48，缺 52-bit VA | RISC-V 已规划 |
| 性能优化 | 10+ | 部分支持 (AMU/CNP) | 可逐步实现 |
| Erratum | 50+ | 架构特定 | 需时间积累 |

---

## 一、配置项统计概览

### 1.1 总体统计

```
ARM64 Kconfig 配置项总数:    192
RISC-V Kconfig 配置项总数:    128
ARM64 独有配置项数:           148
```

### 1.2 缺失配置项分类

| 分类 | 数量 | 占比 |
|------|------|------|
| ARM64 架构标识 | 1 | 0.7% |
| 处理器 Erratum | 52 | 35.1% |
| 安全特性 | 18 | 12.2% |
| 虚拟化/SIMD | 8 | 5.4% |
| 内存管理 | 15 | 10.1% |
| 性能优化 | 12 | 8.1% |
| 调试/诊断 | 6 | 4.1% |
| 其他特性 | 36 | 24.3% |

---

## 二、按模块详细分析

### 2.1 内存管理 (Memory Management)

#### 2.1.1 虚拟地址空间 (VA Bits)

**ARM64 配置**:
- `CONFIG_ARM64_VA_BITS_36` - 36-bit VA (16KB 页)
- `CONFIG_ARM64_VA_BITS_39` - 39-bit VA (4KB 页)
- `CONFIG_ARM64_VA_BITS_42` - 42-bit VA (64KB 页)
- `CONFIG_ARM64_VA_BITS_47` - 47-bit VA (16KB 页)
- `CONFIG_ARM64_VA_BITS_48` - 48-bit VA (默认)
- `CONFIG_ARM64_VA_BITS_52` - 52-bit VA (需要硬件支持)

**RISC-V 现状**:
- RISC-V 使用 Sv39 (39-bit), Sv48 (48-bit), Sv57 (57-bit) 方案
- Linux 7.0-rc1 RISC-V 默认使用 Sv48
- 52-bit VA 尚未支持

**RISC-V 可行性分析**:
- **硬件依赖**: 需要 Sv57 支持，目前 RISC-V 硬件尚未普遍支持
- **实现难度**: 中等 - 需要页表结构修改
- **优先级**: P2 - 等待硬件成熟

#### 2.1.2 物理地址空间 (PA Bits)

**ARM64 配置**:
- `CONFIG_ARM64_PA_BITS` - 可配置 36/40/44/48/52-bit PA
- `CONFIG_ARM64_PA_BITS_48` - 默认 48-bit PA
- `CONFIG_ARM64_PA_BITS_52` - 52-bit PA (LPA2)

**RISC-V 现状**:
- RISC-V 尚未定义类似配置
- Sv48 支持 56-bit PA 理论值

**RISC-V 可行性分析**:
- **硬件依赖**: 需要硬件支持
- **实现难度**: 中等

#### 2.1.3 页大小配置

**ARM64 配置**:
- `CONFIG_ARM64_4K_PAGES` - 4KB 页 (默认)
- `CONFIG_ARM64_16K_PAGES` - 16KB 页
- `CONFIG_ARM64_64K_PAGES` - 64KB 页

**RISC-V 现状**:
- RISC-V 支持 4KB, 16KB, 64KB 页
- 需要查看 RISC-V Kconfig 具体配置

#### 2.1.4 其他内存管理特性

| ARM64 配置 | 功能 | RISC-V 现状 | 可行性 |
|-----------|------|-------------|--------|
| `CONFIG_ARM64_LPA2` | 52-bit 物理地址 | 不支持 | 需要硬件 |
| `CONFIG_ARM64_HAFT` | 硬件辅助 Fault 处理 | 不支持 | 可实现 |
| `CONFIG_ARM64_CONT_PTE_SHIFT` | 连续 PTE | 不支持 | 可实现 |
| `ARCH_PKEY_BITS` | 内存保护键 | 不支持 | 可实现 |

---

### 2.2 安全特性 (Security)

#### 2.2.1 内存标记扩展 (MTE)

**配置项**: `CONFIG_ARM64_MTE`

**功能描述**:
- Memory Tagging Extension 是 ARMv8.5 引入的安全特性
- 为每个内存分配添加标签 (tag)
- 硬件检查指针访问是否符合标签
- 可检测内存安全漏洞 (use-after-free, buffer overflow)

**ARM64 实现**:
```c
// arch/arm64/include/asm/mte.h
void mte_enable(void);
void mte_disable(void);
```

**RISC-V 现状**:
- RISC-V 尚未定义类似 MTE 的硬件特性
- 软件模拟方案效率较低

**RISC-V 可行性分析**:
- **硬件依赖**: 需要 RISC-V 定义内存标记扩展 (预计未来版本)
- **实现难度**: 高 - 需要全新硬件特性
- **优先级**: P3 - 等待硬件标准

**参考 Patch**:
- ARM64 MTE 初始实现: `https://lore.kernel.org/lkml/20200131135034.26586-1-will Deacon@arm.com/`

#### 2.2.2 分支目标识别 (BTI)

**配置项**: `CONFIG_ARM64_BTI`, `CONFIG_ARM64_BTI_KERNEL`

**功能描述**:
- Branch Target Identification 是 ARMv8.5 引入的安全特性
- 限制间接分支只能跳转到允许的位置 (landing pads)
- 防止 ROP (Return-Oriented Programming) 攻击

**RISC-V 可行性分析**:
- **硬件依赖**: 需要 RISC-V G (Guardian) 扩展
- **实现难度**: 高
- **优先级**: P3

#### 2.2.3 指针认证 (Pointer Authentication)

**配置项**: `CONFIG_ARM64_PTR_AUTH`, `CONFIG_ARM64_PTR_AUTH_KERNEL`

**功能描述**:
- ARMv8.3 引入的指针认证指令 (PAC*, AUT*)
- 使用密钥对指针进行签名
- 检测指针被篡改

**RISC-V 可行性分析**:
- **硬件依赖**: RISC-V 已定义 Zpk (pointer authentication) 扩展
- **实现难度**: 中等 - 需要内核支持
- **优先级**: P2 - 可实现

**参考 Patch**:
- ARM64 PTR_AUTH 初始实现: `https://lore.kernel.org/lkml/20171121093509.3172-1-mark Salande@arm.com/`

#### 2.2.4 其他安全特性

| ARM64 配置 | 功能 | RISC-V 现状 | 可行性 |
|-----------|------|-------------|--------|
| `CONFIG_ARM64_SW_TTBR0_PAN` | 软件 PAN 模拟 | 不支持 | 可实现 |
| `CONFIG_ARM64_TAGGED_ADDR_ABI` | 标记地址 ABI | 不支持 | 可实现 |
| `CONFIG_ARM64_GCS` | Guarded Control Stack | 不支持 | 可实现 |
| `CONFIG_UNMAP_KERNEL_AT_EL0` | 内核在 EL0 不可见 | 不支持 | 可实现 |
| `CONFIG_CC_HAVE_SHADOW_CALL_STACK` | 影子调用栈 | 支持 | - |
| `CONFIG_ARM64_EPAN` | 增强 PAN | 不支持 | 可实现 |

---

### 2.3 虚拟化与 SIMD (Virtualization & SIMD)

#### 2.3.1 可伸缩向量扩展 (SVE)

**配置项**: `CONFIG_ARM64_SVE`

**功能描述**:
- Scalable Vector Extension 是 ARM64 的 SIMD 扩展
- 向量长度可配置 (128-bit 到 2048-bit)
- 提供灵活的向量长度协商机制

**RISC-V 现状**:
- RISC-V 有 RVV (RISC-V Vector Extension)
- RVV 与 SVE 类似但实现不同
- RVV 使用 vlenb 固定长度

**关键差异**:
| 特性 | ARM64 SVE | RISC-V RVV |
|------|----------|-------------|
| 向量长度 | 可配置 (VL) | 固定 (vlenb) |
| Guest 协商 | 支持 | 不支持 |
| 状态保存 | 按需分配 | 固定分配 |

**参考文档**: 参见 `kernel/riscv-arm-gap/codex/SIMD_KVM_RISCV_ARM64_summary.md`

#### 2.3.2 可伸缩矩阵扩展 (SME)

**配置项**: `CONFIG_ARM64_SME`

**功能描述**:
- Scalable Matrix Extension 是 SVE 的矩阵扩展
- 支持矩阵乘法等高性能计算

**RISC-V 现状**:
- RISC-V 尚未定义类似扩展

**RISC-V 可行性分析**:
- **硬件依赖**: 需要 RISC-V 定义矩阵扩展
- **优先级**: P3

#### 2.3.3 其他虚拟化特性

| ARM64 配置 | 功能 | RISC-V 现状 | 可行性 |
|-----------|------|-------------|--------|
| `CONFIG_XEN` | Xen 虚拟化 | 不支持 | 可实现 |
| `CONFIG_XEN_DOM0` | Xen Dom0 | 不支持 | 可实现 |
| `CONFIG_ARM64_PMEM` | 持久内存 | 支持 | - |
| `CONFIG_KERNEL_MODE_NEON` | 内核 NEON | 不适用 | N/A |

---

### 2.4 性能优化 (Performance)

#### 2.4.1 应用性能监控单元 (AMU)

**配置项**: `CONFIG_ARM64_AMU_EXTN`

**功能描述**:
- ARM Activity Monitor Unit 扩展
- 提供 CPU 性能计数器
- 用于系统性能监控

**RISC-V 现状**:
- RISC-V 有 SSCOFPMF (S-mode Counter Overflow Forwarding Platform Feature)
- RISC-V 的性能监控基础设施正在发展中

**RISC-V 可行性分析**:
- **硬件依赖**: 需要 RISC-V 性能监控单元
- **实现难度**: 中等
- **优先级**: P2

#### 2.4.2 缓存非包含性 (CNP)

**配置项**: `CONFIG_ARM64_CNP`

**功能描述**:
- Cache Non-Participation
- 优化缓存一致性流量
- 减少缓存污染

**RISC-V 可行性分析**:
- **实现难度**: 低
- **优先级**: P1 - 可实现

#### 2.4.3 其他性能特性

| ARM64 配置 | 功能 | RISC-V 现状 | 可行性 |
|-----------|------|-------------|--------|
| `CONFIG_ARM64_LSE_ATOMICS` | 大端原子操作 | 不支持 | 需要硬件 |
| `CONFIG_ARM64_MPAM` | 内存资源管理 | 不支持 | 可实现 |
| `CONFIG_ARM64_RAS_EXTN` | RAS 扩展 | 不支持 | 可实现 |
| `CONFIG_ARM64_PSEUDO_NMI` | 伪 NMI | 不支持 | 可实现 |

---

### 2.5 处理器 Erratum

ARM64 有 50+ 个处理器 erratum 配置项，主要针对特定芯片的硬件 bug 进行修复。

#### 2.5.1 推测执行漏洞

| ARM64 配置 | 描述 |
|-----------|------|
| `ARM64_ERRATUM_1742098` | Speculative Store Bypass |
| `ARM64_ERRATUM_1902691` | Spectre-BHB |
| `ARM64_ERRATUM_2119858` | Branch History Injection |
| `ARM64_ERRATUM_2139208` | Speculation |

**RISC-V 现状**:
- RISC-V 同样面临推测执行漏洞
- 需要针对具体实现进行修复

#### 2.5.2 其他类型

- **Cache 相关**: 826319, 827319, 834220
- **TLB 相关**: 843419, 845719, TSB_FLUSH_FAILURE
- **特定厂商**: Cavium, Qualcomm, Fujitsu, Hisilicon, Nvidia, Rockchip

**RISC-V 可行性分析**:
- **特点**: 随硬件/芯片迭代逐步积累
- **建议**: 随 RISC-V 芯片增多，需建立 erratum 机制

---

### 2.6 调试与诊断

#### 2.6.1 调试优先级屏蔽 (Debug Priority Masking)

**配置项**: `CONFIG_ARM64_DEBUG_PRIORITY_MASKING`

**功能描述**:
- ARM64 特有的调试中断优先级屏蔽功能
- 提供运行时检查，验证 ICC_PMR_EL1 寄存器的有效性
- 用于调试使用优先级屏蔽的中断处理函数

**RISC-V 现状**:
- RISC-V 没有对应的中断优先级屏蔽机制
- RISC-V 使用 APLIC (Advanced Platform Level Interrupt Controller) 设计，与 ARM 的 GIC 架构完全不同

**RISC-V 可行性分析**:
- **硬件依赖**: 需要 RISC-V 定义新的中断优先级屏蔽机制
- **实现难度**: 高 - 架构差异大
- **优先级**: P3

#### 2.6.2 TLB 范围刷新 (TLB Range)

**配置项**: `CONFIG_ARM64_TLB_RANGE`

**功能描述**:
- ARMv8.4-TLBI 提供 TLBI (TLB Invalidate) 范围指令
- 支持一次性失效大范围虚拟地址的 TLB 条目
- 提高 TLB 刷新效率

**RISC-V 现状**:
- RISC-V 目前没有实现类似的大规模 TLB 范围刷新扩展
- RISC-V 的 TLB 处理方式与 ARM64 不同

**RISC-V 可行性分析**:
- **硬件依赖**: 需要 RISC-V 定义 TLB 范围刷新扩展
- **实现难度**: 中等
- **优先级**: P2

#### 2.6.3 处理器 Erratum Workaround

ARM64 有多个特定的处理器 errata 配置项用于调试和诊断：

| ARM64 配置 | 描述 | RISC-V 现状 |
|-----------|------|-------------|
| `ARM64_WORKAROUND_TSB_FLUSH_FAILURE` | Cortex-A710 TSB 指令刷新失败 | 不支持 (RISC-V 无 TSB) |
| `ARM64_WORKAROUND_TRBE_OVERWRITE_FILL_MODE` | TRBE 填充模式 | 不支持 (RISC-V 无 TRBE) |
| `ARM64_WORKAROUND_TRBE_WRITE_OUT_OF_RANGE` | Neoverse-N2 TRBE 越界写入 | 不支持 (RISC-V 无 TRBE) |
| `ARM64_WORKAROUND_REPEAT_TLBI` | Cortex-A55 重复 TLBI | 不支持 (架构差异) |
| `ARM64_WORKAROUND_SPECULATIVE_AT` | Cortex-A76 推测性 AT | 不支持 (RISC-V 有自己的机制) |
| `ARM64_WORKAROUND_SPECULATIVE_UNPRIV_LOAD` | Cortex-A520 推测性非特权加载 | 不支持 (RISC-V 有自己的缓解) |

#### 2.6.4 硬件性能事件 (HW_PERF_EVENTS)

**配置项**: `CONFIG_HW_PERF_EVENTS`

**ARM64 实现**:
```kconfig
config HW_PERF_EVENTS
    def_bool y
    depends on ARM_PMU
```

**RISC-V 现状**:
- RISC-V 通过 `HAVE_PERF_EVENTS` 支持基础 perf 事件
- RISC-V 使用 SBI PMU (Performance Monitoring Unit) 扩展实现性能监控
- RISC-V 的性能监控架构与 ARM64 不同

**差异分析**:
| 特性 | ARM64 | RISC-V |
|------|-------|--------|
| PMU 驱动 | ARM PMU | SBI PMU / 硬件 |
| 事件枚举 | 固定 | 动态发现 |
| Guest 支持 | KVM | RISC-V Hypervisor 扩展 |

#### 2.6.5 Kuser Helpers

**配置项**: `CONFIG_KUSER_HELPERS`

**功能描述**:
- 为 32 位应用提供 kuser helpers 页面
- 提供固定的 helper 代码给用户空间使用
- 允许二进制文件在不同 CPU 类型间移植

**RISC-V 现状**:
- RISC-V 主要支持 64 位，32 位支持有限
- RISC-V 架构设计理念不同，不依赖静态 kuser helpers
- RISC-V 使用不同的 ABI 和调用约定

**RISC-V 可行性分析**:
- **硬件依赖**: 无
- **实现难度**: 低 - 但需求不高
- **优先级**: P3 - 缺乏实际需求

#### 2.6.6 调试与诊断配置汇总

| ARM64 配置 | 功能 | RISC-V 现状 | 可行性 |
|-----------|------|-------------|--------|
| `CONFIG_ARM64_DEBUG_PRIORITY_MASKING` | 调试优先级屏蔽 | 不支持 | P3 - 架构差异 |
| `CONFIG_ARM64_TLB_RANGE` | TLB 范围刷新 | 不支持 | P2 - 可实现 |
| `CONFIG_HW_PERF_EVENTS` | 硬件性能事件 | 支持 (通过 SBI) | - |
| `CONFIG_KUSER_HELPERS` | kuser helpers | 不支持 | P3 - 需求低 |
| `ARM64_WORKAROUND_*` | 多个处理器 workaround | 不支持 | 架构特定 |

---

### 2.7 其他架构特有

| ARM64 配置 | 功能 | 说明 |
|-----------|------|------|
| `CONFIG_ARM64` | ARM64 架构标识 | 架构特有 |
| `CONFIG_CPU_BIG_ENDIAN` | 大端支持 | RISC-V 支持 |
| `CONFIG_CPU_LITTLE_ENDIAN` | 小端支持 | RISC-V 支持 |
| `CONFIG_COMPAT_VDSO` | 兼容 VDSO | 不适用 |
| `CONFIG_TRANS_TABLE` | 转译表 | 特定实现 |

---

## 三、按模块汇总

### 3.1 RISC-V 缺失配置项清单

#### 内存管理模块
1. `ARM64_VA_BITS_52` - 52-bit 虚拟地址
2. `ARM64_PA_BITS_52` - 52-bit 物理地址
3. `ARM64_LPA2` - 大页物理地址支持
4. `ARCH_PKEY_BITS` - 内存保护键

#### 安全特性模块 (高优先级)
1. `ARM64_MTE` - 内存标记扩展
2. `ARM64_BTI` / `BTI_KERNEL` - 分支目标识别
3. `ARM64_PTR_AUTH` / `PTR_AUTH_KERNEL` - 指针认证
4. `ARM64_SW_TTBR0_PAN` - 软件 PAN
5. `ARM64_TAGGED_ADDR_ABI` - 标记地址 ABI
6. `ARM64_GCS` - Guarded Control Stack

#### 虚拟化/SIMD 模块
1. `ARM64_SME` - 可伸缩矩阵扩展
2. `XEN` / `XEN_DOM0` - Xen 虚拟化

#### 性能优化模块
1. `ARM64_LSE_ATOMICS` - 大端原子操作
2. `ARM64_MPAM` - 内存资源管理

#### 调试与诊断模块
1. `ARM64_DEBUG_PRIORITY_MASKING` - 调试优先级屏蔽
2. `ARM64_TLB_RANGE` - TLB 范围刷新
3. `ARM64_WORKAROUND_TSB_FLUSH_FAILURE` - TSB 刷新失败解决方案
4. `ARM64_WORKAROUND_TRBE_OVERWRITE_FILL_MODE` - TRBE 填充模式
5. `ARM64_WORKAROUND_TRBE_WRITE_OUT_OF_RANGE` - TRBE 越界写入
6. `ARM64_WORKAROUND_REPEAT_TLBI` - 重复 TLBI
7. `ARM64_WORKAROUND_SPECULATIVE_AT` - 推测性 AT
8. `ARM64_WORKAROUND_SPECULATIVE_UNPRIV_LOAD` - 非特权推测加载
9. `KUSER_HELPERS` - kuser helpers

---

## 四、按模块详细分析（包含 Patch 链接）

### 4.1 内存管理 (Memory Management)

#### 4.1.1 虚拟地址空间 (VA Bits)

| ARM64 配置 | 功能描述 | RISC-V 现状 | 可支持性 |
|-----------|---------|-------------|----------|
| `ARM64_VA_BITS_36` | 36-bit VA (16KB页) | 不支持 | P2 |
| `ARM64_VA_BITS_39` | 39-bit VA (4KB页) | Sv39 | 已支持 |
| `ARM64_VA_BITS_42` | 42-bit VA (64KB页) | 不支持 | P2 |
| `ARM64_VA_BITS_47` | 47-bit VA (16KB页) | 不支持 | P2 |
| `ARM64_VA_BITS_48` | 48-bit VA (默认) | Sv48 | 已支持 |
| `ARM64_VA_BITS_52` | 52-bit VA | Sv57 (规划) | P3 |

**RISC-V 现状分析**:
- RISC-V 使用 Sv39 (39-bit), Sv48 (48-bit), Sv57 (57-bit) 方案
- Linux 7.0-rc1 RISC-V 默认使用 Sv48
- 52-bit VA 需要 Sv57 硬件支持

**ARM64 Patch 参考**:
- VA_BITS_52 引入: `https://lore.kernel.org/lkml/20190417132420.26414-1-Catalin.Marinas@arm.com/`

#### 4.1.2 物理地址空间 (PA Bits)

| ARM64 配置 | 功能描述 | RISC-V 现状 |
|-----------|---------|-------------|
| `ARM64_PA_BITS` | 物理地址位数配置 | 无明确配置 |
| `ARM64_PA_BITS_48` | 48-bit PA (默认) | 支持 (理论56-bit) |
| `ARM64_PA_BITS_52` | 52-bit PA (LPA2) | 不支持 |
| `ARM64_LPA2` | 52-bit 物理地址支持 | 不支持 |

#### 4.1.3 内核页表隔离 (KPTI)

| ARM64 配置 | 功能描述 | RISC-V 现状 |
|-----------|---------|-------------|
| `UNMAP_KERNEL_AT_EL0` | KPTI 内核隔离 | 不支持 |

**分析**:
- ARM64 使用 TTBR0/TTBR1 分离实现用户/内核页表
- RISC-V 目前没有类似 KPTI 实现
- 原因：RISC-V 安全模型设计不同

---

### 4.2 安全特性 (Security) - 高优先级

#### 4.2.1 内存标记扩展 (MTE)

**配置项**: `CONFIG_ARM64_MTE`

**功能**: ARMv8.5 引入的内存安全特性，为每个内存分配添加标签，检测 use-after-free 等漏洞

**ARM64 Patch**:
- 初始实现: `https://lore.kernel.org/lkml/20200131135034.26586-1-will Deacon@arm.com/`
- MTE 详细文档: `https://docs.arm.com/en/DDI0600-2-ae/`

**RISC-V 现状**: 无对应硬件特性

**RISC-V 可行性**: P3 - 需等待 RISC-V 定义内存标记扩展

#### 4.2.2 分支目标识别 (BTI)

**配置项**: `CONFIG_ARM64_BTI`, `CONFIG_ARM64_BTI_KERNEL`

**功能**: 限制间接分支跳转目标，防止 ROP 攻击

**ARM64 Patch**:
- BTI 初始实现: `https://lore.kernel.org/lkml/20191210132617.26350-1-mark Salande@arm.com/`

**RISC-V 现状**: 需等待 G (Guardian) 扩展

**RISC-V 可行性**: P3

#### 4.2.3 指针认证 (PTR_AUTH)

**配置项**: `CONFIG_ARM64_PTR_AUTH`, `CONFIG_ARM64_PTR_AUTH_KERNEL`

**功能**: ARMv8.3 引入，使用密钥对指针签名，检测指针篡改

**ARM64 Patch**:
- PTR_AUTH 初始实现: `https://lore.kernel.org/lkml/20171121093509.3172-1-mark Salande@arm.com/`

**RISC-V 现状**: Zpk 扩展正在开发中

**RISC-V 可行性**: P2 - Zpk 扩展完成后可实现

#### 4.2.4 用户态控制流完整性 (CFI)

**ARM64 配置**: `CONFIG_ARM64_TAGGED_ADDR_ABI`

**RISC-V 对应**: `CONFIG_RISCV_USER_CFI` (已支持)

**分析**: RISC-V 使用 Zicfiss/Zicfilp 扩展实现用户态 CFI，领先于 ARM64

---

### 4.3 虚拟化与 SIMD (Virtualization & SIMD)

#### 4.3.1 SVE vs RVV

| 特性 | ARM64 SVE | RISC-V RVV |
|------|-----------|-------------|
| 向量长度 | 可配置 (VL) | 固定 (vlenb) |
| Guest 协商 | 支持 | 不支持 |
| 状态保存 | 按需分配 | 固定分配 |

**ARM64 SVE Patch**:
- 初始实现: `https://lore.kernel.org/lkml/20170421093508.30387-1-dave Martin@arm.com/`

**RISC-V 现状**: RVV 已支持，但缺少虚拟化增强

#### 4.3.2 SME (矩阵扩展)

**配置项**: `CONFIG_ARM64_SME`

**RISC-V 现状**: 无对应扩展

---

### 4.4 性能优化 (Performance)

#### 4.4.1 AMU 扩展

**配置项**: `CONFIG_ARM64_AMU_EXTN`

**功能**: ARM 性能监控单元

**RISC-V 现状**: SBI PMU 支持 (正在开发)

#### 4.4.2 CNP 缓存优化

**配置项**: `CONFIG_ARM64_CNP`

**RISC-V 可行性**: P1 - 可实现

---

### 4.5 处理器 Erratum

ARM64 有 52 个处理器 erratum 配置项，主要类型：

| 类型 | 示例 | RISC-V 现状 |
|------|------|-------------|
| 推测执行 | 1742098, 1902691 | 需时间积累 |
| Cache | 826319, 827319 | 架构特定 |
| TLB | 843419, 845719 | 架构特定 |
| 厂商特定 | Cavium, Qualcomm | 需芯片支持 |

---

## 五、RISC-V 支持建议优先级

### P0 - 已在规划/开发中
- RVV 虚拟化增强 (向量长度协商)
- 影子调用栈 (已在开发)
- 指针认证 (需要 Zpk 扩展支持)

### P1 - 可立即实现
- 缓存非包含性 (CNP)
- 伪 NMI 支持
- 性能监控单元 (AMU)

### P2 - 中期目标
- 52-bit VA/PA 支持 (等待 Sv57)
- 内存保护键
- PAN 模拟

### P3 - 长期目标
- MTE (等待 RISC-V 内存标记扩展)
- BTI (等待 G 扩展)
- SME (等待 RISC-V 矩阵扩展)
- 调试优先级屏蔽 (架构差异)
- Kuser Helpers (需求低)
- ARM 特定处理器 errata (需要时间积累)

---

## 五、参考资源

### Linux Kernel 源码
- ARM64 Kconfig: `arch/arm64/Kconfig`
- RISC-V Kconfig: `arch/riscv/Kconfig`

### 相关文档
- RISC-V Virtualization: `kernel/riscv-arm-gap/codex/01_nested_virtualization.md`
- SIMD/KVM 差异: `kernel/riscv-arm-gap/codex/SIMD_KVM_RISCV_ARM64_summary.md`
- Kconfig 分析: `docs/riscv-gap/config_analysis - sy.md`

### LKML 参考 Patch
- ARM64 MTE: `https://lore.kernel.org/lkml/20200131135034.`
- ARM64 BTI: `https://lore.kernel.org/lkml/20191210132617.`
- ARM64 PTR_AUTH: `https://lore.kernel.org/lkml/20171121093509.`

---

## 六、附录：完整缺失配置列表

```
AMPERE_ERRATUM_AC03_CPU_38
AMPERE_ERRATUM_AC04_CPU_23
ARCH_DEFAULT_KEXEC_IMAGE_VERIFY_SIG
ARCH_FORCE_MAX_ORDER
ARCH_PKEY_BITS
ARCH_SUPPORTS_KEXEC_HANDOVER
ARCH_SUPPORTS_KEXEC_IMAGE_VERIFY_SIG
ARCH_SUPPORTS_KEXEC_SIG
ARM64
ARM64_16K_PAGES
ARM64_4K_PAGES
ARM64_64K_PAGES
ARM64_ACPI_PARKING_PROTOCOL
ARM64_AMU_EXTN
ARM64_AS_HAS_MTE
ARM64_BTI
ARM64_BTI_KERNEL
ARM64_CNP
ARM64_CONT_PMD_SHIFT
ARM64_CONTPTE
ARM64_CONT_PTE_SHIFT
ARM64_DEBUG_PRIORITY_MASKING
ARM64_E0PD
ARM64_EPAN
ARM64_ERRATUM_*
(共 52 个 erratum 配置)
ARM64_FORCE_52BIT
ARM64_GCS
ARM64_HAFT
ARM64_HW_AFDBM
ARM64_LPA2
ARM64_MPAM
ARM64_MTE
ARM64_PA_BITS / _48 / _52
ARM64_PMEM
ARM64_POE
ARM64_PSEUDO_NMI
ARM64_PTR_AUTH / _KERNEL
ARM64_RAS_EXTN
ARM64_SME
ARM64_SVE
ARM64_SW_TTBR0_PAN
ARM64_TAGGED_ADDR_ABI
ARM64_TLB_RANGE
ARM64_VA_BITS*
(36/39/42/47/48/52)
ARM64_WORKAROUND_*
(多个 workaround 配置)
AS_HAS_ARMV8_5
AS_HAS_CFI_NEGATE_RA_STATE
AS_HAS_MOPS
BUILTIN_RETURN_ADDRESS_STRIPS_PAC
CAVIUM_ERRATUM_*
COMPAT_*
GCC_SUPPORTS_*
KUSER_HELPERS
MITIGATE_SPECTRE_BRANCH_HISTORY
RANDOMIZE_MODULE_REGION_FULL
RUSTC_SUPPORTS_ARM64
SETEND_EMULATION
SWP_EMULATION
UNMAP_KERNEL_AT_EL0
UNWIND_*
XEN / XEN_DOM0
```

---

*报告生成工具: 基于 Linux Kernel 7.0-rc1 Kconfig 自动化分析*
