# 2026 年上半年 KVM x86/arm 补丁移植到 RISC-V 的可行性分析

## 结论摘要

- 统计窗口为 `2026-01-01`（含）至 `2026-07-01`（不含），覆盖用户给定 Patchwork KVM 项目的全部状态与归档记录。
- Patchwork 权威清单共 `8,135` 条记录；lore 公共邮件归档解析出 `8,042` 封含 diff 的原始补丁邮件。
- 最终纳入 x86、arm64、x86/arm mixed 和 shared KVM core 的权威补丁版本共 `4,059` 条：
  - x86：`2,585`
  - arm64：`760`
  - mixed x86/arm：`58`
  - shared KVM：`656`
- 按规范化标题去重后为 `2,128` 个逻辑补丁谱系。
- 全量逐补丁评分：
  - `A-shared`：`757`，已经通过通用 KVM 代码或直接修改 RISC-V 生效，不需要另行移植。
  - `B-high`：`1`，近期最明确的 RISC-V 功能缺口。
  - `C-medium`：`767`，可以移植设计意图，但需要明显的 RISC-V 架构适配。
  - `D-low`：`1,646`，只能复用算法、测试方法或错误模型。
  - `E-none`：`888`，架构 ABI 专属、机械清理或没有对应 RISC-V 需求。
- 最新版本候选池为 `343` 个逻辑补丁；经三路人工子系统审计后，保留 `36` 条重点记录：
  - 近期可做 `13`
  - 需要架构重写 `12`
  - 依赖 guest_memfd/私有内存前置 `11`
- 最值得优先推进的是 `KVM_PRE_FAULT_MEMORY`、G-stage/TLB/memslot 正确性、dirty-ring/steal-time 测试、SBI PMU 重编程，以及 AIA/IMSIC 基础测试。

## 数据对账

### Patchwork

使用 Patchwork REST API，查询条件为：

```text
project=kvm
since=2026-01-01
before=2026-07-01
ordering=date,id
per_page=100
```

结果为 `82` 页、`8,135` 条，最早记录时间为 `2026-01-01T09:05:13`，最晚为 `2026-06-30T23:47:15`。Patchwork ID 与 Message-ID 均唯一。

### lore

从 `https://lore.kernel.org/kvm/1` 的 public-inbox Git 镜像解析：

- 候选邮件 commit：`22,195`
- 原始 diff 补丁：`8,042`
- 排除 stable `FAILED: Patch ...` 通知：`31`
- cover letter：`861`
- reply：`12,372`

### 102 条 Patchwork-only 记录

全部抓取 mbox 后分类为：

|类别|数量|处理|
|---|---:|---|
|GIT PULL|93|不是单补丁 diff，不进入逐补丁分析|
|含外部脚本 diff 的 cover letter|4|TDX 模块辅助脚本，不是 Linux 内核补丁|
|PULL cover letter|2|不是单补丁|
|普通 pull request|1|不是单补丁|
|无 diff|1|s390 邮件只有 diffstat，没有补丁正文|
|转发邮件内嵌内核补丁|1|恢复为一个 x86 补丁并纳入分析|

恢复的补丁是 `[RFC PATCH 2/2] KVM: x86: Relay a nested Hyper-V root's vmbus posts`。它依赖 VMX、eVMCS、Hyper-V nested ABI，评级为低可移植性，不进入 RISC-V 候选。外层邮件声称有两个附件，但实际 mbox 仅包含 `2/2` 的 git-format patch；`1/2` 只有描述，没有可恢复的补丁正文。

### 其他边界修正

- 排除 `5` 条 lore-only 的 x86/shared 记录，因为它们不在用户指定的 Patchwork 权威清单中。
- 修正了 `36` 条架构误分类：
  - `4` 条 RISC-V 原生 stage-2 TLB flush 补丁曾因 `stage-2` 关键词被误标为 arm64。
  - `32` 条是在 s390 上模拟 arm64 KVM 的实验补丁，不属于 arm64 主线后端。

## 评分方法

### A-shared

补丁已经修改 `arch/riscv/`，或完全位于 `virt/kvm/`、通用 UAPI、通用 selftests。此类补丁不需要“移植”，只需要在 RISC-V 上验证行为。

### B-high

RISC-V 已有对应基础设施，补丁解决的是跨架构不变量，且适配范围明确、依赖较少。

### C-medium

目标功能或缺陷在 RISC-V 上成立，但 EPT/NPT/ARM Stage-2、APIC/GIC、TSC/PMUv3 等实现必须重写为 G-stage、HFENCE.GVMA、AIA/IMSIC、SBI PMU 或 RISC-V timer 语义。

### D-low / E-none

- D-low：架构机制不能移植，但测试触发方法、状态机或安全模型可作为参考。
- E-none：CPUID/MSR/VMCS/VMCB/sysreg 等 ABI 专属补丁、纯重命名/清理、临时 `DO NOT MERGE` 补丁。

## RISC-V 子系统映射

|x86/arm 子系统|RISC-V 对应位置|结论|
|---|---|---|
|EPT/NPT/ARM Stage-2|`arch/riscv/kvm/gstage.c`、`mmu.c`、`tlb.c`|最高价值方向；移植不变量，不复制 PTE/SPTE 实现|
|dirty log、memslot、MMU notifier|G-stage fault、HFENCE.GVMA、dirty-ring|近期可审计和实现|
|APIC/GIC/ITS|AIA、APLIC、IMSIC|寄存器 ABI 不可移植；测试方法可重写|
|irqfd/eventfd/routing|通用 KVM core + AIA backend|条件性可移植，需要 producer/路由模型|
|TSC/pvclock/ARM arch timer|`vcpu_timer.c`、SSTC、hrtimer|状态机和迁移不变量可移植|
|x86/ARM PMU|SBI PMU、Sscofpmf、perf event|计数器生命周期可移植，事件编码和 UAPI 需重写|
|guest_memfd/private memory|`guest_memfd.c` + G-stage hooks|中长期；缺 Kconfig、capability、页所有权和安全 ABI|
|nested VMX/SVM/EL2|HGATP/CSR/HFENCE + SBI nested 设计|主线完整 nested KVM 尚未落地，仅研究价值|
|TDX/SEV-SNP/pKVM/CCA|未来 CoVE/TEE/TSM 方案|不能按普通补丁移植|

## 近期候选

以下 `13` 条可优先进入 RISC-V KVM 审计或实现队列。`B-high` 只有第一条；其余为需要有限架构重写但收益明确的 `C-medium`。

|#|补丁|建议|
|---:|---|---|
|1|[KVM: arm64: Add pre_fault_memory implementation](https://patchwork.kernel.org/project/kvm/patch/20260612162354.73378-3-jackabt.amazon@gmail.com/)|为 RISC-V 实现 `KVM_PRE_FAULT_MEMORY`，覆盖 MMU notifier 重试、THP 和 huge-leaf 建映射|
|2|[Fix missed remote tlb flush in rmap_write_protect()](https://patchwork.kernel.org/project/kvm/patch/20260626112634.1778506-9-pbonzini@redhat.com/)|审计 write-protect 后是否遗漏远端 `HFENCE.GVMA`|
|3|[Ensure hugepage is in by slot before checking max mapping level](https://patchwork.kernel.org/project/kvm/patch/20260626174620.1819772-9-pbonzini@redhat.com/)|在选择 G-stage huge-leaf 前约束 memslot 边界|
|4|[Don't create SPTEs for addresses that aren't mappable](https://patchwork.kernel.org/project/kvm/patch/20260219002241.2908563-1-seanjc@google.com/)|验证 HGATP mode 的 GPA 宽度，防止高位截断错误映射|
|5|[Drop/zap existing present SPTE when creating an MMIO SPTE](https://patchwork.kernel.org/project/kvm/patch/20260330080144.158592-1-pbonzini@redhat.com/)|审计 RAM 转 MMIO/无 slot 时旧 G-stage leaf 的解除和 flush|
|6|[Introduce kvm_split_cross_boundary_leafs()](https://patchwork.kernel.org/project/kvm/patch/20260106102136.25108-1-yan.y.zhao@intel.com/)|为跨 memslot/属性边界的 huge leaf 设计拆分流程|
|7|[Fix page leak in user_mem_abort() on atomic fault](https://patchwork.kernel.org/project/kvm/patch/20260304162222.836152-2-tabba@google.com/)|审计 RISC-V fault unwind 的 page/PFN 引用计数|
|8|[Enable pre_fault_memory_test for arm64](https://patchwork.kernel.org/project/kvm/patch/20260612162354.73378-4-jackabt.amazon@gmail.com/)|在 RISC-V 实现完成后启用同一通用 selftest|
|9|[Test steal time when re-adding a vCPU on a new thread](https://patchwork.kernel.org/project/kvm/patch/20260505003044.78693-5-dongli.zhang@oracle.com/)|重写为 SBI STA 的 vCPU 重建、换线程和单调性测试|
|10|[memstress: Add option to enable dirty-ring on VM creation](https://patchwork.kernel.org/project/kvm/patch/20260629105950.1790259-2-leo.bras@arm.com/)|直接扩展 RISC-V dirty-ring 高并发压力测试|
|11|[Use hardware value when reprogramming for FIXED_CTR_CTRL changes](https://patchwork.kernel.org/project/kvm/patch/20260603231905.1738487-2-seanjc@google.com/)|验证 SBI PMU 重编程不会清零或丢失累计计数|
|12|[Add a test to measure local timer latency](https://patchwork.kernel.org/project/kvm/patch/b54bdd9878213e06a410db415cc6aaa79000341b.1772732517.git.isaku.yamahata@intel.com/)|重写为 `rdtime`/`vstimecmp`，同时覆盖 SSTC 和 hrtimer fallback|
|13|[Cache IRQ routing entries allocation](https://patchwork.kernel.org/project/kvm/patch/20260525035242.107264-3-yanfei.xu@bytedance.com/)|审计 AIA 路由更新是否需要对应缓存失效或 arch hook|

## 中期候选

`12` 条 T2 候选主要包括：

- ARM hardware dirty-bitmap/HDBSS：只复用批量清 dirty、huge-leaf 拆分和回退算法。
- x86 memslot zap/fast-zap：复用锁内 detach、锁外释放和失效顺序。
- GICv5 selftests：重写为 IMSIC interrupt smoke test、no-AIA 回退测试。
- irqfd producer：在 AIA 硬件加速后端定义 producer 和动态 MSI 路由生命周期。
- Partitioned PMU：重写 overflow、event filter 和 counter partition 测试。
- PV clock timer correction：提取迁移、save/restore 和单调性测试意图。

## 前置依赖候选

`11` 条 T3 候选围绕 guest_memfd/private memory。它们本身具有通用价值，但在以下基础工作完成前不应独立移植：

1. RISC-V Kconfig 选择 `KVM_GUEST_MEMFD` 和 `KVM_GENERIC_MEMORY_ATTRIBUTES`。
2. 定义 private/shared/INIT_SHARED capability 与用户态 ABI。
3. 定义 G-stage attribute 转换、unmap、HFENCE 和 fault 行为。
4. 定义页所有权、folio reclaim、populate、teardown 和 memory failure 语义。
5. 若用于机密虚拟机，先确定 CoVE/TEE/TSM 和设备隔离模型。

## 不建议直接移植

- CPUID、MSR、XSAVE/XFD、VMCS/VMCB、ARM sysreg/ID register：RISC-V 使用 CSR、ISA/SBI extension 和自身 one-reg ABI。
- VMX/SVM/ARM NV：完整 RISC-V nested virtualization 尚未进入主线，字段级移植没有意义。
- APIC/IOAPIC/GIC/ITS 实现：必须按 AIA/APLIC/IMSIC 重写。
- TDX、SEV-SNP、pKVM、CCA：页面所有权、attestation 和固件 ABI 均为平台专属。
- 纯重命名、结构移动、文档、格式和临时 reproducer：不形成 RISC-V 功能缺口。

## 本目录复核入口

- [综合梳理](00-portability-overview.zh-CN.md)
- [2026H1 精选候选](analysis/kvm-2026h1-curated-candidates.md)
- [2025 KVM 报告](02-kvm-2025-report.zh-CN.md)
- [2025 精选候选](analysis/kvm-2025-curated-candidates.md)

## 局限

- 对 `4,059` 条记录的逐补丁结论由标题、触及路径、版本谱系和规则化子系统映射生成；`36` 条重点候选另外进行了正文、RISC-V 主线实现和依赖人工审计。
- Patchwork 页面中的状态字段在本次 API 返回中均为 `new`，因此本报告不把 Patchwork state 作为技术优先级依据。
- Linux RISC-V 基线为 `7.2.0-rc2`，commit `a635d6748234582ea287c5ffeae28b9b23f91c7e`；后续主线若合入 guest_memfd、nested KVM 或新的 AIA 加速，T2/T3 评级应重新计算。
