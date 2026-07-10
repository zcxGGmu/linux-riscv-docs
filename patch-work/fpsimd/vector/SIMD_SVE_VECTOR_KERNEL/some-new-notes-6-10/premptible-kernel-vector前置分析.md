# -1 参考

* [articles/20230805-linux-preemption-models.md · aosp-riscv/working-group - 码云 - 开源中国 (gitee.com)](https://gitee.com/aosp-riscv/working-group/blob/master/articles/20230805-linux-preemption-models.md#1-参考文档)
* [articles/20230806-linux-preempt-rt.md · aosp-riscv/working-group - 码云 - 开源中国 (gitee.com)](https://gitee.com/aosp-riscv/working-group/blob/master/articles/20230806-linux-preempt-rt.md#21-硬中断中存在的不确定性问题)
* [PKG_CONFIG_LIBDIR 和 PKG_CONFIG_PATH 的作用](https://blog.csdn.net/dmgy110/article/details/134554692)

* http://www.wowotech.net/irq_subsystem/soft-irq.html

# 0 计划/思考

- [ ] `1`: linux kernel premmption models (riscv目前没有在中断处理流程上，看到被 `CONFIG_PREEMPTION` 封装的代码 )
- [ ] `2`:  linux hardirq/softirq





# 1 premmption/scheduler

## 1.1 Introduction

Linux是一个多任务操作系统，这些任务通过共享cpu的方式实现了宏观上的并行执行。调度器的工作就是为这些任务分配cpu运行时间，并尽量保证它们在相同的调度策略中能得到公平对待。

但是不同任务对系统的重要性并不相同，如有的任务本身是用于管理调度功能的（如负载均衡），因此其不应该被抢占。而像idle进程仅仅是当cpu上没有可运行任务时，用于管理cpu空闲状态的，故其不应该抢占任何其它进程。为了更好地满足这些不同任务的调度需求，内核实现了几种具有不同调度策略的调度类。

### 1) 内核支持的调度类

当前内核默认支持五大调度类，分别是stop调度类、deadline调度类、rt调度类、cfs调度类以及idle调度类。它们的特点如下：

* `stop 调度类`：具有最高的优先级，它能抢占所有其它的进程，且不会被其它进程抢占；
* `deadline 调度类`：它的优先级介于stop调度类和rt调度类之间。主要用于那些在每个给定周期内，都需要在设定的截止期限之前被调度的任务。其原理如下图，即对于一个设定周期为period，截止调度期限为deadline的任务，调度器必须保证该任务在每个 period 的绿色区域中被调度。

![img](https://picx.zhimg.com/v2-6abedb9a84e399e7a4a1663194e62f01_720w.jpg?source=d16d100b)

* `rt 调度类`：它的优先级低于deadline调度类，但高于cfs调度类，其主要用于那些实时性要求较高的任务。这种任务将严格按照优先级调度，低优先级的任务不能抢占高优先级任务。但其对相同优先级的任务具有两种调度策略，`SCHED_FIFO` 和 `SCHED_RR` 。其中：
  * `SCHED_FIFO`：这种任务被调度后，只能被比它优先级更高的任务抢占。而与其优先级相同的任务，只能等该任务运行完成后才能被调度；
  * `SCHED_RR`：它与SCHED_FIFO唯一的不同，是若就绪队列中含有与其相同优先级的任务时，它们之间采用时间片轮转的方式调度；

* `cfs 调度类`：它采用完全公平调度算法，这种类型任务的调度依赖于虚拟cpu时间。它也包含两种调度策略，`SCHED_NORMAL` 和 `SCHED_BATCH` 。其中，`SCHED_BATCH` 是批处理进程，它们一般是计算密集型，且对实时性要求不高的任务。因此，这类进程被唤醒时并不会抢占其它进程，而只有在tick驱动的周期性调度时，才会执行抢占操作；

* `idle 调度类`：idle进程具有最低优先级，只有当cpu上没有其它可调度进程时，才会调度该进程运行；

### 2) 进程优先级

上一节提到了，不同调度类的进程具有不同优先级，进程优先级是调度器选择下一个调度进程的主要依据。为此内核定义了以下四个与优先级相关的变量：

```c
struct task_struct {
    //...
	int			prio;
	int			static_prio;
	int			normal_prio;
	unsigned int		rt_priority;
    //...
};
```

其中 `static_prio` 用于表示普通进程的优先级，`rt_priority` 表示实时进程的优先级，它们的范围分别为：

| 进程类型 | 优先级类型    | 优先级范围 | 含义                 |
| -------- | ------------- | ---------- | -------------------- |
| 普通进程 | `static_prio` | 139 - 100  | 其值越小，优先级越高 |
| 实时进程 | `rt_priority` | 0 - 99     | 其值越大，优先级越高 |

由于这两种优先级的含义并不相同，为了更方便地对它们进行统一管理，内核对其进行了归一化。其主要流程为：

1. 规定所有进程的优先级都归一化为其值越小，则优先级越高的方式。并用一个新的变量`normal_prio` 表示；

2. 普通进程的 `normal_prio` 等于其静态优先级 `static_prio`，实时进程的 `normal_prio` 按以下公式转换：

   ```c
   normal_prio = MAX_RT_PRIO - 1 - rt_prio   //（其中MAX_RT_PRIO = 100）
   ```

　　转换完成后，它们的关系如下图：

| 进程类型    | 优先级类型  | 优先级范围           | 含义                 |
| ----------- | ----------- | -------------------- | -------------------- |
| 普通进程    | static_prio | 139 - 100            | 其值越小，优先级越高 |
| normal_prio | 139 - 100   | 其值越小，优先级越高 |                      |
| 实时进程    | rt_priority | 0 - 99               | 其值越大，优先级越高 |
| normal_prio | 99 - 0      | 其值越小，优先级越高 |                      |

内核使用以下代码，实现优先级的归一化计算（`kernel/sched/core.c`）：

```c
static inline int __normal_prio(int policy, int rt_prio, int nice)
{
	int prio;

	if (dl_policy(policy))
		prio = MAX_DL_PRIO - 1;                  //1
	else if (rt_policy(policy))
		prio = MAX_RT_PRIO - 1 - rt_prio;        //2
	else
		prio = NICE_TO_PRIO(nice);               //3

	return prio;
}
```

1. 由于 `MAX_DL_PRIO` 等于0，故对于deadline调度类，其优先级固定为-1；
2. 同样由于 `MAX_RT_PRIO` 等于100，故对于实时调度类，其优先级为 `99 – rt_prio`；
3. 对于普通进程，其优先级是通过nice值计算的。nice值是用户态用于表示进程优先级的一个参数，其值为 `-20 ~ 19`，同样其值越小优先级越高。它与 `static_prio` 和 `normal_prio` 的关系都是有一个120的偏移。即 `static_prio = normal_prio = nice + 120`；

除了以上情况以外，还有一种stop调度类，内核规定其优先级为 `-2`。故综上所述，进程优先级之间的关系如下图：

![img](https://picx.zhimg.com/v2-b0ca13aafcf2b7e71c6a45ee587d6455_720w.jpg?source=d16d100b)

除非通过显式的优先级设置接口，改变进程优先级，否则 `normal_prio` 在进程执行过程中是不变的。但是内核在运行过程中，可能需要临时修改一个进程的优先级，以解决一些像优先级反转之类的问题。比如，rt mutex会将持有锁进程的优先级，临时提高到与阻塞在该锁上优先级最高的进程相同，以避免优先级反转。为此，内核引入了一个变量 `prio` 用于表示动态优先级，它在系统运行过程中可能会被临时修改，而调度器实际使用的就是动态优先级。

### 3) 调度时机

根据进程是否自愿放弃cpu，调度方式可分为主动调度和抢占调度两类，它们的区别如下：

> 1. **主动调度：进程需要等待IO、锁等资源，而主动放弃cpu；**
> 2. **抢占调度：进程由于时间片用完，或被优先级更高的进程抢占，而被强制剥夺cpu；**

内核中，那些由于等待资源而需要阻塞的场景，会直接调用 `schedule()` 执行实际的调度流程。而其它需要调度的场景一般都只是设置一个 `TIF_NEED_RESCHED` 标志，并在下一个抢占点到来时才执行实际的抢占操作。

在支持内核抢占之前，只有在系统调用返回用户态之前，或者中断返回用户态之前才能执行抢占操作。而在支持内核抢占以后，即使在内核执行路径中也允许抢占，因此内核支持了更多的抢占点，比如： 

>  **1、从中断上下文返回内核态时，会执行抢占操作**

![img](https://pic1.zhimg.com/v2-d107546da8f95d6a75e53b37de0bb31b_720w.jpg?source=d16d100b)

> **2、开启抢占时，会按以下流程执行抢占操作**

![img](https://pic1.zhimg.com/v2-7bec9d61e6f750f45d547affb17da6f8_720w.jpg?source=d16d100b)

>  **3、开启软中断时，会执行以下抢占流程**

![img](https://pic1.zhimg.com/v2-940e964c15b38720939db77067d3d5c1_720w.jpg?source=d16d100b)

> **4、内核代码中还可以显式地插入cond_resched()，以执行抢占操作**

![img](https://picx.zhimg.com/v2-e18db702e61aee894d84adcaf48b827c_720w.jpg?source=d16d100b)

## 1.2 Scheduler

### 1) 运行队列

内核进程调度是基于cpu的，因此为每个cpu都分配了一个运行队列结构体。而且由于不同调度类含有不同的调度策略，故除了 `stop machine` 和 `idle` 两个在其内部不参与调度的调度类以外，其它的调度类又都会维护其自身的运行队列。以下为它们之间的关系：

![img](https://pic1.zhimg.com/v2-12cb9a39a6ad0966d8c83ab52b18c1a8_720w.jpg?source=d16d100b)

从上图可看出，cfs和dl运行队列都是基于红黑树，而rt运行队列是基于链表的。特点如下： 

* `cfs` 运行队列是通过 `vruntime` 排序的，其中 `vruntime` 最小的调度实体位于左下方。并用一个指针 `rb_leftmost` 指向该节点，从而使调度器能快速地获取到下一个需要调度的实体；

* `rt` 调度类为每个rt优先级都维护了一个链表。这样调度器只要从优先级最高的链表开始遍历，找到的第一个节点即为下一个需要调度的实体；
* `dl` 运行队列与 `cfs` 运行队列一样，都是基于红黑树实现。其区别为，它是通过 `deadline` 的到期时间进行排序，且最先到期的调度实体位于红黑树的左下方。

### 2) 调度类回调

由于实际的调度策略取决于不同的调度类，因此核心调度函数只需要实现总体的调度流程，而调度相关的具体策略都由调度类实现。因此内核为调度类抽象出了一组回调函数，以供核心调度函数使用。以下为该数据结构的定义：

```c
struct sched_class {
#ifdef CONFIG_UCLAMP_TASK
	int uclamp_enabled;
#endif
	void (*enqueue_task) (struct rq *rq, struct task_struct *p, int flags);
	void (*dequeue_task) (struct rq *rq, struct task_struct *p, int flags);
	void (*yield_task)   (struct rq *rq);
	bool (*yield_to_task)(struct rq *rq, struct task_struct *p);
	void (*check_preempt_curr)(struct rq *rq, struct task_struct *p, int flags);
	struct task_struct *(*pick_next_task)(struct rq *rq);
	void (*put_prev_task)(struct rq *rq, struct task_struct *p);
	void (*set_next_task)(struct rq *rq, struct task_struct *p, bool first);

#ifdef CONFIG_SMP
	int (*balance)(struct rq *rq, struct task_struct *prev, struct rq_flags *rf);
	int  (*select_task_rq)(struct task_struct *p, int task_cpu, int flags);
	struct task_struct * (*pick_task)(struct rq *rq);
	void (*migrate_task_rq)(struct task_struct *p, int new_cpu);
	void (*task_woken)(struct rq *this_rq, struct task_struct *task);
	void (*set_cpus_allowed)(struct task_struct *p,
				 const struct cpumask *newmask,
				 u32 flags);
	void (*rq_online)(struct rq *rq);
	void (*rq_offline)(struct rq *rq);
	struct rq *(*find_lock_rq)(struct task_struct *p, struct rq *rq);
#endif

	void (*task_tick)(struct rq *rq, struct task_struct *p, int queued);
	void (*task_fork)(struct task_struct *p);
	void (*task_dead)(struct task_struct *p);

	void (*switched_from)(struct rq *this_rq, struct task_struct *task);
	void (*switched_to)  (struct rq *this_rq, struct task_struct *task);
	void (*prio_changed) (struct rq *this_rq, struct task_struct *task,
			      int oldprio);
	unsigned int (*get_rr_interval)(struct rq *rq,
					struct task_struct *task);
	void (*update_curr)(struct rq *rq);

#define TASK_SET_GROUP		0
#define TASK_MOVE_GROUP		1

#ifdef CONFIG_FAIR_GROUP_SCHED
	void (*task_change_group)(struct task_struct *p, int type);
#endif
};
```

其中一些常用回调函数的含义如下：

* `enqueue_task`：将一个进程插入就绪队列中
* `dequeue_task`：将一个进程从运行队列中移除
* `yield_task`：当前进程放弃cpu，yield进程在调度时将会被忽略
* `check_preempt_curr`：检查当前进程是否可以被其它进程抢占
* `pick_next_task`：获取下一个将要被调度运行的进程
* `put_prev_task`：将被调度出来的进程重新插入就绪队列

以下为其与核心调度函数的关系示意图：

![img](https://pica.zhimg.com/v2-6fda0aa016490fd5e80534429a2aa788_720w.jpg?source=d16d100b)

### 3) 核心调度函数

内核调度器的实现，主要**基于主调度函数和周期性调度函数。**其中主调度函数即为 `schedule`，它会执行实际的调度流程。周期性调度函数由cpu的tick时钟驱动，正常情况下其调度频率为HZ，但是当cpu进入NO_HZ模式后，该调度器也会相应地停止。

#### a) 主调度函数

主调度函数用于执行实际的调度流程，其主要调用流程如下：

![img](https://picx.zhimg.com/v2-083213fab40d4f4678caf334c0da4d43_720w.jpg?source=d16d100b)

由于当前正处于调度流程中，显然不能被抢占，因此在函数开头通过 `preempt_disable` 关闭了抢占功能。然后通过 `cpu_rq` 获取当前cpu对应的rq指针，并调用 `pick_next_task` 函数获取下一个将要运行的进程，最后通过 `context_switch` 执行实际的上下文切换操作。

其中，`pick_next_task` 函数的实现如下：

```c
static inline struct task_struct *
__pick_next_task(struct rq *rq, struct task_struct *prev, struct rq_flags *rf)
{
	//...
	if (likely(prev->sched_class <= &fair_sched_class &&
		   rq->nr_running == rq->cfs.h_nr_running)) {             //1

		p = pick_next_task_fair(rq, prev, rf);
		if (unlikely(p == RETRY_TASK))
			goto restart;

		if (!p) {
			put_prev_task(rq, prev);         
			p = pick_next_task_idle(rq);                          //2
		}

		return p;
	}

restart:
	put_prev_task_balance(rq, prev, rf);                         

	for_each_class(class) {
		p = class->pick_next_task(rq);                            //3
		if (p)
			return p;
	}
	//...
}
```

1. 由于一般的系统中，`cfs` 进程数量最多，因此为了优化效率，若下一个进程为 `cfs` 进程，则直接调用 `cfs` 类的接口；
2. 由于此时肯定没有可运行的实时进程，因此若 `cfs` 运行队列中没有合适的进程，则cpu将运行idle进程以进入空闲状态。注意这里先调用了 `put_prev_task` 接口，若prev进程仍然处于就绪状态，则将其重新添加回 `cfs` 运行队列，否则不将其添加回去。因此，若其被添加回运行队列，且没有更高优先级的进程加入时，则在下一个调度点到来时，它将会抢占idle进程而被重新调度运行；
3. 每个调度类的优先级不同，一般情况下调度函数总是希望，调度就绪队列中优先级最高的进程。因此 `for_each_class` 会从优先级最高的调度类开始遍历，并通过其 `pick_next_task` 回调获取最合适的待运行进程。以下为其定义：

```assembly
#define for_each_class(class) \
	for_class_range(class, sched_class_highest, sched_class_lowest)
```

找到合适的进程以后，就可以通过 `context_switch` 执行实际的上下文切换操作了，在arm64架构下该流程最终由，以下所示的 `__switch_to` 函数完成：

```c
__notrace_funcgraph struct task_struct *__switch_to(struct task_struct *prev,
				struct task_struct *next)
{
	//...
	last = cpu_switch_to(prev, next);
	return last;
}
```

`cpu_switch_to` 比较简单，主要是保存上一个进程的上下文，并将下一个进程的上下文恢复到cpu寄存器中，最后调用 `ret` 从新进程开始执行。其中上下文包括栈指针、callee寄存器以及lr寄存器的值：

```assembly
SYM_FUNC_START(cpu_switch_to)
	mov	x10, #THREAD_CPU_CONTEXT
	add	x8, x0, x10
	mov	x9, sp
	stp	x19, x20, [x8], #16		// store callee-saved registers
	stp	x21, x22, [x8], #16
	stp	x23, x24, [x8], #16
	stp	x25, x26, [x8], #16
	stp	x27, x28, [x8], #16
	stp	x29, x9, [x8], #16
	str	lr, [x8]
	add	x8, x1, x10
	ldp	x19, x20, [x8], #16		// restore callee-saved registers
	ldp	x21, x22, [x8], #16
	ldp	x23, x24, [x8], #16
	ldp	x25, x26, [x8], #16
	ldp	x27, x28, [x8], #16
	ldp	x29, x9, [x8], #16
	ldr	lr, [x8]
	mov	sp, x9
	msr	sp_el0, x1
	ptrauth_keys_install_kernel x1, x8, x9, x10
	scs_save x0
	scs_load x1
	ret
SYM_FUNC_END(cpu_switch_to)
```

#### b) 周期调度函数

周期调度函数，由timer时钟中断驱动，用于周期性地检查进程时间片是否到期，以及是否有抢占事件等，该函数的调用流程如下：

![img](https://pic1.zhimg.com/v2-f3c5905a2ae95fc79dc8f68de914534c_720w.jpg?source=d16d100b)

它主要处理以下任务：

1. 管理与进程调度相关的统计数据，如通过 `update_rq_clock` 函数更新就绪队列的时钟，以及`calc_global_load_tick` 函数更新就绪队列的cpu负载；
2. 调用给定调度类对应的周期性调度回调函数，其具体流程取决于调度类的实现。

---

##### riscv timer硬件逻辑

riscv上有两个最基本的中断控制器aclint和plic，前者是核内的中断控制器，主要是用来产生timer中断和software中断，后者主要用来收集外设的中断，plic通过外部中断线向CPU报中断。

timer相关的寄存器以及寄存器域段有:

* `mip/mie` 里和timer相关的域段，`mtime` 以及 `mtimecmp`。
* `mie` 里有控制timer中断使能的bit: `MTIE/STIE`，控制M mode和S mode timer interrupter是否使能，`mip` 里有表示是否存在pending的timer中断的bit: `MTIP/STIP`。

* `mtime` 是一个可读可写的计数器，其中的数值以一定的时间间隔递增，计数器计满后会回绕，`mtimecmp` 寄存器里的数值用来和 `mtime` 做比较，当 `mtime` 的值大于等于 `mtimecmp` 的值，并且MTIE使能时，M mode timer中断被触发。

软件可以在timer中断处理函数里，去更新 `mtimecmp` 的值，从而维持一个固定周期的时钟中断，
一般这个中断就是Linux内核的时钟中断。软件也可以写STIP触发一个S mode timer中断。

---

aclint上把 `mtime` 以及 `mtimecmp`，抽象成一个M mode timer这样的设备，`mtime` 和 `mtimecmp` 是这个设备上的MMIO接口，一个M mode timer上有一个 `mtime`，一个M mode timer为服务的每个hart设置一个 `mtimecmp`。

aclint协议上描述，一个系统可能会有多个M mode timer设备，这样做的目的是，在CPU存在分层拓扑的时候，比如 CPU cluster/node/socket 时，一组CPU可以和一个M mode timer做在一起，方便这一组CPU的功耗管理。

> 在系统中有多个M mode timer时，需要做多个 `mtime` 数值上的同步，使得多个 `mtime` 之间的误差在一定范围之内。

aclint只定义了M mode timer，riscv的sstc扩展定义了S mode下的timer。对于S mode timer，
sstc只在每个hart上增加了 `stimecmp` 寄存器，当 `time` 计数值大于等于 `stimecmp` 时，触发S mode timer中断，`stimecmp` 是一个CSR寄存器。

从timer整体定义上看，riscv这里定义的比较乱，M mode timer抽象成一个外设，接口是MMIO，但是S mode timer却改成了CSR，而且sstc还修改了riscv特权级spec里的一些系统寄存器的定义，`mip.STIP` 这个域段在 `stimecmp` 有无时，读写属性是不一样的：

* 当支持S mode但是没有实现`stimecmp` 时，`mip.STIP` 是读写的，写这个bit会触发S mode timer中断；
* 当实现 `stimecmp` 时，mip.STIP是只读的；

这样的实现意味着，在有S mode timer的系统上，将无法使用M mode timer从M mode通过mip.STIP触发S mode timer中断，相关的软件方案需要随之变动。sstc里还有虚拟化相关的描述，这些需要在独立文档中描述。

> riscv上还定义了一个用户态可以访问的计数器 `RDTIME`，这个计数器从开机起，就以一定的频率一直递增。

##### riscv timer linux support

> * 内核timer初始化在：`arch/riscv/kernel/time.c: time_init`
> * 内核相关驱动的位置在：`drivers/clocksource/timer-riscv.c`
> * S mode timer的内核patch：https://lwn.net/Articles/886863/

riscv timer的内核驱动，把对应的 `of_device_id` 静态定义到 `__timer_of_table` 段里。`time_init` 里的 `timer_probe` 会扫描 `__timer_of_table` 这个段里timer相关的of_device_id, 然后调用对应的初始化函数，这里就是调用 `riscv_timer_init_dt`，这个函数会找见intc对应的domain，通过domain和S mode timer硬件中断号，得到S mode timer对应中断的virq，最后向virq注册S timer的中断处理函数：

```c
riscv_timer_init_dt
  +-> riscv_clock_event_irq = irq_create_mapping(domain, RV_IRQ_TIMER)
  +-> request_percpu_irq(riscv_clock_event_irq, riscv_timer_interrupt, ...)
```

---

riscv timer驱动，会注册 `clocksource` 和 `clock_event_device` 。

* `clocksource`就是指，不断递增的时钟源。比如，riscv上的 `mtime` 寄存器以一定的频率增加计数，它就是一个clocksource，riscv_clocksource提供一个read接口，通过这个接口可以得到当前`mtime` 计数器里的值。

  在 riscv qemu virt 平台上，这个计数器的频率定义在 cpus 节点的`timebase-frequency` 字段，它的值是 `0x989680`，就是十进制的10000000，也就是说这个计数器 `10ns` 计数一下。

* `clock_event_device` 指的是，可以产生和时钟相关事件的device。比如，riscv上当 `mtime` 的值大于等于 `mtimecmp` 的值时会上报一个M mode timer的中断，`mtime` 和 `mtimecmp` 就可以被看作一个 `clock_event_device`。

riscv timer驱动里定义的 `struct clock_event_device riscv_clock_event` 是个per CPU变量，timer的中断处理函数就是调用 `riscv_clock_event` 里的event_handler。但是这个回调函数，并不是在驱动里直接提供的。

`event_handler` 的注册，是通过这个驱动里注册的cpu hotplug回调riscv_timer_starting_cpu
完成的，大概的调用逻辑如下，event_handler实际上是一个公共函数 `tick_handle_periodic`。

```c
start_kernel
  +-> time_init
    +-> timer_probe
      +-> cpuhp_setup_state
        +-> __cpuhp_setup_state
          +-> __cpuhp_setup_state_cpuslocked
            +-> cpuhp_issue_call
              +-> cpuhp_invoke_callback
                +-> riscv_timer_starting_cpu
                  +-> clockevents_config_and_register
                    +-> clockevents_register_device
                      +-> tick_check_new_device
                        +-> tick_setup_device
                          +-> tick_setup_periodic
			        /* event_handler回调 */
			    +-> tick_handle_periodic
```

`tick_handle_periodic` 就是每次时钟中断时要运行的逻辑，相关逻辑已经和调度有关系，
在另外讲调度的文章里独立分析吧。实际上，`tick_handle_periodic` 只是在内核开始的时候用，内核随后会把event_handler切到高精度定时器的回调函数上 `hrtimer_interrupt`，这个函数里只是处理时间相关的东西，tick时发生的调度要回到entry.S里，也就是处理完timer中断再处理调度相关的逻辑。

### 4) CFS周期性调度 

内核为每个cpu，都维护了一个周期性的 tick 定时器，用于定期更新cpu相关统计信息，和驱动调度器运转。该定时器对应的 clock_event_device 会周期性地触发中断，并在中断处理流程中调用周期性调度函数 `scheduler_tick` 。

#### a) 基于低精度定时器的调度流程

以下为其在arm64架构下，使用低精度定时器方案时的调用流程：

![img](https://pic3.zhimg.com/v2-fdfe29d345bbc589c87fd27adb1b530a_b.jpg)

`scheduler_tick` 函数主要执行调度相关的时间信息更新，检查当前执行进程是否应该被抢占，以及触发负载均衡流程。由于负载均衡流程将在其他文章中单独介绍，代码如下：

```c
void scheduler_tick(void)
{
	//...
	sched_clock_tick();                              //1
    //...
	update_rq_clock(rq);                             //2
	//...
	curr->sched_class->task_tick(rq, curr, 0);       //3
}
```

1. 由于每个cpu的调度时钟是per-cpu的，因此若该时钟的稳定性不足，可能会导致时钟跳变。为了防止这一情况，若配置了 `CONFIG_HAVE_UNSTABLE_SCHED_CLOCK` 选项，就可以使用系统的基准时钟 `ktime` 对其进行校准，本函数即是用于在每个tick中执行校准流程；
2. 该函数用于更新本cpu运行队列相关的时间信息；
3. 该函数为周期性调度执行的主流程；

---

对于 cfs 进程，该回调函数为 `task_tick_fair`，以下：

```c
static void task_tick_fair(struct rq *rq, struct task_struct *curr, int queued)
{
	struct cfs_rq *cfs_rq;
	struct sched_entity *se = &curr->se;

	for_each_sched_entity(se) {                     //1
		cfs_rq = cfs_rq_of(se);
		entity_tick(cfs_rq, se, queued);        	//2
	}
    //...
}
```

1. 若当前调度实体为 `task_group`，需要逐级处理其父实体；
2. 周期性调度主流程，其代码实现如下：

```c
static void entity_tick(struct cfs_rq *cfs_rq, struct sched_entity *curr, int queued)
{
	//...
#ifdef CONFIG_SCHED_HRTICK
	if (queued) {
		resched_curr(rq_of(cfs_rq));
		return;
	}
	if (!sched_feat(DOUBLE_TICK) &&
			hrtimer_active(&rq_of(cfs_rq)->hrtick_timer))
		return;
#endif
	if (cfs_rq->nr_running > 1)
		check_preempt_tick(cfs_rq, curr);
}
```

---

我们先看不支持高精度定时器的情形，此时通过 `check_preempt_tick` 函数，实现具体的调度策略。主要通过时间片和虚拟运行时间，判断当前调度实体是否应该被抢占，主要包含以下三种情形：

1. 当前进程已经用完当前调度周期的时间片，则执行调度操作；
2. 当前进程虽然没有用完时间片，但就绪队列中含有可以抢占当前调度实体的实体，则执行抢占操作；
3. 为了确保调度粒度，若当前进程运行时间小于最小调度粒度，则不执行抢占操作；

代码如下：

```c
static void check_preempt_tick(struct cfs_rq *cfs_rq, struct sched_entity *curr)
{
	//...
	ideal_runtime = sched_slice(cfs_rq, curr);                 //1
	delta_exec = curr->sum_exec_runtime - curr->prev_sum_exec_runtime;
	if (delta_exec > ideal_runtime) {                          //2
		resched_curr(rq_of(cfs_rq));
		clear_buddies(cfs_rq, curr);
		return;
	}

	if (delta_exec < sysctl_sched_min_granularity)             //3
		return;

	se = __pick_first_entity(cfs_rq);                                    
	delta = curr->vruntime - se->vruntime;                     //4

	if (delta < 0)                                             //5
		return;

	if (delta > ideal_runtime)                                 //6
		resched_curr(rq_of(cfs_rq));
}
```

1. 获取当前调度实体，在一个调度周期中的时间片
2. 若其本次执行时间已经超过其时间片，则执行调度操作
3. 若本次执行时间小于最小调度粒度，则本次不调度
4. 获取就绪队列中vruntime最小的调度实体，并计算其与当前调度实体vruntime的差
5. 若当前调度实体依然时vruntime最小的，则显然可以继续执行
6. 能抢占的条件是它们的差值大于一个时间片

以上抢占操作，通过 `resched_curr` 函数实现，它实际只是将抢占标志设置到 `thread_info` 中的 `preempt.need_resched` 变量中，而实际的抢占流程需要在下一个抢占点到来时才会执行。

## 1.3 riscv timer 🔥

### 1) Sstc 扩展

由于 `mtimecmp` 只能在 M 模式下访问，对于 S/HS 模式下的内核和 VU/VS 模式下的虚拟机需要通过 SBI 才能访问，会造成较大的中断延迟和性能开销。为了解决这一问题，RISC-V 新增了 Sstc 拓展支持（已批准但尚未最终集成到规范中）。

Sstc 扩展为 HS 模式和 VS 模式分别新增了 `stimecmp` 和 `vstimecmp` 寄存器，当 $time >= stimecmp$ (HS)或 $time+htimedelta >= vstimecmp$ (VS)时会产生 timer 中断，不再需要通过 SBI 陷入其他模式。

详见 [RISC-V “stimecmp / vstimecmp” 扩展](https://github.com/riscv/riscv-time-compare/releases/download/v0.5.4/Sstc.pdf) 。

### 2) Linux timer 实现

Linux 将底层时钟硬件抽象为两类设备：clockevent 和 clocksource，前者用来在未来指定的时间产生中断，通常用作定时器；后者则用于维护自系统启动以来所经过的时间。

当前 Linux 为 RISC-V 根据内核运行模式实现了两套驱动，代码路径为 drivers/clocksource/timer-riscv.c 和 drivers/clocksource/timer-clint.c。

 Linux 对 Sstc 扩展的支持：[Add Sstc extension support](https://lkml.org/lkml/2022/3/4/1175)。

`mtime` 频率由设备树 CPU 节点中的 timebase-frequency 定义，不同平台都各不相同，如 Kendryte K210 的频率是 7.8 MHz，平头哥 C910 的频率是 3 MHz，SiFive Unmatched A00 频率为 1 MHz。

#### a) NoMMU timer-clint.c

timer-clint.c 驱动适用于 NoMMU 系统，内核运行在 M 模式下，通过 CONFIG_CLINT_TIMER 使能该驱动。RV64 下 clocksource 是通过直接读取 `mtime` 寄存器实现的，RV32 系统需要分两次读取，并需要考虑产生进位的情况。

```
#ifdef CONFIG_64BIT
static u64 notrace clint_get_cycles64(void)
{
    return clint_get_cycles();
}
#else /* CONFIG_64BIT */
static u64 notrace clint_get_cycles64(void)
{
    u32 hi, lo;

    do {
        hi = clint_get_cycles_hi();
        lo = clint_get_cycles();
    } while (hi != clint_get_cycles_hi());

    return ((u64)hi << 32) | lo;
}
#endif /* CONFIG_64BIT */

C
```

`clint_get_cycles/clint_get_cycles_hi` 直接通过内存访问寄存器。

```
#ifdef CONFIG_64BIT
#define clint_get_cycles()  readq_relaxed(clint_timer_val)
#else
#define clint_get_cycles()  readl_relaxed(clint_timer_val)
#define clint_get_cycles_hi()   readl_relaxed(((u32 *)clint_timer_val) + 1)
#endif


C
```

clockevent 是通过使能 `mie` 的 TIMER 中断，并向 `mtimecmp` 寄存器写入期望的计数值实现的。

```
static int clint_clock_next_event(unsigned long delta,
                   struct clock_event_device *ce)
{
    void __iomem *r = clint_timer_cmp +
              cpuid_to_hartid_map(smp_processor_id());

    csr_set(CSR_IE, IE_TIE);
    writeq_relaxed(clint_get_cycles64() + delta, r);
    return 0;
}

C
```

#### b) MMU timer-riscv.c

timer-riscv.c 驱动适用于有 MMU 的场景，内核运行在 S/HS 模式下，通过 CONFIG_RISCV_TIMER 可以使能该驱动。和 timer-riscv.c 的驱动相比，本质上也是访问 `mtime` 和 `mtimecmp` 寄存器，不过由于 S 模式下无法直接访问它们，需要通过其他方式间接完成。

RV64 的 clocksource 是通过 csrr 直接读取 `time` 寄存器实现的；在 RV32 系统由于一条指令无法读完，需要分两次读取 `time` 和 `timeh`， 并考虑可能发生进位的情况。前面提到 `time` 和 `timeh` 这两个 CSR 是 `mtime` 寄存器的映射，因此频率与精度和 `mtime` 是一致的。

```
#ifdef CONFIG_64BIT
static inline u64 get_cycles64(void)
{
    return get_cycles();
}
#else /* CONFIG_64BIT */
static inline u64 get_cycles64(void)
{
    u32 hi, lo;

    do {
        hi = get_cycles_hi();
        lo = get_cycles();
    } while (hi != get_cycles_hi());

    return ((u64)hi << 32) | lo;
}
#endif /* CONFIG_64BIT */

static inline cycles_t get_cycles(void)
{
    return csr_read(CSR_TIME);
}
static inline u32 get_cycles_hi(void)
{
    return csr_read(CSR_TIMEH);
}

C
```

clockevent 则是通过 SBI 间接访问 `mtimecmp` 实现的。

```
static int riscv_clock_next_event(unsigned long delta,
        struct clock_event_device *ce)
{
    csr_set(CSR_IE, IE_TIE);
    sbi_set_timer(get_cycles64() + delta);
    return 0;
}

C
```

这里以 OpenSBI 来分析，如果不支持 Sstc 扩展则调用在 SBI 中注册的 `timer_event_start` 函数写入 `mtimecmp`，这个需要具体平台自己去实现。

```
void sbi_timer_event_start(u64 next_event)
{
    sbi_pmu_ctr_incr_fw(SBI_PMU_FW_SET_TIMER);

    /**
     * Update the stimecmp directly if available. This allows
     * the older software to leverage sstc extension on newer hardware.
     */
    if (sbi_hart_has_feature(sbi_scratch_thishart_ptr(), SBI_HART_HAS_SSTC)) {
#if __riscv_xlen == 32
        csr_write(CSR_STIMECMP, next_event & 0xFFFFFFFF);
        csr_write(CSR_STIMECMPH, next_event >> 32);
#else
        csr_write(CSR_STIMECMP, next_event);
#endif
    } else if (timer_dev && timer_dev->timer_event_start) {
        timer_dev->timer_event_start(next_event);
        csr_clear(CSR_MIP, MIP_STIP);
    }
    csr_set(CSR_MIE, MIP_MTIP);
}

C
```

在支持 Sstc 扩展后，可以直接访问 `stimecmp` 寄存器，避免通过 SBI 调用的方式产生的开销。社区已开展相关工作：[RISC-V: Prefer sstc extension if available](https://lore.kernel.org/all/20220426185245.281182-1-atishp@rivosinc.com/)。

#### c) KVM vcpu_timer.c

在 VS 模式下读取 `time` 时，KVM 会返回真正的 `time` 加上 `htimedelta`。

```
static u64 kvm_riscv_current_cycles(struct kvm_guest_timer *gt)
{
    return get_cycles64() + gt->time_delta;
}

C
```

在 VS 模式下设置 `mtimecmp` 时，KVM 会开启一个已经创建好的高精度定时器，并把定时器的到期时间设置为写入 `mtimecmp` 值对应的 ns。

```
int kvm_riscv_vcpu_timer_next_event(struct kvm_vcpu *vcpu, u64 ncycles)
{
    struct kvm_vcpu_timer *t = &vcpu->arch.timer;
    struct kvm_guest_timer *gt = &vcpu->kvm->arch.timer;
    u64 delta_ns;

    if (!t->init_done)
        return -EINVAL;

    kvm_riscv_vcpu_unset_interrupt(vcpu, IRQ_VS_TIMER);

    delta_ns = kvm_riscv_delta_cycles2ns(ncycles, gt, t);
    t->next_cycles = ncycles;
    hrtimer_start(&t->hrt, ktime_set(0, delta_ns), HRTIMER_MODE_REL);
    t->next_set = true;

    return 0;
}

C
```

在定时器到期后，KVM 会为 Guest 产生 TIMER 中断。

```
static enum hrtimer_restart kvm_riscv_vcpu_hrtimer_expired(struct hrtimer *h)
{
    u64 delta_ns;
    struct kvm_vcpu_timer *t = container_of(h, struct kvm_vcpu_timer, hrt);
    struct kvm_vcpu *vcpu = container_of(t, struct kvm_vcpu, arch.timer);
    struct kvm_guest_timer *gt = &vcpu->kvm->arch.timer;

    if (kvm_riscv_current_cycles(gt) < t->next_cycles) {
        delta_ns = kvm_rizscv_delta_cycles2ns(t->next_cycles, gt, t);
        hrtimer_forward_now(&t->hrt, ktime_set(0, delta_ns));
        return HRTIMER_RESTART;
    }

    t->next_set = false;
    kvm_riscv_vcpu_set_interrupt(vcpu, IRQ_VS_TIMER);

    return HRTIMER_NORESTART;
}

C
```

因此 VS 模式设置时钟事件需要通过 SBI 调用进入 HS 模式然后再进入 M 模式，会产生较大的开销。同样，在支持 Sstc 扩展后，可以直接访问 `vstimecmp` 并产生 timer 中断，社区目前已经开展了相关的工作：[RISC-V: KVM: Support sstc extension](https://lore.kernel.org/all/20220426185245.281182-4-atishp@rivosinc.com/)。

