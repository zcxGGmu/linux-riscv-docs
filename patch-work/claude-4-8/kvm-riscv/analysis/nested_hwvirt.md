# 嵌套虚拟化 + HW 虚拟化引擎/世界切换 可移植性分析

> 类别：Tier C — nested（126 条）+ hw-virt-engine（11 条），共 **137 条**。
> 判定基调：riscv KVM **无嵌套虚拟化**、**无 VMX/SVM 式世界切换**，绝大多数判 **N-A**。
> 基线核对（本地树 `/Users/zq/Desktop/patch-work/linux-riscv`）：
> - `arch/riscv/kvm/vcpu_sbi_replace.c:130`：`Until nested virtualization is implemented, the SBI HFENCE calls should return not supported` —— 嵌套 HFENCE 一律 `SBI_ERR_NOT_SUPPORTED`。
> - `arch/riscv/kvm/` 全树无 `vmcs12/vmcb/EPT/NPT/nested_ops/EL2` 概念；`nested` 仅出现在 NACL（`nacl.c`，SBI **嵌套加速 shim**，非嵌套虚拟化）与 `vcpu_switch.S:232` 注释。
> - riscv 世界切换 = H 扩展 VS-mode + NACL，**无** `__vmx_vcpu_run`/`vmenter.S`/`vmcb` 式引擎。
> - `arch/riscv/kvm/Kconfig` **未** `select KVM_GENERIC_PRE_FAULT_MEMORY`（仅 x86 有）。
> - riscv stage-2 缺页处理器 = `arch/riscv/kvm/mmu.c:537 kvm_riscv_gstage_map()`，形态与 arm64 `user_mem_abort()` 同（`vma_lookup`/`hugetlb shift`/`mmu_seq`/`__kvm_faultin_pfn`）。

## 摘要

- **系列总数**：137（nested 126 + hw-virt-engine 11）。
- **四态计数**：ALREADY 0 / PORTABLE 0 / **PATTERN 6** / **N-A 131**。
  - PATTERN 6 条中，纯嵌套硬件相关的仅是「未来参考」性质（selftests 脚手架）；真正有当下价值的是被**误归入 nested** 的 stage-2 缺页/预取内存改动。
- **N-A 主因**（131 条）：nVMX（vmcs12/VM-Enter-Exit 一致性/EPT）、nSVM（vmcb12/VMRUN/NPT/LBRV/AVIC）、arm64-NV（EL2 寄存器/VNCR/影子 stage-2/GIC-NV）、x86 CPU 缓解（IBPB/RSB/Spectre）、x86 世界切换汇编（vmenter/SPEC_CTRL/DEBUGCTL）、kvm-unit-tests/selftests 的 x86/arm 专有用例、Hyper-V/Xen、FRED/APX/SGX/CET/SMM 等 x86 特性在嵌套语境下的处理。riscv 均无对应硬件，且不扩展通用底座 → 不可移植。

### 本类 Top 候选（按当下价值排序）

| # | 系列 | 判定 | 一句话 |
|---|---|---|---|
| 1 | [113] KVM: arm64: Add KVM_PRE_FAULT_MEMORY support | **PATTERN**（底座 PORTABLE） | **误归 nested**；实为通用 `KVM_GENERIC_PRE_FAULT_MEMORY` opt-in，riscv 可照方抓药 |
| 2 | [82/91] KVM: arm64: Refactor user_mem_abort() → state-object model | **PATTERN** | **误归 nested**；stage-2 缺页处理器状态对象化重构，直接映射 riscv `gstage_map()` |
| 3 | [79] KVM: arm64: Fix latent bugs in user_mem_abort() | **PATTERN** | 缺页处理器 bug 类（原子缺页页泄漏），riscv `gstage_map()` 应自查 |
| 4 | [100] KVM: arm64: selftests: Basic nested guest support | PATTERN（未来/低） | 嵌套 guest selftests 脚手架模板；**riscv 嵌套尚未实现，仅供未来参考** |
| 5 | [96] arm64: kvm-unit-tests Stage-2 MMU + Nested Guest Framework | PATTERN（未来/低） | 嵌套测试基础库模板；**riscv 嵌套尚未实现，仅供未来参考** |

> 注：Top1/Top2/Top3 严格说属 **mmu-stage2** 主题，因补丁触及「nested hwpoison / nested VMA shift」被打上 nested 标签而落入本批。已在此标注，供主代理与 mmu-stage2 归口去重。

## Top 可移植候选（深度）

### 1. KVM: arm64: Add KVM_PRE_FAULT_MEMORY support（PATTERN，底座 PORTABLE）
- **原补丁**：`arm64: Add KVM_PRE_FAULT_MEMORY support`（https://patchwork.kernel.org/project/kvm/patch/20260612162354.73378-3-jackabt.amazon@gmail.com/）状态=new，arch=arm。
- **可移植点**：`KVM_PRE_FAULT_MEMORY` 的**通用 ioctl/CAP 机制已在 `virt/kvm/kvm_main.c`**（`KVM_GENERIC_PRE_FAULT_MEMORY`）。启用只需两步：① `select KVM_GENERIC_PRE_FAULT_MEMORY`；② 实现 arch 钩子 `kvm_arch_vcpu_pre_fault_memory()`。curl 全文确认（178 insertions）：
  - `arch/arm64/kvm/Kconfig`：`+ select KVM_GENERIC_PRE_FAULT_MEMORY`；
  - `case KVM_CAP_PRE_FAULT_MEMORY:` 广告能力；
  - `long kvm_arch_vcpu_pre_fault_memory(struct kvm_vcpu *, struct kvm_pre_fault_memory *range)` 循环调用 stage-2 map；
  - 唯一「nested」内容是 patch 5/5 的 selftest。
- **riscv 落点**：`arch/riscv/kvm/Kconfig`（select）＋ `arch/riscv/kvm/mmu.c`（新增 `kvm_arch_vcpu_pre_fault_memory()`，复用 `kvm_riscv_gstage_map()` 路径，mmu.c:537）＋ `arch/riscv/kvm/vcpu.c`/`vm.c`（`KVM_CAP_PRE_FAULT_MEMORY` 广告）。已核对：riscv 现**未** select，且已有 `kvm_riscv_gstage_map()` 可复用。
- **判定**：**PATTERN**——通用底座（ioctl/CAP）为 **PORTABLE**（riscv 仅需 opt-in），arch 侧钩子约 ~150 行按 arm64 蓝本重写。与基线「pre-fault memory ⚠️ 可 opt-in」缺口吻合。

### 2. KVM: arm64: Refactor user_mem_abort() into a state-object model（PATTERN）
- **原补丁**：v1 `Refactor user_mem_abort() into a state-object model`（https://patchwork.kernel.org/project/kvm/patch/20260306140232.2193802-8-tabba@google.com/）；v2 `Combined user_mem_abort() rework`（https://patchwork.kernel.org/project/kvm/patch/20260327113618.4051534-15-maz@kernel.org/）。状态=new，arch=arm。
- **可移植点**：把庞大的 stage-2 缺页处理器拆成状态对象 `struct kvm_s2_fault` + 一组提取函数（`kvm_s2_fault_get_vma_info()` 隔离 `mmap_read_lock`、PFN 解析、stage-2 权限、页表映射各成独立步骤）。这是**架构无关的代码组织模式**，不依赖 arm64 硬件。
- **riscv 落点**：`arch/riscv/kvm/mmu.c` 的 `kvm_riscv_gstage_map()`（mmu.c:537–650）。已核对其形态与 `user_mem_abort()` 一致（`vma_lookup`/`is_vm_hugetlb_page`/`huge_page_shift`/`mmu_invalidate_seq`/`__kvm_faultin_pfn`），随功能增长同样面临可读性/可测性压力，可套用同一状态对象重构。
- **判定**：**PATTERN**——纯组织重构，riscv 侧重写，中等价值（可读性/为将来 pre-fault、eager-split 等打基础）。

### 3. KVM: arm64: Fix a couple of latent bugs in user_mem_abort()（PATTERN）
- **原补丁**：`Fix a couple of latent bugs in user_mem_abort()`（https://patchwork.kernel.org/project/kvm/patch/20260304162222.836152-3-tabba@google.com/）状态=new，arch=arm。
- **可移植点**：`[1/2] Fix page leak in user_mem_abort() on atomic fault`——原子缺页路径下的页引用泄漏，是**跨架构缺页处理器的通用 bug 类**（`[2/2]` 的 vma_shift/nested hwpoison 属 arm-NV，不移植）。
- **riscv 落点**：`arch/riscv/kvm/mmu.c` `kvm_riscv_gstage_map()`——应审计 `__kvm_faultin_pfn()` 返回后各错误/原子分支是否有对称的 `kvm_release_page`/`put_page`。
- **判定**：**PATTERN**——bug 类自查，低-中价值。

### 4–5. 嵌套 selftests / kvm-unit-tests 脚手架（PATTERN，未来/低）
- **[100]** `KVM: arm64: selftests: Basic nested guest support`（https://patchwork.kernel.org/project/kvm/patch/20260516183003.799058-6-weilin.chang@arm.com/）：`hello_nested`、`shadow_stage2` 等嵌套 guest 测试脚手架（GPR 保存/恢复、guest hypervisor 辅助、L2 栈池）。
- **[96]** `arm64: Add Stage-2 MMU and Nested Guest Framework`（kvm-unit-tests，https://patchwork.kernel.org/project/kvm/patch/20260413204630.1149038-8-jingzhangos@google.com/）：stage-2 页表管理库 + guest 执行/异常框架。
- **可移植点/落点**：两者提供「如何在 selftests/kut 中构造并运行嵌套 guest」的**方法论模板**，若 riscv 未来实现 H-in-VS 嵌套，可参照在 `tools/testing/selftests/kvm/riscv/` 建同类脚手架。
- **判定**：**PATTERN（未来参考）**——**riscv 嵌套尚未实现**，当前无落点，优先级低。

## 全量判定表（137 条）

### nested（126 条）

| # | 系列 | 判定 | 可移植点 / riscv落点（若有） | web_url |
|---|---|---|---|---|
| 1 | nVMX: Always use TLB_FLUSH_GUEST for nested VM-Enter/VM-Exit | N-A | nVMX 专有 | https://patchwork.kernel.org/project/kvm/patch/20250116035008.43404-1-yosryahmed@google.com/ |
| 2 | nSVM: Enter guest mode before initializing nested NPT MMU | N-A | nSVM/NPT 专有 | https://patchwork.kernel.org/project/kvm/patch/20250130010825.220346-1-seanjc@google.com/ |
| 3 | x86: Fix emulation of (some) L2 instructions | N-A | nVMX/nSVM 指令截获模拟 | https://patchwork.kernel.org/project/kvm/patch/20250201015518.689704-4-seanjc@google.com/ |
| 4 | x86: LA57 canonical testcases | N-A | kvm-unit-tests，x86 LA57/nVMX | https://patchwork.kernel.org/project/kvm/patch/20250215013018.1210432-3-seanjc@google.com/ |
| 5 | KVM: arm64: NV userspace ABI | N-A | arm-NV（ID_AA64MMFR NV/E2H/HCR_EL2） | https://patchwork.kernel.org/project/kvm/patch/20250220134907.554085-7-maz@kernel.org/ |
| 6 | VMX: Reject KVM_RUN if userspace forces emulation during nested VM-Enter | N-A | nVMX 专有 | https://patchwork.kernel.org/project/kvm/patch/20250224171409.2348647-1-seanjc@google.com/ |
| 7 | x86: nVMX IRQ fix and VM teardown cleanups | N-A | nVMX + x86 拆除顺序；仅 1 条通用 vCPU 可见性断言，不值单独移植 | https://patchwork.kernel.org/project/kvm/patch/20250224235542.2562848-2-seanjc@google.com/ |
| 8 | KVM: arm64: Add NV GICv3 support | N-A | arm-NV GICv3（ICH_*_EL2） | https://patchwork.kernel.org/project/kvm/patch/20250225172930.1850838-9-maz@kernel.org/ |
| 9 | VMX: Clean up EPT_VIOLATIONS_xxx defines | N-A | nVMX EPT | https://patchwork.kernel.org/project/kvm/patch/20250227000705.3199706-2-seanjc@google.com/ |
| 10 | IBPB cleanups and a fixup | N-A | x86 分支预测缓解（IBPB） | https://patchwork.kernel.org/project/kvm/patch/20250227012712.3193063-7-yosry.ahmed@linux.dev/ |
| 11 | x86: nSVM: Fix a bug with nNPT+x2AVIC | N-A | kvm-unit-tests，nSVM+AVIC | https://patchwork.kernel.org/project/kvm/patch/20250304211223.124321-3-seanjc@google.com/ |
| 12 | nVMX: Check MSR load/store list counts during VM-Enter | N-A | nVMX 一致性检查 | https://patchwork.kernel.org/project/kvm/patch/20250315024402.2363098-1-seanjc@google.com/ |
| 13 | VMX: Flush shadow VMCS on emergency reboot | N-A | nVMX 影子 VMCS | https://patchwork.kernel.org/project/kvm/patch/20250324140849.2099723-1-chao.gao@intel.com/ |
| 14 | KVM: Improve VMware guest support | N-A | x86 VMware backdoor hypercall（含 nested backdoor）| https://patchwork.kernel.org/project/kvm/patch/20250422161304.579394-2-zack.rusin@broadcom.com/ |
| 15 | x86: allow DEBUGCTL FREEZE_IN_SMM passthrough | N-A | nVMX + SMM/DEBUGCTL | https://patchwork.kernel.org/project/kvm/patch/20250522005555.55705-6-mlevitsk@redhat.com/ |
| 16 | x86/mmu: Exempt nested EPT from !USER, CR0.WP=0 logic | N-A | 嵌套 EPT 影子 MMU | https://patchwork.kernel.org/project/kvm/patch/20250602234851.54573-1-seanjc@google.com/ |
| 17 | x86: nSVM: Use PT_* macro for NPT tests | N-A | kvm-unit-tests，nSVM NPT | https://patchwork.kernel.org/project/kvm/patch/20250603044745.1387718-1-eiichi.tsukata@nutanix.com/ |
| 18 | x86: FEP related cleanups and fix | N-A | kvm-unit-tests，强制模拟/nVMX | https://patchwork.kernel.org/project/kvm/patch/20250604183623.283300-5-seanjc@google.com/ |
| 19 | x86/svm: Make nSVM MSR test useful | N-A | kvm-unit-tests，nSVM MSRPM | https://patchwork.kernel.org/project/kvm/patch/20250605192226.532654-2-seanjc@google.com/ |
| 20 | VMX: Add support for FRED context save/restore（+nVMX FRED）| N-A | x86 FRED + nVMX | https://patchwork.kernel.org/project/kvm/patch/20250802171518.3676800-1-xin@zytor.com/ |
| 21 | arm64: Correctly populate FAR_EL2 on nested SEA injection | N-A | arm-NV（FAR_EL2） | https://patchwork.kernel.org/project/kvm/patch/20250813163747.2591317-1-maz@kernel.org/ |
| 22 | x86: Backports for 6.1.y | N-A | x86 backport（nVMX/x2AVIC/APIC） | https://patchwork.kernel.org/project/kvm/patch/20250815001205.2370711-7-seanjc@google.com/ |
| 23 | x86: Backports for 6.6.y | N-A | x86 backport（hyperv/nVMX/APIC） | https://patchwork.kernel.org/project/kvm/patch/20250815002540.2375664-7-seanjc@google.com/ |
| 24 | x86: Backports for 6.12.y | N-A | x86 backport（DEBUGCTL/nVMX） | https://patchwork.kernel.org/project/kvm/patch/20250815005725.2386187-5-seanjc@google.com/ |
| 25 | arm64: GICv5 legacy (GCIE_LEGACY) NV enablement | N-A | arm-NV GICv5 | https://patchwork.kernel.org/project/kvm/patch/20250828105925.3865158-2-sascha.bischoff@arm.com/ |
| 26 | arm64: nested: Fix VA sign extension in VNCR/TLBI paths | N-A | arm-NV VNCR | https://patchwork.kernel.org/project/kvm/patch/20250901141551.57981-1-wlsrbwjd7232@gmail.com/ |
| 27 | KVM: Improve nested VMX performance | N-A | nVMX（L1 MSR bitmap/APIC 缓存）；pfncache 虽通用但仅服务嵌套 | https://patchwork.kernel.org/project/kvm/patch/20250908213241.3189113-2-griffoul@infradead.org/ |
| 28 | nVMX: Mark APIC access page dirty when syncing vmcs12 pages | N-A | nVMX APIC | https://patchwork.kernel.org/project/kvm/patch/20250910085156.1419090-1-griffoul@gmail.com/ |
| 29 | selftests: SET_NESTED_STATE 48-bit L2 on 57-bit L1 | N-A | selftests x86 nested（LA57）；页表 loop 重构极少量通用 | https://patchwork.kernel.org/project/kvm/patch/20250917215031.2567566-4-jmattson@google.com/ |
| 30 | VMX: EPTP cleanups and nVMX fixes | N-A | nVMX EPTP | https://patchwork.kernel.org/project/kvm/patch/20250919005955.1366256-2-seanjc@google.com/ |
| 31 | SVM: Aggressively clear vmcb02 clean bits | N-A | nSVM vmcb | https://patchwork.kernel.org/project/kvm/patch/20250922162935.621409-3-jmattson@google.com/ |
| 32 | nVMX: Use vcpu instead of vmx->vcpu | N-A | nVMX 清理 | https://patchwork.kernel.org/project/kvm/patch/20250924145421.2046822-1-xin@zytor.com/ |
| 33 | x86: selftests: add L1TF exploit test | N-A | selftests x86（L1TF）| https://patchwork.kernel.org/project/kvm/patch/20251013-l1tf-test-v1-2-583fb664836d@google.com/ |
| 34 | Extend test coverage for nested SVM | N-A | selftests x86 nSVM | https://patchwork.kernel.org/project/kvm/patch/20251021074736.1324328-18-yosry.ahmed@linux.dev/ |
| 35 | nSVM: Fixes for SVM_EXIT_CR0_SEL_WRITE injection | N-A | nSVM | https://patchwork.kernel.org/project/kvm/patch/20251024192918.3191141-2-yosry.ahmed@linux.dev/ |
| 36 | selftests: SET_NESTED_STATE 48-bit L2 on 57-bit L1（v2）| N-A | selftests x86 nested | https://patchwork.kernel.org/project/kvm/patch/20251028225827.2269128-3-jmattson@google.com/ |
| 37 | Fix triple fault in eventinj test | N-A | kvm-unit-tests x86 | https://patchwork.kernel.org/project/kvm/patch/20251030073724.259937-3-chao.gao@intel.com/ |
| 38 | Misc fixups/cleanups for nested tests | N-A | kvm-unit-tests nVMX/nSVM | https://patchwork.kernel.org/project/kvm/patch/20251104193016.3408754-5-yosry.ahmed@linux.dev/ |
| 39 | nSVM: Improve virtualization of VMCB12 G_PAT | N-A | nSVM PAT | https://patchwork.kernel.org/project/kvm/patch/20251107201151.3303170-5-jmattson@google.com/ |
| 40 | SVM: LBR virtualization fixes | N-A | nSVM LBRV | https://patchwork.kernel.org/project/kvm/patch/20251108004524.1600006-5-yosry.ahmed@linux.dev/ |
| 41 | x86: Support APX feature for guests | N-A | x86 APX + nVMX 指令信息 | https://patchwork.kernel.org/project/kvm/patch/20251110180131.28264-18-chang.seok.bae@intel.com/ |
| 42 | Improvements for (nested) SVM testing | N-A | kvm-unit-tests nSVM | https://patchwork.kernel.org/project/kvm/patch/20251110232642.633672-13-yosry.ahmed@linux.dev/ |
| 43 | SVM: Fix (hilarious) exit_code bugs | N-A | nSVM exit_code | https://patchwork.kernel.org/project/kvm/patch/20251113225621.1688428-4-seanjc@google.com/ |
| 44 | nVMX: Mark APIC page dirty on VM-Exit | N-A | nVMX；`__kvm_vcpu_map` vCPU-memslots 改动仅服务嵌套 | https://patchwork.kernel.org/project/kvm/patch/20251121223444.355422-2-seanjc@google.com/ |
| 45 | VMX: Fix APICv activation bugs | N-A | nVMX APICv | https://patchwork.kernel.org/project/kvm/patch/20251205231913.441872-2-seanjc@google.com/ |
| 46 | SVM: Fix redundant updates of LBR MSR intercepts | N-A | nSVM LBRV | https://patchwork.kernel.org/project/kvm/patch/20251215192722.3654335-1-yosry.ahmed@linux.dev/ |
| 47 | nSVM: Remove user-triggerable WARN on nested_svm_load_cr3() | N-A | nSVM | https://patchwork.kernel.org/project/kvm/patch/20251216161755.1775409-1-seanjc@google.com/ |
| 48 | nVMX: Disallow access to unsupported vmcs12 fields | N-A | nVMX vmcs12 | https://patchwork.kernel.org/project/kvm/patch/20251230220220.4122282-2-seanjc@google.com/ |
| 49 | selftests: Add Nested NPT support | N-A | selftests x86 嵌套 NPT/EPT | https://patchwork.kernel.org/project/kvm/patch/20251230230150.4150236-5-seanjc@google.com/ |
| 50 | nVMX: Improve performance for unmanaged guest memory | N-A | nVMX；pfncache guest-uses-pfn 仅服务嵌套 | https://patchwork.kernel.org/project/kvm/patch/20260102142429.896101-9-griffoul@gmail.com/ |
| 51 | x86: Ignore -EBUSY when checking nested events from vcpu_block() | N-A | nVMX/nSVM 事件 | https://patchwork.kernel.org/project/kvm/patch/20260109030657.994759-1-seanjc@google.com/ |
| 52 | VMX: Rip out "deferred nested VM-Exit updates" | N-A | nVMX APICv | https://patchwork.kernel.org/project/kvm/patch/20260109034532.1012993-5-seanjc@google.com/ |
| 53 | nSVM: nested VMSAVE/VMLOAD fixes | N-A | nSVM | https://patchwork.kernel.org/project/kvm/patch/20260110004821.3411245-2-yosry.ahmed@linux.dev/ |
| 54 | nSVM: Minor cleanups for intercepts code | N-A | nSVM 截获 | https://patchwork.kernel.org/project/kvm/patch/20260112182022.771276-2-yosry.ahmed@linux.dev/ |
| 55 | nSVM: Drop redundant/wrong comment in nested_vmcb02_prepare_save() | N-A | nSVM | https://patchwork.kernel.org/project/kvm/patch/20260113172807.2178526-1-yosry.ahmed@linux.dev/ |
| 56 | VMX: Add quirk to allow L1 to set FREEZE_IN_SMM in vmcs12 | N-A | nVMX + SMM | https://patchwork.kernel.org/project/kvm/patch/20260113225406.273373-1-jmattson@google.com/ |
| 57 | nSVM: Expose SVM DecodeAssists to guest hypervisors | N-A | nSVM | https://patchwork.kernel.org/project/kvm/patch/20260115131739.25362-1-alejandro.garciavallejo@amd.com/ |
| 58 | nVMX: Disallow access to vmcs12 fields not supported by hardware | N-A | nVMX vmcs12 | https://patchwork.kernel.org/project/kvm/patch/20260115173427.716021-2-seanjc@google.com/ |
| 59 | nVMX: Track vmx emulation errors | N-A | nVMX | https://patchwork.kernel.org/project/kvm/patch/20260120144550.1083396-1-griffoul@gmail.com/ |
| 60 | SVM: Set PFERR_GUEST_{PAGE,FINAL}_MASK for nested NPF | N-A | nSVM NPF | https://patchwork.kernel.org/project/kvm/patch/20260121004906.2373989-3-chengkev@google.com/ |
| 61 | x86/pmu: Add support for AMD HG_ONLY bits | N-A | x86 AMD PMU（Host/Guest-Only）+ nSVM | https://patchwork.kernel.org/project/kvm/patch/20260121225438.3908422-2-jmattson@google.com/ |
| 62 | SVM: Fix IRQ window inhibit handling | N-A | nSVM/AVIC | https://patchwork.kernel.org/project/kvm/patch/20260123224514.2509129-4-seanjc@google.com/ |
| 63 | x86: Plug an intra-guest Spectre v2 hole | N-A | x86 缓解（IBPB + nested transitions） | https://patchwork.kernel.org/project/kvm/patch/20260128013432.3250805-3-seanjc@google.com/ |
| 64 | x86: CET vs. nVMX fix and hardening | N-A | x86 CET/XSS + nVMX | https://patchwork.kernel.org/project/kvm/patch/20260128014310.3255561-3-seanjc@google.com/ |
| 65 | nSVM: Stop tracking EFER.SVME in guest mode | N-A | nSVM EFER | https://patchwork.kernel.org/project/kvm/patch/20260130020735.2517101-4-yosry.ahmed@linux.dev/ |
| 66 | nSVM: Use vcpu->arch.cr2 when updating vmcb12 on nested #VMEXIT | N-A | nSVM | https://patchwork.kernel.org/project/kvm/patch/20260203201010.1871056-1-yosry.ahmed@linux.dev/ |
| 67 | nSVM: Handle L2 clearing EFER.SVME properly | N-A | nSVM EFER | https://patchwork.kernel.org/project/kvm/patch/20260209195142.2554532-2-yosry.ahmed@linux.dev/ |
| 68 | nSVM: Fix save/restore of next_rip & int_state | N-A | nSVM | https://patchwork.kernel.org/project/kvm/patch/20260210005449.3125133-4-yosry.ahmed@linux.dev/ |
| 69 | nSVM: Mark all of vmcb02 dirty when restoring nested state | N-A | nSVM | https://patchwork.kernel.org/project/kvm/patch/20260210010806.3204289-1-yosry.ahmed@linux.dev/ |
| 70 | nSVM: Fix save/restore of NextRIP & interrupt shadow | N-A | nSVM | https://patchwork.kernel.org/project/kvm/patch/20260211162842.454151-5-yosry.ahmed@linux.dev/ |
| 71 | SVM: A fix and cleanups for VMCB intercepts | N-A | nSVM 截获 | https://patchwork.kernel.org/project/kvm/patch/20260218230958.2877682-2-seanjc@google.com/ |
| 72 | nSVM: Fix RIP usage in the control area after restore | N-A | nSVM | https://patchwork.kernel.org/project/kvm/patch/20260223154636.116671-5-yosry@kernel.org/ |
| 73 | X86: Correctly populate nested page fault | N-A | nSVM/nVMX NPF/EPT（x86_exception 拓宽为 x86 专有）| https://patchwork.kernel.org/project/kvm/patch/20260224071822.369326-5-chengkev@google.com/ |
| 74 | nSVM: Ensure AVIC is inhibited when restoring vCPU to guest mode | N-A | nSVM AVIC | https://patchwork.kernel.org/project/kvm/patch/20260224225017.3303870-1-yosry@kernel.org/ |
| 75 | nSVM: Save/restore fixes for (Next)RIP | N-A | nSVM | https://patchwork.kernel.org/project/kvm/patch/20260225005950.3739782-4-yosry@kernel.org/ |
| 76 | Nested SVM fixes, cleanups, and hardening | N-A | nSVM | https://patchwork.kernel.org/project/kvm/patch/20260303003421.2185681-3-yosry@kernel.org/ |
| 77 | nSVM: Fix #UD on VMMCALL issues | N-A | nSVM VMMCALL | https://patchwork.kernel.org/project/kvm/patch/20260304002223.1105129-3-seanjc@google.com/ |
| 78 | nSVM: Intercept STGI/CLGI as needed to inject #UD | N-A | nSVM STGI/CLGI | https://patchwork.kernel.org/project/kvm/patch/20260304003010.1108257-2-seanjc@google.com/ |
| 79 | arm64: Fix a couple of latent bugs in user_mem_abort() | **PATTERN** | stage-2 缺页 bug 类（原子缺页页泄漏）；riscv `mmu.c` `kvm_riscv_gstage_map()` | https://patchwork.kernel.org/project/kvm/patch/20260304162222.836152-3-tabba@google.com/ |
| 80 | VMX APIC timer virtualization support | N-A | x86 VMX APIC 定时器虚拟化（硬件） | https://patchwork.kernel.org/project/kvm/patch/9a50051868ffc58a831e784f6fefe31968f062fc.1772732517.git.isaku.yamahata@intel.com/ |
| 81 | nSVM: Minor post-war fixups | N-A | nSVM | https://patchwork.kernel.org/project/kvm/patch/20260305203005.1021335-3-yosry@kernel.org/ |
| 82 | arm64: Refactor user_mem_abort() into a state-object model | **PATTERN** | 缺页处理器状态对象化重构；riscv `mmu.c:537 kvm_riscv_gstage_map()` | https://patchwork.kernel.org/project/kvm/patch/20260306140232.2193802-8-tabba@google.com/ |
| 83 | nSVM: Fix vmcb12 mapping failure handling | N-A | nSVM | https://patchwork.kernel.org/project/kvm/patch/20260306210900.1933788-6-yosry@kernel.org/ |
| 84 | x86: check validity of nested state when returning from SMM | N-A | nVMX/nSVM + SMM | https://patchwork.kernel.org/project/kvm/patch/20260310202414.406078-6-pbonzini@redhat.com/ |
| 85 | x86: APX reg prep work | N-A | x86 APX + nVMX 寄存器 | https://patchwork.kernel.org/project/kvm/patch/20260311003346.2626238-2-seanjc@google.com/ |
| 86 | VMX: Eliminate sparse warnings in vmcs12.c / hyperv_evmcs.c | N-A | nVMX/eVMCS | https://patchwork.kernel.org/project/kvm/patch/47e4570a1db6f68eacdde989c6cf4f53175cea75.1773193126.git.isaku.yamahata@intel.com/ |
| 87 | Improve test parity between SVM and VMX | N-A | kvm-unit-tests nSVM/nVMX | https://patchwork.kernel.org/project/kvm/patch/20260312200308.3089379-8-chengkev@google.com/ |
| 88 | X86: Correctly populate nested page fault injection error info | N-A | nSVM/nVMX NPF/EPT | https://patchwork.kernel.org/project/kvm/patch/20260313071033.4153209-5-chengkev@google.com/ |
| 89 | SVM: Fixes for VMCB12 checks and mapping | N-A | nSVM VMCB12 | https://patchwork.kernel.org/project/kvm/patch/20260316202732.3164936-9-yosry@kernel.org/ |
| 90 | vmx/nested: Set the SGX feature flag only when hardware supported | N-A | nVMX SGX | https://patchwork.kernel.org/project/kvm/patch/1774322860-25106-1-git-send-email-18341265598@163.com/ |
| 91 | arm64: Combined user_mem_abort() rework | **PATTERN** | 缺页处理器重构（v2/30 patch）；riscv `mmu.c kvm_riscv_gstage_map()` | https://patchwork.kernel.org/project/kvm/patch/20260327113618.4051534-15-maz@kernel.org/ |
| 92 | SVM: Enable FRED support | N-A | x86 FRED SVM + 嵌套异常注入 | https://patchwork.kernel.org/project/kvm/patch/20260402184240.1939480-8-shivansh.dhiman@amd.com/ |
| 93 | nSVM: Redirect IA32_PAT accesses to hPAT or gPAT | N-A | nSVM PAT | https://patchwork.kernel.org/project/kvm/patch/20260407190343.325299-6-jmattson@google.com/ |
| 94 | nSVM: Improve PAT virtualization | N-A | nSVM PAT | https://patchwork.kernel.org/project/kvm/patch/20260407190343.325299-4-jmattson@google.com/ |
| 95 | x86: Reg cleanups / prep work for APX | N-A | x86 APX + nVMX 寄存器 | https://patchwork.kernel.org/project/kvm/patch/20260409224236.2021562-2-seanjc@google.com/ |
| 96 | arm64: Add Stage-2 MMU and Nested Guest Framework（kvm-unit-tests）| PATTERN（未来/低） | 嵌套测试基础库模板；**riscv 嵌套未实现，仅供未来参考** | https://patchwork.kernel.org/project/kvm/patch/20260413204630.1149038-8-jingzhangos@google.com/ |
| 97 | nVMX: Fold requested virtual interrupt check（6.6 backport）| N-A | nVMX | https://patchwork.kernel.org/project/kvm/patch/20260415202346.3026288-1-seanjc@google.com/ |
| 98 | nSVM: Stop leaking single-stepping on VMRUN into L2（+PMU）| N-A | nSVM + AMD mediated PMU | https://patchwork.kernel.org/project/kvm/patch/20260506015733.1671124-2-yosry@kernel.org/ |
| 99 | nSVM: Never use L0's PAUSE loop exiting while L2 is running | N-A | nSVM | https://patchwork.kernel.org/project/kvm/patch/20260512201219.3021354-1-pbonzini@redhat.com/ |
| 100 | arm64: selftests: Basic nested guest support | PATTERN（未来/低） | 嵌套 guest selftests 脚手架；**riscv 嵌套未实现，仅供未来参考** | https://patchwork.kernel.org/project/kvm/patch/20260516183003.799058-6-weilin.chang@arm.com/ |
| 101 | arm64: Nested virtualization support（kvmtool）| N-A | kvmtool 用户态 arm-NV | https://patchwork.kernel.org/project/kvm/patch/20260518124556.164739-5-andre.przywara@arm.com/ |
| 102 | arm64: nv: Reduce FP/SVE overhead on exception/exception return | N-A | arm-NV FP/SVE | https://patchwork.kernel.org/project/kvm/patch/20260520085036.541666-2-maz@kernel.org/ |
| 103 | X86: Fix nested TDP error code info | N-A | nSVM/nVMX NPF/EPT | https://patchwork.kernel.org/project/kvm/patch/20260522232701.3671446-6-seanjc@google.com/ |
| 104 | nVMX: Improve IA32_DEBUGCTLMSR test on debug controls | N-A | kvm-unit-tests nVMX DEBUGCTL | https://patchwork.kernel.org/project/kvm/patch/20260526031704.109102-2-chenyi.qiang@intel.com/ |
| 105 | nVMX: Improve DEBUGCTL test coverage | N-A | kvm-unit-tests nVMX | https://patchwork.kernel.org/project/kvm/patch/20260527151232.4058615-2-seanjc@google.com/ |
| 106 | x86: Virtualize AMD's "disable CPUID in usermode" | N-A | x86 CPUID faulting + nVMX | https://patchwork.kernel.org/project/kvm/patch/20260527174347.2356165-5-jmattson@google.com/ |
| 107 | x86/pmu: Add support for AMD Host-Only/Guest-Only bits | N-A | x86 AMD PMU + nSVM | https://patchwork.kernel.org/project/kvm/patch/20260527234711.4175166-2-yosry@kernel.org/ |
| 108 | x86: small MMU-adjacent cleanups | N-A | nVMX/nSVM 影子 MMU/PDPTR（x86 影子分页专有）| https://patchwork.kernel.org/project/kvm/patch/20260530165545.25599-6-pbonzini@redhat.com/ |
| 109 | KVM: harden and cleanup PDPTR load on forced L1 reload | N-A | nVMX PDPTR 影子分页 | https://patchwork.kernel.org/project/kvm/patch/20260604160733.12555-3-pbonzini@redhat.com/ |
| 110 | x86/mmu: Plug an unsync shadow page leak | N-A | x86 影子 MMU 嵌套 TDP | https://patchwork.kernel.org/project/kvm/patch/20260605174611.2222504-3-seanjc@google.com/ |
| 111 | selftests: Add AMD PMU Host/Guest test | N-A | selftests x86 nSVM PMU | https://patchwork.kernel.org/project/kvm/patch/20260610003030.2957261-4-seanjc@google.com/ |
| 112 | nVMX: Fix ept=n bugs where KVM runs L2 with guest CR3 | N-A | nVMX | https://patchwork.kernel.org/project/kvm/patch/20260612145642.452392-2-seanjc@google.com/ |
| 113 | arm64: Add KVM_PRE_FAULT_MEMORY support | **PATTERN**（底座 PORTABLE） | 通用 `KVM_GENERIC_PRE_FAULT_MEMORY` opt-in；riscv `Kconfig`+`mmu.c kvm_arch_vcpu_pre_fault_memory()`+`vm.c` CAP | https://patchwork.kernel.org/project/kvm/patch/20260612162354.73378-3-jackabt.amazon@gmail.com/ |
| 114 | nVMX: A few TLB flushing fixes（vpid02）| N-A | nVMX VPID | https://patchwork.kernel.org/project/kvm/patch/20260616214652.2157032-2-yosry@kernel.org/ |
| 115 | x86: Relay a nested Hyper-V root's vmbus posts to L0 | N-A | Hyper-V 嵌套 | https://patchwork.kernel.org/project/kvm/patch/29662c85-9c4d-404f-b493-a5d1b8c1e19d@rotek.at/ |
| 116 | x86: Fix VM-Entry fail due to stale CR8 intercept | N-A | nVMX CR8 | https://patchwork.kernel.org/project/kvm/patch/20260618174347.1981064-3-seanjc@google.com/ |
| 117 | x86: Replace BUG_ON with WARN_ON_ONCE on bad nested GPA translation | N-A | 嵌套 TDP GPA | https://patchwork.kernel.org/project/kvm/patch/20260618185746.2023283-1-seanjc@google.com/ |
| 118 | nVMX: backport virtual-APIC host NULL-deref fix | N-A | nVMX posted interrupt backport | https://patchwork.kernel.org/project/kvm/patch/20260619203107.2752678-4-main.kalliope@gmail.com/ |
| 119 | nSVM: Expose DecodeAssists to L1 | N-A | nSVM | https://patchwork.kernel.org/project/kvm/patch/20260629125205.52394-3-zhang_wei@open-hieco.net/ |
| 120 | selftests: Stress save+restore and #PF (ft. nested) | N-A | selftests x86 nSVM/nVMX（STR/XSTR 移入 test_util.h 极少量通用）| https://patchwork.kernel.org/project/kvm/patch/20260629183746.699840-6-yosry@kernel.org/ |
| 121 | x86: Convert nested ops to static calls | N-A | x86 `kvm_x86_ops` static-call 重组；分离 `kvm_nested_ops` 结构的组织思想绑定 x86，riscv 无嵌套间接层（边际未来参考）| https://patchwork.kernel.org/project/kvm/patch/20260630202828.440724-3-seanjc@google.com/ |
| 122 | x86/hyperv: Fix racy usage of vcpu->arch.hyperv | N-A | Hyper-V/Xen | https://patchwork.kernel.org/project/kvm/patch/20260630225619.511632-11-seanjc@google.com/ |
| 123 | x86/vmx: Add some FRED tests | N-A | kvm-unit-tests nVMX FRED | https://patchwork.kernel.org/project/kvm/patch/20260702065039.3434909-5-xin@zytor.com/ |
| 124 | x86: EFER validity fixes and cleanups | N-A | x86 EFER（LME/LMA/SVME）+ 嵌套 | https://patchwork.kernel.org/project/kvm/patch/20260706195413.1966458-7-yosry@kernel.org/ |
| 125 | SVM: Add Bus Lock Detect support and refactor LBRV | N-A | nSVM LBRV + Bus Lock | https://patchwork.kernel.org/project/kvm/patch/20260709082953.69434-2-shivansh.dhiman@amd.com/ |
| 126 | x86: Backports for VM entry failure due to stale CR8 intercept（7.1.y）| N-A | x86 backport nVMX CR8 | https://patchwork.kernel.org/project/kvm/patch/20260709132109.3423488-3-clopez@suse.de/ |

### hw-virt-engine（11 条）

| # | 系列 | 判定 | 可移植点 / riscv落点（若有） | web_url |
|---|---|---|---|---|
| H1 | kvmtool: Handle KVM_EXIT_UNKNOWN / KVM_EXIT_MEMORY_FAULT | N-A | kvmtool **用户态** VMM 退出处理（架构无关，但非 riscv KVM 内核范畴；riscv kvmtool 若上 guest_memfd 可自行采纳）| https://patchwork.kernel.org/project/kvm/patch/20250224091000.3925918-1-aneesh.kumar@kernel.org/ |
| H2 | SVM: Fix an STI shadow on VMRUN bug | N-A | x86 SVM VMRUN 世界切换（RFLAGS.IF/STI shadow）| https://patchwork.kernel.org/project/kvm/patch/20250224165442.2338294-2-seanjc@google.com/ |
| H3 | SVM: Zero DEBUGCTL before VMRUN if necessary | N-A | x86 SVM VMRUN + DEBUGCTL/LBR 快照 | https://patchwork.kernel.org/project/kvm/patch/20250224181315.2376869-2-seanjc@google.com/ |
| H4 | x86/bugs: RSB mitigation fixes and documentation | N-A | x86 CPU 缓解（RSB/retpoline/eIBRS/VMEXIT fill）| https://patchwork.kernel.org/project/kvm/patch/ab73f4659ba697a974759f07befd41ae605e33dd.1744148254.git.jpoimboe@kernel.org/ |
| H5 | kvmtool: KVM_RUN ioctl error handling fixes | N-A | kvmtool 用户态退出/重试处理（架构无关，非内核范畴）| https://patchwork.kernel.org/project/kvm/patch/20250428115745.70832-3-aneesh.kumar@kernel.org/ |
| H6 | arm64: Force HCR_EL2.xMO to 1 at all times in VHE mode | N-A | arm64 VHE HCR_EL2 世界切换寄存器 | https://patchwork.kernel.org/project/kvm/patch/20250429114326.3618875-1-maz@kernel.org/ |
| H7 | arm64: selftests: Run selftests in VHE EL2 | N-A | arm64 VHE EL2 selftests（VGICv3/EL1→EL2 别名）| https://patchwork.kernel.org/project/kvm/patch/20250917212044.294760-12-oliver.upton@linux.dev/ |
| H8 | arm64: De-specialise the timer UAPI | N-A | arm64 EL2 定时器 UAPI（CNTHV_*_EL2，nVHE/VHE 专有；属 timer 归口）| https://patchwork.kernel.org/project/kvm/patch/20250929160458.3351788-10-maz@kernel.org/ |
| H9 | x86: apic, vmexit: Replace NOP with CPUID to serialize deadline timer | N-A | kvm-unit-tests x86 APIC deadline | https://patchwork.kernel.org/project/kvm/patch/2ef8af4c0afc26feee8a993ef818f9ed40a7f329.1772678359.git.isaku.yamahata@intel.com/ |
| H10 | VMX/SVM: use the same SPEC_CTRL assembly code | N-A | x86 vmenter 汇编 + SPEC_CTRL（Spectre MSR）世界切换 | https://patchwork.kernel.org/project/kvm/patch/20260428110507.11248-3-pbonzini@redhat.com/ |
| H11 | x86/svm: work around Virtual VMLOAD/VMSAVE bug on Naples and Rome | N-A | kvm-unit-tests，AMD SVM 勘误 | https://patchwork.kernel.org/project/kvm/patch/20260519080127.69056-1-imammedo@redhat.com/ |

## 结论

- 本类 137 条，**131 条 N-A**——嵌套虚拟化（nVMX/nSVM/arm-NV）与世界切换（VMX/SVM/VHE 引擎）均为 x86/arm 专有硬件，riscv 无对应且这些补丁不扩展通用底座。
- **6 条 PATTERN**，其中真正有当下价值的 3 条（[113] pre-fault、[82/91] user_mem_abort 重构、[79] user_mem_abort bug 类）**实为 stage-2/mmu 主题**，因触及 nested 代码路径被误归入本批；已标注 riscv 落点（均在 `arch/riscv/kvm/mmu.c`），**建议主代理与 mmu-stage2 归口合并去重**。另 2 条（[96][100] 嵌套 selftests 脚手架）仅在 riscv 未来实现 H-in-VS 嵌套时作模板参考，当前无落点。
- riscv 嵌套虚拟化（H-in-VS）一旦立项，可回看本批的**通用嵌套基础设施组织思想**（如 [121] 将 nested_ops 独立成结构），但那需 riscv 侧从零构建，超出「移植」范畴。
