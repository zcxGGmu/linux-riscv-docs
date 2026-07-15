# §2a 跟踪/调试/NMI 硬化簇 候选四态判定（RISC-V 贡献点静态扫描）

> 内核树：`/Users/zq/Desktop/patch-work/linux-riscv`（v7.2.0-rc3，只读，HEAD `cc7474b13`）。
> 本簇 11 个符号均：arm64+x86 都 `select`、riscv 未 `select`。
> **排假阳已完成**：11 个符号全部 `grep "^config <SYM>"` + 全树 `select <SYM>` + riscv Kconfig* 逐一核对——
> 无一由 riscv `def_bool` / 传递 select 获得（唯一近似项 `ARCH_HAVE_NMI_SAFE_CMPXCHG`@`arch/riscv/Kconfig:58` 是**另一个符号**，非 `ARCH_HAS_NMI_SAFE_THIS_CPU_OPS`）。故**无 PARAVIRT 式假阳，11 个全部是真差集**。

## 摘要

- **候选总数 11**；四态：**ALREADY 0 / PORTABLE 2 / PATTERN 8 / N-A 1**。
- 本批 Top 候选（按价值/可行性排序）：
  1. **HAVE_STATIC_CALL** → PATTERN：text-patch 基座已全备（`jump_label.c` 已在 patch JAL/NOP），只差 `static_call.h`+trampoline。**性价比最高**。
  2. **HAVE_RELIABLE_STACKTRACE** → PATTERN：livepatch 的**前置linchpin**，riscv FP unwinder 已识别异常帧（`handle_exception`/`ret_from_exception_end`），补 `arch_stack_walk_reliable()`。
  3. **HAVE_LIVEPATCH** → PORTABLE（gated）：ftrace WITH_ARGS+CALL_OPS+DIRECT_CALLS 基座已全，arm64 无 `asm/livepatch.h`；仅 `select` + 依赖 #2。
  4. **HAVE_HW_BREAKPOINT** → PATTERN：**用户可见缺口**（gdb 硬件断点/观察点当前完全不可用），ptrace 无 HW_BREAK regset，需 Sdtrig/SBI-DBTR + 新 `hw_breakpoint.c`。
  5. **HAVE_NMI + HAVE_PERF_EVENTS_NMI + HAVE_HARDLOCKUP_DETECTOR_PERF** → PATTERN 簇：riscv 无真 NMI（`local_irq_disable`=清 `SSTATUS.SIE`，全屏蔽），须 **AIA IPRIO 阈值伪 NMI**（对标 arm64 `ARM64_PSEUDO_NMI`/ICC_PMR）。**但硬锁检测今日已可用**（buddy detector，见下）。
- **N-A 1 项**：`HAVE_C_RECORDMCOUNT`——riscv 走 `-fpatchable-function-entry`，`FTRACE_MCOUNT_USE_RECORDMCOUNT` 被 `!FTRACE_MCOUNT_USE_PATCHABLE_FUNCTION_ENTRY` 排除，recordmcount 永不运行，select 之为死代码。

## Top 深度候选

### 1. HAVE_STATIC_CALL —— PATTERN（本批最优先）
- **候选**：`HAVE_STATIC_CALL`（来源：Kconfig §2a；`arch/Kconfig:1691`）。x86 无条件 select，arm64 `select ... if CFI`。
- **现状**：riscv **无** `arch/riscv/include/asm/static_call.h`（全树仅 x86/arm64/powerpc 有）。但 text-patch 基座**完备**：`arch/riscv/kernel/patch.c` 提供 `patch_insn_write()`/`patch_text_set_nosync()`；`arch/riscv/kernel/jump_label.c:18` 已用 `patch_insn_write()` 在调用点原子改写 `RISCV_INSN_JAL`↔`NOP4`——正是 static_call 所需原语。
- **落点**：新增 `arch/riscv/include/asm/static_call.h`（out-of-line trampoline：`auipc t1,hi; ld t1,lo(t1); jr t1` 从 rodata 取目标；或近距直接 patch `jal`）+ 新增 `arch/riscv/kernel/static_call.c`（`arch_static_call_transform()` 调 `patch_text`）+ `arch/riscv/Kconfig` `select HAVE_STATIC_CALL`。参照 `arch/arm64/include/asm/static_call.h`（adrp+ldr+br trampoline）、`arch/arm64/kernel/patching.c`。
- **判定**：**PATTERN**——机制与 jump_label 同源，落点明确、风险低；价值高（消除 tracepoint/sched/preempt 等热路径间接调用开销）。可进一步 `HAVE_STATIC_CALL_INLINE`（需 OBJTOOL，riscv 无 → 暂止步 out-of-line）。

### 2. HAVE_RELIABLE_STACKTRACE —— PATTERN（livepatch 前置）
- **候选**：`HAVE_RELIABLE_STACKTRACE`（来源：Kconfig §2a；`arch/Kconfig:1418`）。arm64 无条件 select，x86 `if UNWINDER_ORC || STACK_VALIDATION`。
- **现状**：riscv **无** `arch_stack_walk_reliable()`（`grep` 全 `arch/riscv/` 无匹配）。现有 `arch/riscv/kernel/stacktrace.c` 用 `CONFIG_FRAME_POINTER` 的 `walk_stackframe()`，**已跟踪异常边界** `handle_exception`/`ret_from_exception_end`（可据此判定不可靠帧）。
- **落点**：`arch/riscv/kernel/stacktrace.c` 增 `arch_stack_walk_reliable()`：遇异常/中断帧、FP 不可信、越界即 `return -EINVAL`。参照 `arch/arm64/kernel/stacktrace.c`（`kunwind_state`+source 跟踪）。
- **判定**：**PATTERN**——基于既有 FP unwinder 增可靠性判定；是 livepatch 一致性模型的硬前置，价值随 #3 兑现。

### 3. HAVE_LIVEPATCH —— PORTABLE（gated on #2）
- **候选**：`HAVE_LIVEPATCH`（来源：Kconfig §2a；`kernel/livepatch/Kconfig:2`）。arm64 无条件、x86 `if X86_64`。
- **现状**：riscv **无** select。但底座齐备：`select HAVE_DYNAMIC_FTRACE_WITH_ARGS`(`Kconfig:163`)+`WITH_CALL_OPS`(:162)+`WITH_DIRECT_CALLS`(:161)；`LIVEPATCH` 依赖 `DYNAMIC_FTRACE_WITH_REGS||WITH_ARGS`(`livepatch/Kconfig:9`)——riscv 满足 WITH_ARGS 支。**arm64 无 `asm/livepatch.h`**（纯 ftrace+通用 klp），故 arch 专属代码极少。
- **落点**：`arch/riscv/Kconfig` `select HAVE_LIVEPATCH`；核对 ftrace WITH_ARGS/DIRECT 路径能改写 `pt_regs->epc`（`ftrace_regs`）以重定向被打补丁函数。**真正 arch 工作在 #2**。
- **判定**：**PORTABLE**（gated）——符号本身是 `select` + 通用 klp，arch 增量几近为零；唯一硬门槛是 #2 reliable stacktrace（单独计入 PATTERN，避免重复计工）。

### 4. HAVE_HW_BREAKPOINT —— PATTERN（用户可见缺口）
- **候选**：`HAVE_HW_BREAKPOINT`（来源：Kconfig §2a；`arch/Kconfig:445`，`depends on PERF_EVENTS`——riscv 有 PERF_EVENTS）。x86 无条件、arm64 `if PERF_EVENTS`。
- **现状**：riscv **无**任何硬件断点/观察点接入：无 `arch/riscv/kernel/hw_breakpoint.c`；`arch/riscv/kernel/ptrace.c` regset 仅 `X/F/V/TAGGED_ADDR_CTRL/CFI`，**无 HW_BREAK/HW_WATCH**；全树无 Sdtrig/trigger CSR(`tselect`/`tdata1/2`) 使用。→ **gdb 硬件断点、`perf mem`、内核 data breakpoint 当前全不可用**。
- **落点**：新增 `arch/riscv/kernel/hw_breakpoint.c`（实现 `arch_install/uninstall_hw_breakpoint`、`hw_breakpoint_arch_parse`）+ Sdtrig 触发器 CSR 访问（S 态经 **SBI DBTR 扩展**，M 态直接访 `tselect/tdata*`）+ ptrace `REGSET_HW_BREAK/WATCH`。参照 `arch/arm64/kernel/hw_breakpoint.c`、`arch/x86/kernel/hw_breakpoint.c`。
- **判定**：**PATTERN**——需 Sdtrig 硬件 + SBI-DBTR 固件 ABI；有明确双参照，用户价值高。硬件依赖真实存在（Sdtrig 属 RISC-V debug 规范，多数实现已带），非 N-A。

### 5. NMI 簇（HAVE_NMI / HAVE_PERF_EVENTS_NMI / HAVE_HARDLOCKUP_DETECTOR_PERF / TRACE_IRQFLAGS_NMI_SUPPORT / ARCH_HAS_NMI_SAFE_THIS_CPU_OPS）—— PATTERN
- **候选**：5 符号（`arch/Kconfig:291/463/470/300/587`）。arm64 的 perf-NMI 链**全建在伪 NMI 上**：`HAVE_PERF_EVENTS_NMI if ARM64_PSEUDO_NMI`、`HAVE_HARDLOCKUP_DETECTOR_PERF if PERF_EVENTS && ...`。
- **现状（关键）**：riscv **无真 NMI**——`arch/riscv/include/asm/irqflags.h` 的 `arch_local_irq_disable()` = `csr_clear(CSR_STATUS, SR_IE)`，**清全局 SIE = 屏蔽所有 S 态中断**，无优先级阈值机制。traps.c 中的 `irqentry_nmi_enter/exit`（:156~352）只是 **generic-entry 对内核态异常(非法指令/访存故障/misalign)的 NMI-context 记账**，**非硬件 NMI 源**。全树无 Smrnmi/RNMI（且 Smrnmi 属 M 态，S 态 Linux 不可直接用）。
- **落点**：伪 NMI 须靠 **AIA（Ssaia）IPRIO 优先级阈值**——令 `local_irq_disable()` 改为「抬高中断优先级阈值」而非清 SIE，放行高优先级(NMI 类)中断。落点：`arch/riscv/include/asm/irqflags.h`（阈值化屏蔽）+ `drivers/irqchip/irq-riscv-imsic-*.c`/`irq-riscv-intc.c`（NMI 优先级投递）+ `arch/riscv/kernel/traps.c`/entry（`TRACE_IRQFLAGS_NMI_SUPPORT` 的 irqflags 记账）。参照 arm64 `ARM64_PSEUDO_NMI`(ICC_PMR)。
- **判定**：**PATTERN**（gated on AIA）——链条：`HAVE_NMI`(基) → `HAVE_PERF_EVENTS_NMI`(perf 用 NMI 溢出) → `HAVE_HARDLOCKUP_DETECTOR_PERF`；`TRACE_IRQFLAGS_NMI_SUPPORT` 与 entry 记账捆绑；`ARCH_HAS_NMI_SAFE_THIS_CPU_OPS` 另需 AMO 化 this_cpu（见下），价值低。
- **重要务实旁注**：**硬锁检测今日已可用**——`HAVE_HARDLOCKUP_DETECTOR_BUDDY`(`lib/Kconfig.debug:1168`)仅 `depends on SMP, default y`，非 arch-select，riscv(SMP) **自动具备**；`HARDLOCKUP_DETECTOR` 只需 PERF/BUDDY/ARCH 之一。故 perf-NMI 硬锁检测器是**精度增量**而非从零缺口，urgency 因此下调。

## 全量判定表

| 候选 | 来源 | 判定 | 缺口性质 / riscv 落点 | 备注(arm64/x86 状态 / 假阳说明) |
|---|---|---|---|---|
| `HAVE_STATIC_CALL` | Kconfig `arch/Kconfig:1691` | **PATTERN** | 缺 `static_call.h`+trampoline；text-patch 基座已全 → 新 `arch/riscv/include/asm/static_call.h` + `arch/riscv/kernel/static_call.c` | x86 无条件 / arm64 `if CFI`。非假阳(无 config/def_bool/传递 select)。本批最优先 |
| `HAVE_RELIABLE_STACKTRACE` | Kconfig `arch/Kconfig:1418` | **PATTERN** | 无 `arch_stack_walk_reliable()` → `arch/riscv/kernel/stacktrace.c` 增可靠性判定（复用既有 FP unwinder + 异常帧识别） | x86 `if ORC/STACK_VAL`，arm64 无条件。livepatch 前置 |
| `HAVE_LIVEPATCH` | Kconfig `kernel/livepatch/Kconfig:2` | **PORTABLE**(gated) | ftrace WITH_ARGS/CALL_OPS/DIRECT 已全；`select HAVE_LIVEPATCH` + 核对 ftrace 改 `pt_regs->epc`。真正 arch 工作在 reliable-stacktrace | arm64 无条件+**无 asm/livepatch.h**；x86 `if X86_64`。跨引前两轮「真实缺口」 |
| `HAVE_HW_BREAKPOINT` | Kconfig `arch/Kconfig:445` | **PATTERN** | ptrace 无 HW_BREAK regset、无 hw_breakpoint.c、无 Sdtrig → 新 `arch/riscv/kernel/hw_breakpoint.c` + SBI-DBTR/Sdtrig CSR + ptrace regset | x86 无条件 / arm64 `if PERF_EVENTS`。用户可见(gdb 硬件断点当前不可用) |
| `HAVE_NMI` | Kconfig `arch/Kconfig:291` | **PATTERN** | 无真 NMI(`irqflags.h` 清 SIE 全屏蔽) → AIA IPRIO 阈值伪 NMI：`irqflags.h`+`irq-riscv-imsic-*`+entry | 两家都 select；arm64 建于 PSEUDO_NMI。gated on AIA(Ssaia) |
| `HAVE_PERF_EVENTS_NMI` | Kconfig `arch/Kconfig:463` | **PATTERN** | perf 溢出经 NMI 投递 → `drivers/perf/riscv_pmu_sbi.c`(sscofpmf 溢出)接伪 NMI 路径 | arm64 `if ARM64_PSEUDO_NMI`。gated on HAVE_NMI |
| `HAVE_HARDLOCKUP_DETECTOR_PERF` | Kconfig `arch/Kconfig:470` | **PATTERN** | 精度增量(perf-NMI 硬锁检测) → 依 PERF_EVENTS_NMI | **buddy 检测器今日已自动可用**(SMP);此为增量非从零。gated |
| `TRACE_IRQFLAGS_NMI_SUPPORT` | Kconfig `arch/Kconfig:300` | **PATTERN** | NMI 上下文 irqflags/lockdep 记账正确 → `arch/riscv/kernel/entry.S`/traps.c，与 NMI 工作捆绑 | 两家都 select。独立价值低，gated on NMI |
| `ARCH_HAS_NMI_SAFE_THIS_CPU_OPS` | Kconfig `arch/Kconfig:587` | **PATTERN** | this_cpu 用 asm-generic(非原子,非 NMI 安全) → 新 `arch/riscv/include/asm/percpu.h` 用 AMO(amoadd 等,tp 相对)实现单指令 NMI 安全 | s390/arm64/x86 有。**注意非** riscv 已有的 `ARCH_HAVE_NMI_SAFE_CMPXCHG`(`Kconfig:58`)。消费方 SRCU/RCU `NEED_SRCU_NMI_SAFE` 仅在 HAVE_NMI 时生效；cmpxchg 回退已覆盖 → **价值低,gated** |
| `HAVE_ARCH_KCSAN` | Kconfig `lib/Kconfig.kcsan:3` | **PORTABLE** | 通用编译器 TSAN sanitizer → `arch/riscv/Kconfig` `select HAVE_ARCH_KCSAN` + 少量 arch: 低层文件 `KCSAN_SANITIZE:=n`、entry noinstr 审计(riscv 已 GENERIC_ENTRY) | x86 `if X86_64`,arm64 `if EXPERT`。**跨引前两轮/memory**已判真实缺口,不重复深挖 |
| `HAVE_C_RECORDMCOUNT` | Kconfig `kernel/trace/Kconfig:119` | **N-A** | **不需要**：riscv `select FTRACE_MCOUNT_USE_PATCHABLE_FUNCTION_ENTRY`(`Kconfig:103`)走 `-fpatchable-function-entry`(`Makefile:18`),编译器直出 `__patchable_function_entries`;`FTRACE_MCOUNT_USE_RECORDMCOUNT` 被 `!...PATCHABLE_FUNCTION_ENTRY`(`kernel/trace/Kconfig:897`)排除,recordmcount 永不运行 | arm64 仍(遗留)select,但同走 patchable-entry。riscv 正确略去。**等价能力 ALREADY(经 patchable-entry)**,select 该符号为死代码 |

## 交叉引用（前两轮/memory 已判，本轮仅给落点不重复深挖）
- `HAVE_ARCH_KCSAN`、`HAVE_STATIC_CALL`、`HAVE_LIVEPATCH`、`HAVE_RELIABLE_STACKTRACE`：均见 `_baseline_riscv.md` §二「真实缺口」与 memory `riscv-portability-studies`。本轮补齐 riscv 落点文件与四态归位（KCSAN→PORTABLE；static_call/reliable-stacktrace→PATTERN；livepatch→PORTABLE gated）。

## 结论
本簇 **10/11 是真实可移植/待补缺口**（PORTABLE 2 + PATTERN 8），仅 `HAVE_C_RECORDMCOUNT` 因 riscv 选用 patchable-function-entry 路线而 N-A。**最高性价比三连**：`HAVE_STATIC_CALL`（基座现成）→ `HAVE_RELIABLE_STACKTRACE` → `HAVE_LIVEPATCH`（一条价值链）。**用户可见硬缺口**：`HAVE_HW_BREAKPOINT`（gdb 硬件断点）。**NMI 簇**（5 符号）统一 gated on AIA 伪 NMI，工程量最大且相互依赖；但硬锁检测经 buddy 今日已可用，perf-NMI 链为精度增量，优先级可后置。
