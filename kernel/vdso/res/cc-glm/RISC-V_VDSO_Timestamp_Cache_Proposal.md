# RISC-V vDSO 时间戳缓存机制技术方案（重新设计版）

> 面向问题：RISC-V 上 `clock_gettime()` vDSO 路径因为读取 `CSR_TIME` 可能触发陷入/模拟而显著偏慢。  
> 本文目标：对现有文档提出的“6.2.1 VDSO 时间戳缓存机制”做合理性评估，并给出一份**语义正确、可落地、可验证**的缓存机制技术方案。

## 1. 背景与动机

在通用 vDSO 实现（`lib/vdso/gettimeofday.c`）中，高精度（HRES）时钟会调用架构钩子 `__arch_get_hw_counter()` 读取硬件计数器，再结合 vvar 中的 `cycle_last/mult/shift/basetime` 计算当前时间。  
在 RISC-V 上，该钩子实现为读取 `CSR_TIME`（`arch/riscv/include/asm/vdso/gettimeofday.h`），而在某些平台/固件/虚拟化环境里，读取 `CSR_TIME` 可能并非廉价指令而是触发陷入或慢模拟，导致单次 `clock_gettime()` 成本远高于 x86 TSC。

因此希望通过“缓存”减少昂贵的 `CSR_TIME` 读取次数，从而提升高频调用场景（AI 推理计时、profiling、日志）的吞吐。

## 2. 对现有“时间戳缓存机制”的合理性评估

原文档（`RISC-V_VDSO_Performance_Analysis.md` 的 6.2.1）给出了一类核心思路：

- 使用 `vd->clock_data[0].seq`（vvar 的序列计数器）作为 “generation”
- generation 未变化时，直接返回上一次读取到的 `CSR_TIME`（缓存命中）

并提供了对应补丁草案（`riscv-vdso-cache-patch` / `riscv-vdso-cache-patch-fix`）。

### 2.1 语义正确性问题：仅返回缓存 `CSR_TIME` 会让时间“停住”

在 vDSO 高精度路径中，**时间是否推进**取决于 `cycles = __arch_get_hw_counter(...)` 是否随真实时间前进。

如果缓存命中时直接返回上一次的 `CSR_TIME`：

- `cycles` 不变
- `vdso_calc_ns()` 的 delta 不变
- `clock_gettime()` 的返回值在一段时间内保持不变（“时间冻结”）

而 `vd->clock_data[0].seq` 的更新频率并不保证是微秒级：它通常随内核 timekeeping 更新发生（tick/nohz/调频/校时等影响），完全可能远大于 1µs。  
因此，“generation 未变化就直接返回缓存 time 值”的实现，**无法保证 `clock_gettime(CLOCK_MONOTONIC)` 在高精度语义下持续推进**，属于功能语义层面的不可接受风险（不仅是精度下降，而是时间可能停住毫秒甚至更久）。

结论：  
仅靠 vvar 的 `seq` 作为缓存有效性判定、并直接复用旧 `CSR_TIME`，在 HRES 路径下不满足 `clock_gettime()` 的基本可用性预期。

### 2.2 可实现性问题：vDSO 不应写 VVAR，且在 vDSO 内引入 TLS 风险极高

补丁草案经历了两个阶段：

1) 试图把缓存放到 `vd->arch_data`（也就是 VVAR 的映射数据页）并在 vDSO 中写入更新  
→ VVAR 通常是只读映射，用户态写会触发 SIGSEGV（补丁 fix 也承认这一点）。

2) 改为在 vDSO 中使用 `__thread` TLS 保存缓存  
→ 这在 vDSO 上往往会引入 TLS 相关动态重定位（`R_*_TLS*`），而内核构建 vDSO 有“禁止动态重定位”的硬约束（`lib/vdso/Makefile.include` 的 `vdso_check` 逻辑会检查重定位表）。在很多架构/工具链组合下，**vDSO 引入 TLS 要么无法链接/通过检查，要么存在 ABI/loader 兼容性风险**。

结论：  
“在 vDSO 自身保存跨调用可写状态”的路径（写 VVAR / 在 vDSO 内用 TLS）均不够稳健，难以上游化，也难以在发行版环境中长期维护。

### 2.3 并发与多核问题：缓存必须处理线程并发与 CPU 迁移

即便不考虑 2.2 的可实现性，缓存如果是“全局静态变量”：

- 多线程同时调用 `clock_gettime()` 会产生数据竞争（即使使用 `READ_ONCE/WRITE_ONCE`，逻辑仍可能被交叉更新打乱）
- CPU 迁移可能导致计数器不同步（尤其是若后续方案使用 `cycle` 作为快计数器），存在“时间倒退”风险

结论：  
缓存必须是**每线程**或至少能在迁移/并发时安全失效；单一全局缓存不可取。

## 3. 设计目标与约束

### 3.1 目标

1. 保持 `clock_gettime()` 的基本语义：不会长时间冻结，且对 `CLOCK_MONOTONIC` 不产生倒退（允许短时间相同值，但不允许明显停住）。
2. 明显减少昂贵路径（读取 `CSR_TIME` 触发陷入/慢模拟）的调用频率。
3. 设计可落地：不依赖在 vDSO 内写 VVAR，不依赖在 vDSO 内引入 TLS 动态重定位。
4. 可验证：给出可执行的正确性与性能验证方法，能在目标平台复现收益与边界行为。

### 3.2 约束（必须接受的现实）

1. vDSO 本体通常是只读映射：不能在 vDSO 内持久化可写全局状态。
2. VVAR 是只读映射：vDSO 也不能写 VVAR 来存缓存。
3. 只靠 vvar 的 `seq` 无法提供“微秒级缓存有效期”这一时间尺度判断。
4. 若平台不存在一个“用户态可廉价读取的快计数器”，就无法在 HRES 语义下通过缓存让时间持续推进；此时只能：
   - 退化为 coarse 语义（影响巨大），或
   - 仅为**新的 opt-in 接口**提供“近似时间”（不改变标准 `clock_gettime` 语义）。

## 4. 推荐总体方案：新增 opt-in 的 vDSO 扩展接口 + 用户态可写缓存

核心思想：**让缓存存放在调用方（glibc/应用）的可写内存中**，vDSO 只读取/更新该缓存，不要求 vDSO 自己持久化写状态。

### 4.1 新增 vDSO 符号（不破坏现有 ABI）

新增一个扩展符号（示意）：

```c
struct __vdso_time_cache;
int __vdso_clock_gettime_cached(clockid_t clk,
                                struct __kernel_timespec *ts,
                                struct __vdso_time_cache *cache);
```

- 保留现有 `__vdso_clock_gettime()` 完整语义，不改变 glibc 现有行为。
- glibc/应用若希望更高性能，可选择调用新符号，并自行分配/维护 `cache`（通常为线程局部）。

### 4.2 cache 结构（线程局部、无锁、可迁移失效）

建议 cache 字段至少包含：

```c
struct __vdso_time_cache {
  u32  seq;              // 最近一次成功使用的 vvar seq（用于检测内核更新）
  u32  cpu;              // 最近一次采样时的 CPU（用于迁移检测）
  u64  time_cycles;      // 最近一次读取到的 CSR_TIME（慢路径）
  u64  fast_cycles;      // 最近一次读取到的“快计数器”（见 4.3）
  u64  last_ns;          // 最近一次返回给用户的 ns（单调钳制）
  u64  scale_fp;         // fast_cycles -> time_cycles 的比例（定点数，可选）
};
```

说明：

- `last_ns` 用于“单调钳制”（monotonic clamp）：即便估算误差或迁移导致回退，也至少返回 `>= last_ns`。
- `cpu` 可通过 `__vdso_getcpu()` 或 `rseq`（若可用）获得；若检测到迁移，则强制走慢路径刷新。

### 4.3 缓存命中时如何“推进时间”：必须依赖一个廉价快计数器

要在缓存命中时仍返回“前进的时间”，需要一个用户态可廉价读取的计数器（fast counter）：

候选：

1. `CSR_CYCLE`（`rdcycle`）：通常是廉价指令，但是否可在 U-mode 读取取决于平台的 `mcounteren/scounteren` 配置与安全策略。
2. 其他平台提供的用户态计数器（若硬件/固件有特定扩展或 MMIO 映射）。

> 如果目标平台无法提供 fast counter（或 fast counter 也会 trap），则本方案无法在保持 HRES 语义的前提下工作；需退化到“coarse/近似接口”路线（见 6.2）。

#### 4.3.1 命中路径的估算公式（线性外推）

在慢路径中同时采样：

- `time0 = csr_read(CSR_TIME)`（慢）
- `fast0 = read_fast_counter()`（快）

命中路径中再读：

- `fast1 = read_fast_counter()`（快）

估算：

```
time_est = time0 + (fast1 - fast0) * scale_fp
```

其中 `scale_fp` 是 fast_counter 到 time_counter 的换算比例（定点数）。比例可通过周期性校准获得，例如每 N 次命中或每当 `seq` 变化、或当检测到 `fast_delta` 超过阈值时，重新走慢路径更新比例。

#### 4.3.2 单调钳制与边界处理（必须做）

为保证不倒退：

- 若 `time_est` 对应的最终 `ns_est` < `cache->last_ns`，返回 `cache->last_ns`。
- 若检测到 CPU 迁移、`seq` 变化、fast counter 未推进/异常跳变，则直接走慢路径刷新。

### 4.4 vDSO 内实现要点（伪代码）

```c
int __vdso_clock_gettime_cached(clk, ts, cache) {
  vd = __arch_get_vdso_u_time_data();
  vc = select_clock(vd, clk);      // 复用现有 __cvdso_* 逻辑

  seq = read_seq_begin(vc);        // 复用现有 seqlock 读取
  cpu = vdso_getcpu();             // 可选：若取 CPU 太贵可只在慢路径取

  if (cache->seq == seq && cache->cpu == cpu && cache_ready(cache)) {
     fast1 = read_fast_counter();
     time_est = cache->time_cycles + (fast1 - cache->fast_cycles) * cache->scale_fp;
     ns_est = vdso_calc_ns(vc, time_est, basetime_nsec);
     ns_est = max(ns_est, cache->last_ns);
     cache->last_ns = ns_est;
     fill_timespec(ts, sec, ns_est);
     if (!read_seq_retry(vc, seq))
        return 0;
     // seq 变了，回退到慢路径重试
  }

  // 慢路径：读取 CSR_TIME（可能 trap），并重置/校准缓存
  time0 = csr_read(CSR_TIME);
  fast0 = read_fast_counter();     // 如果可用
  ns0 = vdso_calc_ns(vc, time0, basetime_nsec);
  ns0 = max(ns0, cache->last_ns);
  cache_update(cache, seq, cpu, time0, fast0, ns0, recompute_scale_if_needed);
  fill_timespec(ts, sec, ns0);
  if (!read_seq_retry(vc, seq))
     return 0;
  // seq 变了：按 vDSO 现有逻辑重试
}
```

关键点：

- 缓存命中仍要走一遍 seqlock 校验；否则遇到 vvar 更新会计算出不一致的时间。
- 缓存命中依赖 fast counter；没有 fast counter 时不能推进时间。

## 5. 需要的内核侧配合点（建议分层开关）

### 5.1 Kconfig：允许启用/禁用扩展接口

建议提供：

- `CONFIG_RISCV_VDSO_CLOCK_GETTIME_CACHED`：编译 vDSO 扩展符号（默认 n，避免误用）。
- `CONFIG_RISCV_VDSO_FAST_COUNTER_CYCLE`：允许/配置用户态读取 `cycle` 作为 fast counter（默认 n，涉及安全权衡）。

### 5.2（可选）计数器可用性探测

在没有 fast counter 或 fast counter 不稳定时，应在 vDSO 内直接禁用缓存命中路径（始终慢路径），以保证语义。

可用性探测来源：

- 运行时读取/尝试 fast counter（需要避免触发 SIGILL；更稳妥是由内核通过 hwprobe/vvar 提供能力位）
- 利用 `__vdso_riscv_hwprobe` 返回是否支持相关 ISA/权限

## 6. 备选方案（当 fast counter 不可用时）

### 6.1 不推荐：直接让标准 `clock_gettime()` 退化为 coarse 语义

可以通过强制走 `do_coarse()` 路径来避免读 `CSR_TIME`，但这会显著改变精度/分辨率与应用预期，并可能影响大量依赖高精度计时的组件（profilers、event loops、超时机制等）。  
除非是特定封闭场景（例如只跑某类 AI 推理 workload 且可接受 ms 级时间），不建议作为通用方案。

### 6.2 推荐：仅提供 opt-in 的“近似时间”接口

如果无法提供 fast counter，则缓存只能返回“近似时间”（可能在一小段时间内不推进）。此时应：

- 不影响标准 `clock_gettime()` 行为；
- 通过新符号/新 API 提供 `clock_gettime_fast_approx()` 之类接口；
- 明确文档化语义：允许在 X µs 内返回相同值；保证不倒退；不用于严格超时控制。

## 7. 正确性与安全性分析

### 7.1 正确性

必须保证：

- `CLOCK_MONOTONIC` 不倒退（通过 `last_ns` 单调钳制）。
- 不出现长时间冻结：命中路径能推进（依赖 fast counter），或在阈值/异常下主动回退慢路径刷新。
- CPU 迁移时不倒退：检测到 `cpu` 变化强制慢路径刷新。

### 7.2 安全性/侧信道

启用用户态读取 `cycle` 可能增加侧信道能力（高精度计时器常被用于侧信道攻击）。建议：

- 默认关闭 fast counter 相关开关；
- 仅在可信环境（封闭推理集群、禁用不可信代码执行）启用；
- 或只对特定 cgroup/容器/进程启用（更复杂，可作为后续方向）。

## 8. 性能预期与验证计划

### 8.1 性能预期

在 “CSR_TIME 读取昂贵 + fast counter 廉价 + 高频调用” 的场景下：

- 慢路径（trap）比例显著降低
- 单次 `clock_gettime_cached` 命中成本约为：1 次 fast counter + seqlock 读 + 少量乘加/移位

实际收益取决于：

- 命中率（调用间隔分布）
- fast counter 稳定性（DVFS/迁移）
- seqlock `fence` 成本（RISC-V 端固定存在）

### 8.2 验证步骤（建议必须做）

1. 功能正确性：
   - 单调性：高频循环调用检查不倒退（含多线程、绑核/不绑核）。
   - 长时间正确：sleep 1ms/10ms/1s 后再读，确保时间推进正确。
2. 压力与并发：
   - 多线程同时调用，检查无崩溃、无异常值。
3. 性能：
   - `perf stat` 对比 trap 次数/周期（或用平台可观测的异常计数器）。
   - calls/sec 对比：`clock_gettime` vs `clock_gettime_cached`。

## 9. 结论

“VDSO 时间戳缓存机制”在 RISC-V 上**想要既提升性能又保持 `clock_gettime()` 高精度语义**，关键不在“是否缓存”，而在：

1. 缓存命中时必须有一个廉价的 fast counter 让时间继续推进；
2. 缓存状态必须放在用户态可写内存（线程局部），而不是 vDSO/VVAR 内；
3. 必须处理 CPU 迁移与单调性钳制，避免时间倒退。

因此，建议将“缓存机制”设计为**新增 opt-in vDSO 扩展接口 + 用户态线程局部缓存**，而不是修改现有 `__vdso_clock_gettime()` 的语义或在 vDSO 内引入不可控的可写状态。

