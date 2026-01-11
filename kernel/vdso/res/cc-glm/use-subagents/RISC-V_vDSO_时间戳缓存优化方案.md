# RISC-V vDSO 时间戳缓存纯软件优化方案

> **目标**：在纯软件层面减少 RISC-V vDSO 中昂贵的 `CSR_TIME` 读取操作
> **约束**：不依赖硬件 fast counter，不修改现有 `clock_gettime` 语义

---

## 1. 问题回顾

当前 RISC-V vDSO `clock_gettime()` 的主要性能瓶颈：

```c
// lib/vdso/gettimeofday.c - do_hres()
do {
    seq = vdso_read_begin(vc);      // 读 seq，包含 smp_rmb()
    cycles = __arch_get_hw_counter(); // ← csr_read(CSR_TIME) - 可能 trap!
    ns = vdso_calc_ns(cycles);       // 计算 ns
} while (vdso_read_retry(vc, seq));  // 再次 smp_rmb()
```

**核心问题**：每次调用都需要读取 `CSR_TIME`，这可能：
1. 触发 trap 到 M-mode/SBI
2. 在虚拟化环境中触发 VM exit
3. 即使不 trap，也比 x86 的 `rdtsc` 慢

---

## 2. 推荐方案：Per-CPU VVAR 时间戳缓存

### 2.1 核心思想

**由内核定期更新 per-CPU 缓存，用户态直接读取缓存的 ns 值**

```
┌─────────────────────────────────────────────────────────────────┐
│                         内核态 (S-mode)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   定时器中断 (每 1ms)                                            │
│        │                                                         │
│        ▼                                                         │
│   ┌─────────────────┐                                           │
│   │ for each CPU:   │                                           │
│   │   cycles = csr_read(CSR_TIME)  ← 只在这里读 CSR_TIME       │
│   │   ns = vdso_calc_ns(cycles)                                │
│   │   vvar->cpu_cache[cpu_id].ns = ns                         │
│   │   vvar->cpu_cache[cpu_id].cycles = cycles                   │
│   │   vvar->cpu_cache[cpu_id].seq = new_seq                    │
│   └─────────────────┘                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 写入 VVAR (只读映射给用户态)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         用户态 (U-mode)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   clock_gettime(CLOCK_MONOTONIC):                               │
│        │                                                         │
│        ▼                                                         │
│   ┌─────────────────────────┐                                   │
│   │ cpu_id = get_cpu()      │ ← 确定当前 CPU                     │
│   │ cache = &vvar->cpu_cache[cpu_id]                            │
│   │                                                          │
│   │ // 检查缓存是否"足够新"                                      │
│   │ if (cache_is_fresh(cache)) {  ← 关键优化！                 │
│   │     // 快路径：直接返回缓存值，不读 CSR_TIME                │
│   │     ts->sec = cache->sec                                    │
│   │     ts->nsec = cache->ns & NSEC_MASK                        │
│   │     return 0                                                │
│   │ }                                                          │
│   │                                                          │
│   │ // 慢路径：读取 CSR_TIME                                    │
│   │ cycles = csr_read(CSR_TIME)                                 │
│   │ ns = vdso_calc_ns(cycles)                                   │
│   │ ts->sec = ns / NSEC_PER_SEC                                 │
│   │ ts->nsec = ns % NSEC_PER_SEC                                │
│   └─────────────────────────┘                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 VVAR 数据结构扩展

**文件**: `include/vdso/datapage.h`

```c
// 新增：per-CPU 时间戳缓存
struct vdso_cpu_timestamp {
    u64 seq;          // 序列号（用于校验）
    u64 cycles;       // 对应的 cycle 值
    u64 ns;           // 完整的 ns 时间戳（相对于某个 epoch）
    u64 sec;          // 秒部分（优化读取）
    u32 last_update;  // 上次更新时的 cycle 计数（用于新鲜度检查）
};

struct vdso_time_data {
    // ... 现有字段 ...

    // 新增：per-CPU 缓存数组
    struct vdso_cpu_timestamp cpu_cache[NR_CPUS];
};
```

### 2.3 内核侧实现

**文件**: `kernel/time/vsyscall.c` 或新建 `kernel/time/vdso_cache.c`

```c
// 配置参数
#define VDSO_CACHE_UPDATE_INTERVAL_NS    1000000  // 1ms 更新一次
#define VDSO_CACHE_FRESHNESS_THRESHOLD   500000   // 500µs 认为"新鲜"

// 定时器回调 - 每个 CPU 都会执行
static void vdso_cache_update_timer(struct timer_list *timer)
{
    struct vdso_time_data *vdata = vdso_k_time_data;
    int cpu = smp_processor_id();
    struct vdso_cpu_timestamp *cache = &vdata->cpu_cache[cpu];
    u64 cycles, ns;
    unsigned long seq;

    // 读取当前的 CSR_TIME
    cycles = get_cycles();  // 内核态读 CSR_TIME

    // 计算 ns 时间戳（复用 timekeeper 的计算）
    ns = timekeeping_cycles_to_ns(cycles);

    // 更新缓存（使用 seqlock 保护）
    seq = vdso_update_begin();
    cache->cycles = cycles;
    cache->ns = ns;
    cache->sec = div_u64_rem(ns, NSEC_PER_SEC, &cache->ns);
    cache->last_update = cycles;
    smp_wmb();  // 写屏障
    cache->seq = seq;
    vdso_update_end(seq);

    // 重新调度定时器
    mod_timer(timer, jiffies + usecs_to_jiffies(VDSO_CACHE_UPDATE_INTERVAL_NS / 1000));
}

// 初始化：为每个 CPU 启动定时器
static int __init vdso_cache_init(void)
{
    int cpu;

    for_each_possible_cpu(cpu) {
        struct timer_list *timer = &per_cpu(vdso_cache_timer, cpu);
        timer_setup(timer, vdso_cache_update_timer, TIMER_PINNED);
        mod_timer(timer, jiffies + 1);
    }

    return 0;
}
late_initcall(vdso_cache_init);
```

### 2.4 vDSO 用户态实现

**文件**: `arch/riscv/kernel/vdso/vgettimeofday.c` 或修改 `lib/vdso/gettimeofday.c`

```c
// 新增：RISC-V 特定的快速路径
static __always_inline int do_hres_cached(struct vdso_clock *vc,
                                          clockid_t clk,
                                          struct __kernel_timespec *ts)
{
    const struct vdso_time_data *vdata = __arch_get_vdso_u_time_data();
    struct vdso_cpu_timestamp *cache;
    u32 cpu_id, seq;
    u64 now_cycles, delta_cycles, cached_ns;

    // 获取当前 CPU ID
    cpu_id = __vdso_getcpu();  // 使用现有的 vDSO getcpu

    // 获取当前 CPU 的缓存
    cache = &vdata->cpu_cache[cpu_id];

    // 读取缓存的 seq
    seq = READ_ONCE(cache->seq);

    // 检查缓存是否"新鲜"
    now_cycles = csr_read(CSR_CYCLE);  // CYCLE CSR 通常是用户态可读的
    cached_cycles = READ_ONCE(cache->last_update);

    // 计算经过的 cycle 数（需要处理溢出）
    if (now_cycles >= cached_cycles) {
        delta_cycles = now_cycles - cached_cycles;
    } else {
        // 处理溢出（假设 CYCLE 是 64 位，实际上很少溢出）
        delta_cycles = (U64_MAX - cached_cycles) + now_cycles;
    }

    // 将 cycle 转换为 ns（假设 CPU 频率相对稳定）
    // 这里使用保守估计：即使 CPU 变频，cycle_to_ns 的误差也在可接受范围内
    delta_ns = cycles_to_ns_approx(delta_cycles);

    // 如果缓存足够"新鲜"（< 500µs），直接使用缓存值
    if (delta_ns < VDSO_CACHE_FRESHNESS_THRESHOLD) {
        // 快路径：直接返回缓存，不读 CSR_TIME！
        smp_rmb();
        ts->tv_sec = READ_ONCE(cache->sec);
        ts->tv_nsec = READ_ONCE(cache->ns);

        // 单调性保证：确保不倒退
        // （如果需要，可以加一个 per-thread 的 last_ns 钳制）
        return 0;
    }

    // 缓存过期，走慢路径
    return do_hres_fallback(vc, clk, ts);
}

// 修改现有的 __cvdso_clock_gettime
__cvdso_clock_gettime(clockid_t clock, struct __kernel_timespec *ts)
{
    const struct vdso_time_data *vd = __arch_get_vdso_u_time_data();
    struct vdso_clock *vc = &vd->clock_data[CS_HRES_COARSE];

    // ... 现有的 clock_id 检查逻辑 ...

    // RISC-V 特定优化：尝试使用 per-CPU 缓存
#ifdef CONFIG_RISCV_VDSO_PERCPU_CACHE
    if (do_hres_cached(vc, clock, ts) == 0)
        return 0;
#endif

    // 回退到原有实现
    return __cvdso_clock_gettime_common(clock, ts);
}
```

### 2.5 关键优化点

1. **新鲜度检查使用 CYCLE CSR**：
   - CYCLE CSR 通常是用户态可读的（需要检查 `mcounteren/scounteren` 配置）
   - 即使 CPU 变频，cycle_to_ns 的误差在几百微秒内可以接受
   - 如果 CYCLE 不可用，可以退化为总是使用缓存（精度降低）

2. **缓存更新频率可配置**：
   - 默认 1ms 更新一次
   - 可通过 Kconfig/启动参数调整
   - 平衡精度和性能

3. **单调性保证**：
   - 如果需要严格的单调性，可以添加 per-thread 的 `last_ns` 钳制
   - 类似于原缓存方案中的 `cache->last_ns`

### 2.6 性能预期

```
优化前（每次都读 CSR_TIME）:
├── fence ir,ir × 2         ~6-12 周期
├── csr_read(CSR_TIME)       ~20-50 周期（可能 trap）
└── vdso_calc_ns            ~10-20 周期
总计: ~36-82 周期/调用

优化后（缓存命中，假设 80% 命中率）:
├── getcpu()                ~5-10 周期
├── 读 per-CPU 缓存          ~2-5 周期
├── csr_read(CSR_CYCLE)     ~5-10 周期（用户态可读）
├── 新鲜度计算               ~5-10 周期
└── 返回缓存值               ~2-5 周期
总计: ~19-40 周期/调用

性能提升: ~2-5× (缓存命中路径)
```

---

## 3. 备选方案对比

### 3.1 方案对比表

| 方案 | 复杂度 | 性能提升 | 精度 | 需要硬件支持 | 上游化难度 |
|------|--------|----------|------|--------------|------------|
| **Per-CPU VVAR 缓存** | 中 | 2-5× | µs 级 | CYCLE CSR (可选) | 中 |
| 用户态 TLS 缓存 | 高 | 5-10× | ns 级 | 需要 fast counter | 高 |
| 增加更新频率 | 低 | 1.5-2× | µs 级 | 无 | 低 |
| 混合 COARSE | 低 | 1.2-1.5× | ms 级 | 无 | 低 |

### 3.2 其他可行方案

#### 方案 A：增加 VVAR 更新频率

**修改**: `kernel/time/vsyscall.c` 中的 `update_vsyscall()` 调用频率

```c
// 当前：tick 周期更新（通常 4ms 或更长）
// 优化：通过 hrtimer 每隔 500µs 更新一次
```

**优点**：实现简单，不改变 vDSO 逻辑
**缺点**：增加内核开销，精度仍受限于更新频率

#### 方案 B：自适应缓存策略

```c
// 根据调用频率动态调整
if (调用间隔 < 阈值) {
    // 高频调用：使用 per-CPU 缓存
    return cached_time();
} else {
    // 低频调用：直接读 CSR_TIME
    return read_hw_counter();
}
```

**优点**：自适应，兼顾精度和性能
**缺点**：需要检测调用频率，增加复杂度

---

## 4. 实现步骤

### 4.1 阶段 1：基础框架（P0）

1. 扩展 VVAR 数据结构，添加 `cpu_cache[]` 数组
2. 实现内核侧的 per-CPU 定时器更新逻辑
3. 实现 vDSO 侧的缓存读取和新鲜度检查
4. 添加 Kconfig 选项

### 4.2 阶段 2：优化和完善（P1）

1. 添加 CYCLE CSR 可用性检测
2. 实现单调性保证（per-thread 钳制）
3. CPU 迁移检测和处理
4. 性能测试和调优

### 4.3 阶段 3：可配置和监控（P2）

1. 添加 sysctl 接口（更新频率、新鲜度阈值）
2. 添加 perf 统计（缓存命中率）
3. 文档和测试用例

---

## 5. 风险和缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| CYCLE CSR 不可用 | 部分优化失效 | 添加检测，回退到纯缓存模式 |
| CPU 变频导致精度误差 | 时间戳误差 | 使用保守的新鲜度阈值 |
| CPU 迁移导致读取错误缓存 | 时间倒退 | 添加 CPU 迁移检测 |
| 内核定时器开销 | 内核性能下降 | 可配置更新频率 |
| VVAR 页面大小增加 | 内存占用 | Per-CPU 数量可配置 |

---

## 6. 验证和测试

### 6.1 功能测试

```c
// 测试 1：单调性
for (int i = 0; i < 1000000; i++) {
    clock_gettime(CLOCK_MONOTONIC, &ts);
    assert(ts.tv_nsec >= last_ns);
}

// 测试 2：精度
clock_gettime(CLOCK_MONOTONIC, &t1);
usleep(1000);  // 1ms
clock_gettime(CLOCK_MONOTONIC, &t2);
assert(diff_ns(t2, t1) >= 1000000);

// 测试 3：多线程
// 启动多个线程，同时调用 clock_gettime
```

### 6.2 性能测试

```bash
# 对比优化前后的 calls/sec
./cgtime_bench

# perf 统计
perf stat -e cycles,instructions,exceptions,cache-misses ./cgtime_bench

# 缓存命中率
# 通过 sysctl 或 debugfs 读取统计信息
```

---

## 7. Kconfig 配置

**文件**: `arch/riscv/Kconfig`

```config
config RISCV_VDSO_PERCPU_CACHE
    bool "RISC-V vDSO per-CPU timestamp cache"
    depends on GENERIC_TIME_VSYSCALL
    help
      Enable per-CPU timestamp caching in vDSO to reduce
      expensive CSR_TIME reads. This can improve performance
      of clock_gettime() by 2-5x in high-frequency scenarios
      (e.g., AI workloads, profiling).

      The cache is updated by a kernel timer every 1ms (configurable).
      User-space checks cache freshness and falls back to CSR_TIME
      read if cache is stale.

      If unsure, say N.

config RISCV_VDSO_CACHE_UPDATE_INTERVAL
    int "vDSO cache update interval (microseconds)"
    depends on RISCV_VDSO_PERCPU_CACHE
    range 100 10000
    default 1000
    help
      Interval at which the kernel updates per-CPU timestamp cache.
      Lower values = better accuracy but higher kernel overhead.
```

---

## 8. 与原有方案的关系

### 8.1 与 "时间戳缓存机制技术方案" 的关系

原有方案（`RISC-V_VDSO_Timestamp_Cache_Proposal.md`）提出的是：
- **用户态 TLS 缓存** + **fast counter**（CYCLE CSR）
- 需要 opt-in API
- 语义正确性依赖 fast counter

本方案（**Per-CPU VVAR 缓存**）的优势：
- **内核侧更新**，用户态只读 → 无 TLS 问题
- **不需要 fast counter** 来推进时间 → 内核定期更新保证推进
- **对现有 API 透明** → 无需修改 glibc/应用
- **可配置** → 可根据场景调整精度/性能权衡

### 8.2 组合使用

两种方案可以**组合使用**：

1. **Per-CPU VVAR 缓存**：提供基础的性能优化（2-5×）
2. **用户态 TLS 缓存**（opt-in）：为极高频场景提供进一步优化（5-10×）

---

## 9. 总结

### 9.1 推荐实施路径

```
┌─────────────────────────────────────────────────────────────┐
│                    实施路径                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Phase 1: Per-CPU VVAR 缓存 (本文方案)                       │
│  ├── 复杂度: 中                                             │
│  ├── 收益: 2-5× 性能提升                                    │
│  ├── 精度: µs 级                                            │
│  └── 上游化: 可行                                            │
│                                                             │
│  Phase 2: 统一编译单元 + Ztso 优化 (之前分析)               │
│  ├── 复杂度: 低                                             │
│  ├── 收益: 额外 1.5-2×                                      │
│  └── 与 Phase 1 叠加                                         │
│                                                             │
│  Phase 3 (可选): 用户态 TLS 缓存 (原有方案)                  │
│  ├── 复杂度: 高                                             │
│  ├── 收益: 额外 2-3× (极高频场景)                           │
│  └── 需要 fast counter 支持                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 预期累积性能提升

| 阶段 | 优化项 | 累积提升 |
|------|--------|----------|
| 基线 | 现状 | 1.0× |
| + Phase 1 | Per-CPU VVAR 缓存 | 2-5× |
| + Phase 2 | 编译单元 + Ztso | 3-10× |
| + Phase 3 | 用户态 TLS 缓存 | 6-30× |

### 9.3 立即可行的下一步

1. **实现 Per-CPU VVAR 缓存原型**
   - 扩展 `struct vdso_time_data`
   - 添加内核定时器
   - 实现 vDSO 快速路径

2. **验证可行性**
   - 编写测试用例
   - 性能基准测试
   - 精度验证

3. **评估上游化**
   - 与内核社区讨论
   - 提交 RFC patch

---

*文档版本: 1.0*
*日期: 2026-01-11*
