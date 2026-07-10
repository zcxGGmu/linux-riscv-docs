# RISC-V 架构接口贡献路线图

路线图以补丁可落地性为主，而不是按功能吸引力排序。同一主题应先完成行为不变的 generic helper，再提交 RISC-V enablement 或优化。

## 总体分布

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

## 阶段 A：近期可启动

| ID | 候选 | 领域 | G | 状态 | 分数 |
|---|---|---|---|---|---:|
| [MM-02](03-mmu-memory-tlb.md#mm-02) | RISC-V 批量非一致 DMA 同步 | [MMU/Memory](03-mmu-memory-tlb.md) | G1 | unclaimed | 26 |
| [MM-05](03-mmu-memory-tlb.md#mm-05) | 批量清除大 folio PTE accessed 位 | [MMU/Memory](03-mmu-memory-tlb.md) | G1 | unclaimed | 26 |
| [MM-11](03-mmu-memory-tlb.md#mm-11) | memory hot-remove 范围 TLB 批处理 | [MMU/Memory](03-mmu-memory-tlb.md) | G1 | unclaimed | 26 |
| [MM-06](03-mmu-memory-tlb.md#mm-06) | 实现 pte_needs_flush() 与 huge_pmd_needs_flush() | [MMU/Memory](03-mmu-memory-tlb.md) | G3 | unclaimed | 25 |
| [MM-07](03-mmu-memory-tlb.md#mm-07) | 实现原子 ptep_try_set() | [MMU/Memory](03-mmu-memory-tlb.md) | G3 | unclaimed | 25 |
| [MM-10](03-mmu-memory-tlb.md#mm-10) | RISC-V memory hot-remove 叶子边界与安全释放 | [MMU/Memory](03-mmu-memory-tlb.md) | G3 | unclaimed | 25 |
| [IRQ-09](04-irq-smp-time.md#irq-09) | clockevent 补齐 oneshot-stopped 状态 | [IRQ/SMP/Time](04-irq-smp-time.md) | G1 | unclaimed | 26 |
| [CORE-14](05-core-abi-observability-hardening.md#core-14) | 选择 HAVE_CMPXCHG_LOCAL | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G0 | unclaimed | 28 |
| [CORE-01](05-core-abi-observability-hardening.md#core-01) | reliable unwinder 与 livepatch enablement | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G1 | active RFC | 26 |
| [CORE-06](05-core-abi-observability-hardening.md#core-06) | 实现 arch_bpf_stack_walk() | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G1 | active RFC | 26 |
| [CORE-07](05-core-abi-observability-hardening.md#core-07) | RISC-V BPF exceptions | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G1 | active RFC | 26 |
| [CORE-08](05-core-abi-observability-hardening.md#core-08) | BPF bpf2bpf 与 subprog tailcalls 混用 | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G1 | active RFC | 26 |
| [CORE-16](05-core-abi-observability-hardening.md#core-16) | 实现 ARCH_HAS_EXECMEM_ROX | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G1 | unclaimed | 26 |
| [CORE-13](05-core-abi-observability-hardening.md#core-13) | native acquire/release AMO variants | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G3 | unclaimed | 25 |
| [PLAT-01](06-platform-acpi-numa-power-ras.md#plat-01) | RISC-V ACPI CPU physical hotplug | [Platform/ACPI/RAS](06-platform-acpi-numa-power-ras.md) | G1 | unclaimed | 26 |
| [PLAT-06](06-platform-acpi-numa-power-ras.md#plat-06) | CPPC FIE IRQ-off 读取与 RV32 READ_HI | [Platform/ACPI/RAS](06-platform-acpi-numa-power-ras.md) | G1 | unclaimed | 26 |
| [VIRT-01](07-kvm-iommu-virtualization.md#virt-01) | KVM G-stage 与 RISC-V IOMMU ptdump 可观测性 | [KVM/IOMMU](07-kvm-iommu-virtualization.md) | G1 | unclaimed | 26 |
| [VIRT-02](07-kvm-iommu-virtualization.md#virt-02) | G-stage 脱锁销毁与可调度化 | [KVM/IOMMU](07-kvm-iommu-virtualization.md) | G1 | unclaimed | 26 |
| [VIRT-03](07-kvm-iommu-virtualization.md#virt-03) | guest_memfd shared/mappable 第一阶段 | [KVM/IOMMU](07-kvm-iommu-virtualization.md) | G1 | unclaimed | 26 |
| [VIRT-04](07-kvm-iommu-virtualization.md#virt-04) | 实现 KVM_PRE_FAULT_MEMORY | [KVM/IOMMU](07-kvm-iommu-virtualization.md) | G1 | unclaimed | 26 |
| [VIRT-06](07-kvm-iommu-virtualization.md#virt-06) | 启用 KVM_VFIO 并定义 coherency 语义 | [KVM/IOMMU](07-kvm-iommu-virtualization.md) | G1 | unclaimed | 26 |
| [GEN-02](08-genericization-opportunities.md#gen-02) | 通用 register-offset table walker | [Genericization](08-genericization-opportunities.md) | G2 | unclaimed | 29 |
| [GEN-03](08-genericization-opportunities.md#gen-03) | 复用现有 perf_get_regs_user() generic fallback | [Genericization](08-genericization-opportunities.md) | G2 | unclaimed | 29 |
| [GEN-06](08-genericization-opportunities.md#gen-06) | 下沉 raw_pci_read/write() 通用 bus lookup | [Genericization](08-genericization-opportunities.md) | G2 | unclaimed | 29 |
| [GEN-09](08-genericization-opportunities.md#gen-09) | 提供 copy_oldmem_page() generic default | [Genericization](08-genericization-opportunities.md) | G2 | unclaimed | 29 |
| [GEN-13](08-genericization-opportunities.md#gen-13) | 机械下沉 cacheinfo ci_leaf_init() | [Genericization](08-genericization-opportunities.md) | G2 | unclaimed | 29 |

### P0 首个可提交单元

以下边界刻意缩小为可独立评审的第一步；完整系列见候选卡片。

- [MM-02](03-mmu-memory-tlb.md#mm-02) **RISC-V 批量非一致 DMA 同步**：先把 Zicbom 同步拆成 issue-only helper 与单一 completion fence，并保留 vendor 同步 fallback。
- [MM-05](03-mmu-memory-tlb.md#mm-05) **批量清除大 folio PTE accessed 位**：仅新增 RISC-V `test_and_clear_young_ptes()` 批量 helper，不改变 TLB 语义。
- [MM-11](03-mmu-memory-tlb.md#mm-11) **memory hot-remove 范围 TLB 批处理**：先把单次 hot-remove 的逐页 flush 合并为一次范围 invalidation。
- [MM-06](03-mmu-memory-tlb.md#mm-06) **实现 pte_needs_flush() 与 huge_pmd_needs_flush()**：先实现 4K PTE 的 `pte_needs_flush()` 位级决策和 selftest；THP 后续。
- [MM-07](03-mmu-memory-tlb.md#mm-07) **实现原子 ptep_try_set()**：仅实现空 PTE 的原子 `cmpxchg` 安装与 KUnit；BPF enablement 后续。
- [MM-10](03-mmu-memory-tlb.md#mm-10) **RISC-V memory hot-remove 叶子边界与安全释放**：先增加 hot-remove preflight，拒绝切开现有 leaf；释放流程重构后续。
- [IRQ-09](04-irq-smp-time.md#irq-09) **clockevent 补齐 oneshot-stopped 状态**：接线 `.set_state_oneshot_stopped = riscv_clock_shutdown`，附 Sstc/SBI 状态测试。
- [CORE-14](05-core-abi-observability-hardening.md#core-14) **选择 HAVE_CMPXCHG_LOCAL**：仅选择 `HAVE_CMPXCHG_LOCAL`，补编译矩阵和原子语义测试。
- [CORE-01](05-core-abi-observability-hardening.md#core-01) **reliable unwinder 与 livepatch enablement**：先提交 reliable unwinder、边界规则和负测；livepatch enablement 单独后续。
- [CORE-06](05-core-abi-observability-hardening.md#core-06) **实现 arch_bpf_stack_walk()**：只实现 `arch_bpf_stack_walk()` 与对应 selftest，不同时改异常或 tailcall。
- [CORE-07](05-core-abi-observability-hardening.md#core-07) **RISC-V BPF exceptions**：先定义异常 landing ABI 并支持一个异常类别；组合优化后续。
- [CORE-08](05-core-abi-observability-hardening.md#core-08) **BPF bpf2bpf 与 subprog tailcalls 混用**：先修正 bpf2bpf 与 subprog tailcall 的 frame/counter 规则，并补单一组合测试。
- [CORE-16](05-core-abi-observability-hardening.md#core-16) **实现 ARCH_HAS_EXECMEM_ROX**：先实现通用 RW→ROX allocator 并迁移一个 BPF JIT consumer；其他消费者后续。
- [CORE-13](05-core-abi-observability-hardening.md#core-13) **native acquire/release AMO variants**：先替换一个 AMO primitive 的 fence fallback，并用 LKMM/objdump 证明等价。
- [PLAT-01](06-platform-acpi-numa-power-ras.md#plat-01) **RISC-V ACPI CPU physical hotplug**：先实现 ACPI UID↔hartid↔cpuid 映射 helper 和失败回滚；physical hotplug hook 后续。
- [PLAT-06](06-platform-acpi-numa-power-ras.md#plat-06) **CPPC FIE IRQ-off 读取与 RV32 READ_HI**：先修 RV32 `SBI_CPPC_READ_HI` 与 high-low-high 读取；FIE IRQ-off 扩展后续。
- [VIRT-01](07-kvm-iommu-virtualization.md#virt-01) **KVM G-stage 与 RISC-V IOMMU ptdump 可观测性**：先增加只读 G-stage walker 与 VM debugfs；IOMMU dump 另起系列。
- [VIRT-02](07-kvm-iommu-virtualization.md#virt-02) **G-stage 脱锁销毁与可调度化**：只做 teardown root detach 与锁外释放；普通 memslot zap 保持不变。
- [VIRT-03](07-kvm-iommu-virtualization.md#virt-03) **guest_memfd shared/mappable 第一阶段**：只启用 shared/mappable guest_memfd 的单一 fault path；private/CoVE 后续。
- [VIRT-04](07-kvm-iommu-virtualization.md#virt-04) **实现 KVM_PRE_FAULT_MEMORY**：先接 `KVM_PRE_FAULT_MEMORY` 到现有 G-stage fault helper，并限制单一 memslot 类型。
- [VIRT-06](07-kvm-iommu-virtualization.md#virt-06) **启用 KVM_VFIO 并定义 coherency 语义**：先启用 coherent 平台的 `KVM_VFIO` 基本路径；non-coherent DMA 策略单独 RFC。
- [GEN-02](08-genericization-opportunities.md#gen-02) **通用 register-offset table walker**：新增 register-offset table walker 并只迁移 RISC-V；其他架构后续。
- [GEN-03](08-genericization-opportunities.md#gen-03) **复用现有 perf_get_regs_user() generic fallback**：让 RISC-V 复用现有 fallback，保留 x86-64 override；不新增 capability。
- [GEN-06](08-genericization-opportunities.md#gen-06) **下沉 raw_pci_read/write() 通用 bus lookup**：新增 `pci_generic_raw_read/write()` 并只迁移 RISC-V；arm64 后续。
- [GEN-09](08-genericization-opportunities.md#gen-09) **提供 copy_oldmem_page() generic default**：新增 memremap 版 generic default 并迁移 RISC-V；特殊架构保留 override。
- [GEN-13](08-genericization-opportunities.md#gen-13) **机械下沉 cacheinfo ci_leaf_init()**：仅下沉 `ci_leaf_init()` 并迁移 RISC-V；cache 信息来源策略不变。

## 阶段 B：中期系列

| ID | 候选 | 领域 | G | 状态 | 分数 |
|---|---|---|---|---|---:|
| [MM-03](03-mmu-memory-tlb.md#mm-03) | 实现 cpu_cache_invalidate_memregion() | [MMU/Memory](03-mmu-memory-tlb.md) | G1 | unclaimed | 23 |
| [MM-04](03-mmu-memory-tlb.md#mm-04) | 补齐 ARCH_HAS_UACCESS_FLUSHCACHE | [MMU/Memory](03-mmu-memory-tlb.md) | G1 | unclaimed | 23 |
| [MM-12](03-mmu-memory-tlb.md#mm-12) | 通用化 hotplug 页表 teardown walker | [MMU/Memory](03-mmu-memory-tlb.md) | G2 | unclaimed | 23 |
| [MM-14](03-mmu-memory-tlb.md#mm-14) | arm64/RISC-V versioned ASID allocator 公共核心 | [MMU/Memory](03-mmu-memory-tlb.md) | G2 | unclaimed | 23 |
| [MM-16](03-mmu-memory-tlb.md#mm-16) | 统一 kernel mapping synchronization 模型 | [MMU/Memory](03-mmu-memory-tlb.md) | G2 | unclaimed | 23 |
| [MM-01](03-mmu-memory-tlb.md#mm-01) | RISC-V 接入 generic lazy-MMU 接口 | [MMU/Memory](03-mmu-memory-tlb.md) | G3 | unclaimed | 20 |
| [MM-08](03-mmu-memory-tlb.md#mm-08) | PBMT set_memory 与 PFN-map 缓存类型一致性 | [MMU/Memory](03-mmu-memory-tlb.md) | G3 | unclaimed | 20 |
| [MM-09](03-mmu-memory-tlb.md#mm-09) | 重合并 pageattr 碎片化的 direct-map 大页 | [MMU/Memory](03-mmu-memory-tlb.md) | G3 | unclaimed | 20 |
| [MM-15](03-mmu-memory-tlb.md#mm-15) | 基于 active hart 的本地/远程 TLB 选择 | [MMU/Memory](03-mmu-memory-tlb.md) | G3 | unclaimed | 20 |
| [IRQ-04](04-irq-smp-time.md#irq-04) | IMSIC Multi-MSI 分配与回滚 | [IRQ/SMP/Time](04-irq-smp-time.md) | G1 | unclaimed | 23 |
| [IRQ-01](04-irq-smp-time.md#irq-01) | RISC-V IRQ 入口接入 runtime constant | [IRQ/SMP/Time](04-irq-smp-time.md) | G3 | active RFC | 20 |
| [IRQ-06](04-irq-smp-time.md#irq-06) | IMSIC remote sync 改用 hard irq_work | [IRQ/SMP/Time](04-irq-smp-time.md) | G3 | unclaimed | 20 |
| [IRQ-08](04-irq-smp-time.md#irq-08) | SBI HSM late-AP cleanup 与代际控制 | [IRQ/SMP/Time](04-irq-smp-time.md) | G3 | unclaimed | 20 |
| [IRQ-10](04-irq-smp-time.md#irq-10) | RISC-V clocksource 稳定性测量与策略证明 | [IRQ/SMP/Time](04-irq-smp-time.md) | G3 | unclaimed | 20 |
| [CORE-17](05-core-abi-observability-hardening.md#core-17) | 默认启用 VMAP_STACK | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G0 | unclaimed | 24 |
| [CORE-09](05-core-abi-observability-hardening.md#core-09) | BPF stack arguments 与 private stack | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G1 | unclaimed | 23 |
| [CORE-12](05-core-abi-observability-hardening.md#core-12) | RISC-V KCSAN architecture enablement | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G1 | unclaimed | 23 |
| [CORE-03](05-core-abi-observability-hardening.md#core-03) | RISC-V static-call backend | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G3 | unclaimed | 20 |
| [CORE-04](05-core-abi-observability-hardening.md#core-04) | 完整 ftrace_regs 与 CFI-compatible call-ops | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G3 | unclaimed | 20 |
| [CORE-10](05-core-abi-observability-hardening.md#core-10) | BPF timed may_goto | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G3 | unclaimed | 20 |
| [CORE-02](05-core-abi-observability-hardening.md#core-02) | perf/ptrace/KGDB hardware breakpoints | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G4 | active RFC | 19 |
| [PLAT-13](06-platform-acpi-numa-power-ras.md#plat-13) | RISC-V ACPI memory hotplug 启用与系统测试 | [Platform/ACPI/RAS](06-platform-acpi-numa-power-ras.md) | G0 | unclaimed | 24 |
| [PLAT-02](06-platform-acpi-numa-power-ras.md#plat-02) | SRAT Generic Initiator 与 _OSC 能力接线 | [Platform/ACPI/RAS](06-platform-acpi-numa-power-ras.md) | G1 | unclaimed | 23 |
| [PLAT-04](06-platform-acpi-numa-power-ras.md#plat-04) | PSCI/SBI DT idle genpd 生命周期通用化 | [Platform/ACPI/RAS](06-platform-acpi-numa-power-ras.md) | G2 | unclaimed | 23 |
| [PLAT-05](06-platform-acpi-numa-power-ras.md#plat-05) | arm64/RISC-V ACPI FFH LPI 验证框架 | [Platform/ACPI/RAS](06-platform-acpi-numa-power-ras.md) | G2 | unclaimed | 23 |
| [PLAT-09](06-platform-acpi-numa-power-ras.md#plat-09) | EFI capsule cache-maintenance 通用 hook | [Platform/ACPI/RAS](06-platform-acpi-numa-power-ras.md) | G2 | unclaimed | 23 |
| [PLAT-10](06-platform-acpi-numa-power-ras.md#plat-10) | RISC-V crash hotplug 动态 elfcorehdr | [Platform/ACPI/RAS](06-platform-acpi-numa-power-ras.md) | G1 | unclaimed | 23 |
| [PLAT-11](06-platform-acpi-numa-power-ras.md#plat-11) | RISC-V APEI/GHES 基础与映射属性 | [Platform/ACPI/RAS](06-platform-acpi-numa-power-ras.md) | G1 | unclaimed | 23 |
| [PLAT-12](06-platform-acpi-numa-power-ras.md#plat-12) | GHES memory failure/EDAC 与 Generic Processor CPER | [Platform/ACPI/RAS](06-platform-acpi-numa-power-ras.md) | G1 | unclaimed | 23 |
| [VIRT-05](07-kvm-iommu-virtualization.md#virt-05) | RISC-V KVM userfault exits | [KVM/IOMMU](07-kvm-iommu-virtualization.md) | G1 | unclaimed | 23 |
| [VIRT-07](07-kvm-iommu-virtualization.md#virt-07) | IMSIC irq-bypass/direct-injection 生命周期与测试 | [KVM/IOMMU](07-kvm-iommu-virtualization.md) | G2 | unclaimed | 23 |
| [VIRT-09](07-kvm-iommu-virtualization.md#virt-09) | IOMMU fault queue、PRI/IOPF 与 page response | [KVM/IOMMU](07-kvm-iommu-virtualization.md) | G1 | unclaimed | 23 |
| [VIRT-10](07-kvm-iommu-virtualization.md#virt-10) | SVA、PASID 与 process-directory table | [KVM/IOMMU](07-kvm-iommu-virtualization.md) | G2 | unclaimed | 23 |
| [VIRT-12](07-kvm-iommu-virtualization.md#virt-12) | 基于 AMO_HWAD 的 DMA dirty tracking | [KVM/IOMMU](07-kvm-iommu-virtualization.md) | G1 | unclaimed | 23 |
| [VIRT-08](07-kvm-iommu-virtualization.md#virt-08) | RISC-V IOMMU MSI page table/MRIF 与 AIA/VFIO | [KVM/IOMMU](07-kvm-iommu-virtualization.md) | G4 | unclaimed | 19 |
| [VIRT-11](07-kvm-iommu-virtualization.md#virt-11) | IOMMUFD hw_info、nested HWPT 与 VMID/GSCID 协调 | [KVM/IOMMU](07-kvm-iommu-virtualization.md) | G4 | unclaimed | 19 |
| [GEN-01](08-genericization-opportunities.md#gen-01) | runtime-const 公共迭代器 | [Genericization](08-genericization-opportunities.md) | G2 | unclaimed | 23 |
| [GEN-04](08-genericization-opportunities.md#gen-04) | 生成式复用 ptdump 层级 callback | [Genericization](08-genericization-opportunities.md) | G2 | unclaimed | 23 |
| [GEN-05](08-genericization-opportunities.md#gen-05) | ACPI early table map/unmap 默认实现 | [Genericization](08-genericization-opportunities.md) | G2 | unclaimed | 23 |
| [GEN-07](08-genericization-opportunities.md#gen-07) | PCI topology opt-in dev_to_node helper | [Genericization](08-genericization-opportunities.md) | G2 | unclaimed | 23 |
| [GEN-08](08-genericization-opportunities.md#gen-08) | 统一 no-steal-acc 参数与策略所有权 | [Genericization](08-genericization-opportunities.md) | G2 | unclaimed | 23 |
| [GEN-10](08-genericization-opportunities.md#gen-10) | crash/kdump 默认 RAM walk hooks 与解析 wrapper | [Genericization](08-genericization-opportunities.md) | G2 | unclaimed | 23 |
| [GEN-11](08-genericization-opportunities.md#gen-11) | ftrace call-ops 选择 helper | [Genericization](08-genericization-opportunities.md) | G2 | unclaimed | 23 |
| [GEN-14](08-genericization-opportunities.md#gen-14) | 用 GENERIC_ARCH_TOPOLOGY 替换架构名判断 | [Genericization](08-genericization-opportunities.md) | G2 | dormant | 23 |
| [GEN-15](08-genericization-opportunities.md#gen-15) | PCI ACPI host 使用现有能力组合门控 | [Genericization](08-genericization-opportunities.md) | G2 | unclaimed | 23 |
| [GEN-17](08-genericization-opportunities.md#gen-17) | 向下增长栈 uretprobe 存活 helper | [Genericization](08-genericization-opportunities.md) | G2 | unclaimed | 23 |
| [GEN-18](08-genericization-opportunities.md#gen-18) | 参数化 syscall trace symbol matcher | [Genericization](08-genericization-opportunities.md) | G2 | unclaimed | 23 |
| [GEN-12](08-genericization-opportunities.md#gen-12) | LZO 快路径改用高效非对齐能力 | [Genericization](08-genericization-opportunities.md) | G3 | unclaimed | 20 |

## 阶段 C：架构证明与基础设施

| ID | 候选 | 领域 | G | 状态 | 分数 |
|---|---|---|---|---|---:|
| [MM-13](03-mmu-memory-tlb.md#mm-13) | 内核 data/BSS linear alias 只读化 | [MMU/Memory](03-mmu-memory-tlb.md) | G3 | unclaimed | 15 |
| [IRQ-02](04-irq-smp-time.md#irq-02) | 统一 root IRQ handler 注册与只读化 | [IRQ/SMP/Time](04-irq-smp-time.md) | G2 | unclaimed | 18 |
| [IRQ-03](04-irq-smp-time.md#irq-03) | 通用 per-CPU IPI descriptor 生命周期与 tick broadcast | [IRQ/SMP/Time](04-irq-smp-time.md) | G2 | unclaimed | 18 |
| [IRQ-05](04-irq-smp-time.md#irq-05) | x86/IMSIC MSI vector move 公共状态机 | [IRQ/SMP/Time](04-irq-smp-time.md) | G2 | unclaimed | 18 |
| [IRQ-07](04-irq-smp-time.md#irq-07) | ACPI IRQ dependency 通用化测试后续 | [IRQ/SMP/Time](04-irq-smp-time.md) | G0 | next | 18 |
| [CORE-18](05-core-abi-observability-hardening.md#core-18) | 实现 arch_within_stack_frames() | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G1 | unclaimed | 17 |
| [CORE-05](05-core-abi-observability-hardening.md#core-05) | kprobes-on-ftrace 与 optprobes 加速链 | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G3 | unclaimed | 15 |
| [CORE-11](05-core-abi-observability-hardening.md#core-11) | BPF tail-call poke descriptor | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G3 | unclaimed | 15 |
| [CORE-15](05-core-abi-observability-hardening.md#core-15) | HAVE_CMPXCHG_DOUBLE 与 Zacas/fallback | [Core/ABI/Hardening](05-core-abi-observability-hardening.md) | G4 | active RFC | 14 |
| [PLAT-03](06-platform-acpi-numa-power-ras.md#plat-03) | arm64/RISC-V ACPI NUMA 后端通用化 | [Platform/ACPI/RAS](06-platform-acpi-numa-power-ras.md) | G2 | unclaimed | 18 |
| [PLAT-07](06-platform-acpi-numa-power-ras.md#plat-07) | CPPC artificial Energy Model 通用化 | [Platform/ACPI/RAS](06-platform-acpi-numa-power-ras.md) | G2 | unclaimed | 18 |
| [PLAT-08](06-platform-acpi-numa-power-ras.md#plat-08) | EFI runtime exception recovery 与恢复栈 | [Platform/ACPI/RAS](06-platform-acpi-numa-power-ras.md) | G3 | unclaimed | 15 |
| [VIRT-13](07-kvm-iommu-virtualization.md#virt-13) | RISC-V vIOMMU、vEVENTQ 与 HW queue | [KVM/IOMMU](07-kvm-iommu-virtualization.md) | G4 | unclaimed | 14 |
| [VIRT-14](07-kvm-iommu-virtualization.md#virt-14) | nested KVM architectural state 与 shadow G-stage | [KVM/IOMMU](07-kvm-iommu-virtualization.md) | G4 | unclaimed | 14 |
| [VIRT-15](07-kvm-iommu-virtualization.md#virt-15) | CoVE private memory、guest_memfd 与 memory attributes | [KVM/IOMMU](07-kvm-iommu-virtualization.md) | G4 | unclaimed | 14 |
| [GEN-16](08-genericization-opportunities.md#gen-16) | 显式 opt-in 的 no-immediate-flush young-bit helper | [Genericization](08-genericization-opportunities.md) | G3 | unclaimed | 15 |

## 建议的并行工作流

1. **接口小补丁流：** 每次只处理一个 hook、helper 或 Kconfig capability，先跑三架构构建矩阵。
2. **活跃 RFC 跟进流：** 复现评审意见，补测试或拆分系列，避免平行重写。
3. **通用化流：** 公共 helper、参考架构迁移、RISC-V 迁移分别提交。
4. **平台验证流：** QEMU ACPI/AIA、CPU/memory hotplug、KVM/VFIO/IOMMU 建立可重复启动和故障注入环境。
5. **长期规范流：** nested、CoVE、confidential DMA 在 UAPI 和固件 ABI 稳定前仅推进可独立合入的 generic 前置。

## 开工检查

- 再次检查 mainline、linux-next 和对应 maintainer tree；
- 在 lore 搜索候选 ID 对应符号和系列主题；
- 先验证最小补丁边界能独立构建和回滚；
- 对 G3/G4 项先写架构契约和负面测试；
- 使用 `scripts/get_maintainer.pl` 生成最终收件人列表。
