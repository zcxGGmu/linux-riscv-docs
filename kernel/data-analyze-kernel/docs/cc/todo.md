# ARM64 vs RISC-V Kconfig 配置差异分析计划

> **目标**: 基于 Linux Kernel 7.0-rc1 的 arch/arm64/Kconfig 和 arch/riscv/Kconfig，综合分析 RISC-V 架构缺失的内核特性

**分析范围**:
- Kernel: Linux 7.0-rc1
- ARM64 Kconfig: 2479 行
- RISC-V Kconfig: 1402 行

---

## 阶段一：环境准备与数据提取 (Task 1-2)

### Task 1: 创建分析输出目录

**Step 1: 创建目录结构**
```bash
mkdir -p /home/zcxggmu/workspace/patch-work/linux-riscv-docs/kernel/data-analyze-kernel/docs/cc/kconfig-analysis
```

**Step 2: 验证内核源码目录**
- 确认 `/home/zcxggmu/workspace/patch-work/linux/` 存在
- 确认 `arch/arm64/Kconfig` 和 `arch/riscv/Kconfig` 可访问

---

### Task 2: 提取 Kconfig 配置项列表

**Step 1: 提取 ARM64 配置项**
```bash
grep -E "^config\s+" /home/zcxggmu/workspace/patch-work/linux/arch/arm64/Kconfig | awk '{print $2}' | sort > arm64_configs.txt
```

**Step 2: 提取 RISC-V 配置项**
```bash
grep -E "^config\s+" /home/zcxggmu/workspace/patch-work/linux/arch/riscv/Kconfig | awk '{print $2}' | sort > riscv_configs.txt
```

**Step 3: 生成差异列表**
```bash
comm -23 arm64_configs.txt riscv_configs.txt > arm64_only_configs.txt
```

**预期输出**:
- `arm64_configs.txt`: ARM64 特有配置项
- `riscv_configs.txt`: RISC-V 特有配置项
- `arm64_only_configs.txt`: RISC-V 缺失的配置项

---

## 阶段二：逐项分析与归类 (Task 3-8)

### Task 3: 内存管理模块分析

**分析配置项**:
- `CONFIG_ARM64_PA_BITS`, `CONFIG_ARM64_VA_BITS`
- `CONFIG_ARM64_48BIT_VA`, `CONFIG_ARM64_52BIT_VA`
- `CONFIG_ARM64_USER_VA_BITS_52`
- `CONFIG_ARCH_HAS_MEMBARRIER_SYNC_CORE`
- `CONFIG_ARCH_HAS_STRICT_KERNEL_RWX`
- `CONFIG_ARCH_HAS_STRICT_MODULE_RWX`
- `CONFIG_ARCH_WANT_FRAME_POINTERS`
- `CONFIG_KUSER_HELPERS`
- `CONFIG_SET_FP`
- `CONFIG_SET_PSTATE`

**Step 1: 读取 ARM64 Kconfig 中相关配置**
```bash
grep -A5 "config ARM64_PA_BITS" /home/zcxggmu/workspace/patch-work/linux/arch/arm64/Kconfig
```

**Step 2: 检查 RISC-V 是否存在对应配置**
```bash
grep -E "CONFIG_(PA_BITS|VA_BITS|48BIT_VA|52BIT_VA)" /home/zcxggmu/workspace/patch-work/linux/arch/riscv/Kconfig
```

**Step 3: 搜索 Linux patch 链接**
- 使用 WebSearch 搜索: "site:lkml.org ARM64 VA_BITS patch"
- 记录功能描述与架构依赖分析

---

### Task 4: 虚拟化模块分析 (KVM/Hypervisor)

**分析配置项**:
- `CONFIG_KVM_INTR_VG`, `CONFIG_KVM_GUEST_TIMER`
- `CONFIG_KVM_GENERIC_DIRTYLOG_READ_PFN`
- `CONFIG_KVM_GENERIC_PV_TIME`
- `CONFIG_KVM_ARCH_NR_GSBITS`
- `CONFIG_ARM64_SVE`
- `CONFIG_ARM64_PMEM`
- `CONFIG_ARCH_HAS_PTE_DEVMAP`
- `CONFIG_KVM_INJECT_EXTINT`
- `CONFIG_KVM_MMIO`

**Step 1: 对比虚拟化相关配置**
```bash
grep -E "config KVM" /home/zcxggmu/workspace/patch-work/linux/arch/arm64/Kconfig
grep -E "config KVM" /home/zcxggmu/workspace/patch-work/linux/arch/riscv/Kconfig
```

**Step 2: 分析 SVE/向量支持差异**
```bash
grep -E "SVE|RISCV.*VECTOR" /home/zcxggmu/workspace/patch-work/linux/arch/arm64/Kconfig
grep -E "SVE|RISCV.*VECTOR" /home/zcxggmu/workspace/patch-work/linux/arch/riscv/Kconfig
```

---

### Task 5: 调试与诊断模块分析

**分析配置项**:
- `CONFIG_UNWINDER_FRAME_POINTER`
- `CONFIG_UNWINDER_ARM64_DMEM`
- `CONFIG_ARM64_DEBUG_PRIORITY_INVERSION`
- `CONFIG_KASAN`, `CONFIG_KASAN_SW_TAGS`
- `CONFIG_KCSAN`

**Step 1: 提取调试配置**
```bash
grep -E "config.*DEBUG|config.*KASAN|config.*KCSAN|config.*UNWINDER" /home/zcxggmu/workspace/patch-work/linux/arch/arm64/Kconfig
```

---

### Task 6: 安全特性模块分析

**分析配置项**:
- `CONFIG_ARM64_SW_TTBR0_PAN`
- `CONFIG_ARM64_TAGGED_ADDR_ABI`
- `CONFIG_BTI`
- `CONFIG_MTE`
- `CONFIG_RANDOMIZE_BASE`
- `CONFIG_STACKPROTECTOR`

**Step 1: 对比安全配置**
```bash
grep -E "config.*(BTI|MTE|PAN|STACKPROTECTOR|RANDOMIZE)" /home/zcxggmu/workspace/patch-work/linux/arch/arm64/Kconfig
```

---

### Task 7: 性能优化模块分析

**分析配置项**:
- `CONFIG_ARM64_AMU_EXTN`
- `CONFIG_ARM64_CNP`
- `CONFIG_ARM64_LSE_ATOMICS`
- `CONFIG_DCB`
- `CONFIG_ARM_SDE_INTERFACE`
- `CONFIG_SCHED_MC`, `CONFIG_SCHED_SMT`

**Step 1: 提取性能配置**
```bash
grep -E "config.*(AMU|CNP|LSE|DCB|SCHED)" /home/zcxggmu/workspace/patch-work/linux/arch/arm64/Kconfig
```

---

### Task 8: 中断与异常处理模块分析

**分析配置项**:
- `CONFIG_ARM_GIC_V3_ITS`
- `CONFIG_ARM_GIC_V3_NVHE`
- `CONFIG_ARCH_HIBERNATION_POSSIBLE`
- `CONFIG_SUSPEND`
- `CONFIG_HIBERNATION`

**Step 1: 对比中断/电源配置**
```bash
grep -E "config.*(GIC|SUSPEND|HIBERNATION)" /home/zcxggmu/workspace/patch-work/linux/arch/arm64/Kconfig
```

---

## 阶段三：详细分析与 patch 收集 (Task 9-12)

### Task 9: 生成初步差异报告

**Step 1: 合并所有差异配置项**
```bash
cat arm64_only_configs.txt | sort -u > all_missing_configs.txt
```

**Step 2: 初步分类**
- 统计各模块缺失数量
- 标记架构特有 vs 可移植到 RISC-V 的配置

---

### Task 10: 搜索 ARM64 特性 Linux Patch

**搜索策略**:
1. 对每个关键缺失配置项，搜索相关 commit
2. 使用模式: "LKML ARM64 [CONFIG_NAME] commit"
3. 记录: commit hash, 提交描述, 日期

**示例搜索**:
- "LKML ARM64 MTE memory tagging commit"
- "LKML ARM64 BTI branch target identification commit"
- "LKML ARM64 SVE scalable vector extension commit"

---

### Task 11: 深度分析每个缺失配置

**分析模板**:
```markdown
### CONFIG_XXX 分析

**功能描述**: [从 Kconfig help 提取]

**ARM64 实现**:
- 代码路径: `arch/arm64/...`
- 首次引入: [commit hash]

**RISC-V 现状**:
- 是否存在: [是/否]
- 对应替代: [如有]

**RISC-V 可行性分析**:
- 硬件依赖: [是否需要特定 RISC-V 扩展]
- 实现难度: [低/中/高]
- 优先级建议: [P0-P3]

**参考 Patch**:
- [LKML link 1]
- [LKML link 2]
```

---

### Task 12: 按模块汇总报告

**输出文件**: `kconfig-analysis/modules/summary.md`

**模块分类**:
1. 内存管理 (Memory Management)
2. 虚拟化 (Virtualization)
3. SIMD/向量 (SIMD/Vector)
4. 安全特性 (Security)
5. 调试诊断 (Debug/Diagnostics)
6. 性能优化 (Performance)
7. 中断与电源 (IRQ/Power)
8. 其他架构特有 (Architecture Specific)

---

## 阶段四：输出与验证 (Task 13-15)

### Task 13: 生成最终报告

**输出文件**:
- 主报告: `kconfig-analysis/ARM64_RISC_V_Kconfig_Gap_Analysis.md`
- 摘要: `kconfig-analysis/README.md`
- 详细数据: `kconfig-analysis/data/`

**Step 1: 生成 markdown 报告**

**Step 2: 交叉验证**
- 随机抽取 5 个配置项验证分析准确性
- 确认 patch 链接可访问

---

### Task 14: 代码审查 (可选)

使用 simplify skill 对生成的报告进行质量检查

---

### Task 15: 最终交付

**交付物**:
1. 完整的差异分析 Markdown 报告
2. 包含 patch 链接的参考资料
3. 按模块分类的缺失特性清单
4. RISC-V 支持建议优先级

---

## 关键里程碑

| 阶段 | 里程碑 | 预计复杂度 |
|------|--------|-----------|
| 阶段一 | 完成配置项提取 | 低 |
| 阶段二 | 完成 8 个模块分析 | 高 |
| 阶段三 | 完成 patch 收集 | 高 |
| 阶段四 | 生成最终报告 | 中 |

---

## 风险与挑战

1. **配置项数量**: ARM64 约 200+ 独有配置项，需要筛选关键差异
2. **patch 链接时效**: 部分旧 patch 链接可能失效
3. **可支持性判断**: 部分特性需要深入内核代码分析
4. **范围控制**: 需聚焦核心差异，避免过度展开

---

## 扩展方向 (可选)

1. **时序分析**: 对比各特性在 ARM64 和 RISC-V 上的演进时间线
2. **上游状态**: 列出 RISC-V 特性开发中的 patch 系列
3. **性能影响**: 量化各缺失特性对 RISC-V 生态的影响
