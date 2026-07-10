# 源码与邮件来源索引

## 固定源码

- [Torvalds mainline `d96fcfe1b7f94ac742984ae7986b94a116abff1b`](https://git.kernel.org/torvalds/c/d96fcfe1b7f94ac742984ae7986b94a116abff1b)。
- [linux-next `bee763d5f341b99cf472afeb508d4988f62a6ca1`](https://git.kernel.org/next/c/bee763d5f341b99cf472afeb508d4988f62a6ca1)。
- 研究阶段使用上述提交的本地只读快照；公开复核只依赖固定 commit 和逐候选链接，不依赖文档仓库之外的本地目录。

## 邮件研究索引

- 时间窗口：2025-01-01 至 2026-07-10。
- [linux-arm-kernel Pipermail](https://lists.infradead.org/pipermail/linux-arm-kernel/)。
- [Linux RISC-V lore](https://lore.kernel.org/linux-riscv/)。
- [KVM lore](https://lore.kernel.org/kvm/) 与 [KVM Patchwork](https://patchwork.kernel.org/project/kvm/list/?state=*&archive=both)。
- 逐候选条目保留固定 commit、Message-ID、lore、Pipermail 或 Patchwork 链接，这些公开来源是复核依据。

## 候选来源

### [MMU/Memory](03-mmu-memory-tlb.md)

#### [MM-01：RISC-V 接入 generic lazy-MMU 接口](03-mmu-memory-tlb.md#mm-01)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`include/linux/pgtable.h`；`mm/pagewalk.c`
- **RISC-V**：`arch/riscv/Kconfig`；`arch/riscv/include/asm/pgtable.h`。
- **arm64**：`arch/arm64/Kconfig:ARCH_HAS_LAZY_MMU_MODE`；`arch/arm64/include/asm/pgtable.h`
- **x86**：`arch/x86/Kconfig:PARAVIRT_XXL`；`arch/x86/include/asm/paravirt.h`
- **其他**：`ARCH_HAS_LAZY_MMU_MODE`；`lazy_mmu_mode_enable()`；`lazy_mmu_mode_disable()`；`lazy_mmu_mode_pause()`；`lazy_mmu_mode_resume()`；`arch_enter_lazy_mmu_mode()`；`arch_flush_lazy_mmu_mode()`；`arch_leave_lazy_mmu_mode()`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=0a096ab7a3a6e2859c3c88988e548c5c213138bc)；[来源 2](https://lore.kernel.org/linux-arm-kernel/20251215150323.2218608-8-kevin.brodsky@arm.com/)。

#### [MM-02：RISC-V 批量非一致 DMA 同步](03-mmu-memory-tlb.md#mm-02)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`kernel/dma/direct.h`；`kernel/dma/direct.c`；`drivers/iommu/dma-iommu.c`；`kernel/dma/swiotlb.c`；`include/linux/dma-map-ops.h`
- **RISC-V**：`arch/riscv/mm/dma-noncoherent.c`
- **arm64**：`arch/arm64/mm/dma-mapping.c`
- **x86**：`arch/x86/Kconfig`
- **其他**：`arch_sync_dma_flush()`；`dcache_clean_poc_nosync()`；`dcache_inval_poc_nosync()`；`ARCH_HAS_BATCHED_DMA_SYNC`；`arch_dma_cache_wback()`；`arch_dma_cache_inv()`；`arch_dma_cache_wback_inv()`；`arch_sync_dma_for_{cpu,device}()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=d7eafe655b741dfc241d5b920f6d2cea45b568d9)；[来源 2](https://lore.kernel.org/r/20260228221258.59918-1-21cnbao@gmail.com)；[来源 3](https://lore.kernel.org/r/20260228221239.59903-1-21cnbao@gmail.com)；[来源 4](https://lore.kernel.org/linux-arm-kernel/20260228221316.59934-1-21cnbao@gmail.com/)。

#### [MM-03：实现 cpu_cache_invalidate_memregion()](03-mmu-memory-tlb.md#mm-03)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`include/linux/memory_hotplug.h`
- **RISC-V**：`arch/riscv/mm/cache-ops.c`；`arch/riscv/include/asm/cacheflush.h`；`arch/riscv/mm/dma-noncoherent.c`
- **arm64**：`arch/arm64/mm/cache.S`
- **x86**：`arch/x86/mm/pat/set_memory.c:cpu_cache_invalidate_memregion()`
- **其他**：`cpu_cache_invalidate_memregion()`；`ARCH_HAS_CPU_CACHE_INVALIDATE_MEMREGION`；`phys_to_virt()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=b43652d867cf2a5f31b14e3d9a320ad01fca0992)；[来源 2](https://lore.kernel.org/linux-mm/686eedb25ed02_24471002e@dwillia2-xfh.jf.intel.com.notmuch/)。

#### [MM-04：补齐 ARCH_HAS_UACCESS_FLUSHCACHE](03-mmu-memory-tlb.md#mm-04)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`drivers/nvdimm/pmem.c`；`drivers/dax/super.c`；`drivers/md/dm-writecache.c`；`drivers/md/dm-pcache/`
- **RISC-V**：`arch/riscv/lib/`；`arch/riscv/include/asm/cacheflush.h`；`arch/riscv/include/asm/uaccess.h`。
- **arm64**：`arch/arm64/lib/uaccess_flushcache.c`
- **x86**：`arch/x86/lib/usercopy_64.c`
- **其他**：`ARCH_HAS_UACCESS_FLUSHCACHE`；`ARCH_HAS_PMEM_API`；`_copy_from_iter_flushcache()`；`copy_mc_to_kernel()`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/tree/arch/riscv/include/asm/cacheflush.h?id=bee763d5f341b99cf472afeb508d4988f62a6ca1)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/tree/arch/arm64/lib/uaccess_flushcache.c?id=bee763d5f341b99cf472afeb508d4988f62a6ca1)。

#### [MM-05：批量清除大 folio PTE accessed 位](03-mmu-memory-tlb.md#mm-05)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`mm/vmscan.c`；`include/linux/pgtable.h`
- **RISC-V**：`arch/riscv/include/asm/pgtable.h`
- **arm64**：`arch/arm64/include/asm/pgtable.h`；`arch/arm64/mm/contpte.c`
- **x86**：`arch/x86/mm/pgtable.c:ptep_test_and_clear_young()`；`arch/x86/include/asm/pgtable.h`
- **其他**：`test_and_clear_young_ptes()`；`test_and_clear_young_ptes_notify()`；`ptep_test_and_clear_young()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=9970a9a27ffca8b45c4a242f90adeb979fcaafb0)；[来源 2](https://lkml.kernel.org/r/7f891d42a720cc2e57862f3b79e4f774404f313c.1772778858.git.baolin.wang@linux.alibaba.com)。

#### [MM-06：实现 pte_needs_flush() 与 huge_pmd_needs_flush()](03-mmu-memory-tlb.md#mm-06)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`include/asm-generic/tlb.h`；`mm/mprotect.c`；`mm/huge_memory.c`
- **RISC-V**：`arch/riscv/include/asm/tlbflush.h`；`arch/riscv/include/asm/pgtable-bits.h`
- **arm64**：`arch/arm64/include/asm/tlbflush.h`
- **x86**：`arch/x86/include/asm/tlbflush.h`
- **其他**：`pte_needs_flush()`；`huge_pmd_needs_flush()`；`mprotect()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/tree/arch/x86/include/asm/tlbflush.h?id=bee763d5f341b99cf472afeb508d4988f62a6ca1)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/tree/arch/arm64/include/asm/tlbflush.h?id=bee763d5f341b99cf472afeb508d4988f62a6ca1)；[来源 3](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/tree/include/asm-generic/tlb.h?id=bee763d5f341b99cf472afeb508d4988f62a6ca1)。

#### [MM-07：实现原子 ptep_try_set()](03-mmu-memory-tlb.md#mm-07)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`include/linux/pgtable.h:ptep_try_set()`；`kernel/bpf/arena.c`
- **RISC-V**：`arch/riscv/include/asm/pgtable.h`。
- **arm64**：`arch/arm64/include/asm/pgtable.h`
- **x86**：`arch/x86/include/asm/pgtable.h`
- **其他**：`ptep_try_set()`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=258df8fce42fecc23cd04242de3d39f1fe836433)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=71385b78dbc290328e3b04ebd9b27786642afaca)。

#### [MM-08：PBMT set_memory 与 PFN-map 缓存类型一致性](03-mmu-memory-tlb.md#mm-08)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`set_memory_uc/wc/wb`；`include/linux/pgtable.h`
- **RISC-V**：`arch/riscv/mm/pageattr.c:__set_memory()`；`arch/riscv/include/asm/set_memory.h`；`arch/riscv/include/asm/pgtable.h:pgprot_{noncached,writecombine}`
- **x86**：`arch/x86/include/asm/set_memory.h`；`arch/x86/mm/pat/set_memory.c`
- **其他**：`set_memory_uc()`；`set_memory_wc()`；`set_memory_wb()`；`ioremap_wc()`；`pgprot_dmacoherent()`；`__ioremap_prot()`；`pfnmap_setup_cachemode()`；`pfnmap_track()`；`pfnmap_untrack()`。
- **来源**：[来源 1](https://lore.kernel.org/r/20250722091504.45974-2-cuiyunhui@bytedance.com)；[来源 2](https://lore.kernel.org/r/20250820152316.1012757-1-apatel@ventanamicro.com)；[来源 3](https://lore.kernel.org/linux-arm-kernel/20250917190323.3828347-2-yang@os.amperecomputing.com/)；[来源 4](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/tree/include/linux/pgtable.h?id=bee763d5f341b99cf472afeb508d4988f62a6ca1)；[来源 5](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/tree/arch/x86/mm/pat/memtype.c?id=bee763d5f341b99cf472afeb508d4988f62a6ca1)。

#### [MM-09：重合并 pageattr 碎片化的 direct-map 大页](03-mmu-memory-tlb.md#mm-09)

- **状态/原始架构**：unclaimed；x86。
- **generic/core**：`set_memory_ro/rw/x/nx`。
- **RISC-V**：`arch/riscv/mm/pageattr.c`
- **arm64**：`arch/arm64/mm/pageattr.c:change_memory_common()`
- **x86**：`arch/x86/mm/pat/set_memory.c`
- **其他**：`split_linear_mapping()`；`__split_linear_mapping_{pmd,pud,p4d}()`；`collapse_large_pages()`；`collapse_pmd_page()`；`collapse_pud_page()`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=41d88484c71cd4f659348da41b7b5b3dbd3be1f6)。

#### [MM-10：RISC-V memory hot-remove 叶子边界与安全释放](03-mmu-memory-tlb.md#mm-10)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`mm/memory_hotplug.c`
- **RISC-V**：`arch/riscv/mm/init.c`
- **arm64**：`arch/arm64/mm/mmu.c:addr_splits_kernel_leaf()`；`arch/arm64/mm/mmu.c`
- **x86**：`arch/x86/mm/init_64.c:remove_pagetable()`
- **其他**：`remove_pmd_mapping()`；`remove_pud_mapping()`；`remove_p4d_mapping()`；`arch_remove_memory()`；`__remove_pages()`；`CONFIG_DEBUG_VM`；`flush_tlb_all()`；`remove_{pte,pmd,pud,p4d,pgd}_mapping()`；`free_{pte,pmd,pud}_table()`；`pagetable_dtor()`；`pagetable_free()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=95a58852b0e5413b6ef4c93da60a80e89da9986a)；[来源 2](https://lore.kernel.org/all/aWZYXhrT6D2M-7-N@willie-the-truck/)；[来源 3](https://lkml.kernel.org/r/b89d77c965507b1b102cbabe988e69365cb288b6.1736317725.git.zhengqi.arch@bytedance.com)；[来源 4](https://lore.kernel.org/20260521032730.2104017-1-apopple@nvidia.com)。

#### [MM-11：memory hot-remove 范围 TLB 批处理](03-mmu-memory-tlb.md#mm-11)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`mm/memory_hotplug.c:remove_memory()`；`include/linux/memory_hotplug.h:arch_remove_memory()`
- **RISC-V**：`arch/riscv/mm/init.c:remove_pgd_mapping()`；`arch/riscv/mm/tlbflush.c`
- **x86**：`arch/x86/mm/init_64.c:remove_pagetable()`；`arch/x86/mm/tlb.c:flush_tlb_kernel_range()`
- **其他**：`remove_pgd_mapping()`；`arch_remove_memory()`；`arch_add_memory()`；`flush_tlb_kernel_range()`；`unmap_hotplug_range()`；`flush_tlb_all()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=ff4c5a0de1f2ef7737a8688a86e19301e567020d)；[来源 2](https://lore.kernel.org/linux-arm-kernel/20260309025725.455004-2-anshuman.khandual@arm.com/)。

#### [MM-12：通用化 hotplug 页表 teardown walker](03-mmu-memory-tlb.md#mm-12)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`mm/sparse-vmemmap.c`；`include/linux/mm.h`。
- **RISC-V**：`arch/riscv/mm/init.c`
- **arm64**：`arch/arm64/mm/mmu.c`
- **x86**：`arch/x86/mm/init_64.c`
- **其他**：`unmap_hotplug_range()`；`free_empty_tables()`
- **来源**：[来源 1](https://lore.kernel.org/20260601084845.3792171-4-songmuchun@bytedance.com)；[来源 2](https://lore.kernel.org/20260601084845.3792171-3-songmuchun@bytedance.com)；[来源 3](https://lkml.kernel.org/r/ea372633d94f4d3f9f56a7ec5994bf050bf77e39.1736317725.git.zhengqi.arch@bytedance.com)。

#### [MM-13：内核 data/BSS linear alias 只读化](03-mmu-memory-tlb.md#mm-13)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`include/linux/init.h:mark_rodata_ro()`；`mm/rodata_test.c`。
- **RISC-V**：`arch/riscv/mm/init.c:create_linear_mapping_page_table()`；`arch/riscv/include/asm/page.h:lm_alias()`
- **arm64**：`arch/arm64/mm/mmu.c`
- **x86**：`arch/x86/mm/init_64.c:mark_rodata_ro()`；`arch/x86/mm/pat/set_memory.c:set_memory_ro()`
- **其他**：`mark_rodata_ro()`；`create_kernel_page_table()`；`pgprot_from_va()`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=f2ba877402e5f74b27d9dbc2c8d059e7e9daf500)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=36fa5ffa60344bcc59fb3f50b33af8187e6b8753)；[来源 3](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=382a03e12ebad387fad616da78b99720ea3ee683)。

#### [MM-14：arm64/RISC-V versioned ASID allocator 公共核心](03-mmu-memory-tlb.md#mm-14)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`include/linux/mm_types.h:struct mm_struct::context`；`kernel/fork.c:mm_init()`。
- **RISC-V**：`arch/riscv/mm/context.c`
- **arm64**：`arch/arm64/mm/context.c`
- **其他**：`__flush_context()`；`__new_context()`；`flush_context()`；`new_context()`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/tree/arch/riscv/mm/context.c?id=bee763d5f341b99cf472afeb508d4988f62a6ca1)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/tree/arch/arm64/mm/context.c?id=bee763d5f341b99cf472afeb508d4988f62a6ca1)；[来源 3](https://lore.kernel.org/linux-arm-kernel/20260219113715.8001-1-redacherkaoui67@gmail.com/)。

#### [MM-15：基于 active hart 的本地/远程 TLB 选择](03-mmu-memory-tlb.md#mm-15)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`include/linux/mm_types.h:mm_cpumask()`；`kernel/cpu.c:clear_tasks_mm_cpumask()`
- **RISC-V**：`arch/riscv/mm/context.c:set_mm()`；`arch/riscv/mm/tlbflush.c:__flush_tlb_range()`
- **x86**：`arch/x86/mm/tlb.c`
- **其他**：`mm_cpumask()`；`mprotect()`。
- **来源**：[来源 1](https://lore.kernel.org/linux-arm-kernel/20260523134710.3827956-1-linu.cherian@arm.com/)。

#### [MM-16：统一 kernel mapping synchronization 模型](03-mmu-memory-tlb.md#mm-16)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`mm/vmalloc.c`；`mm/memory.c`
- **RISC-V**：`arch/riscv/mm/init.c:preallocate_pgd_pages_range()`；`arch/riscv/include/asm/cacheflush.h:mark_new_valid_map()`；`arch/riscv/mm/fault.c`
- **arm64**：`arch/arm64/mm/mmu.c`；`arch/arm64/include/asm/pgtable.h`
- **x86**：`arch/x86/mm/init_64.c:arch_sync_kernel_mappings()`
- **其他**：`ARCH_PAGE_TABLE_SYNC_MASK`；`arch_sync_kernel_mappings()`；`vmemmap_populate_finalize()`；`mark_new_valid_map()`；`HAVE_ARCH_HUGE_VMAP`；`HAVE_ARCH_HUGE_VMALLOC`；`arch_vmap_pmd_supported()`；`arch_vmap_pud_supported()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=6659d027998083fbb6d42a165b0c90dc2e8ba989)；[来源 2](https://lore.kernel.org/linux-mm/20250311114420.240341-1-gwan-gyeong.mun@intel.com)；[来源 3](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/tree/arch/riscv/include/asm/cacheflush.h?id=bee763d5f341b99cf472afeb508d4988f62a6ca1)；[来源 4](https://lore.kernel.org/linux-arm-kernel/20260527035607.14919-3-xueyuan.chen21@gmail.com/)；[来源 5](https://lore.kernel.org/r/20250722091504.45974-2-cuiyunhui@bytedance.com)。

### [IRQ/SMP/Time](04-irq-smp-time.md)

#### [IRQ-01：RISC-V IRQ 入口接入 runtime constant](04-irq-smp-time.md#irq-01)

- **状态/原始架构**：active RFC；arm64。
- **generic/core**：`kernel/irq/handle.c::{handle_arch_irq,set_handle_irq,generic_handle_arch_irq}`
- **RISC-V**：`arch/riscv/kernel/traps.c::do_irq`；`drivers/irqchip/irq-riscv-intc.c::{riscv_intc_irq,riscv_intc_aia_irq}`
- **arm64**：`arch/arm64/kernel/entry-common.c::{el0_interrupt,el1_interrupt}`
- **其他**：`do_irq()`；`CONFIG_DEBUG_ENTRY`。
- **来源**：[来源 1](https://lore.kernel.org/linux-arm-kernel/20260220090922.1506-3-jszhang@kernel.org/)；[来源 2](https://lore.kernel.org/linux-arm-kernel/20260220090922.1506-4-jszhang@kernel.org/)。

#### [IRQ-02：统一 root IRQ handler 注册与只读化](04-irq-smp-time.md#irq-02)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`kernel/irq/handle.c::{handle_arch_irq,set_handle_irq,generic_handle_arch_irq}`
- **RISC-V**：`arch/riscv/kernel/irq.c::init_IRQ`；`drivers/irqchip/irq-riscv-intc.c::riscv_intc_init_common`
- **arm64**：`arch/arm64/kernel/irq.c::{handle_arch_irq,set_handle_irq}`
- **其他**：`set_handle_irq()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/irq/handle.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [IRQ-03：通用 per-CPU IPI descriptor 生命周期与 tick broadcast](04-irq-smp-time.md#irq-03)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`kernel/irq/ipi.c`；`include/linux/irq.h`；`/proc/interrupts`；`include/linux/clockchips.h::tick_broadcast`；`kernel/time/tick-broadcast.c`
- **RISC-V**：`arch/riscv/kernel/smp.c::{ipi_desc,riscv_ipi_set_virq_range,riscv_ipi_enable,riscv_ipi_disable,show_ipi_stats,handle_IPI}`；`arch/riscv/kernel/smp.c::tick_broadcast`
- **arm64**：`arch/arm64/kernel/smp.c::{pcpu_ipi_desc,set_smp_ipi_range_percpu,ipi_setup,ipi_teardown,arch_show_interrupts,do_handle_IPI}`；`arch/arm64/kernel/smp.c::tick_broadcast`
- **其他**：`ARCH_HAS_TICK_BROADCAST`；`tick_broadcast()`。
- **来源**：[来源 1](https://lore.kernel.org/linux-arm-kernel/20250703-gicv5-host-v7-18-12e71f1b3528@kernel.org/)。

#### [IRQ-04：IMSIC Multi-MSI 分配与回滚](04-irq-smp-time.md#irq-04)

- **状态/原始架构**：unclaimed；arm64。
- **RISC-V**：`drivers/irqchip/irq-riscv-imsic-platform.c::imsic_irq_domain_alloc`；`drivers/irqchip/irq-riscv-imsic-state.c::{imsic_vector_alloc,imsic_vector_free}`。
- **来源**：[来源 1](https://lore.kernel.org/linux-arm-kernel/b906a38d443577de45923b335d80fc54c5638da0.1750860131.git.namcao@linutronix.de/)。

#### [IRQ-05：x86/IMSIC MSI vector move 公共状态机](04-irq-smp-time.md#irq-05)

- **状态/原始架构**：unclaimed；x86。
- **generic/core**：`kernel/irq/migration.c::{__irq_move_irq,irq_force_complete_move}`。
- **RISC-V**：`drivers/irqchip/irq-riscv-imsic-platform.c::{imsic_irq_set_affinity,imsic_irq_force_complete_move}`；`drivers/irqchip/irq-riscv-imsic-state.c::imsic_vector_move`
- **x86**：`arch/x86/kernel/apic/vector.c::{apic_force_complete_move,free_moved_vector,__vector_cleanup}`
- **来源**：[来源 1](https://lore.kernel.org/linux-arm-kernel/20250217085657.789309-9-apatel@ventanamicro.com/)；[来源 2](https://lore.kernel.org/linux-arm-kernel/20250217085657.789309-11-apatel@ventanamicro.com/)。

#### [IRQ-06：IMSIC remote sync 改用 hard irq_work](04-irq-smp-time.md#irq-06)

- **状态/原始架构**：unclaimed；shared。
- **generic/core**：`kernel/irq_work.c::{irq_work_queue_on,arch_irq_work_raise}`
- **RISC-V**：`drivers/irqchip/irq-riscv-imsic-state.c::{__imsic_remote_sync,__imsic_local_timer_start,imsic_local_timer_callback,imsic_local_sync_all}`；`arch/riscv/kernel/smp.c::arch_irq_work_raise`
- **其他**：`__imsic_remote_sync()`；`add_timer_on()`；`arch_irq_work_has_interrupt()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/irqchip/irq-riscv-imsic-state.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [IRQ-07：ACPI IRQ dependency 通用化测试后续](04-irq-smp-time.md#irq-07)

- **状态/原始架构**：next；shared。
- **generic/core**：`drivers/acpi/irq.c`；`drivers/acpi/riscv/irq.c`
- **RISC-V**：`drivers/irqchip/irq-riscv-intc.c::acpi_set_irq_model`。
- **来源**：[来源 1](https://lore.kernel.org/linux-arm-kernel/20260709-gic-v5-acpi-iwb-probe-deferral-v4-5-48dae790f871@kernel.org/)。

#### [IRQ-08：SBI HSM late-AP cleanup 与代际控制](04-irq-smp-time.md#irq-08)

- **状态/原始架构**：unclaimed；shared。
- **generic/core**：`kernel/cpu.c::{cpuhp_bp_sync_alive,arch_cpuhp_cleanup_kick_cpu}`
- **RISC-V**：`arch/riscv/kernel/smpboot.c::arch_cpuhp_kick_ap_alive`；`arch/riscv/kernel/cpu_ops_sbi.c::{boot_data,sbi_cpu_start,sbi_hsm_hart_get_status,sbi_cpu_is_stopped}`。
- **其他**：`arch_cpuhp_cleanup_kick_cpu()`
- **来源**：[来源 1](https://lore.kernel.org/linux-arm-kernel/20260624092537.2916971-13-ruanjinjie@huawei.com/)。

#### [IRQ-09：clockevent 补齐 oneshot-stopped 状态](04-irq-smp-time.md#irq-09)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`drivers/clocksource/timer-riscv.c::riscv_clock_event`；`drivers/clocksource/arm_arch_timer.c::__arch_timer_setup`；`kernel/time/tick-oneshot.c::tick_program_event`；`kernel/time/clockevents.c::__clockevents_switch_state`。
- **其他**：`riscv_clock_shutdown()`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/clocksource/timer-riscv.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [IRQ-10：RISC-V clocksource 稳定性测量与策略证明](04-irq-smp-time.md#irq-10)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`drivers/clocksource/timer-riscv.c::{riscv_clocksource,riscv_clocksource_rdtime}`；`kernel/time/clocksource.c`
- **x86**：`arch/x86/kernel/tsc.c`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/clocksource/timer-riscv.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

### [Core/ABI/Hardening](05-core-abi-observability-hardening.md)

#### [CORE-01：reliable unwinder 与 livepatch enablement](05-core-abi-observability-hardening.md#core-01)

- **状态/原始架构**：active RFC；x86+arm64。
- **generic/core**：`kernel/stacktrace.c::stack_trace_save_tsk_reliable()`；`include/linux/stacktrace.h`；`tools/testing/selftests/livepatch/`；`kernel/livepatch/transition.c::{klp_check_stack,klp_try_switch_task}`；`include/linux/livepatch.h::klp_have_reliable_stack()`
- **RISC-V**：`arch/riscv/kernel/stacktrace.c::{walk_stackframe,arch_stack_walk,arch_stack_walk_reliable}`；`arch/riscv/Kconfig`。
- **其他**：`HAVE_RELIABLE_STACKTRACE`；`HAVE_LIVEPATCH`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kernel/stacktrace.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/stacktrace.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 3](https://lists.infradead.org/pipermail/linux-riscv/2026-June/093484.html)；[来源 4](https://lists.infradead.org/pipermail/linux-riscv/2026-June/093489.html)；[来源 5](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/livepatch/transition.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [CORE-02：perf/ptrace/KGDB hardware breakpoints](05-core-abi-observability-hardening.md#core-02)

- **状态/原始架构**：active RFC；x86+arm64。
- **generic/core**：`kernel/events/hw_breakpoint.c`；`include/linux/hw_breakpoint.h`；`tools/testing/selftests/breakpoints/`。
- **RISC-V**：`arch/riscv/kernel/ptrace.c`；`arch/riscv/kernel/kgdb.c`
- **arm64**：`arch/arm64/kernel/hw_breakpoint.c`
- **x86**：`arch/x86/kernel/hw_breakpoint.c`
- **其他**：`HAVE_HW_BREAKPOINT`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/events/hw_breakpoint.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/kernel/hw_breakpoint.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 3](https://lists.infradead.org/pipermail/linux-riscv/2025-May/070170.html)。

#### [CORE-03：RISC-V static-call backend](05-core-abi-observability-hardening.md#core-03)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`kernel/static_call.c::static_call_update()`；`include/linux/static_call.h`
- **arm64**：`arch/arm64/include/asm/static_call.h`
- **x86**：`arch/x86/kernel/static_call.c`
- **其他**：`HAVE_STATIC_CALL`；`patch_text()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/static_call.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/x86/kernel/static_call.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 3](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/Kconfig?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [CORE-04：完整 ftrace_regs 与 CFI-compatible call-ops](05-core-abi-observability-hardening.md#core-04)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`include/linux/ftrace.h::{ftrace_get_regs,arch_ftrace_get_regs}`；`kernel/trace/ftrace.c`
- **RISC-V**：`arch/riscv/include/asm/ftrace.h::arch_ftrace_get_regs()`；`arch/riscv/Kconfig`；`arch/riscv/kernel/ftrace.c`；`arch/riscv/include/asm/ftrace.h`
- **x86**：`arch/x86/include/asm/ftrace.h`
- **其他**：`HAVE_DYNAMIC_FTRACE_WITH_REGS`；`arch_ftrace_get_regs()`；`HAVE_DYNAMIC_FTRACE_WITH_CALL_OPS`；`CONFIG_CFI_CLANG=y`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/include/asm/ftrace.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/linux/ftrace.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 3](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/x86/include/asm/ftrace.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 4](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/Kconfig?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 5](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kernel/ftrace.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [CORE-05：kprobes-on-ftrace 与 optprobes 加速链](05-core-abi-observability-hardening.md#core-05)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`kernel/kprobes.c::prepare_kprobe()`；`include/linux/kprobes.h::arch_prepare_kprobe_ftrace()`；`kernel/kprobes.c::{alloc_aggr_kprobe,arch_prepare_optimized_kprobe,optimize_kprobe}`；`include/linux/kprobes.h`
- **x86**：`arch/x86/kernel/kprobes/ftrace.c`；`arch/x86/kernel/kprobes/opt.c`。
- **其他**：`HAVE_KPROBES_ON_FTRACE`；`arch_prepare_kprobe_ftrace()`；`HAVE_OPTPROBES`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/kprobes.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/x86/kernel/kprobes/ftrace.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 3](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kernel/probes?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 4](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/x86/kernel/kprobes/opt.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [CORE-06：实现 arch_bpf_stack_walk()](05-core-abi-observability-hardening.md#core-06)

- **状态/原始架构**：active RFC；x86+arm64。
- **generic/core**：`kernel/bpf/core.c::arch_bpf_stack_walk()`；`kernel/bpf/{helpers.c,stream.c,core.c}`
- **RISC-V**：`arch/riscv/net/bpf_jit_comp64.c`。
- **其他**：`arch_bpf_stack_walk()`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/bpf/core.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://lists.infradead.org/pipermail/linux-riscv/2026-June/093432.html)；[来源 3](https://lists.infradead.org/pipermail/linux-riscv/2026-June/093433.html)。

#### [CORE-07：RISC-V BPF exceptions](05-core-abi-observability-hardening.md#core-07)

- **状态/原始架构**：active RFC；x86+arm64。
- **generic/core**：`kernel/bpf/core.c::bpf_jit_supports_exceptions()`；`kernel/bpf/verifier.c`；`tools/testing/selftests/bpf`。
- **RISC-V**：`arch/riscv/net/bpf_jit_comp64.c`
- **其他**：`bpf_jit_supports_exceptions()`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/bpf/verifier.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://lists.infradead.org/pipermail/linux-riscv/2026-June/093434.html)；[来源 3](https://lists.infradead.org/pipermail/linux-riscv/2026-June/093435.html)。

#### [CORE-08：BPF bpf2bpf 与 subprog tailcalls 混用](05-core-abi-observability-hardening.md#core-08)

- **状态/原始架构**：active RFC；x86+arm64。
- **generic/core**：`kernel/bpf/core.c::bpf_jit_supports_subprog_tailcalls()`；`kernel/bpf/verifier.c`
- **RISC-V**：`arch/riscv/net/bpf_jit_comp64.c`。
- **来源**：[来源 1](https://lists.infradead.org/pipermail/linux-riscv/2026-July/094209.html)；[来源 2](https://lists.infradead.org/pipermail/linux-riscv/2026-July/094208.html)；[来源 3](https://lists.infradead.org/pipermail/linux-riscv/2026-July/094212.html)；[来源 4](https://lists.infradead.org/pipermail/linux-riscv/2026-July/094206.html)。

#### [CORE-09：BPF stack arguments 与 private stack](05-core-abi-observability-hardening.md#core-09)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`kernel/bpf/core.c::bpf_jit_supports_stack_args()`；`kernel/bpf/verifier.c`；`kernel/bpf/btf.c`；`kernel/bpf/core.c::bpf_jit_supports_private_stack()`。
- **RISC-V**：`arch/riscv/net/bpf_jit_comp64.c`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/bpf/core.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/net/bpf_jit_comp64.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 3](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/net/bpf_jit_comp.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 4](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/bpf/verifier.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 5](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/x86/net/bpf_jit_comp.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [CORE-10：BPF timed may_goto](05-core-abi-observability-hardening.md#core-10)

- **状态/原始架构**：unclaimed；x86。
- **generic/core**：`kernel/bpf/core.c::bpf_jit_supports_timed_may_goto()`；`kernel/bpf/fixups.c`
- **RISC-V**：`arch/riscv/net/bpf_jit_comp64.c`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/bpf/fixups.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/bpf/core.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 3](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/net/bpf_jit_comp.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [CORE-11：BPF tail-call poke descriptor](05-core-abi-observability-hardening.md#core-11)

- **状态/原始架构**：unclaimed；x86。
- **generic/core**：`kernel/bpf/arraymap.c::bpf_arch_poke_desc_update()`
- **RISC-V**：`arch/riscv/net/bpf_jit_comp64.c`。
- **x86**：`arch/x86/net/bpf_jit_comp.c`
- **其他**：`bpf_arch_poke_desc_update()`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/bpf/arraymap.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/x86/net/bpf_jit_comp.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 3](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/net/bpf_jit_core.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [CORE-12：RISC-V KCSAN architecture enablement](05-core-abi-observability-hardening.md#core-12)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`lib/Kconfig.kcsan::{HAVE_ARCH_KCSAN,KCSAN}`；`kernel/kcsan/`
- **RISC-V**：`arch/riscv/include/asm/{atomic.h,cmpxchg.h,barrier.h}`。
- **其他**：`HAVE_ARCH_KCSAN`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/lib/Kconfig.kcsan?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/kcsan?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 3](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/include/asm/atomic.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [CORE-13：native acquire/release AMO variants](05-core-abi-observability-hardening.md#core-13)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`include/linux/atomic/atomic-arch-fallback.h`
- **RISC-V**：`arch/riscv/include/asm/atomic.h`；`arch/riscv/include/asm/cmpxchg.h`；`arch/riscv/include/asm/barrier.h`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/include/asm/atomic.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/linux/atomic/atomic-arch-fallback.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 3](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/include/asm/cmpxchg.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [CORE-14：选择 HAVE_CMPXCHG_LOCAL](05-core-abi-observability-hardening.md#core-14)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`mm/vmstat.c`；`lib/percpu_counter.c`
- **RISC-V**：`arch/riscv/include/asm/cmpxchg.h::arch_cmpxchg_local()`；`arch/riscv/Kconfig`。
- **其他**：`HAVE_CMPXCHG_LOCAL`；`arch_cmpxchg_local()`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/include/asm/cmpxchg.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/mm/vmstat.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 3](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/lib/percpu_counter.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [CORE-15：HAVE_CMPXCHG_DOUBLE 与 Zacas/fallback](05-core-abi-observability-hardening.md#core-15)

- **状态/原始架构**：active RFC；x86+arm64。
- **generic/core**：`mm/slub.c`
- **RISC-V**：`arch/riscv/include/asm/cmpxchg.h`；`arch/riscv/Kconfig`。
- **其他**：`HAVE_CMPXCHG_DOUBLE`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/mm/slub.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://lists.infradead.org/pipermail/linux-riscv/2025-March/068203.html)；[来源 3](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/include/asm/cmpxchg.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [CORE-16：实现 ARCH_HAS_EXECMEM_ROX](05-core-abi-observability-hardening.md#core-16)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`mm/execmem.c`；`include/linux/execmem.h`
- **RISC-V**：`arch/riscv/mm/pageattr.c`
- **其他**：`ARCH_HAS_EXECMEM_ROX`；`set_memory_*()`；`CONFIG_STRICT_MODULE_RWX`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/mm/execmem.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/mm/pageattr.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 3](https://lists.infradead.org/pipermail/linux-riscv/2026-July/093771.html)。

#### [CORE-17：默认启用 VMAP_STACK](05-core-abi-observability-hardening.md#core-17)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`init/Kconfig::VMAP_STACK`。
- **RISC-V**：`arch/riscv/Kconfig`；`arch/riscv/kernel/entry.S`；`arch/riscv/kernel/traps.c`；`arch/riscv/include/asm/thread_info.h`
- **其他**：`HAVE_ARCH_VMAP_STACK`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/Kconfig?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kernel/traps.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 3](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/init/Kconfig?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [CORE-18：实现 arch_within_stack_frames()](05-core-abi-observability-hardening.md#core-18)

- **状态/原始架构**：unclaimed；x86。
- **generic/core**：`mm/usercopy.c::check_stack_object()`；`include/linux/thread_info.h::arch_within_stack_frames()`
- **RISC-V**：`arch/riscv/include/asm/thread_info.h`。
- **x86**：`arch/x86/include/asm/thread_info.h`
- **其他**：`arch_within_stack_frames()`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/mm/usercopy.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/linux/thread_info.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 3](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/x86/include/asm/thread_info.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

### [Platform/ACPI/RAS](06-platform-acpi-numa-power-ras.md)

#### [PLAT-01：RISC-V ACPI CPU physical hotplug](06-platform-acpi-numa-power-ras.md#plat-01)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`drivers/acpi/acpi_processor.c::acpi_processor_make_present()`；`drivers/acpi/acpi_processor.c::acpi_processor_make_not_present()`；`drivers/acpi/acpi_processor.c`；`kernel/cpu.c`；`arch_register_cpu()/arch_unregister_cpu()`。
- **RISC-V**：`arch/riscv/kernel/acpi.c`；`arch/riscv/kernel/smpboot.c::{acpi_parse_rintc,acpi_parse_and_init_cpus,setup_smp}`
- **arm64**：`arch/arm64/kernel/acpi.c::acpi_map_cpu()`；`arch/arm64/kernel/acpi.c::acpi_unmap_cpu()`；`arch/arm64/Kconfig::ACPI_HOTPLUG_CPU`；`arch/arm64/kernel/smp.c::{arch_register_cpu,arch_unregister_cpu,acpi_cpu_is_present}`
- **x86**：`arch/x86/Kconfig::ACPI_HOTPLUG_CPU`
- **其他**：`acpi_map_cpu()`；`acpi_unmap_cpu()`；`acpi_get_cpu_uid()`
- **来源**：[来源 1](https://lore.kernel.org/r/20240529133446.28446-18-Jonathan.Cameron@huawei.com)；[来源 2](https://patch.msgid.link/20260401081640.26875-4-fengchengwen@huawei.com)。

#### [PLAT-02：SRAT Generic Initiator 与 _OSC 能力接线](06-platform-acpi-numa-power-ras.md#plat-02)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`drivers/acpi/numa/srat.c::acpi_parse_gi_affinity()`；`drivers/acpi/numa/srat.c::acpi_parse_srat()`；`/sys/devices/system/node/`；`drivers/acpi/numa/srat.c:532-566`
- **其他**：`acpi_map_pxm_to_node()`；`CONFIG_X86 || CONFIG_ARM64`。
- **来源**：[来源 1](https://patch.msgid.link/20250913023224.39281-1-xueshuai@linux.alibaba.com)。

#### [PLAT-03：arm64/RISC-V ACPI NUMA 后端通用化](06-platform-acpi-numa-power-ras.md#plat-03)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`drivers/acpi/numa/srat.c`
- **RISC-V**：`arch/riscv/kernel/acpi_numa.c::acpi_numa_rintc_affinity_init()`；`arch/riscv/kernel/acpi_numa.c`。
- **arm64**：`arch/arm64/kernel/acpi_numa.c::acpi_numa_gicc_affinity_init()`；`arch/arm64/kernel/acpi_numa.c`
- **其他**：`acpi_map_cpus_to_nodes()`；`set_cpu_numa_node()`
- **来源**：[来源 1](https://patch.msgid.link/20260401081640.26875-4-fengchengwen@huawei.com)。

#### [PLAT-04：PSCI/SBI DT idle genpd 生命周期通用化](06-platform-acpi-numa-power-ras.md#plat-04)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`drivers/cpuidle/cpuidle-riscv-sbi.c::sbi_pd_init()`；`drivers/cpuidle/cpuidle-riscv-sbi.c::sbi_genpd_probe()`；`drivers/cpuidle/cpuidle-psci-domain.c::psci_pd_init()`；`drivers/cpuidle/cpuidle-psci-domain.c::psci_cpuidle_domain_probe()`；`drivers/cpuidle/dt_idle_genpd.c::dt_idle_pd_init_topology()`
- **其他**：`of_genpd_add_provider_simple()`；`pm_genpd_add_subdomain()`。
- **来源**：[来源 1](https://lore.kernel.org/r/20250701114733.636510-25-ulf.hansson@linaro.org)。

#### [PLAT-05：arm64/RISC-V ACPI FFH LPI 验证框架](06-platform-acpi-numa-power-ras.md#plat-05)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`drivers/acpi/arm64/cpuidle.c::acpi_processor_ffh_lpi_probe()`；`drivers/acpi/arm64/cpuidle.c::acpi_processor_ffh_lpi_enter()`；`drivers/acpi/riscv/cpuidle.c::acpi_processor_ffh_lpi_probe()`；`drivers/acpi/riscv/cpuidle.c::acpi_processor_ffh_lpi_enter()`；`drivers/acpi/processor_idle.c`。
- **来源**：[来源 1](https://patch.msgid.link/20260616072617.2272-1-lirongqing@baidu.com)。

#### [PLAT-06：CPPC FIE IRQ-off 读取与 RV32 READ_HI](06-platform-acpi-numa-power-ras.md#plat-06)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`drivers/acpi/riscv/cppc.c::cpc_read_ffh()`；`drivers/acpi/riscv/cppc.c::cpc_write_ffh()`；`drivers/cpufreq/cppc_cpufreq.c::cppc_scale_freq_tick()`；`drivers/acpi/cppc_acpi.c::cppc_get_perf_ctrs()`；`drivers/acpi/riscv/cppc.c::SBI_CPPC_READ`；`drivers/acpi/riscv/cppc.c::SBI_CPPC_READ_HI`
- **其他**：`CONFIG_32BIT`。
- **来源**：[来源 1](https://lore.kernel.org/r/20250818143600.894385-2-apatel@ventanamicro.com)。

#### [PLAT-07：CPPC artificial Energy Model 通用化](06-platform-acpi-numa-power-ras.md#plat-07)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`drivers/cpufreq/cppc_cpufreq.c::cppc_cpufreq_register_em()`；`drivers/cpufreq/cppc_cpufreq.c`
- **其他**：`struct acpi_processor::efficiency_class`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/cpufreq/cppc_cpufreq.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [PLAT-08：EFI runtime exception recovery 与恢复栈](06-platform-acpi-numa-power-ras.md#plat-08)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`drivers/firmware/efi/riscv-runtime.c`。
- **RISC-V**：`arch/riscv/kernel/efi.c`
- **arm64**：`arch/arm64/kernel/efi.c::efi_runtime_fixup_exception()`；`arch/arm64/kernel/efi.c::efi_rt_stack_top`；`arch/arm64/kernel/efi-rt-wrapper.S::__efi_rt_asm_recover`；`arch/arm64/mm/fault.c`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/kernel/efi.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [PLAT-09：EFI capsule cache-maintenance 通用 hook](06-platform-acpi-numa-power-ras.md#plat-09)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`drivers/firmware/efi/capsule.c::efi_capsule_update_locked()`
- **RISC-V**：`arch/riscv/include/asm/efi.h`。
- **arm64**：`arch/arm64/include/asm/efi.h::efi_capsule_flush_cache_range()`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/firmware/efi/capsule.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [PLAT-10：RISC-V crash hotplug 动态 elfcorehdr](06-platform-acpi-numa-power-ras.md#plat-10)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`kernel/crash_core.c::crash_prepare_headers()`；`/proc/iomem`。
- **RISC-V**：`arch/riscv/kernel/machine_kexec_file.c::arch_get_system_nr_ranges()`；`arch/riscv/kernel/machine_kexec_file.c::arch_crash_populate_cmem()`
- **其他**：`ARCH_SUPPORTS_CRASH_HOTPLUG`；`arch_crash_hotplug_support()`；`arch_crash_handle_hotplug_event()`
- **来源**：[来源 1](https://patch.msgid.link/20260629094746.191843-4-ruanjinjie@huawei.com)；[来源 2](https://patch.msgid.link/20260629094746.191843-7-ruanjinjie@huawei.com)。

#### [PLAT-11：RISC-V APEI/GHES 基础与映射属性](06-platform-acpi-numa-power-ras.md#plat-11)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`drivers/acpi/apei/ghes.c::ghes_map()`；`drivers/acpi/apei/Kconfig::HAVE_ACPI_APEI`
- **RISC-V**：`arch/riscv/Kconfig`；`arch/riscv/include/asm/acpi.h`
- **arm64**：`arch/arm64/Kconfig::HAVE_ACPI_APEI`；`arch/arm64/include/asm/acpi.h::arch_apei_get_mem_attribute()`
- **其他**：`HAVE_ACPI_APEI`；`__acpi_get_mem_attribute()`；`arch_apei_get_mem_attribute()`；`HAVE_ACPI_APEI if (ACPI && EFI)`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/Kconfig?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [PLAT-12：GHES memory failure/EDAC 与 Generic Processor CPER](06-platform-acpi-numa-power-ras.md#plat-12)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`drivers/acpi/apei/ghes.c::ghes_handle_memory_failure()`；`drivers/edac/ghes_edac.c::ghes_edac_register()`；`drivers/acpi/apei/Kconfig::ACPI_APEI_MEMORY_FAILURE`；`drivers/firmware/efi/cper.c::cper_estatus_print_section()`；`drivers/acpi/apei/ghes.c::ghes_do_proc()`；`include/ras/ras_event.h`
- **其他**：`CONFIG_MEMORY_FAILURE`；`memory_failure()`；`HAVE_ACPI_APEI`；`ghes_do_proc()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/acpi/apei/ghes.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [PLAT-13：RISC-V ACPI memory hotplug 启用与系统测试](06-platform-acpi-numa-power-ras.md#plat-13)

- **状态/原始架构**：unclaimed；x86+arm64。
- **RISC-V**：`arch/riscv/mm/init.c::arch_add_memory()`；`arch/riscv/mm/init.c::arch_remove_memory()`；`arch/riscv/mm/init.c::vmemmap_populate()`；`arch/riscv/mm/init.c::vmemmap_free()`；`arch/riscv/configs/defconfig`
- **其他**：`vmemmap_populate_finalize()`；`CONFIG_MEMORY_HOTPLUG`；`CONFIG_MEMORY_HOTREMOVE`；`CONFIG_ACPI_HOTPLUG_MEMORY`。
- **来源**：[来源 1](https://lore.kernel.org/20260630-mark-after-vmemmap-populate-v4-1-febbc15da028@iscas.ac.cn)。

### [KVM/IOMMU](07-kvm-iommu-virtualization.md)

#### [VIRT-01：KVM G-stage 与 RISC-V IOMMU ptdump 可观测性](07-kvm-iommu-virtualization.md#virt-01)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`drivers/iommu/iommu-debugfs.c`
- **RISC-V**：`arch/riscv/kvm/gstage.c`；`arch/riscv/kvm/Kconfig`；`arch/riscv/kvm/Makefile`；`drivers/iommu/riscv/iommu.c`
- **arm64**：`arch/arm64/kvm/ptdump.c`
- **其他**：`kvm_riscv_gstage_get_leaf()`；`ARCH_HAS_PTDUMP`；`pt_iommu_riscv_64_hw_info()`；`iommu_iova_to_phys()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kvm/gstage.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/kvm/ptdump.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 3](https://lore.kernel.org/linux-arm-kernel/20250407053113.746295-2-anshuman.khandual@arm.com/)；[来源 4](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/iommu-debugfs.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 5](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/riscv/iommu.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [VIRT-02：G-stage 脱锁销毁与可调度化](07-kvm-iommu-virtualization.md#virt-02)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`pgd/pgd_phys/levels`。
- **RISC-V**：`arch/riscv/kvm/mmu.c:kvm_riscv_mmu_free_pgd()`；`arch/riscv/kvm/gstage.c:kvm_riscv_gstage_op_pte()`
- **其他**：`kvm_riscv_mmu_free_pgd()`；`kvm_riscv_gstage_unmap_range()`；`cond_resched()`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kvm/mmu.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n676)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kvm/gstage.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n359)；[来源 3](https://patchwork.kernel.org/project/kvm/patch/20251113052452.975081-4-rananta@google.com/)。

#### [VIRT-03：guest_memfd shared/mappable 第一阶段](07-kvm-iommu-virtualization.md#virt-03)

- **状态/原始架构**：unclaimed；x86+arm64。
- **RISC-V**：`arch/riscv/kvm/Kconfig:config KVM`；`arch/riscv/kvm/mmu.c:kvm_riscv_mmu_map()`
- **arm64**：`arch/arm64/kvm/mmu.c:gmem_abort()`
- **其他**：`kvm_arch_prepare_memory_region()`；`kvm_gmem_get_pfn()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kvm/Kconfig?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/kvm/mmu.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n1606)；[来源 3](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/virt/kvm/guest_memfd.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 4](https://patchwork.kernel.org/project/kvm/patch/20250729225455.670324-19-seanjc@google.com/)；[来源 5](https://patchwork.kernel.org/project/kvm/patch/20250729225455.670324-21-seanjc@google.com/)。

#### [VIRT-04：实现 KVM_PRE_FAULT_MEMORY](07-kvm-iommu-virtualization.md#virt-04)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`include/linux/kvm_host.h:kvm_arch_vcpu_pre_fault_memory()`；`virt/kvm/kvm_main.c`
- **RISC-V**：`arch/riscv/kvm/mmu.c:kvm_arch_vcpu_pre_fault_memory()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/virt/kvm/kvm_main.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n4333)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/x86/kvm/mmu/mmu.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n5015)；[来源 3](https://patchwork.kernel.org/project/kvm/patch/20260612162354.73378-3-jackabt.amazon@gmail.com/)；[来源 4](https://patchwork.kernel.org/project/kvm/patch/20260612162354.73378-4-jackabt.amazon@gmail.com/)。

#### [VIRT-05：RISC-V KVM userfault exits](07-kvm-iommu-virtualization.md#virt-05)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`include/linux/kvm_host.h:kvm_prepare_memory_fault_exit()`
- **RISC-V**：`arch/riscv/kvm/mmu.c:kvm_riscv_mmu_map()`。
- **其他**：`kvm_prepare_memory_fault_exit()`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/linux/kvm_host.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n2513)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kvm/mmu.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n478)；[来源 3](https://patchwork.kernel.org/project/kvm/patch/20250618042424.330664-7-jthoughton@google.com/)。

#### [VIRT-06：启用 KVM_VFIO 并定义 coherency 语义](07-kvm-iommu-virtualization.md#virt-06)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`virt/kvm/vfio.c`；`virt/kvm/vfio.c:kvm_vfio_file_add()`
- **RISC-V**：`arch/riscv/kvm/Kconfig`
- **其他**：`kvm_vfio_update_coherency()`；`kvm_arch_register_noncoherent_dma()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/virt/kvm/vfio.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kvm/Kconfig?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 3](https://patchwork.kernel.org/project/kvm/patch/20250611224604.313496-55-seanjc@google.com/)。

#### [VIRT-07：IMSIC irq-bypass/direct-injection 生命周期与测试](07-kvm-iommu-virtualization.md#virt-07)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`virt/kvm/eventfd.c:kvm_arch_irq_bypass_*()`；`tools/testing/selftests/kvm/riscv/aia_*_test.c`；`kernel/irq/manage.c::irq_set_vcpu_affinity`；`include/linux/irq.h::irq_chip::irq_set_vcpu_affinity`；`drivers/irqchip/irq-gic-v3-its.c::its_irq_set_vcpu_affinity`
- **RISC-V**：`arch/riscv/kvm/aia_imsic.c:kvm_riscv_vcpu_aia_imsic_update()`；`drivers/irqchip/irq-riscv-imsic-platform.c::imsic_irq_base_chip`
- **x86**：`arch/x86/kvm/{vmx/posted_intr.c,svm/avic.c}`。
- **其他**：`HAVE_KVM_IRQ_BYPASS`；`kvm_riscv_vcpu_aia_imsic_release()`；`kvm_irqfd()`；`irq_set_vcpu_affinity()`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kvm/aia_imsic.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n742)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/virt/kvm/eventfd.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n351)；[来源 3](https://patchwork.kernel.org/project/kvm/patch/20250516230734.2564775-4-seanjc@google.com/)；[来源 4](https://patchwork.kernel.org/project/kvm/patch/20260623081433.21250-1-leixiang@kylinos.cn/)；[来源 5](https://patchwork.kernel.org/project/kvm/patch/20260622075103.35164-1-leixiang@kylinos.cn/)。

#### [VIRT-08：RISC-V IOMMU MSI page table/MRIF 与 AIA/VFIO](07-kvm-iommu-virtualization.md#virt-08)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`msiptp/msi_addr_mask/msi_addr_pattern`。
- **RISC-V**：`drivers/iommu/riscv/iommu-bits.h:struct riscv_iommu_msipte`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/riscv/iommu-bits.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n682)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kvm/aia_imsic.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 3](https://patchwork.kernel.org/project/kvm/patch/20250611224604.313496-5-seanjc@google.com/)；[来源 4](https://patchwork.kernel.org/project/kvm/patch/20251120140305.63515-13-mdittgen@amazon.de/)。

#### [VIRT-09：IOMMU fault queue、PRI/IOPF 与 page response](07-kvm-iommu-virtualization.md#virt-09)

- **状态/原始架构**：unclaimed；shared。
- **RISC-V**：`drivers/iommu/riscv/iommu.c:riscv_iommu_fault()`；`drivers/iommu/riscv/iommu-bits.h:struct riscv_iommu_pq_record`
- **其他**：`riscv_iommu_fault()`；`riscv_iommu_fltq_process()`；`report_iommu_fault()`；`iommu_report_device_fault()`；`iopf_group_response()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/riscv/iommu.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n520)；[来源 2](https://lore.kernel.org/linux-arm-kernel/3-v3-e5d08e2d551e+109-iommu_set_fault_jgg@nvidia.com/)；[来源 3](https://lore.kernel.org/linux-arm-kernel/745da1a819eb943f2519e660c8bcfde715885c6c.1779161849.git.nicolinc@nvidia.com/)；[来源 4](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/riscv/iommu-bits.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n655)；[来源 5](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/io-pgfault.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [VIRT-10：SVA、PASID 与 process-directory table](07-kvm-iommu-virtualization.md#virt-10)

- **状态/原始架构**：unclaimed；arm64。
- **RISC-V**：`drivers/iommu/riscv/iommu.c:riscv_iommu_ops`
- **其他**：`iommu_sva_bind_device()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/riscv/iommu.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n1484)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/riscv/iommu-bits.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n386)；[来源 3](https://lore.kernel.org/linux-arm-kernel/20260520150743.727106-1-joonwonkang@google.com/)。

#### [VIRT-11：IOMMUFD hw_info、nested HWPT 与 VMID/GSCID 协调](07-kvm-iommu-virtualization.md#virt-11)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`include/uapi/linux/iommufd.h`
- **RISC-V**：`drivers/iommu/riscv/iommu.c:riscv_iommu_ops`；`arch/riscv/kvm/vmid.c`；`arch/riscv/kvm/mmu.c:kvm_riscv_mmu_update_hgatp()`。
- **其他**：`pt_iommu_riscv_64_hw_info()`；`riscv_iommu_iodir_iotinval()`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/riscv/iommu.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n1289)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/uapi/linux/iommufd.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 3](https://lore.kernel.org/linux-arm-kernel/dab4ace747deb46c1fe70a5c663307f46990ae56.1752126748.git.nicolinc@nvidia.com/)；[来源 4](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/riscv/iommu-bits.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n311)；[来源 5](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/iommufd/hw_pagetable.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n238)。

#### [VIRT-12：基于 AMO_HWAD 的 DMA dirty tracking](07-kvm-iommu-virtualization.md#virt-12)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`drivers/iommu/generic_pt/fmt/riscv.h`
- **RISC-V**：`drivers/iommu/riscv/iommu.c:riscv_iommu_alloc_paging_domain()`。
- **其他**：`pt_entry_is_write_dirty()`；`pt_entry_make_write_dirty()`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/riscv/iommu-bits.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n55)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/generic_pt/iommu_pt.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n237)；[来源 3](https://lore.kernel.org/linux-arm-kernel/20260629111820.1873540-8-leo.bras@arm.com/)。

#### [VIRT-13：RISC-V vIOMMU、vEVENTQ 与 HW queue](07-kvm-iommu-virtualization.md#virt-13)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`drivers/iommu/iommufd/viommu.c`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/iommufd/viommu.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/iommufd/eventq.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 3](https://lore.kernel.org/linux-arm-kernel/dab4ace747deb46c1fe70a5c663307f46990ae56.1752126748.git.nicolinc@nvidia.com/)。

#### [VIRT-14：nested KVM architectural state 与 shadow G-stage](07-kvm-iommu-virtualization.md#virt-14)

- **状态/原始架构**：unclaimed；arm64。
- **RISC-V**：`arch/riscv/kvm/vcpu_config.c`；`arch/riscv/kvm/gstage.c`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kvm/vcpu_config.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/kvm/nested.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 3](https://lore.kernel.org/linux-arm-kernel/20250512105251.577874-4-gankulkarni@os.amperecomputing.com/)；[来源 4](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kvm/gstage.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 5](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/kvm/nested.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n1287)。

#### [VIRT-15：CoVE private memory、guest_memfd 与 memory attributes](07-kvm-iommu-virtualization.md#virt-15)

- **状态/原始架构**：unclaimed；arm64。
- **RISC-V**：`arch/riscv/kvm/Kconfig`
- **其他**：`HAVE_KVM_ARCH_GMEM_*`；`kvm_arch_post_set_memory_attributes()`；`kvm_arch_gmem_prepare()`；`kvm_gmem_populate()`；`kvm_arch_gmem_invalidate()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/virt/kvm/kvm_main.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n2421)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/linux/kvm_host.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n2536)；[来源 3](https://patchwork.kernel.org/project/kvm/patch/20260513131757.116630-26-steven.price@arm.com/)；[来源 4](https://lore.kernel.org/linux-arm-kernel/20250213161426.102987-2-steven.price@arm.com/)。

### [Genericization](08-genericization-opportunities.md)

#### [GEN-01：runtime-const 公共迭代器](08-genericization-opportunities.md#gen-01)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`include/asm-generic/runtime-const.h`。
- **RISC-V**：`arch/riscv/include/asm/runtime-const.h:160-270`
- **arm64**：`arch/arm64/include/asm/runtime-const.h:38-90`
- **x86**：`arch/x86/include/asm/runtime-const.h:44-75`
- **其他**：`runtime_const_init()`；`runtime_const_fixup()`；`runtime_const_ptr()`；`runtime_const_shift_right_32()`；`__runtime_fixup_{ptr,shift}()`
- **来源**：[来源 1](https://lore.kernel.org/linux-arm-kernel/178366995930.1208691.2993932866462893112.b4-review@b4/)。

#### [GEN-02：通用 register-offset table walker](08-genericization-opportunities.md#gen-02)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`regs_query_register_offset/name()`；`kernel/ptrace.c`；`include/linux/ptrace.h`
- **RISC-V**：`arch/riscv/kernel/ptrace.c:496`；`arch/riscv/kernel/ptrace.c::{regs_query_register_offset,regs_query_register_name}`
- **arm64**：`arch/arm64/kernel/ptrace.c:104`
- **x86**：`arch/x86/kernel/ptrace.c:125`
- **其他**：`regs_query_register_offset_from_table()`；`regs_query_register_name_from_table()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/ptrace.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kernel/ptrace.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 3](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/kernel/ptrace.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 4](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/x86/kernel/ptrace.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [GEN-03：复用现有 perf_get_regs_user() generic fallback](08-genericization-opportunities.md#gen-03)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`include/linux/perf_regs.h`
- **RISC-V**：`arch/riscv/kernel/perf_regs.c:38`；`arch/riscv/kernel/perf_regs.c::perf_get_regs_user()`
- **arm64**：`arch/arm64/kernel/perf_regs.c:101`；`arch/arm64/kernel/perf_regs.c::perf_get_regs_user()`
- **x86**：`arch/x86/kernel/perf_regs.c:103`；`arch/x86/kernel/perf_regs.c`。
- **其他**：`perf_get_regs_user()`；`ARCH_PERF_REGS_NEEDS_NMI_COPY`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/linux/perf_regs.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kernel/perf_regs.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 3](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/kernel/perf_regs.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [GEN-04：生成式复用 ptdump 层级 callback](08-genericization-opportunities.md#gen-04)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`note_page_pte/pmd/pud/p4d/pgd/flush`；`include/linux/ptdump.h`；`debugfs/kernel_page_tables`
- **RISC-V**：`arch/riscv/mm/ptdump.c:321`
- **arm64**：`arch/arm64/mm/ptdump.c:254`
- **x86**：`arch/x86/mm/dump_pagetables.c:391`
- **其他**：`CONFIG_DEBUG_WX`。
- **来源**：[来源 1](https://lore.kernel.org/linux-arm-kernel/20260630121005.1130996-7-weilin.chang@arm.com/)。

#### [GEN-05：ACPI early table map/unmap 默认实现](08-genericization-opportunities.md#gen-05)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`map/size`；`drivers/acpi/osl.c`；`include/linux/acpi.h`
- **RISC-V**：`arch/riscv/kernel/acpi.c:219`
- **arm64**：`arch/arm64/kernel/acpi.c:102`
- **x86**：`arch/x86/kernel/acpi/boot.c:121`
- **其他**：`early_memunmap()`；`__acpi_unmap_table()`；`early_memremap()`；`__acpi_map_table()`；`ARCH_ACPI_TABLE_PHYS_ZERO_INVALID`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/acpi/osl.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kernel/acpi.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [GEN-06：下沉 raw_pci_read/write() 通用 bus lookup](08-genericization-opportunities.md#gen-06)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`raw_pci_read/write()`；`drivers/pci/access.c`；`pci_generic_raw_read/write()`。
- **RISC-V**：`arch/riscv/kernel/acpi.c:319,329`
- **arm64**：`arch/arm64/kernel/pci.c:14,24`
- **x86**：`arch/x86/pci/common.c`
- **其他**：`pci_find_bus()`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/pci/access.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [GEN-07：PCI topology opt-in dev_to_node helper](08-genericization-opportunities.md#gen-07)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`include/asm-generic/topology.h`
- **RISC-V**：`arch/riscv/include/asm/pci.h:19`
- **arm64**：`arch/arm64/kernel/pci.c:36`
- **其他**：`dev_to_node()`；`CONFIG_NUMA`；`__pcibus_to_node()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/asm-generic/topology.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [GEN-08：统一 no-steal-acc 参数与策略所有权](08-genericization-opportunities.md#gen-08)

- **状态/原始架构**：unclaimed；x86。
- **generic/core**：`kernel/sched/cputime.c`
- **RISC-V**：`arch/riscv/kernel/paravirt.c:27`
- **arm64**：`arch/arm64/kernel/paravirt.c:35`
- **x86**：`arch/x86/kernel/kvm.c:65`；`arch/x86/kernel/cpu/vmware.c:159`
- **其他**：`paravirt_steal_accounting_enabled()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kernel/paravirt.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [GEN-09：提供 copy_oldmem_page() generic default](08-genericization-opportunities.md#gen-09)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`include/linux/crash_dump.h`；`fs/proc/vmcore.c`
- **RISC-V**：`arch/riscv/kernel/crash_dump.c:12`
- **arm64**：`arch/arm64/kernel/crash_dump.c:15`
- **其他**：`copy_oldmem_page()`；`copy_to_iter()`；`memunmap()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/linux/crash_dump.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [GEN-10：crash/kdump 默认 RAM walk hooks 与解析 wrapper](08-genericization-opportunities.md#gen-10)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`kernel/crash_reserve.c`；`kernel/kexec_file.c`
- **RISC-V**：`arch/riscv/kernel/machine_kexec_file.c:40,48`；`arch/riscv/mm/init.c:1321`
- **arm64**：`arch/arm64/mm/init.c:97`
- **x86**：`arch/x86/kernel/crash.c:150,227`
- **其他**：`get_nr_ram_ranges_callback()`；`prepare_elf64_ram_headers_callback()`；`crash_count_system_ram_ranges()`；`crash_collect_system_ram_ranges()`；`parse_crashkernel()`；`reserve_crashkernel_generic()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=5beabef0cffa)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=7b078a0aa275)；[来源 3](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/crash_core.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [GEN-11：ftrace call-ops 选择 helper](08-genericization-opportunities.md#gen-11)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`kernel/trace/ftrace.c`；`include/linux/ftrace.h`
- **RISC-V**：`arch/riscv/kernel/ftrace.c:81`
- **arm64**：`arch/arm64/kernel/ftrace.c:353`
- **其他**：`arm64_rec_get_ops()`；`riscv64_rec_get_ops()`；`ftrace_find_unique_ops()`；`ftrace_rec_set_ops()`；`ftrace_rec_get_call_ops()`。
- **来源**：[来源 1](https://lore.kernel.org/linux-arm-kernel/20260609-arm64-ftrace-direct-calls-v1-2-4a46f266697f@linux.dev/)。

#### [GEN-12：LZO 快路径改用高效非对齐能力](08-genericization-opportunities.md#gen-12)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`lib/lzo/lzodefs.h:24-39`
- **其他**：`CONFIG_HAVE_EFFICIENT_UNALIGNED_ACCESS`；`HAVE_FAST_UNALIGNED_64BIT_ACCESS`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/lib/lzo/lzo1x_compress.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [GEN-13：机械下沉 cacheinfo ci_leaf_init()](08-genericization-opportunities.md#gen-13)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`include/linux/cacheinfo.h:151`；`drivers/base/cacheinfo.c`；`include/linux/cacheinfo.h`
- **RISC-V**：`arch/riscv/kernel/cacheinfo.c:67`
- **arm64**：`arch/arm64/kernel/cacheinfo.c:34`
- **其他**：`ci_leaf_init()`；`CONFIG_ARM64 || CONFIG_ARM`；`use_arch_cache_info()`；`cacheinfo_init_leaf()`；`ARCH_USE_ARCH_CACHE_INFO`。
- **来源**：[来源 1](https://lore.kernel.org/linux-arm-kernel/20251119122305.302149-6-ben.horgan@arm.com/)。

#### [GEN-14：用 GENERIC_ARCH_TOPOLOGY 替换架构名判断](08-genericization-opportunities.md#gen-14)

- **状态/原始架构**：dormant；arm64。
- **generic/core**：`drivers/base/arch_topology.c:466`
- **其他**：`CONFIG_ARM64 || CONFIG_RISCV`；`ARCH_HAS_GENERIC_CPU_TOPOLOGY_MAP`；`arch_cpu_is_threaded()`。
- **来源**：[来源 1](https://lore.kernel.org/linux-arm-kernel/20250923015409.15983-2-cuiyunhui@bytedance.com/)。

#### [GEN-15：PCI ACPI host 使用现有能力组合门控](08-genericization-opportunities.md#gen-15)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`drivers/pci/pci-acpi.c:1538`
- **其他**：`CONFIG_ARM64 || CONFIG_RISCV`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/acpi/pci_root.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [GEN-16：显式 opt-in 的 no-immediate-flush young-bit helper](08-genericization-opportunities.md#gen-16)

- **状态/原始架构**：unclaimed；arm64。
- **generic/core**：`mm/pgtable-generic.c`
- **RISC-V**：`arch/riscv/include/asm/pgtable.h:693`
- **x86**：`arch/x86/mm/pgtable.c:475`
- **其他**：`ptep_clear_flush_young()`；`ptep_test_and_clear_young()`；`ptep_clear_young_no_flush()`。
- **来源**：[来源 1](https://lore.kernel.org/linux-arm-kernel/24af5144b96103631594501f77d4525f2475c1be.1774075004.git.baolin.wang@linux.alibaba.com/)。

#### [GEN-17：向下增长栈 uretprobe 存活 helper](08-genericization-opportunities.md#gen-17)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`kernel/events/uprobes.c`
- **RISC-V**：`arch/riscv/kernel/probes/uprobes.c:120`
- **arm64**：`arch/arm64/kernel/probes/uprobes.c:139`
- **其他**：`arch_uretprobe_is_alive()`；`uretprobe_is_alive_stack_grows_down()`。
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/trace/trace_uprobe.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

#### [GEN-18：参数化 syscall trace symbol matcher](08-genericization-opportunities.md#gen-18)

- **状态/原始架构**：unclaimed；x86+arm64。
- **generic/core**：`kernel/trace/trace_syscalls.c`
- **RISC-V**：`arch/riscv/include/asm/ftrace.h:31,37`；`arch/riscv/kernel/ftrace.c::arch_syscall_match_sym_name()`
- **arm64**：`arch/arm64/include/asm/ftrace.h:203,210`；`arch/arm64/kernel/ftrace.c::arch_syscall_match_sym_name()`
- **x86**：`arch/x86/kernel/ftrace.c::arch_syscall_match_sym_name()`。
- **其他**：`arch_syscall_match_sym_name()`
- **来源**：[来源 1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/trace/trace_syscalls.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 2](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kernel/ftrace.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)；[来源 3](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/kernel/ftrace.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

## 使用说明

- 邮件链接用于理解语义、评审和系列状态；固定源码链接用于确认当前实现。
- 开工前必须重新检查链接对应系列是否已有新版本或进入 maintainer tree。
- 自动抓取 lore 可能遇到访问限制；可通过 Message-ID、Pipermail 或 Patchwork 交叉定位同一补丁。
