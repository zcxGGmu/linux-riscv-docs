# fp-stress.c 代码详细分析文档

> **文件路径**: `tools/testing/selftests/arm64/fp/fp-stress.c`
> **版权**: Copyright (C) 2022 ARM Limited
> **许可证**: GPL-2.0-only
> **作者**: Mark Brown <broonie@kernel.org>

---

## 目录

1. [概述](#1-概述)
2. [头文件与宏定义](#2-头文件与宏定义)
3. [数据结构](#3-数据结构)
4. [全局变量](#4-全局变量)
5. [核心函数详解](#5-核心函数详解)
6. [主函数流程](#6-主函数流程)
7. [同步机制](#7-同步机制)
8. [信号处理](#8-信号处理)
9. [epoll 事件处理](#9-epoll-事件处理)
10. [硬件探测](#10-硬件探测)
11. [测试启动策略](#11-测试启动策略)
12. [代码流程图](#12-代码流程图)
13. [关键设计模式](#13-关键设计模式)

---

## 1. 概述

### 1.1 功能定位

`fp-stress.c` 是 ARM64 平台浮点/向量上下文切换压力测试的 **kselftest 集成工具**。它的核心目标是：

```
┌─────────────────────────────────────────────────────────────┐
│                    核心测试目标                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 验证 FP/SVE/SME 状态在进程上下文切换中的正确保存/恢复     │
│                                                             │
│  2. 测试所有硬件支持的向量长度 (VL)                         │
│                                                             │
│  3. 验证信号处理过程中浮点状态的一致性                       │
│                                                             │
│  4. 通过高并发测试发现潜在的竞态条件                         │
│                                                             │
│  5. 集成到 kselftest 框架，支持 CI 自动化测试                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 架构关系

```
┌─────────────────────────────────────────────────────────────┐
│                    测试工具层次结构                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                   fp-stress (本文件)                        │
│                          │                                  │
│                          │  fork + execl                    │
│                          ▼                                  │
│  ┌────────────────────────────────────────────────────┐   │
│  │              子测试进程                             │   │
│  ├────────────────────────────────────────────────────┤   │
│  │  • fpsimd-test   → FPSIMD 基础测试                  │   │
│  │  • sve-test      → SVE 可变长度向量测试              │   │
│  │  • ssve-test     → Streaming SVE 测试               │   │
│  │  • za-test       → ZA 矩阵寄存器测试                 │   │
│  │  • zt-test       → ZT 矩阵寄存器测试 (SME2)          │   │
│  │  • kernel-test   → 内核 FP 状态测试                  │   │
│  └────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 头文件与宏定义

### 2.1 头文件包含分析

```c
#define _GNU_SOURCE           // 启用 GNU 扩展功能
#define _POSIX_C_SOURCE 199309L  // POSIX.1c (线程支持)
```

| 头文件 | 用途 | 关键函数/宏 |
|--------|------|-------------|
| `<errno.h>` | 错误码 | `errno`, `EINTR`, `EPIPE` |
| `<getopt.h>` | 命令行参数解析 | `getopt_long()`, `struct option` |
| `<poll.h>` | I/O 多路复用 | `poll()` (本代码用 epoll 替代) |
| `<signal.h>` | 信号处理 | `sigaction()`, `siginfo_t`, `kill()` |
| `<sys/auxv.h>` | 辅助向量访问 | `getauxval(AT_HWCAP)` |
| `<sys/epoll.h>` | epoll I/O | `epoll_create1()`, `epoll_ctl()`, `epoll_wait()` |
| `<sys/prctl.h>` | 进程操作 | `prctl(PR_SVE_SET_VL)` |
| `<sys/wait.h>` | 进程等待 | `waitpid()`, `WIFEXITED()`, `WEXITSTATUS()` |
| `<asm/hwcap.h>` | 硬件能力标志 | `HWCAP_SVE`, `HWCAP2_SME`, `HWCAP2_SME2` |
| `"../../kselftest.h"` | kselftest 框架 | `ksft_print_msg()`, `ksft_exit_fail_msg()` |

### 2.2 宏定义

```c
#define MAX_VLS 16                      // 最大向量长度数量
#define SIGNAL_INTERVAL_MS 25           // 信号发送间隔 (毫秒)
#define LOG_INTERVALS (1000 / SIGNAL_INTERVAL_MS)  // 40 (每秒打印一次日志)
```

**设计考量**：
- `SIGNAL_INTERVAL_MS = 25ms`：每秒发送 40 次信号，产生频繁的信号处理压力
- `MAX_VLS = 16`：足以覆盖当前 ARM 实现的所有向量长度
- `LOG_INTERVALS = 40`：每秒打印一次超时进度，避免日志刷屏

---

## 3. 数据结构

### 3.1 struct child_data

```c
struct child_data {
    char *name;        // 测试名称，格式如 "FPSIMD-0-0", "SVE-VL-256-1"
    char *output;      // 输出缓冲区，存储不完整的行（未遇到 \n）
    pid_t pid;         // 子进程 PID
    int stdout;        // stdout 管道读端 (epoll 监控的 fd)
    bool output_seen;  // 是否收到过输出（用于判断进程是否真正运行）
    bool exited;       // 进程是否已退出
    int exit_status;   // 进程退出状态码
};
```

**状态机转换**：

```
┌─────────────────────────────────────────────────────────────┐
│              child_data 状态转换图                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   [fork 后]                                                 │
│      │                                                      │
│      ▼                                                      │
│   ┌─────────┐    [收到输出]    ┌──────────────┐            │
│   │ 初始    │  ──────────────> │ 运行中       │            │
│   │         │                  │ output_seen  │            │
│   │ exited  │                  │ = true       │            │
│   │ = false │                  └──────────────┘            │
│   └─────────┘         │               │                    │
│      │               │               │ [SIGCHLD]          │
│      │               │               ▼                    │
│      │               │            ┌──────────┐             │
│      │               │            │ 已退出   │             │
│      │               │            │ exited   │             │
│      │               │            │ = true   │             │
│      │               │            └──────────┘             │
│      ▼               │               │                    │
│   [等待 waitpid] <────┘               ▼                    │
│      │                            [cleanup]               │
│      ▼                                                      │
│   [资源释放]                                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**内存管理**：
```c
// output 字段的生命周期
output = NULL
    │
    │ [读取不完整的行]
    ▼
output = malloc(...)  ← asprintf() 分配
    │
    │ [读取完整行后打印并 free]
    ▼
output = NULL

// 最后在 child_cleanup() 或 flush 时检查并释放
if (output) {
    ksft_print_msg(..., "<EOF>");
    free(output);
    output = NULL;
}
```

---

## 4. 全局变量

```c
static int epoll_fd;                      // epoll 实例文件描述符
static struct child_data *children;       // 所有子进程数据数组
static struct epoll_event *evs;           // epoll 事件数组
static int tests;                         // 总测试数量
static int num_children;                  // 实际启动的子进程数
static bool terminate;                    // 退出标志（收到 SIGINT/SIGTERM）
static int startup_pipe[2];               // 启动同步管道 [读端, 写端]
```

**变量用途表**：

| 变量 | 作用域 | 生命周期 | 说明 |
|------|--------|----------|------|
| `epoll_fd` | 全局 | 整个程序运行期间 | 用于监控所有子进程的 stdout |
| `children` | 全局 | 整个程序运行期间 | 存储所有子进程的状态信息 |
| `evs` | 全局 | 主循环中 | epoll_wait() 的事件缓冲区 |
| `tests` | 全局 | 初始化后只读 | 计划的测试数量（用于 kselftest） |
| `num_children` | 全局 | 启动子进程时递增 | 实际启动的子进程计数 |
| `terminate` | 全局 | 信号处理函数设置 | 优雅退出标志 |
| `startup_pipe` | 全局 | 子进程启动后关闭 | 同步子进程启动的屏障 |

---

## 5. 核心函数详解

### 5.1 num_processors() - 获取 CPU 数量

```c
static int num_processors(void)
{
    long nproc = sysconf(_SC_NPROCESSORS_CONF);
    if (nproc < 0) {
        perror("Unable to read number of processors\n");
        exit(EXIT_FAILURE);
    }

    return nproc;
}
```

**技术细节**：
- `sysconf(_SC_NPROCESSORS_CONF)` 返回系统配置的 CPU 数量
- 不是 `_SC_NPROCESSORS_ONLN`（在线 CPU），因为即使某些 CPU 离线也要测试
- 返回值用于计算需要启动的测试进程数量

### 5.2 child_start() - 启动子进程

这是整个程序最复杂的函数之一，实现了完整的子进程启动和管道管理。

```c
static void child_start(struct child_data *child, const char *program)
{
    int ret, pipefd[2], i;
    struct epoll_event ev;

    // 步骤 1: 创建 stdout 捕获管道
    ret = pipe(pipefd);
    if (ret != 0)
        ksft_exit_fail_msg("Failed to create stdout pipe: %s (%d)\n",
                           strerror(errno), errno);

    // 步骤 2: fork 创建子进程
    child->pid = fork();
    if (child->pid == -1)
        ksft_exit_fail_msg("fork() failed: %s (%d)\n",
                           strerror(errno), errno);

    if (!child->pid) {
        // ===== 子进程代码路径 =====

        // 步骤 3: 重定向 stdout 到管道写端
        ret = dup2(pipefd[1], 1);
        if (ret == -1) {
            printf("dup2() %d\n", errno);
            exit(EXIT_FAILURE);
        }

        // 步骤 4: 复制 startup pipe 读端到 FD 3
        ret = dup2(startup_pipe[0], 3);
        if (ret == -1) {
            printf("dup2() %d\n", errno);
            exit(EXIT_FAILURE);
        }

        // 步骤 5: 关闭所有其他文件描述符 (4-8191)
        for (i = 4; i < 8192; i++)
            close(i);

        // 步骤 6: 阻塞读取 startup pipe（等待所有子进程启动完成）
        ret = read(3, &i, sizeof(i));
        if (ret < 0)
            printf("read(startp pipe) failed: %s (%d)\n",
                   strerror(errno), errno);
        if (ret > 0)
            printf("%d bytes of data on startup pipe\n", ret);
        close(3);

        // 步骤 7: 执行测试程序
        ret = execl(program, program, NULL);
        printf("execl(%s) failed: %d (%s)\n",
               program, errno, strerror(errno));

        exit(EXIT_FAILURE);
    } else {
        // ===== 父进程代码路径 =====

        // 步骤 8: 关闭管道写端（只保留读端）
        close(pipefd[1]);
        child->stdout = pipefd[0];
        child->output = NULL;
        child->exited = false;
        child->output_seen = false;

        // 步骤 9: 将 stdout 读端加入 epoll 监控
        ev.events = EPOLLIN | EPOLLHUP;
        ev.data.ptr = child;

        ret = epoll_ctl(epoll_fd, EPOLL_CTL_ADD, child->stdout, &ev);
        if (ret < 0) {
            ksft_exit_fail_msg("%s EPOLL_CTL_ADD failed: %s (%d)\n",
                               child->name, strerror(errno), errno);
        }
    }
}
```

**启动同步机制详解**：

```
┌─────────────────────────────────────────────────────────────┐
│                  子进程启动同步机制                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   父进程                          子进程 (N 个)             │
│   ─────                          ──────────────            │
│                                                             │
│   pipe(startup_pipe)               fork()                   │
│   ┌────────┬────────┐              │                       │
│   │ [0] 读 │ [1] 写 │              ▼                       │
│   └────────┴────────┘         ┌─────────┐                 │
│                               │ dup2()  │ 重定向 stdout    │
│                               │ close() │ 关闭其他 FD       │
│                               └────┬────┘                 │
│                                    │                       │
│                                    ▼                       │
│   ┌─────────────────────────────────────────────┐          │
│   │  read(3, ...) 阻塞在这里                    │          │
│   │  等待 pipe[0] 关闭 (EOF)                    │          │
│   └─────────────────────────────────────────────┘          │
│                                    │                       │
│   fork() N 个子进程                │                       │
│   ────────────────                 │                       │
│                                    │                       │
│   所有子进程启动完成               │                       │
│   ────────────────                 │                       │
│                                    │                       │
│   close(startup_pipe[0]) ──────────► 所有子进程 read 返回   │
│   close(startup_pipe[1])           │                       │
│                                    ▼                       │
│                               execl(test)                  │
│                               ─────────                    │
│                                                             │
│   好处:                                                      │
│   1. 所有子进程几乎同时开始执行测试                          │
│   2. 避免先启动的进程占满 CPU，后启动的进程饥饿             │
│   3. 确保测试的并发性和公平性                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**文件描述符布局**：

```
子进程启动后的 FD 布局：

FD 0: stdin    (继承自父进程)
FD 1: stdout   → pipe[1] (重定向到父进程)
FD 2: stderr   (继承自父进程，直接输出到终端)
FD 3: startup_pipe[0] (复制自父进程，用于同步)
FD 4-8191: 全部关闭
```

### 5.3 child_output_read() - 读取子进程输出

```c
static bool child_output_read(struct child_data *child)
{
    char read_data[1024];
    char work[1024];
    int ret, len, cur_work, cur_read;

    // 步骤 1: 从管道读取数据
    ret = read(child->stdout, read_data, sizeof(read_data));

    // 步骤 2: 处理读取错误
    if (ret < 0) {
        if (errno == EINTR)  // 被信号中断，需要继续读
            return true;

        ksft_print_msg("%s: read() failed: %s (%d)\n",
                       child->name, strerror(errno), errno);
        return false;  // 其他错误，停止读取
    }
    len = ret;

    // 步骤 3: 标记已收到输出
    child->output_seen = true;

    // 步骤 4: 处理之前未完成的部分行
    if (child->output) {
        strncpy(work, child->output, sizeof(work) - 1);
        cur_work = strnlen(work, sizeof(work));
        free(child->output);
        child->output = NULL;
    } else {
        cur_work = 0;
    }

    // 步骤 5: 逐字符处理，按 \n 分行
    cur_read = 0;
    while (cur_read < len) {
        work[cur_work] = read_data[cur_read++];

        if (work[cur_work] == '\n') {
            work[cur_work] = '\0';
            ksft_print_msg("%s: %s\n", child->name, work);
            cur_work = 0;
        } else {
            cur_work++;
        }
    }

    // 步骤 6: 保存未完成的行（没有 \n 结尾）
    if (cur_work) {
        work[cur_work] = '\0';
        ret = asprintf(&child->output, "%s", work);
        if (ret == -1)
            ksft_exit_fail_msg("Out of memory\n");
    }

    return false;  // 这次读取已完成
}
```

**输出处理流程图**：

```
┌─────────────────────────────────────────────────────────────┐
│                  输出处理流程                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   从管道读取的数据流:                                        │
│                                                             │
│   "First line\nSecond line\nThird "                         │
│                             │                               │
│                             ▼                               │
│   ┌─────────────────────────────────────────────────┐      │
│   │ child->output = "Third " (未完成，没有 \n)       │      │
│   └─────────────────────────────────────────────────┘      │
│                                                             │
│   下次读取: "\nFourth line\n"                               │
│                             │                               │
│                             ▼                               │
│   ┌─────────────────────────────────────────────────┐      │
│   │ 1. 恢复: work = "Third "                          │      │
│   │ 2. 追加: work = "Third \n"                        │      │
│   │ 3. 打印: "child: Third "                         │      │
│   │ 4. 继续: work = "Fourth line"                    │      │
│   │ 5. 保存: child->output = "Fourth line"          │      │
│   └─────────────────────────────────────────────────┘      │
│                                                             │
│   进程退出时 (EPOLLHUP):                                    │
│   打印: "child: Fourth line<EOF>"                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.4 child_output() - 处理 epoll 事件

```c
static void child_output(struct child_data *child, uint32_t events,
                         bool flush)
{
    bool read_more;

    // 处理 EPOLLIN: 数据可读
    if (events & EPOLLIN) {
        do {
            read_more = child_output_read(child);
        } while (read_more);  // 如果被 EINTR 中断，继续读
    }

    // 处理 EPOLLHUP: 管道写端关闭（进程退出）
    if (events & EPOLLHUP) {
        close(child->stdout);
        child->stdout = -1;
        flush = true;  // 强制刷新缓冲区
    }

    // 刷新输出缓冲区
    if (flush && child->output) {
        ksft_print_msg("%s: %s<EOF>\n", child->name, child->output);
        free(child->output);
        child->output = NULL;
    }
}
```

**事件处理逻辑**：

```
epoll 返回的事件组合:

EPOLLIN:   数据可读 → 调用 child_output_read()
EPOLLHUP:  管道关闭 → 关闭 fd, 强制 flush
EPOLLIN | EPOLLHUP: 先读数据，再关闭

═══════════════════════════════════════════════════════════════

为什么会有 EPOLLIN | EPOLLHUP?

当进程退出时:
1. 内核关闭管道写端
2. 如果管道里还有数据，EPOLLIN | EPOLLHUP 同时触发
3. 先读完剩余数据 (EPOLLIN)，然后关闭 (EPOLLHUP)
```

### 5.5 child_tickle() - 发送测试信号

```c
static void child_tickle(struct child_data *child)
{
    if (child->output_seen && !child->exited)
        kill(child->pid, SIGUSR1);
}
```

**为什么叫 "tickle"**：
- "tickle" 是"挠痒痒"的意思
- 不是杀死进程，而是给进程一点"刺激"
- 测试进程会捕获 SIGUSR1 并验证 FP 状态

**信号频率**：
- 主循环中每 25ms 调用一次
- 每秒发送 40 次 SIGUSR1
- 产生频繁的信号处理压力

### 5.6 child_stop() - 停止子进程

```c
static void child_stop(struct child_data *child)
{
    if (!child->exited)
        kill(child->pid, SIGTERM);
}
```

**为什么用 SIGTERM 而不是 SIGKILL**：
- SIGTERM 允许进程优雅退出
- 测试进程可以清理资源
- 如果进程没有响应 SIGTERM，父进程会在 waitpid 中阻塞

### 5.7 child_cleanup() - 清理子进程

```c
static void child_cleanup(struct child_data *child)
{
    pid_t ret;
    int status;
    bool fail = false;

    // 步骤 1: 等待子进程退出
    if (!child->exited) {
        do {
            ret = waitpid(child->pid, &status, 0);
            if (ret == -1 && errno == EINTR)
                continue;  // 被信号中断，重试

            if (ret == -1) {
                ksft_print_msg("waitpid(%d) failed: %s (%d)\n",
                               child->pid, strerror(errno), errno);
                fail = true;
                break;
            }
        } while (!WIFEXITED(status));  // 等到进程正常退出
        child->exit_status = WEXITSTATUS(status);
    }

    // 步骤 2: 检查是否有输出
    if (!child->output_seen) {
        ksft_print_msg("%s no output seen\n", child->name);
        fail = true;
    }

    // 步骤 3: 检查退出码
    if (child->exit_status != 0) {
        ksft_print_msg("%s exited with error code %d\n",
                       child->name, child->exit_status);
        fail = true;
    }

    // 步骤 4: 报告测试结果
    ksft_test_result(!fail, "%s\n", child->name);
}
```

**失败条件**：
1. `waitpid()` 失败
2. 从未收到输出（进程可能没有真正运行）
3. 退出码非零

---

## 6. 主函数流程

### 6.1 main() 函数结构

```c
int main(int argc, char **argv)
{
    // ========== 阶段 1: 初始化 ==========
    // 1.1 解析命令行参数
    // 1.2 获取 CPU 数量
    // 1.3 检测硬件能力 (HWCAP)
    // 1.4 探测支持的向量长度

    // ========== 阶段 2: 资源准备 ==========
    // 2.1 创建 epoll 实例
    // 2.2 创建 startup_pipe
    // 2.3 设置信号处理
    // 2.4 分配内存

    // ========== 阶段 3: 启动子进程 ==========
    // 3.1 启动所有测试进程
    // 3.2 关闭 startup_pipe (释放所有子进程)

    // ========== 阶段 4: 主循环 ==========
    // 4.1 epoll_wait 监控事件
    // 4.2 处理输出
    // 4.3 等待所有子进程启动
    // 4.4 定期发送 SIGUSR1
    // 4.5 超时检测

    // ========== 阶段 5: 清理 ==========
    // 5.1 停止所有子进程
    // 5.2 清理所有子进程
    // 5.3 报告测试结果
}
```

### 6.2 命令行参数解析

```c
static const struct option options[] = {
    { "timeout", required_argument, NULL, 't' },
    { }
};

// 解析逻辑
while ((c = getopt_long(argc, argv, "t:", options, NULL)) != -1) {
    switch (c) {
    case 't':
        ret = sscanf(optarg, "%d", &timeout);
        if (ret != 1)
            ksft_exit_fail_msg("Failed to parse timeout %s\n", optarg);
        break;
    default:
        ksft_exit_fail_msg("Unknown argument\n");
    }
}
```

**超时值说明**：

| 值 | 含义 |
|---|-----|
| `> 0` | 运行指定次数的信号间隔（25ms 单位） |
| `= 0` | 无超时，手动终止 (Ctrl+C) |
| 默认 | `10 * (1000 / 25) = 400` 次间隔 = 10 秒 |

### 6.3 硬件能力检测

```c
cpus = num_processors();
tests = 0;

// SVE 检测
if (getauxval(AT_HWCAP) & HWCAP_SVE) {
    probe_vls(sve_vls, &sve_vl_count, PR_SVE_SET_VL);
    tests += sve_vl_count * cpus;
} else {
    sve_vl_count = 0;
}

// SME 检测
if (getauxval(AT_HWCAP2) & HWCAP2_SME) {
    probe_vls(sme_vls, &sme_vl_count, PR_SME_SET_VL);
    tests += sme_vl_count * cpus * 2;  // SSVE + ZA
} else {
    sme_vl_count = 0;
}

// SME2 检测
if (getauxval(AT_HWCAP2) & HWCAP2_SME2) {
    tests += cpus;  // ZT 测试
    have_sme2 = true;
} else {
    have_sme2 = false;
}

// FPSIMD + KERNEL 测试 (每个 CPU 2 个)
tests += cpus * 2;
```

**测试数量计算公式**：

```
总测试数 = cpus × 2                           // FPSIMD + KERNEL
         + cpus × sve_vl_count               // SVE (每个 VL)
         + cpus × sme_vl_count × 2           // SSVE + ZA (每个 VL)
         + cpus × (have_sme2 ? 1 : 0)        // ZT (如果支持 SME2)
```

### 6.4 主循环详解

```c
for (;;) {
    // 检查退出标志
    if (terminate)
        break;

    // epoll_wait 超时机制
    ret = epoll_wait(epoll_fd, evs, tests, poll_interval);
    if (ret < 0) {
        if (errno == EINTR)
            continue;
        ksft_exit_fail_msg("epoll_wait() failed: %s (%d)\n",
                           strerror(errno), errno);
    }

    // 有事件：处理输出
    if (ret > 0) {
        for (i = 0; i < ret; i++) {
            child_output(evs[i].data.ptr, evs[i].events, false);
        }
        continue;  // 有输出时不减少超时
    }

    // epoll_wait 超时

    // 检查所有子进程是否已启动
    if (!all_children_started) {
        seen_children = 0;
        for (i = 0; i < num_children; i++)
            if (children[i].output_seen || children[i].exited)
                seen_children++;

        if (seen_children != num_children) {
            ksft_print_msg("Waiting for %d children\n",
                           num_children - seen_children);
            continue;  // 还有子进程未启动，继续等待
        }

        all_children_started = true;
        poll_interval = SIGNAL_INTERVAL_MS;  // 切换到 25ms 间隔
    }

    // 定期打印进度
    if ((timeout % LOG_INTERVALS) == 0)
        ksft_print_msg("Sending signals, timeout remaining: %d\n",
                       timeout);

    // 发送 SIGUSR1
    for (i = 0; i < num_children; i++)
        child_tickle(&children[i]);

    // 超时检测
    if (timeout < 0)
        continue;  // 无超时限制
    if (--timeout == 0)
        break;
}
```

**超时计数机制**：

```
初始状态:
  poll_interval = 5000ms
  timeout = 400 (10秒 / 25ms)

等待子进程启动阶段 (poll_interval = 5000ms):
  每次 epoll_wait 超时不减少 timeout
  只检查是否所有子进程都有输出

所有子进程启动后:
  poll_interval = 25ms
  每次 epoll_wait 超时后 timeout--
  每 40 次 (timeout % 40 == 0) 打印一次进度

超时退出:
  timeout 减到 0 时退出循环
```

---

## 7. 同步机制

### 7.1 启动同步 (startup_pipe)

```c
// 创建管道
ret = pipe(startup_pipe);

// 在每个子进程中
dup2(startup_pipe[0], 3);
close(startup_pipe[1]);  // 子进程关闭写端

for (i = 4; i < 8192; i++)
    close(i);

read(3, &i, sizeof(i));  // 阻塞直到管道关闭
close(3);

// 在父进程中，所有子进程 fork 完成后
close(startup_pipe[0]);  // 触发所有子进程的 read 返回 0 (EOF)
close(startup_pipe[1]);
```

**时序图**：

```
父进程                      子进程1    子进程2    子进程N
  │                           │          │          │
  │ pipe(startup_pipe)        │          │          │
  ├──────────────────────────►│          │          │
  │ fork()                    │          │          │
  ├──────────────────────────►│          │          │
  │ fork()                    │          │          │
  │                           ├──────────►│          │
  │ ...                       │          │          │
  │                           │          │          │
  │ close(startup_pipe[0])    │          │          │
  │ ──────────────────────────┼──────────┼─────────►│
  │                           │          │          │
  │                           read 返回  read 返回  read 返回
  │                           │          │          │
  │                           execl()   execl()   execl()
  │                           │          │          │
```

### 7.2 等待所有子进程启动

```c
if (!all_children_started) {
    seen_children = 0;
    for (i = 0; i < num_children; i++)
        if (children[i].output_seen || children[i].exited)
            seen_children++;

    if (seen_children != num_children) {
        ksft_print_msg("Waiting for %d children\n",
                       num_children - seen_children);
        continue;
    }

    all_children_started = true;
    poll_interval = SIGNAL_INTERVAL_MS;
}
```

**为什么要等待所有子进程启动**：

1. **确保测试公平性**：所有子进程同时开始，先启动的不会占优
2. **正确统计超时**：超时应该从所有测试真正运行开始计时
3. **避免误判**：慢速启动的进程（大 VL）不应导致超时

---

## 8. 信号处理

### 8.1 SIGCHLD 处理

```c
static void handle_child_signal(int sig, siginfo_t *info, void *context)
{
    int i;
    bool found = false;

    for (i = 0; i < num_children; i++) {
        if (children[i].pid == info->si_pid) {
            children[i].exited = true;
            children[i].exit_status = info->si_status;
            found = true;
            break;
        }
    }

    if (!found)
        ksft_print_msg("SIGCHLD for unknown PID %d with status %d\n",
                       info->si_pid, info->si_status);
}
```

**使用 SA_SIGINFO 的好处**：
- `siginfo_t->si_pid` 直接获取退出进程的 PID
- `siginfo_t->si_status` 获取退出状态
- 避免在信号处理函数中调用 `waitpid()`

### 8.2 SIGINT/SIGTERM 处理

```c
static void handle_exit_signal(int sig, siginfo_t *info, void *context)
{
    int i;

    // 防止重复处理
    if (terminate)
        return;

    ksft_print_msg("Got signal, exiting...\n");

    terminate = true;

    // 立即停止所有子进程
    for (i = 0; i < num_children; i++)
        child_stop(&children[i]);
}
```

**为什么要立即停止子进程**：
- 主循环的 `terminate` 检查可能在下一次 epoll_wait
- 立即发送 SIGTERM 可以更快响应
- 主循环会负责 waitpid 和清理

### 8.3 信号处理设置

```c
memset(&sa, 0, sizeof(sa));
sa.sa_sigaction = handle_exit_signal;
sa.sa_flags = SA_RESTART | SA_SIGINFO;
sigemptyset(&sa.sa_mask);

ret = sigaction(SIGINT, &sa, NULL);
ret = sigaction(SIGTERM, &sa, NULL);

sa.sa_sigaction = handle_child_signal;
ret = sigaction(SIGCHLD, &sa, NULL);
```

**标志说明**：
- `SA_RESTART`：被中断的系统调用自动重启
- `SA_SIGINFO`：使用 `sa_sigaction` 而非 `sa_handler`

---

## 9. epoll 事件处理

### 9.1 epoll 初始化

```c
// 创建 epoll 实例
epoll_fd = epoll_create1(EPOLL_CLOEXEC);

// 分配事件数组
evs = calloc(tests, sizeof(*evs));

// 为每个子进程的 stdout 添加监控
ev.events = EPOLLIN | EPOLLHUP;
ev.data.ptr = child;
epoll_ctl(epoll_fd, EPOLL_CTL_ADD, child->stdout, &ev);
```

### 9.2 epoll 调用模式

```c
// 非阻塞模式（处理完所有待处理事件）
static void drain_output(bool flush)
{
    int ret = 1;
    int i;

    while (ret > 0) {
        ret = epoll_wait(epoll_fd, evs, tests, 0);
        if (ret < 0) {
            if (errno == EINTR)
                continue;
            ksft_print_msg("epoll_wait() failed: %s (%d)\n",
                           strerror(errno), errno);
        }

        for (i = 0; i < ret; i++)
            child_output(evs[i].data.ptr, evs[i].events, flush);
    }
}

// 主循环中的阻塞模式
ret = epoll_wait(epoll_fd, evs, tests, poll_interval);
```

### 9.3 事件处理策略

```
┌─────────────────────────────────────────────────────────────┐
│                   epoll 事件处理策略                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   EPOLLIN 事件:                                             │
│   ├── 调用 child_output_read() 读取数据                     │
│   ├── 如果返回 true (EINTR)，继续读取                        │
│   └── 直到返回 false 或没有更多数据                          │
│                                                             │
│   EPOLLHUP 事件:                                            │
│   ├── 关闭 stdout fd                                        │
│   ├── 设置 child->stdout = -1                               │
│   └── 强制刷新输出缓冲区                                     │
│                                                             │
│   EPOLLIN | EPOLLHUP:                                       │
│   ├── 先处理 EPOLLIN（读完剩余数据）                         │
│   └── 再处理 EPOLLHUP（关闭和刷新）                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 10. 硬件探测

### 10.1 probe_vls() - 向量长度探测

```c
static void probe_vls(int vls[], int *vl_count, int set_vl)
{
    unsigned int vq;
    int vl;

    *vl_count = 0;

    // 从最大向量量化值开始，每次除以 2
    for (vq = SVE_VQ_MAX; vq > 0; vq /= 2) {
        // 尝试设置向量长度
        vl = prctl(set_vl, vq * 16);
        if (vl == -1)
            ksft_exit_fail_msg("SET_VL failed: %s (%d)\n",
                               strerror(errno), errno);

        // 提取实际设置的向量长度
        vl &= PR_SVE_VL_LEN_MASK;

        // 检查是否重复（硬件不支持更小的 VL）
        if (*vl_count && (vl == vls[*vl_count - 1]))
            break;

        // 根据实际设置的 VL 重新计算 vq
        vq = sve_vq_from_vl(vl);

        // 记录向量长度
        vls[*vl_count] = vl;
        *vl_count += 1;
    }
}
```

**探测算法详解**：

```
假设 SVE_VQ_MAX = 16 (最大 VL = 256 bytes = 2048 bits):

迭代过程:
┌─────┬──────────┬─────────────┬────────────┬──────────────┐
│ vq  │ 尝试 VL  │ prctl 返回  │ 实际 VL    │ 记录?        │
├─────┼──────────┼─────────────┼────────────┼──────────────┤
│ 16  │ 256      │ 256         │ 256        │ 是 [0]       │
│ 8   │ 128      │ 128         │ 128        │ 是 [1]       │
│ 4   │ 64       │ 64          │ 64         │ 是 [2]       │
│ 2   │ 32       │ 32          │ 32         │ 是 [3]       │
│ 1   │ 16       │ 16          │ 16         │ 是 [4]       │
│ 0   │ -        │ -           │ -          │ 结束         │
└─────┴──────────┴─────────────┴────────────┴──────────────┘

如果硬件只支持 128, 256:
┌─────┬──────────┬─────────────┬────────────┬──────────────┐
│ vq  │ 尝试 VL  │ prctl 返回  │ 实际 VL    │ 记录?        │
├─────┼──────────┼─────────────┼────────────┼──────────────┤
│ 16  │ 256      │ 256         │ 256        │ 是 [0]       │
│ 8   │ 128      │ 128         │ 128        │ 是 [1]       │
│ 4   │ 64       │ 128 (舍入)  │ 128        │ 重复，退出   │
└─────┴──────────┴─────────────┴────────────┴──────────────┘

最终结果: vls = [256, 128], vl_count = 2
```

**为什么 vq /= 2**：
- SVE 向量长度总是 16 的倍数
- 实现通常支持 2^n 的长度序列
- 二分查找可以快速找到所有支持的长度

### 10.2 硬件能力标志

```c
// 辅助向量获取
unsigned long hwcap = getauxval(AT_HWCAP);
unsigned long hwcap2 = getauxval(AT_HWCAP2);

// SVE 检测
if (hwcap & HWCAP_SVE) {
    // 支持 SVE
}

// SME 检测
if (hwcap2 & HWCAP2_SME) {
    // 支持 SME
}

// SME2 检测
if (hwcap2 & HWCAP2_SME2) {
    // 支持 SME2 (ZT 寄存器)
}
```

**HWCAP 标志表**：

| 宏 | AT_ 类型 | 功能 | 扩展 |
|-----|----------|------|------|
| `HWCAP_SVE` | AT_HWCAP | Scalable Vector Extension | SVE |
| `HWCAP2_SME` | AT_HWCAP2 | Scalable Matrix Extension | SME |
| `HWCAP2_SME2` | AT_HWCAP2 | SME version 2 | ZT 寄存器 |

---

## 11. 测试启动策略

### 11.1 启动函数族

```c
// FPSIMD 测试
start_fpsimd(&children[num_children++], cpu, 0);

// KERNEL 测试
start_kernel(&children[num_children++], cpu, 0);

// SVE 测试 (每个 VL)
for (j = 0; j < sve_vl_count; j++)
    start_sve(&children[num_children++], sve_vls[j], cpu);

// Streaming SVE 测试 (每个 VL)
for (j = 0; j < sme_vl_count; j++)
    start_ssve(&children[num_children++], sme_vls[j], cpu);

// ZA 测试 (每个 VL)
for (j = 0; j < sme_vl_count; j++)
    start_za(&children[num_children++], sme_vls[j], cpu);

// ZT 测试 (SME2)
if (have_sme2)
    start_zt(&children[num_children++], cpu);
```

### 11.2 各启动函数详解

#### start_sve() - SVE 测试

```c
static void start_sve(struct child_data *child, int vl, int cpu)
{
    int ret;

    // 设置 SVE 向量长度（带继承标志）
    ret = prctl(PR_SVE_SET_VL, vl | PR_SVE_VL_INHERIT);
    if (ret < 0)
        ksft_exit_fail_msg("Failed to set SVE VL %d\n", vl);

    // 生成测试名称
    ret = asprintf(&child->name, "SVE-VL-%d-%d", vl, cpu);
    if (ret == -1)
        ksft_exit_fail_msg("asprintf() failed\n");

    // 启动子进程
    child_start(child, "./sve-test");

    ksft_print_msg("Started %s\n", child->name);
}
```

**PR_SVE_VL_INHERIT 的作用**：
- 设置后，子进程会继承父进程的 SVE VL
- 避免在子进程中再次调用 prctl
- 确保测试程序以正确的 VL 运行

#### start_ssve() - Streaming SVE 测试

```c
static void start_ssve(struct child_data *child, int vl, int cpu)
{
    int ret;

    ret = asprintf(&child->name, "SSVE-VL-%d-%d", vl, cpu);
    if (ret == -1)
        ksft_exit_fail_msg("asprintf() failed\n");

    // 设置 SME 向量长度（启用 Streaming 模式）
    ret = prctl(PR_SME_SET_VL, vl | PR_SME_VL_INHERIT);
    if (ret < 0)
        ksft_exit_fail_msg("Failed to set SME VL %d\n", ret);

    child_start(child, "./ssve-test");

    ksft_print_msg("Started %s\n", child->name);
}
```

**Streaming SVE 模式**：
- SME 的 Streaming SVE 模式
- SVL (Streaming Vector Length) 可以与常规 SVE VL 不同
- 通过 `PR_SME_SET_VL` 激活

#### start_za() - ZA 矩阵寄存器测试

```c
static void start_za(struct child_data *child, int vl, int cpu)
{
    int ret;

    ret = prctl(PR_SME_SET_VL, vl | PR_SVE_VL_INHERIT);
    if (ret < 0)
        ksft_exit_fail_msg("Failed to set SME VL %d\n", ret);

    ret = asprintf(&child->name, "ZA-VL-%d-%d", vl, cpu);
    if (ret == -1)
        ksft_exit_fail_msg("asprintf() failed\n");

    child_start(child, "./za-test");

    ksft_print_msg("Started %s\n", child->name);
}
```

**ZA 寄存器**：
- SME 引入的矩阵乘累加寄存器
- 大小可达 8KB (取决于 VL)
- 需要特殊的上下文切换处理

#### start_zt() - ZT 寄存器测试 (SME2)

```c
static void start_zt(struct child_data *child, int cpu)
{
    int ret;

    ret = asprintf(&child->name, "ZT-%d", cpu);
    if (ret == -1)
        ksft_exit_fail_msg("asprintf() failed\n");

    child_start(child, "./zt-test");

    ksft_print_msg("Started %s\n", child->name);
}
```

**ZT 寄存器**：
- SME2 引入的矩阵转置寄存器
- 用于优化矩阵运算
- 固定大小，不受 VL 影响

### 11.3 测试命名规则

| 测试类型 | 命名格式 | 示例 |
|----------|----------|------|
| FPSIMD | `FPSIMD-{cpu}-{copy}` | `FPSIMD-0-0`, `FPSIMD-3-1` |
| KERNEL | `KERNEL-{cpu}-{copy}` | `KERNEL-0-0`, `KERNEL-7-0` |
| SVE | `SVE-VL-{vl}-{cpu}` | `SVE-VL-256-0`, `SVE-VL-128-3` |
| SSVE | `SSVE-VL-{vl}-{cpu}` | `SSVE-VL-512-1` |
| ZA | `ZA-VL-{vl}-{cpu}` | `ZA-VL-256-2` |
| ZT | `ZT-{cpu}` | `ZT-0`, `ZT-7` |

---

## 12. 代码流程图

### 12.1 程序整体流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        main() 函数                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐                                           │
│  │ 解析命令行参数   │  -t N: 设置超时                            │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │ 获取系统信息     │  CPU 数量, HWCAP                          │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │ 探测向量长度     │  probe_vls(SVE), probe_vls(SME)           │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │ 初始化资源       │  epoll, pipe, 信号处理, 内存              │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │ 启动所有子进程   │  fork + execl, 阻塞在 startup_pipe        │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │ 关闭startup_pipe│  释放所有子进程同时开始                   │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────────────────────────────────────┐          │
│  │                  主循环                            │          │
│  │  ┌─────────────┐                                 │          │
│  │  │ epoll_wait  │  监控子进程输出                   │          │
│  │  └──────┬──────┘                                 │          │
│  │         │                                         │          │
│  │         ├─► 有输出: 处理输出                       │          │
│  │         │                                         │          │
│  │         ├─► 超时 + 未全部启动: 继续等待            │          │
│  │         │                                         │          │
│  │         ├─► 超时 + 全部启动: 发送 SIGUSR1          │          │
│  │         │                                         │          │
│  │         └─► 超时 = 0: 退出循环                     │          │
│  └─────────────────────────────────────────────────┘          │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │ 停止所有子进程   │  kill(SIGTERM)                           │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │ 清理所有子进程   │  waitpid, 检查退出状态, 输出              │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │ 报告测试结果     │  ksft_finished()                         │
│  └─────────────────┘                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 12.2 子进程启动流程

```
┌─────────────────────────────────────────────────────────────────┐
│                   child_start() 函数                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐                                           │
│  │ pipe(stdout_fd) │  创建捕获子进程输出的管道                  │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                           │
│  │ fork()          │                                           │
│  └────────┬────────┘                                           │
│           │                                                     │
│      ┌────┴────┐                                               │
│      │         │                                               │
│      ▼         ▼                                               │
│  ┌───────┐ ┌──────────┐                                      │
│  │ 父进程 │ │ 子进程   │                                      │
│  └───┬───┘ └────┬─────┘                                      │
│      │         │                                               │
│      │         ▼                                               │
│      │   ┌─────────────┐                                      │
│      │   │ dup2 stdout │  重定向 stdout 到管道写端             │
│      │   └─────┬───────┘                                      │
│      │         │                                               │
│      │         ▼                                               │
│      │   ┌─────────────┐                                      │
│      │   │ dup2 FD 3   │  复制 startup pipe 读端               │
│      │   └─────┬───────┘                                      │
│      │         │                                               │
│      │         ▼                                               │
│      │   ┌─────────────┐                                      │
│      │   │ close(4-8191)│  关闭所有其他文件描述符              │
│      │   └─────┬───────┘                                      │
│      │         │                                               │
│      │         ▼                                               │
│      │   ┌─────────────┐                                      │
│      │   │ read(FD 3)   │  阻塞等待 startup_pipe 关闭         │
│      │   └─────┬───────┘                                      │
│      │         │                                               │
│      │         ▼                                               │
│      │   ┌─────────────┐                                      │
│      │   │ execl(test)  │  执行测试程序                        │
│      │   └─────────────┘                                      │
│      │         │                                               │
│      ▼         │                                               │
│   ┌─────────────┤                                             │
│   │ close 写端  │                                             │
│   │ 添加 epoll  │                                             │
│   │ 初始化状态  │                                             │
│   └─────────────┘                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 12.3 主循环状态机

```
┌─────────────────────────────────────────────────────────────────┐
│                      主循环状态机                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌────────────────┐                                           │
│   │   初始状态      │  poll_interval = 5000ms                  │
│   │                │  等待子进程输出                            │
│   └───────┬────────┘                                           │
│           │                                                     │
│           ├── epoll_wait 返回 > 0: 处理输出                     │
│           │                                                     │
│           ├── epoll_wait 超时:                                  │
│           │     │                                               │
│           │     ├── 所有子进程启动?                             │
│           │     │     │                                         │
│           │     │     ├── 否: 继续等待                          │
│           │     │     │                                         │
│           │     │     └─── 是: 切换到运行状态                   │
│           │     │                                              │
│           ▼     ▼                                              │
│   ┌────────────────┐                                           │
│   │   运行状态      │  poll_interval = 25ms                    │
│   │                │  timeout--                                │
│   └───────┬────────┘                                           │
│           │                                                     │
│           ├── epoll_wait 返回 > 0: 处理输出 (不减少 timeout)    │
│           │                                                     │
│           ├── epoll_wait 超时:                                  │
│           │     │                                               │
│           │     ├── 发送 SIGUSR1 给所有子进程                   │
│           │     │                                               │
│           │     ├── 每 40 次打印进度                            │
│           │     │                                               │
│           │     └─── timeout == 0?                              │
│           │           │                                         │
│           │           ├── 是: 退出循环                          │
│           │           │                                         │
│           │           └─── 否: 继续循环                         │
│           │                                                     │
│           └── terminate == true?                               │
│                 │                                               │
│                 └── 是: 退出循环                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 13. 关键设计模式

### 13.1 启动屏障模式 (Startup Barrier)

**问题**：多个子进程需要同时开始测试，避免先启动的进程占优势

**解决方案**：使用管道作为同步屏障

```
实现方式:
1. 父进程创建 pipe
2. 每个子进程 fork 后:
   - 复制 pipe[0] 到 FD 3
   - 关闭其他所有 FD
   - read(FD 3) 阻塞
3. 所有子进程 fork 完成后:
   - 父进程关闭 pipe[0] 和 pipe[1]
   - 所有子进程的 read 返回 0 (EOF)
   - 同时执行 execl
```

### 13.2 超时适应模式 (Adaptive Timeout)

**问题**：不同平台子进程启动速度差异巨大

**解决方案**：超时只在所有子进程启动后开始计数

```
实现方式:
1. 初始 poll_interval = 5000ms (长超时)
2. 超时时检查 output_seen 标志
3. 所有子进程都输出后才:
   - 设置 all_children_started = true
   - poll_interval = 25ms (进入测试阶段)
   - 开始减少 timeout 计数
```

### 13.3 事件驱动模式 (Event-Driven)

**问题**：需要同时监控大量子进程的输出

**解决方案**：使用 epoll 多路复用

```
优势:
1. 单线程可处理数百个子进程
2. O(1) 时间复杂度
3. 事件触发，不浪费 CPU

监控事件:
- EPOLLIN: 子进程有输出
- EPOLLHUP: 子进程退出
```

### 13.4 优雅退出模式 (Graceful Shutdown)

**问题**：收到 SIGINT/SIGTERM 时需要正确清理

**解决方案**：多阶段退出机制

```
退出流程:
1. 信号处理器设置 terminate = true
2. 立即发送 SIGTERM 给所有子进程
3. 主循环检测到 terminate 后退出
4. 调用 drain_output(false) 处理剩余输出
5. 调用 child_cleanup() 等待所有子进程
6. 调用 drain_output(true) 刷新缓冲区
7. 调用 ksft_finished() 报告结果
```

### 13.5 输出缓冲模式 (Output Buffering)

**问题**：read() 可能读取不完整的行

**解决方案**：维护 child->output 缓冲区

```
处理逻辑:
1. read() 返回数据可能跨行
2. 按 \n 分割，完整行立即打印
3. 未完成部分保存在 child->output
4. 下次 read() 时拼接
5. EPOLLHUP 时强制刷新并标记 <EOF>
```

---

## 总结

`fp-stress.c` 是一个设计精良的并发测试工具，主要特点：

1. **全面的硬件覆盖**：自动探测和测试所有支持的向量长度
2. **高效的并发模型**：epoll 事件驱动，单线程管理数百子进程
3. **精确的同步控制**：启动屏障确保测试公平性
4. **健壮的错误处理**：完善的信号处理和资源清理
5. **灵活的超时机制**：适应不同平台性能差异

该工具对验证 ARM64 Linux 内核在 FP/SVE/SME 状态管理方面的正确性具有重要意义。
