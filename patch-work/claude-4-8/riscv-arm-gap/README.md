# linux-arm-kernel 补丁 → RISC-V 可移植性汇总（2025-01-01 ~ 2026-07-10）

> 目标：以 **linux-arm-kernel 邮件列表**为源，收集时间区间内**全部补丁**，逐一分析其移植到 **RISC-V 架构**的可能性，
> 列举潜在可移植补丁，并标注「**原补丁 ↔ 可移植点 ↔ RISC-V 落点**」的对应关系。
> 辅助源码：`/Users/zq/Desktop/patch-work/linux-riscv`（Linux v7.2.0-rc3，只读核对）。

---

## TL;DR

- **数据规模**：区间内 linux-arm-kernel 共 **66,718** 个补丁（去重 id 后），归并为 **10,745** 个逻辑补丁系列。
- **信噪分离**：**8,062（75%）系列对 RISC-V 是「硬件噪声」**（板级 DTS、SoC/厂商驱动、defconfig、pull-request、被抄送的无关子系统、ARM 固件 ABI）——批量判 N-A；仅 **2,683（25%）系列**是架构核心信号，逐类送 18 个子代理深度判定。
- **可移植性结论**（对 2,683 信号系列四态判定）：
  - **PORTABLE ≈ 450**（通用/架构无关代码，改动几乎直接适用 riscv）
  - **PATTERN ≈ 210**（arch 专属实现，机制可复用，需在 `arch/riscv/*` 重写）
  - **ALREADY ≈ 61**（riscv 已实现等价能力）
  - **N-A ≈ 1,962**（依赖 ARM 专有硬件/ISA：GIC/ITS/SMMU/MTE/PAC/SME/SPE/pKVM…）
- **⇒ 约 660 个系列（PORTABLE+PATTERN）具备移植/借鉴价值**；本文 §4 精选 **Top 46** 候选并给出落点。
- **最高价值方向**：mm 硬化（`rodata=full`/BBML2 大块映射/KASAN SW_TAGS/COPY_MC）、通用等待原语（`smp_cond_load_*_timeout`↔Zawrs）、
  内核栈回溯与热补丁（SFrame/livepatch/reliable-stacktrace）、`static_call`、ACPI/cacheinfo/topology 通用底座、以及大量**已自带 riscv 补丁**的跨架构系列。

> **数据源说明（patchwork ↔ pipermail 等价）**：本研究用 `patchwork.kernel.org/project/linux-arm-kernel` 的 REST API 作为结构化索引。
> 它与用户给出的 `lists.infradead.org/pipermail/linux-arm-kernel/` 是**同一条邮件列表**——patchwork 自动从该列表邮件中抽取「补丁」
> 并附带 series/version/state/date 元数据，正好等于「收集所有补丁」的需求，且可按日期/系列/状态过滤、可复现。

---

## 1. 方法论

### 1.1 数据源与区间
- Patchwork REST API（无需鉴权，已验证 200）：
  `https://patchwork.kernel.org/api/1.2/patches/?project=linux-arm-kernel&since=2025-01-01T00:00:00&before=2026-07-10T00:00:00&per_page=250&page=N&order=date`
- 每条记录取 `id/name/date/state/submitter/series[id,name,version]/web_url/mbox/msgid`。深挖候选时用 `mbox` 取补丁全文（含 diff）核实。
- 脚本见 `scripts/fetch_patches.py`（267 页并发抓取 + 断点续抓 + 重试）与 `scripts/classify.py`（分类/去重/打标签）。

### 1.2 分层策略（应对 6.7 万补丁规模）
逐条为万级补丁写散文不现实，故采用「**全量自动分类索引 + 候选深度分析**」：
1. **抓全量元数据**（66,718 条）；
2. **按 series 归一化去重**（去 `[vN]`/`[PATCH]`/`m/n`，保留最新版本）→ 10,745 逻辑系列；
3. **关键词分类器**打标签：先吸收高置信噪声（DTS/pull/defconfig），再精准命中 arch 核心信号桶（mm/cpufeature/perf/…），最后广谱噪声兜底；
4. **每个信号桶派 1 个子代理**（大桶分片，共 18 个）做四态判定，对每桶最强 3-6 候选 `curl` 取补丁全文 + Grep 核对 riscv 落点；
5. 主代理综合成文。

### 1.3 四态判定 rubric
| 判定 | 含义 |
|---|---|
| **ALREADY** | riscv 已实现等价能力（引基线/源码为证）|
| **PORTABLE** | 通用/架构无关代码（`mm/`、`kernel/`、`lib/`、`drivers/` 框架、`Documentation/`、`tools/`），改动几乎直接适用 riscv |
| **PATTERN** | arch 专属实现，机制/思想可复用，需在 `arch/riscv/*` 重写；给出具体落点 |
| **N-A** | 依赖 ARM 专有硬件/ISA 且 riscv 无对应、不扩展通用底座 |

判定纪律：**先查 RISC-V 基线**（`analysis/_baseline_riscv.md`），不把 riscv **已有**特性（Svnapot/RVV/Zabha/Zicfilp/kexec/bpf-jit…）误报为可移植；不把**纯 ARM 硬件/ISA**（GIC/SMMU/PAC/MTE/SME）拔高为可移植；Tier-C 若仅扩展通用底座，则通用部分记 PORTABLE。

---

## 2. 数据总览

| 指标 | 数值 |
|---|---|
| 原始补丁（去重 id 后）| 66,718 |
| series 版本 | 19,319 |
| 去重逻辑系列 | **10,745** |
| 信号系列（送子代理）| **2,683（25.0%）** |
| 噪声系列（批量 N-A）| **8,062（75.0%）** |

**架构归属**：generic（无 arch 前缀）6,052 · arm（arm64/ARM 前缀或 arm 专有术语）4,607 · other 86。

**噪声桶**（对 riscv 无移植价值，批量判 N-A，仅计数 + 抽样）：
`dts-board` 3,694 · `soc-driver` 2,323 · `unrelated-cc` 1,084 · `pull-request` 592 · `firmware-abi` 255 · `defconfig` 114。
> 抽样示例（均 N-A）：`arm64: dts: rockchip: Add Orange Pi 5 Max board`、`clk: xilinx: vcu: ...`、`iommu/arm-smmu-qcom: ...`、`media: rkvdec: ...`、`[GIT,PULL] Qualcomm Arm64 DeviceTree fixes`。

---

## 3. 可移植性框架：arm64 机制 ↔ riscv 落点

RISC-V 架构树在近年已相当成熟，**大量 arm64 特性已有 riscv 等价物**（判 ALREADY），这决定了本研究的候选主要落在「通用底座」与「arch 尚缺的模式」两类。核心对应关系（完整表见 `analysis/_taxonomy.md`）：

| arm64 机制 | riscv 现状 | 落点 | 倾向 |
|---|---|---|---|
| contiguous-PTE (contpte) | **Svnapot 已有** | `arch/riscv/mm/hugetlbpage.c` | ALREADY（共享化=PORTABLE）|
| LSE 原子 / WFE / qspinlock | **Zabha/Zacas / Zawrs / combo-spinlock 已有** | `asm/{cmpxchg,barrier,spinlock}.h` | ALREADY |
| SVE 可伸缩向量 | **RVV 已有** | `arch/riscv/kernel/vector.c` | ALREADY / PATTERN |
| BTI / GCS 影子栈 / TBI | **Zicfilp / Zicfiss / Supm 已有** | `arch/riscv/kernel/usercfi.c` | ALREADY / PATTERN |
| arm_pmuv3 / sscofpmf | **riscv_pmu(SBI) 已有** | `drivers/perf/riscv_pmu_sbi.c` | ALREADY / PATTERN |
| ftrace / kprobes / BPF-JIT / kexec / vdso / ACPI | **均已对等** | `arch/riscv/kernel`, `net`, `acpi.c` | ALREADY / PATTERN |
| **`rodata=full` 全线性映射 RO / BBML2 大块映射** | **缺**（仅 STRICT_RWX + 按需拆分）| `arch/riscv/mm/pageattr.c`, `init.c` | **PATTERN** |
| **KASAN SW_TAGS / KCSAN / KMSAN** | **缺**（仅 KASAN-generic + KFENCE）| `arch/riscv/mm/kasan_init.c` + Kconfig | **PORTABLE** |
| **ARCH_HAS_COPY_MC**（机器检查内存拷贝）| **缺** | `arch/riscv/lib/` + `Kconfig` | **PORTABLE+PATTERN** |
| **static_call / HAVE_LIVEPATCH / SFrame 回溯 / GENERIC_IRQ_ENTRY** | **缺** | `arch/riscv/kernel/{stacktrace,entry}` + Kconfig | **PATTERN** |
| **haltpoll/poll_idle (TIF_POLLING_NRFLAG)** | **缺** | `arch/riscv` + `drivers/cpuidle` | **PORTABLE+PATTERN** |
| MTE 内存标签 / PAC 指针认证 / SME 矩阵 / SPE 采样 | **无对应 ISA** | — | **N-A** |
| GIC/ITS/GICv3-5 / arm-SMMU | riscv 用 AIA(APLIC/IMSIC) / riscv-IOMMU | `drivers/irqchip/irq-riscv-*` | N-A（通用 genirq/MSI 底座=PORTABLE）|

---

## 4. Top 46 可移植候选排名

> 列：**原补丁**（linux-arm-kernel 系列名）→ **可移植点** → **RISC-V 落点** → **判定** → **来源**。
> 「来源」为 patchwork 直链或对应 `analysis/*.md`（其中含完整 web_url + mbox + diff 级分析）。★=已核实补丁自带 riscv 侧改动或作者来自 riscv 厂商。

### P1 — 旗舰（填补 riscv 真实缺口 / 通用底座直接受益 / 已带 riscv 补丁）

| 原补丁 | 可移植点 | RISC-V 落点 | 判定 | 来源 |
|---|---|---|---|---|
| **Merge arm64/riscv hugetlbfs contpte support** ★ | 抽 contpte/napot 公共逻辑到 `mm/hugetlb_contpte.c` 共享 | `mm/hugetlb_contpte.c`(新) + `arch/riscv/mm/hugetlbpage.c` | PORTABLE | [patchwork](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250321130635.227011-4-alexghiti@rivosinc.com/) |
| **barrier: smp_cond_load_{relaxed,acquire}_timeout()** | 通用带超时等待原语；riscv 侧接 Zawrs `wrs.nto` | `asm-generic/barrier.h`, `include/linux/atomic.h` + `arch/riscv/include/asm/barrier.h` | PORTABLE+PATTERN | [patchwork](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260702013334.140905-8-ankur.a.arora@oracle.com/) |
| **arm64: support FEAT_BBM level 2 + large block mapping when rodata=full** | 保留大块线性映射、按权限变更再拆分（riscv 无 `rodata=full` 等价）| `arch/riscv/mm/pageattr.c`, `mm/init.c` | PATTERN | [patchwork](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250917190323.3828347-3-yang@os.amperecomputing.com/) |
| **KASAN: 架构无关化 SW_TAGS**（作者含 SiFive）★ | 让 SW_TAGS 模式脱离 arch 依赖，为 riscv 铺路 | `arch/riscv/mm/kasan_init.c` + `Kconfig`(select) | PORTABLE | `analysis/mm_pgtable_1.md` |
| **unwind, arm64: add SFrame unwinder for kernel** | 通用 SFrame 栈回溯核 + arch 启用（riscv 缺可靠栈回溯）| `kernel/unwind/*` + `arch/riscv/kernel/stacktrace.c` | PORTABLE+PATTERN | [patchwork](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260519064950.493949-2-dylanbhatch@google.com/) |
| **Add support for parse_acpi_topology() on RISC-V** ★ | 把 `parse_acpi_topology()` 移到通用码供 riscv 复用（补丁自述）| `drivers/base/arch_topology.c` + `arch/riscv/kernel/smpboot.c` | PORTABLE | [patchwork](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250923015409.15983-2-cuiyunhui@bytedance.com/) |
| **arm64: add ARCH_HAS_COPY_MC support** | 机器检查安全内存拷贝（riscv 确认缺 `ARCH_HAS_COPY_MC`）| `arch/riscv/lib/` + `include/linux/uaccess.h` + `Kconfig` | PORTABLE+PATTERN | [patchwork](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260618092124.3901230-7-tianruidong@linux.alibaba.com/) |
| **mm/sparse-vmemmap 通用 vmemmap_{set,check}_pmd** ★ | 删 arch 私有 helper 改用通用码（补丁自带 riscv patch）| `mm/sparse-vmemmap.c` + `arch/riscv/mm/init.c` | PORTABLE | `analysis/mm_pgtable_1.md` |

### P2 — 高价值（arch 缺口，机制清晰，落点明确）

| 原补丁 | 可移植点 | RISC-V 落点 | 判定 | 来源 |
|---|---|---|---|---|
| **arm64: Use static call trampolines when kCFI is enabled** | `HAVE_STATIC_CALL(_INLINE)`（riscv 尚缺）| `arch/riscv/kernel/{static_call.c(新),patch.c}` + `Kconfig` | PATTERN | [patchwork](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260331110422.301901-2-ardb+git@google.com/) |
| **arm64: entry: Convert to generic irq entry** | `GENERIC_IRQ_ENTRY`（riscv IRQ 内核态入口仍手写）| `arch/riscv/Kconfig` + `kernel/{entry.S,irq.c,traps.c}` | PATTERN | `analysis/entry_exception.md` |
| **arm64: Implement HAVE_LIVEPATCH + reliable stacktrace** | 热补丁 + 可靠栈回溯（riscv 有 ftrace 底座但缺 livepatch）| `arch/riscv/kernel/stacktrace.c` + `Kconfig` | PATTERN | `analysis/misc_arch_3.md` |
| **arm64: kexec: crashkernel CMA reservation** | 通用 `reserve_crashkernel_cma()` 已在树内，riscv 仅需 ~4 行接线 | `arch/riscv/mm/init.c` | PATTERN | [patchwork](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260126081334.699147-1-ruanjinjie@huawei.com/) |
| **arm64/crash: crash hotplug support** | CPU/内存热插拔时更新 crash elfcorehdr（riscv 缺）| `arch/riscv/kernel/crash.c`(新) + `asm/kexec.h` + `Kconfig` | PATTERN | `analysis/misc_arch_1.md` |
| **arm64: support poll_idle() / cpuidle-haltpoll** | `TIF_POLLING_NRFLAG` + `ARCH_HAS_OPTIMIZED_POLL` + haltpoll（riscv 全缺）| `arch/riscv/include/asm/thread_info.h` + `drivers/cpuidle` | PORTABLE+PATTERN | [patchwork](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250218213337.377987-12-ankur.a.arora@oracle.com/) |
| **futex: runtime-const 优化** ★ | `runtime_const_*`（补丁系列已含 riscv 补丁）| `arch/riscv/include/asm/runtime-const.h` | PORTABLE | `analysis/misc_arch_1.md` |
| **bpf: Mitigate Spectre v1 using barriers** | verifier 核心 + arch JIT `bpf_jit_bypass_spec` | `kernel/bpf/verifier.c` + `arch/riscv/net/bpf_jit_comp64.c` | PORTABLE+PATTERN | `analysis/trace_probe.md` |
| **kernel: hq-spinlock（自适应排队自旋锁）** | 通用 `kernel/locking` 新锁，实测 nginx +68~78% | `kernel/locking/` | PORTABLE | `analysis/atomics_locking.md` |
| **Resilient Queued Spin Lock (rqspinlock)** | 通用死锁可恢复自旋锁 | `kernel/bpf/rqspinlock.c` + `include/asm-generic` | PORTABLE | `analysis/trace_probe.md` |
| **ftrace,bpf: single direct ops for bpf trampolines** | 通用 ftrace/trampoline 核重构（riscv DIRECT_CALLS 受益）| `kernel/trace/` + `arch/riscv/kernel/ftrace.c` | PORTABLE | `analysis/trace_probe.md` |
| **page_table_check 重新引入 addr 参数** | 通用 mm API 签名变更，所有架构须适配 | `arch/riscv/include/asm/pgtable.h` | PORTABLE | `analysis/mm_pgtable_1.md` |
| **persistent huge zero folio + set_direct_map_ro_noflush** | riscv 缺 `set_direct_map_ro_noflush` | `arch/riscv/mm/pageattr.c` | PORTABLE+PATTERN | `analysis/mm_pgtable_1.md` |

### P3 — 中等（通用框架受益 / arch 适配 / 硬化）

| 原补丁 | 可移植点 | RISC-V 落点 | 判定 | 来源 |
|---|---|---|---|---|
| arm64: per-CPU 原子用 load-LSE | riscv **无 `asm/percpu.h`**，可用 AMO 实现优化 | `arch/riscv/include/asm/percpu.h`(新) | PATTERN | `analysis/atomics_locking.md` |
| arm64: unaligned atomic emulation | riscv `traps.c` 已有 misaligned 框架可扩展 + prctl | `arch/riscv/kernel/traps.c` + uapi | PATTERN+PORTABLE | `analysis/atomics_locking.md` |
| arm64: VA_BITS=52 → ARCH_MMAP_RND_BITS_MAX | riscv 动态 Sv39/48/57 同类 mmap 随机化问题 | `arch/riscv/Kconfig` + `mm` | PATTERN | `analysis/misc_arch_3.md` |
| arm64 tlbflush 单-CPU 免广播快路径 | riscv 有 mm_cpumask 但无 active_cpu 快路径 | `arch/riscv/mm/tlbflush.c` + `asm/mmu.h` | PATTERN | `analysis/misc_arch_1.md` |
| APEI: 共享 GHES CPER helpers + DT FFH provider | firmware-first RAS 抽成可复用模块 | `drivers/acpi/apei/`, `drivers/ras/` | PORTABLE | `analysis/acpi_arch.md` |
| cacheinfo: cache-id / size-by-level 通用助手 | 通用 `drivers/base/cacheinfo.c`（riscv 同用 DT/PPTT）| `drivers/base/cacheinfo.c` (+arch hook) | PORTABLE | `analysis/misc_arch_3.md` |
| CPPC FFH 框架改进 | 通用 CPPC 核（riscv 已有 SBI CPPC-FFH）| `drivers/acpi/cppc_acpi.c` | PORTABLE | `analysis/acpi_arch.md` |
| kcov: unique PC/EDGE/CMP modes | 通用 `kernel/kcov.c`（riscv 有 `ARCH_HAS_KCOV`）| `kernel/kcov.c` | PORTABLE | `analysis/misc_arch_3.md` |
| lib/crc: 改进 arch-optimized 集成 | 为 riscv 建 arch 加速槽位（riscv 已有 `lib/crc/riscv/`）| `lib/crc/` | PORTABLE | `analysis/misc_arch_3.md` |
| lib/crypto: GHASH/gf128hash 通用化 | 库框架统一（riscv Zvkg 加速属 ALREADY）| `lib/crypto/gf128hash.c` | PORTABLE | `analysis/vector_fp.md` |
| Kexec HandOver (KHO) 泛化 | 架构无关 live-update 框架 | `kernel/liveupdate/kexec_handover.c` | PORTABLE | `analysis/mm_pgtable_2.md` |
| kdump: 传 dm-crypt(LUKS) 密钥给 kdump | 通用 `crash_dump_dm_crypt.c` 已存在，riscv 未接 | `arch/riscv/kernel/machine_kexec_file.c` | PATTERN | `analysis/boot_kexec_userabi.md` |
| arm64: ptrace 用 live x0 for seccomp/audit | riscv 共享同缺陷（`orig_a0`）| `arch/riscv/include/asm/syscall.h` | PATTERN | `analysis/boot_kexec_userabi.md` |
| mm: mprotect() large-folio 优化 + batched unmap | 通用 mm 批处理，riscv 经通用路径获益 | `mm/mprotect.c`, `mm/rmap.c` | PORTABLE | `analysis/mm_pgtable_2.md` |
| pagetable ctor/dtor 系列 | 通用页表构造/析构（补丁内直接改 riscv）| `arch/riscv/include/asm/pgalloc.h` | PORTABLE | `analysis/mm_pgtable_2.md` |
| emit ENDBR/BTI for indirect jump targets | 核层 CFI + riscv Zicfilp `lpad` | `kernel/` + `arch/riscv/net/bpf_jit_comp64.c` | PORTABLE+PATTERN | `analysis/trace_probe.md` |
| dma-mapping: 批量 cache sync | 通用 `kernel/dma` + arch nosync dcache helper | `kernel/dma/` + `arch/riscv/mm/dma-noncoherent.c` | PORTABLE+PATTERN | `analysis/misc_arch_2.md` |

### P4 — 机会 / 测试 / 文档 / 通用中断底座

| 原补丁 | 可移植点 | RISC-V 落点 | 判定 | 来源 |
|---|---|---|---|---|
| genirq/msi + msi-lib + irqdomain 清理 | 通用 MSI 框架（riscv IMSIC/sg2042-msi 已消费）| `kernel/irq/msi.c`, `include/linux/msi.h` | PORTABLE | `analysis/irqchip.md` |
| iommu: MSI mapping w/ nested（核心部分）| `genirq/msi` + `iommu-dma` MSI 通用化 | `kernel/irq/`, `drivers/iommu/dma-iommu.c` | PORTABLE | `analysis/irqchip.md` |
| iommufd: 缓存失效边界硬化 | 通用 iommufd 核（riscv IOMMU 受益）| `drivers/iommu/iommufd/` | PORTABLE | `analysis/security_hw.md` |
| kcfi: Prepare for GCC support | 通用 CFI 报告标准化 + `cfi=` bootparam | `kernel/cfi.c` | PORTABLE | `analysis/security_hw.md` |
| KUnit: suppress warning backtraces | 通用 KUnit 基础设施 | `lib/kunit/bug.c` | PORTABLE | `analysis/docs_tooling.md` |
| KVM selftests 框架/类型清理（8 条）| `tools/testing/selftests/kvm/`（riscv 子目录已存在）| `tools/.../kvm/riscv/` | PORTABLE | `analysis/docs_tooling.md` |
| raid6: 用户态测试改 kunit | `lib/raid6/`（含 `riscv/recov_rvv.c`）| `lib/raid6/test/`, `tests/` | PORTABLE | `analysis/docs_tooling.md` |
| exec: Remove AT_VECTOR_SIZE_ARCH from UAPI | treewide UAPI 清理，riscv `auxvec.h` 需同步 | `arch/riscv/include/asm/auxvec.h` | PATTERN | `analysis/docs_tooling.md` |
| arm64: Use generic TIF bits | riscv `thread_info.h` 可采用 asm-generic TIF 编号 | `arch/riscv/include/asm/thread_info.h` | PATTERN | `analysis/docs_tooling.md` |
| arch,sysfb,efi: 非 x86 EFI 系统 EDID 支持 | 通用 efi/libstub（riscv 是非 x86 EFI 架构）| `drivers/firmware/efi/` | PORTABLE | `analysis/misc_arch_2.md` |

---

## 5. 各类别四态计数汇总

| 类别 | 层级 | 系列 | ALREADY | PORTABLE | PATTERN | N-A |
|---|---|---:|---:|---:|---:|---:|
| mm-pgtable | B | 361 | 7 | 103 | 46 | 205 |
| perf-pmu | B | 285 | 8 | 21 | 3 | 253 |
| cpufeature-alt | B | 143 | 2 | 9 | 10 | 122 |
| atomics-locking | B | 71 | 1 | 9 | 10 | 51 |
| trace-probe | B | 71 | 4 | 33 | 26 | 8 |
| vector-fp | B | 60 | 2 | 6 | 15 | 37 |
| entry-exception | B | 58 | 5 | 12 | 20 | 21 |
| security-hw | B | 45 | 1 | 8 | 13 | 23 |
| acpi-arch | B | 54 | 0 | 26 | 2 | 26 |
| boot/kexec/vdso/signal | B | 59 | 7 | 19 | 14 | 19 |
| irqchip | C | 192 | 1 | 20 | 2 | 169 |
| docs-tooling | A | 208 | 0 | 39 | 2 | 167 |
| misc-arch | B | 605 | 23 | 38 | 46 | 498 |
| generic-cross | A | 471 | 0 | 107 | 1 | 363 |
| **信号合计** | | **2,683** | **≈61** | **≈450** | **≈210** | **≈1,962** |
| 噪声合计 | C/- | 8,062 | — | — | — | 8,062 |

> 每类明细（含全量逐系列判定表 + web_url + mbox + diff 级核实）见 `analysis/<类别>.md`。

---

## 6. 结论与移植路线建议

1. **RISC-V arch 已高度成熟**：contpte(Svnapot)/RVV/LSE(Zabha,Zacas)/WFE(Zawrs)/BTI(Zicfilp)/GCS(Zicfiss)/TBI(Supm)/
   kexec/bpf-jit/ftrace/vdso/ACPI 皆已落地——故 arm64 的大量特性对 riscv 是 **ALREADY**，真正的机会集中在少数「通用底座」与「arch 尚缺模式」。
2. **优先级建议**：
   - **近期低风险高收益**：`smp_cond_load_*_timeout`（接 Zawrs）、`crashkernel CMA`（~4 行）、`page_table_check addr`、pagetable ctor/dtor、
     大量**已自带 riscv 补丁**的跨架构系列（contpte 共享化 / vmemmap / futex runtime-const）——跟随主线合入即可。
   - **中期能力补齐**：`static_call` → `HAVE_LIVEPATCH`、`SFrame`/reliable-stacktrace、`GENERIC_IRQ_ENTRY`、`ARCH_HAS_COPY_MC`、
     haltpoll/`TIF_POLLING_NRFLAG`——均是 riscv 明确缺口，arm64 提供了成熟蓝本。
   - **中期硬化**：`rodata=full`/BBML2 大块映射、KASAN SW_TAGS、KCSAN/KMSAN——mm 与 sanitizer 方向，价值高但工作量较大。
3. **明确不追**：MTE/PAC/SME/SPE（无对应 ISA）、GIC/ITS/GICv3-5、arm-SMMU、pKVM/CCA、板级 DTS 与厂商 SoC 驱动——占噪声主体，判 N-A。
4. **对 RISC-V 社区的启示**：linux-arm-kernel 上「通用核心 + arch 消费者」式的系列（MSI/irqdomain、cacheinfo/topology、ACPI RAS、
   lib/crc、lib/crypto、kcov）是低成本搭便车的富矿——riscv 常已是这些通用框架的消费者，跟随其演进即自动受益。

---

## 附录

### A. 目录结构
```
riscv-arm-gap/
├── README.md                 本文（综合汇总 + Top 46 候选）
├── scripts/
│   ├── fetch_patches.py       抓取 patchwork linux-arm-kernel 元数据（并发+续抓）
│   └── classify.py            分类/去重/打标签
├── data/
│   ├── arm_series.csv         10,745 逻辑系列权威索引（kind/tier/category/arch/state/date/系列名/web_url）
│   ├── category_counts.md     分类统计
│   └── by_category/*.jsonl    按类别分组的精简记录（含 web_url/mbox/sample_titles，供分析追溯）
│   # 注：全量原始转储 all_patches.jsonl（66,718 条 / ~41MB）为可再生中间产物，
│   #     已从仓库精简移除；`python3 scripts/fetch_patches.py` 可重新生成。
└── analysis/
    ├── _baseline_riscv.md     RISC-V arch 能力基线（判定依据）
    ├── _taxonomy.md           分类法 + arm64↔riscv 机制对应表
    ├── _agent_instructions.md 子代理通用指令
    └── <14 类>.md             各类别可移植性明细（含全量逐系列判定表）
```

### B. 复现步骤
```bash
cd riscv-arm-gap/scripts
python3 fetch_patches.py   # → data/all_patches.jsonl（断点续抓，可中断重跑）
python3 classify.py        # → arm_series.csv / category_counts.md / by_category/
```

### C. 局限与口径
- **数据源口径**：patchwork 只登记「被识别为补丁」的邮件，纯讨论帖不计入——这正是「所有补丁」所需口径；与 pipermail 原始归档的差异仅在于后者含讨论噪声。
- **分类为关键词启发式**：存在少量误分类（如 DRM「atomic-KMS」曾误入 atomics 桶、已在分析中甄别为 N-A）；噪声/信号边界以「是否值得逐条深挖」为准，个别边缘系列可能落在 misc-arch/generic-cross 催化桶。
- **四态计数**为各子代理自报的近似值（合计口径以 `classify.py` 的 2,683 信号 / 8,062 噪声为准）；每个 PORTABLE/PATTERN 候选均可经 `analysis/*.md` 追溯到 patchwork web_url 与 riscv 落点。
- 时间区间 `2025-01-01 ~ 2026-07-10`，`state=*`（含各状态），按 series 去重保留最新版本。
