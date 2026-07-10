# linux-arm-kernel 2025-2026 IRQ/Timer/PMU/KVM → RISC-V 可移植性审计

## 1. 范围与方法

- 数据源：`data/parsed/patches.jsonl` 与 `data/parsed/supplemental_patches.jsonl`，共 65,635 条唯一补丁记录。
- 时间窗口：`2025-01-01T00:00:00Z`（含）至 `2026-07-11T00:00:00Z`（不含），即覆盖到 2026-07-10。
- 全量脚本按 `touched_paths` 为主、标题为辅筛选 IRQ/GIC/ITS/MSI、timer/clocksource、PMU/perf、KVM/虚拟化补丁。
- 路径强筛并按规范化 `logical_title` 保留最新修订后，候选池为：IRQ 582、timer 180、PMU 231、KVM 1,675。各池存在交叉。
- 人工复核最新版本、补丁说明和改动路径，并将同一能力的系列补丁合并为一个贡献点。
- 排除：纯 DTS/DT binding、板级 IRQ/定时器数据、仅增加某 ARM SoC compatible、无通用不变量的厂商 uncore PMU、stable 入树通知、讨论邮件、纯重命名/格式化、x86-only KVM 实现。
- 最终保留 **48 个独立贡献点**：IRQ/AIA 19、timer/Sstc 4、PMU/SBI PMU 9、KVM RISC-V 16。

难度定义：

- **低**：通用代码或 selftest 可直接共享，仅需启用 RISC-V 构建或补少量架构 helper。
- **中**：存在明确的 RISC-V 对应模型，但寄存器、状态机或异常路径需按 RISC-V 重写。
- **高**：依赖尚未完整落地的 AIA 直注、RISC-V IOMMU MSI、guest_memfd/private memory、硬件 dirty tracking 或 mediated PMU。

## 2. IRQ/GIC/ITS/MSI → AIA/APLIC/IMSIC

### IRQ-1. 虚拟中断表分配遵守 PREEMPT_RT 原子上下文

- **原始架构/子系统**：GICv3 ITS/vPE。
- **原始补丁**：[irqchip/gic-v3-its: Use GFP_ATOMIC_RT gfp flag in allocate_vpe_l1_table()](https://lore.kernel.org/linux-arm-kernel/20260520204628.933654-2-longman@redhat.com/)
- **可移植点**：中断控制器在 raw spinlock、IRQ-disabled 或其他原子上下文中扩展虚拟中断表时，分配标志必须兼容 PREEMPT_RT，不能进入可睡眠分配路径。
- **RISC-V 落点**：IMSIC guest interrupt file、HGEI/vCPU identity 表和 APLIC MSI 路由表的惰性分配。
- **难度/阻塞**：中；需要审核 AIA 虚拟化路径的锁上下文和内存预分配策略。
- **证据**：补丁由 PREEMPT_RT 内核的 “sleeping function called from invalid context” 报告触发，问题位于 vPE L1 table 分配路径。

### IRQ-2. per-CPU IRQ/NMI 显式 affinity API

- **原始架构/子系统**：通用 genirq + arm64 PMU。
- **原始补丁**：[genirq: Add affinity to percpu_devid interrupt requests](https://lore.kernel.org/linux-arm-kernel/20251020122944.3074811-15-maz@kernel.org/)、[genirq: Update request_percpu_nmi() to take an affinity](https://lore.kernel.org/linux-arm-kernel/20251020122944.3074811-16-maz@kernel.org/)
- **可移植点**：per-CPU 中断不应默认等价于 `cpu_possible_mask`，设备可显式声明可服务 hart 集合。
- **RISC-V 落点**：`kernel/irq/manage.c`、`drivers/perf/riscv_pmu*.c`、IMSIC local interrupt affinity。
- **难度/阻塞**：低到中；需确认 RISC-V PMU IRQ 与 IMSIC identity 的 hart 约束。
- **证据**：系列为 `irqaction` 和 request primitives 增加 affinity，并更新 PMU/NMI 调用者。

### IRQ-3. IRQ kthread preferred affinity 跨 hotplug/cpuset 保持

- **原始架构/子系统**：通用 genirq。
- **原始补丁**：[genirq: Correctly handle preferred kthreads affinity](https://lore.kernel.org/linux-arm-kernel/20251013203146.10162-33-frederic@kernel.org/)
- **可移植点**：IRQ 线程 affinity 应通过 kthread affinity 机制维护，避免被 CPU hotplug、cpuset isolation 或 housekeeping 更新覆盖。
- **RISC-V 落点**：通用 `kernel/irq/manage.c`，直接覆盖 RISC-V 平台 IRQ 线程。
- **难度/阻塞**：低；需要 isolation/hotplug 测试。
- **证据**：补丁明确指出直接调用 scheduler 设置 affinity 无法跨 hotplug 和 cpuset 更新保持。

### IRQ-4. MSI prepare/teardown 对称生命周期

- **原始架构/子系统**：通用 MSI core + GICv3 ITS。
- **原始补丁**：[genirq/msi: Add .msi_teardown() callback as the reverse of .msi_prepare()](https://lore.kernel.org/linux-arm-kernel/20250513163144.2215824-2-maz@kernel.org/)、[irqchip/gic-v3-its: Implement .msi_teardown() callback](https://lore.kernel.org/linux-arm-kernel/20250513163144.2215824-3-maz@kernel.org/)、[genirq/msi: Engage the .msi_teardown() callback on domain removal](https://lore.kernel.org/linux-arm-kernel/20250513163144.2215824-5-maz@kernel.org/)
- **可移植点**：MSI domain/device allocation context 必须有与 prepare 对称的 teardown，不能依赖“释放最后一个 vector”猜测设备生命周期。
- **RISC-V 落点**：IMSIC MSI parent/domain、APLIC MSI mode、PCI MSI domain。
- **难度/阻塞**：中；需要审核 RISC-V MSI domain 是否保存 per-device allocation state。
- **证据**：ITS 在单 MSI 释放后删除 endpoint 结构，随后重新分配多个 MSI 时触发重复 prepare 和生命周期错误。

### IRQ-5. MSI IOMMU IOVA 所有权去指针化

- **原始架构/子系统**：通用 MSI + DMA-IOMMU。
- **原始补丁**：[genirq/msi: Store the IOMMU IOVA directly in msi_desc instead of iommu_cookie](https://lore.kernel.org/linux-arm-kernel/a4f2cd76b9dc1833ee6c1cf325cba57def22231c.1740014950.git.nicolinc@nvidia.com/)
- **可移植点**：跨 prepare/compose 阶段保存稳定值，而不是保存生命周期不明确的 cookie 指针。
- **RISC-V 落点**：`drivers/iommu/riscv/`、`dma-iommu.c`、IMSIC MSI 地址翻译。
- **难度/阻塞**：中到高；依赖 RISC-V IOMMU MSI translation 集成。
- **证据**：补丁明确指出 cookie 指针必须跨两个分离阶段保持有效，但没有可靠的所有权约束。

### IRQ-6. resume 时从软件状态重建中断控制器

- **原始架构/子系统**：GICv3 ITS。
- **原始补丁**：[irqchip/gic-v3-its: Reconfigure ITS from software state on resume](https://lore.kernel.org/linux-arm-kernel/20260507183102.1897629-1-doebel@amazon.de/)
- **可移植点**：恢复寄存器/内存表地址不足以恢复控制器内部状态；resume 必须重放配置命令或从软件 shadow state 重建。
- **RISC-V 落点**：APLIC source/target state、IMSIC MSI identity/device routing、未来 RISC-V IOMMU interrupt translation。
- **难度/阻塞**：中；需确定哪些 AIA 状态在 suspend 后丢失。
- **证据**：ITS BASER 表仍在，但内部状态未恢复，导致 MSI-X 被静默丢弃。

### IRQ-7. LPI/IMSIC identity 释放与重新注册竞态

- **原始架构/子系统**：arm64 KVM VGIC/ITS。
- **原始补丁**：[KVM: arm64: vgic: Fix race between LPI release and re-registration](https://lore.kernel.org/linux-arm-kernel/20260709144225.3433646-3-clopez@suse.de/)
- **可移植点**：reference drop、索引删除和相同 interrupt ID 重新注册必须形成原子生命周期。
- **RISC-V 落点**：`arch/riscv/kvm/aia_imsic.c` 中 IMSIC identity/IRQ 对象索引与引用管理。
- **难度/阻塞**：中。
- **证据**：旧 LPI refcount 降零与另一 CPU 使用相同 INTID 注册并发，可造成 xarray 中新对象被旧释放路径删除。

### IRQ-8. interrupt affinity 迁移与 disable 并发

- **原始架构/子系统**：arm64 KVM VGIC。
- **原始补丁**：[KVM: arm64: Handle race between interrupt affinity change and LPI disabling](https://lore.kernel.org/linux-arm-kernel/20260615181625.3029352-1-maz@kernel.org/)
- **可移植点**：pending interrupt 迁移、目标 vCPU disable 和 active/pending list 修剪并发时必须持有稳定引用。
- **RISC-V 落点**：KVM AIA target hart/guest file 迁移、IMSIC pending identity 重定向。
- **难度/阻塞**：中到高；当前 AIA 加速路径需先具备迁移模型。
- **证据**：补丁描述可在释放锁窗口内释放 IRQ，随后重新访问形成 UAF。

### IRQ-9. 只读调试迭代不能污染全局中断状态

- **原始架构/子系统**：arm64 KVM VGIC debug。
- **原始补丁**：[KVM: arm64: Reimplement vgic-debug XArray iteration](https://lore.kernel.org/linux-arm-kernel/20260202085721.3954942-3-tabba@google.com/)
- **可移植点**：调试/迁移状态迭代应使用 RCU 和动态 iterator，不能通过 XArray mark 修改生产状态。
- **RISC-V 落点**：KVM AIA debug/state enumeration。
- **难度/阻塞**：低到中。
- **证据**：原实现用 mark 做 snapshot，迭代中止或失败会复杂化 refcount 并导致泄漏。

### IRQ-10. 通用 irqfd/VFIO/affinity/migration 压力测试

- **原始架构/子系统**：通用 KVM selftests，初始实现针对 x86。
- **原始补丁**：[Add an irqfd send+receive test](https://lore.kernel.org/linux-arm-kernel/20260626213534.3866178-8-seanjc@google.com/)、[Add VFIO device support](https://lore.kernel.org/linux-arm-kernel/20260626213534.3866178-10-seanjc@google.com/)、[Verify IRQ affinity changes](https://lore.kernel.org/linux-arm-kernel/20260626213534.3866178-12-seanjc@google.com/)、[Set empty routing between IRQs](https://lore.kernel.org/linux-arm-kernel/20260626213534.3866178-13-seanjc@google.com/)、[Verify vCPU migration](https://lore.kernel.org/linux-arm-kernel/20260626213534.3866178-19-seanjc@google.com/)
- **可移植点**：eventfd→irqfd→guest、VFIO IRQ bypass、host IRQ affinity、vCPU 迁移和 `CPUx→NULL→CPUy` 路由重建。
- **RISC-V 落点**：KVM AIA/APLIC/IMSIC irqfd selftest。
- **难度/阻塞**：中；基础 eventfd 路径可先做，VFIO bypass 依赖 IOMMU/AIA。
- **证据**：测试主体在 common code，补丁说明明确计划由其他架构复用。

### IRQ-11. AIA capability、最小中断和 no-irqchip smoke tests

- **原始架构/子系统**：arm64 KVM selftests。
- **原始补丁**：[Add helper to check for VGICv3 support](https://lore.kernel.org/linux-arm-kernel/20250917212044.294760-4-oliver.upton@linux.dev/)、[Create a VGICv3 for default VMs](https://lore.kernel.org/linux-arm-kernel/20250917212044.294760-6-oliver.upton@linux.dev/)、[Introduce a minimal GICv5 PPI selftest](https://lore.kernel.org/linux-arm-kernel/20260319154937.3619520-41-sascha.bischoff@arm.com/)、[Add no-vgic-v5 selftest](https://lore.kernel.org/linux-arm-kernel/20260319154937.3619520-42-sascha.bischoff@arm.com/)
- **可移植点**：统一 capability probe；测试创建 irqchip 后最小 guest interrupt；未创建 irqchip 时相关状态必须隐藏。
- **RISC-V 落点**：`kvm_supports_riscv_aia()`、IMSIC guest interrupt smoke test、no-AIA selftest。
- **难度/阻塞**：低到中。
- **证据**：能力 helper 通过 dummy VM test-create 探测；GICv5 测试明确验证最小单 vCPU 中断和无设备状态隔离。

### IRQ-12. per-vCPU direct interrupt 控制与用户态 MSI bypass

- **原始架构/子系统**：arm64 KVM GICv4/vLPI。
- **原始补丁**：[Add test for per-vCPU vLPI control API](https://lore.kernel.org/linux-arm-kernel/20251120140305.63515-14-mdittgen@amazon.de/)、[Ioctl to set up userspace-injected MSIs as software-bypassing vLPIs](https://lore.kernel.org/linux-arm-kernel/20251120140305.63515-12-mdittgen@amazon.de/)
- **可移植点**：per-vCPU 直注 enable/disable/query 的原子状态机、资源 ID 重用和软件注入/硬件 bypass 切换。
- **RISC-V 落点**：IMSIC HGEI/direct injection、per-vCPU guest interrupt file 管理。
- **难度/阻塞**：高；依赖 AIA 硬件直注、VFIO/irqbypass 和 HGEI 分配。
- **证据**：selftest 验证幂等、未初始化 vGIC、不同 vCPU 重用 vPEID 等边界条件。

### IRQ-13. LPI/IMSIC 压力测试的命令完成与目标编码

- **原始架构/子系统**：arm64 KVM selftests。
- **原始补丁**：[SYNC after guest ITS setup in vgic_lpi_stress](https://lore.kernel.org/linux-arm-kernel/20251119135744.68552-2-mdittgen@amazon.de/)、[fix ITS collection target addresses](https://lore.kernel.org/linux-arm-kernel/20251017161918.40711-1-mdittgen@amazon.de/)
- **可移植点**：控制器命令提交后必须等待完成；collection/target 不能用 vCPU 序号替代架构定义的目标地址。
- **RISC-V 落点**：APLIC target 配置、IMSIC guest index/hart index 编码和同步。
- **难度/阻塞**：中。
- **证据**：原测试在 MAPTI/MAPC 后没有完成保证，并错误地把 `[0,nr_cpus)` 整数直接作为 target address。

### IRQ-14. irqfd 注册与 waitqueue 生命周期系列

- **原始架构/子系统**：通用 KVM irqfd。
- **原始补丁**：[Use a local struct for initial vfs_poll](https://lore.kernel.org/linux-arm-kernel/20250522235223.3178519-2-seanjc@google.com/)、[Acquire SRCU outside irqfds.lock](https://lore.kernel.org/linux-arm-kernel/20250522235223.3178519-3-seanjc@google.com/)、[Initialize callback when adding to queue](https://lore.kernel.org/linux-arm-kernel/20250522235223.3178519-4-seanjc@google.com/)、[Add irqfd via vfs_poll callback](https://lore.kernel.org/linux-arm-kernel/20250522235223.3178519-5-seanjc@google.com/)、[Disallow binding multiple irqfds](https://lore.kernel.org/linux-arm-kernel/20250522235223.3178519-10-seanjc@google.com/)
- **可移植点**：waitqueue、KVM irqfd list、SRCU 和 irqfds lock 的注册顺序必须统一；一个 priority waiter 对应唯一 irqfd。
- **RISC-V 落点**：直接共享 `virt/kvm/eventfd.c`；AIA 后端只需验证回调假设。
- **难度/阻塞**：低。
- **证据**：系列逐步把状态初始化和 list 插入移动到实际注册临界区，并删除重复的事后检查。

### IRQ-15. irqfd 后端可覆盖分配和注入

- **原始架构/子系统**：通用 KVM irqfd。
- **原始补丁**：[Add architecture hooks for irqfd allocation and initialization](https://lore.kernel.org/linux-arm-kernel/20250424141341.841734-3-karim.manaouil@linaro.org/)、[Allow KVM backends to override IRQ injection](https://lore.kernel.org/linux-arm-kernel/20250424141341.841734-4-karim.manaouil@linaro.org/)
- **可移植点**：irqfd core 与架构注入载荷解耦，后端可携带架构状态或替换 `set_irq`。
- **RISC-V 落点**：KVM AIA irqfd 注入和未来硬件 bypass 后端。
- **难度/阻塞**：中；应避免无必要 weak hook，优先明确 ops。
- **证据**：系列用于支持非标准 hypervisor 注入机制，抽象本身不依赖 ARM。

### IRQ-16. IRQ routing/IRTE 更新传递完整新状态

- **原始架构/子系统**：arm64+x86 KVM/VFIO/irqbypass。
- **原始补丁**：[KVM: Pass new routing entries and irqfd when updating IRTEs](https://lore.kernel.org/linux-arm-kernel/20250611224604.313496-5-seanjc@google.com/)
- **可移植点**：路由变化回调必须拿到新 routing entries 和对应 irqfd，不能由后端再次从易变全局状态推导。
- **RISC-V 落点**：RISC-V IOMMU MSI translation、AIA IRQ bypass consumer。
- **难度/阻塞**：高；依赖完整的 IOMMU/AIA/VFIO 链路。
- **证据**：补丁目标是简化并强化 IRTE 更新，消除重复状态查询。

### IRQ-17. 硬件管理 pending state 的 irqchip 抽象

- **原始架构/子系统**：arm64 KVM GICv5。
- **原始补丁**：[Introduce set_pending_state() to irq_op](https://lore.kernel.org/linux-arm-kernel/20260703154811.3355680-29-sascha.bischoff@arm.com/)、[Add GICv5 SPI injection to irqfd](https://lore.kernel.org/linux-arm-kernel/20260703154811.3355680-32-sascha.bischoff@arm.com/)
- **可移植点**：允许 irqchip 后端把 pending 状态直接交给硬件，而不是强制使用软件 list/register 模型。
- **RISC-V 落点**：IMSIC pending identity、APLIC MSI mode、KVM irqfd 注入。
- **难度/阻塞**：高；需要硬件加速模式和软件模拟模式共存。
- **证据**：GICv5 的 SPI/LPI 生命周期部分由硬件管理，因此新增 pending-state op 并接入 irqfd。

### IRQ-18. 虚拟中断生命周期压力测试

- **原始架构/子系统**：arm64 KVM selftests。
- **原始补丁**：[Remove LR-bound limitation](https://lore.kernel.org/linux-arm-kernel/20251120172540.2267180-46-maz@kernel.org/)、[Add asymmetric SPI deactivation test](https://lore.kernel.org/linux-arm-kernel/20251120172540.2267180-48-maz@kernel.org/)
- **可移植点**：测试超出硬件 list-register 数量的中断、跨 vCPU deactivation、ack/EOI 顺序和 pending/active 生命周期。
- **RISC-V 落点**：KVM AIA IMSIC 多 identity 压力测试。
- **难度/阻塞**：中。
- **证据**：测试不再受 LR 数量限制，并刻意让一个 vCPU 激活、另一个 vCPU 执行 deactivation。

### IRQ-19. PMU IRQ affinity 与中断控制器拓扑一致

- **原始架构/子系统**：arm64 perf + genirq。
- **原始补丁**：[perf: arm_pmu: Request specific affinities for percpu NMI/IRQ](https://lore.kernel.org/linux-arm-kernel/20251020122944.3074811-19-maz@kernel.org/)
- **可移植点**：PMU 实例覆盖的 CPU/hart 集必须与 per-CPU IRQ 请求 affinity 一致。
- **RISC-V 落点**：`drivers/perf/riscv_pmu_sbi.c`、IMSIC PMU IRQ routing。
- **难度/阻塞**：中。
- **证据**：ARM PMU 驱动改为显式请求匹配 PMU affinity 的 NMI/IRQ。

## 3. Timer/Clocksource → RISC-V time/Sstc

### TIMER-1. 通用 timer selftest CPU pinning 与迁移

- **原始架构/子系统**：arm64 KVM selftests/common timer helpers。
- **原始补丁**：[Convert arch_timer tests to common helpers to pin task](https://lore.kernel.org/linux-arm-kernel/20250626001225.744268-6-seanjc@google.com/)、[fix thread migration in arch_timer_edge_cases](https://lore.kernel.org/linux-arm-kernel/20250605103613.14544-3-sebott@redhat.com/)
- **可移植点**：timer latency/edge 测试应显式绑核并正确遍历允许 affinity mask，避免 host 调度迁移污染结果。
- **RISC-V 落点**：`tools/testing/selftests/kvm/riscv/arch_timer.c`、Sstc/`vstimecmp`。
- **难度/阻塞**：低。
- **证据**：ARM 测试原先错误假设 CPU0 可用，并在修改 affinity 后使用已缩小的 mask 查找下一 CPU。

### TIMER-2. nested guest hypervisor timer 测试

- **原始架构/子系统**：arm64 KVM nested virtualization。
- **原始补丁**：[Enable hypervisor timer tests to run in vEL2](https://lore.kernel.org/linux-arm-kernel/20250512105251.577874-4-gankulkarni@os.amperecomputing.com/)
- **可移植点**：L1 hypervisor 运行时验证虚拟/物理 hypervisor timer 的注入、屏蔽和到期行为。
- **RISC-V 落点**：未来 nested H-extension、Sstc virtual timer delegation 测试。
- **难度/阻塞**：高；RISC-V nested KVM 基础能力尚不完整。
- **证据**：补丁把 HVTIMER/HPTIMER 测试带入 vEL2，并分别注入对应 timer IRQ。

### TIMER-3. 通用 VDSO 多 clock/辅助时钟框架

- **原始架构/子系统**：通用 time/VDSO + arm64 适配。
- **原始补丁**：[Rework vdso_time_data and introduce vdso_clock](https://lore.kernel.org/linux-arm-kernel/20250303-vdso-clock-v1-19-c1b5c69a166f@linutronix.de/)、[arm64/vdso: Prepare introduction of struct vdso_clock](https://lore.kernel.org/linux-arm-kernel/20250303-vdso-clock-v1-16-c1b5c69a166f@linutronix.de/)、[Update auxiliary clock data in datapage](https://lore.kernel.org/linux-arm-kernel/20250701-vdso-auxclock-v1-11-df7d9f87b9b8@linutronix.de/)
- **可移植点**：将 VDSO clock 数据按实例抽象，支持辅助/PTP clock 和 time namespace。
- **RISC-V 落点**：`arch/riscv/kernel/vdso/`、`arch/riscv/include/asm/vdso/`；大部分通用代码直接共享。
- **难度/阻塞**：低到中。
- **证据**：系列同时修改通用 VDSO、namespace 和 arm64 hook，RISC-V 使用同一 generic VDSO time 框架。

### TIMER-4. timer erratum 的 static-key 快路径

- **原始架构/子系统**：ARM architectural timer。
- **原始补丁**：[Add a static key indicating the need for a runtime workaround](https://lore.kernel.org/linux-arm-kernel/20260508094203.2913880-2-maz@kernel.org/)
- **可移植点**：把“是否存在任一 CPU 需要 workaround”变成 static key，正常系统的频繁 counter read 不承担 per-CPU workaround 检查成本。
- **RISC-V 落点**：`drivers/clocksource/timer-riscv.c`、RISC-V timer vendor errata/alternative。
- **难度/阻塞**：中。
- **证据**：补丁专门为 counter accessor 选择 runtime workaround 引入全局 static key。

## 4. PMU/perf → SBI PMU

### PMU-1. raw events 与 sampling 使用正向 capability

- **原始架构/子系统**：通用 perf core + ARM PMU。
- **原始补丁**：[perf: Introduce positive capability for raw events](https://lore.kernel.org/linux-arm-kernel/542787fd188ea15ef41c53d557989c962ed44771.1755096883.git.robin.murphy@arm.com/)、[perf: Introduce positive capability for sampling](https://lore.kernel.org/linux-arm-kernel/ae81cb65b38555c628e395cce67ac6c7eaafdd23.1755096883.git.robin.murphy@arm.com/)
- **可移植点**：PMU 明确 opt-in raw event/sampling，而不是根据 PMU 类型或负面例外推断。
- **RISC-V 落点**：`drivers/perf/riscv_pmu*.c`，直接采用 capability。
- **难度/阻塞**：低。
- **证据**：补丁指出系统/uncore PMU 数量增加后，旧的“默认 CPU PMU”假设已不成立。

### PMU-2. perf sched_task 回调上下文有效性

- **原始架构/子系统**：通用 perf core。
- **原始补丁**：[perf/core: Fix NULL pmu_ctx passed to PMU sched_task callback](https://lore.kernel.org/linux-arm-kernel/20260413185740.3286146-2-puranjay@kernel.org/)、[perf/core: Fix sched_task callbacks for CPU-wide branch stack events](https://lore.kernel.org/linux-arm-kernel/20260616155716.2631508-2-puranjay@kernel.org/)
- **可移植点**：CPU-wide event 即使没有 per-task context，也可能要求 PMU 在 sched-in/out 执行回调；不得传递 NULL context 或漏调用。
- **RISC-V 落点**：通用 `kernel/events/core.c`；未来 RISC-V branch trace PMU。
- **难度/阻塞**：低。
- **证据**：问题由 CPU-wide branch-stack event 触发，属于 perf core 调度模型而非 ARM 寄存器。

### PMU-3. guest 只看到可实际访问的 counters

- **原始架构/子系统**：arm64 KVM PMU。
- **原始补丁**：[KVM: arm64: Make guests see only counters they can access](https://lore.kernel.org/linux-arm-kernel/20250208020111.2068239-5-coltonlewis@google.com/)
- **可移植点**：guest 可见 counter 数量必须是宿主硬件、调度约束和 hypervisor 保留后的交集。
- **RISC-V 落点**：KVM SBI PMU、`vcpu_pmu.c`、`vcpu_sbi_pmu.c`。
- **难度/阻塞**：中。
- **证据**：ARM HPMN 限制低特权级可访问 counter，但旧实现仍报告硬件总数。

### PMU-4. 异构 PMU profile 与 fixed-counters-only

- **原始架构/子系统**：arm64 KVM PMU。
- **原始补丁**：[Introduce PMU_V3_COMPOSITION](https://lore.kernel.org/linux-arm-kernel/20250806-hybrid-v2-1-0661aec3af8c@rsg.ci.i.u-tokyo.ac.jp/)、[Test guest PMUv3 composition](https://lore.kernel.org/linux-arm-kernel/20250806-hybrid-v2-2-0661aec3af8c@rsg.ci.i.u-tokyo.ac.jp/)、[Introduce FIXED_COUNTERS_ONLY](https://lore.kernel.org/linux-arm-kernel/20260706-hybrid-v8-6-de459617b59d@rsg.ci.i.u-tokyo.ac.jp/)
- **可移植点**：VMM 可选择稳定 PMU profile；异构 CPU 不应向 guest 暴露无法在所有可调度 hart 上维持的 event/counter。
- **RISC-V 落点**：SBI PMU profile/capability、hart PMU 能力交集、vCPU 调度约束。
- **难度/阻塞**：高；可能需要新的 RISC-V KVM UAPI。
- **证据**：系列提供 composition attribute、selftest 和仅固定 counter 的降级模式。

### PMU-5. Partitioned/mediated PMU 生命周期

- **原始架构/子系统**：arm64 KVM + ARM PMUv3 + perf core。
- **原始补丁**：[Add perf_pmu_resched_update](https://lore.kernel.org/linux-arm-kernel/20260504211813.1804997-13-coltonlewis@google.com/)、[Detect overflows for Partitioned PMU](https://lore.kernel.org/linux-arm-kernel/20260504211813.1804997-17-coltonlewis@google.com/)、[Add Partitioned PMU selftest](https://lore.kernel.org/linux-arm-kernel/20260504211813.1804997-20-coltonlewis@google.com/)
- **可移植点**：host/guest counter 分区、动态 reservation、vCPU load 时重验 event filter、lazy context、guest overflow 归属判断。
- **RISC-V 落点**：SBI PMU mediated/direct assignment、`drivers/perf/riscv_pmu_sbi.c`、KVM vCPU PMU。
- **难度/阻塞**：高；需定义 counter ownership 与 guest PMI 注入。
- **证据**：系列跨 perf 和 KVM，处理 counter mask 冲突、调度更新、寄存器保存及溢出注入。

### PMU-6. 通用 guest perf context 和 exclude_guest

- **原始架构/子系统**：通用 perf/KVM。
- **原始补丁**：[perf: Add generic exclude_guest support](https://lore.kernel.org/linux-arm-kernel/20251206001720.468579-3-seanjc@google.com/)、[perf: Add a EVENT_GUEST flag](https://lore.kernel.org/linux-arm-kernel/20251206001720.468579-7-seanjc@google.com/)、[perf: Add APIs to load/put guest mediated PMU context](https://lore.kernel.org/linux-arm-kernel/20251206001720.468579-8-seanjc@google.com/)
- **可移植点**：由 KVM 在 guest enter/exit 切换 host/guest PMU ownership，而非让架构 PMU 猜测当前运行域。
- **RISC-V 落点**：通用 perf APIs + KVM RISC-V world switch。
- **难度/阻塞**：中到高。
- **证据**：补丁说明只有 KVM 准确知道 guest 进入/退出时刻，因此由 KVM 驱动 PMU context。

### PMU-7. PMU IRQ affinity

- **原始架构/子系统**：ARM PMU/genirq。
- **原始补丁**：[perf: arm_pmu: Request specific affinities for percpu NMI/IRQ](https://lore.kernel.org/linux-arm-kernel/20251020122944.3074811-19-maz@kernel.org/)
- **可移植点**：PMU interrupt routing 应与 PMU 覆盖的 CPU/hart mask 一致。
- **RISC-V 落点**：SBI PMU interrupt routing、IMSIC local interrupt。
- **难度/阻塞**：中。
- **证据**：ARM PMU 同时更新 NMI 和普通 IRQ 请求，明确传递 PMU affinity。

### PMU-8. AUX buffer 非连续页能力

- **原始架构/子系统**：通用 perf AUX。
- **原始补丁**：[Allow non-contiguous AUX buffer pages via PMU capability](https://lore.kernel.org/linux-arm-kernel/20250421215818.3800081-2-yabinc@google.com/)、[Allocate non-contiguous AUX pages by default](https://lore.kernel.org/linux-arm-kernel/20250508232642.148767-1-yabinc@google.com/)
- **可移植点**：PMU 显式声明是否要求物理连续 AUX buffer，避免无必要的大块连续内存分配。
- **RISC-V 落点**：未来 RISC-V trace/SPE-like PMU、通用 perf ring buffer。
- **难度/阻塞**：低；当前主要为未来能力。
- **证据**：ARM SPE/ETE 使用虚拟页，不需要连续页，旧默认会增加内存碎片。

### PMU-9. 交替采样周期与固定随机 jitter

- **原始架构/子系统**：通用 perf core。
- **原始补丁**：[Allow periodic events to alternate between two sample periods](https://lore.kernel.org/linux-arm-kernel/20250408171530.140858-3-mark.barnett@arm.com/)、[Allow adding fixed random jitter to the sampling period](https://lore.kernel.org/linux-arm-kernel/20250408171530.140858-4-mark.barnett@arm.com/)
- **可移植点**：采样周期变化在 perf core 中实现，不依赖 ARM PMU；可降低同步采样偏差。
- **RISC-V 落点**：直接共享 `kernel/events/core.c` 和 perf UAPI。
- **难度/阻塞**：低。
- **证据**：补丁修改通用 overflow handling 和 `perf_event_attr`。

## 5. KVM/虚拟化 → KVM RISC-V

### KVM-1. 通用 memory fault 结构与 userfault exits

- **原始架构/子系统**：arm64+x86+通用 KVM。
- **原始补丁**：[Require struct kvm_page_fault for memory fault exits](https://lore.kernel.org/linux-arm-kernel/20250618042424.330664-4-jthoughton@google.com/)、[Add common infrastructure for KVM Userfaults](https://lore.kernel.org/linux-arm-kernel/20250618042424.330664-5-jthoughton@google.com/)、[arm64 support for KVM userfault exits](https://lore.kernel.org/linux-arm-kernel/20250618042424.330664-7-jthoughton@google.com/)
- **可移植点**：统一 fault 描述、memslot bitmap、userspace fault exit 和 retry 语义。
- **RISC-V 落点**：`arch/riscv/kvm/mmu.c`、`gstage.c`、`virt/kvm/kvm_main.c`。
- **难度/阻塞**：中。
- **证据**：common helper 已建立，arm64/x86 使用共同基础字段；RISC-V 需实现 arch fault 转换。

### KVM-2. guest_memfd backing、host mmap 与 arm64 fault

- **原始架构/子系统**：arm64+通用 KVM。
- **原始补丁**：[Handle guest_memfd-backed guest page faults](https://lore.kernel.org/linux-arm-kernel/20250729225455.670324-19-seanjc@google.com/)、[Enable guest_memfd backed memory](https://lore.kernel.org/linux-arm-kernel/20250729225455.670324-21-seanjc@google.com/)、[Allow host mmap on guest_memfd files](https://lore.kernel.org/linux-arm-kernel/20250729225455.670324-22-seanjc@google.com/)
- **可移植点**：无 `userspace_addr` 的 gmem memslot、host mmap capability、fault 时直接从 gmem 获取 folio。
- **RISC-V 落点**：G-stage fault、memslot validation、`virt/kvm/guest_memfd.c`。
- **难度/阻塞**：高；需明确 shared/private、dirty log 和大页语义。
- **证据**：系列完成 core mmap plumbing 和 arm64 page-fault/backing 接入。

### KVM-3. KVM_PRE_FAULT_MEMORY

- **原始架构/子系统**：arm64 KVM + common selftest。
- **原始补丁**：[Add pre_fault_memory implementation](https://lore.kernel.org/linux-arm-kernel/20260612162354.73378-3-jackabt.amazon@gmail.com/)、[Enable pre_fault_memory_test for arm64](https://lore.kernel.org/linux-arm-kernel/20260612162354.73378-4-jackabt.amazon@gmail.com/)
- **可移植点**：通过既有 stage-2 fault handler 预建映射；切回 canonical stage-2；测试支持不同 guest page size 和 exit reason。
- **RISC-V 落点**：`arch/riscv/kvm/mmu.c`、`gstage.c`、common pre-fault selftest。
- **难度/阻塞**：中。
- **证据**：arm64 通过合成 read data abort 复用 fault path，并处理 nested/shadow MMU 状态。

### KVM-4. 大 VM stage-2 销毁期间可调度

- **原始架构/子系统**：arm64 KVM stage-2 MMU。
- **原始补丁**：[Reschedule as needed when destroying the stage-2 page-tables](https://lore.kernel.org/linux-arm-kernel/20251113052452.975081-4-rananta@google.com/)
- **可移植点**：页表递归释放应拆分为可恢复 walker，并在不破坏引用和锁序时调用调度点。
- **RISC-V 落点**：`arch/riscv/kvm/gstage.c` VM teardown。
- **难度/阻塞**：中。
- **证据**：系列先拆分 destroy walker，再周期性 reschedule，解决大 VM teardown 长时间占用 CPU。

### KVM-5. fault 错误路径 page/PFN 引用释放

- **原始架构/子系统**：arm64 KVM MMU。
- **原始补丁**：[Fix page leak in user_mem_abort](https://lore.kernel.org/linux-arm-kernel/20250917130737.2139403-1-tabba@google.com/)、[Fix page leak on atomic fault](https://lore.kernel.org/linux-arm-kernel/20260304162222.836152-2-tabba@google.com/)、[Handle permission faults with guest_memfd](https://lore.kernel.org/linux-arm-kernel/20260505094913.75317-1-alexandru.elisei@arm.com/)
- **可移植点**：faultin 成功后的所有 early return 必须释放 PFN/page；permission-only update 与新映射必须区分。
- **RISC-V 落点**：G-stage fault handler、guest_memfd fault、atomic/attribute fault。
- **难度/阻塞**：中。
- **证据**：两个独立泄漏均源于 faultin 后 early return；恶意 guest 可反复触发导致 host OOM。

### KVM-6. guest_memfd-only dirty log 与 MMU notifier 边界

- **原始架构/子系统**：通用 KVM + arm64。
- **原始补丁**：[Ignore MMU notifiers for guest_memfd-only memslots](https://lore.kernel.org/linux-arm-kernel/20260625130902.258331-1-alexandru.elisei@arm.com/)、[Implement dirty logging for guest_memfd-only memslots](https://lore.kernel.org/linux-arm-kernel/20260702142912.6395-3-alexandru.elisei@arm.com/)
- **可移植点**：gmem-only memslot 不依赖 userspace page tables，因此不应响应 MMU notifier；dirty logging 需以 gmem folio/mapping 为真值。
- **RISC-V 落点**：RISC-V guest_memfd memslot、G-stage dirty log。
- **难度/阻塞**：高。
- **证据**：补丁说明 secondary MMU 直接从 guest_memfd 获取 folio，与 userspace page tables 无关系。

### KVM-7. 硬件 dirty bitmap/ring 清理通用 hook

- **原始架构/子系统**：通用 KVM + arm64 HACDBS。
- **原始补丁**：[arch-generic dirty-bitmap cleaning interface](https://lore.kernel.org/linux-arm-kernel/20260629111820.1873540-8-leo.bras@arm.com/)、[arch-generic dirty-ring cleaning interface](https://lore.kernel.org/linux-arm-kernel/20260629111820.1873540-12-leo.bras@arm.com/)
- **可移植点**：架构硬件批量清 dirty 失败时必须保留未处理项并回退软件路径。
- **RISC-V 落点**：未来 RISC-V hardware dirty tracking、G-stage A/D bit 批处理。
- **难度/阻塞**：高；当前缺少与 HACDBS 等价机制。
- **证据**：两个 hook 都规定 arch 返回错误后由通用软件清理完成剩余工作。

### KVM-8. userspace exit completion 显式 ABI

- **原始架构/子系统**：通用 KVM。
- **原始补丁**：[Add common kvm_run flag for exit completion](https://lore.kernel.org/linux-arm-kernel/20250111012450.1262638-4-seanjc@google.com/)、[Selftests rely on KVM_RUN_NEEDS_COMPLETION](https://lore.kernel.org/linux-arm-kernel/20250111012450.1262638-6-seanjc@google.com/)
- **可移植点**：userspace 不应按 exit 类型硬编码是否需要再次 `KVM_RUN`，由内核显式标记。
- **RISC-V 落点**：SBI/MMIO/userspace exit、save/restore。
- **难度/阻塞**：低。
- **证据**：补丁指出依赖文档注释极易遗漏，且已有开发者新增 exit 后忘记实现 completion。

### KVM-9. VM/vCPU binary stats selftest 基础设施

- **原始架构/子系统**：通用 KVM selftests。
- **原始补丁**：[Add binary stats cache helpers](https://lore.kernel.org/linux-arm-kernel/20250111005049.1247555-6-seanjc@google.com/)、[Add infrastructure for vCPU binary stats](https://lore.kernel.org/linux-arm-kernel/20250111005049.1247555-9-seanjc@google.com/)
- **可移植点**：统一 VM/vCPU stats FD 生命周期、缓存、关闭和资源限制计算。
- **RISC-V 落点**：测试 exits、WFI、SBI、AIA 和 G-stage 统计。
- **难度/阻塞**：低。
- **证据**：系列修复 FD=0 泄漏、VM recreate 后旧 stats FD，并扩展到 vCPU scope。

### KVM-10. kvm->buses[] SRCU 发布/观察屏障

- **原始架构/子系统**：通用 KVM，x86 触发。
- **原始补丁**：[Implement barriers before accessing kvm->buses[] on SRCU read paths](https://lore.kernel.org/linux-arm-kernel/20250909100007.3136249-4-keirf@google.com/)
- **可移植点**：vCPU 已观察到 I/O registration 后，当前 trapped/emulated instruction 必须同步观察对应 bus registration。
- **RISC-V 落点**：RISC-V MMIO/SBI device bus 查找，直接共享 core 修复。
- **难度/阻塞**：低。
- **证据**：补丁同时限制 update-side helper，防止 SRCU reader 获取长期 bus reference。

### KVM-11. VM dead 与 VM bugged 状态分离

- **原始架构/子系统**：通用 KVM + arm64 VGIC。
- **原始补丁**：[Reject ioctls only if the VM is bugged, not simply marked dead](https://lore.kernel.org/linux-arm-kernel/20250729193341.621487-4-seanjc@google.com/)
- **可移植点**：正常终止 VM 与检测到内核/KVM 不一致是不同状态；终止后仍可允许安全的管理 ioctl。
- **RISC-V 落点**：通用 KVM VM lifecycle、AIA device teardown。
- **难度/阻塞**：低。
- **证据**：补丁删除无读取者的 `vm_dead`，仅保留阻止 vCPU 重入的 request 和 bugged 状态。

### KVM-12. shared/private MMU notifier 目标范围

- **原始架构/子系统**：通用 KVM/private memory。
- **原始补丁**：[Prepare for handling only shared mappings in mmu_notifier events](https://lore.kernel.org/linux-arm-kernel/20250213161426.102987-2-steven.price@arm.com/)
- **可移植点**：MMU notifier 只覆盖由 userspace VA 支撑的 shared mappings；private mappings 必须通过独立生命周期处理。
- **RISC-V 落点**：未来 CoVE/private memory、guest_memfd、G-stage invalidation。
- **难度/阻塞**：高。
- **证据**：补丁为 `kvm_gfn_range` 增加 shared/private target flags，避免 tri-state 和错误 invalidation。

### KVM-13. hypervisor vCPU 初始化 pin 清理与发布顺序

- **原始架构/子系统**：arm64 pKVM。
- **原始补丁**：[Fix pin leak and publication ordering in __pkvm_init_vcpu](https://lore.kernel.org/linux-arm-kernel/20260424084908.370776-6-tabba@google.com/)
- **可移植点**：共享页 pin 成功后的所有失败路径必须 unpin；对象必须完全初始化后再发布给并发读者。
- **RISC-V 落点**：未来 RISC-V CoVE/隔离 hypervisor vCPU registration。
- **难度/阻塞**：高。
- **证据**：补丁修复 host vCPU/SVE state 永久 pin 泄漏，并抽出检查后发布 helper。

### KVM-14. lazy vCPU state sync

- **原始架构/子系统**：arm64 pKVM。
- **原始补丁**：[Implement lazy vCPU state sync for non-protected guests](https://lore.kernel.org/linux-arm-kernel/20260706095927.560795-9-fuad.tabba@linux.dev/)
- **可移植点**：host/hypervisor vCPU state 使用 dirty/valid 状态机，只在 host 实际读取或修改时同步。
- **RISC-V 落点**：KVM RISC-V SBI/nested/CoVE world switch。
- **难度/阻塞**：中到高。
- **证据**：补丁避免每次 world switch 无条件复制寄存器上下文，并提供显式 sync hypercall。

### KVM-15. stage-2 TLB invalidation level 传播

- **原始架构/子系统**：arm64 KVM page table。
- **原始补丁**：[Fix propagation of TLBI level in kvm_pgtable_stage2_relax_perms](https://lore.kernel.org/linux-arm-kernel/20260707162935.1900874-1-maz@kernel.org/)
- **可移植点**：页表权限更新必须把真实 leaf level 或“未知”状态无损传给 TLB flush，避免窄类型截断 sentinel。
- **RISC-V 落点**：G-stage `HFENCE.GVMA` 范围/层级选择。
- **难度/阻塞**：中。
- **证据**：ARM 代码将 32-bit `TLBI_TTL_UNKNOWN` 写入 `s8` level，导致未知值传播不可靠。

### KVM-16. guest_memfd inode、NUMA policy 与实例生命周期

- **原始架构/子系统**：通用 KVM guest_memfd。
- **原始补丁**：[Use guest mem inodes instead of anonymous inodes](https://lore.kernel.org/linux-arm-kernel/20251016172853.52451-4-seanjc@google.com/)、[Enforce NUMA mempolicy using shared policy](https://lore.kernel.org/linux-arm-kernel/20251016172853.52451-6-seanjc@google.com/)
- **可移植点**：区分 guest memory inode 与单个 VM/file view；通过 shared policy 使 `mbind()` 等 NUMA policy 对 gmem allocation 生效。
- **RISC-V 落点**：直接共享 `virt/kvm/guest_memfd.c`，支持大型 RISC-V VM/NUMA。
- **难度/阻塞**：低到中；依赖 RISC-V 启用 guest_memfd。
- **证据**：系列将 instance 元数据移入专用 inode，并修复无 process policy 时任意 NUMA node 分配问题。

## 6. 优先实施建议

### 第一批：可直接共享或测试先行

1. IRQ-2、IRQ-3、IRQ-4、IRQ-14：genirq/MSI/irqfd 通用生命周期。
2. IRQ-10、IRQ-11、IRQ-18：AIA smoke、irqfd 和虚拟中断压力测试。
3. TIMER-1、TIMER-3：Sstc 测试绑核和 VDSO clock 框架。
4. PMU-1、PMU-2、PMU-9：通用 perf capability、调度回调和采样逻辑。
5. KVM-8、KVM-9、KVM-10、KVM-11：通用 exit、stats、SRCU 和 VM lifecycle。

### 第二批：明确的架构映射

1. IRQ-6 至 IRQ-9：IMSIC/APLIC 状态恢复、identity 生命周期和 affinity 并发。
2. TIMER-4：RISC-V timer erratum static-key 路径。
3. PMU-3、PMU-4：SBI PMU counter 可见性和异构 profile。
4. KVM-1、KVM-3 至 KVM-5、KVM-15：G-stage fault、pre-fault、teardown、HFENCE。

### 第三批：依赖基础设施

1. IRQ-5、IRQ-12、IRQ-16、IRQ-17：RISC-V IOMMU MSI、HGEI/direct injection 和 irqbypass。
2. PMU-5、PMU-6：mediated/partitioned SBI PMU。
3. KVM-2、KVM-6、KVM-7、KVM-12 至 KVM-14：guest_memfd、private memory、硬件 dirty tracking 和隔离 hypervisor。

## 7. 结论

- 最终候选贡献点：**48**。
- 直接共享或低难度：约 18 项。
- 需要按 AIA/Sstc/SBI PMU/G-stage 重写：约 19 项。
- 依赖 RISC-V IOMMU、AIA 直注、guest_memfd/private memory 或 mediated PMU：约 11 项。
- 最优先的上游切入点是：**KVM irqfd/AIA selftests、IMSIC identity 生命周期、Sstc 测试稳定性、SBI PMU counter 可见性、G-stage pre-fault 与 teardown 调度点**。
