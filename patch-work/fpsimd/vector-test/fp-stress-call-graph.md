# fp-stress.c 函数调用关系图

## 目录

1. [全局调用关系图](#1-全局调用关系图)
2. [主函数调用流程](#2-主函数调用流程)
3. [子进程管理调用图](#3-子进程管理调用图)
4. [信号处理调用图](#4-信号处理调用图)
5. [I/O 处理调用图](#5-io-处理调用图)
6. [测试启动调用图](#6-测试启动调用图)
7. [函数依赖矩阵](#7-函数依赖矩阵)

---

## 1. 全局调用关系图

```mermaid
graph TB
    %% 主函数
    MAIN[main<br/>内核测试工具入口]

    %% 系统信息获取
    NUM_PROC[num_processors<br/>获取CPU数量]

    %% 硬件探测
    PROBE_VLS[probe_vls<br/>探测向量长度]

    %% 资源初始化
    INIT[初始化阶段<br/>epoll/pipe/信号]

    %% 测试启动函数组
    START_FPSIMD[start_fpsimd<br/>启动FPSIMD测试]
    START_KERNEL[start_kernel<br/>启动KERNEL测试]
    START_SVE[start_sve<br/>启动SVE测试]
    START_SSVE[start_ssve<br/>启动SSVE测试]
    START_ZA[start_za<br/>启动ZA测试]
    START_ZT[start_zt<br/>启动ZT测试]

    %% 子进程管理
    CHILD_START[child_start<br/>启动子进程]
    CHILD_OUTPUT[child_output<br/>处理输出]
    CHILD_TICKLE[child_tickle<br/>发送SIGUSR1]
    CHILD_STOP[child_stop<br/>停止子进程]
    CHILD_CLEAN[child_cleanup<br/>清理子进程]

    %% I/O 处理
    CHILD_READ[child_output_read<br/>读取输出]
    DRAIN[drain_output<br/>处理待处理输出]

    %% 信号处理
    HANDLE_CHILD[handle_child_signal<br/>SIGCHLD处理]
    HANDLE_EXIT[handle_exit_signal<br/>SIGINT/SIGTERM处理]

    %% 主循环
    MAIN_LOOP[主循环<br/>epoll_wait]

    %% 清理阶段
    CLEANUP[清理阶段<br/>停止并清理所有子进程]

    %% kselftest 框架
    KSFT[kselftest 框架函数<br/>ksft_*]

    %% 系统调用
    SYSCALL[系统调用<br/>fork/prctl/epoll/等]

    %% 调用关系
    MAIN --> NUM_PROC
    MAIN --> PROBE_VLS
    MAIN --> INIT
    MAIN --> START_FPSIMD
    MAIN --> START_KERNEL
    MAIN --> START_SVE
    MAIN --> START_SSVE
    MAIN --> START_ZA
    MAIN --> START_ZT
    MAIN --> MAIN_LOOP
    MAIN --> CLEANUP
    MAIN --> KSFT

    START_FPSIMD --> CHILD_START
    START_KERNEL --> CHILD_START
    START_SVE --> CHILD_START
    START_SSVE --> CHILD_START
    START_ZA --> CHILD_START
    START_ZT --> CHILD_START

    MAIN_LOOP --> CHILD_OUTPUT
    MAIN_LOOP --> CHILD_TICKLE
    MAIN_LOOP --> DRAIN

    CHILD_OUTPUT --> CHILD_READ
    DRAIN --> CHILD_OUTPUT

    CLEANUP --> CHILD_STOP
    CLEANUP --> CHILD_CLEAN
    CLEANUP --> DRAIN

    CHILD_START --> SYSCALL
    CHILD_READ --> SYSCALL
    CHILD_TICKLE --> SYSCALL
    CHILD_STOP --> SYSCALL
    CHILD_CLEAN --> SYSCALL

    INIT --> HANDLE_CHILD
    INIT --> HANDLE_EXIT

    HANDLE_CHILD --> CHILD_CLEAN
    HANDLE_EXIT --> CHILD_STOP

    STYLE MAIN fill:#e1f5ff
    STYLE MAIN_LOOP fill:#fff4e1
    STYLE CHILD_START fill:#e8f5e9
    STYLE CHILD_OUTPUT fill:#e8f5e9
    STYLE INIT fill:#f3e5f5
    STYLE CLEANUP fill:#fce4ec
```

---

## 2. 主函数调用流程

```mermaid
graph TB
    MAIN[main 函数]

    %% 阶段划分
    PHASE1[阶段1: 参数解析]
    PHASE2[阶段2: 硬件探测]
    PHASE3[阶段3: 资源准备]
    PHASE4[阶段4: 启动子进程]
    PHASE5[阶段5: 主循环]
    PHASE6[阶段6: 清理退出]

    %% 详细流程
    P1_1[getopt_long<br/>解析 -t 参数]
    P1_2[设置 timeout 变量]

    P2_1[num_processors<br/>获取CPU数量]
    P2_2[getauxval AT_HWCAP<br/>检测SVE]
    P2_3[getauxval AT_HWCAP2<br/>检测SME/SME2]
    P2_4[probe_vls PR_SVE_SET_VL<br/>探测SVE VL]
    P2_5[probe_vls PR_SME_SET_VL<br/>探测SME VL]
    P2_6[计算 tests 总数]

    P3_1[ksft_print_header<br/>打印TAP头]
    P3_2[ksft_set_plan<br/>设置测试计划]
    P3_3[epoll_create1<br/>创建epoll实例]
    P3_4[pipe startup_pipe<br/>创建同步管道]
    P3_5[sigaction SIGINT<br/>设置中断处理]
    P3_6[sigaction SIGTERM<br/>设置终止处理]
    P3_7[sigaction SIGCHLD<br/>设置子进程处理]
    P3_8[calloc children<br/>分配子进程数据]
    P3_9[calloc evs<br/>分配事件数组]

    P4_1[循环每个CPU]
    P4_2[start_fpsimd<br/>启动FPSIMD测试]
    P4_3[start_kernel<br/>启动KERNEL测试]
    P4_4[循环每个SVE VL<br/>start_sve]
    P4_5[循环每个SME VL<br/>start_ssve + start_za]
    P4_6[如果有SME2<br/>start_zt]
    P4_7[关闭startup_pipe<br/>释放所有子进程]

    P5_1[epoll_wait<br/>等待事件]
    P5_2{有事件?}
    P5_3[child_output<br/>处理输出]
    P5_4{子进程全启动?}
    P5_5[等待更多子进程]
    P5_6[child_tickle<br/>发送SIGUSR1]
    P5_7{timeout==0?}
    P5_8[继续循环]
    P5_9[退出循环]

    P6_1[设置 terminate=true]
    P6_2[循环发送SIGTERM<br/>child_stop]
    P6_3[drain_output false<br/>处理剩余输出]
    P6_4[循环清理子进程<br/>child_cleanup]
    P6_5[drain_output true<br/>刷新缓冲区]
    P6_6[ksft_finished<br/>报告结果]

    %% 连接关系
    MAIN --> PHASE1
    PHASE1 --> P1_1 --> P1_2

    MAIN --> PHASE2
    PHASE2 --> P2_1 --> P2_2 --> P2_3 --> P2_4 --> P2_5 --> P2_6

    MAIN --> PHASE3
    PHASE3 --> P3_1 --> P3_2 --> P3_3 --> P3_4 --> P3_5 --> P3_6 --> P3_7 --> P3_8 --> P3_9

    MAIN --> PHASE4
    PHASE4 --> P4_1 --> P4_2 --> P4_3 --> P4_4 --> P4_5 --> P4_6 --> P4_7

    MAIN --> PHASE5
    PHASE5 --> P5_1 --> P5_2
    P5_2 -->|是| P5_3 --> P5_1
    P5_2 -->|否| P5_4
    P5_4 -->|否| P5_5 --> P5_1
    P5_4 -->|是| P5_6 --> P5_7
    P5_7 -->|是| P5_9
    P5_7 -->|否| P5_8 --> P5_1

    MAIN --> PHASE6
    PHASE6 --> P6_1 --> P6_2 --> P6_3 --> P6_4 --> P6_5 --> P6_6

    STYLE MAIN fill:#e1f5ff
    STYLE PHASE1 fill:#e8f5e9
    STYLE PHASE2 fill:#c8e6c9
    STYLE PHASE3 fill:#a5d6a7
    STYLE PHASE4 fill:#81c784
    STYLE PHASE5 fill:#fff9c4
    STYLE PHASE6 fill:#ffccbc
```

---

## 3. 子进程管理调用图

```mermaid
graph TB
    %% 子进程管理函数
    CHILD_START[child_start<br/>启动子进程]
    CHILD_OUTPUT[child_output<br/>处理输出]
    CHILD_READ[child_output_read<br/>读取输出]
    CHILD_TICKLE[child_tickle<br/>发送信号]
    CHILD_STOP[child_stop<br/>停止子进程]
    CHILD_CLEAN[child_cleanup<br/>清理子进程]

    %% 系统调用
    PIPE[pipe<br/>创建管道]
    FORK[fork<br/>创建进程]
    DUP2[dup2<br/>重定向FD]
    CLOSE[close<br/>关闭FD]
    READ[read<br/>读取数据]
    EXECL[execl<br/>执行程序]
    EPOLL_CTL[epoll_ctl<br/>添加监控]
    KILL[kill<br/>发送信号]
    WAITPID[waitpid<br/>等待退出]

    %% child_start 详细流程
    CHILD_START --> PIPE
    CHILD_START --> FORK
    FORK -->|子进程| DUP2
    DUP2 --> CLOSE
    CLOSE --> READ
    READ --> EXECL
    FORK -->|父进程| EPOLL_CTL

    %% child_output 详细流程
    CHILD_OUTPUT -->|EPOLLIN| CHILD_READ
    CHILD_OUTPUT -->|EPOLLHUP| CLOSE

    %% child_read 详细流程
    CHILD_READ --> READ
    CHILD_READ -->|EINTR| CHILD_READ
    CHILD_READ -->|数据| ksft_print_msg

    %% child_tickle 详细流程
    CHILD_TICKLE -->|检查output_seen| CHILD_TICKLE
    CHILD_TICKLE -->|检查exited| KILL

    %% child_stop 详细流程
    CHILD_STOP -->|检查exited| KILL

    %% child_cleanup 详细流程
    CHILD_CLEAN -->|检查exited| WAITPID
    WAITPID -->|EINTR| WAITPID
    WAITPID -->|WIFEXITED| CHILD_CLEAN
    CHILD_CLEAN -->|检查output_seen| CHILD_CLEAN
    CHILD_CLEAN -->|检查exit_status| CHILD_CLEAN
    CHILD_CLEAN --> ksft_test_result

    STYLE CHILD_START fill:#e8f5e9
    STYLE CHILD_OUTPUT fill:#e8f5e9
    STYLE CHILD_READ fill:#e8f5e9
    STYLE CHILD_TICKLE fill:#e8f5e9
    STYLE CHILD_STOP fill:#e8f5e9
    STYLE CHILD_CLEAN fill:#e8f5e9
    STYLE FORK fill:#ffecb3
```

---

## 4. 信号处理调用图

```mermaid
graph LR
    %% 信号源
    SIGINT[SIGINT<br/>Ctrl+C]
    SIGTERM[SIGTERM<br/>kill命令]
    SIGCHLD[SIGCHLD<br/>子进程退出]
    SIGUSR1[SIGUSR1<br/>测试信号]

    %% 信号处理函数
    HANDLE_EXIT[handle_exit_signal<br/>处理退出信号]
    HANDLE_CHILD[handle_child_signal<br/>处理子进程信号]

    %% 处理流程
    HANDLE_EXIT -->|检查terminate| HANDLE_EXIT
    HANDLE_EXIT -->|设置terminate=true| CHILD_STOP
    HANDLE_EXIT --> ksft_print_msg

    HANDLE_CHILD -->|查找子进程| HANDLE_CHILD
    HANDLE_CHILD -->|设置exited=true| HANDLE_CHILD
    HANDLE_CHILD -->|保存exit_status| HANDLE_CHILD
    HANDLE_CHILD -->|未找到| ksft_print_msg

    %% 测试进程中的信号处理
    TEST_PROCESS[测试子进程]
    TEST_PROCESS -->|捕获SIGUSR1| TEST_HANDLER[信号处理函数<br/>验证FP状态]

    %% 主循环发送信号
    MAIN_LOOP[主循环]
    MAIN_LOOP --> CHILD_TICKLE
    CHILD_TICKLE --> KILL
    KILL -->|SIGUSR1| TEST_PROCESS

    SIGINT --> HANDLE_EXIT
    SIGTERM --> HANDLE_EXIT
    SIGCHLD --> HANDLE_CHILD
    SIGUSR1 --> TEST_HANDLER

    STYLE HANDLE_EXIT fill:#f3e5f5
    STYLE HANDLE_CHILD fill:#f3e5f5
    STYLE TEST_HANDLER fill:#fff9c4
    STYLE CHILD_STOP fill:#e8f5e9
```

---

## 5. I/O 处理调用图

```mermaid
graph TB
    %% I/O 处理函数
    DRAIN[drain_output<br/>处理待处理输出]
    CHILD_OUTPUT[child_output<br/>处理epoll事件]
    CHILD_READ[child_output_read<br/>读取数据]

    %% epoll 相关
    EPOLL_WAIT[epoll_wait<br/>等待事件]
    EPOLL_CTL[epoll_ctl<br/>添加/修改监控]

    %% 输出处理
    OUTPUT_BUF[output缓冲区<br/>child->output]
    PRINT_MSG[ksft_print_msg<br/>打印消息]
    FLUSH[刷新缓冲区<br/>标记<EOF>]

    %% 调用关系
    EPOLL_WAIT -->|返回>0| CHILD_OUTPUT
    EPOLL_WAIT -->|超时| MAIN_LOOP[继续主循环]

    CHILD_OUTPUT -->|EPOLLIN| CHILD_READ
    CHILD_OUTPUT -->|EPOLLHUP| CLOSE_FD[关闭stdout fd]
    CHILD_OUTPUT -->|flush参数| FLUSH

    CHILD_READ -->|EINTR| CHILD_READ
    CHILD_READ -->|成功| OUTPUT_BUF
    CHILD_READ -->|读取到\n| PRINT_MSG
    CHILD_READ -->|未完成行| OUTPUT_BUF

    OUTPUT_BUF -->|拼接| CHILD_READ
    OUTPUT_BUF -->|flush时| FLUSH

    DRAIN --> EPOLL_WAIT
    DRAIN --> CHILD_OUTPUT

    %% 启动时添加监控
    CHILD_START[child_start] --> EPOLL_CTL

    STYLE DRAIN fill:#e1f5ff
    STYLE CHILD_OUTPUT fill:#e1f5ff
    STYLE CHILD_READ fill:#e1f5ff
    STYLE OUTPUT_BUF fill:#fff9c4
```

---

## 6. 测试启动调用图

```mermaid
graph TB
    %% 测试启动函数
    START_FPSIMD[start_fpsimd<br/>FPSIMD测试]
    START_KERNEL[start_kernel<br/>KERNEL测试]
    START_SVE[start_sve<br/>SVE测试]
    START_SSVE[start_ssve<br/>SSVE测试]
    START_ZA[start_za<br/>ZA测试]
    START_ZT[start_zt<br/>ZT测试]

    %% 共同调用
    CHILD_START[child_start<br/>启动子进程]
    ASPRINTF[asprintf<br/>生成测试名称]
    PRCTL[prctl<br/>设置向量长度]
    PRINT_MSG[ksft_print_msg<br/>打印启动消息]

    %% prctl 参数
    PR_SVE[PR_SVE_SET_VL<br/>设置SVE VL]
    PR_SME[PR_SME_SET_VL<br/>设置SME VL]
    VL_INHERIT[VL_INHERIT标志<br/>子进程继承]

    %% 调用关系
    START_FPSIMD --> ASPRINTF
    START_FPSIMD --> CHILD_START
    START_FPSIMD --> PRINT_MSG

    START_KERNEL --> ASPRINTF
    START_KERNEL --> CHILD_START
    START_KERNEL --> PRINT_MSG

    START_SVE --> PR_SVE
    PR_SVE --> VL_INHERIT
    PR_SVE --> PRCTL
    START_SVE --> ASPRINTF
    START_SVE --> CHILD_START
    START_SVE --> PRINT_MSG

    START_SSVE --> ASPRINTF
    START_SSVE --> PR_SME
    PR_SME --> VL_INHERIT
    PR_SME --> PRCTL
    START_SSVE --> CHILD_START
    START_SSVE --> PRINT_MSG

    START_ZA --> PR_SME
    START_ZA --> ASPRINTF
    START_ZA --> CHILD_START
    START_ZA --> PRINT_MSG

    START_ZT --> ASPRINTF
    START_ZT --> CHILD_START
    START_ZT --> PRINT_MSG

    %% 测试程序
    TEST1["./fpsimd-test"]
    TEST2["./kernel-test"]
    TEST3["./sve-test"]
    TEST4["./ssve-test"]
    TEST5["./za-test"]
    TEST6["./zt-test"]

    CHILD_START -->|FPSIMD| TEST1
    CHILD_START -->|KERNEL| TEST2
    CHILD_START -->|SVE| TEST3
    CHILD_START -->|SSVE| TEST4
    CHILD_START -->|ZA| TEST5
    CHILD_START -->|ZT| TEST6

    STYLE START_FPSIMD fill:#e8f5e9
    STYLE START_KERNEL fill:#e8f5e9
    STYLE START_SVE fill:#c8e6c9
    STYLE START_SSVE fill:#a5d6a7
    STYLE START_ZA fill:#81c784
    STYLE START_ZT fill:#66bb6a
    STYLE CHILD_START fill:#e1f5ff
```

---

## 7. 函数依赖矩阵

### 7.1 函数分类

| 类别 | 函数 |
|------|------|
| **入口函数** | `main()` |
| **系统信息** | `num_processors()` |
| **硬件探测** | `probe_vls()` |
| **测试启动** | `start_fpsimd()`, `start_kernel()`, `start_sve()`, `start_ssve()`, `start_za()`, `start_zt()` |
| **子进程管理** | `child_start()`, `child_stop()`, `child_cleanup()`, `child_tickle()` |
| **I/O 处理** | `child_output()`, `child_output_read()`, `drain_output()` |
| **信号处理** | `handle_child_signal()`, `handle_exit_signal()` |

### 7.2 调用关系矩阵

| 被调用者 → | main | num_processors | probe_vls | child_start | child_output | child_read | child_tickle | child_stop | child_cleanup | drain_output | start_* | handle_* |
|------------|------|----------------|-----------|-------------|--------------|------------|--------------|------------|---------------|--------------|----------|----------|
| **调用者 ↓** | | | | | | | | | | | | |
| main | ✓ | ✓ | ✓ | | | | | | ✓ | ✓ | ✓ | ✓ |
| child_start | | | | | | | | | | | | |
| child_output | | | | | | ✓ | | | | | | |
| child_read | | | | | | | | | | ✓ | | |
| drain_output | | | | | | ✓ | | | | | | |
| start_* | | | ✓ | ✓ | | | | | | | | |
| handle_child | | | | | | | | | ✓ | | | |
| handle_exit | | | | | | | | ✓ | | | | |

### 7.3 系统调用依赖

| 函数 | 系统调用 |
|------|----------|
| `num_processors()` | `sysconf(_SC_NPROCESSORS_CONF)` |
| `probe_vls()` | `prctl(PR_SVE_SET_VL)`, `prctl(PR_SME_SET_VL)` |
| `child_start()` | `pipe()`, `fork()`, `dup2()`, `close()`, `read()`, `execl()`, `epoll_ctl()` |
| `child_output_read()` | `read()` |
| `child_tickle()` | `kill(SIGUSR1)` |
| `child_stop()` | `kill(SIGTERM)` |
| `child_cleanup()` | `waitpid()` |
| `drain_output()` | `epoll_wait()` |
| `main()` | `epoll_create1()`, `pipe()`, `sigaction()`, `getauxval()` |

### 7.4 kselftest 框架依赖

| 函数 | kselftest 调用 |
|------|----------------|
| `main()` | `ksft_print_header()`, `ksft_set_plan()`, `ksft_print_msg()`, `ksft_finished()` |
| `start_*()` | `ksft_print_msg()` |
| `child_start()` | `ksft_exit_fail_msg()` |
| `child_output_read()` | `ksft_print_msg()`, `ksft_exit_fail_msg()` |
| `child_cleanup()` | `ksft_print_msg()`, `ksft_test_result()` |
| `handle_*()` | `ksft_print_msg()` |

---

## 8. 调用时序图

### 8.1 程序启动时序

```mermaid
sequenceDiagram
    participant Main as main()
    participant Init as 初始化
    participant Probe as 硬件探测
    participant Start as 启动子进程
    participant Loop as 主循环
    participant Child as 子进程
    participant Clean as 清理

    Main->>Init: 解析参数
    Main->>Probe: 检测 HWCAP
    Probe->>Probe: probe_vls(SVE)
    Probe->>Probe: probe_vls(SME)
    Probe-->>Main: 返回支持的VL列表

    Main->>Init: 创建 epoll
    Main->>Init: 创建 startup_pipe
    Main->>Init: 设置信号处理

    loop 每个CPU
        Main->>Start: start_fpsimd()
        Start->>Child: fork() + 阻塞在 pipe
        Main->>Start: start_kernel()
        Start->>Child: fork() + 阻塞在 pipe

        loop 每个SVE VL
            Main->>Start: start_sve()
            Start->>Start: prctl(SVE VL)
            Start->>Child: fork() + 阻塞在 pipe
        end

        loop 每个SME VL
            Main->>Start: start_ssve()
            Start->>Start: prctl(SME VL)
            Start->>Child: fork() + 阻塞在 pipe

            Main->>Start: start_za()
            Start->>Child: fork() + 阻塞在 pipe
        end

        if 有SME2
            Main->>Start: start_zt()
            Start->>Child: fork() + 阻塞在 pipe
        end
    end

    Main->>Child: 关闭 startup_pipe
    Child->>Child: read() 返回
    Child->>Child: execl(test)

    Main->>Loop: epoll_wait()
    Loop->>Child: 监控 stdout

    loop 主循环
        alt 有输出事件
            Child-->>Loop: stdout 数据
            Loop->>Loop: child_output()
            Loop-->>Main: 继续等待
        else 超时事件
            alt 子进程未全启动
                Loop->>Loop: 等待更多输出
            else 子进程已启动
                Loop->>Child: SIGUSR1
                Loop->>Loop: timeout--
                alt timeout == 0
                    Loop-->>Main: 退出循环
                else timeout > 0
                    Loop-->>Main: 继续循环
                end
            end
        end
    end

    Main->>Clean: child_stop() 所有子进程
    Clean->>Child: SIGTERM
    Main->>Clean: drain_output(false)
    Main->>Clean: child_cleanup() 所有子进程
    Clean->>Child: waitpid()
    Child-->>Clean: 退出状态
    Main->>Clean: drain_output(true)
    Main->>Main: ksft_finished()
```

### 8.2 信号处理时序

```mermaid
sequenceDiagram
    participant User as 用户/Ctrl+C
    participant Main as 主进程
    participant Handler as handle_exit_signal
    participant Child as 子进程
    participant Loop as 主循环
    participant Clean as 清理

    User->>Main: SIGINT
    Main->>Handler: 调用信号处理函数
    Handler->>Handler: 检查 terminate 标志
    Handler->>Handler: 设置 terminate = true
    Handler->>Child: kill(SIGTERM) 所有子进程

    Note over Loop: 下一次循环检查
    Loop->>Loop: 检查 terminate
    Loop-->>Main: 退出主循环

    Main->>Clean: 进入清理阶段
    Clean->>Child: 再次发送 SIGTERM (保险)
    Clean->>Clean: drain_output(false)
    Clean->>Child: waitpid()
    Child-->>Clean: 退出状态
    Clean->>Clean: child_cleanup()
    Clean->>Clean: drain_output(true)
    Clean-->>Main: 清理完成

    Main->>Main: ksft_finished()
    Main-->>User: 程序退出
```

### 8.3 子进程输出处理时序

```mermaid
sequenceDiagram
    participant Child as 子进程
    participant Pipe as 管道
    participant Epoll as epoll
    participant Loop as 主循环
    participant Output as child_output
    participant Read as child_read
    participant Buffer as output缓冲区

    Child->>Pipe: write("Line 1\nLine 2\nPart ")
    Pipe->>Epoll: EPOLLIN 事件
    Epoll->>Loop: epoll_wait() 返回
    Loop->>Output: child_output(EPOLLIN)

    Output->>Read: child_output_read()
    Read->>Pipe: read(1024)
    Pipe-->>Read: "Line 1\nLine 2\nPart "

    Read->>Read: 处理 "Line 1\n"
    Read->>Loop: ksft_print_msg("Line 1")

    Read->>Read: 处理 "Line 2\n"
    Read->>Loop: ksft_print_msg("Line 2")

    Read->>Read: 处理 "Part " (无\n)
    Read->>Buffer: 保存到 child->output

    Read-->>Output: 返回
    Output-->>Loop: 处理完成

    Note over Child,Buffer: 子进程继续运行

    Child->>Pipe: write("3\n")
    Pipe->>Epoll: EPOLLIN 事件
    Epoll->>Loop: epoll_wait() 返回
    Loop->>Output: child_output(EPOLLIN)

    Output->>Read: child_output_read()
    Read->>Buffer: 恢复 "Part "
    Read->>Pipe: read()
    Pipe-->>Read: "3\n"

    Read->>Read: 拼接 "Part " + "3\n"
    Read->>Read: 处理 "Part 3\n"
    Read->>Loop: ksft_print_msg("Part 3")
    Read->>Buffer: 清空 child->output

    Read-->>Output: 返回
    Output-->>Loop: 处理完成

    Note over Child: 子进程退出
    Child->>Pipe: close() (退出)
    Pipe->>Epoll: EPOLLHUP 事件
    Epoll->>Loop: epoll_wait() 返回
    Loop->>Output: child_output(EPOLLHUP|EPOLLIN)

    Output->>Output: close(stdout fd)
    Output->>Buffer: 检查 child->output
    alt 有剩余数据
        Output->>Loop: ksft_print_msg("...<EOF>")
        Output->>Buffer: free(output)
    end
    Output-->>Loop: 处理完成
```

---

## 9. 数据流图

```mermaid
graph LR
    %% 输入数据
    ARGV[命令行参数<br/>-t timeout]
    HWCAP[硬件能力<br/>AT_HWCAP]
    HWCAP2[硬件能力<br/>AT_HWCAP2]
    SYSCONF[系统配置<br/>CPU数量]

    %% 处理过程
    PARSE[参数解析<br/>timeout]
    PROBE[硬件探测<br/>probe_vls]
    CALC[计算测试数量<br/>tests]

    %% 测试数据
    SVE_VLS[SVE VL列表<br/>sve_vls[]]
    SME_VLS[SME VL列表<br/>sme_vls[]]
    CPU_COUNT[CPU数量<br/>cpus]

    %% 子进程数据
    CHILDREN[子进程数组<br/>children[]]
    CHILD_DATA[child_data结构<br/>每个子进程]

    %% 运行时数据
    EPOLL_EVENTS[epoll事件<br/>evs[]]
    OUTPUT_BUF[输出缓冲区<br/>child->output]
    EXIT_STATUS[退出状态<br/>child->exit_status]

    %% 输出数据
    TAP[TAP输出<br/>stdout]
    MSG[日志消息<br/>ksft_print_msg]
    RESULT[测试结果<br/>ok/not ok]

    %% 数据流
    ARGV --> PARSE
    HWCAP --> PROBE
    HWCAP2 --> PROBE
    SYSCONF --> CALC

    PARSE --> CALC
    PROBE --> SVE_VLS
    PROBE --> SME_VLS
    SYSCONF --> CPU_COUNT

    SVE_VLS --> CALC
    SME_VLS --> CALC
    CPU_COUNT --> CALC

    CALC --> CHILDREN

    CHILDREN --> CHILD_DATA
    CHILD_DATA --> EPOLL_EVENTS
    CHILD_DATA --> OUTPUT_BUF
    CHILD_DATA --> EXIT_STATUS

    EPOLL_EVENTS --> MSG
    OUTPUT_BUF --> MSG
    EXIT_STATUS --> RESULT
    MSG --> TAP
    RESULT --> TAP

    STYLE ARGV fill:#e8f5e9
    STYLE HWCAP fill:#fff9c4
    STYLE SVE_VLS fill:#c8e6c9
    STYLE SME_VLS fill:#a5d6a7
    STYLE CHILDREN fill:#e1f5ff
    STYLE TAP fill:#ffccbc
```

---

## 10. 总结

### 函数调用层次

```
Level 0: main()
    │
    ├─ Level 1: 系统信息与初始化
    │   ├─ num_processors()
    │   ├─ probe_vls()
    │   ├─ epoll_create1()
    │   ├─ pipe()
    │   └─ sigaction()
    │
    ├─ Level 1: 测试启动
    │   ├─ start_fpsimd()
    │   ├─ start_kernel()
    │   ├─ start_sve()
    │   ├─ start_ssve()
    │   ├─ start_za()
    │   └─ start_zt()
    │       │
    │       └─ Level 2: child_start()
    │
    ├─ Level 1: 主循环
    │   ├─ epoll_wait()
    │   │   │
    │   │   └─ Level 2: child_output()
    │   │       │
    │   │       └─ Level 3: child_output_read()
    │   │
    │   └─ child_tickle()
    │
    ├─ Level 1: 清理
    │   ├─ child_stop()
    │   ├─ drain_output()
    │   │   │
    │   │   └─ Level 2: child_output()
    │   │
    │   └─ child_cleanup()
    │       └─ waitpid()
    │
    └─ Level 1: 信号处理
        ├─ handle_child_signal()
        │   └─ (设置 child->exited)
        │
        └─ handle_exit_signal()
            └─ child_stop()
```

### 关键调用路径

1. **启动路径**: `main()` → `start_*()` → `child_start()` → `execl()`
2. **监控路径**: `main()` → `epoll_wait()` → `child_output()` → `child_output_read()`
3. **信号路径**: `main()` → `sigaction()` → `handle_*()` → `child_stop/cleanup()`
4. **清理路径**: `main()` → `child_stop()` → `child_cleanup()` → `waitpid()`
