# RISC-V 架构能力基线（判定依据）

> 内核树 = Linux **v7.2.0-rc3**（`/Users/zq/Desktop/patch-work/linux-riscv`）。
> 本文由两个 Explore 子代理盘点 `arch/riscv/` 全树得出，**所有文件路径均已核对存在**。
> 用途：作为「原补丁能否移植到 riscv」四态判定的**事实依据**——
> **凡 riscv 已实现的能力，对应 arm64 补丁应判 ALREADY，勿误报为「可移植」。**

---

## 1. MM / 页表 —— 成熟

| 能力 | 状态 | riscv 落点 | 备注 / arm64 对应 |
|---|---|---|---|
| Sv39/48/57 多级页表 | ✅ 运行时动态 | `mm/init.c:46-56`, `kernel/pi/fdt_early.c` | `satp_mode` 动态降级；p4d/pud 动态折叠（arm64 是编译期 `PGTABLE_LEVELS`）|
| hugetlb / THP（含 PUD-THP）| ✅ | `mm/hugetlbpage.c`, `Kconfig:149-150` | THP/hugetlb migration + THP swap |
| **Svnapot（连续 PTE）** | ✅ `CONFIG_RISCV_ISA_SVNAPOT` | `mm/hugetlbpage.c`, `pgtable-64.h` | **= arm64 contiguous-PTE (contpte)**；`arch_make_huge_pte`/`pte_mknapot` |
| 线性映射拆分 | ✅ | `mm/pageattr.c` `__split_linear_mapping_{pmd,pud,p4d,pgd}` | 改权限时按需拆分 |
| vmemmap | ✅ | `mm/init.c:62` `SPARSEMEM_VMEMMAP` | `ARCH_WANT_OPTIMIZE_HUGETLB_VMEMMAP` |
| TLB 刷新 | ✅ | `mm/tlbflush.c` | range flush + **Svinval** + SBI rfence/IPI + ASID + 批量 unmap（`tlbbatch.h`）|
| rodata / 页权限 | ⚠️ 部分 | `mm/init.c:741`, `mm/pageattr.c` | `STRICT_KERNEL_RWX` + 按需拆分；**无 arm64 `rodata=full` 全线性映射 RO** |
| **Svvptc** | ✅ | `pgtable.h:571-588` | 有 SVVPTC 时略过 valid-entry 后的 eager SFENCE（与 arm64 BBM 是不同问题）|
| Svade/Svadu（HW A/D）| ✅ | `cpufeature.c:294`, `pgtable-bits.h` | = arm64 HW AF/DBM |
| Svpbmt（内存类型）| ✅ | — | = arm64 MAIR 属性 |

## 2. cpufeature / ISA 检测 —— 成熟

- `elf_hwcap`、`riscv_isa_ext[]`（~105 扩展，`hwcap.h`，最高 `ZICFISS`=105）、`__riscv_isa_extension_available`、
  `riscv_has_extension_likely/unlikely`（alternatives + static key）。
- **hwprobe**（`sys_riscv_hwprobe`，`sys_hwprobe.c`）：MVENDORID/MARCHID/MIMPID、IMA_EXT_0/1、CPUPERF、misaligned perf、
  CBO block size、highest-virt-addr；vDSO 加速。Doc: `Documentation/arch/riscv/hwprobe.rst`。
- **alternatives**：`alternative.c`（`apply_alternatives`/`riscv_cpufeature_patch_func`，按 MVENDORID 分派）。
- **errata**：四厂商 **andes / mips / sifive / thead**（`errata/*/errata.c`）；vendor_extensions（xtheadvector 等）。
- arm64 对应：arm64 用 MIDR + 系统寄存器能力扫描；riscv 用 DT/ACPI ISA 串 + SBI + MVENDORID errata（更年轻、不统一）。

## 3. entry / 异常 / syscall —— 成熟
- 单一 `handle_exception`（`entry.S:128`）→ C 分派（`traps.c`）；`__switch_to`、irq stack、栈溢出处理。
- context tracking（`irqentry_*`）、`arch_exit_to_user_mode_prepare`（`entry-common.h`）。
- **已 `select GENERIC_ENTRY`**（`arch/riscv/Kconfig:112`）：syscall/异常→用户态走通用 `syscall_*` + `irqentry_*_from_user_mode`（`traps.c`）；但**未** select `GENERIC_IRQ_ENTRY`（IRQ 内核态仍手写 `handle_exception`→`do_irq`；arm64 二者皆有）→「转通用 IRQ entry」是真实 PATTERN 候选。32-bit compat（`compat_syscall_table.c`）。

## 4. 原子 / 锁 / 屏障 —— 成熟
- **Zabha**（子字 AMO `amoswap.b/.h`）= arm64 LSE 子字原子（`cmpxchg.h:22-26`）。
- **Zacas**（CAS 含 dword `amocas.*`）= arm64 CAS/CASP；缺则退回 LR/SC 循环（`cmpxchg.h:135-191`）。
- **Zawrs**（`wrs.nto/sto` 等待保留集）= arm64 `smp_cond_load` 中的 WFE（`barrier.h:69-77`）。
- **combo spinlock**：运行时在 ticket ↔ qspinlock 间切换（static key，`spinlock.h:21-28`, `setup.c:271-295`）——比 arm64（恒 qspinlock）更灵活。
- fence 指令 + `mmiowb.h`/`membarrier.h`/`sync_core.h`。

## 5. boot / head / EFI / KASLR —— 成熟
- `head.S`：`_start`/`secondary_start_sbi`/`relocate_enable_mmu`。
- **EFI stub**（`CONFIG_EFI_STUB`）、**KASLR**（`RELOCATABLE`+`RANDOMIZE_BASE`，`kernel/pi/` 位置无关早期码 + `archrandom_early.c` 取种子）、XIP。

## 6. signal / ptrace / ELF —— 成熟
- `signal.c`：sigcontext 存取、FP、**动态 vector 状态**（`riscv_v_vstate_save`）；32-bit `compat_signal.c`。
- `ptrace.c` regset：`REGSET_X/F/V`（GPR/FP/向量）、`REGSET_TAGGED_ADDR_CTRL`（指针掩码）、`REGSET_CFI`（CFI）。

## 7. 向量 / FP —— 成熟（RVV 1.0）
- `kernel/vector.c`、`kernel_mode_vector.c`、`fpu.S`；ptrace(`REGSET_V`)、signal(`__sc_riscv_v_state`)、Vector-Crypto（`crypto/`，Zvkned/Zvbb/…）。
- 首次使用惰性 trap、per-task 存取、脏状态跟踪、kernel-mode vector、动态 VLEN。
- arm64 对应：**SVE → RVV**（均可伸缩向量）。**无 SME（矩阵/streaming）对应。**

## 8. 控制流完整性 / 影子栈 —— 已落地（较新）
- `kernel/usercfi.c`、`asm/usercfi.h`、`vdso_cfi/`；`CONFIG_RISCV_USER_CFI`（`Kconfig:1181`，`-fcf-protection=full`）。
- **Zicfilp**（落地页）= arm64 **BTI**；**Zicfiss**（影子栈）= arm64 **GCS**；`prctl(PR_SHADOW_STACK_ENABLE)`。
- kernel kCFI（`kernel/cfi.c`，Clang）。注意：开 CFI 时 `HAVE_DYNAMIC_FTRACE_WITH_CALL_OPS` 关闭（`Kconfig:162`）。

## 9. 指针掩码 —— 已落地（仅掩码，无标签检查）
- **Supm**（用户态指针掩码，hw `Smnpm`/`Ssnpm`）= arm64 **TBI / TAGGED_ADDR_ABI**（`process.c` `prctl PR_PMLEN`）。
- hwprobe `RISCV_HWPROBE_EXT_SUPM`。**无 MTE（内存标签）对应**（无 tag 检查/tag 存储）。

## 10. perf / PMU —— 成熟
- `drivers/perf/riscv_pmu_sbi.c`（+legacy）：SBI-PMU + **sscofpmf**（计数器溢出采样，`pmu_sbi_ovf_handler`/`CSR_SCOUNTOVF`）+ SBI-PMU snapshot 共享内存。
- callchain/regs：`kernel/perf_callchain.c`/`perf_regs.c`。
- arm64 对应：**arm_pmuv3 → riscv_pmu**。**无 SPE（统计采样）对应**——sscofpmf 仅计数器溢出采样。

## 11. trace / probes / BPF —— 成熟（与 arm64 基本对等）
- ftrace：`DYNAMIC_FTRACE` + `WITH_ARGS` + `WITH_CALL_OPS` + `WITH_DIRECT_CALLS` + `FUNCTION_GRAPH`（`kernel/ftrace.c`, `mcount-dyn.S`）。
- probes：kprobes/kretprobes（rethook）/uprobes（`kernel/probes/`）。
- **BPF JIT**：64+32 位（`net/bpf_jit_comp64.c`），支持 kfunc-call/arena/per-cpu insn/ptr_xchg/fsession。
- `HAVE_ARCH_JUMP_LABEL(_RELATIVE)`（`kernel/jump_label.c`）；kgdb（`kernel/kgdb.c`）。

## 12. kexec / crash / kdump —— 成熟（与 arm64 对等）
- `machine_kexec.c`/`machine_kexec_file.c`（ELF+Image loader）/`kexec_relocate.S`；crash（`crash_dump.c`/`vmcore_info.c`）；purgatory（`purgatory/`）。

## 13. ACPI —— 成熟（64-bit）
- `kernel/acpi.c`/`acpi_numa.c`（`ARCH_SUPPORTS_ACPI if 64BIT`）；MADT-**RINTC**、**RHCT**、**RIMT**、SRAT-RINTC NUMA。年轻于 arm64 但可用。

## 14. KASAN / KFENCE / 硬化 —— 部分
- **KASAN 仅 generic（outline/inline）**——**无 `KASAN_SW_TAGS`、无 HW_TAGS**（arm64 两者皆有，HW_TAGS 靠 MTE）。
- KFENCE、per-task stackprotector、VMAP_STACK、KGDB 均有。**无 KCSAN、无 KMSAN**（grep 确认 arch/riscv/Kconfig 中缺）。

---

## 与 arm64 的关键差距（移植候选的来源）

| # | arm64 有、riscv 缺/弱 | riscv 现状 | 移植倾向 |
|---|---|---|---|
| 1 | **KCSAN / KMSAN / KASAN SW_TAGS** | 仅 KASAN-generic + KFENCE | **PORTABLE**（通用 sanitizer，可 select + 补少量 arch 钩子）|
| 2 | **`rodata=full`** 全线性映射 RO | 仅 STRICT_RWX + 按需拆分 | **PATTERN**（`mm/pageattr.c`/`mm/init.c`）|
| 3 | **BBML2 大块映射 / contpte 优化** | 有 Svnapot，但块合并/拆分优化点不同 | **PATTERN**（`mm/`，看 diff 定）|
| 4 | **MTE（内存标签）** | 仅 Supm 指针掩码（掩码≠标签检查）| **N-A**（无对应 ISA；除非补丁扩展通用底座）|
| 5 | **PAC（指针认证）** | 无 | **N-A**（无对应扩展）|
| 6 | **SME（可伸缩矩阵）** | 仅 RVV 覆盖向量角色 | **N-A** |
| 7 | **SPE（统计采样 profiling）** | 仅 sscofpmf 计数器溢出采样 | **N-A**（无硬件采样器；perf 通用框架部分可能 PORTABLE）|

**已落地的 emerging 类比**（对应 arm64 补丁多判 **ALREADY / PATTERN**，勿误报为「新可移植」）：
BTI→**Zicfilp**、GCS→**Zicfiss**、SVE→**RVV**、TBI/tagged-addr→**Supm**、LSE→**Zabha/Zacas**、WFE→**Zawrs**、contpte→**Svnapot**、HW-AF/DBM→**Svade/Svadu**。
