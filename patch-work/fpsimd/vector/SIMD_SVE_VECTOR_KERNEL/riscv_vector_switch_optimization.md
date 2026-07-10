# -1 问题





# 0 规划

- [ ] 梳理TIF_FOREIGN_FPSTATE相关的，函数调用链路



# 1 kernel/kvm-riscv

* spec
  * [riscv-v-spec/v-spec.adoc at master · riscv/riscv-v-spec (github.com)](https://github.com/riscv/riscv-v-spec/blob/master/v-spec.adoc#vector-context-status-in-mstatus)
  * riscv-privileged-spec：3.1.6.6 Extension Context Status in mstatus Register

* code
  * [vcpu_fp.c - arch/riscv/kvm/vcpu_fp.c - Linux source code (v6.8) - Bootlin](https://elixir.bootlin.com/linux/v6.8/source/arch/riscv/kvm/vcpu_fp.c)
  * [vcpu_vector.c - arch/riscv/kvm/vcpu_vector.c - Linux source code (v6.8) - Bootlin](https://elixir.bootlin.com/linux/v6.8/source/arch/riscv/kvm/vcpu_vector.c)
  * [vector.c - arch/riscv/kernel/vector.c - Linux source code (v6.8) - Bootlin](https://elixir.bootlin.com/linux/v6.8/source/arch/riscv/kernel/vector.c)
  * [kernel_mode_vector.c - arch/riscv/kernel/kernel_mode_vector.c - Linux source code (v6.8) - Bootlin](https://elixir.bootlin.com/linux/v6.8/source/arch/riscv/kernel/kernel_mode_vector.c)
* [v11, 00/10\] riscv: support kernel-mode Vector - Andy Chiu](https://lore.kernel.org/linux-riscv/20240115055929.4736-1-andy.chiu@sifive.com/)
* [PATCH v10 00/16\] riscv: Add vector ISA support - Greentime Hu (kernel.org)](https://lore.kernel.org/all/cover.1652257230.git.greentime.hu@sifive.com/)

```c
/*		kvm-riscv 	  */
//vcpu_fp.c
kvm_riscv_vcpu_fp_reset
kvm_riscv_vcpu_fp_clean
kvm_riscv_vcpu_{host/guest}_fp_save
kvm_riscv_vcpu_{host/guest}_fp_restore
kvm_riscv_vcpu_{get/set}_reg_fp

//vcpu_vector.c
kvm_riscv_vcpu_vector_reset
kvm_riscv_vcpu_vector_clean
kvm_riscv_vcpu_{host/guest}_vector_save
kvm_riscv_vcpu_{host/guest}_vector_restore
kvm_riscv_vcpu_{alloc/free}_vector_context
kvm_riscv_vcpu_vreg_addr
kvm_riscv_vcpu_{get/set}_reg_vector
    
/*		kernel-riscv 	  */
//vector.c
riscv_v_vstate_ctrl_user_allowed
riscv_v_first_use_handler
riscv_v_vstate_ctrl_init
riscv_v_init
    
//kernel_mode_vector.c
riscv_v_{start/stop}
{get/put}_cpu_vector_context
riscv_preempt_v_{set/reset}_dirty
riscv_v_{start/stop}_kernel_context
riscv_v_context_nesting_{start/end}
kernel_vector_{begin/end}
```

## 1.1 目前kernel方案

### a) non-virtualization

* [RISC-V架构下 FPU Context 的动态保存和恢复 - 知乎 (zhihu.com)](https://zhuanlan.zhihu.com/p/532099752)
* [RISC-V特权指令集架构概述 | c_yongheng space (c-yongheng.github.io)](https://c-yongheng.github.io/2022/07/30/riscv-privileged-spec/)

#### 硬件支持

在mstatus[10:9]中添加了一个向量上下文状态字段VS，并在sstatus[10:9]中进行了镜像。它的定义与浮点上下文状态字段FS类似。

* 当 `mstatus.VS` 设置为Off时：尝试执行任何向量指令，或访问向量CSRs都会引发非法指令异常。

* 当 `mstatus.VS` 设置为Initial或Clean时：执行任何改变向量状态的指令，包括向量CSRs，都将把 `mstatus.VS` 更改为Dirty。实现也可以在向量状态没有改变的情况下，随时将mstatus.VS从Initial或Clean更改为Dirty。

> **<font color='red'>准确设置mstatus.VS是一种优化方法。软件通常会使用VS来减少上下文切换的开销。</font>**

---

The FS[1:0] and VS[1:0] WARL fields and the XS[1:0] read-only field are used to reduce the cost of context save and restore by setting and tracking the current state of the floating-point unit and any other user-mode extensions respectively. The FS field encodes the status of the floating-point unit state, including the floating-point registers f0–f31 and the CSRs fcsr, frm, and fflags. The VS field encodes the status of the vector extension state, including the vector registers v0–v31 and the CSRs vcsr, vxrm, vxsat, vstart, vl, vtype, and vlenb. The XS field encodes the status of additional user-mode extensions and associated state. 

These fields can be checked by a context switch routine to quickly determine whether a state save or restore is required. If a save or restore is required, additional instructions and CSRs are typically required to effect and optimize the process.

> The design anticipates that most context switches will not need to save/restore state in either or both of the floating-point unit or other extensions, so provides a fast check via the SD bit.

The FS, VS, and XS fields use the same status encoding as shown in Table 3.3, with the four possible status values being Off, Initial, Clean, and Dirty.

![image-20240411145556884](https://cdn.jsdelivr.net/gh/MaskerDad/BlogImage@main/202404111455905.png)

If the F extension is implemented, the FS field shall not be read-only zero.

If neither the F extension nor S-mode is implemented, then FS is read-only zero. If S-mode is implemented but the F extension is not, FS may optionally be read-only zero.

> Implementations with S-mode but without the F extension are permitted, but not required, to make the FS field be read-only zero. Some such implementations will choose not to have the FS field be read-only zero, so as to enable emulation of the F extension for both S-mode and U-mode via invisible traps into M-mode.

If the v registers are implemented, the VS field shall not be read-only zero.

If neither the v registers nor S-mode is implemented, then VS is read-only zero. If S-mode is implemented but the v registers are not, VS may optionally be read-only zero.

In systems without additional user extensions requiring new state, the XS field is read-only zero. Every additional extension with state provides a CSR field that encodes the equivalent of the XS states. The XS field represents a summary of all extensions’ status as shown in Table 3.3.

> The XS field effectively reports the maximum status value across all user-extension status fields, though individual extensions can use a different encoding than XS.

The SD bit is a read-only bit that summarizes whether either the FS, VS, or XS fields signal the presence of some dirty state that will require saving extended user context to memory. If FS, XS, and VS are all read-only zero, then SD is also always zero.

**When an extension’s status is set to Off, any instruction that attempts to read or write the corresponding state will cause an illegal instruction exception. When the status is Initial, the corresponding state should have an initial constant value. When the status is Clean, the corresponding state is potentially different from the initial value, but matches the last value stored on a context swap. When the status is Dirty, the corresponding state has potentially been modified since the last context save.**

**During a context save, the responsible privileged code need only write out the corresponding state if its status is Dirty, and can then reset the extension’s status to Clean. During a context restore, the context need only be loaded from memory if the status is Clean (it should never be Dirty at restore). If the status is Initial, the context must be set to an initial constant value on context restore to avoid a security hole, but this can be done without accessing memory. For example, the floating-point registers can all be initialized to the immediate value 0.**

The FS and XS fields are read by the privileged code before saving the context. The FS field is set directly by privileged code when resuming a user context, while the XS field is set indirectly by writing to the status register of the individual extensions. The status fields will also be updated during execution of instructions, regardless of privilege mode.

Extensions to the user-mode ISA often include additional user-mode state, and this state can be considerably larger than the base integer registers. The extensions might only be used for some applications, or might only be needed for short phases within a single application. To improve performance, the user-mode extension can define additional instructions to allow user-mode software to return the unit to an initial state or even to turn off the unit.

For example, a coprocessor might require to be configured before use and can be “unconfigured” after use. The unconfigured state would be represented as the Initial state for context save. If the same application remains running between the unconfigure and the next configure (which would set status to Dirty), there is no need to actually reinitialize the state at the unconfigure instruction, as all state is local to the user process, i.e., the Initial state may only cause the coprocessor state to be initialized to a constant value at context restore, not at every unconfigure.

Executing a user-mode instruction to disable a unit and place it into the Off state will cause an illegal instruction exception to be raised if any subsequent instruction tries to use the unit before it is turned back on. A user-mode instruction to turn a unit on must also ensure the unit’s state is properly initialized, as the unit might have been used by another context meantime.

Changing the setting of FS has no effect on the contents of the floating-point register state. In particular, setting FS=Off does not destroy the state, nor does setting FS=Initial clear the contents. Similarly, the setting of VS has no effect on the contents of the vector register state. Other extensions, however, might not preserve state when set to Off.

Implementations may choose to track the dirtiness of the floating-point register state imprecisely by reporting the state to be dirty even when it has not been modified. On some implementations, some instructions that do not mutate the floating-point state may cause the state to transition from Initial or Clean to Dirty. On other implementations, dirtiness might not be tracked at all, in which case the valid FS states are Off and Dirty, and an attempt to set FS to Initial or Clean causes it to be set to Dirty.

> This definition of FS does not disallow setting FS to Dirty as a result of errant speculation. Someplatforms may choose to disallow speculatively writing FS to close a potential side channel.

If an instruction explicitly or implicitly writes a floating-point register or the fcsr but does not alter its contents, and FS=Initial or FS=Clean, it is implementation-defined whether FS transitionsto Dirty.

Implementations may choose to track the dirtiness of the vector register state in an analogous imprecise fashion, including possibly setting VS to Dirty when software attempts to set VS=Initial or VS=Clean. When VS=Initial or VS=Clean, it is implementation-defined whether an instruction that writes a vector register or vector CSR but does not alter its contents causes VS to transition
to Dirty.

**Table 3.4 shows all the possible state transitions for the FS, VS, or XS status bits. Note that the standard floating-point and vector extensions do not support user-mode unconfigure or disable/enable instructions.**

![image-20240411145636797](https://cdn.jsdelivr.net/gh/MaskerDad/BlogImage@main/202404111456823.png)

Standard privileged instructions to initialize, save, and restore extension state are provided to insulate privileged code from details of the added extension state by treating the state as an opaque object.

> Many coprocessor extensions are only used in limited contexts that allows software to safely unconfigure or even disable units when done. This reduces the context-switch overhead of large stateful coprocessors.
> We separate out floating-point state from other extension state, as when a floating-point unit is present the floating-point registers are part of the standard calling convention, and so user-mode software cannot know when it is safe to disable the floating-point unit.

The XS field provides a summary of all added extension state, but additional microarchitectural bits might be maintained in the extension to further reduce context save and restore overhead.

**The SD bit is read-only and is set when either the FS, VS, or XS bits encode a Dirty state (i.e., SD=((FS==11) OR (XS==11) OR (VS==11))). This allows privileged code to quickly determine when no additional context save is required beyond the integer register set and PC.**

The floating-point unit state is always initialized, saved, and restored using standard instructions (F, D, and/or Q), and privileged code must be aware of FLEN to determine the appropriate space to reserve for each f register.

Machine and Supervisor modes share a single copy of the FS, VS, and XS bits. Supervisor-level software normally uses the FS, VS, and XS bits directly to record the status with respect to the supervisor-level saved context. Machine-level software must be more conservative in saving and restoring the extension state in their corresponding version of the context.

> In any reasonable use case, the number of context switches between user and supervisor level should far outweigh the number of context switches to other privilege levels. Note that coprocessors should not require their context to be saved and restored to service asynchronous interrupts, unless the interrupt results in a user-level context swap.

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

vector状态管理：

![image-20240411161517088](https://cdn.jsdelivr.net/gh/MaskerDad/BlogImage@main/202404111615142.png)

```c
#define SR_VS		_AC(0x00000600, UL) /* Vector Status */
#define SR_VS_OFF	_AC(0x00000000, UL)
#define SR_VS_INITIAL	_AC(0x00000200, UL)
#define SR_VS_CLEAN	_AC(0x00000400, UL)
#define SR_VS_DIRTY	_AC(0x00000600, UL)

static inline void __riscv_v_vstate_clean(struct pt_regs *regs)
{
	regs->status = (regs->status & ~SR_VS) | SR_VS_CLEAN;
}

static inline void __riscv_v_vstate_dirty(struct pt_regs *regs)
{
	regs->status = (regs->status & ~SR_VS) | SR_VS_DIRTY;
}

static inline void riscv_v_vstate_off(struct pt_regs *regs)
{
	regs->status = (regs->status & ~SR_VS) | SR_VS_OFF;
}

static inline void riscv_v_vstate_on(struct pt_regs *regs)
{
	regs->status = (regs->status & ~SR_VS) | SR_VS_INITIAL;
}

static inline bool riscv_v_vstate_query(struct pt_regs *regs)
{
	return (regs->status & SR_VS) != 0;
}

static __always_inline void riscv_v_enable(void)
{
	csr_set(CSR_SSTATUS, SR_VS);
}

static __always_inline void riscv_v_disable(void)
{
	csr_clear(CSR_SSTATUS, SR_VS);
}
```

#### vector context switch

[PATCH v10 08/16\] riscv: Add task switch support for vector - Greentime Hu (kernel.org)](https://lore.kernel.org/all/3f544b952369e55f72a8771d0bec387c2ff49ae0.1652257230.git.greentime.hu@sifive.com/)

[PATCH v10 10/16\] riscv: Add sigcontext save/restore for vector - Greentime Hu (kernel.org)](https://lore.kernel.org/all/055b74196f945ab09c97e229ad54b2c07e55bf90.1652257230.git.greentime.hu@sifive.com/)

---

触发vector context切换的场景：

```c
@@ -96,6 +96,25 @@ void start_thread(struct pt_regs *regs, unsigned long pc,
 		 */
 		fstate_restore(current, regs);
 	}
+
+	if (has_vector()) {
+		struct __riscv_v_state *vstate = &(current->thread.vstate);
+
+		/* Enable vector and allocate memory for vector registers. */
+		if (!vstate->datap) {
+			vstate->datap = kzalloc(riscv_vsize, GFP_KERNEL);
+			if (WARN_ON(!vstate->datap))
+				return;
+		}
+		regs->status |= SR_VS_INITIAL;
+
+		/*
+		 * Restore the initial value to the vector register
+		 * before starting the user program.
+		 */
+		vstate_restore(current, regs);
+	}
+
 	regs->epc = pc;
 	regs->sp = sp;
 }
@@ -111,15 +130,29 @@ void flush_thread(void)
 	fstate_off(current, task_pt_regs(current));
 	memset(&current->thread.fstate, 0, sizeof(current->thread.fstate));
 #endif
+#ifdef CONFIG_VECTOR
+	/* Reset vector state */
+	vstate_off(current, task_pt_regs(current));
+	memset(&current->thread.vstate, 0, RISCV_V_STATE_DATAP);
+#endif
 }
```

[vector.h - arch/riscv/include/asm/vector.h - Linux source code (v6.8) - Bootlin](https://elixir.bootlin.com/linux/v6.8/source/arch/riscv/include/asm/vector.h#L235)

[processor.h - arch/riscv/include/asm/processor.h - Linux source code (v6.8) - Bootlin](https://elixir.bootlin.com/linux/v6.8/source/arch/riscv/include/asm/processor.h#L109)

```c
+static inline void vstate_save(struct task_struct *task,
+			       struct pt_regs *regs)
+{
+	if ((regs->status & SR_VS) == SR_VS_DIRTY) {
+		struct __riscv_v_state *vstate = &(task->thread.vstate);
+
+		__vstate_save(vstate, vstate->datap);
+		__vstate_clean(regs);
+	}
+}
+
+static inline void vstate_restore(struct task_struct *task,
+				  struct pt_regs *regs)
+{
+	if ((regs->status & SR_VS) != SR_VS_OFF) {
+		struct __riscv_v_state *vstate = &(task->thread.vstate);
+		
   	 	//无法判断当前hart上的vector状态，是否匹配vstate->datap
    	//因此，必须恢复该task的上下文
+		__vstate_restore(vstate, vstate->datap);
+		__vstate_clean(regs);
+	}
+}
+
+static inline void __switch_to_vector(struct task_struct *prev,
+				   struct task_struct *next)
+{
+	struct pt_regs *regs;
+
+	regs = task_pt_regs(prev);
+	if (unlikely(regs->status & SR_SD))
+		vstate_save(prev, regs); //将修改过的最新vector状态拉取下来
+	vstate_restore(next, task_pt_regs(next));
+}
 extern struct task_struct *__switch_to(struct task_struct *,
 				       struct task_struct *);
 
@@ -77,6 +141,8 @@ do {							\
 	struct task_struct *__next = (next);		\
 	if (has_fpu())					\
 		__switch_to_fpu(__prev, __next);	\
+	if (has_vector())					\
+		__switch_to_vector(__prev, __next);	\
 	((last) = __switch_to(__prev, __next));		\
 } while (0)
```

#### kernel-mode vector

https://lore.kernel.org/all/20240115055929.4736-2-andy.chiu@sifive.com/

该系列提供了在内核模式中运行Vector所需的支持。此外，内核模式下的Vector可以配置为在CONFIG_PREEMPT内核上不关闭抢占。除了提供支持外，我们还添加了优化过的`copy_{to,from}_user` 函数，并提供了一个简单的阈值来决定何时运行矢量化函数。

由于对内核_vector_begin()中的内存副作用的担忧，我们决定暂时放弃矢量化的memcpy/memset/memmove。详细描述请参见v9[0]。

此系列包含4个部分：

- 补丁1-4：添加内核模式Vector的基本支持
- 补丁5：将矢量化的 `copy_{to,from}_user` 包含到内核中
- 补丁6：重构fpu中的上下文切换代码[1]
- 补丁7-10：提供一些代码重构和支持可抢占的内核模式Vector。

只要{1~4, 5, 6, 7~10}中的任何部分已经足够成熟，就可以合并此系列。

该补丁已在使用设置阈值为0的情况下的QEMU上进行测试，并验证引导、正常用户空间操作均正常工作。此外，我们通过启动多个内核线程，在后台连续执行和验证矢量化操作来进行测试。预期测试这些操作的模块稍后将被上游。

---

##### 支持内核向量操作

[v11, 01/10\] riscv: Add support for kernel mode vector - Andy Chiu](https://lore.kernel.org/all/20240115055929.4736-2-andy.chiu@sifive.com/)

```c
+/*
+ * kernel_vector_begin(): obtain the CPU vector registers for use by the calling
+ * context
+ *
+ * Must not be called unless may_use_simd() returns true.
+ * Task context in the vector registers is saved back to memory as necessary.
+ *
+ * A matching call to kernel_vector_end() must be made before returning from the
+ * calling context.
+ *
+ * The caller may freely use the vector registers until kernel_vector_end() is
+ * called.
+ */
+void kernel_vector_begin(void)
+{
+	if (WARN_ON(!has_vector()))
+		return;
+
+	BUG_ON(!may_use_simd());
+
+	get_cpu_vector_context();
+
+	riscv_v_vstate_save(current, task_pt_regs(current));
+
+	riscv_v_enable();
+}
+EXPORT_SYMBOL_GPL(kernel_vector_begin);
+
+/*
+ * kernel_vector_end(): give the CPU vector registers back to the current task
+ *
+ * Must be called from a context in which kernel_vector_begin() was previously
+ * called, with no call to kernel_vector_end() in the meantime.
+ *
+ * The caller must not use the vector registers after this function is called,
+ * unless kernel_vector_begin() is called again in the meantime.
+ */
+void kernel_vector_end(void)
+{
+	if (WARN_ON(!has_vector()))
+		return;
+
+	riscv_v_vstate_restore(current, task_pt_regs(current));
+
+	riscv_v_disable();
+
+	put_cpu_vector_context();
+}
+EXPORT_SYMBOL_GPL(kernel_vector_end);
```

由于内核线程一旦进行vector操作，将覆盖用户态的vector上下文，因此内核在使用vector前，必须调用 `kernel_vector_begin` 保存并使能vector；在内核结束vector操作后，必须调用 `kernel_vector_end` 恢复并禁用vector。

实际上，内核使用vector的场景不多，主要包括：

* 内核的一些加密算法，需要vector加速；
* 数据拷贝 `copy_{tp/from}_user`，超过一定数量阈值，考虑用vector加速；
* 设备相关的，中断处理流程；

第三种场景，在中断上下文内进行vector操作，相应的设备驱动在注册中断ISR时，必须使用 `kvm_vector_begin/kvm_vector_end` 封装vector代码。同时，在soft_irq处理流程中不能再次使用vector，因为中断嵌套将覆盖上一个中断上下文的vector内容，而且嵌套的保存恢复vector是开销极大的，内核中仅接受在一次中断中使用vector。

---

[v11, 02/10\] riscv: vector: make Vector always available for softirq context - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20240115055929.4736-3-andy.chiu@sifive.com/)

这个补丁的目标是在内核的软中断（softirq）上下文中提供对向量的完全支持，从而使某些加密算法无需回退到标量模式。通过在活跃的内核模式向量操作中禁用下半部，软中断将无法在任何内核模式向量操作上进行嵌套。因此，软中断上下文可以在运行时自由使用向量。

此外，补丁规定，在中断被禁用的情况下不能启动向量上下文，否则 `local_bh_enable()` 可能会在不适当的上下文中执行。对于实时内核，仅禁用下半部不足以防止抢占，因此必须禁用抢占，这同时意味着在实时环境中也需要禁用下半部。

```c
@@ -28,8 +28,12 @@ static __must_check inline bool may_use_simd(void)
 	/*
 	 * RISCV_KERNEL_MODE_V is only set while preemption is disabled,
 	 * and is clear whenever preemption is enabled.
+	 *
+	 * Kernel-mode Vector temporarily disables bh. So we must not return
+	 * true on irq_disabled(). Otherwise we would fail the lockdep check
+	 * calling local_bh_enable()
 	 */
-	return !in_hardirq() && !in_nmi() && !(riscv_v_flags() & RISCV_KERNEL_MODE_V);
+	return !in_hardirq() && !in_nmi() && !irqs_disabled() && !(riscv_v_flags() & RISCV_KERNEL_MODE_V);
 }

 void get_cpu_vector_context(void)
 {
-	preempt_disable();
+	/*
+	 * disable softirqs so it is impossible for softirqs to nest
+	 * get_cpu_vector_context() when kernel is actively using Vector.
+	 */
+	if (!IS_ENABLED(CONFIG_PREEMPT_RT))
+		local_bh_disable();
+	else
+		preempt_disable();
 
 	riscv_v_start(RISCV_KERNEL_MODE_V);
 }
@@ -62,7 +69,10 @@ void put_cpu_vector_context(void)
 {
 	riscv_v_stop(RISCV_KERNEL_MODE_V);
 
-	preempt_enable();
+	if (!IS_ENABLED(CONFIG_PREEMPT_RT))
+		local_bh_enable();
+	else
+		preempt_enable();
 }
```

- [ ] [内核抢占，让世界变得更美好 | Linux 内核 - 知乎 (zhihu.com)](https://zhuanlan.zhihu.com/p/405965784)

- [ ] [实时Linux内核的实现-腾讯云开发者社区-腾讯云 (tencent.com)](https://cloud.tencent.com/developer/article/1894161)

---

[v11, 04/10\] riscv: sched: defer restoring Vector context for user - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20240115055929.4736-5-andy.chiu@sifive.com/)

用户只有在内核真正返回用户空间后，才会使用其向量寄存器。因此，我们可以延迟恢复向量寄存器，直到我们仍在内核模式运行。添加一个线程标志来指示需要恢复向量，并在最后一个与架构相关的退出到用户的钩子中进行恢复。这样可以节约在内核模式下切换多个进程时的上下文恢复成本。

* 如果内核从A切换到B再到C，并且返回到C的用户空间，则无需恢复B的向量寄存器。
* 避免了在多次执行内核模式向量操作时重复恢复向量上下文的情况。

这种方法的成本是，在 `vstate_{save,restore}` 过程中我们必须禁用抢占并标记向量为忙。这是因为在`vstate_{save,restore}` 过程中发生导致陷阱的上下文切换时，**向量上下文将不会立刻恢复。**

> 在 `__switch_to_vector` 中，仅设置了一个TIF_RISCV_V_DEFER_RESTORE，推迟到返回用户态前恢复。

```c
#define TIF_NOTIFY_SIGNAL	9	/* signal notifications exist */
 #define TIF_UPROBE		10	/* uprobe breakpoint or singlestep */
 #define TIF_32BIT		11	/* compat-mode 32bit process */
+#define TIF_RISCV_V_DEFER_RESTORE	12 /* restore Vector before returing to user */
 
 #define _TIF_NOTIFY_RESUME	(1 << TIF_NOTIFY_RESUME)
 #define _TIF_SIGPENDING		(1 << TIF_SIGPENDING)
 #define _TIF_NEED_RESCHED	(1 << TIF_NEED_RESCHED)
 #define _TIF_NOTIFY_SIGNAL	(1 << TIF_NOTIFY_SIGNAL)
 #define _TIF_UPROBE		(1 << TIF_UPROBE)
+#define _TIF_RISCV_V_DEFER_RESTORE	(1 << TIF_RISCV_V_DEFER_RESTORE)

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
    
+static inline void riscv_v_vstate_set_restore(struct task_struct *task,
+					      struct pt_regs *regs)
+{
+	if ((regs->status & SR_VS) != SR_VS_OFF) {
+		set_tsk_thread_flag(task, TIF_RISCV_V_DEFER_RESTORE);
+		riscv_v_vstate_on(regs);
+	}
+}
+

@@ -200,7 +209,7 @@ static inline void __switch_to_vector(struct task_struct *prev,
 
 	regs = task_pt_regs(prev);
 	riscv_v_vstate_save(prev, regs);
-	riscv_v_vstate_restore(next, task_pt_regs(next));
+	riscv_v_vstate_set_restore(next, task_pt_regs(next));
 }
```

##### 支持可抢占的内核模式Vector

https://lore.kernel.org/linux-riscv/20240115055929.4736-11-andy.chiu@sifive.com/

我们使用一个标志来跟踪内核中的向量上下文。目前，该标志具有以下含义：

* 位 0：指示内核中的向量上下文是否处于活动状态。此状态的激活会禁用抢占。在非 RT 内核上，它还会禁用 bh。
* 位 8：用于跟踪可抢占内核模式向量，当 RISCV_ISA_V_PREEMPTIVE 被启用时。调用 kernel_vector_begin() 不会禁用抢占，如果线程的 kernel_vstate.datap 被分配。相反，内核设置这个位域。然后陷阱入口/出口代码会知道我们是进入/退出拥有 preempt_v 上下文的上下文。
  * 0：任务未使用 preempt_v；
  * 1：任务正在积极使用 preempt_v。但任务是否拥有 preempt_v 上下文是由 RISCV_V_CTX_DEPTH_MASK 中的位决定的；

* 位 16-23 是 RISCV_V_CTX_DEPTH_MASK，用于上下文跟踪例程当 preempt_v 开始时：
  * 0：任务正在使用，并拥有 preempt_v 上下文。
  * 非零：任务正在使用 preempt_v，但随后在其中发生了陷阱。因此，任务不拥有 preempt_v。任何使用向量的操作都必须保存 preempt_v，如果它是脏的，则回退到非可抢占内核模式向量。

* 位 30：内核中的 preempt_v 上下文已保存，并且在返回到拥有 preempt_v 上下文的上下文时需要恢复。
* 位 31：内核中的 preempt_v 上下文是脏的，由陷阱入口代码表示。任何切换出当前任务的上下文需要将其保存到任务的内核 V 上下文中。此外，任何堆叠在 preempt_v 之上并请求使用 V 的陷阱需要保存。

```c
#define RISCV_V_CTX_DEPTH_MASK		0x00ff0000

#define RISCV_V_CTX_UNIT_DEPTH		0x00010000
#define RISCV_KERNEL_MODE_V		0x00000001
#define RISCV_PREEMPT_V			0x00000100
#define RISCV_PREEMPT_V_DIRTY		0x80000000
#define RISCV_PREEMPT_V_NEED_RESTORE	0x40000000

+config RISCV_ISA_V_PREEMPTIVE
+	bool "Run kernel-mode Vector with kernel preemption"
+	depends on PREEMPTION
+	depends on RISCV_ISA_V
+	default y
+	help
+	  Usually, in-kernel SIMD routines are run with preemption disabled.
+	  Functions which envoke long running SIMD thus must yield core's
+	  vector unit to prevent blocking other tasks for too long.
+
+	  This config allows kernel to run SIMD without explicitly disable
+	  preemption. Enabling this config will result in higher memory
+	  consumption due to the allocation of per-task's kernel Vector context.
    
    
 static inline void __switch_to_vector(struct task_struct *prev,
 				      struct task_struct *next)
 {
 	struct pt_regs *regs;
 
-	regs = task_pt_regs(prev);
-	riscv_v_vstate_save(&prev->thread.vstate, regs);
-	riscv_v_vstate_set_restore(next, task_pt_regs(next));
+	if (riscv_preempt_v_started(prev)) {
+		if (riscv_preempt_v_dirty(prev)) {
+			__riscv_v_vstate_save(&prev->thread.kernel_vstate,
+					      prev->thread.kernel_vstate.datap);
+			riscv_preempt_v_clear_dirty(prev);
+		}
+	} else {
+		regs = task_pt_regs(prev);
+		riscv_v_vstate_save(&prev->thread.vstate, regs);
+	}
+
+	if (riscv_preempt_v_started(next))
+		riscv_preempt_v_set_restore(next);
+	else
+		riscv_v_vstate_set_restore(next, task_pt_regs(next));
 }

// arch/riscv/kernel/entry.S
@@ -83,6 +83,10 @@ SYM_CODE_START(handle_exception)
 	/* Load the kernel shadow call stack pointer if coming from userspace */
 	scs_load_current_if_task_changed s5
 
+#ifdef CONFIG_RISCV_ISA_V_PREEMPTIVE
+	move a0, sp
+	call riscv_v_context_nesting_start
+#endif
 	move a0, sp /* pt_regs */
 	la ra, ret_from_exception
 
@@ -138,6 +142,10 @@ SYM_CODE_START_NOALIGN(ret_from_exception)
 	 */
 	csrw CSR_SCRATCH, tp
 1:
+#ifdef CONFIG_RISCV_ISA_V_PREEMPTIVE
+	move a0, sp
+	call    
    
static int riscv_v_stop_kernel_context(void);
static int riscv_v_start_kernel_context(bool *is_nested);
/* low-level V context handling code, called with irq disabled */
+asmlinkage void riscv_v_context_nesting_start(struct pt_regs *regs);
+asmlinkage void riscv_v_context_nesting_end(struct pt_regs *regs);

void kernel_vector_begin(void)
 {
+	bool nested = false;
+
 	if (WARN_ON(!has_vector()))
 		return;
 
 	BUG_ON(!may_use_simd());
 
-	get_cpu_vector_context();
+	if (riscv_v_start_kernel_context(&nested)) {
+		get_cpu_vector_context();
+		riscv_v_vstate_save(&current->thread.vstate, task_pt_regs(current));
+	}
 
-	riscv_v_vstate_save(&current->thread.vstate, task_pt_regs(current));
+	if (!nested)
+		riscv_v_vstate_set_restore(current, task_pt_regs(current));
 
 	riscv_v_enable();
 }
@@ -117,10 +239,9 @@ void kernel_vector_end(void)
 	if (WARN_ON(!has_vector()))
 		return;
 
-	riscv_v_vstate_set_restore(current, task_pt_regs(current));
-
 	riscv_v_disable();
 
-	put_cpu_vector_context();
+	if (riscv_v_stop_kernel_context())
+		put_cpu_vector_context();
 }

@@ -28,12 +29,27 @@ static __must_check inline bool may_use_simd(void)
 	/*
 	 * RISCV_KERNEL_MODE_V is only set while preemption is disabled,
 	 * and is clear whenever preemption is enabled.
-	 *
-	 * Kernel-mode Vector temporarily disables bh. So we must not return
-	 * true on irq_disabled(). Otherwise we would fail the lockdep check
-	 * calling local_bh_enable()
 	 */
-	return !in_hardirq() && !in_nmi() && !irqs_disabled() && !(riscv_v_flags() & RISCV_KERNEL_MODE_V);
+	if (in_hardirq() || in_nmi())
+		return false;
+
+	/*
+	 * Nesting is acheived in preempt_v by spreading the control for
+	 * preemptible and non-preemptible kernel-mode Vector into two fields.
+	 * Always try to match with prempt_v if kernel V-context exists. Then,
+	 * fallback to check non preempt_v if nesting happens, or if the config
+	 * is not set.
+	 */
+	if (IS_ENABLED(CONFIG_RISCV_ISA_V_PREEMPTIVE) && current->thread.kernel_vstate.datap) {
+		if (!riscv_preempt_v_started(current))
+			return true;
+	}
+	/*
+	 * Non-preemptible kernel-mode Vector temporarily disables bh. So we
+	 * must not return true on irq_disabled(). Otherwise we would fail the
+	 * lockdep check calling local_bh_enable()
+	 */
+	return !irqs_disabled() && !(riscv_v_flags() & RISCV_KERNEL_MODE_V);
 }
```

### b) virtualization

#### 硬件支持





#### kvm: vector switch

[PATCH v10 16/16\] riscv: KVM: Add vector lazy save/restore support - Greentime Hu (kernel.org)](https://lore.kernel.org/all/8174f9e04cbb55b8bdeceeb0ca6ff2bdd748290c.1652257230.git.greentime.hu@sifive.com/)



# 2 arm64

## 2.1 引用

* https://elixir.bootlin.com/linux/latest/source/arch/arm64/kernel/fpsimd.c#L416
* [PATCH 2/3\] arm64: defer reloading a task's FPSIMD state to userland resume - Ard Biesheuvel (kernel.org)](https://lore.kernel.org/all/1399548184-9534-2-git-send-email-ard.biesheuvel@linaro.org/)



## 2.2 per-cpu: fpsimd_last_state

> 如果一个任务被调度出去再重新调度回来，并且在此期间没有任何操作影响到它的FPSIMD状态，那么就没有必要从内存中重新加载它。同样，对 `kernel_neon_begin()` 和 `kernel_neon_end()` 的重复调用将在每次调用时保留和恢复FPSIMD状态。
>
> 这个补丁将FPSIMD状态的恢复推迟到最后可能的时刻，即在任务返回到用户空间之前。如果一个任务根本不返回到用户空间（由于任何原因），现有的FPSIMD状态将被保留，并且如果该任务在同一CPU上再次被调度，则可以重用。
>
> 此补丁添加了两个函数，以抽象出直接的FPSIMD寄存器文件保存和恢复：
>
> - `fpsimd_restore_current_state` -> 确保当前的FPSIMD状态已加载
> - `fpsimd_flush_task_state` -> 使任务的FPSIMD状态的活动副本失效

---

注意：在本讨论中，有关FPSIMD的陈述同样适用于SVE。

为了减少不必要地保存和恢复FPSIMD状态的次数，我们需要记住两件事：

>  * （a）对于每个任务，我们需要记住最后一次将任务的FPSIMD状态，加载到其FPSIMD寄存器对应的CPU是哪个；
>  * （b）对于每个CPU，我们需要记住最近已加载到其FPSIMD寄存器中，是哪个任务的用户层FPSIMD状态，或者在此期间是否已用于执行内核模式NEON。

对于（a），我们向thread_struct添加了一个 `fpsimd_cpu` 字段，每当状态加载到CPU上时，该字段就会更新为当前CPU的ID。对于（b），我们添加了每个CPU变量 `fpsimd_last_state`，它包含最近加载到CPU上的用户层FPSIMD状态的地址，或者如果之后已执行内核模式NEON，则为NULL。

有了这个设计，我们就不再需要在任务之间切换时，立即恢复下一个FPSIMD状态。相反，我们可以将此检查推迟到用户空间恢复时，届时我们会验证CPU的 `fpsimd_last_state` 和任务的 `fpsimd_cpu` 是否仍然相互同步。如果都保持同步，我们可以省略FPSIMD的恢复。

作为优化，我们使用thread_info标志 `TIF_FOREIGN_FPSTATE` 来指示，当前任务的用户层FPSIMD状态是否存在于寄存器中。除非此CPU的FPSIMD寄存器，包含当前任务的最新用户层FPSIMD状态，否则将设置该标志。如果任务表现为VMM，则这将由KVM进行管理，KVM将清除它以指示vcpu的FPSIMD状态当前已加载到CPU上，从而允许在出现FPSIMD感知软中断时保存状态。在 `vcpu_put()` 之后，KVM将保存vcpu的FP状态，并标记寄存器状态为无效。

为了允许软中断处理程序使用FPSIMD，可以从软中断上下文调用 `kernel_neon_begin()`，该函数会将任务的FPSIMD上下文保存回task_struct。为了防止这与任务上下文中的任务的FPSIMD状态的操作发生竞争并因此破坏状态，有必要使用 `get_cpu_fpsimd_context()` 保护任务的fpsimd_state或TIF_FOREIGN_FPSTATE标志的任何操作，该函数将完全暂停软中断服务，直到调用 `put_cpu_fpsimd_context()` 为止。

**对于某个任务，序列可能如下所示：**

* **任务被调度进入**：如果任务的 `fpsimd_cpu` 字段为当前CPU的ID，并且CPU的 `fpsimd_last_state per-cpu` 变量指向任务的`fpsimd_state` ，则清除TIF_FOREIGN_FPSTATE标志，否则设置该标志；
* **任务返回到用户空间：**如果设置了TIF_FOREIGN_FPSTATE，则从内存中将任务的用户空间FPSIMD状态复制到寄存器中，将任务的`fpsimd_cpu` 字段设置为当前CPU的ID，将当前CPU的 `fpsimd_last_state`指针设置为此任务的`fpsimd_state`，并清除TIF_FOREIGN_FPSTATE标志；
* **任务执行普通系统调用**：返回到用户空间时，TIF_FOREIGN_FPSTATE标志仍将被清除，因此不会恢复任何FPSIMD状态；
* **任务执行和NEON相关的系统调用：**在调用 `kernel_neon_begin()` 之前，会将任务的FPSIMD寄存器内容复制到内存中，清除`fpsimd_last_state` per-cpu变量并设置TIF_FOREIGN_FPSTATE标志；
* **在调用kernel_neon_end()后，任务被抢占：**由于我们尚未从第二个系统调用中返回，因此TIF_FOREIGN_FPSTATE仍然被设置，因此FPSIMD寄存器中的任何内容都不会保存到内存中，而是被丢弃。

---

>task_0, task_1, hart0, hart1;
>
>* 对于hart0，prev=task_0，next=task_1；进入调度流 `__switch_to`：
>  * `save task_0`：保存是否可以推迟？即使dirty也无需立即保存，显然不行，因为task_0可能调度到其他hart上，dirty的vector上下文必须立即保存；
>  * `restore task_1`：恢复是否可以推迟？
>    * 内核空间发生多次调度，A->B->C，内核只需要恢复C的；
>    * 内核态的vector行为，如果多次发生，也没必要多次恢复；
>
>* 如果一个任务被调度出去再重新调度回来，并且在此期间没有任何操作影响到它的FPSIMD状态，那么就没有必要从内存中重新加载它；

---

## 2.3 non-virtualization

```c
/*
 * Ensure FPSIMD/SVE storage in memory for the loaded context is up to
 * date with respect to the CPU registers. Note carefully that the
 * current context is the context last bound to the CPU stored in
 * last, if KVM is involved this may be the guest VM context rather
 * than the host thread for the VM pointed to by current. This means
 * that we must always reference the state storage via last rather
 * than via current, if we are saving KVM state then it will have
 * ensured that the type of registers to save is set in last->to_save.
 */
fpsimd_save_user_state
    if (test_thread_flag(TIF_FOREIGN_FPSTATE))
		return;

sve_init_regs
   	/*
	 * Convert the FPSIMD state to SVE, zeroing all the state that
	 * is not shared with FPSIMD. If (as is likely) the current
	 * state is live in the registers then do this there and
	 * update our metadata for the current task including
	 * disabling the trap, otherwise update our in-memory copy.
	 * We are guaranteed to not be in streaming mode, we can only
	 * take a SVE trap when not in streaming mode and we can't be
	 * in streaming mode when taking a SME trap.
	 */
    +-> if (!test_thread_flag(TIF_FOREIGN_FPSTATE)) {
        	//...
        	fpsimd_bind_task_to_cpu();
    	}

/*
 * Trapped SME access
 *
 * Storage is allocated for the full SVE and SME state, the current
 * FPSIMD register contents are migrated to SVE if SVE is not already
 * active, and the access trap is disabled.
 *
 * TIF_SME should be clear on entry: otherwise, fpsimd_restore_current_state()
 * would have disabled the SME access trap for userspace during
 * ret_to_user, making an SME access trap impossible in that case.
 */
do_sme_acc
    +-> if (!test_thread_flag(TIF_FOREIGN_FPSTATE)) {
        	//...
        	fpsimd_bind_task_to_cpu();
    	}

void fpsimd_thread_switch(struct task_struct *next)
{
	bool wrong_task, wrong_cpu;

	if (!system_supports_fpsimd())
		return;

	WARN_ON_ONCE(!irqs_disabled());

	/* Save unsaved fpsimd state, if any: */
	if (test_thread_flag(TIF_KERNEL_FPSTATE))
		fpsimd_save_kernel_state(current);
	else
		fpsimd_save_user_state();

	if (test_tsk_thread_flag(next, TIF_KERNEL_FPSTATE)) {
		fpsimd_load_kernel_state(next);
		set_tsk_thread_flag(next, TIF_FOREIGN_FPSTATE);
	} else {
		/*
		 * Fix up TIF_FOREIGN_FPSTATE to correctly describe next's
		 * state.  For kernel threads, FPSIMD registers are never
		 * loaded with user mode FPSIMD state and so wrong_task and
		 * wrong_cpu will always be true.
		 */
		wrong_task = __this_cpu_read(fpsimd_last_state.st) !=
			&next->thread.uw.fpsimd_state;
		wrong_cpu = next->thread.fpsimd_cpu != smp_processor_id();

		update_tsk_thread_flag(next, TIF_FOREIGN_FPSTATE,
				       wrong_task || wrong_cpu);
	}
}

/*
 * Load the userland FPSIMD state of 'current' from memory, but only if the
 * FPSIMD state already held in the registers is /not/ the most recent FPSIMD
 * state of 'current'.  This is called when we are preparing to return to
 * userspace to ensure that userspace sees a good register state.
 */
void fpsimd_restore_current_state(void)
{
	/*
	 * TIF_FOREIGN_FPSTATE is set on the init task and copied by
	 * arch_dup_task_struct() regardless of whether FP/SIMD is detected.
	 * Thus user threads can have this set even when FP/SIMD hasn't been
	 * detected.
	 *
	 * When FP/SIMD is detected, begin_new_exec() will set
	 * TIF_FOREIGN_FPSTATE via flush_thread() -> fpsimd_flush_thread(),
	 * and fpsimd_thread_switch() will set TIF_FOREIGN_FPSTATE when
	 * switching tasks. We detect FP/SIMD before we exec the first user
	 * process, ensuring this has TIF_FOREIGN_FPSTATE set and
	 * do_notify_resume() will call fpsimd_restore_current_state() to
	 * install the user FP/SIMD context.
	 *
	 * When FP/SIMD is not detected, nothing else will clear or set
	 * TIF_FOREIGN_FPSTATE prior to the first return to userspace, and
	 * we must clear TIF_FOREIGN_FPSTATE to avoid do_notify_resume()
	 * looping forever calling fpsimd_restore_current_state().
	 */
	if (!system_supports_fpsimd()) {
		clear_thread_flag(TIF_FOREIGN_FPSTATE);
		return;
	}

	get_cpu_fpsimd_context();

	if (test_and_clear_thread_flag(TIF_FOREIGN_FPSTATE)) {
		task_fpsimd_load();
		fpsimd_bind_task_to_cpu();
	}

	put_cpu_fpsimd_context();
}

/*
 * Load an updated userland FPSIMD state for 'current' from memory and set the
 * flag that indicates that the FPSIMD register contents are the most recent
 * FPSIMD state of 'current'. This is used by the signal code to restore the
 * register state when returning from a signal handler in FPSIMD only cases,
 * any SVE context will be discarded.
 */
void fpsimd_update_current_state(struct user_fpsimd_state const *state)
{
	if (WARN_ON(!system_supports_fpsimd()))
		return;

	get_cpu_fpsimd_context();

	current->thread.uw.fpsimd_state = *state;
	if (test_thread_flag(TIF_SVE))
		fpsimd_to_sve(current);

	task_fpsimd_load();
	fpsimd_bind_task_to_cpu();

	clear_thread_flag(TIF_FOREIGN_FPSTATE);

	put_cpu_fpsimd_context();
}

/*
 * Invalidate live CPU copies of task t's FPSIMD state
 *
 * This function may be called with preemption enabled.  The barrier()
 * ensures that the assignment to fpsimd_cpu is visible to any
 * preemption/softirq that could race with set_tsk_thread_flag(), so
 * that TIF_FOREIGN_FPSTATE cannot be spuriously re-cleared.
 *
 * The final barrier ensures that TIF_FOREIGN_FPSTATE is seen set by any
 * subsequent code.
 */
void fpsimd_flush_task_state(struct task_struct *t)
{
	t->thread.fpsimd_cpu = NR_CPUS;
	/*
	 * If we don't support fpsimd, bail out after we have
	 * reset the fpsimd_cpu for this task and clear the
	 * FPSTATE.
	 */
	if (!system_supports_fpsimd())
		return;
	barrier();
	set_tsk_thread_flag(t, TIF_FOREIGN_FPSTATE);

	barrier();
}

/*
 * Invalidate any task's FPSIMD state that is present on this cpu.
 * The FPSIMD context should be acquired with get_cpu_fpsimd_context()
 * before calling this function.
 */
static void fpsimd_flush_cpu_state(void)
{
	WARN_ON(!system_supports_fpsimd());
	__this_cpu_write(fpsimd_last_state.st, NULL);

	/*
	 * Leaving streaming mode enabled will cause issues for any kernel
	 * NEON and leaving streaming mode or ZA enabled may increase power
	 * consumption.
	 */
	if (system_supports_sme())
		sme_smstop();

	set_thread_flag(TIF_FOREIGN_FPSTATE);
}
```

* `TIF_XXX_XXX`

  ```c
  #define TIF_FOREIGN_FPSTATE	3	/* CPU's FP state is not current's */
  #define TIF_SVE			23	/* Scalable Vector Extension in use */
  #define TIF_SME			27	/* SME in use */
  #define TIF_KERNEL_FPSTATE	29	/* Task is in a kernel mode FPSIMD section */
  
  //fpsimd将flag作为thread_info, vector目前作为thread_struct中的字段riscvs_v_flags。
  ```

* `fpsimd_save_user_state`

  ```c
  vec_set_vector_length
      +-> fpsimd_save_user_state
  fpsimd_thread_switch
      +-> fpsimd_save_user_state
  fpsimd_preserve_current_state
      +-> fpsimd_save_user_state
  fpsimd_save_and_flush_cpu_state
      +-> fpsimd_save_user_state
  kernel_neon_begin
     	+-> if (test_thread_flag(TIF_KERNEL_FPSTATE)) {
  			BUG_ON(IS_ENABLED(CONFIG_PREEMPT_RT) || !in_serving_softirq());
  			fpsimd_save_kernel_state(current);
  		} else {
  			fpsimd_save_user_state();
      	}
  ```

* `sve_init_regs`

  ```c
  do_sve_acc
      +-> sve_init_regs
  ```

* `fpsimd_thread_switch`

  ```c
  __switch_to
      +-> fpsimd_thread_switch
  ```

* `fpsimd_restore_current_state`

  ```c
  void do_notify_resume(struct pt_regs *regs, unsigned long thread_flags)
  {
  	do {
  		if (thread_flags & _TIF_NEED_RESCHED) {
  			/* Unmask Debug and SError for the next task */
  			local_daif_restore(DAIF_PROCCTX_NOIRQ);
  
  			schedule();
  		} else {
              //...
  			if (thread_flags & _TIF_FOREIGN_FPSTATE)
  				fpsimd_restore_current_state();
  		}
  
  		local_daif_mask();
  		thread_flags = read_thread_flags();
  	} while (thread_flags & _TIF_WORK_MASK);
  }
  ```

* `fpsimd_update_current_state`

  ```c
  restore_sigframe
  	+-> restore_fpsimd_context/restore_sve_fpsimd_context
      	+-> fpsimd_update_current_state
  ```

* `fpsimd_flush_task_state`

  ```c
  //arch/arm64/kernel/fpsimd.c
  vec_set_vector_length
      +-> fpsimd_flush_task_state
  
  begin_new_exec
      +-> flush_thread  
      	+-> fpsimd_flush_thread
      		+-> fpsimd_flush_task_state
      
  //arch/arm64/kernel/process.c
  copy_thread
      +-> fpsimd_flush_task_state
  
  //arch/arm64/kernel/ptrace.c
  fpr_set
  sve_set_common
  za/zt_set
  compat_vfp_set
      +-> fpsimd_flush_task_state
  
  //arch/arm64/kernel/signal.c
  restore_sve_fpsimd_context
  restore_za_context
  restore_zt_context
      +-> fpsimd_flush_task_state
  ```

* `fpsimd_flush_cpu_state`

  ```c
  fpsimd_cpu_pm_notifier
  	+-> fpsimd_save_and_flush_cpu_state
      	+-> fpsimd_flush_cpu_state
      
  kernel_neon_begin
      +-> fpsimd_flush_cpu_state
      
  #ifdef CONFIG_CPU_PM
  static int fpsimd_cpu_pm_notifier(struct notifier_block *self,
  				  unsigned long cmd, void *v)
  {
  	switch (cmd) {
  	case CPU_PM_ENTER:
  		fpsimd_save_and_flush_cpu_state();
  		break;
  	case CPU_PM_EXIT:
  		break;
  	case CPU_PM_ENTER_FAILED:
  	default:
  		return NOTIFY_DONE;
  	}
  	return NOTIFY_OK;
  }
  ```

  



## 2.4 virtualization





