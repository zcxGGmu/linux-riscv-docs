# 2014 FPSIMD 系列 vs 当前内核：行为差异与风险评估

> 参考基线：2014-05 的 1/3、2/3、3/3 FPSIMD 系列补丁  
> 对照对象：当前本地内核树（`/home/zcxggmu/workspace/patch-work/linux`）

## 1. 系列补丁核心目标回顾

2014 系列完成三件事：

1. **抽象保存/更新接口**（1/3）：引入 `fpsimd_preserve_current_state()` 与 `fpsimd_update_current_state()`；
2. **引入 lazy restore**（2/3）：用 `TIF_FOREIGN_FPSTATE` + per-CPU `fpsimd_last_state` + `fpsimd_state.cpu` 记录，延迟到返回用户态再恢复；
3. **允许中断上下文 NEON**（3/3）：加入 partial save/restore，扩展 `kernel_neon_begin()` 到任何上下文。

## 2. 当前内核的关键实现要点

### 2.1 退出到用户态的恢复点

- `TIF_FOREIGN_FPSTATE` 仍是核心标志。  
- 逻辑位置已迁移到 `arch_exit_to_user_mode_work()`（`arch/arm64/include/asm/entry-common.h`）。

### 2.2 数据结构进化

- 2014：`struct fpsimd_state { vregs + fpsr/fpcr + cpu }`  
- 当前：
  - 用户态状态存放在 `user_fpsimd_state`（`thread.uw.fpsimd_state`）
  - CPU 绑定字段为 `thread.fpsimd_cpu`  
  - per-CPU 跟踪结构为 `struct cpu_fp_state`，包含 SVE/SME/ZA/FFR/FPMR 等扩展状态

### 2.3 Kernel NEON 与任务切换

- 当前内核引入 `TIF_KERNEL_FPSTATE`，允许**内核态 NEON 状态在上下文切换中被保存/恢复**。
- `kernel_neon_begin()` 使用 `get_cpu_fpsimd_context()` + `fpsimd_save_user_state()`，并根据上下文设置 `TIF_KERNEL_FPSTATE`。

### 2.4 中断上下文约束

- `may_use_simd()` 明确禁止 **hardirq / NMI / irqs_disabled** 情况下使用 NEON。  
- 软中断允许但需遵循 `kernel_neon_begin/end` 与 TIF 规则。

## 3. 关键行为差异详解

### 3.1 `fpsimd_update_current_state()` 语义变化（重要）

| 项目 | 2014 系列 | 当前内核 |
|------|-----------|-----------|
| 语义 | 直接加载寄存器 | 仅更新内存副本，真正加载在返回用户态时完成 |
| 风险 | 预期“立即生效” | 若代码依赖“立即生效”，会在当前内核失效 |

**影响**：若有代码（如 ptrace 或信号处理路径）依赖更新后立刻读寄存器，则在当前内核不会成立，必须通过用户态返回路径恢复。

### 3.2 `kernel_neon_begin()` 可用上下文

| 项目 | 2014 3/3 | 当前内核 |
|------|----------|-----------|
| HardIRQ | 允许（partial save） | 禁止 |
| SoftIRQ | 允许（partial save） | 允许，但不使用 partial save |
| Task context | 允许 | 允许且支持 TIF_KERNEL_FPSTATE |

**风险**：若沿用 2014 的“任意上下文可用”假设，在当前内核会触发 WARN/BUG 或破坏状态一致性。

### 3.3 per-CPU tracking 语义增强

- 2014：`fpsimd_last_state` 仅记录“哪个任务的 FPSIMD 状态在寄存器里”。
- 当前：`cpu_fp_state` 还能绑定 SVE/SME/ZA/FFR/FPMR 状态，且可能指向 **KVM 客户机上下文**。

**风险**：若仍假设“寄存器只属于 current 用户态”，会在 KVM 或扩展向量上下文中出错。

### 3.4 `TIF_FOREIGN_FPSTATE` 的完整性增强

- 当前 `fpsimd_flush_task_state()` 使用内存屏障防止软中断/抢占竞争导致 flag 被错误清除。
- 2014 版本只是简单将 `cpu` 设置为 `NR_CPUS`。

**风险**：在更复杂的抢占/软中断体系下，简单标记不足以确保一致性。

### 3.5 CPU PM 行为差异

- 2014：CPU_PM_EXIT 设置 `TIF_FOREIGN_FPSTATE`，等待用户态恢复。  
- 当前：进入低功耗时直接 `fpsimd_save_and_flush_cpu_state()`，退出不做显式 restore，完全依赖 lazy restore。

## 4. 风险评估（面向实际维护/回溯移植）

### 4.1 功能回溯风险

- 试图直接移植 2014 的 `kernel_neon_begin_partial` 到当前内核，会与 `may_use_simd()` 规则冲突。  
- 当前内核没有 partial save/restore 支持，硬中断 NEON 使用属于被明确禁止的行为。

### 4.2 语义误用风险

- 依赖 `fpsimd_update_current_state()` 立即更新寄存器的代码，在当前内核只会更新内存副本，导致“读到旧寄存器值”或“用户态恢复不一致”的问题。  
- 期望 `fpsimd_last_state` 只指向 current 用户态，将忽略 KVM/扩展向量 context 的实际使用方式。

### 4.3 并发/抢占风险

- 2014 设计假设较少（未考虑 SVE/SME/guest context），在现代内核中并发语义更复杂，必须遵循 `get_cpu_fpsimd_context()` / `TIF_KERNEL_FPSTATE` / `fpsimd_save_user_state()` 等新路径。

## 5. 结论

- 2014 系列在当时成功引入 **lazy restore + 中断可用 NEON**。  
- 当前内核保持 lazy restore，但**取消了硬中断 NEON 的设计**，并扩展为完整的 FPSIMD/SVE/SME 状态机。  
- 任何回溯或复用旧逻辑时，最关键的风险点是：
  - `kernel_neon_begin()` 的上下文约束已改变；
  - `fpsimd_update_current_state()` 语义已从“硬件更新”变为“内存更新”；
  - `fpsimd_last_state` 与 `TIF_FOREIGN_FPSTATE` 现在承担更复杂的状态同步任务。

