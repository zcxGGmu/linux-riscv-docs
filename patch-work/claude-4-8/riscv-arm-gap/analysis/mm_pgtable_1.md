# mm-pgtable 可移植性分析（linux-arm-kernel → RISC-V）—— shard 1

> 输入：`data/by_category/mm-pgtable.0.jsonl`（182 条系列）。
> 类别：页表 / TLB / hugetlb / 大块映射 / rodata / vmemmap / sanitizer / KVM stage-2 / iommu。
> 判定依据：`_baseline_riscv.md`、`_taxonomy.md`，并对 6 条最强候选 `curl` 取全文核实 diff、用 Grep 核对 riscv 落点文件存在。

## 摘要

- **系列总数：182**
- **四态计数：**
  - **PORTABLE：55**（通用 mm / KASAN / vmemmap / shstk / page_table_check / bpf / vmalloc 等）
  - **PATTERN：24**（rodata=full 类线性别名、ROX/BBML2 大块合并、线性映射拆分、热插拔 TLB、ASID、TLBI API 等 arch 重写）
  - **ALREADY：1**（generic vDSO，riscv 已用）
  - **N-A：102**（KVM arm64 stage-2 / nested / pKVM、arm-SMMU/io-pgtable、errata、板级 DTS、ARM32、POE/MTE/HDBSS/HACDBS 等 arm 专有 HW/ISA）

- **本类 Top 候选（按价值排序）：**
  1. **KASAN SW_TAGS 架构无关化**（#90）—— PORTABLE，riscv 真实缺口，作者含 SiFive 的 Samuel Holland，直接为 riscv SW_TAGS 铺路。
  2. **mm/sparse-vmemmap 通用 vmemmap_set_pmd/check_pmd**（#45）—— PORTABLE，**补丁自带 riscv patch**（3/5 删除 riscv 私有 helper 改用通用码）。
  3. **mm arch/shstk 通用 vm_mmap_shadow_stack()**（#122）—— PORTABLE，**补丁自带 riscv patch**（3/5 转用通用 helper）。
  4. **mm/kasan 让 kasan=on|off 对三种模式生效**（#123）—— PORTABLE，KASAN 通用核心，riscv 落点 `kasan_init.c`+Kconfig。
  5. **arm64 Unmap linear alias of kernel data/bss = rodata=full 类**（#47）—— PATTERN，riscv 落点 `mm/init.c`+`pageattr.c`。
  6. **arm64 EXECMEM_ROX_CACHE + PMD 线性映射合并（BBML2）**（#29）—— PATTERN，riscv 落点 `pageattr.c`（已有 `__split_linear_mapping`，需补 collapse/coalesce）。
  7. **page_table_check 重新引入 addr 参数**（#157）—— PORTABLE，改通用 mm API 签名，riscv 必须适配 `pgtable.h`。
  8. **ARCH_HAS_COPY_MC 通用 fallback + hwpoison**（#24）—— PORTABLE+PATTERN，riscv 确认无 `ARCH_HAS_COPY_MC`（真实缺口）。
  9. **persistent huge zero folio 只读 + set_direct_map_ro_noflush**（#10）—— PORTABLE+PATTERN，riscv 确认缺 `set_direct_map_ro_noflush`。
  10. **bpf: KASAN checks in JITed programs**（#38）—— PORTABLE，riscv 落点 `arch/riscv/net/bpf_jit_comp64.c`。

---

## Top 可移植候选（深度，已核实）

### 1. KASAN SW_TAGS 架构无关化（#90）—— PORTABLE
- **原补丁**：`[v12,01/15] kasan: sw_tags: Use arithmetic shift for shadow computation`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/6080be7964fc726327186d5bf7979e16ddd282bb.1774872838.git.m.wieczorretman@pm.me/）状态=new
- **可移植点**：把原本 arm64 专属的 KASAN **SW_TAGS**（软件标签，非 MTE）通用化 —— `kasan: arm64: x86: Make special tags arch specific`、`Make page_to_virt() KASAN aware`；引入 `arch/*/include/asm/kasan-tags.h`（tag 宽度/native tag 架构化），x86 计划用 4-bit tag。**由 Samuel Holland（sifive）参与**，方向即"让 SW_TAGS 不再绑死 arm64"。
- **riscv 落点**：`arch/riscv/mm/kasan_init.c`、`arch/riscv/include/asm/kasan.h`（现仅 generic 影子，`KASAN_SHADOW_SCALE_SHIFT` 路径已核实）、新增 `arch/riscv/include/asm/kasan-tags.h`、`arch/riscv/Kconfig`（`select HAVE_ARCH_KASAN_SW_TAGS`）。指针掩码可复用已落地的 **Supm**（`process.c` `PR_PMLEN`）承载 tag-in-pointer。
- **判定**：PORTABLE —— 基线确认 riscv 仅 `KASAN_GENERIC`（`Kconfig:301 depends on KASAN_GENERIC`），SW_TAGS 是真实缺口；本系列正是通用化前置工作。

### 2. mm/sparse-vmemmap 通用 vmemmap_set_pmd()/check_pmd()（#45）—— PORTABLE
- **原补丁**：`[v3,1/5] mm/sparse-vmemmap: provide generic vmemmap_set_pmd() and vmemmap_check_pmd()`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260601084845.3792171-3-songmuchun@bytedance.com/）状态=new
- **可移植点**：把各架构重复的 `vmemmap_set_pmd`/`vmemmap_check_pmd` 收敛进通用 `mm/sparse-vmemmap.c`；**补丁 3/5 = `riscv/mm: drop vmemmap_pmd helpers and use generic code`**（Cc linux-riscv，Palmer/Paul/Alex Ghiti 在收件人）。
- **riscv 落点**：`arch/riscv/mm/init.c`（已核实 `vmemmap_populate_hugepages` at :1373）—— 补丁直接删 riscv 私有 helper 转用通用码。
- **判定**：PORTABLE —— 通用 mm 收敛，补丁本身即含 riscv 适配，近乎零成本随通用码落地。

### 3. mm arch/shstk 通用 vm_mmap_shadow_stack()（#122）—— PORTABLE
- **原补丁**：`mm: arch/shstk: Common shadow stack mapping helper and VM_NOHUGEPAGE`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260225161404.3157851-6-catalin.marinas@arm.com/）状态=new
- **可移植点**：新增通用 `vm_mmap_shadow_stack()`（`VM_SHADOW_STACK`）+ "不把影子栈映射为 THP"；**补丁 3/5 = `riscv: shstk: Use the new common vm_mmap_shadow_stack() helper`**（Cc linux-riscv 已核实）。
- **riscv 落点**：`arch/riscv/kernel/usercfi.c`（已核实 `is_shstk_*`/`set_shstk_*` 全套存在，对应 **Zicfiss**）。
- **判定**：PORTABLE —— 通用 mm helper + riscv 已有影子栈基础设施，补丁自带 riscv 转换。

### 4. mm/kasan 让 kasan=on|off 对三种模式生效（#123）—— PORTABLE
- **原补丁**：`[v5,01/15] mm/kasan: make kasan=on|off work for all three modes`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260225081412.76502-14-bhe@redhat.com/）状态=new
- **可移植点**：把 `kasan=` 引导开关从 arm64/HW_TAGS 专属提升为通用（generic/sw_tags/hw_tags 三模式统一），`move kasan= code to common place`、`don't initialize kasan if disabled`。
- **riscv 落点**：`arch/riscv/mm/kasan_init.c`、`arch/riscv/Kconfig`（`HAVE_ARCH_KASAN if MMU && 64BIT`）—— riscv 可直接受益于通用运行时开关。
- **判定**：PORTABLE —— 通用 KASAN 核心；配合 #90 后 riscv 三模式开关同样适用。

### 5. arm64 Unmap linear alias of kernel data/bss（= rodata=full 类）（#47）—— PATTERN
- **原补丁**：`[v7,01/15] arm64: Unmap linear alias of kernel data/bss`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260529150150.1670604-30-ardb+git@google.com/）状态=new
- **可移植点**：把内核 data/bss 的**线性映射别名**改为不可写/不可执行（rodata=full 家族硬化）；含通用 `mm: Make empty_zero_page[] const`（移入 .rodata），及"按需保留 table/非连续/连续描述符"的线性映射精细拆分。
- **riscv 落点**：`arch/riscv/mm/init.c`（线性映射建立）+ `arch/riscv/mm/pageattr.c`（已核实 `__split_linear_mapping_{pmd,pud,p4d,pgd}`、`set_memory_ro`）。基线明确 riscv **无 rodata=full 全线性别名 RO**（`_baseline_riscv.md` §1）。
- **判定**：PATTERN —— 机制清晰、riscv 有拆分基础设施，但需在 riscv 侧重写别名解除/RO 逻辑（arm 用 BBML2 免 break-before-make，riscv 侧靠 Svvptc 邻域语义）。

### 6. arm64 EXECMEM_ROX_CACHE + PMD 线性映射合并（BBML2）（#29）—— PATTERN
- **原补丁**：`[RFC,1/6] arm64: mm: ... EXECMEM_ROX_CACHE on bbml2 no abort`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260611130144.1385343-7-abarnas@google.com/）状态=new
- **可移植点**：为 execmem ROX 缓存启用大块映射；核心是 `try_collapse_kernel_pmd()`/`__try_collapse_pmd()` —— 权限改动拆块后，**把碎片化线性映射重新合并回 PMD 巨页**（riscv 现只有拆分、无回收合并）。
- **riscv 落点**：`arch/riscv/mm/pageattr.c`（已核实 `split_linear_mapping` 全套；需新增 collapse/coalesce 反向操作）+ execmem 启用（riscv 现用 `bpf_jit`/`init.c` execmem 路径）。
- **判定**：PATTERN —— "拆分后回收合并巨页"是通用价值机制，需 riscv 侧新写；BBML2 检测本身 arm 专属（对应能力 riscv 靠 Svvptc，非同一 CPU-cap）。

### 7. page_table_check 重新引入 addr 参数（#157）—— PORTABLE
- **原补丁**：`[v18,03/12] mm/page_table_check: Reinstate address parameter in ...`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251219-pgtable_check_v18rebase-v18-12-755bc151a50b@linux.ibm.com/）状态=new
- **可移植点**：改通用 `mm/page_table_check.c` 接口签名（`page_table_check_ptes_set`/`pmd[s]_set`/`pud_clear` 等重新带 `addr`）——**所有支持 PTC 的架构都必须同步适配**。
- **riscv 落点**：`arch/riscv/include/asm/pgtable.h`（已核实 `page_table_check_ptes_set(mm, addr, ptep, ...)` 等 8 处调用；riscv `Kconfig:72 select ARCH_SUPPORTS_PAGE_TABLE_CHECK`）。
- **判定**：PORTABLE —— 通用 mm API 变更，riscv 已是 PTC 消费者，属"随通用码适配"。

### 8. ARCH_HAS_COPY_MC 通用 fallback + hwpoison（#24）—— PORTABLE + PATTERN
- **原补丁**：`[v15,1/9] uaccess: add generic fallback version of copy_mc_to_user()`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260618092124.3901230-7-tianruidong@linux.alibaba.com/）状态=new
- **可移植点**：通用 `uaccess` fallback + `mm/hwpoison: return -EFAULT when copy fail`（PORTABLE）；机器检查安全拷贝的 arch 实现（PATTERN）。
- **riscv 落点**：`arch/riscv/lib/`(uaccess) + extable/异常表；基线确认 riscv **无 `ARCH_HAS_COPY_MC`**（grep 无命中，真实缺口）。
- **判定**：PORTABLE（通用 fallback/hwpoison 直接可用）+ PATTERN（同步外部异常恢复的 arch 实现需 riscv 重写，依赖 riscv 的 poison/EDAC 支持成熟度）。

---

## 其余中价值候选（简述，未逐条 curl）

- **#10** persistent huge zero folio 只读：通用 mm（PORTABLE）+ riscv 需补 `set_direct_map_ro_noflush`（`pageattr.c` 现仅 `set_direct_map_invalid_noflush`，已核实缺口，PATTERN）。
- **#38** bpf KASAN in JIT：通用 bpf 框架 `BPF_JIT_KASAN`（PORTABLE）+ riscv JIT 发射 KASAN 检查需重写（`arch/riscv/net/bpf_jit_comp64.c`，PATTERN）。
- **#3 / #106 / #160 / #173** mm/vmalloc 巨块/连续批量映射 + exec folio 对齐：通用 mm/vmalloc（PORTABLE）；arm64 CONT_PTE 部分对应 riscv **Svnapot**（已有）。
- **#12 / #110 / #135 / #167** hugetlb `huge_ptep_get()` 正确性 & 大 folio young/rmap 批处理：通用 mm rmap/migrate/mprotect（PORTABLE）+ riscv arch young helper（`pgtable.h` 已有 `ptep_test_and_clear_young`，PATTERN 增量）。
- **#6** HVO：通用 `hugetlb_vmemmap` 改进（PORTABLE，riscv 已 `select ARCH_WANT_OPTIMIZE_HUGETLB_VMEMMAP`，自动受益）；arm64 `system_supports_hvo` cpucap 为 arm 侧。
- **#50** kpkeys 页表硬化：通用 `mm: Introduce kpkeys` + `set_memory_pkey()` stub（PORTABLE 底座）；arm64 POE 实现 N-A（riscv 无 pkey/POE HW）。
- **#54 / #61 / #43** `ptep_try_set()`/`ptep_try_install()` 无锁空槽安装 + bpf arena：通用 mm/bpf（PORTABLE），riscv 落点 `pgtable.h`（arm64 的 `ptep_try_set` 实现补丁 #26/#34 为 N-A）。
- **#132 / #148 / #159 / #177 / #180 / #174** 线性映射建立提速 / `pgtable_alloc` / `split_kernel_leaf_mapping` 原子上下文 / `change_memory_common`：PATTERN（riscv `mm/init.c`+`pageattr.c`），部分自带通用 `mm: introduce pagetable_alloc_nolock()`（PORTABLE）。
- **#18 / #58 / #107 / #59** 内存热插拔 range TLB flush / pagetable dtor：PATTERN（riscv `mm/tlbflush.c` 已有 range flush+Svinval，属增量对齐）。
- **#71 / #19 / #144** 通用 KVM（`kvm_arch_flush_shadow_all` 锁、guest_memfd MMU notifier、selftests page_align 含 riscv patch）：PORTABLE（virt/kvm 核心与 selftests，riscv KVM 同样调用）。
- **#40 / #46** iommu 通用 `iova_to_phys_length` 接口：PORTABLE（`iommu_domain_ops`/`io_pgtable_ops` 通用框架，riscv IOMMU 可实现）；arm-smmu 具体实现 N-A。

---

## 全量判定表（182 条）

| # | 系列 | arch | 判定 | 可移植点(若有) | riscv落点(若有) | web_url |
|---|---|---|---|---|---|---|
| 1 | Support FEAT_HDBSS (Armv9.5) | arm | N-A | — arm HW 脏页跟踪 | — | .../20260709104026.2612599-3-... |
| 2 | arm-smmu-v3 CMDQ batch force-sync | arm | N-A | — SMMU HW | — | .../20260709095613.831769-1-... |
| 3 | mm/vmalloc speed up ioremap/vmalloc/vmap | arm | **PORTABLE** | 通用 vmap_set_ptes/批量映射 | `mm/vmalloc` 通用；Svnapot 承载 CONT | .../20260709073823.6643-7-... |
| 4 | mm/early_ioremap cleanup reset() | arm | **PORTABLE** | 通用 early_ioremap | riscv 用 early_ioremap | .../20260708170647.362562-4-... |
| 5 | Add BBML3 cpu feature | arm | N-A | — arm cpufeature/BBM level | — (riscv 靠 Svvptc) | .../20260708144331.679816-5-... |
| 6 | Another attempt at HVO on arm64 | arm | **PORTABLE** | 通用 hugetlb_vmemmap 改进 | `mm/init.c`(已 select HVO) | .../20260708031129.3503195-8-... |
| 7 | KVM arm64 Fix TLBI level relax_perms | arm | N-A | — KVM arm stage-2 | — | .../20260707162935.1900874-1-... |
| 8 | Use generic iommu page table for SMMUv3 | arm | N-A | — arm SMMU/iommupt | — | .../7-v1-807e2d1a5efb+e1-... |
| 9 | Organize SMMUv3 invalidation flow | arm | N-A | — SMMU HW | — | .../2-v2-43074a57a53a+fb95-... |
| 10 | make persistent huge zero folio read-only | arm | **PORTABLE**+PATTERN | 通用 mm 只读巨零页 | `pageattr.c` 需补 set_direct_map_ro_noflush | .../20260706130440.9295-4-... |
| 11 | coco guest host page-size align shared bufs | arm | N-A | (通用 swiotlb/dma 对齐可复用) | — riscv 无 CoCo guest | .../20260706060432.1375570-2-... |
| 12 | Fix incorrect access of hugetlb pte entries | arm | **PORTABLE** | 通用 mm huge_ptep_get() 修正 | `mm/rmap,migrate,mprotect` | .../20260703114202.365553-7-... |
| 13 | arm64 mm decode Xs when ISV=1 | arm | N-A | — arm ESR 解码 | — | .../20260702-arm64-xs-decode-... |
| 14 | treewide remove invalid range checks memblock | arm | **PORTABLE** | 通用 memblock 迭代清理 | memblock 通用 | .../20260630150413.1718632-6-... |
| 15 | KVM arm64 ptdump Shadow ptdump fixes | arm | N-A | — KVM arm nested ptdump | — | .../20260630121005.1130996-2-... |
| 16 | KVM Dirty-bit HW accel (HACDBS) | arm | N-A | — arm HW 脏位加速 | — | .../20260629111820.1873540-2-... |
| 17 | ARM mm fix UAF in show_pte() | arm | N-A | (ARM32 fault 修复) | — | .../20260626073048.3595106-3-... |
| 18 | arm64/mm Optimize TLB flush unmap_hotplug | arm | PATTERN | 热插拔 TLB flush 优化 | `mm/tlbflush.c`(已 range flush) | .../20260626012845.475959-1-... |
| 19 | KVM Ignore MMU notifiers guest_memfd-only | generic | **PORTABLE** | 通用 KVM mmu notifier | virt/kvm; riscv KVM | .../20260625130902.258331-1-... |
| 20 | arm64 refresh stale pmd after split_contpmd | arm | N-A | — arm contpmd 特有 | — | .../20260625113953.2332-1-... |
| 21 | arm64 Defer RO remap data/bss linear alias | arm | PATTERN | rodata=full 类线性别名 | `mm/init.c`,`pageattr.c` | .../20260623202817.2225495-2-... |
| 22 | KVM arm64 nv Shadow ptdump fixes | arm | N-A | — KVM nested | — | .../20260623142443.648972-4-... |
| 23 | iommu/qcom Misc Fixes | generic | N-A | — qcom SoC 驱动 | — | .../20260623122034.1166295-7-... |
| 24 | arm64 add ARCH_HAS_COPY_MC support | arm | **PORTABLE**+PATTERN | 通用 copy_mc fallback+hwpoison | `lib/`uaccess+extable(缺 COPY_MC) | .../20260618092124.3901230-7-... |
| 25 | io-pgtable-arm contiguous hint bit | generic | N-A | — arm io-pgtable | — | .../20260618-iommu_contig_hint-... |
| 26 | arm64 mm Remove pte_none comment ptep_try_set | arm | N-A | (trivial 注释) | — | .../20260614210209.2371030-1-... |
| 27 | ARM correct CONFIG_ARM_LPAE comment | arm | N-A | (trivial 注释) | — | .../20260613230139.141855-1-... |
| 28 | kasan hw_tags tag only at allocation | generic | N-A | — HW_TAGS 依赖 MTE | — | .../20260612044425.763060-2-... |
| 29 | arm64 ROX CACHE bbml2 no abort | arm | PATTERN | execmem ROX + PMD 合并 | `pageattr.c`(有 split，需 collapse) | .../20260611130144.1385343-7-... |
| 30 | arm64 errata TLBI NVIDIA Olympus | arm | N-A | — errata/vendor CPU | — | .../20260609234044.3945938-1-... |
| 31 | arm64 mm show direct mapping /proc/meminfo | arm | PATTERN | DirectMap 统计展示 | `mm/init.c` 可加 | .../20260609214205.1260279-1-... |
| 32 | arm64 errata TLBI various Arm CPUs | arm | N-A | — errata | — | .../20260609101203.1512409-2-... |
| 33 | arm-smmu-v3 Tegra264 invalidation workaround | arm | N-A | — SMMU HW | — | .../20260609073204.1760077-3-... |
| 34 | arm64 mm Complete PTE store ptep_try_set | arm | N-A | (arm impl of 通用 ptep_try_set) | — | .../7f5f7c94601312c1a401fb18998291cc@... |
| 35 | KVM arm64 nv Skip vCPUs no pseudo-TLB | arm | N-A | — KVM nested | — | .../aiUvSbrWndQeUPc8@v4bel/ |
| 36 | KVM arm64 Fix block mapping stage-1 walker | arm | N-A | — KVM arm stage-1 | — | .../20260605185255.2431996-1-... |
| 37 | net ethtool mm FPE verification retry | generic | **PORTABLE** | 通用 net(MAC Merge，非页表) | net 通用 | .../20260605025631.2872-1-... |
| 38 | bpf KASAN checks in JITed programs | other | **PORTABLE** | 通用 bpf BPF_JIT_KASAN | `arch/riscv/net/bpf_jit_comp64.c` | .../20260604-kasan-v2-1-... |
| 39 | fixes for data/bss linear alias unmap | arm | PATTERN | 线性别名 + 通用 kasan bss | `mm/init.c`,`pageattr.c` | .../20260604151151.150377-10-... |
| 40 | iommu iova_to_phys_length (v3, 32p) | arm | **PORTABLE** | 通用 iommu_domain_ops 接口 | `drivers/iommu/riscv` 可实现 | .../20260603151804.1963871-15-... |
| 41 | KVM arm64 SRCU lock pgtable walk AT emul | arm | N-A | — KVM arm AT 模拟 | — | .../aiAZfdeyanIvP8SD@v4bel/ |
| 42 | arm64/coco Convert pKVM to CC platform | arm | N-A | — pKVM | — | .../20260603110522.3331819-4-... |
| 43 | bpf Replace scratch PTE atomically arena | generic | **PORTABLE** | 通用 bpf arena PTE 原子替换 | `pgtable.h`,bpf | .../20260601183728.1800490-1-... |
| 44 | mm improve large folio readahead exec | generic | **PORTABLE** | 通用 mm readahead | `mm/filemap,readahead` | .../20260601102205.3985788-2-... |
| 45 | mm/sparse-vmemmap generic set_pmd/check_pmd | arm | **PORTABLE** | 通用 vmemmap（自带 riscv patch） | `mm/init.c` vmemmap | .../20260601084845.3792171-3-... |
| 46 | iommu iova_to_phys_length (9p) | arm | **PORTABLE** | 通用 iommu io_pgtable_ops 接口 | `drivers/iommu/riscv` | .../20260531093637.3893199-5-... |
| 47 | arm64 Unmap linear alias kernel data/bss | arm | PATTERN | rodata=full 类线性别名解除 | `mm/init.c`,`pageattr.c` | .../20260529150150.1670604-30-... |
| 48 | ARM decompressor SCTLR.UWXN/WXN | arm | N-A | — arm 解压器 | — | .../20260529073343.1147383-1-... |
| 49 | remoteproc cleanup carveout helpers | generic | **PORTABLE** | 通用 remoteproc 框架(非页表) | drivers 通用 | .../20260529021637.2077602-4-... |
| 50 | pkeys-based page table hardening (kpkeys) | arm | **PORTABLE**+N-A | 通用 kpkeys/set_memory_pkey stub | `mm/`；arm POE N-A | .../20260526-kpkeys-v8-1-... |
| 51 | ARM mm fix kexec/hibernation TTBR0_PAN | arm | N-A | — arm 专有 | — | .../20260523000839.430550-1-... |
| 52 | ARM io avoid KASAN raw halfword I/O | arm | N-A | — arm asm | — | .../20260522212018.25295-1-... |
| 53 | ARM entry byte load KASAN VMAP shadow | arm | N-A | — arm asm | — | .../20260522211503.25219-1-... |
| 54 | mm Add ptep_try_set() lockless empty-slot | generic | **PORTABLE** | 通用 mm 无锁 PTE 安装 | `pgtable.h` | .../8dc7b56d0f9ef4ef5b8c41f86ab97f3f@... |
| 55 | Add test atomic uaccess POE | arm | N-A | — arm POE | — | .../20260521-poe_futex-v1-1-... |
| 56 | arm64 SMCCC cache invalidation backend | arm | N-A | — SMCCC 固件 ABI | — | .../20260521073047.320614-3-... |
| 57 | arm64 tlb Flush walk cache unshare PMD | arm | PATTERN | walk-cache flush(PMD 共享) | `mm/tlbflush.c` | .../20260521073011.4121277-1-... |
| 58 | arm64 mmu range TLB flush hot unplug | arm | PATTERN | 热插拔 range TLB flush | `mm/tlbflush.c`(已 range) | .../20260521042426.2128731-1-... |
| 59 | arm64 mm pagetable dtor free hot-removed | arm | PATTERN | 热移除 pgtable dtor | `mm/` 热插拔 | .../20260521032730.2104017-1-... |
| 60 | arm64/mm Rename ptdesc_t | arm | N-A | (trivial rename) | — | .../20260520063417.2363417-1-... |
| 61 | mm Add ptep_try_install() lockless (8p) | generic | **PORTABLE** | 通用 mm 无锁 PTE + bpf arena | `pgtable.h`,bpf | .../20260517211232.1670594-5-... |
| 62 | arm64 mm u32 FDT size fixmap_remap_fdt | arm | N-A | — arm fixmap | — | .../20260514171304.2034930-1-... |
| 63 | io-pgtable-arm iommu-pages cleanup | generic | N-A | — arm io-pgtable | — | .../20260513215203.3852661-3-... |
| 64 | arm64 mm drop redundant remap FDT 1st page | arm | N-A | — arm FDT | — | .../20260513170101.1858213-1-... |
| 65 | arm64/mm Enable 128 bit page table entries | arm | **PORTABLE**+N-A | 通用 pxd_val 打印/vm_page_prot 访问器 | `mm/`；D128 HW N-A | .../20260513044547.4128549-2-... |
| 66 | objtool/arm64 Port klp-build to arm64 | arm | PATTERN | 通用 klp-build/objtool 移植范式 | riscv objtool(有限) | .../8881010b54f07432929acb8e704cd6ffcc835318...@... |
| 67 | arm64 mm fix no-map reserved linear mapping | arm | PATTERN | no-map 线性映射处理 | `mm/init.c` | .../20260513010255.3764038-1-... |
| 68 | ARM Do not select HAVE_RUST when KASAN | arm | N-A | — arm Kconfig | — | .../20260511-arm-avoid-rust-with-kasan-... |
| 69 | KVM arm64 nv nested stage-2 reverse map | arm | N-A | — KVM nested | — | .../20260510145338.322962-4-... |
| 70 | arm mm init Integrator boards DT | arm | N-A | — 板级 | — | .../20260509211422.33160-1-... |
| 71 | KVM Fix race kvm_arch_flush_shadow_all | arm | **PORTABLE** | 通用 KVM MMU 锁(loong/mips/generic) | virt/kvm; riscv KVM | .../20260504224213.1049426-4-... |
| 72 | KVM arm64 SMMUv3 driver for pKVM | arm | N-A | — pKVM+SMMU | — | .../20260501111928.259252-2-... |
| 73 | KVM Dirty-bit accel (HACDBS) v1 | arm | N-A | — arm HW | — | .../20260430111424.3479613-4-... |
| 74 | arm64/mm Replace BUG_ON with VM_WARN_ON_ONCE | arm | N-A | (trivial 硬化) | — | .../20260430053859.890613-1-... |
| 75 | mm reduce mmap_lock contention page fault | generic | **PORTABLE** | 通用 mm fault/filemap 重试 | `mm/filemap,memory` | .../20260430040427.4672-5-... |
| 76 | Optimize this_cpu_*() non-x86 (ARM64) | arm | **PORTABLE**+PATTERN | 通用 mm/percpu 专用区 | `mm/percpu`；arm impl PATTERN | .../20260429170758.3018959-6-... |
| 77 | POE sigreturn fix and extra tests | arm | N-A | — arm POE/POR | — | .../20260427-poe_signal-v2-1-... |
| 78 | mm/page_alloc fix tags huge zero folio | generic | N-A | — MTE tag 初始化 | — | .../20260421-zerotags-v2-1-... |
| 79 | arm64 C1-Pro erratum 4193714 backport | arm | N-A | — errata | — | .../20260421100018.335793-6-... |
| 80 | KVM arm64 unsupported guest granule sizes | arm | N-A | — KVM nested granule | — | .../20260414000334.3947257-3-... |
| 81 | mm split file's i_mmap tree for NUMA | generic | **PORTABLE** | 通用 mm i_mmap | `mm/` | .../20260413062042.804-4-... |
| 82 | test mm/arm pgtable remove young check (RFC) | generic | **PORTABLE** | 通用 debug_vm_pgtable 测试 | `mm/debug_vm_pgtable.c` | .../20260410114336.983057-1-... |
| 83 | mm/arm pgtable remove young bit pte_valid_user | generic | **PORTABLE** | 通用 debug_vm_pgtable | `mm/debug_vm_pgtable.c` | .../20260409125446.981747-1-... |
| 84 | arm64 rsi linear-map alias realm config | arm | N-A | — arm RSI/CCA | — | .../20260407152900.396431-1-... |
| 85 | arm64 C1-Pro erratum CVE-2026-0995 | arm | N-A | — errata | — | .../20260407102848.2266988-4-... |
| 86 | arm64 mm set_memory_encrypted vmalloc (RFC) | arm | N-A | — arm CC/encrypt | (`pageattr.c` 若将来 CoCo) | .../20260406213317.216171-1-... |
| 87 | iommu/rockchip fix v2 IOMMU pgtable flags | generic | N-A | — SoC IOMMU 驱动 | — | .../20260331075010.1463-1-... |
| 88 | Fix bugs realm guest + BBML2_NOABORT | arm | PATTERN | 大 leaf 映射处理(realm N-A) | `mm/init.c`,`pageattr.c` | .../20260330161705.3349825-4-... |
| 89 | KVM arm64 protected guest memory pKVM | arm | N-A | — pKVM | — | .../20260330144841.26181-38-... |
| 90 | kasan sw_tags arithmetic shift + arch-generic | arm | **PORTABLE** | KASAN SW_TAGS 架构无关化 | `kasan_init.c`,`asm/kasan*.h`,Kconfig | .../6080be7964fc726327186d5bf7979e16ddd282bb...@... |
| 91 | KVM arm64 stage-2 mmu teardown cleanups | arm | N-A | — KVM arm stage-2 | — | .../20260328145439.2501562-2-... |
| 92 | KVM arm64 ptdump init parser_state | arm | N-A | — KVM ptdump | — | .../20260328053155.12219-1-... |
| 93 | KVM arm64 page-table lifetime fixes | arm | N-A | — KVM arm | — | .../20260327192758.21739-3-... |
| 94 | KVM arm64 Combined user_mem_abort rework | arm | N-A | — KVM arm stage-2 fault | — | .../20260327113618.4051534-15-... |
| 95 | soc fsl qe panic on ioremap failure | generic | N-A | — SoC 驱动 | — | .../tencent_FED49CF5331CC0C7910618883332A08E2606@... |
| 96 | arm64/kvm eager hugepage splitting HDBSS | arm | N-A | — arm HW | — | .../acQna2hLwdr1juTN@devkitleo/ |
| 97 | exec inherit HWCAPs from parent process | arm | **PORTABLE** | 通用 exec/mm HWCAP 继承 | `fs/exec.c`,`mm`; riscv hwcap | .../20260323175340.3361311-2-... |
| 98 | arm64 mm __ptep_set_access_flags hint TTL | arm | N-A | — arm TTL/TLBI level | — | .../20260323163918.2028109-1-... |
| 99 | memblock improve late freeing reserved | other | **PORTABLE** | 通用 memblock free_reserved | `mm/memblock.c` | .../20260323074836.3653702-5-... |
| 100 | change young flag check functions to bool | generic | **PORTABLE** | 通用 mm young 接口(riscv 已 bool) | `pgtable.h`(已 bool) | .../a668b9a974c0d675e7a41f6973bcbe3336e8b373...@... |
| 101 | mm expand mmap_prepare functionality | generic | **PORTABLE** | 通用 mm mmap_prepare | `mm/mmap,vma` | .../4c5e98297eb0aae9565c564e1c296a112702f144...@... |
| 102 | arm64 mm Use generic enum pgtable_level | arm | PATTERN | 采用通用 enum pgtable_level | `pgtable.h`,`ptdump.c` | .../20260318092543.73331-1-... |
| 103 | KVM arm64 nv Expose shadow pgtables debugfs | arm | N-A | — KVM nested | — | .../20260317182638.1592507-3-... |
| 104 | KVM arm64 scoped resource guard EL1/EL2 | arm | N-A | (guard() 通用惯用法)；pKVM hyp | — | .../20260316-tabba-el2_guard-v1-6-... |
| 105 | arm lpae fix non-atomic pte update | arm | N-A | — ARM32 LPAE | — | .../20260315004746.GA32062@udknight/ |
| 106 | arm64/mm contpte-sized exec folios 16K/64K | arm | **PORTABLE** | 通用 exec folio 对齐(Svnapot) | `mm/`,`fs/exec`; Svnapot | .../20260310145406.3073394-2-... |
| 107 | arm64/mm batched TLB flush unmap_hotplug | arm | PATTERN | 热插拔批量 TLB flush | `mm/tlbflush.c` | .../20260309025725.455004-2-... |
| 108 | mm/page_table_check pass mm_struct (s390) | other | **PORTABLE** | 通用 PTC 接口 | `pgtable.h`(已用 PTC) | .../975007c27f8563e46d66a1fbb4b14ae6a4147edd...@... |
| 109 | KVM arm64 user_mem_abort state-object model | arm | N-A | — KVM arm stage-2 | — | .../20260306140232.2193802-8-... |
| 110 | batched young flag check for MGLRU | arm | **PORTABLE**+PATTERN | 通用 mm MGLRU young 批处理 | `mm/`;`pgtable.h` arch helper | .../ea14af84e7967ccebb25082c28a8669d6da8fe57...@... |
| 111 | arm64 contpte fix set_access_flags SMMU/ATS | arm | N-A | — arm contpte+SMMU | — | .../20260305-contpte-fault-loop-v2-1-... |
| 112 | sparc64 vdso Switch to generic vDSO library | arm | **ALREADY** | riscv 已用 generic vDSO | `arch/riscv/kernel/vdso/` | .../20260304-vdso-sparc64-generic-2-v6-4-... |
| 113 | arm64 Refactor TLB invalidation API | arm | PATTERN | TLBI API C 化重构 | `mm/tlbflush.c`(已清晰) | .../20260302135602.3716920-8-... |
| 114 | arm64/mm Drop TTBR_CNP_BIT/ASID_MASK | arm | N-A | — arm TTBR bits | — | .../20260302064437.2791034-3-... |
| 115 | mm add huge pfnmap remap_pfn_range() | other | **PORTABLE** | 通用 mm PMD 级 huge pfnmap | `pgtable.h`(有 PUD/PMD THP) | .../20260228070906.1418911-4-... |
| 116 | arm64 mm Add PTE_DIRTY back PAGE_KERNEL kexec | arm | N-A | — arm PTE bits | — | .../20260227185544.1482632-1-... |
| 117 | ARM cleanup fault handling | arm | N-A | (ARM32 fault) | — | .../E1vvzcX-0000000Awo0-2KBN@... |
| 118 | ARM Remaining PREEMPT_RT bits | arm | N-A | — ARM32 RT | — | .../20260226111742.3598421-3-... |
| 119 | arm64/mm Describe 52 bits PA TTBRx | arm | N-A | — arm 52-bit PA 文档 | — | .../20260226101135.1915529-1-... |
| 120 | arm64 move kfence pool alloc after acpi | arm | N-A | — arm boot 顺序 | — | .../20260226020748.1282208-1-... |
| 121 | KVM arm64 minor fixes S2 walker | arm | N-A | — KVM nested | — | .../20260225173515.20490-2-... |
| 122 | mm arch/shstk Common shadow stack helper | arm | **PORTABLE** | 通用 vm_mmap_shadow_stack(自带 riscv) | `kernel/usercfi.c`(Zicfiss) | .../20260225161404.3157851-6-... |
| 123 | mm/kasan make kasan=on/off all three modes | arm | **PORTABLE** | 通用 KASAN 运行时开关 | `kasan_init.c`,Kconfig | .../20260225081412.76502-14-... |
| 124 | arm64/mm Describe TTBR1_BADDR_4852_OFFSET | arm | N-A | — arm 文档 | — | .../20260225064028.1525192-1-... |
| 125 | arm64 Fix syzkaller splat ioremap_prot | arm | N-A | (arm ioremap memtype) | — | .../20260223221012.31962-2-... |
| 126 | mm/pgtable page table check on s390 | other | **PORTABLE** | 通用 PTC 接口 | `pgtable.h`(已用 PTC) | .../fa08bb93c20a48884b7836834c79f44b5fb9b8b3...@... |
| 127 | cleanup bitmaps printing in sysfs | other | **PORTABLE** | 通用 lib(非页表) | `lib/` | .../20260219181407.290201-8-... |
| 128 | arm64/mm avoid max_pinned_asids underflow | arm | N-A | — arm ASID | — | .../20260219123007.9101-1-... |
| 129 | arm64/mm harden ASID allocator | arm | PATTERN | ASID 分配器硬化 | `arch/riscv/mm/context.c` | .../20260219113715.8001-1-... |
| 130 | mm/pkeys Remove unused tsk param | generic | **PORTABLE** | 通用 pkeys 接口清理 | `mm/`(riscv 无 pkey 但接口通用) | .../20260219063506.545148-1-... |
| 131 | arm64 tlb Optimize REPEAT_TLBI | arm | N-A | — arm errata workaround | — | .../20260218164348.2022831-2-... |
| 132 | arm64 Speed up boot faster linear map | arm | PATTERN | 线性映射建立提速 | `mm/init.c` | .../20260217133527.2881603-3-... |
| 133 | arm64 hugetlbpage avoid unused warn gcc-16 | arm | N-A | (trivial 编译) | — | .../20260216105432.2381873-1-... |
| 134 | phy apple use local var ioremap | generic | N-A | — SoC 驱动 | — | .../20260215-phy-apple-resource-err-ptr-... |
| 135 | batch check refs + unmapping large folios | arm | **PORTABLE**+PATTERN | 通用 mm rmap 批处理 | `mm/rmap`;`pgtable.h` arch | .../b53a16f67c93a3fe65e78092069ad135edf00eff...@... |
| 136 | arm64 tlb call kvm_call_hyp once (RFC) | arm | N-A | — KVM arm tlb | — | .../42bcdd9100bf4c63b79d2b72bd6db951@... |
| 137 | io-pgtable Arm Mali v10+ GPU format (RFC) | generic | N-A | — Mali GPU io-pgtable | — | .../20260209112542.194140-1-... |
| 138 | arm-smmu-v3 MMU-700 errata restrict | arm | N-A | — SMMU errata | — | .../20260206-smmuv3-v2-1-... |
| 139 | debugobjects+io-pgtable-arm-v7s gcc-16 | generic | N-A | (debugobjects 通用 noted) | — | .../20260203162406.2215716-1-... |
| 140 | arm64 mm fix user prot ioremap_prot access_phys | arm | PATTERN | generic_access_phys prot | `arch/riscv/mm`(ioremap_prot) | .../20260130073807.99474-1-... |
| 141 | cpuset/isolation Honour kthreads affinity | generic | **PORTABLE** | 通用 cpuset/sched(非页表) | `kernel/sched,cpuset` | .../20260125224541.50226-34-... |
| 142 | arm64 mm explicitly use kernel pte ioremap_prot | arm | N-A | — arm ioremap | — | .../20260123030238.835748-1-... |
| 143 | mm rmap skip batched unmapping UFFD vmas | generic | **PORTABLE** | 通用 mm rmap/UFFD | `mm/rmap.c` | .../20260116162652.176054-1-... |
| 144 | KVM selftests align + arm64 MMU cleanup | arm | **PORTABLE** | 通用 KVM selftests(含 riscv patch) | tools/testing KVM | .../20260109082218.3236580-5-... |
| 145 | io-pgtable-arm Drop DMA API for CMOs | generic | N-A | — arm io-pgtable | — | .../20260108113846.56179-1-... |
| 146 | arm64/mm Assert NR_BM_PUD_TABLES | arm | N-A | — arm bootmem | — | .../20260107061606.3160088-1-... |
| 147 | asm-generic Remove pud_user pgtable-nopmd | generic | **PORTABLE** | 通用 asm-generic 页表 | `include/asm-generic` | .../61ef32ebc3ea2e926de2bebecf3b5c3a10989fca...@... |
| 148 | fix mem alloc APIs PREEMPT_RT arm64 | arm | PATTERN | pgtable_alloc_t 线性拆分 | `pageattr.c` split | .../20260105202328.2418990-2-... |
| 149 | arm64/mm Fix annotated branch unbootable | arm | N-A | — arm boot | — | .../20251231-annotated-v1-1-... |
| 150 | KVM selftests Add Nested NPT support | generic | N-A | — x86 nested NPT | — | .../20251230230150.4150236-5-... |
| 151 | arm64 mm fix incorrect CONT_PTES non-batched | arm | N-A | — arm contpte bug | — | .../38f3d9fbd486bdd75874a833a24a8c704b6b5a95...@... |
| 152 | KVM arm64 Fix hyp VA size layout/MMU | arm | N-A | — KVM arm hyp | — | .../20251223193440.1441657-2-... |
| 153 | arm64 mm warn once ioremap on RAM | arm | N-A | (ioremap RAM 检查) | — | .../20251222-arm64_ioremap-v1-1-... |
| 154 | media amphion kmalloc vs vmalloc | generic | N-A | — NXP media 驱动 | — | .../20251222084912.747-1-... |
| 155 | io-pgtable-arm fix size_t signedness | generic | N-A | — arm io-pgtable | — | .../20251219232858.51902-1-... |
| 156 | mm increase lowmem size linux-7.0 | arm | N-A | — ARM32 highmem/lowmem | — | .../20251219161559.556737-5-... |
| 157 | Support page table check on PowerPC | arm | **PORTABLE** | 通用 PTC 重引 addr 参数(触及 riscv) | `pgtable.h` PTC 调用 | .../20251219-pgtable_check_v18rebase-v18-12-... |
| 158 | Nesting support for lazy MMU mode | other | **PORTABLE** | 通用 mm lazy_mmu 框架 | (riscv 未用 lazy_mmu) | .../20251215150323.2218608-15-... |
| 159 | introduce pagetable_alloc_nolock() | arm | **PORTABLE**+PATTERN | 通用 mm pagetable_alloc_nolock | `mm/`;arm impl PATTERN | .../20251212161832.2067134-2-... |
| 160 | Enable vmalloc huge mappings default arm64 | arm | **PORTABLE** | 通用 mm/vmalloc(不对齐 huge size) | `mm/vmalloc`;Svnapot | .../20251212042701.71993-3-... |
| 161 | arm64 linear map randomization PArange (RFC) | arm | N-A | (KASLR 线性映射随机化 arm PArange) | — | .../20251211040935.1288349-2-... |
| 162 | arm64 mm Fix kexec pte_mkwrite_novma | arm | N-A | — arm kexec | — | .../20251204062722.3367201-1-... |
| 163 | arm64 mm prevent ctx switch during idmap | arm | N-A | — arm idmap | — | .../20251202004223.108388-1-... |
| 164 | io-pgtable-arm Add concatenated PGD cases | generic | N-A | — arm io-pgtable | — | .../20251130194506.593700-1-... |
| 165 | arch/arm don't init kasan if disabled | arm | **PORTABLE** | 通用 kasan disable(#123 子集) | `kasan_init.c` | .../20251128033320.1349620-5-... |
| 166 | ARM/mm/fault always goto bad_area | generic | N-A | (ARM32 fault) | — | .../20251127140109.191657-2-... |
| 167 | batched checks references large folios | arm | **PORTABLE**+PATTERN | 通用 mm rmap references | `mm/rmap`;`pgtable.h` arch | .../dde5a9135710d8d883e30e0acadcbf1ae754bf7a...@... |
| 168 | arm64 mm fix direct map use over accounting | arm | N-A | — arm DirectMap 统计 | — | .../20251119235706.1944517-1-... |
| 169 | Introduce meminspect | generic | **PORTABLE** | 通用 kernel 内存自省(非页表) | `kernel/`,`mm/` | .../20251119154427.1033475-2-... |
| 170 | arm64 mm Simplify arch_kfence_init_pool | arm | PATTERN | KFENCE init 简化 | `arch/riscv/mm`(KFENCE) | .../20251119130016.283216-1-... |
| 171 | drm/msm adreno 8xx family | generic | N-A | — GPU 驱动 | — | .../20251118-kaana-gpu-support-v4-22-... |
| 172 | arm tlbflush avoid TLBI broadcast reused | arm | **PORTABLE**+PATTERN | 通用 mm huge pmd spurious fault | `mm/memory`;arm tlbi PATTERN | .../20251114085403.101552-2-... |
| 173 | Enable vmalloc block mappings default arm64 | arm | **PORTABLE** | 通用 mm/vmalloc(不对齐 huge) | `mm/vmalloc`;Svnapot | .../20251112110807.69958-3-... |
| 174 | arm64/mm change_memory_common fix + doc | arm | PATTERN | pageattr 返回值传播 | `pageattr.c` | .../20251112062716.64801-2-... |
| 175 | mm/huge_memory restrict __GFP_ZEROTAGS HW tag | generic | **PORTABLE** | 通用 mm 守卫 MTE 代码 | `mm/huge_memory.c` | .../20251109003613.1461433-1-... |
| 176 | mm/huge_memory initialise tags huge zero folio | generic | N-A | — MTE tags | — | .../20251108191948.684586-1-... |
| 177 | Don't sleep split_kernel_leaf_mapping atomic | arm | PATTERN | 线性映射拆分原子上下文 | `pageattr.c` split | .../20251106160945.3182799-4-... |
| 178 | arm64 kprobes check set_memory_rox return | arm | PATTERN | kprobes set_memory_rox 检查 | `arch/riscv/kernel/probes` | .../20251104214947.799005-1-... |
| 179 | clk mediatek ioremap resource leak | generic | N-A | — SoC 驱动 | — | .../20251104040431.1452-1-... |
| 180 | arm64 mm Don't sleep split_kernel_leaf (v1) | arm | PATTERN | (同 #177 v1) | `pageattr.c` | .../20251103125738.3073566-1-... |
| 181 | Move io-pgtable-arm selftest to KUnit | generic | N-A | — arm io-pgtable 测试 | — | .../20251103123355.1769093-5-... |

---

## 判定要点与纪律说明

- **KVM arm64 stage-2 / nested / pKVM 系列（约 30 条）全部 N-A**：riscv KVM（H 扩展）有独立 G-stage 页表与 SBI 接口，arm64 的 `kvm_pgtable.c`/VTCR/HDBSS/HACDBS/pKVM/nested(NV) 机制无直接对应。少数**通用 KVM 核心/selftests**（#19、#71、#144）判 PORTABLE。
- **arm-SMMU / io-pgtable-arm 系列（约 15 条）N-A**（HW 特定）；仅**通用 iommu 框架接口**（#40/#46 `iova_to_phys_length`）判 PORTABLE（riscv IOMMU 驱动可实现）。
- **errata / 板级 DTS / SoC 驱动 / ARM32 专有（约 25 条）N-A**：riscv 有独立四厂商 errata 框架，不移植 arm 具体 CPU 勘误。
- **勿误报的 ALREADY 邻域**（已按基线判低/PATTERN 增量，非"新可移植"）：Svnapot=contpte（#20/#111/#151 arm contpte bug 判 N-A）、range TLB flush+Svinval（#18/#58/#107/#113 判 PATTERN 增量）、HW A/D=Svade/Svadu、Zicfiss=GCS（#122 通用 helper 仍 PORTABLE，含 riscv patch）、HVO 已 select（#6 通用改进 PORTABLE）、page_table_check 已支持（#108/#126/#157 通用接口变更 PORTABLE）、young 已返回 bool（#100 PORTABLE 接口层）。
- **真实缺口（最高价值）**：KASAN SW_TAGS（#90/#123）、rodata=full 全线性别名 RO（#21/#47）、大块映射合并/BBML2（#29）、ARCH_HAS_COPY_MC（#24）、set_direct_map_ro_noflush（#10）—— 均已用 curl/grep 核实。
