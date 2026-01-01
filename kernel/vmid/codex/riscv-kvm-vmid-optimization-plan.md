# RISC-V KVM VMID 分配器优化实现方案（参考 arm64 与 RISC-V ASID）

本文给出在 RISC-V KVM 中改进 VMID 分配器的技术方案，借鉴 arm64 KVM VMID allocator 以及 RISC-V ASID allocator 的设计思路，目标是降低回卷成本并改善并发一致性。

## 1. 目标与非目标

目标：
1. 减少 VMID 回卷时对所有 CPU 的强制 IPI 刷新频率。
2. 在 VMID 资源紧张时仍保证正确性与可预测的性能退化。
3. 与现有 KVM 请求/运行循环无缝集成，保持代码可维护性。

非目标：
1. 不改变 RISC-V KVM 仍然“每 VM 一个 VMID”的模型。
2. 不引入跨 VM 的 VMID 回收列表或复杂回收策略。
3. 不改动现有 TLB 子系统对外接口（仅复用或扩展）。

## 2. 现状与问题点（基于当前实现）

现实现的关键特点：
1. 全局 `vmid_next` 线性分配，VMID 用尽后回卷。
2. 回卷时立即对所有 CPU 触发 `hfence.gvma all`（IPI 广播）。
3. 不维护 per-CPU active/reserved 或 bitmap。

主要问题：
1. VMID 回卷代价高：全 CPU IPI + 全量 TLB flush。
2. 高频 VM 创建/销毁场景下回卷频率增加，性能波动大。
3. 分配器无法判断某 VMID 是否仍在某 CPU 上活跃，仅能全量清理。

## 3. 优化设计概览

总体思路：
1. 引入“版本号 + 位图”的 VMID allocator。
2. 维护 per-CPU active/reserved VMID 集合，避免回卷时无谓保留。
3. 引入 per-CPU TLB flush pending，采用“延迟本地 flush”替代全 CPU IPI。

设计参考来源：
1. arm64 KVM VMID allocator 的 generation + bitmap + active/reserved 逻辑。
2. RISC-V ASID allocator 的“回卷 + pending flush + 下一次切换本地 flush”。

## 4. 数据结构与全局状态

新增/调整的全局状态：
1. `vmid_generation`：全局 VMID 版本号（atomic64）。
2. `vmid_map`：当前版本已分配 VMID 的位图。
3. `active_vmids`（per-CPU, atomic64）：当前 CPU 上活跃 VMID。
4. `reserved_vmids`（per-CPU, u64）：回卷时保留的 VMID。
5. `vmid_tlb_flush_pending`（cpumask）：需要在下一次 vCPU 进入前执行本地 `hfence.gvma all` 的 CPU。
6. `vmid_lock`：保护分配与回卷。

新增宏（示意）：
1. `VMID_MASK` / `VMID_FIRST_VERSION` / `vmid2idx()` / `idx2vmid()`
2. `VMID_ACTIVE_INVALID`（用于 schedule out 清除）。

## 5. 核心算法设计

### 5.1 分配路径（new_vmid）

1. 若 `kvm->arch.vmid.vmid` 非 0，尝试在新版本中保留旧 index。
2. 若旧 index 未占用，则复用（更新到新版本）。
3. 否则从 `vmid_map` 中分配新 index。
4. 若无空闲 index，触发回卷。

### 5.2 回卷路径（flush_context）

回卷操作：
1. 递增 `vmid_generation`。
2. 清空 `vmid_map`。
3. 遍历所有 CPU：将 `active_vmids` 或 `reserved_vmids` 标记进 `vmid_map`。
4. 设置 `vmid_tlb_flush_pending = all CPUs`。

与当前实现的差异：
- 不再立即 IPI 触发全量 `hfence.gvma all`。
- 延迟到每个 CPU 下一次 vCPU 进入前执行本地 flush。

### 5.3 vCPU 进入路径（kvm_riscv_gstage_vmid_update）

1. 快路径：若 `active_vmids` 有效且版本匹配，使用 cmpxchg 更新并返回。
2. 慢路径：持锁检查版本，必要时调用 `new_vmid()`。
3. 若本 CPU 在 `vmid_tlb_flush_pending`，执行 `hfence.gvma all` 并清除该 CPU pending 标记。
4. 更新 `active_vmids`。
5. 若 VMID 变化，向所有 vCPU 发 `KVM_REQ_UPDATE_HGATP`。

### 5.4 vCPU 退出路径（kvm_riscv_gstage_vmid_clear_active）

在 `kvm_arch_vcpu_put()` 中加入：
1. 将 `active_vmids` 设置为 `VMID_ACTIVE_INVALID`。
2. 允许回卷时不保留不活跃的 VMID。

## 6. 与现有 KVM 子系统的接口改动

涉及文件（建议新增/修改）：
1. `arch/riscv/kvm/vmid.c`：核心 allocator 实现替换。
2. `arch/riscv/include/asm/kvm_vmid.h`：新增接口与结构字段。
3. `arch/riscv/kvm/vcpu.c`：`kvm_arch_vcpu_put()` 中清除 active VMID。
4. `arch/riscv/kvm/mmu.c`：保持 `kvm_riscv_mmu_update_hgatp()` 逻辑不变，但注意 pending flush 的协同。

## 7. 与 HGATP 更新与 TLB flush 的交互

1. VMID 变更后仍通过 `KVM_REQ_UPDATE_HGATP` 更新 HGATP。
2. pending flush 由 vCPU 进入前执行，保证 HGATP 切换前 TLB 已清理。
3. 现有 `kvm_riscv_gstage_vmid_sanitize()` 仍保留，用于 vCPU 迁核时局部清理。

## 8. 并发与一致性保证

关键点：
1. `vmid_lock` 保护回卷与分配，避免并发下重复回卷。
2. 双重检查（锁前 + 锁后）避免重复分配。
3. pending flush 保证在 VMID 被复用前，每 CPU 至少执行一次本地 `hfence.gvma all`。

## 9. 回退策略与兼容性

1. 若硬件 VMID 数量不足，保持现有逻辑：`vmid_bits = 0`，走无 VMID 路径。
2. 若 allocator 运行异常，可通过编译选项或运行时开关回退到旧分配器（可选实现）。

## 10. 预期收益与代价

收益：
1. 避免回卷时全 CPU IPI 刷新，降低抖动。
2. 在多 VM 场景下提高稳定性。

代价：
1. 维护更多全局状态与 per-CPU 数据。
2. vCPU 进入路径多一次 pending flush 判断。

## 11. 实现步骤建议（分阶段）

阶段 1：引入新 allocator 的数据结构与基础代码路径，但保持回卷时 IPI 刷新作为保守兜底。 
阶段 2：启用 pending flush 机制，回卷时不再 IPI 全量刷新。 
阶段 3：补充统计与调试接口（可选），验证性能与正确性。 

## 12. 测试与验证建议

1. 功能测试：创建/销毁 VM、频繁 vCPU 迁核、内存映射更新。 
2. 压力测试：大量 VM churn，验证回卷频率与性能抖动。 
3. 一致性验证：开启/关闭 VMID 支持路径对比结果。 
4. 与现有 TLB flush 请求（HFENCE/VVMA）路径联动回归。 

## 13. 风险与注意事项

1. pending flush 必须与 VMID 复用严格绑定，否则可能出现 stale TLB 使用。 
2. vCPU 退出时清除 active_vmids，避免回卷保留过多 VMID。 
3. VMID 变更后必须确保 HGATP 更新先于 guest 进入。 

## 14. 关键函数伪代码草案

### 14.1 `kvm_riscv_gstage_vmid_update()`（进入前更新）

```
function kvm_riscv_gstage_vmid_update(vcpu):
    vmid = vcpu.kvm.arch.vmid
    if !vmid_bits:
        return

    if vmid_gen_match(vmid.id):
        old = per_cpu(active_vmids)
        if old != 0 and cmpxchg(active_vmids, old, vmid.id) succeeds:
            return

    lock(vmid_lock)
    vmid_id = vmid.id
    if !vmid_gen_match(vmid_id):
        vmid_id = new_vmid(vmid)
        vmid.id = vmid_id

    if cpu in vmid_tlb_flush_pending:
        local_hfence_gvma_all()
        clear cpu from vmid_tlb_flush_pending

    per_cpu(active_vmids) = vmid_id
    unlock(vmid_lock)

    if vmid changed:
        for each vcpu in vm:
            kvm_make_request(KVM_REQ_UPDATE_HGATP, vcpu)
```

### 14.2 `new_vmid()`（分配）

```
function new_vmid(vmid):
    if vmid.id != 0:
        new_id = generation | old_index(vmid.id)
        if update_reserved(old_id, new_id):
            return new_id
        if bitmap_test_and_set(old_index) == 0:
            return new_id

    idx = find_next_zero_bit(vmid_map, cur_idx)
    if idx not found:
        generation += VMID_FIRST_VERSION
        flush_context()
        idx = find_next_zero_bit(vmid_map, 1)

    set bit idx in vmid_map
    cur_idx = idx
    return generation | idx
```

### 14.3 `flush_context()`（回卷处理）

```
function flush_context():
    clear vmid_map
    for each cpu:
        vmid = xchg(active_vmids[cpu], 0)
        if vmid == 0:
            vmid = reserved_vmids[cpu]
        set bit index(vmid) in vmid_map
        reserved_vmids[cpu] = vmid
    set all cpus in vmid_tlb_flush_pending
```

### 14.4 `kvm_riscv_gstage_vmid_clear_active()`（vCPU 退出）

```
function kvm_riscv_gstage_vmid_clear_active():
    per_cpu(active_vmids) = VMID_ACTIVE_INVALID
```

## 15. 补丁拆分建议（文件/函数级）

### Patch 1/4：新增 VMID allocator 基础设施
修改文件：  
- `arch/riscv/kvm/vmid.c`：添加 version+bitmap+active/reserved 数据结构与分配逻辑  
- `arch/riscv/include/asm/kvm_vmid.h`：新增接口声明与必要结构  
- `arch/riscv/kvm/Makefile`（如需新增文件）  

关键函数：  
- `flush_context()` / `new_vmid()` / `kvm_riscv_gstage_vmid_update()`  

### Patch 2/4：vCPU 进入/退出路径集成
修改文件：  
- `arch/riscv/kvm/vcpu.c`：  
  - 在 `kvm_arch_vcpu_put()` 增加 `kvm_riscv_gstage_vmid_clear_active()`  
  - 保持 `kvm_riscv_gstage_vmid_update()` 调用位置  

### Patch 3/4：pending flush 机制接入
修改文件：  
- `arch/riscv/kvm/vmid.c`：引入 `vmid_tlb_flush_pending` 逻辑  
- `arch/riscv/kvm/vcpu.c`：进入前检测并执行本地 `hfence.gvma all`  

### Patch 4/4：文档与调试（可选）
修改文件：  
- `Documentation/virt/kvm/riscv/vmid.rst`（新增或扩展）  
- debugfs 或 tracepoint（可选）  

## 16. 风险点的形式化不变式清单

1. **VMID-版本一致性**：  
   对任一 VM，`vmid.id` 的 version 必须等于 `vmid_generation`，否则该 VM 进入 guest 前必须重新分配。  

2. **TLB flush 先于复用**：  
   若某 CPU 可能持有旧 version 的 TLB 条目，则在该 CPU 上复用 VMID index 前必须执行一次 `hfence.gvma all`。  

3. **active/reserved 保留正确性**：  
   在回卷时，任何仍在 CPU 上运行的 VMID 必须被记录到 `reserved_vmids` 或 `active_vmids`，以避免被错误分配给其他 VM。  

4. **HGATP 更新顺序**：  
   对任一 vCPU，若其所属 VM 的 VMID 发生变化，则必须在进入 guest 之前完成 HGATP 更新。  

5. **无 VMID 模式安全性**：  
   当 `vmid_bits == 0`，必须保证每次 HGATP 更新后执行 `hfence.gvma all`。  

6. **队列降级安全性**：  
   HFENCE 队列满时降级为 `KVM_REQ_TLB_FLUSH` 必须保证语义不弱于原请求。  

## 17. 伪代码映射到具体函数签名与字段修改清单

### 17.1 新增/调整的结构字段

文件：`arch/riscv/include/asm/kvm_vmid.h`（或新建私有头）  

建议新增字段（示意）：  
- `struct kvm_vmid { atomic64_t id; };`（若需要替换现有 `vmid`/`vmid_version` 组合）  
- 或保留现有 `struct kvm_vmid`，新增：  
  - `atomic64_t id`（组合 version+index）  
  - `u64 reserved;`（可选，按 VM 记录最近一次 VMID index）  

新增全局/CPU 变量（建议放在 `arch/riscv/kvm/vmid.c`）：  
- `static atomic64_t vmid_generation;`  
- `static unsigned long *vmid_map;`  
- `static DEFINE_PER_CPU(atomic64_t, active_vmids);`  
- `static DEFINE_PER_CPU(u64, reserved_vmids);`  
- `static cpumask_t vmid_tlb_flush_pending;`  

### 17.2 具体函数签名映射

- **新函数**：  
  - `static void kvm_riscv_vmid_flush_context(void);`  
  - `static u64 kvm_riscv_vmid_new(struct kvm_vmid *vmid);`  
  - `void kvm_riscv_gstage_vmid_clear_active(void);`  

- **修改函数**：  
  - `void kvm_riscv_gstage_vmid_update(struct kvm_vcpu *vcpu);`  
    - 新增 pending flush 处理与 active_vmids 更新  
  - `int kvm_riscv_gstage_vmid_init(struct kvm *kvm);`  
    - 初始化 `vmid->id = 0`  

### 17.3 访问点与调用位置

- `arch/riscv/kvm/vcpu.c`：  
  - `kvm_arch_vcpu_put()` 添加 `kvm_riscv_gstage_vmid_clear_active()`  
  - `kvm_arch_vcpu_load()` 保持 `kvm_riscv_mmu_update_hgatp()`，但 `kvm_riscv_gstage_vmid_update()` 仍在 run loop 早期执行  

- `arch/riscv/kvm/vmid.c`：  
  - 替换原 `vmid_version/vmid_next` 逻辑  
  - 引入 bitmap 分配与代际回卷  

## 18. 每个 patch 的预计 diff 轮廓

### Patch 1/4：引入新 allocator 框架
- 新增：`vmid_generation`, `vmid_map`, `active_vmids`, `reserved_vmids`, `vmid_tlb_flush_pending`  
- 新增：`kvm_riscv_vmid_flush_context()` / `kvm_riscv_vmid_new()`  
- 修改：`kvm_riscv_gstage_vmid_init()`（将 VMID 置零）  

预计 diff 轮廓：  
```
arch/riscv/kvm/vmid.c
  + static atomic64_t vmid_generation
  + static unsigned long *vmid_map
  + static DEFINE_PER_CPU(atomic64_t, active_vmids)
  + static DEFINE_PER_CPU(u64, reserved_vmids)
  + static cpumask_t vmid_tlb_flush_pending
  + new_vmid(), flush_context()
```

### Patch 2/4：进入/退出路径集成
- 修改：`kvm_arch_vcpu_put()` 增加 `kvm_riscv_gstage_vmid_clear_active()`  
- 新增：`kvm_riscv_gstage_vmid_clear_active()` 实现  

预计 diff 轮廓：  
```
arch/riscv/kvm/vcpu.c
  + call kvm_riscv_gstage_vmid_clear_active()
arch/riscv/kvm/vmid.c
  + void kvm_riscv_gstage_vmid_clear_active(void)
```

### Patch 3/4：pending flush 机制
- 修改：`kvm_riscv_gstage_vmid_update()`  
  - 快路径 cmpxchg  
  - 进入 slow path 处理 pending flush  
  - 本地 `hfence.gvma all` 并清 pending  

预计 diff 轮廓：  
```
arch/riscv/kvm/vmid.c
  ~ kvm_riscv_gstage_vmid_update()
    + check/clear vmid_tlb_flush_pending
```

### Patch 4/4：文档/调试（可选）
- 新增：`Documentation/virt/kvm/riscv/vmid.rst` 或更新现有文档  
- 可选：tracepoint/debugfs  

## 19. 新增自测点与 tracepoint 建议

### 19.1 自测点建议

1. **VMID 回卷测试**  
   - 启动大量 VM，确保触发回卷，并验证所有 vCPU 能继续运行。  
2. **vCPU 迁核一致性**  
   - 频繁迁移 vCPU，检查是否出现 G-stage page fault 异常或 stale 映射。  
3. **无 VMID 模式**  
   - 强制 `vmid_bits=0`，验证 HGATP 更新与 `hfence.gvma all` 正常执行。  
4. **高并发分配**  
   - 多 vCPU 并发进入 guest，确保 VMID 分配不重复。  

### 19.2 tracepoint 建议

1. **VMID 分配事件**  
   - `trace_kvm_riscv_vmid_alloc(vmid, generation, cpu)`  
2. **VMID 回卷事件**  
   - `trace_kvm_riscv_vmid_rollover(old_gen, new_gen)`  
3. **pending flush 处理**  
   - `trace_kvm_riscv_vmid_pending_flush(cpu)`  
4. **HGATP 更新事件**  
   - `trace_kvm_riscv_hgatp_update(vmid, pgd_phys)`  

## 20. 结构体字段命名与迁移方案（兼容现有 `struct kvm_vmid`）

### 20.1 当前结构

```
struct kvm_vmid {
    unsigned long vmid_version;
    unsigned long vmid;
};
```

### 20.2 分阶段迁移方案

**阶段 A：新增组合字段并保持兼容**  
在 `struct kvm_vmid` 中新增组合字段 `id`，同时保留旧字段：  

```
struct kvm_vmid {
    atomic64_t id;               // [generation | index]
    unsigned long vmid_version;  // 兼容字段（阶段性保留）
    unsigned long vmid;          // 兼容字段（阶段性保留）
};
```

同步策略：  
- allocator 内部只更新 `id`；  
- 每次写 `id` 后，同步更新 `vmid`/`vmid_version`（供旧路径暂时读取）；  
- 提供 helper：  
  - `kvm_vmid_id_read()`  
  - `kvm_vmid_index(id)`  
  - `kvm_vmid_generation(id)`  

**阶段 B：迁移读路径**  
- `kvm_riscv_mmu_update_hgatp()` 从 `vmid.vmid` 改为 `kvm_vmid_index(id)`；  
- `kvm_riscv_gstage_vmid_ver_changed()` 从 `vmid_version` 改为 `kvm_vmid_generation(id)`；  
- 清理所有 `vmid.vmid`/`vmid_version` 直接访问点。  

**阶段 C：移除旧字段（可选）**  
- 删除 `vmid`/`vmid_version`，只保留 `id`；  
- 若担心外部工具依赖，可保留只读缓存字段（不参与逻辑）。  

### 20.3 字段命名建议

- `id`：组合字段（generation|index）  
- `generation`：用 helper 计算，不单独存储  
- `index`：VMID index（低位）  
- `reserved`：可选，记录最近一次分配 index  

## 21. TRACE_EVENT() 模板草案

建议新增文件：`include/trace/events/kvm_riscv.h`  

```c
#undef TRACE_SYSTEM
#define TRACE_SYSTEM kvm_riscv

#if !defined(_TRACE_KVM_RISCV_H) || defined(TRACE_HEADER_MULTI_READ)
#define _TRACE_KVM_RISCV_H

#include <linux/tracepoint.h>

TRACE_EVENT(kvm_riscv_vmid_alloc,
    TP_PROTO(u64 vmid_id, u64 gen, u32 idx, int cpu),
    TP_ARGS(vmid_id, gen, idx, cpu),
    TP_STRUCT__entry(
        __field(u64, vmid_id)
        __field(u64, gen)
        __field(u32, idx)
        __field(int, cpu)
    ),
    TP_fast_assign(
        __entry->vmid_id = vmid_id;
        __entry->gen = gen;
        __entry->idx = idx;
        __entry->cpu = cpu;
    ),
    TP_printk("vmid_id=%llx gen=%llx idx=%u cpu=%d",
              __entry->vmid_id, __entry->gen, __entry->idx, __entry->cpu)
);

TRACE_EVENT(kvm_riscv_vmid_rollover,
    TP_PROTO(u64 old_gen, u64 new_gen),
    TP_ARGS(old_gen, new_gen),
    TP_STRUCT__entry(
        __field(u64, old_gen)
        __field(u64, new_gen)
    ),
    TP_fast_assign(
        __entry->old_gen = old_gen;
        __entry->new_gen = new_gen;
    ),
    TP_printk("old_gen=%llx new_gen=%llx",
              __entry->old_gen, __entry->new_gen)
);

TRACE_EVENT(kvm_riscv_vmid_pending_flush,
    TP_PROTO(int cpu),
    TP_ARGS(cpu),
    TP_STRUCT__entry(
        __field(int, cpu)
    ),
    TP_fast_assign(
        __entry->cpu = cpu;
    ),
    TP_printk("cpu=%d", __entry->cpu)
);

TRACE_EVENT(kvm_riscv_hgatp_update,
    TP_PROTO(u64 hgatp, u64 vmid_id, phys_addr_t pgd_phys),
    TP_ARGS(hgatp, vmid_id, pgd_phys),
    TP_STRUCT__entry(
        __field(u64, hgatp)
        __field(u64, vmid_id)
        __field(phys_addr_t, pgd_phys)
    ),
    TP_fast_assign(
        __entry->hgatp = hgatp;
        __entry->vmid_id = vmid_id;
        __entry->pgd_phys = pgd_phys;
    ),
    TP_printk("hgatp=%llx vmid_id=%llx pgd=%llx",
              __entry->hgatp, __entry->vmid_id,
              (unsigned long long)__entry->pgd_phys)
);

#endif /* _TRACE_KVM_RISCV_H */

#include <trace/define_trace.h>
```

集成方式（示意）：  
- 在 `arch/riscv/kvm/` 添加 `trace.h` 并 `#include <trace/events/kvm_riscv.h>`；  
- 参考 arm64 的 `trace_arm.h` 加入编译入口。  

## 22. VMID 回卷性能评估指标与基准脚本思路

### 22.1 指标建议

1. **回卷次数/秒**：`kvm_riscv_vmid_rollover` 计数。  
2. **回卷完成时间**：从 rollover 到所有 vCPU HGATP 更新完成的延迟。  
3. **hfence 触发次数**：全量 `hfence.gvma all` 与 `hfence.gvma.vmid_all` 次数。  
4. **guest 进入延迟**：回卷前后 `kvm_riscv_vcpu_run` 的平均进入耗时差异。  
5. **IPI/退出率**：回卷期间因 IPI 导致的 guest exit 次数。  

### 22.2 基准脚本思路（示意）

**脚本 A：VM churn**  
- 快速创建/销毁 N 个 VM，触发回卷；  
- 统计 rollover 与 hfence 次数。  

**脚本 B：高并发 vCPU 进入**  
- 固定 VM 数，提升 vCPU 频繁进入频率；  
- 观察 pending flush 次数与分配冲突。  

**脚本 C：迁核场景**  
- 通过 `taskset`/cpuset 强制迁核；  
- 观察 `hfence.gvma.vmid_all` 次数与 guest 稳定性。  

### 22.3 采集方式建议

1. **trace-cmd**  
   - `trace-cmd record -e kvm_riscv:*` 收集 tracepoint。  
2. **ftrace function graph**  
   - 跟踪 `kvm_riscv_local_hfence_gvma_all` 耗时。  
3. **统计导出**  
   - 可选新增 debugfs/kvm_stats 计数器用于长期观测。  

## 23. Tracepoint 调用点映射（插桩位置）

| Tracepoint | 建议插桩函数 | 触发时机 |
|---|---|---|
| `kvm_riscv_vmid_alloc` | `kvm_riscv_vmid_new()` | 成功分配 VMID（设置 `vmid->id` 之后） |
| `kvm_riscv_vmid_rollover` | `kvm_riscv_vmid_flush_context()` | `vmid_generation` 递增之后 |
| `kvm_riscv_vmid_pending_flush` | `kvm_riscv_gstage_vmid_update()` | 检测到 pending flush 并执行本地 `hfence.gvma all` |
| `kvm_riscv_hgatp_update` | `kvm_riscv_mmu_update_hgatp()` | `ncsr_write(CSR_HGATP, hgatp)` 之后 |

建议插入点示意：  
- `kvm_riscv_vmid_new()`：在 `vmid->id` 最终赋值处。  
- `kvm_riscv_vmid_flush_context()`：`vmid_generation` 递增后立即记录。  
- `kvm_riscv_gstage_vmid_update()`：执行 `local_hfence_gvma_all()` 后记录一次。  
- `kvm_riscv_mmu_update_hgatp()`：写 HGATP 后记录一次，用于关联 HGATP 更新与 VMID 变化。  

## 24. 简化测试脚本骨架（bash）

### 24.1 VM churn（快速创建/销毁 VM）

```bash
#!/usr/bin/env bash
set -euo pipefail

VMLINUX=/path/to/Image
INITRD=/path/to/initrd.img
QEMU=qemu-system-riscv64
N=32
RUNTIME=5

run_vm() {
  ${QEMU} -machine virt -m 256M -smp 1 \
    -kernel ${VMLINUX} -initrd ${INITRD} \
    -append "console=ttyS0" -nographic \
    -no-reboot >/dev/null 2>&1 &
  echo $!
}

for i in $(seq 1 ${N}); do
  pid=$(run_vm)
  sleep 0.1
  kill -9 ${pid} || true
done

sleep ${RUNTIME}
```

### 24.2 迁核测试（vCPU 迁移）

```bash
#!/usr/bin/env bash
set -euo pipefail

VMLINUX=/path/to/Image
INITRD=/path/to/initrd.img
QEMU=qemu-system-riscv64

${QEMU} -machine virt -m 512M -smp 4 \
  -kernel ${VMLINUX} -initrd ${INITRD} \
  -append "console=ttyS0" -nographic &
PID=$!

# 强制迁核（示意，需按实际 taskset/host CPU 调整）
for cpu in 0 1 2 3; do
  taskset -pc ${cpu} ${PID}
  sleep 1
done

kill -9 ${PID} || true
```

## 25. 迁移期 helper 宏/inline 签名与示例

### 25.1 helper 签名建议

```c
static inline u64 kvm_vmid_id_read(const struct kvm_vmid *v)
{
    return atomic64_read(&v->id);
}

static inline u32 kvm_vmid_index(u64 id)
{
    return (u32)(id & VMID_INDEX_MASK);
}

static inline u64 kvm_vmid_generation(u64 id)
{
    return id & ~VMID_INDEX_MASK;
}

static inline void kvm_vmid_set_id(struct kvm_vmid *v, u64 id)
{
    atomic64_set(&v->id, id);
    /* 兼容字段同步 */
    v->vmid = kvm_vmid_index(id);
    v->vmid_version = kvm_vmid_generation(id);
}
```

### 25.2 使用示例

```c
u64 id = kvm_vmid_id_read(&kvm->arch.vmid);
if (kvm_vmid_generation(id) != atomic64_read(&vmid_generation))
    id = kvm_riscv_vmid_new(&kvm->arch.vmid);

/* HGATP 写入 */
hgatp |= (kvm_vmid_index(id) << HGATP_VMID_SHIFT);
```

---

结论：
可以参考 arm64 KVM VMID allocator 与 RISC-V ASID allocator 的逻辑，对当前 RISC-V KVM VMID 分配器进行优化。核心是引入 version+bitmap+active/reserved+pending flush 机制，用更细粒度的方式替代全 CPU IPI flush，从而在保证正确性的前提下降低回卷代价。

## 26. “最小可合入”精简版 patch 拆分

目标：在最少 patch 里先引入**可回卷但不引入复杂优化**的最小安全改动，再逐步扩展。

### Patch A：统一 VMID 组合字段（低风险基础）
- 添加 `struct kvm_vmid::id` 与 helper 宏/inline  
- 同步维护旧字段（`vmid`/`vmid_version`）  
- 不改 allocator 逻辑，仅为后续迁移做准备  

### Patch B：切换读路径到组合字段（低风险迁移）
- `kvm_riscv_mmu_update_hgatp()` 改用 `kvm_vmid_index(id)`  
- `kvm_riscv_gstage_vmid_ver_changed()` 改用 `kvm_vmid_generation(id)`  
- 保持原 `vmid_version` 的更新逻辑不动  

### Patch C：引入 bitmap 分配与回卷（核心功能）
- 新增 `vmid_generation + vmid_map`  
- 用新分配器替换 `vmid_next` 逻辑  
- 仍保留 IPI 全量 flush（行为与现状一致，便于合入）  

### Patch D：pending flush 与 active/reserved（性能优化，可选）
- 引入 `active_vmids/reserved_vmids` 与 `vmid_tlb_flush_pending`  
- 回卷时不再 IPI 全量 flush，改为下一次 vCPU 进入本地 flush  
- 这是性能优化 patch，可单独 review/测试  

### Patch E：文档与 tracepoint（可选）
- 文档补充与 tracepoint 仅在稳定后合入  

## 27. 可运行测试套件（含 trace-cmd 自动收集）

目录建议：`tools/testing/riscv-kvm-vmid/`

### 27.1 目录结构

```
tools/testing/riscv-kvm-vmid/
  run.sh
  env.sh
  vm_churn.sh
  migrate.sh
  trace.sh
  README.md
```

### 27.2 env.sh（环境配置）

```bash
#!/usr/bin/env bash
export VMLINUX=/path/to/Image
export INITRD=/path/to/initrd.img
export QEMU=qemu-system-riscv64
export TRACE_DIR=/tmp/kvm_riscv_trace
```

### 27.3 trace.sh（自动 trace-cmd 收集）

```bash
#!/usr/bin/env bash
set -euo pipefail
source ./env.sh

mkdir -p ${TRACE_DIR}
trace-cmd record -o ${TRACE_DIR}/trace.dat -e kvm_riscv:* &
TRACE_PID=$!

echo ${TRACE_PID} > ${TRACE_DIR}/trace.pid
```

### 27.4 vm_churn.sh

```bash
#!/usr/bin/env bash
set -euo pipefail
source ./env.sh

N=${N:-32}
SLEEP=${SLEEP:-0.1}

run_vm() {
  ${QEMU} -machine virt -m 256M -smp 1 \
    -kernel ${VMLINUX} -initrd ${INITRD} \
    -append "console=ttyS0" -nographic \
    -no-reboot >/dev/null 2>&1 &
  echo $!
}

for i in $(seq 1 ${N}); do
  pid=$(run_vm)
  sleep ${SLEEP}
  kill -9 ${pid} || true
done
```

### 27.5 migrate.sh

```bash
#!/usr/bin/env bash
set -euo pipefail
source ./env.sh

${QEMU} -machine virt -m 512M -smp 4 \
  -kernel ${VMLINUX} -initrd ${INITRD} \
  -append "console=ttyS0" -nographic &
PID=$!

for cpu in 0 1 2 3; do
  taskset -pc ${cpu} ${PID}
  sleep 1
done

kill -9 ${PID} || true
```

### 27.6 run.sh（统一入口）

```bash
#!/usr/bin/env bash
set -euo pipefail
./trace.sh
./vm_churn.sh
./migrate.sh

TRACE_PID=$(cat /tmp/kvm_riscv_trace/trace.pid)
kill -2 ${TRACE_PID} || true

echo "Trace saved in /tmp/kvm_riscv_trace/trace.dat"
```

## 28. VMID_INDEX_MASK 推导与宏定义位置建议

### 28.1 推导

若 VMID bits 为 `vmid_bits`，则 index mask 为：  
```
VMID_INDEX_MASK = (1UL << vmid_bits) - 1
```

组合字段 `id` 结构：  
- 低 `vmid_bits` 为 index  
- 高位为 generation  

### 28.2 宏定义位置建议

建议在 `arch/riscv/kvm/vmid.c` 或 `arch/riscv/include/asm/kvm_vmid.h` 中定义：  
```
#define VMID_INDEX_MASK ((1UL << vmid_bits) - 1)
#define VMID_GEN_MASK   (~VMID_INDEX_MASK)
```

若 `vmid_bits` 为运行时确定（非编译期常量），建议用 inline：  
```
static inline u64 kvm_vmid_index_mask(void)
{
    return (1UL << vmid_bits) - 1;
}
```

并在 helper 中使用该函数。  
