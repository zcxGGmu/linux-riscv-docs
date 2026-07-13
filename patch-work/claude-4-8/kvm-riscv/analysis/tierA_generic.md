# Tier A 通用层（GENERIC）可移植性分析

> 输入：`A_guest_memfd.jsonl`(10) · `A_core.jsonl`(4) · `A_io-irq-infra.jsonl`(3) · `A_docs.jsonl`(4) = **21 系列**
> 判定依据：`_baseline_riscv.md` + 本地树 `/Users/zq/Desktop/patch-work/linux-riscv`（Linux 7.2.0-rc3）源码核对 + 5 条候选 curl mbox 全文。

## 摘要

- **系列总数 21**：ALREADY **1** / PORTABLE **11** / PATTERN **2** / N-A **7**
- 本批**重中之重 = guest_memfd 启用**：通用引擎（`virt/kvm/guest_memfd.c`、`KVM_CAP_GUEST_MEMFD*`、内存属性、gmem-only memslot、INIT_SHARED 共享 mmap）**已全部在树内**，riscv 仅未 `select`。核对确认 `arch/riscv/` 零 `guest_memfd`/`gmem` 引用，Kconfig 未 select（`arch/riscv/kvm/Kconfig:23-34`），而 arm64 已 select（`arch/arm64/kvm/Kconfig:39`）、x86 亦然。
- **关键落点**：`arch/riscv/kvm/Kconfig`（加 `select KVM_GUEST_MEMFD`）+ `arch/riscv/kvm/mmu.c:535 kvm_riscv_mmu_map()`（加 arm64 式 `gmem_abort()` 分支调 `kvm_gmem_get_pfn()`）。arm64 参照实现：`arch/arm64/kvm/mmu.c:1608 gmem_abort()`，调用点 `mmu.c:2418-2419`。

### 本类 Top 候选（按价值排序）

| # | 系列 | 判定 | 一句话价值 |
|---|---|---|---|
| 1 | **guest_memfd 启用（S3/S4 基线簇）** | PORTABLE | 通用引擎已在树，riscv `select`+一个 fault 钩子即得机密内存底座 |
| 2 | **S9 gmem-only memslot 脏页日志** | PORTABLE | 纯 `virt/kvm/*`，为 gmem 后端客户机补上脏跟踪/迁移能力 |
| 3 | **S8 in-place 转换 / 内存属性可选化** | PORTABLE | 通用 memattr 大重构（未合入），riscv 将一并受益 |
| 4 | **S6 gmem Direct Map Removal** | PORTABLE | 通用 mm+gmem 加固（去除内核直映射） |
| 5 | **core S1 lock_all_vcpus 抽取** | ALREADY | riscv 已切换（`aia_device.c:30`），作参照锚点 |
| 6 | **io-irq S2 修正悬空 irqfd bypass** | PORTABLE | `virt/kvm/eventfd.c` 通用 bugfix |

---

## Top 可移植候选（深度）

### 1. guest_memfd 启用（S1/S2/S3/S4/S5/S7 基线簇 → 高价值）
- **原补丁**：
  - S3 v12「Mapping guest_memfd for SW-protected VMs」x86 18p（https://patchwork.kernel.org/project/kvm/patch/20250611133330.1514028-14-tabba@google.com/）state=new — 通用**改名/中立化**：`CONFIG_KVM_PRIVATE_MEM→KVM_GMEM`、`kvm_arch_has_private_mem()→kvm_arch_supports_gmem()`、`kvm_slot_can_be_private()→kvm_slot_has_gmem()`。
  - S4 v2「guest_memfd: MMAP and related fixes」x86 13p（https://patchwork.kernel.org/project/kvm/patch/20251003232606.4070510-8-seanjc@google.com/）state=new — `KVM_CAP_GUEST_MEMFD_FLAGS`、`GUEST_MEMFD_FLAG_INIT_SHARED`、允许对 gmem `mmap()`（软件保护/非 CoCo VM 也可用）。
- **可移植点**：整套通用引擎位于 `virt/kvm/guest_memfd.c`（25886 B，已在树）+ `virt/kvm/kvm_main.c` 的 CAP/ioctl 布线：`KVM_CAP_GUEST_MEMFD`(kvm_main.c:4930)、`KVM_CAP_GUEST_MEMFD_FLAGS`(4932)、`KVM_CAP_MEMORY_ATTRIBUTES`(4926)、`KVM_SET_MEMORY_ATTRIBUTES`(5330)、`kvm_gmem_create`(5376)。arch 钩子全部 opt-in（`CONFIG_HAVE_KVM_ARCH_GMEM_PREPARE/INVALIDATE/POPULATE`），非机密路径**无需实现**。
- **riscv 落点**：① `arch/riscv/kvm/Kconfig` 增 `select KVM_GUEST_MEMFD`（软件保护型再加 `KVM_GENERIC_MEMORY_ATTRIBUTES`）；② `arch/riscv/kvm/mmu.c:535 kvm_riscv_mmu_map()` 内，当 `kvm_slot_has_gmem(memslot)` 时走 `kvm_gmem_get_pfn()` 而非 `__kvm_faultin_pfn()`。依据：本地核对确认通用符号 `GUEST_MEMFD_FLAG_INIT_SHARED`(guest_memfd.c:154)、`KVM_CAP_GUEST_MEMFD_FLAGS 244`(uapi/kvm.h:994)、`kvm_arch_supports_gmem_init_shared __weak`(guest_memfd.c:555) 均**已在树**；arm64 同款落点 `arch/arm64/kvm/mmu.c:1608`。
- **判定**：**PORTABLE** —— 通用引擎已在树、riscv 仅缺 Kconfig select + 一个 fault 钩子（arm64 已示范）。

### 2. S9「Dirty page logging for guest_memfd-only memslots」（arm RFC 3p，未合入）
- **原补丁**：https://patchwork.kernel.org/project/kvm/patch/20260702142912.6395-3-alexandru.elisei@arm.com/ state=new
- **可移植点**：curl 确认 patch 2/3「Implement dirty page logging for guest_memfd-only memslots」**仅触通用文件**：`virt/kvm/guest_memfd.c`、`virt/kvm/kvm_main.c`、`virt/kvm/kvm_mm.h`、`include/linux/kvm_host.h`、`include/uapi/linux/kvm.h`、`Documentation/virt/kvm/api.rst`。patch 1/3（用 memslot id 跟踪关联 memslot）亦通用。为无 userspace HVA 的 gmem-only memslot 补脏页跟踪 → 直接支撑热迁移。
- **riscv 落点**：通用层一次生效；riscv 侧仅需 patch 3/3 类比（arm64 版是数行「允许 gmem-only memslot 脏日志」开关）落到 `arch/riscv/kvm/mmu.c` 的 memslot flags 校验。前提是先启用 gmem（候选 1）。gmem-only 概念已在树：`KVM_MEMSLOT_GMEM_ONLY`(guest_memfd.c:692)、`kvm_memslot_is_gmem_only()`(kvm_host.h:2528)。
- **判定**：**PORTABLE** —— 核心增量纯 `virt/kvm/*`。

### 3. S8「guest_memfd: In-place conversion support」（x86 v8 46p，未合入）
- **原补丁**：https://patchwork.kernel.org/project/kvm/patch/20260618-gmem-inplace-conversion-v8-21-9d2959357853@google.com/ state=new
- **可移植点**：通用 memattr 大重构 —— 每-gmem 属性（patch 01）、`KVM_GENERIC_MEMORY_ATTRIBUTES→KVM_VM_MEMORY_ATTRIBUTES` 改名（02）、使其**可选化/可 select**（05）、解耦 `kvm_arch_has_private_mem` 与 CONFIG（04）。curl 确认 patch 21/46 仅触 `virt/kvm/guest_memfd.c`。本地核对 `KVM_VM_MEMORY_ATTRIBUTES` **尚未在树**（属未来增量）。
- **riscv 落点**：通用层受益；riscv 若走「私有内存属性」路线可 `select KVM_VM_MEMORY_ATTRIBUTES`。x86 就地转换 glue（SEV/TDX 相关）对 riscv 为 N-A。
- **判定**：**PORTABLE**（通用 memattr/gmem 部分）；机密转换 glue 部分 N-A。

### 4. S6「Direct Map Removal Support for guest_memfd」（x86 v12 16p）
- **原补丁**：https://patchwork.kernel.org/project/kvm/patch/20260410151746.61150-7-kalyazin@amazon.com/ state=new
- **可移植点**：多为跨架构 mm/ 层（`set_memory` 取址化、`folio_{zap,restore}_direct_map`、`mm/gup` 调整、`AS_NO_DIRECT_MAP`）+ 通用 gmem 挂钩，将 gmem 页移出内核直映射以增强隔离。
- **riscv 落点**：通用 gmem 侧一次生效；依赖 arch `set_direct_map_*`（riscv 已有 `CONFIG_ARCH_HAS_SET_DIRECT_MAP`）。前提为候选 1。
- **判定**：**PORTABLE**（通用 gmem/mm 部分）。

### 5. core S1「extract lock_all_vcpus/unlock_all_vcpus」（x86+arm v2 4p）
- **原补丁**：https://patchwork.kernel.org/project/kvm/patch/20250409014136.2816971-2-mlevitsk@redhat.com/ state=new
- **落点/依据**：**已合入且 riscv 已切换**。本地核对 `arch/riscv/kvm/aia_device.c:30/42` 已调 `kvm_trylock_all_vcpus()/kvm_unlock_all_vcpus()`；通用实现 `virt/kvm/kvm_main.c:1358-1415`；该系列 patch 4/4 即「RISC-V: KVM: switch to kvm_lock/unlock_all_vcpus」。
- **判定**：**ALREADY**（作为「通用抽取→riscv 直接消费」的锚点范例）。

### 6. io-irq S2「Fix dangling IRQ bypass on x86 and arm64」（x86+arm 2p）
- **原补丁**：https://patchwork.kernel.org/project/kvm/patch/20260113174606.104978-2-seanjc@google.com/ state=new
- **可移植点**：patch 1/2「Don't clobber irqfd routing type when deassigning irqfd」为 `virt/kvm/eventfd.c` 通用 bugfix。
- **riscv 落点**：通用层一次生效（`virt/kvm/eventfd.c`）；但 riscv 未 `select HAVE_KVM_IRQ_BYPASS`（Kconfig 核对确认缺失），悬空 producer 路径当前不可达，价值随未来 IMSIC 直注启用而兑现。
- **判定**：**PORTABLE**（通用修复，低-中价值）。

---

## 全量判定表（21 系列）

| 系列 | 判定 | 可移植点(若有) | riscv 落点(若有) | web_url |
|---|---|---|---|---|
| GMF-S1 Mapping gmem@host + SW-protected VM (arm v1 9p) | PORTABLE | 通用 gmem host-mmap 基础设施；arm fault glue 为 PATTERN | `arch/riscv/kvm/mmu.c:535` fault 钩子 + Kconfig select | https://patchwork.kernel.org/project/kvm/patch/20250122152738.1173160-10-tabba@google.com/ |
| GMF-S2 Restricted mapping + arm64 (arm v7 7p) | PORTABLE | 通用 folio 共享状态机（guest_memfd.c）；arm64 部分 PATTERN | `virt/kvm/guest_memfd.c`(通用) + riscv fault 钩子 | https://patchwork.kernel.org/project/kvm/patch/20250328153133.3504118-7-tabba@google.com/ |
| GMF-S3 Mapping gmem for SW-protected VMs (x86 v12 18p) | PORTABLE | 通用改名/中立化 `has_private_mem→supports_gmem`、CONFIG_KVM_GMEM | 通用层；riscv 定义 gmem 支持谓词 | https://patchwork.kernel.org/project/kvm/patch/20250611133330.1514028-14-tabba@google.com/ |
| GMF-S4 MMAP and related fixes (x86 v2 13p) | PORTABLE | `KVM_CAP_GUEST_MEMFD_FLAGS`+`INIT_SHARED` 共享 mmap（**已在树**） | `Kconfig: select KVM_GUEST_MEMFD` + `mmu.c:535` | https://patchwork.kernel.org/project/kvm/patch/20251003232606.4070510-8-seanjc@google.com/ |
| GMF-S5 move kvm_gmem_get_index() (x86 v3 2p) | PORTABLE | `virt/kvm/guest_memfd.c` 微清理 | 通用，随 gmem 启用生效 | https://patchwork.kernel.org/project/kvm/patch/20251012071607.17646-2-shivankg@amd.com/ |
| GMF-S6 Direct Map Removal for gmem (x86 v12 16p) | PORTABLE | 通用 mm(`AS_NO_DIRECT_MAP`/`set_memory`)+gmem 挂钩 | 通用；依赖 riscv `set_direct_map_*` | https://patchwork.kernel.org/project/kvm/patch/20260410151746.61150-7-kalyazin@amazon.com/ |
| GMF-S7 MAINTAINERS + guest_memfd.h 拆分 (x86 RFC 5p) | PORTABLE | patch2/5 通用头文件拆分（`guest_memfd.h`）；余 MAINTAINERS 中性 | 通用 | https://patchwork.kernel.org/project/kvm/patch/20260428171541.1342335-4-seanjc@google.com/ |
| GMF-S8 In-place conversion support (x86 v8 46p) | PORTABLE | 通用 memattr 重构（`KVM_VM_MEMORY_ATTRIBUTES` 可选化，**未在树**）；x86 转换 glue=N-A | 通用；私有内存路线可 select | https://patchwork.kernel.org/project/kvm/patch/20260618-gmem-inplace-conversion-v8-21-9d2959357853@google.com/ |
| GMF-S9 Dirty logging for gmem-only memslots (arm RFC 3p) | PORTABLE | patch1-2/3 纯 `virt/kvm/*` 脏页日志；patch3/3 arm64 开关=PATTERN | 通用层生效；riscv `mmu.c` memslot flags 类比开关 | https://patchwork.kernel.org/project/kvm/patch/20260702142912.6395-3-alexandru.elisei@arm.com/ |
| GMF-S10 Add gmem support for arm64 (**kvmtool** v2 4p) | N-A | 用户态 VMM(kvmtool) 补丁，非内核；riscv 需自做 kvmtool 侧支持 | 内核 KVM 无落点（用户态工作） | https://patchwork.kernel.org/project/kvm/patch/20260708182510.2181857-3-fuad.tabba@linux.dev/ |
| CORE-S1 extract lock_all_vcpus (x86+arm v2 4p) | ALREADY | — | riscv 已切换 `aia_device.c:30`；通用 `kvm_main.c:1358` | https://patchwork.kernel.org/project/kvm/patch/20250409014136.2816971-2-mlevitsk@redhat.com/ |
| CORE-S2 x86 WFS vs pending SMI WARN (x86 4p) | N-A | x86 SMM/SMI + SIPI/INIT MP_STATE 语义，riscv 无 SMM | — | https://patchwork.kernel.org/project/kvm/patch/20250605195018.539901-5-seanjc@google.com/ |
| CORE-S3 per-vCPU vLPI injection API (arm RFC 13p) | N-A | GICv4 vLPI/vPE 硬件；patch1 通用 Kconfig 但特性绑 ITS，riscv AIA 无对应 | — | https://patchwork.kernel.org/project/kvm/patch/20251120140305.63515-9-mdittgen@amazon.de/ |
| CORE-S4 arm64 memslot for ST_GPA_BASE in check_steal_time_uapi (arm 1p) | PATTERN | **selftest** 修复模式；riscv 已有 steal-time(SBI STA)+steal_time 自测 | `tools/testing/selftests/kvm/steal_time.c`(riscv 部分) | https://patchwork.kernel.org/project/kvm/patch/20260501021639.2563219-1-xujiakai2025@iscas.ac.cn/ |
| IO-S1 iommu: Overhaul device posted IRQs (x86+arm v3 62p) | N-A | 设备直投(AVIC/Intel PI/GICv4+IOMMU IRTE)硬件；patch3/62 通用 irqfd 管道为底座 | 无消费者（riscv 未选 IRQ_BYPASS）；作未来 IMSIC 直注模式参考 | https://patchwork.kernel.org/project/kvm/patch/20250611224604.313496-4-seanjc@google.com/ |
| IO-S2 Fix dangling IRQ bypass (x86+arm 2p) | PORTABLE | patch1/2 通用 `virt/kvm/eventfd.c` bugfix | 通用生效；riscv 未选 bypass 故当前不可达 | https://patchwork.kernel.org/project/kvm/patch/20260113174606.104978-2-seanjc@google.com/ |
| IO-S3 arm64 set irqfd->producer for vLPI (arm RFC 1p) | N-A | arm64 vLPI producer 布线 | — | https://patchwork.kernel.org/project/kvm/patch/20260623081433.21250-1-leixiang@kylinos.cn/ |
| DOC-S1 x86 Strengthen kvm_lock rules (x86 2p) | PORTABLE | patch2/2 `Documentation` 通用锁序指南；patch1/2 x86 特定 | 文档/通用锁规约，适用全架构 | https://patchwork.kernel.org/project/kvm/patch/20250124191109.205955-2-pbonzini@redhat.com/ |
| DOC-S2 arm64 SIGBUS VMM for SEA guest abort (arm RFC v3 3p) | PATTERN | 「客户机内存错误经 SIGBUS/退出报 VMM」机制+UAPI 文档；core 为 arm64 SEA/ESR 专属 | riscv 可类比 access-fault→VMM 路径（`vcpu_exit.c`/新 UAPI） | https://patchwork.kernel.org/project/kvm/patch/20250220232959.247600-1-jiaqiyan@google.com/ |
| DOC-S3 x86,fs/resctrl Global BW Enforcement (x86 RFC 19p) | N-A | x86 RDT/MBA resctrl，非 KVM 核心，无 riscv 对应 | — | https://patchwork.kernel.org/project/kvm/patch/a4ca7d43100132b79adba85a4674c7b46b05bb8c.1769029977.git.babu.moger@amd.com/ |
| DOC-S4 Documentation: Synchronize x86 VM types (x86 1p) | N-A | x86 VM 类型文档 | — | https://patchwork.kernel.org/project/kvm/patch/20260603114504.814647-2-clopez@suse.de/ |

---

## 核对证据锚点（本地树 Linux 7.2.0-rc3）

- riscv Kconfig 无 gmem select：`arch/riscv/kvm/Kconfig:23-34`；`arch/riscv/` 全树 0 处 `guest_memfd`/`gmem`。
- arm64 已 select：`arch/arm64/kvm/Kconfig:39 select KVM_GUEST_MEMFD`（并 `:52 select PTDUMP`）；x86 `select KVM_GUEST_MEMFD if X86_64` + `KVM_GENERIC_MEMORY_ATTRIBUTES`。
- 通用引擎在树：`virt/kvm/guest_memfd.c`(25886 B)；CAP/ioctl 布线 `virt/kvm/kvm_main.c:4926/4930/4932/5330/5376`。
- S4 已合入：`GUEST_MEMFD_FLAG_INIT_SHARED`(guest_memfd.c:154)、`KVM_CAP_GUEST_MEMFD_FLAGS 244`(uapi/kvm.h:994)、`kvm_arch_supports_gmem_init_shared __weak`(guest_memfd.c:555)。
- gmem-only：`KVM_MEMSLOT_GMEM_ONLY`(guest_memfd.c:692)、`kvm_memslot_is_gmem_only()`(kvm_host.h:2528)。
- S8 未合入：全树无 `KVM_VM_MEMORY_ATTRIBUTES`。
- core S1 已落 riscv：`arch/riscv/kvm/aia_device.c:30/42`；通用 `virt/kvm/kvm_main.c:1358-1415`。
- riscv 未选 IRQ bypass：`arch/riscv/kvm/Kconfig` 无 `HAVE_KVM_IRQ_BYPASS`（arm64 `:34` 有）。
- arm64 gmem fault 参照：`arch/arm64/kvm/mmu.c:1608 gmem_abort()`，调用点 `:2418-2419`；riscv 对应落点 `arch/riscv/kvm/mmu.c:535 kvm_riscv_mmu_map()`。
