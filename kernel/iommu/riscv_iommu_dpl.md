# RISC-V IOMMU 脏页日志（DPL）提案工作说明书

# 引言

IOMMU G-stage脏页日志功能扩展了AMO_HWAD功能，以在IOHGATP页表遍历（PTW）期间记录脏页地址。每当PTW更新脏位时，相应的Guest物理地址（GPA）和IOHGATP值将分别记录到GPA缓冲区和IOHGATP缓冲区中。类似于ARM的FEAT_HDBSS或Intel的PML。

# 现有扩展为何不足？

现有的IOMMU规范及其AMO_HWAD机制（类似于ARM的FEAT_DBM或Intel的EPT脏位）未能为G-stage转换提供任何硬件辅助的脏页日志功能（类似于ARM的FEAT_HDBSS或Intel的PML）。

# 定义

- HDBSS - ARM的硬件脏状态跟踪结构（Hardware Dirty State Tracking Structure）
- PML - Intel的页修改日志（Page Modifications Logging）
- DBM - ARM中硬件更新访问标志和脏状态的脏位修改器（Dirty Bit Modifier）
- EPT脏位 - Intel的扩展页表脏位（Extended Page Tables Dirty Bit）
- IOHGATP - RISC-V IOMMU的IO超虚拟化程序Guest地址转换与保护（IO Hypervisor Guest Address Translation and Protection）
- GPA - Guest物理地址（Guest Physical Address）
- AMO_HWAD - RISC-V IOMMU的原子内存操作，用于硬件访问与脏位（Atomic Memory Operations for Hardware Access & Dirty bits）

# 背景

实时迁移是现代数据中心和云计算环境中的关键能力，它支持运行中的虚拟机（VM）在物理主机之间无缝迁移，而不会中断服务，并支持灵活的云资源调度。该过程通常包括两个阶段：预拷贝阶段（在VM在源主机上执行时，将内存页从源主机传输到目标主机）和后拷贝阶段（在VM切换后，从源主机获取缺失的页面，由执行期间的页故障触发）。

在VM实时迁移的预拷贝阶段，ARM的FEAT_HDBSS（硬件脏状态跟踪结构）和Intel的PML（页修改日志）等高级硬件脏日志功能已成为标准。这些功能允许处理器在任何写操作更新第二阶段页表（ARM的stage-2，Intel的EPT）中的脏状态时，自动将脏页的Guest物理地址（GPA）追加到专用硬件管理的日志缓冲区或队列中。此过程在页表遍历期间透明发生，对于允许的写操作不会产生额外的故障，从而避免了软件页故障的性能惩罚，极大地提高了迁移效率并降低了主机CPU负载。

然而，目前尚无商业可用的IOMMU支持脏日志功能。因此，系统采用基于软件的位图扫描来跟踪设备导致的脏页——这种方法会产生大量CPU开销，破坏迁移吞吐量，并削弱CPU端硬件加速所实现的效率提升。

在CPU和IOMMU共享G-stage表场景[1]中，直通DMA设备重用CPU的G-stage页表，IOMMU必须原生支持脏日志功能以与CPU协作。只有通过这种硬件协调方法，才能实现跨CPU和设备发起内存访问的全面、系统级的脏页跟踪。

为弥合这一关键差距，我们向RISC-V IOMMU[2]提出G-stage脏页日志（DPL）扩展。该扩展可以通过在iohgatp页表遍历（PTW）期间扩展AMO_HWAD功能来实现。当PTW更新脏位时，相应的Guest物理地址（GPA）和iohgatp值将分别记录到GPA缓冲区和IOHGATP缓冲区中。这些缓冲区由脏日志队列维护，脏日志队列使用若干内存映射寄存器。脏日志队列遵循RISC-V IOMMU CQ/FQ/PQ设计。以下是示意图：

![image.png](https://lists.riscv.org/g/sig-datacenter/attachment/214/0)

[1] https://lore.kernel.org/linux-iommu/20231202091211.13376-1-yan.y.zhao@.../

[2] https://docs.google.com/document/d/1o0sCdeDmHcVrZypAX_vpnHcaj2sexjmWLql-i6S_mB0

# 目标

本任务组（TG）将定义RISC-V IOMMU脏页日志（DPL）扩展，具体目标如下：

- 确定内存映射寄存器设计。
- 确定内存数据结构设计。
  - 队列格式
  - GPA缓冲区格式
  - IOHGATP缓冲区格式
- 建立QEMU + Linux概念验证原型。
- 建立硬件原型以演示可实现性。
- 与CPU脏页日志TG合作，统一GPA缓冲区格式。

---

# 技术深度分析报告

## 1. 架构分析 (Architecture Analysis)

### 1.1 DPL 对 AMO_HWAD 能力的扩展机制

DPL 提案的核心设计理念是**复用并扩展现有的 AMO_HWAD (Atomic Memory Operations for Hardware Access & Dirty bits) 机制**。AMO_HWAD 是 RISC-V IOMMU 中用于原子性地更新 Access Flag 和 Dirty Bit 的硬件能力，DPL 在此基础上增加了**日志记录**功能。

扩展方式：
- **原有功能保留**：AMO_HWAD 仍然执行原有的原子读写操作，更新 G-stage 页表中的 access flag 和 dirty state
- **新增触发点**：当 PTW (Page Table Walk) 过程中因写操作触发 dirty bit 更新时，额外触发 GPA 和 IOHGATP 值的日志记录
- **透明集成**：这种扩展对正常翻译路径零干扰，dirty logging 以副作用形式发生在 PTW 过程中

### 1.2 PTW 与 Dirty Bit 更新的关联

PTW 是 IOMMU 进行地址翻译时的页表遍历过程。当设备发起 DMA 写操作时：

```
DMA Write → IOMMU PTW → G-stage页表遍历 → 发现PTE未设置dirty bit →
触发AMO_HWAD原子更新dirty bit → DPL触发日志记录
```

关键设计点在于 DPL 的触发条件是**PTW 更新 dirty bit 这一动作本身**，而非单纯的页表遍历。这确保了只有真正被写入的页面才会被记录，避免了过度记录的问题。

### 1.3 GPA 和 IOHGATP Buffer 分离设计

提案中一个重要的设计决策是将 GPA (Guest Physical Address) 和 IOHGATP (IO Hypervisor Guest Address Translation and Protection) 值**分别记录到独立的缓冲区**：

| Buffer 类型 | 存储内容 | 设计目的 |
|------------|---------|---------|
| GPA Buffer | 被污染页面的客户物理地址 | 精确定位需要迁移的内存页 |
| IOHGATP Buffer | 污染发生时的 iohgatp 寄存器值 | 保留完整的翻译上下文，支持重建页表状态 |

这种分离设计的深层原因：
1. **效率考量**：GPA 是变长数据（不同页大小），而 IOHGATP 是固定宽度的控制寄存器值，分离存储便于硬件实现
2. **灵活性**：软件可以独立处理两类信息，根据 IOHGATP 的上下文信息来决定如何解析 GPA
3. **缓存友好**：固定宽度的 IOHGATP 条目便于批量处理和缓存预取

### 1.4 CQ/FQ/PQ 队列设计模式

DPL 采用了 RISC-V IOMMU 规范中经典的**命令队列 (Command Queue/CQ)、故障队列 (Fault Queue/FQ) 和轮询队列 (Poll Queue/PQ)** 设计模式：

```
+---------------------------------------------------------+
|                    Dirtylog Queue                       |
+---------------------------------------------------------+
|  GPA Buffer    <---写入--- PTW Dirty Bit Update Event     |
|  IOHGATP Buffer<---写入--- PTW Dirty Bit Update Event     |
|       |              |                                  |
|       v              v                                  |
|  Software reads via Memory-Mapped Registers             |
+---------------------------------------------------------+
```

这种设计的关键特征：
- **异步处理**：硬件将脏页信息推入队列，软件通过轮询或中断方式消费
- **批量操作**：队列机制支持批量读取，减少 MMIO 次数
- **可靠性保证**：队列设计提供了生产者和消费者之间的解耦，确保信息不丢失

---

## 2. 技术实现细节 (Technical Implementation Details)

### 2.1 IOHGATP 页表遍历期间的脏页日志机制

当 IOMMU 执行 IOHGATP 页表遍历时，脏页日志的工作流程如下：

```
Step 1: IOMMU 接收到设备 DMA 写请求
Step 2: 执行 G-stage 页表遍历
Step 3: 检查目标 PTE 的 D (Dirty) bit 状态
Step 4: 如果 D=0 且写权限存在：
        a. 执行 AMO_HWAD 原子操作设置 D=1
        b. 触发 DPL 日志记录：
           - 将当前 GPA 追加到 GPA Buffer
           - 将当前 IOHGATP 值追加到 IOHGATP Buffer
Step 5: 完成正常的地址翻译
```

### 2.2 GPA 和 IOHGATP 值分别日志记录的机制

提案设计了两套独立的 buffer 维护机制：

**GPA Buffer 格式**（提案待定）：
- 可能采用变长条目格式，编码页面地址和页面大小信息
- 考虑到 4KB/2MB/1GB 等多种页面粒度，地址编码需要支持多种偏移量

**IOHGATP Buffer 格式**（提案待定）：
- 固定宽度条目，直接存储 iohgatp CSR 的完整值
- 包含 VMID、PPN、模式位等关键信息

这种分离设计的实现考量在于：
- **IOHGATP 上下文恢复价值高**：知道 GPA 的同时如果知道污染发生时的完整翻译上下文，可以支持更复杂的状态重建
- **软件处理灵活性**：分离后软件可以先收集批量的 GPA，再根据对应的 IOHGATP 进行分组处理

### 2.3 通过 Memory-Mapped Registers 的缓冲区维护

DPL 提案采用内存映射寄存器来管理缓冲区：

| 寄存器类型 | 功能 |
|-----------|------|
| GPA Buffer Base | GPA Buffer 的物理地址 |
| GPA Buffer Size | Buffer 容量（决定何时回绕） |
| GPA Buffer Head/Tail | 生产者/消费者指针 |
| IOHGATP Buffer Base | IOHGATP Buffer 的物理地址 |
| IOHGATP Buffer Size | Buffer 容量 |
| IOHGATP Buffer Head/Tail | 生产者/消费者指针 |
| DPL Status/Control | 启用/禁用位、中断使能等 |

这种设计的优点：
- **软件兼容性**：与现有 IOMMU 寄存器接口保持一致
- **硬件实现简化**：硬件只需读写内存，无需复杂的软件接口
- **性能优化**：支持 DMA 方式的批量数据传输

---

## 3. 行业对比 (Industry Comparison)

### 3.1 ARM FEAT_HDBSS vs Intel PML vs RISC-V DPL

| 特性 | ARM FEAT_HDBSS | Intel PML | RISC-V DPL |
|------|----------------|-----------|------------|
| **架构位置** | Armv8.1+ VMSA (Stage-2) | VT-d EPT | RISC-V IOMMU G-stage |
| **日志格式** | HDB (Hardware Dirty Bit) 结构 | PML buffer (4KB aligned) | 待定 (GPA + IOHGATP 分离) |
| **触发条件** | Stage-2 页表 dirty bit 更新 | EPT dirty bit 更新 | IOHGATP PTW dirty bit 更新 |
| **队列机制** | 专用 HDBI (Dirty Log Instruction) | 专用 PML buffer descriptor | CQ/FQ/PQ 模式扩展 |
| **CPU 协同** | 通过 HCR_EL2.VM 相关位协同 | 通过 EPT dirty bit 协同 | 计划与 CPU Dirty Logging TG 协同 |
| **状态恢复** | HDB 重建 stage-2 页表状态 | PML 数据直接用于迁移 | 待定 |

### 3.2 FEAT_DBM/EPT Dirty Bit 与 DPL 的本质区别

**FEAT_DBM (ARM) / EPT Dirty Bit (Intel) / AMO_HWAD (RISC-V)**：
- 本质是**页表维护功能**：在页表条目中标记页面已被写入
- 只能回答"页面是否被污染"的二元问题
- 需要软件主动扫描才能找到所有污染页面
- 典型的"Pull"模式：软件需要主动查询

**FEAT_HDBSS (ARM) / PML (Intel) / DPL (RISC-V)**：
- 本质是**污染日志功能**：自动记录污染事件
- 记录了"哪些页面被污染"的详细信息
- 硬件主动推送污染页面列表
- 典型的"Push"模式：硬件主动通知

### 3.3 共同模式与设计分歧

**共同模式**：
1. **事件驱动**：都依赖于底层 dirty bit 状态变化作为触发源
2. **环形缓冲区**：都采用生产者-消费者环形缓冲区设计
3. **批量记录**：都支持一次性记录多个污染页面
4. **中断通知**：都支持缓冲区满时产生中断通知软件

**设计分歧**：
1. **上下文保存粒度**：ARM HDBSS 保存完整的页表结构信息，Intel PML 仅保存 GPA，RISC-V DPL 采用分离的双 buffer 设计
2. **状态重建方式**：ARM 需要通过 HDB 重建页表，Intel PML 数据可直接用于迁移，RISC-V DPL 方式待定
3. **与 CPU 协同**：ARM 和 Intel 已有成熟的 CPU-IOMMU 协同方案，RISC-V DPL 正在规划中

---

## 4. 使用场景与收益 (Use Cases and Benefits)

### 4.1 实时迁移场景 (Live Migration Scenarios)

**Pre-copy 阶段**：
```
源主机:
  while (迭代次数 < 最大值 && 脏页率 > 阈值) {
    1. 读取 DPL queue 获取新增脏页列表
    2. 传输这些页面到目标主机
    3. 清除/标记已传输页面
    4. 等待下一轮迭代
  }

目标主机:
  接收页面数据并写入
```

DPL 在 pre-copy 中的价值：
- **迭代加速**：传统 bitmap 扫描需要 O(n) 时间复杂度，DPL 提供 O(k) 的增量记录（k=实际脏页数）
- **传输效率提升**：减少不必要的页面传输，特别是对于低污染场景
- **CPU 开销降低**：消除持续的 bitmap 扫描开销

**Post-copy 阶段**：
```
VM 在目标主机启动后:
  1. 缺失页面触发 page fault
  2. Fault handler 向源主机请求对应页面
  3. 源主机通过 DPL 确认页面是否在传输期间被污染
  4. 如果已污染，重新传输；否则使用预传输的数据
```

### 4.2 跨 CPU 和设备访问的系统级脏页跟踪

在**共享 G-stage 表**场景中，CPU 和 IOMMU 共用同一套页表：

```
+---------------------------------------------------------+
|                    共享 G-stage 页表                     |
+---------------------------------------------------------+
|  CPU 侧:                                                 |
|    Guest VM 写入 -> G-stage PTW -> 设置 dirty bit -> CPU DPL|
|                                                          |
|  IOMMU 侧:                                               |
|    Device DMA -> IOHGATP PTW -> 设置 dirty bit -> IOMMU DPL|
+---------------------------------------------------------+
```

DPL 的关键价值在于：
- **统一视图**：IOMMU DPL 记录设备引发的污染，CPU DPL 记录 CPU 引发的污染
- **协同追踪**：只有两者结合才能提供完整的系统级污染跟踪
- **一致性保证**：避免一方污染被遗漏导致的迁移失败

### 4.3 性能影响与 CPU 开销降低

**传统软件 bitmap 扫描的开销**：
- 全量扫描时间：O(page_count)，对于 64GB VM 需要扫描 16M 个 bitmap 位
- 每次迁移迭代都需要全量扫描
- 即使没有污染也需要扫描，造成无谓的 CPU 消耗

**DPL 的开销模型**：
- 写操作时：增加少量硬件逻辑比较 dirty bit 是否从 0->1
- 污染事件发生时：GPA + IOHGATP 写入 buffer（约 16-32 字节）
- 软件读取：批量 DMA 读取，O(k) 复杂度（k=实际脏页数）

**预估收益**：
- 对于 5% 污染率的 VM，DPL 可减少约 95% 的污染跟踪 CPU 开销
- 迁移迭代次数可从 20+ 次降低到 5-10 次
- 迁移总时间缩短 30-50%（取决于应用负载特征）

---

## 5. 挑战与考虑 (Challenges and Considerations)

### 5.1 商业 IOMMU 当前均不支持脏日志功能

文档指出的核心问题：**No commercially available IOMMU currently supports Dirty Logging functionality**

原因分析：
1. **市场需求**：脏日志功能主要影响虚拟化场景，而在非虚拟化环境中价值有限
2. **硬件复杂度**：需要额外的硬件状态机和 buffer 管理逻辑
3. **标准化进程**：ARM 和 Intel 虽然有类似功能，但 IOMMU 层面的支持仍在完善中
4. **软件栈依赖**：需要 KVM/QEMU 等虚拟化软件的配合支持

### 5.2 软件 Bitmap 扫描的局限性

传统软件 bitmap 扫描方案的问题：

| 维度 | 局限性 |
|------|--------|
| **时间复杂度** | O(n) 扫描所有页面，即使无污染也必须扫描 |
| **内存带宽** | 每次扫描都需要读取整个 bitmap，造成内存带宽浪费 |
| **延迟** | 扫描期间新产生的污染可能被遗漏，需要频繁扫描 |
| **精度** | 无法区分污染时间点，只能提供迭代开始时的静态快照 |
| **功耗** | 持续扫描导致不必要的功耗增加 |

### 5.3 共享 G-stage 表的协调挑战

共享 G-stage 表场景引入了复杂的协调问题：

**场景描述**：
```
CPU 和 IOMMU 共享同一个 G-stage 页表
- CPU 拥有页表的"主控"权限
- IOMMU 需要在翻译时读取页表
- 双方都可能触发 dirty bit 更新
```

**协调挑战**：

1. **一致性保证**：
   - CPU 和 IOMMU 对 dirty bit 的更新必须原子协调
   - 需要防止一方更新时另一方的 stale read

2. **DPL 触发竞争**：
   - CPU 和 IOMMU 可能在极短时间内对同一页面触发 DPL
   - 需要去重或合并机制

3. **状态同步**：
   - CPU 可能修改页表结构（e.g., 页表分裂）
   - IOMMU 持有的 IOHGATP 上下文可能失效

4. **缓存一致性**：
   - G-stage 页表通常缓存在 TLB 中
   - DPL 触发时需要确保 TLB 状态与页表一致

### 5.4 与 CPU Dirty Page Logging TG 的集成

DPL 提案明确提到需要"Cooperate with the CPU Dirty Page Logging TG and unify the GPA buffer format"

集成挑战：

| 挑战类型 | 具体问题 |
|---------|---------|
| **格式统一** | CPU DPL 和 IOMMU DPL 需要使用相同的 GPA 编码格式 |
| **协同触发** | 双方需要协调何时开始/停止日志记录 |
| **状态合并** | 需要合并来自 CPU 和 IOMMU 的污染记录 |
| **去重处理** | 同一页面的污染可能同时被 CPU 和 IOMMU 记录 |
| **生命周期管理** | G-stage 表切换时，双方的 DPL 状态需要正确保存/恢复 |

---

## 6. 设计原理 (Design Rationale)

### 6.1 分离 GPA 和 IOHGATP Buffer 的设计决策

**支持分离的论据**：

1. **信息完整性**：
   - GPA 本身不包含翻译上下文
   - 知道页面地址但不知道发生时使用的是哪个页表结构
   - 分离设计允许软件在处理时携带完整上下文

2. **硬件实现效率**：
   - IOHGATP 是固定宽度（与 iohgatp CSR 宽度一致）
   - GPA 是变长（取决于页大小和压缩策略）
   - 分离存储便于硬件的 buffer 指针管理和地址计算

3. **软件处理灵活性**：
   - 可以独立于 GPA 单独处理 IOHGATP
   - 支持延迟 GPA 解析（先处理 IOHGATP 过滤不关心的条目）
   - 便于实现流式处理和并行处理

**潜在替代方案的缺陷**：

| 替代方案 | 缺陷 |
|---------|------|
| 合并存储为单一结构 | 固定结构导致 GPA 空间浪费，或变长结构导致硬件解析复杂 |
| 仅记录 GPA | 丢失翻译上下文，无法支持复杂的状态重建场景 |
| 仅记录 IOHGATP | 无法精确定位污染页面 |

### 6.2 队列-based 设计的好处

**队列设计的优势**：

1. **生产-消费解耦**：
   - 硬件（生产者）仅需写入队列，无需关心软件处理逻辑
   - 软件（消费者）可以按自己的节奏处理，不阻塞硬件

2. **批量操作优化**：
   - 避免每次污染事件都触发中断
   - 支持 interrupt coalescing，减少中断风暴
   - 批量读取提高内存总线效率

3. **可靠性保证**：
   - 环形队列提供有界 buffer
   - Head/Tail 指针机制确保不丢失数据
   - 溢出时有明确的处理策略（覆盖/阻塞）

4. **与现有 IOMMU 基础设施一致**：
   - RISC-V IOMMU 已有的 CQ/FQ 设计提供了成熟的框架
   - 软件驱动只需复用相同的队列处理模式
   - 降低实现风险和验证复杂度

### 6.3 扩展 AMO_HWAD 机制的设计考量

**选择扩展 AMO_HWAD 而非新建独立机制的原因**：

1. **最小化硬件改动**：
   - AMO_HWAD 已在 IOMMU 内部执行
   - 只需在 AMO_HWAD 成功的"副作用"路径上添加日志逻辑
   - 避免引入全新的硬件状态机

2. **语义一致性**：
   - DPL 本质上就是 dirty bit 更新的日志
   - 与 AMO_HWAD 的语义紧密耦合
   - 在dirty bit 更新点触发日志是最自然的设计

3. **避免重复功能**：
   - 不需要额外的触发条件判断
   - 复用 AMO_HWAD 的原子性保证
   - 减少验证工作量

4. **向后兼容**：
   - 不启用 DPL 时，AMO_HWAD 行为不变
   - DPL 是可选扩展，不影响现有系统

---

## 7. 总结

RISC-V IOMMU Dirty Page Logging (DPL) 提案填补了当前虚拟化基础设施中的一个关键空白。通过复用 AMO_HWAD 机制并在 PTW 过程中脏位更新时触发日志记录，DPL 能够在 IOMMU 层面实现对设备引发污染的硬件辅助追踪。

**核心设计亮点**：
- GPA 和 IOHGATP 的分离 buffer 设计在信息完整性和实现效率之间取得了良好平衡
- 队列-based 设计确保了生产-消费解耦和批量操作优化
- 与 CPU Dirty Page Logging TG 的协作规划体现了系统级设计思维

**待解决的关键问题**：
- 与 CPU DPL 的格式统一和协同机制
- 共享 G-stage 场景下的状态一致性保证
- 商业实现的可行性验证

DPL 提案的成功将标志着 RISC-V 在虚拟化支持方面追平 ARM 和 Intel 的重要一步，为云服务商提供更高效的 VM 迁移能力。
