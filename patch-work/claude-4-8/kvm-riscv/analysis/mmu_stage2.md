# MMU / Stage-2 页表 可移植性分析 (Tier B)

> 输入：`kvm-riscv/data/by_category/B_mmu-stage2.jsonl`（44 条系列）
> 核对基线：本地内核树 `/Users/zq/Desktop/patch-work/linux-riscv`（`arch/riscv/kvm/gstage.c` `mmu.c` `tlb.c`，Kconfig）
> 深挖（curl mbox 全文）：#36 #15 #3 #17 #29（另取各系列的通用底座补丁核对 diff 落点）

## 摘要

- **系列总数：44**
- **四态计数**：ALREADY **0** / PORTABLE **4** / PATTERN **14** / N-A **26**
  - PORTABLE（通用底座主导，含 riscv 需跟进的 arch 钩子）：#3、#15、#24、#36
  - PATTERN（机制可复用，需在 `gstage.c`/`mmu.c` 重写）：#7、#9、#10、#16、#17、#27、#29、#30、#32、#33、#37、#39、#40、#41
  - N-A（shadow MMU / TDP-spte / VMX / nested / 机密计算 / arm HDBSS 等硬件专属）：其余 26 条
- **本类结论**：MMU/stage-2 富矿主要在 **mmu_notifier 通用层**（#36 锁语义、#3 无锁 aging）与 **stage-2 生命周期 PATTERN**（#17 拆销时让出 CPU、#29 拆分不清零、#32 eager split 思想）。大量 x86 条目是 shadow MMU / TDP-spte / TDX-private 专属（riscv 无对应），arm 新条目多为 HDBSS/HACDBS 硬件脏位加速（N-A）。

### 本类 Top 候选（按价值排序）

1. **#36 Fix races in `kvm_arch_flush_shadow_all()`** — PORTABLE，通用锁语义修复，**上游补丁已直接改 `arch/riscv/kvm/mmu.c` + `vm.c`**。
2. **#15 KVM Userfault** — PORTABLE（`virt/kvm` 通用底座）+ PATTERN（riscv 需 `KVM_GENERIC_PAGE_FAULT` + `kvm_page_fault` + 缺页钩子）；无 userfaultfd 的 post-copy 迁移/按需分页。
3. **#3 Age SPTEs locklessly** — PORTABLE（`CONFIG_KVM_MMU_NOTIFIER_AGING_LOCKLESS` opt-in）+ PATTERN（riscv `kvm_age_gfn` 无锁化）；MGLRU 性能。
4. **#17 (+#16) Reschedule when destroying stage-2** — PATTERN，riscv 拆销全地址空间不让出 CPU（大 guest 软锁风险）。
5. **#29 Don't zero-allocate split page table** — PATTERN，微优化直接适用 riscv `kvm_riscv_gstage_split_huge`。
6. **#41 Ensure hugepage in slot before max mapping level** — PATTERN 缺陷修复，核对 riscv `fault_supports_gstage_huge_mapping`。
7. **#32 Eager hugepage split（思想）** — PATTERN，对应 riscv「仅 lazy 拆分」缺口（上游与 arm HDBSS 硬件耦合）。

---

## Top 可移植候选（深度）

### #36 KVM: Fix race conditions in kvm_arch_flush_shadow_all()  ★最高置信
- **原补丁**：arch/多架构，5 patches，state=new
  （https://patchwork.kernel.org/project/kvm/patch/20260504224213.1049426-4-jthoughton@google.com/）
- **可移植点**：通用层把「调用 `kvm_arch_flush_shadow_all()` 时须**独占持有 `kvm->mmu_lock`**」这一约定上移到 `virt/kvm/kvm_main.c`，消除 `kvm` 的 mm 销毁（`exit_mm()`）与最后一个 `kvm` 引用释放并发时对页表/缓存的**双重释放**。系列同时改 arm64/loongarch/mips，patch 4/5 是通用改动。
- **riscv 落点**：`arch/riscv/kvm/mmu.c:kvm_arch_flush_shadow_all` → `kvm_riscv_mmu_free_pgd`（mmu.c:683）与 `arch/riscv/kvm/vm.c` 的初始化失败回滚路径。**上游 patch 4/5 的 diff 已经包含 riscv hunk**：删除 `free_pgd` 内部自取锁、改为 `lockdep_assert_held`，并在 `vm.c` 调用点显式加锁。
- **判定**：**PORTABLE**。通用契约变更且 riscv 已被上游纳入；当前本地树 `free_pgd` 仍自取 `write_lock`（未应用该系列），落地即需此协同改动否则将双重加锁。
- **备注**：上游 hunk 基于 riscv 仍用 `spin_lock` 的旧树；当前本地树已是 `rwlock`（`cond_resched_rwlock_write`，gstage.c:440），需按 rwlock 语义微调（`lockdep_assert_held_write`）。当前 riscv 因 `free_pgd` 在锁内检查/清 `kvm->arch.pgd` 尚无该竞态 bug，但契约统一后必须跟进。

### #15 KVM: Introduce KVM Userfault
- **原补丁**：x86+arm，15 patches，state=new
  （https://patchwork.kernel.org/project/kvm/patch/20250618042424.330664-10-jthoughton@google.com/）
- **可移植点**：通用底座（patch 04/15，落 `virt/kvm/kvm_main.c` + `include/linux/kvm_host.h` + `include/uapi/linux/kvm.h`）：新增 `KVM_MEM_USERFAULT` memslot 标志、per-slot `userfault_bitmap`、`KVM_MEMORY_EXIT_FLAG_USERFAULT`、`kvm_do_userfault()`、`kvm_is_userfault_memslot()`，及弱符号 arch 钩子 `kvm_arch_userfault_enabled()`（默认退化为 `kvm_arch_flush_shadow_memslot`）。由 `CONFIG_KVM_GENERIC_PAGE_FAULT` 开关。用于无 userfaultfd 的 post-copy 实时迁移/按需分页。
- **riscv 落点**：
  1) `arch/riscv/kvm/Kconfig` select `KVM_GENERIC_PAGE_FAULT`（当前**未选**）；
  2) 引入统一 `struct kvm_page_fault`（patch 01-03 为 x86/arm 建的通用缺页结构，riscv 目前 `kvm_riscv_mmu_map` 用裸参数，需补）；
  3) 缺页路径 `arch/riscv/kvm/mmu.c:kvm_riscv_mmu_map`（mmu.c:535）在 faultin 前调用 `kvm_is_userfault_memslot()`+`kvm_do_userfault()`，命中则走 `KVM_EXIT_MEMORY_FAULT` 退出。
- **判定**：**PORTABLE**（通用底座一次性生效）+ **PATTERN**（riscv arch 钩子需重写）。arch=x86+arm 表明设计即为跨架构，riscv 属自然扩展。

### #3 KVM: x86/mmu: Age SPTEs locklessly
- **原补丁**：x86，11 patches，state=new
  （https://patchwork.kernel.org/project/kvm/patch/20250204004038.1680123-2-jthoughton@google.com/）
- **可移植点**：通用层新增 `CONFIG_KVM_MMU_NOTIFIER_AGING_LOCKLESS`（`virt/kvm/Kconfig`）+ `struct kvm_gfn_range.lockless`（`include/linux/kvm_host.h`）+ `virt/kvm/kvm_main.c` 的无锁 memslot 遍历，并将 `kvm_handle_hva_range()` 改名/重构（patch 01-02 均为通用）。选中该 config 的架构可在不持 `mmu_lock` 情况下做 aging（MGLRU 回收路径热点）。
- **riscv 落点**：`arch/riscv/kvm/mmu.c:kvm_age_gfn`（mmu.c:264）/`kvm_test_age_gfn`（mmu.c:284）。riscv 已用 `ptep_test_and_clear_young` 且具备 cmpxchg 型 `kvm_riscv_gstage_try_update_pte`（gstage.c:126），可在 `Kconfig` select 该 config 后将 aging 改为无锁（用 `range->lockless` 决定是否加读锁）。
- **判定**：**PORTABLE**（通用 opt-in 基础设施）+ **PATTERN**（riscv 侧 select + 校验其 aging 无锁安全）。

### #17 KVM: arm64: Reschedule as needed when destroying the stage-2 page-tables（含 #16 v1）
- **原补丁**：arm，2 patches，state=new
  （https://patchwork.kernel.org/project/kvm/patch/20250820162242.2624752-2-rananta@google.com/）
- **可移植点**：把 `kvm_pgtable_stage2_destroy()` 拆成 `..._range()`（按地址范围走表/释放）+ `..._pgd()`（释放 PGD），从而可**分块释放大页表并在块间 `cond_resched()`**，避免拆销超大 guest 时长时间持锁导致的软锁/看门狗告警。
- **riscv 落点**：`arch/riscv/kvm/mmu.c:kvm_riscv_mmu_free_pgd`（mmu.c:683）与 `kvm_arch_flush_shadow_memslot`（mmu.c:136）当前都以 `may_block=false` 调 `kvm_riscv_gstage_unmap_range`（gstage.c:404）——**拆销路径不让出 CPU**。而 `unmap_range` 在 `may_block=true` 时**已有** `cond_resched_rwlock_write`（gstage.c:439）。落地非常干净：在拆销路径按 arm64 思想放开让步（分块 + 让出锁）。
- **判定**：**PATTERN**，riscv 缺口明确、复用已有让步原语即可。

### #29 KVM: x86/mmu: Don't zero-allocate page table used for splitting a hugepage
- **原补丁**：x86，1 patch，state=new
  （https://patchwork.kernel.org/project/kvm/patch/20260218210820.2828896-1-seanjc@google.com/）
- **可移植点**：拆分大页时新页表的每个条目都会被写满，故分配不必清零（`get_zeroed_page` → `__get_free_page`），省一次清零。
- **riscv 落点**：`arch/riscv/kvm/gstage.c:kvm_riscv_gstage_split_huge`（gstage.c:306）——其循环（gstage.c:342-345）确实写满 `PTRS_PER_PTE` 个子 PTE；但 riscv 拆分与建表**共用** `vcpu->arch.mmu_page_cache`（`gfp_zero = __GFP_ZERO`，vcpu.c:138），不能全局关闭清零。需为拆分路径引入独立的非清零分配/缓存。
- **判定**：**PATTERN**（微优化，直接适用但受共享缓存约束需小心）。

---

## 全量判定表

| # | 系列 (arch, n) | 判定 | 可移植点 / 理由 | riscv 落点 | web_url |
|---|---|---|---|---|---|
| 1 | Private MMIO for private assigned dev (x86,12) | N-A | dma-buf/vfio 私有 MMIO 供 TDISP/机密设备；仅极小 dma-buf 通用钩子 | — | .../20250107142719.179636-12-yilun.xu@.../ |
| 2 | Ensure NX huge page recovery thread alive (x86,1) | N-A | x86 iTLB-multihit NX 回收线程 | — | .../20250124234623.3609069-1-seanjc@.../ |
| 3 | Age SPTEs locklessly (x86,11) | **PORTABLE**+PATTERN | 通用 `KVM_MMU_NOTIFIER_AGING_LOCKLESS`+无锁 memslot 遍历 | `mmu.c:264/284` aging | .../20250204004038.1680123-2-jthoughton@.../ |
| 4 | more huge page recovery fallout (x86,2) | N-A | vhost_task + NX 回收线程 | — | .../20250226024257.1807282-1-kbusch@.../ |
| 5 | Remove tdp_mmu_for_each_pte() (x86,1) | N-A | x86 TDP MMU 迭代器清理 | — | .../20250226074131.312565-1-nik.borisov@.../ |
| 6 | Wrap sanity check w/ KVM_PROVE_MMU (x86,1) | N-A | x86 TDP 调试断言（弱：调试门控思想） | — | .../20250315023448.2358456-1-seanjc@.../ |
| 7 | Small changes: prefetch & spurious faults (x86,5) | PATTERN(低) | spurious-fault/prefetch 跳过冗余更新之思想；余为 x86 spte/tdp | `gstage.c` 缺页路径 | .../20250318013238.5732-1-yan.y.zhao@.../ |
| 8 | Use kvm_x86_call() instead of static_call() (x86,1) | N-A | x86 调用封装清理 | — | .../20250331182703.725214-1-seanjc@.../ |
| 9 | Prevent hugepages when mem attrs changing (x86,1) | PATTERN(future) | 依赖 `KVM_GENERIC_MEMORY_ATTRIBUTES`（riscv 未选）；随 gmem/mem-attr 到来才相关 | `gstage.c` map 路径 | .../20250430220954.522672-1-seanjc@.../ |
| 10 | Introduce RET_PF_RETRY_INVALID_SLOT (x86,2) | PATTERN(低) | x86 缺页返回码；附带可移植 selftest（prefault+并发删 memslot） | `mmu.c` faultin;selftests | .../20250519023815.30384-1-yan.y.zhao@.../ |
| 11 | VMX MMIO Stale Data Mitigation (x86,5) | N-A | VMX CPU 勘误缓解；irqbypass revert | — | .../20250523011756.3243624-6-seanjc@.../ |
| 12 | TDISP using TSM (x86,30) | N-A | 机密计算（TSM/TDISP）；仅 gmem 底座 | — | .../20250529053513.1592088-29-yilun.xu@.../ |
| 13 | Embed direct bits into gpa for PRE_FAULT_MEMORY (x86,1) | N-A | TDX `gfn_shared_mask`；riscv 无 PRE_FAULT_MEMORY 与 direct bits | — | .../20250611001018.2179964-1-xiaoyao.li@.../ |
| 14 | Reject direct bits in gpa for PRE_FAULT_MEMORY (x86,1) | N-A | 同上，TDX direct bits | — | .../20250612044943.151258-1-pbonzini@.../ |
| 15 | Introduce KVM Userfault (x86+arm,15) | **PORTABLE**+PATTERN | 通用 `KVM_MEM_USERFAULT`/`kvm_do_userfault`/弱钩子（virt/kvm）；无 uffd 的 post-copy | Kconfig+`kvm_page_fault`+`mmu.c:535` | .../20250618042424.330664-10-jthoughton@.../ |
| 16 | arm64 Destroy stage-2 periodically (arm,2) | PATTERN | #17 之 v1；拆销分块+cond_resched | `mmu.c:683/136` `gstage.c:404` | .../20250724235144.2428795-2-rananta@.../ |
| 17 | arm64 Reschedule when destroying stage-2 (arm,2) | **PATTERN** | 拆销分块让出 CPU，复用已有 `cond_resched_rwlock_write` | `mmu.c:683/136` `gstage.c:439` | .../20250820162242.2624752-2-rananta@.../ |
| 18 | vhost_task NX recovery race (x86,3) | N-A | x86 NX 回收线程生命周期 | — | .../20250826004012.3835150-3-seanjc@.../ |
| 19 | vhost_task NX recovery race v2 (x86,3) | N-A | 同 #18 | — | .../20250827194107.4142164-3-seanjc@.../ |
| 20 | arm64 nv Optimize unmap shadow S2 (arm,1) | N-A | 嵌套虚拟化 shadow S2 | — | .../20250905062929.1741536-1-gankulkarni@.../ |
| 21 | Skip MMIO SPTE invalidation if mmio_caching=0 (x86,1) | N-A | x86 MMIO SPTE 缓存 | — | .../20250926135139.1597781-1-dmaluka@.../ |
| 22 | Move export of kvm_zap_gfn_range() (x86,1) | N-A | x86 导出符号移动 | — | .../20251021114345.159372-1-kai.huang@.../ |
| 23 | Don't read guest CR3 async pf MMU direct (x86,1) | N-A | x86 async_pf + CR3 | — | .../20251212135051.2155280-1-xiaoyao.li@.../ |
| 24 | selftests alignment fixes + arm64 MMU cleanup (arm,5) | **PORTABLE** | selftests；**已含 riscv patch**（page_align 取整）+ 共享头 | `tools/.../selftests/kvm/riscv` | .../20260109082218.3236580-5-tabba@.../ |
| 25 | Don't check old SPTE perms when unsync (x86,2) | N-A | shadow-paging unsync | — | .../20260123090304.32286-1-jiangshanlai@.../ |
| 26 | move reused pages to top of active_mmu_pages (x86,1) | N-A | shadow MMU LRU | — | .../20260129030231.567759-1-someguy@.../ |
| 27 | targeted TLB sync IPIs for lockless PT walkers (x86,3) | PATTERN(低) | core mm + x86/tlb arch 钩子；非 KVM-gstage | `arch/riscv/.../tlbflush` | .../20260202074557.16544-3-lance.yang@.../ |
| 28 | arm64 nv Avoid NV stage-2 when NV unsupported (arm,1) | N-A | 嵌套虚拟化 | — | .../20260202152310.113467-1-tabba@.../ |
| 29 | Don't zero-allocate split page table (x86,1) | **PATTERN** | 拆分页表全写满，免清零 | `gstage.c:306`（split 专用非清零分配） | .../20260218210820.2828896-1-seanjc@.../ |
| 30 | Don't create SPTEs for addresses not mappable (x86,1) | PATTERN(低) | 缺页路径可映射性校验 | `mmu.c:615` faultin | .../20260219002241.2908563-1-seanjc@.../ |
| 31 | Fix base gfn check when zapping private huge SPTE (x86,1) | N-A | TDX private SPTE | — | .../20260309083844.217215-1-pcj3195161583@.../ |
| 32 | arm64 eager hugepage split if HDBSS (arm,1) | PATTERN | **eager split 思想**（上游与 HDBSS 硬件耦合）；riscv 仅 lazy | `gstage.c:306` + `mmu.c:19` wp 路径 | .../acQna2hLwdr1juTN@devkitleo/ |
| 33 | Only WARN in direct MMUs when overwriting SPTE (x86,1) | PATTERN(低) | WARN 作用域/健壮性 | `gstage.c:140` set_pte | .../20260330074909.140480-2-pbonzini@.../ |
| 34 | Drop/zap present SPTE when creating MMIO SPTE (x86,1) | N-A | x86 MMIO SPTE 缺陷 | — | .../20260330080144.158592-1-pbonzini@.../ |
| 35 | KVM Dirty-bit cleaning accelerator HACDBS (arm,12) | N-A | arm FEAT_HACDBS 硬件脏位加速（内含 eager-split=PATTERN 思想） | — | .../20260430111424.3479613-4-leo.bras@.../ |
| 36 | Fix races in kvm_arch_flush_shadow_all() (arm/多,5) | **PORTABLE** | 通用「caller 独占 mmu_lock」契约；**patch 已改 riscv mmu.c+vm.c** | `mmu.c:131/683` `vm.c` | .../20260504224213.1049426-4-jthoughton@.../ |
| 37 | Expose shadow MMU pages as a stat (x86,1) | PATTERN(低) | binary-stats 已有；riscv 可暴露 gstage 页数 | `vm.c` stats | .../20260612133727.411902-1-seanjc@.../ |
| 38 | x86.{c,h} spring cleaning (x86,30) | N-A | x86 文件重构 | — | .../20260613000329.732085-10-seanjc@.../ |
| 39 | Bug the VM not host if WP upper SPTEs (x86,1) | PATTERN(低) | `KVM_BUG_ON` 卫生（杀 VM 而非 host） | `gstage.c:359` op_pte WP | .../20260618185641.2022368-1-seanjc@.../ |
| 40 | don't kill VM on disabled passthrough BAR (x86,1) | PATTERN(低) | MMIO 模拟而非杀 VM | `vcpu_exit.c` MMIO | .../20260621133708.3454718-2-mike.malyshev@.../ |
| 41 | Ensure hugepage in slot before max mapping level (x86,1) | **PATTERN** | 映射级别校验缺陷；核对 riscv 是否同样受影响 | `mmu.c:304` `fault_supports_gstage_huge_mapping` | .../20260626112437.1777775-2-pbonzini@.../ |
| 42 | fixes for CVE-2026-46113 (shadow paging) (x86,8) | N-A | shadow-paging UAF；riscv 无 shadow paging | — | .../20260626174620.1819772-2-pbonzini@.../ |
| 43 | KVM Dirty-bit cleaning hw accelerator HACDBS v2 (arm,13) | N-A | 同 #35（arm 硬件） | — | .../20260629111820.1873540-2-leo.bras@.../ |
| 44 | Support FEAT_HDBSS (Armv9.5) (arm,6) | N-A | arm 硬件脏位状态；内含 eager-split=PATTERN 思想 | — | .../20260709104026.2612599-3-zhengtian10@.../ |

---

## 针对 lead 关注缺口的专项结论

- **大页 eager split（预先拆分）**：本批的 eager-split 系列（#32/#35/#44）均**与 arm HDBSS/HACDBS 硬件耦合**，硬件部分 N-A；可移植的是「dirty-log 开启时预拆整个 memslot」这一 **PATTERN**。落点：`mmu_wp_memory_region`（mmu.c:19，当前只 wp 不拆）+ 复用已存在的 `kvm_riscv_gstage_split_huge`（gstage.c:306，当前仅 gstage.c:274 lazy 调用）。本批无「纯通用 eager-split」独立系列，可参照 x86 `tdp_mmu.c`/arm64 `hyp/pgtable.c` 既有实现重写。
- **关闭 dirty-log 后回收/合并大页**：确认缺口——gstage.c:264 注释「freeing the page tables (not support now)」。本批的 x86「NX huge page recovery」系列（#2/#4/#18/#19）属 **iTLB-multihit 缓解专属**（N-A），并非「dirty-log 关闭后 collapse」。故本批不提供可移植补丁；缺口成立，PATTERN 参考为 x86/arm 的 recovery 机制，需在 ioctl（关闭 dirty-log）上下文新增 collapse 逻辑。
- **dirty-log 性能 / mmu_notifier / gfn-range 失效（通用层）**：#3（无锁 aging）与 #36（flush_shadow_all 锁语义）是本类真正的通用层 **PORTABLE** 项；#17（拆销让步）为相邻性能/健壮性 PATTERN。
- **x86 shadow MMU / TDP-spte / TDX-private 专属**：#5/#7/#21/#25/#26/#31/#34/#42 等（spte/rmap/unsync/mmio-spte/private-spte）riscv 无对应结构 → N-A 或极低价值 PATTERN。
