# RISC-V 向量内核支持系列补丁（2024-01-15）技术分析

> 说明：本分析按用户给出的链接顺序整理。该批次属于 linux-riscv 邮件列表的 v11 系列（00/10~10/10）。用户列表中缺少 02/10 的链接，因此本文仅标注其缺失并不展开。citeturn16view0  
> 所有代码逻辑分析基于邮件补丁内容（lists.infradead.org 存档）。

## 0. 系列概览（对应链接 -1，cover letter）

该系列整体目标是**在 RISC-V 内核中安全、高效地支持向量（V）指令的内核态使用**，并配套改进向量上下文保存/恢复、拷贝性能与内核可抢占性等路径。核心主题包括：

- 引入 `kernel_vector_begin()/end()` 作为内核态向量使用的统一护栏。
- 通过延迟恢复（defer restore）减少不必要的向量上下文恢复成本。
- 用向量指令加速 XOR 与 copy_to_user/copy_from_user。
- 增强向量上下文管理（kmem_cache、vstate_ctrl 掩码）。
- 支持 **可抢占的内核态向量**（preemptible kernel-mode Vector）。

（系列封面信主要列出上述主题，详见列表存档的 00/10。）citeturn17view0

> **缺失说明**：用户链接未包含 02/10（v11 02/10）补丁；该补丁与软中断上下文的向量可用性相关，本文不展开。citeturn16view0

---

## 1. [v11 01/10] riscv: Add support for kernel mode vector（对应链接 -2）

### 1.1 关键改动

1. **新增内核态向量入口/出口**：`kernel_vector_begin()` / `kernel_vector_end()`，并提供 `get_cpu_vector_context()` / `put_cpu_vector_context()` 来统一管理 CPU 向量寄存器的所有权。citeturn17view1  
2. **新增 `arch/riscv/kernel/kernel_mode_vector.c`**，将内核态向量使用的保存/恢复逻辑集中实现。citeturn17view1  
3. 引入 `arch/riscv/include/asm/simd.h` 中的 `may_use_simd()` 判定，用于限制向量在中断等非法上下文使用。citeturn17view1  
4. `thread_struct` 增加 `riscv_v_flags`，并定义 `RISCV_KERNEL_MODE_V` 标志用于跟踪内核态向量上下文。citeturn17view1

### 1.2 代码逻辑

- `kernel_vector_begin()`：
  1. 检查 `has_vector()` 和 `may_use_simd()`；
  2. 通过 `get_cpu_vector_context()` 禁止抢占并标记内核态向量使用；
  3. 保存当前任务的用户态 V 状态；
  4. 开启向量执行。citeturn17view1

- `kernel_vector_end()`：
  1. 关闭向量执行；
  2. 恢复用户态向量状态；
  3. 释放上下文（允许抢占）。citeturn17view1

### 1.3 设计意义

此补丁奠定了内核态向量使用的“护栏”机制，使后续性能补丁（XOR、用户拷贝等）可以复用 `kernel_vector_begin/end()`，并避免在错误上下文下滥用向量寄存器。citeturn17view1

---

## 2. [v11 03/10] riscv: Add vector extension XOR implementation（对应链接 -4）

### 2.1 关键改动

- 增加 RVV 优化 XOR 例程：`xor_regs_2_` ~ `xor_regs_5_`（汇编实现）。citeturn17view2  
- 新增 `arch/riscv/include/asm/xor.h` 中的 `xor_vector_*` 封装，调用 `kernel_vector_begin/end()` 包裹向量 XOR。citeturn17view2  
- 将 RVV XOR 作为 XOR 框架候选模板。citeturn17view2

### 2.2 代码逻辑

- 向量 XOR 汇编实现循环：
  - `vsetvli` 配置 VL；
  - `vle8.v` 载入多个输入；
  - `vxor.vv` 逐步合并；
  - `vse8.v` 写回。citeturn17view2  

- C 侧封装确保内核态向量寄存器的保存/恢复正确：
  - `kernel_vector_begin()` → XOR 汇编 → `kernel_vector_end()`。citeturn17view2

### 2.3 设计意义

在 RAID/XOR 等热点路径中引入向量加速，配合 01/10 提供的 kernel-mode vector 机制，实现安全可控的性能提升。citeturn17view2

---

## 3. [v11 04/10] riscv: sched: defer restoring Vector context for user（对应链接 -5）

### 3.1 关键改动

- 新增 `TIF_RISCV_V_DEFER_RESTORE` 标志位，表示**用户态 V 上下文恢复延迟**。citeturn17view3  
- `arch_exit_to_user_mode_prepare()` 中在返回用户态前恢复向量上下文。citeturn17view3  
- `__switch_to_vector()` 由“立即恢复”改为“设置延迟恢复标志”。citeturn17view3  
- `kernel_vector_end()` 也改为仅标记延迟恢复，而非立刻恢复。citeturn17view3

### 3.2 核心逻辑

- 任务切换：保存 old 任务 V 状态；对 new 任务只设置 `TIF_RISCV_V_DEFER_RESTORE`，不立即恢复。citeturn17view3  
- 返回用户态前，统一在 `arch_exit_to_user_mode_prepare()` 恢复向量寄存器。citeturn17view3

### 3.3 设计意义

避免在内核态中频繁恢复 V 寄存器，尤其是多次内核态切换后只真正恢复最终要返回用户态的任务，降低上下文切换成本。citeturn17view3

---

## 4. [v11 05/10] riscv: lib: vectorize copy_to_user/copy_from_user（对应链接 -6）

### 4.1 关键改动

- 新增 `__asm_vector_usercopy`（RVV 汇编实现），支持向量化用户拷贝。citeturn19view0  
- 引入 `enter_vector_usercopy()`，根据阈值决定使用向量或标量路径，并在异常时回退标量。citeturn19view0  
- 在 `__asm_copy_to_user` 中增加 `ALTERNATIVE` 分支与阈值判断，按需跳转到向量拷贝。citeturn19view0

### 4.2 代码逻辑

- `enter_vector_usercopy()`：
  - 若 `may_use_simd()` 允许 → `kernel_vector_begin()` → `__asm_vector_usercopy` → `kernel_vector_end()`；
  - 若发生异常或剩余未复制 → 回退到标量实现。citeturn19view0

- `__asm_vector_usercopy`：
  - 通过 `SR_SUM` 允许访问用户态内存；
  - 使用 RVV load/store 迭代拷贝；
  - 发生异常则通过 extable 修复并回退。citeturn19view0

### 4.3 设计意义

在“大块内存拷贝”场景下显著提升性能，同时保留异常回退路径保证安全性。citeturn19view0

---

## 5. [v11 06/10] riscv: fpu: drop SR_SD bit checking（对应链接 -7）

### 5.1 改动内容

- 移除 `SR_SD` 总览位判断，直接保存 FPU 状态。citeturn19view1

### 5.2 逻辑意义

`SR_SD` 只是对 FS/VS/XS 的汇总，拆分管理后反而增加复杂度，直接保存简化了 FPU 上下文切换逻辑，并与向量上下文改造保持一致。citeturn19view1

---

## 6. [v11 07/10] riscv: vector: do not pass task_struct into riscv_v_vstate_{save,restore}（对应链接 -8）

### 6.1 关键改动

- `riscv_v_vstate_save/restore()` 从接收 `task_struct` 改为接收 `__riscv_v_ext_state *`。citeturn19view2  
- 调用者自行传入 `current->thread.vstate` 或内核态 `kernel_vstate`。citeturn19view2

### 6.2 设计意义

为后续 **内核态 V 上下文** 引入独立存储铺路，使保存/恢复函数不再绑定用户态任务结构。citeturn19view2

---

## 7. [v11 08/10] riscv: vector: use a mask to write vstate_ctrl（对应链接 -9）

### 7.1 改动内容

- 在写 `vstate_ctrl` 时加入掩码：
  - 清除 `PR_RISCV_V_VSTATE_CTRL_MASK` 覆盖位；
  - 再写入新控制位，避免破坏其他字段。citeturn19view3

### 7.2 逻辑意义

避免覆写非相关位，确保用户态可控字段与内核态维护字段不会互相干扰。citeturn19view3

---

## 8. [v11 09/10] riscv: vector: use kmem_cache to manage vector context（对应链接 -10）

### 8.1 关键改动

- 用 `kmem_cache` 管理 `thread.vstate.datap` 分配，替代 `kzalloc`。citeturn19view4  
- 增加 `riscv_v_setup_ctx_cache()`，在 `arch_task_cache_init()` 中初始化。citeturn19view4  
- `riscv_v_thread_free()` 统一释放向量上下文。citeturn19view4

### 8.2 设计意义

减少首次使用向量时的分配开销，并在 `/proc/slabinfo` 中可见向量上下文占用，方便调试与容量规划。citeturn19view4

---

## 9. [v11 10/10] riscv: vector: allow kernel-mode Vector with preemption（对应链接 -11）

### 9.1 关键改动

- **新增 per-task 内核态向量上下文** `kernel_vstate`。citeturn19view5  
- **扩展 `riscv_v_flags`**：增加 preempt_v 标志与嵌套深度/dirty/restore 位。citeturn19view5  
- **入口/出口跟踪**：在异常入口/出口调用 `riscv_v_context_nesting_start/end()`。citeturn19view5  
- `kernel_vector_begin/end()` 根据是否启用 preempt_v 执行不同的上下文保存/恢复策略。citeturn19view5  
- `__switch_to_vector()` 与 `may_use_simd()` 逻辑更新，以兼容可抢占的内核向量执行。citeturn19view5

### 9.2 核心逻辑

1. **preemptible kernel-mode Vector 启动**：
   - 如果 `kernel_vstate` 已分配，进入 preempt_v 模式并记录状态；
   - 若在内核态 V 执行过程中发生 trap/上下文切换，保存 kernel_vstate。citeturn19view5

2. **嵌套管理**：
   - `riscv_v_context_nesting_start()` / `_end()` 维护 depth 计数；
   - depth 回到 0 时恢复保存的 kernel_vstate。citeturn19view5

3. **调度路径**：
   - 若任务处于 preempt_v 并 dirty，则 `__switch_to_vector()` 负责保存 kernel_vstate；
   - 否则仍走用户态 vstate 保存。citeturn19view5

### 9.3 设计意义

这一补丁使内核态向量使用不再必须关闭抢占，从而降低长时间 SIMD 操作对调度延迟的影响，同时通过 kernel_vstate 实现安全恢复。citeturn19view5

---

## 10. 结论

该系列补丁逐步搭建起 **RISC-V 内核态向量执行框架**：

1. **01/10** 建立内核态向量 API；
2. **03/10、05/10** 将其用于 XOR 与用户拷贝路径；
3. **04/10** 引入延迟恢复以降低上下文切换成本；
4. **07~09/10** 改进接口、标志与内存管理；
5. **10/10** 支持可抢占内核态向量，实现性能与实时性的平衡。citeturn17view1turn17view2turn17view3turn19view0turn19view2turn19view4turn19view5

整体逻辑清晰：**先提供安全护栏 → 引入性能路径 → 优化恢复策略 → 最终支持可抢占执行**。

