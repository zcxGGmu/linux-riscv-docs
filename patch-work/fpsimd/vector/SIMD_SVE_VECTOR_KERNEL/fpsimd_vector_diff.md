# 1 引用







# 2 arm64_fpsimd_commit

## 2.1 kernel/fpsimd.c

[fpsimd.c - arch/arm64/kernel/fpsimd.c - Linux source code (v6.8.6) - Bootlin](https://elixir.bootlin.com/linux/latest/source/arch/arm64/kernel/fpsimd.c#L416)

```shell
61da7c8e2a60	2024-01-30	Mark Brown	arm64/signal: Don't assume that TIF_SVE means we saved SVE state
63a2d92e1461	2023-12-12	Mark Rutland	arm64: Cleanup system cpucap handling
2632e2521769	2023-12-08	Ard Biesheuvel	arm64: fpsimd: Implement lazy restore for kernel mode FPSIMD
aefbab8e77eb	2023-12-08	Ard Biesheuvel	arm64: fpsimd: Preserve/restore kernel mode NEON at context switch
9b19700e623f	2023-12-08	Ard Biesheuvel	arm64: fpsimd: Drop unneeded 'busy' flag

a76521d16028	2023-10-16	Mark Rutland	arm64: Avoid cpus_have_const_cap() for ARM64_{SVE,SME,SME2,FA64}
34f66c4c4d55	2023-10-16	Mark Rutland	arm64: Use a positive cpucap for FP/SIMD
14567ba42c57	2023-10-16	Mark Rutland	arm64: Rename SVE/SME cpu_enable functions
907722917002	2023-10-16	Mark Rutland	arm64: Use build-time assertions for cpucap ordering

1192b93ba352	2022-11-15	Mark Brown	arm64/fp: Use a struct to pass data to fpsimd_bind_state_to_cpu()
8c845e273104	2022-11-15	Mark Brown	arm64/sve: Leave SVE enabled on syscall if we don't context switch
bbc6172eefdb	2022-11-15	Mark Brown	arm64/fpsimd: SME no longer requires SVE register state
a0136be443d5	2022-11-15	Mark Brown	arm64/fpsimd: Load FP state based on recorded data type
62021cc36add	2022-11-15	Mark Brown	arm64/fpsimd: Stop using TIF_SVE to manage register saving in KVM
deeb8f9a80fd	2022-11-15	Mark Brown	arm64/fpsimd: Have KVM explicitly say which FP registers to save
baa8515281b3	2022-11-15	Mark Brown	arm64/fpsimd: Track the saved FPSIMD state type separately to TIF_SVE
93ae6b01bafe	2022-11-15	Mark Brown	KVM: arm64: Discard any SVE state when entering KVM guests
aaeca9845643	2022-11-07	Mark Brown	arm64/fpsimd: Make kernel_neon_ API _GPL

2e990e63220b	2022-06-02	Mark Brown	arm64/sme: Fix EFI save/restore
bb314511b6dc	2022-06-10	Xiang wangx	arm64/fpsimd: Fix typo in comment

696207d4258b	2022-05-05	Sebastian Andrzej Siewior	arm64/sve: Make kernel FPU protection RT friendly
a1259dd80719	2022-05-05	Sebastian Andrzej Siewior	arm64/sve: Delay freeing memory in fpsimd_flush_thread()
8d56e5c5a99c	2022-04-25	Alexandru Elisei	arm64: Treat ESR_ELx as a 64-bit register

432110cd83ca	2022-01-24	Mark Brown	arm64/fpsimd: Clarify the purpose of using last in fpsimd_save()

12b792e5e234	2021-12-07	Mark Brown	arm64/fp: Add comments documenting the usage of state restore functions
30c43e73b3fa	2021-12-10	Mark Brown	arm64/sve: Generalise vector length configuration prctl() for SME
97bcbee404e3	2021-12-10	Mark Brown	arm64/sve: Make sysctl interface for SVE reusable by SME
31aa126de88e	2021-10-21	Marc Zyngier arm64/fpsimd: Document the use of TIF_FOREIGN_FPSTATE by KVM
04ee53a55543	2021-10-22	Mark Brown	arm64/sve: Fix warnings when SVE is disabled
5838a1557984	2021-10-19	Mark Brown	arm64/sve: Track vector lengths for tasks in an array
ddc806b5c475	2021-10-19	Mark Brown	arm64/sve: Explicitly load vector length when restoring SVE state
b5bc00ffddc0	2021-10-19	Mark Brown	arm64/sve: Put system wide vector length information into structs
0423eedcf4e1	2021-10-19	Mark Brown	arm64/sve: Use accessor functions for vector lengths in thread_struct

12cc2352bfb3	2021-10-19	Mark Brown	arm64/sve: Make sve_state_size() static
2d481bd3b636	2021-10-19	Mark Brown	arm64/fp: Reindent fpsimd_save()
e35ac9d0b56e	2021-09-09	Mark Brown	arm64/sve: Use correct size when reinitialising SVE state
7559b7d7d651	2021-08-24	Mark Brown	arm64/sve: Better handle failure to allocate SVE register storage
b24b5205099a	2021-07-30	Mark Brown	arm64/sve: Make fpsimd_bind_task_to_cpu() static

087dfa5ca7d8	2021-04-15	Mark Brown	arm64/sve: Add compile time checks for SVE hooks in generic functions
ef9c5d09797d	2021-04-12	Mark Brown	arm64/sve: Remove redundant system_supports_sve() tests
13150149aa6d	2021-03-02	Ard Biesheuvel	arm64: fpsimd: run kernel mode NEON with softirqs disabled
cccb78ce89c4	2021-03-12	Mark Brown	arm64/sve: Rework SVE access trap to convert state in registers

52f73c383b24	2020-01-13	Suzuki K Poulose	arm64: nofpsmid: Handle TIF_FOREIGN_FPSTATE flag cleanly

6dcdefcde413	2019-05-21	Julien Grall	arm64/fpsimd: Don't disable softirq when touching FPSIMD/SVE state
54b8c7cbc57c	2019-05-21	Julien Grall	arm64/fpsimd: Introduce fpsimd_save_and_flush_cpu_state() and use it

ead9e430c0fb	2018-09-28	Dave Martin	arm64/sve: In-kernel vector length availability query interface
0495067420f3	2018-09-28	Dave Martin	arm64/sve: Enable SVE state tracking for non-task contexts
efbc20249fee	2018-09-28	Dave Martin	arm64: fpsimd: Always set TIF_FOREIGN_FPSTATE on task state flush

e6b673b741ea	2018-04-06	Dave Martin	KVM: arm64: Optimise FPSIMD handling to reduce guest/host thrashing
0cff8e776f8f	2018-05-09	Dave Martin	arm64/sve: Refactor user SVE trap maintenance for external use
df3fb9682045	2018-05-21	Dave Martin	arm64: fpsimd: Eliminate task->mm checks
d179761519d9	2018-04-06	Dave Martin	arm64: fpsimd: Generalise context saving for non-task contexts
09d1223a6279	2018-04-11	Dave Martin	arm64: Use update{,_tsk}_thread_flag()
d8ad71fa38a9	2018-05-21	Dave Martin	arm64: fpsimd: Fix TIF_FOREIGN_FPSTATE after invalidating cpu regs
20b8547277a6	2018-03-28	Dave Martin	arm64: fpsimd: Split cpu field out from struct fpsimd_state

a45448313706	2017-12-15	Will Deacon	arm64: fpsimd: Fix copying of FP state from signal frame into task struct
cb968afc7898	2017-12-06	Dave Martin	arm64/sve: Avoid dereference of dead task_struct in KVM guest entry
8884b7bd7e52	2017-12-06	Dave Martin	arm64: fpsimd: Abstract out binding of task's fpsimd context to the cpu.

43d4da2c45b2	2017-10-31	Dave Martin	arm64/sve: ptrace and ELF coredump support
fdfa976cae5c	2017-10-31	Dave Martin	arm64/sve: Preserve SVE registers around EFI runtime service calls
9cf5b54fafed	2017-10-31	Dave Martin	arm64: fpsimd: Simplify uses of {set,clear}_ti_thread_flag()
94ef7ecbdf6f	2017-10-31	Dave Martin	arm64: fpsimd: Correctly annotate exception helpers called from asm
ae2e972dae3c	2017-10-06	Suzuki K Poulose	arm64: Ensure fpsimd support is ready before userspace is active
e580b8bc4316	2017-09-18	Dave Martin	arm64: efi: Don't include EFI fpsimd save/restore code in non-EFI kernels
3b66023d574f	2017-08-18	Dave Martin	arm64: neon/efi: Make EFI fpsimd save/restore variables static
11cefd5ac25f	2017-08-07	Catalin Marinas	arm64: neon: Export kernel_neon_busy to loadable modules
cb84d11e1625	2017-08-03	Dave Martin	arm64: neon: Remove support for nested or hardirq kernel-mode NEON
4328825d4fdc	2017-08-03	Dave Martin	arm64: neon: Allow EFI runtime services to use FPSIMD in irq context
82e0191a1aa1	2016-11-08	Suzuki K Poulose	arm64: Support systems without FP/ASIMD
c23a7266e659	2016-09-06	Sebastian Andrzej Siewior	arm64/FP/SIMD: Convert to hotplug state machine
fe80f9f2da10	2015-10-19	Suzuki K. Poulose	arm64: Move FP/ASIMD hwcap handling to common code
674c242c9323	2015-08-27	Ard Biesheuvel	arm64: flush FP/SIMD state correctly after execve()
32365e64a20e	2015-06-11	Janet Liu	arm64: fix bug for reloading FPSIMD state after CPU hotplug.
7c68a9cc0402	2014-09-01	Leo Yan	arm64: fix bug for reloading FPSIMD state after cpu power off
c51f92693c35	2014-02-24	Ard Biesheuvel	arm64: add abstractions for FPSIMD state manipulation
fb1ab1ab3889	2013-07-19	Lorenzo Pieralisi	arm64: kernel: implement fpsimd CPU PM notifier
```

* TIF_FOREIGN_FPSTATE

* fpsimd hotplug init

  * [tip:smp/hotplug\] arm64/FP/SIMD: Convert to hotplug state machine - tip-bot for Sebastian Andrzej Siewior (kernel.org)](https://lore.kernel.org/all/tip-c23a7266e6599e74305cc5b790f93398bb212380@git.kernel.org/)

* EFI FPSIMD

  * [PATCH 4/5\] arm64: neon: Allow EFI runtime services to use FPSIMD in irq context - Dave Martin (kernel.org)](https://lore.kernel.org/all/1501777403-9782-5-git-send-email-Dave.Martin@arm.com/)

* implement fpsimd CPU PM notifier

  * [PATCH v2 06/13\] arm64: kernel: implement fpsimd CPU PM notifier - Lorenzo Pieralisi](https://lore.kernel.org/all/1381748590-14279-7-git-send-email-lorenzo.pieralisi@arm.com/)

    > 当CPU进入低功耗状态时，其浮点寄存器（FP register）的内容会丢失。这个补丁添加了一个通知器，在CPU关闭时保存FP上下文，并在CPU恢复时恢复它。只有在挂起的线程不是内核线程时，才会保存和恢复上下文，这反映了当前上下文切换的行为。



## 2.2 kvm/fpsimd.c

[fpsimd.c - arch/arm64/kvm/fpsimd.c - Linux source code (v6.8.6) - Bootlin](https://elixir.bootlin.com/linux/latest/source/arch/arm64/kvm/fpsimd.c)

```shell
e6b673b741ea    2018-04-06      Dave Martin     KVM: arm64: Optimise FPSIMD handling to reduce guest/host thrashing
85acda3b4a27    2018-04-20      Dave Martin     KVM: arm64: Save host SVE context as appropriate
b045e4d0f392    2018-06-15      Dave Martin     KVM: arm64: Don't mask softirq with IRQs disabled in vcpu_put()
b3eb56b629d1    2018-06-15      Dave Martin     KVM: arm64/sve: Fix SVE trap restoration for non-current tasks
2955bcc8c309    2018-06-15      Dave Martin     KVM: arm64: Avoid mistaken attempts to save SVE state for vcpus
0495067420f3    2018-09-28      Dave Martin     arm64/sve: Enable SVE state tracking for non-task contexts
73433762fcae    2018-09-28      Dave Martin     KVM: arm64/sve: System register context switch and access support
b43b5dd990eb    2018-09-28      Dave Martin     KVM: arm64/sve: Context switch the SVE registers
54b8c7cbc57c    2019-05-21      Julien Grall    arm64/fpsimd: Introduce fpsimd_save_and_flush_cpu_state() and use it
4d395762599d    2020-02-28      Peter Xu        KVM: Remove unnecessary asm/kvm_host.h includes
308472c69213    2019-07-04      Marc Zyngier    KVM: arm64: sve: Use __vcpu_sys_reg() instead of raw sys_regs access
e47c2055c68e    2019-06-28      Marc Zyngier    KVM: arm64: Make struct kvm_regs userspace-only
83857371d4cb    2021-03-11      Marc Zyngier    KVM: arm64: Use {read,write}_sysreg_el1 to access ZCR_EL1
0a9a98fda3a2    2021-03-11      Marc Zyngier    KVM: arm64: Map SVE context at EL2 when available
b145a8437aab    2021-03-12      Marc Zyngier    KVM: arm64: Save guest's ZCR_EL1 before saving the FPSIMD state
8c8010d69c13    2021-03-11      Marc Zyngier    KVM: arm64: Save/restore SVE state for nVHE
8383741ab2e7    2021-10-27      Marc Zyngier    KVM: arm64: Get rid of host SVE tracking/saving
af9a0e21d817    2021-10-21      Marc Zyngier    KVM: arm64: Introduce flag shadowing TIF_FOREIGN_FPSTATE
bee14bca735a    2021-10-21      Marc Zyngier    KVM: arm64: Stop mapping current thread_info at EL2
bff01a61af3c    2021-10-14      Marc Zyngier    KVM: arm64: Move SVE state mapping at HYP to finalize-time

23afc82539cf    2022-01-24      Mark Brown      KVM: arm64: Add comments for context flush and sync callbacks

861262ab8627    2022-04-19      Mark Brown      KVM: arm64: Handle SME host state when running guests
ec0067a63e5a    2022-05-10      Mark Brown      arm64/sme: Remove _EL0 from name of SVCR - FIXME sysreg.h
d52d165d67c5    2022-05-28      Marc Zyngier    KVM: arm64: Always start with clearing SVE flag on load
039f49c4cafb    2022-05-28      Marc Zyngier    KVM: arm64: Always start with clearing SME flag on load
e9ada6c208c1    2022-05-28      Marc Zyngier    KVM: arm64: Drop FP_FOREIGN_STATE from the hypervisor code
f8077b0d5923    2022-05-28      Marc Zyngier    KVM: arm64: Move FP state ownership from flag to a tristate
0affa37fcd1d    2022-05-28      Marc Zyngier    KVM: arm64: Move vcpu SVE/SME flags to the state flag set
b4da91879e98    2022-06-08      Marc Zyngier    KVM: arm64: Move the handling of !FP outside of the fast path
93ae6b01bafe    2022-11-15      Mark Brown      KVM: arm64: Discard any SVE state when entering KVM guests
baa8515281b3    2022-11-15      Mark Brown      arm64/fpsimd: Track the saved FPSIMD state type separately to TIF_SVE
deeb8f9a80fd    2022-11-15      Mark Brown      arm64/fpsimd: Have KVM explicitly say which FP registers to save
62021cc36add    2022-11-15      Mark Brown      arm64/fpsimd: Stop using TIF_SVE to manage register saving in KVM
1192b93ba352    2022-11-15      Mark Brown      arm64/fp: Use a struct to pass data to fpsimd_bind_state_to_cpu()
59d78a2ec0e9    2022-12-20      Nianyao Tang    KVM: arm64: Synchronize SMEN on vcpu schedule out
ce514000da4f    2023-01-16      Mark Brown      arm64/sme: Rename za_state to sme_state

4c181e3d352e    2023-03-07      Mark Brown      KVM: arm64: Document check for TIF_FOREIGN_FPSTATE
aaa2f14e6f3f    2023-03-07      Mark Brown      KVM: arm64: Clarify host SME state management
75c76ab5a641    2023-06-09      Marc Zyngier    KVM: arm64: Rework CPTR_EL2 programming for HVHE configuration
75841d89f3ed    2024-01-03      Bjorn Helgaas   KVM: arm64: Fix typos
203f2b95a882    2024-03-06      Mark Brown      arm64/fpsimd: Support FEAT_FPMR
```

* `kvm_arch_vcpu_ctxflush_fp/kvm_arch_vcpu_ctxsync_fp`：在Host/Guest world切换前后，未支持fp/vector flush/sync





# 3 riscv_vector_commit

## 3.1 kernel/vector.c

[vector.c - arch/riscv/kernel/vector.c - Linux source code (v6.8) - Bootlin](https://elixir.bootlin.com/linux/v6.8/source/arch/riscv/kernel/vector.c)

```shell
7017858eb2d7    2023-06-05      Greentime Hu    riscv: Introduce riscv_v_vsize to record size of Vector context
cd054837243b    2023-06-05      Andy Chiu       riscv: Allocate user's vector context in the first-use trap
1fd96a3e9d5d    2023-06-05      Andy Chiu       riscv: Add prctl controls for userspace vector management
7ca7a7b9b635    2023-06-05      Andy Chiu       riscv: Add sysctl to set the default vector rule for new processes
75b59f2a90aa    2023-06-27      Andy Chiu       riscv: vector: clear V-reg in the first-use trap
f6ca506f4237    2023-10-02      Joel Granados   riscv: Remove now superfluous sentinel element from ctl_table array
7df56cbc27e4    2024-01-15      Andy Chiu       riscv: sched: defer restoring Vector context for user
5b6048f2ff71    2024-01-15      Andy Chiu       riscv: vector: use a mask to write vstate_ctrl
bd446f5df5af    2024-01-15      Andy Chiu       riscv: vector: use kmem_cache to manage vector context
2080ff949307    2024-01-15      Andy Chiu       riscv: vector: allow kernel-mode Vector with preemption
```







## 3.2 kernel/kernel_mode_vector.c

[kernel_mode_vector.c - arch/riscv/kernel/kernel_mode_vector.c - Linux source code (v6.8) - Bootlin](https://elixir.bootlin.com/linux/v6.8/source/arch/riscv/kernel/kernel_mode_vector.c)

```shell
ecd2ada8a5e0    2024-01-15      Greentime Hu    riscv: Add support for kernel mode vector
956895b9d8f7    2024-01-15      Andy Chiu       riscv: vector: make Vector always available for softirq context
7df56cbc27e4    2024-01-15      Andy Chiu       riscv: sched: defer restoring Vector context for user
d6c78f1ca3e8    2024-01-15      Andy Chiu       riscv: vector: do not pass task_struct into riscv_v_vstate_{save,restore}()
2080ff949307    2024-01-15      Andy Chiu       riscv: vector: allow kernel-mode Vector with preemption
```



## 3.3 kvm/vcpu_vector.c

[vcpu_vector.c - arch/riscv/kvm/vcpu_vector.c - Linux source code (v6.8) - Bootlin](https://elixir.bootlin.com/linux/v6.8/source/arch/riscv/kvm/vcpu_vector.c)

```shell
0f4b82579716    2023-06-05      Vincent Chen    riscv: KVM: Add vector lazy save/restore support
1deaf754f531    2023-08-03      Andrew Jones    RISC-V: KVM: Improve vector save/restore errors
630b4cee9c37    2023-08-04      Andrew Jones    RISC-V: KVM: Improve vector save/restore functions
e72c4333d2f2    2023-10-31      Xiao Wang       riscv: Rearrange hwcap.h and cpufeature.h
197bd237b672    2023-12-05      Daniel Henrique Barboza RISC-V: KVM: set 'vlenb' in kvm_riscv_vcpu_alloc_vector_context()
2fa290372dfe    2023-12-05      Daniel Henrique Barboza RISC-V: KVM: add 'vlenb' Vector CSR%
```





