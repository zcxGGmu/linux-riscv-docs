# -1 reference

* [riscv: vector: allow kernel-mode Vector with preemption](https://lore.kernel.org/all/20240115055929.4736-11-andy.chiu@sifive.com/)
* [PERCPU - fpsimd_last_state](https://elixir.bootlin.com/linux/v6.10-rc5/C/ident/DEFINE_PER_CPU)





# 0 todo

- [ ] `kernelmode-vector-preemption`: 内存性能优化 🔥
  - [ ] 优化
    - [ ] 关于抢占/调度，在独立的文档分析
    - [ ] 关于 linux 中 riscv-timer 的处理
  - [ ] 如果添加一个 `kernelmod-vector/selftest`，你该如何构造这种场景 "使用内核模式向量时被抢占"？
    * https://elixir.bootlin.com/linux/v6.10-rc5/source/tools/testing/selftests/arm64/fp
    * https://elixir.bootlin.com/linux/v6.10-rc5/source/tools/testing/selftests/x86
    * https://elixir.bootlin.com/linux/v6.10-rc5/source/tools/testing/selftests/riscv
- [ ] `arm64 => DEFINE_PER_CPU(struct cpu_fp_state, fpsimd_last_state);`





# 1 Anything else interesting about vector?

## 1.0 Documentation

本文档简要概述了 Linux 为支持 RISC-V 向量扩展在用户空间提供的接口。

### 1) prctl() Interface

新增了两个 `prctl` 调用，允许程序管理用户空间中向量使用的启用状态。此接口的使用指南是，为 init 系统提供一种方法，来修改其域内运行进程的向量可用性。不建议在库例程中调用这些接口，因为库不应覆盖父进程配置的策略。另外，用户必须注意，这些接口在非 Linux 或非 RISC-V 环境中不可移植，因此不建议在可移植代码中使用。

要获取 ELF 程序中向量的可用性，请读取辅助向量中的 `:c:macro: COMPAT_HWCAP_ISA_V` 位的 `:c:macro: ELF_HWCAP` 。

* `prctl(PR_RISCV_V_SET_CONTROL, unsigned long arg)`

    设置调用线程的向量启用状态，控制参数由两个 2 位启用状态和一个继承模式位组成。调用进程的其他线程不受影响。启用状态，是占用控制参数 2 位空间的三态值：

    * `:c:macro: PR_RISCV_V_VSTATE_CTRL_DEFAULT`: 在 execve() 上使用系统范围的默认启用状态。系统范围的默认设置可以通过 sysctl 接口控制（见下文 sysctl 部分）。

    * `:c:macro: PR_RISCV_V_VSTATE_CTRL_ON`: 允许线程运行向量。

    * `:c:macro: PR_RISCV_V_VSTATE_CTRL_OFF`: 禁止向量。在这种情况下执行向量指令将导致线程终止。

    控制 `arg` 参数是一个由 3 部分组成的 5 位值，通过 3 个掩码分别访问。

    * `PR_RISCV_V_VSTATE_CTRL_CUR_MASK`: bit[1:0] 表示当前线程的启用状态
    * `PR_RISCV_V_VSTATE_CTRL_NEXT_MASK` : bit[3:2] 在下一个 execve() 时生效
    * `PR_RISCV_V_VSTATE_CTRL_INHERIT` : bit[4] 定义 bit[3:2] 设置的继承模式

    ```shell
    * :c:macro:`PR_RISCV_V_VSTATE_CTRL_CUR_MASK`: bit[1:0]: 表示调用线程的向量启用状态。调用线程在启用向量后无法关闭向量。
    如果该掩码中的值为 PR_RISCV_V_VSTATE_CTRL_OFF 但当前启用状态不是关闭状态，prctl() 调用将以 EPERM 失败。在此处设置 PR_RISCV_V_VSTATE_CTRL_DEFAULT 无效，只会恢复原始启用状态。
    
    * :c:macro:`PR_RISCV_V_VSTATE_CTRL_NEXT_MASK`: bit[3:2]: 表示调用线程在下一个 execve() 系统调用中的向量启用设置。
    如果在此掩码中使用 PR_RISCV_V_VSTATE_CTRL_DEFAULT，则启用状态将在 execve() 发生时由系统范围的启用状态决定。
    
    * :c:macro:`PR_RISCV_V_VSTATE_CTRL_INHERIT`: bit[4]: 表示 PR_RISCV_V_VSTATE_CTRL_NEXT_MASK 设置的继承模式。
    如果设置了该位，则随后的 execve() 不会清除 PR_RISCV_V_VSTATE_CTRL_NEXT_MASK 和 PR_RISCV_V_VSTATE_CTRL_INHERIT 中的设置。此设置在系统范围的默认值发生变化时仍然存在。
    ```

    ---

    返回值:
       * 成功返回 0;
       * `EINVAL`: 不支持向量，当前或下一个掩码的启用状态无效;
       * `EPERM`: 如果向量已为调用线程启用，则在 `PR_RISCV_V_VSTATE_CTRL_CUR_MASK` 中关闭向量 ;

    成功时:
       * `PR_RISCV_V_VSTATE_CTRL_CUR_MASK` 的有效设置立即生效`PR_RISCV_V_VSTATE_CTRL_NEXT_MASK` 中指定的启用状态，将在下一个 `execve()` 调用时生效，或者如果设置了 `PR_RISCV_V_VSTATE_CTRL_INHERIT` 位，则在所有后续的 `execve()` 调用中生效。
       * 每次成功调用，都会覆盖调用线程的先前设置；

---

* `prctl(PR_RISCV_V_GET_CONTROL)`

    获取调用线程的相同向量启用状态。为下一个 `execve()` 调用和继承位设置的值，将被 OR 运算合并在一起。

    注意，ELF 程序可以通过读取辅助向量中的 `:c:macro: COMPAT_HWCAP_ISA_V` 位的 `:c:macro: ELF_HWCAP` 来获取自身的向量可用性。

    返回值:

    * 成功时返回非负值；
    * `EINVAL`: 不支持向量；

### 2) System runtime configuration (sysctl)

为了减轻信号栈扩展的 ABI 影响，提供了一种策略机制，供管理员、发行版维护人员和开发人员以 `sysctl` 节点的形式，控制用户空间进程的默认向量启用状态：

* `/proc/sys/abi/riscv_v_default_allow`

    向此文件写入 0 或 1 ，可以设置新启动的用户程序的默认系统启用状态。有效值为：

    * `0`: 默认情况下不允许执行向量代码
    * `1`: 默认情况下允许执行向量代码

    读取此文件，将返回当前系统默认启用状态。

    在每次 `execve()` 调用时，新进程的启用状态将设置为系统默认值，除非：

      * `PR_RISCV_V_VSTATE_CTRL_INHERIT` 已为调用进程设置，且 `PR_RISCV_V_VSTATE_CTRL_NEXT_MASK` 中的设置不是 `PR_RISCV_V_VSTATE_CTRL_DEFAULT`。或，

      * `PR_RISCV_V_VSTATE_CTRL_NEXT_MASK` 中的设置不是 `PR_RISCV_V_VSTATE_CTRL_DEFAULT`。

    修改系统默认启用状态，不会影响任何不进行 execve() 调用的现有进程或线程的启用状态。

### 3) Vector Register State Across System Calls

---------------------------------------------

如 V 扩展版本 1.0 [1] 所示，向量寄存器在系统调用时会被破坏。

1: https://github.com/riscv/riscv-v-spec/blob/master/calling-convention.adoc





## 1.1 overview

- [ ] `arm64/riscv` 对向量长度配置：

  * `arm64-sve` 给用户态暴露了 `PR_SVE_VL_*` 相关的 control-flag，支持用户去配置，当前进程所对应向量上下文的内存区域。

  * `riscv-vector` 在目前的内核实现中，用户态无法自由配置这个长度，如下：

    ```c
    int riscv_v_setup_vsize(void)
    {
    	unsigned long this_vsize;
    
    	/* There are 32 vector registers with vlenb length. */
    	riscv_v_enable();
    	this_vsize = csr_read(CSR_VLENB) * 32;
    	riscv_v_disable();
    
    	if (!riscv_v_vsize) {
    		riscv_v_vsize = this_vsize;
    		return 0;
    	}
    
    	if (riscv_v_vsize != this_vsize) {
    		WARN(1, "RISCV_ISA_V only supports one vlenb on SMP systems");
    		return -EOPNOTSUPP;
    	}
    
    	return 0;
    }
    
    /*
     * C entry point for a secondary processor.
     */
    smp_callin
    +-> riscv_v_setup_vsize
    ```

    针对 smp 系统的多hart，全部初始化完毕，`riscv_v_size` 将是所有hart中最大的 `VLEN`。预分配进程 vector 上下文时，使用的也是 `riscv_v_size`，如下：

    ```c
    void __init riscv_v_setup_ctx_cache(void)
    {
    	if (!has_vector())
    		return;
    
    	riscv_v_user_cachep = kmem_cache_create_usercopy("riscv_vector_ctx",
    							 riscv_v_vsize, 16, SLAB_PANIC,
    							 0, riscv_v_vsize, NULL);
    #ifdef CONFIG_RISCV_ISA_V_PREEMPTIVE
    	riscv_v_kernel_cachep = kmem_cache_create("riscv_vector_kctx",
    						  riscv_v_vsize, 16,
    						  SLAB_PANIC, NULL);
    #endif
    }
    ```

    

## 1.2  selftests/riscv/vector

https://elixir.bootlin.com/linux/v6.10-rc6/source/tools/testing/selftests/riscv/vector













# 2 kernel mode vector preemption

## 2.1 overview

> 这个补丁在 QEMU 上进行了测试，使用 V（向量扩展）并验证了引导和正常用户空间操作在阈值设置为 0 时都能正常工作。此外，我们通过启动多个内核线程来测试，这些线程在后台连续执行并验证向量操作。测试这些操作的模块预计将在稍后合并到上游。
>
> 添加了 `kernel_vstate` 以跟踪内核模式向量寄存器在陷阱引发的上下文切换时的状态。同时，提供了 `riscv_v_flags` 以让上下文保存/恢复例程跟踪上下文状态。上下文跟踪发生在核心开始其内核中的向量执行时。一个活动的（脏的）内核任务的 V 上下文将在陷阱引发的上下文切换时保存到内存中，或者在软中断（softirq）嵌套在其上并使用向量时保存。上下文恢复发生在执行返回到原始内核上下文并首次启用 `preempt_v` 时。
>
> 此外，提供了一个配置选项 `CONFIG_RISCV_ISA_V_PREEMPTIVE`，允许用户在构建时选择禁用可抢占的内核模式向量。具有内存限制的用户可能希望禁用此配置，因为可抢占的内核模式向量需要额外的空间来跟踪每个线程的内核模式 V 上下文。或者，如果所有内核模式向量代码都是时间敏感的且无法容忍上下文切换开销，用户也可能希望禁用它。

```c
/* kernelmode vector vstate allocate */
start_kernel
+-> fork_init
    +-> arch_task_cache_init
        +-> riscv_v_setup_ctx_cache
            +-> #ifdef CONFIG_RISCV_ISA_V_PREEMPTIVE
                riscv_v_kernel_cachep = kmem_cache_create("riscv_vector_kctx",
                                      riscv_v_vsize, 16,
                                      SLAB_PANIC, NULL);
                #endif

// arch/riscv/kernel/process.c
/*
 *  Ok, this is the main fork-routine.
 *
 * It copies the process, and if successful kick-starts
 * it and waits for it to finish using the VM if required.
 *
 * args->exit_signal is expected to be checked for sanity by the caller.
 */
SYSCALL_DEFINE0(fork)
kernel_thread
kernel_clone
copy_process
copy_thread
+-> if (has_vector()) //return riscv_has_extension_unlikely(RISCV_ISA_EXT_v);
    	riscv_v_thread_alloc(p);
		+-> #ifdef CONFIG_RISCV_ISA_V_PREEMPTIVE
            riscv_v_thread_zalloc(riscv_v_kernel_cachep, &tsk->thread.kernel_vstate);
            #endif

static int riscv_v_thread_zalloc(struct kmem_cache *cache,
				 struct __riscv_v_ext_state *ctx)
{
	void *datap;

	datap = kmem_cache_zalloc(cache, GFP_KERNEL);
	if (!datap)
		return -ENOMEM;

	ctx->datap = datap;
	memset(ctx, 0, offsetof(struct __riscv_v_ext_state, datap));
	return 0;
}
```

```c
/* usermode vector vstate allocate */
// arch/riscv/kernel/traps.c
do_trap_insn_illegal
riscv_v_first_use_handler
	/*
	 * Now we sure that this is a V instruction. And it executes in the
	 * context where VS has been off. So, try to allocate the user's V
	 * context and resume execution.
	 */
	if (riscv_v_thread_zalloc(riscv_v_user_cachep, &current->thread.vstate)) {
		force_sig(SIGBUS);
		return true;
	}
```

- [ ] `riscv_v_thread_alloc` 单从函数名来看，语义就很模糊，且内部仅调用 `riscv_v_thread_zalloc` 来分配内核模式向量的缓存，为什么这么定义？ 比较奇怪。

- [ ] `{kernelmode/usermode}_vector` 的分配原则并不统一，`usermode_vector` 遵循 “即用即分” 的原则，在用户真正使用vector操作时 (执行向量指令或访问向量寄存器) 才分配向量缓存。显然，`kernelmode_vector` 没有做到这一点，在fork流程中直接分配了向量缓存，如果系统开启了 `CONFIG_RISCV_ISA_V_PREEMPTIVE`，但大量进程并没有触发 "内核模式向量抢占“ 这一行为，这些内存开销则是无意义的。

  那应该在什么位置，分配 `kernelmode_vector` 最合适，在触发 "内核模式向量抢占“ 时，借助现有的框架应该可以感知到这一时机，大致逻辑如下:

  ```c
  riscv_v_context_nesting_start
  +-> riscv_v_ctx_depth_inc();
  +-> if (riscv_v_ctx_get_depth() == 1) {
      	riscv_v_thread_zalloc(riscv_v_kernel_cachep, &tsk->thread.kernel_vstate);
  	}
  	// `CONFIG_RISCV_ISA_V_PREEMPTIVE` 在外层添加，这里不需要
  ```





## 2.2 vector selftests

### 1) test setup

编写一个内核自测程序（selftest）以测试被抢占的内核向量上下文，需要以下几个步骤：

1. **编写内核模块**：创建一个内核模块，启动一个使用向量指令的内核线程。
2. **触发 softirq**：在合适的时机触发 softirq 来打断向量线程的执行。
3. **上下文保存与恢复**：确保在软中断上下文中正确保存和恢复向量寄存器状态。
4. **验证测试结果**：检查向量寄存器的值以确保它们在中断前后保持一致。

以下是一个简化的例子，展示了如何实现这些步骤：

#### 1. 创建内核模块

首先，编写一个内核模块，启动一个使用向量指令的内核线程：

```c
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/kthread.h>
#include <linux/interrupt.h>
#include <linux/delay.h>

static struct task_struct *vector_thread;

static int vector_thread_fn(void *data) {
    while (!kthread_should_stop()) {
        // 使用向量指令的代码（这是一个假设的例子）
        asm volatile (
            ".insn r 0x57, 0, x0, x0, x0" // 假设的向量指令
        );
        msleep(100); // 休眠一段时间
    }
    return 0;
}

static void my_softirq_handler(struct softirq_action *action) {
    pr_info("SoftIRQ handler executed\n");
    // 在这里你可以验证向量寄存器的上下文保存和恢复
}

static int __init mymodule_init(void) {
    vector_thread = kthread_run(vector_thread_fn, NULL, "vector_thread");
    if (IS_ERR(vector_thread)) {
        pr_err("Failed to create vector thread\n");
        return PTR_ERR(vector_thread);
    }

    // 注册 SoftIRQ
    open_softirq(0, my_softirq_handler);

    // 模拟触发 SoftIRQ
    raise_softirq(0);

    pr_info("Module loaded\n");
    return 0;
}

static void __exit mymodule_exit(void) {
    if (vector_thread) {
        kthread_stop(vector_thread);
    }
    pr_info("Module unloaded\n");
}

module_init(mymodule_init);
module_exit(mymodule_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Your Name");
MODULE_DESCRIPTION("Kernel selftest for preempted vector context");
```

#### 2. 编写用户空间自测程序

接下来，编写一个用户空间自测程序来加载和卸载内核模块，并检查内核日志中的输出以验证测试结果：

```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(void) {
    system("insmod mymodule.ko"); // 加载内核模块
    sleep(5); // 等待一段时间，让内核线程运行并触发 SoftIRQ
    system("rmmod mymodule.ko"); // 卸载内核模块

    // 读取内核日志以验证测试结果
    system("dmesg | tail -20");

    return 0;
}
```

#### 3. 验证和调试

1. **编译内核模块**：
   
   ```sh
   make -C /lib/modules/$(uname -r)/build M=$(pwd) modules
   ```
   
2. **运行用户空间自测程序**：
   ```sh
   gcc -o test_user test_user.c
   sudo ./test_user
   ```

3. **检查输出**：
   验证内核日志输出，确保 SoftIRQ 处理程序被调用，并且向量寄存器的上下文在中断前后保持一致。

> 这个例子展示了如何编写一个内核自测程序，用于测试被抢占的内核向量上下文。通过创建一个使用向量指令的内核线程，并在合适的时机触发 SoftIRQ 中断，可以验证内核是否正确保存和恢复向量寄存器的状态。实际应用中，你可能需要根据具体的硬件和内核配置调整向量指令和 SoftIRQ 的实现。

---

### 2) arm64/fp-stress.c 🔥

https://elixir.bootlin.com/linux/v6.10-rc5/source/tools/testing/selftests/arm64/fp

#### a) `child_start`

> 这段代码是一个典型的 Unix/Linux 系统编程示例，主要涉及创建子进程、重定向文件描述符和执行新程序。它的目标是设置子进程的环境，准备好所有必要的文件描述符，然后使用 `execl` 执行另一个程序。以下是对每个部分的详细分析：
>
> ### 代码段分析：
>
> #### 1. 重定向 `stdout` 到管道的写端
>
> ```c
> ret = dup2(pipefd[1], 1);
> if (ret == -1) {
>     fprintf(stderr, "dup2() %d\n", errno);
>     exit(EXIT_FAILURE);
> }
> ```
>
> - `dup2(pipefd[1], 1)`：将文件描述符 `pipefd[1]`（管道的写端）复制到文件描述符 `1`（`stdout`）。
> - 如果 `dup2` 调用失败，程序会打印错误信息并退出。
>
> #### 2. 将启动管道的读端复制到文件描述符 3
>
> ```c
> ret = dup2(startup_pipe[0], 3);
> if (ret == -1) {
>     fprintf(stderr, "dup2() %d\n", errno);
>     exit(EXIT_FAILURE);
> }
> ```
>
> - `dup2(startup_pipe[0], 3)`：将文件描述符 `startup_pipe[0]`（启动管道的读端）复制到文件描述符 `3`。
> - 如果 `dup2` 调用失败，程序会打印错误信息并退出。
>
> #### 3. 关闭除标准输入/输出/错误和指定文件描述符之外的所有文件描述符
>
> ```c
> for (i = 4; i < 8192; i++)
>     close(i);
> ```
>
> - 这个循环关闭所有从 4 到 8191 的文件描述符，确保除了标准输入/输出/错误（0、1、2）和前面设置的文件描述符（3）之外的所有文件描述符都被关闭。
>
> #### 4. 从启动管道读取数据
>
> ```c
> ret = read(3, &i, sizeof(i));
> if (ret < 0)
>     fprintf(stderr, "read(startp pipe) failed: %s (%d)\n", strerror(errno), errno);
> if (ret > 0)
>     fprintf(stderr, "%d bytes of data on startup pipe\n", ret);
> close(3);
> ```
>
> - `read(3, &i, sizeof(i))`：从文件描述符 3（启动管道的读端）读取数据。由于没有数据，这个调用应该阻塞，直到管道被关闭。
> - 如果读取失败，会打印错误信息。如果读取到数据（不期望的情况），会打印数据字节数。
> - 读取完成后，关闭文件描述符 3。
>
> #### 5. 使用 `execl` 执行新程序
>
> ```c
> ret = execl(program, program, NULL);
> fprintf(stderr, "execl(%s) failed: %d (%s)\n", program, errno, strerror(errno));
> exit(EXIT_FAILURE);
> ```
>
> - `execl(program, program, NULL)`：用新程序替换当前进程映像。`program` 是要执行的程序的路径。
> - 如果 `execl` 调用失败，程序会打印错误信息并退出。
>
> ### 总结：
>
> 这段代码的主要目的是：
>
> 1. 将子进程的标准输出重定向到一个管道，以便父进程可以读取子进程的输出。
> 2. 将启动管道的读端复制到文件描述符 3。
> 3. 关闭除标准文件描述符和特定文件描述符之外的所有文件描述符。
> 4. 读取启动管道的数据，这会阻塞子进程，直到管道被关闭。
> 5. 使用 `execl` 执行一个新程序，并在失败时处理错误。
>
> 这段代码展示了如何在 Unix/Linux 系统中进行进程间通信和文件描述符操作，是一个经典的系统编程示例。







### 3) fp_vector_.c













# 3 arm64: TIF_FOREIGN_FPSTATE