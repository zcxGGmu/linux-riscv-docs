# -1 参考

* [PATCH -next v21 00/27\] riscv: Add vector ISA support - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230605110724.21391-1-andy.chiu@sifive.com/#r)
* [v11, 00/10\] riscv: support kernel-mode Vector - Andy Chiu](https://lore.kernel.org/all/20240115055929.4736-1-andy.chiu@sifive.com/)



# 0 计划/思考

- [ ] patch-analysis mainline

  - [ ] kernel/kvm context switch🎈

  - [ ] 分支展开，逻辑分析，从 `entry.S: riscv_v_start_kernel_context(bool *is_nested)` 开始：

    ```c
    if (!kvstate->datap)
    		return -ENOENT;
    //...
    return 0;
    ```

- [ ] selftests补充

  - [x] vector-signal: 社区review, [riscv: selftests: Add signal handling vector tests](https://lore.kernel.org/all/20240403-vector_sigreturn_tests-v1-1-2e68b7a3b8d7@rivosinc.com/)
  - [ ] vector-ptrace
  - [ ] vector-stress
  - [ ] kernel-mode-vector/preemptible
  - [ ] kvm: selftests: get-reg-list.c🎈

- [ ] x86/arm64 diff

  - [ ] `PR_*` flag🎈

    ```c
    #define PR_SVE_SET_VL			50	/* set task vector length */
    # define PR_SVE_SET_VL_ONEXEC		(1 << 18) /* defer effect until exec */
    #define PR_SVE_GET_VL	
    ```

    为什么rvv没有提供这样的接口？





# 1 RISC-V Vector HW





# 2 RISC-V Vector Kernel/KVM Support-Base

## 2.1 kernel-support

这个补丁集基于矢量1.0规范实现了在riscv Linux内核中添加矢量支持。对于此实现，有以下一些假设。

1. 我们假设系统中所有harts（硬件线程）具有相同的ISA（指令集架构）。
2. 默认情况下，我们在内核和用户空间都禁用了矢量支持[1]。只有在非法指令陷阱发生时，即用户实际开始执行矢量指令（首次使用陷阱[2]），才会启用用户的矢量支持。
3. 我们检测“riscv,isa”以确定是否支持矢量指令。

我们在结构体`thread_struct`中定义了一个新的结构体`__riscv_v_ext_state`，用于保存和恢复与矢量相关的寄存器。它适用于内核空间和用户空间。
- 在内核空间中，`__riscv_v_ext_state`中的`datap`指针将被分配用于保存矢量寄存器。
- 在用户空间中：
  - 在用户空间的信号处理程序中，该结构体放置在`__riscv_ctx_hdr`之后，它嵌入在fp保留区。这是为了避免ABI（应用程序二进制接口）破坏[2]。`datap`指针指向`__riscv_v_ext_state`的末尾。
  - 在ptrace中，数据将放入`ubuf`中，我们使用`riscv_vr_get()`/`riscv_vr_set()`从/向其中获取或设置`__riscv_v_ext_state`数据结构，`datap`指针将被清零，矢量寄存器将复制到`ubuf`中`__riscv_v_ext_state`结构体之后的地址。

这个补丁集已经重新基于v6.4-rc1版本并通过运行多个矢量程序同时测试。它在一个测试中正确地传递了信号，在信号处理程序中可以看到有效的`ucontext_t`，并且从中返回了正确的V上下文。ptrace接口通过`PTRACE_{GET,SET}REGSET`进行测试。最后，KVM通过在使用相同内核镜像的guest中运行上述测试进行了测试。所有测试均在rv64gcv virt QEMU上完成。

此外，为了应对在[4]中提到的ABI稳定性潜在影响，我们实现了`prctl()`和`sysctl`接口来控制用户空间的矢量兼容性。可以通过kselftest测试`prctl`接口，提供在该系列末尾的测试。默认情况下启用用户空间的矢量支持，因为这可能是ABI破坏的理论情况，并且提供了早期发现破坏（如果有的话）的机会，开发人员可以玩转V[5]。

源码树：
https://github.com/sifive/riscv-linux/tree/riscv/for-next/vector-v20

链接：
- [1] https://lore.kernel.org/all/20220921214439.1491510-17-stillson@rivosinc.com/
- [2] https://lore.kernel.org/all/73c0124c-4794-6e40-460c-b26df407f322@rivosinc.com/T/#u
- [3] https://lore.kernel.org/all/20230128082847.3055316-1-apatel@ventanamicro.com/
- [4] https://inbox.sourceware.org/libc-alpha/87leinq5wg.fsf@all.your.base.are.belong.to.us/
- [5] https://lore.kernel.org/all/mhng-8554b236-c9d4-4590-8941-ed7ca5316d18@palmer-ri-x1c9a/

---

这组PATCH，按功能归类如下：

* `non-functional patch`
  * [[PATCH -next v20 24/26\] riscv: Add documentation for Vector - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-25-andy.chiu@sifive.com/)
* `compiler support`
  * [[PATCH -next v20 22/26\] riscv: detect assembler support for .option arch - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-23-andy.chiu@sifive.com/)
* `enable Vector code to be built `
  * [[PATCH -next v20 23/26\] riscv: Enable Vector code to be built - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-24-andy.chiu@sifive.com/)

* `vector hwprobe`
  * [[PATCH -next v20 02/26\] riscv: Extending cpufeature.c to detect V-extension - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-3-andy.chiu@sifive.com/)
  * [[PATCH -next v20 03/26\] riscv: hwprobe: Add support for probing V in RISCV_HWPROBE_KEY_IMA_EXT_0 - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-4-andy.chiu@sifive.com/)
* `bootup vector set`
  * [PATCH -next v20 05/26\] riscv: Clear vector regfile on bootup - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-6-andy.chiu@sifive.com/)
* `kernel-mode vector disable`：后续补丁将支持内核模式下的向量行为
  * [[PATCH -next v20 06/26\] riscv: Disable Vector Instructions for kernel itself - Andy Chiu](https://lore.kernel.org/all/20230518161949.11203-7-andy.chiu@sifive.com/)
* `vector smp regs size set`
  * [[PATCH -next v20 08/26\] riscv: Introduce riscv_v_vsize to record size of Vector context - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-9-andy.chiu@sifive.com/)
* `vector first-use trap`
  * [[PATCH -next v20 04/26\] riscv: Add new csr defines related to vector extension - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-5-andy.chiu@sifive.com/)
  * [[PATCH -next v20 11/26\] riscv: Allocate user's vector context in the first-use trap - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-12-andy.chiu@sifive.com/)
* `vector per-task context switch`
  * [[PATCH -next v20 07/26\] riscv: Introduce Vector enable/disable helpers - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-8-andy.chiu@sifive.com/)
  * [[PATCH -next v20 09/26\] riscv: Introduce struct/helpers to save/restore per-task Vector state - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-10-andy.chiu@sifive.com/)
  * [[PATCH -next v20 10/26\] riscv: Add task switch support for vector - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-11-andy.chiu@sifive.com/)
  * [[PATCH -next v20 17/26\] riscv: prevent stack corruption by reserving task_pt_regs(p) early - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-18-andy.chiu@sifive.com/)
* `ptrace vector`
  * [[PATCH -next v20 12/26\] riscv: Add ptrace vector support - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-13-andy.chiu@sifive.com/)
* `vector signal handle `
  * [[PATCH -next v20 13/26\] riscv: signal: check fp-reserved words unconditionally - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-14-andy.chiu@sifive.com/)
  * [[PATCH -next v20 14/26\] riscv: signal: Add sigcontext save/restore for vector - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-15-andy.chiu@sifive.com/)
  * [[PATCH -next v20 15/26\] riscv: signal: Report signal frame size to userspace via auxv - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-16-andy.chiu@sifive.com/)
  * [[PATCH -next v20 16/26\] riscv: signal: validate altstack to reflect Vector - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-17-andy.chiu@sifive.com/)

* `userapce vector prctl`
  * [[PATCH -next v20 20/26\] riscv: Add prctl controls for userspace vector management - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-21-andy.chiu@sifive.com/)
  * [[PATCH -next v20 21/26\] riscv: Add sysctl to set the default vector rule for new processes - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-22-andy.chiu@sifive.com/)
  * [[PATCH -next v20 25/26\] selftests: Test RISC-V Vector prctl interface - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-26-andy.chiu@sifive.com/)
  * [[PATCH -next v20 26/26\] selftests: add .gitignore file for RISC-V hwprobe - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-27-andy.chiu@sifive.com/)

---

### 1) documention

本文档概述了Linux为支持RISC-V矢量扩展，提供给用户空间的接口。

#### `prctl`

新增了两个 `prctl` 调用，以允许用户态程序管理用户空间中，矢量使用的启用状态：

- `prctl(PR_RISCV_V_SET_CONTROL, unsigned long arg)`

  设置调用线程的矢量启用状态，其中控制参数由两个2位的启用状态和一个继承模式位组成。调用进程的其他线程不受影响。启用状态是一个`tri-state` 值，每个占用控制参数的2位空间：

  ```assembly
  # define PR_RISCV_V_VSTATE_CTRL_DEFAULT		0
  # define PR_RISCV_V_VSTATE_CTRL_OFF		1
  # define PR_RISCV_V_VSTATE_CTRL_ON		2
  ```

  - `PR_RISCV_V_VSTATE_CTRL_DEFAULT`

    在execve()时使用系统范围的默认启用状态。系统范围的默认设置，可以通过sysctl接口控制（见下文的sysctl部分）。

  - `PR_RISCV_V_VSTATE_CTRL_ON`

    允许线程运行矢量指令。

  - `PR_RISCV_V_VSTATE_CTRL_OFF`

    不允许矢量指令。在这种情况下，执行矢量指令会导致线程终止。

  控制参数是一个5位值，由3部分组成，分别由3个掩码访问：

  ```assembly
  # define PR_RISCV_V_VSTATE_CTRL_CUR_MASK	0x3
  # define PR_RISCV_V_VSTATE_CTRL_NEXT_MASK	0xc
  # define PR_RISCV_V_VSTATE_CTRL_INHERIT		(1 << 4)
  # define PR_RISCV_V_VSTATE_CTRL_MASK		0x1f
  ```

  分别表示bit[1:0]、bit[3:2]和bit[4]：

  - `PR_RISCV_V_VSTATE_CTRL_CUR_MASK => bit[1:0]`

    表示调用线程的矢量启用状态。调用线程一旦启用了矢量，就不能关闭矢量。如果当前启用状态不是关闭，并且在此掩码中设置了`PR_RISCV_V_VSTATE_CTRL_OFF`，则prctl()调用会以EPERM失败。在此处设置 `PR_RISCV_V_VSTATE_CTRL_DEFAULT` 无效，只会恢复原始启用状态。

  - `PR_RISCV_V_VSTATE_CTRL_NEXT_MASK => bit[3:2]`

    表示调用线程，在下一个execve()系统调用中的矢量启用设置。如果在此掩码中使用 `PR_RISCV_V_VSTATE_CTRL_DEFAULT`，则启用状态将由execve()发生时的系统范围启用状态决定。

  - `PR_RISCV_V_VSTATE_CTRL_INHERIT => bit[4]`

    `PR_RISCV_V_VSTATE_CTRL_NEXT_MASK`设置的继承模式。如果设置了该位，则后续的execve()将不会清除`PR_RISCV_V_VSTATE_CTRL_NEXT_MASK` 和 `PR_RISCV_V_VSTATE_CTRL_INHERIT` 中的设置。此设置在系统范围默认值更改时，仍然有效。

  > 返回值：
  >
  > - 成功时返回0；
  > - EINVAL：不支持矢量或当前或下一个掩码的启用状态无效；
  > - EPERM：在调用线程启用了矢量的情况下，在 `PR_RISCV_V_VSTATE_CTRL_CUR_MASK` 中关闭矢量。
  >
  > 成功时：
  >
  > - `PR_RISCV_V_VSTATE_CTRL_CUR_MASK` 的有效设置立即生效。`PR_RISCV_V_VSTATE_CTRL_NEXT_MASK` 中指定的启用状态将在下一个execve()调用时生效，或者如果设置了 `PR_RISCV_V_VSTATE_CTRL_INHERIT` 位，则在所有后续的execve()调用中生效。
  > - 每次成功调用，都会覆盖调用线程的先前设置。

- `prctl(PR_RISCV_V_GET_CONTROL)`

  获取调用线程的相同矢量启用状态。下一个execve()调用和继承位的设置，都会被OR在一起。

  > 返回值：
  >
  > - 成功时返回非负值；
  > - EINVAL：不支持矢量。

---

#### `sysctl`

为了缓解信号栈扩展对ABI的影响，提供了一种策略机制，允许管理员、发行版维护者和开发人员通过 `sysctl` 接口控制用户空间进程的默认矢量启用状态：

- `/proc/sys/abi/riscv_v_default_allow`

  向此文件写入0或1的文本，表示值以设置新启动的用户空间程序的默认系统启用状态。有效值为：

  - `0`：不允许新进程执行矢量代码；
  - `1`：允许新进程执行矢量代码；

  读取此文件，返回当前的系统默认启用状态。

  在每次execve()调用时，新进程的启用状态将设置为系统默认值，除非：

  - 调用进程设置了`PR_RISCV_V_VSTATE_CTRL_INHERIT`，并且`PR_RISCV_V_VSTATE_CTRL_NEXT_MASK`中的设置不是`PR_RISCV_V_VSTATE_CTRL_DEFAULT`；
  - `PR_RISCV_V_VSTATE_CTRL_NEXT_MASK` 中的设置，不是 `PR_RISCV_V_VSTATE_CTRL_DEFAULT`；

  修改系统默认启用状态，不会影响不调用execve()的任何现有进程或线程的启用状态。

---

### 2) enable Vector code to be built

首先，它检测构建代码所需的工具链支持。然后，它提供了一个选项，用于设置：**是否在用户空间隐式启用矢量支持。**

```c
+config TOOLCHAIN_HAS_V
+	bool
+	default y
+	depends on !64BIT || $(cc-option,-mabi=lp64 -march=rv64iv)
+	depends on !32BIT || $(cc-option,-mabi=ilp32 -march=rv32iv)
+	depends on LLD_VERSION >= 140000 || LD_VERSION >= 23800
+	depends on AS_HAS_OPTION_ARCH
+
+config RISCV_ISA_V
+	bool "VECTOR extension support"
+	depends on TOOLCHAIN_HAS_V
+	depends on FPU
+	select DYNAMIC_SIGFRAME
+	default y
+	help
+	  Say N here if you want to disable all vector related procedure
+	  in the kernel.
+
+	  If you don't know what to do here, say Y.
+
+config RISCV_ISA_V_DEFAULT_ENABLE
+	bool "Enable userspace Vector by default"
+	depends on RISCV_ISA_V
+	default y
+	help
+	  Say Y here if you want to enable Vector in userspace by default.
+	  Otherwise, userspace has to make explicit prctl() call to enable
+	  Vector, or enable it via the sysctl interface.
+
+	  If you don't know what to do here, say Y.
+
    diff --git a/arch/riscv/Makefile b/arch/riscv/Makefile
index 0fb256bf8270..6ec6d52a4180 100644
--- a/arch/riscv/Makefile
+++ b/arch/riscv/Makefile
@@ -60,6 +60,7 @@ riscv-march-$(CONFIG_ARCH_RV32I)	:= rv32ima
 riscv-march-$(CONFIG_ARCH_RV64I)	:= rv64ima
 riscv-march-$(CONFIG_FPU)		:= $(riscv-march-y)fd
 riscv-march-$(CONFIG_RISCV_ISA_C)	:= $(riscv-march-y)c
+riscv-march-$(CONFIG_RISCV_ISA_V)	:= $(riscv-march-y)v
-KBUILD_CFLAGS += -march=$(subst fd,,$(riscv-march-y))
+# Remove F,D,V from isa string for all. Keep extensions between "fd" and "v" by
+# matching non-v and non-multi-letter extensions out with the filter ([^v_]*)
+KBUILD_CFLAGS += -march=$(shell echo $(riscv-march-y) | sed -E 's/(rv32ima|rv64ima)fd([^v_]*)v?/\1\2/')
```

---

```c
static bool riscv_v_implicit_uacc = IS_ENABLED(CONFIG_RISCV_ISA_V_DEFAULT_ENABLE);
```

### 3) vector hwprobe

* [hwprobe.rst - Documentation/arch/riscv/hwprobe.rst - Linux source code (v6.9.1) - Bootlin](https://elixir.bootlin.com/linux/latest/source/Documentation/arch/riscv/hwprobe.rst)

* [[PATCH -next v20 02/26\] riscv: Extending cpufeature.c to detect V-extension - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-3-andy.chiu@sifive.com/)
* [[PATCH -next v20 03/26\] riscv: hwprobe: Add support for probing V in RISCV_HWPROBE_KEY_IMA_EXT_0 - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-4-andy.chiu@sifive.com/)

---

> **The diff between hwcap and ISA ？**
>
> ```c
> // arch/riscv/include/asm/hwcap.h
> #define RISCV_ISA_EXT_a		('a' - 'a')
> #define RISCV_ISA_EXT_c		('c' - 'a')
> #define RISCV_ISA_EXT_d		('d' - 'a')
> #define RISCV_ISA_EXT_f		('f' - 'a')
> #define RISCV_ISA_EXT_h		('h' - 'a')
> #define RISCV_ISA_EXT_i		('i' - 'a')
> #define RISCV_ISA_EXT_m		('m' - 'a')
> #define RISCV_ISA_EXT_q		('q' - 'a')
> #define RISCV_ISA_EXT_v		('v' - 'a')
> 
> // arch/riscv/include/uapi/asm/hwcap.h
> #define COMPAT_HWCAP_ISA_I	(1 << ('I' - 'A'))
> #define COMPAT_HWCAP_ISA_M	(1 << ('M' - 'A'))
> #define COMPAT_HWCAP_ISA_A	(1 << ('A' - 'A'))
> #define COMPAT_HWCAP_ISA_F	(1 << ('F' - 'A'))
> #define COMPAT_HWCAP_ISA_D	(1 << ('D' - 'A'))
> #define COMPAT_HWCAP_ISA_C	(1 << ('C' - 'A'))
> #define COMPAT_HWCAP_ISA_V	(1 << ('V' - 'A'))
> 
> void __init riscv_fill_hwcap(void) 
> {
>     if (elf_hwcap & COMPAT_HWCAP_ISA_V) {
> 		riscv_v_setup_vsize();
> 		/*
> 		 * ISA string in device tree might have 'v' flag, but
> 		 * CONFIG_RISCV_ISA_V is disabled in kernel.
> 		 * Clear V flag in elf_hwcap if CONFIG_RISCV_ISA_V is disabled.
> 		 */
> 		if (!IS_ENABLED(CONFIG_RISCV_ISA_V))
> 			elf_hwcap &= ~COMPAT_HWCAP_ISA_V;
> 	}
> }
> ```
>
> 从 `riscv_fill_hwcap` 函数中，可以明确区分出 hwcap 和 ISA 宏的不同语义，以vector为例，`COMPAT_HWCAP_ISA_V` 由内核和硬件共同决定，即使硬件支持vector，内核如果关闭 `CONFIG_RISCV_ISA_V`，最终系统无法支持用户态程序使用vector操作。

```c
do_riscv_hwprobe
    +-> hwprobe_get_values
    +->	hwprobe_get_cpus
        +-> hwprobe_one_pair
            +-> if (has_vector()) //jump
                    pair->value |= RISCV_HWPROBE_IMA_V;

has_vector
    +-> riscv_has_extension_unlikely(RISCV_ISA_EXT_v)
    	+-> __riscv_isa_extension_available(NULL, ext)
bool __riscv_isa_extension_available(const unsigned long *isa_bitmap, unsigned int bit)
{
	const unsigned long *bmap = (isa_bitmap) ? isa_bitmap : riscv_isa;

	if (bit >= RISCV_ISA_EXT_MAX)
		return false;

	return test_bit(bit, bmap) ? true : false;
}

//where is riscv_isa from?
/* Host ISA bitmap */
static DECLARE_BITMAP(riscv_isa, RISCV_ISA_EXT_MAX) __read_mostly;
/* Per-cpu ISA extensions. */
struct riscv_isainfo hart_isa[NR_CPUS];

start_kernel
    +-> setup_arch(&command_line);
		/*
			isa2hwcap['i' - 'a'] = COMPAT_HWCAP_ISA_I;
            isa2hwcap['m' - 'a'] = COMPAT_HWCAP_ISA_M;
            isa2hwcap['a' - 'a'] = COMPAT_HWCAP_ISA_A;
            isa2hwcap['f' - 'a'] = COMPAT_HWCAP_ISA_F;
            isa2hwcap['d' - 'a'] = COMPAT_HWCAP_ISA_D;
            isa2hwcap['c' - 'a'] = COMPAT_HWCAP_ISA_C;
            isa2hwcap['v' - 'a'] = COMPAT_HWCAP_ISA_V;
		*/
		+-> riscv_fill_hwcap(void)
    		+-> riscv_fill_hwcap_from_isa_string(isa2hwcap);
				+-> for_each_possible_cpu(cpu)
                    +-> struct riscv_isainfo *isainfo = &hart_isa[cpu];
					/* 通过解析指定的cpu-node，进行物理hart的isa写入 */
					+-> node = of_cpu_device_node_get(cpu);
                        rc = of_property_read_string(node, "riscv,isa", &isa);
					/* hart_isa/isainfo在这里配置*/
					+-> riscv_parse_isa_string(&this_hwcap, isainfo, isa2hwcap, isa); //此处的isa是从设备树中解析出来的
						+-> if (riscv_isa_extension_check(nr)) //目前只有RISCV_ISA_EXT_ZICBOM/RISCV_ISA_EXT_ZICBOZ
							+-> *this_hwcap |= isa2hwcap[nr];
							+-> set_bit(nr, isainfo->isa); //hart_isa初始化
						+-> match_isa_ext(&riscv_isa_ext[i], ext, ext_end, isainfo);
					------------------------------------------------------------------> //hart信息检测结束
					/* elf_hwcap初始化 */
					if (elf_hwcap)
						elf_hwcap &= this_hwcap;
					else
						elf_hwcap = this_hwcap;
					/* riscv_isa根据实际的硬件hart_isa进行设置 */
                    +-> if (bitmap_empty(riscv_isa, RISCV_ISA_EXT_MAX))
                            bitmap_copy(riscv_isa, isainfo->isa, RISCV_ISA_EXT_MAX);
                        else
                            bitmap_and(riscv_isa, riscv_isa, isainfo->isa, RISCV_ISA_EXT_MAX); 
```

### 4) bootup vector set

[PATCH -next v20 05/26\] riscv: Clear vector regfile on bootup - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-6-andy.chiu@sifive.com/)

如果内核使能了vector，初始化vector相关寄存器：

```c
diff --git a/arch/riscv/kernel/head.S b/arch/riscv/kernel/head.S
index 4bf6c449d78b..3fd6a4bd9c3e 100644
--- a/arch/riscv/kernel/head.S
+++ b/arch/riscv/kernel/head.S
@@ -392,7 +392,7 @@ ENTRY(reset_regs)
 #ifdef CONFIG_FPU
 	csrr	t0, CSR_MISA
 	andi	t0, t0, (COMPAT_HWCAP_ISA_F | COMPAT_HWCAP_ISA_D)
-	beqz	t0, .Lreset_regs_done
+	beqz	t0, .Lreset_regs_done_fpu
 
 	li	t1, SR_FS
 	csrs	CSR_STATUS, t1
@@ -430,8 +430,31 @@ ENTRY(reset_regs)
 	fmv.s.x	f31, zero
 	csrw	fcsr, 0
 	/* note that the caller must clear SR_FS */
+.Lreset_regs_done_fpu:
 #endif /* CONFIG_FPU */
-.Lreset_regs_done:
+
+#ifdef CONFIG_RISCV_ISA_V
+	csrr	t0, CSR_MISA
+	li	t1, COMPAT_HWCAP_ISA_V
+	and	t0, t0, t1
+	beqz	t0, .Lreset_regs_done_vector
+
+	/*
+	 * Clear vector registers and reset vcsr
+	 * VLMAX has a defined value, VLEN is a constant,
+	 * and this form of vsetvli is defined to set vl to VLMAX.
+	 */
+	li	t1, SR_VS
+	csrs	CSR_STATUS, t1
+	csrs	CSR_VCSR, x0
+	vsetvli t1, x0, e8, m8, ta, ma
+	vmv.v.i v0, 0
+	vmv.v.i v8, 0
+	vmv.v.i v16, 0
+	vmv.v.i v24, 0
+	/* note that the caller must clear SR_VS */
+.Lreset_regs_done_vector:
+#endif /* CONFIG_RISCV_ISA_V */
```

### 5) kernel-mode vector disable

[[PATCH -next v20 06/26\] riscv: Disable Vector Instructions for kernel itself - Andy Chiu](https://lore.kernel.org/all/20230518161949.11203-7-andy.chiu@sifive.com/)

[在Linux内核中使用浮点寄存器和SIMD寄存器有什么要求?_fpsimd-CSDN博客](https://blog.csdn.net/yuxiaochen99/article/details/133339189)

在内核模式的入口处禁用矢量指令的执行。这有助于发现内核空间中非法使用矢量指令的情况，这与FPU（浮点处理单元）的处理方式类似。后续补丁将支持内核模式下的浮点/向量行为，但这必须要遵循特定的规则，否则将破坏用户态的寄存器值。

```c
--- a/arch/riscv/kernel/entry.S
+++ b/arch/riscv/kernel/entry.S
@@ -48,10 +48,10 @@ _save_context:
 	 * Disable user-mode memory access as it should only be set in the
 	 * actual user copy routines.
 	 *
-	 * Disable the FPU to detect illegal usage of floating point in kernel
-	 * space.
+	 * Disable the FPU/Vector to detect illegal usage of floating point
+	 * or vector in kernel space.
 	 */
-	li t0, SR_SUM | SR_FS
+	li t0, SR_SUM | SR_FS_VS
 
 	REG_L s0, TASK_TI_USER_SP(tp)
 	csrrc s1, CSR_STATUS, t0
diff --git a/arch/riscv/kernel/head.S b/arch/riscv/kernel/head.S
index 3fd6a4bd9c3e..e16bb2185d55 100644
--- a/arch/riscv/kernel/head.S
+++ b/arch/riscv/kernel/head.S
@@ -140,10 +140,10 @@ secondary_start_sbi:
 	.option pop
 
 	/*
-	 * Disable FPU to detect illegal usage of
-	 * floating point in kernel space
+	 * Disable FPU & VECTOR to detect illegal usage of
+	 * floating point or vector in kernel space
 	 */
-	li t0, SR_FS
+	li t0, SR_FS_VS
 	csrc CSR_STATUS, t0
 
 	/* Set trap vector to spin forever to help debug */
@@ -234,10 +234,10 @@ pmp_done:
 .option pop
 
 	/*
-	 * Disable FPU to detect illegal usage of
-	 * floating point in kernel space
+	 * Disable FPU & VECTOR to detect illegal usage of
+	 * floating point or vector in kernel space
 	 */
-	li t0, SR_FS
+	li t0, SR_FS_VS
 	csrc CSR_STATUS, t0
```

### 6) vector smp regs size set

[[PATCH -next v20 08/26\] riscv: Introduce riscv_v_vsize to record size of Vector context - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-9-andy.chiu@sifive.com/)

[多核启动基本逻辑分析 | Sherlock's blog (wangzhou.github.io)](https://wangzhou.github.io/多核启动基本逻辑分析/)

此补丁用于检测CPU矢量寄存器的大小，并使用 `riscv_v_vsize`，保存所有矢量寄存器的大小。它假设在 SMP 系统中，所有harts具有相同的能力。如果某个核心，检测到的 `VLENB`（矢量寄存器长度字节数）与引导核心的不同，则会发出警告并关闭用户空间的矢量支持。

```c
//从核的内核启动地址并不是_start，而是secondary_start_sbi
secondary_start_sbi
    +-> smp_callin
    	...
```

```c
--- a/arch/riscv/kernel/smpboot.c
+++ b/arch/riscv/kernel/smpboot.c
@@ -31,6 +31,8 @@
 #include <asm/tlbflush.h>
 #include <asm/sections.h>
 #include <asm/smp.h>
+#include <uapi/asm/hwcap.h>
+#include <asm/vector.h>
 
 #include "head.h"
 
@@ -169,6 +171,11 @@ asmlinkage __visible void smp_callin(void)
 	set_cpu_online(curr_cpuid, 1);
 	probe_vendor_features(curr_cpuid);
 
+	if (has_vector()) {
+		if (riscv_v_setup_vsize())
+			elf_hwcap &= ~COMPAT_HWCAP_ISA_V;
+	}
+
--- /dev/null
+++ b/arch/riscv/kernel/vector.c
@@ -0,0 +1,36 @@
+// SPDX-License-Identifier: GPL-2.0-or-later
+/*
+ * Copyright (C) 2023 SiFive
+ * Author: Andy Chiu <andy.chiu@sifive.com>
+ */
+#include <linux/export.h>
+
+#include <asm/vector.h>
+#include <asm/csr.h>
+#include <asm/elf.h>
+#include <asm/bug.h>
+
+unsigned long riscv_v_vsize __read_mostly;
+EXPORT_SYMBOL_GPL(riscv_v_vsize);
+
+int riscv_v_setup_vsize(void)
+{
+	unsigned long this_vsize;
+
+	/* There are 32 vector registers with vlenb length. */
+	riscv_v_enable();
+	this_vsize = csr_read(CSR_VLENB) * 32;
+	riscv_v_disable();
+
+	if (!riscv_v_vsize) {
+		riscv_v_vsize = this_vsize;
+		return 0;
+	}
+
+	if (riscv_v_vsize != this_vsize) {
+		WARN(1, "RISCV_ISA_V only supports one vlenb on SMP systems");
+		return -EOPNOTSUPP;
+	}
+
+	return 0;
+}
```

----

### 7) vector first-use trap

* [[PATCH -next v20 04/26\] riscv: Add new csr defines related to vector extension - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-5-andy.chiu@sifive.com/)
* [[PATCH -next v20 11/26\] riscv: Allocate user's vector context in the first-use trap - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-12-andy.chiu@sifive.com/)

默认情况下，所有用户进程的矢量单元都是禁用的。因此，当进程第一次使用矢量指令时，会触发一个陷阱（非法指令），进入内核。只有在那之后，内核才会为该用户进程分配矢量上下文，并开始管理该上下文。

> `riscv-priv-3.1.6.6 mstatus.FS/VS`
>
> ***When an extension’s status is set to Off, any instruction that attempts to read or write the corresponding state will cause an illegal instruction exception.*** When the status is Initial, the corresponding state should have an initial constant value. When the status is Clean, the corresponding state is potentially different from the initial value, but matches the last value stored on a context swap. When the status is Dirty, the corresponding state has potentially been modified since the last context save.

```c
--- a/arch/riscv/include/asm/csr.h
+++ b/arch/riscv/include/asm/csr.h
@@ -24,16 +24,24 @@
 #define SR_FS_CLEAN	_AC(0x00004000, UL)
 #define SR_FS_DIRTY	_AC(0x00006000, UL)
 
+#define SR_VS		_AC(0x00000600, UL) /* Vector Status */
+#define SR_VS_OFF	_AC(0x00000000, UL)
+#define SR_VS_INITIAL	_AC(0x00000200, UL)
+#define SR_VS_CLEAN	_AC(0x00000400, UL)
+#define SR_VS_DIRTY	_AC(0x00000600, UL)
+
 #define SR_XS		_AC(0x00018000, UL) /* Extension Status */
 #define SR_XS_OFF	_AC(0x00000000, UL)
 #define SR_XS_INITIAL	_AC(0x00008000, UL)
 #define SR_XS_CLEAN	_AC(0x00010000, UL)
 #define SR_XS_DIRTY	_AC(0x00018000, UL)
 
+#define SR_FS_VS	(SR_FS | SR_VS) /* Vector and Floating-Point Unit */
+
 #ifndef CONFIG_64BIT
-#define SR_SD		_AC(0x80000000, UL) /* FS/XS dirty */
+#define SR_SD		_AC(0x80000000, UL) /* FS/VS/XS dirty */
 #else
-#define SR_SD		_AC(0x8000000000000000, UL) /* FS/XS dirty */
+#define SR_SD		_AC(0x8000000000000000, UL) /* FS/VS/XS dirty */
 #endif
 
 #ifdef CONFIG_64BIT
@@ -375,6 +383,12 @@
 #define CSR_MVIPH		0x319
 #define CSR_MIPH		0x354
 
+#define CSR_VSTART		0x8
+#define CSR_VCSR		0xf
+#define CSR_VL			0xc20
+#define CSR_VTYPE		0xc21
+#define CSR_VLENB		0xc22
+
 #ifdef CONFIG_RISCV_M_MODE
 # define CSR_STATUS	CSR_MSTATUS
 # define CSR_IE		CSR_MIE
```

```c
do_trap_insn_illegal(struct pt_regs *regs)
    +-> riscv_v_first_use_handler(regs);

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
	if (riscv_v_thread_zalloc(riscv_v_user_cachep, &current->thread.vstate)) {
		force_sig(SIGBUS);
		return true;
	}
	riscv_v_vstate_on(regs);
	return true;
}
```

```c
--- a/arch/riscv/kernel/traps.c
+++ b/arch/riscv/kernel/traps.c
@@ -26,6 +26,7 @@
 #include <asm/ptrace.h>
 #include <asm/syscall.h>
 #include <asm/thread_info.h>
+#include <asm/vector.h>
 
 int show_unhandled_signals = 1;
 
@@ -145,8 +146,29 @@ DO_ERROR_INFO(do_trap_insn_misaligned,
 	SIGBUS, BUS_ADRALN, "instruction address misaligned");
 DO_ERROR_INFO(do_trap_insn_fault,
 	SIGSEGV, SEGV_ACCERR, "instruction access fault");
-DO_ERROR_INFO(do_trap_insn_illegal,
-	SIGILL, ILL_ILLOPC, "illegal instruction");
+
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
+
 DO_ERROR_INFO(do_trap_load_fault,
 	SIGSEGV, SEGV_ACCERR, "load access fault");
 #ifndef CONFIG_RISCV_M_MODE
diff --git a/arch/riscv/kernel/vector.c b/arch/riscv/kernel/vector.c
index 120f1ce9abf9..0080798e8d2e 100644
--- a/arch/riscv/kernel/vector.c
+++ b/arch/riscv/kernel/vector.c
@@ -4,10 +4,19 @@
  * Author: Andy Chiu <andy.chiu@sifive.com>
  */
 #include <linux/export.h>
+#include <linux/sched/signal.h>
+#include <linux/types.h>
+#include <linux/slab.h>
+#include <linux/sched.h>
+#include <linux/uaccess.h>
 
+#include <asm/thread_info.h>
+#include <asm/processor.h>
+#include <asm/insn.h>
 #include <asm/vector.h>
 #include <asm/csr.h>
 #include <asm/elf.h>
+#include <asm/ptrace.h>
 #include <asm/bug.h>
 
 unsigned long riscv_v_vsize __read_mostly;
@@ -34,3 +43,89 @@ int riscv_v_setup_vsize(void)
 
 	return 0;
 }
+
+static bool insn_is_vector(u32 insn_buf)
+{
+	u32 opcode = insn_buf & __INSN_OPCODE_MASK;
+	u32 width, csr;
+
+	/*
+	 * All V-related instructions, including CSR operations are 4-Byte. So,
+	 * do not handle if the instruction length is not 4-Byte.
+	 */
+	if (unlikely(GET_INSN_LENGTH(insn_buf) != 4))
+		return false;
+
+	switch (opcode) {
+	case RVV_OPCODE_VECTOR:
+		return true;
+	case RVV_OPCODE_VL:
+	case RVV_OPCODE_VS:
+		width = RVV_EXRACT_VL_VS_WIDTH(insn_buf);
+		if (width == RVV_VL_VS_WIDTH_8 || width == RVV_VL_VS_WIDTH_16 ||
+		    width == RVV_VL_VS_WIDTH_32 || width == RVV_VL_VS_WIDTH_64)
+			return true;
+
+		break;
+	case RVG_OPCODE_SYSTEM:
+		csr = RVG_EXTRACT_SYSTEM_CSR(insn_buf);
+		if ((csr >= CSR_VSTART && csr <= CSR_VCSR) ||
+		    (csr >= CSR_VL && csr <= CSR_VLENB))
+			return true;
+	}
+
+	return false;
+}
+
+static int riscv_v_thread_zalloc(void)
+{
+	void *datap;
+
+	datap = kzalloc(riscv_v_vsize, GFP_KERNEL);
+	if (!datap)
+		return -ENOMEM;
+
+	current->thread.vstate.datap = datap;
+	memset(&current->thread.vstate, 0, offsetof(struct __riscv_v_ext_state,
+						    datap));
+	return 0;
+}
+
+bool riscv_v_first_use_handler(struct pt_regs *regs)
+{
+	u32 __user *epc = (u32 __user *)regs->epc;
+	u32 insn = (u32)regs->badaddr;
+
+	/* Do not handle if V is not supported, or disabled */
+	if (!has_vector() || !(elf_hwcap & COMPAT_HWCAP_ISA_V))
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
+		force_sig(SIGKILL);
+		return true;
+	}
+	riscv_v_vstate_on(regs);
+	return true;
+}
```

### TODO: 8) vector per-task context switch

* [[PATCH -next v20 07/26\] riscv: Introduce Vector enable/disable helpers - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-8-andy.chiu@sifive.com/)
* [[PATCH -next v20 09/26\] riscv: Introduce struct/helpers to save/restore per-task Vector state - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-10-andy.chiu@sifive.com/)
* [[PATCH -next v20 10/26\] riscv: Add task switch support for vector - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-11-andy.chiu@sifive.com/)
* [[PATCH -next v20 17/26\] riscv: prevent stack corruption by reserving task_pt_regs(p) early - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-18-andy.chiu@sifive.com/)



### TODO: 9) ptrace vector

[[PATCH -next v20 12/26\] riscv: Add ptrace vector support - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-13-andy.chiu@sifive.com/)





### Ext: 10) vector signal handle

* [[PATCH -next v20 13/26\] riscv: signal: check fp-reserved words unconditionally - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-14-andy.chiu@sifive.com/)
* [[PATCH -next v20 14/26\] riscv: signal: Add sigcontext save/restore for vector - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-15-andy.chiu@sifive.com/)
* [[PATCH -next v20 15/26\] riscv: signal: Report signal frame size to userspace via auxv - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-16-andy.chiu@sifive.com/)
* [[PATCH -next v20 16/26\] riscv: signal: validate altstack to reflect Vector - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-17-andy.chiu@sifive.com/)

#### check fp-reserved words unconditionally

为了让内核和用户，在现有信号帧上定位和识别扩展上下文，我们将利用浮点寄存器的保留空间，并在那里编码信息。由于 `sigcontext` ，已经为有或没有配置浮点单元（CONFIG_FPU）的浮点上下文预留了空间，我们将这些保留字的检查/设置例程移回通用代码中。

此提交还撤销了重构提交 007f5c3589578（“重构信号设置/返回过程中的 FPU 代码”）所带来的额外逻辑更改。最初，如果通用寄存器（GPR）的恢复失败，我们不会恢复浮点上下文。这样做是可以的，这样内核可以保持寄存器文件完整，并可能在恢复失败点做出反应。

```c
//...

```

#### Add sigcontext save/restore for vector

这个补丁利用现有的浮点保留字，在用户的信号帧上放置第一个扩展的上下文头。一个上下文头包括: 一个独特的魔术字和栈上扩展的大小（包括头本身）。然后，帧接着是该扩展的上下文，如果存在另一个扩展，则是另一个头和上下文主体。如果没有更多扩展，则帧必须以一个空的上下文头结尾。一个特殊情况是 `rv64gc`，其中内核不支持那些需要向用户暴露额外寄存器文件的扩展。在这种情况下，内核会在保存信号帧时在 `__riscv_q_ext_state` 的第一个保留字之后，放置空的上下文头。而当信号处理程序返回时，内核会检查所有保留字是否都是零。

```c
__riscv_q_ext_state---->|    |<-__riscv_extra_ext_header
                        ~    ~
    .reserved[0]--->|0   |<- .reserved
            <-------|magic |<- .hdr
            |       |size  |_______ end of sc_fpregs
            |       |ext-bdy|
            |       ~     ~
    +)size  ------->|magic |<- another context header
                    |size  |
                    |ext-bdy|
                    ~     ~
                    |magic:0|<- null context header
                    |size:0 |
```

向量寄存器将保存在 `datap` 指针中。当任务在内核空间中需要时，`datap` 指针将动态分配。另一方面，信号帧上的 `datap` 指针将在 `__riscv_v_ext_state` 数据结构之后设置。

> **数据结构与宏定义**

```c
--- a/arch/riscv/include/uapi/asm/ptrace.h
+++ b/arch/riscv/include/uapi/asm/ptrace.h
@@ -71,6 +71,21 @@ struct __riscv_q_ext_state {
 	__u32 reserved[3];
 };
 
+struct __riscv_ctx_hdr {
+	__u32 magic;
+	__u32 size;
+};
+
+struct __riscv_extra_ext_header {
+	__u32 __padding[129] __attribute__((aligned(16)));
+	/*
+	 * Reserved for expansion of sigcontext structure.  Currently zeroed
+	 * upon signal, and must be zero upon sigreturn.
+	 */
+	__u32 reserved;
+	struct __riscv_ctx_hdr hdr;
+};
+
--- a/arch/riscv/include/uapi/asm/sigcontext.h
+++ b/arch/riscv/include/uapi/asm/sigcontext.h
@@ -8,6 +8,17 @@
 
 #include <asm/ptrace.h>
 
+/* The Magic number for signal context frame header. */
+#define RISCV_V_MAGIC	0x53465457
+#define END_MAGIC	0x0
+
+/* The size of END signal context header. */
+#define END_HDR_SIZE	0x0
+
+struct __sc_riscv_v_state {
+	struct __riscv_v_ext_state v_state;
+} __attribute__((aligned(16)));
+
 /*
  * Signal context structure
  *
@@ -16,7 +27,10 @@
  */
 struct sigcontext {
 	struct user_regs_struct sc_regs;
-	union __riscv_fp_state sc_fpregs;
+	union {
+		union __riscv_fp_state sc_fpregs;
+		struct __riscv_extra_ext_header sc_extdesc;
+	};
 };
 
 #endif /* _UAPI_ASM_RISCV_SIGCONTEXT_H */
--- a/arch/riscv/kernel/setup.c
+++ b/arch/riscv/kernel/setup.c
@@ -262,6 +262,8 @@ static void __init parse_dtb(void)
 #endif
 }
 
+extern void __init init_rt_signal_env(void);
+
 void __init setup_arch(char **cmdline_p)
 {
 	parse_dtb();
@@ -295,6 +297,7 @@ void __init setup_arch(char **cmdline_p)
 
 	riscv_init_cbo_blocksizes();
 	riscv_fill_hwcap();
+	init_rt_signal_env();
 	apply_boot_alternatives();
 	if (IS_ENABLED(CONFIG_RISCV_ISA_ZICBOM) &&
 	    riscv_isa_extension_available(NULL, ZICBOM))
diff --git a/arch/riscv/kernel/signal.c b/arch/riscv/kernel/signal.c
index 6b4a5c90bd87..c46f3dc039bb 100644
--- a/arch/riscv/kernel/signal.c
+++ b/arch/riscv/kernel/signal.c
@@ -19,10 +19,12 @@
 #include <asm/signal.h>
 #include <asm/signal32.h>
 #include <asm/switch_to.h>
+#include <asm/vector.h>
 #include <asm/csr.h>
 #include <asm/cacheflush.h>
 
 extern u32 __user_rt_sigreturn[2];
+static size_t riscv_v_sc_size __ro_after_init;
```



> **vector-signal执行流**







#### Report signal frame size to userspace via auxv

向量寄存器属于信号上下文。它们需要在进入和离开信号处理程序时保存和恢复。根据 V 扩展规范，向量寄存器的最大长度可以是 2^16。因此，如果用户空间参考 MINSIGSTKSZ 来创建信号帧，可能不够。为了解决这个问题，这个补丁参考了提交 94b07c1f8c39c（"arm64: signal: Report signal frame size to userspace via auxv"），使用户空间能够通过辅助向量（auxiliary vector）知道所需的最小信号帧大小，并使用它来分配足够的内存以保存信号上下文。

请注意，只要内核启用了 CONFIG_RISCV_ISA_V，auxv 总是报告信号帧的大小，仿佛所有启动的进程都存在 V 扩展。这是因为用户通常参考这个值来分配备用信号栈，而用户随时可能使用 V。因此，用户必须在信号帧中为 V 上下文预留空间，以防信号处理程序在内核分配 V 之后调用。





#### validate altstack to reflect Vector

一些扩展（例如 Vector）会动态改变信号帧上的占用空间，因此 MINSIGSTKSZ 不再准确。例如，即将支持的 vlen = 512 的 RV64V 实现可能占用信号帧的 2K + 40 + 12 字节。而不执行任何向量指令的进程不需要保留额外的信号帧空间。因此，我们需要一种方法根据 V 的当前状态在进程运行时保护信号帧的分配大小。

因此，提供函数 `sigaltstack_size_valid()`，以根据当前支持的扩展的分配状态验证其大小。







### *11) userapce vector prctl/sysctl

* [[PATCH -next v20 20/26\] riscv: Add prctl controls for userspace vector management - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-21-andy.chiu@sifive.com/)
* [[PATCH -next v20 21/26\] riscv: Add sysctl to set the default vector rule for new processes - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-22-andy.chiu@sifive.com/)
* [[PATCH -next v20 25/26\] selftests: Test RISC-V Vector prctl interface - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-26-andy.chiu@sifive.com/)
* [[PATCH -next v20 26/26\] selftests: add .gitignore file for RISC-V hwprobe - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-27-andy.chiu@sifive.com/)

> `prctl` 和 `sysctl` 都是用于控制和配置操作系统行为的接口，但它们在用途和应用范围上有一些重要的区别：
>
> ### `prctl`
>
> `prctl` 是一个用于控制特定进程或线程行为的系统调用。其主要特点和作用包括：
>
> 1. **进程/线程级控制**：`prctl` 通常用于设置和获取当前进程或线程的特定属性或行为。它的作用范围是调用该系统调用的进程或线程。
> 2. **定制化控制**：提供了多种操作，如设置进程名、启用或禁用特定的功能、安全属性等。例如，可以使用 `prctl` 来启用进程的核心转储、设置进程的名字，或者在RISC-V架构中控制矢量扩展的启用状态。
> 3. **安全性和灵活性**：由于 `prctl` 仅影响调用它的进程或线程，提供了更高的灵活性和安全性，适用于需要细粒度控制的场景。
>
> **示例：**
>
> ```c
> #include <sys/prctl.h>
> #include <linux/prctl.h>
> 
> int result = prctl(PR_SET_NAME, "my_process_name", 0, 0, 0);
> if (result == -1) {
>     perror("prctl");
> }
> ```
>
> ### `sysctl`
>
> `sysctl` 是一个用于读取和写入内核参数的接口。其主要特点和作用包括：
>
> 1. **系统级控制**：`sysctl` 主要用于系统范围内的配置。通过调整内核参数，可以影响整个系统的行为和性能。
> 2. **内核参数管理**：`sysctl` 接口允许管理员读取和设置运行时的内核参数，涉及内存管理、网络设置、文件系统行为等方面。它通过 `/proc/sys` 文件系统实现，管理员可以通过文件接口进行参数调整。
> 3. **配置持久化**：一些系统配置可以通过 `sysctl` 永久保存，并在系统启动时应用，通常通过 `/etc/sysctl.conf` 文件或 `/etc/sysctl.d/` 目录下的配置文件来实现。
>
> **示例：**
> ```sh
> # 读取当前的最大文件描述符数
> sysctl fs.file-max
> 
> # 设置新的最大文件描述符数
> sysctl -w fs.file-max=100000
> 
> # 永久保存配置，在 /etc/sysctl.conf 中添加以下行
> echo "fs.file-max = 100000" >> /etc/sysctl.conf
> ```
>
> ### 区别总结
>
> 1. **作用范围**：
>    - `prctl` 主要针对单个进程或线程，用于控制进程或线程的特定行为。
>    - `sysctl` 主要针对系统级参数，用于配置和调整整个系统的行为。
>
> 2. **使用场景**：
>    - `prctl` 常用于需要对特定进程或线程进行定制化控制的场景。
>    - `sysctl` 常用于系统管理员需要调整系统参数以优化性能、增强安全性或适应特定工作负载的场景。
>
> 3. **实现方式**：
>    - `prctl` 是一个系统调用，直接在代码中调用。
>    - `sysctl` 通过 `/proc/sys` 文件系统接口实现，通常通过命令行或配置文件进行操作。

---

#### `prctl`

该补丁添加了两个特定于 RISC-V 的 prctl，用于允许用户空间控制向量单元的使用：

* `PR_RISCV_V_SET_CONTROL`: 控制线程在下一次或所有后续 execve 中使用向量的权限。由于库可能已经注册了，可能执行向量指令的 ifunc，因此无法关闭线程的向量活动。
* `PR_RISCV_V_GET_CONTROL`: 获取当前线程的相同权限设置，以及后续 execve 的设置。

> **数据结构与宏定义**

```c
--- a/arch/riscv/include/asm/processor.h
+++ b/arch/riscv/include/asm/processor.h
@@ -40,6 +40,7 @@ struct thread_struct {
 	unsigned long s[12];	/* s[0]: frame pointer */
 	struct __riscv_d_ext_state fstate;
 	unsigned long bad_cause;
+	unsigned long vstate_ctrl;
 	struct __riscv_v_ext_state vstate;
 };
+#ifdef CONFIG_RISCV_ISA_V
+/* Userspace interface for PR_RISCV_V_{SET,GET}_VS prctl()s: */
+#define RISCV_V_SET_CONTROL(arg)	riscv_v_vstate_ctrl_set_current(arg)
+#define RISCV_V_GET_CONTROL()		riscv_v_vstate_ctrl_get_current()
+extern long riscv_v_vstate_ctrl_set_current(unsigned long arg);
+extern long riscv_v_vstate_ctrl_get_current(void);
+#else /* !CONFIG_RISCV_ISA_V */
+#define RISCV_V_SET_CONTROL(arg)	(-EINVAL)
+#define RISCV_V_GET_CONTROL()		(-EINVAL)
+#endif /* CONFIG_RISCV_ISA_V */
+void riscv_v_vstate_ctrl_init(struct task_struct *tsk);
+bool riscv_v_vstate_ctrl_user_allowed(void);

--- a/include/uapi/linux/prctl.h
+++ b/include/uapi/linux/prctl.h
@@ -294,4 +294,15 @@ struct prctl_mm_map {
 
 #define PR_SET_MEMORY_MERGE		67
 #define PR_GET_MEMORY_MERGE		68
+
+#define PR_RISCV_V_SET_CONTROL		69
+#define PR_RISCV_V_GET_CONTROL		70
+# define PR_RISCV_V_VSTATE_CTRL_DEFAULT		0
+# define PR_RISCV_V_VSTATE_CTRL_OFF		1
+# define PR_RISCV_V_VSTATE_CTRL_ON		2
+# define PR_RISCV_V_VSTATE_CTRL_INHERIT		(1 << 4)
+# define PR_RISCV_V_VSTATE_CTRL_CUR_MASK	0x3
+# define PR_RISCV_V_VSTATE_CTRL_NEXT_MASK	0xc
+# define PR_RISCV_V_VSTATE_CTRL_MASK		0x1f
+
 #endif /* _LINUX_PRCTL_H */
diff --git a/kernel/sys.c b/kernel/sys.c
index 339fee3eff6a..d0d3106698a1 100644
--- a/kernel/sys.c
+++ b/kernel/sys.c
@@ -140,6 +140,12 @@
 #ifndef GET_TAGGED_ADDR_CTRL
 # define GET_TAGGED_ADDR_CTRL()		(-EINVAL)
 #endif
+#ifndef PR_RISCV_V_SET_CONTROL
+# define RISCV_V_SET_CONTROL(a)		(-EINVAL)
+#endif
+#ifndef PR_RISCV_V_GET_CONTROL
+# define RISCV_V_GET_CONTROL()		(-EINVAL)
+#endif
```

> **`prctl` 执行流**

```c
//pactl入口
@@ -2708,6 +2714,12 @@ SYSCALL_DEFINE5(prctl, int, option, unsigned long, arg2, unsigned long, arg3,
 		error = !!test_bit(MMF_VM_MERGE_ANY, &me->mm->flags);
 		break;
 #endif
+	case PR_RISCV_V_SET_CONTROL:
+		error = RISCV_V_SET_CONTROL(arg2);
+		break;
+	case PR_RISCV_V_GET_CONTROL:
+		error = RISCV_V_GET_CONTROL();
+		break;
 	default:
 		error = -EINVAL;
 		break;
                                       
//flush_thread
--- a/arch/riscv/kernel/process.c
+++ b/arch/riscv/kernel/process.c
@@ -149,6 +149,7 @@ void flush_thread(void)
 #endif
 #ifdef CONFIG_RISCV_ISA_V
 	/* Reset vector state */
+	riscv_v_vstate_ctrl_init(current);
 	riscv_v_vstate_off(task_pt_regs(current));
 	kfree(current->thread.vstate.datap);
 	memset(&current->thread.vstate, 0, sizeof(struct __riscv_v_ext_state));

//some helpers
+static bool riscv_v_implicit_uacc = IS_ENABLED(CONFIG_RISCV_ISA_V_DEFAULT_ENABLE);
+
+#define VSTATE_CTRL_GET_CUR(x) ((x) & PR_RISCV_V_VSTATE_CTRL_CUR_MASK)
+#define VSTATE_CTRL_GET_NEXT(x) (((x) & PR_RISCV_V_VSTATE_CTRL_NEXT_MASK) >> 2)
+#define VSTATE_CTRL_MAKE_NEXT(x) (((x) << 2) & PR_RISCV_V_VSTATE_CTRL_NEXT_MASK)
+#define VSTATE_CTRL_GET_INHERIT(x) (!!((x) & PR_RISCV_V_VSTATE_CTRL_INHERIT))
+static inline int riscv_v_ctrl_get_cur(struct task_struct *tsk)
+{
+	return VSTATE_CTRL_GET_CUR(tsk->thread.vstate_ctrl);
+}
+
+static inline int riscv_v_ctrl_get_next(struct task_struct *tsk)
+{
+	return VSTATE_CTRL_GET_NEXT(tsk->thread.vstate_ctrl);
+}
+
+static inline bool riscv_v_ctrl_test_inherit(struct task_struct *tsk)
+{
+	return VSTATE_CTRL_GET_INHERIT(tsk->thread.vstate_ctrl);
+}
+
+bool riscv_v_vstate_ctrl_user_allowed(void)
+{
+	return riscv_v_ctrl_get_cur(current) == PR_RISCV_V_VSTATE_CTRL_ON;
+}
+EXPORT_SYMBOL_GPL(riscv_v_vstate_ctrl_user_allowed);
+
```

下面是三个核心函数：

* `riscv_v_vstate_ctrl_init`
* `riscv_v_vstate_ctrl_get_current`
* `riscv_v_vstate_ctrl_set_current`

```c
tatic struct linux_binfmt elf_format = {
	.module		= THIS_MODULE,
	.load_binary	= load_elf_binary,
	.load_shlib	= load_elf_library,
#ifdef CONFIG_COREDUMP
	.core_dump	= elf_core_dump,
	.min_coredump	= ELF_EXEC_PAGESIZE,
#endif
};

SYSCALL_DEFINE3(execve,
		const char __user *, filename,
		const char __user *const __user *, argv,
		const char __user *const __user *, envp)
{
	return do_execve(getname(filename), argv, envp);
}

do_execve
   +-> do_execveat_common
    	+-> bprm_execve
    		+-> exec_binprm
    			+-> search_binary_handler
    				+-> fmt->load_binary(bprm);
						+-> load_elf_binary
                            /* Flush all traces of the currently running executable */
                            +-> begin_new_exec
                                +-> flush_thread
                            		+-> riscv_v_vstate_ctrl_init

+void riscv_v_vstate_ctrl_init(struct task_struct *tsk)
+{
+	bool inherit;
+	int cur, next;
+
+	if (!has_vector())
+		return;
+
+	next = riscv_v_ctrl_get_next(tsk);
+	if (!next) {
+		if (riscv_v_implicit_uacc)
+			cur = PR_RISCV_V_VSTATE_CTRL_ON;
+		else
+			cur = PR_RISCV_V_VSTATE_CTRL_OFF;
+	} else {
+		cur = next;
+	}
+	/* Clear next mask if inherit-bit is not set */
+	inherit = riscv_v_ctrl_test_inherit(tsk);
+	if (!inherit)
+		next = PR_RISCV_V_VSTATE_CTRL_DEFAULT;
+
+	riscv_v_ctrl_set(tsk, cur, next, inherit);
+}
+
+long riscv_v_vstate_ctrl_get_current(void)
+{
+	if (!has_vector())
+		return -EINVAL;
+
+	return current->thread.vstate_ctrl & PR_RISCV_V_VSTATE_CTRL_MASK;
+}
+
+long riscv_v_vstate_ctrl_set_current(unsigned long arg)
+{
+	bool inherit;
+	int cur, next;
+
+	if (!has_vector())
+		return -EINVAL;
+
+	if (arg & ~PR_RISCV_V_VSTATE_CTRL_MASK)
+		return -EINVAL;
+
+	cur = VSTATE_CTRL_GET_CUR(arg);
+	switch (cur) {
+	case PR_RISCV_V_VSTATE_CTRL_OFF:
+		/* Do not allow user to turn off V if current is not off */
+		if (riscv_v_ctrl_get_cur(current) != PR_RISCV_V_VSTATE_CTRL_OFF)
+			return -EPERM;
+
+		break;
+	case PR_RISCV_V_VSTATE_CTRL_ON:
+		break;
+	case PR_RISCV_V_VSTATE_CTRL_DEFAULT:
+		cur = riscv_v_ctrl_get_cur(current);
+		break;
+	default:
+		return -EINVAL;
+	}
+
+	next = VSTATE_CTRL_GET_NEXT(arg);
+	inherit = VSTATE_CTRL_GET_INHERIT(arg);
+	switch (next) {
+	case PR_RISCV_V_VSTATE_CTRL_DEFAULT:
+	case PR_RISCV_V_VSTATE_CTRL_OFF:
+	case PR_RISCV_V_VSTATE_CTRL_ON:
+		riscv_v_ctrl_set(current, cur, next, inherit);
+		return 0;
+	}
+
+	return -EINVAL;
+}
+
+static inline void riscv_v_ctrl_set(struct task_struct *tsk, int cur, int nxt,
+				    bool inherit)
+{
+	unsigned long ctrl;
+
+	ctrl = cur & PR_RISCV_V_VSTATE_CTRL_CUR_MASK;
+	ctrl |= VSTATE_CTRL_MAKE_NEXT(nxt);
+	if (inherit)
+		ctrl |= PR_RISCV_V_VSTATE_CTRL_INHERIT;
+	tsk->thread.vstate_ctrl = ctrl;
+}
```

#### `sysctl`

为了支持 Vector 扩展，该系列在信号帧上导出可变长度的向量寄存器。然而，如果在旧的二进制文件中，信号处理程序需要处理向量寄存器，这可能会破坏 ABI。例如，如果通过信号触发用户级上下文切换，则需要这样做。

> 见讨论: https://lore.kernel.org/all/87cz4048rp.fsf@all.your.base.are.belong.to.us/

因此，最好将决定权留给发行版维护者，他们可以控制新启动的程序中用户空间 Vector 的启用。开发人员也可能需要这个开关，来进行实验。通过 `sysctl` 接口可以配置该参数，因此如果在实际环境中确实发生破坏，发行版可以在初始化脚本中早期关闭 Vector。

一旦设置后，该开关仅对新的 execve 生效。这不会影响不调用 execve 的现有进程，也不会影响通过显式 PR_RISCV_V_SET_CONTROL prctl 调用设置了非默认 vstate_ctrl 的进程。

```c
--- a/arch/riscv/kernel/vector.c
+++ b/arch/riscv/kernel/vector.c
@@ -184,7 +184,7 @@ void riscv_v_vstate_ctrl_init(struct task_struct *tsk)
 
 	next = riscv_v_ctrl_get_next(tsk);
 	if (!next) {
-		if (riscv_v_implicit_uacc)
+		if (READ_ONCE(riscv_v_implicit_uacc))
 			cur = PR_RISCV_V_VSTATE_CTRL_ON;
 		else
 			cur = PR_RISCV_V_VSTATE_CTRL_OFF;
@@ -247,3 +247,34 @@ long riscv_v_vstate_ctrl_set_current(unsigned long arg)
 
 	return -EINVAL;
 }
+
+#ifdef CONFIG_SYSCTL
+
+static struct ctl_table riscv_v_default_vstate_table[] = {
+	{
+		.procname	= "riscv_v_default_allow",
+		.data		= &riscv_v_implicit_uacc,
+		.maxlen		= sizeof(riscv_v_implicit_uacc),
+		.mode		= 0644,
+		.proc_handler	= proc_dobool,
+	},
+	{ }
+};
+
+static int __init riscv_v_sysctl_init(void)
+{
+	if (has_vector())
+		if (!register_sysctl("abi", riscv_v_default_vstate_table))
+			return -EINVAL;
+	return 0;
+}
+
+#else /* ! CONFIG_SYSCTL */
+static int __init riscv_v_sysctl_init(void) { return 0; }
+#endif /* ! CONFIG_SYSCTL */
+
+static int riscv_v_init(void)
+{
+	return riscv_v_sysctl_init();
+}
+core_initcall(riscv_v_init);
```







## TODO: 2.2 kvm-support

[[PATCH -next v20 18/26\] riscv: kvm: Add V extension to KVM ISA - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-19-andy.chiu@sifive.com/)

[[PATCH -next v20 19/26\] riscv: KVM: Add vector lazy save/restore support - Andy Chiu (kernel.org)](https://lore.kernel.org/all/20230518161949.11203-20-andy.chiu@sifive.com/)





# 3 RISC-V Kernel-Mode Vector Support

https://lore.kernel.org/all/20240115055929.4736-1-andy.chiu@sifive.com/#r

> 该系列补丁提供了在内核模式下运行 Vector 的支持。此外，内核模式 Vector 可以在 CONFIG_PREEMPT 内核上配置为在不关闭抢占的情况下运行。随着支持的增加，我们添加了 Vector 优化的 `copy_{to,from}_user` 函数，并提供了一个简单的阈值来决定何时运行向量化函数。
>
> 由于担心 `kernel_vector_begin()` 中的内存副作用，我们决定暂时放弃向量化的 `memcpy`/`memset`/`memmove`。详细描述可在 https://lore.kernel.org/all/20231229143627.22898-1-andy.chiu@sifive.com/ 中找到。
>
> 这个系列由四部分组成：
>
> - 补丁 1-4：添加了内核模式 Vector 的基本支持
> - 补丁 5：将向量化的 `copy_{to,from}_user` 包含到内核中
> - 补丁 6：重构 FPU 中的上下文切换代码
> - 补丁 7-10：提供了一些代码重构和对可抢占内核模式 Vector 的支持
>
> 如果我们认为 {1~4, 5, 6, 7~10} 中的任何部分已经足够成熟，可以合并这些补丁。
>
> 这个补丁在启用了 V 的 QEMU 上进行了测试，并验证了启动和正常的用户空间操作在阈值设置为 0 时都能正常工作。此外，我们通过启动多个内核线程在后台连续执行和验证 Vector 操作来进行测试。预计测试这些操作的模块稍后会提交到上游。

对这组PATCH归类如下：

* `adds basic support for kernel-mode Vector`
  * [riscv: Add support for kernel mode vector](https://lore.kernel.org/all/20240115055929.4736-2-andy.chiu@sifive.com/#r)
  * [riscv: vector: make Vector always available for softirq context](https://lore.kernel.org/all/20240115055929.4736-3-andy.chiu@sifive.com/)
  * [riscv: Add vector extension XOR implementation](https://lore.kernel.org/all/20240115055929.4736-4-andy.chiu@sifive.com/)
  * [riscv: sched: defer restoring Vector context for user](https://lore.kernel.org/all/20240115055929.4736-5-andy.chiu@sifive.com/)
* `includes vectorized copy_{to,from}_user into the kernel`
  * [riscv: lib: vectorize copy_to_user/copy_from_user](https://lore.kernel.org/all/20240115055929.4736-6-andy.chiu@sifive.com/)
* `refactor context switch code in fpu`
* `support for preemptible kernel-mode Vector`
  * [riscv: vector: do not pass task_struct into riscv_v_vstate_{save,restore}()](https://lore.kernel.org/all/20240115055929.4736-8-andy.chiu@sifive.com/)
  * [riscv: vector: use a mask to write vstate_ctrl](https://lore.kernel.org/all/20240115055929.4736-9-andy.chiu@sifive.com/)
  * [riscv: vector: use kmem_cache to manage vector context](https://lore.kernel.org/all/20240115055929.4736-10-andy.chiu@sifive.com/)
  * [riscv: vector: allow kernel-mode Vector with preemption](https://lore.kernel.org/all/20240115055929.4736-11-andy.chiu@sifive.com/)





## 3.1 adds basic support for kernel-mode Vector

* [riscv: Add support for kernel mode vector](https://lore.kernel.org/all/20240115055929.4736-2-andy.chiu@sifive.com/#r)
* [riscv: vector: make Vector always available for softirq context](https://lore.kernel.org/all/20240115055929.4736-3-andy.chiu@sifive.com/)
* [riscv: Add vector extension XOR implementation](https://lore.kernel.org/all/20240115055929.4736-4-andy.chiu@sifive.com/)
* [riscv: sched: defer restoring Vector context for user](https://lore.kernel.org/all/20240115055929.4736-5-andy.chiu@sifive.com/)

在 `kernel_mode_vector.c` 文件中，添加 `kernel_vector_begin()` 和 `kernel_vector_end()` 函数的声明和相应的定义。这些函数用于在内核模式下包装对 vector 的使用。

### 1) 数据结构与宏

```c
--- a/arch/riscv/include/asm/processor.h
+++ b/arch/riscv/include/asm/processor.h
@@ -73,6 +73,15 @@
 struct task_struct;
 struct pt_regs;
 
+/*
+ * We use a flag to track in-kernel Vector context. Currently the flag has the
+ * following meaning:
+ *
+ *  - bit 0: indicates whether the in-kernel Vector context is active. The
+ *    activation of this state disables the preemption.
+ */
+#define RISCV_KERNEL_MODE_V	0x1
+
 /* CPU-specific state of a task */
 struct thread_struct {
 	/* Callee-saved registers */
@@ -81,7 +90,8 @@ struct thread_struct {
 	unsigned long s[12];	/* s[0]: frame pointer */
 	struct __riscv_d_ext_state fstate;
 	unsigned long bad_cause;
-	unsigned long vstate_ctrl;
+	u32 riscv_v_flags;
+	u32 vstate_ctrl;
 	struct __riscv_v_ext_state vstate;
 	unsigned long align_ctl;
 };
--- a/arch/riscv/kernel/Makefile
+++ b/arch/riscv/kernel/Makefile
@@ -64,6 +64,7 @@ obj-$(CONFIG_MMU) += vdso.o vdso/
 obj-$(CONFIG_RISCV_MISALIGNED)	+= traps_misaligned.o
 obj-$(CONFIG_FPU)		+= fpu.o
 obj-$(CONFIG_RISCV_ISA_V)	+= vector.o
+obj-$(CONFIG_RISCV_ISA_V)	+= kernel_mode_vector.o
 obj-$(CONFIG_SMP)		+= smpboot.o
 obj-$(CONFIG_SMP)		+= smp.o
 obj-$(CONFIG_SMP)		+= cpu_ops.o
     
--- a/arch/riscv/include/asm/vector.h
+++ b/arch/riscv/include/asm/vector.h
@@ -22,6 +22,15 @@
 extern unsigned long riscv_v_vsize;
 int riscv_v_setup_vsize(void);
 bool riscv_v_first_use_handler(struct pt_regs *regs);
+void kernel_vector_begin(void);
+void kernel_vector_end(void);
+void get_cpu_vector_context(void);
+void put_cpu_vector_context(void);
+
+static inline u32 riscv_v_flags(void)
+{
+	return current->thread.riscv_v_flags;
+}
```

### 2) kernel-mode vector逻辑分析

#### function overview

* `may_use_simd`

  ```c
  /*
   * may_use_simd - 是否允许在当前时间发出向量指令或访问向量寄存器文件
   *
   * 调用者不能假设结果在下一次 preempt_enable() 或从软中断上下文返回后仍然为真。
   */
  static __must_check inline bool may_use_simd(void)
  {
  	/*
  	 * RISCV_KERNEL_MODE_V 仅在抢占禁用时设置，
  	 * 并且在抢占启用时清除。
  	 */
  	return !in_hardirq() && !in_nmi() && !(riscv_v_flags() & RISCV_KERNEL_MODE_V);
  }
  ```

  > `riscv_v_flags() & RISCV_KERNEL_MODE_V == true` 时不允许使用simd，即暂不支持嵌套kernel-vector的使用

* `riscv_v_start/stop`

  ```c
  +static inline void riscv_v_flags_set(u32 flags)
  +{
  +	current->thread.riscv_v_flags = flags;
  +}
  +
  +static inline void riscv_v_start(u32 flags)
  +{
  +	int orig;
  +
  +	orig = riscv_v_flags();
  +	BUG_ON((orig & flags) != 0);
  +	riscv_v_flags_set(orig | flags);
  +}
  +
  +static inline void riscv_v_stop(u32 flags)
  +{
  +	int orig;
  +
  +	orig = riscv_v_flags();
  +	BUG_ON((orig & flags) == 0);
  +	riscv_v_flags_set(orig & ~flags);
  +}
  ```

* `get/put_cpu_vector_context`

  ```c
  /*
   * 声明对 CPU 向量上下文的所有权，以供调用上下文使用。
   *
   * 调用者可以自由操作向量上下文元数据，直到调用 put_cpu_vector_context()。
   */
  void get_cpu_vector_context(void)
  {
  	preempt_disable();
  	riscv_v_start(RISCV_KERNEL_MODE_V);
  }
  
  /*
   * 释放 CPU 向量上下文。
   *
   * 必须从之前调用了 get_cpu_vector_context() 的上下文中调用，
   * 并且在此期间未调用 put_cpu_vector_context()。
   */
  void put_cpu_vector_context(void)
  {
  	riscv_v_stop(RISCV_KERNEL_MODE_V);
  	preempt_enable();
  }
  ```

* `kernel_vector_begin/end`

  ```c
  /*
   * kernel_vector_begin(): 获取调用上下文可用的CPU向量寄存器
   *
   * 除非may_use_simd()返回true，否则不能调用此函数。
   * 必要时，将向量寄存器中的任务上下文保存回内存。
   *
   * 在返回调用上下文之前，必须匹配调用kernel_vector_end()。
   *
   * 调用者可以自由使用向量寄存器，直到调用kernel_vector_end()为止。
   */
  void kernel_vector_begin(void)
  {
  	if (WARN_ON(!has_vector()))
  		return;
  
  	BUG_ON(!may_use_simd());
  
  	get_cpu_vector_context();
  
  	riscv_v_vstate_save(current, task_pt_regs(current));
  
  	riscv_v_enable();
  }
  EXPORT_SYMBOL_GPL(kernel_vector_begin);
  
  /*
   * kernel_vector_end(): 将CPU向量寄存器交还给当前任务
   *
   * 必须在之前调用过kernel_vector_begin()的上下文中调用此函数，中间不能有kernel_vector_end()的调用。
   *
   * 除非在此期间再次调用kernel_vector_begin()，否则调用者在调用此函数后不得使用向量寄存器。
   */
  void kernel_vector_end(void)
  {
  	if (WARN_ON(!has_vector()))
  		return;
  
  	riscv_v_vstate_restore(current, task_pt_regs(current));
  
  	riscv_v_disable();
  
  	put_cpu_vector_context();
  }
  EXPORT_SYMBOL_GPL(kernel_vector_end);
  ```

> 目前在 `thread_struct` 中只保留一份 `vstate`，用于保存用户态的vector上下文，内核在某些路径下使用vector相关寄存器时，会破坏原来的vector切换机制，导致用户态vector上下文丢失。
>
> 其实，想在内核中使用vector硬件而不破坏用户态的vector状态并不难，只要内核在使用vector的代码片段前后维护好 `current->vstate` 就可以了，arm64和riscv采用的方法相同，规定：内核在使用任何vector硬件之前，需要调用 `kernel_vector_begin` 保存用户态vector-ctx，在之后调用 `kernel_vector_end` 恢复用户态vector-ctx。
>
> 但这也意味着一件事，内核的vector状态是无法保留的，因此必须保证某个内核线程已持有的vector状态不能被破坏，因为这份状态只能保存在硬件上，一旦破坏内核vector上下文将彻底丢失， `kernel_vector_begin` 因此也设定了一些规则来保护它：
>
> ```c
> +void kernel_vector_begin(void)
> +{
> +	if (WARN_ON(!has_vector()))
> +		return;
> +
> +	BUG_ON(!may_use_simd());
> +
> +	get_cpu_vector_context();
> +
> +	riscv_v_vstate_save(current, task_pt_regs(current));
> +
> +	riscv_v_enable();
> +}
> 
> +void get_cpu_vector_context(void)
> +{
> +	preempt_disable();
> +
> +	riscv_v_start(RISCV_KERNEL_MODE_V);
> +}
> 
> +static __must_check inline bool may_use_simd(void)
> +{
> +	/*
> +	 * RISCV_KERNEL_MODE_V is only set while preemption is disabled,
> +	 * and is clear whenever preemption is enabled.
> +	 */
> +	return !in_hardirq() && !in_nmi() && !(riscv_v_flags() & RISCV_KERNEL_MODE_V);
> +}
> ```
>
> 可以看到，内核在使用vector之前将进行 `riscv_v_flags` 检查，如果已经被标记为 `RISCV_KERNEL_MODE_V`，说明当前hart上的vector状态已经被某一个内核线程所占用，内核则不允许再次使用vector操作，这样软中断将从 `kernel_vector_begin` 中退出 。
>
> 除此之外，内核还必须禁止抢占行为，抢占和中断不一样，中断发生在内核态且最重要的是：interrupt-handler在操作vector之前，会调用 `kernel_vector_begin` 进行检查，因此中断上下文，并不会对已经被某个kernel-thread占用的vector硬件进行操作。但抢占它的某个线程就不一样了，如果最终返回到用户态，那么内核所使用过的一切vector状态都会丢失，不留痕迹。
>
> 这组补丁的后续代码，将对内核模式的vector抢占使用，提供支持。

---

#### TODO: scenario logic analysis

内核使用vector操作的场景: 

* `vector-crypto`: 内核可能会在普通控制流中使用vector进行加密操作；
* `vector-softirq-enbale`: 在软中断上下文中使用vector；
* `vector-preempt-enable`: 内核线程抢占后使用vector；

```c
//vector-crypto



//vector-softirq-enbale



//vector-preempt-enable

```

## 3.2 includes vectorized `copy_{to,from}_user` into the kernel

[riscv: lib: vectorize copy_to_user/copy_from_user](https://lore.kernel.org/all/20240115055929.4736-6-andy.chiu@sifive.com/)



## 3.3 support for preemptible kernel-mode Vector

* [riscv: vector: do not pass task_struct into riscv_v_vstate_{save,restore}()](https://lore.kernel.org/all/20240115055929.4736-8-andy.chiu@sifive.com/)
* [riscv: vector: use a mask to write vstate_ctrl](https://lore.kernel.org/all/20240115055929.4736-9-andy.chiu@sifive.com/)
* [riscv: vector: use kmem_cache to manage vector context](https://lore.kernel.org/all/20240115055929.4736-10-andy.chiu@sifive.com/)
* [riscv: vector: allow kernel-mode Vector with preemption](https://lore.kernel.org/all/20240115055929.4736-11-andy.chiu@sifive.com/)

引入 `kernel_vstate` ，以在发生陷阱导致的上下文切换时，跟踪内核模式的向量寄存器。此外，提供 `riscv_v_flags` ，以使上下文保存/恢复例程能够跟踪上下文状态。上下文跟踪，发生在hart内核模式向量执行时。活动（脏）的内核任务的向量上下文，将在发生陷阱导致的上下文切换时，被保存至内存。或者，当在其上嵌套发生的软中断（softirq）使用向量时，也会发生上下文保存。上下文恢复发生在执行转回到最初启用 `preempt_v` 的原始内核上下文时。

此外，提供配置选项 `CONFIG_RISCV_ISA_V_PREEMPTIVE`，让用户在构建时，可以选择禁用可抢占的内核模式向量。内存受限的用户可能希望禁用此配置，因为可抢占的内核模式向量需要额外的空间，来跟踪每个线程的内核模式向量上下文。或者，如果所有内核模式向量代码都是时间敏感的，并且不能容忍上下文切换的开销，用户也可能希望禁用它。

> 通常情况下，内核中的SIMD例程在禁用抢占的情况下运行。因此，调用长时间运行的SIMD函数时，必须让出核心的向量单元，以防止长时间阻塞其他任务。
>
> 此配置允许内核，在不显式禁用抢占的情况下运行SIMD。启用此配置将导致更高的内存消耗，因为需要为每个任务分配内核向量上下文。

### 1) kconfig/structure/macros and some helpers

```c
--- a/arch/riscv/Kconfig
+++ b/arch/riscv/Kconfig
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
+
--- a/arch/riscv/include/asm/processor.h
+++ b/arch/riscv/include/asm/processor.h
@@ -80,8 +80,35 @@ struct pt_regs;
  *  - bit 0: indicates whether the in-kernel Vector context is active. The
  *    activation of this state disables the preemption. On a non-RT kernel, it
  *    also disable bh.
+ *  - bits 8: is used for tracking preemptible kernel-mode Vector, when
+ *    RISCV_ISA_V_PREEMPTIVE is enabled. Calling kernel_vector_begin() does not
+ *    disable the preemption if the thread's kernel_vstate.datap is allocated.
+ *    Instead, the kernel set this bit field. Then the trap entry/exit code
+ *    knows if we are entering/exiting the context that owns preempt_v.
+ *     - 0: the task is not using preempt_v
+ *     - 1: the task is actively using preempt_v. But whether does the task own
+ *          the preempt_v context is decided by bits in RISCV_V_CTX_DEPTH_MASK.
+ *  - bit 16-23 are RISCV_V_CTX_DEPTH_MASK, used by context tracking routine
+ *     when preempt_v starts:
+ *     - 0: the task is actively using, and own preempt_v context.
+ *     - non-zero: the task was using preempt_v, but then took a trap within.
+ *       Thus, the task does not own preempt_v. Any use of Vector will have to
+ *       save preempt_v, if dirty, and fallback to non-preemptible kernel-mode
+ *       Vector.
+ *  - bit 30: The in-kernel preempt_v context is saved, and requries to be
+ *    restored when returning to the context that owns the preempt_v.
+ *  - bit 31: The in-kernel preempt_v context is dirty, as signaled by the
+ *    trap entry code. Any context switches out-of current task need to save
+ *    it to the task's in-kernel V context. Also, any traps nesting on-top-of
+ *    preempt_v requesting to use V needs a save.
  */
-#define RISCV_KERNEL_MODE_V	0x1
+#define RISCV_V_CTX_DEPTH_MASK		0x00ff0000
+
+#define RISCV_V_CTX_UNIT_DEPTH		0x00010000
+#define RISCV_KERNEL_MODE_V		0x00000001
+#define RISCV_PREEMPT_V			0x00000100
+#define RISCV_PREEMPT_V_DIRTY		0x80000000
+#define RISCV_PREEMPT_V_NEED_RESTORE	0x40000000
 /* CPU-specific state of a task */
 struct thread_struct {
@@ -95,6 +122,7 @@ struct thread_struct {
 	u32 vstate_ctrl;
 	struct __riscv_v_ext_state vstate;
 	unsigned long align_ctl;
+	struct __riscv_v_ext_state kernel_vstate;
 };
```

```c
/*
 * 我们使用一个标志来跟踪内核中的向量上下文。目前，该标志有以下含义：
 *
 *  - 位 0：指示内核中的向量上下文是否激活。此状态的激活会禁用抢占。在非实时（RT）内核上，它还会禁用底半部（bh）。
 *  - 位 8：用于在启用 RISCV_ISA_V_PREEMPTIVE 时跟踪可抢占的内核模式向量。调用 kernel_vector_begin() 不会禁用抢占，如果线程的 kernel_vstate.datap 被分配的话。相反，内核会设置此位字段。然后陷阱入口/出口代码知道我们是否正在进入/退出拥有 preempt_v 的上下文。
 *     - 0：任务未使用 preempt_v
 *     - 1：任务正在主动使用 preempt_v。但任务是否拥有 preempt_v 上下文由 RISCV_V_CTX_DEPTH_MASK 中的位决定。
 *  - 位 16-23 是 RISCV_V_CTX_DEPTH_MASK，启动 preempt_v 时由上下文跟踪例程使用：
 *     - 0：任务正在主动使用并拥有 preempt_v 上下文。
 *     - 非零：任务曾使用 preempt_v，但随后在其内发生了陷阱。因此，任务不拥有 preempt_v。任何使用向量的操作都必须保存 preempt_v（如果是脏的），并回退到不可抢占的内核模式向量。
 *  - 位 30：内核中的 preempt_v 上下文已保存，返回到拥有 preempt_v 的上下文时需要恢复。
 *  - 位 31：内核中的 preempt_v 上下文为脏，由陷阱入口代码标记。任何当前任务的上下文切换需要将其保存到任务的内核 V 上下文中。此外，任何在 preempt_v 之上嵌套的陷阱请求使用 V 都需要进行保存。
 */
```

```c
-- a/arch/riscv/include/asm/vector.h
+++ b/arch/riscv/include/asm/vector.h
@@ -28,10 +28,11 @@ void get_cpu_vector_context(void);
 void put_cpu_vector_context(void);
 void riscv_v_thread_free(struct task_struct *tsk);
 void __init riscv_v_setup_ctx_cache(void);
+void riscv_v_thread_alloc(struct task_struct *tsk);
 
 static inline u32 riscv_v_flags(void)
 {
-	return current->thread.riscv_v_flags;
+	return READ_ONCE(current->thread.riscv_v_flags);
 }
 
 static __always_inline bool has_vector(void)
@@ -200,14 +201,62 @@ static inline void riscv_v_vstate_set_restore(struct task_struct *task,
 	}
 }
 
+#ifdef CONFIG_RISCV_ISA_V_PREEMPTIVE
+static inline bool riscv_preempt_v_dirty(struct task_struct *task)
+{
+	return !!(task->thread.riscv_v_flags & RISCV_PREEMPT_V_DIRTY);
+}
+
+static inline bool riscv_preempt_v_restore(struct task_struct *task)
+{
+	return !!(task->thread.riscv_v_flags & RISCV_PREEMPT_V_NEED_RESTORE);
+}
+
+static inline void riscv_preempt_v_clear_dirty(struct task_struct *task)
+{
+	barrier();
+	task->thread.riscv_v_flags &= ~RISCV_PREEMPT_V_DIRTY;
+}
+
+static inline void riscv_preempt_v_set_restore(struct task_struct *task)
+{
+	barrier();
+	task->thread.riscv_v_flags |= RISCV_PREEMPT_V_NEED_RESTORE;
+}
+
+static inline bool riscv_preempt_v_started(struct task_struct *task)
+{
+	return !!(task->thread.riscv_v_flags & RISCV_PREEMPT_V);
+}
+
+#else /* !CONFIG_RISCV_ISA_V_PREEMPTIVE */
+static inline bool riscv_preempt_v_dirty(struct task_struct *task) { return false; }
+static inline bool riscv_preempt_v_restore(struct task_struct *task) { return false; }
+static inline bool riscv_preempt_v_started(struct task_struct *task) { return false; }
+#define riscv_preempt_v_clear_dirty(tsk)	do {} while (0)
+#define riscv_preempt_v_set_restore(tsk)	do {} while (0)
+#endif /* CONFIG_RISCV_ISA_V_PREEMPTIVE */
```

```c
+#ifdef CONFIG_RISCV_ISA_V_PREEMPTIVE
+static __always_inline u32 *riscv_v_flags_ptr(void)
+{
+	return &current->thread.riscv_v_flags;
+}
+
+static inline void riscv_preempt_v_set_dirty(void)
+{
+	*riscv_v_flags_ptr() |= RISCV_PREEMPT_V_DIRTY;
+}
+
+static inline void riscv_preempt_v_reset_flags(void)
+{
+	*riscv_v_flags_ptr() &= ~(RISCV_PREEMPT_V_DIRTY | RISCV_PREEMPT_V_NEED_RESTORE);
+}
+
+static inline void riscv_v_ctx_depth_inc(void)
+{
+	*riscv_v_flags_ptr() += RISCV_V_CTX_UNIT_DEPTH;
+}
+
+static inline void riscv_v_ctx_depth_dec(void)
+{
+	*riscv_v_flags_ptr() -= RISCV_V_CTX_UNIT_DEPTH;
+}
+
+static inline u32 riscv_v_ctx_get_depth(void)
+{
+	return *riscv_v_flags_ptr() & RISCV_V_CTX_DEPTH_MASK;
+}
```

### 2) preemptible kernel-mode vector逻辑分析

#### patch overview

* `may_use_simd`

  ```c
  --- a/arch/riscv/include/asm/simd.h
  +++ b/arch/riscv/include/asm/simd.h
  @@ -12,6 +12,7 @@
   #include <linux/percpu.h>
   #include <linux/preempt.h>
   #include <linux/types.h>
  +#include <linux/thread_info.h>
   
   #include <asm/vector.h>
   
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

* `__switch_to_vector`

  ```c
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
  ```

* `entry.S: riscv_v_context_nesting_start/end`

  ```c
  --- a/arch/riscv/kernel/entry.S
  +++ b/arch/riscv/kernel/entry.S
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
  +	call riscv_v_context_nesting_end
  +#endif
   	REG_L a0, PT_STATUS(sp)
   	/*
   	 * The current load reservation is effectively part of the processor's
  ```

  ```c
  +
  +/* low-level V context handling code, called with irq disabled */
  +asmlinkage void riscv_v_context_nesting_start(struct pt_regs *regs)
  +{
  +	int depth;
  +
  +	if (!riscv_preempt_v_started(current))
  +		return;
  +
  +	depth = riscv_v_ctx_get_depth();
  +	if (depth == 0 && (regs->status & SR_VS) == SR_VS_DIRTY)
  +		riscv_preempt_v_set_dirty();
  +
  +	riscv_v_ctx_depth_inc();
  +}
  +
  +asmlinkage void riscv_v_context_nesting_end(struct pt_regs *regs)
  +{
  +	struct __riscv_v_ext_state *vstate = &current->thread.kernel_vstate;
  +	u32 depth;
  +
  +	WARN_ON(!irqs_disabled());
  +
  +	if (!riscv_preempt_v_started(current))
  +		return;
  +
  +	riscv_v_ctx_depth_dec();
  +	depth = riscv_v_ctx_get_depth();
  +	if (depth == 0) {
  +		if (riscv_preempt_v_restore(current)) {
  +			__riscv_v_vstate_restore(vstate, vstate->datap);
  +			__riscv_v_vstate_clean(regs);
  +			riscv_preempt_v_reset_flags();
  +		}
  +	}
  +}
  ```

* `riscv_v_{start/stop}_kernel_context`

  ```c
  +static int riscv_v_stop_kernel_context(void)
  +{
  +	if (riscv_v_ctx_get_depth() != 0 || !riscv_preempt_v_started(current))
  +		return 1;
  +
  +	riscv_preempt_v_clear_dirty(current);
  +	riscv_v_stop(RISCV_PREEMPT_V);
  +	return 0;
  +}
  +
  +static int riscv_v_start_kernel_context(bool *is_nested)
  +{
  +	struct __riscv_v_ext_state *kvstate, *uvstate;
  +
  +	kvstate = &current->thread.kernel_vstate;
  +	if (!kvstate->datap)
  +		return -ENOENT;
  +
  +	if (riscv_preempt_v_started(current)) {
  +		WARN_ON(riscv_v_ctx_get_depth() == 0);
  +		*is_nested = true;
  +		get_cpu_vector_context();
  +		if (riscv_preempt_v_dirty(current)) {
  +			__riscv_v_vstate_save(kvstate, kvstate->datap);
  +			riscv_preempt_v_clear_dirty(current);
  +		}
  +		riscv_preempt_v_set_restore(current);
  +		return 0;
  +	}
  +
  +	/* Transfer the ownership of V from user to kernel, then save */
  +	riscv_v_start(RISCV_PREEMPT_V | RISCV_PREEMPT_V_DIRTY);
  +	if ((task_pt_regs(current)->status & SR_VS) == SR_VS_DIRTY) {
  +		uvstate = &current->thread.vstate;
  +		__riscv_v_vstate_save(uvstate, uvstate->datap);
  +	}
  +	riscv_preempt_v_clear_dirty(current);
  +	return 0;
  +}
  ```

  ```c
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
  ```

---

#### scenario logic analysis 🔥

> 或许，你应该按照如下的vector控制流，进行分析：
>
> 1. 用户态携带vector状态，陷入内核；
> 2. 内核执行vector操作，但此时还仅仅为 `kernel-mode-vector`，并非嵌套；
> 3. 开启可抢占的vector模式后，内核在执行vector操作途中可能被抢占，先假设为中断抢占了内核vector线程 (此时，vector才处于嵌套场景)；
> 4. 嵌套中断上下文中，此时depth仍为0，一旦执行vector操作，在vector代码前后将调用 `kernel_vector_begin/end`；（这个阶段中断是否开启？是否还能继续嵌套？）

我们使用一个标志来跟踪内核中的向量上下文。目前该标志具有以下含义：

- `bit 0`：指示内核中的向量上下文是否激活。该状态的激活会禁用抢占。在非实时内核（non-RT kernel）中，它也会禁用下半部（bh）。
- `bit 8`：当启用 RISCV_ISA_V_PREEMPTIVE 时，用于跟踪可抢占的内核模式向量。调用 kernel_vector_begin() 不会禁用抢占，如果线程的 kernel_vstate.datap 已分配。相反，内核会设置这个位字段。然后陷阱（trap）入口/出口代码知道我们是否进入/退出拥有 preempt_v 的上下文。
  - `0`：任务未使用 preempt_v
  - `1`：任务正在主动使用 preempt_v。但任务是否拥有 preempt_v 上下文由 RISCV_V_CTX_DEPTH_MASK 中的位决定。
- `bit 16-23` 是 RISCV_V_CTX_DEPTH_MASK，当 preempt_v 开始时由上下文跟踪例程使用：
  - `0`：任务正在主动使用并拥有 preempt_v 上下文。
  - `non-zero`：任务曾使用 preempt_v，但随后在其中发生了陷阱（trap）。因此，任务不再拥有 preempt_v。任何向量的使用都必须保存 preempt_v（如果是脏的），并回退到不可抢占的内核模式向量。
- `bit 30`：内核中的 preempt_v 上下文已保存，需要在返回拥有 preempt_v 的上下文时恢复。
- `bit 31`：内核中的 preempt_v 上下文是脏的，由陷阱入口代码标记。任何从当前任务切换出去的上下文需要将其保存到任务的内核 V 上下文。此外，任何在 preempt_v 上嵌套的陷阱请求使用 V 时需要保存。

```c
handle_exception
+-> move a0, sp
		call riscv_v_context_nesting_start //该函数在中断嵌套时调用,流程才能走完

/* low-level V context handling code, called with irq disabled */
asmlinkage void riscv_v_context_nesting_start(struct pt_regs *regs)
{
	int depth;
	
  //current是否标记RISCV_PREEMPT_V,嵌套中断上下文中使用过vector才设置此标记
  //如果这里检测到current已被标记,后续进行嵌套vector的一些处理,否则直接返回
	if (!riscv_preempt_v_started(current))
		return;
	
  //depth表示vector嵌套深度,depth=0表示这是第一层嵌套,且当前kernel-vector为脏
  //标记current为RISCV_PREEMPT_V_DIRTY,这表示kernel-vstate需要在适当时机保存
	depth = riscv_v_ctx_get_depth();
	if (depth == 0 && (regs->status & SR_VS) == SR_VS_DIRTY)
		riscv_preempt_v_set_dirty();

  //depth+=1
	riscv_v_ctx_depth_inc();
}
```

```c
//中断还能继续嵌套吗？
==========================> //继续走中断处理流程
do_irq
+-> low_level_interrupt_handler //假设在此嵌套中断上下文中使用vector
  	+-> kernel_vector_begin			//1) 
  			+-> //...
  	+-> /* do vector... */
  	+-> kernel_vector_end				//2)
  			+-> //...
  
===========================> //1)
void kernel_vector_begin(void)
{
	bool nested = false;

	if (WARN_ON(!has_vector()))
		return;
	
  //
	BUG_ON(!may_use_simd());

	if (riscv_v_start_kernel_context(&nested)) {
		get_cpu_vector_context();
		riscv_v_vstate_save(&current->thread.vstate, task_pt_regs(current));
	}

	if (!nested)
		riscv_v_vstate_set_restore(current, task_pt_regs(current));

	riscv_v_enable();
}

===========================> //2)
void kernel_vector_end(void)
{
	if (WARN_ON(!has_vector()))
		return;

	riscv_v_disable();

	if (riscv_v_stop_kernel_context())
		put_cpu_vector_context();
}
```



```c
// `do_irq`执行完毕返回
ret_from_exception
+-> move a0, sp
	  call riscv_v_context_nesting_end
  
  
  
  
  
```

















