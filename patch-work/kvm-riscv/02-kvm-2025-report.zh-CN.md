# KVM 2025 x86/arm 补丁向 RISC-V 移植可行性分析

## 结论摘要

本报告覆盖 Patchwork KVM 项目在 **2025-01-01（含）至
2026-01-01（不含）** 的全部记录，并以 Patchwork 清单作为权威范围，
lore KVM 邮件仓库用于恢复补丁正文、diff 路径和版本谱系。

主要结果：

- Patchwork 权威记录：**12,817** 条，覆盖 **129** 个 API 页面。
- lore 原始 diff 邮件：**12,332** 条。
- 最终 x86/arm/shared 权威补丁版本：**5,318** 条。
- 逻辑补丁谱系：**2,856** 个。
- 自动评分中的最新 B/C 候选谱系：**427** 个。
- 人工审计后的重点候选：**36** 条。
  - T1 近期可实施：**13**
  - T2 需要架构重写：**14**
  - T3 依赖基础能力：**9**
- 36 条重点候选的原始架构：
  - x86：**20**
  - arm64：**14**
  - mixed-x86-arm：**2**
- 其中 **3** 条在 2026 年出现了后续修订版本，实施时应优先参考新版。

总体判断：

1. **最适合近期推进的是 selftests、AIA 测试、stage-2 页表释放和通用
   KVM 测试基础设施。**
2. **guest_memfd、userfault、private memory 和 memory attributes**
   具有较高长期价值，但依赖 RISC-V KVM 尚未具备的基础能力。
3. ARM GIC/VGIC 和 x86 APIC/SAVIC 补丁不能直接复制，但大量中断注入、
   迁移、WFI 唤醒和属性冻结测试方法可重写为 APLIC/IMSIC 测试。
4. x86/arm PMU 与 timer 的寄存器 ABI 不可移植，但基于 perf 的计数器
   生命周期、硬件能力过滤、suspend 连续性和测试容差值得迁移。
5. TDX、SEV-SNP、VMX/SVM nested 和架构寄存器类补丁数量很大，但对
   当前 RISC-V KVM 的直接移植价值较低。

## 范围与数据源

Patchwork API 查询：

```text
https://patchwork.kernel.org/api/1.2/patches/?project=kvm&since=2025-01-01&before=2026-01-01&ordering=date%2Cid&per_page=100
```

时间范围采用半开区间：

```text
2025-01-01T00:00:00Z <= patch date < 2026-01-01T00:00:00Z
```

数据源职责：

- **Patchwork**：决定补丁是否属于统计范围，并提供 patch ID、状态、
  archive 标记、series 和 mbox 链接。
- **lore/public-inbox**：恢复邮件正文、补丁 diff、touched paths、
  Message-ID、版本号和线程关系。
- **本地 Linux 主线基线**：用于核对 RISC-V KVM 当前能力与拟议落点，
  基线为 `a635d6748234582ea287c5ffeae28b9b23f91c7e`。

## 对账结果

|项目|数量|
|---|---:|
|Patchwork 权威记录|12,817|
|lore 原始 diff 邮件|12,332|
|lore 初步 x86/arm/shared 记录|5,353|
|与 Patchwork 匹配的目标记录|5,322|
|lore-only 排除记录|31|
|Patchwork-only 记录|564|
|人工审计排除记录|4|
|最终权威补丁版本|5,318|

Patchwork-only 的 564 条记录全部抓取 mbox 并分类：

|类型|数量|
|---|---:|
|普通 cover letter|382|
|GIT PULL|177|
|带外部非内核 diff 的 cover letter|5|
|可恢复的内嵌独立内核补丁|0|

人工审计另外排除：

- 2 条只修改 TDX guest/TSC 校准、没有 KVM 实现路径的补丁。
- 1 条引用内核 diff 的死锁讨论邮件。
- 1 条修改 QEMU `target/arm/kvm`、并非 Linux 内核的补丁。

## 架构分布

|原始架构分类|补丁版本数|占比|
|---|---:|---:|
|x86|3,236|60.9%|
|arm64|1,265|23.8%|
|shared-kvm|744|14.0%|
|mixed-x86-arm|73|1.4%|
|合计|5,318|100.0%|

分类反例扫描结果：

- 未发现标题含 RISC-V、s390、LoongArch、PowerPC 或 MIPS，但被错误保留
  为 x86/arm/shared 的记录。
- 发现 6 个同标题谱系在不同修订版中由 x86/arm 路径迁移为
  shared/mixed 路径，这属于补丁演进，不是架构误标。
- 338 条标题和路径不直接包含 KVM 的记录主要属于 TDX、SEV-SNP、
  VFIO/IOMMU 等 KVM 项目接受的紧耦合虚拟化系列；评分时大多降为
  confidential-computing、VFIO 或低/不适用。

## 可移植性评分

|评分|含义|版本数|
|---|---|---:|
|A-shared|已经位于通用 KVM/RISC-V 路径，无需单独移植|831|
|B-high|存在明确跨架构不变量，近期值得实现|4|
|C-medium|方法或语义可迁移，但需要架构适配|725|
|D-low|只能借鉴设计或测试思路|2,320|
|E-none|架构专属、机械清理或不适用|1,438|
|合计||5,318|

自动规则按标题、路径、架构和子系统对每个版本评分，再按规范化标题合并
重复修订。最新 B/C 候选为 **427** 个，其中：

- x86：291
- arm64：129
- mixed-x86-arm：7

自动评分只用于完整覆盖和初筛。最终 36 条重点候选额外检查了补丁正文、
RISC-V 当前实现、依赖关系和跨年新版。

## T1：近期可实施

|#|原始架构|补丁|RISC-V 建议|
|---:|---|---|---|
|1|arm64|[Reschedule as needed when destroying stage-2 page-tables](https://patchwork.kernel.org/project/kvm/patch/20251113052452.975081-4-rananta@google.com/)|在 G-stage 页表递归销毁中加入安全调度点|
|2|x86|[Only validate counts for hardware-supported arch events](https://patchwork.kernel.org/project/kvm/patch/20250117234204.2600624-3-seanjc@google.com/)|SBI PMU 自测试仅验证宿主实际支持的事件|
|3|arm64|[Convert arch_timer tests to common helpers to pin task](https://patchwork.kernel.org/project/kvm/patch/20250626001225.744268-6-seanjc@google.com/)|复用绑核 helper 扩展 SSTC/vstimecmp 测试|
|4|x86|[Add infrastructure for getting vCPU binary stats](https://patchwork.kernel.org/project/kvm/patch/20250111005049.1247555-9-seanjc@google.com/)|验证 RISC-V exits、WFI、SBI、AIA 统计|
|5|x86|[Provide extra mmap flags in vm_mem_add()](https://patchwork.kernel.org/project/kvm/patch/20250707224720.4016504-7-jthoughton@google.com/)|支持 stage-2、memstress 和预缺页测试映射|
|6|x86|[Rely on KVM_RUN_NEEDS_COMPLETION to complete userspace exits](https://patchwork.kernel.org/project/kvm/patch/20250111012450.1262638-6-seanjc@google.com/)|统一 RISC-V MMIO/SBI userspace exit 完成路径|
|7|mixed|[Add utilities to create eventfds and do KVM_IRQFD](https://patchwork.kernel.org/project/kvm/patch/20250522235223.3178519-13-seanjc@google.com/)|构建 APLIC/IMSIC irqfd 路由测试|
|8|arm64|[Add helper to check for VGICv3 support](https://patchwork.kernel.org/project/kvm/patch/20250917212044.294760-4-oliver.upton@linux.dev/)|实现 RISC-V AIA 支持与模式探测 helper|
|9|arm64|[Add test for nASSGIcap attribute](https://patchwork.kernel.org/project/kvm/patch/20250613155239.2029059-5-rananta@google.com/)|测试 AIA 属性初始化前可配置、初始化后冻结|
|10|arm64|[Extend vgic_init to test GICv4 config attr](https://patchwork.kernel.org/project/kvm/patch/20250514192159.1751538-4-rananta@google.com/)|覆盖 AIA EMUL/AUTO/HWACCEL 配置模式|
|11|x86|[Add MSI injection test for SAVIC](https://patchwork.kernel.org/project/kvm/patch/20250923050942.206116-36-Neeraj.Upadhyay@amd.com/)|重写为 IMSIC MSI 注入、pending 和错误目标测试|
|12|x86|[Extend savic_test with idle halt testing](https://patchwork.kernel.org/project/kvm/patch/20250923050942.206116-32-Neeraj.Upadhyay@amd.com/)|验证 WFI 后由 IMSIC/APLIC 中断唤醒|
|13|x86|[Take ownership of producer/consumer token tracking](https://patchwork.kernel.org/project/kvm/patch/20250516230734.2564775-4-seanjc@google.com/)|复用 irqbypass token 管理，准备 AIA bypass consumer|

## T2：需要架构重写

T2 共 **14** 条，主要集中在以下方向：

- **guest_memfd 与 userfault**
  - guest_memfd-backed G-stage page fault
  - RISC-V guest_memfd capability 与 GMEM_ONLY memslot
  - shared mapping 的 G-stage huge-page 级别
  - KVM userfault exits
- **MMU 与 vCPU 时间**
  - MMU fault injection
  - suspend 时长计入 SBI STA steal time
  - suspend 后 guest time/htimedelta/vstimecmp 连续性
- **PMU**
  - 仅暴露可访问 counters
  - 异构 hart composite PMU profile
- **AIA 测试**
  - 默认 AIA irqchip
  - APLIC sourcecfg/target/enable/pending
  - 跨 vCPU IMSIC MSI 与 SBI IPI
  - 最小 IMSIC smoke test
- **IRQ bypass**
  - 将设备分配状态与 bypass-capable IRQ 状态解耦

这些补丁的行为目标具有可迁移性，但 ARM GIC、x86 APIC/IRTE、TSC、
PMCR/HPMN 和 x86 MMU 数据结构都不能直接复用。

## T3：基础能力依赖

T3 共 **9** 条：

- RISC-V private memory 与通用 memory attributes
- 属性边界 huge-leaf 拆分
- 属性变化期间禁止跨界 hugepage
- RISC-V pre-fault 的 memslot generation 和 VM-dead 退出语义
- RISC-V IOMMU/AIA irqfd routing-update hook
- IMSIC/HGEI direct injection 压力测试
- 无目标 vCPU 时跳过 IOMMU interrupt-remap 更新
- mediated vPMU 测试创建 helper

这些项目需要先落地 CoVE/private-memory、KVM guest_memfd、pre-fault、
RISC-V IOMMU MSI translation、AIA 硬件直注或 mediated-vPMU ABI。

## 跨年度修订

自动候选中有 **46** 个 2025 谱系在 2026H1 出现同标题修订。
36 条人工候选中有 3 条：

|2025 补丁|2026 后续版本|
|---|---|
|[Minimal GICv5 PPI selftest](https://patchwork.kernel.org/project/kvm/patch/20251219155222.1383109-36-sascha.bischoff@arm.com/)|[2026 修订版](https://patchwork.kernel.org/project/kvm/patch/20260319154937.3619520-41-sascha.bischoff@arm.com/)|
|[arm64 private memory support](https://patchwork.kernel.org/project/kvm/patch/20251217101125.91098-20-steven.price@arm.com/)|[2026 修订版](https://patchwork.kernel.org/project/kvm/patch/20260513131757.116630-26-steven.price@arm.com/)|
|[Split cross-boundary mirror leafs](https://patchwork.kernel.org/project/kvm/patch/20250807094450.4673-1-yan.y.zhao@intel.com/)|[2026 修订版](https://patchwork.kernel.org/project/kvm/patch/20260106102236.25177-1-yan.y.zhao@intel.com/)|

实施这 3 个方向时应以 2026 修订版为技术基线，但它们仍保留在 2025
统计中，因为原始提交属于本报告时间范围。

## 推荐实施顺序

1. **RISC-V selftests 快速收益**
   - vCPU binary stats
   - KVM_RUN completion
   - mmap flags
   - PMU 硬件事件过滤
   - timer CPU pin helper
2. **AIA 测试体系**
   - capability/config helper
   - device attribute freeze
   - IMSIC MSI 注入
   - WFI 唤醒
   - APLIC source 测试
3. **G-stage/MMU 稳健性**
   - 页表销毁调度
   - fault injection
   - userfault exit
4. **guest_memfd 与 memory attributes**
   - guest_memfd page fault
   - huge mapping
   - private/shared 转换
5. **硬件直注与机密 VM**
   - irqbypass/AIA/IOMMU
   - HGEI direct injection
   - private memory/CoVE

## 本目录复核入口

- [综合梳理](00-portability-overview.zh-CN.md)
- [2025 精选候选](analysis/kvm-2025-curated-candidates.md)
- [2026H1 KVM 报告](01-kvm-2026h1-report.zh-CN.md)
- [2026H1 精选候选](analysis/kvm-2026h1-curated-candidates.md)

## 限制

- 自动评分是确定性启发式，主要使用标题、架构和 touched paths；不能替代
  对全部 5,318 个版本的逐行代码审查。
- 36 条重点候选经过人工语义审计，但仍需在实际开发前检查补丁是否已合入、
  被 supersede 或在 2026H2 继续修订。
- RISC-V guest_memfd、private memory、nested virtualization、AIA 硬件加速
  和 IOMMU 集成状态会改变未来评级。
- Patchwork 2025 历史记录当前大部分为 archived，状态字段不能等价于
  “已合入”或“已拒绝”。
