# ARM64 FP 压力测试 Kselftest 集成补丁分析

## 补丁信息

| 属性 | 值 |
|------|-----|
| **作者** | Mark Brown <broonie@kernel.org> |
| **提交日期** | 2022年8月29日 |
| **邮件主题** | `[PATCH v2 4/4] kselftest/arm64: kselftest harness for FP stress tests` |
| **原始链接** | https://lore.kernel.org/r/20220829154452.824870-5-broonie@kernel.org |

---

## 一、补丁背景

### 1.1 问题描述

在此之前，ARM64 平台的浮点上下文切换压力测试存在以下问题：

1. **手动运行** - 测试程序需要手动执行，缺乏自动化集成
2. **测试覆盖不全** - 现有的简单测试工具没有集成到 kselftest 框架
3. **向量长度受限** - 对于 SVE (Scalable Vector Extension) 和 SME (Scalable Matrix Extension)，测试只使用进程默认的向量长度，无法覆盖所有支持的 VL
4. **CI 无法运行** - 由于没有集成到 kselftest，CI 系统无法自动运行这些测试

### 1.2 补丁目标

提供一个 kselftest 集成工具，能够：

- 自动检测硬件能力 (FPSIMD/SVE/SME)
- 探测所有支持的向量长度
- 并发运行多个测试进程以产生上下文切换压力
- 集成到 kselftest 框架，支持 CI 自动化

---

## 二、补丁内容概览

### 2.1 文件变更

| 文件路径 | 变更类型 | 说明 |
|----------|----------|------|
| `tools/testing/selftests/arm64/fp/.gitignore` | 修改 | 添加 `fp-stress` 可执行文件 |
| `tools/testing/selftests/arm64/fp/Makefile` | 修改 | 将 `fp-stress` 加入 `TEST_GEN_PROGS` |
| `tools/testing/selftests/arm64/fp/fp-stress.c` | 新增 | 主测试工具，535行代码 |

### 2.2 代码结构

```
fp-stress.c (535 lines)
│
├── 数据结构定义
│   └── struct child_data     // 子进程状态管理
│
├── 硬件探测
│   ├── num_processors()      // 获取 CPU 数量
│   └── probe_vls()           // 探测支持的向量长度
│
├── 子进程管理
│   ├── child_start()         // 启动子进程 (fork + execl)
│   ├── child_output()        // 处理子进程输出
│   ├── child_tickle()        // 发送 SIGUSR2
│   ├── child_stop()          // 发送 SIGTERM
│   └── child_cleanup()       // 等待并检查子进程状态
│
├── 测试启动器
│   ├── start_fpsimd()        // 启动 FPSIMD 测试
│   ├── start_sve()           // 启动 SVE 测试
│   ├── start_ssve()          // 启动 Streaming SVE 测试
│   └── start_za()            // 启动 ZA 状态测试
│
├── 信号处理
│   ├── handle_child_signal() // SIGCHLD 处理
│   └── handle_exit_signal()  // SIGINT/SIGTERM 处理
│
├── 辅助功能
│   └── drain_output()        // 非阻塞输出处理
│
└── main()                    // 主函数
```

---

## 三、核心功能设计

### 3.1 测试启动策略

```
┌─────────────────────────────────────────────────────────────────┐
│                      测试启动策略                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 仅支持 FPSIMD                                           │   │
│  │   每个CPU 启动 2 个 fpsimd-test 进程                    │   │
│  │   目的: 强制产生上下文切换                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 支持 SVE/SME                                            │   │
│  │   每个CPU 启动:                                          │   │
│  │     - 1 个 fpsimd-test                                  │   │
│  │     - 每个 SVE VL 启动 1 个 sve-test                     │   │
│  │     - 每个 SME VL 启动 1 个 ssve-test (Streaming SVE)   │   │
│  │     - 每个 SME VL 启动 1 个 za-test (ZA状态)            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 主要数据结构

```c
struct child_data {
    char *name;        // 测试名称，如 "FPSIMD-0-0", "SVE-VL-256-1"
    char *output;      // 输出缓冲区（处理不完整行）
    pid_t pid;         // 子进程 PID
    int stdout;        // stdout 管道读端
    bool output_seen;  // 是否收到过输出
    bool exited;       // 是否已退出
    int exit_status;   // 退出状态码
};
```

### 3.3 主流程

```
┌───────────────────────────────────────────────────────────────┐
│                         主流程                                 │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐                                         │
│  │ 1. 解析命令行   │  -t N: 设置运行时长（默认10秒）          │
│  │    参数         │  N=0: 无超时，需手动终止                 │
│  └────────┬────────┘                                         │
│           │                                                   │
│           ▼                                                   │
│  ┌─────────────────┐                                         │
│  │ 2. 检测硬件能力 │  getauxval(AT_HWCAP) & HWCAP_SVE        │
│  │                 │  getauxval(AT_HWCAP2) & HWCAP2_SME      │
│  └────────┬────────┘                                         │
│           │                                                   │
│           ▼                                                   │
│  ┌─────────────────┐                                         │
│  │ 3. 探测向量长度 │  probe_vls() 使用 prctl() 探测所有       │
│  │                 │  支持的 SVE/SME VL                       │
│  └────────┬────────┘                                         │
│           │                                                   │
│           ▼                                                   │
│  ┌─────────────────┐                                         │
│  │ 4. 设置信号处理 │  SIGCHLD → 追踪子进程退出                │
│  │                 │  SIGINT/SIGTERM → 优雅退出              │
│  └────────┬────────┘                                         │
│           │                                                   │
│           ▼                                                   │
│  ┌─────────────────┐                                         │
│  │ 5. 启动子进程   │  按策略启动所有测试进程                  │
│  └────────┬────────┘                                         │
│           │                                                   │
│           ▼                                                   │
│  ┌─────────────────┐                                         │
│  │ 6. epoll 监控   │  监控所有子进程输出                      │
│  │    循环         │  每秒发送 SIGUSR2                        │
│  │                 │  超时检测                                │
│  └────────┬────────┘                                         │
│           │                                                   │
│           ▼                                                   │
│  ┌─────────────────┐                                         │
│  │ 7. 清理并报告   │  停止所有子进程                          │
│  │    结果         │  检查退出状态和输出                      │
│  └─────────────────┘                                         │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

## 四、关键技术点

### 4.1 向量长度探测 (probe_vls)

```c
static void probe_vls(int vls[], int *vl_count, int set_vl)
{
    unsigned int vq;
    int vl;

    *vl_count = 0;

    // 从最大向量长度开始递减
    for (vq = SVE_VQ_MAX; vq > 0; --vq) {
        // 尝试设置向量长度
        vl = prctl(set_vl, vq * 16);

        if (vl == -1)
            ksft_exit_fail_msg("SET_VL failed: %s (%d)\n",
                               strerror(errno), errno);

        // 提取实际设置的向量长度
        vl &= PR_SVE_VL_LEN_MASK;

        // 根据实际VL重新计算vq，继续递减
        vq = sve_vq_from_vl(vl);

        vls[*vl_count] = vl;
        *vl_count += 1;

        // 最多记录16个向量长度
        if (*vl_count >= MAX_VLS)
            break;
    }
}
```

**说明**：
- `set_vl` 参数可以是 `PR_SVE_SET_VL` 或 `PR_SME_SET_VL`
- 通过尝试设置不同的向量长度，内核会返回实际支持的长度
- 从最大值递减探测，确保获取所有支持的 VL

### 4.2 prctl 系统调用

| prctl 命令 | 用途 | 参数说明 |
|------------|------|----------|
| `PR_SVE_SET_VL` | 设置 SVE 向量长度 | `vl \| PR_SVE_VL_INHERIT` |
| `PR_SME_SET_VL` | 设置 SME 向量长度 | `vl \| PR_SME_VL_INHERIT` |
| `PR_SVE_VL_INHERIT` | VL 继承标志 | 子进程继承父进程的 VL 设置 |
| `PR_SME_VL_INHERIT` | VL 继承标志 | 子进程继承父进程的 VL 设置 |
| `PR_SVE_VL_LEN_MASK` | VL 长度掩码 | 提取向量长度值 |

**向量长度示例**：
```
SVE VL: 128, 256, 384, 512, 640, 768, 896, 1024, 1152, 1280, 1408, 1536 (bytes)
       = 16 * vq, 其中 vq 从 1 到 12 (对应 1-12 个 128-bit 向量)
```

### 4.3 信号处理机制

| 信号 | 处理函数 | 触发时机 | 作用 |
|------|----------|----------|------|
| `SIGUSR2` | 子进程处理 | 每秒发送一次 | 测试信号处理期间的 FP 状态一致性 |
| `SIGCHLD` | `handle_child_signal` | 子进程状态变化 | 记录子进程退出状态 |
| `SIGINT` | `handle_exit_signal` | 用户按 Ctrl+C | 优雅终止所有子进程 |
| `SIGTERM` | `handle_exit_signal` | 外部终止信号 | 优雅终止所有子进程 |

```c
// 每秒向所有子进程发送 SIGUSR2
static void child_tickle(struct child_data *child)
{
    if (child->output_seen && !child->exited)
        kill(child->pid, SIGUSR2);
}
```

**目的**：
- 测试信号处理过程中 FP/SVE/SME 状态的保存和恢复
- 增加调度器压力，使上下文切换更频繁
- 验证信号处理程序不会破坏浮点状态

### 4.4 epoll 多路复用

```c
// 为每个子进程的 stdout 创建 epoll 监控
ev.events = EPOLLIN | EPOLLHUP;
ev.data.ptr = child;
epoll_ctl(epoll_fd, EPOLL_CTL_ADD, child->stdout, &ev);

// 主循环中的 epoll_wait
ret = epoll_wait(epoll_fd, &ev, 1, 1000);  // 1秒超时
```

**设计考虑**：
- `EPOLLIN`: 子进程有输出可读
- `EPOLLHUP`: 子进程关闭了管道（进程退出）
- 1秒超时用于发送 SIGUSR2 和超时计数

### 4.5 超时机制设计

**创新点**：超时按"无输出的秒数"计数，而非绝对时间

```c
ret = epoll_wait(epoll_fd, &ev, 1, 1000);  // 等待1秒

if (ret == 1) {
    // 有事件（输出），处理但不减少超时计数
    child_output(ev.data.ptr, ev.events, false);
} else {
    // 超时（无输出），减少超时计数
    for (i = 0; i < num_children; i++)
        child_tickle(&children[i]);  // 发送 SIGUSR2

    if (--timeout == 0)
        break;  // 超时退出
}
```

**原因**：
在虚拟平台上，测试程序启动可能非常慢：
- 模拟器本身执行速度慢
- 支持的向量长度多（可能有十几个不同的 VL）
- 每个进程都需要初始化 FP/SVE/SME 状态

这种设计确保测试有足够的启动时间，不会误判超时。

---

## 五、硬件能力检测

### 5.1 HWCAP 检测

```c
// SVE (Scalable Vector Extension) 检测
if (getauxval(AT_HWCAP) & HWCAP_SVE) {
    probe_vls(sve_vls, &sve_vl_count, PR_SVE_SET_VL);
    tests += sve_vl_count * cpus;
}

// SME (Scalable Matrix Extension) 检测
if (getauxval(AT_HWCAP2) & HWCAP2_SME) {
    probe_vls(sme_vls, &sme_vl_count, PR_SME_SET_VL);
    tests += sme_vl_count * cpus * 2;
}
```

### 5.2 ARM64 FP/SVE/SME 架构概述

```
┌─────────────────────────────────────────────────────────────────┐
│                    ARM64 SIMD 架构演进                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  FPSIMD (基础)                                                  │
│  ├── 32 × 128-bit 浮点/向量寄存器 (v0-v31)                     │
│  └── 支持 ASIMD 指令集                                          │
│                                                                 │
│  SVE (Scalable Vector Extension)                               │
│  ├── 可变长度向量寄存器 (128-2048 bits)                         │
│  ├── 谓词寄存器 (P0-P15)                                        │
│  └── 向量长度与实现相关                                         │
│                                                                 │
│  SME (Scalable Matrix Extension)                               │
│  ├── Streaming SVE 模式 (SSVE)                                 │
│  ├── ZA 矩阵寄存器 (用于矩阵乘法)                               │
│  └── SVL (Streaming Vector Length) 可能与 SVE VL 不同           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 上下文切换状态

| 特性 | 需要保存的状态 |
|------|----------------|
| FPSIMD | v0-v31 (32 × 128-bit) + FPSR + FPCR |
| SVE | z0-z31 (可变长度) + p0-p15 (16 × 16-bit) + FFR + SVCR |
| SME (SSVE模式) | z0-z31 + p0-p15 + SVCR (SM, ZA位) |
| SME (ZA状态) | ZA 矩阵寄存器 (最大 ~8KB) |

---

## 六、测试覆盖范围

### 6.1 测试目标

| 测试类型 | 覆盖内容 |
|----------|----------|
| **FPSIMD 上下文切换** | 基础浮点/向量寄存器的保存和恢复 |
| **SVE 状态管理** | 可变长度向量寄存器、谓词寄存器、FFR |
| **SME 流程模式** | Streaming SVE 状态 |
| **ZA 矩阵寄存器** | SME 特有的矩阵乘法寄存器 |
| **信号处理** | SIGUSR2 期间的 FP 状态一致性 |
| **并发压力** | 多进程同时竞争 CPU 导致频繁切换 |
| **多 VL 覆盖** | 所有硬件支持的向量长度 |

### 6.2 各测试程序说明

| 程序 | 功能 | 向量长度设置 |
|------|------|--------------|
| `fpsimd-test` | FPSIMD 上下文切换测试 | 默认 |
| `sve-test` | SVE 状态测试 | 通过 `PR_SVE_SET_VL` 设置 |
| `ssve-test` | Streaming SVE 测试 | 通过 `PR_SME_SET_VL` 设置 |
| `za-test` | ZA 矩阵寄存器测试 | 通过 `PR_SME_SET_VL` 设置 |

---

## 七、命令行使用

### 7.1 基本用法

```bash
# 默认运行 10 秒
./fp-stress

# 运行 60 秒
./fp-stress -t 60

# 无超时，手动终止 (Ctrl+C)
./fp-stress -t 0
```

### 7.2 输出示例

```
TAP version 13
1..24
# 8 CPUs, 12 SVE VLs, 4 SME VLs
# Will run for 10s
# Started FPSIMD-0-0
# Started FPSIMD-0-1
# Started SVE-VL-128-0
# Started SVE-VL-256-0
...
# FPSIMD-0-0: Running with FPSIMD
# FPSIMD-0-0: Got SIGUSR2
# FPSIMD-0-0: Got SIGUSR2
...
# Finishing up...
ok FPSIMD-0-0
ok FPSIMD-0-1
ok SVE-VL-128-0
...
# Total Tests: 24
# Passed: 24
# Failed: 0
```

---

## 八、与内核的交互

### 8.1 内核接口调用

```
┌─────────────────────────────────────────────────────────────┐
│                   fp-stress 与内核交互                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  用户空间                          内核空间                   │
│  ─────────                        ─────────                  │
│                                                             │
│  fp-stress                                            内核   │
│     │                                                   │    │
│     ├── getauxval(AT_HWCAP)  ──────────────────→  读取硬件  │
│     │                                           能力标志    │
│     ├── prctl(PR_SVE_SET_VL) ─────────────────→  设置 SVE  │
│     │                                           向量长度    │
│     ├── prctl(PR_SME_SET_VL) ─────────────────→  设置 SME  │
│     │                                           向量长度    │
│     │                                                   │    │
│     ├── fork() ────────────────────────────────→  创建子   │
│     │                                             进程     │
│     │                                                   │    │
│     ├── kill(SIGUSR2) ─────────────────────────→  发送信号 │
│     │                                                   │    │
│     │                                             上下文    │
│     │  ←──────────────────────────────────────  切换时    │
│     │              保存/恢复 FP/SVE/SME 状态               │
│     │                                                   │    │
│     └── waitpid() ─────────────────────────────→  等待子   │
│                                                  进程退出   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 测试的内核代码路径

```
内核中与 FP/SVE/SME 相关的代码：

arch/arm64/include/asm/fpsimd.h       FPSIMD/SVE 头文件
arch/arm64/include/asm/fpsimdmacros.h FPSIMD 汇编宏
arch/arm64/kernel/fpsimd.c            FPSIMD/SVE 核心实现
arch/arm64/kernel/entry-fpsimd.S      异常入口/出口的 FPSIMD 处理
arch/arm64/kvm/fpsimd.c               KVM FPSIMD 支持
arch/arm64/kvm/hyp/fpsimd.S           KVM Hypervisor FPSIMD
```

---

## 九、技术亮点与设计考量

### 9.1 技术亮点

1. **全面覆盖**：自动探测所有支持的向量长度，确保测试覆盖完整

2. **灵活的超时机制**：按"无输出秒数"计数，适应不同平台性能差异

3. **信号处理测试**：通过定期发送 SIGUSR2，验证信号处理不会破坏 FP 状态

4. **高效 I/O 处理**：使用 epoll 管理大量子进程的输出

5. **优雅退出**：完整的信号处理和子进程清理机制

### 9.2 设计考量

| 考量 | 解决方案 |
|------|----------|
| 虚拟平台启动慢 | 超时按无输出时间计数 |
| 多种 VL 需要测试 | 自动探测并启动对应数量的测试进程 |
| 需要产生上下文切换压力 | 每个CPU启动多个进程，数量超过CPU核心数 |
| 测试信号处理 | 每秒发送 SIGUSR2 |
| 集成到 kselftest | 使用 ksft_* 辅助函数，输出 TAP 格式 |

---

## 十、总结

这个补丁为 ARM64 平台提供了一个完整的浮点/向量上下文切换压力测试工具：

1. **自动化集成** - 完全集成到 kselftest 框架，支持 CI
2. **全面测试** - 覆盖 FPSIMD/SVE/SME/ZA，所有支持的向量长度
3. **并发压力** - 通过多进程并发测试上下文切换
4. **信号处理** - 验证信号处理过程中的状态一致性
5. **跨平台** - 设计考虑了从高性能硬件到慢速模拟器的各种场景

该工具对确保 ARM64 Linux 内核在 FP/SVE/SME 功能上的稳定性具有重要意义。
