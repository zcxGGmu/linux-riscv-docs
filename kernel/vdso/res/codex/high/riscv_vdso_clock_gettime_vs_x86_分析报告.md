# RISC-V 内核 vDSO + `clock_gettime()` 相比 x86_64 过慢：原因分析与优化方向

> 生成时间：2026-01-11  
> 数据来源：`perf_whisper_riscv_openmp_4.txt`、`perf_whisper_x86_openmp_4.txt`、`riscv-x86对比.jpg`、`硬件平台配置x86 vs risc-v.docx`  
> 内核源码参考：`/home/zcxggmu/workspace/patch-work/linux`（kernelversion：`6.19.0-rc1`）

## 1. 现象与结论摘要

### 1.0 平台与内核信息（来自 `硬件平台配置x86 vs risc-v.docx`）

- x86_64 内核：`Linux sophgo-Rack-Server 6.8.0-90-generic #91~22.04.1-Ubuntu SMP PREEMPT_DYNAMIC Thu Nov 20 15:20:45 UTC 2 x86_64 ...`
- RISC-V 内核：`Linux openeuler-riscv64 6.12.56-0.0.0.0.riscv64 #1 SMP Fri Oct 31 03:04:33 CST 2025 riscv64 ...`
- 时间相关内核配置（docx 中 `grep -E "NO_HZ|HPET|TSC" /boot/config-$(uname -r)` 摘要）：
  - 两边都有：`CONFIG_NO_HZ_COMMON=y`、`CONFIG_NO_HZ_FULL=y`、`CONFIG_NO_HZ=y`
  - x86_64 侧显式启用：`CONFIG_X86_TSC=y`、`CONFIG_HPET_TIMER=y`、`CONFIG_HPET=y`、`CONFIG_HPET_MMAP=y` 等
  - RISC-V 侧无对应 TSC/HPET 项（与 `riscv-x86对比.jpg` 中“x86 有 TSC/HPET，RISC-V 无”一致）

### 1.1 现象（从对比图整理）

下表来自 `riscv-x86对比.jpg`（单位：calls/sec）：

| 接口 | x86_64 | RISC-V | 慢多少 |
|---|---:|---:|---:|
| `clock_gettime(CLOCK_MONOTONIC)` | 2,103,771 | 328,056 | **6.4×** |
| `time.time()` | 17,830,207 | 4,539,203 | 3.9× |
| `time.perf_counter()` | 17,736,566 | 4,249,661 | 4.2× |
| `time.monotonic()` | 17,736,566 | 4,407,442 | 4.1× |

对应的“单次调用平均耗时”（≈ `1e9 / calls_per_sec`）：

| 接口 | x86_64 (ns/call) | RISC-V (ns/call) |
|---|---:|---:|
| `clock_gettime(CLOCK_MONOTONIC)` | ~476 | ~3,048 |
| `time.time()` | ~56 | ~220 |
| `time.perf_counter()` | ~56 | ~235 |
| `time.monotonic()` | ~56 | ~227 |

图表（本目录生成）：

![](chart_calls_per_sec.svg)

同时建议保留原始对比图（包含测试截图与配置摘要）：

![](riscv-x86对比.jpg)

### 1.2 perf 侧证（whisper + openmp 场景）

在 RISC-V 的 perf report 中，`__vdso_clock_gettime` 成为 Top 热点之一，而 x86_64 基本不可见：

![](chart_perf_overhead.svg)

从 `perf_whisper_riscv_openmp_4.txt` 的 Top15 可见（截取关键信息）：

- `13.27%  [vdso] __vdso_clock_gettime`
- `4.26%   libc.so.6 clock_gettime@@GLIBC_2.27`

而 `perf_whisper_x86_openmp_4.txt` 中：

- `__vdso_clock_gettime` 仅以 `0.00%` 出现（接近不可测）

这说明在你的业务（AI 卡运行 + openmp）里，**时间读取路径确实被高频调用，且在 RISC-V 上成本显著更高**。

perf 报告采样概况（来自两个文件头部）：

| 平台 | event | Samples | Event count (approx.) |
|---|---|---:|---:|
| RISC-V | `cpu-clock` | 363K | 90,904,750,000 |
| x86_64 | `cpu-clock` | 115K | 28,998,750,000 |

perf Top 开销条目对比（从两个 report 的 Top15 抽取前 8 项，便于快速定位热点）：

**RISC-V Top8（`perf_whisper_riscv_openmp_4.txt`）**

| Overhead | Shared Object | Symbol |
|---:|---|---|
| 13.27% | `[vdso]` | `__vdso_clock_gettime` |
| 11.90% | `libm.so.6` | `expf@@GLIBC_2.27` |
| 8.96% | `libgomp.so.1.0.0.xdd` | `gomp_barrier_wait_end` |
| 5.24% | `libtorch_cpu.so` | `...invoke_parallel... [clone ._omp_fn.0]` |
| 4.26% | `libc.so.6` | `clock_gettime@@GLIBC_2.27` |
| 3.97% | `libgomp.so.1.0.0.xdd` | `gomp_team_barrier_wait_end` |
| 3.92% | `libtorch_cpu.so` | `...serial_vec_log_softmax...` |
| 3.11% | `libtorch_cpu.so` | `...VectorizedLoop2d...` |

**x86_64 Top8（`perf_whisper_x86_openmp_4.txt`）**

| Overhead | Shared Object | Symbol |
|---:|---|---|
| 46.04% | `libgomp.so.1` | `0x000000000001de62` |
| 6.95% | `libgomp.so.1` | `0x000000000001de66` |
| 5.42% | `libgomp.so.1` | `0x000000000001de6d` |
| 3.13% | `libtorch_cpu.so` | `...AVX2::topk_impl_loop...` |
| 2.97% | `libgomp.so.1` | `0x000000000001e02a` |
| 1.60% | `_multiarray_umath...so` | `npy_floatbits_to_halfbits` |
| 1.39% | `[kernel.kallsyms]` | `do_user_addr_fault` |
| 1.29% | `libgomp.so.1` | `0x000000000001de60` |

> 解释：x86_64 的 Top 热点主要在 OpenMP 自旋/屏障与向量化算子上；RISC-V 则出现明显的 `__vdso_clock_gettime` 热点，符合“计时开销被放大并进入主路径”的观察。

### 1.3 最核心的根因（高置信度）

RISC-V 的 vDSO 高精度时间读取依赖读取 `CSR_TIME`（`rdtime`/`csrr time`）。在你给定内核源码里，vDSO 的实现明确写道：

- `arch/riscv/include/asm/vdso/gettimeofday.h`：`__arch_get_hw_counter()` 直接 `csr_read(CSR_TIME)`，并注明该读取的“目的”可能是 **触发陷入到 M-mode 获取 CSR_TIME**（即：硬件/固件/虚拟化环境可能对 `time` CSR 进行陷入仿真）。

一旦 `CSR_TIME` 的读取不是本地快速指令、而是陷入到 M-mode/Hypervisor 处理（SBI/HS 模式），那么 vDSO 里“看似用户态的函数”就会变成“**每次调用都要陷入固件/虚拟化层**”，其代价通常会达到微秒级，这与 `~3,048ns/call` 的量级非常吻合。

> 这也解释了一个容易困惑的现象：perf 报告里热点看起来仍在 `[vdso] __vdso_clock_gettime`，但实际上“消耗的时间可能发生在 M-mode/Hypervisor”，不一定以 Linux 内核函数符号呈现。

## 2. vDSO `clock_gettime()` 关键路径：RISC-V vs x86_64

### 2.1 Linux vDSO 读时间的通用算法（与架构无关的主体）

内核源码：`lib/vdso/gettimeofday.c`

核心逻辑（简化）：

1. 读取 vvar 页（`vdso_time_data`）中对应 clock 的 `seq`（类似 seqlock），保证一致性。
2. 调用 `__arch_get_hw_counter(clock_mode, vd)` 读取“硬件计数器”。
3. 用 `mult/shift` 将计数器增量换算为 ns，并与 `basetime` 合成最终的 `timespec`。
4. 若 `seq` 发生变化则重试。

因此，单次调用的成本主要来自：

- `__arch_get_hw_counter()` 的代价
- 内存屏障/一致性读（`smp_rmb()` 等）
- 换算数学（乘法 + 位移，少量分支）
- 少量重试（在 timekeeper 更新窗口撞上时）

### 2.2 RISC-V：`CSR_TIME` 读硬件计数器

内核源码：`arch/riscv/include/asm/vdso/gettimeofday.h`

- `__arch_get_hw_counter()`：`return csr_read(CSR_TIME);`

风险点：

- `CSR_TIME` 读取若由固件/虚拟化“陷入仿真”，则 **每次 vDSO 调用都要陷入**，成本从“几十纳秒”升级到“几微秒”。

### 2.3 x86_64：`RDTSC` / pvclock / hvclock 等

内核源码：`arch/x86/include/asm/vdso/gettimeofday.h`

典型情况（物理机）：

- `__arch_get_hw_counter()`：读取 `TSC`（`rdtsc_ordered()`），这是用户态可直接执行的指令，延迟通常为几十个 cycle。
- x86 还有 paravirt/hyperv 的 vclock（共享页方式），避免陷入。

此外，x86 的内存模型更强，vDSO 读 `seq` 的屏障成本更低：

- x86：`arch/x86/include/asm/barrier.h` 中 `__smp_rmb()` 退化为编译器屏障（`barrier()`）
- RISC-V：`arch/riscv/include/asm/barrier.h` 中 `__smp_rmb()` 是 `RISCV_FENCE(r, r)`（真实 `fence` 指令）

虽然 `fence` 本身未必造成“6×”，但在高频调用下会叠加放大差距。

## 3. 为什么 RISC-V 的 `__vdso_clock_gettime` 会在业务里变成热点

基于你的 perf 与对比图，可以把“慢”的成分拆为两类：

### 3.1 固件/虚拟化陷入（最可能、最致命）

证据链：

- `arch/riscv/include/asm/vdso/gettimeofday.h` 的注释直接提示 `csr_read(CSR_TIME)` 可能用于“trap 到 M-mode 获取 CSR_TIME”
- 微基准显示 `clock_gettime(CLOCK_MONOTONIC)` 达到 **微秒级**（~3.0us）而不是“几百 ns”
- perf 中热点集中在 vDSO 函数本身，而不是 Linux 内核 syscall 路径（`syscall` 总占比非常低）

典型触发场景：

- 机器没有原生实现可直接读取的 `time` CSR（或被设计为陷入仿真）
- 运行在虚拟化环境中，`time` CSR 被 hypervisor 捕获（HS 模式）
- SBI/固件对时间 CSR 的实现路径过长（锁、MMIO、IPI、串行化等）

### 3.2 架构内存模型差异带来的屏障与重试（次要，但可观）

即便不存在 M-mode/Hypervisor trap，RISC-V 相对 x86 仍会更慢：

- vDSO 读 seqlock 的 `smp_rmb()` 在 RISC-V 上是 `fence`，x86 上近似 0 成本
- `__vdso_clock_gettime` 中可能存在重试（与 timekeeper 更新频率、NO_HZ、tick 行为、CPU 迁移有关）

这部分通常体现为 **~1.x～2.x** 的差距，更难单独解释你图中 `6.4×` 的量级，但会在“trap 已经很贵”时进一步放大。

### 3.3 时钟源能力差异（“x86 有 TSC，RISC-V 没有同级替代品”）

`riscv-x86对比.jpg` 也指出：

- x86：TSC/HPET 等硬件计时资源完善
- RISC-V：对应项缺失（或至少在该平台上未启用）

严格讲，RISC-V 也有 `cycle/time/instret` 类 CSR，但是否“本地快速可读、跨核同步、频率稳定、可被 vDSO 安全使用”取决于 CPU/SoC/固件实现质量。

## 4. 针对当前场景：RISC-V 内核 vDSO 可能的优化点（按收益/风险排序）

> 重点说明：如果 `CSR_TIME` 的读取本身会陷入到 M-mode/Hypervisor，那么 **仅靠 Linux 内核里“改几行 vDSO 代码”无法达到 x86 的量级**。最大的收益来自“让用户态读计数器不再陷入”。

### 4.1（最大收益）让 `CSR_TIME` 成为“真·用户态快速可读”

目标：把 `csr_read(CSR_TIME)` 从“陷入仿真”变成“本地寄存器读”或“极短路径”。

落地检查清单（建议你在 RISC-V 机器上验证）：

1. 确认 `SCOUNTEREN` 是否已开启 `time` 位  
   - 内核源码 `arch/riscv/kernel/head.S` 会写 `CSR_SCOUNTEREN = 0x2`（time）  
   - 若实际系统被某层复位/限制，需要排查固件/bootloader
2. 确认 CPU 是否实现 `Zicntr`（或至少 `time` CSR 的原生实现）  
   - 可通过 `/proc/cpuinfo`、hwprobe（不同发行版工具不同）判断
3. 若在虚拟化环境：让 hypervisor “直通”或提供共享页计时（类似 x86 pvclock/hvclock）
4. 优化/替换 SBI 时间实现路径（减少锁/序列化/慢速 MMIO）

> 这一步属于“平台/固件/虚拟化栈”优化，但对 `vDSO clock_gettime` 的收益通常是数量级的。

### 4.2（中高收益）为 RISC-V 增加类似 x86 的“共享页 paravirt 时钟源”（避免陷入）

x86 在虚拟化场景能做到快，关键点是：**不靠陷入读时间**，而是 hypervisor 提供共享内存页（pvclock/hvclock）。

RISC-V 当前内核树里：

- `arch/riscv/kernel/paravirt.c` 只实现了 steal-time（SBI STA），不解决 `clock_gettime`

可行方向：

- 为 RISC-V/KVM 设计一页只读的 vclock 数据（类似 pvclock）
- 在 `drivers/clocksource/timer-riscv.c` 中注册一个新的 clocksource，设置 `vdso_clock_mode` 为新的 VDSO mode
- 在 `arch/riscv/include/asm/vdso/clocksource.h` 增加新的 `VDSO_CLOCKMODE_*`
- 在 `arch/riscv/include/asm/vdso/gettimeofday.h` 的 `__arch_get_hw_counter()` 中根据 `clock_mode` 选择“共享页读值”而不是 `CSR_TIME`

这类方案的优势是：**即使 `time` CSR 必须陷入，也能绕开陷入**；缺点是实现量更大，需要虚拟化/固件配合。

### 4.3（中等收益，高风险）尝试用 `CSR_CYCLE`（类似“RISC-V 的 TSC”）做 vDSO 计时

前提非常苛刻：

- `cycle` 在所有 hart 上同步/单调（跨核迁移不跳变）
- 频率稳定或可精确换算（无 DVFS 或有可靠频率源）
- 用户态可直接读取且不陷入

若上述前提成立，可考虑：

- 增加 `VDSO_CLOCKMODE_RISCV_CYCLE`，`__arch_get_hw_counter()` 读 `CSR_CYCLE`
- 增加/选择一个基于 cycle 的 clocksource（或为现有 clocksource 增加 cycle 作为 VDSO 读取源）

注意：这一步如果做错，会直接导致 `clock_gettime` **不单是慢，而是“不准/倒退”**，因此必须在硬件平台上充分验证。

### 4.4（中低收益）降低 vDSO 读路径的屏障/重试成本（细节优化）

在 `lib/vdso/gettimeofday.c` 的算法框架不变的情况下，能做的通常是微调：

- 减少不必要的重试：例如确保 timekeeper 更新窗口更短、更少写 vvar（会牵涉内核 timekeeping 更新策略）
- 若硬件支持更强内存序（例如某些扩展/模式），让 `smp_rmb()` 更便宜（依赖平台能力）

这类优化很难带来“6×”量级收益，更像是在“计数器读取已很快”的前提下，把 1.3× 打磨到 1.1×。

### 4.5（应用侧缓解，往往立竿见影）

如果你当前的业务里存在“高频计时”（profiling、busy-loop 轮询、OpenMP/线程池频繁打点），在 RISC-V 平台上建议优先：

- 将非必须的高精度计时改为 `CLOCK_MONOTONIC_COARSE` / `CLOCK_REALTIME_COARSE`
- 将“每次迭代取时间”改为“批量/采样取时间”
- 若仅用于耗时统计且允许小误差，可按线程缓存 timestamp

这并不替代内核优化，但能在短周期内显著降低 `__vdso_clock_gettime` 的热点占比。

## 5. 建议的进一步验证（用于把“推断”变成“定论”）

在 RISC-V 机器上做 3 个小实验，基本能把根因锁死：

1. **测量单条 `rdtime` 的平均开销**  
   - 写一个 C microbench：循环执行 `csrr time`（或编译器内联读 time CSR），统计每次耗时  
   - 若出现微秒级，几乎可以确认存在 M-mode/Hypervisor trap
2. **对比 `rdcycle` vs `rdtime` 的开销**（如果 `rdcycle` 可用）  
   - 若 `rdcycle` 明显更快，说明“陷入/慢路径”集中在 `time` CSR
3. **确认是否运行在虚拟化环境、以及 SBI 版本/实现**  
   - `dmesg | grep -i sbi`、检查 hypervisor/firmware 信息  
   - 在 KVM 场景，考虑 paravirt vclock 方案

## 6. 附：与本报告直接相关的内核源码位置（便于你快速对照）

- RISC-V vDSO 读硬件计数器：`/home/zcxggmu/workspace/patch-work/linux/arch/riscv/include/asm/vdso/gettimeofday.h`
- RISC-V 计时 clocksource 与 vDSO mode：`/home/zcxggmu/workspace/patch-work/linux/drivers/clocksource/timer-riscv.c`
- 通用 vDSO gettimeofday/clock_gettime 实现：`/home/zcxggmu/workspace/patch-work/linux/lib/vdso/gettimeofday.c`
- x86 vDSO 读硬件计数器与 pvclock：`/home/zcxggmu/workspace/patch-work/linux/arch/x86/include/asm/vdso/gettimeofday.h`
- 内存屏障差异：  
  - x86：`/home/zcxggmu/workspace/patch-work/linux/arch/x86/include/asm/barrier.h`  
  - RISC-V：`/home/zcxggmu/workspace/patch-work/linux/arch/riscv/include/asm/barrier.h`
