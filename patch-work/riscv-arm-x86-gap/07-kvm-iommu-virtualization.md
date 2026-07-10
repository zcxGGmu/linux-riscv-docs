# RISC-V KVM、IOMMU 与虚拟化架构接口差距

## 1. 范围、基线与结论

本文只讨论 RISC-V 相对 arm64/x86 在 KVM、G-stage MMU、guest_memfd、VFIO、AIA irq-bypass、RISC-V IOMMU、IOMMUFD、nested virtualization 和 CoVE 方面的架构接口差距。候选以统一注册表中的 `VIRT-01` 至 `VIRT-15` 为准，不把同一机制在 IRQ、MMU 或平台报告中的交叉命中重复计算。

固定审计基线：

- Torvalds mainline：`d96fcfe1b7f94ac742984ae7986b94a116abff1b`，Linux `7.2.0-rc2`，提交日期 `2026-07-10`。
- linux-next：`bee763d5f341b99cf472afeb508d4988f62a6ca1`，快照日期 `2026-07-10`。
- 邮件窗口：`2025-01-01` 至 `2026-07-10`（含）。
- 在固定快照中，mainline 与 linux-next 的 `arch/riscv/kvm/` 内容一致；linux-next 的 `drivers/iommu/riscv/` 没有补齐本文列出的高级接口。

本领域最终保留 **15 个主候选**：

- **P0：5 项**，可以形成近期独立系列。
- **P1：7 项**，其中部分可拆出低依赖第一阶段，其余依赖设备、IOMMU 或 ABI 基础设施。
- **P2：3 项**，属于 nested、vIOMMU 和 CoVE 长期能力。
- **状态：15 项均为 `unclaimed`**。部分相关 arm64/x86 或通用系列仍在演进，但截至基线没有对应的 RISC-V 实现系列进入 mainline、linux-next 或形成可识别的 active RFC。

最建议优先投入的顺序是：

1. `VIRT-01` G-stage/IOMMU ptdump 和 `VIRT-02` G-stage 脱锁销毁，先补可观测性和长临界区问题。
2. `VIRT-04` `KVM_PRE_FAULT_MEMORY`，复用已经稳定的 generic ioctl，并把 memslot generation、VM-dead 和 MMU notifier retry 作为首版契约。
3. `VIRT-03` shared/mappable guest_memfd，作为后续 private memory 和 CoVE 的必要地基。
4. `VIRT-06` KVM/VFIO generic device API 第一阶段、`VIRT-09` fault reporting 第一阶段、`VIRT-11` IOMMUFD `hw_info` 第一阶段。
5. 在可用 RISC-V IOMMU 和 AIA HWACCEL 平台上推进 `VIRT-07`、`VIRT-08`、`VIRT-10`、`VIRT-12`。
6. 将 `VIRT-13`、`VIRT-14`、`VIRT-15` 维持为 P2 长期路线，不把尚未稳定的 ABI 伪装成近期可交付工作。

## 2. 分类与阅读规则

本文沿用统一注册表的 G 分类：

- **G1：直接实现已有通用接口。** KVM/IOMMU core 已有明确 hook、UAPI 或生命周期，RISC-V 缺后端。
- **G2：跨子系统通用化。** 需要 KVM、IRQ、VFIO、IOMMU 或 IOMMUFD 共同定义对象生命周期。
- **G4：基础设施依赖。** 缺口成立，但依赖 AIA HWACCEL、RISC-V IOMMU、nested、CoVE、硬件能力或未稳定 ABI。

状态字段含义：

- **unclaimed**：缺口真实，但没有发现精确对应的 RISC-V 实现系列。
- **相关系列活跃**：arm64/x86 或通用接口仍有补丁活动，不等于 RISC-V 候选已经有人认领。
- **第一阶段可独立**：主候选虽然总体依赖较重，但可以拆出不依赖完整栈的首个可评审系列。

原始架构标签指候选设计证据主要来自何处：

- `arm64`：主要由 arm64 KVM、SMMU 或 pKVM/CCA 系列提供接口先例。
- `x86+arm64`：x86 和 arm64 均已有实现或共同推动了通用接口。
- `shared`：核心接口本身位于通用 KVM/IOMMU 代码，架构补丁只提供使用先例。

## 3. 十五项候选总表

| ID | 分层 | G / P | 状态 | 原始架构 | 第一可交付点 | 依赖判断 |
|---|---|---|---|---|---|---|
| `VIRT-01` | KVM core / IOMMU observability | G1 / P0 | unclaimed | arm64 | canonical G-stage debugfs ptdump | 低依赖；IOMMU dump 可作为同组后续 |
| `VIRT-02` | KVM core | G1 / P0 | unclaimed | arm64 | 锁内 detach、锁外释放 G-stage tree | 低依赖，但必须证明 teardown 排他性 |
| `VIRT-03` | guest_memfd | G1 / P0 | unclaimed | x86+arm64 | shared/mappable guest_memfd | 中等依赖；不含 private memory |
| `VIRT-04` | prefault | G1 / P0 | unclaimed | x86+arm64 | 普通 userspace memory prefault | 低至中等依赖；gmem 后续接入 |
| `VIRT-05` | userfault | G1 / P1 | unclaimed | arm64 | 4K leaf memory-fault exit | 依赖 generic userfault UAPI 稳定 |
| `VIRT-06` | VFIO | G1 / P0 | unclaimed | x86+arm64 | 选择 `KVM_VFIO` 并跑通 generic API | 第一阶段可独立；coherency 需另审 |
| `VIRT-07` | AIA irq-bypass | G2 / P1 | unclaimed | x86+arm64 | producer/consumer add、del、retarget、rollback | 依赖 AIA HWACCEL、VFIO producer 和 MSI translation |
| `VIRT-08` | AIA + RISC-V IOMMU MSI | G4 / P1 | unclaimed | arm64 | per-device MSI translation table | 明确基础设施依赖 |
| `VIRT-09` | IOMMU fault / PRI / IOPF | G1 / P1 | unclaimed | shared | 结构化不可恢复 fault reporting | 第一阶段可独立；PRI/IOPF 后续 |
| `VIRT-10` | IOMMU SVA / PASID | G2 / P1 | unclaimed | arm64 | kernel-managed global PASID + single-device SVA | 依赖 ATS、IOPF 和 mm/PASID 生命周期 |
| `VIRT-11` | IOMMUFD / nested HWPT | G4 / P1 | unclaimed | x86+arm64 | RISC-V `iommu_hw_info` UAPI | `hw_info` 可独立；nested/tag 协调依赖重 |
| `VIRT-12` | IOMMU dirty tracking | G1 / P1 | unclaimed | arm64 | AMO_HWAD 条件下 D-bit dirty ops | 依赖真实硬件能力和精确 IOTINVAL |
| `VIRT-13` | vIOMMU | G4 / P2 | unclaimed | x86+arm64 | vIOMMU object + nested domain glue | 长期；依赖 `VIRT-09`、`VIRT-11` |
| `VIRT-14` | nested KVM | G4 / P2 | unclaimed | arm64 | nested state/UAPI + 最小 L2 启动 | 长期；规范、QEMU ABI 和 shadow G-stage |
| `VIRT-15` | CoVE | G4 / P2 | unclaimed | arm64 | shared gmem 后的 memory-attribute 状态机 | 长期；依赖稳定 CoVE ABI 和页所有权 |

## 4. KVM Core

<a id="virt-01"></a>
### VIRT-01：KVM G-stage 与 RISC-V IOMMU ptdump 可观测性

- **分类与状态**：G1，P0，`unclaimed`，总分 26；原始架构为 arm64。
- **六维评分**：impact=5，generality=4，readiness=5，validation=4，hardware-independence=4，acceptance=4；**总分=26**。
- **价值判断**：这是低风险、高杠杆的可观测性工作。它不改变 G-stage 或 IOMMU 的映射语义，却能为 huge leaf、PBMT、NAPOT、dirty logging、IMSIC 映射、IOMMU nested 和 CoVE 后续工作提供直接证据。
- **基线证据**：
  - arm64 已有 `CONFIG_PTDUMP_STAGE2_DEBUGFS` 和 `arch/arm64/kvm/ptdump.c`。
  - RISC-V 的 `arch/riscv/kvm/` 没有 ptdump 文件、Kconfig 或 VM debugfs walker。
  - generic IOMMU debugfs 已存在，但 `drivers/iommu/riscv/iommu.c` 没有 DDT、PDT 或 IO page-table dump。
- **精确落点**：
  - `arch/riscv/kvm/gstage.c`
  - `arch/riscv/kvm/Kconfig`
  - `arch/riscv/kvm/Makefile`
  - `drivers/iommu/iommu-debugfs.c`
  - `drivers/iommu/riscv/iommu.c`
  - `kvm_riscv_gstage_get_leaf()`、`pt_iommu_riscv_64_hw_info()`、`iommu_iova_to_phys()`
- **RISC-V 缺口**：
  - KVM 侧无法直接检查 GPA range、leaf level、HPA、R/W/X、A/D、PBMT、NAPOT、MMIO 和 IMSIC 映射。
  - IOMMU 侧无法检查 device context、PSCID/GSCID、IOSATP/IOHGATP、IOVA leaf、MSI PTE 和 attached device。
- **移植方式**：移植 arm64 ptdump 的“只读 walker + seq_file + 生命周期锁”模式，不复制 arm64 PTE 解码。RISC-V 必须使用自身 G-stage PTE、PBMT、NAPOT 和 HGATP mode 语义。
- **第一版补丁系列**：
  1. 为 RISC-V G-stage 增加只读 walker 或稳定的 walker callback 接口。
  2. 增加 VM debugfs `stage2_page_tables`，只覆盖 canonical G-stage root。
  3. 输出 4K/2M/1G leaf、权限、A/D、PBMT 和 NAPOT。
  4. 单独后续补丁为 kernel-managed RISC-V IOMMU paging domain 增加 debugfs dump。
  5. DDT、PDT、MSI table 和 nested root 留到后续系列。
- **阻塞与风险**：
  - walker 必须在 `mmu_lock` 读侧或等价生命周期保护下运行，不能读取已释放页表页。
  - 大 VM 输出需要可中断，不能长时间占锁。
  - confidential/private PA 不应暴露给无权限用户。
- **验证**：
  - 创建 4K、2M、1G、MMIO、IMSIC 和 dirty-log 映射并核对输出。
  - map/unmap、memslot delete、VM teardown 与循环读取 debugfs 并发。
  - 对 IOMMU 输出与 `iommu_iova_to_phys()` 做抽样对照。
  - 启用 KASAN、KCSAN 和 lockdep。
- **维护者与列表**：RISC-V KVM、RISC-V IOMMU、IOMMU core；`kvm-riscv@lists.infradead.org`、`kvm@vger.kernel.org`、`iommu@lists.linux.dev`、`linux-riscv@lists.infradead.org`。
- **原始补丁与先例**：
  - [arm64 KVM stage-2 ptdump walker 演进](https://lore.kernel.org/linux-arm-kernel/20250407053113.746295-2-anshuman.khandual@arm.com/)
  - [通用 IOMMU page-table dump 提案](https://lore.kernel.org/linux-arm-kernel/20250814093005.2040511-2-xiaqinxin@huawei.com/)
  - [arm64 KVM ptdump 基线实现](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/kvm/ptdump.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)
  - [RISC-V G-stage 当前实现](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kvm/gstage.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)

<a id="virt-02"></a>
### VIRT-02：G-stage 脱锁销毁与可调度化

- **分类与状态**：G1，P0，`unclaimed`，总分 26；原始架构为 arm64。
- **六维评分**：impact=5，generality=4，readiness=5，validation=4，hardware-independence=4，acceptance=4；**总分=26**。
- **价值判断**：这是明确的长临界区和可抢占性问题。RISC-V 大 VM 销毁时，当前实现可能在 spin-based `rwlock_t` 写锁内递归遍历并释放大量 G-stage 页表。
- **基线证据**：`kvm_riscv_mmu_free_pgd()` 在 `mmu_lock` 写锁内调用全地址空间 `kvm_riscv_gstage_unmap_range()`；mainline 与 linux-next 相同。
- **精确落点**：
  - `arch/riscv/kvm/mmu.c:kvm_riscv_mmu_free_pgd()`
  - `arch/riscv/kvm/gstage.c:kvm_riscv_gstage_op_pte()`
  - `arch/riscv/kvm/gstage.c:kvm_riscv_gstage_unmap_range()`
  - `pgd`、`pgd_phys`、`levels` 和 remote HFENCE 路径
- **RISC-V 缺口**：全树递归释放期间不能直接调用 `cond_resched()`；页表越稀疏且 guest physical address space 越大，最长不可抢占区越明显。
- **移植方式**：采用 arm64 和 x86 后续 MMU 重构共同体现的“两阶段 teardown”不变量：锁内停止新访问并 detach root，锁外遍历和释放 detached tree。
- **第一版补丁系列**：
  1. 在写锁内将 root 从 VM 可见状态原子分离，清除 `pgd/pgd_phys/levels`。
  2. 完成使旧 root 不再可被硬件使用所需的 remote HFENCE。
  3. 新增 teardown-only walker，在锁外释放页表页。
  4. 每释放固定数量的页表页调用 `cond_resched()`。
  5. 不把普通 memslot unmap 改成无锁释放。
- **阻塞与风险**：
  - 必须证明 VM teardown 后没有新的 vCPU fault、map 或 notifier 回调进入旧 root。
  - 页表页释放前必须完成必要的远端 translation invalidation。
  - 不应为复用代码而改变普通 zap 的锁语义。
- **验证**：
  - 构造数百 GB 稀疏 GPA 和数十万页表页，循环创建/销毁 VM。
  - 测量最长不可抢占时间和 scheduler latency。
  - 并发 vCPU teardown、memslot removal 和 VM fd close。
  - PREEMPT、lockdep、KASAN、KCSAN、RCU torture。
- **维护者与列表**：RISC-V KVM；通用 KVM MMU 评审应抄送 KVM core。
- **原始补丁与先例**：
  - [KVM: arm64: Reschedule as needed when destroying the stage-2 page-tables](https://patchwork.kernel.org/project/kvm/patch/20251113052452.975081-4-rananta@google.com/)
  - [KVM: x86/mmu: Split kvm_mmu_zap_all_fast() into front and back halves](https://patchwork.kernel.org/project/kvm/patch/20260630222607.497895-9-seanjc@google.com/)
  - [RISC-V 当前 free_pgd 路径](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kvm/mmu.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n676)

## 5. guest_memfd、Prefault 与 Userfault

<a id="virt-03"></a>
### VIRT-03：guest_memfd shared/mappable 第一阶段

- **分类与状态**：G1，P0，`unclaimed`，总分 26；原始架构为 x86+arm64。
- **六维评分**：impact=5，generality=4，readiness=5，validation=4，hardware-independence=4，acceptance=4；**总分=26**。
- **价值判断**：这是 RISC-V KVM 私有内存、CoVE 和统一 gmem selftests 的基础，但首版必须刻意限制为 shared/mappable gmem，避免把未稳定的 private-memory 语义拖入同一系列。
- **基线证据**：
  - arm64 和 x86 的 `KVM_GUEST_MEMFD` 已进入 mainline。
  - RISC-V `arch/riscv/kvm/Kconfig` 未选择 `KVM_GUEST_MEMFD`。
  - `kvm_riscv_mmu_map()` 仍以 HVA/VMA fault 为主，没有 `kvm_gmem_get_pfn()` 路径。
- **精确落点**：
  - `arch/riscv/kvm/Kconfig`
  - `arch/riscv/kvm/mmu.c:kvm_riscv_mmu_map()`
  - `kvm_arch_prepare_memory_region()`
  - `kvm_gmem_get_pfn()`
  - `virt/kvm/guest_memfd.c`
- **RISC-V 缺口**：无法创建 `KVM_MEM_GUEST_MEMFD` memslot，也无法从 guest_memfd 获取 PFN 并建立 G-stage 映射。
- **移植方式**：复用 arm64 的 gmem fault 分支和通用 guest_memfd 生命周期，但重新实现 RISC-V G-stage leaf 选择、HFENCE、PBMT 和 dirty-log 规则。
- **第一版补丁系列**：
  1. 选择 `KVM_GUEST_MEMFD`。
  2. 仅接受 `GUEST_MEMFD_FLAG_MMAP` 和 `GUEST_MEMFD_FLAG_INIT_SHARED`。
  3. 在 fault path 中区分普通 HVA 与 shared gmem。
  4. 明确拒绝 gmem-only/private slot。
  5. 保持 readonly、dirty logging、MMU notifier 和 memslot generation 语义。
  6. 先使用保守 4K leaf；huge-leaf 支持可在 folio 和 mapping-level 规则稳定后单独提交。
- **阻塞与风险**：
  - 需要定义 shared gmem folio release、HWPOISON 和 VM teardown 顺序。
  - 查询 gmem folio 或 mapping level 的路径不能在不允许睡眠的 MMU 锁区间执行。
  - 不能因为未来 CoVE 需求提前开放 private 状态。
- **验证**：
  - 将 `guest_memfd_test` 和 `set_memory_region_test` 的 gmem 用例加入 RISC-V。
  - `mmu_stress`、memslot move/delete、mmap fault、HWPOISON、VM teardown。
  - readonly、dirty-log、shared mapping 和普通 HVA slot 混合。
- **维护者与列表**：RISC-V KVM、KVM guest_memfd/core。
- **原始补丁与先例**：
  - [KVM: arm64: Handle guest_memfd-backed guest page faults](https://patchwork.kernel.org/project/kvm/patch/20250729225455.670324-19-seanjc@google.com/)
  - [KVM: arm64: Enable support for guest_memfd backed memory](https://patchwork.kernel.org/project/kvm/patch/20250729225455.670324-21-seanjc@google.com/)
  - [KVM: x86/mmu: Extend guest_memfd max mapping level to shared mappings](https://patchwork.kernel.org/project/kvm/patch/20250729225455.670324-16-seanjc@google.com/)
  - [arm64 mainline guest_memfd enablement commit](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=32e200bd6e44)
  - [x86 mainline guest_memfd enablement commit](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=d1e54dd08f16)

<a id="virt-04"></a>
### VIRT-04：实现 `KVM_PRE_FAULT_MEMORY`

- **分类与状态**：G1，P0，`unclaimed`，总分 26；原始架构为 x86+arm64。
- **六维评分**：impact=5，generality=4，readiness=5，validation=4，hardware-independence=4，acceptance=4；**总分=26**。
- **价值判断**：generic ioctl 已稳定，RISC-V 已有 G-stage map 和通用 MMU notifier locking，是最清晰的近期功能缺口之一。它直接改善迁移恢复和大 VM 启动的逐页 fault 成本。
- **基线证据**：
  - generic `KVM_PRE_FAULT_MEMORY` ioctl 和 x86 backend 已在 mainline。
  - arm64 在 2026 年提交了实现与 selftest enablement。
  - RISC-V 未选择 `KVM_GENERIC_PRE_FAULT_MEMORY`，也没有 `kvm_arch_vcpu_pre_fault_memory()`。
- **精确落点**：
  - `include/linux/kvm_host.h:kvm_arch_vcpu_pre_fault_memory()`
  - `virt/kvm/kvm_main.c`
  - `arch/riscv/kvm/mmu.c`
  - `mmu_invalidate_seq`、memslot generation、VM-dead 状态
- **RISC-V 缺口**：VMM 无法在 vCPU 运行前主动建立 G-stage 映射，只能等待 guest fault。
- **移植方式**：复用 RISC-V G-stage 建映射 helper，不伪造完整 guest trap；将“可睡眠 fault-in”和“锁内安装 PTE”分开。
- **第一版补丁系列**：
  1. 选择 `KVM_GENERIC_PRE_FAULT_MEMORY`。
  2. 先只支持普通 userspace memory。
  3. 按页或 folio fault-in，并在批次边界检查 signal、VM-dead、memslot generation 和 `mmu_invalidate_seq`。
  4. memslot move/delete 或 notifier 竞争时返回 `-EAGAIN`。
  5. 将通用 `pre_fault_memory_test` 加入 RISC-V。
  6. guest_memfd prefault 在 `VIRT-03` 合入后单独扩展。
- **阻塞与风险**：
  - GUP/gmem 获取不能在 `mmu_lock` 下睡眠。
  - 必须保持 userspace 可重试契约，不能吞掉 memslot generation 变化。
  - huge leaf 只能在 slot、folio、GPA 和属性边界全部满足时建立。
- **验证**：
  - 普通匿名内存、hugetlb、THP、dirty logging。
  - memslot move/delete、并发 MMU notifier、signal interruption、VM fd close。
  - 验证 `-EAGAIN` 和 VM-dead 退出，不留下部分错误映射。
- **维护者与列表**：RISC-V KVM、KVM core/selftests。
- **原始补丁与先例**：
  - [KVM: arm64: Add pre_fault_memory implementation](https://patchwork.kernel.org/project/kvm/patch/20260612162354.73378-3-jackabt.amazon@gmail.com/)
  - [KVM: selftests: Enable pre_fault_memory_test for arm64](https://patchwork.kernel.org/project/kvm/patch/20260612162354.73378-4-jackabt.amazon@gmail.com/)
  - [KVM: x86/mmu: Return -EAGAIN if userspace deletes/moves memslot during prefault](https://patchwork.kernel.org/project/kvm/patch/20250822070347.26451-1-yan.y.zhao@intel.com/)
  - [KVM: x86/mmu: Bail out mapping when VM is dead](https://patchwork.kernel.org/project/kvm/patch/20250226195529.2314580-21-pbonzini@redhat.com/)
  - [generic pre-fault core](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/virt/kvm/kvm_main.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n4333)

<a id="virt-05"></a>
### VIRT-05：RISC-V KVM userfault exits

- **分类与状态**：G1，P1，`unclaimed`，总分 23；原始架构为 arm64。
- **六维评分**：impact=4，generality=4，readiness=4，validation=4，hardware-independence=4，acceptance=3；**总分=23**。
- **价值判断**：`KVM_EXIT_MEMORY_FAULT` 和 `kvm_prepare_memory_fault_exit()` 已存在，但 generic userfault policy 和 UAPI 仍需先稳定。该候选适合跟进上游接口，不适合在 RISC-V 私自定义另一套 ABI。
- **基线证据**：
  - mainline 已有 memory-fault exit helper。
  - arm64 userfault 系列仍处于邮件提案阶段。
  - RISC-V G-stage fault path 没有 arch 接入。
- **精确落点**：
  - `include/linux/kvm_host.h:kvm_prepare_memory_fault_exit()`
  - `arch/riscv/kvm/mmu.c:kvm_riscv_mmu_map()`
  - RISC-V load/store/execute fault 访问类型解码
- **RISC-V 缺口**：不能把指定 GPA 的缺页或用户管理权限 fault 以稳定 KVM exit 交给 VMM。
- **移植方式**：等待通用 UAPI 合入后，只实现 RISC-V arch policy 和 fault exit 构造；不把 host `userfaultfd` PTE 标志与 KVM userfault ABI 混用。
- **第一版补丁系列**：
  1. 只支持 4K leaf。
  2. 在获取 PFN 前判断 userfault policy。
  3. 精确构造 read、write、execute fault flags。
  4. userspace 处理后重新进入 guest，再走正常 G-stage map。
  5. huge leaf、guest_memfd 和 private memory 交互留到后续。
- **阻塞与风险**：
  - generic userfault UAPI 必须先稳定。
  - 需要定义 dirty logging、MMU notifier retry、memslot generation 和 huge-leaf split 的交互。
  - 不能把所有 G-stage fault 都暴露给 userspace，避免性能和安全回退。
- **验证**：
  - userspace 收到 exit、填页并重入。
  - read/write/execute、取消、memslot generation 变化。
  - dirty-log 开关、slot delete、并发 notifier。
- **维护者与列表**：KVM core、RISC-V KVM。
- **原始补丁与先例**：
  - [KVM: arm64: Add support for KVM userfault exits](https://patchwork.kernel.org/project/kvm/patch/20250618042424.330664-7-jthoughton@google.com/)
  - [mainline memory-fault exit helper](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/linux/kvm_host.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n2513)

## 6. VFIO、AIA 与 IRQ Bypass

<a id="virt-06"></a>
### VIRT-06：启用 `KVM_VFIO` 并定义 coherency 语义

- **分类与状态**：G1，P0，`unclaimed`，总分 26；原始架构为 x86+arm64。
- **六维评分**：impact=5，generality=4，readiness=5，validation=4，hardware-independence=4，acceptance=4；**总分=26**。
- **价值判断**：`virt/kvm/vfio.c` 已是通用实现，RISC-V 的第一步可以非常小：选择 `KVM_VFIO` 并验证 generic device API。non-coherent DMA policy 必须作为独立第二阶段，不应与 irq-bypass 混成一个系列。
- **基线证据**：
  - arm64/x86 选择 `KVM_VFIO`。
  - RISC-V 未选择该能力。
  - generic 实现会调用 `kvm_arch_register_noncoherent_dma()` 等架构 hook。
- **精确落点**：
  - `arch/riscv/kvm/Kconfig`
  - `virt/kvm/vfio.c:kvm_vfio_file_add()`
  - `kvm_vfio_update_coherency()`
  - `kvm_arch_register_noncoherent_dma()` / `kvm_arch_unregister_noncoherent_dma()`
- **RISC-V 缺口**：缺少 `KVM_DEV_TYPE_VFIO` 设备关联、VFIO file 到 VM 的绑定，以及 IOMMU group coherency 生命周期。
- **移植方式**：先复用 generic KVM/VFIO device API；再根据 RISC-V DMA coherency 描述和平台 CMO 能力决定架构 hook。
- **第一版补丁系列**：
  1. RISC-V KVM 选择 `KVM_VFIO`。
  2. 编译并运行 generic add/del、重复绑定和 VM close 路径。
  3. 若一致性平台上空 hook 足够，先保持最小实现。
  4. non-coherent 平台的 per-VM assignment count、vCPU entry/exit cache policy 单独提交。
  5. irq-bypass 由 `VIRT-07` 负责，不进入本系列。
- **阻塞与风险**：
  - VFIO/IOMMUFD 直通环境和可靠的 DMA coherency 描述。
  - 不能假设所有 RISC-V 平台一致性相同。
  - cache maintenance 必须与 DMA API、Zicbom 或 vendor CMO provider 协调。
- **验证**：
  - QEMU RISC-V IOMMU + vfio-pci，或 mock VFIO file。
  - add/del、重复绑定、VM close、group detach、错误回滚。
  - coherent 与 non-coherent group，KASAN 和 lockdep。
- **维护者与列表**：VFIO、KVM core、RISC-V KVM、IOMMU。
- **原始补丁与先例**：
  - [KVM: x86: Decouple device assignment from IRQ bypass](https://patchwork.kernel.org/project/kvm/patch/20250611224604.313496-55-seanjc@google.com/)
  - [2026-07 generic KVM/VFIO 生命周期修订](https://lore.kernel.org/linux-arm-kernel/20260706085229.979525-4-seiden@linux.ibm.com/)
  - [generic KVM VFIO implementation](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/virt/kvm/vfio.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)

<a id="virt-07"></a>
### VIRT-07：IMSIC irq-bypass/direct-injection 生命周期与测试

- **分类与状态**：G2，P1，`unclaimed`，总分 23；原始架构为 x86+arm64。
- **六维评分**：impact=3，generality=5，readiness=4，validation=4，hardware-independence=5，acceptance=2；**总分=23**。
- **注册表归并说明**：本条是唯一主条目，已吸收 KVM/IOMMU 报告中的 `AIA-01`、`AIA-03` 和 IRQ 报告中的 `IST-09`。本文不再单列 `irq_set_vcpu_affinity()` 的另一份候选。
- **价值判断**：RISC-V 已有 AIA/IMSIC guest-file 生命周期，但没有 KVM irq-bypass consumer、producer retarget 和失败回滚。功能系列和 selftests 必须作为同一主线的两个可独立评审阶段。
- **基线证据**：
  - RISC-V 未选择 `HAVE_KVM_IRQ_BYPASS`。
  - `aia_imsic.c` 的 guest-file release/update 路径存在 producer 重定向和 IOMMU mapping 待实现点。
  - generic `irqfd_test` 已进入 RISC-V common tests，真正缺的是 AIA HWACCEL 和 direct-injection 专项测试。
- **精确落点**：
  - `arch/riscv/kvm/aia_imsic.c:kvm_riscv_vcpu_aia_imsic_update()`
  - `kvm_riscv_vcpu_aia_imsic_release()`
  - `virt/kvm/eventfd.c:kvm_arch_irq_bypass_*()`
  - `kernel/irq/manage.c:irq_set_vcpu_affinity()`
  - `drivers/irqchip/irq-riscv-imsic-platform.c`
  - `tools/testing/selftests/kvm/riscv/`
- **RISC-V 缺口**：
  - vCPU 从一个 hart 迁移到另一个 hart 时，VFIO/eventfd producer 不能原子切换到新的 IMSIC VS-file。
  - producer add 失败、route 更新和 teardown 没有 rollback。
  - AIA EMUL/AUTO/HWACCEL、WFI、MSI、迁移和 no-AIA fallback 缺少专项回归。
- **移植方式**：复用 irq-bypass token、producer/consumer 和 routing-update 生命周期，不复制 GIC ITS 或 x86 IRTE/APIC 数据结构。
- **第一版补丁系列**：
  1. 增加 RISC-V KVM irq-bypass consumer add/del。
  2. 让 irqfd 保存 producer，并实现 stop → retarget → start。
  3. 迁移失败时恢复旧 target 或降级到 software file。
  4. 将 `irq_set_vcpu_affinity()` 与 VS-file 生命周期绑定。
  5. 后续 selftests 覆盖 AIA capability、config freeze、MSI injection、WFI、迁移和 irqfd race。
- **阻塞与风险**：
  - AIA HWACCEL、VFIO producer 和 `VIRT-08` MSI translation。
  - routing update 必须遵守 KVM irqfd/SRCU/锁顺序。
  - HGEI 资源不足时测试必须 skip 或回退，不应误报功能失败。
- **验证**：
  - VFIO MSI → irqfd → IMSIC，循环迁移 vCPU hart。
  - 迁移窗口持续发 MSI，验证不丢失、不重复、不写入旧 VS-file。
  - producer add 失败、route replace、deassign、VM teardown。
  - AIA EMUL/AUTO/HWACCEL 和 no-AIA VM。
- **维护者与列表**：RISC-V KVM/AIA、KVM irqfd、IRQ bypass、VFIO、IRQ core。
- **原始补丁与先例**：
  - [irqbypass: Take ownership of producer/consumer token tracking](https://patchwork.kernel.org/project/kvm/patch/20250516230734.2564775-4-seanjc@google.com/)
  - [KVM: arm64: Set irqfd producer to enable vLPI routing updates](https://patchwork.kernel.org/project/kvm/patch/20260623081433.21250-1-leixiang@kylinos.cn/)
  - [KVM: Nullify irqfd producer when add_producer() fails](https://patchwork.kernel.org/project/kvm/patch/20260622075103.35164-1-leixiang@kylinos.cn/)
  - [KVM selftests eventfd/KVM_IRQFD helpers](https://patchwork.kernel.org/project/kvm/patch/20250522235223.3178519-13-seanjc@google.com/)
  - [arm64 direct-injected vLPI 压力测试](https://patchwork.kernel.org/project/kvm/patch/20251120140305.63515-13-mdittgen@amazon.de/)

<a id="virt-08"></a>
### VIRT-08：RISC-V IOMMU MSI page table/MRIF 与 AIA/VFIO

- **分类与状态**：G4，P1，`unclaimed`，总分 19；原始架构为 arm64。
- **六维评分**：impact=5，generality=3，readiness=3，validation=3，hardware-independence=2，acceptance=3；**总分=19**。
- **价值判断**：代码边界清晰，但属于明确的基础设施依赖。没有 RISC-V IOMMU MSI translation，就无法把设备 MSI 安全地定向到 guest IMSIC file，`VIRT-07` 也只能停留在软件或模拟路径。
- **基线证据**：`iommu-bits.h` 已定义 MSI page table、MRIF、guest interrupt file、`msiptp`、mask 和 pattern；驱动没有分配、编程或失效这些结构。
- **精确落点**：
  - `drivers/iommu/riscv/iommu-bits.h:struct riscv_iommu_msipte`
  - device context 中的 `msiptp`、`msi_addr_mask`、`msi_addr_pattern`
  - `arch/riscv/kvm/aia_imsic.c`
  - IOTINVAL 和 device attach/detach 路径
- **RISC-V 缺口**：设备 MSI 无法由 RISC-V IOMMU 受控重定向到 guest IMSIC VS-file，阻塞 VFIO direct injection 和 AIA irq-bypass。
- **移植方式**：借鉴 ARM ITS/SMMU 和 x86 interrupt-remapping 的生命周期与安全边界，但使用 RISC-V IOMMU MSI PTE/MRIF 规范实现。
- **第一版补丁系列**：
  1. 按 capability 为设备分配 MSI translation table。
  2. 实现 MSI PTE 创建、更新、撤销和精确 IOTINVAL。
  3. 提供只允许内核使用的“更新单个 guest interrupt target”驱动 API。
  4. KVM/VFIO glue 在 irqfd route 更新和 vCPU 迁移时调用。
  5. MRIF 和高级聚合能力在基础 MSI PTE 稳定后提交。
- **阻塞与风险**：
  - 硬件 MSI capability、IMSIC guest files、VFIO 和 `VIRT-07`。
  - 必须阻止 guest 构造任意 host MSI address。
  - detach、reset 和 VM teardown 必须先撤销 translation，再释放 VS-file。
- **验证**：
  - QEMU 或真实硬件设备向 guest IMSIC 发 MSI。
  - VS-file 切换、设备解绑、FLR、VM teardown。
  - invalid MSI PTE、旧 target、恶意地址和 IOTINVAL 丢失故障注入。
- **维护者与列表**：RISC-V IOMMU、RISC-V KVM/AIA、VFIO、IOMMU core。
- **原始补丁与先例**：
  - [KVM: Pass new routing entries and irqfd when updating IRTEs](https://patchwork.kernel.org/project/kvm/patch/20250611224604.313496-5-seanjc@google.com/)
  - [arm64 direct-injected vLPI 压力测试](https://patchwork.kernel.org/project/kvm/patch/20251120140305.63515-13-mdittgen@amazon.de/)
  - [RISC-V IOMMU MSI table definitions](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/riscv/iommu-bits.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n682)

## 7. RISC-V IOMMU、SVA、PRI 与 IOMMUFD

<a id="virt-09"></a>
### VIRT-09：IOMMU fault queue、PRI/IOPF 与 page response

- **分类与状态**：G1，P1，`unclaimed`，总分 23；原始架构为 shared。
- **六维评分**：impact=4，generality=4，readiness=4，validation=4，hardware-independence=4，acceptance=3；**总分=23**。
- **价值判断**：应拆成两个系列。第一阶段结构化 fault reporting 依赖低、源码明确保留了未来处理入口；第二阶段 PRI/IOPF 依赖 PASID/PDT、ATS 和设备 page-request 能力。
- **基线证据**：
  - `riscv_iommu_fault()` 明确标注 future fault handling，仅打印 warning。
  - `struct riscv_iommu_pq_record`、`EN_PRI` 和 ATS `PRGR` 命令已经定义。
  - 驱动没有 page-request queue、IOPF group 或 `.page_response`。
- **精确落点**：
  - `drivers/iommu/riscv/iommu.c:riscv_iommu_fault()`
  - `riscv_iommu_fltq_process()`
  - `iommu_report_device_fault()`
  - `drivers/iommu/riscv/iommu-bits.h:struct riscv_iommu_pq_record`
  - `drivers/iommu/io-pgfault.c:iopf_group_response()`
- **RISC-V 缺口**：
  - fault record 不能映射到 `struct device` 和 domain，VFIO/IOMMUFD 无法收到结构化 fault。
  - PCIe PRI page request 不能进入 Linux IOPF queue，也无法返回 success、invalid 或 failure response。
- **移植方式**：第一阶段直接实现 generic IOMMU fault API；第二阶段按 IOPF group 和 page-response contract 接入 PRI，不复制 SMMU event queue 格式。
- **第一版补丁系列**：
  1. 建立 DID 到 device/domain 的受生命周期保护查找。
  2. 解析 read/write/execute/private 和 fault address。
  3. 调用 generic fault handler；无 handler 时保留 rate-limited log。
  4. remove/unbind 与 fault IRQ 同步。
  5. PRI queue、IOPF 和 page response 作为第二系列。
- **阻塞与风险**：
  - device context 生命周期和 fault IRQ 并发。
  - PRI 阶段依赖 PCI PRI/ATS、SVA/PASID 和 IOPF queue。
  - 错误 response 必须终止或重试正确 transaction，不能造成设备永久 stall。
- **验证**：
  - DMA 到 unmapped IOVA、无效 DDT/PTE、权限错误。
  - handler 收到正确 device、address、permission 和 reason。
  - unbind/remove 与 fault 并发。
  - PRI 阶段测试 partial group、last-page、invalid PASID、timeout 和 page response。
- **维护者与列表**：RISC-V IOMMU、IOMMU core、SVA/IOPF、PCI/VFIO。
- **原始补丁与先例**：
  - [IOMMU driver 显式声明 fault-reporting 能力](https://lore.kernel.org/linux-arm-kernel/3-v3-e5d08e2d551e+109-iommu_set_fault_jgg@nvidia.com/)
  - [IOMMU fault device quarantine/reset 生命周期](https://lore.kernel.org/linux-arm-kernel/745da1a819eb943f2519e660c8bcfde715885c6c.1779161849.git.nicolinc@nvidia.com/)
  - [PRI/IOPF response 类型显式化](https://lore.kernel.org/linux-arm-kernel/6c713c724fa09bf5a1b5e2247c633e516036f079.1779944354.git.nicolinc@nvidia.com/)
  - [RISC-V 当前 fault 处理入口](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/riscv/iommu.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n520)

<a id="virt-10"></a>
### VIRT-10：SVA、PASID 与 process-directory table

- **分类与状态**：G2，P1，`unclaimed`，总分 23；原始架构为 arm64。
- **六维评分**：impact=3，generality=5，readiness=4，validation=4，hardware-independence=5，acceptance=2；**总分=23**。
- **价值判断**：RISC-V IOMMU 规范和位定义已经提供 PDT/PASID 基础，但 Linux driver 尚未实现 SVA 生命周期。应先交付受限的 kernel-managed PASID 模型，再讨论 device-owned PASID space。
- **基线证据**：驱动注释明确说明 SVA/PASID 尚未合入；`riscv_iommu_ops` 没有 `domain_alloc_sva`，domain ops 没有 `set_dev_pasid`。
- **精确落点**：
  - `drivers/iommu/riscv/iommu.c:riscv_iommu_ops`
  - `RISCV_IOMMU_DC_TC_PDTV`
  - PDT modes `PD8`、`PD17`、`PD20`
  - `iommu_sva_bind_device()`
  - mmu_notifier、PSCID 和 PASID allocator
- **RISC-V 缺口**：设备不能使用进程虚拟地址空间；PDT、PASID 到 IOSATP/PSCID、device attach/detach 和 mm teardown 均为空。
- **移植方式**：复用 generic SVA API 和 ARM SMMU 的生命周期测试，不复制 SMMU STE/CD 表示。
- **第一版补丁系列**：
  1. 仅支持 kernel-managed global PASID。
  2. 仅支持 single-device SVA。
  3. 分配并管理 PDT。
  4. 实现 `domain_alloc_sva`、`set_dev_pasid`、detach 和 mm teardown。
  5. device-owned PASID space 和多层 PASID namespace 留到后续。
- **阻塞与风险**：
  - CPU/IOMMU 页表格式兼容性。
  - ATS、`VIRT-09` IOPF 和 mm PASID 生命周期。
  - ASID、PSCID、PASID 是不同命名空间，不能直接复用整数。
- **验证**：
  - SVA test device 访问进程 VA。
  - fork、exec、mm exit、unbind、PASID reuse。
  - mmu_notifier invalidation 和并发 DMA。
  - PDT walk KUnit 和 fault/IOPF 联动。
- **维护者与列表**：RISC-V IOMMU、IOMMU SVA/IOPF。
- **原始补丁与先例**：
  - [每设备 PASID 空间的 SVA 模型](https://lore.kernel.org/linux-arm-kernel/20260520150743.727106-1-joonwonkang@google.com/)
  - [RISC-V IOMMU ops 当前状态](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/riscv/iommu.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n1484)
  - [RISC-V PDT definitions](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/riscv/iommu-bits.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n386)

<a id="virt-11"></a>
### VIRT-11：IOMMUFD `hw_info`、nested HWPT 与 VMID/GSCID 协调

- **分类与状态**：G4，P1，`unclaimed`，总分 19；原始架构为 x86+arm64。
- **六维评分**：impact=5，generality=3，readiness=3，validation=3，hardware-independence=2，acceptance=3；**总分=19**。
- **价值判断**：这是一个三阶段主候选，而不是一个巨型系列。`hw_info` 是近期可独立提交的 UAPI 能力；nested HWPT 和 KVM VMID/GSCID 协调属于后续基础设施。
- **基线证据**：
  - Intel、AMD 和 SMMUv3 已实现 `iommu_ops.hw_info`。
  - RISC-V 没有 `iommu_hw_info_riscv` UAPI 类型。
  - RISC-V IOMMU 已定义 IOHGATP、GSCID 和 IOTINVAL，但没有 `domain_alloc_nested` 或 `cache_invalidate_user`。
  - KVM VMID allocator 与 IOMMU GSCID 没有关联。
- **精确落点**：
  - `drivers/iommu/riscv/iommu.c:riscv_iommu_ops`
  - `include/uapi/linux/iommufd.h`
  - `pt_iommu_riscv_64_hw_info()`
  - `drivers/iommu/iommufd/hw_pagetable.c`
  - `riscv_iommu_iodir_iotinval()`
  - `arch/riscv/kvm/vmid.c`
  - `arch/riscv/kvm/mmu.c:kvm_riscv_mmu_update_hgatp()`
- **RISC-V 缺口**：
  - VMM 无法枚举 page-table modes、address widths、Svnapot、Svpbmt、ATS、AMO_HWAD、MSI/MRIF、PASID 和 GSCID。
  - IOMMUFD 无法创建 guest-managed first stage + host-managed G-stage 的 nested HWPT。
  - assigned device 的 IOMMU G-stage 与 CPU G-stage 没有统一 tag 和 invalidation 生命周期。
- **移植方式**：按 UAPI → nested HWPT → KVM/IOMMU tag coordination 三个独立阶段推进。
- **第一版补丁系列**：
  1. 定义版本化 `struct iommu_hw_info_riscv`。
  2. 实现 `.hw_info`，只暴露稳定能力和 page-table format。
  3. 使用 length negotiation 和 reserved fields 保持前向兼容。
  4. nested alloc data、userspace invalidation 和 GSCID allocator 另开系列。
  5. KVM VMID pin/get/put 与 HFENCE/IOTINVAL 协调最后实现。
- **阻塞与风险**：
  - UAPI 必须与 IOMMUFD 维护者先达成字段边界。
  - nested 阶段依赖 PSCID/GSCID allocator、ATS invalidation，支持 PASID 时还依赖 `VIRT-10`。
  - 硬件不能共享 tag 时必须支持双 tag + 双失效，而不是强行复用同一编号。
- **验证**：
  - IOMMUFD mock 和真实 RISC-V IOMMU 的 `hw_info` 一致性。
  - 旧 userspace 小 buffer、未知 future field 和 length negotiation。
  - nested selftests、attach rollback、GSCID reuse、ATS device。
  - 高频 VMID rollover、CPU/device 并发访问同一 GPA、memslot unmap 和 VM teardown。
- **维护者与列表**：IOMMUFD、RISC-V IOMMU、RISC-V KVM、VFIO。
- **原始补丁与先例**：
  - [IOMMUFD vIOMMU/HW queue UAPI 演进](https://lore.kernel.org/linux-arm-kernel/dab4ace747deb46c1fe70a5c663307f46990ae56.1752126748.git.nicolinc@nvidia.com/)
  - [按 attachment 构造 nested invalidation plan](https://lore.kernel.org/linux-arm-kernel/eee884e734230ccdf8592a2dcd6962060e83b750.1773733797.git.nicolinc@nvidia.com/)
  - [attach 显式传递旧 domain](https://lore.kernel.org/linux-arm-kernel/7f760e795097e3052da82abf410c6ee963e4c62b.1761017765.git.nicolinc@nvidia.com/)
  - [SMMUv3/KVM 共享 VMID 与 broadcast TLB maintenance](https://lore.kernel.org/linux-arm-kernel/20250319173202.78988-6-shameerali.kolothum.thodi@huawei.com/)
  - [RISC-V IOMMUFD hw-info helper 落点](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/riscv/iommu.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n1289)

<a id="virt-12"></a>
### VIRT-12：基于 `AMO_HWAD` 的 DMA dirty tracking

- **分类与状态**：G1，P1，`unclaimed`，总分 23；原始架构为 arm64。
- **六维评分**：impact=4，generality=4，readiness=4，validation=4，hardware-independence=4，acceptance=3；**总分=23**。
- **价值判断**：这是 VFIO/IOMMUFD live migration 的关键缺口。RISC-V IOMMU 已声明 `AMO_HWAD` capability，但 generic_pt RISC-V format 和 domain 没有 dirty ops。
- **基线证据**：
  - `RISCV_IOMMU_CAPABILITIES_AMO_HWAD` 已定义。
  - `drivers/iommu/generic_pt/fmt/riscv.h` 没有 D-bit dirty read/clear/set。
  - RISC-V paging domain 没有发布 `struct iommu_dirty_ops`。
- **精确落点**：
  - `drivers/iommu/generic_pt/fmt/riscv.h`
  - `drivers/iommu/generic_pt/iommu_pt.h`
  - `drivers/iommu/riscv/iommu.c:riscv_iommu_alloc_paging_domain()`
  - 精确 IOTINVAL 路径
- **RISC-V 缺口**：设备 DMA dirty bitmap 无法由 IOMMUFD 获取和清理，阻塞 assigned-device live migration。
- **移植方式**：借鉴 ARM hardware dirty-bitmap 的批量读取、失败回退和 huge mapping 处理，不移植 HDBSS 指令或 ARM 页表格式。
- **第一版补丁系列**：
  1. generic_pt RISC-V format 增加 D-bit read、clear、set。
  2. 仅当硬件声明 `AMO_HWAD` 时发布 dirty support。
  3. 实现 enable/disable、read 和 read-and-clear。
  4. 清 D 后执行精确 IOTINVAL。
  5. Svnapot leaf 按完整映射组报告 dirty。
- **阻塞与风险**：
  - 必须确认规范中的原子 A/D 更新和 clear 后同步规则。
  - 不能在无 `AMO_HWAD` 平台上软件假装支持。
  - dirty clear 与并发 DMA 的竞态必须符合 IOMMUFD contract。
- **验证**：
  - IOMMUFD dirty bitmap selftest。
  - 设备 DMA 写 4K、huge 和 Svnapot 映射。
  - `NO_CLEAR`、read-and-clear、并发 DMA、stop-copy。
  - 不具备 `AMO_HWAD` 的设备正确拒绝能力。
- **维护者与列表**：RISC-V IOMMU、generic_pt、IOMMUFD/VFIO。
- **原始补丁与先例**：
  - [generic hardware dirty-cleaning hook 的失败回退模型](https://lore.kernel.org/linux-arm-kernel/20260629111820.1873540-8-leo.bras@arm.com/)
  - [KVM: arm64: Add hardware-accelerated dirty-bitmap cleaning routine](https://patchwork.kernel.org/project/kvm/patch/20260629111820.1873540-9-leo.bras@arm.com/)
  - [RISC-V AMO_HWAD capability](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/riscv/iommu-bits.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b#n55)

<a id="virt-13"></a>
### VIRT-13：RISC-V vIOMMU、vEVENTQ 与 HW queue

- **分类与状态**：G4，P2，`unclaimed`，总分 14；原始架构为 x86+arm64。
- **六维评分**：impact=4，generality=3，readiness=2，validation=2，hardware-independence=1，acceptance=2；**总分=14**。
- **价值判断**：这是 P2 长期项。IOMMUFD core 已有 vIOMMU、vEVENTQ 和 HW queue，但 RISC-V 还缺 `hw_info`、nested HWPT、IOPF 和 guest-visible ABI，不能从 queue mmap 反向开始实现。
- **基线证据**：ARM SMMUv3 和 AMD 有 driver glue；RISC-V 没有 `iommufd_viommu_ops`、UAPI type 或 queue glue。
- **精确落点**：
  - `drivers/iommu/iommufd/viommu.c`
  - `drivers/iommu/iommufd/eventq.c`
  - RISC-V command、fault、page-request queues
  - RISC-V nested domain alloc/invalidate structures
- **RISC-V 缺口**：VMM 无法虚拟化 RISC-V IOMMU 控制面，也无法把 guest command queue、fault/PQ event 和 nested domain 接入 IOMMUFD。
- **移植方式**：复用 IOMMUFD 对象、依赖和 event 生命周期；RISC-V guest-visible queue descriptor 必须依据自身规范重新定义。
- **第一版补丁系列**：
  1. 在 `VIRT-11` 完成后增加 RISC-V vIOMMU object。
  2. 只接 nested domain allocation，不开放 HW queue mmap。
  3. 第二阶段增加 vEVENTQ。
  4. 第三阶段在安全模型明确后开放受控 HW queue。
- **阻塞与风险**：
  - `VIRT-09` IOPF、`VIRT-11` `hw_info`/nested HWPT。
  - queue pinning、overflow、lost event 和 destroy dependency。
  - guest descriptor 必须经过完整校验，不能让 guest 直接控制 host queue。
- **验证**：
  - 先用 IOMMUFD mock selftests。
  - 再用 QEMU RISC-V IOMMU。
  - queue overflow、lost event、malformed descriptor、destroy ordering、VM reset。
- **维护者与列表**：IOMMUFD、RISC-V IOMMU。
- **原始补丁与先例**：
  - [IOMMUFD vIOMMU event/command/HW queue series](https://lore.kernel.org/linux-arm-kernel/dab4ace747deb46c1fe70a5c663307f46990ae56.1752126748.git.nicolinc@nvidia.com/)
  - [IOMMUFD vIOMMU core](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/iommufd/viommu.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)
  - [IOMMUFD event queue core](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/iommufd/eventq.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)

## 8. Nested Virtualization

<a id="virt-14"></a>
### VIRT-14：nested KVM architectural state 与 shadow G-stage

- **分类与状态**：G4，P2，`unclaimed`，总分 14；原始架构为 arm64。
- **六维评分**：impact=4，generality=3，readiness=2，validation=2，hardware-independence=1，acceptance=2；**总分=14**。
- **价值判断**：这是长期架构能力，不应被拆成零散 CSR 补丁。最小闭环必须同时考虑可迁移 nested state、L2 启动、L1 G-stage walk、shadow G-stage 和 HFENCE 失效；nested AIA 不作为独立主候选。
- **基线证据**：
  - arm64 mainline 已有 `KVM_CAP_ARM_EL2`、nested state、nested stage-2 和 pseudo-TLB。
  - RISC-V 没有 nested capability/UAPI。
  - `vcpu_sbi_replace.c` 明确说明 nested virtualization 尚未实现。
  - 当前 RISC-V 只有单一 canonical G-stage root。
- **精确落点**：
  - `arch/riscv/kvm/vcpu_config.c`
  - `arch/riscv/kvm/vcpu_exit.c`
  - `arch/riscv/kvm/vcpu_sbi_replace.c`
  - `arch/riscv/kvm/vcpu_switch.S`
  - `arch/riscv/kvm/gstage.c`
  - `arch/riscv/kvm/mmu.c`
  - `arch/riscv/kvm/tlb.c`
- **RISC-V 缺口**：
  - L1 guest hypervisor 无法拥有虚拟 H-extension 状态或运行 L2。
  - 即使补 CSR，L2 GPA 也无法经过 L1 G-stage 与 host G-stage 合成。
  - L1 修改页表后没有 pseudo-TLB 或 nested HFENCE 失效。
- **移植方式**：借鉴 arm64 nested KVM 的 UAPI、状态迁移、shadow stage-2 和 pseudo-TLB 设计，不移植 EL2 sysreg、VNCR 或 ARM page-table walker。
- **第一版补丁系列**：
  1. 定义可迁移的虚拟 H-extension state 和 capability/UAPI。
  2. 支持最小 L2 启动、异常注入、ecall、timer 和 virtual-instruction trap。
  3. 首版 shadow G-stage 只支持 4K leaf，不支持 guest huge/NAPOT。
  4. 为每个 L1 `hgatp` root 建立 shadow root。
  5. 处理 `HFENCE.GVMA/VVMA`、memslot invalidation 和跨 vCPU共享页表。
  6. nested AIA 维持为后续观察项，不重复建立 `VIRT-*`。
- **阻塞与风险**：
  - RISC-V nested virtualization 规范和 QEMU/KVM userspace ABI。
  - capability 与 nested-state ioctl 的接口选择。
  - L1 page-table page 来源可能是普通 memory 或 guest_memfd。
  - 跨 vCPU共享 L1 page table 的 notifier 和缓存一致性。
- **验证**：
  - 自包含 L1 test hypervisor 启动最小 L2。
  - ecall、page fault、virtual instruction、timer、HFENCE。
  - L1 动态修改 L2 mapping/permission。
  - migration state save/restore、跨 vCPU、memslot move/delete。
  - KASAN、KCSAN 和长时间 nested stress。
- **维护者与列表**：RISC-V KVM、KVM UAPI、RISC-V KVM MMU。
- **原始补丁与先例**：
  - [arm64 nested hypervisor timer selftest 蓝图](https://lore.kernel.org/linux-arm-kernel/20250512105251.577874-4-gankulkarni@os.amperecomputing.com/)
  - [arm64 VNCR pseudo-TLB](https://lore.kernel.org/linux-arm-kernel/20250514103501.2225951-8-maz@kernel.org/)
  - [arm64 nested implementation](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/kvm/nested.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)
  - [RISC-V canonical G-stage](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kvm/gstage.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)

## 9. CoVE 与 Private Memory

<a id="virt-15"></a>
### VIRT-15：CoVE private memory、guest_memfd 与 memory attributes

- **分类与状态**：G4，P2，`unclaimed`，总分 14；原始架构为 arm64。
- **六维评分**：impact=4，generality=3，readiness=2，validation=2，hardware-independence=1，acceptance=2；**总分=14**。
- **价值判断**：CoVE 不能从“选择 Kconfig”开始。正确顺序是 shared guest_memfd → memory-attribute 状态机 → 页所有权转换 → monitor donate/share/reclaim。首阶段必须能够拒绝不安全转换。
- **基线证据**：
  - RISC-V 未选择 `KVM_GUEST_MEMFD` 或 `KVM_GENERIC_MEMORY_ATTRIBUTES`。
  - RISC-V 没有 `HAVE_KVM_ARCH_GMEM_*` hooks。
  - mainline 与 linux-next 没有 CoVE KVM 实现。
- **精确落点**：
  - `arch/riscv/kvm/Kconfig`
  - `arch/riscv/kvm/mmu.c`
  - `kvm_arch_post_set_memory_attributes()`
  - `kvm_arch_gmem_prepare()`
  - `kvm_gmem_populate()`
  - `kvm_arch_gmem_invalidate()` / gmem folio free 生命周期
  - 未来 CoVE SBI/monitor glue
- **RISC-V 缺口**：无法表达 shared/private GPA、页所有权转换、private G-stage mapping、populate/reclaim 和 VMM memory-fault exit。
- **移植方式**：借鉴 ARM CCA/pKVM 和 x86 TDX/SEV 的通用 guest_memfd/memory-attribute contract，只迁移状态机、不迁移固件 ABI、页表格式或 attestation 机制。
- **第一版补丁系列**：
  1. 以前置 `VIRT-03` shared/mappable guest_memfd 为基础。
  2. 选择 generic memory attributes，但首版只做状态跟踪和严格拒绝。
  3. 定义 shared → private 和 private → shared 的 arch hooks、unmap、HFENCE 和 rollback。
  4. 定义 populate、free/reclaim、VM teardown 和 poisoned folio 生命周期。
  5. 最后接入 CoVE monitor 的 donate/share/reclaim。
- **阻塞与风险**：
  - 稳定 CoVE ABI、页状态转换和 monitor 错误模型。
  - host direct-map alias、cache flush、TLB flush 和 folio 生命周期。
  - assigned device DMA 到 private page 的隔离模型尚未完成；protected IOMMU/confidential DMA 不作为当前独立候选。
- **验证**：
  - shared/private 往返、失败回滚和重复转换。
  - memslot delete、VM teardown、poisoned folio。
  - 并发 vCPU、host access 和 DMA。
  - private page 不可由 host userspace mmap。
  - monitor 拒绝、超时和部分成功后的恢复。
- **维护者与列表**：RISC-V KVM、KVM guest_memfd、RISC-V confidential-computing/firmware、未来 CoVE monitor 维护者。
- **原始补丁与先例**：
  - [KVM: arm64: Expose support for private memory，2026 修订版](https://patchwork.kernel.org/project/kvm/patch/20260513131757.116630-26-steven.price@arm.com/)
  - [arm64 shared/private MMU notifier 范围](https://lore.kernel.org/linux-arm-kernel/20250213161426.102987-2-steven.price@arm.com/)
  - [KVM: Add capability for SET_MEMORY_ATTRIBUTES2 flags](https://patchwork.kernel.org/project/kvm/patch/20260428-gmem-inplace-conversion-v5-28-d8608ccfca22@google.com/)
  - [KVM: Rework gmem invalidate into gmem free-folio](https://patchwork.kernel.org/project/kvm/patch/20260626231416.3943216-5-seanjc@google.com/)
  - [guest_memfd stage-2 poisoned-folio selftest](https://patchwork.kernel.org/project/kvm/patch/20260602-memory-failure-mf-delayed-fix-v4-7-a5bc7db5a9b2@google.com/)

## 10. 实施路线与依赖分层

### 10.1 短期：可独立启动

以下工作不要求先完成完整 RISC-V IOMMU、AIA direct injection、nested 或 CoVE：

1. **`VIRT-01` KVM G-stage ptdump**：先只做 canonical G-stage；IOMMU dump 可后续。
2. **`VIRT-02` G-stage teardown**：解决锁内递归释放和调度延迟。
3. **`VIRT-04` 普通 userspace memory prefault**：先不支持 guest_memfd。
4. **`VIRT-03` shared/mappable guest_memfd**：严格排除 private memory。
5. **`VIRT-06` KVM/VFIO generic device API 第一阶段**：先在 coherent 或 mock 环境验证。
6. **`VIRT-09` 结构化不可恢复 fault reporting**：不在首版引入 PRI/IOPF。
7. **`VIRT-11` RISC-V IOMMUFD `hw_info`**：只提交稳定 UAPI 和 capability report。

推荐补丁批次：

| 批次 | 候选 | 目标 |
|---|---|---|
| A | `VIRT-01`、`VIRT-02` | 建立可观测性并消除 G-stage teardown 长临界区 |
| B | `VIRT-04` | 完成普通内存 prefault 和通用 selftest |
| C | `VIRT-03` | 完成 shared/mappable guest_memfd |
| D | `VIRT-06`、`VIRT-09` 第一阶段 | 接入 generic VFIO device API 和 IOMMU fault API |
| E | `VIRT-11` 第一阶段 | 定义 RISC-V IOMMUFD `hw_info` |

### 10.2 中期：依赖设备和跨子系统基础设施

- **`VIRT-05`**：等待 generic KVM userfault UAPI 稳定。
- **`VIRT-07`**：依赖 AIA HWACCEL、VFIO producer 和 MSI translation。
- **`VIRT-08`**：依赖真实 RISC-V IOMMU MSI capability 和 IMSIC guest file。
- **`VIRT-09` 第二阶段**：PRI/IOPF 依赖 PASID/PDT、ATS 和 page-request queue；完整可缺页 SVA 需要该阶段。
- **`VIRT-10`**：可先实现禁用 faulting 的 PDT/PASID attach；完整 SVA 依赖 `VIRT-09` 的 PRI/IOPF 和 mm/PASID 生命周期。
- **`VIRT-11` 第二、三阶段**：依赖 nested HWPT、GSCID allocator 和 KVM/IOMMU 失效协调。
- **`VIRT-12`**：依赖 `AMO_HWAD` 硬件和 live-migration 验证设备。

主要依赖关系：

```text
VIRT-03 shared guest_memfd
  └─> VIRT-15 CoVE/private memory

VIRT-06 KVM_VFIO
  ├─> VIRT-07 irq-bypass
  └─> VIRT-08 MSI translation

VIRT-09 fault reporting
  ├─> VIRT-10 PDT/PASID attach
  └─> VIRT-09 PRI/IOPF

VIRT-10 PDT/PASID + VIRT-09 PRI/IOPF + ATS
  └─> complete SVA

VIRT-11 hw_info
  └─> VIRT-11 nested HWPT
        ├─> VIRT-11 VMID/GSCID coordination
        └─> VIRT-13 vIOMMU

VIRT-08 MSI translation + VIRT-07 irq-bypass
  └─> VFIO direct injection
```

### 10.3 P2 长期项

- **`VIRT-13` vIOMMU**：必须晚于 `hw_info`、nested HWPT 和 IOPF。
- **`VIRT-14` nested KVM**：必须以完整状态/UAPI和 shadow G-stage 最小闭环为目标，不能只提交孤立 CSR。
- **`VIRT-15` CoVE**：必须晚于 shared guest_memfd，并以稳定 monitor ABI 和页所有权模型为前提。

这三项可以提前做 selftest skeleton、UAPI 讨论和 QEMU 模型验证，但不应以“RISC-V 已支持”作为近期里程碑。

## 11. 已排除的伪差距与归并项

以下项目不再作为独立贡献点：

| 项目 | 结论 | 证据或处理 |
|---|---|---|
| G-stage TLB batching | 已进入 mainline | commit `60aa6734f542` 已实现 RISC-V stage-2 TLB flush batching |
| hugetlb block mapping memslot bounds | 已进入 mainline | commit `49476d58f217` 已完成对应检查 |
| dirty-log write-fault fast path | 已进入 mainline | `7705be59eb2d`、`d7a26a0ba715`、`7dd416fdd3fb` 已提供原子 PTE 更新和 fast path |
| common MMU notifier locking | 已进入 mainline | commit `9090ba2e7cf8` 已让 RISC-V 使用通用 locking |
| generic `irqfd_test` | 已覆盖 RISC-V | 缺口是 AIA HWACCEL/direct-injection 专项测试，归入 `VIRT-07` |
| RISC-V IOMMU 基础 paging driver | 已存在 | 真正缺口是 fault、SVA、PRI、dirty、nested、vIOMMU 和 MSI virtualization |
| IRQ 报告 `IST-09` | 不单列 | 已归并到唯一主条目 `VIRT-07` |
| nested AIA | 不进入 15 项主表 | 同时依赖 `VIRT-14`、shadow G-stage 和 IMSIC ownership，保留为后续观察 |
| protected IOMMU/confidential DMA | 不进入 15 项主表 | 同时依赖 `VIRT-15`、protected device assignment、monitor 和 shared-page contract |

## 12. 验证矩阵

| ID | 最小验证环境 | 关键用例 | 通过标准 |
|---|---|---|---|
| `VIRT-01` | QEMU KVM + debugfs；IOMMU mock/硬件 | 4K/huge/PBMT/NAPOT、并发 map/unmap | 输出与真实 mapping 一致，无 UAF、锁告警或私有 PA 泄露 |
| `VIRT-02` | PREEMPT 内核 + 大稀疏 VM | 循环 VM create/destroy、并发 close | 最长不可抢占时间显著下降，无 stale translation 或 double free |
| `VIRT-03` | QEMU RISC-V KVM | gmem mmap、memslot move/delete、HWPOISON | shared gmem 正确映射和回收，private/gmem-only 明确拒绝 |
| `VIRT-04` | QEMU RISC-V KVM | prefault、hugetlb、notifier、signal | 映射正确；竞争返回 `-EAGAIN`；VM-dead 及时退出 |
| `VIRT-05` | generic userfault UAPI + QEMU | read/write/exec fault、取消和重入 | userspace 获得精确 fault，处理后 guest 可继续运行 |
| `VIRT-06` | mock VFIO 或 QEMU RISC-V IOMMU | add/del、重复绑定、VM close | generic KVM/VFIO 生命周期完整，coherency policy 不被误判 |
| `VIRT-07` | AIA HWACCEL + VFIO MSI | vCPU 迁移期间持续发 MSI | 不丢失、不重复、不写旧 VS-file；失败可回滚 |
| `VIRT-08` | RISC-V IOMMU MSI capability | MSI PTE update、detach、恶意地址 | 只能命中授权 guest IMSIC target，teardown 后无残留 translation |
| `VIRT-09` | RISC-V IOMMU fault injection | unmapped IOVA、invalid DDT/PTE、PRI | fault 与 device/domain 对应正确；page response 可恢复或终止 transaction |
| `VIRT-10` | SVA test device | fork/exec/mm exit、PASID reuse | 无 stale PASID/PDT；mm teardown 后设备不可继续访问旧地址空间 |
| `VIRT-11` | IOMMUFD selftests + RISC-V IOMMU | `hw_info`、nested attach、GSCID reuse | UAPI 向前兼容；无 stale CPU/IOMMU translation |
| `VIRT-12` | `AMO_HWAD` 硬件 + VFIO migration | dirty read/clear、Svnapot、并发 DMA | bitmap 不漏脏；clear 后同步正确；无能力设备拒绝支持 |
| `VIRT-13` | IOMMUFD mock + QEMU vIOMMU | queue overflow、恶意 descriptor、destroy | 对象依赖正确，队列不可越权，event 不静默丢失 |
| `VIRT-14` | L1 test hypervisor + QEMU/KVM | L2 boot、HFENCE、migration、跨 vCPU | L2 可运行并迁移；L1 页表更新不会留下 stale shadow mapping |
| `VIRT-15` | CoVE monitor/模拟器 | shared/private 往返、rollback、poison、DMA | 页所有权唯一，失败可恢复，private 页不可被 host userspace/DMA 越权访问 |

所有候选的通用验证要求：

- KASAN、KCSAN、lockdep 和必要的 fault injection。
- 架构 selftests 必须按 capability skip，不得把缺硬件误判为回归。
- 对 UAPI 候选验证旧 userspace、小 buffer、未知 flag 和 future field。
- 对页表、IOMMU 和 irq-bypass 候选验证 reset、hot-unplug、VM teardown 和错误回滚，而不仅是正常路径。

## 13. 维护者路由

建议根据实际 touched files 运行 `scripts/get_maintainer.pl`，以下为固定基线上的主要路由：

- **RISC-V KVM**：Anup Patel、Atish Patra；`kvm-riscv@lists.infradead.org`、`kvm@vger.kernel.org`、`linux-riscv@lists.infradead.org`。
- **RISC-V IOMMU / IOMMU core**：Tomasz Jeznach、Joerg Roedel、Will Deacon、Robin Murphy；`iommu@lists.linux.dev`。
- **IOMMUFD**：Jason Gunthorpe、Kevin Tian；`iommu@lists.linux.dev`。
- **VFIO**：Alex Williamson；`kvm@vger.kernel.org`、`iommu@lists.linux.dev`。
- **KVM core**：Paolo Bonzini 及对应 KVM 子系统评审者。
- **IRQ/AIA**：RISC-V irqchip/AIA、IRQ core 和 KVM irqfd/irq-bypass 维护者。

跨子系统系列应避免一次抄送所有列表并提交巨型 patchset。更可接受的拆分方式是：

1. 先由基础子系统合入独立能力，例如 IOMMU fault reporting、`hw_info` 或 MSI table API。
2. 再由 KVM/VFIO 系列消费该能力。
3. selftests 与功能补丁放在同一主题下，但保持可独立审阅。

## 14. 审计限制

- 本文是固定 mainline/linux-next 快照上的源码、调用链和邮件谱系审计，没有在具备 RISC-V IOMMU、AIA HWACCEL、VFIO 直通、nested 或 CoVE monitor 的真实硬件上完成功能验证。
- 原始 arm64/x86 补丁用于证明接口演进、错误模型和测试方法，不代表其寄存器、页表或中断控制器实现可以直接复制。
- Patchwork 状态不能单独证明补丁已合入、被拒绝或仍活跃；本文的 `unclaimed` 结论来自固定源码、linux-next 和邮件谱系交叉检查。
- 2026 年统计索引的完整逐补丁窗口截至 `2026-06-30`，本文另用邮件核验补充到 `2026-07-10`。
- nested、CoVE、vIOMMU、AIA direct injection 和 confidential DMA 的优先级会随规范、QEMU、固件和硬件支持变化，需要在实际开发前重新核验。

## 15. 基线与核心来源

- [Torvalds mainline `d96fcfe1b7f9`](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)
- [linux-next `bee763d5f341`](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=bee763d5f341b99cf472afeb508d4988f62a6ca1)
- [RISC-V KVM](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kvm?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)
- [RISC-V IOMMU](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/riscv?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)
- [IOMMUFD](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/iommu/iommufd?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)
- [KVM guest_memfd core](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/virt/kvm/guest_memfd.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)
- [KVM VFIO core](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/virt/kvm/vfio.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)
- [KVM irqfd/eventfd core](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/virt/kvm/eventfd.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)
