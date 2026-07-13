# misc-arch (shard 1) 可移植性分析（linux-arm-kernel → RISC-V）

> 输入：`data/by_category/misc-arch.0.jsonl`（202 条系列）。类别 = arm64/ARM 架构杂项 catch-all。
> 判定依据：`_baseline_riscv.md` + 本地内核树 `/Users/zq/Desktop/patch-work/linux-riscv`（v7.2.0-rc3）Grep 核对。

## 摘要

- **系列总数：202**
- 四态计数：
  - **PORTABLE：9**（通用层/跨架构，含已带 riscv 补丁的系列）
  - **PATTERN：14**（arch 机制可复用，需在 arch/riscv 重写；给出落点）
  - **ALREADY：9**（riscv 已有等价能力，本地源码为证）
  - **N-A：170**（ARM 专属 HW/ISA：KVM/pKVM/CCA/FF-A/GIC/errata、arm 板级平台、defconfig 等）

- **本类 Top 候选（按价值排序）：**
  1. **#18 futex runtime-const**（跨架构，**系列内已含 riscv 补丁** `runtime_const_mask_32()`）→ `arch/riscv/include/asm/runtime-const.h`
  2. **#198 module: force sh_addr=0**（通用 module loader，**系列内含 riscv 补丁 4/4**）→ `arch/riscv/include/asm/module.lds.h`
  3. **#189 arm64/crash: crash hotplug**（riscv 有 crash_dump 但**无 hotplug**，确认缺口）→ `arch/riscv/kernel/crash.c`(新) + `Kconfig` + `asm/kexec.h`
  4. **#159/#165/#166 irqflags `__always_inline`**（riscv 用普通 `static inline`，直接适用）→ `arch/riscv/include/asm/irqflags.h`
  5. **#95(+#50/#14) arm64 tlbflush 单-CPU 免广播**（riscv 有 mm_cpumask 但无 active_cpu 快路径）→ `arch/riscv/mm/tlbflush.c` + `asm/mmu.h`
  6. **#158 uaccess `copy_*_user_partial`/scoped**（通用 uaccess 框架）→ `arch/riscv/include/asm/uaccess.h`
  7. **#183 arm64 pi: validate bootargs**（riscv 有等价 pi 早期码）→ `arch/riscv/kernel/pi/cmdline_early.c`

---

## Top 可移植候选（深度，已 curl 核对 diff + Grep 核对落点）

### 1. #18 futex: Use runtime constants for futex_hash computation — **PORTABLE + PATTERN**
- **原补丁**：`futex: Use runtime constants for futex_hash computation`（v5，8 patches）
  (https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260630045531.3939-2-kprateek.nayak@amd.com/) 状态=new
- **可移植点**：patch 1/8 引入 `runtime_const_mask_32()`（优化掩码运算），futex 核心（`kernel/futex/`）改用 runtime-const 计算 hash。**该系列本身已含 x86/arm64/riscv/s390 各自的 arch 补丁**（patch 4/5 = riscv：`Replace open-coded placeholder with RUNTIME_MAGIC` + `Introduce runtime_const_mask_32()`）。
- **riscv 落点**：`arch/riscv/include/asm/runtime-const.h`。Grep 证实：该文件现有 `runtime_const_ptr` / `runtime_const_shift_right_32`，**缺 `runtime_const_mask_32`**（正是本系列补的）。
- **判定**：PORTABLE（futex 核心通用）+ PATTERN（riscv runtime-const 增量，已在系列内作者化）。**最高价值**——直接落地即可。

### 2. #198 module: force sh_addr=0 for arch-specific sections — **PORTABLE + PATTERN**
- **原补丁**：`module: force sh_addr=0 for arch-specific sections`（4 patches）
  (https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260327080023.861105-2-petr.pavlu@suse.com/) 状态=new
- **可移植点**：修复 module loader 对 arch 专属节（PLT/alternatives）的 `sh_addr` 处理——通过链接脚本 `.plt 0 : { BYTE(0) }` 强制 `sh_addr=0`，避免 kallsyms/GDB 误读。**patch 4/4 = riscv**（`module, riscv: force sh_addr=0`）。
- **riscv 落点**：`arch/riscv/include/asm/module.lds.h`。Grep 证实 `arch/riscv/kernel/module.c:901-903` 用 `.alternative` 节的 `s->sh_addr`——正是需 sh_addr=0 归零的 arch 节。
- **判定**：PORTABLE（core 通用）+ PATTERN（riscv module.lds.h 落点明确，系列内已含）。

### 3. #189 arm64/crash: Add crash hotplug support — **PATTERN（强，真缺口）**
- **原补丁**：`arm64/crash: Add crash hotplug support`（1 patch）
  (https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260402081459.635022-1-ruanjinjie@huawei.com/) 状态=new
- **可移植点**：新增 `ARCH_SUPPORTS_CRASH_HOTPLUG` + arch 钩子 `arch_crash_handle_hotplug_event()` / `arch_crash_hotplug_support()` / `arch_crash_get_elfcorehdr_size()` + `update_crash_elfcorehdr()`——CPU/内存热插拔时重建 elfcorehdr。通用 CRASH_HOTPLUG 基建在 `kernel/`（x86 早已支持）。
- **riscv 落点**：新增 `arch/riscv/kernel/crash.c` + `arch/riscv/Kconfig`（select `ARCH_SUPPORTS_CRASH_HOTPLUG`）+ `arch/riscv/include/asm/kexec.h`。Grep 证实 riscv 有 `crash_dump.c` 与 `ARCH_SUPPORTS_CRASH_DUMP`，但**无任何 `CRASH_HOTPLUG`/`arch_crash_*`**——确认缺口。
- **判定**：PATTERN。riscv kexec/crash 已对等 arm64，唯独缺 hotplug；机制可直接照搬 arm64/x86。

### 4. #159 / #165 / #166 arm64/irqflags & daifflags `__always_inline` — **PATTERN（强）**
- **原补丁**：`arm64/irqflags: __always_inline the arch_local_irq_*()`（v2, #165）
  (https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260421-arm64_always_inline-v2-1-c59d1400514d@debian.org/)；
  伴 `arm64/daifflags: Make local_daif_*() __always_inline`（#159）、RFC 前身（#166）。状态=new
- **可移植点**：将 irq flag 访问器强制 `__always_inline`——避免 `noinstr`/KCOV/编译器不内联导致的 objtool/noinstr 违规。属编译正确性硬化，思想跨架构。
- **riscv 落点**：`arch/riscv/include/asm/irqflags.h`。Grep 证实 riscv 的 `arch_local_irq_enable/disable/save/restore` 等**全部用普通 `static inline`（非 `__always_inline`）**——同样面临 noinstr 隐患，改动直接适用。
- **判定**：PATTERN。三条同质（合并为一个改动方向）。

### 5. #95(+#50/#14) arm64 tlbflush: 单-CPU 免广播 — **PATTERN**
- **原补丁**：`arm64: tlbflush: Don't broadcast if mm was only active on local cpu`（v2, #95）
  (https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260523134710.3827956-1-linu.cherian@arm.com/)；
  伴 `Reset active_cpu on ASID rollover`（#50）、`debug counters for local vs broadcast`（#14）。状态=new
- **可移植点**：`mm_context_t` 增 `active_cpu` 字段（哨兵 `ACTIVE_CPU_NONE`/`ACTIVE_CPU_MULTIPLE`/单 CPU id）；mm 仅在本 CPU 活跃时退回纯本地 TLB flush，跳过硬件广播（DVM/TLBI-IS）。
- **riscv 落点**：`arch/riscv/mm/tlbflush.c` + `arch/riscv/include/asm/mmu.h`。Grep 证实 riscv `__flush_tlb_range` 已传 `mm_cpumask(mm)` 并分派 local / SBI rfence / IPI——**已有比 arm64 更细粒度的 cpumask 定向**（部分等价），但仍可加"仅本地 CPU→免 SBI/IPI"的单-CPU 快路径 + 溢出计数器（#14）。
- **判定**：PATTERN（riscv 部分能力已具备，属增量优化；落点明确）。

### 6. #158 uaccess: copy_*_user_partial / scoped user access — **PORTABLE**
- **原补丁**：`uaccess: Convert small fixed size copy_{to/from}_user() to scoped user access`（RFC v1, 9 patches）
  (https://patchwork.kernel.org/project/linux-arm-kernel/patch/0ee46bb228d97163fbdc14f2a7c52b93d8bc34ce.1777306795.git.chleroy@kernel.org/) 状态=new
- **可移植点**：通用 uaccess 框架改造——`INLINE_COPY_*` 转 Kconfig、引入 `copy_{to/from}_user_partial()`、`unsafe_copy_from_user()`、改 copy 返回语义。核心在 `include/linux/uaccess.h` / `lib/usercopy.c`。
- **riscv 落点**：`arch/riscv/include/asm/uaccess.h`（riscv 已有 `unsafe_get_user`/`unsafe_put_user` asm-goto，可对接新 scoped 接口）。
- **判定**：PORTABLE（通用框架，各 arch 随通用改造受益/需少量 arch 钩子）。RFC 阶段，语义未定，观望。

### 7. #183 arm64: pi: validate bootargs before parsing them — **PATTERN**
- **原补丁**：`arm64: pi: validate bootargs before parsing them`（1 patch）
  (https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260403143004.4-arm64-pi-bootargs-pengpeng@iscas.ac.cn/) 状态=new
- **可移植点**：位置无关早期码（KASLR 前）解析 bootargs 前做长度/边界校验，防越界。
- **riscv 落点**：`arch/riscv/kernel/pi/cmdline_early.c`（Grep 证实存在；riscv pi 早期码同样解析 cmdline 取 KASLR 种子）。
- **判定**：PATTERN。作者 pengpeng@iscas.ac.cn（ISCAS，做 riscv），同类 DT/cmdline 硬化很可能已/将投 riscv。

---

## 其余 PORTABLE / PATTERN / ALREADY（逐条）

### PORTABLE（除上文）
| # | 系列 | 可移植点 | riscv 落点 | web_url |
|---|---|---|---|---|
| 47 | init: discoverable root partitions | 可省略 `root=` 的 DPS 发现（init/ 通用）+ 每-arch 根分区 GUID | `init/do_mounts` 通用；riscv 需定义自身 DPS GUID | .../20260615-discoverable-root_partitions-v1-4-...@kernel.org/ |
| 88 | tracing: Fix bpf_get_stackid -EFAULT on ARM64 | bpf 栈采样 -EFAULT 修复（栈回溯/bpf core） | `kernel/bpf` 或 arch stacktrace（待核） | .../20260526192012.76223-1-gyokhan@amazon.de/ |
| 110 | Bump minimum LLVM to 17.0.1 | 树级最低编译器版本 + 去除过时 ld.lld 条件 | riscv 亦有扩展相关 min-version 门槛 | .../20260517-bump-minimum-supported-llvm-version...@kernel.org/ |
| 123 | perf record: Refactor ARM64 leaf caller out of arch | 把 arm64 leaf-caller 采集下沉为通用（tools/perf） | `tools/perf/util/*`（利好 riscv perf） | .../20260512054140.3427725-1-irogers@google.com/ |
| 175 | treewide: Cleanup LATCH/CLOCK_TICK_RATE/get_cycles | 移除 `CLOCK_TICK_RATE`、清理 `get_cycles()` 误用、delay 校准重构 | `kernel/time`、`calibrate`；riscv `get_cycles`/timer 触点 | .../20260410120318.045532623@kernel.org/ |
| 200 | srcu: Optimize SRCU-fast per-CPU counter increments | SRCU-fast 每-CPU 计数增量优化（core，arm64 首用） | `kernel/rcu/srcutree.c` 通用；riscv per-cpu 亦受益 | .../20260326102608.1855088-1-puranjay@kernel.org/ |

### PATTERN（除上文；含弱候选，诚实标注）
| # | 系列 | 可移植点 | riscv 落点 | 强度 |
|---|---|---|---|---|
| 83 | rust: arm64: set uwtable llvm module flag | `CONFIG_UNWIND_TABLES` 时置 Rust uwtable 标志 | `arch/riscv/Makefile` / rust 配置（riscv 有 Rust） | 中 |
| 40 | ARM: smp: separate IPI labels from counters | `/proc/interrupts` IPI 标签与计数分离 | `arch/riscv/kernel/smp.c`（show_ipi_list） | 弱(外观) |
| 154 | arm64: fix KERNEL_SEGMENT_COUNT error | kexec 段计数上限修复 | `arch/riscv/kernel/machine_kexec*.c`（需核语境） | 弱 |
| 164 | arm64: smp: Limit nr_cpu_ids under nosmp | nosmp 时收敛 nr_cpu_ids | `arch/riscv/kernel/smp.c` | 弱 |
| 19/23 | ARM: enable interrupts on user fault / notify_die | 处理用户态错误时开中断降延迟 | `arch/riscv/mm/fault.c`、`kernel/traps.c`（riscv 或已部分具备） | 弱 |

### ALREADY（riscv 已有等价，本地源码为证）
| # | 系列 | riscv 现状（证据） |
|---|---|---|
| 101/124 | arm/arm64: Implement `_THIS_IP_` using inline asm | riscv **已用** inline asm：`asm/linkage.h:12` `_THIS_IP_ ... "auipc %0, 0"` |
| 169 | arm: race on PG_dcache_clean in __sync_icache_dcache | riscv **已用安全序**：`mm/cacheflush.c:104-106` `if(!test_bit){ flush; set_bit; }`（先刷后置，无竞态） |
| 199 | arm64: panic if IRQ handler stacks can't be allocated | riscv **已 panic**：`kernel/irq.c:105` "Failed to allocate IRQ stack resources"、:89 影子栈 |
| 33/34 | ARM: `__ASSEMBLY__` → `__ASSEMBLER__` | riscv 头文件 **零** `__ASSEMBLY__` 出现（已迁移） |
| 114 | ARM64: remove arch-specific `<asm/device.h>` | riscv **无** 自定义 `asm/device.h`（已用 asm-generic） |
| 87 | arm64: Kconfig: remove replaced HAVE_FUNCTION_GRAPH_RETVAL | riscv Kconfig 不 select 该过时符号（select `HAVE_FUNCTION_GRAPH_FREGS`） |
| 191 | lib/crc: arm64: Assume little-endian | riscv 天然 LE-only，crc 无 BE 分支可去 |

---

## 全量判定表（N-A 同质合并成组；非-N-A 已在上文逐条）

| 组 / 系列 | 数量 | 判定 | 说明 | 代表 web_url |
|---|---|---|---|---|
| **KVM: arm64**（pKVM/nVHE hyp、NV 嵌套虚拟化、stage-2 walker、ESR/SError 注入、SMC/FF-A、ZCR/SVE、cache config、guest_memfd、hyp trace）| ~55 | N-A | 依赖 EL2/hyp、GIC-vLPI、SVE、FF-A/SMCCC 固件 ABI；KVM 深挖不在本研究范围。generic KVM 核心(guest_memfd/dirty-log)另有 tierA 桶覆盖 | #4,5,6,7,8,15,17,24,27,29,31,35–37,39,42–44,48,51,52,60,64,65,68–74,79,80,82,99,100,102,103,106,116,118,145–147,151,153,168,170,177,179,190,192,194,201,202 |
| **ARM CCA / 机密计算**（RME/RMM/RSI/TSM/TDISP 测量寄存器）| 3 | N-A | = ARM 机密计算，riscv 对应为 CoVE(AP-TEE)，ABI 不同 | #121,#160,#171 |
| **ARM OF-node / device_node refcount 泄漏修复** | ~19 | N-A | of_node_put 卫生模式虽通用，但实例均在 arm mach/平台驱动（tegra/imx/mvebu/omap/mstar/npcm/highbank/socfpga…） | #11,30,45,46,56–58,62,63,67,85,90–93,119,120,148,149 |
| **ARM defconfig / Kconfig 配置** | ~18 | N-A | arm 板级配置启停符号（SND_ALOOP/dma-buf/EXT4/gpiolib/多 v7 清理…） | #1,3,10,16,25,26,41,54,77,86,152,155–157,172,173,176,195 |
| **ARM 遗留平台清理 / 头文件迁移 / mach**（footbridge/riscpc/sa1100/pxa/omap/imx/shmobile、sparse-IRQ 转换、header move、死代码删除、warning/hardening 修复）| ~55 | N-A | arm32 厂商平台内部；无 riscv 对应 | #21,22,28,49,53,55,59,61,66,75,76,78,84,94,96–98,104,107–109,111–113,115,117,122,125–144,150,161–163,167,178,180–188,193,196,197 |
| **arm64 errata**（CNP/HIP09、REPEAT_TLBI、C1-Pro 4193714）| 4 | N-A | arm64 特定芯片勘误；riscv 用四厂商 errata 框架，机制不通用 | #20,81,89,145 |
| **其它 arch / 杂项**（mips #142、x86 #174、Hyper-V-arm64 MSHV_VTL #163、resctrl/MPAM #2、arm64 uapi __u128 #32〔riscv uapi 无 __uint128_t〕、arm64 futex-LSUI #105、MAINTAINERS #38、arm dma-mapping #21、arm kasan cleanup #22）| ~9 | N-A | 非 arm/riscv，或依赖 ARM 专属 ISA/子系统；riscv 无对应或已不受影响 | #2,32,38,105,142,163,174 |

> N-A 合计 ≈ 170；上表分组之并集覆盖除「非-N-A 32 条」外的全部输入系列。个别系列跨组（如 #15/#70 dirty-log、#2 resctrl）已就近归入，不重复计数。

---

## 结论要点
- **真候选集中在跨架构/通用系列**：#18(futex runtime-const) 与 #198(module sh_addr) **系列内已带 riscv 补丁**，落地风险最低；#189(crash hotplug)、#159/165/166(irqflags __always_inline)、#95(tlbflush 免广播)、#158(uaccess partial)、#183(pi bootargs 校验) 为需在 arch/riscv 重写的 PATTERN，落点已 Grep 证实。
- **纪律校正**：`_THIS_IP_`(#101/124)、PG_dcache_clean 竞态(#169)、IRQ 栈 panic(#199)、`__ASSEMBLER__` 迁移(#33/34)、`asm/device.h` 精简(#114) —— riscv **均已具备/已正确**，判 ALREADY，未误报为可移植。
- **绝大多数(170/202) 为 N-A**：KVM:arm64（pKVM/NV/CCA/FF-A）与 arm32 厂商平台/defconfig 占比最高，符合 catch-all 桶预期。
