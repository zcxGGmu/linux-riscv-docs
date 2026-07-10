# linux-arm-kernel MMU / 内存管理补丁的 RISC-V 可移植性审计

## 范围与方法

- 时间范围：`2025-01-01T00:00:00Z`（含）至 `2026-07-11T00:00:00Z`（不含）；7 月 mbox 结束后的 142 封索引邮件已逐页补采。
- 数据源：`data/parsed/patches.jsonl` 与 `data/parsed/supplemental_patches.jsonl`，共 65,635 条唯一补丁邮件。
- 全量脚本筛选：同时匹配标题/描述中的 MMU、页表、TLB、ASID、VMID、内存属性、热插拔、IOMMU/SMMU、SVA/PASID、IOPF 等术语，以及 `arch/arm*/mm`、页表头文件、`mm/`、`drivers/iommu/`、`iommufd` 等路径。
- 初筛结果：5,296 个补丁版本、2,407 个规范化标题谱系；脚本先排除了 17,179 条仅修改 DTS、DT binding 或维护者数据的记录。
- 人工核查：逐项检查高价值候选的 `subject`、`description`、`touched_paths` 和 `lore_url`，排除稳定树通知、仅厂商设备支持、纯重命名和没有 RISC-V 复用价值的 ARM ISA 细节。
- 合并规则：同标题 v1-vN 仅保留最新修订；同一系列中承担同一机制的准备、实现和测试补丁合并为一个“贡献点”。
- 最终结果：45 个潜在贡献点，其中 21 个可直接共享或进入通用层，17 个需要在 RISC-V MMU/KVM 中重新实现，7 个依赖 RISC-V IOMMU、CoVE 或嵌套虚拟化基础。

难度定义：

- **低**：通用代码已覆盖 RISC-V，或仅需启用、补测试和少量适配。
- **中**：语义通用，但需要修改 RISC-V 页表、TLB、ASID 或 IOMMU 驱动。
- **高**：依赖尚未完整具备的硬件扩展、UAPI、机密虚拟化或嵌套虚拟化。

## A. 可直接共享或优先进入通用层

### 1. 统一页表析构与延迟释放生命周期

- **原始架构/子系统**：generic MM，覆盖 arm、arm64、RISC-V、x86 等。
- **原始补丁**：[mm: pgtable: introduce pagetable_dtor()](https://lore.kernel.org/linux-arm-kernel/47f44fff9dc68d9d9e9a0d6c036df275f820598a.1736317725.git.zhengqi.arch@bytedance.com/)
- **可移植点**：统一各级页表析构，把页表锁和页表页放到同一延迟释放生命周期，避免锁先释放而页表页仍由 RCU 延迟回收导致 UAF。
- **RISC-V 落点**：继续收敛 `arch/riscv/include/asm/pgalloc.h`、`arch/riscv/include/asm/tlb.h` 中可由 `pagetable_dtor()`、通用 `__tlb_remove_table()` 和 `__pgd_{alloc,free}` 覆盖的实现。
- **难度/阻塞**：低；重点验证 split page-table lock、RCU table free 和不同页表级别。
- **证据**：描述明确指出各架构析构逻辑仅在 `ptlock` 处理上不同，并点名防止 ptlock 与页表页释放时序造成的 UAF；路径包含 arm64、RISC-V 和 `include/asm-generic`。

### 2. 按 PTE 范围批量刷新 TLB

- **原始架构/子系统**：arm64/RISC-V/x86，generic MM rmap。
- **原始补丁**：[mm: Support tlbbatch flush for a range of PTEs](https://lore.kernel.org/linux-arm-kernel/20250214093015.51024-3-21cnbao@gmail.com/)
- **可移植点**：让 TLB batch 记录地址范围，而不是逐页追加刷新请求，为批量 unmap 和大 folio 回收减少 IPI/SBI 调用。
- **RISC-V 落点**：`arch/riscv/mm/tlbflush.c` 的 `arch_tlbbatch_add_pending()`、范围 `sfence.vma`/SBI RFENCE 选择和 `mm/rmap.c` 批量反向映射。
- **难度/阻塞**：低；补丁已直接修改 RISC-V，后续重点是大范围阈值和本地/远端 hart 策略。
- **证据**：路径直接包含 `arch/riscv/include/asm/tlbflush.h`、`arch/riscv/mm/tlbflush.c` 和 `mm/rmap.c`。

### 3. arm64/RISC-V 共享连续 HugeTLB 操作

- **原始架构/子系统**：arm64 + RISC-V，HugeTLB/连续 PTE。
- **原始补丁**：[mm: Use common huge_ptep_get() function for riscv/arm64](https://lore.kernel.org/linux-arm-kernel/20250321130635.227011-4-alexghiti@rivosinc.com/)
- **可移植点**：将 `huge_ptep_get`、`set_huge_pte_at`、clear、access-flags、wrprotect、clear-flush 等七组近似实现下沉到 `mm/hugetlb_contpte.c`。
- **RISC-V 落点**：继续以通用 `hugetlb_contpte` 为唯一实现，RISC-V 仅保留 NAPOT PTE 编解码和架构屏障钩子。
- **难度/阻塞**：低；需覆盖 Svnapot、非 NAPOT HugeTLB 和 dirty/access bit。
- **证据**：系列描述多次说明“两架构实现相同或几乎相同”；路径同时包含 arm64、RISC-V 和 `mm/hugetlb_contpte.c`。

### 4. 通用页表 dump 回调与热拔插锁

- **原始架构/子系统**：generic ptdump，arm64/RISC-V/s390/x86。
- **原始补丁**：[mm/ptdump: Split note_page() into level specific callbacks](https://lore.kernel.org/linux-arm-kernel/20250407053113.746295-2-anshuman.khandual@arm.com/)
- **可移植点**：用强类型的 PGD/P4D/PUD/PMD/PTE 回调代替假设 `pxd_val()` 为 `u64` 的接口，并在通用 walker 内持有 memory-hotplug 锁。
- **RISC-V 落点**：`arch/riscv/mm/ptdump.c` 直接使用通用回调和锁，不再在架构侧重复保护。
- **难度/阻塞**：低。
- **证据**：补丁路径直接包含 `arch/riscv/mm/ptdump.c`；配套热插拔补丁说明中间页表并发释放会造成 ptdump UAF。

### 5. 地址感知的 page_table_check 接口

- **原始架构/子系统**：generic page-table-check，arm64/RISC-V/x86。
- **原始补丁**：[mm/page_table_check: Reinstate address parameter in [__]page_table_check_pte_clear()](https://lore.kernel.org/linux-arm-kernel/20251219-pgtable_check_v18rebase-v18-8-755bc151a50b@linux.ibm.com/)
- **可移植点**：set/clear 和 user-accessible 检查保留虚拟地址及 `mm_struct`，避免假设所有权限信息都编码在 PTE 中。
- **RISC-V 落点**：保持 `arch/riscv/include/asm/pgtable.h` 的 page-table-check 包装器地址完整，为未来 Svnapot、PBMT、影子栈或地址相关权限检查留接口。
- **难度/阻塞**：低。
- **证据**：最新系列同时修改 arm64、RISC-V、x86、`include/linux/page_table_check.h` 和 `mm/page_table_check.c`。

### 6. 页表构造器获得 `mm_struct`

- **原始架构/子系统**：generic pgtable allocation，arm/arm64/RISC-V 等。
- **原始补丁**：[mm: Pass mm down to pagetable_{pte,pmd}_ctor](https://lore.kernel.org/linux-arm-kernel/20250408095222.860601-2-kevin.brodsky@arm.com/)
- **可移植点**：构造页表页时获得所属地址空间，为每-mm 元数据、页表统计、锁和安全策略提供上下文。
- **RISC-V 落点**：`arch/riscv/mm/init.c` 的 PTE/PMD/PUD/P4D 分配路径统一调用带 `mm` 的 ctor。
- **难度/阻塞**：低。
- **证据**：路径包含 `arch/riscv/mm/init.c`，系列另有 RISC-V PUD/P4D ctor 配套补丁。

### 7. 通用 lazy-MMU 与 pagewalk 批处理接口

- **原始架构/子系统**：generic MM/pagewalk，arm64/x86/powerpc。
- **原始补丁**：[mm: introduce generic lazy_mmu helpers](https://lore.kernel.org/linux-arm-kernel/20251215150323.2218608-8-kevin.brodsky@arm.com/)
- **可移植点**：为页表批量修改提供 enter/leave lazy-MMU 和 pre/post-PTE-table 回调，将屏障、TLB 同步和页表写合并。
- **RISC-V 落点**：评估在 `set_memory_*`、direct-map permission change、vmalloc page-table walk 中加入 RISC-V lazy-MMU 钩子。
- **难度/阻塞**：中；必须证明嵌套规则、抢占/中断上下文和远端 TLB 可见性。
- **证据**：路径覆盖 `include/linux/pagewalk.h`、`mm/pagewalk.c` 和多架构页表代码；arm64 系列用于降低 pageattr 逐 PTE 屏障成本。

### 8. young-bit 批量清除返回值标准化

- **原始架构/子系统**：generic MM，arm64/RISC-V/powerpc/parisc。
- **原始补丁**：[mm: change to return bool for ptep_clear_flush_young()/clear_flush_young_ptes()](https://lore.kernel.org/linux-arm-kernel/24af5144b96103631594501f77d4525f2475c1be.1774075004.git.baolin.wang@linux.alibaba.com/)
- **可移植点**：标准化“是否实际清除了 young/accessed 位”的返回值，避免无变化时进行不必要的 TLB 刷新和 reclaim 工作。
- **RISC-V 落点**：RISC-V A-bit 管理、large folio reclaim 和 `clear_flush_young_ptes()`。
- **难度/阻塞**：低；需兼容软件 A/D 与硬件 A/D 两种模式。
- **证据**：路径直接包含 `arch/riscv/include/asm/pgtable.h`。

### 9. `ioremap_prot()` 使用类型安全的 `pgprot_t`

- **原始架构/子系统**：generic ioremap，多架构。
- **原始补丁**：[mm/ioremap: Pass pgprot_t to ioremap_prot() instead of unsigned long](https://lore.kernel.org/linux-arm-kernel/20250218101954.415331-1-anshuman.khandual@arm.com/)
- **可移植点**：避免页保护属性在通用接口中退化为整数，提升 PBMT/缓存属性传递的类型安全。
- **RISC-V 落点**：`arch/riscv/include/asm/io.h`、ACPI ioremap 和 Svpbmt 属性组合。
- **难度/阻塞**：低；补丁已经包含 RISC-V 路径。
- **证据**：路径包含 `arch/riscv/include/asm/io.h`、`arch/riscv/kernel/acpi.c` 和 `mm/ioremap.c`。

### 10. DMA 同步发起与完成等待分离

- **原始架构/子系统**：arm64 + generic DMA/IOMMU。
- **原始补丁**：[dma-mapping: Separate DMA sync issuing and completion waiting](https://lore.kernel.org/linux-arm-kernel/20260228221316.59934-1-21cnbao@gmail.com/)
- **可移植点**：允许一批 cache maintenance 先异步发起，再统一等待完成，降低非一致性 DMA 的串行屏障成本。
- **RISC-V 落点**：非一致性平台的 `arch_sync_dma_*`、Zicbom/Zicboz 实现、`dma-iommu.c` 和 SWIOTLB。
- **难度/阻塞**：中；依赖平台 cache-block 操作和完成语义，必须保持 DMA direction 正确。
- **证据**：路径同时包含 arm64 cache/DMA、`drivers/iommu/dma-iommu.c` 和通用 DMA map ops。

### 11. 机密计算共享 DMA 属性

- **原始架构/子系统**：generic DMA/direct、机密计算。
- **原始补丁**：[dma-direct: make dma_direct_map_phys() honor DMA_ATTR_CC_SHARED](https://lore.kernel.org/linux-arm-kernel/yq5ase5th627.fsf@kernel.org/)
- **可移植点**：把“必须以共享/解密状态暴露给设备”的 DMA 属性贯穿 direct map、DMA-BUF、NVMe、P2PDMA 和原子池。
- **RISC-V 落点**：CoVE/TEE guest 的 shared-page 转换、SWIOTLB shared pool 和设备 DMA 映射。
- **难度/阻塞**：高；依赖 RISC-V CoVE 页所有权和共享转换 ABI。
- **证据**：补丁路径跨 DMA-BUF、块层、NVMe、P2PDMA 和通用 DMA 头文件，说明它不是单一设备修复。

### 12. 通用 IOMMU 页表 dump 设施

- **原始架构/子系统**：generic IOMMU/debug。
- **原始补丁**：[iommu/debug: Add IOMMU page table dump debug facility](https://lore.kernel.org/linux-arm-kernel/20250814093005.2040511-2-xiaqinxin@huawei.com/)
- **可移植点**：为 IOMMU domain 提供统一页表遍历、格式化和 debugfs 输出。
- **RISC-V 落点**：为 `drivers/iommu/riscv/` 实现 io-pgtable dump ops，输出 DDT/PDT 和 IOVA leaf 属性。
- **难度/阻塞**：中；需要避免与 map/unmap 并发和泄露敏感地址。
- **证据**：路径包含 `drivers/iommu/iommu.c`、`include/linux/io_ptdump.h`、`mm/io_ptdump.c`。

### 13. io-pgtable KUnit 化

- **原始架构/子系统**：ARM io-pgtable selftests。
- **原始补丁**：[iommu/io-pgtable-arm-selftests: Use KUnit](https://lore.kernel.org/linux-arm-kernel/20251103123355.1769093-5-smostafa@google.com/)
- **可移植点**：将页表格式测试从驱动内自检迁移到可独立运行、可注入失败、可覆盖边界的 KUnit。
- **RISC-V 落点**：建立 RISC-V IOMMU DDT/PDT、NAPOT/superpage、权限、unmap 和 invalidation 的 KUnit 套件。
- **难度/阻塞**：中；需要先把 RISC-V IOMMU 页表操作解耦成可测试接口。
- **证据**：补丁新增 KUnit 配置并独立 `io-pgtable-arm-selftests.c`。

### 14. IOMMU deferred attach 锁定与状态一致性

- **原始架构/子系统**：generic IOMMU core。
- **原始补丁**：[iommu: Lock group->mutex in iommu_deferred_attach()](https://lore.kernel.org/linux-arm-kernel/cb38f91526596f4efd0cd1cffa50b4c1b334f7a4.1765834788.git.nicolinc@nvidia.com/)
- **可移植点**：把 group、device、default domain 和 deferred attach 的状态迁移放在明确锁域内。
- **RISC-V 落点**：RISC-V IOMMU 驱动接入 deferred attach、probe 和 domain switch 时直接遵循通用锁约束。
- **难度/阻塞**：低；核心代码直接共享，驱动只需避免锁外读取状态。
- **证据**：最新修订仅修改 `drivers/iommu/iommu.c`，说明是通用核心修复。

### 15. domain attach 显式传递旧 domain

- **原始架构/子系统**：generic IOMMU core，多驱动。
- **原始补丁**：[iommu: Pass in old domain to attach_dev callback functions](https://lore.kernel.org/linux-arm-kernel/7f760e795097e3052da82abf410c6ee963e4c62b.1761017765.git.nicolinc@nvidia.com/)
- **可移植点**：让驱动以事务方式完成旧/新 domain 切换，支持 RMR、blocked/identity domain 和失败回滚。
- **RISC-V 落点**：`drivers/iommu/riscv/` 的 attach 回调、设备 DDT 更新和 IOTLB invalidation。
- **难度/阻塞**：中；需定义切换期间设备 DMA 阻断和失效顺序。
- **证据**：路径覆盖 ARM SMMU、AMD、Intel、Apple、RISC-V 等多驱动和 `include/linux/iommu.h`。

### 16. 设备故障隔离与 reset 生命周期

- **原始架构/子系统**：generic IOMMU core。
- **原始补丁**：[iommu: Add iommu_report_device_broken() to quarantine a broken device](https://lore.kernel.org/linux-arm-kernel/745da1a819eb943f2519e660c8bcfde715885c6c.1779161849.git.nicolinc@nvidia.com/)
- **可移植点**：硬件恢复失败后将设备切入 blocked/quarantine domain，并与 reset prepare/done 生命周期联动。
- **RISC-V 落点**：RISC-V IOMMU fatal fault、command queue timeout、DDT 更新失败后的设备隔离。
- **难度/阻塞**：中；要求硬件有可靠的 DMA 阻断模式。
- **证据**：补丁修改通用 `iommu.c`/`iommu.h`；同系列包含 reset result 和硬件故障恢复回调。

### 17. IOMMU fault 报告能力显式化

- **原始架构/子系统**：generic IOMMU fault API。
- **原始补丁**：[iommu: Allow drivers to say if they use report_iommu_fault()](https://lore.kernel.org/linux-arm-kernel/3-v3-e5d08e2d551e+109-iommu_set_fault_jgg@nvidia.com/)
- **可移植点**：由驱动声明旧式 fault 回调是否有效，避免 core 对不支持的路径作错误假设。
- **RISC-V 落点**：RISC-V IOMMU 在基础 fault、IOPF、PRI 三条路径之间明确能力和回调归属。
- **难度/阻塞**：低。
- **证据**：路径覆盖通用 IOMMU core 和多种 ARM IOMMU 驱动。

### 18. IOMMU 页表页 freelist 与 IOTLB gather 统一

- **原始架构/子系统**：generic IOMMU memory management。
- **原始补丁**：[iommu: Change iommu_iotlb_gather to use iommu_page_list](https://lore.kernel.org/linux-arm-kernel/11-v4-c8663abbb606+3f7-iommu_pages_jgg@nvidia.com/)
- **可移植点**：unmap 时把待释放页表页放入结构化 page list，在 invalidation 完成后统一回收，并支持 sub-page allocator。
- **RISC-V 落点**：RISC-V IOMMU 页表页缓存、批量 unmap、IOTINVAL 完成与内存回收。
- **难度/阻塞**：中；需保证 command queue completion 之前不复用页表页。
- **证据**：系列描述包含 formalize freelist、sub-page allocation 和 gather 改造。

### 19. 长度感知的 IOVA 到物理地址查询

- **原始架构/子系统**：generic IOMMU/IOMMUFD。
- **原始补丁**：[iommu: introduce iova_to_phys_length in iommu_domain_ops](https://lore.kernel.org/linux-arm-kernel/20260603151804.1963871-2-guanghuifeng@linux.alibaba.com/)
- **可移植点**：查询不仅返回物理地址，还返回当前 leaf 映射可连续覆盖的长度，减少 IOMMUFD unmap/查询的逐页 walk。
- **RISC-V 落点**：RISC-V IOMMU superpage/NAPOT leaf walker 和 IOMMUFD unmap。
- **难度/阻塞**：中；必须正确处理多级页表、非对齐 IOVA 和权限边界。
- **证据**：系列后续直接让 IOMMUFD 使用该接口进行高效 unmap。

### 20. IOMMUFD cache invalidation 数组由 core 迭代

- **原始架构/子系统**：generic IOMMUFD。
- **原始补丁**：[iommufd: Iterate the cache invalidation array in the core](https://lore.kernel.org/linux-arm-kernel/c19b7508428e9f14d6997ff9f5a41d9d5ba6cde5.1783539724.git.nicolinc@nvidia.com/)
- **可移植点**：把用户数组复制、条目长度/数量上限和循环放到 core，驱动只处理单条失效命令。
- **RISC-V 落点**：RISC-V vIOMMU/IOMMUFD cache invalidation UAPI，映射到 `IOTINVAL.VMA/GVMA` 等命令。
- **难度/阻塞**：中；依赖 RISC-V IOMMU nesting/UAPI。
- **证据**：路径集中在 `iommufd/hw_pagetable.c` 和通用头文件，配套补丁增加 entry 数量和长度上限。

### 21. 每设备 PASID/SSID 空间的 SVA 模型

- **原始架构/子系统**：generic IOMMU SVA。
- **原始补丁**：[iommu: Allow device driver to use its own PASID space for SVA](https://lore.kernel.org/linux-arm-kernel/20260520150743.727106-1-joonwonkang@google.com/)
- **可移植点**：允许设备驱动管理自己的 process address-space ID，而不是强制所有设备共享统一 PASID 分配器。
- **RISC-V 落点**：RISC-V IOMMU process-directory ID、PCIe PASID 与 hart ASID 的映射和 SVA bind/unbind。
- **难度/阻塞**：高；依赖完整 RISC-V IOMMU SVA、IOPF 和 PCIe PASID 支持。
- **证据**：补丁修改 `drivers/iommu/iommu-sva.c` 和 `include/linux/iommu.h`，语义不绑定 ARM。

## B. 需要在 RISC-V MMU/KVM 中重新实现

### 22. 内核 block mapping 的权限变更

- **原始架构/子系统**：arm64 pageattr。
- **原始补丁**：[arm64: Enable permission change on arm64 kernel block mappings](https://lore.kernel.org/linux-arm-kernel/20250917190323.3828347-2-yang@os.amperecomputing.com/)
- **可移植点**：pagewalk 遇到 block/large leaf 时安全拆分，再执行 RO/RW/X/NX 等权限变更。
- **RISC-V 落点**：`arch/riscv/mm/pageattr.c`、linear-map 和 vmalloc 的 PMD/PUD superpage 拆分。
- **难度/阻塞**：中；需处理 SFENCE.VMA、失败回滚和并发访问。
- **证据**：路径同时修改 arm64 pageattr、`include/linux/pagewalk.h` 和 `mm/pagewalk.c`，表明核心方法可泛化。

### 23. 内存热拔插的页表生命周期约束

- **原始架构/子系统**：arm64 MM/hotplug。
- **原始补丁**：[arm64/mm: Reject memory removal that splits a kernel leaf mapping](https://lore.kernel.org/linux-arm-kernel/20260309025725.455004-3-anshuman.khandual@arm.com/)
- **可移植点**：热移除前检查是否会切开仍在使用的大 leaf；页级建立 vmemmap/linear map，并在释放 hot-removed 页表时调用 dtor。
- **RISC-V 落点**：`arch/riscv/mm/init.c` 的 memory hotplug add/remove、vmemmap 和 direct-map page-table teardown。
- **难度/阻塞**：中；取决于 RISC-V memory hot-remove 完整度和 superpage 布局。
- **证据**：同谱系包含 page-level vmemmap/linear populate、leaf split 拒绝和 pagetable dtor。

### 24. 热拔插 unmap 的范围 TLB 批处理

- **原始架构/子系统**：arm64 TLB/hotplug。
- **原始补丁**：[arm64/mm: Enable batched TLB flush in unmap_hotplug_range()](https://lore.kernel.org/linux-arm-kernel/20260309025725.455004-2-anshuman.khandual@arm.com/)
- **可移植点**：先拆除整段 direct-map 页表，再按范围一次性完成 TLB 同步，而不是每个 leaf 单独广播。
- **RISC-V 落点**：RISC-V memory hot-unplug 中的 `flush_tlb_kernel_range()` 与 SBI RFENCE 合并。
- **难度/阻塞**：中；需保证页表页回收晚于远端 hart 完成失效。
- **证据**：最新谱系有 16 个版本，后续补丁继续改为 range-based flush 并优化 PMD/PUD 范围。

### 25. 基于 mm 活跃 CPU 的本地/广播 TLB 选择

- **原始架构/子系统**：arm64 ASID/TLB。
- **原始补丁**：[arm64: tlbflush: Don't broadcast if mm was only active on local cpu](https://lore.kernel.org/linux-arm-kernel/20260523134710.3827956-1-linu.cherian@arm.com/)
- **可移植点**：跟踪地址空间是否只在当前 CPU 活跃，满足条件时使用本地失效，ASID rollover 时重置状态。
- **RISC-V 落点**：`arch/riscv/mm/context.c`、`tlbflush.c`，在本地 `sfence.vma` 与 SBI remote fence 之间选择。
- **难度/阻塞**：中；必须覆盖迁核、lazy TLB、CPU hotplug 和 ASID rollover。
- **证据**：路径包含 arm64 `mmu_context.h`、`context.c` 和 `tlbflush.h`；配套补丁专门修复 rollover 状态。

### 26. 页面复用与 stale TLB 竞态

- **原始架构/子系统**：arm64 fault/TLB。
- **原始补丁**：[arm64, tlbflush: don't TLBI broadcast if page reused in write fault](https://lore.kernel.org/linux-arm-kernel/20251114085403.101552-3-ying.huang@linux.alibaba.com/)
- **可移植点**：在写故障中区分“旧映射仍可能被远端使用”和“页面已经在本地安全复用”，避免多余广播，同时封堵 stale entry 仍有效的理论竞态。
- **RISC-V 落点**：COW/write-protect fault、folio reuse 和远端 `sfence.vma` 决策。
- **难度/阻塞**：中高；需要内存模型证明和压力测试。
- **证据**：路径覆盖 arm64 PTE、TLB、contpte 和 fault，实现横跨映射状态与失效策略。

### 27. 连续 PTE 的 BBM 优化映射到 Svnapot

- **原始架构/子系统**：arm64 contpte/BBML2。
- **原始补丁**：[arm64/mm: Elide tlbi in contpte_convert() under BBML2](https://lore.kernel.org/linux-arm-kernel/20250625113435.26849-5-miko.lenczewski@arm.com/)
- **可移植点**：在硬件允许更宽松 break-before-make 时，批量转换连续映射并省略不必要 TLBI；同时提供 split/convert 正确性约束。
- **RISC-V 落点**：Svnapot PTE 与普通 PTE/superpage 之间的转换、拆分和权限修改。
- **难度/阻塞**：高；RISC-V 没有 BBML2 同名保证，必须按规范重新证明可见性和 SFENCE.VMA 要求。
- **证据**：系列经过 9 个版本，并同时增加 CPU/SMMU BBM capability 与 contpte 转换逻辑。

### 28. 从 linear map 移除或只读映射内核数据别名

- **原始架构/子系统**：arm64 kernel linear map hardening。
- **原始补丁**：[arm64: Map the kernel data/bss read-only in the linear map](https://lore.kernel.org/linux-arm-kernel/20260119164747.1402434-8-ardb+git@google.com/)
- **可移植点**：避免内核镜像的 data/bss 同时存在可写 linear alias，最终可完全 unmap 该别名。
- **RISC-V 落点**：`arch/riscv/mm/init.c` 的 kernel image、direct-map alias 和 secondary CPU early mapping。
- **难度/阻塞**：中高；需审计 early boot、kexec、hibernation、BPF text 和模块访问。
- **证据**：同系列同时提供“只读 linear alias”和“完全 unmap data/bss alias”两个阶段。

### 29. 页表写保护与受控写入口

- **原始架构/子系统**：arm64 kernel protection keys/page-table hardening。
- **原始补丁**：[arm64: kpkeys: Guard page table writes](https://lore.kernel.org/linux-arm-kernel/20260526-kpkeys-v8-21-eaaacdacc67c@arm.com/)
- **可移植点**：默认将内核页表只读，仅在受控 helper 中短暂开放写权限，并保护 `init_pg_dir`、vmemmap 页表。
- **RISC-V 落点**：可先实现软件受控的页表写 API和只读 direct-map alias；未来结合 ePMP/Sspmp 或其他内核隔离扩展。
- **难度/阻塞**：高；RISC-V 缺少与 ARM permission overlay/kpkeys 等价的低成本硬件机制。
- **证据**：路径修改 arm64 PTE 写入口和 fault 处理，系列另有保护 init_pg_dir、vmemmap page tables。

### 30. 所有页表写经由类型化访问器

- **原始架构/子系统**：arm64 pgtable/D128 准备。
- **原始补丁**：[arm64/mm: Route all pgtable writes via ptdesc_set()](https://lore.kernel.org/linux-arm-kernel/20260224051153.3150613-11-anshuman.khandual@arm.com/)
- **可移植点**：禁止散落的裸 `WRITE_ONCE`，统一从 ptdesc/pxdp accessor 读写页表，便于扩展更宽 PTE、原子更新和调试。
- **RISC-V 落点**：审计 `arch/riscv/include/asm/pgtable.h` 和 `arch/riscv/mm/`，统一 PTE/PMD/PUD/PGD 访问器。
- **难度/阻塞**：中；当前 64 位 PTE 不强制需要，但可降低 Svnapot/PBMT/未来宽 PTE 演进成本。
- **证据**：后续系列将各级 `READ_ONCE()` 替换为 `pmdp_get()`、`pudp_get()`、`pgdp_get()`。

### 31. 大 leaf 拆分、保留与失败处理

- **原始架构/子系统**：arm64 kernel page-table mapping。
- **原始补丁**：[arm64: mm: Handle invalid large leaf mappings correctly](https://lore.kernel.org/linux-arm-kernel/20260330161705.3349825-3-ryan.roberts@arm.com/)
- **可移植点**：拆分大 leaf 时区分 invalid/table/leaf，保留已有 table 和非连续描述符，并在原子上下文避免分配睡眠。
- **RISC-V 落点**：RISC-V direct map、kernel pageattr、kexec 临时页表和 memory hotplug 的 superpage split。
- **难度/阻塞**：中高；需设计预分配或两阶段拆分。
- **证据**：相关谱系包含 “Don't sleep in split_kernel_leaf_mapping”、preserve table mappings 和 invalid large leaf 修复。

### 32. huge-vmalloc 默认启用

- **原始架构/子系统**：arm64 vmalloc/pageattr。
- **原始补丁**：[arm64/mm: Enable huge-vmalloc by default](https://lore.kernel.org/linux-arm-kernel/20251212042701.71993-3-dev.jain@arm.com/)
- **可移植点**：在架构支持安全拆分和权限调整后，让 vmalloc 使用 PMD/PUD 大映射以降低 TLB 压力。
- **RISC-V 落点**：`arch/riscv/include/asm/vmalloc.h`、`arch_vmap_pmd_supported()` 和 pageattr split。
- **难度/阻塞**：中；必须先保证模块、BPF、set_memory_* 和 debug-pagealloc 可拆分大映射。
- **证据**：路径同时修改 arm64 pageattr、通用 vmalloc 头和 `mm/vmalloc.c`。

### 33. 零页及 huge-zero folio 的只读 linear alias

- **原始架构/子系统**：arm64 pageattr/hardening。
- **原始补丁**：[arm64/mm: make huge zero folio read-only in linear map](https://lore.kernel.org/linux-arm-kernel/20260527035607.14919-3-xueyuan.chen21@gmail.com/)
- **可移植点**：共享零页不应在 direct map 中保留可写别名，防止单点写破坏所有只读映射。
- **RISC-V 落点**：`empty_zero_page`、huge zero folio 初始化和 direct-map permission adjustment。
- **难度/阻塞**：中；需要处理早期分配、kexec 和调试配置。
- **证据**：系列另有将普通 zero page 移至 rodata 的补丁。

### 34. ASID rollover 空 bitmap 防御

- **原始架构/子系统**：arm64 ASID allocator。
- **原始补丁**：[arm64/mm: harden ASID allocator against empty bitmap after rollover](https://lore.kernel.org/linux-arm-kernel/20260219113715.8001-1-redacherkaoui67@gmail.com/)
- **可移植点**：rollover 后分配器不应假设 bitmap 必有可用位；异常情况下应重试、扩展或安全失败。
- **RISC-V 落点**：`arch/riscv/mm/context.c` 的 ASID generation、CPU hotplug 和 rollover 路径。
- **难度/阻塞**：低到中；需构造小 ASID 位宽和高并发压力测试。
- **证据**：补丁只修改 arm64 `mm/context.c`，问题模型与 RISC-V ASID generation allocator 同类。

### 35. 页故障 tracepoint

- **原始架构/子系统**：arm64 page fault observability。
- **原始补丁**：[arm64: mm: Add page fault trace points](https://lore.kernel.org/linux-arm-kernel/61063f55e2c2df6db69cb63eac9d6653f38fbfbd.1747649899.git.namcao@linutronix.de/)
- **可移植点**：记录 fault address、访问类型、用户/内核态、处理结果和延迟，为 MMU 性能与异常诊断提供稳定接口。
- **RISC-V 落点**：`arch/riscv/mm/fault.c`，覆盖 instruction/load/store page fault 和 guest page fault。
- **难度/阻塞**：低；需控制 tracepoint 热路径成本和地址泄露。
- **证据**：该标题经历 9 个修订，说明字段和 ABI 经过较充分讨论。

### 36. fixmap/KASAN 页表移出 BSS

- **原始架构/子系统**：arm64 early page tables/linker layout。
- **原始补丁**：[arm64: Move fixmap and kasan page tables to end of kernel image](https://lore.kernel.org/linux-arm-kernel/20260529150150.1670604-26-ardb+git@google.com/)
- **可移植点**：将早期页表放在明确、可对齐和可保护的镜像尾部，避免 BSS 清零或重映射阶段破坏。
- **RISC-V 落点**：RISC-V `vmlinux.lds.S`、fixmap、KASAN early page tables 和 boot page-table ownership。
- **难度/阻塞**：中；需验证 XIP、KASLR、不同页表级别和 relocatable kernel。
- **证据**：路径包含 linker script、fixmap、KASAN init 和 mmu 头文件。

### 37. vmalloc 区域的加密/共享属性转换

- **原始架构/子系统**：arm64 CCA/Realm pageattr。
- **原始补丁**：[arm64: Add encrypt/decrypt support for vmalloc regions](https://lore.kernel.org/linux-arm-kernel/20250811005036.714274-3-sdonthineni@nvidia.com/)
- **可移植点**：属性转换不能只支持 linear map；对 vmalloc 需要逐页解析物理地址、转换所有权并同步别名。
- **RISC-V 落点**：CoVE guest 的 `set_memory_shared/private`、vmalloc bounce buffers 和驱动共享内存。
- **难度/阻塞**：高；依赖 RISC-V CoVE/TEE 页转换 ABI和失败回滚。
- **证据**：描述明确指出现有 `set_memory_encrypted/decrypted()` 对非 linear-map 地址返回 `-EINVAL`，新 helper 用 `vmalloc_to_page()` 处理。

### 38. 嵌套虚拟化中的软件 pseudo-TLB

- **原始架构/子系统**：KVM arm64 nested virtualization。
- **原始补丁**：[KVM: arm64: nv: Add pseudo-TLB backing VNCR_EL2](https://lore.kernel.org/linux-arm-kernel/20250514103501.2225951-8-maz@kernel.org/)
- **可移植点**：缓存由 L1 guest 提供的虚拟控制结构映射，并让 MMU notifier、跨 vCPU TLBI 和 fixmap teardown 能使其失效。
- **RISC-V 落点**：未来 RISC-V nested KVM 对 VS/HS 控制结构、`vsatp`/`hgatp` 影子映射或嵌套 vCPU 状态页的缓存。
- **难度/阻塞**：高；RISC-V KVM 嵌套虚拟化 ABI和硬件扩展尚需稳定。
- **证据**：配套补丁增加跨 vCPU S1 TLB invalidation primitive，并使用原子计数跟踪 VM 内是否存在缓存映射。

## C. 依赖 RISC-V IOMMU、CoVE 或硬件队列基础

### 39. 将 io-pgtable 算法与内核运行时解耦

- **原始架构/子系统**：ARM io-pgtable/SMMUv3。
- **原始补丁**：[iommu/io-pgtable-arm: Factor kernel specific code out](https://lore.kernel.org/linux-arm-kernel/20251117184815.1027271-5-smostafa@google.com/)
- **可移植点**：把页表格式、walk、map/unmap 与内核内存分配、锁和日志解耦，使同一页表算法能在 host kernel 和受保护 hypervisor 中复用。
- **RISC-V 落点**：将 RISC-V IOMMU DDT/PDT/page-table 操作拆成纯算法层、Linux glue 和 CoVE monitor glue。
- **难度/阻塞**：中高；需先清理现有驱动的分配器和 command queue 耦合。
- **证据**：路径新增 `io-pgtable-arm-kernel.c`，后续 pKVM 补丁新增独立 hyp allocation hooks。

### 40. 受保护 hypervisor 控制 IOMMU

- **原始架构/子系统**：arm64 pKVM/SMMUv3。
- **原始补丁**：[iommu/arm-smmu-v3-kvm: Add SMMUv3 driver](https://lore.kernel.org/linux-arm-kernel/20260501111928.259252-12-smostafa@google.com/)
- **可移植点**：host 去特权后，将 IOMMU 寄存器、队列和资源所有权交给 EL2；影子 host stream table、command queue 和 CPU stage-2 页表。
- **RISC-V 落点**：CoVE security monitor 或 HS/更高特权层控制 RISC-V IOMMU，host 通过受控接口配置设备 DMA。
- **难度/阻塞**：高；依赖 RISC-V CoVE、IOMMU 硬件、设备分配和可信 monitor ABI。
- **证据**：系列包含 SMMUv3 skeleton、MMIO emulation、CMDQ shadow、stream-table shadow、CPU stage-2 shadow、nesting 和设备接管。

### 41. vIOMMU 事件队列、命令队列、硬件队列与 mmap

- **原始架构/子系统**：generic IOMMUFD/vIOMMU。
- **原始补丁**：[iommufd/viommu: Add IOMMUFD_CMD_HW_QUEUE_ALLOC ioctl](https://lore.kernel.org/linux-arm-kernel/dab4ace747deb46c1fe70a5c663307f46990ae56.1752126748.git.nicolinc@nvidia.com/)
- **可移植点**：以对象和 refcount 管理 vEVENTQ、vCMDQ/vQUEUE/HW_QUEUE，并允许 VMM mmap 硬件 MMIO/queue 区域。
- **RISC-V 落点**：把 RISC-V IOMMU command queue、fault queue 和虚拟设备上下文接入 IOMMUFD vIOMMU。
- **难度/阻塞**：高；需要 RISC-V vIOMMU 驱动、用户态 VMM 协议和安全的 queue memory pinning。
- **证据**：系列分别定义事件 FD、虚拟/硬件 queue ioctl、依赖关系、mmap 生命周期和 selftests。

### 42. CPU 与 IOMMU 的共享 VMID/TLB 广播

- **原始架构/子系统**：SMMUv3 nested/IOMMUFD/KVM。
- **原始补丁**：[iommu/arm-smmu-v3: Enable broadcast TLB maintenance](https://lore.kernel.org/linux-arm-kernel/20250319173202.78988-6-shameerali.kolothum.thodi@huawei.com/)
- **可移植点**：CPU 和 IOMMU 使用同一 VMID/tag 时，可由共享广播失效维护嵌套 stage-2，一致管理 tag 生命周期。
- **RISC-V 落点**：协调 KVM `hgatp.VMID` 与 RISC-V IOMMU G-stage tag，评估 `HFENCE.GVMA`/IOTINVAL 联动。
- **难度/阻塞**：高；取决于硬件是否支持跨 agent 广播或必须显式双重失效。
- **证据**：配套补丁直接从 KVM 获取 pinned VMID 用于 SMMU stage-2 domain。

### 43. 按 attachment 构造完整失效计划

- **原始架构/子系统**：SMMUv3 ASID/VMID/ATS invalidation。
- **原始补丁**：[iommu/arm-smmu-v3: Populate smmu_domain->invs when attaching masters](https://lore.kernel.org/linux-arm-kernel/eee884e734230ccdf8592a2dcd6962060e83b750.1773733797.git.nicolinc@nvidia.com/)
- **可移植点**：domain 不只保存一个 tag，而是按 SVA、stage-1、stage-2、nested 和 ATS master 预计算所需失效集合。
- **RISC-V 落点**：RISC-V IOMMU domain attach 时建立 PASID/PSCID/GSCID、device ATS 和 nested translation 的 invalidation descriptor 集。
- **难度/阻塞**：高；依赖 ATS、SVA、nesting 和精确 tag 生命周期。
- **证据**：描述明确列出 S1 ASID、S2 VMID、ATS SID 和 nested vSMMU 的不同 invalidation 组合。

### 44. PRI/IOPF 响应类型显式化

- **原始架构/子系统**：SMMUv3 PRI/IOPF。
- **原始补丁**：[iommu/arm-smmu-v3: Submit CMDQ_OP_PRI_RESP for IOPF event](https://lore.kernel.org/linux-arm-kernel/6c713c724fa09bf5a1b5e2247c633e516036f079.1779944354.git.nicolinc@nvidia.com/)
- **可移植点**：generic fault flags 显式区分“阻塞设备事务的 stall”与“来自 PRI queue 的 page request”，据此选择正确响应命令。
- **RISC-V 落点**：RISC-V IOMMU page-request/fault queue 到 Linux IOPF 的事件分类和 response opcode。
- **难度/阻塞**：高；依赖 PCIe PRI、IOPF 和硬件 page-request queue。
- **证据**：描述指出仅凭 master capability 无法区分两类 `IOMMU_FAULT_PAGE_REQ`，因此新增通用 flag。

### 45. ATS walker 与聚合 PTE 视图的一致性

- **原始架构/子系统**：arm64 contpte + SMMU/ATS。
- **原始补丁**：[arm64: contpte: fix set_access_flags() no-op check for SMMU/ATS faults](https://lore.kernel.org/linux-arm-kernel/20260305-contpte-fault-loop-v2-1-0216f0026d7f@nvidia.com/)
- **可移植点**：CPU 可按一组连续 PTE 聚合 A/D 状态，但 IOMMU/ATS walker 可能逐 descriptor 解释；不能用聚合值判断单个 leaf 已完成权限更新。
- **RISC-V 落点**：Svnapot 与 RISC-V IOMMU/ATS 组合下，A/D、只读和 fault resolution 必须检查目标 leaf 的真实状态。
- **难度/阻塞**：高；需明确 CPU MMU、IOMMU 和 PCIe ATS 对 NAPOT/聚合映射的共同语义。
- **证据**：描述给出具体故障循环：兄弟 PTE 的 dirty 位使聚合读取看似已更新，但 SMMU 逐项读取时目标 PTE 仍为只读。

## 建议实施顺序

1. **近期直接收益**：1-9、12-18、34-35。以通用 MM/IOMMU API、测试和诊断为主，硬件依赖最低。
2. **RISC-V MMU 性能与正确性**：22-27、30-33。重点是 large leaf split、TLB batching、ASID rollover、Svnapot 和 pageattr。
3. **内核内存硬化**：28-29、36-37。先完成 linear alias 审计，再考虑页表写保护和 CoVE 属性转换。
4. **RISC-V IOMMU 基础**：19-21、39、43-45。优先补齐 page-table test、失效描述、SVA/PASID 和 IOPF。
5. **长期虚拟化**：38、40-42。需要与 RISC-V nested KVM、CoVE 和 vIOMMU UAPI 联合设计。

## 排除说明

- 未收录仅增加 SoC/设备节点、`iommus` 属性、reserved-memory 节点或 binding compatible 的 DTS/DT-binding 补丁。
- 未收录仅支持单一厂商 IOMMU 型号、没有可抽象机制的寄存器表和兼容字符串更新。
- 未收录 stable-tree “Patch has been added” 通知、回复邮件和纯回退通知。
- 未将同一机制的准备补丁、重命名、机械转换和 selftest 分别计数；例如 arm64/RISC-V HugeTLB 通用化七个补丁计为一个贡献点，pKVM SMMUv3 完整系列计为一个贡献点。
