# 分类法与四态判定（RISC-V 贡献点静态扫描）

> 本轮候选 = 三路**源码树静态信号**：
> - **§1** 官方 `Documentation/features` 矩阵中 riscv=TODO（6 项，最可信）
> - **§2** Kconfig 能力差集：arm64∪x86 有、riscv 未 `select`（§2a=arm64+x86 都有 46 个；§2b=仅一家 201 个）
> - **§3** arch/riscv 及 riscv 驱动内 TODO/FIXME/桩（54 处）
>
> 判定语义：**「该缺口是否值得且可行地在 riscv 补上」**。

## 四态 rubric

| 判定 | 含义 | 证据要求 |
|---|---|---|
| **ALREADY** | riscv 其实已实现（scan 误报/假阳） | 引 `_baseline_riscv.md` 或本地源码路径/行号 |
| **PORTABLE** | 可直接 `select` 或补通用层钩子(`mm/ kernel/ lib/ include/linux/ 框架 Documentation/ tools/`)，几乎直接适用 | 说明为何通用/无 arch 依赖 |
| **PATTERN** | 需在 `arch/riscv/*` 实现 arch 专属部分，机制可参照 arm64/x86 | 给出**具体 riscv 落点文件** + 改写点 |
| **N-A** | riscv 无对应硬件/ISA 语义、不适用/不需要 | 点名所依赖的专属硬件/ISA |

## 判定纪律

1. **先查基线再判**——riscv 已有 Svnapot/RVV/Zabha/Zacas/Zawrs/Zicfilp/Zicfiss/Supm/combo-spinlock/kexec/bpf-jit/ftrace/vdso/ACPI/KFENCE/VMAP_STACK/**PARAVIRT** 等，勿误报为缺口。
2. **排假阳（本轮关键）**——§2 符号判定前**必** grep `config <SYM>` / `def_bool` / 传递 select，**不止看** `arch/riscv/Kconfig* 的 select`。（scan 口径只看 select，PARAVIRT 即因此假阳。参见 `_baseline_riscv.md` §四高假阳清单。）
3. 不把**无对应 HW/ISA**（MTE/PAC/SME/SPE/GIC/ITS/SMMU/PKU/RDT/MPAM）拔高为可移植。
4. Tier-C 若**仅需扩展通用底座**（通用 sanitizer / mm 接口 / perf core / prctl-ABI），把通用部分标 PORTABLE 并注明，arch/HW 部分标 PATTERN/N-A。
5. §1 官方矩阵最可信；判定时同时记录 **arm64/x86 是否已做**：都做→PORTABLE/PATTERN 优先且有双参照；仅一家→参照那家；都没做→价值低（可剔除）。

## arm64 / x86 机制 ↔ riscv 落点 速查表

| 对端机制 | riscv 对应 | riscv 落点 | 默认判定倾向 |
|---|---|---|---|
| contiguous-PTE (contpte) | **Svnapot** | `arch/riscv/mm/hugetlbpage.c` | ALREADY / PATTERN(增量) |
| BBML2 大块映射 | （无直接等价） | `arch/riscv/mm/`, `pgtable.h` | PATTERN |
| `rodata=full` | 无 | `arch/riscv/mm/pageattr.c`, `init.c` | PATTERN |
| HW AF/DBM | **Svade/Svadu** | `arch/riscv/kernel/cpufeature.c` | ALREADY |
| LSE 原子 | **Zabha/Zacas** | `arch/riscv/include/asm/cmpxchg.h`, `atomic.h` | ALREADY / PATTERN |
| WFE 自旋等待 | **Zawrs** | `arch/riscv/include/asm/barrier.h` | ALREADY |
| qspinlock | combo spinlock | `arch/riscv/include/asm/spinlock.h` | ALREADY |
| `cmpxchg_local`(小字对象) | LR/SC 或 Zabha 可实现 | `arch/riscv/include/asm/cmpxchg.h` | PORTABLE / PATTERN |
| SVE / SME | **RVV** / 无 | `arch/riscv/kernel/vector.c` / — | ALREADY / N-A(SME) |
| BTI / GCS / TBI | **Zicfilp / Zicfiss / Supm** | `arch/riscv/kernel/usercfi.c`, `process.c` | ALREADY / PATTERN |
| PAC / MTE | 无 | — | N-A |
| KASAN SW_TAGS / KCSAN / KMSAN | 无(仅 generic+KFENCE) | `arch/riscv/mm/kasan_init.c` + Kconfig | PORTABLE(通用) / N-A(HW_TAGS 需 MTE) |
| **static_call**(x86/arm64) | 无 | `arch/riscv/kernel/` + text-patch, `include/asm/static_call.h`(新) | PATTERN |
| **HAVE_LIVEPATCH** | 无(需 reliable stacktrace) | `arch/riscv/kernel/stacktrace.c` + Kconfig | PORTABLE/PATTERN |
| **HAVE_RELIABLE_STACKTRACE** | 无 | `arch/riscv/kernel/stacktrace.c` | PATTERN |
| **ARCH_HAS_COPY_MC**(x86) | 无 | `arch/riscv/lib/` + 异常表 | PATTERN |
| **NMI / hardlockup-perf** | 无真 NMI(AIA 可支撑) | `drivers/irqchip/irq-riscv-*`, `arch/riscv/kernel/` | PATTERN |
| **haltpoll / TIF_POLLING_NRFLAG**(x86) | 无 | `arch/riscv/include/asm/thread_info.h` + cpuidle | PATTERN |
| **HAVE_HW_BREAKPOINT** | debug trigger 未接框架 | `arch/riscv/kernel/hw_breakpoint.c`(新) | PATTERN |
| **SMT/cluster 调度** | 拓扑 | `arch/riscv/kernel/smpboot.c` + topology/Kconfig | PORTABLE / PATTERN |
| ftrace/kprobes/bpf-jit | 已对等 | `arch/riscv/kernel/`, `net/` | ALREADY / PATTERN(增量) |
| entry/exception | 已 GENERIC_ENTRY **→传递 GENERIC_IRQ_ENTRY**(arch/Kconfig:114) | `arch/riscv/kernel/entry.S`, `irq.c` | ALREADY |
| kexec/kdump / vDSO | 已对等 | `arch/riscv/kernel/` | ALREADY / PATTERN |
| ACPI(MADT/IORT…) | RINTC/RHCT/RIMT | `arch/riscv/kernel/acpi.c` | PATTERN(架构无关部分 PORTABLE) |
| GIC/ITS/GICv4 | AIA(APLIC/IMSIC) | `drivers/irqchip/irq-riscv-*` | N-A(HW 内部) / PORTABLE(通用 irq 基础设施) |
| arm-SMMU IOMMU | riscv IOMMU | `drivers/iommu/riscv/` | N-A(HW 特定) / PATTERN(通用 iommu 能力) |
| PSCI/SMCCC/SCMI/FF-A 固件 | SBI | `arch/riscv/kernel/sbi.c` | N-A(不同 ABI) |
| **pkeys(PKU/POE) / resctrl(RDT/MPAM)** | 无 | — | N-A |
| **mem_encrypt/CC(SEV/TDX/CCA)** | CoVE 在途未合 | — | N-A(注明在途) |
| **legacy compat(UID16/OLD_SIG*)** | 新架构无包袱 | — | N-A(不需要) |

## 三路信号 → 子代理 → 输出文件

| 信号路 | 子代理 | 输出 |
|---|---|---|
| §1 features TODO(6) | `feat_official` | `analysis/feat_official.md` |
| §2a 跟踪/调试/NMI 硬化簇 | `kconfig_trace_nmi` | `analysis/kconfig_trace_nmi.md` |
| §2a 其余 + N-A 簇 + §2b(201) 抽样 | `kconfig_sched_mm_rest` | `analysis/kconfig_sched_mm_rest.md` |
| §3 代码 TODO(54，8 真缺口+噪声) | `code_todo` | `analysis/code_todo.md` |
