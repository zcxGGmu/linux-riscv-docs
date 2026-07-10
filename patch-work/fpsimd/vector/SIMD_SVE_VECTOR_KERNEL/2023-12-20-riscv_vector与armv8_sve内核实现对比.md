---
title: riscv_vector与armv8_sve内核实现对比

date: 2023-12-20 17:00:00 +0800

categories: [SIMD内核支持]

tags: [vector]

description: 
---

# 0 资料

* **riscv_vector**
  * [riscv-v-spec/v-spec.adoc at master · riscv/riscv-v-spec (github.com)](https://github.com/riscv/riscv-v-spec/blob/master/v-spec.adoc)
  * [[PATCH v10 00/16\] riscv: Add vector ISA support - Greentime Hu (kernel.org)](https://lore.kernel.org/all/cover.1652257230.git.greentime.hu@sifive.com/)
  * [ARM与RISC-V的向量扩展比较 - 知乎 (zhihu.com)](https://zhuanlan.zhihu.com/p/370293866)
  * [riscv-v-spec-1.0（矢量指令） 学习理解（1-5 & 18 segment）-CSDN博客](https://blog.csdn.net/weixin_43348382/article/details/113736632)
* **armv8_sve**
  * [Scalable Vector Extension support for AArch64 Linux — The Linux Kernel documentation](https://www.kernel.org/doc/html/v5.15/arm64/sve.html)
  * [[PATCH v5 00/30\] ARM Scalable Vector Extension (SVE) - Dave Martin (kernel.org)](https://lore.kernel.org/all/1509465082-30427-1-git-send-email-Dave.Martin@arm.com/)
  * [[PATCH v7 00/27\] KVM: arm64: SVE guest support [LWN.net]](https://lwn.net/ml/linux-arm-kernel/1553864452-15080-1-git-send-email-Dave.Martin@arm.com/)
  * [ARM SVE特性学习 - 知乎 (zhihu.com)](https://zhuanlan.zhihu.com/p/382429327)
  * [Linux 内核使用浮点问题_内核开启硬浮点-CSDN博客](https://blog.csdn.net/pen_cil/article/details/105467817)
  * [基于armv8的kvm实现分析（四）cpu虚拟化 - 知乎 (zhihu.com)](https://zhuanlan.zhihu.com/p/530665800)



# 1 ARM与RISC-V向量扩展对比

ARM SVE和RISC-V Vector特性引入的目的都是针对向量计算，实现指令级别的SIMD高性能运算。本文并不会分析两者在向量运算上的一些异同，比如：执行的向量指令格式有什么区别、提供的寄存器组的区别等，因为这些都是用户态应用程序或者标准库、编译器关注的事情，本文只会讨论一件事：**目前Linux Kernel在多核系统上支持这两种特性上有什么区别？**

相应规范如下：

* riscv
  * [riscv-v-spec/v-spec.adoc at master · riscv/riscv-v-spec (github.com)](https://github.com/riscv/riscv-v-spec/blob/master/v-spec.adoc#vector-context-status-in-mstatus)
* armv8
  * [ARM Architecture Reference Manual Supplement - The Scalable Vector Extension (SVE), for ARMv8-A](https://developer.arm.com/documentation/ddi0584/ab/?lang=en)

我们只关注部分控制状态寄存器的作用即可。

## 1.1 RISC-V "V" Vector Extension

### Vector Extension Programmer’s Model

向量扩展向基标量RISC-V ISA中增加了32个向量寄存器(v0-v31)以及7个无特权的CSRS（控制和状态寄存器），分别是vstart、vxsat、vxrm、vcsr、vl、vtype、vlenb。向量寄存器的位宽为固定的VLEN宽度。

riscv 架构规定了一些只在机器模式下支持的寄存器，机器模式是riscv中硬件线程执行时的最高权限模式。机器模式对内存，I/O和一些对于启动和配置系统来说必要的底层功能有着完全的使用权。通常用户写的程序都在用户模式执行，用户态具有最低级别的权限。当用户程序需要使用一些底层硬件设备或者执行出现了异常又或者外围设备对正在执行的处理器发起了中断请求，那么cpu就会由用户态切换至内核态，也就是切换到机器模式下，将cpu的控制权，转交给内核程序。

riscv把程序执行时出现的异常，或者外部中断统称为陷阱（陷阱其实很好理解，因为不管是异常还是中断，cpu都会由用户态陷入内核态，这个陷入内核的过程就可以理解成踩入了陷阱里，要经过一些其他的操作，才能爬出陷阱，恢复正常行走）。当遇到陷阱时，首先要将当前的pc保存下来，方便之后进行恢复。然后清空异常指令之前的流水线。接下来根据对应的陷阱类型，切换到对应的程序入口，开始执行内核程序（ 内核程序也是由一条条指令组成的，同样需要在流水线上执行）。等内核程序执行完成后，在重新把cpu的控制权转交给用户程序，从之前保存的pc指针开始重新取指，执行。

在重新回到riscv规定了一些只支持机器模式相关的寄存器的话题。`mstatus` 寄存器是机器模式下的状态寄存器，其中 `mstatus[10:9]` 是向量上下文状态域。

> 一个进程存储在处理器各寄存器中的中间数据叫做进程的上下文，所以进程的切换实质上就是被中止运行进程与待运行进程上下文的切换

`mstatus.vs` 域同 `mstatus.fs` 类似。当 `mstatus.vs` 域被写成0时，试图执行向量指令或者访问向量寄存器均会引发非法指令异常。当`mstatus.vs` 域被设置为初始状态或者干净的状态，只要执行了相关的指令改变了vpu（vector processor unit）状态，该域就会被改写成dirty的状态。

`misa` 寄存器用于指示当前处理器的架构特性，该寄存器高两位用于表示当前处理器所支持的架构位数；该寄存器低 26 位用于指示当前处理器所支持的不同模块化指令集。riscv架构文档规定 `misa` 寄存器可读可写，从而允许处理器可以动态的配置某些特性。`misa.v` 表示 Vector 扩展指令集域，即使 `misa.v` 域被清0，`mstatus.vs` 域也存在。这样设计可以简化 `mstatus.vs` 的处理。

### mstatus: Vector上下文状态

在mstatus[10:9]中添加了一个向量上下文状态字段VS，并在sstatus[10:9]中进行了镜像。它的定义与浮点上下文状态字段FS类似。

当mstatus.VS设置为Off时，尝试执行任何向量指令或访问向量CSRs都会引发非法指令异常。

当mstatus.VS设置为Initial或Clean时，执行任何改变向量状态的指令，包括向量CSRs，都将把mstatus.VS更改为Dirty。实现也可以在向量状态没有改变的情况下随时将mstatus.VS从Initial或Clean更改为Dirty。

> **<font color='red'>准确设置mstatus.VS是一种优化方法。软件通常会使用VS来减少上下文切换的开销。</font>**

如果mstatus.VS是脏的，那么mstatus.SD为1；否则，mstatus.SD根据现有规范进行设置。

实现可能具有可写的misa.V字段。类似于对浮点单元的处理方式，即使misa.V被清除，mstatus.VS字段仍然可能存在。

> 在misa.V未设置的情况下，允许存在mstatus.VS，可以实现向量仿真，并简化对于具有可写misa.V的系统中mstatus.VS的处理。

### vsstatus: Vector上下文状态

当存在虚拟机扩展时，向vsstatus[10:9]添加一个向量上下文状态字段VS。它的定义类似于浮点上下文状态字段FS。

* 当V=1时，vsstatus.VS和mstatus.VS都生效：当任一字段设置为Off时，执行任何向量指令或访问向量CSRs都会引发非法指令异常。
* 当V=1且vsstatus.VS和mstatus.VS都未设置为Off时，执行任何改变向量状态的指令，包括向量CSRs，都会将mstatus.VS和vsstatus.VS都改为Dirty。即使向量状态没有改变，实现也可以随时将mstatus.VS或vsstatus.VS从Initial或Clean更改为Dirty。
* 如果vsstatus.VS为Dirty，则vsstatus.SD为1；否则，根据现有规范设置vsstatus.SD。
* 如果mstatus.VS为Dirty，则mstatus.SD为1；否则，根据现有规范设置mstatus.SD。
* 对于具有可写的misa.V字段的实现，即使misa.V被清除，vsstatus.VS字段也可能存在。

### vstart: Vector Start Index CSR

XLEN位宽的可读写vstart CSR指定了向量指令执行的第一个元素的索引，如第Prestart、Active、Inactive、Body和Tail元素定义部分所述。

通常情况下，vstart只在向量指令发生陷阱时由硬件进行写入，vstart的值表示陷阱发生的元素（可以是同步异常或异步中断），并且在可恢复陷阱处理后应该从该元素处恢复执行。

所有的向量指令都被定义为从vstart CSR所给出的元素编号开始执行，不会改变目标向量中较早的元素，并且在执行结束时将vstart CSR重置为零。

>***关于元素的定义：***
>
>向量指令执行期间的元素索引，可以分成四个没有交集的子集。
>
>* `prestart elememts`：元素索引小于vstart寄存器中的初始值，对应的元素集合。该元素集合不产生异常，也不会更新目的向量寄存器；
>* `active elements`：表示在向量指令执行过程中，在向量长度设置范围内，且掩码有效的元素集合。该元素集合可以产生异常并且也可以更新目的向量寄存器；
>* `inactive elements`：表示在向量指令执行过程中，在向量长度设置范围内，但是掩码无效的严肃集合。该元素集合不产生异常，vma=0的设置下，不更新目的向量寄存器；vma=1的设置下，被掩码掩蔽的元素将被写1；
>* `tail elemememts`：表示在向量执行过程中，超过了向量设置的长度。该元素集合不产生异常，vta=0的设置下，不更新目的向量寄存器；vta=1的设置下，tail元素将被写1。当分组因子LMUL<1时，超过LMAX的元素也纳入tail元素集合中。
>
>除上述定义的子集外。inactive和active的集合还可以统称body element。该集合在prestart elements之后，在tail elements之前。

vstart为可读可写寄存器，该寄存器规定了一条向量指令中第一个被执行的元素的索引。

vstart寄存器通常在向量指令执行的过程中产生了陷阱被写入。该寄存器记录了进入陷阱时向量指令操作元素的索引，以便跳出陷阱之后能够继续执行剩下的元素。 所有向量指令都根据vstart中指定的元素索引开始执行。执行的过程保证该索引之前的目的寄存器的元素不被干扰，在执行的末尾，将vstart寄存器的值复位到0。当向量指令产生非法指令异常时，vstart寄存器将不会被改写。所以vstart寄存器被改写，只能是程序执行时出现了可恢复的同步异常，或者外部产生中断的情况。

**思考：**假如不能通过vstart存储异常时的元素索引，那么在执行向量指令过程中发生的可恢复异常，必须要等到这条向量指令执行完，才能进入异常处理程序。这就要求向量指令必须是原子的，增加了控制复杂度，并且对于一些长延时的指令，比如load，将会导致响应中断的时间特别的长。

若vstart索引值大于vl的值，说明vstart指向的元素索引已经超过了当前所有元素的范围，该指令不会执行，并且同时会把vstart寄存器复位到0。
vstart可写的bit位，根据VLMAX确定，在vl部分已经描述过。

### Exception Handling

在矢量指令的陷阱中（由同步异常或异步中断引起），现有的 `*epc` CSR会被写入指向陷阱矢量指令的指针，而 `vstart` CSR则包含陷阱发生时的元素索引。

>我们选择添加vstart CSR以允许恢复部分执行的向量指令，以减少中断延迟并简化前进保证。这类似于IBM 3090向量设施中的方案。为了确保没有vstart CSR的前进进展，实现必须保证整个向量指令始终可以原子地完成而不生成陷阱。在存在跨步或分散/聚集操作和需求分页虚拟内存的情况下，这特别难以保证。

异常和中断从广义上来看，都叫做异常。RISC-V 架构规定，在处理器的程序执行过程中，一旦遇到异常发生，则终止当前的程序流，处理器被强行跳转到一个新的 PC 地址。该过程在 RISC-V 的架构中定义为“陷阱(trap)”， 字面含义为“跳入陷阱”，更加准确的意译为“进入异常”。在一条向量指令执行的过程中遇到了陷阱，需要将当前指令pc保存在 `*epc` 中，并且需要记录当前遇到异常时的元素索引到 vstart，以便退出异常服务程序后能恢复原先执行的程序。

如果发生异常时，只记录指令的pc指针，没有用vstart记录发生异常时的元素索引，那么需要保证该指令的执行是原子的，这加大了设计控制难度。并且向量指令设计为原子的，在有些long latency的指令执行过程中，会导致中断的响应非常缓慢。(思考假如指令不是原子的，那么出现异常直接被打断，又没有保存被打断时的索引，那么下一次从这一条指令重新开始执行会有什么问题？)

中断通常是由外设（中断源）产生的，而异常通常是由程序执行过程中遇到的异常。

* 因此中断是一种外因，通常不能精确定位到某条指令引起，因为外设发起中断的时间是偶然的，程序执行过程中遇到中断，任何指令都可能碰到，这些倒霉的指令只是一个背锅侠，因此称这种中断为异步异常；
* 异常的产生通常是内因，比如某条指令解码的时候出错，或者执行的时候进行了除 0 的操作，这些异常都可以被精确的定位到某一条指令。并且同样的程序执行n遍，都是能复现的。因此称这种异常为同步异常。

---

对于异步异常，还可以被细分为**精确异步异常和非精确异步异常。**精确和不精确的区分主要在于进入异常的程序能否精确区分到某条指令的边界

* 比如某条指令之前的指令都执行完了，而该条指令之后的指令都没有执行，外部中断就是一种精确异步异常。
* 而非精确异步异常是指当前处理器的状态可能是一个很模糊的状态，没法明确的根据一条指令划界。举个例子，比如写存指令，访问存储器需要一定的时间，但是为了流水线高效率的执行，通常写存指令发出去，没等到写的响应有没有正确响应，后续的指令就在继续执行。那么有可能出现等访问完成，发现出现了异常，此时已经过去了很多条指令了，难以精准确的定位到某一条指令。

异常可能发生在处理器流水线的各个阶段，为了保证处理器按照指令先后顺序处理异常，需要将异常的处理放在 `commit` 阶段。

#### Precise vector traps

> 我们假设大多数具有需求分页的监管模式环境都需要精确的向量陷阱。

精确的向量陷阱具有如下要求：

* 所有比陷阱指令旧的指令都已经完成了 `commit` 过程；
* 所有比陷阱指令新的指令都应该被flush掉，不允许新指令更改处理器的状态；
* 陷阱指令中，所有小于vstart元素索引的元素操作都完成了 `commit`；
* 陷阱指令中，所有大于等于vstart元素索引的元素都不会被执行。但是如果操作重新开始该指令，可以将处理器恢复到正确的状态，那么该条约束可以放松；

举个例子，对于具有幂等性的存储区域进行操作，就可以允许发生trap对应的索引之后的元素改变存储器的状态，而不具有幂等性的存储区域就不能允许大于等于vsart索引的元素更新存储器状态。

> 幂等性是指多次执行一个操作与执行一次该操作得到的结果相同，该操作就可以说是幂等的。

跳出异常服务程序时，需要从vstart记录的元素索引开始。这是因为比如有些指令源寄存器与目的寄存器有交叠，那么可能vstart之前的源寄存器内容已经被目的寄存器覆盖了，那么重新执行这部分元素，将会得到错误的结果。

#### Imprecise vector traps

非精确向量陷阱，spec中写的是比 `*epc` 新的指令可能已经commit，比 `*epc` 老的指令有可能还在执行。对这个地方我是有疑问的，因为即使是超标量流水线，也会经历一个inorder-outoforder-inorder的过程，也就是真正commit的时候，指令肯定是会按照程序指令顺序，依次改变处理器状态，怎么会出现比 `*epc` 老的指令还在执行。鉴于这部分理解的有分叉，我就不多描述了，希望能和大家一起讨论清楚。



## //TODO: 1.2 ARM Scalable Vector Extension



# 2 RISC-V Vector内核支持

[[PATCH v10 00/16\] riscv: Add vector ISA support - Greentime Hu (kernel.org)](https://lore.kernel.org/all/cover.1652257230.git.greentime.hu@sifive.com/)

[[v6, 00/10\] riscv: support kernel-mode Vector - Andy Chiu](https://lore.kernel.org/all/20231220075412.24084-1-andy.chiu@sifive.com/)

该补丁集是基于向量1.0规范实现的，以在riscv Linux内核中添加向量支持。对于这些实现，有一些假设。
1. 我们假设系统中的所有harts都具有相同的ISA。
2. 我们在某些方面使用类似浮点单元(FPU)的向量，而不是使用特定IP的向量。
3. 默认情况下，在内核空间中禁用向量，除非内核使用内核模式的向量kernel_rvv_begin()/kernel_rvv_end()。
4. 我们通过检测"riscv,isa"来确定是否支持向量。

我们在struct thread_struct中定义了一个名为 `__riscv_v_state` 的新结构，用于保存/恢复与向量相关的寄存器。它用于内核空间和用户空间。

* 在内核空间中，`__riscv_v_state` 中的datap指针将被分配用于保存向量寄存器；
* 在用户空间中：
  * 在用户空间的信号处理程序中，datap将指向 `__riscv_v_state` 数据结构的地址，以在堆栈中保存向量寄存器。我们还为未来的扩展在sigcontext中创建了一个 `reserved[]` 数组；
  * 在ptrace中，数据将被放入ubuf中，我们使用 `riscv_vr_get()/riscv_vr_set()` 从中获取或设置 `__riscv_v_state` 数据结构，datap指针将被清零，并且向量寄存器将被复制到riscv_v_state结构之后的地址中。

该补丁集还添加了对内核模式向量的支持，使用向量ISA实现了内核XOR，并包括了几个错误修复和代码优化。

该补丁集已重新基于v5.18-rc6，并通过同时运行多个向量程序进行了测试。它还可以在信号处理程序中获取正确的ucontext_t，并在sigreturn后恢复正确的上下文。它还经过了使用ptrace()系统调用来使用PTRACE_GETREGSET/PTRACE_SETREGSET获取/设置向量寄存器的测试。

待办事项：

1. 优化start_thread()中的 `__riscv_v_state` 分配；
2. 通过延迟保存/恢复来优化向量上下文切换函数；
3. 添加AMP支持，以支持具有不同ISA的harts。

---

## 2.1 Lazy save/restore

[[PATCH -next v21 00/27\] riscv: Add vector ISA support - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230605110724.21391-1-andy.chiu@sifive.com/)

### non-virtualization

```c
static inline void riscv_v_vstate_off(struct pt_regs *regs)
{
	regs->status = (regs->status & ~SR_VS) | SR_VS_OFF;
}

static struct linux_binfmt elf_format = {
	.module		= THIS_MODULE,
	.load_binary	= load_elf_binary,
	.load_shlib	= load_elf_library,
#ifdef CONFIG_COREDUMP
	.core_dump	= elf_core_dump,
	.min_coredump	= ELF_EXEC_PAGESIZE,
#endif
};

/*
kernel_entry*
 start_kernel
    setup_arch*
     trap_init*
        mm_init
            mem_init*
        init_IRQ*
        time_init*
        rest_init
            kernel_thread
            kernel_thread
            cpu_startup_entry
*/

do_execve
	+-> load_elf_binary
		+->begin_new_exec
			+-> flush_thread
				+-> riscv_v_vstate_off

    
```

内核中实际执行execv()或execve()系统调用的程序是 `do_execve()`，这个函数先打开目标映像文件，并从目标文件的头部（第一个字节开始）读入若干（当前Linux内核中是128）字节（实际上就是填充ELF文件头），然后调用另一个函数 `search_binary_handler()`，在此函数里面，它会搜索我们上面提到的Linux支持的可执行文件类型队列，让各种可执行程序的处理程序前来认领和处理。如果类型匹配，则调用 `load_binary` 函数指针所指向的处理函数来处理目标映像文件。在ELF文件格式中，处理函数是`load_elf_binary` 函数。

---

#### vector trap处理

[PATCH -next v21 11/27\] riscv: Allocate user's vector context in the first-use trap - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230605110724.21391-12-andy.chiu@sifive.com/)

vector对于所有用户进程默认情况下是禁用的。因此，当一个进程首次进行vector操作时，将触发非法指令异常，陷入内核。之后，内核为该用户进程分配一个vector_context，并开始管理该上下文。

```c
+asmlinkage __visible __trap_section void do_trap_insn_illegal(struct pt_regs *regs)
+{
+	if (user_mode(regs)) {
+		irqentry_enter_from_user_mode(regs);
+
+		local_irq_enable();
+
+		if (!riscv_v_first_use_handler(regs))
+			do_trap_error(regs, SIGILL, ILL_ILLOPC, regs->epc,
+				      "Oops - illegal instruction");
+
+		irqentry_exit_to_user_mode(regs);
+	} else {
+		irqentry_state_t state = irqentry_nmi_enter(regs);
+
+		do_trap_error(regs, SIGILL, ILL_ILLOPC, regs->epc,
+			      "Oops - illegal instruction");
+
+		irqentry_nmi_exit(regs, state);
+	}
+}

+bool riscv_v_first_use_handler(struct pt_regs *regs)
+{
+	u32 __user *epc = (u32 __user *)regs->epc;
+	u32 insn = (u32)regs->badaddr;
+
+	/* Do not handle if V is not supported, or disabled */
+	if (!(ELF_HWCAP & COMPAT_HWCAP_ISA_V))
+		return false;
+
+	/* If V has been enabled then it is not the first-use trap */
+	if (riscv_v_vstate_query(regs))
+		return false;
+
+	/* Get the instruction */
+	if (!insn) {
+		if (__get_user(insn, epc))
+			return false;
+	}
+
+	/* Filter out non-V instructions */
+	if (!insn_is_vector(insn))
+		return false;
+
+	/* Sanity check. datap should be null by the time of the first-use trap */
+	WARN_ON(current->thread.vstate.datap);
+
+	/*
+	 * Now we sure that this is a V instruction. And it executes in the
+	 * context where VS has been off. So, try to allocate the user's V
+	 * context and resume execution.
+	 */
+	if (riscv_v_thread_zalloc()) {
+		force_sig(SIGBUS);
+		return true;
+	}
+	riscv_v_vstate_on(regs);
+	return true;
+}   
```

riscv_vector_spec 中：

> Accurate setting of `mstatus.VS` is an optimization. Software will typically use VS to reduce context-swap overhead.

内核启动默认关闭 `mstatus.VS`，用户态程序首次执行 vector 指令会触发Trap，这是一个非法指令异常。随后内核会判断该指令是否为vector指令以及是否首次执行，一切确定后则设置 `mstatus.VS = INITIAL` 并分配vector_context内存，返回用户态后程序就能正常执行vector指令了。

vector上下文的保存恢复函数为 `__switch_to_vector`，该函数就在常规的调度控制流中，且与常规的 `x0~x31` 寄存器保存/恢复流程解耦，分布在不同的函数中。内核将其称之为 “lazy store/restore”，在 `vector_store/restore` 函数中实际上存在对 `mstatus.VS` 的判断，这一举动**可以在用户态程序不用vector指令的情况下帮助内核降低上下文切换开销，**具体来说：

* 当 `mstatus.VS == OFF`时：内核不需要保存/恢复vector上下文，因为用户态程序根本没使用过这些vector寄存器组；
* 当 `mstatus.VS != OFF` 时：内核需要保存/恢复vector上下文，表示用户态程序使用了vector寄存器组；

`mstatus.VS` 提供了一种用户态程序通知内核的硬件机制，触发Trap时相当于告诉内核：“用户确实使用了vector，请内核使能必要的vector工作”。

---

#### 当前的Lazy还不够

为什么这么说，因为目前的实现在开启 `mstatus.VS` 之后vector_context的保存/恢复工作似乎无法阻拦了，那么在任何场景下都必须执行这些工作吗？并不是，具体见 `3.1`。

---

### virtualization

目前内核对 vector 虚拟化的支持不完善，主要体现在两方面：

* vector_contex的host/guest管理；
* guest侧vector_trap处理；

---

#### vector_context保存/恢复

[[PATCH -next v21 19/27\] riscv: KVM: Add vector lazy save/restore support - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230605110724.21391-20-andy.chiu@sifive.com/)

> 为区分不同的执行流，命名如下：
>
> 1. 宿主机内核态vcpu线程：vcpu_host_kernel
> 2. 宿主机用户态vcpu线程：vcpu_host_user
> 3. 虚拟机内核态vcpu线程：vcpu_guest_kernel
> 4. 虚拟机用户态vcpu线程：vcpu_guest_user

在虚拟化模型中，涉及CPU上下文保存恢复的场景有 ( `/` 左侧为需要保存到内存的执行流状态，右侧为需要恢复到CPU寄存器上的执行流状态)：

* host/guest world switch (vcpu线程进入退出)

  * 相关函数：`__kvm_riscv_switch_to/__kvm_switch_return`

  * `vcpu_host_kernel/vcpu_guest_kernel`

* host对vcpu线程的全局调度

  * 相关函数：`vcpu_load/vcpu_put`

  * 对两个vcpu线程的切换，如果被抢占的vcpu线程处于guest-Mode，除了做world switch外还需要做不同vcpu线程的上下文切换：
    * step_1：`vcpu_guest_kernel/vcpu_host_kernel`
    * step_2：`vcpu_host_kernel_prev/vcpu_host_kernel_next`
    * step_3：`vcpu_host_kernel/vcpu_guest_kernel`

* 退出到host user处理guest异常

  * 相关函数：`vcpu_load/vcpu_put`

  * 先做world switch，再做trap return：
    * step_1：`vcpu_guest_kernel/vcpu_host_kernel`
    * step_2：`vcpu_host_kernel/vcpu_host_user`

---

https://elixir.bootlin.com/linux/v6.7-rc6/C/ident/kvm_arch_vcpu_load

https://elixir.bootlin.com/linux/v6.7-rc6/C/ident/kvm_arch_vcpu_put

```c
kvm_arch_vcpu_load
    +-> kvm_riscv_vcpu_host_fp_save(&vcpu->arch.host_context);
	+-> kvm_riscv_vcpu_guest_fp_restore(&vcpu->arch.guest_context, vcpu->arch.isa);
	+-> kvm_riscv_vcpu_host_vector_save(&vcpu->arch.host_context);
	+-> kvm_riscv_vcpu_guest_vector_restore(&vcpu->arch.guest_context, vcpu->arch.isa);

kvm_arch_vcpu_put
    +-> kvm_riscv_vcpu_guest_fp_save(&vcpu->arch.guest_context, vcpu->arch.isa);
	+-> kvm_riscv_vcpu_host_fp_restore(&vcpu->arch.host_context);
	+-> kvm_riscv_vcpu_guest_vector_save(&vcpu->arch.guest_context, vcpu->arch.isa);
	+-> kvm_riscv_vcpu_host_vector_restore(&vcpu->arch.host_context);
```

存在的缺陷：

* 对于 `kvm_arch_vcpu_load`：

  * `kvm_riscv_vcpu_host_fp_save/kvm_riscv_vcpu_host_vector_save`

    仅检查是否支持f扩展，就直接保存host状态 => 考虑guest对fp/vector的使用情况，应该延迟保存

  * `kvm_riscv_vcpu_guest_fp_restore/kvm_riscv_vcpu_guest_vector_restore`

    仅检查 `vsstatus.FS != SR_FS_OFF` 和 `vsstatus.VS != SR_VS_OFF `，说明guest已允许float/vector指令的执行，直接恢复guest状态

    * 如果条件判断为guest禁用了float/vector_trap，恢复其上下文完全没有问题；但考虑这样一种情况：host没使用过float/vector指令，当前pCPU的float/vector寄存器仅为guest所用，guest此时完全不需要执行本次恢复工作。
    * 如果条件判断为guest启用了float/vector_trap，那么之前的host状态完全没必须要保存；

  >  put 操作同理

#### guest发生vector_trap处理











## 2.2 *Delayed update strategy

### non-virtualization

> 见3.1



### virtualization

* [switch.h - arch/arm64/kvm/hyp/include/hyp/switch.h - Linux source code (v6.7-rc6) - Bootlin](https://elixir.bootlin.com/linux/v6.7-rc6/source/arch/arm64/kvm/hyp/include/hyp/switch.h#L299)
* https://elixir.bootlin.com/linux/v6.7-rc6/C/ident/FP_STATE_GUEST_OWNED







# 3 ARMv8 FPSIMD/SVE内核支持

## 3.1 Linux-ARM引入的FPSIMD状态跟踪机制

[fpsimd.c - arch/arm64/kernel/fpsimd.c - Linux source code (v6.7-rc6) - Bootlin](https://elixir.bootlin.com/linux/v6.7-rc6/source/arch/arm64/kernel/fpsimd.c)

（注意：在本讨论中，关于FPSIMD的陈述同样适用于SVE。）

为了减少不必要地保存和恢复FPSIMD状态的次数，我们需要跟踪两件事情：

* 对于每个任务，我们需要记住最后一个将任务的FPSIMD状态加载到其FPSIMD寄存器中的CPU是哪一个；
* 对于每个CPU，我们需要记住最近加载到其FPSIMD寄存器中的用户态FPSIMD状态属于哪个任务，或者在此期间是否已被用于执行内核模式NEON操作。

对于（a），我们向thread_struct添加了一个fpsimd_cpu字段，每当状态被加载到CPU上时，该字段会更新为当前CPU的ID。对于（b），我们添加了每个CPU的变量 `fpsimd_last_state`，其中包含最近加载到CPU上的任务的用户空间FPSIMD状态的地址，如果在此之后执行了内核模式NEON，则为NULL。

有了这个设置，我们在任务切换时就不再需要立即恢复下一个FPSIMD状态。相反，我们可以将这个检查推迟到用户空间的恢复阶段，在这个阶段我们验证CPU的 `fpsimd_last_state` 和任务的 `fpsimd_cpu` 是否仍然保持同步。如果是这种情况，我们可以省略FPSIMD的恢复操作。

作为一种优化，我们使用线程信息标志 `TIF_FOREIGN_FPSTATE` 来指示当前任务的用户态FPSIMD状态是否存在于寄存器中。除非当前CPU的FPSIMD寄存器当前包含当前任务的最新用户态FPSIMD状态，否则设置该标志。如果任务表现为虚拟机监视器（VMM），则由KVM管理，KVM将清除该标志以指示vcpu的FPSIMD状态当前加载在CPU上，以便在FPSIMD感知的软中断触发时保存状态。在vcpu_put()时，KVM将保存vcpu的FP状态并标记寄存器状态为无效。

为了允许softirq处理程序使用FPSIMD，`kernel_neon_begin()` 可能会在softirq上下文中将任务的FPSIMD上下文保存回task_struct。
为了防止这与任务上下文中的FPSIMD状态的操作竞争，并因此破坏状态，有必要使用 `{，__}get_cpu_fpsimd_context()` 保护对任务的fpsimd_state或TIF_FOREIGN_FPSTATE标志的任何操作。这仍将允许softirq运行，但防止它们使用FPSIMD。

对于某个任务，其序列可能如下所示：

* **任务被调度：**如果任务的fpsimd_cpu字段包含当前CPU的ID，且CPU的 `fpsimd_last_state` per-cpu变量指向任务的fpsimd_state，TIF_FOREIGN_FPSTATE标志位被清除，否则被设置；
* **任务返回到用户空间：**如果设置了TIF_FOREIGN_FPSTATE标志，任务的用户空间FPSIMD状态将从内存复制到寄存器中，任务的fpsimd_cpu字段将设置为当前CPU的ID，当前CPU的 `fpsimd_last_state` 指针将设置为该任务的fpsimd_state，并清除TIF_FOREIGN_FPSTATE标志；
* **该任务执行一个普通的系统调用：**当返回到用户空间时，TIF_FOREIGN_FPSTATE标志仍将被清除，因此不会恢复FPSIMD状态；
* **该任务执行一个系统调用，该系统调用执行一些NEON指令：**在此之前，调用 `kernel_neon_begin()` 函数，将任务的FPSIMD寄存器内容复制到内存中，清除fpsimd_last_state每CPU变量，并设置TIF_FOREIGN_FPSTATE标志；
* **在调用kernel_neon_end()之后，任务被抢占：**由于我们还没有从第二个系统调用中返回，TIF_FOREIGN_FPSTATE仍然被设置，因此FPSIMD寄存器中的内容不会被保存到内存中，而是被丢弃。

---



![fpsimd_reduce_switch_times.drawio](https://cdn.jsdelivr.net/gh/MaskerDad/BlogImage@main/202312201753572.png)



1. **task0首次被调度：**

   > 判断是否保持同步
   > \* task0->fpsimd_cpu ?= pCPU0;
   > \* fpsimd_last_state ?= task0;
   > => 
   > TIF_FOREIGN_FPSTATE = true;

2) **task0返回用户态：**

   > \* 判断TIF_FOREIGN_FPSTATE，这里为TRUE，
   >   那就恢复FPSIMD状态到寄存器上；
   > \* task0->fpsimd_cpu = pCPU0;
   > \* fpsimd_last_state = task0;
   > \* TIF_FOREIGN_FPSTATE = false;

3. **task0在用户态主动或被动地让出CPU控制权：**

   > 注意：并不是被另一个task抢占，这种情况也比较常见，而且假设在task0等待期间pCPU0处于闲置状态，即pCPU0并没有装载其它task的上下文。

4. **task0再次被调度运行，目标CPU仍然为pCPU0：**

   > 还是判断和1）相同的两个变量，看是否同步，此时：
   > task0->fpsimd_cpu = pCPU0；
   > fpsimd_last_state = task0;
   > => TIF_FOREIGN_FPSTATE = false;

5) **task0再次返回用户态：**

   > task0再次被调度运行，目标CPU仍然为pCPU0：

## 3.2 针对虚拟化场景的优化

#### Linux KVM-ARM

##### PATCH

[[PATCH v5 0/8\] arm64/sve: Clean up KVM integration and optimise syscalls - Mark Brown (kernel.org)](https://lore.kernel.org/all/20221115094640.112848-1-broonie@kernel.org/)

该补丁系列试图澄清在支持SVE系统中跟踪哪组浮点寄存器的保存情况，特别是与KVM相关的情况，并利用这种澄清结果来提高用户空间使用SVE的简单系统调用的性能。

目前，我们通过为当前任务使用的TIF_SVE标志来跟踪活动的寄存器状态，该标志还控制用户空间是否能使用SVE，这在一定程度上是相对简单的，但对于KVM来说稍微复杂一些，因为我们可能在寄存器中加载了客户机状态。这导致KVM在客户机运行时修改VMM任务的TIF_SVE，这并没有完全有助于使事情易于理解。为了使事情更清晰，该系列对此进行了更改，除了TIF_SVE之外，我们还明确跟踪了当前保存在任务结构体中的寄存器类型以及在保存时应该保存的寄存器类型。

> 因此，TIF_SVE仅控制用户空间是否可以无需陷阱地使用SVE，对于KVM客户机而言，它没有功能，我们可以从KVM中删除管理它的代码。

通过添加单独的跟踪，重新设计的工作开始进行，同时还添加了在查看分离的状态之前对状态进行验证的检查。此举的目标是将重复性更高的部分拆分出来，并更容易调试可能出现的任何问题。

在单独跟踪状态后，我们开始优化使用SVE的系统调用的性能。目前，每个系统调用都会为用户空间禁用SVE，这意味着下一个SVE指令需要再次陷入EL1，刷新SVE寄存器，并为EL0重新启用SVE，从而为混合使用SVE和系统调用的任务创建了开销。借助上述的重新设计，我们通过在不需要从内存重新加载状态时保持SVE启用，来消除对直接返回用户空间的简单系统调用的开销，这意味着如果系统调用不阻塞，我们避免了下一次使用SVE时陷入EL1的开销。

该系列还包括一个相关的补丁，简化了 `fpsimd_bind_state_to_cpu()` 的接口，减少了该函数接受的大量参数。不管有没有这个系列的影响，这已经是一个问题，但该系列进一步放放大了这个问题，如果这种方法对大家都可以接受，我们可以在更多地方使用该结构体。为了避免用户可见的改进被代码清理所拖延，此补丁被放在最后。

---

[[PATCH v2 04/19\] KVM: arm64: Move FP state ownership from flag to a tristate - Marc Zyngier (kernel.org)](https://lore.kernel.org/all/20220610092838.1205755-5-maz@kernel.org/#r)

KVM FP代码使用一对标志来表示三种状态：

- 设置FP_ENABLED：客户机拥有FP状态
- 设置FP_HOST：主机拥有FP状态
- 清除FP_ENABLED和FP_HOST：没有任何人拥有FP状态

同时设置两个标志是非法状态，但没有任何地方会检查这种状态...

事实证明，这对标志并不是一个好的匹配方式，如果我们将其改为更简单的三态，并且每个状态都有一个实际反映状态的名称，那会更好：

- FP_STATE_FREE（空闲状态）
- FP_STATE_HOST_OWNED（主机拥有状态）
- FP_STATE_GUEST_OWNED（客户机拥有状态）

删除这两个标志，并改为使用枚举来表示这三种状态。这样可以减少令人困惑的代码，并减少忘记清除两个标志中的一个而导致进入未知领域的风险。

---

#### fpsimd/sve虚拟化框架分析

https://elixir.bootlin.com/linux/v6.7-rc7/C/ident/kvm_hyp_handle_fpsimd

在armv8中，fp和sve复用一套寄存器，可以看到在函数中针对sve的处理为：

```c
/* SVE exposed to guest */
#define GUEST_HAS_SVE		__vcpu_single_flag(cflags, BIT(0))

#define vcpu_has_sve(vcpu) (system_supports_sve() &&			\
			    vcpu_get_flag(vcpu, GUEST_HAS_SVE))

static bool kvm_hyp_handle_fpsimd(struct kvm_vcpu *vcpu, u64 *exit_code)
{
	bool sve_guest;
	u8 esr_ec;
	u64 reg;

	if (!system_supports_fpsimd())
		return false;

	sve_guest = vcpu_has_sve(vcpu);
	esr_ec = kvm_vcpu_trap_get_class(vcpu);

	/* Only handle traps the vCPU can support here: */
	switch (esr_ec) {
	case ESR_ELx_EC_FP_ASIMD:
		break;
	case ESR_ELx_EC_SVE:
		if (!sve_guest)
			return false;
		break;
	default:
		return false;
	}

	/* Valid trap.  Switch the context: */

	/* First disable enough traps to allow us to update the registers */

	/* Write out the host state if it's in the registers */
	if (vcpu->arch.fp_state == FP_STATE_HOST_OWNED)
		__fpsimd_save_state(vcpu->arch.host_fpsimd_state);

	/* Restore the guest state */
	if (sve_guest)
		__hyp_sve_restore_guest(vcpu);
	else
		__fpsimd_restore_state(&vcpu->arch.ctxt.fp_regs);

	vcpu->arch.fp_state = FP_STATE_GUEST_OWNED;

	return true;
}
```

可以看到，在arm中guest首次访问fp/sve被定义为不同类型的异常，因为当硬件支持SVE时fp/sve复用一套寄存器组，各自对恢复上下文的处理方式得到了统一：

* `ESR_ELx_EC_FP_ASIMD`
  * `sve_guest == true`：恢复至SVE寄存器组的低bit；
  * `sve_guest == false`：guest不支持sve，恢复至传统的fp_regs；
* `ESR_ELx_EC_SVE`
  * `sve_guest == true`：恢复至SVE寄存器组的完整bit；
  * `sve_guest == false`：Invalid Trap!!!

> 疑问：riscv支持vector扩展时，是否和fp复用一套寄存器？
>
> 这关系到vector_guest启用时，恢复哪些寄存器组，涉及到代码结构的设计。

---

```c
/* Check whether the FP regs are owned by the guest */
static inline bool guest_owns_fp_regs(struct kvm_vcpu *vcpu)
{
	return vcpu->arch.fp_state == FP_STATE_GUEST_OWNED;
}


```



---

![](C:/Users/26896/Desktop/%E8%B7%B3%E6%9D%BF%E6%9C%BA%E9%85%8D%E7%BD%AE.png)

```shell
Host tiaoban
    HostName isrc.iscas.ac.cn 
    Port 5022
     User USERNAME 
Host server 
    HostName SERVER_IP 
    Port 22 
    User SERVER_USERNAME 
    ProxyCommand ssh tiaoban -W %h:%p
    
192.168.16.208
zhouquan
ISRCpassword123
```

[使用xshell通过跳板机(堡垒机)连接服务器_堡垒机主机地址是怎么样的-CSDN博客](https://blog.csdn.net/sqlgao22/article/details/99570680)

[VSCode Remote ssh跳板机配置（windows平台） - 知乎 (zhihu.com)](https://zhuanlan.zhihu.com/p/103578899)







