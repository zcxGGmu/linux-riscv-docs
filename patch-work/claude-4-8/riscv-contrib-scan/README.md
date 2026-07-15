# RISC-V 贡献点候选扫描 —— 三路静态信号的深度甄别（第三轮）

> 源码树：`/Users/zq/Desktop/patch-work/linux-riscv`（Linux v7.2.0-rc3，只读）。
> 与 `../riscv-arm-gap/`（补丁邮件列表差异挖掘）**互补**：本轮从内核树**静态信号**（官方特性矩阵 / Kconfig 能力差集 / 代码内 TODO）出发，找**当前树的真实缺口**。
> `scripts/scan.py` 产出**原始候选**（可 `python3 scripts/scan.py` 复现）；本文是对其**逐条穿透核实后的四态判定**，逐条证据见 `analysis/*.md`。

## TL;DR

- 三路原始候选约 **307** 项（§1 官方矩阵 6 + §2a 强信号 46 + §2b 次强 201 + §3 代码 TODO 54，另 2 DTS）。逐条到只读内核树核实后，**高假阳 / 高噪声是主基调**：
  - **§1「官方矩阵」也有假阳**：`virt-cpuacct` 其实 ALREADY（`arch-support.txt` 由 `features-refresh.sh` 仅 grep `arch/<arch>/Kconfig*` + 状态粘滞，看不到 `arch/Kconfig` 的 `default y if 64BIT`）。
  - **§2「只看 select」漏传递**：`PARAVIRT`、`GENERIC_IRQ_ENTRY`、`EXECMEM`、`NEED_DMA_MAP_STATE` 等其实 ALREADY（经 `config`/`def_bool`/传递 select 获得）；§2b 另有 ~11 例同类假阳（`VMAP_STACK`/`JUMP_LABEL`/`PERF_EVENTS`/`PTDUMP`…）。
  - **§3 真缺口:噪声 ≈ 1:7.7**：54 处里仅 6 处真 PATTERN（仅 3 有实际价值），其余是正常运行时分支 / UAPI 常量 / 能力日志；且初判的 2 处「真缺口」经逐行核实**证伪降级 N-A**。
- **净高价值贡献点约 12 个**，**旗舰 4 个**：`HAVE_STATIC_CALL`、`cmpxchg-local`、`HAVE_HW_BREAKPOINT`、`reliable_stacktrace → livepatch` 链。
- **最强单点**：`HAVE_STATIC_CALL`（PATTERN）——text-patch 基座已全备（`jump_label.c` 已在原子改写 JAL/NOP），只差 `static_call.h`+trampoline，**性价比最高**。
- **用户可见硬缺口**：`HAVE_HW_BREAKPOINT`（PATTERN）——gdb 硬件断点/观察点当前**完全不可用**。
- **最大工程（gated）**：NMI 簇（5 符号，须 AIA IPRIO 阈值伪 NMI，相互依赖）；但硬锁检测经 buddy detector **今日已可用**，perf-NMI 属精度增量而非从零。
- **设备直通闭环**：`IOMMU Second-Stage` + `KVM AIA IMSIC↔IOMMU 映射`（§3，与 `kvm-riscv` 轮深度重叠，建议并为「AIA+IOMMU 直通」簇）。

## 1. 方法论

- **数据源**：内核树静态扫描（`scan.py` 三路信号），非补丁邮件。与 `riscv-arm-gap` 的在途补丁挖掘互补。
- **四态 rubric**：**ALREADY**（已实现/假阳）/ **PORTABLE**（可 select 或补通用钩子）/ **PATTERN**（需在 `arch/riscv/*` 实现，给落点）/ **N-A**（无对应 HW/ISA 或不需要）。详见 `analysis/_taxonomy.md`、基线 `analysis/_baseline_riscv.md`。
- **核心纪律——穿透 scan 口径**（本轮增值所在）：三路的原始信号都会因**检测口径**产生系统性假阳/噪声，故每条候选均**逐条 grep + Read 核实**：
  1. §1：`arch-support.txt` 的 ok/TODO 由 `tools/docs/features-refresh.sh` 朴素子串 grep（仅 `arch/<arch>/Kconfig*`）+ **状态粘滞**生成 → 看不到通用 `default y`/传递 select，`ok`≠现在真的 select。
  2. §2：`scan.py` 只比对 `arch/<arch>/Kconfig*` 的 `select` 行 → 漏掉 `config`/`def_bool`/**传递 select**（`GENERIC_ENTRY→GENERIC_IRQ_ENTRY` 即典型）。
  3. §3：正则命中大量正常运行时分支、UAPI `*_UNSUPPORTED` 常量、`pr_warn/err` 日志，非待办。

## 2. 三路总览（甄别后四态计数，子代理自报近似值）

| 路 | 原始候选 | ALREADY/假阳 | PORTABLE | PATTERN | N-A/噪声 | 明细 |
|---|---|---|---|---|---|---|
| §1 官方矩阵 | 6 | 1 | 0 | 3 | 2 | `analysis/feat_official.md` |
| §2a 强信号 | 46 | 2 | 12* | 18* | 14 | `analysis/kconfig_trace_nmi.md`（跟踪/NMI 11）+ `analysis/kconfig_sched_mm_rest.md`（其余 35）|
| §2b 次强 | 201 | ~11 | ~4 | ~18 | ~168 | `analysis/kconfig_sched_mm_rest.md` §2b |
| §3 代码 TODO | 54(+2 DTS) | 0 | 0 | 6 | 50 | `analysis/code_todo.md` |

> \* §2a 的 `HAVE_CMPXCHG_LOCAL` 被 kconfig 子代理记为 PORTABLE（仅指能力位一行 select），但完整方案须新增 `arch/riscv/include/asm/percpu.h`，本文与 §1 `cmpxchg-local` 合并计为 **PATTERN**（见 §4）。计数为近似口径，权威以各 `analysis/*.md` 全量表为准。

## 3. arm64/x86 机制 ↔ RISC-V 落点 速查（精选）

| 对端机制/符号 | RISC-V 落点 | 判定倾向 |
|---|---|---|
| `HAVE_STATIC_CALL` | 新增 `arch/riscv/include/asm/static_call.h` + `kernel/static_call.c`（复用 `patch.c`/`jump_label.c` 原语）| PATTERN |
| `cmpxchg-local`(=HAVE_CMPXCHG_LOCAL) | 新增 `arch/riscv/include/asm/percpu.h`（仿 arm64 `_pcp_protect`）+ `select` | PATTERN |
| `HAVE_HW_BREAKPOINT` | 新增 `arch/riscv/kernel/hw_breakpoint.c` + Sdtrig/SBI-DBTR + ptrace regset | PATTERN |
| `HAVE_RELIABLE_STACKTRACE`→`HAVE_LIVEPATCH` | `arch/riscv/kernel/stacktrace.c` 补 `arch_stack_walk_reliable()` + `select HAVE_LIVEPATCH` | PATTERN→PORTABLE |
| NMI 簇（真 NMI）| AIA IPRIO 阈值伪 NMI：`asm/irqflags.h` + `irq-riscv-imsic-*` + entry | PATTERN(gated AIA) |
| `HAVE_ARCH_KCSAN` | `select HAVE_ARCH_KCSAN` + 低层文件 `KCSAN_SANITIZE:=n` | PORTABLE |
| SCHED_SMT/CLUSTER | `select`（`arch_topology` 已解析 cluster/thread）+ SMT 掩码接线 | PORTABLE |
| IOMMU Second-Stage / IMSIC↔IOMMU | `drivers/iommu/riscv/iommu.c` + `arch/riscv/kvm/aia_imsic.c` | PATTERN(HW 专属) |
| pkeys / resctrl / NONLEAF_PMD_YOUNG / 机密计算 | —（无 ISA/HW；CoVE 在途）| N-A |

## 4. Top 候选（分级，按价值×可行性）

### P1 — 旗舰（高价值、落点明确、可行）

| 候选 | 缺口性质 | RISC-V 落点 | 判定 | 来源 |
|---|---|---|---|---|
| **`HAVE_STATIC_CALL`** | 无 `static_call.h`；但 text-patch 基座已全（`jump_label.c` 已 patch JAL/NOP）| 新增 `asm/static_call.h`（out-of-line trampoline）+ `kernel/static_call.c`；`select` | **PATTERN** | §2a Kconfig `arch/Kconfig:1691` |
| **`cmpxchg-local`** | `arch_cmpxchg_local` 已具（`cmpxchg.h:288`），但无 `asm/percpu.h`→`this_cpu_cmpxchg` 走 irq-save | 新增 `asm/percpu.h`（仿 arm64 `percpu.h:235`）+ `select HAVE_CMPXCHG_LOCAL`；消费者 `mm/vmstat.c:547` | **PATTERN** | §1 `locking/cmpxchg-local` + §2a `HAVE_CMPXCHG_LOCAL`（同符号）|
| **`HAVE_HW_BREAKPOINT`** | 无 hw_breakpoint.c、ptrace 无 HW_BREAK regset、无 Sdtrig 接入（**gdb 硬件断点当前不可用**）| 新增 `kernel/hw_breakpoint.c` + Sdtrig/SBI-DBTR CSR + ptrace regset | **PATTERN** | §2a `arch/Kconfig:445` |
| **`reliable_stacktrace`→`livepatch`** | 无 `arch_stack_walk_reliable()`；ftrace WITH_ARGS/CALL_OPS/DIRECT 已全 | `stacktrace.c` 补可靠性判定（复用 FP unwinder + 异常帧）→ 再 `select HAVE_LIVEPATCH` | **PATTERN→PORTABLE** | §2a `arch/Kconfig:1418` + `livepatch/Kconfig:2` |

### P2 — 高价值

| 候选 | 缺口性质 | RISC-V 落点 | 判定 | 来源 |
|---|---|---|---|---|
| **AIA+IOMMU 直通簇** | IOMMU G-stage 未合 + IMSIC↔IOMMU MSI 重映射未接线（设备直通/IRQ bypass 闭环）| `drivers/iommu/riscv/iommu.c:1149` + `arch/riscv/kvm/aia_imsic.c:773,864` | **PATTERN** | §3 代码 TODO（与 kvm 轮重叠）|
| **`HAVE_ARCH_KCSAN`** | 无 KCSAN（仅 generic+KFENCE）；通用 sanitizer | `select` + 低层 `KCSAN_SANITIZE:=n` + noinstr 审计 | **PORTABLE** | §2a `lib/Kconfig.kcsan`（前两轮已判）|
| **SCHED_SMT / SCHED_CLUSTER / HOTPLUG_SMT** | 拓扑底座已就绪（`GENERIC_ARCH_TOPOLOGY`+`SCHED_MC`），差 select+SMT 掩码 | `arch/riscv/Kconfig` + arch_topology 掩码接线 | **PORTABLE**(SMT/HOTPLUG 偏 PATTERN) | §2a `arch/Kconfig:38/44/47` |
| **NMI 簇**（HAVE_NMI/PERF_EVENTS_NMI/HARDLOCKUP_DETECTOR_PERF/TRACE_IRQFLAGS_NMI/NMI_SAFE_THIS_CPU_OPS）| 无真 NMI（`irqflags.h` 清 SIE 全屏蔽）| AIA IPRIO 伪 NMI（对标 arm64 PSEUDO_NMI）| **PATTERN**(gated AIA) | §2a `arch/Kconfig:291…` |

### P3 — 机会/增量（多为一行 select 的能力位，或低优先 PATTERN）

| 候选 | 判定 | 落点/说明 | 来源 |
|---|---|---|---|
| `ARCH_HAS_LAZY_MMU_MODE` / `UACCESS_FLUSHCACHE`(Zicbom) / `HAVE_ARCH_PREL32_RELOCATIONS` | PATTERN | 批 sfence / CBO.flush / R_RISCV_32_PCREL | §2a |
| `ARCH_HAS_EXECMEM_ROX` / `ARCH_HAS_RELR` / `UNWIND_TABLES` / `MMU_GATHER_MERGE_VMAS` | PATTERN/PORTABLE | §2b 漏网通用缺口 | §2b |
| `ARCH_SUPPORTS_MEMORY_FAILURE` / `ARCH_HAS_ZONE_DMA_SET` / `ARCH_WANT_DEFAULT_BPF_JIT` / `CPUMASK_OFFSTACK` / `ACPI_TABLE_UPGRADE` | PORTABLE | 一行 select 能力位（部分需上游 RAS/APEI 才有实效）| §2a |
| `kprobes-on-ftrace`（卡 WITH_REGS，arm64 同因）/ `optprobes` / kprobes REJECTED 模拟 | PATTERN(低) | probes 覆盖率增量 | §1 + §3 |
| `IMSIC Multi-MSI` / PMU 虚拟化协调 / spinlock static_key→alternative | PATTERN(低) | irqchip/kvm/锁 精修（后两与 kvm/static_call 重叠）| §3 |

### 明确剔除 / 已证伪（甄别的严谨性所在）

- **官方矩阵假阳（ALREADY）**：`virt-cpuacct`（riscv64 经 `default y if 64BIT` 已得）；`cBPF-JIT`→N-A（遗留，已有 `HAVE_EBPF_JIT`）；`user-ret-profiler`→N-A（唯一消费者 `arch/x86/kvm/x86.c`）。
- **§2「只看 select」假阳（ALREADY）**：`PARAVIRT`、`GENERIC_IRQ_ENTRY`、`EXECMEM`、`NEED_DMA_MAP_STATE`（传递）；§2b 的 `VMAP_STACK`/`JUMP_LABEL`/`PERF_EVENTS`/`MMU_NOTIFIER`/`DEBUG_FS`/`PTDUMP`/`RTC_LIB`/`IRQ_DOMAIN_HIERARCHY`/`GENERIC_IRQ_CHIP`/`PHYS_ADDR_T_64BIT`/`KMAP_LOCAL`。
- **§3 逐行证伪降级 N-A**：`BPF-JIT 1/2 字节 RMW`（BPF verifier + arm64 均只支持 W/DW，是防御性死代码，「arm64 已支持」不成立）；`perf guest-OS callchain`（x86/arm64 逐字相同 TODO 且同样提前 return，三家都没做）。
- **无对应 HW/ISA → N-A**：`pkeys`(PKU/POE)、`resctrl`(RDT/MPAM)、`ARCH_HAS_NONLEAF_PMD_YOUNG`(无 ARM64_HAFT 等价)、`ARCH_USES_PG_ARCH_2`(MTE)、机密计算三件套(`CC_PLATFORM`/`MEM_ENCRYPT`/`FORCE_DMA_UNENCRYPTED`，CoVE **在途未合**)、`DMA_OPS`(遗留/Xen)。
- **新架构不需要 → N-A**：`HAVE_UID16`/`COMPAT_OLD_SIGACTION`/`OLD_SIGSUSPEND3`(legacy compat)、`HAVE_C_RECORDMCOUNT`(riscv 走 `-fpatchable-function-entry`，recordmcount 是死代码)。

## 5. 三路四态计数汇总

| 判定 | §1 | §2a | §2b(抽样) | §3 | 合计(近似) |
|---|---|---|---|---|---|
| ALREADY/假阳 | 1 | 2 | ~11 | 0 | ~14 |
| PORTABLE | 0 | 12* | ~4 | 0 | ~16 |
| PATTERN | 3 | 18* | ~18 | 6 | ~45 |
| N-A/噪声 | 2 | 14 | ~168 | 50 | ~234 |
| **原始候选** | **6** | **46** | **201** | **54(+2)** | **~309** |

> 净"值得投入"候选（PORTABLE+有价值 PATTERN，去重跨路重叠如 cmpxchg/static_call）约 **12 个**（见 §4 P1/P2 + P3 精选）。

## 6. 结论与贡献路线建议

- **近期低风险（PORTABLE，多为一行 `select` 能力位）**：`HAVE_ARCH_KCSAN`、`SCHED_CLUSTER`、`ARCH_SUPPORTS_MEMORY_FAILURE`、`ARCH_WANT_DEFAULT_BPF_JIT`、`CPUMASK_OFFSTACK`、`ACPI_TABLE_UPGRADE`。⚠️ `cmpxchg-local` 的能力位虽一行 select 即可点亮，但完整收益须带 `percpu.h`（否则 `this_cpu_cmpxchg` 仍 irq-save），故归 PATTERN。
- **中期补 arch 钩子（PATTERN，落点明确）**：**价值链 `static_call → reliable_stacktrace → livepatch`**（三连，基座现成）；`HAVE_HW_BREAKPOINT`（用户可见）；`LAZY_MMU_MODE`/`UACCESS_FLUSHCACHE`(Zicbom)/`EXECMEM_ROX`/`RELR`/`PREL32_RELOCATIONS`。
- **大工程（gated，工程量大/依赖在途特性）**：**NMI 簇**（AIA IPRIO 伪 NMI，5 符号相互依赖；硬锁检测经 buddy 今日已可用，可后置 perf-NMI）；**AIA+IOMMU 直通簇**（IOMMU G-stage + IMSIC↔IOMMU，与 kvm 轮重叠）。
- **明确不追**：无 ISA/HW（pkeys/resctrl/NONLEAF_PMD_YOUNG/PG_ARCH_2/机密计算 CoVE 在途）；不需要（legacy compat/C_RECORDMCOUNT/cBPF-JIT/user-ret-profiler）；已证伪（BPF 1/2 字节 RMW、perf guest callchain）。

## 附录

### A. 原始扫描口径与局限
`scripts/scan.py` 是**朴素静态信号扫描**，三路各有系统性偏差（见 §1 方法论），故其原始 `README` 输出**仅为候选线索**，必须逐条穿透核实——本文 §2/§4 与 `analysis/*.md` 即为核实结果。原始逐符号清单可 `SRC=/Users/zq/Desktop/patch-work/linux-riscv python3 scripts/scan.py` 复现。

### B. 目录结构 / 复现
```
riscv-contrib-scan/
├── README.md                        # 本文（甄别后结论）
├── scripts/scan.py                  # 三路静态扫描器（可复现原始候选）
└── analysis/
    ├── _baseline_riscv.md           # riscv 能力基线 / 真实缺口 / N-A / 假阳清单
    ├── _taxonomy.md                 # 四态 rubric + arm64/x86↔riscv 机制速查
    ├── _agent_instructions.md       # 分析子代理指令模板
    ├── feat_official.md             # §1 官方矩阵 6 项
    ├── kconfig_trace_nmi.md         # §2a 跟踪/调试/NMI 簇 11 符号
    ├── kconfig_sched_mm_rest.md     # §2a 其余 35 + §2b 201 抽样
    └── code_todo.md                 # §3 代码 TODO 56 处
```

### C. 口径说明
- 四态计数为各子代理**自报近似值**（§2b 为抽样估算），权威口径以 `analysis/*.md` 全量判定表为准。
- 每个 PORTABLE/PATTERN 候选均带 riscv 落点文件并已在只读内核树核实存在；每个 ALREADY/假阳均带传递链或源码行号证据。
- 本轮与 `kvm-riscv`（AIA/IOMMU/PMU 虚拟化）、`riscv-arm-gap`（KCSAN/static_call/livepatch/haltpoll/COPY_MC）结论交叉一致。
