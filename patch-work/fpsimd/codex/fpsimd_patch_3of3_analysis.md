# arm64 FPSIMD 补丁 3/3 详细技术分析

> 补丁标题：`[PATCH 3/3] arm64: add support for kernel mode NEON in interrupt context`  
> 目标：允许 `kernel_neon_begin()/end()` 在任意上下文（含中断）使用，并支持“只保存部分寄存器”的轻量路径。

## 1. 背景与动机

在 1/3 与 2/3 引入 lazy restore 后，内核使用 NEON 的成本降低。但在 2014 版本里，`kernel_neon_begin()` **禁止在中断上下文调用**。该补丁扩展其适用范围，使 **硬中断/软中断也能安全使用 NEON**，并允许只保存底部 N 个寄存器，从而减少保存开销。

## 2. 新增结构与接口

### 2.1 `struct fpsimd_partial_state`

新增结构用于保存“底部 n 个 Q 寄存器”的部分状态：

- `fpsr` / `fpcr`
- `num_regs`（记录保存的寄存器数量）
- `vregs[32]`（128-bit Q 寄存器槽位）

### 2.2 新增 API

- `fpsimd_save_partial_state(state, num_regs)`  
- `fpsimd_load_partial_state(state)`  
- `kernel_neon_begin_partial(u32 num_regs)`  
- `kernel_neon_begin()` 变为宏：`kernel_neon_begin_partial(32)`

**要点**：
- `kernel_neon_begin_partial()` 允许调用者指定需要的寄存器数量（底部 n 个 Q）。
- 完整 NEON 使用仍可通过 `kernel_neon_begin()` 实现。

## 3. 汇编宏：按需保存/恢复部分寄存器

补丁在 `fpsimdmacros.h` 中新增：

- `fpsimd_save_partial`  
- `fpsimd_restore_partial`

核心技巧：

- 根据 `num_regs` 计算跳转偏移，使保存/恢复流程“跳过不需要的高寄存器”。
- 以 `stp/ldp` 配对方式保存 Q 寄存器，`num_regs` 会被 `roundup(num_regs, 2)` 对齐到偶数对。

## 4. 中断上下文支持逻辑

### 4.1 per-CPU 缓冲区

新增两份 per-CPU 缓冲区：

- `hardirq_fpsimdstate`
- `softirq_fpsimdstate`

这样保证 **中断内保存的 partial state 不与任务上下文混用**。

### 4.2 `kernel_neon_begin_partial()` 的上下文分支

伪代码概括：

```
if (in_interrupt()) {
    s = per_cpu(hardirq or softirq state)
    save bottom num_regs regs into s
} else {
    preempt_disable()
    if (current->mm && !TIF_FOREIGN_FPSTATE)
        save full user fpsimd state
    fpsimd_last_state = NULL
}
```

**关键点**：

- **中断上下文**只保存部分寄存器，避免全量 save/restore。
- **任务上下文**仍走 patch 2/3 的 lazy restore 逻辑：保存用户态状态并将 `fpsimd_last_state` 置空。

### 4.3 `kernel_neon_end()`

- 中断上下文：恢复 partial state。  
- 任务上下文：仅 `preempt_enable()`，用户态状态仍由 lazy restore 处理。

## 5. 行为与语义变化总结

### 5.1 新能力

- `kernel_neon_begin()` 可在 **hardirq/softirq** 使用。  
- 支持“部分寄存器保存”降低中断路径成本。

### 5.2 与 patch 2/3 的配合

- 任务上下文仍保持 lazy restore。  
- 中断上下文只保存/恢复必要寄存器，不干扰用户态 lazy restore 机制。

## 6. 潜在边界条件（2014 视角）

1. **嵌套中断场景**依赖 per-CPU 缓冲区是否安全覆盖：硬中断嵌套硬中断的情况需要谨慎保证一致性。  
2. `kernel_neon_begin_partial()` 仅保存底部寄存器，调用者必须确保高寄存器不被访问。

## 7. 小结

该补丁将 NEON 使用范围扩展到了中断上下文，并通过部分寄存器保存降低开销。这对当时的加密、校验等内核路径（尤其软中断）非常关键，也为后续 crypto 代码在更多上下文中使用 NEON 提供了基础。

