# RISC-V 相对 arm64/x86 架构接口差距：执行摘要

## 结论

本研究以 Linux mainline `d96fcfe1b7f94ac742984ae7986b94a116abff1b`、linux-next `bee763d5f341b99cf472afeb508d4988f62a6ca1` 和 2025-01-01 至 2026-07-10 的补丁讨论为固定基线，聚焦 RISC-V 相对 arm64/x86 的架构接口差距、可直接移植点和跨架构通用化机会。

最终从 127 个领域原始候选中完成源码核验、邮件状态校准、伪差距剔除和跨报告去重，形成 **90 个主候选**：P0 26 个、P1 48 个、P2 16 个。这些条目不是功能愿望清单，而是具有明确 Linux 接口、源码落点、补丁边界和验证路径的贡献题目。

## 核心判断

- **近期最有效的切入点是 G1/G2。** 优先实现已有 generic hook 的 RISC-V 后端，或把 arm64/x86/RISC-V 重复 helper 下沉为公共实现。
- **不要按 Kconfig 名称机械补齐。** 缺少 `select` 可能是不同硬件模型、已有 fallback，或公共前置已合入但架构后端尚未接线。
- **mainline、linux-next、RFC 必须分层。** 本清单有 1 项主体在 linux-next、7 项 active RFC、1 项 dormant、81 项 unclaimed。
- **内存、可观测性和通用化最适合持续贡献。** 三类合计 52 项，包含大量不依赖新硬件的接口实现、测试和机械重构。
- **Nested、CoVE、direct injection 等长期项必须服从基础设施顺序。** P2 代表边界清楚但受 UAPI、固件、硬件或安全模型约束。

## 精确统计

| 维度 | 分类 | 数量 |
|---|---|---:|
| 领域 | MMU/Memory | 16 |
| 领域 | IRQ/SMP/Time | 10 |
| 领域 | Core/ABI/Hardening | 18 |
| 领域 | Platform/ACPI/RAS | 13 |
| 领域 | KVM/IOMMU | 15 |
| 领域 | Genericization | 18 |
| 优先级 | P0 | 26 |
| 优先级 | P1 | 48 |
| 优先级 | P2 | 16 |
| G 分类 | G0 | 4 |
| G 分类 | G1 | 29 |
| G 分类 | G2 | 29 |
| G 分类 | G3 | 21 |
| G 分类 | G4 | 7 |
| 状态 | mainline | 0 |
| 状态 | next | 1 |
| 状态 | active RFC | 7 |
| 状态 | dormant | 1 |
| 状态 | unclaimed | 81 |
| 原始架构 | x86 | 6 |
| 原始架构 | arm64 | 39 |
| 原始架构 | x86+arm64 | 41 |
| 原始架构 | shared | 4 |

## P0 候选

| ID | 候选 | 领域 | G | 状态 | 原始架构 | 分数 |
|---|---|---|---|---|---|---:|
| [GEN-02](08-genericization-opportunities.md#gen-02) | 通用 register-offset table walker | [Genericization](08-genericization-opportunities.md) | G2 | unclaimed | x86+arm64 | 29 |
| [GEN-03](08-genericization-opportunities.md#gen-03) | 复用现有 perf_get_regs_user() generic fallback | [Genericization](08-genericization-opportunities.md) | G2 | unclaimed | x86+arm64 | 29 |
| [GEN-06](08-genericization-opportunities.md#gen-06) | 下沉 raw_pci_read/write() 通用 bus lookup | [Genericization](08-genericization-opportunities.md) | G2 | unclaimed | arm64 | 29 |
| [GEN-09](08-genericization-opportunities.md#gen-09) | 提供 copy_oldmem_page() generic default | [Genericization](08-genericization-opportunities.md) | G2 | unclaimed | arm64 | 29 |
| [GEN-13](08-genericization-opportunities.md#gen-13) | 机械下沉 cacheinfo ci_leaf_init() | [Genericization](08-genericization-opportunities.md) | G2 | unclaimed | arm64 | 29 |
| [CORE-14](05-core-abi-observability-hardening.md#core-14) | 选择 HAVE_CMPXCHG_LOCAL | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G0 | unclaimed | x86+arm64 | 28 |
| [CORE-01](05-core-abi-observability-hardening.md#core-01) | reliable unwinder 与 livepatch enablement | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G1 | active RFC | x86+arm64 | 26 |
| [CORE-06](05-core-abi-observability-hardening.md#core-06) | 实现 arch_bpf_stack_walk() | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G1 | active RFC | x86+arm64 | 26 |
| [CORE-07](05-core-abi-observability-hardening.md#core-07) | RISC-V BPF exceptions | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G1 | active RFC | x86+arm64 | 26 |
| [CORE-08](05-core-abi-observability-hardening.md#core-08) | BPF bpf2bpf 与 subprog tailcalls 混用 | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G1 | active RFC | x86+arm64 | 26 |
| [CORE-16](05-core-abi-observability-hardening.md#core-16) | 实现 ARCH_HAS_EXECMEM_ROX | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G1 | unclaimed | x86+arm64 | 26 |
| [IRQ-09](04-irq-smp-time.md#irq-09) | clockevent 补齐 oneshot-stopped 状态 | [IRQ/SMP/Time](04-irq-smp-time.md) | G1 | unclaimed | x86+arm64 | 26 |
| [MM-02](03-mmu-memory-tlb.md#mm-02) | RISC-V 批量非一致 DMA 同步 | [MMU/Memory](03-mmu-memory-tlb.md) | G1 | unclaimed | arm64 | 26 |
| [MM-05](03-mmu-memory-tlb.md#mm-05) | 批量清除大 folio PTE accessed 位 | [MMU/Memory](03-mmu-memory-tlb.md) | G1 | unclaimed | arm64 | 26 |
| [MM-11](03-mmu-memory-tlb.md#mm-11) | memory hot-remove 范围 TLB 批处理 | [MMU/Memory](03-mmu-memory-tlb.md) | G1 | unclaimed | arm64 | 26 |
| [PLAT-01](06-platform-acpi-numa-power-ras.md#plat-01) | RISC-V ACPI CPU physical hotplug | [Platform/ACPI/RAS](06-platform-acpi-numa-power-ras.md) | G1 | unclaimed | arm64 | 26 |
| [PLAT-06](06-platform-acpi-numa-power-ras.md#plat-06) | CPPC FIE IRQ-off 读取与 RV32 READ_HI | [Platform/ACPI/RAS](06-platform-acpi-numa-power-ras.md) | G1 | unclaimed | arm64 | 26 |
| [VIRT-01](07-kvm-iommu-virtualization.md#virt-01) | KVM G-stage 与 RISC-V IOMMU ptdump 可观测性 | [KVM/IOMMU](07-kvm-iommu-virtualization.md) | G1 | unclaimed | arm64 | 26 |
| [VIRT-02](07-kvm-iommu-virtualization.md#virt-02) | G-stage 脱锁销毁与可调度化 | [KVM/IOMMU](07-kvm-iommu-virtualization.md) | G1 | unclaimed | arm64 | 26 |
| [VIRT-03](07-kvm-iommu-virtualization.md#virt-03) | guest_memfd shared/mappable 第一阶段 | [KVM/IOMMU](07-kvm-iommu-virtualization.md) | G1 | unclaimed | x86+arm64 | 26 |
| [VIRT-04](07-kvm-iommu-virtualization.md#virt-04) | 实现 KVM_PRE_FAULT_MEMORY | [KVM/IOMMU](07-kvm-iommu-virtualization.md) | G1 | unclaimed | x86+arm64 | 26 |
| [VIRT-06](07-kvm-iommu-virtualization.md#virt-06) | 启用 KVM_VFIO 并定义 coherency 语义 | [KVM/IOMMU](07-kvm-iommu-virtualization.md) | G1 | unclaimed | x86+arm64 | 26 |
| [CORE-13](05-core-abi-observability-hardening.md#core-13) | native acquire/release AMO variants | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G3 | unclaimed | arm64 | 25 |
| [MM-06](03-mmu-memory-tlb.md#mm-06) | 实现 pte_needs_flush() 与 huge_pmd_needs_flush() | [MMU/Memory](03-mmu-memory-tlb.md) | G3 | unclaimed | x86+arm64 | 25 |
| [MM-07](03-mmu-memory-tlb.md#mm-07) | 实现原子 ptep_try_set() | [MMU/Memory](03-mmu-memory-tlb.md) | G3 | unclaimed | x86+arm64 | 25 |
| [MM-10](03-mmu-memory-tlb.md#mm-10) | RISC-V memory hot-remove 叶子边界与安全释放 | [MMU/Memory](03-mmu-memory-tlb.md) | G3 | unclaimed | arm64 | 25 |

## 推荐推进顺序

1. **小接口与现有 hook：** clockevent 状态接线、DMA batching、PTE/TLB 原语、ptrace/perf helper、ACPI/PCI 默认实现。
2. **活跃 RFC 跟进：** reliable stacktrace/livepatch、BPF、硬件断点等已经有评审上下文的系列。
3. **跨架构通用化：** 先提交无行为变化的公共 helper，再分别迁移 arm64、x86、RISC-V。
4. **平台闭环：** ACPI CPU hotplug、SRAT/NUMA、APEI/GHES、KVM/VFIO/IOMMU 需要成套启动与错误路径测试。
5. **长期基础设施：** nested KVM、CoVE、confidential DMA、direct injection 等应在 UAPI 和硬件模型稳定后推进。

## 文档导航

- [研究方法与基线](01-methodology-and-baselines.md)：范围、基线、评分和状态定义。
- [统一候选索引](02-interface-gap-inventory.md)：90 项候选及领域入口。
- [贡献路线图](09-ranked-contribution-roadmap.md)：按 P0/P1/P2 排列的实施顺序。
- [源码与邮件索引](10-source-and-mail-index.md)：公开固定源码、邮件和逐候选来源。
