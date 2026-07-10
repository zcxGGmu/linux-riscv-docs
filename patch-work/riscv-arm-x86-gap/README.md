# RISC-V、arm64 与 x86 架构接口差距研究指南

本目录研究 RISC-V 相对 arm64、x86 已有架构接口的能力差距，以及可将多架构重复实现下沉到通用内核的贡献机会。

研究固定在指定的 mainline、linux-next 基线和 2025-2026 补丁讨论上，最终整理出 90 个候选贡献点。每个候选均包含原始架构、源码位置、差距说明、建议补丁边界、阻塞条件、验证方法和上游来源。

## 从哪里开始

| 你的目标 | 建议入口 |
|---|---|
| 用几分钟了解主要结论 | [执行摘要](00-executive-summary.md) |
| 浏览全部 90 个候选并按领域筛选 | [统一清单](02-interface-gap-inventory.md) |
| 寻找近期可以启动的补丁 | [贡献路线图](09-ranked-contribution-roadmap.md) |
| 理解候选如何产生、评分和去重 | [研究方法与固定基线](01-methodology-and-baselines.md) |
| 核查源码、邮件和原始补丁 | [源码与邮件来源索引](10-source-and-mail-index.md) |
| 深入某个技术领域 | 阅读下方对应的领域报告 |

## 文档地图

### 总览与方法

| 文档 | 内容 |
|---|---|
| [00-executive-summary.md](00-executive-summary.md) | 汇总结论、统计、P0 候选和推荐推进顺序，适合作为首篇阅读。 |
| [01-methodology-and-baselines.md](01-methodology-and-baselines.md) | 说明固定源码基线、邮件时间范围、G 分类、优先级、状态定义、证据要求和研究限制。 |
| [02-interface-gap-inventory.md](02-interface-gap-inventory.md) | 统一列出 90 个候选，可按领域、优先级、状态和原始架构快速定位，并跳转到完整候选卡。 |

### 领域报告

| 文档 | 内容 |
|---|---|
| [03-mmu-memory-tlb.md](03-mmu-memory-tlb.md) | MMU、页表、TLB、ASID、内存热插拔、DMA cache 同步和映射属性，共 16 个候选。 |
| [04-irq-smp-time.md](04-irq-smp-time.md) | IRQ、IPI、SMP、IMSIC、CPU hotplug、clockevent 和 clocksource，共 10 个候选。 |
| [05-core-abi-observability-hardening.md](05-core-abi-observability-hardening.md) | unwinder、livepatch、ftrace、BPF、kprobes、原子操作、KCSAN 和内核安全加固，共 18 个候选。 |
| [06-platform-acpi-numa-power-ras.md](06-platform-acpi-numa-power-ras.md) | ACPI、NUMA、CPU hotplug、功耗管理、RAS、kexec 和固件接口，共 13 个候选。 |
| [07-kvm-iommu-virtualization.md](07-kvm-iommu-virtualization.md) | KVM、guest_memfd、prefault、VFIO、RISC-V IOMMU、nested virtualization 和 CoVE，共 15 个候选。 |
| [08-genericization-opportunities.md](08-genericization-opportunities.md) | helper 下沉、generic default、能力门控和跨架构共享状态机，共 18 个通用化候选。 |

### 行动与证据

| 文档 | 内容 |
|---|---|
| [09-ranked-contribution-roadmap.md](09-ranked-contribution-roadmap.md) | 按近期、中期和基础设施阶段排序候选，并为 P0 项给出首个可提交单元。 |
| [10-source-and-mail-index.md](10-source-and-mail-index.md) | 为每个候选集中列出固定源码、原始架构实现、邮件讨论和补丁链接。 |

## 推荐阅读路线

### 快速决策

1. 阅读[执行摘要](00-executive-summary.md)，了解候选规模和优先级分布。
2. 打开[贡献路线图](09-ranked-contribution-roadmap.md)，查看 P0 项和首个可提交单元。
3. 从候选编号跳转到领域报告，核对阻塞条件和验证要求。

### 按子系统深入

1. 在[统一清单](02-interface-gap-inventory.md)中选择领域。
2. 阅读对应领域报告的总表、完整候选卡、依赖关系和测试矩阵。
3. 在[来源索引](10-source-and-mail-index.md)中检查原始实现和讨论状态。

### 准备实际投稿

1. 优先选择状态为 `unclaimed`、范围较小且验证条件可获得的候选。
2. 使用候选卡中的“第一版补丁系列边界”控制首版规模。
3. 开工前重新检查 mainline、linux-next 和邮件列表，确认没有更新版本或并行工作。
4. 按候选卡列出的验证矩阵准备编译、启动、自测、压力测试或硬件测试证据。
5. 根据维护者路由发送到对应子系统列表，并抄送 linux-riscv。

## 如何理解候选标记

- `P0`：近期价值和可执行性最高，通常已有清晰接口、落点和验证路径。
- `P1`：适合中期推进，可能需要先完成依赖、硬件验证或跨子系统协调。
- `P2`：长期方向或基础设施项目，当前阻塞较多。
- `G0/G1`：直接共享、直接启用或较明确的 RISC-V 接入。
- `G2`：适合下沉到 generic core 的重复实现。
- `G3/G4`：需要 RISC-V 架构实现、语义证明或较大范围的基础设施工作。

完整定义以[研究方法与固定基线](01-methodology-and-baselines.md)为准。

## 使用边界

- 优先级是工程调研结论，不代表维护者已经接受该方向。
- 邮件系列、maintainer tree 和 linux-next 状态会持续变化，开工前必须重新核查。
- 标记为可移植不等于可以逐行复制 arm64 或 x86 实现。涉及内存模型、TLB、中断、虚拟化和固件 ABI 时，应按 RISC-V 规范重新证明语义。
- 本目录是贡献路线图，不包含内核代码实现或硬件验证结果。
