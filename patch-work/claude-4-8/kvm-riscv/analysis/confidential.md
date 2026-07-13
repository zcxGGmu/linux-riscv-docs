# 机密计算 (Tier C — Confidential) 可移植性分析

> 输入：`kvm-riscv/data/by_category/C_confidential.jsonl`（229 条系列）。
> 基调：riscv **无 CoVE / 机密计算**支持（对照 `_baseline_riscv.md` §"明确不适用"）。绝大多数系列依赖 x86 TDX/SEV(-ES/-SNP) 或 arm pKVM/CCA/RME 专有硬件 → **N-A**。
> 本类真正价值 = 少数**扩展了通用底座**的系列（`virt/kvm/guest_memfd.c`、`KVM_GENERIC_MEMORY_ATTRIBUTES`、通用 VM/ioctl 生命周期）。这些与 riscv 的 guest_memfd 移植（基线缺口 #1，高价值）强相关。

## 摘要

- **系列总数**：229
- **四态计数**：
  - **ALREADY**：1（通用 vcpu-ioctl 钩子重命名已落地 riscv）
  - **PORTABLE**：11（通用 guest_memfd / 内存属性 / VM 生命周期底座；其中 6 条为纯/主要通用，5 条为混合系列的通用子集）
  - **PATTERN**：1（guest_memfd selftests，需 riscv 先具 gmem）
  - **N-A**：216（TDX/SEV/SNP/AVIC/pKVM/CCA/RME 硬件专属 + QEMU 用户态 + x86 遗留）

### 本类 Top 候选（按移植价值排序）

| # | 系列 | 判定 | 一句话 |
|---|---|---|---|
| L73 | Enable host userspace mapping for guest_memfd (non-CoCo) v16/22p | PORTABLE★ | 通用 guest_memfd 使能主线，显式面向非机密 VM；含 arm64 消费方，riscv 照做即可 |
| L75 | Enable mmap() for guest_memfd v17/24p | PORTABLE★ | L73 的后继，为 guest_memfd 加 mmap；同为跨架构通用底座 |
| L60 | guest_memfd: Support in-place conversion for CoCo VMs | PORTABLE | `virt/kvm/guest_memfd.c` 通用 shared↔private 转换框架（已 curl 证实） |
| L130 | guest_memfd: Rework preparation/population flows | PORTABLE | `virt/kvm/guest_memfd.c` 通用 populate/prepare 重构（已 curl 证实） |
| L54 | SEV-SNP fix cpu soft lockup 1TB+（内存属性） | PORTABLE | 纯通用 `virt/kvm/kvm_main.c`：mem-attr 设置加 `cond_resched` + tracepoint（已 curl 证实） |
| L195 | guest_memfd fixes for bind and populate | PORTABLE | 3/5 为通用 guest_memfd 缺陷修复（GUP 写权限/整数溢出/xa_store_range 错误） |
| L74 | KVM: Drop vm_dead, pivot on vm_bugged for -EIO | PORTABLE | 通用 `virt/kvm/kvm_main.c` VM 生命周期 & ioctl 拒绝逻辑（`KVM_REQ_VM_DEAD`） |
| L114 | TDX post-populate cleanups（通用子集） | ALREADY | 2 补丁把 `kvm_arch_vcpu_async_ioctl` 改名 `_unlocked_ioctl` 并设为必需——riscv 已有该钩子 |

## Top 可移植候选（深度）

> 关键前提（本地源码核对，`/Users/zq/Desktop/patch-work/linux-riscv`）：
> - `virt/kvm/guest_memfd.c`（25 KB）与 `virt/kvm/Kconfig`（`KVM_GUEST_MEMFD` L106、`KVM_GENERIC_MEMORY_ATTRIBUTES` L103、`HAVE_KVM_ARCH_GMEM_*` L110-120）**通用底座已在树内**。
> - **arm64 已 `select KVM_GUEST_MEMFD`；x86 两者皆选；riscv 一个都没选**（`arch/riscv/kvm/Kconfig` 仅 IRQCHIP/DIRTYLOG/MMIO 等）。
> - `kvm_arch_has_private_mem()` 是 `include/linux/kvm_host.h:726` 的通用弱默认；riscv 未覆盖。
> - riscv 缺页主路径 `arch/riscv/kvm/mmu.c:599-650`（`__kvm_faultin_pfn()` → `kvm_riscv_gstage_map_page()`）；arm64 在同位置 `mmu.c:1644` 走 `kvm_gmem_get_pfn()`。**此处即 riscv 的 gmem 落点。**
> - riscv 全树无 `kvm_mem_is_private` / `kvm_slot_has_gmem` / `mem_attr_array` 使用 → 缺口坐实。

### 1. Enable host userspace mapping for guest_memfd — non-CoCo（L73，最高价值）
- **原补丁**：https://patchwork.kernel.org/project/kvm/patch/20250723104714.1674617-17-tabba@google.com/ 状态=new，v16/22 补丁
- **可移植点**：通用 guest_memfd 使能主线，**显式脱离机密计算**（"for non-CoCo VMs"）。配置重命名 `CONFIG_KVM_PRIVATE_MEM→CONFIG_KVM_GUEST_MEMFD`、`kvm_slot_can_be_private()→kvm_slot_has_gmem()`，把 gmem 变成任意 VM 可用的通用后端。系列内含 arm64 `user_mem_abort()` 消费方补丁（curl 证实 mbox 中该补丁改 `arch/arm64/kvm/mmu.c`）——**通用系列引入第二个架构消费方，riscv 即第三个**。
- **riscv 落点**：`arch/riscv/kvm/Kconfig` 加 `select KVM_GUEST_MEMFD`（照抄 arm64）；缺页路径 `arch/riscv/kvm/mmu.c:~615` 增 `kvm_mem_is_private()` 分支调 `kvm_gmem_get_pfn()`（对标 arm64 `mmu.c:1644`）。通用代码 `virt/kvm/guest_memfd.c` 已在树内，无需重写。
- **判定**：**PORTABLE** —— 通用底座 + 明确的跨架构消费模式，riscv 只需 Kconfig 选入 + 极少缺页胶水。

### 2. Enable mmap() for guest_memfd（L75）
- **原补丁**：https://patchwork.kernel.org/project/kvm/patch/20250729225455.670324-18-seanjc@google.com/ 状态=new，v17/24 补丁
- **可移植点**：L73 的直接后继/合流版，为 guest_memfd 增加 host 用户态 `mmap()` 能力（同样的配置重命名 + 通用 folio/映射逻辑）。curl 证实 mbox 中所链补丁仍是 arm64 `user_mem_abort()` 通用重构。
- **riscv 落点**：同 L73（`arch/riscv/kvm/Kconfig` + `arch/riscv/kvm/mmu.c`）；mmap 逻辑在 `virt/kvm/guest_memfd.c` 通用实现，riscv 自动受益。
- **判定**：**PORTABLE** —— 与 L73 属同一通用工作流，是 riscv gmem 落地后的即时增益。

### 3. guest_memfd: Support in-place conversion for CoCo VMs（L60）
- **原补丁**：https://patchwork.kernel.org/project/kvm/patch/20250613005400.3694904-2-michael.roth@amd.com/ 状态=new，RFC v1/5
- **可移植点**：通用 shared↔private **原地转换**框架。curl 证实 patch 1/5 "Remove preparation tracking" 改 `virt/kvm/guest_memfd.c`（-47 行）；另含 "Only access KVM memory attributes when appropriate"、"Call arch invalidation hooks when converting to shared"、"Don't prepare shared folios"——全在通用层，仅 patch 5（SNP_LAUNCH_UPDATE）为 SEV 专属。
- **riscv 落点**：`virt/kvm/guest_memfd.c`（通用，随 gmem 选入自动生效）；arch 失效钩子对应 riscv 侧可选实现 `HAVE_KVM_ARCH_GMEM_INVALIDATE`（`arch/riscv/kvm/mmu.c` 新增）。
- **判定**：**PORTABLE**（通用转换框架）；SEV 收尾补丁 N-A。

### 4. guest_memfd: Rework preparation/population flows（L130）
- **原补丁**：https://patchwork.kernel.org/project/kvm/patch/20260108214622.1084057-4-michael.roth@amd.com/ 状态=new，v3/6
- **可移植点**：通用 populate/prepare 流程重构。curl 证实 patch 3/6 "Remove preparation tracking" 改 `virt/kvm/guest_memfd.c`（-44 行）；含 "Remove partial hugepage handling from kvm_gmem_populate()"、"GUP source pages prior to populating"。patch 1/4/5 为 SVM/SEV/TDX 收尾。
- **riscv 落点**：`virt/kvm/guest_memfd.c`（通用）；若 riscv 走 `HAVE_KVM_ARCH_GMEM_POPULATE` 则新增 `arch/riscv/kvm/mmu.c` 钩子。
- **判定**：**PORTABLE**（通用 populate 底座）；厂商收尾 N-A。

### 5. SEV-SNP fix cpu soft lockup 1TB+ — 内存属性（L54）
- **原补丁**：https://patchwork.kernel.org/project/kvm/patch/20250609091121.2497429-3-liam.merwick@oracle.com/ 状态=new，v2/3
- **可移植点**：**纯通用**。curl 证实 patch 1/3 仅改 `virt/kvm/kvm_main.c`（+3 行）在 `kvm_vm_set_mem_attributes()` 大范围设置时加 `cond_resched`；patch 2 加 `trace_kvm_vm_set_mem_attributes()`。虽由 SNP 触发，改动 0% 架构相关。
- **riscv 落点**：`virt/kvm/kvm_main.c:2537`（`kvm_vm_set_mem_attributes` 已在树内）——一旦 riscv `select KVM_GENERIC_MEMORY_ATTRIBUTES` 即受益；tracepoint 本地已存在（`kvm_main.c:2563`）。
- **判定**：**PORTABLE** —— 内存属性通用路径的健壮性改进，随 riscv 选入 `KVM_GENERIC_MEMORY_ATTRIBUTES` 直接适用。

### 6. guest_memfd fixes for bind and populate（L195）
- **原补丁**：https://patchwork.kernel.org/project/kvm/patch/20260522-fix-sev-gmem-post-populate-v2-4-3f196bfad5a1@google.com/ 状态=new，v2/5
- **可移植点**：patch 1-3 为**通用 `virt/kvm/guest_memfd.c` 缺陷修复**："Use write permissions when GUP-ing source pages"、"Fix possible signed integer overflow"、"Handle errors from xa_store_range() when binding"。patch 4-5（所链补丁改 `arch/x86/kvm/svm/sev.c`）为 SNP 专属。
- **riscv 落点**：`virt/kvm/guest_memfd.c`（通用，随 gmem 生效）。
- **判定**：**PORTABLE**（通用 gmem bind/populate 修复子集）；SNP 部分 N-A。

### 7. KVM: Drop vm_dead, pivot on vm_bugged for -EIO（L74）
- **原补丁**：https://patchwork.kernel.org/project/kvm/patch/20250729193341.621487-6-seanjc@google.com/ 状态=new，5 补丁
- **可移植点**：通用 VM 生命周期 & ioctl 拒绝逻辑（`KVM_REQ_VM_DEAD` 处理、"Reject ioctls only if the VM is bugged, not simply marked dead"）位于 `virt/kvm/kvm_main.c`，对所有架构生效。patch 2/5 为 TDX 收尾。
- **riscv 落点**：`virt/kvm/kvm_main.c`（通用核心，自动适用 riscv）。
- **判定**：**PORTABLE**（通用核心）；TDX 补丁 N-A。

### 附：ALREADY 与次要 PORTABLE
- **L114**（TDX post-populate cleanups）：patch 1-2 "Make `kvm_arch_vcpu_async_ioctl()` mandatory" + 改名 `kvm_arch_vcpu_unlocked_ioctl()` 为通用改动，但 **riscv 已有 `kvm_arch_vcpu_unlocked_ioctl`（`arch/riscv/kvm/vcpu.c:245`）** → 通用部分判 **ALREADY**，其余 TDX/x86-mmu 判 N-A。
- **L44**（New KVM ioctl to link gmem inode / `KVM_LINK_GUEST_MEMFD`）：**PORTABLE（部分）** —— patch 1-4 为通用 gmem inode 重构 + 新 ioctl（`fs/` + `virt/kvm/guest_memfd.c`），可复用于 riscv gmem；但 RFC 且用途窄（VM 间私有内存转移/热升级），所链 patch 8 为 x86 refactor。riscv 落点：`virt/kvm/guest_memfd.c`。
- **L211 / L213 / L229**（SEV 修复系列的通用 gmem 钩子子集）：**PORTABLE（部分）** —— 各含 1 个通用 `virt/kvm/guest_memfd.c` 钩子改动（L211 "Add `write` param to `kvm_gmem_populate()`"；L213/L229 "Rework `.gmem_invalidate()` into `.gmem_free_folio()`"），随 riscv gmem 生效；其余 SEV/x86-mmu 部分 N-A。
- **L184**（guest_memfd selftests INIT_SHARED）：**PATTERN** —— 通用 selftest lib（`vm_vaddr_alloc` private/shared、转换测试）riscv selftests 可复用，但**须 riscv 先具 gmem**，且当前面向 CoCo。落点：`tools/testing/selftests/kvm/`（riscv 目录滞后）。

## 全量判定表

> 说明：actionable 行（PORTABLE/ALREADY/PATTERN，共 13 条）带 web_url 与 riscv 落点；N-A 行（216 条）给硬件/子系统归因关键词，url 见源 JSONL 对应行号（L#）。sample_titles 中的架构关键词是判 N-A 的直接依据。

### Actionable 行（PORTABLE / ALREADY / PATTERN）

| L# | 系列 | 判定 | 可移植点 | riscv落点 | web_url |
|---|---|---|---|---|---|
| 44 | New KVM ioctl to link gmem inode (KVM_LINK_GUEST_MEMFD) | PORTABLE(部分) | 通用 gmem inode 重构 + 新 ioctl | `virt/kvm/guest_memfd.c` | .../e9de4d2a...afranji@google.com/ |
| 54 | SEV-SNP fix cpu soft lockup 1TB+ | PORTABLE | mem-attr 设置 cond_resched + tracepoint（纯通用，已证） | `virt/kvm/kvm_main.c:2537` | .../20250609091121.2497429-3-liam.merwick@oracle.com/ |
| 60 | guest_memfd: in-place conversion for CoCo | PORTABLE | 通用 shared↔private 转换框架（已证） | `virt/kvm/guest_memfd.c` | .../20250613005400.3694904-2-michael.roth@amd.com/ |
| 73 | Enable host userspace mapping for guest_memfd (non-CoCo) | PORTABLE★ | 通用 gmem 使能主线 + 配置重命名 + arm64 消费方 | `arch/riscv/kvm/Kconfig`+`mmu.c:615` | .../20250723104714.1674617-17-tabba@google.com/ |
| 74 | KVM: Drop vm_dead, pivot on vm_bugged for -EIO | PORTABLE | 通用 VM 生命周期/ioctl 拒绝逻辑 | `virt/kvm/kvm_main.c` | .../20250729193341.621487-6-seanjc@google.com/ |
| 75 | Enable mmap() for guest_memfd | PORTABLE★ | 通用 gmem mmap 支持（含 arm64 消费方） | `arch/riscv/kvm/Kconfig`+`mmu.c:615` | .../20250729225455.670324-18-seanjc@google.com/ |
| 114 | KVM: x86/mmu: TDX post-populate cleanups | ALREADY | vcpu-ioctl 钩子改名/必需——riscv 已有 | `arch/riscv/kvm/vcpu.c:245` | .../20251030200951.3402865-29-seanjc@google.com/ |
| 130 | guest_memfd: Rework preparation/population flows | PORTABLE | 通用 populate/prepare 重构（已证） | `virt/kvm/guest_memfd.c` | .../20260108214622.1084057-4-michael.roth@amd.com/ |
| 184 | [POC] selftests: guest_memfd INIT_SHARED | PATTERN | 通用 gmem selftest lib（须先具 gmem） | `tools/testing/selftests/kvm/` | .../1edc2c94...ackerleytng@google.com/ |
| 195 | guest_memfd fixes for bind and populate | PORTABLE | 通用 gmem bind/populate 修复(1-3/5) | `virt/kvm/guest_memfd.c` | .../20260522-fix-sev-gmem-post-populate-v2-4-...@google.com/ |
| 211 | kvm: sev: Fix issues reported by Sashiko | PORTABLE(部分) | 通用 `kvm_gmem_populate()` 加 write 参数 | `virt/kvm/guest_memfd.c` | .../20260623091556.1500930-5-joro@8bytes.org/ |
| 213 | KVM: SEV: Fix RMP #PF freeing in-use VMSA | PORTABLE(部分) | 通用 `.gmem_invalidate()`→`.gmem_free_folio()` | `virt/kvm/*` gmem 钩子 | .../20260626231416.3943216-5-seanjc@google.com/ |
| 229 | KVM: SEV: Fix RMP #PF freeing in-use VMSA (v4) | PORTABLE(部分) | 同 L213（通用 gmem 钩子重构） | `virt/kvm/*` gmem 钩子 | .../20260709204948.1988414-14-seanjc@google.com/ |

### N-A 行（硬件/用户态专属，覆盖其余 216 条）

> 归因关键词：TDX=Intel TDX/SEAMCALL/S-EPT/PAMT；SEV/SNP=AMD SEV(-ES/-SNP)/GHCB/VMSA/RMP/ASID；AVIC=Secure AVIC；SEV-TIO/TSM=SEV-TIO/PCI TDISP/TSM Connect；pKVM/CCA/RME=arm 机密；QEMU=用户态 VMM；x86-hw=VMX/EPT/MTRR/CET/MSR/quirk/tsc 等 x86 专属；chore=MAINTAINERS/docs。riscv 均无对应硬件且不扩展通用底座。

| L# | 系列 | 归因 | L# | 系列 | 归因 |
|---|---|---|---|---|---|
| 1 | Secure TSC for SNP guests | SEV/SNP | 2 | SEV Pin guest mem out of CMA | SEV/SNP |
| 3 | TDX SEPT SEAMCALL retry | TDX | 4 | TDX SEAMCALL wrappers for KVM | TDX |
| 5 | SEV to_kvm_sev_info() helper | SEV/SNP | 6 | SVM Flush cache on SEV CPUs | SEV/SNP |
| 7 | WBNOINVD over WBINVD | x86-hw | 8 | Force legacy PCI hole WB SNP/TDX | x86-hw |
| 9 | x86/tsc PV clocks vs TSC | x86-hw | 10 | QEMU target/i386 sev cmdline | QEMU |
| 11 | Fix SNP support KVM built-in | SEV/SNP | 12 | SEV fix wrong pinning of pages | SEV/SNP |
| 13 | TSM Secure VFIO/TDISP/SEV TIO | SEV-TIO/TSM | 14 | two KVM MMU fixes for TDX | TDX |
| 15 | TDX init + vCPU/VM creation | TDX | 16 | TDX hypercalls exit to userspace | TDX |
| 17 | TDX interrupts | TDX | 18 | TDX MMU part 2 | TDX |
| 19 | TDX "the rest" part | TDX | 20 | SVM cleanup SEV_FEATURES | SEV/SNP |
| 21 | selftests SEV smoke printf fix | SEV/SNP | 22 | quirk EPT_IGNORE_GUEST_PAT | x86-hw |
| 23 | quirk IGNORE_GUEST_PAT | x86-hw | 24 | Basic SEV-SNP Selftests | SEV/SNP |
| 25 | TDX TD vcpu enter/exit | TDX | 26 | ALLOWED_SEV_FEATURES | SEV/SNP |
| 27 | TDX defer guest memory removal | TDX | 28 | x86 Support protected TSC | x86-hw/CoCo |
| 29 | SVM Enable Secure TSC SNP | SEV/SNP | 30 | TDX cleanup kvm_x86_ops | TDX/VMX |
| 31 | ccp Abort SEV INIT if SNP fails | SEV/SNP | 32 | SEV-ES/SNP decrypt VMSA | SEV/SNP |
| 33 | Move init SEV/SNP to KVM | SEV/SNP | 34 | SVM Rework ASID management | SEV/SNP |
| 35 | SVM Fix SNP AP destroy race | SEV/SNP | 36 | optee OP-TEE Mediator (arm) | pKVM/CCA/arm-TEE |
| 37 | I/O port filtering sev module | SEV/SNP | 38 | TDX selftests private memory | TDX |
| 39 | TDX attestation GetQuote | TDX | 40 | Doc fix TDX whitepaper | chore |
| 41 | sev remove GFP_KERNEL_ACCOUNT | SEV/SNP | 42 | QEMU TDX support | QEMU |
| 43 | SEV Disable SNP on init failure | SEV/SNP | 45 | Optimize SEV cache flushing | SEV/SNP |
| 46 | Dynamically alloc hashed page list | x86-hw/TDX | 47 | TD-Preserving updates | TDX |
| 48 | tdh_vp_enter __flatten | TDX | 49 | sev/vc efi runtime insn emul | SEV/SNP |
| 50 | tdx inline tdx_tdvpr_pa | TDX | 51 | Remove hardcoded SNP policy checks | SEV/SNP |
| 52 | SVM NULL VMSA MOVE_ENC_CONTEXT | SEV/SNP | 53 | SNP guest request throttling | SEV/SNP |
| 55 | tdx_alloc/free_page helpers | TDX | 56 | VMX DEBUGCTL.FREEZE_IN_SMM | x86-hw/VMX |
| 57 | TDX Decrease VM shutdown | TDX | 58 | TDX intra-host migration | TDX |
| 59 | TDX PAMT alloc in fault path | TDX | 61 | TDX attestation GHCI fixup | TDX |
| 62 | sev efi runtime code | SEV/SNP | 63 | TDX Decouple init mem region | TDX |
| 64 | MAINTAINERS TDX entry | chore | 65 | MAINTAINERS TDX mail list | chore |
| 66 | TDX cleanup ATTRIBUTES defs | TDX | 67 | Improve KVM_SET_TSC_KHZ CoCo | x86-hw/CoCo |
| 68 | TDX cleanup TD ATTRIBUTES | TDX | 69 | iommu/amd kdump SNP | SEV/SNP |
| 70 | SEV min GHCB version | SEV/SNP | 71 | TDX Don't report base TDVMCALLs | TDX |
| 72 | TDX KVM_TDX_TERMINATE_VM | TDX | 76 | SEV GHCB Version Handling | SEV/SNP |
| 77 | Enable Secure TSC SEV-SNP | SEV/SNP | 78 | SEV SMT Protection | SEV/SNP |
| 79 | TDX Remove redundant __GFP_ZERO | TDX | 80 | SVM fixes for SEV | SEV/SNP |
| 81 | TDX MWAIT in guest | TDX | 82 | tdx skip clearing reclaimed pages | TDX |
| 83 | MCE recovery TDX/SEAM | TDX | 84 | SVM Enable Secure TSC SEV-SNP | SEV/SNP |
| 85 | SEV-SNP CipherTextHiding | SEV/SNP | 86 | SEV save policy LAUNCH_START | SEV/SNP |
| 87 | KVM Fix deadlock invalid memslots | x86-hw/mmu | 88 | Add host kdump support SNP | SEV/SNP |
| 89 | Force legacy PCI hole UC TDX/SNP | x86-hw | 90 | AMD Secure AVIC Guest Support | AVIC |
| 91 | TDX host kexec/kdump | TDX | 92 | TDX Force split irqchip | TDX |
| 93 | tdx precalc TDVPR page phys | TDX | 94 | KVM: x86: Mega-CET | x86-hw/CET |
| 95 | ccp SFS driver | SEV/SNP | 96 | TDX memdup_user tdx_td_init | TDX |
| 97 | user return MSR TSC_AUX SEV-ES | SEV/SNP | 98 | TDX fix uninit error code | TDX |
| 99 | SEV Reject non-positive LAUNCH_UPD | SEV/SNP | 100 | user return MSR TSC_AUX SEV-ES | SEV/SNP |
| 101 | KVM: x86: Super Mega CET | x86-hw/CET | 102 | Secure AVIC KVM Support | AVIC |
| 103 | Secure AVIC KVM selftests | AVIC | 104 | SVM TSC_AUX clobbered | SEV/SNP |
| 105 | QEMU i386 SEV VMSA features | QEMU | 106 | Arm CCA planes support | CCA/RME |
| 107 | SEV-ES guest shadow stack | SEV/SNP | 108 | VMX Handle SEAMCALL/TDCALL exits | TDX/VMX |
| 109 | User-return MSR cleanups | x86-hw/TDX | 110 | SEV-SNP guest policy bits | SEV/SNP |
| 111 | TDX MMU lock tdh_vp_init | TDX | 112 | SVM module param SNP Secure TSC | SEV/SNP |
| 113 | User-return MSR fix+cleanups | x86-hw/TDX | 115 | sev has_cpuflag cpu_feature | SEV/SNP |
| 116 | tdx sparse fixups | TDX | 117 | TDX in place TDX.PAGE.ADD | TDX |
| 118 | TDX struct_size get_capabilities | TDX | 119 | PCI/TSM TDX Connect SPDM/IDE | SEV-TIO/TSM |
| 120 | TDX Dynamic PAMT | TDX | 121 | split_lock TDX guest | TDX |
| 122 | SEV hypervisor report SNP | SEV/SNP | 123 | arm64 SMCCC filter to pKVM | pKVM/CCA/RME |
| 124 | TDX metadata auto-gen | TDX | 125 | VMX Intel MBEC | x86-hw/VMX |
| 126 | Expose TDX Module version | TDX | 127 | TDX huge page private memory | TDX |
| 128 | QEMU query-tdx-capabilities | QEMU | 129 | arm64 FEAT_IDST | pKVM/CCA/arm-sysreg |
| 131 | SVM Drop SEV-ES DebugSwap param | SEV/SNP | 132 | tdx print module version | TDX |
| 133 | SNP certificate fetching | SEV/SNP | 134 | TDX userspace errors MAPGPA | TDX |
| 135 | QEMU target/i386 sev.h header | QEMU | 136 | SEV KVM_SEV_SNP_HV_REPORT_REQ | SEV/SNP |
| 137 | SEV mutex guards | SEV/SNP | 138 | tdx use pg_level in APIs | TDX |
| 139 | TDX Dynamic PAMT + S-EPT Hugepage | TDX | 140 | SEV Track SNP launch state | SEV/SNP |
| 141 | SEV Enable SNP AP CPU hotplug | SEV/SNP | 142 | SEV IBPB-on-Entry | SEV/SNP |
| 143 | fred SEV-ES/SNP boot failures | SEV/SNP | 144 | get quote time via tdvmcall | TDX |
| 145 | arm64 pKVM state sync | pKVM/CCA/RME | 146 | tdx Handle VMXON during bringup | TDX/VMX |
| 147 | RAPL_DIS during SNP_INIT_EX | SEV/SNP | 148 | TDX SIGNIFICANT_INDEX CPUIDs | TDX |
| 149 | x86 Emulator MMIO fix/cleanups | x86-hw/emulate | 150 | PCI/TSM SEV-TIO TDISP phase2 | SEV-TIO/TSM |
| 151 | SEV KVM_SEV_SNP_HV_REPORT_REQ | SEV/SNP | 152 | tdx cleanup TD ATTRIBUTES | TDX |
| 153 | Extend KVM_HC_MAP_GPA_RANGE retry | x86-hw/hcall | 154 | IBS virtualization | SEV/SNP/perf |
| 155 | QEMU i386/sev/igvm | QEMU | 156 | QEMU SEV-SNP SVSM interface | QEMU |
| 157 | SEV CR8 intercept SEV-ES | SEV/SNP | 158 | Fixes lock cleanup+hardening (SEV) | SEV/SNP |
| 159 | SEV BTB Isolation | SEV/SNP | 160 | SEV Drop WARN REG_REGION | SEV/SNP |
| 161 | QEMU TCG SEV emulated | QEMU | 162 | fred SEV-ES/SNP boot | SEV/SNP |
| 163 | TDX Fix APIC MSR ranges | TDX | 164 | arm64 pKVM PSCI relay | pKVM/CCA/RME |
| 165 | tdx memory hotplug guest | TDX | 166 | Revoke supported SEV VM types | SEV/SNP |
| 167 | PCI/TSM PCIe Link Enc TDX | SEV-TIO/TSM | 168 | tdx SEAMCALL helpers move | TDX |
| 169 | Fuller TDX kexec | TDX | 170 | SEV IBPB/BTB Isolation | SEV/SNP |
| 171 | TDX Fix x2APIC MSR | TDX | 172 | QEMU monitor sgx/sev | QEMU |
| 173 | SEV Don't advertise unusable types | SEV/SNP | 174 | x86 paranoid CPUID verify (TDX) | TDX/cpuid |
| 175 | tdx HKID leak kexec | TDX | 176 | SEV-SNP restricted injection | SEV/SNP |
| 177 | QEMU QOM lifecycle | QEMU | 178 | RAPL during SNP init | SEV/SNP |
| 179 | TDX MSR_IA32_PLATFORM_ID | TDX | 180 | struct page→PFN TDX private mem | TDX |
| 181 | SEV sev_dbg_crypt overhaul | SEV/SNP | 182 | MBEC/GMET support | x86-hw/mmu |
| 183 | TDX Disable PMU virtualization | TDX/x86-pmu | 185 | Enable APX for guests | x86-hw/APX |
| 186 | tdx zero-extension CPUID | TDX | 187 | arm64 CCA in KVM (44p) | CCA/RME |
| 188 | Macrofy GPR swapping | x86-hw/asm | 189 | SEV fix merge conflict | SEV/SNP |
| 190 | Runtime TDX module update | TDX | 191 | QEMU target/i386/sev leak | QEMU |
| 192 | TDX KVM selftests | TDX | 193 | TDX Module Ext DICE Quoting | TDX |
| 194 | has_protected_pmu for TDX | TDX/x86-pmu | 196 | Dynamic PAMT | TDX |
| 197 | tdx Port I/O emul fixes | TDX | 198 | MAINTAINERS TDX | chore |
| 199 | TDX MMU refactors | TDX/x86-mmu | 200 | Misc SEV/SNP fixes | SEV/SNP |
| 201 | fix various GHCB issues | SEV/SNP | 202 | Misc SEV/SNP related fixes | SEV/SNP |
| 203 | TDX Validate configurable CPUID | TDX | 204 | selftests conversion TDX | TDX |
| 205 | KVM Planes + SEV-SNP Support | SEV/SNP | 206 | SEV Don't return assigned gmem pg | SEV/SNP |
| 207 | SEV direct VMSA setting SNP | SEV/SNP | 208 | tdx-guest Quote buffer dynamic | TDX |
| 209 | Optimize nSVM TLB flushes | x86-hw/nested | 210 | DICE-based TDX Quoting Ext | TDX |
| 212 | target/arm WFxT (SEV=Send Event) | QEMU/arm(误分类) | 214 | x86/msr Inline rdmsr/wrmsr | x86-hw/msr |
| 215 | SEV Backports GHCB leak | SEV/SNP | 216 | Add RMPOPT support | SEV/SNP |
| 217 | x86 gmem populate fix/cleanups | SEV/SNP+TDX | 218 | tdx Port I/O handling bugs | TDX |
| 219 | SEV drop FOLL_LONGTERM | SEV/SNP | 220 | x86 PV clocks vs TSC (51p) | x86-hw/tsc |
| 221 | tdx no error non-present feature | TDX | 222 | TDX check_shl_overflow | TDX |
| 223 | QEMU UI/security fixes | QEMU | 224 | Add Realm support QEMU-VMM (arm) | CCA/RME/QEMU |
| 225 | TDX validated CPUID entry count | TDX | 226 | SVM SEV-SNP Secure AVIC | SEV/SNP+AVIC |
| 227 | selftests SEV TODOs | SEV/SNP | 228 | selftests SEV VM types | SEV/SNP |

> 备注：L212 "target/arm WFxT" 标题中的 "SEV/SEVL" 实为 ARM **Send-Event** 指令（WFE 配套），非 AMD SEV 机密计算——属分类误置，无论如何对 riscv KVM 内核 N-A（QEMU 用户态 arm TCG）。
