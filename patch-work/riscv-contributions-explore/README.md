# linux-arm-kernel 补丁中的 RISC-V 贡献机会研究指南

本目录从 `linux-arm-kernel` 邮件列表的 2025-01-01 至 2026-07-10 补丁中，系统探索可以直接共享、重新实现或借鉴到 RISC-V 的贡献机会。

研究覆盖 65,635 封唯一补丁邮件和 29,534 个逻辑补丁谱系，最终整理出 168 个独立贡献点，并保留 227 个原始补丁链接。

## 从哪里开始

| 你的目标 | 建议入口 |
|---|---|
| 了解研究结论、方法和全部候选 | [总报告](REPORT.zh-CN.md) |
| 快速浏览 168 个候选表格 | [候选汇总](analysis/curated_candidates.md) |
| 只看内存、页表、TLB 和 IOMMU | [MMU 与内存审计](analysis/audit_mmu_memory.md) |
| 只看 IRQ、Timer、PMU 和 KVM | [IRQ、Timer、PMU 与 KVM 审计](analysis/audit_irq_timer_pmu.md) |
| 只看 PCI、DMA、固件和平台驱动 | [驱动与平台审计](analysis/audit_drivers_platform.md) |
| 只看 tracing、livepatch 和 hardening | [核心与工具链审计](analysis/audit_core_tooling.md) |

## 文档地图

| 文档 | 内容 |
|---|---|
| [REPORT.zh-CN.md](REPORT.zh-CN.md) | 总结数据范围、研究方法、建议工作包和全部 168 个贡献点，是本目录的主入口。 |
| [analysis/curated_candidates.md](analysis/curated_candidates.md) | 以紧凑表格汇总全部候选，适合按优先级、年份、来源域、原始架构和阻塞条件快速检索。 |
| [analysis/audit_mmu_memory.md](analysis/audit_mmu_memory.md) | 深入分析 MMU、页表生命周期、TLB、ASID、内存热插拔、DMA、IOMMU、SVA、IOPF 和机密内存，共 45 个贡献点。 |
| [analysis/audit_irq_timer_pmu.md](analysis/audit_irq_timer_pmu.md) | 深入分析 AIA/APLIC/IMSIC、MSI、irqfd、timer、Sstc、SBI PMU 和 KVM，共 48 个原始审计点。总报告合并跨领域重复项后使用 47 个。 |
| [analysis/audit_drivers_platform.md](analysis/audit_drivers_platform.md) | 深入分析 PCI/PCIe、ACPI、EFI、SCMI、电源管理、DMA、通用驱动框架和平台抽象，共 62 个贡献点。 |
| [analysis/audit_core_tooling.md](analysis/audit_core_tooling.md) | 深入分析 livepatch、可靠栈回溯、SFrame、ftrace、BPF、kprobes、动态文本修改、vDSO、LTO 和 Rust 内存访问，共 16 个贡献点。 |

## 推荐阅读路线

### 快速寻找可做事项

1. 阅读[总报告的结论摘要和建议工作包](REPORT.zh-CN.md#结论摘要)。
2. 在[候选汇总](analysis/curated_candidates.md)中优先筛选 `P0`。
3. 根据来源域进入对应审计文档，查看原始补丁、RISC-V 落点、难度和阻塞。

### 按现有经验选方向

- 熟悉内存管理、页表或 IOMMU：从[MMU 与内存审计](analysis/audit_mmu_memory.md)开始。
- 熟悉中断、定时器、性能计数器或虚拟化：从[IRQ、Timer、PMU 与 KVM 审计](analysis/audit_irq_timer_pmu.md)开始。
- 熟悉 SoC、PCIe、DMA、ACPI 或固件：从[驱动与平台审计](analysis/audit_drivers_platform.md)开始。
- 熟悉 tracing、BPF、livepatch 或内核安全：从[核心与工具链审计](analysis/audit_core_tooling.md)开始。

### 从原始补丁形成 RISC-V 系列

1. 阅读候选的“原始架构/子系统”，区分通用补丁、arm64 实现和特定 ARM 硬件驱动。
2. 打开原始补丁链接，确认系列版本、评审意见和最新状态。
3. 对照“RISC-V 落点”，在当前 mainline 或 linux-next 中确认接口和源码仍然一致。
4. 将可复用的不变量与 ARM 专属实现分开，避免机械复制寄存器、异常模型或固件假设。
5. 根据“难度/阻塞”准备硬件、固件、模拟器、自测或跨架构回归环境。

## 优先级含义

- `P0`：通用框架已经具备，或 RISC-V 有明确接入点，适合近期实现、补测试或参与现有系列。
- `P1`：价值明确，但依赖具体平台、硬件能力、固件描述或多个子系统协作。
- `P2`：长期能力、前置基础设施或当前缺少明确硬件需求的方向。

## 与架构接口差距研究的区别

本目录采用“从补丁邮件发现机会”的方法，适合跟踪近期上游变化和从 ARM 社区迁移经验。

相邻的 [`riscv-arm-x86-gap`](../riscv-arm-x86-gap/README.md) 采用“比较 RISC-V、arm64、x86 架构接口”的方法，更适合系统识别缺失能力、通用化接口和长期路线。两个目录存在主题交叉，但候选形成方法和编号体系不同。

## 使用边界

- “来自 ARM 邮件列表”不代表补丁只属于 ARM。大量候选修改的是通用内核、驱动框架或跨架构 API。
- “可移植”可能表示直接共享、按 RISC-V 语义重新实现，或仅在采用相同硬件 IP、固件协议的平台上适用。
- 邮件状态会变化，投稿前应重新确认最新版本、maintainer tree、linux-next 和 mainline。
- 本目录保留的是探索性文档，不包含原始邮件归档、脚本、CSV、JSONL 或内核代码修改。
