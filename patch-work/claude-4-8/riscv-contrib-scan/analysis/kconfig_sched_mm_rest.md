# §2a 其余能力符号 + N-A 簇 + §2b(201) 抽样 候选四态判定（RISC-V 贡献点静态扫描）

> 内核树只读核对：`/Users/zq/Desktop/patch-work/linux-riscv`（v7.2.0-rc3）。
> 判定前均已 grep `config`/`def_bool`/传递 select（不止看 `arch/riscv/Kconfig` 的 select），逐一排假阳。

## 摘要

- **§2a 本批候选 35 个**（46 − 11 已分他人的跟踪/NMI/断点簇）。四态计数：
  - **ALREADY 2**（PARAVIRT、NEED_DMA_MAP_STATE，均传递/已有）
  - **PORTABLE 10**、**PATTERN 10**、**N-A 13**
- **§2b 201 个**：抽样批量归类——**~165+ 为平台/SoC/时钟/irqchip/x86-legacy/ARM 固件/大页尺寸特定 → N-A**；捞出**漏网通用符号 7 个**并排掉 **~11 个假阳**（详见 §2b 节）。

### 本批 Top 候选（按价值/可行性排序）
1. **HAVE_CMPXCHG_LOCAL** → PORTABLE：riscv 已实现 `arch_cmpxchg_local`（cmpxchg.h:289），仅差一行 `select`。**同 §1 features 的 cmpxchg-local**。
2. **ARCH_SUPPORTS_SCHED_CLUSTER** → PORTABLE：riscv 已 `select GENERIC_ARCH_TOPOLOGY`+`ARCH_SUPPORTS_SCHED_MC`，arch_topology 已解析 cluster；差一行 select。
3. **ARCH_SUPPORTS_SCHED_SMT (+HOTPLUG_SMT)** → PORTABLE/PATTERN：同拓扑底座，arch_topology 已解析 DT cpu-map thread；补 select + SMT 掩码接线。
4. **ARCH_HAS_LAZY_MMU_MODE / ARCH_HAS_UACCESS_FLUSHCACHE / HAVE_ARCH_PREL32_RELOCATIONS** → PATTERN：均有 riscv HW/工具链基础（sfence 批处理 / Zicbom / R_RISCV_32_PCREL），落点明确。
5. **§2b 漏网**：**ARCH_HAS_EXECMEM_ROX / ARCH_HAS_RELR / MMU_GATHER_MERGE_VMAS** → PATTERN/PORTABLE（真缺口）。
6. **重大假阳纠正**：**GENERIC_IRQ_ENTRY 与 EXECMEM 其实 riscv 已传递获得 → ALREADY**（见下，纠正 `_baseline_riscv.md`）。

---

## Top 深度候选

### 1. HAVE_CMPXCHG_LOCAL —— PORTABLE（最强，跨 §1）
- **候选**：`HAVE_CMPXCHG_LOCAL`（来源：§2a Kconfig；def `arch/Kconfig:598`）。亦即 §1 `Documentation/features/locking/cmpxchg-local`（riscv=TODO）。
- **现状**：riscv **已实现** `arch_cmpxchg_local`（`arch/riscv/include/asm/cmpxchg.h:288-289`，映射到 `arch_cmpxchg_relaxed`）；但 `arch/riscv/Kconfig` **未** `select HAVE_CMPXCHG_LOCAL`（grep 全树 arch/riscv 无）。arm64/x86 均 `select`（arm64:181, x86:218）。
- **落点**：`arch/riscv/Kconfig` 加一行 `select HAVE_CMPXCHG_LOCAL`；实现已就位，主要收益是打开 SLUB per-cpu freelist 无锁快路径。参照 `arch/arm64/Kconfig:181`。
- **判定**：**PORTABLE** —— 能力已实现，缺的只是能力位；近零风险、可直接补，且能同时消掉 §1 features 矩阵的 TODO。

### 2. ARCH_SUPPORTS_SCHED_CLUSTER / _SMT / HOTPLUG_SMT —— PORTABLE（拓扑底座已就绪）
- **候选**：`ARCH_SUPPORTS_SCHED_CLUSTER`、`ARCH_SUPPORTS_SCHED_SMT`、`HOTPLUG_SMT`（来源：§2a Kconfig；def `arch/Kconfig:38/44/47`）。
- **现状**：riscv 已 `select GENERIC_ARCH_TOPOLOGY`（Kconfig:105）与 `ARCH_SUPPORTS_SCHED_MC if SMP`（:76），**共用 `drivers/base/arch_topology.c`**（同 arm64）解析 DT `cpu-map`（thread/core/cluster）与 ACPI PPTT；缺 SMT/CLUSTER/HOTPLUG_SMT 三个 select。arm64 全选（`arch/arm64/Kconfig:86-88, 234`）。
- **落点**：`arch/riscv/Kconfig` 增 `select ARCH_SUPPORTS_SCHED_CLUSTER`、`select ARCH_SUPPORTS_SCHED_SMT`、`select HOTPLUG_SMT if HOTPLUG_CPU`；SMT 另需确认 `topology_smt`/thread-sibling 掩码接线（arch_topology 已提供 cluster/核内掩码）。参照 arm64 拓扑路径。
- **判定**：**CLUSTER=PORTABLE**（几乎只差 select，arch_topology 已解析 cluster，SoC 多核簇立即受益）；**SMT=PORTABLE→PATTERN**（thread 掩码接线小改）；**HOTPLUG_SMT=PATTERN**（cpu_smt 控制接线，仅在有 SMT HW 时有意义）。

### 3. ARCH_HAS_NONLEAF_PMD_YOUNG —— N-A（ISA 语义所限，纠正基线倾向）
- **候选**：`ARCH_HAS_NONLEAF_PMD_YOUNG`（来源：§2a Kconfig；def `arch/Kconfig:1785`）。
- **现状**：riscv 有 `pmd_young/pmd_mkyoung`（`pgtable.h:828-844`，仅用于**叶** PMD/大页）。但本符号要求 **HW 在“非叶” PMD（指向 PTE 表的目录项）上置 A 位**。x86 select `if PGTABLE_LEVELS>2`，arm64 select `if ARM64_HAFT`（ARMv8.9 表描述符硬件访问标志）——**均为 HW 特性门控**。RISC-V 特权规范规定非叶 PTE 的 A/D/U 位保留、软件须清零，Svade/Svadu 仅对**叶**翻译更新 A/D，硬件不会在非叶 PMD 置 A。
- **判定**：**N-A** —— riscv ISA 无“非叶 PMD 置 A”硬件语义（无 ARM64_HAFT 等价扩展），MGLRU 该优化不适用。

### 4. §2b 漏网通用符号 GENERIC_IRQ_ENTRY —— ALREADY（传递假阳，纠正基线）
- **候选**：`GENERIC_IRQ_ENTRY`（来源：§2b，arm64 提供；def `arch/Kconfig:105`）。
- **现状**：`config GENERIC_ENTRY` 现 **`select GENERIC_IRQ_ENTRY` + `select GENERIC_SYSCALL`**（`arch/Kconfig:112-115`）。riscv **已** `select GENERIC_ENTRY`（`arch/riscv/Kconfig:112`），故 **传递获得 GENERIC_IRQ_ENTRY（及 GENERIC_SYSCALL）**。arm64 因未选 GENERIC_ENTRY 才直接 `select GENERIC_IRQ_ENTRY`（arm64:133）。
- **判定**：**ALREADY（假阳）** —— scan 只看 `select` 漏了 `GENERIC_ENTRY→GENERIC_IRQ_ENTRY` 传递链。**纠正 `_baseline_riscv.md` §31 与 `_taxonomy.md` 速查表把 GENERIC_IRQ_ENTRY 记为缺口/PATTERN 的说法**。

---

## §2a 全量判定表（35 个）

| 候选 | 来源 | 判定 | 缺口性质 / riscv 落点 | 备注（arm64/x86 / 假阳） |
|---|---|---|---|---|
| ARCH_SUPPORTS_SCHED_SMT | §2a | **PORTABLE** | select + thread 掩码接线；`arch/riscv/Kconfig`,`smpboot.c`/arch_topology | arm64:86 选；共用 arch_topology |
| ARCH_SUPPORTS_SCHED_CLUSTER | §2a | **PORTABLE** | 仅差 select；arch_topology 已解析 cluster | arm64:87 选；riscv 已有 SCHED_MC |
| HOTPLUG_SMT | §2a | **PATTERN** | cpu_smt 控制接线；`arch/riscv/kernel/`+Kconfig | arm64:234 `if HOTPLUG_CPU`；仅 SMT HW 有意义 |
| ARCH_HAS_LAZY_MMU_MODE | §2a | **PATTERN** | 批处理 sfence.vma；`asm/pgtable.h`+tlbflush | arm64:37/x86:808/ppc/sparc 选 |
| ARCH_HAS_UACCESS_FLUSHCACHE | §2a | **PATTERN** | pmem DAX；Zicbom CBO.flush 入 `arch/riscv/lib/uaccess` | 依赖 Zicbom（已有 HW）|
| ARCH_HAS_CACHE_LINE_SIZE | §2a | **PATTERN** | 运行时 `cache_line_size()`=riscv_cbom_block_size；`asm/cache.h` | 价值较低 |
| ARCH_HAS_CPU_CACHE_INVALIDATE_MEMREGION | §2a | **PATTERN** | nvdimm `cpu_cache_invalidate_memregion`；Zicbom | 需 pmem 场景 |
| ARCH_SUPPORTS_MEMORY_FAILURE | §2a | **PORTABLE** | mm 侧通用；门控符号；`arch/riscv/Kconfig` | 须 arch 交付 poison 故障(RAS/APEI)才有用 |
| ARCH_HAS_NONLEAF_PMD_YOUNG | §2a | **N-A** | — | ISA 非叶 PTE A/D 保留须清零；无 ARM64_HAFT 等价 |
| ARCH_USES_PG_ARCH_2 | §2a | **N-A** | — | x86=PAT/arm64=MTE；riscv 用 Svpbmt、无 MTE，无需第 2 arch 页标志 |
| HAVE_CMPXCHG_LOCAL | §2a/§1 | **PORTABLE** | 已实现，仅差 select；`asm/cmpxchg.h:289` | arm64:181/x86:218；消 §1 TODO |
| HAVE_CMPXCHG_DOUBLE | §2a | **PATTERN** | 128b CAS 需 Zacas AMOCAS.Q（可选扩展，难无条件保证）| 正被 this_cpu_cmpxchg128 取代，价值低 |
| ARCH_HAS_DMA_OPS | §2a | **N-A** | — | 仅遗留自定义 dma_ops/Xen/GART 用；“**驱动禁止 select**”；riscv 用 dma-direct+dma-iommu；arm64/x86 仅 `if XEN/GART` |
| ARCH_HAS_ZONE_DMA_SET | §2a | **PORTABLE** | 运行时设 ZONE_DMA 位；`arch/riscv/Kconfig`+mm | 可选；riscv 现用 ZONE_DMA32 |
| NEED_DMA_MAP_STATE | §2a | **ALREADY** | — | **传递**：riscv `select ARCH_HAS_SYNC_DMA_FOR_CPU`(:360)→`select NEED_DMA_MAP_STATE`(dma/Kconfig:64) |
| NEED_SG_DMA_LENGTH | §2a | **PORTABLE** | 随 IOMMU_DMA 免费获得；`drivers/iommu/Kconfig:158` | 现 RISCV_IOMMU 未选 IOMMU_DMA→暂不需要 |
| CPUMASK_OFFSTACK | §2a | **PORTABLE** | 通用 lib（大 NR_CPUS）；`arch/riscv/Kconfig` | 非 arch 门控，可直接开 |
| GENERIC_ALLOCATOR | §2a | **PORTABLE** | 通用 lib（gen_pool）；驱动按需 select | 非 arch 能力；价值低 |
| GENERIC_CPU_AUTOPROBE | §2a | **PATTERN** | CPU modalias/模块自加载；需 arch cpu uevent 钩子；`drivers/base` | 价值较低 |
| GENERIC_IRQ_PROBE | §2a | **N-A** | — | 遗留 ISA IRQ 自探测 probe_irq_on/off；riscv 无此类驱动 |
| HAVE_ARCH_PREL32_RELOCATIONS | §2a | **PATTERN** | R_RISCV_32_PCREL + 模块加载器；`arch/riscv/kernel/module.c` | 64 位半尺寸 fixup/initcall 表；中等 |
| ARCH_WANT_DEFAULT_BPF_JIT | §2a | **PORTABLE** | 一行 select（默认开 JIT 策略）；riscv 已有全 BPF JIT | arm64/x86 选；价值/风险低 |
| POWER_SUPPLY | §2a | **N-A** | — | 驱动子系统 tristate，用户可选；非 arch 能力 |
| PARAVIRT | §2a | **ALREADY** | — | `config PARAVIRT`@`arch/riscv/Kconfig:1127`（基线已知假阳）|
| ARCH_HAS_CC_PLATFORM | §2a | **N-A** | — | 机密计算 SEV/TDX/CCA；riscv CoVE **在途未合** |
| ARCH_HAS_MEM_ENCRYPT | §2a | **N-A** | — | 同上（CoVE 在途）|
| ARCH_HAS_FORCE_DMA_UNENCRYPTED | §2a | **N-A** | — | 同上（CoVE 在途）|
| ARCH_HAS_PKEYS | §2a | **N-A** | — | PKU/POE 硬件保护键；riscv 无 ISA |
| ARCH_HAS_CPU_RESCTRL | §2a | **N-A** | — | RDT/MPAM QoS；riscv 无 HW（Ssqosid 在途未合）|
| ACPI_HOTPLUG_CPU | §2a | **PATTERN** | ACPI 物理 CPU 热插；`arch/riscv/kernel/acpi.c` | riscv ACPI 尚浅，价值低 |
| ARCH_HAS_ACPI_TABLE_UPGRADE | §2a | **PORTABLE** | initrd ACPI 表覆盖，早初始化较通用 | riscv ACPI，价值低 |
| HAVE_ACPI_APEI | §2a | **PATTERN** | APEI/GHES 错误上报；需 ACPI+RAS | riscv ACPI/RAS 尚浅 |
| HAVE_UID16 | §2a | **N-A** | — | 16 位 UID 遗留 syscall；新架构无包袱 |
| COMPAT_OLD_SIGACTION | §2a | **N-A** | — | 遗留 32 位 sigaction ABI；riscv compat 不带此老 ABI |
| OLD_SIGSUSPEND3 | §2a | **N-A** | — | 遗留 sigsuspend ABI 变体；不需要 |

---

## §2b（201）抽样批量归类

### 分类计数（抽样估算）
| 判定 | 约数 | 典型 |
|---|---|---|
| **N-A** | ~165+ | 平台/SoC/时钟/irqchip：Apple(APPLE_AIC/PMGR)、MVEBU(GICP/ICU/ODMI/PIC/SEI)、Exynos(CLKSRC_EXYNOS_MCT/EXYNOS_PMU/PM_DOMAINS)、Rockchip/Samsung(SOC_SAMSUNG)/TI(SOC_TI/TI_K3_SOCINFO)/IMX(IMX_GPCV2*)/STM32/Sunxi(SUN6I_R_INTC/SUNXI_NMI_INTC)/NPCM/OWL/MTK/DW_APB_*/HISILICON_IRQ_MBIGEN/ALPINE_MSI；x86-legacy(GEODE_COMMON/OLPC_EC/HAVE_EISA/CLK*_I8253/RTC_MC146818_LIB/HAVE_PCSPKR_PLATFORM/ARCH_MIGHT_HAVE_PC_PARPORT/SERIO/INSTRUCTION_DECODER/IOSF_MBI/GENERIC_CMOS_UPDATE/EARLY_PRINTK_USB)；ARM 固件(HAVE_ARM_SMCCC/HAVE_ARM_ARCH_TIMER/REGULATOR_ARM_SCMI)；ARM ACPI(ACPI_APMT/GTDT/IORT/CCA_REQUIRED)；大页尺寸(HAVE_PAGE_SIZE_16KB/64KB，riscv 仅 4K 基页+Svnapot 连续)；objtool 簇(OBJTOOL/HAVE_OBJTOOL*/HAVE_STACK_VALIDATION/HAVE_*_VALIDATION/HAVE_NOINSTR_HACK/CALL_THUNKS/CALL_PADDING，x86 中心)；DYNAMIC_SCS（riscv 有 Zicfiss HW 影子栈，优先 HW）；KMAP_LOCAL（rv64 无 highmem）|
| **ALREADY(假阳)** | ~11 | 见下“排假阳” |
| **PATTERN** | ~15-20 | 见下“漏网通用”+ x86 ftrace/kprobes 变体(HAVE_DYNAMIC_FTRACE_WITH_REGS/HAVE_FENTRY/HAVE_KPROBES_ON_FTRACE/HAVE_OPTPROBES/ARCH_CORRECT_STACKTRACE_ON_KRETPROBE，交叉 `feat_official`)；ARCH_HAS_COPY_MC、ARCH_CPUIDLE_HALTPOLL（基线已列 PATTERN）|
| **PORTABLE** | ~3-6 | MMU_GATHER_MERGE_VMAS、XARRAY_MULTI、NUMA_MEMBLKS/NUMA_KEEP_MEMINFO(若 riscv NUMA)、GENERIC_IOMAP 等通用 lib |

### 漏网通用能力符号（单独判定）
| 符号 | 提供方 | 判定 | 说明 / riscv 落点 |
|---|---|---|---|
| **GENERIC_IRQ_ENTRY** | arm64 | **ALREADY** | 传递：riscv `select GENERIC_ENTRY`→`select GENERIC_IRQ_ENTRY`(`arch/Kconfig:114`)。**纠正基线** |
| **EXECMEM** | x86 | **ALREADY** | 传递：KPROBES(`arch/Kconfig:121`)/MODULES(`kernel/module/Kconfig:5`)/BPF_JIT(`kernel/bpf/Kconfig:46`) 均 select；riscv 三者皆有 |
| **ARCH_HAS_EXECMEM_ROX** | x86 | **PATTERN** | W^X ROX 模块 text 缓存；riscv 有 text-patching 底座；`arch/riscv/` + execmem 钩子。真缺口，中等 |
| **ARCH_HAS_RELR** | arm64 | **PATTERN** | RELR 压缩重定位（缩小 KASLR 重定位）；需 linker+重定位处理；`arch/riscv/`。中等 |
| **MMU_GATHER_MERGE_VMAS** | x86 | **PORTABLE** | mmu_gather 合并相邻 VMA 的 opt-in 标志；需 riscv tlb flush 容忍合并区间；低风险 |
| **UNWIND_TABLES** | arm64 | **PATTERN** | 保留 .eh_frame 供 SFrame/unwinder；低-中等 |
| **DYNAMIC_SCS** | arm64 | **N-A/低** | SW 影子调用栈（arm64 无 GCS 时用）；riscv 有 Zicfiss HW 影子栈，优先 HW |

### 排假阳（riscv 其实已有/非 arch 门控，scan 只看 select 误报）
| 符号 | 提供方 | 真相 |
|---|---|---|
| VMAP_STACK | arm64 | riscv `select HAVE_ARCH_VMAP_STACK if MMU && 64BIT`(:153) → ALREADY |
| JUMP_LABEL | arm64 | riscv `select HAVE_ARCH_JUMP_LABEL(_RELATIVE)`(:134-135) → ALREADY |
| PERF_EVENTS | x86 | riscv `select HAVE_PERF_EVENTS`(:192)，perf 可用 → ALREADY |
| MMU_NOTIFIER | x86 | KVM 传递 `select MMU_NOTIFIER`(`virt/kvm/Kconfig:8`)；riscv KVM 有 → ALREADY/可用 |
| DEBUG_FS | x86 | 通用调试项(`lib/Kconfig.debug:708`)，非 arch 门控，riscv 可用 → ALREADY |
| RTC_LIB | x86 | 由 RTC_CLASS 传递 select(`drivers/rtc/Kconfig:11,17`)，非 arch 门控 |
| PTDUMP | x86 | riscv **已有** `arch/riscv/mm/ptdump.c` → ALREADY |
| IRQ_DOMAIN_HIERARCHY | x86 | 由 irqchip 驱动传递 select(`drivers/irqchip/Kconfig:11,38,56`)；riscv AIA/PLIC 驱动带 |
| GENERIC_IRQ_CHIP | arm64 | 同上，irqchip 驱动传递；非 arch 门控 |
| PHYS_ADDR_T_64BIT | x86 | riscv 64BIT 下 def_bool 自动 y（通用），非缺口 |
| KMAP_LOCAL | x86 | highmem 相关；rv64 无 highmem → N-A（仅 rv32+highmem 才涉及）|

---

## 判定纪律落实说明
- **排假阳**：本批新捕获 3 例传递/已有假阳——**GENERIC_IRQ_ENTRY**、**EXECMEM**（传递 select）、**NEED_DMA_MAP_STATE**（传递 select），另确认 §2b 11 例 scan 口径假阳；PARAVIRT 复核为 ALREADY。
- **无 HW/ISA 不拔高**：ARCH_HAS_NONLEAF_PMD_YOUNG（非叶 A 位）、ARCH_HAS_PKEYS、ARCH_HAS_CPU_RESCTRL、机密计算三件套、ARCH_USES_PG_ARCH_2 均据 ISA/HW 缺失判 N-A。
- **通用底座拆 PORTABLE**：SCHED_CLUSTER/SMT、HAVE_CMPXCHG_LOCAL、MEMORY_FAILURE、MMU_GATHER_MERGE_VMAS 等因通用层/已有实现就位判 PORTABLE。
- **arm64/x86 参照**：每条 PORTABLE/PATTERN 均已核对对端 select 位置作落点参照。
