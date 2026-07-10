# RISC-V Core ABI、可观测性与安全加固接口差距

## 1. 结论与范围

本文聚焦 RISC-V 相对 x86/arm64 在 core ABI、栈回溯、perf/ptrace、ftrace/kprobes、BPF JIT、原子操作、可执行内存和内核栈硬化方面的接口差距。候选以统一注册表中的 `CORE-01` 至 `CORE-18` 为唯一编号，不再沿用原始研究报告的 25 个 `CAH-*` 条目计数。

固定核验基线：

- mainline：`d96fcfe1b7f94ac742984ae7986b94a116abff1b`，Linux 7.2-rc2，提交日期 2026-07-10。
- linux-next：`bee763d5f341b99cf472afeb508d4988f62a6ca1`，快照日期 2026-07-10。
- 邮件窗口：2025-01-01 至 2026-07-10。
- 状态口径：`active RFC` 表示窗口内存在仍在修订、且固定基线尚未合入的精确系列；`unclaimed` 表示缺口真实，但未找到覆盖该候选完整范围的公开系列。

统一候选共 **18 项**：

| 维度 | 分类 | 数量 |
|---|---|---:|
| 状态 | active RFC | 6 |
| 状态 | unclaimed | 12 |
| 优先级 | P0 | 7 |
| 优先级 | P1 | 7 |
| 优先级 | P2 | 4 |
| 通用性 | G0 | 2 |
| 通用性 | G1 | 8 |
| 通用性 | G3 | 6 |
| 通用性 | G4 | 2 |
| 原始架构 | x86+arm64 | 13 |
| 原始架构 | arm64 | 2 |
| 原始架构 | x86 | 3 |

最适合立即投入的工作分成两类：

1. **帮助活跃系列合入**：`CORE-01`、`CORE-02`、`CORE-06`、`CORE-07`、`CORE-08`、`CORE-15`。
2. **新开边界清晰的 RISC-V 系列**：优先 `CORE-14`、`CORE-13`、`CORE-16`，随后推进 `CORE-04`、`CORE-12`、`CORE-17`。

## 2. 十八项总表

| ID | 候选 | 原始参考架构 | G | 优先级 | 状态 | 总分 | 关键依赖 |
|---|---|---|---|---|---|---:|---|
| CORE-01 | reliable unwinder 与 livepatch enablement | x86+arm64 | G1 | P0 | active RFC | 26 | frame-record contract、异常栈边界 |
| CORE-02 | perf/ptrace/KGDB hardware breakpoints | x86+arm64 | G4 | P1 | active RFC | RISC-V Debug triggers、资源所有权 |
| CORE-03 | RISC-V static-call backend | x86+arm64 | G3 | P1 | unclaimed | text patch、模块距离、I-cache |
| CORE-04 | 完整 `ftrace_regs` 与 CFI-compatible call-ops | arm64 | G3 | P1 | unclaimed | CFI/KCFI、trampoline、模块 |
| CORE-05 | kprobes-on-ftrace 与 optprobes 加速链 | x86+arm64 | G3 | P2 | unclaimed | CORE-04；optprobes 还依赖 CORE-16 |
| CORE-06 | 实现 `arch_bpf_stack_walk()` | x86+arm64 | G1 | P0 | active RFC | 稳定 BPF JIT frame ABI |
| CORE-07 | RISC-V BPF exceptions | x86+arm64 | G1 | P0 | active RFC | CORE-06 |
| CORE-08 | BPF bpf2bpf 与 subprog tailcalls 混用 | x86+arm64 | G1 | P0 | active RFC | tailcall counter、统一 frame ABI |
| CORE-09 | BPF stack arguments 与 private stack | x86+arm64 | G1 | P1 | unclaimed | CORE-06/07/08 的栈 ABI |
| CORE-10 | BPF timed `may_goto` | x86 | G3 | P1 | unclaimed | JIT 多 pass offset、branch range |
| CORE-11 | BPF tail-call poke descriptor | x86 | G3 | P2 | unclaimed | CORE-16、SMP text patch |
| CORE-12 | RISC-V KCSAN architecture enablement | x86+arm64 | G1 | P1 | unclaimed | 原子/entry/uaccess 不可递归插桩 |
| CORE-13 | native acquire/release AMO variants | arm64 | G3 | P0 | unclaimed | LKMM、LR/SC 失败路径 ordering |
| CORE-14 | 选择 `HAVE_CMPXCHG_LOCAL` | x86+arm64 | G0 | P0 | unclaimed | 宽度与 PREEMPT 语义验证 |
| CORE-15 | `HAVE_CMPXCHG_DOUBLE` 与 Zacas/fallback | x86+arm64 | G4 | P2 | active RFC | Zacas、编译期能力与运行时发现 |
| CORE-16 | 实现 `ARCH_HAS_EXECMEM_ROX` | x86+arm64 | G1 | P0 | unclaimed | pageattr、I-cache、alias/W^X |
| CORE-17 | 默认启用 `VMAP_STACK` | x86+arm64 | G0 | P1 | unclaimed | RV32、crash/hibernate、overflow stack |
| CORE-18 | 实现 `arch_within_stack_frames()` | x86 | G1 | P2 | unclaimed | CORE-01 的可靠 frame metadata |

## 3. 能力链与实施依赖

### 3.1 reliable stacktrace、livepatch 与 frame-aware hardening

`CORE-01` 是这一组的根节点。livepatch 在切换任务前必须证明被替换函数不在任何任务栈上，因此普通“尽力而为”的 backtrace 不足以选择 `HAVE_LIVEPATCH`。可靠 unwinder 还可为 `CORE-18` 提供 frame 边界和异常栈终止规则；`CORE-17` 的 vmapped stack/guard page 则会扩大必须覆盖的栈形态。

推荐顺序：

1. 合入 `CORE-01` 的 reliable frame-record unwinder、负测和异常栈规则。
2. 在同一 frame contract 上启用 livepatch，并覆盖 module/ftrace/kprobe 并发。
3. 以只观测或 debug 模式原型验证 `CORE-18`，避免 hardened usercopy 误拒绝。
4. 将 `CORE-17` 的默认策略变更放在栈回溯、kdump 和 RV32 回归稳定之后。

### 3.2 breakpoint、ftrace、kprobe 与 text patch

`CORE-02` 解决硬件触发器到 perf/ptrace/KGDB 的资源管理闭环；它不等于 kprobe，但可以统一用户 watchpoint、perf breakpoint 与调试器的 trigger ownership。

动态插桩链的主依赖为：

```text
CORE-04 完整 ftrace_regs/CFI call-ops
  -> CORE-05 kprobes-on-ftrace
  -> CORE-05 optprobes
       -> CORE-16 execmem ROX
```

`CORE-03` static call 与该链共享 text patch、模块范围和 I-cache 同步基础，但应作为独立系列推进。`CORE-16` 是 optprobe detour buffer、BPF poke、ftrace trampoline 和模块可执行内存的共同安全底座。

### 3.3 BPF JIT 栈 ABI

BPF 候选不是八个互不相关的 feature bit，而是一条共享 frame ABI 的链：

```text
CORE-06 arch_bpf_stack_walk
  -> CORE-07 exceptions
  -> CORE-08 bpf2bpf + subprog tailcalls
  -> CORE-09 stack arguments/private stack

CORE-10 timed may_goto             （相对独立的 lowering）
CORE-11 tail-call poke descriptor  （依赖 CORE-16 与 text patch）
```

`CORE-06`、`CORE-07`、`CORE-08` 已有活跃系列，近期贡献重点应是复现、review、补齐组合测试和修复 CI denylist，而不是并行重写一套不兼容的 JIT frame 约定。`CORE-09` 必须等待 stack walk、异常 landing、tailcall counter 和 callee frame 规则稳定，否则 private stack 会放大不可回溯和跨任务栈污染风险。

### 3.4 原子操作与 KCSAN

`CORE-14` 是最小接线项：接口已经存在，只缺 Kconfig 能力声明。`CORE-13` 是语义等价的性能优化，需要用 `.aq`/`.rl` 取代 fallback fence 组合。`CORE-15` 则涉及 Zacas 和双 machine-word 原子能力，不能把运行时 ISA 发现直接包装成全局编译期承诺。

`CORE-12` KCSAN 依赖对这些原子路径、异常入口和 uaccess 的系统审计。合理顺序是先完成 `CORE-14` 和 `CORE-13` 的语义测试，再以 `EXPERT` 配置试启用 KCSAN；`CORE-15` 不应成为 KCSAN 的前置条件。

### 3.5 execmem 与 hardening

`CORE-16` 的目标不是给单一调用者增加一次 writable 切换，而是建立统一的“RW 生成、ROX 执行、无持久 W+X”契约。它直接服务于 BPF JIT、kprobes/optprobes、ftrace trampoline 和 modules。

`CORE-17` 与 `CORE-18` 分别强化栈溢出隔离和跨 frame usercopy 检测。前者已有架构基础，属于默认策略和兼容性证明；后者依赖稳定 frame layout，必须优先复用 `CORE-01`，不能独立复制 x86 的 frame walk 假设。

## 4. 活跃 RFC：优先参与 review、测试与收敛

<a id="core-01"></a>
### CORE-01：reliable unwinder 与 livepatch enablement

- **源报告映射**：`CAH-01 + CAH-02`。
- **分类**：G1；P0；active RFC；原始架构 x86+arm64。
- **六维评分**：impact=5，generality=4，readiness=5，validation=4，hardware-independence=4，acceptance=4；**总分=26**。
- **基线状态**：2026-06 v4 RESEND 覆盖 reliable unwinder、livepatch enablement 和 selftest；固定 mainline/linux-next 均未合入。
- **源码与符号**：`HAVE_RELIABLE_STACKTRACE`、`arch/riscv/kernel/stacktrace.c::{walk_stackframe,arch_stack_walk,arch_stack_walk_reliable}`、`kernel/stacktrace.c::stack_trace_save_tsk_reliable()`、`HAVE_LIVEPATCH`、`kernel/livepatch/transition.c::{klp_check_stack,klp_try_switch_task}`、`include/linux/livepatch.h::klp_have_reliable_stack()`、`arch/riscv/Kconfig`。
- **RISC-V 缺口**：现有 backtrace 可用于诊断，但不能向 generic core 证明遍历完整，也不能可靠区分正常根帧、损坏 frame record、异常栈切换和提前停止。livepatch 因而无法证明被替换函数已离开全部任务栈。
- **移植/实现方案**：先完成 frame-record metadata、stack boundary helper、异常/IRQ/overflow/kthread 根帧终止规则，再选择 `HAVE_RELIABLE_STACKTRACE`；其后单独选择 `HAVE_LIVEPATCH` 并接入 RISC-V selftests。
- **首版系列边界**：第一阶段只提交 unwinder、边界规则和正负测试；第二阶段提交 livepatch Kconfig、架构前缀、module relocation/text patch 验证。
- **依赖关系**：阻塞 `CORE-18`；与 `CORE-04`、`CORE-05`、modules text modification 存在并发交互；`CORE-17` 增加需要覆盖的栈形态。
- **主要阻塞**：编译器 frame-record contract；异常入口和所有栈切换；不能把“停止”当成“完成”；module PLT、alternatives、ftrace 和 livepatch patching 串行化。
- **验证**：`tools/testing/selftests/livepatch/`；损坏 frame record 负测；IRQ/overflow stack、kthread、busy task、preempt、module unload、ftrace/kprobe 并发；QEMU SMP 和至少一套真实硬件；FP/非 FP 配置必须有明确 Kconfig 行为。
- **维护者方向**：RISC-V 架构；Josh Poimboeuf、Mark Rutland；Jiri Kosina、Miroslav Benes、Petr Mladek。
- **原始补丁与源码**：[v4 RESEND cover](https://lists.infradead.org/pipermail/linux-riscv/2026-June/093484.html)、[reliable unwinder patch](https://lists.infradead.org/pipermail/linux-riscv/2026-June/093489.html)、[RISC-V stacktrace](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kernel/stacktrace.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[livepatch transition](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/livepatch/transition.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

<a id="core-02"></a>
### CORE-02：perf/ptrace/KGDB hardware breakpoints

- **源报告映射**：`CAH-03`。
- **分类**：G4；P1；active RFC；原始架构 x86+arm64。
- **六维评分**：impact=5，generality=3，readiness=3，validation=3，hardware-independence=2，acceptance=3；**总分=19**。
- **基线状态**：2025-05 有 RISC-V RFC；固定 mainline/linux-next 均未选择 `HAVE_HW_BREAKPOINT`。
- **源码与符号**：`kernel/events/hw_breakpoint.c`、`include/linux/hw_breakpoint.h`、`arch/riscv/kernel/ptrace.c`、`arch/riscv/kernel/kgdb.c`；参考 `arch/arm64/kernel/hw_breakpoint.c` 和 `arch/x86/kernel/hw_breakpoint.c`。
- **RISC-V 缺口**：RISC-V triggers 未接入 perf breakpoint PMU，perf event、ptrace watchpoint 与 KGDB 无法共用 generic slot 管理、任务切换和回调分发。
- **移植/实现方案**：实现 `arch_*hw_breakpoint*` backend、trigger slot 枚举与编码、异常解码、per-task/per-CPU 安装、ptrace regset；选择 `HAVE_HW_BREAKPOINT` 后再让 KGDB 复用同一资源层。
- **首版系列边界**：先覆盖单地址 execute/load/store breakpoint 和 perf/ptrace；chained trigger、复杂 match 和 KGDB 可拆为后续阶段。
- **依赖关系**：依赖 RISC-V Debug trigger 规范和实现能力探测；KVM 必须定义 host/guest trigger ownership。
- **主要阻塞**：不同实现的 trigger 数量和 match 类型不一致；内核/用户地址过滤；CPU hotplug；虚拟化切换；Debug 规范版本差异。
- **验证**：`tools/testing/selftests/breakpoints/`；perf breakpoint events；ptrace exec/fork/single-step；CPU hotplug；KVM guest/host 隔离；KGDB。
- **维护者方向**：RISC-V、perf、ptrace、KGDB；Will Deacon、Peter Zijlstra。
- **原始补丁与源码**：[RISC-V RFC](https://lists.infradead.org/pipermail/linux-riscv/2025-May/070170.html)、[generic hw breakpoint core](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/events/hw_breakpoint.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[arm64 backend](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/kernel/hw_breakpoint.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

<a id="core-06"></a>
### CORE-06：实现 `arch_bpf_stack_walk()`

- **源报告映射**：`CAH-12`。
- **分类**：G1；P0；active RFC；原始架构 x86+arm64。
- **六维评分**：impact=5，generality=4，readiness=5，validation=4，hardware-independence=4，acceptance=4；**总分=26**。
- **基线状态**：2026-06 有 v2 活跃系列；固定 mainline/linux-next 的 RISC-V JIT 未实现该 hook。
- **源码与符号**：`kernel/bpf/core.c::arch_bpf_stack_walk()`、`kernel/bpf/{helpers.c,stream.c,core.c}`、`arch/riscv/net/bpf_jit_comp64.c`。
- **RISC-V 缺口**：BPF exception、debug、stream 和 stack trace 路径无法沿 RISC-V JIT frame 恢复调用链。
- **移植/实现方案**：定义稳定的 JIT frame record 和返回地址规则，实现有界 walker，并与普通内核 unwinder 共享栈边界检查；显式处理 tailcall 和异常 landing frame。
- **首版系列边界**：只建立 walker、frame ABI 和测试，不同时引入 private stack 或 poke 优化。
- **依赖关系**：是 `CORE-07` 的直接前置，也是 `CORE-08`、`CORE-09` 共享栈 ABI 的基础；可复用 `CORE-01` 的通用栈边界思想，但两种 frame ABI 不应混为一体。
- **主要阻塞**：JIT prologue/epilogue 必须稳定；不同 JIT feature 组合不能产生 walker 无法识别的帧。
- **验证**：BPF stack trace、exceptions、stream selftests；损坏 frame 和越界负测；tailcall、bpf2bpf、trampoline、private-stack 组合。
- **维护者方向**：BPF；Björn Töpel、Pu Lehui、Puranjay Mohan；RISC-V。
- **原始补丁与源码**：[v2 cover](https://lists.infradead.org/pipermail/linux-riscv/2026-June/093432.html)、[`arch_bpf_stack_walk()` patch](https://lists.infradead.org/pipermail/linux-riscv/2026-June/093433.html)、[generic BPF core](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/bpf/core.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

<a id="core-07"></a>
### CORE-07：RISC-V BPF exceptions

- **源报告映射**：`CAH-13`。
- **分类**：G1；P0；active RFC；原始架构 x86+arm64。
- **六维评分**：impact=5，generality=4，readiness=5，validation=4，hardware-independence=4，acceptance=4；**总分=26**。
- **基线状态**：2026-06 v2 活跃系列；固定基线中 `bpf_jit_supports_exceptions()` 仍走 false weak default。
- **源码与符号**：`bpf_jit_supports_exceptions()`、`kernel/bpf/core.c`、`kernel/bpf/verifier.c`、`arch/riscv/net/bpf_jit_comp64.c`、`tools/testing/selftests/bpf`。
- **RISC-V 缺口**：verifier 因架构 capability 为 false 而拒绝异常功能；JIT 缺 exception callback lowering、异常 landing、栈恢复和可靠 caller 定位。
- **移植/实现方案**：在 `CORE-06` 的 frame ABI 上实现 exception callback lowering、epilogue/landing 和返回值恢复，通过完整 selftests 后再返回 true。
- **首版系列边界**：JIT exception lowering、stack walk 接线、selftests 和 CI denylist 移除；不同时引入 private stack。
- **依赖关系**：硬依赖 `CORE-06`；必须与 `CORE-08` 的 tailcall frame 和 `CORE-09` 的栈布局兼容。
- **主要阻塞**：异常返回值 ABI、tailcall/bpf2bpf 混合栈、trampoline/kfunc 和 unwind 边界。
- **验证**：BPF exception 全集；JIT on/off；bpf2bpf、tailcall、trampoline、kfunc；故障注入和 CI。
- **维护者方向**：BPF；Björn Töpel、Pu Lehui、Puranjay Mohan；RISC-V。
- **原始补丁与源码**：[BPF exceptions patch](https://lists.infradead.org/pipermail/linux-riscv/2026-June/093434.html)、[CI denylist removal](https://lists.infradead.org/pipermail/linux-riscv/2026-June/093435.html)、[verifier gate](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/bpf/verifier.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

<a id="core-08"></a>
### CORE-08：BPF bpf2bpf 与 subprog tailcalls 混用

- **源报告映射**：`CAH-14`。
- **分类**：G1；P0；active RFC；原始架构 x86+arm64。
- **六维评分**：impact=5，generality=4，readiness=5，validation=4，hardware-independence=4，acceptance=4；**总分=26**。
- **基线状态**：2026-07 v6 活跃系列；截至 2026-07-10 未进入固定基线。
- **源码与符号**：`kernel/bpf/core.c::bpf_jit_supports_subprog_tailcalls()`、`kernel/bpf/verifier.c`、`arch/riscv/net/bpf_jit_comp64.c`。
- **RISC-V 缺口**：JIT 不能声明 subprogram 与 tailcall 混用能力，根因是 tailcall counter、callee frame 和返回地址恢复约定没有闭环。
- **移植/实现方案**：采用 v6 的统一 tailcall offset/helper，固定 prologue 中 counter 与 frame 布局，再实现 capability hook。
- **首版系列边界**：tailcall offset、frame/counter 修复、能力 hook、selftests 和 denylist 移除；避免混入 private stack。
- **依赖关系**：与 `CORE-06`、`CORE-07` 必须共享可回溯 frame ABI；是 `CORE-09` 的重要前置。
- **主要阻塞**：直接/间接 tailcall、最大 bpf2bpf 深度、异常路径和 tailcall counter 跨 subprog 生命周期。
- **验证**：tailcall selftests 全矩阵；最大深度；多层 subprogram；JIT blinding；exceptions；trampoline。
- **维护者方向**：BPF；Pu Lehui、Puranjay Mohan、Björn Töpel。
- **原始补丁与源码**：[v6 cover](https://lists.infradead.org/pipermail/linux-riscv/2026-July/094209.html)、[mixing bpf2bpf and tailcalls](https://lists.infradead.org/pipermail/linux-riscv/2026-July/094208.html)、[tailcall offset helper](https://lists.infradead.org/pipermail/linux-riscv/2026-July/094212.html)、[CI denylist removal](https://lists.infradead.org/pipermail/linux-riscv/2026-July/094206.html)。

<a id="core-15"></a>
### CORE-15：`HAVE_CMPXCHG_DOUBLE` 与 Zacas/fallback

- **源报告映射**：`CAH-22`。
- **分类**：G4；P2；active RFC；原始架构 x86+arm64。
- **六维评分**：impact=4，generality=3，readiness=2，validation=2，hardware-independence=1，acceptance=2；**总分=14**。
- **基线状态**：2025-03 有 RFC；RISC-V 未选择 `HAVE_CMPXCHG_DOUBLE`。该候选为中置信，RV64 双字更新通常需要 128-bit atomic capability。
- **源码与符号**：`arch/riscv/include/asm/cmpxchg.h`、`mm/slub.c`、`arch/riscv/Kconfig`。
- **RISC-V 缺口**：SLUB 等 generic consumer 无法使用双 machine-word 原子快路径；RV64 的自然实现依赖 Zacas `AMOCAS.Q`，不能假设所有 CPU 都支持。
- **移植/实现方案**：定义 extension-gated backend；评估仅在强制 Zacas 的构建中选择 capability，或者提供真正满足 generic 原子 contract 的 fallback。
- **首版系列边界**：先解决 capability 表达、对齐和 RV64 Zacas backend；无 Zacas fallback 若需要锁，应单独证明 NMI、递归和性能语义。
- **依赖关系**：与 `CORE-13`、`CORE-14` 同属原子接口链，但不应阻塞它们；KCSAN、KASAN 和 SLUB 是重要验证配置。
- **主要阻塞**：Kconfig 是编译期全局承诺，ISA extension 常为运行时发现；混合 CPU；RV32 语义；fallback 锁递归和 NMI 安全。
- **验证**：SLUB debug/torture；KASAN；CPU hotplug；Zacas 有/无平台；对齐负测；并发 freelist 压力。
- **维护者方向**：SLUB、atomics、RISC-V；Vlastimil Babka、Christoph Lameter、Will Deacon。
- **原始补丁与源码**：[RISC-V RFC](https://lists.infradead.org/pipermail/linux-riscv/2025-March/068203.html)、[SLUB consumer](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/mm/slub.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[RISC-V cmpxchg](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/include/asm/cmpxchg.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

## 5. 未认领候选：适合新开 RISC-V 系列

<a id="core-03"></a>
### CORE-03：RISC-V static-call backend

- **源报告映射**：`CAH-07`。
- **分类**：G3；P1；unclaimed；原始架构 x86+arm64。
- **六维评分**：impact=4，generality=3，readiness=3，validation=4，hardware-independence=3，acceptance=3；**总分=20**。
- **基线状态**：RISC-V 未选择 `HAVE_STATIC_CALL`；generic function-pointer fallback 可工作。
- **源码与符号**：`kernel/static_call.c::static_call_update()`、`include/linux/static_call.h`、`arch/x86/kernel/static_call.c`、`arch/arm64/include/asm/static_call.h`、RISC-V `patch_text()`。
- **RISC-V 缺口**：高频 static call 仍经可变函数指针间接调用，不能把 trampoline 或 call site 更新为直接跳转、nop 或 return0。
- **移植/实现方案**：先实现 permanent trampoline backend，再评估 inline call-site patching；定义 `JAL`、`AUIPC+JALR`、模块 PLT、null/return0 形式和 I-cache 同步。
- **首版系列边界**：只做 permanent trampoline 和 selftest；inline site patching 单独提交。
- **依赖关系**：与 ftrace/BPF/modules 共享 text patch 基础；不应强行绑定 `CORE-04` 或 `CORE-16`，但最终需统一 W^X 和 CFI 策略。
- **主要阻塞**：模块地址范围、压缩指令、SMP patch 原子性、CFI target、I-cache shootdown。
- **验证**：static-call selftest；tracepoint、fgraph、BPF、KVM/paravirt；module load/unload；SMP patch stress；objdump。
- **维护者方向**：Peter Zijlstra、Josh Poimboeuf、Steven Rostedt；RISC-V。
- **来源**：[generic static call](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/static_call.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[x86 backend](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/x86/kernel/static_call.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[RISC-V Kconfig](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/Kconfig?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

<a id="core-04"></a>
### CORE-04：完整 `ftrace_regs` 与 CFI-compatible call-ops

- **源报告映射**：`CAH-08 + CAH-09`。
- **分类**：G3；P1；unclaimed；原始架构 arm64。
- **六维评分**：impact=4，generality=3，readiness=3，validation=4，hardware-independence=3，acceptance=3；**总分=20**。
- **基线状态**：`arch_ftrace_get_regs()` 固定返回 `NULL`；RISC-V 只在 `!CFI` 时选择 `HAVE_DYNAMIC_FTRACE_WITH_CALL_OPS`，固定 linux-next 未改变。
- **源码与符号**：`HAVE_DYNAMIC_FTRACE_WITH_REGS`、`arch/riscv/include/asm/ftrace.h::arch_ftrace_get_regs()`、`include/linux/ftrace.h`、`HAVE_DYNAMIC_FTRACE_WITH_CALL_OPS`、`arch/riscv/kernel/ftrace.c`、`kernel/trace/ftrace.c`、`CONFIG_CFI_CLANG`。
- **RISC-V 缺口**：generic consumer 不能获得完整且可修改的 `pt_regs`；IPMODIFY、寄存器修改 callback 和 kprobes-on-ftrace 受限。CFI 开启后 call-ops 被主动关闭，说明当前 trampoline/call target 不满足类型契约。
- **移植/实现方案**：第一阶段定义完整 `ftrace_regs` 保存布局和 WITH_REGS trampoline；第二阶段增加 CFI-safe entry shim 和 call-ops target。
- **首版系列边界**：两阶段必须分别可构建、可运行；不要在同一首版中同时改写 generic ftrace selector。
- **依赖关系**：直接前置于 `CORE-05`；与 livepatch、BPF trampoline 和 modules 交叉；可复用 Genericization 的 call-ops 选择 helper，但二者不是同一候选。
- **主要阻塞**：寄存器保存成本、异常入口布局、function graph、KCFI type hash、模块 PLT、`-fpatchable-function-entry`。
- **验证**：ftrace selftests；function/function_graph；IPMODIFY；register-modifying callback；modules；RV32/RV64；Clang CFI/KCFI；livepatch、BPF、kprobes；objdump。
- **维护者方向**：Steven Rostedt、Mark Rutland、Naveen N. Rao、Sami Tolvanen、Kees Cook；RISC-V。
- **来源**：[RISC-V ftrace header](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/include/asm/ftrace.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[RISC-V ftrace implementation](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kernel/ftrace.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[generic ftrace](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/trace/ftrace.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

<a id="core-05"></a>
### CORE-05：kprobes-on-ftrace 与 optprobes 加速链

- **源报告映射**：`CAH-10 + CAH-11`。
- **分类**：G3；P2；unclaimed；原始架构 x86+arm64。
- **六维评分**：impact=3，generality=3，readiness=2，validation=3，hardware-independence=2，acceptance=2；**总分=15**。
- **基线状态**：RISC-V 未选择 `HAVE_KPROBES_ON_FTRACE` 或 `HAVE_OPTPROBES`。
- **源码与符号**：`kernel/kprobes.c::prepare_kprobe()`、`include/linux/kprobes.h::arch_prepare_kprobe_ftrace()`、`arch/x86/kernel/kprobes/ftrace.c`、`kernel/kprobes.c::{arch_prepare_optimized_kprobe,optimize_kprobe}`、`arch/x86/kernel/kprobes/opt.c`。
- **RISC-V 缺口**：函数入口探针仍主要走断点异常/单步模拟；热点探针没有 detour buffer 快路径。
- **移植/实现方案**：先实现 kprobes-on-ftrace 和一致的 regs/IPMODIFY contract；待 text relocation、远跳转和 ROX execmem 证明后再实现 optprobes。
- **首版系列边界**：首版严格限制为 kprobes-on-ftrace；optprobes 必须是独立后续系列。
- **依赖关系**：kprobes-on-ftrace 依赖 `CORE-04`；optprobes 依赖 `CORE-16`，并与 `CORE-01` livepatch、CFI 和 graph tracer 冲突处理交叉。
- **主要阻塞**：RVC 2/4 字节混合、PC-relative relocation、远跳、SMP patch 原子性、递归/preempt、模块、CFI landing。
- **验证**：kprobe selftests、tracefs events、递归和多 handler、module、unregister race；optprobe benchmark、RVC on/off、CPU hotplug、回滚故障注入。
- **维护者方向**：Masami Hiramatsu、Steven Rostedt、Naveen N. Rao、Mike Rapoport；RISC-V。
- **来源**：[generic kprobes](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/kprobes.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[x86 kprobes-on-ftrace](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/x86/kernel/kprobes/ftrace.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[x86 optprobes](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/x86/kernel/kprobes/opt.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

<a id="core-09"></a>
### CORE-09：BPF stack arguments 与 private stack

- **源报告映射**：`CAH-15 + CAH-16`。
- **分类**：G1；P1；unclaimed；原始架构 x86+arm64。
- **六维评分**：impact=4，generality=4，readiness=4，validation=4，hardware-independence=4，acceptance=3；**总分=23**。
- **基线状态**：x86/arm64 capability hook 返回 true；RISC-V 使用 false weak default。
- **源码与符号**：`bpf_jit_supports_stack_args()`、`bpf_jit_supports_private_stack()`、`kernel/bpf/{core.c,verifier.c,btf.c}`、`arch/riscv/net/bpf_jit_comp64.c`。
- **RISC-V 缺口**：JIT 无法接受超出 BPF 寄存器容量的 stack arguments，也不能切换到 private stack，限制 kfunc/subprog 形态并增加内核栈压力。
- **移植/实现方案**：先固定 stack-argument ABI、对齐、spill/load 和 callee frame offset；其后实现 per-CPU/per-task private stack 分配与 SP 切换。
- **首版系列边界**：首版只做 stack arguments；private stack 在 exceptions、tailcalls 和 stack walk ABI 稳定后另开系列。
- **依赖关系**：依赖 `CORE-06`、`CORE-07`、`CORE-08` 的共同 frame ABI；private stack 与 `CORE-17` 的 kernel stack 压力目标互补，但不能替代 VMAP_STACK。
- **主要阻塞**：BPF internal ABI 与 Linux RISC-V ABI 边界；递归 BPF、IRQ/NMI-like、preempt、migration、异常 unwind、跨任务污染。
- **验证**：many-args kfunc/subprog；边界参数数量和对齐；trampoline/exceptions；private-stack recursion、IRQ、tailcall、CPU hotplug；KASAN/KCSAN/lockdep。
- **维护者方向**：BPF 和 RISC-V BPF JIT。
- **来源**：[generic BPF capability hooks](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/bpf/core.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[RISC-V JIT](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/net/bpf_jit_comp64.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[arm64 reference](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/net/bpf_jit_comp.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[x86 reference](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/x86/net/bpf_jit_comp.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

<a id="core-10"></a>
### CORE-10：BPF timed `may_goto`

- **源报告映射**：`CAH-17`。
- **分类**：G3；P1；unclaimed；原始架构 x86。
- **六维评分**：impact=4，generality=3，readiness=3，validation=4，hardware-independence=3，acceptance=3；**总分=20**。
- **基线状态**：x86/arm64 返回 true；RISC-V weak default 为 false。
- **源码与符号**：`bpf_jit_supports_timed_may_goto()`、`kernel/bpf/fixups.c`、`kernel/bpf/core.c`、`arch/riscv/net/bpf_jit_comp64.c`。
- **RISC-V 缺口**：generic fixup 无法为 RISC-V 选择高效的有界倒计时 lowering。
- **移植/实现方案**：增加计数递减、条件跳转和超时路径 emission，固定 32/64 位宽度及多 pass 指令长度。
- **首版系列边界**：只实现 timed `may_goto` lowering、capability hook 和 selftests。
- **依赖关系**：相对独立，但必须与 `CORE-08` 的 tailcall counter 寄存器/栈布局兼容。
- **主要阻塞**：branch range、JIT pass offset 稳定、counter 共存、speculation 行为。
- **验证**：BPF `may_goto` selftests、边界计数、JIT blinding、branch-range stress、interpreter/JIT 对照。
- **维护者方向**：BPF 和 RISC-V BPF JIT。
- **来源**：[generic fixups](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/bpf/fixups.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[capability hook](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/bpf/core.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[arm64 reference](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/net/bpf_jit_comp.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

<a id="core-11"></a>
### CORE-11：BPF tail-call poke descriptor

- **源报告映射**：`CAH-18`。
- **分类**：G3；P2；unclaimed；原始架构 x86。
- **六维评分**：impact=3，generality=3，readiness=2，validation=3，hardware-independence=2，acceptance=2；**总分=15**。
- **基线状态**：generic weak hook 已存在，x86 有成熟 `bpf_arch_poke_desc_update()`；RISC-V 未实现。
- **源码与符号**：`kernel/bpf/arraymap.c::bpf_arch_poke_desc_update()`、`arch/x86/net/bpf_jit_comp.c`、`arch/riscv/net/bpf_jit_{core,comp64}.c`。
- **RISC-V 缺口**：tail-call map 更新不能将 JIT site 动态改写为 direct、indirect 或 null 路径，持续承担间接查表和跳转成本。
- **移植/实现方案**：定义 RISC-V poke descriptor 和固定长度 patchable sequence，支持三态更新并使用架构 text patch/I-cache shootdown。
- **首版系列边界**：先证明 patch sequence、并发状态机和 JIT image 生命周期；不得在 execmem ROX 未闭环时选择能力。
- **依赖关系**：强依赖 `CORE-16`；与 `CORE-03`、`CORE-05` 共用 SMP text patch 证明；与 `CORE-08` 的 tailcall ABI 交叉。
- **主要阻塞**：SMP 原子可见性、JIT 地址范围、RVC 长度、W^X、map update 并发、image free/reuse。
- **验证**：并发 map update、CPU migration、JIT image 回收；direct/null 循环切换；stale I-cache 和非法指令监测。
- **维护者方向**：BPF、RISC-V text patch、execmem。
- **来源**：[generic poke hook](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/bpf/arraymap.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[x86 implementation](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/x86/net/bpf_jit_comp.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[RISC-V JIT core](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/net/bpf_jit_core.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

<a id="core-12"></a>
### CORE-12：RISC-V KCSAN architecture enablement

- **源报告映射**：`CAH-19`。
- **分类**：G1；P1；unclaimed；原始架构 x86+arm64。
- **六维评分**：impact=4，generality=4，readiness=4，validation=4，hardware-independence=4，acceptance=3；**总分=23**。
- **基线状态**：RISC-V 未选择 `HAVE_ARCH_KCSAN`；x86-64 与 arm64 已选择。
- **源码与符号**：`lib/Kconfig.kcsan::{HAVE_ARCH_KCSAN,KCSAN}`、`kernel/kcsan/`、`arch/riscv/include/asm/{atomic.h,cmpxchg.h,barrier.h}`。
- **RISC-V 缺口**：generic runtime 和 compiler instrumentation 存在，但架构尚未证明 atomic、trap/IRQ、uaccess 和 noinstr 路径不会产生递归插桩或错误 watchpoint 行为。
- **移植/实现方案**：审计不可插桩路径和 atomic inline asm，补齐 annotation/hook，先以 `EXPERT` 选择能力并加入专门 CI。
- **首版系列边界**：只做架构审计、必要 annotation、Kconfig EXPERT 和测试；不要以“能编译”为完成标准。
- **依赖关系**：与 `CORE-13`、`CORE-14` 的原子实现直接相关；`CORE-15` 不是前置；可作为 `CORE-09` private stack 的并发验证器。
- **主要阻塞**：trap/IRQ recursion、noinstr 边界、uaccess、watchpoint runtime 自监控、GCC/Clang 差异。
- **验证**：KCSAN kselftests；LKDTM；lock/RCU/atomic torture；RV64 SMP、PREEMPT、modules；GCC/Clang。
- **维护者方向**：Marco Elver、Dmitry Vyukov、Andrew Morton、Will Deacon、Boqun Feng；RISC-V。
- **来源**：[KCSAN Kconfig](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/lib/Kconfig.kcsan?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[KCSAN core](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/kcsan?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[RISC-V atomics](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/include/asm/atomic.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[2026 KCSAN core activity](https://lore.kernel.org/linux-arm-kernel/20260410120318.862164111@kernel.org/)。

<a id="core-13"></a>
### CORE-13：native acquire/release AMO variants

- **源报告映射**：`CAH-20`。
- **分类**：G3；P0；unclaimed；原始架构 arm64。
- **六维评分**：impact=5，generality=4，readiness=4，validation=4，hardware-independence=4，acceptance=4；**总分=25**。
- **基线状态**：RISC-V 只显式实现 relaxed 与 full `.aqrl` 版本，acquire/release API 经 `atomic-arch-fallback.h` 组合额外 fence。
- **源码与符号**：`arch/riscv/include/asm/atomic.h`、`arch/riscv/include/asm/cmpxchg.h`、`include/linux/atomic/atomic-arch-fallback.h`、`arch/riscv/include/asm/barrier.h`。
- **RISC-V 缺口**：语义正确但常见 acquire/release RMW 不能直接使用 `.aq`/`.rl`，可能多发独立 fence。
- **移植/实现方案**：补齐 `arch_atomic_*_{acquire,release}`、`arch_atomic_fetch_*_{acquire,release}` 和 cmpxchg variants，保留 relaxed 与 full `.aqrl`。
- **首版系列边界**：按操作族拆分，先 atomic fetch/RMW，再 cmpxchg；每一批附 objdump 和 LKMM 证据。
- **依赖关系**：与 `CORE-12` KCSAN 验证互相促进；不依赖 Zacas；应先于更复杂的 `CORE-15`。
- **主要阻塞**：LKMM 对成功/失败 RMW 的 ordering；LR/SC cmpxchg 失败路径；Ztso 不得改变 API contract。
- **验证**：LKMM litmus/herd7；atomic selftests；locking/RCU torture；objdump 检查 fence 消除；竞争/非竞争微基准。
- **维护者方向**：Will Deacon、Peter Zijlstra、Boqun Feng、Mark Rutland；RISC-V。
- **来源**：[RISC-V atomic backend](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/include/asm/atomic.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[atomic fallback](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/linux/atomic/atomic-arch-fallback.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[RISC-V cmpxchg](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/include/asm/cmpxchg.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

<a id="core-14"></a>
### CORE-14：选择 `HAVE_CMPXCHG_LOCAL`

- **源报告映射**：`CAH-21`。
- **分类**：G0；P0；unclaimed；原始架构 x86+arm64。
- **六维评分**：impact=5，generality=4，readiness=5，validation=5，hardware-independence=5，acceptance=4；**总分=28**。
- **基线状态**：`arch_cmpxchg_local()` 已在 RISC-V `cmpxchg.h` 中实现，但 mainline/linux-next 均未选择 `HAVE_CMPXCHG_LOCAL`。
- **源码与符号**：`arch/riscv/include/asm/cmpxchg.h::arch_cmpxchg_local()`、`arch/riscv/Kconfig`、`mm/vmstat.c`、`lib/percpu_counter.c`。
- **RISC-V 缺口**：generic consumer 因 capability 为 false 不编译 local cmpxchg 快路径，这是接口已存在但能力未接线的最小差距。
- **移植/实现方案**：验证 1/2/4/8 字节和 PREEMPT 语义后选择 `HAVE_CMPXCHG_LOCAL`；若宽度不完整，先补实现或限制 contract。
- **首版系列边界**：实现/验证缺失宽度、Kconfig select、vmstat/percpu-counter 测试和 objdump，一组小系列即可。
- **依赖关系**：可独立推进；为 `CORE-12` 提供更完整的原子测试面；不依赖 `CORE-13` 或 `CORE-15`。
- **主要阻塞**：local 语义不能意外加入全局 barrier；RV32 64-bit；sub-word 实现和编译器约束。
- **验证**：vmstat/percpu-counter stress；CPU hotplug；PREEMPT_RT；atomic selftests；构建确认 consumer fast path；objdump。
- **维护者方向**：Andrew Morton、Dennis Zhou、Tejun Heo、Will Deacon；RISC-V。
- **来源**：[RISC-V cmpxchg](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/include/asm/cmpxchg.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[vmstat consumer](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/mm/vmstat.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[percpu counter](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/lib/percpu_counter.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

<a id="core-16"></a>
### CORE-16：实现 `ARCH_HAS_EXECMEM_ROX`

- **源报告映射**：`CAH-23`。
- **分类**：G1；P0；unclaimed；原始架构 x86+arm64。
- **六维评分**：impact=5，generality=4，readiness=5，validation=4，hardware-independence=4，acceptance=4；**总分=26**。
- **基线状态**：RISC-V 未选择 `ARCH_HAS_EXECMEM_ROX`；2026-07 的 `EXECMEM_KPROBES` writable 补丁暴露了当前权限模型缺口。
- **源码与符号**：`ARCH_HAS_EXECMEM_ROX`、`mm/execmem.c`、`include/linux/execmem.h`、`arch/riscv/mm/pageattr.c`、`set_memory_*()`、`CONFIG_STRICT_MODULE_RWX`。
- **RISC-V 缺口**：execmem core 不能统一采用 writable-but-non-executable 生成、完成后 ROX 的模型，部分调用者仍需要 W+X 窗口或改写 executable mapping。
- **移植/实现方案**：设计 RISC-V execmem range/allocator、RW alias 或严格 RW→ROX 状态机，统一 BPF JIT、kprobes、ftrace trampoline 和 modules。
- **首版系列边界**：先建立架构 allocator/range 和单一调用者验证，再迁移其他 consumer；最终选择 capability。避免一次性重写全部 text patch。
- **依赖关系**：是 `CORE-05` optprobes 和 `CORE-11` poke 的安全前置；与 `CORE-03`、`CORE-04` 共享 I-cache 和 patch serialization。
- **主要阻塞**：I-cache coherence、alias 映射、`set_memory_*()` 粒度、vmalloc/huge page、module/JIT 生命周期、SMP text patch。
- **验证**：`CONFIG_STRICT_MODULE_RWX`、`DEBUG_WX`；BPF JIT、kprobes、ftrace、modules；页表扫描无持久 W+X；并发生成/释放。
- **维护者方向**：Mike Rapoport、Kees Cook；BPF、kprobes、modules、RISC-V。
- **来源**：[generic execmem](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/mm/execmem.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[RISC-V page attributes](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/mm/pageattr.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[2026 writable EXECMEM_KPROBES patch](https://lists.infradead.org/pipermail/linux-riscv/2026-July/093771.html)。

<a id="core-17"></a>
### CORE-17：默认启用 `VMAP_STACK`

- **源报告映射**：`CAH-24`。
- **分类**：G0；P1；unclaimed；原始架构 x86+arm64。
- **六维评分**：impact=3，generality=4，readiness=4，validation=5，hardware-independence=5，acceptance=3；**总分=24**。
- **基线状态**：RISC-V 已选择 `HAVE_ARCH_VMAP_STACK` 并具备异常/IRQ/overflow stack 基础，但没有像 arm64 一样把 `VMAP_STACK` 作为默认硬化策略。
- **源码与符号**：`arch/riscv/Kconfig`、`arch/riscv/kernel/entry.S`、`arch/riscv/kernel/traps.c`、`arch/riscv/include/asm/thread_info.h`、`init/Kconfig::VMAP_STACK`。
- **RISC-V 缺口**：非 vmapped kernel stack 无 guard page，溢出可能静默破坏邻接内存。
- **移植/实现方案**：审计全部受支持配置后将 `VMAP_STACK` 设为默认，修复 early/secondary CPU、hibernate、crash/debug 路径，并保留显式关闭选项。
- **首版系列边界**：配置审计、缺陷修复、默认值切换和文档应分阶段，默认值变更放在最后。
- **依赖关系**：与 `CORE-01` 的异常/overflow stack unwind、`CORE-18` 的 frame 检测、kdump 和 KASAN 交叉。
- **主要阻塞**：vmalloc/TLB 开销、极早期异常、内存受限系统、RV32 地址空间、crash dump unwinding。
- **验证**：stack overflow selftest/LKDTM；CPU hotplug；suspend/hibernate；kdump；KASAN；PREEMPT_RT；RV32/RV64。
- **维护者方向**：RISC-V、Kees Cook、mm/vmalloc。
- **来源**：[RISC-V Kconfig](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/Kconfig?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[RISC-V traps](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kernel/traps.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[generic VMAP_STACK](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/init/Kconfig?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

<a id="core-18"></a>
### CORE-18：实现 `arch_within_stack_frames()`

- **源报告映射**：`CAH-25`。
- **分类**：G1；P2；unclaimed；原始架构 x86。
- **六维评分**：impact=3，generality=3，readiness=3，validation=3，hardware-independence=3，acceptance=2；**总分=17**。
- **基线状态**：x86 提供 frame-aware 实现；RISC-V 使用 generic fallback。该候选为中置信，因为正确性依赖稳定 frame layout。
- **源码与符号**：`mm/usercopy.c::check_stack_object()`、`include/linux/thread_info.h::arch_within_stack_frames()`、`arch/x86/include/asm/thread_info.h`、候选落点 `arch/riscv/include/asm/thread_info.h`。
- **RISC-V 缺口**：hardened usercopy 能判断对象位于 task stack，但不能进一步识别 copy 是否跨越当前函数 frame。
- **移植/实现方案**：复用 reliable frame metadata 做有界遍历，返回“位于单一 frame”“跨 frame”“无法判断”，不能把无法判断直接当失败。
- **首版系列边界**：先以 debug-only telemetry/KUnit 统计误报，再考虑接入强制 hardened usercopy 判定。
- **依赖关系**：强依赖 `CORE-01`；需覆盖 `CORE-17` 的 vmapped/overflow stack；与编译器优化、尾调用、inlining 直接相关。
- **主要阻塞**：异常 frame、无 frame-pointer 构建、编译器布局、错误拒绝合法 usercopy 的高回归风险。
- **验证**：hardened-usercopy selftests；LKDTM；异常/IRQ/overflow stack；Clang/GCC；不同优化级别；telemetry 误报分析。
- **维护者方向**：Kees Cook、Gustavo A. R. Silva；RISC-V；compiler/frame-layout 维护者。
- **来源**：[hardened usercopy](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/mm/usercopy.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[generic thread info](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/linux/thread_info.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[x86 frame check](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/x86/include/asm/thread_info.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

## 6. 跨报告去重与边界

原始 Core/ABI 报告有 25 个 `CAH-*` 条目，但统一注册表只保留 18 个 `CORE-*`。以下三项已移入 Genericization 领域，**不得重复计入本领域 18 项**：

| 原 Core 条目 | 统一 ID | 处理 |
|---|---|---|
| `CAH-04` ptrace register-offset table walker | `GEN-02` | 与 Genericization `HC-02` 合并，并缩小为 offset table walker；不宣称 RISC-V ptrace ABI 缺失。 |
| `CAH-06` `perf_get_regs_user()` 默认实现 | `GEN-03` | 与 `HC-03` 合并；复用现有 generic fallback，保留 x86-64 NMI override。 |
| `CAH-05` syscall trace symbol matcher | `GEN-18` | 与 `HC-27` 合并；参数化 prefix/compat 规则，不宣称 syscall ABI 不完整。 |

另有两个相关但不计入 CORE 主清单的通用化点：

- Genericization `HC-13` kprobe nested state 仅适合抽取 arm64/RISC-V 的小型 save/restore helper；x86 额外保存 flags，收益不足，降为附带清理。
- Genericization `HC-14` ftrace call-ops selector 可作为 `CORE-04` 的配套公共 helper，但它解决“选择哪个 ops”的重复控制流，`CORE-04` 解决 RISC-V 的完整 regs/CFI 能力，两者不可合并为一个编号。

## 7. 伪差距与不应立项项

以下项目不能再作为新的 RISC-V Core/ABI 贡献点：

1. **page-fault tracepoints**：RISC-V 已调用 `trace_page_fault_user()` 和 `trace_page_fault_kernel()`。
2. **irqentry/context tracking**：trap/IRQ entry 已接入 generic irqentry/context-tracking 主链，入口汇编不同不等于接口缺失。
3. **基础 ptrace/syscall ABI**：已有 `PTRACE_SET_SYSCALL_INFO`、`orig_a0` 和 `syscall_get_nr()`/参数/返回值/rollback helpers。
4. **用户 CFI signal context**：当前源码已有 RISC-V 用户 CFI 状态、ptrace regset 和 signal context；arm64 SVE/SME/GCS record 不能脱离对应 ISA/ABI 直接移植。
5. **KASAN enablement**：RISC-V 已支持 KASAN；KASAN 应作为 BPF、cmpxchg、execmem 和 VMAP_STACK 的验证配置，而不是新候选。
6. **`HAVE_PERF_EVENTS_NMI`**：SBI PMU overflow IRQ 不等于 NMI；需要真实的 RISC-V NMI 规范、入口和平台路由。
7. **`TRACE_IRQFLAGS_NMI_SUPPORT`**：这是 NMI entry/exit 语义的从属能力，不能独立选择。
8. **`__preserve_most` RISC-V enablement**：当前编译器和架构 ABI 尚无可用、稳定的 RISC-V contract，只能作为工具链观察项。
9. **仅有未来 ISA 设想的 CFI/atomic/debug 项**：没有 generic hook、Kconfig contract、UAPI 或当前 consumer 时，不进入贡献清单。

## 8. 验证矩阵

### 8.1 公共最低矩阵

| 维度 | 最低要求 | 重点候选 |
|---|---|---|
| 架构宽度 | RV64；涉及宽度、栈 ABI 或原子时增加 RV32 | CORE-01、09、13、14、15、17、18 |
| 编译器 | GCC、Clang；CFI 项增加 Clang CFI/KCFI | CORE-01、03、04、05、16、18 |
| 核心配置 | SMP、PREEMPT、modules、debug | 全部 |
| 硬化配置 | KASAN、KCSAN、DEBUG_WX、STRICT_MODULE_RWX、VMAP_STACK | CORE-05、09、11、12、15、16、17、18 |
| 虚拟平台 | QEMU virt；硬件能力项至少一套真实平台 | 全部；CORE-02/15 必须真实硬件 |
| 并发 | CPU hotplug、module load/unload、patch/update race | CORE-01 至 05、11、14 至 17 |
| 静态证据 | objdump、relocation、section、Kconfig capability | CORE-03、04、05、10、11、13、14、16 |
| 内存模型 | LKMM litmus/herd7、locking/RCU/atomic torture | CORE-12、13、14、15 |

### 8.2 候选到测试套件映射

| 候选 | 必跑验证 |
|---|---|
| CORE-01 | livepatch selftests、损坏 frame 负测、异常/overflow/kthread/module/ftrace/kprobe |
| CORE-02 | breakpoints selftests、perf、ptrace、KGDB、KVM host/guest trigger 隔离 |
| CORE-03 | static-call selftest、module、SMP patch stress、objdump |
| CORE-04 | ftrace selftests、function graph、IPMODIFY、CFI/KCFI、module、BPF/livepatch |
| CORE-05 | kprobe selftests、递归/注销 race、RVC、optprobe relocation/rollback |
| CORE-06 | BPF stack trace、stream、损坏 frame、tailcall/bpf2bpf/trampoline |
| CORE-07 | BPF exception 全集、JIT on/off、kfunc、故障注入 |
| CORE-08 | tailcall 全矩阵、最大深度、subprog、JIT blinding、exceptions |
| CORE-09 | many-args、private stack、递归、IRQ/preempt/migration、KASAN/KCSAN |
| CORE-10 | timed may_goto 边界、branch-range、interpreter/JIT 对照 |
| CORE-11 | 并发 tailcall map update、JIT image 回收、direct/null 循环、I-cache |
| CORE-12 | KCSAN、LKDTM、lock/RCU/atomic torture、GCC/Clang |
| CORE-13 | LKMM/herd7、objdump fence、locking/RCU torture、微基准 |
| CORE-14 | vmstat、percpu-counter、PREEMPT_RT、CPU hotplug、宽度测试 |
| CORE-15 | SLUB debug/torture、KASAN、Zacas 有/无、对齐和混合 CPU |
| CORE-16 | DEBUG_WX、STRICT_MODULE_RWX、BPF/kprobe/ftrace/module、页表扫描 |
| CORE-17 | stack overflow/LKDTM、hibernate、kdump、RV32/RV64、PREEMPT_RT |
| CORE-18 | hardened-usercopy、LKDTM、异常/IRQ/overflow stack、telemetry 误报 |

### 8.3 完成判据

候选不能以“编译通过”作为完成。每个补丁系列至少满足：

1. generic consumer 确实进入新路径，Kconfig capability 与实现一致。
2. fallback 与新路径在可观察行为上等价，性能项提供 objdump 或基准证据。
3. 不支持的硬件、ABI 或配置保持 capability false，或返回明确错误。
4. 不产生持久 W+X、未同步 I-cache、错误 unwind 成功、跨任务栈污染或错误原子 ordering。
5. mainline/linux-next 固定基线中没有已合入的重复实现，邮件状态没有被“邻近子系统活跃”误标为精确候选 active RFC。

## 9. 推荐贡献顺序

1. **立即 review/测试**：`CORE-01`、`CORE-06`、`CORE-07`、`CORE-08`；这四项已有活跃高价值系列。
2. **小型新系列**：`CORE-14`；接口已存在，只需补齐能力证明和接线。
3. **原子性能系列**：`CORE-13`；按操作族拆分并附 LKMM/objdump。
4. **安全基础设施**：`CORE-16`；先建立 ROX execmem contract，再解锁 optprobes 和 BPF poke。
5. **可观测性链**：`CORE-04` 后接 `CORE-05`；先完整 regs/CFI，再做 kprobes-on-ftrace。
6. **架构硬化**：`CORE-12`、`CORE-17`；先以 EXPERT/配置矩阵积累证据。
7. **硬件或强契约长期项**：`CORE-02`、`CORE-15`、`CORE-18`；需要真实硬件、编译器 frame contract 或运行时/编译期能力模型。

总体上，RISC-V 的基本 syscall/signal ABI 并不是本领域的主要短板。真正可持续的贡献空间集中在：把“已有 fallback”升级为可验证的架构 contract，把 BPF/ftrace/kprobe 的栈和 text patch 规则闭环，以及把 W^X、VMAP_STACK、KCSAN 和 frame-aware usercopy 提升到与成熟架构相近的验证强度。
