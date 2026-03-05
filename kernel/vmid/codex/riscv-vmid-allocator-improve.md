# Linux/RISC-V VMID Allocator 优化方案（参考 ARM64）

## 1. 范围与输入

目标文件：`/home/zq/work-space/repo/patch-work/linux/arch/riscv/kvm/vmid.c`

规范补充来源：
- `/home/zq/Downloads/arch-spec/riscv/riscv-privileged.pdf`
- 重点章节：Chapter 21（21.2.10 `hgatp`，21.3.2 `HFENCE.VVMA/HFENCE.GVMA`）

参考补丁（ARM64）：
- https://lore.kernel.org/all/20211122121844.867-1-shameerali.kolothum.thodi@huawei.com/
- https://lore.kernel.org/all/20211122121844.867-2-shameerali.kolothum.thodi@huawei.com/
- https://lore.kernel.org/all/20211122121844.867-3-shameerali.kolothum.thodi@huawei.com/
- https://lore.kernel.org/all/20211122121844.867-4-shameerali.kolothum.thodi@huawei.com/
- https://lore.kernel.org/all/20211122121844.867-5-shameerali.kolothum.thodi@huawei.com/

本地内核代码对应提交（便于追溯补丁内容）：
- `417838392f2e` `KVM: arm64: Introduce a new VMID allocator for KVM`（对应 -2）
- `f8051e960922` `KVM: arm64: Make VMID bits accessible outside of allocator`（对应 -3）
- `3248136b3637` `KVM: arm64: Align the VMID allocation with the arm64 ASID`（对应 -4）
- `100b4f092f87` `KVM: arm64: Make active_vmids invalid on vCPU schedule out`（对应 -5）

说明：`-1` 链接是 cover letter。

### 1.1 ARM 参考补丁（-1~-5）逐项提炼

1. `-1`（cover letter）
   - 重点问题：v3 中 `active_vmids` 在部分场景保留了不再活跃的 VMID，导致保留集膨胀。
   - 关键结论：在 vCPU schedule out 时把 active VMID 标记为无效，减少无谓保留。
2. `-2`（对应 commit `417838392f2e`）
   - 关键改动：引入新 `arch/arm64/kvm/vmid.c`，采用 `generation + bitmap + per-CPU active/reserved`。
   - 并发模型：快路径原子、慢路径全局锁、回卷时重建位图并全局 flush。
3. `-3`（对应 commit `f8051e960922`）
   - 关键改动：`kvm_arm_vmid_bits` 对 allocator 外可见，用于后续路径统一 mask 与编码。
4. `-4`（对应 commit `3248136b3637`）
   - 关键改动：把旧 VMID 逻辑从 `arm.c` 移除，切到新 allocator；删除原“force vm exit + 老分配器”路径。
   - 性能动机：减少回卷时强制 VM-exit 带来的 IPI 压力。
5. `-5`（对应 commit `100b4f092f87`）
   - 关键改动：`kvm_arch_vcpu_put()` 调用 `kvm_arm_vmid_clear_active()`，把 active 置为 `VMID_ACTIVE_INVALID`。
   - 预期收益：降低无效 reserved VMID 占位，减少过早回卷概率。

补充：该系列主要给出稳定性与机制性收益，缺少严格性能量化数据；迁移到 RISC-V 时建议补齐基准测试证据。

---

## 2. ARM vs RISC-V：VMID 硬件机制对比

| 维度 | ARM64 (KVM S2) | RISC-V (KVM G-stage) |
|---|---|---|
| VMID 所在寄存器 | `VTTBR_EL2` VMID 字段 | `HGATP` VMID 字段 |
| 位宽来源 | `ID_AA64MMFR1_EL1.VMIDBits`（通常 8 或 16） | 通过写 `HGATP.VMID=all-ones` 再读回探测 `VMIDLEN`（可为 0；`VMIDMAX` 为 7 或 14） |
| TLB 语义 | S2/S1 相关条目按 VMID 区分 | G-stage 以及部分 VS-stage 失效路径依赖 VMID（VVMA 需切到目标 `HGATP.VMID`） |
| 失效指令作用域 | TLBI 具备 inner-shareable 广播语义（可一次性全域失效） | `HFENCE.GVMA/VVMA` 仅本 hart 生效；跨 hart 需要 IPI/SBI RFENCE 协调 |
| 回卷影响 | 可在回卷时做一次全域失效 | 回卷通常需要 `on_each_cpu*` 同步到每个 hart 执行本地 `HFENCE` |

对优化设计的直接影响：
1. ARM 的“回卷时一次广播 flush”在 RISC-V 上不能 1:1 复制为纯硬件广播，必须明确远端同步策略。
2. RISC-V 上必须严格处理“跨 hart 何时完成 flush”这个时序问题，否则 VMID 复用会有 stale TLB 风险。

### 2.1 Chapter 21 规范约束（直接影响方案）

以下条目来自 `riscv-privileged.pdf` Chapter 21（21.2.10 与 21.3.2）：

1. `VMIDLEN` 未指定且可以为 0；实现按 VMID 低位优先实现；`VMIDMAX=7`（Sv32x4）或 `14`（Sv39x4/Sv48x4/Sv57x4）。
2. 写 `hgatp` 不提供“页表写入 -> 后续 G-stage 隐式读”的排序保证；当 VMID 被复用或新 VM 页表有更新时，需要执行 `HFENCE.GVMA`（可在写 `hgatp` 前或后，取决于时序设计）。
3. `HFENCE.GVMA` 是本 hart 语义；要实现系统范围效果，必须在所有相关 hart 执行。
4. 若给定 VMID 的 `hgatp.MODE` 发生变化，必须执行 `HFENCE.GVMA(rs1=x0, rs2=x0 或该 VMID)`，即使旧/新 MODE 为 Bare。
5. `HFENCE.GVMA` 的 `rs1` 为 guest physical address 右移 2 bit 编码，`rs2` 高于 `VMIDMAX` 的 bit 为保留位，软件应清零。

---

## 3. ARM vs RISC-V：Linux VMID allocator 现状对比

### 3.1 ARM64 当前实现（`arch/arm64/kvm/vmid.c`）

核心机制：
1. `atomic64 vmid_generation` + `vmid_map(bitmap)`。
2. per-CPU `active_vmids` 与 `reserved_vmids`。
3. 快路径：`cmpxchg` 更新当前 CPU active VMID，避免频繁拿全局锁。
4. 慢路径：代际不匹配时加锁分配 `new_vmid()`。
5. 回卷时 `flush_context()`：重建 bitmap（保留 active/reserved）+ `__kvm_flush_vm_context()`。
6. `kvm_arch_vcpu_put()` 调用 `kvm_arm_vmid_clear_active()`，减少无效 VMID 保留。

结论：ARM64 方案重点不是“完全避免回卷 flush”，而是“把分配逻辑做成可扩展、并发友好、保留集正确”。

### 3.2 RISC-V 当前实现（`arch/riscv/kvm/vmid.c`）

核心机制：
1. 全局 `vmid_version` + `vmid_next` 线性分配。
2. 每 VM 保存 `vmid_version` 与 `vmid` 两个字段。
3. 快路径：版本未变化则直接返回。
4. 慢路径：全局 `vmid_lock` 下分配。
5. 回卷（`vmid_next == 0`）时：
   - `vmid_version++`
   - `vmid_next = 1`
   - `on_each_cpu_mask(cpu_online_mask, ... hfence_gvma_all ..., wait=1)`
6. 分配完成后对该 VM 所有 vCPU 发 `KVM_REQ_UPDATE_HGATP`。
7. 启动阶段若 `(1 << vmid_bits) < num_possible_cpus()`，直接禁用 VMID（`vmid_bits = 0`）。

### 3.3 差距总结

1. 数据结构差距：RISC-V 没有 bitmap、active/reserved 集合。
2. 并发差距：RISC-V 没有 ARM64 的原子快路径，慢路径全局锁竞争更集中。
3. 回卷策略差距：RISC-V 每次回卷都同步全核 IPI flush，扩展到大核数时抖动明显。
4. 资源利用差距：RISC-V 线性分配 + 全局回卷，不能像 ARM64 一样优先复用可保留 index。

---

## 4. ARM 补丁思路迁移到 RISC-V 的可行性

### 4.1 可直接迁移（高可行）

1. `generation + bitmap` 分配模型。
2. per-CPU `active_vmids` / `reserved_vmids`。
3. 以“VMID index + generation”统一编码 VMID 标识。
4. `kvm_arch_vcpu_put()` 清理 active VMID 的生命周期管理。
5. “快路径原子更新、慢路径加锁分配”的结构化并发模型。

### 4.2 需要改造后迁移（中可行）

1. ARM 的回卷 flush 语义需要适配 RISC-V 本地 `HFENCE` 机制。
2. ARM 的 VTTBR 访问路径需要对应替换为 HGATP 更新路径（`KVM_REQ_UPDATE_HGATP` 仍保留）。
3. ARM `atomic64 id` 的具体位宽/掩码需按 `HGATP_VMID_SHIFT` 与 `VMIDLEN` 适配。

### 4.3 不建议直接照搬（低可行）

1. 直接复制 ARM 的 `__kvm_flush_vm_context` 行为假设（RISC-V 没有同等广播 TLBI 指令语义）。
2. 不加时序控制地引入“延迟 flush”机制（RISC-V 若处理不当易出现跨 hart stale TLB）。

---

## 5. 推荐优化方案（RISC-V）

### 5.1 设计目标

1. 保持 correctness：VMID 复用前必须满足 flush/同步不变式。
2. 降低锁竞争：引入快路径，减少每次 vCPU 进入都走全局锁。
3. 降低回卷抖动：通过保留集与复用策略减少回卷频率和冲击。
4. 尽量小改：优先复用现有 HGATP 更新与 KVM 请求机制。
5. 显式满足 Chapter 21 的排序约束：不依赖“写 HGATP 自带排序”。

### 5.2 新 allocator 结构（建议）

新增状态（`arch/riscv/kvm/vmid.c`）：
1. `atomic64_t vmid_generation`
2. `unsigned long *vmid_map`
3. `DEFINE_PER_CPU(atomic64_t, active_vmids)`
4. `DEFINE_PER_CPU(u64, reserved_vmids)`
5. `DEFINE_RAW_SPINLOCK(vmid_lock)`（或保留 spinlock，按调用上下文决定）

每 VM 状态（`struct kvm_vmid`）建议改为：
1. `atomic64_t id`（高位 generation，低位 index）

### 5.3 算法路径

1. `kvm_riscv_gstage_vmid_update()` 快路径：
   - 读 `kvm_vmid->id` 与当前 generation 比较。
   - 若匹配，尝试更新本 CPU `active_vmids`（cmpxchg），成功即返回。
2. 慢路径：
   - 持 `vmid_lock` 二次检查。
   - 不匹配则 `new_vmid()` 分配或复用 index。
   - 写本 CPU `active_vmids`。
3. 回卷路径：
   - generation 递增。
   - `flush_context()`：重建 `vmid_map`，保留 active/reserved。
   - 触发全核 `HFENCE.GVMA all`（第一阶段保持保守同步模式）。
4. schedule-out 路径：
   - 新增 `kvm_riscv_gstage_vmid_clear_active()`。
   - 在 `kvm_arch_vcpu_put()` 调用，避免回卷时保留过多无效 VMID。

### 5.4 与现有 RISC-V 路径集成点

1. `arch/riscv/include/asm/kvm_vmid.h`
   - 调整 `struct kvm_vmid`。
   - 增加 `kvm_riscv_gstage_vmid_clear_active()` 声明。
2. `arch/riscv/kvm/vmid.c`
   - 替换为 generation+bitmap+active/reserved 实现。
3. `arch/riscv/kvm/vcpu.c`
   - 在 `kvm_arch_vcpu_put()`（或等效退出路径）调用 clear_active。
4. `arch/riscv/kvm/mmu.c`
   - `kvm_riscv_mmu_update_hgatp()` 从新编码中提取 index 写入 HGATP。

### 5.5 基于 Chapter 21 的时序约束（必须实现）

1. VMID 复用路径：
   - 在“复用旧 VMID index 给新 generation”之前，必须确保所有可能缓存该 VMID 的 hart 已执行 `HFENCE.GVMA`（Phase 1 继续使用同步 `on_each_cpu* + wait=1` 保守语义）。
2. HGATP 编程路径：
   - 不将 `ncsr_write(CSR_HGATP, ...)` 视为隐式屏障。
   - 若在该 VMID 下 G-stage 页表有更新，必须配套触发 `HFENCE.GVMA` 请求流（本地 + 远端）。
3. MODE 切换路径：
   - 若后续扩展涉及 `hgatp.MODE` 变化，必须额外执行 `HFENCE.GVMA(rs1=x0, rs2=x0 或 vmid)`，即使模式切到/从 Bare。
4. 参数编码路径：
   - 使用按规范编码的 VMID（高位清零）；涉及地址参数时按“GPA>>2”规则构造指令参数。

---

## 6. 分阶段落地计划

### Phase 1（低风险，建议先做）

目标：先完成 ARM 风格 allocator 主体迁移，但保留“回卷时全核同步 flush”保守策略。

交付：
1. 新数据结构与分配逻辑。
2. vcpu put 清 active。
3. HGATP 更新路径适配。
4. 保持现有 correctness 行为，不引入惰性 flush。

预期收益：
1. 降低锁竞争。
2. 降低无效 VMID 占用。
3. 回卷频率下降（由于 index 复用更有效）。

### Phase 2（中风险，可选）

目标：评估是否引入“flush pending（惰性本地 flush）”以减少回卷时的同步尖峰。

前置条件：
1. 先证明 Phase 1 correctness 稳定。
2. 补齐跨 hart 时序证明与测试。

说明：RISC-V 与 ARM 在 flush 指令作用域不同，Phase 2 需要额外形式化验证，不建议与 Phase 1 同时提交。

### Phase 3（可选增强）

1. 评估是否放宽“`vmid_bits < nr_cpus` 即禁用 VMID”的策略（需基准测试支撑）。
2. 增加 tracepoint/debug 统计：回卷次数、锁冲突、回卷耗时、每核 flush 次数。

---

## 7. 正确性不变式（必须满足）

1. VMID 复用不变式：同一 VMID index 在新 generation 生效前，所有可能持有旧条目的 hart 已完成必须的 flush。
2. 进入 guest 不变式：vCPU 进入前，`HGATP` 中 VMID 与该 VM 的当前有效 VMID 一致。
3. 回卷保留不变式：回卷时所有 active/reserved VMID 都被重新占位到 `vmid_map`，避免冲突重分配。
4. 生命周期不变式：vCPU schedule-out 后 active 标记可失效，防止不必要的长期保留。
5. 排序不变式：任何依赖 G-stage 页表更新可见性的路径，必须显式经由 `HFENCE.GVMA` 建立顺序，不依赖写 `HGATP`。

---

## 8. 验证计划

### 8.1 功能正确性

1. 单 VM 多 vCPU 长稳运行（无异常 page fault / 指令异常）。
2. 高频 vCPU 迁核场景（配合 `kvm_riscv_local_tlb_sanitize()`）。
3. 大量 VM 创建/销毁（触发回卷）。
4. MMU 更新 + HFENCE 请求混合压力。
5. 覆盖 `VMIDLEN=0`（无 VMID）与 `VMIDLEN>0` 两类平台路径。

### 8.2 并发与一致性

1. 压测回卷窗口（多核并发进入 guest）。
2. 检查 `KVM_REQ_UPDATE_HGATP` 的覆盖率（所有 vCPU 均更新）。
3. lockdep + KCSAN（若环境允许）。
4. 规则检查：确认不存在“仅写 HGATP、不发 HFENCE”的 VMID 复用路径。

### 8.3 性能评估

核心指标：
1. VM entry/exit 延迟分布（P50/P99）。
2. 回卷次数与单次回卷耗时。
3. `vmid_lock` 竞争次数。
4. 大核数平台下抖动幅度。
5. 远端 `HFENCE.GVMA` 次数与尾延迟（评估回卷同步成本）。

---

## 9. 风险评估

高风险：
1. 若在 RISC-V 过早引入惰性 flush，可能出现跨 hart stale TLB 窗口。

中风险：
1. `struct kvm_vmid` 从双字段改为原子编码后，涉及多个读写路径适配。
2. 与现有 `KVM_REQ_UPDATE_HGATP` 的时序联动需谨慎复核。

低风险：
1. schedule-out 清 active（该策略已被 ARM 证明有效）。

---

## 10. 结论

1. ARM VMID allocator 的主干思想（generation + bitmap + active/reserved + 快慢路径）可以迁移到 RISC-V，且可显著改善当前线性分配器的可扩展性。
2. 真正的架构差异点在于 flush 机制：RISC-V 需要显式远端同步，不能简单照搬 ARM 的广播语义。
3. 建议采用“两阶段策略”：
   - 先做保守且收益明确的 Phase 1（推荐）。
   - 再评估更激进的惰性 flush Phase 2。

该路线兼顾了 correctness、工程可落地性和后续性能演进空间。
