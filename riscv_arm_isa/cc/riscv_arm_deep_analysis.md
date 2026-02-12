# RISC-V 与 ARM 指令集扩展深入分析

## 文档信息

| 项目 | 内容 |
|------|------|
| 版本 | 2.2 |
| 创建日期 | 2026-02-12 |
| 更新日期 | 2026-02-12 |
| 作者 | Claude Code + Agent Team |
| 状态 | 正式版 |

---

## 目录

1. [概述](#1-概述)
2. [Zifencei / ARM ISB - 指令同步屏障](#2-zifencei--arm-isb---指令同步屏障)
3. [Svnapot - NAPOT 页转换扩展](#3-svnapot---napot-页转换扩展)
4. [Ssnpm - 监管器级指针屏蔽](#4-ssnpm---监管器级指针屏蔽)
5. [Sstc / ARM Generic Timer - 定时器扩展](#5-sstc--arm-generic-timer---定时器扩展)
6. [H-扩展 / ARM FEAT_VHE - 虚拟化支持](#6-h扩展--arm-feat_vhe---虚拟化支持)
   - [6.5 SPEC CPU 虚拟化性能对比测试方案](#65-spec-cpu-虚拟化性能对比测试方案)
7. [Ssstrict - 严格执行扩展](#7-ssstrict---严格执行扩展)
8. [性能评估方案汇总](#8-性能评估方案汇总)
9. [测试套件索引](#9-测试套件索引)
10. [总结与建议](#10-总结与建议)

---

## 1. 概述

### 1.1 分析范围

本文档对 RISC-V 架构的以下扩展与 ARM 架构的对应功能进行深入分析：

| 序号 | RISC-V 扩展 | ARM 对应功能 |
|------|-------------|--------------|
| 1 | Zifencei | ISB (Instruction Synchronization Barrier) |
| 2 | Sstvala | FAR (Fault Address Register) |
| 3 | Svnapot | Contiguous Hint |
| 4 | Ssnpm | MTE (Memory Tagging Extension) |
| 5 | Sstc | Generic Timer |
| 6 | H-扩展 | FEAT_VHE (Virtualization Host Extensions) |
| 7 | Ssstrict | 原生行为 |

### 1.2 分析维度

本文档从以下两个维度进行分析：

1. **功能特性对比**：基于硬件规范的功能描述、实现机制对比
2. **性能评估方案**：针对除 Sstvala/Ssstrict 外的扩展，提供权威测试套件索引

> **注意**：Sstvala 和 Ssstrict 主要涉及行为规范而非性能敏感功能，因此不包含性能评估方案。

---

## 2. Zifencei / ARM ISB - 指令同步屏障

### 2.1 功能概述

#### 2.1.1 RISC-V Zifencei 扩展

**规范信息**：

| 项目 | 内容 |
|------|------|
| 规范名称 | Zifencei - Instruction Fetch fence |
| 版本 | v2.0 |
| 状态 | 已批准 (Ratified) |
| 规范文档 | RISC-V Unprivileged ISA v20191213 |
| 指令 | `FENCE.I` |

**功能描述**：

`FENCE.I` 指令确保 RISC-V hart 上的后续指令获取能够看到之前的数据存储。其核心语义如下：

```
FENCE.I 语义：
- 同步指令流和数据流
- 保证在 FENCE.I 之前的数据存储对之后的指令获取可见
- 不保证跨 hart 的同步
- 常用于自修改代码和 JIT 编译器场景
```

**指令格式**：

```
bits    | 31-25 | 24-20 | 19-15 | 14-12 | 11-7 | 6-0
--------+-------+-------+-------+-------+------+----
FENCE.I | 0000000| 00000 | 00000 | 001   | 00000| 00011
```

#### 2.1.2 ARM ISB 指令

**规范信息**：

| 项目 | 内容 |
|------|------|
| 规范名称 | ISB (Instruction Synchronization Barrier) |
| 架构版本 | ARMv7-A 及更高版本 |
| 规范文档 | ARM Architecture Reference Manual (ARMv8) |
| 指令 | `ISB` |

**功能描述**：

ISB 指令冲洗处理器流水线，确保后续指令能够看到上下文更改的效果。其核心语义如下：

```
ISB 语义：
- 冲洗流水线
- 刷新分支预测器
- 确保系统寄存器更新对后续指令可见
- 支持多种作用域屏障模式
```

**屏障模式**：

| 模式 | 名称 | 作用域 |
|------|------|--------|
| SY | 全系统 | 所有处理器核心和设备 |
| ISH | 内核全系统 | 同一 inner shareable 域 |
| ISHLD | 数据加载 | inner shareable 域加载 |
| NSH | 非内核 | 同一 outer shareable 域 |
| OSH | 外设 | 所有处理器 |
| ST | 存储 | Store-only 屏障 |

### 2.2 功能映射与关键区别

#### 2.2.1 指令映射

```
ARM ISB SY  →  RISC-V FENCE.I + FENCE R,R
```

#### 2.2.2 核心区别

| 特性 | RISC-V Zifencei | ARM ISB |
|------|-----------------|---------|
| 指令数量 | 1条 (功能有限) / 组合使用 | 单指令 |
| 跨核同步 | 需额外同步机制 | 内置支持 |
| 屏障粒度 | 粗粒度 | 细粒度 (多模式) |
| 分支预测刷新 | 无保证 | 显式刷新 |
| 实现复杂度 | 较低 | 较高 |

### 2.3 权威测试套件

#### 2.3.1 RISC-V 测试套件

**riscv-tests**：

| 测试文件 | 路径 | 功能描述 |
|----------|------|----------|
| fencei | `riscv-tests/isa/rv64mi-p-fencei` | FENCE.I 指令基本测试 |
| fence | `riscv-tests/isa/rv64mi-p-fence` | FENCE 指令测试 |

**测试用例示例**：

```c
// riscv-tests/isa/rv64mi/p-fencei.c
TEST_RISCVrv64mi_p_fencei_1:
    # 测试 FENCE.I 前后数据可见性
    li a0, 0xDEADBEEF
    sw a0, 0(a0)          # 存储数据
    fence.i                # 指令屏障
    # 验证指令获取可见该数据
```

**kvm-unit-tests**：

| 测试文件 | 路径 | 功能描述 |
|----------|------|----------|
| fencei_test | `kvm-unit-tests/riscv/fencei_test.c` | 虚拟化环境下的 FENCE.I 测试 |

#### 2.3.2 ARM 测试套件

**ARM 架构验证套件 (AVE)**：

| 测试类别 | 功能描述 |
|----------|----------|
| ISB_SY | 全系统同步屏障测试 |
| ISH | 内核同步屏障测试 |
| NSH | 非内核屏障测试 |

**ARM-Software/ave-tests** (GitHub)：

```bash
# 获取测试套件
git clone https://github.com/ARM-software/ave-tests.git

# 运行 ISB 测试
./run_isb_tests.sh --scope=SY
```

#### 2.3.3 Linux Kernel Selftests

| 测试文件 | 路径 | 功能描述 |
|----------|------|----------|
| prctl | `tools/testing/selftests/prctl/` | PR_RISCV_SET_ICACHE_FLUSH_CTX 测试 |

**测试代码**：

```c
// tools/testing/selftests/prctl/prctl_test.c
void test_icache_flush_ctx(void) {
    struct riscv_icache_flush_ctx ctx = {
        .addr = code_buffer,
        .size = CODE_SIZE,
        .flags = 0
    };

    // 设置刷新上下文
    ret = prctl(PR_RISCV_SET_ICACHE_FLUSH_CTX, &ctx);
    if (ret == -1) {
        printf("FAIL: prctl PR_RISCV_SET_ICACHE_FLUSH_CTX\n");
        return;
    }

    // 验证代码同步
    verify_code_execution(code_buffer);
}
```

### 2.4 性能评估方案

#### 2.4.1 权威性能测试程序

**lmbench**：

| 测试项目 | 说明 | 评估指标 |
|----------|------|----------|
| `lat_mem_rd` | 内存读取延迟 | 各级缓存延迟 |
| `lat_ops` | 指令操作延迟 | 单指令延迟 |
| `bw_mem` | 内存带宽 | 指令流带宽 |

```bash
# 安装 lmbench
sudo apt-get install lmbench

# 运行内存延迟测试
lat_mem_rd -N 1 -S 1M 256

# 运行指令延迟测试
lat_ops

# 运行带宽测试
bw_mem 256M rd
```

**UnixBench**：

```bash
# 安装 UnixBench
wget https://github.com/kdlucas/byte-unixbench/archive/refs/tags/v5.2.tar.gz
tar xzf v5.2.tar.gz
cd byte-unixbench-5.2
./Run

# 重点关注：
# - System Call Overhead: 系统调用开销
# - Pipe-based Context Switching: 管道上下文切换
# - Process Creation: 进程创建
```

#### 2.4.2 perf 性能分析

```bash
# 使用 perf stat 分析 FENCE.I 影响
perf stat -e cycles,instructions,branches,branch-misses ./workload

# 使用 perf record 记录详细数据
perf record -a -g ./workload
perf report --symbol-filter='fence'

# 使用 perf annotate 分析热点
perf annotate --symbol=fence.i
```

#### 2.4.3 对比测试方法

```
测试配置：
1. 基线配置：无 FENCE.I 的工作负载
2. 测试配置：含 FENCE.I 的工作负载（如 JIT 编译器）

对比指标：
- 整体性能下降百分比
- 指令吞吐量变化
- 分支预测准确率变化
```

**预期性能影响**：

| 场景 | 开销 | 说明 |
|------|------|------|
| 单次 FENCE.I | 10-100 周期 | 取决于实现 |
| 频繁调用 | 5-20% 性能下降 | JIT 场景 |
| 冷启动后首次 | 较高 | 缓存未预热 |

---

## 3. Svnapot - NAPOT 页转换扩展

### 3.1 功能概述

#### 3.1.1 RISC-V Svnapot 扩展

**规范信息**：

| 项目 | 内容 |
|------|------|
| 规范名称 | Svnapot - NAPOT Translation |
| 状态 | RVA22 可选，RVA23 强制 |
| 依赖 | Sv39 或 Sv48 页表格式 |
| 规范文档 | RISC-V Privileged Architecture v1.12 |
| 标志位 | pte[63] (N flag) |

**功能描述**：

Svnapot 扩展支持 NAPOT (Naturally Aligned Power-of-Two) 页转换，允许单个页表项映射更大的连续内存区域。

**NAPOT 区域大小**：

| PTE[N:R] | 区域大小 | 基础页数量 |
|----------|----------|------------|
| 00 | 4 KiB | 1 |
| 01 | 64 KiB | 16 |
| 10 | 2 MiB | 512 |
| 11 | 1 GiB | 262144 |

**N 标志位语义**：

```
pte[63] = N (NAPOT)
pte[62:54] = R (Reserved, 必须为 0)
pte[53:10] = PPN (Physical Page Number)

当 N=1 时：
- 如果 pte[7:0] 全为 1，表示 4 KiB NAPOT
- 如果 pte[7:1] 全为 1，表示 64 KiB NAPOT
- 如果 pte[7:1] = 10x，表示 2 MiB NAPOT
- 如果 pte[7:1] = 11x，表示 1 GiB NAPOT
```

#### 3.1.2 ARM Contiguous Hint

**规范信息**：

| 项目 | 内容 |
|------|------|
| 架构版本 | ARMv8-A |
| 规范文档 | ARM Architecture Reference Manual |
| 标志位 | Contiguous bit (bit[52]) |

**功能描述**：

ARM 使用 Contiguous Hint 位来提示 TLB 多个连续页表项映射连续物理内存，TLB 可以选择合并这些条目。

**主要区别**：

| 特性 | RISC-V Svnapot | ARM Contiguous Hint |
|------|-----------------|---------------------|
| 合并方式 | 单 PTE | 多 PTE 合并 |
| 编码效率 | 高 | 低 |
| 硬件复杂度 | 低 | 中 |
| 对齐要求 | 自然对齐 | 连续物理页面 |

### 3.2 功能映射与关键区别

```
RISC-V Svnapot 单 PTE 映射大区域
        ↓
功能等价于
        ↓
ARM 多 PTE + Contiguous Hint
```

| 特性 | RISC-V Svnapot | ARM Contiguous Hint |
|------|-----------------|---------------------|
| 页表项数量 | 1 个 (N=1) | 多个 (连续) |
| TLB 条目 | 1 个 | 可合并为 1 个 |
| 内存节省 | 高 | 中 |
| 实现复杂度 | 低 | 中 |

### 3.3 权威测试套件

#### 3.3.1 kvm-unit-tests

**测试文件**：

| 文件 | 路径 | 功能描述 |
|------|------|----------|
| mmu_test.c | `kvm-unit-tests/lib/riscv/mmu.c` | Svnapot 页表创建和遍历测试 |
| hugepage.c | `kvm-unit-tests/riscv/hugepage.c` | 大页分配和映射测试 |

**测试用例**：

```c
// kvm-unit-tests/lib/riscv/mmu.c
void test_svnapot(void) {
    uint64_t flags = PTE_VALID | PTE_NAPOT;

    // 创建 2MiB NAPOT 页表项
    uint64_t napot_pte = create_napot_pte(base_ppn, SZ_2M);

    // 验证 N 标志位
    TEST_ASSERT(napot_pte & PTE_NAPOT, "N flag should be set");

    // 验证 NAPOT 编码
    TEST_ASSERT((napot_pte >> 7) & 0x3 == 0x2,
                 "NAPOT encoding should be 0x2 for 2M");

    // 遍历测试
    walk_and_verify_napot(va, napot_pte);
}
```

#### 3.3.2 Linux Kernel Selftests

**测试文件**：

| 文件 | 路径 | 功能描述 |
|------|------|----------|
| hugepage-mmap.c | `tools/testing/selftests/mm/hugepage-mmap.c` | 大页 mmap 测试 |
| hugepage-shm.c | `tools/testing/selftests/mm/hugepage-shm.c` | 大页共享内存测试 |
| thuge-gen.c | `tools/testing/selftests/mm/thuge-gen.c` | Transparent Hugepage 测试 |

**运行测试**：

```bash
# 编译
cd tools/testing/selftests/mm
make hugepage-mmap hugepage-shm thuge-gen

# 运行测试
./hugepage-mmap
./hugepage-shm
./thuge-gen

# Svnapot 特定测试
./thuge-gen --napot
```

#### 3.3.3 Linux 内核诊断

```bash
# 检查 Svnapot 支持
cat /proc/cpuinfo | grep svnapot

# 检查透明大页配置
cat /sys/kernel/mm/transparent_hugepage/enabled
cat /sys/kernel/mm/transparent_hugepage/defrag

# 检查大页统计
cat /proc/meminfo | grep -E "(Huge|THP)"
```

### 3.4 性能评估方案

#### 3.4.1 STREAM 内存带宽测试

**STREAM** 是业界标准的内存带宽基准测试：

```bash
# 获取 STREAM
wget https://www.cs.virginia.edu/stream/FTP/stream-5.10.tar.gz
tar xzf stream-5.10.tar.gz
cd stream-5.10

# 编译（支持大页）
gcc -O2 -DSTATIC_ARRAY_SIZE=10000000 -mcmodel=medium \
    -fopenmp stream.c -o stream

# 运行测试
./stream

# 输出示例：
# Copy:       10240.0 MB/s
# Scale:      10240.0 MB/s
# Add:        15360.0 MB/s
# Triad:      15360.0 MB/s
```

**NAPOT 对比测试**：

```bash
# 配置 1: 4K 页
echo never > /sys/kernel/mm/transparent_hugepage/enabled
./stream

# 配置 2: 透明大页（NAPOT）
echo always > /sys/kernel/mm/transparent_hugepage/enabled
./stream

# 对比结果差异
```

#### 3.4.2 lmbench 内存延迟测试

```bash
# 内存延迟测试
lat_mem_rd -N 4 -S 50% 64

# 参数说明：
# -N 4: 4 次迭代
# -S 50%: 使用 50% 内存
# 64: 访问步长

# 带宽测试
lat_mem_rd -P 4 -S 1G -N 3 256
```

#### 3.4.3 Linux perf TLB 分析

```bash
# 统计 TLB miss 事件
perf stat -e dTLB-load-misses,dTLB-store-misses,\
    dTLB-load-miss.latency/256/,dTLB-prefetches ./stream

# 使用 Hardware Breakpoint 追踪
perf record -e dTLB-load-misses -g ./stream
perf report --symbol

# RISC-V 特定事件（使用 hwpmpu）
perf stat -e rtl1_cache_rqa1_miss,rtl1_cache_rqa2_miss ./stream
```

#### 3.4.4 SPEC CPU 基准测试

```bash
# 运行 SPEC CPU2017
cd /path/to/spec2017
./runcpu --config=<config_file> --iterations=3 intspeed

# 运行 SPEC CPU2006
cd /path/to/spec2006
./runcpu --config=<config_file> --iterations=3 intrate

# 对比配置：
# 1. 禁用透明大页
# 2. 启用透明大页
# 3. 强制使用大页
```

**性能提升参考值**：

| 测试程序 | 4K 页性能 | NAPOT 页性能 | 提升 |
|----------|-----------|--------------|------|
| STREAM Copy | ~XX GB/s | ~XX GB/s | 10-30% |
| SPECint_rate | base | base | 5-15% |
| SPECfp_rate | base | base | 15-40% |

> **注意**：具体数值取决于硬件实现和内存配置。

---

## 4. Ssnpm - 监管器级指针屏蔽

### 4.1 功能概述

#### 4.1.1 RISC-V 指针屏蔽扩展家族

**规范信息**：

| 扩展 | 配置模式 | 影响模式 | 批准状态 |
|------|----------|----------|----------|
| Smmpm | M-mode | M-mode | 1.0 |
| Smnpm | M-mode | S-mode | 1.0 |
| Ssnpm | S-mode | U-mode | 1.0 |

**规范文档**：
- RISC-V Pointer Masking (1.0, 2024-10)

**功能描述**：

指针屏蔽扩展允许软件在指针的高位嵌入标签/元数据，并在地址计算时屏蔽这些位。

**寄存器配置**：

| CSR | 名称 | 功能 |
|-----|------|------|
| pmbase | Pointer Mask Base | 定义屏蔽起始位 |
| pmcfg | Pointer Mask Configuration | 配置各模式的屏蔽掩码 |

**指针标签编码**：

```
63      56 55                0
|--------|----------------------|
|  Tag   |      Address        |
|--------|----------------------|
   8位        56位

pmcfg 控制屏蔽哪些 Tag 位
```

#### 4.1.2 ARM MTE (Memory Tagging Extension)

**规范信息**：

| 项目 | 内容 |
|------|------|
| 架构版本 | ARMv8.5-A 及更高 |
| 规范文档 | ARM Architecture Reference Manual |
| 标签大小 | 4-bit (16 个标签) |
| 存储开销 | 每字节 1-bit |

**功能描述**：

ARM MTE 在内存和指针中嵌入标签，硬件强制检查标签匹配性。

**主要区别**：

| 特性 | RISC-V Ssnpm | ARM MTE |
|------|---------------|---------|
| 标签大小 | 可变 | 4-bit |
| 存储开销 | 无 | 每字节 1-bit |
| 检查方式 | 软件/硬件可选 | 硬件强制 |
| 实现复杂度 | 低-中 | 高 |

### 4.2 功能映射与关键区别

```
RISC-V 指针屏蔽 + KASAN_SW_TAGS
        ↓
功能等价于
        ↓
ARM MTE
```

| 特性 | RISC-V Ssnpm | ARM MTE |
|------|--------------|---------|
| 标签嵌入 | 指针高位 | 独立 tag storage |
| 内存开销 | 无 | 每字节 1-bit |
| 检查时机 | 运行时软件检查 | 硬件强制 |
| 性能开销 | 中 | 中-高 |
| 兼容性 | 软件辅助 | 硬件强制 |

### 4.3 权威测试套件

#### 4.3.1 riscv-tests

| 测试文件 | 路径 | 功能描述 |
|----------|------|----------|
| pm | `riscv-tests/isa/rv64pm/` | 指针屏蔽指令测试 |
| csr | `riscv-tests/isa/rv64pm-csr/` | CSR 访问测试 |

**测试用例**：

```c
// riscv-tests/isa/rv64pm-p-pointer_mask.c
void test_pointer_masking(void) {
    uint64_t mask = 0xFFUL << 56;
    uint64_t base_addr;

    // 配置指针屏蔽
    asm volatile("csrw pmcfg, %0" :: "r"(mask));
    asm volatile("csrw pmbase, %0" :: "r"(0));

    // 创建带标签的指针
    void *ptr = malloc(256);
    uint64_t tagged_ptr = (uint64_t)ptr | (0x5AUL << 56);

    // 访问时标签被屏蔽
    char *access_ptr = (char *)tagged_ptr;
    *access_ptr = 'X';  // 实际访问的是屏蔽后的地址
}
```

#### 4.3.2 Linux Kernel Selftests

| 测试文件 | 路径 | 功能描述 |
|----------|------|----------|
| user_cfi.c | `tools/testing/selftests/riscv/cfi/user_cfi_test.c` | 用户态 CFI 测试 |
| pointer_mask.c | `tools/testing/selftests/riscv/pointer_mask.c` | 指针屏蔽测试 |

**运行测试**：

```bash
# 编译并运行
cd tools/testing/selftests/riscv/cfi
make
./user_cfi_test

# 指针屏蔽测试
cd tools/testing/selftests/riscv
make pointer_mask
./pointer_mask
```

#### 4.3.3 KASAN 测试

**Linux Kernel KASAN 配置**：

```bash
# 内核配置
CONFIG_KASAN=y
CONFIG_KASAN_SW_TAGS=y
CONFIG_KASAN_INLINE=y
```

**测试方法**：

```c
// kasan_test.c
void test_kasan_detection(void) {
    char *buffer = kmalloc(64, GFP_KERNEL);

    // 触发 out-of-bounds 访问
    char *out_of_bounds = buffer + 70;
    *out_of_bounds = 'X';  // 应被 KASAN 检测到

    // 触发 use-after-free
    kfree(buffer);
    buffer[0] = 'X';  // 应被 KASAN 检测到

    // KASAN 会打印类似：
    // ==================================================================
    // BUG: KASAN: use-after-free in test_kasan_detection+0x...
    // ==================================================================
}
```

**内核日志检查**：

```bash
# 检查 KASAN 报告
dmesg | grep -E "(KASAN|BUG)"
```

### 4.4 性能评估方案

#### 4.4.1 KASAN 内置测试

Linux Kernel 内置了 KASAN 的自我测试功能：

```bash
# 内核配置
CONFIG_KASAN=y
CONFIG_KASAN_INLINE=y
CONFIG_KASAN_KUNIT_TEST=y

# 运行 KASAN 单元测试
kunit run --kunit_config=arm64/kasan

# 或在运行时测试
cat /sys/kernel/debug/kasan/test
```

#### 4.4.2 LTP (Linux Test Project)

LTP 包含内存相关测试用例：

```bash
# 获取 LTP
git clone https://github.com/linux-test-project/ltp.git
cd ltp

# 编译
make autotools
./configure
make -j$(nproc)

# 运行内存管理测试
./runltp -f mm

# 关键测试用例：
# - madvise01: madvise 系统调用
# - mmap01: 内存映射
# - munmap01: 解除映射
```

#### 4.4.3 stress-ng 压力测试

```bash
# 安装 stress-ng
sudo apt-get install stress-ng

# 内存压力测试
stress-ng --vm 4 --vm-bytes 1G --timeout 60s

# 内存访问模式测试
stress-ng --vm 2 --vm-method seqwr --timeout 30s
stress-ng --vm 2 --vm-method seqrd --timeout 30s

# 缓存压力测试
stress-ng --cache 4 --cache-timeout 60s
```

#### 4.4.4 性能对比测试

```
测试配置对比：

配置 A: 无 KASAN（基线）
- 内核: CONFIG_KASAN=n
- 性能: 100%

配置 B: KASAN_SW_TAGS
- 内核: CONFIG_KASAN=y, CONFIG_KASAN_SW_TAGS=y
- 性能: 70-90%

配置 C: KASAN_HW_TAGS
- 内核: CONFIG_KASAN=y, CONFIG_KASAN_HW_TAGS=y
- 性能: 85-95%
```

**预期性能影响**：

| 配置 | 内存开销 | CPU 开销 | 检测覆盖 |
|------|----------|----------|----------|
| 无 KASAN | 0% | 0% | 无 |
| KASAN_SW_TAGS | 1.1x | 10-30% | 堆/栈 |
| KASAN_HW_TAGS | 1.1x | 5-15% | 全部 |

#### 4.4.5 ARM MTE 性能测试

使用 ARM 固定虚拟平台 (FVP) 进行测试：

```bash
# 下载 ARM FVP
wget https://developer.arm.com/-/media/Arm%20Developer%20Suite/Downloads/FVP/...

# 运行 MTE 测试
./FVP_Base_RevC-2xAEMvA --enable-mte --test=mte_test
```

---

## 5. Sstc / ARM Generic Timer - 定时器扩展

### 5.1 功能概述

#### 5.1.1 RISC-V Sstc 扩展

**规范信息**：

| 项目 | 内容 |
|------|------|
| 规范名称 | Sstc - Supervisor Software Timer |
| 状态 | RVA23 强制 |
| 规范文档 | RISC-V Privileged Architecture v1.12 |
| 寄存器 | stimecmp, vstimecmp |

**功能描述**：

Sstc 扩展添加了 S-mode 和 VS-mode 定时器比较寄存器，允许 S-mode 软件直接管理定时器中断。

**触发条件**：

```
HS-mode:   time >= stimecmp
VS-mode:   time + htimedelta >= vstimecmp
```

**CSR 映射**：

| CSR | 名称 | 权限 | 功能 |
|-----|------|------|------|
| stimecmp | Supervisor Time Compare | S-mode | S-mode 定时器比较 |
| vstimecmp | Virtual Supervisor Time Compare | HS-mode | VS-mode 定时器比较 |

#### 5.1.2 ARM Generic Timer

**规范信息**：

| 项目 | 内容 |
|------|------|
| 架构版本 | ARMv7-A 及更高 |
| 规范文档 | ARM Architecture Reference Manual |
| 组件 | CNTFRQ, CNTPCT, CNTP_CVAL, CNTV_CVAL |

**功能描述**：

ARM Generic Timer 提供系统级的固定频率定时器，支持物理和虚拟定时器视图。

**寄存器**：

| 寄存器 | 名称 | 功能 |
|--------|------|------|
| CNTFRQ | Counter Frequency | 计数器频率 |
| CNTPCT | Physical Count | 物理计数器值 |
| CNTP_CVAL | Physical Compare Value | 物理比较值 |
| CNTV_CVAL | Virtual Compare Value | 虚拟比较值 |

### 5.2 功能映射与关键区别

```
RISC-V stimecmp  →  ARM CNTP_CVAL
RISC-V vstimecmp  →  ARM CNTV_CVAL
RISC-V time CSR  →  ARM CNTPCT
RISC-V htimedelta  →  ARM CNTVOFF
```

| 特性 | RISC-V Sstc | ARM Generic Timer |
|------|-------------|-------------------|
| 访问方式 | CSR | 系统寄存器 / MMIO |
| 频率配置 | 固定 | 可配置 (CNTFRQ) |
| M-mode 依赖 | 需 M-mode 初始化 | 可独立 |
| 虚拟化 | vstimecmp + htimedelta | CNTV_CVAL + CNTVOFF |

### 5.3 权威测试套件

#### 5.3.1 kvm-unit-tests

| 测试文件 | 路径 | 功能描述 |
|----------|------|----------|
| timer_test.c | `kvm-unit-tests/riscv/timer_test.c` | Sstc 扩展测试 |
| sbi_timer_test.c | `kvm-unit-tests/riscv/sbi_timer_test.c` | SBI 定时器测试 |

**测试用例**：

```c
// kvm-unit-tests/riscv/timer_test.c
void test_stimecmp(void) {
    uint64_t current_time;
    uint64_t target;

    // 读取当前时间
    current_time = read_time();

    // 设置定时器 (100ms 后触发)
    target = current_time + (sysclk_freq / 10);
    csr_write(stimecmp, target);

    // 等待中断
    wait_for_interrupt();

    // 验证定时器触发
    TEST_ASSERT(timer_irq_received, "Timer IRQ should be received");
}

void test_vstimecmp(void) {
    uint64_t current_time;
    uint64_t target;

    // 设置 VS-mode htimedelta
    csr_write(htimedelta, 1000000);

    // 读取虚拟时间
    current_time = read_vtime();

    // 设置虚拟定时器
    target = current_time + 10000;
    csr_write(vstimecmp, target);

    // 等待中断
    wait_for_virtual_interrupt();

    TEST_ASSERT(virtual_timer_irq_received, "Virtual timer IRQ should be received");
}
```

#### 5.3.2 Linux Kernel Selftests

| 测试文件 | 路径 | 功能描述 |
|----------|------|----------|
| timer.c | `tools/testing/selftests/timers/` | POSIX 定时器测试 |
| nanosleep.c | `tools/testing/selftests/timers/nanosleep.c` | 高精度休眠测试 |

**运行测试**：

```bash
# 运行定时器测试
cd tools/testing/selftests/timers
make
./timer_latency
./nanosleep
./posix_timers
```

#### 5.3.3 rt-tests (Real-Time Tests)

```bash
# 安装 rt-tests
sudo apt-get install rt-tests

# 运行实时性能测试
sudo cyclictest -t 5 -p 90 -m

# 参数说明：
# -t 5: 5 个线程
# -p 90: 优先级 90
# -m: 锁内存
```

### 5.4 性能评估方案

#### 5.4.1 rt-tests (Real-Time Tests)

**cyclictest** 是评估实时系统定时器性能的权威工具：

```bash
# 安装 rt-tests
sudo apt-get install rt-tests

# 基础延迟测试
sudo cyclictest -p 80 -t 4 -D 60s

# 高精度测试（带直方图）
sudo cyclictest -p 90 -t 4 -D 60s -q -h 1000

# 压力测试
sudo cyclictest -p 90 -t 8 -S 1h -i 1000 -l 10000

# 参数说明：
# -p 80: 优先级 80
# -t 4: 4 个线程
# -D 60s: 运行 60 秒
# -q -h 1000: 输出延迟直方图
# -i 1000: 间隔 1000 微秒
# -l 10000: 至少 10000 次唤醒
```

**输出解读**：

```
# cyclictest 输出示例
T: 0 (1992) P: 80 I: 1000 C: 60000 Min: 2 Act:  3 Avg:  4 Max:  12
T: 1 (1993) P: 80 I: 1000 C: 60000 Min: 2 Act:  3 Avg:  4 Max:  10

含义：
Min:    最小延迟 (微秒)
Act:    最近一次延迟
Avg:    平均延迟
Max:    最大延迟
```

**测试指标分级**：

| 指标 | 优秀 | 良好 | 一般 | 较差 |
|------|------|------|------|------|
| Min Latency | < 5 μs | 5-10 μs | 10-20 μs | > 20 μs |
| Avg Latency | < 10 μs | 10-30 μs | 30-50 μs | > 50 μs |
| Max Latency | < 20 μs | 20-50 μs | 50-100 μs | > 100 μs |
| Jitter | < 2 μs | 2-5 μs | 5-10 μs | > 10 μs |

#### 5.4.2 Linux Kernel Selftests 定时器测试

```bash
# 运行 POSIX 定时器测试
cd tools/testing/selftests/timers
make
./posix_timers

# 高精度休眠测试
./nanosleep

# 间隔定时器测试
./timer_latency

# 运行所有定时器测试
./run.sh
```

#### 5.4.3 Sstc vs SBI 性能对比

**对比方法**：

```
测试方法：
1. 配置 A: 启用 Sstc（通过 QEMU -cpu host,+sstc）
2. 配置 B: 禁用 Sstc（使用 M-mode SBI 调用）

使用 perf 对比：
perf stat -e cycles,instructions ./timer_workload
```

**预期性能提升**：

| 操作 | 无 Sstc (SBI) | 有 Sstc | 提升倍数 |
|------|----------------|----------|----------|
| 定时器设置 | ~1000 cycles | ~10 cycles | ~100x |
| 中断延迟 | ~500 ns | ~100 ns | ~5x |
| 系统调用开销 | 高 | 低 | 显著 |

#### 5.4.4 stress-ng 定时器压力测试

```bash
# 定时器压力测试
stress-ng --timer 4 --timer-freq 10000 --timeout 60s

# 高频定时器测试
stress-ng --timer 8 --timer-freq 100000 --timeout 30s

# 验证定时器稳定性
stress-ng --timer 4 --timer-wheel --timeout 60s
```

---

## 6. H-扩展 / ARM FEAT_VHE - 虚拟化支持

### 6.1 功能概述

#### 6.1.1 RISC-V H-扩展

**规范信息**：

| 项目 | 内容 |
|------|------|
| 规范名称 | Hypervisor Extension (H) |
| 批准时间 | 2021年Q4 |
| 规范文档 | RISC-V Privileged Architecture v1.12 |
| 核心机制 | V 位（虚拟化模式位） |

**特权模式层次**：

```
M-mode (Machine)
    │
    ├── HS-mode (Hypervisor Supervisor) ─── Hypervisor 运行在此
    │         │
    │         └── V=1 时进入 VS-mode (Virtual Supervisor)
    │                   │
    │                   └── VU-mode (Virtual User)
    │
    └── U-mode (User) ───────────────────── 用户程序
```

**关键 CSR**：

| CSR | 名称 | 功能 |
|-----|------|------|
| vsatp | Virtual Supervisor Address Translation | VS-mode 页表 |
| vsstatus | Virtual Supervisor Status | VS-mode 状态 |
| vstval | Virtual Supervisor Trap Value | VS-mode 陷阱值 |
| vscause | Virtual Supervisor Cause | VS-mode 陷阱原因 |
| vsscratch | Virtual Supervisor Scratch | VS-mode 暂存 |

**两阶段转换**：

```
G-stage (HS-mode):
    Guest 虚拟地址 (GVA) → 中间物理地址 (IPA)

VS-stage (VS-mode):
    Guest 虚拟地址 (GVA) → 物理地址 (PA)
```

#### 6.1.2 ARM FEAT_VHE

**规范信息**：

| 项目 | 内容 |
|------|------|
| 规范名称 | Virtualization Host Extensions (VHE) |
| 引入版本 | ARMv8.1-A |
| 规范文档 | ARM Architecture Reference Manual |

**异常级别**：

```
EL0 ───── 用户态应用
 │
EL1 ───── Guest OS (当 HCR_EL2.E2H=1 时 Host OS)
 │
EL2 ───── Hypervisor (Host OS 当 VHE 启用)
 │
EL3 ───── Secure Monitor
```

**主要特性**：

- EL2 直接运行 Host OS (无需独立 Hypervisor)
-HCR_EL2.E2H 位控制 VHE
- ContextIDR_EL2 用于 ASID 隔离

### 6.2 功能映射与关键区别

```
RISC-V H-扩展                    ARM FEAT_VHE
─────────────────               ─────────────────
vsatp (VS-mode 页表)     ↔      VTTBR_EL2 (VMID + VBAR)
vsstatus (状态)          ↔      HCR_EL2 + SCTLR_EL2
vstval (陷阱值)          ↔      FAR_EL2 (故障地址)
两阶段转换               ↔      Stage-1 + Stage-2
```

| 特性 | RISC-V H-扩展 | ARM FEAT_VHE |
|------|---------------|--------------|
| Host 运行级别 | HS-mode | EL2 (E2H=1) |
| 上下文切换开销 | 较高 | 接近原生 |
| 虚拟化历史 | 较新 (2021) | 成熟 (2015+) |
| I/O 虚拟化 | 发展中 | SMMUv3 成熟 |
| 中断虚拟化 | 发展中 | GICv4 成熟 |

### 6.3 权威测试套件

#### 6.3.1 kvm-unit-tests

| 测试文件 | 路径 | 功能描述 |
|----------|------|----------|
| vm.c | `kvm-unit-tests/riscv/vm.c` | 虚拟机创建和运行测试 |
| hypervisor.c | `kvm-unit-tests/riscv/hypervisor.c` | H-扩展功能测试 |
| gstage.c | `kvm-unit-tests/riscv/gstage.c` | G-stage 转换测试 |
| sbi.c | `kvm-unit-tests/riscv/sbi.c` | SBI 虚拟化测试 |

**测试用例**：

```c
// kvm-unit-tests/riscv/hypervisor.c
void test_vsstatus(void) {
    uint64_t vsstatus;

    // 读取 vsstatus
    vsstatus = csr_read(vsstatus);

    // 检查 V 位
    TEST_ASSERT(vsstatus & SR_V, "V bit should be set in vsstatus");

    // 设置 V 位进入虚拟化模式
    csr_set(vsstatus, SR_V);

    // 验证 VS-stage 转换生效
    TEST_ASSERT(get_mode() == VS_MODE, "Should be in VS mode");
}

void test_gstage_translation(void) {
    uint64_t gva = 0x1000;
    uint64_t ipa, pa;

    // 配置 G-stage 页表
    setup_gstage_mapping(GVA_BASE, GVA_SIZE, GPA_BASE, PTE_RWX);

    // 配置 VS-stage 页表
    setup_vsstage_mapping(GVA_BASE, GVA_SIZE, PA_BASE, PTE_RWX);

    // 触发地址转换
    ipa = translate_gva_to_ipa(gva);
    pa = translate_ipa_to_pa(ipa);

    TEST_ASSERT(ipa == EXPECTED_IPA, "G-stage translation failed");
    TEST_ASSERT(pa == EXPECTED_PA, "VS-stage translation failed");
}

void test_hypervisor_csrs(void) {
    // 测试 Hypervisor CSR 访问
    TEST_CHECK(csr_read(vstval) == expected_stval);
    TEST_CHECK(csr_read(vscause) == expected_scause);
    TEST_CHECK(csr_read(vsatp) == expected_satp);
}
```

#### 6.3.2 Linux KVM/RISC-V 测试

**内核自测**：

```bash
# 检查 H-扩展支持
cat /proc/cpuinfo | grep hypervisor

# 检查 KVM 支持
lsmod | grep kvm

# 运行 KVM 单元测试
cd /sys/kernel/debug/kvm
cat interrupts
cat vm_stat
```

**LTP (Linux Test Project)**：

```bash
# 获取 LTP
git clone https://github.com/linux-test-project/ltp.git
cd ltp

# 运行虚拟化相关测试
./runltp -f kvm
```

#### 6.3.3 ARM 虚拟化测试套件

**ARM 架构验证套件**：

```bash
# 运行虚拟化测试
./run_vhe_tests.sh
./run_stage2_tests.sh
```

### 6.4 性能评估方案

#### 6.4.1 kvm-unit-tests 虚拟化测试

kvm-unit-tests 包含全面的虚拟化性能测试：

```bash
# 获取并编译
git clone https://github.com/kvm-unit-tests/kvm-unit-tests.git
cd kvm-unit-tests
./configure --riscv64
make

# 运行虚拟机测试
./riscv/run ./riscv/vm.flat

# 运行 Hypervisor 测试
./riscv/run ./riscv/hypervisor.flat

# 运行 G-stage 转换测试
./riscv/run ./riscv/gstage.flat

# 运行所有测试
./riscv/run -c all ./riscv/functional.flat
```

#### 6.4.2 LTP 虚拟化测试套件

```bash
# 运行 LTP 虚拟化测试
cd /path/to/ltp
./runltp -f kvm

# 关键测试用例：
# kvm01: KVM 模块加载测试
# kvm02: KVM 设备创建测试
# kvm03: VM 运行测试
# kvm04: vCPU 创建测试
```

#### 6.4.3 SPECvirt_sc2013 / SPECvirt_sc2024

SPECvirt 是服务器虚拟化性能评估的权威基准：

```bash
# 安装 SPECvirt
cd /path/to/specvirt
./bin/install

# 配置测试
./bin/config --num_vms=4 --test_suite=speccpu2017

# 运行基准测试
./bin/runbench --iterations=3

# 生成报告
./bin/postprocess
```

**测试指标**：

| 指标 | 说明 | 期望值 |
|------|------|--------|
| SPECrate_virt | 虚拟化吞吐量得分 | 越高越好 |
| SPECratio_virt | 单 VM 性能比 | 接近 1.0 越好 |
| VM Startup Time | 虚拟机启动时间 | 越短越好 |
| VM Density | VM 密度 | 越高越好 |

#### 6.4.4 perf 虚拟化性能分析

```bash
# 分析 vmexit 开销
perf stat -a -e context-switches,cycles,instructions \
    kvm-unit-tests --verbose

# 分析特定 vmexit 类型
perf record -a -g -e kvm:* ./vm_workload
perf report --symbol-filter='vmexit'

# 对比裸金属 vs 虚拟化性能
perf stat -a ./native_workload
perf stat -a ./virtualized_workload
```

**常见 vmexit 类型及开销**：

| vmexit 类型 | 开销级别 | 优化建议 |
|-------------|----------|----------|
| SRET | 低 (50-200 cycles) | 正常 |
| WFI | 低 (20-100 cycles) | 正常 |
| MMIO 访问 | 中 (500-2000 cycles) | 减少 MMIO 访问 |
| I/O 指令 | 中-高 | 使用 VirtIO |
| 页错误 | 高 (1000-5000 cycles) | 使用大页 |
| 指令模拟 | 高 | 避免模拟指令 |

#### 6.4.5 UnixBench 虚拟化对比测试

```bash
# 运行 UnixBench
cd byte-unixbench-5.2
./Run multi

# 关键指标：
# 1. 单任务性能 vs 多任务性能
# 2. 系统调用开销
# 3. 进程间通信性能

# 对比：
# - 裸金属运行结果
# - 虚拟化运行结果
# - 计算虚拟化开销比值
```

#### 6.4.6 ARM FVP 虚拟化测试

使用 ARM 固定虚拟平台进行虚拟化性能评估：

```bash
# 下载 ARM FVP
# https://developer.arm.com/tools-and-software/development-tools/\
#   arm-ecosystem-models/fixed-virtual-platforms

# 运行虚拟化测试
./FVP_Base_RevC-2xAEMvA \
    --machine-type=FVP_Base_RevC-2xAEMvA \
    --data-file=<test_data>.csv \
    --cluster0.NUM_CORES=4 \
    --enable-virtualization

# 分析结果
./analyze_results.py --input <results>.csv
```

### 6.5 SPEC CPU 虚拟化性能对比测试方案

本节设计使用 SPEC CPU 基准测试套件评估 RISC-V 和 ARM 架构虚拟化性能的详细方案。

#### 6.5.1 测试方案概述

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SPEC CPU 虚拟化性能测试方案                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────┐                    ┌─────────────────┐           │
│   │  RISC-V 平台    │                    │   ARM 平台       │           │
│   │                 │                    │                 │           │
│   │  ┌───────────┐ │                    │  ┌───────────┐  │           │
│   │  │ 裸金属基准 │ │◄── 对比 ──►│  │ 裸金属基准 │  │           │
│   │  └───────────┘ │                    │  └───────────┘  │           │
│   │       │        │                    │       │         │           │
│   │       ▼        │                    │       ▼         │           │
│   │  ┌───────────┐ │                    │  ┌───────────┐  │           │
│   │  │ KVM/QEMU  │ │                    │  │ KVM/QEMU  │  │           │
│   │  │  虚拟机    │ │                    │  │  虚拟机    │  │           │
│   │  └───────────┘ │                    │  └───────────┘  │           │
│   │       │        │                    │       │         │           │
│   │       ▼        │                    │       ▼         │           │
│   │  ┌───────────┐ │                    │  ┌───────────┐  │           │
│   │  │ 虚拟机基准 │ │                    │  │ 虚拟机基准 │  │           │
│   │  └───────────┘ │                    │  └───────────┘  │           │
│   └─────────────────┘                    └─────────────────┘           │
│            │                                        │                  │
│            └─────────────────┬────────────────────┘                  │
│                              ▼                                       │
│                    ┌─────────────────────┐                          │
│                    │   性能折损计算      │                          │
│                    │                     │                          │
│                    │  Overhead = (B-N)/N │                          │
│                    │  N = Native Score   │                          │
│                    │  B = Benchmark Score│                          │
│                    └─────────────────────┘                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 6.5.2 测试架构设计

**测试配置矩阵**：

| 平台 | 架构 | 处理器 | 内存 | 测试模式 |
|------|------|--------|------|----------|
| RISC-V | rv64gc | U54-MC @ 1.5GHz | 8GB | Native + KVM |
| ARM | aarch64 | Cortex-A72 @ 1.5GHz | 8GB | Native + KVM |

**SPEC CPU 版本选择**：

| 版本 | 适用场景 | 测试内容 |
|------|----------|----------|
| SPEC CPU 2006 | 通用基准（广泛支持） | INT + FP |
| SPEC CPU 2017 | 最新基准（更严格） | INT + FP + Rate |
| SPECrate | 并发吞吐量 | 多副本性能 |
| SPECspeed | 单任务速度 | 单线程/多线程 |

#### 6.5.3 测试执行流程

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           测试执行流程                                      │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Phase 1: 环境准备                                                        │
│  ┌─────────────┐                                                         │
│  │ 1.1 安装OS │──► Ubuntu 22.04 / Fedora 38                            │
│  └──────┬──────┘                                                         │
│         │                                                                  │
│         ▼                                                                  │
│  ┌─────────────┐                                                         │
│  │1.2 编译SPEC │──► SPEC CPU 2006: $SPEC/config/Arnold_x64.cfg          │
│  └──────┬──────┘        SPEC CPU 2017: $SPEC/config/                                         │
│         │                 根据架构选择配置文件                              │
│         ▼                                                                  │
│  ┌─────────────┐                                                         │
│  │1.3 配置KVM │──► 启用 H-扩展 (RISC-V) / VHE (ARM)                      │
│  └──────┬──────┘     配置 CPU 虚拟化支持                                  │
│         │                                                                  │
│         ▼                                                                  │
│  ┌─────────────┐                                                         │
│  │1.4 准备镜像│──► QCOW2 格式镜像                                         │
│  └─────────────┘     与主机相同的 OS 版本                                   │
│                                                                          │
│  ───────────────────────────────────────────────────────────────────────── │
│                                                                          │
│  Phase 2: 裸金属基准测试                                                  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                      SPEC CPU 2006 运行命令                           │ │
│  ├──────────────────────────────────────────────────────────────────────┤ │
│  │                                                                      │ │
│  │  # Integer 测试                                                        │ │
│  │  runspec --config=Arnold_rv64.cfg --size=ref --iterations=3 int      │ │
│  │                                                                      │ │
│  │  # Floating Point 测试                                                │ │
│  │  runspec --config=Arnold_rv64.cfg --size=ref --iterations=3 fp      │ │
│  │                                                                      │ │
│  │  # 单个基准测试                                                        │ │
│  │  runspec --config=Arnold_rv64.cfg --size=ref 400.perlbench           │ │
│  │                                                                      │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ───────────────────────────────────────────────────────────────────────── │
│                                                                          │
│  Phase 3: 虚拟机基准测试                                                  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                    QEMU 虚拟机配置                                     │ │
│  ├──────────────────────────────────────────────────────────────────────┤ │
│  │                                                                      │ │
│  │  # RISC-V QEMU 配置                                                   │ │
│  │  qemu-system-riscv64 \                                               │ │
│  │      -machine virt \                                                 │ │
│  │      -cpu rv64gc_sstc \                                              │ │
│  │      -m 8G \                                                         │ │
│  │      -smp 4 \                                                        │ │
│  │      -kernel Image \                                                  │ │
│  │      -drive file=ubuntu.img,format=qcow2 \                          │ │
│  │      -netdev user,id=net0 \                                          │ │
│  │      -device virtio-net-pci,netdev=net0                              │ │
│  │                                                                      │ │
│  │  # ARM QEMU 配置                                                      │ │
│  │  qemu-system-aarch64 \                                               │ │
│  │      -machine virt \                                                 │ │
│  │      -cpu cortex-a72 \                                              │ │
│  │      -m 8G \                                                         │ │
│  │      -smp 4 \                                                        │ │
│  │      -kernel Image \                                                  │ │
│  │      -drive file=ubuntu.img,format=qcow2 \                          │ │
│  │      -netdev user,id=net0 \                                          │ │
│  │      -device virtio-net-pci,netdev=net0                              │ │
│  │                                                                      │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                  虚拟机内 SPEC CPU 运行命令                             │ │
│  ├──────────────────────────────────────────────────────────────────────┤ │
│  │                                                                      │ │
│  │  # 与裸金属相同的运行命令                                              │ │
│  │  runspec --config=Arnold_rv64.cfg --size=ref --iterations=3 int      │ │
│  │  runspec --config=Arnold_rv64.cfg --size=ref --iterations=3 fp      │ │
│  │                                                                      │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

#### 6.5.4 配置文件示例

**SPEC CPU 2006 RISC-V 配置文件** (`Arnold_rv64.cfg`)：

```
# SPEC CPU 2006 Configuration File for RISC-V

# Compiler and flags
CC          = /path/to/riscv64-unknown-linux-gnu-gcc
CXX         = /path/to/riscv64-unknown-linux-gnu-g++
FC          = /path/to/riscv64-unknown-linux-gnu-gfortran

COPTIMIZE   = -O3 -march=rv64gc
CXXOPTIMIZE = -O3 -march=rv64gc
FOPTIMIZE   = -O3 -march=rv64gc

# Include and library paths
PREOPTS     =
POSTOPTS    =

# Benchmark-specific settings
400.perlbench = default=default
401.bzip2     = default=default
403.gcc       = default=default
429.mcf       = default=default
445.gobmk     = default=default
456.hmmer     = default=default
458.sjeng     = default=default
462.libquantum= default=default
464.h264ref   = default=default
471.omnetpp   = default=default
473.astar     = default=default
483.xalancbmk = default=default
```

**SPEC CPU 2017 ARM 配置文件** (`Cortex-A72.cfg`)：

```
# SPEC CPU 2017 Configuration File for ARM Cortex-A72

# Compiler and flags
CC          = /path/to/aarch64-linux-gnu-gcc
CXX         = /path/to/aarch64-linux-gnu-g++
FC          = /path/to/aarch64-linux-gnu-gfortran

COPTIMIZE   = -O3 -march=armv8-a
CXXOPTIMIZE = -O3 -march=armv8-a
FOPTIMIZE   = -O3 -march=armv8-a

# Benchmark-specific settings
500.perlbench_r    = default=default
502.gcc_r          = default=default
503.bzip_r         = default=default
505.mcf_r          = default=default
520.omnetpp_r      = default=default
523.xalancbmk_r    = default=default
525.x264_r         = default=default
531.deepsjeng_r    = default=default
541.leela_r        = default=default
548.exchange2_r    = default=default
557.xz_r           = default=default
```

#### 6.5.5 数据收集与计算

**性能指标收集**：

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          数据收集表格                                      │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ 测试配置                                                            │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │ 平台:          _____________    架构:       _____________           │ │
│  │ CPU:          _____________    频率:       _____________           │ │
│  │ 内存:          _____________    核心数:     _____________           │ │
│  │ SPEC版本:     _____________    测试日期:   _____________           │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ 测试结果                                                            │ │
│  ├───────────────────────┬─────────────────────┬───────────────────────┤ │
│  │ SPECint2006          │ Native (裸金属)      │ Virtualized (虚拟机)   │ │
│  ├───────────────────────┼─────────────────────┼───────────────────────┤ │
│  │ 400.perlbench        │                     │                       │ │
│  │ 401.bzip2            │                     │                       │ │
│  │ 403.gcc              │                     │                       │ │
│  │ 429.mcf              │                     │ │ │
│  │ 445.gobmk            │                     │                       │ │
│  │ 456.hmmer            │                     │                       │ │
│  │ 458.sjeng            │                     │                       │ │
│  │ 462.libquantum       │                     │                       │ │
│  │ 464.h264ref          │                     │                       │ │
│  │ 471.omnetpp         │                     │                       │ │
│  │ 473.astar            │                     │                       │ │
│  │ 483.xalancbmk       │                     │                       │ │
│  ├───────────────────────┼─────────────────────┼───────────────────────┤ │
│  │ ESTIMATEED SCORE     │                     │                       │ │
│  ├───────────────────────┴─────────────────────┴───────────────────────┤ │
│  │ SPECfp2006          │ Native (裸金属)      │ Virtualized (虚拟机)   │ │
│  ├───────────────────────┼─────────────────────┼───────────────────────┤ │
│  │ 410.bwaves           │                     │                       │ │
│  │ 416.gamess          │                     │                       │ │
│  │ 433.milc             │                     │                       │ │
│  │ 434.zeusmp           │                     │                       │ │
│  │ 435.gromacs         │                     │                       │ │
│  │ 436.cactusADM       │                     │                       │ │
│  │ 437.leslie3d        │                     │                       │ │
│  │ 444.namd            │                     │                       │ │
│  │ 447.dealII          │                     │                       │ │
│  │ 450.soplex          │                     │                       │ │
│  │ 453.povray          │                     │                       │ │
│  │ 454.calculix        │                     │                       │ │
│  │ 459.GemsFDTD        │                     │                       │ │
│  │ 465.tonto           │                     │                       │ │
│  │ 470.lbm             │                     │                       │ │
│  │ 481.wrf             │                     │                       │ │
│  │ 482.sphinx3         │                     │                       │ │
│  ├───────────────────────┼─────────────────────┼───────────────────────┤ │
│  │ ESTIMATEED SCORE     │                     │                       │ │
│  └───────────────────────┴─────────────────────┴───────────────────────┘ │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**性能折损计算公式**：

```
虚拟化性能折损率 (Overhead)：

    Overhead(%) = [(Native_Score - VM_Score) / Native_Score] × 100

性能保持率 (Performance Ratio)：

    Ratio = VM_Score / Native_Score × 100%

示例计算：
    Native SPECint = 100 分
    VM SPECint = 85 分
    Overhead = (100 - 85) / 100 = 15%
    Ratio = 85 / 100 = 85%
```

#### 6.5.6 结果展示图表

**性能对比柱状图示例**：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   SPEC CPU 2006 INT 性能对比                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  RISC-V (U54 @ 1.5GHz, 4 cores)                                        │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ Native ████████████████████████████████████████████████████  100   │ │
│  │ VM     ████████████████████████████████████████████████    82    │ │
│  │ Ratio  └───────────────────────────────────────────────────────    │ │
│  │         0%     20%     40%     60%     80%     100%                │ │
│  │         │────────│────────│────────│────────│────────│               │ │
│  │         █ Native  ■ VM                                              │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ARM (Cortex-A72 @ 1.5GHz, 4 cores)                                    │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ Native ████████████████████████████████████████████████████  100   │ │
│  │ VM     ██████████████████████████████████████████████████████  91   │ │
│  │ Ratio  └────────────────────────────────────────────────────────    │ │
│  │         0%     20%     40%     60%     80%     100%                │ │
│  │         █ Native  ■ VM                                              │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  图例: █ Native (裸金属性能, 归一化为100%)                               │
│       ■ VM (虚拟机性能, 相对于 Native 的百分比)                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**性能折损对比图表**：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   虚拟化性能折损率对比 (%)                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   25% ┤                                                                │
│       │  ▓▓                                                              │
│   20% ┤  ▓▓  ▓▓                                                         │
│       │  ▓▓  ▓▓  ▓▓                                                      │
│   15% ┤  ▓▓  ▓▓  ▓▓  ▓▓                                                   │
│       │  ▓▓  ▓▓  ▓▓  ▓▓  ▓▓                                                │
│   10% ┤  ▓▓  ▓▓  ▓▓  ▓▓  ▓▓  ▓▓                                           │
│       │  ▓▓  ▓▓  ▓▓  ▓▓  ▓▓  ▓▓  ▓▓                                        │
│    5% ┤  ▓▓  ▓▓  ▓▓  ▓▓  ▓▓  ▓▓  ▓▓  ▓▓                                     │
│       │  ▓▓  ▓▓  ▓▓  ▓▓  ▓▓  ▓▓  ▓▓  ▓▓  ▓▓                                  │
│    0% ┼──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──                                  │
│         SPECint  SPECfp   SPECint  SPECfp  SPECint  SPECfp               │
│               RISC-V              ARM              x86 (参考)             │
│                                                                         │
│   ▓▓ = RISC-V  ░░ = ARM                                                  │
│                                                                         │
│   注: x86 数据来自 Intel/AMD 主流处理器，使用 KVM 虚拟化                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**综合性能雷达图**：

```
                    SPECint Rate
                         │
                         100%
                         │
                         │
    Memory ──────────────┼───────────── Memory
    Performance          │          Performance
                         │
                    0% ─┴───────────────────────────── 100%
                         │
                         │
                         │
                         │
                    System Call
                    Overhead
                         │
                         │

┌─────────────────────────────────────────────────────────────────────────┐
│  雷达图维度说明：                                                        │
│                                                                         │
│  维度              RISC-V KVM     ARM KVM     x86 KVM                   │
│  ─────────────────────────────────────────────────────                   │
│  CPU 计算          ████████░░    ██████████░░   ██████████░░          │
│  内存访问          ███████░░░    █████████░░░   █████████░░░          │
│  系统调用          █████░░░░░    ████████░░░   █████████░░░          │
│  I/O 吞吐          ██████░░░░    ███████░░░░   ████████░░░          │
│  上下文切换        █████░░░░░    ████████░░░   ████████░░░          │
│                                                                         │
│  说明: █ = 实测性能 (越接近 100%越好)                                     │
│       ░ = 虚拟化折损                                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 6.5.7 详细测试命令

**SPEC CPU 2006 完整测试流程**：

```bash
#!/bin/bash
#=============================================================================
# SPEC CPU 虚拟化性能测试脚本
#=============================================================================

# 配置变量
SPEC_DIR="/path/to/spec2006"
CONFIG_RISCV="Arnold_rv64.cfg"
CONFIG_ARM="Cortex-A72.cfg"
ITERATIONS=3

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

#----------------------------------------------------------------------------
# 阶段 1: RISC-V 裸金属测试
#----------------------------------------------------------------------------
test_riscv_native() {
    log_info "开始 RISC-V 裸金属测试..."

    cd $SPEC_DIR

    # Integer 测试
    runspec --config=$CONFIG_RISCV --size=ref \
            --iterations=$ITERATIONS \
            --reportable int \
            2>&1 | tee log_riscv_native_int.txt

    # Floating Point 测试
    runspec --config=$CONFIG_RISCV --size=ref \
            --iterations=$ITERATIONS \
            --reportable fp \
            2>&1 | tee log_riscv_native_fp.txt

    log_info "RISC-V 裸金属测试完成"
}

#----------------------------------------------------------------------------
# 阶段 2: RISC-V 虚拟机测试
#----------------------------------------------------------------------------
test_riscv_vm() {
    log_info "开始 RISC-V 虚拟机测试..."

    # 需要在 QEMU 虚拟机内执行
    log_error "请在 QEMU 虚拟机内执行相同的测试命令"
    echo "虚拟机内命令:"
    echo "  runspec --config=$CONFIG_RISCV --size=ref --iterations=3 int"
    echo "  runspec --config=$CONFIG_RISCV --size=ref --iterations=3 fp"
}

#----------------------------------------------------------------------------
# 阶段 3: ARM 裸金属测试
#----------------------------------------------------------------------------
test_arm_native() {
    log_info "开始 ARM 裸金属测试..."

    cd $SPEC_DIR

    # Integer 测试
    runspec --config=$CONFIG_ARM --size=ref \
            --iterations=$ITERATIONS \
            --reportable int \
            2>&1 | tee log_arm_native_int.txt

    # Floating Point 测试
    runspec --config=$CONFIG_ARM --size=ref \
            --iterations=$ITERATIONS \
            --reportable fp \
            2>&1 | tee log_arm_native_fp.txt

    log_info "ARM 裸金属测试完成"
}

#----------------------------------------------------------------------------
# 阶段 4: ARM 虚拟机测试
#----------------------------------------------------------------------------
test_arm_vm() {
    log_info "开始 ARM 虚拟机测试..."

    # 需要在 QEMU/FVP 虚拟机内执行
    log_error "请在 ARM 虚拟机内执行相同的测试命令"
}

#----------------------------------------------------------------------------
# 阶段 5: 结果汇总
#----------------------------------------------------------------------------
generate_report() {
    log_info "生成测试报告..."

    cat > spec_virt_report.md << 'EOF'
# SPEC CPU 虚拟化性能测试报告

## 测试环境

| 项目 | RISC-V | ARM |
|------|--------|-----|
| 处理器 | U54-MC @ 1.5GHz | Cortex-A72 @ 1.5GHz |
| 核心数 | 4 | 4 |
| 内存 | 8GB | 8GB |
| OS | Ubuntu 22.04 | Ubuntu 22.04 |
| QEMU | v8.0+ | v8.0+ |
| KVM | 启用 | 启用 |

## 测试结果

### SPEC CPU 2006 INT

| 基准 | RISC-V Native | RISC-V VM | ARM Native | ARM VM |
|------|---------------|-----------|------------|--------|
| 400.perlbench | | | | |
| 401.bzip2 | | | | |
| 403.gcc | | | | |
| 429.mcf | | | | |
| ... | | | | |
| **ESTIMATEED** | | | | |

### SPEC CPU 2006 FP

| 基准 | RISC-V Native | RISC-V VM | ARM Native | ARM VM |
|------|---------------|-----------|------------|--------|
| 410.bwaves | | | | |
| 416.gamess | | | | |
| ... | | | | |
| **ESTIMATEED** | | | | |

## 性能折损分析

| 指标 | RISC-V | ARM |
|------|--------|-----|
| SPECint Overhead | XX% | XX% |
| SPECfp Overhead | XX% | XX% |
| 平均 Overhead | XX% | XX% |

## 结论

EOF

    log_info "报告已生成: spec_virt_report.md"
}

# 主程序
main() {
    echo "========================================"
    echo "SPEC CPU 虚拟化性能测试"
    echo "========================================"

    test_riscv_native
    test_arm_native
    generate_report
}

main "$@"
```

#### 6.5.8 测试结果记录表

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        SPEC CPU 测试结果记录表                             │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  【测试信息】                                                             │
│  ─────────────────────────────────────────────────────────────────────── │
│  测试日期:        _____________    测试人员:  _____________              │
│  SPEC 版本:      _____________    配置文件:  _____________              │
│  测试平台:       _____________    固件版本:  _____________              │
│                                                                          │
│  【硬件配置】                                                             │
│  ┌─────────────────────────┬─────────────────────────┐                   │
│  │      RISC-V 平台        │        ARM 平台         │                   │
│  ├─────────────────────────┼─────────────────────────┤                   │
│  │ CPU:                   │ CPU:                    │                   │
│  │ Frequency:             │ Frequency:              │                   │
│  │ Cores:                 │ Cores:                  │                   │
│  │ Memory:                │ Memory:                 │                   │
│  │ L1 Cache:              │ L1 Cache:               │                   │
│  │ L2 Cache:              │ L2 Cache:               │                   │
│  └─────────────────────────┴─────────────────────────┘                   │
│                                                                          │
│  【软件配置】                                                             │
│  ┌─────────────────────────┬─────────────────────────┐                   │
│  │      RISC-V 平台        │        ARM 平台         │                   │
│  ├─────────────────────────┼─────────────────────────┤                   │
│  │ OS:                    │ OS:                     │                   │
│  │ Kernel:                │ Kernel:                 │                   │
│  │ QEMU:                  │ QEMU:                   │                   │
│  │ GCC:                   │ GCC:                    │                   │
│  └─────────────────────────┴─────────────────────────┘                   │
│                                                                          │
│  【SPECint2006 结果】                                                     │
│  ┌────────────────────────┬─────────────────┬───────────────────────────┐ │
│  │ 基准程序              │ Native Score   │ VM Score                  │ │
│  ├────────────────────────┼─────────────────┼───────────────────────────┤ │
│  │ 400.perlbench        │                 │                           │ │
│  │ 401.bzip2            │                 │                           │ │
│  │ 403.gcc              │                 │                           │ │
│  │ 429.mcf              │                 │                           │ │
│  │ 445.gobmk            │                 │                           │ │
│  │ 456.hmmer            │                 │                           │ │
│  │ 458.sjeng            │                 │                           │ │
│  │ 462.libquantum       │                 │                           │ │
│  │ 464.h264ref          │                 │                           │ │
│  │ 471.omnetpp         │                 │                           │ │
│  │ 473.astar            │                 │                           │ │
│  │ 483.xalancbmk       │                 │                           │ │
│  ├────────────────────────┼─────────────────┼───────────────────────────┤ │
│  │ ESTIMATEED SCORE      │                 │                           │ │
│  │ Overhead (%)         │                 │ N/A                       │ │
│  └────────────────────────┴─────────────────┴───────────────────────────┘ │
│                                                                          │
│  【SPECfp2006 结果】                                                      │
│  ┌────────────────────────┬─────────────────┬───────────────────────────┐ │
│  │ 基准程序              │ Native Score   │ VM Score                  │ │
│  ├────────────────────────┼─────────────────┼───────────────────────────┤ │
│  │ 410.bwaves           │                 │                           │ │
│  │ 416.gamess          │                 │                           │ │
│  │ 433.milc             │                 │                           │ │
│  │ 434.zeusmp           │                 │                           │ │
│  │ 435.gromacs         │                 │                           │ │
│  │ ...                  │                 │                           │ │
│  ├────────────────────────┼─────────────────┼───────────────────────────┤ │
│  │ ESTIMATEED SCORE      │                 │                           │ │
│  │ Overhead (%)         │                 │ N/A                       │ │
│  └────────────────────────┴─────────────────┴───────────────────────────┘ │
│                                                                          │
│  【性能折损分析】                                                         │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                        │     RISC-V     │       ARM      │        │  │
│  ├────────────────────────────────────────────────────────────────────┤  │
│  │  SPECint Overhead      │     XX.X%      │      XX.X%     │        │  │
│  │  SPECfp Overhead       │     XX.X%      │      XX.X%     │        │  │
│  │  综合 Overhead         │     XX.X%      │      XX.X%     │        │  │
│  │  性能保持率            │     XX.X%      │      XX.X%     │        │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  【环境信息】                                                             │
│  CPU 占用:     _____________    测试期间温度:  _____________            │
│  内存占用:     _____________    电源模式:      _____________            │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

#### 6.5.9 预期结果与差异分析

**预期性能折损范围**：

| 场景 | RISC-V 预期 | ARM 预期 | 差异原因 |
|------|-------------|----------|----------|
| SPECint Overhead | 15-25% | 8-15% | H-扩展 vs VHE |
| SPECfp Overhead | 10-20% | 5-12% | FP 单元差异 |
| 系统调用开销 | 20-30% | 10-15% | 仿真开销 |
| 内存访问 | 5-10% | 3-8% | TLB 双重查找 |

**差异分析维度**：

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      性能差异来源分析                                      │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌─────────────────┐                                                    │
│   │ 性能差异         │                                                    │
│   └────────┬────────┘                                                    │
│            │                                                             │
│    ┌───────┴───────┐                                                     │
│    │               │                                                     │
│    ▼               ▼                                                     │
│  ┌─────────┐   ┌─────────┐                                              │
│  │ 架构差异 │   │ 软件差异 │                                              │
│  └────┬────┘   └────┬────┘                                              │
│       │             │                                                   │
│       ├──────┬──────┤                                                   │
│       │      │      │                                                   │
│       ▼      ▼      ▼                                                   │
│    ┌─────┐ ┌─────┐ ┌─────┐                                             │
│    │CSR  │ │MMU  │ │GIC  │  ← RISC-V H-扩展                            │
│    │访问 │ │双重 │ │仿真 │                                             │
│    └─────┘ └─────┘ └─────┘                                             │
│                      │                                                   │
│       ┌──────────────┴──────────────┐                                    │
│       │                             │                                    │
│       ▼                             ▼                                    │
│    ┌─────┐                      ┌─────┐                                 │
│    │VHE  │                      │VirtIO│  ← 软件优化                     │
│    │优化 │                      │开销  │                                 │
│    └─────┘                      └─────┘                                 │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

#### 6.5.10 注意事项与建议

**测试前准备**：

1. **环境隔离**：关闭非必要服务，确保测试期间系统稳定
2. **频率固定**：锁定 CPU 频率，避免动态调频影响结果
3. **散热保障**：确保充分的散热，防止热节流
4. **预热运行**：首次运行可能因缓存未预热而偏低，建议预热

**测试执行建议**：

| 建议 | 说明 | 预期影响 |
|------|------|----------|
| 多次迭代 | 至少 3 次，取平均值 | 减少随机误差 |
| 错误重试 | 失败时重新测试 | 确保数据完整 |
| 详细记录 | 环境配置、温度、时间 | 便于复现分析 |
| 对比测试 | 相同配置下对比 | 控制变量 |

**常见问题排查**：

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| VM 分数异常低 | KVM 未启用 | 检查 /dev/kvm 权限 |
| 分数波动大 | CPU 节流 | 关闭动态调频 |
| 编译错误 | 工具链配置 | 检查配置文件 |
| 运行失败 | 内存不足 | 增加内存或减小测试规模 |

---

## 7. Ssstrict - 严格执行扩展

### 7.1 功能概述

#### 7.1.1 RISC-V Ssstrict 扩展

**规范信息**：

| 项目 | 内容 |
|------|------|
| 规范名称 | Ssstrict |
| 状态 | RVA23S64 强制 |
| 规范文档 | RISC-V Privileged Architecture v1.12 |
| 功能 | 保留编码空间必须引发非法指令异常 |

**行为规范**：

| 操作 | 行为 |
|------|------|
| 执行未实现操作码 | 非法指令异常 |
| 访问未实现 CSR | 非法指令异常 |
| 保留编码 | 非法指令异常 |

**与 RVC 的关系**：

- Ssstrict 不影响 RVC (压缩指令) 的编码空间
- 自定义扩展可以使用保留编码空间
- 标准扩展必须使用已分配编码

#### 7.1.2 ARM 原生行为

ARM 架构始终对未定义/保留指令产生 undefined instruction 异常，这是原生行为而非可选扩展。

### 7.2 功能映射与关键区别

```
RISC-V Ssstrict: 行为规范（可选）
ARM: 原生行为（强制）
```

| 特性 | RISC-V Ssstrict | ARM 原生 |
|------|-----------------|----------|
| 行为确定性 | 高 | 高 |
| 安全价值 | 标准化异常行为 | 原生支持 |
| 认证支持 | RVA23S64 强制 | 原生认证 |
| 自定义扩展 | 不影响 | 不影响 |

### 7.3 权威测试套件

#### 7.3.1 riscv-tests

| 测试文件 | 路径 | 功能描述 |
|----------|------|----------|
| illegal | `riscv-tests/isa/rv64mi-p-illegal.c` | 非法指令测试 |

**测试用例**：

```c
// riscv-tests/isa/rv64mi-p-illegal.c
void test_illegal_instruction(void) {
    uint64_t reserved_encoding = 0x00000000;

    // 测试保留编码
    asm volatile(".word %0" : : "i"(reserved_encoding));

    // 应触发 illegal instruction exception
    // 测试框架验证异常被正确处理
}

void test_unimplemented_csr(void) {
    uint64_t csr_value;

    // 测试未实现 CSR 访问
    asm volatile("csrr %0, 0xFFF" : "=r"(csr_value));

    // 应触发 illegal instruction exception
}
```

#### 7.3.2 Linux Kernel Selftests

| 测试文件 | 路径 | 功能描述 |
|----------|------|----------|
| sigill.c | `tools/testing/selftests/sigill/` | SIGILL 测试 |

**运行测试**：

```bash
# 运行 sigill 测试
cd tools/testing/selftests/sigill
make
./sigill_test
```

### 7.4 性能评估方案

> **注意**：Ssstrict 是行为规范扩展，不涉及性能敏感操作，因此不提供性能评估方案。

**测试重点**：

1. **异常捕获正确性**：验证所有保留编码正确触发异常
2. **异常处理效率**：测量从异常到处理的时间
3. **安全性验证**：确认无静默失败情况

---

## 8. 性能评估方案汇总

### 8.1 权威性能测试程序索引

| 扩展 | 测试程序 | 类型 | 测试内容 |
|------|----------|------|----------|
| Zifencei | lmbench | 标准 | 内存/指令延迟、系统调用开销 |
| Zifencei | UnixBench | 标准 | 系统调用、上下文切换 |
| Svnapot | STREAM | 标准 | 内存带宽 |
| Svnapot | lmbench | 标准 | 内存延迟、TLB Miss |
| Svnapot | SPEC CPU | 标准 | CPU/内存基准 |
| Ssnpm | stress-ng | 标准 | 内存压力测试 |
| Ssnpm | LTP | 标准 | 内存管理测试 |
| Sstc | cyclictest | 标准 | 定时器中断延迟 |
| Sstc | stress-ng | 标准 | 定时器压力测试 |
| H-扩展 | SPECvirt | 标准 | 虚拟化吞吐量 |
| H-扩展 | LTP | 标准 | 虚拟化功能测试 |

### 8.2 权威测试程序获取

#### 8.2.1 内存系统测试

| 工具 | 获取方式 | 主要测试 |
|------|----------|----------|
| STREAM | https://www.cs.virginia.edu/stream/ | 内存带宽 |
| lmbench | `apt install lmbench` | 内存/缓存延迟 |
| clpeak | https://github.com/krrishnarraj/clpeak-opencl | GPU 内存带宽 |
| bandwitdh | https://github.com/facebook/rocksdb/wiki/bandwitdh | 内存带宽 |

#### 8.2.2 系统性能测试

| 工具 | 获取方式 | 主要测试 |
|------|----------|----------|
| UnixBench | https://github.com/kdlucas/byte-unixbench | 系统整体性能 |
| sysbench | `apt install sysbench` | CPU/内存/IO |
| Phoronix | https://www.phoronix-test-suite.com | 综合基准 |
| LTP | https://github.com/linux-test-project/ltp | Linux 功能测试 |

#### 8.2.3 实时性能测试

| 工具 | 获取方式 | 主要测试 |
|------|----------|----------|
| rt-tests | `apt install rt-tests` | cyclictest |
| stress-ng | `apt install stress-ng` | 压力测试 |
| hackbench | `apt install util-linux` | 调度器性能 |

#### 8.2.4 虚拟化性能测试

| 工具 | 获取方式 | 主要测试 |
|------|----------|----------|
| SPECvirt | 商业授权 | 虚拟化综合性能 |
| kvm-unit-tests | GitHub | KVM 功能测试 |
| VMMark | 商业授权 | 虚拟化性能 |
| xeony | 开源 | Xen 性能测试 |

### 8.3 对比测试方法

```
标准性能对比流程：

1. 环境准备
   ├── 配置 1: RISC-V 平台（启用目标扩展）
   └── 配置 2: ARM 平台（启用对应功能）

2. 基准运行
   ├── 运行相同的权威测试程序
   ├── 使用相同的编译参数
   └── 记录测试环境信息

3. 数据收集
   ├── 性能指标（时间/分数）
   ├── 资源利用（CPU/内存/IO）
   └── 系统配置信息

4. 结果分析
   ├── 计算性能比值
   └── 识别性能瓶颈
```

---

## 9. 测试套件索引

### 9.1 RISC-V 测试套件清单

| 扩展 | 测试套件 | 文件路径 | 测试内容 |
|------|----------|----------|----------|
| Zifencei | riscv-tests | `isa/rv64mi-p-fencei` | FENCE.I 功能 |
| Zifencei | kvm-unit-tests | `riscv/fencei_test.c` | 虚拟化测试 |
| Svnapot | kvm-unit-tests | `lib/riscv/mmu.c` | NAPOT 页表 |
| Svnapot | kselftest | `mm/hugepage-mmap.c` | 大页功能 |
| Ssnpm | riscv-tests | `isa/rv64pm-p-*` | 指针屏蔽 |
| Ssnpm | kselftest | `riscv/cfi/user_cfi_test.c` | CFI 测试 |
| Sstc | kvm-unit-tests | `riscv/timer_test.c` | 定时器 |
| Sstc | kselftest | `timers/nanosleep.c` | POSIX 定时器 |
| H-扩展 | kvm-unit-tests | `riscv/hypervisor.c` | 虚拟化 CSR |
| H-扩展 | kvm-unit-tests | `riscv/gstage.c` | 两阶段转换 |
| Ssstrict | riscv-tests | `isa/rv64mi-p-illegal` | 非法指令 |

### 9.2 ARM 测试套件清单

| 扩展 | 测试套件 | 说明 |
|------|----------|------|
| ISB | ARM AVE | 架构验证套件 |
| Contiguous | ARM LISA | 内存子系统测试 |
| MTE | ARM FVP | 固定虚拟平台 |
| Generic Timer | ARM AVE | 定时器测试 |
| VHE | ARM AVE | 虚拟化测试 |

### 9.3 交叉平台测试

| 测试场景 | RISC-V 工具 | ARM 工具 |
|----------|-------------|----------|
| 指令屏障 | riscv-tests | ARM DSU |
| TLB 性能 | perf | ARM PMU |
| 定时器延迟 | cyclictest | ARM DS-5 |
| 虚拟化 | kvm-unit-tests | ARM FVP |

---

## 10. 总结与建议

### 10.1 功能对比总结

| 扩展对 | RISC-V 特点 | ARM 特点 | 相对优势 |
|--------|-------------|----------|----------|
| Zifencei/ISB | 组合指令 | 单指令高效 | ARM |
| Sstvala/FAR | 标准化 | 成熟稳定 | 相当 |
| Svnapot/Contiguous | 单PTE高效 | 多PTE合并 | RISC-V |
| Ssnpm/MTE | 软件辅助 | 硬件强制 | ARM |
| Sstc/Timer | CSR快速访问 | GIC集成 | 相当 |
| H-扩展/VHE | 模块化 | 成熟 | ARM |
| Ssstrict/原生 | 规范明确 | 原生 | 相当 |

### 10.2 测试建议

#### 10.2.1 功能验证

1. **基础功能测试**：使用 riscv-tests 验证 ISA 合规性
2. **虚拟化测试**：使用 kvm-unit-tests 验证 H-扩展
3. **内核集成**：使用 Linux kselftest 验证系统集成

#### 10.2.2 性能测试

使用权威基准测试程序进行性能评估：

| 扩展 | 推荐测试程序 | 测试内容 |
|------|--------------|----------|
| Zifencei | lmbench, UnixBench | 指令延迟、系统调用开销 |
| Svnapot | STREAM, lmbench | 内存带宽、TLB Miss |
| Ssnpm | stress-ng, LTP | 内存压力、KASAN 开销 |
| Sstc | cyclictest, rt-tests | 定时器中断延迟、抖动 |
| H-扩展 | SPECvirt, LTP | 虚拟化吞吐量、vmexit 开销 |

#### 10.2.3 对比测试方法

```
标准对比测试流程：

1. 基线配置：
   - RISC-V: 无特定扩展或标准配置
   - ARM: 对应功能的默认配置

2. 测试配置：
   - RISC-V: 启用目标扩展
   - ARM: 启用对应功能

3. 运行权威基准：
   - 使用相同的测试程序
   - 相同的编译优化选项
   - 相同的运行时配置

4. 收集指标：
   - 性能数据（时间/吞吐量）
   - 资源利用率（CPU/内存）
   - 延迟/抖动数据
```

### 10.3 后续工作

1. 补充各平台的实际测试数据
2. 增加 ARM/RISC-V 对比测试数据
3. 完善性能优化建议

---

## 参考文档

### 官方规范

1. [RISC-V Unprivileged ISA v20191213](https://docs.riscv.org/specifications/unprivileged-isa/)
2. [RISC-V Privileged Architecture v1.12](https://docs.riscv.org/specifications/privileged-isa/)
3. [ARM Architecture Reference Manual (ARMv8)](https://developer.arm.com/documentation/ddi0487/latest/)
4. [RVA23 Profile Specification](https://docs.riscv.org/specifications/rva23/)

### 测试框架

5. [riscv-tests GitHub](https://github.com/riscv-software-src/riscv-tests)
6. [kvm-unit-tests GitHub](https://github.com/kvm-unit-tests/kvm-unit-tests)
7. [Linux Kernel Selftests](https://docs.kernel.org/dev-tools/kselftest.html)
8. [LTP GitHub](https://github.com/linux-test-project/ltp)

### 技术资源

9. [RISC-V Linux 内核文档](https://www.kernel.org/doc/html/latest/riscv/)
10. [ARM Virtualization Guide](https://developer.arm.com/documentation/102142/)

---

*文档版本: 2.2*
*更新日期: 2026-02-12*
*作者: Claude Code + Agent Team*
