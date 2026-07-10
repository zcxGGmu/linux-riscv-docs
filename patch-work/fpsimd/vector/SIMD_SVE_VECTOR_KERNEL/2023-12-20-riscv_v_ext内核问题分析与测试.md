---
title: riscv_v_ext内核问题分析与测试

date: 2023-12-20 17:00:00 +0800

categories: [SIMD内核支持]

tags: [vector]

description: 
---

# 0 资料

[[PATCH v10 00/16\] riscv: Add vector ISA support - Greentime Hu (kernel.org)](https://lore.kernel.org/all/cover.1652257230.git.greentime.hu@sifive.com/)

[vcpu_vector.c - arch/riscv/kvm/vcpu_vector.c - Linux source code (v6.7-rc6) - Bootlin](https://elixir.bootlin.com/linux/v6.7-rc6/source/arch/riscv/kvm/vcpu_vector.c#L60)

[[PATCH v10 16/16\] riscv: KVM: Add vector lazy save/restore support - Greentime Hu (kernel.org)](https://lore.kernel.org/all/8174f9e04cbb55b8bdeceeb0ca6ff2bdd748290c.1652257230.git.greentime.hu@sifive.com/)

# 1 背景

关于host kernel/kvm针对riscv vector上下文切换的开销问题：

* **host kernel**
  * `vstate_save/vstate_restor` 是否调用仅受 `has_vector()` 限制，正常场景下我们想在用户态运行使用vector指令编写的程序，内核编译时开启vector选项，在线程切换时可以正确的保存/恢复 `prev/next` 上下文。到目前为止一切正常，内核为保证用户态程序执行状态的正确性必然要保存/恢复vector上下文。
    * 但在riscv多核系统上的所有程序都一定存在vector需求吗？
    * 那些不存在vector需求的程序在运行过程中参与调度，会经历一些 “没必要的vector上下文切换” 过程，性能是否会造成损失？
* **kvm guests**
  * 实际上对于虚拟化场景，也具有和裸机相同的问题。虽然目前内核中已经做了 `lazy save/restore`，只要不参与vcpu线程的全局调度，在 `kvm_world_switch` 场景下完全不需要保存恢复vector相关内容；
  * 一旦guest使用了vector，vcpu在调度过程中必须要携带这部分内容，这是完全正确的。但相关的函数 `kvm_riscv_vcpu_guest_vector_save/kvm_riscv_vcpu_host_vector_restore` 在 vcpu_load/vcpu_put 中，有以下情况会调用这些函数：
    * 全局vcpu调度：在 guest 不使用vector时存在无谓开销；
    * vcpu退出到用户态处理相关事务：如果vcpu从退出到返回guest整个过程中不参与调度，我们让目前pCPU上存在的vector内容一直保留着就可以了，去调用 `*_vector_save/restore` 这些函数也是没必要的；

无论对于虚拟化还是非虚拟化场景，解决这个问题可能需要硬件的参与，两种方案：

1. 硬件参与：我们需要调整并控制vector指令的Trap机制，当vector指令首次运行时会触发Trap陷入host kernel/kvm，然后内核会标记一个 flag 表示用户态确实在使用vector指令（即使用pCPU上的这些vector寄存器组），然后在相关的调用路径上开启 vector 保存/恢复工作；
2. **<font color='red'>仅靠软件能实现吗？？？</font>**
   * 非虚拟化：
   * 虚拟化：

> 具体思路：
>
> * 测试：首先在非虚拟化环境下，跑一个多线程应用程序，该程序不会使用任何vector指令，在以下两种内核环境上运行：
>   * 开启 `has_vector` 
>   * 不开启 `has_vector`
> * 分析 ARMv8 fpsimd 的内核支持，对比 riscv vector，分析异同点，是否是由硬件机制的差异导致的，还是riscv的内核支持不完善？

 

# 2 测试







