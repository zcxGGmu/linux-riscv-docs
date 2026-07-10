# linux-arm-kernel 通用核心 / tracing / hardening 补丁的 RISC-V 可移植性审计

## 范围

- 时间范围：2025-01-01 至 2026-07-10（含）。
- 重点：livepatch、可靠栈回溯、SFrame、ftrace/BPF、kprobes、模块装载、动态文本修改、vDSO、LTO/READ_ONCE、Rust 内存访问语义。
- 排除：仅 ARM 指令集扩展、FPSIMD/SVE/SME、单一 SoC 配置、纯清理和 stable 失败通知。

## 潜在贡献点

### CORE-1. 为 RISC-V 启用 livepatch 和 patch-pending 任务状态

- **原始架构/子系统**：arm64 / livepatch。
- **原始补丁**：[arm64: Implement HAVE_LIVEPATCH](https://lore.kernel.org/linux-arm-kernel/20250630174502.842486-1-song@kernel.org/)
- **可移植点**：为任务提供 patch-pending 标志，并在内核返回用户态/调度边界切换到新函数版本。
- **RISC-V 落点**：`arch/riscv/Kconfig`、`arch/riscv/include/asm/thread_info.h`、异常返回和 entry 路径。
- **难度/阻塞**：中；依赖可靠栈回溯和对所有异常/中断返回边界的审计。
- **证据**：arm64 实现主要是任务标志、entry 检查和 Kconfig 能力，不依赖 ARM 指令语义。

### CORE-2. 实现 RISC-V `arch_stack_walk_reliable()`

- **原始架构/子系统**：arm64 / stacktrace、livepatch。
- **原始补丁**：[arm64: stacktrace: Implement arch_stack_walk_reliable()](https://lore.kernel.org/linux-arm-kernel/20250521111000.2237470-3-mark.rutland@arm.com/)
- **可移植点**：可靠性接口不要求每次都成功，而是必须识别异常边界、不可展开帧和不可信栈。
- **RISC-V 落点**：`arch/riscv/kernel/stacktrace.c`、异常入口元数据、livepatch stack check。
- **难度/阻塞**：中；需要定义 trap frame、IRQ stack、kretprobe/ftrace trampoline 的可靠性规则。
- **证据**：补丁描述明确将“可靠检测失败”作为 livepatch 所需契约。

### CORE-3. 引入内核 SFrame V3 回溯

- **原始架构/子系统**：arm64 + generic unwind。
- **原始补丁**：[arm64, unwind: build kernel with sframe V3 info](https://lore.kernel.org/linux-arm-kernel/20260519064950.493949-3-dylanbhatch@google.com/)、[sframe: Provide PC lookup for vmlinux .sframe section](https://lore.kernel.org/linux-arm-kernel/20260519064950.493949-6-dylanbhatch@google.com/)、[unwind: arm64: Use sframe to unwind interrupt frames](https://lore.kernel.org/linux-arm-kernel/20260519064950.493949-10-dylanbhatch@google.com/)
- **可移植点**：用紧凑的编译器生成 unwind 信息覆盖无 frame pointer、异常帧和模块。
- **RISC-V 落点**：RISC-V 工具链 SFrame 生成、链接脚本、`arch/riscv/kernel/stacktrace.c`、模块 SFrame 注册。
- **难度/阻塞**：高；依赖 binutils/LLVM 对 RISC-V SFrame ABI 的完整支持和 trap frame 描述。
- **证据**：通用 lookup/validation 已位于 `kernel/unwind/`，架构只需生成格式并提供 PC/frame 解释。

### CORE-4. 为 RISC-V ftrace/BPF 提供每函数元数据

- **原始架构/子系统**：generic + arm64 / ftrace、BPF。
- **原始补丁**：[add per-function metadata storage support](https://lore.kernel.org/linux-arm-kernel/20250303132837.498938-3-dongml2@chinatelecom.cn/)、[arm64: implement per-function metadata storage for arm64](https://lore.kernel.org/linux-arm-kernel/20250303132837.498938-5-dongml2@chinatelecom.cn/)
- **可移植点**：低开销保存 BPF trampoline、ftrace callback 等每函数状态，避免为每个函数单独分配 trampoline。
- **RISC-V 落点**：`arch/riscv/kernel/ftrace.c`、函数入口 padding/patchable-function-entry、`kernel/trace/kfunc_md.c`。
- **难度/阻塞**：中高；需要确认 RISC-V 函数对齐、入口可修改字节和 CFI/kprobe 的空间冲突。
- **证据**：generic 存储层已独立，arm64 仅负责把索引编码到函数入口附近。

### CORE-5. 支持 ftrace direct calls 而不依赖 CALL_OPS

- **原始架构/子系统**：arm64 / ftrace。
- **原始补丁**：[arm64: ftrace: prepare ftrace_modify_call() for use without CALL_OPS](https://lore.kernel.org/linux-arm-kernel/20260609-arm64-ftrace-direct-calls-v1-1-4a46f266697f@linux.dev/)、[arm64: ftrace: allow DIRECT_CALLS without CALL_OPS](https://lore.kernel.org/linux-arm-kernel/20260609-arm64-ftrace-direct-calls-v1-2-4a46f266697f@linux.dev/)
- **可移植点**：把修改 call site 的能力与架构保存 callback 指针的方式解耦。
- **RISC-V 落点**：`arch/riscv/kernel/ftrace.c`、BPF trampoline direct call、module PLT/long jump。
- **难度/阻塞**：中；需处理 ±1 MiB JAL 范围、AUIPC/JALR 序列和 icache 同步。
- **证据**：系列目标是消除 DIRECT_CALLS 对 CALL_OPS 的不必要架构耦合。

### CORE-6. 统一 ftrace direct hash 和 BPF trampoline 生命周期

- **原始架构/子系统**：generic ftrace/BPF。
- **原始补丁**：[ftrace: Use direct hash interface in direct functions](https://lore.kernel.org/linux-arm-kernel/20250923215147.1571952-7-jolsa@kernel.org/)、[bpf, x86: Use single ftrace_ops for direct calls](https://lore.kernel.org/linux-arm-kernel/20251120212402.466524-9-jolsa@kernel.org/)
- **可移植点**：用统一 hash 管理 direct call 注册、修改和删除，并减少每 trampoline 的 `ftrace_ops`。
- **RISC-V 落点**：通用代码可直接受益；补充 RISC-V direct-call/BPF trampoline 测试。
- **难度/阻塞**：低到中；要求 RISC-V 已支持动态 ftrace 和 BPF trampoline。
- **证据**：主要修改 `kernel/trace/ftrace.c` 与 `kernel/bpf/trampoline.c`。

### CORE-7. kprobe/execmem 映射同时保护执行别名和 direct map

- **原始架构/子系统**：arm64 / kprobes、execmem、W^X。
- **原始补丁**：[arm64: kprobes: call set_memory_rox() for kprobe page](https://lore.kernel.org/linux-arm-kernel/20250917190323.3828347-6-yang@os.amperecomputing.com/)、[arm64: kprobes: check the return value of set_memory_rox()](https://lore.kernel.org/linux-arm-kernel/20251104214947.799005-1-yang@os.amperecomputing.com/)
- **可移植点**：execmem 返回 ROX 别名后，还要同步处理 direct-map 权限，并传播权限修改失败。
- **RISC-V 落点**：`arch/riscv/kernel/probes/`、`arch/riscv/mm/pageattr.c`、module/ftrace execmem region。
- **难度/阻塞**：中；必须处理大页拆分、icache flush、失败回滚和严格 W^X。
- **证据**：arm64 漏洞来自执行别名和 linear map 权限不一致，RISC-V 同样存在多别名风险。

### CORE-8. 模块 alternatives callback 必须指向可信 core text

- **原始架构/子系统**：arm64 / module loader、alternatives。
- **原始补丁**：[arch: arm64: Reject modules with internal alternative callbacks](https://lore.kernel.org/linux-arm-kernel/20250922130427.2904977-3-abarnas@google.com/)
- **可移植点**：模块加载时验证 alternative callback 的目标区域，禁止模块内未受信任回调在重写阶段执行。
- **RISC-V 落点**：`arch/riscv/kernel/alternative.c`、`arch/riscv/kernel/module.c`。
- **难度/阻塞**：中；需检查 RISC-V alternatives 的 callback/patch-function 模型是否允许模块目标。
- **证据**：安全不变量与 ISA 无关：早期或模块装载期动态指令重写只能调用可信代码。

### CORE-9. runtime constants 优化中断入口热路径

- **原始架构/子系统**：generic genirq，arm64 验证，RISC-V 实机验证。
- **原始补丁**：[genirq: use runtime constant to optimize handle_arch_irq access](https://lore.kernel.org/linux-arm-kernel/20260220090922.1506-3-jszhang@kernel.org/)
- **可移植点**：把启动后不再变化的 `handle_arch_irq` 间接指针改为运行时常量重写。
- **RISC-V 落点**：`kernel/irq/handle.c` 已共享；验证 RISC-V alternatives/runtime-const patching 和 icache 同步。
- **难度/阻塞**：低；补丁说明已在 Sipeed Lichee Pi 4A 上取得约 5.8% 的 perf sched 提升。
- **证据**：这是直接面向 RISC-V 测试过的通用优化。

### CORE-10. 禁止模块使用仅启动期修补的 runtime constants

- **原始架构/子系统**：arm64 / runtime-const、module。
- **原始补丁**：[arm64: make runtime const not usable by modules](https://lore.kernel.org/linux-arm-kernel/20260221023847.3506-1-jszhang@kernel.org/)
- **可移植点**：运行时常量只在 core kernel 启动阶段修补，模块不能假设相同 fixup 生命周期。
- **RISC-V 落点**：RISC-V runtime-const/alternatives 头文件和 module build checks。
- **难度/阻塞**：低；在 RISC-V 扩展 runtime constants 时应同步加入限制。
- **证据**：arm64 补丁直接复用了 x86 已发现的生命周期约束。

### CORE-11. 修复 LTO 下 `__READ_ONCE()` 原子性和静态分析语义

- **原始架构/子系统**：arm64 / compiler、memory access。
- **原始补丁**：[arm64: Fix non-atomic __READ_ONCE() with CONFIG_LTO=y](https://lore.kernel.org/linux-arm-kernel/20260130132951.2714396-2-elver@google.com/)、[arm64, compiler-context-analysis: Permit alias analysis through __READ_ONCE() with CONFIG_LTO=y](https://lore.kernel.org/linux-arm-kernel/20260216142436.2207937-4-elver@google.com/)
- **可移植点**：架构自定义 READ_ONCE 必须同时保证单次原子访问、阻止错误优化，并允许锁/别名静态分析理解数据流。
- **RISC-V 落点**：审计 `arch/riscv/include/asm/rwonce.h`、LTO 构建和 compiler context analysis。
- **难度/阻塞**：中；需要针对不同宽度、未对齐访问和编译器版本生成代码测试。
- **证据**：问题由 LTO 改变内联/别名分析触发，不是 ARM 寄存器特性。

### CORE-12. 为 Rust `READ_ONCE/WRITE_ONCE` 暴露架构能力

- **原始架构/子系统**：arm64+alpha + generic Rust。
- **原始补丁**：[arch: add CONFIG_ARCH_USE_CUSTOM_READ_ONCE for arm64/alpha](https://lore.kernel.org/linux-arm-kernel/20251231-rwonce-v1-1-702a10b85278@google.com/)、[rust: sync: add READ_ONCE and WRITE_ONCE](https://lore.kernel.org/linux-arm-kernel/20251231-rwonce-v1-2-702a10b85278@google.com/)
- **可移植点**：Rust 根据架构是否有自定义 READ_ONCE 选择 volatile 或 C helper，保持与 C 内存访问语义一致。
- **RISC-V 落点**：RISC-V Rust 构建、`rust/kernel/sync/rwonce.rs` 和架构 Kconfig。
- **难度/阻塞**：低；当前 RISC-V 若使用通用实现可直接共享，未来自定义实现时必须设置能力位。
- **证据**：generic Rust API 已共享，架构只声明访问实现类型。

### CORE-13. vDSO 多时钟和辅助时钟框架

- **原始架构/子系统**：generic vDSO + arm64。
- **原始补丁**：[vdso: Rework struct vdso_time_data and introduce struct vdso_clock](https://lore.kernel.org/linux-arm-kernel/20250303-vdso-clock-v1-19-c1b5c69a166f@linutronix.de/)、[vdso/gettimeofday: Add support for auxiliary clocks](https://lore.kernel.org/linux-arm-kernel/20250701-vdso-auxclock-v1-12-df7d9f87b9b8@linutronix.de/)
- **可移植点**：把 vDSO 数据从单时钟布局改为可扩展 clock 描述，并支持辅助硬件时钟。
- **RISC-V 落点**：`arch/riscv/kernel/vdso/`、time namespace、未来平台/虚拟化辅助 clock。
- **难度/阻塞**：中；需要定义稳定 clockmode、cycle reader 和用户态 ABI。
- **证据**：核心实现位于 `lib/vdso/` 和 `kernel/time/`，arm64 仅提供架构读取钩子。

### CORE-14. vDSO 兼容 time64 ABI 自测

- **原始架构/子系统**：generic selftests + ARM/arm64 compat vDSO。
- **原始补丁**：[selftests: vDSO: vdso_test_abi: Add test for clock_getres_time64()](https://lore.kernel.org/linux-arm-kernel/20251223-vdso-compat-time32-v1-4-97ea7a06a543@linutronix.de/)、[ARM: VDSO: provide clock_getres_time64()](https://lore.kernel.org/linux-arm-kernel/20251223-vdso-compat-time32-v1-7-97ea7a06a543@linutronix.de/)
- **可移植点**：用统一 ABI 测试覆盖 32-bit compat time64 symbol、fallback 和 patch-out 行为。
- **RISC-V 落点**：RISC-V 32-bit 用户态/compat vDSO 支持和 `tools/testing/selftests/vDSO/`。
- **难度/阻塞**：中；取决于内核是否支持 RV32 compat 或原生 RV32 测试环境。
- **证据**：自测框架是通用的，ARM 补丁展示了缺失 symbol 的处理方式。

### CORE-15. 推迟 NOHZ_FULL CPU 的动态文本修补 IPI

- **原始架构/子系统**：x86 + generic context tracking。
- **原始补丁**：[context_tracking,x86: Defer kernel text patching IPIs](https://lore.kernel.org/linux-arm-kernel/20251114151428.1064524-5-vschneid@redhat.com/)
- **可移植点**：用户态运行的 NOHZ_FULL CPU 不必立即接收同步 IPI，可在保证调用者等待所有 CPU 可见后延迟处理。
- **RISC-V 落点**：RISC-V alternatives、ftrace、kprobes 文本修改和 context-tracking work。
- **难度/阻塞**：高；需要严格证明指令可见性、返回内核前同步和远端 `fence.i`。
- **证据**：核心不变量是动态代码修改同步和 full-dynticks 隔离，适用于所有支持运行时文本修补的架构。

### CORE-16. 修复重入 kprobe 的 per-CPU 当前探针状态

- **原始架构/子系统**：generic kprobes。
- **原始补丁**：[kernel: kprobes: fix cur_kprobe corruption during re-entrant kprobe_busy_begin() calls](https://lore.kernel.org/linux-arm-kernel/20260302105347.3602192-2-khaja.khaji@oss.qualcomm.com/)
- **可移植点**：重入探针必须保存和恢复 per-CPU `cur_kprobe`，避免嵌套 busy path 破坏外层状态。
- **RISC-V 落点**：通用 `kernel/kprobes.c` 直接共享；增加 RISC-V 异常/中断嵌套压力测试。
- **难度/阻塞**：低。
- **证据**：补丁完全位于通用 kprobes core。

## 优先级

1. **近期直接验证**：CORE-7、CORE-9、CORE-10、CORE-11、CORE-12、CORE-16。
2. **明确架构实现**：CORE-1、CORE-2、CORE-4、CORE-5、CORE-8、CORE-13。
3. **依赖工具链或复杂同步**：CORE-3、CORE-14、CORE-15。
