# arm64 FPSIMD 补丁 1/3 详细技术分析

> 补丁标题：`[PATCH 1/3] arm64: add abstractions for FPSIMD state manipulation`  
> 目标：为后续“延迟恢复（lazy restore）”做铺垫，抽象出 FPSIMD 状态保存/更新接口。

## 1. 背景与动机

补丁作者指出，后续优化会打破两个“默认假设”：

1. CPU 中的 FPSIMD 寄存器一定保存着 current 的用户态 FPSIMD 状态；
2. 任务切换时一定会立即恢复下一任务的 FPSIMD 状态。

为避免直接操作寄存器带来的耦合，本补丁先引入对“保存/更新 current 状态”的抽象接口，并把相关路径改为使用这些接口。

## 2. 新增的接口与语义

### 2.1 `fpsimd_preserve_current_state()`

- 语义：确保 current 的用户态 FPSIMD 状态已保存到内存。  
- 实现：
  - `preempt_disable()`
  - `fpsimd_save_state(&current->thread.fpsimd_state)`
  - `preempt_enable()`

**要点**：该函数只是封装保存动作，但明确了“保存 current 的用户态状态”的语义边界，供后续 lazy restore 依赖。

### 2.2 `fpsimd_update_current_state(struct fpsimd_state *state)`

- 语义：用一份新的 FPSIMD 状态“更新” current。  
- 实现：
  - `preempt_disable()`
  - `fpsimd_load_state(state)`
  - `preempt_enable()`

**要点**：在 2014 的实现中，这个接口直接把状态加载进寄存器（即同步到硬件）。

## 3. 关键调用点的调整

### 3.1 `arch_dup_task_struct()`

原来在 fork 路径直接调用 `fpsimd_save_state()`，现在改为：

- `fpsimd_preserve_current_state()`

这样把 fork 路径与“寄存器是否一定对应 current”解耦，为后续引入 lazy restore 做准备。

### 3.2 信号保存/恢复

#### `signal.c`

- 保存：`fpsimd_save_state()` → `fpsimd_preserve_current_state()`
- 恢复：原先手动 `preempt_disable()` + `fpsimd_load_state()`，改为 `fpsimd_update_current_state()`

#### `signal32.c`

- 兼容 AArch32 的 VFP 保存/恢复同样改为使用新接口。

**影响**：信号路径的状态处理逻辑变得更加抽象且可替换，为后续 patch 2/3 中的 lazy restore 逻辑留出了插入点。

## 4. 行为变化总结

- **功能层面**：
  - 对外行为几乎一致，但将保存/更新动作集中到统一接口。

- **并发语义**：
  - `fpsimd_preserve_current_state()` / `fpsimd_update_current_state()` 内部显式关闭抢占，统一了调用点的时序假设。
  - 这为后续“寄存器可能不是 current 的状态”提供正确的保护。  

## 5. 关键意义

该补丁本身并不引入 lazy restore，但完成了以下铺垫：

1. 抽象了“保存 current”与“更新 current”的语义边界；
2. 将重要路径（fork / signal / compat signal）从“直接操作寄存器”改为“走统一接口”；
3. 为 patch 2/3 的 `TIF_FOREIGN_FPSTATE` / `fpsimd_restore_current_state()` 机制提供落脚点。

简言之：这是 **lazy restore 设计的“接口预埋补丁”**。

