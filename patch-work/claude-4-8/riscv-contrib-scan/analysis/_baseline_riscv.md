# RISC-V 能力基线（判 ALREADY / 排假阳 的依据）

> 内核树：`/Users/zq/Desktop/patch-work/linux-riscv`（Linux v7.2.0-rc3，只读）。
> 本轮候选来自**源码树静态扫描**（features 矩阵 TODO / Kconfig `select` 差集 / 代码 TODO），**非补丁**。
> 判定任一候选前先对照本基线：**riscv 已有的能力 → ALREADY（scan 误报）**。

## 一、已成熟实现（判 ALREADY 的依据，勿误报为缺口）

**MM/页表**：Sv39/48/57 运行时动态；hugetlb/THP（含 PUD-THP）；**Svnapot**(=arm64 contpte 连续 PTE)；线性映射拆分 `__split_linear_mapping_*`(`arch/riscv/mm/pageattr.c`)；vmemmap；TLB range flush + **Svinval** + SBI rfence + 批量 unmap；STRICT_KERNEL_RWX；**Svvptc**；Svade/Svadu(=HW A/D)；Svpbmt(=MAIR)。

**cpufeature**：`elf_hwcap`/hwprobe/`riscv_isa_ext[]`(~105 扩展)/alternatives/四厂商 errata(andes/mips/sifive/thead)/vendor_extensions。

**原子/锁**：**Zabha**(子字 AMO=LSE)、**Zacas**(CAS，缺则退回 LR/SC)、**Zawrs**(=WFE)、**combo spinlock**(ticket↔qspinlock 运行时切换)。

**entry/boot**：已 `select GENERIC_ENTRY`（**并经其传递获得 `GENERIC_IRQ_ENTRY`+`GENERIC_SYSCALL`**，`arch/Kconfig:114`）；compat；head.S；EFI-stub；KASLR(`RANDOMIZE_BASE`)；XIP。

**vector/CFI/指针掩码**：完整 RVV 1.0 + kernel-mode vector + Vector-Crypto；**Zicfilp**(=BTI 落地页)、**Zicfiss**(=GCS 影子栈)、kCFI；**Supm**(=TBI/tagged-addr ABI，`prctl PR_PMLEN`)。

**perf/trace/kexec/acpi/debug**：SBI-PMU + **sscofpmf**(溢出采样)+snapshot；dynamic ftrace(WITH_ARGS/CALL_OPS/DIRECT_CALLS/FUNCTION_GRAPH)、kprobes/kretprobes/uprobes、BPF-JIT(64+32,kfunc/arena/percpu)、jump_label、kgdb；完整 kexec/kexec_file/purgatory/kdump；ACPI(RINTC/RHCT/RIMT/SRAT，64bit)；KASAN-generic + KFENCE + stackprotector + **VMAP_STACK**。

**虚拟化底座**：**`config PARAVIRT`**（`arch/riscv/Kconfig:1127`）+ `PARAVIRT_TIME_ACCOUNTING` + stolen-time；KVM(H 扩展，含 AIA)。

## 二、真实缺口（arm64/x86 有、riscv 无/部分）——移植候选来源

- **KCSAN / KMSAN / KASAN SW_TAGS**：riscv 缺（仅 generic + KFENCE）；通用 sanitizer → 多 PORTABLE（补 arch 少量钩子 + `select`）。
- **static_call / HAVE_STATIC_CALL(_INLINE)**：riscv 无 → PATTERN（需 arch text-patching 直接跳转改写，`arch/riscv/kernel/`）。
- **HAVE_LIVEPATCH**：riscv 无（依赖 reliable stacktrace + ftrace WITH_REGS）→ PORTABLE/PATTERN。
- **HAVE_RELIABLE_STACKTRACE**：riscv 无 → PATTERN（unwinder 硬化，livepatch 前置）。
- **ARCH_HAS_COPY_MC**：riscv 无（机器检查内存拷贝容错）→ PATTERN。
- **NMI 类**（HAVE_NMI / PERF_EVENTS_NMI / HAVE_HARDLOCKUP_DETECTOR_PERF / HAVE_PERF_EVENTS_NMI / TRACE_IRQFLAGS_NMI_SUPPORT / ARCH_HAS_NMI_SAFE_THIS_CPU_OPS）：riscv 无真 NMI（AIA/IMSIC 可支撑）→ PATTERN。
- ~~**GENERIC_IRQ_ENTRY**~~：**核实纠正为 ALREADY** —— `config GENERIC_ENTRY` 现 `select GENERIC_IRQ_ENTRY`（`arch/Kconfig:114`），riscv 已选 GENERIC_ENTRY 故传递获得（scan 只看 select 的假阳；旧基线/memory 误记为缺口）。
- **haltpoll / ARCH_CPUIDLE_HALTPOLL / TIF_POLLING_NRFLAG**：riscv 无 → PATTERN。
- **HAVE_HW_BREAKPOINT**：riscv 有 debug trigger 但未接入 perf hw_breakpoint 框架 → PATTERN。
- **cmpxchg-local / HAVE_CMPXCHG_LOCAL**：features 矩阵 TODO，arm64+x86 都有 → PORTABLE/PATTERN（`arch/riscv/include/asm/cmpxchg.h`）。
- **SMT 调度（SCHED_SMT / HOTPLUG_SMT / ARCH_SUPPORTS_SCHED_CLUSTER）**：riscv 未 select → 视拓扑，PORTABLE/PATTERN。
- **MM 增量**：ARCH_HAS_NONLEAF_PMD_YOUNG、ARCH_HAS_LAZY_MMU_MODE、rodata=full/BBML2 → PATTERN。
- **§1 features TODO**：cmpxchg-local、virt-cpuacct（arm64+x86 都 ok）；kprobes-on-ftrace、optprobes、user-ret-profiler（仅 x86 ok）；cBPF-JIT（三家都 TODO，遗留，价值最低）。

## 三、无对应硬件/ISA → 一律 N-A（不误报为可移植）

- **MTE**(内存标签)、**PAC**(指针认证)、**SME**(矩阵)、**SPE**(统计采样)：riscv 无对应 ISA。
- **GIC/ITS/GICv4**、**arm-SMMU**、Apple/MVEBU/Exynos/Rockchip/Samsung/TI 等**平台中断/SoC/时钟**：riscv 用 AIA(APLIC/IMSIC) + 自有 IOMMU，HW 内部实现不可移植（**通用** irq/iommu 框架另论）。
- **pkeys / ARCH_HAS_PKEYS**(x86 PKU / arm64 POE)、**resctrl / RESCTRL_FS / ARCH_HAS_CPU_RESCTRL**(x86 RDT / arm64 MPAM)：需硬件保护键/QoS，riscv 暂无 → N-A。
- **mem_encrypt / ARCH_HAS_MEM_ENCRYPT / ARCH_HAS_CC_PLATFORM / FORCE_DMA_UNENCRYPTED**(SEV/TDX/CCA 机密计算)：riscv CoVE 在途**未合入** → N-A（注明"在途"）。
- **PSCI/SMCCC/SCMI/FF-A/OP-TEE** 固件 ABI：riscv 用 SBI，ABI 不同 → N-A（仅思想类比）。
- **legacy compat**（HAVE_UID16 / OLD_SIGACTION / OLD_SIGSUSPEND3 / COMPAT_OLD_SIGACTION）：riscv 是新架构，无 32 位 legacy 包袱 → N-A（不需要）。

## 四、本轮假阳性专项警示（scan 只看 `arch/riscv/Kconfig* 的 select` 的口径缺陷）

判 §2 Kconfig 符号前**必须** grep 确认 riscv 是否已通过以下任一方式获得，杜绝 PARAVIRT 式误判：
1. `config <SYM>` / `def_bool` 定义（如 **PARAVIRT** 已有 → ALREADY）。
2. 架构无关 Kconfig 里对 riscv 生效的 select / 传递 select。
3. 已有等价能力但符号名不同。

**高假阳风险符号（riscv 很可能其实已有，务必逐一核实）**：`PARAVIRT`、`VMAP_STACK`、`JUMP_LABEL`、`PERF_EVENTS`、`MMU_NOTIFIER`、`DEBUG_FS`、`GENERIC_ALLOCATOR`、`GENERIC_IRQ_CHIP`、`RTC_LIB`、`KMAP_LOCAL`、`GENERIC_IRQ_PROBE`、`GENERIC_CPU_AUTOPROBE`、`ARCH_WANT_DEFAULT_BPF_JIT` 等通用符号。
