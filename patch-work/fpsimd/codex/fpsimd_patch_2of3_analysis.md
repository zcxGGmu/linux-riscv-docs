# arm64 FPSIMD 补丁 2/3 详细技术分析

> 补丁标题：`[PATCH 2/3] arm64: defer reloading a task's FPSIMD state to userland resume`  
> 作者：Ard Biesheuvel  
> 日期：2014-05-08（PDT）  
> 主题：将 FPSIMD 状态的恢复延迟到返回用户态之前（lazy restore）

## 1. 背景与动机

在该补丁之前，arm64 的 FPSIMD 处理路径在**任务切换**和**kernel_neon_begin()/kernel_neon_end()** 之间会频繁保存/恢复用户态 FPSIMD 寄存器。这样做虽然正确，但存在两个明显的浪费：

1. **任务调度“出去再回来”**时，如果 CPU 的 FPSIMD 寄存器内容并未被其他任务或内核 NEON 使用破坏，继续从内存恢复是一种不必要的开销。
2. **重复调用 kernel_neon_begin()/kernel_neon_end()** 时，每次都保存/恢复用户态状态，产生额外的内存带宽和延迟。

补丁的核心思想是：**把 FPSIMD 状态的恢复延迟到真正需要它的时刻——即返回用户态之前。** 如果任务一直停留在内核态（或在同一 CPU 上再次被调度而寄存器内容仍有效），则可以避免恢复。

## 2. 核心设计：两级“最近状态追踪”

补丁引入两个配合的追踪机制：

### 2.1 每任务：`fpsimd_state.cpu`

在 `struct fpsimd_state` 中新增字段：

- `cpu`：记录**最近一次将该任务 FPSIMD 状态加载到寄存器的 CPU 编号**。

### 2.2 每 CPU：`fpsimd_last_state`

新增 per-CPU 指针：

- `fpsimd_last_state`：记录**该 CPU 当前寄存器中保存的是哪一个任务的用户态 FPSIMD 状态**。
- 若内核使用了 NEON（kernel mode），该指针会被清空（NULL），表示寄存器内容已不再对应任何用户态状态。

### 2.3 线程标志：`TIF_FOREIGN_FPSTATE`

新增线程标志位，含义为：

- **当前 CPU 的 FPSIMD 寄存器不包含当前任务的最新用户态状态**。

当 `TIF_FOREIGN_FPSTATE` 被设置时，意味着 **需要在返回用户态之前恢复状态**。

## 3. 关键流程改造

下面以任务切换、返回用户态、kernel NEON 使用三条主流程为核心分析。

### 3.1 任务切换：`fpsimd_thread_switch()`

逻辑变化点：

- **保存 current 状态**：
  - 仅当 `current->mm` 存在（用户进程）且 `TIF_FOREIGN_FPSTATE` 未设置时，才保存。
  - 避免保存“非当前任务的寄存器内容”。

- **处理 next 任务**：
  - 如果 `next` 是用户任务，则比较：
    - `fpsimd_last_state == &next->thread.fpsimd_state`
    - `next->thread.fpsimd_state.cpu == 当前 CPU`
  - 两者都匹配：说明寄存器内容已经是 next 的最新状态，**清除** `TIF_FOREIGN_FPSTATE`。
  - 任一不匹配：说明寄存器无效，**设置** `TIF_FOREIGN_FPSTATE`，在用户态返回前再恢复。

**效果**：减少任务切换时的 FPSIMD restore 次数。

### 3.2 返回用户态：`do_notify_resume()`

`TIF_FOREIGN_FPSTATE` 被纳入 `_TIF_WORK_MASK`，保证在返回用户态路径进入 `do_notify_resume()`。

在 `do_notify_resume()` 中新增逻辑：

- 如果 `TIF_FOREIGN_FPSTATE` 被设置，则调用 `fpsimd_restore_current_state()`。

`fpsimd_restore_current_state()` 的作用：

- 从 `current->thread.fpsimd_state` 加载寄存器内容。
- 更新 `fpsimd_last_state` 指向当前任务。
- 更新 `fpsimd_state.cpu` 为当前 CPU。
- 清除 `TIF_FOREIGN_FPSTATE`。

**效果**：把 restore 延迟到“真正即将进入用户态”的时刻。

### 3.3 内核 NEON 使用：`kernel_neon_begin()` / `kernel_neon_end()`

改动重点：

- 在 `kernel_neon_begin()`：
  - 仅当 `current->mm` 且 `TIF_FOREIGN_FPSTATE` 未设置时才保存 FPSIMD 状态。
  - 将 `fpsimd_last_state` 清空（NULL），表明寄存器内容已被内核覆盖。
  - 设置 `TIF_FOREIGN_FPSTATE`。

- `kernel_neon_end()`：
  - 不再恢复 FPSIMD 状态。
  - 恢复由用户态返回路径统一处理。

**效果**：避免重复 save/restore，提高 kernel NEON 使用效率。

## 4. 其它关键改动

### 4.1 `fpsimd_preserve_current_state()`

只在 `TIF_FOREIGN_FPSTATE` 未设置时保存，避免将“非 current 的寄存器内容”写回。

### 4.2 `fpsimd_update_current_state()`

加载新状态后，若原本处于 foreign，则更新：

- per-CPU `fpsimd_last_state`
- `fpsimd_state.cpu`
- 清除 `TIF_FOREIGN_FPSTATE`

### 4.3 `fpsimd_flush_thread()`

- 清空 `current->thread.fpsimd_state`
- **设置 `TIF_FOREIGN_FPSTATE`**，确保后续返回用户态时重新加载

### 4.4 CPU PM 事件处理

在 CPU 低功耗进入/退出时：

- **进入**：若当前任务是用户任务且不 foreign，保存 FPSIMD 状态。
- **退出**：设置 `TIF_FOREIGN_FPSTATE`，强制恢复。

### 4.5 ptrace / compat VFP 写入

当 ptrace 或 compat VFP 修改目标任务 FPSIMD 状态时：

- 调用 `fpsimd_flush_task_state(target)`
- 将 `target->thread.fpsimd_state.cpu = NR_CPUS`

这样保证：**任何仍持有旧状态的 CPU 在下次使用该任务时都会触发恢复**。

## 5. 状态机视角总结

可以将 FPSIMD 状态视为以下状态机：

- **状态 A（本地有效）**：
  - `TIF_FOREIGN_FPSTATE = 0`
  - `fpsimd_last_state == current->state`
  - `current->state.cpu == 当前 CPU`

- **状态 B（需恢复）**：
  - `TIF_FOREIGN_FPSTATE = 1`
  - 寄存器内容不可信
  - 在返回用户态前必须 restore

状态切换：

- kernel NEON → B
- CPU PM EXIT → B
- 任务迁移到其他 CPU → B
- 返回用户态 restore → A

## 6. 性能与正确性影响

### 性能收益

- 减少无意义的 FPSIMD restore
- 减少 kernel_neon_begin/end 频繁 save/restore
- 有利于调度频繁场景和短内核路径

### 正确性保障

- 使用 `TIF_FOREIGN_FPSTATE` 明确标记寄存器可信性
- 通过 `(fpsimd_last_state, fpsimd_state.cpu)` 双重一致性确认
- ptrace 和兼容模式更新后强制失效 CPU 缓存

## 7. 与当前内核实现的关系（基于本地树观察）

在当前代码树中（较新版本）：

- `TIF_FOREIGN_FPSTATE` 仍存在，是 FPSIMD/SVE/SME 状态管理的基础标志。
- `fpsimd_last_state` 从简单指针扩展为 `struct cpu_fp_state`，用于管理 SVE/SME 等更多状态。
- 但 **“lazy restore + foreign 标志” 的核心思路与本补丁一致**。

该补丁可视为 arm64 FPSIMD 状态管理从“立即恢复”转向“延迟恢复”的关键起点。

## 8. 小结

本补丁通过引入 `TIF_FOREIGN_FPSTATE`、`fpsimd_state.cpu` 和 per-CPU `fpsimd_last_state`，实现了 FPSIMD 状态的“延迟恢复”策略。它显著减少了上下文切换与 kernel NEON 使用时的重复 save/restore，并保证在返回用户态前恢复正确状态，是 arm64 FPSIMD 性能优化的重要一步。

