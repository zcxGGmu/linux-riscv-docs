# RISC-V IRQ / SMP / Time 架构接口差距与可移植贡献点

## 1. 范围与结论

本文聚焦 RISC-V 相对 arm64/x86 在 IRQ 入口、root IRQ handler、IPI 生命周期、IMSIC MSI、CPU bring-up、ACPI IRQ 依赖以及 clockevent/clocksource 接口上的差距，并寻找可以直接移植、抽取为通用接口或通过 RISC-V 语义补全的贡献点。

固定分析基线如下：

- mainline：`d96fcfe1b7f94ac742984ae7986b94a116abff1b`，Linux 7.2-rc2，2026-07-10。
- linux-next：`bee763d5f341b99cf472afeb508d4988f62a6ca1`，next-20260710。
- 邮件窗口：2025-01-01 至 2026-07-10。
- 状态含义：`active RFC` 表示对应方向存在仍在修订的精确系列；`next` 表示主体已经进入固定 linux-next；`unclaimed` 表示缺口真实，但未找到精确的 RISC-V 实现或通用化系列。

统一分类采用：

- `G0`：主体已由 generic/mainline/next 覆盖，只剩测试、清理或 RISC-V 接线。
- `G1`：已有稳定 generic hook，可以直接实现 RISC-V backend。
- `G2`：两个或更多架构存在重复实现，适合下沉公共 helper 或状态机。
- `G3`：RISC-V 已有可用 fallback，但仍需要架构语义证明、正确性补强或快路径优化。
- `G4`：依赖尚未完成的硬件、固件、UAPI 或其他基础设施；本领域纯观察项不进入主表。

六维评分分别为 `impact`、`generality`、`readiness`、`validation`、`hardware-independence` 和 `acceptance`，单项 0-5 分。基础阈值为 P0=24-30、P1=18-23、P2=12-17；存在有界依赖或实质架构证明时允许降一级，因此 18 分的高风险通用化/测试项可保持 P2。

最终保留 **10 个主候选**：

- 优先级：P0 1 项、P1 5 项、P2 4 项。
- 分类：G0 1 项、G1 2 项、G2 3 项、G3 4 项。
- 状态：active RFC 1 项、next 1 项、unclaimed 8 项。
- 原始架构：arm64 4 项、x86 1 项、x86+arm64 2 项、shared 3 项。

近期最值得直接开工的是 **IRQ-09 clockevent oneshot-stopped 接线**。最适合跟进现有讨论的是 **IRQ-01 runtime constant**。最有明确 AIA 功能收益的是 **IRQ-04 IMSIC Multi-MSI**，而 **IRQ-07** 已不再是实现缺口，只应作为 linux-next 通用化后的测试补全。

## 2. 十项总表

| ID | 可移植贡献点 | 状态 | G / P / 总分 | 原始架构 | 建议定位 |
|---|---|---|---|---|---|
| IRQ-01 | RISC-V IRQ 入口接入 runtime constant | active RFC | G3 / P1 / 20 | arm64 | 跟进 genirq/arm64 RFC，补 RISC-V 接线与性能证明 |
| IRQ-02 | 统一 root IRQ handler 注册与只读化 | unclaimed | G2 / P2 / 18 | arm64 | runtime-constant 稳定后的第二阶段通用化 |
| IRQ-03 | 通用 per-CPU IPI descriptor 生命周期与 tick broadcast | unclaimed | G2 / P2 / 18 | arm64 | 先抽生命周期 helper，再迁移 tick broadcast |
| IRQ-04 | IMSIC Multi-MSI 分配与回滚 | unclaimed | G1 / P1 / 23 | arm64 | 明确功能缺口，优先实现 parent-domain 批量分配 |
| IRQ-05 | x86/IMSIC MSI vector move 公共状态机 | unclaimed | G2 / P2 / 18 | x86 | 只抽 move transaction，硬件 pending 语义留在架构侧 |
| IRQ-06 | IMSIC remote sync 改用 hard irq_work | unclaimed | G3 / P1 / 20 | shared | 用硬 IPI 缩短下一 jiffy 的同步延迟 |
| IRQ-07 | ACPI IRQ dependency 通用化测试后续 | next | G0 / P2 / 18 | shared | 不再改主体，仅补 probe-order 和错误表覆盖 |
| IRQ-08 | SBI HSM late-AP cleanup 与代际控制 | unclaimed | G3 / P1 / 20 | shared | 解决启动超时后迟到 hart 与重试冲突 |
| IRQ-09 | clockevent 补齐 oneshot-stopped 状态 | unclaimed | G1 / P0 / 26 | x86+arm64 | 最小、低风险、可独立提交 |
| IRQ-10 | RISC-V clocksource 稳定性测量与策略证明 | unclaimed | G3 / P1 / 20 | x86+arm64 | 先测量跨 hart 偏差，再落地 MUST_VERIFY 策略 |

> “原始架构”表示本候选所参考的成熟实现、活跃补丁或共同接口来源，不表示 RISC-V 代码本身来自该架构。

## 3. 完整候选卡片

<a id="irq-01"></a>
### IRQ-01：RISC-V IRQ 入口接入 runtime constant

- **状态**：`active RFC`。2026-02-20 已出现 genirq runtime-constant 和 arm64 入口接线系列；固定 mainline/linux-next 尚未包含该主体，也没有 RISC-V 接线。
- **分类与优先级**：G3，P1。
- **六维评分**：impact=4，generality=3，readiness=3，validation=4，hardware-independence=3，acceptance=3；**总分=20**。
- **原始架构**：arm64。arm64 是当前邮件系列中已经展示入口接线的架构；RISC-V 需要单独证明其 `noinstr`、指令重写和 I-cache 同步约束。
- **源报告映射**：`IST-01`。旧报告中的 G0/P0 已被独立审查纠正，最终分类为 G3/P1。
- **路径与符号**：
  - `kernel/irq/handle.c::{handle_arch_irq,set_handle_irq,generic_handle_arch_irq}`
  - `arch/riscv/kernel/traps.c::do_irq`
  - `drivers/irqchip/irq-riscv-intc.c::{riscv_intc_irq,riscv_intc_aia_irq}`
  - `arch/arm64/kernel/entry-common.c::{el0_interrupt,el1_interrupt}`
  - `CONFIG_DEBUG_ENTRY`
- **RISC-V 缺口**：RISC-V 外部中断入口仍通过可变函数指针间接调用 root handler。处理函数完成 irqchip 初始化后基本不再变化，但当前基线没有将该事实转化为固定目标调用。通用 runtime-constant 系列尚未合入，因此这不是“直接打开已有 generic 能力”，而是需要跟随 RFC 并完成 RISC-V 特有证明的快路径工作。
- **方案**：复用 genirq runtime-constant 机制，在 `do_irq()` 的 `noinstr` 路径增加 RISC-V callsite；保留 handler 未注册时的早期检查；handler 固化后通过受控 text patch 将间接调用改为固定目标，并执行必要的远端 I-cache 同步。RISC-V 部分不应重新发明一套 runtime-constant 框架。
- **第一版补丁边界**：
  1. 在通用系列稳定版本之上增加 RISC-V callsite 描述和 patchable sequence。
  2. 接线 `do_irq()`，覆盖 RV32/RV64 以及 AIA/非 AIA root handler。
  3. 增加反汇编检查、启动测试和 cycles/IRQ 基准结果；不在第一版同时重构 root handler 所有权。
- **阻塞**：`noinstr`/objtool 约束、alternatives 与 runtime patching 的执行顺序、RV32/RV64 指令长度、模块化 irqchip 初始化、跨 hart I-cache 一致性，以及 `CONFIG_DEBUG_ENTRY` 下的额外入口逻辑。
- **验证**：
  - 用 `objdump` 确认热路径从 load+indirect jump 转为固定目标序列。
  - QEMU virt 上分别覆盖 SBI interrupt、AIA/IMSIC、Sstc 与非 Sstc 组合。
  - 运行 IPI flood、网络中断压力和 `perf bench sched messaging`，比较 cycles/IRQ 与分支预测数据。
  - 构建并启动 `CONFIG_DEBUG_ENTRY`、lockdep、KASAN、PREEMPT_RT 配置。
- **维护者与列表**：Thomas Gleixner、RISC-V 架构维护者；`linux-kernel@vger.kernel.org`、`linux-riscv@lists.infradead.org`。涉及通用系列和 arm64 对照时抄送 `linux-arm-kernel@lists.infradead.org`。
- **原始补丁与来源**：
  - [genirq runtime constant 提案](https://lore.kernel.org/linux-arm-kernel/20260220090922.1506-3-jszhang@kernel.org/)
  - [arm64 IRQ 入口接线](https://lore.kernel.org/linux-arm-kernel/20260220090922.1506-4-jszhang@kernel.org/)

<a id="irq-02"></a>
### IRQ-02：统一 root IRQ handler 注册与只读化

- **状态**：`unclaimed`。mainline 中仍存在 genirq 与 arm64 私有的两套 root handler 注册模型，未发现 2025-2026 年完整通用化系列。
- **分类与优先级**：G2，P2。
- **六维评分**：impact=2，generality=4，readiness=3，validation=4，hardware-independence=4，acceptance=1；**总分=18**。
- **原始架构**：arm64。RISC-V 已使用 genirq 通用存储和注册函数，待通用化的主要重复来自 arm64 私有模型。
- **源报告映射**：`IST-02`。独立审查认为原 P0 过高，最终降为 P2；该项依赖 IRQ-01 的接口方向稳定，但不能与 IRQ-01 合并。
- **路径与符号**：
  - `kernel/irq/handle.c::{handle_arch_irq,set_handle_irq,generic_handle_arch_irq}`
  - `arch/riscv/kernel/irq.c::init_IRQ`
  - `drivers/irqchip/irq-riscv-intc.c::riscv_intc_init_common`
  - `arch/arm64/kernel/irq.c::{handle_arch_irq,set_handle_irq}`
- **RISC-V 缺口**：RISC-V 本身已经采用通用 root handler 模型，但其 runtime-constant 固化和“初始化后只读”的长期语义仍受两套所有权模型影响。arm64 私有实现包含 default handler、FIQ、伪 NMI 和 priority masking 特例，无法机械删除。
- **方案**：在 genirq 中表达“单次注册、可选默认 handler、启动后只读/固化”的共同合同，并为 arm64 的 FIQ/伪 NMI 特例保留明确 override。RISC-V 作为已使用通用模型的参考架构，不应为了对齐 arm64 引入新的私有层。
- **第一版补丁边界**：
  1. 为 genirq root handler 增加最小的 default-handler/只读状态表达，不改变调用路径。
  2. 迁移 arm64 普通 IRQ handler 的注册和存储，保留 FIQ/伪 NMI 独立字段。
  3. 增加重复注册负测和 early IRQ 测试；runtime text patch 继续由 IRQ-01 负责。
- **阻塞**：arm64 priority masking、伪 NMI、FIQ handler 与普通 IRQ 的生命周期不同；过度统一会把 arm64 特有语义泄漏到 genirq。该项接受度低，必须证明公共 API 比现有两套小实现更清晰。
- **验证**：arm64 GICv3/GICv5 与 RISC-V INTC/AIA 启动；重复注册、未注册早期中断、NMI/priority masking；objtool/noinstr；确认无额外热路径间接调用。
- **维护者与列表**：Thomas Gleixner；Catalin Marinas、Will Deacon；RISC-V 架构维护者；`linux-kernel`、`linux-arm-kernel`、`linux-riscv`。
- **原始补丁与来源**：
  - [固定 mainline 的 genirq root handler 实现](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/irq/handle.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)
  - [相关 arm64 runtime-constant 接线](https://lore.kernel.org/linux-arm-kernel/20260220090922.1506-4-jszhang@kernel.org/)

<a id="irq-03"></a>
### IRQ-03：通用 per-CPU IPI descriptor 生命周期与 tick broadcast

- **状态**：`unclaimed`。mainline 已有 arm64 与 RISC-V 两套相似实现；arm64 non-SGI IPI 已于 2025 年合入，但未发现公共生命周期抽取系列。
- **分类与优先级**：G2，P2。
- **六维评分**：impact=2，generality=4，readiness=3，validation=4，hardware-independence=4，acceptance=1；**总分=18**。
- **原始架构**：arm64。arm64 non-SGI IPI 扩展使两架构在 per-CPU descriptor 生命周期上的重复更加明确。
- **源报告映射**：`IST-03 + IST-05`。最终注册表将 tick broadcast 作为 descriptor 生命周期的第二阶段 consumer，删除了独立的 IST-05 主条目。
- **路径与符号**：
  - RISC-V：`arch/riscv/kernel/smp.c::{ipi_desc,riscv_ipi_set_virq_range,riscv_ipi_enable,riscv_ipi_disable,show_ipi_stats,handle_IPI,tick_broadcast}`
  - arm64：`arch/arm64/kernel/smp.c::{pcpu_ipi_desc,set_smp_ipi_range_percpu,ipi_setup,ipi_teardown,arch_show_interrupts,do_handle_IPI,tick_broadcast}`
  - 通用候选落点：`kernel/irq/ipi.c`、`include/linux/irq.h`
  - 时间子系统：`include/linux/clockchips.h::tick_broadcast`、`kernel/time/tick-broadcast.c`
- **RISC-V 缺口**：arm64/RISC-V 都需要分配 per-CPU virq、请求 handler、在 CPU online/offline 时 enable/disable descriptor，并向 `/proc/interrupts` 输出统计。两者还都把通用 tick broadcast cpumask 转为 timer IPI。当前重复代码的结构相似，但 parent domain、消息分发和 NMI 属性不同。
- **方案**：只抽 descriptor 请求/释放、CPUHP enable/disable 和统计 helper；架构继续拥有 parent irqdomain、消息表、dispatch callback 与 NMI-capable 属性。tick broadcast 在第二阶段通过该 helper 注册 timer IPI，避免第一版引入覆盖全部 IPI 模型的 `generic_ipi_set` 大接口。
- **第一版补丁边界**：
  1. 在 `kernel/irq/ipi.c` 提供 descriptor 生命周期和统计 helper。
  2. 分别迁移 arm64 non-SGI/per-CPU descriptor 与 RISC-V IMSIC/SBI IPI descriptor。
  3. 将两架构 `tick_broadcast()` 迁为该 helper 的 consumer，并加入 CPU hotplug/NO_HZ 测试。
- **阻塞**：arm64 同时有 SGI、LPI/non-SGI 和 priority masking；RISC-V 同时有 IMSIC 与 SBI+software mux fallback。公共层必须允许不同 parent domain，且不能改变 timer IPI 的 deep-idle wakeup 能力。
- **验证**：
  - CPU hotplug 循环和 `/proc/interrupts` IPI 统计一致性。
  - call-function、reschedule、irq_work、timer、backtrace、KGDB 消息。
  - arm64 GICv3/GICv5 与 RISC-V AIA/SBI 双后端。
  - `CLOCK_EVT_FEAT_C3STOP`、NO_HZ_IDLE、NO_HZ_FULL、suspend/resume 与 timer migration。
- **维护者与列表**：Thomas Gleixner、Daniel Lezcano、arm64/RISC-V 架构维护者；`linux-kernel`、`linux-arm-kernel`、`linux-riscv`。
- **原始补丁与来源**：
  - [arm64 non-SGI IPI v7](https://lore.kernel.org/linux-arm-kernel/20250703-gicv5-host-v7-18-12e71f1b3528@kernel.org/)
  - [arm64 non-SGI IPI mainline commit ba1004f861d1](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=ba1004f861d16f24179f14f13f70c09227ccbffb)

<a id="irq-04"></a>
### IRQ-04：IMSIC Multi-MSI 分配与回滚

- **状态**：`unclaimed`。固定 mainline/linux-next 的 IMSIC base domain 明确拒绝 `nr_irqs > 1`。
- **分类与优先级**：G1，P1。
- **六维评分**：impact=4，generality=4，readiness=4，validation=4，hardware-independence=4，acceptance=3；**总分=23**。
- **原始架构**：arm64。注册表以 arm64/common MSI library 工作作为原始架构来源；实际实现目标是 RISC-V IMSIC。
- **源报告映射**：`IST-08`。独立审查确认该项有明确拒绝点和可编译的 allocator/rollback 边界，可保留为 P1。
- **路径与符号**：
  - `drivers/irqchip/irq-riscv-imsic-platform.c::imsic_irq_domain_alloc`
  - `drivers/irqchip/irq-riscv-imsic-state.c::{imsic_vector_alloc,imsic_vector_free}`
  - MSI parent-domain 分配、irqdomain data 和 compose-message 路径
- **RISC-V 缺口**：PCI Multi-MSI 或 platform multi-MSI 一次请求多个 IRQ 时，IMSIC base domain 直接返回 `-EOPNOTSUPP`。设备只能退回单 MSI/MSI-X，或在不支持回退时失败。
- **方案**：扩展 IMSIC vector allocator 支持 `nr_irqs`；依据 MSI 类型选择连续或非连续 EID；批量建立 irqdomain data 和 MSI message；任何中途失败都按已分配数量逆序回滚。优先复用 MSI core parent-domain API，不在 IMSIC 中复制通用 MSI 管理逻辑。
- **第一版补丁边界**：
  1. 为 IMSIC state allocator 增加批量分配和批量释放 API。
  2. 在 platform domain 中支持 Multi-MSI 分配、message compose 和完整失败回滚。
  3. 增加合成设备测试和 EID 碎片/耗尽 fault injection。
  4. 第一版不同时实现 vCPU direct injection，也不抽取 IRQ-05 的 vector-move 状态机。
- **阻塞**：PCI Multi-MSI 的 power-of-two 与 message-data 连续性、每 CPU EID 空间碎片、整组 affinity move、CPU hotplug 期间的部分分配，以及 MSI-X 与 Multi-MSI 的不同约束。
- **验证**：NVMe/virtio 多向量设备、合成 Multi-MSI endpoint、每个分配阶段的失败回滚、CPU hotplug、affinity churn、EID 碎片和耗尽压力。
- **维护者与列表**：Thomas Gleixner、RISC-V irqchip/架构维护者；`linux-kernel@vger.kernel.org`、`linux-riscv@lists.infradead.org`。
- **原始补丁与来源**：
  - [common MSI library 系列 03/12](https://lore.kernel.org/linux-arm-kernel/b906a38d443577de45923b335d80fc54c5638da0.1750860131.git.namcao@linutronix.de/)
  - [固定 mainline IMSIC platform driver](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/irqchip/irq-riscv-imsic-platform.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)

<a id="irq-05"></a>
### IRQ-05：x86/IMSIC MSI vector move 公共状态机

- **状态**：`unclaimed`。x86 APIC 与 RISC-V IMSIC 在 mainline 中均有成熟的延迟 vector move 逻辑，但未发现公共状态机抽取系列。
- **分类与优先级**：G2，P2。
- **六维评分**：impact=2，generality=4，readiness=3，validation=4，hardware-independence=4，acceptance=1；**总分=18**。
- **原始架构**：x86。IMSIC 实现和注释直接参考了 x86 APIC vector move，但硬件 pending 状态并不等价。
- **源报告映射**：`IST-10`。独立审查将其从 P0 降为 P2，要求避免把 x86 IRR/APIC 与 IMSIC EIP/EIE 强行抽成同一硬件模型。
- **路径与符号**：
  - IMSIC platform：`drivers/irqchip/irq-riscv-imsic-platform.c::{imsic_irq_set_affinity,imsic_irq_force_complete_move}`
  - IMSIC state：`drivers/irqchip/irq-riscv-imsic-state.c::imsic_vector_move`
  - x86：`arch/x86/kernel/apic/vector.c::{apic_force_complete_move,free_moved_vector,__vector_cleanup}`
  - 通用：`kernel/irq/migration.c::{__irq_move_irq,irq_force_complete_move}`
- **RISC-V 缺口**：两套实现都管理 old/new vector、延迟完成、CPU offline 强制清理以及非原子 MSI 更新窗口；genirq 当前只提供最外层 force-complete hook。重复存在，但硬件 pending-bit 读取、replay 和最终清理条件不同。
- **方案**：在 genirq 中只抽 move transaction 的生命周期和状态所有权，包括 old/new handle、temporary/final MSI program callback、pending replay callback 和 force-cleanup callback。x86 与 IMSIC 保留硬件 pending 状态判断和低层寄存器操作。
- **第一版补丁边界**：
  1. 定义不包含硬件 pending 语义的 `irq_vector_move` 状态和状态转换 helper。
  2. 先迁移 IMSIC 的 metadata、回滚和 force-complete 编排。
  3. 再用 x86 作为第二 consumer 验证抽象；若 x86 迁移导致更多分支或间接调用，则缩小为仅共享 helper。
- **阻塞**：x86 IRR/APIC 与 IMSIC EIP/EIE 的可见性、清除和 replay 语义不同；过度抽象可能增加热路径间接调用，或把非原子 MSI update 的具体顺序错误地固定到 genirq。
- **验证**：PCI IRQ affinity 高频切换、不可原子更新 MSI message 的设备、pending interrupt replay、CPU offline/online、分配失败、lockdep、KCSAN 和 fault injection。
- **维护者与列表**：Thomas Gleixner、x86 APIC 维护者、RISC-V irqchip 维护者；`linux-kernel`、`linux-riscv`。
- **原始补丁与来源**：
  - [IMSIC force-complete move](https://lore.kernel.org/linux-arm-kernel/20250217085657.789309-9-apatel@ventanamicro.com/)
  - [IMSIC non-atomic MSI update](https://lore.kernel.org/linux-arm-kernel/20250217085657.789309-11-apatel@ventanamicro.com/)

<a id="irq-06"></a>
### IRQ-06：IMSIC remote sync 改用 hard irq_work

- **状态**：`unclaimed`。固定 mainline 仍通过目标 CPU 上的 pinned timer 执行 remote sync，未发现替代系列。
- **分类与优先级**：G3，P1。
- **六维评分**：impact=4，generality=3，readiness=3，validation=4，hardware-independence=3，acceptance=3；**总分=20**。
- **原始架构**：shared。候选依赖 generic irq_work 与 RISC-V 已有硬 IPI irq_work 能力，不是从单一架构机械移植。
- **源报告映射**：`IST-11`。独立审查确认源码边界明确，保留 G3/P1。
- **路径与符号**：
  - `drivers/irqchip/irq-riscv-imsic-state.c::{__imsic_remote_sync,__imsic_local_timer_start,imsic_local_timer_callback,imsic_local_sync_all}`
  - `kernel/irq_work.c::{irq_work_queue_on,arch_irq_work_raise}`
  - `arch/riscv/kernel/smp.c::{arch_irq_work_raise,arch_irq_work_has_interrupt}`
  - `add_timer_on()`
- **RISC-V 缺口**：远端 IMSIC enable/move 清理通过目标 CPU 的下一 jiffy pinned timer 完成，正常情况下会引入毫秒级延迟。RISC-V 已能通过硬 IPI 触发 irq_work，因此现有 timer 路径不是功能缺失，而是可消除的高延迟 fallback。
- **方案**：为每 CPU IMSIC sync state 增加 hard irq_work。dirty bitmap 从空变为非空时只 queue 一次，目标 CPU 在硬 irq_work 中合并并应用全部 dirty state；CPU offline/dying 或 queue 失败时保留 timer/next-online 全量同步作为 fallback。
- **第一版补丁边界**：
  1. 增加 per-CPU hard irq_work 和合并 dirty bitmap 的内存序。
  2. 将在线 CPU 的 remote sync 从 `add_timer_on()` 迁移到 `irq_work_queue_on()`。
  3. 保留 timer fallback，并加入 CPU dying、queue failure 和重复合并测试。
- **阻塞**：调用点可能持有 raw spinlock 且 IRQ disabled；需要证明 queue-on 的内存序、递归行为、CPU dying 生命周期和 PREEMPT_RT 下 hard/lazy work 分类正确。
- **验证**：MSI mask/unmask、affinity churn 和 vector move 延迟；CPU offline race；irq_work flood；timer fallback；lockdep、KCSAN、PREEMPT_RT。
- **维护者与列表**：Thomas Gleixner、RISC-V irqchip/架构维护者；`linux-kernel`、`linux-riscv`。
- **原始补丁与来源**：
  - [固定 mainline IMSIC state 实现](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/irqchip/irq-riscv-imsic-state.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)
  - [固定 mainline irq_work 实现](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/irq_work.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)

<a id="irq-07"></a>
### IRQ-07：ACPI IRQ dependency 通用化测试后续

- **状态**：`next`。通用 ACPI IRQ dependency 改造已进入固定 linux-next；实现主体不再是 RISC-V 缺口。
- **分类与优先级**：G0，P2。
- **六维评分**：impact=2，generality=3，readiness=3，validation=4，hardware-independence=4，acceptance=2；**总分=18**。
- **原始架构**：shared。通用改造同时服务多个架构和 irqchip，RISC-V 剩余价值主要是 AIA 拓扑覆盖。
- **源报告映射**：`IST-12`。独立审查将旧 P0 实现候选纠正为 G0/P2 测试后续。
- **路径与符号**：
  - `drivers/acpi/irq.c`
  - `drivers/acpi/riscv/irq.c`
  - `drivers/irqchip/irq-riscv-intc.c::acpi_set_irq_model`
  - linux-next 的 RISC-V GSI handle 回调和 probe dependency 路径
- **RISC-V 缺口**：固定 linux-next 已解决主体接口问题。剩余缺口是缺乏对 RINTC→IMSIC→APLIC→设备依赖链的自动化 probe-order 回归、错误 GSI、malformed MADT/AIA table、多个控制器 region 和循环依赖覆盖。
- **方案**：使用 ACPICA table override、QEMU ACPI 启动场景或可接受的 kselftest 外围，构造正确与错误拓扑；随机延迟 irqchip/consumer probe，验证 dependency graph 不死锁、不提前消费无效 GSI，并保留可诊断错误。
- **第一版补丁边界**：
  1. 增加一组最小 RISC-V AIA ACPI table fixtures。
  2. 覆盖正常 probe deferral、错误 GSI、缺失 parent、多个 APLIC/IMSIC region。
  3. 不修改已进入 linux-next 的主体接口，除非测试发现确定回归。
- **阻塞**：内核树缺少成熟的 ACPI irqchip 单元测试框架；若只能依赖 QEMU 外围测试，需要维护者接受测试落点和固件表生成方式。
- **验证**：纯 ACPI 启动、模块化 consumer、随机 probe 延迟、错误 GSI、malformed table、多个 APLIC/IMSIC region、无 DT fallback。
- **维护者与列表**：Rafael Wysocki、Thomas Gleixner、RISC-V ACPI/irqchip 维护者；`linux-acpi@vger.kernel.org`、`linux-kernel`、`linux-riscv`。
- **原始补丁与来源**：
  - [ACPI IRQ 通用化 v4 5/7](https://lore.kernel.org/linux-arm-kernel/20260709-gic-v5-acpi-iwb-probe-deferral-v4-5-48dae790f871@kernel.org/)
  - [固定 linux-next ACPI IRQ 实现](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/tree/drivers/acpi/irq.c?id=bee763d5f341b99cf472afeb508d4988f62a6ca1)

<a id="irq-08"></a>
### IRQ-08：SBI HSM late-AP cleanup 与代际控制

- **状态**：`unclaimed`。RISC-V parallel bring-up 已进入 mainline，但 RISC-V 尚未实现 `arch_cpuhp_cleanup_kick_cpu()` 的有效 cleanup。
- **分类与优先级**：G3，P1。
- **六维评分**：impact=4，generality=3，readiness=3，validation=4，hardware-independence=3，acceptance=3；**总分=20**。
- **原始架构**：shared。generic CPU hotplug 提供 cleanup hook，arm64 parallel hotplug 系列提供异常路径参考，RISC-V 需要结合 SBI HSM 语义实现。
- **源报告映射**：`IST-14`。独立审查确认现有 `boot_data` 缺少代际字段，保留 G3/P1。
- **路径与符号**：
  - `kernel/cpu.c::{cpuhp_bp_sync_alive,arch_cpuhp_cleanup_kick_cpu}`
  - `arch/riscv/kernel/smpboot.c::arch_cpuhp_kick_ap_alive`
  - `arch/riscv/kernel/cpu_ops_sbi.c::{boot_data,sbi_cpu_start,sbi_hsm_hart_get_status,sbi_cpu_is_stopped}`
- **RISC-V 缺口**：CPU 启动 timeout 后，generic core 调用弱 no-op cleanup。SBI `HART_START` 可能随后迟到，旧 `boot_data` 仍能把 hart 带入当前内核，与重试、present/online mask 或新的启动参数冲突。
- **方案**：为每 CPU boot data 增加 generation/cookie 和目标状态；secondary entry 在继续启动前验证 cookie；cleanup hook 撤销旧 cookie、查询 HSM state，并等待 STOPPED，或让迟到 hart 在自检失败后进入安全 park/stop 路径。
- **第一版补丁边界**：
  1. 在 RISC-V SBI boot data 中增加 generation/cookie，并在 secondary entry 校验。
  2. 实现 `arch_cpuhp_cleanup_kick_cpu()`，覆盖 START_PENDING、STARTED、STOPPED 和固件错误状态。
  3. 增加 OpenSBI/QEMU fault injection，模拟迟到启动和重试；第一版不依赖不存在的远端强制停止 SBI 调用。
- **阻塞**：SBI HSM 没有通用的远端强制停止已 STARTED hart 接口；固件可能返回错误或过时状态，因此必须依赖 secondary 自检，不能假设 cleanup 一定能立即把 hart 变为 STOPPED。
- **验证**：延迟 `HART_START`、丢启动 IPI、错误 HSM 状态、并行 boot、offline/online 重试、启动 timeout 后再次 online、suspend/thaw。
- **维护者与列表**：Thomas Gleixner、Peter Zijlstra、RISC-V/SBI 维护者；`linux-kernel`、`linux-riscv`。
- **原始补丁与来源**：
  - [RISC-V parallel CPU bring-up commit 231fb999a9ac](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=231fb999a9acd17b1335e79f0fd6fc627353a6bc)
  - [arm64 parallel hotplug v3 cleanup 参考](https://lore.kernel.org/linux-arm-kernel/20260624092537.2916971-13-ruanjinjie@huawei.com/)

<a id="irq-09"></a>
### IRQ-09：clockevent 补齐 oneshot-stopped 状态

- **状态**：`unclaimed`。固定 mainline/linux-next 均未接线。
- **分类与优先级**：G1，P0。
- **六维评分**：impact=5，generality=4，readiness=5，validation=4，hardware-independence=4，acceptance=4；**总分=26**。
- **原始架构**：x86+arm64。成熟 clockevent 驱动已经为 `CLOCK_EVT_STATE_ONESHOT_STOPPED` 提供硬件停止 callback，ARM arch timer 是直接对照。
- **源报告映射**：`IST-15`。该项是本领域唯一 P0，独立审查确认 callback 缺失会使 core 返回 `-ENOSYS`，且补丁边界最小。
- **路径与符号**：
  - `drivers/clocksource/timer-riscv.c::{riscv_clock_event,riscv_clock_shutdown}`
  - `drivers/clocksource/arm_arch_timer.c::__arch_timer_setup`
  - `kernel/time/tick-oneshot.c::tick_program_event`
  - `kernel/time/clockevents.c::__clockevents_switch_state`
- **RISC-V 缺口**：clockevents core 进入 `CLOCK_EVT_STATE_ONESHOT_STOPPED` 时，只在 `.set_state_oneshot_stopped` 存在时执行硬件 stop。RISC-V 已有同时适用于 SBI timer 和 Sstc comparator 的 `riscv_clock_shutdown()`，但只赋给 `.set_state_shutdown`。
- **方案**：把 `riscv_clock_shutdown` 同时赋给 `.set_state_shutdown` 和 `.set_state_oneshot_stopped`，并注释说明两条 timer 路径都通过最大 comparator 值停止下一次事件。
- **第一版补丁边界**：
  1. 一个功能补丁完成 callback 接线和必要注释。
  2. 一个测试/验证说明覆盖 SBI timer、Sstc、NO_HZ 和 tick broadcast 状态转换。
  3. 不在同一系列重构 timer driver 或引入新的 clockevent helper。
- **阻塞**：风险较低；需要确认旧 SBI timer 实现对 `U64_MAX` 的行为，以及从 oneshot-stopped 恢复后首次事件编程不会继承错误状态。
- **验证**：NO_HZ_IDLE、NO_HZ_FULL、tick broadcast enter/exit、deep idle、CPU hotplug、Sstc 与 SBI 双路径；跟踪 clockevent state transition，确认停止期间不产生幽灵 timer interrupt。
- **维护者与列表**：Daniel Lezcano、Thomas Gleixner、RISC-V timer/架构维护者；`linux-kernel`、`linux-riscv`。
- **原始补丁与来源**：
  - [固定 mainline RISC-V timer driver](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/clocksource/timer-riscv.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)
  - [固定 mainline ARM arch timer 对照](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/clocksource/arm_arch_timer.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)

<a id="irq-10"></a>
### IRQ-10：RISC-V clocksource 稳定性测量与策略证明

- **状态**：`unclaimed`。固定 mainline/linux-next 的 `riscv_clocksource.flags` 只有 `CLOCK_SOURCE_IS_CONTINUOUS`。
- **分类与优先级**：G3，P1。
- **六维评分**：impact=4，generality=3，readiness=3，validation=4，hardware-independence=3，acceptance=3；**总分=20**。
- **原始架构**：x86+arm64。x86 TSC 提供 `CLOCK_SOURCE_MUST_VERIFY` 和 watchdog policy 的成熟参考，arm64 提供跨 CPU counter 稳定性处理经验。
- **源报告映射**：`IST-16`。独立审查将旧 P0 降为 P1，并要求先完成测量和策略证明，避免在缺少 watchdog 的平台上无条件启用验证标志。
- **路径与符号**：
  - `drivers/clocksource/timer-riscv.c::{riscv_clocksource,riscv_clocksource_rdtime}`
  - `kernel/time/clocksource.c`
  - `arch/x86/kernel/tsc.c`
  - `CLOCK_SOURCE_MUST_VERIFY`
- **RISC-V 缺口**：驱动注释承认不同 hart 的时间读数技术上可能倒退，只要求在一个 tick 内同步；但该 clocksource 以 rating 400 注册，未要求被选为主 clocksource 前通过 watchdog。直接设置 `MUST_VERIFY` 又可能使没有可靠 reference clock 的平台失去可用 clocksource。
- **方案**：默认以 `CLOCK_SOURCE_MUST_VERIFY` 表达未经证明的跨 hart 稳定性；平台若有明确的强一致性保证，并通过启动期多 CPU sanity check，可清除或绕过该策略。测量逻辑应记录最大 skew/倒退，而不是把 IPI 往返延迟直接等同于 counter 偏差。
- **第一版补丁边界**：
  1. 增加可复现的跨 hart offset/drift 测量和调试输出，明确阈值来源。
  2. 在具备 watchdog reference 的平台启用 `CLOCK_SOURCE_MUST_VERIFY`，定义无 reference clock 时的保守 fallback。
  3. 只有测量证明不会误判“一 tick 内同步”的正常平台后，才提交默认策略变更。
- **阻塞**：部分 RISC-V 平台没有独立 watchdog reference clock；IPI latency 会污染跨 CPU 采样；阈值依赖 timebase、CPU 数量和调度抖动。错误策略可能降低系统可启动性或错误标记稳定 clocksource。
- **验证**：QEMU 注入 per-hart offset/drift 和倒退、CPU migration、NO_HZ_FULL、不同 timebase frequency、不同 CPU 数量、无 watchdog fallback；确认正常的一 tick skew 不被误判。
- **维护者与列表**：Daniel Lezcano、Thomas Gleixner、RISC-V timer/架构维护者；`linux-kernel`、`linux-riscv`。
- **原始补丁与来源**：
  - [固定 mainline RISC-V clocksource](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/clocksource/timer-riscv.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)
  - [clocksource watchdog 重写 commit 763aacf86f1b](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=763aacf86f1baefb134c70813aa8c72d1675d738)

## 4. 分阶段贡献路线

### 4.1 低依赖、可较快验证

1. **IRQ-09：clockevent oneshot-stopped**
   - 先做最小 callback 接线。
   - 在 SBI timer 与 Sstc 双路径验证状态切换。
   - 这是最适合作为独立首个系列的项目。
2. **IRQ-07：ACPI IRQ dependency 测试**
   - 基于已进入 linux-next 的实现补测试，不再重做接口。
   - 优先构造错误 GSI、probe deferral 和多控制器 region 场景。
3. **IRQ-10：clocksource 稳定性测量**
   - 先建立测量与故障注入证据，再决定默认 `MUST_VERIFY` 策略。
   - 不应在没有 reference clock 的平台上直接施加无法满足的验证要求。

### 4.2 跨架构通用化

1. **IRQ-01：runtime constant RISC-V 接线**
   - 直接参与现有 RFC review。
   - 等通用 patching 机制稳定后补 RISC-V `do_irq()` 接线和性能数据。
2. **IRQ-02：root IRQ handler 所有权**
   - 依赖 IRQ-01 的接口方向稳定。
   - 只统一普通 root handler 的单次注册和只读语义，arm64 FIQ/伪 NMI 保留特例。
3. **IRQ-03：IPI descriptor 生命周期**
   - 第一阶段只抽 request/free、CPUHP enable/disable 和统计。
   - 第二阶段再把 tick broadcast 作为 consumer 迁移。
4. **IRQ-05：MSI vector move transaction**
   - 只抽状态生命周期和回滚编排。
   - x86 APIC 与 IMSIC 的 pending/replay 语义继续留在各自驱动中。

### 4.3 AIA 与固件依赖

1. **IRQ-04：IMSIC Multi-MSI**
   - 先完成批量 EID 分配、message compose 和失败回滚。
   - 后续再处理整组 affinity move，不与 direct injection 混合。
2. **IRQ-06：IMSIC hard irq_work remote sync**
   - 先证明 raw-spinlock、内存序和 CPU dying 场景正确。
   - 保留 timer fallback，避免一次性删除恢复路径。
3. **IRQ-08：SBI HSM late-AP cleanup**
   - 需要 OpenSBI/QEMU fault injection。
   - 设计必须接受“固件无法远端强制停止已启动 hart”的现实，以 generation/cookie 和 secondary 自检闭环。

## 5. 已确认伪差距

以下项目不能再作为独立的“RISC-V 缺失功能”：

- **RISC-V 不支持 parallel CPU bring-up**：不成立。RISC-V 已选择 `HOTPLUG_PARALLEL`，并接入 split-startup 和 `arch_cpuhp_kick_ap_alive()`。
- **RISC-V 未接入 context tracking**：不成立。RISC-V 已选择 `HAVE_CONTEXT_TRACKING_USER`，IRQ/异常入口已使用 generic irqentry/context-tracking。
- **IMSIC 不更新 effective affinity**：不成立。IMSIC/APLIC 已调用 `irq_data_update_effective_affinity()`，并选择 `GENERIC_IRQ_EFFECTIVE_AFF_MASK`。
- **RISC-V timer 在 CPU offline 后不停止 comparator**：已修复。mainline commit `70c93b026ed07078e933583591aa9ca6701cd9da` 已在 dying CPU 路径停止 clockevent。
- **ACPI IRQ dependency 主体仍未实现**：截至固定 linux-next 已不成立。主体已进入 next，主表仅保留 IRQ-07 测试后续。

## 6. 被移出 IRQ 主表的旧候选

| 旧 ID | 处理 | 原因或新归属 |
|---|---|---|
| IST-04 | 降为观察项 | 为标准 IPI 分配独立 IMSIC EID 属性能设计，受 EID 预算、guest-file 预留和优先级策略约束，缺少近期独立合入边界。 |
| IST-06 | 移出主表 | SMP stop/crash-stop 通用化抽象面过大，没有明确的第一版可编译 API；不同架构的 mask、超时和 escalation 语义差异显著。 |
| IST-07 | 降为 P3 基础设施观察 | non-maskable stop/backtrace 依赖 RISC-V NMI 路由、入口和固件/硬件基础，当前不能独立实现。 |
| IST-09 | 并入 `VIRT-07` | `irq_set_vcpu_affinity()`、irq-bypass 与 IMSIC direct injection 属同一 KVM/IOMMU 生命周期，不在 IRQ 主表重复维护。 |
| IST-13 | 并入 `PLAT-01` | ACPI CPU physical hotplug 的主要接口和规范问题属于 Platform/ACPI 领域。 |
| IST-17 | 删除近期候选 | 尚无具体 RISC-V timer erratum 或虚拟化故障 consumer，不能仅凭 arm64 先例建立 accessor 层。 |
| IST-18 | 降为调查附录 | context-tracking off-stack 目前只有审计步骤，没有定位到阻塞调用或可提交 patch；现有 context tracking 功能本身已经存在。 |

## 7. 结论

IRQ/SMP/Time 领域的贡献机会并不等同于把 arm64/x86 的 Kconfig 或接口逐项复制到 RISC-V。高价值工作集中在三类：

1. **已有 generic hook 的 RISC-V 正确性补全**，以 IRQ-09 为代表。
2. **两个架构已经重复实现、但仍能保持硬件语义边界的公共化**，以 IRQ-03 和 IRQ-05 为代表。
3. **RISC-V 已有 fallback、但存在明确延迟或失败恢复缺口的语义增强**，以 IRQ-06、IRQ-08 和 IRQ-10 为代表。

推荐实际开工顺序为：**IRQ-09 → IRQ-07/IRQ-10 测试证据 → IRQ-01 RFC 接线 → IRQ-04 Multi-MSI → IRQ-06/IRQ-08 → IRQ-03/IRQ-02/IRQ-05 通用化**。这一顺序优先获得可独立验证的成果，再进入需要跨子系统协调和硬件语义证明的系列。
