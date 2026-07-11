# KVM x86/arm 补丁到 RISC-V 的可移植性研究指南

本目录整理基于 KVM Patchwork 与 lore 邮件数据的 RISC-V 可移植性研究，覆盖 2025 全年和 2026 年上半年。

研究目标是从 x86、arm64、mixed x86/arm 和 shared KVM 补丁中筛选可迁移到 RISC-V 的贡献点，标注原始架构、移植落点、优先级、阻塞条件和原始补丁链接。

## 从哪里开始

| 你的目标 | 建议入口 |
|---|---|
| 先看跨年度合并结论 | [综合梳理](00-portability-overview.zh-CN.md) |
| 只看 2026H1 研究 | [2026H1 KVM 报告](01-kvm-2026h1-report.zh-CN.md) |
| 只看 2025 全年研究 | [2025 KVM 报告](02-kvm-2025-report.zh-CN.md) |
| 快速浏览 2026H1 精选候选 | [2026H1 精选候选](analysis/kvm-2026h1-curated-candidates.md) |
| 快速浏览 2025 精选候选 | [2025 精选候选](analysis/kvm-2025-curated-candidates.md) |

## 文档地图

| 文档 | 内容 |
|---|---|
| [00-portability-overview.zh-CN.md](00-portability-overview.zh-CN.md) | 合并 2025 与 2026H1 结果，去重跨年度修订，按阶段给出推荐实施路线和全部候选。 |
| [01-kvm-2026h1-report.zh-CN.md](01-kvm-2026h1-report.zh-CN.md) | 2026 年上半年 KVM Patchwork/lore 对账、评分方法、近期候选、中期候选和前置依赖候选。 |
| [02-kvm-2025-report.zh-CN.md](02-kvm-2025-report.zh-CN.md) | 2025 全年 KVM 补丁清单、架构分布、评分、T1/T2/T3 候选和推荐实施顺序。 |
| [analysis/kvm-2026h1-curated-candidates.md](analysis/kvm-2026h1-curated-candidates.md) | 2026H1 精选候选表，适合按原始架构、RISC-V 落点、阻塞条件和补丁链接快速检索。 |
| [analysis/kvm-2025-curated-candidates.md](analysis/kvm-2025-curated-candidates.md) | 2025 精选候选表，适合回溯全年候选和跨年度替代关系。 |

## 推荐阅读路线

### 快速找近期可做项

1. 阅读[综合梳理](00-portability-overview.zh-CN.md)的“推荐实施路线”。
2. 优先看 `T1：近期可实施` 候选。
3. 进入对应年份的精选候选表，核对原始补丁、RISC-V 落点和阻塞条件。

### 按 KVM 子系统深入

- G-stage、memslot、huge-leaf、prefault：优先看综合梳理第二阶段和年度报告中的 MMU/memory 候选。
- AIA、APLIC、IMSIC、irqfd：优先看综合梳理第三阶段和 selftests/irqfd 候选。
- SBI PMU、timer、steal-time：优先看综合梳理第四阶段。
- guest_memfd、memory attributes、私有内存：优先看综合梳理第五阶段。

### 准备实际投稿

1. 先确认候选原始架构：x86、arm64、mixed x86/arm 或 shared KVM。
2. 重新打开原始 Patchwork 链接，确认是否已有新版本、已合并或被替代。
3. 判断可移植类型：直接复用 selftest/helper、按 RISC-V 重写架构实现、或等待基础设施成熟。
4. 对照 RISC-V 当前 mainline/linux-next，确认 KVM、AIA、SBI PMU、guest_memfd 或 IOMMU 依赖是否已经具备。
5. 将首版补丁控制在单一机制或单一 selftest，避免把 x86/arm64 专属寄存器语义机械搬到 RISC-V。

## 优先级和分层含义

- `T1-near-term`：近期可实施，多为 selftests、正确性审计、接口接入或低风险行为修复。
- `T2-architecture-rewrite`：需要按 RISC-V G-stage、AIA、SBI PMU、timer 或 guest memory 模型重新实现。
- `T3-foundation-dependent`：依赖 guest_memfd、memory attributes、private memory、IOMMU/VFIO IRQ bypass、mediated PMU 等基础能力。
- `A-shared/B-high/C-medium/D-low/E-none`：年度报告中的自动/人工评分结果，具体定义见对应年度报告的评分方法。

## 使用边界

- 本目录只保留人类可读 Markdown 文档，不包含原始 Patchwork/lore 数据、CSV/JSONL、脚本、缓存或内核源码树。
- “可移植”不等于可直接复制原架构代码。x86 TDP MMU、arm64 stage-2、GIC/vGIC、PMUv3、TSC/PV clock 等机制均需要转换为 RISC-V 对应语义。
- Patchwork 状态会变化，投稿前必须重新核查最新系列和 maintainer tree。
