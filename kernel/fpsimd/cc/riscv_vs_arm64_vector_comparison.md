# RISC-V Vector vs ARM64 FPSIMD 状态管理机制对比分析

## 概述

本文档详细对比 RISC-V 向量扩展和 ARM64 FPSIMD 的状态管理机制，分析两种架构的设计理念和实现差异。

## 核心设计理念对比

### ARM64 FPSIMD
- **统一管理**：将浮点（FP）和 SIMD（NEON）作为统一的状态管理
- **优化延迟恢复**：通过双向跟踪（per-task 和 per-CPU）减少状态保存/恢复
- **简化用户空间**：默认启用，对用户空间透明

### RISC-V Vector
- **按需分配**：首次使用时才分配状态空间，节省内存
- **细粒度控制**：提供精细的状态控制机制
- **可配置性**：支持用户空间控制向量扩展的启用/禁用

## 数据结构对比

### ARM64 数据结构
```c
struct thread_struct {
    struct fpsimd_state fpsimd_state;     // 统一的浮点/SIMD 状态
    unsigned int fpsimd_cpu;              // 最后加载该状态的CPU ID
};

struct fpsimd_state {
    __uint128_t vregs[32];                // 32个128位向量寄存器
    u32 fpsr;                            // 浮点状态寄存器
    u32 fpcr;                            // 浮点控制寄存器
};
```

### RISC-V 数据结构
```c
struct thread_struct {
    struct __riscv_v_ext_state vstate;   // 用户态向量状态
    struct __riscv_v_ext_state kernel_vstate; // 内核态向量状态（抢占模式）
    u32 vstate_ctrl;                     // 向量状态控制
    u32 riscv_v_flags;                   // 内核向量标志
};

struct __riscv_v_ext_state {
    unsigned long vstart;                // 向量起始位置
    unsigned long vl;                    // 向量长度
    unsigned long vtype;                 // 向量类型
    unsigned long vcsr;                  // 向量控制状态寄存器
    unsigned long vlenb;                 // 向量寄存器长度
    void *datap;                         // 动态分配的寄存器数据
};
```

## 状态跟踪机制对比

### ARM64 双向跟踪
- **per-task 跟踪**：`task->thread.fpsimd_cpu` 记录最后加载的CPU
- **per-CPU 跟踪**：`fpsimd_last_state` 指向当前加载的任务状态
- **标志位**：`TIF_FOREIGN_FPSTATE` 指示是否需要恢复状态

### RISC-V 懒惰分配+延迟恢复
- **懒惰分配**：首次使用陷阱时才分配 `datap`
- **延迟恢复**：`TIF_RISCV_V_DEFER_RESTORE` 标记延迟恢复
- **状态控制**：`vstate_ctrl` 精细控制向量扩展使用

## 任务切换处理对比

### ARM64 任务切换
```c
// 检查是否需要保存当前状态
if (prev->thread.fpsimd_state && cpu_has_fpsimd()) {
    fpsimd_save_state(prev);
}

// 设置延迟恢复标志
if (next->thread.fpsimd_cpu != smp_processor_id()) {
    set_tsk_thread_flag(next, TIF_FOREIGN_FPSTATE);
}
```

### RISC-V 任务切换
```c
// __switch_to_vector 的处理
if (riscv_preempt_v_started(prev)) {
    // 处理抢占式向量状态
    if (riscv_v_is_on()) {
        riscv_v_disable();
        prev->thread.riscv_v_flags |= RISCV_PREEMPT_V_IN_SCHEDULE;
    }
} else {
    // 处理用户态向量状态
    riscv_v_vstate_save(&prev->thread.vstate, regs);
}

// 设置延迟恢复
riscv_v_vstate_set_restore(next, task_pt_regs(next));
```

## 用户空间接口对比

### ARM64
- **默认启用**：FPSIMD 默认对用户空间可用
- **prctl 支持**：`PR_SVE_SET_VL` 控制向量长度
- **透明使用**：用户空间无需特殊初始化

### RISC-V
- **按需启用**：首次使用时触发陷阱
- **精细控制**：`PR_RISCV_V_VSTATE_CTRL` 控制策略
- **继承机制**：支持父子进程间的策略继承

## 内核态使用对比

### ARM64 kernel_neon_begin/end
```c
void kernel_neon_begin(void) {
    // 保存用户态状态
    fpsimd_save_state(current->thread.fpsimd_state);

    // 清除 per-CPU 跟踪
    __this_cpu_write(fpsimd_last_state, NULL);

    // 设置标志
    set_thread_flag(TIF_FOREIGN_FPSTATE);
}
```

### RISC-V kernel_vector_begin/end
```c
void kernel_vector_begin(void) {
    bool is_nested = false;

    // 启动内核向量上下文
    if (riscv_v_start_kernel_context(&is_nested) < 0) {
        // 非抢占模式：禁用软中断
        get_cpu_vector_context();
    }

    // 保存用户态状态
    if (__riscv_v_vstate_check(regs->status, DIRTY)) {
        __riscv_v_vstate_save(&current->thread.vstate, datap);
    }
}
```

## 性能特性对比

### 内存使用
- **ARM64**：每个任务固定分配 544 字节（32×16 + 控制寄存器）
- **RISC-V**：动态分配，支持可变向量长度（VLEN）

### 上下文切换开销
- **ARM64**：优化后常量时间开销
- **RISC-V**：与向量长度（VLEN）成正比

### 首次使用开销
- **ARM64**：无额外开销
- **RISC-V**：首次使用时分配和初始化开销

## 可扩展性对比

### ARM64 SVE扩展
- **向后兼容**：SVE 是 FPSIMD 的超集
- **向量长度**：支持可变向量长度（128-2048位）
- **状态管理**：复用 FPSIMD 的管理框架

### RISC-V Vector扩展
- **模块化设计**：向量扩展是独立的模块
- **可配置性**：支持不同的 VLEN 配置
- **厂商扩展**：支持 T-Head 等厂商的私有扩展

## 优势和适用场景

### ARM64 优势
1. **成熟稳定**：经过长期验证的设计
2. **性能优化**：针对常见场景进行了深度优化
3. **软件生态**：广泛的软件支持

### RISC-V 优势
1. **内存效率**：按需分配节省内存
2. **可扩展性**：模块化设计便于扩展
3. **精细化控制**：提供更多控制选项

## 总结

两种架构都采用了延迟恢复的优化策略，但实现方式有所不同：

- **ARM64** 采用双向跟踪机制，实现精细的状态管理，适合对性能要求高的场景
- **RISC-V** 采用懒惰分配机制，提供更好的内存效率和可扩展性，适合资源受限或多样化的场景

选择哪种机制取决于具体的应用需求和硬件特性。两种设计都有其合理性，反映了不同架构的设计哲学。