# mm-pgtable 可移植性分析（linux-arm-kernel → RISC-V）—— 第 2 片

> 输入：`data/by_category/mm-pgtable.1.jsonl`（180 条系列）。
> 基线树：Linux v7.2.0-rc3（`/Users/zq/Desktop/patch-work/linux-riscv`），落点已 Grep 核对。
> 深挖（curl 全文核实）：#33 / #47 / #69 / #135 / #173（5 条，含 riscv 落点比对）。

## 摘要

- **系列总数**：180
- **四态计数**：
  - **ALREADY**：6（riscv 已采纳同一通用基础设施 —— fault 追踪点 / ptdump 分级回调 / kasan_init_generic / __pgd_alloc）
  - **PORTABLE**：约 48（通用 `mm/`、`kernel/`、`lib/` 改动，几乎直接适用 riscv）
  - **PATTERN**：约 22（arm64 专属实现，机制可在 `arch/riscv/mm/*` 重写）
  - **N-A**：约 104（ARM 专有 HW/ISA：KVM-arm64 nested、arm-SMMU/Apple-DART IOMMU、MTE/HW_TAGS、POE/S1PIE、CCA Realm、TTBR/TCR 寄存器、arm 错误清理、x86/powerpc、网络驱动噪声）

### 本类 Top 候选（按价值排序）

1. **#135 Merge arm64/riscv hugetlbfs contpte support**（PORTABLE）—— 新增 `mm/hugetlb_contpte.c` 共享文件，**同时改 arch/riscv 与 arch/arm64**，Rivos（riscv 厂商）主导。arm64↔riscv 融合的最佳范例。
2. **#69 / #116 Optimize mprotect() for large folios**（PORTABLE）—— `mm/mprotect.c` PTE 批处理，riscv 经通用路径自动获益。
3. **#47 Direct Map Removal for guest_memfd**（PORTABLE）—— 通用 `AS_NO_DIRECT_MAP` + `set_direct_map_valid_noflush` 导出；riscv 已有该接口。
4. **#173 / #177 / #128 pagetable ctor/dtor 系列**（PORTABLE）—— 通用页表构造/析构；riscv `pgalloc.h`/`init.c` 直接在补丁内被改。
5. **#33 arm64: FEAT_BBM L2 + large block mapping when rodata=full**（PATTERN）—— rodata=full 保留大块线性映射、按权限变更再拆分；riscv 落点 `mm/pageattr.c`（BBML2 属 arm 硬件，需 riscv 等价的安全更新保证）。
6. **#109 kexec: Kexec HandOver (KHO)**（PORTABLE）—— 通用 `kernel/kexec` + `memblock` 框架。
7. **#165 batched unmap lazyfree large folios**（PORTABLE）—— `mm/rmap` + tlbbatch 区间刷新；riscv 已有 tlbbatch。

> 反例（勿误报）：**#20/#104**（arm64 fault 追踪点）、**#129**（ptdump 分级回调）、**#60/#82**（kasan_init_generic 统一）均 **ALREADY** —— riscv 本树已实现/已采纳。

---

## Top 可移植候选（深度，已 curl + Grep 核实）

### 1. #135 Merge arm64/riscv hugetlbfs contpte support — PORTABLE ★
- **原补丁**：Merge arm64/riscv hugetlbfs contpte support（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250321130635.227011-4-alexghiti@rivosinc.com/）状态=new
- **可移植点**：把 riscv NAPOT 与 arm64 contpte 的 `huge_ptep_get()`/`set_huge_pte_at()`/`huge_pte_clear()`/`huge_ptep_get_and_clear()` 抽成**通用文件 `mm/hugetlb_contpte.c`**；两侧 Kconfig 各 `select` 之。
- **riscv 落点**：`mm/hugetlb_contpte.c`（新建，共享）、`arch/riscv/include/asm/pgtable.h`（+45 行）、`arch/riscv/include/asm/hugetlb.h`、`arch/riscv/mm/hugetlbpage.c`（-62 行）。**已核实**：本树 `arch/riscv/mm/hugetlbpage.c:6` 已有 `huge_ptep_get`、`:246` `set_huge_pte_at`、`:187` `arch_make_huge_pte`、napot 全套 —— 能力 ALREADY，本系列价值在“共享化”。
- **判定**：PORTABLE —— 由 riscv 厂商主导、diff 直接改 arch/riscv，是 arm↔riscv 机制统一的样板；能力层面 riscv 已具备（ALREADY），迁移点=共享代码。

### 2. #69 Optimize mprotect() for large folios (v5) — PORTABLE
- **原补丁**：Optimize mprotect() for large folios（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250718090244.21092-7-dev.jain@arm.com/）状态=new
- **可移植点**：patch 6/7「mm: Optimize mprotect() by PTE batching」纯改 `mm/mprotect.c`（+125 行）；配套 `ptep_modify_prot_start/commit` 的批处理版本（patch 3）与 `FPB_RESPECT_WRITE`、`can_change_pte_writable()` 拆分均在通用 `mm/`。
- **riscv 落点**：通用 `mm/mprotect.c` 自动适用；riscv **未**覆写 `ptep_modify_prot_start/commit`（Grep 空），走通用回退即获益。若追求批处理加速，可在 `arch/riscv/include/asm/pgtable.h` 增批处理 hook（PATTERN 增量）。
- **判定**：PORTABLE —— 核心为通用 mm，riscv 直接受益。

### 3. #47 Direct Map Removal Support for guest_memfd — PORTABLE
- **原补丁**：Direct Map Removal Support for guest_memfd（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250828093902.2719-4-roypat@amazon.co.uk/）状态=new
- **可移植点**：patch 3「mm: introduce AS_NO_DIRECT_MAP」纯通用（`include/linux/pagemap.h`、`mm/gup.c`、`mm/mlock.c`、`mm/secretmem.c`）；patch 2「arch: export set_direct_map_valid_noflush to KVM」需各 arch 导出符号。
- **riscv 落点**：**已核实** `arch/riscv/mm/pageattr.c:389` `set_direct_map_valid_noflush(page, nr, valid)` 已存在，导出即可；`AS_NO_DIRECT_MAP` 通用生效。
- **判定**：PORTABLE —— 通用 mm 底座；riscv 接口齐备。

### 4. #173 move pagetable_*_dtor() to __tlb_remove_table()（含 #177/#128 同族）— PORTABLE
- **原补丁**：move pagetable_*_dtor() to __tlb_remove_table()（https://patchwork.kernel.org/project/linux-arm-kernel/patch/47f44fff9dc68d9d9e9a0d6c036df275f820598a.1736317725.git.zhengqi.arch@bytedance.com/）状态=new
- **可移植点**：patch 07「mm: pgtable: introduce pagetable_dtor()」统一 22+ 架构页表析构；**diff 直接包含** `arch/riscv/include/asm/pgalloc.h`(8±) 与 `arch/riscv/mm/init.c`(4±)，还含 patch 02「riscv: mm: Skip pgtable level check in {pud,p4d}_alloc_one」、patch 05「arm64: use mmu gather to free p4d」。
- **riscv 落点**：`arch/riscv/include/asm/pgalloc.h`、`arch/riscv/mm/init.c`、通用 `include/linux/mm.h`+`mm/memory.c`。**已核实** riscv `pgalloc.h:115` 已用通用 `__pgd_alloc(mm,0)`（#177 的 `asm-generic __pgd_alloc` 已落地）。
- **判定**：PORTABLE —— 通用页表生命周期重构，riscv 是直接参与方。

### 5. #33 arm64: FEAT_BBM L2 + large block mapping when rodata=full (v8) — PATTERN ★
- **原补丁**：arm64: support FEAT_BBM level 2 and large block mapping when rodata=full（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250917190323.3828347-3-yang@os.amperecomputing.com/）状态=new
- **可移植点**：核心思想 = rodata=full 下**保留线性映射大块（PMD/PUD）**、仅在权限变更时按需拆分（patch 3「support large block mapping when rodata=full」+ patch 4「split linear mapping if BBML2 unsupported on secondary CPUs」）。与 riscv 当前“总是可按需拆分”互补 —— 目标是先享大块 TLB、再懒拆分。
- **riscv 落点**：`arch/riscv/mm/pageattr.c`（**已核实** `__split_linear_mapping_{pmd,pud,p4d,pgd}`、`split_linear_mapping()`、`set_memory_ro` 齐备）、`arch/riscv/mm/init.c`（线性映射建立）。
- **判定**：PATTERN —— 机制可复用；但 patch 1/2「BBM Level 2 cpufeature + AmpereOne 白名单」是 **arm 硬件特性**（break-before-make L2 无冲突中止保证），riscv 侧需以 Svvptc/自身 BBM 语义提供等价的“安全原地改块”保证，非直接照搬。

### 6. #109 kexec: introduce Kexec HandOver (KHO) — PORTABLE
- **原补丁**：kexec: introduce Kexec HandOver (KHO)（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250509074635.3187114-10-changyuanl@google.com/）状态=new
- **可移植点**：`memblock`（MEMBLOCK_RSRV_KERN/scratch）、`kernel/kexec` KHO 生成/解析/内存保存均在通用层。
- **riscv 落点**：通用 `kernel/kexec_*`、`mm/memblock.c`；riscv 已有 `machine_kexec*.c`（基线 §12），KHO 的 arch 钩子可增。
- **判定**：PORTABLE（框架通用）+ 少量 PATTERN（arch fdt/内存交接钩子）。

### 7. #165 batched unmap lazyfree large folios during reclamation — PORTABLE
- **原补丁**：mm: batched unmap lazyfree large folios（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250214093015.51024-3-21cnbao@gmail.com/）状态=new
- **可移植点**：patch 2「mm: Support tlbbatch flush for a range of PTEs」+ patch 3「batched unmap for lazyfree large folios」，通用 `mm/rmap.c` + tlbbatch 区间化。
- **riscv 落点**：**已核实** `arch/riscv/include/asm/tlbbatch.h` 存在、`arch/riscv/mm/tlbflush.c` 有区间刷新/IPI/阈值逻辑（基线 §1 批量 unmap）。
- **判定**：PORTABLE —— 通用 mm；riscv tlbbatch 底座已备。

---

## 全量判定表（覆盖 180 条；同质 N-A 已归类）

| # | 系列 | arch | 判定 | 可移植点 / riscv 落点（若有） |
|---|---|---|---|---|
| 1 | arm64/mm: TTBRx_EL1 related changes | arm | N-A | arm TTBR 寄存器布局（ASID/CnP/52bit PA 折叠）；riscv 用 satp |
| 2 | PGD_SIZE align when PA_BITS=52 | arm | N-A | arm 52-bit PA PGD 对齐 |
| 3 | KVM x86/mmu TDX post-populate | other | N-A | x86 TDX |
| 4 | ARM: mm pgd_alloc memcpy 指针 | arm | N-A | arch/arm 32-bit 琐碎清理 |
| 5 | KVM selftests LA57 nested | generic | N-A | x86 VMX 测试 |
| 6 | KVM TDX MMU lock | generic | N-A | x86 TDX |
| 7 | arm64: Add TLBI_XXX_MASK macros | arm | N-A | arm TLBI 指令编码 |
| 8 | linear mapping perm update robust (partial range) | arm | PATTERN | 线性映射拆分健壮性 / `arch/riscv/mm/pageattr.c` |
| 9 | mm: INVALID_PHYS_ADDR generic macro | generic | PORTABLE | 通用宏 / `include/linux/*` |
| 10 | Elide TLB flush in certain pte prot transitions | arm | PATTERN | 权限转换省 TLB flush / `arch/riscv/mm/tlbflush.c`,`pgtable.h` |
| 11 | prevent panic on -ENOMEM in arch_add_memory | arm | PATTERN | pgtable_alloc 错误传播 / `arch/riscv/mm/init.c` |
| 12 | ARM spectre-v2 mitigations | arm | N-A | arch/arm 32-bit 硬件缓解 |
| 13 | avoid always making PTE dirty in pte_mkwrite | arm | PATTERN | HW dirty 交互 / `arch/riscv/include/asm/pgtable.h`（Svade/Svadu 语境）|
| 14 | Drop redundant extern rodata_full | arm | N-A | arm 专属符号清理 |
| 15 | Drop cpu_set_[default/idmap]_tcr_t0sz | arm | N-A | arm TCR 寄存器 |
| 16 | fallback stub for pgd_page_paddr() | arm | N-A | arm 页表 helper 清理 |
| 17 | Two minor fixes for BBML2_NOABORT | arm | PATTERN | 大块映射/relax huge vmap / `arch/riscv/mm/pageattr.c`（BBML2 属 arm）|
| 18 | Support memory hotplug in a Realm | arm | N-A | arm CCA Realm |
| 19 | KVM arm64 nv: Optimize unmap shadow S2 | arm | N-A | KVM arm64 nested |
| 20 | arm64/mm/fault: exceptions tracepoints | arm | **ALREADY** | riscv `mm/fault.c` 已含 `trace/events/exceptions.h`+`trace_page_fault_*` |
| 21 | hugetlb: avoid soft lockup on mprotect | generic | PORTABLE | 通用 `mm/hugetlb.c` cond_resched |
| 22 | hugetlb soft lockup w/ PROT_MTE | generic | PORTABLE | 通用 cond_resched（MTE 框架无关部分）|
| 23 | ARM: arm940 mmu flags | arm | N-A | arch/arm SoC proc info |
| 24 | arm64: alternative patching callbacks safe | arm | N-A | arm alternatives + HW_TAGS；仅 kasan `__always_inline` 通用 |
| 25 | arm64: remove duplicate asm/mmu.h | arm | N-A | 头文件清理 |
| 26 | Enable vmalloc-huge with ptdump | arm | PATTERN | ptdump 支持 huge / `arch/riscv/mm/ptdump.c` |
| 27 | mm/thp fix MTE tag mismatch (zero subpage) | arm | N-A | MTE 标签语义 |
| 28 | ARM: mm support memory-failure | arm | N-A | arch/arm 32-bit RAS |
| 29 | Neoverse-V3AE workarounds | arm | N-A | arm CPU errata |
| 30 | kprobes: call set_memory_rox() | arm | PATTERN | 通用硬化模式 / `arch/riscv/kernel/probes/` |
| 31 | FEAT_BBM L2 for Olympus core | arm | N-A | arm CPU BBML2 白名单 |
| 32 | realm: encrypted data from firmware | arm | N-A | arm CCA Realm |
| 33 | FEAT_BBM L2 + large block mapping when rodata=full | arm | **PATTERN★** | rodata=full 大块+懒拆分 / `arch/riscv/mm/pageattr.c`,`init.c` |
| 34 | ARCH_PAGE_TABLE_SYNC_MASK_VMALLOC | generic | PORTABLE | 通用 `mm/vmalloc.c` 内核映射同步 |
| 35 | kasan.write_only in hw-tags | generic | N-A | HW_TAGS 依赖 MTE |
| 36 | KVM arm64 TTW SEA + 52bit PA S1 | arm | N-A | KVM arm64 硬件页表走查 |
| 37 | mm: Move KPTI helpers to mmu.c | arm | N-A | arm KPTI |
| 38 | iommu io-pgtable-dart off-by-one | generic | N-A | Apple DART IOMMU |
| 39 | arm64: refactor the rodata=xxx | arm | PATTERN | rodata= 解析 / `arch/riscv/mm/init.c` |
| 40 | Type correctness cleanup ARM64 MMU init | arm | N-A | arm mm init 类型清理 |
| 41 | Cleanup free_pages() misuse | arm | PORTABLE | 通用 `mm/page_alloc`；**含 riscv patch**（已覆盖）|
| 42 | KVM arm64 nested VNCR TLB ASID | arm | N-A | KVM arm64 nested |
| 43 | reject unreasonable folio/compound sizes (memremap) | generic | PORTABLE | 通用 `mm/` folio 尺寸校验 |
| 44 | KVM arm64 nested VA sign ext | arm | N-A | KVM arm64 nested |
| 45 | Fix CFI in kpti_ng_pgd_alloc | arm | N-A | arm KPTI + CFI |
| 46 | Don't broadcast TLBI if mm local-only | arm | PATTERN | mm_cpumask 优化 / `arch/riscv/mm/tlbflush.c` |
| 47 | Direct Map Removal for guest_memfd | generic | **PORTABLE** | `AS_NO_DIRECT_MAP`+set_direct_map / `arch/riscv/mm/pageattr.c:389` |
| 48 | reject unreasonable folio sizes (alloc_contig) | generic | PORTABLE | 通用 `mm/page_alloc` |
| 49 | kernel-doc MEMBLOCK_RSRV_NOINIT | generic | PORTABLE | 通用文档 |
| 50 | iommu apple-dart 4-level | generic | N-A | Apple DART IOMMU |
| 51 | KVM arm64 reschedule S2 destroy | arm | N-A | KVM arm64（cond_resched 思想通用但落点 KVM-arm）|
| 52 | pkeys-based cred hardening | arm | N-A | arm POE/POR 硬件；通用 SLAB_SET_PKEY 无 riscv 后端 |
| 53 | iommu io_ptdump + SMMUv3 dump | arm | N-A | arm SMMU |
| 54 | iommu apple-dart 4-level (v1) | generic | N-A | Apple DART IOMMU |
| 55 | kasan.store_only in hw-tags | generic | N-A | HW_TAGS 依赖 MTE |
| 56 | Remove pud_user from pgtable-nopmd.h | generic | PORTABLE | 通用 asm-generic 页表清理 |
| 57 | kasan stonly-mode in hw-tags | generic | N-A | HW_TAGS 依赖 MTE |
| 58 | ARM: mm Don't use %pK | arm | N-A | arch/arm 清理 |
| 59 | encrypt/decrypt for vmalloc regions | arm | N-A | arm CCA 内存加密 |
| 60 | kasan: unify kasan_enabled() (ARCH_DEFER_KASAN) | generic | **ALREADY** | riscv `mm/kasan_init.c:536` 已调用 `kasan_init_generic()` |
| 61 | mm: Pass page instead of folio_page | generic | PORTABLE | 通用 mm 热修 |
| 62 | KVM: Enable mmap() for guest_memfd | other | N-A | x86 为主（通用 guest_memfd 核心属底座）|
| 63 | KVM arm64 SMMUv3 driver for pKVM | arm | N-A | arm SMMU + pKVM |
| 64 | Fix UAF race hotunplug vs ptdump | arm | PATTERN | 见 #84 通用 ptdump 锁 / `arch/riscv/mm/ptdump.c` |
| 65 | KVM arm64 destroy S2 periodically | arm | N-A | KVM arm64 |
| 66 | mm/page_alloc PCP list for THP CMA | generic | PORTABLE | 通用 `mm/page_alloc.c` |
| 67 | phys_to_ttbr on pgdir for idmap | arm | N-A | arm TTBR/idmap |
| 68 | vmalloc VMALLOC_EARLY_START boundary | generic | PORTABLE | 通用 `mm/vmalloc.c` |
| 69 | Optimize mprotect() for large folios (v5) | arm | **PORTABLE** | 通用 `mm/mprotect.c` PTE 批处理 |
| 70 | arm: mm fault string choices helper | arm | N-A | arch/arm 32-bit 琐碎 |
| 71 | arm: mm l2x0 string choices helper | arm | N-A | arch/arm L2 缓存 |
| 72 | stackleak: Clang stack depth (KSTACK_ERASE) | arm | PATTERN | 通用硬化 / `arch/riscv/Kconfig` select + KCOV __init 处理 |
| 73 | Drop redundant addr inc in set_huge_pte_at | arm | N-A | arm hugetlb 清理 |
| 74 | Replace TLBI macros with C functions | arm | N-A | arm TLBI 编码（riscv tlbflush 已是 C）|
| 75 | torture: EXPERT Kconfig for arm64 KCSAN | arm | N-A | arm64 测试配置（riscv 缺 KCSAN，属独立缺口）|
| 76 | efi: Fix KASAN false positive EFI stack | arm | N-A | arm64 EFI runtime stack 专属 |
| 77 | Drop wrong writes into TCR2_EL1 | arm | N-A | arm TCR2 寄存器 |
| 78 | Enable perm change on kernel block mappings (v4) | arm | PATTERN | 同 #33/#87 族 / `arch/riscv/mm/pageattr.c` |
| 79 | mm/rmap fix OOB during batched unmap | generic | PORTABLE | 通用 `mm/rmap.c` |
| 80 | mm/rmap folio unmap batching safe | generic | PORTABLE | 通用 `mm/rmap.c` |
| 81 | Initial BBML2 support for contpte_convert | arm | N-A | arm BBML2 硬件（Svnapot 语境但优化依赖 BBML2）|
| 82 | kasan: unify kasan_arch_is_ready w/ kasan_enabled | arm | **ALREADY** | 同 #60 统一已落地；riscv `kasan_init.c` 已采纳 |
| 83 | Optimize loop of contpte_ptep_get | arm | PATTERN | 见通用 #125 / `arch/riscv/mm/hugetlbpage.c`（napot）|
| 84 | mm/ptdump take hotplug lock in walk_pgd | generic | PORTABLE | 通用 `mm/ptdump.c`；riscv 用通用 ptdump |
| 85 | Remove pXX_devmap bit and pfn_t type | generic | PORTABLE | 通用 mm + `arch/riscv/include/asm/pgtable*.h` 去 pXd_devmap |
| 86 | KVM: Introduce KVM Userfault | arm | N-A | 通用 KVM 核心属底座；x86/arm64 为主 |
| 87 | Enable perm change on block mappings (v3, pagewalk) | arm | PATTERN | 通用 pagewalk + `arch/riscv/mm/pageattr.c` |
| 88 | Add FIELD_MODIFY() helper | arm | PORTABLE | 通用 `include/linux/bitfield.h` helper |
| 89 | Remove arch_flush_tlb_batched_pending() | generic | PORTABLE | 通用 mm + `arch/riscv/include/asm/tlbflush.h` |
| 90 | Readahead tweaks for larger folios | generic | PORTABLE | 通用 `mm/readahead`+`filemap`；arch exec folio hook（PATTERN 增量）|
| 91 | task_stack: object_is_on_stack for KASAN tagged | generic | N-A | 标签指针（SW/HW_TAGS）；riscv 无标签 |
| 92 | ptdump: prevent hotplug in check_wx() | arm | PATTERN | 见 #84 / `arch/riscv/mm/ptdump.c` |
| 93 | Ensure lazy_mmu_mode never nests | arm | N-A | riscv 无 lazy_mmu（Grep 空）|
| 94 | Close race where stale TLB entry valid | arm | N-A | arm break-before-make |
| 95 | Lazy mmu mode fixes and improvements | arm | PORTABLE | 通用 mm 修复（arch_in_lazy_mmu_mode）；riscv 无 lazy_mmu 后端但通用修复适用 |
| 96 | Enable huge-vmalloc permission change | arm | PATTERN | 通用 pagewalk without locks + `arch/riscv/mm/pageattr.c` |
| 97 | KVM arm64 mask VA bits TLBI VNCR | arm | N-A | KVM arm64 nested |
| 98 | Elide dsb in kernel TLB invalidations | arm | N-A | arm dsb 屏障 |
| 99 | KVM arm64 nv TLBI S1E2 VNCR | arm | N-A | KVM arm64 nested |
| 100 | Lift cma address limit w/ DMA_NUMA_CMA | arm | N-A | arm CMA 地址限制（弱 PATTERN）|
| 101 | iommu arm-smmu + drm/msm stall-on-fault | arm | N-A | arm SMMU + msm GPU |
| 102 | KVM arm64 nv VNCR SW-TLB mmu_lock | arm | N-A | KVM arm64 nested |
| 103 | drm/msm sparse VM_BIND (io-pgtable-arm) | generic | N-A | arm iommu |
| 104 | RV LTL monitors（arm64 page fault trace points）| arm | **ALREADY** | 同 #20；riscv fault.c 已有追踪点 |
| 105 | Check pxd_leaf() vs !pxd_table() teardown | arm | N-A | arm 页表编码（弱 PATTERN）|
| 106 | KVM arm64 Recursive NV support | arm | N-A | KVM arm64 nested |
| 107 | Permit lazy_mmu_mode to be nested | arm | N-A | riscv 无 lazy_mmu |
| 108 | Disable barrier batching in irq contexts | arm | N-A | arm BBM 批处理 |
| 109 | kexec: Kexec HandOver (KHO) | arm | **PORTABLE** | 通用 `kernel/kexec`+`memblock`；riscv 已有 kexec |
| 110 | Drop redundant check in pmd_trans_huge | arm | N-A | arm 清理 |
| 111 | Drop duplicate check in pmd_trans_huge | arm | N-A | arm 清理 |
| 112 | iommu io-pgtable-arm quirk WARN_ON | generic | N-A | arm iommu |
| 113 | mm: Avoid sharing high VMA flag bits | arm | PORTABLE | 通用 mm VM_HIGH_ARCH；riscv Zicfiss 影子栈用之 |
| 114 | ARCH_FORCE_PAGE_BLOCK_ORDER | generic | PORTABLE | 通用 mm Kconfig |
| 115 | Kcompressd for memory compression | generic | PORTABLE | 通用 mm 压缩 |
| 116 | Optimize mprotect for large folios (v2) | arm | PORTABLE | 同 #69 族，通用 `mm/mprotect.c` |
| 117 | Re-organise FEAT_S1PIE PIRE0/PIR_EL1 | arm | N-A | arm S1PIE 权限间接（硬件）|
| 118 | Reorder tlbi in contpte_convert under BBML2 | arm | N-A | arm BBML2 硬件 |
| 119 | iommu io-pgtable-arm selftest device | generic | N-A | arm iommu 测试 |
| 120 | mm: Introduce for_each_valid_pfn() | other | PORTABLE | 通用 mm PFN 迭代器（FLATMEM/SPARSEMEM）|
| 121 | Perf improvements hugetlb/vmalloc arm64 | arm | PORTABLE | page_table_check 批处理（通用）+ arm64 hugetlb（PATTERN）|
| 122 | igc: Frame Preemption | generic | N-A | 网络驱动噪声（误入 mm 桶）|
| 123 | arm: includes for mem_encrypt | arm | N-A | arm 头文件 |
| 124 | KVM arm64 hcr uninit fix | arm | N-A | KVM arm64 |
| 125 | mm/contpte optimize loop | generic | PORTABLE | 通用；riscv napot 语境 / `arch/riscv/mm/hugetlbpage.c` |
| 126 | Implement pte_po_index() POE | arm | N-A | arm POE 权限覆盖 |
| 127 | Fix mmu notifiers range-based (6.6 backport) | generic | PORTABLE | 通用 mmu notifier（stable 回移）|
| 128 | Always call constructor for kernel page tables | arm | PORTABLE | 通用 pte ctor/dtor + `arch/riscv` pgalloc |
| 129 | mm/ptdump split note_page level callbacks | arm | **ALREADY** | riscv `mm/ptdump.c` 已有 `note_page_pte/pmd/pud/p4d/pgd` |
| 130 | for_each_valid_pfn() (RFC v2) | other | PORTABLE | 同 #120，通用 mm |
| 131 | pageattr bail for vmalloc_huge perm change | arm | PATTERN | 同 #87 族 / `arch/riscv/mm/pageattr.c` |
| 132 | string: load_unaligned_zeropad in strscpy | arm | PORTABLE | 通用 `lib/string`（kasan 测试属 arm HW_TAGS）|
| 133 | mm/filemap arch exec folio size | generic | PORTABLE | 通用 `mm/filemap`；arch hook 增量 PATTERN |
| 134 | drm/panfrost AARCH64_4K pgtable | arm | N-A | GPU 驱动 |
| 135 | Merge arm64/riscv hugetlbfs contpte support | arm | **PORTABLE★** | 新建 `mm/hugetlb_contpte.c`；**diff 直接改 arch/riscv** |
| 136 | Correct the update of max_pfn | arm | N-A | arm（弱 PATTERN，riscv 有 max_pfn）|
| 137 | iommu arm-smmu-v3 pinned KVM VMID | arm | N-A | arm SMMU |
| 138 | Remove randomization of linear map | arm | N-A | arm 线性映射 KASLR（弱 PATTERN）|
| 139 | igc: Frame Preemption in IGC | generic | N-A | 网络驱动噪声 |
| 140 | selftest powerpc/mm/pkey build fix | other | N-A | powerpc |
| 141 | Define PTDESC_ORDER | arm | N-A | arm 清理 |
| 142 | Create level specific section mappings map_range | arm | N-A | arm 早期映射（弱 PATTERN）|
| 143 | Improve Zram (kcompressd) | generic | PORTABLE | 通用 mm 压缩 |
| 144 | Define PTE_SHIFT | arm | N-A | arm 清理 |
| 145 | Populate vmemmap at page level if unaligned | arm | PATTERN | 页级 vmemmap / `arch/riscv/mm/init.c` vmemmap |
| 146 | Use memory copy instructions in usercopy | arm | N-A | arm FEAT_MOPS ISA |
| 147 | Convert __pte_to_phys/__phys_to_pte_val funcs | arm | N-A | arm 清理 |
| 148 | mm: Rework generic PTDUMP configs | arm | PORTABLE | 通用 ptdump Kconfig；riscv select PTDUMP |
| 149 | Fixes for hugetlb on arm64 | arm | PORTABLE | 通用 huge_ptep_get_and_clear 参数 + arm64 hugetlb(PATTERN) |
| 150 | Fix Boot panic on Ampere Altra | arm | N-A | arm CPU 专属 |
| 151 | KVM x86 nVMX IRQ + teardown | other | N-A | x86 KVM |
| 152 | hotplug: Drop redundant WARN_ON | arm | N-A | arm 清理 |
| 153 | kselftest arm64 mte hugetlb test | arm | N-A | MTE 测试 |
| 154 | Drop PXD_TABLE_BIT | arm | N-A | arm 页表编码 |
| 155 | Consistently use pud_sect_supported() | arm | N-A | arm hugetlb 清理 |
| 156 | arm/pgtable remove duplicate header | generic | N-A | 头文件清理 |
| 157 | io-pgtable-dart DART1 subpage prot | generic | N-A | Apple DART |
| 158 | Explicit cast conversions | arm | N-A | arm 清理 |
| 159 | mm: pgtable fix pte_swp_exclusive | generic | PORTABLE | 通用 + `arch/riscv/include/asm/pgtable.h:1196`（已有）|
| 160 | ioremap_prot: pass pgprot_t | generic | PORTABLE | 通用 `mm/ioremap` + arch ioremap_prot |
| 161 | perf/arm-cmn ioremap CMN700 | generic | N-A | arm CMN PMU |
| 162 | Fixes for hugetlb and vmalloc arm64 | arm | PORTABLE | huge_ptep 参数 + arch_sync_kernel_mappings（通用）|
| 163 | arm64: mm Don't use %pK | arm | N-A | arm 清理 |
| 164 | arm: pgtable fix NULL deref | arm | N-A | arch/arm 32-bit |
| 165 | batched unmap lazyfree large folios | generic | **PORTABLE** | 通用 `mm/rmap`+tlbbatch / `arch/riscv/include/asm/tlbbatch.h` |
| 166 | Populate vmemmap/linear page level (v6) | arm | PATTERN | 见 #145 / `arch/riscv/mm/init.c` |
| 167 | hugetlb/vmalloc fixes+perf (v1, 16p) | arm | PORTABLE | page_table_check 批处理（通用）+ arm64 hugetlb(PATTERN) |
| 168 | mm/ptdump Drop GENERIC_PTDUMP | generic | PORTABLE | 通用 ptdump 配置 |
| 169 | KVM arm64 Fix nested S2 realloc | arm | N-A | KVM arm64 nested |
| 170 | mm/pkey: PKEY_UNRESTRICTED macro | other | PORTABLE | 通用 uapi 宏（pkeys 后端 riscv 无）|
| 171 | TLB Conflict Abort Exception handler KVM | arm | N-A | arm BBM/KVM |
| 172 | account hotplug mem in linear randomize | arm | N-A | arm KASLR 线性区（弱 PATTERN）|
| 173 | move pagetable_*_dtor to __tlb_remove_table | arm | **PORTABLE** | 通用 pgtable_dtor；**diff 改 arch/riscv pgalloc+init** |
| 174 | selftests/mm silence unused-result | generic | PORTABLE | 通用 selftests |
| 175 | Rename pte_mkpresent as pte_mkvalid | arm | N-A | arm 清理 |
| 176 | Replace open encodings with PXD_TABLE_BIT | arm | N-A | arm 页表编码 |
| 177 | Account page tables at all levels (PGD ctor/dtor) | arm | PORTABLE | 通用 `__pgd_alloc`（riscv 已用）+ PGD ctor/dtor |
| 178 | Populate vmemmap page level hotplug (v3) | arm | PATTERN | 见 #145 / `arch/riscv/mm/init.c` |
| 179 | Test pmd_sect() in vmemmap_check_pmd | arm | N-A | arm vmemmap 清理 |
| 180 | docs: arm64 vmemmap layout | arm | N-A | arm 专属文档 |

### N-A 主要分组（归类计数）
- **KVM-arm64 nested/S2/VNCR**：#19,36,42,44,51,63,65,86(部分),97,99,102,106,124,137,169,171 —— ARM 虚拟化硬件页表走查，riscv KVM 另有 H 扩展路径。
- **arm-SMMU / Apple-DART / GPU IOMMU**：#38,50,53,54,63,101,103,112,119,134,137,157 —— 厂商 IOMMU/GPU 硬件。
- **MTE / HW_TAGS / 标签指针**：#27,35,55,57,91,153 —— 无 riscv 对应 ISA。
- **CCA Realm / 内存加密**：#18,32,59 —— arm 机密计算硬件。
- **arm 寄存器/页表编码清理**：#1,2,7,14,15,16,25,37,40,45,67,73,74,77,110,111,141,144,147,152,154,155,156,158,163,175,176,179,180。
- **arch/arm 32-bit / SoC / 硬件缓解**：#4,12,23,28,58,70,71,123,164。
- **POE/S1PIE/MOPS 专有 ISA**：#52,117,126,146。
- **x86 / powerpc / 网络驱动噪声**：#3,5,6,62,140,151,122,139。
