# 分类法与层级定义（linux-arm-kernel → RISC-V）

## 三层级 + 噪声

- **Tier A — GENERIC（通用/跨架构）**：改动落在通用代码（`mm/`、`kernel/`、`lib/`、`include/linux`、`drivers/` 框架、
  `Documentation/`、`tools/`、`selftests/`），或虽经 arm 列表但**架构无关**。→ 多 **PORTABLE**，部分对 riscv **自动适用**。
- **Tier B — ARCH-PATTERN（arch 模式可移植）**：`arch/arm64`（或 `arch/arm`）中概念/机制 riscv 也有或可有的实现——
  mm、cpufeature/alternatives/errata、perf、entry、vdso、trace/probe/bpf、atomics/locking、signal/ptrace、kexec、boot、acpi。
  → 机制可复用，需在 `arch/riscv/*` 重写，判 **PATTERN**（或 riscv 已有 → **ALREADY**）。
- **Tier C — HW/ISA-SPECIFIC（硬件/ISA 专属，低/无可移植）**：ARM 专有硬件或 ISA——GIC/ITS/GICv4、arm-SMMU、
  PSCI/SMCCC/SCMI/FF-A 固件 ABI、MTE/PAC/SME/SPE、板级 DTS、厂商 SoC 驱动。→ 判 **N-A**，除非补丁**扩展了通用底座**。
- **噪声（kind=noise）**：`dts-board`/`soc-driver`/`defconfig`/`pull-request`/`unrelated-cc`/`firmware-abi`——
  对 riscv 无可移植价值，分类器批量判 **N-A**，README 仅计数 + 抽样示例，**不逐条分析**。

## 四态判定 rubric

| 判定 | 含义 | 证据要求 |
|---|---|---|
| **ALREADY** | riscv 已实现等价能力 | 引 `_baseline_riscv.md` 或本地源码路径 |
| **PORTABLE** | 通用/架构无关，改动几乎直接适用 riscv | 说明为何是通用代码（文件在 `mm/`、`kernel/`… 或无 arch 依赖）|
| **PATTERN** | arch 专属实现，机制可复用需重写 | 给出**具体 riscv 落点文件** + 需改写的点 |
| **N-A** | 依赖 ARM 专有 HW/ISA 且无 riscv 对应、不扩展通用底座 | 指出所依赖的 ARM 专属硬件/ISA |

**判定纪律：**
1. 不把 riscv **已有**特性误报为「可移植」——先查基线（如 Svnapot/RVV/Zabha/Zicfilp/kexec/bpf-jit 都已实现）。
2. 不把**纯 ARM 硬件/ISA**（GIC/SMMU/PAC/MTE/SME/板级 DTS）拔高为可移植。
3. Tier-C 系列若**仅扩展了通用底座**（如通用 sanitizer 框架、mm 通用接口、`prctl`/ABI 协商），
   把「通用底座部分」标 PORTABLE 并注明，其余标 N-A。
4. `arch=generic`（无 arch 前缀）的信号系列**优先考虑 PORTABLE**；`arch=arm`（`arm64:`/`ARM:` 前缀）优先考虑 PATTERN/ALREADY。

## arm64 机制 ↔ riscv 落点 对应表（判定速查）

| arm64 机制 | riscv 对应 | riscv 落点 | 默认判定倾向 |
|---|---|---|---|
| contiguous-PTE (contpte) | **Svnapot** | `arch/riscv/mm/hugetlbpage.c` | ALREADY / PATTERN(增量优化) |
| BBML2 大块映射 | （无直接等价，Svvptc 邻域） | `arch/riscv/mm/`, `pgtable.h` | PATTERN |
| `rodata=full` | 无 | `arch/riscv/mm/pageattr.c`, `init.c` | PATTERN |
| HW AF/DBM | **Svade/Svadu** | `arch/riscv/kernel/cpufeature.c`, `pgtable-bits.h` | ALREADY |
| LSE 原子 | **Zabha/Zacas** | `arch/riscv/include/asm/cmpxchg.h`, `atomic.h` | ALREADY / PATTERN |
| WFE 自旋等待 | **Zawrs** | `arch/riscv/include/asm/barrier.h` | ALREADY |
| qspinlock | combo spinlock | `arch/riscv/include/asm/spinlock.h` | ALREADY |
| MIDR/sysreg cpufeature | ISA 串 + hwprobe + alternatives | `arch/riscv/kernel/cpufeature.c`, `sys_hwprobe.c` | PATTERN |
| errata 框架 | 四厂商 errata | `arch/riscv/errata/*` | ALREADY / PATTERN |
| arm_pmuv3 | **riscv_pmu(SBI)** + sscofpmf | `drivers/perf/riscv_pmu_sbi.c` | ALREADY / PATTERN |
| SPE 统计采样 | 无（仅 sscofpmf 溢出采样） | — | N-A / 部分 PORTABLE(perf core) |
| SVE 可伸缩向量 | **RVV** | `arch/riscv/kernel/vector.c` | ALREADY / PATTERN |
| SME 矩阵 | 无 | — | N-A |
| BTI 落地页 | **Zicfilp** | `arch/riscv/kernel/usercfi.c` | ALREADY / PATTERN |
| GCS 影子栈 | **Zicfiss** | `arch/riscv/kernel/usercfi.c` | ALREADY / PATTERN |
| PAC 指针认证 | 无 | — | N-A |
| MTE 内存标签 | 无（仅 Supm 掩码） | — | N-A |
| TBI/tagged-addr ABI | **Supm** | `arch/riscv/kernel/process.c` | ALREADY / PATTERN |
| KASAN SW_TAGS/HW_TAGS | 无（仅 generic） | `arch/riscv/mm/kasan_init.c` | PORTABLE(SW_TAGS 通用) / N-A(HW_TAGS 需 MTE) |
| KCSAN / KMSAN | 无 | `arch/riscv/` + Kconfig | PORTABLE |
| ftrace/kprobes/bpf-jit | 已对等 | `arch/riscv/kernel/`, `net/` | ALREADY / PATTERN(增量) |
| vDSO | 已有 | `arch/riscv/kernel/vdso/` | ALREADY / PATTERN |
| entry/exception | 已 GENERIC_ENTRY；缺 GENERIC_IRQ_ENTRY | `arch/riscv/kernel/entry.S`, `traps.c`, `irq.c` | PATTERN |
| kexec/kdump | 已对等 | `arch/riscv/kernel/machine_kexec*.c` | ALREADY / PATTERN |
| ACPI(MADT/IORT…) | RINTC/RHCT/RIMT | `arch/riscv/kernel/acpi.c` | PATTERN(架构无关部分 PORTABLE) |
| GIC/ITS/GICv4 中断控制器 | AIA(APLIC/IMSIC) | `drivers/irqchip/irq-riscv-*` | N-A(HW 内部) / PORTABLE(通用 irq 基础设施) |
| arm-SMMU IOMMU | riscv IOMMU | `drivers/iommu/riscv/` | N-A(HW 特定) |
| PSCI/SMCCC/SCMI/FF-A 固件 | SBI | `arch/riscv/kernel/sbi.c` | N-A(不同 ABI；仅思想类比) |

## 信号桶 → 主分析文件 对应

| 类别 (category) | 层级 | 输出文件 |
|---|---|---|
| mm-pgtable | B | `analysis/mm_pgtable.md` |
| cpufeature-alt | B | `analysis/cpufeature_alt.md` |
| perf-pmu | B | `analysis/perf_pmu.md` |
| entry-exception | B | `analysis/entry_exception.md` |
| vdso | B | `analysis/vdso.md` |
| trace-probe | B | `analysis/trace_probe.md` |
| atomics-locking | B | `analysis/atomics_locking.md` |
| vector-fp | B | `analysis/vector_fp.md` |
| security-hw | B | `analysis/security_hw.md` |
| signal-ptrace-elf | B | `analysis/signal_ptrace_elf.md` |
| kexec-crash | B | `analysis/kexec_crash.md` |
| acpi-arch | B | `analysis/acpi_arch.md` |
| boot-head | B | `analysis/boot_head.md` |
| irqchip | C | `analysis/irqchip.md` |
| generic-cross | A | `analysis/generic_cross.md` |
| docs-tooling | A | `analysis/docs_tooling.md` |
| misc-arch | B | `analysis/misc_arch.md` |
