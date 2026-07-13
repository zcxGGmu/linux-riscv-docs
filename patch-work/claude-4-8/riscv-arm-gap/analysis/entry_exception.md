# entry-exception 可移植性分析（linux-arm-kernel → RISC-V）

> 输入：`data/by_category/entry-exception.jsonl`（58 条系列，全部 tier=B、kind=signal）。
> 本地内核树核对：`/Users/zq/Desktop/patch-work/linux-riscv`（Linux v7.2.0-rc3）。

## ⚠️ 基线修正（重要）

`_baseline_riscv.md` §3 称「riscv **不用** `CONFIG_GENERIC_ENTRY`（手写，同 arm64）」——**此说已过时**。
在 v7.2.0-rc3 中 `arch/riscv/Kconfig:112` 已 **`select GENERIC_ENTRY`**，且：

- `arch/riscv/kernel/traps.c` 全面使用通用入口 C 助手：`syscall_enter_from_user_mode` / `syscall_exit_to_user_mode`（`do_trap_ecall_u`，line 336/345）、`irqentry_enter_from_user_mode` / `irqentry_exit_to_user_mode`、`irqentry_nmi_enter/exit`。
- 存在 `arch/riscv/include/asm/entry-common.h`。
- **但 riscv 未 `select GENERIC_IRQ_ENTRY`**（grep 计数=0）：仍保留手写 `entry.S:128 handle_exception`，IRQ 走 `call do_irq`（entry.S:226）而非通用 IRQ 入口；异常经 `excp_vect_table` 分派。

**结论**：riscv 处于「syscall/异常→用户态路径已用 GENERIC_ENTRY，但 IRQ 内核态路径仍手写」的**混合态**——恰是 arm64 正在推进（#46/#19）的中间点。这直接改变了「entry 转换」类补丁的判定：转换框架多判 **ALREADY**，`GENERIC_IRQ_ENTRY` 缺口判 **PATTERN**，通用 `kernel/entry` 核心改进判 **PORTABLE（自动受益）**。

其余基线核对（本地源码确认）：
- syscall.h（`arch/riscv/include/asm/syscall.h`）：`syscall_get_arguments` 已**展开**（args[0..5]，非 memcpy），且 **arg0 用 `regs->orig_a0`**（line 71）；`syscall_set_arguments` 已存在（line 79）。
- `stacktrace.c`：有 `arch_stack_walk`（line 179）与 `arch_stack_walk_user`（line 214），**无 `arch_stack_walk_reliable`**。
- **无 livepatch**（无 `HAVE_LIVEPATCH`、无 `asm/livepatch.h`）；**无 sframe / unwind_user**（Kconfig 无 `SFRAME`/`UNWIND_USER`）。
- 有 SCS（`CONFIG_SHADOW_CALL_STACK`，`entry.S` 多处 `scs_save_current`/`scs_load_current`）；有 `HAVE_ARCH_VMAP_STACK if MMU && 64BIT`。

---

## 摘要

- **系列总数：58**
- 判定计数：**ALREADY 5 / PORTABLE 12 / PATTERN 20 / N-A 21**
- 说明：约 1/3（21 条）是被关键词误挂进本桶的**驱动/固件/ARM-EHABI/MTE** 类（多数 "unwind" 实为「探测失败的资源回收 error-unwind」而非栈回溯）→ N-A。真正有价值的是 **entry 核心演进 + 栈回溯/SFrame + livepatch + vdso futex + syscall 助手**几个簇。

### 本类 Top 候选（按价值排序）

| # | 系列 | 判定 | riscv 落点 |
|---|---|---|---|
| 1 | unwind, arm64: add sframe unwinder for kernel (#17) | PORTABLE(核心)+PATTERN(启用) | `kernel/unwind/*`(通用直用) + `arch/riscv/{Kconfig,kernel/stacktrace.c,Makefile}` |
| 2 | arm64: entry: Convert to generic irq entry (#46) | PATTERN | `arch/riscv/Kconfig`(select GENERIC_IRQ_ENTRY) + `kernel/{entry.S,irq.c,traps.c}` |
| 3 | arm64: stacktrace reliable + livepatch (#51/#55/#56) | PATTERN | `arch/riscv/kernel/stacktrace.c` + `Kconfig`(HAVE_RELIABLE_STACKTRACE→HAVE_LIVEPATCH) |
| 4 | arm64/entry: 通用 entry 核心拆分 (#27/#28) | PORTABLE | `kernel/entry/common.c`, `include/linux/entry-common.h`（riscv 已 GENERIC_ENTRY，自动受益）|
| 5 | arm64: vdso: __vdso_futex_robust_try_unlock() (#2) | PATTERN | `arch/riscv/kernel/vdso/`（新增 vdso futex）|
| 6 | arm64: SFrame user space unwinding (#26) | PATTERN | `arch/riscv/kernel/vdso` + `Kconfig`(HAVE_UNWIND_USER_FP)；通用 `kernel/unwind/user.c` 直用 |
| 7 | perf libunwind + RISC-V support (#18) | PORTABLE | `tools/perf/`（补丁本身即含 riscv 支持）|
| 8 | Drivers: hv: entry "virt" API 通用化 (#45) | PORTABLE | `kernel/entry/*`, `include/linux/entry-kvm.h`→virt（riscv KVM 受益）|

---

## Top 可移植候选（深度）

### 1. unwind, arm64: add sframe unwinder for kernel（#17）
- **原补丁**：<https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260519064950.493949-2-dylanbhatch@google.com/>，状态=new，9 patches。
- **可移植点**：内核态 SFrame 栈回溯**核心是通用的**。curl 确认 patch 1/9 diff 落在 `kernel/unwind/sframe.c`(+270)、`kernel/unwind/user.c`、`include/linux/sframe.h`、`include/linux/unwind_types.h`、`arch/Kconfig`(+4，新增通用 select)——纯通用层；arch 侧仅 x86 头文件重命名。后续 patch（build kernel with sframe V3、per-func CFI 注解、模块 sframe 支持）是 arch 启用。
- **riscv 落点**：通用 `kernel/unwind/` 对 riscv **直接可用**；riscv 侧需 `arch/riscv/Kconfig`（select 新的 sframe 通用选项）、`arch/riscv/Makefile`（`-Wa,--gsframe` 类生成）、`arch/riscv/kernel/stacktrace.c`（接入 sframe 查表）、`entry.S`/asm 叶子函数 CFI 注解。本地确认 riscv 现无任何 sframe/unwind_user。
- **判定**：**PORTABLE（通用核心）+ PATTERN（arch 启用）**——通用回溯器一旦合入，riscv 与 arm64/x86 共享，仅需增量启用工作。

### 2. arm64: entry: Convert to generic irq entry（#46，v8；另见 #9/#53 ARM32、#19）
- **原补丁**：<https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250815030633.448613-9-ruanjinjie@huawei.com/>，状态=new，8 patches。
- **可移植点**：curl 确认 patch 8/8「Switch to generic IRQ entry」把 `arch/arm64/Kconfig` 翻为 `select GENERIC_IRQ_ENTRY`，删除 `entry-common.c` ~378 行手写 IRQ 入口逻辑，改用通用 `irqentry_enter/exit`。**riscv 恰好尚未做这一步**（仍手写 `handle_exception`→`do_irq`）。
- **riscv 落点**：`arch/riscv/Kconfig`（select `GENERIC_IRQ_ENTRY`）；`arch/riscv/kernel/entry.S`（`handle_exception` IRQ 分支）、`irq.c`（`do_irq`/`call_on_irq_stack`）、`traps.c`（改用通用 `irqentry_enter/exit` 内核态助手）。系列中 patch 5「entry: Add `arch_irqentry_exit_need_resched()`」落在通用 `kernel/entry` → 对 riscv 是 PORTABLE 前置件。
- **判定**：**PATTERN**——机制通用、riscv 落点明确，是 riscv entry 现代化最清晰的下一步；风险中等（抢占/异常屏蔽语义需对齐）。

### 3. arm64: stacktrace reliable + HAVE_LIVEPATCH（#51/#55/#56）
- **原补丁**：#51 <https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250521111000.2237470-3-mark.rutland@arm.com/>（reliable stacktrace，2p）；#55 <https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250320171559.3423224-3-song@kernel.org/>（Enable livepatch without sframe，2p）；#56 为其 RFC。
- **可移植点**：curl 确认 #51 patch 2/2 仅改 `arch/arm64/Kconfig`（select `HAVE_RELIABLE_STACKTRACE`）+ `arch/arm64/kernel/stacktrace.c`（实现 `arch_stack_walk_reliable()`：遇不可靠帧/kretprobe 返回 -EINVAL）。这是通用 livepatch 一致性模型所需的**标准 arch 接口**。#55 在其上 `select HAVE_LIVEPATCH`。
- **riscv 落点**：`arch/riscv/kernel/stacktrace.c`（在现有 `walk_stackframe`/`arch_stack_walk` 之上新增 `arch_stack_walk_reliable`，line 179 附近）+ `arch/riscv/Kconfig`（select `HAVE_RELIABLE_STACKTRACE`、`HAVE_LIVEPATCH`）+ 新增 `arch/riscv/include/asm/livepatch.h`、ftrace direct-call 挂钩。本地确认 riscv 二者皆缺。
- **判定**：**PATTERN**——高价值（为 riscv 解锁 livepatch），接口通用、落点明确。

### 4. arm64/entry: 通用 entry 核心拆分（#27，Mark Rutland 10p；#28）
- **原补丁**：<https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260407131650.3813777-10-mark.rutland@arm.com/>，状态=new，10 patches。
- **可移植点**：patch 01-05 前缀为 `entry:`，改 `kernel/entry/common.c` + `include/linux/entry-common.h`——「Fix stale comment for irqentry_enter()」「Remove `local_irq_{enable,disable}_exit_to_user()`」「Split kernel mode logic from `irqentry_{enter,exit}()`」「Split preemption from `irqentry_exit_to_kernel_mode()`」。curl 确认 patch 09（arm64 侧）改 `arch/arm64/{include/asm/entry-common.h,kernel/entry-common.c}`；即 01-05 通用、06-10 arm64。#28「Remove `arch_irqentry_exit_need_resched()`」亦为通用 entry 清理。
- **riscv 落点**：通用改动**自动作用于** riscv（riscv 已 `select GENERIC_ENTRY`）；riscv 采纳 `GENERIC_IRQ_ENTRY`（见 #46）后，内核态 `irqentry_enter/exit` 的抢占拆分将直接受益。
- **判定**：**PORTABLE**——通用入口核心改进，riscv 免费获得；无需 arch 重写。

### 5. arm64: vdso: Implement __vdso_futex_robust_try_unlock()（#2）
- **原补丁**：<https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260705-tonyk-robust_arm-v4-1-e0fd0fa259d3@igalia.com/>，状态=new，5 patches。
- **可移植点**：为 robust futex 解锁提供 vDSO 快路径（避免进程退出时逐个 futex 陷入内核）。curl 确认 patch 1「arm64/entry: Unify user mode handling」是 arch/arm64/kernel/entry-common.c 的小清理（-11 行）；核心是 vdso 侧新增 `__vdso_futex_robust_try_unlock()` + vdso32 对应。依赖通用 vDSO futex ABI/robust-list 基础设施。
- **riscv 落点**：`arch/riscv/kernel/vdso/`（新增 vdso futex 实现，类比现有 `getrandom.c`/`vgettimeofday.c` 的 vdso 数据页模式）+ `vdso.lds.S` 导出符号。本地确认 riscv vdso 现无 futex 条目。
- **判定**：**PATTERN**——机制通用可复用，riscv vdso 框架成熟，落点清晰；需等通用 vDSO futex ABI 定稿。

### 6. arm64: SFrame user space unwinding（#26）
- **原补丁**：<https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260417150827.1183376-4-jremus@linux.ibm.com/>，状态=new，4 patches。
- **可移植点**：基于**通用 `unwind_user` 框架**（`kernel/unwind/user.c`，与 #17 同源）做用户态 SFrame 回溯。patch 标题：`HAVE_UNWIND_USER_FP`、`unsafe_copy_from_user()`、vDSO 生成 SFrame、`HAVE_UNWIND_USER_SFRAME`。
- **riscv 落点**：`arch/riscv/Kconfig`（select `HAVE_UNWIND_USER_FP`/`_SFRAME`）、`arch/riscv/include/asm/uaccess.h`（`unsafe_copy_from_user`）、`arch/riscv/kernel/vdso`（SFrame 生成）；riscv 已有 `arch_stack_walk_user`（stacktrace.c:214）可对接。通用 `unwind_user` 直接可用。
- **判定**：**PATTERN**（arch 启用）+ 通用框架 PORTABLE——与 #17 是「内核态/用户态」一对。

### 7. perf libunwind multiple remote support（#18，含 RISC-V 支持）
- **原补丁**：<https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260513233151.572332-8-irogers@google.com/>，状态=new，7 patches。
- **可移植点**：`tools/perf` 跨平台 libunwind 重构，patch 7/7 直接「Add RISC-V libunwind support」。纯用户态工具、架构无关框架。
- **riscv 落点**：`tools/perf/util/unwind-libunwind*`、`tools/perf/arch/riscv/`。补丁本身即面向 riscv。
- **判定**：**PORTABLE**——工具层，补丁已含 riscv 目标。

### 8. Drivers: hv: entry "virt" API 通用化（#45）
- **原补丁**：<https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250828000156.23389-3-seanjc@google.com/>，状态=new，7 patches。
- **可移植点**：将 KVM 专用的 entry 助手（`entry-kvm.h`/`xfer_to_guest_mode_*`）**通用化为 "entry virt" API**（patch 4/5「Move KVM details into KVM proper」「Rename kvm→virt to genericize」）——落在 `kernel/entry/` + `include/linux/entry-kvm.h`。Hyper-V root 分区驱动部分是 x86/arm 特定（N-A），但通用化改动 riscv KVM 受益。
- **riscv 落点**：`kernel/entry/kvm.c`→virt（通用，自动适用）；riscv KVM（`arch/riscv/kvm/vcpu.c` 的 `xfer_to_guest_mode_handle_work` 调用点）随之受益。
- **判定**：**PORTABLE**（通用 entry-virt 部分）。

---

## 全量判定表（覆盖全部 58 条）

| # | 系列 | arch | 判定 | 可移植点 / riscv 落点（或 N-A 理由） | web_url 关键字 |
|---|---|---|---|---|---|
| 1 | arm64: Add support for FEAT_NMI | arm | **N-A** | GIC PMR 优先级屏蔽 pseudo-NMI，依赖 ICC_PMR_EL1/DAIF；riscv 无对应 HW（通用 `irqentry_nmi_*` riscv 已用）| 20260709...vladimir.murzin |
| 2 | arm64: vdso: __vdso_futex_robust_try_unlock() | arm | **PATTERN** | vdso robust futex 解锁 → `arch/riscv/kernel/vdso/` | 20260705...igalia |
| 3 | firmware: arm_scmi: Fix OF node ref … | generic | **N-A** | SCMI 固件 ABI 驱动（`drivers/firmware/arm_scmi`），非 arch 入口 | 20260703...scmi_core |
| 4 | arm64/sve: Performance improvements (SVE save) | arm | **PATTERN** | SVE 陷入抑制/惰性状态管理思想 → RVV `arch/riscv/kernel/vector.c` | 20260703...sve-trap |
| 5 | i2c: imx-lpi2c: fix probe error handling | generic | **N-A** | i2c 驱动探测错误回收，NXP 特定 | 20260630...carlos.song |
| 6 | [v3] ARM: entry: expand comment in __switch_to | arm | **N-A** | 仅 ARM32 `__switch_to` 注释扩写，无可移植代码 | 20260630...comments-in-switch |
| 7 | iommu/arm-smmu: Use pm_runtime in fault handlers | arm | **N-A** | arm-SMMU IOMMU 硬件驱动 | 20260630...smmu-rpm |
| 8 | arm: backtrace-clang: fix wrong sp usage | arm | **N-A** | ARM32 手写 backtrace 汇编 sp 修正，ARM EHABI 特定 | 20260624...maninder1.s |
| 9 | ARM: entry: Convert IRQ handling to generic IRQ entry | arm | **PATTERN** | 同 #46 主题（ARM32 版）→ riscv `GENERIC_IRQ_ENTRY`（`Kconfig`+`entry.S`）| 20260623...arm-generic-irq |
| 10 | memory: atmel-ebi: unwind SMC clock on probe fail | generic | **N-A** | 内存控制器驱动探测回收，Atmel 特定 | 20260616...pengpeng |
| 11 | KVM: arm64: Restore POR_EL0 access to host EL0 | arm | **N-A** | POE 权限覆盖寄存器 POR_EL0，arm64 专属 | 20260604...joey.gouly |
| 12 | ARM: module.lds: fix unwind metadata … | arm | **N-A** | ARM EHABI 模块 unwind 表链接，ARM32 专属 | tencent_08845B64 |
| 13 | fix: arm64: syscall: use live x0 for arg0 | arm | **PATTERN** | riscv `syscall.h:71` arg0 用 `orig_a0`，与 args1-5(live) 同样不一致 → 同源待评估 | 20260529065444 |
| 14 | fix: arm: syscall: use live r0 for arg0 | generic(arm32) | **PATTERN** | 同 #13（ARM32）→ riscv `arch/riscv/include/asm/syscall.h` | 20260529065302 |
| 15 | iommu/arm-smmu-v3: Add PRI support | arm | **N-A** | SMMU-v3 页请求接口硬件 | c0b1c3cfb88b...nicolinc |
| 16 | arm64/entry: Don't disable preempt in debug_exception_enter (RT) | arm | **PATTERN**(弱) | RT + 调试异常抢占；riscv `traps.c` 调试路径，价值低 | 20260519222524...longman |
| 17 | unwind, arm64: add sframe unwinder for kernel | arm | **PORTABLE+PATTERN** | 通用 `kernel/unwind/sframe.c` 直用 + `arch/riscv/{Kconfig,Makefile,stacktrace.c}` 启用 | 20260519064950...dylanbhatch |
| 18 | perf libunwind multiple remote support | generic | **PORTABLE** | `tools/perf`（含 riscv libunwind 支持）| 20260513233151...irogers |
| 19 | arm64: entry: Convert to Generic Entry | arm | **ALREADY** | riscv 已 `select GENERIC_ENTRY`；仅 patch01「syscall_trace_enter 截断修复」是通用 PORTABLE 残留 | 20260511092103...ruanjinjie |
| 20 | arm64/entry: Fix arm64-specific rseq brokenness (v2) | arm | **PATTERN**(弱) | arm64 特定 rseq/entry 顺序 bug；riscv 走通用 entry 处理 rseq，多半免疫，需核对 | 20260508...mark.rutland |
| 21 | arm64: Fix garbled logs (race between stack traces) | arm | **PATTERN**(弱) | 并发栈打印乱序；riscv `stacktrace.c` show_stack，或属通用 printk | 20260430...dssauerw |
| 22 | perf sched-migration: Port to python module | generic | **PORTABLE** | `tools/perf/scripts` 架构无关工具 | 20260425...irogers |
| 23 | arm64/entry: Fix arm64-specific rseq brokenness (thread) | arm | **PATTERN**(弱) | 同 #20 线程 | aeueE1I1OuVkOcEZ |
| 24 | perf syscall-counts-by-pid: Port to python | generic | **PORTABLE** | `tools/perf/scripts` 工具 | 20260423194428...irogers |
| 25 | crypto: ixp4xx - fix buffer chain unwind … | generic | **N-A** | 驱动分配失败 error-unwind（非栈回溯），ixp4xx SoC | 20260423111956 |
| 26 | arm64: SFrame user space unwinding | arm | **PATTERN** | 通用 `unwind_user` + `arch/riscv/{Kconfig,vdso,uaccess.h}`；riscv 已有 `arch_stack_walk_user` | 20260417150827...jremus |
| 27 | arm64/entry: (Mark Rutland 10p, entry 核心拆分) | arm | **PORTABLE** | patch01-05 通用 `kernel/entry/common.c`/`entry-common.h`，riscv 自动受益 | 20260407131650...mark.rutland |
| 28 | arm64/entry: Fix involuntary preemption masking | arm | **PORTABLE** | 「Remove `arch_irqentry_exit_need_resched()`」通用 entry 清理 + arm64 屏蔽 | 20260320113026...mark.rutland |
| 29 | arm64: scs: Remove redundant SCS SP save/restore on EL0 | arm | **PATTERN** | riscv 有 SCS（`entry.S` `scs_save/load_current`），可查同类冗余优化 | 20260313123220...will |
| 30 | [rc] iommu/arm-smmu-v3: Drain in-flight fault handlers | arm | **N-A** | SMMU-v3 硬件驱动 | 20260307001723...nicolinc |
| 31 | arm64: Optionally disable EL0 MTE via cmdline | arm | **N-A** | MTE 内存标签，riscv 无对应（仅 Supm 掩码）| plslbeuzfag5 |
| 32 | ARM: fix wrong lockdep hardirqs state | arm | **ALREADY** | riscv 已用 GENERIC_ENTRY，lockdep hardirq/rseq 退出统计由通用 `exit_to_user_mode` 正确处理；ARM32 补课 | 20260125164016 |
| 33 | kselftest/arm64: Use syscall() over nolibc my_syscall() | arm | **N-A** | arm64 selftest 清理，测试专属 | 20260117...weissschuh |
| 34 | perf dwarf/libdw extra support, speed, cleanups | other | **PORTABLE** | `tools/perf` dwarf/libdw（含跨架构 unwind 修复）| 20260117052849...irogers |
| 35 | [v3] perf unwind-libdw: fix cross-arch unwinding bug | generic | **PORTABLE** | `tools/perf/util/unwind-libdw.c` 架构无关修复 | 20260107...skydio |
| 36 | syscall: Cleanup and improve syscall_get_arguments() | arm | **PORTABLE** | patch1「Remove unused `SYSCALL_MAX_ARGS`」通用 `include/linux/syscall.h`；patch2 arm64 去 memcpy → riscv 已展开(ALREADY) | 20251201120633...ruanjinjie |
| 37 | [v2] arm64: entry: Clean out some indirection | arm | **PATTERN**(弱) | arm64 el0 handler 间接层清理；riscv `excp_vect_table` 有类似间接，可增量优化 | 20251105...linaro |
| 38 | arm64: Add kernel param to disable trap EL0 IMPDEF regs | arm | **N-A** | IMPDEF 系统寄存器陷入，arm64 专属 | 20251021...liaochang1 |
| 39 | KVM: guest_memfd: Add NUMA mempolicy support | generic | **PORTABLE** | 通用 `virt/kvm/guest_memfd.c`（riscv KVM 受益，实为 mm/KVM 误挂本桶）| 20251016...seanjc |
| 40 | [v2] arm64: debug: always unmask interrupts in el0_softstp() | arm | **PATTERN**(弱) | arm64 软件单步 + DAIF；riscv 单步机制不同(icount/ebreak)，转移有限 | 20251014...ada.coupriediaz |
| 41 | [v2] ARM: module: fix unwind section reloc range | arm | **N-A** | ARM EHABI 模块 unwind 段重定位，ARM32 专属 | 20250922...william.zhang |
| 42 | arm/syscalls: mark syscall invocation likely | generic(arm32) | **PATTERN**(弱) | 分支提示；riscv `do_trap_ecall_u` 分派，价值极低 | 20250919100042 |
| 43 | arm64: add unlikely hint to MTE async fault check | arm | **N-A** | MTE 异步故障检查，riscv 无 MTE | 20250919033327 |
| 44 | [net-next] net: ti: icssm-prueth: unwind cleanly in probe() | generic | **N-A** | 网卡驱动探测 error-unwind，TI 特定 | aMvVagz8aBRxMvFn |
| 45 | Drivers: hv: Fix NEED_RESCHED_LAZY, use common APIs | generic | **PORTABLE** | 通用 `kernel/entry` KVM→virt API 通用化（riscv KVM 受益）；hv 驱动本身 N-A | 20250828000156...seanjc |
| 46 | arm64: entry: Convert to generic irq entry (v8) | arm | **PATTERN** | riscv `select GENERIC_IRQ_ENTRY` + `kernel/{entry.S,irq.c,traps.c}` 改用通用 IRQ 入口 | 20250815030633...ruanjinjie |
| 47 | ARM: stacktrace: include asm/sections.h … | arm | **N-A** | ARM32 头文件包含修正，琐碎 | 20250807...arnd |
| 48 | arm64/entry: Mask DAIF in cpu_switch_to(), call_on_irq_stack() | arm | **PATTERN**(弱) | DAIF 特定；riscv `__switch_to`/`call_on_irq_stack` 中断屏蔽类比，价值低 | 20250718...ada.coupriediaz |
| 49 | arm64: set VMAP_STACK by default | arm | **ALREADY** | riscv 已 `HAVE_ARCH_VMAP_STACK if MMU && 64BIT`；「默认开/去条件化」是次要 cleanup pattern | 20250707...debian |
| 50 | arm64: debug: remove hook registration, split exception entry | arm | **PATTERN** | riscv `traps.c` 已静态调用 step/break handler（部分 ALREADY）；调试异常 entry/exit 拆分可借鉴 | 20250707114109...ada.coupriediaz |
| 51 | arm64: stacktrace: Enable reliable stacktrace | arm | **PATTERN** | `arch/riscv/kernel/stacktrace.c` 新增 `arch_stack_walk_reliable` + `Kconfig` HAVE_RELIABLE_STACKTRACE | 20250521111000...mark.rutland |
| 52 | docs: align with scripts/syscall.tbl migration | generic | **PORTABLE** | `Documentation/` 文档对齐，架构无关 | 20250506...y.j3ms.n |
| 53 | ARM: Switch to generic entry (31p) | arm | **ALREADY** | ARM32 全量转 generic entry；riscv 已完成 syscall/异常路径转换（IRQ 路径见 #46）| 20250420...linaro |
| 54 | crypto: sun8i-ce-hash - Refine exception handling | generic | **N-A** | 驱动 error-handling（非硬件异常），Allwinner 特定 | 3727de04...web.de |
| 55 | arm64: livepatch: Enable livepatch without sframe | arm | **PATTERN** | `arch_stack_walk_reliable` + `select HAVE_LIVEPATCH` + `asm/livepatch.h` → riscv 解锁 livepatch | 20250320171559...song |
| 56 | [RFC] arm64: Implement arch_stack_walk_reliable | arm | **PATTERN** | 同 #51/#55 的 RFC 前身 | 20250129232936...song |
| 57 | syscall.h: add syscall_set_arguments() on remaining arches | generic | **ALREADY** | riscv `syscall.h:79` 已有 `syscall_set_arguments`（本补丁受益者之一）| 20250107230418...strace |
| 58 | [v2] KVM: arm64: Fix nVHE stacktrace VA bits mask | arm | **N-A** | nVHE hypervisor 栈回溯 VA 掩码，arm64 虚拟化专属 | 20250107112821...vdonnefort |

---

## 判定纪律备注

1. **基线过时点已修正**：riscv v7.2.0-rc3 **已 `select GENERIC_ENTRY`**（`Kconfig:112`），syscall/异常→用户态路径用通用助手；据此把 arm64「转 generic entry」类（#19/#53）判 **ALREADY**，把仍缺的 **`GENERIC_IRQ_ENTRY`**（#46/#9）判 **PATTERN**，通用 `kernel/entry` 改进（#27/#28）判 **PORTABLE（自动受益）**。
2. **关键词误挂**：本桶约 9 条 "unwind" 实为驱动探测失败的 **error-unwind**（#5/#10/#25/#44/#54 等），非栈回溯 → N-A。
3. **syscall 助手簇**：riscv `syscall.h` 已展开参数（非 memcpy）、已有 `set_arguments`、arg0 用 `orig_a0` → #36/#57 多为 ALREADY，仅 #13/#14「live 寄存器 arg0 一致性」是 riscv 同源待评估的 PATTERN。
4. **最高价值三簇**：(a) SFrame 内核/用户态回溯（#17/#26，通用核心 PORTABLE + arch 启用 PATTERN）；(b) reliable stacktrace → livepatch（#51/#55/#56，PATTERN）；(c) GENERIC_IRQ_ENTRY 采纳（#46，PATTERN）。
