# RISC-V vDSO `clock_gettime()` 相比 x86_64 偏慢的原因分析（初版）

> 目标：解释为什么在 AI 算力卡场景下，RISC-V 内核 vDSO + `clock_gettime()` 明显慢于 x86_64，并给出 RISC-V vDSO/时钟路径的可优化点与快速排查清单。  
> 说明：本文基于当前目录中的测试数据与 `/home/zcxggmu/workspace/patch-work/linux` 内核源码做“尽快但不做深挖”的分析，结论偏向可操作性与下一步方向。

## 1. 现象与数据摘录

来自 `riscv-x86对比.jpg`（“比较时间获取方式”）：

- `clock_gettime(CLOCK_MONOTONIC)`
  - x86_64：**2,103,771 calls/sec**
  - RISC-V：**328,056 calls/sec**
  - 差异：**约 6.4×**
- `time.time()`：x86_64 **17,830,207** vs RISC-V **4,539,203**（约 3.9×）
- `time.perf_counter()`：x86_64 **17,736,566** vs RISC-V **4,249,661**（约 4.2×）
- `time.monotonic()`：x86_64 **17,736,566** vs RISC-V **4,407,442**（约 4.1×）

来自 perf 报告：

- RISC-V：`perf_whisper_riscv_openmp_4.txt` 中 `__vdso_clock_gettime` 占比 **13.27%**，同时 `libc.so.6: clock_gettime@@GLIBC_2.27` 仍占 **4.26%**（说明并非所有调用都成功走 vDSO 快路径，或者部分路径回退/二次调用/符号归因导致采样分散）。
- x86_64：`perf_whisper_x86_openmp_4.txt` 中 `__vdso_clock_gettime` 采样占比接近 **0.00%**（说明在该 workload 下它几乎不可见，或被其它热点淹没）。

平台/内核版本（摘自 `硬件平台配置x86 vs risc-v.docx` 中的 `uname -a` 文本）：

- x86_64：Ubuntu 22.04，`6.8.0-90-generic`
- RISC-V：openEuler riscv64，`6.12.56-0.0.0.0.riscv64`

> 注意：两平台 CPU 主频、微架构、内存子系统差异会对 “calls/sec” 有直接影响；但本文重点解释 **RISC-V vDSO 取时路径的额外固定开销**，并指出可优化方向。

## 2. Linux vDSO 取时的代码路径（RISC-V）

在该内核树中，RISC-V vDSO 的 `clock_gettime` 入口非常薄：

- `arch/riscv/kernel/vdso/vgettimeofday.c`：`__vdso_clock_gettime()` 直接调用通用实现 `__cvdso_clock_gettime()`。
- 通用实现位于：`lib/vdso/gettimeofday.c`。

核心流程（简化）：

1. `__vdso_clock_gettime()` → `__cvdso_clock_gettime()`
2. `__cvdso_clock_gettime_common()` 根据 clockid 选择 highres/coarse/raw/aux 分支
3. highres 路径 `do_hres()`：
   - 读取 vvar 中的 `vdso_clock.seq` 做 seqlock 重试
   - 调用 `vdso_get_timestamp()`：
     - 通过 `__arch_get_hw_counter(clock_mode, vd)` 读硬件计数器
     - `vdso_calc_ns()` 做 delta/mult/shift 换算
   - `vdso_set_timespec()` 组装 `timespec`

RISC-V 的 “读硬件计数器” 由 `arch/riscv/include/asm/vdso/gettimeofday.h` 提供：

```c
static __always_inline u64 __arch_get_hw_counter(s32 clock_mode,
						 const struct vdso_time_data *vd)
{
	/*
	 * The purpose of csr_read(CSR_TIME) is to trap the system into
	 * M-mode to obtain the value of CSR_TIME.
	 */
	return csr_read(CSR_TIME);
}
```

也就是说：**RISC-V vDSO 快路径的关键一步是读取 `CSR_TIME`**（`time` CSR）。

## 3. 为什么 RISC-V 的 vDSO `clock_gettime()` 会明显更慢

### 3.1 关键根因：读 `CSR_TIME` 可能触发 trap/模拟路径（固定开销大）

从 `arch/riscv/include/asm/vdso/gettimeofday.h` 的注释可见，该实现假设读取 `CSR_TIME` 需要“trap 到 M-mode”来获取时间值。

这在实践里通常意味着以下几类情况之一（任何一种都会把 vDSO 的优势明显削弱）：

1. **固件/平台把 `rdtime`/`csrr time` 配置成陷入更高特权级**（M-mode 处理后返回），每次读取都要走异常/陷入路径。
2. **虚拟化/仿真环境对 `time` CSR 做了慢路径模拟**（例如某些 hypervisor/模拟器实现里，读 time 不是“纯硬件寄存器读”，而是带锁/计算/VMExit/Trap 的模拟流程）。
3. **计数器访问权限/实现差异**导致 “在用户态可读” 不是一个廉价操作（即便 Linux 在启动时设置了 `SCOUNTEREN` 允许访问，也不代表底层实现的 `time` CSR 读取是常数级的快速硬件路径）。

这类固定开销对 `clock_gettime()` 这种“很短的小函数”是致命的：  
**只要读一次计数器就要陷入/退出，单次耗时就会上升一个数量级**，最终表现为 calls/sec 大幅下降，并且 perf 中 `__vdso_clock_gettime` 变成显著热点（你的 RISC-V perf 结果正是这样）。

### 3.2 次要但常见的放大因素：CPU 主频/功耗策略差异

从 `硬件平台配置x86 vs risc-v.docx` 的截图可见，x86 机器为 Xeon Gold 6530（最高 4GHz），而 RISC-V 平台 `scaling_cur_freq` 输出中大量 CPU 处于较低频点（截图中多次出现 `800000`，并偶尔出现更高频点）。

对于“纯用户态小函数 microbench”（例如 tight-loop 调 `clock_gettime`），主频差异会近似线性影响 calls/sec。  
这解释了为什么：

- `time.*()` 类函数差异约 4×（更接近“主频差异 + 少量额外开销”）
- `clock_gettime(CLOCK_MONOTONIC)` 差异达到 6.4×（更像是在主频差异基础上，叠加了“读计数器 trap/模拟”的额外固定成本）

> 结论：**主频/调频策略解释一部分差异，但不足以解释全部；vDSO 读硬件计数器的实现/代价是更关键的结构性因素。**

### 3.3 RISC-V vDSO 的实现形态差异：跨对象文件调用带来额外开销（小，但可优化）

在 x86_64 上：

- `arch/x86/entry/vdso/vclock_gettime.c` 直接 `#include "../../../../lib/vdso/gettimeofday.c"`
- 这会让编译器在同一个翻译单元内看到通用实现，更容易做 `static inline` 展开、常量传播、去掉不必要的分支/栈帧，尤其在未启用 LTO 的情况下会更有利。

在 RISC-V 上：

- `arch/riscv/kernel/vdso/vgettimeofday.c` 只是一个 thin wrapper，通用实现以单独对象文件方式链接进 vDSO。
- 未启用 LTO 时，跨对象文件的 inlining/去栈帧通常做不到，会多出若干次函数调用开销。

这部分开销通常比 “trap/模拟” 小得多，但在极致 microbench 中仍可能贡献可见比例，属于 **低风险、可尝试的 vDSO 微优化点**。

## 4. 与 x86_64 的本质差异：计数器能力与 vDSO 时钟模式

### 4.1 x86_64：TSC（`rdtsc`）是用户态可直接读取的快计数器

x86 的 `__arch_get_hw_counter()`（`arch/x86/include/asm/vdso/gettimeofday.h`）在 `VDSO_CLOCKMODE_TSC` 下使用 `rdtsc_ordered()` 直接读 TSC，属于常数级极低开销。

只要系统满足 “稳定 TSC/同步/不频繁回退” 等条件，`clock_gettime()` 的核心路径就是：

- 少量内存读取（vvar）
- 一次 `rdtsc`
- 少量整数运算

因此在 perf 中往往不可见（或占比极低）。

### 4.2 RISC-V：当前实现等价于“把时钟源读操作的成本交给平台”

RISC-V 的 `VDSO_CLOCKMODE_ARCHTIMER` 最终落到 `csr_read(CSR_TIME)`。  
如果该读取不是“直接硬件寄存器读”，而是 trap/模拟，那么 vDSO 的核心优势（避免 syscall）会被很大程度抵消。

## 5. RISC-V 内核 vDSO/取时路径的优化点（按收益/风险分级）

> 下面列的是“优化方向”，不要求你现在就深入实现；但每一项都尽量给出内核侧落点与可验证方式。

### 5.1 高收益（前提是平台支持）：让用户态读取 time/cycle 变成真正的“无 trap”硬件路径

目标：让 `__arch_get_hw_counter()` 变成一次廉价指令或一次廉价 MMIO load（理想情况是 CSR 读不 trap）。

建议优先确认：

1. **读 `CSR_TIME` 是否真的会 trap/退出到 M-mode/固件？**
   - 现象侧证：vDSO `clock_gettime` 在 perf 中占比高、calls/sec 低。
   - 需要进一步证据（可作为后续动作，不在本文深挖）：用 `perf`/trace/PMU 统计异常数、或固件侧计数器、或对比 `rdtime` 指令的单次延迟。
2. 若确实 trap：从平台/固件/虚拟化层面解决（例如允许直通 time CSR，或提供更快的时钟读取机制），这通常比在 Linux vDSO 里做微优化更有效。

内核侧相关点：

- RISC-V 内核启动在 `arch/riscv/kernel/head.S` 写了 `CSR_SCOUNTEREN` 以允许访问 time 计数器，但这只解决“权限”，不保证“快”。

### 5.2 中收益：在 vDSO 内减少函数调用与分支（更偏“工程优化”）

方向 A：把通用实现合并编译单元（仿照 x86/s390）

- 当前：`arch/riscv/kernel/vdso/vgettimeofday.c` thin wrapper → 调 `lib/vdso/gettimeofday.c` 中的 `__cvdso_*`
- 建议：像 `arch/x86/entry/vdso/vclock_gettime.c` 那样，直接 `#include "../../../../lib/vdso/gettimeofday.c"`，并在同一文件内提供 RISC-V 的 `__arch_get_hw_counter()` 等接口。
- 预期收益：减少 `__vdso_*` → `__cvdso_*` 的 call/ret/栈帧开销，提升编译器优化空间。
- 风险：低（但要注意 include 方式对符号/编译选项的影响，需跑 vDSO 构建与检查）。

方向 B：确认 RISC-V vDSO 是否启用了不必要的保护/选项

- 例如：某些 toolchain 默认插入的指令序列（间接跳转保护、BTI/PAC 类似机制、或过多 barrier）在 vDSO 热路径上可能放大开销。
- 在本内核树里 vDSO 已显式设置 `-fno-stack-protector`/`-fno-builtin` 等，仍可检查是否存在额外的间接层。

### 5.3 低收益：算法级微调（通常不是瓶颈，但可做“锦上添花”）

在 `lib/vdso/gettimeofday.c` 中：

- `vdso_set_timespec()` 使用 `__iter_div_u64_rem()` 做 `ns / NSEC_PER_SEC`，并有注释说明不要在 seqlock 循环里调用以免慢；当前路径已放在循环外，通常没问题。
- `vdso_calc_ns()` 对 delta 做乘法/移位，必要时走 `mul_u64_u32_add_u64_shr()` 处理溢出保护；这属于纯整数运算，通常不是最主要矛盾。

除非确认 `CSR_TIME` 读取已是“无 trap 的极快读”，否则不建议把主要精力投入到这类微调。

## 6. 快速排查清单（不深挖版）

### 6.1 确认是否走 vDSO 快路径

- 现有证据：RISC-V perf 已看到 `[vdso] __vdso_clock_gettime`（`perf_whisper_riscv_openmp_4.txt`）。
- 仍建议在真实 workload 中确认：
  - `clock_gettime` 是否频繁回退到 syscall（回退通常发生在 clockid 不支持、VDSO clock_mode = NONE、或 vvar 读取异常等情况下）。

### 6.2 判断 “慢” 主要来自哪里

优先级从高到低：

1. **读 time CSR 的代价**（是否 trap/模拟）
2. **CPU 主频/调频策略**（是否长时间低频运行）
3. vDSO 内部的函数调用/分支/栈帧（是否能通过 include 合并、LTO 等减少）
4. vDSO 算法本身（乘法/移位/div）

### 6.3 内核侧检查点（配置/实现）

结合你提供的“检查并启用内核参数”截图：

- x86 有 `CONFIG_X86_TSC=y`、`CONFIG_HPET_TIMER=y` 等，天然有成熟的用户态快计数器路径；
- RISC-V 对应的关键不在 HPET/TSC，而在 **`time` 计数器的可用性与访问成本**（硬件/固件/虚拟化决定性更强）。

## 7. 结论（面向当前问题的回答）

1. 你的数据（calls/sec 6.4× 差异 + RISC-V perf 中 `__vdso_clock_gettime` 占比 13.27%）符合一个典型模式：  
   **RISC-V 平台的 vDSO 取时快路径被“读 `CSR_TIME` 的高固定开销”拖慢**，而 x86_64 的 TSC 读几乎是“免费”的。
2. 除平台时钟实现外，RISC-V vDSO 还有一个可做的工程优化点：  
   **像 x86 一样把 `lib/vdso/gettimeofday.c` 直接 include 进 RISC-V vDSO 编译单元**，以减少跨对象文件调用并提升编译器内联机会；但如果 `CSR_TIME` 读取本身很慢，这只能带来“边际改善”。

## 8. 建议的下一步（如果你希望我继续）

我可以在 `/home/zcxggmu/workspace/patch-work/linux` 内核树里做一个最小改动的 vDSO 优化原型（例如把 RISC-V 的 vgettimeofday 改成 include 通用实现的形式），并在当前目录补充一份 “如何验证 vDSO 热路径是否变快” 的实验步骤文档。

