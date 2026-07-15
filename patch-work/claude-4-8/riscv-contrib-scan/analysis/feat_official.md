# §1 官方特性矩阵 TODO 候选四态判定（RISC-V 贡献点静态扫描）

> 来源：`Documentation/features/**/arch-support.txt`（内核树 `/Users/zq/Desktop/patch-work/linux-riscv`，只读）。
> 本批 6 项 riscv 均标 `TODO`，是三路信号里最可信的一路，但**判定时须穿透"矩阵 TODO"的检测口径**（见下"检测口径警示"）。

## 检测口径警示（影响本批全部判定，务必先读）

`tools/docs/features-refresh.sh` 生成 arch-support.txt 的算法是**朴素子串 grep + 状态粘滞**：

```
K = 头部 "# Kconfig:" 里的符号名
for arch: K_GREP = grep "$K" $(find arch/<arch> -name 'Kconfig*')   # 仅搜 arch/<arch>/ 目录下
   K_GREP 非空 → "ok"
   K_GREP 为空 → 保留该 arch 在旧文件里的原状态（ok 保持 ok，TODO 保持 TODO）
```

推论（本批已实测验证）：
1. 只搜 `arch/<arch>/Kconfig*`，**看不到** `arch/Kconfig` 里的 `default y if 64BIT` / 通用 `select`。→ 一个 arch 功能上已具备、但符号串没出现在自己目录，会被显示成 `TODO`（**假阳**）。
2. 状态**粘滞**：`ok` 一旦写入，即便后来 select 被删也不回退。→ `ok` 不等于"现在真的 select 了"。
3. 实测：`grep -rn "HAVE_VIRT_CPU_ACCOUNTING" arch/arm64 arch/x86 arch/riscv` **三家都无匹配**，但矩阵里 arm64/x86=ok、riscv=TODO —— 纯属历史粘滞 + riscv 从未被人工翻绿。

**结论：本批 "riscv=TODO" 必须逐项回源码核实，不能直接当缺口。** virt-cpuacct 即因此被判为 ALREADY 假阳。

## 摘要

- **候选总数**：6
- **四态计数**：ALREADY 1 / PORTABLE 0 / PATTERN 3 / N-A 2
  - ALREADY：virt-cpuacct（矩阵假阳）
  - PATTERN：cmpxchg-local、kprobes-on-ftrace、optprobes
  - N-A：user-ret-profiler、cBPF-JIT
- **本批 Top 候选（按价值排序）**：
  1. **cmpxchg-local**（PATTERN，**最高价值**）：arm64+x86+s390 都 ok，与 §2a `HAVE_CMPXCHG_LOCAL` 互为佐证；riscv 底层 `arch_cmpxchg_local` 已具备，只差一个 arch percpu 层。落点清晰、风险低。
  2. **virt-cpuacct**（ALREADY）：riscv64 已通过 `default y if 64BIT` 获得能力，矩阵 TODO 是假阳 —— **应从候选剔除**（至多补一行 cosmetic select 翻绿矩阵）。
  3. **kprobes-on-ftrace**（PATTERN，中-重）：受阻于 `KPROBES_ON_FTRACE depends on DYNAMIC_FTRACE_WITH_REGS`，而 riscv 走 WITH_ARGS/CALL_OPS 无 WITH_REGS —— 与 **arm64 同因 TODO**，非"加个 ftrace.c"即可。
  4. **optprobes**（PATTERN，低）：RV 定长指令 + 跳转范围/原子改写受限，与 arm64 同因 TODO，价值/可行性低。
  5. **user-ret-profiler**（N-A）：唯一消费者是 `arch/x86/kvm/x86.c`（x86 MSR 懒恢复），riscv 无对应消费者。
  6. **cBPF-JIT**（N-A）：classic-BPF JIT 遗留，已被 cBPF→eBPF + eBPF JIT 取代（riscv 已有 `HAVE_EBPF_JIT`），x86/arm64/riscv 一致 TODO —— **建议剔除**。

## Top 深度候选

### 1. cmpxchg-local（HAVE_CMPXCHG_LOCAL）— PATTERN，最高价值
- **候选**：`locking/cmpxchg-local`（来源：`Documentation/features/locking/cmpxchg-local/arch-support.txt`；riscv=TODO，arm64/x86/s390=ok）。与 §2a `HAVE_CMPXCHG_LOCAL` 同一符号，互为佐证。
- **现状**：
  - riscv **底层能力已具备**：`arch/riscv/include/asm/cmpxchg.h:288` `#define arch_cmpxchg_local(ptr,o,n) arch_cmpxchg_relaxed(...)`（含 1/2 字节 masked LR/SC 与 Zabha/Zacas amocas 路径；64 位 local 在 :297）。
  - 但 riscv **无 `arch/riscv/include/asm/percpu.h`**（已确认文件不存在）→ 完全走 `asm-generic/percpu.h`，其 `this_cpu_cmpxchg` 是 **local_irq_save/restore 版**（非 lock-free）。
  - riscv Kconfig **未** `select HAVE_CMPXCHG_LOCAL`（仅有 `ARCH_HAVE_NMI_SAFE_CMPXCHG`:58、`ARCH_USE_CMPXCHG_LOCKREF`:77）。
  - `HAVE_CMPXCHG_LOCAL` 定义在 `arch/Kconfig:598`（裸 `bool`，**无 default → 必须显式 select**）；全树唯一消费者 `mm/vmstat.c:547`（`#ifdef CONFIG_HAVE_CMPXCHG_LOCAL` 走 `this_cpu_try_cmpxchg` 的 `mod_zone_state` 快路，规避 irq-save）。
- **落点**：
  - 新增 `arch/riscv/include/asm/percpu.h`：仿 `arch/arm64/include/asm/percpu.h:156`（`_pcp_protect`）与 `:235-242`（`this_cpu_cmpxchg_{1,2,4,8} = _pcp_protect_return(cmpxchg_relaxed,...)`），用 `preempt_disable_notrace` + 既有 `arch_cmpxchg_relaxed/arch_cmpxchg_local` 实现 lock-free `this_cpu_cmpxchg`（loongarch `arch/loongarch/include/asm/percpu.h` 为另一 RISC 风格参照）。
  - `arch/riscv/Kconfig`：在 H 段（约 :155 `HAVE_BUILDTIME_MCOUNT_SORT` 附近）加 `select HAVE_CMPXCHG_LOCAL`。
- **判定**：**PATTERN**。理由：核心原子已 ALREADY，缺的是 arch percpu 层（新文件）+ 一行 select。**注**：若只加 select 不加 percpu 层，`this_cpu_try_cmpxchg` 仍是 irq-save 版，cmpxchg 重试循环每轮 irq 开销，反而不划算 —— 故完整方案须带 percpu.h（不是纯 PORTABLE 的一行 select）。无 HW 障碍（1/2 字节 cmpxchg 已由 masked LR/SC 或 Zabha 覆盖）。

### 2. virt-cpuacct（HAVE_VIRT_CPU_ACCOUNTING）— ALREADY（矩阵假阳）
- **候选**：`time/virt-cpuacct`（来源：`Documentation/features/time/virt-cpuacct/arch-support.txt`；riscv=TODO，arm64/x86 及另 11 家=ok）。
- **现状**：矩阵检测子串 `HAVE_VIRT_CPU_ACCOUNTING` 命中 `..._GEN`；而 `HAVE_VIRT_CPU_ACCOUNTING_GEN` 定义于 `arch/Kconfig:1054-1056` 为 **`default y if 64BIT`（无 depends）** → **riscv64 自动 =y**。其上层 `VIRT_CPU_ACCOUNTING_GEN`（`init/Kconfig:591-596`）依赖三项 riscv **均已满足**：`HAVE_CONTEXT_TRACKING_USER`（`arch/riscv/Kconfig:156`）、`HAVE_VIRT_CPU_ACCOUNTING_GEN`（=y）、`GENERIC_CLOCKEVENTS`（`kernel/time/Kconfig:20` `def_bool !LEGACY_TIMER_TICK` → riscv=y）。且 GEN 实现**全在通用层**（`kernel/sched/cputime.c` + 通用 entry 的 context-tracking 钩子，riscv 已 GENERIC_ENTRY），**无需任何 arch 代码**。
- **落点**：无功能落点。若要翻绿矩阵，可在 `arch/riscv/Kconfig` 加 cosmetic `select HAVE_VIRT_CPU_ACCOUNTING_GEN`（注：arm64/x86 自己都没这行，靠 64BIT 默认；riscv 加了反而更显式）。
- **判定**：**ALREADY**。证据：`arch/Kconfig:1056` + riscv 三项依赖齐全 + GEN 纯通用实现。矩阵 TODO 系检测口径假阳。**建议从候选剔除。**

### 3. kprobes-on-ftrace（HAVE_KPROBES_ON_FTRACE）— PATTERN，中-重
- **候选**：`debug/kprobes-on-ftrace`（riscv=TODO，x86/csky/loongarch/parisc/powerpc/s390=ok，**arm64=TODO**）。
- **现状**：
  - **关键前置**：`KPROBES_ON_FTRACE`（`arch/Kconfig:173-176`）`def_bool y; depends on KPROBES && HAVE_KPROBES_ON_FTRACE && DYNAMIC_FTRACE_WITH_REGS`。
  - riscv 走现代 **WITH_ARGS/CALL_OPS** 路（`arch/riscv/Kconfig:162-163`），**无 `DYNAMIC_FTRACE_WITH_REGS`** → 即便 select `HAVE_KPROBES_ON_FTRACE` 也不会开。**arm64 同理**（只 WITH_ARGS，`arch/arm64/Kconfig:186`，故 arm64 也 TODO）。对照：x86 `WITH_REGS`:228、loongarch `WITH_REGS`:143（+WITH_ARGS:140）→ 二者 ok。
  - riscv `arch/riscv/kernel/probes/` 有 kprobes.c/uprobes.c/rethook，**无 `ftrace.c`、无 `kprobe_ftrace_handler`**。
- **落点**：二选一前置 +（新）`arch/riscv/kernel/probes/ftrace.c`（`kprobe_ftrace_handler`+`arch_prepare_kprobe_ftrace`）+ select：
  - 路 A（仿 loongarch）：给 riscv 加 `HAVE_DYNAMIC_FTRACE_WITH_REGS`（重：ftrace 桩需存全量 pt_regs，削弱 CALL_OPS 效率）。
  - 路 B（通用改造）：推动通用 `KPROBES_ON_FTRACE` 支持 WITH_ARGS（跨架构改动，非 riscv 本地）。
  - 参照：`arch/x86/kernel/kprobes/ftrace.c`、loongarch probes/ftrace 实现。
- **判定**：**PATTERN**（中-重，价值中）。有真实前置门槛（WITH_REGS），非"补个 ftrace.c"；与 arm64 同结构性卡点。

### 补充（次要，简述）

**4. optprobes（HAVE_OPTPROBES）— PATTERN，低价值**
- 现状：riscv 无 `opt.c` / `arch_prepare_optimized_kprobe`；x86/arm/powerpc=ok，**arm64=TODO**。
- 障碍：RV 定长指令 + 跳转范围受限（`JAL` ±1MB；全范围需 `AUIPC+JALR` 两指令，**单点无法原子改写**为跳转），与 arm64 未做同因。
- 落点：新增 `arch/riscv/kernel/probes/opt.c` + `select HAVE_OPTPROBES`；参照 `arch/powerpc/kernel/optprobes.c`（RISC 风格）/ `arch/x86/kernel/kprobes/opt.c`。低优先。

**5. user-ret-profiler（HAVE_USER_RETURN_NOTIFIER）— N-A**
- 仅 x86=ok。通用基建存在（`kernel/user-return-notifier.c`、`kernel/fork.c` 初始化），但**唯一实义消费者是 `arch/x86/kvm/x86.c`**（返回用户态时懒恢复 guest MSR），`arch/x86/include/asm/entry-common.h` 触发。riscv KVM 无此 MSR 懒恢复语义、无消费者 → 补了是死代码。**N-A**（x86-KVM 专属基建）。

**6. cBPF-JIT（HAVE_CBPF_JIT）— N-A，建议剔除**
- x86=TODO、arm64=TODO，仅 mips/powerpc/sparc=ok（遗留）。现代内核 cBPF 经 `bpf_migrate_filter` 转 eBPF，由 eBPF JIT 编译；riscv 已 `select HAVE_EBPF_JIT if MMU`（`arch/riscv/Kconfig:168`）。classic-BPF JIT 属废弃技术，三大主力 arch 一致不做。**N-A**，价值最低，建议从候选清单剔除。

## 全量判定表

| 候选 | 来源(features) | 判定 | 缺口性质 / riscv 落点 | 备注(arm64/x86 状态 / 假阳说明) |
|---|---|---|---|---|
| cmpxchg-local | locking/cmpxchg-local | **PATTERN** | 底层 `arch_cmpxchg_local` 已具备(cmpxchg.h:288)；缺 arch percpu 层 → 新增 `arch/riscv/include/asm/percpu.h`(仿 arm64 percpu.h:235) + `select HAVE_CMPXCHG_LOCAL`(Kconfig H段) | arm64:181/x86:218/s390:198 都 select；与 §2a 互证；唯一消费者 mm/vmstat.c:547；纯 select 无 percpu 层不划算 |
| virt-cpuacct | time/virt-cpuacct | **ALREADY** | 无功能落点；riscv64 经 `default y if 64BIT`(arch/Kconfig:1056)已得 GEN，依赖(ctx-tracking:156/clockevents/GEN)全满足，GEN 实现纯通用 | arm64/x86 及 11 家 ok 但**三家 arch 目录均无该串**→纯历史粘滞；riscv TODO 系检测假阳；**建议剔除** |
| kprobes-on-ftrace | debug/kprobes-on-ftrace | **PATTERN**(中-重) | 前置卡点：`KPROBES_ON_FTRACE depends on DYNAMIC_FTRACE_WITH_REGS`(arch/Kconfig:176)，riscv 只 WITH_ARGS/CALL_OPS(Kconfig:162-163)；需加 WITH_REGS 或通用改 WITH_ARGS + 新 `arch/riscv/kernel/probes/ftrace.c` | **arm64=TODO 同因**(只 WITH_ARGS,186)；x86(WITH_REGS:228)/loongarch(WITH_REGS:143)=ok 为参照 |
| optprobes | debug/optprobes | **PATTERN**(低) | 新增 `arch/riscv/kernel/probes/opt.c` + `select HAVE_OPTPROBES`；参照 powerpc/x86 opt | **arm64=TODO 同因**；RV 定长指令+跳转范围/原子改写受限；低优先 |
| user-ret-profiler | debug/user-ret-profiler | **N-A** | 无 riscv 消费者(唯一消费者 arch/x86/kvm/x86.c 的 MSR 懒恢复) | 仅 x86 ok；通用基建 kernel/user-return-notifier.c 存在但 riscv 无对应语义 |
| cBPF-JIT | core/cBPF-JIT | **N-A** | 遗留技术，已被 cBPF→eBPF + eBPF JIT 取代；riscv 已 `HAVE_EBPF_JIT`(Kconfig:168) | x86/arm64 亦 TODO；仅 mips/powerpc/sparc ok；**建议剔除** |

## 交叉给主代理/其它路的提示

- **检测口径假阳是全局风险**：本批已证 arch-support.txt 的 `ok/TODO` 由 `arch/<arch>/Kconfig*` 子串 grep + 粘滞状态生成，**看不到 `arch/Kconfig` 的 `default y if 64BIT` 与通用 select**。§2 Kconfig 路判定时务必同样穿透（与 `_baseline_riscv.md §四` PARAVIRT 式假阳同源）。
- **cmpxchg-local 与 §2a `HAVE_CMPXCHG_LOCAL` 是同一符号**，可合并为一条贡献点（本文落点更细）。
- 本批净贡献候选：**cmpxchg-local(强) > kprobes-on-ftrace(中) > optprobes(低)**；virt-cpuacct/cBPF-JIT 建议剔除；user-ret-profiler N-A。
