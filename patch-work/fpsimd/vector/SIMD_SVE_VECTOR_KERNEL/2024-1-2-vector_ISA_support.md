---
Stitle: vector_ISA_support

date: 2024-1-2 17:00:00 +0800

categories: [SIMD内核支持]

tags: [vector]

description: 
---

# 0 参考

* [vector-isa-support]([[PATCH -next v20 00/26\] riscv: Add vector ISA support - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-1-andy.chiu@sifive.com/))

* [vector-1.0-spec]([riscv/riscv-v-spec: Working draft of the proposed RISC-V V vector extension (github.com)](https://github.com/riscv/riscv-v-spec))
* [vector-1.0解读]([【个人笔记】RISC-V "V" Vector Extension Version 1.0 - 知乎 (zhihu.com)](https://zhuanlan.zhihu.com/p/674158689))



# 1 背景

[[PATCH -next v21 00/27\] riscv: Add vector ISA support - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230605110724.21391-1-andy.chiu@sifive.com/)在这个实现中，有一些假设：

1. 我们假设系统中的所有harts都具有相同的ISA。
2. 默认情况下，我们在内核和用户空间中禁用向量。只有在一个非法指令陷阱（第一次使用陷阱）中，实际开始执行向量后，才启用用户的向量。
3. 我们检测 "riscv,isa" 来确定是否支持向量。

我们在结构体 `thread_struct` 中定义了一个新的结构体 `__riscv_v_ext_state`，用于保存/恢复与向量相关的寄存器。它用于内核空间和用户空间。
 - 在内核空间中，`__riscv_v_ext_state` 中的 datap 指针将被分配用于保存向量寄存器。
 - 在用户空间中：
	- 在用户空间的信号处理器中，该结构体位于 `__riscv_ctx_hdr` 之后，该结构体嵌入在fp保留区域中。这是为了避免ABI中断。并且datap指向 `__riscv_v_ext_state` 的末尾。
	- 在ptrace中，数据将被放入ubuf中，我们使用 `riscv_vr_get()/riscv_vr_set()` 从ubuf中获取或设置 `__riscv_v_ext_state` 数据结构，datap指针将被清零，向量寄存器将被复制到ubuf中 `__riscv_v_ext_state` 结构体后的地址。

---

重点关注以下几点：

* vector的Trap处理
* vector的上下文保存与恢复

# 2 解析

## 2.1 vector_trap

### ISA

![img](https://pic2.zhimg.com/v2-e7e8927ab88d08fdf59e5c6d7fdf3529_b.jpg)

>* `mstatus/sstatus`
>
>A vector context status field, `VS`, is added to `mstatus[10:9]` and shadowed in `sstatus[10:9]`. It is defined analogously to the floating-point context status field, `FS`.
>
><font color='red'>**Attempts to execute any vector instruction, or to access the vector CSRs, raise an illegal-instruction exception when `mstatus.VS` is set to Off.**</font>
>
>When `mstatus.VS` is set to Initial or Clean, executing any instruction that changes vector state, including the vector CSRs, will change `mstatus.VS` to Dirty. Implementations may also change `mstatus.VS` from Initial or Clean to Dirty at any time, even when there is no change in vector state.
>
>* `vsstatus`
>
>When the hypervisor extension is present, a vector context status field, `VS`, is added to `vsstatus[10:9]`. It is defined analogously to the floating-point context status field, `FS`.
>
>**<font color='red'>When V=1, both `vsstatus.VS` and `mstatus.VS` are in effect: attempts to execute any vector instruction, or to access the vector CSRs, raise an illegal-instruction exception when either field is set to Off.</font>**
>
>When V=1 and neither `vsstatus.VS` nor `mstatus.VS` is set to Off, executing any instruction that changes vector state, including the vector CSRs, will change both `mstatus.VS` and `vsstatus.VS` to Dirty. Implementations may also change `mstatus.VS` or `vsstatus.VS` from Initial or Clean to Dirty at any time, even when there is no change in vector state.
>
>If `vsstatus.VS` is Dirty, `vsstatus.SD` is 1; otherwise, `vsstatus.SD` is set in accordance with existing specifications.
>
>If `mstatus.VS` is Dirty, `mstatus.SD` is 1; otherwise, `mstatus.SD` is set in accordance with existing specifications.
>
>For implementations with a writable `misa.V` field, the `vsstatus.VS` field may exist even if `misa.V` is clear.

---

### fpsimd_state

```c
union __riscv_fp_state {
	struct __riscv_f_ext_state f;
	struct __riscv_d_ext_state d;
	struct __riscv_q_ext_state q;
};

struct __riscv_v_ext_state {
	unsigned long vstart;
	unsigned long vl;
	unsigned long vtype;
	unsigned long vcsr;
	unsigned long vlenb;
	void *datap;
	/*
	 * In signal handler, datap will be set a correct user stack offset
	 * and vector registers will be copied to the address of datap
	 * pointer.
	 */
};
```

考虑到 `vector_context` 的大小可能变化且可能很大，它们被保存在动态分配的内存中，由`__riscv_v_ext_state` 中的datap指针指向。

### trap_control/handle

流程如下：

* 系统启动，主/从核拉起时，设置fpsimd为OFF状态；

  ```c
  SYM_CODE_START(_start_kernel)
      /*
  	 * Disable FPU & VECTOR to detect illegal usage of
  	 * floating point or vector in kernel space
  	 */
  	li t0, SR_FS_VS
  	csrc CSR_STATUS, t0
  #ifdef CONFIG_SMP
  	.global secondary_start_sbi
  secondary_start_sbi:
  	/*
  	 * Disable FPU & VECTOR to detect illegal usage of
  	 * floating point or vector in kernel space
  	 */
  	li t0, SR_FS_VS
  	csrc CSR_STATUS, t0
  ```

* 进程在用户态首次执行fpsimd指令，陷入处理并返回：

  向量单元默认情况下对所有用户进程都是禁用的。因此当进程首次使用向量时，它会因非法指令而陷入内核。只有在那之后，内核才会为该用户进程分配vector上下文，并开始管理该上下文。

  ```c
  static int riscv_v_thread_zalloc(void)
  {
  	void *datap;
  
  	datap = kzalloc(riscv_v_vsize, GFP_KERNEL);
  	if (!datap)
  		return -ENOMEM;
  
  	current->thread.vstate.datap = datap;
  	memset(&current->thread.vstate, 0, offsetof(struct __riscv_v_ext_state,
  						    datap));
  	return 0;
  }
  
  bool riscv_v_first_use_handler(struct pt_regs *regs)
  {
  	u32 __user *epc = (u32 __user *)regs->epc;
  	u32 insn = (u32)regs->badaddr;
  
  	/* Do not handle if V is not supported, or disabled */
  	if (!(ELF_HWCAP & COMPAT_HWCAP_ISA_V))
  		return false;
  
  	/* If V has been enabled then it is not the first-use trap */
  	if (riscv_v_vstate_query(regs))
  		return false;
  
  	/* Get the instruction */
  	if (!insn) {
  		if (__get_user(insn, epc))
  			return false;
  	}
  
  	/* Filter out non-V instructions */
  	if (!insn_is_vector(insn))
  		return false;
  
  	/* Sanity check. datap should be null by the time of the first-use trap */
  	WARN_ON(current->thread.vstate.datap);
  
  	/*
  	 * Now we sure that this is a V instruction. And it executes in the
  	 * context where VS has been off. So, try to allocate the user's V
  	 * context and resume execution.
  	 */
  	if (riscv_v_thread_zalloc()) {
  		force_sig(SIGBUS);
  		return true;
  	}
  	riscv_v_vstate_on(regs);
  	riscv_v_vstate_restore(current, regs);
  	return true;
  }
  ```

  用户态首次vector_trap将分配实际内存，用于保存/恢复vector上下文，返回用户态之前将 `sstatus.VS` 设置为Initial。之后用户态将正常使用vector。

## 2.2 vector_context_switch

相较于通用寄存器组，vector上下文更庞大。因此在大量使用vector的场景中，需要尽可能的避免vector上下文的保存/恢复，降低系统开销。在多核多进程系统中，内核需要跟踪比对 `task - cpu` 的 (绑定指向) 状态以确定某一次的vector上下文的保存/恢复上是否 “真的有必要”。先看一下目前内核在该问题的处理方式。

### kernel: context_save/restore

```c
static inline void riscv_v_vstate_save(struct task_struct *task,
				       struct pt_regs *regs)
{
	if ((regs->status & SR_VS) == SR_VS_DIRTY) {
		struct __riscv_v_ext_state *vstate = &task->thread.vstate;

		__riscv_v_vstate_save(vstate, vstate->datap);
		__riscv_v_vstate_clean(regs);
	}
}

static inline void riscv_v_vstate_restore(struct task_struct *task,
					  struct pt_regs *regs)
{
	if ((regs->status & SR_VS) != SR_VS_OFF) {
		struct __riscv_v_ext_state *vstate = &task->thread.vstate;

		__riscv_v_vstate_restore(vstate, vstate->datap);
		__riscv_v_vstate_clean(regs);
	}
}

static inline void __switch_to_vector(struct task_struct *prev,
				      struct task_struct *next)
{
	struct pt_regs *regs;

	regs = task_pt_regs(prev);
	riscv_v_vstate_save(prev, regs);
	riscv_v_vstate_restore(next, task_pt_regs(next));
}
```

`vector-1.0-spec` 中有一句注释：

> Accurate setting of `mstatus.VS` is an optimization. Software will typically use VS to reduce context-swap overhead.

内核中也确实这么做了，这是硬件的优化机制：

* vector上下文如果为DIRTY状态，保存的时候就必须去硬件上拉取最新的内容，否则就不需要做任何工作；
* vector上下文如果为OFF状态，恢复的时候就无需做任何工作，否则就必须恢复vector上下文状态；

---

内核最近提了一组[PATCH](https://lore.kernel.org/linux-riscv/20240108035209.GA212605@sol.localdomain/T/#mda836061caf7a5db9b6994a58ec8e32721ae5038)，考虑了这样一种调度场景：

>用户只有在内核真正返回到用户空间后才会使用其向量寄存器。因此，只要我们还在内核模式下运行，可以延迟恢复向量寄存器。内核需要添加一个线程标志以指示是否需要恢复向量，并在最后的特定于架构的退出用户模式的临界点处进行恢复。这样可以节省在内核模式下切换多个运行V操作的进程时的上下文恢复开销。
>
>举个例子：如果内核执行 `A->B->C` 的上下文切换，并最终返回到 C 的用户空间，那么就没有必要恢复 B 的vector寄存器。
>
>此外，这还可以防止我们在多次执行内核模式的向量操作时重复恢复vector上下文。这样做的代价是，在执行 `vstate_{save,restore}` 期间我们必须禁用抢占并将向量标记为忙碌。因为如果在 `vstate_{save,restore}` 过程中发生导致陷阱的上下文切换，vector上下文将不会立即恢复。

![image-20240110162607218](https://cdn.jsdelivr.net/gh/MaskerDad/BlogImage@main/202401101626365.png)

```c
riscv_v_first_use_handler
    +-> riscv_v_vstate_set_restore
__switch_to_vector
    +-> riscv_v_vstate_set_restore

#define TIF_RISCV_V_DEFER_RESTORE	12 /* restore Vector before returing to user */
#define _TIF_RISCV_V_DEFER_RESTORE	(1 << TIF_RISCV_V_DEFER_RESTORE)

static inline void riscv_v_vstate_set_restore(struct task_struct *task, struct pt_regs *regs)
{
	if ((regs->status & SR_VS) != SR_VS_OFF) {
		set_tsk_thread_flag(task, TIF_RISCV_V_DEFER_RESTORE);
		riscv_v_vstate_on(regs);
	}
}

+static inline void arch_exit_to_user_mode_prepare(struct pt_regs *regs,
+						  unsigned long ti_work)
+{
+	if (ti_work & _TIF_RISCV_V_DEFER_RESTORE) {
+		clear_thread_flag(TIF_RISCV_V_DEFER_RESTORE);
+		/*
+		 * We are already called with irq disabled, so go without
+		 * keeping track of riscv_v_flags.
+		 */
+		riscv_v_vstate_restore(current, regs);
+	}
+}
+
+#define arch_exit_to_user_mode_prepare arch_exit_to_user_mode_prepare
```

总体来说，将vector恢复工作推迟到返回用户态的节点，有两个优势：

* S-Mode下无论发生了多少次抢占，内核只关注返回用户态的那个task，中间的多个 `task_vector_context` 没必要恢复；
* S-Mode下也可能会使用vector，这种情况下会覆盖掉用户态的vector上下文，内核必须在使用vector前保存用户态vector上下文，在使用vector结束时恢复。但S-Mode有可能多次执行向量操作时，内核没必要重复恢复vector上下文，因此也是标记一个 `REFER_RESTORE`，一并推迟到返回用户态的节点；

### kvm: context_save/restore

[KVM: Add vector lazy save/restore support](https://lore.kernel.org/all/20230518161949.11203-20-andy.chiu@sifive.com/)

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

kvm_arch_vcpu_load(vcpu);
while(ret > 0) {
    //...
    __guest_enter();
    //...
    ret = handle_exit(vcpu);
}
kvm_arch_vcpu_put(vcpu);

void kvm_riscv_vcpu_guest_vector_save(struct kvm_cpu_context *cntx,
				      unsigned long *isa)
{
	if ((cntx->sstatus & SR_VS) == SR_VS_DIRTY) {
		if (riscv_isa_extension_available(isa, v))
			__kvm_riscv_vector_save(cntx);
		kvm_riscv_vcpu_vector_clean(cntx);
	}
}

void kvm_riscv_vcpu_guest_vector_restore(struct kvm_cpu_context *cntx,
					 unsigned long *isa)
{
	if ((cntx->sstatus & SR_VS) != SR_VS_OFF) {
		if (riscv_isa_extension_available(isa, v))
			__kvm_riscv_vector_restore(cntx);
		kvm_riscv_vcpu_vector_clean(cntx);
	}
}

void kvm_riscv_vcpu_host_vector_save(struct kvm_cpu_context *cntx)
{
	/* No need to check host sstatus as it can be modified outside */
	if (riscv_isa_extension_available(NULL, v))
		__kvm_riscv_vector_save(cntx);
}

void kvm_riscv_vcpu_host_vector_restore(struct kvm_cpu_context *cntx)
{
	if (riscv_isa_extension_available(NULL, v))
		__kvm_riscv_vector_restore(cntx);
}
```

存在的缺陷：

* 对于 `kvm_arch_vcpu_load`：

  * `kvm_riscv_vcpu_host_fp_save/kvm_riscv_vcpu_host_vector_save`

    仅检查是否支持f扩展，就直接保存host状态 => 考虑guest对fp/vector的使用情况，应该延迟保存

  * `kvm_riscv_vcpu_guest_fp_restore/kvm_riscv_vcpu_guest_vector_restore`

    仅检查 `vsstatus.FS != SR_FS_OFF` 和 `vsstatus.VS != SR_VS_OFF `，说明guest已允许float/vector指令的执行，直接恢复guest状态

    * 如果条件判断为guest禁用了float/vector_trap，恢复其上下文完全没有问题；但考虑这样一种情况：host没使用过float/vector指令，当前pCPU的float/vector寄存器仅为guest所用，guest此时完全不需要执行本次恢复工作。
    * 如果条件判断为guest启用了float/vector_trap，那么之前的host状态完全没必须要保存；
